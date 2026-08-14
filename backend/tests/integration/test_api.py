import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

from src.main import app
from src.database import get_db


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def rate_limited_redis():
    """Redis mock that reports more than 50 requests in the sliding window."""
    mock = AsyncMock()
    mock.zremrangebyscore.return_value = None
    mock.zadd.return_value = 1
    mock.expire.return_value = True
    mock.zcard.return_value = 51
    with patch("src.main.redis_client", mock):
        yield mock


@pytest.fixture
def allow_redis():
    """Redis mock admitting requests (rate limiter below threshold)."""
    mock = AsyncMock()
    mock.zremrangebyscore.return_value = None
    mock.zadd.return_value = 1
    mock.expire.return_value = True
    mock.zcard.return_value = 1
    with patch("src.main.redis_client", mock):
        yield mock


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
        assert resp.status_code == 401

    def test_create_zone(self, client, override_db, auth_headers, allow_redis):
        override_db.query.return_value.filter.return_value.first.return_value = None

        def fake_refresh(obj):
            obj.id = 1

        override_db.refresh.side_effect = fake_refresh
        resp = client.post("/zones/", json={"city": "New Zone"}, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["id"] == 1


class TestSensorsEndpoint:
    def test_list_sensors(self, client, override_db, auth_headers):
        resp = client.get("/sensors/", headers=auth_headers)
        assert resp.status_code == 200

    def test_list_sensors_unauthorized(self, client, override_db):
        resp = client.get("/sensors/")
        assert resp.status_code == 401


class TestReadingsEndpoint:
    def test_get_readings(self, client, override_db, auth_headers):
        resp = client.get("/readings/", headers=auth_headers)
        assert resp.status_code == 200

    def test_get_statistics(self, client, override_db, auth_headers):
        # No continuous aggregate available -> the COUNT fallback path runs.
        override_db.execute.return_value.scalar.return_value = False
        override_db.query.return_value.filter.return_value.count.return_value = 42
        resp = client.get("/sensors/1/statistics", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total_readings"] == 42

    def test_rate_limiter_returns_429(self, client, override_db, auth_headers, rate_limited_redis):
        """Resilience (Redis): beyond 50 req/s on /readings/ the API must throttle with 429."""
        resp = client.post(
            "/readings/",
            json={
                "value": 150,
                "sensor_id": 1,
                "device_timestamp": 1700000000,
                "signature_hex": "ab" * 64,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 429
        assert "Rate limit" in resp.json()["detail"]

    def test_readings_rejects_malformed_json(self, client, override_db, auth_headers, allow_redis):
        """Ingestion robustness: invalid JSON body must be rejected, not crash the API."""
        resp = client.post(
            "/readings/",
            data="{ not-valid-json",
            headers={**auth_headers, "Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    def test_readings_rejects_missing_fields(self, client, override_db, auth_headers, allow_redis):
        """Ingestion robustness: missing required fields must be rejected with 422."""
        resp = client.post(
            "/readings/",
            json={"value": 150},
            headers=auth_headers,
        )
        assert resp.status_code == 422


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
