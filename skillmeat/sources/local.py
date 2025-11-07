"""Local filesystem artifact source implementation."""

import shutil
from pathlib import Path
from typing import Optional

from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType
from skillmeat.sources.base import ArtifactSource, FetchResult, UpdateInfo
from skillmeat.utils.metadata import extract_artifact_metadata
from skillmeat.utils.validator import ArtifactValidator


class LocalSource(ArtifactSource):
    """Local filesystem artifact source."""

    def fetch(self, path: str, artifact_type: ArtifactType) -> FetchResult:
        """Fetch artifact from local filesystem.

        Args:
            path: Local filesystem path to artifact
            artifact_type: Type of artifact

        Returns:
            FetchResult with artifact location and metadata

        Raises:
            ValueError: If path doesn't exist or artifact is invalid
            RuntimeError: If fetch fails
        """
        source_path = Path(path).resolve()

        # Validate path exists
        if not source_path.exists():
            raise ValueError(f"Path does not exist: {path}")

        # Validate artifact structure
        validation = ArtifactValidator.validate(source_path, artifact_type)
        if not validation.is_valid:
            raise ValueError(f"Invalid artifact: {validation.error_message}")

        # Extract metadata
        try:
            metadata = extract_artifact_metadata(source_path, artifact_type)
        except Exception as e:
            # If metadata extraction fails, use empty metadata
            from rich.console import Console

            console = Console()
            console.print(f"[yellow]Warning: Failed to extract metadata: {e}[/yellow]")
            metadata = ArtifactMetadata()

        # Return FetchResult
        # For local sources, the artifact_path is the original path
        # (no copying needed - caller will handle copying to collection)
        return FetchResult(
            artifact_path=source_path,
            metadata=metadata,
            resolved_sha=None,  # No SHA for local sources
            resolved_version=None,  # No version for local sources
            upstream_url=None,  # No upstream for local sources
        )

    def check_updates(self, artifact: Artifact) -> Optional[UpdateInfo]:
        """Local artifacts don't have upstream.

        Args:
            artifact: Artifact to check for updates

        Returns:
            None (local artifacts have no upstream)
        """
        return None

    def validate(self, path: Path, artifact_type: ArtifactType) -> bool:
        """Validate local artifact structure.

        Args:
            path: Path to artifact
            artifact_type: Type of artifact

        Returns:
            True if valid, False otherwise
        """
        result = ArtifactValidator.validate(path, artifact_type)
        return result.is_valid
