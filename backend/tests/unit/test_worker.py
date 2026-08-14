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

    def test_process_fragments_cooldown_by_geohash(self, mock_db_session, mock_redis):
        """GNSS-ready: a sensor fix fragments the cooldown key per-area."""
        _mock_zone(mock_db_session)
        event = {
            "value": 5500,
            "sensor_id": 1,
            "zone_id": 2,
            "latitude": 45.4642,
            "longitude": 9.19,
            "sensor_geohash": "u0nd",
        }
        process_event(event, mock_db_session)
        called_key = mock_redis.set.call_args[0][0]
        assert called_key == "alert_cooldown:u0nd"
        assert mock_redis.set.call_args[1]["nx"] is True

    def test_process_falls_back_to_zone_cooldown_without_fix(self, mock_db_session, mock_redis):
        """Legacy path: coordinates-less sensors keep the per-zone key."""
        _mock_zone(mock_db_session)
        event = {
            "value": 5500,
            "sensor_id": 1,
            "zone_id": 7,
        }
        process_event(event, mock_db_session)
        called_key = mock_redis.set.call_args[0][0]
        assert called_key == "alert_cooldown:zone:7"

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
    def test_loop_moves_batch_error_to_dlq_and_continues(self, mock_redis):
        """Ingestion resilience: a failed batch and a malformed entry go to the DLQ
        stream (and are ACKed), the loop keeps running and later entries still drain."""
        mock_redis.xautoclaim.return_value = ("0-0", [], [])
        db = MagicMock()

        batch = [
            [("readings:stream", [
                [b"1-0", {"payload": '{"value": 150, "sensor_id": 1}'}],
                [b"2-0", {"payload": "{ not-valid-json"}],
                [b"3-0", {"payload": '{"value": 160, "sensor_id": 1}'}],
            ])],
            [],  # xreadgroup timeout -> loop iterates again
            KeyboardInterrupt,
        ]
        mock_redis.xreadgroup.side_effect = batch

        processed = []

        def fake_process_batch(events, session):
            processed.extend(events)
            if any(e.get("sensor_id") == 1 and e.get("value") == 150 for e in events):
                raise RuntimeError("simulated DB failure")

        with patch("src.worker.SessionLocal", return_value=db):
            with patch("src.worker.process_batch", side_effect=fake_process_batch):
                with patch("src.worker.time.sleep"):
                    with pytest.raises(KeyboardInterrupt):
                        run_worker()

        assert db.rollback.called
        dlq_reasons = [c.args[1].get("reason") for c in mock_redis.xadd.call_args_list]
        assert "malformed_json" in dlq_reasons
        assert any(r.startswith("process_error") for r in dlq_reasons)
        assert mock_redis.xack.called
        assert processed[-1]["value"] == 160
