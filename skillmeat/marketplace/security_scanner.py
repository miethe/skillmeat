"""Security scanning for SkillMeat marketplace bundles.

Scans bundles for secrets, malicious patterns, and validates file types
before publishing to marketplace.
"""

import logging
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

from skillmeat.core.sharing.bundle import Bundle

logger = logging.getLogger(__name__)


class SecurityViolationError(Exception):
    """Raised when security scan fails."""

    pass


@dataclass
class ScanResult:
    """Result of security scan.

    Attributes:
        passed: Whether scan passed
        violations: List of security violations found
        warnings: List of warnings
        file_violations: Dict mapping file paths to violation descriptions
    """

    passed: bool
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    file_violations: Dict[str, List[str]] = field(default_factory=dict)

    @property
    def has_violations(self) -> bool:
        """Return True if violations were found."""
        return len(self.violations) > 0

    @property
    def has_warnings(self) -> bool:
        """Return True if warnings were found."""
        return len(self.warnings) > 0


class SecurityScanner:
    """Scans bundles for security issues before marketplace publishing.

    Performs checks for:
    - Secrets (API keys, tokens, passwords)
    - Malicious patterns (eval, exec, shell commands)
    - File type validation
    - Size limits
    """

    # Maximum bundle size (100MB)
    MAX_BUNDLE_SIZE = 100 * 1024 * 1024

    # Maximum artifact count
    MAX_ARTIFACT_COUNT = 1000

    # Allowed file extensions
    ALLOWED_EXTENSIONS = {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".md",
        ".txt",
        ".json",
        ".toml",
        ".yaml",
        ".yml",
        ".html",
        ".css",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".sql",
        ".graphql",
        ".proto",
        ".xml",
        ".csv",
        ".ini",
        ".cfg",
        ".conf",
        ".properties",
    }

    # Blocked file extensions
    BLOCKED_EXTENSIONS = {
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".bin",
        ".app",
        ".deb",
        ".rpm",
        ".msi",
        ".dmg",
        ".pkg",
        ".apk",
        ".ipa",
    }

    # Warning file extensions (allowed but flagged)
    WARNING_EXTENSIONS = {
        ".env",
        ".key",
        ".pem",
        ".cert",
        ".crt",
        ".p12",
        ".pfx",
        ".jks",
    }

    # Secret patterns
    SECRET_PATTERNS = {
        "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
        "aws_secret_key": re.compile(
            r"aws_secret_access_key\s*=\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?",
            re.IGNORECASE,
        ),
        "github_token": re.compile(r"ghp_[a-zA-Z0-9]{36}"),
        "github_oauth": re.compile(r"gho_[a-zA-Z0-9]{36}"),
        "github_app": re.compile(r"(ghu|ghs)_[a-zA-Z0-9]{36}"),
        "slack_token": re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,48}"),
        "slack_webhook": re.compile(
            r"https://hooks\.slack\.com/services/T[a-zA-Z0-9_]{8}/B[a-zA-Z0-9_]{8}/[a-zA-Z0-9_]{24}"
        ),
        "google_api_key": re.compile(r"AIza[0-9A-Za-z\\-_]{35}"),
        "stripe_api_key": re.compile(r"sk_live_[0-9a-zA-Z]{24}"),
        "stripe_restricted_key": re.compile(r"rk_live_[0-9a-zA-Z]{24}"),
        "mailchimp_api_key": re.compile(r"[0-9a-f]{32}-us[0-9]{1,2}"),
        "mailgun_api_key": re.compile(r"key-[0-9a-zA-Z]{32}"),
        "twilio_api_key": re.compile(r"SK[0-9a-fA-F]{32}"),
        "private_key": re.compile(r"-----BEGIN (RSA |EC )?PRIVATE KEY-----"),
        "ssh_private_key": re.compile(r"-----BEGIN OPENSSH PRIVATE KEY-----"),
        "generic_api_key": re.compile(
            r"api[_-]?key\s*[=:]\s*['\"]([a-zA-Z0-9_\-]{20,})['\"]", re.IGNORECASE
        ),
        "generic_secret": re.compile(
            r"secret\s*[=:]\s*['\"]([a-zA-Z0-9_\-]{20,})['\"]", re.IGNORECASE
        ),
        "password": re.compile(
            r"password\s*[=:]\s*['\"]([^'\"]{8,})['\"]", re.IGNORECASE
        ),
        "database_url": re.compile(
            r"(?:postgres|mysql|mongodb)://[^:]+:[^@]+@", re.IGNORECASE
        ),
    }

    # Malicious patterns (language-specific)
    MALICIOUS_PATTERNS = {
        "python": {
            "eval": re.compile(r"\beval\s*\("),
            "exec": re.compile(r"\bexec\s*\("),
            "compile": re.compile(r"\bcompile\s*\("),
            "subprocess_shell": re.compile(
                r"subprocess\.[a-z]+\([^)]*shell\s*=\s*True", re.IGNORECASE
            ),
            "os_system": re.compile(r"\bos\.system\s*\("),
            "pickle_loads": re.compile(r"\bpickle\.loads\s*\("),
        },
        "javascript": {
            "eval": re.compile(r"\beval\s*\("),
            "function_constructor": re.compile(r"new\s+Function\s*\("),
            "child_process": re.compile(r"require\s*\(\s*['\"]child_process['\"]"),
            "vm_run": re.compile(r"vm\.run"),
        },
        "shell": {
            "rm_rf": re.compile(r"\brm\s+-rf\s+/"),
            "curl_pipe_sh": re.compile(r"curl\s+[^|]+\|\s*sh"),
            "wget_pipe_sh": re.compile(r"wget\s+[^|]+\|\s*sh"),
        },
    }

    def __init__(self):
        """Initialize security scanner."""
        pass

    def scan_bundle(self, bundle: Bundle, bundle_path: Path) -> ScanResult:
        """Perform comprehensive security scan on bundle.

        Args:
            bundle: Bundle object to scan
            bundle_path: Path to bundle file

        Returns:
            ScanResult with scan results

        Raises:
            SecurityViolationError: If critical violations found
        """
        result = ScanResult(passed=True)

        # Check size limits
        self._check_size_limits(bundle, bundle_path, result)

        # Check artifact count
        self._check_artifact_count(bundle, result)

        # Validate file types
        self._validate_file_types(bundle, bundle_path, result)

        # Scan for secrets
        self._scan_for_secrets(bundle, bundle_path, result)

        # Scan for malicious patterns
        self._scan_for_malicious_patterns(bundle, bundle_path, result)

        # Determine if scan passed
        result.passed = not result.has_violations

        return result

    def _check_size_limits(
        self, bundle: Bundle, bundle_path: Path, result: ScanResult
    ) -> None:
        """Check bundle size limits.

        Args:
            bundle: Bundle to check
            bundle_path: Path to bundle file
            result: ScanResult to update
        """
        bundle_size = bundle_path.stat().st_size

        if bundle_size > self.MAX_BUNDLE_SIZE:
            size_mb = bundle_size / (1024 * 1024)
            max_mb = self.MAX_BUNDLE_SIZE / (1024 * 1024)
            result.violations.append(
                f"Bundle size {size_mb:.1f}MB exceeds maximum {max_mb:.1f}MB"
            )

    def _check_artifact_count(self, bundle: Bundle, result: ScanResult) -> None:
        """Check artifact count limits.

        Args:
            bundle: Bundle to check
            result: ScanResult to update
        """
        artifact_count = bundle.artifact_count

        if artifact_count > self.MAX_ARTIFACT_COUNT:
            result.violations.append(
                f"Artifact count {artifact_count} exceeds maximum {self.MAX_ARTIFACT_COUNT}"
            )

    def _validate_file_types(
        self, bundle: Bundle, bundle_path: Path, result: ScanResult
    ) -> None:
        """Validate file types in bundle.

        Args:
            bundle: Bundle to check
            bundle_path: Path to bundle file
            result: ScanResult to update
        """
        try:
            with zipfile.ZipFile(bundle_path, "r") as zf:
                for file_info in zf.filelist:
                    file_path = Path(file_info.filename)

                    # Skip directories
                    if file_info.is_dir():
                        continue

                    # Get file extension
                    ext = file_path.suffix.lower()

                    # Check if blocked
                    if ext in self.BLOCKED_EXTENSIONS:
                        result.violations.append(
                            f"Blocked file type: {file_path} (extension {ext} not allowed)"
                        )
                        if str(file_path) not in result.file_violations:
                            result.file_violations[str(file_path)] = []
                        result.file_violations[str(file_path)].append(
                            f"Blocked extension: {ext}"
                        )

                    # Check if warning
                    elif ext in self.WARNING_EXTENSIONS:
                        result.warnings.append(
                            f"Sensitive file type: {file_path} (extension {ext})"
                        )

                    # Check if allowed (or no extension)
                    elif ext and ext not in self.ALLOWED_EXTENSIONS:
                        result.warnings.append(
                            f"Unknown file type: {file_path} (extension {ext})"
                        )

        except Exception as e:
            logger.error(f"Failed to validate file types: {e}")
            result.violations.append(f"Failed to read bundle contents: {e}")

    def _scan_for_secrets(
        self, bundle: Bundle, bundle_path: Path, result: ScanResult
    ) -> None:
        """Scan bundle for secrets and credentials.

        Args:
            bundle: Bundle to scan
            bundle_path: Path to bundle file
            result: ScanResult to update
        """
        try:
            with zipfile.ZipFile(bundle_path, "r") as zf:
                for file_info in zf.filelist:
                    # Skip directories
                    if file_info.is_dir():
                        continue

                    # Skip binary files
                    file_path = Path(file_info.filename)
                    if file_path.suffix.lower() in {
                        ".png",
                        ".jpg",
                        ".jpeg",
                        ".gif",
                        ".ico",
                        ".woff",
                        ".woff2",
                        ".ttf",
                        ".eot",
                    }:
                        continue

                    # Read file content (text files only)
                    try:
                        content = zf.read(file_info.filename).decode(
                            "utf-8", errors="ignore"
                        )
                    except Exception:
                        continue

                    # Scan for secret patterns
                    for secret_type, pattern in self.SECRET_PATTERNS.items():
                        matches = pattern.findall(content)
                        if matches:
                            result.violations.append(
                                f"Potential {secret_type} found in {file_path}"
                            )
                            if str(file_path) not in result.file_violations:
                                result.file_violations[str(file_path)] = []
                            result.file_violations[str(file_path)].append(
                                f"Potential {secret_type}"
                            )

        except Exception as e:
            logger.error(f"Failed to scan for secrets: {e}")
            result.warnings.append(f"Secret scanning failed: {e}")

    def _scan_for_malicious_patterns(
        self, bundle: Bundle, bundle_path: Path, result: ScanResult
    ) -> None:
        """Scan bundle for malicious code patterns.

        Args:
            bundle: Bundle to scan
            bundle_path: Path to bundle file
            result: ScanResult to update
        """
        try:
            with zipfile.ZipFile(bundle_path, "r") as zf:
                for file_info in zf.filelist:
                    # Skip directories
                    if file_info.is_dir():
                        continue

                    file_path = Path(file_info.filename)

                    # Determine language
                    language = self._get_language(file_path)
                    if not language:
                        continue

                    # Read file content
                    try:
                        content = zf.read(file_info.filename).decode(
                            "utf-8", errors="ignore"
                        )
                    except Exception:
                        continue

                    # Scan for malicious patterns
                    patterns = self.MALICIOUS_PATTERNS.get(language, {})
                    for pattern_type, pattern in patterns.items():
                        if pattern.search(content):
                            result.warnings.append(
                                f"Suspicious {pattern_type} pattern in {file_path}"
                            )

        except Exception as e:
            logger.error(f"Failed to scan for malicious patterns: {e}")
            result.warnings.append(f"Malicious pattern scanning failed: {e}")

    def _get_language(self, file_path: Path) -> Optional[str]:
        """Determine programming language from file extension.

        Args:
            file_path: Path to file

        Returns:
            Language identifier or None
        """
        ext = file_path.suffix.lower()

        if ext == ".py":
            return "python"
        elif ext in {".js", ".jsx", ".ts", ".tsx"}:
            return "javascript"
        elif ext in {".sh", ".bash", ".zsh", ".fish"}:
            return "shell"

        return None
