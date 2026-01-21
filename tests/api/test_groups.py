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
    Base,
    Collection,
    CollectionArtifact,
    Group,
    GroupArtifact,
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
def source_group_with_artifacts(test_db, source_collection) -> tuple[Group, list[str]]:
    """Create a source group with artifacts for testing."""
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

    # Create some artifact IDs and add them to the group
    artifact_ids = [f"artifact-{i}" for i in range(3)]

    for i, artifact_id in enumerate(artifact_ids):
        # Add to collection
        collection_artifact = CollectionArtifact(
            collection_id=source_collection.id,
            artifact_id=artifact_id,
        )
        test_db.add(collection_artifact)

        # Add to group
        group_artifact = GroupArtifact(
            group_id=group.id,
            artifact_id=artifact_id,
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
            for artifact_id in artifact_ids:
                collection_artifact = (
                    session.query(CollectionArtifact)
                    .filter_by(
                        collection_id=target_collection.id,
                        artifact_id=artifact_id,
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

        # Pre-add one artifact to target collection
        existing_artifact_id = artifact_ids[0]
        existing_association = CollectionArtifact(
            collection_id=target_collection.id,
            artifact_id=existing_artifact_id,
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
            artifact_ids_in_collection = [ca.artifact_id for ca in collection_artifacts]

            # Should have exactly len(artifact_ids) artifacts (no duplicates)
            assert len(artifact_ids_in_collection) == len(artifact_ids)
            for artifact_id in artifact_ids:
                assert artifact_id in artifact_ids_in_collection

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
                assert new_ga.artifact_id == source_ga.artifact_id
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
