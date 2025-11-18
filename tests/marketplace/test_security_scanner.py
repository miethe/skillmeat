"""Unit tests for security scanning."""

import zipfile
from pathlib import Path

import pytest

from skillmeat.core.sharing.bundle import Bundle, BundleArtifact, BundleMetadata
from skillmeat.marketplace.security_scanner import (
    ScanResult,
    SecurityScanner,
    SecurityViolationError,
)


class TestSecurityScanner:
    """Test SecurityScanner functionality."""

    @pytest.fixture
    def scanner(self):
        """Create scanner instance."""
        return SecurityScanner()

    @pytest.fixture
    def sample_bundle(self, tmp_path):
        """Create sample bundle for testing."""
        # Create bundle metadata
        metadata = BundleMetadata(
            name="test-bundle",
            description="Test bundle",
            author="Test Author",
            created_at="2025-01-01T00:00:00",
            license="MIT",
        )

        # Create artifact
        artifact = BundleArtifact(
            type="skill",
            name="test-skill",
            version="1.0.0",
            scope="user",
            path="artifacts/test-skill/",
            files=["SKILL.md", "script.py"],
            hash="sha256:abc123",
        )

        # Create bundle
        bundle = Bundle(
            metadata=metadata,
            artifacts=[artifact],
            bundle_hash="sha256:def456",
        )

        return bundle

    @pytest.fixture
    def create_test_bundle_file(self, tmp_path):
        """Helper to create test bundle ZIP files."""

        def _create(files_content):
            """Create bundle ZIP with given files.

            Args:
                files_content: Dict mapping file paths to content

            Returns:
                Path to created bundle file
            """
            bundle_path = tmp_path / "test.skillmeat-pack"

            with zipfile.ZipFile(bundle_path, "w") as zf:
                for file_path, content in files_content.items():
                    zf.writestr(file_path, content)

            return bundle_path

        return _create

    def test_check_size_limits_valid(self, scanner, sample_bundle, tmp_path):
        """Test size limit check with valid bundle."""
        # Create small bundle file
        bundle_path = tmp_path / "test.skillmeat-pack"
        with open(bundle_path, "wb") as f:
            f.write(b"x" * 1000)  # 1KB

        result = ScanResult(passed=True)
        scanner._check_size_limits(sample_bundle, bundle_path, result)

        assert result.passed is True
        assert len(result.violations) == 0

    def test_check_size_limits_too_large(self, scanner, sample_bundle, tmp_path):
        """Test size limit check with too-large bundle."""
        # Create large bundle file (simulate)
        bundle_path = tmp_path / "test.skillmeat-pack"
        # We can't actually create a 100MB+ file in tests, so we'll mock the stat
        with open(bundle_path, "wb") as f:
            f.write(b"x" * 1000)

        # Mock the file size
        original_stat = bundle_path.stat

        def mock_stat():
            s = original_stat()
            return type("MockStat", (), {"st_size": 101 * 1024 * 1024})()

        bundle_path.stat = mock_stat

        result = ScanResult(passed=True)
        scanner._check_size_limits(sample_bundle, bundle_path, result)

        assert len(result.violations) > 0
        assert any("size" in v.lower() for v in result.violations)

    def test_check_artifact_count_valid(self, scanner, sample_bundle):
        """Test artifact count check with valid bundle."""
        result = ScanResult(passed=True)
        scanner._check_artifact_count(sample_bundle, result)

        assert result.passed is True
        assert len(result.violations) == 0

    def test_validate_file_types_allowed(
        self, scanner, sample_bundle, create_test_bundle_file
    ):
        """Test file type validation with allowed types."""
        bundle_path = create_test_bundle_file(
            {
                "artifacts/skill/test.py": "print('hello')",
                "artifacts/skill/README.md": "# Test",
                "artifacts/skill/config.json": "{}",
            }
        )

        result = ScanResult(passed=True)
        scanner._validate_file_types(sample_bundle, bundle_path, result)

        assert len(result.violations) == 0

    def test_validate_file_types_blocked(
        self, scanner, sample_bundle, create_test_bundle_file
    ):
        """Test file type validation with blocked types."""
        bundle_path = create_test_bundle_file(
            {
                "artifacts/skill/malware.exe": b"\x00" * 100,
            }
        )

        result = ScanResult(passed=True)
        scanner._validate_file_types(sample_bundle, bundle_path, result)

        assert len(result.violations) > 0
        assert any("blocked" in v.lower() for v in result.violations)

    def test_validate_file_types_warning(
        self, scanner, sample_bundle, create_test_bundle_file
    ):
        """Test file type validation with warning types."""
        bundle_path = create_test_bundle_file(
            {
                "artifacts/skill/.env": "API_KEY=secret",
            }
        )

        result = ScanResult(passed=True)
        scanner._validate_file_types(sample_bundle, bundle_path, result)

        assert len(result.warnings) > 0
        assert any("sensitive" in w.lower() for w in result.warnings)

    def test_scan_for_secrets_aws_key(
        self, scanner, sample_bundle, create_test_bundle_file
    ):
        """Test secret detection for AWS keys."""
        bundle_path = create_test_bundle_file(
            {
                "artifacts/skill/config.py": "AWS_ACCESS_KEY = 'AKIAIOSFODNN7EXAMPLE'",
            }
        )

        result = ScanResult(passed=True)
        scanner._scan_for_secrets(sample_bundle, bundle_path, result)

        assert len(result.violations) > 0
        assert any("aws" in v.lower() for v in result.violations)

    def test_scan_for_secrets_github_token(
        self, scanner, sample_bundle, create_test_bundle_file
    ):
        """Test secret detection for GitHub tokens."""
        bundle_path = create_test_bundle_file(
            {
                "artifacts/skill/config.py": "GITHUB_TOKEN = 'ghp_abcdefghijklmnopqrstuvwxyz123456'",
            }
        )

        result = ScanResult(passed=True)
        scanner._scan_for_secrets(sample_bundle, bundle_path, result)

        assert len(result.violations) > 0
        assert any("github" in v.lower() for v in result.violations)

    def test_scan_for_secrets_private_key(
        self, scanner, sample_bundle, create_test_bundle_file
    ):
        """Test secret detection for private keys."""
        bundle_path = create_test_bundle_file(
            {
                "artifacts/skill/key.pem": "-----BEGIN RSA PRIVATE KEY-----\ndata\n-----END RSA PRIVATE KEY-----",
            }
        )

        result = ScanResult(passed=True)
        scanner._scan_for_secrets(sample_bundle, bundle_path, result)

        assert len(result.violations) > 0
        assert any("private" in v.lower() for v in result.violations)

    def test_scan_for_malicious_patterns_python_eval(
        self, scanner, sample_bundle, create_test_bundle_file
    ):
        """Test malicious pattern detection for Python eval."""
        bundle_path = create_test_bundle_file(
            {
                "artifacts/skill/script.py": "result = eval(user_input)",
            }
        )

        result = ScanResult(passed=True)
        scanner._scan_for_malicious_patterns(sample_bundle, bundle_path, result)

        assert len(result.warnings) > 0
        assert any("eval" in w.lower() for w in result.warnings)

    def test_scan_for_malicious_patterns_python_exec(
        self, scanner, sample_bundle, create_test_bundle_file
    ):
        """Test malicious pattern detection for Python exec."""
        bundle_path = create_test_bundle_file(
            {
                "artifacts/skill/script.py": "exec('import os')",
            }
        )

        result = ScanResult(passed=True)
        scanner._scan_for_malicious_patterns(sample_bundle, bundle_path, result)

        assert len(result.warnings) > 0
        assert any("exec" in w.lower() for w in result.warnings)

    def test_scan_bundle_complete(
        self, scanner, sample_bundle, create_test_bundle_file
    ):
        """Test complete bundle scan."""
        bundle_path = create_test_bundle_file(
            {
                "artifacts/skill/SKILL.md": "# Test Skill",
                "artifacts/skill/script.py": "print('hello')",
            }
        )

        result = scanner.scan_bundle(sample_bundle, bundle_path)

        assert result.passed is True
        assert len(result.violations) == 0

    def test_scan_bundle_with_violations(
        self, scanner, sample_bundle, create_test_bundle_file
    ):
        """Test bundle scan with violations."""
        bundle_path = create_test_bundle_file(
            {
                "artifacts/skill/config.py": "API_KEY = 'AKIAIOSFODNN7EXAMPLE'",
                "artifacts/skill/malware.exe": b"\x00" * 100,
            }
        )

        result = scanner.scan_bundle(sample_bundle, bundle_path)

        assert result.passed is False
        assert len(result.violations) > 0


class TestScanResult:
    """Test ScanResult data class."""

    def test_create_result(self):
        """Test creating scan result."""
        result = ScanResult(
            passed=True,
            violations=["Violation 1"],
            warnings=["Warning 1"],
        )

        assert result.passed is True
        assert result.has_violations is True
        assert result.has_warnings is True

    def test_no_violations(self):
        """Test result with no violations."""
        result = ScanResult(passed=True)

        assert result.has_violations is False
        assert result.has_warnings is False
