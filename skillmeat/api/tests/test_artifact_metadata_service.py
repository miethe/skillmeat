"""Tests for artifact metadata lookup service.

Tests the 3-step lookup mechanism:
1. Cache table (Artifact model)
2. Marketplace catalog (MarketplaceCatalogEntry model)
3. Minimal fallback
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, Mock

from skillmeat.api.services.artifact_metadata_service import (
    get_artifact_metadata,
    _lookup_in_cache,
    _lookup_in_marketplace,
)
from skillmeat.api.schemas.user_collections import ArtifactSummary
from skillmeat.cache.models import Artifact, MarketplaceCatalogEntry


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_session():
    """Create a mock SQLAlchemy session."""
    session = MagicMock()
    return session


@pytest.fixture
def sample_artifact():
    """Create a sample Artifact record from cache table."""
    artifact = Mock(spec=Artifact)
    artifact.id = "test-artifact-id"
    artifact.name = "test-skill"
    artifact.type = "skill"
    artifact.source = "github:user/repo/test-skill"
    artifact.deployed_version = "v1.2.0"
    artifact.upstream_version = "v1.3.0"
    return artifact


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
    return entry


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
    # Mock cache lookup returning artifact
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = sample_artifact
    mock_session.query.return_value = mock_query

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

    # Verify cache was queried first
    mock_session.query.assert_called_with(Artifact)


def test_get_artifact_metadata_from_cache_uses_upstream_version(mock_session):
    """Test cache lookup uses upstream_version when deployed_version is None."""
    # Create artifact with no deployed_version
    artifact = Mock(spec=Artifact)
    artifact.name = "test-skill"
    artifact.type = "skill"
    artifact.source = "github:user/repo/skill"
    artifact.deployed_version = None
    artifact.upstream_version = "v2.0.0"

    # Mock query
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = artifact
    mock_session.query.return_value = mock_query

    # Call function
    result = get_artifact_metadata(mock_session, "test-id")

    # Assertions
    assert result.version == "v2.0.0"


def test_get_artifact_metadata_from_marketplace(mock_session, sample_marketplace_entry):
    """Test getting metadata from marketplace catalog (step 2)."""

    # Mock cache lookup returning None (skip step 1)
    # Mock marketplace lookup returning entry (step 2)
    def mock_query_side_effect(model):
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter

        if model == Artifact:
            # Cache miss
            mock_filter.first.return_value = None
        elif model == MarketplaceCatalogEntry:
            # Marketplace hit
            mock_filter.first.return_value = sample_marketplace_entry

        return mock_query

    mock_session.query.side_effect = mock_query_side_effect

    # Call function
    result = get_artifact_metadata(mock_session, "marketplace-entry-id")

    # Assertions
    assert isinstance(result, ArtifactSummary)
    assert result.name == sample_marketplace_entry.name
    assert result.type == sample_marketplace_entry.artifact_type
    assert result.version == sample_marketplace_entry.detected_version
    assert result.source == sample_marketplace_entry.upstream_url

    # Verify both cache and marketplace were queried
    assert mock_session.query.call_count == 2


def test_get_artifact_metadata_fallback(mock_session):
    """Test fallback metadata when both cache and marketplace miss (step 3)."""
    # Mock both cache and marketplace returning None
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = None
    mock_session.query.return_value = mock_query

    # Call function
    result = get_artifact_metadata(mock_session, "unknown-artifact-id")

    # Assertions
    assert isinstance(result, ArtifactSummary)
    assert result.name == "unknown-artifact-id"
    assert result.type == "unknown"
    assert result.version is None
    assert result.source == "unknown-artifact-id"

    # Verify both cache and marketplace were queried
    assert mock_session.query.call_count == 2


def test_get_artifact_metadata_cache_priority(
    mock_session, sample_artifact, sample_marketplace_entry
):
    """Test that cache is prioritized over marketplace when both exist."""

    # Mock both cache and marketplace returning results
    def mock_query_side_effect(model):
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter

        if model == Artifact:
            # Cache hit
            mock_filter.first.return_value = sample_artifact
        elif model == MarketplaceCatalogEntry:
            # Marketplace also has entry (but shouldn't be reached)
            mock_filter.first.return_value = sample_marketplace_entry

        return mock_query

    mock_session.query.side_effect = mock_query_side_effect

    # Call function
    result = get_artifact_metadata(mock_session, "test-artifact-id")

    # Assertions - should use cache data, not marketplace
    assert result.name == sample_artifact.name
    assert result.type == sample_artifact.type
    assert result.version == sample_artifact.deployed_version
    assert result.source == sample_artifact.source

    # Verify only cache was queried (marketplace never reached)
    assert mock_session.query.call_count == 1
    mock_session.query.assert_called_with(Artifact)


def test_get_artifact_metadata_marketplace_lookup_by_import_id(
    mock_session, sample_marketplace_entry
):
    """Test marketplace lookup succeeds when matching import_id."""
    # Setup entry with import_id
    sample_marketplace_entry.import_id = "imported-skill-xyz"

    # Mock cache miss, marketplace hit by import_id
    def mock_query_side_effect(model):
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter

        if model == Artifact:
            mock_filter.first.return_value = None
        elif model == MarketplaceCatalogEntry:
            mock_filter.first.return_value = sample_marketplace_entry

        return mock_query

    mock_session.query.side_effect = mock_query_side_effect

    # Call function with import_id
    result = get_artifact_metadata(mock_session, "imported-skill-xyz")

    # Assertions
    assert result.name == sample_marketplace_entry.name
    assert result.type == sample_marketplace_entry.artifact_type


def test_get_artifact_metadata_marketplace_lookup_by_path_contains(
    mock_session, sample_marketplace_entry
):
    """Test marketplace lookup succeeds when path contains artifact_id."""

    # Mock cache miss, marketplace hit by path contains
    def mock_query_side_effect(model):
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter

        if model == Artifact:
            mock_filter.first.return_value = None
        elif model == MarketplaceCatalogEntry:
            # Entry's path contains "marketplace-skill"
            mock_filter.first.return_value = sample_marketplace_entry

        return mock_query

    mock_session.query.side_effect = mock_query_side_effect

    # Call function with substring from path
    result = get_artifact_metadata(mock_session, "marketplace-skill")

    # Assertions
    assert result.name == sample_marketplace_entry.name
    assert result.type == sample_marketplace_entry.artifact_type


def test_get_artifact_metadata_handles_none_source_in_cache(mock_session):
    """Test cache lookup handles None source gracefully."""
    # Create artifact with None source
    artifact = Mock(spec=Artifact)
    artifact.name = "test-skill"
    artifact.type = "skill"
    artifact.source = None  # No source
    artifact.deployed_version = "v1.0.0"
    artifact.upstream_version = None

    # Mock query
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = artifact
    mock_session.query.return_value = mock_query

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

    # Mock cache miss, marketplace hit
    def mock_query_side_effect(model):
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter

        if model == Artifact:
            mock_filter.first.return_value = None
        elif model == MarketplaceCatalogEntry:
            mock_filter.first.return_value = entry

        return mock_query

    mock_session.query.side_effect = mock_query_side_effect

    # Call function
    result = get_artifact_metadata(mock_session, "skill-id")

    # Assertions
    assert result.version is None  # Should handle None gracefully
    assert result.name == entry.name
