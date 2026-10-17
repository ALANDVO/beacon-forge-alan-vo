"""SQLAlchemy database setup and session management."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .core.config import settings

# Convert sqlite:/// to sqlite+aiosqlite:/// for async.
db_url = settings.database_url
_connect_args: dict = {}
if db_url.startswith("sqlite:///"):
    db_url = "sqlite+aiosqlite://" + db_url[len("sqlite://"):]
    _connect_args["check_same_thread"] = False
elif db_url.startswith("sqlite://"):
    db_url = "sqlite+aiosqlite://" + db_url[len("sqlite://"):]
    _connect_args["check_same_thread"] = False

engine = create_async_engine(
    db_url,
    echo=settings.debug,
    future=True,
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base with shared metadata."""

    pass


async def init_db() -> None:
    """Create all tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yield an async session."""
    async with AsyncSessionLocal() as session:
        yield session