"""Local file system vault connector.

Simple connector for testing and local team sharing via shared directories.
No authentication required.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from skillmeat.core.sharing.bundle import BundleMetadata
from skillmeat.core.sharing.builder import inspect_bundle

from .base import (
    ProgressCallback,
    VaultBundleMetadata,
    VaultConnector,
    VaultError,
    VaultNotFoundError,
)

logger = logging.getLogger(__name__)


class LocalVaultConnector(VaultConnector):
    """Local file system vault connector.

    Stores bundles in a local directory structure:

    vault_path/
        bundles/
            bundle-name-v1.0.0.skillmeat-pack
            bundle-name-v1.1.0.skillmeat-pack
        metadata/
            bundle-name-v1.0.0.json
            bundle-name-v1.1.0.json
        index.json  # Index of all bundles

    Configuration:
        path: str - Directory path for vault storage
    """

    METADATA_FILENAME = "index.json"

    def __init__(
        self,
        vault_id: str,
        config: Dict[str, Any],
        read_only: bool = False,
    ):
        """Initialize local vault connector.

        Args:
            vault_id: Unique identifier for this vault
            config: Configuration dict with 'path' key
            read_only: If True, prevent write operations

        Raises:
            ValueError: If config is invalid
        """
        super().__init__(vault_id, config, read_only)

        if "path" not in config:
            raise ValueError("Local vault config must contain 'path'")

        self.vault_path = Path(config["path"]).expanduser().resolve()
        self.bundles_dir = self.vault_path / "bundles"
        self.metadata_dir = self.vault_path / "metadata"
        self.index_path = self.vault_path / self.METADATA_FILENAME

        logger.info(f"Local vault initialized at {self.vault_path}")

    def authenticate(self) -> bool:
        """Authenticate with vault (no-op for local vault).

        Creates directory structure if it doesn't exist (unless read-only).

        Returns:
            True always (no authentication needed)

        Raises:
            VaultError: If directory creation fails
        """
        try:
            # Check if vault path exists
            if not self.vault_path.exists():
                if self.read_only:
                    raise VaultError(
                        f"Vault directory does not exist: {self.vault_path}"
                    )

                # Create directory structure
                self.vault_path.mkdir(parents=True, exist_ok=True)
                self.bundles_dir.mkdir(parents=True, exist_ok=True)
                self.metadata_dir.mkdir(parents=True, exist_ok=True)

                # Create empty index
                self._write_index({})
                logger.info(f"Created local vault at {self.vault_path}")
            else:
                # Ensure subdirectories exist
                if not self.read_only:
                    self.bundles_dir.mkdir(parents=True, exist_ok=True)
                    self.metadata_dir.mkdir(parents=True, exist_ok=True)

            # Verify we can read
            if not self.vault_path.is_dir():
                raise VaultError(f"Vault path is not a directory: {self.vault_path}")

            # Verify we can write (if not read-only)
            if not self.read_only:
                test_file = self.vault_path / ".test"
                try:
                    test_file.write_text("test")
                    test_file.unlink()
                except Exception as e:
                    raise VaultError(f"Vault directory is not writable: {e}")

                # Create empty index if it doesn't exist
                if not self.index_path.exists():
                    self._write_index({})

            self._authenticated = True
            logger.debug(f"Authenticated with local vault: {self.vault_path}")
            return True

        except Exception as e:
            if isinstance(e, VaultError):
                raise
            raise VaultError(f"Failed to authenticate with local vault: {e}")

    def push(
        self,
        bundle_path: Path,
        bundle_metadata: BundleMetadata,
        bundle_hash: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> str:
        """Upload bundle to local vault.

        Args:
            bundle_path: Path to .skillmeat-pack file
            bundle_metadata: Bundle metadata from manifest
            bundle_hash: SHA-256 hash of bundle
            progress_callback: Optional callback for upload progress

        Returns:
            Bundle ID (filename in vault)

        Raises:
            VaultError: If upload fails
            VaultPermissionError: If read-only mode enabled
            FileNotFoundError: If bundle_path doesn't exist
        """
        self._check_authenticated()
        self._check_write_permission()
        self._validate_bundle_path(bundle_path)

        try:
            # Generate bundle ID
            bundle_id = self._generate_bundle_id(
                bundle_metadata.name, bundle_metadata.version
            )

            # Destination path
            dest_path = self.bundles_dir / f"{bundle_id}.skillmeat-pack"

            # Check if bundle already exists
            if dest_path.exists():
                logger.warning(f"Bundle already exists, overwriting: {bundle_id}")

            # Copy bundle file with progress tracking
            bundle_size = bundle_path.stat().st_size
            chunk_size = 1024 * 1024  # 1MB chunks

            if progress_callback:
                progress_callback(
                    self._create_progress_info(
                        0, bundle_size, "upload", bundle_metadata.name
                    )
                )

            # For local vault, just copy the file
            # (In a real scenario, we might stream with progress)
            shutil.copy2(bundle_path, dest_path)

            if progress_callback:
                progress_callback(
                    self._create_progress_info(
                        bundle_size, bundle_size, "upload", bundle_metadata.name
                    )
                )

            # Create vault metadata
            uploaded_at = datetime.utcnow().isoformat()
            vault_metadata = VaultBundleMetadata.from_bundle_metadata(
                bundle_id=bundle_id,
                bundle_metadata=bundle_metadata,
                uploaded_at=uploaded_at,
                size_bytes=bundle_size,
                bundle_hash=bundle_hash,
                vault_path=str(dest_path),
            )

            # Save metadata
            metadata_path = self.metadata_dir / f"{bundle_id}.json"
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(vault_metadata.to_dict(), f, indent=2)

            # Update index
            self._add_to_index(bundle_id, vault_metadata)

            logger.info(f"Bundle pushed to local vault: {bundle_id}")
            return bundle_id

        except Exception as e:
            if isinstance(e, VaultError):
                raise
            raise VaultError(f"Failed to push bundle to local vault: {e}")

    def pull(
        self,
        bundle_id: str,
        destination: Path,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Path:
        """Download bundle from local vault.

        Args:
            bundle_id: Bundle identifier (filename without extension)
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
            # Find bundle file
            bundle_path = self.bundles_dir / f"{bundle_id}.skillmeat-pack"

            if not bundle_path.exists():
                raise VaultNotFoundError(f"Bundle not found in vault: {bundle_id}")

            # Get metadata for progress
            metadata = self._read_metadata(bundle_id)

            # Destination path
            destination.mkdir(parents=True, exist_ok=True)
            dest_path = destination / bundle_path.name

            # Copy with progress tracking
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

            logger.info(f"Bundle pulled from local vault: {bundle_id} -> {dest_path}")
            return dest_path

        except VaultNotFoundError:
            raise
        except Exception as e:
            raise VaultError(f"Failed to pull bundle from local vault: {e}")

    def list(
        self,
        name_filter: Optional[str] = None,
        tag_filter: Optional[List[str]] = None,
    ) -> List[VaultBundleMetadata]:
        """List bundles in local vault.

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

            logger.debug(f"Listed {len(bundles)} bundles from local vault")
            return bundles

        except Exception as e:
            raise VaultError(f"Failed to list bundles from local vault: {e}")

    def delete(self, bundle_id: str) -> bool:
        """Delete bundle from local vault.

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
            bundle_path = self.bundles_dir / f"{bundle_id}.skillmeat-pack"
            metadata_path = self.metadata_dir / f"{bundle_id}.json"

            if not bundle_path.exists():
                return False

            # Delete bundle file
            bundle_path.unlink()

            # Delete metadata file
            if metadata_path.exists():
                metadata_path.unlink()

            # Remove from index
            self._remove_from_index(bundle_id)

            logger.info(f"Bundle deleted from local vault: {bundle_id}")
            return True

        except Exception as e:
            raise VaultError(f"Failed to delete bundle from local vault: {e}")

    def exists(self, bundle_id: str) -> bool:
        """Check if bundle exists in local vault.

        Args:
            bundle_id: Bundle identifier

        Returns:
            True if bundle exists, False otherwise
        """
        self._check_authenticated()

        bundle_path = self.bundles_dir / f"{bundle_id}.skillmeat-pack"
        return bundle_path.exists()

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

        if not self.exists(bundle_id):
            raise VaultNotFoundError(f"Bundle not found: {bundle_id}")

        return self._read_metadata(bundle_id)

    # ====================
    # Helper Methods
    # ====================

    def _generate_bundle_id(self, name: str, version: str) -> str:
        """Generate bundle ID from name and version.

        Args:
            name: Bundle name
            version: Bundle version

        Returns:
            Bundle ID (e.g., "my-bundle-v1.0.0")
        """
        # Sanitize name
        safe_name = name.replace(" ", "-").lower()
        return f"{safe_name}-v{version}"

    def _read_index(self) -> Dict[str, Dict[str, Any]]:
        """Read vault index.

        Returns:
            Index dictionary mapping bundle_id to metadata
        """
        if not self.index_path.exists():
            return {}

        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted vault index: {e}")
            return {}

    def _write_index(self, index: Dict[str, Dict[str, Any]]) -> None:
        """Write vault index.

        Args:
            index: Index dictionary to write
        """
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, sort_keys=True)

    def _add_to_index(self, bundle_id: str, metadata: VaultBundleMetadata) -> None:
        """Add bundle to index.

        Args:
            bundle_id: Bundle identifier
            metadata: Bundle metadata
        """
        index = self._read_index()
        index[bundle_id] = metadata.to_dict()
        self._write_index(index)

    def _remove_from_index(self, bundle_id: str) -> None:
        """Remove bundle from index.

        Args:
            bundle_id: Bundle identifier
        """
        index = self._read_index()
        if bundle_id in index:
            del index[bundle_id]
            self._write_index(index)

    def _read_metadata(self, bundle_id: str) -> VaultBundleMetadata:
        """Read bundle metadata from file.

        Args:
            bundle_id: Bundle identifier

        Returns:
            Bundle metadata

        Raises:
            VaultNotFoundError: If metadata file not found
            VaultError: If metadata is invalid
        """
        metadata_path = self.metadata_dir / f"{bundle_id}.json"

        if not metadata_path.exists():
            raise VaultNotFoundError(f"Bundle metadata not found: {bundle_id}")

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata_dict = json.load(f)
            return VaultBundleMetadata(**metadata_dict)
        except Exception as e:
            raise VaultError(f"Failed to read bundle metadata: {e}")
