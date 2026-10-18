
import os
import json
import pika

RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL",
    "amqp://eventuser:eventpass@localhost:5673/"
)

QUEUE_NAME = "webhook_events"


def publish_event(event):
    connection = pika.BlockingConnection(
        pika.URLParameters(RABBITMQ_URL)
    )

    try:
        channel = connection.channel()

        channel.queue_declare(
            queue=QUEUE_NAME,
            durable=True
        )

        channel.confirm_delivery()

        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=json.dumps(event).encode("utf-8"),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
                message_id=event["event_id"]
            ),
            mandatory=True
        )

    finally:
        connection.close()
