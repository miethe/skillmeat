"""Tests for artifact metadata lookup service.

Tests the 3-step lookup mechanism:
1. Cache table (Artifact model)
2. Marketplace catalog (MarketplaceCatalogEntry model)
3. Minimal fallback

Also tests metadata extraction (description, author, tags) and
collection membership lookup.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, Mock, PropertyMock

from skillmeat.api.services.artifact_metadata_service import (
    get_artifact_metadata,
    _lookup_in_cache,
    _lookup_in_marketplace,
    _get_artifact_collections,
    _extract_artifact_tags,
    _extract_artifact_description,
)
from skillmeat.api.schemas.user_collections import ArtifactSummary
from skillmeat.cache.models import (
    Artifact,
    Collection,
    CollectionArtifact,
    MarketplaceCatalogEntry,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_session():
    """Create a mock SQLAlchemy session."""
    session = MagicMock()
    return session


def _create_mock_artifact(
    artifact_id="test-artifact-id",
    name="test-skill",
    artifact_type="skill",
    source="github:user/repo/test-skill",
    deployed_version="v1.2.0",
    upstream_version="v1.3.0",
    description=None,
    tags=None,
    artifact_metadata=None,
):
    """Create a sample Artifact record from cache table with proper mocking."""
    artifact = Mock(spec=Artifact)
    artifact.id = artifact_id
    artifact.name = name
    artifact.type = artifact_type
    artifact.source = source
    artifact.deployed_version = deployed_version
    artifact.upstream_version = upstream_version
    artifact.description = description

    # Mock tags relationship - empty list by default
    if tags is None:
        artifact.tags = []
    else:
        artifact.tags = tags

    # Mock artifact_metadata relationship
    artifact.artifact_metadata = artifact_metadata

    return artifact


@pytest.fixture
def sample_artifact():
    """Create a sample Artifact record from cache table."""
    return _create_mock_artifact()


@pytest.fixture
def sample_marketplace_entry():
    """Create a sample MarketplaceCatalogEntry record."""
    entry = Mock(spec=MarketplaceCatalogEntry)
    entry.id = "marketplace-entry-id"
    entry.name = "marketplace-skill"
    entry.artifact_type = "skill"
    entry.path = "skills/marketplace-skill"
    entry.upstream_url = (
        "https://github.com/user/repo/tree/main/skills/marketplace-skill"
    )
    entry.detected_version = "v2.0.0"
    entry.detected_sha = "abc123def456"
    entry.import_id = None
    entry.detected_metadata = None  # Add this field
    return entry


def _setup_mock_session_for_get_artifact_metadata(
    mock_session,
    cache_artifact=None,
    marketplace_entry=None,
    collection_associations=None,
):
    """
    Helper to set up mock session for get_artifact_metadata tests.

    This handles the multiple query calls made by the function:
    1. Collection lookup (CollectionArtifact, Collection)
    2. Cache lookup (Artifact)
    3. Marketplace lookup (MarketplaceCatalogEntry) - if cache miss
    4. Collection count query
    """
    if collection_associations is None:
        collection_associations = []

    def mock_query_side_effect(*models):
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_join = MagicMock()
        mock_filter_by = MagicMock()

        # Set up default chain
        mock_query.filter.return_value = mock_filter
        mock_query.join.return_value = mock_join
        mock_query.filter_by.return_value = mock_filter_by
        mock_join.filter.return_value = mock_filter
        mock_filter.first.return_value = None
        mock_filter.all.return_value = []
        mock_filter.count.return_value = 0
        mock_filter_by.count.return_value = 0

        # Handle tuple query (CollectionArtifact, Collection)
        if len(models) == 2 and models[0] == CollectionArtifact:
            mock_filter.all.return_value = collection_associations
            return mock_query

        # Handle single model queries
        model = models[0] if models else None

        if model == Artifact:
            mock_filter.first.return_value = cache_artifact
        elif model == MarketplaceCatalogEntry:
            mock_filter.first.return_value = marketplace_entry
        elif model == CollectionArtifact:
            mock_filter_by.count.return_value = len(collection_associations)

        return mock_query

    mock_session.query.side_effect = mock_query_side_effect


# =============================================================================
# Cache Lookup Tests (_lookup_in_cache)
# =============================================================================


def test_lookup_in_cache_found(mock_session, sample_artifact):
    """Test successful lookup in cache table."""
    # Mock query chain
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = sample_artifact
    mock_session.query.return_value = mock_query

    # Call function
    result = _lookup_in_cache(mock_session, "test-artifact-id")

    # Assertions
    assert result == sample_artifact
    mock_session.query.assert_called_once_with(Artifact)
    mock_query.filter.assert_called_once()
    mock_filter.first.assert_called_once()


def test_lookup_in_cache_not_found(mock_session):
    """Test cache lookup when artifact doesn't exist."""
    # Mock query chain returning None
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = None
    mock_session.query.return_value = mock_query

    # Call function
    result = _lookup_in_cache(mock_session, "nonexistent-id")

    # Assertions
    assert result is None
    mock_session.query.assert_called_once_with(Artifact)


def test_lookup_in_cache_by_type_and_name(mock_session, sample_artifact):
    """Test cache lookup using type:name format (e.g., 'agent:my-agent').

    This tests the fix for the bug where artifact_id in CollectionArtifact
    uses 'type:name' format but Artifact.id uses different formats like
    'ctx_abc123...'. The lookup should parse the type:name and query by
    Artifact.type and Artifact.name instead.
    """
    # Create artifact with separate type and name
    sample_artifact.type = "agent"
    sample_artifact.name = "a11y-sheriff"

    # Mock query chain - should call filter with type and name
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = sample_artifact
    mock_session.query.return_value = mock_query

    # Call function with type:name format
    result = _lookup_in_cache(mock_session, "agent:a11y-sheriff")

    # Assertions
    assert result == sample_artifact
    mock_session.query.assert_called_once_with(Artifact)
    # Verify filter was called (the filter call should use type and name)
    mock_query.filter.assert_called_once()
    mock_filter.first.assert_called_once()


def test_lookup_in_cache_fallback_for_unknown_format(mock_session, sample_artifact):
    """Test cache lookup falls back to ID lookup for non-type:name format."""
    # Mock query chain
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = sample_artifact
    mock_session.query.return_value = mock_query

    # Call function with a format that doesn't match type:name
    result = _lookup_in_cache(mock_session, "some-artifact-without-colon")

    # Assertions
    assert result == sample_artifact
    mock_session.query.assert_called_once_with(Artifact)
    mock_query.filter.assert_called_once()


# =============================================================================
# Marketplace Lookup Tests (_lookup_in_marketplace)
# =============================================================================


def test_lookup_in_marketplace_by_id(mock_session, sample_marketplace_entry):
    """Test marketplace lookup matching by entry ID."""
    # Mock query chain
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = sample_marketplace_entry
    mock_session.query.return_value = mock_query

    # Call function
    result = _lookup_in_marketplace(mock_session, "marketplace-entry-id")

    # Assertions
    assert result == sample_marketplace_entry
    mock_session.query.assert_called_once_with(MarketplaceCatalogEntry)
    mock_query.filter.assert_called_once()


def test_lookup_in_marketplace_by_import_id(mock_session, sample_marketplace_entry):
    """Test marketplace lookup matching by import_id."""
    # Setup entry with import_id
    sample_marketplace_entry.import_id = "imported-artifact-123"

    # Mock query chain
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = sample_marketplace_entry
    mock_session.query.return_value = mock_query

    # Call function with import_id
    result = _lookup_in_marketplace(mock_session, "imported-artifact-123")

    # Assertions
    assert result == sample_marketplace_entry
    mock_session.query.assert_called_once_with(MarketplaceCatalogEntry)


def test_lookup_in_marketplace_by_path_contains(mock_session, sample_marketplace_entry):
    """Test marketplace lookup matching by path contains."""
    # Mock query chain
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = sample_marketplace_entry
    mock_session.query.return_value = mock_query

    # Call function with substring of path
    result = _lookup_in_marketplace(mock_session, "marketplace-skill")

    # Assertions
    assert result == sample_marketplace_entry
    mock_session.query.assert_called_once_with(MarketplaceCatalogEntry)


def test_lookup_in_marketplace_not_found(mock_session):
    """Test marketplace lookup when no entry matches."""
    # Mock query chain returning None
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = None
    mock_session.query.return_value = mock_query

    # Call function
    result = _lookup_in_marketplace(mock_session, "nonexistent-artifact")

    # Assertions
    assert result is None
    mock_session.query.assert_called_once_with(MarketplaceCatalogEntry)


# =============================================================================
# get_artifact_metadata Tests (Full 3-Step Lookup)
# =============================================================================


def test_get_artifact_metadata_from_cache(mock_session, sample_artifact):
    """Test getting metadata from cache table (step 1)."""
    # Setup mock session with cache hit
    _setup_mock_session_for_get_artifact_metadata(
        mock_session,
        cache_artifact=sample_artifact,
    )

    # Call function
    result = get_artifact_metadata(mock_session, "test-artifact-id")

    # Assertions
    assert isinstance(result, ArtifactSummary)
    assert result.name == sample_artifact.name
    assert result.type == sample_artifact.type
    assert (
        result.version == sample_artifact.deployed_version
    )  # Prefers deployed_version
    assert result.source == sample_artifact.source


def test_get_artifact_metadata_from_cache_uses_upstream_version(mock_session):
    """Test cache lookup uses upstream_version when deployed_version is None."""
    # Create artifact with no deployed_version
    artifact = _create_mock_artifact(
        name="test-skill",
        artifact_type="skill",
        source="github:user/repo/skill",
        deployed_version=None,
        upstream_version="v2.0.0",
    )

    # Setup mock session with cache hit
    _setup_mock_session_for_get_artifact_metadata(
        mock_session,
        cache_artifact=artifact,
    )

    # Call function
    result = get_artifact_metadata(mock_session, "test-id")

    # Assertions
    assert result.version == "v2.0.0"


def test_get_artifact_metadata_from_marketplace(mock_session, sample_marketplace_entry):
    """Test getting metadata from marketplace catalog (step 2)."""
    # Setup mock session with cache miss, marketplace hit
    _setup_mock_session_for_get_artifact_metadata(
        mock_session,
        cache_artifact=None,
        marketplace_entry=sample_marketplace_entry,
    )

    # Call function
    result = get_artifact_metadata(mock_session, "marketplace-entry-id")

    # Assertions
    assert isinstance(result, ArtifactSummary)
    assert result.name == sample_marketplace_entry.name
    assert result.type == sample_marketplace_entry.artifact_type
    assert result.version == sample_marketplace_entry.detected_version
    assert result.source == sample_marketplace_entry.upstream_url


def test_get_artifact_metadata_fallback(mock_session):
    """Test fallback metadata when both cache and marketplace miss (step 3)."""
    # Setup mock session with both cache and marketplace miss
    _setup_mock_session_for_get_artifact_metadata(
        mock_session,
        cache_artifact=None,
        marketplace_entry=None,
    )

    # Call function
    result = get_artifact_metadata(mock_session, "unknown-artifact-id")

    # Assertions
    assert isinstance(result, ArtifactSummary)
    assert result.name == "unknown-artifact-id"
    assert result.type == "unknown"
    assert result.version is None
    assert result.source == "unknown-artifact-id"


def test_get_artifact_metadata_cache_priority(
    mock_session, sample_artifact, sample_marketplace_entry
):
    """Test that cache is prioritized over marketplace when both exist."""
    # Setup mock session with both cache and marketplace having data
    # (marketplace should never be reached)
    _setup_mock_session_for_get_artifact_metadata(
        mock_session,
        cache_artifact=sample_artifact,
        marketplace_entry=sample_marketplace_entry,
    )

    # Call function
    result = get_artifact_metadata(mock_session, "test-artifact-id")

    # Assertions - should use cache data, not marketplace
    assert result.name == sample_artifact.name
    assert result.type == sample_artifact.type
    assert result.version == sample_artifact.deployed_version
    assert result.source == sample_artifact.source


def test_get_artifact_metadata_marketplace_lookup_by_import_id(
    mock_session, sample_marketplace_entry
):
    """Test marketplace lookup succeeds when matching import_id."""
    # Setup entry with import_id
    sample_marketplace_entry.import_id = "imported-skill-xyz"

    # Setup mock session with cache miss, marketplace hit
    _setup_mock_session_for_get_artifact_metadata(
        mock_session,
        cache_artifact=None,
        marketplace_entry=sample_marketplace_entry,
    )

    # Call function with import_id
    result = get_artifact_metadata(mock_session, "imported-skill-xyz")

    # Assertions
    assert result.name == sample_marketplace_entry.name
    assert result.type == sample_marketplace_entry.artifact_type


def test_get_artifact_metadata_marketplace_lookup_by_path_contains(
    mock_session, sample_marketplace_entry
):
    """Test marketplace lookup succeeds when path contains artifact_id."""
    # Setup mock session with cache miss, marketplace hit
    _setup_mock_session_for_get_artifact_metadata(
        mock_session,
        cache_artifact=None,
        marketplace_entry=sample_marketplace_entry,
    )

    # Call function with substring from path
    result = get_artifact_metadata(mock_session, "marketplace-skill")

    # Assertions
    assert result.name == sample_marketplace_entry.name
    assert result.type == sample_marketplace_entry.artifact_type


def test_get_artifact_metadata_handles_none_source_in_cache(mock_session):
    """Test cache lookup handles None source gracefully."""
    # Create artifact with None source
    artifact = _create_mock_artifact(
        name="test-skill",
        artifact_type="skill",
        source=None,  # No source
        deployed_version="v1.0.0",
        upstream_version=None,
    )

    # Setup mock session with cache hit
    _setup_mock_session_for_get_artifact_metadata(
        mock_session,
        cache_artifact=artifact,
    )

    # Call function
    result = get_artifact_metadata(mock_session, "test-id")

    # Assertions - should fallback to artifact_id for source
    assert result.source == "test-id"


def test_get_artifact_metadata_handles_none_version_in_marketplace(mock_session):
    """Test marketplace lookup handles None detected_version gracefully."""
    # Create entry with no version
    entry = Mock(spec=MarketplaceCatalogEntry)
    entry.name = "skill-no-version"
    entry.artifact_type = "skill"
    entry.upstream_url = "https://github.com/user/repo"
    entry.detected_version = None
    entry.path = "skills/skill-no-version"
    entry.detected_metadata = None

    # Setup mock session with cache miss, marketplace hit
    _setup_mock_session_for_get_artifact_metadata(
        mock_session,
        cache_artifact=None,
        marketplace_entry=entry,
    )

    # Call function
    result = get_artifact_metadata(mock_session, "skill-id")

    # Assertions
    assert result.version is None  # Should handle None gracefully
    assert result.name == entry.name


# =============================================================================
# New Tests for Extended Metadata (description, author, tags, collections)
# =============================================================================


def test_get_artifact_metadata_includes_description_from_artifact(mock_session):
    """Test that description is extracted from artifact.description field."""
    artifact = _create_mock_artifact(description="A helpful test skill")

    _setup_mock_session_for_get_artifact_metadata(
        mock_session,
        cache_artifact=artifact,
    )

    result = get_artifact_metadata(mock_session, "test-artifact-id")

    assert result.description == "A helpful test skill"


def test_get_artifact_metadata_includes_description_from_metadata(mock_session):
    """Test that description is extracted from artifact_metadata relationship."""
    # Create metadata mock
    metadata = Mock()
    metadata.description = "Description from metadata"
    metadata.metadata_json = None

    artifact = _create_mock_artifact(
        description=None,  # No direct description
        artifact_metadata=metadata,
    )

    _setup_mock_session_for_get_artifact_metadata(
        mock_session,
        cache_artifact=artifact,
    )

    result = get_artifact_metadata(mock_session, "test-artifact-id")

    assert result.description == "Description from metadata"


def test_get_artifact_metadata_includes_tags(mock_session):
    """Test that tags are extracted from artifact.tags relationship."""
    # Create mock tags
    tag1 = Mock()
    tag1.name = "productivity"
    tag2 = Mock()
    tag2.name = "automation"

    artifact = _create_mock_artifact(tags=[tag1, tag2])

    _setup_mock_session_for_get_artifact_metadata(
        mock_session,
        cache_artifact=artifact,
    )

    result = get_artifact_metadata(mock_session, "test-artifact-id")

    assert result.tags == ["productivity", "automation"]


def test_get_artifact_metadata_includes_author_from_metadata_json(mock_session):
    """Test that author is extracted from metadata_json field."""
    import json

    metadata = Mock()
    metadata.description = None
    metadata.metadata_json = json.dumps({"author": "Test Author"})

    artifact = _create_mock_artifact(artifact_metadata=metadata)

    _setup_mock_session_for_get_artifact_metadata(
        mock_session,
        cache_artifact=artifact,
    )

    result = get_artifact_metadata(mock_session, "test-artifact-id")

    assert result.author == "Test Author"


def test_get_artifact_metadata_includes_collections(mock_session):
    """Test that collection memberships are included."""
    artifact = _create_mock_artifact()

    # Create mock collection association
    mock_assoc = Mock()
    mock_collection = Mock(spec=Collection)
    mock_collection.id = "coll-123"
    mock_collection.name = "My Collection"

    _setup_mock_session_for_get_artifact_metadata(
        mock_session,
        cache_artifact=artifact,
        collection_associations=[(mock_assoc, mock_collection)],
    )

    result = get_artifact_metadata(mock_session, "test-artifact-id")

    assert result.collections is not None
    assert len(result.collections) == 1
    assert result.collections[0].id == "coll-123"
    assert result.collections[0].name == "My Collection"


def test_get_artifact_metadata_empty_collections(mock_session):
    """Test that empty collections returns None instead of empty list."""
    artifact = _create_mock_artifact()

    _setup_mock_session_for_get_artifact_metadata(
        mock_session,
        cache_artifact=artifact,
        collection_associations=[],
    )

    result = get_artifact_metadata(mock_session, "test-artifact-id")

    assert result.collections is None


def test_get_artifact_metadata_marketplace_with_metadata(mock_session):
    """Test marketplace entries extract metadata from detected_metadata field."""
    import json

    entry = Mock(spec=MarketplaceCatalogEntry)
    entry.name = "marketplace-skill"
    entry.artifact_type = "skill"
    entry.upstream_url = "https://github.com/user/repo"
    entry.detected_version = "v1.0.0"
    entry.detected_metadata = json.dumps({
        "description": "Marketplace description",
        "author": "Marketplace Author",
        "tags": ["tag1", "tag2"],
    })

    _setup_mock_session_for_get_artifact_metadata(
        mock_session,
        cache_artifact=None,
        marketplace_entry=entry,
    )

    result = get_artifact_metadata(mock_session, "marketplace-id")

    assert result.description == "Marketplace description"
    assert result.author == "Marketplace Author"
    assert result.tags == ["tag1", "tag2"]
