
import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.rabbitmq import publish_event

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
DEMO_DB_PATH = os.getenv("DEMO_DB_PATH", "/tmp/demo_events.db")
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

demo_lock = threading.Lock()

app = FastAPI(
    title="Idempotent Event Processing System",
    description="Webhook processing with RabbitMQ, Redis and SQLite demo mode",
    version="1.2.0"
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


@app.get("/api/health")
@app.get("/health")
def health():
    return {
        "status": "ok",
        "mode": "demo" if DEMO_MODE else "rabbitmq"
    }


@app.post("/api/webhooks", status_code=202)
@app.post("/webhooks", status_code=202)
def receive_webhook(event: WebhookEvent):
    if DEMO_MODE:
        try:
            result = save_demo_event(event)
        except sqlite3.Error as exc:
            raise HTTPException(
                status_code=500,
                detail="Demo database unavailable"
            ) from exc

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


if (FRONTEND_DIST / "assets").is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST / "assets"),
        name="frontend-assets"
    )


@app.get("/")
def root():
    index_file = FRONTEND_DIST / "index.html"

    if index_file.is_file():
        return FileResponse(index_file)

    return {
        "message": "Event Processing API is running",
        "mode": "demo" if DEMO_MODE else "rabbitmq"
    }
