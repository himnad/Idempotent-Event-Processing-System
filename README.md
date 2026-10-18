\# Idempotent Event Processing System



A fault-tolerant, Dockerized event processing backend built using \*\*Python, FastAPI, RabbitMQ, Redis, and SQLite\*\*.



The system accepts webhook events, processes them asynchronously using four concurrent consumers, prevents duplicate database inserts, retries failed events, and routes permanently failing messages to a Dead Letter Queue (DLQ).



\## Features



\- REST API for webhook ingestion using FastAPI

\- RabbitMQ-based asynchronous message processing

\- Four concurrent worker processes

\- Redis-based distributed event locking and deduplication

\- SQLite persistence with unique event IDs

\- At-least-once message delivery with idempotent database inserts

\- Automatic retries with a 2-second delay

\- Maximum of three processing attempts

\- Dead Letter Queue for failed messages

\- Docker Compose orchestration

\- Automated PyTest tests

\- Throughput, duplicate-delivery, and latency benchmarks



\## Architecture



```text

Webhook Client

&#x20;     |

&#x20;     v

FastAPI REST API

&#x20;     |

&#x20;     v

RabbitMQ Main Queue

&#x20;     |

&#x20;     v

Four Consumer Workers

&#x20;     |

&#x20;     +----> Redis (Locking / Deduplication)

&#x20;     |

&#x20;     +----> SQLite (Persistent Records)

&#x20;     |

&#x20;     +----> Processing Failure

&#x20;                   |

&#x20;                   v

&#x20;             Retry Queue

&#x20;             (2-second TTL)

&#x20;                   |

&#x20;                   v

&#x20;             Main Queue

&#x20;                   |

&#x20;                   v

&#x20;          Dead Letter Queue

&#x20;          (After 3 Attempts)

```



\## Technology Stack



| Component | Technology |

|---|---|

| API | FastAPI |

| Programming Language | Python |

| Message Broker | RabbitMQ |

| Deduplication and Locking | Redis |

| Database | SQLite |

| Containerization | Docker Compose |

| Testing | PyTest |

| Message Client | Pika |



\## Project Structure



```text

app/

&#x20; main.py

&#x20; rabbitmq.py

&#x20; consumer.py

&#x20; processor.py



scripts/

&#x20; benchmark.py

&#x20; duplicate\_benchmark.py

&#x20; latency\_benchmark.py



tests/

&#x20; test\_processor.py



Dockerfile

docker-compose.yml

requirements.txt

README.md

```



\## Getting Started



\### Prerequisites



\- Docker Desktop

\- Docker Compose



\### Start the Application



```bash

docker compose up -d --build --scale consumer=4

```



\### Verify Running Services



```bash

docker compose ps

```



\### API Health Check



```bash

curl http://localhost:8000/health

```



Expected response:



```json

{"status":"ok"}

```



\### Submit a Webhook Event



```bash

curl -X POST http://localhost:8000/webhooks \\

&#x20; -H "Content-Type: application/json" \\

&#x20; -d '{"event\_id":"example\_001","event\_type":"payment.completed","payload":{"amount":500}}'

```



\### View Consumer Logs



```bash

docker compose logs --tail=50 consumer

```



\### RabbitMQ Management Dashboard



Open:



http://localhost:15673



For local development, the example Docker Compose configuration uses:



\- Username: `eventuser`

\- Password: `eventpass`



\*\*Security:\*\* These are demonstration credentials. Replace them and configure secrets securely before deploying outside a trusted local environment.



\## Idempotency Strategy



Each event contains a unique `event\_id`.



The processor uses Redis to coordinate concurrent processing and detect recently completed events. SQLite also enforces uniqueness for event IDs.



Repeated delivery of the same event does not create additional database records.



This design supports idempotent database insertion under at-least-once delivery. It does \*\*not\*\* guarantee exactly-once execution of arbitrary external side effects.



\## Retry and Dead Letter Queue



When an event fails:



1\. The consumer publishes the message to a retry queue.

2\. RabbitMQ delays redelivery using a 2-second message TTL.

3\. The message returns to the main queue.

4\. Processing is attempted again.

5\. After three failed attempts, the message is routed to the DLQ.



\## Testing



Run:



```bash

python -m pytest tests -q

```



Latest verified result:



```text

5 passed in 0.61s

```



Tests cover initial processing, duplicate events, multiple unique events, concurrent duplicate submissions, and database persistence.



\## Benchmarks



The following results were measured locally using four concurrent threads and direct processor calls.



| Benchmark | Result |

|---|---:|

| Unique events processed | 1,000 |

| Unique-event throughput | 142.22 events/sec |

| Duplicate benchmark deliveries | 1,000 |

| Duplicate benchmark unique events | 700 |

| Duplicate database records | 0 |

| Duplicate benchmark throughput | 204.91 deliveries/sec |

| Average processor latency | 27.73 ms |

| p95 processor latency | 61.70 ms |

| p99 processor latency | 79.82 ms |



These measurements represent the processor benchmark environment, \*\*not end-to-end HTTP-to-RabbitMQ throughput\*\*. Results may vary by hardware, workload, and configuration.



\## Docker Integration Verification



Successfully verified:



\- Four RabbitMQ consumers connected

\- Webhook accepted through the Dockerized API

\- Event persisted to the shared SQLite database

\- Repeated webhook delivery produced only one database record

\- Injected processing failure reached the Dead Letter Queue



\## Future Improvements



\- PostgreSQL for production-grade persistence

\- Transactional outbox for reliable publication of follow-up events

\- Prom

