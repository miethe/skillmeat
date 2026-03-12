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

Ownership / membership-aware helpers (Phase 5+)
------------------------------------------------
* ``apply_ownership_filter`` / ``apply_ownership_filter_stmt``:
    Filter rows by resolved readable scopes expressed as
    ``(owner_type, owner_id)`` pairs.  Replaces ad-hoc owner column
    comparisons in individual repositories.
* ``apply_membership_visibility_filter`` / ``apply_membership_visibility_filter_stmt``:
    Drop-in replacements for the original visibility helpers that treat
    ``visibility == 'team'`` as membership-aware rather than tenant-wide.
    A row with ``visibility == 'team'`` is now visible only if the owning
    team is present in the caller's ``readable_scopes``.
* ``validate_write_target``:
    Guard helper — returns ``True`` when the resolved ownership context
    permits writing to the given ``OwnerTarget``.

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

Membership-aware (Phase 5+, session.query style)::

    from skillmeat.core.repositories.filters import (
        apply_ownership_filter,
        apply_membership_visibility_filter,
    )
    from skillmeat.core.ownership import ResolvedOwnership

    q = session.query(UserCollection)
    q = apply_membership_visibility_filter(q, UserCollection, auth_context, resolved)
    results = q.all()
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Type

from sqlalchemy import and_, or_

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from skillmeat.api.schemas.auth import AuthContext
    from skillmeat.core.ownership import OwnerTarget, ResolvedOwnership


# ---------------------------------------------------------------------------
# SQLAlchemy 2.x (select() / Select) variant — for enterprise repositories
# ---------------------------------------------------------------------------


def apply_visibility_filter_stmt(
    stmt: Any,
    model: Type[Any],
    auth_context: "AuthContext",
    resolved_ownership: "ResolvedOwnership | None" = None,
) -> Any:
    """Append visibility access-control predicates to a SQLAlchemy 2.x *Select*.

    Modifies *stmt* in-place via chained ``.where()`` and returns the new
    statement.  The original statement object is not mutated (SQLAlchemy
    ``Select`` is immutable).

    Visibility rules applied:
      - Admins (``system_admin`` role): no additional filter — see all rows.
      - Non-admins: show rows where:
          ``visibility == 'public'``
          OR ``visibility == 'team'``   (simplified: same tenant = visible,
                                         OR membership-aware if resolved_ownership provided)
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
    resolved_ownership:
        Optional resolved ownership context.  When provided, team-visibility
        uses membership-aware checking: a row with ``visibility == 'team'`` is
        visible only when its ``(owner_type, owner_id)`` is present in
        ``resolved_ownership.readable_scopes``.  When ``None`` (default),
        the original tenant-wide shortcut is used — backward compatible for
        all existing callers.

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

    # When resolved_ownership is provided, delegate entirely to the
    # membership-aware helper which handles all visibility tiers correctly.
    if resolved_ownership is not None:
        logger.debug(
            "apply_visibility_filter_stmt: delegating to membership-aware helper "
            "for user_id=%s (model=%s)",
            auth_context.user_id,
            model.__name__,
        )
        return apply_membership_visibility_filter_stmt(
            stmt, model, auth_context, resolved_ownership
        )

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
    resolved_ownership: "ResolvedOwnership | None" = None,
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
    resolved_ownership:
        Optional resolved ownership context.  When provided, team-visibility
        uses membership-aware checking: a row with ``visibility == 'team'`` is
        visible only when its ``(owner_type, owner_id)`` is present in
        ``resolved_ownership.readable_scopes``.  When ``None`` (default),
        the original tenant-wide shortcut is used — backward compatible for
        all existing callers.

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

    # When resolved_ownership is provided, delegate entirely to the
    # membership-aware helper which handles all visibility tiers correctly.
    if resolved_ownership is not None:
        logger.debug(
            "apply_visibility_filter: delegating to membership-aware helper "
            "for user_id=%s (model=%s)",
            auth_context.user_id,
            model.__name__,
        )
        return apply_membership_visibility_filter(
            query, model, auth_context, resolved_ownership
        )

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


# ---------------------------------------------------------------------------
# Ownership-scope helpers (Phase 5+)
# These helpers operate on ResolvedOwnership rather than AuthContext directly,
# enabling membership-aware filtering that goes beyond the simplified
# tenant-wide "team" shortcut above.
# ---------------------------------------------------------------------------


def apply_ownership_filter(
    query: Any,
    model: Type[Any],
    resolved: "ResolvedOwnership",
) -> Any:
    """Filter a SQLAlchemy 1.x *Query* to rows readable by *resolved*.

    A row is included when its ``(owner_type, owner_id)`` pair matches any
    entry in ``resolved.readable_scopes``.  Uses SQL-level ``OR`` predicates
    so the database evaluates the filter — no Python-side row iteration.

    When ``resolved.readable_scopes`` is empty the query is constrained to
    return no rows (``filter(False)``).  This is intentional: a context with
    no readable scopes should see nothing.

    Parameters
    ----------
    query:
        A SQLAlchemy 1.x ``Query`` object (from ``session.query(model)``).
    model:
        The ORM model class being queried.  Must have ``owner_type`` and
        ``owner_id`` mapped columns.
    resolved:
        The resolved ownership context produced by ``OwnershipResolver``.

    Returns
    -------
    Query
        The ownership-filtered query.

    Raises
    ------
    AttributeError
        If *model* lacks ``owner_type`` or ``owner_id`` columns.
    """
    from skillmeat.core.ownership import ResolvedOwnership  # noqa: F401 (runtime import)

    if not resolved.readable_scopes:
        logger.debug(
            "apply_ownership_filter: no readable scopes — returning empty result (model=%s)",
            model.__name__,
        )
        return query.filter(False)  # type: ignore[arg-type]

    conditions = [
        and_(
            model.owner_type == scope.owner_type.value,
            model.owner_id == scope.owner_id,
        )
        for scope in resolved.readable_scopes
    ]

    logger.debug(
        "apply_ownership_filter: %d scope(s) applied (model=%s)",
        len(conditions),
        model.__name__,
    )
    return query.filter(or_(*conditions))


def apply_ownership_filter_stmt(
    stmt: Any,
    model: Type[Any],
    resolved: "ResolvedOwnership",
) -> Any:
    """Filter a SQLAlchemy 2.x *Select* to rows readable by *resolved*.

    Equivalent to :func:`apply_ownership_filter` but uses the immutable
    ``stmt.where()`` API suitable for SQLAlchemy 2.x ``select()`` statements.

    Parameters
    ----------
    stmt:
        A SQLAlchemy 2.x ``Select`` statement.
    model:
        The ORM model class being queried.  Must have ``owner_type`` and
        ``owner_id`` mapped columns.
    resolved:
        The resolved ownership context produced by ``OwnershipResolver``.

    Returns
    -------
    Select
        The ownership-filtered statement.

    Raises
    ------
    AttributeError
        If *model* lacks ``owner_type`` or ``owner_id`` columns.
    """
    from skillmeat.core.ownership import ResolvedOwnership  # noqa: F401 (runtime import)

    if not resolved.readable_scopes:
        logger.debug(
            "apply_ownership_filter_stmt: no readable scopes — returning empty result (model=%s)",
            model.__name__,
        )
        # Use a literal false predicate; compatible with both SQLite and PG.
        from sqlalchemy import literal  # local import to keep top-level clean

        return stmt.where(literal(False))

    conditions = [
        and_(
            model.owner_type == scope.owner_type.value,
            model.owner_id == scope.owner_id,
        )
        for scope in resolved.readable_scopes
    ]

    logger.debug(
        "apply_ownership_filter_stmt: %d scope(s) applied (model=%s)",
        len(conditions),
        model.__name__,
    )
    return stmt.where(or_(*conditions))


# ---------------------------------------------------------------------------
# Membership-aware visibility helpers (Phase 5+)
# Replaces the tenant-wide "team" shortcut with proper membership checking.
# ---------------------------------------------------------------------------


def apply_membership_visibility_filter(
    query: Any,
    model: Type[Any],
    auth_context: "AuthContext",
    resolved: "ResolvedOwnership",
) -> Any:
    """Visibility filter with membership-aware team checks (SQLAlchemy 1.x).

    This is the Phase-5 replacement for :func:`apply_visibility_filter`.
    The critical difference is how ``visibility == 'team'`` rows are handled:

    * **Old behaviour** (apply_visibility_filter): ``visibility == 'team'``
      rows are shown to *all* users within the tenant — a deliberate
      simplification described as the "tenant-wide team visibility shortcut".
    * **New behaviour** (this function): ``visibility == 'team'`` rows are
      visible only when the row's ``(owner_type, owner_id)`` pair exists in
      the caller's ``resolved.readable_scopes``.  This enforces actual
      team-membership gating.

    Rules applied (in order of precedence):
      1. ``auth_context.is_admin()`` → no filter, see all rows.
      2. ``visibility == 'public'`` → visible to all authenticated users.
      3. ``visibility == 'team'`` → visible only if the owning
         ``(owner_type, owner_id)`` is in ``resolved.readable_scopes``.
      4. ``visibility == 'private'`` → visible only if
         ``owner_id == str(auth_context.user_id)``.

    Parameters
    ----------
    query:
        A SQLAlchemy 1.x ``Query`` object.
    model:
        The ORM model class being queried.  Must have ``visibility``,
        ``owner_type``, and ``owner_id`` mapped columns.
    auth_context:
        The authenticated request context (used for admin bypass and
        ``user_id`` comparison on private rows).
    resolved:
        The resolved ownership context carrying the caller's
        ``readable_scopes`` (used for team-membership gating).

    Returns
    -------
    Query
        The membership-visibility-filtered query.
    """
    if auth_context.is_admin():
        logger.debug(
            "apply_membership_visibility_filter: admin bypass for user_id=%s",
            auth_context.user_id,
        )
        return query

    owner_id_str = str(auth_context.user_id)

    # Build team-membership conditions: a 'team' row is visible when its
    # (owner_type, owner_id) matches any of the caller's readable scopes.
    team_conditions = [
        and_(
            model.visibility == "team",
            model.owner_type == scope.owner_type.value,
            model.owner_id == scope.owner_id,
        )
        for scope in resolved.readable_scopes
    ]

    if team_conditions:
        team_clause = or_(*team_conditions)
    else:
        # No readable scopes → team rows are never visible.
        team_clause = and_(model.visibility == "team", False)  # type: ignore[arg-type]

    visibility_predicate = or_(
        model.visibility == "public",
        team_clause,
        and_(
            model.visibility == "private",
            model.owner_id == owner_id_str,
        ),
    )

    logger.debug(
        "apply_membership_visibility_filter: applied for user_id=%s, "
        "%d team scope(s) (model=%s)",
        auth_context.user_id,
        len(resolved.readable_scopes),
        model.__name__,
    )
    return query.filter(visibility_predicate)


def apply_membership_visibility_filter_stmt(
    stmt: Any,
    model: Type[Any],
    auth_context: "AuthContext",
    resolved: "ResolvedOwnership",
) -> Any:
    """Visibility filter with membership-aware team checks (SQLAlchemy 2.x).

    Equivalent to :func:`apply_membership_visibility_filter` but uses the
    immutable ``stmt.where()`` API for SQLAlchemy 2.x ``select()`` statements.

    Parameters
    ----------
    stmt:
        A SQLAlchemy 2.x ``Select`` statement.
    model:
        The ORM model class being queried.  Must have ``visibility``,
        ``owner_type``, and ``owner_id`` mapped columns.
    auth_context:
        The authenticated request context.
    resolved:
        The resolved ownership context carrying ``readable_scopes``.

    Returns
    -------
    Select
        The membership-visibility-filtered statement.
    """
    if auth_context.is_admin():
        logger.debug(
            "apply_membership_visibility_filter_stmt: admin bypass for user_id=%s",
            auth_context.user_id,
        )
        return stmt

    owner_id_str = str(auth_context.user_id)

    team_conditions = [
        and_(
            model.visibility == "team",
            model.owner_type == scope.owner_type.value,
            model.owner_id == scope.owner_id,
        )
        for scope in resolved.readable_scopes
    ]

    if team_conditions:
        team_clause = or_(*team_conditions)
    else:
        team_clause = and_(model.visibility == "team", False)  # type: ignore[arg-type]

    visibility_predicate = or_(
        model.visibility == "public",
        team_clause,
        and_(
            model.visibility == "private",
            model.owner_id == owner_id_str,
        ),
    )

    logger.debug(
        "apply_membership_visibility_filter_stmt: applied for user_id=%s, "
        "%d team scope(s) (model=%s)",
        auth_context.user_id,
        len(resolved.readable_scopes),
        model.__name__,
    )
    return stmt.where(visibility_predicate)


# ---------------------------------------------------------------------------
# Write-target validation helper
# ---------------------------------------------------------------------------


def validate_write_target(
    target: "OwnerTarget",
    resolved: "ResolvedOwnership",
) -> bool:
    """Return ``True`` if writing to *target* is permitted by *resolved*.

    Delegates to ``ResolvedOwnership.can_write_to`` so callers do not need to
    import ``ResolvedOwnership`` directly.  Intended as a lightweight guard at
    service-layer write paths before touching the database.

    Parameters
    ----------
    target:
        The ``OwnerTarget`` (owner_type + owner_id pair) to write to.
    resolved:
        The resolved ownership context for the current request.

    Returns
    -------
    bool
        ``True`` when *target* is present in ``resolved.writable_scopes``;
        ``False`` otherwise.

    Example::

        if not validate_write_target(owner_target, resolved):
            raise PermissionError(f"Write to {owner_target} denied")
    """
    return resolved.can_write_to(target.owner_type, target.owner_id)
