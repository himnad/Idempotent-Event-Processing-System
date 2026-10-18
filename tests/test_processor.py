
import sqlite3
import uuid
from concurrent.futures import ThreadPoolExecutor

from app.processor import initialize_database, process_event


def make_event():
    return {
        "event_id": f"test_{uuid.uuid4().hex}",
        "event_type": "payment.completed",
        "payload": {"amount": 500}
    }


def count_records(event_id):
    with sqlite3.connect("events.db") as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM processed_events WHERE event_id=?",
            (event_id,)
        ).fetchone()[0]


def test_first_event_processed():
    initialize_database()
    event = make_event()

    assert process_event(event) == "processed"
    assert count_records(event["event_id"]) == 1


def test_duplicate_event():
    initialize_database()
    event = make_event()

    assert process_event(event) == "processed"
    assert process_event(event) == "duplicate"
    assert count_records(event["event_id"]) == 1


def test_multiple_unique_events():
    initialize_database()
    events = [make_event() for _ in range(20)]

    results = [process_event(event) for event in events]

    assert results.count("processed") == 20


def test_concurrent_duplicate_events():
    initialize_database()
    event = make_event()

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(
            executor.map(process_event, [event] * 50)
        )

    assert results.count("processed") == 1
    assert count_records(event["event_id"]) == 1
    assert all(
        result in ("processed", "duplicate", "busy")
        for result in results
    )


def test_database_persistence():
    initialize_database()
    event = make_event()

    process_event(event)

    assert count_records(event["event_id"]) == 1
