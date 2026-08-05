# ROADMAP — QuakeGuard

> Semantic Versioning progression.

---

## v1.0.0 — Edge Seismic Detection (Released)

Edge seismic detection on ESP32 with local alerts.

- ADXL345 acquisition at 100 Hz with STA/LTA triggering
- ECDSA signature on every payload
- Local alert via LED / serial

---

## v1.1.0 — Cloud & Security (Released)

Data Plane migration to MQTT Cloud (HiveMQ), REST Control Plane (HTTPS) and TLS security.

- Data Plane: ESP32 → HiveMQ Cloud (port 8883, TLS + username/password)
- Control Plane: ngrok HTTPS tunnel for REST provisioning
- `setInsecure()` for TLS handshake on ESP32
- MQTT Bridge (Python Paho) with TLS
- Working mobile dashboard with live data
- Active CI/CD

---

## v1.2.0 — AI Cloud (Current)

On-premise AI integration (LLM in the backend) to generate textual emergency reports from MQTT data.

- ✅ On-premise LLM via Ollama (`llama3.2:1b`) consuming confirmed alerts — telemetry never exposed
- ✅ Automatic emergency report generation: magnitude, zone, timestamp, recommendations (deterministic, anti-hallucination)
- ✅ WebSocket push of the AI report to the mobile app (banner + history card)
- ✅ `PENDING → COMPLETED | FAILED` state machine with DLQ and explicit fallback
- ✅ REST endpoint `GET /reports/{alert_id}`

---

## v1.3.0 — Synchronized GNSS

Advanced GNSS synchronization of nodes for exact timestamps.

- Optional GPS/GNSS module on ESP32
- Correct NTP + PPS timestamps for all nodes
- Replace hardcoded GPS (Rome coordinates) with real coordinates
- ADXL345 offset calibration on boot

---

## v2.0.0 — Epicenter Triangulation

Triangulation algorithm. Multi-node spatial correlation combined with AI reports to compute the internal epicenter.

- Triangulation algorithm from ≥3 nodes
- Multi-node spatial and temporal correlation
- Internal epicenter computation
- AI + triangulation data fusion for precise alerts

---

## #Research — Scientific Validation (SIL)

Parallel node (non-semantic): started after reaching **v2.1** at a minimum.

Software-in-the-Loop (SIL) cross-validation: no logic duplication. It uses **100% of the production C++ code** on both the firmware and the host, guaranteeing numerical equivalence for the IEEE paper.

### R1 — STA/LTA detection cross-validation (High priority)

- ✅ Isolation of the STA/LTA algorithmic core in pure C++, fully decoupled from the ESP32 hardware (no I2C/WiFi/FreeRTOS calls in the algorithmic core)
- ✅ Native host compilation of the C++ core (same source as the firmware)
- ✅ Python as the **sole orchestrator**: reading the public INGV dataset (accelerograms), passing data to the C++ binary via `ctypes`/`subprocess`/`pybind11`, collecting trigger points and tracing ROC curves
- ✅ Metrics: Sensitivity/Recall, False-Alarm Rate, response latency
- ✅ Calibration of the trigger parameters (`TRIGGER_RATIO`, `NOISE_FLOOR`, `HPF_ALPHA`) against INGV ground-truth

### R2 — AI Benchmarking (Claim of novelty)

- P50/P99 latency benchmark of the local async AI worker (Ollama)
- Measurement of the hallucination rate of the generated reports
- Quantification of the privacy/latency advantage vs Cloud baseline

---

### R3 — Scientific Validation (parallel node, starts after v1.2)

- [ ] SIL cross-validation against INGV ground-truth catalog
- [ ] ROC metrics + AI benchmarking (latency P50/P99, hallucination rate)
- [ ] Publish open validation dataset (Zenodo DOI, separate from software)
- [ ] Draft technical paper / preprint (arXiv)
