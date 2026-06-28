// =============================================================================
// QuakeGuard — Technical Documentation (English)
// =============================================================================

#set page(
  paper: "a4",
  margin: (top: 2cm, bottom: 2cm, left: 2.5cm, right: 2.5cm),
  numbering: "1",
)
#set text(font: ("DejaVu Serif"), size: 11pt)
#set heading(numbering: "1.1")
#set par(justify: true, leading: 0.65em)

// =============================================================================
// PACKAGES
// =============================================================================
#import "@preview/fletcher:0.5.8": diagram, node, edge

// =============================================================================
// COLORS
// =============================================================================
#let color-primary = rgb("#dc2626")
#let color-secondary = rgb("#1f2937")
#let color-accent = rgb("#4f46e5")
#let color-green = rgb("#16a34a")
#let color-muted = rgb("#6b7280")
#let color-light = rgb("#f3f4f6")

// =============================================================================
// HELPERS
// =============================================================================
#let highlight(content) = {
  rect(
    fill: rgb("#fef2f2"),
    stroke: color-primary + 1pt,
    inset: 8pt,
    radius: 4pt,
    content,
  )
}

#let techstack(content) = {
  grid(
    columns: (1fr,),
    gutter: 4pt,
    rect(
      fill: color-light,
      stroke: rgb("#e5e7eb") + 0.5pt,
      inset: 10pt,
      radius: 4pt,
      content,
    ),
  )
}

// =============================================================================
// TITLE PAGE
// =============================================================================
#align(center + top, [
  #block(height: 2cm)
  #text(size: 16pt, weight: "light", fill: color-muted)[Electro-Domestic Seismic Alarm System]
  #block(height: 5mm)
  #text(size: 36pt, weight: "bold", fill: color-primary)[QuakeGuard]
  #block(height: 5mm)
  #text(size: 14pt, fill: color-secondary)[Technical Documentation]
  #block(height: 3mm)
  #text(size: 10pt, fill: color-muted)[v1.0.0 — June 2026]
  #block(height: 1.5cm)
  #line(length: 40%, stroke: color-primary + 1.5pt)
  #block(height: 1cm)
  #text(size: 10pt, fill: color-muted)[
    *Authors:* Giovanni Zanotti (\@GiZano), Riccardo (\@riccardo0731) \
    *License:* GNU Affero General Public License v3.0 \
    *Repository:* #text(fill: color-accent)[github.com/GiZano/QuakeGuard]
  ]
])

#pagebreak()

// =============================================================================
// TABLE OF CONTENTS
// =============================================================================
#outline(indent: auto, title: [
  #text(size: 20pt, weight: "bold", fill: color-secondary)[Table of Contents]
])

#pagebreak()

// =============================================================================
// 1 — INTRODUCTION
// =============================================================================
= Introduction

== Overview

*QuakeGuard* is a full-stack IoT architecture for real-time detection,
analysis, and reporting of seismic events. The system transforms everyday
household appliances — washing machines, TVs, refrigerators — into a distributed
seismic sensor network, each node capable of detecting and reporting earthquake
activity autonomously.

Intelligent edge sensors (ESP32-C3 + ADXL345) analyze vibrations locally using
professional-grade algorithms and transmit cryptographically signed data to an
asynchronous cloud backend. The backend is engineered to handle the massive
traffic spikes — the *Thundering Herd* effect — typical during widespread
seismic events, ensuring reliable alarm delivery without bottlenecking. A React
Native mobile app receives real-time haptic and visual alerts via WebSocket.

#highlight[
  *Context:* Developed as a school contest project for *Hackersgen* by
  Sorint.lab and the *GF Marilli* competition.
]

== Architectural Principles

The system follows:

- *Microservices:* Three fully independent layers (IoT, Backend, Frontend)
- *Event-Driven Design:* Redis as message broker decouples ingestion,
  processing, and notification
- *Zero-Trust Security:* Every payload is ECDSA NIST256p signed, verified
  by the backend, with anti-replay protection
- *Fail-Fast:* Missing environment variables halt startup with clear
  error messages

#pagebreak()

// =============================================================================
// 2 — SYSTEM ARCHITECTURE
// =============================================================================
= System Architecture

== Architectural Diagram

#align(center, table(
  columns: (auto, auto, auto, auto, auto),
  stroke: 0.5pt + rgb("#e5e7eb"),
  [*Layer*], [*Component*], [*Technology*], [*Flow*], [*Protocol*],
  [1 -- IoT], [Edge Sensors], [ESP32-C3 + ADXL345], [Vibration sensing], [GPIO / I²C],
  [], [Firmware], [STA/LTA], [Local processing], [],
  [], [Signature], [ECDSA NIST256p], [Payload signing], [],
  [2 -- Messaging], [Message Broker], [Mosquitto MQTT], [IoT → Cloud], [MQTT],
  [3 -- Backend], [API Gateway], [FastAPI + Redis], [Receive & validate], [HTTPS],
  [], [Validation], [ECDSA Anti-Replay], [Signature verification], [],
  [], [Queue], [Redis Queue], [Async buffering], [LPUSH / BRPOP],
  [4 -- Processing], [Worker], [Python Background], [Data analysis], [],
  [5 -- Storage], [Database], [PostgreSQL + PostGIS], [Persistence], [SQL],
  [6 -- Notifications], [WebSocket Server], [FastAPI WS], [Real-time broadcast], [WS / WSS],
  [7 -- Mobile], [App], [React Native (Expo)], [Alert display], [WebSocket],
  [], [Demo Route], [/demo/trigger-earthquake], [Earthquake simulation], [HTTP POST],
))

== End-to-End Data Flow

#diagram(
  node((0, 0), [ESP32\nADXL345], radius: 1.2cm, stroke: color-primary),
  edge("-|>", stroke: color-primary),
  node((3, 0), [Mosquitto], radius: 1.2cm, stroke: color-accent),
  edge("-|>"),
  node((6, 0), [FastAPI], radius: 1.2cm, stroke: color-green),
  edge("-|>"),
  node((9, 0), [Redis\nQueue], radius: 1.2cm, stroke: rgb("#d97706")),
  edge("-|>"),
  node((12, 0), [Worker], radius: 1.2cm, stroke: rgb("#d97706")),
  edge("-|>"),
  node((15, 0), [PostGIS], radius: 1.2cm, stroke: rgb("#7c3aed")),
  edge((12, -1.5), "-|>", label: text(size: 7pt)[Pub/Sub]),
  edge("-|>"),
  node((12, -3), [WebSocket], radius: 1.2cm, stroke: rgb("#db2777")),
  edge("-|>"),
  node((12, -6), [Mobile\nApp], radius: 1.2cm, stroke: rgb("#0d9488")),
)

#pagebreak()

// =============================================================================
// 3 — SYSTEM COMPONENTS
// =============================================================================
= System Components

== 3.1 IoT Edge

=== Hardware Specifications

#table(
  columns: (4cm, auto),
  stroke: 0.5pt + rgb("#e5e7eb"),
  [*Specification*], [*Detail*],
  [Microcontroller], [ESP32-C3 SuperMini (RISC-V 32-bit, 160MHz)],
  [Sensor], [ADXL345 Digital Accelerometer (MEMS, I2C)],
  [Range], [±2G, ±4G, ±8G, ±16G (configurable)],
  [Sample Rate], [100 Hz (fixed)],
  [SDA Pin], [GPIO 7],
  [SCL Pin], [GPIO 8],
)

=== Firmware (v3.3.0-PROV-REFACTORED)

The firmware implements a FreeRTOS dual-task architecture:

*Task 1 — SensorTask (Priority 5, Stack 8KB)*
#techstack[
  - ADXL345 acquisition at 100 Hz
  - HPF (High-Pass Filter, $alpha = 0.9$) to remove gravity
  - STA/LTA calculation with circular buffers
  - Trigger detection when ratio $>= 1.8$ and signal $> "0.04 G"$
]

*Task 2 — NetworkTask (Priority 1, Stack 8KB)*
#techstack[
  - MQTT connection to Mosquitto broker
  - NTP synchronization (pool.ntp.org)
  - ECDSA payload signing
  - Publish to topic `quakeguard/telemetry`
]

=== STA/LTA Detection Algorithm

The STA/LTA (Short Term Average / Long Term Average) algorithm is the core
of the detection system:

$ "STA" = "1s sliding window (100 samples)" $

$ "LTA" = "10s sliding window (1000 samples)" $

$ "Ratio" = "STA" / "LTA" $

$ "Trigger when Ratio" >= 1.8 " and STA > " 0.04 G $

#techstack[
  *Noise Gate:* Signals below 0.04G are zeroed to prevent false positives \
  from electrical noise.\
  *HPF:* High-Pass Filter with $alpha = 0.9$ removes the DC component (gravity).\
  *Dropout Protection:* 0G frames are automatically discarded.
]

=== Security Subsystem

The firmware uses MbedTLS for cryptography:

#techstack[
  - *ECDSA NIST256p (secp256r1):* Key generation on first boot
  - *Storage:* NVS (Non-Volatile Storage) partition
  - *Signing:* SHA-256 of formatted payload `"value:timestamp"`
  - *NTP:* Time synchronization for anti-replay
]

=== Automatic Provisioning

The device performs an automatic handshake on first boot:

#diagram(
  node((0, 0), [ESP32\nBoot], radius: 1cm, stroke: color-primary),
  edge("-|>", label: text(size: 7pt)[Generate ECDSA key]),
  node((3, 0), [ECDSA Key\nGenerated], radius: 1cm, stroke: color-accent),
  edge("-|>", label: text(size: 7pt)[WiFiManager]),
  node((6, 0), [WiFi\nConnected], radius: 1cm, stroke: color-green),
  edge("-|>", label: text(size: 7pt)[POST /devices/register]),
  node((9, 0), [Backend\nRegister], radius: 1cm, stroke: rgb("#7c3aed")),
  edge("-|>"),
  node((12, 0), [Receives\nsensor_id], radius: 1cm, stroke: rgb("#0d9488")),
  edge("-|>", label: text(size: 7pt)[Save in NVS]),
  node((15, 0), [Operational], radius: 1cm, stroke: color-green),
)

#pagebreak()

== 3.2 Backend

=== Technology Stack

#techstack[
  - *Framework:* FastAPI (Python 3.11) — fully async
  - *Database:* PostgreSQL 15 + PostGIS 3.4 (geospatial extensions)
  - *Message Broker:* Redis 7 (queue + Pub/Sub + rate limiting + deduplication)
  - *MQTT Broker:* Eclipse Mosquitto 2
  - *ORM:* SQLAlchemy 2.0 + GeoAlchemy2 0.19
  - *Containerization:* Docker Compose (6 services)
  - *DB Connection Pool:* pool_size=40, max_overflow=60 (total 100 connections)
]

=== Docker Services

#table(
  columns: (2cm, 1.5cm, 3.5cm, auto),
  stroke: 0.5pt + rgb("#e5e7eb"),
  [*Service*], [*Port*], [*Depends On*], [*Role*],
  [postgres], [5432], [—], [PostgreSQL + PostGIS database],
  [redis], [6379], [—], [Message broker + cache],
  [fastapi-app], [8000], [postgres (healthy),\nredis], [HTTP/WS API Gateway],
  [mosquitto], [1883], [—], [MQTT broker],
  [mqtt-bridge], [—], [mosquitto (healthy),\nfastapi-app (healthy)], [MQTT → HTTP bridge],
  [worker], [—], [postgres (healthy),\nredis], [Background event processor],
)

=== Database Structure

#diagram(
  node((0, 0), [
    #text(size: 9pt, weight: "bold")[*zones*]\
    #text(size: 7pt)[id (PK, int)]\
    #text(size: 7pt)[city (varchar, unique)]\
    #text(size: 7pt)[created_at (timestamp)]\
    #text(size: 7pt)[geom (POLYGON, srid=4326)]
  ], radius: 1.5cm, stroke: rgb("#7c3aed")),
  node((0, -3.5), [
    #text(size: 9pt, weight: "bold")[*alerts*]\
    #text(size: 7pt)[id (PK, int)]\
    #text(size: 7pt)[zone_id (FK)]\
    #text(size: 7pt)[timestamp (timestamp)]\
    #text(size: 7pt)[severity (float)]\
    #text(size: 7pt)[message (varchar)]
  ], radius: 1.5cm, stroke: rgb("#d97706")),
  node((5, 0), [
    #text(size: 9pt, weight: "bold")[*misurators*]\
    #text(size: 7pt)[id (PK, int)]\
    #text(size: 7pt)[active (bool)]\
    #text(size: 7pt)[zone_id (FK)]\
    #text(size: 7pt)[latitude, longitude (float)]\
    #text(size: 7pt)[location (POINT, srid=4326)]\
    #text(size: 7pt)[public_key_hex (varchar, unique)]\
    #text(size: 7pt)[mac_address (varchar, unique)]
  ], radius: 1.8cm, stroke: color-green),
  node((5, -3.5), [
    #text(size: 9pt, weight: "bold")[*misurations*]\
    #text(size: 7pt)[id (PK, int)]\
    #text(size: 7pt)[recorded_at (timestamp)]\
    #text(size: 7pt)[value (int)]\
    #text(size: 7pt)[misurator_id (FK)]
  ], radius: 1.5cm, stroke: rgb("#0d9488")),
  edge((0, -1.5), (0, -2.0), stroke: 0.5pt + rgb("#d1d5db"), "-->"),
  edge((5, -1.8), (5, -2.0), stroke: 0.5pt + rgb("#d1d5db"), "-->"),
  edge((0, 1.5), (5, 1.5), stroke: 0.5pt + rgb("#d1d5db"), "--", label: text(size: 7pt)[1:N, zone_id]),
  edge((5, 1.5), (0, 1.5), stroke: 0.5pt + rgb("#d1d5db"), "--"),
  edge((5, -1.8), (0, -1.8), stroke: 0.5pt + rgb("#d1d5db"), "--", label: text(size: 7pt)[1:N, zone_id]),
)

=== Security Model

The backend implements a four-layer security model:

#highlight[
  1. *API Key* — `X-API-Key` header verified on every request (except /health and /devices/register)
  2. *ECDSA Verification* — NIST256p signature verified using Python `cryptography` library
  3. *Anti-Replay* — 60-second window on device timestamp
  4. *Rate Limiting* — 50 requests/second per IP (Redis fixed window)
]

*Polyglot crypto* support: the backend accepts both DER-encoded (MbedTLS/C++)
and RAW (Python/JS) signature formats, ensuring compatibility with various
client implementations.

=== Magnitude Estimation

The worker estimates seismic magnitude using the MyShake-style formula:

$ M_("IoT") = log_10 ( (v / S) / K ) + b $

Where:
#techstack[
  - $v$ = raw sensor value (int -8192..8192)
  - $S = 100.0$ = scale factor (raw → m/s²)
  - $K = 1.6$ = MEMS calibration factor
  - $b = 3.0$ = empirical offset
]

A CRITICAL alert is triggered when $M >= 4.5$, with per-zone deduplication
(60-second Redis cooldown).

=== REST API Endpoints

#table(
  columns: (2.5cm, 4cm, auto),
  stroke: 0.5pt + rgb("#e5e7eb"),
  [*Method*], [*Path*], [*Description*],
  [GET], [/health], [Health check (PostgreSQL + Redis ping)],
  [POST], [/zones/], [Create geographic zone],
  [GET], [/zones/], [List zones],
  [POST], [/misurators/], [Register sensor with public key],
  [POST], [/devices/register], [ESP32 auto-handshake],
  [GET], [/misurators/], [List registered sensors],
  [POST], [/misurations/], [Data ingestion (with ECDSA validation)],
  [GET], [/sensors/{id}/statistics], [Sensor statistics],
  [GET], [/misurations/], [Last 50 readings],
  [POST], [/demo/trigger-earthquake], [Simulate earthquake (demo)],
)

#techstack[
  *WebSocket:* `/ws/alerts?token=MOBILE_WS_TOKEN` \
  — Persistent connection for real-time alert broadcast
]

=== Geographic Zones

The DB is pre-seeded with 8 global macro-regions. Automatic sensor assignment
uses PostGIS `ST_Contains`, ordered by ascending area to ensure assignment to
the most specific region.

#table(
  columns: (4cm, auto),
  stroke: 0.5pt + rgb("#e5e7eb"),
  [*Zone*], [*Coverage*],
  [Italy - North], [Lombardy, Veneto, Piedmont],
  [Italy - Center], [Tuscany, Lazio, Umbria],
  [Italy - South & Islands], [Campania, Sicily, Sardinia],
  [Western Europe], [France, Spain, Germany, UK],
  [North America], [USA, Canada, Mexico],
  [South America], [Brazil, Argentina, Chile],
  [East Asia], [China, Japan, India],
  [Unknown Region], [Fallback for unmapped coordinates],
)

#pagebreak()

== 3.3 Mobile Frontend

=== Technology Stack

#techstack[
  - *Framework:* React Native 0.81 (Expo SDK 54, React 19.1)
  - *Language:* TypeScript 5.9
  - *Navigation:* Expo Router 6 (file-based, 3-tab bottom navigator)
  - *State Management:* Zustand 5 (3 store slices)
  - *Server State:* TanStack Query 5 (React Query)
  - *Real-Time:* Native WebSocket with exponential backoff reconnection
  - *Notifications:* expo-notifications + Vibration API
  - *Maps:* react-native-maps 1.20
  - *Charts:* victory-native 36
  - *Icons:* lucide-react-native 0.563
]

=== Screen Structure

#diagram(
  node((0, 0), [
    #text(size: 9pt, weight: "bold")[Root Layout]\
    #text(size: 7pt)[QueryClientProvider]\
    #text(size: 7pt)[SafeAreaProvider]\
    #text(size: 7pt)[WebSocketProvider]
  ], radius: 1.5cm, stroke: color-secondary),
  edge("-|>"),
  node((0, -4.5), [
    #text(size: 9pt, weight: "bold")[Tab Navigator]\
    #text(size: 7pt)[3 tabs: Monitor, Map, Settings]
  ], radius: 1.5cm, stroke: color-accent),
  edge((-2.8, -4.5), (-1.5, -4.5), "--", stroke: 0.5pt + rgb("#d1d5db")),
  edge((1.5, -4.5), (2.8, -4.5), "--", stroke: 0.5pt + rgb("#d1d5db")),
  node((-4, -4.5), [
    #text(size: 8pt, weight: "bold")[Monitor]\
    #text(size: 7pt)[Dashboard]\
    #text(size: 7pt)[Seismograph]\
    #text(size: 7pt)[Alert History]
  ], radius: 1.2cm, stroke: color-green),
  node((0, -6), [
    #text(size: 8pt, weight: "bold")[Map]\
    #text(size: 7pt)[Sensor Map]\
    #text(size: 7pt)[Stats Callout]
  ], radius: 1.2cm, stroke: rgb("#0d9488")),
  node((4, -4.5), [
    #text(size: 8pt, weight: "bold")[Settings]\
    #text(size: 7pt)[Notifications toggle]\
    #text(size: 7pt)[Offline mode]\
    #text(size: 7pt)[Clear history]
  ], radius: 1.2cm, stroke: rgb("#d97706")),
  edge((-2.8, -4.5), (-2.8, -6), stroke: 0.5pt + rgb("#d1d5db"), "--"),
  edge((2.8, -4.5), (2.8, -6), stroke: 0.5pt + rgb("#d1d5db"), "--"),
)

=== State Management

The project uses three independent Zustand stores:

*usePreferencesStore*
#techstack[
  - `isOfflineMode` (default: false) — silences WebSocket and polling
  - `notificationsEnabled` (default: true)
]

*useAlertStore*
#techstack[
  - `alerts[]` — last 10 critical alerts in memory
  - `addAlert()`, `clearAlerts()`
]

*useQuakeStore* (legacy)
#techstack[
  - HTTP polling every 2 seconds on `GET /zones/1/alerts`
  - `systemStatus: "SECURE" | "ALERT"`
]

=== WebSocket with Exponential Backoff

The WebSocket context implements a robust reconnection mechanism:

#techstack[
  - Max delay: 30 seconds
  - Exponential backoff: $ "delay" = min(1000 "ms" dot 2^("attempts"), 30 000 "ms") $
  - SOS vibration pattern for critical alerts
  - OS push notifications via expo-notifications
  - Offline Mode support (intentional WS closure)
  - Double-connection guard
]

#pagebreak()

// =============================================================================
// 4 — SECURITY
// =============================================================================
= Security Model

== Threat Model Coverage

#table(
  columns: (4cm, auto),
  stroke: 0.5pt + rgb("#e5e7eb"),
  [*Threat*], [*Countermeasure*],
  [Man-in-the-Middle (MitM)], [ECDSA NIST256p signature on every payload],
  [Device spoofing], [Public key registration + signature verification],
  [Replay attack], [60-second timestamp window],
  [API brute force], [Rate limiting 50 req/s per IP],
  [Unauthorized access], [API Key + enrollment token fail-fast],
  [Malformed payload], [Pydantic validation on all input],
)

== Verification Flow

#diagram(
  node((0, 0), [ESP32\ngenerates payload], radius: 1.2cm, stroke: color-primary),
  edge("-|>", label: text(size: 7pt)[SHA-256 hash]),
  node((3.5, 0), [Sign with\nECDSA NIST256p], radius: 1.2cm, stroke: color-accent),
  edge("-|>", label: text(size: 7pt)[MQTT → Backend]),
  node((7, 0), [Verify\nAPI Key], radius: 1.2cm, stroke: color-green),
  edge("-|>", label: text(size: 7pt)[fail 401]),
  node((7, -3), [Verify\nAnti-Replay], radius: 1.2cm, stroke: rgb("#d97706")),
  edge("-|>", label: text(size: 7pt)[fail 403]),
  node((7, -6), [Verify\nECDSA], radius: 1.2cm, stroke: color-primary),
  edge("-|>", label: text(size: 7pt)[fail 401]),
  node((7, -9), [Redis\nQueue], radius: 1.2cm, stroke: rgb("#7c3aed")),
)

#pagebreak()

// =============================================================================
// 5 — DEPLOYMENT
// =============================================================================
= Deployment

== Docker Compose

The entire backend is orchestrated with Docker Compose:

#techstack[
  ```
  docker compose up --build -d
  ```
  - API: `http://localhost:8000`
  - Swagger UI: `http://localhost:8000/docs`
  - Health Check: `http://localhost:8000/health`
]

== Environment Variables

*Backend (.env)*
#techstack[
  `POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB` \
  `API_PORT, REDIS_HOST, REDIS_PORT, MQTT_PORT` \
  `ENROLLMENT_TOKEN, IOT_API_KEY, MOBILE_WS_TOKEN` \
  `K_CALIBRATION=1.6, B_OFFSET=3.0, SENSOR_SCALE=100.0`
]

*Frontend (.env)*
#techstack[
  `EXPO_PUBLIC_API_BASE_URL` \
  `EXPO_PUBLIC_IOT_API_KEY` \
  `EXPO_PUBLIC_MOBILE_WS_TOKEN`
]

*ESP32 (esp32_config.env)*
#techstack[
  `WIFI_SSID, WIFI_PASS` \
  `SERVER_HOST, SERVER_PORT, SERVER_PATH` \
  `ENROLLMENT_TOKEN`
]

== CI/CD Pipeline

#table(
  columns: (2.5cm, 3.5cm, auto),
  stroke: 0.5pt + rgb("#e5e7eb"),
  [*Workflow*], [*Trigger*], [*Tools*],
  [Backend CI], [Push/PR on backend/\*], [Bandit, Safety, Docker Stress Test],
  [Frontend CI], [Push/PR on frontend/\*], [ESLint, npm audit],
  [IoT CI], [Push/PR on iot/\*], [PlatformIO compile],
  [DevOps CI], [Push/PR on .github/\*], [Actionlint],
  [PR Lint], [Every PR], [Semantic PR title with scope],
  [Deploy], [Push on main (backend)], [Build → Push to GHCR],
)

#pagebreak()

// =============================================================================
// 6 — PERFORMANCE
// =============================================================================
= Performance Metrics

#table(
  columns: (5cm, auto),
  stroke: 0.5pt + rgb("#e5e7eb"),
  [*Parameter*], [*Value*],
  [Sampling Rate], [100 Hz],
  [STA Window], [1 second (100 samples)],
  [LTA Window], [10 seconds (1000 samples)],
  [DB Pool (max)], [100 connections],
  [Rate Limiting], [50 req/s per IP],
  [Anti-Replay Window], [60 seconds],
  [Alert Cooldown], [60 seconds per zone],
  [Magnitude Threshold], [M $>=$ 4.5],
  [WebSocket Reconnect], [Exponential, max 30s],
  [Sensor Polling (app)], [10 seconds],
  [Readings Polling (app)], [2 seconds],
  [Alert History (app)], [Last 10 events],
)

#pagebreak()

// =============================================================================
// 7 — STRESS TEST
// =============================================================================
= Stress Test

The load test (`tests/stress_test.py`, v3.0) validates the entire pipeline
in three phases:

== Phase 1: MQTT Firehose
#techstack[
  - 150+ virtual sensors with valid ECDSA signature
  - MQTT publish on `quakeguard/telemetry`
  - Middleware rate limiting (50 req/s per IP)
]

== Phase 2: Security Attacks
#techstack[
  - *Bad Signature:* Sign with unregistered key → blocked (401)
  - *Replay Attack:* 2-hour-old timestamp → blocked (403)
]

== Phase 3: End-to-End Verification
#techstack[
  - Polling `GET /sensors/{id}/statistics`
  - Up to 10 attempts in 10 seconds
  - PostgreSQL persistence verification
]

*Success criteria:* `🏆 SYSTEM CERTIFIED`

#pagebreak()

// =============================================================================
// 8 — AUTOMATED TESTS (CI/CD)
// =============================================================================
= Automated Tests (CI/CD)

The CI pipeline automatically runs over 90 tests across three platforms
on every push to `main`/`develop`.

== Backend (Python — pytest, 62 tests)

Unit tests (`tests/unit/`) run without Docker and cover:

#table(
  columns: (3cm, 1.5cm, auto),
  stroke: 0.5pt + rgb("#e5e7eb"),
  [*Module*], [*Tests*], [*What it verifies*],
  [$monospace("security")$], [13], [ECDSA valid/invalid signature, API key auth, anti-replay, IoT payload validation],
  [$monospace("magnitude")$], [10], [Magnitude estimation: zero, negative, M4.5 threshold, clamping, consistency],
  [$monospace("schemas")$], [11], [Pydantic validation: value range, short signature, timestamp, coordinates],
  [$monospace("models")$], [8], [ORM creation: Zone, Misurator, Misuration, Alert, and relationships],
  [$monospace("seed")$], [5], [Idempotent seeding, expected regions, Unknown Region geometry],
  [$monospace("worker")$], [5], [Event processing, CRITICAL alerts, Redis dedup, error rollback],
)

Integration tests (`tests/integration/`) require Docker and test FastAPI
endpoints with `TestClient`:
- 10 tests on health, CRUD zones/misurators/misurations, statistics, provisioning
- HTTP response verification (401, 403, 201, 202, 503)

The existing load test (`tests/stress_test.py`) completes the suite with 150+
virtual sensors over MQTT.

== Frontend (TypeScript — Jest, 21 tests)

Jest tests cover pure Zustand store logic and the API service:

#table(
  columns: (3cm, 1.5cm, auto),
  stroke: 0.5pt + rgb("#e5e7eb"),
  [*Module*], [*Tests*], [*What it verifies*],
  [$monospace("useAlertStore")$], [5], [Alert addition, 10-item cap, LIFO order, reset],
  [$monospace("usePreferencesStore")$], [3], [Offline mode toggle, notifications toggle],
  [$monospace("quakeStore")$], [7], [Sensor fetch, monitoring start/stop, error handling, single polling],
  [$monospace("api")$], [6], [GET/POST, HTTP errors, network errors, JSON body],
)

== IoT (C++ — PlatformIO Unity, 12 tests)

Native PlatformIO tests compile and run on Linux host without hardware:

#table(
  columns: (3cm, 1.5cm, auto),
  stroke: 0.5pt + rgb("#e5e7eb"),
  [*Module*], [*Tests*], [*What it verifies*],
  [$monospace("RingBuffer")$], [6], [Push, average, buffer full, wraparound, overwrite],
  [$monospace("Detect")$], [6], [HPF gravity removal, transients, noise floor, trigger ratio, zero-division protection],
)

== CI Workflow Integration

All tests are integrated into the existing GitHub Actions workflows:

#techstack[
  - `backend-ci.yml`: bandit + safety + pytest unit + pytest integration + stress test
  - `frontend-ci.yml`: eslint + npm audit + Jest
  - `iot-ci.yml`: pio build + pio test native (firmware/)
]

#pagebreak()

// =============================================================================
// 9 — ROADMAP
// =============================================================================
= Roadmap

#table(
  columns: (2cm, 2cm, auto),
  stroke: 0.5pt + rgb("#e5e7eb"),
  [*Version*], [*Status*], [*Goals*],
  [v1.0], [✅ Current], [Full E2E pipeline, mobile app, CI/CD],
  [v1.1], [🔄 In progress], [Wiki docs, Alembic migrations, cloud MQTT],
  [v2.0], [🔮 Future], [AI seismic assistant (Ollama + natural language)],
)

#pagebreak()

// =============================================================================
// 10 — LICENSE
// =============================================================================
= License

#align(center)[
  #block(height: 1cm)

  This project is distributed under the \
  *GNU Affero General Public License v3.0 (AGPL-3.0)*

  #block(height: 5mm)

  #text(size: 9pt, fill: color-muted)[
    Copyright (c) 2026 GiZano. All rights reserved. \
    Developed by Giovanni Zanotti (\@GiZano) and Riccardo (\@riccardo0731) \
    Open source project for educational and research purposes.
  ]
]
