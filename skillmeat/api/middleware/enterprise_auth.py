"""Enterprise PAT authentication dependency.

Provides ``verify_enterprise_pat``, a FastAPI dependency that validates the
``Authorization: Bearer <token>`` header against the ``ENTERPRISE_PAT_SECRET``
environment variable and returns a structured :class:`AuthContext`.

This is the Phase 3 bootstrap auth implementation (ENT-3.4).  It performs a
simple constant-time comparison against a server-side secret — no database
lookup, no Clerk JWT.  Full RBAC / Clerk JWT integration is deferred to PRD 2.

Because the PAT is a static shared secret (no JWT claims), the returned
``AuthContext`` is synthesised with a stable enterprise service-account UUID
(``ENTERPRISE_SERVICE_USER_ID``), ``system_admin`` role, and the full scope
set.  ``tenant_id`` is ``None`` at this bootstrap phase; it will be wired to
the authenticated identity in a later phase.

Usage
-----
Apply as a router-level dependency::

    router = APIRouter(dependencies=[Depends(verify_enterprise_pat)])

Or per-endpoint (captures the returned AuthContext)::

    @router.get("/resource")
    def get_resource(auth: EnterprisePATDep):
        if auth.is_admin():
            ...
"""

from __future__ import annotations

import hmac
import logging
import os
import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from skillmeat.api.schemas.auth import AuthContext, Role, Scope

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Enterprise service-account sentinel
# ---------------------------------------------------------------------------

#: Stable UUID representing the enterprise PAT service account.
#: Distinct from ``LOCAL_ADMIN_USER_ID`` (``00000000-0000-4000-a000-000000000002``)
#: so that audit logs can distinguish local-admin actions from enterprise-API
#: actions.  When Clerk JWT integration lands this will be replaced by the
#: real user UUID extracted from the token claims.
ENTERPRISE_SERVICE_USER_ID: uuid.UUID = uuid.UUID(
    "00000000-0000-4000-a000-000000000003"
)

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
) -> AuthContext:
    """Validate an enterprise PAT from the ``Authorization: Bearer`` header.

    The expected secret is read from the ``ENTERPRISE_PAT_SECRET`` environment
    variable at call-time (not at import-time), so it can be injected by the
    test harness or a secrets manager without restarting the process.

    On success a fully-populated :class:`~skillmeat.api.schemas.auth.AuthContext`
    is returned.  The context carries:

    * ``user_id`` — :data:`ENTERPRISE_SERVICE_USER_ID` (stable sentinel UUID).
    * ``tenant_id`` — ``None`` (bootstrap phase; wired in a later phase).
    * ``roles`` — ``[Role.system_admin]``.
    * ``scopes`` — all defined :class:`~skillmeat.api.schemas.auth.Scope` values.

    Parameters
    ----------
    credentials:
        Parsed ``Authorization: Bearer <token>`` header injected by FastAPI.
        ``None`` when the header is absent or malformed.

    Returns
    -------
    AuthContext
        Immutable auth context for the validated enterprise service account.

    Raises
    ------
    HTTPException(401)
        When the ``Authorization`` header is missing or not a Bearer token.
    HTTPException(403)
        When the token is present but does not match ``ENTERPRISE_PAT_SECRET``,
        or when ``ENTERPRISE_PAT_SECRET`` is not configured on the server.
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
    return AuthContext(
        user_id=ENTERPRISE_SERVICE_USER_ID,
        tenant_id=None,
        roles=[Role.system_admin.value],
        scopes=[s.value for s in Scope],
    )


# ---------------------------------------------------------------------------
# Type alias for cleaner route signatures
# ---------------------------------------------------------------------------

EnterprisePATDep = Annotated[AuthContext, Depends(verify_enterprise_pat)]
