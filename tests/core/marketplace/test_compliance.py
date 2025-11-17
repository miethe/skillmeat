"""Tests for compliance module."""

import pytest
from datetime import datetime, timedelta

from skillmeat.core.marketplace.compliance import (
    ComplianceItem,
    ComplianceItemType,
    ComplianceChecklist,
    ConsentLog,
    ComplianceReport,
    ComplianceManager,
)


class TestComplianceItem:
    """Tests for ComplianceItem model."""

    def test_create_compliance_item(self):
        """Test creating a compliance item."""
        item = ComplianceItem(
            id="test-1",
            text="Test item",
            item_type=ComplianceItemType.LEGAL_RIGHTS,
            required=True,
            acknowledged=False,
        )

        assert item.id == "test-1"
        assert item.text == "Test item"
        assert item.item_type == ComplianceItemType.LEGAL_RIGHTS
        assert item.required is True
        assert item.acknowledged is False

    def test_compliance_item_with_notes(self):
        """Test compliance item with notes."""
        item = ComplianceItem(
            id="test-2",
            text="Test item",
            item_type=ComplianceItemType.LICENSE_COMPLIANCE,
            required=True,
            acknowledged=True,
            notes="Additional context",
        )

        assert item.notes == "Additional context"


class TestComplianceChecklist:
    """Tests for ComplianceChecklist model."""

    def test_create_checklist(self):
        """Test creating a compliance checklist."""
        items = [
            ComplianceItem(
                id="item-1",
                text="Item 1",
                item_type=ComplianceItemType.LEGAL_RIGHTS,
                required=True,
            ),
            ComplianceItem(
                id="item-2",
                text="Item 2",
                item_type=ComplianceItemType.LICENSE_COMPLIANCE,
                required=True,
            ),
        ]

        checklist = ComplianceChecklist(
            version="1.0.0",
            items=items,
            agreement_version="1.0.0",
        )

        assert checklist.version == "1.0.0"
        assert len(checklist.items) == 2
        assert checklist.acknowledged_at is None
        assert checklist.acknowledged_by is None

    def test_is_complete_false_when_unacknowledged(self):
        """Test that checklist is incomplete when items are unacknowledged."""
        items = [
            ComplianceItem(
                id="item-1",
                text="Item 1",
                item_type=ComplianceItemType.LEGAL_RIGHTS,
                required=True,
                acknowledged=False,
            )
        ]

        checklist = ComplianceChecklist(
            version="1.0.0",
            items=items,
            agreement_version="1.0.0",
        )

        assert checklist.is_complete() is False

    def test_is_complete_true_when_all_acknowledged(self):
        """Test that checklist is complete when all required items acknowledged."""
        items = [
            ComplianceItem(
                id="item-1",
                text="Item 1",
                item_type=ComplianceItemType.LEGAL_RIGHTS,
                required=True,
                acknowledged=True,
            ),
            ComplianceItem(
                id="item-2",
                text="Item 2",
                item_type=ComplianceItemType.LICENSE_COMPLIANCE,
                required=True,
                acknowledged=True,
            ),
        ]

        checklist = ComplianceChecklist(
            version="1.0.0",
            items=items,
            agreement_version="1.0.0",
        )

        assert checklist.is_complete() is True

    def test_is_complete_ignores_optional_items(self):
        """Test that optional items don't affect completion status."""
        items = [
            ComplianceItem(
                id="item-1",
                text="Required item",
                item_type=ComplianceItemType.LEGAL_RIGHTS,
                required=True,
                acknowledged=True,
            ),
            ComplianceItem(
                id="item-2",
                text="Optional item",
                item_type=ComplianceItemType.LICENSE_COMPLIANCE,
                required=False,
                acknowledged=False,
            ),
        ]

        checklist = ComplianceChecklist(
            version="1.0.0",
            items=items,
            agreement_version="1.0.0",
        )

        assert checklist.is_complete() is True

    def test_get_unacknowledged_items(self):
        """Test getting list of unacknowledged items."""
        items = [
            ComplianceItem(
                id="item-1",
                text="Item 1",
                item_type=ComplianceItemType.LEGAL_RIGHTS,
                required=True,
                acknowledged=True,
            ),
            ComplianceItem(
                id="item-2",
                text="Item 2",
                item_type=ComplianceItemType.LICENSE_COMPLIANCE,
                required=True,
                acknowledged=False,
            ),
            ComplianceItem(
                id="item-3",
                text="Item 3",
                item_type=ComplianceItemType.TERMS_OF_SERVICE,
                required=True,
                acknowledged=False,
            ),
        ]

        checklist = ComplianceChecklist(
            version="1.0.0",
            items=items,
            agreement_version="1.0.0",
        )

        unacknowledged = checklist.get_unacknowledged_items()
        assert len(unacknowledged) == 2
        assert unacknowledged[0].id == "item-2"
        assert unacknowledged[1].id == "item-3"

    def test_acknowledge_all(self):
        """Test acknowledging all items in checklist."""
        items = [
            ComplianceItem(
                id="item-1",
                text="Item 1",
                item_type=ComplianceItemType.LEGAL_RIGHTS,
                required=True,
                acknowledged=False,
            ),
            ComplianceItem(
                id="item-2",
                text="Item 2",
                item_type=ComplianceItemType.LICENSE_COMPLIANCE,
                required=True,
                acknowledged=False,
            ),
        ]

        checklist = ComplianceChecklist(
            version="1.0.0",
            items=items,
            agreement_version="1.0.0",
        )

        checklist.acknowledge_all(user_id="test-user", ip_address="127.0.0.1")

        assert all(item.acknowledged for item in checklist.items)
        assert checklist.acknowledged_by == "test-user"
        assert checklist.ip_address == "127.0.0.1"
        assert checklist.acknowledged_at is not None
        assert isinstance(checklist.acknowledged_at, datetime)


class TestConsentLog:
    """Tests for ConsentLog model."""

    def test_create_consent_log(self):
        """Test creating a consent log."""
        consent = ConsentLog.create_with_hash(
            consent_id="consent-123",
            submission_id="sub-123",
            user_id="test-user",
            checklist_version="1.0.0",
            items_acknowledged=["item-1", "item-2"],
            timestamp=datetime.utcnow(),
            agreement_version="1.0.0",
        )

        assert consent.consent_id == "consent-123"
        assert consent.submission_id == "sub-123"
        assert consent.user_id == "test-user"
        assert consent.checklist_version == "1.0.0"
        assert len(consent.items_acknowledged) == 2
        assert consent.agreement_version == "1.0.0"
        assert consent.consent_hash != ""
        assert len(consent.consent_hash) == 64  # SHA256 hex digest length

    def test_verify_hash_valid(self):
        """Test verifying a valid consent hash."""
        consent = ConsentLog.create_with_hash(
            consent_id="consent-123",
            submission_id="sub-123",
            user_id="test-user",
            checklist_version="1.0.0",
            items_acknowledged=["item-1", "item-2"],
            timestamp=datetime.utcnow(),
            agreement_version="1.0.0",
        )

        assert consent.verify_hash() is True

    def test_verify_hash_invalid(self):
        """Test detecting tampered consent hash."""
        consent = ConsentLog.create_with_hash(
            consent_id="consent-123",
            submission_id="sub-123",
            user_id="test-user",
            checklist_version="1.0.0",
            items_acknowledged=["item-1", "item-2"],
            timestamp=datetime.utcnow(),
            agreement_version="1.0.0",
        )

        # Tamper with data
        consent.user_id = "hacker"

        assert consent.verify_hash() is False

    def test_consent_log_with_optional_fields(self):
        """Test consent log with optional fields."""
        consent = ConsentLog.create_with_hash(
            consent_id="consent-123",
            submission_id="sub-123",
            user_id="test-user",
            checklist_version="1.0.0",
            items_acknowledged=["item-1"],
            timestamp=datetime.utcnow(),
            agreement_version="1.0.0",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        assert consent.ip_address == "192.168.1.1"
        assert consent.user_agent == "Mozilla/5.0"


class TestComplianceReport:
    """Tests for ComplianceReport model."""

    def test_create_compliance_report(self):
        """Test creating a compliance report."""
        report = ComplianceReport(
            bundle_path="/path/to/bundle.zip",
            scan_timestamp=datetime.utcnow(),
            licenses_found=["MIT", "Apache-2.0"],
            license_counts={"MIT": 3, "Apache-2.0": 2},
            pass_status=True,
        )

        assert report.bundle_path == "/path/to/bundle.zip"
        assert len(report.licenses_found) == 2
        assert report.license_counts["MIT"] == 3
        assert report.pass_status is True

    def test_has_critical_issues_false_when_passing(self):
        """Test that passing report has no critical issues."""
        report = ComplianceReport(
            bundle_path="/path/to/bundle.zip",
            scan_timestamp=datetime.utcnow(),
            licenses_found=["MIT"],
            license_counts={"MIT": 1},
            pass_status=True,
        )

        assert report.has_critical_issues() is False

    def test_has_critical_issues_true_when_conflicts(self):
        """Test that report with conflicts has critical issues."""
        report = ComplianceReport(
            bundle_path="/path/to/bundle.zip",
            scan_timestamp=datetime.utcnow(),
            licenses_found=["MIT", "GPL-3.0"],
            license_counts={"MIT": 1, "GPL-3.0": 1},
            conflicts=["MIT <-> GPL-3.0"],
            pass_status=True,  # Has conflicts even if pass_status is True
        )

        assert report.has_critical_issues() is True

    def test_has_critical_issues_true_when_failing(self):
        """Test that failing report has critical issues."""
        report = ComplianceReport(
            bundle_path="/path/to/bundle.zip",
            scan_timestamp=datetime.utcnow(),
            licenses_found=[],
            license_counts={},
            pass_status=False,
        )

        assert report.has_critical_issues() is True

    def test_get_summary(self):
        """Test generating report summary."""
        report = ComplianceReport(
            bundle_path="/path/to/bundle.zip",
            scan_timestamp=datetime.utcnow(),
            licenses_found=["MIT", "Apache-2.0"],
            license_counts={"MIT": 3, "Apache-2.0": 2},
            warnings=["Warning 1", "Warning 2"],
            recommendations=["Recommendation 1"],
            pass_status=True,
        )

        summary = report.get_summary()

        assert "bundle.zip" in summary
        assert "MIT: 3 artifact(s)" in summary
        assert "Apache-2.0: 2 artifact(s)" in summary
        assert "Status: PASS" in summary
        assert "Warning 1" in summary
        assert "Recommendation 1" in summary


class TestComplianceManager:
    """Tests for ComplianceManager."""

    def test_get_checklist_v1(self):
        """Test getting v1.0.0 checklist."""
        manager = ComplianceManager()
        checklist = manager.get_checklist(version="1.0.0", agreement_version="1.0.0")

        assert checklist.version == "1.0.0"
        assert checklist.agreement_version == "1.0.0"
        assert len(checklist.items) == 8  # Standard v1 has 8 items
        assert all(not item.acknowledged for item in checklist.items)

    def test_get_checklist_default_version(self):
        """Test getting checklist with default version."""
        manager = ComplianceManager()
        checklist = manager.get_checklist()

        assert checklist.version == "1.0.0"
        assert len(checklist.items) > 0

    def test_get_checklist_unknown_version(self):
        """Test getting checklist with unknown version fails."""
        manager = ComplianceManager()

        with pytest.raises(ValueError, match="Unknown checklist version"):
            manager.get_checklist(version="999.0.0")

    def test_validate_consent_complete(self):
        """Test validating complete checklist."""
        manager = ComplianceManager()
        checklist = manager.get_checklist()

        # Acknowledge all items
        checklist.acknowledge_all(user_id="test-user")

        assert manager.validate_consent(checklist) is True

    def test_validate_consent_incomplete(self):
        """Test validating incomplete checklist."""
        manager = ComplianceManager()
        checklist = manager.get_checklist()

        # Don't acknowledge items

        assert manager.validate_consent(checklist) is False

    def test_create_consent_log(self):
        """Test creating consent log from checklist."""
        manager = ComplianceManager()
        checklist = manager.get_checklist()
        checklist.acknowledge_all(user_id="test-user")

        consent_log = manager.create_consent_log(
            submission_id="sub-123",
            checklist=checklist,
            user_id="test-user",
            ip_address="127.0.0.1",
        )

        assert consent_log.submission_id == "sub-123"
        assert consent_log.user_id == "test-user"
        assert consent_log.ip_address == "127.0.0.1"
        assert consent_log.checklist_version == checklist.version
        assert consent_log.agreement_version == checklist.agreement_version
        assert len(consent_log.items_acknowledged) == len(checklist.items)
        assert consent_log.consent_hash != ""
        assert consent_log.verify_hash() is True

    def test_create_consent_log_incomplete_fails(self):
        """Test that creating consent log with incomplete checklist fails."""
        manager = ComplianceManager()
        checklist = manager.get_checklist()

        # Don't acknowledge items

        with pytest.raises(ValueError, match="Checklist is incomplete"):
            manager.create_consent_log(
                submission_id="sub-123",
                checklist=checklist,
                user_id="test-user",
            )

    def test_get_available_versions(self):
        """Test getting available checklist versions."""
        manager = ComplianceManager()
        versions = manager.get_available_versions()

        assert isinstance(versions, list)
        assert "1.0.0" in versions

    def test_generate_consent_id(self):
        """Test generating consent ID."""
        manager = ComplianceManager()
        consent_id = manager._generate_consent_id("sub-123")

        assert consent_id.startswith("consent-sub-123-")
        assert len(consent_id) > len("consent-sub-123-")

    def test_checklist_items_are_independent(self):
        """Test that checklist items are independent (not shared references)."""
        manager = ComplianceManager()

        checklist1 = manager.get_checklist()
        checklist2 = manager.get_checklist()

        # Modify checklist1
        checklist1.items[0].acknowledged = True

        # checklist2 should not be affected
        assert checklist2.items[0].acknowledged is False

    def test_all_compliance_item_types_covered(self):
        """Test that standard checklist covers all compliance item types."""
        manager = ComplianceManager()
        checklist = manager.get_checklist()

        item_types = {item.item_type for item in checklist.items}

        # Should have most major types
        assert ComplianceItemType.LEGAL_RIGHTS in item_types
        assert ComplianceItemType.LICENSE_COMPLIANCE in item_types
        assert ComplianceItemType.TERMS_OF_SERVICE in item_types
        assert ComplianceItemType.INTELLECTUAL_PROPERTY in item_types
