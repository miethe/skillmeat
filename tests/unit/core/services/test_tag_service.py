"""Unit tests for TagService.

Tests for tag CRUD operations, search, and artifact-tag associations.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from skillmeat.cache.repositories import RepositoryError

# Import schemas at module level - this should work because the circular import
# is only through skillmeat.api.routers which we don't import in tests
from skillmeat.api.schemas.tags import (
    TagCreateRequest,
    TagUpdateRequest,
    TagResponse,
    TagListResponse,
)
from skillmeat.api.schemas.common import PageInfo


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_tag():
    """Create a mock tag ORM instance."""
    tag = Mock()
    tag.id = "test-tag-id"
    tag.name = "Python"
    tag.slug = "python"
    tag.color = "#3776AB"
    tag.created_at = datetime(2025, 1, 1, 0, 0, 0)
    tag.updated_at = datetime(2025, 1, 1, 0, 0, 0)
    return tag


@pytest.fixture
def mock_repository(mock_tag):
    """Create a mock TagRepository."""
    with patch("skillmeat.core.services.tag_service.TagRepository") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.create.return_value = mock_tag
        mock_repo.get_by_id.return_value = mock_tag
        mock_repo.get_by_slug.return_value = mock_tag
        mock_repo.update.return_value = mock_tag
        mock_repo.delete.return_value = True
        mock_repo.list_all.return_value = ([mock_tag], None, False)
        mock_repo.search_by_name.return_value = [mock_tag]
        mock_repo.get_tag_artifact_count.return_value = 3
        mock_repo.get_all_tag_counts.return_value = [(mock_tag, 3)]
        mock_repo.add_tag_to_artifact.return_value = None
        mock_repo.remove_tag_from_artifact.return_value = True
        mock_repo.get_artifact_tags.return_value = [mock_tag]
        yield mock_repo


@pytest.fixture
def tag_service(mock_repository):
    """Create TagService instance with mocked repository."""
    # Import here to avoid circular import issues
    from skillmeat.core.services.tag_service import TagService

    return TagService()


# =============================================================================
# Test: Create Tag
# =============================================================================


def test_create_tag_success(tag_service, mock_repository):
    """Test creating a tag successfully."""
    request = TagCreateRequest(
        name="Python",
        slug="python",
        color="#3776AB",
    )

    result = tag_service.create_tag(request)

    # Verify repository was called
    mock_repository.create.assert_called_once_with(
        name="Python",
        slug="python",
        color="#3776AB",
    )

    # Verify response
    assert isinstance(result, TagResponse)
    assert result.name == "Python"
    assert result.slug == "python"
    assert result.color == "#3776AB"


def test_create_tag_duplicate_name(tag_service, mock_repository):
    """Test creating tag with duplicate name raises ValueError."""
    mock_repository.create.side_effect = RepositoryError(
        "Tag with name 'Python' already exists"
    )

    request = TagCreateRequest(name="Python", slug="python-2")

    with pytest.raises(ValueError) as excinfo:
        tag_service.create_tag(request)

    assert "already exists" in str(excinfo.value)


def test_create_tag_duplicate_slug(tag_service, mock_repository):
    """Test creating tag with duplicate slug raises ValueError."""
    mock_repository.create.side_effect = RepositoryError(
        "Tag with slug 'python' already exists"
    )

    request = TagCreateRequest(name="Python 2", slug="python")

    with pytest.raises(ValueError) as excinfo:
        tag_service.create_tag(request)

    assert "already exists" in str(excinfo.value)


def test_create_tag_repository_error(tag_service, mock_repository):
    """Test creating tag with repository error raises LookupError."""
    mock_repository.create.side_effect = RepositoryError("Database connection failed")

    request = TagCreateRequest(name="Python", slug="python")

    with pytest.raises(LookupError) as excinfo:
        tag_service.create_tag(request)

    assert "Failed to create tag" in str(excinfo.value)


# =============================================================================
# Test: Get Tag
# =============================================================================


def test_get_tag_by_id_success(tag_service, mock_repository, mock_tag):
    """Test getting tag by ID successfully."""
    result = tag_service.get_tag("test-tag-id")

    # Verify repository was called
    mock_repository.get_by_id.assert_called_once_with("test-tag-id")
    mock_repository.get_tag_artifact_count.assert_called_once_with("test-tag-id")

    # Verify response
    assert isinstance(result, TagResponse)
    assert result.id == "test-tag-id"
    assert result.name == "Python"
    assert result.artifact_count == 3


def test_get_tag_by_id_not_found(tag_service, mock_repository):
    """Test getting non-existent tag returns None."""
    mock_repository.get_by_id.return_value = None

    result = tag_service.get_tag("nonexistent")

    assert result is None


def test_get_tag_by_slug_success(tag_service, mock_repository, mock_tag):
    """Test getting tag by slug successfully."""
    result = tag_service.get_tag_by_slug("python")

    # Verify repository was called
    mock_repository.get_by_slug.assert_called_once_with("python")
    mock_repository.get_tag_artifact_count.assert_called_once_with("test-tag-id")

    # Verify response
    assert isinstance(result, TagResponse)
    assert result.slug == "python"
    assert result.artifact_count == 3


def test_get_tag_by_slug_not_found(tag_service, mock_repository):
    """Test getting tag by non-existent slug returns None."""
    mock_repository.get_by_slug.return_value = None

    result = tag_service.get_tag_by_slug("nonexistent")

    assert result is None


# =============================================================================
# Test: Update Tag
# =============================================================================


def test_update_tag_success(tag_service, mock_repository, mock_tag):
    """Test updating tag successfully."""
    request = TagUpdateRequest(color="#FF0000")

    result = tag_service.update_tag("test-tag-id", request)

    # Verify repository was called
    mock_repository.update.assert_called_once_with(
        tag_id="test-tag-id",
        name=None,
        slug=None,
        color="#FF0000",
    )

    # Verify response
    assert isinstance(result, TagResponse)
    assert result.id == "test-tag-id"


def test_update_tag_not_found(tag_service, mock_repository):
    """Test updating non-existent tag returns None."""
    mock_repository.update.return_value = None

    request = TagUpdateRequest(color="#FF0000")
    result = tag_service.update_tag("nonexistent", request)

    assert result is None


def test_update_tag_duplicate_name(tag_service, mock_repository):
    """Test updating tag with duplicate name raises ValueError."""
    mock_repository.update.side_effect = RepositoryError(
        "Tag with name 'JavaScript' already exists"
    )

    request = TagUpdateRequest(name="JavaScript")

    with pytest.raises(ValueError) as excinfo:
        tag_service.update_tag("test-tag-id", request)

    assert "already exists" in str(excinfo.value)


# =============================================================================
# Test: Delete Tag
# =============================================================================


def test_delete_tag_success(tag_service, mock_repository):
    """Test deleting tag successfully."""
    result = tag_service.delete_tag("test-tag-id")

    # Verify repository was called
    mock_repository.delete.assert_called_once_with("test-tag-id")

    # Verify result
    assert result is True


def test_delete_tag_not_found(tag_service, mock_repository):
    """Test deleting non-existent tag returns False."""
    mock_repository.delete.return_value = False

    result = tag_service.delete_tag("nonexistent")

    assert result is False


def test_delete_tag_repository_error(tag_service, mock_repository):
    """Test deleting tag with repository error raises LookupError."""
    mock_repository.delete.side_effect = RepositoryError("Database error")

    with pytest.raises(LookupError) as excinfo:
        tag_service.delete_tag("test-tag-id")

    assert "Failed to delete tag" in str(excinfo.value)


# =============================================================================
# Test: List Tags
# =============================================================================


def test_list_tags_success(tag_service, mock_repository, mock_tag):
    """Test listing tags successfully."""
    result = tag_service.list_tags(limit=50)

    # Verify repository was called
    mock_repository.list_all.assert_called_once_with(limit=50, after_cursor=None)
    mock_repository.get_all_tag_counts.assert_called_once()

    # Verify response
    assert isinstance(result, TagListResponse)
    assert len(result.items) == 1
    assert result.items[0].name == "Python"
    assert result.items[0].artifact_count == 3
    assert isinstance(result.page_info, PageInfo)
    assert result.page_info.has_next_page is False


def test_list_tags_with_pagination(tag_service, mock_repository):
    """Test listing tags with pagination cursor."""
    tag_service.list_tags(limit=10, after_cursor="cursor-123")

    # Verify cursor was passed to repository
    mock_repository.list_all.assert_called_once_with(
        limit=10, after_cursor="cursor-123"
    )


def test_list_tags_has_next_page(tag_service, mock_repository, mock_tag):
    """Test listing tags with has_next_page flag."""
    # Mock repository to indicate more pages
    mock_repository.list_all.return_value = ([mock_tag], "next-cursor", True)

    result = tag_service.list_tags(limit=10)

    # Verify pagination info
    assert result.page_info.has_next_page is True
    assert result.page_info.end_cursor == "next-cursor"


def test_list_tags_empty(tag_service, mock_repository):
    """Test listing tags when no tags exist."""
    mock_repository.list_all.return_value = ([], None, False)
    mock_repository.get_all_tag_counts.return_value = []

    result = tag_service.list_tags()

    # Verify empty result
    assert len(result.items) == 0
    assert result.page_info.has_next_page is False


# =============================================================================
# Test: Search Tags
# =============================================================================


def test_search_tags_success(tag_service, mock_repository, mock_tag):
    """Test searching tags successfully."""
    result = tag_service.search_tags("py", limit=10)

    # Verify repository was called
    mock_repository.search_by_name.assert_called_once_with(pattern="py", limit=10)

    # Verify response
    assert len(result) == 1
    assert result[0].name == "Python"
    assert result[0].artifact_count == 3


def test_search_tags_empty_query(tag_service, mock_repository):
    """Test searching with empty query returns empty list."""
    result = tag_service.search_tags("", limit=10)

    # Verify repository was not called
    mock_repository.search_by_name.assert_not_called()

    # Verify empty result
    assert result == []


def test_search_tags_whitespace_query(tag_service, mock_repository):
    """Test searching with whitespace-only query returns empty list."""
    result = tag_service.search_tags("   ", limit=10)

    # Verify repository was not called
    mock_repository.search_by_name.assert_not_called()

    # Verify empty result
    assert result == []


def test_search_tags_no_results(tag_service, mock_repository):
    """Test searching tags with no results."""
    mock_repository.search_by_name.return_value = []
    mock_repository.get_all_tag_counts.return_value = []

    result = tag_service.search_tags("nonexistent", limit=10)

    # Verify empty result
    assert len(result) == 0


# =============================================================================
# Test: Artifact Associations
# =============================================================================


def test_add_tag_to_artifact_success(tag_service, mock_repository):
    """Test adding tag to artifact successfully."""
    result = tag_service.add_tag_to_artifact("artifact-123", "tag-456")

    # Verify repository was called with new artifact_uuid kwarg
    mock_repository.add_tag_to_artifact.assert_called_once_with(
        artifact_uuid="artifact-123", tag_id="tag-456"
    )

    # Verify result
    assert result is True


def test_add_tag_to_artifact_already_exists(tag_service, mock_repository):
    """Test adding duplicate tag association raises ValueError."""
    mock_repository.add_tag_to_artifact.side_effect = RepositoryError(
        "Artifact already has tag"
    )

    with pytest.raises(ValueError) as excinfo:
        tag_service.add_tag_to_artifact("artifact-123", "tag-456")

    assert "already has tag" in str(excinfo.value)


def test_add_tag_to_artifact_not_found(tag_service, mock_repository):
    """Test adding tag to non-existent artifact raises ValueError."""
    mock_repository.add_tag_to_artifact.side_effect = RepositoryError(
        "Artifact not found"
    )

    with pytest.raises(ValueError) as excinfo:
        tag_service.add_tag_to_artifact("nonexistent", "tag-456")

    assert "not found" in str(excinfo.value)


def test_remove_tag_from_artifact_success(tag_service, mock_repository):
    """Test removing tag from artifact successfully."""
    result = tag_service.remove_tag_from_artifact("artifact-123", "tag-456")

    # Verify repository was called with new artifact_uuid kwarg
    mock_repository.remove_tag_from_artifact.assert_called_once_with(
        artifact_uuid="artifact-123", tag_id="tag-456"
    )

    # Verify result
    assert result is True


def test_remove_tag_from_artifact_not_found(tag_service, mock_repository):
    """Test removing non-existent association returns False."""
    mock_repository.remove_tag_from_artifact.return_value = False

    result = tag_service.remove_tag_from_artifact("artifact-123", "tag-456")

    assert result is False


def test_get_artifact_tags_success(tag_service, mock_repository, mock_tag):
    """Test getting artifact tags successfully."""
    result = tag_service.get_artifact_tags("artifact-123")

    # Verify repository was called with new artifact_uuid kwarg
    mock_repository.get_artifact_tags.assert_called_once_with(
        artifact_uuid="artifact-123"
    )

    # Verify response
    assert len(result) == 1
    assert result[0].name == "Python"


def test_get_artifact_tags_no_tags(tag_service, mock_repository):
    """Test getting artifact tags when artifact has no tags."""
    mock_repository.get_artifact_tags.return_value = []

    result = tag_service.get_artifact_tags("artifact-123")

    # Verify empty result
    assert len(result) == 0
