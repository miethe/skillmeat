"""Tests for submission tracking."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from skillmeat.config import ConfigManager
from skillmeat.core.marketplace.submission import (
    Submission,
    SubmissionStatus,
    SubmissionStore,
)


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory."""
    config_dir = tmp_path / ".skillmeat"
    config_dir.mkdir(parents=True)
    return config_dir


@pytest.fixture
def config_manager(temp_config_dir):
    """Create config manager with temp directory."""
    config_path = temp_config_dir / "config.toml"
    config_path.write_text("[settings]\n")
    # ConfigManager expects directory path, not file path
    return ConfigManager(config_dir=temp_config_dir)


@pytest.fixture
def submission_store(config_manager):
    """Create submission store."""
    return SubmissionStore(config_manager)


@pytest.fixture
def sample_submission():
    """Create sample submission."""
    return Submission(
        submission_id="sub-2025-11-17-abc123",
        bundle_path="/path/to/bundle.skillmeat-pack",
        broker_name="skillmeat",
        metadata={
            "name": "Test Bundle",
            "version": "1.0.0",
            "category": "skill",
            "license": "MIT",
        },
        status=SubmissionStatus.PENDING,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def test_submission_status_enum():
    """Test SubmissionStatus enum."""
    assert SubmissionStatus.PENDING == "pending"
    assert SubmissionStatus.VALIDATING == "validating"
    assert SubmissionStatus.APPROVED == "approved"
    assert SubmissionStatus.REJECTED == "rejected"
    assert SubmissionStatus.PUBLISHED == "published"
    assert SubmissionStatus.FAILED == "failed"


def test_submission_creation(sample_submission):
    """Test Submission model creation."""
    assert sample_submission.submission_id == "sub-2025-11-17-abc123"
    assert sample_submission.bundle_path == "/path/to/bundle.skillmeat-pack"
    assert sample_submission.broker_name == "skillmeat"
    assert sample_submission.status == SubmissionStatus.PENDING
    assert sample_submission.metadata["name"] == "Test Bundle"


def test_submission_to_dict(sample_submission):
    """Test Submission.to_dict()."""
    data = sample_submission.to_dict()

    assert data["submission_id"] == "sub-2025-11-17-abc123"
    assert data["bundle_path"] == "/path/to/bundle.skillmeat-pack"
    assert data["broker_name"] == "skillmeat"
    assert data["status"] == "pending"
    assert "created_at" in data
    assert "updated_at" in data


def test_submission_from_dict():
    """Test Submission.from_dict()."""
    data = {
        "submission_id": "sub-test",
        "bundle_path": "/path/to/bundle",
        "broker_name": "test-broker",
        "metadata": {"name": "Test"},
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    submission = Submission.from_dict(data)

    assert submission.submission_id == "sub-test"
    assert submission.bundle_path == "/path/to/bundle"
    assert submission.status == SubmissionStatus.PENDING


def test_submission_store_initialization(submission_store):
    """Test SubmissionStore initialization."""
    assert submission_store.storage_path.exists()

    # Read storage file
    with open(submission_store.storage_path) as f:
        data = json.load(f)

    assert data["version"] == "1.0"
    assert data["submissions"] == []


def test_submission_store_add_submission(submission_store, sample_submission):
    """Test adding submission to store."""
    submission_store.add_submission(sample_submission)

    # Verify submission was added
    retrieved = submission_store.get_submission(sample_submission.submission_id)
    assert retrieved is not None
    assert retrieved.submission_id == sample_submission.submission_id
    assert retrieved.bundle_path == sample_submission.bundle_path


def test_submission_store_add_duplicate(submission_store, sample_submission):
    """Test adding duplicate submission fails."""
    submission_store.add_submission(sample_submission)

    with pytest.raises(ValueError, match="already exists"):
        submission_store.add_submission(sample_submission)


def test_submission_store_get_submission(submission_store, sample_submission):
    """Test getting submission by ID."""
    submission_store.add_submission(sample_submission)

    retrieved = submission_store.get_submission(sample_submission.submission_id)
    assert retrieved is not None
    assert retrieved.submission_id == sample_submission.submission_id


def test_submission_store_get_nonexistent(submission_store):
    """Test getting nonexistent submission returns None."""
    result = submission_store.get_submission("nonexistent-id")
    assert result is None


def test_submission_store_update_submission(submission_store, sample_submission):
    """Test updating submission."""
    submission_store.add_submission(sample_submission)

    # Update submission
    sample_submission.status = SubmissionStatus.APPROVED
    sample_submission.listing_id = "list-123"
    submission_store.update_submission(sample_submission)

    # Verify update
    retrieved = submission_store.get_submission(sample_submission.submission_id)
    assert retrieved.status == SubmissionStatus.APPROVED
    assert retrieved.listing_id == "list-123"


def test_submission_store_update_nonexistent(submission_store, sample_submission):
    """Test updating nonexistent submission fails."""
    with pytest.raises(ValueError, match="not found"):
        submission_store.update_submission(sample_submission)


def test_submission_store_list_submissions(submission_store):
    """Test listing submissions."""
    # Add multiple submissions
    submissions = [
        Submission(
            submission_id=f"sub-{i}",
            bundle_path=f"/path/to/bundle-{i}",
            broker_name="skillmeat",
            metadata={"name": f"Bundle {i}"},
            status=SubmissionStatus.PENDING if i % 2 == 0 else SubmissionStatus.PUBLISHED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        for i in range(5)
    ]

    for submission in submissions:
        submission_store.add_submission(submission)

    # List all submissions
    all_submissions = submission_store.list_submissions()
    assert len(all_submissions) == 5

    # List pending submissions
    pending = submission_store.list_submissions(status=SubmissionStatus.PENDING)
    assert len(pending) == 3  # 0, 2, 4

    # List published submissions
    published = submission_store.list_submissions(status=SubmissionStatus.PUBLISHED)
    assert len(published) == 2  # 1, 3


def test_submission_store_list_with_broker_filter(submission_store):
    """Test listing submissions with broker filter."""
    # Add submissions with different brokers
    submission1 = Submission(
        submission_id="sub-1",
        bundle_path="/path/1",
        broker_name="broker-a",
        metadata={},
        status=SubmissionStatus.PENDING,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    submission2 = Submission(
        submission_id="sub-2",
        bundle_path="/path/2",
        broker_name="broker-b",
        metadata={},
        status=SubmissionStatus.PENDING,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    submission_store.add_submission(submission1)
    submission_store.add_submission(submission2)

    # Filter by broker
    broker_a = submission_store.list_submissions(broker_name="broker-a")
    assert len(broker_a) == 1
    assert broker_a[0].submission_id == "sub-1"


def test_submission_store_list_with_limit(submission_store):
    """Test listing submissions with limit."""
    # Add 10 submissions
    for i in range(10):
        submission = Submission(
            submission_id=f"sub-{i}",
            bundle_path=f"/path/{i}",
            broker_name="skillmeat",
            metadata={},
            status=SubmissionStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        submission_store.add_submission(submission)

    # List with limit
    limited = submission_store.list_submissions(limit=5)
    assert len(limited) == 5


def test_submission_store_delete_submission(submission_store, sample_submission):
    """Test deleting submission."""
    submission_store.add_submission(sample_submission)

    # Delete submission
    result = submission_store.delete_submission(sample_submission.submission_id)
    assert result is True

    # Verify deletion
    retrieved = submission_store.get_submission(sample_submission.submission_id)
    assert retrieved is None


def test_submission_store_delete_nonexistent(submission_store):
    """Test deleting nonexistent submission."""
    result = submission_store.delete_submission("nonexistent-id")
    assert result is False


def test_submission_store_get_stats(submission_store):
    """Test getting submission statistics."""
    # Add submissions with different statuses
    statuses = [
        SubmissionStatus.PENDING,
        SubmissionStatus.PENDING,
        SubmissionStatus.PUBLISHED,
        SubmissionStatus.REJECTED,
        SubmissionStatus.FAILED,
    ]

    for i, status in enumerate(statuses):
        submission = Submission(
            submission_id=f"sub-{i}",
            bundle_path=f"/path/{i}",
            broker_name="skillmeat",
            metadata={},
            status=status,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        submission_store.add_submission(submission)

    # Get stats
    stats = submission_store.get_stats()

    assert stats["total"] == 5
    assert stats["pending"] == 2
    assert stats["published"] == 1
    assert stats["rejected"] == 1
    assert stats["failed"] == 1
    assert stats["validating"] == 0
    assert stats["approved"] == 0
