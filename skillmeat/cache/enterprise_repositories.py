"""Enterprise repository base with automatic tenant filtering.

This module provides the foundational repository infrastructure for the
enterprise (PostgreSQL) data tier introduced in the enterprise-db-storage
feature (Phase 2).

The central design goal is *structural* tenant isolation: subclass repositories
never need to manually add ``WHERE tenant_id = ?`` predicates — the base class
injects them automatically via ``_apply_tenant_filter()``.

Architecture notes
------------------
- ``EnterpriseRepositoryBase`` accepts an injected ``Session`` rather than
  managing its own engine/db_path.  This fits the FastAPI dependency-injection
  model (``get_db_session`` / ``DbSessionDep``) and makes repositories easy to
  test with in-memory or temporary databases.
- Tenant identity is stored in a ``contextvars.ContextVar`` so it is naturally
  isolated across concurrent async tasks and threads — no ``threading.local``
  needed.
- SQLAlchemy 2.x ``select()`` style is used throughout (not the legacy 1.x
  ``session.query()`` API) because enterprise models target PostgreSQL and the
  project already uses 2.x-style ``select`` in newer code.

Exports
-------
TenantContext
    Module-level ``ContextVar[Optional[UUID]]`` holding the current tenant.
tenant_scope
    Context manager that sets ``TenantContext`` for the duration of a block.
TenantIsolationError
    Domain exception raised when a cross-tenant access attempt is detected.
EnterpriseRepositoryBase
    Generic base for all enterprise repository implementations.

Usage::

    from skillmeat.cache.enterprise_repositories import (
        EnterpriseRepositoryBase,
        TenantContext,
        TenantIsolationError,
        tenant_scope,
    )
    from skillmeat.cache.models_enterprise import EnterpriseArtifact

    class ArtifactRepository(EnterpriseRepositoryBase[EnterpriseArtifact]):
        def __init__(self, session: Session) -> None:
            super().__init__(session, EnterpriseArtifact)

        def get_by_name(self, name: str) -> Optional[EnterpriseArtifact]:
            stmt = self._apply_tenant_filter(
                select(EnterpriseArtifact).where(EnterpriseArtifact.name == name)
            )
            return self.session.execute(stmt).scalar_one_or_none()

    # In a FastAPI route (tenant set per-request by middleware):
    with tenant_scope(uuid.UUID("...")):
        repo = ArtifactRepository(db_session)
        artifact = repo.get_by_name("canvas-design")

References
----------
ENT-2.1 implementation task.
Phase 1 foundation: skillmeat/cache/models_enterprise.py,
                    skillmeat/cache/repositories.py,
                    skillmeat/cache/constants.py
"""

from __future__ import annotations

import logging
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Generator, Generic, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from skillmeat.cache.constants import DEFAULT_TENANT_ID

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type variable
# ---------------------------------------------------------------------------

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Tenant context — request-scoped tenant identity
# ---------------------------------------------------------------------------

#: Module-level ContextVar holding the active tenant UUID for the current
#: execution context (async task, thread, or coroutine).  ``None`` signals
#: "not set"; ``_get_tenant_id()`` falls back to ``DEFAULT_TENANT_ID``.
TenantContext: ContextVar[Optional[uuid.UUID]] = ContextVar(
    "TenantContext", default=None
)


@contextmanager
def tenant_scope(tenant_id: uuid.UUID) -> Generator[None, None, None]:
    """Context manager that sets ``TenantContext`` for the duration of a block.

    Restores the previous value (or ``None``) when the block exits, even if an
    exception is raised — making nested ``tenant_scope`` calls safe.

    Parameters
    ----------
    tenant_id:
        The UUID identifying the tenant that should own all repository
        operations performed inside this block.

    Yields
    ------
    None

    Examples
    --------
    ::

        with tenant_scope(uuid.UUID("acme-tenant-uuid")):
            artifacts = artifact_repo.list_active()

        # Nested scopes are supported — inner scope restores outer on exit.
        with tenant_scope(tenant_a):
            with tenant_scope(tenant_b):
                ...  # tenant_b is active here
            ...  # tenant_a is active again here
    """
    token = TenantContext.set(tenant_id)
    try:
        yield
    finally:
        TenantContext.reset(token)


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------


class TenantIsolationError(Exception):
    """Raised when a cross-tenant data access attempt is detected.

    This exception is thrown by ``EnterpriseRepositoryBase._assert_tenant_owns``
    when an ORM object's ``tenant_id`` does not match the tenant currently
    active in ``TenantContext``.

    It is intentionally a plain ``Exception`` subclass (not an HTTP exception)
    so that it can be caught at any layer and mapped to an appropriate HTTP 403
    or 404 response by the API boundary.

    Attributes
    ----------
    object_tenant_id:
        The ``tenant_id`` found on the retrieved object.
    current_tenant_id:
        The tenant UUID that was active in ``TenantContext`` at the time of the
        check.
    """

    def __init__(
        self,
        object_tenant_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        detail: Optional[str] = None,
    ) -> None:
        self.object_tenant_id = object_tenant_id
        self.current_tenant_id = current_tenant_id
        message = (
            f"Tenant isolation violation: object belongs to tenant "
            f"{object_tenant_id!s} but current tenant is {current_tenant_id!s}."
        )
        if detail:
            message = f"{message} {detail}"
        super().__init__(message)


# ---------------------------------------------------------------------------
# Enterprise repository base
# ---------------------------------------------------------------------------


class EnterpriseRepositoryBase(Generic[T]):
    """Base repository for all enterprise (PostgreSQL) data access operations.

    Provides automatic tenant filtering so that every query issued by a
    subclass is scoped to the tenant currently stored in ``TenantContext``.
    Subclasses must call ``_apply_tenant_filter(stmt)`` on any ``select()``
    statement before executing it.

    Design contract
    ---------------
    * The ``Session`` is *injected* at construction time — this class does not
      create engines or manage connection pools.  Use the FastAPI
      ``get_db_session`` dependency (``skillmeat.cache.session``) or the
      ``DbSessionDep`` alias (``skillmeat.api.dependencies``) to supply it.
    * All query statements are SQLAlchemy 2.x ``select()`` style.
    * ``tenant_id`` columns on enterprise models are ``UUID(as_uuid=True)``
      — Python values are ``uuid.UUID`` instances, not strings.
    * Transaction management (commit / rollback) is the caller's
      responsibility; this class only manages *query construction*.

    Type Parameters
    ---------------
    T:
        The SQLAlchemy ORM model class this repository operates on.  Must be
        a subclass of ``EnterpriseBase`` and must have a ``tenant_id``
        column of type ``UUID``.

    Parameters
    ----------
    session:
        An open SQLAlchemy ``Session`` bound to the PostgreSQL enterprise
        database.
    model_class:
        The ORM model class (e.g. ``EnterpriseArtifact``).

    Examples
    --------
    Minimal subclass::

        class CollectionRepository(EnterpriseRepositoryBase[EnterpriseCollection]):
            def __init__(self, session: Session) -> None:
                super().__init__(session, EnterpriseCollection)

            def list_all(self) -> list[EnterpriseCollection]:
                stmt = self._apply_tenant_filter(select(EnterpriseCollection))
                return list(self.session.execute(stmt).scalars())
    """

    def __init__(self, session: Session, model_class: Type[T]) -> None:
        """Initialise the repository.

        Parameters
        ----------
        session:
            Injected SQLAlchemy session.  The session's lifecycle (commit,
            rollback, close) is managed by the caller — typically a FastAPI
            dependency or a ``with repo.transaction()`` block in tests.
        model_class:
            The ORM model class this repository is typed against.
        """
        self.session: Session = session
        self.model_class: Type[T] = model_class
        logger.debug(
            "Initialised %s for model %s",
            self.__class__.__name__,
            model_class.__name__,
        )

    # ------------------------------------------------------------------
    # Tenant identity resolution
    # ------------------------------------------------------------------

    def _get_tenant_id(self) -> uuid.UUID:
        """Return the active tenant UUID.

        Resolution order:

        1. ``TenantContext`` ContextVar — set per-request by middleware or
           ``tenant_scope()`` in tests.
        2. ``DEFAULT_TENANT_ID`` constant from ``skillmeat.cache.constants``
           — used in Phase 1 single-tenant mode and as a safe fallback.

        Returns
        -------
        uuid.UUID
            The UUID of the tenant that should own all current repository
            operations.
        """
        tenant_id = TenantContext.get()
        if tenant_id is None:
            logger.debug(
                "TenantContext not set; falling back to DEFAULT_TENANT_ID (%s)",
                DEFAULT_TENANT_ID,
            )
            return DEFAULT_TENANT_ID
        return tenant_id

    # ------------------------------------------------------------------
    # Automatic tenant filtering
    # ------------------------------------------------------------------

    def _apply_tenant_filter(self, stmt: Select) -> Select:
        """Append a ``WHERE tenant_id = <current_tenant>`` clause to *stmt*.

        This method must be called on every ``select()`` statement that
        targets an enterprise model table before the statement is executed.
        Subclasses should not bypass this call — doing so is a security defect.

        Parameters
        ----------
        stmt:
            A SQLAlchemy 2.x ``Select`` statement targeting ``self.model_class``
            (or a join that includes it).

        Returns
        -------
        Select
            The same statement with an additional ``WHERE tenant_id = ?``
            predicate appended via ``.where()``.

        Example
        -------
        ::

            stmt = self._apply_tenant_filter(
                select(EnterpriseArtifact)
                .where(EnterpriseArtifact.is_active.is_(True))
                .order_by(EnterpriseArtifact.created_at.desc())
            )
            result = self.session.execute(stmt).scalars().all()
        """
        tenant_id = self._get_tenant_id()
        return stmt.where(self.model_class.tenant_id == tenant_id)

    # ------------------------------------------------------------------
    # Ownership assertion
    # ------------------------------------------------------------------

    def _assert_tenant_owns(self, obj: T) -> None:
        """Verify that *obj* belongs to the currently active tenant.

        Use this after retrieving an object by primary key (where the query
        may not have gone through ``_apply_tenant_filter``), or after any
        cross-join that might surface rows from another tenant.

        Parameters
        ----------
        obj:
            An ORM instance that has a ``tenant_id`` attribute of type
            ``uuid.UUID``.

        Raises
        ------
        TenantIsolationError
            If ``obj.tenant_id`` does not equal ``_get_tenant_id()``.
        AttributeError
            If *obj* does not have a ``tenant_id`` attribute.  This would
            indicate a programming error — using this base with a model that
            lacks tenant isolation.

        Example
        -------
        ::

            artifact = self.session.get(EnterpriseArtifact, artifact_id)
            if artifact is None:
                raise NotFoundError(artifact_id)
            self._assert_tenant_owns(artifact)
        """
        current_tenant_id = self._get_tenant_id()
        object_tenant_id: uuid.UUID = obj.tenant_id  # type: ignore[attr-defined]
        if object_tenant_id != current_tenant_id:
            logger.warning(
                "Tenant isolation violation detected: object tenant=%s, "
                "current tenant=%s, model=%s",
                object_tenant_id,
                current_tenant_id,
                self.model_class.__name__,
            )
            raise TenantIsolationError(
                object_tenant_id=object_tenant_id,
                current_tenant_id=current_tenant_id,
            )

    # ------------------------------------------------------------------
    # Convenience: bare select scoped to current tenant
    # ------------------------------------------------------------------

    def _tenant_select(self) -> Select:
        """Return ``select(model_class).where(tenant_id == current_tenant)``.

        Shorthand for the most common query opening pattern.  Equivalent to::

            self._apply_tenant_filter(select(self.model_class))

        Returns
        -------
        Select
            A tenant-filtered ``Select`` statement ready for additional
            ``.where()``, ``.order_by()``, ``.limit()``, etc. chaining.
        """
        return self._apply_tenant_filter(select(self.model_class))
