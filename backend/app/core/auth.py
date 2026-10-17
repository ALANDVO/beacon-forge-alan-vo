"""Authentication and authorization.

Round 1: simple API-key gate.  All endpoints reject requests that lack a valid
API key (header ``X-API-Key``).  Unauthenticated → 401.  This stub will be
replaced by full Keycloak OIDC authorization-code login with PKCE in a future
milestone.

Roles (future):
    - viewer  — read-only access to sessions, goals, timelines
    - operator — create sessions, manage goals
    - admin   — full access including deletion and compaction

For now every authenticated key has operator-level privileges.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from .config import settings

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Roles are flat strings; future milestones will map OIDC claims to these.
VIEWER = "viewer"
OPERATOR = "operator"
ADMIN = "admin"
VALID_ROLES = (VIEWER, OPERATOR, ADMIN)


def get_api_key(
    api_key: Annotated[str | None, Security(API_KEY_HEADER)] = None,
) -> str:
    """Extract and validate the API key from the request header.

    Returns the validated key string or raises 401.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "APIKey"},
        )
    # Constant-time comparison to avoid timing attacks.
    import hmac

    if not hmac.compare_digest(api_key, settings.api_key or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "APIKey"},
        )
    return api_key


def require_role(role: str):
    """Dependency factory that enforces a minimum role.

    Future: will inspect the decoded OIDC token for role claims.
    """
    if role not in VALID_ROLES:
        raise ValueError(f"Unknown role: {role}")

    def _enforce(
        api_key: Annotated[str, Depends(get_api_key)] = ...,
    ) -> str:
        # Round 1: any valid key is operator-level.
        if role == VIEWER:
            return api_key
        return api_key

    return _enforce


# Convenience dependency: operator-level (default for write endpoints).
require_operator = require_role(OPERATOR)
require_viewer = require_role(VIEWER)