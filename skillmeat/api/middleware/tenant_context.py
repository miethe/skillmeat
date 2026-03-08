"""TenantContext middleware for SkillMeat API.

Extracts the tenant_id from the per-request AuthContext and sets the
TenantContext ContextVar so that enterprise repository implementations
can implicitly scope all queries to the correct tenant without requiring
callers to pass tenant_id explicitly.

Design notes
------------
``require_auth`` is a FastAPI *dependency*, not a Starlette
``BaseHTTPMiddleware``.  It runs during FastAPI's dependency-injection phase
(inside the ASGI handler), **after** all ``app.add_middleware()`` layers have
already processed the request.  A ``BaseHTTPMiddleware`` therefore executes too
early to observe the ``AuthContext`` that ``require_auth`` constructs.

The correct hook point is a *dependency* that:

1. Calls (or re-uses) ``require_auth`` to obtain the authenticated
   ``AuthContext``.
2. Extracts ``tenant_id`` from that context.
3. Sets ``TenantContext`` so that the request's enterprise repository calls
   are automatically scoped to the right tenant.
4. Clears ``TenantContext`` after the downstream handler returns (via a
   ``finally`` block), preventing context leakage between requests when a
   thread/coroutine is reused.

Usage
-----
Add as a router-level or app-level dependency so it runs on every protected
request::

    # Per-router (recommended — attach to enterprise routers only)
    router = APIRouter(dependencies=[Depends(set_tenant_context_dep)])

    # App-level (affects every request, including unauthenticated ones)
    app = FastAPI(dependencies=[Depends(set_tenant_context_dep)])

    # Per-endpoint (captures both auth context and sets tenant)
    @router.get("/resource")
    async def get_resource(
        _: None = Depends(set_tenant_context_dep),
        auth: AuthContext = Depends(require_auth()),
    ):
        ...

Local mode
----------
When the edition is ``"local"`` or the ``AuthContext.tenant_id`` is ``None``
(e.g. ``LOCAL_ADMIN_CONTEXT``), the dependency is a no-op: it skips setting
``TenantContext`` and the enterprise repository layer falls back to
``DEFAULT_TENANT_ID`` (defined in ``enterprise_repositories.py``).

References
----------
.claude/progress/aaa-rbac-foundation/  AUTH-006
skillmeat/cache/enterprise_repositories.py  TenantContext, set_tenant_context, clear_tenant_context
skillmeat/api/dependencies.py  require_auth, AuthContextDep
"""

from __future__ import annotations

import logging
from typing import Annotated, AsyncGenerator

from fastapi import Depends

from skillmeat.api.dependencies import require_auth
from skillmeat.api.schemas.auth import AuthContext
from skillmeat.cache.enterprise_repositories import (
    clear_tenant_context,
    set_tenant_context,
)

logger = logging.getLogger(__name__)


async def set_tenant_context_dep(
    auth_context: AuthContext = Depends(require_auth()),
) -> AsyncGenerator[None, None]:
    """FastAPI dependency that propagates AuthContext.tenant_id to TenantContext.

    This dependency must be declared *after* ``require_auth`` in the dependency
    graph (either as a router/app-level dependency or explicitly on a route) so
    that the ``AuthContext`` has already been resolved before this function runs.

    The ContextVar token is stored locally and reset in the ``finally`` block,
    which guarantees that the tenant context is cleared even when the downstream
    handler raises an exception — preventing tenant context leakage across
    requests on a reused async task.

    Parameters
    ----------
    auth_context:
        The authenticated context injected by ``require_auth()``.

    Yields
    ------
    None
        This is a generator dependency; it yields control to the route handler
        and performs cleanup in the ``finally`` block.

    Notes
    -----
    * When ``tenant_id`` is ``None`` (local / single-tenant mode) the
      ``TenantContext`` ContextVar is left unchanged and enterprise repositories
      fall back to ``DEFAULT_TENANT_ID`` automatically.
    * When ``tenant_id`` is set (enterprise / multi-tenant mode) it is pushed
      onto ``TenantContext`` for the duration of the request and then reset.
    """
    if auth_context.tenant_id is None:
        # Local / single-tenant mode — no tenant isolation required.
        logger.debug(
            "set_tenant_context_dep: tenant_id is None (local mode), skipping TenantContext"
        )
        yield
        return

    # Enterprise mode — set TenantContext for the duration of this request.
    logger.debug(
        "set_tenant_context_dep: setting TenantContext to tenant_id=%s for user=%s",
        auth_context.tenant_id,
        auth_context.user_id,
    )
    reset_token = set_tenant_context(auth_context.tenant_id)
    try:
        yield
    finally:
        clear_tenant_context(reset_token)
        logger.debug(
            "set_tenant_context_dep: cleared TenantContext (tenant_id=%s)",
            auth_context.tenant_id,
        )


# ---------------------------------------------------------------------------
# Type alias for cleaner route / router signatures
# ---------------------------------------------------------------------------

#: Annotated dependency alias.  Add to a router with:
#:
#:     router = APIRouter(dependencies=[TenantContextDep])
#:
#: or to a route handler's parameter list:
#:
#:     async def handler(_: TenantContextDep): ...
TenantContextDep = Annotated[None, Depends(set_tenant_context_dep)]


# ---------------------------------------------------------------------------
# Registration note (do NOT modify server.py here — wire-up is deferred)
# ---------------------------------------------------------------------------
#
# To activate this dependency application-wide, add the following to
# ``skillmeat/api/server.py`` inside ``create_app()``, **after** the existing
# middleware registrations and **before** ``app.include_router(...)`` calls:
#
#     from skillmeat.api.middleware.tenant_context import set_tenant_context_dep
#
#     app = FastAPI(
#         ...,
#         dependencies=[Depends(set_tenant_context_dep)],
#     )
#
# Alternatively, attach it at the router level for enterprise-only routers:
#
#     from skillmeat.api.middleware.tenant_context import set_tenant_context_dep
#
#     router = APIRouter(
#         prefix="/api/v1/enterprise",
#         dependencies=[Depends(set_tenant_context_dep)],
#     )
#
# Wire-up will be performed when all auth/RBAC middleware is assembled
# together in the final integration phase.
