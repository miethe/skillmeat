"""Prerequisite checking for web development environment.

This module provides functionality to detect and validate Node.js, pnpm,
and other dependencies required for the web interface.
"""

import logging
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class VersionInfo:
    """Version information for a detected tool."""

    version: str
    """Semantic version string (e.g., '18.20.0')"""

    path: str
    """Absolute path to the executable"""

    raw_output: str
    """Raw output from version command"""

    @property
    def major(self) -> Optional[int]:
        """Extract major version number."""
        match = re.match(r"^v?(\d+)", self.version)
        return int(match.group(1)) if match else None

    @property
    def minor(self) -> Optional[int]:
        """Extract minor version number."""
        match = re.match(r"^v?\d+\.(\d+)", self.version)
        return int(match.group(1)) if match else None

    @property
    def patch(self) -> Optional[int]:
        """Extract patch version number."""
        match = re.match(r"^v?\d+\.\d+\.(\d+)", self.version)
        return int(match.group(1)) if match else None

    def meets_requirement(self, min_version: str) -> bool:
        """Check if this version meets a minimum requirement.

        Args:
            min_version: Minimum version string (e.g., '18.18.0')

        Returns:
            True if version meets or exceeds requirement
        """
        # Parse minimum version
        match = re.match(r"^v?(\d+)\.(\d+)\.(\d+)", min_version)
        if not match:
            return False

        min_major, min_minor, min_patch = map(int, match.groups())

        # Compare versions
        if self.major is None:
            return False

        if self.major > min_major:
            return True
        if self.major < min_major:
            return False

        # Major versions equal, check minor
        if self.minor is None:
            return False

        if self.minor > min_minor:
            return True
        if self.minor < min_minor:
            return False

        # Minor versions equal, check patch
        if self.patch is None:
            return False

        return self.patch >= min_patch


class RequirementsChecker:
    """Check for Node.js, pnpm, and other web development prerequisites."""

    # Minimum required versions
    MIN_NODE_VERSION = "18.18.0"
    MIN_PNPM_VERSION = "8.0.0"

    def __init__(self):
        """Initialize requirements checker."""
        self._node_info: Optional[VersionInfo] = None
        self._pnpm_info: Optional[VersionInfo] = None
        self._python_info: Optional[VersionInfo] = None

    def detect_node(self) -> Optional[VersionInfo]:
        """Detect Node.js installation and version.

        Returns:
            VersionInfo if Node.js is detected, None otherwise
        """
        if self._node_info is not None:
            return self._node_info

        # Find node executable
        node_path = shutil.which("node")
        if not node_path:
            logger.debug("Node.js not found in PATH")
            return None

        try:
            # Get version
            result = subprocess.run(
                [node_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            )

            version_str = result.stdout.strip()
            # Remove 'v' prefix if present
            version_clean = version_str.lstrip("v")

            self._node_info = VersionInfo(
                version=version_clean,
                path=node_path,
                raw_output=version_str,
            )

            logger.debug(f"Detected Node.js {version_clean} at {node_path}")
            return self._node_info

        except (subprocess.SubprocessError, OSError) as e:
            logger.warning(f"Failed to detect Node.js version: {e}")
            return None

    def detect_pnpm(self) -> Optional[VersionInfo]:
        """Detect pnpm installation and version.

        Returns:
            VersionInfo if pnpm is detected, None otherwise
        """
        if self._pnpm_info is not None:
            return self._pnpm_info

        # Find pnpm executable
        pnpm_path = shutil.which("pnpm")
        if not pnpm_path:
            logger.debug("pnpm not found in PATH")
            return None

        try:
            # Get version
            result = subprocess.run(
                [pnpm_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            )

            version_str = result.stdout.strip()

            self._pnpm_info = VersionInfo(
                version=version_str,
                path=pnpm_path,
                raw_output=version_str,
            )

            logger.debug(f"Detected pnpm {version_str} at {pnpm_path}")
            return self._pnpm_info

        except (subprocess.SubprocessError, OSError) as e:
            logger.warning(f"Failed to detect pnpm version: {e}")
            return None

    def detect_python(self) -> Optional[VersionInfo]:
        """Detect Python installation and version.

        Returns:
            VersionInfo for current Python interpreter
        """
        if self._python_info is not None:
            return self._python_info

        import sys

        # Get Python version
        version_str = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        python_path = sys.executable

        self._python_info = VersionInfo(
            version=version_str,
            path=python_path,
            raw_output=version_str,
        )

        logger.debug(f"Detected Python {version_str} at {python_path}")
        return self._python_info

    def check_node(self) -> Tuple[bool, Optional[str]]:
        """Check if Node.js meets minimum requirements.

        Returns:
            Tuple of (meets_requirement, error_message)
        """
        node_info = self.detect_node()

        if node_info is None:
            return False, (
                f"Node.js not found. Please install Node.js {self.MIN_NODE_VERSION} or higher.\n"
                f"Download from: https://nodejs.org/"
            )

        if not node_info.meets_requirement(self.MIN_NODE_VERSION):
            return False, (
                f"Node.js version {node_info.version} is too old. "
                f"Please upgrade to {self.MIN_NODE_VERSION} or higher.\n"
                f"Current: {node_info.version} at {node_info.path}"
            )

        return True, None

    def check_pnpm(self) -> Tuple[bool, Optional[str]]:
        """Check if pnpm meets minimum requirements.

        Returns:
            Tuple of (meets_requirement, error_message)
        """
        pnpm_info = self.detect_pnpm()

        if pnpm_info is None:
            return False, (
                f"pnpm not found. Please install pnpm {self.MIN_PNPM_VERSION} or higher.\n"
                f"Install with: npm install -g pnpm\n"
                f"Or visit: https://pnpm.io/installation"
            )

        if not pnpm_info.meets_requirement(self.MIN_PNPM_VERSION):
            return False, (
                f"pnpm version {pnpm_info.version} is too old. "
                f"Please upgrade to {self.MIN_PNPM_VERSION} or higher.\n"
                f"Current: {pnpm_info.version} at {pnpm_info.path}\n"
                f"Upgrade with: pnpm add -g pnpm"
            )

        return True, None

    def check_web_directory(self) -> Tuple[bool, Optional[str]]:
        """Check if web directory exists and has required files.

        Returns:
            Tuple of (valid, error_message)
        """
        # Get web directory path (relative to package root)
        import skillmeat

        package_root = Path(skillmeat.__file__).parent
        web_dir = package_root / "web"

        if not web_dir.exists():
            return False, (
                f"Web directory not found at {web_dir}\n"
                f"The Next.js application may not be installed correctly."
            )

        # Check for required files
        required_files = ["package.json", "next.config.js"]
        missing_files = [f for f in required_files if not (web_dir / f).exists()]

        if missing_files:
            return False, (
                f"Missing required files in web directory: {', '.join(missing_files)}\n"
                f"The Next.js application may not be installed correctly."
            )

        return True, None

    def check_web_dependencies(self) -> Tuple[bool, Optional[str]]:
        """Check if web dependencies are installed.

        Returns:
            Tuple of (installed, error_message)
        """
        # Get web directory path
        import skillmeat

        package_root = Path(skillmeat.__file__).parent
        web_dir = package_root / "web"
        node_modules = web_dir / "node_modules"

        if not node_modules.exists():
            return False, (
                f"Web dependencies not installed.\n"
                f"Run 'pnpm install' in {web_dir}"
            )

        return True, None

    def check_all(self) -> Tuple[bool, list[str]]:
        """Run all requirement checks.

        Returns:
            Tuple of (all_passed, list of error messages)
        """
        errors = []

        # Check Node.js
        node_ok, node_error = self.check_node()
        if not node_ok:
            errors.append(node_error)

        # Check pnpm
        pnpm_ok, pnpm_error = self.check_pnpm()
        if not pnpm_ok:
            errors.append(pnpm_error)

        # Check web directory
        web_ok, web_error = self.check_web_directory()
        if not web_ok:
            errors.append(web_error)
        else:
            # Only check dependencies if web directory is valid
            deps_ok, deps_error = self.check_web_dependencies()
            if not deps_ok:
                errors.append(deps_error)

        return len(errors) == 0, errors
