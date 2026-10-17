"""Session management REST endpoints."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
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
) -> PaginatedSessions:
    """List sessions with pagination, most recent first."""
    offset = (page - 1) * per_page
    total = await db.scalar(select(func.count()).select_from(SessionModel))
    rows = await db.execute(
        select(SessionModel)
        .order_by(SessionModel.created_at.desc())
        .limit(per_page)
        .offset(offset)
    )
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