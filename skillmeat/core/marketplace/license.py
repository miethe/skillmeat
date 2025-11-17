"""License validation for marketplace publishing.

This module provides license compatibility checking and validation for
bundles being published to marketplaces.
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Set

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class LicenseType(str, Enum):
    """Types of licenses."""

    OSI_APPROVED = "osi_approved"
    PROPRIETARY = "proprietary"
    COPYLEFT = "copyleft"
    PERMISSIVE = "permissive"
    UNKNOWN = "unknown"


class LicenseCompatibility(str, Enum):
    """License compatibility status."""

    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    REQUIRES_REVIEW = "requires_review"
    UNKNOWN = "unknown"


class LicenseInfo(BaseModel):
    """Information about a software license.

    Attributes:
        identifier: SPDX license identifier
        name: Human-readable license name
        license_type: Type of license
        is_osi_approved: Whether OSI approved
        allows_redistribution: Whether redistribution is allowed
        requires_attribution: Whether attribution is required
        is_copyleft: Whether it's a copyleft license
        notes: Additional notes about the license
    """

    identifier: str = Field(..., description="SPDX license identifier")
    name: str = Field(..., description="Human-readable name")
    license_type: LicenseType = Field(..., description="License type")
    is_osi_approved: bool = Field(..., description="OSI approved")
    allows_redistribution: bool = Field(..., description="Allows redistribution")
    requires_attribution: bool = Field(..., description="Requires attribution")
    is_copyleft: bool = Field(False, description="Is copyleft license")
    notes: Optional[str] = Field(None, description="Additional notes")


class LicenseValidationResult(BaseModel):
    """Result of license validation.

    Attributes:
        is_valid: Whether validation passed
        compatibility: Overall compatibility status
        warnings: List of warning messages
        errors: List of error messages
        conflicts: List of conflicting license pairs
        recommendations: List of recommendations
    """

    is_valid: bool = Field(..., description="Validation passed")
    compatibility: LicenseCompatibility = Field(..., description="Compatibility status")
    warnings: List[str] = Field(default_factory=list, description="Warnings")
    errors: List[str] = Field(default_factory=list, description="Errors")
    conflicts: List[tuple[str, str]] = Field(
        default_factory=list, description="Conflicting licenses"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations"
    )


class LicenseValidator:
    """Validates license compatibility for marketplace bundles.

    Provides functionality for:
    - Identifying license types
    - Checking OSI approval status
    - Detecting license conflicts
    - Validating redistribution rights
    - Providing compatibility recommendations
    """

    # OSI-approved permissive licenses
    OSI_PERMISSIVE: Set[str] = {
        "MIT",
        "Apache-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "ISC",
        "0BSD",
        "Unlicense",
        "CC0-1.0",
    }

    # OSI-approved copyleft licenses
    OSI_COPYLEFT: Set[str] = {
        "GPL-2.0",
        "GPL-2.0-only",
        "GPL-2.0-or-later",
        "GPL-3.0",
        "GPL-3.0-only",
        "GPL-3.0-or-later",
        "LGPL-2.1",
        "LGPL-2.1-only",
        "LGPL-2.1-or-later",
        "LGPL-3.0",
        "LGPL-3.0-only",
        "LGPL-3.0-or-later",
        "AGPL-3.0",
        "AGPL-3.0-only",
        "AGPL-3.0-or-later",
        "MPL-2.0",
        "EPL-2.0",
    }

    # Known proprietary/commercial licenses
    PROPRIETARY: Set[str] = {
        "Proprietary",
        "Commercial",
        "All Rights Reserved",
        "UNLICENSED",
    }

    # Incompatible license combinations (copyleft conflicts)
    INCOMPATIBLE_COMBINATIONS: Set[tuple[str, str]] = {
        # GPL incompatible with proprietary
        ("GPL-2.0", "Proprietary"),
        ("GPL-3.0", "Proprietary"),
        ("AGPL-3.0", "Proprietary"),
        # GPL-2.0 and GPL-3.0 are incompatible
        ("GPL-2.0", "GPL-3.0"),
        ("GPL-2.0-only", "GPL-3.0"),
        # Apache-2.0 incompatible with GPL-2.0
        ("Apache-2.0", "GPL-2.0"),
        ("Apache-2.0", "GPL-2.0-only"),
    }

    def __init__(self):
        """Initialize license validator."""
        self._license_db: Dict[str, LicenseInfo] = self._build_license_db()

    def _build_license_db(self) -> Dict[str, LicenseInfo]:
        """Build database of known licenses.

        Returns:
            Dictionary mapping license identifiers to LicenseInfo
        """
        licenses = {}

        # Add permissive licenses
        for license_id in self.OSI_PERMISSIVE:
            licenses[license_id] = LicenseInfo(
                identifier=license_id,
                name=self._get_license_name(license_id),
                license_type=LicenseType.PERMISSIVE,
                is_osi_approved=True,
                allows_redistribution=True,
                requires_attribution=True,
                is_copyleft=False,
            )

        # Add copyleft licenses
        for license_id in self.OSI_COPYLEFT:
            licenses[license_id] = LicenseInfo(
                identifier=license_id,
                name=self._get_license_name(license_id),
                license_type=LicenseType.COPYLEFT,
                is_osi_approved=True,
                allows_redistribution=True,
                requires_attribution=True,
                is_copyleft=True,
            )

        # Add proprietary licenses
        for license_id in self.PROPRIETARY:
            licenses[license_id] = LicenseInfo(
                identifier=license_id,
                name=license_id,
                license_type=LicenseType.PROPRIETARY,
                is_osi_approved=False,
                allows_redistribution=False,
                requires_attribution=False,
                is_copyleft=False,
                notes="Redistribution may be restricted",
            )

        return licenses

    def _get_license_name(self, license_id: str) -> str:
        """Get human-readable name for license.

        Args:
            license_id: SPDX license identifier

        Returns:
            Human-readable name
        """
        # Common names
        names = {
            "MIT": "MIT License",
            "Apache-2.0": "Apache License 2.0",
            "GPL-2.0": "GNU General Public License v2.0",
            "GPL-3.0": "GNU General Public License v3.0",
            "LGPL-2.1": "GNU Lesser General Public License v2.1",
            "LGPL-3.0": "GNU Lesser General Public License v3.0",
            "AGPL-3.0": "GNU Affero General Public License v3.0",
            "BSD-2-Clause": "BSD 2-Clause License",
            "BSD-3-Clause": "BSD 3-Clause License",
            "MPL-2.0": "Mozilla Public License 2.0",
            "ISC": "ISC License",
            "Unlicense": "The Unlicense",
        }

        return names.get(license_id, license_id)

    def get_license_info(self, license_id: str) -> Optional[LicenseInfo]:
        """Get information about a license.

        Args:
            license_id: License identifier

        Returns:
            LicenseInfo if known, None otherwise
        """
        # Normalize license ID
        license_id = license_id.strip()

        # Try exact match
        if license_id in self._license_db:
            return self._license_db[license_id]

        # Try case-insensitive match
        for db_id, info in self._license_db.items():
            if db_id.lower() == license_id.lower():
                return info

        # Unknown license
        return None

    def validate_license(self, license_id: str) -> LicenseValidationResult:
        """Validate a single license.

        Args:
            license_id: License identifier

        Returns:
            LicenseValidationResult
        """
        result = LicenseValidationResult(
            is_valid=True,
            compatibility=LicenseCompatibility.COMPATIBLE,
        )

        license_info = self.get_license_info(license_id)

        if license_info is None:
            # Unknown license
            result.warnings.append(
                f"Unknown license '{license_id}'. Consider using a standard SPDX identifier."
            )
            result.compatibility = LicenseCompatibility.UNKNOWN
            result.recommendations.append(
                "Use a standard license identifier (e.g., MIT, Apache-2.0)"
            )
            return result

        # Check if OSI approved
        if not license_info.is_osi_approved:
            result.warnings.append(
                f"License '{license_id}' is not OSI-approved. "
                "This may limit distribution on some marketplaces."
            )

        # Check redistribution rights
        if not license_info.allows_redistribution:
            result.warnings.append(
                f"License '{license_id}' may restrict redistribution. "
                "Ensure you have permission to publish to marketplaces."
            )
            result.compatibility = LicenseCompatibility.REQUIRES_REVIEW

        # Copyleft notice
        if license_info.is_copyleft:
            result.warnings.append(
                f"License '{license_id}' is a copyleft license. "
                "Ensure all bundled artifacts are compatible."
            )

        return result

    def validate_bundle_licenses(
        self, primary_license: str, artifact_licenses: List[str]
    ) -> LicenseValidationResult:
        """Validate license compatibility across a bundle.

        Args:
            primary_license: Primary bundle license
            artifact_licenses: List of artifact licenses in bundle

        Returns:
            LicenseValidationResult
        """
        result = LicenseValidationResult(
            is_valid=True,
            compatibility=LicenseCompatibility.COMPATIBLE,
        )

        # Validate primary license
        primary_result = self.validate_license(primary_license)
        result.warnings.extend(primary_result.warnings)
        result.errors.extend(primary_result.errors)

        # Get primary license info
        primary_info = self.get_license_info(primary_license)

        # Validate each artifact license
        all_licenses = [primary_license] + artifact_licenses

        for artifact_license in artifact_licenses:
            artifact_result = self.validate_license(artifact_license)

            # Merge warnings (avoid duplicates)
            for warning in artifact_result.warnings:
                if warning not in result.warnings:
                    result.warnings.append(warning)

        # Check for incompatible combinations
        checked_pairs = set()

        for i, license1 in enumerate(all_licenses):
            for license2 in all_licenses[i + 1 :]:
                # Normalize and create ordered pair
                pair = tuple(sorted([license1, license2]))

                if pair in checked_pairs:
                    continue

                checked_pairs.add(pair)

                # Check if combination is incompatible
                if self._is_incompatible(license1, license2):
                    result.conflicts.append((license1, license2))
                    result.errors.append(
                        f"Incompatible licenses detected: {license1} and {license2}"
                    )
                    result.compatibility = LicenseCompatibility.INCOMPATIBLE
                    result.is_valid = False

        # Add recommendations
        if primary_info and primary_info.is_copyleft:
            result.recommendations.append(
                "Copyleft licenses require all bundled artifacts to be compatible. "
                "Review artifact licenses carefully."
            )

        if not result.errors and result.warnings:
            result.recommendations.append(
                "Review warnings and ensure you have necessary rights to publish."
            )

        return result

    def _is_incompatible(self, license1: str, license2: str) -> bool:
        """Check if two licenses are incompatible.

        Args:
            license1: First license
            license2: Second license

        Returns:
            True if incompatible, False otherwise
        """
        # Normalize
        license1 = license1.strip()
        license2 = license2.strip()

        # Create ordered pair
        pair = tuple(sorted([license1, license2]))

        # Check exact matches
        if pair in self.INCOMPATIBLE_COMBINATIONS:
            return True

        # Check if either license is in known combinations
        for combo in self.INCOMPATIBLE_COMBINATIONS:
            # Check variations (e.g., GPL-3.0 vs GPL-3.0-only)
            if self._matches_license_family(license1, combo[0]) and \
               self._matches_license_family(license2, combo[1]):
                return True
            if self._matches_license_family(license1, combo[1]) and \
               self._matches_license_family(license2, combo[0]):
                return True

        # GPL with proprietary is always incompatible
        info1 = self.get_license_info(license1)
        info2 = self.get_license_info(license2)

        if info1 and info2:
            # Strong copyleft (GPL, AGPL) with proprietary
            if (info1.is_copyleft and info2.license_type == LicenseType.PROPRIETARY):
                if "GPL" in license1 or "AGPL" in license1:
                    return True

            if (info2.is_copyleft and info1.license_type == LicenseType.PROPRIETARY):
                if "GPL" in license2 or "AGPL" in license2:
                    return True

        return False

    def _matches_license_family(self, license1: str, license2: str) -> bool:
        """Check if two licenses are in the same family.

        Args:
            license1: First license
            license2: Second license

        Returns:
            True if same family
        """
        # Extract base license (e.g., GPL-3.0-only -> GPL-3.0)
        base1 = license1.split("-only")[0].split("-or-later")[0]
        base2 = license2.split("-only")[0].split("-or-later")[0]

        return base1 == base2

    def get_recommended_licenses(self) -> List[str]:
        """Get list of recommended licenses for marketplace publication.

        Returns:
            List of license identifiers
        """
        return [
            "MIT",
            "Apache-2.0",
            "BSD-3-Clause",
            "GPL-3.0-or-later",
            "LGPL-3.0-or-later",
            "MPL-2.0",
        ]

    def explain_license(self, license_id: str) -> str:
        """Get human-readable explanation of a license.

        Args:
            license_id: License identifier

        Returns:
            Explanation text
        """
        info = self.get_license_info(license_id)

        if not info:
            return f"Unknown license: {license_id}"

        parts = [
            f"{info.name} ({info.identifier})",
            f"Type: {info.license_type.value}",
        ]

        if info.is_osi_approved:
            parts.append("OSI Approved: Yes")
        else:
            parts.append("OSI Approved: No")

        if info.allows_redistribution:
            parts.append("Redistribution: Allowed")
        else:
            parts.append("Redistribution: Restricted")

        if info.requires_attribution:
            parts.append("Attribution: Required")

        if info.is_copyleft:
            parts.append("Copyleft: Yes (derivative works must use same license)")

        if info.notes:
            parts.append(f"Note: {info.notes}")

        return "\n".join(parts)
