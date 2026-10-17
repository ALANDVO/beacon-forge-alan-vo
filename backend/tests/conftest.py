"""Pytest fixtures for Beacon Forge backend tests.

Environment variables are set *before* any application import so that
pydantic-settings picks up the test database URL and API key.
"""
import os

# MUST be set before importing app modules so config picks them up.
os.environ["DATABASE_URL"] = "sqlite:///./test_beacon_forge.db"
os.environ["API_KEY"] = "test-secret-key"
os.environ["DEBUG"] = "false"

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db import Base, engine, init_db
from app.main import app

TEST_API_KEY = "test-secret-key"


@pytest.fixture(scope="session", autouse=True)
async def _setup_db():
    """Create all tables once for the test session."""
    await init_db()
    yield


@pytest.fixture(autouse=True)
async def _clean_db():
    """Truncate all tables before each test for isolation."""
    from app.db import Base
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(text(f"DELETE FROM {table.name}"))
    yield


@pytest.fixture
async def client():
    """AsyncClient with a valid API key."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": TEST_API_KEY},
    ) as ac:
        yield ac


@pytest.fixture
async def no_auth_client():
    """AsyncClient without an API key — all requests should get 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac