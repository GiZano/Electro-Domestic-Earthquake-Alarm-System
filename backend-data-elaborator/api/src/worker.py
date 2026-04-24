import os
import json
import time
from datetime import datetime, timezone
import redis
from sqlalchemy.orm import Session
from src.database import SessionLocal, engine
from src.models import Misuration

# Redis Config
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_sync = redis.from_url(REDIS_URL, decode_responses=True)

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
    # The stress test sends random values between 100 and 999.
    # Let's trigger a CRITICAL alert if a reading exceeds 850.
    sensor_value = event.get("value", 0)
    
    if sensor_value > 850:
        # Create the exact JSON schema the Mobile App is expecting
        alert_payload = {
            "type": "CRITICAL",
            "zone_id": event.get("zone_id", 0),
            "magnitude": round(sensor_value / 100, 1), # Faux magnitude calculation (e.g. 8.5)
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
                    print(f"✅ Processed sensor {event.get('misurator_id')} -> {event.get('value')}", flush=True)
                except Exception as e:
                    print(f"❌ DB Error: {e}. Moving to DLQ.", flush=True)
                    db.rollback()
                    redis_sync.lpush("seismic_events_dlq", data)
                    
        except Exception as e:
            print(f"❌ Redis Connection Error: {e}", flush=True)
            time.sleep(2)

if __name__ == "__main__":
    run_worker()