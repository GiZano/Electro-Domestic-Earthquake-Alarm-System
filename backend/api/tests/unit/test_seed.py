import pytest
from unittest.mock import MagicMock

from src.seed import seed_zones, ZONES_DATA


class TestSeedZones:
    def test_seeds_all_zones(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        seed_zones(mock_db)
        assert mock_db.add.call_count == len(ZONES_DATA)
        assert mock_db.commit.called

    def test_skips_existing_zones(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = MagicMock()
        seed_zones(mock_db)
        assert mock_db.add.call_count == 0

    def test_zones_data_has_expected_regions(self):
        cities = [z["city"] for z in ZONES_DATA]
        assert "Italy - North" in cities
        assert "Western Europe" in cities
        assert "Unknown Region" in cities

    def test_seed_is_idempotent(self):
        mock_db = MagicMock()
        first_mock = MagicMock()
        first_mock.side_effect = [None] * len(ZONES_DATA)
        mock_db.query.return_value.filter.return_value.first = first_mock
        seed_zones(mock_db)
        assert mock_db.add.call_count == len(ZONES_DATA)

        first_mock.side_effect = [MagicMock()] * len(ZONES_DATA)
        seed_zones(mock_db)
        assert mock_db.add.call_count == len(ZONES_DATA)

    def test_unknown_region_has_no_geom(self):
        unknown = next(z for z in ZONES_DATA if z["city"] == "Unknown Region")
        assert unknown["geom"] is None
