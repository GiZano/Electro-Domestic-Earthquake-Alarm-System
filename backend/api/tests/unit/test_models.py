from datetime import datetime
from src.models import Zone, Sensor, Reading, Alert


class TestZoneModel:
    def test_create_zone(self):
        z = Zone(city="Test City")
        assert z.city == "Test City"
        assert z.id is None

    def test_zone_repr(self):
        z = Zone(city="Italy - North")
        assert "Italy" in z.city


class TestSensorModel:
    def test_create_sensor(self):
        s = Sensor(
            active=True,
            zone_id=1,
            latitude=41.9,
            longitude=12.5,
            public_key_hex="abcd1234",
        )
        assert s.active is True
        assert s.public_key_hex == "abcd1234"

    def test_inactive_sensor(self):
        s = Sensor(active=False, zone_id=1, public_key_hex="deadbeef")
        assert s.active is False


class TestReadingModel:
    def test_create_reading(self):
        r = Reading(value=450, sensor_id=1)
        assert r.value == 450
        assert r.sensor_id == 1
        assert r.recorded_at is None

    def test_reading_relations(self):
        sensor = Sensor(active=True, zone_id=1, public_key_hex="key")
        r = Reading(value=100, sensor_id=1, sensor=sensor)
        assert r.sensor.public_key_hex == "key"


class TestAlertModel:
    def test_create_alert(self):
        a = Alert(zone_id=1, magnitude=4.5, message="Test alert")
        assert a.magnitude == 4.5
        assert "Test" in a.message

    def test_alert_defaults(self):
        a = Alert(zone_id=1, magnitude=5.0)
        assert a.message is None
