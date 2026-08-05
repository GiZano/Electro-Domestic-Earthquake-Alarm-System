"""
Ollama Local LLM Client
-----------------------
Responsible for generating AI emergency reports from alert telemetry.

Privacy model:
    Ollama runs locally inside the Docker network (default `http://ollama:11434`).
    No telemetry ever leaves the host. This satisfies the v1.2.0 privacy requirement.

Anti-hallucination for safety-critical systems:
    * `options.temperature` is forced to 0.0 (maximal deterministic sampling).
    * `options.top_k` is forced to 1 (greedy decoding).
    * The system prompt explicitly forbids inventing data and limits the output to
      a strict two-section structure (SUMMARY / RECOMMENDATIONS).
    * On any connectivity/timeout error the client returns an explicit
      "unavailable" report — it never fabricates seismic data to "keep the pipeline green".
"""

import json
import os

import requests

# --- CONFIGURATION ---
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")  # NOSONAR:S5332 local on-premise Ollama, HTTP confined to the private Docker network
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "30"))

# Status constants (mirrored in the EmergencyReport.status column)
STATUS_PENDING = "PENDING"
STATUS_COMPLETED = "COMPLETED"
STATUS_FAILED = "FAILED"

SYSTEM_PROMPT = (
    "You are an emergency response AI. Only use the provided JSON telemetry. Do not invent data."
)

INSTRUCTIONS = """
Generate an emergency seismic report based ONLY on the provided JSON telemetry.

Strict rules:
- Never invent magnitude, coordinates, timestamps, alerts, or zone names not present in the input.
- Never provide specific, unverified evacuation instructions. Only generic, universally safe guidance.
- Output plain text with exactly two sections:
  1. "SUMMARY:" followed by a concise 2-3 sentence summary of the event.
  2. "RECOMMENDATIONS:" followed by 3-5 short bullet lines, each starting with "- ".
- Do not add any other text, headers, or commentary outside these two sections.
"""

# Keys delivered by the telemetry context. Any value missing from the input JSON
# must be omitted from the prompt so the model cannot be led to hallucinate them.
TELEMETRY_KEYS = ("alert_id", "zone_id", "zone_name", "magnitude", "sensor_id", "value", "timestamp")


def build_prompt(telemetry: dict) -> str:
    """Serialize the telemetry context into a deterministic prompt."""
    safe = {key: telemetry[key] for key in TELEMETRY_KEYS if key in telemetry}
    telemetry_json = json.dumps(safe, ensure_ascii=False, sort_keys=True)
    return f"{SYSTEM_PROMPT}\n\n{INSTRUCTIONS}\n\nJSON telemetry:\n{telemetry_json}"


def parse_report(raw: str, model: str) -> dict:
    """Parse the raw model output into (summary, recommendations). Tolerant of format drift."""
    summary = ""
    recommendations = []
    current = None

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        upper = stripped.upper()
        if upper.startswith("SUMMARY"):
            current = "summary"
            _, _, rest = stripped.partition(":")
            if rest.strip():
                summary = rest.strip()
        elif upper.startswith("RECOMMENDATIONS"):
            current = "recommendations"
        elif current == "recommendations":
            recommendations.append(stripped.lstrip("- ").strip())

    if not summary:
        summary = raw.strip()[:500] or "(no summary returned)"

    return {
        "summary": summary,
        "recommendations": recommendations,
        "model": model,
        "raw": raw,
    }


def generate_report(telemetry: dict) -> dict:
    """Call `POST /api/generate` on the local Ollama host with forced determinism.

    Returns a dict with: summary, recommendations, model, raw.
    On failure returns an explicit "unavailable" result carrying an `error` field,
    so the worker can mark the report as FAILED.
    """
    prompt = build_prompt(telemetry)
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "top_k": 1,
        },
    }
    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json=payload,
            timeout=OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        raw = resp.json().get("response", "")
        return parse_report(raw, model=OLLAMA_MODEL)
    except Exception as exc:  # noqa: BLE001 - any failure must degrade gracefully
        return {
            "summary": "AI report unavailable.",
            "recommendations": ["Verify the situation with local authorities."],
            "model": OLLAMA_MODEL,
            "raw": "",
            "error": str(exc),
        }