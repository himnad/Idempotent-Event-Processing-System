
import os
import sys
import time
import uuid
import sqlite3
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from app.processor import initialize_database, process_event

TOTAL_EVENTS = 1000
WORKERS = 4


def main():
    initialize_database()

    run_id = uuid.uuid4().hex[:8]

    events = [
        {
            "event_id": f"bench_{run_id}_{i}",
            "event_type": "payment.completed",
            "payload": {"amount": 500, "index": i}
        }
        for i in range(TOTAL_EVENTS)
    ]

    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        results = list(executor.map(process_event, events))

    duration = time.perf_counter() - start

    processed = results.count("processed")
    duplicates = results.count("duplicate")
    busy = results.count("busy")

    with sqlite3.connect("events.db") as conn:
        stored = conn.execute(
            "SELECT COUNT(*) FROM processed_events WHERE event_id LIKE ?",
            (f"bench_{run_id}_%",)
        ).fetchone()[0]

    print("\n===== PERFORMANCE BENCHMARK =====")
    print(f"Total events:       {TOTAL_EVENTS}")
    print(f"Concurrent workers: {WORKERS}")
    print(f"Processed:          {processed}")
    print(f"Duplicates:         {duplicates}")
    print(f"Busy:               {busy}")
    print(f"Stored in SQLite:   {stored}")
    print(f"Execution time:     {duration:.3f} seconds")
    print(f"Throughput:         {TOTAL_EVENTS / duration:.2f} events/sec")
    print("=================================")


if __name__ == "__main__":
    main()
