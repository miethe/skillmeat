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

import hashlib
import logging
import uuid
from contextlib import contextmanager
from contextvars import ContextVar, Token
from datetime import datetime
from typing import TYPE_CHECKING, Dict, Generator, Generic, List, Optional, Tuple, Type, TypeVar

from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from skillmeat.cache.constants import DEFAULT_TENANT_ID

from skillmeat.core.interfaces.repositories import IDbUserCollectionRepository

if TYPE_CHECKING:
    from skillmeat.api.schemas.auth import AuthContext

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
# Imperative tenant context helpers (SVR-003)
# ---------------------------------------------------------------------------

def set_tenant_context(tenant_id: uuid.UUID) -> Token:
    """Set the current tenant in ``TenantContext`` and return a reset token.

    The returned token must be passed to :func:`clear_tenant_context` to
    restore the previous value.  Prefer the :func:`tenant_scope` context
    manager when possible — it handles cleanup automatically.

    Parameters
    ----------
    tenant_id:
        The UUID of the tenant to activate for the current execution context.

    Returns
    -------
    contextvars.Token
        Opaque token that can be passed to :func:`clear_tenant_context` to
        undo this set operation.

    Examples
    --------
    ::

        token = set_tenant_context(my_tenant_id)
        try:
            ...
        finally:
            clear_tenant_context(token)
    """
    return TenantContext.set(tenant_id)


def get_tenant_context() -> Optional[uuid.UUID]:
    """Return the tenant UUID currently stored in ``TenantContext``.

    Returns ``None`` when no tenant has been set for this execution context,
    allowing callers to decide their own fallback behaviour (e.g. default to
    ``DEFAULT_TENANT_ID`` for single-tenant mode, or raise for strict
    multi-tenant enforcement).

    Returns
    -------
    uuid.UUID or None
        The active tenant UUID, or ``None`` if not set.
    """
    return TenantContext.get(None)


def clear_tenant_context(token: Token) -> None:
    """Reset ``TenantContext`` to the value it held before a :func:`set_tenant_context` call.

    Parameters
    ----------
    token:
        The token returned by the corresponding :func:`set_tenant_context`
        call.  Passing any other token is undefined behaviour (mirrors the
        underlying ``ContextVar.reset`` contract).

    Examples
    --------
    ::

        token = set_tenant_context(my_tenant_id)
        try:
            ...
        finally:
            clear_tenant_context(token)
    """
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

    # ------------------------------------------------------------------
    # Audit logging
    # ------------------------------------------------------------------

    def _log_operation(
        self,
        operation: str,
        entity_type: str,
        entity_id: Optional[object],
        metadata: Optional[Dict[str, object]] = None,
    ) -> None:
        """Emit a structured audit log entry for a mutating repository operation.

        This method is intended to be called at the end of any state-changing
        operation (create, update, delete).  Read operations are deliberately
        excluded to keep audit volume manageable and to avoid leaking query
        patterns into the audit trail.

        No ``AuditLog`` SQLAlchemy model exists in Phase 1, so entries are
        written to the Python ``logging`` subsystem at ``INFO`` level as a JSON-
        serialisable dict.  This makes them easy to ingest by log-aggregation
        tools (Loki, CloudWatch, Datadog) without a schema migration.

        Parameters
        ----------
        operation:
            Short verb describing the mutation, e.g. ``"create"``,
            ``"update"``, ``"delete"``, ``"soft_delete"``.
        entity_type:
            The ORM model class name or table-name token that was mutated,
            e.g. ``"EnterpriseArtifact"``, ``"EnterpriseCollection"``.
            Conventionally pass ``self.model_class.__name__``.
        entity_id:
            The primary key of the affected row, or ``None`` when the PK is
            not yet available (e.g. before a flush).  Converted to ``str`` for
            JSON-safe serialisation.
        metadata:
            Optional dict of additional key-value pairs to include in the log
            entry.  Useful for recording old/new values, operation-specific
            flags, or caller context.  Values must be JSON-serialisable.

        Examples
        --------
        Typical usage at the end of a create method::

            def create(self, artifact: EnterpriseArtifact) -> EnterpriseArtifact:
                self.session.add(artifact)
                self.session.flush()
                self._log_operation(
                    operation="create",
                    entity_type=self.model_class.__name__,
                    entity_id=artifact.id,
                )
                return artifact

        With extra metadata on a delete::

            def delete(self, artifact: EnterpriseArtifact) -> None:
                self.session.delete(artifact)
                self.session.flush()
                self._log_operation(
                    operation="delete",
                    entity_type=self.model_class.__name__,
                    entity_id=artifact.id,
                    metadata={"name": artifact.name, "artifact_type": artifact.artifact_type},
                )
        """
        tenant_id = self._get_tenant_id()
        entry: Dict[str, object] = {
            "tenant_id": str(tenant_id),
            "operation": operation,
            "entity_type": entity_type,
            "entity_id": str(entity_id) if entity_id is not None else None,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        if metadata:
            entry["metadata"] = metadata
        logger.info("audit %s", entry)

    # ------------------------------------------------------------------
    # Auth context helpers (SVR-006)
    # ------------------------------------------------------------------

    def _apply_auth_context(
        self, auth_context: Optional["AuthContext"]
    ) -> Optional[uuid.UUID]:
        """Apply auth_context tenant to TenantContext and return the owner_id.

        When *auth_context* is provided and carries a ``tenant_id``, this
        method sets ``TenantContext`` so that all subsequent ``_apply_tenant_filter``
        / ``_get_tenant_id`` calls in the same operation use the authenticated
        tenant rather than any previously set value.

        Parameters
        ----------
        auth_context:
            The authenticated request context, or ``None`` for local/zero-auth
            mode.  When ``None`` the method is a no-op.

        Returns
        -------
        uuid.UUID or None
            The ``user_id`` from *auth_context* (to use as ``owner_id`` on new
            records), or ``None`` when *auth_context* is absent.
        """
        if auth_context is None:
            return None
        if auth_context.tenant_id is not None:
            set_tenant_context(auth_context.tenant_id)
        return auth_context.user_id


# ---------------------------------------------------------------------------
# EnterpriseArtifactRepository — write operations (ENT-2.4, ENT-2.5)
# ---------------------------------------------------------------------------


class EnterpriseArtifactRepository(EnterpriseRepositoryBase):  # type: ignore[type-arg]
    """Repository for enterprise artifact write operations.

    Provides create, update, soft_delete, and hard_delete methods for
    ``EnterpriseArtifact`` rows in the PostgreSQL enterprise schema.

    All methods assert tenant ownership before any mutation and use
    SQLAlchemy 2.x style queries throughout.

    Lookup and list methods (get, list_active, etc.) are added by a
    companion agent (ENT-2.2/ENT-2.3) to the same class — this file
    contains only the write-path methods to avoid concurrent conflicts.
    """

    def __init__(self, session: Session) -> None:
        from skillmeat.cache.models_enterprise import EnterpriseArtifact

        super().__init__(session, EnterpriseArtifact)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _next_version(current_tag: str) -> str:
        """Increment the patch component of a semver string.

        If *current_tag* does not match ``vM.m.p`` or ``M.m.p``, falls
        back to a UTC-timestamp-based tag to guarantee uniqueness.

        Parameters
        ----------
        current_tag:
            The version string of the most recent ``EnterpriseArtifactVersion``
            for this artifact (e.g. ``"v1.0.0"`` or ``"1.2.3"``).

        Returns
        -------
        str
            Next patch-incremented version string in the same format as
            *current_tag*, or ``"v<epoch_ms>"`` as fallback.
        """
        tag = current_tag.lstrip("v")
        parts = tag.split(".")
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            major, minor, patch = parts
            new_tag = f"{int(major)}.{int(minor)}.{int(patch) + 1}"
            # Preserve leading "v" if original had it
            if current_tag.startswith("v"):
                return f"v{new_tag}"
            return new_tag
        # Non-semver fallback: timestamp-based unique tag
        epoch_ms = int(datetime.utcnow().timestamp() * 1000)
        return f"v{epoch_ms}"

    @staticmethod
    def _compute_content_hash(content: str) -> str:
        """Return the SHA256 hex digest of *content* (64 hex chars)."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # ENT-2.2: Lookup methods with tenant scoping
    # ------------------------------------------------------------------

    def get(
        self,
        artifact_id: uuid.UUID,
        auth_context: Optional["AuthContext"] = None,
    ) -> "Optional[EnterpriseArtifact]":
        """Fetch an artifact by primary key, asserting tenant ownership.

        Uses ``session.get()`` for a PK lookup (identity-map hit when cached),
        then validates ownership via ``_assert_tenant_owns``.  Returns ``None``
        if no row with *artifact_id* exists or if the row belongs to a different
        tenant -- both cases are treated identically to avoid cross-tenant
        existence disclosure.

        Parameters
        ----------
        artifact_id:
            UUID primary key of the artifact to fetch.
        auth_context:
            Optional authentication context.  When provided, sets the active
            tenant via ``TenantContext`` before filtering.

        Returns
        -------
        EnterpriseArtifact or None
            The matching row, or ``None`` if absent or owned by another tenant.
        """
        from skillmeat.cache.models_enterprise import EnterpriseArtifact

        from skillmeat.core.repositories.filters import apply_visibility_filter_stmt

        self._apply_auth_context(auth_context)
        obj = self.session.get(EnterpriseArtifact, artifact_id)
        if obj is None:
            return None
        try:
            self._assert_tenant_owns(obj)
        except TenantIsolationError:
            logger.debug(
                "get(%s): artifact exists but belongs to a different tenant; "
                "returning None to avoid tenant-existence disclosure",
                artifact_id,
            )
            return None
        # ENT-002: Enforce visibility after tenant check.  Private artifacts
        # are only visible to their owner; admins bypass the filter.
        # Returns None for both not-found and not-visible (prevents existence
        # disclosure — callers cannot distinguish the two cases).
        if auth_context is not None:
            stmt = apply_visibility_filter_stmt(
                select(EnterpriseArtifact).where(EnterpriseArtifact.id == artifact_id),
                EnterpriseArtifact,
                auth_context,
            )
            obj = self.session.execute(stmt).scalar_one_or_none()
        return obj

    def get_by_uuid(
        self,
        artifact_uuid: str,
        auth_context: Optional["AuthContext"] = None,
    ) -> "Optional[EnterpriseArtifact]":
        """Fetch an artifact by its UUID string with tenant filter at query time.

        Unlike ``get()``, accepts a *string* UUID (the form typically received
        from an API path parameter) and applies the tenant predicate directly in
        the SELECT so that only the owning tenant's row is ever returned.

        Parameters
        ----------
        artifact_uuid:
            UUID of the artifact as a string; will be parsed to ``uuid.UUID``.
        auth_context:
            Optional authentication context.  When provided, sets the active
            tenant via ``TenantContext`` before filtering.

        Returns
        -------
        EnterpriseArtifact or None
            The matching row, or ``None`` if not found for the current tenant.

        Raises
        ------
        ValueError
            If *artifact_uuid* is not a valid UUID string.
        """
        from skillmeat.cache.models_enterprise import EnterpriseArtifact

        from skillmeat.core.repositories.filters import apply_visibility_filter_stmt

        self._apply_auth_context(auth_context)
        parsed: uuid.UUID = uuid.UUID(artifact_uuid)
        stmt = self._tenant_select().where(EnterpriseArtifact.id == parsed)
        # ENT-002: Enforce visibility access control when auth context is present.
        # Returns None for both not-found and not-visible (prevents existence
        # disclosure — callers cannot distinguish the two cases).
        if auth_context is not None:
            stmt = apply_visibility_filter_stmt(stmt, EnterpriseArtifact, auth_context)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_name(
        self,
        name: str,
        auth_context: Optional["AuthContext"] = None,
    ) -> "Optional[EnterpriseArtifact]":
        """Fetch an artifact by name within the current tenant's scope.

        Name uniqueness is enforced by ``uq_enterprise_artifacts_tenant_name_type``,
        but this method returns the *first* match ordered by ``created_at`` to
        handle any edge cases in test data.

        Parameters
        ----------
        name:
            Human-readable artifact name (e.g. ``"canvas-design"``).
            Exact, case-sensitive match.
        auth_context:
            Optional authentication context.  When provided, sets the active
            tenant via ``TenantContext`` before filtering.

        Returns
        -------
        EnterpriseArtifact or None
            The matching row, or ``None`` if not found.
        """
        from skillmeat.cache.models_enterprise import EnterpriseArtifact

        from skillmeat.core.repositories.filters import apply_visibility_filter_stmt

        self._apply_auth_context(auth_context)
        stmt = (
            self._tenant_select()
            .where(EnterpriseArtifact.name == name)
            .order_by(EnterpriseArtifact.created_at)
            .limit(1)
        )
        # ENT-002: Enforce visibility access control when auth context is present.
        # Returns None for both not-found and not-visible (prevents existence
        # disclosure — callers cannot distinguish the two cases).
        if auth_context is not None:
            stmt = apply_visibility_filter_stmt(stmt, EnterpriseArtifact, auth_context)
        return self.session.execute(stmt).scalar_one_or_none()

    # ------------------------------------------------------------------
    # ENT-2.3: Paginated listing and JSONB tag search
    # ------------------------------------------------------------------

    def list(
        self,
        offset: int = 0,
        limit: int = 50,
        artifact_type: Optional[str] = None,
        name_contains: Optional[str] = None,
        auth_context: Optional["AuthContext"] = None,
    ) -> "List[EnterpriseArtifact]":
        """Return a paginated list of artifacts for the current tenant.

        Filters are additive (AND logic).  Results are ordered newest-first by
        ``created_at`` so callers always see recently added artifacts at the top.

        Parameters
        ----------
        offset:
            Number of rows to skip.  Combine with *limit* for page-based
            navigation: ``offset = page * limit``.
        limit:
            Maximum number of rows to return.
        artifact_type:
            When provided, restrict results to this type (e.g. ``"skill"``,
            ``"command"``).  Must match the ``ck_enterprise_artifacts_type``
            vocabulary.
        name_contains:
            When provided, perform a case-insensitive substring match on
            ``name`` using SQL ``ILIKE``.
        auth_context:
            Optional authentication context.  When provided, sets the active
            tenant via ``TenantContext`` before filtering.

        Returns
        -------
        list[EnterpriseArtifact]
            Ordered list of matching artifacts (may be empty).
        """
        from skillmeat.cache.models_enterprise import EnterpriseArtifact
        from skillmeat.core.repositories.filters import apply_visibility_filter_stmt

        self._apply_auth_context(auth_context)
        stmt = self._tenant_select().order_by(
            EnterpriseArtifact.created_at.desc()
        )
        if artifact_type is not None:
            stmt = stmt.where(EnterpriseArtifact.artifact_type == artifact_type)
        if name_contains is not None:
            stmt = stmt.where(
                EnterpriseArtifact.name.ilike(f"%{name_contains}%")
            )
        # ENT-002: Apply visibility-based access control when auth context is
        # present.  Public and team items are visible to all tenant members;
        # private items are restricted to their owner.
        # Visibility-excluded items are silently omitted from results.
        if auth_context is not None:
            stmt = apply_visibility_filter_stmt(stmt, EnterpriseArtifact, auth_context)
        stmt = stmt.offset(offset).limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def count(
        self,
        artifact_type: Optional[str] = None,
        auth_context: Optional["AuthContext"] = None,
    ) -> int:
        """Return the number of artifacts for the current tenant.

        Parameters
        ----------
        artifact_type:
            When provided, count only artifacts of this type.
        auth_context:
            Optional authentication context.  When provided, sets the active
            tenant via ``TenantContext`` before filtering.

        Returns
        -------
        int
            Row count matching the filter (0 if none).
        """
        from sqlalchemy import func

        from skillmeat.cache.models_enterprise import EnterpriseArtifact
        from skillmeat.core.repositories.filters import apply_visibility_filter_stmt

        self._apply_auth_context(auth_context)
        # ENT-002: For count with visibility, use a subquery approach so that
        # apply_visibility_filter_stmt (which works on a Select of the model)
        # can add its WHERE predicates before wrapping in count().
        # Counts only visibility-filtered results — excluded artifacts are not counted.
        if auth_context is not None:
            inner = self._tenant_select()
            if artifact_type is not None:
                inner = inner.where(EnterpriseArtifact.artifact_type == artifact_type)
            inner = apply_visibility_filter_stmt(inner, EnterpriseArtifact, auth_context)
            stmt = select(func.count()).select_from(inner.subquery())
        else:
            stmt = self._apply_tenant_filter(
                select(func.count()).select_from(EnterpriseArtifact)
            )
            if artifact_type is not None:
                stmt = stmt.where(EnterpriseArtifact.artifact_type == artifact_type)
        result = self.session.execute(stmt).scalar_one()
        return int(result)

    def search_by_tags(
        self,
        tags: List[str],
        match_all: bool = False,
        auth_context: Optional["AuthContext"] = None,
    ) -> "List[EnterpriseArtifact]":
        """Return artifacts whose ``tags`` JSONB array contains the given tags.

        Two matching modes are supported:

        ``match_all=True``
            The artifact's ``tags`` must contain *every* tag in *tags*.
            Uses the PostgreSQL ``@>`` containment operator on the
            GIN-indexed ``tags`` column (O(log n) via
            ``idx_enterprise_artifacts_tags_gin``).

        ``match_all=False`` (default)
            The artifact's ``tags`` must contain *at least one* of the given
            tags.  Implemented as OR-joined ``@>`` predicates so each
            individual tag lookup still hits the GIN index.

        Parameters
        ----------
        tags:
            List of tag strings to search for.  Empty list returns no rows.
        match_all:
            When ``True``, require all listed tags to be present.
        auth_context:
            Optional authentication context.  When provided, sets the active
            tenant via ``TenantContext`` before filtering.

        Returns
        -------
        list[EnterpriseArtifact]
            Matching artifacts ordered by ``created_at`` descending.
        """
        import json

        from sqlalchemy import cast, or_
        from sqlalchemy.dialects.postgresql import JSONB

        from skillmeat.cache.models_enterprise import EnterpriseArtifact

        self._apply_auth_context(auth_context)
        if not tags:
            return []

        # Use the PostgreSQL @> (contains) operator resolved by the GIN index
        # (idx_enterprise_artifacts_tags_gin).  The cast is required so
        # SQLAlchemy renders the right-hand side as a JSONB literal rather than
        # a plain text bind parameter.
        tags_col = cast(EnterpriseArtifact.tags, JSONB)

        if match_all:
            # tags_col @> '["a", "b"]'::jsonb -- single predicate, most efficient
            required_jsonb = cast(json.dumps(tags), JSONB)
            predicate = tags_col.op("@>")(required_jsonb)
            stmt = (
                self._tenant_select()
                .where(predicate)
                .order_by(EnterpriseArtifact.created_at.desc())
            )
        else:
            # OR of: tags_col @> '["a"]', tags_col @> '["b"]', ...
            predicates = [
                tags_col.op("@>")(cast(json.dumps([tag]), JSONB))
                for tag in tags
            ]
            stmt = (
                self._tenant_select()
                .where(or_(*predicates))
                .order_by(EnterpriseArtifact.created_at.desc())
            )

        # ENT-002: Enforce visibility access control when auth context is present.
        # Visibility-excluded items are silently omitted from results.
        if auth_context is not None:
            from skillmeat.core.repositories.filters import apply_visibility_filter_stmt

            stmt = apply_visibility_filter_stmt(stmt, EnterpriseArtifact, auth_context)

        return list(self.session.execute(stmt).scalars().all())

    def batch_resolve_uuids(
        self,
        artifacts: List[Tuple[str, str]],
        ctx: Optional["RequestContext"] = None,
        auth_context: Optional["AuthContext"] = None,
    ) -> Dict[Tuple[str, str], str]:
        """Batch-resolve UUIDs for multiple (artifact_type, name) pairs.

        Executes a single query with OR conditions for all pairs, applying
        tenant scoping per EnterpriseRepositoryBase conventions.

        Parameters
        ----------
        artifacts:
            List of (artifact_type, name) tuples to resolve.
        ctx:
            Optional per-request metadata (unused in enterprise repo).
        auth_context:
            Optional authentication context for tenant scoping.

        Returns
        -------
        dict
            Mapping from (artifact_type, name) tuple to 32-char hex UUID string.
            Pairs that cannot be resolved are omitted.
        """
        from sqlalchemy import and_, or_

        from skillmeat.cache.models_enterprise import EnterpriseArtifact

        if not artifacts:
            return {}

        self._apply_auth_context(auth_context)

        # Build OR conditions for each (type, name) pair
        conditions = [
            and_(
                EnterpriseArtifact.artifact_type == atype,
                EnterpriseArtifact.name == name,
            )
            for atype, name in artifacts
        ]

        stmt = self._tenant_select().where(or_(*conditions))
        rows = self.session.execute(stmt).scalars().all()

        # Map results back to (type, name) tuple keys
        return {
            (row.artifact_type, row.name): row.id.hex
            for row in rows
        }

    # ------------------------------------------------------------------
    # ENT-2.6: Version history retrieval
    # ------------------------------------------------------------------

    def get_content(
        self,
        artifact_id: uuid.UUID,
        version: Optional[str] = None,
        auth_context: Optional["AuthContext"] = None,
    ) -> Optional[str]:
        """Return the Markdown content for a specific or the latest artifact version.

        Validates the artifact against the current tenant before querying
        version rows, so a caller cannot read content from another tenant's
        artifact by guessing its UUID.

        Parameters
        ----------
        artifact_id:
            UUID primary key of the parent artifact.
        version:
            Optional ``version_tag`` string (e.g. ``"v1.2.0"``, ``"latest"``).
            When ``None``, the newest version by ``created_at`` is returned.
        auth_context:
            Optional authentication context.  When provided, sets the active
            tenant via ``TenantContext`` before filtering.

        Returns
        -------
        str or None
            The ``markdown_payload`` of the matching version, or ``None`` if
            the artifact does not exist for this tenant or has no versions.
        """
        from skillmeat.cache.models_enterprise import EnterpriseArtifactVersion

        self._apply_auth_context(auth_context)
        # get() returns None for both not-found and not-visible (prevents existence
        # disclosure).  Propagate None immediately — no separate access-denied path.
        artifact = self.get(artifact_id, auth_context=auth_context)
        if artifact is None:
            return None

        stmt = select(EnterpriseArtifactVersion).where(
            EnterpriseArtifactVersion.artifact_id == artifact_id
        )
        if version is not None:
            stmt = stmt.where(EnterpriseArtifactVersion.version_tag == version)
        else:
            stmt = stmt.order_by(EnterpriseArtifactVersion.created_at.desc())
        stmt = stmt.limit(1)

        version_row = self.session.execute(stmt).scalar_one_or_none()
        if version_row is None:
            return None
        return version_row.markdown_payload

    def list_versions(
        self,
        artifact_id: uuid.UUID,
        auth_context: Optional["AuthContext"] = None,
    ) -> "List[EnterpriseArtifactVersion]":
        """Return all version records for an artifact, newest first.

        Validates the artifact against the current tenant before querying
        version rows to prevent enumeration of another tenant's version history.

        Parameters
        ----------
        artifact_id:
            UUID primary key of the parent artifact.
        auth_context:
            Optional authentication context.  When provided, sets the active
            tenant via ``TenantContext`` before filtering.

        Returns
        -------
        list[EnterpriseArtifactVersion]
            Ordered list of version rows (newest first by ``created_at``).
            Returns an empty list if the artifact does not exist for this
            tenant or has no recorded versions.
        """
        from skillmeat.cache.models_enterprise import EnterpriseArtifactVersion

        self._apply_auth_context(auth_context)
        # get() returns None for both not-found and not-visible (prevents existence
        # disclosure).  Propagate empty list immediately — no separate access-denied path.
        artifact = self.get(artifact_id, auth_context=auth_context)
        if artifact is None:
            return []

        stmt = (
            select(EnterpriseArtifactVersion)
            .where(EnterpriseArtifactVersion.artifact_id == artifact_id)
            .order_by(EnterpriseArtifactVersion.created_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

        # ------------------------------------------------------------------
    # ENT-2.4: Create
    # ------------------------------------------------------------------

    def create(
        self,
        name: str,
        artifact_type: str,
        source: Optional[str] = None,
        content: Optional[str] = None,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
        auth_context: Optional["AuthContext"] = None,
    ) -> "EnterpriseArtifact":
        """Create a new artifact row and optionally an initial version.

        Parameters
        ----------
        name:
            Human-readable artifact name (e.g. ``"canvas-design"``).
        artifact_type:
            One of the recognised type values enforced by
            ``ck_enterprise_artifacts_type`` (e.g. ``"skill"``).
        source:
            Optional GitHub origin URL for upstream sync tracking.
        content:
            If provided, an ``EnterpriseArtifactVersion`` row at
            ``version_tag="1.0.0"`` is created alongside the artifact.
        metadata:
            Arbitrary JSONB key-value pairs stored in ``custom_fields``.
        tags:
            List of tag strings stored in the ``tags`` JSONB column.
        auth_context:
            Optional authentication context.  When provided, the active tenant
            is set via ``TenantContext`` and ``owner_id`` is populated from
            ``auth_context.user_id``.

        Returns
        -------
        EnterpriseArtifact
            The freshly committed and refreshed artifact instance.
        """
        from skillmeat.cache.models_enterprise import (
            EnterpriseArtifact,
            EnterpriseArtifactVersion,
        )

        owner_id = self._apply_auth_context(auth_context)
        tenant_id = self._get_tenant_id()
        artifact = EnterpriseArtifact(
            tenant_id=tenant_id,
            owner_id=owner_id,
            name=name,
            artifact_type=artifact_type,
            source_url=source,
            tags=tags or [],
            custom_fields=metadata or {},
        )
        self.session.add(artifact)
        self.session.flush()  # Populate artifact.id before version FK reference

        if content is not None:
            content_hash = self._compute_content_hash(content)
            version = EnterpriseArtifactVersion(
                tenant_id=tenant_id,
                artifact_id=artifact.id,
                version_tag="1.0.0",
                content_hash=content_hash,
                markdown_payload=content,
            )
            self.session.add(version)

        self.session.commit()
        self.session.refresh(artifact)
        self._log_operation(
            operation="create",
            entity_type="EnterpriseArtifact",
            entity_id=artifact.id,
            metadata={"name": name, "artifact_type": artifact_type},
        )
        return artifact

    # ------------------------------------------------------------------
    # ENT-2.4: Update
    # ------------------------------------------------------------------

    def update(
        self,
        artifact_id: uuid.UUID,
        name: Optional[str] = None,
        content: Optional[str] = None,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
        auth_context: Optional["AuthContext"] = None,
    ) -> "EnterpriseArtifact":
        """Update mutable fields on an existing artifact.

        If *content* changes (i.e. it differs from the latest stored
        version's ``markdown_payload``), a new ``EnterpriseArtifactVersion``
        row is created with an auto-incremented version tag.

        Parameters
        ----------
        artifact_id:
            UUID primary key of the artifact to update.
        name:
            New name, or ``None`` to leave unchanged.
        content:
            New Markdown content.  A new version row is only created when
            the content hash differs from the most recent stored version.
        metadata:
            Replacement ``custom_fields`` dict, or ``None`` to leave
            unchanged.
        tags:
            Replacement tag list, or ``None`` to leave unchanged.
        auth_context:
            Optional authentication context.  When provided, the active tenant
            is set via ``TenantContext`` and the update is further restricted to
            artifacts owned by ``auth_context.user_id``.

        Returns
        -------
        EnterpriseArtifact
            The updated and refreshed artifact instance.

        Raises
        ------
        ValueError
            If no artifact with *artifact_id* exists in the current tenant (or
            owned by the authenticated user when *auth_context* is provided).
        TenantIsolationError
            If the artifact belongs to a different tenant.
        """
        from skillmeat.cache.models_enterprise import (
            EnterpriseArtifact,
            EnterpriseArtifactVersion,
        )

        owner_id = self._apply_auth_context(auth_context)
        artifact: Optional[EnterpriseArtifact] = self.session.get(
            EnterpriseArtifact, artifact_id
        )
        if artifact is None:
            raise ValueError(f"EnterpriseArtifact {artifact_id!r} not found.")
        self._assert_tenant_owns(artifact)
        # When an authenticated user is present, enforce owner-level access.
        if owner_id is not None and artifact.owner_id != owner_id:
            raise ValueError(
                f"EnterpriseArtifact {artifact_id!r} is not owned by the "
                f"authenticated user."
            )

        changed_fields: Dict[str, object] = {}
        if name is not None:
            changed_fields["name"] = name
            artifact.name = name
        if metadata is not None:
            artifact.custom_fields = metadata
        if tags is not None:
            artifact.tags = tags

        artifact.updated_at = datetime.utcnow()

        if content is not None:
            new_hash = self._compute_content_hash(content)
            # Only create a new version when content actually changed
            latest_version: Optional[EnterpriseArtifactVersion] = None
            if artifact.versions:
                latest_version = artifact.versions[0]  # ordered by created_at desc
            if latest_version is None or latest_version.content_hash != new_hash:
                next_tag = (
                    self._next_version(latest_version.version_tag)
                    if latest_version
                    else "1.0.0"
                )
                new_version = EnterpriseArtifactVersion(
                    tenant_id=artifact.tenant_id,
                    artifact_id=artifact.id,
                    version_tag=next_tag,
                    content_hash=new_hash,
                    markdown_payload=content,
                )
                self.session.add(new_version)
                changed_fields["new_version_tag"] = next_tag

        self.session.commit()
        self.session.refresh(artifact)
        self._log_operation(
            operation="update",
            entity_type="EnterpriseArtifact",
            entity_id=artifact_id,
            metadata=changed_fields or None,
        )
        return artifact

    # ------------------------------------------------------------------
    # ENT-2.5: Soft delete
    # ------------------------------------------------------------------

    def soft_delete(
        self,
        artifact_id: uuid.UUID,
        auth_context: Optional["AuthContext"] = None,
    ) -> bool:
        """Logically delete an artifact by clearing ``is_active``.

        The row is retained in the database for audit purposes.  Subsequent
        reads that filter on ``is_active = TRUE`` will exclude this artifact.

        Parameters
        ----------
        artifact_id:
            UUID primary key of the artifact to soft-delete.
        auth_context:
            Optional authentication context.  When provided, the active tenant
            is set via ``TenantContext`` and the operation is restricted to
            artifacts owned by ``auth_context.user_id``.

        Returns
        -------
        bool
            ``True`` on success.

        Raises
        ------
        ValueError
            If no artifact with *artifact_id* exists in the current tenant (or
            owned by the authenticated user when *auth_context* is provided).
        TenantIsolationError
            If the artifact belongs to a different tenant.
        """
        from skillmeat.cache.models_enterprise import EnterpriseArtifact

        owner_id = self._apply_auth_context(auth_context)
        artifact: Optional[EnterpriseArtifact] = self.session.get(
            EnterpriseArtifact, artifact_id
        )
        if artifact is None:
            raise ValueError(f"EnterpriseArtifact {artifact_id!r} not found.")
        self._assert_tenant_owns(artifact)
        if owner_id is not None and artifact.owner_id != owner_id:
            raise ValueError(
                f"EnterpriseArtifact {artifact_id!r} is not owned by the "
                f"authenticated user."
            )

        artifact.is_active = False
        artifact.updated_at = datetime.utcnow()
        self.session.flush()
        self.session.commit()
        self._log_operation(
            operation="soft_delete",
            entity_type="EnterpriseArtifact",
            entity_id=artifact_id,
        )
        return True

    # ------------------------------------------------------------------
    # ENT-2.5: Hard delete
    # ------------------------------------------------------------------

    def hard_delete(
        self,
        artifact_id: uuid.UUID,
        auth_context: Optional["AuthContext"] = None,
    ) -> bool:
        """Permanently remove an artifact and all related rows.

        Removal order:
        1. Assert tenant ownership.
        2. Delete ``EnterpriseCollectionArtifact`` membership rows so that
           collections that hold this artifact do not end up with dangling
           references (the DB ON DELETE CASCADE handles this too, but we
           do it explicitly for clarity and to avoid relying on cascade
           configuration in test environments).
        3. Delete the ``EnterpriseArtifact`` row — the
           ``cascade="all, delete-orphan"`` on ``versions`` removes all
           associated ``EnterpriseArtifactVersion`` rows automatically via
           the SQLAlchemy ORM cascade.

        Parameters
        ----------
        artifact_id:
            UUID primary key of the artifact to permanently remove.
        auth_context:
            Optional authentication context.  When provided, the active tenant
            is set via ``TenantContext`` and the operation is restricted to
            artifacts owned by ``auth_context.user_id``.

        Returns
        -------
        bool
            ``True`` on success.

        Raises
        ------
        ValueError
            If no artifact with *artifact_id* exists in the current tenant (or
            owned by the authenticated user when *auth_context* is provided).
        TenantIsolationError
            If the artifact belongs to a different tenant.
        """
        from skillmeat.cache.models_enterprise import (
            EnterpriseArtifact,
            EnterpriseCollectionArtifact,
        )

        owner_id = self._apply_auth_context(auth_context)
        artifact: Optional[EnterpriseArtifact] = self.session.get(
            EnterpriseArtifact, artifact_id
        )
        if artifact is None:
            raise ValueError(f"EnterpriseArtifact {artifact_id!r} not found.")
        self._assert_tenant_owns(artifact)
        if owner_id is not None and artifact.owner_id != owner_id:
            raise ValueError(
                f"EnterpriseArtifact {artifact_id!r} is not owned by the "
                f"authenticated user."
            )

        # Explicitly remove collection membership rows before the artifact
        # itself so that intent is clear regardless of cascade settings.
        self.session.execute(
            delete(EnterpriseCollectionArtifact).where(
                EnterpriseCollectionArtifact.artifact_id == artifact_id
            )
        )

        # Deleting the artifact cascades to EnterpriseArtifactVersion via the
        # "all, delete-orphan" relationship cascade defined on EnterpriseArtifact.
        self.session.delete(artifact)
        self.session.commit()
        self._log_operation(
            operation="hard_delete",
            entity_type="EnterpriseArtifact",
            entity_id=artifact_id,
        )
        return True


# ---------------------------------------------------------------------------
# EnterpriseCollectionRepository  (ENT-2.7, ENT-2.8)
# ---------------------------------------------------------------------------


class EnterpriseCollectionRepository(
    EnterpriseRepositoryBase["EnterpriseCollection"]
):
    """Repository for tenant-scoped CRUD on EnterpriseCollection.

    All queries are automatically scoped to the tenant stored in
    ``TenantContext``.  Membership helpers (ENT-2.8) additionally validate
    that the target artifact belongs to the same tenant before creating a
    link.

    Parameters
    ----------
    session:
        An open SQLAlchemy ``Session`` bound to the PostgreSQL enterprise
        database.  Lifecycle (commit/rollback/close) is managed by the caller.

    Examples
    --------
    ::

        with tenant_scope(tenant_uuid):
            repo = EnterpriseCollectionRepository(db_session)
            col = repo.create("My Collection", description="Personal picks")
            repo.add_artifact(col.id, artifact_uuid)
            artifacts = repo.list_artifacts(col.id)
    """

    def __init__(self, session: Session) -> None:
        from skillmeat.cache.models_enterprise import EnterpriseCollection as _EC

        super().__init__(session, _EC)

    # ------------------------------------------------------------------
    # ENT-2.7: Collection CRUD
    # ------------------------------------------------------------------

    def create(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None,
        auth_context: Optional["AuthContext"] = None,
    ) -> "EnterpriseCollection":
        """Create a new collection scoped to the current tenant.

        Parameters
        ----------
        name:
            Human-readable collection name; must be unique per tenant.
        description:
            Optional free-text description.
        metadata:
            Reserved for future extensibility; unused by the model today.
        auth_context:
            Optional authentication context.  When provided, the active tenant
            is set via ``TenantContext`` and ``owner_id`` is populated from
            ``auth_context.user_id``.

        Returns
        -------
        EnterpriseCollection
            The newly persisted ORM instance (added and flushed).
        """
        from skillmeat.cache.models_enterprise import EnterpriseCollection

        owner_id = self._apply_auth_context(auth_context)
        tenant_id = self._get_tenant_id()
        collection = EnterpriseCollection(
            tenant_id=tenant_id,
            owner_id=owner_id,
            name=name,
            description=description,
        )
        self.session.add(collection)
        self.session.flush()
        self._log_operation(
            operation="create",
            entity_type="EnterpriseCollection",
            entity_id=collection.id,
            metadata={"name": name},
        )
        return collection

    def get(
        self,
        collection_id: uuid.UUID,
        auth_context: Optional["AuthContext"] = None,
    ) -> "Optional[EnterpriseCollection]":
        """Retrieve a collection by primary key, asserting tenant ownership.

        .. note::
            Collections are intentionally **not** visibility-filtered.
            ``EnterpriseCollection`` has no ``visibility`` column — all tenant
            members share access to every collection (shared-library model).
            Visibility filtering applies only to the *artifacts* returned
            through a collection (see :meth:`list_artifacts`).

        Parameters
        ----------
        collection_id:
            UUID primary key of the collection to fetch.
        auth_context:
            Optional authentication context.  When provided, sets the active
            tenant via ``TenantContext`` before the ownership assertion.

        Returns
        -------
        EnterpriseCollection or None
            The collection instance, or ``None`` if it does not exist.

        Raises
        ------
        TenantIsolationError
            If the retrieved collection belongs to a different tenant.
        """
        from skillmeat.cache.models_enterprise import EnterpriseCollection

        self._apply_auth_context(auth_context)
        collection = self.session.get(EnterpriseCollection, collection_id)
        if collection is None:
            return None
        self._assert_tenant_owns(collection)
        return collection

    def get_by_name(
        self,
        name: str,
        auth_context: Optional["AuthContext"] = None,
    ) -> "Optional[EnterpriseCollection]":
        """Retrieve a collection by name within the current tenant.

        .. note::
            Collections are intentionally **not** visibility-filtered.
            ``EnterpriseCollection`` has no ``visibility`` column — all tenant
            members share access to every collection (shared-library model).
            Visibility filtering applies only to the *artifacts* returned
            through a collection (see :meth:`list_artifacts`).

        Parameters
        ----------
        name:
            The exact collection name to look up.
        auth_context:
            Optional authentication context.  When provided, sets the active
            tenant via ``TenantContext`` before filtering.

        Returns
        -------
        EnterpriseCollection or None
        """
        from skillmeat.cache.models_enterprise import EnterpriseCollection

        self._apply_auth_context(auth_context)
        stmt = self._tenant_select().where(EnterpriseCollection.name == name)
        return self.session.execute(stmt).scalar_one_or_none()

    def list(
        self,
        offset: int = 0,
        limit: int = 50,
        auth_context: Optional["AuthContext"] = None,
    ) -> "List[EnterpriseCollection]":
        """Return a paginated list of collections for the current tenant.

        .. note::
            Collections are intentionally **not** visibility-filtered.
            ``EnterpriseCollection`` has no ``visibility`` column — all tenant
            members share access to every collection (shared-library model).
            Visibility filtering applies only to the *artifacts* returned
            through a collection (see :meth:`list_artifacts`).

        Parameters
        ----------
        offset:
            Number of rows to skip (0-based).
        limit:
            Maximum number of rows to return.
        auth_context:
            Optional authentication context.  When provided, sets the active
            tenant via ``TenantContext`` before filtering.

        Returns
        -------
        List[EnterpriseCollection]
            Collections ordered alphabetically by name.
        """
        from skillmeat.cache.models_enterprise import EnterpriseCollection

        self._apply_auth_context(auth_context)
        stmt = (
            self._tenant_select()
            .order_by(EnterpriseCollection.name)
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars())

    def update(
        self,
        collection_id: uuid.UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        auth_context: Optional["AuthContext"] = None,
    ) -> "EnterpriseCollection":
        """Update mutable fields on an existing collection.

        Only non-``None`` arguments are applied; passing ``None`` leaves the
        field unchanged.

        Parameters
        ----------
        collection_id:
            UUID of the collection to update.
        name:
            New name, or ``None`` to leave unchanged.
        description:
            New description, or ``None`` to leave unchanged.
        auth_context:
            Optional authentication context.  When provided, the active tenant
            is set via ``TenantContext`` and the update is restricted to
            collections owned by ``auth_context.user_id``.

        Returns
        -------
        EnterpriseCollection
            The updated ORM instance (already flushed).

        Raises
        ------
        ValueError
            If the collection does not exist (or is not owned by the
            authenticated user when *auth_context* is provided).
        TenantIsolationError
            If the collection belongs to a different tenant.
        """
        owner_id = self._apply_auth_context(auth_context)
        collection = self.get(collection_id)
        if collection is None:
            raise ValueError(
                f"EnterpriseCollection {collection_id!r} not found."
            )
        if owner_id is not None and collection.owner_id != owner_id:
            raise ValueError(
                f"EnterpriseCollection {collection_id!r} is not owned by the "
                f"authenticated user."
            )
        changed: Dict[str, object] = {}
        if name is not None:
            changed["name"] = name
            collection.name = name
        if description is not None:
            changed["description"] = description
            collection.description = description
        collection.updated_at = datetime.utcnow()
        self.session.flush()
        self._log_operation(
            operation="update",
            entity_type="EnterpriseCollection",
            entity_id=collection_id,
            metadata=changed or None,
        )
        return collection

    def delete(
        self,
        collection_id: uuid.UUID,
        auth_context: Optional["AuthContext"] = None,
    ) -> bool:
        """Delete a collection and all of its membership rows.

        Membership rows are removed first (in case the DB engine does not
        honour cascade deletes in the same flush), then the collection itself
        is deleted.

        Parameters
        ----------
        collection_id:
            UUID of the collection to delete.
        auth_context:
            Optional authentication context.  When provided, the active tenant
            is set via ``TenantContext`` and the operation is restricted to
            collections owned by ``auth_context.user_id``.

        Returns
        -------
        bool
            ``True`` if the collection existed and was deleted; ``False`` if it
            was not found.

        Raises
        ------
        ValueError
            If the collection is not owned by the authenticated user when
            *auth_context* is provided.
        TenantIsolationError
            If the collection belongs to a different tenant.
        """
        from skillmeat.cache.models_enterprise import EnterpriseCollectionArtifact

        owner_id = self._apply_auth_context(auth_context)
        collection = self.get(collection_id)
        if collection is None:
            return False
        if owner_id is not None and collection.owner_id != owner_id:
            raise ValueError(
                f"EnterpriseCollection {collection_id!r} is not owned by the "
                f"authenticated user."
            )
        # Remove membership rows explicitly alongside the ORM cascade.
        self.session.execute(
            delete(EnterpriseCollectionArtifact).where(
                EnterpriseCollectionArtifact.collection_id == collection_id
            )
        )
        self.session.delete(collection)
        self.session.flush()
        self._log_operation(
            operation="delete",
            entity_type="EnterpriseCollection",
            entity_id=collection_id,
        )
        return True

    # ------------------------------------------------------------------
    # ENT-2.8: Collection membership
    # ------------------------------------------------------------------

    def _get_artifact_for_tenant(
        self,
        artifact_id: uuid.UUID,
        auth_context: Optional["AuthContext"] = None,
    ) -> "Optional[EnterpriseArtifact]":
        """Return an EnterpriseArtifact if it exists and belongs to the current tenant.

        This is a write-path helper (called from :meth:`add_artifact`).
        Visibility filtering is intentionally not applied here: write
        operations check tenant isolation only, not per-user visibility.

        Parameters
        ----------
        artifact_id:
            UUID of the artifact to look up.
        auth_context:
            Optional authentication context.  Reserved for future use;
            currently unused in write-path existence checks (``None`` is the
            expected default).

        Raises
        ------
        TenantIsolationError
            If the artifact exists but belongs to a different tenant.
        """
        from skillmeat.cache.models_enterprise import EnterpriseArtifact

        artifact = self.session.get(EnterpriseArtifact, artifact_id)
        if artifact is None:
            return None
        current_tenant = self._get_tenant_id()
        if artifact.tenant_id != current_tenant:
            raise TenantIsolationError(
                object_tenant_id=artifact.tenant_id,
                current_tenant_id=current_tenant,
                detail=(
                    f"EnterpriseArtifact {artifact_id!r} belongs to a different tenant."
                ),
            )
        return artifact

    def add_artifact(
        self,
        collection_id: uuid.UUID,
        artifact_id: uuid.UUID,
        position: Optional[int] = None,
        auth_context: Optional["AuthContext"] = None,
    ) -> "EnterpriseCollectionArtifact":
        """Add an artifact to a collection.

        Both the collection and the artifact must belong to the current tenant.
        If *position* is ``None`` the artifact is appended after all existing
        members (``max(order_index) + 1``).

        Parameters
        ----------
        collection_id:
            UUID of the target collection.
        artifact_id:
            UUID of the artifact to add.
        position:
            Explicit 0-based position index; ``None`` = append.
        auth_context:
            Optional authentication context.  When provided, sets the active
            tenant via ``TenantContext`` before all ownership checks.

        Returns
        -------
        EnterpriseCollectionArtifact
            The newly created membership row (flushed but not committed).

        Raises
        ------
        ValueError
            If the collection or artifact does not exist.
        TenantIsolationError
            If either belongs to a different tenant.
        """
        from sqlalchemy import func as _func
        from skillmeat.cache.models_enterprise import EnterpriseCollectionArtifact

        self._apply_auth_context(auth_context)
        collection = self.get(collection_id)
        if collection is None:
            raise ValueError(
                f"EnterpriseCollection {collection_id!r} not found."
            )
        artifact = self._get_artifact_for_tenant(artifact_id)
        if artifact is None:
            raise ValueError(
                f"EnterpriseArtifact {artifact_id!r} not found."
            )

        if position is None:
            result = self.session.execute(
                select(_func.max(EnterpriseCollectionArtifact.order_index)).where(
                    EnterpriseCollectionArtifact.collection_id == collection_id
                )
            ).scalar()
            position = 0 if result is None else result + 1

        membership = EnterpriseCollectionArtifact(
            collection_id=collection_id,
            artifact_id=artifact_id,
            order_index=position,
        )
        self.session.add(membership)
        self.session.flush()
        self._log_operation(
            operation="add_artifact",
            entity_type="EnterpriseCollectionArtifact",
            entity_id=membership.id,
            metadata={
                "collection_id": str(collection_id),
                "artifact_id": str(artifact_id),
                "position": position,
            },
        )
        return membership

    def remove_artifact(
        self,
        collection_id: uuid.UUID,
        artifact_id: uuid.UUID,
        auth_context: Optional["AuthContext"] = None,
    ) -> bool:
        """Remove an artifact from a collection.

        Parameters
        ----------
        collection_id:
            UUID of the collection.
        artifact_id:
            UUID of the artifact to remove.
        auth_context:
            Optional authentication context.  When provided, sets the active
            tenant via ``TenantContext`` before the ownership check.

        Returns
        -------
        bool
            ``True`` if a membership row was found and deleted; ``False`` if
            the membership did not exist.

        Raises
        ------
        TenantIsolationError
            If the collection belongs to a different tenant.
        """
        from skillmeat.cache.models_enterprise import EnterpriseCollectionArtifact

        self._apply_auth_context(auth_context)
        collection = self.get(collection_id)
        if collection is None:
            return False

        result = self.session.execute(
            delete(EnterpriseCollectionArtifact).where(
                EnterpriseCollectionArtifact.collection_id == collection_id,
                EnterpriseCollectionArtifact.artifact_id == artifact_id,
            )
        )
        deleted = result.rowcount > 0
        if deleted:
            self.session.flush()
            self._log_operation(
                operation="remove_artifact",
                entity_type="EnterpriseCollectionArtifact",
                entity_id=None,
                metadata={
                    "collection_id": str(collection_id),
                    "artifact_id": str(artifact_id),
                },
            )
        return deleted

    def list_artifacts(
        self,
        collection_id: uuid.UUID,
        auth_context: Optional["AuthContext"] = None,
    ) -> "List[EnterpriseArtifact]":
        """Return the visibility-filtered artifacts in a collection, ordered by position.

        Collections themselves are public-within-tenant (no ``visibility``
        column on ``EnterpriseCollection``).  However, the *artifacts* inside
        a collection DO carry per-row visibility, so a tenant member must not
        see private artifacts owned by someone else just because they share a
        collection.  When *auth_context* is provided,
        :func:`~skillmeat.core.repositories.filters.apply_visibility_filter_stmt`
        is applied to the ``EnterpriseArtifact`` half of the join so that only
        rows the caller is permitted to see are returned.

        Parameters
        ----------
        collection_id:
            UUID of the collection.
        auth_context:
            Optional authentication context.  When provided, sets the active
            tenant via ``TenantContext`` before the ownership check and applies
            per-user visibility filtering to the returned artifacts.

        Returns
        -------
        List[EnterpriseArtifact]
            Artifacts ordered by ``order_index`` ascending, filtered by the
            caller's visibility permissions when *auth_context* is not ``None``.

        Raises
        ------
        TenantIsolationError
            If the collection belongs to a different tenant.
        """
        from skillmeat.cache.models_enterprise import (
            EnterpriseArtifact,
            EnterpriseCollectionArtifact,
        )
        from skillmeat.core.repositories.filters import apply_visibility_filter_stmt

        self._apply_auth_context(auth_context)
        collection = self.get(collection_id)
        if collection is None:
            return []

        stmt = (
            select(EnterpriseArtifact)
            .join(
                EnterpriseCollectionArtifact,
                EnterpriseCollectionArtifact.artifact_id == EnterpriseArtifact.id,
            )
            .where(
                EnterpriseCollectionArtifact.collection_id == collection_id,
                EnterpriseArtifact.tenant_id == self._get_tenant_id(),
            )
            .order_by(EnterpriseCollectionArtifact.order_index)
        )
        # ENT-002: Visibility-excluded artifacts are silently omitted from
        # results.  Members cannot see private artifacts owned by others even
        # when they share the same collection.
        if auth_context is not None:
            stmt = apply_visibility_filter_stmt(stmt, EnterpriseArtifact, auth_context)
        return list(self.session.execute(stmt).scalars())

    def reorder_artifacts(
        self,
        collection_id: uuid.UUID,
        artifact_ids: List[uuid.UUID],
        auth_context: Optional["AuthContext"] = None,
    ) -> bool:
        """Reorder artifacts within a collection.

        Sets ``order_index`` for each membership to the position of that
        artifact in *artifact_ids* (0-based).  Artifacts that are currently
        members but absent from *artifact_ids* retain their existing
        ``order_index`` values.

        Parameters
        ----------
        collection_id:
            UUID of the collection to reorder.
        artifact_ids:
            Ordered list of artifact UUIDs.  Position 0 → ``order_index = 0``.
        auth_context:
            Optional authentication context.  When provided, sets the active
            tenant via ``TenantContext`` before the ownership check.

        Returns
        -------
        bool
            ``True`` if the collection exists and the update was applied;
            ``False`` if the collection was not found.

        Raises
        ------
        TenantIsolationError
            If the collection belongs to a different tenant.
        """
        from skillmeat.cache.models_enterprise import EnterpriseCollectionArtifact

        self._apply_auth_context(auth_context)
        collection = self.get(collection_id)
        if collection is None:
            return False

        for index, artifact_id in enumerate(artifact_ids):
            self.session.execute(
                EnterpriseCollectionArtifact.__table__.update()
                .where(
                    EnterpriseCollectionArtifact.collection_id == collection_id,
                    EnterpriseCollectionArtifact.artifact_id == artifact_id,
                )
                .values(order_index=index)
            )

        self.session.flush()
        self._log_operation(
            operation="reorder_artifacts",
            entity_type="EnterpriseCollection",
            entity_id=collection_id,
            metadata={"count": len(artifact_ids)},
        )


# =============================================================================
# EnterpriseUserCollectionAdapter
# =============================================================================


class EnterpriseUserCollectionAdapter(IDbUserCollectionRepository):
    """Adapts :class:`EnterpriseCollectionRepository` to
    :class:`~skillmeat.core.interfaces.repositories.IDbUserCollectionRepository`.

    In enterprise mode the ``user_collections`` router must query PostgreSQL
    instead of SQLite.  This adapter wraps the existing
    :class:`EnterpriseCollectionRepository` and translates its ORM results to
    :class:`~skillmeat.core.interfaces.dtos.UserCollectionDTO` frozen
    dataclasses, satisfying the interface contract without modifying the
    underlying repository or the router.

    Parameters
    ----------
    session:
        An open SQLAlchemy ``Session`` bound to the PostgreSQL enterprise
        database.  Lifecycle is managed by the FastAPI DI layer via
        ``get_db_session``.
    """

    def __init__(self, session: Session) -> None:
        self._repo = EnterpriseCollectionRepository(session=session)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_dto(collection: "EnterpriseCollection") -> "UserCollectionDTO":  # type: ignore[name-defined]
        """Convert an :class:`EnterpriseCollection` ORM instance to a DTO."""
        from skillmeat.core.interfaces.dtos import UserCollectionDTO

        created_at_iso: Optional[str] = None
        updated_at_iso: Optional[str] = None
        if collection.created_at is not None:
            created_at_iso = collection.created_at.isoformat()
        if collection.updated_at is not None:
            updated_at_iso = collection.updated_at.isoformat()

        # created_by on EnterpriseCollection is a string (user ID or "system")
        created_by = collection.created_by

        # Membership count — available only when the relationship is loaded;
        # fall back to 0 rather than triggering a lazy load.
        try:
            artifact_count = len(collection.memberships)
        except Exception:
            artifact_count = 0

        return UserCollectionDTO(
            id=str(collection.id),
            name=collection.name,
            description=collection.description,
            created_by=created_by,
            collection_type=None,
            context_category=None,
            created_at=created_at_iso,
            updated_at=updated_at_iso,
            artifact_count=artifact_count,
        )

    # ------------------------------------------------------------------
    # IDbUserCollectionRepository implementation
    # ------------------------------------------------------------------

    def list(
        self,
        *,
        created_by: Optional[str] = None,
        collection_type: Optional[str] = None,
        context_category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        ctx: Optional[object] = None,
    ) -> "list[UserCollectionDTO]":  # type: ignore[override]
        """Return a paginated list of enterprise collections as DTOs.

        The *created_by*, *collection_type*, and *context_category* filters
        map as follows against the enterprise schema:

        * ``created_by`` — filters by ``EnterpriseCollection.created_by``
          (string user-ID column).
        * ``collection_type`` and ``context_category`` — the enterprise schema
          has no direct equivalents; these filters are silently ignored so the
          adapter remains forward-compatible.
        """
        from skillmeat.cache.models_enterprise import EnterpriseCollection

        collections = self._repo.list(offset=offset, limit=limit)

        if created_by is not None:
            collections = [c for c in collections if c.created_by == created_by]

        return [self._to_dto(c) for c in collections]

    def get_by_id(
        self,
        collection_id: str,
        ctx: Optional[object] = None,
    ) -> "UserCollectionDTO | None":
        """Return a collection by its UUID string primary key."""
        try:
            uid = uuid.UUID(collection_id)
        except (ValueError, AttributeError):
            return None

        collection = self._repo.get(uid)
        if collection is None:
            return None
        return self._to_dto(collection)

    def get_by_name(
        self,
        name: str,
        ctx: Optional[object] = None,
    ) -> "UserCollectionDTO | None":
        """Return a collection by its human-readable name."""
        collection = self._repo.get_by_name(name)
        if collection is None:
            return None
        return self._to_dto(collection)

    def create(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        created_by: Optional[str] = None,
        collection_type: Optional[str] = None,
        context_category: Optional[str] = None,
        ctx: Optional[object] = None,
    ) -> "UserCollectionDTO":
        """Persist a new enterprise collection and return its DTO."""
        collection = self._repo.create(name=name, description=description)
        # Populate created_by when provided and the ORM model supports it.
        if created_by is not None and hasattr(collection, "created_by"):
            collection.created_by = created_by
            self._repo.session.flush()
        return self._to_dto(collection)

    def update(
        self,
        collection_id: str,
        ctx: Optional[object] = None,
        **kwargs: object,
    ) -> "UserCollectionDTO":
        """Apply a partial update to an existing enterprise collection."""
        try:
            uid = uuid.UUID(collection_id)
        except (ValueError, AttributeError):
            raise KeyError(f"Collection {collection_id!r} not found.")

        collection = self._repo.update(
            uid,
            name=kwargs.get("name"),
            description=kwargs.get("description"),
        )
        return self._to_dto(collection)

    def delete(
        self,
        collection_id: str,
        ctx: Optional[object] = None,
    ) -> bool:
        """Delete an enterprise collection and all its membership records."""
        try:
            uid = uuid.UUID(collection_id)
        except (ValueError, AttributeError):
            return False

        return self._repo.delete(uid)

    def ensure_default(
        self,
        *,
        created_by: Optional[str] = None,
        ctx: Optional[object] = None,
    ) -> "UserCollectionDTO":
        """Return the default collection, creating it if it does not exist."""
        default_name = "Default Collection"
        existing = self._repo.get_by_name(default_name)
        if existing is not None:
            return self._to_dto(existing)

        collection = self._repo.create(name=default_name, description="Default collection")
        if created_by is not None and hasattr(collection, "created_by"):
            collection.created_by = created_by
            self._repo.session.flush()
        return self._to_dto(collection)

    def ensure_sentinel_project(self) -> None:
        """No-op for enterprise mode — enterprise uses different FK relationships."""
        pass

    def get_artifact_count(
        self,
        collection_id: str,
        ctx: Optional[object] = None,
    ) -> int:
        """Return the number of artifacts in the given enterprise collection."""
        from sqlalchemy import func
        from skillmeat.cache.models_enterprise import EnterpriseCollectionArtifact

        try:
            uid = uuid.UUID(collection_id)
        except (ValueError, AttributeError):
            return 0

        result = self._repo.session.execute(
            select(func.count()).select_from(EnterpriseCollectionArtifact).where(
                EnterpriseCollectionArtifact.collection_id == uid
            )
        )
        return result.scalar_one() or 0

    def get_groups(
        self,
        collection_id: str,
        ctx: Optional[object] = None,
    ) -> "list[str]":
        """Enterprise does not have the same group association model; returns empty list."""
        return []

    def list_with_artifact_stats(
        self,
        *,
        created_by: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        ctx: Optional[object] = None,
    ) -> "list[UserCollectionDTO]":
        """Return collections with artifact_count populated.

        Delegates to :meth:`list`; the DTO already carries ``artifact_count``
        from :meth:`_to_dto`.
        """
        return self.list(
            created_by=created_by,
            limit=limit,
            offset=offset,
            ctx=ctx,
        )

    def add_group(
        self,
        collection_id: str,
        group_id: str,
        ctx: Optional[object] = None,
    ) -> bool:
        """Enterprise does not support the same group model; returns False."""
        return False

    def remove_group(
        self,
        collection_id: str,
        group_id: str,
        ctx: Optional[object] = None,
    ) -> bool:
        """Enterprise does not support the same group model; returns False."""
        return False


# ---------------------------------------------------------------------------
# EnterpriseTagRepository  (ENT2-3.1)
# ---------------------------------------------------------------------------


class EnterpriseTagRepository(
    EnterpriseRepositoryBase["EnterpriseTag"],
):
    """Repository for tenant-scoped CRUD on EnterpriseTag.

    Implements :class:`~skillmeat.core.interfaces.repositories.ITagRepository`
    for the enterprise PostgreSQL backend.

    All queries are automatically scoped to the tenant stored in
    ``TenantContext`` via ``_apply_tenant_filter()``.  Slug generation
    normalises the tag name using a simple regex: lowercase, replace
    non-alphanumeric runs with hyphens, strip leading/trailing hyphens.

    Parameters
    ----------
    session:
        An open SQLAlchemy ``Session`` bound to the enterprise database.
        Lifecycle (commit/rollback/close) is managed by the caller.

    Notes
    -----
    The interface defines ``id`` as ``str``; enterprise tag PKs are
    ``uuid.UUID``.  All public methods accept and return ``str`` IDs and
    convert internally.
    """

    def __init__(self, session: Session) -> None:
        from skillmeat.cache.models_enterprise import EnterpriseTag as _ET

        super().__init__(session, _ET)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _slugify(name: str) -> str:
        """Derive a URL-safe slug from *name*.

        Lowercases the string, replaces every run of non-alphanumeric
        characters (including spaces) with a single hyphen, and strips
        leading/trailing hyphens.

        Parameters
        ----------
        name:
            Human-readable tag name, e.g. ``"AI & ML"``.

        Returns
        -------
        str
            Normalised slug, e.g. ``"ai-ml"``.
        """
        import re

        slug = name.lower()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        return slug.strip("-")

    def _to_dto(self, tag: "EnterpriseTag", artifact_count: int = 0) -> "TagDTO":
        """Map an ``EnterpriseTag`` ORM instance to a :class:`~skillmeat.core.interfaces.dtos.TagDTO`.

        Parameters
        ----------
        tag:
            ORM instance to convert.
        artifact_count:
            Number of artifacts currently carrying this tag.  Defaults to
            ``0`` when the caller does not supply a pre-computed count.

        Returns
        -------
        TagDTO
            Immutable DTO ready for serialisation.
        """
        from skillmeat.core.interfaces.dtos import TagDTO

        return TagDTO(
            id=str(tag.id),
            name=tag.name,
            slug=tag.slug,
            color=tag.color,
            artifact_count=artifact_count,
            deployment_set_count=0,
            created_at=tag.created_at.isoformat() if tag.created_at else None,
            updated_at=tag.updated_at.isoformat() if tag.updated_at else None,
        )

    # ------------------------------------------------------------------
    # ITagRepository: get
    # ------------------------------------------------------------------

    def get(
        self,
        id: str,
        ctx: "Optional[object]" = None,
    ) -> "Optional[TagDTO]":
        """Return a :class:`~skillmeat.core.interfaces.dtos.TagDTO` by string UUID.

        Parameters
        ----------
        id:
            Tag UUID as a string (e.g. from an API path parameter).
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        TagDTO or None
            The matching DTO when found within the current tenant, ``None``
            otherwise.
        """
        from skillmeat.cache.models_enterprise import EnterpriseTag

        try:
            tag_uuid = uuid.UUID(id)
        except (ValueError, AttributeError):
            return None
        stmt = self._tenant_select().where(EnterpriseTag.id == tag_uuid)
        tag = self.session.execute(stmt).scalar_one_or_none()
        if tag is None:
            return None
        return self._to_dto(tag, artifact_count=len(tag.artifact_tags))

    # ------------------------------------------------------------------
    # ITagRepository: get_by_slug
    # ------------------------------------------------------------------

    def get_by_slug(
        self,
        slug: str,
        ctx: "Optional[object]" = None,
    ) -> "Optional[TagDTO]":
        """Return a :class:`~skillmeat.core.interfaces.dtos.TagDTO` by slug.

        Parameters
        ----------
        slug:
            URL-safe normalised tag slug (e.g. ``"ai-ml"``).
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        TagDTO or None
        """
        from skillmeat.cache.models_enterprise import EnterpriseTag

        stmt = self._tenant_select().where(EnterpriseTag.slug == slug)
        tag = self.session.execute(stmt).scalar_one_or_none()
        if tag is None:
            return None
        return self._to_dto(tag, artifact_count=len(tag.artifact_tags))

    # ------------------------------------------------------------------
    # ITagRepository: list
    # ------------------------------------------------------------------

    def list(
        self,
        filters: "Optional[dict]" = None,
        ctx: "Optional[object]" = None,
    ) -> "list[TagDTO]":
        """Return all tags for the current tenant.

        Parameters
        ----------
        filters:
            Optional filter map.  Recognised key: ``"name"`` — performs a
            case-insensitive prefix filter.  Unknown keys are ignored.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        list[TagDTO]
            Tags ordered alphabetically by name.
        """
        from sqlalchemy import func
        from skillmeat.cache.models_enterprise import EnterpriseTag

        stmt = self._tenant_select().order_by(EnterpriseTag.name)
        if filters:
            name_filter = filters.get("name")
            if name_filter:
                stmt = stmt.where(
                    func.lower(EnterpriseTag.name).like(
                        f"{name_filter.lower()}%"
                    )
                )
        tags = list(self.session.execute(stmt).scalars())
        return [self._to_dto(t, artifact_count=len(t.artifact_tags)) for t in tags]

    # ------------------------------------------------------------------
    # ITagRepository: create
    # ------------------------------------------------------------------

    def create(
        self,
        name: str,
        color: "Optional[str]" = None,
        ctx: "Optional[object]" = None,
    ) -> "TagDTO":
        """Create a new tenant-scoped tag.

        The slug is automatically derived from *name* via :meth:`_slugify`.

        Parameters
        ----------
        name:
            Human-readable tag name.  Must be unique within the tenant.
        color:
            Optional hex or CSS colour string (e.g. ``"#3B82F6"``).
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        TagDTO
            The newly created tag.

        Raises
        ------
        ValueError
            If a tag with the same derived slug already exists for this tenant.
        """
        from skillmeat.cache.models_enterprise import EnterpriseTag

        tenant_id = self._get_tenant_id()
        slug = self._slugify(name)

        # Guard: uniqueness check on (tenant_id, slug) before insert.
        existing = self.get_by_slug(slug)
        if existing is not None:
            raise ValueError(
                f"A tag with slug {slug!r} already exists in this tenant."
            )

        tag = EnterpriseTag(
            tenant_id=tenant_id,
            name=name,
            slug=slug,
            color=color,
        )
        self.session.add(tag)
        self.session.flush()
        self._log_operation(
            operation="create",
            entity_type="EnterpriseTag",
            entity_id=tag.id,
            metadata={"name": name, "slug": slug},
        )
        return self._to_dto(tag)

    # ------------------------------------------------------------------
    # ITagRepository: update
    # ------------------------------------------------------------------

    def update(
        self,
        id: str,
        updates: "dict",
        ctx: "Optional[object]" = None,
    ) -> "TagDTO":
        """Apply a partial update to an existing tag.

        Parameters
        ----------
        id:
            Tag UUID as a string.
        updates:
            Map of field names to new values.  Recognised keys:
            ``"name"``, ``"color"``.  An updated ``"name"`` automatically
            regenerates the slug unless ``"slug"`` is also provided
            explicitly.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        TagDTO
            The updated tag DTO.

        Raises
        ------
        KeyError
            If no tag with *id* exists in the current tenant.
        """
        from skillmeat.cache.models_enterprise import EnterpriseTag

        try:
            tag_uuid = uuid.UUID(id)
        except (ValueError, AttributeError) as exc:
            raise KeyError(id) from exc

        stmt = self._tenant_select().where(EnterpriseTag.id == tag_uuid)
        tag = self.session.execute(stmt).scalar_one_or_none()
        if tag is None:
            raise KeyError(id)

        changed: Dict[str, object] = {}
        if "name" in updates:
            tag.name = updates["name"]
            changed["name"] = updates["name"]
            # Auto-regenerate slug when name changes unless slug is explicit.
            if "slug" not in updates:
                tag.slug = self._slugify(updates["name"])
                changed["slug"] = tag.slug
        if "slug" in updates:
            tag.slug = updates["slug"]
            changed["slug"] = updates["slug"]
        if "color" in updates:
            tag.color = updates["color"]
            changed["color"] = updates["color"]

        tag.updated_at = datetime.utcnow()
        self.session.flush()
        self._log_operation(
            operation="update",
            entity_type="EnterpriseTag",
            entity_id=tag_uuid,
            metadata=changed or None,
        )
        return self._to_dto(tag, artifact_count=len(tag.artifact_tags))

    # ------------------------------------------------------------------
    # ITagRepository: delete
    # ------------------------------------------------------------------

    def delete(
        self,
        id: str,
        ctx: "Optional[object]" = None,
    ) -> bool:
        """Delete a tag and remove all its artifact associations.

        The ``ON DELETE CASCADE`` on ``enterprise_artifact_tags.tag_id``
        removes association rows automatically at the database level.

        Parameters
        ----------
        id:
            Tag UUID as a string.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        bool
            ``True`` when the tag was found and deleted, ``False`` otherwise.
        """
        from skillmeat.cache.models_enterprise import EnterpriseTag

        try:
            tag_uuid = uuid.UUID(id)
        except (ValueError, AttributeError):
            return False

        stmt = self._tenant_select().where(EnterpriseTag.id == tag_uuid)
        tag = self.session.execute(stmt).scalar_one_or_none()
        if tag is None:
            return False

        self.session.delete(tag)
        self.session.flush()
        self._log_operation(
            operation="delete",
            entity_type="EnterpriseTag",
            entity_id=tag_uuid,
        )
        return True

    # ------------------------------------------------------------------
    # ITagRepository: assign
    # ------------------------------------------------------------------

    def assign(
        self,
        tag_id: str,
        artifact_id: str,
        ctx: "Optional[object]" = None,
    ) -> bool:
        """Associate a tag with an artifact (idempotent).

        Parameters
        ----------
        tag_id:
            Tag UUID as a string.
        artifact_id:
            Artifact UUID as a string.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        bool
            ``True`` on success (including when the association already existed).

        Raises
        ------
        KeyError
            If *tag_id* or *artifact_id* does not exist within the current
            tenant.
        """
        from skillmeat.cache.models_enterprise import (
            EnterpriseArtifact,
            EnterpriseArtifactTag,
            EnterpriseTag,
        )

        try:
            tag_uuid = uuid.UUID(tag_id)
            artifact_uuid = uuid.UUID(artifact_id)
        except (ValueError, AttributeError) as exc:
            raise KeyError(tag_id) from exc

        tenant_id = self._get_tenant_id()

        # Validate both entities exist within the tenant.
        tag_stmt = self._tenant_select().where(EnterpriseTag.id == tag_uuid)
        tag = self.session.execute(tag_stmt).scalar_one_or_none()
        if tag is None:
            raise KeyError(tag_id)

        art_stmt = self._apply_tenant_filter(
            select(EnterpriseArtifact).where(EnterpriseArtifact.id == artifact_uuid)
        )
        artifact = self.session.execute(art_stmt).scalar_one_or_none()
        if artifact is None:
            raise KeyError(artifact_id)

        # Idempotent: check if the association already exists.
        existing_stmt = select(EnterpriseArtifactTag).where(
            EnterpriseArtifactTag.tenant_id == tenant_id,
            EnterpriseArtifactTag.tag_id == tag_uuid,
            EnterpriseArtifactTag.artifact_uuid == artifact_uuid,
        )
        existing = self.session.execute(existing_stmt).scalar_one_or_none()
        if existing is not None:
            return True

        assoc = EnterpriseArtifactTag(
            tenant_id=tenant_id,
            tag_id=tag_uuid,
            artifact_uuid=artifact_uuid,
        )
        self.session.add(assoc)
        self.session.flush()
        self._log_operation(
            operation="assign",
            entity_type="EnterpriseArtifactTag",
            entity_id=assoc.id,
            metadata={"tag_id": str(tag_uuid), "artifact_uuid": str(artifact_uuid)},
        )
        return True

    # ------------------------------------------------------------------
    # ITagRepository: unassign
    # ------------------------------------------------------------------

    def unassign(
        self,
        tag_id: str,
        artifact_id: str,
        ctx: "Optional[object]" = None,
    ) -> bool:
        """Remove the association between a tag and an artifact.

        Parameters
        ----------
        tag_id:
            Tag UUID as a string.
        artifact_id:
            Artifact UUID as a string.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        bool
            ``True`` when the association existed and was removed, ``False``
            if there was no such association.
        """
        from skillmeat.cache.models_enterprise import EnterpriseArtifactTag

        try:
            tag_uuid = uuid.UUID(tag_id)
            artifact_uuid = uuid.UUID(artifact_id)
        except (ValueError, AttributeError):
            return False

        tenant_id = self._get_tenant_id()
        result = self.session.execute(
            delete(EnterpriseArtifactTag).where(
                EnterpriseArtifactTag.tenant_id == tenant_id,
                EnterpriseArtifactTag.tag_id == tag_uuid,
                EnterpriseArtifactTag.artifact_uuid == artifact_uuid,
            )
        )
        removed = result.rowcount > 0
        if removed:
            self.session.flush()
            self._log_operation(
                operation="unassign",
                entity_type="EnterpriseArtifactTag",
                entity_id=None,
                metadata={
                    "tag_id": str(tag_uuid),
                    "artifact_uuid": str(artifact_uuid),
                },
            )
        return removed


# ---------------------------------------------------------------------------
# EnterpriseGroupRepository  (ENT2-3.2)
# ---------------------------------------------------------------------------


class EnterpriseGroupRepository(
    EnterpriseRepositoryBase["EnterpriseGroup"],
):
    """Repository for tenant-scoped CRUD on EnterpriseGroup.

    Implements :class:`~skillmeat.core.interfaces.repositories.IGroupRepository`
    for the enterprise PostgreSQL backend.

    Groups are named, position-ordered buckets within a collection.  All
    queries are automatically scoped to the tenant stored in ``TenantContext``
    via ``_apply_tenant_filter()``.

    Parameters
    ----------
    session:
        An open SQLAlchemy ``Session`` bound to the enterprise database.
        Lifecycle (commit/rollback/close) is managed by the caller.

    Notes
    -----
    The IGroupRepository interface uses ``int`` group IDs for historical
    reasons (local SQLite model uses autoincrement integers).  The enterprise
    model uses ``uuid.UUID`` PKs.  All public methods accept ``int | str``
    IDs, attempt UUID parse first, and raise ``KeyError`` for invalid values.
    """

    def __init__(self, session: Session) -> None:
        from skillmeat.cache.models_enterprise import EnterpriseGroup as _EG

        super().__init__(session, _EG)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _to_dto(
        self,
        group: "EnterpriseGroup",
        artifact_count: int = 0,
    ) -> "GroupDTO":
        """Map an ``EnterpriseGroup`` ORM instance to a :class:`~skillmeat.core.interfaces.dtos.GroupDTO`.

        Parameters
        ----------
        group:
            ORM instance to convert.
        artifact_count:
            Number of artifacts currently in this group.

        Returns
        -------
        GroupDTO
        """
        from skillmeat.core.interfaces.dtos import GroupDTO

        return GroupDTO(
            id=str(group.id),
            name=group.name or "",
            collection_id=str(group.collection_id) if group.collection_id else "",
            description=group.description,
            position=group.position or 0,
            artifact_count=artifact_count,
            tags=[],
            color="slate",
            icon="layers",
            created_at=group.created_at.isoformat() if group.created_at else None,
            updated_at=group.updated_at.isoformat() if group.updated_at else None,
        )

    def _ga_to_dto(
        self,
        ga: "EnterpriseGroupArtifact",
    ) -> "GroupArtifactDTO":
        """Map an ``EnterpriseGroupArtifact`` join row to a :class:`~skillmeat.core.interfaces.dtos.GroupArtifactDTO`.

        Parameters
        ----------
        ga:
            ORM join-table instance to convert.

        Returns
        -------
        GroupArtifactDTO
        """
        from skillmeat.core.interfaces.dtos import GroupArtifactDTO

        return GroupArtifactDTO(
            group_id=str(ga.group_id),
            artifact_uuid=str(ga.artifact_uuid),
            position=ga.position or 0,
            added_at=None,
        )

    def _resolve_group_uuid(self, group_id: "int | str") -> "Optional[uuid.UUID]":
        """Coerce *group_id* to a ``uuid.UUID``, returning ``None`` on failure.

        Accepts integer IDs (silently converted via ``str()`` before UUID
        parse) or string UUIDs.

        Parameters
        ----------
        group_id:
            Raw group identifier from an API path or interface call.

        Returns
        -------
        uuid.UUID or None
        """
        try:
            return uuid.UUID(str(group_id))
        except (ValueError, AttributeError):
            return None

    def _fetch_group(
        self,
        group_uuid: uuid.UUID,
    ) -> "Optional[EnterpriseGroup]":
        """Fetch a tenant-filtered group by UUID.

        Parameters
        ----------
        group_uuid:
            UUID of the group to retrieve.

        Returns
        -------
        EnterpriseGroup or None
        """
        from skillmeat.cache.models_enterprise import EnterpriseGroup

        stmt = self._tenant_select().where(EnterpriseGroup.id == group_uuid)
        return self.session.execute(stmt).scalar_one_or_none()

    # ------------------------------------------------------------------
    # IGroupRepository: get_with_artifacts
    # ------------------------------------------------------------------

    def get_with_artifacts(
        self,
        group_id: int,
        ctx: "Optional[object]" = None,
    ) -> "Optional[GroupDTO]":
        """Return a group by ID, including its artifact membership count.

        Parameters
        ----------
        group_id:
            Group primary key (integer or UUID string accepted).
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        GroupDTO or None
        """
        gid = self._resolve_group_uuid(group_id)
        if gid is None:
            return None
        group = self._fetch_group(gid)
        if group is None:
            return None
        artifact_count = len(group.group_artifacts)
        return self._to_dto(group, artifact_count=artifact_count)

    # ------------------------------------------------------------------
    # IGroupRepository: list
    # ------------------------------------------------------------------

    def list(
        self,
        collection_id: str,
        filters: "Optional[dict]" = None,
        ctx: "Optional[object]" = None,
    ) -> "list[GroupDTO]":
        """Return all groups belonging to a collection, ordered by position.

        Parameters
        ----------
        collection_id:
            Collection UUID as a string.
        filters:
            Optional additional filter map.  Recognised key: ``"name"`` —
            case-insensitive exact match.  Unknown keys are ignored.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        list[GroupDTO]
        """
        from skillmeat.cache.models_enterprise import EnterpriseGroup

        try:
            col_uuid = uuid.UUID(str(collection_id))
        except (ValueError, AttributeError):
            return []

        stmt = (
            self._tenant_select()
            .where(EnterpriseGroup.collection_id == col_uuid)
            .order_by(EnterpriseGroup.position)
        )
        if filters:
            name_filter = filters.get("name")
            if name_filter:
                stmt = stmt.where(EnterpriseGroup.name == name_filter)

        groups = list(self.session.execute(stmt).scalars())
        return [
            self._to_dto(g, artifact_count=len(g.group_artifacts))
            for g in groups
        ]

    # ------------------------------------------------------------------
    # IGroupRepository: create
    # ------------------------------------------------------------------

    def create(
        self,
        name: str,
        collection_id: str,
        description: "Optional[str]" = None,
        position: "Optional[int]" = None,
        ctx: "Optional[object]" = None,
        owner_target: "Optional[object]" = None,
    ) -> "GroupDTO":
        """Create a new group in the given collection.

        If *position* is ``None``, the group is appended after all existing
        groups in the collection (``max(position) + 1``).

        Parameters
        ----------
        name:
            Human-readable group name.
        collection_id:
            Owning collection UUID as a string.
        description:
            Optional free-text description.
        position:
            Explicit display position.  ``None`` = append at the end.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).
        owner_target:
            Optional ownership target (reserved for future use; unused in
            the enterprise backend today).

        Returns
        -------
        GroupDTO
            The newly created group.

        Raises
        ------
        ValueError
            If a group with the same *name* already exists in the collection.
        """
        from sqlalchemy import func
        from skillmeat.cache.models_enterprise import EnterpriseGroup

        try:
            col_uuid = uuid.UUID(str(collection_id))
        except (ValueError, AttributeError) as exc:
            raise ValueError(
                f"Invalid collection_id {collection_id!r}: not a valid UUID."
            ) from exc

        tenant_id = self._get_tenant_id()

        # Guard: name uniqueness within (tenant, collection).
        dup_stmt = (
            self._tenant_select()
            .where(
                EnterpriseGroup.collection_id == col_uuid,
                EnterpriseGroup.name == name,
            )
        )
        if self.session.execute(dup_stmt).scalar_one_or_none() is not None:
            raise ValueError(
                f"A group named {name!r} already exists in collection "
                f"{collection_id!r}."
            )

        if position is None:
            max_pos_result = self.session.execute(
                select(func.max(EnterpriseGroup.position)).where(
                    EnterpriseGroup.tenant_id == tenant_id,
                    EnterpriseGroup.collection_id == col_uuid,
                )
            ).scalar()
            position = 0 if max_pos_result is None else max_pos_result + 1

        group = EnterpriseGroup(
            tenant_id=tenant_id,
            name=name,
            collection_id=col_uuid,
            description=description,
            position=position,
        )
        self.session.add(group)
        self.session.flush()
        self._log_operation(
            operation="create",
            entity_type="EnterpriseGroup",
            entity_id=group.id,
            metadata={"name": name, "collection_id": str(col_uuid)},
        )
        return self._to_dto(group)

    # ------------------------------------------------------------------
    # IGroupRepository: update
    # ------------------------------------------------------------------

    def update(
        self,
        group_id: int,
        updates: "dict",
        ctx: "Optional[object]" = None,
    ) -> "GroupDTO":
        """Apply a partial update to an existing group's metadata.

        Parameters
        ----------
        group_id:
            Group primary key.
        updates:
            Map of field names to new values.  Recognised keys:
            ``"name"``, ``"description"``, ``"position"``.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        GroupDTO
            The updated group DTO.

        Raises
        ------
        KeyError
            If no group with *group_id* exists in the current tenant.
        """
        gid = self._resolve_group_uuid(group_id)
        if gid is None:
            raise KeyError(group_id)
        group = self._fetch_group(gid)
        if group is None:
            raise KeyError(group_id)

        changed: Dict[str, object] = {}
        if "name" in updates:
            group.name = updates["name"]
            changed["name"] = updates["name"]
        if "description" in updates:
            group.description = updates["description"]
            changed["description"] = updates["description"]
        if "position" in updates:
            group.position = updates["position"]
            changed["position"] = updates["position"]

        group.updated_at = datetime.utcnow()
        self.session.flush()
        self._log_operation(
            operation="update",
            entity_type="EnterpriseGroup",
            entity_id=gid,
            metadata=changed or None,
        )
        return self._to_dto(group, artifact_count=len(group.group_artifacts))

    # ------------------------------------------------------------------
    # IGroupRepository: delete
    # ------------------------------------------------------------------

    def delete(
        self,
        group_id: int,
        ctx: "Optional[object]" = None,
    ) -> None:
        """Delete a group and all its artifact membership records.

        The ``ON DELETE CASCADE`` on ``enterprise_group_artifacts.group_id``
        removes membership rows automatically at the database level.

        Parameters
        ----------
        group_id:
            Group primary key.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Raises
        ------
        KeyError
            If no group with *group_id* exists in the current tenant.
        """
        gid = self._resolve_group_uuid(group_id)
        if gid is None:
            raise KeyError(group_id)
        group = self._fetch_group(gid)
        if group is None:
            raise KeyError(group_id)

        self.session.delete(group)
        self.session.flush()
        self._log_operation(
            operation="delete",
            entity_type="EnterpriseGroup",
            entity_id=gid,
        )

    # ------------------------------------------------------------------
    # IGroupRepository: copy_to_collection
    # ------------------------------------------------------------------

    def copy_to_collection(
        self,
        group_id: int,
        target_collection_id: str,
        ctx: "Optional[object]" = None,
    ) -> "GroupDTO":
        """Duplicate a group and its artifact memberships into another collection.

        The new group gets the same name, description, and position as the
        source.  Artifact UUIDs are preserved.

        Parameters
        ----------
        group_id:
            Integer primary key of the source group.
        target_collection_id:
            UUID string of the destination collection.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        GroupDTO
            The newly created group DTO in the target collection.

        Raises
        ------
        KeyError
            If *group_id* does not exist in the current tenant.
        ValueError
            If *target_collection_id* is not a valid UUID.
        """
        from sqlalchemy import func
        from skillmeat.cache.models_enterprise import (
            EnterpriseGroup,
            EnterpriseGroupArtifact,
        )

        gid = self._resolve_group_uuid(group_id)
        if gid is None:
            raise KeyError(group_id)
        source = self._fetch_group(gid)
        if source is None:
            raise KeyError(group_id)

        try:
            target_col_uuid = uuid.UUID(str(target_collection_id))
        except (ValueError, AttributeError) as exc:
            raise ValueError(
                f"Invalid target_collection_id {target_collection_id!r}."
            ) from exc

        tenant_id = self._get_tenant_id()

        # Compute append position in the target collection.
        max_pos_result = self.session.execute(
            select(func.max(EnterpriseGroup.position)).where(
                EnterpriseGroup.tenant_id == tenant_id,
                EnterpriseGroup.collection_id == target_col_uuid,
            )
        ).scalar()
        new_position = 0 if max_pos_result is None else max_pos_result + 1

        new_group = EnterpriseGroup(
            tenant_id=tenant_id,
            name=source.name,
            collection_id=target_col_uuid,
            description=source.description,
            position=new_position,
        )
        self.session.add(new_group)
        self.session.flush()

        # Copy artifact memberships preserving positions.
        source_memberships = list(
            self.session.execute(
                select(EnterpriseGroupArtifact).where(
                    EnterpriseGroupArtifact.group_id == gid,
                    EnterpriseGroupArtifact.tenant_id == tenant_id,
                )
            ).scalars()
        )
        for mem in source_memberships:
            new_mem = EnterpriseGroupArtifact(
                tenant_id=tenant_id,
                group_id=new_group.id,
                artifact_uuid=mem.artifact_uuid,
                position=mem.position,
            )
            self.session.add(new_mem)

        self.session.flush()
        self._log_operation(
            operation="copy_to_collection",
            entity_type="EnterpriseGroup",
            entity_id=new_group.id,
            metadata={
                "source_group_id": str(gid),
                "target_collection_id": str(target_col_uuid),
            },
        )
        return self._to_dto(
            new_group,
            artifact_count=len(source_memberships),
        )

    # ------------------------------------------------------------------
    # IGroupRepository: reorder_groups
    # ------------------------------------------------------------------

    def reorder_groups(
        self,
        collection_id: str,
        ordered_ids: "list[int]",
        ctx: "Optional[object]" = None,
    ) -> None:
        """Bulk-update the display positions of all groups in a collection.

        Parameters
        ----------
        collection_id:
            Collection UUID as a string.
        ordered_ids:
            Complete list of group primary keys in the desired display order.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Raises
        ------
        KeyError
            If *collection_id* does not map to a valid UUID or any group in
            *ordered_ids* is not found in the current tenant.
        ValueError
            If *ordered_ids* does not include all groups in the collection.
        """
        from skillmeat.cache.models_enterprise import EnterpriseGroup

        try:
            col_uuid = uuid.UUID(str(collection_id))
        except (ValueError, AttributeError) as exc:
            raise KeyError(collection_id) from exc

        # Fetch all groups in the collection for this tenant.
        stmt = (
            self._tenant_select()
            .where(EnterpriseGroup.collection_id == col_uuid)
        )
        groups = {g.id: g for g in self.session.execute(stmt).scalars()}

        # Validate completeness.
        ordered_uuids: list[uuid.UUID] = []
        for raw_id in ordered_ids:
            uid = self._resolve_group_uuid(raw_id)
            if uid is None or uid not in groups:
                raise KeyError(raw_id)
            ordered_uuids.append(uid)

        if len(ordered_uuids) != len(groups):
            raise ValueError(
                f"ordered_ids must include all {len(groups)} groups in the "
                f"collection; got {len(ordered_uuids)}."
            )

        for position, gid in enumerate(ordered_uuids):
            groups[gid].position = position
            groups[gid].updated_at = datetime.utcnow()

        self.session.flush()

    # ------------------------------------------------------------------
    # IGroupRepository: add_artifacts
    # ------------------------------------------------------------------

    def add_artifacts(
        self,
        group_id: int,
        artifact_uuids: "list[str]",
        ctx: "Optional[object]" = None,
    ) -> None:
        """Add one or more artifacts to a group (idempotent).

        Artifacts already in the group are silently skipped.  Newly added
        artifacts are appended after existing members.

        Parameters
        ----------
        group_id:
            Group primary key.
        artifact_uuids:
            List of artifact UUID strings to add.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Raises
        ------
        KeyError
            If *group_id* does not exist in the current tenant.
        """
        from sqlalchemy import func
        from skillmeat.cache.models_enterprise import EnterpriseGroupArtifact

        gid = self._resolve_group_uuid(group_id)
        if gid is None:
            raise KeyError(group_id)
        group = self._fetch_group(gid)
        if group is None:
            raise KeyError(group_id)

        tenant_id = self._get_tenant_id()

        # Fetch current max position.
        max_pos_result = self.session.execute(
            select(func.max(EnterpriseGroupArtifact.position)).where(
                EnterpriseGroupArtifact.group_id == gid,
                EnterpriseGroupArtifact.tenant_id == tenant_id,
            )
        ).scalar()
        next_position = 0 if max_pos_result is None else max_pos_result + 1

        # Collect existing artifact UUIDs to deduplicate.
        existing_stmt = select(EnterpriseGroupArtifact.artifact_uuid).where(
            EnterpriseGroupArtifact.group_id == gid,
            EnterpriseGroupArtifact.tenant_id == tenant_id,
        )
        existing_uuids: set[uuid.UUID] = {
            row for row in self.session.execute(existing_stmt).scalars()
        }

        for raw_uuid in artifact_uuids:
            try:
                art_uuid = uuid.UUID(str(raw_uuid))
            except (ValueError, AttributeError):
                continue
            if art_uuid in existing_uuids:
                continue
            mem = EnterpriseGroupArtifact(
                tenant_id=tenant_id,
                group_id=gid,
                artifact_uuid=art_uuid,
                position=next_position,
            )
            self.session.add(mem)
            existing_uuids.add(art_uuid)
            next_position += 1

        self.session.flush()

    # ------------------------------------------------------------------
    # IGroupRepository: remove_artifact
    # ------------------------------------------------------------------

    def remove_artifact(
        self,
        group_id: int,
        artifact_uuid: str,
        ctx: "Optional[object]" = None,
    ) -> None:
        """Remove a single artifact from a group.

        Parameters
        ----------
        group_id:
            Group primary key.
        artifact_uuid:
            Artifact UUID string to remove.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Raises
        ------
        KeyError
            If *group_id* does not exist or *artifact_uuid* is not a member.
        """
        from skillmeat.cache.models_enterprise import EnterpriseGroupArtifact

        gid = self._resolve_group_uuid(group_id)
        if gid is None:
            raise KeyError(group_id)
        group = self._fetch_group(gid)
        if group is None:
            raise KeyError(group_id)

        try:
            art_uuid = uuid.UUID(str(artifact_uuid))
        except (ValueError, AttributeError) as exc:
            raise KeyError(artifact_uuid) from exc

        tenant_id = self._get_tenant_id()
        result = self.session.execute(
            delete(EnterpriseGroupArtifact).where(
                EnterpriseGroupArtifact.group_id == gid,
                EnterpriseGroupArtifact.artifact_uuid == art_uuid,
                EnterpriseGroupArtifact.tenant_id == tenant_id,
            )
        )
        if result.rowcount == 0:
            raise KeyError(artifact_uuid)
        self.session.flush()

    # ------------------------------------------------------------------
    # IGroupRepository: update_artifact_position
    # ------------------------------------------------------------------

    def update_artifact_position(
        self,
        group_id: int,
        artifact_uuid: str,
        position: int,
        ctx: "Optional[object]" = None,
    ) -> None:
        """Update the display position of a single artifact within a group.

        Parameters
        ----------
        group_id:
            Group primary key.
        artifact_uuid:
            Artifact UUID string whose position to update.
        position:
            New zero-based display position.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Raises
        ------
        KeyError
            If *group_id* does not exist or *artifact_uuid* is not a member.
        """
        from skillmeat.cache.models_enterprise import EnterpriseGroupArtifact

        gid = self._resolve_group_uuid(group_id)
        if gid is None:
            raise KeyError(group_id)
        group = self._fetch_group(gid)
        if group is None:
            raise KeyError(group_id)

        try:
            art_uuid = uuid.UUID(str(artifact_uuid))
        except (ValueError, AttributeError) as exc:
            raise KeyError(artifact_uuid) from exc

        tenant_id = self._get_tenant_id()
        stmt = select(EnterpriseGroupArtifact).where(
            EnterpriseGroupArtifact.group_id == gid,
            EnterpriseGroupArtifact.artifact_uuid == art_uuid,
            EnterpriseGroupArtifact.tenant_id == tenant_id,
        )
        mem = self.session.execute(stmt).scalar_one_or_none()
        if mem is None:
            raise KeyError(artifact_uuid)

        mem.position = position
        self.session.flush()

    # ------------------------------------------------------------------
    # IGroupRepository: reorder_artifacts
    # ------------------------------------------------------------------

    def reorder_artifacts(
        self,
        group_id: int,
        ordered_uuids: "list[str]",
        ctx: "Optional[object]" = None,
    ) -> None:
        """Bulk-update the display positions of all artifacts in a group.

        Parameters
        ----------
        group_id:
            Group primary key.
        ordered_uuids:
            Complete list of artifact UUID strings in the desired display
            order.  Must include all current members.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Raises
        ------
        KeyError
            If *group_id* does not exist in the current tenant.
        ValueError
            If *ordered_uuids* does not cover all current members.
        """
        from skillmeat.cache.models_enterprise import EnterpriseGroupArtifact

        gid = self._resolve_group_uuid(group_id)
        if gid is None:
            raise KeyError(group_id)
        group = self._fetch_group(gid)
        if group is None:
            raise KeyError(group_id)

        tenant_id = self._get_tenant_id()
        memberships_stmt = select(EnterpriseGroupArtifact).where(
            EnterpriseGroupArtifact.group_id == gid,
            EnterpriseGroupArtifact.tenant_id == tenant_id,
        )
        memberships = {
            m.artifact_uuid: m
            for m in self.session.execute(memberships_stmt).scalars()
        }

        parsed_uuids: list[uuid.UUID] = []
        for raw in ordered_uuids:
            try:
                parsed_uuids.append(uuid.UUID(str(raw)))
            except (ValueError, AttributeError):
                continue

        if len(parsed_uuids) != len(memberships):
            raise ValueError(
                f"ordered_uuids must include all {len(memberships)} current "
                f"members; got {len(parsed_uuids)}."
            )

        for position, art_uuid in enumerate(parsed_uuids):
            if art_uuid not in memberships:
                raise ValueError(
                    f"Artifact {art_uuid!s} is not a member of group {group_id!r}."
                )
            memberships[art_uuid].position = position

        self.session.flush()

    # ------------------------------------------------------------------
    # IGroupRepository: list_group_artifacts
    # ------------------------------------------------------------------

    def list_group_artifacts(
        self,
        group_id: str,
        ctx: "Optional[object]" = None,
    ) -> "list[GroupArtifactDTO]":
        """Return the ordered artifact membership records for a group.

        Parameters
        ----------
        group_id:
            Group primary key (string or integer).
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        list[GroupArtifactDTO]
            Membership records ordered by ``position`` ascending.  Returns an
            empty list when the group does not exist or has no members.
        """
        from skillmeat.cache.models_enterprise import EnterpriseGroupArtifact

        gid = self._resolve_group_uuid(group_id)
        if gid is None:
            return []

        tenant_id = self._get_tenant_id()
        stmt = (
            select(EnterpriseGroupArtifact)
            .where(
                EnterpriseGroupArtifact.group_id == gid,
                EnterpriseGroupArtifact.tenant_id == tenant_id,
            )
            .order_by(EnterpriseGroupArtifact.position)
        )
        members = list(self.session.execute(stmt).scalars())
        return [self._ga_to_dto(m) for m in members]

    # ------------------------------------------------------------------
    # IGroupRepository: add_artifacts_at_position
    # ------------------------------------------------------------------

    def add_artifacts_at_position(
        self,
        group_id: str,
        artifact_uuids: "list[str]",
        position: int,
        ctx: "Optional[object]" = None,
    ) -> None:
        """Insert artifacts at a specific position within a group.

        Existing artifacts at or after *position* are shifted down by the
        count of new insertions.  Artifacts already in the group are silently
        skipped (deduplicated).

        Parameters
        ----------
        group_id:
            Group primary key string.
        artifact_uuids:
            Ordered list of artifact UUID strings to insert.
        position:
            Zero-based target position for the first inserted artifact.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Raises
        ------
        KeyError
            If *group_id* does not exist in the current tenant.
        RuntimeError
            On unexpected database errors.
        """
        from skillmeat.cache.models_enterprise import EnterpriseGroupArtifact

        gid = self._resolve_group_uuid(group_id)
        if gid is None:
            raise KeyError(group_id)
        group = self._fetch_group(gid)
        if group is None:
            raise KeyError(group_id)

        tenant_id = self._get_tenant_id()

        # Deduplicate: skip UUIDs already in the group.
        existing_stmt = select(EnterpriseGroupArtifact.artifact_uuid).where(
            EnterpriseGroupArtifact.group_id == gid,
            EnterpriseGroupArtifact.tenant_id == tenant_id,
        )
        existing_uuids: set[uuid.UUID] = {
            row for row in self.session.execute(existing_stmt).scalars()
        }

        new_uuids: list[uuid.UUID] = []
        for raw in artifact_uuids:
            try:
                art_uuid = uuid.UUID(str(raw))
            except (ValueError, AttributeError):
                continue
            if art_uuid not in existing_uuids:
                new_uuids.append(art_uuid)

        if not new_uuids:
            return

        # Shift existing members at or after *position* down by len(new_uuids).
        shift = len(new_uuids)
        shift_stmt = select(EnterpriseGroupArtifact).where(
            EnterpriseGroupArtifact.group_id == gid,
            EnterpriseGroupArtifact.tenant_id == tenant_id,
            EnterpriseGroupArtifact.position >= position,
        )
        for mem in self.session.execute(shift_stmt).scalars():
            if mem.position is not None:
                mem.position = mem.position + shift

        # Insert new membership rows starting at *position*.
        for offset, art_uuid in enumerate(new_uuids):
            new_mem = EnterpriseGroupArtifact(
                tenant_id=tenant_id,
                group_id=gid,
                artifact_uuid=art_uuid,
                position=position + offset,
            )
            self.session.add(new_mem)

        self.session.flush()


# =============================================================================
# EnterpriseSettingsRepository  (ENT2-3.3)
# =============================================================================


class EnterpriseSettingsRepository(
    EnterpriseRepositoryBase["EnterpriseSettings"],
):
    """Repository for tenant-scoped reads and writes on EnterpriseSettings.

    Implements :class:`~skillmeat.core.interfaces.repositories.ISettingsRepository`
    for the enterprise PostgreSQL backend.

    The ``EnterpriseSettings`` table has a ``UNIQUE (tenant_id)`` constraint —
    exactly one settings row per tenant.  :meth:`update` uses an ORM
    check-then-insert/update pattern (no raw ``INSERT ON CONFLICT``) so it
    works portably across SQLAlchemy dialects in unit tests.

    Parameters
    ----------
    session:
        An open SQLAlchemy ``Session`` bound to the enterprise database.
        Lifecycle (commit/rollback/close) is managed by the caller.

    Notes
    -----
    The interface defines ``github_token``, ``collection_path``,
    ``default_scope``, ``edition``, and ``indexing_mode`` as first-class
    fields; additional keys in the ``updates`` dict are stored in the JSONB
    ``extra`` column.
    """

    def __init__(self, session: Session) -> None:
        from skillmeat.cache.models_enterprise import EnterpriseSettings as _ES

        super().__init__(session, _ES)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    _KNOWN_FIELDS = frozenset(
        {"github_token", "collection_path", "default_scope", "edition", "indexing_mode"}
    )

    def _to_dto(self, row: "EnterpriseSettings") -> "SettingsDTO":
        """Map an ``EnterpriseSettings`` ORM instance to a :class:`~skillmeat.core.interfaces.dtos.SettingsDTO`.

        Parameters
        ----------
        row:
            ORM instance to convert.

        Returns
        -------
        SettingsDTO
        """
        from skillmeat.core.interfaces.dtos import SettingsDTO

        return SettingsDTO(
            github_token=row.github_token,
            collection_path=row.collection_path,
            default_scope=row.default_scope or "user",
            edition=row.edition or "enterprise",
            indexing_mode=row.indexing_mode or "opt_in",
            extra=dict(row.extra) if row.extra else {},
        )

    def _fetch_row(self) -> "Optional[EnterpriseSettings]":
        """Fetch the single settings row for the current tenant.

        Returns
        -------
        EnterpriseSettings or None
        """
        from skillmeat.cache.models_enterprise import EnterpriseSettings

        stmt = self._tenant_select()
        return self.session.execute(stmt).scalar_one_or_none()

    # ------------------------------------------------------------------
    # ISettingsRepository: get
    # ------------------------------------------------------------------

    def get(
        self,
        ctx: "Optional[object]" = None,
    ) -> "SettingsDTO":
        """Return the current application settings snapshot for this tenant.

        If no settings row exists yet, a default :class:`~skillmeat.core.interfaces.dtos.SettingsDTO`
        is returned without writing to the database.

        Parameters
        ----------
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        SettingsDTO
        """
        from skillmeat.core.interfaces.dtos import SettingsDTO

        row = self._fetch_row()
        if row is None:
            return SettingsDTO(edition="enterprise")
        return self._to_dto(row)

    # ------------------------------------------------------------------
    # ISettingsRepository: update
    # ------------------------------------------------------------------

    def update(
        self,
        updates: "dict",
        ctx: "Optional[object]" = None,
    ) -> "SettingsDTO":
        """Apply a partial update to the application settings for this tenant.

        Only provided keys are changed.  If no settings row exists yet, a new
        one is created (upsert semantics via ORM check-then-insert/update).
        Unknown keys are stored in the ``extra`` JSONB column.

        Parameters
        ----------
        updates:
            Map of setting keys to new values.  Recognised first-class keys:
            ``github_token``, ``collection_path``, ``default_scope``,
            ``edition``, ``indexing_mode``.  All other keys go into ``extra``.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        SettingsDTO
            The updated settings snapshot.
        """
        from skillmeat.cache.models_enterprise import EnterpriseSettings

        tenant_id = self._get_tenant_id()
        row = self._fetch_row()

        if row is None:
            # No row yet — create one with defaults then apply updates.
            row = EnterpriseSettings(
                tenant_id=tenant_id,
                extra={},
            )
            self.session.add(row)

        # Apply first-class field updates.
        for field_name in self._KNOWN_FIELDS:
            if field_name in updates:
                setattr(row, field_name, updates[field_name])

        # Remaining keys go into the extra JSONB bag.
        extra_updates = {k: v for k, v in updates.items() if k not in self._KNOWN_FIELDS}
        if extra_updates:
            merged_extra = dict(row.extra or {})
            merged_extra.update(extra_updates)
            row.extra = merged_extra

        row.updated_at = datetime.utcnow()
        self.session.flush()
        self._log_operation(
            operation="update",
            entity_type="EnterpriseSettings",
            entity_id=row.id,
            metadata={k: str(v)[:80] for k, v in updates.items()},
        )
        return self._to_dto(row)

    # ------------------------------------------------------------------
    # ISettingsRepository: validate_github_token
    # ------------------------------------------------------------------

    def validate_github_token(
        self,
        token: str,
        ctx: "Optional[object]" = None,
    ) -> bool:
        """Validate a GitHub Personal Access Token against the API.

        Delegates to the centralised :func:`~skillmeat.core.github_client.get_github_client`
        singleton.  Returns ``False`` on any error rather than raising.

        Parameters
        ----------
        token:
            Raw GitHub PAT string.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        bool
            ``True`` if the token authenticates successfully, ``False``
            otherwise.
        """
        try:
            from skillmeat.core.github_client import GitHubClient

            client = GitHubClient(token=token)
            rate_limit = client.get_rate_limit()
            return rate_limit is not None
        except Exception:
            return False

    # ------------------------------------------------------------------
    # ISettingsRepository: list_entity_type_configs
    # ------------------------------------------------------------------

    def list_entity_type_configs(
        self,
        ctx: "Optional[object]" = None,
    ) -> "list[EntityTypeConfigDTO]":
        """Return all registered entity type configurations for this tenant.

        Parameters
        ----------
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        list[EntityTypeConfigDTO]
            Both system-defined (``is_system=True``) and user-created entries,
            ordered by ``entity_type``.
        """
        from skillmeat.cache.models_enterprise import EnterpriseEntityTypeConfig
        from skillmeat.core.interfaces.dtos import EntityTypeConfigDTO

        stmt = (
            self._apply_tenant_filter(select(EnterpriseEntityTypeConfig))
            .order_by(EnterpriseEntityTypeConfig.entity_type)
        )
        rows = list(self.session.execute(stmt).scalars())
        return [
            EntityTypeConfigDTO(
                id=str(row.id),
                entity_type=row.entity_type,
                display_name=row.display_name or row.entity_type,
                description=row.description,
                icon=row.icon,
                color=row.color,
                is_system=bool(row.is_system),
            )
            for row in rows
        ]

    # ------------------------------------------------------------------
    # ISettingsRepository: create_entity_type_config
    # ------------------------------------------------------------------

    def create_entity_type_config(
        self,
        entity_type: str,
        display_name: str,
        description: "Optional[str]" = None,
        icon: "Optional[str]" = None,
        color: "Optional[str]" = None,
        ctx: "Optional[object]" = None,
    ) -> "EntityTypeConfigDTO":
        """Create a new user-defined entity type configuration.

        Parameters
        ----------
        entity_type:
            Machine-readable entity type key, e.g. ``"workflow"``.  Must be
            unique within the tenant.
        display_name:
            Human-readable display name.
        description:
            Optional description text.
        icon:
            Optional icon identifier or URL.
        color:
            Optional hex color code, e.g. ``"#FF5733"``.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        EntityTypeConfigDTO
            The newly created config.

        Raises
        ------
        ValueError
            If an entity type config with the same *entity_type* already exists
            in this tenant.
        """
        from skillmeat.cache.models_enterprise import EnterpriseEntityTypeConfig
        from skillmeat.core.interfaces.dtos import EntityTypeConfigDTO

        tenant_id = self._get_tenant_id()

        # Guard: uniqueness check on (tenant_id, entity_type).
        dup_stmt = self._apply_tenant_filter(
            select(EnterpriseEntityTypeConfig).where(
                EnterpriseEntityTypeConfig.entity_type == entity_type
            )
        )
        if self.session.execute(dup_stmt).scalar_one_or_none() is not None:
            raise ValueError(
                f"An entity type config for {entity_type!r} already exists in this tenant."
            )

        row = EnterpriseEntityTypeConfig(
            tenant_id=tenant_id,
            entity_type=entity_type,
            display_name=display_name,
            description=description,
            icon=icon,
            color=color,
            is_system=False,
        )
        self.session.add(row)
        self.session.flush()
        self._log_operation(
            operation="create",
            entity_type="EnterpriseEntityTypeConfig",
            entity_id=row.id,
            metadata={"entity_type": entity_type},
        )
        return EntityTypeConfigDTO(
            id=str(row.id),
            entity_type=row.entity_type,
            display_name=row.display_name or row.entity_type,
            description=row.description,
            icon=row.icon,
            color=row.color,
            is_system=False,
        )

    # ------------------------------------------------------------------
    # ISettingsRepository: update_entity_type_config
    # ------------------------------------------------------------------

    def update_entity_type_config(
        self,
        config_id: str,
        updates: "dict",
        ctx: "Optional[object]" = None,
    ) -> "EntityTypeConfigDTO":
        """Apply a partial update to an existing entity type configuration.

        Parameters
        ----------
        config_id:
            UUID string of the config record to update.
        updates:
            Map of field names to new values.  Recognised keys:
            ``display_name``, ``description``, ``icon``, ``color``.
            ``entity_type`` and ``is_system`` are immutable.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        EntityTypeConfigDTO
            The updated config.

        Raises
        ------
        KeyError
            If no config with *config_id* exists in this tenant.
        ValueError
            If the update attempts to mutate ``entity_type`` or ``is_system``.
        """
        from skillmeat.cache.models_enterprise import EnterpriseEntityTypeConfig
        from skillmeat.core.interfaces.dtos import EntityTypeConfigDTO

        if "entity_type" in updates or "is_system" in updates:
            raise ValueError(
                "The 'entity_type' and 'is_system' fields are immutable after creation."
            )

        try:
            cfg_uuid = uuid.UUID(str(config_id))
        except (ValueError, AttributeError) as exc:
            raise KeyError(config_id) from exc

        stmt = self._apply_tenant_filter(
            select(EnterpriseEntityTypeConfig).where(
                EnterpriseEntityTypeConfig.id == cfg_uuid
            )
        )
        row = self.session.execute(stmt).scalar_one_or_none()
        if row is None:
            raise KeyError(config_id)

        for field_name in ("display_name", "description", "icon", "color"):
            if field_name in updates:
                setattr(row, field_name, updates[field_name])

        self.session.flush()
        self._log_operation(
            operation="update",
            entity_type="EnterpriseEntityTypeConfig",
            entity_id=cfg_uuid,
            metadata=updates or None,
        )
        return EntityTypeConfigDTO(
            id=str(row.id),
            entity_type=row.entity_type,
            display_name=row.display_name or row.entity_type,
            description=row.description,
            icon=row.icon,
            color=row.color,
            is_system=bool(row.is_system),
        )

    # ------------------------------------------------------------------
    # ISettingsRepository: delete_entity_type_config
    # ------------------------------------------------------------------

    def delete_entity_type_config(
        self,
        config_id: str,
        ctx: "Optional[object]" = None,
    ) -> None:
        """Delete a user-defined entity type configuration.

        System-defined configs (``is_system=True``) cannot be deleted.

        Parameters
        ----------
        config_id:
            UUID string of the config record to delete.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Raises
        ------
        KeyError
            If no config with *config_id* exists in this tenant.
        ValueError
            If the config is system-defined.
        """
        from skillmeat.cache.models_enterprise import EnterpriseEntityTypeConfig

        try:
            cfg_uuid = uuid.UUID(str(config_id))
        except (ValueError, AttributeError) as exc:
            raise KeyError(config_id) from exc

        stmt = self._apply_tenant_filter(
            select(EnterpriseEntityTypeConfig).where(
                EnterpriseEntityTypeConfig.id == cfg_uuid
            )
        )
        row = self.session.execute(stmt).scalar_one_or_none()
        if row is None:
            raise KeyError(config_id)
        if row.is_system:
            raise ValueError(
                f"Cannot delete system-defined entity type config {config_id!r}."
            )

        self.session.delete(row)
        self.session.flush()
        self._log_operation(
            operation="delete",
            entity_type="EnterpriseEntityTypeConfig",
            entity_id=cfg_uuid,
        )

    # ------------------------------------------------------------------
    # ISettingsRepository: list_categories
    # ------------------------------------------------------------------

    def list_categories(
        self,
        entity_type: "Optional[str]" = None,
        platform: "Optional[str]" = None,
        ctx: "Optional[object]" = None,
    ) -> "list[CategoryDTO]":
        """Return all categories for this tenant, optionally filtered.

        Parameters
        ----------
        entity_type:
            When provided, return only categories scoped to this entity type.
        platform:
            When provided, return only categories scoped to this platform.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        list[CategoryDTO]
            Categories ordered by ``sort_order`` ascending.
        """
        from skillmeat.cache.models_enterprise import EnterpriseEntityCategory
        from skillmeat.core.interfaces.dtos import CategoryDTO

        stmt = self._apply_tenant_filter(
            select(EnterpriseEntityCategory)
        ).order_by(EnterpriseEntityCategory.sort_order)

        if entity_type is not None:
            stmt = stmt.where(EnterpriseEntityCategory.entity_type == entity_type)
        if platform is not None:
            stmt = stmt.where(EnterpriseEntityCategory.platform == platform)

        rows = list(self.session.execute(stmt).scalars())
        return [
            CategoryDTO(
                id=str(row.id),
                name=row.name,
                slug=row.slug or "",
                entity_type=row.entity_type,
                description=row.description,
                color=row.color,
                platform=row.platform,
                sort_order=row.sort_order or 0,
            )
            for row in rows
        ]

    # ------------------------------------------------------------------
    # ISettingsRepository: create_category
    # ------------------------------------------------------------------

    def create_category(
        self,
        name: str,
        slug: "Optional[str]" = None,
        entity_type: "Optional[str]" = None,
        description: "Optional[str]" = None,
        color: "Optional[str]" = None,
        platform: "Optional[str]" = None,
        sort_order: "Optional[int]" = None,
        ctx: "Optional[object]" = None,
    ) -> "CategoryDTO":
        """Create a new category for this tenant.

        Parameters
        ----------
        name:
            Human-readable category name.
        slug:
            Optional URL-safe slug; auto-generated from *name* when omitted.
        entity_type:
            Optional entity type this category applies to.
        description:
            Optional description text.
        color:
            Optional hex color code for UI display.
        platform:
            Optional platform scope filter.
        sort_order:
            Optional explicit display order; defaults to 0.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        CategoryDTO
            The newly created category.

        Raises
        ------
        ValueError
            If a category with the same resolved slug already exists in this
            tenant.
        """
        import re

        from skillmeat.cache.models_enterprise import EnterpriseEntityCategory
        from skillmeat.core.interfaces.dtos import CategoryDTO

        tenant_id = self._get_tenant_id()

        if slug is None:
            slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

        # Guard: uniqueness check on (tenant_id, slug).
        dup_stmt = self._apply_tenant_filter(
            select(EnterpriseEntityCategory).where(
                EnterpriseEntityCategory.slug == slug
            )
        )
        if self.session.execute(dup_stmt).scalar_one_or_none() is not None:
            raise ValueError(
                f"A category with slug {slug!r} already exists in this tenant."
            )

        row = EnterpriseEntityCategory(
            tenant_id=tenant_id,
            name=name,
            slug=slug,
            entity_type=entity_type,
            description=description,
            color=color,
            platform=platform,
            sort_order=sort_order or 0,
        )
        self.session.add(row)
        self.session.flush()
        self._log_operation(
            operation="create",
            entity_type="EnterpriseEntityCategory",
            entity_id=row.id,
            metadata={"name": name, "slug": slug},
        )
        return CategoryDTO(
            id=str(row.id),
            name=row.name,
            slug=row.slug or "",
            entity_type=row.entity_type,
            description=row.description,
            color=row.color,
            platform=row.platform,
            sort_order=row.sort_order or 0,
        )

    # ------------------------------------------------------------------
    # ISettingsRepository: update_category
    # ------------------------------------------------------------------

    def update_category(
        self,
        category_id: int,
        updates: "dict",
        ctx: "Optional[object]" = None,
    ) -> "CategoryDTO":
        """Apply a partial update to an existing category.

        Parameters
        ----------
        category_id:
            UUID or integer primary key of the category to update.
        updates:
            Map of field names to new values.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        CategoryDTO
            The updated category.

        Raises
        ------
        KeyError
            If no category with *category_id* exists in this tenant.
        ValueError
            If the requested new slug is already taken.
        """
        import re

        from skillmeat.cache.models_enterprise import EnterpriseEntityCategory
        from skillmeat.core.interfaces.dtos import CategoryDTO

        try:
            cat_uuid = uuid.UUID(str(category_id))
        except (ValueError, AttributeError) as exc:
            raise KeyError(category_id) from exc

        stmt = self._apply_tenant_filter(
            select(EnterpriseEntityCategory).where(
                EnterpriseEntityCategory.id == cat_uuid
            )
        )
        row = self.session.execute(stmt).scalar_one_or_none()
        if row is None:
            raise KeyError(category_id)

        if "slug" in updates:
            new_slug = updates["slug"]
            dup_stmt = self._apply_tenant_filter(
                select(EnterpriseEntityCategory).where(
                    EnterpriseEntityCategory.slug == new_slug,
                    EnterpriseEntityCategory.id != cat_uuid,
                )
            )
            if self.session.execute(dup_stmt).scalar_one_or_none() is not None:
                raise ValueError(
                    f"Slug {new_slug!r} is already used by another category in this tenant."
                )

        for field_name in ("name", "slug", "entity_type", "description", "color", "platform", "sort_order"):
            if field_name in updates:
                setattr(row, field_name, updates[field_name])

        self.session.flush()
        self._log_operation(
            operation="update",
            entity_type="EnterpriseEntityCategory",
            entity_id=cat_uuid,
            metadata=updates or None,
        )
        return CategoryDTO(
            id=str(row.id),
            name=row.name,
            slug=row.slug or "",
            entity_type=row.entity_type,
            description=row.description,
            color=row.color,
            platform=row.platform,
            sort_order=row.sort_order or 0,
        )

    # ------------------------------------------------------------------
    # ISettingsRepository: delete_category
    # ------------------------------------------------------------------

    def delete_category(
        self,
        category_id: int,
        ctx: "Optional[object]" = None,
    ) -> None:
        """Delete a category by primary key.

        Parameters
        ----------
        category_id:
            UUID or integer primary key of the category to delete.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Raises
        ------
        KeyError
            If no category with *category_id* exists in this tenant.
        ValueError
            If the category has artifact associations.
        """
        from skillmeat.cache.models_enterprise import EnterpriseEntityCategory

        try:
            cat_uuid = uuid.UUID(str(category_id))
        except (ValueError, AttributeError) as exc:
            raise KeyError(category_id) from exc

        stmt = self._apply_tenant_filter(
            select(EnterpriseEntityCategory).where(
                EnterpriseEntityCategory.id == cat_uuid
            )
        )
        row = self.session.execute(stmt).scalar_one_or_none()
        if row is None:
            raise KeyError(category_id)

        if row.entity_category_associations:
            raise ValueError(
                f"Category {category_id!r} has existing associations and cannot be deleted."
            )

        self.session.delete(row)
        self.session.flush()
        self._log_operation(
            operation="delete",
            entity_type="EnterpriseEntityCategory",
            entity_id=cat_uuid,
        )


# =============================================================================
# EnterpriseContextEntityRepository  (ENT2-3.4)
# =============================================================================


class EnterpriseContextEntityRepository(
    EnterpriseRepositoryBase["EnterpriseContextEntity"],
):
    """Repository for tenant-scoped CRUD on EnterpriseContextEntity.

    Implements :class:`~skillmeat.core.interfaces.repositories.IContextEntityRepository`
    for the enterprise PostgreSQL backend.

    Context entities are special artifacts (CLAUDE.md, spec files, rule files,
    context files, progress templates) stored in ``enterprise_context_entities``.
    All queries are automatically scoped to the tenant stored in ``TenantContext``
    via ``_apply_tenant_filter()``.

    Parameters
    ----------
    session:
        An open SQLAlchemy ``Session`` bound to the enterprise database.
        Lifecycle (commit/rollback/close) is managed by the caller.

    Notes
    -----
    The ``artifact_id`` FK is nullable — context entities may exist
    independently of any artifact row.  The ``target_platforms`` and
    ``category_associations`` fields are JSONB/relational respectively; JSONB
    filters use standard equality (not ``@>``), so they are safe in SQLite-
    backed unit tests.
    """

    def __init__(self, session: Session) -> None:
        from skillmeat.cache.models_enterprise import EnterpriseContextEntity as _ECE

        super().__init__(session, _ECE)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_content_hash(content: "Optional[str]") -> "Optional[str]":
        """Return the SHA-256 hex digest of *content*, or ``None`` when empty.

        Parameters
        ----------
        content:
            Raw string content to hash.

        Returns
        -------
        str or None
        """
        if not content:
            return None
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _to_dto(self, row: "EnterpriseContextEntity") -> "ContextEntityDTO":
        """Map an ``EnterpriseContextEntity`` ORM instance to a :class:`~skillmeat.core.interfaces.dtos.ContextEntityDTO`.

        Parameters
        ----------
        row:
            ORM instance to convert.

        Returns
        -------
        ContextEntityDTO
        """
        from skillmeat.core.interfaces.dtos import ContextEntityDTO

        category_ids: List[int] = []
        if row.category_associations:
            for assoc in row.category_associations:
                try:
                    category_ids.append(int(str(assoc.category_id)))
                except (TypeError, ValueError):
                    pass

        return ContextEntityDTO(
            id=str(row.id),
            name=row.name,
            entity_type=row.entity_type,
            content=row.content or "",
            path_pattern=row.path_pattern or "",
            description=row.description,
            category=row.category,
            auto_load=bool(row.auto_load),
            version=row.version,
            target_platforms=list(row.target_platforms or []),
            content_hash=self._compute_content_hash(row.content),
            category_ids=category_ids,
            created_at=row.created_at.isoformat() if row.created_at else None,
            updated_at=row.updated_at.isoformat() if row.updated_at else None,
        )

    def _fetch_entity(
        self,
        entity_uuid: uuid.UUID,
    ) -> "Optional[EnterpriseContextEntity]":
        """Fetch a tenant-filtered context entity by UUID.

        Parameters
        ----------
        entity_uuid:
            UUID of the entity to retrieve.

        Returns
        -------
        EnterpriseContextEntity or None
        """
        from skillmeat.cache.models_enterprise import EnterpriseContextEntity

        stmt = self._tenant_select().where(EnterpriseContextEntity.id == entity_uuid)
        return self.session.execute(stmt).scalar_one_or_none()

    # ------------------------------------------------------------------
    # IContextEntityRepository: list
    # ------------------------------------------------------------------

    def list(
        self,
        filters: "Optional[dict]" = None,
        limit: int = 20,
        after: "Optional[str]" = None,
        ctx: "Optional[object]" = None,
    ) -> "list[ContextEntityDTO]":
        """Return a page of context entities matching optional filter criteria.

        Supported filter keys: ``entity_type``, ``category``, ``auto_load``,
        ``search`` (case-insensitive prefix on ``name``).

        Parameters
        ----------
        filters:
            Optional key/value filter map.
        limit:
            Maximum number of records to return (1-100).
        after:
            Opaque cursor (base64-encoded UUID string) for keyset pagination.
            Pass the ``id`` of the last seen item.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        list[ContextEntityDTO]
        """
        import base64

        from sqlalchemy import func
        from skillmeat.cache.models_enterprise import EnterpriseContextEntity

        stmt = self._tenant_select().order_by(EnterpriseContextEntity.created_at)

        if filters:
            entity_type = filters.get("entity_type")
            if entity_type is not None:
                stmt = stmt.where(EnterpriseContextEntity.entity_type == entity_type)

            category = filters.get("category")
            if category is not None:
                stmt = stmt.where(EnterpriseContextEntity.category == category)

            auto_load = filters.get("auto_load")
            if auto_load is not None:
                stmt = stmt.where(EnterpriseContextEntity.auto_load.is_(bool(auto_load)))

            search = filters.get("search")
            if search:
                stmt = stmt.where(
                    func.lower(EnterpriseContextEntity.name).like(
                        f"{search.lower()}%"
                    )
                )

        # Keyset pagination: skip rows whose id <= after cursor.
        if after:
            try:
                cursor_id = uuid.UUID(base64.b64decode(after.encode()).decode())
                stmt = stmt.where(EnterpriseContextEntity.id > cursor_id)
            except Exception:
                pass  # Ignore invalid cursor; return from beginning.

        limit = max(1, min(limit, 100))
        stmt = stmt.limit(limit)

        rows = list(self.session.execute(stmt).scalars())
        return [self._to_dto(row) for row in rows]

    # ------------------------------------------------------------------
    # IContextEntityRepository: get
    # ------------------------------------------------------------------

    def get(
        self,
        entity_id: str,
        ctx: "Optional[object]" = None,
    ) -> "Optional[ContextEntityDTO]":
        """Return a context entity by its identifier.

        Parameters
        ----------
        entity_id:
            Entity UUID as a string.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        ContextEntityDTO or None
        """
        try:
            entity_uuid = uuid.UUID(str(entity_id))
        except (ValueError, AttributeError):
            return None

        row = self._fetch_entity(entity_uuid)
        if row is None:
            return None
        return self._to_dto(row)

    # ------------------------------------------------------------------
    # IContextEntityRepository: create
    # ------------------------------------------------------------------

    def create(
        self,
        name: str,
        entity_type: str,
        content: str,
        path_pattern: str,
        description: "Optional[str]" = None,
        category: "Optional[str]" = None,
        auto_load: bool = False,
        version: "Optional[str]" = None,
        target_platforms: "Optional[list[str]]" = None,
        category_ids: "Optional[list[int]]" = None,
        ctx: "Optional[object]" = None,
    ) -> "ContextEntityDTO":
        """Persist a new context entity and return the stored representation.

        Parameters
        ----------
        name:
            Human-readable entity name.
        entity_type:
            Entity type key, e.g. ``"context_file"``, ``"rule_file"``.
        content:
            Assembled markdown content.
        path_pattern:
            Target deployment path (must start with ``".claude/"`` or a
            supported prefix).
        description:
            Optional description.
        category:
            Optional category label string.
        auto_load:
            Whether to auto-load on platform startup.
        version:
            Optional version string.
        target_platforms:
            Optional list of platform identifiers.
        category_ids:
            Ordered list of category IDs to associate.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        ContextEntityDTO
            The persisted entity.

        Raises
        ------
        ValueError
            If *path_pattern* is blank.
        """
        from skillmeat.cache.models_enterprise import (
            EnterpriseContextEntity,
            EnterpriseEntityCategoryAssociation,
        )

        if not path_pattern:
            raise ValueError("path_pattern must not be empty.")

        tenant_id = self._get_tenant_id()

        row = EnterpriseContextEntity(
            tenant_id=tenant_id,
            name=name,
            entity_type=entity_type,
            content=content,
            path_pattern=path_pattern,
            description=description,
            category=category,
            auto_load=auto_load,
            version=version,
            target_platforms=target_platforms or [],
        )
        self.session.add(row)
        self.session.flush()  # Populate row.id before associations.

        if category_ids:
            for position, cat_id in enumerate(category_ids):
                try:
                    cat_uuid = uuid.UUID(str(cat_id))
                except (ValueError, AttributeError):
                    continue
                assoc = EnterpriseEntityCategoryAssociation(
                    tenant_id=tenant_id,
                    entity_id=row.id,
                    category_id=cat_uuid,
                    position=position,
                )
                self.session.add(assoc)
            self.session.flush()

        self._log_operation(
            operation="create",
            entity_type="EnterpriseContextEntity",
            entity_id=row.id,
            metadata={"name": name, "entity_type": entity_type},
        )
        return self._to_dto(row)

    # ------------------------------------------------------------------
    # IContextEntityRepository: update
    # ------------------------------------------------------------------

    def update(
        self,
        entity_id: str,
        updates: "dict",
        ctx: "Optional[object]" = None,
    ) -> "ContextEntityDTO":
        """Apply a partial update to an existing context entity.

        Parameters
        ----------
        entity_id:
            Entity UUID as a string.
        updates:
            Map of field names to new values.  Supported keys:
            ``name``, ``entity_type``, ``content``, ``path_pattern``,
            ``description``, ``category``, ``auto_load``, ``version``,
            ``target_platforms``, ``category_ids``.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        ContextEntityDTO
            The updated entity.

        Raises
        ------
        KeyError
            If no entity with *entity_id* exists in this tenant.
        ValueError
            If *updates* contains invalid field values.
        """
        from skillmeat.cache.models_enterprise import (
            EnterpriseContextEntity,
            EnterpriseEntityCategoryAssociation,
        )

        try:
            entity_uuid = uuid.UUID(str(entity_id))
        except (ValueError, AttributeError) as exc:
            raise KeyError(entity_id) from exc

        row = self._fetch_entity(entity_uuid)
        if row is None:
            raise KeyError(entity_id)

        for field_name in (
            "name",
            "entity_type",
            "content",
            "path_pattern",
            "description",
            "category",
            "auto_load",
            "version",
            "target_platforms",
        ):
            if field_name in updates:
                setattr(row, field_name, updates[field_name])

        if "category_ids" in updates:
            tenant_id = self._get_tenant_id()
            # Replace all existing associations.
            for assoc in list(row.category_associations):
                self.session.delete(assoc)
            self.session.flush()

            for position, cat_id in enumerate(updates["category_ids"] or []):
                try:
                    cat_uuid = uuid.UUID(str(cat_id))
                except (ValueError, AttributeError):
                    continue
                assoc = EnterpriseEntityCategoryAssociation(
                    tenant_id=tenant_id,
                    entity_id=row.id,
                    category_id=cat_uuid,
                    position=position,
                )
                self.session.add(assoc)

        row.updated_at = datetime.utcnow()
        self.session.flush()
        self._log_operation(
            operation="update",
            entity_type="EnterpriseContextEntity",
            entity_id=entity_uuid,
            metadata={k: str(v)[:80] for k, v in updates.items() if k != "content"},
        )
        return self._to_dto(row)

    # ------------------------------------------------------------------
    # IContextEntityRepository: delete
    # ------------------------------------------------------------------

    def delete(
        self,
        entity_id: str,
        ctx: "Optional[object]" = None,
    ) -> None:
        """Delete a context entity permanently.

        The ``ON DELETE CASCADE`` on ``enterprise_entity_category_associations``
        removes association rows automatically at the database level.

        Parameters
        ----------
        entity_id:
            Entity UUID as a string.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Raises
        ------
        KeyError
            If no entity with *entity_id* exists in this tenant.
        """
        try:
            entity_uuid = uuid.UUID(str(entity_id))
        except (ValueError, AttributeError) as exc:
            raise KeyError(entity_id) from exc

        row = self._fetch_entity(entity_uuid)
        if row is None:
            raise KeyError(entity_id)

        self.session.delete(row)
        self.session.flush()
        self._log_operation(
            operation="delete",
            entity_type="EnterpriseContextEntity",
            entity_id=entity_uuid,
        )

    # ------------------------------------------------------------------
    # IContextEntityRepository: deploy
    # ------------------------------------------------------------------

    def deploy(
        self,
        entity_id: str,
        project_path: str,
        options: "Optional[dict]" = None,
        ctx: "Optional[object]" = None,
    ) -> None:
        """Deploy a context entity's content to a filesystem project path.

        Writes the assembled content to the location specified by
        ``path_pattern``, resolved against *project_path*.

        Parameters
        ----------
        entity_id:
            Entity UUID as a string.
        project_path:
            Absolute filesystem path to the target project directory.
        options:
            Optional deployment options: ``overwrite`` (bool, default False).
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Raises
        ------
        KeyError
            If *entity_id* does not exist.
        FileExistsError
            If the target file already exists and ``options["overwrite"]`` is
            ``False``.
        ValueError
            If *project_path* does not exist or ``path_pattern`` is missing.
        """
        from pathlib import Path

        try:
            entity_uuid = uuid.UUID(str(entity_id))
        except (ValueError, AttributeError) as exc:
            raise KeyError(entity_id) from exc

        row = self._fetch_entity(entity_uuid)
        if row is None:
            raise KeyError(entity_id)

        if not row.path_pattern:
            raise ValueError(f"Entity {entity_id!r} has no path_pattern set.")

        project = Path(project_path)
        if not project.exists():
            raise ValueError(f"project_path {project_path!r} does not exist.")

        target = project / row.path_pattern.lstrip("/")
        overwrite = (options or {}).get("overwrite", False)

        if target.exists() and not overwrite:
            raise FileExistsError(
                f"Target file {target} already exists. Pass overwrite=True to replace it."
            )

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(row.content or "", encoding="utf-8")

        self._log_operation(
            operation="deploy",
            entity_type="EnterpriseContextEntity",
            entity_id=entity_uuid,
            metadata={"project_path": project_path, "target": str(target)},
        )

    # ------------------------------------------------------------------
    # IContextEntityRepository: get_content
    # ------------------------------------------------------------------

    def get_content(
        self,
        entity_id: str,
        ctx: "Optional[object]" = None,
    ) -> "Optional[str]":
        """Return the raw markdown content of a context entity.

        Parameters
        ----------
        entity_id:
            Entity UUID as a string.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        str or None
            Raw content string when the entity exists, ``None`` otherwise.
        """
        try:
            entity_uuid = uuid.UUID(str(entity_id))
        except (ValueError, AttributeError):
            return None

        row = self._fetch_entity(entity_uuid)
        if row is None:
            return None
        return row.content


# =============================================================================
# EnterpriseProjectRepository  (ENT2-4.1)
# =============================================================================


class EnterpriseProjectRepository(
    EnterpriseRepositoryBase["EnterpriseProject"],
):
    """Repository for tenant-scoped CRUD on EnterpriseProject.

    Implements :class:`~skillmeat.core.interfaces.repositories.IProjectRepository`
    for the enterprise PostgreSQL backend.

    Enterprise projects are DB records — ``path`` is an informational metadata
    field recorded at registration time, NOT a live filesystem reference.
    Methods that carry filesystem semantics in the local backend (e.g.
    ``refresh``, ``get_artifacts``) operate purely on DB data and never touch
    the filesystem.  A debug-level log is emitted for every method where
    enterprise behaviour meaningfully diverges from the local implementation.

    Parameters
    ----------
    session:
        An open SQLAlchemy ``Session`` bound to the enterprise database.
        Lifecycle (commit/rollback/close) is managed by the caller.

    Notes
    -----
    - ``path`` is unique per tenant (``uq_enterprise_projects_tenant_path``).
    - ``_apply_tenant_filter()`` is called on every ``select()`` statement.
    - No filesystem operations are performed anywhere in this class.
    """

    def __init__(self, session: Session) -> None:
        from skillmeat.cache.models_enterprise import EnterpriseProject as _EP

        super().__init__(session, _EP)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _to_dto(self, row: "EnterpriseProject") -> "ProjectDTO":
        """Map an ``EnterpriseProject`` ORM instance to a :class:`~skillmeat.core.interfaces.dtos.ProjectDTO`.

        Parameters
        ----------
        row:
            ORM instance to convert.

        Returns
        -------
        ProjectDTO
        """
        from skillmeat.core.interfaces.dtos import ProjectDTO

        return ProjectDTO(
            id=str(row.id),
            name=row.name,
            path=row.path or "",
            description=row.description,
            status=row.status or "active",
            artifact_count=len(row.project_artifacts) if row.project_artifacts else 0,
            created_at=row.created_at.isoformat() if row.created_at else None,
            updated_at=row.updated_at.isoformat() if row.updated_at else None,
        )

    def _fetch_project(
        self,
        project_uuid: "uuid.UUID",
    ) -> "Optional[EnterpriseProject]":
        """Fetch a tenant-filtered project by UUID.

        Parameters
        ----------
        project_uuid:
            UUID of the project to retrieve.

        Returns
        -------
        EnterpriseProject or None
        """
        from skillmeat.cache.models_enterprise import EnterpriseProject

        stmt = self._tenant_select().where(EnterpriseProject.id == project_uuid)
        return self.session.execute(stmt).scalar_one_or_none()

    # ------------------------------------------------------------------
    # IProjectRepository: get
    # ------------------------------------------------------------------

    def get(
        self,
        id: str,
        ctx: "Optional[object]" = None,
    ) -> "Optional[ProjectDTO]":
        """Return the project with the given identifier.

        Parameters
        ----------
        id:
            Project UUID as a string (enterprise PK).
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        ProjectDTO or None
        """
        try:
            project_uuid = uuid.UUID(str(id))
        except (ValueError, AttributeError):
            return None

        row = self._fetch_project(project_uuid)
        if row is None:
            return None
        return self._to_dto(row)

    # ------------------------------------------------------------------
    # IProjectRepository: list
    # ------------------------------------------------------------------

    def list(
        self,
        filters: "Optional[dict]" = None,
        ctx: "Optional[object]" = None,
    ) -> "list[ProjectDTO]":
        """Return all known projects for the current tenant.

        Parameters
        ----------
        filters:
            Optional filter map.  Supported keys: ``status``, ``search``
            (case-insensitive prefix on ``name``).
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        list[ProjectDTO]
        """
        from sqlalchemy import func
        from skillmeat.cache.models_enterprise import EnterpriseProject

        stmt = self._tenant_select().order_by(EnterpriseProject.created_at)

        if filters:
            status = filters.get("status")
            if status is not None:
                stmt = stmt.where(EnterpriseProject.status == status)

            search = filters.get("search")
            if search:
                stmt = stmt.where(
                    func.lower(EnterpriseProject.name).like(f"{search.lower()}%")
                )

        rows = list(self.session.execute(stmt).scalars())
        return [self._to_dto(row) for row in rows]

    # ------------------------------------------------------------------
    # IProjectRepository: create
    # ------------------------------------------------------------------

    def create(
        self,
        dto: "ProjectDTO",
        ctx: "Optional[object]" = None,
    ) -> "ProjectDTO":
        """Register a new project record.

        Parameters
        ----------
        dto:
            Project data.  ``dto.path`` is stored as an informational field;
            no filesystem access is performed.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        ProjectDTO
            The persisted project.
        """
        from skillmeat.cache.models_enterprise import EnterpriseProject

        tenant_id = self._get_tenant_id()

        row = EnterpriseProject(
            tenant_id=tenant_id,
            name=dto.name,
            path=dto.path or "",
            status=dto.status or "active",
            description=dto.description,
        )
        self.session.add(row)
        self.session.flush()

        self._log_operation(
            operation="create",
            entity_type="EnterpriseProject",
            entity_id=row.id,
            metadata={"name": dto.name, "path": dto.path},
        )
        return self._to_dto(row)

    # ------------------------------------------------------------------
    # IProjectRepository: update
    # ------------------------------------------------------------------

    def update(
        self,
        id: str,
        updates: "dict",
        ctx: "Optional[object]" = None,
    ) -> "ProjectDTO":
        """Apply a partial update to an existing project.

        Parameters
        ----------
        id:
            Project UUID as a string.
        updates:
            Map of field names to new values.  Supported keys:
            ``name``, ``path``, ``status``, ``description``.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        ProjectDTO
            The updated project.

        Raises
        ------
        KeyError
            If no project with *id* exists in this tenant.
        """
        try:
            project_uuid = uuid.UUID(str(id))
        except (ValueError, AttributeError) as exc:
            raise KeyError(id) from exc

        row = self._fetch_project(project_uuid)
        if row is None:
            raise KeyError(id)

        for field_name in ("name", "path", "status", "description"):
            if field_name in updates:
                setattr(row, field_name, updates[field_name])

        row.updated_at = datetime.utcnow()
        self.session.flush()

        self._log_operation(
            operation="update",
            entity_type="EnterpriseProject",
            entity_id=row.id,
            metadata={k: str(v)[:80] for k, v in updates.items()},
        )
        return self._to_dto(row)

    # ------------------------------------------------------------------
    # IProjectRepository: delete
    # ------------------------------------------------------------------

    def delete(
        self,
        id: str,
        ctx: "Optional[object]" = None,
    ) -> bool:
        """Remove a project record.

        Does not delete anything on disk — only removes the DB entry.

        Parameters
        ----------
        id:
            Project UUID as a string.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        bool
            ``True`` when the project was found and deleted, ``False``
            otherwise.
        """
        from skillmeat.cache.models_enterprise import EnterpriseProject

        try:
            project_uuid = uuid.UUID(str(id))
        except (ValueError, AttributeError):
            return False

        row = self._fetch_project(project_uuid)
        if row is None:
            return False

        self.session.delete(row)
        self.session.flush()

        self._log_operation(
            operation="delete",
            entity_type="EnterpriseProject",
            entity_id=project_uuid,
            metadata={"id": id},
        )
        return True

    # ------------------------------------------------------------------
    # IProjectRepository: get_artifacts
    # ------------------------------------------------------------------

    def get_artifacts(
        self,
        project_id: str,
        ctx: "Optional[object]" = None,
    ) -> "list[ArtifactDTO]":
        """Return all artifacts deployed to a project.

        Queries ``enterprise_project_artifacts`` and resolves the associated
        ``EnterpriseArtifact`` rows.  No filesystem access is performed.

        Parameters
        ----------
        project_id:
            Project UUID as a string.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        list[ArtifactDTO]
        """
        from skillmeat.cache.models_enterprise import (
            EnterpriseArtifact,
            EnterpriseProjectArtifact,
        )
        from skillmeat.core.interfaces.dtos import ArtifactDTO

        logger.debug(
            "EnterpriseProjectRepository.get_artifacts: querying DB only "
            "(no filesystem scan) for project_id=%s",
            project_id,
        )

        try:
            project_uuid = uuid.UUID(str(project_id))
        except (ValueError, AttributeError):
            return []

        tenant_id = self._get_tenant_id()

        stmt = (
            select(EnterpriseArtifact)
            .join(
                EnterpriseProjectArtifact,
                EnterpriseProjectArtifact.artifact_uuid == EnterpriseArtifact.id,
            )
            .where(
                EnterpriseProjectArtifact.project_id == project_uuid,
                EnterpriseProjectArtifact.tenant_id == tenant_id,
                EnterpriseArtifact.tenant_id == tenant_id,
            )
        )

        rows = list(self.session.execute(stmt).scalars())
        return [
            ArtifactDTO(
                id=row.id or f"{row.artifact_type}:{row.name}",
                name=row.name,
                artifact_type=row.artifact_type or "",
                uuid=str(row.id),
                source=row.source,
                version=row.version,
                scope=row.scope,
                description=row.description,
                project_id=str(project_uuid),
                created_at=row.created_at.isoformat() if row.created_at else None,
                updated_at=row.updated_at.isoformat() if row.updated_at else None,
            )
            for row in rows
        ]

    # ------------------------------------------------------------------
    # IProjectRepository: refresh
    # ------------------------------------------------------------------

    def refresh(
        self,
        id: str,
        ctx: "Optional[object]" = None,
    ) -> "ProjectDTO":
        """Trigger a cache refresh for a single project.

        In the enterprise backend, the DB is the source of truth — no
        filesystem rescan is possible from within the repository layer.
        This method reloads the project record from DB (touching
        ``updated_at``) and returns the current state.

        Parameters
        ----------
        id:
            Project UUID as a string.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        ProjectDTO
            The current project state.

        Raises
        ------
        KeyError
            If no project with *id* exists in this tenant.
        """
        logger.debug(
            "EnterpriseProjectRepository.refresh: enterprise backend has no "
            "filesystem rescan; returning current DB state for project_id=%s",
            id,
        )
        try:
            project_uuid = uuid.UUID(str(id))
        except (ValueError, AttributeError) as exc:
            raise KeyError(id) from exc

        row = self._fetch_project(project_uuid)
        if row is None:
            raise KeyError(id)

        row.updated_at = datetime.utcnow()
        self.session.flush()
        return self._to_dto(row)

    # ------------------------------------------------------------------
    # IProjectRepository: get_by_path
    # ------------------------------------------------------------------

    def get_by_path(
        self,
        path: str,
        ctx: "Optional[object]" = None,
    ) -> "Optional[ProjectDTO]":
        """Return the project whose stored path matches *path*.

        Matches against the ``path`` column (informational, stored at
        registration time).  No live filesystem access is performed.

        Parameters
        ----------
        path:
            Path string to match against.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        ProjectDTO or None
        """
        from skillmeat.cache.models_enterprise import EnterpriseProject

        logger.debug(
            "EnterpriseProjectRepository.get_by_path: matching stored path "
            "column only (no filesystem resolution) for path=%s",
            path,
        )

        stmt = self._tenant_select().where(EnterpriseProject.path == path)
        row = self.session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        return self._to_dto(row)

    # ------------------------------------------------------------------
    # IProjectRepository: get_or_create_by_path
    # ------------------------------------------------------------------

    def get_or_create_by_path(
        self,
        path: str,
        ctx: "Optional[object]" = None,
    ) -> "ProjectDTO":
        """Return the project for *path*, creating a DB record if absent.

        Looks up an existing project by its stored ``path`` column and
        creates a new one if none is found.  No filesystem resolution
        is performed.

        Parameters
        ----------
        path:
            Path string to match or register.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        ProjectDTO
            Existing or newly created project.
        """
        from skillmeat.cache.models_enterprise import EnterpriseProject
        from skillmeat.core.interfaces.dtos import ProjectDTO as _ProjectDTO

        logger.debug(
            "EnterpriseProjectRepository.get_or_create_by_path: using stored "
            "path column only (no filesystem resolution) for path=%s",
            path,
        )

        existing = self.get_by_path(path, ctx=ctx)
        if existing is not None:
            return existing

        # No existing record — create one using the path as both path and name.
        # Derive a display name from the last path component (string-only, no I/O).
        name = path.rstrip("/\\").rsplit("/", 1)[-1] or path
        tenant_id = self._get_tenant_id()

        row = EnterpriseProject(
            tenant_id=tenant_id,
            name=name,
            path=path,
            status="active",
        )
        self.session.add(row)
        self.session.flush()

        self._log_operation(
            operation="create",
            entity_type="EnterpriseProject",
            entity_id=row.id,
            metadata={"name": name, "path": path, "via": "get_or_create_by_path"},
        )
        return self._to_dto(row)


# =============================================================================
# EnterpriseDeploymentRepository  (ENT2-4.2)
# =============================================================================


class EnterpriseDeploymentRepository(
    EnterpriseRepositoryBase["EnterpriseDeployment"],
):
    """Repository for tenant-scoped CRUD on EnterpriseDeployment.

    Implements :class:`~skillmeat.core.interfaces.repositories.IDeploymentRepository`
    for the enterprise PostgreSQL backend.

    Deployment records reference projects via ``project_id`` (nullable FK) and
    artifacts via ``artifact_uuid`` (nullable FK) plus the text ``artifact_id``
    field for backward compatibility with the ``sync_deployment_cache`` callers.

    Parameters
    ----------
    session:
        An open SQLAlchemy ``Session`` bound to the enterprise database.
        Lifecycle (commit/rollback/close) is managed by the caller.

    Notes
    -----
    - Both ``project_id`` and ``artifact_uuid`` are nullable FKs (SET NULL
      on delete); callers must handle ``None`` values gracefully.
    - ``artifact_id`` (text ``"type:name"`` format) is kept for write-through
      compatibility with ``sync_deployment_cache`` and ``remove_deployment_cache``.
    - ``_apply_tenant_filter()`` is called on every ``select()`` statement.
    """

    def __init__(self, session: Session) -> None:
        from skillmeat.cache.models_enterprise import EnterpriseDeployment as _ED

        super().__init__(session, _ED)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _to_dto(self, row: "EnterpriseDeployment") -> "DeploymentDTO":
        """Map an ``EnterpriseDeployment`` ORM instance to a :class:`~skillmeat.core.interfaces.dtos.DeploymentDTO`.

        Parameters
        ----------
        row:
            ORM instance to convert.

        Returns
        -------
        DeploymentDTO
        """
        from skillmeat.core.interfaces.dtos import DeploymentDTO

        artifact_id = row.artifact_id or ""
        # Derive name and type from text identifier "type:name" when possible.
        parts = artifact_id.split(":", 1)
        artifact_type = parts[0] if len(parts) == 2 else ""
        artifact_name = parts[1] if len(parts) == 2 else artifact_id

        project_path: Optional[str] = None
        project_name: Optional[str] = None
        if row.project is not None:
            project_path = row.project.path
            project_name = row.project.name

        return DeploymentDTO(
            id=str(row.id),
            artifact_id=artifact_id,
            artifact_name=artifact_name,
            artifact_type=artifact_type,
            project_id=str(row.project_id) if row.project_id else None,
            project_path=project_path,
            project_name=project_name,
            status=row.status or "deployed",
            deployed_at=row.deployed_at.isoformat() if row.deployed_at else None,
            collection_sha=row.content_hash,
            local_modifications=bool(row.local_modifications),
            deployment_profile_id=(
                str(row.deployment_profile_id) if row.deployment_profile_id else None
            ),
            platform=row.platform,
        )

    def _fetch_deployment(
        self,
        deployment_uuid: "uuid.UUID",
    ) -> "Optional[EnterpriseDeployment]":
        """Fetch a tenant-filtered deployment record by UUID.

        Parameters
        ----------
        deployment_uuid:
            UUID of the deployment to retrieve.

        Returns
        -------
        EnterpriseDeployment or None
        """
        from skillmeat.cache.models_enterprise import EnterpriseDeployment

        stmt = self._tenant_select().where(EnterpriseDeployment.id == deployment_uuid)
        return self.session.execute(stmt).scalar_one_or_none()

    # ------------------------------------------------------------------
    # IDeploymentRepository: get
    # ------------------------------------------------------------------

    def get(
        self,
        id: str,
        ctx: "Optional[object]" = None,
    ) -> "Optional[DeploymentDTO]":
        """Return a deployment record by its identifier.

        Parameters
        ----------
        id:
            Deployment UUID as a string.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        DeploymentDTO or None
        """
        try:
            deployment_uuid = uuid.UUID(str(id))
        except (ValueError, AttributeError):
            return None

        row = self._fetch_deployment(deployment_uuid)
        if row is None:
            return None
        return self._to_dto(row)

    # ------------------------------------------------------------------
    # IDeploymentRepository: list
    # ------------------------------------------------------------------

    def list(
        self,
        filters: "Optional[dict]" = None,
        ctx: "Optional[object]" = None,
    ) -> "list[DeploymentDTO]":
        """Return deployment records matching optional filter criteria.

        Parameters
        ----------
        filters:
            Optional filter map.  Supported keys: ``project_id``,
            ``artifact_id``, ``artifact_type``, ``status``.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        list[DeploymentDTO]
        """
        from skillmeat.cache.models_enterprise import EnterpriseDeployment

        stmt = self._tenant_select().order_by(EnterpriseDeployment.deployed_at.desc())

        if filters:
            project_id = filters.get("project_id")
            if project_id is not None:
                try:
                    proj_uuid = uuid.UUID(str(project_id))
                    stmt = stmt.where(EnterpriseDeployment.project_id == proj_uuid)
                except (ValueError, AttributeError):
                    pass

            artifact_id = filters.get("artifact_id")
            if artifact_id is not None:
                stmt = stmt.where(EnterpriseDeployment.artifact_id == artifact_id)

            artifact_type = filters.get("artifact_type")
            if artifact_type is not None:
                # artifact_id is stored as "type:name" — filter by prefix.
                stmt = stmt.where(
                    EnterpriseDeployment.artifact_id.like(f"{artifact_type}:%")
                )

            status = filters.get("status")
            if status is not None:
                stmt = stmt.where(EnterpriseDeployment.status == status)

        rows = list(self.session.execute(stmt).scalars())
        return [self._to_dto(row) for row in rows]

    # ------------------------------------------------------------------
    # IDeploymentRepository: deploy
    # ------------------------------------------------------------------

    def deploy(
        self,
        artifact_id: str,
        project_id: str,
        options: "Optional[dict]" = None,
        ctx: "Optional[object]" = None,
    ) -> "DeploymentDTO":
        """Record an artifact deployment to a project.

        Creates a new ``EnterpriseDeployment`` row.  Does not perform any
        filesystem copy — the enterprise layer treats deployment tracking as
        a DB write-through from the CLI layer.

        Parameters
        ----------
        artifact_id:
            Artifact primary key in ``"type:name"`` format.
        project_id:
            Target project UUID as a string.
        options:
            Optional deployment options.  Recognised keys: ``status``,
            ``content_hash``, ``deployment_profile_id``, ``platform``,
            ``local_modifications``.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        DeploymentDTO
            The created deployment record.

        Raises
        ------
        KeyError
            If *project_id* is not a valid UUID or does not exist for this
            tenant.
        """
        from skillmeat.cache.models_enterprise import EnterpriseDeployment

        try:
            proj_uuid = uuid.UUID(str(project_id))
        except (ValueError, AttributeError) as exc:
            raise KeyError(project_id) from exc

        opts = options or {}
        tenant_id = self._get_tenant_id()

        profile_id: Optional[uuid.UUID] = None
        raw_profile = opts.get("deployment_profile_id")
        if raw_profile:
            try:
                profile_id = uuid.UUID(str(raw_profile))
            except (ValueError, AttributeError):
                pass

        row = EnterpriseDeployment(
            tenant_id=tenant_id,
            artifact_id=artifact_id,
            project_id=proj_uuid,
            status=opts.get("status", "deployed"),
            deployed_at=datetime.utcnow(),
            content_hash=opts.get("content_hash"),
            deployment_profile_id=profile_id,
            local_modifications=bool(opts.get("local_modifications", False)),
            platform=opts.get("platform"),
        )
        self.session.add(row)
        self.session.flush()

        self._log_operation(
            operation="deploy",
            entity_type="EnterpriseDeployment",
            entity_id=row.id,
            metadata={"artifact_id": artifact_id, "project_id": project_id},
        )
        return self._to_dto(row)

    # ------------------------------------------------------------------
    # IDeploymentRepository: undeploy
    # ------------------------------------------------------------------

    def undeploy(
        self,
        id: str,
        ctx: "Optional[object]" = None,
    ) -> bool:
        """Remove a deployment record.

        Parameters
        ----------
        id:
            Deployment UUID as a string.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        bool
            ``True`` when the record was found and deleted, ``False``
            otherwise.
        """
        try:
            deployment_uuid = uuid.UUID(str(id))
        except (ValueError, AttributeError):
            return False

        row = self._fetch_deployment(deployment_uuid)
        if row is None:
            return False

        self.session.delete(row)
        self.session.flush()

        self._log_operation(
            operation="undeploy",
            entity_type="EnterpriseDeployment",
            entity_id=deployment_uuid,
            metadata={"id": id},
        )
        return True

    # ------------------------------------------------------------------
    # IDeploymentRepository: get_status
    # ------------------------------------------------------------------

    def get_status(
        self,
        id: str,
        ctx: "Optional[object]" = None,
    ) -> str:
        """Return the current status string for a deployment.

        Parameters
        ----------
        id:
            Deployment UUID as a string.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        str
            Status string, e.g. ``"deployed"``, ``"undeployed"``.

        Raises
        ------
        KeyError
            If no deployment with *id* exists in this tenant.
        """
        try:
            deployment_uuid = uuid.UUID(str(id))
        except (ValueError, AttributeError) as exc:
            raise KeyError(id) from exc

        row = self._fetch_deployment(deployment_uuid)
        if row is None:
            raise KeyError(id)

        return row.status or "deployed"

    # ------------------------------------------------------------------
    # IDeploymentRepository: get_by_artifact
    # ------------------------------------------------------------------

    def get_by_artifact(
        self,
        artifact_id: str,
        ctx: "Optional[object]" = None,
    ) -> "list[DeploymentDTO]":
        """Return all active deployments for a given artifact.

        Parameters
        ----------
        artifact_id:
            Artifact primary key in ``"type:name"`` format.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        list[DeploymentDTO]
        """
        from skillmeat.cache.models_enterprise import EnterpriseDeployment

        stmt = (
            self._tenant_select()
            .where(EnterpriseDeployment.artifact_id == artifact_id)
            .order_by(EnterpriseDeployment.deployed_at.desc())
        )
        rows = list(self.session.execute(stmt).scalars())
        return [self._to_dto(row) for row in rows]

    # ------------------------------------------------------------------
    # IDeploymentRepository: get_by_project  (enterprise extra)
    # ------------------------------------------------------------------

    def get_by_project(
        self,
        project_id: str,
        ctx: "Optional[object]" = None,
    ) -> "list[DeploymentDTO]":
        """Return all deployments for a given project.

        This is an enterprise-specific helper method.  The
        :class:`~skillmeat.core.interfaces.repositories.IDeploymentRepository`
        interface exposes the same via ``list(filters={"project_id": ...})``,
        but this dedicated method is provided for clarity.

        Parameters
        ----------
        project_id:
            Project UUID as a string.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        list[DeploymentDTO]
        """
        return self.list(filters={"project_id": project_id}, ctx=ctx)

    # ------------------------------------------------------------------
    # IDeploymentRepository: list_by_status  (enterprise extra)
    # ------------------------------------------------------------------

    def list_by_status(
        self,
        status: str,
        ctx: "Optional[object]" = None,
    ) -> "list[DeploymentDTO]":
        """Return all deployments with the given status.

        Enterprise-specific filtered query helper backed by the
        ``idx_enterprise_deployments_tenant_status`` index.

        Parameters
        ----------
        status:
            Deployment status string, e.g. ``"deployed"``, ``"undeployed"``.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        list[DeploymentDTO]
        """
        return self.list(filters={"status": status}, ctx=ctx)

    # ------------------------------------------------------------------
    # IDeploymentRepository: upsert_idp_deployment_set
    # ------------------------------------------------------------------

    def upsert_idp_deployment_set(
        self,
        *,
        remote_url: str,
        name: str,
        provisioned_by: str,
        description: "Optional[str]" = None,
        ctx: "Optional[object]" = None,
    ) -> "Tuple[str, bool]":
        """Idempotently create or update a DeploymentSet for an IDP registration.

        Parameters
        ----------
        remote_url:
            Remote Git repository URL.
        name:
            Artifact target identifier used as the set name.
        provisioned_by:
            Audit field identifying the provisioning agent.
        description:
            Optional JSON-serialised metadata string.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        tuple[str, bool]
            ``(deployment_set_id, created)`` where *created* is ``True``
            when a new record was inserted.
        """
        from skillmeat.cache.models_enterprise import EnterpriseDeploymentSet

        tenant_id = self._get_tenant_id()

        stmt = (
            select(EnterpriseDeploymentSet)
            .where(
                EnterpriseDeploymentSet.tenant_id == tenant_id,
                EnterpriseDeploymentSet.remote_url == remote_url,
                EnterpriseDeploymentSet.name == name,
            )
        )
        row = self.session.execute(stmt).scalar_one_or_none()

        created = False
        if row is None:
            row = EnterpriseDeploymentSet(
                tenant_id=tenant_id,
                remote_url=remote_url,
                name=name,
                provisioned_by=provisioned_by,
                description=description,
            )
            self.session.add(row)
            created = True
        else:
            row.provisioned_by = provisioned_by
            if description is not None:
                row.description = description
            row.updated_at = datetime.utcnow()

        self.session.flush()

        self._log_operation(
            operation="upsert_idp_deployment_set",
            entity_type="EnterpriseDeploymentSet",
            entity_id=row.id,
            metadata={
                "remote_url": remote_url,
                "name": name,
                "created": created,
            },
        )
        return str(row.id), created

    # ------------------------------------------------------------------
    # IDeploymentRepository: sync_deployment_cache
    # ------------------------------------------------------------------

    def sync_deployment_cache(
        self,
        artifact_id: str,
        project_path: str,
        project_name: str,
        deployed_at: "Any",
        content_hash: "Optional[str]" = None,
        deployment_profile_id: "Optional[str]" = None,
        local_modifications: bool = False,
        platform: "Optional[str]" = None,
        ctx: "Optional[object]" = None,
    ) -> bool:
        """Upsert a single deployment entry into the enterprise deployments table.

        Performs a write-through update: looks up an existing active
        deployment record for the ``(artifact_id, project_path)`` pair and
        updates it, or creates a new row if none exists.

        Parameters
        ----------
        artifact_id:
            Artifact primary key in ``"type:name"`` format.
        project_path:
            Stored path of the target project.
        project_name:
            Human-readable project directory name.
        deployed_at:
            Deployment timestamp (``datetime`` or ISO string).
        content_hash:
            Optional SHA of the deployed content.
        deployment_profile_id:
            Optional deployment profile identifier.
        local_modifications:
            Whether local modifications are present.
        platform:
            Optional platform identifier string.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        bool
            Always ``True`` for the enterprise backend (upsert always succeeds).
        """
        from skillmeat.cache.models_enterprise import EnterpriseDeployment, EnterpriseProject

        tenant_id = self._get_tenant_id()

        # Resolve or create project row by stored path.
        proj_stmt = select(EnterpriseProject).where(
            EnterpriseProject.tenant_id == tenant_id,
            EnterpriseProject.path == project_path,
        )
        project_row = self.session.execute(proj_stmt).scalar_one_or_none()
        if project_row is None:
            project_row = EnterpriseProject(
                tenant_id=tenant_id,
                name=project_name,
                path=project_path,
                status="active",
            )
            self.session.add(project_row)
            self.session.flush()

        # Normalise deployed_at to a datetime.
        if isinstance(deployed_at, str):
            try:
                from datetime import timezone
                deployed_dt = datetime.fromisoformat(deployed_at)
            except (ValueError, TypeError):
                deployed_dt = datetime.utcnow()
        elif isinstance(deployed_at, datetime):
            deployed_dt = deployed_at
        else:
            deployed_dt = datetime.utcnow()

        # Look for an existing active deployment row for this artifact+project.
        existing_stmt = self._tenant_select().where(
            EnterpriseDeployment.artifact_id == artifact_id,
            EnterpriseDeployment.project_id == project_row.id,
            EnterpriseDeployment.status == "deployed",
        )
        row = self.session.execute(existing_stmt).scalar_one_or_none()

        profile_id: Optional[uuid.UUID] = None
        if deployment_profile_id:
            try:
                profile_id = uuid.UUID(str(deployment_profile_id))
            except (ValueError, AttributeError):
                pass

        if row is None:
            row = EnterpriseDeployment(
                tenant_id=tenant_id,
                artifact_id=artifact_id,
                project_id=project_row.id,
                status="deployed",
                deployed_at=deployed_dt,
                content_hash=content_hash,
                deployment_profile_id=profile_id,
                local_modifications=local_modifications,
                platform=platform,
            )
            self.session.add(row)
        else:
            row.deployed_at = deployed_dt
            row.content_hash = content_hash
            row.deployment_profile_id = profile_id
            row.local_modifications = local_modifications
            row.platform = platform
            row.updated_at = datetime.utcnow()

        self.session.flush()

        self._log_operation(
            operation="sync_deployment_cache",
            entity_type="EnterpriseDeployment",
            entity_id=row.id,
            metadata={"artifact_id": artifact_id, "project_path": project_path},
        )
        return True

    # ------------------------------------------------------------------
    # IDeploymentRepository: remove_deployment_cache
    # ------------------------------------------------------------------

    def remove_deployment_cache(
        self,
        artifact_id: str,
        project_path: str,
        profile_id: "Optional[str]" = None,
        ctx: "Optional[object]" = None,
    ) -> bool:
        """Remove a deployment entry from the enterprise deployments table.

        Marks matching ``EnterpriseDeployment`` rows as ``"undeployed"``
        (soft delete) rather than physically removing them, so audit history
        is preserved.

        Parameters
        ----------
        artifact_id:
            Artifact primary key in ``"type:name"`` format.
        project_path:
            Stored path of the target project.
        profile_id:
            Optional profile ID to narrow the removal to a specific entry.
        ctx:
            Optional per-request metadata (unused by the enterprise backend).

        Returns
        -------
        bool
            ``True`` when at least one matching record was found and updated,
            ``False`` otherwise.
        """
        from skillmeat.cache.models_enterprise import EnterpriseDeployment, EnterpriseProject

        tenant_id = self._get_tenant_id()

        # Resolve project by stored path.
        proj_stmt = select(EnterpriseProject).where(
            EnterpriseProject.tenant_id == tenant_id,
            EnterpriseProject.path == project_path,
        )
        project_row = self.session.execute(proj_stmt).scalar_one_or_none()
        if project_row is None:
            logger.debug(
                "EnterpriseDeploymentRepository.remove_deployment_cache: "
                "project not found for path=%s — nothing to remove",
                project_path,
            )
            return False

        stmt = self._tenant_select().where(
            EnterpriseDeployment.artifact_id == artifact_id,
            EnterpriseDeployment.project_id == project_row.id,
        )

        if profile_id:
            try:
                prof_uuid = uuid.UUID(str(profile_id))
                stmt = stmt.where(EnterpriseDeployment.deployment_profile_id == prof_uuid)
            except (ValueError, AttributeError):
                pass

        rows = list(self.session.execute(stmt).scalars())
        if not rows:
            return False

        for row in rows:
            row.status = "undeployed"
            row.updated_at = datetime.utcnow()

        self.session.flush()

        self._log_operation(
            operation="remove_deployment_cache",
            entity_type="EnterpriseDeployment",
            entity_id=None,
            metadata={
                "artifact_id": artifact_id,
                "project_path": project_path,
                "rows_updated": len(rows),
            },
        )
        return True


# =============================================================================
# EnterpriseDeploymentSetRepository  (ENT2-4.3)
# =============================================================================


class EnterpriseDeploymentSetRepository(
    EnterpriseRepositoryBase["EnterpriseDeploymentSet"]
):
    """Enterprise repository for DeploymentSet CRUD with tenant-scoped access.

    Implements the same callable interface as the local ``DeploymentSetRepository``
    in ``repositories.py``, replacing the ``owner_id`` scope parameter with
    automatic tenant filtering via ``TenantContext``.

    Tag filtering uses the ``EnterpriseDeploymentSetTag`` join table rather
    than the ``tags_json`` TEXT column so that queries leverage the indexed
    ``tag`` column.

    FR-10 delete semantics: Before deleting a set, any
    ``EnterpriseDeploymentSetMember`` rows in *other* sets that reference the
    doomed set via ``member_set_id`` are deleted first, preventing orphan
    references.

    Usage::

        with tenant_scope(tenant_uuid):
            repo = EnterpriseDeploymentSetRepository(db_session)
            ds = repo.create(name="My Set", owner_id="user-1")
            fetched = repo.get(str(ds.id), owner_id="user-1")
            sets = repo.list(owner_id="user-1", tag="prod")
            ok = repo.delete(str(ds.id), owner_id="user-1")

    Notes
    -----
    * ``owner_id`` parameters are accepted for interface compatibility but are
      not used for filtering — tenant isolation is enforced structurally via
      ``TenantContext``.
    * SQLAlchemy 2.x ``select()`` style throughout.
    * UUID primary keys.
    """

    def __init__(self, session: Session) -> None:
        """Initialise the enterprise deployment set repository.

        Parameters
        ----------
        session:
            Injected SQLAlchemy session bound to the PostgreSQL enterprise
            database.
        """
        from skillmeat.cache.models_enterprise import EnterpriseDeploymentSet

        super().__init__(session, EnterpriseDeploymentSet)

    # =========================================================================
    # Internal helpers
    # =========================================================================

    def _sync_tags(
        self,
        deployment_set_id: uuid.UUID,
        tag_names: List[str],
    ) -> None:
        """Replace all tag associations for a deployment set.

        Deletes existing ``EnterpriseDeploymentSetTag`` rows for the set, then
        inserts one row per non-empty tag name.

        Parameters
        ----------
        deployment_set_id:
            UUID primary key of the parent deployment set.
        tag_names:
            List of tag name strings to associate with the set.
        """
        from skillmeat.cache.models_enterprise import EnterpriseDeploymentSetTag

        tenant_id = self._get_tenant_id()

        # Clear existing tag rows for this set.
        self.session.execute(
            delete(EnterpriseDeploymentSetTag).where(
                EnterpriseDeploymentSetTag.set_id == deployment_set_id
            )
        )

        now = datetime.utcnow()
        for raw_name in tag_names:
            name = raw_name.strip()
            if not name:
                continue
            tag_row = EnterpriseDeploymentSetTag(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                set_id=deployment_set_id,
                tag=name,
                created_at=now,
            )
            self.session.add(tag_row)

    # =========================================================================
    # Create
    # =========================================================================

    def create(
        self,
        *,
        name: str,
        owner_id: str,
        description: Optional[str] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> "EnterpriseDeploymentSet":
        """Create and return a new ``EnterpriseDeploymentSet``.

        Parameters
        ----------
        name:
            Human-readable set name (required).
        owner_id:
            Accepted for interface compatibility; tenant filtering is applied
            automatically via ``TenantContext``.
        description:
            Optional free-text description.
        color:
            Ignored — ``EnterpriseDeploymentSet`` has no ``color`` column.
            Accepted for interface parity with the local repository.
        icon:
            Ignored — ``EnterpriseDeploymentSet`` has no ``icon`` column.
            Accepted for interface parity with the local repository.
        tags:
            Optional list of tag name strings.

        Returns
        -------
        EnterpriseDeploymentSet
            Newly created and flushed instance.

        Raises
        ------
        Exception
            Re-raises any database error after rolling back the session.
        """
        from skillmeat.cache.models_enterprise import EnterpriseDeploymentSet

        tenant_id = self._get_tenant_id()
        now = datetime.utcnow()

        ds = EnterpriseDeploymentSet(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=name,
            description=description,
            provisioned_by=owner_id,
            created_at=now,
            updated_at=now,
        )
        try:
            self.session.add(ds)
            self.session.flush()
            if tags:
                self._sync_tags(ds.id, tags)
            self.session.flush()
            logger.debug(
                "Created EnterpriseDeploymentSet id=%s tenant=%s",
                ds.id,
                tenant_id,
            )
            self._log_operation(
                operation="create",
                entity_type="EnterpriseDeploymentSet",
                entity_id=ds.id,
                metadata={"name": name, "owner_id": owner_id},
            )
            return ds
        except Exception:
            self.session.rollback()
            raise

    # =========================================================================
    # Read
    # =========================================================================

    def get(
        self,
        set_id: str,
        owner_id: str,
    ) -> "Optional[EnterpriseDeploymentSet]":
        """Fetch a single deployment set by ID, scoped to the current tenant.

        Parameters
        ----------
        set_id:
            String representation of the deployment set UUID.
        owner_id:
            Accepted for interface compatibility; not used for filtering.

        Returns
        -------
        EnterpriseDeploymentSet or None
        """
        from skillmeat.cache.models_enterprise import EnterpriseDeploymentSet

        try:
            set_uuid = uuid.UUID(str(set_id))
        except (ValueError, AttributeError):
            return None

        stmt = self._tenant_select().where(EnterpriseDeploymentSet.id == set_uuid)
        return self.session.execute(stmt).scalar_one_or_none()

    # =========================================================================
    # List
    # =========================================================================

    def list(
        self,
        owner_id: str,
        *,
        name: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> "List[EnterpriseDeploymentSet]":
        """Return a paginated, filterable list of deployment sets for the current tenant.

        Parameters
        ----------
        owner_id:
            Accepted for interface compatibility; not used for filtering.
        name:
            Optional substring filter on ``name`` (case-insensitive).
        tag:
            Optional tag string to filter by; matches via the
            ``EnterpriseDeploymentSetTag`` join table.
        limit:
            Maximum rows to return (default 50).
        offset:
            Rows to skip for pagination (default 0).

        Returns
        -------
        List[EnterpriseDeploymentSet]
            Ordered by ``created_at`` descending.
        """
        from skillmeat.cache.models_enterprise import (
            EnterpriseDeploymentSet,
            EnterpriseDeploymentSetTag,
        )

        stmt = self._tenant_select().order_by(EnterpriseDeploymentSet.created_at.desc())

        if name is not None:
            stmt = stmt.where(EnterpriseDeploymentSet.name.ilike(f"%{name}%"))

        if tag is not None:
            stmt = stmt.join(
                EnterpriseDeploymentSetTag,
                EnterpriseDeploymentSetTag.set_id == EnterpriseDeploymentSet.id,
            ).where(EnterpriseDeploymentSetTag.tag == tag)

        stmt = stmt.limit(limit).offset(offset)
        return list(self.session.execute(stmt).scalars())

    # =========================================================================
    # Count
    # =========================================================================

    def count(
        self,
        owner_id: str,
        *,
        name: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> int:
        """Count deployment sets matching the given filters for the current tenant.

        Parameters
        ----------
        owner_id:
            Accepted for interface compatibility; not used for filtering.
        name:
            Optional substring filter on ``name``.
        tag:
            Optional tag filter.

        Returns
        -------
        int
            Count of matching sets.
        """
        from sqlalchemy import func as sa_func

        from skillmeat.cache.models_enterprise import (
            EnterpriseDeploymentSet,
            EnterpriseDeploymentSetTag,
        )

        stmt = self._apply_tenant_filter(
            select(sa_func.count(EnterpriseDeploymentSet.id))
        )

        if name is not None:
            stmt = stmt.where(EnterpriseDeploymentSet.name.ilike(f"%{name}%"))

        if tag is not None:
            stmt = stmt.join(
                EnterpriseDeploymentSetTag,
                EnterpriseDeploymentSetTag.set_id == EnterpriseDeploymentSet.id,
            ).where(EnterpriseDeploymentSetTag.tag == tag)

        return self.session.execute(stmt).scalar() or 0

    # =========================================================================
    # Update
    # =========================================================================

    def update(
        self,
        set_id: str,
        owner_id: str,
        **kwargs: object,
    ) -> "Optional[EnterpriseDeploymentSet]":
        """Update mutable fields on a deployment set.

        Accepted keyword arguments: ``name`` (str), ``description`` (str | None),
        ``tags`` (list[str]).  ``color`` and ``icon`` are silently ignored as
        ``EnterpriseDeploymentSet`` has no such columns.  ``updated_at`` is
        refreshed on every successful update.

        Parameters
        ----------
        set_id:
            String UUID of the deployment set to update.
        owner_id:
            Accepted for interface compatibility; not used for filtering.
        **kwargs:
            Keyword arguments for fields to update.

        Returns
        -------
        EnterpriseDeploymentSet or None
            Updated instance, or ``None`` if not found.

        Raises
        ------
        Exception
            Re-raises any database error after rolling back the session.
        """
        from skillmeat.cache.models_enterprise import EnterpriseDeploymentSet

        try:
            set_uuid = uuid.UUID(str(set_id))
        except (ValueError, AttributeError):
            return None

        stmt = self._tenant_select().where(EnterpriseDeploymentSet.id == set_uuid)
        ds = self.session.execute(stmt).scalar_one_or_none()
        if ds is None:
            return None

        try:
            if "name" in kwargs:
                ds.name = kwargs["name"]  # type: ignore[assignment]
            if "description" in kwargs:
                ds.description = kwargs["description"]  # type: ignore[assignment]
            if "tags" in kwargs:
                tag_list = kwargs["tags"]
                self._sync_tags(ds.id, list(tag_list) if tag_list else [])  # type: ignore[arg-type]

            ds.updated_at = datetime.utcnow()
            self.session.flush()
            logger.debug(
                "Updated EnterpriseDeploymentSet id=%s tenant=%s",
                set_id,
                self._get_tenant_id(),
            )
            self._log_operation(
                operation="update",
                entity_type="EnterpriseDeploymentSet",
                entity_id=ds.id,
                metadata={"fields": list(kwargs.keys())},
            )
            return ds
        except Exception:
            self.session.rollback()
            raise

    # =========================================================================
    # Delete  (FR-10)
    # =========================================================================

    def delete(self, set_id: str, owner_id: str) -> bool:
        """Delete a deployment set, cleaning up cross-set member references first.

        FR-10 semantics: Before deleting the target set, any
        ``EnterpriseDeploymentSetMember`` rows in *other* sets that reference the
        target via ``member_set_id`` are deleted to prevent orphan references.
        The target set's own members are removed by the ``ON DELETE CASCADE``
        on ``enterprise_deployment_set_members.set_id``.

        Parameters
        ----------
        set_id:
            String UUID of the deployment set to delete.
        owner_id:
            Accepted for interface compatibility; not used for filtering.

        Returns
        -------
        bool
            ``True`` if the set was found and deleted, ``False`` otherwise.

        Raises
        ------
        Exception
            Re-raises any database error after rolling back the session.
        """
        from skillmeat.cache.models_enterprise import (
            EnterpriseDeploymentSet,
            EnterpriseDeploymentSetMember,
        )

        try:
            set_uuid = uuid.UUID(str(set_id))
        except (ValueError, AttributeError):
            return False

        stmt = self._tenant_select().where(EnterpriseDeploymentSet.id == set_uuid)
        ds = self.session.execute(stmt).scalar_one_or_none()
        if ds is None:
            return False

        try:
            # FR-10: remove member rows in OTHER sets referencing this set as a
            # nested member before deleting the set itself.
            orphan_stmt = select(EnterpriseDeploymentSetMember).where(
                EnterpriseDeploymentSetMember.member_set_id == set_uuid,
                EnterpriseDeploymentSetMember.set_id != set_uuid,
            )
            orphans = list(self.session.execute(orphan_stmt).scalars())
            for member in orphans:
                self.session.delete(member)

            self.session.delete(ds)
            self.session.flush()
            logger.debug(
                "Deleted EnterpriseDeploymentSet id=%s (removed %d orphan member refs)",
                set_id,
                len(orphans),
            )
            self._log_operation(
                operation="delete",
                entity_type="EnterpriseDeploymentSet",
                entity_id=set_uuid,
                metadata={"orphan_members_removed": len(orphans)},
            )
            return True
        except Exception:
            self.session.rollback()
            raise

    # =========================================================================
    # Member management
    # =========================================================================

    def add_member(
        self,
        set_id: str,
        owner_id: str,
        *,
        artifact_id: Optional[str] = None,
        position: Optional[int] = None,
    ) -> "EnterpriseDeploymentSetMember":
        """Add a member artifact to a deployment set.

        Parameters
        ----------
        set_id:
            String UUID of the parent deployment set.
        owner_id:
            Accepted for interface compatibility; not used for filtering.
        artifact_id:
            Text artifact identifier (e.g. ``"skill:canvas"``).
        position:
            Explicit 0-based ordering position.  Auto-assigned (max + 1) when
            omitted.

        Returns
        -------
        EnterpriseDeploymentSetMember
            Newly created member row.

        Raises
        ------
        ValueError
            If the parent set does not exist in the current tenant.
        Exception
            Re-raises any database error after rolling back the session.
        """
        from skillmeat.cache.models_enterprise import (
            EnterpriseDeploymentSet,
            EnterpriseDeploymentSetMember,
        )

        try:
            set_uuid = uuid.UUID(str(set_id))
        except (ValueError, AttributeError) as exc:
            raise ValueError(f"Invalid set_id: {set_id!r}") from exc

        tenant_id = self._get_tenant_id()

        # Verify the parent set belongs to this tenant.
        stmt = self._tenant_select().where(EnterpriseDeploymentSet.id == set_uuid)
        ds = self.session.execute(stmt).scalar_one_or_none()
        if ds is None:
            raise ValueError(
                f"EnterpriseDeploymentSet {set_id!r} not found for current tenant"
            )

        # Auto-assign position if not supplied.
        if position is None:
            pos_stmt = select(EnterpriseDeploymentSetMember.position).where(
                EnterpriseDeploymentSetMember.set_id == set_uuid
            )
            positions = list(self.session.execute(pos_stmt).scalars())
            position = (max(positions) + 1) if positions else 0

        try:
            member = EnterpriseDeploymentSetMember(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                set_id=set_uuid,
                artifact_id=artifact_id or "",
                position=position,
            )
            self.session.add(member)
            self.session.flush()
            logger.debug(
                "Added member artifact_id=%s to EnterpriseDeploymentSet id=%s",
                artifact_id,
                set_id,
            )
            return member
        except Exception:
            self.session.rollback()
            raise

    def remove_member(
        self,
        set_id: str,
        owner_id: str,
        artifact_id: str,
    ) -> bool:
        """Remove a member artifact from a deployment set.

        Parameters
        ----------
        set_id:
            String UUID of the parent deployment set.
        owner_id:
            Accepted for interface compatibility; not used for filtering.
        artifact_id:
            Text artifact identifier of the member to remove.

        Returns
        -------
        bool
            ``True`` if a matching member was found and deleted, ``False``
            otherwise.
        """
        from skillmeat.cache.models_enterprise import EnterpriseDeploymentSetMember

        try:
            set_uuid = uuid.UUID(str(set_id))
        except (ValueError, AttributeError):
            return False

        stmt = select(EnterpriseDeploymentSetMember).where(
            EnterpriseDeploymentSetMember.set_id == set_uuid,
            EnterpriseDeploymentSetMember.artifact_id == artifact_id,
        )
        member = self.session.execute(stmt).scalar_one_or_none()
        if member is None:
            return False

        try:
            self.session.delete(member)
            self.session.flush()
            return True
        except Exception:
            self.session.rollback()
            raise

    def list_members(
        self,
        set_id: str,
        owner_id: str,
    ) -> "List[EnterpriseDeploymentSetMember]":
        """List all members of a deployment set ordered by position.

        Parameters
        ----------
        set_id:
            String UUID of the parent deployment set.
        owner_id:
            Accepted for interface compatibility; not used for filtering.

        Returns
        -------
        List[EnterpriseDeploymentSetMember]
            Members ordered by ``position`` ascending.
        """
        from skillmeat.cache.models_enterprise import EnterpriseDeploymentSetMember

        try:
            set_uuid = uuid.UUID(str(set_id))
        except (ValueError, AttributeError):
            return []

        stmt = (
            select(EnterpriseDeploymentSetMember)
            .where(EnterpriseDeploymentSetMember.set_id == set_uuid)
            .order_by(EnterpriseDeploymentSetMember.position.asc())
        )
        return list(self.session.execute(stmt).scalars())


# =============================================================================
# EnterpriseDeploymentProfileRepository  (ENT2-4.4)
# =============================================================================


class EnterpriseDeploymentProfileRepository(
    EnterpriseRepositoryBase["EnterpriseDeploymentProfile"]
):
    """Enterprise repository for DeploymentProfile CRUD with tenant-scoped access.

    Implements the same callable interface as the local ``DeploymentProfileRepository``
    in ``repositories.py``.

    The ``EnterpriseDeploymentProfile`` model stores flexible configuration in
    the ``extra_metadata`` JSONB column (NOT ``metadata`` — that name conflicts
    with SQLAlchemy's reserved ``DeclarativeBase.metadata`` attribute).

    Usage::

        with tenant_scope(tenant_uuid):
            repo = EnterpriseDeploymentProfileRepository(db_session)
            profile = repo.create(
                project_id="proj-1",
                profile_id="claude_code",
                platform="claude_code",
                root_dir=".claude",
            )
            fetched = repo.read_by_project_and_profile_id("proj-1", "claude_code")

    Notes
    -----
    * ``project_id`` parameters are stored in ``extra_metadata["project_id"]``
      since ``EnterpriseDeploymentProfile`` has no dedicated ``project_id``
      column.
    * ``profile_id`` is stored as a plain name tag in ``extra_metadata["profile_id"]``.
    * SQLAlchemy 2.x ``select()`` style throughout.
    * UUID primary keys.
    """

    def __init__(self, session: Session) -> None:
        """Initialise the enterprise deployment profile repository.

        Parameters
        ----------
        session:
            Injected SQLAlchemy session bound to the PostgreSQL enterprise
            database.
        """
        from skillmeat.cache.models_enterprise import EnterpriseDeploymentProfile

        super().__init__(session, EnterpriseDeploymentProfile)

    # =========================================================================
    # Create
    # =========================================================================

    def create(
        self,
        *,
        project_id: str,
        profile_id: str,
        platform: str,
        root_dir: str,
        description: Optional[str] = None,
        artifact_path_map: Optional[Dict[str, str]] = None,
        config_filenames: Optional[List[str]] = None,
        context_prefixes: Optional[List[str]] = None,
        supported_types: Optional[List[str]] = None,
    ) -> "EnterpriseDeploymentProfile":
        """Create a deployment profile.

        Parameters
        ----------
        project_id:
            Project identifier; stored in ``extra_metadata["project_id"]``.
        profile_id:
            Profile identifier string (e.g. ``"claude_code"``); stored in
            ``extra_metadata["profile_id"]``.
        platform:
            Target platform string (e.g. ``"claude_code"``).
        root_dir:
            Destination root directory (e.g. ``".claude"``).
        description:
            Optional free-text description.
        artifact_path_map:
            Optional mapping of artifact type to destination path.
        config_filenames:
            Optional list of config file names for this profile.
        context_prefixes:
            Optional list of context path prefixes.
        supported_types:
            Optional list of artifact type strings this profile supports.

        Returns
        -------
        EnterpriseDeploymentProfile
            Newly created and flushed instance.

        Raises
        ------
        Exception
            Re-raises any database error after rolling back.
        """
        from skillmeat.cache.models_enterprise import EnterpriseDeploymentProfile

        tenant_id = self._get_tenant_id()
        now = datetime.utcnow()

        meta: Dict[str, object] = {
            "project_id": project_id,
            "profile_id": profile_id,
            "root_dir": root_dir,
        }
        if artifact_path_map is not None:
            meta["artifact_path_map"] = artifact_path_map
        if config_filenames is not None:
            meta["config_filenames"] = config_filenames
        if context_prefixes is not None:
            meta["context_prefixes"] = context_prefixes
        if supported_types is not None:
            meta["supported_types"] = supported_types

        profile = EnterpriseDeploymentProfile(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=f"{project_id}/{profile_id}",
            scope="project",
            dest_path=root_dir,
            platform=platform,
            overwrite=False,
            extra_metadata=meta,
            created_at=now,
            updated_at=now,
        )
        if description is not None:
            # Store in extra_metadata since the model has no description column.
            profile.extra_metadata = {**meta, "description": description}

        try:
            self.session.add(profile)
            self.session.flush()
            logger.debug(
                "Created EnterpriseDeploymentProfile id=%s project=%s profile_id=%s",
                profile.id,
                project_id,
                profile_id,
            )
            self._log_operation(
                operation="create",
                entity_type="EnterpriseDeploymentProfile",
                entity_id=profile.id,
                metadata={"project_id": project_id, "profile_id": profile_id},
            )
            return profile
        except Exception:
            self.session.rollback()
            raise

    # =========================================================================
    # Read
    # =========================================================================

    def read_by_id(self, profile_db_id: str) -> "Optional[EnterpriseDeploymentProfile]":
        """Read a deployment profile by its UUID primary key.

        Parameters
        ----------
        profile_db_id:
            String representation of the profile UUID.

        Returns
        -------
        EnterpriseDeploymentProfile or None
        """
        from skillmeat.cache.models_enterprise import EnterpriseDeploymentProfile

        try:
            profile_uuid = uuid.UUID(str(profile_db_id))
        except (ValueError, AttributeError):
            return None

        stmt = self._tenant_select().where(
            EnterpriseDeploymentProfile.id == profile_uuid
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def read_by_project_and_profile_id(
        self, project_id: str, profile_id: str
    ) -> "Optional[EnterpriseDeploymentProfile]":
        """Read a deployment profile by project and profile ID.

        Matches against ``extra_metadata["project_id"]`` and
        ``extra_metadata["profile_id"]`` stored in the JSONB column.

        Parameters
        ----------
        project_id:
            Project identifier.
        profile_id:
            Profile identifier string (e.g. ``"claude_code"``).

        Returns
        -------
        EnterpriseDeploymentProfile or None
        """
        from skillmeat.cache.models_enterprise import EnterpriseDeploymentProfile

        # Construct a JSONB containment filter: extra_metadata @> {...}
        # This requires the psycopg2 / asyncpg JSONB operator support.
        # We use the canonical name match as a fallback via the stored name.
        canonical_name = f"{project_id}/{profile_id}"
        stmt = self._tenant_select().where(
            EnterpriseDeploymentProfile.name == canonical_name
        )
        return self.session.execute(stmt).scalar_one_or_none()

    # =========================================================================
    # List
    # =========================================================================

    def list_by_project(
        self, project_id: str
    ) -> "List[EnterpriseDeploymentProfile]":
        """List all deployment profiles for a project.

        Matches profiles whose ``name`` starts with ``"{project_id}/"``
        (the canonical naming format used by ``create()``).

        Parameters
        ----------
        project_id:
            Project identifier.

        Returns
        -------
        List[EnterpriseDeploymentProfile]
            Profiles ordered by ``name`` ascending.
        """
        from skillmeat.cache.models_enterprise import EnterpriseDeploymentProfile

        stmt = (
            self._tenant_select()
            .where(EnterpriseDeploymentProfile.name.like(f"{project_id}/%"))
            .order_by(EnterpriseDeploymentProfile.name.asc())
        )
        return list(self.session.execute(stmt).scalars())

    def list_all_profiles(
        self, project_id: str
    ) -> "List[EnterpriseDeploymentProfile]":
        """Alias for ``list_by_project()`` — interface parity with local repo.

        Parameters
        ----------
        project_id:
            Project identifier.

        Returns
        -------
        List[EnterpriseDeploymentProfile]
        """
        return self.list_by_project(project_id)

    # =========================================================================
    # Platform / primary-profile helpers
    # =========================================================================

    def get_profile_by_platform(
        self,
        project_id: str,
        platform: "str | object",
    ) -> "Optional[EnterpriseDeploymentProfile]":
        """Get the first deployment profile matching a project and platform.

        Parameters
        ----------
        project_id:
            Project identifier.
        platform:
            Platform string or enum with ``.value``.

        Returns
        -------
        EnterpriseDeploymentProfile or None
        """
        from skillmeat.cache.models_enterprise import EnterpriseDeploymentProfile

        platform_value = (
            platform.value  # type: ignore[union-attr]
            if hasattr(platform, "value")
            else str(platform)
        )
        stmt = (
            self._tenant_select()
            .where(
                EnterpriseDeploymentProfile.name.like(f"{project_id}/%"),
                EnterpriseDeploymentProfile.platform == platform_value,
            )
            .order_by(EnterpriseDeploymentProfile.name.asc())
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_primary_profile(
        self, project_id: str
    ) -> "Optional[EnterpriseDeploymentProfile]":
        """Get the primary deployment profile for a project.

        Preference order:
        1. Explicit ``claude_code`` platform profile.
        2. Profile whose name ends with ``/claude_code``.
        3. First profile alphabetically.

        Parameters
        ----------
        project_id:
            Project identifier.

        Returns
        -------
        EnterpriseDeploymentProfile or None
        """
        primary = self.get_profile_by_platform(project_id, "claude_code")
        if primary:
            return primary

        profile = self.read_by_project_and_profile_id(project_id, "claude_code")
        if profile:
            return profile

        profiles = self.list_by_project(project_id)
        return profiles[0] if profiles else None

    def ensure_default_claude_profile(
        self, project_id: str
    ) -> "EnterpriseDeploymentProfile":
        """Ensure a backward-compatible default Claude Code profile exists.

        Returns an existing profile if one is found; otherwise creates a new
        ``claude_code`` profile with sensible defaults.

        Parameters
        ----------
        project_id:
            Project identifier.

        Returns
        -------
        EnterpriseDeploymentProfile
        """
        primary = self.get_primary_profile(project_id)
        if primary:
            return primary

        return self.create(
            project_id=project_id,
            profile_id="claude_code",
            platform="claude_code",
            root_dir=".claude",
            artifact_path_map={
                "skill": ".claude/skills",
                "command": ".claude/commands",
                "agent": ".claude/agents",
                "hook": ".claude/hooks",
                "mcp": ".claude/mcp",
            },
            config_filenames=["CLAUDE.md", "settings.json"],
            context_prefixes=[".claude/context/", ".claude/"],
            supported_types=["skill", "command", "agent", "hook", "mcp"],
        )

    def get_project_id_by_path(self, project_path: str) -> "Optional[str]":
        """Return the project ID for the given filesystem path.

        Delegates to the ``EnterpriseProject`` table.

        Parameters
        ----------
        project_path:
            Absolute path string to match against ``EnterpriseProject.path``.

        Returns
        -------
        str or None
            Project ID string when a matching row exists, ``None`` otherwise.
        """
        from skillmeat.cache.models_enterprise import EnterpriseProject

        tenant_id = self._get_tenant_id()
        stmt = select(EnterpriseProject).where(
            EnterpriseProject.tenant_id == tenant_id,
            EnterpriseProject.path == project_path,
        )
        row = self.session.execute(stmt).scalar_one_or_none()
        return str(row.id) if row else None

    # =========================================================================
    # Update
    # =========================================================================

    def update(
        self,
        project_id: str,
        profile_id: str,
        **updates: object,
    ) -> "Optional[EnterpriseDeploymentProfile]":
        """Update an existing deployment profile.

        Parameters
        ----------
        project_id:
            Project identifier.
        profile_id:
            Profile identifier string.
        **updates:
            Keyword arguments for fields to update.  Supported: ``platform``,
            ``dest_path``, ``scope``, ``overwrite``, ``extra_metadata``.
            Any key present in ``extra_metadata`` is merged in.

        Returns
        -------
        EnterpriseDeploymentProfile or None
            Updated instance, or ``None`` if not found.

        Raises
        ------
        Exception
            Re-raises any database error after rolling back.
        """
        profile = self.read_by_project_and_profile_id(project_id, profile_id)
        if profile is None:
            return None

        try:
            direct_fields = {"platform", "dest_path", "scope", "overwrite"}
            meta_updates: Dict[str, object] = {}

            for key, value in updates.items():
                if key in direct_fields and value is not None:
                    setattr(profile, key, value)
                elif key not in {"project_id", "profile_id"}:
                    meta_updates[key] = value

            if meta_updates:
                existing_meta = profile.extra_metadata or {}
                profile.extra_metadata = {**existing_meta, **meta_updates}

            profile.updated_at = datetime.utcnow()
            self.session.flush()
            logger.debug(
                "Updated EnterpriseDeploymentProfile name=%s/%s",
                project_id,
                profile_id,
            )
            self._log_operation(
                operation="update",
                entity_type="EnterpriseDeploymentProfile",
                entity_id=profile.id,
                metadata={"project_id": project_id, "profile_id": profile_id},
            )
            return profile
        except Exception:
            self.session.rollback()
            raise

    # =========================================================================
    # Delete
    # =========================================================================

    def delete(self, project_id: str, profile_id: str) -> bool:
        """Delete a deployment profile by project and profile ID.

        Parameters
        ----------
        project_id:
            Project identifier.
        profile_id:
            Profile identifier string.

        Returns
        -------
        bool
            ``True`` if found and deleted, ``False`` otherwise.

        Raises
        ------
        Exception
            Re-raises any database error after rolling back.
        """
        profile = self.read_by_project_and_profile_id(project_id, profile_id)
        if profile is None:
            return False

        try:
            self.session.delete(profile)
            self.session.flush()
            logger.debug(
                "Deleted EnterpriseDeploymentProfile name=%s/%s",
                project_id,
                profile_id,
            )
            self._log_operation(
                operation="delete",
                entity_type="EnterpriseDeploymentProfile",
                entity_id=profile.id,
                metadata={"project_id": project_id, "profile_id": profile_id},
            )
            return True
        except Exception:
            self.session.rollback()
            raise


# =============================================================================
# EnterpriseMarketplaceSourceRepository  (ENT2-5.1)
# =============================================================================


class EnterpriseMarketplaceSourceRepository(
    EnterpriseRepositoryBase["EnterpriseMarketplaceSource"],
):
    """Enterprise repository for marketplace source and catalog-entry operations.

    Implements
    :class:`~skillmeat.core.interfaces.repositories.IMarketplaceSourceRepository`
    for the enterprise PostgreSQL backend.

    The enterprise model (``EnterpriseMarketplaceSource``) is GitHub-repo-
    centric — each row represents a scanned GitHub repository — whereas the
    interface's :class:`~skillmeat.core.interfaces.dtos.MarketplaceSourceDTO`
    uses broker-centric terminology (``endpoint``, ``supports_publish``).
    The ``_source_to_dto`` helper bridges the two schemas by mapping:

    - ``repo_url`` → ``endpoint``
    - ``name`` synthesised as ``"owner/repo_name"``
    - ``scan_status == "done"`` → ``enabled = True``
    - ``supports_publish = False`` (GitHub repos are read-only sources)

    Catalog operations are backed by ``EnterpriseMarketplaceCatalogEntry``
    which has a leaner schema than the local SQLite catalog model (no
    ``excluded_at``, ``excluded_reason``, or ``path_segments`` columns).
    Methods that reference those local-only columns are implemented with
    best-effort equivalents using the available ``status`` column.

    Parameters
    ----------
    session:
        An open SQLAlchemy ``Session`` bound to the enterprise database.
        Lifecycle (commit/rollback/close) is managed by the caller.

    Notes
    -----
    * SQLAlchemy 2.x ``select()`` style throughout.
    * ``_apply_tenant_filter()`` is called on every query.
    * UUID primary keys for both sources and catalog entries.
    * ``import_item`` and ``get_composite_members`` are not directly
      supported by the enterprise schema; both return empty results and
      log a debug note.  Full implementation is deferred to v3.
    """

    def __init__(self, session: Session) -> None:
        """Initialise the enterprise marketplace source repository.

        Parameters
        ----------
        session:
            Injected SQLAlchemy session bound to the PostgreSQL enterprise
            database.
        """
        from skillmeat.cache.models_enterprise import EnterpriseMarketplaceSource

        super().__init__(session, EnterpriseMarketplaceSource)

    # ------------------------------------------------------------------
    # DTO helpers
    # ------------------------------------------------------------------

    def _source_to_dto(self, row: "EnterpriseMarketplaceSource") -> "MarketplaceSourceDTO":
        """Convert an ``EnterpriseMarketplaceSource`` ORM row to a DTO.

        Parameters
        ----------
        row:
            ORM instance to convert.

        Returns
        -------
        MarketplaceSourceDTO
        """
        from skillmeat.core.interfaces.dtos import MarketplaceSourceDTO

        name = (
            f"{row.owner}/{row.repo_name}"
            if row.owner and row.repo_name
            else (row.owner or row.repo_name or str(row.id))
        )
        enabled = row.scan_status in ("done", "success") if row.scan_status else False
        return MarketplaceSourceDTO(
            id=str(row.id),
            name=name,
            enabled=enabled,
            endpoint=row.repo_url or "",
            description=None,
            supports_publish=False,
            created_at=row.created_at.isoformat() if row.created_at else None,
            updated_at=row.updated_at.isoformat() if row.updated_at else None,
        )

    def _entry_to_catalog_dto(
        self, row: "EnterpriseMarketplaceCatalogEntry"
    ) -> "CatalogItemDTO":
        """Convert an ``EnterpriseMarketplaceCatalogEntry`` ORM row to a DTO.

        Parameters
        ----------
        row:
            ORM instance to convert.

        Returns
        -------
        CatalogItemDTO
        """
        from skillmeat.core.interfaces.dtos import CatalogItemDTO

        return CatalogItemDTO(
            listing_id=str(row.id),
            name=row.name or "",
            source_id=str(row.source_id),
            publisher=None,
            description=None,
            license=None,
            version=row.detected_sha,
            artifact_count=1,
            tags=[row.artifact_type] if row.artifact_type else [],
            source_url=row.upstream_url,
            bundle_url=None,
            signature=None,
            downloads=0,
            rating=None,
            price=None,
            created_at=row.created_at.isoformat() if row.created_at else None,
        )

    # ------------------------------------------------------------------
    # Source CRUD — IMarketplaceSourceRepository
    # ------------------------------------------------------------------

    def list_sources(
        self,
        filters: "Optional[Dict[str, object]]" = None,
        ctx: "Optional[object]" = None,
    ) -> "List[MarketplaceSourceDTO]":
        """Return all marketplace sources for the current tenant.

        Parameters
        ----------
        filters:
            Optional filter map.  Supported keys: ``enabled`` (bool).
        ctx:
            Optional per-request metadata (unused by enterprise backend).

        Returns
        -------
        list[MarketplaceSourceDTO]
        """
        from skillmeat.cache.models_enterprise import EnterpriseMarketplaceSource

        stmt = self._tenant_select().order_by(EnterpriseMarketplaceSource.created_at.asc())
        rows = list(self.session.execute(stmt).scalars())

        dtos = [self._source_to_dto(r) for r in rows]

        if filters and "enabled" in filters:
            want_enabled = bool(filters["enabled"])
            dtos = [d for d in dtos if d.enabled == want_enabled]

        return dtos

    def get_source(
        self,
        source_id: str,
        ctx: "Optional[object]" = None,
    ) -> "Optional[MarketplaceSourceDTO]":
        """Return a marketplace source by its identifier.

        Parameters
        ----------
        source_id:
            UUID string of the source row.
        ctx:
            Optional per-request metadata (unused by enterprise backend).

        Returns
        -------
        MarketplaceSourceDTO or None
        """
        from skillmeat.cache.models_enterprise import EnterpriseMarketplaceSource

        try:
            uid = uuid.UUID(source_id)
        except ValueError:
            logger.debug(
                "EnterpriseMarketplaceSourceRepository.get_source: invalid UUID %r",
                source_id,
            )
            return None

        stmt = self._apply_tenant_filter(
            select(EnterpriseMarketplaceSource).where(EnterpriseMarketplaceSource.id == uid)
        )
        row = self.session.execute(stmt).scalar_one_or_none()
        return self._source_to_dto(row) if row is not None else None

    def create_source(
        self,
        name: str,
        endpoint: str,
        enabled: bool = True,
        description: "Optional[str]" = None,
        supports_publish: bool = False,
        ctx: "Optional[object]" = None,
    ) -> "MarketplaceSourceDTO":
        """Register a new marketplace source.

        Maps the broker-centric interface fields onto the GitHub-repo-centric
        enterprise schema: ``endpoint`` is stored as ``repo_url``,
        ``name`` is parsed into ``owner``/``repo_name`` when it contains a
        ``"/"`` separator.  ``enabled`` is translated to an initial
        ``scan_status``.

        Parameters
        ----------
        name:
            Human-readable name (``"owner/repo"`` convention for GitHub repos).
        endpoint:
            Base URL for the broker API / repository URL.
        enabled:
            Whether to activate the source immediately.
        description:
            Ignored by the enterprise backend (no description column on source).
        supports_publish:
            Ignored by the enterprise backend (GitHub sources are read-only).
        ctx:
            Optional per-request metadata (unused by enterprise backend).

        Returns
        -------
        MarketplaceSourceDTO
            The created source.

        Raises
        ------
        ValueError
            If a source with the same ``endpoint`` (repo URL) already exists
            for this tenant.
        """
        from skillmeat.cache.models_enterprise import EnterpriseMarketplaceSource

        # Check uniqueness within tenant.
        existing_stmt = self._apply_tenant_filter(
            select(EnterpriseMarketplaceSource).where(
                EnterpriseMarketplaceSource.repo_url == endpoint
            )
        )
        existing = self.session.execute(existing_stmt).scalar_one_or_none()
        if existing is not None:
            raise ValueError(
                f"A marketplace source with endpoint {endpoint!r} already exists "
                f"for this tenant (id={existing.id})."
            )

        tenant_id = self._get_tenant_id()
        now = datetime.utcnow()

        # Parse owner / repo_name from the name field if possible.
        owner: Optional[str] = None
        repo_name: Optional[str] = None
        if "/" in name:
            parts = name.split("/", 1)
            owner = parts[0] or None
            repo_name = parts[1] or None

        # Translate ``enabled`` to an initial scan_status.
        initial_scan_status = "pending" if enabled else "disabled"

        row = EnterpriseMarketplaceSource(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            repo_url=endpoint,
            owner=owner,
            repo_name=repo_name or name,
            ref="main",
            scan_status=initial_scan_status,
            artifact_count=0,
            created_at=now,
            updated_at=now,
        )
        try:
            self.session.add(row)
            self.session.flush()
            self._log_operation(
                operation="create",
                entity_type="EnterpriseMarketplaceSource",
                entity_id=row.id,
                metadata={"name": name, "endpoint": endpoint},
            )
            return self._source_to_dto(row)
        except Exception:
            self.session.rollback()
            raise

    def update_source(
        self,
        source_id: str,
        updates: "Dict[str, object]",
        ctx: "Optional[object]" = None,
    ) -> "MarketplaceSourceDTO":
        """Apply a partial update to a marketplace source configuration.

        Recognised update keys: ``enabled`` (bool), ``endpoint`` (str),
        ``description`` (ignored — no column), ``supports_publish`` (ignored).
        Additional keys in ``updates`` are silently ignored to avoid errors
        when the caller passes broker-centric fields not present in the
        enterprise schema.

        Parameters
        ----------
        source_id:
            UUID string of the source to update.
        updates:
            Map of field names to new values.
        ctx:
            Optional per-request metadata (unused by enterprise backend).

        Returns
        -------
        MarketplaceSourceDTO
            The updated source.

        Raises
        ------
        KeyError
            If no source with *source_id* exists for this tenant.
        """
        from skillmeat.cache.models_enterprise import EnterpriseMarketplaceSource

        try:
            uid = uuid.UUID(source_id)
        except ValueError:
            raise KeyError(source_id)

        stmt = self._apply_tenant_filter(
            select(EnterpriseMarketplaceSource).where(EnterpriseMarketplaceSource.id == uid)
        )
        row = self.session.execute(stmt).scalar_one_or_none()
        if row is None:
            raise KeyError(source_id)

        if "enabled" in updates:
            row.scan_status = "pending" if updates["enabled"] else "disabled"
        if "endpoint" in updates:
            row.repo_url = str(updates["endpoint"])
        if "ref" in updates:
            row.ref = str(updates["ref"])
        if "scan_status" in updates:
            row.scan_status = str(updates["scan_status"])

        row.updated_at = datetime.utcnow()

        try:
            self.session.flush()
            self._log_operation(
                operation="update",
                entity_type="EnterpriseMarketplaceSource",
                entity_id=row.id,
                metadata={k: str(v)[:80] for k, v in updates.items()},
            )
            return self._source_to_dto(row)
        except Exception:
            self.session.rollback()
            raise

    def delete_source(
        self,
        source_id: str,
        ctx: "Optional[object]" = None,
    ) -> None:
        """Remove a marketplace source configuration.

        Cascade-deletes all associated catalog entries (via the FK
        ``ON DELETE CASCADE`` on ``enterprise_marketplace_catalog_entries``).

        Parameters
        ----------
        source_id:
            UUID string of the source to remove.
        ctx:
            Optional per-request metadata (unused by enterprise backend).

        Raises
        ------
        KeyError
            If no source with *source_id* exists for this tenant.
        """
        from skillmeat.cache.models_enterprise import EnterpriseMarketplaceSource

        try:
            uid = uuid.UUID(source_id)
        except ValueError:
            raise KeyError(source_id)

        stmt = self._apply_tenant_filter(
            select(EnterpriseMarketplaceSource).where(EnterpriseMarketplaceSource.id == uid)
        )
        row = self.session.execute(stmt).scalar_one_or_none()
        if row is None:
            raise KeyError(source_id)

        try:
            self.session.delete(row)
            self.session.flush()
            self._log_operation(
                operation="delete",
                entity_type="EnterpriseMarketplaceSource",
                entity_id=uid,
                metadata={"source_id": source_id},
            )
        except Exception:
            self.session.rollback()
            raise

    # ------------------------------------------------------------------
    # Catalog operations — IMarketplaceSourceRepository
    # ------------------------------------------------------------------

    def list_catalog_items(
        self,
        source_id: "Optional[str]" = None,
        filters: "Optional[Dict[str, object]]" = None,
        page: int = 1,
        limit: int = 50,
        ctx: "Optional[object]" = None,
    ) -> "List[CatalogItemDTO]":
        """Return paginated catalog listings from one or all sources.

        Parameters
        ----------
        source_id:
            When provided, restrict results to entries belonging to this
            source UUID.  When ``None`` all tenant catalog entries are returned.
        filters:
            Optional filter map.  Supported keys: ``query`` (substring match
            on ``name``), ``artifact_type``.
        page:
            One-based page number.
        limit:
            Maximum results per page (1-100).
        ctx:
            Optional per-request metadata (unused by enterprise backend).

        Returns
        -------
        list[CatalogItemDTO]
        """
        from skillmeat.cache.models_enterprise import EnterpriseMarketplaceCatalogEntry

        stmt = self._apply_tenant_filter(
            select(EnterpriseMarketplaceCatalogEntry)
        ).order_by(EnterpriseMarketplaceCatalogEntry.created_at.desc())

        if source_id is not None:
            try:
                src_uid = uuid.UUID(source_id)
                stmt = stmt.where(EnterpriseMarketplaceCatalogEntry.source_id == src_uid)
            except ValueError:
                logger.debug(
                    "EnterpriseMarketplaceSourceRepository.list_catalog_items: "
                    "invalid source_id UUID %r — returning empty list",
                    source_id,
                )
                return []

        if filters:
            if "query" in filters and filters["query"]:
                q = f"%{filters['query']}%"
                stmt = stmt.where(EnterpriseMarketplaceCatalogEntry.name.ilike(q))
            if "artifact_type" in filters and filters["artifact_type"]:
                stmt = stmt.where(
                    EnterpriseMarketplaceCatalogEntry.artifact_type == filters["artifact_type"]
                )

        offset = (max(1, page) - 1) * limit
        stmt = stmt.offset(offset).limit(limit)

        rows = list(self.session.execute(stmt).scalars())
        return [self._entry_to_catalog_dto(r) for r in rows]

    def import_item(
        self,
        listing_id: str,
        source_id: "Optional[str]" = None,
        strategy: str = "keep",
        ctx: "Optional[object]" = None,
    ) -> "List[ArtifactDTO]":
        """Download and import a marketplace listing.

        .. note::
            Full import orchestration is not implemented at the enterprise DB
            repository layer (it requires the CLI/source pipeline).  This
            method logs a debug note and returns an empty list.  The API
            layer's ``MarketplaceBrokerService`` handles the actual import
            flow independently of this repository.

        Parameters
        ----------
        listing_id:
            Catalog entry primary key.
        source_id:
            Optional source UUID string.
        strategy:
            Conflict resolution strategy (unused by this stub).
        ctx:
            Optional per-request metadata.

        Returns
        -------
        list[ArtifactDTO]
            Always empty — import orchestration is handled outside this repo.
        """
        logger.debug(
            "EnterpriseMarketplaceSourceRepository.import_item: "
            "import orchestration is deferred to the broker service layer; "
            "listing_id=%r source_id=%r",
            listing_id,
            source_id,
        )
        return []

    def get_composite_members(
        self,
        composite_id: str,
        ctx: "Optional[object]" = None,
    ) -> "List[ArtifactDTO]":
        """Return child artifacts for a composite listing.

        .. note::
            Composite membership tracking is not modelled in the enterprise
            schema.  Returns an empty list and logs a debug note.

        Parameters
        ----------
        composite_id:
            Artifact primary key of the composite artifact.
        ctx:
            Optional per-request metadata.

        Returns
        -------
        list[ArtifactDTO]
            Always empty.
        """
        logger.debug(
            "EnterpriseMarketplaceSourceRepository.get_composite_members: "
            "composite membership not modelled in enterprise schema; "
            "composite_id=%r",
            composite_id,
        )
        return []

    def get_catalog_entry_raw(
        self,
        entry_id: str,
        source_id: "Optional[str]" = None,
        ctx: "Optional[object]" = None,
    ) -> "Optional[object]":
        """Return the raw ORM catalog entry for read-only inspection.

        Parameters
        ----------
        entry_id:
            UUID string of the catalog entry.
        source_id:
            When provided, verify the entry belongs to this source.
        ctx:
            Optional per-request metadata.

        Returns
        -------
        EnterpriseMarketplaceCatalogEntry or None
        """
        from skillmeat.cache.models_enterprise import EnterpriseMarketplaceCatalogEntry

        try:
            entry_uid = uuid.UUID(entry_id)
        except ValueError:
            return None

        stmt = self._apply_tenant_filter(
            select(EnterpriseMarketplaceCatalogEntry).where(
                EnterpriseMarketplaceCatalogEntry.id == entry_uid
            )
        )
        row = self.session.execute(stmt).scalar_one_or_none()

        if row is None:
            return None

        if source_id is not None:
            try:
                src_uid = uuid.UUID(source_id)
            except ValueError:
                return None
            if row.source_id != src_uid:
                return None

        return row

    def update_catalog_entry_exclusion(
        self,
        entry_id: str,
        source_id: str,
        excluded: bool,
        reason: "Optional[str]" = None,
        ctx: "Optional[object]" = None,
    ) -> "object":
        """Toggle the exclusion status of a catalog entry.

        The enterprise schema has no ``excluded_at`` or ``excluded_reason``
        columns.  Exclusion is approximated by setting ``status`` to
        ``"excluded"`` (when *excluded* is ``True``) or reverting to
        ``"available"`` (when *excluded* is ``False``).

        Parameters
        ----------
        entry_id:
            UUID string of the catalog entry.
        source_id:
            Source the entry must belong to.
        excluded:
            ``True`` to exclude, ``False`` to restore.
        reason:
            Ignored by the enterprise backend (no ``excluded_reason`` column).
        ctx:
            Optional per-request metadata.

        Returns
        -------
        EnterpriseMarketplaceCatalogEntry
            The updated ORM instance.

        Raises
        ------
        KeyError
            If *entry_id* is not found or does not belong to *source_id*.
        """
        row = self.get_catalog_entry_raw(entry_id, source_id=source_id, ctx=ctx)
        if row is None:
            raise KeyError(entry_id)

        row.status = "excluded" if excluded else "available"
        row.updated_at = datetime.utcnow()

        try:
            self.session.flush()
            self._log_operation(
                operation="update_exclusion",
                entity_type="EnterpriseMarketplaceCatalogEntry",
                entity_id=row.id,
                metadata={"excluded": excluded, "reason": reason},
            )
            return row
        except Exception:
            self.session.rollback()
            raise

    def update_catalog_entry_path_tags(
        self,
        entry_id: str,
        source_id: str,
        path_segments_json: str,
        ctx: "Optional[object]" = None,
    ) -> "object":
        """Persist updated path_segments for a catalog entry.

        The enterprise schema has no ``path_segments`` column.  This method
        records the operation via audit log for traceability but does not
        write the JSON to a column.  The catalog entry's ``updated_at`` is
        refreshed so that callers can detect a change.

        Parameters
        ----------
        entry_id:
            UUID string of the catalog entry.
        source_id:
            Source the entry must belong to.
        path_segments_json:
            Serialised JSON (logged only; no enterprise column stores it).
        ctx:
            Optional per-request metadata.

        Returns
        -------
        EnterpriseMarketplaceCatalogEntry
            The ORM instance with a refreshed ``updated_at``.

        Raises
        ------
        KeyError
            If *entry_id* is not found or does not belong to *source_id*.
        """
        row = self.get_catalog_entry_raw(entry_id, source_id=source_id, ctx=ctx)
        if row is None:
            raise KeyError(entry_id)

        logger.debug(
            "EnterpriseMarketplaceSourceRepository.update_catalog_entry_path_tags: "
            "path_segments column not present in enterprise schema; "
            "entry_id=%r path_segments_json=%r",
            entry_id,
            path_segments_json,
        )
        row.updated_at = datetime.utcnow()

        try:
            self.session.flush()
            self._log_operation(
                operation="update_path_tags",
                entity_type="EnterpriseMarketplaceCatalogEntry",
                entity_id=row.id,
                metadata={"path_segments_json": path_segments_json[:200]},
            )
            return row
        except Exception:
            self.session.rollback()
            raise

    def get_artifact_row(
        self,
        artifact_id: str,
        ctx: "Optional[object]" = None,
    ) -> "Optional[object]":
        """Return the raw ORM Artifact row for the given type:name id.

        .. note::
            The enterprise marketplace source repository does not hold
            ``Artifact`` rows — those are managed by
            :class:`EnterpriseArtifactRepository`.  This method always
            returns ``None`` and logs a debug note.

        Parameters
        ----------
        artifact_id:
            Artifact primary key in ``"type:name"`` format.
        ctx:
            Optional per-request metadata.

        Returns
        -------
        None
            Always ``None`` — enterprise marketplace sources do not own Artifact
            rows.
        """
        logger.debug(
            "EnterpriseMarketplaceSourceRepository.get_artifact_row: "
            "Artifact rows are not managed by the marketplace source repo in the "
            "enterprise backend; artifact_id=%r",
            artifact_id,
        )
        return None

    def upsert_composite_memberships(
        self,
        composite_id: str,
        child_artifact_ids: "List[str]",
        collection_id: str,
        ctx: "Optional[object]" = None,
    ) -> int:
        """Create or update CompositeMembership rows for a composite artifact.

        .. note::
            Composite membership is not modelled in the enterprise schema.
            Returns 0 and logs a debug note.

        Parameters
        ----------
        composite_id:
            Primary key of the composite artifact.
        child_artifact_ids:
            Ordered list of child ``type:name`` artifact primary keys.
        collection_id:
            Collection the composite belongs to.
        ctx:
            Optional per-request metadata.

        Returns
        -------
        int
            Always 0.
        """
        logger.debug(
            "EnterpriseMarketplaceSourceRepository.upsert_composite_memberships: "
            "composite membership not modelled in enterprise schema; "
            "composite_id=%r child_count=%d",
            composite_id,
            len(child_artifact_ids),
        )
        return 0

    def commit_source_session(
        self,
        ctx: "Optional[object]" = None,
    ) -> None:
        """Flush pending changes on the source repository session.

        Parameters
        ----------
        ctx:
            Optional per-request metadata (unused by enterprise backend).
        """
        try:
            self.session.flush()
        except Exception:
            self.session.rollback()
            raise


# =============================================================================
# EnterpriseProjectTemplateRepository  (ENT2-5.2)
# =============================================================================


class EnterpriseProjectTemplateRepository(
    EnterpriseRepositoryBase["EnterpriseRepositoryBase"],
):
    """Safe stub for project template operations in the enterprise backend.

    Implements
    :class:`~skillmeat.core.interfaces.repositories.IProjectTemplateRepository`
    for the enterprise PostgreSQL backend.

    .. note::
        Full implementation is deferred to v3.  No database queries are
        issued; all methods return empty collections or ``None`` and emit
        a ``DEBUG`` log so callers know the stub was reached.

    Parameters
    ----------
    session:
        An open SQLAlchemy ``Session`` bound to the enterprise database.
        The session is stored but never queried by this stub.
    """

    def __init__(self, session: Session) -> None:
        """Initialise the enterprise project template repository stub.

        Parameters
        ----------
        session:
            Injected SQLAlchemy session.  Stored for interface compliance;
            not used by any stub method.
        """
        # Use type(None) as a sentinel model_class; no DB queries are issued
        # so this value is never passed to _apply_tenant_filter.  We pass it
        # only to satisfy the Generic[T] contract of EnterpriseRepositoryBase.
        super().__init__(session, type(None))  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # IProjectTemplateRepository: collection queries
    # ------------------------------------------------------------------

    def list(
        self,
        filters: "Optional[Dict[str, object]]" = None,
        limit: int = 50,
        offset: int = 0,
        ctx: "Optional[object]" = None,
    ) -> "List[ProjectTemplateDTO]":
        """Return a page of project templates.

        Returns
        -------
        list[ProjectTemplateDTO]
            Always empty — full implementation deferred to v3.
        """
        logger.debug(
            "EnterpriseProjectTemplateRepository: stub — full implementation deferred to v3"
        )
        return []

    def count(
        self,
        filters: "Optional[Dict[str, object]]" = None,
        ctx: "Optional[object]" = None,
    ) -> int:
        """Return the total number of project templates.

        Returns
        -------
        int
            Always 0 — full implementation deferred to v3.
        """
        logger.debug(
            "EnterpriseProjectTemplateRepository: stub — full implementation deferred to v3"
        )
        return 0

    # ------------------------------------------------------------------
    # IProjectTemplateRepository: single-item lookup
    # ------------------------------------------------------------------

    def get(
        self,
        template_id: str,
        ctx: "Optional[object]" = None,
    ) -> "Optional[ProjectTemplateDTO]":
        """Return a project template by its identifier.

        Returns
        -------
        None
            Always None — full implementation deferred to v3.
        """
        logger.debug(
            "EnterpriseProjectTemplateRepository: stub — full implementation deferred to v3"
        )
        return None

    # ------------------------------------------------------------------
    # IProjectTemplateRepository: mutations
    # ------------------------------------------------------------------

    def create(
        self,
        name: str,
        entity_ids: "List[str]",
        description: "Optional[str]" = None,
        collection_id: "Optional[str]" = None,
        default_project_config_id: "Optional[str]" = None,
        ctx: "Optional[object]" = None,
    ) -> "ProjectTemplateDTO":
        """Create a new project template.

        Returns a minimal stub DTO.  No data is persisted.

        Returns
        -------
        ProjectTemplateDTO
            Minimal stub DTO — full implementation deferred to v3.
        """
        logger.debug(
            "EnterpriseProjectTemplateRepository: stub — full implementation deferred to v3"
        )
        from skillmeat.core.interfaces.dtos import ProjectTemplateDTO

        return ProjectTemplateDTO(
            id="",
            name=name,
            description=description,
            collection_id=collection_id,
            default_project_config_id=default_project_config_id,
            entities=[],
            entity_count=0,
        )

    def update(
        self,
        template_id: str,
        updates: "Dict[str, object]",
        ctx: "Optional[object]" = None,
    ) -> "ProjectTemplateDTO":
        """Apply a partial update to an existing project template.

        Raises
        ------
        KeyError
            Always — no templates are stored in this stub.
        """
        logger.debug(
            "EnterpriseProjectTemplateRepository: stub — full implementation deferred to v3"
        )
        raise KeyError(template_id)

    def delete(
        self,
        template_id: str,
        ctx: "Optional[object]" = None,
    ) -> None:
        """Delete a project template.

        No-op stub.  Logs a debug message and returns silently.
        """
        logger.debug(
            "EnterpriseProjectTemplateRepository: stub — full implementation deferred to v3"
        )

    # ------------------------------------------------------------------
    # IProjectTemplateRepository: deployment
    # ------------------------------------------------------------------

    def deploy(
        self,
        template_id: str,
        project_path: str,
        options: "Optional[Dict[str, object]]" = None,
        ctx: "Optional[object]" = None,
    ) -> "Dict[str, object]":
        """Deploy template entities to a target project directory.

        Returns
        -------
        dict
            Minimal result dict indicating no files were deployed.
        """
        logger.debug(
            "EnterpriseProjectTemplateRepository: stub — full implementation deferred to v3"
        )
        return {
            "success": False,
            "deployed_files": [],
            "skipped_files": [],
            "message": (
                "EnterpriseProjectTemplateRepository is a stub; "
                "full implementation deferred to v3."
            ),
        }
