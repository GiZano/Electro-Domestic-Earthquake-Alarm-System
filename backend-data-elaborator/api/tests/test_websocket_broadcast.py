"""
Stress Test / Simulation for WebSocket Broadcast (#30)
------------------------------------------------------
Simulates multiple mobile clients connecting to the FastAPI WebSocket endpoint,
then publishes a fake earthquake alert via Redis to verify all clients receive it instantly.

Requires: pip install websockets redis
"""
import asyncio
import websockets
import json
import os

import redis.asyncio as aioredis

# Assumes the backend is running locally on port 8000
WS_URI = "ws://127.0.0.1:8000/ws/alerts?token=SecretMobileAppToken2024"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
NUM_CLIENTS = 100

async def simulate_client(client_id: int, received_events: list):
    """Simulates a mobile app keeping a WebSocket connection open."""
    try:
        async with websockets.connect(WS_URI) as ws:
            while True:
                # Wait for the backend to push an alert
                msg = await ws.recv()
                print(f"📱 Client {client_id:03} received alert: {msg}")
                received_events.append(client_id)
                break  # Exit successfully after receiving the first alert
    except Exception as e:
        print(f"❌ Client {client_id:03} failed: {e}")

async def trigger_alert():
    """Simulates the background worker triggering an earthquake alert via Redis."""
    await asyncio.sleep(2)  # Give all clients 2 seconds to establish their WS connections
    
    print("\n🚨 Triggering simulated earthquake alert via Redis Pub/Sub...")
    r = aioredis.from_url(REDIS_URL)
    
    alert_payload = json.dumps({
        "event_type": "EARTHQUAKE_WARNING", 
        "magnitude": 6.5, 
        "zone_id": 1,
        "message": "DROP, COVER, AND HOLD ON!"
    })
    
    # Publish to the channel the FastAPI app is listening to
    await r.publish("quake_alerts", alert_payload)
    await r.aclose()

async def main():
    print(f"Starting broadcast test with {NUM_CLIENTS} concurrent clients...\n")
    received_events = []
    
    # 1. Create tasks for all 100 simulated mobile clients
    client_tasks = [simulate_client(i, received_events) for i in range(NUM_CLIENTS)]
    
    # 2. Create the task that will trigger the Redis alert
    publisher_task = asyncio.create_task(trigger_alert())
    
    # 3. Run everything concurrently
    await asyncio.gather(*client_tasks, publisher_task)
    
    # 4. Evaluate Results
    print(f"\n✅ Broadcast Test Complete: {len(received_events)}/{NUM_CLIENTS} clients received the alert.")
    
    if len(received_events) == NUM_CLIENTS:
        print("🎉 SUCCESS: Task #30 Completed. Backend scales correctly with Redis Pub/Sub.")
    else:
        print("❌ FAILURE: Some clients missed the alert.")

if __name__ == "__main__":
    asyncio.run(main())