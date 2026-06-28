from datetime import datetime
from src.models import Zone, Misurator, Misuration, Alert


class TestZoneModel:
    def test_create_zone(self):
        z = Zone(city="Test City")
        assert z.city == "Test City"
        assert z.id is None

    def test_zone_repr(self):
        z = Zone(city="Italy - North")
        assert "Italy" in z.city


class TestMisuratorModel:
    def test_create_misurator(self):
        m = Misurator(
            active=True,
            zone_id=1,
            latitude=41.9,
            longitude=12.5,
            public_key_hex="abcd1234",
        )
        assert m.active is True
        assert m.public_key_hex == "abcd1234"

    def test_inactive_misurator(self):
        m = Misurator(active=False, zone_id=1, public_key_hex="deadbeef")
        assert m.active is False


class TestMisurationModel:
    def test_create_misuration(self):
        m = Misuration(value=450, misurator_id=1)
        assert m.value == 450
        assert m.misurator_id == 1
        assert m.recorded_at is None

    def test_misuration_relations(self):
        misurator = Misurator(active=True, zone_id=1, public_key_hex="key")
        m = Misuration(value=100, misurator_id=1, misurator=misurator)
        assert m.misurator.public_key_hex == "key"


class TestAlertModel:
    def test_create_alert(self):
        a = Alert(zone_id=1, severity=4.5, message="Test alert")
        assert a.severity == 4.5
        assert "Test" in a.message

    def test_alert_defaults(self):
        a = Alert(zone_id=1, severity=5.0)
        assert a.message is None
