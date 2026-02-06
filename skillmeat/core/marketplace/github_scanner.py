"""GitHub repository scanning service for artifact discovery.

Scans GitHub repositories using the API or clone, applies heuristic detection,
and returns discovered artifacts with metadata.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from skillmeat.api.schemas.marketplace import DetectedArtifact, ScanResultDTO
from skillmeat.core.github_client import (
    GitHubClient,
    GitHubClientError,
    GitHubRateLimitError,
    GitHubNotFoundError,
)
from skillmeat.core.marketplace.observability import (
    MarketplaceOperation,
    operation_context,
    log_error,
)
from skillmeat.observability.metrics import (
    marketplace_scan_duration_seconds,
    marketplace_scan_artifacts_total,
    marketplace_scan_errors_total,
    github_requests_total,
    github_rate_limit_remaining,
)

from skillmeat.core.marketplace.heuristic_detector import (
    HeuristicDetector,
    detect_artifacts_in_tree,
)
from skillmeat.core.marketplace.deduplication_engine import DeduplicationEngine

logger = logging.getLogger(__name__)


def compute_artifact_hash_from_tree(
    artifact_path: str,
    tree: List[Dict[str, Any]],
) -> str:
    """Compute content hash for an artifact from GitHub tree blob SHAs.

    Uses blob SHAs (Git's content-based hashes) from the tree to create
    a deterministic artifact-level hash without fetching file content.

    Args:
        artifact_path: Path to artifact directory (e.g., "skills/my-skill")
        tree: GitHub tree API response with path, type, sha for each item

    Returns:
        SHA256 hash of sorted path:sha pairs for files within artifact_path
    """
    import hashlib

    # Normalize artifact path (no trailing slash)
    artifact_path = artifact_path.rstrip("/")

    # Find all blob entries within this artifact directory
    file_entries = []
    for item in tree:
        if item.get("type") != "blob":
            continue
        item_path = item.get("path", "")
        # Check if file is within artifact directory or is the artifact itself
        if item_path.startswith(f"{artifact_path}/") or item_path == artifact_path:
            # Get relative path within artifact
            if item_path == artifact_path:
                rel_path = item_path.split("/")[-1]  # Just filename
            else:
                rel_path = item_path[len(artifact_path) + 1 :]  # Remove prefix
            blob_sha = item.get("sha", "")
            if blob_sha:
                file_entries.append(f"{rel_path}:{blob_sha}")

    # Sort for deterministic hash
    file_entries.sort()

    # Compute composite hash
    combined = "\n".join(file_entries)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def get_existing_collection_hashes(session) -> Set[str]:
    """Query existing artifact hashes from the marketplace catalog.

    Args:
        session: SQLAlchemy database session

    Returns:
        Set of content hashes from non-excluded catalog entries

    Note:
        Hashes are expected to be in metadata.content_hash field.
        Handles None/missing hashes gracefully.
    """
    from skillmeat.cache.models import MarketplaceCatalogEntry
    from sqlalchemy import func
    import json

    hashes = set()

    # Optimized query using SQLite JSON extraction
    # This avoids fetching full objects and parsing JSON in Python
    # which gives ~10x performance improvement for large catalogs
    try:
        bind = session.get_bind()
        dialect_name = bind.dialect.name if bind is not None else None

        if dialect_name == "sqlite":
            results = (
                session.query(
                    func.json_extract(
                        MarketplaceCatalogEntry.metadata_json, "$.content_hash"
                    )
                )
                .filter(MarketplaceCatalogEntry.excluded_at.is_(None))
                .filter(MarketplaceCatalogEntry.metadata_json.isnot(None))
                .all()
            )

            for (content_hash,) in results:
                if content_hash:
                    hashes.add(content_hash)
        else:
            raise RuntimeError(
                f"json_extract optimization not supported for dialect '{dialect_name}'"
            )

    except Exception as e:
        # Fallback for databases that don't support json_extract or other errors
        logger.warning(f"Optimized hash query failed, falling back to slow method: {e}")
        session.rollback()

        entries = (
            session.query(MarketplaceCatalogEntry)
            .filter(MarketplaceCatalogEntry.excluded_at.is_(None))
            .all()
        )

        for entry in entries:
            if entry.metadata_json:
                try:
                    metadata = json.loads(entry.metadata_json)
                    content_hash = metadata.get("content_hash")
                    if content_hash:
                        hashes.add(content_hash)
                except (json.JSONDecodeError, AttributeError):
                    # Skip entries with invalid JSON or missing metadata
                    continue

    logger.debug(f"Loaded {len(hashes)} existing content hashes from collection")
    return hashes


@dataclass
class ScanConfig:
    """Configuration for GitHub scanning."""

    # API timeout in seconds
    timeout: int = 60

    # Maximum files to process per repo
    max_files: int = 5000

    # Rate limit handling
    retry_count: int = 3
    retry_delay: float = 1.0

    # Cache settings
    cache_ttl_seconds: int = 300  # 5 minutes


class GitHubScanner:
    """Scans GitHub repositories for Claude Code artifacts.

    Uses the centralized GitHubClient to fetch repository tree and applies
    heuristic detection to identify artifacts.

    Example:
        >>> scanner = GitHubScanner(token="ghp_...")
        >>> result = scanner.scan_repository(
        ...     owner="anthropics",
        ...     repo="anthropic-quickstarts",
        ...     ref="main",
        ... )
        >>> print(f"Found {result.artifacts_found} artifacts")
    """

    def __init__(
        self,
        token: Optional[str] = None,
        config: Optional[ScanConfig] = None,
    ):
        """Initialize scanner with optional authentication.

        Args:
            token: GitHub Personal Access Token (recommended for higher rate limits).
                If not provided, token is resolved from ConfigManager,
                SKILLMEAT_GITHUB_TOKEN, or GITHUB_TOKEN environment variables.
            config: Optional scanning configuration
        """
        self.config = config or ScanConfig()
        self._client = GitHubClient(token)
        self.detector = HeuristicDetector()

    @property
    def token(self) -> Optional[str]:
        """Get the resolved GitHub token (for backward compatibility)."""
        return self._client.token

    def get_rate_limit(self) -> Dict[str, Any]:
        """Get current GitHub API rate limit information.

        Returns:
            Dictionary containing:
                - remaining: int - Requests remaining
                - limit: int - Total request limit
                - reset: datetime - When limit resets (UTC)
        """
        return self._client.get_rate_limit()

    def scan_repository(
        self,
        owner: str,
        repo: str,
        ref: str = "main",
        root_hint: Optional[str] = None,
        source_id: Optional[str] = None,
        session=None,
        manual_mappings: Optional[Dict[str, str]] = None,
    ) -> ScanResultDTO:
        """Scan a GitHub repository for artifacts.

        Args:
            owner: Repository owner/organization
            repo: Repository name
            ref: Branch, tag, or SHA to scan
            root_hint: Optional subdirectory to focus on
            source_id: Optional source ID for metrics tracking
            session: Optional SQLAlchemy session for cross-source deduplication
            manual_mappings: Optional directory-to-artifact-type mappings for manual
                override. Format: {"path/to/dir": "skill", "another/path": "command"}.

        Returns:
            ScanResultDTO with scan results and statistics

        Raises:
            GitHubAPIError: If API call fails
            RateLimitError: If rate limited and retries exhausted
        """
        repo_full_name = f"{owner}/{repo}"
        source_id = source_id or repo_full_name

        # Create operation context with tracing and logging
        with operation_context(
            MarketplaceOperation.SCAN,
            source_id=source_id,
            owner=owner,
            repo=repo,
            ref=ref,
        ) as ctx:
            start_time = time.time()
            errors: List[str] = []

            try:
                # 1. Fetch repository tree (may fallback to actual default branch)
                ctx.metadata["phase"] = "fetch_tree"
                tree, actual_ref = self._fetch_tree(owner, repo, ref)
                ctx.metadata["tree_size"] = len(tree)
                ctx.metadata["actual_ref"] = actual_ref
                if actual_ref != ref:
                    logger.info(
                        f"Using actual ref '{actual_ref}' instead of '{ref}' "
                        f"for {repo_full_name}"
                    )

                # 2. Filter to relevant paths
                ctx.metadata["phase"] = "extract_paths"
                file_paths = self._extract_file_paths(tree, root_hint)
                ctx.metadata["file_count"] = len(file_paths)

                # 3. Get commit SHA for versioning (use actual_ref, not original ref)
                ctx.metadata["phase"] = "get_sha"
                commit_sha = self._get_ref_sha(owner, repo, actual_ref)
                ctx.metadata["commit_sha"] = commit_sha

                # 4. Apply heuristic detection
                ctx.metadata["phase"] = "detect_artifacts"
                base_url = f"https://github.com/{owner}/{repo}"
                detected_artifacts = detect_artifacts_in_tree(
                    file_paths,
                    repo_url=base_url,
                    ref=actual_ref,
                    root_hint=root_hint,
                    detected_sha=commit_sha,
                    manual_mappings=manual_mappings,
                )
                ctx.metadata["detected_count"] = len(detected_artifacts)
                logger.info(
                    f"Detected {len(detected_artifacts)} artifacts from {repo_full_name}"
                )

                # 4b. Compute content hash for each artifact from tree blob SHAs
                # This enables proper deduplication without fetching file content
                ctx.metadata["phase"] = "compute_content_hashes"
                for artifact in detected_artifacts:
                    content_hash = compute_artifact_hash_from_tree(artifact.path, tree)
                    # Store in metadata for deduplication
                    if artifact.metadata is None:
                        artifact.metadata = {}
                    artifact.metadata["content_hash"] = content_hash

                # 5. Deduplicate within source
                ctx.metadata["phase"] = "deduplicate_within_source"
                engine = DeduplicationEngine()

                # Convert DetectedArtifact Pydantic models to dicts for deduplication
                artifacts_dicts = [a.model_dump() for a in detected_artifacts]

                kept_dicts, within_excluded_dicts = engine.deduplicate_within_source(
                    artifacts_dicts
                )
                ctx.metadata["within_source_duplicates"] = len(within_excluded_dicts)
                logger.info(
                    f"Within-source dedup: {len(kept_dicts)} kept, "
                    f"{len(within_excluded_dicts)} duplicates"
                )

                # 6. Deduplicate against existing collection
                ctx.metadata["phase"] = "deduplicate_cross_source"
                cross_excluded_dicts = []
                if session is not None:
                    existing_hashes = get_existing_collection_hashes(session)
                    unique_dicts, cross_excluded_dicts = (
                        engine.deduplicate_cross_source(kept_dicts, existing_hashes)
                    )
                    kept_dicts = unique_dicts
                    ctx.metadata["cross_source_duplicates"] = len(cross_excluded_dicts)
                    logger.info(
                        f"Cross-source dedup: {len(unique_dicts)} unique, "
                        f"{len(cross_excluded_dicts)} duplicates against "
                        f"{len(existing_hashes)} existing"
                    )
                else:
                    logger.debug(
                        "No session provided, skipping cross-source deduplication"
                    )

                # Convert dicts back to DetectedArtifact models
                from skillmeat.api.schemas.marketplace import DetectedArtifact

                kept = [DetectedArtifact(**d) for d in kept_dicts]
                within_excluded = [DetectedArtifact(**d) for d in within_excluded_dicts]
                cross_excluded = [DetectedArtifact(**d) for d in cross_excluded_dicts]

                # Combine all artifacts (unique + excluded)
                artifacts = kept + within_excluded + cross_excluded

                # 7. Build result
                duration_ms = (time.time() - start_time) * 1000
                duration_seconds = duration_ms / 1000

                # Record metrics
                marketplace_scan_duration_seconds.labels(source_id=source_id).observe(
                    duration_seconds
                )

                # Count artifacts by type
                artifact_counts = {}
                for artifact in artifacts:
                    artifact_type = (
                        artifact.artifact_type
                        if hasattr(artifact, "artifact_type")
                        else artifact.get("artifact_type", "unknown")
                    )
                    artifact_counts[artifact_type] = (
                        artifact_counts.get(artifact_type, 0) + 1
                    )
                    marketplace_scan_artifacts_total.labels(
                        source_id=source_id, artifact_type=artifact_type
                    ).inc()

                ctx.metadata["artifact_counts"] = artifact_counts
                ctx.metadata["artifacts_found"] = len(artifacts)

                return ScanResultDTO(
                    source_id="",  # Set by caller
                    status="success",
                    artifacts_found=len(artifacts),
                    artifacts=artifacts,
                    new_count=len(kept),  # Unique artifacts
                    updated_count=0,
                    removed_count=0,
                    unchanged_count=0,
                    duplicates_within_source=len(within_excluded),
                    duplicates_cross_source=len(cross_excluded),
                    total_detected=len(detected_artifacts),
                    total_unique=len(kept),
                    scan_duration_ms=duration_ms,
                    errors=errors,
                    scanned_at=datetime.utcnow(),
                )

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                error_type = type(e).__name__

                # Record error metrics
                marketplace_scan_errors_total.labels(
                    source_id=source_id, error_type=error_type
                ).inc()

                log_error(e, MarketplaceOperation.SCAN, source_id=source_id)
                errors.append(str(e))

                return ScanResultDTO(
                    source_id="",
                    status="error",
                    artifacts_found=0,
                    artifacts=[],
                    new_count=0,
                    updated_count=0,
                    removed_count=0,
                    unchanged_count=0,
                    duplicates_within_source=0,
                    duplicates_cross_source=0,
                    total_detected=0,
                    total_unique=0,
                    scan_duration_ms=duration_ms,
                    errors=errors,
                    scanned_at=datetime.utcnow(),
                )

    def _fetch_tree(
        self,
        owner: str,
        repo: str,
        ref: str,
    ) -> tuple[List[Dict[str, Any]], str]:
        """Fetch repository tree using Git Trees API.

        Uses recursive tree fetch for efficiency. If ref is 'main' and fails
        with 404, automatically falls back to the repository's actual default
        branch (e.g., 'master').

        Args:
            owner: Repository owner
            repo: Repository name
            ref: Git reference (branch, tag, SHA)

        Returns:
            Tuple of (tree items, actual_ref used). The actual_ref may differ
            from the input ref if fallback to default branch occurred.

        Raises:
            GitHubAPIError: If API call fails
        """
        owner_repo = f"{owner}/{repo}"
        actual_ref = ref  # Track which ref was actually used

        try:
            tree = self._client.get_repo_tree(owner_repo, ref=ref, recursive=True)
            return tree, actual_ref
        except GitHubNotFoundError:
            # If ref="main" fails with 404, try actual default branch
            if ref == "main":
                logger.warning(
                    f"Branch 'main' not found for {owner_repo}, "
                    "fetching actual default branch"
                )
                actual_default = self._get_default_branch(owner, repo)
                if actual_default != "main":
                    logger.info(
                        f"Retrying with default branch '{actual_default}' "
                        f"for {owner_repo}"
                    )
                    tree = self._client.get_repo_tree(
                        owner_repo, ref=actual_default, recursive=True
                    )
                    return tree, actual_default
            raise

    def _extract_file_paths(
        self,
        tree: List[Dict[str, Any]],
        root_hint: Optional[str] = None,
    ) -> List[str]:
        """Extract file paths from tree, optionally filtering by root_hint.

        Includes both regular files (type="blob") and symlinks (type="symlink")
        from the tree. Symlinks are identified by get_repo_tree() using Git's
        mode 120000. They are included in the path list so heuristic detection
        can see them as part of the artifact structure. The import coordinator
        handles actual symlink resolution via the Contents API.

        Args:
            tree: Tree items from GitHub API
            root_hint: Optional subdirectory to filter by

        Returns:
            List of file paths
        """
        paths = []
        symlink_count = 0

        for item in tree:
            item_type = item.get("type", "")
            if item_type not in ("blob", "symlink"):
                continue

            path = item.get("path", "")

            # Apply root_hint filter if provided
            if root_hint:
                root_normalized = root_hint.rstrip("/") + "/"
                if not path.startswith(root_normalized) and path != root_hint.rstrip(
                    "/"
                ):
                    continue

            paths.append(path)

            if item_type == "symlink":
                symlink_count += 1

        if symlink_count > 0:
            logger.debug(f"Included {symlink_count} symlink entries in file paths")

        # Limit to max_files
        if len(paths) > self.config.max_files:
            logger.warning(
                f"Truncating file list from {len(paths)} to {self.config.max_files}"
            )
            paths = paths[: self.config.max_files]

        return paths

    def _get_ref_sha(self, owner: str, repo: str, ref: str) -> str:
        """Get the commit SHA for a ref.

        Args:
            owner: Repository owner
            repo: Repository name
            ref: Git reference

        Returns:
            Commit SHA

        Raises:
            GitHubClientError: If API call fails
        """
        owner_repo = f"{owner}/{repo}"
        return self._client.resolve_version(owner_repo, ref)

    def get_file_tree(
        self,
        owner: str,
        repo: str,
        path: str = "",
        sha: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch file tree for a repository or subdirectory.

        Uses GitHub's Git Trees API to retrieve file listings. If no SHA is
        provided, fetches the default branch SHA first.

        Args:
            owner: Repository owner
            repo: Repository name
            path: Path prefix to filter files (e.g., "src/components")
            sha: Git tree SHA. If None, fetches default branch SHA.

        Returns:
            List of file entries with keys:
                - path: File path relative to repository root
                - type: "blob" for files, "tree" for directories
                - size: File size in bytes (only for blobs)
                - sha: Git blob/tree SHA

        Raises:
            GitHubClientError: If API call fails
            GitHubRateLimitError: If rate limited

        Example:
            >>> scanner = GitHubScanner(token="ghp_...")
            >>> files = scanner.get_file_tree(
            ...     owner="anthropics",
            ...     repo="anthropic-quickstarts",
            ...     path="skills",
            ... )
            >>> for f in files:
            ...     print(f"{f['type']}: {f['path']} ({f.get('size', 'dir')})")
        """
        owner_repo = f"{owner}/{repo}"

        # Fetch recursive tree using the ref (sha) if provided
        tree = self._client.get_repo_tree(owner_repo, ref=sha, recursive=True)

        # Filter by path prefix if provided
        if path:
            path_normalized = path.rstrip("/")
            tree = [
                item
                for item in tree
                if item["path"].startswith(f"{path_normalized}/")
                or item["path"] == path_normalized
            ]

        return tree

    def _get_default_branch(self, owner: str, repo: str) -> str:
        """Get the repository's default branch name.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Name of the default branch (e.g., "main", "master")

        Raises:
            GitHubClientError: If API call fails
        """
        owner_repo = f"{owner}/{repo}"
        metadata = self._client.get_repo_metadata(owner_repo)
        return metadata["default_branch"]

    def _get_default_branch_sha(self, owner: str, repo: str) -> str:
        """Get the SHA of the repository's default branch.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            SHA of the default branch HEAD commit

        Raises:
            GitHubClientError: If API call fails
        """
        owner_repo = f"{owner}/{repo}"
        # "latest" resolves to the default branch HEAD
        return self._client.resolve_version(owner_repo, "latest")

    # File content truncation constants
    MAX_FILE_SIZE = 1_048_576  # 1MB
    MAX_LINES = 10_000

    def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str | None = None,
    ) -> Dict[str, Any] | None:
        """Fetch content and metadata of a specific file from GitHub.

        Uses the centralized GitHubClient to retrieve file content along with
        metadata like size, SHA, and encoding information.

        Large text files (>1MB) are automatically truncated to the first
        10,000 lines to prevent performance issues. When truncation occurs,
        the returned dict includes 'truncated': True and 'original_size'
        with the pre-truncation size.

        Args:
            owner: Repository owner/organization
            repo: Repository name
            path: File path within repository (e.g., "src/main.py")
            ref: Git reference (branch, tag, SHA). Defaults to repo's default branch.

        Returns:
            Dict containing:
                - content: Decoded file content (str for text, base64 for binary)
                - encoding: "utf-8" for text, "base64" for binary
                - size: File size in bytes (truncated size if truncated)
                - name: File name
                - path: Full path within repo
                - is_binary: Whether file appears to be binary
                - truncated: Whether content was truncated (default False)
                - original_size: Original size before truncation (None if not truncated)

            Returns None if file not found (404).

        Raises:
            GitHubClientError: If API call fails (non-404 errors)
            GitHubRateLimitError: If rate limited

        Example:
            >>> scanner = GitHubScanner(token="ghp_...")
            >>> result = scanner.get_file_content(
            ...     owner="anthropics",
            ...     repo="anthropic-quickstarts",
            ...     path="README.md",
            ...     ref="main",
            ... )
            >>> if result:
            ...     print(result["content"][:50])
            '# Anthropic Quickstarts...'
        """
        import base64

        owner_repo = f"{owner}/{repo}"
        name = path.split("/")[-1] if "/" in path else path

        try:
            file_data = self._client.get_file_with_metadata(owner_repo, path, ref=ref)
            content_bytes = file_data["content"]
            file_sha = file_data["sha"]
        except GitHubNotFoundError:
            logger.debug(f"File not found: {owner_repo}/{path}")
            return None
        except GitHubClientError as e:
            # Symlinks to directories or unresolvable symlinks
            error_msg = str(e).lower()
            if "is a directory" in error_msg or "symlink" in error_msg:
                logger.debug(f"Path is not a regular file: {owner_repo}/{path}: {e}")
                return None
            raise

        size = len(content_bytes)

        # Determine if file is binary based on common binary extensions
        binary_extensions = {
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".ico",
            ".webp",
            ".bmp",
            ".pdf",
            ".zip",
            ".tar",
            ".gz",
            ".rar",
            ".7z",
            ".exe",
            ".dll",
            ".so",
            ".dylib",
            ".woff",
            ".woff2",
            ".ttf",
            ".otf",
            ".eot",
            ".mp3",
            ".mp4",
            ".wav",
            ".avi",
            ".mov",
            ".pyc",
            ".class",
            ".o",
            ".obj",
        }
        file_ext = "." + name.split(".")[-1].lower() if "." in name else ""
        is_binary = file_ext in binary_extensions

        # Decode content
        decoded_content: str
        encoding: str
        if is_binary:
            # For binary files, keep as base64 to avoid encoding issues
            decoded_content = base64.b64encode(content_bytes).decode("ascii")
            encoding = "base64"
        else:
            # For text files, decode to UTF-8 string
            try:
                decoded_content = content_bytes.decode("utf-8")
                encoding = "utf-8"
            except UnicodeDecodeError:
                # File is binary despite extension, keep as base64
                logger.debug(f"Binary content detected for: {path}")
                is_binary = True
                decoded_content = base64.b64encode(content_bytes).decode("ascii")
                encoding = "base64"

        # Apply truncation for large text files
        truncated = False
        original_size: int | None = None

        if not is_binary and len(decoded_content) > self.MAX_FILE_SIZE:
            original_size = len(decoded_content)
            lines = decoded_content.split("\n")[: self.MAX_LINES]
            decoded_content = "\n".join(lines)
            truncated = True
            logger.info(
                f"Truncated large file {path}: {original_size} bytes -> "
                f"{len(decoded_content)} bytes ({self.MAX_LINES} lines)"
            )

        return {
            "content": decoded_content,
            "encoding": encoding,
            "size": len(decoded_content) if truncated else size,
            "sha": file_sha,
            "name": name,
            "path": path,
            "is_binary": is_binary,
            "truncated": truncated,
            "original_size": original_size,
        }


class GitHubAPIError(GitHubClientError):
    """Error from GitHub API.

    Deprecated: Use GitHubClientError from skillmeat.core.github_client instead.
    This class is kept for backward compatibility.
    """

    pass


class RateLimitError(GitHubRateLimitError, GitHubAPIError):
    """Rate limit exceeded.

    Deprecated: Use GitHubRateLimitError from skillmeat.core.github_client instead.
    This class is kept for backward compatibility.

    Note: Inherits from both GitHubRateLimitError (new) and GitHubAPIError (legacy)
    to maintain backward compatibility with code that catches GitHubAPIError.
    """

    pass


# =============================================================================
# Repository Metadata Fetching
# =============================================================================

# Truncation limits for fetched metadata
MAX_REPO_DESCRIPTION_CHARS = 2000
MAX_REPO_README_CHARS = 50000  # 50KB

# Common README file names in priority order
README_FILENAMES = [
    "README.md",
    "readme.md",
    "README.MD",
    "Readme.md",
    "README.rst",
    "readme.rst",
    "README.txt",
    "readme.txt",
    "README",
]


async def fetch_repo_description(
    client: GitHubClient,
    owner: str,
    repo: str,
    timeout_seconds: float = 5.0,
) -> Optional[str]:
    """Fetch repository description from GitHub API.

    Uses the centralized GitHubClient wrapper to fetch repository metadata
    and extract the description field.

    Args:
        client: GitHubClient instance to use for the request
        owner: Repository owner/organization
        repo: Repository name
        timeout_seconds: Request timeout in seconds (default: 5.0)

    Returns:
        Description string truncated to 2000 chars, or None on error

    Note:
        Errors are logged as warnings but do not raise exceptions.
        This allows scans to continue even if metadata fetch fails.
    """
    import asyncio

    owner_repo = f"{owner}/{repo}"

    try:
        # Run synchronous GitHub client in executor with timeout
        loop = asyncio.get_event_loop()
        metadata = await asyncio.wait_for(
            loop.run_in_executor(None, client.get_repo_metadata, owner_repo),
            timeout=timeout_seconds,
        )

        description = metadata.get("description")
        if description:
            # Truncate to max length
            if len(description) > MAX_REPO_DESCRIPTION_CHARS:
                logger.debug(
                    f"Truncating description for {owner_repo}: "
                    f"{len(description)} -> {MAX_REPO_DESCRIPTION_CHARS} chars"
                )
                description = description[:MAX_REPO_DESCRIPTION_CHARS]
            return description
        return None

    except asyncio.TimeoutError:
        logger.warning(
            f"Timeout fetching repo description for {owner_repo} "
            f"(>{timeout_seconds}s)"
        )
        return None
    except GitHubNotFoundError:
        logger.warning(f"Repository not found when fetching description: {owner_repo}")
        return None
    except GitHubRateLimitError as e:
        logger.warning(f"Rate limit hit fetching description for {owner_repo}: {e}")
        return None
    except GitHubClientError as e:
        logger.warning(f"Error fetching repo description for {owner_repo}: {e}")
        return None
    except Exception as e:
        logger.warning(
            f"Unexpected error fetching repo description for {owner_repo}: {e}"
        )
        return None


async def fetch_repo_readme(
    client: GitHubClient,
    owner: str,
    repo: str,
    ref: str = "main",
    timeout_seconds: float = 5.0,
) -> Optional[str]:
    """Fetch README content from GitHub.

    Tries common README filenames in priority order (README.md, readme.md, etc.)
    and returns the content of the first one found.

    Args:
        client: GitHubClient instance to use for the request
        owner: Repository owner/organization
        repo: Repository name
        ref: Git reference (branch, tag, SHA) to fetch from (default: "main")
        timeout_seconds: Request timeout in seconds (default: 5.0)

    Returns:
        README content truncated to 50KB, or None if not found or on error

    Note:
        Errors are logged as warnings but do not raise exceptions.
        This allows scans to continue even if README fetch fails.
    """
    import asyncio

    owner_repo = f"{owner}/{repo}"

    async def try_fetch_readme(filename: str) -> Optional[str]:
        """Try to fetch a specific README file."""
        try:
            loop = asyncio.get_event_loop()
            content_bytes = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: client.get_file_content(owner_repo, filename, ref=ref),
                ),
                timeout=timeout_seconds,
            )

            # Decode bytes to string
            try:
                content = content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                logger.debug(f"Non-UTF-8 README in {owner_repo}/{filename}")
                return None

            # Truncate to max length
            if len(content) > MAX_REPO_README_CHARS:
                logger.debug(
                    f"Truncating README for {owner_repo}: "
                    f"{len(content)} -> {MAX_REPO_README_CHARS} chars"
                )
                content = content[:MAX_REPO_README_CHARS]

            return content

        except asyncio.TimeoutError:
            logger.debug(
                f"Timeout fetching {filename} for {owner_repo} (>{timeout_seconds}s)"
            )
            return None
        except GitHubNotFoundError:
            # Expected for some README variants - try next one
            return None
        except GitHubRateLimitError as e:
            logger.warning(f"Rate limit hit fetching README for {owner_repo}: {e}")
            return None
        except GitHubClientError as e:
            logger.debug(f"Error fetching {filename} for {owner_repo}: {e}")
            return None
        except Exception as e:
            logger.debug(f"Unexpected error fetching {filename} for {owner_repo}: {e}")
            return None

    # Try each README filename in priority order
    for filename in README_FILENAMES:
        content = await try_fetch_readme(filename)
        if content is not None:
            logger.debug(f"Found README at {owner_repo}/{filename}")
            return content

    logger.debug(f"No README found in {owner_repo}")
    return None


async def fetch_repo_metadata_for_source(
    client: GitHubClient,
    owner: str,
    repo: str,
    ref: str = "main",
    import_description: bool = False,
    import_readme: bool = False,
) -> Dict[str, Optional[str]]:
    """Fetch repository description and README from GitHub.

    Conditionally fetches metadata based on the import flags.
    Uses the centralized GitHubClient wrapper.

    Args:
        client: GitHubClient instance to use for requests
        owner: Repository owner/organization
        repo: Repository name
        ref: Git reference for README fetch (default: "main")
        import_description: If True, fetch repository description
        import_readme: If True, fetch README content

    Returns:
        Dict with 'repo_description' and 'repo_readme' keys.
        Values may be None if not requested or on error.

    Note:
        Each fetch has a 5 second timeout. Errors are logged but
        don't cause the operation to fail.
    """
    import asyncio

    result: Dict[str, Optional[str]] = {
        "repo_description": None,
        "repo_readme": None,
    }

    tasks = []

    if import_description:
        tasks.append(("repo_description", fetch_repo_description(client, owner, repo)))

    if import_readme:
        tasks.append(("repo_readme", fetch_repo_readme(client, owner, repo, ref=ref)))

    if not tasks:
        return result

    # Run fetches concurrently
    for key, coro in tasks:
        try:
            result[key] = await coro
        except Exception as e:
            logger.warning(f"Error in fetch_repo_metadata_for_source ({key}): {e}")
            result[key] = None

    return result


def scan_github_source(
    repo_url: str,
    ref: str = "main",
    root_hint: Optional[str] = None,
    token: Optional[str] = None,
) -> Tuple[ScanResultDTO, List[DetectedArtifact]]:
    """Convenience function to scan a GitHub repository.

    Args:
        repo_url: Full GitHub URL (e.g., "https://github.com/user/repo")
        ref: Branch/tag/SHA to scan
        root_hint: Optional subdirectory focus
        token: Optional GitHub token

    Returns:
        Tuple of (scan_result, detected_artifacts)

    Raises:
        ValueError: If repository URL is invalid
        GitHubAPIError: If scan fails
    """
    # Parse owner/repo from URL
    parts = repo_url.rstrip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"Invalid repository URL: {repo_url}")

    owner = parts[-2]
    repo = parts[-1].replace(".git", "")

    scanner = GitHubScanner(token=token)

    # Fetch tree and detect (may fallback to actual default branch)
    tree, actual_ref = scanner._fetch_tree(owner, repo, ref)
    file_paths = scanner._extract_file_paths(tree, root_hint)
    commit_sha = scanner._get_ref_sha(owner, repo, actual_ref)

    artifacts = detect_artifacts_in_tree(
        file_paths,
        repo_url=repo_url,
        ref=actual_ref,
        root_hint=root_hint,
        detected_sha=commit_sha,
    )

    # Compute content hash for each artifact from tree blob SHAs
    for artifact in artifacts:
        content_hash = compute_artifact_hash_from_tree(artifact.path, tree)
        if artifact.metadata is None:
            artifact.metadata = {}
        artifact.metadata["content_hash"] = content_hash

    result = ScanResultDTO(
        source_id="",
        status="success",
        artifacts_found=len(artifacts),
        new_count=len(artifacts),
        updated_count=0,
        removed_count=0,
        unchanged_count=0,
        duplicates_within_source=0,
        duplicates_cross_source=0,
        total_detected=len(artifacts),
        total_unique=len(artifacts),
        scan_duration_ms=0,
        errors=[],
        scanned_at=datetime.utcnow(),
    )

    return result, artifacts
