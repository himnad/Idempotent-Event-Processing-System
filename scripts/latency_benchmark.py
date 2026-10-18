
import os
import sys
import time
import uuid
import statistics
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from app.processor import initialize_database, process_event

TOTAL = 1000
WORKERS = 4


def timed_process(event):
    start = time.perf_counter()
    result = process_event(event)
    latency_ms = (time.perf_counter() - start) * 1000
    return result, latency_ms


def percentile(values, percent):
    values = sorted(values)
    index = (len(values) - 1) * percent / 100
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)
    fraction = index - lower
    return values[lower] * (1 - fraction) + values[upper] * fraction


def main():
    initialize_database()

    run_id = uuid.uuid4().hex[:8]

    events = [
        {
            "event_id": f"latency_{run_id}_{i}",
            "event_type": "payment.completed",
            "payload": {"amount": 500}
        }
        for i in range(TOTAL)
    ]

    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        results = list(executor.map(timed_process, events))

    duration = time.perf_counter() - start

    latencies = [latency for _, latency in results]
    processed = sum(result == "processed" for result, _ in results)

    print("\n===== LATENCY BENCHMARK =====")
    print(f"Total events:       {TOTAL}")
    print(f"Workers:            {WORKERS}")
    print(f"Processed:          {processed}")
    print(f"Average latency:    {statistics.mean(latencies):.2f} ms")
    print(f"Median latency:     {statistics.median(latencies):.2f} ms")
    print(f"P95 latency:        {percentile(latencies, 95):.2f} ms")
    print(f"P99 latency:        {percentile(latencies, 99):.2f} ms")
    print(f"Max latency:        {max(latencies):.2f} ms")
    print(f"Throughput:         {TOTAL / duration:.2f} events/sec")
    print("=============================")


if __name__ == "__main__":
    main()
