"""Local (zero-auth) authentication provider for SkillMeat single-user mode.

In local mode there is no external identity service.  Every request is treated
as coming from the implicit ``local_admin`` user, which holds the
``system_admin`` role and all permission scopes.  The provider never raises an
exception — authentication always succeeds without inspecting the request.

Usage::

    from skillmeat.api.auth.local_provider import LocalAuthProvider

    provider = LocalAuthProvider()
    ctx = await provider.validate(request)  # always returns LOCAL_ADMIN_CONTEXT

References:
    .claude/progress/aaa-rbac-foundation/  AUTH-002
"""

from __future__ import annotations

from fastapi import Request

from skillmeat.api.auth.provider import AuthProvider
from skillmeat.api.schemas.auth import LOCAL_ADMIN_CONTEXT, AuthContext


class LocalAuthProvider(AuthProvider):
    """Authentication provider for local single-user (zero-auth) mode.

    Always returns the pre-built ``LOCAL_ADMIN_CONTEXT`` regardless of the
    request content.  No headers, tokens, or cookies are inspected.

    This provider is appropriate only when the SkillMeat instance is running
    locally for a single trusted user.  It must **not** be used in
    multi-tenant or network-exposed deployments.

    Thread safety:
        Stateless — safe to share across concurrent requests.
    """

    async def validate(self, request: Request) -> AuthContext:
        """Return the local admin context without inspecting the request.

        Args:
            request: Incoming HTTP request (not used; accepted to satisfy the
                ``AuthProvider`` ABC contract).

        Returns:
            The singleton ``LOCAL_ADMIN_CONTEXT`` carrying the
            ``system_admin`` role and all permission scopes.  This method
            never raises.
        """
        return LOCAL_ADMIN_CONTEXT
