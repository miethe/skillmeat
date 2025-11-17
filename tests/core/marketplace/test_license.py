"""Tests for license validation."""

import pytest

from skillmeat.core.marketplace.license import (
    LicenseCompatibility,
    LicenseValidator,
)


@pytest.fixture
def validator():
    """Create license validator."""
    return LicenseValidator()


def test_osi_approved_licenses(validator):
    """Test OSI-approved licenses are recognized."""
    for license_id in ["MIT", "Apache-2.0", "BSD-3-Clause", "GPL-3.0"]:
        info = validator.get_license_info(license_id)
        assert info is not None
        assert info.is_osi_approved


def test_proprietary_licenses(validator):
    """Test proprietary licenses are recognized."""
    for license_id in ["Proprietary", "Commercial", "UNLICENSED"]:
        info = validator.get_license_info(license_id)
        assert info is not None
        assert not info.is_osi_approved
        assert not info.allows_redistribution


def test_validate_mit_license(validator):
    """Test MIT license validation."""
    result = validator.validate_license("MIT")

    assert result.is_valid
    assert result.compatibility == LicenseCompatibility.COMPATIBLE
    assert len(result.errors) == 0


def test_validate_gpl_license(validator):
    """Test GPL license validation."""
    result = validator.validate_license("GPL-3.0")

    assert result.is_valid
    assert result.compatibility == LicenseCompatibility.COMPATIBLE
    # Should have copyleft warning
    assert any("copyleft" in w.lower() for w in result.warnings)


def test_validate_proprietary_license(validator):
    """Test proprietary license validation."""
    result = validator.validate_license("Proprietary")

    assert result.compatibility == LicenseCompatibility.REQUIRES_REVIEW
    # Should have warnings about redistribution
    assert len(result.warnings) > 0


def test_validate_unknown_license(validator):
    """Test unknown license validation."""
    result = validator.validate_license("CustomLicense123")

    assert result.compatibility == LicenseCompatibility.UNKNOWN
    assert any("unknown" in w.lower() for w in result.warnings)


def test_validate_bundle_licenses_compatible(validator):
    """Test bundle with compatible licenses."""
    result = validator.validate_bundle_licenses(
        primary_license="MIT",
        artifact_licenses=["MIT", "Apache-2.0", "BSD-3-Clause"],
    )

    assert result.is_valid
    assert result.compatibility == LicenseCompatibility.COMPATIBLE
    assert len(result.conflicts) == 0


def test_validate_bundle_licenses_gpl_conflict(validator):
    """Test bundle with GPL-proprietary conflict."""
    result = validator.validate_bundle_licenses(
        primary_license="GPL-3.0",
        artifact_licenses=["MIT", "Proprietary"],
    )

    assert not result.is_valid
    assert result.compatibility == LicenseCompatibility.INCOMPATIBLE
    assert len(result.conflicts) > 0
    assert len(result.errors) > 0


def test_validate_bundle_licenses_gpl2_gpl3_conflict(validator):
    """Test bundle with GPL-2.0 and GPL-3.0 conflict."""
    result = validator.validate_bundle_licenses(
        primary_license="GPL-2.0",
        artifact_licenses=["GPL-3.0"],
    )

    assert not result.is_valid
    assert result.compatibility == LicenseCompatibility.INCOMPATIBLE


def test_validate_bundle_licenses_apache_gpl2_conflict(validator):
    """Test bundle with Apache-2.0 and GPL-2.0 conflict."""
    result = validator.validate_bundle_licenses(
        primary_license="Apache-2.0",
        artifact_licenses=["GPL-2.0"],
    )

    assert not result.is_valid
    assert result.compatibility == LicenseCompatibility.INCOMPATIBLE


def test_validate_bundle_licenses_permissive_mix(validator):
    """Test bundle with permissive licenses."""
    result = validator.validate_bundle_licenses(
        primary_license="MIT",
        artifact_licenses=["Apache-2.0", "BSD-2-Clause", "ISC"],
    )

    assert result.is_valid
    assert len(result.conflicts) == 0


def test_validate_bundle_licenses_lgpl_compatible(validator):
    """Test bundle with LGPL (weak copyleft)."""
    result = validator.validate_bundle_licenses(
        primary_license="LGPL-3.0",
        artifact_licenses=["MIT", "Apache-2.0"],
    )

    assert result.is_valid


def test_is_incompatible_gpl_proprietary(validator):
    """Test GPL-proprietary incompatibility detection."""
    assert validator._is_incompatible("GPL-3.0", "Proprietary")
    assert validator._is_incompatible("Proprietary", "GPL-3.0")


def test_is_incompatible_gpl_versions(validator):
    """Test GPL version incompatibility detection."""
    assert validator._is_incompatible("GPL-2.0", "GPL-3.0")
    assert validator._is_incompatible("GPL-2.0-only", "GPL-3.0")


def test_is_incompatible_permissive(validator):
    """Test permissive licenses are compatible."""
    assert not validator._is_incompatible("MIT", "Apache-2.0")
    assert not validator._is_incompatible("BSD-3-Clause", "ISC")


def test_matches_license_family(validator):
    """Test license family matching."""
    assert validator._matches_license_family("GPL-3.0", "GPL-3.0-only")
    assert validator._matches_license_family("GPL-3.0-only", "GPL-3.0-or-later")
    assert not validator._matches_license_family("GPL-2.0", "GPL-3.0")


def test_get_recommended_licenses(validator):
    """Test getting recommended licenses."""
    licenses = validator.get_recommended_licenses()

    assert len(licenses) > 0
    assert "MIT" in licenses
    assert "Apache-2.0" in licenses
    assert "GPL-3.0-or-later" in licenses


def test_explain_license_mit(validator):
    """Test explaining MIT license."""
    explanation = validator.explain_license("MIT")

    assert "MIT" in explanation
    assert "permissive" in explanation.lower()
    assert "OSI Approved" in explanation


def test_explain_license_gpl(validator):
    """Test explaining GPL license."""
    explanation = validator.explain_license("GPL-3.0")

    assert "GPL" in explanation
    assert "copyleft" in explanation.lower()
    assert "derivative works" in explanation.lower()


def test_explain_license_proprietary(validator):
    """Test explaining proprietary license."""
    explanation = validator.explain_license("Proprietary")

    assert "Proprietary" in explanation
    assert "Redistribution: Restricted" in explanation


def test_explain_license_unknown(validator):
    """Test explaining unknown license."""
    explanation = validator.explain_license("UnknownLicense")

    assert "Unknown license" in explanation


def test_case_insensitive_license_match(validator):
    """Test case-insensitive license matching."""
    info_lower = validator.get_license_info("mit")
    info_upper = validator.get_license_info("MIT")

    assert info_lower is not None
    assert info_upper is not None
    assert info_lower.identifier == info_upper.identifier
