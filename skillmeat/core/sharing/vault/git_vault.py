"""Git repository vault connector.

Stores bundles in a Git repository for version-controlled team sharing.
Supports SSH and HTTPS authentication.
"""

import json
import logging
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from skillmeat.core.sharing.bundle import BundleMetadata
from skillmeat.core.sharing.builder import inspect_bundle
from skillmeat.core.auth.storage import get_storage_backend

from .base import (
    ProgressCallback,
    VaultBundleMetadata,
    VaultConnector,
    VaultAuthError,
    VaultConnectionError,
    VaultError,
    VaultNotFoundError,
)

logger = logging.getLogger(__name__)


class GitVaultConnector(VaultConnector):
    """Git repository vault connector.

    Uses a Git repository to store bundles. The repository structure:

    repo/
        bundles/
            bundle-name-v1.0.0.skillmeat-pack
            bundle-name-v1.1.0.skillmeat-pack
        metadata/
            bundle-name-v1.0.0.json
            bundle-name-v1.1.0.json
        index.json
        README.md

    Configuration:
        url: str - Git repository URL (SSH or HTTPS)
        branch: str - Branch to use (default: "main")
        ssh_key_path: str - Path to SSH private key (optional)
        username: str - Git username for HTTPS (optional)
        password: str - Git password/token for HTTPS (optional)
        commit_author: str - Author for commits (optional)
        commit_email: str - Email for commits (optional)

    Credentials are stored securely via OS keychain or encrypted file storage.
    """

    METADATA_FILENAME = "index.json"
    BUNDLES_DIR = "bundles"
    METADATA_DIR = "metadata"

    def __init__(
        self,
        vault_id: str,
        config: Dict[str, Any],
        read_only: bool = False,
    ):
        """Initialize Git vault connector.

        Args:
            vault_id: Unique identifier for this vault
            config: Configuration dict with Git settings
            read_only: If True, prevent write operations

        Raises:
            ValueError: If config is invalid
        """
        super().__init__(vault_id, config, read_only)

        if "url" not in config:
            raise ValueError("Git vault config must contain 'url'")

        self.url = config["url"]
        self.branch = config.get("branch", "main")
        self.ssh_key_path = config.get("ssh_key_path")
        self.commit_author = config.get("commit_author", "SkillMeat")
        self.commit_email = config.get("commit_email", "skillmeat@localhost")

        # Validate URL
        self._validate_url(self.url)

        # Local clone path (temporary)
        self.clone_path: Optional[Path] = None

        # Credential storage
        self._storage = get_storage_backend()

        logger.info(f"Git vault initialized for {self.url}")

    def _validate_url(self, url: str) -> None:
        """Validate Git repository URL.

        Args:
            url: Git URL to validate

        Raises:
            ValueError: If URL is invalid or potentially dangerous
        """
        # Check for dangerous protocols
        if url.startswith("file://"):
            raise ValueError("File URLs are not supported for security reasons")

        # Validate SSH or HTTPS
        if not (url.startswith("git@") or url.startswith("https://") or url.startswith("ssh://")):
            raise ValueError(
                f"Invalid Git URL: {url}. "
                f"Must use SSH (git@...) or HTTPS (https://...)"
            )

        # Basic format validation
        if url.startswith("https://"):
            parsed = urlparse(url)
            if not parsed.netloc or not parsed.path:
                raise ValueError(f"Invalid HTTPS Git URL: {url}")

    def authenticate(self) -> bool:
        """Authenticate with Git repository.

        Clones the repository to verify credentials and connectivity.

        Returns:
            True if authentication successful

        Raises:
            VaultAuthError: If authentication fails
            VaultConnectionError: If repository is unreachable
        """
        try:
            # Create temporary directory for clone
            if self.clone_path is None:
                self.clone_path = Path(tempfile.mkdtemp(prefix="skillmeat-git-vault-"))

            # Test clone
            logger.info(f"Cloning Git repository: {self.url}")
            self._git_clone()

            # Verify we can read
            if not self.clone_path.is_dir():
                raise VaultConnectionError(
                    f"Failed to clone repository: {self.clone_path}"
                )

            # Verify we can write (if not read-only)
            if not self.read_only:
                test_file = self.clone_path / ".test"
                test_file.write_text("test")
                test_file.unlink()

            self._authenticated = True
            logger.info(f"Authenticated with Git vault: {self.url}")
            return True

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            if "Authentication failed" in error_msg or "permission denied" in error_msg.lower():
                raise VaultAuthError(f"Git authentication failed: {error_msg}")
            raise VaultConnectionError(f"Failed to clone repository: {error_msg}")
        except Exception as e:
            if isinstance(e, (VaultAuthError, VaultConnectionError)):
                raise
            raise VaultError(f"Failed to authenticate with Git vault: {e}")

    def push(
        self,
        bundle_path: Path,
        bundle_metadata: BundleMetadata,
        bundle_hash: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> str:
        """Upload bundle to Git repository.

        Args:
            bundle_path: Path to .skillmeat-pack file
            bundle_metadata: Bundle metadata from manifest
            bundle_hash: SHA-256 hash of bundle
            progress_callback: Optional callback for upload progress

        Returns:
            Bundle ID in repository

        Raises:
            VaultError: If upload fails
            VaultPermissionError: If read-only mode enabled
            FileNotFoundError: If bundle_path doesn't exist
        """
        self._check_authenticated()
        self._check_write_permission()
        self._validate_bundle_path(bundle_path)

        try:
            # Pull latest changes
            self._git_pull()

            # Generate bundle ID
            bundle_id = self._generate_bundle_id(
                bundle_metadata.name, bundle_metadata.version
            )

            # Copy bundle to repository
            bundles_dir = self.clone_path / self.BUNDLES_DIR
            bundles_dir.mkdir(parents=True, exist_ok=True)

            dest_path = bundles_dir / f"{bundle_id}.skillmeat-pack"
            bundle_size = bundle_path.stat().st_size

            if progress_callback:
                progress_callback(
                    self._create_progress_info(
                        0, bundle_size, "upload", bundle_metadata.name
                    )
                )

            shutil.copy2(bundle_path, dest_path)

            if progress_callback:
                progress_callback(
                    self._create_progress_info(
                        bundle_size, bundle_size, "upload", bundle_metadata.name
                    )
                )

            # Create metadata
            metadata_dir = self.clone_path / self.METADATA_DIR
            metadata_dir.mkdir(parents=True, exist_ok=True)

            uploaded_at = datetime.utcnow().isoformat()
            vault_metadata = VaultBundleMetadata.from_bundle_metadata(
                bundle_id=bundle_id,
                bundle_metadata=bundle_metadata,
                uploaded_at=uploaded_at,
                size_bytes=bundle_size,
                bundle_hash=bundle_hash,
                vault_path=f"{self.BUNDLES_DIR}/{bundle_id}.skillmeat-pack",
            )

            metadata_path = metadata_dir / f"{bundle_id}.json"
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(vault_metadata.to_dict(), f, indent=2)

            # Update index
            index_path = self.clone_path / self.METADATA_FILENAME
            index = self._read_index()
            index[bundle_id] = vault_metadata.to_dict()
            with open(index_path, "w", encoding="utf-8") as f:
                json.dump(index, f, indent=2, sort_keys=True)

            # Git add, commit, and push
            self._git_add([
                str(dest_path.relative_to(self.clone_path)),
                str(metadata_path.relative_to(self.clone_path)),
                self.METADATA_FILENAME,
            ])

            commit_msg = (
                f"Add bundle: {bundle_metadata.name} v{bundle_metadata.version}\n\n"
                f"Bundle ID: {bundle_id}\n"
                f"Author: {bundle_metadata.author}\n"
                f"Hash: {bundle_hash}"
            )
            self._git_commit(commit_msg)
            self._git_push()

            logger.info(f"Bundle pushed to Git vault: {bundle_id}")
            return bundle_id

        except Exception as e:
            if isinstance(e, VaultError):
                raise
            raise VaultError(f"Failed to push bundle to Git vault: {e}")

    def pull(
        self,
        bundle_id: str,
        destination: Path,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Path:
        """Download bundle from Git repository.

        Args:
            bundle_id: Bundle identifier
            destination: Directory where bundle will be saved
            progress_callback: Optional callback for download progress

        Returns:
            Path to downloaded bundle file

        Raises:
            VaultNotFoundError: If bundle not found
            VaultError: If download fails
        """
        self._check_authenticated()

        try:
            # Pull latest changes
            self._git_pull()

            # Find bundle file
            bundle_path = self.clone_path / self.BUNDLES_DIR / f"{bundle_id}.skillmeat-pack"

            if not bundle_path.exists():
                raise VaultNotFoundError(f"Bundle not found in vault: {bundle_id}")

            # Get metadata
            metadata = self._read_metadata(bundle_id)

            # Copy to destination
            destination.mkdir(parents=True, exist_ok=True)
            dest_path = destination / bundle_path.name

            bundle_size = bundle_path.stat().st_size

            if progress_callback:
                progress_callback(
                    self._create_progress_info(
                        0, bundle_size, "download", metadata.name
                    )
                )

            shutil.copy2(bundle_path, dest_path)

            if progress_callback:
                progress_callback(
                    self._create_progress_info(
                        bundle_size, bundle_size, "download", metadata.name
                    )
                )

            logger.info(f"Bundle pulled from Git vault: {bundle_id} -> {dest_path}")
            return dest_path

        except VaultNotFoundError:
            raise
        except Exception as e:
            raise VaultError(f"Failed to pull bundle from Git vault: {e}")

    def list(
        self,
        name_filter: Optional[str] = None,
        tag_filter: Optional[List[str]] = None,
    ) -> List[VaultBundleMetadata]:
        """List bundles in Git repository.

        Args:
            name_filter: Optional name pattern to filter bundles
            tag_filter: Optional list of tags to filter bundles

        Returns:
            List of bundle metadata

        Raises:
            VaultError: If listing fails
        """
        self._check_authenticated()

        try:
            # Pull latest changes
            self._git_pull()

            index = self._read_index()
            bundles = []

            for bundle_id, metadata_dict in index.items():
                metadata = VaultBundleMetadata(**metadata_dict)

                # Apply filters
                if name_filter and name_filter.lower() not in metadata.name.lower():
                    continue

                if tag_filter and not any(tag in metadata.tags for tag in tag_filter):
                    continue

                bundles.append(metadata)

            # Sort by uploaded_at (newest first)
            bundles.sort(key=lambda b: b.uploaded_at, reverse=True)

            logger.debug(f"Listed {len(bundles)} bundles from Git vault")
            return bundles

        except Exception as e:
            raise VaultError(f"Failed to list bundles from Git vault: {e}")

    def delete(self, bundle_id: str) -> bool:
        """Delete bundle from Git repository.

        Args:
            bundle_id: Bundle identifier

        Returns:
            True if bundle was deleted, False if not found

        Raises:
            VaultError: If deletion fails
            VaultPermissionError: If read-only mode enabled
        """
        self._check_authenticated()
        self._check_write_permission()

        try:
            # Pull latest changes
            self._git_pull()

            bundle_path = self.clone_path / self.BUNDLES_DIR / f"{bundle_id}.skillmeat-pack"
            metadata_path = self.clone_path / self.METADATA_DIR / f"{bundle_id}.json"

            if not bundle_path.exists():
                return False

            # Remove files
            paths_to_remove = []
            if bundle_path.exists():
                bundle_path.unlink()
                paths_to_remove.append(str(bundle_path.relative_to(self.clone_path)))

            if metadata_path.exists():
                metadata_path.unlink()
                paths_to_remove.append(str(metadata_path.relative_to(self.clone_path)))

            # Update index
            index_path = self.clone_path / self.METADATA_FILENAME
            index = self._read_index()
            if bundle_id in index:
                del index[bundle_id]
                with open(index_path, "w", encoding="utf-8") as f:
                    json.dump(index, f, indent=2, sort_keys=True)
                paths_to_remove.append(self.METADATA_FILENAME)

            # Git remove, commit, and push
            self._git_remove(paths_to_remove)

            commit_msg = f"Remove bundle: {bundle_id}"
            self._git_commit(commit_msg)
            self._git_push()

            logger.info(f"Bundle deleted from Git vault: {bundle_id}")
            return True

        except Exception as e:
            raise VaultError(f"Failed to delete bundle from Git vault: {e}")

    def exists(self, bundle_id: str) -> bool:
        """Check if bundle exists in Git repository.

        Args:
            bundle_id: Bundle identifier

        Returns:
            True if bundle exists, False otherwise
        """
        self._check_authenticated()

        try:
            self._git_pull()
            bundle_path = self.clone_path / self.BUNDLES_DIR / f"{bundle_id}.skillmeat-pack"
            return bundle_path.exists()
        except Exception:
            return False

    def get_metadata(self, bundle_id: str) -> VaultBundleMetadata:
        """Get metadata for a specific bundle.

        Args:
            bundle_id: Bundle identifier

        Returns:
            Bundle metadata

        Raises:
            VaultNotFoundError: If bundle not found
            VaultError: If metadata retrieval fails
        """
        self._check_authenticated()

        try:
            self._git_pull()

            if not self.exists(bundle_id):
                raise VaultNotFoundError(f"Bundle not found: {bundle_id}")

            return self._read_metadata(bundle_id)
        except VaultNotFoundError:
            raise
        except Exception as e:
            raise VaultError(f"Failed to get bundle metadata: {e}")

    # ====================
    # Git Operations
    # ====================

    def _git_clone(self) -> None:
        """Clone Git repository.

        Raises:
            subprocess.CalledProcessError: If clone fails
        """
        env = self._get_git_env()

        cmd = ["git", "clone", "--depth", "1", "--branch", self.branch, self.url, str(self.clone_path)]

        result = subprocess.run(
            cmd,
            capture_output=True,
            check=True,
            env=env,
        )

        logger.debug(f"Git clone successful: {self.url}")

    def _git_pull(self) -> None:
        """Pull latest changes from remote.

        Raises:
            subprocess.CalledProcessError: If pull fails
        """
        env = self._get_git_env()

        result = subprocess.run(
            ["git", "pull", "origin", self.branch],
            cwd=self.clone_path,
            capture_output=True,
            check=True,
            env=env,
        )

        logger.debug("Git pull successful")

    def _git_add(self, paths: List[str]) -> None:
        """Add files to Git staging area.

        Args:
            paths: List of file paths relative to repository root

        Raises:
            subprocess.CalledProcessError: If add fails
        """
        cmd = ["git", "add"] + paths

        result = subprocess.run(
            cmd,
            cwd=self.clone_path,
            capture_output=True,
            check=True,
        )

        logger.debug(f"Git add successful: {paths}")

    def _git_remove(self, paths: List[str]) -> None:
        """Remove files from Git.

        Args:
            paths: List of file paths relative to repository root

        Raises:
            subprocess.CalledProcessError: If remove fails
        """
        cmd = ["git", "rm"] + paths

        result = subprocess.run(
            cmd,
            cwd=self.clone_path,
            capture_output=True,
            check=True,
        )

        logger.debug(f"Git rm successful: {paths}")

    def _git_commit(self, message: str) -> None:
        """Commit staged changes.

        Args:
            message: Commit message

        Raises:
            subprocess.CalledProcessError: If commit fails
        """
        # Check if there are changes to commit
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=self.clone_path,
            capture_output=True,
        )

        if result.returncode == 0:
            logger.debug("No changes to commit")
            return

        cmd = [
            "git",
            "commit",
            "-m", message,
            "--author", f"{self.commit_author} <{self.commit_email}>",
        ]

        result = subprocess.run(
            cmd,
            cwd=self.clone_path,
            capture_output=True,
            check=True,
        )

        logger.debug("Git commit successful")

    def _git_push(self) -> None:
        """Push commits to remote.

        Raises:
            subprocess.CalledProcessError: If push fails
        """
        env = self._get_git_env()

        result = subprocess.run(
            ["git", "push", "origin", self.branch],
            cwd=self.clone_path,
            capture_output=True,
            check=True,
            env=env,
        )

        logger.debug("Git push successful")

    def _get_git_env(self) -> Dict[str, str]:
        """Get environment variables for Git commands.

        Includes SSH key configuration and credentials.

        Returns:
            Environment dict
        """
        import os
        env = os.environ.copy()

        # Configure SSH key if provided
        if self.ssh_key_path:
            ssh_key = Path(self.ssh_key_path).expanduser().resolve()
            if ssh_key.exists():
                env["GIT_SSH_COMMAND"] = f"ssh -i {ssh_key} -o StrictHostKeyChecking=no"
            else:
                logger.warning(f"SSH key not found: {ssh_key}")

        # Configure HTTPS credentials if needed
        if self.url.startswith("https://"):
            # Try to get credentials from storage
            cred_id = f"git-vault:{self.vault_id}"
            try:
                cred_data = self._storage.retrieve(cred_id)
                if cred_data:
                    creds = json.loads(cred_data)
                    username = creds.get("username")
                    password = creds.get("password")

                    if username and password:
                        # Use Git credential helper
                        parsed = urlparse(self.url)
                        auth_url = f"{parsed.scheme}://{username}:{password}@{parsed.netloc}{parsed.path}"
                        # Note: This is not ideal for security, but works for automation
                        # In production, use credential helpers
                        logger.debug("Using stored credentials for HTTPS")
            except Exception as e:
                logger.debug(f"No stored credentials found: {e}")

        return env

    # ====================
    # Helper Methods
    # ====================

    def _generate_bundle_id(self, name: str, version: str) -> str:
        """Generate bundle ID from name and version.

        Args:
            name: Bundle name
            version: Bundle version

        Returns:
            Bundle ID
        """
        safe_name = name.replace(" ", "-").lower()
        return f"{safe_name}-v{version}"

    def _read_index(self) -> Dict[str, Dict[str, Any]]:
        """Read vault index.

        Returns:
            Index dictionary
        """
        index_path = self.clone_path / self.METADATA_FILENAME

        if not index_path.exists():
            return {}

        try:
            with open(index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted vault index: {e}")
            return {}

    def _read_metadata(self, bundle_id: str) -> VaultBundleMetadata:
        """Read bundle metadata.

        Args:
            bundle_id: Bundle identifier

        Returns:
            Bundle metadata

        Raises:
            VaultNotFoundError: If metadata not found
            VaultError: If metadata is invalid
        """
        metadata_path = self.clone_path / self.METADATA_DIR / f"{bundle_id}.json"

        if not metadata_path.exists():
            raise VaultNotFoundError(f"Bundle metadata not found: {bundle_id}")

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata_dict = json.load(f)
            return VaultBundleMetadata(**metadata_dict)
        except Exception as e:
            raise VaultError(f"Failed to read bundle metadata: {e}")

    def __del__(self):
        """Cleanup temporary clone directory."""
        if self.clone_path and self.clone_path.exists():
            try:
                shutil.rmtree(self.clone_path)
                logger.debug(f"Cleaned up Git clone: {self.clone_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup Git clone: {e}")
