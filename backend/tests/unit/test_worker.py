import json
import pytest
from unittest.mock import MagicMock, patch

from src.worker import estimate_magnitude, process_event


class TestProcessEvent:
    def test_process_normal_event(self, mock_db_session, mock_redis):
        event = {
            "value": 150,
            "sensor_id": 1,
        }
        process_event(event, mock_db_session)
        assert mock_db_session.add.called
        assert mock_db_session.commit.called

    def test_process_triggers_alert(self, mock_db_session, mock_redis):
        event = {
            "value": 5500,
            "sensor_id": 1,
            "zone_id": 2,
        }
        process_event(event, mock_db_session)
        assert mock_redis.publish.called

    def test_process_suppresses_duplicate_alert(self, mock_db_session, mock_redis):
        mock_redis.set.return_value = False
        event = {
            "value": 5500,
            "sensor_id": 1,
            "zone_id": 2,
        }
        process_event(event, mock_db_session)
        assert not mock_redis.publish.called

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
