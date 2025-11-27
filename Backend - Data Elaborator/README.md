# Earthquake Data Backend

## English

### Overview
This FastAPI backend stores and analyzes measurements coming from distributed misurators across monitored zones. It exposes REST APIs to manage zones, devices, measurements, and statistics plus an alert algorithm that flags seismic events by counting measurements inside a configurable time window (`/alerts/{zone_id}`).

### Architecture
- **FastAPI app** (`api/src/main.py`): handles routing, validation, and business logic.
- **SQLAlchemy ORM** (`api/src/models.py`, `api/src/schemas.py`): maps Zone, Misurator, and Misuration entities.
- **PostgreSQL 15** (`api/docker-compose.yml`): primary data store bootstrapped via `init-scripts`.
- **PgAdmin** (optional): database UI when running through Docker Compose.
- **Alert engine**: uses `ALERT_THRESHOLD = 10` and `ALERT_TIME_WINDOW_SECONDS = 5` (defined in `main.py`) to detect seismic activity.

### Local Setup
#### Requirements
- Python 3.11
- Access to PostgreSQL (or Docker)
- Virtual environment recommended

#### Steps
```bash
cd api
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DATABASE_URL="postgresql://developer:password@localhost:5432/monitoraggio_db"
uvicorn src.main:app --reload
```
The API runs on `http://localhost:8000` and the interactive docs on `http://localhost:8000/docs`.

### Run with Docker
```bash
cd api
docker compose up --build
```
Included services:
- `postgres`: database with persistent volume `postgres_data`.
- `pgadmin`: DB console on `http://localhost:8080`.
- `fastapi-app`: backend on `http://localhost:8000` with live-mounted code.

Pre-built image on GitHub Container Registry:
```bash
docker pull ghcr.io/gizano/earthquake-data-server:1.0.0
```

### Environment Variables
| Name | Purpose | Default (docker-compose) |
|------|---------|---------------------------|
| `DATABASE_URL` | SQLAlchemy URI used by the backend (`api/src/database.py`). | `postgresql://developer:password@postgres:5432/monitoraggio_db` |
| `POSTGRES_DB` | Postgres database name. | `monitoraggio_db` |
| `POSTGRES_USER` | Postgres username. | `developer` |
| `POSTGRES_PASSWORD` | Postgres password. | `password` |
| `PGADMIN_DEFAULT_EMAIL` / `PGADMIN_DEFAULT_PASSWORD` | PgAdmin credentials. | `admin@example.com` / `admin` |

### Data Model
| Entity | Fields | Relationships |
|--------|--------|---------------|
| `Zone` | `id`, `city` | — |
| `Misurator` | `id`, `active`, `zone_id` | `misurators.zone_id -> zones.id` |
| `Misuration` | `id`, `created_at`, `value`, `misurator_id` | `misurations.misurator_id -> misurators.id` |

### API Reference
Default base URL: `http://localhost:8000`

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Root banner with key endpoint hints |
| `GET` | `/health` | Application and DB health check |
| `GET` / `POST` | `/zones/` | List or create zones |
| `GET` / `PUT` / `DELETE` | `/zones/{zone_id}` | Retrieve, update, or delete a zone |
| `GET` / `POST` | `/misurators/` | Manage misurators with `active` and `zone_id` filters |
| `PUT` | `/misurators/{id}/activate` & `/deactivate` | Toggle a misurator active state |
| `GET` / `POST` | `/misurations/` | Retrieve or create measurements with optional filters |
| `GET` | `/alerts/{zone_id}` | Zone alert detection |
| `GET` | `/stats/zones` | Statistics per zone |
| `GET` | `/stats/misurators/{id}` | Statistics for a misurator (last `days`) |
| `GET` | `/docs` | Auto-generated Swagger/OpenAPI UI |

> All request/response schemas live in `api/src/schemas.py`.

### Useful Links
- FastAPI documentation: https://fastapi.tiangolo.com/
- Docker documentation: https://docs.docker.com/
- Main repository: <https://github.com/GiZano/Electro-Domestic-Earthquake-Alarm-System>
- Interactive OpenAPI: `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc`

---

## Italiano

### Panoramica
Questo backend FastAPI archivia e analizza le misurazioni provenienti dai misuratori distribuiti in diverse zone geografiche. Espone API REST per creare, aggiornare e interrogare zone, misuratori, misurazioni e statistiche, oltre a un algoritmo di allerta che rileva attività sismica sulla base di una finestra temporale configurata (`/alerts/{zone_id}`).

### Architettura
- **Applicazione FastAPI** (`api/src/main.py`): gestisce routing, validazione e logica degli endpoint.
- **SQLAlchemy ORM** (`api/src/models.py`, `api/src/schemas.py`): modella Zone, Misurator e Misuration con relazioni basilari.
- **PostgreSQL 15** (`api/docker-compose.yml`): livello di persistenza inizializzato tramite `init-scripts`.
- **PgAdmin** (opzionale): interfaccia DB quando si usa Docker Compose.
- **Motore di allerta**: utilizza `ALERT_THRESHOLD = 10` e `ALERT_TIME_WINDOW_SECONDS = 5` (in `main.py`) per rilevare attività sismica.

### Setup Locale
#### Requisiti
- Python 3.11
- Accesso a PostgreSQL (o Docker)
- Ambiente virtuale consigliato

#### Passi
```bash
cd api
python -m venv .venv && source .venv/bin/activate  # su Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DATABASE_URL="postgresql://developer:password@localhost:5432/monitoraggio_db"
uvicorn src.main:app --reload
```
L'applicazione sarà disponibile su `http://localhost:8000` e la documentazione interattiva su `http://localhost:8000/docs`.

### Esecuzione con Docker
```bash
cd api
docker compose up --build
```
Servizi inclusi:
- `postgres`: database persistente con volume `postgres_data`.
- `pgadmin`: pannello DB su `http://localhost:8080`.
- `fastapi-app`: backend su `http://localhost:8000` con codice montato come volume.

Per usare l’immagine pre-costruita su GitHub Container Registry:
```bash
docker pull ghcr.io/gizano/earthquake-data-server:1.0.0
```

### Variabili d'Ambiente
| Nome | Scopo | Default (docker-compose) |
|------|-------|---------------------------|
| `DATABASE_URL` | URI SQLAlchemy usato dal backend (`api/src/database.py`). | `postgresql://developer:password@postgres:5432/monitoraggio_db` |
| `POSTGRES_DB` | Nome del DB creato dal container Postgres. | `monitoraggio_db` |
| `POSTGRES_USER` | Utente Postgres. | `developer` |
| `POSTGRES_PASSWORD` | Password Postgres. | `password` |
| `PGADMIN_DEFAULT_EMAIL` / `PGADMIN_DEFAULT_PASSWORD` | Credenziali PgAdmin. | `admin@example.com` / `admin` |

### Modello Dati
| Entità | Campi | Relazioni |
|--------|-------|-----------|
| `Zone` | `id`, `city` | — |
| `Misurator` | `id`, `active`, `zone_id` | `misurators.zone_id -> zones.id` |
| `Misuration` | `id`, `created_at`, `value`, `misurator_id` | `misurations.misurator_id -> misurators.id` |

### Riferimento API
Base URL predefinito: `http://localhost:8000`

| Metodo | Path | Descrizione |
|--------|------|-------------|
| `GET` | `/` | Banner iniziale con i principali endpoint |
| `GET` | `/health` | Verifica applicazione e connessione al database |
| `GET` / `POST` | `/zones/` | Lista o creazione delle zone |
| `GET` / `PUT` / `DELETE` | `/zones/{zone_id}` | Dettaglio, aggiornamento o cancellazione di una zona |
| `GET` / `POST` | `/misurators/` | Gestione misuratori con filtri `active` e `zone_id` |
| `PUT` | `/misurators/{id}/activate` & `/deactivate` | Attiva o disattiva un misuratore |
| `GET` / `POST` | `/misurations/` | Consultazione o inserimento di misurazioni con filtri opzionali |
| `GET` | `/alerts/{zone_id}` | Algoritmo di allerta per la zona indicata |
| `GET` | `/stats/zones` | Statistiche per ogni zona |
| `GET` | `/stats/misurators/{id}` | Statistiche per un misuratore (ultimi `days`) |
| `GET` | `/docs` | Interfaccia Swagger/OpenAPI generata automaticamente |

> Tutti gli schemi di richiesta/risposta sono definiti in `api/src/schemas.py`.

### Collegamenti Utili
- Documentazione FastAPI: https://fastapi.tiangolo.com/it/
- Documentazione Docker: https://docs.docker.com/
- Repository principale: <https://github.com/GiZano/Electro-Domestic-Earthquake-Alarm-System>
- OpenAPI interattivo: `http://localhost:8000/docs` (Swagger UI) e `http://localhost:8000/redoc`