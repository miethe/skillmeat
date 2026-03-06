"""Enterprise edition configuration for SkillMeat.

Reads edition and API connection settings from environment variables:
- SKILLMEAT_EDITION: "community" (default) or "enterprise"
- SKILLMEAT_API_URL: URL of the enterprise API server (e.g. http://localhost:8080)
- SKILLMEAT_PAT: Personal Access Token for enterprise API auth

PAT resolution priority (highest to lowest):
1. In-memory override set via ``set_session_pat()`` (CLI --token flag)
2. ``SKILLMEAT_PAT`` environment variable
3. ``[auth] pat`` key in ``~/.skillmeat/enterprise.toml``
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

__all__ = [
    "EnterpriseConfig",
    "EnterpriseConfigError",
    "get_enterprise_config",
    "is_enterprise_mode",
    "get_pat",
    "store_pat",
    "clear_pat",
    "set_session_pat",
]

_VALID_EDITIONS = frozenset({"community", "enterprise"})

_ENTERPRISE_CONFIG_SINGLETON: Optional["EnterpriseConfig"] = None

# In-memory PAT override — set by the CLI --token flag for the current session.
# Takes priority over env var and config file when not None.
_SESSION_PAT: Optional[str] = None

# Path to the enterprise config file.
_ENTERPRISE_TOML_PATH: Path = Path.home() / ".skillmeat" / "enterprise.toml"


class EnterpriseConfigError(Exception):
    """Raised when an enterprise operation cannot proceed due to missing config.

    Typical cause: a PAT is required but was not found in any source
    (CLI flag, environment variable, or config file).
    """


@dataclass(frozen=True)
class EnterpriseConfig:
    """Resolved enterprise edition configuration.

    Attributes:
        edition: Active edition — "community" or "enterprise".
        api_url: URL of the enterprise API server. May be None in community mode.
        pat: Personal Access Token for enterprise API authentication. May be None.
    """

    edition: str
    api_url: Optional[str]
    pat: Optional[str]

    def is_enterprise(self) -> bool:
        """Return True when running in enterprise mode."""
        return self.edition == "enterprise"


def _read_edition() -> str:
    """Read and validate SKILLMEAT_EDITION env var.

    Returns:
        Validated edition string, defaulting to "community".
    """
    raw = os.environ.get("SKILLMEAT_EDITION", "community").strip().lower()
    if raw not in _VALID_EDITIONS:
        # Fall back to community rather than crashing on a bad value.
        return "community"
    return raw


def get_enterprise_config() -> EnterpriseConfig:
    """Return the singleton EnterpriseConfig, constructing it on first call.

    Reads from environment variables:
        SKILLMEAT_EDITION  — "community" | "enterprise" (default: "community")
        SKILLMEAT_API_URL  — URL of the enterprise API server
        SKILLMEAT_PAT      — Personal Access Token for API auth

    Returns:
        EnterpriseConfig instance (frozen dataclass).
    """
    global _ENTERPRISE_CONFIG_SINGLETON
    if _ENTERPRISE_CONFIG_SINGLETON is None:
        _ENTERPRISE_CONFIG_SINGLETON = EnterpriseConfig(
            edition=_read_edition(),
            api_url=os.environ.get("SKILLMEAT_API_URL") or None,
            pat=os.environ.get("SKILLMEAT_PAT") or None,
        )
    return _ENTERPRISE_CONFIG_SINGLETON


def is_enterprise_mode() -> bool:
    """Return True when SKILLMEAT_EDITION is set to "enterprise".

    Convenience wrapper around get_enterprise_config().is_enterprise().
    """
    return get_enterprise_config().is_enterprise()


# =============================================================================
# PAT management
# =============================================================================


def set_session_pat(token: str) -> None:
    """Set an in-memory PAT for the current process lifetime.

    This is called by the CLI ``--token`` flag.  The value is never persisted
    to disk — use :func:`store_pat` for that.

    Args:
        token: Personal Access Token string.
    """
    global _SESSION_PAT
    _SESSION_PAT = token


def _read_toml_pat() -> Optional[str]:
    """Read the PAT from ``~/.skillmeat/enterprise.toml`` if present.

    Returns:
        PAT string, or None if the file does not exist or contains no PAT.
    """
    if not _ENTERPRISE_TOML_PATH.exists():
        return None
    try:
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            try:
                import tomllib  # type: ignore[no-redef]
            except ImportError:
                import tomli as tomllib  # type: ignore[no-redef]

        with open(_ENTERPRISE_TOML_PATH, "rb") as fh:
            data = tomllib.load(fh)
        auth = data.get("auth", {})
        pat = auth.get("pat")
        return pat if isinstance(pat, str) and pat else None
    except Exception:
        # Silently ignore parse errors — treat as no PAT.
        return None


def get_pat() -> Optional[str]:
    """Return the active PAT using the priority chain.

    Priority (highest wins):
    1. In-memory session override (set via ``--token`` CLI flag /
       :func:`set_session_pat`)
    2. ``SKILLMEAT_PAT`` environment variable
    3. ``[auth] pat`` in ``~/.skillmeat/enterprise.toml``

    Returns:
        PAT string, or None if no PAT is configured from any source.
    """
    if _SESSION_PAT:
        return _SESSION_PAT
    env_pat = os.environ.get("SKILLMEAT_PAT")
    if env_pat:
        return env_pat
    return _read_toml_pat()


def store_pat(token: str) -> None:
    """Persist a PAT to ``~/.skillmeat/enterprise.toml``.

    Reads the existing file (if any) to preserve other keys, then rewrites it
    with the ``[auth]`` section updated.  Uses manual TOML serialisation because
    ``tomllib`` is read-only.

    Args:
        token: Personal Access Token string to persist.

    Raises:
        OSError: If the config directory cannot be created or the file cannot
            be written.
    """
    config_dir = _ENTERPRISE_TOML_PATH.parent
    config_dir.mkdir(parents=True, exist_ok=True)

    # Read existing content to preserve non-auth sections.
    existing_lines: list[str] = []
    if _ENTERPRISE_TOML_PATH.exists():
        try:
            existing_lines = _ENTERPRISE_TOML_PATH.read_text(encoding="utf-8").splitlines()
        except OSError:
            existing_lines = []

    # Strip out any existing [auth] block (section + its keys until next section).
    cleaned: list[str] = []
    inside_auth = False
    for line in existing_lines:
        stripped = line.strip()
        if stripped == "[auth]":
            inside_auth = True
            continue
        if inside_auth:
            if stripped.startswith("[") and not stripped.startswith("[auth]"):
                # New section — stop skipping.
                inside_auth = False
                cleaned.append(line)
            # else: skip auth section keys
            continue
        cleaned.append(line)

    # Remove trailing blank lines for a clean append.
    while cleaned and not cleaned[-1].strip():
        cleaned.pop()

    # Escape any double-quotes in the token for safe TOML inline string.
    escaped = token.replace("\\", "\\\\").replace('"', '\\"')

    new_block = ["", "[auth]", f'pat = "{escaped}"', ""]
    output = "\n".join(cleaned + new_block)

    _ENTERPRISE_TOML_PATH.write_text(output, encoding="utf-8")


def clear_pat() -> None:
    """Remove the stored PAT from ``~/.skillmeat/enterprise.toml``.

    If the file does not exist or contains no PAT, this is a no-op.
    Does **not** clear the in-memory session PAT or the environment variable.
    """
    if not _ENTERPRISE_TOML_PATH.exists():
        return

    existing_lines = _ENTERPRISE_TOML_PATH.read_text(encoding="utf-8").splitlines()

    cleaned: list[str] = []
    inside_auth = False
    for line in existing_lines:
        stripped = line.strip()
        if stripped == "[auth]":
            inside_auth = True
            continue
        if inside_auth:
            if stripped.startswith("[") and not stripped.startswith("[auth]"):
                inside_auth = False
                cleaned.append(line)
            continue
        cleaned.append(line)

    # Remove trailing blank lines.
    while cleaned and not cleaned[-1].strip():
        cleaned.pop()

    _ENTERPRISE_TOML_PATH.write_text("\n".join(cleaned) + "\n", encoding="utf-8")
