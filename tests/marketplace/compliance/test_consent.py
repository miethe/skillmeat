"""Tests for consent logger."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from skillmeat.marketplace.compliance.consent import ConsentLogger, ConsentRecord


@pytest.fixture
def consent_logger(tmp_path):
    """Create consent logger with temp storage."""
    return ConsentLogger(storage_dir=tmp_path)


def test_consent_record_creation():
    """Test consent record creation."""
    record = ConsentRecord(
        consent_id="test-consent-1",
        checklist_id="checklist-1",
        bundle_id="bundle-1",
        publisher_email="test@example.com",
        timestamp=datetime.utcnow(),
        consents={"item1": True, "item2": True},
        signature="sha256:abcdef",
    )

    assert record.consent_id == "test-consent-1"
    assert record.checklist_id == "checklist-1"
    assert record.bundle_id == "bundle-1"
    assert record.publisher_email == "test@example.com"
    assert record.signature == "sha256:abcdef"


def test_consent_record_validation():
    """Test consent record validation."""
    with pytest.raises(ValueError, match="consent_id cannot be empty"):
        ConsentRecord(
            consent_id="",
            checklist_id="test",
            bundle_id="test",
            publisher_email="test@example.com",
            timestamp=datetime.utcnow(),
            consents={},
            signature="test",
        )


def test_consent_record_to_dict():
    """Test consent record to dict conversion."""
    record = ConsentRecord(
        consent_id="test-consent-1",
        checklist_id="checklist-1",
        bundle_id="bundle-1",
        publisher_email="test@example.com",
        timestamp=datetime.utcnow(),
        consents={"item1": True},
        signature="sha256:abcdef",
        ip_address="127.0.0.1",
    )

    data = record.to_dict()

    assert data["consent_id"] == "test-consent-1"
    assert data["checklist_id"] == "checklist-1"
    assert data["publisher_email"] == "test@example.com"
    assert data["ip_address"] == "127.0.0.1"


def test_consent_record_from_dict():
    """Test consent record from dict conversion."""
    data = {
        "consent_id": "test-consent-1",
        "checklist_id": "checklist-1",
        "bundle_id": "bundle-1",
        "publisher_email": "test@example.com",
        "timestamp": "2024-01-01T00:00:00",
        "consents": {"item1": True},
        "signature": "sha256:abcdef",
        "ip_address": "127.0.0.1",
    }

    record = ConsentRecord.from_dict(data)

    assert record.consent_id == "test-consent-1"
    assert isinstance(record.timestamp, datetime)


def test_consent_logger_initialization(tmp_path):
    """Test consent logger initialization."""
    logger = ConsentLogger(storage_dir=tmp_path)

    assert logger.storage_dir == tmp_path
    assert logger.consent_file.exists()


def test_record_consent(consent_logger):
    """Test recording consent."""
    record = consent_logger.record_consent(
        checklist_id="checklist-1",
        bundle_id="bundle-1",
        publisher_email="test@example.com",
        consents={"item1": True, "item2": True},
    )

    assert record.consent_id is not None
    assert record.signature.startswith("sha256:")
    assert isinstance(record.timestamp, datetime)


def test_record_consent_with_ip(consent_logger):
    """Test recording consent with IP address."""
    record = consent_logger.record_consent(
        checklist_id="checklist-1",
        bundle_id="bundle-1",
        publisher_email="test@example.com",
        consents={"item1": True},
        ip_address="192.168.1.1",
    )

    assert record.ip_address == "192.168.1.1"


def test_verify_consent(consent_logger):
    """Test verifying consent."""
    record = consent_logger.record_consent(
        checklist_id="checklist-1",
        bundle_id="bundle-1",
        publisher_email="test@example.com",
        consents={"item1": True},
    )

    assert consent_logger.verify_consent(record.consent_id) is True


def test_verify_consent_invalid_id(consent_logger):
    """Test verifying invalid consent ID."""
    assert consent_logger.verify_consent("invalid-id") is False


def test_get_consent(consent_logger):
    """Test getting consent by ID."""
    record = consent_logger.record_consent(
        checklist_id="checklist-1",
        bundle_id="bundle-1",
        publisher_email="test@example.com",
        consents={"item1": True},
    )

    retrieved = consent_logger.get_consent(record.consent_id)

    assert retrieved is not None
    assert retrieved.consent_id == record.consent_id
    assert retrieved.publisher_email == "test@example.com"


def test_get_consent_not_found(consent_logger):
    """Test getting non-existent consent."""
    retrieved = consent_logger.get_consent("non-existent")

    assert retrieved is None


def test_get_consent_history(consent_logger):
    """Test getting consent history."""
    # Record multiple consents
    consent_logger.record_consent(
        checklist_id="checklist-1",
        bundle_id="bundle-1",
        publisher_email="user1@example.com",
        consents={"item1": True},
    )
    consent_logger.record_consent(
        checklist_id="checklist-2",
        bundle_id="bundle-2",
        publisher_email="user2@example.com",
        consents={"item1": True},
    )

    history = consent_logger.get_consent_history()

    assert len(history) == 2


def test_get_consent_history_filtered(consent_logger):
    """Test getting filtered consent history."""
    consent_logger.record_consent(
        checklist_id="checklist-1",
        bundle_id="bundle-1",
        publisher_email="user1@example.com",
        consents={"item1": True},
    )
    consent_logger.record_consent(
        checklist_id="checklist-2",
        bundle_id="bundle-2",
        publisher_email="user2@example.com",
        consents={"item1": True},
    )

    history = consent_logger.get_consent_history(publisher_email="user1@example.com")

    assert len(history) == 1
    assert history[0].publisher_email == "user1@example.com"


def test_export_consent(consent_logger):
    """Test exporting consent."""
    record = consent_logger.record_consent(
        checklist_id="checklist-1",
        bundle_id="bundle-1",
        publisher_email="test@example.com",
        consents={"item1": True},
    )

    exported = consent_logger.export_consent(record.consent_id)

    assert exported is not None
    data = json.loads(exported)
    assert data["consent_id"] == record.consent_id


def test_export_consent_not_found(consent_logger):
    """Test exporting non-existent consent."""
    exported = consent_logger.export_consent("non-existent")

    assert exported is None


def test_get_consents_for_bundle(consent_logger):
    """Test getting consents for bundle."""
    consent_logger.record_consent(
        checklist_id="checklist-1",
        bundle_id="bundle-1",
        publisher_email="test@example.com",
        consents={"item1": True},
    )
    consent_logger.record_consent(
        checklist_id="checklist-2",
        bundle_id="bundle-1",
        publisher_email="test@example.com",
        consents={"item2": True},
    )
    consent_logger.record_consent(
        checklist_id="checklist-3",
        bundle_id="bundle-2",
        publisher_email="test@example.com",
        consents={"item3": True},
    )

    records = consent_logger.get_consents_for_bundle("bundle-1")

    assert len(records) == 2
    assert all(r.bundle_id == "bundle-1" for r in records)


def test_get_consents_for_checklist(consent_logger):
    """Test getting consents for checklist."""
    consent_logger.record_consent(
        checklist_id="checklist-1",
        bundle_id="bundle-1",
        publisher_email="test@example.com",
        consents={"item1": True},
    )
    consent_logger.record_consent(
        checklist_id="checklist-1",
        bundle_id="bundle-2",
        publisher_email="test@example.com",
        consents={"item2": True},
    )

    records = consent_logger.get_consents_for_checklist("checklist-1")

    assert len(records) == 2
    assert all(r.checklist_id == "checklist-1" for r in records)


def test_get_statistics(consent_logger):
    """Test getting statistics."""
    consent_logger.record_consent(
        checklist_id="checklist-1",
        bundle_id="bundle-1",
        publisher_email="user1@example.com",
        consents={"item1": True, "item2": True},
    )
    consent_logger.record_consent(
        checklist_id="checklist-2",
        bundle_id="bundle-2",
        publisher_email="user2@example.com",
        consents={"item1": True, "item2": False},
    )

    stats = consent_logger.get_statistics()

    assert stats["total_consents"] == 2
    assert stats["unique_publishers"] == 2
    assert stats["unique_bundles"] == 2
    assert stats["full_consents"] == 1  # Only first has all True
    assert stats["partial_consents"] == 1


def test_signature_generation(consent_logger):
    """Test that signatures are deterministic."""
    record1 = consent_logger.record_consent(
        checklist_id="checklist-1",
        bundle_id="bundle-1",
        publisher_email="test@example.com",
        consents={"item1": True},
    )

    # Create another record with same data
    record2 = ConsentRecord(
        consent_id=record1.consent_id,
        checklist_id=record1.checklist_id,
        bundle_id=record1.bundle_id,
        publisher_email=record1.publisher_email,
        timestamp=record1.timestamp,
        consents=record1.consents,
        signature="",
    )

    # Generate signature for record2
    signature2 = consent_logger._generate_signature(record2)

    # Signatures should match
    assert record1.signature == signature2


def test_consent_history_sorted_by_date(consent_logger):
    """Test that history is sorted by date (newest first)."""
    import time

    # Record consents with small delays
    consent_logger.record_consent(
        checklist_id="checklist-1",
        bundle_id="bundle-1",
        publisher_email="test@example.com",
        consents={"item1": True},
    )

    time.sleep(0.01)  # Small delay

    consent_logger.record_consent(
        checklist_id="checklist-2",
        bundle_id="bundle-2",
        publisher_email="test@example.com",
        consents={"item2": True},
    )

    history = consent_logger.get_consent_history()

    # First should be newest
    assert history[0].checklist_id == "checklist-2"
    assert history[1].checklist_id == "checklist-1"
