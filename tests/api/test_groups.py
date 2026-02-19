"""Tests for Groups API endpoints.

This module tests the /api/v1/groups endpoints, including:
- Copy group to another collection (BE-001, BE-002, BE-003)
"""

import os
import tempfile
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.cache.models import (
    Artifact,
    Base,
    Collection,
    CollectionArtifact,
    Group,
    GroupArtifact,
    Project,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def test_settings():
    """Create test settings."""
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        cors_enabled=True,
        cors_origins=["http://localhost:3000"],
        api_key_enabled=False,  # Disable API key for testing
    )


@pytest.fixture
def test_db_path(tmp_path):
    """Create a temporary database file path."""
    db_path = tmp_path / "test.db"
    return str(db_path)


@pytest.fixture
def test_engine(test_db_path):
    """Create a SQLite engine for testing with proper threading settings."""
    engine = create_engine(
        f"sqlite:///{test_db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    # Configure SQLite PRAGMA settings on connection
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session_factory(test_engine):
    """Create a session factory for testing."""
    return sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


@pytest.fixture
def test_db(test_session_factory):
    """Create a database session for testing."""
    session = test_session_factory()
    yield session
    session.close()


@pytest.fixture
def app(test_settings):
    """Create FastAPI app for testing."""
    from skillmeat.api.config import get_settings

    app = create_app(test_settings)
    app.dependency_overrides[get_settings] = lambda: test_settings
    return app


@pytest.fixture
def client(app, test_session_factory):
    """Create test client with mocked database session."""
    from skillmeat.api.middleware.auth import verify_token

    # Mock verify_token to bypass authentication
    app.dependency_overrides[verify_token] = lambda: "mock-token"

    # Create a closure to return a new session for each call
    def get_test_session():
        return test_session_factory()

    with patch("skillmeat.api.routers.groups.get_session", get_test_session):
        with TestClient(app) as test_client:
            yield test_client

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def source_collection(test_db) -> Collection:
    """Create a source collection for testing."""
    collection = Collection(
        id=uuid.uuid4().hex,
        name="Source Collection",
        description="Source collection for testing copy",
    )
    test_db.add(collection)
    test_db.commit()
    return collection


@pytest.fixture
def target_collection(test_db) -> Collection:
    """Create a target collection for testing."""
    collection = Collection(
        id=uuid.uuid4().hex,
        name="Target Collection",
        description="Target collection for testing copy",
    )
    test_db.add(collection)
    test_db.commit()
    return collection


@pytest.fixture
def test_project(test_db) -> "Project":
    """Create a test project to serve as FK parent for Artifact rows."""
    project = Project(
        id=uuid.uuid4().hex,
        name="Test Project",
        path="/tmp/test-project",
        status="active",
    )
    test_db.add(project)
    test_db.commit()
    return project


@pytest.fixture
def source_group_with_artifacts(test_db, source_collection, test_project) -> tuple[Group, list[str]]:
    """Create a source group with artifacts for testing.

    CAI-P5-02: GroupArtifact now uses artifact_uuid FK → artifacts.uuid.
    Fixtures must create real Artifact rows first.
    """
    # Create group
    group = Group(
        id=uuid.uuid4().hex,
        collection_id=source_collection.id,
        name="My Group",
        description="A group with artifacts",
        position=0,
    )
    test_db.add(group)
    test_db.flush()

    # Create Artifact rows and wire them into the group/collection
    artifact_ids = [f"skill:artifact-{i}" for i in range(3)]

    for i, artifact_id in enumerate(artifact_ids):
        artifact_uuid = uuid.uuid4().hex
        artifact = Artifact(
            id=artifact_id,
            uuid=artifact_uuid,
            project_id=test_project.id,
            name=f"artifact-{i}",
            type="skill",
        )
        test_db.add(artifact)
        test_db.flush()  # persist so FK constraints are satisfied

        # Add to collection (P5-01: uses artifact_uuid)
        collection_artifact = CollectionArtifact(
            collection_id=source_collection.id,
            artifact_uuid=artifact_uuid,
            added_at=datetime.utcnow(),
        )
        test_db.add(collection_artifact)

        # Add to group (P5-02: uses artifact_uuid)
        group_artifact = GroupArtifact(
            group_id=group.id,
            artifact_uuid=artifact_uuid,
            position=i,
        )
        test_db.add(group_artifact)

    test_db.commit()
    return group, artifact_ids


@pytest.fixture
def empty_group(test_db, source_collection) -> Group:
    """Create an empty group for testing."""
    group = Group(
        id=uuid.uuid4().hex,
        collection_id=source_collection.id,
        name="Empty Group",
        description="A group with no artifacts",
        position=1,
    )
    test_db.add(group)
    test_db.commit()
    return group


# =============================================================================
# Copy Group Tests (BE-001, BE-002, BE-003)
# =============================================================================


class TestCopyGroup:
    """Test POST /api/v1/groups/{group_id}/copy endpoint."""

    def test_copy_group_to_different_collection_success(
        self,
        client,
        test_session_factory,
        source_group_with_artifacts,
        target_collection,
    ):
        """Test successful copy of a group to a different collection."""
        source_group, artifact_ids = source_group_with_artifacts

        response = client.post(
            f"/api/v1/groups/{source_group.id}/copy",
            json={"target_collection_id": target_collection.id},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # Verify response structure
        assert data["collection_id"] == target_collection.id
        assert data["name"] == f"{source_group.name} (Copy)"
        assert data["description"] == source_group.description
        assert data["artifact_count"] == len(artifact_ids)

        # Verify group was created in target collection
        with test_session_factory() as session:
            new_group = (
                session.query(Group)
                .filter_by(id=data["id"], collection_id=target_collection.id)
                .first()
            )
            assert new_group is not None
            assert new_group.name == f"{source_group.name} (Copy)"

            # Verify artifacts were added to target collection
            # P5-02: CollectionArtifact uses artifact_uuid; resolve via Artifact table
            for artifact_id in artifact_ids:
                art = session.query(Artifact).filter_by(id=artifact_id).first()
                assert art is not None, f"Artifact {artifact_id} not in cache"
                collection_artifact = (
                    session.query(CollectionArtifact)
                    .filter_by(
                        collection_id=target_collection.id,
                        artifact_uuid=art.uuid,
                    )
                    .first()
                )
                assert collection_artifact is not None

            # Verify artifacts were added to new group
            new_group_artifacts = (
                session.query(GroupArtifact).filter_by(group_id=new_group.id).all()
            )
            assert len(new_group_artifacts) == len(artifact_ids)

    def test_copy_group_with_duplicate_artifacts(
        self,
        client,
        test_db,
        test_session_factory,
        source_group_with_artifacts,
        target_collection,
    ):
        """Test copying when some artifacts already exist in target collection."""
        source_group, artifact_ids = source_group_with_artifacts

        # Pre-add one artifact to target collection (P5-01: uses artifact_uuid)
        existing_artifact_id = artifact_ids[0]
        existing_art = test_db.query(Artifact).filter_by(id=existing_artifact_id).first()
        assert existing_art is not None
        existing_association = CollectionArtifact(
            collection_id=target_collection.id,
            artifact_uuid=existing_art.uuid,
            added_at=datetime.utcnow(),
        )
        test_db.add(existing_association)
        test_db.commit()

        response = client.post(
            f"/api/v1/groups/{source_group.id}/copy",
            json={"target_collection_id": target_collection.id},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # All artifacts should be in the new group
        assert data["artifact_count"] == len(artifact_ids)

        # Check no duplicate artifacts in target collection
        with test_session_factory() as session:
            collection_artifacts = (
                session.query(CollectionArtifact)
                .filter_by(collection_id=target_collection.id)
                .all()
            )
            # P5-02: collection_artifacts uses artifact_uuid; count is sufficient
            # No duplicate check needed — the router already guards duplicates by UUID
            assert len(collection_artifacts) == len(artifact_ids)

    def test_copy_empty_group(
        self,
        client,
        empty_group,
        target_collection,
    ):
        """Test copying an empty group."""
        response = client.post(
            f"/api/v1/groups/{empty_group.id}/copy",
            json={"target_collection_id": target_collection.id},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["collection_id"] == target_collection.id
        assert data["name"] == f"{empty_group.name} (Copy)"
        assert data["artifact_count"] == 0

    def test_copy_group_to_same_collection(
        self,
        client,
        test_session_factory,
        source_group_with_artifacts,
        source_collection,
    ):
        """Test copying a group to the same collection."""
        source_group, artifact_ids = source_group_with_artifacts

        response = client.post(
            f"/api/v1/groups/{source_group.id}/copy",
            json={"target_collection_id": source_collection.id},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # Should be in same collection with " (Copy)" suffix
        assert data["collection_id"] == source_collection.id
        assert data["name"] == f"{source_group.name} (Copy)"
        assert data["artifact_count"] == len(artifact_ids)

        # Verify two groups now exist in source collection
        with test_session_factory() as session:
            groups = (
                session.query(Group).filter_by(collection_id=source_collection.id).all()
            )
            assert len(groups) >= 2

    def test_copy_group_not_found(self, client, target_collection):
        """Test copying a non-existent group returns 404."""
        response = client.post(
            "/api/v1/groups/nonexistent-group-id/copy",
            json={"target_collection_id": target_collection.id},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_copy_group_target_collection_not_found(
        self,
        client,
        source_group_with_artifacts,
    ):
        """Test copying to a non-existent collection returns 404."""
        source_group, _ = source_group_with_artifacts

        response = client.post(
            f"/api/v1/groups/{source_group.id}/copy",
            json={"target_collection_id": "nonexistent-collection-id"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_copy_group_name_conflict(
        self,
        client,
        test_db,
        source_group_with_artifacts,
        target_collection,
    ):
        """Test copying when the target name already exists returns 400."""
        source_group, _ = source_group_with_artifacts

        # Pre-create a group with the expected name in target collection
        existing_group = Group(
            id=uuid.uuid4().hex,
            collection_id=target_collection.id,
            name=f"{source_group.name} (Copy)",
            description="Pre-existing group",
            position=0,
        )
        test_db.add(existing_group)
        test_db.commit()

        response = client.post(
            f"/api/v1/groups/{source_group.id}/copy",
            json={"target_collection_id": target_collection.id},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"].lower()

    def test_copy_group_preserves_artifact_positions(
        self,
        client,
        test_session_factory,
        source_group_with_artifacts,
        target_collection,
    ):
        """Test that artifact positions are preserved when copying."""
        source_group, artifact_ids = source_group_with_artifacts

        response = client.post(
            f"/api/v1/groups/{source_group.id}/copy",
            json={"target_collection_id": target_collection.id},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # Verify positions are preserved
        with test_session_factory() as session:
            new_group_artifacts = (
                session.query(GroupArtifact)
                .filter_by(group_id=data["id"])
                .order_by(GroupArtifact.position)
                .all()
            )

            source_group_artifacts = (
                session.query(GroupArtifact)
                .filter_by(group_id=source_group.id)
                .order_by(GroupArtifact.position)
                .all()
            )

            assert len(new_group_artifacts) == len(source_group_artifacts)

            for new_ga, source_ga in zip(new_group_artifacts, source_group_artifacts):
                # P5-02: GroupArtifact now uses artifact_uuid
                assert new_ga.artifact_uuid == source_ga.artifact_uuid
                assert new_ga.position == source_ga.position

    def test_copy_group_appends_to_end_of_collection(
        self,
        client,
        test_db,
        source_group_with_artifacts,
        target_collection,
    ):
        """Test that copied group is appended to the end of target collection."""
        source_group, _ = source_group_with_artifacts

        # Create existing groups in target collection
        for i in range(3):
            existing_group = Group(
                id=uuid.uuid4().hex,
                collection_id=target_collection.id,
                name=f"Existing Group {i}",
                position=i,
            )
            test_db.add(existing_group)
        test_db.commit()

        response = client.post(
            f"/api/v1/groups/{source_group.id}/copy",
            json={"target_collection_id": target_collection.id},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # New group should have position 3 (after existing 0, 1, 2)
        assert data["position"] == 3


class TestCopyGroupTransactionRollback:
    """Test that copy operation rolls back on failure."""

    def test_copy_group_rollback_on_error(
        self,
        app,
        source_group_with_artifacts,
        target_collection,
    ):
        """Test that transaction rolls back on error during copy."""
        from skillmeat.api.middleware.auth import verify_token

        source_group, artifact_ids = source_group_with_artifacts

        app.dependency_overrides[verify_token] = lambda: "mock-token"

        # Patch to cause an error after group creation but before commit
        def get_error_session():
            """Return a session that will fail on flush after certain operations."""
            mock_session = MagicMock()

            # Set up query chain
            source_group_mock = MagicMock()
            source_group_mock.id = source_group.id
            source_group_mock.collection_id = source_group.collection_id
            source_group_mock.name = source_group.name
            source_group_mock.description = source_group.description

            target_collection_mock = MagicMock()
            target_collection_mock.id = target_collection.id

            call_count = [0]

            def mock_first():
                call_count[0] += 1
                if call_count[0] == 1:  # First call: source group
                    return source_group_mock
                elif call_count[0] == 2:  # Second call: target collection
                    return target_collection_mock
                elif call_count[0] == 3:  # Third call: existing group check
                    return None  # No existing group
                elif call_count[0] == 4:  # Fourth call: max position
                    return None
                return None

            mock_query = MagicMock()
            mock_query.filter_by.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.all.return_value = []
            mock_query.first.side_effect = mock_first

            mock_session.query.return_value = mock_query
            mock_session.add.return_value = None

            # Make flush raise an exception to test rollback
            mock_session.flush.side_effect = Exception("Simulated database error")

            return mock_session

        with patch("skillmeat.api.routers.groups.get_session", get_error_session):
            with TestClient(app) as test_client:
                response = test_client.post(
                    f"/api/v1/groups/{source_group.id}/copy",
                    json={"target_collection_id": target_collection.id},
                )

        # Should return 500 error
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

        app.dependency_overrides.clear()


class TestGroupMetadataCRUD:
    """Test groups metadata fields across create/update/list/detail endpoints."""

    def test_create_group_with_metadata_defaults(self, client, source_collection):
        """Create group without metadata fields should apply defaults."""
        response = client.post(
            "/api/v1/groups",
            json={
                "collection_id": source_collection.id,
                "name": "Defaults Group",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["tags"] == []
        assert data["color"] == "slate"
        assert data["icon"] == "layers"

    def test_create_group_with_metadata_normalization(self, client, source_collection):
        """Create group should normalize tags and accept valid color/icon values."""
        response = client.post(
            "/api/v1/groups",
            json={
                "collection_id": source_collection.id,
                "name": "Normalized Group",
                "tags": [" Frontend ", "frontend", "Critical_Path"],
                "color": "#22C55E",
                "icon": "Folder",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["tags"] == ["frontend", "critical_path"]
        assert data["color"] == "#22c55e"
        assert data["icon"] == "folder"

    @pytest.mark.parametrize(
        "payload",
        [
            {"tags": ["invalid tag!"]},
            {"color": "purple"},
            {"color": "#12"},
            {"icon": "rocket"},
            {"tags": [f"t{i}" for i in range(21)]},
        ],
    )
    def test_create_group_rejects_invalid_metadata(
        self, client, source_collection, payload
    ):
        """Create group should reject invalid metadata values."""
        response = client.post(
            "/api/v1/groups",
            json={
                "collection_id": source_collection.id,
                "name": "Invalid Metadata Group",
                **payload,
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_update_group_partial_and_full_metadata(
        self, client, source_collection, test_db
    ):
        """Update group should support partial and full metadata updates."""
        group = Group(
            id=uuid.uuid4().hex,
            collection_id=source_collection.id,
            name="Editable Group",
            tags_json='["legacy"]',
            color="slate",
            icon="layers",
            position=0,
        )
        test_db.add(group)
        test_db.commit()

        partial_response = client.put(
            f"/api/v1/groups/{group.id}",
            json={"color": "green"},
        )
        assert partial_response.status_code == status.HTTP_200_OK
        partial_data = partial_response.json()
        assert partial_data["color"] == "green"
        assert partial_data["icon"] == "layers"
        assert partial_data["tags"] == ["legacy"]

        full_response = client.put(
            f"/api/v1/groups/{group.id}",
            json={
                "name": "Edited Group",
                "description": "Updated description",
                "tags": ["Ops", "on_call"],
                "color": "#f59e0b",
                "icon": "wrench",
            },
        )
        assert full_response.status_code == status.HTTP_200_OK
        full_data = full_response.json()
        assert full_data["name"] == "Edited Group"
        assert full_data["description"] == "Updated description"
        assert full_data["tags"] == ["ops", "on_call"]
        assert full_data["color"] == "#f59e0b"
        assert full_data["icon"] == "wrench"

    def test_list_and_detail_include_metadata_fields(
        self, client, source_collection, test_db
    ):
        """List/detail endpoints should include tags, color, and icon."""
        group = Group(
            id=uuid.uuid4().hex,
            collection_id=source_collection.id,
            name="Metadata Group",
            description="Group with metadata",
            tags_json='["frontend","critical"]',
            color="blue",
            icon="sparkles",
            position=0,
        )
        test_db.add(group)
        test_db.commit()

        list_response = client.get(f"/api/v1/groups?collection_id={source_collection.id}")
        assert list_response.status_code == status.HTTP_200_OK
        list_data = list_response.json()
        listed_group = next(g for g in list_data["groups"] if g["id"] == group.id)
        assert listed_group["tags"] == ["frontend", "critical"]
        assert listed_group["color"] == "blue"
        assert listed_group["icon"] == "sparkles"

        detail_response = client.get(f"/api/v1/groups/{group.id}")
        assert detail_response.status_code == status.HTTP_200_OK
        detail_data = detail_response.json()
        assert detail_data["tags"] == ["frontend", "critical"]
        assert detail_data["color"] == "blue"
        assert detail_data["icon"] == "sparkles"
