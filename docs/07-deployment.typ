= Deployment & Operations Guide

This section outlines the procedures for provisioning the QuakeGuard infrastructure in a local or development environment.

== Prerequisites

To orchestrate the full stack, the host machine must have the following dependencies installed:
- *Backend:* Docker Engine and Docker Compose.
- *Edge (IoT):* Visual Studio Code with the PlatformIO IDE extension.
- *Mobile:* Node.js (v18+) and the Expo Go application installed on a physical smartphone.

== Backend Provisioning

The backend services (PostgreSQL, Redis, FastAPI, Worker, and MQTT Bridge) are fully containerized[cite: 1]. Since v1.2.1 the database image is a single unified TimescaleDB+PostGIS build (`backend/docker/postgres-timescale.Dockerfile`), so the `readings` table is provisioned as a hypertable with spatial extensions enabled in one container. The image explicitly runs as the non-root `postgres` user[cite: 1].

+ Navigate to the backend directory:
  ```bash
  cd backend
  ```
+ Clone the environment template and configure the secrets:
  ```bash
  cp .env.example .env
  ```
  _Ensure the `MQTT_BROKER`, `MQTT_USERNAME`, and `MQTT_PASSWORD` fields are correctly populated with your HiveMQ Cloud credentials._
+ Boot the infrastructure in detached mode:
  ```bash
  docker compose up --build -d
  ```
The API Gateway will be exposed at `http://localhost:8000`, with the OpenAPI Swagger documentation available at `/docs`.

== Horizontal Worker Scaling

Because telemetry is consumed through Redis Streams consumer groups, the worker tier scales horizontally without reconfiguration: messages are balanced across the group automatically[cite: 1].
```bash
docker compose up --scale worker=N -d
```

== Seismic Simulation & Stress Testing

Two companion scripts exercise the ingestion pipeline[cite: 1]:
- *`scripts/load_test.py`* — a high-concurrency End-to-End (E2E) stress test that simulates a massive seismic event through the real REST path (see the stress test section below).
- *`scripts/simulate_zone.py`* — streams synthetic per-zone readings straight through the ingestion flow, exercising the per-area cooldown fragmentation and the per-zone seismograph endpoints[cite: 1].

== Edge Node Flashing (ESP32-C3)

The firmware strictly requires compile-time secret injection to operate.

+ Navigate to the firmware directory:
  ```bash
  cd firmware
  ```
+ Clone the configuration template:
  ```bash
  cp esp32_config.env.example esp32_config.env
  ```
+ Edit `esp32_config.env` to include your local Wi-Fi credentials, the ngrok tunnel URL (or local IP) for the `SERVER_HOST`, and the `ENROLLMENT_TOKEN`.
+ Connect the ESP32-C3 via USB and trigger the PlatformIO upload sequence.
+ Open the Serial Monitor at `115200` baud. On its first boot, the device will generate its ECDSA keys, connect to the network, and automatically register with the backend.

== Mobile Client Initialization

The React Native client must point to the backend's IP address.

+ Navigate to the mobile directory and install dependencies:
  ```bash
  cd mobile
  npm install
  ```
+ Create a `.env` file in the root of the mobile project matching the backend secrets:
  ```env
  EXPO_PUBLIC_IOT_API_KEY=your_secret_key
  EXPO_PUBLIC_MOBILE_WS_TOKEN=your_ws_token
  EXPO_PUBLIC_API_BASE_URL=http://YOUR_LOCAL_IP:8000
  ```
+ Start the Expo development server:
  ```bash
  npx expo start
  ```
+ Scan the generated QR code using the Expo Go app. Both the smartphone and the backend host must be on the same Local Area Network (LAN).

== Executing the Critical Stress Test

To validate the deployment, the system includes an End-to-End (E2E) stress test that simulates a massive seismic event.

From the \`backend\` directory, execute:
```bash
export API_URL="http://localhost:8000"
export NUM_SENSORS=150
export CONCURRENCY_LIMIT=50
python -m tests.stress_test
```
A successful test will conclude with the message `🏆 SYSTEM CERTIFIED`, confirming that the rate limiter, security gates, and per-area cooldown locks are functioning nominally.