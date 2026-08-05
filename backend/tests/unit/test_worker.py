import json
from types import SimpleNamespace
import pytest
from unittest.mock import MagicMock, patch

from src.models import EmergencyReport
from src.worker import estimate_magnitude, process_event


def _mock_zone(db, city="Test Zone"):
    """Configure the shared mock DB session to return a zone for zone lookups."""
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(city=city)


class TestProcessEvent:
    def test_process_normal_event(self, mock_db_session, mock_redis):
        event = {
            "value": 150,
            "sensor_id": 1,
        }
        process_event(event, mock_db_session)
        assert mock_db_session.add.called
        assert mock_db_session.commit.called

    def test_process_triggers_alert_and_enqueues_ai_report(self, mock_db_session, mock_redis):
        _mock_zone(mock_db_session)
        event = {
            "value": 5500,
            "sensor_id": 1,
            "zone_id": 2,
        }
        with patch("src.worker.AI_REPORT_ENABLED", True):
            process_event(event, mock_db_session)
        assert mock_redis.publish.called
        mock_redis.lpush.assert_called_once()

        queue, payload = mock_redis.lpush.call_args[0]
        assert queue == "ai_report_queue"
        enqueued = json.loads(payload)
        assert enqueued["zone_id"] == 2
        assert enqueued["zone_name"] == "Test Zone"
        assert enqueued["magnitude"] >= 4.5

    def test_process_creates_pending_report_row(self, mock_db_session, mock_redis):
        _mock_zone(mock_db_session)
        added = []

        def fake_add(obj):
            added.append(obj)

        mock_db_session.add.side_effect = fake_add
        event = {
            "value": 5500,
            "sensor_id": 1,
            "zone_id": 2,
        }
        with patch("src.worker.AI_REPORT_ENABLED", True):
            process_event(event, mock_db_session)

        report = next((a for a in added if isinstance(a, EmergencyReport)), None)
        assert report is not None
        assert report.status == "PENDING"

    def test_process_suppresses_duplicate_alert(self, mock_db_session, mock_redis):
        mock_redis.set.return_value = False
        event = {
            "value": 5500,
            "sensor_id": 1,
            "zone_id": 2,
        }
        process_event(event, mock_db_session)
        assert not mock_redis.publish.called
        assert not mock_redis.lpush.called

    def test_process_propagates_db_error(self, mock_db_session, mock_redis):
        mock_db_session.commit.side_effect = Exception("DB Error")
        event = {
            "value": 150,
            "sensor_id": 1,
        }
        with pytest.raises(Exception, match="DB Error"):
            process_event(event, mock_db_session)

    def test_process_below_threshold(self, mock_db_session, mock_redis):
        event = {
            "value": 50,
            "sensor_id": 1,
        }
        process_event(event, mock_db_session)
        assert not mock_redis.publish.called
