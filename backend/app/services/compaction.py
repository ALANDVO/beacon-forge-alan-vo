"""Event-log compaction engine.

Addresses opencode issue #33356: the ``message.updated.1``-style snapshot events
grow without bound because full-snapshots are retained forever.  The compaction
engine prunes superseded snapshots — only the most recent ``snapshot`` event per
goal is kept; all individual transition events (``created``, ``started``,
``completed`` …) and notes are retained for auditability.

Compaction is a pure domain operation: given an in-memory list of events ordered
by ``seq``, it returns the compacted list and the set of event ids to delete.
The DB layer calls this before bulk-deleting pruned rows.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..models.event import EventType
from ..models.goal import GoalModel


@dataclass(frozen=True)
class CompactedLog:
    """Result of compressing an event stream."""

    retained_event_ids: list[str]   # events to keep, ordered by seq
    deleted_event_ids: list[str]    # events to mark for deletion
    latest_snapshot_id: str | None  # id of the retained latest snapshot

    @property
    def total_pruned(self) -> int:
        return len(self.deleted_event_ids)


class CompactionEngine:
    """Collapses superseded snapshot events, preserving the audit trail."""

    def compact(self, events: list) -> CompactedLog:
        """Return ``CompactedLog`` for the given event list.

        ``events`` must be ordered ascending by ``seq``.  Each event must have
        ``id``, ``event_type`` (an ``EventType`` or its ``value`` string), and
        ``seq`` attributes.
        """
        # Group snapshot event ids by goal (single goal per call).
        snapshot_ids: list[str] = []
        other_ids: list[str] = []

        for ev in events:
            etype = ev.event_type.value if hasattr(ev.event_type, "value") else str(ev.event_type)
            if etype == EventType.SNAPSHOT.value:
                snapshot_ids.append(ev.id)
            else:
                other_ids.append(ev.id)

        # Keep only the last snapshot (highest seq).  If multiple, delete earlier.
        latest_snapshot: str | None = None
        deleted: list[str] = []
        if len(snapshot_ids) > 1:
            # snapshots are in seq order; keep the last.
            latest_snapshot = snapshot_ids[-1]
            deleted.extend(snapshot_ids[:-1])
        elif len(snapshot_ids) == 1:
            latest_snapshot = snapshot_ids[0]

        retained = other_ids + ([latest_snapshot] if latest_snapshot else [])
        # Sort retained by their original position in the input.
        id_to_index = {ev.id: i for i, ev in enumerate(events)}
        retained.sort(key=lambda eid: id_to_index.get(eid, 0))

        return CompactedLog(
            retained_event_ids=retained,
            deleted_event_ids=deleted,
            latest_snapshot_id=latest_snapshot,
        )

    def compact_goal(self, goal: GoalModel, events: list) -> CompactedLog:
        """Convenience wrapper for a single goal's events."""
        return self.compact(events)  # events are already scoped to one goal

    def summary(self, events: list) -> dict[str, int]:
        """Return a count summary by event type — useful for diagnostics."""
        counts: dict[str, int] = {}
        for ev in events:
            etype = ev.event_type.value if hasattr(ev.event_type, "value") else str(ev.event_type)
            counts[etype] = counts.get(etype, 0) + 1
        return counts