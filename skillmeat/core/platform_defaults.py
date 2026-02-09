"""Platform-specific default configuration values.

This module provides platform defaults for directory structures, artifact types,
and configuration filenames across different AI coding platforms (Claude Code,
Codex, Gemini, Cursor, etc.).

The defaults can be overridden via:
1. TOML configuration at `platform.defaults.{platform}` key in config.toml
2. Environment variable SKILLMEAT_PLATFORM_DEFAULTS_JSON (JSON format)

Example:
    >>> from skillmeat.core.platform_defaults import resolve_platform_defaults
    >>> defaults = resolve_platform_defaults("claude_code")
    >>> defaults["root_dir"]
    '.claude'
    >>> defaults["artifact_path_map"]["skill"]
    'skills'
"""

from __future__ import annotations

import copy
import json
import os
from typing import Any

__all__ = ["PLATFORM_DEFAULTS", "resolve_platform_defaults", "resolve_all_platform_defaults"]


# =============================================================================
# Hardcoded Platform Defaults
# =============================================================================

PLATFORM_DEFAULTS = {
    "claude_code": {
        "root_dir": ".claude",
        "artifact_path_map": {
            "skill": "skills",
            "command": "commands",
            "agent": "agents",
            "hook": "hooks",
            "mcp": "mcp",
        },
        "config_filenames": ["CLAUDE.md"],
        "supported_artifact_types": ["skill", "command", "agent", "hook", "mcp"],
        "context_prefixes": [".claude/context/", ".claude/"],
    },
    "codex": {
        "root_dir": ".codex",
        "artifact_path_map": {
            "skill": "skills",
            "command": "commands",
            "agent": "agents",
        },
        "config_filenames": ["AGENTS.md"],
        "supported_artifact_types": ["skill", "command", "agent"],
        "context_prefixes": [".codex/context/", ".codex/"],
    },
    "gemini": {
        "root_dir": ".gemini",
        "artifact_path_map": {
            "skill": "skills",
            "command": "commands",
        },
        "config_filenames": ["GEMINI.md"],
        "supported_artifact_types": ["skill", "command"],
        "context_prefixes": [".gemini/context/", ".gemini/"],
    },
    "cursor": {
        "root_dir": ".cursor",
        "artifact_path_map": {
            "skill": "skills",
            "command": "commands",
            "agent": "agents",
        },
        "config_filenames": [".cursorrules"],
        "supported_artifact_types": ["skill", "command", "agent"],
        "context_prefixes": [".cursor/context/", ".cursor/"],
    },
    "other": {
        "root_dir": ".custom",
        "artifact_path_map": {},
        "config_filenames": [],
        "supported_artifact_types": ["skill"],
        "context_prefixes": [],
    },
}


# =============================================================================
# Deep Merge Utility
# =============================================================================


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries.

    Merging rules:
    - Dict values: recursively deep merge
    - List values: replace (don't append)
    - Scalar values: replace

    Args:
        base: Base dictionary (will be modified in place)
        override: Override dictionary

    Returns:
        Merged dictionary (same object as base)
    """
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            # Recursively merge nested dicts
            _deep_merge(base[key], value)
        else:
            # Replace for lists and scalars
            base[key] = value
    return base


# =============================================================================
# Platform Defaults Resolution
# =============================================================================


def resolve_platform_defaults(platform: str) -> dict[str, Any]:
    """Resolve platform defaults with layered overrides.

    Resolution order (later layers override earlier):
    1. Hardcoded defaults from PLATFORM_DEFAULTS
    2. TOML overrides from ConfigManager at `platform.defaults.{platform}`
    3. Environment variable SKILLMEAT_PLATFORM_DEFAULTS_JSON

    Args:
        platform: Platform name (e.g., "claude_code", "codex")

    Returns:
        Resolved platform defaults dictionary

    Raises:
        ValueError: If platform is not recognized

    Example:
        >>> defaults = resolve_platform_defaults("claude_code")
        >>> defaults["root_dir"]
        '.claude'
    """
    if platform not in PLATFORM_DEFAULTS:
        raise ValueError(
            f"Unknown platform '{platform}'. "
            f"Supported platforms: {', '.join(PLATFORM_DEFAULTS.keys())}"
        )

    # Start with deep copy of hardcoded defaults
    result = copy.deepcopy(PLATFORM_DEFAULTS[platform])

    # Layer 2: TOML overrides from ConfigManager
    try:
        from skillmeat.config import ConfigManager

        cm = ConfigManager()
        toml_overrides = cm.get(f"platform.defaults.{platform}")
        if toml_overrides and isinstance(toml_overrides, dict):
            _deep_merge(result, toml_overrides)
    except Exception:
        # Silently ignore if ConfigManager fails (avoid breaking callers)
        pass

    # Layer 3: Environment variable overrides
    env_json = os.environ.get("SKILLMEAT_PLATFORM_DEFAULTS_JSON")
    if env_json:
        try:
            env_overrides = json.loads(env_json)
            if isinstance(env_overrides, dict) and platform in env_overrides:
                platform_env = env_overrides[platform]
                if isinstance(platform_env, dict):
                    _deep_merge(result, platform_env)
        except (json.JSONDecodeError, TypeError):
            # Silently ignore malformed JSON
            pass

    return result


def resolve_all_platform_defaults() -> dict[str, dict[str, Any]]:
    """Resolve defaults for all platforms.

    Returns:
        Dictionary mapping platform names to their resolved defaults

    Example:
        >>> all_defaults = resolve_all_platform_defaults()
        >>> all_defaults["claude_code"]["root_dir"]
        '.claude'
        >>> all_defaults["gemini"]["root_dir"]
        '.gemini'
    """
    return {platform: resolve_platform_defaults(platform) for platform in PLATFORM_DEFAULTS.keys()}
