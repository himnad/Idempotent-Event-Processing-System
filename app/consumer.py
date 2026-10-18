
import json
import logging
import os

import pika

from app.processor import initialize_database, process_event

RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL",
    "amqp://eventuser:eventpass@localhost:5673/"
)

QUEUE = "webhook_events"
RETRY_QUEUE = "webhook_events_retry"
DLQ = "webhook_events_dlq"
MAX_ATTEMPTS = 3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(process)d %(levelname)s %(message)s"
)

logger = logging.getLogger(__name__)


def setup_queues(channel):
    channel.queue_declare(queue=QUEUE, durable=True)

    channel.queue_declare(
        queue=RETRY_QUEUE,
        durable=True,
        arguments={
            "x-message-ttl": 2000,
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": QUEUE
        }
    )

    channel.queue_declare(queue=DLQ, durable=True)
    channel.confirm_delivery()


def publish_message(channel, queue, body, attempt):
    channel.basic_publish(
        exchange="",
        routing_key=queue,
        body=body,
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type="application/json",
            headers={"x-attempt": attempt}
        ),
        mandatory=True
    )


def handle_message(channel, method, properties, body):
    attempt = (properties.headers or {}).get("x-attempt", 1)

    try:
        event = json.loads(body)

        if event.get("payload", {}).get("simulate_failure"):
            raise RuntimeError("Injected test failure")

        result = process_event(event)

        if result == "busy":
            raise RuntimeError("Event currently locked")

        logger.info(
            "Event %s: %s (attempt %s)",
            event["event_id"],
            result,
            attempt
        )

        channel.basic_ack(method.delivery_tag)

    except Exception as exc:
        logger.error(
            "Processing failed on attempt %s: %s",
            attempt,
            exc
        )

        if attempt < MAX_ATTEMPTS:
            destination = RETRY_QUEUE
            next_attempt = attempt + 1
        else:
            destination = DLQ
            next_attempt = attempt

        try:
            publish_message(
                channel,
                destination,
                body,
                next_attempt
            )
            channel.basic_ack(method.delivery_tag)
        except Exception:
            logger.exception("Retry/DLQ publishing failed")
            channel.basic_nack(
                method.delivery_tag,
                requeue=True
            )


def main():
    initialize_database()

    connection = pika.BlockingConnection(
        pika.URLParameters(RABBITMQ_URL)
    )

    try:
        channel = connection.channel()
        setup_queues(channel)

        channel.basic_qos(prefetch_count=1)

        channel.basic_consume(
            queue=QUEUE,
            on_message_callback=handle_message
        )

        logger.info("Consumer started with retry and DLQ support")
        channel.start_consuming()

    except KeyboardInterrupt:
        logger.info("Consumer stopped")

    finally:
        if connection.is_open:
            connection.close()


if __name__ == "__main__":
    main()
