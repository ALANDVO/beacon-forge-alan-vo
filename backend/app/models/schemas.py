"""Pydantic schemas for the REST API request/response envelopes."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .event import EventType


class SessionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)


class SessionResponse(BaseModel):
    id: str
    name: str
    description: str | None
    status: str
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GoalCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=2000)
    token_budget: int | None = Field(None, ge=1, description="Max tokens the agent may spend.")


class GoalUpdate(BaseModel):
    description: str | None = Field(None, max_length=2000)
    token_budget: int | None = Field(None, ge=1, description="New token budget.")


class GoalTarget(BaseModel):
    target: str = Field(..., description="New status: running, paused, completed, failed")
    tokens_spent: int = Field(0, ge=0)
    note: str | None = Field(None, max_length=2000)


class GoalResponse(BaseModel):
    id: str
    session_id: str
    description: str
    token_budget: int | None
    tokens_consumed: int
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GoalEventResponse(BaseModel):
    id: str
    goal_id: str
    seq: int
    event_type: str
    data: dict[str, Any]
    tokens_at_event: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TimelineResponse(BaseModel):
    goal_id: str
    goal_status: str
    goal_tokens_consumed: int
    goal_token_budget: int | None
    latest_snapshot: GoalEventResponse | None
    events: list[GoalEventResponse]


class EventAppend(BaseModel):
    event_type: EventType
    data: dict[str, Any] | None = None


class PaginatedSessions(BaseModel):
    items: list[SessionResponse]
    total: int
    page: int
    per_page: int


class PaginatedGoals(BaseModel):
    items: list[GoalResponse]
    total: int
    page: int
    per_page: int


class ErrorResponse(BaseModel):
    detail: str