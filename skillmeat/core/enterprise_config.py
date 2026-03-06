"""Enterprise edition configuration for SkillMeat.

Reads edition and API connection settings from environment variables:
- SKILLMEAT_EDITION: "community" (default) or "enterprise"
- SKILLMEAT_API_URL: URL of the enterprise API server (e.g. http://localhost:8080)
- SKILLMEAT_PAT: Personal Access Token for enterprise API auth
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

__all__ = [
    "EnterpriseConfig",
    "get_enterprise_config",
    "is_enterprise_mode",
]

_VALID_EDITIONS = frozenset({"community", "enterprise"})

_ENTERPRISE_CONFIG_SINGLETON: Optional["EnterpriseConfig"] = None


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
