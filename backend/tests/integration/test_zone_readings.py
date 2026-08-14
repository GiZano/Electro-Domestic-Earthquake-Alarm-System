"""Integration tests for the per-zone readings endpoint (PostGIS zones).

These verify the zone-scoped seismograph feed: readings are attributed to a
zone through their sensor's ``zone_id`` and sensors in other zones (or with no
zone) never leak into a zone's window.

They skip cleanly when no database is reachable.
"""

import pytest
from sqlalchemy import MetaData, text

from src.database import Base, engine, SessionLocal
from src.main import delete_zone_readings, get_zone_alerts, get_zone_readings
from src.models import Alert, Reading, Sensor, Zone
from geoalchemy2.elements import WKTElement


def _ensure_schema() -> None:
    with engine.begin() as c:
        c.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    # The shared integration conftest mocks Base.metadata.create_all (it is
    # designed for mocked-DB API tests), so run the real DDL through a clean
    # MetaData carrying the ORM tables.
    md = MetaData()
    for table in Base.metadata.tables.values():
        table.to_metadata(md)
    md.create_all(bind=engine)


@pytest.fixture(scope="module")
def zone_db():
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
    except Exception:
        pytest.skip("Database not reachable; skipping zone readings integration tests")

    _ensure_schema()
    with SessionLocal() as session:
        yield session
    engine.dispose()


@pytest.fixture(scope="module")
def seeded_zones_and_sensors(zone_db):
    # Idempotent setup: wipe any leftover test data so repeated runs on a
    # shared/live DB never accumulate readings across executions.
    from src.models import EmergencyReport

    zone_db.query(EmergencyReport).delete()
    zone_db.query(Alert).delete()
    zone_db.query(Reading).delete()
    zone_db.query(Sensor).delete()
    zone_db.query(Zone).filter(Zone.city.in_(["Zone A - Test", "Zone B - Test"])).delete()
    zone_db.commit()

    zone_a = Zone(city="Zone A - Test")
    zone_b = Zone(city="Zone B - Test")
    zone_db.add_all([zone_a, zone_b])
    zone_db.flush()

    sensor_in_a = Sensor(
        active=True,
        zone_id=zone_a.id,
        latitude=45.0,
        longitude=9.0,
        location=WKTElement("POINT(9 45)", srid=4326),
        public_key_hex="a" * 64,
        mac_address="00:00:00:00:00:AA",
    )
    sensor_in_b = Sensor(
        active=True,
        zone_id=zone_b.id,
        latitude=45.1,
        longitude=9.1,
        location=WKTElement("POINT(9.1 45.1)", srid=4326),
        public_key_hex="b" * 64,
        mac_address="00:00:00:00:00:BB",
    )
    sensor_unassigned = Sensor(
        active=True,
        zone_id=zone_b.id,
        latitude=46.0,
        longitude=8.0,
        location=WKTElement("POINT(8 46)", srid=4326),
        public_key_hex="c" * 64,
        mac_address="00:00:00:00:00:CC",
    )
    zone_db.add_all([sensor_in_a, sensor_in_b, sensor_unassigned])
    zone_db.flush()

    from datetime import datetime, timedelta, timezone

    base = datetime.now(timezone.utc)
    for i, value in enumerate([100, 200, 300]):
        zone_db.add(
            Reading(
                value=value,
                sensor_id=sensor_in_a.id,
                recorded_at=base - timedelta(seconds=i),
            )
        )
    zone_db.add(
        Reading(
            value=9999,
            sensor_id=sensor_in_b.id,
            recorded_at=base - timedelta(seconds=1),
        )
    )
    zone_db.add(
        Reading(
            value=7777,
            sensor_id=sensor_unassigned.id,
            recorded_at=base - timedelta(seconds=2),
        )
    )
    zone_db.commit()

    return {"a": zone_a.id, "b": zone_b.id}


class TestGetZoneReadings:
    def test_returns_only_zone_sensors(self, zone_db, seeded_zones_and_sensors):
        readings = get_zone_readings(
            zone_id=seeded_zones_and_sensors["a"], limit=10, db=zone_db
        )
        assert [r.value for r in readings] == [100, 200, 300]
        assert all(r.sensor_id is not None for r in readings)

    def test_other_zone_data_is_excluded(self, zone_db, seeded_zones_and_sensors):
        readings = get_zone_readings(
            zone_id=seeded_zones_and_sensors["a"], limit=10, db=zone_db
        )
        assert 9999 not in [r.value for r in readings]
        assert 7777 not in [r.value for r in readings]

    def test_empty_zone_returns_empty_list(self, zone_db, seeded_zones_and_sensors):
        empty = Zone(city="Zone Empty - Test")
        zone_db.add(empty)
        zone_db.commit()
        readings = get_zone_readings(zone_id=empty.id, limit=10, db=zone_db)
        assert readings == []
        zone_db.delete(empty)
        zone_db.commit()

    def test_missing_zone_raises_404(self, zone_db):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as excinfo:
            get_zone_readings(zone_id=999999, limit=10, db=zone_db)
        assert excinfo.value.status_code == 404


class TestDeleteZoneReadings:
    def test_deletes_only_zone_readings(self, zone_db, seeded_zones_and_sensors):
        result = delete_zone_readings(zone_id=seeded_zones_and_sensors["a"], db=zone_db)
        assert result["deleted"] == 3

        remaining = get_zone_readings(zone_id=seeded_zones_and_sensors["a"], limit=10, db=zone_db)
        assert remaining == []

    def test_other_zone_data_survives(self, zone_db, seeded_zones_and_sensors):
        delete_zone_readings(zone_id=seeded_zones_and_sensors["a"], db=zone_db)
        from src.models import Reading

        other = zone_db.query(Reading).filter(Reading.value.in_([9999, 7777])).count()
        assert other == 2

    def test_missing_zone_raises_404(self, zone_db):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as excinfo:
            delete_zone_readings(zone_id=999999, db=zone_db)
        assert excinfo.value.status_code == 404


class TestGetZoneAlerts:
    def test_returns_zone_alerts_desc(self, zone_db, seeded_zones_and_sensors):
        from datetime import datetime, timedelta, timezone

        base = datetime.now(timezone.utc)
        zone_db.add_all(
            [
                Alert(zone_id=seeded_zones_and_sensors["a"], magnitude=4.0, created_at=base - timedelta(seconds=2)),
                Alert(zone_id=seeded_zones_and_sensors["a"], magnitude=5.2, created_at=base),
            ]
        )
        zone_db.commit()

        alerts = get_zone_alerts(zone_id=seeded_zones_and_sensors["a"], limit=10, db=zone_db)
        assert [a.magnitude for a in alerts] == [5.2, 4.0]

    def test_other_zone_alerts_excluded(self, zone_db, seeded_zones_and_sensors):
        from datetime import datetime, timedelta, timezone

        base = datetime.now(timezone.utc)
        zone_db.add(
            Alert(zone_id=seeded_zones_and_sensors["b"], magnitude=6.0, created_at=base)
        )
        zone_db.commit()

        alerts = get_zone_alerts(zone_id=seeded_zones_and_sensors["a"], limit=10, db=zone_db)
        assert all(a.zone_id == seeded_zones_and_sensors["a"] for a in alerts)

    def test_missing_zone_raises_404(self, zone_db):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as excinfo:
            get_zone_alerts(zone_id=999999, limit=10, db=zone_db)
        assert excinfo.value.status_code == 404
