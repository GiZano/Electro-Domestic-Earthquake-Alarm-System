from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List
import json
import asyncio

app = FastAPI()

# --- 1. Connection Manager (Il "Centralino") ---
class ConnectionManager:
    def __init__(self):
        # Lista di tutti i telefoni connessi
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"📱 Client connesso. Totale: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"❌ Client disconnesso. Totale: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        # Invia l'alert a TUTTI i telefoni connessi
        print(f"📡 Broadcasting: {message}")
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                print(f"Errore invio: {e}")

manager = ConnectionManager()

# --- 2. Endpoint WebSocket ---
@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Qui il server rimane in ascolto (keep-alive)
            # In un caso reale, qui potresti non ricevere nulla dal client,
            # ma il server userà 'manager.broadcast' quando Redis rileva un sisma.
            data = await websocket.receive_text() 
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- 3. Endpoint di Test (Per simulare un terremoto) ---
# Chiama questo con Postman per vedere l'app reagire!
@app.post("/simulate-quake")
async def simulate_quake(zone_id: int, magnitude: float):
    alert_data = {
        "type": "CRITICAL",
        "zone_id": zone_id,
        "magnitude": magnitude,
        "timestamp": "2024-02-27T10:00:00Z",
        "message": f"SCSSA SISMICA RILEVATA: MAG {magnitude}"
    }
    await manager.broadcast(alert_data)
    return {"status": "Alert sent"}