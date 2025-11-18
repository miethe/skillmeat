"""License validation for SkillMeat marketplace publishing.

Validates SPDX license identifiers and checks compatibility between
bundle licenses and artifact licenses using SPDX license data.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.request import urlopen

logger = logging.getLogger(__name__)


class LicenseValidationError(Exception):
    """Raised when license validation fails."""

    pass


@dataclass
class LicenseInfo:
    """Information about a specific license.

    Attributes:
        license_id: SPDX license identifier
        name: Full license name
        is_osi_approved: Whether OSI approved
        is_fsf_libre: Whether FSF libre
        is_deprecated: Whether deprecated
        reference: URL to license text
        details_url: URL to SPDX license details
    """

    license_id: str
    name: str
    is_osi_approved: bool = False
    is_fsf_libre: bool = False
    is_deprecated: bool = False
    reference: Optional[str] = None
    details_url: Optional[str] = None


@dataclass
class CompatibilityResult:
    """Result of license compatibility check.

    Attributes:
        compatible: Whether licenses are compatible
        warnings: List of warning messages
        errors: List of error messages
        details: Additional compatibility details
    """

    compatible: bool
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    details: Dict[str, str] = field(default_factory=dict)


class LicenseValidator:
    """Validates licenses using SPDX license list.

    Provides methods to validate license identifiers, check compatibility,
    and fetch license information from the SPDX API.
    """

    # SPDX API endpoint
    SPDX_LICENSE_LIST_URL = "https://raw.githubusercontent.com/spdx/license-list-data/main/json/licenses.json"

    # Common permissive licenses
    PERMISSIVE_LICENSES = {
        "MIT",
        "Apache-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "ISC",
        "0BSD",
        "Unlicense",
        "CC0-1.0",
    }

    # Copyleft licenses (strong)
    COPYLEFT_LICENSES = {
        "GPL-2.0",
        "GPL-2.0-only",
        "GPL-2.0-or-later",
        "GPL-3.0",
        "GPL-3.0-only",
        "GPL-3.0-or-later",
        "AGPL-3.0",
        "AGPL-3.0-only",
        "AGPL-3.0-or-later",
    }

    # Weak copyleft licenses
    WEAK_COPYLEFT_LICENSES = {
        "LGPL-2.1",
        "LGPL-2.1-only",
        "LGPL-2.1-or-later",
        "LGPL-3.0",
        "LGPL-3.0-only",
        "LGPL-3.0-or-later",
        "MPL-2.0",
        "EPL-2.0",
    }

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize license validator.

        Args:
            cache_dir: Optional directory to cache SPDX license data
        """
        self.cache_dir = cache_dir or Path.home() / ".skillmeat" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "spdx_licenses.json"

        # License data cache
        self._licenses: Optional[Dict[str, LicenseInfo]] = None

    def _load_license_data(self) -> Dict[str, LicenseInfo]:
        """Load SPDX license data from cache or API.

        Returns:
            Dictionary mapping license ID to LicenseInfo

        Raises:
            LicenseValidationError: If license data cannot be loaded
        """
        if self._licenses is not None:
            return self._licenses

        # Try to load from cache first
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self._licenses = {}
                for lic_data in data.get("licenses", []):
                    license_id = lic_data.get("licenseId")
                    if license_id:
                        self._licenses[license_id] = LicenseInfo(
                            license_id=license_id,
                            name=lic_data.get("name", ""),
                            is_osi_approved=lic_data.get("isOsiApproved", False),
                            is_fsf_libre=lic_data.get("isFsfLibre", False),
                            is_deprecated=lic_data.get("isDeprecatedLicenseId", False),
                            reference=lic_data.get("reference"),
                            details_url=lic_data.get("detailsUrl"),
                        )

                logger.debug(
                    f"Loaded {len(self._licenses)} licenses from cache"
                )
                return self._licenses

            except Exception as e:
                logger.warning(f"Failed to load license cache: {e}")

        # Fetch from SPDX API
        try:
            logger.info("Fetching SPDX license list from API...")
            with urlopen(self.SPDX_LICENSE_LIST_URL, timeout=10) as response:
                data = json.loads(response.read().decode())

            # Save to cache
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            # Parse license data
            self._licenses = {}
            for lic_data in data.get("licenses", []):
                license_id = lic_data.get("licenseId")
                if license_id:
                    self._licenses[license_id] = LicenseInfo(
                        license_id=license_id,
                        name=lic_data.get("name", ""),
                        is_osi_approved=lic_data.get("isOsiApproved", False),
                        is_fsf_libre=lic_data.get("isFsfLibre", False),
                        is_deprecated=lic_data.get("isDeprecatedLicenseId", False),
                        reference=lic_data.get("reference"),
                        details_url=lic_data.get("detailsUrl"),
                    )

            logger.info(f"Loaded {len(self._licenses)} licenses from SPDX API")
            return self._licenses

        except Exception as e:
            raise LicenseValidationError(
                f"Failed to load SPDX license data: {e}"
            ) from e

    def validate_license(self, license_id: str) -> LicenseInfo:
        """Validate that a license ID is valid SPDX identifier.

        Args:
            license_id: SPDX license identifier to validate

        Returns:
            LicenseInfo for the license

        Raises:
            LicenseValidationError: If license is not valid
        """
        licenses = self._load_license_data()

        if license_id not in licenses:
            raise LicenseValidationError(
                f"Invalid SPDX license identifier: {license_id}. "
                f"See https://spdx.org/licenses/ for valid identifiers."
            )

        license_info = licenses[license_id]

        # Warn about deprecated licenses
        if license_info.is_deprecated:
            logger.warning(
                f"License {license_id} is deprecated. "
                f"Consider using a current license identifier."
            )

        return license_info

    def get_license_info(self, license_id: str) -> Optional[LicenseInfo]:
        """Get information about a license.

        Args:
            license_id: SPDX license identifier

        Returns:
            LicenseInfo or None if not found
        """
        try:
            licenses = self._load_license_data()
            return licenses.get(license_id)
        except Exception as e:
            logger.error(f"Failed to get license info: {e}")
            return None

    def is_copyleft(self, license_id: str) -> bool:
        """Check if a license is copyleft (strong or weak).

        Args:
            license_id: SPDX license identifier

        Returns:
            True if license is copyleft
        """
        return license_id in (self.COPYLEFT_LICENSES | self.WEAK_COPYLEFT_LICENSES)

    def is_permissive(self, license_id: str) -> bool:
        """Check if a license is permissive.

        Args:
            license_id: SPDX license identifier

        Returns:
            True if license is permissive
        """
        return license_id in self.PERMISSIVE_LICENSES

    def check_compatibility(
        self, bundle_license: str, artifact_licenses: List[str]
    ) -> CompatibilityResult:
        """Check if artifact licenses are compatible with bundle license.

        Compatibility rules:
        - MIT/Apache/BSD → Compatible with all
        - GPL → Only compatible with GPL/LGPL
        - Proprietary → Must be explicitly allowed
        - Unknown → Warn but allow with confirmation

        Args:
            bundle_license: License for the bundle
            artifact_licenses: List of artifact licenses

        Returns:
            CompatibilityResult with compatibility status and details
        """
        result = CompatibilityResult(compatible=True)

        # Validate bundle license
        try:
            bundle_info = self.validate_license(bundle_license)
        except LicenseValidationError as e:
            result.compatible = False
            result.errors.append(str(e))
            return result

        # Check each artifact license
        unknown_licenses = []
        incompatible_licenses = []

        for artifact_license in artifact_licenses:
            # Skip if same as bundle license
            if artifact_license == bundle_license:
                continue

            # Check if valid SPDX license
            try:
                artifact_info = self.validate_license(artifact_license)
            except LicenseValidationError:
                unknown_licenses.append(artifact_license)
                continue

            # Check compatibility based on bundle license type
            if self.is_permissive(bundle_license):
                # Permissive bundle licenses can include most other licenses
                if artifact_license in self.COPYLEFT_LICENSES:
                    result.warnings.append(
                        f"Artifact with {artifact_license} included in {bundle_license} bundle. "
                        f"This may require the entire bundle to be {artifact_license}."
                    )
            elif bundle_license in self.COPYLEFT_LICENSES:
                # GPL bundles can only include GPL-compatible licenses
                if not self._is_gpl_compatible(artifact_license):
                    incompatible_licenses.append(artifact_license)
            elif bundle_license in self.WEAK_COPYLEFT_LICENSES:
                # LGPL/MPL bundles have more flexibility
                if artifact_license in self.COPYLEFT_LICENSES:
                    result.warnings.append(
                        f"Artifact with {artifact_license} may conflict with {bundle_license} bundle"
                    )

        # Add warnings for unknown licenses
        if unknown_licenses:
            result.warnings.append(
                f"Unknown or custom licenses found: {', '.join(unknown_licenses)}. "
                f"Please verify license compatibility manually."
            )

        # Add errors for incompatible licenses
        if incompatible_licenses:
            result.compatible = False
            result.errors.append(
                f"Incompatible licenses found: {', '.join(incompatible_licenses)}. "
                f"These are not compatible with {bundle_license}."
            )

        return result

    def _is_gpl_compatible(self, license_id: str) -> bool:
        """Check if a license is GPL-compatible.

        Args:
            license_id: SPDX license identifier

        Returns:
            True if license is GPL-compatible
        """
        # GPL is compatible with itself, LGPL, and some permissive licenses
        gpl_compatible = (
            self.COPYLEFT_LICENSES
            | self.WEAK_COPYLEFT_LICENSES
            | {
                "MIT",
                "Apache-2.0",
                "BSD-2-Clause",
                "BSD-3-Clause",
                "ISC",
                "CC0-1.0",
            }
        )
        return license_id in gpl_compatible

    def warn_incompatibilities(self, licenses: List[str]) -> List[str]:
        """Generate warnings for potentially incompatible licenses.

        Args:
            licenses: List of license identifiers

        Returns:
            List of warning messages
        """
        warnings = []
        unique_licenses = set(licenses)

        # Check for GPL + proprietary
        if any(
            lic in self.COPYLEFT_LICENSES for lic in unique_licenses
        ) and "Proprietary" in unique_licenses:
            warnings.append(
                "GPL license cannot be combined with proprietary code"
            )

        # Check for multiple copyleft licenses
        copyleft_found = [
            lic for lic in unique_licenses if lic in self.COPYLEFT_LICENSES
        ]
        if len(copyleft_found) > 1:
            warnings.append(
                f"Multiple copyleft licenses found: {', '.join(copyleft_found)}. "
                f"This may create licensing conflicts."
            )

        return warnings
