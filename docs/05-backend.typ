= Backend Services & Event Processing

The QuakeGuard backend is engineered to handle massive telemetry spikes (firehosing) typical of seismic swarms[cite: 1]. To achieve this, the architecture strictly decouples data ingestion from data processing using a producer-consumer pattern mediated by Redis[cite: 1].

== API Gateway & Asynchronous Ingestion

The primary entry point is a FastAPI application running behind an ASGI server (Uvicorn) within a Docker container[cite: 1]. 
- *Rate Limiting:* To protect against Denial of Service (DoS) and buggy edge nodes, the ingestion endpoint (`/readings/`) utilizes a sliding-window rate limiter backed by Redis sorted sets (`ZADD`, `ZREMRANGEBYSCORE`), restricting traffic to 50 requests per second per IP[cite: 1].
- *Queue Offloading:* Once a payload passes the strict cryptographic validation pipeline, the API does not block to perform database writes[cite: 1]. Instead, it immediately serializes the event and pushes it to a Redis List (`seismic_events`) via an `lpush` command, returning an HTTP `202 Accepted` to the bridge in milliseconds[cite: 1].

== Background Worker & Persistence

A decoupled Python worker (`worker.py`) runs in a continuous loop, consuming the `seismic_events` queue via a blocking `brpop` operation[cite: 1].
- *Database Pooling:* The worker and the API share a heavily optimized SQLAlchemy connection pool targeting a PostgreSQL/PostGIS database[cite: 1]. The engine is configured with aggressive pooling parameters (`pool_size`, `max_overflow`) to handle high-concurrency load testing without queue exhaustion[cite: 1].
- *Atomicity:* The worker saves the raw `Reading` and evaluates the alarm logic within a single, atomic database transaction (`db.commit()`), rolling back and routing failed events to a Dead Letter Queue (`seismic_events_dlq`) in case of DB errors[cite: 1].

== Magnitude Estimation & Deduplication

For every processed event, the worker performs a physical magnitude estimation based on a MyShake-style MEMS calibration approach[cite: 1]. 
The raw Peak Ground Acceleration (PGA) is converted using the formula[cite: 1]:

$ M_"IoT" = log_10("PGA"_"calib") + b $

Where $"PGA"_"calib"$ accounts for the ADXL345 scale and hardware calibration constant (`K_CALIBRATION = 1.6`), and $b$ is an empirical offset (`B_OFFSET = 3.0`)[cite: 1].

- *Thresholding:* If the estimated magnitude reaches or exceeds the critical threshold of $4.5$, the worker triggers an `Alert` entity[cite: 1].
- *Redis Deduplication:* During a real earthquake, dozens of sensors in the same Zone will breach the threshold simultaneously. To prevent notification spam, the worker uses a Redis atomic check-and-set operation (`SET nx=True, ex=60`) keyed by `zone_id`[cite: 1]. This enforces a strict 60-second cooldown per geographic zone[cite: 1]. 
- *Outbox Pattern:* Only the first worker process that successfully acquires the Redis lock will persist the `Alert` to PostgreSQL and publish the JSON payload to the `quake_alerts` Redis Pub/Sub channel[cite: 1].