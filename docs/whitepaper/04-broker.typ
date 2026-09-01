= Data Plane & Message Broker (MQTT)

With the release of v1.1.0, QuakeGuard migrated its Data Plane from a local, cleartext MQTT architecture to a robust, cloud-based infrastructure. This decoupling ensures that high-frequency seismic telemetry is handled by a dedicated message broker optimized for IoT, freeing the edge nodes from the overhead of HTTP round-trips.

== HiveMQ Cloud Infrastructure

The core of the Data Plane is a HiveMQ Cloud Serverless broker.
- *Encrypted Transport:* All telemetry is transmitted over port 8883 using strict Transport Layer Security (TLS).
- *Authentication:* Anonymous access (`allow_anonymous true`) has been deprecated. The broker now requires explicit `MQTT_USERNAME` and `MQTT_PASSWORD` credentials for every connection.
- *Topic Topology:* All valid seismic anomalies are published to the unified `quakeguard/telemetry` topic.

== Edge Node Implementation (Firmware)

On the ESP32-C3, the `networkTask` handles the MQTT transmission asynchronously. 
- To support TLS on resource-constrained hardware, the firmware utilizes `WiFiClientSecure::setInsecure()` combined with the `PubSubClient` library. 
- When a `SeismicEvent` is popped from the FreeRTOS queue, the firmware packages the JSON and fires the payload to the broker. This "fire-and-forget" approach reduces transmission blocking time to milliseconds, ensuring the `sensorTask` is never starved of CPU cycles.

== Host Serial Bridge — Second Ingestion Path 

When MQTT is unreachable the host can collect `[QG:FB]` frames over USB CDC and forward them to the same ingestion pipeline. `firmware/tools/serial_bridge.py` tails `/dev/ttyACM0` (default `SERIAL_PORT`), filters lines starting with `[QG:FB]`, parses the JSON suffix and POSTs it to `/readings/` with `X-API-Key` — identical security gates as the MQTT bridge. URL validation (`_validate_api_url`) restricts schemes to `http/https`, rejects embedded credentials and non-alphanumeric hostnames (SSRF guard), and `parse_frame()` returns `None` on boot-log noise so the reader never crashes on malformed lines. A `dry-run` and `--stdin` mode plus the `iot-ci.yml` parser smoke test keep the bridge testable without hardware.

== Internal MQTT Bridge Service

To securely ingest the MQTT data into the backend without exposing the FastAPI worker directly to the public internet, QuakeGuard employs a dedicated bridging microservice (`mqtt_subscriber.py`).
- *Protocol Bridging:* Written in Python using the `paho.mqtt.client` (v2 API), the bridge acts as an authorized subscriber to the HiveMQ broker. It initiates a secure connection using `client.tls_set(cert_reqs=ssl.CERT_REQUIRED)`.
- *Internal Routing:* Upon receiving a message on `quakeguard/telemetry`, the bridge wraps the payload and forwards it to the internal FastAPI ingestion endpoint (`/readings/`) via a standard HTTP POST request.
- *Security Injection:* The bridge injects the `X-API-Key` header into the HTTP request, acting as a trusted proxy between the external MQTT cloud and the internal Docker network. If the API rejects the payload (e.g., due to an invalid cryptographic signature), the bridge logs the failure without crashing.