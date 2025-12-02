"""Version comparison utilities for cache operations.

Provides semantic versioning comparison and version difference detection
for artifact version tracking.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class VersionInfo:
    """Parsed version information.

    Attributes:
        major: Major version number
        minor: Minor version number
        patch: Patch version number
        pre_release: Pre-release identifier (e.g., "alpha", "rc.1")
        build_metadata: Build metadata
        original: Original version string
    """

    major: int
    minor: int
    patch: int
    pre_release: Optional[str] = None
    build_metadata: Optional[str] = None
    original: str = ""

    def __str__(self) -> str:
        """Return semantic version string."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.pre_release:
            version += f"-{self.pre_release}"
        if self.build_metadata:
            version += f"+{self.build_metadata}"
        return version

    def is_pre_release(self) -> bool:
        """Check if this is a pre-release version."""
        return self.pre_release is not None


class VersionComparator:
    """Semantic version comparison utility.

    Supports standard semver format (MAJOR.MINOR.PATCH) with optional
    pre-release and build metadata components.

    Version precedence follows semver 2.0.0:
    - Normal versions take precedence over pre-releases
    - Pre-release versions are compared alphanumerically
    - Build metadata is ignored for precedence
    """

    # Semver regex pattern
    # Format: MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
    SEMVER_PATTERN = re.compile(
        r"^(?:v)?(\d+)\.(\d+)\.(\d+)"  # Major.Minor.Patch
        r"(?:-([0-9A-Za-z\-\.]+))?"  # Optional pre-release
        r"(?:\+([0-9A-Za-z\-\.]+))?$"  # Optional build metadata
    )

    @classmethod
    def parse_version(cls, version: str) -> Optional[VersionInfo]:
        """Parse version string into components.

        Supports:
        - Standard semver: 1.2.3, v1.2.3
        - Pre-release: 1.0.0-alpha, 1.0.0-rc.1
        - Build metadata: 1.0.0+20230101
        - Combined: 1.0.0-beta.1+build.123

        Args:
            version: Version string to parse

        Returns:
            VersionInfo if version is valid semver, None otherwise

        Examples:
            >>> VersionComparator.parse_version("1.2.3")
            VersionInfo(major=1, minor=2, patch=3)

            >>> VersionComparator.parse_version("v2.0.0-alpha.1")
            VersionInfo(major=2, minor=0, patch=0, pre_release="alpha.1")
        """
        if not version:
            return None

        match = cls.SEMVER_PATTERN.match(version.strip())
        if not match:
            logger.debug(f"Failed to parse version as semver: {version}")
            return None

        major, minor, patch, pre_release, build = match.groups()

        return VersionInfo(
            major=int(major),
            minor=int(minor),
            patch=int(patch),
            pre_release=pre_release,
            build_metadata=build,
            original=version,
        )

    @classmethod
    def compare_versions(
        cls, version1: str, version2: str
    ) -> Tuple[int, Optional[str]]:
        """Compare two version strings.

        Args:
            version1: First version string
            version2: Second version string

        Returns:
            Tuple of (result, reason):
            - result: -1 if version1 < version2
                      0 if version1 == version2
                      1 if version1 > version2
                      None if versions cannot be compared
            - reason: Explanation of comparison result or failure

        Examples:
            >>> VersionComparator.compare_versions("1.0.0", "2.0.0")
            (-1, "version1 is older")

            >>> VersionComparator.compare_versions("2.1.0", "2.0.5")
            (1, "version1 is newer")

            >>> VersionComparator.compare_versions("abc123", "def456")
            (None, "Non-semver versions: comparing as strings")
        """
        # Try to parse both versions
        v1 = cls.parse_version(version1)
        v2 = cls.parse_version(version2)

        # Handle non-semver versions
        if v1 is None and v2 is None:
            # Both non-semver - compare as strings
            if version1 == version2:
                return (0, "String equality")
            elif version1 < version2:
                return (-1, "Non-semver versions: comparing as strings")
            else:
                return (1, "Non-semver versions: comparing as strings")

        if v1 is None:
            # version1 is not semver, assume it's older
            return (-1, "version1 is not semver, assuming older")

        if v2 is None:
            # version2 is not semver, assume version1 is newer
            return (1, "version2 is not semver, assuming version1 newer")

        # Both are semver - compare components

        # Compare major version
        if v1.major != v2.major:
            result = 1 if v1.major > v2.major else -1
            reason = "major version difference"
            return (result, reason)

        # Compare minor version
        if v1.minor != v2.minor:
            result = 1 if v1.minor > v2.minor else -1
            reason = "minor version difference"
            return (result, reason)

        # Compare patch version
        if v1.patch != v2.patch:
            result = 1 if v1.patch > v2.patch else -1
            reason = "patch version difference"
            return (result, reason)

        # Major.minor.patch are equal - check pre-release
        # Normal version > pre-release version
        if v1.pre_release is None and v2.pre_release is None:
            return (0, "versions are equal")

        if v1.pre_release is None:
            # v1 is normal, v2 is pre-release -> v1 > v2
            return (1, "version1 is stable, version2 is pre-release")

        if v2.pre_release is None:
            # v1 is pre-release, v2 is normal -> v1 < v2
            return (-1, "version1 is pre-release, version2 is stable")

        # Both are pre-releases - compare identifiers
        # Split by dots and compare each component
        pre1_parts = v1.pre_release.split(".")
        pre2_parts = v2.pre_release.split(".")

        for p1, p2 in zip(pre1_parts, pre2_parts):
            # Try numeric comparison first
            try:
                n1 = int(p1)
                n2 = int(p2)
                if n1 != n2:
                    result = 1 if n1 > n2 else -1
                    return (result, "pre-release numeric component difference")
            except ValueError:
                # Non-numeric - compare as strings
                if p1 != p2:
                    result = 1 if p1 > p2 else -1
                    return (result, "pre-release string component difference")

        # All compared parts are equal - check length
        if len(pre1_parts) != len(pre2_parts):
            result = 1 if len(pre1_parts) > len(pre2_parts) else -1
            return (result, "pre-release component count difference")

        # Completely equal
        return (0, "versions are equal")

    @classmethod
    def is_outdated(
        cls, deployed_version: str, upstream_version: str
    ) -> Tuple[bool, Optional[str]]:
        """Check if deployed version is outdated compared to upstream.

        Args:
            deployed_version: Currently deployed version
            upstream_version: Latest available upstream version

        Returns:
            Tuple of (is_outdated, reason):
            - is_outdated: True if deployed < upstream
            - reason: Explanation

        Examples:
            >>> VersionComparator.is_outdated("1.0.0", "2.0.0")
            (True, "deployed version is older (major version difference)")

            >>> VersionComparator.is_outdated("2.0.0", "2.0.0")
            (False, "versions are equal")

            >>> VersionComparator.is_outdated("2.1.0", "2.0.0")
            (False, "deployed version is newer")
        """
        result, reason = cls.compare_versions(deployed_version, upstream_version)

        if result is None:
            # Could not compare - assume not outdated
            return (False, f"Cannot compare versions: {reason}")

        if result < 0:
            # deployed < upstream -> outdated
            return (True, f"deployed version is older ({reason})")

        # deployed >= upstream -> not outdated
        return (False, f"deployed version is current or newer ({reason})")

    @classmethod
    def get_version_difference(cls, version1: str, version2: str) -> Optional[str]:
        """Get human-readable description of version difference.

        Args:
            version1: First version
            version2: Second version

        Returns:
            Description of difference, or None if versions are equal

        Examples:
            >>> VersionComparator.get_version_difference("1.0.0", "2.0.0")
            "major version upgrade (1 -> 2)"

            >>> VersionComparator.get_version_difference("2.0.0", "2.1.0")
            "minor version upgrade (0 -> 1)"

            >>> VersionComparator.get_version_difference("2.1.0", "2.1.5")
            "patch version upgrade (0 -> 5)"
        """
        v1 = cls.parse_version(version1)
        v2 = cls.parse_version(version2)

        # Handle non-semver
        if v1 is None or v2 is None:
            if version1 == version2:
                return None
            return f"{version1} -> {version2}"

        # Compare and describe difference
        if v1.major != v2.major:
            direction = "upgrade" if v2.major > v1.major else "downgrade"
            return f"major version {direction} ({v1.major} -> {v2.major})"

        if v1.minor != v2.minor:
            direction = "upgrade" if v2.minor > v1.minor else "downgrade"
            return f"minor version {direction} ({v1.minor} -> {v2.minor})"

        if v1.patch != v2.patch:
            direction = "upgrade" if v2.patch > v1.patch else "downgrade"
            return f"patch version {direction} ({v1.patch} -> {v2.patch})"

        # Check pre-release differences
        if v1.pre_release != v2.pre_release:
            if v1.pre_release is None:
                return f"downgrade to pre-release ({v2.pre_release})"
            if v2.pre_release is None:
                return f"upgrade to stable from pre-release ({v1.pre_release})"
            return f"pre-release change ({v1.pre_release} -> {v2.pre_release})"

        # Versions are equal
        return None


def is_sha_version(version: str) -> bool:
    """Check if version looks like a git SHA.

    Args:
        version: Version string to check

    Returns:
        True if version appears to be a git SHA

    Examples:
        >>> is_sha_version("abc1234")
        True

        >>> is_sha_version("1.2.3")
        False
    """
    if not version:
        return False

    # SHA should be 7-40 hex characters
    return (
        len(version) >= 7
        and len(version) <= 40
        and all(c in "0123456789abcdef" for c in version.lower())
    )
