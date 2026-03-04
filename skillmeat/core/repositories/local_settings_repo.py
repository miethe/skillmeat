"""Local TOML-backed implementation of the ISettingsRepository interface.

Settings are stored in ``~/.skillmeat/config.toml`` and managed by
:class:`~skillmeat.config.ConfigManager`.  This repository provides the
hexagonal-architecture-compatible interface over that existing mechanism,
converting between the flat TOML config structure and the
:class:`~skillmeat.core.interfaces.dtos.SettingsDTO` contract.

The ``validate_github_token`` method performs a lightweight call to the
GitHub API (via the :class:`~skillmeat.core.github_client.GitHubClient`
wrapper) to verify that the supplied token is valid.  On import failure or
network error it degrades gracefully and returns ``False``.

Design notes:
- Constructor takes a ``ProjectPathResolver`` for forward-compatibility (e.g.
  future collection-path resolution); at present only ``ConfigManager`` is
  used.
- No I/O at construction time: the config file is read lazily on first
  method call.
- Python 3.9+ compatible (no ``X | Y`` union syntax in runtime code).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from skillmeat.config import ConfigManager
from skillmeat.core.interfaces.context import RequestContext
from skillmeat.core.interfaces.dtos import SettingsDTO
from skillmeat.core.interfaces.repositories import ISettingsRepository
from skillmeat.core.path_resolver import ProjectPathResolver

logger = logging.getLogger(__name__)

__all__ = ["LocalSettingsRepository"]

# TOML config key that stores the GitHub Personal Access Token.
_GITHUB_TOKEN_KEY = "settings.github-token"

# TOML key for the user's chosen default scope.
_DEFAULT_SCOPE_KEY = "settings.default-scope"

# TOML key for the active collection path (when overridden from default).
_COLLECTION_PATH_KEY = "settings.collection-path"

# TOML key for the edition identifier (community / pro / etc.).
_EDITION_KEY = "settings.edition"

# TOML key for the artifact search indexing mode.
_INDEXING_MODE_KEY = "artifact_search.indexing_mode"


def _read_settings_dto(config: ConfigManager, resolver: ProjectPathResolver) -> SettingsDTO:
    """Build a :class:`SettingsDTO` from the current TOML configuration.

    All TOML entries that do not map to known DTO fields are collected into
    ``extra`` so no information is silently discarded.

    Args:
        config: Initialised :class:`~skillmeat.config.ConfigManager`.
        resolver: :class:`~skillmeat.core.path_resolver.ProjectPathResolver`
            used to determine the default collection path.

    Returns:
        Fully populated :class:`SettingsDTO`.
    """
    github_token: Optional[str] = config.get(_GITHUB_TOKEN_KEY)

    # Mask the token in the DTO — only expose whether it is set.
    # Callers that need the raw token must read it from ConfigManager directly.
    masked_token: Optional[str] = None
    if github_token:
        visible = github_token[:4] if len(github_token) > 4 else github_token
        masked_token = visible + "*" * (len(github_token) - len(visible))

    raw_collection_path: Optional[str] = config.get(_COLLECTION_PATH_KEY)
    if not raw_collection_path:
        raw_collection_path = str(resolver.collection_root())

    default_scope: str = config.get(_DEFAULT_SCOPE_KEY, "user") or "user"
    edition: str = config.get(_EDITION_KEY, "community") or "community"
    indexing_mode: str = config.get_indexing_mode()

    # Collect the full TOML tree, flatten top-level, gather unknowns.
    full_config: Dict[str, Any] = {}
    try:
        full_config = config.read()
    except Exception:
        pass

    known_sections = {"settings", "artifact_search", "analytics", "scoring", "similarity", "platform"}
    extra: Dict[str, Any] = {
        section: values
        for section, values in full_config.items()
        if section not in known_sections
    }

    return SettingsDTO(
        github_token=masked_token,
        collection_path=raw_collection_path,
        default_scope=default_scope,
        edition=edition,
        indexing_mode=indexing_mode,
        extra=extra,
    )


class LocalSettingsRepository(ISettingsRepository):
    """``ISettingsRepository`` backed by ``~/.skillmeat/config.toml``.

    Wraps :class:`~skillmeat.config.ConfigManager` to expose settings through
    the hexagonal-architecture interface contract.

    Args:
        path_resolver: :class:`~skillmeat.core.path_resolver.ProjectPathResolver`
            used for default collection-path resolution.
        config_manager: Optional pre-configured
            :class:`~skillmeat.config.ConfigManager`.  When ``None``, a
            default instance pointing at ``~/.skillmeat/`` is created.
    """

    def __init__(
        self,
        path_resolver: ProjectPathResolver,
        config_manager: Optional[ConfigManager] = None,
    ) -> None:
        self._resolver = path_resolver
        self._config = config_manager or ConfigManager()

    # ------------------------------------------------------------------
    # ISettingsRepository
    # ------------------------------------------------------------------

    def get(
        self,
        ctx: Optional[RequestContext] = None,
    ) -> SettingsDTO:
        """Return the current application settings snapshot.

        Reads ``~/.skillmeat/config.toml`` on every call to ensure freshness.
        The GitHub token is masked before being included in the DTO.

        Args:
            ctx: Optional per-request metadata.

        Returns:
            A :class:`~skillmeat.core.interfaces.dtos.SettingsDTO` populated
            with the current configuration values.
        """
        return _read_settings_dto(self._config, self._resolver)

    def update(
        self,
        updates: Dict[str, Any],
        ctx: Optional[RequestContext] = None,
    ) -> SettingsDTO:
        """Apply a partial update to the application settings.

        Recognised keys and their TOML mappings:

        =====================  ============================
        DTO key                TOML path
        =====================  ============================
        ``github_token``       ``settings.github-token``
        ``collection_path``    ``settings.collection-path``
        ``default_scope``      ``settings.default-scope``
        ``edition``            ``settings.edition``
        ``indexing_mode``      ``artifact_search.indexing_mode``
        =====================  ============================

        Unknown keys from *updates* are stored under ``settings.<key>`` for
        forward-compatibility.

        Args:
            updates: Map of setting keys to new values.
            ctx: Optional per-request metadata.

        Returns:
            The updated :class:`~skillmeat.core.interfaces.dtos.SettingsDTO`.
        """
        _known_key_map: Dict[str, str] = {
            "github_token": _GITHUB_TOKEN_KEY,
            "collection_path": _COLLECTION_PATH_KEY,
            "default_scope": _DEFAULT_SCOPE_KEY,
            "edition": _EDITION_KEY,
        }

        for dto_key, value in updates.items():
            if dto_key == "indexing_mode":
                self._config.set_indexing_mode(str(value))
            elif dto_key in _known_key_map:
                self._config.set(_known_key_map[dto_key], value)
            else:
                # Store unknown keys under the settings section.
                self._config.set(f"settings.{dto_key}", value)

        return _read_settings_dto(self._config, self._resolver)

    def validate_github_token(
        self,
        token: str,
        ctx: Optional[RequestContext] = None,
    ) -> bool:
        """Validate a GitHub Personal Access Token against the GitHub API.

        Performs a lightweight ``GET /rate_limit`` call (or equivalent)
        through the :class:`~skillmeat.core.github_client.GitHubClient`
        wrapper.  Returns ``False`` on any error (network failure, import
        error, invalid token) so the caller can degrade gracefully.

        Args:
            token: Raw GitHub PAT string.
            ctx: Optional per-request metadata.

        Returns:
            ``True`` if the token is valid and authenticated, ``False``
            otherwise.
        """
        if not token or not token.strip():
            return False

        try:
            from skillmeat.core.github_client import GitHubClient, GitHubAuthError

            client = GitHubClient(token=token)
            rate_limit = client.get_rate_limit()
            # A successful rate-limit call confirms the token is valid.
            # Authenticated tokens have a higher rate limit than unauthenticated.
            limit = (
                rate_limit.get("rate", {}).get("limit")
                if isinstance(rate_limit, dict)
                else None
            )
            if limit is not None and int(limit) > 60:
                return True
            # Even if we cannot read the limit, a non-exception response means
            # the token was accepted.
            return rate_limit is not None
        except Exception as exc:
            exc_str = str(exc).lower()
            if "auth" in exc_str or "401" in exc_str or "403" in exc_str:
                logger.debug("validate_github_token: token rejected by GitHub: %s", exc)
            else:
                logger.debug("validate_github_token: unexpected error: %s", exc)
            return False
