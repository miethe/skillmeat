"""Tests for publisher service."""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from skillmeat.core.marketplace.license import LicenseCompatibility
from skillmeat.core.marketplace.metadata import PublisherMetadata
from skillmeat.core.marketplace.models import PublishResult
from skillmeat.core.marketplace.publisher import PublisherService
from skillmeat.core.marketplace.submission import SubmissionStatus


@pytest.fixture
def publisher_service(tmp_path):
    """Create publisher service with isolated storage."""
    from skillmeat.config import ConfigManager
    from skillmeat.core.marketplace.submission import SubmissionStore

    # Create isolated config directory
    config_dir = tmp_path / ".skillmeat"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "config.toml"
    config_path.write_text("[settings]\n")

    config_mgr = ConfigManager(config_dir=config_dir)
    submission_store = SubmissionStore(config_mgr)

    return PublisherService(
        config_manager=config_mgr,
        submission_store=submission_store,
    )


@pytest.fixture
def valid_metadata():
    """Create valid publisher metadata."""
    return PublisherMetadata(
        name="Test Bundle",
        description="This is a comprehensive test bundle description.",
        category="skill",
        version="1.0.0",
        license="MIT",
        tags=["testing", "automation"],
        sign_bundle=True,
    )


@pytest.fixture
def mock_broker():
    """Create mock marketplace broker."""
    broker = Mock()
    broker.name = "test-broker"
    return broker


def test_publisher_service_initialization(publisher_service):
    """Test PublisherService initialization."""
    assert publisher_service.config_manager is not None
    assert publisher_service.submission_store is not None
    assert publisher_service.metadata_validator is not None
    assert publisher_service.license_validator is not None


def test_register_broker(publisher_service, mock_broker):
    """Test registering a marketplace broker."""
    publisher_service.register_broker(mock_broker)

    assert publisher_service.get_broker("test-broker") == mock_broker


def test_get_broker_nonexistent(publisher_service):
    """Test getting nonexistent broker returns None."""
    result = publisher_service.get_broker("nonexistent")
    assert result is None


def test_validate_metadata_success(publisher_service):
    """Test successful metadata validation."""
    metadata_dict = {
        "name": "Test Bundle",
        "description": "Valid description with sufficient length.",
        "category": "skill",
        "version": "1.0.0",
        "license": "MIT",
    }

    validated, suggestions = publisher_service.validate_metadata(metadata_dict)

    assert validated.name == "Test Bundle"
    assert validated.version == "1.0.0"
    assert isinstance(suggestions, list)


def test_validate_metadata_invalid(publisher_service):
    """Test metadata validation with invalid data."""
    from skillmeat.core.marketplace.metadata import MetadataValidationError

    metadata_dict = {
        "name": "A",  # Too short
        "description": "Short",  # Too short
    }

    with pytest.raises(MetadataValidationError):
        publisher_service.validate_metadata(metadata_dict)


def test_validate_license_compatible(publisher_service, tmp_path):
    """Test license validation for compatible licenses."""
    # Create a mock bundle file
    bundle_path = tmp_path / "test-bundle.skillmeat-pack"
    bundle_path.touch()

    # Mock inspect_bundle to return a bundle with MIT-licensed artifacts
    with patch("skillmeat.core.marketplace.publisher.inspect_bundle") as mock_inspect:
        mock_bundle = Mock()
        mock_bundle.artifacts = [
            Mock(metadata={"license": "MIT"}),
            Mock(metadata={"license": "Apache-2.0"}),
        ]
        mock_inspect.return_value = mock_bundle

        result = publisher_service.validate_license(bundle_path, "MIT")

        assert result.is_valid
        assert result.compatibility == LicenseCompatibility.COMPATIBLE


def test_validate_license_incompatible(publisher_service, tmp_path):
    """Test license validation for incompatible licenses."""
    bundle_path = tmp_path / "test-bundle.skillmeat-pack"
    bundle_path.touch()

    # Mock inspect_bundle to return GPL and Proprietary
    with patch("skillmeat.core.marketplace.publisher.inspect_bundle") as mock_inspect:
        mock_bundle = Mock()
        mock_bundle.artifacts = [
            Mock(metadata={"license": "GPL-3.0"}),
            Mock(metadata={"license": "Proprietary"}),
        ]
        mock_inspect.return_value = mock_bundle

        result = publisher_service.validate_license(bundle_path, "GPL-3.0")

        assert not result.is_valid
        assert result.compatibility == LicenseCompatibility.INCOMPATIBLE


def test_create_submission(publisher_service, valid_metadata, tmp_path):
    """Test creating submission record."""
    bundle_path = tmp_path / "test-bundle.skillmeat-pack"
    bundle_path.touch()

    publish_result = PublishResult(
        success=True,
        listing_id="list-123",
        listing_url="https://example.com/list-123",
        message="Published successfully",
    )

    submission = publisher_service.create_submission(
        bundle_path=bundle_path,
        metadata=valid_metadata,
        broker_name="test-broker",
        publish_result=publish_result,
    )

    assert submission.submission_id == "list-123"
    assert submission.bundle_path == str(bundle_path)
    assert submission.broker_name == "test-broker"
    assert submission.status == SubmissionStatus.PENDING
    assert submission.listing_id == "list-123"


def test_get_submission_status(publisher_service, valid_metadata, tmp_path):
    """Test getting submission status."""
    bundle_path = tmp_path / "test-bundle.skillmeat-pack"
    bundle_path.touch()

    publish_result = PublishResult(
        success=True,
        listing_id="sub-test-123",
        message="Published",
    )

    # Create submission
    submission = publisher_service.create_submission(
        bundle_path=bundle_path,
        metadata=valid_metadata,
        broker_name="test-broker",
        publish_result=publish_result,
    )

    # Get submission status
    retrieved = publisher_service.get_submission_status(submission.submission_id)

    assert retrieved is not None
    assert retrieved.submission_id == submission.submission_id


def test_update_submission_status(publisher_service, valid_metadata, tmp_path):
    """Test updating submission status."""
    bundle_path = tmp_path / "test-bundle.skillmeat-pack"
    bundle_path.touch()

    publish_result = PublishResult(
        success=True,
        listing_id="sub-test-update",
        message="Published",
    )

    # Create submission
    submission = publisher_service.create_submission(
        bundle_path=bundle_path,
        metadata=valid_metadata,
        broker_name="test-broker",
        publish_result=publish_result,
    )

    # Update status
    publisher_service.update_submission_status(
        submission_id=submission.submission_id,
        status=SubmissionStatus.PUBLISHED,
        moderation_feedback="Approved!",
    )

    # Verify update
    updated = publisher_service.get_submission_status(submission.submission_id)
    assert updated.status == SubmissionStatus.PUBLISHED
    assert updated.moderation_feedback == "Approved!"


def test_list_submissions(publisher_service):
    """Test listing submissions."""
    # List should be empty initially (or from previous tests)
    submissions = publisher_service.list_submissions()
    initial_count = len(submissions)

    # Add some submissions
    for i in range(3):
        publish_result = PublishResult(
            success=True,
            listing_id=f"sub-list-{i}",
            message="Published",
        )

        bundle_path = Path(f"/tmp/bundle-{i}.skillmeat-pack")
        metadata = PublisherMetadata(
            name=f"Bundle {i}",
            description="Test bundle description",
            category="skill",
            version="1.0.0",
            license="MIT",
        )

        publisher_service.create_submission(
            bundle_path=bundle_path,
            metadata=metadata,
            broker_name="test-broker",
            publish_result=publish_result,
        )

    # List all submissions
    all_submissions = publisher_service.list_submissions()
    assert len(all_submissions) >= initial_count + 3


def test_list_submissions_filtered(publisher_service):
    """Test listing submissions with filters."""
    # Add submission with specific broker and status
    publish_result = PublishResult(
        success=True,
        listing_id="sub-filter-test",
        message="Published",
    )

    metadata = PublisherMetadata(
        name="Filter Test",
        description="Test bundle for filtering",
        category="skill",
        version="1.0.0",
        license="MIT",
    )

    submission = publisher_service.create_submission(
        bundle_path=Path("/tmp/filter-test.skillmeat-pack"),
        metadata=metadata,
        broker_name="filter-broker",
        publish_result=publish_result,
    )

    # Filter by broker
    filtered = publisher_service.list_submissions(broker_name="filter-broker")
    assert len(filtered) >= 1
    assert any(s.submission_id == submission.submission_id for s in filtered)


def test_get_submission_stats(publisher_service):
    """Test getting submission statistics."""
    stats = publisher_service.get_submission_stats()

    assert "total" in stats
    assert "pending" in stats
    assert "published" in stats
    assert isinstance(stats["total"], int)


def test_check_signing_key_available(publisher_service):
    """Test checking if signing key is available."""
    # This will fail in test environment without keys
    result = publisher_service.check_signing_key_available()
    assert isinstance(result, bool)


def test_get_recommended_licenses(publisher_service):
    """Test getting recommended licenses."""
    licenses = publisher_service.get_recommended_licenses()

    assert len(licenses) > 0
    assert "MIT" in licenses
    assert "Apache-2.0" in licenses


def test_explain_license(publisher_service):
    """Test explaining a license."""
    explanation = publisher_service.explain_license("MIT")

    assert "MIT" in explanation
    assert len(explanation) > 0


def test_publish_bundle_dry_run(publisher_service, valid_metadata, tmp_path, mock_broker):
    """Test publishing bundle in dry-run mode."""
    # Create mock bundle
    bundle_path = tmp_path / "test-bundle.skillmeat-pack"
    bundle_path.touch()

    # Register broker
    publisher_service.register_broker(mock_broker)

    # Mock inspect_bundle
    with patch("skillmeat.core.marketplace.publisher.inspect_bundle") as mock_inspect:
        mock_bundle = Mock()
        mock_bundle.artifacts = [Mock(metadata={"license": "MIT"})]
        mock_inspect.return_value = mock_bundle

        # Publish in dry-run mode
        result = publisher_service.publish_bundle(
            bundle_path=bundle_path,
            metadata=valid_metadata,
            broker_name="test-broker",
            validate_license=True,
            sign_bundle=False,
            dry_run=True,
        )

        assert result.success
        assert "Dry run successful" in result.message


def test_publish_bundle_bundle_not_found(publisher_service, valid_metadata, mock_broker):
    """Test publishing nonexistent bundle fails."""
    from skillmeat.core.marketplace.publisher import PublisherError

    # Register broker
    publisher_service.register_broker(mock_broker)

    # Try to publish nonexistent bundle
    with pytest.raises(PublisherError, match="Bundle not found"):
        publisher_service.publish_bundle(
            bundle_path=Path("/nonexistent/bundle.skillmeat-pack"),
            metadata=valid_metadata,
            broker_name="test-broker",
            dry_run=False,
        )


def test_publish_bundle_unknown_broker(publisher_service, valid_metadata, tmp_path):
    """Test publishing to unknown broker fails."""
    from skillmeat.core.marketplace.publisher import PublisherError

    bundle_path = tmp_path / "test-bundle.skillmeat-pack"
    bundle_path.touch()

    with pytest.raises(PublisherError, match="Unknown marketplace broker"):
        publisher_service.publish_bundle(
            bundle_path=bundle_path,
            metadata=valid_metadata,
            broker_name="unknown-broker",
            dry_run=False,
        )
