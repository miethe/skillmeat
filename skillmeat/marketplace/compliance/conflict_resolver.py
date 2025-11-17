"""License conflict detection and resolution.

Detects incompatible license combinations and suggests resolutions
for common licensing conflicts.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class LicenseConflict:
    """Represents a license compatibility conflict.

    Attributes:
        license1: First license in conflict
        license2: Second license in conflict
        conflict_type: Type of conflict (incompatible, warning, info)
        description: Description of the conflict
        resolution: Suggested resolution
    """

    license1: str
    license2: str
    conflict_type: str  # "incompatible", "warning", "info"
    description: str
    resolution: str

    def __post_init__(self):
        """Validate conflict type."""
        valid_types = {"incompatible", "warning", "info"}
        if self.conflict_type not in valid_types:
            raise ValueError(
                f"Invalid conflict_type '{self.conflict_type}'. "
                f"Must be one of {valid_types}"
            )


class ConflictResolver:
    """Detects and resolves license conflicts.

    Checks license compatibility matrix and provides resolution
    suggestions for common conflicts.
    """

    # License compatibility matrix
    # Format: (license1, license2) -> (compatibility, description, resolution)
    CONFLICT_MATRIX: Dict[Tuple[str, str], Tuple[str, str, str]] = {
        # GPL-2.0 incompatibilities
        ("GPL-2.0", "Apache-2.0"): (
            "incompatible",
            "GPL-2.0 is incompatible with Apache-2.0 due to patent clause",
            "Upgrade to GPL-3.0 or remove Apache-2.0 components",
        ),
        ("GPL-2.0-only", "Apache-2.0"): (
            "incompatible",
            "GPL-2.0-only is incompatible with Apache-2.0",
            "Upgrade to GPL-3.0 or remove Apache-2.0 components",
        ),
        ("GPL-2.0", "Proprietary"): (
            "incompatible",
            "GPL cannot be combined with proprietary code",
            "Remove proprietary code or obtain alternative licensing",
        ),
        ("GPL-2.0-only", "Proprietary"): (
            "incompatible",
            "GPL cannot be combined with proprietary code",
            "Remove proprietary code or obtain alternative licensing",
        ),
        # GPL-3.0 with Apache is compatible
        ("GPL-3.0", "Apache-2.0"): (
            "info",
            "GPL-3.0 is compatible with Apache-2.0",
            "No action needed",
        ),
        ("GPL-3.0-only", "Apache-2.0"): (
            "info",
            "GPL-3.0 is compatible with Apache-2.0",
            "No action needed",
        ),
        ("GPL-3.0-or-later", "Apache-2.0"): (
            "info",
            "GPL-3.0+ is compatible with Apache-2.0",
            "No action needed",
        ),
        # GPL with proprietary
        ("GPL-3.0", "Proprietary"): (
            "incompatible",
            "GPL cannot be combined with proprietary code",
            "Remove proprietary code or obtain alternative licensing",
        ),
        ("GPL-3.0-only", "Proprietary"): (
            "incompatible",
            "GPL cannot be combined with proprietary code",
            "Remove proprietary code or obtain alternative licensing",
        ),
        # AGPL conflicts
        ("AGPL-3.0", "Proprietary"): (
            "incompatible",
            "AGPL cannot be combined with proprietary code",
            "Remove proprietary code or dual-license",
        ),
        ("AGPL-3.0-only", "Proprietary"): (
            "incompatible",
            "AGPL cannot be combined with proprietary code",
            "Remove proprietary code or dual-license",
        ),
        # Permissive licenses are generally compatible
        ("MIT", "Apache-2.0"): (
            "info",
            "MIT and Apache-2.0 are compatible",
            "No action needed",
        ),
        ("MIT", "BSD-2-Clause"): (
            "info",
            "MIT and BSD are compatible",
            "No action needed",
        ),
        ("MIT", "BSD-3-Clause"): (
            "info",
            "MIT and BSD are compatible",
            "No action needed",
        ),
        ("Apache-2.0", "BSD-2-Clause"): (
            "info",
            "Apache-2.0 and BSD are compatible",
            "No action needed",
        ),
        ("Apache-2.0", "BSD-3-Clause"): (
            "info",
            "Apache-2.0 and BSD are compatible",
            "No action needed",
        ),
        # BSD variants with GPL
        ("BSD-3-Clause", "GPL-2.0"): (
            "warning",
            "BSD can be combined with GPL, but result must be GPL",
            "Ensure bundle is distributed under GPL",
        ),
        ("BSD-2-Clause", "GPL-2.0"): (
            "warning",
            "BSD can be combined with GPL, but result must be GPL",
            "Ensure bundle is distributed under GPL",
        ),
        ("BSD-3-Clause", "GPL-3.0"): (
            "warning",
            "BSD can be combined with GPL, but result must be GPL",
            "Ensure bundle is distributed under GPL",
        ),
        ("BSD-2-Clause", "GPL-3.0"): (
            "warning",
            "BSD can be combined with GPL, but result must be GPL",
            "Ensure bundle is distributed under GPL",
        ),
        # MIT with GPL
        ("MIT", "GPL-2.0"): (
            "warning",
            "MIT can be combined with GPL, but result must be GPL",
            "Ensure bundle is distributed under GPL",
        ),
        ("MIT", "GPL-3.0"): (
            "warning",
            "MIT can be combined with GPL, but result must be GPL",
            "Ensure bundle is distributed under GPL",
        ),
        # LGPL combinations
        ("LGPL-2.1", "Proprietary"): (
            "warning",
            "LGPL can be used with proprietary code if dynamically linked",
            "Ensure LGPL components are dynamically linkable",
        ),
        ("LGPL-3.0", "Proprietary"): (
            "warning",
            "LGPL can be used with proprietary code if dynamically linked",
            "Ensure LGPL components are dynamically linkable",
        ),
        # MPL combinations
        ("MPL-2.0", "Proprietary"): (
            "warning",
            "MPL allows combination with proprietary code per file",
            "Ensure MPL files remain under MPL",
        ),
        ("MPL-2.0", "GPL-2.0"): (
            "warning",
            "MPL 2.0 can be combined with GPL but is complex",
            "Review Mozilla's GPL compatibility guide",
        ),
        ("MPL-2.0", "GPL-3.0"): (
            "info",
            "MPL 2.0 is compatible with GPL-3.0",
            "No action needed",
        ),
    }

    # License categories
    COPYLEFT_STRONG = {
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

    COPYLEFT_WEAK = {
        "LGPL-2.1",
        "LGPL-2.1-only",
        "LGPL-2.1-or-later",
        "LGPL-3.0",
        "LGPL-3.0-only",
        "LGPL-3.0-or-later",
        "MPL-2.0",
        "EPL-2.0",
    }

    PERMISSIVE = {
        "MIT",
        "Apache-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "ISC",
        "0BSD",
        "Unlicense",
    }

    def __init__(self):
        """Initialize conflict resolver."""
        pass

    def detect_conflicts(self, licenses: List[str]) -> List[LicenseConflict]:
        """Detect conflicts in a list of licenses.

        Args:
            licenses: List of SPDX license identifiers

        Returns:
            List of LicenseConflicts found
        """
        conflicts = []
        unique_licenses = list(set(licenses))

        logger.info(f"Checking {len(unique_licenses)} unique licenses for conflicts")

        # Check each pair of licenses
        for i, lic1 in enumerate(unique_licenses):
            for lic2 in unique_licenses[i + 1 :]:
                conflict = self.can_combine(lic1, lic2)
                if conflict:
                    conflicts.append(conflict)

        # Check for multiple copyleft licenses
        copyleft_licenses = [
            lic for lic in unique_licenses if lic in self.COPYLEFT_STRONG
        ]
        if len(copyleft_licenses) > 1:
            conflicts.append(
                LicenseConflict(
                    license1=copyleft_licenses[0],
                    license2=copyleft_licenses[1],
                    conflict_type="warning",
                    description=f"Multiple copyleft licenses: {', '.join(copyleft_licenses)}",
                    resolution="Choose a single copyleft license or separate into multiple bundles",
                )
            )

        logger.info(
            f"Found {len(conflicts)} conflicts: "
            f"{sum(1 for c in conflicts if c.conflict_type == 'incompatible')} incompatible, "
            f"{sum(1 for c in conflicts if c.conflict_type == 'warning')} warnings"
        )

        return conflicts

    def suggest_resolutions(
        self, conflicts: List[LicenseConflict]
    ) -> Dict[str, List[str]]:
        """Suggest resolutions for detected conflicts.

        Args:
            conflicts: List of LicenseConflicts

        Returns:
            Dictionary mapping conflict type to list of suggestions
        """
        resolutions = {
            "incompatible": [],
            "warning": [],
            "info": [],
        }

        for conflict in conflicts:
            resolution = f"{conflict.license1} + {conflict.license2}: {conflict.resolution}"
            resolutions[conflict.conflict_type].append(resolution)

        return resolutions

    def can_combine(
        self, license1: str, license2: str
    ) -> Optional[LicenseConflict]:
        """Check if two licenses can be combined.

        Args:
            license1: First SPDX license identifier
            license2: Second SPDX license identifier

        Returns:
            LicenseConflict if there's an issue, None if compatible
        """
        # Same license is always compatible
        if license1 == license2:
            return None

        # Check matrix (both directions)
        for lic_pair in [(license1, license2), (license2, license1)]:
            if lic_pair in self.CONFLICT_MATRIX:
                conflict_type, description, resolution = self.CONFLICT_MATRIX[
                    lic_pair
                ]

                # Only return conflicts/warnings, not info
                if conflict_type in {"incompatible", "warning"}:
                    return LicenseConflict(
                        license1=license1,
                        license2=license2,
                        conflict_type=conflict_type,
                        description=description,
                        resolution=resolution,
                    )

        # Check general compatibility rules
        # Permissive licenses are generally compatible with each other
        if license1 in self.PERMISSIVE and license2 in self.PERMISSIVE:
            return None

        # Proprietary with any copyleft is incompatible
        if (
            "proprietary" in license1.lower() or "proprietary" in license2.lower()
        ):
            if license1 in self.COPYLEFT_STRONG or license2 in self.COPYLEFT_STRONG:
                return LicenseConflict(
                    license1=license1,
                    license2=license2,
                    conflict_type="incompatible",
                    description="Copyleft licenses cannot be combined with proprietary code",
                    resolution="Remove proprietary code or obtain alternative licensing",
                )

        # Permissive with copyleft requires copyleft for derivative
        if (
            license1 in self.PERMISSIVE
            and license2 in self.COPYLEFT_STRONG
            or license2 in self.PERMISSIVE
            and license1 in self.COPYLEFT_STRONG
        ):
            copyleft_lic = (
                license1 if license1 in self.COPYLEFT_STRONG else license2
            )
            return LicenseConflict(
                license1=license1,
                license2=license2,
                conflict_type="warning",
                description=f"Permissive license combined with {copyleft_lic}",
                resolution=f"Ensure bundle is distributed under {copyleft_lic}",
            )

        # No known conflict
        return None

    def require_dual_license(self, licenses: List[str]) -> Optional[str]:
        """Determine if dual licensing is needed.

        Args:
            licenses: List of SPDX license identifiers

        Returns:
            Recommendation for dual licensing, or None if not needed
        """
        conflicts = self.detect_conflicts(licenses)

        # Check for incompatible licenses
        incompatible = [c for c in conflicts if c.conflict_type == "incompatible"]
        if incompatible:
            return (
                "Dual licensing recommended to resolve incompatibilities. "
                "Consider offering bundle under multiple licenses."
            )

        # Check for multiple copyleft licenses
        copyleft_count = sum(1 for lic in licenses if lic in self.COPYLEFT_STRONG)
        if copyleft_count > 1:
            return (
                "Multiple copyleft licenses detected. "
                "Consider dual licensing or separate bundles."
            )

        return None

    def get_compatibility_matrix(self) -> Dict[Tuple[str, str], str]:
        """Get simplified compatibility matrix.

        Returns:
            Dictionary mapping license pairs to compatibility status
        """
        matrix = {}
        for (lic1, lic2), (status, _, _) in self.CONFLICT_MATRIX.items():
            matrix[(lic1, lic2)] = status

        return matrix

    def is_copyleft(self, license: str) -> bool:
        """Check if license is copyleft (strong or weak).

        Args:
            license: SPDX license identifier

        Returns:
            True if copyleft
        """
        return license in (self.COPYLEFT_STRONG | self.COPYLEFT_WEAK)

    def is_permissive(self, license: str) -> bool:
        """Check if license is permissive.

        Args:
            license: SPDX license identifier

        Returns:
            True if permissive
        """
        return license in self.PERMISSIVE

    def get_license_category(self, license: str) -> str:
        """Get category for a license.

        Args:
            license: SPDX license identifier

        Returns:
            Category: "copyleft-strong", "copyleft-weak", "permissive", "proprietary", "unknown"
        """
        if license in self.COPYLEFT_STRONG:
            return "copyleft-strong"
        elif license in self.COPYLEFT_WEAK:
            return "copyleft-weak"
        elif license in self.PERMISSIVE:
            return "permissive"
        elif "proprietary" in license.lower() or "commercial" in license.lower():
            return "proprietary"
        else:
            return "unknown"
