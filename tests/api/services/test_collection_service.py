"""Unit tests for CollectionService.

Tests the centralized collection membership query service that eliminates
N+1 query patterns in the API layer.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, create_autospec
from sqlalchemy.orm import Session, Query

from skillmeat.api.services.collection_service import CollectionService
from skillmeat.api.schemas.artifacts import ArtifactCollectionInfo
from skillmeat.cache.models import Collection, CollectionArtifact


class TestCollectionService:
    """Test suite for CollectionService batch and single-artifact methods."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create a mock SQLAlchemy database session.

        Returns:
            MagicMock: Mock database session with query interface
        """
        return create_autospec(Session, spec_set=True)

    @pytest.fixture
    def service(self, mock_session: MagicMock) -> CollectionService:
        """Create CollectionService instance with mock session.

        Args:
            mock_session: Mock database session

        Returns:
            CollectionService: Service instance for testing
        """
        return CollectionService(mock_session)

    def _create_mock_collection(
        self, collection_id: str, name: str, count: int = 1
    ) -> Collection:
        """Helper to create a mock Collection object.

        Args:
            collection_id: Collection UUID
            name: Collection name
            count: Number of artifacts in collection

        Returns:
            Mock Collection object with required attributes
        """
        collection = MagicMock(spec=Collection)
        collection.id = collection_id
        collection.name = name
        collection.created_at = datetime.utcnow()
        collection.updated_at = datetime.utcnow()
        return collection

    def _create_mock_association(
        self, collection_id: str, artifact_id: str
    ) -> CollectionArtifact:
        """Helper to create a mock CollectionArtifact association.

        Args:
            collection_id: Collection UUID
            artifact_id: Artifact ID (e.g., 'skill:canvas')

        Returns:
            Mock CollectionArtifact object with required attributes
        """
        assoc = MagicMock(spec=CollectionArtifact)
        assoc.collection_id = collection_id
        assoc.artifact_id = artifact_id
        assoc.added_at = datetime.utcnow()
        return assoc

    # =========================================================================
    # Edge Cases
    # =========================================================================

    def test_empty_artifact_ids(self, service: CollectionService):
        """Empty list input returns empty dict without querying database."""
        result = service.get_collection_membership_batch([])

        assert result == {}
        # Should not make any database queries
        service.db.query.assert_not_called()

    def test_single_artifact_no_collections(
        self, service: CollectionService, mock_session: MagicMock
    ):
        """Artifact with no collection memberships returns empty list."""
        # Mock query chain: query() -> filter() -> all() -> []
        mock_query = MagicMock(spec=Query)
        mock_query.filter.return_value.all.return_value = []

        mock_session.query.return_value = mock_query

        result = service.get_collection_membership_batch(["skill:nonexistent"])

        assert result == {"skill:nonexistent": []}
        mock_session.query.assert_called_once()

    # =========================================================================
    # Single Artifact Scenarios
    # =========================================================================

    def test_single_artifact_one_collection(
        self, service: CollectionService, mock_session: MagicMock
    ):
        """Artifact in one collection returns that collection."""
        artifact_id = "skill:canvas"
        collection_id = "coll-abc123"

        # Mock association query
        association = self._create_mock_association(collection_id, artifact_id)
        mock_assoc_query = MagicMock(spec=Query)
        mock_assoc_query.filter.return_value.all.return_value = [association]

        # Mock collection query with count subquery
        collection = self._create_mock_collection(collection_id, "Design Tools", 5)
        mock_coll_query = MagicMock(spec=Query)
        mock_coll_query.outerjoin.return_value.filter.return_value.all.return_value = [
            (collection, 5)
        ]

        # Setup query side effect: first call -> associations, later calls -> collections
        mock_session.query.side_effect = [mock_assoc_query, MagicMock(), mock_coll_query]

        result = service.get_collection_membership_batch([artifact_id])

        assert artifact_id in result
        assert len(result[artifact_id]) == 1
        assert isinstance(result[artifact_id][0], ArtifactCollectionInfo)
        assert result[artifact_id][0].id == collection_id
        assert result[artifact_id][0].name == "Design Tools"
        assert result[artifact_id][0].artifact_count == 5

    def test_single_artifact_multiple_collections(
        self, service: CollectionService, mock_session: MagicMock
    ):
        """Artifact in multiple collections returns all collections."""
        artifact_id = "skill:canvas"
        coll_id_1 = "coll-abc123"
        coll_id_2 = "coll-def456"

        # Mock associations
        associations = [
            self._create_mock_association(coll_id_1, artifact_id),
            self._create_mock_association(coll_id_2, artifact_id),
        ]
        mock_assoc_query = MagicMock(spec=Query)
        mock_assoc_query.filter.return_value.all.return_value = associations

        # Mock collections
        coll_1 = self._create_mock_collection(coll_id_1, "Design Tools", 5)
        coll_2 = self._create_mock_collection(coll_id_2, "UI Components", 10)
        mock_coll_query = MagicMock(spec=Query)
        mock_coll_query.outerjoin.return_value.filter.return_value.all.return_value = [
            (coll_1, 5),
            (coll_2, 10),
        ]

        mock_session.query.side_effect = [mock_assoc_query, MagicMock(), mock_coll_query]

        result = service.get_collection_membership_batch([artifact_id])

        assert artifact_id in result
        assert len(result[artifact_id]) == 2

        # Verify both collections are present (order not guaranteed)
        collection_ids = {c.id for c in result[artifact_id]}
        assert collection_ids == {coll_id_1, coll_id_2}

        collection_names = {c.name for c in result[artifact_id]}
        assert collection_names == {"Design Tools", "UI Components"}

    # =========================================================================
    # Batch Scenarios
    # =========================================================================

    def test_batch_multiple_artifacts(
        self, service: CollectionService, mock_session: MagicMock
    ):
        """Multiple artifacts with mixed memberships."""
        artifact_1 = "skill:canvas"
        artifact_2 = "skill:pdf"
        artifact_3 = "skill:orphan"
        coll_id_1 = "coll-abc123"
        coll_id_2 = "coll-def456"

        # Mock associations:
        # - artifact_1 in coll_1 and coll_2
        # - artifact_2 in coll_2 only
        # - artifact_3 in no collections
        associations = [
            self._create_mock_association(coll_id_1, artifact_1),
            self._create_mock_association(coll_id_2, artifact_1),
            self._create_mock_association(coll_id_2, artifact_2),
        ]
        mock_assoc_query = MagicMock(spec=Query)
        mock_assoc_query.filter.return_value.all.return_value = associations

        # Mock collections
        coll_1 = self._create_mock_collection(coll_id_1, "Design Tools", 5)
        coll_2 = self._create_mock_collection(coll_id_2, "Document Tools", 8)
        mock_coll_query = MagicMock(spec=Query)
        mock_coll_query.outerjoin.return_value.filter.return_value.all.return_value = [
            (coll_1, 5),
            (coll_2, 8),
        ]

        mock_session.query.side_effect = [mock_assoc_query, MagicMock(), mock_coll_query]

        result = service.get_collection_membership_batch(
            [artifact_1, artifact_2, artifact_3]
        )

        # All input artifacts should be in result
        assert set(result.keys()) == {artifact_1, artifact_2, artifact_3}

        # artifact_1 in 2 collections
        assert len(result[artifact_1]) == 2
        assert {c.id for c in result[artifact_1]} == {coll_id_1, coll_id_2}

        # artifact_2 in 1 collection
        assert len(result[artifact_2]) == 1
        assert result[artifact_2][0].id == coll_id_2

        # artifact_3 in no collections
        assert result[artifact_3] == []

    # =========================================================================
    # Artifact Count Accuracy
    # =========================================================================

    def test_artifact_count_accuracy(
        self, service: CollectionService, mock_session: MagicMock
    ):
        """Verify artifact_count field is accurate from count subquery."""
        artifact_id = "skill:canvas"
        collection_id = "coll-abc123"

        # Mock association
        association = self._create_mock_association(collection_id, artifact_id)
        mock_assoc_query = MagicMock(spec=Query)
        mock_assoc_query.filter.return_value.all.return_value = [association]

        # Mock collection with count=15
        collection = self._create_mock_collection(collection_id, "My Collection", 15)
        mock_coll_query = MagicMock(spec=Query)
        mock_coll_query.outerjoin.return_value.filter.return_value.all.return_value = [
            (collection, 15)
        ]

        mock_session.query.side_effect = [mock_assoc_query, MagicMock(), mock_coll_query]

        result = service.get_collection_membership_batch([artifact_id])

        assert result[artifact_id][0].artifact_count == 15

    def test_artifact_count_zero_when_none(
        self, service: CollectionService, mock_session: MagicMock
    ):
        """Verify artifact_count is 0 when count is None from query."""
        artifact_id = "skill:canvas"
        collection_id = "coll-abc123"

        # Mock association
        association = self._create_mock_association(collection_id, artifact_id)
        mock_assoc_query = MagicMock(spec=Query)
        mock_assoc_query.filter.return_value.all.return_value = [association]

        # Mock collection with count=None (outer join with no matches)
        collection = self._create_mock_collection(collection_id, "Empty Collection")
        mock_coll_query = MagicMock(spec=Query)
        mock_coll_query.outerjoin.return_value.filter.return_value.all.return_value = [
            (collection, None)
        ]

        mock_session.query.side_effect = [mock_assoc_query, MagicMock(), mock_coll_query]

        result = service.get_collection_membership_batch([artifact_id])

        assert result[artifact_id][0].artifact_count == 0

    # =========================================================================
    # Input/Output Consistency
    # =========================================================================

    def test_all_input_ids_in_result(
        self, service: CollectionService, mock_session: MagicMock
    ):
        """All input artifact_ids appear in result (even if empty)."""
        input_ids = ["skill:one", "skill:two", "skill:three", "skill:four"]

        # Mock association query returns empty (no memberships)
        mock_assoc_query = MagicMock(spec=Query)
        mock_assoc_query.filter.return_value.all.return_value = []

        mock_session.query.return_value = mock_assoc_query

        result = service.get_collection_membership_batch(input_ids)

        # All input IDs should be keys in result
        assert set(result.keys()) == set(input_ids)

        # All should have empty lists
        for artifact_id in input_ids:
            assert result[artifact_id] == []

    def test_partial_memberships_all_ids_present(
        self, service: CollectionService, mock_session: MagicMock
    ):
        """Partial memberships still include all input IDs in result."""
        artifact_1 = "skill:has_collections"
        artifact_2 = "skill:no_collections"
        coll_id = "coll-abc123"

        # Only artifact_1 has membership
        associations = [self._create_mock_association(coll_id, artifact_1)]
        mock_assoc_query = MagicMock(spec=Query)
        mock_assoc_query.filter.return_value.all.return_value = associations

        # Mock collection
        collection = self._create_mock_collection(coll_id, "Test Collection", 3)
        mock_coll_query = MagicMock(spec=Query)
        mock_coll_query.outerjoin.return_value.filter.return_value.all.return_value = [
            (collection, 3)
        ]

        mock_session.query.side_effect = [mock_assoc_query, MagicMock(), mock_coll_query]

        result = service.get_collection_membership_batch([artifact_1, artifact_2])

        # Both artifacts should be in result
        assert set(result.keys()) == {artifact_1, artifact_2}
        assert len(result[artifact_1]) == 1
        assert result[artifact_2] == []

    # =========================================================================
    # Single-Artifact Convenience Method
    # =========================================================================

    def test_get_collection_membership_single_delegates_to_batch(
        self, service: CollectionService, mock_session: MagicMock
    ):
        """Single-artifact method delegates to batch method."""
        artifact_id = "skill:canvas"
        collection_id = "coll-abc123"

        # Mock association
        association = self._create_mock_association(collection_id, artifact_id)
        mock_assoc_query = MagicMock(spec=Query)
        mock_assoc_query.filter.return_value.all.return_value = [association]

        # Mock collection
        collection = self._create_mock_collection(collection_id, "Test Collection", 5)
        mock_coll_query = MagicMock(spec=Query)
        mock_coll_query.outerjoin.return_value.filter.return_value.all.return_value = [
            (collection, 5)
        ]

        mock_session.query.side_effect = [mock_assoc_query, MagicMock(), mock_coll_query]

        # Use single-artifact method
        result = service.get_collection_membership_single(artifact_id)

        # Should return list (not dict)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].id == collection_id
        assert result[0].name == "Test Collection"

    def test_get_collection_membership_single_no_collections(
        self, service: CollectionService, mock_session: MagicMock
    ):
        """Single-artifact method returns empty list when no memberships."""
        # Mock empty associations
        mock_assoc_query = MagicMock(spec=Query)
        mock_assoc_query.filter.return_value.all.return_value = []

        mock_session.query.return_value = mock_assoc_query

        result = service.get_collection_membership_single("skill:orphan")

        assert result == []

    # =========================================================================
    # Schema Contract Validation
    # =========================================================================

    def test_returns_artifact_collection_info_schema(
        self, service: CollectionService, mock_session: MagicMock
    ):
        """Verify returned objects conform to ArtifactCollectionInfo schema."""
        artifact_id = "skill:canvas"
        collection_id = "coll-abc123"

        # Mock association
        association = self._create_mock_association(collection_id, artifact_id)
        mock_assoc_query = MagicMock(spec=Query)
        mock_assoc_query.filter.return_value.all.return_value = [association]

        # Mock collection
        collection = self._create_mock_collection(collection_id, "Test Collection", 7)
        mock_coll_query = MagicMock(spec=Query)
        mock_coll_query.outerjoin.return_value.filter.return_value.all.return_value = [
            (collection, 7)
        ]

        mock_session.query.side_effect = [mock_assoc_query, MagicMock(), mock_coll_query]

        result = service.get_collection_membership_batch([artifact_id])

        # Verify schema fields
        info = result[artifact_id][0]
        assert isinstance(info, ArtifactCollectionInfo)
        assert hasattr(info, "id")
        assert hasattr(info, "name")
        assert hasattr(info, "artifact_count")
        assert info.id == collection_id
        assert info.name == "Test Collection"
        assert info.artifact_count == 7

    # =========================================================================
    # Performance/Query Optimization
    # =========================================================================

    def test_batch_uses_single_query_for_associations(
        self, service: CollectionService, mock_session: MagicMock
    ):
        """Batch method uses single query for all artifact associations."""
        # Mock empty associations
        mock_assoc_query = MagicMock(spec=Query)
        mock_assoc_query.filter.return_value.all.return_value = []

        mock_session.query.return_value = mock_assoc_query

        # Query for 100 artifacts
        artifact_ids = [f"skill:artifact_{i}" for i in range(100)]
        service.get_collection_membership_batch(artifact_ids)

        # Should only call query.filter once with .in_() clause
        mock_assoc_query.filter.assert_called_once()
