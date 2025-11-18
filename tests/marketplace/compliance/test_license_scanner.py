"""Tests for license scanner."""

import tempfile
import zipfile
from pathlib import Path

import pytest

from skillmeat.marketplace.compliance.license_scanner import (
    BundleLicenseReport,
    LicenseDetectionResult,
    LicenseScanner,
)


@pytest.fixture
def scanner():
    """Create license scanner instance."""
    return LicenseScanner()


@pytest.fixture
def test_bundle(tmp_path):
    """Create a test bundle with various license scenarios."""
    bundle_path = tmp_path / "test-bundle.zip"

    with zipfile.ZipFile(bundle_path, "w") as zf:
        # Bundle metadata with MIT license
        zf.writestr(
            "bundle.toml",
            'license = "MIT"\n'
        )

        # MIT licensed file
        zf.writestr(
            "src/main.py",
            '# SPDX-License-Identifier: MIT\n'
            '# Copyright (c) 2024 Test Author\n'
            'def main():\n'
            '    pass\n'
        )

        # Apache licensed file
        zf.writestr(
            "src/helper.py",
            '# SPDX-License-Identifier: Apache-2.0\n'
            '# Copyright (c) 2024 Apache Author\n'
            'def helper():\n'
            '    pass\n'
        )

        # File without license
        zf.writestr(
            "src/utils.py",
            'def util():\n'
            '    pass\n'
        )

        # LICENSE file
        zf.writestr(
            "LICENSE",
            'MIT License\n\n'
            'Permission is hereby granted, free of charge, to any person\n'
            'obtaining a copy of this software...\n'
        )

    return bundle_path


def test_scanner_initialization():
    """Test scanner initialization."""
    scanner = LicenseScanner()
    assert scanner.max_file_size == 1024 * 1024


def test_scan_bundle_success(scanner, test_bundle):
    """Test successful bundle scanning."""
    report = scanner.scan_bundle(test_bundle)

    assert isinstance(report, BundleLicenseReport)
    assert report.declared_license == "MIT"
    assert len(report.detected_licenses) > 0
    assert "MIT" in report.unique_licenses


def test_scan_bundle_detects_spdx(scanner, test_bundle):
    """Test SPDX identifier detection."""
    report = scanner.scan_bundle(test_bundle)

    # Should detect both MIT and Apache-2.0
    assert "MIT" in report.unique_licenses
    assert "Apache-2.0" in report.unique_licenses


def test_scan_bundle_detects_copyright(scanner, test_bundle):
    """Test copyright notice extraction."""
    report = scanner.scan_bundle(test_bundle)

    # Check if copyright notices were extracted
    has_copyright = any(
        d.copyright_notices for d in report.detected_licenses
    )
    assert has_copyright


def test_scan_bundle_identifies_conflicts(scanner, test_bundle):
    """Test license conflict detection."""
    report = scanner.scan_bundle(test_bundle)

    # MIT bundle with Apache-2.0 file should create conflict
    assert len(report.conflicts) > 0


def test_scan_bundle_missing_licenses(scanner, test_bundle):
    """Test detection of files without licenses."""
    report = scanner.scan_bundle(test_bundle)

    # utils.py has no license
    assert len(report.missing_licenses) > 0
    assert any("utils.py" in f for f in report.missing_licenses)


def test_scan_bundle_attribution_required(scanner, test_bundle):
    """Test attribution requirement detection."""
    report = scanner.scan_bundle(test_bundle)

    # MIT requires attribution
    assert report.attribution_required is True


def test_scan_bundle_recommendations(scanner, test_bundle):
    """Test recommendation generation."""
    report = scanner.scan_bundle(test_bundle)

    assert len(report.recommendations) > 0


def test_scan_invalid_bundle(scanner, tmp_path):
    """Test scanning invalid bundle."""
    invalid_path = tmp_path / "not-a-bundle.txt"
    invalid_path.write_text("not a zip file")

    with pytest.raises(ValueError, match="Not a valid ZIP file"):
        scanner.scan_bundle(invalid_path)


def test_detect_license_from_file(scanner, tmp_path):
    """Test license detection from single file."""
    test_file = tmp_path / "test.py"
    test_file.write_text(
        "# SPDX-License-Identifier: GPL-3.0\n"
        "# Copyright (c) 2024 GPL Author\n"
    )

    result = scanner.detect_license(test_file)

    assert result is not None
    assert result.detected_license == "GPL-3.0"
    assert result.confidence > 0.9  # SPDX has high confidence
    assert len(result.copyright_notices) > 0


def test_extract_copyright(scanner, tmp_path):
    """Test copyright extraction."""
    test_file = tmp_path / "test.py"
    test_file.write_text(
        "# Copyright (c) 2024 Author Name\n"
        "# (c) 2023 Another Author\n"
    )

    notices = scanner.extract_copyright(test_file)

    assert len(notices) >= 1
    assert any("2024" in notice for notice in notices)


def test_find_license_files(scanner, test_bundle):
    """Test finding LICENSE files in bundle."""
    license_files = scanner.find_license_files(test_bundle)

    assert len(license_files) > 0
    assert any("LICENSE" in f for f in license_files)


def test_compare_licenses(scanner):
    """Test license comparison."""
    declared = "MIT"
    detected = ["MIT", "Apache-2.0"]

    discrepancies = scanner.compare_licenses(declared, detected)

    # Should detect unexpected Apache-2.0
    assert len(discrepancies) > 0
    assert any("Apache-2.0" in d for d in discrepancies)


def test_detect_license_patterns(scanner, tmp_path):
    """Test pattern-based license detection."""
    test_file = tmp_path / "LICENSE"
    test_file.write_text(
        "MIT License\n\n"
        "Permission is hereby granted, free of charge, to any person\n"
        "obtaining a copy of this software and associated documentation\n"
    )

    result = scanner.detect_license(test_file)

    assert result is not None
    assert result.detected_license == "MIT"
    assert result.confidence > 0.0


def test_multiple_copyright_notices(scanner, tmp_path):
    """Test extraction of multiple copyright notices."""
    test_file = tmp_path / "test.py"
    test_file.write_text(
        "# Copyright (c) 2024 First Author\n"
        "# Copyright (c) 2023-2024 Second Author\n"
        "# © 2022 Third Author\n"
    )

    notices = scanner.extract_copyright(test_file)

    assert len(notices) >= 2  # Should extract multiple notices


def test_large_file_skipped(scanner, tmp_path):
    """Test that large files are skipped."""
    large_file = tmp_path / "large.py"
    # Create file larger than max_file_size
    large_file.write_bytes(b"x" * (scanner.max_file_size + 1))

    result = scanner.detect_license(large_file)

    assert result is None  # Large files should be skipped


def test_unique_licenses_property():
    """Test unique_licenses property."""
    report = BundleLicenseReport(
        declared_license="MIT",
        detected_licenses=[
            LicenseDetectionResult(file_path="a.py", detected_license="MIT"),
            LicenseDetectionResult(file_path="b.py", detected_license="MIT"),
            LicenseDetectionResult(file_path="c.py", detected_license="Apache-2.0"),
        ],
    )

    assert len(report.unique_licenses) == 2
    assert "MIT" in report.unique_licenses
    assert "Apache-2.0" in report.unique_licenses
