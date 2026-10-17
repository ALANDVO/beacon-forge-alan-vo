"""Goal domain model — a single objective within an agent session.

Goals have an optional token budget and follow a deterministic lifecycle
state machine (see services/goal_engine.py).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base


class GoalStatus(str, Enum):
    """Lifecycle states for a goal."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class GoalModel(Base):
    __tablename__ = "goals"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    token_budget: Mapped[int | None] = mapped_column(Integer, default=None)
    tokens_consumed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[GoalStatus] = mapped_column(
        SAEnum(GoalStatus), default=GoalStatus.PENDING, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    session: Mapped["SessionModel"] = relationship(back_populates="goals")
    events: Mapped[list["GoalEventModel"]] = relationship(
        back_populates="goal",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Goal {self.id} desc={self.description[:30]!r} status={self.status}>"