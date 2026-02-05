"""Import coordinator for mapping upstream artifacts to local collection.

Handles the process of importing artifacts from marketplace catalog
entries to the user's local collection.
"""

import base64
import logging
import os
import posixpath
import re
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import requests

from skillmeat.core.artifact import Artifact, ArtifactType, ArtifactMetadata
from skillmeat.core.collection import Collection
from skillmeat.storage.manifest import ManifestManager

logger = logging.getLogger(__name__)


class ImportStatus(str, Enum):
    """Status of an import operation."""

    PENDING = "pending"
    SUCCESS = "success"
    SKIPPED = "skipped"
    CONFLICT = "conflict"
    ERROR = "error"


class ConflictStrategy(str, Enum):
    """Strategy for handling import conflicts."""

    SKIP = "skip"  # Skip conflicting artifacts
    OVERWRITE = "overwrite"  # Overwrite existing
    RENAME = "rename"  # Rename with suffix


@dataclass
class ImportEntry:
    """A single entry in an import operation."""

    catalog_entry_id: str
    artifact_type: str
    name: str
    upstream_url: str
    status: ImportStatus = ImportStatus.PENDING
    error_message: Optional[str] = None
    local_path: Optional[str] = None
    conflict_with: Optional[str] = None
    # Metadata from source artifact (frontmatter)
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class ImportResult:
    """Result of an import operation."""

    import_id: str
    source_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    entries: List[ImportEntry] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        return sum(1 for e in self.entries if e.status == ImportStatus.SUCCESS)

    @property
    def skipped_count(self) -> int:
        return sum(1 for e in self.entries if e.status == ImportStatus.SKIPPED)

    @property
    def conflict_count(self) -> int:
        return sum(1 for e in self.entries if e.status == ImportStatus.CONFLICT)

    @property
    def error_count(self) -> int:
        return sum(1 for e in self.entries if e.status == ImportStatus.ERROR)

    @property
    def summary(self) -> Dict[str, int]:
        return {
            "total": len(self.entries),
            "success": self.success_count,
            "skipped": self.skipped_count,
            "conflict": self.conflict_count,
            "error": self.error_count,
        }


@dataclass
class DownloadResult:
    """Result of downloading an artifact from GitHub."""

    success: bool
    files_downloaded: int
    error_message: Optional[str] = None


class ImportCoordinator:
    """Coordinates importing artifacts from catalog to local collection.

    Handles conflict detection, strategy application, and import tracking.

    Example:
        >>> coordinator = ImportCoordinator(collection_path)
        >>> result = coordinator.import_entries(catalog_entries, source_id)
        >>> print(f"Imported {result.success_count} artifacts")
    """

    def __init__(
        self,
        collection_path: Optional[Path] = None,
        collection_name: Optional[str] = None,
        collection_mgr: Optional["CollectionManager"] = None,
    ):
        """Initialize coordinator with collection path.

        Args:
            collection_path: Explicit collection path override
            collection_name: Collection name (defaults to active collection)
            collection_mgr: Optional CollectionManager instance to resolve paths
        """
        if collection_path is not None:
            self.collection_path = collection_path
            self.collection_name = None
            self.collection_mgr = collection_mgr
            return

        from skillmeat.core.collection import CollectionManager

        self.collection_mgr = collection_mgr or CollectionManager()
        self.collection_name = (
            collection_name or self.collection_mgr.get_active_collection_name()
        )
        self.collection_path = self.collection_mgr.config.get_collection_path(
            self.collection_name
        )

    def import_entries(
        self,
        entries: List[Dict],
        source_id: str,
        strategy: ConflictStrategy = ConflictStrategy.SKIP,
        source_ref: Optional[str] = None,
    ) -> ImportResult:
        """Import catalog entries to local collection.

        Args:
            entries: List of catalog entry dicts to import
                Each should have: id, artifact_type, name, upstream_url, path
            source_id: ID of the marketplace source
            strategy: Conflict resolution strategy
            source_ref: Optional branch/ref override from source config.
                If provided, overrides the ref parsed from upstream_url.

        Returns:
            ImportResult with status for each entry
        """
        self.source_ref = source_ref
        self.import_id = str(uuid.uuid4())
        # Use timezone-aware UTC datetime
        now = (
            datetime.now(timezone.utc)
            if sys.version_info >= (3, 11)
            else datetime.utcnow()
        )
        result = ImportResult(
            import_id=self.import_id,
            source_id=source_id,
            started_at=now,
        )

        # Get existing artifacts to detect conflicts
        existing = self._get_existing_artifacts()

        for entry_data in entries:
            entry = ImportEntry(
                catalog_entry_id=entry_data.get("id", ""),
                artifact_type=entry_data.get("artifact_type", ""),
                name=entry_data.get("name", ""),
                upstream_url=entry_data.get("upstream_url", ""),
                description=entry_data.get("description"),
                tags=entry_data.get("tags", []),
            )

            try:
                self._process_entry(entry, existing, strategy)
            except Exception as e:
                entry.status = ImportStatus.ERROR
                entry.error_message = str(e)
                logger.error(f"Import error for {entry.name}: {e}")

            result.entries.append(entry)

        # Use timezone-aware UTC datetime
        result.completed_at = (
            datetime.now(timezone.utc)
            if sys.version_info >= (3, 11)
            else datetime.utcnow()
        )

        logger.info(
            f"Import {self.import_id} completed: "
            f"{result.success_count} success, {result.skipped_count} skipped, "
            f"{result.conflict_count} conflicts, {result.error_count} errors"
        )

        return result

    def _process_entry(
        self,
        entry: ImportEntry,
        existing: Dict[str, str],
        strategy: ConflictStrategy,
    ) -> None:
        """Process a single import entry."""
        # Generate local artifact key
        artifact_key = f"{entry.artifact_type}:{entry.name}"

        # Check for conflicts
        if artifact_key in existing:
            entry.conflict_with = existing[artifact_key]

            if strategy == ConflictStrategy.SKIP:
                entry.status = ImportStatus.SKIPPED
                logger.info(
                    f"Skipping {entry.name}: already exists at {entry.conflict_with}"
                )
                return

            elif strategy == ConflictStrategy.RENAME:
                # Generate unique name
                counter = 1
                new_name = f"{entry.name}-{counter}"
                new_key = f"{entry.artifact_type}:{new_name}"
                while new_key in existing:
                    counter += 1
                    new_name = f"{entry.name}-{counter}"
                    new_key = f"{entry.artifact_type}:{new_name}"
                entry.name = new_name
                artifact_key = new_key

            # OVERWRITE: Continue with import (will replace)

        # Compute local path
        entry.local_path = self._compute_local_path(entry.artifact_type, entry.name)

        # Wire the actual download flow
        try:
            # Determine target directory for artifact files
            target_dir = Path(entry.local_path)
            if not target_dir.is_absolute():
                target_dir = self.collection_path / target_dir

            # Create parent directory if needed
            target_dir.parent.mkdir(parents=True, exist_ok=True)

            # Download artifact files from GitHub
            download_result = self._download_artifact(entry, target_dir)

            if not download_result.success:
                entry.status = ImportStatus.ERROR
                entry.error_message = download_result.error_message or "Download failed"
                logger.error(f"Failed to download {entry.name}: {entry.error_message}")
                return

            # Update the collection manifest with the new artifact
            self._update_manifest(
                collection_path=self.collection_path,
                entry=entry,
                local_path=Path(entry.local_path),
            )

            entry.status = ImportStatus.SUCCESS
            logger.info(
                f"Successfully imported {entry.name} ({download_result.files_downloaded} files) to {entry.local_path}"
            )

        except Exception as e:
            entry.status = ImportStatus.ERROR
            entry.error_message = str(e)
            logger.exception(f"Error importing {entry.name}: {e}")

    def _get_existing_artifacts(self) -> Dict[str, str]:
        """Get existing artifacts in collection.

        Returns:
            Dict mapping "type:name" to local path
        """
        existing: Dict[str, str] = {}

        artifacts_path = self.collection_path / "artifacts"
        if not artifacts_path.exists():
            # Try old structure (skills/, commands/, agents/ directly in collection_path)
            for type_dir_name in ["skills", "commands", "agents"]:
                type_dir = self.collection_path / type_dir_name
                if type_dir.exists() and type_dir.is_dir():
                    artifact_type = type_dir_name.rstrip("s")  # Remove trailing 's'
                    for artifact_dir in type_dir.iterdir():
                        if not artifact_dir.is_dir():
                            continue
                        name = artifact_dir.name
                        key = f"{artifact_type}:{name}"
                        existing[key] = str(artifact_dir)
            return existing

        for type_dir in artifacts_path.iterdir():
            if not type_dir.is_dir():
                continue

            artifact_type = type_dir.name.rstrip("s")  # Remove trailing 's'

            for artifact_dir in type_dir.iterdir():
                if not artifact_dir.is_dir():
                    continue

                name = artifact_dir.name
                key = f"{artifact_type}:{name}"
                existing[key] = str(artifact_dir)

        return existing

    def _compute_local_path(self, artifact_type: str, name: str) -> str:
        """Compute local path for an artifact."""
        # Normalize artifact type for directory (ensure plural)
        if not artifact_type.endswith("s"):
            type_dir = artifact_type + "s"
        else:
            type_dir = artifact_type

        # Check if using new structure (artifacts/) or old structure
        artifacts_path = self.collection_path / "artifacts"
        if artifacts_path.exists():
            return str(artifacts_path / type_dir / name)
        else:
            # Use old structure for backward compatibility
            return str(self.collection_path / type_dir / name)

    def _update_manifest(
        self,
        collection_path: Path,
        entry: ImportEntry,
        local_path: Path,
    ) -> None:
        """Add imported artifact to collection manifest.

        Args:
            collection_path: Path to collection root (e.g., ~/.skillmeat/collections/default)
            entry: Import entry with artifact metadata
            local_path: Relative path where artifact was downloaded

        Raises:
            ValueError: If artifact type is invalid
        """
        manifest_mgr = ManifestManager()

        # Load or create collection
        if manifest_mgr.exists(collection_path):
            collection = manifest_mgr.read(collection_path)
        else:
            # Create new collection if it doesn't exist
            collection = Collection(
                name="default",
                version="1.0.0",
                artifacts=[],
                created=datetime.utcnow(),
                updated=datetime.utcnow(),
            )

        # Convert artifact type string to ArtifactType enum
        try:
            artifact_type = ArtifactType(entry.artifact_type)
        except ValueError as e:
            raise ValueError(
                f"Invalid artifact type '{entry.artifact_type}': {e}"
            ) from e

        # Create artifact metadata using source artifact's description if available
        metadata = ArtifactMetadata(
            title=entry.name,
            description=entry.description,  # Use source artifact description (may be None)
        )

        # Use tags from source artifact, fallback to empty list
        # Do NOT add generic tags like "marketplace" or "imported" - use origin field for provenance
        artifact_tags = entry.tags if entry.tags else []

        # Create Artifact object
        artifact = Artifact(
            name=entry.name,
            type=artifact_type,
            path=str(local_path),
            origin="marketplace",  # Track provenance via origin field, not tags
            metadata=metadata,
            added=datetime.utcnow(),
            upstream=entry.upstream_url,  # Keep full GitHub URL
            version_spec="latest",  # Default to latest
            resolved_sha=None,  # Will be set after actual download
            resolved_version=None,
            last_updated=None,
            tags=artifact_tags,
            origin_source="github",  # Currently all marketplace sources are GitHub-based
            import_id=self.import_id,  # Track import batch ID
        )

        # Add artifact to collection
        try:
            collection.add_artifact(artifact)
        except ValueError as e:
            # Artifact already exists
            logger.warning(f"Artifact {entry.name} already in manifest: {e}")
            # If overwriting, remove and re-add
            collection.remove_artifact(entry.name, artifact_type)
            collection.add_artifact(artifact)

        # Write updated manifest
        manifest_mgr.write(collection_path, collection)

        # Invalidate collection cache since we bypassed CollectionManager.save_collection()
        if self.collection_mgr is not None and self.collection_name is not None:
            self.collection_mgr.invalidate_collection_cache(self.collection_name)
        elif self.collection_mgr is not None:
            # Fallback: use collection name from the loaded collection
            self.collection_mgr.invalidate_collection_cache(collection.name)

    def _download_artifact(
        self,
        entry: ImportEntry,
        target_path: Path,
    ) -> DownloadResult:
        """Download artifact files from GitHub to target directory.

        Parses GitHub URLs and recursively downloads all files from the
        specified repository path.

        Args:
            entry: Import entry with upstream_url
            target_path: Local directory to download files into

        Returns:
            DownloadResult with success status and file count

        Supported URL formats:
            - https://github.com/{owner}/{repo}/tree/{ref}/{path}
            - https://github.com/{owner}/{repo}/blob/{ref}/{path}
            - https://github.com/{owner}/{repo}

        Example:
            >>> result = coordinator._download_artifact(entry, Path("/tmp/artifact"))
            >>> if result.success:
            ...     print(f"Downloaded {result.files_downloaded} files")
        """
        # Parse GitHub URL
        url_parts = self._parse_github_url(entry.upstream_url)
        if not url_parts:
            return DownloadResult(
                success=False,
                files_downloaded=0,
                error_message=f"Invalid GitHub URL: {entry.upstream_url}",
            )

        owner, repo, ref, path = url_parts

        # Use source ref if provided (overrides ref parsed from URL)
        ref = self.source_ref or ref
        logger.debug(f"Using ref={ref} for download (source_ref={self.source_ref})")

        # Get GitHub token for API requests
        github_token = os.environ.get("SKILLMEAT_GITHUB_TOKEN") or os.environ.get(
            "GITHUB_TOKEN"
        )

        # Create session with auth
        session = requests.Session()
        if github_token:
            session.headers["Authorization"] = f"token {github_token}"
        session.headers["Accept"] = "application/vnd.github.v3+json"
        session.headers["User-Agent"] = "SkillMeat/1.0"

        # Download files
        try:
            files_downloaded = self._download_directory_recursive(
                session=session,
                owner=owner,
                repo=repo,
                ref=ref,
                remote_path=path,
                local_path=target_path,
            )

            return DownloadResult(
                success=True,
                files_downloaded=files_downloaded,
            )

        except Exception as e:
            logger.error(f"Download failed for {entry.name}: {e}")
            return DownloadResult(
                success=False,
                files_downloaded=0,
                error_message=str(e),
            )
        finally:
            session.close()

    def _parse_github_url(self, url: str) -> Optional[Tuple[str, str, str, str]]:
        """Parse GitHub URL to extract owner, repo, ref, and path.

        Args:
            url: GitHub URL

        Returns:
            Tuple of (owner, repo, ref, path) or None if invalid

        Examples:
            >>> _parse_github_url("https://github.com/user/repo/tree/main/skills/my-skill")
            ("user", "repo", "main", "skills/my-skill")
            >>> _parse_github_url("https://github.com/user/repo")
            ("user", "repo", "main", "")
        """
        # Pattern: https://github.com/{owner}/{repo}/(tree|blob)/{ref}/{path}
        pattern = r"https://github\.com/([^/]+)/([^/]+)(?:/(tree|blob)/([^/]+)/(.+))?"
        match = re.match(pattern, url.rstrip("/"))

        if not match:
            logger.warning(f"Could not parse GitHub URL: {url}")
            return None

        owner = match.group(1)
        repo = match.group(2)
        ref = match.group(4) or "main"  # Default to main if not specified
        path = match.group(5) or ""  # Empty string for root

        return owner, repo, ref, path

    def _download_directory_recursive(
        self,
        session: requests.Session,
        owner: str,
        repo: str,
        ref: str,
        remote_path: str,
        local_path: Path,
        retry_count: int = 3,
        _visited_symlinks: Optional[Set[str]] = None,
    ) -> int:
        """Recursively download directory contents from GitHub.

        Uses GitHub Contents API to fetch directory listings and download files.
        Handles symlinks by resolving their targets and downloading the actual
        content into the symlink's location.

        Args:
            session: Requests session with auth headers
            owner: Repository owner
            repo: Repository name
            ref: Git reference (branch, tag, SHA)
            remote_path: Path within repository
            local_path: Local directory to download into
            retry_count: Number of retries for rate limiting
            _visited_symlinks: Internal set tracking resolved symlink targets
                to prevent circular symlink loops. Callers should not set this.

        Returns:
            Number of files downloaded

        Raises:
            requests.HTTPError: If API request fails
            RuntimeError: If rate limited and retries exhausted
        """
        if _visited_symlinks is None:
            _visited_symlinks = set()
        # Build API URL
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{remote_path}"
        params = {"ref": ref}

        # Make request with retry logic
        for attempt in range(retry_count):
            try:
                response = session.get(api_url, params=params, timeout=30)

                # Handle rate limiting
                if response.status_code == 403:
                    remaining = response.headers.get("X-RateLimit-Remaining", "0")
                    if remaining == "0":
                        reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                        wait_time = max(reset_time - time.time(), 0)
                        if wait_time < 60:  # Only wait if less than 1 minute
                            logger.warning(f"Rate limited, waiting {wait_time:.0f}s")
                            time.sleep(wait_time + 1)
                            continue
                        raise RuntimeError(f"Rate limited, reset in {wait_time:.0f}s")

                response.raise_for_status()
                break

            except requests.exceptions.RequestException as e:
                if attempt < retry_count - 1:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    raise

        # Parse response
        data = response.json()

        # Handle single file (blob)
        if isinstance(data, dict) and data.get("type") == "file":
            return self._download_file(data, local_path)

        # Handle directory (array of items)
        if not isinstance(data, list):
            logger.warning(f"Unexpected response type for {remote_path}: {type(data)}")
            return 0

        # Create local directory
        local_path.mkdir(parents=True, exist_ok=True)

        files_downloaded = 0

        # Process each item in directory
        for item in data:
            item_name = item.get("name", "")
            item_type = item.get("type", "")
            item_path = item.get("path", "")

            if item_type == "file":
                # Download file
                file_path = local_path / item_name
                if self._download_file(item, file_path):
                    files_downloaded += 1

            elif item_type == "dir":
                # Recurse into subdirectory
                subdir_path = local_path / item_name
                files_downloaded += self._download_directory_recursive(
                    session=session,
                    owner=owner,
                    repo=repo,
                    ref=ref,
                    remote_path=item_path,
                    local_path=subdir_path,
                    retry_count=retry_count,
                    _visited_symlinks=_visited_symlinks,
                )

            elif item_type == "symlink":
                # GitHub Contents API returns symlinks with a "target" field
                # containing the relative path to the actual file/directory.
                symlink_target = item.get("target", "")
                if not symlink_target:
                    logger.warning(f"Symlink {item_name} has no target, skipping")
                    continue

                # Resolve the relative target path against the current directory
                resolved_path = posixpath.normpath(
                    posixpath.join(remote_path, symlink_target)
                )

                # Guard against paths resolving outside the repository root
                if resolved_path.startswith("..") or resolved_path.startswith("/"):
                    logger.warning(
                        f"Symlink {item_name} resolves outside repo: "
                        f"{symlink_target} -> {resolved_path}, skipping"
                    )
                    continue

                # Circular symlink detection
                if resolved_path in _visited_symlinks:
                    logger.warning(
                        f"Circular symlink detected: {item_name} -> "
                        f"{resolved_path} (already visited), skipping"
                    )
                    continue

                _visited_symlinks.add(resolved_path)
                logger.info(f"Resolving symlink: {item_name} -> {resolved_path}")

                # Fetch the symlink target from GitHub Contents API
                try:
                    target_api_url = (
                        f"https://api.github.com/repos/{owner}/{repo}"
                        f"/contents/{resolved_path}"
                    )
                    target_params = {"ref": ref}
                    target_response = session.get(
                        target_api_url, params=target_params, timeout=30
                    )
                    target_response.raise_for_status()
                    target_data = target_response.json()

                    if isinstance(target_data, list):
                        # Target is a directory - recursively download
                        # into the symlink's local location
                        symlink_local_path = local_path / item_name
                        files_downloaded += self._download_directory_recursive(
                            session=session,
                            owner=owner,
                            repo=repo,
                            ref=ref,
                            remote_path=resolved_path,
                            local_path=symlink_local_path,
                            retry_count=retry_count,
                            _visited_symlinks=_visited_symlinks,
                        )
                    elif isinstance(target_data, dict):
                        # Target is a single file
                        file_path = local_path / item_name
                        local_path.mkdir(parents=True, exist_ok=True)
                        if self._download_file(target_data, file_path):
                            files_downloaded += 1
                    else:
                        logger.warning(
                            f"Unexpected response for symlink target "
                            f"{resolved_path}: {type(target_data)}"
                        )

                except requests.exceptions.RequestException as e:
                    logger.warning(
                        f"Failed to resolve symlink {item_name} -> "
                        f"{resolved_path}: {e}"
                    )

        return files_downloaded

    def _download_file(
        self,
        file_data: Dict,
        local_path: Path,
    ) -> bool:
        """Download a single file from GitHub.

        Args:
            file_data: GitHub API file data with content or download_url
            local_path: Local path to save file

        Returns:
            True if file was downloaded successfully

        Note:
            GitHub API returns base64-encoded content for files < 1MB.
            For larger files, uses download_url.
        """
        try:
            # Check if content is base64-encoded (files < 1MB)
            if file_data.get("encoding") == "base64":
                content_b64 = file_data.get("content", "")
                content_bytes = base64.b64decode(content_b64)
                local_path.write_bytes(content_bytes)
                logger.debug(f"Downloaded (base64): {local_path.name}")
                return True

            # For larger files, use download_url
            download_url = file_data.get("download_url")
            if download_url:
                response = requests.get(download_url, timeout=30)
                response.raise_for_status()
                local_path.write_bytes(response.content)
                logger.debug(f"Downloaded (URL): {local_path.name}")
                return True

            logger.warning(f"No content or download_url for {local_path.name}")
            return False

        except Exception as e:
            logger.error(f"Failed to download {local_path.name}: {e}")
            return False

    def check_conflicts(
        self,
        entries: List[Dict],
    ) -> List[Tuple[str, str, str]]:
        """Check for conflicts without importing.

        Args:
            entries: List of catalog entry dicts

        Returns:
            List of (entry_id, name, existing_path) tuples for conflicts
        """
        existing = self._get_existing_artifacts()
        conflicts = []

        for entry in entries:
            artifact_key = f"{entry.get('artifact_type', '')}:{entry.get('name', '')}"
            if artifact_key in existing:
                conflicts.append(
                    (
                        entry.get("id", ""),
                        entry.get("name", ""),
                        existing[artifact_key],
                    )
                )

        return conflicts


def import_from_catalog(
    entries: List[Dict],
    source_id: str,
    strategy: str = "skip",
    collection_path: Optional[Path] = None,
) -> ImportResult:
    """Convenience function to import catalog entries.

    Args:
        entries: Catalog entries to import
        source_id: Marketplace source ID
        strategy: Conflict strategy ("skip", "overwrite", "rename")
        collection_path: Optional collection path override

    Returns:
        ImportResult with status
    """
    strat = ConflictStrategy(strategy)
    coordinator = ImportCoordinator(collection_path)
    return coordinator.import_entries(entries, source_id, strat)


if __name__ == "__main__":
    import tempfile

    # Create temp collection
    with tempfile.TemporaryDirectory() as tmpdir:
        collection_path = Path(tmpdir) / "collection"

        # Create existing artifact (old structure)
        existing_path = collection_path / "skills" / "existing-skill"
        existing_path.mkdir(parents=True)
        (existing_path / "SKILL.md").write_text("# Existing Skill")

        # Test entries
        entries = [
            {
                "id": "e1",
                "artifact_type": "skill",
                "name": "new-skill",
                "upstream_url": "https://github.com/user/repo/skills/new-skill",
            },
            {
                "id": "e2",
                "artifact_type": "skill",
                "name": "existing-skill",  # Conflict!
                "upstream_url": "https://github.com/user/repo/skills/existing-skill",
            },
            {
                "id": "e3",
                "artifact_type": "command",
                "name": "my-command",
                "upstream_url": "https://github.com/user/repo/commands/my-command",
            },
        ]

        # Test skip strategy
        result = import_from_catalog(entries, "source-123", "skip", collection_path)

        print("Import Results (skip strategy):")
        print(f"  Summary: {result.summary}")
        for entry in result.entries:
            print(f"  - {entry.name}: {entry.status.value}")
            if entry.conflict_with:
                print(f"    Conflict with: {entry.conflict_with}")

        print()

        # Test rename strategy
        result2 = import_from_catalog(entries, "source-123", "rename", collection_path)

        print("Import Results (rename strategy):")
        print(f"  Summary: {result2.summary}")
        for entry in result2.entries:
            print(f"  - {entry.name}: {entry.status.value}")
            if entry.local_path:
                print(f"    Path: {entry.local_path}")

        print()

        # Test conflict checking
        coordinator = ImportCoordinator(collection_path)
        conflicts = coordinator.check_conflicts(entries)

        print(f"Conflicts found: {len(conflicts)}")
        for entry_id, name, existing_path in conflicts:
            print(f"  - {name} (ID: {entry_id}) conflicts with {existing_path}")
