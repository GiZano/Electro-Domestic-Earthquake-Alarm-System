"""
Redis Streams Ingestion Substrate
---------------------------------
Right-sized backpressure + horizontal scale for the IoT ingestion path.

The old design enqueued heartbeats into a Redis LIST ('seismic_events') consumed
by a single worker via BRPOP. Lists cannot support consumer goups, so scale was
bounded to one process and a crash mid-read meant a lost message.

This module replaces that with Redis Streams + consumer groups:
  - Any number of producers XADD to the stream (HTTP API, MQTT bridge, ...).
  - Any number of worker processes consume with XREADGROUP; Redis balances
    deliveries across the group. Adding replicas = `scale worker=N`.
  - XAUTOCLAIM recovers stale pending entries from crashed consumers, so
    at-least-once delivery holds across worker restarts.
  - Unparseable / fatally-failing messages are parked on a DLQ stream and ACKed,
    so a poisoned heartbeat can never stall the group.

Every key can be re-pointed with environment variables so a single backend can
serve multiple logical regions simply by renaming the stream.
"""

import os
from redis.exceptions import ResponseError

# --- Stream / group topology -------------------------------------------------
READINGS_STREAM = os.getenv("READINGS_STREAM", "readings:stream")
READINGS_GROUP = os.getenv("READINGS_GROUP", "quakeguard-ingest")
READINGS_DLQ = os.getenv("READINGS_DLQ", "readings:dlq")
CONSUMER_PREFIX = os.getenv("READINGS_CONSUMER_PREFIX", "worker")
MAXLEN = int(os.getenv("READINGS_STREAM_MAXLEN", "200000"))
MIN_IDLE_MS = int(os.getenv("READINGS_MIN_IDLE_MS", "30000"))
BATCH_SIZE = int(os.getenv("READINGS_BATCH_SIZE", "64"))
BLOCK_MS = int(os.getenv("READINGS_BLOCK_MS", "500"))

# Field name carrying the serialized payload inside each stream entry.
PAYLOAD_FIELD = "payload"


def _is_group_exists(exc: Exception) -> bool:
    """BUSYGROUP (group exists) is the expected steady state -> ignore only it."""
    return isinstance(exc, ResponseError) or "BUSYGROUP" in str(exc)


def ensure_group(client) -> None:
    """Create the consumer group (and stream) if missing. Best-effort: producers
    may legitimately run before any worker, so XADD will create the stream."""
    try:
        client.xgroup_create(
            READINGS_STREAM, READINGS_GROUP, id="0", mkstream=True
        )
    except Exception as exc:  # noqa: BLE001 - re-raise anything unexpected
        if not _is_group_exists(exc):
            raise


async def ensure_group_async(client) -> None:
    """Async counterpart of :func:`ensure_group` for the FastAPI event loop."""
    try:
        await client.xgroup_create(
            READINGS_STREAM, READINGS_GROUP, id="0", mkstream=True
        )
    except Exception as exc:  # noqa: BLE001 - re-raise anything unexpected
        if not _is_group_exists(exc):
            raise


def enqueue_reading(client, payload_json: str) -> str:
    """Append one serialized heartbeat to the stream. Returns its message id."""
    return client.xadd(
        READINGS_STREAM,
        {PAYLOAD_FIELD: payload_json},
        maxlen=MAXLEN,
        approximate=True,
    )


def read_batch(client, consumer: str, count: int = BATCH_SIZE,
               block_ms: int = BLOCK_MS) -> list:
    """Block for new messages assigned to this consumer. Returns a list of
    ``(message_id, payload_json)`` tuples ([] on timeout)."""
    raw = client.xreadgroup(
        READINGS_GROUP, consumer,
        {READINGS_STREAM: ">"},
        count=count,
        block=block_ms,
    )
    if not raw:
        return []
    # raw == [ [stream_name, [[msg_id, {field: value}], ...]] ]
    _, entries = raw[0]
    return [(entry_id, values[PAYLOAD_FIELD]) for entry_id, values in entries]


def ack(client, message_ids) -> None:
    if not message_ids:
        return
    client.xack(READINGS_STREAM, READINGS_GROUP, *message_ids)


def move_to_dlq(client, message_id: str, payload_json: str, reason: str) -> None:
    """Park a poisoned message on the DLQ stream and acknowledge the original."""
    client.xadd(
        READINGS_DLQ,
        {"reason": reason, "original_id": message_id, PAYLOAD_FIELD: payload_json},
        maxlen=MAXLEN,
        approximate=True,
    )
    ack(client, [message_id])


def recover_pending(client, consumer: str, min_idle_ms: int = MIN_IDLE_MS) -> int:
    """Reclaim entries left pending by crashed consumers (at-least-once across
    restarts). Returns the number of reclaimed entries."""
    reclaimed = client.xautoclaim(
        READINGS_STREAM,
        READINGS_GROUP,
        consumer,
        min_idle_time=min_idle_ms,
        start_id="0",
    )
    # XAUTOCLAIM => [next_cursor, [ [id, {field: value}], ... ], deleted_ids]
    return len(reclaimed[1])
