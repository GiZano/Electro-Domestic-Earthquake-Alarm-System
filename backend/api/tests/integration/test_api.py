import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

from src.main import app
from src.database import get_db


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def override_db():
    mock_db = MagicMock()
    mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = []
    app.dependency_overrides[get_db] = lambda: mock_db
    yield mock_db
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    return {"X-API-Key": "ci-test-key-123"}


class TestHealthEndpoint:
    def test_health_returns_503_without_infra(self, client):
        with patch("src.main.redis_client.ping", side_effect=Exception("No Redis")):
            with patch("src.main.ping_db", side_effect=Exception("No DB")):
                resp = client.get("/health")
                assert resp.status_code == 503
                data = resp.json()
                assert data["status"] == "error"


class TestZonesEndpoint:
    def test_list_zones(self, client, override_db, auth_headers):
        resp = client.get("/zones/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_zones_unauthorized(self, client, override_db):
        resp = client.get("/zones/")
        assert resp.status_code == 403

    def test_create_zone(self, client, override_db, auth_headers):
        override_db.query.return_value.filter.return_value.first.return_value = None
        resp = client.post("/zones/", json={"city": "New Zone"}, headers=auth_headers)
        assert resp.status_code == 201


class TestMisuratorsEndpoint:
    def test_list_misurators(self, client, override_db, auth_headers):
        resp = client.get("/misurators/", headers=auth_headers)
        assert resp.status_code == 200

    def test_list_misurators_unauthorized(self, client, override_db):
        resp = client.get("/misurators/")
        assert resp.status_code == 403


class TestMisurationsEndpoint:
    def test_get_misurations(self, client, override_db, auth_headers):
        resp = client.get("/misurations/", headers=auth_headers)
        assert resp.status_code == 200

    def test_get_statistics(self, client, override_db, auth_headers):
        override_db.query.return_value.filter.return_value.count.return_value = 42
        resp = client.get("/sensors/1/statistics", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total_readings"] == 42


class TestDeviceRegistration:
    def test_register_device_invalid_token(self, client, override_db):
        resp = client.post(
            "/devices/register",
            json={
                "public_key_hex": "abcd" * 32,
                "mac_address": "AA:BB:CC:DD:EE:FF",
                "enrollment_token": "wrong_token",
            },
        )
        assert resp.status_code == 401

    def test_register_device_valid(self, client, override_db):
        with patch("src.main.ENROLLMENT_TOKEN", "valid_token"):
            override_db.query.return_value.filter.return_value.first.return_value = None
            resp = client.post(
                "/devices/register",
                json={
                    "public_key_hex": "abcd" * 32,
                    "mac_address": "AA:BB:CC:DD:EE:FF",
                    "enrollment_token": "valid_token",
                    "latitude": 41.9,
                    "longitude": 12.5,
                },
            )
            assert resp.status_code == 201
            data = resp.json()
            assert "sensor_id" in data
