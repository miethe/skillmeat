"""Bundle validation logic for secure import operations.

Validates bundle integrity, prevents path traversal attacks, checks file sizes,
and ensures bundle schema compliance.
"""

import hashlib
import json
import logging
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from skillmeat.utils.toml_compat import loads as toml_loads

logger = logging.getLogger(__name__)


# Security constants
MAX_BUNDLE_SIZE_MB = 500  # Maximum bundle size in MB
MAX_BUNDLE_FILES = 10000  # Maximum number of files in bundle
MAX_FILE_SIZE_MB = 100  # Maximum individual file size in MB
MAX_PATH_LENGTH = 255  # Maximum path component length
SUSPICIOUS_EXTENSIONS = {".exe", ".dll", ".so", ".dylib", ".bat", ".sh", ".cmd"}
ALLOWED_ARTIFACT_TYPES = {"skill", "command", "agent"}


@dataclass
class ValidationIssue:
    """Represents a validation issue found during bundle inspection."""

    severity: str  # "error", "warning", "info"
    category: str  # "security", "schema", "integrity", "size"
    message: str
    file_path: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        """Format issue for display."""
        prefix = f"[{self.severity.upper()}] {self.category}: "
        if self.file_path:
            return f"{prefix}{self.message} (file: {self.file_path})"
        return f"{prefix}{self.message}"


@dataclass
class ValidationResult:
    """Result of bundle validation."""

    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    bundle_hash: Optional[str] = None
    manifest_data: Optional[Dict[str, Any]] = None
    artifact_count: int = 0
    total_size_bytes: int = 0

    def has_errors(self) -> bool:
        """Check if validation has any errors."""
        return any(issue.severity == "error" for issue in self.issues)

    def has_warnings(self) -> bool:
        """Check if validation has any warnings."""
        return any(issue.severity == "warning" for issue in self.issues)

    def get_errors(self) -> List[ValidationIssue]:
        """Get all error-level issues."""
        return [issue for issue in self.issues if issue.severity == "error"]

    def get_warnings(self) -> List[ValidationIssue]:
        """Get all warning-level issues."""
        return [issue for issue in self.issues if issue.severity == "warning"]

    def summary(self) -> str:
        """Generate human-readable summary."""
        if self.is_valid:
            return (
                f"Bundle valid: {self.artifact_count} artifacts, "
                f"{self.total_size_bytes / 1024 / 1024:.2f} MB"
            )
        else:
            error_count = len(self.get_errors())
            warning_count = len(self.get_warnings())
            return (
                f"Bundle invalid: {error_count} errors, {warning_count} warnings"
            )


class BundleValidator:
    """Validates bundle files for security and integrity.

    Performs comprehensive validation including:
    - Integrity checks (hash verification)
    - Security checks (path traversal, zip bombs, suspicious files)
    - Schema validation (manifest structure, artifact metadata)
    - Size limits (bundle size, file count, individual file sizes)
    """

    def __init__(
        self,
        max_bundle_size_mb: int = MAX_BUNDLE_SIZE_MB,
        max_file_size_mb: int = MAX_FILE_SIZE_MB,
        max_files: int = MAX_BUNDLE_FILES,
    ):
        """Initialize bundle validator.

        Args:
            max_bundle_size_mb: Maximum bundle size in MB
            max_file_size_mb: Maximum individual file size in MB
            max_files: Maximum number of files in bundle
        """
        self.max_bundle_size_mb = max_bundle_size_mb
        self.max_file_size_mb = max_file_size_mb
        self.max_files = max_files

    def validate(
        self,
        bundle_path: Path,
        expected_hash: Optional[str] = None,
    ) -> ValidationResult:
        """Validate bundle file.

        Args:
            bundle_path: Path to bundle ZIP file
            expected_hash: Optional SHA-256 hash to verify against

        Returns:
            ValidationResult with issues and metadata
        """
        issues: List[ValidationIssue] = []

        # Check file exists and is readable
        if not bundle_path.exists():
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="integrity",
                    message=f"Bundle file not found: {bundle_path}",
                )
            )
            return ValidationResult(is_valid=False, issues=issues)

        if not bundle_path.is_file():
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="integrity",
                    message=f"Bundle path is not a file: {bundle_path}",
                )
            )
            return ValidationResult(is_valid=False, issues=issues)

        # Check bundle size
        bundle_size = bundle_path.stat().st_size
        if bundle_size > self.max_bundle_size_mb * 1024 * 1024:
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="size",
                    message=(
                        f"Bundle size {bundle_size / 1024 / 1024:.2f} MB exceeds "
                        f"maximum {self.max_bundle_size_mb} MB"
                    ),
                )
            )
            return ValidationResult(
                is_valid=False, issues=issues, total_size_bytes=bundle_size
            )

        # Compute bundle hash
        bundle_hash = self._compute_hash(bundle_path)

        # Verify hash if provided
        if expected_hash:
            if bundle_hash != expected_hash:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        category="integrity",
                        message=(
                            "Bundle hash mismatch. "
                            f"Expected: {expected_hash}, Got: {bundle_hash}"
                        ),
                    )
                )
                return ValidationResult(
                    is_valid=False,
                    issues=issues,
                    bundle_hash=bundle_hash,
                    total_size_bytes=bundle_size,
                )

        # Validate ZIP integrity
        try:
            with zipfile.ZipFile(bundle_path, "r") as zf:
                # Test ZIP integrity
                bad_file = zf.testzip()
                if bad_file:
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            category="integrity",
                            message=f"Corrupt file in bundle: {bad_file}",
                        )
                    )
                    return ValidationResult(
                        is_valid=False,
                        issues=issues,
                        bundle_hash=bundle_hash,
                        total_size_bytes=bundle_size,
                    )

                # Validate contents
                file_issues = self._validate_zip_contents(zf)
                issues.extend(file_issues)

                # Check for manifest
                manifest_data = None
                if "bundle.toml" not in zf.namelist():
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            category="schema",
                            message="Bundle missing required bundle.toml manifest",
                        )
                    )
                else:
                    # Validate manifest
                    manifest_issues, manifest_data = self._validate_manifest(zf)
                    issues.extend(manifest_issues)

                # Count artifacts
                artifact_count = 0
                if manifest_data and "artifacts" in manifest_data:
                    artifact_count = len(manifest_data["artifacts"])

        except zipfile.BadZipFile as e:
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="integrity",
                    message=f"Invalid ZIP file: {e}",
                )
            )
            return ValidationResult(
                is_valid=False,
                issues=issues,
                bundle_hash=bundle_hash,
                total_size_bytes=bundle_size,
            )
        except Exception as e:
            logger.error(f"Unexpected error validating bundle: {e}", exc_info=True)
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="integrity",
                    message=f"Unexpected error during validation: {e}",
                )
            )
            return ValidationResult(
                is_valid=False,
                issues=issues,
                bundle_hash=bundle_hash,
                total_size_bytes=bundle_size,
            )

        # Determine overall validity
        is_valid = not any(issue.severity == "error" for issue in issues)

        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            bundle_hash=bundle_hash,
            manifest_data=manifest_data,
            artifact_count=artifact_count,
            total_size_bytes=bundle_size,
        )

    def _compute_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file.

        Args:
            file_path: Path to file

        Returns:
            Hex-encoded SHA-256 hash
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _validate_zip_contents(self, zf: zipfile.ZipFile) -> List[ValidationIssue]:
        """Validate ZIP file contents for security issues.

        Args:
            zf: Open ZipFile object

        Returns:
            List of validation issues found
        """
        issues: List[ValidationIssue] = []
        file_count = 0
        total_uncompressed_size = 0
        max_file_size_bytes = self.max_file_size_mb * 1024 * 1024

        for info in zf.infolist():
            file_count += 1
            file_path = info.filename
            file_size = info.file_size
            compressed_size = info.compress_size

            # Check file count limit
            if file_count > self.max_files:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        category="size",
                        message=f"Too many files in bundle (>{self.max_files})",
                    )
                )
                break

            # Check path traversal (CRITICAL SECURITY)
            path_issues = self._check_path_safety(file_path)
            issues.extend(path_issues)

            # Check individual file size
            if file_size > max_file_size_bytes:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        category="size",
                        message=(
                            f"File too large: {file_path} "
                            f"({file_size / 1024 / 1024:.2f} MB > {self.max_file_size_mb} MB)"
                        ),
                        file_path=file_path,
                    )
                )

            # Check for zip bomb (compression ratio)
            if compressed_size > 0:
                compression_ratio = file_size / compressed_size
                if compression_ratio > 100:
                    issues.append(
                        ValidationIssue(
                            severity="warning",
                            category="security",
                            message=(
                                f"Suspicious compression ratio: {compression_ratio:.1f}:1 "
                                f"(possible zip bomb)"
                            ),
                            file_path=file_path,
                        )
                    )

            # Check for suspicious file extensions
            file_path_obj = Path(file_path)
            if file_path_obj.suffix.lower() in SUSPICIOUS_EXTENSIONS:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        category="security",
                        message=f"Suspicious file extension: {file_path_obj.suffix}",
                        file_path=file_path,
                    )
                )

            total_uncompressed_size += file_size

        # Check total uncompressed size (zip bomb detection)
        if total_uncompressed_size > self.max_bundle_size_mb * 1024 * 1024 * 10:
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="security",
                    message=(
                        f"Total uncompressed size {total_uncompressed_size / 1024 / 1024:.2f} MB "
                        f"exceeds safe limit (possible zip bomb)"
                    ),
                )
            )

        return issues

    def _check_path_safety(self, file_path: str) -> List[ValidationIssue]:
        """Check file path for security issues.

        Args:
            file_path: Path from ZIP entry

        Returns:
            List of validation issues
        """
        issues: List[ValidationIssue] = []

        # Normalize path
        normalized = Path(file_path).as_posix()

        # Check for absolute paths
        if normalized.startswith("/") or (
            len(normalized) > 1 and normalized[1] == ":"
        ):
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="security",
                    message="Absolute path detected (security risk)",
                    file_path=file_path,
                )
            )

        # Check for parent directory references
        if ".." in normalized.split("/"):
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="security",
                    message="Parent directory reference detected (path traversal attack)",
                    file_path=file_path,
                )
            )

        # Check for symlinks (if possible)
        # Note: ZIP doesn't preserve symlinks by default, but check anyway
        if normalized.startswith("../") or "/../" in normalized:
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="security",
                    message="Invalid path traversal sequence",
                    file_path=file_path,
                )
            )

        # Check path component length
        for component in Path(file_path).parts:
            if len(component) > MAX_PATH_LENGTH:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        category="schema",
                        message=f"Path component too long (>{MAX_PATH_LENGTH} chars)",
                        file_path=file_path,
                    )
                )

        # Check for hidden files (potential security risk)
        if any(part.startswith(".") and part != "." for part in Path(file_path).parts):
            issues.append(
                ValidationIssue(
                    severity="info",
                    category="security",
                    message="Hidden file detected",
                    file_path=file_path,
                )
            )

        return issues

    def _validate_manifest(
        self, zf: zipfile.ZipFile
    ) -> tuple[List[ValidationIssue], Optional[Dict[str, Any]]]:
        """Validate bundle.toml manifest.

        Args:
            zf: Open ZipFile object

        Returns:
            Tuple of (issues, manifest_data)
        """
        issues: List[ValidationIssue] = []

        try:
            with zf.open("bundle.toml") as f:
                manifest_content = f.read().decode("utf-8")
                manifest_data = toml_loads(manifest_content)

        except Exception as e:
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="schema",
                    message=f"Failed to parse bundle.toml: {e}",
                )
            )
            return issues, None

        # Validate required fields
        if "bundle" not in manifest_data:
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="schema",
                    message="Missing required [bundle] section in manifest",
                )
            )
            return issues, manifest_data

        bundle_section = manifest_data["bundle"]

        # Check required bundle fields
        required_fields = ["name", "version", "created_at", "creator"]
        for field in required_fields:
            if field not in bundle_section:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        category="schema",
                        message=f"Missing required field 'bundle.{field}' in manifest",
                    )
                )

        # Validate artifacts section
        if "artifacts" not in manifest_data:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    category="schema",
                    message="Bundle contains no artifacts",
                )
            )
        else:
            artifacts = manifest_data["artifacts"]
            if not isinstance(artifacts, list):
                issues.append(
                    ValidationIssue(
                        severity="error",
                        category="schema",
                        message="'artifacts' must be a list",
                    )
                )
            else:
                # Validate each artifact
                for idx, artifact in enumerate(artifacts):
                    artifact_issues = self._validate_artifact_entry(artifact, idx)
                    issues.extend(artifact_issues)

                # Check for duplicate artifacts (name + type)
                artifact_keys = set()
                for artifact in artifacts:
                    key = (artifact.get("name"), artifact.get("type"))
                    if key in artifact_keys:
                        issues.append(
                            ValidationIssue(
                                severity="error",
                                category="schema",
                                message=f"Duplicate artifact: {key[0]} ({key[1]})",
                            )
                        )
                    artifact_keys.add(key)

        return issues, manifest_data

    def _validate_artifact_entry(
        self, artifact: Dict[str, Any], index: int
    ) -> List[ValidationIssue]:
        """Validate single artifact entry in manifest.

        Args:
            artifact: Artifact dictionary from manifest
            index: Index of artifact in list

        Returns:
            List of validation issues
        """
        issues: List[ValidationIssue] = []
        prefix = f"artifacts[{index}]"

        # Check required fields
        required_fields = ["name", "type", "path"]
        for field in required_fields:
            if field not in artifact:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        category="schema",
                        message=f"Missing required field '{prefix}.{field}'",
                    )
                )

        # Validate artifact type
        if "type" in artifact:
            artifact_type = artifact["type"]
            if artifact_type not in ALLOWED_ARTIFACT_TYPES:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        category="schema",
                        message=(
                            f"Invalid artifact type '{artifact_type}' in {prefix}. "
                            f"Must be one of: {', '.join(ALLOWED_ARTIFACT_TYPES)}"
                        ),
                    )
                )

        # Validate name (no path separators)
        if "name" in artifact:
            name = artifact["name"]
            if not name or "/" in name or "\\" in name or ".." in name:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        category="security",
                        message=f"Invalid artifact name in {prefix}: {name}",
                    )
                )

        # Validate path (relative, no traversal)
        if "path" in artifact:
            path = artifact["path"]
            path_issues = self._check_path_safety(path)
            for issue in path_issues:
                issue.message = f"{prefix}: {issue.message}"
                issues.append(issue)

        return issues
