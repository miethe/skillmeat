"""Shared query filter utilities for repository visibility and ownership.

This module provides reusable SQLAlchemy filter helpers that enforce
visibility-based access control on ORM models.  Both local (SQLite) and
enterprise (PostgreSQL) repositories can import and apply these helpers so
the access-control semantics stay consistent across storage backends.

Design notes
------------
* ``_apply_visibility_filter`` is a *function*, not a method, so it works
  equally well in the local ``session.query()`` world (1.x style) and the
  enterprise ``select()`` world (2.x style).  Callers pass in the statement
  and the model class they are filtering on.
* Admin bypass: ``AuthContext.is_admin()`` returns True for ``system_admin``
  role holders.  Admins see all rows regardless of visibility — this mirrors
  the tenant-isolation safety valve in ``enterprise_repositories.py``.
* Visibility semantics (matching ``cache/auth_types.Visibility``):
    - ``public``  → visible to all authenticated users within the tenant
    - ``team``    → simplified for Phase 4: visible to all within the tenant
                    (full team-membership checks are a future-phase concern)
    - ``private`` → visible only when ``owner_id`` matches the caller's
                    ``user_id`` (string comparison — see DES-001 note below)
* DES-001 type mismatch: ``owner_id`` is stored as ``String`` in models.py
  but ``AuthContext.user_id`` is a ``uuid.UUID``.  Use the
  ``str_owner_id()`` helper from ``skillmeat.api.schemas.auth`` (or call
  ``str(auth_context.user_id)`` directly) before passing into filter logic.
  This module calls ``str(auth_context.user_id)`` internally for the same
  reason.

Usage
-----
Local repos (session.query style)::

    from skillmeat.core.repositories.filters import apply_visibility_filter
    from skillmeat.cache.models import Artifact

    q = session.query(Artifact)
    q = apply_visibility_filter(q, Artifact, auth_context)
    results = q.all()

Enterprise repos (select() style)::

    from skillmeat.core.repositories.filters import apply_visibility_filter_stmt
    from skillmeat.cache.models_enterprise import EnterpriseArtifact

    stmt = select(EnterpriseArtifact)
    stmt = apply_visibility_filter_stmt(stmt, EnterpriseArtifact, auth_context)
    results = session.execute(stmt).scalars().all()
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Type

from sqlalchemy import and_, or_

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from skillmeat.api.schemas.auth import AuthContext


# ---------------------------------------------------------------------------
# SQLAlchemy 2.x (select() / Select) variant — for enterprise repositories
# ---------------------------------------------------------------------------


def apply_visibility_filter_stmt(
    stmt: Any,
    model: Type[Any],
    auth_context: "AuthContext",
) -> Any:
    """Append visibility access-control predicates to a SQLAlchemy 2.x *Select*.

    Modifies *stmt* in-place via chained ``.where()`` and returns the new
    statement.  The original statement object is not mutated (SQLAlchemy
    ``Select`` is immutable).

    Visibility rules applied:
      - Admins (``system_admin`` role): no additional filter — see all rows.
      - Non-admins: show rows where:
          ``visibility == 'public'``
          OR ``visibility == 'team'``   (simplified: same tenant = visible)
          OR (``visibility == 'private'`` AND ``owner_id == str(user_id)``)

    Parameters
    ----------
    stmt:
        A SQLAlchemy 2.x ``Select`` statement.
    model:
        The ORM model class being queried.  Must have ``visibility`` and
        ``owner_id`` mapped columns.
    auth_context:
        The authenticated request context carrying ``user_id`` and ``roles``.

    Returns
    -------
    Select
        The visibility-filtered statement.

    Raises
    ------
    AttributeError
        If *model* lacks ``visibility`` or ``owner_id`` columns — indicates
        a programming error (applying visibility filter to an unsupported model).
    """
    if auth_context.is_admin():
        logger.debug(
            "apply_visibility_filter_stmt: admin bypass for user_id=%s",
            auth_context.user_id,
        )
        return stmt

    # DES-001: owner_id is String in DB; user_id is uuid.UUID in AuthContext.
    owner_id_str = str(auth_context.user_id)

    stmt = stmt.where(
        or_(
            model.visibility == "public",
            model.visibility == "team",  # simplified: within tenant = visible
            and_(
                model.visibility == "private",
                model.owner_id == owner_id_str,
            ),
        )
    )
    logger.debug(
        "apply_visibility_filter_stmt: applied for user_id=%s (model=%s)",
        auth_context.user_id,
        model.__name__,
    )
    return stmt


# ---------------------------------------------------------------------------
# SQLAlchemy 1.x (session.query() / Query) variant — for local repositories
# ---------------------------------------------------------------------------


def apply_visibility_filter(
    query: Any,
    model: Type[Any],
    auth_context: "AuthContext",
) -> Any:
    """Append visibility access-control predicates to a SQLAlchemy 1.x *Query*.

    Works identically to :func:`apply_visibility_filter_stmt` but accepts a
    ``session.query(...)`` object instead of a ``select()`` statement.

    Parameters
    ----------
    query:
        A SQLAlchemy 1.x ``Query`` object (from ``session.query(model)``).
    model:
        The ORM model class being queried.  Must have ``visibility`` and
        ``owner_id`` mapped columns.
    auth_context:
        The authenticated request context carrying ``user_id`` and ``roles``.

    Returns
    -------
    Query
        The visibility-filtered query.
    """
    if auth_context.is_admin():
        logger.debug(
            "apply_visibility_filter: admin bypass for user_id=%s",
            auth_context.user_id,
        )
        return query

    # DES-001: owner_id is String in DB; user_id is uuid.UUID in AuthContext.
    owner_id_str = str(auth_context.user_id)

    query = query.filter(
        or_(
            model.visibility == "public",
            model.visibility == "team",  # simplified: within tenant = visible
            and_(
                model.visibility == "private",
                model.owner_id == owner_id_str,
            ),
        )
    )
    logger.debug(
        "apply_visibility_filter: applied for user_id=%s (model=%s)",
        auth_context.user_id,
        model.__name__,
    )
    return query
