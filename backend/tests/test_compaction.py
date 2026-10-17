"""Unit tests for the EventLogCompactionEngine."""
import pytest

from app.models.event import EventType
from app.services.compaction import CompactionEngine


class _Event:
    """Lightweight stand-in for GoalEventModel for unit tests."""

    def __init__(self, id, seq, event_type, data="{}"):
        self.id = id
        self.seq = seq
        self.event_type = event_type
        self.data = data


@pytest.fixture
def compaction():
    return CompactionEngine()


class TestCompactionEngine:
    def test_keeps_latest_snapshot_only(self, compaction):
        """Multiple snapshots: keep only the one with the highest seq."""
        events = [
            _Event("s1", 1, EventType.SNAPSHOT),
            _Event("e1", 2, EventType.CREATED),
            _Event("s2", 3, EventType.SNAPSHOT),
            _Event("e2", 4, EventType.STARTED),
        ]
        result = compaction.compact(events)
        assert "s1" in result.deleted_event_ids
        assert "s2" not in result.deleted_event_ids
        assert result.latest_snapshot_id == "s2"
        assert "e1" in result.retained_event_ids
        assert "e2" in result.retained_event_ids
        assert result.total_pruned == 1

    def test_single_snapshot_kept(self, compaction):
        """One snapshot: no deletion."""
        events = [
            _Event("s1", 1, EventType.CREATED),
            _Event("snap1", 2, EventType.SNAPSHOT),
            _Event("e1", 3, EventType.STARTED),
        ]
        result = compaction.compact(events)
        assert result.deleted_event_ids == []
        assert result.latest_snapshot_id == "snap1"
        assert len(result.retained_event_ids) == 3

    def test_no_snapshots_no_pruning(self, compaction):
        events = [
            _Event("e1", 1, EventType.CREATED),
            _Event("e2", 2, EventType.STARTED),
            _Event("e3", 3, EventType.COMPLETED),
        ]
        result = compaction.compact(events)
        assert result.deleted_event_ids == []
        assert result.latest_snapshot_id is None
        assert len(result.retained_event_ids) == 3

    def test_many_snapshots_compacted(self, compaction):
        """Simulate issue #33356: many snapshot events."""
        events = [
            _Event(f"snap{i}", i, EventType.SNAPSHOT)
            if i % 3 == 0
            else _Event(f"evt{i}", i, EventType.STARTED if i % 3 == 1 else EventType.COMPLETED)
            for i in range(1, 31)
        ]
        result = compaction.compact(events)
        # Snapshots at seq 3, 6, 9, ... 30 — 10 snapshots, keep 1, prune 9.
        assert result.total_pruned == 9
        assert result.latest_snapshot_id == "snap30"
        # 20 non-snapshot events + 1 snapshot = 21 retained.
        assert len(result.retained_event_ids) == 21

    def test_retained_events_preserve_order(self, compaction):
        events = [
            _Event("e1", 1, EventType.CREATED),
            _Event("s1", 2, EventType.SNAPSHOT),
            _Event("e2", 3, EventType.STARTED),
            _Event("s2", 4, EventType.SNAPSHOT),
        ]
        result = compaction.compact(events)
        # Order should match original seq order.
        id_to_seq = {e.id: e.seq for e in events}
        retained_seqs = [id_to_seq[eid] for eid in result.retained_event_ids]
        assert retained_seqs == sorted(retained_seqs)

    def test_summary_counts(self, compaction):
        events = [
            _Event("e1", 1, EventType.CREATED),
            _Event("e2", 2, EventType.STARTED),
            _Event("e3", 3, EventType.SNAPSHOT),
        ]
        counts = compaction.summary(events)
        assert counts["created"] == 1
        assert counts["started"] == 1
        assert counts["snapshot"] == 1