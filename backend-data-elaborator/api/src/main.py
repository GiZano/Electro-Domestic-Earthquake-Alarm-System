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

from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from sqlalchemy.exc import OperationalError
from redis import asyncio as aioredis
from geoalchemy2.elements import WKTElement

# --- LOCAL MODULES ---
from src.database import get_db, engine, SessionLocal
import src.models as models
import src.schemas as schemas
from src.security import verify_api_key, validate_iot_payload
from src.seed import seed_zones

# --- SECURE CONFIGURATION ---
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

MOBILE_WS_TOKEN = os.getenv("MOBILE_WS_TOKEN")
if not MOBILE_WS_TOKEN:
    raise RuntimeError("🚨 CRITICAL STARTUP ERROR: 'MOBILE_WS_TOKEN' environment variable is not set!")

ENROLLMENT_TOKEN = os.getenv("ENROLLMENT_TOKEN")
if not ENROLLMENT_TOKEN:
    raise RuntimeError("🚨 CRITICAL STARTUP ERROR: 'ENROLLMENT_TOKEN' environment variable is not set!")

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

wait_for_db()
models.Base.metadata.create_all(bind=engine)
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
    with SessionLocal() as db:
        seed_zones(db)
        
    listener_task = asyncio.create_task(redis_alert_listener())
    yield
    listener_task.cancel()

# Initialize FastAPI
app = FastAPI(title="QuakeGuard Backend", version="2.2.0", lifespan=lifespan)

# ==========================================
# MIDDLEWARE
# ==========================================

async def rate_limiter(request: Request):
    """Fixed-window rate limiter using Redis."""
    client_ip = request.client.host
    current_second = int(time.time())
    key = f"rate_limit:{client_ip}:{current_second}"
    
    request_count = await redis_client.incr(key)
    if request_count == 1:
        await redis_client.expire(key, 5) 
        
    if request_count > 50:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Too many requests from this IP."
        )

def resolve_zone(db: Session, latitude: float, longitude: float) -> int:
    """
    Spatial auto-assignment helper.
    Finds the smallest containing polygon for given GPS coordinates.
    Falls back to 'Unknown Region' if no match is found.
    """
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
    loop = asyncio.get_running_loop()

    # 1. Define discrete async checks with error logging
    async def check_postgres():
        try:
            await loop.run_in_executor(None, ping_db)
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

@app.post("/misurators/", response_model=schemas.Misurator, status_code=status.HTTP_201_CREATED, tags=["Registration"])
def create_misurator(misurator: schemas.MisuratorCreate, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    existing = db.query(models.Misurator).filter(models.Misurator.public_key_hex == misurator.public_key_hex).first()
    if existing:
        return existing

    # 🌍 SPATIAL AUTO-ASSIGNMENT LOGIC (Refactored)
    assigned_zone_id = misurator.zone_id or resolve_zone(db, misurator.latitude, misurator.longitude)

    gps_point = f"POINT({misurator.longitude} {misurator.latitude})"
    db_misurator = models.Misurator(
        active=misurator.active, 
        zone_id=assigned_zone_id,
        latitude=misurator.latitude, 
        longitude=misurator.longitude,
        location=WKTElement(gps_point, srid=4326), 
        public_key_hex=misurator.public_key_hex
    )
    db.add(db_misurator)
    db.commit()
    db.refresh(db_misurator)
    return db_misurator

@app.post("/devices/register", status_code=status.HTTP_201_CREATED, tags=["Provisioning"])
def register_device(payload: schemas.DeviceRegisterRequest, db: Session = Depends(get_db)):
    """Automated Device Handshake with Spatial Zone Assignment."""
    if payload.enrollment_token != ENROLLMENT_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid enrollment token")

    existing = db.query(models.Misurator).filter(
        (models.Misurator.mac_address == payload.mac_address) |
        (models.Misurator.public_key_hex == payload.public_key_hex)
    ).first()

    if existing:
        return {"sensor_id": existing.id}

    # 🌍 SPATIAL AUTO-ASSIGNMENT LOGIC (Refactored)
    assigned_zone_id = resolve_zone(db, payload.latitude, payload.longitude)
    point = WKTElement(f"POINT({payload.longitude} {payload.latitude})", srid=4326)

    new_device = models.Misurator(
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

@app.get("/misurators/", response_model=List[schemas.Misurator], tags=["Data Retrieval"])
def get_misurators(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    return db.query(models.Misurator).offset(skip).limit(limit).all()

@app.post("/misurations/", status_code=status.HTTP_202_ACCEPTED, tags=["Ingestion"], dependencies=[Depends(rate_limiter)])
async def create_misuration_async(
    # 💡 MAGIC HAPPENS HERE: validate_iot_payload handles all cryptography, replay checks, and API Key checks!
    valid_data: dict = Depends(validate_iot_payload)
):
    # Extract the validated objects returned from our security module
    misuration = valid_data["misuration"]
    misurator = valid_data["misurator"]
    
    # Enqueue for Worker
    payload = misuration.model_dump()
    payload['zone_id'] = misurator.zone_id
    
    # Offload to the Redis queue
    await redis_client.lpush("seismic_events", json.dumps(payload))
    return {"status": "accepted"}

@app.get("/sensors/{id}/statistics", tags=["Data Retrieval"])
def get_sensor_statistics(id: int, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    count = db.query(models.Misuration).filter(models.Misuration.misurator_id == id).count()
    return {
        "sensor_id": id,
        "total_readings": count
    }

@app.get("/misurations/", response_model=List[schemas.Misuration], tags=["Data Retrieval"])
def get_misurations(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    """
    Fetch recent sensor readings. 
    Used primarily by the frontend dashboard to render the live seismograph.
    """
    return db.query(models.Misuration).order_by(models.Misuration.recorded_at.desc()).offset(skip).limit(limit).all()