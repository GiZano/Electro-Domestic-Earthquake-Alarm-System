"""
QuakeGuard Backend Service API
-------------------------------
Core API Gateway.
Responsibilities:
1. IoT Data Ingestion.
2. Data Retrieval (REST).
3. Real-Time Alert Distribution (Redis Pub/Sub -> WebSocket).
"""

import json
import asyncio
import time
import os
from typing import List
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from urllib.parse import urlparse

import asyncpg
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from sqlalchemy.exc import OperationalError
from redis import asyncio as aioredis
from geoalchemy2.elements import WKTElement

# --- LOCAL MODULES ---
from src.database import get_db, engine, SessionLocal, DATABASE_URL
import src.models as models
import src.schemas as schemas
from src.security import verify_api_key, validate_iot_payload
from src.seed import seed_zones

# --- SECURE CONFIGURATION ---
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

MOBILE_WS_TOKEN = os.getenv("MOBILE_WS_TOKEN")
if not MOBILE_WS_TOKEN or len(MOBILE_WS_TOKEN) < 8:
    raise RuntimeError("🚨 CRITICAL STARTUP ERROR: 'MOBILE_WS_TOKEN' environment variable is not set or too short (min 8 chars)!")

ENROLLMENT_TOKEN = os.getenv("ENROLLMENT_TOKEN")
if not ENROLLMENT_TOKEN or len(ENROLLMENT_TOKEN) < 8:
    raise RuntimeError("🚨 CRITICAL STARTUP ERROR: 'ENROLLMENT_TOKEN' environment variable is not set or too short (min 8 chars)!")

# ==========================================
# INFRASTRUCTURE INITIALIZATION
# ==========================================

def wait_for_db(retries: int = 10, delay: int = 3) -> None:
    print("Checking Database connection...")
    for i in range(retries):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            print("✅ Database is up and running!")
            return
        except OperationalError:
            print(f"⏳ Waiting for DB... ({i+1}/{retries})")
            time.sleep(delay)
    raise Exception("❌ DB Connection Failed after multiple retries.")

def ping_db() -> None:
    """Synchronous helper to ping the PostgreSQL database."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)

# ==========================================
# REAL-TIME NOTIFICATION SYSTEM (PUBSUB)
# ==========================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"📱 Client Connected. Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"📱 Client Disconnected. Active: {len(self.active_connections)}")

    async def broadcast(self, message: str) -> None:
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"⚠️ Failed to broadcast to a client: {e}")
                dead_connections.append(connection)
                
        for dead in dead_connections:
            self.disconnect(dead)

manager = ConnectionManager()

async def redis_alert_listener() -> None:
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("quake_alerts")
    print("🎧 Redis Pub/Sub Listener active on channel: 'quake_alerts'")

    async for message in pubsub.listen():
        if message["type"] == "message":
            alert_payload = message["data"]
            await manager.broadcast(alert_payload)

@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, wait_for_db)
    await loop.run_in_executor(None, lambda: models.Base.metadata.create_all(bind=engine))

    db = SessionLocal()
    try:
        seed_zones(db)
    finally:
        db.close()

    listener_task = asyncio.create_task(redis_alert_listener())
    yield
    listener_task.cancel()

# Initialize FastAPI
app = FastAPI(title="QuakeGuard Backend", version="2.2.0", lifespan=lifespan)

# ==========================================
# MIDDLEWARE
# ==========================================

async def rate_limiter(request: Request):
    """Sliding-window rate limiter using Redis sorted sets. Uses X-Forwarded-For if behind proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    client_ip = forwarded.split(",")[0].strip() if forwarded else request.client.host
    now = time.time()
    window = 1.0
    key = f"rate_limit:{client_ip}"
    
    # Remove entries outside the window and add current timestamp
    await redis_client.zremrangebyscore(key, 0, now - window)
    await redis_client.zadd(key, {str(now): now})
    await redis_client.expire(key, 60)
    
    request_count = await redis_client.zcard(key)
        
    if request_count > 50:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Too many requests from this IP."
        )

def resolve_zone(db: Session, latitude: float | None, longitude: float | None) -> int:
    """
    Spatial auto-assignment helper.
    Finds the smallest containing polygon for given GPS coordinates.
    Falls back to 'Unknown Region' if no match is found or coordinates are null.
    """
    if latitude is None or longitude is None:
        fallback = db.query(models.Zone).filter(models.Zone.city == "Unknown Region").first()
        return fallback.id if fallback else 1

    point = WKTElement(f"POINT({longitude} {latitude})", srid=4326)
    
    # Query PostGIS to find the containing polygon, ordered by smallest area first
    matched_zone = db.query(models.Zone).filter(
        func.ST_Contains(models.Zone.geom, point)
    ).order_by(func.ST_Area(models.Zone.geom).asc()).first()

    if matched_zone:
        return matched_zone.id
        
    # Fallback to Unknown Region
    fallback = db.query(models.Zone).filter(models.Zone.city == "Unknown Region").first()
    return fallback.id if fallback else 1 # Final failsafe

# ==========================================
# WEBSOCKET ENDPOINT
# ==========================================

@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if token != MOBILE_WS_TOKEN:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, Exception):
        manager.disconnect(websocket)

# ==========================================
# REST API ENDPOINTS
# ==========================================

# --- HEALTH CHECK ---
@app.get("/health", tags=["Observability"])
async def health_check():
    """
    Infrastructure Observability Endpoint.
    Pings PostgreSQL and Redis concurrently to verify full system health.
    """
    health_status = {
        "status": "ok",
        "postgres": "connected",
        "redis": "connected"
    }
    http_status_code = status.HTTP_200_OK

    # 1. Define discrete async checks with error logging
    async def check_postgres():
        try:
            parsed = urlparse(DATABASE_URL)
            conn = await asyncpg.connect(
                host=parsed.hostname or "localhost",
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path.lstrip("/"),
            )
            await conn.execute("SELECT 1")
            await conn.close()
            return True
        except Exception as e:
            print(f"❌ Health Check - Postgres Error: {e}", flush=True)
            return False

    async def check_redis():
        try:
            await redis_client.ping()
            return True
        except Exception as e:
            print(f"❌ Health Check - Redis Error: {e}", flush=True)
            return False

    # 2. Execute checks concurrently
    pg_ok, redis_ok = await asyncio.gather(check_postgres(), check_redis())

    # 3. Evaluate results
    if not pg_ok:
        health_status["status"] = "error"
        health_status["postgres"] = "disconnected"
        http_status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    if not redis_ok:
        health_status["status"] = "error"
        health_status["redis"] = "disconnected"
        http_status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    if http_status_code != status.HTTP_200_OK:
        return JSONResponse(status_code=http_status_code, content=health_status)
        
    return health_status

@app.post("/demo/trigger-earthquake", status_code=status.HTTP_200_OK, tags=["Demo"])
async def trigger_demo_earthquake(
    payload: schemas.DemoAlertRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Instantly triggers a simulated CRITICAL earthquake alert.
    Bypasses the IoT ingestion pipeline and broadcasts directly to all connected WebSocket clients.
    """
    # Construct the exact payload format expected by the frontend WebSocketContext
    alert_data = {
        "type": "CRITICAL",
        "zone_id": payload.zone_id,
        "magnitude": payload.magnitude,
        "message": payload.message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Publish directly to the Redis Pub/Sub channel
    await redis_client.publish("quake_alerts", json.dumps(alert_data))

    return {
        "status": "success",
        "detail": "Demo alert broadcasted successfully",
        "payload": alert_data
    }

@app.post("/zones/", response_model=schemas.Zone, status_code=status.HTTP_201_CREATED, tags=["Registration"])
def create_zone(zone: schemas.ZoneCreate, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    existing = db.query(models.Zone).filter(models.Zone.city == zone.city).first()
    if existing:
        return existing 
        
    db_zone = models.Zone(city=zone.city)
    db.add(db_zone)
    db.commit()
    db.refresh(db_zone)
    return db_zone

@app.get("/zones/", response_model=List[schemas.Zone], tags=["Data Retrieval"])
def get_zones(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    return db.query(models.Zone).offset(skip).limit(limit).all()

@app.post("/sensors/", response_model=schemas.Sensor, status_code=status.HTTP_201_CREATED, tags=["Registration"])
def create_sensor(sensor: schemas.SensorCreate, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    existing = db.query(models.Sensor).filter(models.Sensor.public_key_hex == sensor.public_key_hex).first()
    if existing:
        return existing

    # 🌍 SPATIAL AUTO-ASSIGNMENT LOGIC (Refactored)
    assigned_zone_id = sensor.zone_id or resolve_zone(db, sensor.latitude, sensor.longitude)

    gps_point = f"POINT({sensor.longitude} {sensor.latitude})"
    db_sensor = models.Sensor(
        active=sensor.active, 
        zone_id=assigned_zone_id,
        latitude=sensor.latitude, 
        longitude=sensor.longitude,
        location=WKTElement(gps_point, srid=4326), 
        public_key_hex=sensor.public_key_hex
    )
    db.add(db_sensor)
    db.commit()
    db.refresh(db_sensor)
    return db_sensor

@app.post("/devices/register", status_code=status.HTTP_201_CREATED, tags=["Provisioning"])
def register_device(payload: schemas.DeviceRegisterRequest, db: Session = Depends(get_db)):
    """Automated Device Handshake with Spatial Zone Assignment."""
    if payload.enrollment_token != ENROLLMENT_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid enrollment token")

    existing = db.query(models.Sensor).filter(
        (models.Sensor.mac_address == payload.mac_address) |
        (models.Sensor.public_key_hex == payload.public_key_hex)
    ).first()

    if existing:
        return {"sensor_id": existing.id}

    # 🌍 SPATIAL AUTO-ASSIGNMENT LOGIC (Refactored)
    assigned_zone_id = resolve_zone(db, payload.latitude, payload.longitude)
    point = WKTElement(f"POINT({payload.longitude} {payload.latitude})", srid=4326)

    new_device = models.Sensor(
        active=True,
        zone_id=assigned_zone_id,
        latitude=payload.latitude, 
        longitude=payload.longitude, 
        location=point,
        public_key_hex=payload.public_key_hex,
        mac_address=payload.mac_address
    )
    
    db.add(new_device)
    db.commit()
    db.refresh(new_device)

    return {"sensor_id": new_device.id}

@app.get("/sensors/", response_model=List[schemas.Sensor], tags=["Data Retrieval"])
def get_sensors(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    return db.query(models.Sensor).offset(skip).limit(limit).all()

@app.post("/readings/", status_code=status.HTTP_202_ACCEPTED, tags=["Ingestion"], dependencies=[Depends(rate_limiter)])
async def create_reading_async(
    # 💡 MAGIC HAPPENS HERE: validate_iot_payload handles all cryptography, replay checks, and API Key checks!
    valid_data: dict = Depends(validate_iot_payload)
):
    # Extract the validated objects returned from our security module
    reading = valid_data["reading"]
    sensor = valid_data["sensor"]
    
    # Enqueue for Worker
    payload = reading.model_dump()
    payload['zone_id'] = sensor.zone_id
    
    # Offload to the Redis queue
    await redis_client.lpush("seismic_events", json.dumps(payload))
    return {"status": "accepted"}

@app.get("/sensors/{id}/statistics", tags=["Data Retrieval"])
def get_sensor_statistics(id: int, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    count = db.query(models.Reading).filter(models.Reading.sensor_id == id).count()
    return {
        "sensor_id": id,
        "total_readings": count
    }

@app.get("/readings/", response_model=List[schemas.Reading], tags=["Data Retrieval"])
def get_readings(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    """
    Fetch recent sensor readings. 
    Used primarily by the frontend dashboard to render the live seismograph.
    """
    return db.query(models.Reading).order_by(models.Reading.recorded_at.desc()).offset(skip).limit(limit).all()