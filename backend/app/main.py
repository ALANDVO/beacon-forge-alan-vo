"""Beacon Forge — FastAPI application factory and entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.goals import router as goals_router
from .api.sessions import router as sessions_router
from .core.config import settings
from .db import init_db

DESCRIPTION = """
Beacon Forge — AI/ML developer tool for managing and evaluating AI coding agent
session goals with token budgets and event-sourced activity timelines.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup; clean up on shutdown."""
    await init_db()
    yield


def create_app() -> FastAPI:
    """Application factory — used by Docker and local dev."""
    app = FastAPI(
        title="Beacon Forge",
        description=DESCRIPTION,
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS — operator configures allowed origins in production.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else ["http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(goals_router)
    app.include_router(sessions_router)

    # Health endpoint.
    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "app": "beacon-forge",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_app()