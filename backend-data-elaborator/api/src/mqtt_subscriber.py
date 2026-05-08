import os
import time
import requests
import paho.mqtt.client as mqtt

IOT_API_KEY = os.getenv("IOT_API_KEY")
if not IOT_API_KEY:
    raise RuntimeError("🚨 CRITICAL: IOT_API_KEY not set!")

MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883)) 
MQTT_TOPIC = "quakeguard/telemetry"
API_INGESTION_URL = "http://fastapi-app:8000/misurations/"
API_HEALTH_URL = "http://fastapi-app:8000/health"

def wait_for_api(retries=10, delay=3):
    """💡 FIX: Deterministic wait for the API to be ready to accept data."""
    print("Checking API connection...")
    for i in range(retries):
        try:
            r = requests.get(API_HEALTH_URL, timeout=5)
            if r.status_code == 200:
                return
        except requests.exceptions.RequestException as e:
            print(f"Health check failed: {e}")
            
        print(f"⏳ Waiting for API... ({i+1}/{retries})")
        time.sleep(delay)
    raise RuntimeError("❌ API never became healthy")

def on_connect(client, userdata, flags, rc):
    print(f"📡 MQTT Bridge connected with result code {rc}")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        headers = {"X-API-Key": IOT_API_KEY, "Content-Type": "application/json"}
        response = requests.post(API_INGESTION_URL, data=payload, headers=headers, timeout=10)
        
        if response.status_code == 202:
            print("✅ Payload bridged successfully.")
        else:
            print(f"⚠️ API rejected payload: HTTP {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Bridge Error: {e}")

if __name__ == "__main__":
    wait_for_api()
    
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    print(f"🔌 Connecting to MQTT Broker at {MQTT_BROKER}:{MQTT_PORT}...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()