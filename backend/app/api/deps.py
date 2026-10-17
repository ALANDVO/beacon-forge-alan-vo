"""Shared API dependencies and pagination helpers."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, Query
from pydantic import BaseModel

from ..core.auth import require_viewer
from ..db import AsyncSession, get_db


class Pagination(BaseModel):
    page: int = Query(default=1, ge=1, le=10000)
    per_page: int = Query(default=20, ge=1, le=100)


def get_pagination(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
) -> Pagination:
    return Pagination(page=page, per_page=per_page)


PaginationDep = Annotated[Pagination, Depends(get_pagination)]
DbDep = Annotated[AsyncSession, Depends(get_db)]
ViewerDep = Annotated[str, Depends(require_viewer)]