# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - (Target: v1.2.0)
### Added
- Groundwork for AI-generated emergency reports via LLM integration.

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
