# ROADMAP — QuakeGuard

> Semantic Versioning progression.

---

## v1.0.0 — Rilevamento Sismico Edge (Completata)

Rilevamento sismico edge su ESP32 e alert locale.

- Acquisizione ADXL345 a 100 Hz con STA/LTA triggering
- Firma ECDSA su ogni payload
- Alert locale via LED / seriale

---

## v1.1.0 — Cloud & Sicurezza (Attuale)

Migrazione Data Plane su MQTT Cloud (HiveMQ), Control Plane REST (HTTPS) e sicurezza TLS.

- Data Plane: ESP32 → HiveMQ Cloud (porta 8883, TLS + username/password)
- Control Plane: ngrok tunnel HTTPS per provisioning REST
- `setInsecure()` per handshake TLS su ESP32
- MQTT Bridge (Python Paho) con TLS
- Dashboard mobile funzionante con dati live
- CI/CD attivo

---

## v1.2.0 — AI Cloud (Attuale)

Integrazione AI Cloud (LLM on-premise nel backend per la generazione di report di emergenza testuali partendo dai dati MQTT).

- ✅ LLM on-premise via Ollama (`llama3.2:1b`) che consuma gli alert confermati — telemetry mai esposta
- ✅ Generazione automatica report emergenza: magnitudo, zona, timestamp, raccomandazioni (deterministico, anti-allucinazione)
- ✅ WebSocket push del report AI alla mobile app (banner + card storico)
- ✅ Stato `PENDING → COMPLETED | FAILED` con DLQ e fallback esplicito
- ✅ Endpoint REST `GET /reports/{alert_id}`

---

## v1.3.0 — GNSS Sincronizzato

Sincronizzazione GNSS avanzata dei nodi per timestamp esatti.

- GPS/GNSS module opzionale su ESP32
- Timestamp NTP + PPS corretti per tutti i nodi
- Risoluzione hardcoded GPS (coordinate Roma) con coordinate reali
- Calibrazione ADXL345 offset su boot

---

## v2.0.0 — Triangolazione Epicentro

Algoritmo di Triangolazione. Correlazione spaziale multi-nodo unita ai report AI per il calcolo dell'epicentro interno.

- Algoritmo di triangolazione da ≥3 nodi
- Correlazione spaziale e temporale multi-nodo
- Calcolo epicentro interno
- Unione dati AI + triangolazione per alert precisi