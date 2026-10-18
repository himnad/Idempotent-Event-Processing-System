
import os
import sqlite3
import threading

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Any

from app.rabbitmq import publish_event

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
DEMO_DB_PATH = os.getenv("DEMO_DB_PATH", "/tmp/demo_events.db")
demo_lock = threading.Lock()

app = FastAPI(
    title="Idempotent Event Processing System",
    description=(
        "Public SQLite demo on Render; "
        "full RabbitMQ + Redis architecture available via Docker Compose."
        if DEMO_MODE
        else "Fault-tolerant webhook processing using RabbitMQ and Redis"
    ),
    version="1.1.0"
)


class WebhookEvent(BaseModel):
    event_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    payload: dict[str, Any]


def save_demo_event(event: WebhookEvent):
    with demo_lock:
        with sqlite3.connect(DEMO_DB_PATH, timeout=10) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS demo_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
            """)

            import json

            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO demo_events
                (event_id, event_type, payload)
                VALUES (?, ?, ?)
                """,
                (
                    event.event_id,
                    event.event_type,
                    json.dumps(event.payload)
                )
            )

            conn.commit()
            return "processed" if cursor.rowcount == 1 else "duplicate"


@app.get("/")
def root():
    return {
        "message": "Event Processing API is running",
        "mode": "demo" if DEMO_MODE else "rabbitmq"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhooks", status_code=202)
def receive_webhook(event: WebhookEvent):
    if DEMO_MODE:
        result = save_demo_event(event)

        return {
            "status": result,
            "event_id": event.event_id,
            "mode": "sqlite_demo",
            "persistent": False
        }

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
