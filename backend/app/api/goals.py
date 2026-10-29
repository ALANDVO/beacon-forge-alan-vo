"""Goal management, lifecycle transitions, and event-log endpoints."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.deps import DbDep, ViewerDep
from ..models.event import EventType, GoalEventModel
from ..models.goal import GoalModel, GoalStatus
from ..models.schemas import (
    CompactAllResponse,
    CompactResponse,
    EventAppend,
    GoalCreate,
    GoalResponse,
    GoalTarget,
    GoalUpdate,
    PaginatedGoals,
    TimelineResponse,
)
from ..models.session import SessionModel
from ..services.compaction import CompactionEngine
from ..services.goal_engine import GoalLifecycleEngine, GoalStateError

router = APIRouter(prefix="/api", tags=["goals"])

_goal_engine = GoalLifecycleEngine()
_compaction = CompactionEngine()


# ------------------------------------------------------------------ #
# Goal CRUD
# ------------------------------------------------------------------ #


@router.post(
    "/sessions/{session_id}/goals",
    response_model=GoalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_goal(
    session_id: str,
    payload: GoalCreate,
    db: DbDep,
    _: ViewerDep,
) -> GoalResponse:
    """Create a goal under a session."""
    row = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
    session = row.scalar_one_or_none()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    now = datetime.now(timezone.utc)
    goal = GoalModel(
        session_id=session_id,
        description=payload.description,
        token_budget=payload.token_budget,
        tokens_consumed=0,
        status=GoalStatus.PENDING,
        created_at=now,
        updated_at=now,
    )
    db.add(goal)
    await db.flush([goal])  # get id before creating event

    # Append a "created" event.
    await _append_event(db, goal.id, EventType.CREATED, {}, 0)
    await db.commit()
    await db.refresh(goal)
    return goal


@router.get("/goals", response_model=PaginatedGoals)
async def list_goals(
    db: DbDep,
    _: ViewerDep,
    session_id: str | None = None,
    status: GoalStatus | None = None,
    page: int = 1,
    per_page: int = 20,
) -> PaginatedGoals:
    """List goals with optional filtering by session and/or status."""
    stmt = select(GoalModel)
    if session_id is not None:
        stmt = stmt.where(GoalModel.session_id == session_id)
    if status is not None:
        stmt = stmt.where(GoalModel.status == status)
    stmt = stmt.order_by(GoalModel.created_at.desc()).limit(per_page).offset(
        (page - 1) * per_page
    )
    total_stmt = select(func.count()).select_from(GoalModel)
    if session_id is not None:
        total_stmt = total_stmt.where(GoalModel.session_id == session_id)
    if status is not None:
        total_stmt = total_stmt.where(GoalModel.status == status)

    rows = await db.execute(stmt)
    total = await db.scalar(total_stmt)
    goals = rows.scalars().all()
    return PaginatedGoals(
        items=goals,  # type: ignore
        total=total or 0,
        page=page,
        per_page=per_page,
    )


@router.get("/goals/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: str,
    db: DbDep,
    _: ViewerDep,
) -> GoalResponse:
    """Get a single goal."""
    row = await db.execute(select(GoalModel).where(GoalModel.id == goal_id))
    goal = row.scalar_one_or_none()
    if goal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Goal {goal_id} not found",
        )
    return goal


@router.patch("/goals/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: str,
    db: DbDep,
    _: ViewerDep,
    payload: GoalUpdate,
) -> GoalResponse:
    """Update goal description or token budget."""
    row = await db.execute(select(GoalModel).where(GoalModel.id == goal_id))
    goal = row.scalar_one_or_none()
    if goal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Goal {goal_id} not found",
        )
    now = datetime.now(timezone.utc)
    if payload.description is not None:
        goal.description = payload.description
    if payload.token_budget is not None:
        goal.token_budget = payload.token_budget
        await _append_event(
            db,
            goal_id,
            EventType.BUDGET_UPDATED,
            {"token_budget": payload.token_budget},
            goal.tokens_consumed,
        )
    goal.updated_at = now
    await db.commit()
    await db.refresh(goal)
    return goal


@router.delete("/goals/{goal_id}", response_model=GoalResponse)
async def delete_goal(
    goal_id: str,
    db: DbDep,
    _: ViewerDep,
) -> GoalResponse:
    """Delete a goal (hard delete — events cascade via FK)."""
    row = await db.execute(select(GoalModel).where(GoalModel.id == goal_id))
    goal = row.scalar_one_or_none()
    if goal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Goal {goal_id} not found",
        )
    await db.delete(goal)
    await db.commit()
    return goal  # returned before delete for client acknowledgment


# ------------------------------------------------------------------ #
# Lifecycle transitions
# ------------------------------------------------------------------ #


@router.post("/goals/{goal_id}/transition", response_model=GoalResponse)
async def transition_goal(
    goal_id: str,
    payload: GoalTarget,
    db: DbDep,
    _: ViewerDep,
) -> GoalResponse:
    """Transition a goal to a new status via the state machine.

    ``target`` must be one of: running, paused, completed, failed.
    On completion, the token-budget invariant is enforced.
    """
    row = await db.execute(select(GoalModel).where(GoalModel.id == goal_id))
    goal = row.scalar_one_or_none()
    if goal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Goal {goal_id} not found",
        )

    try:
        target_status = GoalStatus(payload.target)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid target status: {payload.target}. "
            f"Valid: {', '.join(s.value for s in GoalStatus)}",
        )

    tokens_spent = payload.tokens_spent or 0

    try:
        result = _goal_engine.transition(
            current=goal.status,
            target=target_status,
            tokens_spent=tokens_spent,
            token_budget=goal.token_budget,
            tokens_consumed_so_far=goal.tokens_consumed,
        )
    except GoalStateError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    if not result.allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.reason or "Transition rejected",
        )

    # Apply transition.
    now = datetime.now(timezone.utc)
    goal.status = result.new_status
    goal.tokens_consumed += result.tokens_added

    if target_status == GoalStatus.RUNNING and goal.started_at is None:
        goal.started_at = now
    if target_status == GoalStatus.COMPLETED:
        goal.completed_at = now
    elif target_status in (GoalStatus.FAILED, GoalStatus.RUNNING):
        goal.completed_at = None  # clear previous completion if retrying

    event_type = _event_type_for_transition(target_status)
    event_data: dict = {"tokens_spent": tokens_spent}
    if payload.note:
        event_data["note"] = payload.note

    await _append_event(db, goal_id, event_type, event_data, goal.tokens_consumed)
    await db.commit()
    await db.refresh(goal)
    return goal


# ------------------------------------------------------------------ #
# Events & timeline
# ------------------------------------------------------------------ #


@router.post("/goals/{goal_id}/events", status_code=status.HTTP_201_CREATED)
async def append_event(
    goal_id: str,
    payload: EventAppend,
    db: DbDep,
    _: ViewerDep,
) -> dict:
    """Append an event to a goal's activity log."""
    row = await db.execute(select(GoalModel).where(GoalModel.id == goal_id))
    goal = row.scalar_one_or_none()
    if goal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Goal {goal_id} not found",
        )
    event = await _append_event(
        db, goal_id, payload.event_type, payload.data or {}, goal.tokens_consumed
    )
    await db.commit()
    return {"id": event.id, "seq": event.seq, "event_type": event.event_type.value}


@router.get("/goals/{goal_id}/timeline", response_model=TimelineResponse)
async def get_timeline(
    goal_id: str,
    db: DbDep,
    _: ViewerDep,
) -> TimelineResponse:
    """Get the compacted timeline for a goal.

    Returns the latest snapshot (if any) plus all non-snapshot events, in
    ``seq`` order.  The compaction engine also prunes superseded snapshots
    from the database on read.
    """
    row = await db.execute(select(GoalModel).where(GoalModel.id == goal_id))
    goal = row.scalar_one_or_none()
    if goal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Goal {goal_id} not found",
        )

    ev_rows = await db.execute(
        select(GoalEventModel)
        .where(GoalEventModel.goal_id == goal_id)
        .order_by(GoalEventModel.seq.asc())
    )
    events = ev_rows.scalars().all()

    # Run compaction: prune superseded snapshots.
    compacted = _compaction.compact(events)
    if compacted.deleted_event_ids:
        await db.execute(
            GoalEventModel.__table__.delete().where(
                GoalEventModel.id.in_(compacted.deleted_event_ids)
            )
        )
        await db.commit()

    # Filter to retained events for the response.
    retained_events = [e for e in events if e.id in set(compacted.retained_event_ids)]
    latest_snapshot = None
    if compacted.latest_snapshot_id:
        latest_snapshot = next(
            (e for e in retained_events if e.id == compacted.latest_snapshot_id),
            None,
        )

    return TimelineResponse(
        goal_id=goal_id,
        goal_status=goal.status.value,
        goal_tokens_consumed=goal.tokens_consumed,
        goal_token_budget=goal.token_budget,
        latest_snapshot=_serialize_event(latest_snapshot) if latest_snapshot else None,
        events=[_serialize_event(e) for e in retained_events],
    )


@router.post("/goals/{goal_id}/compact", response_model=CompactResponse)
async def compact_goal(
    goal_id: str,
    db: DbDep,
    _: ViewerDep,
) -> CompactResponse:
    """Manually trigger compaction for a goal's event log.

    Returns compaction statistics: events before/after, snapshots pruned.
    """
    row = await db.execute(select(GoalModel).where(GoalModel.id == goal_id))
    goal = row.scalar_one_or_none()
    if goal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Goal {goal_id} not found",
        )

    ev_rows = await db.execute(
        select(GoalEventModel)
        .where(GoalEventModel.goal_id == goal_id)
        .order_by(GoalEventModel.seq.asc())
    )
    events = ev_rows.scalars().all()
    total_before = len(events)

    compacted = _compaction.compact(events)

    if compacted.deleted_event_ids:
        await db.execute(
            GoalEventModel.__table__.delete().where(
                GoalEventModel.id.in_(compacted.deleted_event_ids)
            )
        )
        await db.commit()

    total_after = total_before - len(compacted.deleted_event_ids)
    return CompactResponse(
        goal_id=goal_id,
        total_events_before=total_before,
        total_events_after=total_after,
        snapshots_pruned=len(compacted.deleted_event_ids),
        latest_snapshot_id=compacted.latest_snapshot_id,
    )


@router.post("/goals/compact-all", response_model=CompactAllResponse)
async def compact_all_goals(
    db: DbDep,
    _: ViewerDep,
) -> CompactAllResponse:
    """Manually trigger compaction for all goals' event logs.

    Returns aggregate compaction statistics across all goals.
    """
    # Get all goals
    goals_rows = await db.execute(select(GoalModel))
    goals = goals_rows.scalars().all()

    total_goals_compacted = 0
    total_events_before = 0
    total_events_after = 0
    total_snapshots_pruned = 0

    for goal in goals:
        ev_rows = await db.execute(
            select(GoalEventModel)
            .where(GoalEventModel.goal_id == goal.id)
            .order_by(GoalEventModel.seq.asc())
        )
        events = ev_rows.scalars().all()
        if not events:
            continue

        total_before = len(events)
        total_events_before += total_before

        compacted = _compaction.compact(events)

        if compacted.deleted_event_ids:
            await db.execute(
                GoalEventModel.__table__.delete().where(
                    GoalEventModel.id.in_(compacted.deleted_event_ids)
                )
            )
            total_goals_compacted += 1
            total_snapshots_pruned += len(compacted.deleted_event_ids)

        total_events_after += total_before - len(compacted.deleted_event_ids)

    await db.commit()

    return CompactAllResponse(
        goals_compacted=total_goals_compacted,
        total_events_before=total_events_before,
        total_events_after=total_events_after,
        total_snapshots_pruned=total_snapshots_pruned,
    )


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #


async def _append_event(
    db: AsyncSession,
    goal_id: str,
    event_type: EventType,
    data: dict,
    tokens_at_event: int,
) -> GoalEventModel:
    """Get the next sequence number and append an event."""
    max_seq = await db.scalar(
        select(func.max(GoalEventModel.seq)).where(GoalEventModel.goal_id == goal_id)
    )
    seq = (max_seq or 0) + 1
    event = GoalEventModel(
        goal_id=goal_id,
        seq=seq,
        event_type=event_type,
        data=json.dumps(data),
        tokens_at_event=tokens_at_event,
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)
    return event


def _event_type_for_transition(target: GoalStatus) -> EventType:
    """Map a target status to its corresponding event type."""
    if target == GoalStatus.RUNNING:
        return EventType.STARTED
    if target == GoalStatus.PAUSED:
        return EventType.PAUSED
    if target == GoalStatus.COMPLETED:
        return EventType.COMPLETED
    if target == GoalStatus.FAILED:
        return EventType.FAILED
    return EventType.NOTE


def _serialize_event(ev: GoalEventModel) -> dict:
    """Serialize an event model to the response envelope."""
    return {
        "id": ev.id,
        "goal_id": ev.goal_id,
        "seq": ev.seq,
        "event_type": ev.event_type.value,
        "data": json.loads(ev.data) if ev.data else {},
        "tokens_at_event": ev.tokens_at_event,
        "created_at": ev.created_at.isoformat(),
    }