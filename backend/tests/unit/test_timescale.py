from unittest.mock import MagicMock

from src import timescale


class FakeResult:
    def __init__(self, scalar):
        self._scalar = scalar

    def scalar(self):
        return self._scalar


def _db_with_execute(fn):
    db = MagicMock()
    db.execute.side_effect = fn
    return db


def _ok_execute(statement, *args, **kwargs):
    """Success for everything except Timescale policy helpers (already-exists)."""
    s = str(statement)
    if "add_continuous_aggregate_policy" in s or "add_compression_policy" in s \
            or "add_retention_policy" in s:
        raise Exception("policy already exists")
    if "timescaledb_information.hypertables" in s:
        return FakeResult(False)
    return MagicMock()


class TestApplyTimescale:
    def test_noop_when_extension_unavailable(self):
        db = _db_with_execute(lambda *a, **k: (_ for _ in ()).throw(Exception("extension not found")))
        report = timescale.apply_timescale(db)
        assert report["timescaledb"] is False
        assert report["hypertable"] is False
        assert report["aggregate"] is False

    def test_creates_hypertable_and_aggregate_when_missing(self):
        db = _db_with_execute(_ok_execute)
        report = timescale.apply_timescale(db)
        assert report["timescaledb"] is True
        assert report["hypertable"] is True
        assert report["aggregate"] is True
        calls = [str(c.args[0]) for c in db.execute.call_args_list]
        assert any("create_hypertable" in c for c in calls)
        assert any("readings_minute" in c for c in calls)
        assert any("create extension if not exists timescaledb" in c.lower() for c in calls)

    def test_skips_hypertable_when_already_present(self):
        def fake_execute(statement, *args, **kwargs):
            s = str(statement)
            if "timescaledb_information.hypertables" in s:
                return FakeResult(True)
            return MagicMock()

        db = _db_with_execute(fake_execute)
        report = timescale.apply_timescale(db)
        assert report["hypertable"] is True
        calls = [str(c.args[0]) for c in db.execute.call_args_list]
        assert not any("create_hypertable" in c for c in calls)

    def test_continues_after_hypertable_failure(self):
        def fake_execute(statement, *args, **kwargs):
            s = str(statement)
            if "create_hypertable" in s:
                raise Exception("TimescaleDB extension not loaded (shared_preload_libraries)")
            return _ok_execute(statement, *args, **kwargs)

        db = _db_with_execute(fake_execute)
        report = timescale.apply_timescale(db)
        assert report["timescaledb"] is True
        assert report["hypertable"] is False
        assert report["aggregate"] is True

    def test_tolerates_already_existing_policies(self):
        db = _db_with_execute(_ok_execute)
        report = timescale.apply_timescale(db)
        assert report["aggregate"] is True
        assert report["retention"] is True
        db.rollback.assert_called()
