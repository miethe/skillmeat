"""Attribution tracking and generation for license compliance.

Extracts attribution requirements from bundles and generates proper
credits and notice files according to license requirements.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set
import zipfile

logger = logging.getLogger(__name__)


@dataclass
class AttributionRequirement:
    """Attribution requirement for a component.

    Attributes:
        component_name: Name of the component
        license: License identifier
        copyright_notices: List of copyright notices
        source_url: Optional URL to source repository
        modifications: Optional description of modifications made
        license_text: Optional full license text
    """

    component_name: str
    license: str
    copyright_notices: List[str] = field(default_factory=list)
    source_url: Optional[str] = None
    modifications: Optional[str] = None
    license_text: Optional[str] = None

    def __post_init__(self):
        """Validate attribution requirement."""
        if not self.component_name:
            raise ValueError("component_name cannot be empty")
        if not self.license:
            raise ValueError("license cannot be empty")


class AttributionTracker:
    """Tracks and generates attribution requirements for bundles.

    Extracts attribution requirements from bundle contents and generates
    proper CREDITS and NOTICE files according to license requirements.
    """

    # Licenses requiring attribution
    ATTRIBUTION_REQUIRED = {
        "MIT",
        "Apache-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "ISC",
        "CC-BY-4.0",
        "CC-BY-SA-4.0",
    }

    # Licenses requiring NOTICE file
    NOTICE_REQUIRED = {"Apache-2.0"}

    def __init__(self):
        """Initialize attribution tracker."""
        pass

    def extract_attributions(
        self, bundle_path: Path, scan_results: Optional[List] = None
    ) -> List[AttributionRequirement]:
        """Extract attribution requirements from bundle.

        Args:
            bundle_path: Path to bundle ZIP file
            scan_results: Optional license scan results to use

        Returns:
            List of AttributionRequirements

        Raises:
            ValueError: If bundle_path is not a valid ZIP file
        """
        if not zipfile.is_zipfile(bundle_path):
            raise ValueError(f"Not a valid ZIP file: {bundle_path}")

        logger.info(f"Extracting attributions from: {bundle_path}")

        attributions: Dict[str, AttributionRequirement] = {}

        with zipfile.ZipFile(bundle_path, "r") as zf:
            # Look for existing CREDITS or NOTICE files
            for name in zf.namelist():
                filename = Path(name).name.upper()

                if filename in {"CREDITS", "CREDITS.MD", "CREDITS.TXT"}:
                    try:
                        content = zf.read(name).decode("utf-8")
                        self._parse_credits_file(content, attributions)
                    except Exception as e:
                        logger.warning(f"Failed to parse {name}: {e}")

                elif filename in {"NOTICE", "NOTICE.TXT", "NOTICE.MD"}:
                    try:
                        content = zf.read(name).decode("utf-8")
                        self._parse_notice_file(content, attributions)
                    except Exception as e:
                        logger.warning(f"Failed to parse {name}: {e}")

            # If scan results provided, extract from those
            if scan_results:
                for result in scan_results:
                    if result.detected_license in self.ATTRIBUTION_REQUIRED:
                        component = self._extract_component_name(result.file_path)
                        if component not in attributions:
                            attributions[component] = AttributionRequirement(
                                component_name=component,
                                license=result.detected_license,
                                copyright_notices=result.copyright_notices or [],
                            )

        logger.info(f"Found {len(attributions)} attribution requirements")
        return list(attributions.values())

    def generate_credits(
        self, attributions: List[AttributionRequirement]
    ) -> str:
        """Generate CREDITS.md file content.

        Args:
            attributions: List of attribution requirements

        Returns:
            Formatted CREDITS.md content
        """
        if not attributions:
            return "# Credits and Attributions\n\nNo third-party components.\n"

        lines = [
            "# Credits and Attributions",
            "",
            "This bundle includes the following third-party software:",
            "",
        ]

        # Sort by component name
        sorted_attrs = sorted(attributions, key=lambda a: a.component_name.lower())

        for attr in sorted_attrs:
            lines.append(f"## {attr.component_name}")
            lines.append("")
            lines.append(f"- **License**: {attr.license}")

            if attr.copyright_notices:
                lines.append("- **Copyright**:")
                for notice in attr.copyright_notices:
                    lines.append(f"  - {notice}")

            if attr.source_url:
                lines.append(f"- **Source**: {attr.source_url}")

            if attr.modifications:
                lines.append(f"- **Modifications**: {attr.modifications}")
            else:
                lines.append("- **Modifications**: None")

            lines.append("")

        return "\n".join(lines)

    def generate_notice(
        self, attributions: List[AttributionRequirement], bundle_name: str
    ) -> str:
        """Generate NOTICE file content (Apache 2.0 format).

        Args:
            attributions: List of attribution requirements
            bundle_name: Name of the bundle

        Returns:
            Formatted NOTICE content
        """
        lines = [
            f"{bundle_name}",
            "",
            "This bundle contains software developed by the contributors",
            "listed in the CREDITS file.",
            "",
        ]

        # Add Apache-licensed components
        apache_components = [
            attr for attr in attributions if attr.license == "Apache-2.0"
        ]

        if apache_components:
            lines.append("Apache-Licensed Components:")
            lines.append("")

            for attr in sorted(
                apache_components, key=lambda a: a.component_name.lower()
            ):
                lines.append(f"- {attr.component_name}")
                if attr.copyright_notices:
                    for notice in attr.copyright_notices:
                        lines.append(f"  {notice}")
                lines.append("")

        return "\n".join(lines)

    def validate_attributions(
        self, bundle_path: Path, attributions: List[AttributionRequirement]
    ) -> List[str]:
        """Validate that attribution requirements are met.

        Args:
            bundle_path: Path to bundle ZIP file
            attributions: List of known attribution requirements

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not zipfile.is_zipfile(bundle_path):
            errors.append(f"Not a valid ZIP file: {bundle_path}")
            return errors

        # Check if CREDITS file exists if attributions required
        if attributions:
            has_credits = False
            has_notice = False

            with zipfile.ZipFile(bundle_path, "r") as zf:
                for name in zf.namelist():
                    filename = Path(name).name.upper()
                    if filename.startswith("CREDITS"):
                        has_credits = True
                    if filename.startswith("NOTICE"):
                        has_notice = True

            if not has_credits:
                errors.append(
                    "CREDITS file missing but attribution required "
                    f"for {len(attributions)} components"
                )

            # Check if NOTICE required
            apache_count = sum(
                1 for attr in attributions if attr.license == "Apache-2.0"
            )
            if apache_count > 0 and not has_notice:
                errors.append(
                    f"NOTICE file required for {apache_count} Apache-2.0 components"
                )

        # Validate each attribution has required fields
        for attr in attributions:
            if not attr.copyright_notices:
                errors.append(
                    f"Missing copyright notices for {attr.component_name}"
                )

            if attr.license in self.ATTRIBUTION_REQUIRED and not attr.copyright_notices:
                errors.append(
                    f"Copyright notice required for {attr.component_name} ({attr.license})"
                )

        return errors

    def format_notice(
        self, attributions: List[AttributionRequirement], bundle_name: str
    ) -> str:
        """Format NOTICE file per Apache 2.0 requirements.

        Args:
            attributions: List of attribution requirements
            bundle_name: Name of the bundle

        Returns:
            Formatted NOTICE content (same as generate_notice)
        """
        return self.generate_notice(attributions, bundle_name)

    def _extract_component_name(self, file_path: str) -> str:
        """Extract component name from file path.

        Args:
            file_path: Path to file within bundle

        Returns:
            Component name (first directory or filename)
        """
        parts = Path(file_path).parts
        if len(parts) > 1:
            # Use first directory name
            return parts[0]
        else:
            # Use filename without extension
            return Path(file_path).stem

    def _parse_credits_file(
        self, content: str, attributions: Dict[str, AttributionRequirement]
    ) -> None:
        """Parse existing CREDITS file and extract attributions.

        Args:
            content: CREDITS file content
            attributions: Dictionary to populate (modified in place)
        """
        # Simple parsing - look for "## Component" headers
        lines = content.split("\n")
        current_component = None
        current_license = None
        current_copyrights = []

        for line in lines:
            line = line.strip()

            # Component header
            if line.startswith("## "):
                # Save previous component
                if current_component and current_license:
                    attributions[current_component] = AttributionRequirement(
                        component_name=current_component,
                        license=current_license,
                        copyright_notices=current_copyrights,
                    )

                # Start new component
                current_component = line[3:].strip()
                current_license = None
                current_copyrights = []

            # License line
            elif line.startswith("- **License**:") or line.startswith("- License:"):
                current_license = line.split(":")[-1].strip()

            # Copyright line
            elif "Copyright" in line and current_component:
                # Extract copyright notice
                if ":" in line:
                    copyright = line.split(":", 1)[-1].strip()
                    if copyright and copyright not in current_copyrights:
                        current_copyrights.append(copyright)

        # Save last component
        if current_component and current_license:
            attributions[current_component] = AttributionRequirement(
                component_name=current_component,
                license=current_license,
                copyright_notices=current_copyrights,
            )

    def _parse_notice_file(
        self, content: str, attributions: Dict[str, AttributionRequirement]
    ) -> None:
        """Parse existing NOTICE file and extract attributions.

        Args:
            content: NOTICE file content
            attributions: Dictionary to populate (modified in place)
        """
        # Apache NOTICE files typically list components with copyright
        lines = content.split("\n")

        for line in lines:
            line = line.strip()

            # Look for copyright notices
            if "Copyright" in line:
                # Try to extract component and copyright
                # Format: "- ComponentName: Copyright (c) Year Holder"
                if ":" in line:
                    parts = line.split(":", 1)
                    component = parts[0].strip("- ").strip()
                    copyright = parts[1].strip()

                    if component and component not in attributions:
                        attributions[component] = AttributionRequirement(
                            component_name=component,
                            license="Apache-2.0",  # NOTICE implies Apache
                            copyright_notices=[copyright],
                        )
