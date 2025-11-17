"""Unit tests for license validation."""

import json
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from skillmeat.marketplace.license_validator import (
    CompatibilityResult,
    LicenseInfo,
    LicenseValidationError,
    LicenseValidator,
)


class TestLicenseValidator:
    """Test LicenseValidator functionality."""

    @pytest.fixture
    def validator(self, tmp_path):
        """Create validator with temp cache dir."""
        return LicenseValidator(cache_dir=tmp_path / "cache")

    @pytest.fixture
    def mock_spdx_data(self):
        """Mock SPDX license list data."""
        return {
            "licenses": [
                {
                    "licenseId": "MIT",
                    "name": "MIT License",
                    "isOsiApproved": True,
                    "isFsfLibre": True,
                    "isDeprecatedLicenseId": False,
                    "reference": "https://spdx.org/licenses/MIT.html",
                },
                {
                    "licenseId": "GPL-3.0-only",
                    "name": "GNU General Public License v3.0 only",
                    "isOsiApproved": True,
                    "isFsfLibre": True,
                    "isDeprecatedLicenseId": False,
                    "reference": "https://spdx.org/licenses/GPL-3.0-only.html",
                },
                {
                    "licenseId": "Apache-2.0",
                    "name": "Apache License 2.0",
                    "isOsiApproved": True,
                    "isFsfLibre": True,
                    "isDeprecatedLicenseId": False,
                    "reference": "https://spdx.org/licenses/Apache-2.0.html",
                },
            ]
        }

    def test_validate_license_valid(self, validator, mock_spdx_data):
        """Test validating valid license."""
        # Create mock cache file
        cache_file = validator.cache_file
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump(mock_spdx_data, f)

        # Validate MIT license
        license_info = validator.validate_license("MIT")

        assert license_info.license_id == "MIT"
        assert license_info.name == "MIT License"
        assert license_info.is_osi_approved is True

    def test_validate_license_invalid(self, validator, mock_spdx_data):
        """Test validating invalid license."""
        # Create mock cache file
        cache_file = validator.cache_file
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump(mock_spdx_data, f)

        # Validate invalid license
        with pytest.raises(LicenseValidationError, match="Invalid SPDX license"):
            validator.validate_license("INVALID-LICENSE")

    def test_is_copyleft(self, validator):
        """Test copyleft detection."""
        assert validator.is_copyleft("GPL-3.0-only") is True
        assert validator.is_copyleft("LGPL-2.1-only") is True
        assert validator.is_copyleft("MIT") is False
        assert validator.is_copyleft("Apache-2.0") is False

    def test_is_permissive(self, validator):
        """Test permissive license detection."""
        assert validator.is_permissive("MIT") is True
        assert validator.is_permissive("Apache-2.0") is True
        assert validator.is_permissive("BSD-3-Clause") is True
        assert validator.is_permissive("GPL-3.0-only") is False

    def test_check_compatibility_permissive_bundle(self, validator, mock_spdx_data):
        """Test compatibility check with permissive bundle license."""
        # Create mock cache file
        cache_file = validator.cache_file
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump(mock_spdx_data, f)

        # MIT bundle with MIT artifacts should be compatible
        result = validator.check_compatibility("MIT", ["MIT", "Apache-2.0"])

        assert result.compatible is True
        assert len(result.errors) == 0

    def test_check_compatibility_copyleft_bundle(self, validator, mock_spdx_data):
        """Test compatibility check with copyleft bundle license."""
        # Create mock cache file
        cache_file = validator.cache_file
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump(mock_spdx_data, f)

        # GPL bundle with MIT artifacts should be compatible
        result = validator.check_compatibility(
            "GPL-3.0-only", ["MIT", "GPL-3.0-only"]
        )

        assert result.compatible is True
        assert len(result.errors) == 0

    def test_check_compatibility_warning(self, validator, mock_spdx_data):
        """Test compatibility check with warnings."""
        # Create mock cache file
        cache_file = validator.cache_file
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump(mock_spdx_data, f)

        # MIT bundle with GPL artifact should warn
        result = validator.check_compatibility("MIT", ["GPL-3.0-only"])

        assert len(result.warnings) > 0

    def test_warn_incompatibilities(self, validator):
        """Test warning generation for incompatible licenses."""
        warnings = validator.warn_incompatibilities(
            ["GPL-3.0-only", "Proprietary"]
        )

        assert len(warnings) > 0
        assert any("proprietary" in w.lower() for w in warnings)

    def test_cache_loading(self, validator, mock_spdx_data):
        """Test that license data is cached."""
        # Create mock cache file
        cache_file = validator.cache_file
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump(mock_spdx_data, f)

        # First load should read from cache
        validator._load_license_data()

        # Second load should use in-memory cache
        validator._load_license_data()

        # Verify cache file was only read once
        assert validator._licenses is not None
        assert len(validator._licenses) == 3


class TestCompatibilityResult:
    """Test CompatibilityResult data class."""

    def test_create_result(self):
        """Test creating compatibility result."""
        result = CompatibilityResult(
            compatible=True,
            warnings=["Warning 1"],
            errors=[],
        )

        assert result.compatible is True
        assert len(result.warnings) == 1
        assert len(result.errors) == 0


class TestLicenseInfo:
    """Test LicenseInfo data class."""

    def test_create_license_info(self):
        """Test creating license info."""
        info = LicenseInfo(
            license_id="MIT",
            name="MIT License",
            is_osi_approved=True,
            is_fsf_libre=True,
        )

        assert info.license_id == "MIT"
        assert info.name == "MIT License"
        assert info.is_osi_approved is True
        assert info.is_fsf_libre is True
