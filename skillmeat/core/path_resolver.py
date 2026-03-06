"""Path resolution utilities for SkillMeat deployments and collections.

Two complementary utilities live here:

``ProjectPathResolver``
    Centralises all path construction for the user's personal collection
    (``~/.skillmeat/collection/``) and global/local deployment targets.
    Use this wherever code currently hard-codes collection or deploy paths.

Profile-aware helpers (``resolve_profile_root``, ``resolve_artifact_path``, …)
    Lower-level utilities for resolving paths *within* a project's profile
    root (e.g. ``.claude/skills/…``).  These back the deployment layer and
    remain available for callers that need fine-grained profile control.
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


# ---------------------------------------------------------------------------
# Collection-level path resolver
# ---------------------------------------------------------------------------

#: Subdirectory under ``~/.skillmeat`` that holds the active collection.
_DEFAULT_COLLECTION_SUBDIR = "collection"

#: Subdirectory inside a collection root that holds all artifacts.
_ARTIFACTS_SUBDIR = "artifacts"

#: Filename of the collection manifest.
_MANIFEST_FILENAME = "manifest.toml"

#: Filename of the collection lock-file.
_LOCKFILE_FILENAME = "lockfile.toml"

#: Subdirectory inside ``~/.skillmeat`` that holds snapshots.
_SNAPSHOTS_SUBDIR = "snapshots"

#: Path segments for the global (user-scope) Claude Code skill directory.
_USER_DEPLOY_SEGMENTS = (".claude", "skills", "user")

#: Path segments for the local (project-scope) Claude Code skill directory.
_LOCAL_DEPLOY_SEGMENTS = (".claude", "skills")


class ProjectPathResolver:
    """Centralised path resolution for the SkillMeat collection and deploy targets.

    All paths that were previously hard-coded as ``Path.home() / ".skillmeat"``
    or ``Path.home() / ".claude" / "skills" / "user"`` across the codebase should
    be obtained through this class instead.

    Design notes
    ------------
    * ``collection_root`` is the only configurable parameter.  Everything else
      is derived deterministically from it so that tests can redirect all I/O to
      a temporary directory by passing a single value.
    * The class is deliberately *not* a singleton — it is intended to be
      constructed once and injected wherever path resolution is needed.
    * No I/O is performed in any method; all paths are returned as
      ``pathlib.Path`` objects and creation is left to the caller.
    * Python 3.9+ compatible (no ``X | Y`` union syntax in annotations).

    Parameters
    ----------
    collection_root:
        Override the collection root directory.  Defaults to
        ``~/.skillmeat/collection``.  Pass an explicit path in tests to avoid
        touching the real user home directory.

    Examples
    --------
    >>> resolver = ProjectPathResolver()
    >>> resolver.collection_root()
    PosixPath('/home/user/.skillmeat/collection')

    >>> resolver = ProjectPathResolver(collection_root=Path("/tmp/test-collection"))
    >>> str(resolver.artifacts_dir())
    '/tmp/test-collection/artifacts'
    """

    def __init__(self, collection_root: Optional[Path] = None) -> None:
        if collection_root is not None:
            self._collection_root = Path(collection_root)
        else:
            self._collection_root = (
                Path.home() / ".skillmeat" / _DEFAULT_COLLECTION_SUBDIR
            )

    # ------------------------------------------------------------------
    # Collection paths
    # ------------------------------------------------------------------

    def collection_root(self) -> Path:
        """Return the collection root directory (``~/.skillmeat/collection``).

        Returns
        -------
        Path
            Absolute path to the collection root.
        """
        return self._collection_root

    def artifacts_dir(self) -> Path:
        """Return the artifacts sub-directory of the collection.

        Returns
        -------
        Path
            ``<collection_root>/artifacts``
        """
        return self._collection_root / _ARTIFACTS_SUBDIR

    def artifact_path(self, name: str, artifact_type: str) -> Path:
        """Return the directory path for a specific artifact in the collection.

        Artifacts are stored under
        ``<collection_root>/artifacts/<type>s/<name>`` following the
        convention established by ``CollectionManager``.  The plural form
        (e.g. ``skills``, ``commands``) is used as the container directory
        name to match the layout on disk.

        Parameters
        ----------
        name:
            Artifact name (e.g. ``"canvas-design"``).
        artifact_type:
            Artifact type string, singular form (e.g. ``"skill"``,
            ``"command"``, ``"agent"``, ``"hook"``, ``"mcp"``).

        Returns
        -------
        Path
            ``<collection_root>/artifacts/<artifact_type_plural>/<name>``

        Raises
        ------
        ValueError
            If *artifact_type* is not a recognised type string.
        """
        container = DEFAULT_ARTIFACT_PATH_MAP.get(artifact_type)
        if not container:
            raise ValueError(
                f"Unknown artifact type '{artifact_type}'. "
                f"Valid types: {sorted(DEFAULT_ARTIFACT_PATH_MAP)}"
            )
        return self.artifacts_dir() / container / name

    def manifest_path(self) -> Path:
        """Return the path to the collection manifest file.

        Returns
        -------
        Path
            ``<collection_root>/manifest.toml``
        """
        return self._collection_root / _MANIFEST_FILENAME

    def lockfile_path(self) -> Path:
        """Return the path to the collection lock-file.

        Returns
        -------
        Path
            ``<collection_root>/lockfile.toml``
        """
        return self._collection_root / _LOCKFILE_FILENAME

    def snapshots_dir(self) -> Path:
        """Return the snapshots directory for the collection.

        Snapshots are stored as siblings of the collection root under
        ``~/.skillmeat/snapshots`` so that they are not accidentally
        treated as collection contents.

        Returns
        -------
        Path
            ``<collection_root_parent>/snapshots``
        """
        return self._collection_root.parent / _SNAPSHOTS_SUBDIR

    # ------------------------------------------------------------------
    # Deployment target paths
    # ------------------------------------------------------------------

    def user_deploy_dir(self) -> Path:
        """Return the global (user-scope) skill deployment directory.

        This is the directory that Claude Code reads from at startup when
        resolving user-scoped skills: ``~/.claude/skills/user/``.

        Returns
        -------
        Path
            ``~/.claude/skills/user``
        """
        result = Path.home()
        for segment in _USER_DEPLOY_SEGMENTS:
            result = result / segment
        return result

    def local_deploy_dir(self, project_root: Path) -> Path:
        """Return the local (project-scope) skill deployment directory.

        This is the directory inside a specific project from which Claude
        Code loads project-local skills: ``<project_root>/.claude/skills/``.

        Parameters
        ----------
        project_root:
            Absolute path to the project root directory.

        Returns
        -------
        Path
            ``<project_root>/.claude/skills``
        """
        result = Path(project_root)
        for segment in _LOCAL_DEPLOY_SEGMENTS:
            result = result / segment
        return result

    def deploy_target(
        self,
        scope: str,
        project_root: Optional[Path] = None,
    ) -> Path:
        """Resolve a deployment target directory by scope name.

        Parameters
        ----------
        scope:
            Either ``"user"`` (global, ``~/.claude/skills/user/``) or
            ``"local"`` (project-specific, ``<project_root>/.claude/skills/``).
        project_root:
            Required when *scope* is ``"local"``; ignored for ``"user"`` scope.

        Returns
        -------
        Path
            The resolved deployment target directory.

        Raises
        ------
        ValueError
            If *scope* is not ``"user"`` or ``"local"``, or if *scope* is
            ``"local"`` but *project_root* is not provided.
        """
        if scope == "user":
            return self.user_deploy_dir()
        if scope == "local":
            if project_root is None:
                raise ValueError(
                    "project_root must be provided when scope is 'local'"
                )
            return self.local_deploy_dir(project_root)
        raise ValueError(
            f"Invalid scope '{scope}'. Valid values: 'user', 'local'"
        )
