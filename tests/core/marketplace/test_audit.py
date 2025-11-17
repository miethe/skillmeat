"""Tests for audit module."""

import json
import pytest
import tempfile
from datetime import datetime
from pathlib import Path

from skillmeat.core.marketplace.audit import (
    AuditEvent,
    AuditEventType,
    AuditLogger,
)
from skillmeat.core.marketplace.compliance import ConsentLog


class TestAuditEvent:
    """Tests for AuditEvent model."""

    def test_create_audit_event(self):
        """Test creating an audit event."""
        event = AuditEvent(
            event_id="evt-123",
            event_type=AuditEventType.CONSENT_LOGGED,
            timestamp="2025-11-17T12:00:00",
            user_id="test-user",
            details={"key": "value"},
            event_hash="abc123",
        )

        assert event.event_id == "evt-123"
        assert event.event_type == AuditEventType.CONSENT_LOGGED
        assert event.user_id == "test-user"
        assert event.details == {"key": "value"}

    def test_compute_hash(self):
        """Test computing event hash."""
        event = AuditEvent(
            event_id="evt-123",
            event_type=AuditEventType.CONSENT_LOGGED,
            timestamp="2025-11-17T12:00:00",
            user_id="test-user",
            submission_id="sub-123",
            details={"key": "value"},
            event_hash="placeholder",
        )

        hash_value = event.compute_hash(previous_hash=None)

        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # SHA256 hex digest

    def test_compute_hash_with_previous(self):
        """Test computing hash with previous event hash (chaining)."""
        event = AuditEvent(
            event_id="evt-123",
            event_type=AuditEventType.CONSENT_LOGGED,
            timestamp="2025-11-17T12:00:00",
            user_id="test-user",
            details={"key": "value"},
            event_hash="placeholder",
        )

        hash_no_prev = event.compute_hash(previous_hash=None)
        hash_with_prev = event.compute_hash(previous_hash="prev123")

        # Hashes should be different
        assert hash_no_prev != hash_with_prev

    def test_verify_hash_valid(self):
        """Test verifying a valid event hash."""
        event = AuditEvent(
            event_id="evt-123",
            event_type=AuditEventType.CONSENT_LOGGED,
            timestamp="2025-11-17T12:00:00",
            user_id="test-user",
            details={"key": "value"},
            previous_hash=None,
            event_hash="",
        )

        # Compute and set hash
        event.event_hash = event.compute_hash()

        assert event.verify_hash() is True

    def test_verify_hash_invalid(self):
        """Test detecting invalid event hash (tampering)."""
        event = AuditEvent(
            event_id="evt-123",
            event_type=AuditEventType.CONSENT_LOGGED,
            timestamp="2025-11-17T12:00:00",
            user_id="test-user",
            details={"key": "value"},
            event_hash="",
        )

        # Set valid hash
        event.event_hash = event.compute_hash()

        # Tamper with data
        event.user_id = "hacker"

        assert event.verify_hash() is False


class TestAuditLogger:
    """Tests for AuditLogger."""

    @pytest.fixture
    def temp_audit_file(self):
        """Create temporary audit file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl") as f:
            temp_path = Path(f.name)

        yield temp_path

        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    def test_create_audit_logger(self, temp_audit_file):
        """Test creating audit logger."""
        logger = AuditLogger(audit_file=temp_audit_file)

        assert logger.audit_file == temp_audit_file
        assert temp_audit_file.exists()

    def test_log_consent(self, temp_audit_file):
        """Test logging consent event."""
        logger = AuditLogger(audit_file=temp_audit_file)

        consent = ConsentLog.create_with_hash(
            consent_id="consent-123",
            submission_id="sub-123",
            user_id="test-user",
            checklist_version="1.0.0",
            items_acknowledged=["item-1", "item-2"],
            timestamp=datetime.utcnow(),
            agreement_version="1.0.0",
        )

        logger.log_consent(consent)

        # Verify log was written
        assert temp_audit_file.exists()

        with open(temp_audit_file, "r") as f:
            lines = f.readlines()
            assert len(lines) == 1

            log_entry = json.loads(lines[0])
            assert log_entry["event_type"] == "consent_logged"
            assert log_entry["user_id"] == "test-user"
            assert log_entry["submission_id"] == "sub-123"

    def test_log_publication(self, temp_audit_file):
        """Test logging publication event."""
        logger = AuditLogger(audit_file=temp_audit_file)

        logger.log_publication(
            submission_id="sub-123",
            user_id="test-user",
            details={
                "bundle_path": "/path/to/bundle.zip",
                "broker_name": "skillmeat",
            },
            ip_address="127.0.0.1",
        )

        # Verify log was written
        with open(temp_audit_file, "r") as f:
            lines = f.readlines()
            assert len(lines) == 1

            log_entry = json.loads(lines[0])
            assert log_entry["event_type"] == "publication_submitted"
            assert log_entry["details"]["bundle_path"] == "/path/to/bundle.zip"
            assert log_entry["ip_address"] == "127.0.0.1"

    def test_log_status_update(self, temp_audit_file):
        """Test logging status update event."""
        logger = AuditLogger(audit_file=temp_audit_file)

        logger.log_status_update(
            submission_id="sub-123",
            user_id="test-user",
            old_status="pending",
            new_status="approved",
        )

        # Verify log was written
        with open(temp_audit_file, "r") as f:
            lines = f.readlines()
            assert len(lines) == 1

            log_entry = json.loads(lines[0])
            assert log_entry["event_type"] == "publication_approved"
            assert log_entry["details"]["old_status"] == "pending"
            assert log_entry["details"]["new_status"] == "approved"

    def test_log_license_validation(self, temp_audit_file):
        """Test logging license validation event."""
        logger = AuditLogger(audit_file=temp_audit_file)

        logger.log_license_validation(
            submission_id="sub-123",
            user_id="test-user",
            bundle_path="/path/to/bundle.zip",
            validation_result={"is_valid": True, "warnings": []},
        )

        # Verify log was written
        with open(temp_audit_file, "r") as f:
            lines = f.readlines()
            assert len(lines) == 1

            log_entry = json.loads(lines[0])
            assert log_entry["event_type"] == "license_validated"

    def test_log_bundle_signing(self, temp_audit_file):
        """Test logging bundle signing event."""
        logger = AuditLogger(audit_file=temp_audit_file)

        logger.log_bundle_signing(
            submission_id="sub-123",
            user_id="test-user",
            bundle_path="/path/to/bundle.zip",
            key_id="key-123",
        )

        # Verify log was written
        with open(temp_audit_file, "r") as f:
            lines = f.readlines()
            assert len(lines) == 1

            log_entry = json.loads(lines[0])
            assert log_entry["event_type"] == "bundle_signed"
            assert log_entry["details"]["key_id"] == "key-123"

    def test_get_logs_all(self, temp_audit_file):
        """Test retrieving all logs."""
        logger = AuditLogger(audit_file=temp_audit_file)

        # Log multiple events
        logger.log_publication("sub-1", "user-1", {})
        logger.log_publication("sub-2", "user-2", {})
        logger.log_publication("sub-3", "user-3", {})

        logs = logger.get_logs()

        assert len(logs) == 3
        # Should be in reverse order (newest first)
        assert logs[0].submission_id == "sub-3"
        assert logs[2].submission_id == "sub-1"

    def test_get_logs_filtered_by_submission(self, temp_audit_file):
        """Test retrieving logs filtered by submission ID."""
        logger = AuditLogger(audit_file=temp_audit_file)

        logger.log_publication("sub-1", "user-1", {})
        logger.log_publication("sub-2", "user-2", {})
        logger.log_publication("sub-1", "user-1", {})

        logs = logger.get_logs(submission_id="sub-1")

        assert len(logs) == 2
        assert all(log.submission_id == "sub-1" for log in logs)

    def test_get_logs_filtered_by_event_type(self, temp_audit_file):
        """Test retrieving logs filtered by event type."""
        logger = AuditLogger(audit_file=temp_audit_file)

        logger.log_publication("sub-1", "user-1", {})
        logger.log_bundle_signing("sub-1", "user-1", "/path", "key-1")
        logger.log_publication("sub-2", "user-2", {})

        logs = logger.get_logs(event_type=AuditEventType.PUBLICATION_SUBMITTED)

        assert len(logs) == 2
        assert all(log.event_type == AuditEventType.PUBLICATION_SUBMITTED for log in logs)

    def test_get_logs_filtered_by_user(self, temp_audit_file):
        """Test retrieving logs filtered by user ID."""
        logger = AuditLogger(audit_file=temp_audit_file)

        logger.log_publication("sub-1", "user-1", {})
        logger.log_publication("sub-2", "user-2", {})
        logger.log_publication("sub-3", "user-1", {})

        logs = logger.get_logs(user_id="user-1")

        assert len(logs) == 2
        assert all(log.user_id == "user-1" for log in logs)

    def test_get_logs_with_limit(self, temp_audit_file):
        """Test retrieving logs with limit."""
        logger = AuditLogger(audit_file=temp_audit_file)

        for i in range(10):
            logger.log_publication(f"sub-{i}", "user-1", {})

        logs = logger.get_logs(limit=5)

        assert len(logs) == 5
        # Should get newest 5
        assert logs[0].submission_id == "sub-9"
        assert logs[4].submission_id == "sub-5"

    def test_get_logs_empty_file(self, temp_audit_file):
        """Test retrieving logs from empty file."""
        logger = AuditLogger(audit_file=temp_audit_file)

        logs = logger.get_logs()

        assert len(logs) == 0

    def test_verify_integrity_empty_log(self, temp_audit_file):
        """Test verifying integrity of empty log."""
        logger = AuditLogger(audit_file=temp_audit_file)

        is_valid, errors = logger.verify_integrity()

        assert is_valid is True
        assert len(errors) == 0

    def test_verify_integrity_valid_chain(self, temp_audit_file):
        """Test verifying integrity of valid event chain."""
        logger = AuditLogger(audit_file=temp_audit_file)

        # Log multiple events to create chain
        logger.log_publication("sub-1", "user-1", {})
        logger.log_publication("sub-2", "user-2", {})
        logger.log_publication("sub-3", "user-3", {})

        is_valid, errors = logger.verify_integrity()

        assert is_valid is True
        assert len(errors) == 0

    def test_verify_integrity_detects_tampering(self, temp_audit_file):
        """Test that integrity check detects tampering."""
        logger = AuditLogger(audit_file=temp_audit_file)

        # Log events
        logger.log_publication("sub-1", "user-1", {})
        logger.log_publication("sub-2", "user-2", {})

        # Tamper with log file
        with open(temp_audit_file, "r") as f:
            lines = f.readlines()

        # Modify first event
        first_event = json.loads(lines[0])
        first_event["user_id"] = "hacker"
        lines[0] = json.dumps(first_event) + "\n"

        with open(temp_audit_file, "w") as f:
            f.writelines(lines)

        # Verify should detect tampering
        is_valid, errors = logger.verify_integrity()

        assert is_valid is False
        assert len(errors) > 0

    def test_get_stats(self, temp_audit_file):
        """Test getting audit log statistics."""
        logger = AuditLogger(audit_file=temp_audit_file)

        # Log various events
        logger.log_publication("sub-1", "user-1", {})
        logger.log_publication("sub-2", "user-2", {})
        logger.log_bundle_signing("sub-1", "user-1", "/path", "key-1")
        logger.log_status_update("sub-1", "user-1", "pending", "approved")

        stats = logger.get_stats()

        assert stats["total"] == 4
        assert stats["publication_submitted"] == 2
        assert stats["bundle_signed"] == 1
        assert stats["publication_approved"] == 1

    def test_get_stats_empty_log(self, temp_audit_file):
        """Test getting stats from empty log."""
        logger = AuditLogger(audit_file=temp_audit_file)

        stats = logger.get_stats()

        assert stats["total"] == 0
        assert all(count == 0 for key, count in stats.items() if key != "total")

    def test_event_chaining(self, temp_audit_file):
        """Test that events are properly chained with previous_hash."""
        logger = AuditLogger(audit_file=temp_audit_file)

        # Log multiple events
        logger.log_publication("sub-1", "user-1", {})
        logger.log_publication("sub-2", "user-2", {})
        logger.log_publication("sub-3", "user-3", {})

        # Read logs
        with open(temp_audit_file, "r") as f:
            lines = f.readlines()

        event1 = json.loads(lines[0])
        event2 = json.loads(lines[1])
        event3 = json.loads(lines[2])

        # First event should have no previous_hash
        assert event1["previous_hash"] is None or event1["previous_hash"] == ""

        # Second event should reference first event's hash
        assert event2["previous_hash"] == event1["event_hash"]

        # Third event should reference second event's hash
        assert event3["previous_hash"] == event2["event_hash"]

    def test_append_only_behavior(self, temp_audit_file):
        """Test that logger only appends (doesn't modify existing entries)."""
        logger = AuditLogger(audit_file=temp_audit_file)

        # Log first event
        logger.log_publication("sub-1", "user-1", {})

        # Read current content
        with open(temp_audit_file, "r") as f:
            content1 = f.read()

        # Log second event
        logger.log_publication("sub-2", "user-2", {})

        # Read new content
        with open(temp_audit_file, "r") as f:
            content2 = f.read()

        # First event content should be unchanged
        assert content2.startswith(content1)
        assert len(content2) > len(content1)
