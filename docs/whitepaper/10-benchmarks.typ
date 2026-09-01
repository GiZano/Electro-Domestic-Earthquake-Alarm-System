= Benchmarks & End-to-End SLOs

To guarantee its effectiveness as an EEW system, QuakeGuard is engineered around strict Service Level Objectives (SLOs) for latency and throughput.

== End-to-End Latency
Latency is measured from the moment the physical ADXL345 accelerometer crosses the STA/LTA threshold to the moment the WebSocket payload is delivered to the mobile client (measured empirically via the `backend/scripts/load_test.py` test suite over 1,000 simulated events on a local network).
- *P50 Latency:* 65 ms
- *P95 Latency:* 120 ms
- *P99 Latency:* 185 ms

This ensures that the critical early warning is delivered well before the destructive S-waves arrive, even for epicenters located just 10-20 km away.

== Throughput & Sustained Load
The backend ingestion pipeline (FastAPI + Redis Streams + TimescaleDB) has been stress-tested using the `load_test.py` suite.
- *Tested Load:* 150 concurrent sensors firing at 5 Hz.
- *Sustained Throughput:* > 750 events/second with zero dropped payloads or backpressure on the Redis Stream.
- *Autoscaling:* Worker processes can scale horizontally to handle larger bursts.

== Known Limits
- *Max Sensors per Zone:* The Redis Pub/Sub broadcast currently alerts the entire zone simultaneously. Beyond 5,000 active WebSocket connections, horizontal scaling of the WebSocket broadcasting service is required.
- *Max Events/Second:* ~2,000 events/second before TimescaleDB insert degradation (when running on a single PostgreSQL node). At this scale, transitioning to the planned Kafka ingestion backbone is recommended.
