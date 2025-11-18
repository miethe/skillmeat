"""License scanning for bundle files.

Scans all files in a bundle for license headers, copyright notices,
and license files. Detects SPDX identifiers and compares declared vs detected licenses.
"""

import logging
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class LicenseDetectionResult:
    """Result of license detection in a single file.

    Attributes:
        file_path: Path to the file within bundle
        detected_license: Detected SPDX identifier (if found)
        confidence: Confidence level (0.0 to 1.0)
        license_text: Extracted license text
        copyright_notices: List of copyright notices found
    """

    file_path: str
    detected_license: Optional[str] = None
    confidence: float = 0.0
    license_text: Optional[str] = None
    copyright_notices: List[str] = field(default_factory=list)


@dataclass
class BundleLicenseReport:
    """Complete license report for a bundle.

    Attributes:
        declared_license: License declared in bundle metadata
        detected_licenses: List of detected licenses in files
        conflicts: List of conflicting licenses
        missing_licenses: List of files without license headers
        attribution_required: Whether attribution is required
        recommendations: List of recommendations for publisher
    """

    declared_license: str
    detected_licenses: List[LicenseDetectionResult] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    missing_licenses: List[str] = field(default_factory=list)
    attribution_required: bool = False
    recommendations: List[str] = field(default_factory=list)

    @property
    def has_conflicts(self) -> bool:
        """Check if report has license conflicts."""
        return len(self.conflicts) > 0

    @property
    def has_missing_licenses(self) -> bool:
        """Check if report has files missing licenses."""
        return len(self.missing_licenses) > 0

    @property
    def unique_licenses(self) -> Set[str]:
        """Get set of unique detected licenses."""
        licenses = set()
        for detection in self.detected_licenses:
            if detection.detected_license:
                licenses.add(detection.detected_license)
        return licenses


class LicenseScanner:
    """Scans bundle files for licenses and copyright notices.

    Uses multiple detection methods:
    1. SPDX identifier scanning in file headers
    2. LICENSE file parsing
    3. Package metadata reading
    4. Pattern matching for common licenses
    """

    # SPDX identifier patterns
    SPDX_PATTERN = re.compile(
        r"SPDX-License-Identifier:\s*([A-Za-z0-9\-\.]+)", re.IGNORECASE
    )

    # Copyright notice patterns
    COPYRIGHT_PATTERNS = [
        re.compile(r"Copyright\s+(?:\(c\)\s*)?(\d{4}(?:-\d{4})?)\s+(.+)", re.IGNORECASE),
        re.compile(r"\(c\)\s+(\d{4}(?:-\d{4})?)\s+(.+)", re.IGNORECASE),
        re.compile(r"©\s+(\d{4}(?:-\d{4})?)\s+(.+)", re.IGNORECASE),
    ]

    # License file names
    LICENSE_FILES = {
        "LICENSE",
        "LICENSE.txt",
        "LICENSE.md",
        "COPYING",
        "COPYING.txt",
        "COPYRIGHT",
        "NOTICE",
        "NOTICE.txt",
    }

    # Package metadata files
    PACKAGE_METADATA_FILES = {
        "package.json": "license",
        "setup.py": None,  # Requires parsing
        "pyproject.toml": "license",
        "Cargo.toml": "license",
        "composer.json": "license",
        "pom.xml": None,  # Requires XML parsing
    }

    # Common license patterns (substring matching)
    LICENSE_PATTERNS = {
        "MIT": [
            "Permission is hereby granted, free of charge",
            "MIT License",
        ],
        "Apache-2.0": [
            "Apache License, Version 2.0",
            "Licensed under the Apache License",
        ],
        "GPL-2.0": [
            "GNU General Public License, version 2",
            "GPL version 2",
        ],
        "GPL-3.0": [
            "GNU General Public License, version 3",
            "GPL version 3",
        ],
        "BSD-2-Clause": [
            "Redistribution and use in source and binary forms",
            "BSD 2-Clause License",
        ],
        "BSD-3-Clause": [
            "Redistribution and use in source and binary forms",
            "Neither the name of",
        ],
    }

    # File extensions to scan
    SCANNABLE_EXTENSIONS = {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".rs",
        ".go",
        ".rb",
        ".php",
        ".cs",
        ".swift",
        ".kt",
        ".scala",
        ".md",
        ".txt",
        ".json",
        ".toml",
        ".yaml",
        ".yml",
        ".xml",
    }

    def __init__(self, max_file_size: int = 1024 * 1024):
        """Initialize license scanner.

        Args:
            max_file_size: Maximum file size to scan (default 1MB)
        """
        self.max_file_size = max_file_size

    def scan_bundle(self, bundle_path: Path) -> BundleLicenseReport:
        """Scan all files in bundle for license information.

        Args:
            bundle_path: Path to bundle ZIP file

        Returns:
            BundleLicenseReport with scan results

        Raises:
            ValueError: If bundle_path is not a valid ZIP file
        """
        if not zipfile.is_zipfile(bundle_path):
            raise ValueError(f"Not a valid ZIP file: {bundle_path}")

        logger.info(f"Scanning bundle for licenses: {bundle_path}")

        detected_licenses = []
        license_files = []
        declared_license = None

        with zipfile.ZipFile(bundle_path, "r") as zf:
            # First, look for bundle metadata to get declared license
            for name in zf.namelist():
                if name.endswith("bundle.toml"):
                    try:
                        content = zf.read(name).decode("utf-8")
                        match = re.search(r'license\s*=\s*"([^"]+)"', content)
                        if match:
                            declared_license = match.group(1)
                            logger.debug(f"Found declared license: {declared_license}")
                    except Exception as e:
                        logger.warning(f"Failed to read bundle.toml: {e}")

            # Scan all files
            for file_info in zf.filelist:
                # Skip directories
                if file_info.is_dir():
                    continue

                # Check if it's a license file
                filename = Path(file_info.filename).name.upper()
                if filename in self.LICENSE_FILES:
                    license_files.append(file_info.filename)
                    result = self._scan_license_file(zf, file_info)
                    if result:
                        detected_licenses.append(result)
                    continue

                # Check if file should be scanned
                if not self._should_scan_file(file_info):
                    continue

                # Scan source file
                result = self._scan_source_file(zf, file_info)
                if result:
                    detected_licenses.append(result)

        # Use declared license or try to infer from detected
        if not declared_license and detected_licenses:
            # Use most common detected license
            license_counts: Dict[str, int] = {}
            for detection in detected_licenses:
                if detection.detected_license:
                    license_counts[detection.detected_license] = (
                        license_counts.get(detection.detected_license, 0) + 1
                    )
            if license_counts:
                declared_license = max(license_counts, key=license_counts.get)  # type: ignore
                logger.info(f"Inferred declared license: {declared_license}")

        # Build report
        report = BundleLicenseReport(
            declared_license=declared_license or "Unknown",
            detected_licenses=detected_licenses,
        )

        # Analyze results
        self._analyze_report(report)

        logger.info(
            f"Scan complete: {len(detected_licenses)} files scanned, "
            f"{len(report.unique_licenses)} unique licenses found"
        )

        return report

    def detect_license(self, file_path: Path) -> Optional[LicenseDetectionResult]:
        """Detect license from a single file.

        Args:
            file_path: Path to file to scan

        Returns:
            LicenseDetectionResult or None if file cannot be scanned
        """
        if not file_path.exists() or not file_path.is_file():
            return None

        if file_path.stat().st_size > self.max_file_size:
            logger.debug(f"Skipping large file: {file_path}")
            return None

        try:
            content = file_path.read_text(encoding="utf-8")
            return self._detect_from_content(str(file_path), content)
        except Exception as e:
            logger.debug(f"Failed to scan {file_path}: {e}")
            return None

    def extract_copyright(self, file_path: Path) -> List[str]:
        """Extract copyright notices from a file.

        Args:
            file_path: Path to file

        Returns:
            List of copyright notices found
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            return self._extract_copyright_notices(content)
        except Exception as e:
            logger.debug(f"Failed to extract copyright from {file_path}: {e}")
            return []

    def find_license_files(self, bundle_path: Path) -> List[str]:
        """Find all LICENSE files in bundle.

        Args:
            bundle_path: Path to bundle ZIP file

        Returns:
            List of license file paths within bundle
        """
        if not zipfile.is_zipfile(bundle_path):
            return []

        license_files = []
        with zipfile.ZipFile(bundle_path, "r") as zf:
            for name in zf.namelist():
                filename = Path(name).name.upper()
                if filename in self.LICENSE_FILES:
                    license_files.append(name)

        return license_files

    def compare_licenses(
        self, declared: str, detected: List[str]
    ) -> List[str]:
        """Compare declared license with detected licenses.

        Args:
            declared: Declared license identifier
            detected: List of detected license identifiers

        Returns:
            List of discrepancies found
        """
        discrepancies = []
        detected_set = set(detected)

        if declared not in detected_set and detected_set:
            discrepancies.append(
                f"Declared license '{declared}' not found in any scanned files"
            )

        unexpected = detected_set - {declared}
        if unexpected:
            discrepancies.append(
                f"Unexpected licenses found: {', '.join(sorted(unexpected))}"
            )

        return discrepancies

    def _should_scan_file(self, file_info: zipfile.ZipInfo) -> bool:
        """Check if file should be scanned.

        Args:
            file_info: ZipInfo for file

        Returns:
            True if file should be scanned
        """
        # Check size
        if file_info.file_size > self.max_file_size:
            return False

        # Check extension
        suffix = Path(file_info.filename).suffix.lower()
        return suffix in self.SCANNABLE_EXTENSIONS

    def _scan_source_file(
        self, zf: zipfile.ZipFile, file_info: zipfile.ZipInfo
    ) -> Optional[LicenseDetectionResult]:
        """Scan a source file for license information.

        Args:
            zf: ZipFile object
            file_info: ZipInfo for file to scan

        Returns:
            LicenseDetectionResult or None
        """
        try:
            content = zf.read(file_info.filename).decode("utf-8", errors="ignore")
            # Only scan first 50 lines for performance
            lines = content.split("\n")[:50]
            content_header = "\n".join(lines)

            return self._detect_from_content(file_info.filename, content_header)

        except Exception as e:
            logger.debug(f"Failed to scan {file_info.filename}: {e}")
            return None

    def _scan_license_file(
        self, zf: zipfile.ZipFile, file_info: zipfile.ZipInfo
    ) -> Optional[LicenseDetectionResult]:
        """Scan a LICENSE file.

        Args:
            zf: ZipFile object
            file_info: ZipInfo for LICENSE file

        Returns:
            LicenseDetectionResult or None
        """
        try:
            content = zf.read(file_info.filename).decode("utf-8", errors="ignore")
            result = self._detect_from_content(file_info.filename, content, is_license_file=True)

            # Higher confidence for LICENSE files
            if result and result.detected_license:
                result.confidence = min(1.0, result.confidence + 0.3)

            return result

        except Exception as e:
            logger.debug(f"Failed to scan license file {file_info.filename}: {e}")
            return None

    def _detect_from_content(
        self, file_path: str, content: str, is_license_file: bool = False
    ) -> Optional[LicenseDetectionResult]:
        """Detect license from file content.

        Args:
            file_path: Path to file
            content: File content
            is_license_file: Whether this is a LICENSE file

        Returns:
            LicenseDetectionResult or None
        """
        detected_license = None
        confidence = 0.0
        license_text = None
        copyright_notices = self._extract_copyright_notices(content)

        # Method 1: Look for SPDX identifier (highest confidence)
        spdx_match = self.SPDX_PATTERN.search(content)
        if spdx_match:
            detected_license = spdx_match.group(1)
            confidence = 0.95
            logger.debug(f"Found SPDX identifier in {file_path}: {detected_license}")

        # Method 2: Pattern matching (medium confidence)
        elif is_license_file or not detected_license:
            for license_id, patterns in self.LICENSE_PATTERNS.items():
                matches = sum(1 for pattern in patterns if pattern in content)
                pattern_confidence = matches / len(patterns)

                if pattern_confidence > confidence:
                    detected_license = license_id
                    confidence = pattern_confidence * 0.7  # Lower than SPDX
                    if is_license_file:
                        license_text = content[:500]  # First 500 chars

        # Only return if we found something
        if detected_license or copyright_notices:
            return LicenseDetectionResult(
                file_path=file_path,
                detected_license=detected_license,
                confidence=confidence,
                license_text=license_text,
                copyright_notices=copyright_notices,
            )

        return None

    def _extract_copyright_notices(self, content: str) -> List[str]:
        """Extract copyright notices from content.

        Args:
            content: File content

        Returns:
            List of copyright notices
        """
        notices = []
        for pattern in self.COPYRIGHT_PATTERNS:
            for match in pattern.finditer(content):
                year = match.group(1)
                holder = match.group(2).strip()
                # Clean up holder (remove trailing punctuation, newlines)
                holder = re.sub(r"[\n\r]+", " ", holder)
                holder = holder.split(".")[0].strip()  # Stop at first period
                notice = f"Copyright (c) {year} {holder}"
                if notice not in notices:
                    notices.append(notice)

        return notices

    def _analyze_report(self, report: BundleLicenseReport) -> None:
        """Analyze scan results and add conflicts/recommendations.

        Args:
            report: BundleLicenseReport to analyze (modified in place)
        """
        # Check for files without licenses
        for detection in report.detected_licenses:
            if not detection.detected_license and not detection.copyright_notices:
                report.missing_licenses.append(detection.file_path)

        # Check for conflicts with declared license
        unique_licenses = report.unique_licenses
        if report.declared_license != "Unknown":
            for lic in unique_licenses:
                if lic != report.declared_license:
                    report.conflicts.append(
                        f"File licensed under {lic} conflicts with declared {report.declared_license}"
                    )

        # Check if attribution required
        attribution_licenses = {
            "MIT",
            "Apache-2.0",
            "BSD-2-Clause",
            "BSD-3-Clause",
            "ISC",
        }
        if report.declared_license in attribution_licenses or any(
            lic in attribution_licenses for lic in unique_licenses
        ):
            report.attribution_required = True

        # Add recommendations
        if report.missing_licenses:
            report.recommendations.append(
                f"Add license headers to {len(report.missing_licenses)} files"
            )

        if report.conflicts:
            report.recommendations.append(
                "Resolve license conflicts or use dual licensing"
            )

        if report.declared_license == "Unknown":
            report.recommendations.append(
                "Declare a license in bundle metadata"
            )

        if not any(
            d.copyright_notices for d in report.detected_licenses
        ):
            report.recommendations.append(
                "Add copyright notices to your source files"
            )
