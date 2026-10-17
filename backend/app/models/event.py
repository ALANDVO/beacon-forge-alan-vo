"""Goal event model — immutable append-only event log with snapshots.

Each goal has an event log.  Two event sub-types:

* ``snapshot`` — a full state snapshot (e.g. ``message.updated.1`` equivalent).
  Only the latest snapshot per goal is retained; older ones are pruned by the
  compaction engine (see services/compaction.py).
* ``event`` — an individual state transition or note.  All retained.

This directly addresses opencode issue #33356: unbounded growth from retained
full-snapshot events.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base


class EventType(str, Enum):
    """Types of events in the goal activity log."""

    # Lifecycle transitions
    CREATED = "created"
    STARTED = "started"
    PAUSED = "paused"
    RESUMED = "resumed"
    COMPLETED = "completed"
    FAILED = "failed"

    # State updates
    NOTE = "note"
    BUDGET_UPDATED = "budget_updated"

    # Snapshot — full goal state at a point in time.
    SNAPSHOT = "snapshot"


class GoalEventModel(Base):
    __tablename__ = "goal_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    goal_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("goals.id", ondelete="CASCADE"), nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[EventType] = mapped_column(
        SAEnum(EventType), nullable=False
    )
    data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    tokens_at_event: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    goal: Mapped["GoalModel"] = relationship(back_populates="events")

    def __repr__(self) -> str:
        return (
            f"<GoalEvent goal={self.goal_id[:8]} seq={self.seq} "
            f"type={self.event_type}>"
        )