"""Session management REST endpoints."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from ..api.deps import DbDep, ViewerDep
from ..models.schemas import PaginatedSessions, SessionCreate, SessionResponse
from ..models.session import SessionModel, SessionStatus

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: SessionCreate,
    db: DbDep,
    _: ViewerDep,
) -> SessionResponse:
    """Create a new agent session."""
    now = datetime.now(timezone.utc)
    session = SessionModel(
        name=payload.name,
        description=payload.description,
        status=SessionStatus.ACTIVE,
        started_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("", response_model=PaginatedSessions)
async def list_sessions(
    db: DbDep,
    _: ViewerDep,
    page: int = 1,
    per_page: int = 20,
    status_filter: str | None = Query(default=None, alias="status"),
) -> PaginatedSessions:
    """List sessions with pagination, most recent first.

    Optional ``status_filter`` filter: "active", "archived", or "all" (default).
    """
    offset = (page - 1) * per_page

    query = select(SessionModel).order_by(SessionModel.created_at.desc())
    count_query = select(func.count()).select_from(SessionModel)

    if status_filter and status_filter != "all":
        try:
            session_status = SessionStatus(status_filter)
            query = query.where(SessionModel.status == session_status)
            count_query = count_query.where(SessionModel.status == session_status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status_filter}. Must be 'active', 'archived', or 'all'.",
            )

    total = await db.scalar(count_query)
    rows = await db.execute(query.limit(per_page).offset(offset))
    sessions = rows.scalars().all()
    return PaginatedSessions(
        items=sessions,  # type: ignore
        total=total or 0,
        page=page,
        per_page=per_page,
    )

@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: DbDep,
    _: ViewerDep,
) -> SessionResponse:
    """Get a single session by id."""
    row = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
    session = row.scalar_one_or_none()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    return session


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    db: DbDep,
    _: ViewerDep,
    name: str | None = None,
    description: str | None = None,
) -> SessionResponse:
    """Update session name or description."""
    row = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
    session = row.scalar_one_or_none()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    if name is not None:
        session.name = name
    if description is not None:
        session.description = description
    session.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(session)
    return session


@router.delete("/{session_id}", response_model=SessionResponse)
async def archive_session(
    session_id: str,
    db: DbDep,
    _: ViewerDep,
) -> SessionResponse:
    """Archive (soft-delete) a session.  Goals and events cascade-delete via DB."""
    row = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
    session = row.scalar_one_or_none()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    session.status = SessionStatus.ARCHIVED
    session.ended_at = datetime.now(timezone.utc)
    session.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(session)
    return session


@router.post("/{session_id}/restore", response_model=SessionResponse)
async def restore_session(
    session_id: str,
    db: DbDep,
    _: ViewerDep,
) -> SessionResponse:
    """Restore an archived session back to active status."""
    row = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
    session = row.scalar_one_or_none()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    if session.status != SessionStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session {session_id} is not archived (current status: {session.status.value})",
        )
    session.status = SessionStatus.ACTIVE
    session.ended_at = None
    session.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(session)
    return session