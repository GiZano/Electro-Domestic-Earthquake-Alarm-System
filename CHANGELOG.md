# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - (Target: v1.2.0)
### Added
- **On-Premise AI Emergency Reports:** New AI layer generates human-readable emergency reports from confirmed seismic alerts via a local Ollama LLM (`llama3.2:1b` default), keeping telemetry on the host.
- **`ollama_client.py`:** Deterministic report generation (`temperature 0.0`, `top_k 1`, streaming disabled) with a strict system prompt ("Only use the provided JSON telemetry. Do not invent data.") and explicit `"AI report unavailable."` fallback on failure.
- **`EmergencyReport` Model & State Machine:** `PENDING → COMPLETED | FAILED` lifecycle, persisted in PostgreSQL alongside alerts.
- **`ai_report_worker.py`:** Dedicated consumer of the `ai_report_queue`; publishes `EMERGENCY_REPORT` to the `ai_reports` Redis channel, routes failures to `ai_report_queue_dlq`, and handles graceful shutdown.
- **Worker Integration:** Alert engine now enqueues report jobs non-blocking (gated by `AI_REPORT_ENABLED`, default `false`); alert payloads carry `alert_id`.
- **`GET /reports/{alert_id}`:** REST endpoint for report retrieval after WebSocket reconnect.
- **Docker Compose `ai` profile:** `ollama` and `ai-worker` services behind a profile; `init-scripts/ollama-entrypoint.sh` auto-pulls the model on startup.
- **Mobile Report UI:** Inline AI report banner + history cards (summary + recommendations; "Report non disponibile" badge on `FAILED`), driven by the `ai_reports` WebSocket channel.
- **Unit Tests:** Coverage for the Ollama client, AI worker state machine, worker enqueue path, and EmergencyReport model (68 backend tests; mobile store tests for report handling).

### Changed
- WebSocket broadcaster subscribes to the `ai_reports` channel in addition to `quake_alerts`.
- Mobile `WebSocketContext` handles `EMERGENCY_REPORT` messages and stores the latest report; `useAlertStore` keeps a `reports` map keyed by `alert_id`.

## [1.1.0] - 2026-07-29
### Added
- **HiveMQ Cloud MQTT Integration:** Migrated from local MQTT broker to a fully managed, TLS-secured cloud broker.
- **Python MQTT Bridge (`mqtt_subscriber.py`):** New service to proxy MQTT payloads to the HTTP ingestion pipeline securely.
- **ngrok HTTPS Tunnel:** Enabled secure, remote exposure of the control plane for device registration.
- **Docs as Code:** Added modular Typst documentation (`docs/`) outlining the entire system architecture.

### Changed
- Refactored ESP32 firmware to connect to port 8883 (TLS) and authenticate via standard MQTT credentials.
- Updated Mobile React Native App to point to the new remote WebSocket endpoint.
- Hardened Redis `seismic_events` queue to handle edge-case worker disconnects.

## [1.0.0] - 2026-06-15
### Added
- Initial stable release for the Hackersgen contest.
- STA/LTA seismic detection algorithm implemented in C++ (ESP32-C3).
- FastAPI backend with PostgreSQL + PostGIS integration for sensor mapping.
- ECDSA cryptographic signing and Zero-Trust device provisioning.
- React Native Mobile App with WebSockets and native haptic alerts.
- End-to-End stress test suite (`tests/stress_test.py`).
