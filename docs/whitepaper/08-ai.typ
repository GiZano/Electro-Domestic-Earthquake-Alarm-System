= AI Emergency Report Service

With the release of v1.2.0, QuakeGuard introduces an on-premise AI layer that automatically generates human-readable emergency reports from confirmed seismic alerts[cite: 1]. The service is powered by a locally hosted Large Language Model (LLM) via Ollama, guaranteeing that raw telemetry — including zone coordinates and magnitude estimates — never leaves the host machine[cite: 1].

== Privacy-First Local Inference

The AI pipeline is strictly self-contained and requires no external API keys or cloud LLM endpoints[cite: 1].

- *Local Ollama Service:* A dedicated `ollama` Docker container exposes the native Ollama API (`/api/generate`) on an internal Docker network[cite: 1]. On first startup the entrypoint script (`init-scripts/ollama-entrypoint.sh`) automatically pulls the configured model (`OLLAMA_MODEL`, default `llama3.2:1b`) before the service becomes healthy[cite: 1].
- *On-Premise Isolation:* Because the model runs inside the Compose network, every telemetry attribute used to compose a report stays within the host's Docker bridge network[cite: 1]. No third-party receives the data[cite: 1].
- *Model Selection:* The default 1B-parameter model is intentionally small to keep CPU and RAM footprints low while remaining fast enough to generate a report in near real-time[cite: 1]. Operators may override `OLLAMA_MODEL` (e.g., `qwen2.5:1.5b`) for higher quality output[cite: 1].

== Deterministic Report Generation

Emergency messaging must never fabricate data[cite: 1]. The AI client (`ollama_client.py`) therefore constrains the model with hard guarantees[cite: 1]:

- *Sampling:* Every request is issued with `temperature: 0.0` and `top_k: 1` (greedy decoding), eliminating stochastic drift between retries[cite: 1].
- *Streaming Disabled:* Reports are generated in a single non-streaming inference pass, simplifying parsing and validation on the backend[cite: 1].
- *Strict System Prompt:* The model is instructed: _"You are an emergency response AI. Only use the provided JSON telemetry. Do not invent data."_[cite: 1]
- *Telemetry Whitelist:* The prompt is built from a fixed allowlist of fields (`zone_id`, `zone_name`, `magnitude`, `timestamp`, `sensor_count`), so the model can only reason about authenticated, persisted data[cite: 1].
- *Failure Fallback:* If the inference request fails or returns an unparseable response, the pipeline stores an explicit `"AI report unavailable."` message rather than attempting to guess[cite: 1].

== Asynchronous Worker & State Machine

Report generation is fully decoupled from the alert engine via a dedicated Redis queue (`ai_report_queue`) and a separate consumer process (`ai_report_worker.py`)[cite: 1].

- *Non-Blocking Enqueue:* When the main worker (`worker.py`) persists a confirmed `Alert`, it creates an `EmergencyReport` row in `PENDING` state and pushes the alert context to `ai_report_queue` via `lpush`[cite: 1]. The alert pipeline is never blocked by LLM latency[cite: 1].
- *State Machine:* Each report transitions through a tri-state lifecycle[cite: 1]:

#align(center)[
  ```text
           [Alert Triggered]
                  |
                  v
             +---------+
             | PENDING |
             +---------+
                  |
           (Ollama Processing)
                  |
      +-----------+-----------+
      |                       |
      v                       v
 +-----------+          +-----------+
 | COMPLETED |          |  FAILED   |
 +-----------+          +-----------+
      |                       |
(WebSocket Push)        (DLQ Retry)
  ```
  _Figure: AI Report State Machine_
]

- *Dedicated Consumer:* The `ai-worker` container loops on a blocking `brpop`, fetches the telemetry context, invokes Ollama, and atomically flips the report state[cite: 1]. On success the worker publishes an `EMERGENCY_REPORT` payload to the `ai_reports` Redis Pub/Sub channel and commits the `COMPLETED` report with its `summary` and `recommendations`[cite: 1].
- *Dead Letter Queue:* Unrecoverable failures (missing report, persistent inference errors) push the event to `ai_report_queue_dlq` and mark the report `FAILED`[cite: 1]. The mobile app renders a "Report unavailable" badge for `FAILED` reports instead of showing partial or fabricated content[cite: 1].
- *Graceful Shutdown:* The worker traps `SIGTERM`/`SIGINT` to drain in-flight inference calls before exiting[cite: 1].

== WebSocket Delivery

The mobile client receives reports through the existing real-time channel[cite: 1].

- *Channel Subscription:* The backend WebSocket broadcaster (`main.py`) subscribes to both `quake_alerts` and `ai_reports`, delivering each `EMERGENCY_REPORT` payload over the authenticated `/ws/alerts` socket[cite: 1].
- *Correlation:* The payload carries the originating `alert_id`, allowing the app to attach the report to the matching alert in its history[cite: 1].
- *REST Fallback:* A new `GET /reports/{alert_id}` endpoint exposes the persisted report for clients that reconnect after the alert (e.g., after a WebSocket drop)[cite: 1].
- *Inline Presentation:* The mobile app renders `COMPLETED` reports as a highlighted banner for the latest alert and as a dedicated card inside the alert history feed, showing the generated summary and per-item recommendations[cite: 1].

== Operational Notes

- *Compose Profile:* The `ollama` and `ai-worker` services are gated behind the `ai` profile so that the default `docker compose up` remains lightweight and CI stays hermetic[cite: 1]. Enable the pipeline with `docker compose --profile ai up -d`[cite: 1].
- *Feature Flag:* The main worker only enqueues reports when `AI_REPORT_ENABLED=true` (default `false`) to avoid orphaned `PENDING` rows when the AI profile is not running[cite: 1].
- *Timeouts:* Inference requests honor `OLLAMA_TIMEOUT`; the Ollama service uses `KEEP_ALIVE` to reduce cold-start latency between alerts[cite: 1].
