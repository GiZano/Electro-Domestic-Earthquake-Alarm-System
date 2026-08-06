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

## v1.2.0 — On-Premise AI Reports (Current)

On-premise AI integration (LLM in the backend) to generate textual emergency reports from MQTT data.

- ✅ On-premise LLM via Ollama (`llama3.2:1b`) consuming confirmed alerts — telemetry never exposed
- ✅ Automatic emergency report generation: magnitude, zone, timestamp, recommendations (deterministic, anti-hallucination)
- ✅ WebSocket push of the AI report to the mobile app (banner + history card)
- ✅ `PENDING → COMPLETED | FAILED` state machine with DLQ and explicit fallback
- ✅ REST endpoint `GET /reports/{alert_id}`

---

## v1.2.1 — Zero-Trust Serial Fallback

Signed telemetry over a serial link (USB CDC) when MQTT/WiFi connectivity is lost, so the host still receives data during offline simulations.

- Second consumer of the existing event queue: signed telemetry over USB CDC when MQTT is unreachable
- ECDSA-signed payloads, identical signing to the MQTT data plane
- Host-side bridge collecting serial output and forwarding to the ingestion pipeline

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

## v2.1.0 — Data Dashboards

Grafana dashboards for real-time visualization of seismic telemetry.

- Grafana dashboards for live seismic telemetry
- Real-time visualization of multi-node network activity

---

## v2.2.0 — Heterogeneous Edge Intelligence

Crowning of the engineering phase. Two-tier edge cluster where TinyML is **not** a simple STA/LTA replacement, but a hierarchical Decision Fusion between cheap ubiquitous sensors and intelligent confirmation gates.

> **Blocking prerequisite:** the STA/LTA parameter calibration from **R1** must be completed before drafting/training the v2.2.0 models. Calibration is urgent and runs in parallel with v1.3.

**Tier A — Ubiquitous sensors (ESP32-C3):**
- Low-cost, installable anywhere; STA/LTA + ECDSA signing, unchanged from v1.x
- Produce the **proprietary MEMS dataset** (fills the domain gap vs INGV professional seismometers)

**Tier B — Intelligent confirmation gates (ESP32-S3):**
- Hybrid quantized CNN (INT8) via ESP-DL / TensorFlow Lite Micro
- Activated **only on STA/LTA triggers** to compute the local event probability
- Emits a confidence score that confirms or discards Tier A triggers (Decision Fusion)

---

## #Research — Scientific Validation (SIL)

Parallel node (non-semantic). **R1 is the Foundation**: it starts immediately, in parallel with v1.3 (GNSS), and its calibration is urgent because it is the blocking prerequisite for v2.2.0 and the paper.

Software-in-the-Loop (SIL) cross-validation: no logic duplication. It uses **100% of the production C++ code** on both the firmware and the host, guaranteeing numerical equivalence for the IEEE paper.

### R1 — STA/LTA detection cross-validation via SIL (Foundation)

> Status: **implemented (Fase 0–4).** The STA/LTA core is isolated in pure C++, compiled natively in CI, and driven by the Python orchestrator with zero logic duplication.
>
> Scheduling: **in parallel with v1.3 (GNSS)**. The calibration of the trigger parameters is **urgent and blocking**: it gates the start of v2.2.0 model drafting/training.

- [x] Isolation of the STA/LTA algorithmic core in pure C++, fully decoupled from the ESP32 hardware (no I2C/WiFi/FreeRTOS calls in the algorithmic core) — `firmware/src/DetectionCore.h`
- [x] Native host compilation of the C++ core (same source as the firmware) — `detect_cli.cpp` + CI build
- [x] Python as the **sole orchestrator**: reading the public INGV dataset (accelerograms), passing data to the C++ binary via `subprocess`, collecting trigger points and tracing ROC curves — `research/`
- [x] Metrics: Sensitivity/Recall, False-Alarm Rate, response latency — `research/metrics.py`
- [x] Calibration of the trigger parameters (`TRIGGER_RATIO`, `NOISE_FLOOR`, `HPF_ALPHA`) against ground-truth — `research/calibrate.py`; **real ITACA download pending** (`ITICA_TOKEN`, see `research/README.md`)

> **Remaining for full R1 closure:** real ITACA/INGV ground-truth validation once the ITACA token portal is reachable; the calibration currently runs on the realistic synthetic fallback (unit-tested, CI-covered).

### R2 — AI Benchmarking (this is the paper's primary novelty contribution)

- P50/P99 latency benchmark of the local async AI worker (Ollama)
- Measurement of the hallucination rate of the generated reports
- Quantification of the privacy/latency advantage vs Cloud baseline

---

### R3 — Dissemination & Output

> R1 + R2 converge here: results are published as artifacts separate from the software.

- [ ] Publish open validation dataset (Zenodo DOI, separate from software)
- [ ] Draft technical paper / preprint (arXiv)

---

## Future Horizon — Cloud Infrastructure & Real-Time Auto-Scaling

Production-grade cloud platform behind the alert pipeline: the MQTT/REST/AI stack of v1.x–v2.2 runs as containerized workloads on Kubernetes, fully provisioned as **Infrastructure-as-Code** with Terraform. The control plane elastically scales with the number of deployed sensors and with real-time alert bursts.

> Post-research horizon (after v2.2.0 / paper). Not blocking for the thesis; it targets the operational release of the system.

**Infrastructure-as-Code (Terraform):**
- Declarative provisioning of the cloud provider resources (managed Kubernetes cluster, VPC, node pools, networking) in versioned modules
- State management and drift detection for reproducible, auditable deployments

**Orchestration (Kubernetes):**
- Containerized deployment of the MQTT broker, AI report worker, REST control plane and dashboard
- Native autoscaling (Horizontal Pod Autoscaler / cluster autoscaler) driven by MQTT ingestion rate and CPU/memory
- Real-time elastic burst handling: alert spikes scale up workers (AI reports) and event queues; quiet periods scale to zero
- Rolling updates, health probes and self-healing for continuous availability

**Delivery & observability:**
- GitOps / CI/CD pipeline applying Terraform and Helm charts
- Monitoring and alerting for the cluster itself (resource saturation, autoscaling events)

---

