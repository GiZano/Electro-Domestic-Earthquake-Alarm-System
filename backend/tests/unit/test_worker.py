import json
from types import SimpleNamespace
import pytest
from unittest.mock import MagicMock, patch

from src.models import EmergencyReport
from src.worker import estimate_magnitude, process_event, run_worker


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

    def test_50_duplicate_triggers_enqueue_single_ai_task(self, mock_db_session, mock_redis):
        """Resilience (Redis): 50 rapid triggers for the same zone must yield exactly one AI task."""
        _mock_zone(mock_db_session)

        call_count = {"n": 0}

        def fake_cooldown_set(*args, **kwargs):
            call_count["n"] += 1
            return call_count["n"] == 1  # First trigger acquires the cooldown, the rest are suppressed

        mock_redis.set.side_effect = fake_cooldown_set

        with patch("src.worker.AI_REPORT_ENABLED", True):
            for _ in range(50):
                process_event(
                    {"value": 5500, "sensor_id": 1, "zone_id": 2},
                    mock_db_session,
                )

        assert mock_redis.lpush.call_count == 1
        assert mock_redis.publish.call_count == 1
        queue, payload = mock_redis.lpush.call_args[0]
        assert queue == "ai_report_queue"
        assert json.loads(payload)["magnitude"] >= 4.5


class TestWorkerLoopResilience:
    def test_loop_moves_db_error_to_dlq_and_continues(self, mock_redis):
        """Ingestion resilience: an event that raises is pushed to the DLQ, loop keeps running."""
        db = MagicMock()

        batch = [
            (b"seismic_events", json.dumps({"value": 150, "sensor_id": 1})),
            (b"seismic_events", "{ not-valid-json"),  # malformed -> consumer must survive
            (b"seismic_events", json.dumps({"value": 160, "sensor_id": 1})),
            None,  # brpop timeout -> loop iterates again
            KeyboardInterrupt,
        ]
        mock_redis.brpop.side_effect = batch

        processed = []

        def fake_process_event(event, session):
            processed.append(event)
            if event.get("sensor_id") == 1 and event.get("value") == 150:
                raise RuntimeError("simulated DB failure")

        with patch("src.worker.SessionLocal", return_value=db):
            with patch("src.worker.process_event", side_effect=fake_process_event):
                with patch("src.worker.time.sleep"):
                    with pytest.raises(KeyboardInterrupt):
                        run_worker()

        assert db.rollback.called
        assert mock_redis.lpush.called
        dlq_queue, dlq_payload = mock_redis.lpush.call_args[0]
        assert dlq_queue == "seismic_events_dlq"
        assert json.loads(dlq_payload)["value"] == 150
        assert mock_redis.brpop.call_count >= 4
        # Second + third valid/clean items still reached process_event
        assert processed[-1]["value"] == 160
