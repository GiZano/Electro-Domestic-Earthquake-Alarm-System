"""Real TimescaleDB migration tests (run when a live TimescaleDB is reachable).

Skipped automatically when DATABASE_URL points at a plain Postgres/PostGIS
container (e.g. the geo integration job), because the migration is designed to
fail closed there. The dedicated CI job boots timescale/timescaledb so the
hypertable + continuous aggregate paths are exercised against the real engine.
"""

import os

import pytest
from sqlalchemy import text

from src.database import engine, Base
from src.models import Reading, Sensor, Zone
from src.timescale import apply_timescale

pytestmark = pytest.mark.integration


def _seed_zone_and_sensor(session):
    from geoalchemy2.elements import WKTElement

    zone = session.query(Zone).filter(Zone.city == "Unknown Region").first()
    if zone is None:
        zone = Zone(city="Unknown Region")
        session.add(zone)
        session.flush()
    sensor = Sensor(
        active=True,
        zone_id=zone.id,
        latitude=45.46,
        longitude=9.19,
        location=WKTElement("POINT(9.19 45.46)", srid=4326),
        public_key_hex="a" * 64,
        mac_address="00:00:00:00:00:01",
    )
    session.add(sensor)
    session.commit()


@pytest.fixture(scope="module")
def tsdb_session():
    from src.database import SessionLocal
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
    except Exception:
        pytest.skip("Database not reachable; skipping TimescaleDB integration tests")

    with engine.begin() as c:
        c.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    # The shared integration conftest mocks Base.metadata.create_all (it is
    # designed for mocked-DB API tests), so run the real DDL through a clean
    # MetaData carrying the ORM tables.
    from sqlalchemy import MetaData

    md = MetaData()
    for table in Base.metadata.tables.values():
        table.to_metadata(md)
    md.create_all(bind=engine)
    with SessionLocal() as session:
        if session.execute(text("SELECT count(*) FROM sensors")).scalar() == 0:
            _seed_zone_and_sensor(session)
        yield session
    engine.dispose()


class TestHypertableMigration:
    def test_migration_creates_hypertable(self, tsdb_session):
        report = apply_timescale(tsdb_session)
        assert report["hypertable"] is True

    def test_readings_is_listed_as_hypertable(self, tsdb_session):
        row = tsdb_session.execute(
            text(
                "SELECT (EXISTS (SELECT 1 FROM timescaledb_information.hypertables "
                "WHERE hypertable_name = 'readings'))"
            )
        ).scalar()
        assert row is True

    def test_continuous_aggregate_view_exists(self, tsdb_session):
        assert tsdb_session.execute(
            text("SELECT to_regclass('public.readings_minute') IS NOT NULL")
        ).scalar() is True

    def test_orm_insert_into_hypertable(self, tsdb_session):
        from src.database import SessionLocal

        with SessionLocal() as session:
            sensor_id = session.execute(text("SELECT min(id) FROM sensors")).scalar()
            if sensor_id is None:
                pytest.skip("No sensors seeded; can't insert a reading")
            reading = Reading(value=150, sensor_id=sensor_id, latitude=45.46, longitude=9.19)
            session.add(reading)
            session.commit()
            persisted = session.execute(
                text("SELECT count(*) FROM readings WHERE sensor_id = :sid"),
                {"sid": sensor_id},
            ).scalar()
            assert persisted >= 1

    def test_migration_is_idempotent(self, tsdb_session):
        first = apply_timescale(tsdb_session)
        second = apply_timescale(tsdb_session)
        assert first == second
