<div align="center">

# 🌋 QuakeGuard
### Electro-Domestic Seismic Alarm System

**Full-Stack IoT Architecture for Real-Time Earthquake Detection**

![Version](https://img.shields.io/badge/Version-1.1.0-red?style=for-the-badge)
![License](https://img.shields.io/badge/License-AGPL--3.0-blue?style=for-the-badge)
![C++](https://img.shields.io/badge/C++-Hardware_Logic-00599C?style=for-the-badge&logo=c%2B%2B&logoColor=white)
![Python](https://img.shields.io/badge/Python-FastAPI-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![React Native](https://img.shields.io/badge/React_Native-Mobile-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-PostGIS-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-Message_Broker-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Containerization-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![HiveMQ](https://img.shields.io/badge/HiveMQ-Cloud_MQTT-FFC107?style=for-the-badge&logo=mqtt&logoColor=black)
![ngrok](https://img.shields.io/badge/ngrok-HTTPS_Tunnel-1F1E37?style=for-the-badge&logo=ngrok&logoColor=white)

![CI Backend](https://github.com/GiZano/QuakeGuard/actions/workflows/backend-ci.yml/badge.svg)
![CI Frontend](https://github.com/GiZano/QuakeGuard/actions/workflows/frontend-ci.yml/badge.svg)
![CI IoT](https://github.com/GiZano/QuakeGuard/actions/workflows/iot-ci.yml/badge.svg)
[![Quality gate status](https://sonarcloud.io/api/project_badges/measure?project=GiZano_QuakeGuard&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=GiZano_QuakeGuard)

> 📚 **Technical Specification:** A comprehensive architecture whitepaper is available in the `docs/` directory, compiled via Typst.

![QuakeGuard Logo](docs/assets/logo/png/github-banner.png)


</div>

---

## 📖 Overview

**QuakeGuard** is a full-stack IoT architecture for real-time detection, analysis, and reporting of seismic events. The system transforms everyday household appliances — washing machines, TVs, refrigerators — into a distributed seismic sensor network, each node capable of detecting and reporting earthquake activity autonomously.

Intelligent edge sensors (ESP32-C3 + ADXL345) analyze vibrations locally using professional-grade algorithms and transmit cryptographically signed data to an asynchronous cloud backend. The backend is engineered to handle the massive traffic spikes — the **Thundering Herd** effect — typical during widespread seismic events, ensuring reliable alarm delivery without bottlenecking. A React Native mobile app receives real-time haptic and visual alerts via WebSocket.

> 🎓 Developed as a school contest project for **Hackersgen** by Sorint.lab and the **GF Marilli** competition.

---

## 🏗️ System Architecture

```
ESP32-C3 + ADXL345
       │
       │  MQTT (signed payload)
       ▼
MQTT Bridge ──► POST /readings/ ──► ECDSA Verification
                                              │
                                              ▼
                                        Redis Queue
                                              │
                                              ▼
                                     Background Worker
                                      │           │
                                      ▼           ▼
                               PostgreSQL    Redis Pub/Sub
                               + PostGIS          │
                                                  ▼
                                           WebSocket Broadcast
                                                  │
                                                  ▼
                                        React Native Mobile App
                                        (Haptic + Visual Alert)
```

The project follows **Microservices** and **Event-Driven Design** principles across three fully independent layers.

---

## 📡 IoT Edge (`firmware/`)

| Feature | Detail |
|---------|--------|
| Hardware | ESP32-C3 SuperMini + ADXL345 Accelerometer |
| Sampling Rate | 100 Hz |
| Detection Algorithm | STA/LTA (Short Term / Long Term Average) |
| Signal Processing | Digital High-Pass Filter (HPF) to remove gravity |
| Data Structure | Statically allocated Ring Buffers (`RingBuffer<100>` STA, `RingBuffer<1000>` LTA) |
| Security | ECDSA NIST256p cryptographic signing on every payload |
| Transmission | MQTT publish to `quakeguard/telemetry` |
| Provisioning | Automated device handshake on first boot via `POST /devices/register` |
| Secret Injection | Compile-time `ENROLLMENT_TOKEN` via PlatformIO pre-script + `#error` fail-fast |

---

## ☁️ Backend (`backend/`)

| Feature | Detail |
|---------|--------|
| Framework | FastAPI (Python 3.11), fully async |
| Security | API Key auth, ECDSA signature verification, Anti-Replay (60s window) |
| Message Broker | Redis — decouples ingestion from processing |
| Rate Limiting | Fixed-window 50 req/s per IP via Redis |
| Alert Engine | ML-like magnitude proxy (`M = log10(PGA_calib) + b`), threshold M ≥ 4.5 |
| Deduplication | Redis TTL cooldown lock per zone (60s), prevents alert storms |
| Persistence | PostgreSQL + PostGIS with `recorded_at` timestamps |
| Zone Assignment | Automatic via PostGIS `ST_Contains` spatial query, ordered by `ST_Area` ascending |
| Zone Seeding | 8 pre-populated global macro-regions + "Unknown Region" fallback |
| Observability | `GET /health` — concurrent PostgreSQL + Redis ping |
| Secrets | Fail-fast `RuntimeError` on missing env vars at startup |
| MQTT Bridge | `mqtt_subscriber.py` — forwards MQTT payloads to the secure HTTP pipeline |

---

## 📱 Frontend (`mobile/`)

| Feature | Detail |
|---------|--------|
| Framework | React Native (Expo) with TypeScript |
| Navigation | Expo Router — 3-tab Bottom Navigator (Monitor, Sensors Map, Settings) |
| State Management | Zustand slices (`usePreferencesStore`, `useAlertStore`) |
| Server State | TanStack Query + Axios — caching, background refetch, retry |
| Real-Time | WebSocket context with exponential backoff reconnection |
| Alert Delivery | SOS haptic vibration pattern + OS push notification via `expo-notifications` |
| Alert History | In-session feed of last 10 critical events |
| Offline Mode | Toggle silences WebSocket, halts all TanStack Query polling |
| Notifications | `notificationsEnabled` toggle gates haptics and push notifications |
| Safe Areas | `react-native-safe-area-context` — Dynamic Island and punch-hole compatible |

---

## 🔐 Security Model

Data integrity is paramount in an emergency system. Every telemetry packet is cryptographically secured end-to-end.

```
ESP32 signs payload with ECDSA NIST256p (SHA256)
         ↓
Backend verifies signature against registered public key
         ↓
Timestamp validated within 60-second window (Anti-Replay)
         ↓
API Key checked on every request (X-API-Key header)
         ↓
Payload accepted → Redis Queue
```

**Threat model coverage:**
- ✅ Man-in-the-Middle (MitM) — ECDSA signature verification
- ✅ Spoofing — public key registration + signature check
- ✅ Replay attacks — 60-second timestamp window
- ✅ Brute force — rate limiting 50 req/s per IP
- ✅ Unauthorized access — API Key + enrollment token fail-fast

---

## 🚀 Quick Start

### Prerequisites

- Docker Desktop & Docker Compose
- PlatformIO (VS Code Extension)
- Node.js 18+ & Expo Go (mobile)
- A mobile hotspot or shared WiFi network for ESP32 + backend connectivity

### 1. Configure Environment Variables

```bash
cd backend
cp .env.example .env
```

Edit `.env` and set the required secrets:

```env
# --- Application Secrets ---
IOT_API_KEY=your_secret_key
MOBILE_WS_TOKEN=your_ws_token
ENROLLMENT_TOKEN=your_enrollment_token

# --- Database ---
POSTGRES_DB=quakeguard_db
POSTGRES_USER=developer
POSTGRES_PASSWORD=your_db_password
API_PORT=8000

# --- Cloud MQTT (HiveMQ) ---
MQTT_BROKER=your-cluster-id.s1.eu.hivemq.cloud
MQTT_PORT=8883
MQTT_USERNAME=your_mqtt_username
MQTT_PASSWORD=your_mqtt_password
```

> ⚠️ The backend will refuse to start if any of these are missing — this is intentional fail-fast behavior.

### 2. Launch the Backend Stack

```bash
cd backend
docker compose up --build -d
```

| Endpoint | URL |
|----------|-----|
| API | `http://localhost:8000` |
| Swagger UI | `http://localhost:8000/docs` |
| Health Check | `http://localhost:8000/health` |

### 3. Configure and Flash the IoT Firmware

```bash
cd firmware
cp esp32_config.env.example esp32_config.env
# Edit esp32_config.env with your network IP and ENROLLMENT_TOKEN
```

Flash via PlatformIO. On first boot the device will:
1. Open a WiFi captive portal (`QuakeGuard-Setup`)
2. Connect to your network
3. Automatically register with the backend and receive a `sensor_id`

> 💡 If the sensor registers with `latitude=0.0, longitude=0.0` it will be assigned to "Unknown Region". Hardcode your coordinates in `main.cpp` for correct zone assignment until GPS integration is complete.

### 4. Launch the Mobile App

```bash
cd mobile
npm install
```

Update `constants/config.ts` with your machine's local IP:

```typescript
export const API_BASE_URL = "http://YOUR_LOCAL_IP:8000";
```

Create `.env` in the mobile root:

```env
EXPO_PUBLIC_IOT_API_KEY=your_secret_key
EXPO_PUBLIC_MOBILE_WS_TOKEN=your_ws_token
```

```bash
npx expo start
```

Scan the QR code with Expo Go. Ensure your phone is on the **same WiFi network** as the backend machine.

---

## 🧪 Stress Test

Validates the full pipeline: ingestion → Redis → worker → PostGIS → WebSocket alerts.

```bash
cd backend
export API_URL="http://localhost:8000"
export NUM_SENSORS=150
export CONCURRENCY_LIMIT=50
python -m tests.stress_test
```

**Three phases:**

| Phase | What it tests |
|-------|--------------|
| 🔥 Phase 1 — Firehose | 150 concurrent sensors, rate limiter validation |
| ⚔️ Phase 2 — Security | Bad signature blocked (401), Replay attack blocked (403) |
| 🔍 Phase 3 — E2E | DB persistence verified via polling `GET /sensors/{id}/statistics` |

A successful run ends with `🏆 SYSTEM CERTIFIED`.

---

## 🎮 Demo Mode

Trigger a simulated earthquake instantly from Swagger UI without running the stress test:

```
POST /demo/trigger-earthquake
```

Default payload (works with empty `{}`):
```json
{
  "zone_id": 1,
  "magnitude": 7.5,
  "message": "Simulated Critical Event"
}
```

This publishes directly to the Redis `quake_alerts` channel, bypassing the IoT pipeline entirely and triggering the mobile app alert UI within milliseconds.

---

## 🗺️ Geographic Zones

The database is pre-seeded with 8 global macro-regions. Sensors are automatically assigned to the correct zone via PostGIS spatial query at registration time.

| Zone | Coverage |
|------|----------|
| Italy - North | Lombardy, Veneto, Piedmont |
| Italy - Center | Tuscany, Lazio, Umbria |
| Italy - South & Islands | Campania, Sicily, Sardinia |
| Western Europe | France, Spain, Germany, UK |
| North America | USA, Canada, Mexico |
| South America | Brazil, Argentina, Chile |
| East Asia | China, Japan, India |
| Unknown Region | Fallback for unmapped coordinates |

---

## 🔄 CI/CD Pipeline

| Workflow | Trigger | Checks |
|----------|---------|--------|
| `backend-ci.yml` | `backend/**` | Bandit, Safety, stress test |
| `frontend-ci.yml` | `mobile/**` | ESLint, npm audit |
| `iot-ci.yml` | `firmware/**` | PlatformIO compilation |
| `pr-lint.yml` | All PRs | Semantic PR title (`type(scope): message`) |
| `devops-ci.yml` | `.github/workflows/**` | Actionlint workflow validation |

---

## 🗂️ Project Structure

```
QuakeGuard/
├── backend/
│   ├── src/
│   │   ├── main.py              # FastAPI gateway + REST endpoints
│   │   ├── security.py          # ECDSA, API Key, Anti-Replay
│   │   ├── worker.py            # Redis consumer + magnitude + alert engine
│   │   ├── mqtt_subscriber.py   # MQTT to HTTP bridge
│   │   ├── seed.py              # Geographic zone seeder
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   └── database.py          # DB engine and session factory
│   ├── tests/
│   │   └── stress_test.py       # Critical E2E stress test suite
│   ├── init-scripts/
│   ├── build.ps1                # Automatic container publish
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── mosquitto.conf
│   ├── requirements.txt         # Python requirements for backend development
│   └── .env.example
├── mobile/
│   ├── app/                         # Expo Router screens
│   │   └── (tabs)/
│   │       ├── index.tsx            # Monitor / Dashboard
│   │       ├── map.tsx              # Sensor Network Map
│   │       └── settings.tsx         # User Preferences
│   ├── api/                         # Axios client + TanStack Query hooks
│   ├── components/                  # Shared UI components
│   ├── store/                       # Zustand state slices
│   ├── context/
│   │   └── WebSocketContext.tsx     # Real-time alert context
│   └── constants/
│       └── config.ts                # Centralized configuration
├── firmware/
│   ├── src/
│   │   ├── main.cpp             # FreeRTOS tasks, STA/LTA, MQTT, provisioning
│   │   └── RingBuffer.h         # Statically allocated circular buffer
│   ├── test/                    # Test scripts to insert into the ESP32
│   ├── key-generator/           # ECDSA key generator for backend testing
│   ├── esp32_config.env.example
│   ├── extra_script.py          # ENV variables injector
│   └── platformio.ini
└── docs/                            # Technical Documentation
    ├── main.typ                     # Typst Whitepaper Entrypoint
    ├── 01-architecture.typ          # System Architecture & Overview
    ├── 02-hardware.typ              # Hardware & Edge Computing (ESP32-C3)
    ├── 03-security.typ              # Cryptographic Security & Provisioning
    ├── 04-broker.typ                # Data Plane & Message Broker (MQTT)
    ├── 05-backend.typ               # Backend Services & Event Processing
    └── 06-mobile.typ                # Mobile Client & Live Telemetry
```

---

## 🔮 Roadmap

| Version | Focus |
|---------|-------|
| **v1.0** | ✅ Released — edge seismic detection on ESP32, local alerts |
| **v1.1** | ✅ Current — HiveMQ Cloud MQTT (TLS), ngrok HTTPS tunnel, security hardening |
| **v1.2** | AI Cloud — LLM backend for emergency report generation from MQTT telemetry |
| **v1.3** | GNSS sync — accurate node timestamps, GPS coordinate resolution, ADXL345 calibration |
| **v2.0** | Triangulation — multi-node spatial correlation + AI reports for epicenter calculation |

---

## 📄 License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.
See the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Developed by [GiZano](https://giovanni-zanotti.is-a.dev) and [riccardo0731](https://riccardo0731.github.io)**
<br>
*Open Source — AGPL-3.0 License*
<br><br>

</div>