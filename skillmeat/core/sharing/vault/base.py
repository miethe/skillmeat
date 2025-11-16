"""Base vault connector interface and exceptions.

This module defines the abstract base class for vault connectors and
common exceptions used across all vault implementations.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from skillmeat.core.sharing.bundle import BundleMetadata

logger = logging.getLogger(__name__)


# ====================
# Exceptions
# ====================


class VaultError(Exception):
    """Base exception for vault operations."""

    pass


class VaultAuthError(VaultError):
    """Raised when vault authentication fails."""

    pass


class VaultNotFoundError(VaultError):
    """Raised when vault or bundle is not found."""

    pass


class VaultConnectionError(VaultError):
    """Raised when vault connection fails."""

    pass


class VaultPermissionError(VaultError):
    """Raised when vault operation is not permitted."""

    pass


# ====================
# Data Classes
# ====================


@dataclass
class VaultBundleMetadata:
    """Extended metadata for bundles stored in vaults.

    Includes both bundle metadata and vault-specific information.

    Attributes:
        bundle_id: Unique identifier for the bundle in vault
        name: Bundle name from manifest
        version: Bundle version
        description: Bundle description
        author: Bundle author
        created_at: ISO 8601 timestamp of bundle creation
        uploaded_at: ISO 8601 timestamp of vault upload
        size_bytes: Bundle file size in bytes
        bundle_hash: SHA-256 hash of bundle contents
        tags: List of tags for categorization
        vault_path: Path/URL to bundle in vault
        metadata: Additional vault-specific metadata
    """

    bundle_id: str
    name: str
    version: str
    description: str
    author: str
    created_at: str
    uploaded_at: str
    size_bytes: int
    bundle_hash: str
    tags: List[str]
    vault_path: str
    metadata: Dict[str, Any]

    @classmethod
    def from_bundle_metadata(
        cls,
        bundle_id: str,
        bundle_metadata: BundleMetadata,
        uploaded_at: str,
        size_bytes: int,
        bundle_hash: str,
        vault_path: str,
        **kwargs,
    ) -> "VaultBundleMetadata":
        """Create from BundleMetadata object.

        Args:
            bundle_id: Unique identifier in vault
            bundle_metadata: Bundle metadata from manifest
            uploaded_at: ISO 8601 timestamp of upload
            size_bytes: Bundle file size
            bundle_hash: SHA-256 hash of bundle
            vault_path: Path/URL in vault
            **kwargs: Additional vault-specific metadata

        Returns:
            VaultBundleMetadata instance
        """
        return cls(
            bundle_id=bundle_id,
            name=bundle_metadata.name,
            version=bundle_metadata.version,
            description=bundle_metadata.description,
            author=bundle_metadata.author,
            created_at=bundle_metadata.created_at,
            uploaded_at=uploaded_at,
            size_bytes=size_bytes,
            bundle_hash=bundle_hash,
            tags=bundle_metadata.tags,
            vault_path=vault_path,
            metadata=kwargs,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "bundle_id": self.bundle_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "created_at": self.created_at,
            "uploaded_at": self.uploaded_at,
            "size_bytes": self.size_bytes,
            "bundle_hash": self.bundle_hash,
            "tags": self.tags,
            "vault_path": self.vault_path,
            "metadata": self.metadata,
        }


@dataclass
class ProgressInfo:
    """Progress information for upload/download operations.

    Attributes:
        current: Current bytes transferred
        total: Total bytes to transfer
        percentage: Progress percentage (0-100)
        operation: Operation type ("upload" or "download")
        bundle_name: Name of bundle being transferred
    """

    current: int
    total: int
    percentage: float
    operation: str
    bundle_name: str


# Type alias for progress callbacks
ProgressCallback = Callable[[ProgressInfo], None]


# ====================
# Base Connector
# ====================


class VaultConnector(ABC):
    """Abstract base class for vault storage connectors.

    All vault connectors must implement this interface to provide:
    - Bundle upload (push)
    - Bundle download (pull)
    - Bundle listing
    - Bundle deletion
    - Authentication

    Implementations should:
    - Handle retries for network operations
    - Provide progress callbacks for large transfers
    - Validate URLs and file paths
    - Never log credentials
    - Support read-only mode
    """

    def __init__(
        self,
        vault_id: str,
        config: Dict[str, Any],
        read_only: bool = False,
    ):
        """Initialize vault connector.

        Args:
            vault_id: Unique identifier for this vault
            config: Vault-specific configuration dictionary
            read_only: If True, prevent destructive operations
        """
        self.vault_id = vault_id
        self.config = config
        self.read_only = read_only
        self._authenticated = False

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with vault.

        Should validate credentials and test connectivity.

        Returns:
            True if authentication successful

        Raises:
            VaultAuthError: If authentication fails
            VaultConnectionError: If vault is unreachable
        """
        pass

    @abstractmethod
    def push(
        self,
        bundle_path: Path,
        bundle_metadata: BundleMetadata,
        bundle_hash: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> str:
        """Upload bundle to vault.

        Args:
            bundle_path: Path to .skillmeat-pack file
            bundle_metadata: Bundle metadata from manifest
            bundle_hash: SHA-256 hash of bundle
            progress_callback: Optional callback for upload progress

        Returns:
            Bundle ID or URL in vault

        Raises:
            VaultError: If upload fails
            VaultAuthError: If not authenticated
            VaultPermissionError: If read-only mode enabled
            FileNotFoundError: If bundle_path doesn't exist
        """
        pass

    @abstractmethod
    def pull(
        self,
        bundle_id: str,
        destination: Path,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Path:
        """Download bundle from vault.

        Args:
            bundle_id: Bundle identifier or URL in vault
            destination: Directory where bundle will be saved
            progress_callback: Optional callback for download progress

        Returns:
            Path to downloaded bundle file

        Raises:
            VaultNotFoundError: If bundle not found
            VaultError: If download fails
            VaultAuthError: If not authenticated
        """
        pass

    @abstractmethod
    def list(
        self,
        name_filter: Optional[str] = None,
        tag_filter: Optional[List[str]] = None,
    ) -> List[VaultBundleMetadata]:
        """List bundles in vault.

        Args:
            name_filter: Optional name pattern to filter bundles
            tag_filter: Optional list of tags to filter bundles

        Returns:
            List of bundle metadata

        Raises:
            VaultError: If listing fails
            VaultAuthError: If not authenticated
        """
        pass

    @abstractmethod
    def delete(self, bundle_id: str) -> bool:
        """Delete bundle from vault.

        Args:
            bundle_id: Bundle identifier in vault

        Returns:
            True if bundle was deleted, False if not found

        Raises:
            VaultError: If deletion fails
            VaultAuthError: If not authenticated
            VaultPermissionError: If read-only mode enabled
        """
        pass

    @abstractmethod
    def exists(self, bundle_id: str) -> bool:
        """Check if bundle exists in vault.

        Args:
            bundle_id: Bundle identifier in vault

        Returns:
            True if bundle exists, False otherwise

        Raises:
            VaultError: If check fails
            VaultAuthError: If not authenticated
        """
        pass

    @abstractmethod
    def get_metadata(self, bundle_id: str) -> VaultBundleMetadata:
        """Get metadata for a specific bundle.

        Args:
            bundle_id: Bundle identifier in vault

        Returns:
            Bundle metadata

        Raises:
            VaultNotFoundError: If bundle not found
            VaultError: If metadata retrieval fails
            VaultAuthError: If not authenticated
        """
        pass

    def _check_authenticated(self) -> None:
        """Check if connector is authenticated.

        Raises:
            VaultAuthError: If not authenticated
        """
        if not self._authenticated:
            raise VaultAuthError(
                f"Not authenticated with vault '{self.vault_id}'. "
                f"Call authenticate() first."
            )

    def _check_write_permission(self) -> None:
        """Check if write operations are allowed.

        Raises:
            VaultPermissionError: If vault is read-only
        """
        if self.read_only:
            raise VaultPermissionError(
                f"Vault '{self.vault_id}' is read-only. "
                f"Write operations are not permitted."
            )

    def _validate_bundle_path(self, bundle_path: Path) -> None:
        """Validate bundle file path.

        Args:
            bundle_path: Path to validate

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not a valid bundle
        """
        if not bundle_path.exists():
            raise FileNotFoundError(f"Bundle file not found: {bundle_path}")

        if not bundle_path.is_file():
            raise ValueError(f"Bundle path is not a file: {bundle_path}")

        if not bundle_path.suffix == ".skillmeat-pack":
            logger.warning(
                f"Bundle file does not have .skillmeat-pack extension: {bundle_path}"
            )

    def _sanitize_path(self, path: str) -> str:
        """Sanitize file path to prevent directory traversal.

        Args:
            path: Path to sanitize

        Returns:
            Sanitized path

        Raises:
            ValueError: If path contains dangerous patterns
        """
        # Check for directory traversal attempts
        if ".." in path or path.startswith("/") or "\\" in path:
            raise ValueError(f"Invalid path contains dangerous patterns: {path}")

        return path

    def _create_progress_info(
        self,
        current: int,
        total: int,
        operation: str,
        bundle_name: str,
    ) -> ProgressInfo:
        """Create progress info object.

        Args:
            current: Current bytes transferred
            total: Total bytes to transfer
            operation: Operation type ("upload" or "download")
            bundle_name: Name of bundle

        Returns:
            ProgressInfo instance
        """
        percentage = (current / total * 100) if total > 0 else 0.0
        return ProgressInfo(
            current=current,
            total=total,
            percentage=percentage,
            operation=operation,
            bundle_name=bundle_name,
        )
