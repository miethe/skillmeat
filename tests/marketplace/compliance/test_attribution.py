"""Tests for attribution tracker."""

import zipfile
from pathlib import Path

import pytest

from skillmeat.marketplace.compliance.attribution import (
    AttributionRequirement,
    AttributionTracker,
)


@pytest.fixture
def tracker():
    """Create attribution tracker instance."""
    return AttributionTracker()


@pytest.fixture
def test_bundle(tmp_path):
    """Create test bundle with attribution requirements."""
    bundle_path = tmp_path / "test-bundle.zip"

    with zipfile.ZipFile(bundle_path, "w") as zf:
        # CREDITS file
        zf.writestr(
            "CREDITS.md",
            "# Credits and Attributions\n\n"
            "## Component A\n\n"
            "- **License**: MIT\n"
            "- **Copyright**: Copyright (c) 2024 Author A\n\n"
            "## Component B\n\n"
            "- **License**: Apache-2.0\n"
            "- **Copyright**: Copyright (c) 2024 Author B\n",
        )

        # NOTICE file
        zf.writestr(
            "NOTICE",
            "Test Bundle\n\n"
            "Apache-Licensed Components:\n\n"
            "- Component B: Copyright (c) 2024 Author B\n",
        )

    return bundle_path


def test_attribution_requirement_creation():
    """Test attribution requirement creation."""
    req = AttributionRequirement(
        component_name="test-component",
        license="MIT",
        copyright_notices=["Copyright (c) 2024 Test Author"],
        source_url="https://github.com/test/component",
    )

    assert req.component_name == "test-component"
    assert req.license == "MIT"
    assert len(req.copyright_notices) == 1


def test_attribution_requirement_validation():
    """Test attribution requirement validation."""
    with pytest.raises(ValueError, match="component_name cannot be empty"):
        AttributionRequirement(
            component_name="",
            license="MIT",
        )

    with pytest.raises(ValueError, match="license cannot be empty"):
        AttributionRequirement(
            component_name="test",
            license="",
        )


def test_extract_attributions_from_credits(tracker, test_bundle):
    """Test extracting attributions from CREDITS file."""
    attributions = tracker.extract_attributions(test_bundle)

    assert len(attributions) >= 2

    # Check for Component A
    comp_a = next((a for a in attributions if a.component_name == "Component A"), None)
    assert comp_a is not None
    assert comp_a.license == "MIT"
    assert len(comp_a.copyright_notices) > 0


def test_extract_attributions_from_notice(tracker, test_bundle):
    """Test extracting attributions from NOTICE file."""
    attributions = tracker.extract_attributions(test_bundle)

    # Check for Component B (from NOTICE)
    comp_b = next((a for a in attributions if a.component_name == "Component B"), None)
    assert comp_b is not None
    assert comp_b.license in ["Apache-2.0", "MIT"]  # Could be from either file


def test_generate_credits_empty(tracker):
    """Test generating credits with no attributions."""
    credits = tracker.generate_credits([])

    assert "No third-party components" in credits


def test_generate_credits_with_attributions(tracker):
    """Test generating credits with attributions."""
    attributions = [
        AttributionRequirement(
            component_name="Component A",
            license="MIT",
            copyright_notices=["Copyright (c) 2024 Author A"],
            source_url="https://example.com/a",
        ),
        AttributionRequirement(
            component_name="Component B",
            license="Apache-2.0",
            copyright_notices=["Copyright (c) 2024 Author B"],
            modifications="Added feature X",
        ),
    ]

    credits = tracker.generate_credits(attributions)

    assert "# Credits and Attributions" in credits
    assert "Component A" in credits
    assert "Component B" in credits
    assert "MIT" in credits
    assert "Apache-2.0" in credits
    assert "https://example.com/a" in credits
    assert "Added feature X" in credits


def test_generate_credits_sorted(tracker):
    """Test that credits are sorted by component name."""
    attributions = [
        AttributionRequirement(component_name="Z-Component", license="MIT"),
        AttributionRequirement(component_name="A-Component", license="MIT"),
    ]

    credits = tracker.generate_credits(attributions)

    # A should come before Z
    a_pos = credits.index("A-Component")
    z_pos = credits.index("Z-Component")
    assert a_pos < z_pos


def test_generate_notice(tracker):
    """Test generating NOTICE file."""
    attributions = [
        AttributionRequirement(
            component_name="Component A",
            license="Apache-2.0",
            copyright_notices=["Copyright (c) 2024 Author A"],
        ),
        AttributionRequirement(
            component_name="Component B",
            license="MIT",
            copyright_notices=["Copyright (c) 2024 Author B"],
        ),
    ]

    notice = tracker.generate_notice(attributions, "Test Bundle")

    assert "Test Bundle" in notice
    assert "Apache-Licensed Components" in notice
    assert "Component A" in notice
    # Component B is MIT, should not be in Apache section


def test_validate_attributions_missing_credits(tracker, tmp_path):
    """Test validating bundle without CREDITS file."""
    bundle_path = tmp_path / "no-credits.zip"
    with zipfile.ZipFile(bundle_path, "w") as zf:
        zf.writestr("test.txt", "test")

    attributions = [
        AttributionRequirement(
            component_name="Component A",
            license="MIT",
            copyright_notices=["Copyright (c) 2024 Test"],
        ),
    ]

    errors = tracker.validate_attributions(bundle_path, attributions)

    assert len(errors) > 0
    assert any("CREDITS" in error for error in errors)


def test_validate_attributions_missing_notice(tracker, tmp_path):
    """Test validating Apache-licensed bundle without NOTICE."""
    bundle_path = tmp_path / "no-notice.zip"
    with zipfile.ZipFile(bundle_path, "w") as zf:
        zf.writestr("CREDITS.md", "test")

    attributions = [
        AttributionRequirement(
            component_name="Component A",
            license="Apache-2.0",
            copyright_notices=["Copyright (c) 2024 Test"],
        ),
    ]

    errors = tracker.validate_attributions(bundle_path, attributions)

    assert len(errors) > 0
    assert any("NOTICE" in error for error in errors)


def test_validate_attributions_missing_copyright(tracker, tmp_path):
    """Test validating attribution without copyright notices."""
    bundle_path = tmp_path / "test.zip"
    with zipfile.ZipFile(bundle_path, "w") as zf:
        zf.writestr("CREDITS.md", "test")

    attributions = [
        AttributionRequirement(
            component_name="Component A",
            license="MIT",
            copyright_notices=[],  # No copyright!
        ),
    ]

    errors = tracker.validate_attributions(bundle_path, attributions)

    assert len(errors) > 0
    assert any("copyright" in error.lower() for error in errors)


def test_format_notice(tracker):
    """Test format_notice (same as generate_notice)."""
    attributions = [
        AttributionRequirement(
            component_name="Component A",
            license="Apache-2.0",
            copyright_notices=["Copyright (c) 2024 Test"],
        ),
    ]

    notice = tracker.format_notice(attributions, "Test Bundle")

    assert "Test Bundle" in notice
    assert "Component A" in notice


def test_extract_component_name_from_path(tracker):
    """Test extracting component name from file path."""
    # Test with directory structure
    name1 = tracker._extract_component_name("vendor/component-a/src/main.py")
    assert name1 == "vendor"

    # Test with single file
    name2 = tracker._extract_component_name("main.py")
    assert name2 == "main"


def test_parse_credits_file_simple(tracker):
    """Test parsing simple CREDITS file."""
    content = """
# Credits

## Component A

- **License**: MIT
- **Copyright**: Copyright (c) 2024 Author A
"""

    attributions = {}
    tracker._parse_credits_file(content, attributions)

    assert "Component A" in attributions
    assert attributions["Component A"].license == "MIT"


def test_parse_notice_file(tracker):
    """Test parsing NOTICE file."""
    content = """
Test Bundle

Apache-Licensed Components:

- Component A: Copyright (c) 2024 Author A
- Component B: Copyright (c) 2024 Author B
"""

    attributions = {}
    tracker._parse_notice_file(content, attributions)

    # Should extract components from NOTICE
    assert len(attributions) >= 1


def test_attribution_required_licenses(tracker):
    """Test attribution required license detection."""
    assert "MIT" in tracker.ATTRIBUTION_REQUIRED
    assert "Apache-2.0" in tracker.ATTRIBUTION_REQUIRED
    assert "BSD-3-Clause" in tracker.ATTRIBUTION_REQUIRED
    assert "GPL-3.0" not in tracker.ATTRIBUTION_REQUIRED


def test_notice_required_licenses(tracker):
    """Test NOTICE file required license detection."""
    assert "Apache-2.0" in tracker.NOTICE_REQUIRED


def test_generate_credits_no_modifications(tracker):
    """Test credits generation without modifications."""
    attributions = [
        AttributionRequirement(
            component_name="Component A",
            license="MIT",
            copyright_notices=["Copyright (c) 2024 Test"],
        ),
    ]

    credits = tracker.generate_credits(attributions)

    assert "Modifications: None" in credits


def test_validate_attributions_valid(tracker, tmp_path):
    """Test validating valid attributions."""
    bundle_path = tmp_path / "valid.zip"
    with zipfile.ZipFile(bundle_path, "w") as zf:
        zf.writestr("CREDITS.md", "test")
        zf.writestr("NOTICE", "test")

    attributions = [
        AttributionRequirement(
            component_name="Component A",
            license="Apache-2.0",
            copyright_notices=["Copyright (c) 2024 Test"],
        ),
    ]

    errors = tracker.validate_attributions(bundle_path, attributions)

    # Should have no errors (CREDITS and NOTICE present, copyright exists)
    assert len(errors) == 0


def test_validate_attributions_invalid_bundle(tracker, tmp_path):
    """Test validating with invalid bundle path."""
    invalid_path = tmp_path / "not-a-bundle.txt"
    invalid_path.write_text("not a zip")

    errors = tracker.validate_attributions(invalid_path, [])

    assert len(errors) > 0
    assert any("not a valid ZIP" in error for error in errors)
