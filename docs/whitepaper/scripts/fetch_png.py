import base64
import requests
import os

def get_mermaid_png(mermaid_code, output_path):
    encoded = base64.b64encode(mermaid_code.encode('utf-8')).decode('utf-8')
    url = f"https://mermaid.ink/img/{encoded}?type=png&bgColor=ffffff"
    print(f"Fetching {url}")
    response = requests.get(url)
    if response.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(response.content)
        print(f"Saved {output_path}")
    else:
        print(f"Failed to generate {output_path}: {response.status_code}")

diagrams = {
    "01-architecture": """%%{init: {'themeVariables': { 'fontSize': '24px'}}}%%
flowchart LR
    EN["Edge Node\n(ESP32-C3)"]
    HMQ["HiveMQ\nBroker"]
    FB["FastAPI\nBackend"]
    MA["Mobile App\n(React Native)"]

    EN -- "MQTT\n(TLS)" --> HMQ
    EN == "USB CDC\nFallback" ==> FB
    
    HMQ -- "HTTP POST\n(Bridge)" --> FB
    
    FB -- "WebSocket" --> MA
    
    style EN fill:#f9f,stroke:#333,stroke-width:2px
    style HMQ fill:#bbf,stroke:#333,stroke-width:2px
    style MA fill:#bfb,stroke:#333,stroke-width:2px
    style FB fill:#fbb,stroke:#333,stroke-width:2px
""",
    "03-security": """sequenceDiagram
    participant EN as Edge Node (ESP32)
    participant FB as FastAPI Backend

    EN->>FB: POST /devices/register<br>{ pubKey, mac, enrollment_token }
    FB-->>EN: 201 Created<br>{ sensor_id: 42, zone: "Rome" }
    Note over EN: Store sensor_id in NVS
""",
    "08-ai": """flowchart TD
    Start(("Alert Triggered"))
    Start --> PENDING["PENDING"]
    PENDING -- "Ollama Processing" --> Split{" "}
    Split -- Success --> COMPLETED["COMPLETED"]
    Split -- Error --> FAILED["FAILED"]
    COMPLETED --> End1(("WebSocket Push"))
    FAILED --> End2(("DLQ Retry"))
    
    style PENDING fill:#fbb,stroke:#333,stroke-width:2px
    style COMPLETED fill:#bfb,stroke:#333,stroke-width:2px
    style FAILED fill:#f9f,stroke:#333,stroke-width:2px
"""
}

os.makedirs("assets", exist_ok=True)
for name, code in diagrams.items():
    get_mermaid_png(code, f"assets/{name}.png")
