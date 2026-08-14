= Backend Services & Event Processing

The QuakeGuard backend is engineered to handle massive telemetry spikes (firehosing) typical of seismic swarms[cite: 1]. To achieve this, the architecture strictly decouples data ingestion from data processing using a producer-consumer pattern mediated by Redis[cite: 1].

== API Gateway & Asynchronous Ingestion

The primary entry point is a FastAPI application running behind an ASGI server (Uvicorn) within a Docker container[cite: 1].
- *Rate Limiting:* To protect against Denial of Service (DoS) and buggy edge nodes, the ingestion endpoint (`/readings/`) utilizes a sliding-window rate limiter backed by Redis sorted sets (`ZADD`, `ZREMRANGEBYSCORE`), restricting traffic to 50 requests per second per IP[cite: 1].
- *Queue Offloading:* Once a payload passes the strict cryptographic validation pipeline, the API does not block to perform database writes[cite: 1]. Instead, it immediately serializes the event and pushes it to the ingest stream via an `XADD` command, returning an HTTP `202 Accepted` to the bridge in milliseconds[cite: 1].

== Redis Streams Ingestion Substrate

Since v1.2.1 the telemetry queue is a Redis *Stream* (default `readings:stream`), not a plain List. Lists cannot support consumer groups, so the previous single-worker `BRPOP` design bounded scale to one process and could lose a message on a crash mid-read[cite: 1]. Streams fix both concerns:
- *Horizontal Scale:* Any number of producers `XADD` to the stream (HTTP API, MQTT bridge, ...). Any number of worker processes consume with `XREADGROUP`; Redis balances deliveries across the group, so capacity is added with `docker compose scale worker=N`[cite: 1].
- *At-Least-Once Delivery:* `XAUTOCLAIM` reclaims entries left pending by crashed consumers, so no message is lost across worker restarts[cite: 1].
- *Poisoned-Message Isolation:* Unparseable or fatally-failing messages are parked on a Dead Letter Stream (default `readings:dlq`) and acknowledged, so a poisoned heartbeat can never stall the group[cite: 1].
- *Right-Sized Backpressure:* The stream is capped with `MAXLEN ~200000` (approximate trimming); consumers read in batches of up to 64 messages with a 500ms block, and every batch is flushed in a single database transaction[cite: 1].
- *Logical Multi-Tenancy:* Every key (stream, group, DLQ, consumer prefix) is re-pointable via environment variables, so a single backend can serve multiple logical regions simply by renaming the stream[cite: 1].

== Background Worker & Persistence

A decoupled Python worker (`worker.py`) runs in a continuous loop, consuming the `readings:stream` via a blocking `XREADGROUP` and reclaiming stale pending entries with `XAUTOCLAIM`[cite: 1].
- *Database Pooling:* The worker and the API share a heavily optimized SQLAlchemy connection pool targeting a PostgreSQL database[cite: 1]. The engine is configured with aggressive pooling parameters (`pool_size`, `max_overflow`) to handle high-concurrency load testing without queue exhaustion[cite: 1].
- *Batch Atomicity:* A whole stream batch is staged in-memory and persisted with a single `db.commit()`; only cooldown locks are taken per-event (atomic Redis `SET NX`). On a database error the entire batch is routed to the DLQ rather than partially applied[cite: 1].

== TimescaleDB Hypertable

The `readings` table is provisioned as a TimescaleDB *hypertable* partitioned on `recorded_at`, so time-series chunks stay small and pruning stays efficient even under firehosing[cite: 1]. The provisioning module (`timescale.py`) applies the DDL best-effort and idempotently: if the connected image lacks the extension it fails closed with a warning, keeping the standard PostGIS image compatible for CI while production uses the unified TimescaleDB+PostGIS image[cite: 1]. On newer TimescaleDB releases (2.13+/3.x) the hypertable is additionally configured for columnstore access[cite: 1]. The `Reading` model uses a composite primary key `(id, recorded_at)` because TimescaleDB requires the partitioning column to be part of every unique key[cite: 1].

== Geographic Zoning & Zone-Scoped Data

v1.2.1 makes PostGIS zones the source of truth for the network topology[cite: 1]:
- *Zone Management:* `GET /zones` lists the monitored polygons; `POST /zones/` creates one[cite: 1].
- *Spatial Auto-Assignment:* On provisioning, `resolve_zone` maps a device's coordinates to the smallest containing polygon. It first consults a Redis fast-path index (`zoneindex:<geohash>` → set of zone ids, precision 3), and only on a cache miss or an ambiguous multi-zone match does it run the authoritative PostGIS `ST_Contains` query ordered by polygon area. The cache is purely an optimization and can never assign the wrong zone[cite: 1].
- *Zone Detection:* `GET /zones/locate?latitude=...&longitude=...` resolves an arbitrary GPS fix into its containing monitored zone (404 when outside any polygon), powering the mobile "Detect my zone" flow[cite: 1].
- *Zone-Scoped Retrieval:* `GET /zones/{zone_id}/readings` (live per-zone telemetry for the per-zone seismograph), `DELETE /zones/{zone_id}/readings` (operational purge), and `GET /zones/{zone_id}/alerts` (confirmed alerts raised for a single area)[cite: 1].

== Magnitude Estimation & Per-Area Deduplication

For every processed event, the worker performs a physical magnitude estimation based on a MyShake-style MEMS calibration approach[cite: 1].
The raw Peak Ground Acceleration (PGA) is converted using the formula[cite: 1]:

$ M_"IoT" = log_10("PGA"_"calib") + b $

Where $"PGA"_"calib"$ accounts for the ADXL345 scale and hardware calibration constant (`K_CALIBRATION = 1.6`), and $b$ is an empirical offset (`B_OFFSET = 3.0`)[cite: 1]. The same normalization is shared with the mobile client so the app and the backend report identical magnitudes[cite: 1].

- *Thresholding:* If the estimated magnitude reaches or exceeds the critical threshold of $4.5$, the worker triggers an `Alert` entity[cite: 1].
- *Per-Area Cooldown:* During a real earthquake, dozens of sensors in the same region will breach the threshold simultaneously. To prevent notification spam, the worker uses a Redis atomic check-and-set operation (`SET nx=True, ex=60`) keyed by the *area* — the reading's geohash region (precision 4, ~39 x 19 km) when coordinates are present, else the zone — enforcing a strict 60-second cooldown per geographic area rather than globally[cite: 1]. `Reading.lat/lon` are captured at ingestion precisely to enable this fragmentation and future spatial correlation[cite: 1].
- *Outbox Pattern:* Only the first worker process that successfully acquires the Redis lock will persist the `Alert` to PostgreSQL and publish the JSON payload to the `quake_alerts` Redis Pub/Sub channel[cite: 1].