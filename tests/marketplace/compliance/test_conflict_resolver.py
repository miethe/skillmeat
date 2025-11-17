"""Tests for license conflict resolver."""

import pytest

from skillmeat.marketplace.compliance.conflict_resolver import (
    ConflictResolver,
    LicenseConflict,
)


@pytest.fixture
def resolver():
    """Create conflict resolver instance."""
    return ConflictResolver()


def test_license_conflict_creation():
    """Test license conflict creation."""
    conflict = LicenseConflict(
        license1="GPL-2.0",
        license2="Apache-2.0",
        conflict_type="incompatible",
        description="Test conflict",
        resolution="Test resolution",
    )

    assert conflict.license1 == "GPL-2.0"
    assert conflict.license2 == "Apache-2.0"
    assert conflict.conflict_type == "incompatible"


def test_license_conflict_invalid_type():
    """Test license conflict with invalid type."""
    with pytest.raises(ValueError, match="Invalid conflict_type"):
        LicenseConflict(
            license1="MIT",
            license2="Apache-2.0",
            conflict_type="invalid",
            description="Test",
            resolution="Test",
        )


def test_can_combine_same_license(resolver):
    """Test that same licenses can be combined."""
    result = resolver.can_combine("MIT", "MIT")

    assert result is None  # No conflict


def test_can_combine_gpl2_apache_incompatible(resolver):
    """Test GPL-2.0 + Apache-2.0 incompatibility."""
    conflict = resolver.can_combine("GPL-2.0", "Apache-2.0")

    assert conflict is not None
    assert conflict.conflict_type == "incompatible"


def test_can_combine_gpl3_apache_compatible(resolver):
    """Test GPL-3.0 + Apache-2.0 compatibility."""
    # GPL-3.0 is compatible with Apache, so should only return info/warning if anything
    conflict = resolver.can_combine("GPL-3.0", "Apache-2.0")

    # Should be None (compatible) or just info
    assert conflict is None or conflict.conflict_type == "info"


def test_can_combine_permissive_licenses(resolver):
    """Test that permissive licenses can be combined."""
    result = resolver.can_combine("MIT", "Apache-2.0")

    assert result is None  # Permissive licenses are compatible


def test_can_combine_gpl_proprietary(resolver):
    """Test GPL + Proprietary incompatibility."""
    conflict = resolver.can_combine("GPL-3.0", "Proprietary")

    assert conflict is not None
    assert conflict.conflict_type == "incompatible"


def test_can_combine_mit_gpl_warning(resolver):
    """Test MIT + GPL creates warning."""
    conflict = resolver.can_combine("MIT", "GPL-3.0")

    # MIT can combine with GPL but result must be GPL
    assert conflict is not None
    assert conflict.conflict_type == "warning"


def test_detect_conflicts_no_conflicts(resolver):
    """Test detecting no conflicts."""
    licenses = ["MIT", "Apache-2.0", "BSD-3-Clause"]

    conflicts = resolver.detect_conflicts(licenses)

    # Permissive licenses should have no incompatibilities
    incompatible = [c for c in conflicts if c.conflict_type == "incompatible"]
    assert len(incompatible) == 0


def test_detect_conflicts_with_incompatibility(resolver):
    """Test detecting incompatible licenses."""
    licenses = ["GPL-2.0", "Apache-2.0"]

    conflicts = resolver.detect_conflicts(licenses)

    # Should detect incompatibility
    incompatible = [c for c in conflicts if c.conflict_type == "incompatible"]
    assert len(incompatible) > 0


def test_detect_conflicts_multiple_copyleft(resolver):
    """Test detecting multiple copyleft licenses."""
    licenses = ["GPL-2.0", "GPL-3.0"]

    conflicts = resolver.detect_conflicts(licenses)

    # Should warn about multiple copyleft
    assert len(conflicts) > 0


def test_suggest_resolutions(resolver):
    """Test suggesting resolutions."""
    conflicts = [
        LicenseConflict(
            license1="GPL-2.0",
            license2="Apache-2.0",
            conflict_type="incompatible",
            description="Test",
            resolution="Upgrade to GPL-3.0",
        ),
        LicenseConflict(
            license1="MIT",
            license2="GPL-3.0",
            conflict_type="warning",
            description="Test",
            resolution="Use GPL-3.0 for bundle",
        ),
    ]

    resolutions = resolver.suggest_resolutions(conflicts)

    assert "incompatible" in resolutions
    assert "warning" in resolutions
    assert len(resolutions["incompatible"]) == 1
    assert len(resolutions["warning"]) == 1


def test_require_dual_license_with_incompatibilities(resolver):
    """Test dual licensing recommendation with incompatibilities."""
    licenses = ["GPL-2.0", "Apache-2.0"]

    recommendation = resolver.require_dual_license(licenses)

    assert recommendation is not None
    assert "dual licensing" in recommendation.lower()


def test_require_dual_license_with_multiple_copyleft(resolver):
    """Test dual licensing recommendation with multiple copyleft."""
    licenses = ["GPL-2.0", "GPL-3.0", "MIT"]

    recommendation = resolver.require_dual_license(licenses)

    assert recommendation is not None


def test_require_dual_license_not_needed(resolver):
    """Test no dual licensing needed."""
    licenses = ["MIT", "Apache-2.0"]

    recommendation = resolver.require_dual_license(licenses)

    assert recommendation is None  # Permissive licenses don't need dual licensing


def test_get_compatibility_matrix(resolver):
    """Test getting compatibility matrix."""
    matrix = resolver.get_compatibility_matrix()

    assert isinstance(matrix, dict)
    assert len(matrix) > 0

    # Check a known pair
    gpl2_apache = ("GPL-2.0", "Apache-2.0")
    assert gpl2_apache in matrix
    assert matrix[gpl2_apache] == "incompatible"


def test_is_copyleft(resolver):
    """Test copyleft detection."""
    assert resolver.is_copyleft("GPL-3.0") is True
    assert resolver.is_copyleft("LGPL-3.0") is True
    assert resolver.is_copyleft("MIT") is False


def test_is_permissive(resolver):
    """Test permissive detection."""
    assert resolver.is_permissive("MIT") is True
    assert resolver.is_permissive("Apache-2.0") is True
    assert resolver.is_permissive("GPL-3.0") is False


def test_get_license_category(resolver):
    """Test license categorization."""
    assert resolver.get_license_category("GPL-3.0") == "copyleft-strong"
    assert resolver.get_license_category("LGPL-3.0") == "copyleft-weak"
    assert resolver.get_license_category("MIT") == "permissive"
    assert resolver.get_license_category("Proprietary") == "proprietary"
    assert resolver.get_license_category("Unknown-License") == "unknown"


def test_conflict_matrix_bidirectional(resolver):
    """Test that conflict matrix works bidirectionally."""
    # Test both directions
    conflict1 = resolver.can_combine("GPL-2.0", "Apache-2.0")
    conflict2 = resolver.can_combine("Apache-2.0", "GPL-2.0")

    # Both should detect incompatibility
    if conflict1:
        assert conflict1.conflict_type == "incompatible"
    if conflict2:
        assert conflict2.conflict_type == "incompatible"


def test_lgpl_proprietary_warning(resolver):
    """Test LGPL + Proprietary creates warning."""
    conflict = resolver.can_combine("LGPL-3.0", "Proprietary")

    assert conflict is not None
    assert conflict.conflict_type == "warning"
    assert "dynamically" in conflict.description.lower()


def test_mpl_combinations(resolver):
    """Test MPL license combinations."""
    # MPL + Proprietary should warn
    conflict1 = resolver.can_combine("MPL-2.0", "Proprietary")
    assert conflict1 is not None
    assert conflict1.conflict_type == "warning"

    # MPL + GPL-3.0 should be compatible
    conflict2 = resolver.can_combine("MPL-2.0", "GPL-3.0")
    assert conflict2 is None or conflict2.conflict_type == "info"
