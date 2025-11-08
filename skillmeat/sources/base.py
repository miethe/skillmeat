"""Abstract base classes for artifact sources."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType


@dataclass
class FetchResult:
    """Result of fetching an artifact from a source."""

    artifact_path: Path  # temporary path where artifact was fetched
    metadata: ArtifactMetadata
    resolved_sha: Optional[str] = None  # for GitHub sources
    resolved_version: Optional[str] = None  # for GitHub sources
    upstream_url: Optional[str] = None  # for GitHub sources


@dataclass
class UpdateInfo:
    """Information about available updates."""

    current_sha: str
    latest_sha: str
    current_version: Optional[str]
    latest_version: Optional[str]
    has_update: bool
    commit_count: int = 0
    changes_description: Optional[str] = None


class ArtifactSource(ABC):
    """Abstract base class for artifact sources."""

    @abstractmethod
    def fetch(self, spec: str, artifact_type: ArtifactType) -> FetchResult:
        """Fetch artifact from source to temporary location.

        Args:
            spec: Source-specific specification (e.g., "user/repo/path@version" for GitHub)
            artifact_type: Type of artifact to fetch

        Returns:
            FetchResult with artifact location and metadata

        Raises:
            ValueError: Invalid spec format
            RuntimeError: Fetch failed
        """
        pass

    @abstractmethod
    def check_updates(self, artifact: Artifact) -> Optional[UpdateInfo]:
        """Check if updates are available for artifact.

        Args:
            artifact: Artifact to check for updates

        Returns:
            UpdateInfo if updates available, None if no upstream or up-to-date
        """
        pass

    @abstractmethod
    def validate(self, path: Path, artifact_type: ArtifactType) -> bool:
        """Validate artifact structure.

        Args:
            path: Path to artifact
            artifact_type: Type of artifact

        Returns:
            True if valid, False otherwise
        """
        pass
