"""GitHub artifact source implementation."""

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

from rich.console import Console

from skillmeat.core.artifact import Artifact, ArtifactType
from skillmeat.core.github_client import GitHubClient as GitHubClientWrapper
from skillmeat.core.github_client import (
    GitHubAuthError,
    GitHubClientError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)
from skillmeat.sources.base import ArtifactSource, FetchResult, UpdateInfo
from skillmeat.utils.metadata import extract_artifact_metadata
from skillmeat.utils.validator import ArtifactValidator

console = Console()


@dataclass
class ArtifactSpec:
    """Parses GitHub artifact specification: username/repo/path/to/artifact[@version]"""

    username: str
    repo: str
    path: str  # path within repo (can have multiple levels, or empty for root)
    version: str  # "latest", "v1.0.0", "abc123" (SHA), "main" (branch)

    @classmethod
    def parse(cls, spec: str) -> "ArtifactSpec":
        """Parse spec string into components.

        Examples:
            - anthropics/skills/python@latest
            - wshobson/commands/review@v1.2.0
            - obra/superpowers/agents/code-review@abc123
            - username/repo@main

        Args:
            spec: Spec string in format username/repo[/path/to/artifact][@version]

        Returns:
            ArtifactSpec with parsed components

        Raises:
            ValueError: If spec format is invalid
        """
        # Split version from spec
        if "@" in spec:
            spec_without_version = spec.rsplit("@", 1)[0]
            version = spec.rsplit("@", 1)[1]
        else:
            spec_without_version = spec
            version = "latest"

        # Parse repository and path
        parts = spec_without_version.split("/")
        if len(parts) < 2:
            raise ValueError(
                f"Invalid artifact spec: {spec}. Expected 'username/repo' or 'username/repo/path/...'."
            )

        username = parts[0]
        repo = parts[1]
        # Support arbitrary nesting: join all remaining parts as path
        path = "/".join(parts[2:]) if len(parts) > 2 else ""

        return cls(username=username, repo=repo, path=path, version=version)

    @property
    def repo_url(self) -> str:
        """Get GitHub repository URL."""
        return f"https://github.com/{self.username}/{self.repo}"

    @property
    def artifact_path(self) -> str:
        """Get artifact path within repository."""
        return self.path if self.path else "."

    def __str__(self) -> str:
        """String representation."""
        if self.path:
            return f"{self.username}/{self.repo}/{self.path}@{self.version}"
        return f"{self.username}/{self.repo}@{self.version}"


class GitHubClient:
    """Handles GitHub API and repository operations.

    This class delegates to GitHubClientWrapper for API operations while
    maintaining backward compatibility with the existing interface.
    """

    def __init__(self, github_token: Optional[str] = None):
        """Initialize GitHub client.

        Args:
            github_token: GitHub personal access token for authentication.
                If not provided, the wrapper handles token resolution from
                ConfigManager, SKILLMEAT_GITHUB_TOKEN, or GITHUB_TOKEN.
        """
        self._wrapper = GitHubClientWrapper(token=github_token)

    @property
    def token(self) -> Optional[str]:
        """Get the resolved GitHub token."""
        return self._wrapper.token

    def resolve_version(self, spec: ArtifactSpec) -> Tuple[str, Optional[str]]:
        """Resolve version spec to concrete SHA and version tag.

        Version resolution:
            - "latest" -> fetch latest commit SHA on default branch
            - "v1.0.0" -> resolve tag to SHA
            - "abc123" -> validate SHA exists
            - "main" -> fetch latest commit on branch

        Args:
            spec: ArtifactSpec with version to resolve

        Returns:
            (resolved_sha, resolved_version) tuple

        Raises:
            RuntimeError: If version resolution fails
        """
        owner_repo = f"{spec.username}/{spec.repo}"

        try:
            sha = self._wrapper.resolve_version(owner_repo, spec.version)

            # Determine resolved_version: only set for tags
            resolved_version = None
            if spec.version.startswith("v") or "." in spec.version:
                # If it looks like a tag and we got here, it's a valid tag
                resolved_version = spec.version

            return sha, resolved_version

        except GitHubNotFoundError as e:
            raise RuntimeError(
                f"Version '{spec.version}' not found in repository: {e.message}"
            )
        except GitHubRateLimitError as e:
            raise RuntimeError(f"GitHub rate limit exceeded: {e.message}")
        except GitHubAuthError as e:
            raise RuntimeError(f"GitHub authentication failed: {e.message}")
        except GitHubClientError as e:
            raise RuntimeError(f"Failed to resolve version: {e.message}")

    def clone_repo(self, spec: ArtifactSpec, dest_dir: Path, sha: str) -> None:
        """Clone repository to destination and checkout specific SHA.

        Args:
            spec: ArtifactSpec with repo info
            dest_dir: Destination directory for clone
            sha: Commit SHA to checkout

        Raises:
            RuntimeError: If clone or checkout fails
        """
        try:
            repo_url = spec.repo_url

            # Add auth if token is available
            if self.token:
                parsed = urlparse(repo_url)
                repo_url = f"https://oauth2:{self.token}@github.com{parsed.path}"

            # Clone with depth 1 for efficiency
            cmd = ["git", "clone", "--depth", "1", repo_url, str(dest_dir)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode != 0:
                raise RuntimeError(f"Git clone failed: {result.stderr}")

            # If we need a specific SHA, fetch it
            if sha:
                # First, unshallow the repo if needed
                cmd = ["git", "-C", str(dest_dir), "fetch", "--unshallow"]
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=120
                )
                # Ignore errors - might already be a complete repo

                # Checkout the specific SHA
                cmd = ["git", "-C", str(dest_dir), "checkout", sha]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode != 0:
                    raise RuntimeError(f"Failed to checkout {sha}: {result.stderr}")

        except subprocess.TimeoutExpired:
            raise RuntimeError("Git operation timed out")
        except Exception as e:
            # Cleanup on failure
            if dest_dir.exists():
                shutil.rmtree(dest_dir, ignore_errors=True)
            raise RuntimeError(f"Failed to clone repository: {e}")

    def fetch_artifact(
        self, spec: ArtifactSpec, artifact_type: ArtifactType, dest_dir: Path
    ) -> FetchResult:
        """Fetch artifact from GitHub to temp directory.

        Args:
            spec: ArtifactSpec with artifact location
            artifact_type: Type of artifact to fetch
            dest_dir: Temporary directory to store artifact

        Returns:
            FetchResult with artifact location and metadata

        Raises:
            RuntimeError: If fetch fails
            ValueError: If artifact path not found or invalid
        """
        # Resolve version to SHA
        try:
            resolved_sha, resolved_version = self.resolve_version(spec)
        except Exception as e:
            raise RuntimeError(f"Failed to resolve version: {e}")

        # Clone repository
        repo_dir = dest_dir / "repo"
        try:
            self.clone_repo(spec, repo_dir, resolved_sha)
        except Exception as e:
            raise RuntimeError(f"Failed to clone repository: {e}")

        # Get artifact path
        artifact_path = repo_dir / spec.artifact_path
        if not artifact_path.exists():
            shutil.rmtree(dest_dir, ignore_errors=True)
            raise ValueError(
                f"Artifact path '{spec.artifact_path}' not found in repository"
            )

        # Validate artifact structure
        validation = ArtifactValidator.validate(artifact_path, artifact_type)
        if not validation.is_valid:
            shutil.rmtree(dest_dir, ignore_errors=True)
            raise ValueError(f"Invalid artifact: {validation.error_message}")

        # Extract metadata
        try:
            metadata = extract_artifact_metadata(artifact_path, artifact_type)
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to extract metadata: {e}[/yellow]")
            from skillmeat.core.artifact import ArtifactMetadata

            metadata = ArtifactMetadata()

        # Construct upstream URL
        upstream_url = self.get_upstream_url(spec, resolved_sha)

        # Copy artifact to final destination (remove repo wrapper)
        final_path = dest_dir / "artifact"
        if artifact_path.is_file():
            final_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(artifact_path, final_path)
        else:
            shutil.copytree(artifact_path, final_path)

        # Clean up repo directory
        shutil.rmtree(repo_dir, ignore_errors=True)

        return FetchResult(
            artifact_path=final_path,
            metadata=metadata,
            resolved_sha=resolved_sha,
            resolved_version=resolved_version,
            upstream_url=upstream_url,
        )

    def get_upstream_url(self, spec: ArtifactSpec, sha: str) -> str:
        """Construct GitHub URL for artifact.

        Args:
            spec: ArtifactSpec with artifact location
            sha: Commit SHA

        Returns:
            GitHub URL
        """
        if spec.path:
            return (
                f"https://github.com/{spec.username}/{spec.repo}/tree/{sha}/{spec.path}"
            )
        return f"https://github.com/{spec.username}/{spec.repo}/tree/{sha}"


class GitHubSource(ArtifactSource):
    """GitHub artifact source."""

    def __init__(self, github_token: Optional[str] = None):
        """Initialize GitHub source.

        Args:
            github_token: GitHub personal access token
        """
        self.client = GitHubClient(github_token)

    def fetch(self, spec: str, artifact_type: ArtifactType) -> FetchResult:
        """Fetch artifact from GitHub.

        Args:
            spec: GitHub spec in format username/repo/path@version
            artifact_type: Type of artifact to fetch

        Returns:
            FetchResult with artifact location and metadata

        Raises:
            ValueError: Invalid spec format or artifact
            RuntimeError: Fetch failed
        """
        # Parse spec
        try:
            artifact_spec = ArtifactSpec.parse(spec)
        except Exception as e:
            raise ValueError(f"Invalid GitHub spec: {e}")

        # Create temp directory
        temp_dir = Path(tempfile.mkdtemp(prefix="skillmeat_github_"))

        try:
            # Fetch artifact
            result = self.client.fetch_artifact(artifact_spec, artifact_type, temp_dir)
            return result
        except Exception as e:
            # Clean up on failure
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise

    def check_updates(self, artifact: Artifact) -> Optional[UpdateInfo]:
        """Check GitHub for updates.

        Args:
            artifact: Artifact to check for updates

        Returns:
            UpdateInfo if updates available, None if no upstream or up-to-date
        """
        if not artifact.upstream or artifact.origin != "github":
            return None

        if not artifact.resolved_sha:
            return None

        # Parse upstream URL to reconstruct spec
        # URL format: https://github.com/username/repo/tree/sha/path
        try:
            url = artifact.upstream
            if not url.startswith("https://github.com/"):
                return None

            # Remove https://github.com/
            parts = url.replace("https://github.com/", "").split("/")
            if len(parts) < 4:  # username, repo, "tree", sha
                return None

            username = parts[0]
            repo = parts[1]
            # parts[2] should be "tree"
            # parts[3] is the sha (skip it)
            # parts[4:] is the path
            path = "/".join(parts[4:]) if len(parts) > 4 else ""

            # Reconstruct spec with version_spec
            if path:
                spec_str = (
                    f"{username}/{repo}/{path}@{artifact.version_spec or 'latest'}"
                )
            else:
                spec_str = f"{username}/{repo}@{artifact.version_spec or 'latest'}"

            spec = ArtifactSpec.parse(spec_str)

            # Resolve current version spec to get latest SHA
            latest_sha, latest_version = self.client.resolve_version(spec)

            # Compare SHAs
            if latest_sha != artifact.resolved_sha:
                return UpdateInfo(
                    current_sha=artifact.resolved_sha,
                    latest_sha=latest_sha,
                    current_version=artifact.resolved_version,
                    latest_version=latest_version,
                    has_update=True,
                )

            return None

        except Exception as e:
            console.print(
                f"[yellow]Warning: Failed to check updates for {artifact.name}: {e}[/yellow]"
            )
            return None

    def validate(self, path: Path, artifact_type: ArtifactType) -> bool:
        """Validate artifact structure based on type.

        Args:
            path: Path to artifact
            artifact_type: Type of artifact

        Returns:
            True if valid, False otherwise
        """
        result = ArtifactValidator.validate(path, artifact_type)
        return result.is_valid
