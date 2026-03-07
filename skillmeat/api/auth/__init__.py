"""Authentication provider package for SkillMeat AAA/RBAC system.

Exports the ``AuthProvider`` ABC that all concrete authentication backends
(local passthrough, Clerk JWT, API key, etc.) must implement.

Example::

    from skillmeat.api.auth import AuthProvider
    from skillmeat.api.schemas.auth import AuthContext

    class MyProvider(AuthProvider):
        async def validate(self, request):
            ...
            return AuthContext(user_id=..., roles=[...], scopes=[...])
"""

from skillmeat.api.auth.provider import AuthProvider

__all__ = ["AuthProvider"]
