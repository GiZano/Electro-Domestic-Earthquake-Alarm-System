from unittest.mock import MagicMock

from src import ingest


def _client():
    return MagicMock()


class TestEnqueueReading:
    def test_xadd_with_maxlen_and_payload_field(self):
        client = _client()
        client.xadd.return_value = "42-0"
        mid = ingest.enqueue_reading(client, '{"value": 150}')
        assert mid == "42-0"
        args, kwargs = client.xadd.call_args
        assert args[0] == ingest.READINGS_STREAM
        assert args[1] == {ingest.PAYLOAD_FIELD: '{"value": 150}'}
        assert kwargs["maxlen"] == ingest.MAXLEN
        assert kwargs["approximate"] is True


class TestReadBatch:
    def test_returns_empty_on_timeout(self):
        client = _client()
        client.xreadgroup.return_value = None
        assert ingest.read_batch(client, "worker-a") == []

    def test_parses_entries_and_forwards_group(self):
        client = _client()
        client.xreadgroup.return_value = [
            ["readings:stream", [["1-0", {"payload": "{}"}], ["2-0", {"payload": "{}"}]]]
        ]
        batch = ingest.read_batch(client, "worker-a", count=2, block_ms=100)
        assert batch == [("1-0", "{}"), ("2-0", "{}")]
        args, kwargs = client.xreadgroup.call_args
        assert args[0] == ingest.READINGS_GROUP
        assert args[1] == "worker-a"
        assert args[2] == {ingest.READINGS_STREAM: ">"}
        assert kwargs["count"] == 2
        assert kwargs["block"] == 100


class TestAck:
    def test_ack_skips_empty_list(self):
        client = _client()
        ingest.ack(client, [])
        client.xack.assert_not_called()

    def test_ack_forwards_ids(self):
        client = _client()
        ingest.ack(client, ["1-0", "2-0"])
        client.xack.assert_called_once_with(
            ingest.READINGS_STREAM, ingest.READINGS_GROUP, "1-0", "2-0"
        )


class TestMoveToDlq:
    def test_parks_message_and_acks_original(self):
        client = _client()
        ingest.move_to_dlq(client, "5-0", '{"x": 1}', reason="malformed_json")
        args, _ = client.xadd.call_args
        assert args[0] == ingest.READINGS_DLQ
        assert args[1]["reason"] == "malformed_json"
        assert args[1]["original_id"] == "5-0"
        client.xack.assert_called_once_with(
            ingest.READINGS_STREAM, ingest.READINGS_GROUP, "5-0"
        )


class TestEnsureGroup:
    def test_ignores_busygroup(self):
        client = _client()
        client.xgroup_create.side_effect = Exception("BUSYGROUP Consumer Group name already exists")
        ingest.ensure_group(client)  # must not raise
        client.xgroup_create.assert_called_once()

    def test_creates_with_mkstream(self):
        client = _client()
        ingest.ensure_group(client)
        client.xgroup_create.assert_called_once_with(
            ingest.READINGS_STREAM, ingest.READINGS_GROUP, id="0", mkstream=True
        )


class TestRecoverPending:
    def test_counts_reclaimed_entries(self):
        client = _client()
        client.xautoclaim.return_value = ("9-9", [["1-0", {}], ["2-0", {}]], [])
        assert ingest.recover_pending(client, "worker-a") == 2
