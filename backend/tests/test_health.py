"""Tests for the health and root endpoints."""
import pytest
from httpx import AsyncClient


async def test_health_endpoint(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "timestamp" in body


async def test_root_endpoint(client: AsyncClient):
    resp = await client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["app"] == "beacon-forge"
    assert body["version"] == "1.0.0"


async def test_health_no_auth(no_auth_client: AsyncClient):
    """Health endpoint does not require auth — it's a readiness probe."""
    resp = await no_auth_client.get("/health")
    assert resp.status_code == 200


async def test_api_requires_auth(no_auth_client: AsyncClient):
    """All /api/ endpoints reject unauthenticated requests."""
    resp = await no_auth_client.get("/api/sessions")
    assert resp.status_code == 401


async def test_invalid_api_key(client: AsyncClient):
    """Invalid API key is rejected with 401."""
    client.headers["X-API-Key"] = "wrong-key"
    resp = await client.get("/api/sessions")
    assert resp.status_code == 401