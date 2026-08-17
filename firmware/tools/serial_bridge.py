#!/usr/bin/env python3
"""
QuakeGuard USB Serial Bridge (v1.2.2).

Reads the [QG:FB] machine-readable frames the firmware emits over USB CDC when
the MQTT data plane is unreachable, and forwards each frame to the ingestion
pipeline -- exactly like backend/src/mqtt_subscriber.py does for MQTT.

The frames carry the same payload as the MQTT data plane, so the backend's
ECDSA signature + replay-window checks apply unchanged:
    {"value":..,"sensor_id":..,"device_timestamp":..,"signature_hex":".."}
"""

import argparse
import json
import os
import sys

DEFAULT_MARKER = "[QG:FB]"
DEFAULT_API_URL = "http://fastapi-app:8000/readings/"


def parse_frame(line, marker=DEFAULT_MARKER):
    """Extract the telemetry payload from a serial line.

    Returns a dict on a valid frame line, None on any other line (boot logs,
    blank lines, etc.). Pure function: no I/O, unit-testable in CI.
    """
    line = line.strip()
    if not line.startswith(marker):
        return None
    try:
        payload = json.loads(line[len(marker):])
    except (ValueError, TypeError):
        return None
    required = {"value", "sensor_id", "device_timestamp", "signature_hex"}
    if not required.issubset(payload.keys()):
        return None
    return payload


def forward(payload, api_url, api_key, timeout=10):
    """POST one telemetry payload to the ingestion endpoint.

    Returns the HTTP status code. Pure function apart from the network call.
    """
    import requests

    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
    response = requests.post(api_url, data=json.dumps(payload), headers=headers, timeout=timeout)
    return response.status_code


def _run(stream, api_url, api_key, dry_run):
    for raw in stream:
        payload = parse_frame(raw, DEFAULT_MARKER)
        if payload is None:
            continue
        if dry_run:
            print(f"BRIDGE frame: {json.dumps(payload)}")
            continue
        try:
            status = forward(payload, api_url, api_key)
            if status == 202:
                print("✅ Frame bridged successfully.")
            else:
                print(f"⚠️ API rejected frame: HTTP {status}")
        except Exception as exc:  # network errors must not kill the reader loop
            print(f"❌ Bridge Error: {exc}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default=os.getenv("SERIAL_PORT", "/dev/ttyACM0"),
                        help="USB CDC device (default: /dev/ttyACM0)")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate")
    parser.add_argument("--api-url", default=os.getenv("API_INGESTION_URL", DEFAULT_API_URL),
                        help="Backend ingestion endpoint")
    parser.add_argument("--api-key", default=os.getenv("IOT_API_KEY"),
                        help="X-API-Key header (default: $IOT_API_KEY)")
    parser.add_argument("--stdin", action="store_true",
                        help="Read lines from stdin instead of a serial port (testing)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and print frames without forwarding")
    args = parser.parse_args(argv)

    if not args.api_key:
        parser.error("IOT_API_KEY is required (env or --api-key)")

    if args.stdin:
        _run(sys.stdin, args.api_url, args.api_key, args.dry_run)
        return 0

    import serial  # imported lazily so parse_frame/forward work without pyserial

    with serial.Serial(args.port, args.baud, timeout=1) as ser:
        print(f"🔌 Listening on {args.port} @ {args.baud} baud...")
        _run(ser, args.api_url, args.api_key, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
