import os
import json
import time
import math
from datetime import datetime, timezone
import redis
from sqlalchemy.orm import Session
from src.database import SessionLocal, engine
from src.models import Misuration

# Redis Config
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_sync = redis.from_url(REDIS_URL, decode_responses=True)

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
    return round(max(0.0, min(magnitude, 9.9)), 1)

def process_event(event: dict, db: Session):
    """Inserts a single sensor measurement into PostGIS and triggers alerts."""
    
    # 1. Save to Database
    new_entry = Misuration(
        value=event.get("value"),
        misurator_id=event.get("misurator_id")
    )
    db.add(new_entry)
    db.commit()

    # 2. 🚨 ALARM LOGIC: Check if threshold is breached
    sensor_value = event.get("value", 0)
    magnitude = estimate_magnitude(sensor_value)
    
    # Trigger a CRITICAL alert if physical magnitude is 4.5 or higher
    if magnitude >= 4.5:
        # Create the exact JSON schema the Mobile App is expecting
        alert_payload = {
            "type": "CRITICAL",
            "zone_id": event.get("zone_id", 0),
            "magnitude": magnitude,
            "message": f"High seismic activity detected (Sensor {event.get('misurator_id')})!",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Publish to the channel that FastAPI is listening to
        redis_sync.publish("quake_alerts", json.dumps(alert_payload))
        print(f"🚨 ALERT PUBLISHED: Zone {event.get('zone_id')} - Mag {alert_payload['magnitude']}", flush=True)

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
                    print(f"✅ Processed sensor {event.get('misurator_id')} -> {event.get('value')} (Mag: {estimate_magnitude(event.get('value', 0))})", flush=True)
                except Exception as e:
                    print(f"❌ DB Error: {e}. Moving to DLQ.", flush=True)
                    db.rollback()
                    redis_sync.lpush("seismic_events_dlq", data)
                    
        except Exception as e:
            print(f"❌ Redis Connection Error: {e}", flush=True)
            time.sleep(2)

if __name__ == "__main__":
    run_worker()