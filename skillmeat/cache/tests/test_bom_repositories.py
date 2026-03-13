"""Unit tests for BOM/History repositories.

Coverage:
    TASK-11.2  DbArtifactHistoryRepository (local SQLite-backed)
    TASK-11.2  EnterpriseArtifactHistoryStub (enterprise no-op stub)

Architecture note — two test strategies:
    1. SQLite-backed tests for DbArtifactHistoryRepository
       The local repository uses SQLAlchemy 1.x ``session.query()`` style
       and only touches ``artifacts`` and ``artifact_versions`` tables.
       Both tables avoid PostgreSQL-specific column types, so a minimal
       SQLite in-memory engine can exercise real query paths.

    2. Mock-based tests for EnterpriseArtifactHistoryStub
       The stub has no DB interactions; mock-based tests verify that all
       three methods return the expected empty/None sentinels and that
       the stub satisfies the IDbArtifactHistoryRepository contract.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Generator
from unittest.mock import MagicMock, call

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from skillmeat.cache.enterprise_repositories import EnterpriseArtifactHistoryStub
from skillmeat.cache.models import Artifact, ArtifactVersion, Base, Project
from skillmeat.cache.repositories import DbArtifactHistoryRepository
from skillmeat.core.interfaces.dtos import ArtifactVersionDTO, CacheArtifactSummaryDTO


# ---------------------------------------------------------------------------
# Tables required by the local repo (FK-dependency order, no TSVECTOR tables)
# ---------------------------------------------------------------------------
# Artifact has lazy="selectin" relationships on artifact_metadata, tags
# (via artifact_tags), versions, and composite_memberships.  All four
# secondary tables must exist so that the selectin loader doesn't raise
# "no such table" when SQLAlchemy eagerly fetches those collections.
#
# artifact_tags also references the tags table (FK), and composite_memberships
# references composite_artifacts (FK).  We omit group_artifacts here because
# that relationship uses lazy="select" and is only triggered explicitly.
# ---------------------------------------------------------------------------

_TABLES_NEEDED = [
    # Core tables
    "projects",
    "artifacts",
    # selectin relationship: artifact_metadata (uselist=False)
    "artifact_metadata",
    # selectin relationship: tags (via artifact_tags join table)
    "tags",
    "artifact_tags",
    # selectin relationship: versions
    "artifact_versions",
    # selectin relationship: composite_memberships
    "composite_artifacts",
    "composite_memberships",
    # selectin relationship: categories (via entity_category_associations)
    "entity_type_configs",
    "entity_categories",
    "entity_category_associations",
]


# ---------------------------------------------------------------------------
# Fixtures — SQLite engine / session
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def engine():
    """Minimal SQLite in-memory engine with only the tables under test."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(eng, "connect")
    def _set_pragmas(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    meta = Base.metadata
    with eng.begin() as conn:
        for table_name in _TABLES_NEEDED:
            meta.tables[table_name].create(conn, checkfirst=True)

    yield eng
    eng.dispose()


@pytest.fixture()
def session(engine) -> Generator[Session, None, None]:
    """Transactional session that rolls back after every test."""
    connection = engine.connect()
    transaction = connection.begin()
    Session_ = sessionmaker(bind=connection, autoflush=False, autocommit=False)
    sess = Session_()
    yield sess
    sess.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture()
def project(session: Session) -> Project:
    """Minimal Project row required by the Artifact FK."""
    proj = Project(
        id="proj-history-test",
        name="History test project",
        path="/tmp/history-test",
        status="active",
    )
    session.add(proj)
    session.flush()
    return proj


@pytest.fixture()
def artifact(session: Session, project: Project) -> Artifact:
    """A single Artifact row with a deterministic UUID."""
    art = Artifact(
        id="skill:history-skill",
        uuid="aabbccddeeff00112233445566778899",
        project_id=project.id,
        name="history-skill",
        type="skill",
    )
    session.add(art)
    session.flush()
    return art


@pytest.fixture()
def artifact2(session: Session, project: Project) -> Artifact:
    """A second Artifact row with a different name/type for multi-row queries."""
    art = Artifact(
        id="command:history-cmd",
        uuid="bbbbccccddddeeee0000111122223333",
        project_id=project.id,
        name="history-cmd",
        type="command",
    )
    session.add(art)
    session.flush()
    return art


def _make_repo(session: Session) -> DbArtifactHistoryRepository:
    """Return a repository that uses *session* as its session factory."""
    return DbArtifactHistoryRepository(get_session=lambda: session)


# ---------------------------------------------------------------------------
# Helper: build an ArtifactVersion row
# ---------------------------------------------------------------------------


def _add_version(
    session: Session,
    artifact: Artifact,
    *,
    content_hash: str,
    change_origin: str = "deployment",
    parent_hash: str | None = None,
    created_at: datetime | None = None,
    version_lineage: str | None = None,
    metadata_json: str | None = None,
) -> ArtifactVersion:
    ver = ArtifactVersion(
        id=uuid.uuid4().hex,
        artifact_id=artifact.id,
        content_hash=content_hash,
        parent_hash=parent_hash,
        change_origin=change_origin,
        created_at=created_at or datetime.utcnow(),
        version_lineage=version_lineage,
        metadata_json=metadata_json,
    )
    session.add(ver)
    session.flush()
    return ver


# ===========================================================================
# Tests — DbArtifactHistoryRepository.get_cache_artifact_by_uuid
# ===========================================================================


class TestGetCacheArtifactByUuid:
    """get_cache_artifact_by_uuid() — single artifact lookup by stable UUID."""

    def test_returns_dto_when_uuid_matches(
        self, session: Session, artifact: Artifact
    ) -> None:
        """Returns a populated CacheArtifactSummaryDTO for a known UUID."""
        repo = _make_repo(session)
        result = repo.get_cache_artifact_by_uuid(artifact.uuid)

        assert result is not None
        assert isinstance(result, CacheArtifactSummaryDTO)
        assert result.uuid == artifact.uuid
        assert result.id == artifact.id
        assert result.name == artifact.name
        assert result.type == artifact.type

    def test_returns_none_for_unknown_uuid(self, session: Session) -> None:
        """Returns None when no artifact has the requested UUID."""
        repo = _make_repo(session)
        result = repo.get_cache_artifact_by_uuid("00000000000000000000000000000000")
        assert result is None

    def test_project_path_populated_from_relationship(
        self, session: Session, artifact: Artifact, project: Project
    ) -> None:
        """project_path reflects the owning project's filesystem path."""
        # Ensure the ORM relationship is loaded
        session.refresh(artifact)
        repo = _make_repo(session)
        result = repo.get_cache_artifact_by_uuid(artifact.uuid)

        assert result is not None
        assert result.project_path == project.path

    def test_ctx_parameter_is_ignored(
        self, session: Session, artifact: Artifact
    ) -> None:
        """ctx parameter is accepted without error (no-op for the local impl)."""
        repo = _make_repo(session)
        result = repo.get_cache_artifact_by_uuid(artifact.uuid, ctx=object())
        assert result is not None

    def test_session_closed_after_call(self, artifact: Artifact) -> None:
        """The session returned by the factory is closed after the call returns."""
        mock_session = MagicMock(spec=Session)
        query_chain = (
            mock_session.query.return_value.filter.return_value.first
        )
        mock_artifact = MagicMock()
        mock_artifact.id = artifact.id
        mock_artifact.uuid = artifact.uuid
        mock_artifact.name = artifact.name
        mock_artifact.type = artifact.type
        mock_artifact.project = None
        query_chain.return_value = mock_artifact

        repo = DbArtifactHistoryRepository(get_session=lambda: mock_session)
        repo.get_cache_artifact_by_uuid(artifact.uuid)

        mock_session.close.assert_called_once()

    def test_session_closed_even_on_exception(self) -> None:
        """The session is closed even when the query raises an exception."""
        mock_session = MagicMock(spec=Session)
        mock_session.query.side_effect = RuntimeError("db exploded")

        repo = DbArtifactHistoryRepository(get_session=lambda: mock_session)
        with pytest.raises(RuntimeError):
            repo.get_cache_artifact_by_uuid("any-uuid")

        mock_session.close.assert_called_once()


# ===========================================================================
# Tests — DbArtifactHistoryRepository.list_cache_artifacts_by_name_type
# ===========================================================================


class TestListCacheArtifactsByNameType:
    """list_cache_artifacts_by_name_type() — multi-row lookup by name + type."""

    def test_returns_empty_list_when_no_match(self, session: Session) -> None:
        """Returns [] when no artifacts match the name/type filter."""
        repo = _make_repo(session)
        result = repo.list_cache_artifacts_by_name_type("ghost-skill", "skill")
        assert result == []

    def test_returns_single_dto_for_exact_match(
        self, session: Session, artifact: Artifact
    ) -> None:
        """Returns a one-element list for an exact name+type match."""
        repo = _make_repo(session)
        result = repo.list_cache_artifacts_by_name_type("history-skill", "skill")

        assert len(result) == 1
        assert isinstance(result[0], CacheArtifactSummaryDTO)
        assert result[0].name == "history-skill"
        assert result[0].type == "skill"

    def test_name_filter_is_exact_not_substring(
        self, session: Session, artifact: Artifact
    ) -> None:
        """Partial name substrings do not match (no LIKE query)."""
        repo = _make_repo(session)
        result = repo.list_cache_artifacts_by_name_type("history", "skill")
        assert result == []

    def test_type_filter_is_required(
        self, session: Session, artifact: Artifact
    ) -> None:
        """Correct name but wrong type returns empty list."""
        repo = _make_repo(session)
        result = repo.list_cache_artifacts_by_name_type("history-skill", "command")
        assert result == []

    def test_returns_multiple_rows_for_same_name_type(
        self, session: Session, project: Project
    ) -> None:
        """Multiple artifacts with the same name+type (different projects) are all returned."""
        proj2 = Project(
            id="proj-history-test-2",
            name="History test project 2",
            path="/tmp/history-test-2",
            status="active",
        )
        session.add(proj2)
        session.flush()

        art_a = Artifact(
            id="skill:dup-skill-projA",
            uuid=uuid.uuid4().hex,
            project_id="proj-history-test",
            name="dup-skill",
            type="skill",
        )
        art_b = Artifact(
            id="skill:dup-skill-projB",
            uuid=uuid.uuid4().hex,
            project_id="proj-history-test-2",
            name="dup-skill",
            type="skill",
        )
        session.add_all([art_a, art_b])
        session.flush()

        repo = _make_repo(session)
        result = repo.list_cache_artifacts_by_name_type("dup-skill", "skill")

        ids = {dto.id for dto in result}
        assert "skill:dup-skill-projA" in ids
        assert "skill:dup-skill-projB" in ids
        assert len(result) == 2

    def test_ctx_parameter_is_ignored(
        self, session: Session, artifact: Artifact
    ) -> None:
        """ctx parameter is accepted without error."""
        repo = _make_repo(session)
        result = repo.list_cache_artifacts_by_name_type(
            "history-skill", "skill", ctx=object()
        )
        assert len(result) == 1

    def test_session_closed_after_call(self, artifact: Artifact) -> None:
        """The session is closed after list_cache_artifacts_by_name_type returns."""
        mock_session = MagicMock(spec=Session)
        mock_session.query.return_value.filter.return_value.all.return_value = []

        repo = DbArtifactHistoryRepository(get_session=lambda: mock_session)
        repo.list_cache_artifacts_by_name_type("any", "skill")

        mock_session.close.assert_called_once()

    def test_session_closed_even_on_exception(self) -> None:
        """The session is closed even when the query raises."""
        mock_session = MagicMock(spec=Session)
        mock_session.query.side_effect = RuntimeError("broken")

        repo = DbArtifactHistoryRepository(get_session=lambda: mock_session)
        with pytest.raises(RuntimeError):
            repo.list_cache_artifacts_by_name_type("any", "skill")

        mock_session.close.assert_called_once()


# ===========================================================================
# Tests — DbArtifactHistoryRepository.list_versions_for_artifacts
# ===========================================================================


class TestListVersionsForArtifacts:
    """list_versions_for_artifacts() — version lineage query."""

    def test_returns_empty_list_for_empty_input(self, session: Session) -> None:
        """Short-circuits immediately and returns [] for an empty artifact_ids list."""
        repo = _make_repo(session)
        result = repo.list_versions_for_artifacts([])
        assert result == []

    def test_no_session_opened_for_empty_input(self) -> None:
        """The session factory is never called when artifact_ids is empty."""
        factory_calls = []

        def counting_factory():
            factory_calls.append(1)
            return MagicMock(spec=Session)

        repo = DbArtifactHistoryRepository(get_session=counting_factory)
        repo.list_versions_for_artifacts([])
        assert factory_calls == []

    def test_returns_empty_list_when_no_versions_exist(
        self, session: Session, artifact: Artifact
    ) -> None:
        """Returns [] for a valid artifact_id that has no version rows."""
        repo = _make_repo(session)
        result = repo.list_versions_for_artifacts([artifact.id])
        assert result == []

    def test_returns_dto_for_single_version(
        self, session: Session, artifact: Artifact
    ) -> None:
        """Returns a one-element list when a single version exists."""
        ver = _add_version(session, artifact, content_hash="abc123")

        repo = _make_repo(session)
        result = repo.list_versions_for_artifacts([artifact.id])

        assert len(result) == 1
        dto = result[0]
        assert isinstance(dto, ArtifactVersionDTO)
        assert dto.artifact_id == artifact.id
        assert dto.content_hash == "abc123"
        assert dto.id == ver.id

    def test_versions_ordered_newest_first(
        self, session: Session, artifact: Artifact
    ) -> None:
        """Versions are returned ordered by created_at descending."""
        t1 = datetime(2024, 1, 1, 0, 0, 0)
        t2 = datetime(2024, 6, 1, 0, 0, 0)
        t3 = datetime(2025, 1, 1, 0, 0, 0)

        _add_version(session, artifact, content_hash="hash-old", created_at=t1)
        _add_version(session, artifact, content_hash="hash-mid", created_at=t2)
        _add_version(session, artifact, content_hash="hash-new", created_at=t3)

        repo = _make_repo(session)
        result = repo.list_versions_for_artifacts([artifact.id])

        assert len(result) == 3
        hashes = [dto.content_hash for dto in result]
        assert hashes == ["hash-new", "hash-mid", "hash-old"]

    def test_filters_by_artifact_id(
        self, session: Session, artifact: Artifact, artifact2: Artifact
    ) -> None:
        """Only versions belonging to the requested artifact_ids are returned."""
        _add_version(session, artifact, content_hash="hash-art1")
        _add_version(session, artifact2, content_hash="hash-art2")

        repo = _make_repo(session)
        result = repo.list_versions_for_artifacts([artifact.id])

        assert len(result) == 1
        assert result[0].content_hash == "hash-art1"

    def test_accepts_multiple_artifact_ids(
        self, session: Session, artifact: Artifact, artifact2: Artifact
    ) -> None:
        """Versions for multiple artifact_ids are all returned."""
        _add_version(session, artifact, content_hash="hash-multi-1")
        _add_version(session, artifact2, content_hash="hash-multi-2")

        repo = _make_repo(session)
        result = repo.list_versions_for_artifacts([artifact.id, artifact2.id])

        hashes = {dto.content_hash for dto in result}
        assert "hash-multi-1" in hashes
        assert "hash-multi-2" in hashes
        assert len(result) == 2

    def test_dto_fields_are_mapped_correctly(
        self, session: Session, artifact: Artifact
    ) -> None:
        """All DTO fields are populated from the corresponding ORM columns."""
        ver = _add_version(
            session,
            artifact,
            content_hash="fieldhash",
            change_origin="sync",
            parent_hash="parenthash",
            version_lineage='["parenthash"]',
            metadata_json='{"key": "value"}',
            created_at=datetime(2025, 3, 13, 12, 0, 0),
        )

        repo = _make_repo(session)
        result = repo.list_versions_for_artifacts([artifact.id])

        assert len(result) == 1
        dto = result[0]
        assert dto.id == ver.id
        assert dto.artifact_id == artifact.id
        assert dto.content_hash == "fieldhash"
        assert dto.change_origin == "sync"
        assert dto.parent_hash == "parenthash"
        assert dto.version_lineage == '["parenthash"]'
        assert dto.metadata_json == '{"key": "value"}'
        assert dto.created_at is not None
        assert "2025" in dto.created_at

    def test_dto_created_at_is_iso_string(
        self, session: Session, artifact: Artifact
    ) -> None:
        """created_at in the DTO is an ISO-8601 string, not a datetime object."""
        _add_version(
            session,
            artifact,
            content_hash="tstest",
            created_at=datetime(2025, 6, 15, 10, 30, 45),
        )

        repo = _make_repo(session)
        result = repo.list_versions_for_artifacts([artifact.id])

        assert len(result) == 1
        created_at = result[0].created_at
        assert isinstance(created_at, str)
        # Should look like an ISO datetime
        assert "2025" in created_at
        assert "10:30:45" in created_at

    def test_dto_optional_fields_none_when_absent(
        self, session: Session, artifact: Artifact
    ) -> None:
        """parent_hash, version_lineage, and metadata_json default to None."""
        _add_version(session, artifact, content_hash="nullfields")

        repo = _make_repo(session)
        result = repo.list_versions_for_artifacts([artifact.id])

        dto = result[0]
        assert dto.parent_hash is None
        assert dto.version_lineage is None
        assert dto.metadata_json is None

    def test_ctx_parameter_is_ignored(
        self, session: Session, artifact: Artifact
    ) -> None:
        """ctx parameter is accepted without error."""
        _add_version(session, artifact, content_hash="ctxtest2")

        repo = _make_repo(session)
        result = repo.list_versions_for_artifacts([artifact.id], ctx=object())
        assert len(result) == 1

    def test_session_closed_after_call(self, artifact: Artifact) -> None:
        """The session is closed after list_versions_for_artifacts returns."""
        mock_session = MagicMock(spec=Session)
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        repo = DbArtifactHistoryRepository(get_session=lambda: mock_session)
        repo.list_versions_for_artifacts(["skill:foo"])

        mock_session.close.assert_called_once()

    def test_session_closed_even_on_exception(self) -> None:
        """The session is closed even when the query raises."""
        mock_session = MagicMock(spec=Session)
        mock_session.query.side_effect = RuntimeError("crashed")

        repo = DbArtifactHistoryRepository(get_session=lambda: mock_session)
        with pytest.raises(RuntimeError):
            repo.list_versions_for_artifacts(["skill:foo"])

        mock_session.close.assert_called_once()


# ===========================================================================
# Tests — DbArtifactHistoryRepository (immutability / constructor)
# ===========================================================================


class TestDbArtifactHistoryRepositoryConstructor:
    """Constructor and session-factory injection."""

    def test_uses_provided_session_factory(self) -> None:
        """When a custom get_session callable is provided it is used."""
        mock_session = MagicMock(spec=Session)
        mock_session.query.return_value.filter.return_value.first.return_value = None

        calls = []

        def factory():
            calls.append(True)
            return mock_session

        repo = DbArtifactHistoryRepository(get_session=factory)
        repo.get_cache_artifact_by_uuid("anyuuid")

        assert len(calls) == 1

    def test_uses_default_session_factory_when_none_provided(self) -> None:
        """When get_session=None the module default is wired in (smoke test)."""
        # We only verify the constructor doesn't raise; the default factory is
        # the real model get_session which requires an initialised DB.
        repo = DbArtifactHistoryRepository(get_session=None)
        assert repo._get_session is not None

    def test_methods_are_read_only(self) -> None:
        """The repository exposes no write methods (confirms read-only contract)."""
        repo = DbArtifactHistoryRepository.__dict__
        write_verbs = {"create", "update", "delete", "save", "insert", "upsert"}
        for method_name in repo:
            if method_name.startswith("_"):
                continue
            for verb in write_verbs:
                assert not method_name.lower().startswith(verb), (
                    f"Unexpected write method found: {method_name}"
                )


# ===========================================================================
# Tests — EnterpriseArtifactHistoryStub
# ===========================================================================


class TestEnterpriseArtifactHistoryStub:
    """Verify stub behaviour: all methods return empty/None sentinels."""

    @pytest.fixture()
    def stub(self) -> EnterpriseArtifactHistoryStub:
        return EnterpriseArtifactHistoryStub()

    def test_get_cache_artifact_by_uuid_returns_none(
        self, stub: EnterpriseArtifactHistoryStub
    ) -> None:
        """get_cache_artifact_by_uuid always returns None."""
        result = stub.get_cache_artifact_by_uuid("any-uuid")
        assert result is None

    def test_get_cache_artifact_by_uuid_with_ctx_returns_none(
        self, stub: EnterpriseArtifactHistoryStub
    ) -> None:
        """ctx parameter is accepted without error."""
        result = stub.get_cache_artifact_by_uuid("any-uuid", ctx=object())
        assert result is None

    def test_list_cache_artifacts_by_name_type_returns_empty_list(
        self, stub: EnterpriseArtifactHistoryStub
    ) -> None:
        """list_cache_artifacts_by_name_type always returns []."""
        result = stub.list_cache_artifacts_by_name_type("any-name", "skill")
        assert result == []

    def test_list_cache_artifacts_by_name_type_with_ctx_returns_empty(
        self, stub: EnterpriseArtifactHistoryStub
    ) -> None:
        """ctx parameter is accepted without error."""
        result = stub.list_cache_artifacts_by_name_type(
            "any-name", "command", ctx=object()
        )
        assert result == []

    def test_list_versions_for_artifacts_returns_empty_list(
        self, stub: EnterpriseArtifactHistoryStub
    ) -> None:
        """list_versions_for_artifacts always returns []."""
        result = stub.list_versions_for_artifacts(["skill:foo", "command:bar"])
        assert result == []

    def test_list_versions_for_artifacts_empty_input_returns_empty(
        self, stub: EnterpriseArtifactHistoryStub
    ) -> None:
        """list_versions_for_artifacts with empty input still returns []."""
        result = stub.list_versions_for_artifacts([])
        assert result == []

    def test_list_versions_for_artifacts_with_ctx_returns_empty(
        self, stub: EnterpriseArtifactHistoryStub
    ) -> None:
        """ctx parameter is accepted without error."""
        result = stub.list_versions_for_artifacts(["skill:foo"], ctx=object())
        assert result == []

    def test_stub_satisfies_interface_contract(self) -> None:
        """EnterpriseArtifactHistoryStub is a valid IDbArtifactHistoryRepository."""
        from skillmeat.core.interfaces.repositories import IDbArtifactHistoryRepository

        stub = EnterpriseArtifactHistoryStub()
        assert isinstance(stub, IDbArtifactHistoryRepository)

    def test_stub_return_types_are_correct_types(
        self, stub: EnterpriseArtifactHistoryStub
    ) -> None:
        """Return values have the expected Python types (None and list)."""
        assert stub.get_cache_artifact_by_uuid("x") is None
        assert isinstance(stub.list_cache_artifacts_by_name_type("x", "skill"), list)
        assert isinstance(stub.list_versions_for_artifacts(["x"]), list)
