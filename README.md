# Idempotent Event Processing System

A fault-tolerant, Dockerized webhook processing backend built with **Python, FastAPI, RabbitMQ, Redis, and SQLite**.

It accepts webhook events, processes them asynchronously with four concurrent consumers, guarantees that duplicate deliveries never create duplicate database records, retries failures automatically, and routes permanently failing messages to a Dead Letter Queue (DLQ).

![Python](https://img.shields.io/badge/Python-3.x-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-REST%20API-009688)
![RabbitMQ](https://img.shields.io/badge/RabbitMQ-Broker-FF6600)
![Redis](https://img.shields.io/badge/Redis-Dedup%20%26%20Locking-DC382D)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)

---

## Table of Contents

- [Why This Project](#why-this-project)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [API Reference](#api-reference)
- [How Idempotency Works](#how-idempotency-works)
- [Retry and Dead Letter Queue](#retry-and-dead-letter-queue)
- [Testing](#testing)
- [Benchmarks](#benchmarks)
- [Docker Integration Verification](#docker-integration-verification)
- [Limitations](#limitations)
- [Future Improvements](#future-improvements)

---

## Why This Project

Payment gateways and other webhook providers use **at-least-once delivery**: the same event may arrive more than once. Without safeguards, this leads to duplicate records and inconsistent state.

This project demonstrates a practical pattern for handling that safely: asynchronous processing through a message broker, Redis-based coordination between concurrent workers, and a database-level uniqueness guarantee as the final safety net.

## Features

- **REST ingestion** – FastAPI webhook endpoint
- **Async processing** – RabbitMQ main queue with four concurrent consumer workers
- **Deduplication and locking** – Redis coordinates concurrent processing and detects recently completed events
- **Persistent storage** – SQLite with a unique constraint on `event_id`
- **Idempotent inserts** – safe under at-least-once delivery
- **Automatic retries** – 2-second delay between attempts, maximum of three attempts
- **Dead Letter Queue** – permanently failing messages are isolated for inspection
- **Docker Compose** – one-command orchestration
- **Automated tests** – PyTest suite
- **Benchmarks** – throughput, duplicate-delivery, and latency scripts

## Architecture

```text
Webhook Client
      │
      ▼
FastAPI REST API
      │
      ▼
RabbitMQ Main Queue
      │
      ▼
Four Consumer Workers
      │
      ├──► Redis   (locking / deduplication)
      ├──► SQLite  (persistent records)
      └──► Processing failure
                │
                ▼
          Retry Queue (2-second TTL)
                │
                ▼
          Main Queue  ──► retried
                │
                ▼  (after 3 failed attempts)
        Dead Letter Queue
```

## Tech Stack

| Component                 | Technology     |
| ------------------------- | -------------- |
| API                       | FastAPI        |
| Language                  | Python         |
| Message broker            | RabbitMQ       |
| Deduplication and locking | Redis          |
| Database                  | SQLite         |
| Message client            | Pika           |
| Containerization          | Docker Compose |
| Testing                   | PyTest         |

## Project Structure

```text
app/
  main.py          # FastAPI app and webhook endpoint
  rabbitmq.py      # RabbitMQ connection and queue setup
  consumer.py      # Consumer worker and retry/DLQ handling
  processor.py     # Idempotent event processing logic

scripts/
  benchmark.py
  duplicate_benchmark.py
  latency_benchmark.py

tests/
  test_processor.py

Dockerfile
docker-compose.yml
requirements.txt
README.md
```

## Getting Started

### Prerequisites

- Docker Desktop
- Docker Compose

### 1. Start the application

```bash
docker compose up -d --build --scale consumer=4
```

### 2. Verify services are running

```bash
docker compose ps
```

### 3. Check API health

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status": "ok"}
```

### 4. Submit a webhook event

```bash
curl -X POST http://localhost:8000/webhooks \
  -H "Content-Type: application/json" \
  -d '{"event_id":"example_001","event_type":"payment.completed","payload":{"amount":500}}'
```

### 5. View consumer logs

```bash
docker compose logs --tail=50 consumer
```

### RabbitMQ Management Dashboard

Open <http://localhost:15673>.

For local development, the example Docker Compose file uses:

| Username    | Password    |
| ----------- | ----------- |
| `eventuser` | `eventpass` |

> **Security:** These are demonstration credentials. Replace them and manage secrets properly before deploying outside a trusted local environment.

## API Reference

| Method | Endpoint     | Description                  |
| ------ | ------------ | ---------------------------- |
| `GET`  | `/health`    | Service health check         |
| `POST` | `/webhooks`  | Submit a webhook event       |

**Webhook request body**

| Field        | Type   | Description                         |
| ------------ | ------ | ----------------------------------- |
| `event_id`   | string | Unique identifier used for dedup    |
| `event_type` | string | Event category, e.g. `payment.completed` |
| `payload`    | object | Event data                          |

## How Idempotency Works

Every event carries a unique `event_id`, and two layers protect against duplicates:

1. **Redis** coordinates concurrent workers and detects recently completed events, so two workers never process the same event at the same time.
2. **SQLite** enforces a unique constraint on `event_id`, acting as the final guarantee at the storage layer.

Repeated delivery of the same event therefore does not create additional database records.

> This design provides idempotent database insertion under at-least-once delivery. It does **not** guarantee exactly-once execution of arbitrary external side effects.

## Retry and Dead Letter Queue

When processing fails:

1. The consumer publishes the message to a retry queue.
2. RabbitMQ delays redelivery using a 2-second message TTL.
3. The message returns to the main queue.
4. Processing is attempted again.
5. After three failed attempts, the message is routed to the DLQ.

## Testing

```bash
python -m pytest tests -q
```

Latest verified result:

```text
5 passed in 0.61s
```

The tests cover:

- Initial event processing
- Duplicate events
- Multiple unique events
- Concurrent duplicate submissions
- Database persistence

## Benchmarks

Measured locally using four concurrent threads and direct processor calls.

| Benchmark                        |           Result |
| -------------------------------- | ---------------: |
| Unique events processed          |            1,000 |
| Unique-event throughput          | 142.22 events/s  |
| Duplicate benchmark deliveries   |            1,000 |
| Duplicate benchmark unique events|              700 |
| Duplicate database records       |                0 |
| Duplicate benchmark throughput   | 204.91 deliveries/s |
| Average processor latency        |         27.73 ms |
| p95 processor latency            |         61.70 ms |
| p99 processor latency            |         79.82 ms |

> These figures reflect the **processor benchmark environment only**, not end-to-end HTTP-to-RabbitMQ throughput. Results vary with hardware, workload, and configuration.

## Docker Integration Verification

Successfully verified:

- [x] Four RabbitMQ consumers connected
- [x] Webhook accepted through the Dockerized API
- [x] Event persisted to the shared SQLite database
- [x] Repeated webhook delivery produced only one database record
- [x] Injected processing failure reached the Dead Letter Queue

## Limitations

- SQLite is suited to local development and demos, not high-write production workloads.
- Idempotency covers database inserts, not external side effects.
- Benchmarks measure the processor in isolation, not the full pipeline.
- Demo credentials are included for local use only.

## Future Improvements

- PostgreSQL for production-grade persistence
- Transactional outbox for reliable publication of follow-up events
- Prometheus metrics and monitoring
