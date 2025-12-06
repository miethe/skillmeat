"""GitHub repository scanning service for artifact discovery.

Scans GitHub repositories using the API or clone, applies heuristic detection,
and returns discovered artifacts with metadata.
"""

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

from skillmeat.api.schemas.marketplace import DetectedArtifact, ScanResultDTO

# Note: This import will be available once SVC-002 (heuristic detector) is implemented
# from skillmeat.core.marketplace.heuristic_detector import (
#     HeuristicDetector,
#     detect_artifacts_in_tree,
# )

logger = logging.getLogger(__name__)


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

    Uses GitHub's Contents API to fetch repository tree and applies
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

    API_BASE = "https://api.github.com"

    def __init__(
        self,
        token: Optional[str] = None,
        config: Optional[ScanConfig] = None,
    ):
        """Initialize scanner with optional authentication.

        Args:
            token: GitHub Personal Access Token (recommended for higher rate limits)
            config: Optional scanning configuration
        """
        self.token = (
            token
            or os.environ.get("SKILLMEAT_GITHUB_TOKEN")
            or os.environ.get("GITHUB_TOKEN")
        )
        self.config = config or ScanConfig()
        self.session = requests.Session()

        if self.token:
            self.session.headers["Authorization"] = f"token {self.token}"

        self.session.headers["Accept"] = "application/vnd.github.v3+json"
        self.session.headers["User-Agent"] = "SkillMeat/1.0"

        # Will be initialized once heuristic detector is implemented
        # self.detector = HeuristicDetector()

    def scan_repository(
        self,
        owner: str,
        repo: str,
        ref: str = "main",
        root_hint: Optional[str] = None,
    ) -> ScanResultDTO:
        """Scan a GitHub repository for artifacts.

        Args:
            owner: Repository owner/organization
            repo: Repository name
            ref: Branch, tag, or SHA to scan
            root_hint: Optional subdirectory to focus on

        Returns:
            ScanResultDTO with scan results and statistics

        Raises:
            GitHubAPIError: If API call fails
            RateLimitError: If rate limited and retries exhausted
        """
        start_time = time.time()
        errors: List[str] = []

        try:
            # 1. Fetch repository tree
            tree = self._fetch_tree(owner, repo, ref)

            # 2. Filter to relevant paths
            file_paths = self._extract_file_paths(tree, root_hint)

            # 3. Get commit SHA for versioning
            commit_sha = self._get_ref_sha(owner, repo, ref)

            # 4. Apply heuristic detection
            # NOTE: This will be uncommented once SVC-002 (heuristic detector) is implemented
            # base_url = f"https://github.com/{owner}/{repo}"
            # artifacts = detect_artifacts_in_tree(
            #     file_paths,
            #     repo_url=base_url,
            #     ref=ref,
            #     root_hint=root_hint,
            #     detected_sha=commit_sha,
            # )

            # Placeholder until heuristic detector is implemented
            artifacts = []
            logger.warning(
                "Heuristic detector not yet implemented (SVC-002). "
                "Returning empty artifact list."
            )

            # 5. Build result
            duration_ms = (time.time() - start_time) * 1000

            return ScanResultDTO(
                source_id="",  # Set by caller
                status="success",
                artifacts_found=len(artifacts),
                new_count=len(artifacts),  # All new on first scan
                updated_count=0,
                removed_count=0,
                unchanged_count=0,
                scan_duration_ms=duration_ms,
                errors=errors,
                scanned_at=datetime.utcnow(),
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Scan failed for {owner}/{repo}: {e}", exc_info=True)
            errors.append(str(e))

            return ScanResultDTO(
                source_id="",
                status="error",
                artifacts_found=0,
                new_count=0,
                updated_count=0,
                removed_count=0,
                unchanged_count=0,
                scan_duration_ms=duration_ms,
                errors=errors,
                scanned_at=datetime.utcnow(),
            )

    def _fetch_tree(
        self,
        owner: str,
        repo: str,
        ref: str,
    ) -> List[Dict[str, Any]]:
        """Fetch repository tree using Git Trees API.

        Uses recursive tree fetch for efficiency.

        Args:
            owner: Repository owner
            repo: Repository name
            ref: Git reference (branch, tag, SHA)

        Returns:
            List of tree items with path and type information

        Raises:
            GitHubAPIError: If API call fails
        """
        url = f"{self.API_BASE}/repos/{owner}/{repo}/git/trees/{ref}?recursive=1"
        response = self._request_with_retry(url)

        data = response.json()
        if "tree" not in data:
            raise GitHubAPIError(f"Invalid tree response: {data}")

        return data["tree"]

    def _extract_file_paths(
        self,
        tree: List[Dict[str, Any]],
        root_hint: Optional[str] = None,
    ) -> List[str]:
        """Extract file paths from tree, optionally filtering by root_hint.

        Args:
            tree: Tree items from GitHub API
            root_hint: Optional subdirectory to filter by

        Returns:
            List of file paths
        """
        paths = []

        for item in tree:
            if item.get("type") != "blob":
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
            GitHubAPIError: If API call fails
        """
        url = f"{self.API_BASE}/repos/{owner}/{repo}/commits/{ref}"
        response = self._request_with_retry(url)
        data = response.json()
        return data.get("sha", "")

    def _request_with_retry(self, url: str) -> requests.Response:
        """Make HTTP request with retry logic for rate limits.

        Implements exponential backoff for transient failures and handles
        GitHub rate limiting with appropriate wait times.

        Args:
            url: URL to request

        Returns:
            Response object

        Raises:
            GitHubAPIError: If request fails after retries
            RateLimitError: If rate limited and cannot wait
        """
        for attempt in range(self.config.retry_count):
            try:
                response = self.session.get(url, timeout=self.config.timeout)

                # Check for rate limiting (403 with rate limit headers)
                if response.status_code == 403:
                    remaining = response.headers.get("X-RateLimit-Remaining", "0")
                    if remaining == "0":
                        reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                        wait_time = max(reset_time - time.time(), 0)
                        if wait_time < 60:  # Only wait if less than 1 minute
                            logger.warning(f"Rate limited, waiting {wait_time:.0f}s")
                            time.sleep(wait_time + 1)
                            continue
                        raise RateLimitError(f"Rate limited, reset in {wait_time:.0f}s")

                # Check for explicit rate limit response (429)
                if response.status_code == 429:
                    retry_after = int(
                        response.headers.get("Retry-After", self.config.retry_delay)
                    )
                    if retry_after < 60:
                        time.sleep(retry_after)
                        continue
                    raise RateLimitError(f"Rate limited for {retry_after}s")

                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as e:
                if attempt < self.config.retry_count - 1:
                    wait_time = self.config.retry_delay * (2**attempt)
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    raise GitHubAPIError(
                        f"Request failed after {self.config.retry_count} attempts: {e}"
                    ) from e

        raise GitHubAPIError("Max retries exceeded")

    def get_file_content(
        self, owner: str, repo: str, path: str, ref: str = "main"
    ) -> str:
        """Fetch content of a specific file.

        Useful for extracting metadata from manifest files.

        Args:
            owner: Repository owner
            repo: Repository name
            path: File path within repository
            ref: Git reference (branch, tag, SHA)

        Returns:
            Decoded file content

        Raises:
            GitHubAPIError: If API call fails
        """
        import base64

        url = f"{self.API_BASE}/repos/{owner}/{repo}/contents/{path}?ref={ref}"
        response = self._request_with_retry(url)
        data = response.json()

        if data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8")

        return data.get("content", "")


class GitHubAPIError(Exception):
    """Error from GitHub API."""

    pass


class RateLimitError(GitHubAPIError):
    """Rate limit exceeded."""

    pass


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

    # Fetch tree and detect
    tree = scanner._fetch_tree(owner, repo, ref)
    file_paths = scanner._extract_file_paths(tree, root_hint)
    commit_sha = scanner._get_ref_sha(owner, repo, ref)

    # NOTE: This will be uncommented once SVC-002 (heuristic detector) is implemented
    # artifacts = detect_artifacts_in_tree(
    #     file_paths,
    #     repo_url=repo_url,
    #     ref=ref,
    #     root_hint=root_hint,
    #     detected_sha=commit_sha,
    # )

    # Placeholder until heuristic detector is implemented
    artifacts = []
    logger.warning(
        "Heuristic detector not yet implemented (SVC-002). "
        "Returning empty artifact list."
    )

    result = ScanResultDTO(
        source_id="",
        status="success",
        artifacts_found=len(artifacts),
        new_count=len(artifacts),
        updated_count=0,
        removed_count=0,
        unchanged_count=0,
        scan_duration_ms=0,
        errors=[],
        scanned_at=datetime.utcnow(),
    )

    return result, artifacts
