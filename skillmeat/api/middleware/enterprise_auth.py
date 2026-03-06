"""Enterprise PAT authentication dependency.

Provides ``verify_enterprise_pat``, a FastAPI dependency that validates the
``Authorization: Bearer <token>`` header against the ``ENTERPRISE_PAT_SECRET``
environment variable.

This is the Phase 3 bootstrap auth implementation (ENT-3.4).  It performs a
simple constant-time comparison against a server-side secret — no database
lookup, no Clerk JWT.  Full RBAC / Clerk JWT integration is deferred to PRD 2.

Usage
-----
Apply as a router-level dependency::

    router = APIRouter(dependencies=[Depends(verify_enterprise_pat)])

Or per-endpoint::

    @router.get("/resource")
    def get_resource(auth: Annotated[str, Depends(verify_enterprise_pat)]):
        ...
"""

from __future__ import annotations

import hmac
import logging
import os
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Security scheme
# ---------------------------------------------------------------------------

# auto_error=False so we can return a 401 (not a 403) when the header is absent.
_bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------


def verify_enterprise_pat(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer_scheme),
    ],
) -> str:
    """Validate an enterprise PAT from the ``Authorization: Bearer`` header.

    The expected secret is read from the ``ENTERPRISE_PAT_SECRET`` environment
    variable at call-time (not at import-time), so it can be injected by the
    test harness or a secrets manager without restarting the process.

    Parameters
    ----------
    credentials:
        Parsed ``Authorization: Bearer <token>`` header injected by FastAPI.
        ``None`` when the header is absent or malformed.

    Returns
    -------
    str
        The validated token string.

    Raises
    ------
    HTTPException(401)
        When the ``Authorization`` header is missing or not a Bearer token.
    HTTPException(403)
        When the token is present but does not match ``ENTERPRISE_PAT_SECRET``.
    """
    if not credentials:
        logger.warning("Enterprise PAT auth: missing Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header — Bearer token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token: str = credentials.credentials
    expected: str | None = os.environ.get("ENTERPRISE_PAT_SECRET")

    if not expected:
        # Server misconfiguration: secret not set.  Fail closed.
        logger.error(
            "Enterprise PAT auth: ENTERPRISE_PAT_SECRET is not configured; "
            "rejecting all requests."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Enterprise authentication is not configured on this server.",
        )

    # Use constant-time comparison to prevent timing attacks.
    if not hmac.compare_digest(token.encode(), expected.encode()):
        logger.warning("Enterprise PAT auth: invalid token presented")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid enterprise PAT.",
        )

    logger.debug("Enterprise PAT auth: token validated successfully")
    return token


# ---------------------------------------------------------------------------
# Type alias for cleaner route signatures
# ---------------------------------------------------------------------------

EnterprisePATDep = Annotated[str, Depends(verify_enterprise_pat)]
