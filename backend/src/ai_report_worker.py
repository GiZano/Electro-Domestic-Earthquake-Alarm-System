"""
AI Report Worker
----------------
Consumes the `ai_report_queue` and generates human-readable emergency reports
via the local Ollama service.

Decoupling rationale (v1.2.0):
    * The high-throughput ingestion worker (`worker.py`) must never block on LLM
      inference. It enqueues alert context and immediately returns.
    * This dedicated process owns the slow, stateful interaction with Ollama and
      transitions `EmergencyReport.status` (PENDING -> COMPLETED | FAILED).

Failure semantics:
    * On any processing error the payload is pushed to `ai_report_queue_dlq` and
      the corresponding DB row is marked FAILED so clients stop waiting.
"""

import json
import os
import signal
import time
from datetime import datetime, timezone

import redis
from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.models import EmergencyReport
from src.ollama_client import generate_report, STATUS_COMPLETED, STATUS_FAILED

# Redis Config
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
AI_REPORT_QUEUE = os.getenv("AI_REPORT_QUEUE", "ai_report_queue")
AI_REPORT_DLQ = os.getenv("AI_REPORT_DLQ", "ai_report_queue_dlq")
AI_REPORTS_CHANNEL = os.getenv("AI_REPORTS_CHANNEL", "ai_reports")

redis_sync = redis.from_url(REDIS_URL, decode_responses=True)

RUNNING = True


def handle_signal(signum, frame):
    global RUNNING
    RUNNING = False


def publish_report(report: EmergencyReport, event: dict, recommendations: list) -> None:
    """Broadcast the terminal report state to the WebSocket layer."""
    payload = {
        "type": "EMERGENCY_REPORT",
        "alert_id": event.get("alert_id"),
        "report_id": report.id,
        "zone_id": report.zone_id,
        "magnitude": report.magnitude,
        "status": report.status,
        "summary": report.summary,
        "recommendations": recommendations,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    redis_sync.publish(AI_REPORTS_CHANNEL, json.dumps(payload))


def process_ai_event(event: dict, db: Session) -> None:
    report_id = event.get("report_id")
    if not report_id:
        return

    report = db.query(EmergencyReport).filter(EmergencyReport.id == report_id).first()
    if not report:
        return

    result = generate_report(event)

    if result.get("error"):
        report.status = STATUS_FAILED
        report.summary = "AI report unavailable."
        report.error = str(result["error"])[:255]
        recommendations = []
    else:
        report.status = STATUS_COMPLETED
        report.summary = result["summary"]
        report.recommendations = "\n".join(result["recommendations"])
        report.model_used = result["model"]
        recommendations = result["recommendations"]

    db.commit()
    publish_report(report, event, recommendations)


def mark_failed(report_id) -> None:
    """Best-effort FAILED transition using a fresh session (e.g. after DLQ push)."""
    if not report_id:
        return
    try:
        db = SessionLocal()
        try:
            report = db.query(EmergencyReport).filter(EmergencyReport.id == report_id).first()
            if report and report.status != STATUS_COMPLETED:
                report.status = STATUS_FAILED
                report.error = "Report processing failed."
                db.commit()
        finally:
            db.close()
    except Exception:  # noqa: BLE001 - best effort only
        pass


def run_ai_worker() -> None:
    print("🤖 AI Report Worker started. Listening for 'ai_report_queue'...")
    db = SessionLocal()

    while RUNNING:
        try:
            result = redis_sync.brpop(AI_REPORT_QUEUE, timeout=1)
            if not result:
                continue

            _, data = result
            event = json.loads(data)

            try:
                process_ai_event(event, db)
                print(f"✅ AI Report processed (report_id={event.get('report_id')})", flush=True)
            except Exception as e:
                print(f"❌ AI Report Error: {e}. Moving to DLQ.", flush=True)
                db.rollback()
                redis_sync.lpush(AI_REPORT_DLQ, data)
                mark_failed(event.get("report_id"))

        except Exception as e:
            print(f"❌ Redis Connection Error: {e}", flush=True)
            time.sleep(2)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    run_ai_worker()
