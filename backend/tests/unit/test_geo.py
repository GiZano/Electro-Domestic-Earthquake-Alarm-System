import math
import pytest
from unittest.mock import MagicMock

from src.geo import (
    _cells_in_bbox,
    _cell_indices_to_geohash,
    candidate_zone_ids,
    geohash_bounds,
    point_to_geohash,
    zone_covering_geohashes,
)


class TestPointToGeohash:
    def test_wikipedia_reference(self):
        # Aalborg University, the canonical geohash example from Wikipedia.
        assert point_to_geohash(57.64911, 10.40744, 11) == "u4pruydqqvj"
        assert point_to_geohash(57.64911, 10.40744, 3) == "u4p"

    def test_known_low_precision(self):
        # London (BBC) resolves to the "gcp" cells at precision 3.
        assert point_to_geohash(51.5218, -0.1817, 3) == "gcp"

    def test_equator_origin(self):
        assert point_to_geohash(0.0, 0.0, 3) == "s00"

    def test_consistent_precision_prefix(self):
        full = point_to_geohash(45.4642, 9.1900, 6)
        assert point_to_geohash(45.4642, 9.1900, 3) == full[:3]


class TestGeohashBounds:
    @pytest.mark.parametrize(
        "lat,lon,prec",
        [(45.4642, 9.19, 4), (-33.8688, 151.2093, 5), (0.0, 0.0, 3), (40.7128, -74.006, 6)],
    )
    def test_point_inside_own_cell(self, lat, lon, prec):
        cell = point_to_geohash(lat, lon, prec)
        lon_min, lat_min, lon_max, lat_max = geohash_bounds(cell)
        assert lon_min <= lon <= lon_max
        assert lat_min <= lat <= lat_max

    def test_cell_indices_reconstruct(self):
        for lat, lon in [(45.4642, 9.19), (35.6762, 139.6503), (-1.2833, 36.8167)]:
            for precision in (3, 4, 5):
                cell = point_to_geohash(lat, lon, precision)
                lon_bits = (precision * 5 + 1) // 2
                lat_bits = precision * 5 // 2
                lon_step = 360.0 / (1 << lon_bits)
                lat_step = 180.0 / (1 << lat_bits)
                lon_min, lat_min, _, _ = geohash_bounds(cell)
                lon_idx = math.floor((lon_min + 180.0) / lon_step)
                lat_idx = math.floor((lat_min + 90.0) / lat_step)
                assert _cell_indices_to_geohash(lon_idx, lat_idx, precision) == cell


class TestCellsInBbox:
    def test_small_bbox(self):
        # ~0.75 deg around Paris -> a handful of prec-3 cells.
        cells = _cells_in_bbox(48.5, 1.9, 49.3, 2.7, 3)
        assert cells
        for cell in cells:
            assert len(cell) == 3

    def test_known_cell_included(self):
        cells = _cells_in_bbox(48.0, 1.0, 50.0, 3.0, 3)
        assert point_to_geohash(48.8566, 2.3522, 3) in cells


class TestCandidateZoneIds:
    def test_resolves_from_redis_set(self):
        mock_redis = MagicMock()
        mock_redis.smembers.return_value = {"7", "9"}
        assert candidate_zone_ids(45.46, 9.19, redis_client=mock_redis) == {7, 9}
        mock_redis.smembers.assert_called_once()

    def test_redis_failure_is_non_fatal(self):
        mock_redis = MagicMock()
        mock_redis.smembers.side_effect = Exception("Redis down")
        assert candidate_zone_ids(45.46, 9.19, redis_client=mock_redis) == set()

    def test_uses_configured_precision(self):
        mock_redis = MagicMock()
        mock_redis.smembers.return_value = set()
        candidate_zone_ids(45.46, 9.19, redis_client=mock_redis, precision=4)
        cell = point_to_geohash(45.46, 9.19, 4)
        mock_redis.smembers.assert_called_once_with(f"zoneindex:{cell}")


class TestZoneCoveringGeohashes:
    def test_queries_db_and_returns_cell_keys(self):
        zone = MagicMock()
        zone.id = 1
        db = MagicMock()

        bbox_result = MagicMock()
        bbox_result.first.return_value = (1.0, 48.0, 3.0, 49.0)
        select_result = MagicMock()
        select_result.fetchall.return_value = [("spd",), ("spe",)]
        # _zone_bbox -> CREATE TEMP TABLE -> DELETE -> INSERT -> SELECT
        db.execute.side_effect = [bbox_result, MagicMock(), MagicMock(), MagicMock(), select_result]

        cells = zone_covering_geohashes(db, zone, precision=3)
        assert cells == ["spd", "spe"]
        assert db.execute.call_count == 5

    def test_empty_bbox_returns_empty(self):
        zone = MagicMock()
        zone.id = 99
        db = MagicMock()
        db.execute.return_value.first.return_value = None
        assert zone_covering_geohashes(db, zone) == []