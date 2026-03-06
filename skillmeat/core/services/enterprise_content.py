"""Enterprise content assembly service.

Builds and streams artifact payload bundles for enterprise download.  Each
bundle carries the artifact's DB metadata, a content hash for integrity
verification, and the full file tree read from the filesystem collection.

Design notes
------------
- Pure Python class — no FastAPI imports.  The router (ENT-3.2) wraps this.
- Filesystem root is ``~/.skillmeat/collections/<collection>/``.  The
  ``artifact_path`` column on ``EnterpriseArtifact`` (stored in
  ``source_url`` / ``custom_fields``) is used when available; otherwise the
  service falls back to the canonical per-type layout used by
  ``ArtifactManager``:

    skills/<name>/          directory artifact (Skill)
    commands/<name>.md      single-file artifact (Command)
    agents/<name>.md        single-file artifact (Agent)
    composites/<name>/      directory artifact (Composite / Plugin)
    workflows/<name>/       directory artifact (Workflow)

- Compression: ``gzip`` stdlib only — no third-party deps.
- Version resolution order (``version`` parameter):

    1. ``content_hash`` exact match across all versions of the artifact.
    2. ``version_tag`` exact match (e.g. ``"v1.2.0"``, ``"latest"``).
    3. ``None`` / omitted → latest version by ``created_at``.

Usage::

    from sqlalchemy.orm import Session
    from skillmeat.cache.enterprise_repositories import EnterpriseArtifactRepository
    from skillmeat.core.services.enterprise_content import EnterpriseContentService

    service = EnterpriseContentService(
        session=db_session,
        artifact_repo=EnterpriseArtifactRepository(db_session),
    )

    # Uncompressed dict (JSON-serialisable)
    payload = service.build_payload("canvas-design")

    # gzip-compressed bytes ready for a streaming HTTP response
    compressed = service.build_payload("canvas-design", compress=True)
"""

from __future__ import annotations

import gzip
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from sqlalchemy.orm import Session

from skillmeat.cache.enterprise_repositories import EnterpriseArtifactRepository
from skillmeat.cache.models_enterprise import EnterpriseArtifactVersion
from sqlalchemy import select

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------


class ArtifactNotFoundError(Exception):
    """Raised when the requested artifact does not exist for the current tenant.

    Attributes
    ----------
    artifact_id:
        The identifier that was looked up (name, UUID string, or raw arg).
    """

    def __init__(self, artifact_id: str, detail: Optional[str] = None) -> None:
        self.artifact_id = artifact_id
        msg = f"Artifact not found: {artifact_id!r}"
        if detail:
            msg = f"{msg}. {detail}"
        super().__init__(msg)


class ArtifactVersionNotFoundError(Exception):
    """Raised when the requested artifact version does not exist.

    Attributes
    ----------
    artifact_id:
        The identifier of the parent artifact.
    version:
        The version string that was requested but not found.
    """

    def __init__(self, artifact_id: str, version: str) -> None:
        self.artifact_id = artifact_id
        self.version = version
        super().__init__(
            f"Version {version!r} not found for artifact {artifact_id!r}."
        )


class ArtifactFilesystemError(Exception):
    """Raised when the artifact's files cannot be read from the filesystem.

    This is a non-fatal condition from the DB perspective but prevents bundle
    assembly.  The router should map it to HTTP 422 or 503.

    Attributes
    ----------
    path:
        The filesystem path that could not be read.
    """

    def __init__(self, path: Path, cause: Optional[Exception] = None) -> None:
        self.path = path
        msg = f"Cannot read artifact files from {path!s}"
        if cause is not None:
            msg = f"{msg}: {cause}"
        super().__init__(msg)


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

#: A single file entry within the payload ``files`` list.
FileEntry = Dict[str, Any]

#: The uncompressed payload dict (JSON-serialisable).
ArtifactPayload = Dict[str, Any]


# ---------------------------------------------------------------------------
# Helper: filesystem path resolution
# ---------------------------------------------------------------------------

# Maps artifact_type → subdirectory name within a collection root.
_DIR_ARTIFACT_TYPES: frozenset[str] = frozenset(
    {"skill", "composite", "workflow", "mcp", "mcp_server"}
)

# Types stored as single files (``<subdir>/<name>.md``).
_FILE_ARTIFACT_TYPES: frozenset[str] = frozenset({"command", "agent", "hook"})

# Subdir names per type for the canonical layout.
_TYPE_SUBDIR: Dict[str, str] = {
    "skill": "skills",
    "command": "commands",
    "agent": "agents",
    "composite": "composites",
    "workflow": "workflows",
    "mcp": "mcp",
    "mcp_server": "mcp",
    "hook": "hooks",
}

# Files excluded from bundle assembly (mirrors skillmeat/core/hashing.py exclusions).
_EXCLUDED_NAMES: frozenset[str] = frozenset(
    {".DS_Store", "Thumbs.db", ".gitkeep", ".git"}
)
_EXCLUDED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        "venv",
        ".venv",
        "dist",
        "build",
    }
)
_EXCLUDED_SUFFIXES: tuple[str, ...] = (".tmp", ".swp", ".swo", "~")
_EXCLUDED_PREFIXES: tuple[str, ...] = ("~$", ".#")


def _is_excluded(name: str) -> bool:
    """Return True if a file or directory name should be skipped in bundle assembly."""
    if name in _EXCLUDED_NAMES or name in _EXCLUDED_DIRS:
        return True
    for prefix in _EXCLUDED_PREFIXES:
        if name.startswith(prefix):
            return True
    for suffix in _EXCLUDED_SUFFIXES:
        if name.endswith(suffix):
            return True
    return False


def _resolve_artifact_fs_path(
    name: str,
    artifact_type: str,
    collection_root: Path,
    custom_fields: Optional[Dict[str, Any]] = None,
) -> Path:
    """Return the filesystem path for an artifact's files.

    Resolution order:
    1. ``custom_fields["fs_path"]`` — explicit override stored at import time.
    2. Canonical layout derived from *artifact_type* and *name*.

    Parameters
    ----------
    name:
        Human-readable artifact name (e.g. ``"canvas-design"``).
    artifact_type:
        Artifact type string (e.g. ``"skill"``, ``"command"``).
    collection_root:
        Root of the collection on disk (e.g. ``~/.skillmeat/collections/default``).
    custom_fields:
        Optional ``EnterpriseArtifact.custom_fields`` JSONB dict.  When the
        key ``"fs_path"`` is present its value is used directly (relative to
        *collection_root* if not absolute).

    Returns
    -------
    Path
        Resolved absolute filesystem path (may not exist).
    """
    if custom_fields:
        override = custom_fields.get("fs_path")
        if override:
            candidate = Path(override)
            if not candidate.is_absolute():
                candidate = collection_root / candidate
            return candidate

    subdir = _TYPE_SUBDIR.get(artifact_type, artifact_type + "s")

    if artifact_type in _FILE_ARTIFACT_TYPES:
        return collection_root / subdir / f"{name}.md"

    # Directory-based artifact
    return collection_root / subdir / name


# ---------------------------------------------------------------------------
# Helper: file tree reader
# ---------------------------------------------------------------------------


def _read_file_tree(root: Path) -> List[FileEntry]:
    """Walk *root* and collect all includable files as ``FileEntry`` dicts.

    Parameters
    ----------
    root:
        Directory to walk.

    Returns
    -------
    list[FileEntry]
        Sorted (by relative POSIX path) list of file entries::

            {
                "path": "relative/posix/path",
                "content": "<utf-8 text or base64>",
                "size": <int bytes>,
                "encoding": "utf-8" | "base64",
            }
    """
    entries: List[FileEntry] = []

    for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
        # Prune excluded dirs in-place to avoid descending into them.
        dirnames[:] = sorted(d for d in dirnames if not _is_excluded(d))

        for filename in sorted(filenames):
            if _is_excluded(filename):
                continue

            full_path = Path(dirpath) / filename
            try:
                if not full_path.is_file():
                    continue
                size = full_path.stat().st_size
            except OSError:
                continue

            relative = full_path.relative_to(root).as_posix()

            # Attempt UTF-8 text read; fall back to base64 for binary files.
            try:
                content = full_path.read_text(encoding="utf-8")
                encoding = "utf-8"
            except (UnicodeDecodeError, OSError):
                import base64

                try:
                    content = base64.b64encode(full_path.read_bytes()).decode("ascii")
                    encoding = "base64"
                except OSError:
                    logger.debug("Skipping unreadable file: %s", full_path)
                    continue

            entries.append(
                {
                    "path": relative,
                    "content": content,
                    "size": size,
                    "encoding": encoding,
                }
            )

    return sorted(entries, key=lambda e: e["path"])


def _read_single_file(path: Path) -> List[FileEntry]:
    """Read a single-file artifact and return it as a one-element ``FileEntry`` list.

    Parameters
    ----------
    path:
        Absolute path to the file.

    Returns
    -------
    list[FileEntry]
        One-element list containing the file's content.

    Raises
    ------
    ArtifactFilesystemError
        If the file cannot be read.
    """
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ArtifactFilesystemError(path, exc) from exc

    try:
        content = path.read_text(encoding="utf-8")
        encoding = "utf-8"
    except (UnicodeDecodeError, OSError):
        import base64

        try:
            content = base64.b64encode(path.read_bytes()).decode("ascii")
            encoding = "base64"
        except OSError as exc:
            raise ArtifactFilesystemError(path, exc) from exc

    return [
        {
            "path": path.name,
            "content": content,
            "size": size,
            "encoding": encoding,
        }
    ]


# ---------------------------------------------------------------------------
# EnterpriseContentService
# ---------------------------------------------------------------------------


class EnterpriseContentService:
    """Service that builds and optionally compresses artifact payload bundles.

    Designed to be instantiated per-request with an injected DB session and
    repository, following the same pattern as other enterprise services in
    this package.

    Parameters
    ----------
    session:
        An open SQLAlchemy ``Session`` bound to the PostgreSQL enterprise
        database.  Transaction management is the caller's responsibility.
    artifact_repo:
        An ``EnterpriseArtifactRepository`` instance pre-configured with
        the same *session* and the current tenant scope via ``tenant_scope()``.
    collection_root:
        Filesystem root of the user's default collection.  Defaults to
        ``~/.skillmeat/collections/default`` when ``None``.

    Examples
    --------
    Typical usage inside a FastAPI route dependency::

        with tenant_scope(tenant_id):
            repo = EnterpriseArtifactRepository(db_session)
            svc  = EnterpriseContentService(
                session=db_session,
                artifact_repo=repo,
            )
            payload = svc.build_payload("canvas-design", compress=False)
    """

    #: Default collection name used for filesystem path resolution.
    DEFAULT_COLLECTION: str = "default"

    def __init__(
        self,
        session: Session,
        artifact_repo: EnterpriseArtifactRepository,
        collection_root: Optional[Path] = None,
    ) -> None:
        self._session = session
        self._repo = artifact_repo
        if collection_root is not None:
            self._collection_root = collection_root
        else:
            self._collection_root = (
                Path.home() / ".skillmeat" / "collections" / self.DEFAULT_COLLECTION
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_payload(
        self,
        artifact_id: str,
        version: Optional[str] = None,
        compress: bool = False,
    ) -> Union[ArtifactPayload, bytes]:
        """Build a complete artifact bundle for enterprise download.

        Parameters
        ----------
        artifact_id:
            Artifact identifier — either a UUID string (looked up by primary
            key) or a human-readable name (looked up by name within the
            current tenant).
        version:
            Optional version specifier.  Resolution order:

            1. Exact ``content_hash`` match (64-char hex string).
            2. Exact ``version_tag`` match (e.g. ``"v1.2.0"``).
            3. ``None`` — latest version by ``created_at``.
        compress:
            When ``True``, gzip-compress the JSON-serialised payload and
            return ``bytes``.  When ``False`` (default), return the raw
            ``dict``.

        Returns
        -------
        ArtifactPayload or bytes
            Uncompressed ``dict`` when *compress* is ``False``; gzip
            ``bytes`` when ``True``.

        Raises
        ------
        ArtifactNotFoundError
            If the artifact does not exist for the current tenant.
        ArtifactVersionNotFoundError
            If *version* was specified but no matching version exists.
        ArtifactFilesystemError
            If the artifact's files cannot be read from the filesystem.
        ValueError
            If *artifact_id* is an invalid UUID string when UUID lookup is
            attempted.
        """
        artifact = self._resolve_artifact(artifact_id)
        version_row = self._resolve_version(artifact, version)

        # Build the version string included in the payload.
        resolved_version: str = (
            version_row.version_tag if version_row is not None else "unknown"
        )
        resolved_hash: str = (
            version_row.content_hash if version_row is not None else ""
        )

        # Resolve the filesystem path and collect files.
        fs_path = _resolve_artifact_fs_path(
            name=artifact.name,
            artifact_type=artifact.artifact_type,
            collection_root=self._collection_root,
            custom_fields=artifact.custom_fields,
        )
        files = self._collect_files(fs_path, artifact.artifact_type)

        payload: ArtifactPayload = {
            "artifact_id": str(artifact.id),
            "version": resolved_version,
            "content_hash": resolved_hash,
            "metadata": {
                "name": artifact.name,
                "type": artifact.artifact_type,
                "source": artifact.source_url,
                "description": artifact.description,
                "tags": artifact.tags,
                "scope": artifact.scope,
            },
            "files": files,
        }

        logger.info(
            "Built enterprise content payload: artifact=%s version=%s files=%d compress=%s",
            artifact.id,
            resolved_version,
            len(files),
            compress,
        )

        if compress:
            return self._compress(payload)
        return payload

    def get_version_list(
        self, artifact_id: str
    ) -> List[Dict[str, Any]]:
        """Return a summary list of all versions for an artifact.

        Parameters
        ----------
        artifact_id:
            UUID string or artifact name.

        Returns
        -------
        list[dict]
            Each entry has keys: ``version_tag``, ``content_hash``,
            ``created_at`` (ISO-8601 string), ``commit_sha``.

        Raises
        ------
        ArtifactNotFoundError
            If the artifact does not exist for the current tenant.
        """
        artifact = self._resolve_artifact(artifact_id)
        versions = self._repo.list_versions(artifact.id)
        return [
            {
                "version_tag": v.version_tag,
                "content_hash": v.content_hash,
                "created_at": v.created_at.isoformat(),
                "commit_sha": v.commit_sha,
            }
            for v in versions
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_artifact(self, artifact_id: str):  # type: ignore[return]
        """Look up an artifact by UUID string or name.

        Tries UUID parse first; falls back to name lookup.

        Parameters
        ----------
        artifact_id:
            UUID string or human-readable name.

        Returns
        -------
        EnterpriseArtifact

        Raises
        ------
        ArtifactNotFoundError
            If neither lookup finds the artifact.
        """
        from skillmeat.cache.models_enterprise import EnterpriseArtifact  # local import to avoid circular

        # Attempt UUID parse first.
        artifact = None
        try:
            parsed_uuid = uuid.UUID(artifact_id)
            artifact = self._repo.get(parsed_uuid)
        except ValueError:
            # Not a valid UUID — fall through to name lookup.
            pass

        if artifact is None:
            artifact = self._repo.get_by_name(artifact_id)

        if artifact is None:
            raise ArtifactNotFoundError(artifact_id)

        return artifact

    def _resolve_version(
        self,
        artifact,  # EnterpriseArtifact
        version: Optional[str],
    ) -> Optional["EnterpriseArtifactVersion"]:
        """Resolve *version* to an ``EnterpriseArtifactVersion`` row.

        Resolution order:
        1. If *version* is a 64-char hex string → match by ``content_hash``.
        2. Otherwise → match by ``version_tag``.
        3. *version* is ``None`` → return the latest (newest ``created_at``).

        Parameters
        ----------
        artifact:
            Parent ``EnterpriseArtifact`` instance (already tenant-validated).
        version:
            Version specifier string or ``None``.

        Returns
        -------
        EnterpriseArtifactVersion or None
            ``None`` only when the artifact has no version rows at all and
            *version* was also ``None`` (caller handles gracefully).

        Raises
        ------
        ArtifactVersionNotFoundError
            When *version* is specified but no matching row exists.
        """
        from skillmeat.cache.models_enterprise import EnterpriseArtifactVersion

        if version is None:
            # Latest version by created_at desc.
            stmt = (
                select(EnterpriseArtifactVersion)
                .where(EnterpriseArtifactVersion.artifact_id == artifact.id)
                .order_by(EnterpriseArtifactVersion.created_at.desc())
                .limit(1)
            )
            return self._session.execute(stmt).scalar_one_or_none()

        # Determine lookup strategy: content_hash (64 hex chars) or version_tag.
        is_hash_lookup = len(version) == 64 and all(
            c in "0123456789abcdefABCDEF" for c in version
        )

        if is_hash_lookup:
            stmt = select(EnterpriseArtifactVersion).where(
                EnterpriseArtifactVersion.artifact_id == artifact.id,
                EnterpriseArtifactVersion.content_hash == version.lower(),
            )
        else:
            stmt = select(EnterpriseArtifactVersion).where(
                EnterpriseArtifactVersion.artifact_id == artifact.id,
                EnterpriseArtifactVersion.version_tag == version,
            )

        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            raise ArtifactVersionNotFoundError(
                artifact_id=str(artifact.id), version=version
            )
        return row

    def _collect_files(
        self, fs_path: Path, artifact_type: str
    ) -> List[FileEntry]:
        """Read artifact files from *fs_path* and return ``FileEntry`` list.

        Parameters
        ----------
        fs_path:
            Resolved filesystem path (file or directory).
        artifact_type:
            Used to decide whether the path should be a file or directory.

        Returns
        -------
        list[FileEntry]
            Sorted list of file entries (empty list if path does not exist).

        Raises
        ------
        ArtifactFilesystemError
            If the path exists but cannot be read.
        """
        if not fs_path.exists():
            logger.warning(
                "Artifact filesystem path does not exist: %s — returning empty file list",
                fs_path,
            )
            return []

        if fs_path.is_file():
            return _read_single_file(fs_path)

        if fs_path.is_dir():
            try:
                return _read_file_tree(fs_path)
            except Exception as exc:
                raise ArtifactFilesystemError(fs_path, exc) from exc

        raise ArtifactFilesystemError(
            fs_path,
            ValueError(f"Path is neither a file nor a directory: {fs_path}"),
        )

    @staticmethod
    def _compress(payload: ArtifactPayload) -> bytes:
        """JSON-serialise *payload* and gzip-compress it.

        Parameters
        ----------
        payload:
            JSON-serialisable dict to compress.

        Returns
        -------
        bytes
            gzip-compressed UTF-8 JSON bytes (``Content-Encoding: gzip``).
        """
        raw = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        return gzip.compress(raw, compresslevel=6)
