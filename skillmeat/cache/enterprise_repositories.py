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
from typing import TYPE_CHECKING, Dict, Generator, Generic, List, Optional, Type, TypeVar

from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from skillmeat.cache.constants import DEFAULT_TENANT_ID

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

        self._apply_auth_context(auth_context)
        parsed: uuid.UUID = uuid.UUID(artifact_uuid)
        stmt = self._tenant_select().where(EnterpriseArtifact.id == parsed)
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

        self._apply_auth_context(auth_context)
        stmt = (
            self._tenant_select()
            .where(EnterpriseArtifact.name == name)
            .order_by(EnterpriseArtifact.created_at)
            .limit(1)
        )
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

        self._apply_auth_context(auth_context)
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

        return list(self.session.execute(stmt).scalars().all())

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
        artifact = self.get(artifact_id)
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
        artifact = self.get(artifact_id)
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
        self, artifact_id: uuid.UUID
    ) -> "Optional[EnterpriseArtifact]":
        """Return an EnterpriseArtifact if it exists and belongs to the current tenant.

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
        """Return the artifacts in a collection, ordered by position.

        Parameters
        ----------
        collection_id:
            UUID of the collection.
        auth_context:
            Optional authentication context.  When provided, sets the active
            tenant via ``TenantContext`` before the ownership check.

        Returns
        -------
        List[EnterpriseArtifact]
            Artifacts ordered by ``order_index`` ascending.

        Raises
        ------
        TenantIsolationError
            If the collection belongs to a different tenant.
        """
        from skillmeat.cache.models_enterprise import (
            EnterpriseArtifact,
            EnterpriseCollectionArtifact,
        )

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
        return True
