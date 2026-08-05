import os
import json
import time
import math
from datetime import datetime, timezone
import redis
from sqlalchemy.orm import Session
from src.database import SessionLocal, engine
from src.models import Reading, Alert, EmergencyReport, Zone

# Redis Config
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_sync = redis.from_url(REDIS_URL, decode_responses=True)

# AI Report integration
AI_REPORT_QUEUE = os.getenv("AI_REPORT_QUEUE", "ai_report_queue")
# Gate: when False (or unset), the worker skips AI report creation/enqueue entirely.
# The Ollama + ai-worker containers run behind the `ai` compose profile.
AI_REPORT_ENABLED = os.getenv("AI_REPORT_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")

# Seismic Calibration Constants (Tunable via Environment)
K_CALIBRATION = float(os.getenv("K_CALIBRATION", "1.6"))  # MyShake-style MEMS calibration factor
B_OFFSET = float(os.getenv("B_OFFSET", "3.0"))            # Empirical offset, anchor: PGA 0.07 m/s² ≈ M3.85
SENSOR_SCALE = float(os.getenv("SENSOR_SCALE", "100.0"))  # Raw value to m/s² conversion factor

def estimate_magnitude(sensor_value: int) -> float:
    """
    Estimates IoT magnitude from STA-based peak acceleration.
    Formula: M_IoT = log10(PGA_calib) + b
    Based on MyShake-style MEMS network approach.
    Reference: Zanotti, G. (2026) - QuakeGuard Magnitude Estimation Note.
    """
    pga_m_s2 = sensor_value / SENSOR_SCALE
    pga_calib = pga_m_s2 / K_CALIBRATION
    
    # Guard against log10(0) or negative values
    if pga_calib <= 0:
        return 0.0
    
    magnitude = math.log10(pga_calib) + B_OFFSET
    
    # Clamp to physically meaningful range for MEMS sensors
    return max(0.0, min(magnitude, 9.9))

def process_event(event: dict, db: Session):
    """Inserts a single sensor measurement into PostGIS and triggers alerts with deduplication."""
    
    # 1. Save to Database
    new_entry = Reading(
        value=event.get("value"),
        sensor_id=event.get("sensor_id")
    )
    db.add(new_entry)

    # 2. 🚨 ALARM LOGIC: Check if threshold is breached
    sensor_value = event.get("value", 0)
    magnitude = estimate_magnitude(sensor_value)
    zone_id = event.get("zone_id", 0)
    alert_published = False
    alert_entry = None
    
    # Trigger a CRITICAL alert if physical magnitude is 4.5 or higher
    if magnitude >= 4.5:
        cooldown_key = f"alert_cooldown:{zone_id}"
        
        # Atomic check-and-set with 60s TTL (Deduplication)
        if redis_sync.set(cooldown_key, "active", nx=True, ex=60):
            alert_published = True
            alert_entry = Alert(
                zone_id=zone_id,
                magnitude=magnitude,
                message=f"High seismic activity detected (Sensor {event.get('sensor_id')})!"
            )
            db.add(alert_entry)
        else:
            print(f"🚫 ALERT SUPPRESSED: Zone {zone_id} is in 60s cooldown.", flush=True)

    # 3. Commit atomically: Reading (+ Alert) — flush to obtain IDs before enqueue
    db.commit()
    if alert_published and alert_entry is not None:
        db.refresh(alert_entry)

    # 4. Publish alert to Redis (best-effort after DB commit — outbox pattern)
    if alert_published and alert_entry is not None:
        alert_payload = {
            "type": "CRITICAL",
            "alert_id": alert_entry.id,
            "zone_id": zone_id,
            "magnitude": round(magnitude, 1),
            "message": f"High seismic activity detected (Sensor {event.get('sensor_id')})!",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        redis_sync.publish("quake_alerts", json.dumps(alert_payload))
        print(f"🚨 ALERT PUBLISHED: Zone {zone_id} - Mag {round(magnitude, 1)}", flush=True)

        # 5. 🤖 AI REPORT: enqueue context for the dedicated worker (non-blocking)
        if AI_REPORT_ENABLED:
            enqueue_ai_report(db, event, alert_entry.id, zone_id, magnitude)

def enqueue_ai_report(db: Session, event: dict, alert_id: int, zone_id: int, magnitude: float) -> None:
    """Create a PENDING EmergencyReport and enqueue the AI report job.

    The DB row is written first so the state machine is observable (PENDING) even
    before the dedicated AI worker processes the job. The AI worker transitions it
    to COMPLETED or FAILED and broadcasts the result over WebSocket.
    """
    zone_name = "Unknown Region"
    zone = db.query(Zone).filter(Zone.id == zone_id).first() if zone_id else None
    if zone is not None:
        zone_name = zone.city

    report = EmergencyReport(
        alert_id=alert_id,
        zone_id=zone_id,
        magnitude=magnitude,
        status="PENDING",
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    ai_payload = {
        "report_id": report.id,
        "alert_id": alert_id,
        "zone_id": zone_id,
        "zone_name": zone_name,
        "magnitude": round(magnitude, 1),
        "sensor_id": event.get("sensor_id"),
        "value": event.get("value"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    redis_sync.lpush(AI_REPORT_QUEUE, json.dumps(ai_payload))
    print(f"🤖 AI Report enqueued (report_id={report.id})", flush=True)

def run_worker():
    print("👷 Worker started. Listening for 'seismic_events'...")
    db = SessionLocal()
    
    while True:
        try:
            # Block until data is available in the queue
            result = redis_sync.brpop("seismic_events", timeout=0)
            if result:
                _, data = result
                event = json.loads(data)
                
                try:
                    process_event(event, db)
                    print(f"✅ Processed sensor {event.get('sensor_id')} -> {event.get('value')} (Mag: {estimate_magnitude(event.get('value', 0))})", flush=True)
                except Exception as e:
                    print(f"❌ DB Error: {e}. Moving to DLQ.", flush=True)
                    db.rollback()
                    redis_sync.lpush("seismic_events_dlq", data)
                    
        except Exception as e:
            print(f"❌ Redis Connection Error: {e}", flush=True)
            time.sleep(2)

if __name__ == "__main__":
    run_worker()