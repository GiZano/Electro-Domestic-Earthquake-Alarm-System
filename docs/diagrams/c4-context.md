# C4 Context Diagram — QuakeGuard

> Level 1 (System Context): shows the QuakeGuard system and the external actors/systems that interact with it.

```mermaid
C4Context
    title QuakeGuard — System Context Diagram

    Person(user, "End User", "Receives earthquake alerts on mobile device")
    Person(maintainer, "Maintainer", "Deploys, configures, and monitors the system")

    System(quakeguard, "QuakeGuard System", "Distributed IoT EEW platform: edge sensors, backend, mobile app")

    System_Ext(hivemq, "HiveMQ Cloud", "Managed MQTT broker (TLS, port 8883)")
    System_Ext(ollama, "Ollama (Host)", "Local LLM inference engine (Llama 3.2)")
    System_Ext(cloudflare, "Cloudflare Tunnel", "HTTPS tunnel for remote control plane access")
    System_Ext(expo, "Expo Push Service", "Delivers push notifications to iOS/Android")

    Rel(user, quakeguard, "Receives alerts, views sensor map", "WebSocket / Push Notification")
    Rel(maintainer, quakeguard, "Deploys stack, flashes firmware", "Docker / PlatformIO / SSH")
    Rel(quakeguard, hivemq, "Publishes/subscribes telemetry", "MQTT over TLS")
    Rel(quakeguard, ollama, "Requests AI emergency reports", "HTTP (localhost)")
    Rel(quakeguard, cloudflare, "Exposes control plane", "HTTPS tunnel")
    Rel(quakeguard, expo, "Sends push notifications", "HTTPS")
```

## Container-Level Breakdown

```mermaid
C4Container
    title QuakeGuard — Container Diagram

    Person(user, "End User")

    System_Boundary(edge, "IoT Edge Layer") {
        Container(esp32, "ESP32-C3 Node", "C++/FreeRTOS", "STA/LTA detection, ECDSA signing, MQTT publish")
        Container(adxl, "ADXL345", "I2C Sensor", "3-axis accelerometer @ 100 Hz")
        Container(gnss, "NEO-6M GNSS", "UART", "GPS coordinates + PPS time sync")
    }

    System_Boundary(backend, "Backend Layer (Docker)") {
        Container(api, "FastAPI Gateway", "Python 3.11", "REST API, ECDSA verification, WebSocket")
        Container(worker, "Background Worker", "Python", "Magnitude calc, alert engine, triangulation")
        Container(ai_worker, "AI Report Worker", "Python", "Consumes ai_report_queue, generates reports via Ollama")
        Container(mqtt_bridge, "MQTT Bridge", "Python/Paho", "Subscribes to HiveMQ, forwards to HTTP pipeline")
        ContainerDb(postgres, "PostgreSQL + PostGIS", "TimescaleDB", "Sensors, readings, zones, alerts")
        ContainerDb(redis, "Redis", "Streams + Pub/Sub", "Ingestion queue, alert broadcast, zone cache")
    }

    System_Boundary(mobile, "Mobile Layer") {
        Container(app, "React Native App", "Expo/TypeScript", "Dashboard, sensor map, alert feed")
    }

    System_Ext(hivemq, "HiveMQ Cloud")
    System_Ext(ollama, "Ollama (Host)")

    Rel(esp32, hivemq, "MQTT publish", "TLS 8883")
    Rel(mqtt_bridge, hivemq, "MQTT subscribe", "TLS 8883")
    Rel(mqtt_bridge, api, "POST /readings/", "HTTP")
    Rel(esp32, api, "POST /devices/register", "HTTP/HTTPS")
    Rel(api, redis, "XADD readings:stream")
    Rel(worker, redis, "XREADGROUP")
    Rel(worker, postgres, "INSERT readings, alerts")
    Rel(worker, redis, "PUBLISH quake_alerts")
    Rel(ai_worker, redis, "BRPOP ai_report_queue")
    Rel(ai_worker, ollama, "POST /api/generate", "HTTP")
    Rel(ai_worker, redis, "PUBLISH ai_reports")
    Rel(api, app, "WebSocket broadcast", "WSS")
    Rel(app, api, "REST queries", "HTTPS")
    Rel(user, app, "Views alerts")
    Rel(adxl, esp32, "I2C data")
    Rel(gnss, esp32, "UART + PPS")
```
