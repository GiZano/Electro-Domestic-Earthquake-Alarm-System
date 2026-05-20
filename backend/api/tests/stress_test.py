"""
QuakeGuard Critical Stress Test Suite v3.0 (MQTT Edition)
------------------------------------------------------------
Features:
- Massive MQTT Telemetry Firehosing (aiomqtt)
- Smart Polling for End-to-End DB Verification
- Active Security Attacks (Invalid Sig + Replay) verified via API
- Dynamic Infrastructure Provisioning (HTTP)
- IOT API Key Authentication Support
- Realistic Magnitude Spikes simulating M4.5+ events
- Redis Pub/Sub Alert Deduplication Verification
"""

import asyncio
import aiohttp
import time
import random
import os
import json
import hashlib
import redis.asyncio as aioredis
import aiomqtt
from typing import Tuple
from dataclasses import dataclass

# --- NEW CRYPTOGRAPHY IMPORTS ---
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

# --- CONFIGURATION ---
API_URL = os.getenv("API_URL", "http://localhost:8000")
IOT_API_KEY = os.getenv("IOT_API_KEY", "SuperSecretIoTKey2024")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = "quakeguard/telemetry"

NUM_SENSORS = int(os.getenv("NUM_SENSORS", 200)) 
CONCURRENCY_LIMIT = int(os.getenv("CONCURRENCY_LIMIT", 50)) 
TIMEOUT_SECONDS = 30
POLLING_RETRIES = 10 

@dataclass
class TestStats:
    req_sent: int = 0
    req_success: int = 0
    req_failed: int = 0
    auth_rejected: int = 0
    replay_rejected: int = 0
    latency_accum: float = 0.0

class VirtualSensor:
    def __init__(self):
        # Generate private key using cryptography SECP256R1 (equivalent to NIST256p)
        self.sk = ec.generate_private_key(ec.SECP256R1())
        
        # Extract the public key in DER format and convert to hex
        public_key = self.sk.public_key()
        self.public_key_hex = public_key.public_bytes(
            encoding=Encoding.DER,
            format=PublicFormat.SubjectPublicKeyInfo
        ).hex()
        
        self.sensor_id: int = 0
        # Bounding box roughly around Italy
        self.lat = round(random.uniform(36.0, 47.0), 6)
        self.lon = round(random.uniform(6.5, 18.5), 6)
        self.sent_count = 0 

    def sign_message(self, message: str) -> str:
        # Sign the message using SHA256 and convert to hex
        signature_bytes = self.sk.sign(
            message.encode('utf-8'),
            ec.ECDSA(hashes.SHA256())
        )
        return signature_bytes.hex()

class MaliciousSensor(VirtualSensor):
    def sign_with_wrong_key(self, message: str) -> str:
        # Generate a completely separate fake private key to forge the signature
        fake_sk = ec.generate_private_key(ec.SECP256R1())
        signature_bytes = fake_sk.sign(
            message.encode('utf-8'),
            ec.ECDSA(hashes.SHA256())
        )
        return signature_bytes.hex()

# --- UTILS (HTTP Provisioning) ---

async def get_test_zone(session: aiohttp.ClientSession) -> int:
    """Fetches the ID of the seeded 'Unknown Region' zone to use for load testing."""
    async with session.get(f"{API_URL}/zones/") as resp:
        if resp.status != 200: 
            raise Exception(f"Failed to fetch zones: {resp.status}")
        
        zones = await resp.json()
        fallback_zone = next((z for z in zones if z["city"] == "Unknown Region"), zones[0])
        return fallback_zone['id']

async def register_sensor(session, sensor, sem):
    async with sem:
        payload = { "active": True, "latitude": sensor.lat, "longitude": sensor.lon, "public_key_hex": sensor.public_key_hex }
        try:
            async with session.post(f"{API_URL}/misurators/", json=payload) as resp:
                if resp.status in [200, 201]:
                    data = await resp.json()
                    sensor.sensor_id = data['id']
                    return True
                
                # 💡 FIX: Print the exact error so we aren't flying blind!
                error_text = await resp.text()
                print(f"❌ Registration Failed (HTTP {resp.status}): {error_text}")
                return False
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            return False

async def get_sensor_readings(session, sensor_id: int) -> int:
    """Helper to check how many readings the backend actually persisted."""
    try:
        async with session.get(f"{API_URL}/sensors/{sensor_id}/statistics") as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("total_readings", 0)
    except: pass
    return 0

# --- MQTT PUBLISHING ---

async def publish_measurement(mqtt_client, sensor, sem, is_malicious=None) -> Tuple[bool, float]:
    if random.random() < 0.05:
        value = random.randint(5000, 15000)
    else:
        value = random.randint(100, 999)
        
    timestamp = int(time.time())
    
    if is_malicious == 'REPLAY':
        timestamp -= 7200 # 2 hours ago

    message = f"{value}:{timestamp}"
    
    if is_malicious == 'BAD_SIG':
        signature = sensor.sign_with_wrong_key(message)
    else:
        signature = sensor.sign_message(message)

    payload = { "value": value, "misurator_id": sensor.sensor_id, "device_timestamp": timestamp, "signature_hex": signature }

    start_t = time.perf_counter()
    async with sem:
        try:
            # Publish payload to broker with QoS 1 (Guaranteed delivery to Mosquitto)
            await mqtt_client.publish(MQTT_TOPIC, payload=json.dumps(payload), qos=1)
            return True, time.perf_counter() - start_t
        except Exception:
            return False, 0.0

# --- BACKGROUND TASKS ---

async def listen_for_alerts(stop_event: asyncio.Event) -> int:
    try:
        redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
        pubsub = redis.pubsub()
        await pubsub.subscribe("quake_alerts")
        
        alert_count = 0
        while not stop_event.is_set():
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
            if msg:
                alert_count += 1
                print(f"   🔔 Intercepted Alert from worker: {msg['data']}")
                
        await pubsub.unsubscribe()
        await redis.aclose()
        return alert_count
    except Exception as e:
        print(f"   ⚠️ Redis Listener failed: {e}")
        return 0

# --- PHASES ---

async def run_load_test(mqtt_client, sensors, sem) -> TestStats:
    stats = TestStats()
    print(f"🔥 Phase 1: MQTT Firehose ({len(sensors)} sensors publishing)...")
    tasks = []
    
    for s in sensors:
        tasks.append(publish_measurement(mqtt_client, s, sem))
        s.sent_count += 1 
        # Pace the requests to ~40 per second to avoid triggering rate limiter in the Bridge
        await asyncio.sleep(0.025)

    results = await asyncio.gather(*tasks)
    for success, latency in results:
        stats.req_sent += 1
        stats.latency_accum += latency
        if success: stats.req_success += 1
        else: stats.req_failed += 1
            
    return stats

async def run_security_test(session, mqtt_client, sem) -> TestStats:
    stats = TestStats()
    print("\n⚔️  Phase 2: Security Attacks (Verifying via Backend DB)...")
    bad_sensor = MaliciousSensor()
    await register_sensor(session, bad_sensor, sem)
    
    # Attack A: Bad Sig
    print("   👉 A: Bad Signature...", end=" ")
    await publish_measurement(mqtt_client, bad_sensor, sem, is_malicious='BAD_SIG')
    await asyncio.sleep(2) # Give bridge/worker time to process and reject
    
    readings = await get_sensor_readings(session, bad_sensor.sensor_id)
    if readings == 0: 
        print("✅ Blocked (Dropped by backend)")
        stats.auth_rejected += 1
    else: print("💀 FAILED (Backend persisted invalid signature)")

    # Attack B: Replay
    print("   👉 B: Replay Attack...", end=" ")
    await publish_measurement(mqtt_client, bad_sensor, sem, is_malicious='REPLAY')
    await asyncio.sleep(2)
    
    readings = await get_sensor_readings(session, bad_sensor.sensor_id)
    if readings == 0: 
        print("✅ Blocked (Dropped by backend)")
        stats.replay_rejected += 1
    else: print("💀 FAILED (Backend persisted replay attack)")
    
    return stats

async def verify_persistence_with_polling(session, sensors) -> bool:
    print(f"\n🔍 Phase 3: E2E Verification (Polling Worker)...")
    
    test_sensor = next((s for s in sensors if s.sensor_id > 0 and s.sent_count > 0), None)
    if not test_sensor:
        print("   ❌ E2E Failed: No valid sensors found with sent data to verify.")
        return False
        
    print(f"   👉 Tracking Sensor ID {test_sensor.sensor_id} (Expected readings: {test_sensor.sent_count})")
    
    for attempt in range(POLLING_RETRIES):
        readings = await get_sensor_readings(session, test_sensor.sensor_id)
        if readings >= test_sensor.sent_count:
            print(f"   ✅ DB Confirmed! All {test_sensor.sent_count} reading(s) securely persisted.")
            return True
        else:
            print(f"   ⏳ Worker processing... {readings}/{test_sensor.sent_count} (Attempt {attempt+1}/{POLLING_RETRIES})")
        await asyncio.sleep(1)
        
    print("   ❌ Polling timed out. Redis Worker may be down or slow.")
    return False

# --- MAIN ---

async def main():
    print(f"🚀 QUAKEGUARD CRITICAL TEST v3.0 (MQTT)")
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    headers = {"X-API-Key": IOT_API_KEY}
    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with aiomqtt.Client(hostname=MQTT_BROKER, port=MQTT_PORT) as mqtt_client:
            
            # Setup
            try:
                sensors = [VirtualSensor() for _ in range(NUM_SENSORS)]
                await asyncio.gather(*[register_sensor(session, s, sem) for s in sensors])
                print(f"📝 Registered {NUM_SENSORS} sensors via Spatial Auto-Assignment.")
            except Exception as e:
                print(f"❌ Setup Failed: {e}")
                return

            # Start Redis Alert Listener for Deduplication checking
            stop_listener = asyncio.Event()
            listener_task = asyncio.create_task(listen_for_alerts(stop_listener))

            # Execution
            load_stats = await run_load_test(mqtt_client, sensors, sem)
            
            # Wait a moment to ensure all alerts propagate, then stop listener
            await asyncio.sleep(2)
            stop_listener.set()
            total_alerts_published = await listener_task
            
            print("\n⏳ Letting Redis Rate Limiter cool down for 10 seconds...")
            await asyncio.sleep(10)
            
            sec_stats = await run_security_test(session, mqtt_client, sem)
            
            # End-to-End Test Execution
            e2e_passed = await verify_persistence_with_polling(session, sensors)

    # Report
    print("\n" + "="*40)
    print("📊 MISSION REPORT")
    print("="*40)
    print(f"MQTT Publish:   {load_stats.req_success}/{load_stats.req_sent} ACK'd by Broker")
    print(f"Sec (BadSig): {sec_stats.auth_rejected} Blocked")
    print(f"Sec (Replay): {sec_stats.replay_rejected} Blocked")
    print(f"Alerts Fired: {total_alerts_published} (Expected deduplication: 1)")
    
    persistence_str = "✅ VERIFIED" if e2e_passed else "❌ FAILED"
    print(f"Persistence:  {persistence_str}")
    print("="*40)

    if sec_stats.auth_rejected > 0 and sec_stats.replay_rejected > 0 and e2e_passed and total_alerts_published <= 1:
        print("🏆 SYSTEM CERTIFIED")
    else:
        print("⚠️ SYSTEM FAILURE (Check deduplication logs if Alerts Fired > 1)")

if __name__ == "__main__":
    try:
        import sys
        if sys.platform == 'win32': asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except: pass
    asyncio.run(main())