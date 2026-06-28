// =============================================================================
// QuakeGuard — Documentazione Tecnica (Italiano)
// =============================================================================

#set page(
  paper: "a4",
  margin: (top: 2cm, bottom: 2cm, left: 2.5cm, right: 2.5cm),
  numbering: "1",
)
#set text(font: ("DejaVu Serif"), size: 11pt)
#set heading(numbering: "1.1")
#set par(justify: true, leading: 0.65em)

// =============================================================================
// PACKAGES
// =============================================================================
#import "@preview/fletcher:0.5.8": diagram, node, edge

// =============================================================================
// COLORI
// =============================================================================
#let color-primary = rgb("#dc2626")
#let color-secondary = rgb("#1f2937")
#let color-accent = rgb("#4f46e5")
#let color-green = rgb("#16a34a")
#let color-muted = rgb("#6b7280")
#let color-light = rgb("#f3f4f6")

// =============================================================================
// HELPERS
// =============================================================================
#let highlight(content) = {
  rect(
    fill: rgb("#fef2f2"),
    stroke: color-primary + 1pt,
    inset: 8pt,
    radius: 4pt,
    content,
  )
}

#let techstack(content) = {
  grid(
    columns: (1fr,),
    gutter: 4pt,
    rect(
      fill: color-light,
      stroke: rgb("#e5e7eb") + 0.5pt,
      inset: 10pt,
      radius: 4pt,
      content,
    ),
  )
}

// =============================================================================
// FRONTESPIZIO
// =============================================================================
#align(center + top, [
  #block(height: 2cm)
  #text(size: 16pt, weight: "light", fill: color-muted)[Sistema Elettro-Domestico di Allarme Sismico]
  #block(height: 5mm)
  #text(size: 36pt, weight: "bold", fill: color-primary)[QuakeGuard]
  #block(height: 5mm)
  #text(size: 14pt, fill: color-secondary)[Documentazione Tecnica]
  #block(height: 3mm)
  #text(size: 10pt, fill: color-muted)[v1.0.0 — Giugno 2026]
  #block(height: 1.5cm)
  #line(length: 40%, stroke: color-primary + 1.5pt)
  #block(height: 1cm)
  #text(size: 10pt, fill: color-muted)[
    *Autori:* Giovanni Zanotti (\@GiZano), Riccardo (\@riccardo0731) \
    *Licenza:* GNU Affero General Public License v3.0 \
    *Repository:* #text(fill: color-accent)[github.com/GiZano/QuakeGuard]
  ]
])

#pagebreak()

// =============================================================================
// INDICE
// =============================================================================
#outline(indent: auto, title: [
  #text(size: 20pt, weight: "bold", fill: color-secondary)[Indice]
])

#pagebreak()

// =============================================================================
// 1 — INTRODUZIONE
// =============================================================================
= Introduzione

== Panoramica

*QuakeGuard* è un'architettura IoT full-stack per la rilevazione, analisi e
segnalazione in tempo reale di eventi sismici. Il sistema trasforma
elettrodomestici comuni — lavatrici, televisori, frigoriferi — in una rete
distribuita di sensori sismici, ciascuno in grado di rilevare e segnalare
autonomamente attività tellurica.

I sensori edge intelligenti (ESP32-C3 + ADXL345) analizzano le vibrazioni
localmente utilizzando algoritmi professionali e trasmettono dati firmati
crittograficamente a un backend asincrono sul cloud. Il backend è progettato per
gestire i picchi di traffico massicci — l'effetto *Thundering Herd* — tipici
durante eventi sismici diffusi, garantendo una consegna affidabile degli allarmi
senza colli di bottiglia. Un'app mobile React Native riceve avvisi aptici e
visivi in tempo reale tramite WebSocket.

#highlight[
  *Contesto:* Progetto sviluppato per la competizione scolastica *Hackersgen*
  da Sorint.lab e il concorso *GF Marilli*.
]

== Principi Architetturali

Il sistema segue i principi di:

- *Microservizi:* Tre strati completamente indipendenti (IoT, Backend, Frontend)
- *Event-Driven Design:* Redis come message broker per disaccoppiare
  ingestione, elaborazione e notifica
- *Zero-Trust Security:* Ogni payload è firmato ECDSA NIST256p, verificato
  dal backend, con protezione anti-replay
- *Fail-Fast:* Le variabili d'ambiente mancanti bloccano l'avvio con messaggi
  di errore chiari

#pagebreak()

// =============================================================================
// 2 — ARCHITETTURA DI SISTEMA
// =============================================================================
= Architettura di Sistema

== Diagramma Architetturale

#align(center, table(
  columns: (auto, auto, auto, auto, auto),
  stroke: 0.5pt + rgb("#e5e7eb"),
  [*Livello*], [*Componente*], [*Tecnologia*], [*Flusso*], [*Protocollo*],
  [1 -- IoT], [Sensori Edge], [ESP32-C3 + ADXL345], [Rilevamento vibrazioni], [GPIO / I²C],
  [], [Firmware], [STA/LTA], [Elaborazione locale], [],
  [], [Firma], [ECDSA NIST256p], [Firma dei payload], [],
  [2 -- Messaging], [Message Broker], [Mosquitto MQTT], [IoT → Cloud], [MQTT],
  [3 -- Backend], [API Gateway], [FastAPI + Redis], [Ricezione e validazione], [HTTPS],
  [], [Validazione], [ECDSA Anti-Replay], [Verifica firme], [],
  [], [Coda], [Redis Queue], [Buffering asincrono], [LPUSH / BRPOP],
  [4 -- Elaborazione], [Worker], [Python Background], [Analisi dati], [],
  [5 -- Storage], [Database], [PostgreSQL + PostGIS], [Persistenza], [SQL],
  [6 -- Notifiche], [WebSocket Server], [FastAPI WS], [Broadcast in tempo reale], [WS / WSS],
  [7 -- Mobile], [App], [React Native (Expo)], [Visualizzazione allarmi], [WebSocket],
  [], [Demo Route], [/demo/trigger-earthquake], [Simulazione terremoto], [HTTP POST],
))

== Flusso dei Dati End-to-End

#diagram(
  node((0, 0), [ESP32\nADXL345], radius: 1.2cm, stroke: color-primary),
  edge("-|>", stroke: color-primary),
  node((3, 0), [Mosquitto], radius: 1.2cm, stroke: color-accent),
  edge("-|>"),
  node((6, 0), [FastAPI], radius: 1.2cm, stroke: color-green),
  edge("-|>"),
  node((9, 0), [Redis\nQueue], radius: 1.2cm, stroke: rgb("#d97706")),
  edge("-|>"),
  node((12, 0), [Worker], radius: 1.2cm, stroke: rgb("#d97706")),
  edge("-|>"),
  node((15, 0), [PostGIS], radius: 1.2cm, stroke: rgb("#7c3aed")),
  edge((12, -1.5), "-|>", label: text(size: 7pt)[Pub/Sub]),
  edge("-|>"),
  node((12, -3), [WebSocket], radius: 1.2cm, stroke: rgb("#db2777")),
  edge("-|>"),
  node((12, -6), [App\nMobile], radius: 1.2cm, stroke: rgb("#0d9488")),
)

#pagebreak()

// =============================================================================
// 3 — COMPONENTI DEL SISTEMA
// =============================================================================
= Componenti del Sistema

== 3.1 IoT Edge

=== Hardware

#table(
  columns: (4cm, auto),
  stroke: 0.5pt + rgb("#e5e7eb"),
  [*Specifica*], [*Dettaglio*],
  [Microcontrollore], [ESP32-C3 SuperMini (RISC-V 32-bit, 160MHz)],
  [Sensore], [ADXL345 Accelerometro Digitale (MEMS, I2C)],
  [Range], [±2G, ±4G, ±8G, ±16G (configurabile)],
  [Sample Rate], [100 Hz (fisso)],
  [Pin SDA], [GPIO 7],
  [Pin SCL], [GPIO 8],
)

=== Firmware (v3.3.0-PROV-REFACTORED)

Il firmware implementa un'architettura FreeRTOS a due task:

*Task 1 — SensorTask (Priorità 5, Stack 8KB)*
#techstack[
  - Acquisizione ADXL345 a 100 Hz
  - Filtro HPF (High-Pass Filter, $alpha = 0.9$) per rimuovere la gravità
  - Calcolo STA/LTA con buffer circolari
  - Rilevamento trigger quando ratio $>= 1.8$ e segnale $> "0.04 G"$
]

*Task 2 — NetworkTask (Priorità 1, Stack 8KB)*
#techstack[
  - Connessione MQTT al broker Mosquitto
  - Sincronizzazione NTP (pool.ntp.org)
  - Firma ECDSA del payload
  - Publish su topic `quakeguard/telemetry`
]

=== Algoritmo di Rilevamento STA/LTA

L'algoritmo STA/LTA (Short Term Average / Long Term Average) è il cuore
del sistema di rilevamento:

$ "STA" = "media finestra mobile 1s (100 campioni)" $

$ "LTA" = "media finestra mobile 10s (1000 campioni)" $

$ "Ratio" = "STA" / "LTA" $

$ "Trigger quando Ratio" >= 1.8 " e STA > " 0.04 G $

#techstack[
  *Noise Gate:* Segnali inferiori a 0.04 G vengono azzerati per prevenire \
  falsi positivi da rumore elettrico.\
  *HPF:* Filtro passa-alto con $alpha = 0.9$ rimuove la componente DC (gravità).\
  *Dropout Protection:* Frame di valore 0G vengono automaticamente scartati.
]

=== Security Subsystem

Il firmware utilizza MbedTLS per la crittografia:

#techstack[
  - *ECDSA NIST256p (secp256r1):* Generazione chiavi su primo boot
  - *Memorizzazione:* NVS (Non-Volatile Storage) partizione
  - *Firma:* SHA-256 del payload formattato `"value:timestamp"`
  - *NTP:* Sincronizzazione tempo per anti-replay
]

=== Provisioning Automatico

Il dispositivo esegue un handshake automatico al primo avvio:

#diagram(
  node((0, 0), [Boot ESP32], radius: 1cm, stroke: color-primary),
  edge("-|>", label: text(size: 7pt)[Genera chiave ECDSA]),
  node((3, 0), [ECDSA Key\nGenerated], radius: 1cm, stroke: color-accent),
  edge("-|>", label: text(size: 7pt)[WiFiManager]),
  node((6, 0), [WiFi\nConnected], radius: 1cm, stroke: color-green),
  edge("-|>", label: text(size: 7pt)[POST /devices/register]),
  node((9, 0), [Backend\nRegistra], radius: 1cm, stroke: rgb("#7c3aed")),
  edge("-|>"),
  node((12, 0), [Riceve\nsensor_id], radius: 1cm, stroke: rgb("#0d9488")),
  edge("-|>", label: text(size: 7pt)[Salva in NVS]),
  node((15, 0), [Operativo], radius: 1cm, stroke: color-green),
)

#pagebreak()

== 3.2 Backend

=== Stack Tecnologico

#techstack[
  - *Framework:* FastAPI (Python 3.11) — completamente asincrono
  - *Database:* PostgreSQL 15 + PostGIS 3.4 (estensioni geospaziali)
  - *Message Broker:* Redis 7 (coda + Pub/Sub + rate limiting + deduplicazione)
  - *MQTT Broker:* Eclipse Mosquitto 2
  - *ORM:* SQLAlchemy 2.0 + GeoAlchemy2 0.19
  - *Containerizzazione:* Docker Compose (6 servizi)
  - *Pool Connessioni DB:* pool_size=40, max_overflow=60 (totale 100 connessioni)
]

=== Servizi Docker

#table(
  columns: (2cm, 1.5cm, 3.5cm, auto),
  stroke: 0.5pt + rgb("#e5e7eb"),
  [*Servizio*], [*Porta*], [*Dipende da*], [*Ruolo*],
  [postgres], [5432], [—], [Database PostgreSQL + PostGIS],
  [redis], [6379], [—], [Message broker + cache],
  [fastapi-app], [8000], [postgres (healthy),\nredis], [API Gateway HTTP/WS],
  [mosquitto], [1883], [—], [MQTT broker],
  [mqtt-bridge], [—], [mosquitto (healthy),\nfastapi-app (healthy)], [Bridge MQTT → HTTP],
  [worker], [—], [postgres (healthy),\nredis], [Elaboratore eventi in background],
)

=== Struttura del Database

#diagram(
  node((0, 0), [
    #text(size: 9pt, weight: "bold")[*zones*]\
    #text(size: 7pt)[id (PK, int)]\
    #text(size: 7pt)[city (varchar, unique)]\
    #text(size: 7pt)[created_at (timestamp)]\
    #text(size: 7pt)[geom (POLYGON, srid=4326)]
  ], radius: 1.5cm, stroke: rgb("#7c3aed")),
  node((0, -3.5), [
    #text(size: 9pt, weight: "bold")[*alerts*]\
    #text(size: 7pt)[id (PK, int)]\
    #text(size: 7pt)[zone_id (FK)]\
    #text(size: 7pt)[timestamp (timestamp)]\
    #text(size: 7pt)[severity (float)]\
    #text(size: 7pt)[message (varchar)]
  ], radius: 1.5cm, stroke: rgb("#d97706")),
  node((5, 0), [
    #text(size: 9pt, weight: "bold")[*misurators*]\
    #text(size: 7pt)[id (PK, int)]\
    #text(size: 7pt)[active (bool)]\
    #text(size: 7pt)[zone_id (FK)]\
    #text(size: 7pt)[latitude, longitude (float)]\
    #text(size: 7pt)[location (POINT, srid=4326)]\
    #text(size: 7pt)[public_key_hex (varchar, unique)]\
    #text(size: 7pt)[mac_address (varchar, unique)]
  ], radius: 1.8cm, stroke: color-green),
  node((5, -3.5), [
    #text(size: 9pt, weight: "bold")[*misurations*]\
    #text(size: 7pt)[id (PK, int)]\
    #text(size: 7pt)[recorded_at (timestamp)]\
    #text(size: 7pt)[value (int)]\
    #text(size: 7pt)[misurator_id (FK)]
  ], radius: 1.5cm, stroke: rgb("#0d9488")),
  edge((0, -1.5), (0, -2.0), stroke: 0.5pt + rgb("#d1d5db"), "-->"),
  edge((5, -1.8), (5, -2.0), stroke: 0.5pt + rgb("#d1d5db"), "-->"),
  edge((0, 1.5), (5, 1.5), stroke: 0.5pt + rgb("#d1d5db"), "--", label: text(size: 7pt)[1:N, zone_id]),
  edge((5, 1.5), (0, 1.5), stroke: 0.5pt + rgb("#d1d5db"), "--"),
  edge((5, -1.8), (0, -1.8), stroke: 0.5pt + rgb("#d1d5db"), "--", label: text(size: 7pt)[1:N, zone_id]),
)

=== Security Model

Il backend implementa un modello di sicurezza a quattro livelli:

#highlight[
  1. *API Key* — Header `X-API-Key` verificato su ogni richiesta (tranne /health e /devices/register)
  2. *Verifica ECDSA* — Firma NIST256p verificata con libreria `cryptography` (Python)
  3. *Anti-Replay* — Finestra di 60 secondi sul timestamp del dispositivo
  4. *Rate Limiting* — 50 richieste al secondo per IP (finestra fissa Redis)
]

Supporto *polyglot crypto*: il backend accetta firme in formato DER (MbedTLS/C++)
e RAW (Python/JS), offrendo compatibilità con diverse implementazioni client.

=== Magnitudo Estimation

Il worker stima la magnitudo sismica con la formula MyShake-style:

$ M_("IoT") = log_10 ( (v / S) / K ) + b $

Dove:
#techstack[
  - $v$ = valore grezzo dal sensore (int -8192..8192)
  - $S = 100.0$ = fattore di scala (raw → m/s²)
  - $K = 1.6$ = fattore di calibrazione MEMS
  - $b = 3.0$ = offset empirico
]

Un allarme CRITICO viene attivato quando $M >= 4.5$, con deduplicazione
per zona (cooldown Redis di 60 secondi).

=== API REST Endpoints

#table(
  columns: (2.5cm, 4cm, auto),
  stroke: 0.5pt + rgb("#e5e7eb"),
  [*Metodo*], [*Path*], [*Descrizione*],
  [GET], [/health], [Health check (PostgreSQL + Redis ping)],
  [POST], [/zones/], [Crea zona geografica],
  [GET], [/zones/], [Lista zone],
  [POST], [/misurators/], [Registra sensore con chiave pubblica],
  [POST], [/devices/register], [Handshake automatico ESP32],
  [GET], [/misurators/], [Lista sensori registrati],
  [POST], [/misurations/], [Ingress dati (con validazione ECDSA)],
  [GET], [/sensors/{id}/statistics], [Statistiche sensore],
  [GET], [/misurations/], [Ultime 50 letture],
  [POST], [/demo/trigger-earthquake], [Simula terremoto (demo)],
)

#techstack[
  *WebSocket:* `/ws/alerts?token=MOBILE_WS_TOKEN` \
  — Connessione persistente per broadcast alert in tempo reale
]

=== Geographic Zones

Il DB è pre-seeded con 8 macro-regioni globali. L'assegnazione automatica
dei sensori usa PostGIS `ST_Contains`, ordinando per area crescente
per garantire l'assegnazione alla regione più specifica.

#table(
  columns: (4cm, auto),
  stroke: 0.5pt + rgb("#e5e7eb"),
  [*Zona*], [*Copertura*],
  [Italy - North], [Lombardia, Veneto, Piemonte],
  [Italy - Center], [Toscana, Lazio, Umbria],
  [Italy - South & Islands], [Campania, Sicilia, Sardegna],
  [Western Europe], [Francia, Spagna, Germania, UK],
  [North America], [USA, Canada, Messico],
  [South America], [Brasile, Argentina, Cile],
  [East Asia], [Cina, Giappone, India],
  [Unknown Region], [Fallback per coordinate non mappate],
)

#pagebreak()

== 3.3 Frontend Mobile

=== Stack Tecnologico

#techstack[
  - *Framework:* React Native 0.81 (Expo SDK 54, React 19.1)
  - *Linguaggio:* TypeScript 5.9
  - *Navigazione:* Expo Router 6 (file-based, 3-tab bottom navigator)
  - *State Management:* Zustand 5 (3 store slices)
  - *Server State:* TanStack Query 5 (React Query)
  - *Real-Time:* WebSocket nativo con riconnessione esponenziale
  - *Notifiche:* expo-notifications + Vibration API
  - *Mappe:* react-native-maps 1.20
  - *Grafici:* victory-native 36
  - *Icone:* lucide-react-native 0.563
]

=== Struttura degli Schermi

#diagram(
  node((0, 0), [
    #text(size: 9pt, weight: "bold")[Root Layout]\
    #text(size: 7pt)[QueryClientProvider]\
    #text(size: 7pt)[SafeAreaProvider]\
    #text(size: 7pt)[WebSocketProvider]
  ], radius: 1.5cm, stroke: color-secondary),
  edge("-|>"),
  node((0, -4.5), [
    #text(size: 9pt, weight: "bold")[Tab Navigator]\
    #text(size: 7pt)[3 schede: Monitor, Mappa, Impostazioni]
  ], radius: 1.5cm, stroke: color-accent),
  edge((-2.8, -4.5), (-1.5, -4.5), "--", stroke: 0.5pt + rgb("#d1d5db")),
  edge((1.5, -4.5), (2.8, -4.5), "--", stroke: 0.5pt + rgb("#d1d5db")),
  node((-4, -4.5), [
    #text(size: 8pt, weight: "bold")[Monitor]\
    #text(size: 7pt)[Dashboard]\
    #text(size: 7pt)[Sismografo]\
    #text(size: 7pt)[Cronologia Alert]
  ], radius: 1.2cm, stroke: color-green),
  node((0, -6), [
    #text(size: 8pt, weight: "bold")[Mappa]\
    #text(size: 7pt)[Sensori su mappa]\
    #text(size: 7pt)[Callout statistiche]
  ], radius: 1.2cm, stroke: rgb("#0d9488")),
  node((4, -4.5), [
    #text(size: 8pt, weight: "bold")[Settings]\
    #text(size: 7pt)[Notifiche toggle]\
    #text(size: 7pt)[Offline mode]\
    #text(size: 7pt)[Clear history]
  ], radius: 1.2cm, stroke: rgb("#d97706")),
  edge((-2.8, -4.5), (-2.8, -6), stroke: 0.5pt + rgb("#d1d5db"), "--"),
  edge((2.8, -4.5), (2.8, -6), stroke: 0.5pt + rgb("#d1d5db"), "--"),
)

=== Gestione dello Stato

Il progetto utilizza tre store Zustand indipendenti:

*usePreferencesStore*
#techstack[
  - `isOfflineMode` (default: false) — silenzia WebSocket e polling
  - `notificationsEnabled` (default: true)
]

*useAlertStore*
#techstack[
  - `alerts[]` — ultimi 10 alert critici in memoria
  - `addAlert()`, `clearAlerts()`
]

*useQuakeStore* (legacy)
#techstack[
  - Polling HTTP ogni 2 secondi su `GET /zones/1/alerts`
  - `systemStatus: "SECURE" | "ALERT"`
]

=== WebSocket con Riconnessione Esponenziale

Il context WebSocket implementa un meccanismo di riconnessione robusto:

#techstack[
  - Massimo delay: 30 secondi
  - Backoff esponenziale: $ "delay" = min(1000 "ms" dot 2^("tentativi"), 30 000 "ms") $
  - Pattern vibrazione SOS per allarme critico
  - Notifica push OS tramite expo-notifications
  - Supporto Offline Mode (chiusura intenzionale WS)
  - Protezione contro doppia connessione
]

#pagebreak()

// =============================================================================
// 4 — SICUREZZA
// =============================================================================
= Modello di Sicurezza

== Copertura della Threat Model

#table(
  columns: (4cm, auto),
  stroke: 0.5pt + rgb("#e5e7eb"),
  [*Minaccia*], [*Contromisura*],
  [Man-in-the-Middle (MitM)], [Firma ECDSA NIST256p su ogni payload],
  [Spoofing dispositivo], [Registrazione chiave pubblica + verifica firma],
  [Replay attack], [Finestra temporale di 60 secondi],
  [Brute force API], [Rate limiting 50 req/s per IP],
  [Accesso non autorizzato], [API Key + enrollment token fail-fast],
  [Payload malformato], [Validazione Pydantic su tutti gli input],
)

== Flusso di Verifica

#diagram(
  node((0, 0), [ESP32\ngenera payload], radius: 1.2cm, stroke: color-primary),
  edge("-|>", label: text(size: 7pt)[SHA-256 hash]),
  node((3.5, 0), [Firma con\nECDSA NIST256p], radius: 1.2cm, stroke: color-accent),
  edge("-|>", label: text(size: 7pt)[MQTT → Backend]),
  node((7, 0), [Verifica\nAPI Key], radius: 1.2cm, stroke: color-green),
  edge("-|>", label: text(size: 7pt)[fail 401]),
  node((7, -3), [Verifica\nAnti-Replay], radius: 1.2cm, stroke: rgb("#d97706")),
  edge("-|>", label: text(size: 7pt)[fail 403]),
  node((7, -6), [Verifica\nECDSA], radius: 1.2cm, stroke: color-primary),
  edge("-|>", label: text(size: 7pt)[fail 401]),
  node((7, -9), [Redis\nQueue], radius: 1.2cm, stroke: rgb("#7c3aed")),
)

#pagebreak()

// =============================================================================
// 5 — DEPLOYMENT
// =============================================================================
= Deployment

== Docker Compose

L'intero backend è orchestrato con Docker Compose:

#techstack[
  ```
  docker compose up --build -d
  ```
  - API: `http://localhost:8000`
  - Swagger UI: `http://localhost:8000/docs`
  - Health Check: `http://localhost:8000/health`
]

== Variabili d'Ambiente

*Backend (.env)*
#techstack[
  `POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB` \
  `API_PORT, REDIS_HOST, REDIS_PORT, MQTT_PORT` \
  `ENROLLMENT_TOKEN, IOT_API_KEY, MOBILE_WS_TOKEN` \
  `K_CALIBRATION=1.6, B_OFFSET=3.0, SENSOR_SCALE=100.0`
]

*Frontend (.env)*
#techstack[
  `EXPO_PUBLIC_API_BASE_URL` \
  `EXPO_PUBLIC_IOT_API_KEY` \
  `EXPO_PUBLIC_MOBILE_WS_TOKEN`
]

*ESP32 (esp32_config.env)*
#techstack[
  `WIFI_SSID, WIFI_PASS` \
  `SERVER_HOST, SERVER_PORT, SERVER_PATH` \
  `ENROLLMENT_TOKEN`
]

== CI/CD Pipeline

#table(
  columns: (2.5cm, 3.5cm, auto),
  stroke: 0.5pt + rgb("#e5e7eb"),
  [*Workflow*], [*Trigger*], [*Strumenti*],
  [Backend CI], [Push/PR su backend/\*], [Bandit, Safety, Stress Test Docker],
  [Frontend CI], [Push/PR su frontend/\*], [ESLint, npm audit],
  [IoT CI], [Push/PR su iot/\*], [PlatformIO compile],
  [DevOps CI], [Push/PR su .github/\*], [Actionlint],
  [PR Lint], [Ogni PR], [Semantic PR title con scope],
  [Deploy], [Push su main (backend)], [Build → Push a GHCR],
)

#pagebreak()

// =============================================================================
// 6 — PERFORMANCE
// =============================================================================
= Metriche di Performance

#table(
  columns: (5cm, auto),
  stroke: 0.5pt + rgb("#e5e7eb"),
  [*Parametro*], [*Valore*],
  [Sampling Rate], [100 Hz],
  [Finestra STA], [1 secondo (100 campioni)],
  [Finestra LTA], [10 secondi (1000 campioni)],
  [Pool DB (max)], [100 connessioni],
  [Rate Limiting], [50 req/s per IP],
  [Anti-Replay Window], [60 secondi],
  [Alert Cooldown], [60 secondi per zona],
  [Soglia Magnitudo], [M $>=$ 4.5],
  [WebSocket Reconnect], [Esponenziale, max 30s],
  [Polling Sensori (app)], [10 secondi],
  [Polling Letture (app)], [2 secondi],
  [Alert History (app)], [Ultimi 10 eventi],
)

#pagebreak()

// =============================================================================
// 7 — STRESS TEST
// =============================================================================
= Stress Test

Il test di carico (`tests/stress_test.py`, v3.0) valida l'intera pipeline
in tre fasi:

== Fase 1: Firehose (MQTT)
#techstack[
  - 150+ sensori virtuali con firma ECDSA valida
  - Publish MQTT su `quakeguard/telemetry`
  - Middleware rate limiting (50 req/s per IP)
]

== Fase 2: Security Attacks
#techstack[
  - *Bad Signature:* Firma con chiave non registrata → bloccato (401)
  - *Replay Attack:* Timestamp di 2 ore fa → bloccato (403)
]

== Fase 3: End-to-End Verification
#techstack[
  - Polling `GET /sensors/{id}/statistics`
  - Fino a 10 tentativi in 10 secondi
  - Verifica persistenza su PostgreSQL
]

*Criterio di successo:* `🏆 SYSTEM CERTIFIED`

#pagebreak()

// =============================================================================
// 8 — TEST AUTOMATIZZATI (CI/CD)
// =============================================================================
= Test Automatizzati (CI/CD)

La pipeline CI esegue automaticamente oltre 90 test distribuiti su tre
piattaforme a ogni push su `main`/`develop`.

== Backend (Python — pytest, 62 test)

I test unitari (`tests/unit/`) si eseguono senza Docker e coprono:

#table(
  columns: (3cm, 1.5cm, auto),
  stroke: 0.5pt + rgb("#e5e7eb"),
  [*Modulo*], [*Test*], [*Cosa verifica*],
  [$monospace("security")$], [13], [Firma ECDSA valida/invalida, API key auth, anti-replay, validazione payload IoT],
  [$monospace("magnitude")$], [10], [Stima magnitudo: zero, negativo, soglia M4.5, clamping, consistenza],
  [$monospace("schemas")$], [11], [Validazione Pydantic: range valori, firma corta, timestamp, coordinate],
  [$monospace("models")$], [8], [Creazione ORM: Zone, Misurator, Misuration, Alert e relazioni],
  [$monospace("seed")$], [5], [Seeding idempotente, regioni attese, geometria Unknown Region],
  [$monospace("worker")$], [5], [Processazione eventi, alert CRITICAL, deduplica Redis, rollback errori],
)

I test di integrazione (`tests/integration/`) richiedono Docker e testano gli
endpoint FastAPI con `TestClient`:
- 10 test su health, CRUD zone/misuratori/misurazioni, statistiche, provisioning
- Verifica risposte HTTP (401, 403, 201, 202, 503)

Il test di carico esistente (`tests/stress_test.py`) completa la suite con 150+
sensori virtuali via MQTT.

== Frontend (TypeScript — Jest, 21 test)

I test Jest coprono la logica pura degli store Zustand e del servizio API:

#table(
  columns: (3cm, 1.5cm, auto),
  stroke: 0.5pt + rgb("#e5e7eb"),
  [*Modulo*], [*Test*], [*Cosa verifica*],
  [$monospace("useAlertStore")$], [5], [Aggiunta alert, limite 10, ordine LIFO, reset],
  [$monospace("usePreferencesStore")$], [3], [Toggle offline mode, toggle notifiche],
  [$monospace("quakeStore")$], [7], [Fetch sensori, start/stop monitoring, error handling, polling singolo],
  [$monospace("api")$], [6], [GET/POST, errori HTTP, errori di rete, body JSON],
)

== IoT (C++ — PlatformIO Unity, 12 test)

I test nativi PlatformIO compilano ed eseguono su host Linux senza hardware:

#table(
  columns: (3cm, 1.5cm, auto),
  stroke: 0.5pt + rgb("#e5e7eb"),
  [*Modulo*], [*Test*], [*Cosa verifica*],
  [$monospace("RingBuffer")$], [6], [Push, media, buffer pieno, wraparound, sovrascrittura],
  [$monospace("Detect")$], [6], [HPF filtro gravità, transienti, noise floor, trigger ratio, protezione divisione per zero],
)

== Workflow CI

Tutti i test sono integrati nei workflow GitHub Actions esistenti:

#techstack[
  - `backend-ci.yml`: bandit + safety + pytest unit + pytest integration + stress test
  - `frontend-ci.yml`: eslint + npm audit + Jest (mobile/)
  - `iot-ci.yml`: pio build + pio test native (firmware/)
]

#pagebreak()

// =============================================================================
// 9 — ROADMAP
// =============================================================================
= Roadmap

#table(
  columns: (2cm, 2cm, auto),
  stroke: 0.5pt + rgb("#e5e7eb"),
  [*Versione*], [*Stato*], [*Obiettivi*],
  [v1.0], [✅ Corrente], [Pipeline E2E completa, app mobile, CI/CD],
  [v1.1], [🔄 In sviluppo], [Documentazione wiki, migrazioni Alembic, MQTT cloud],
  [v2.0], [🔮 Futuro], [Assistente sismico AI (Ollama + linguaggio naturale)],
)

#pagebreak()

// =============================================================================
// 10 — LICENZA
// =============================================================================
= Licenza

#align(center)[
  #block(height: 1cm)

  Questo progetto è distribuito sotto licenza \
  *GNU Affero General Public License v3.0 (AGPL-3.0)*

  #block(height: 5mm)

  #text(size: 9pt, fill: color-muted)[
    Copyright (c) 2026 GiZano. All rights reserved. \
    Sviluppato da Giovanni Zanotti (\@GiZano) e Riccardo (\@riccardo0731) \
    Progetto open source per scopi educativi e di ricerca.
  ]
]
