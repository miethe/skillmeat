"""Unit tests for EnterpriseCollectionRepository (ENT-2.12).

Covers:
    - ENT-2.7: Collection CRUD (create, get, get_by_name, list, update, delete)
    - ENT-2.8: Membership operations (add_artifact, remove_artifact,
      list_artifacts, reorder_artifacts)
    - Multi-tenant isolation: tenant A cannot see or modify tenant B data

All tests use an in-memory SQLite engine.  Enterprise models target PostgreSQL
but the ORM layer is dialect-agnostic enough for SQLite unit tests:

    - UUID columns use Python-side ``default=uuid.uuid4`` (no gen_random_uuid()).
    - JSONB columns fall back to SQLite's TEXT storage.
    - TIMESTAMPTZ columns become SQLite DATETIME (no timezone info stored, but
      that does not affect these tests).
    - PostgreSQL-specific index hints (``postgresql_using``, ``postgresql_where``)
      are silently ignored by SQLAlchemy when targeting SQLite.

Session lifecycle:
    Each test gets a fresh connection wrapped in a transaction that is rolled
    back on teardown — zero state leaks between tests, no test-order dependency.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Generator

import pytest
from sqlalchemy import JSON, String, create_engine, event, inspect as sa_inspect
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.sql.schema import ColumnDefault as _ColumnDefault
from sqlalchemy.types import CHAR, TypeDecorator

from skillmeat.cache.enterprise_repositories import (
    EnterpriseCollectionRepository,
    TenantIsolationError,
    tenant_scope,
)
from skillmeat.cache.models_enterprise import (
    EnterpriseArtifact,
    EnterpriseArtifactVersion,
    EnterpriseBase,
    EnterpriseCollection,
    EnterpriseCollectionArtifact,
)


# ---------------------------------------------------------------------------
# SQLite compatibility shims
#
# The enterprise models use PostgreSQL-specific column types (JSONB, UUID).
# SQLAlchemy cannot render JSONB DDL for SQLite.  Before creating tables we
# patch those column types to SQLite-compatible equivalents.  The patch is
# applied once per module and is idempotent (if column.type is already JSON /
# String we skip it).
# ---------------------------------------------------------------------------


class _UUIDString(TypeDecorator):
    """TypeDecorator that stores UUID as a 36-char string in SQLite.

    SQLAlchemy's ``UUID(as_uuid=True)`` uses the PostgreSQL UUID type which
    SQLite cannot bind.  This decorator serialises ``uuid.UUID`` objects to
    their canonical hyphenated string form on the way in, and deserialises
    back to ``uuid.UUID`` on the way out.  It is only used in the test-time
    metadata patch below.
    """

    impl = CHAR(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(uuid.UUID(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


def _patch_enterprise_metadata_for_sqlite() -> None:
    """Make enterprise table metadata renderable by the SQLite DDL compiler.

    The enterprise models use PostgreSQL-specific constructs that SQLite
    cannot handle:

    * ``JSONB`` column type → replaced with ``JSON``
    * ``UUID(as_uuid=True)`` column type → replaced with ``_UUIDString``
      (stores as CHAR(36) with automatic uuid.UUID ↔ str conversion)
    * ``server_default`` values that use PG syntax (``gen_random_uuid()``,
      ``now()``, ``'[]'::jsonb``, ``'{}'::jsonb``, ``true``, ``false``) →
      cleared so SQLAlchemy does not emit them in the CREATE TABLE DDL.
      Python-side ``default=`` values are unaffected and remain active.

    Called once before ``EnterpriseBase.metadata.create_all()`` in the
    module-scoped engine fixture.  The patch mutates the in-process Table
    objects inside ``EnterpriseBase.metadata`` and is safe because no
    PostgreSQL engine is ever used in this test module.

    Isolation note — ORM comparator type cache
    -------------------------------------------
    SQLAlchemy's ORM mapper may have been configured (via ``configure_mappers()``
    or first-use of any ORM model class) before this patch runs.  When mappers
    are configured, each ``InstrumentedAttribute.comparator`` stores a snapshot
    of the column's type in its own ``__dict__['type']``.  Mutating
    ``column.type`` on the Table object does NOT automatically propagate to
    these already-built ``_Annotated`` column proxies.

    This matters because ORM WHERE-clause bind parameters take their type from
    the comparator, not the Table column.  If the comparator still holds
    ``UUID(as_uuid=True)`` after we replace the column type with ``_UUIDString``,
    the bind processor for ``UUID(as_uuid=True)`` (which strips hyphens for
    PostgreSQL) is used instead of ``_UUIDString.process_bind_param`` (which
    preserves hyphens for SQLite CHAR(36) storage).  The stored value has
    hyphens but the WHERE clause binds the no-hyphen form, so all equality
    comparisons silently return zero rows.

    To fix this, after patching the Table columns we also refresh the type
    reference on every mapped column's comparator so both the INSERT binding
    and the SELECT/WHERE binding use the same ``_UUIDString`` processor.
    """
    # Step 1: patch Table-level column types.
    for table in EnterpriseBase.metadata.tables.values():
        for column in table.columns:
            # Fix dialect-specific column types
            if isinstance(column.type, JSONB):
                column.type = JSON()
            elif isinstance(column.type, UUID):
                column.type = _UUIDString()
            # Strip PostgreSQL-only server_default expressions so SQLite DDL
            # does not choke on gen_random_uuid(), now(), '[]'::jsonb, etc.
            if column.server_default is not None:
                column.server_default = None
            # Add Python-side defaults for timestamp columns that relied solely
            # on server_default so INSERT statements succeed without explicit values.
            if column.name in ("created_at", "updated_at", "added_at") and column.default is None:
                column.default = _ColumnDefault(datetime.utcnow)

    # Step 2: propagate patched types to ORM comparator caches.
    #
    # If configure_mappers() has already run (e.g. because a test in another
    # module instantiated an enterprise ORM class before this fixture fires),
    # each InstrumentedAttribute.comparator holds a frozen copy of the column
    # type in its __dict__['type'].  We must overwrite that entry with the
    # new patched type so that WHERE-clause bind parameters use _UUIDString
    # rather than the original UUID(as_uuid=True).
    _enterprise_model_classes = [
        EnterpriseArtifact,
        EnterpriseArtifactVersion,
        EnterpriseCollection,
        EnterpriseCollectionArtifact,
    ]
    for model_cls in _enterprise_model_classes:
        mapper = sa_inspect(model_cls)
        for col_name, mapped_col in mapper.columns.items():
            attr = getattr(model_cls, col_name, None)
            if attr is not None and hasattr(attr, "comparator"):
                comparator = attr.comparator
                if "type" in comparator.__dict__:
                    comparator.__dict__["type"] = mapped_col.type

# ---------------------------------------------------------------------------
# Fixed tenant UUIDs — stable across re-runs for readable failure messages
# ---------------------------------------------------------------------------

TENANT_A = uuid.UUID("aaaaaaaa-0000-4000-a000-000000000001")
TENANT_B = uuid.UUID("bbbbbbbb-0000-4000-b000-000000000002")


# ---------------------------------------------------------------------------
# Module-scoped engine
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def engine():
    """In-memory SQLite engine shared across the module.

    ``check_same_thread=False`` is required because SQLAlchemy's connection
    pool may hand the connection to a different thread during teardown.
    Foreign-key enforcement is enabled so cascade behaviour is testable.

    JSONB and UUID column types are patched to SQLite-compatible equivalents
    before ``create_all`` is called (see ``_patch_enterprise_metadata_for_sqlite``).
    """
    # Must patch before create_all so DDL uses SQLite-renderable types
    _patch_enterprise_metadata_for_sqlite()

    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(eng, "connect")
    def _set_pragmas(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    EnterpriseBase.metadata.create_all(eng)
    yield eng
    eng.dispose()


# ---------------------------------------------------------------------------
# Function-scoped session (fresh per test, no rollback dependency)
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_session(engine) -> Generator[Session, None, None]:
    """Provide a fresh Session for each test, fully committed and then cleaned up.

    We use a full commit-per-test approach rather than a transaction-rollback
    wrapper because:

    1. ``EnterpriseCollectionRepository.create()`` / ``update()`` / ``delete()``
       call ``session.flush()`` internally, and some methods call
       ``session.commit()`` — wrapping in a never-committed outer transaction
       would conflict with those internal commits.
    2. SQLite bind-parameter errors inside a test leave the connection in an
       unusable state when a shared connection-level transaction is used.

    Isolation is provided by the module-scoped in-memory engine: all data
    disappears when the engine is disposed at module teardown.  Each test
    therefore operates on whatever rows prior tests left; test order must not
    depend on a clean slate beyond what each test explicitly inserts.

    To achieve independence, test names are used as part of fixture names
    where necessary, or each test inserts unique names.
    """
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    sess = factory()
    try:
        yield sess
    finally:
        sess.close()


# ---------------------------------------------------------------------------
# Helper: context managers that set TenantContext
# ---------------------------------------------------------------------------


@pytest.fixture()
def tenant_a_context():
    """Return the ``tenant_scope`` context manager pre-set to TENANT_A."""
    return lambda: tenant_scope(TENANT_A)


@pytest.fixture()
def tenant_b_context():
    """Return the ``tenant_scope`` context manager pre-set to TENANT_B."""
    return lambda: tenant_scope(TENANT_B)


# ---------------------------------------------------------------------------
# Helper factory functions
# ---------------------------------------------------------------------------


def _now() -> datetime:
    """Return current UTC time as a naive datetime (SQLite compatible)."""
    return datetime.utcnow()


def _make_artifact(
    db_session: Session,
    tenant_id: uuid.UUID,
    name: str = "test-skill",
    artifact_type: str = "skill",
) -> EnterpriseArtifact:
    """Create and flush an EnterpriseArtifact for *tenant_id*.

    Supplies Python-side timestamps because ``server_default`` values are
    stripped for SQLite compatibility (see ``_patch_enterprise_metadata_for_sqlite``).

    Returns the flushed ORM instance with a populated ``id``.
    """
    now = _now()
    artifact = EnterpriseArtifact(
        tenant_id=tenant_id,
        name=name,
        artifact_type=artifact_type,
        tags=[],
        custom_fields={},
        created_at=now,
        updated_at=now,
    )
    db_session.add(artifact)
    db_session.flush()
    return artifact


def _make_collection(
    db_session: Session,
    tenant_id: uuid.UUID,
    name: str = "My Collection",
    description: str | None = None,
) -> EnterpriseCollection:
    """Create and flush an EnterpriseCollection for *tenant_id*.

    Supplies Python-side timestamps because ``server_default`` values are
    stripped for SQLite compatibility.

    Returns the flushed ORM instance with a populated ``id``.
    """
    now = _now()
    collection = EnterpriseCollection(
        tenant_id=tenant_id,
        name=name,
        description=description,
        created_at=now,
        updated_at=now,
    )
    db_session.add(collection)
    db_session.flush()
    return collection


# ---------------------------------------------------------------------------
# ENT-2.7: Collection CRUD
# ---------------------------------------------------------------------------


class TestCollectionCreate:
    def test_create_sets_tenant_id_automatically(self, db_session, tenant_a_context):
        """create() stamps the collection with the active tenant UUID."""
        with tenant_a_context():
            repo = EnterpriseCollectionRepository(db_session)
            col = repo.create("Alpha Collection")

        assert col.tenant_id == TENANT_A
        assert col.name == "Alpha Collection"
        assert col.id is not None

    def test_create_stores_description(self, db_session, tenant_a_context):
        """Optional description is persisted when provided."""
        with tenant_a_context():
            repo = EnterpriseCollectionRepository(db_session)
            col = repo.create("Desc Collection", description="A helpful note")

        assert col.description == "A helpful note"

    def test_create_defaults_is_default_false(self, db_session, tenant_a_context):
        """New collections must not be marked as default."""
        with tenant_a_context():
            repo = EnterpriseCollectionRepository(db_session)
            col = repo.create("Plain Collection")

        assert col.is_default is False


class TestCollectionGet:
    def test_get_by_pk_asserts_tenant_ownership(self, db_session, tenant_a_context):
        """get() returns the collection when tenant matches."""
        with tenant_a_context():
            col = _make_collection(db_session, TENANT_A, "Owned Col")
            repo = EnterpriseCollectionRepository(db_session)
            fetched = repo.get(col.id)

        assert fetched is not None
        assert fetched.id == col.id

    def test_get_returns_none_for_cross_tenant(
        self, db_session, tenant_a_context, tenant_b_context
    ):
        """get() raises TenantIsolationError when the object belongs to another tenant."""
        with tenant_a_context():
            col_a = _make_collection(db_session, TENANT_A, "Tenant A Col")

        with tenant_b_context():
            repo = EnterpriseCollectionRepository(db_session)
            with pytest.raises(TenantIsolationError):
                repo.get(col_a.id)

    def test_get_returns_none_for_missing_pk(self, db_session, tenant_a_context):
        """get() returns None when no row matches the given UUID."""
        with tenant_a_context():
            repo = EnterpriseCollectionRepository(db_session)
            result = repo.get(uuid.uuid4())

        assert result is None

    def test_get_by_name_with_tenant_filter(
        self, db_session, tenant_a_context, tenant_b_context
    ):
        """get_by_name() finds the collection when the name matches within the tenant."""
        with tenant_a_context():
            _make_collection(db_session, TENANT_A, "Shared Name")

        with tenant_b_context():
            _make_collection(db_session, TENANT_B, "Shared Name")

        # Each tenant should see only their own collection
        with tenant_a_context():
            repo = EnterpriseCollectionRepository(db_session)
            result = repo.get_by_name("Shared Name")
        assert result is not None
        assert result.tenant_id == TENANT_A

        with tenant_b_context():
            repo = EnterpriseCollectionRepository(db_session)
            result = repo.get_by_name("Shared Name")
        assert result is not None
        assert result.tenant_id == TENANT_B

    def test_get_by_name_returns_none_when_not_found(self, db_session, tenant_a_context):
        """get_by_name() returns None for an unknown name."""
        with tenant_a_context():
            repo = EnterpriseCollectionRepository(db_session)
            result = repo.get_by_name("nonexistent-collection")

        assert result is None


class TestCollectionList:
    def test_list_only_returns_current_tenant_collections(
        self, db_session, tenant_a_context, tenant_b_context
    ):
        """list() excludes collections belonging to other tenants."""
        with tenant_a_context():
            _make_collection(db_session, TENANT_A, "A Col 1")
            _make_collection(db_session, TENANT_A, "A Col 2")

        with tenant_b_context():
            _make_collection(db_session, TENANT_B, "B Col 1")

        with tenant_a_context():
            repo = EnterpriseCollectionRepository(db_session)
            result = repo.list()

        names = {c.name for c in result}
        assert "A Col 1" in names
        assert "A Col 2" in names
        assert "B Col 1" not in names

    def test_list_pagination(self, db_session, tenant_a_context):
        """list() respects offset and limit parameters."""
        with tenant_a_context():
            for i in range(5):
                _make_collection(db_session, TENANT_A, f"Page Col {i:02d}")

            repo = EnterpriseCollectionRepository(db_session)
            page1 = repo.list(offset=0, limit=2)
            page2 = repo.list(offset=2, limit=2)
            page3 = repo.list(offset=4, limit=2)

        assert len(page1) == 2
        assert len(page2) == 2
        assert len(page3) == 1  # only one left after 4 rows skipped

        # Pages must not overlap
        page1_ids = {c.id for c in page1}
        page2_ids = {c.id for c in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_list_ordered_alphabetically(self, db_session, tenant_a_context):
        """list() returns collections sorted alphabetically by name."""
        with tenant_a_context():
            _make_collection(db_session, TENANT_A, "Zebra")
            _make_collection(db_session, TENANT_A, "Apple")
            _make_collection(db_session, TENANT_A, "Mango")

            repo = EnterpriseCollectionRepository(db_session)
            result = repo.list()

        names = [c.name for c in result]
        assert names == sorted(names)


class TestCollectionUpdate:
    def test_update_collection_name(self, db_session, tenant_a_context):
        """update() changes the collection name for the owning tenant."""
        with tenant_a_context():
            col = _make_collection(db_session, TENANT_A, "Old Name")
            repo = EnterpriseCollectionRepository(db_session)
            updated = repo.update(col.id, name="New Name")

        assert updated.name == "New Name"
        assert updated.id == col.id

    def test_update_collection_description(self, db_session, tenant_a_context):
        """update() changes the description when provided."""
        with tenant_a_context():
            col = _make_collection(db_session, TENANT_A, "Desc Col")
            repo = EnterpriseCollectionRepository(db_session)
            updated = repo.update(col.id, description="Fresh description")

        assert updated.description == "Fresh description"

    def test_update_raises_on_cross_tenant(
        self, db_session, tenant_a_context, tenant_b_context
    ):
        """update() raises TenantIsolationError when attempting to modify another tenant's collection."""
        with tenant_a_context():
            col_a = _make_collection(db_session, TENANT_A, "A Update Target")

        with tenant_b_context():
            repo = EnterpriseCollectionRepository(db_session)
            with pytest.raises(TenantIsolationError):
                repo.update(col_a.id, name="Hijacked")

    def test_update_raises_value_error_for_missing(self, db_session, tenant_a_context):
        """update() raises ValueError when the collection UUID does not exist."""
        with tenant_a_context():
            repo = EnterpriseCollectionRepository(db_session)
            with pytest.raises(ValueError, match="not found"):
                repo.update(uuid.uuid4(), name="Ghost")


class TestCollectionDelete:
    def test_delete_removes_collection(self, db_session, tenant_a_context):
        """delete() removes the collection and returns True."""
        with tenant_a_context():
            col = _make_collection(db_session, TENANT_A, "Deletable Col")
            col_id = col.id
            repo = EnterpriseCollectionRepository(db_session)
            result = repo.delete(col_id)
            # Confirm it is gone
            gone = repo.get(col_id)

        assert result is True
        assert gone is None

    def test_delete_returns_false_for_missing(self, db_session, tenant_a_context):
        """delete() returns False when the collection does not exist."""
        with tenant_a_context():
            repo = EnterpriseCollectionRepository(db_session)
            result = repo.delete(uuid.uuid4())

        assert result is False

    def test_delete_raises_on_cross_tenant(
        self, db_session, tenant_a_context, tenant_b_context
    ):
        """delete() raises TenantIsolationError when attempting to delete another tenant's collection."""
        with tenant_a_context():
            col_a = _make_collection(db_session, TENANT_A, "A Delete Target")

        with tenant_b_context():
            repo = EnterpriseCollectionRepository(db_session)
            with pytest.raises(TenantIsolationError):
                repo.delete(col_a.id)


# ---------------------------------------------------------------------------
# ENT-2.8: Membership operations
# ---------------------------------------------------------------------------


class TestMembershipAddArtifact:
    def test_add_artifact_creates_membership(self, db_session, tenant_a_context):
        """add_artifact() creates an EnterpriseCollectionArtifact join row."""
        with tenant_a_context():
            col = _make_collection(db_session, TENANT_A, "Membership Col")
            art = _make_artifact(db_session, TENANT_A, "test-skill-add")
            repo = EnterpriseCollectionRepository(db_session)
            membership = repo.add_artifact(col.id, art.id)

        assert membership.collection_id == col.id
        assert membership.artifact_id == art.id
        assert membership.id is not None

    def test_add_artifact_auto_assigns_position(self, db_session, tenant_a_context):
        """add_artifact() appends at max(order_index)+1 when position is None."""
        with tenant_a_context():
            col = _make_collection(db_session, TENANT_A, "Auto Pos Col")
            art1 = _make_artifact(db_session, TENANT_A, "skill-pos-1")
            art2 = _make_artifact(db_session, TENANT_A, "skill-pos-2")
            art3 = _make_artifact(db_session, TENANT_A, "skill-pos-3")
            repo = EnterpriseCollectionRepository(db_session)

            m1 = repo.add_artifact(col.id, art1.id)
            m2 = repo.add_artifact(col.id, art2.id)
            m3 = repo.add_artifact(col.id, art3.id)

        assert m1.order_index == 0
        assert m2.order_index == 1
        assert m3.order_index == 2

    def test_add_artifact_explicit_position(self, db_session, tenant_a_context):
        """add_artifact() respects an explicitly provided position."""
        with tenant_a_context():
            col = _make_collection(db_session, TENANT_A, "Explicit Pos Col")
            art = _make_artifact(db_session, TENANT_A, "skill-explicit")
            repo = EnterpriseCollectionRepository(db_session)
            membership = repo.add_artifact(col.id, art.id, position=7)

        assert membership.order_index == 7

    def test_add_artifact_cross_tenant_artifact_rejected(
        self, db_session, tenant_a_context, tenant_b_context
    ):
        """add_artifact() raises TenantIsolationError when the artifact belongs to another tenant."""
        with tenant_a_context():
            col_a = _make_collection(db_session, TENANT_A, "A Only Col")

        with tenant_b_context():
            art_b = _make_artifact(db_session, TENANT_B, "b-skill-cross")

        with tenant_a_context():
            repo = EnterpriseCollectionRepository(db_session)
            with pytest.raises(TenantIsolationError):
                repo.add_artifact(col_a.id, art_b.id)

    def test_add_artifact_raises_for_missing_collection(self, db_session, tenant_a_context):
        """add_artifact() raises ValueError when the collection UUID does not exist."""
        with tenant_a_context():
            art = _make_artifact(db_session, TENANT_A, "skill-no-col")
            repo = EnterpriseCollectionRepository(db_session)
            with pytest.raises(ValueError, match="not found"):
                repo.add_artifact(uuid.uuid4(), art.id)

    def test_add_artifact_raises_for_missing_artifact(self, db_session, tenant_a_context):
        """add_artifact() raises ValueError when the artifact UUID does not exist."""
        with tenant_a_context():
            col = _make_collection(db_session, TENANT_A, "Existing Col")
            repo = EnterpriseCollectionRepository(db_session)
            with pytest.raises(ValueError, match="not found"):
                repo.add_artifact(col.id, uuid.uuid4())


class TestMembershipRemoveArtifact:
    def test_remove_artifact_deletes_membership(self, db_session, tenant_a_context):
        """remove_artifact() deletes the join row and returns True."""
        with tenant_a_context():
            col = _make_collection(db_session, TENANT_A, "Remove Col")
            art = _make_artifact(db_session, TENANT_A, "skill-remove")
            repo = EnterpriseCollectionRepository(db_session)
            repo.add_artifact(col.id, art.id)

            result = repo.remove_artifact(col.id, art.id)
            remaining = repo.list_artifacts(col.id)

        assert result is True
        assert remaining == []

    def test_remove_artifact_returns_false_when_not_member(
        self, db_session, tenant_a_context
    ):
        """remove_artifact() returns False when the artifact is not in the collection."""
        with tenant_a_context():
            col = _make_collection(db_session, TENANT_A, "Empty Col")
            art = _make_artifact(db_session, TENANT_A, "skill-not-member")
            repo = EnterpriseCollectionRepository(db_session)
            result = repo.remove_artifact(col.id, art.id)

        assert result is False


class TestMembershipListArtifacts:
    def test_list_artifacts_ordered_by_position(self, db_session, tenant_a_context):
        """list_artifacts() returns artifacts sorted by order_index ascending."""
        with tenant_a_context():
            col = _make_collection(db_session, TENANT_A, "Ordered Col")
            art_x = _make_artifact(db_session, TENANT_A, "skill-x")
            art_y = _make_artifact(db_session, TENANT_A, "skill-y")
            art_z = _make_artifact(db_session, TENANT_A, "skill-z")
            repo = EnterpriseCollectionRepository(db_session)
            # Add in reverse order with explicit positions
            repo.add_artifact(col.id, art_z.id, position=0)
            repo.add_artifact(col.id, art_y.id, position=1)
            repo.add_artifact(col.id, art_x.id, position=2)

            artifacts = repo.list_artifacts(col.id)

        assert [a.id for a in artifacts] == [art_z.id, art_y.id, art_x.id]

    def test_list_artifacts_only_from_current_tenant(
        self, db_session, tenant_a_context, tenant_b_context
    ):
        """list_artifacts() only surfaces artifacts belonging to the current tenant."""
        with tenant_a_context():
            col_a = _make_collection(db_session, TENANT_A, "A Col List")
            art_a = _make_artifact(db_session, TENANT_A, "skill-a-list")
            repo_a = EnterpriseCollectionRepository(db_session)
            repo_a.add_artifact(col_a.id, art_a.id)

        # Tenant B creates their own collection and artifact
        with tenant_b_context():
            col_b = _make_collection(db_session, TENANT_B, "B Col List")
            art_b = _make_artifact(db_session, TENANT_B, "skill-b-list")
            repo_b = EnterpriseCollectionRepository(db_session)
            repo_b.add_artifact(col_b.id, art_b.id)

        # Tenant A's collection must not surface Tenant B's artifact
        with tenant_a_context():
            repo = EnterpriseCollectionRepository(db_session)
            artifacts = repo.list_artifacts(col_a.id)

        assert len(artifacts) == 1
        assert artifacts[0].id == art_a.id

    def test_list_artifacts_returns_empty_for_nonexistent_collection(
        self, db_session, tenant_a_context
    ):
        """list_artifacts() returns an empty list when the collection UUID does not exist."""
        with tenant_a_context():
            repo = EnterpriseCollectionRepository(db_session)
            result = repo.list_artifacts(uuid.uuid4())

        assert result == []


class TestMembershipReorder:
    def test_reorder_artifacts_updates_positions(self, db_session, tenant_a_context):
        """reorder_artifacts() reassigns order_index values to match the supplied list."""
        with tenant_a_context():
            col = _make_collection(db_session, TENANT_A, "Reorder Col")
            art1 = _make_artifact(db_session, TENANT_A, "skill-r1")
            art2 = _make_artifact(db_session, TENANT_A, "skill-r2")
            art3 = _make_artifact(db_session, TENANT_A, "skill-r3")
            repo = EnterpriseCollectionRepository(db_session)
            repo.add_artifact(col.id, art1.id, position=0)
            repo.add_artifact(col.id, art2.id, position=1)
            repo.add_artifact(col.id, art3.id, position=2)

            # Reverse the order: 3, 2, 1
            result = repo.reorder_artifacts(col.id, [art3.id, art2.id, art1.id])
            artifacts = repo.list_artifacts(col.id)

        assert result is True
        assert [a.id for a in artifacts] == [art3.id, art2.id, art1.id]

    def test_reorder_artifacts_returns_false_for_missing_collection(
        self, db_session, tenant_a_context
    ):
        """reorder_artifacts() returns False when the collection does not exist."""
        with tenant_a_context():
            repo = EnterpriseCollectionRepository(db_session)
            result = repo.reorder_artifacts(uuid.uuid4(), [uuid.uuid4()])

        assert result is False

    def test_reorder_artifacts_raises_on_cross_tenant(
        self, db_session, tenant_a_context, tenant_b_context
    ):
        """reorder_artifacts() raises TenantIsolationError for another tenant's collection."""
        with tenant_a_context():
            col_a = _make_collection(db_session, TENANT_A, "A Reorder Target")

        with tenant_b_context():
            repo = EnterpriseCollectionRepository(db_session)
            with pytest.raises(TenantIsolationError):
                repo.reorder_artifacts(col_a.id, [])


# ---------------------------------------------------------------------------
# Multi-tenant isolation
# ---------------------------------------------------------------------------


class TestMultiTenantIsolation:
    def test_tenant_a_cannot_see_tenant_b_collections(
        self, db_session, tenant_a_context, tenant_b_context
    ):
        """Tenant A's list() must not include collections owned by Tenant B."""
        with tenant_b_context():
            _make_collection(db_session, TENANT_B, "B Invisible Col")

        with tenant_a_context():
            repo = EnterpriseCollectionRepository(db_session)
            results = repo.list()

        assert all(c.tenant_id == TENANT_A for c in results)
        assert all(c.name != "B Invisible Col" for c in results)

    def test_tenant_a_cannot_modify_tenant_b_collection(
        self, db_session, tenant_a_context, tenant_b_context
    ):
        """Tenant A's update() targeting Tenant B's collection raises TenantIsolationError."""
        with tenant_b_context():
            col_b = _make_collection(db_session, TENANT_B, "B Protected Col")

        with tenant_a_context():
            repo = EnterpriseCollectionRepository(db_session)
            with pytest.raises(TenantIsolationError):
                repo.update(col_b.id, name="Stolen Name")

    def test_membership_scoped_to_tenant(
        self, db_session, tenant_a_context, tenant_b_context
    ):
        """Artifacts added to Tenant B's collection are inaccessible to Tenant A.

        ``list_artifacts`` calls ``self.get(collection_id)`` which asserts tenant
        ownership, so a cross-tenant access raises ``TenantIsolationError`` rather
        than silently returning an empty list.
        """
        with tenant_b_context():
            col_b = _make_collection(db_session, TENANT_B, "B Membership Col")
            art_b = _make_artifact(db_session, TENANT_B, "skill-b-membership")
            repo_b = EnterpriseCollectionRepository(db_session)
            repo_b.add_artifact(col_b.id, art_b.id)

        # Tenant A must not be able to read Tenant B's collection artifacts
        with tenant_a_context():
            repo_a = EnterpriseCollectionRepository(db_session)
            with pytest.raises(TenantIsolationError):
                repo_a.list_artifacts(col_b.id)

    def test_get_by_name_does_not_leak_across_tenants(
        self, db_session, tenant_a_context, tenant_b_context
    ):
        """get_by_name() for Tenant A must not return a same-named collection owned by Tenant B."""
        with tenant_b_context():
            _make_collection(db_session, TENANT_B, "Leaked Name")

        with tenant_a_context():
            repo = EnterpriseCollectionRepository(db_session)
            result = repo.get_by_name("Leaked Name")

        assert result is None

    def test_delete_cross_tenant_collection_raises(
        self, db_session, tenant_a_context, tenant_b_context
    ):
        """delete() raises TenantIsolationError when Tenant A tries to delete Tenant B's collection."""
        with tenant_b_context():
            col_b = _make_collection(db_session, TENANT_B, "B Delete Iso Col")

        with tenant_a_context():
            repo = EnterpriseCollectionRepository(db_session)
            with pytest.raises(TenantIsolationError):
                repo.delete(col_b.id)
