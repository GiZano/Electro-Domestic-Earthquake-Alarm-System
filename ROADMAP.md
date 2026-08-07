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

> **Geo-zoning & cooldown-lock design (relevant for the paper's System-Engineering claim):**
> - The per-zone Redis cooldown lock (`lock:cooldown:<zone>`) can *silence independent
>   earthquakes* inside a single macro-region (e.g. two events in the same "North America"
>   polygon trigger one lock and the second alert is dropped as a duplicate).
> - Plan fragmentation to Geohash/H3 keys (`lock:cooldown:<geohash>`) — this offloads zone
>   assignment from PostGIS `ST_Contains` to fast Redis lookups.
> - For real administrative polygons: apply `ST_SimplifyPreserveTopology` + a GiST index;
>   size zones so an event cannot physically reach the adjacent zone (~50–100 km for
>   destructive surface-wave propagation).

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
- [x] Calibration of the trigger parameters (`TRIGGER_RATIO`, `NOISE_FLOOR`, `HPF_ALPHA`) against ground-truth — `research/calibrate.py`; **real ground-truth download via ESM** (public FDSN API + ObsPy, CC-BY-4.0 flatfiles) — see `research/README.md`

> **Remaining for full R1 closure:** real ESM ground-truth validation via ObsPy (public FDSN API, no token required); the calibration currently runs on the realistic synthetic fallback (unit-tested, CI-covered).

### R2 — AI Benchmarking (this is the paper's primary novelty contribution)

- P50/P99 latency benchmark of the local async AI worker (Ollama)
- Measurement of the hallucination rate of the generated reports
- Quantification of the privacy/latency advantage vs Cloud baseline

> **Two distinct claims — do not conflate them in the paper:**
> - **Self-hosted, data-sovereign LLM.** Inference runs inside the Docker network
>   (`http://ollama:11434`), uses no third-party inference API, and telemetry never
>   leaves the deployment. *True regardless of deployment target (defensible).*
> - **Local-first resilience** is a *deployment property*, not a software property:
>   it holds only when the full alert path (local MQTT broker → bridge → AI worker)
>   runs on an on-premise host co-located with the community. **Today the alert path
>   uses HiveMQ Cloud, so the alert path still depends on the WAN.** Claim this only
>   for the on-premise topology.
>
> **Determinism is a hypothesis, not a guarantee:** `temperature=0`, `top_k=1`
> (greedy decoding) remove *stochastic variance*, but the model can be
> *deterministically wrong*. The hallucination rate must be **measured empirically**
> in this benchmark before any quantitative claim is reported.

---

### R3 — Dissemination & Output

> R1 + R2 converge here: results are published as artifacts separate from the software.

- [ ] Publish open validation dataset (Zenodo DOI, separate from software)
- [ ] Draft technical paper / preprint (arXiv)

> **Open data strategy & license gate:**
> - Publish the **derived ESM parametric dataset** (CC-BY-4.0) as a re-distributable
>   Zenodo artifact with its own DOI, separate from the software.
> - **License re-verification step before publishing ANY derived data:** re-check the
>   current ITACA/ESM license terms and update `CITATION.cff` at release time (ITACA is
>   CC-BY-NC-ND-4.0 and forbids redistribution of derived waveforms).

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

### Performance & scaling engineering (post-paper, not needed at current scale)

- **Non-blocking MQTT-Bridge refactor** — `aiomqtt` + async push to Redis (or `httpx`/`aiohttp`)
  to make the bridge relay fully non-blocking. *Parked: the current synchronous bridge is not
  the bottleneck at sandbox scale.*
- **Rust ingestion microservice (Axum) + ECDSA verification via PyO3** — the hybrid path:
  keep FastAPI/PostGIS/Ollama, move only the CPU-bound signature verification (P-256/SHA-256)
  to native speed; a dedicated Axum ingestion endpoint can later absorb `POST /readings/`.
- **Local MQTT broker (`mosquitto`) as the default alert path** — makes the R2 "local-first
  resilience" claim real; explicitly note HiveMQ Cloud as the current WAN dependency.
- **Load-test on rented infrastructure (e.g. AWS), one-off** — not GitHub Actions (hardware
  limits); results published as static charts in the paper.

---

