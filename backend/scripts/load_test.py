#!/usr/bin/env python3
"""Load generator for the QuakeGuard ingestion path.

Simulates ``--sensors`` IoT devices emitting heartbeats at ``--hz`` each and
measures sustained throughput. Two transport modes:

  --mode stream  XADD directly to the Redis Streams bus (bypasses the API; this
                 is the steady-state ingestion bottleneck we must keep O(1)).
  --mode http    POST to the FastAPI /readings/ endpoint (exercises the full
                 ingress, but without ECDSA signature validation).

Usage:
  python scripts/load_test.py --sensors 150 --hz 1 --duration 60
  python scripts/load_test.py --sensors 1000 --hz 1 --duration 30 --mode http --api http://localhost:8000
"""

import argparse
import json
import time

import redis


def stream_worker(args, stop_event):
    client = redis.from_url(args.redis, decode_responses=True)

    def emit(sensor_id):
        payload = {
            "value": 150,
            "sensor_id": sensor_id,
            "latitude": 45.0 + (sensor_id % 100) / 1000.0,
            "longitude": 9.0 + (sensor_id % 100) / 1000.0,
        }
        client.xadd(
            args.stream, {"payload": json.dumps(payload)}, maxlen=200000, approximate=True
        )

    next_emit = time.monotonic()
    interval = 1.0 / args.hz
    while not stop_event.is_set():
        now = time.monotonic()
        if now < next_emit:
            time.sleep(0.001)
            continue
        next_emit += interval
        for sid in range(1, args.sensors + 1):
            emit(sid)


def http_worker(args, stop_event):
    import requests

    def emit(sensor_id):
        payload = {
            "value": 150,
            "sensor_id": sensor_id,
            "latitude": 45.0,
            "longitude": 9.0,
        }
        requests.post(
            args.api + "/readings/",
            json=payload,
            headers={"X-API-Key": args.api_key},
            timeout=5,
        )

    emitted = 0
    next_emit = time.monotonic()
    interval = 1.0 / args.hz
    while not stop_event.is_set():
        now = time.monotonic()
        if now < next_emit:
            time.sleep(0.001)
            continue
        next_emit += interval
        emit((emitted % args.sensors) + 1)
        emitted += 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sensors", type=int, default=150, help="number of simulated devices")
    parser.add_argument("--hz", type=float, default=1.0, help="heartbeats per second per device")
    parser.add_argument("--duration", type=int, default=60, help="test duration in seconds")
    parser.add_argument("--mode", choices=["stream", "http"], default="stream")
    parser.add_argument("--redis", default="redis://localhost:6379/0")
    parser.add_argument("--stream", default="readings:stream")
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--api-key", default="ci-test-key-123")
    args = parser.parse_args()

    import threading

    stop_event = threading.Event()
    worker = stream_worker if args.mode == "stream" else http_worker

    print(
        f"🚀 Load test: {args.sensors} sensors @ {args.hz} Hz each, "
        f"target {args.sensors * args.hz:.0f} msg/s, {args.duration}s, mode={args.mode}",
        flush=True,
    )

    worker_thread = threading.Thread(target=worker, args=(args, stop_event), daemon=True)
    worker_thread.start()

    start = time.monotonic()
    time.sleep(args.duration)
    stop_event.set()
    elapsed = time.monotonic() - start
    worker_thread.join(timeout=2)

    total_msgs = args.sensors * args.hz * elapsed
    print(f"📊 Emitted ~{total_msgs:.0f} messages in {elapsed:.1f}s", flush=True)
    print(f"📊 Sustained rate: {total_msgs / elapsed:.0f} msg/s", flush=True)


if __name__ == "__main__":
    main()
