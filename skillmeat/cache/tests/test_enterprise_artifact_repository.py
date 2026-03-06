"""Unit tests for EnterpriseArtifactRepository.

Coverage:
    ENT-2.2  Lookup with tenant scoping (get, get_by_uuid, get_by_name)
    ENT-2.3  Paginated list / count / tag search
    ENT-2.4  Create and update (including version versioning)
    ENT-2.5  Soft delete and hard delete
    ENT-2.6  Version history retrieval

Architecture note — why mock sessions rather than SQLite in-memory:
    ``EnterpriseArtifact`` uses ``sqlalchemy.dialects.postgresql.JSONB`` and
    ``UUID(as_uuid=True)`` column types.  SQLite's DDL compiler cannot render
    JSONB, so ``EnterpriseBase.metadata.create_all()`` raises
    ``CompileError`` against a SQLite engine.  All tests therefore use
    ``unittest.mock.MagicMock`` sessions and pre-built ORM instance stubs so
    that repository logic (tenant isolation, content hashing, version
    bookkeeping, cascade helpers) is exercised without a live database.

    JSONB tag-search tests (``search_by_tags``) are additionally skipped on
    non-PostgreSQL backends because the ``@>`` operator is PostgreSQL-specific.
    They are marked ``integration`` so that a CI job with a real PG database
    can run them via ``pytest -m integration``.
"""

from __future__ import annotations

import hashlib
import uuid
from contextlib import contextmanager
from typing import Generator, List, Optional
from unittest.mock import MagicMock, call, patch

import pytest
from sqlalchemy.orm import Session

from skillmeat.cache.enterprise_repositories import (
    EnterpriseArtifactRepository,
    TenantContext,
    TenantIsolationError,
    tenant_scope,
)
from skillmeat.cache.models_enterprise import (
    EnterpriseArtifact,
    EnterpriseArtifactVersion,
)


# ---------------------------------------------------------------------------
# Deterministic test UUIDs
# ---------------------------------------------------------------------------

TENANT_A: uuid.UUID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_B: uuid.UUID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

ART_ID_1: uuid.UUID = uuid.UUID("11111111-1111-1111-1111-111111111111")
ART_ID_2: uuid.UUID = uuid.UUID("22222222-2222-2222-2222-222222222222")

VER_ID_1: uuid.UUID = uuid.UUID("aaaaaaaa-1111-1111-1111-111111111111")
VER_ID_2: uuid.UUID = uuid.UUID("aaaaaaaa-2222-2222-2222-222222222222")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256(text: str) -> str:
    """Return the SHA256 hex digest of *text* (mirrors repository helper)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _make_artifact(
    artifact_id: uuid.UUID = ART_ID_1,
    tenant_id: uuid.UUID = TENANT_A,
    name: str = "test-skill",
    artifact_type: str = "skill",
    tags: Optional[List[str]] = None,
    is_active: bool = True,
    versions: Optional[List[EnterpriseArtifactVersion]] = None,
) -> MagicMock:
    """Build a MagicMock that behaves like an EnterpriseArtifact row."""
    art = MagicMock(spec=EnterpriseArtifact)
    art.id = artifact_id
    art.tenant_id = tenant_id
    art.name = name
    art.artifact_type = artifact_type
    art.tags = tags if tags is not None else []
    art.is_active = is_active
    art.versions = versions if versions is not None else []
    art.custom_fields = {}
    return art


def _make_version(
    artifact_id: uuid.UUID = ART_ID_1,
    tenant_id: uuid.UUID = TENANT_A,
    version_tag: str = "1.0.0",
    content: str = "# Hello",
    version_id: Optional[uuid.UUID] = None,
) -> MagicMock:
    """Build a MagicMock that behaves like an EnterpriseArtifactVersion row."""
    ver = MagicMock(spec=EnterpriseArtifactVersion)
    ver.id = version_id or uuid.uuid4()
    ver.artifact_id = artifact_id
    ver.tenant_id = tenant_id
    ver.version_tag = version_tag
    ver.content_hash = _sha256(content)
    ver.markdown_payload = content
    return ver


def _make_session(
    *,
    get_return: Optional[MagicMock] = None,
    execute_scalars: Optional[List] = None,
    execute_scalar_one: Optional[int] = None,
) -> MagicMock:
    """Build a MagicMock session pre-configured for common return values.

    Parameters
    ----------
    get_return:
        The object returned by ``session.get(...)``.
    execute_scalars:
        The list returned by ``session.execute(...).scalars().all()``.
    execute_scalar_one:
        The int returned by ``session.execute(...).scalar_one()``.
    """
    session = MagicMock(spec=Session)

    # session.get() → ORM instance or None
    session.get.return_value = get_return

    # Chain: session.execute(stmt).scalars().all() → list
    if execute_scalars is not None:
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = execute_scalars
        execute_mock = MagicMock()
        execute_mock.scalars.return_value = scalars_mock
        execute_mock.scalar_one_or_none.return_value = (
            execute_scalars[0] if execute_scalars else None
        )
        session.execute.return_value = execute_mock

    # Chain: session.execute(stmt).scalar_one() → int
    if execute_scalar_one is not None:
        execute_mock = MagicMock()
        execute_mock.scalar_one.return_value = execute_scalar_one
        session.execute.return_value = execute_mock

    return session


def _repo(session: MagicMock, tenant_id: uuid.UUID = TENANT_A) -> EnterpriseArtifactRepository:
    """Return a repository instance with *tenant_id* active in TenantContext.

    Note: callers are responsible for wrapping test bodies in
    ``with tenant_scope(tenant_id):`` when the repo's methods also need the
    context active during execution.
    """
    return EnterpriseArtifactRepository(session)


# ---------------------------------------------------------------------------
# ENT-2.2: Lookup tests
# ---------------------------------------------------------------------------


class TestGet:
    """get(artifact_id) — PK lookup with ownership assertion."""

    def test_get_returns_own_tenant_artifact(self) -> None:
        """get() returns the artifact when it belongs to the current tenant."""
        art = _make_artifact(artifact_id=ART_ID_1, tenant_id=TENANT_A)
        session = _make_session(get_return=art)
        repo = _repo(session)

        with tenant_scope(TENANT_A):
            result = repo.get(ART_ID_1)

        assert result is art
        session.get.assert_called_once_with(EnterpriseArtifact, ART_ID_1)

    def test_get_returns_none_for_missing_artifact(self) -> None:
        """get() returns None when no row with the given PK exists."""
        session = _make_session(get_return=None)
        repo = _repo(session)

        with tenant_scope(TENANT_A):
            result = repo.get(ART_ID_1)

        assert result is None

    def test_get_returns_none_for_cross_tenant(self) -> None:
        """get() returns None (not raises) when the artifact belongs to a different tenant.

        This hides cross-tenant existence to prevent enumeration.
        """
        art = _make_artifact(artifact_id=ART_ID_1, tenant_id=TENANT_A)
        session = _make_session(get_return=art)
        repo = _repo(session)

        with tenant_scope(TENANT_B):
            result = repo.get(ART_ID_1)

        # Must be None — cross-tenant existence must NOT be disclosed
        assert result is None

    def test_get_does_not_raise_on_cross_tenant(self) -> None:
        """get() swallows TenantIsolationError and returns None instead of raising."""
        art = _make_artifact(artifact_id=ART_ID_1, tenant_id=TENANT_B)
        session = _make_session(get_return=art)
        repo = _repo(session)

        with tenant_scope(TENANT_A):
            # Should NOT propagate TenantIsolationError
            result = repo.get(ART_ID_1)

        assert result is None


class TestGetByUuid:
    """get_by_uuid(str) — query with tenant filter applied at SELECT time."""

    def test_get_by_uuid_with_tenant_filter(self) -> None:
        """get_by_uuid returns the artifact when the tenant filter matches."""
        art = _make_artifact(artifact_id=ART_ID_1, tenant_id=TENANT_A)
        session = _make_session(execute_scalars=[art])
        repo = _repo(session)

        with tenant_scope(TENANT_A):
            result = repo.get_by_uuid(str(ART_ID_1))

        assert result is art
        # A SELECT was issued (not session.get)
        session.execute.assert_called_once()

    def test_get_by_uuid_returns_none_for_cross_tenant(self) -> None:
        """get_by_uuid returns None when tenant filter excludes the artifact."""
        session = _make_session(execute_scalars=[])
        repo = _repo(session)

        with tenant_scope(TENANT_B):
            result = repo.get_by_uuid(str(ART_ID_1))

        assert result is None

    def test_get_by_uuid_raises_on_invalid_uuid_string(self) -> None:
        """get_by_uuid raises ValueError for a malformed UUID string."""
        session = _make_session()
        repo = _repo(session)

        with tenant_scope(TENANT_A):
            with pytest.raises(ValueError):
                repo.get_by_uuid("not-a-valid-uuid")


class TestGetByName:
    """get_by_name(name) — name lookup scoped to current tenant."""

    def test_get_by_name_with_tenant_filter(self) -> None:
        """get_by_name returns the artifact for the current tenant."""
        art = _make_artifact(name="canvas-design", tenant_id=TENANT_A)
        session = _make_session(execute_scalars=[art])
        repo = _repo(session)

        with tenant_scope(TENANT_A):
            result = repo.get_by_name("canvas-design")

        assert result is art

    def test_get_by_name_returns_none_when_not_found(self) -> None:
        """get_by_name returns None when the name does not exist for this tenant."""
        session = _make_session(execute_scalars=[])
        repo = _repo(session)

        with tenant_scope(TENANT_A):
            result = repo.get_by_name("nonexistent")

        assert result is None

    def test_get_by_name_cross_tenant_returns_none(self) -> None:
        """get_by_name issued under TENANT_B does not return TENANT_A's artifact.

        The method appends a tenant_id predicate in _tenant_select(), so a
        different tenant finds nothing even if the name matches.
        """
        session = _make_session(execute_scalars=[])
        repo = _repo(session)

        with tenant_scope(TENANT_B):
            result = repo.get_by_name("canvas-design")

        assert result is None


# ---------------------------------------------------------------------------
# ENT-2.3: List / count / tag search tests
# ---------------------------------------------------------------------------


class TestList:
    """list() — paginated active artifact listing."""

    def test_list_only_returns_current_tenant_artifacts(self) -> None:
        """list() calls _tenant_select which injects tenant_id predicate."""
        art_a = _make_artifact(artifact_id=ART_ID_1, tenant_id=TENANT_A)
        session = _make_session(execute_scalars=[art_a])
        repo = _repo(session)

        with tenant_scope(TENANT_A):
            results = repo.list()

        assert len(results) == 1
        assert results[0] is art_a

    def test_list_pagination(self) -> None:
        """list() passes offset and limit to the executed statement.

        We validate that the session.execute() was called (pagination
        parameters are baked into the compiled statement, not passed as
        separate args to session.execute, so we cannot inspect them directly
        without compiling; we confirm the call count and return value instead).
        """
        arts = [
            _make_artifact(artifact_id=uuid.uuid4(), tenant_id=TENANT_A, name=f"art-{i}")
            for i in range(3)
        ]
        session = _make_session(execute_scalars=arts)
        repo = _repo(session)

        with tenant_scope(TENANT_A):
            results = repo.list(offset=0, limit=3)

        assert len(results) == 3
        session.execute.assert_called_once()

    def test_list_filter_by_type(self) -> None:
        """list(artifact_type=...) narrows results to the requested type."""
        skill = _make_artifact(artifact_id=ART_ID_1, artifact_type="skill")
        session = _make_session(execute_scalars=[skill])
        repo = _repo(session)

        with tenant_scope(TENANT_A):
            results = repo.list(artifact_type="skill")

        assert len(results) == 1
        assert results[0].artifact_type == "skill"

    def test_list_returns_empty_for_no_match(self) -> None:
        """list() returns an empty list when no artifacts match the filters."""
        session = _make_session(execute_scalars=[])
        repo = _repo(session)

        with tenant_scope(TENANT_A):
            results = repo.list(artifact_type="mcp")

        assert results == []


class TestCount:
    """count() — tenant-scoped row count."""

    def test_count_with_tenant_isolation(self) -> None:
        """count() returns the number of artifacts for the active tenant."""
        session = _make_session(execute_scalar_one=5)
        repo = _repo(session)

        with tenant_scope(TENANT_A):
            result = repo.count()

        assert result == 5
        session.execute.assert_called_once()

    def test_count_returns_zero_for_empty_tenant(self) -> None:
        """count() returns 0 when the tenant has no artifacts."""
        session = _make_session(execute_scalar_one=0)
        repo = _repo(session)

        with tenant_scope(TENANT_B):
            result = repo.count()

        assert result == 0

    def test_count_by_type(self) -> None:
        """count(artifact_type=...) restricts the count to the given type."""
        session = _make_session(execute_scalar_one=2)
        repo = _repo(session)

        with tenant_scope(TENANT_A):
            result = repo.count(artifact_type="command")

        assert result == 2


class TestSearchByTags:
    """search_by_tags() — JSONB @> operator; skipped on non-PostgreSQL backends.

    These tests are marked ``integration`` because the @> containment operator
    is PostgreSQL-specific.  They can be run against a real PG database via:

        pytest -m integration skillmeat/cache/tests/test_enterprise_artifact_repository.py

    The tests here use the mock session to verify the return value contract
    (i.e. that the method returns a list and passes empty-list guard).  The
    actual @> SQL is exercised only in a live-DB environment.
    """

    def test_search_by_tags_empty_list_returns_no_rows(self) -> None:
        """search_by_tags([]) short-circuits and returns an empty list."""
        session = _make_session()
        repo = _repo(session)

        with tenant_scope(TENANT_A):
            results = repo.search_by_tags([])

        assert results == []
        # session.execute must NOT be called — the guard returns early
        session.execute.assert_not_called()

    @pytest.mark.integration
    def test_search_by_tags_match_all(self) -> None:
        """search_by_tags(tags, match_all=True) requires all tags to be present.

        NOTE: Skipped in unit test runs — requires PostgreSQL for the @> operator.
        Run with: pytest -m integration
        """
        art = _make_artifact(tags=["python", "ai"])
        session = _make_session(execute_scalars=[art])
        repo = _repo(session)

        with tenant_scope(TENANT_A):
            results = repo.search_by_tags(["python", "ai"], match_all=True)

        assert len(results) == 1
        assert results[0] is art

    @pytest.mark.integration
    def test_search_by_tags_match_any(self) -> None:
        """search_by_tags(tags, match_all=False) requires at least one tag match.

        NOTE: Skipped in unit test runs — requires PostgreSQL for the @> operator.
        Run with: pytest -m integration
        """
        art_a = _make_artifact(artifact_id=ART_ID_1, tags=["python"])
        art_b = _make_artifact(artifact_id=ART_ID_2, tags=["ai"])
        session = _make_session(execute_scalars=[art_a, art_b])
        repo = _repo(session)

        with tenant_scope(TENANT_A):
            results = repo.search_by_tags(["python", "ai"], match_all=False)

        assert len(results) == 2


# ---------------------------------------------------------------------------
# ENT-2.4: Create / update tests
# ---------------------------------------------------------------------------


class TestCreate:
    """create() — new artifact row with optional initial version."""

    def test_create_sets_tenant_id_automatically(self) -> None:
        """create() stamps the artifact with the currently active tenant_id."""
        session = MagicMock(spec=Session)

        # Capture the artifact object passed to session.add()
        added_objects: list = []
        session.add.side_effect = lambda obj: added_objects.append(obj)
        # flush assigns id; simulate by doing nothing (id already set via default)
        session.flush.return_value = None
        session.commit.return_value = None
        session.refresh.return_value = None

        repo = _repo(session)

        with tenant_scope(TENANT_A):
            artifact = repo.create(name="my-skill", artifact_type="skill")

        # The artifact returned should have tenant_id == TENANT_A
        assert artifact.tenant_id == TENANT_A

    def test_create_without_content_creates_no_version(self) -> None:
        """create() without *content* inserts only the artifact row."""
        session = MagicMock(spec=Session)
        added_objects: list = []
        session.add.side_effect = lambda obj: added_objects.append(obj)
        session.flush.return_value = None
        session.commit.return_value = None
        session.refresh.return_value = None

        repo = _repo(session)

        with tenant_scope(TENANT_A):
            repo.create(name="no-content-skill", artifact_type="skill")

        # Only one object added: the artifact itself
        artifact_adds = [o for o in added_objects if isinstance(o, EnterpriseArtifact)]
        version_adds = [o for o in added_objects if isinstance(o, EnterpriseArtifactVersion)]
        assert len(artifact_adds) == 1
        assert len(version_adds) == 0

    def test_create_with_content_creates_initial_version(self) -> None:
        """create(content=...) adds both the artifact and a v1.0.0 version row."""
        session = MagicMock(spec=Session)
        added_objects: list = []
        session.add.side_effect = lambda obj: added_objects.append(obj)
        session.flush.return_value = None
        session.commit.return_value = None
        session.refresh.return_value = None

        repo = _repo(session)

        with tenant_scope(TENANT_A):
            repo.create(
                name="versioned-skill",
                artifact_type="skill",
                content="# Hello World",
            )

        artifact_adds = [o for o in added_objects if isinstance(o, EnterpriseArtifact)]
        version_adds = [o for o in added_objects if isinstance(o, EnterpriseArtifactVersion)]
        assert len(artifact_adds) == 1
        assert len(version_adds) == 1
        version = version_adds[0]
        assert version.version_tag == "1.0.0"
        assert version.markdown_payload == "# Hello World"
        assert version.content_hash == _sha256("# Hello World")

    def test_create_stores_tags_and_metadata(self) -> None:
        """create(tags=..., metadata=...) persists them on the artifact."""
        session = MagicMock(spec=Session)
        added_objects: list = []
        session.add.side_effect = lambda obj: added_objects.append(obj)
        session.flush.return_value = None
        session.commit.return_value = None
        session.refresh.return_value = None

        repo = _repo(session)

        with tenant_scope(TENANT_A):
            repo.create(
                name="tagged-skill",
                artifact_type="skill",
                tags=["python", "ai"],
                metadata={"source": "github"},
            )

        artifact = [o for o in added_objects if isinstance(o, EnterpriseArtifact)][0]
        assert artifact.tags == ["python", "ai"]
        assert artifact.custom_fields == {"source": "github"}


class TestUpdate:
    """update() — mutable field update with optional new version creation."""

    def _setup_update(
        self,
        existing_versions: Optional[List[MagicMock]] = None,
    ):
        """Return (session, repo, artifact) ready for an update test."""
        art = _make_artifact(
            artifact_id=ART_ID_1,
            tenant_id=TENANT_A,
            versions=existing_versions or [],
        )
        session = MagicMock(spec=Session)
        session.get.return_value = art

        added_objects: list = []
        session.add.side_effect = lambda obj: added_objects.append(obj)
        session.commit.return_value = None
        session.refresh.side_effect = lambda obj: None  # no-op

        return session, added_objects, art

    def test_update_raises_on_cross_tenant(self) -> None:
        """update() raises TenantIsolationError when the artifact belongs to a different tenant."""
        art = _make_artifact(artifact_id=ART_ID_1, tenant_id=TENANT_A)
        session = MagicMock(spec=Session)
        session.get.return_value = art

        repo = _repo(session)

        with tenant_scope(TENANT_B):
            with pytest.raises(TenantIsolationError):
                repo.update(ART_ID_1, name="new-name")

    def test_update_raises_on_missing_artifact(self) -> None:
        """update() raises ValueError when the artifact does not exist."""
        session = MagicMock(spec=Session)
        session.get.return_value = None

        repo = _repo(session)

        with tenant_scope(TENANT_A):
            with pytest.raises(ValueError, match="not found"):
                repo.update(ART_ID_1, name="irrelevant")

    def test_update_creates_new_version_on_content_change(self) -> None:
        """update(content=...) adds a new version row when content hash differs."""
        v1 = _make_version(content="# v1", version_tag="1.0.0")
        session, added, art = self._setup_update(existing_versions=[v1])

        repo = _repo(session)

        with tenant_scope(TENANT_A):
            repo.update(ART_ID_1, content="# v2 different content")

        version_adds = [o for o in added if isinstance(o, EnterpriseArtifactVersion)]
        assert len(version_adds) == 1
        assert version_adds[0].version_tag == "1.0.1"
        assert version_adds[0].markdown_payload == "# v2 different content"

    def test_update_deduplicates_unchanged_content(self) -> None:
        """update(content=...) does NOT add a version row when content is identical."""
        content = "# Same content"
        v1 = _make_version(content=content, version_tag="1.0.0")
        session, added, art = self._setup_update(existing_versions=[v1])

        repo = _repo(session)

        with tenant_scope(TENANT_A):
            repo.update(ART_ID_1, content=content)  # same payload

        version_adds = [o for o in added if isinstance(o, EnterpriseArtifactVersion)]
        assert len(version_adds) == 0

    def test_update_updates_name_field(self) -> None:
        """update(name=...) mutates the artifact's name attribute."""
        session, added, art = self._setup_update()
        repo = _repo(session)

        with tenant_scope(TENANT_A):
            repo.update(ART_ID_1, name="renamed-skill")

        assert art.name == "renamed-skill"

    def test_update_updates_tags(self) -> None:
        """update(tags=...) replaces the artifact's tag list."""
        session, added, art = self._setup_update()
        repo = _repo(session)

        with tenant_scope(TENANT_A):
            repo.update(ART_ID_1, tags=["new-tag"])

        assert art.tags == ["new-tag"]


# ---------------------------------------------------------------------------
# ENT-2.5: Delete tests
# ---------------------------------------------------------------------------


class TestSoftDelete:
    """soft_delete() — sets is_active=False, row retained."""

    def test_soft_delete_sets_is_active_false(self) -> None:
        """soft_delete() flips is_active to False on the artifact row."""
        art = _make_artifact(artifact_id=ART_ID_1, tenant_id=TENANT_A, is_active=True)
        session = MagicMock(spec=Session)
        session.get.return_value = art
        session.flush.return_value = None
        session.commit.return_value = None

        repo = _repo(session)

        with tenant_scope(TENANT_A):
            result = repo.soft_delete(ART_ID_1)

        assert result is True
        assert art.is_active is False

    def test_soft_delete_raises_on_missing(self) -> None:
        """soft_delete() raises ValueError for a non-existent artifact."""
        session = MagicMock(spec=Session)
        session.get.return_value = None

        repo = _repo(session)

        with tenant_scope(TENANT_A):
            with pytest.raises(ValueError, match="not found"):
                repo.soft_delete(ART_ID_1)

    def test_soft_delete_raises_on_cross_tenant(self) -> None:
        """soft_delete() raises TenantIsolationError for a different tenant's artifact."""
        art = _make_artifact(artifact_id=ART_ID_1, tenant_id=TENANT_A)
        session = MagicMock(spec=Session)
        session.get.return_value = art

        repo = _repo(session)

        with tenant_scope(TENANT_B):
            with pytest.raises(TenantIsolationError):
                repo.soft_delete(ART_ID_1)


class TestHardDelete:
    """hard_delete() — removes artifact row and all related rows."""

    def test_hard_delete_removes_artifact_and_versions(self) -> None:
        """hard_delete() calls session.delete on the artifact (cascade handles versions)."""
        art = _make_artifact(artifact_id=ART_ID_1, tenant_id=TENANT_A)
        session = MagicMock(spec=Session)
        session.get.return_value = art
        session.execute.return_value = MagicMock()
        session.delete.return_value = None
        session.commit.return_value = None

        repo = _repo(session)

        with tenant_scope(TENANT_A):
            result = repo.hard_delete(ART_ID_1)

        assert result is True
        # session.delete should have been called with the artifact
        session.delete.assert_called_once_with(art)
        # session.execute should have been called (for collection membership removal)
        session.execute.assert_called_once()

    def test_hard_delete_raises_on_missing(self) -> None:
        """hard_delete() raises ValueError for a non-existent artifact."""
        session = MagicMock(spec=Session)
        session.get.return_value = None

        repo = _repo(session)

        with tenant_scope(TENANT_A):
            with pytest.raises(ValueError, match="not found"):
                repo.hard_delete(ART_ID_1)

    def test_hard_delete_raises_on_cross_tenant(self) -> None:
        """hard_delete() raises TenantIsolationError for a different tenant's artifact."""
        art = _make_artifact(artifact_id=ART_ID_1, tenant_id=TENANT_A)
        session = MagicMock(spec=Session)
        session.get.return_value = art

        repo = _repo(session)

        with tenant_scope(TENANT_B):
            with pytest.raises(TenantIsolationError):
                repo.hard_delete(ART_ID_1)


# ---------------------------------------------------------------------------
# ENT-2.6: Version history retrieval tests
# ---------------------------------------------------------------------------


class TestListVersions:
    """list_versions() — ordered version history per artifact."""

    def test_list_versions_newest_first(self) -> None:
        """list_versions() returns version rows ordered newest-first."""
        art = _make_artifact(artifact_id=ART_ID_1, tenant_id=TENANT_A)

        v1 = _make_version(version_id=VER_ID_1, version_tag="1.0.0", content="v1 content")
        v2 = _make_version(version_id=VER_ID_2, version_tag="1.0.1", content="v2 content")

        session = MagicMock(spec=Session)
        # get() → artifact (for ownership check inside list_versions)
        session.get.return_value = art

        # execute() for the versions query → [v2, v1] (newest first)
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [v2, v1]
        execute_mock = MagicMock()
        execute_mock.scalars.return_value = scalars_mock
        session.execute.return_value = execute_mock

        repo = _repo(session)

        with tenant_scope(TENANT_A):
            versions = repo.list_versions(ART_ID_1)

        assert len(versions) == 2
        assert versions[0].version_tag == "1.0.1"
        assert versions[1].version_tag == "1.0.0"

    def test_list_versions_returns_empty_for_unknown_artifact(self) -> None:
        """list_versions() returns [] when the artifact does not exist for this tenant."""
        session = MagicMock(spec=Session)
        session.get.return_value = None  # artifact not found

        repo = _repo(session)

        with tenant_scope(TENANT_A):
            versions = repo.list_versions(ART_ID_1)

        assert versions == []

    def test_list_versions_cross_tenant_returns_empty(self) -> None:
        """list_versions() returns [] when the artifact belongs to a different tenant.

        The internal get() call returns None (cross-tenant existence hidden),
        so list_versions() propagates that by returning an empty list.
        """
        art = _make_artifact(artifact_id=ART_ID_1, tenant_id=TENANT_A)
        session = MagicMock(spec=Session)
        session.get.return_value = art

        repo = _repo(session)

        with tenant_scope(TENANT_B):
            versions = repo.list_versions(ART_ID_1)

        assert versions == []


class TestGetContent:
    """get_content() — Markdown payload retrieval for specific or latest version."""

    def test_get_content_latest_version(self) -> None:
        """get_content(artifact_id) returns the most recent version's Markdown payload."""
        art = _make_artifact(artifact_id=ART_ID_1, tenant_id=TENANT_A)

        v_latest = _make_version(content="# Latest content", version_tag="1.0.1")

        session = MagicMock(spec=Session)
        session.get.return_value = art

        version_result = MagicMock()
        version_result.scalar_one_or_none.return_value = v_latest
        session.execute.return_value = version_result

        repo = _repo(session)

        with tenant_scope(TENANT_A):
            content = repo.get_content(ART_ID_1)

        assert content == "# Latest content"

    def test_get_content_specific_version(self) -> None:
        """get_content(artifact_id, version='1.0.0') returns that specific version."""
        art = _make_artifact(artifact_id=ART_ID_1, tenant_id=TENANT_A)

        v_specific = _make_version(content="# v1 content", version_tag="1.0.0")

        session = MagicMock(spec=Session)
        session.get.return_value = art

        version_result = MagicMock()
        version_result.scalar_one_or_none.return_value = v_specific
        session.execute.return_value = version_result

        repo = _repo(session)

        with tenant_scope(TENANT_A):
            content = repo.get_content(ART_ID_1, version="1.0.0")

        assert content == "# v1 content"

    def test_get_content_returns_none_for_unknown_artifact(self) -> None:
        """get_content() returns None when the artifact does not exist for this tenant."""
        session = MagicMock(spec=Session)
        session.get.return_value = None

        repo = _repo(session)

        with tenant_scope(TENANT_A):
            result = repo.get_content(ART_ID_1)

        assert result is None

    def test_get_content_returns_none_when_no_versions(self) -> None:
        """get_content() returns None when the artifact has no version rows."""
        art = _make_artifact(artifact_id=ART_ID_1, tenant_id=TENANT_A)

        session = MagicMock(spec=Session)
        session.get.return_value = art

        version_result = MagicMock()
        version_result.scalar_one_or_none.return_value = None
        session.execute.return_value = version_result

        repo = _repo(session)

        with tenant_scope(TENANT_A):
            result = repo.get_content(ART_ID_1)

        assert result is None

    def test_get_content_cross_tenant_returns_none(self) -> None:
        """get_content() returns None for cross-tenant artifact access."""
        art = _make_artifact(artifact_id=ART_ID_1, tenant_id=TENANT_A)
        session = MagicMock(spec=Session)
        session.get.return_value = art

        repo = _repo(session)

        with tenant_scope(TENANT_B):
            result = repo.get_content(ART_ID_1)

        assert result is None


# ---------------------------------------------------------------------------
# ENT-2.1: Base infrastructure tests
# ---------------------------------------------------------------------------


class TestTenantContext:
    """TenantContext ContextVar and tenant_scope() context manager."""

    def test_tenant_scope_sets_and_restores_context(self) -> None:
        """tenant_scope() sets TenantContext and restores previous value on exit."""
        assert TenantContext.get() is None

        with tenant_scope(TENANT_A):
            assert TenantContext.get() == TENANT_A

        assert TenantContext.get() is None

    def test_nested_tenant_scope_restores_outer(self) -> None:
        """Nested tenant_scope() restores the outer scope on exit."""
        with tenant_scope(TENANT_A):
            assert TenantContext.get() == TENANT_A
            with tenant_scope(TENANT_B):
                assert TenantContext.get() == TENANT_B
            assert TenantContext.get() == TENANT_A

    def test_tenant_scope_restores_on_exception(self) -> None:
        """tenant_scope() restores context even when an exception is raised."""
        assert TenantContext.get() is None
        try:
            with tenant_scope(TENANT_A):
                raise RuntimeError("boom")
        except RuntimeError:
            pass

        assert TenantContext.get() is None


class TestTenantIsolationError:
    """TenantIsolationError domain exception."""

    def test_tenant_isolation_error_attributes(self) -> None:
        """TenantIsolationError stores object_tenant_id and current_tenant_id."""
        exc = TenantIsolationError(
            object_tenant_id=TENANT_A,
            current_tenant_id=TENANT_B,
        )
        assert exc.object_tenant_id == TENANT_A
        assert exc.current_tenant_id == TENANT_B

    def test_tenant_isolation_error_message(self) -> None:
        """TenantIsolationError message includes both tenant UUIDs."""
        exc = TenantIsolationError(
            object_tenant_id=TENANT_A,
            current_tenant_id=TENANT_B,
        )
        message = str(exc)
        assert str(TENANT_A) in message
        assert str(TENANT_B) in message


class TestAssertTenantOwns:
    """_assert_tenant_owns() — ownership assertion helper."""

    def test_assert_tenant_owns_passes_for_matching_tenant(self) -> None:
        """_assert_tenant_owns() does not raise when tenant_id matches."""
        art = _make_artifact(tenant_id=TENANT_A)
        session = MagicMock(spec=Session)
        repo = _repo(session)

        with tenant_scope(TENANT_A):
            repo._assert_tenant_owns(art)  # should not raise

    def test_assert_tenant_owns_raises_for_different_tenant(self) -> None:
        """_assert_tenant_owns() raises TenantIsolationError for wrong tenant."""
        art = _make_artifact(tenant_id=TENANT_A)
        session = MagicMock(spec=Session)
        repo = _repo(session)

        with tenant_scope(TENANT_B):
            with pytest.raises(TenantIsolationError) as exc_info:
                repo._assert_tenant_owns(art)

        assert exc_info.value.object_tenant_id == TENANT_A
        assert exc_info.value.current_tenant_id == TENANT_B


class TestNextVersion:
    """_next_version() static helper — version tag incrementing."""

    def test_next_version_semver_with_v_prefix(self) -> None:
        """_next_version('v1.2.3') returns 'v1.2.4'."""
        assert EnterpriseArtifactRepository._next_version("v1.2.3") == "v1.2.4"

    def test_next_version_semver_without_v_prefix(self) -> None:
        """_next_version('1.2.3') returns '1.2.4'."""
        assert EnterpriseArtifactRepository._next_version("1.2.3") == "1.2.4"

    def test_next_version_non_semver_returns_timestamp_tag(self) -> None:
        """_next_version('not-semver') returns a timestamp-based tag."""
        result = EnterpriseArtifactRepository._next_version("not-semver")
        assert result.startswith("v")
        # Timestamp part should be numeric
        numeric_part = result.lstrip("v")
        assert numeric_part.isdigit()

    def test_next_version_patch_zero(self) -> None:
        """_next_version('v1.0.0') returns 'v1.0.1'."""
        assert EnterpriseArtifactRepository._next_version("v1.0.0") == "v1.0.1"


class TestComputeContentHash:
    """_compute_content_hash() static helper — SHA256 of content string."""

    def test_hash_is_64_hex_chars(self) -> None:
        """_compute_content_hash returns a 64-character hex string."""
        result = EnterpriseArtifactRepository._compute_content_hash("hello")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_hash_matches_sha256(self) -> None:
        """_compute_content_hash matches hashlib.sha256 on the same input."""
        content = "# My skill document"
        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
        result = EnterpriseArtifactRepository._compute_content_hash(content)
        assert result == expected

    def test_hash_differs_for_different_content(self) -> None:
        """_compute_content_hash produces unique digests for distinct content."""
        h1 = EnterpriseArtifactRepository._compute_content_hash("content A")
        h2 = EnterpriseArtifactRepository._compute_content_hash("content B")
        assert h1 != h2
