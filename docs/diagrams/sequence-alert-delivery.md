# Sequence Diagram — Alert Delivery (Earthquake Detection → Mobile Alert)

```mermaid
sequenceDiagram
    participant ADXL as ADXL345 Sensor
    participant ESP as ESP32-C3 Node
    participant MQTT as HiveMQ Cloud
    participant Bridge as MQTT Bridge
    participant API as FastAPI Gateway
    participant Redis as Redis
    participant Worker as Background Worker
    participant DB as PostgreSQL
    participant AI as AI Report Worker
    participant Ollama as Ollama LLM
    participant WS as WebSocket
    participant App as Mobile App
    participant User as End User

    ADXL->>ESP: Acceleration data (100 Hz, I2C)
    ESP->>ESP: HPF → STA/LTA detection
    Note over ESP: STA/LTA ratio > 1.8 → TRIGGER

    ESP->>ESP: ECDSA sign (value:timestamp)
    ESP->>MQTT: PUBLISH quakeguard/telemetry<br/>{value, sensor_id, timestamp, signature}

    MQTT->>Bridge: Deliver message (TLS)
    Bridge->>API: POST /readings/<br/>X-API-Key header

    API->>API: Validate API Key
    API->>API: Verify ECDSA signature
    API->>API: Check anti-replay (300s window)
    API->>API: Rate limit check (50 req/s/IP)

    API->>Redis: XADD readings:stream

    Worker->>Redis: XREADGROUP (batch)
    Worker->>Worker: Calculate magnitude<br/>M = log10(PGA/scale) × K + B
    Worker->>DB: INSERT INTO readings

    alt M ≥ 4.5 (Alert threshold)
        Worker->>Redis: Check cooldown lock<br/>(alert_cooldown:geohash)

        alt No active cooldown
            Worker->>DB: INSERT INTO alerts
            Worker->>Redis: SET cooldown lock (60s TTL)
            Worker->>Redis: PUBLISH quake_alerts<br/>{zone, magnitude, alert_id}

            Redis->>WS: Broadcast to subscribers
            WS->>App: QUAKE_ALERT message

            App->>App: SOS haptic vibration
            App->>App: Push notification
            App->>User: 🚨 EARTHQUAKE ALERT

            opt AI Reports enabled
                Worker->>Redis: LPUSH ai_report_queue
                AI->>Redis: BRPOP ai_report_queue
                AI->>Ollama: POST /api/generate<br/>(structured prompt + telemetry)
                Ollama-->>AI: Emergency report text
                AI->>DB: UPDATE EmergencyReport (COMPLETED)
                AI->>Redis: PUBLISH ai_reports
                Redis->>WS: Broadcast report
                WS->>App: EMERGENCY_REPORT message
                App->>User: 📋 AI Report banner
            end

        else Cooldown active
            Note over Worker: Duplicate suppressed (60s window)
        end
    end
```
