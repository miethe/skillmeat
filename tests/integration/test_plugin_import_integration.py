"""Integration tests for plugin import orchestration (CAI-P3-08).

Tests the full import_plugin_transactional pipeline against a real SQLite
in-memory database with real file operations. External services (GitHub,
network I/O) are the only mocked surface.

Test scenarios
--------------
1. Happy path: 3-child plugin imported for the first time.
   - Verifies CompositeArtifact, Artifact, ArtifactVersion, and
     CompositeMembership rows are all committed.
   - Verifies pinned_version_hash stored correctly on each membership.
   - Verifies ImportResult has children_imported=3, children_reused=0.

2. Deduplication: same plugin imported a second time with identical content.
   - Verifies children_reused=3, children_imported=0 on the second call.
   - Verifies no duplicate Artifact or ArtifactVersion rows are created.

3. Rollback on mid-import failure.
   - compute_artifact_hash raises on the second child.
   - Verifies the transaction is rolled back and no orphaned rows exist.
   - Verifies ImportResult.success=False.

4. API endpoint smoke test: GET /artifacts/{composite_id}/associations.
   - Imports a plugin via import_plugin_transactional.
   - Queries the associations endpoint.
   - Verifies 200 response, correct children list, pinned_version_hash present.

Infrastructure
--------------
- SQLite in-memory database created with Base.metadata.create_all (no Alembic).
- Real temporary directories for artifact files so compute_artifact_hash works.
- SQLite FK enforcement enabled via PRAGMA for every connection.
"""

from __future__ import annotations

import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, event as sa_event, text
from sqlalchemy.orm import Session, sessionmaker

from skillmeat.cache.models import (
    Artifact,
    ArtifactVersion,
    Base,
    Collection,
    CompositeArtifact,
    CompositeMembership,
    Project,
    create_db_engine,
)
from skillmeat.core.discovery import DiscoveredArtifact, DiscoveredGraph
from skillmeat.core.hashing import compute_artifact_hash
from skillmeat.core.importer import ImportResult, import_plugin_transactional


# =============================================================================
# Constants
# =============================================================================

PROJECT_ID = "proj-integration-001"
COLLECTION_ID = "col-integration-001"
SOURCE_URL = "github:test-owner/test-plugin"
PLUGIN_NAME = "git-workflow-pro"
COMPOSITE_ID = f"composite:{PLUGIN_NAME}"


# =============================================================================
# Engine / session fixtures
# =============================================================================


def _enable_fk_pragmas(dbapi_conn, connection_record):
    """Enable FK enforcement on every new SQLite connection."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture()
def db_engine():
    """In-memory SQLite engine with all ORM tables and FK enforcement."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    sa_event.listen(engine, "connect", _enable_fk_pragmas)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine) -> Generator[Session, None, None]:
    """Live session bound to the in-memory engine.

    Yields the session without closing it so callers can commit/rollback and
    then issue read-back queries in the same connection.
    """
    SessionLocal = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def seeded_project(db_session) -> str:
    """Insert a Project row that child Artifact rows can reference.

    Returns the project id string.
    """
    project = Project(
        id=PROJECT_ID,
        name="Integration Test Project",
        path="/tmp/integration-test-project",
        status="active",
    )
    db_session.add(project)
    db_session.flush()
    return PROJECT_ID


@pytest.fixture()
def seeded_collection(db_session) -> str:
    """Insert a Collection row needed by the associations endpoint.

    Returns the collection id string.
    """
    collection = Collection(
        id=COLLECTION_ID,
        name="default",
    )
    db_session.add(collection)
    db_session.flush()
    return COLLECTION_ID


# =============================================================================
# Artifact directory helpers
# =============================================================================


def _make_skill_dir(parent: Path, name: str) -> Path:
    """Create a minimal skill directory with a SKILL.md manifest.

    Returns the directory path.
    """
    skill_dir = parent / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\n---\n# {name}\nA test skill.\n",
        encoding="utf-8",
    )
    (skill_dir / "implementation.py").write_text(
        f"# implementation for {name}\npass\n",
        encoding="utf-8",
    )
    return skill_dir


def _make_command_file(parent: Path, name: str) -> Path:
    """Create a minimal command markdown file.

    Returns the file path.
    """
    cmd_file = parent / f"{name}.md"
    cmd_file.write_text(
        f"---\nname: {name}\n---\n# {name}\nA test command.\n",
        encoding="utf-8",
    )
    return cmd_file


def _make_discovered_artifact(
    name: str, artifact_type: str, path: str, description: str = ""
) -> DiscoveredArtifact:
    """Return a real DiscoveredArtifact Pydantic instance."""
    return DiscoveredArtifact(
        type=artifact_type,
        name=name,
        path=path,
        description=description or f"Test {artifact_type} {name}",
        discovered_at=datetime.now(timezone.utc),
    )


def _make_graph(
    plugin_name: str,
    children: List[DiscoveredArtifact],
    source_root: str,
) -> DiscoveredGraph:
    """Build a DiscoveredGraph with the given children."""
    parent = _make_discovered_artifact(
        name=plugin_name,
        artifact_type="composite",
        path=source_root,
        description="Integration test plugin",
    )
    links = [
        {
            "parent_id": f"composite:{plugin_name}",
            "child_id": f"{c.type}:{c.name}",
            "relationship_type": "contains",
        }
        for c in children
    ]
    return DiscoveredGraph(
        parent=parent,
        children=children,
        links=links,
        source_root=source_root,
    )


# =============================================================================
# Scenario 1: Happy path
# =============================================================================


class TestHappyPath:
    """3-child plugin import with no prior data."""

    @pytest.fixture()
    def artifact_workspace(self, tmp_path) -> Dict[str, Any]:
        """Create real artifact directories/files under tmp_path.

        Returns a dict with child DiscoveredArtifacts and computed hashes.
        """
        skill1_dir = _make_skill_dir(tmp_path, "canvas-skill")
        skill2_dir = _make_skill_dir(tmp_path, "deploy-skill")
        cmd_file = _make_command_file(tmp_path, "build-cmd")

        children = [
            _make_discovered_artifact("canvas-skill", "skill", str(skill1_dir)),
            _make_discovered_artifact("deploy-skill", "skill", str(skill2_dir)),
            _make_discovered_artifact("build-cmd", "command", str(cmd_file)),
        ]

        expected_hashes = [compute_artifact_hash(c.path) for c in children]

        return {
            "children": children,
            "expected_hashes": expected_hashes,
            "source_root": str(tmp_path),
        }

    def test_all_rows_committed(
        self,
        db_session,
        seeded_project,
        seeded_collection,
        artifact_workspace,
    ):
        """Verify CompositeArtifact, Artifact, ArtifactVersion, and
        CompositeMembership rows are all present after the import.
        """
        graph = _make_graph(
            PLUGIN_NAME,
            artifact_workspace["children"],
            artifact_workspace["source_root"],
        )

        result = import_plugin_transactional(
            discovered_graph=graph,
            source_url=SOURCE_URL,
            session=db_session,
            project_id=PROJECT_ID,
            collection_id=COLLECTION_ID,
        )

        assert result.success is True, f"Import failed: {result.errors}"

        # -- CompositeArtifact -----------------------------------------------
        composite = (
            db_session.query(CompositeArtifact)
            .filter(CompositeArtifact.id == COMPOSITE_ID)
            .first()
        )
        assert composite is not None, "CompositeArtifact row missing"
        assert composite.composite_type == "plugin"
        assert composite.collection_id == COLLECTION_ID

        # -- Artifact + ArtifactVersion rows (3 children) -------------------
        artifact_rows = (
            db_session.query(Artifact).filter(Artifact.project_id == PROJECT_ID).all()
        )
        assert (
            len(artifact_rows) == 3
        ), f"Expected 3 Artifact rows, found {len(artifact_rows)}"

        version_rows = db_session.query(ArtifactVersion).all()
        assert (
            len(version_rows) == 3
        ), f"Expected 3 ArtifactVersion rows, found {len(version_rows)}"

        # -- CompositeMembership rows -----------------------------------------
        membership_rows = (
            db_session.query(CompositeMembership)
            .filter(CompositeMembership.composite_id == COMPOSITE_ID)
            .all()
        )
        assert (
            len(membership_rows) == 3
        ), f"Expected 3 CompositeMembership rows, found {len(membership_rows)}"

    def test_pinned_version_hash_stored(
        self,
        db_session,
        seeded_project,
        seeded_collection,
        artifact_workspace,
    ):
        """pinned_version_hash on each membership must equal the child's
        actual content hash computed by compute_artifact_hash.
        """
        graph = _make_graph(
            PLUGIN_NAME,
            artifact_workspace["children"],
            artifact_workspace["source_root"],
        )

        result = import_plugin_transactional(
            discovered_graph=graph,
            source_url=SOURCE_URL,
            session=db_session,
            project_id=PROJECT_ID,
            collection_id=COLLECTION_ID,
        )

        assert result.success is True, f"Import failed: {result.errors}"

        memberships = (
            db_session.query(CompositeMembership)
            .filter(CompositeMembership.composite_id == COMPOSITE_ID)
            .all()
        )

        stored_hashes = {m.pinned_version_hash for m in memberships}
        expected_hashes = set(artifact_workspace["expected_hashes"])

        assert (
            stored_hashes == expected_hashes
        ), f"Hash mismatch.\nStored:   {stored_hashes}\nExpected: {expected_hashes}"
        # All hashes must be non-null 64-char hex strings
        for h in stored_hashes:
            assert h is not None
            assert len(h) == 64
            assert all(c in "0123456789abcdef" for c in h)

    def test_import_result_counts(
        self,
        db_session,
        seeded_project,
        seeded_collection,
        artifact_workspace,
    ):
        """ImportResult must report children_imported=3, children_reused=0."""
        graph = _make_graph(
            PLUGIN_NAME,
            artifact_workspace["children"],
            artifact_workspace["source_root"],
        )

        result = import_plugin_transactional(
            discovered_graph=graph,
            source_url=SOURCE_URL,
            session=db_session,
            project_id=PROJECT_ID,
            collection_id=COLLECTION_ID,
        )

        assert result.success is True, f"Import failed: {result.errors}"
        assert result.plugin_id == COMPOSITE_ID
        assert result.children_imported == 3
        assert result.children_reused == 0
        assert result.errors == []
        assert result.transaction_id  # non-empty UUID string


# =============================================================================
# Scenario 2: Deduplication — same content imported twice
# =============================================================================


class TestDeduplication:
    """Re-importing the same plugin should reuse existing artifacts."""

    @pytest.fixture()
    def artifact_workspace(self, tmp_path) -> Dict[str, Any]:
        """Three real artifact paths used for both imports."""
        skill1_dir = _make_skill_dir(tmp_path, "shared-skill-a")
        skill2_dir = _make_skill_dir(tmp_path, "shared-skill-b")
        cmd_file = _make_command_file(tmp_path, "shared-cmd")

        children = [
            _make_discovered_artifact("shared-skill-a", "skill", str(skill1_dir)),
            _make_discovered_artifact("shared-skill-b", "skill", str(skill2_dir)),
            _make_discovered_artifact("shared-cmd", "command", str(cmd_file)),
        ]
        return {
            "children": children,
            "source_root": str(tmp_path),
        }

    def test_second_import_reuses_all_children(
        self,
        db_session,
        seeded_project,
        seeded_collection,
        artifact_workspace,
    ):
        """Second import of identical content must yield children_reused=3."""
        plugin_name = "dedup-plugin"
        graph = _make_graph(
            plugin_name,
            artifact_workspace["children"],
            artifact_workspace["source_root"],
        )

        # First import
        result1 = import_plugin_transactional(
            discovered_graph=graph,
            source_url=SOURCE_URL,
            session=db_session,
            project_id=PROJECT_ID,
            collection_id=COLLECTION_ID,
        )
        assert result1.success is True, f"First import failed: {result1.errors}"
        assert result1.children_imported == 3
        assert result1.children_reused == 0

        # Second import — same graph, same content hashes
        result2 = import_plugin_transactional(
            discovered_graph=graph,
            source_url=SOURCE_URL,
            session=db_session,
            project_id=PROJECT_ID,
            collection_id=COLLECTION_ID,
        )
        assert result2.success is True, f"Second import failed: {result2.errors}"
        assert result2.children_imported == 0
        assert result2.children_reused == 3

    def test_no_duplicate_artifact_rows_after_two_imports(
        self,
        db_session,
        seeded_project,
        seeded_collection,
        artifact_workspace,
    ):
        """Two imports of the same content must not create duplicate Artifact rows."""
        plugin_name = "no-dup-plugin"
        graph = _make_graph(
            plugin_name,
            artifact_workspace["children"],
            artifact_workspace["source_root"],
        )

        import_plugin_transactional(
            discovered_graph=graph,
            source_url=SOURCE_URL,
            session=db_session,
            project_id=PROJECT_ID,
            collection_id=COLLECTION_ID,
        )
        import_plugin_transactional(
            discovered_graph=graph,
            source_url=SOURCE_URL,
            session=db_session,
            project_id=PROJECT_ID,
            collection_id=COLLECTION_ID,
        )

        # Should still be exactly 3 Artifact rows (one per child)
        artifact_rows = (
            db_session.query(Artifact).filter(Artifact.project_id == PROJECT_ID).all()
        )
        assert (
            len(artifact_rows) == 3
        ), f"Expected 3 Artifact rows after 2 imports, found {len(artifact_rows)}"

        # Should still be exactly 3 ArtifactVersion rows
        version_rows = db_session.query(ArtifactVersion).all()
        assert (
            len(version_rows) == 3
        ), f"Expected 3 ArtifactVersion rows, found {len(version_rows)}"


# =============================================================================
# Scenario 3: Rollback on mid-import failure
# =============================================================================


class TestRollback:
    """When hashing fails mid-import the entire transaction must be rolled back."""

    @pytest.fixture()
    def artifact_workspace(self, tmp_path) -> Dict[str, Any]:
        """Three artifact paths; the second will trigger a hash failure."""
        skill1_dir = _make_skill_dir(tmp_path, "rollback-skill-a")
        skill2_dir = _make_skill_dir(tmp_path, "rollback-skill-b")
        cmd_file = _make_command_file(tmp_path, "rollback-cmd")

        children = [
            _make_discovered_artifact("rollback-skill-a", "skill", str(skill1_dir)),
            _make_discovered_artifact("rollback-skill-b", "skill", str(skill2_dir)),
            _make_discovered_artifact("rollback-cmd", "command", str(cmd_file)),
        ]
        return {
            "children": children,
            "source_root": str(tmp_path),
        }

    def test_failure_returns_success_false(
        self,
        db_session,
        seeded_project,
        seeded_collection,
        artifact_workspace,
    ):
        """ImportResult.success must be False when compute_artifact_hash raises
        on the second child.
        """
        graph = _make_graph(
            "rollback-plugin",
            artifact_workspace["children"],
            artifact_workspace["source_root"],
        )

        real_hash = compute_artifact_hash

        call_count = 0

        def _hash_with_fault(path: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise FileNotFoundError(f"Simulated hash failure on path: {path}")
            return real_hash(path)

        with patch(
            "skillmeat.core.hashing.compute_artifact_hash",
            side_effect=_hash_with_fault,
        ):
            result = import_plugin_transactional(
                discovered_graph=graph,
                source_url=SOURCE_URL,
                session=db_session,
                project_id=PROJECT_ID,
                collection_id=COLLECTION_ID,
            )

        assert result.success is False
        assert len(result.errors) >= 1

    def test_no_orphaned_artifacts_after_rollback(
        self,
        db_session,
        seeded_project,
        seeded_collection,
        artifact_workspace,
    ):
        """After a mid-import failure, the DB must contain zero new rows for
        Artifact, ArtifactVersion, CompositeArtifact, and CompositeMembership.
        """
        graph = _make_graph(
            "rollback-plugin",
            artifact_workspace["children"],
            artifact_workspace["source_root"],
        )

        real_hash = compute_artifact_hash
        call_count = 0

        def _hash_with_fault(path: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise FileNotFoundError(f"Simulated hash failure on path: {path}")
            return real_hash(path)

        with patch(
            "skillmeat.core.hashing.compute_artifact_hash",
            side_effect=_hash_with_fault,
        ):
            import_plugin_transactional(
                discovered_graph=graph,
                source_url=SOURCE_URL,
                session=db_session,
                project_id=PROJECT_ID,
                collection_id=COLLECTION_ID,
            )

        # Rollback means the session state is clean; start a fresh query
        # against the same connection to confirm nothing was persisted.
        artifact_rows = (
            db_session.query(Artifact).filter(Artifact.project_id == PROJECT_ID).all()
        )
        assert (
            artifact_rows == []
        ), f"Orphaned Artifact rows after rollback: {[r.id for r in artifact_rows]}"

        composite_rows = (
            db_session.query(CompositeArtifact)
            .filter(CompositeArtifact.id == f"composite:rollback-plugin")
            .all()
        )
        assert (
            composite_rows == []
        ), f"Orphaned CompositeArtifact rows after rollback: {[r.id for r in composite_rows]}"

        membership_rows = db_session.query(CompositeMembership).all()
        assert (
            membership_rows == []
        ), f"Orphaned CompositeMembership rows after rollback: {membership_rows}"

        version_rows = db_session.query(ArtifactVersion).all()
        assert (
            version_rows == []
        ), f"Orphaned ArtifactVersion rows after rollback: {version_rows}"


# =============================================================================
# Scenario 4: API endpoint — GET /artifacts/{plugin_id}/associations
# =============================================================================


class TestAssociationsEndpoint:
    """After a successful import, the associations endpoint must return the
    imported children with their pinned_version_hash values.
    """

    @pytest.fixture()
    def temp_db_path(self, tmp_path) -> Path:
        """Return a path to a fresh SQLite file (not in-memory) so the test
        client and the import session share the same persistent store.
        """
        return tmp_path / "test.db"

    @pytest.fixture()
    def file_engine(self, temp_db_path):
        """File-based SQLite engine with FK enforcement and all tables created."""
        engine = create_db_engine(str(temp_db_path))
        sa_event.listen(engine, "connect", _enable_fk_pragmas)
        Base.metadata.create_all(engine)
        yield engine
        engine.dispose()

    @pytest.fixture()
    def file_session(self, file_engine) -> Generator[Session, None, None]:
        """Session bound to the file-based engine."""
        SessionLocal = sessionmaker(bind=file_engine, autocommit=False, autoflush=False)
        session = SessionLocal()
        yield session
        session.close()

    @pytest.fixture()
    def imported_plugin(
        self, tmp_path, temp_db_path, file_session, file_engine
    ) -> Dict[str, Any]:
        """Seed a Project + Collection, build real artifact dirs, run the import,
        and return identifying metadata for assertions.
        """
        # Seed Project
        file_session.add(
            Project(
                id=PROJECT_ID,
                name="API Test Project",
                path="/tmp/api-test-project",
                status="active",
            )
        )
        # Seed Collection
        file_session.add(
            Collection(
                id=COLLECTION_ID,
                name="default",
            )
        )
        file_session.flush()

        # Build real artifact files
        skill1_dir = _make_skill_dir(tmp_path, "api-skill-one")
        skill2_dir = _make_skill_dir(tmp_path, "api-skill-two")
        cmd_file = _make_command_file(tmp_path, "api-cmd")

        children = [
            _make_discovered_artifact("api-skill-one", "skill", str(skill1_dir)),
            _make_discovered_artifact("api-skill-two", "skill", str(skill2_dir)),
            _make_discovered_artifact("api-cmd", "command", str(cmd_file)),
        ]
        expected_hashes = [compute_artifact_hash(c.path) for c in children]

        graph = _make_graph(
            PLUGIN_NAME,
            children,
            str(tmp_path),
        )

        result = import_plugin_transactional(
            discovered_graph=graph,
            source_url=SOURCE_URL,
            session=file_session,
            project_id=PROJECT_ID,
            collection_id=COLLECTION_ID,
        )
        assert result.success is True, f"Fixture import failed: {result.errors}"

        return {
            "composite_id": COMPOSITE_ID,
            "collection_id": COLLECTION_ID,
            "expected_hashes": expected_hashes,
            "db_path": str(temp_db_path),
            "engine": file_engine,
        }

    def test_associations_returns_200_with_children(self, imported_plugin, tmp_path):
        """GET /api/v1/artifacts/{composite_id}/associations returns HTTP 200 with
        the three imported children.
        """
        from fastapi.testclient import TestClient
        from unittest.mock import patch as _patch, MagicMock

        from skillmeat.api.config import APISettings, Environment, get_settings
        from skillmeat.api.middleware.auth import verify_token
        from skillmeat.api.server import create_app
        from skillmeat.cache.composite_repository import CompositeMembershipRepository
        from sqlalchemy.orm import sessionmaker

        db_path = imported_plugin["db_path"]
        col_id = imported_plugin["collection_id"]
        composite_id = imported_plugin["composite_id"]
        engine = imported_plugin["engine"]

        settings = APISettings(env=Environment.TESTING, api_key_enabled=False)
        app = create_app(settings)
        app.dependency_overrides[get_settings] = lambda: settings
        app.dependency_overrides[verify_token] = lambda: "test-token"

        # Build a CollectionManager mock that satisfies the endpoint lookup
        mock_artifact = MagicMock()
        mock_artifact.name = "git-workflow-pro"
        mock_artifact.type = "composite"
        mock_collection = MagicMock()
        mock_collection.find_artifact.return_value = mock_artifact
        mock_mgr = MagicMock()
        mock_mgr.get_active_collection_name.return_value = "default"
        mock_mgr.list_collections.return_value = ["default"]
        mock_mgr.load_collection.return_value = mock_collection

        from skillmeat.api.dependencies import get_collection_manager

        app.dependency_overrides[get_collection_manager] = lambda: mock_mgr

        # Wire the real composite repository and a real session to the temp DB
        with _patch("skillmeat.cache.migrations.run_migrations"):
            real_repo = CompositeMembershipRepository(db_path=db_path)

        SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

        def _get_session():
            return SessionLocal()

        with (
            _patch(
                "skillmeat.api.routers.artifacts.CompositeMembershipRepository",
                return_value=real_repo,
            ),
            _patch(
                "skillmeat.api.routers.artifacts.get_session",
                side_effect=_get_session,
            ),
        ):
            with TestClient(app) as client:
                resp = client.get(
                    f"/api/v1/artifacts/{composite_id}/associations",
                    params={"collection_id": col_id},
                )

        assert (
            resp.status_code == 200
        ), f"Expected 200 but got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["artifact_id"] == composite_id

        children = body["children"]
        assert (
            len(children) == 3
        ), f"Expected 3 children, got {len(children)}: {children}"

    def test_associations_children_have_pinned_hash(self, imported_plugin, tmp_path):
        """Each child item in the associations response must carry the correct
        pinned_version_hash value matching what was stored at import time.
        """
        from fastapi.testclient import TestClient
        from unittest.mock import patch as _patch, MagicMock

        from skillmeat.api.config import APISettings, Environment, get_settings
        from skillmeat.api.middleware.auth import verify_token
        from skillmeat.api.server import create_app
        from skillmeat.cache.composite_repository import CompositeMembershipRepository
        from sqlalchemy.orm import sessionmaker

        db_path = imported_plugin["db_path"]
        col_id = imported_plugin["collection_id"]
        composite_id = imported_plugin["composite_id"]
        expected_hashes = set(imported_plugin["expected_hashes"])
        engine = imported_plugin["engine"]

        settings = APISettings(env=Environment.TESTING, api_key_enabled=False)
        app = create_app(settings)
        app.dependency_overrides[get_settings] = lambda: settings
        app.dependency_overrides[verify_token] = lambda: "test-token"

        mock_artifact = MagicMock()
        mock_artifact.name = "git-workflow-pro"
        mock_artifact.type = "composite"
        mock_collection = MagicMock()
        mock_collection.find_artifact.return_value = mock_artifact
        mock_mgr = MagicMock()
        mock_mgr.get_active_collection_name.return_value = "default"
        mock_mgr.list_collections.return_value = ["default"]
        mock_mgr.load_collection.return_value = mock_collection

        from skillmeat.api.dependencies import get_collection_manager

        app.dependency_overrides[get_collection_manager] = lambda: mock_mgr

        with _patch("skillmeat.cache.migrations.run_migrations"):
            real_repo = CompositeMembershipRepository(db_path=db_path)

        SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

        def _get_session():
            return SessionLocal()

        with (
            _patch(
                "skillmeat.api.routers.artifacts.CompositeMembershipRepository",
                return_value=real_repo,
            ),
            _patch(
                "skillmeat.api.routers.artifacts.get_session",
                side_effect=_get_session,
            ),
        ):
            with TestClient(app) as client:
                resp = client.get(
                    f"/api/v1/artifacts/{composite_id}/associations",
                    params={"collection_id": col_id},
                )

        assert resp.status_code == 200
        body = resp.json()

        response_hashes = {
            item["pinned_version_hash"]
            for item in body["children"]
            if item.get("pinned_version_hash") is not None
        }
        assert response_hashes == expected_hashes, (
            f"pinned_version_hash mismatch.\n"
            f"Response: {response_hashes}\nExpected: {expected_hashes}"
        )
