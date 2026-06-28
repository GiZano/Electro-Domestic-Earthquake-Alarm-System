import pytest
from pydantic import ValidationError
from src.schemas import (
    MisurationCreate, MisuratorCreate, DeviceRegisterRequest,
    ZoneCreate, DemoAlertRequest,
)


class TestMisurationCreate:
    def test_valid_misuration(self):
        m = MisurationCreate(
            value=450,
            misurator_id=1,
            device_timestamp=1700000000,
            signature_hex="a" * 128,
        )
        assert m.value == 450
        assert m.misurator_id == 1

    def test_value_out_of_range(self):
        with pytest.raises(ValidationError):
            MisurationCreate(
                value=99999,
                misurator_id=1,
                device_timestamp=1700000000,
                signature_hex="a" * 128,
            )

    def test_signature_too_short(self):
        with pytest.raises(ValidationError):
            MisurationCreate(
                value=450,
                misurator_id=1,
                device_timestamp=1700000000,
                signature_hex="a" * 10,
            )

    def test_timestamp_too_old(self):
        with pytest.raises(ValidationError):
            MisurationCreate(
                value=450,
                misurator_id=1,
                device_timestamp=1000,
                signature_hex="a" * 128,
            )

    def test_negative_misurator_id(self):
        with pytest.raises(ValidationError):
            MisurationCreate(
                value=450,
                misurator_id=-1,
                device_timestamp=1700000000,
                signature_hex="a" * 128,
            )


class TestMisuratorCreate:
    def test_valid_misurator(self):
        m = MisuratorCreate(
            active=True,
            latitude=41.9,
            longitude=12.5,
            public_key_hex="abcd" * 32,
        )
        assert m.latitude == 41.9

    def test_invalid_latitude(self):
        with pytest.raises(ValidationError):
            MisuratorCreate(
                active=True,
                latitude=100.0,
                longitude=12.5,
                public_key_hex="abcd" * 32,
            )


class TestDeviceRegisterRequest:
    def test_valid_request(self):
        r = DeviceRegisterRequest(
            public_key_hex="abcd" * 32,
            mac_address="AA:BB:CC:DD:EE:FF",
            enrollment_token="token123",
        )
        assert r.mac_address == "AA:BB:CC:DD:EE:FF"

    def test_invalid_mac(self):
        with pytest.raises(ValidationError):
            DeviceRegisterRequest(
                public_key_hex="abcd" * 32,
                mac_address="too_long_mac_address_here",
                enrollment_token="token123",
            )


class TestDemoAlertRequest:
    def test_default_values(self):
        d = DemoAlertRequest()
        assert d.zone_id == 1
        assert d.magnitude == 7.5
        assert d.message == "Simulated Critical Event"


class TestZoneCreate:
    def test_valid_zone(self):
        z = ZoneCreate(city="Test Zone")
        assert z.city == "Test Zone"
