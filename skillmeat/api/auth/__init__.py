"""Authentication provider package for SkillMeat AAA/RBAC system.

Exports the ``AuthProvider`` ABC and concrete provider implementations.

Available providers:

``AuthProvider``
    Abstract base class all concrete backends must implement.

``ClerkAuthProvider``
    Validates Clerk JWTs and maps claims to ``AuthContext``.  Requires the
    ``CLERK_JWKS_URL`` environment variable to point at the Clerk JWKS endpoint.

Example::

    from skillmeat.api.auth import AuthProvider, ClerkAuthProvider
    from skillmeat.api.schemas.auth import AuthContext

    class MyProvider(AuthProvider):
        async def validate(self, request):
            ...
            return AuthContext(user_id=..., roles=[...], scopes=[...])
"""

from skillmeat.api.auth.clerk_provider import ClerkAuthProvider
from skillmeat.api.auth.provider import AuthProvider

__all__ = ["AuthProvider", "ClerkAuthProvider"]
