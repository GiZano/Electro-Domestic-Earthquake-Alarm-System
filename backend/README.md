# QuakeGuard Backend Service

QuakeGuard is a distributed, high-throughput backend system designed for the real-time ingestion, cryptographic validation, and processing of seismic data from IoT devices.

This repository hosts the **API Gateway**, **Background Worker**, and **Persistence Layer** definitions, serving as the core infrastructure for an Earthquake Early Warning (EEW) system.

---

## 📂 Project Structure

The project is organized as a modular microservice architecture:

```text
backend/
└── api/
    ├── init-scripts/       # SQL initialization scripts (PostGIS)
    │   └── ollama-entrypoint.sh  # Auto-pulls the Ollama model on startup
    ├── src/                # Source Code
    │   ├── main.py         # FastAPI Gateway & REST Endpoints
    │   ├── worker.py       # Stream consumer (Redis Streams, batched persistence)
    │   ├── ingest.py       # Redis Streams ingestion substrate (group/DLQ/recovery)
    │   ├── timescale.py    # Idempotent TimescaleDB hypertable + aggregates migration
    │   ├── geo.py          # Geohash zone-index (Redis) + candidate pruning
    │   ├── ai_report_worker.py  # Dedicated AI report consumer (Ollama + state machine)
    │   ├── ollama_client.py     # Deterministic LLM client (anti-hallucination)
    │   ├── database.py     # SQLAlchemy Connection & Pool config
    │   ├── models.py       # ORM Models (GeoAlchemy2 + EmergencyReport)
    │   └── schemas.py      # Pydantic DTOs
    ├── scripts/
    │   └── load_test.py    # Load generator (N sensors at H Hz, stream or HTTP)
    ├── docker/
    │   └── postgres-timescale.Dockerfile  # TimescaleDB + PostGIS DB image
    ├── tests/              # Testing Suite
    │   ├── __init__.py
    │   ├── stress_test.py  # Load testing & ECDSA simulation tool
    │   └── unit/           # Unit tests (worker, ollama, AI worker, models)
    ├── .venv/              # Local Python Environment
    ├── build.ps1           # Build helper script
    ├── docker-compose.yml  # Container orchestration
    ├── Dockerfile          # Python runtime environment
    └── requirements.txt    # Project dependencies
```

---

## 🏗 System Architecture

The system operates on three decoupled layers:

1.  **Ingestion Layer (FastAPI):**
    * **Role:** Acts as the secure gateway for IoT sensors.
    * **Features:**
        * Asynchronous request handling (`async/await`).
        * **Zero-Trust Security:** Enforces ECDSA (NIST256p) signature verification with SHA-256 hashing on every payload.
        * **Polyglot Crypto Support:** Handles both DER (MbedTLS/C++) and RAW (Python/JS) signature formats.
        * **O(1) enqueue:** Valid payloads are appended to a **Redis Streams** bus (`readings:stream`) instead of touching the database — the API stays fast no matter how many sensors emit.

2.  **Processing Layer (Worker):**
    * **Role:** Drains the stream via consumer groups and persists + analyzes the data.
    * **Features:**
        * **Horizontally scalable:** `docker compose scale worker=N` — Redis balances deliveries across consumers; `XAUTOCLAIM` reclaims entries left pending by crashed workers (at-least-once delivery).
        * **Batched persistence:** a stream batch (default 64 heartbeats) is committed to PostgreSQL in one transaction.
        * **Poison-message isolation:** unparseable/failing heartbeats are parked on the `readings:dlq` stream and ACKed, so they can never stall the group.
        * Triggers persistent `Alerts` when predefined thresholds are breached (Redis `SET NX` cooldown deduplication).

3.  **Persistence Layer:**
    * **TimescaleDB + PostGIS (single image):** `readings` is a TimescaleDB *hypertable* chunked on `recorded_at` (continuous aggregate `readings_minute` serves the dashboard rollups; compression + retention). PostGIS remains the authoritative source for zone geometry.
    * **Redis:** Streams for ingestion buffering, Pub/Sub for real-time alert distribution, geohash zone-index + cooldown keys for the alerting fast path.

---

## 🚀 Installation & Setup

### Prerequisites
* **Docker** & **Docker Compose**
* **Python 3.11+** (Optional, for local testing)

### 1. Environment Configuration
The system relies on environment variables. Ensure your `.env` or Docker configuration includes:

```env
DATABASE_URL=postgresql://developer:development_pass@db:5432/monitoraggio_db
REDIS_URL=redis://redis:6379/0

# --- Optional: AI Emergency Reports ---
# Enables report enqueueing from the alert engine (default: false)
AI_REPORT_ENABLED=true
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=llama3.2:1b
```

### 2. Build and Deployment
Navigate to the `api` directory and launch the stack:

```bash
cd api
docker-compose up -d --build
```

The API will be accessible at: `http://localhost:8000`

### 3. Optional — Enable AI Emergency Reports
To run the on-premise AI report pipeline (local Ollama + dedicated worker), start the stack with the `ai` profile:

```bash
cd api
docker-compose --profile ai up -d --build
```

The Ollama service auto-pulls the configured model (`OLLAMA_MODEL`, default `llama3.2:1b`) on first startup. Reports are generated entirely on the host — telemetry never leaves your machine.

### 4. API Documentation
Interactive Swagger UI is available at:
`http://localhost:8000/docs`

---

## 📡 API Endpoints Overview

### 🛠️ Registration (Admin & Setup)
Endpoints for provisioning the infrastructure.

* **POST** `/zones/` - Create a new monitoring zone.
* **POST** `/sensors/` - Register a new sensor.
    * *Note:* Requires the sensor's ECDSA Public Key (Hex format).
* **GET** `/zones/` - Retrieve available zones.
* **GET** `/sensors/` - Retrieve registered sensors.

### 📍 Geo-Location (v1.2.1)
* **GET** `/zones/locate?latitude=..&longitude=..` - Resolve a GPS fix into the smallest containing monitored zone (powers "Detect my zone").
* **GET** `/zones/{zone_id}/readings` - Fetch the most recent readings emitted by sensors of a single zone (per-zone seismograph feed).
* **DELETE** `/zones/{zone_id}/readings` - Clear the telemetry emitted by a single zone (returns `{ "deleted": n }`).

### 📥 Data Ingestion (IoT)
* **POST** `/readings/` - High-frequency ingestion endpoint.
    * **Payload:** Telemetry data including `value`, `device_timestamp`, and `signature_hex`.
    * **Security:** Rejects any payload with an invalid or missing digital signature.

### 📊 Data Retrieval & Analytics
* **GET** `/zones/{zone_id}/alerts` - Retrieve confirmed seismic alerts for a specific area.
* **GET** `/sensors/{sensor_id}/statistics` - Get aggregated metrics (Count, Avg, Max, Min) for sensor diagnostics.

### 🤖 AI Emergency Reports (v1.2.0)
* **GET** `/reports/{alert_id}` - Retrieve the AI-generated emergency report for a confirmed alert (persisted; useful after a WebSocket reconnect).

### 🟢 System
* **GET** `/health` - Detailed status check of API, Database, and Redis connectivity.

---

## ⚙️ Technical Specifications

### Cryptography & Security
The backend enforces strict cryptographic standards to prevent spoofing or replay attacks:
* **Algorithm:** ECDSA (Elliptic Curve Digital Signature Algorithm).
* **Curve:** NIST P-256 (secp256r1).
* **Hash Function:** SHA-256.
* **Format:** Accepts **DER encoded** signatures (standard for ESP32/MbedTLS) with a fallback to RAW formats.

### High-Concurrency Configuration
To handle bursts of traffic during seismic events, the database engine is optimized:
* **Pool Size:** 40 persistent connections.
* **Max Overflow:** 60 additional temporary connections (Total capacity: 100 concurrent threads).
* **Pre-Ping:** Enabled to prevent stale connection errors.

### Scaling (right-sized)
| Tier | Configuration | Sustained write rate |
| :--- | :--- | :--- |
| 150 sensors (test) | 1 worker, default settings | ~30 msg/s (1 reading / 5 s) |
| 10k sensors | `scale worker=N`, TimescaleDB hypertable | ~2k msg/s (1 Hz each) on 1 Postgres node |
| 1M sensors | + EMQX federation, Kafka/Redpanda buffer, ClickHouse analytics | beyond single-node; ports are designed, not deployed |

The TimescaleDB migration (`src/timescale.py`) is idempotent and **fails closed**: on a stock PostGIS container every step is skipped with a warning and the service keeps running on the plain relational table. Provisioning happens automatically at startup and via `python -m src.timescale`.

Load generator for capacity planning:

```bash
# 150 sensors @ 1 Hz into the stream bus (matches the CI requirement)
python scripts/load_test.py --sensors 150 --hz 1 --duration 60
# End-to-end through the FastAPI ingress
python scripts/load_test.py --sensors 150 --hz 1 --mode http --api http://localhost:8000
```

---

## 🧪 Stress Testing

A specialized end-to-end stress suite lives in `tests/stress_test.py`. It simulates a fleet of **150 sensors** (configurable via `NUM_SENSORS`) firehosing cryptographically valid MQTT telemetry, verifies end-to-end persistence, and runs active security attacks (invalid signature + replay) against the API.

**To run the test:**

1.  Ensure the Docker stack is running.
2.  Install test dependencies:
    ```bash
    pip install aiohttp ecdsa aiomqtt
    ```
3.  Execute the script:
    ```bash
    python -m tests.stress_test
    ```

**Success Criteria:**
The test should report a 100% success rate (HTTP 202 Accepted) with no signature validation errors.