"""
RequestContext: per-request metadata carrier for the repository layer.

Keeps auth, tracing, and edition information out of method signatures while
making it available to any repository call that needs it.  This is the
foundation layer — it must not import from other skillmeat modules.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass
class RequestContext:
    """Carries per-request metadata through the repository layer.

    Intended to be constructed once per request (e.g. in an API
    dependency or CLI entry-point) and threaded through to repository
    calls as an optional parameter.

    Attributes:
        user_id:    Identifies the acting user.  Reserved for future RBAC;
                    ``None`` means "unauthenticated / not yet enforced".
        request_id: Opaque correlation token that links log lines across
                    repository calls within a single request.  Defaults to
                    an empty string; use :meth:`create` to get a UUID-backed
                    ID automatically.
        tenant_id:  Reserved for future multi-tenancy.  ``None`` means
                    single-tenant (current default).
        edition:    Deployment edition token.  Should match
                    ``config.EDITION``; defaults to ``"local"``.
    """

    user_id: str | None = None
    request_id: str = ""
    tenant_id: str | None = None
    edition: str = "local"

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(cls, request_id: str | None = None) -> RequestContext:
        """Return a new :class:`RequestContext` with a guaranteed request ID.

        Args:
            request_id: An explicit correlation ID.  When ``None`` (or
                        omitted) a random UUID4 string is generated.

        Returns:
            A freshly constructed :class:`RequestContext`.
        """
        resolved_id = request_id if request_id is not None else str(uuid.uuid4())
        return cls(request_id=resolved_id)
