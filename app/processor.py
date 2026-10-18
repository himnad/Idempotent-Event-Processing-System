
import json
import os
import sqlite3
import time
import redis

REDIS_URL = os.getenv(
    "REDIS_URL", "redis://localhost:6380/0"
)
DB_PATH = os.getenv("DB_PATH", "events.db")

redis_client = redis.Redis.from_url(
    REDIS_URL, decode_responses=True
)


def initialize_database():
    with sqlite3.connect(DB_PATH, timeout=30) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                processed_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


def process_event(event):
    event_id = event["event_id"]
    lock_key = f"event:lock:{event_id}"
    completed_key = f"event:completed:{event_id}"

    if redis_client.exists(completed_key):
        return "duplicate"

    lock_token = os.urandom(16).hex()

    acquired = redis_client.set(
        lock_key, lock_token, nx=True, ex=60
    )

    if not acquired:
        return "busy"

    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO processed_events
                (event_id, event_type, payload)
                VALUES (?, ?, ?)
                """,
                (
                    event_id,
                    event["event_type"],
                    json.dumps(event["payload"])
                )
            )

            inserted = conn.execute(
                "SELECT changes()"
            ).fetchone()[0]

        redis_client.set(completed_key, "1", ex=86400)

        return "processed" if inserted else "duplicate"

    finally:
        redis_client.eval(
            """
            if redis.call('GET', KEYS[1]) == ARGV[1]
            then
                return redis.call('DEL', KEYS[1])
            else
                return 0
            end
            """,
            1,
            lock_key,
            lock_token
        )
