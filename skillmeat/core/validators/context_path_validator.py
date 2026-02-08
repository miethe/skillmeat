"""Profile-aware context path validation utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from skillmeat.core.enums import Platform
from skillmeat.core.path_resolver import (
    DEFAULT_PROFILE_ROOTS,
    DeploymentPathProfile,
    normalize_profile,
)


@dataclass(frozen=True)
class ValidatedPath:
    """Result of context path validation."""

    normalized_path: str
    resolved_path: Optional[Path]
    allowed_prefixes: List[str]
    matched_prefix: Optional[str] = None
    matched_config_filename: Optional[str] = None
    profile_id: Optional[str] = None


def validate_context_path(
    path: str,
    project: Optional[Path | str] = None,
    profile_id: Optional[str] = None,
    *,
    profile: Optional[object] = None,
    allowed_prefixes: Optional[Sequence[str]] = None,
    config_filenames: Optional[Sequence[str]] = None,
) -> ValidatedPath:
    """Validate a context path against security and profile-aware constraints."""
    normalized_path = Path(path).as_posix().strip()
    if not normalized_path:
        raise ValueError("Context path cannot be empty")

    # Absolute path checks (POSIX + Windows drive).
    if normalized_path.startswith("/"):
        raise ValueError("Absolute path detected - must be relative")
    if len(normalized_path) > 1 and normalized_path[1] == ":":
        raise ValueError("Absolute path detected - must be relative")

    path_parts = [part for part in normalized_path.split("/") if part]
    if ".." in path_parts:
        raise ValueError("Context path cannot contain '..' (path traversal)")

    profile_obj = profile
    if profile_obj is None and project is not None:
        profile_obj = resolve_project_profile(project, profile_id)
    profile_cfg = normalize_profile(profile_obj) if profile_obj is not None else None

    effective_prefixes = _normalize_prefixes(
        allowed_prefixes
        if allowed_prefixes is not None
        else (profile_cfg.context_prefixes if profile_cfg is not None else None)
    )
    if not effective_prefixes:
        effective_prefixes = [f"{root.rstrip('/')}/" for root in DEFAULT_PROFILE_ROOTS]

    effective_config_filenames = _normalize_filenames(
        config_filenames
        if config_filenames is not None
        else (
            profile_cfg.config_filenames
            if profile_cfg is not None
            else default_config_filenames_for_platform(None)
        )
    )

    matched_prefix = next(
        (prefix for prefix in effective_prefixes if normalized_path.startswith(prefix)),
        None,
    )
    matched_config_filename: Optional[str] = None
    if matched_prefix is None:
        filename = Path(normalized_path).name
        if "/" not in normalized_path and filename in effective_config_filenames:
            matched_config_filename = filename
        else:
            prefixes_str = ", ".join(effective_prefixes)
            raise ValueError(
                f"Context path '{normalized_path}' must start with one of: {prefixes_str}"
            )

    resolved_path: Optional[Path] = None
    if project is not None:
        project_root = Path(project).expanduser().resolve()
        resolved_path = (project_root / normalized_path).resolve(strict=False)
        try:
            resolved_path.relative_to(project_root)
        except ValueError as exc:
            raise ValueError(
                f"Context path escapes project root: {resolved_path}"
            ) from exc

    return ValidatedPath(
        normalized_path=normalized_path,
        resolved_path=resolved_path,
        allowed_prefixes=effective_prefixes,
        matched_prefix=matched_prefix,
        matched_config_filename=matched_config_filename,
        profile_id=getattr(profile_cfg, "profile_id", profile_id),
    )


def normalize_context_prefixes(profile: object) -> List[str]:
    """Return normalized context prefixes with root-dir fallback."""
    profile_cfg = normalize_profile(profile)
    prefixes = _normalize_prefixes(profile_cfg.context_prefixes)
    root_prefix = f"{profile_cfg.root_dir.rstrip('/')}/"
    if root_prefix not in prefixes:
        prefixes.append(root_prefix)
    return prefixes


def rewrite_path_for_profile(path: str, profile: object) -> str:
    """Rewrite a profile-rooted path to the selected profile's root dir."""
    profile_cfg = normalize_profile(profile)
    normalized_path = Path(path).as_posix().strip()
    if "/" not in normalized_path:
        return normalized_path

    target_root = f"{profile_cfg.root_dir.rstrip('/')}/"
    if normalized_path.startswith(target_root):
        return normalized_path

    for root in DEFAULT_PROFILE_ROOTS:
        root_prefix = f"{root.rstrip('/')}/"
        if normalized_path.startswith(root_prefix):
            return target_root + normalized_path[len(root_prefix) :]

    return normalized_path


def resolve_project_profile(
    project: Path | str,
    profile_id: Optional[str] = None,
) -> DeploymentPathProfile:
    """Resolve a project's deployment profile with safe fallback."""
    from skillmeat.cache.models import Project, get_session
    from skillmeat.cache.repositories import DeploymentProfileRepository
    from skillmeat.core.path_resolver import default_profile

    project_root = Path(project).expanduser().resolve()
    fallback = default_profile()

    session = None
    try:
        session = get_session()
        project_row = (
            session.query(Project).filter(Project.path == str(project_root)).first()
        )
        if not project_row:
            if profile_id:
                return _fallback_profile(profile_id)
            return fallback

        repo = DeploymentProfileRepository()
        if profile_id:
            profile = repo.read_by_project_and_profile_id(project_row.id, profile_id)
            if profile:
                return normalize_profile(profile)
            return _fallback_profile(profile_id)

        primary = repo.get_primary_profile(project_row.id)
        if primary:
            return normalize_profile(primary)
        return fallback
    except Exception:
        if profile_id:
            return _fallback_profile(profile_id)
        return fallback
    finally:
        if session is not None:
            session.close()


def default_config_filenames_for_platform(platform: Optional[Platform]) -> List[str]:
    """Return default project config filename set for a platform."""
    base = [".skillmeat-project.toml"]
    if platform == Platform.CODEX:
        return ["CODEX.md", *base]
    if platform == Platform.GEMINI:
        return ["GEMINI.md", *base]
    if platform == Platform.CURSOR:
        return ["CURSOR.md", *base]
    return ["CLAUDE.md", "AGENTS.md", *base]


def _fallback_profile(profile_id: str) -> DeploymentPathProfile:
    profile_key = (profile_id or "claude_code").strip() or "claude_code"
    mapping = {
        "claude_code": (Platform.CLAUDE_CODE, ".claude"),
        "codex": (Platform.CODEX, ".codex"),
        "gemini": (Platform.GEMINI, ".gemini"),
        "cursor": (Platform.CURSOR, ".cursor"),
    }
    platform, root_dir = mapping.get(profile_key, (Platform.OTHER, f".{profile_key}"))
    return DeploymentPathProfile(
        profile_id=profile_key,
        platform=platform,
        root_dir=root_dir,
        config_filenames=default_config_filenames_for_platform(platform),
        context_prefixes=[f"{root_dir}/context/"],
    )


def _normalize_prefixes(prefixes: Optional[Iterable[str]]) -> List[str]:
    if not prefixes:
        return []
    normalized: List[str] = []
    for raw_prefix in prefixes:
        prefix = Path(raw_prefix).as_posix().strip()
        if not prefix:
            continue
        if not prefix.endswith("/"):
            prefix = f"{prefix}/"
        if prefix not in normalized:
            normalized.append(prefix)
    return normalized


def _normalize_filenames(filenames: Optional[Iterable[str]]) -> List[str]:
    if not filenames:
        return []
    normalized: List[str] = []
    for name in filenames:
        if not name:
            continue
        filename = Path(name).name.strip()
        if filename and filename not in normalized:
            normalized.append(filename)
    return normalized
