"""Tests for legal compliance checklist."""

import pytest

from skillmeat.marketplace.compliance.legal_checklist import (
    ComplianceChecklist,
    ComplianceChecklistGenerator,
    ComplianceItem,
)


@pytest.fixture
def generator():
    """Create checklist generator instance."""
    return ComplianceChecklistGenerator()


def test_compliance_item_creation():
    """Test compliance item creation."""
    item = ComplianceItem(
        id="test_item",
        question="Test question?",
        required=True,
        category="license",
        help_text="Test help text",
    )

    assert item.id == "test_item"
    assert item.question == "Test question?"
    assert item.required is True
    assert item.category == "license"
    assert item.help_text == "Test help text"


def test_compliance_item_invalid_category():
    """Test compliance item with invalid category."""
    with pytest.raises(ValueError, match="Invalid category"):
        ComplianceItem(
            id="test",
            question="Test?",
            required=True,
            category="invalid",
        )


def test_generate_mit_checklist(generator):
    """Test generating checklist for MIT license."""
    checklist = generator.create_checklist(
        bundle_id="test-bundle",
        license="MIT",
    )

    assert isinstance(checklist, ComplianceChecklist)
    assert checklist.bundle_id == "test-bundle"
    assert checklist.license == "MIT"
    assert len(checklist.items) > 0

    # MIT should have base items + permissive items
    assert any(item.id == "files_licensed" for item in checklist.items)
    assert any(item.id == "license_preserved" for item in checklist.items)


def test_generate_gpl_checklist(generator):
    """Test generating checklist for GPL license."""
    checklist = generator.create_checklist(
        bundle_id="test-bundle",
        license="GPL-3.0",
    )

    # GPL should have base items + GPL-specific items
    assert any(item.id == "source_included" for item in checklist.items)
    assert any(item.id == "modifications_marked" for item in checklist.items)
    assert any(item.id == "same_license" for item in checklist.items)


def test_generate_apache_checklist(generator):
    """Test generating checklist for Apache-2.0."""
    checklist = generator.create_checklist(
        bundle_id="test-bundle",
        license="Apache-2.0",
    )

    # Apache should have base items + permissive items + Apache-specific
    assert any(item.id == "notice_file" for item in checklist.items)
    assert any(item.id == "patent_grant" for item in checklist.items)


def test_generate_proprietary_checklist(generator):
    """Test generating checklist for proprietary license."""
    checklist = generator.create_checklist(
        bundle_id="test-bundle",
        license="Proprietary",
    )

    # Proprietary should have base items + proprietary-specific
    assert any(item.id == "permission_granted" for item in checklist.items)
    assert any(item.id == "commercial_allowed" for item in checklist.items)


def test_checklist_is_complete_empty():
    """Test is_complete on empty checklist."""
    checklist = ComplianceChecklist(
        checklist_id="test",
        bundle_id="test-bundle",
        license="MIT",
        items=[],
    )

    assert checklist.is_complete is True  # No required items


def test_checklist_is_complete_with_items():
    """Test is_complete with required items."""
    items = [
        ComplianceItem(id="req1", question="Required?", required=True, category="license"),
        ComplianceItem(id="opt1", question="Optional?", required=False, category="license"),
    ]

    checklist = ComplianceChecklist(
        checklist_id="test",
        bundle_id="test-bundle",
        license="MIT",
        items=items,
    )

    assert checklist.is_complete is False  # Required item not completed

    checklist.completed_items.append("req1")
    assert checklist.is_complete is True  # Required item completed


def test_checklist_completion_percentage():
    """Test completion percentage calculation."""
    items = [
        ComplianceItem(id="req1", question="Req 1?", required=True, category="license"),
        ComplianceItem(id="req2", question="Req 2?", required=True, category="license"),
        ComplianceItem(id="opt1", question="Opt?", required=False, category="license"),
    ]

    checklist = ComplianceChecklist(
        checklist_id="test",
        bundle_id="test-bundle",
        license="MIT",
        items=items,
    )

    assert checklist.completion_percentage == 0.0

    checklist.completed_items.append("req1")
    assert checklist.completion_percentage == 50.0

    checklist.completed_items.append("req2")
    assert checklist.completion_percentage == 100.0


def test_checklist_incomplete_required_items():
    """Test getting incomplete required items."""
    items = [
        ComplianceItem(id="req1", question="Req 1?", required=True, category="license"),
        ComplianceItem(id="req2", question="Req 2?", required=True, category="license"),
    ]

    checklist = ComplianceChecklist(
        checklist_id="test",
        bundle_id="test-bundle",
        license="MIT",
        items=items,
        completed_items=["req1"],
    )

    incomplete = checklist.incomplete_required_items

    assert len(incomplete) == 1
    assert incomplete[0].id == "req2"


def test_checklist_mark_complete(generator):
    """Test marking item as complete."""
    checklist = generator.create_checklist(
        bundle_id="test-bundle",
        license="MIT",
    )

    item_id = checklist.items[0].id

    checklist.mark_complete(item_id, consented=True)

    assert item_id in checklist.completed_items
    assert checklist.consents[item_id] is True


def test_checklist_mark_complete_invalid_id(generator):
    """Test marking invalid item as complete."""
    checklist = generator.create_checklist(
        bundle_id="test-bundle",
        license="MIT",
    )

    with pytest.raises(ValueError, match="Item ID not found"):
        checklist.mark_complete("invalid_id")


def test_validate_checklist_incomplete(generator):
    """Test validating incomplete checklist."""
    checklist = generator.create_checklist(
        bundle_id="test-bundle",
        license="MIT",
    )

    errors = generator.validate_checklist(checklist)

    assert len(errors) > 0  # Should have errors for incomplete items


def test_validate_checklist_complete(generator):
    """Test validating complete checklist."""
    checklist = generator.create_checklist(
        bundle_id="test-bundle",
        license="MIT",
    )

    # Complete all required items
    for item in checklist.items:
        if item.required:
            checklist.mark_complete(item.id, consented=True)

    errors = generator.validate_checklist(checklist)

    assert len(errors) == 0  # Should have no errors


def test_validate_checklist_missing_consent(generator):
    """Test validating checklist with missing consent."""
    checklist = generator.create_checklist(
        bundle_id="test-bundle",
        license="MIT",
    )

    # Mark as completed but don't consent
    item = next(i for i in checklist.items if i.required)
    checklist.completed_items.append(item.id)
    # Don't add to consents dict

    errors = generator.validate_checklist(checklist)

    assert len(errors) > 0
    assert any("Missing consent" in error for error in errors)


def test_validate_checklist_proprietary_signature(generator):
    """Test proprietary license requires signature."""
    checklist = generator.create_checklist(
        bundle_id="test-bundle",
        license="Proprietary",
    )

    # Complete all items
    for item in checklist.items:
        if item.required:
            checklist.mark_complete(item.id, consented=True)

    # Without signature
    errors = generator.validate_checklist(checklist)
    assert any("signature required" in error.lower() for error in errors)

    # With signature
    checklist.publisher_signature = "test-signature"
    errors = generator.validate_checklist(checklist)
    # Should still have signature error removed
    assert not any("signature required" in error.lower() for error in errors)


def test_get_required_items_mit(generator):
    """Test getting required items for MIT."""
    items = generator.get_required_items("MIT")

    assert len(items) > 0
    assert all(item.required for item in items)


def test_checklist_to_dict(generator):
    """Test converting checklist to dict."""
    checklist = generator.create_checklist(
        bundle_id="test-bundle",
        license="MIT",
    )

    data = checklist.to_dict()

    assert data["checklist_id"] == checklist.checklist_id
    assert data["bundle_id"] == "test-bundle"
    assert data["license"] == "MIT"
    assert "items" in data
    assert "is_complete" in data
    assert "completion_percentage" in data


def test_license_categorization(generator):
    """Test license categorization methods."""
    assert generator._is_gpl_license("GPL-3.0") is True
    assert generator._is_gpl_license("MIT") is False

    assert generator._is_permissive_license("MIT") is True
    assert generator._is_permissive_license("GPL-3.0") is False

    assert generator._is_proprietary_license("Proprietary") is True
    assert generator._is_proprietary_license("MIT") is False
