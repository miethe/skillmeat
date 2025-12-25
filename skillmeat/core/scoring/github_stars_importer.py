"""GitHub stars importer for artifact quality signals.

This module provides the GitHubStarsImporter class for fetching GitHub repository
statistics and converting them to quality signals (ScoreSource objects) for artifacts.

The importer uses the GitHub REST API to fetch repository data, caches results to
minimize API calls, and handles rate limiting with exponential backoff.

Example:
    >>> from skillmeat.core.scoring.github_stars_importer import GitHubStarsImporter
    >>> from datetime import datetime
    >>>
    >>> # Initialize with optional GitHub token
    >>> importer = GitHubStarsImporter(token="ghp_xxx", cache_ttl_hours=24)
    >>>
    >>> # Fetch stats for a single artifact
    >>> import asyncio
    >>> score_source = asyncio.run(importer.import_for_artifact("anthropics/skills/pdf"))
    >>> print(f"Score: {score_source.score}, Sample: {score_source.sample_size}")
    >>>
    >>> # Batch import for multiple artifacts
    >>> sources = ["anthropics/skills/pdf", "user/repo/skill"]
    >>> results = asyncio.run(importer.batch_import(sources))
"""

import asyncio
import json
import logging
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import httpx
from sqlalchemy.exc import IntegrityError

from skillmeat.cache.models import get_session
from skillmeat.core.scoring.score_aggregator import ScoreSource

logger = logging.getLogger(__name__)


# =============================================================================
# Exception Classes
# =============================================================================


class GitHubAPIError(Exception):
    """Base exception for GitHub API errors."""

    pass


class RateLimitError(GitHubAPIError):
    """Rate limit exceeded.

    Attributes:
        reset_at: Datetime when rate limit resets
    """

    def __init__(self, message: str, reset_at: datetime):
        super().__init__(message)
        self.reset_at = reset_at


class RepoNotFoundError(GitHubAPIError):
    """Repository not found (404)."""

    pass


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class GitHubRepoStats:
    """Stats from a GitHub repository.

    Attributes:
        owner: Repository owner (username or org)
        repo: Repository name
        stars: Number of stars (stargazers_count)
        forks: Number of forks
        watchers: Number of watchers
        open_issues: Number of open issues
        last_updated: Last update timestamp from GitHub (updated_at)
        fetched_at: Timestamp when stats were fetched
    """

    owner: str
    repo: str
    stars: int
    forks: int
    watchers: int
    open_issues: int
    last_updated: datetime
    fetched_at: datetime


# =============================================================================
# GitHub Stars Importer
# =============================================================================


class GitHubStarsImporter:
    """Import GitHub stars as quality signals for artifacts.

    This class fetches repository statistics from the GitHub API and converts
    star counts to normalized quality scores (0-100) using a logarithmic scale.

    The importer includes:
    - Caching to minimize API calls (configurable TTL)
    - Rate limit handling with exponential backoff
    - Batch import with concurrency control
    - Artifact source parsing (username/repo/path[@version])

    Attributes:
        token: Optional GitHub personal access token
        cache_ttl_hours: Cache TTL in hours (default: 24)

    Example:
        >>> importer = GitHubStarsImporter(token="ghp_xxx")
        >>> stats = await importer.fetch_repo_stats("anthropics", "skills")
        >>> print(f"Stars: {stats.stars}")
        >>>
        >>> score = importer.normalize_stars_to_score(stats.stars)
        >>> print(f"Normalized score: {score}")
    """

    GITHUB_API_BASE = "https://api.github.com"
    USER_AGENT = "skillmeat"

    def __init__(
        self,
        token: Optional[str] = None,
        cache_ttl_hours: int = 24,
    ):
        """Initialize importer with optional GitHub token.

        Args:
            token: GitHub personal access token (optional)
                - Without token: 60 requests/hour
                - With token: 5000 requests/hour
            cache_ttl_hours: Cache TTL in hours (default: 24)

        Example:
            >>> # Unauthenticated (60 req/hour)
            >>> importer = GitHubStarsImporter()
            >>>
            >>> # Authenticated (5000 req/hour)
            >>> importer = GitHubStarsImporter(token="ghp_xxx")
        """
        self.token = token
        self.cache_ttl_hours = cache_ttl_hours

    async def fetch_repo_stats(self, owner: str, repo: str) -> GitHubRepoStats:
        """Fetch repository statistics from GitHub API.

        First checks cache, then fetches from API if cache miss or expired.
        Implements exponential backoff for rate limiting.

        Args:
            owner: Repository owner (username or org)
            repo: Repository name

        Returns:
            GitHubRepoStats with current repository statistics

        Raises:
            RepoNotFoundError: If repository doesn't exist (404)
            RateLimitError: If rate limit exceeded (403)
            GitHubAPIError: For other API errors

        Example:
            >>> stats = await importer.fetch_repo_stats("anthropics", "skills")
            >>> print(f"Stars: {stats.stars}, Forks: {stats.forks}")
        """
        # Check cache first
        cached_stats = self._get_cached_stats(owner, repo)
        if cached_stats:
            logger.debug(f"Cache hit for {owner}/{repo}")
            return cached_stats

        # Fetch from API
        logger.debug(f"Cache miss for {owner}/{repo}, fetching from API")
        url = f"{self.GITHUB_API_BASE}/repos/{owner}/{repo}"

        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "application/vnd.github.v3+json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        # Retry with exponential backoff
        max_retries = 3
        retry_delay = 1  # seconds

        async with httpx.AsyncClient() as client:
            for attempt in range(max_retries):
                try:
                    response = await client.get(url, headers=headers, timeout=10.0)

                    # Log rate limit headers
                    if "X-RateLimit-Remaining" in response.headers:
                        remaining = response.headers["X-RateLimit-Remaining"]
                        reset = response.headers.get("X-RateLimit-Reset", "unknown")
                        logger.debug(
                            f"Rate limit: {remaining} remaining, resets at {reset}"
                        )

                    # Handle errors
                    if response.status_code == 404:
                        raise RepoNotFoundError(f"Repository {owner}/{repo} not found")
                    elif response.status_code == 403:
                        # Rate limit exceeded
                        reset_timestamp = int(
                            response.headers.get("X-RateLimit-Reset", 0)
                        )
                        reset_at = datetime.fromtimestamp(
                            reset_timestamp, tz=timezone.utc
                        )
                        raise RateLimitError(
                            f"Rate limit exceeded. Resets at {reset_at}", reset_at
                        )
                    elif not response.is_success:
                        raise GitHubAPIError(
                            f"GitHub API error: {response.status_code} - {response.text}"
                        )

                    # Parse response
                    data = response.json()
                    stats = GitHubRepoStats(
                        owner=owner,
                        repo=repo,
                        stars=data.get("stargazers_count", 0),
                        forks=data.get("forks_count", 0),
                        watchers=data.get("watchers_count", 0),
                        open_issues=data.get("open_issues_count", 0),
                        last_updated=datetime.fromisoformat(
                            data["updated_at"].replace("Z", "+00:00")
                        ),
                        fetched_at=datetime.now(timezone.utc),
                    )

                    # Cache result
                    self._cache_stats(stats)

                    return stats

                except (httpx.TimeoutException, httpx.NetworkError) as e:
                    if attempt == max_retries - 1:
                        raise GitHubAPIError(
                            f"Network error fetching {owner}/{repo}: {e}"
                        )
                    logger.warning(
                        f"Network error (attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff

        # Should not reach here
        raise GitHubAPIError(
            f"Failed to fetch {owner}/{repo} after {max_retries} retries"
        )

    def normalize_stars_to_score(self, stars: int) -> float:
        """Normalize star count to 0-100 score using logarithmic scale.

        Uses logarithmic scale to handle wide range of star counts:
        - 0 stars = 0
        - 10 stars = 40
        - 100 stars = 60
        - 1000 stars = 80
        - 10000+ stars = 95-100

        Args:
            stars: Number of stars (>= 0)

        Returns:
            Normalized score (0-100)

        Example:
            >>> importer = GitHubStarsImporter()
            >>> importer.normalize_stars_to_score(0)
            0.0
            >>> importer.normalize_stars_to_score(10)
            40.0
            >>> importer.normalize_stars_to_score(100)
            60.0
            >>> importer.normalize_stars_to_score(1000)
            80.0
            >>> importer.normalize_stars_to_score(10000)
            95.0
        """
        if stars <= 0:
            return 0.0

        # Logarithmic scaling: score = 20 * log10(stars) + 20
        # This gives approximately:
        # 1 star = 20, 10 stars = 40, 100 stars = 60, 1000 stars = 80, 10000 stars = 100
        score = 20.0 * math.log10(stars) + 20.0

        # Clamp to 0-100 range
        score = min(100.0, max(0.0, score))

        # Cap at 95 for 10000+ stars (leave room for exceptional repos)
        if stars >= 10000:
            score = min(95.0, score)

        return round(score, 1)

    async def import_for_artifact(
        self,
        artifact_source: str,
    ) -> Optional[ScoreSource]:
        """Import GitHub stats and convert to ScoreSource.

        Parses artifact source to extract owner/repo. Returns None if source
        is not a GitHub repo (e.g., local path).

        Args:
            artifact_source: Artifact source string (e.g., "anthropics/skills/pdf")

        Returns:
            ScoreSource object or None if not a GitHub source

        Example:
            >>> # GitHub source
            >>> score = await importer.import_for_artifact("anthropics/skills/pdf")
            >>> print(f"Score: {score.score}, Sample: {score.sample_size}")
            >>>
            >>> # Local source
            >>> score = await importer.import_for_artifact("/local/path")
            >>> assert score is None
        """
        # Parse artifact source: "owner/repo/path[@version]"
        parsed = self._parse_artifact_source(artifact_source)
        if not parsed:
            logger.debug(f"Not a GitHub source: {artifact_source}")
            return None

        owner, repo = parsed

        try:
            stats = await self.fetch_repo_stats(owner, repo)

            return ScoreSource(
                source_name="github_stars",
                score=self.normalize_stars_to_score(stats.stars),
                weight=0.25,  # From DEFAULT_SOURCE_WEIGHTS
                last_updated=stats.last_updated,
                sample_size=stats.stars,  # Use star count as sample size
            )

        except RepoNotFoundError:
            logger.warning(f"Repository not found: {owner}/{repo}")
            return None
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            raise
        except GitHubAPIError as e:
            logger.error(f"GitHub API error for {owner}/{repo}: {e}")
            return None

    async def batch_import(
        self,
        artifact_sources: List[str],
        concurrency: int = 5,
    ) -> List[ScoreSource]:
        """Import stars for multiple artifacts with rate limit awareness.

        Fetches GitHub stats for multiple artifacts concurrently with controlled
        concurrency to respect rate limits.

        Args:
            artifact_sources: List of artifact source strings
            concurrency: Max concurrent requests (default: 5)

        Returns:
            List of ScoreSource objects (one per valid GitHub artifact)

        Example:
            >>> sources = [
            ...     "anthropics/skills/pdf",
            ...     "user/repo/skill",
            ...     "/local/path",  # Will be skipped
            ... ]
            >>> results = await importer.batch_import(sources, concurrency=3)
            >>> print(f"Imported {len(results)} scores")
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def _fetch_with_semaphore(source: str) -> Optional[ScoreSource]:
            async with semaphore:
                return await self.import_for_artifact(source)

        tasks = [_fetch_with_semaphore(source) for source in artifact_sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out None and exceptions
        score_sources = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error importing {artifact_sources[i]}: {result}")
            elif result is not None:
                score_sources.append(result)

        logger.info(
            f"Batch import: {len(score_sources)}/{len(artifact_sources)} successful"
        )

        return score_sources

    # =========================================================================
    # Private Methods
    # =========================================================================

    def _parse_artifact_source(self, source: str) -> Optional[tuple[str, str]]:
        """Parse artifact source to extract owner/repo.

        Args:
            source: Artifact source string (e.g., "owner/repo/path[@version]")

        Returns:
            Tuple of (owner, repo) or None if not a GitHub source

        Example:
            >>> importer = GitHubStarsImporter()
            >>> importer._parse_artifact_source("anthropics/skills/pdf")
            ('anthropics', 'skills')
            >>> importer._parse_artifact_source("user/repo/path@v1.0")
            ('user', 'repo')
            >>> importer._parse_artifact_source("/local/path")
            None
        """
        # Remove version suffix if present
        source = source.split("@")[0]

        # Split by '/'
        parts = source.split("/")

        # Need at least owner/repo
        if len(parts) < 2:
            return None

        # Check if it looks like a filesystem path (starts with '/', '~', or '.')
        if source.startswith(("/", "~", ".")):
            return None

        owner, repo = parts[0], parts[1]

        # Validate owner and repo are non-empty
        if not owner or not repo:
            return None

        return (owner, repo)

    def _get_cached_stats(self, owner: str, repo: str) -> Optional[GitHubRepoStats]:
        """Get cached stats from database.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Cached GitHubRepoStats or None if cache miss or expired
        """
        session = get_session()
        try:
            from skillmeat.cache.models import GitHubRepoCache

            cache_key = f"{owner}/{repo}"
            entry = (
                session.query(GitHubRepoCache).filter_by(cache_key=cache_key).first()
            )

            if not entry:
                return None

            # Check if expired
            now = datetime.now(timezone.utc)
            # Convert naive datetime to aware if needed
            fetched_at = entry.fetched_at
            if fetched_at.tzinfo is None:
                fetched_at = fetched_at.replace(tzinfo=timezone.utc)

            cache_age = (now - fetched_at).total_seconds() / 3600  # hours
            if cache_age > self.cache_ttl_hours:
                logger.debug(f"Cache expired for {cache_key} (age: {cache_age:.1f}h)")
                return None

            # Parse JSON data
            data = json.loads(entry.data)
            return GitHubRepoStats(
                owner=data["owner"],
                repo=data["repo"],
                stars=data["stars"],
                forks=data["forks"],
                watchers=data["watchers"],
                open_issues=data["open_issues"],
                last_updated=datetime.fromisoformat(data["last_updated"]),
                fetched_at=datetime.fromisoformat(data["fetched_at"]),
            )

        finally:
            session.close()

    def _cache_stats(self, stats: GitHubRepoStats) -> None:
        """Cache stats to database.

        Args:
            stats: GitHubRepoStats to cache
        """
        session = get_session()
        try:
            from skillmeat.cache.models import GitHubRepoCache

            cache_key = f"{stats.owner}/{stats.repo}"

            # Serialize stats to JSON
            data = asdict(stats)
            # Convert datetime objects to ISO format strings
            data["last_updated"] = stats.last_updated.isoformat()
            data["fetched_at"] = stats.fetched_at.isoformat()

            # Upsert: delete existing, insert new
            session.query(GitHubRepoCache).filter_by(cache_key=cache_key).delete()
            entry = GitHubRepoCache(
                cache_key=cache_key,
                data=json.dumps(data),
                fetched_at=stats.fetched_at,
            )
            session.add(entry)
            session.commit()

            logger.debug(f"Cached stats for {cache_key}")

        except IntegrityError as e:
            session.rollback()
            logger.warning(f"Failed to cache stats for {cache_key}: {e}")
        finally:
            session.close()
