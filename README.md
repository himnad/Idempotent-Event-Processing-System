# Idempotent Event Processing System

A fault-tolerant, Dockerized webhook processing system with an interactive **EventFlow** dashboard, built using **Python, FastAPI, RabbitMQ, Redis, SQLite, React, and Docker**.

The full local deployment accepts webhooks, processes events asynchronously using four concurrent consumers, prevents duplicate database records, retries failed events, and routes messages that repeatedly fail to a Dead Letter Queue (DLQ). The public deployment provides a lightweight SQLite-based demonstration of event submission and deduplication.

![Python](https://img.shields.io/badge/Python-3.x-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-REST%20API-009688)
![RabbitMQ](https://img.shields.io/badge/RabbitMQ-Broker-FF6600)
![Redis](https://img.shields.io/badge/Redis-Dedup%20%26%20Locking-DC382D)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![React](https://img.shields.io/badge/React-19-149ECA)

**[Live EventFlow Dashboard](https://idempotent-event-processing-system.onrender.com/)** · **[Swagger API Docs](https://idempotent-event-processing-system.onrender.com/docs)**

> **Deployment note:** The Render Free demo does **not** run RabbitMQ, Redis, background consumers, retries, or the DLQ. Run Docker Compose locally to use the full asynchronous architecture. The public demo uses ephemeral SQLite storage.

## Table of Contents

- [Why This Project](#why-this-project)
- [Features](#features)
- [EventFlow Dashboard](#eventflow-dashboard)
- [Deployment Modes](#deployment-modes)
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

## Why This Project

Webhook providers such as payment services commonly use **at-least-once delivery**: the same event may arrive multiple times. Without deduplication, repeated delivery can create duplicate records or inconsistent state.

This project demonstrates asynchronous message processing through RabbitMQ, Redis-based coordination between concurrent workers, and database-level uniqueness as the final protection against duplicate inserts.

## Features

- **REST ingestion:** FastAPI webhook endpoints with request validation.
- **Asynchronous processing (local):** RabbitMQ main queue with four consumer workers.
- **Deduplication (local):** Redis-based coordination and SQLite uniqueness on `event_id`.
- **Automatic retries (local):** 2-second retry delay, up to three failed attempts.
- **Dead Letter Queue (local):** Isolates permanently failing messages.
- **EventFlow UI:** Submit events, view responses, detect duplicates, and check API health.
- **Public demo:** Render-hosted React dashboard and SQLite-backed synchronous webhook processing.
- **Docker Compose:** Orchestrates the full local pipeline.
- **Tests and benchmarks:** PyTest suite and processor-level performance scripts.

## EventFlow Dashboard

**Live:** https://idempotent-event-processing-system.onrender.com/

The dashboard uses **React 19, Vite 8, Tailwind CSS 4, and Lucide React**. It supports webhook submission, backend health checks, and a recent-request list. The displayed counters and request history are **browser-session data**, not system-wide metrics or a query of historical database records.

The public demo may take time to respond after inactivity because the free service can spin down.

## Deployment Modes

| Capability | Full local Docker deployment | Public Render Free demo |
|---|---|---|
| React dashboard | Available after frontend build | Yes |
| FastAPI endpoints | Yes | Yes |
| RabbitMQ | Yes | No |
| Redis | Yes | No |
| Four consumer workers | Yes | No |
| Delayed retries and DLQ | Yes | No |
| Duplicate database insert prevention | Yes | Yes |
| SQLite data durability | Local Docker volume | Ephemeral; can reset |
| Webhook processing | Asynchronous | Synchronous |

**Render demo mode:** Set `DEMO_MODE=true`. Incoming events are inserted using SQLite's unique `event_id` constraint (`INSERT OR IGNORE`). This demonstrates duplicate handling without relying on a message broker. Render's local filesystem is ephemeral; records can disappear after restart or redeployment.

**Full local mode:** Run Docker Compose with demo mode disabled to exercise the RabbitMQ → consumer → Redis/SQLite pipeline, including retries and DLQ.

## Architecture

### Full local pipeline

```text
Webhook Client / EventFlow Dashboard
                |
                v
           FastAPI API
                |
                v
        RabbitMQ Main Queue
                |
                v
        Four Consumer Workers
                |
         +------+-------+
         |              |
         v              v
       Redis          SQLite
  (coordination)   (unique event_id)
                |
        On processing failure
                |
                v
       Retry Queue (2s TTL)
                |
                v
        RabbitMQ Main Queue
                |
      After 3 failed attempts
                |
                v
         Dead Letter Queue
```

### Public demo pipeline

```text
Browser / React EventFlow Dashboard
                |
                v
         FastAPI on Render
                |
                v
       SQLite demo database
        (ephemeral storage)
```

## Tech Stack

| Component | Technology |
|---|---|
| Backend API | Python, FastAPI, Pydantic |
| Frontend | React 19, Vite 8 |
| Styling and icons | Tailwind CSS 4, Lucide React |
| Message broker (full mode) | RabbitMQ, Pika |
| Coordination / deduplication (full mode) | Redis |
| Database | SQLite |
| Containerization | Docker, Docker Compose |
| Demo hosting | Render Free |
| Testing | PyTest |

## Project Structure

```text
app/
  main.py                 # FastAPI endpoints, demo mode, frontend serving
  rabbitmq.py             # RabbitMQ connection and queue setup
  consumer.py             # Consumer worker and retry/DLQ handling
  processor.py            # Idempotent processing logic

frontend/
  src/
    App.jsx               # EventFlow dashboard
    index.css             # Tailwind styles
  package.json
  vite.config.js

scripts/
  benchmark.py
  duplicate_benchmark.py
  latency_benchmark.py

tests/
  test_processor.py

Dockerfile                # Multi-stage frontend + backend image
docker-compose.yml
requirements.txt
README.md
```

## Getting Started

### Prerequisites

- Docker Desktop with Docker Compose
- For frontend development outside Docker: Node.js and npm

### 1. Start the full local system

```bash
docker compose up -d --build --scale consumer=4
```

### 2. Verify running services

```bash
docker compose ps
```

### 3. Check API health

```bash
curl http://localhost:8000/health
```

Example response in full mode:

```json
{"status":"ok","mode":"rabbitmq"}
```

### 4. Submit a webhook

```bash
curl -X POST http://localhost:8000/webhooks \
  -H "Content-Type: application/json" \
  -d '{"event_id":"example_001","event_type":"payment.completed","payload":{"amount":500}}'
```

In full mode, a successful request returns HTTP 202 and a response such as:

```json
{"status":"accepted","event_id":"example_001"}
```

### 5. Inspect consumer logs

```bash
docker compose logs --tail=50 consumer
```

### RabbitMQ Management Dashboard

Open http://localhost:15673 and sign in with the **local development-only** example credentials `eventuser` / `eventpass`. Replace demo credentials and use secure secret management before deploying to any shared environment.

### Frontend development

```bash
cd frontend
npm ci
npm run dev
```

Vite proxies `/api` calls to the local backend at `http://localhost:8000`. Start the backend before testing API-dependent dashboard functionality.

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Backend health and active mode |
| `GET` | `/api/health` | Health endpoint used by dashboard |
| `POST` | `/webhooks` | Submit webhook |
| `POST` | `/api/webhooks` | Webhook endpoint used by dashboard |
| `GET` | `/docs` | Interactive Swagger API documentation |

**Webhook request body:**

```json
{
  "event_id": "example_001",
  "event_type": "payment.completed",
  "payload": {"amount": 500}
}
```

`event_id` and `event_type` are required nonempty strings; `payload` is an object.

**Demo-mode response example** (HTTP 202):

```json
{
  "status": "processed",
  "event_id": "example_001",
  "mode": "sqlite_demo",
  "persistent": false
}
```

Resubmitting the same `event_id` in the same demo database returns `"status": "duplicate"`. In full mode, the API returns `"status": "accepted"` when an event is queued; processing happens asynchronously.

## How Idempotency Works

Each event has a unique `event_id`.

1. **Redis (full mode)** coordinates concurrent workers and helps identify recently completed events.
2. **SQLite (both modes)** enforces a unique `event_id` constraint, preventing duplicate database records.

Repeated delivery therefore does not create additional database rows for the same event ID. This is **idempotent database insertion**, not a guarantee of exactly-once execution for arbitrary external side effects.

## Retry and Dead Letter Queue

In the **full local pipeline**:

1. A failed processing attempt is published to a retry queue.
2. RabbitMQ delays redelivery using a 2-second message TTL.
3. The message returns to the main queue for another attempt.
4. After three failed attempts, the message is sent to the DLQ.

These features are **not available in the public Render demo**.

## Testing

```bash
python -m pytest tests -q
```

Latest locally reported result: **5 tests passed**. Tests cover initial processing, duplicate events, multiple unique events, concurrent duplicate submissions, and database persistence.

Frontend production build:

```bash
cd frontend
npm ci
npm run build
```

## Benchmarks

Measured **locally with four concurrent threads and direct processor calls**, not end-to-end HTTP-to-RabbitMQ traffic or Render hosting.

| Benchmark | Result |
|---|---:|
| Unique events processed | 1,000 |
| Unique-event throughput | 142.22 events/s |
| Duplicate benchmark deliveries | 1,000 |
| Duplicate benchmark unique events | 700 |
| Duplicate database records | 0 |
| Duplicate benchmark throughput | 204.91 deliveries/s |
| Average processor latency | 27.73 ms |
| p95 processor latency | 61.70 ms |
| p99 processor latency | 79.82 ms |

Results depend on hardware, workload, and configuration. **Do not interpret these numbers as full-pipeline or cloud-service throughput.**

## Docker Integration Verification

The full local integration was verified for:

- [x] Four RabbitMQ consumers connected
- [x] Webhook accepted by Dockerized API
- [x] Event stored in shared SQLite database
- [x] Duplicate webhook produced only one database record
- [x] Injected failure reached the DLQ

## Limitations

- SQLite is suitable for demos and modest workloads, not a substitute for a production database under high write concurrency.
- Public Render demo uses synchronous SQLite processing, not the full queue-based architecture.
- Render Free local storage is ephemeral; records can reset.
- Dashboard metrics are browser-session-only, not server-wide monitoring.
- Idempotency covers database inserts, not arbitrary external side effects.
- Benchmarks measure the local processor in isolation.
- Example RabbitMQ credentials are for trusted local development only.

## Future Improvements

- PostgreSQL for durable, production-grade storage
- Transactional outbox for reliable follow-up event publication
- Prometheus metrics and monitoring dashboards
- Durable cloud hosting for RabbitMQ, Redis, and worker services
- Server-side metrics and paginated event history
