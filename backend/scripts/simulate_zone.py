"""
QuakeGuard Zone Demo Simulator
------------------------------
Injects a 20-second stream of (signed) telemetry into the live pipeline for a
given zone, ending with an earthquake ramp that crosses the CRITICAL threshold
(~M4.7+) so the dashboard seismograph and the alert websocket come to life.

How it works:
1. Ensures the target zone exists (POST /zones/).
2. Registers a throwaway ECDSA (NIST P-256) sensor pinned to that zone.
3. Streams 20 samples (1/sec): random noise, then a seismic ramp spike.
Each reading is signed exactly like the firmware does
(signature over "value:timestamp") and POSTed to the /readings/ ingestion API.

Run inside the backend container (has requests + cryptography + IOT_API_KEY):
    docker cp scripts/simulate_zone.py backend-fastapi-app-1:/tmp/
    docker exec backend-fastapi-app-1 python /tmp/simulate_zone.py
"""

import os
import time
import math
import random
import json

import requests
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

API_URL = os.getenv("API_URL", "http://localhost:8000")
IOT_API_KEY = os.getenv("IOT_API_KEY", "")
ZONE_NAME = os.getenv("ZONE_NAME", "TEST ZONE")
SENSOR_LAT = float(os.getenv("SENSOR_LAT", "41.9028"))
SENSOR_LON = float(os.getenv("SENSOR_LON", "12.4964"))
DURATION_SECONDS = int(os.getenv("DURATION_SECONDS", "20"))


def normalize(name: str) -> str:
    """'ZONE A - TEST' / 'A-TEST' / 'a test' all collapse to the same key."""
    return name.replace("-", "").replace("_", "").replace(" ", "").lower()

B_OFFSET = 3.0
K_CALIBRATION = 1.6
SENSOR_SCALE = 100.0


def estimate_magnitude(value: int) -> float:
    """Same M_IoT formula as the backend worker (for the printout only)."""
    pga = value / SENSOR_SCALE / K_CALIBRATION
    if pga <= 0:
        return 0.0
    return max(0.0, min(math.log10(pga) + B_OFFSET, 9.9))


def _magnitude_flag(mag: float) -> str:
    """Return the emoji flag for a given magnitude."""
    if mag >= 4.5:
        return " 🚨 CRITICAL!"
    if mag >= 4.0:
        return " ⚠️ caution"
    return ""


def headers() -> dict:
    if not IOT_API_KEY:
        raise RuntimeError("IOT_API_KEY not set")
    return {"X-API-Key": IOT_API_KEY, "Content-Type": "application/json"}


def ensure_zone() -> int:
    """Reuse an existing zone whenever possible — never duplicate a test zone.

    Matching rules:
    1. Exact city name.
    2. Normalized fuzzy match ('ZONE A - TEST' == 'A-TEST' == 'a test').
    Only when nothing matches do we create a new zone.
    """
    existing = requests.get(f"{API_URL}/zones/", params={"limit": 1000}, headers=headers(), timeout=10)
    existing.raise_for_status()
    for z in existing.json():
        if z["city"] == ZONE_NAME or normalize(z["city"]) == normalize(ZONE_NAME):
            print(f"🗺️  Reusing existing zone '{z['city']}' (id={z['id']})", flush=True)
            return z["id"]

    resp = requests.post(f"{API_URL}/zones/", json={"city": ZONE_NAME}, headers=headers(), timeout=10)
    resp.raise_for_status()
    print(f"🗺️  Created zone '{ZONE_NAME}' (id={resp.json()['id']})", flush=True)
    return resp.json()["id"]


def register_sensor(zone_id: int) -> tuple:
    sk = ec.generate_private_key(ec.SECP256R1())
    public_key = sk.public_key()
    public_key_hex = public_key.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo).hex()
    payload = {
        "active": True,
        "zone_id": zone_id,
        "latitude": SENSOR_LAT,
        "longitude": SENSOR_LON,
        "public_key_hex": public_key_hex,
    }
    resp = requests.post(f"{API_URL}/sensors/", json=payload, headers=headers(), timeout=10)
    resp.raise_for_status()
    sensor_id = resp.json()["id"]
    print(f"📡 Sensor registered (id={sensor_id})", flush=True)
    return sensor_id, sk


def sign(sk, value: int, ts: int) -> str:
    sig = sk.sign(f"{value}:{ts}".encode(), ec.ECDSA(hashes.SHA256()))
    return sig.hex()


def sample_value(step: int) -> int:
    """Random noise for most of the window, then an escalating seismic ramp."""
    if step >= 15:
        ramp = [1800, 2600, 3400, 5600, 7600]
        return ramp[min(step - 15, len(ramp) - 1)]
    if step == 6:
        return random.SystemRandom().randint(900, 1600)
    return random.SystemRandom().randint(120, 750)


def main() -> None:
    zone_id = ensure_zone()
    sensor_id, sk = register_sensor(zone_id)

    print(f"🌊 Streaming {DURATION_SECONDS}s of telemetry into zone '{ZONE_NAME}'...", flush=True)
    for step in range(DURATION_SECONDS):
        value = sample_value(step)
        ts = int(time.time())
        payload = {
            "value": value,
            "sensor_id": sensor_id,
            "device_timestamp": ts,
            "signature_hex": sign(sk, value, ts),
        }
        resp = requests.post(f"{API_URL}/readings/", json=payload, headers=headers(), timeout=10)
        status = resp.status_code
        mag = estimate_magnitude(value)
        flag = _magnitude_flag(mag)
        print(f"   t+{step:>2}s  value={value:>5}  M≈{mag:.2f}{flag}  http {status}", flush=True)
        if status != 202:
            print(f"      API: {resp.text}", flush=True)
        time.sleep(1.0)

    print("\n✅ Stream complete. The dashboard should now show the wave; "
          "the CRITICAL at the end triggers the siren in the app.", flush=True)


if __name__ == "__main__":
    main()