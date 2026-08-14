"""
Real-spatial integration tests (run when a live PostGIS + Redis are reachable).

These tests exercise the actual seeded polygons and the Redis zone index, so
they cross-validate the pure-Python geohash encoder against PostGIS
``ST_GeoHash`` and assert ``resolve_zone`` on known coordinates.

They skip cleanly when no database/redis is reachable (the shared integration
conftest runs against mocked infra in the base CI job); a dedicated CI job
runs them against the seeded Docker stack.
"""

import os

import pytest
from sqlalchemy import text

from src.database import Base, engine, SessionLocal
from src.geo import (
    COOLDOWN_PRECISION,
    ZONE_INDEX_PRECISION,
    build_zone_index,
    candidate_zone_ids,
    clear_zone_index,
    point_to_geohash,
    redis_sync,
)
from src.main import resolve_zone
from src.seed import seed_zones

# (latitude, longitude, expected zone name)
KNOWN_POINTS = [
    (45.4642, 9.1900, "Italy - North"),        # Milan
    (40.4168, -3.7038, "Western Europe"),      # Madrid
    (35.6762, 139.6503, "East Asia"),          # Tokyo
    (48.8566, 2.3522, "Western Europe"),       # Paris
    (4.7110, -74.0721, "South America"),       # Bogota
    (-23.5505, -46.6333, "South America"),     # Sao Paulo
    (37.7749, -122.4194, "North America"),     # San Francisco
    (-1.2833, 36.8167, "Unknown Region"),      # Nairobi (no polygon)
]


@pytest.fixture(scope="module")
def infra_available():
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        redis_sync.ping()
    except Exception:
        pytest.skip("PostGIS and/or Redis not reachable; skipping spatial integration tests")
        return

    # Create only the `zones` table via raw DDL: the shared integration conftest
    # replaces Base.metadata.create_all with a mock (it is designed for
    # mocked-DB tests), so we bypass it with an explicit schema.
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS zones CASCADE"))
        conn.execute(
            text(
                "CREATE TABLE zones ("
                "id SERIAL PRIMARY KEY, "
                "city VARCHAR(100) NOT NULL UNIQUE, "
                "created_at TIMESTAMPTZ NOT NULL DEFAULT now(), "
                "geom geometry(Polygon, 4326))"
            )
        )
    try:
        with SessionLocal() as db:
            seed_zones(db)
            build_zone_index(db)
        yield True
    finally:
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS zones CASCADE"))
        clear_zone_index()


def zone_name_of(zone_id: int) -> str:
    with SessionLocal() as db:
        row = db.execute(text("SELECT city FROM zones WHERE id = :zid"), {"zid": zone_id}).first()
        return row[0] if row else "missing"


class TestResolveZoneReal:
    @pytest.mark.parametrize("lat,lon,expected", KNOWN_POINTS)
    def test_resolves_known_points(self, infra_available, lat, lon, expected):
        with SessionLocal() as db:
            assert zone_name_of(resolve_zone(db, lat, lon)) == expected

    def test_null_coordinates_use_unknown(self, infra_available):
        with SessionLocal() as db:
            assert zone_name_of(resolve_zone(db, None, None)) == "Unknown Region"


class TestGeohashVsPostGIS:
    @pytest.mark.parametrize(
        "lat,lon",
        [(45.4642, 9.19), (40.4168, -3.7038), (35.6762, 139.6503), (0.0, 0.0), (-33.8688, 151.2093)],
    )
    def test_encoder_matches_st_geohash(self, infra_available, lat, lon):
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT ST_GeoHash(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), :prec)"),
                {"lon": lon, "lat": lat, "prec": ZONE_INDEX_PRECISION},
            ).first()
        assert row[0] == point_to_geohash(lat, lon, ZONE_INDEX_PRECISION)

    def test_cooldown_geohash_matches_st_geohash(self, infra_available):
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT ST_GeoHash(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), :prec)"),
                {"lon": -74.006, "lat": 40.7128, "prec": COOLDOWN_PRECISION},
            ).first()
        assert row[0] == point_to_geohash(40.7128, -74.006, COOLDOWN_PRECISION)


class TestZoneIndexFastPath:
    def test_candidates_resolve_to_expected_zone(self, infra_available):
        with SessionLocal() as db:
            milan_id = resolve_zone(db, 45.4642, 9.1900)
        candidates = candidate_zone_ids(45.4642, 9.1900, precision=ZONE_INDEX_PRECISION)
        assert milan_id in candidates

    def test_unknown_point_has_no_candidates(self, infra_available):
        assert candidate_zone_ids(-1.2833, 36.8167, precision=ZONE_INDEX_PRECISION) == set()

    def test_index_header_env(self, infra_available):
        """Sanity: precision env knobs are processable ints in the default range."""
        assert 1 <= ZONE_INDEX_PRECISION <= 12
        assert 1 <= COOLDOWN_PRECISION <= 12