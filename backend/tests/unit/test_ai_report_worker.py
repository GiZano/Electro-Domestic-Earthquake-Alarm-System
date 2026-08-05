import json
import requests
from types import SimpleNamespace
import pytest
from unittest.mock import MagicMock, patch

from src.ai_report_worker import process_ai_event, mark_failed, run_ai_worker
from src.ollama_client import STATUS_COMPLETED, STATUS_FAILED


@pytest.fixture
def mock_ai_redis():
    with patch("src.ai_report_worker.redis_sync") as m:
        m.publish.return_value = 1
        yield m


def _make_report(status="PENDING"):
    return SimpleNamespace(
        id=10,
        alert_id=5,
        zone_id=2,
        magnitude=5.0,
        status=status,
        summary=None,
        recommendations=None,
        model_used=None,
        error=None,
    )


class TestProcessAiEvent:
    def test_success_transitions_to_completed(self, mock_db_session, mock_ai_redis):
        report = _make_report()
        mock_db_session.query.return_value.filter.return_value.first.return_value = report

        with patch(
            "src.ai_report_worker.generate_report",
            return_value={"summary": "Event detected.", "recommendations": ["Stay safe."], "model": "test-model"},
        ):
            process_ai_event({"report_id": 10, "alert_id": 5}, mock_db_session)

        assert report.status == STATUS_COMPLETED
        assert report.summary == "Event detected."
        assert report.model_used == "test-model"
        mock_db_session.commit.assert_called()
        mock_ai_redis.publish.assert_called_once()

        payload = json.loads(mock_ai_redis.publish.call_args[0][1])
        assert payload["type"] == "EMERGENCY_REPORT"
        assert payload["status"] == "COMPLETED"
        assert payload["recommendations"] == ["Stay safe."]

    def test_failure_transitions_to_failed(self, mock_db_session, mock_ai_redis):
        report = _make_report()
        mock_db_session.query.return_value.filter.return_value.first.return_value = report

        with patch(
            "src.ai_report_worker.generate_report",
            return_value={
                "summary": "AI report unavailable.",
                "recommendations": ["Verify with local authorities."],
                "model": "test-model",
                "error": "timeout",
            },
        ):
            process_ai_event({"report_id": 10, "alert_id": 5}, mock_db_session)

        assert report.status == STATUS_FAILED
        assert report.error == "timeout"
        payload = json.loads(mock_ai_redis.publish.call_args[0][1])
        assert payload["status"] == "FAILED"

    def test_missing_report_is_noop(self, mock_db_session, mock_ai_redis):
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        with patch("src.ai_report_worker.generate_report") as mock_gen:
            process_ai_event({"report_id": 999, "alert_id": 5}, mock_db_session)

        mock_gen.assert_not_called()
        mock_ai_redis.publish.assert_not_called()

    def test_missing_report_id_is_noop(self, mock_db_session, mock_ai_redis):
        process_ai_event({"alert_id": 5}, mock_db_session)
        mock_ai_redis.publish.assert_not_called()

    def test_timeout_degrades_to_failed(self, mock_db_session, mock_ai_redis):
        """Graceful degradation: a timeout from Ollama must FAIL the report, never crash."""
        report = _make_report()
        mock_db_session.query.return_value.filter.return_value.first.return_value = report

        with patch(
            "src.ai_report_worker.generate_report",
            return_value={
                "summary": "AI report unavailable.",
                "recommendations": ["Verify with local authorities."],
                "model": "test-model",
                "error": str(requests.Timeout("connect timeout")),
            },
        ):
            process_ai_event({"report_id": 10, "alert_id": 5}, mock_db_session)

        assert report.status == STATUS_FAILED
        assert report.error
        payload = json.loads(mock_ai_redis.publish.call_args[0][1])
        assert payload["status"] == "FAILED"
        assert payload["recommendations"] == []


class TestWorkerLoopResilience:
    def test_loop_moves_failure_to_dlq_and_continues(self, mock_ai_redis):
        """AI resilience: an exception during processing goes to the DLQ, the loop keeps consuming."""
        db = MagicMock()

        batch = [
            (b"ai_report_queue", json.dumps({"report_id": 10, "alert_id": 5})),
            (b"ai_report_queue", json.dumps({"report_id": 20, "alert_id": 6})),
            None,  # brpop timeout -> loop iterates again
            KeyboardInterrupt,
        ]
        mock_ai_redis.brpop.side_effect = batch

        def fake_process(event, session):
            if event.get("report_id") == 10:
                raise RuntimeError("Ollama unreachable")

        with patch("src.ai_report_worker.SessionLocal", return_value=db):
            with patch("src.ai_report_worker.process_ai_event", side_effect=fake_process):
                with patch("src.ai_report_worker.mark_failed") as mock_mark:
                    with patch("src.ai_report_worker.time.sleep"):
                        with pytest.raises(KeyboardInterrupt):
                            run_ai_worker()

        assert db.rollback.called
        dlq_queue, dlq_payload = mock_ai_redis.lpush.call_args[0]
        assert dlq_queue == "ai_report_queue_dlq"
        assert json.loads(dlq_payload)["report_id"] == 10
        mock_mark.assert_called_once_with(10)
        assert mock_ai_redis.brpop.call_count >= 3


class TestMarkFailed:
    def test_marks_pending_as_failed(self):
        report = _make_report()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = report

        with patch("src.ai_report_worker.SessionLocal", return_value=mock_db):
            mark_failed(10)

        assert report.status == STATUS_FAILED
        mock_db.commit.assert_called()
        mock_db.close.assert_called()

    def test_does_not_overwrite_completed(self):
        report = _make_report(status=STATUS_COMPLETED)
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = report

        with patch("src.ai_report_worker.SessionLocal", return_value=mock_db):
            mark_failed(10)

        assert report.status == STATUS_COMPLETED
        mock_db.commit.assert_not_called()
