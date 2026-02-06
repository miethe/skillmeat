"""Centralized GitHub API client wrapper using PyGithub.

Provides a unified interface for GitHub API operations with configurable
authentication, rate limiting, and SkillMeat-specific error handling.

Token Resolution Priority:
    1. Explicit token parameter passed to constructor
    2. ConfigManager at `settings.github-token`
    3. SKILLMEAT_GITHUB_TOKEN environment variable
    4. GITHUB_TOKEN environment variable
    5. Unauthenticated (60 req/hr fallback)

Example:
    >>> from skillmeat.core.github_client import get_github_client
    >>>
    >>> # Get singleton client (uses token resolution priority)
    >>> client = get_github_client()
    >>>
    >>> # Get repository metadata
    >>> metadata = client.get_repo_metadata("anthropics/skills")
    >>> print(f"Stars: {metadata['stars']}, Topics: {metadata['topics']}")
    >>>
    >>> # Get file content
    >>> content = client.get_file_content("anthropics/skills", "SKILL.md")
    >>>
    >>> # Resolve version to SHA
    >>> sha = client.resolve_version("anthropics/skills", "latest")
"""

import base64
import logging
import os
import posixpath
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from github import Auth, Github, GithubException
from github.ContentFile import ContentFile
from github.GithubException import (
    BadCredentialsException,
    RateLimitExceededException,
    UnknownObjectException,
)
from github.GithubObject import NotSet
from github.Repository import Repository

from skillmeat.config import ConfigManager

logger = logging.getLogger(__name__)


# =============================================================================
# Exception Classes
# =============================================================================


class GitHubClientError(Exception):
    """Base exception for GitHub client errors.

    All SkillMeat-specific GitHub errors inherit from this class.

    Attributes:
        message: Error description
        original_error: The underlying exception, if any
    """

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.original_error = original_error


class GitHubRateLimitError(GitHubClientError):
    """GitHub API rate limit exceeded.

    Attributes:
        remaining: Requests remaining (usually 0)
        limit: Total request limit (60 unauthenticated, 5000 authenticated)
        reset_at: Datetime when rate limit resets
    """

    def __init__(
        self,
        message: str,
        remaining: int = 0,
        limit: int = 0,
        reset_at: Optional[datetime] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message, original_error)
        self.remaining = remaining
        self.limit = limit
        self.reset_at = reset_at


class GitHubAuthError(GitHubClientError):
    """GitHub authentication failed.

    Raised when the provided token is invalid or lacks required scopes.
    """

    pass


class GitHubNotFoundError(GitHubClientError):
    """GitHub resource not found.

    Raised when a repository, file, or ref does not exist.
    """

    pass


# =============================================================================
# GitHub Client
# =============================================================================


class GitHubClient:
    """Centralized GitHub API client using PyGithub.

    Provides a unified interface for GitHub API operations with automatic
    token resolution from multiple sources and SkillMeat-specific error handling.

    Token Resolution Priority:
        1. Explicit token parameter passed to constructor
        2. ConfigManager at `settings.github-token`
        3. SKILLMEAT_GITHUB_TOKEN environment variable
        4. GITHUB_TOKEN environment variable
        5. Unauthenticated (60 req/hr fallback)

    Attributes:
        _token: Resolved GitHub token (or None for unauthenticated)
        _github: Lazily initialized PyGithub client

    Example:
        >>> client = GitHubClient()
        >>> repo = client.get_repo("anthropics/skills")
        >>> print(repo.full_name)
        'anthropics/skills'
    """

    def __init__(self, token: Optional[str] = None):
        """Initialize GitHub client with token resolution.

        Args:
            token: Explicit GitHub token. If not provided, token is resolved
                from ConfigManager, then environment variables, in priority order.
        """
        self._token = self._resolve_token(token)
        self._github: Optional[Github] = None

        if self._token:
            logger.info("GitHub client initialized with authentication")
        else:
            logger.info(
                "GitHub client initialized without authentication (60 req/hr limit)"
            )

    def _resolve_token(self, explicit_token: Optional[str]) -> Optional[str]:
        """Resolve GitHub token from multiple sources.

        Priority:
            1. Explicit token parameter
            2. ConfigManager settings.github-token
            3. SKILLMEAT_GITHUB_TOKEN environment variable
            4. GITHUB_TOKEN environment variable

        Args:
            explicit_token: Token passed directly to constructor

        Returns:
            Resolved token string, or None if no token available
        """
        # 1. Explicit token
        if explicit_token:
            return explicit_token

        # 2. ConfigManager
        try:
            config = ConfigManager()
            config_token = config.get("settings.github-token")
            if config_token:
                logger.debug("Using GitHub token from ConfigManager")
                return config_token
        except Exception as e:
            logger.debug(f"Could not read ConfigManager: {e}")

        # 3. SKILLMEAT_GITHUB_TOKEN
        skillmeat_token = os.environ.get("SKILLMEAT_GITHUB_TOKEN")
        if skillmeat_token:
            logger.debug("Using GitHub token from SKILLMEAT_GITHUB_TOKEN")
            return skillmeat_token

        # 4. GITHUB_TOKEN
        github_token = os.environ.get("GITHUB_TOKEN")
        if github_token:
            logger.debug("Using GitHub token from GITHUB_TOKEN")
            return github_token

        # 5. No token - unauthenticated
        return None

    @property
    def token(self) -> Optional[str]:
        """Get the resolved GitHub token.

        Returns:
            The GitHub token string, or None if unauthenticated.
        """
        return self._token

    def _get_client(self) -> Github:
        """Get or create the PyGithub client (lazy initialization).

        Returns:
            Configured Github instance
        """
        if self._github is None:
            # Disable PyGithub's default retry (GithubRetry(total=10)) which
            # retries rate-limited requests with exponential backoff, causing
            # the CLI to hang. SkillMeat handles rate limits in _handle_exception().
            if self._token:
                auth = Auth.Token(self._token)
                self._github = Github(auth=auth, retry=0, timeout=30)
            else:
                self._github = Github(retry=0, timeout=30)
        return self._github

    def _extract_owner_repo(self, owner_repo: str) -> Tuple[str, str]:
        """Extract owner and repo from various formats.

        Supports:
            - "owner/repo"
            - "owner/repo/path/to/something"

        Args:
            owner_repo: Repository identifier in owner/repo format

        Returns:
            Tuple of (owner, repo)

        Raises:
            GitHubClientError: If format is invalid
        """
        parts = owner_repo.strip().split("/")
        if len(parts) < 2:
            raise GitHubClientError(
                f"Invalid repository format: '{owner_repo}'. "
                "Expected 'owner/repo' or 'owner/repo/path'."
            )
        return parts[0], parts[1]

    def _handle_exception(self, e: GithubException, context: str = "") -> None:
        """Convert PyGithub exceptions to SkillMeat exceptions.

        Args:
            e: PyGithub exception
            context: Additional context for error message

        Raises:
            GitHubRateLimitError: If rate limit exceeded
            GitHubAuthError: If authentication failed
            GitHubNotFoundError: If resource not found
            GitHubClientError: For other errors
        """
        ctx = f" ({context})" if context else ""

        if isinstance(e, RateLimitExceededException):
            rate_limit = self.get_rate_limit()
            raise GitHubRateLimitError(
                f"GitHub API rate limit exceeded{ctx}. "
                f"Limit: {rate_limit['limit']}, "
                f"Resets at: {rate_limit['reset']}",
                remaining=rate_limit["remaining"],
                limit=rate_limit["limit"],
                reset_at=rate_limit["reset"],
                original_error=e,
            )

        if isinstance(e, BadCredentialsException):
            raise GitHubAuthError(
                f"GitHub authentication failed{ctx}. "
                "Please verify your token is valid and has required scopes.",
                original_error=e,
            )

        if isinstance(e, UnknownObjectException):
            raise GitHubNotFoundError(
                f"GitHub resource not found{ctx}. "
                "Please verify the repository/path exists and is accessible.",
                original_error=e,
            )

        # Check status code for more specific handling
        status = getattr(e, "status", None)
        if status == 404:
            raise GitHubNotFoundError(
                f"GitHub resource not found{ctx}.",
                original_error=e,
            )
        if status == 401:
            raise GitHubAuthError(
                f"GitHub authentication required{ctx}.",
                original_error=e,
            )
        if status == 403:
            # Could be rate limit or permission issue
            data = getattr(e, "data", {}) or {}
            message = data.get("message", "").lower() if isinstance(data, dict) else ""
            if "rate limit" in message:
                rate_limit = self.get_rate_limit()
                raise GitHubRateLimitError(
                    f"GitHub API rate limit exceeded{ctx}.",
                    remaining=rate_limit["remaining"],
                    limit=rate_limit["limit"],
                    reset_at=rate_limit["reset"],
                    original_error=e,
                )
            raise GitHubAuthError(
                f"GitHub access forbidden{ctx}. "
                "Check token permissions or resource visibility.",
                original_error=e,
            )

        # Generic error
        raise GitHubClientError(
            f"GitHub API error{ctx}: {e}",
            original_error=e,
        )

    # =========================================================================
    # Public API Methods
    # =========================================================================

    def get_repo(self, owner_repo: str) -> Repository:
        """Get a GitHub Repository object.

        Args:
            owner_repo: Repository in "owner/repo" format (may include path)

        Returns:
            PyGithub Repository object

        Raises:
            GitHubNotFoundError: If repository not found
            GitHubAuthError: If authentication required/failed
            GitHubRateLimitError: If rate limit exceeded
            GitHubClientError: For other errors

        Example:
            >>> client = GitHubClient()
            >>> repo = client.get_repo("anthropics/skills")
            >>> print(repo.default_branch)
        """
        owner, repo = self._extract_owner_repo(owner_repo)
        try:
            return self._get_client().get_repo(f"{owner}/{repo}")
        except GithubException as e:
            self._handle_exception(e, context=f"get_repo({owner}/{repo})")
            raise  # This line won't be reached but satisfies type checker

    def get_repo_metadata(self, owner_repo: str) -> Dict[str, Any]:
        """Get repository metadata including stars, topics, and description.

        Args:
            owner_repo: Repository in "owner/repo" format

        Returns:
            Dictionary containing:
                - stars: int - Star count
                - description: str | None - Repository description
                - topics: list[str] - Repository topics/tags
                - default_branch: str - Default branch name
                - license: str | None - License SPDX identifier
                - forks: int - Fork count
                - watchers: int - Watcher count
                - open_issues: int - Open issue count
                - updated_at: datetime - Last update time

        Raises:
            GitHubNotFoundError: If repository not found
            GitHubRateLimitError: If rate limit exceeded
            GitHubClientError: For other errors

        Example:
            >>> client = GitHubClient()
            >>> metadata = client.get_repo_metadata("anthropics/skills")
            >>> print(f"Stars: {metadata['stars']}")
        """
        repo = self.get_repo(owner_repo)
        return {
            "stars": repo.stargazers_count,
            "description": repo.description,
            "topics": repo.get_topics(),
            "default_branch": repo.default_branch,
            "license": repo.license.spdx_id if repo.license else None,
            "forks": repo.forks_count,
            "watchers": repo.subscribers_count,
            "open_issues": repo.open_issues_count,
            "updated_at": repo.updated_at,
        }

    def get_file_content(
        self, owner_repo: str, path: str, ref: Optional[str] = None
    ) -> bytes:
        """Get file content from a repository.

        Args:
            owner_repo: Repository in "owner/repo" format
            path: Path to file within repository
            ref: Git ref (branch, tag, SHA). Defaults to default branch.

        Returns:
            File content as bytes

        Raises:
            GitHubNotFoundError: If file or repository not found
            GitHubRateLimitError: If rate limit exceeded
            GitHubClientError: For other errors (e.g., path is a directory)

        Example:
            >>> client = GitHubClient()
            >>> content = client.get_file_content("anthropics/skills", "README.md")
            >>> print(content.decode("utf-8"))
        """
        repo = self.get_repo(owner_repo)
        try:
            # PyGithub expects NotSet for default, not None
            content_file = repo.get_contents(
                path, ref=ref if ref is not None else NotSet
            )

            # Handle single file
            if isinstance(content_file, ContentFile):
                if content_file.type != "file":
                    raise GitHubClientError(
                        f"Path '{path}' is not a file (type: {content_file.type})"
                    )
                return content_file.decoded_content

            # Handle list (shouldn't happen for files, but be defensive)
            if isinstance(content_file, list):
                raise GitHubClientError(f"Path '{path}' is a directory, not a file")

            raise GitHubClientError(f"Unexpected content type for '{path}'")

        except GithubException as e:
            self._handle_exception(e, context=f"get_file_content({owner_repo}, {path})")
            raise

    def get_file_with_metadata(
        self, owner_repo: str, path: str, ref: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get file content with metadata from a repository.

        Unlike get_file_content() which returns only bytes, this method
        returns a dictionary with content, SHA, and other metadata.

        Args:
            owner_repo: Repository in "owner/repo" format
            path: Path to file within repository
            ref: Git ref (branch, tag, SHA). Defaults to default branch.

        Returns:
            Dictionary containing:
                - content: bytes - Raw file content
                - sha: str - Git blob SHA
                - size: int - File size in bytes
                - name: str - File name

        Raises:
            GitHubNotFoundError: If file or repository not found
            GitHubRateLimitError: If rate limit exceeded
            GitHubClientError: For other errors (e.g., path is a directory)
        """
        repo = self.get_repo(owner_repo)
        try:
            content_file = repo.get_contents(
                path, ref=ref if ref is not None else NotSet
            )

            if isinstance(content_file, ContentFile):
                if content_file.type == "symlink":
                    # Symlink detected - resolve target and fetch actual content
                    import posixpath

                    symlink_target = getattr(content_file, "target", None)
                    if symlink_target:
                        # Resolve relative path against parent directory
                        parent_dir = posixpath.dirname(path)
                        resolved_path = posixpath.normpath(
                            posixpath.join(parent_dir, symlink_target)
                        )
                        # Validate resolved path stays within repo
                        if not resolved_path.startswith(
                            ".."
                        ) and not resolved_path.startswith("/"):
                            # Recursive call to get content at the resolved path
                            return self.get_file_with_metadata(
                                owner_repo, resolved_path, ref=ref
                            )
                    raise GitHubClientError(
                        f"Cannot resolve symlink at '{path}' "
                        f"(target: {symlink_target})"
                    )

                if content_file.type != "file":
                    raise GitHubClientError(
                        f"Path '{path}' is not a file (type: {content_file.type})"
                    )
                return {
                    "content": content_file.decoded_content,
                    "sha": content_file.sha,
                    "size": content_file.size,
                    "name": content_file.name,
                }

            if isinstance(content_file, list):
                raise GitHubClientError(f"Path '{path}' is a directory, not a file")

            raise GitHubClientError(f"Unexpected content type for '{path}'")

        except GithubException as e:
            self._handle_exception(
                e, context=f"get_file_with_metadata({owner_repo}, {path})"
            )
            raise

    def get_repo_tree(
        self, owner_repo: str, ref: Optional[str] = None, recursive: bool = True
    ) -> List[Dict[str, Any]]:
        """Get repository tree (file listing).

        Args:
            owner_repo: Repository in "owner/repo" format
            ref: Git ref (branch, tag, SHA). Defaults to default branch.
            recursive: If True, include all nested files/directories

        Returns:
            List of dictionaries, each containing:
                - path: str - File/directory path
                - type: str - "blob" (file), "tree" (directory), or "symlink"
                - sha: str - Object SHA
                - size: int | None - File size (None for directories)

        Raises:
            GitHubNotFoundError: If repository not found
            GitHubRateLimitError: If rate limit exceeded
            GitHubClientError: For other errors

        Note:
            Symlinks are resolved to their target type. If a symlink points to
            a directory in the same tree, it returns type "tree". If it points
            to a file, it returns type "blob". If the target cannot be resolved
            (external symlink), it returns type "symlink".

        Example:
            >>> client = GitHubClient()
            >>> tree = client.get_repo_tree("anthropics/skills")
            >>> files = [t for t in tree if t["type"] == "blob"]
        """
        repo = self.get_repo(owner_repo)
        try:
            # Get ref or default branch
            tree_ref = ref or repo.default_branch
            git_tree = repo.get_git_tree(tree_ref, recursive=recursive)

            # First pass: build path -> type lookup for symlink resolution
            path_types: Dict[str, str] = {}
            symlinks: List[Tuple[Any, str]] = []  # (item, path) pairs for symlinks

            for item in git_tree.tree:
                mode = getattr(item, "mode", "")
                if item.type == "blob" and mode == "120000":
                    # This is a symlink - we'll resolve it in second pass
                    symlinks.append((item, item.path))
                else:
                    path_types[item.path] = item.type

            # Second pass: resolve symlinks to their target types
            symlink_resolved_types: Dict[str, str] = {}
            for item, symlink_path in symlinks:
                try:
                    # Get symlink target by fetching blob content
                    blob = repo.get_git_blob(item.sha)
                    if blob.encoding == "base64":
                        target = base64.b64decode(blob.content).decode("utf-8").strip()
                    else:
                        target = blob.content.strip()

                    # Resolve relative path from symlink location
                    symlink_dir = posixpath.dirname(symlink_path)
                    resolved_path = posixpath.normpath(
                        posixpath.join(symlink_dir, target)
                    )

                    # Look up resolved path in tree
                    if resolved_path in path_types:
                        symlink_resolved_types[symlink_path] = path_types[resolved_path]
                    else:
                        # Target not in tree (external symlink or broken)
                        symlink_resolved_types[symlink_path] = "symlink"
                except Exception as e:
                    # If we can't resolve, fall back to "symlink"
                    logger.debug(f"Failed to resolve symlink {symlink_path}: {e}")
                    symlink_resolved_types[symlink_path] = "symlink"

            # Build final result
            result = []
            for item in git_tree.tree:
                mode = getattr(item, "mode", "")
                if item.type == "blob" and mode == "120000":
                    # Use resolved type for symlinks
                    resolved_type = symlink_resolved_types.get(item.path, "symlink")
                    result.append(
                        {
                            "path": item.path,
                            "type": resolved_type,
                            "sha": item.sha,
                            "size": item.size if resolved_type == "blob" else None,
                        }
                    )
                else:
                    result.append(
                        {
                            "path": item.path,
                            "type": item.type,
                            "sha": item.sha,
                            "size": item.size if item.type == "blob" else None,
                        }
                    )

            return result
        except GithubException as e:
            self._handle_exception(e, context=f"get_repo_tree({owner_repo})")
            raise

    def resolve_version(self, owner_repo: str, version: str) -> str:
        """Resolve a version specifier to a commit SHA.

        Version formats supported:
            - "latest" - Latest commit on default branch
            - "v1.0.0" or "1.0.0" - Tag name
            - "abc1234..." - Commit SHA (validated)
            - "main", "develop" - Branch name

        Args:
            owner_repo: Repository in "owner/repo" format
            version: Version specifier to resolve

        Returns:
            Full commit SHA (40 characters)

        Raises:
            GitHubNotFoundError: If version/ref not found
            GitHubRateLimitError: If rate limit exceeded
            GitHubClientError: For other errors

        Example:
            >>> client = GitHubClient()
            >>> sha = client.resolve_version("anthropics/skills", "latest")
            >>> print(sha)  # e.g., "abc123def456..."
        """
        repo = self.get_repo(owner_repo)

        try:
            # Handle "latest" - get default branch HEAD
            if version.lower() == "latest":
                default_branch = repo.default_branch
                branch = repo.get_branch(default_branch)
                return branch.commit.sha

            # Check if it looks like a SHA (7-40 hex characters)
            if re.match(r"^[0-9a-fA-F]{7,40}$", version):
                # Validate SHA exists
                commit = repo.get_commit(version)
                return commit.sha

            # Try as a tag first
            try:
                # Try exact tag name
                ref = repo.get_git_ref(f"tags/{version}")
                # Tags can point to commits or tag objects
                if ref.object.type == "tag":
                    tag = repo.get_git_tag(ref.object.sha)
                    return tag.object.sha
                return ref.object.sha
            except GithubException:
                pass  # Not a tag, try as branch

            # Try as branch
            try:
                branch = repo.get_branch(version)
                return branch.commit.sha
            except GithubException:
                pass  # Not a branch

            # Nothing found
            raise GitHubNotFoundError(
                f"Version '{version}' not found in {owner_repo}. "
                "Expected a tag, branch, or commit SHA."
            )

        except GithubException as e:
            self._handle_exception(
                e, context=f"resolve_version({owner_repo}, {version})"
            )
            raise

    def validate_token(self) -> Dict[str, Any]:
        """Validate the current token and return auth info.

        Returns:
            Dictionary containing:
                - valid: bool - Whether token is valid
                - username: str | None - Authenticated username
                - scopes: list[str] - Token scopes
                - rate_limit: dict - Current rate limit info

        Note:
            Returns valid=True even for unauthenticated clients,
            as they can still make 60 requests/hour.

        Example:
            >>> client = GitHubClient(token="ghp_xxx")
            >>> info = client.validate_token()
            >>> print(f"User: {info['username']}, Scopes: {info['scopes']}")
        """
        client = self._get_client()
        rate_limit = self.get_rate_limit()

        if not self._token:
            return {
                "valid": True,  # Unauthenticated is "valid" (just limited)
                "username": None,
                "scopes": [],
                "rate_limit": rate_limit,
            }

        try:
            user = client.get_user()
            # Get scopes from rate limit response headers
            rate_limit_response = client.get_rate_limit()
            scopes = (
                getattr(rate_limit_response.raw_headers, "x-oauth-scopes", "") or ""
            )
            scope_list = [s.strip() for s in scopes.split(",") if s.strip()]

            return {
                "valid": True,
                "username": user.login,
                "scopes": scope_list,
                "rate_limit": rate_limit,
            }
        except BadCredentialsException:
            return {
                "valid": False,
                "username": None,
                "scopes": [],
                "rate_limit": rate_limit,
            }
        except GithubException as e:
            logger.warning(f"Token validation error: {e}")
            return {
                "valid": False,
                "username": None,
                "scopes": [],
                "rate_limit": rate_limit,
            }

    def get_rate_limit(self) -> Dict[str, Any]:
        """Get current rate limit information.

        Returns:
            Dictionary containing:
                - remaining: int - Requests remaining
                - limit: int - Total request limit
                - reset: datetime - When limit resets (UTC)

        Example:
            >>> client = GitHubClient()
            >>> limit = client.get_rate_limit()
            >>> print(f"Remaining: {limit['remaining']}/{limit['limit']}")
        """
        try:
            client = self._get_client()
            rate_limit_overview = client.get_rate_limit()
            # PyGithub uses .rate for the core rate limit
            rate = rate_limit_overview.rate

            return {
                "remaining": rate.remaining,
                "limit": rate.limit,
                "reset": (
                    rate.reset.replace(tzinfo=timezone.utc)
                    if rate.reset.tzinfo is None
                    else rate.reset
                ),
            }
        except GithubException:
            # Return defaults if we can't get rate limit
            return {
                "remaining": 0,
                "limit": 60 if not self._token else 5000,
                "reset": datetime.now(timezone.utc),
            }

    def is_authenticated(self) -> bool:
        """Check if the client is authenticated.

        Returns:
            True if a token is configured, False otherwise.

        Note:
            This only checks if a token is present, not if it's valid.
            Use validate_token() for full validation.
        """
        return self._token is not None


# =============================================================================
# Singleton Pattern
# =============================================================================

# Cache of clients by token
_client_cache: Dict[Optional[str], GitHubClient] = {}


def get_github_client(token: Optional[str] = None) -> GitHubClient:
    """Get a GitHub client instance (singleton per token).

    Returns a cached client instance for the given token, creating one
    if it doesn't exist. This allows reuse without recreating connections.

    Args:
        token: Optional explicit token. If None, uses token resolution
            priority (ConfigManager -> SKILLMEAT_GITHUB_TOKEN -> GITHUB_TOKEN).

    Returns:
        GitHubClient instance

    Example:
        >>> # Get default client (uses token resolution)
        >>> client = get_github_client()
        >>>
        >>> # Get client with specific token
        >>> client = get_github_client(token="ghp_xxx")
        >>>
        >>> # Same token returns same instance
        >>> client2 = get_github_client(token="ghp_xxx")
        >>> assert client2 is client
    """
    # For None token, we need to resolve it first to get the cache key
    if token is None:
        # Create a temp client to resolve the token
        temp_client = GitHubClient()
        resolved_token = temp_client.token
        cache_key = resolved_token
    else:
        cache_key = token

    if cache_key not in _client_cache:
        _client_cache[cache_key] = GitHubClient(token=token)

    return _client_cache[cache_key]


def clear_client_cache() -> None:
    """Clear the client cache.

    Useful for testing or when tokens change.
    """
    global _client_cache
    _client_cache = {}


# Alias for backward compatibility
GitHubClientWrapper = GitHubClient
