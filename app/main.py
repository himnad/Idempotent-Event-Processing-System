
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Any

from app.rabbitmq import publish_event

app = FastAPI(
    title="Idempotent Event Processing System",
    description="Fault-tolerant webhook processing using RabbitMQ and Redis",
    version="1.0.0"
)


class WebhookEvent(BaseModel):
    event_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    payload: dict[str, Any]


@app.get("/")
def root():
    return {"message": "Event Processing API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhooks", status_code=202)
def receive_webhook(event: WebhookEvent):
    try:
        publish_event(event.model_dump())

        return {
            "status": "accepted",
            "event_id": event.event_id
        }

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Message broker unavailable"
        ) from exc
