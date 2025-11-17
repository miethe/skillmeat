"""Tests for publisher metadata validation."""

import pytest
from pydantic import ValidationError

from skillmeat.core.marketplace.metadata import (
    MetadataValidationError,
    MetadataValidator,
    PublisherMetadata,
)
from skillmeat.core.marketplace.models import ArtifactCategory


@pytest.fixture
def validator():
    """Create metadata validator."""
    return MetadataValidator()


@pytest.fixture
def valid_metadata_dict():
    """Create valid metadata dictionary."""
    return {
        "name": "Test Bundle",
        "description": "This is a test bundle with sufficient description length.",
        "category": "skill",
        "version": "1.0.0",
        "license": "MIT",
        "tags": ["testing", "automation"],
        "homepage": "https://example.com",
        "repository": "https://github.com/user/repo",
    }


def test_publisher_metadata_creation(valid_metadata_dict):
    """Test PublisherMetadata creation."""
    metadata = PublisherMetadata(**valid_metadata_dict)

    assert metadata.name == "Test Bundle"
    assert metadata.version == "1.0.0"
    assert metadata.category == ArtifactCategory.SKILL
    assert len(metadata.tags) == 2


def test_name_validation_too_short():
    """Test name must be at least 3 characters."""
    with pytest.raises(ValidationError):
        PublisherMetadata(
            name="AB",
            description="Valid description here",
            category="skill",
            version="1.0.0",
            license="MIT",
        )


def test_name_validation_too_long():
    """Test name must not exceed 100 characters."""
    with pytest.raises(ValidationError):
        PublisherMetadata(
            name="A" * 101,
            description="Valid description",
            category="skill",
            version="1.0.0",
            license="MIT",
        )


def test_name_validation_invalid_characters():
    """Test name can only contain valid characters."""
    with pytest.raises(ValidationError):
        PublisherMetadata(
            name="Test@Bundle!",
            description="Valid description",
            category="skill",
            version="1.0.0",
            license="MIT",
        )


def test_description_validation_too_short():
    """Test description must be at least 10 characters."""
    with pytest.raises(ValidationError):
        PublisherMetadata(
            name="Test Bundle",
            description="Short",
            category="skill",
            version="1.0.0",
            license="MIT",
        )


def test_version_validation_semver():
    """Test version must be valid semver."""
    # Valid semver
    metadata = PublisherMetadata(
        name="Test",
        description="Valid description",
        category="skill",
        version="1.0.0",
        license="MIT",
    )
    assert metadata.version == "1.0.0"

    # Invalid semver
    with pytest.raises(ValidationError):
        PublisherMetadata(
            name="Test",
            description="Valid description",
            category="skill",
            version="1.0",
            license="MIT",
        )


def test_version_validation_prerelease():
    """Test semver with prerelease."""
    metadata = PublisherMetadata(
        name="Test",
        description="Valid description",
        category="skill",
        version="1.0.0-beta.1",
        license="MIT",
    )
    assert metadata.version == "1.0.0-beta.1"


def test_tags_validation_max_count():
    """Test maximum 10 tags allowed."""
    with pytest.raises(ValidationError):
        PublisherMetadata(
            name="Test",
            description="Valid description",
            category="skill",
            version="1.0.0",
            license="MIT",
            tags=["tag" + str(i) for i in range(11)],
        )


def test_tags_validation_length():
    """Test tag length constraints."""
    # Tag too short
    with pytest.raises(ValidationError):
        PublisherMetadata(
            name="Test",
            description="Valid description",
            category="skill",
            version="1.0.0",
            license="MIT",
            tags=["a"],
        )

    # Tag too long
    with pytest.raises(ValidationError):
        PublisherMetadata(
            name="Test",
            description="Valid description",
            category="skill",
            version="1.0.0",
            license="MIT",
            tags=["a" * 31],
        )


def test_tags_validation_invalid_characters():
    """Test tags can only contain valid characters."""
    with pytest.raises(ValidationError):
        PublisherMetadata(
            name="Test",
            description="Valid description",
            category="skill",
            version="1.0.0",
            license="MIT",
            tags=["invalid tag!"],
        )


def test_tags_validation_duplicates():
    """Test duplicate tags not allowed."""
    with pytest.raises(ValidationError):
        PublisherMetadata(
            name="Test",
            description="Valid description",
            category="skill",
            version="1.0.0",
            license="MIT",
            tags=["test", "test"],
        )


def test_metadata_validator_validate_metadata(validator, valid_metadata_dict):
    """Test metadata validation."""
    validated = validator.validate_metadata(valid_metadata_dict)

    assert validated.name == "Test Bundle"
    assert validated.version == "1.0.0"


def test_metadata_validator_missing_fields(validator):
    """Test validation fails with missing required fields."""
    with pytest.raises(MetadataValidationError, match="Missing required fields"):
        validator.validate_metadata({"name": "Test"})


def test_metadata_validator_with_suggestions(validator, valid_metadata_dict):
    """Test validation with suggestions."""
    # Remove optional fields to get suggestions
    minimal_metadata = {
        "name": "Test",
        "description": "Short description",
        "category": "skill",
        "version": "1.0.0",
        "license": "MIT",
    }

    validated, suggestions = validator.validate_metadata_with_suggestions(minimal_metadata)

    assert validated is not None
    assert len(suggestions) > 0
    # Should suggest adding homepage, repository, more tags
    assert any("homepage" in s.lower() for s in suggestions)
    assert any("repository" in s.lower() for s in suggestions)


def test_metadata_validator_suggest_tags(validator):
    """Test tag suggestion based on content."""
    tags = validator.suggest_tags(
        name="API Testing Tool",
        description="Automated testing for REST APIs",
    )

    assert len(tags) > 0
    assert "testing" in tags
    assert "api" in tags


def test_metadata_validator_validate_version_increment(validator):
    """Test version increment validation."""
    # First version
    assert validator.validate_version_increment("1.0.0", None)

    # Valid increments
    assert validator.validate_version_increment("1.0.1", "1.0.0")
    assert validator.validate_version_increment("1.1.0", "1.0.0")
    assert validator.validate_version_increment("2.0.0", "1.0.0")

    # Invalid increments
    assert not validator.validate_version_increment("1.0.0", "1.0.0")  # Same version
    assert not validator.validate_version_increment("0.9.0", "1.0.0")  # Downgrade


def test_metadata_validator_sanitize_metadata(validator):
    """Test metadata sanitization."""
    dirty_metadata = {
        "name": "  Test Bundle  ",
        "description": "  Description  ",
        "tags": ["  tag1  ", "", "  tag2  "],
    }

    sanitized = validator.sanitize_metadata(dirty_metadata)

    assert sanitized["name"] == "Test Bundle"
    assert sanitized["description"] == "Description"
    assert sanitized["tags"] == ["tag1", "tag2"]


def test_metadata_validator_get_validation_summary(validator, valid_metadata_dict):
    """Test validation summary generation."""
    validated = validator.validate_metadata(valid_metadata_dict)
    summary = validator.get_validation_summary(validated)

    assert "Test Bundle" in summary
    assert "1.0.0" in summary
    assert "MIT" in summary
