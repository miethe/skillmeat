"""Profile-aware path resolution utilities for project deployments.

This module centralizes profile-root path construction and validation so
deployment, storage, and API layers can avoid hardcoded ``.claude`` paths.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from skillmeat.core.enums import Platform

logger = logging.getLogger(__name__)

DEFAULT_PROFILE_ID = "claude_code"
DEFAULT_PROFILE_ROOT_DIR = ".claude"
DEFAULT_PROFILE_ROOTS = [
    ".claude",
    ".codex",
    ".gemini",
    ".cursor",
]

DEFAULT_PROJECT_CONFIG_FILENAMES_BY_PLATFORM = {
    Platform.CLAUDE_CODE: ["CLAUDE.md", "AGENTS.md", ".skillmeat-project.toml"],
    Platform.CODEX: ["CODEX.md", ".skillmeat-project.toml"],
    Platform.GEMINI: ["GEMINI.md", ".skillmeat-project.toml"],
    Platform.CURSOR: ["CURSOR.md", ".skillmeat-project.toml"],
    Platform.OTHER: [".skillmeat-project.toml"],
}

DEFAULT_ARTIFACT_PATH_MAP = {
    "skill": "skills",
    "command": "commands",
    "agent": "agents",
    "hook": "hooks",
    "mcp": "mcp",
}


@dataclass(frozen=True)
class DeploymentPathProfile:
    """Profile contract needed for path resolution."""

    profile_id: str = DEFAULT_PROFILE_ID
    platform: Platform = Platform.CLAUDE_CODE
    root_dir: str = DEFAULT_PROFILE_ROOT_DIR
    artifact_path_map: Mapping[str, str] = field(default_factory=dict)
    config_filenames: Sequence[str] = field(default_factory=tuple)
    context_prefixes: Sequence[str] = field(default_factory=tuple)


def default_profile() -> DeploymentPathProfile:
    """Return the backward-compatible default Claude Code profile."""
    return DeploymentPathProfile(
        profile_id=DEFAULT_PROFILE_ID,
        platform=Platform.CLAUDE_CODE,
        root_dir=DEFAULT_PROFILE_ROOT_DIR,
        artifact_path_map=DEFAULT_ARTIFACT_PATH_MAP.copy(),
        config_filenames=tuple(default_project_config_filenames(Platform.CLAUDE_CODE)),
        context_prefixes=(f"{DEFAULT_PROFILE_ROOT_DIR}/context/",),
    )


def default_project_config_filenames(platform: Optional[Platform]) -> list[str]:
    """Return default project config filenames for a platform."""
    if platform is None:
        platform = Platform.CLAUDE_CODE
    return list(
        DEFAULT_PROJECT_CONFIG_FILENAMES_BY_PLATFORM.get(
            platform, DEFAULT_PROJECT_CONFIG_FILENAMES_BY_PLATFORM[Platform.OTHER]
        )
    )


def normalize_profile(profile: Optional[Any]) -> DeploymentPathProfile:
    """Normalize any profile-like object to ``DeploymentPathProfile``."""
    if profile is None:
        return default_profile()

    if isinstance(profile, DeploymentPathProfile):
        return profile

    platform_value = getattr(profile, "platform", Platform.CLAUDE_CODE)
    if isinstance(platform_value, Platform):
        platform = platform_value
    else:
        platform = Platform(str(platform_value))

    artifact_path_map = getattr(profile, "artifact_path_map", None) or {}
    config_filenames = getattr(profile, "config_filenames", None) or ()
    context_prefixes = getattr(profile, "context_prefixes", None) or ()

    return DeploymentPathProfile(
        profile_id=getattr(profile, "profile_id", DEFAULT_PROFILE_ID),
        platform=platform,
        root_dir=getattr(profile, "root_dir", DEFAULT_PROFILE_ROOT_DIR),
        artifact_path_map=artifact_path_map,
        config_filenames=config_filenames,
        context_prefixes=context_prefixes,
    )


def resolve_profile_root(project_path: Path, profile: Optional[Any] = None) -> Path:
    """Resolve and validate a profile root directory within a project root."""
    profile_cfg = normalize_profile(profile)
    project_root = Path(project_path).resolve()

    root_dir = Path(profile_cfg.root_dir)
    if root_dir.is_absolute():
        raise ValueError(
            f"Profile root_dir '{profile_cfg.root_dir}' must be relative to project root"
        )

    raw_root = project_root / root_dir
    _warn_if_symlink(raw_root, project_root, profile_cfg.profile_id)
    resolved_root = raw_root.resolve(strict=False)
    _ensure_inside_project(project_root, resolved_root, "profile root")
    return resolved_root


def resolve_artifact_path(
    artifact_name: str,
    artifact_type: str,
    project_path: Path,
    profile: Optional[Any] = None,
) -> Path:
    """Resolve destination path for a deployed artifact in a profile root."""
    profile_cfg = normalize_profile(profile)
    root = resolve_profile_root(project_path, profile_cfg)

    artifact_type_str = str(artifact_type)
    container = (
        profile_cfg.artifact_path_map.get(artifact_type_str)
        or DEFAULT_ARTIFACT_PATH_MAP.get(artifact_type_str)
    )
    if not container:
        raise ValueError(f"Unknown artifact type: {artifact_type_str}")

    if artifact_type_str in {"skill", "mcp"}:
        relative_path = Path(container) / artifact_name
    else:
        relative_path = Path(container) / f"{artifact_name}.md"

    return _resolve_within_root(root, relative_path, "artifact path")


def resolve_deployment_path(
    deployment_relative_path: Path | str,
    project_path: Path,
    profile: Optional[Any] = None,
) -> Path:
    """Resolve a deployment record's relative artifact path in a profile root."""
    root = resolve_profile_root(project_path, profile)
    return _resolve_within_root(root, Path(deployment_relative_path), "deployment path")


def resolve_config_path(
    project_path: Path,
    profile: Optional[Any] = None,
    filename: str = ".skillmeat-project.toml",
) -> Path:
    """Resolve a profile-scoped config file path."""
    root = resolve_profile_root(project_path, profile)
    return _resolve_within_root(root, Path(filename), "config path")


def resolve_context_path(
    context_relative_path: Path | str,
    project_path: Path,
    profile: Optional[Any] = None,
) -> Path:
    """Resolve a context entity path and validate profile-specific prefixes."""
    profile_cfg = normalize_profile(profile)
    context_path = Path(context_relative_path)

    if context_path.is_absolute():
        raise ValueError("Context path must be relative")

    context_path_str = context_path.as_posix()
    prefixes = [p for p in profile_cfg.context_prefixes if p]
    if prefixes and not any(context_path_str.startswith(p) for p in prefixes):
        raise ValueError(
            f"Context path '{context_path_str}' is outside allowed profile prefixes"
        )

    root = resolve_profile_root(project_path, profile_cfg)
    normalized_context_path = context_path

    root_prefix = Path(profile_cfg.root_dir).as_posix().rstrip("/") + "/"
    if context_path_str.startswith(root_prefix):
        normalized_context_path = Path(context_path_str[len(root_prefix) :])

    return _resolve_within_root(root, normalized_context_path, "context path")


def _resolve_within_root(root: Path, relative_path: Path, label: str) -> Path:
    if relative_path.is_absolute():
        raise ValueError(f"{label.capitalize()} must be relative")

    resolved_path = (root / relative_path).resolve(strict=False)
    _ensure_inside_project(root, resolved_path, label)
    return resolved_path


def _ensure_inside_project(base: Path, candidate: Path, label: str) -> None:
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise ValueError(f"{label.capitalize()} escapes allowed root: {candidate}") from exc


def _warn_if_symlink(candidate: Path, project_root: Path, profile_id: str) -> None:
    """Log warning if any existing segment from project root is a symlink."""
    try:
        relative = candidate.relative_to(project_root)
    except ValueError:
        return

    cursor = project_root
    for segment in relative.parts:
        cursor = cursor / segment
        if cursor.exists() and cursor.is_symlink():
            logger.warning(
                "Profile root resolves through symlink",
                extra={
                    "profile_id": profile_id,
                    "project_root": str(project_root),
                    "symlink_segment": str(cursor),
                    "resolved_target": str(candidate),
                },
            )
            return
