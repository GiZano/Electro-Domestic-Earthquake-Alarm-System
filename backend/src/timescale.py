"""
TimescaleDB Provisioning (best-effort, idempotent)
--------------------------------------------------
Upgrades the ``readings`` table to a TimescaleDB *hypertable* partitioned on
``recorded_at`` so the time-series ingestion path scales with chunking,
compression and continuous aggregates — without touching the ORM model.

The migration is deliberately **best-effort**: on a stock PostGIS container
(no TimescaleDB), every step fails closed with a warning and the application
keeps running on the plain relational table. This lets CI and local dev use the
standard PostGIS image while production uses the TimescaleDB+PostGIS image.

Run manually:   python -m src.timescale
Auto-applied:   on FastAPI startup (see src/main.py lifespan)
"""

import os

from sqlalchemy import text
from sqlalchemy.orm import Session

TSDB_RETENTION_DAYS = os.getenv("TSDB_RETENTION_DAYS", "180")


def apply_timescale(db: Session) -> dict:
    """Apply TimescaleDB DDL where possible. Returns a per-step report dict.

    Steps are isolated: a failure in any step never blocks the others nor the
    application startup.
    """
    report = {
        "timescaledb": False,
        "hypertable": False,
        "aggregate": False,
        "retention": False,
    }

    # 1. Extension ---------------------------------------------------------
    try:
        db.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
        db.commit()
        report["timescaledb"] = True
    except Exception as e:
        db.rollback()
        print(f"⚠️ TimescaleDB extension unavailable: {e}", flush=True)
        return report

    # 2. Hypertable --------------------------------------------------------
    try:
        already_hypertable = db.execute(
            text(
                "SELECT (EXISTS (SELECT 1 FROM timescaledb_information.hypertables "
                "WHERE hypertable_name = 'readings'))"
            )
        ).scalar()
        if not already_hypertable:
            db.execute(
                text(
                    "SELECT create_hypertable('readings', 'recorded_at', "
                    "if_not_exists => TRUE, migrate_data => TRUE)"
                )
            )
        db.commit()
        report["hypertable"] = True
        print("✅ readings is a TimescaleDB hypertable (chunked on recorded_at).", flush=True)
    except Exception as e:
        db.rollback()
        print(f"⚠️ Hypertable creation skipped: {e}", flush=True)

    # 3. Continuous aggregate (per-sensor minute rollups) -------------------
    try:
        db.execute(
            text(
                "CREATE MATERIALIZED VIEW IF NOT EXISTS readings_minute "
                "WITH (timescaledb.continuous) AS "
                "SELECT sensor_id, time_bucket('1 minute', recorded_at) AS bucket, "
                "count(*) AS n, max(value) AS peak "
                "FROM readings GROUP BY sensor_id, bucket WITH NO DATA"
            )
        )
        db.commit()
        try:
            db.execute(
                text(
                    "SELECT add_continuous_aggregate_policy('readings_minute', "
                    "start_offset => INTERVAL '3 hours', "
                    "end_offset => INTERVAL '10 seconds', "
                    "schedule_interval => INTERVAL '1 minute')"
                )
            )
            db.commit()
        except Exception:
            db.rollback()  # policy already present or not yet refreshable
        report["aggregate"] = True
        print("✅ Continuous aggregate readings_minute created.", flush=True)
    except Exception as e:
        db.rollback()
        print(f"⚠️ Continuous aggregate skipped: {e}", flush=True)

    # 4. Compression + retention -------------------------------------------
    try:
        # Newer TimescaleDB (2.13+/3.x) requires columnstore on the hypertable
        # before a columnstore compression policy can be added.
        db.execute(text("ALTER TABLE readings SET (timescaledb.columnstore = true)"))
        db.commit()
    except Exception as e:
        db.rollback()
        if "already" not in str(e).lower():
            print(f"⚠️ Columnstore enable skipped: {e}", flush=True)
    try:
        db.execute(text("SELECT add_compression_policy('readings', INTERVAL '1 day')"))
        db.commit()
    except Exception as e:
        db.rollback()
        if "already exists" not in str(e).lower():
            print(f"⚠️ Compression policy skipped: {e}", flush=True)
    try:
        db.execute(
            text(
                "SELECT add_retention_policy('readings', "
                f"INTERVAL '{TSDB_RETENTION_DAYS} days')"
            )
        )
        db.commit()
        report["retention"] = True
    except Exception as e:
        db.rollback()
        if "already exists" in str(e).lower():
            report["retention"] = True
        else:
            print(f"⚠️ Retention policy skipped: {e}", flush=True)
    if report["retention"]:
        print(f"✅ Retention policy set to {TSDB_RETENTION_DAYS} days.", flush=True)

    return report


def run_migration() -> dict:
    from src.database import SessionLocal
    with SessionLocal() as db:
        report = apply_timescale(db)
    print(f"📋 TimescaleDB migration report: {report}", flush=True)
    return report


if __name__ == "__main__":
    run_migration()
