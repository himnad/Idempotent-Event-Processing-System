
import os
import sys
import time
import uuid
import random
import sqlite3
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from app.processor import initialize_database, process_event

TOTAL = 1000
UNIQUE = 700
WORKERS = 4


def main():
    initialize_database()

    run_id = uuid.uuid4().hex[:10]

    unique_events = [
        {
            "event_id": f"dupbench_{run_id}_{i}",
            "event_type": "payment.completed",
            "payload": {"amount": 500, "index": i}
        }
        for i in range(UNIQUE)
    ]

    random.seed(42)
    duplicates = [
        random.choice(unique_events)
        for _ in range(TOTAL - UNIQUE)
    ]

    events = unique_events + duplicates
    random.shuffle(events)

    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        results = list(executor.map(process_event, events))

    duration = time.perf_counter() - start

    with sqlite3.connect("events.db") as conn:
        stored = conn.execute(
            "SELECT COUNT(*) FROM processed_events WHERE event_id LIKE ?",
            (f"dupbench_{run_id}_%",)
        ).fetchone()[0]

    print("\n===== DUPLICATE BENCHMARK =====")
    print(f"Total deliveries:     {TOTAL}")
    print(f"Unique event IDs:     {UNIQUE}")
    print(f"Duplicate deliveries: {TOTAL - UNIQUE}")
    print(f"Concurrent workers:   {WORKERS}")
    print(f"Processed:            {results.count('processed')}")
    print(f"Duplicate results:    {results.count('duplicate')}")
    print(f"Busy results:         {results.count('busy')}")
    print(f"Database records:     {stored}")
    print(f"Duplicate DB records: {max(0, stored - UNIQUE)}")
    print(f"Execution time:       {duration:.3f} sec")
    print(f"Delivery throughput:  {TOTAL / duration:.2f}/sec")
    print("===============================")

    assert stored == UNIQUE, (
        f"Expected {UNIQUE} unique records, found {stored}"
    )


if __name__ == "__main__":
    main()
