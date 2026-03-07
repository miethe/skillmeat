"""Abstract authentication provider interface for SkillMeat AAA/RBAC system.

Defines the ``AuthProvider`` ABC that all concrete authentication backends must
implement.  The provider pattern decouples the API middleware from any specific
authentication mechanism (local passthrough, Clerk JWT, API key, etc.).

Usage pattern::

    class LocalAuthProvider(AuthProvider):
        async def validate(self, request: Request) -> AuthContext:
            # Local single-tenant mode: always return the admin context.
            from skillmeat.api.schemas.auth import LOCAL_ADMIN_CONTEXT
            return LOCAL_ADMIN_CONTEXT

    class ClerkAuthProvider(AuthProvider):
        async def validate(self, request: Request) -> AuthContext:
            token = request.headers.get("Authorization", "").removeprefix("Bearer ")
            if not token:
                raise HTTPException(status_code=401, detail="Missing bearer token")
            # ... validate JWT with Clerk JWKS ...
            return AuthContext(user_id=..., roles=[...], scopes=[...])

References:
    .claude/progress/aaa-rbac-foundation/  AUTH-001
"""

from __future__ import annotations

import abc

from fastapi import HTTPException, Request

from skillmeat.api.schemas.auth import AuthContext


class AuthProvider(abc.ABC):
    """Abstract base class for SkillMeat authentication providers.

    Concrete providers implement ``validate`` to inspect the incoming HTTP
    request and return an ``AuthContext`` describing the authenticated
    principal.  If authentication fails the method must raise an
    ``HTTPException`` with an appropriate status code rather than returning
    a partial or unauthenticated context.

    Error conventions:
        - 401 Unauthorized — credentials are missing or cannot be parsed.
        - 403 Forbidden    — credentials are present but insufficient.
        - 503 Service Unavailable — upstream identity service is unreachable.

    Thread / concurrency safety:
        Providers are instantiated once and reused across many concurrent
        requests; implementations must be stateless or use thread-safe state.
    """

    @abc.abstractmethod
    async def validate(self, request: Request) -> AuthContext:
        """Validate the incoming request and return an ``AuthContext``.

        Args:
            request: The raw FastAPI / Starlette ``Request`` object.  Use
                ``request.headers`` to access ``Authorization`` or custom
                header values, and ``request.state`` to store per-request
                attributes set by earlier middleware.

        Returns:
            A fully-populated, immutable ``AuthContext`` for the authenticated
            principal.

        Raises:
            HTTPException: With status 401 when credentials are absent or
                invalid; with status 403 when credentials are valid but access
                is denied; with status 503 when the identity backend is
                unavailable.
        """
        ...  # pragma: no cover
