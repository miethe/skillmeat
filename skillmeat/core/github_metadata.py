"""GitHub metadata extraction service.

Provides GitHub repository metadata extraction with caching support for SkillMeat
artifact auto-population.
"""

import base64
import logging
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
import yaml
from pydantic import BaseModel, Field

from skillmeat.core.cache import MetadataCache
from skillmeat.core.discovery_metrics import (
    discovery_metrics,
    github_metadata_fetch_duration,
    github_metadata_requests_total,
    log_performance,
)

logger = logging.getLogger(__name__)


class GitHubSourceSpec(BaseModel):
    """Parsed GitHub source specification.

    Represents a parsed GitHub artifact source with owner, repository,
    path within the repository, and version information.

    Attributes:
        owner: GitHub username or organization
        repo: Repository name
        path: Path to artifact within repository
        version: Version specifier (tag, SHA, branch name, or "latest")
    """

    owner: str
    repo: str
    path: str
    version: Optional[str] = "latest"


class GitHubMetadata(BaseModel):
    """GitHub repository and artifact metadata.

    Contains metadata extracted from GitHub repository and artifact files,
    including frontmatter from markdown files and repository-level information.

    Attributes:
        title: Artifact title from frontmatter
        description: Artifact description from frontmatter
        author: Artifact author from frontmatter
        license: Repository license identifier (SPDX)
        topics: Repository topics/tags
        url: Full GitHub URL to the artifact
        fetched_at: Timestamp when metadata was fetched
        source: Source of metadata (always "auto-populated")
    """

    title: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    license: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    url: str
    fetched_at: datetime
    source: str = "auto-populated"


class GitHubMetadataExtractor:
    """Extracts metadata from GitHub repositories with caching.

    Provides GitHub API integration for fetching artifact metadata including
    YAML frontmatter from markdown files and repository-level metadata like
    topics and license information.

    Attributes:
        cache: MetadataCache instance for caching responses
        token: Optional GitHub personal access token for higher rate limits
        session: Requests session with authentication if token provided
        base_url: GitHub API base URL
    """

    def __init__(self, cache: MetadataCache, token: Optional[str] = None):
        """Initialize GitHub metadata extractor.

        Args:
            cache: MetadataCache instance for caching API responses
            token: Optional GitHub personal access token. If not provided,
                will check SKILLMEAT_GITHUB_TOKEN then GITHUB_TOKEN environment
                variables. Used for higher rate limits (5000/hr vs 60/hr
                unauthenticated).
        """
        self.cache = cache
        # Priority: explicit token > SKILLMEAT_GITHUB_TOKEN env > GITHUB_TOKEN env
        self.token = (
            token
            or os.environ.get("SKILLMEAT_GITHUB_TOKEN")
            or os.environ.get("GITHUB_TOKEN")
        )
        self.session = requests.Session()

        if self.token:
            self.session.headers["Authorization"] = f"token {self.token}"
            logger.debug("GitHub token configured for authentication")

        self.base_url = "https://api.github.com"

    def parse_github_url(self, url: str) -> GitHubSourceSpec:
        """Parse GitHub URL or spec string into components.

        Supports multiple URL formats:
        - Short format: user/repo/path/to/artifact
        - Versioned: user/repo/path@v1.0.0 or @abc1234 (SHA)
        - HTTPS: https://github.com/user/repo/tree/main/path

        Args:
            url: GitHub URL or spec string to parse

        Returns:
            GitHubSourceSpec with parsed owner, repo, path, and version

        Raises:
            ValueError: If URL format is invalid or missing required components

        Examples:
            >>> extractor.parse_github_url("anthropics/skills/canvas")
            GitHubSourceSpec(owner='anthropics', repo='skills', path='canvas', version='latest')

            >>> extractor.parse_github_url("user/repo/path@v1.0.0")
            GitHubSourceSpec(owner='user', repo='repo', path='path', version='v1.0.0')

            >>> extractor.parse_github_url("https://github.com/user/repo/tree/main/path")
            GitHubSourceSpec(owner='user', repo='repo', path='path', version='latest')
        """
        original_url = url

        # Handle HTTPS GitHub URLs
        if url.startswith("https://github.com/"):
            parsed = urlparse(url)
            # URL format: https://github.com/owner/repo/tree/ref/path/to/artifact
            path_parts = parsed.path.strip("/").split("/")

            if len(path_parts) < 2:
                raise ValueError(
                    f"Invalid GitHub URL: {original_url}. "
                    "Expected format: https://github.com/owner/repo/tree/ref/path"
                )

            owner = path_parts[0]
            repo = path_parts[1]

            # Check if there's a /tree/ref/ part
            if len(path_parts) > 3 and path_parts[2] == "tree":
                # Skip /tree/ref and get the rest as path
                path = "/".join(path_parts[4:]) if len(path_parts) > 4 else ""
            else:
                # No /tree/ref, just owner/repo
                path = ""

            version = "latest"

        else:
            # Handle short format: user/repo/path[@version]

            # Split version from spec
            if "@" in url:
                spec_without_version, version = url.rsplit("@", 1)
            else:
                spec_without_version = url
                version = "latest"

            # Parse owner/repo/path
            parts = spec_without_version.split("/")

            if len(parts) < 2:
                raise ValueError(
                    f"Invalid GitHub spec: {original_url}. "
                    "Expected format: owner/repo or owner/repo/path or owner/repo/path@version"
                )

            owner = parts[0]
            repo = parts[1]
            path = "/".join(parts[2:]) if len(parts) > 2 else ""

        logger.debug(
            f"Parsed GitHub URL: owner={owner}, repo={repo}, path={path}, version={version}"
        )

        return GitHubSourceSpec(owner=owner, repo=repo, path=path, version=version)

    @log_performance("metadata_fetch")
    def fetch_metadata(self, source: str) -> GitHubMetadata:
        """Fetch metadata from GitHub with caching support.

        Retrieves metadata from GitHub API including:
        1. YAML frontmatter from artifact markdown files (SKILL.md, etc.)
        2. Repository metadata (topics, license)

        Results are cached based on the source string to reduce API calls.

        Args:
            source: GitHub source spec (e.g., "user/repo/path@version")

        Returns:
            GitHubMetadata with all available metadata

        Raises:
            ValueError: If source format is invalid
            RuntimeError: If GitHub API rate limit exceeded or other API errors

        Examples:
            >>> metadata = extractor.fetch_metadata("anthropics/skills/canvas-design")
            >>> print(metadata.title)
            'Canvas Design'
            >>> print(metadata.topics)
            ['design', 'canvas', 'art']
        """
        start_time = time.perf_counter()

        # Check cache first
        cache_key = f"github_metadata:{source}"
        cached = self.cache.get(cache_key)

        if cached:
            logger.info(
                "Cache hit for GitHub metadata",
                extra={"source": source, "cache_hit": True},
            )
            github_metadata_requests_total.labels(cache_hit="true").inc()
            discovery_metrics.record_metadata_fetch(cache_hit=True)
            return GitHubMetadata(**cached)

        logger.info(
            "Fetching metadata from GitHub",
            extra={"source": source, "cache_hit": False},
        )
        github_metadata_requests_total.labels(cache_hit="false").inc()
        discovery_metrics.record_metadata_fetch(cache_hit=False)

        # Parse source to get owner/repo/path
        try:
            spec = self.parse_github_url(source)
        except ValueError as e:
            raise ValueError(f"Invalid GitHub source: {e}")

        # Initialize metadata with URL
        url = f"https://github.com/{spec.owner}/{spec.repo}"
        if spec.path:
            url += f"/tree/{spec.version}/{spec.path}"

        metadata_dict: Dict[str, Any] = {
            "url": url,
            "fetched_at": datetime.now(),
            "source": "auto-populated",
            "topics": [],
        }

        # Try to fetch file content and extract frontmatter
        # Look for standard metadata files in order of preference
        metadata_files = ["SKILL.md", "COMMAND.md", "AGENT.md", "README.md"]

        frontmatter_data = None
        for filename in metadata_files:
            file_path = f"{spec.path}/{filename}" if spec.path else filename
            content = self._fetch_file_content(
                spec.owner, spec.repo, file_path, spec.version
            )

            if content:
                logger.debug(f"Found {filename} for {source}")
                frontmatter_data = self._extract_frontmatter(content)
                if frontmatter_data:
                    break

        # Extract frontmatter fields
        if frontmatter_data:
            metadata_dict["title"] = frontmatter_data.get("title")
            metadata_dict["description"] = frontmatter_data.get("description")
            metadata_dict["author"] = frontmatter_data.get("author")

        # Fetch repository metadata (topics, license)
        repo_metadata = self._fetch_repo_metadata(spec.owner, spec.repo)
        if repo_metadata:
            metadata_dict["topics"] = repo_metadata.get("topics", [])
            license_info = repo_metadata.get("license")
            if license_info and isinstance(license_info, dict):
                metadata_dict["license"] = license_info.get("spdx_id")

        # Create metadata object
        metadata = GitHubMetadata(**metadata_dict)

        # Cache the result
        self.cache.set(cache_key, metadata.model_dump())

        # Record duration
        duration = time.perf_counter() - start_time
        github_metadata_fetch_duration.observe(duration)

        logger.info(
            f"Cached metadata for {source}",
            extra={
                "source": source,
                "duration_ms": round(duration * 1000, 2),
                "has_title": metadata.title is not None,
                "has_description": metadata.description is not None,
            },
        )

        return metadata

    def _retry_with_backoff(self, func, max_retries: int = 3):
        """Retry function with exponential backoff on network errors.

        Retries the given function up to max_retries times with exponential
        backoff (2^attempt seconds) between attempts on network failures.

        Args:
            func: Function to retry (should return a value or raise exception)
            max_retries: Maximum number of retry attempts

        Returns:
            Result from successful function call

        Raises:
            Last exception if all retries fail
        """
        for attempt in range(max_retries):
            try:
                return func()
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    # Last attempt, re-raise
                    raise

                wait_time = 2**attempt
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{max_retries}), "
                    f"retrying in {wait_time}s: {e}"
                )
                time.sleep(wait_time)

    def _fetch_file_content(
        self, owner: str, repo: str, path: str, ref: str = "HEAD"
    ) -> Optional[str]:
        """Fetch file content from GitHub Contents API.

        Retrieves file content from GitHub repository using the Contents API.
        Content is base64 encoded in the API response and decoded here.

        Args:
            owner: Repository owner (username or organization)
            repo: Repository name
            path: Path to file within repository
            ref: Git ref (branch, tag, SHA, or "HEAD")

        Returns:
            Decoded file content as string, or None if file not found

        Note:
            Handles 404 errors gracefully by returning None.
            Logs warnings for missing files, errors for API failures.
        """

        def fetch():
            url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
            params = {"ref": ref} if ref != "HEAD" else {}

            response = self.session.get(url, params=params, timeout=10)

            # Handle 404 - file not found (expected for many files)
            if response.status_code == 404:
                logger.debug(f"File not found: {path} in {owner}/{repo}")
                return None

            # Handle rate limiting
            if response.status_code == 429:
                logger.error(
                    f"GitHub API rate limit exceeded. "
                    f"Consider setting GITHUB_TOKEN environment variable for higher limits."
                )
                raise RuntimeError(
                    "GitHub API rate limit exceeded. Use a GitHub token for higher limits."
                )

            # Handle forbidden (might be rate limit without 429)
            if response.status_code == 403:
                # Check if it's rate limiting
                if "rate limit" in response.text.lower():
                    logger.error("GitHub API rate limit exceeded (403 forbidden)")
                    raise RuntimeError(
                        "GitHub API rate limit exceeded. Use a GitHub token for higher limits."
                    )

            # Raise for other HTTP errors
            response.raise_for_status()

            # Decode base64 content
            data = response.json()
            if "content" not in data:
                logger.warning(f"No content field in response for {path}")
                return None

            content_b64 = data["content"]
            content_bytes = base64.b64decode(content_b64)
            content_str = content_bytes.decode("utf-8")

            return content_str

        try:
            return self._retry_with_backoff(fetch)
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch {path} from {owner}/{repo}: {e}")
            return None

    def _extract_frontmatter(self, content: str) -> Dict[str, Any]:
        """Extract YAML frontmatter from markdown content.

        Looks for YAML frontmatter delimited by --- at the start of the file:
        ---
        title: My Artifact
        description: Does something
        author: Author Name
        ---

        Args:
            content: Markdown file content

        Returns:
            Dictionary of frontmatter data, or empty dict if no frontmatter

        Note:
            Gracefully handles YAML parsing errors by returning empty dict.
            Uses regex pattern from skillmeat/utils/metadata.py
        """
        if not content or not content.strip():
            return {}

        # Match YAML frontmatter: --- ... ---
        # Must be at start of file
        pattern = r"^---\s*\n(.*?)\n---\s*\n"
        match = re.match(pattern, content, re.DOTALL)

        if not match:
            logger.debug("No YAML frontmatter found in content")
            return {}

        yaml_content = match.group(1)

        try:
            data = yaml.safe_load(yaml_content)
            if isinstance(data, dict):
                logger.debug(f"Extracted frontmatter with {len(data)} fields")
                return data
            else:
                logger.warning("YAML frontmatter is not a dictionary")
                return {}
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse YAML frontmatter: {e}")
            return {}

    def _fetch_repo_metadata(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch repository metadata from GitHub Repositories API.

        Retrieves repository-level metadata including topics, license,
        description, and other repository information.

        Args:
            owner: Repository owner (username or organization)
            repo: Repository name

        Returns:
            Dictionary with repository metadata (topics, license, etc.),
            or empty dict if fetch fails

        Note:
            Handles errors gracefully by returning empty dict.
            Topics and license information are the primary fields used.
        """

        def fetch():
            url = f"{self.base_url}/repos/{owner}/{repo}"
            response = self.session.get(url, timeout=10)

            # Handle rate limiting
            if response.status_code == 429:
                logger.error("GitHub API rate limit exceeded")
                raise RuntimeError(
                    "GitHub API rate limit exceeded. Use a GitHub token for higher limits."
                )

            # Handle forbidden
            if response.status_code == 403:
                if "rate limit" in response.text.lower():
                    logger.error("GitHub API rate limit exceeded (403 forbidden)")
                    raise RuntimeError(
                        "GitHub API rate limit exceeded. Use a GitHub token for higher limits."
                    )

            # Raise for other HTTP errors
            response.raise_for_status()

            return response.json()

        try:
            data = self._retry_with_backoff(fetch)
            logger.debug(f"Fetched repository metadata for {owner}/{repo}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch repository metadata for {owner}/{repo}: {e}")
            return {}
