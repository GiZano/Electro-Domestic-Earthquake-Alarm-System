= Data Plane & Message Broker (MQTT)

With the release of v1.1.0, QuakeGuard migrated its Data Plane from a local, cleartext MQTT architecture to a robust, cloud-based infrastructure[cite: 1]. This decoupling ensures that high-frequency seismic telemetry is handled by a dedicated message broker optimized for IoT, freeing the edge nodes from the overhead of HTTP round-trips[cite: 1].

== HiveMQ Cloud Infrastructure

The core of the Data Plane is a HiveMQ Cloud Serverless broker[cite: 1].
- *Encrypted Transport:* All telemetry is transmitted over port 8883 using strict Transport Layer Security (TLS)[cite: 1].
- *Authentication:* Anonymous access (`allow_anonymous true`) has been deprecated[cite: 1]. The broker now requires explicit `MQTT_USERNAME` and `MQTT_PASSWORD` credentials for every connection[cite: 1].
- *Topic Topology:* All valid seismic anomalies are published to the unified `quakeguard/telemetry` topic[cite: 1].

== Edge Node Implementation (Firmware)

On the ESP32-C3, the `networkTask` handles the MQTT transmission asynchronously[cite: 1]. 
- To support TLS on resource-constrained hardware, the firmware utilizes `WiFiClientSecure::setInsecure()` combined with the `PubSubClient` library[cite: 1]. 
- When a `SeismicEvent` is popped from the FreeRTOS queue, the firmware packages the JSON and fires the payload to the broker[cite: 1]. This "fire-and-forget" approach reduces transmission blocking time to milliseconds, ensuring the `sensorTask` is never starved of CPU cycles[cite: 1].

== Internal MQTT Bridge Service

To securely ingest the MQTT data into the backend without exposing the FastAPI worker directly to the public internet, QuakeGuard employs a dedicated bridging microservice (`mqtt_subscriber.py`)[cite: 1].
- *Protocol Bridging:* Written in Python using the `paho.mqtt.client` (v2 API), the bridge acts as an authorized subscriber to the HiveMQ broker[cite: 1]. It initiates a secure connection using `client.tls_set(cert_reqs=ssl.CERT_REQUIRED)`[cite: 1].
- *Internal Routing:* Upon receiving a message on `quakeguard/telemetry`, the bridge wraps the payload and forwards it to the internal FastAPI ingestion endpoint (`/readings/`) via a standard HTTP POST request[cite: 1].
- *Security Injection:* The bridge injects the `X-API-Key` header into the HTTP request, acting as a trusted proxy between the external MQTT cloud and the internal Docker network[cite: 1]. If the API rejects the payload (e.g., due to an invalid cryptographic signature), the bridge logs the failure without crashing[cite: 1].