<div align="center">

# 🌋 QuakeGuard 
### Electro-Domestic Seismic Alarm System

**Full-Stack IoT Architecture for Real-Time Earthquake Detection**

![License](https://img.shields.io/badge/License-AGPL--3.0-blue?style=for-the-badge)
![C++](https://img.shields.io/badge/C++-Hardware_Logic-00599C?style=for-the-badge&logo=c%2B%2B&logoColor=white)
![Python](https://img.shields.io/badge/Python-FastAPI-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![React Native](https://img.shields.io/badge/React_Native-Mobile-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-PostGIS-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-Message_Broker-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Containerization-2496ED?style=for-the-badge&logo=docker&logoColor=white)

![QuakeGuard Logo](docs/assets/logo/png/github-banner.png)

*Version 0.9.0 (Release Candidate)*

</div>

---

## 📖 Overview
**QuakeGuard** is a Full-Stack IoT architecture for real-time detection, analysis, and reporting of seismic events.

The system uses intelligent edge sensors (ESP32-C3) that analyze vibrations locally and transmit cryptographically secured data to an asynchronous cloud backend. The backend is engineered to handle the massive traffic spikes (**Thundering Herd** effect) typical during widespread earthquake events, ensuring reliable alarm delivery without bottlenecking. A React Native mobile app receives real-time haptic and visual alerts via WebSocket.

---

## 🏗️ System Architecture

The project is highly modular, following **Microservices** and **Event-Driven Design** principles across three main layers:

### 1. 📡 IoT Edge (`iot-data-harvester/`)
* **Hardware:** ESP32-C3 SuperMini paired with an ADXL345 Accelerometer.
* **Edge Computing:** 100Hz sampling rate, applying Digital High-Pass Filters (HPF) and the **STA/LTA** (Short Term/Long Term Average) seismic algorithm directly on the device.
* **Security:** Hardware-level digital signing of payloads using **ECDSA (NIST256p)**.
* **Resilience:** Temporal timestamp reconstruction to mitigate network latency and out-of-order packet delivery.

### 2. ☁️ Backend (`backend-data-elaborator/`)
* **Core API:** Built with **FastAPI** (Python 3.11) for high-performance asynchronous routing.
* **Security Layer:** Dedicated `src/security.py` module enforcing API Key authentication, ECDSA signature verification, and Anti-Replay timestamp validation on every IoT payload.
* **Event Pattern:** Producer-Consumer architecture leveraging **Redis** as a Message Broker to decouple ingestion from processing. Includes a fixed-window Rate Limiter (50 req/s per IP).
* **Real-Time Alerts:** Redis Pub/Sub listener broadcasts CRITICAL seismic alerts to all connected mobile clients via WebSocket.
* **Persistence:** **PostgreSQL + PostGIS** for robust geospatial data management.
* **Observability:** `GET /health` endpoint for Docker/Kubernetes liveness probing, concurrently pinging both PostgreSQL and Redis.
* **Performance:** Fully asynchronous architecture stress-tested at >500 Req/s with 150 concurrent sensors.

### 3. 📱 Frontend (`frontend-mobile-app/`)
* **Framework:** **React Native** (Expo) with TypeScript for cross-platform compatibility.
* **Architecture:** Zustand for client-side state management, TanStack Query + Axios for server-state caching and background refetching.
* **Real-Time:** WebSocket context with exponential backoff reconnection, delivering live visual and haptic (SOS pattern) seismic alerts.
* **Navigation:** Expo Router file-based routing with a 3-tab Bottom Navigator (Monitor, Sensors Map, Settings).

---

## 🔐 Security & Cryptography

Data integrity is paramount in emergency systems. Every telemetry packet transmitted by the edge sensors is cryptographically signed.

```json
{ 
  "value": 250, 
  "timestamp": 17000000, 
  "signature": "a1b2c3d4e5f6..." 
}
```

The backend verifies the signature (**SHA256 + ECDSA**) against the sensor's registered public key before accepting any payload. This strictly prevents **Man-in-the-Middle (MitM)** and **Spoofing** attacks, ensuring alarms cannot be falsely triggered by malicious actors. Replay attacks are blocked via a 60-second timestamp validation window.

---

## 🚀 Quick Start (Local Deployment)

### Prerequisites
* Docker & Docker Compose
* PlatformIO (VS Code Extension)
* Node.js 18+ & Expo Go (mobile app)

### 1. Configure Environment Variables
Before launching, set the required secrets:
```bash
cd backend-data-elaborator/api
cp .env.example .env
# Edit .env with your own IOT_API_KEY and MOBILE_WS_TOKEN
```

### 2. Launch the Cloud Backend
```bash
cd backend-data-elaborator/api
docker compose up --build -d
```
The backend will be live at `http://localhost:8000`.
API documentation is auto-generated at `http://localhost:8000/docs`.
Health status is available at `http://localhost:8000/health`.

### 3. Configure and Flash the IoT Edge Device
1. Edit `iot-data-harvester/esp32_config.env` with your local network IP and WiFi credentials.
2. Flash the firmware to the ESP32-C3 via PlatformIO.
3. **⚠️ IMPORTANT:** On first boot, copy the generated `PUBLIC KEY` from the serial monitor and register the device via the Swagger UI at `http://localhost:8000/docs`.

### 4. Launch the Mobile App
```bash
cd frontend-mobile-app
npm install
npx expo start
```
Scan the QR code with Expo Go. Ensure your phone is on the **same WiFi network** as the backend machine.

---

## 🧪 Running the Stress Test

To validate the full backend pipeline (ingestion → Redis → worker → PostGIS → WebSocket alerts):

```bash
cd backend-data-elaborator/api
export API_URL="http://localhost:8000"
export NUM_SENSORS=150
export CONCURRENCY_LIMIT=50
python -m tests.stress_test
```

A successful run ends with `🏆 SYSTEM CERTIFIED`, confirming all three phases: load handling, security attack blocking, and E2E database persistence.

---

## 🗂️ Project Structure

```
QuakeGuard/
├── backend-data-elaborator/
│   └── api/
│       ├── src/
│       │   ├── main.py          # FastAPI gateway
│       │   ├── security.py      # ECDSA, API Key, Anti-Replay
│       │   ├── worker.py        # Redis consumer + alert engine
│       │   ├── models.py        # SQLAlchemy models
│       │   ├── schemas.py       # Pydantic schemas
│       │   └── database.py      # DB engine and session
│       ├── tests/
│       │   └── stress_test.py   # Critical E2E stress test
│       └── docker-compose.yml
├── frontend-mobile-app/
│   ├── app/                     # Expo Router screens
│   ├── src/
│   │   ├── api/                 # Axios client + TanStack Query hooks
│   │   └── store/               # Zustand state slices
│   └── context/
│       └── WebSocketContext.tsx # Real-time alert context
└── iot-data-harvester/
    └── src/                     # ESP32-C3 C++ firmware
```

---

<div align="center">

**Developed by [GiZano](https://giovanni-zanotti.is-a.dev)**
<br>
*Open Source — AGPL-3.0 License*

</div>
