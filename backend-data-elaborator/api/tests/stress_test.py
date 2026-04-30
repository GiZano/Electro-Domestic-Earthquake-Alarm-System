"""
QuakeGuard Critical Stress Test Suite v2.4
------------------------------------------------------------
Features:
- Client-side Semaphore Throttling
- Smart Polling for End-to-End DB Verification
- Active Security Attacks (Invalid Sig + Replay)
- Dynamic Infrastructure
- IoT API Key Authentication Support
- Paced requests to respect Server Rate Limits
- Realistic Magnitude Spikes simulating M4.5+ events
- Redis Pub/Sub Alert Deduplication Verification
"""

import asyncio
import aiohttp
import time
import random
import os
import uuid
import hashlib
import redis.asyncio as aioredis
from typing import List, Tuple
from dataclasses import dataclass

from ecdsa import SigningKey, NIST256p
from ecdsa.util import sigencode_der

# --- CONFIGURATION ---
API_URL = os.getenv("API_URL", "http://localhost:8000")
IOT_API_KEY = os.getenv("IOT_API_KEY", "SuperSecretIoTKey2024")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
NUM_SENSORS = int(os.getenv("NUM_SENSORS", 200)) 
CONCURRENCY_LIMIT = int(os.getenv("CONCURRENCY_LIMIT", 50)) 
TIMEOUT_SECONDS = 30
POLLING_RETRIES = 10 # Max seconds to wait for worker persistence

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
        self.sk = SigningKey.generate(curve=NIST256p)
        self.vk = self.sk.verifying_key
        self.public_key_hex = self.vk.to_der().hex()
        self.sensor_id: int = 0
        self.lat = round(random.uniform(-90, 90), 6)
        self.lon = round(random.uniform(-180, 180), 6)
        self.sent_count = 0 

    def sign_message(self, message: str) -> str:
        return self.sk.sign(message.encode('utf-8'), hashfunc=hashlib.sha256, sigencode=sigencode_der).hex()

class MaliciousSensor(VirtualSensor):
    def sign_with_wrong_key(self, message: str) -> str:
        fake_sk = SigningKey.generate(curve=NIST256p)
        return fake_sk.sign(message.encode('utf-8'), hashfunc=hashlib.sha256, sigencode=sigencode_der).hex()

# --- UTILS ---

async def create_dynamic_zone(session: aiohttp.ClientSession) -> int:
    city_name = f"TestZone_{uuid.uuid4().hex[:8]}"
    async with session.post(f"{API_URL}/zones/", json={"city": city_name}) as resp:
        if resp.status not in [200, 201]: raise Exception(f"Zone creation failed: {resp.status}")
        data = await resp.json()
        return data['id']

async def register_sensor(session, sensor, zone_id, sem):
    async with sem:
        payload = { "active": True, "zone_id": zone_id, "latitude": sensor.lat, "longitude": sensor.lon, "public_key_hex": sensor.public_key_hex }
        try:
            async with session.post(f"{API_URL}/misurators/", json=payload) as resp:
                if resp.status in [200, 201]:
                    data = await resp.json()
                    sensor.sensor_id = data['id']
                    return True
                return False
        except: return False

async def send_measurement(session, sensor, sem, is_malicious=None) -> Tuple[int, float]:
    
    # 5% chance of a massive seismic event (M4.5 - M5.0+)
    if random.random() < 0.05:
        value = random.randint(5000, 15000)
    else:
        value = random.randint(100, 999)
        
    timestamp = int(time.time())
    
    if is_malicious == 'REPLAY':
        timestamp -= 7200 # 2 hours ago (Ancient History)

    message = f"{value}:{timestamp}"
    
    if is_malicious == 'BAD_SIG':
        signature = sensor.sign_with_wrong_key(message)
    else:
        signature = sensor.sign_message(message)

    payload = { "value": value, "misurator_id": sensor.sensor_id, "device_timestamp": timestamp, "signature_hex": signature }

    start_t = time.perf_counter()
    async with sem:
        try:
            async with session.post(f"{API_URL}/misurations/", json=payload, timeout=TIMEOUT_SECONDS) as resp:
                await resp.read()
                return resp.status, time.perf_counter() - start_t
        except Exception:
            return 999, 0.0

# --- BACKGROUND TASKS ---

async def listen_for_alerts(stop_event: asyncio.Event) -> int:
    """Background task to count alerts published to Redis Pub/Sub."""
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
        print(f"   ⚠️ Redis Listener failed (is Redis running at {REDIS_URL}?): {e}")
        return 0

# --- PHASES ---

async def run_load_test(session, sensors, sem) -> TestStats:
    stats = TestStats()
    print(f"🔥 Phase 1: Firehose ({len(sensors)} concurrent requests)...")
    tasks = []
    for s in sensors:
        tasks.append(send_measurement(session, s, sem))
        s.sent_count += 1 
        
        # Pace the requests to ~40 per second to avoid triggering our new 50 req/sec Rate Limiter
        await asyncio.sleep(0.025)

    results = await asyncio.gather(*tasks)
    for status_code, latency in results:
        stats.req_sent += 1
        stats.latency_accum += latency
        if status_code == 202: stats.req_success += 1
        else: 
            stats.req_failed += 1
            if status_code == 429:
                pass # Expected if timing gets bunched up
    return stats

async def run_security_test(session, zone_id, sem) -> TestStats:
    stats = TestStats()
    print("\n⚔️  Phase 2: Security Attacks...")
    bad_sensor = MaliciousSensor()
    await register_sensor(session, bad_sensor, zone_id, sem)
    
    # Attack A: Bad Sig
    print("   👉 A: Bad Signature...", end=" ")
    status_a, _ = await send_measurement(session, bad_sensor, sem, is_malicious='BAD_SIG')
    if status_a == 401: 
        print("✅ Blocked (401)")
        stats.auth_rejected += 1
    else: print(f"💀 FAILED (Got {status_a})")

    # Attack B: Replay
    print("   👉 B: Replay Attack...", end=" ")
    status_b, _ = await send_measurement(session, bad_sensor, sem, is_malicious='REPLAY')
    if status_b == 403: 
        print("✅ Blocked (403)")
        stats.replay_rejected += 1
    else: print(f"💀 FAILED (Got {status_b})")
    
    return stats

async def verify_persistence_with_polling(session, sensors, sem) -> bool:
    print(f"\n🔍 Phase 3: E2E Verification (Polling Worker)...")
    
    # 1. Robust Selection: Find a sensor that successfully registered AND sent data
    test_sensor = next((s for s in sensors if s.sensor_id > 0 and s.sent_count > 0), None)
    
    if not test_sensor:
        print("   ❌ E2E Failed: No valid sensors found with sent data to verify.")
        return False
        
    print(f"   👉 Tracking Sensor ID {test_sensor.sensor_id} (Expected readings: {test_sensor.sent_count})")
    
    for attempt in range(POLLING_RETRIES):
        async with sem:  
            try:
                async with session.get(f"{API_URL}/sensors/{test_sensor.sensor_id}/statistics") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        readings = data.get("total_readings", 0)
                        
                        if readings >= test_sensor.sent_count:
                            print(f"   ✅ DB Confirmed! All {test_sensor.sent_count} reading(s) securely persisted.")
                            return True
                        else:
                            print(f"   ⏳ Worker processing... {readings}/{test_sensor.sent_count} (Attempt {attempt+1}/{POLLING_RETRIES})")
                    else:
                        print(f"   ⚠️ API Error: Expected 200, got {resp.status}")
                        return False
            except Exception as e:
                print(f"   ⚠️ Connection Error: {e}")
                
        await asyncio.sleep(1)
        
    print("   ❌ Polling timed out. Redis Worker may be down or slow.")
    return False

# --- MAIN ---

async def main():
    print(f"🚀 QUAKEGUARD CRITICAL TEST v2.4")
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)

    headers = {"X-API-Key": IOT_API_KEY}
    
    async with aiohttp.ClientSession(headers=headers) as session:
        # Setup
        try:
            zone_id = await create_dynamic_zone(session)
            sensors = [VirtualSensor() for _ in range(NUM_SENSORS)]
            await asyncio.gather(*[register_sensor(session, s, zone_id, sem) for s in sensors])
            print(f"📝 Registered {NUM_SENSORS} sensors.")
        except Exception as e:
            print(f"❌ Setup Failed: {e}")
            return

        # Start Redis Alert Listener for Deduplication checking
        stop_listener = asyncio.Event()
        listener_task = asyncio.create_task(listen_for_alerts(stop_listener))

        # Execution
        load_stats = await run_load_test(session, sensors, sem)
        
        # Wait a moment to ensure all alerts propagate, then stop listener
        await asyncio.sleep(2)
        stop_listener.set()
        total_alerts_published = await listener_task
        
        print("\n⏳ Letting Redis Rate Limiter cool down for 10 seconds...")
        await asyncio.sleep(10)
        
        sec_stats = await run_security_test(session, zone_id, sem)
        
        # End-to-End Test Execution
        e2e_passed = await verify_persistence_with_polling(session, sensors, sem)

    # Report
    print("\n" + "="*40)
    print("📊 MISSION REPORT")
    print("="*40)
    print(f"Traffic:      {load_stats.req_success}/{load_stats.req_sent} Accepted")
    print(f"Sec (BadSig): {sec_stats.auth_rejected} Blocked")
    print(f"Sec (Replay): {sec_stats.replay_rejected} Blocked")
    print(f"Alerts Fired: {total_alerts_published} (Expected deduplication: 1)")
    
    # Update Report to reflect E2E status
    persistence_str = "✅ VERIFIED" if e2e_passed else "❌ FAILED"
    print(f"Persistence:  {persistence_str}")
    print("="*40)

    # Must pass security, persistence, AND deduplication (<= 1 alert) to be certified!
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