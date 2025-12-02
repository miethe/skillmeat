"""Tests for cache version comparison utilities."""

import pytest

from skillmeat.cache.version_utils import (
    VersionComparator,
    VersionInfo,
    is_sha_version,
)


class TestVersionInfo:
    """Tests for VersionInfo dataclass."""

    def test_str_basic_version(self):
        """Test string representation of basic version."""
        version = VersionInfo(major=1, minor=2, patch=3)
        assert str(version) == "1.2.3"

    def test_str_with_prerelease(self):
        """Test string representation with pre-release."""
        version = VersionInfo(major=1, minor=0, patch=0, pre_release="alpha")
        assert str(version) == "1.0.0-alpha"

    def test_str_with_build_metadata(self):
        """Test string representation with build metadata."""
        version = VersionInfo(major=1, minor=0, patch=0, build_metadata="20230101")
        assert str(version) == "1.0.0+20230101"

    def test_str_complete(self):
        """Test string representation with all components."""
        version = VersionInfo(
            major=2,
            minor=0,
            patch=0,
            pre_release="rc.1",
            build_metadata="build.123",
        )
        assert str(version) == "2.0.0-rc.1+build.123"

    def test_is_pre_release(self):
        """Test pre-release detection."""
        stable = VersionInfo(major=1, minor=0, patch=0)
        pre_release = VersionInfo(major=1, minor=0, patch=0, pre_release="alpha")

        assert not stable.is_pre_release()
        assert pre_release.is_pre_release()


class TestVersionComparator:
    """Tests for VersionComparator class."""

    def test_parse_basic_version(self):
        """Test parsing basic semver."""
        v = VersionComparator.parse_version("1.2.3")
        assert v is not None
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.pre_release is None
        assert v.build_metadata is None

    def test_parse_version_with_v_prefix(self):
        """Test parsing version with 'v' prefix."""
        v = VersionComparator.parse_version("v2.0.0")
        assert v is not None
        assert v.major == 2
        assert v.minor == 0
        assert v.patch == 0

    def test_parse_version_with_prerelease(self):
        """Test parsing version with pre-release."""
        v = VersionComparator.parse_version("1.0.0-alpha")
        assert v is not None
        assert v.major == 1
        assert v.minor == 0
        assert v.patch == 0
        assert v.pre_release == "alpha"

    def test_parse_version_with_prerelease_numeric(self):
        """Test parsing version with numeric pre-release."""
        v = VersionComparator.parse_version("1.0.0-rc.1")
        assert v is not None
        assert v.pre_release == "rc.1"

    def test_parse_version_with_build(self):
        """Test parsing version with build metadata."""
        v = VersionComparator.parse_version("1.0.0+20230101")
        assert v is not None
        assert v.build_metadata == "20230101"

    def test_parse_version_complete(self):
        """Test parsing complete version."""
        v = VersionComparator.parse_version("2.0.0-beta.1+build.123")
        assert v is not None
        assert v.major == 2
        assert v.minor == 0
        assert v.patch == 0
        assert v.pre_release == "beta.1"
        assert v.build_metadata == "build.123"

    def test_parse_invalid_version(self):
        """Test parsing invalid version strings."""
        assert VersionComparator.parse_version("invalid") is None
        assert VersionComparator.parse_version("1.2") is None
        assert VersionComparator.parse_version("abc123") is None
        assert VersionComparator.parse_version("") is None

    def test_compare_equal_versions(self):
        """Test comparing equal versions."""
        result, reason = VersionComparator.compare_versions("1.2.3", "1.2.3")
        assert result == 0
        assert "equal" in reason.lower()

    def test_compare_major_version_difference(self):
        """Test comparing versions with major difference."""
        result, reason = VersionComparator.compare_versions("1.0.0", "2.0.0")
        assert result == -1
        assert "major" in reason.lower()

        result, reason = VersionComparator.compare_versions("2.0.0", "1.0.0")
        assert result == 1
        assert "major" in reason.lower()

    def test_compare_minor_version_difference(self):
        """Test comparing versions with minor difference."""
        result, reason = VersionComparator.compare_versions("1.0.0", "1.1.0")
        assert result == -1
        assert "minor" in reason.lower()

        result, reason = VersionComparator.compare_versions("1.2.0", "1.1.0")
        assert result == 1
        assert "minor" in reason.lower()

    def test_compare_patch_version_difference(self):
        """Test comparing versions with patch difference."""
        result, reason = VersionComparator.compare_versions("1.0.0", "1.0.5")
        assert result == -1
        assert "patch" in reason.lower()

        result, reason = VersionComparator.compare_versions("1.0.5", "1.0.1")
        assert result == 1
        assert "patch" in reason.lower()

    def test_compare_stable_vs_prerelease(self):
        """Test comparing stable and pre-release versions."""
        # Stable > pre-release for same base version
        result, reason = VersionComparator.compare_versions("1.0.0", "1.0.0-alpha")
        assert result == 1
        assert "stable" in reason.lower() or "pre-release" in reason.lower()

        result, reason = VersionComparator.compare_versions("1.0.0-alpha", "1.0.0")
        assert result == -1

    def test_compare_prerelease_versions(self):
        """Test comparing pre-release versions."""
        # alpha < beta
        result, reason = VersionComparator.compare_versions("1.0.0-alpha", "1.0.0-beta")
        assert result == -1

        # rc.1 < rc.2
        result, reason = VersionComparator.compare_versions("1.0.0-rc.1", "1.0.0-rc.2")
        assert result == -1

    def test_compare_non_semver_versions(self):
        """Test comparing non-semver versions."""
        # SHA versions - compare as strings
        result, reason = VersionComparator.compare_versions("abc123", "def456")
        assert result is not None  # Should still return a result
        assert "string" in reason.lower() or "semver" in reason.lower()

    def test_is_outdated_basic(self):
        """Test is_outdated with basic versions."""
        # Deployed is older -> outdated
        is_outdated, reason = VersionComparator.is_outdated("1.0.0", "2.0.0")
        assert is_outdated is True
        assert "older" in reason.lower()

        # Same version -> not outdated
        is_outdated, reason = VersionComparator.is_outdated("1.0.0", "1.0.0")
        assert is_outdated is False

        # Deployed is newer -> not outdated
        is_outdated, reason = VersionComparator.is_outdated("2.0.0", "1.0.0")
        assert is_outdated is False

    def test_is_outdated_prerelease(self):
        """Test is_outdated with pre-release versions."""
        # Pre-release is outdated compared to stable
        is_outdated, reason = VersionComparator.is_outdated("1.0.0-alpha", "1.0.0")
        assert is_outdated is True

        # Older pre-release is outdated
        is_outdated, reason = VersionComparator.is_outdated("1.0.0-alpha", "1.0.0-beta")
        assert is_outdated is True

    def test_get_version_difference_major(self):
        """Test version difference for major upgrades."""
        diff = VersionComparator.get_version_difference("1.0.0", "2.0.0")
        assert diff is not None
        assert "major" in diff.lower()
        assert "upgrade" in diff.lower()

    def test_get_version_difference_minor(self):
        """Test version difference for minor upgrades."""
        diff = VersionComparator.get_version_difference("1.0.0", "1.1.0")
        assert diff is not None
        assert "minor" in diff.lower()
        assert "upgrade" in diff.lower()

    def test_get_version_difference_patch(self):
        """Test version difference for patch upgrades."""
        diff = VersionComparator.get_version_difference("1.0.0", "1.0.1")
        assert diff is not None
        assert "patch" in diff.lower()
        assert "upgrade" in diff.lower()

    def test_get_version_difference_downgrade(self):
        """Test version difference for downgrades."""
        diff = VersionComparator.get_version_difference("2.0.0", "1.0.0")
        assert diff is not None
        assert "downgrade" in diff.lower()

    def test_get_version_difference_prerelease(self):
        """Test version difference for pre-release changes."""
        diff = VersionComparator.get_version_difference("1.0.0", "1.0.0-alpha")
        assert diff is not None
        assert "pre-release" in diff.lower()

    def test_get_version_difference_equal(self):
        """Test version difference for equal versions."""
        diff = VersionComparator.get_version_difference("1.0.0", "1.0.0")
        assert diff is None

    def test_get_version_difference_non_semver(self):
        """Test version difference for non-semver versions."""
        diff = VersionComparator.get_version_difference("abc123", "def456")
        assert diff is not None
        assert "abc123" in diff
        assert "def456" in diff


def test_is_sha_version():
    """Test SHA version detection."""
    # Valid SHA versions
    assert is_sha_version("abc1234")  # Short SHA
    assert is_sha_version("abc1234567890abcdef1234567890abcdef1234")  # Full SHA
    assert is_sha_version("ABCDEF1")  # Uppercase

    # Invalid SHA versions
    assert not is_sha_version("1.2.3")  # Semver
    assert not is_sha_version("v1.0.0")  # Version with prefix
    assert not is_sha_version("abc")  # Too short
    assert not is_sha_version("")  # Empty
    assert not is_sha_version("xyz123")  # Contains non-hex characters


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
