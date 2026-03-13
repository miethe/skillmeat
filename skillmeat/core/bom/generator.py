"""BomGenerator service and adapter infrastructure for SkillMeat.

This module implements the core BOM (Bill of Materials) generation pipeline:

1.  ``BaseArtifactAdapter`` — abstract base class that every per-type adapter
    must implement.  Adapters transform an ORM ``Artifact`` row into a
    normalised BOM-entry dict and compute its content hash.

2.  ``SkillAdapter`` — reference implementation for skill-type artifacts.
    Skills are directory-based, so content hashing uses the Merkle-tree
    algorithm from ``skillmeat.core.hashing``.  File-content fallback is used
    when no filesystem path is resolvable (e.g. content stored in DB column).

3.  ``BomGenerator`` — orchestrator that:
    - Queries deployed artifacts from the SQLAlchemy session (1.x-style
      ``session.query()`` matching local-repo conventions).
    - Resolves the correct adapter for each artifact type via an internal
      registry.
    - Collects BOM entries and assembles the final BOM dict.
    - Guarantees determinism by sorting entries by ``(type, name)`` before
      returning.

Design decisions
----------------
* **No hard failure on missing adapters** — unknown artifact types are logged
  as warnings and skipped so partial BOMs are still useful.
* **Idempotent** — calling ``generate()`` twice with the same DB state returns
  identical output.
* **Adapter registry is open** — callers may register additional adapters via
  ``BomGenerator.register_adapter()`` before calling ``generate()``.
* **Content-hash strategy** — adapters prefer filesystem paths (resolved from
  ``Artifact.source`` or ``project_path``) but fall back to hashing the DB
  ``content`` column bytes, and ultimately emit an empty-string hash when
  neither is available, logging a warning.
"""

from __future__ import annotations

import hashlib
import json
import logging
import mimetypes
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from skillmeat.cache.models import Artifact, CompositeMembership
from skillmeat.core.hashing import compute_artifact_hash

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# BOM schema constant
# ---------------------------------------------------------------------------

_BOM_SCHEMA_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Base adapter
# ---------------------------------------------------------------------------


class BaseArtifactAdapter(ABC):
    """Abstract base class for BOM artifact adapters.

    Each concrete subclass handles one artifact type (e.g. skill, command,
    agent) and is responsible for:

    * Producing a normalised BOM-entry dict from an ORM ``Artifact`` row.
    * Computing a deterministic SHA-256 content hash for that artifact.

    Subclasses must not maintain mutable state between ``adapt()`` calls so
    that the adapter instances may be reused across many artifacts.
    """

    @abstractmethod
    def get_artifact_type(self) -> str:
        """Return the artifact type string this adapter handles.

        Returns:
            One of the type strings recognised by the ``artifacts`` table
            ``check_artifact_type`` constraint, e.g. ``"skill"``.
        """

    @abstractmethod
    def compute_content_hash(
        self,
        artifact: Artifact,
        project_path: Optional[Path] = None,
    ) -> str:
        """Return the SHA-256 hex digest for *artifact*'s content.

        Implementations should prefer filesystem-based hashing when a path is
        resolvable, then fall back to hashing the DB ``content`` column, and
        finally return ``""`` (empty string) with a warning when nothing is
        available.

        Args:
            artifact: The ORM artifact row to hash.
            project_path: Optional base project directory used to resolve
                          relative deployment paths.

        Returns:
            64-character lowercase hex string, or ``""`` on failure.
        """

    @abstractmethod
    def adapt(
        self,
        artifact: Artifact,
        project_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Return a normalised BOM-entry dict for *artifact*.

        The dict MUST contain at minimum:

        .. code-block:: python

            {
                "name":         str,   # artifact.name
                "type":         str,   # artifact.type
                "source":       str | None,
                "version":      str | None,
                "content_hash": str,   # SHA-256 hex or ""
                "metadata":     dict,  # arbitrary per-type metadata
            }

        Args:
            artifact: The ORM artifact row to convert.
            project_path: Optional base project directory; forwarded to
                          ``compute_content_hash``.

        Returns:
            BOM-entry dict as described above.
        """


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _hash_string(text: str) -> str:
    """Return the SHA-256 hex digest of *text* encoded as UTF-8.

    Args:
        text: Arbitrary string to hash.

    Returns:
        64-character lowercase hex string.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hash_bytes(data: bytes) -> str:
    """Return the SHA-256 hex digest of *data*.

    Args:
        data: Raw bytes to hash.

    Returns:
        64-character lowercase hex string.
    """
    return hashlib.sha256(data).hexdigest()


def _resolve_artifact_fs_path(
    artifact: Artifact,
    project_path: Optional[Path],
) -> Optional[Path]:
    """Try to resolve a filesystem path for *artifact*.

    Resolution order:

    1. ``project_path / <type_dir> / <name>`` — standard deployment layout.
    2. ``source`` field parsed as a local absolute path when it starts with
       ``"/"`` or ``"."``.
    3. ``None`` when no path can be determined.

    Args:
        artifact: ORM artifact row.
        project_path: Optional project root directory.

    Returns:
        A ``Path`` that *exists* on disk, or ``None``.
    """
    # Attempt 1: derive from project layout.
    if project_path is not None:
        # Canonical deployment paths per type (mirrors path_resolver defaults).
        _TYPE_DIRS: Dict[str, str] = {
            "skill": ".claude/skills",
            "command": ".claude/commands",
            "agent": ".claude/agents",
            "mcp": ".claude/mcp",
            "mcp_server": ".claude/mcp",
            "hook": ".claude/hooks",
            "workflow": ".claude/workflows",
            "composite": ".claude/skills",
        }
        type_dir = _TYPE_DIRS.get(artifact.type)
        if type_dir:
            candidate = project_path / type_dir / artifact.name
            if candidate.exists():
                return candidate

    # Attempt 2: treat source as a local path.
    if artifact.source and (
        artifact.source.startswith("/") or artifact.source.startswith(".")
    ):
        candidate = Path(artifact.source)
        if candidate.exists():
            return candidate

    return None


# ---------------------------------------------------------------------------
# SkillAdapter — reference implementation
# ---------------------------------------------------------------------------


class SkillAdapter(BaseArtifactAdapter):
    """BOM adapter for skill-type artifacts.

    Skills are directory-based artifacts.  Content hashing uses the Merkle-tree
    algorithm from ``skillmeat.core.hashing.compute_artifact_hash`` when a
    filesystem path is resolvable.  When only DB content is available the raw
    UTF-8 bytes are hashed instead.

    Metadata extracted per BOM entry:

    * ``author``, ``description`` — from ``artifact_metadata`` relationship.
    * ``tags`` — comma-split from ``artifact_metadata.tags``.
    * ``created_at``, ``updated_at`` — ISO-8601 timestamps from ``Artifact``.
    """

    def get_artifact_type(self) -> str:
        """Return ``"skill"``."""
        return "skill"

    def compute_content_hash(
        self,
        artifact: Artifact,
        project_path: Optional[Path] = None,
    ) -> str:
        """Compute content hash for a skill artifact.

        Tries filesystem hashing first (Merkle-tree over directory), then
        falls back to hashing the DB ``content`` column.

        Args:
            artifact: ORM artifact row.
            project_path: Optional project root directory.

        Returns:
            64-character lowercase hex string, or ``""`` on failure.
        """
        # Prefer filesystem path.
        fs_path = _resolve_artifact_fs_path(artifact, project_path)
        if fs_path is not None:
            try:
                return compute_artifact_hash(str(fs_path))
            except (FileNotFoundError, ValueError, OSError) as exc:
                logger.debug(
                    "Filesystem hash failed for skill %r (%s); falling back to DB content.",
                    artifact.name,
                    exc,
                )

        # Fall back to DB content column (may be None).
        if artifact.content_hash:
            # Reuse the already-stored hash if present (e.g. populated by refresh).
            logger.debug(
                "Using cached content_hash from DB for skill %r.", artifact.name
            )
            return artifact.content_hash

        if artifact.content:
            return _hash_string(artifact.content)

        logger.warning(
            "Cannot compute content hash for skill %r (id=%r): "
            "no filesystem path and no DB content available.",
            artifact.name,
            artifact.id,
        )
        return ""

    def adapt(
        self,
        artifact: Artifact,
        project_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Return a normalised BOM entry for a skill artifact.

        Args:
            artifact: ORM artifact row (with ``artifact_metadata`` eagerly
                      loaded or accessible via lazy select).
            project_path: Optional project root directory.

        Returns:
            BOM-entry dict with keys: name, type, source, version,
            content_hash, metadata.
        """
        content_hash = self.compute_content_hash(artifact, project_path)

        # Extract extended metadata from the ArtifactMetadata relationship.
        meta = artifact.artifact_metadata
        author: Optional[str] = None
        description: Optional[str] = None
        tags: List[str] = []

        if meta is not None:
            description = meta.description
            if meta.tags:
                tags = [t.strip() for t in meta.tags.split(",") if t.strip()]
            # author may live in the raw metadata_json blob.
            if meta.metadata_json:
                try:
                    raw_meta = json.loads(meta.metadata_json)
                    author = raw_meta.get("author")
                    if not description:
                        description = raw_meta.get("description")
                except (json.JSONDecodeError, AttributeError):
                    pass

        return {
            "name": artifact.name,
            "type": artifact.type,
            "source": artifact.source,
            "version": artifact.deployed_version or artifact.upstream_version,
            "content_hash": content_hash,
            "metadata": {
                "author": author,
                "description": description,
                "tags": tags,
                "created_at": (
                    artifact.created_at.isoformat() if artifact.created_at else None
                ),
                "updated_at": (
                    artifact.updated_at.isoformat() if artifact.updated_at else None
                ),
            },
        }


# ---------------------------------------------------------------------------
# Shared helper for metadata extraction (used by multiple adapters)
# ---------------------------------------------------------------------------


def _extract_standard_metadata(
    artifact: Artifact,
) -> Dict[str, Any]:
    """Extract the standard metadata block from an ``Artifact`` row.

    Pulls ``author``, ``description``, and ``tags`` from the
    ``artifact_metadata`` relationship (including the ``metadata_json`` blob)
    and adds ``created_at``/``updated_at`` ISO-8601 timestamps.

    Args:
        artifact: ORM artifact row with accessible ``artifact_metadata``.

    Returns:
        Metadata dict suitable for inclusion in a BOM entry.
    """
    meta = artifact.artifact_metadata
    author: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = []

    if meta is not None:
        description = meta.description
        if meta.tags:
            tags = [t.strip() for t in meta.tags.split(",") if t.strip()]
        if meta.metadata_json:
            try:
                raw_meta = json.loads(meta.metadata_json)
                author = raw_meta.get("author")
                if not description:
                    description = raw_meta.get("description")
            except (json.JSONDecodeError, AttributeError):
                pass

    return {
        "author": author,
        "description": description,
        "tags": tags,
        "created_at": (
            artifact.created_at.isoformat() if artifact.created_at else None
        ),
        "updated_at": (
            artifact.updated_at.isoformat() if artifact.updated_at else None
        ),
    }


def _compute_directory_or_db_hash(
    artifact: Artifact,
    project_path: Optional[Path],
) -> str:
    """Compute content hash for a directory-based artifact.

    Strategy (in order):
    1. Filesystem Merkle-tree via ``compute_artifact_hash`` if path resolves.
    2. Cached ``content_hash`` DB column.
    3. Hash of ``content`` DB column text.
    4. Empty string with warning.

    Args:
        artifact: ORM artifact row.
        project_path: Optional project root directory.

    Returns:
        64-character lowercase hex string, or ``""`` on failure.
    """
    fs_path = _resolve_artifact_fs_path(artifact, project_path)
    if fs_path is not None:
        try:
            return compute_artifact_hash(str(fs_path))
        except (FileNotFoundError, ValueError, OSError) as exc:
            logger.debug(
                "Filesystem hash failed for %r %r (%s); falling back to DB content.",
                artifact.type,
                artifact.name,
                exc,
            )

    if artifact.content_hash:
        logger.debug(
            "Using cached content_hash from DB for %r %r.",
            artifact.type,
            artifact.name,
        )
        return artifact.content_hash

    if artifact.content:
        return _hash_string(artifact.content)

    logger.warning(
        "Cannot compute content hash for %r %r (id=%r): "
        "no filesystem path and no DB content available.",
        artifact.type,
        artifact.name,
        artifact.id,
    )
    return ""


# ---------------------------------------------------------------------------
# TASK-2.2: CommandAdapter
# ---------------------------------------------------------------------------


class CommandAdapter(BaseArtifactAdapter):
    """BOM adapter for command-type artifacts.

    Commands are typically stored under ``.claude/commands/<name>/``.
    Content hashing mirrors the ``SkillAdapter`` strategy: filesystem
    Merkle-tree when a path resolves, DB content otherwise.

    Metadata extracted per BOM entry:

    * ``author``, ``description``, ``tags`` — from ``artifact_metadata``.
    * ``created_at``, ``updated_at`` — ISO-8601 timestamps.
    """

    def get_artifact_type(self) -> str:
        """Return ``"command"``."""
        return "command"

    def compute_content_hash(
        self,
        artifact: Artifact,
        project_path: Optional[Path] = None,
    ) -> str:
        """Compute content hash for a command artifact.

        Args:
            artifact: ORM artifact row.
            project_path: Optional project root directory.

        Returns:
            64-character lowercase hex string, or ``""`` on failure.
        """
        return _compute_directory_or_db_hash(artifact, project_path)

    def adapt(
        self,
        artifact: Artifact,
        project_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Return a normalised BOM entry for a command artifact.

        Args:
            artifact: ORM artifact row.
            project_path: Optional project root directory.

        Returns:
            BOM-entry dict with keys: name, type, source, version,
            content_hash, metadata.
        """
        return {
            "name": artifact.name,
            "type": artifact.type,
            "source": artifact.source,
            "version": artifact.deployed_version or artifact.upstream_version,
            "content_hash": self.compute_content_hash(artifact, project_path),
            "metadata": _extract_standard_metadata(artifact),
        }


# ---------------------------------------------------------------------------
# TASK-2.3: AgentAdapter, McpAdapter
# ---------------------------------------------------------------------------


class AgentAdapter(BaseArtifactAdapter):
    """BOM adapter for agent-type artifacts.

    Agents reside under ``.claude/agents/<name>``.  Hashing and metadata
    extraction follow the same strategy as ``SkillAdapter``.
    """

    def get_artifact_type(self) -> str:
        """Return ``"agent"``."""
        return "agent"

    def compute_content_hash(
        self,
        artifact: Artifact,
        project_path: Optional[Path] = None,
    ) -> str:
        """Compute content hash for an agent artifact.

        Args:
            artifact: ORM artifact row.
            project_path: Optional project root directory.

        Returns:
            64-character lowercase hex string, or ``""`` on failure.
        """
        return _compute_directory_or_db_hash(artifact, project_path)

    def adapt(
        self,
        artifact: Artifact,
        project_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Return a normalised BOM entry for an agent artifact.

        Args:
            artifact: ORM artifact row.
            project_path: Optional project root directory.

        Returns:
            BOM-entry dict with keys: name, type, source, version,
            content_hash, metadata.
        """
        return {
            "name": artifact.name,
            "type": artifact.type,
            "source": artifact.source,
            "version": artifact.deployed_version or artifact.upstream_version,
            "content_hash": self.compute_content_hash(artifact, project_path),
            "metadata": _extract_standard_metadata(artifact),
        }


class McpAdapter(BaseArtifactAdapter):
    """BOM adapter for MCP server artifacts.

    MCP servers reside under ``.claude/mcp/<name>``.  Hashing and metadata
    extraction follow the same strategy as ``SkillAdapter``.
    """

    def get_artifact_type(self) -> str:
        """Return ``"mcp_server"``."""
        return "mcp_server"

    def compute_content_hash(
        self,
        artifact: Artifact,
        project_path: Optional[Path] = None,
    ) -> str:
        """Compute content hash for an MCP server artifact.

        Args:
            artifact: ORM artifact row.
            project_path: Optional project root directory.

        Returns:
            64-character lowercase hex string, or ``""`` on failure.
        """
        return _compute_directory_or_db_hash(artifact, project_path)

    def adapt(
        self,
        artifact: Artifact,
        project_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Return a normalised BOM entry for an MCP server artifact.

        Args:
            artifact: ORM artifact row.
            project_path: Optional project root directory.

        Returns:
            BOM-entry dict with keys: name, type, source, version,
            content_hash, metadata.
        """
        return {
            "name": artifact.name,
            "type": artifact.type,
            "source": artifact.source,
            "version": artifact.deployed_version or artifact.upstream_version,
            "content_hash": self.compute_content_hash(artifact, project_path),
            "metadata": _extract_standard_metadata(artifact),
        }


# ---------------------------------------------------------------------------
# TASK-2.4: HookAdapter, WorkflowAdapter, CompositeAdapter
# ---------------------------------------------------------------------------


class HookAdapter(BaseArtifactAdapter):
    """BOM adapter for hook-type artifacts.

    Hooks reside under ``.claude/hooks/<name>``.  Hashing and metadata
    extraction follow the same strategy as ``SkillAdapter``.
    """

    def get_artifact_type(self) -> str:
        """Return ``"hook"``."""
        return "hook"

    def compute_content_hash(
        self,
        artifact: Artifact,
        project_path: Optional[Path] = None,
    ) -> str:
        """Compute content hash for a hook artifact.

        Args:
            artifact: ORM artifact row.
            project_path: Optional project root directory.

        Returns:
            64-character lowercase hex string, or ``""`` on failure.
        """
        return _compute_directory_or_db_hash(artifact, project_path)

    def adapt(
        self,
        artifact: Artifact,
        project_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Return a normalised BOM entry for a hook artifact.

        Args:
            artifact: ORM artifact row.
            project_path: Optional project root directory.

        Returns:
            BOM-entry dict with keys: name, type, source, version,
            content_hash, metadata.
        """
        return {
            "name": artifact.name,
            "type": artifact.type,
            "source": artifact.source,
            "version": artifact.deployed_version or artifact.upstream_version,
            "content_hash": self.compute_content_hash(artifact, project_path),
            "metadata": _extract_standard_metadata(artifact),
        }


class WorkflowAdapter(BaseArtifactAdapter):
    """BOM adapter for workflow-type artifacts.

    Workflows are directory-based artifacts stored under
    ``.claude/workflows/<name>``.  Hashing and metadata extraction follow the
    same strategy as ``SkillAdapter``.
    """

    def get_artifact_type(self) -> str:
        """Return ``"workflow"``."""
        return "workflow"

    def compute_content_hash(
        self,
        artifact: Artifact,
        project_path: Optional[Path] = None,
    ) -> str:
        """Compute content hash for a workflow artifact.

        Args:
            artifact: ORM artifact row.
            project_path: Optional project root directory.

        Returns:
            64-character lowercase hex string, or ``""`` on failure.
        """
        return _compute_directory_or_db_hash(artifact, project_path)

    def adapt(
        self,
        artifact: Artifact,
        project_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Return a normalised BOM entry for a workflow artifact.

        Args:
            artifact: ORM artifact row.
            project_path: Optional project root directory.

        Returns:
            BOM-entry dict with keys: name, type, source, version,
            content_hash, metadata.
        """
        return {
            "name": artifact.name,
            "type": artifact.type,
            "source": artifact.source,
            "version": artifact.deployed_version or artifact.upstream_version,
            "content_hash": self.compute_content_hash(artifact, project_path),
            "metadata": _extract_standard_metadata(artifact),
        }


#: Maximum recursion depth for nested composite member resolution.
_COMPOSITE_MAX_DEPTH = 4


class CompositeAdapter(BaseArtifactAdapter):
    """BOM adapter for composite-type artifacts.

    Composites are multi-artifact bundles (e.g. plugins).  The BOM entry
    includes a ``members`` list that enumerates child artifact references
    resolved via ``CompositeMembership`` rows.

    Member resolution
    -----------------
    The adapter queries ``CompositeMembership`` rows where
    ``composite_id == artifact.id`` (both use the ``type:name`` string format).
    Each membership row's ``child_artifact`` relationship provides the child
    ``Artifact``.  Recursion is capped at ``_COMPOSITE_MAX_DEPTH`` to prevent
    cycles.

    Session access
    --------------
    A SQLAlchemy ``Session`` is required to query memberships.  Pass it via the
    ``session`` constructor argument.  When ``session`` is ``None`` the adapter
    logs a warning and returns an empty ``members`` list.

    Args:
        session: SQLAlchemy session for querying ``CompositeMembership`` rows.
    """

    def __init__(self, session: Optional[Session] = None) -> None:
        self._session = session

    def get_artifact_type(self) -> str:
        """Return ``"composite"``."""
        return "composite"

    def compute_content_hash(
        self,
        artifact: Artifact,
        project_path: Optional[Path] = None,
    ) -> str:
        """Compute content hash for a composite artifact.

        Computes a hash over the sorted member UUIDs so that any change in
        membership (add/remove/reorder) produces a different hash.  Falls back
        to filesystem / DB content hashing when no session is available.

        Args:
            artifact: ORM artifact row.
            project_path: Optional project root directory.

        Returns:
            64-character lowercase hex string, or ``""`` on failure.
        """
        if self._session is not None:
            try:
                memberships = (
                    self._session.query(CompositeMembership)
                    .filter(CompositeMembership.composite_id == artifact.id)
                    .all()
                )
                if memberships:
                    # Sort for determinism: hash over sorted child UUIDs.
                    child_uuids = sorted(m.child_artifact_uuid for m in memberships)
                    return _hash_string(
                        f"{artifact.id}:{'|'.join(child_uuids)}"
                    )
            except Exception as exc:
                logger.debug(
                    "Failed to query memberships for composite %r (%s); "
                    "falling back to directory hash.",
                    artifact.name,
                    exc,
                )

        return _compute_directory_or_db_hash(artifact, project_path)

    def _resolve_members(
        self, artifact: Artifact, depth: int
    ) -> List[Dict[str, Any]]:
        """Recursively resolve member artifacts up to ``_COMPOSITE_MAX_DEPTH``.

        Args:
            artifact: Parent composite ``Artifact`` row.
            depth: Current recursion depth (0 = first level).

        Returns:
            List of member dicts with keys: uuid, name, type, source,
            version, relationship_type, pinned_version_hash.
        """
        if depth >= _COMPOSITE_MAX_DEPTH:
            logger.debug(
                "Composite member recursion depth %d reached for %r; stopping.",
                depth,
                artifact.name,
            )
            return []

        if self._session is None:
            return []

        try:
            memberships = (
                self._session.query(CompositeMembership)
                .filter(CompositeMembership.composite_id == artifact.id)
                .all()
            )
        except Exception as exc:
            logger.warning(
                "Failed to query CompositeMembership for composite %r (id=%r): %s",
                artifact.name,
                artifact.id,
                exc,
            )
            return []

        members: List[Dict[str, Any]] = []
        for membership in memberships:
            child = membership.child_artifact
            if child is None:
                logger.debug(
                    "CompositeMembership child_artifact is None for uuid=%r; skipping.",
                    membership.child_artifact_uuid,
                )
                continue

            member_entry: Dict[str, Any] = {
                "uuid": child.uuid,
                "name": child.name,
                "type": child.type,
                "source": child.source,
                "version": child.deployed_version or child.upstream_version,
                "relationship_type": membership.relationship_type,
                "pinned_version_hash": membership.pinned_version_hash,
            }

            # Recurse if the child is itself a composite.
            if child.type == "composite":
                member_entry["members"] = self._resolve_members(
                    child, depth + 1
                )

            members.append(member_entry)

        return members

    def adapt(
        self,
        artifact: Artifact,
        project_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Return a normalised BOM entry for a composite artifact.

        Includes a ``members`` list populated by querying
        ``CompositeMembership`` rows for this composite.

        Args:
            artifact: ORM artifact row.
            project_path: Optional project root directory.

        Returns:
            BOM-entry dict with keys: name, type, source, version,
            content_hash, metadata, members.
        """
        if self._session is None:
            logger.warning(
                "CompositeAdapter has no session; members list will be empty "
                "for composite artifact %r (id=%r).",
                artifact.name,
                artifact.id,
            )

        meta = _extract_standard_metadata(artifact)

        return {
            "name": artifact.name,
            "type": artifact.type,
            "source": artifact.source,
            "version": artifact.deployed_version or artifact.upstream_version,
            "content_hash": self.compute_content_hash(artifact, project_path),
            "metadata": meta,
            "members": self._resolve_members(artifact, depth=0),
        }


# ---------------------------------------------------------------------------
# TASK-2.5: ConfigAdapter, SpecAdapter, RuleAdapter, ContextFileAdapter
# ---------------------------------------------------------------------------

#: File extensions recognised as plain-text for MIME guessing.
_TEXT_EXTENSIONS: Dict[str, str] = {
    ".md": "text/markdown",
    ".py": "text/x-python",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
    ".json": "application/json",
    ".toml": "application/toml",
    ".txt": "text/plain",
    ".sh": "application/x-sh",
    ".ts": "text/typescript",
    ".tsx": "text/typescript",
    ".jsx": "text/javascript",
    ".js": "text/javascript",
    ".css": "text/css",
}


def _guess_mime_type(path: Optional[Path]) -> Optional[str]:
    """Guess the MIME type of *path* based on its file extension.

    Checks a curated ``_TEXT_EXTENSIONS`` dict first; falls back to
    ``mimetypes.guess_type`` from the stdlib for anything else.

    Args:
        path: Filesystem path whose extension is inspected.  May be ``None``.

    Returns:
        MIME type string (e.g. ``"text/markdown"``) or ``None`` when
        the type cannot be determined.
    """
    if path is None:
        return None
    suffix = path.suffix.lower()
    if suffix in _TEXT_EXTENSIONS:
        return _TEXT_EXTENSIONS[suffix]
    mime, _ = mimetypes.guess_type(str(path))
    return mime


def _compute_file_hash(
    artifact: Artifact,
    project_path: Optional[Path],
) -> str:
    """Compute content hash for a file-based artifact.

    For file-based types (config, spec, rule, context) hashing directly
    reads the file bytes rather than using the Merkle-tree algorithm.
    Falls back to the DB ``content_hash`` or ``content`` columns.

    Args:
        artifact: ORM artifact row.
        project_path: Optional project root directory.

    Returns:
        64-character lowercase hex string, or ``""`` on failure.
    """
    fs_path = _resolve_artifact_fs_path(artifact, project_path)
    if fs_path is not None and fs_path.is_file():
        try:
            return _hash_bytes(fs_path.read_bytes())
        except OSError as exc:
            logger.debug(
                "File read failed for %r %r (%s); falling back to DB content.",
                artifact.type,
                artifact.name,
                exc,
            )
    elif fs_path is not None and fs_path.is_dir():
        # If path resolves to a directory fall back to Merkle tree.
        try:
            return compute_artifact_hash(str(fs_path))
        except (FileNotFoundError, ValueError, OSError) as exc:
            logger.debug(
                "Directory hash failed for %r %r (%s); falling back to DB content.",
                artifact.type,
                artifact.name,
                exc,
            )

    if artifact.content_hash:
        logger.debug(
            "Using cached content_hash from DB for %r %r.",
            artifact.type,
            artifact.name,
        )
        return artifact.content_hash

    if artifact.content:
        return _hash_string(artifact.content)

    logger.warning(
        "Cannot compute content hash for %r %r (id=%r): "
        "no filesystem path and no DB content available.",
        artifact.type,
        artifact.name,
        artifact.id,
    )
    return ""


def _file_based_adapt(
    artifact: Artifact,
    project_path: Optional[Path],
) -> Dict[str, Any]:
    """Build a normalised BOM entry for a file-based artifact.

    Shared implementation used by ``ConfigAdapter``, ``SpecAdapter``,
    ``RuleAdapter``, and ``ContextFileAdapter``.  Adds ``mime_type`` to the
    standard metadata block.

    Args:
        artifact: ORM artifact row.
        project_path: Optional project root directory.

    Returns:
        BOM-entry dict with keys: name, type, source, version,
        content_hash, metadata (including mime_type).
    """
    fs_path = _resolve_artifact_fs_path(artifact, project_path)
    meta = _extract_standard_metadata(artifact)
    meta["mime_type"] = _guess_mime_type(fs_path) or _guess_mime_type(
        Path(artifact.name) if artifact.name else None
    )

    return {
        "name": artifact.name,
        "type": artifact.type,
        "source": artifact.source,
        "version": artifact.deployed_version or artifact.upstream_version,
        "content_hash": _compute_file_hash(artifact, project_path),
        "metadata": meta,
    }


class ConfigAdapter(BaseArtifactAdapter):
    """BOM adapter for project configuration file artifacts.

    Config files live under ``.claude/config/``.  Content hashing reads the
    file bytes directly.  A ``mime_type`` field is included in the metadata.
    """

    def get_artifact_type(self) -> str:
        """Return ``"project_config"``."""
        return "project_config"

    def compute_content_hash(
        self,
        artifact: Artifact,
        project_path: Optional[Path] = None,
    ) -> str:
        """Compute content hash for a config file artifact.

        Args:
            artifact: ORM artifact row.
            project_path: Optional project root directory.

        Returns:
            64-character lowercase hex string, or ``""`` on failure.
        """
        return _compute_file_hash(artifact, project_path)

    def adapt(
        self,
        artifact: Artifact,
        project_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Return a normalised BOM entry for a config file artifact.

        Args:
            artifact: ORM artifact row.
            project_path: Optional project root directory.

        Returns:
            BOM-entry dict with keys: name, type, source, version,
            content_hash, metadata (including mime_type).
        """
        return _file_based_adapt(artifact, project_path)


class SpecAdapter(BaseArtifactAdapter):
    """BOM adapter for spec file artifacts.

    Spec files live under ``.claude/specs/``.  Content hashing reads the
    file bytes directly.  A ``mime_type`` field is included in the metadata.
    """

    def get_artifact_type(self) -> str:
        """Return ``"spec_file"``."""
        return "spec_file"

    def compute_content_hash(
        self,
        artifact: Artifact,
        project_path: Optional[Path] = None,
    ) -> str:
        """Compute content hash for a spec file artifact.

        Args:
            artifact: ORM artifact row.
            project_path: Optional project root directory.

        Returns:
            64-character lowercase hex string, or ``""`` on failure.
        """
        return _compute_file_hash(artifact, project_path)

    def adapt(
        self,
        artifact: Artifact,
        project_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Return a normalised BOM entry for a spec file artifact.

        Args:
            artifact: ORM artifact row.
            project_path: Optional project root directory.

        Returns:
            BOM-entry dict with keys: name, type, source, version,
            content_hash, metadata (including mime_type).
        """
        return _file_based_adapt(artifact, project_path)


class RuleAdapter(BaseArtifactAdapter):
    """BOM adapter for rule file artifacts.

    Rule files live under ``.claude/rules/``.  Content hashing reads the
    file bytes directly.  A ``mime_type`` field is included in the metadata.
    """

    def get_artifact_type(self) -> str:
        """Return ``"rule_file"``."""
        return "rule_file"

    def compute_content_hash(
        self,
        artifact: Artifact,
        project_path: Optional[Path] = None,
    ) -> str:
        """Compute content hash for a rule file artifact.

        Args:
            artifact: ORM artifact row.
            project_path: Optional project root directory.

        Returns:
            64-character lowercase hex string, or ``""`` on failure.
        """
        return _compute_file_hash(artifact, project_path)

    def adapt(
        self,
        artifact: Artifact,
        project_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Return a normalised BOM entry for a rule file artifact.

        Args:
            artifact: ORM artifact row.
            project_path: Optional project root directory.

        Returns:
            BOM-entry dict with keys: name, type, source, version,
            content_hash, metadata (including mime_type).
        """
        return _file_based_adapt(artifact, project_path)


class ContextFileAdapter(BaseArtifactAdapter):
    """BOM adapter for context file artifacts.

    Context files live under ``.claude/context/``.  Content hashing reads the
    file bytes directly.  A ``mime_type`` field is included in the metadata.
    """

    def get_artifact_type(self) -> str:
        """Return ``"context_file"``."""
        return "context_file"

    def compute_content_hash(
        self,
        artifact: Artifact,
        project_path: Optional[Path] = None,
    ) -> str:
        """Compute content hash for a context file artifact.

        Args:
            artifact: ORM artifact row.
            project_path: Optional project root directory.

        Returns:
            64-character lowercase hex string, or ``""`` on failure.
        """
        return _compute_file_hash(artifact, project_path)

    def adapt(
        self,
        artifact: Artifact,
        project_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Return a normalised BOM entry for a context file artifact.

        Args:
            artifact: ORM artifact row.
            project_path: Optional project root directory.

        Returns:
            BOM-entry dict with keys: name, type, source, version,
            content_hash, metadata (including mime_type).
        """
        return _file_based_adapt(artifact, project_path)


# ---------------------------------------------------------------------------
# BomGenerator
# ---------------------------------------------------------------------------


class BomGenerator:
    """Core service for generating Software Bills of Materials.

    Queries deployed artifacts from the SQLAlchemy session, resolves the
    appropriate adapter for each artifact type, and assembles a normalised
    BOM dict.

    The resulting BOM dict structure::

        {
            "schema_version":  str,          # e.g. "1.0.0"
            "generated_at":    str,          # ISO-8601 UTC timestamp
            "project_path":    str | None,   # resolved project root, if any
            "artifact_count":  int,
            "artifacts":       List[dict],   # sorted by (type, name)
            "metadata": {
                "generator": "skillmeat-bom",
                "elapsed_ms": float,
            },
        }

    Adapters are registered in a per-instance registry so that callers may
    inject additional adapters without monkey-patching module globals.

    Args:
        session: SQLAlchemy session bound to the local SQLite cache.
        project_path: Optional project root; forwarded to adapters for
                      filesystem path resolution.

    Example::

        from skillmeat.core.bom import BomGenerator

        bom = BomGenerator(session=session, project_path="/path/to/project")
        result = bom.generate()
    """

    def __init__(
        self,
        session: Session,
        project_path: Optional[str | Path] = None,
    ) -> None:
        self._session = session
        self._project_path: Optional[Path] = (
            Path(project_path) if project_path is not None else None
        )
        # Internal adapter registry: type_string -> adapter instance.
        self._adapters: Dict[str, BaseArtifactAdapter] = {}
        self._register_builtin_adapters()

    # ------------------------------------------------------------------
    # Adapter registry
    # ------------------------------------------------------------------

    def _register_builtin_adapters(self) -> None:
        """Register the built-in adapters shipped with this module.

        All standard artifact type adapters are registered here.  The
        ``CompositeAdapter`` receives the session so it can query membership
        rows at generation time.
        """
        self.register_adapter(SkillAdapter())
        # TASK-2.2
        self.register_adapter(CommandAdapter())
        # TASK-2.3
        self.register_adapter(AgentAdapter())
        self.register_adapter(McpAdapter())
        # TASK-2.4
        self.register_adapter(HookAdapter())
        self.register_adapter(WorkflowAdapter())
        self.register_adapter(CompositeAdapter(session=self._session))
        # TASK-2.5
        self.register_adapter(ConfigAdapter())
        self.register_adapter(SpecAdapter())
        self.register_adapter(RuleAdapter())
        self.register_adapter(ContextFileAdapter())

    def register_adapter(self, adapter: BaseArtifactAdapter) -> None:
        """Register (or replace) an adapter for its declared artifact type.

        Args:
            adapter: Adapter instance to register.  The adapter's
                     ``get_artifact_type()`` return value is used as the
                     registry key.
        """
        artifact_type = adapter.get_artifact_type()
        self._adapters[artifact_type] = adapter
        logger.debug("Registered BOM adapter for artifact type %r.", artifact_type)

    def get_adapter(self, artifact_type: str) -> Optional[BaseArtifactAdapter]:
        """Return the adapter for *artifact_type*, or ``None`` if not found.

        Args:
            artifact_type: Artifact type string (e.g. ``"skill"``).

        Returns:
            Registered ``BaseArtifactAdapter`` instance, or ``None``.
        """
        return self._adapters.get(artifact_type)

    # ------------------------------------------------------------------
    # BOM generation
    # ------------------------------------------------------------------

    def _query_artifacts(self) -> List[Artifact]:
        """Query all artifacts from the DB session (SQLAlchemy 1.x style).

        Uses the local-repo ``session.query()`` convention mandated by the
        cache CLAUDE.md invariants.

        Returns:
            List of all ``Artifact`` ORM rows accessible via the session.
        """
        return self._session.query(Artifact).all()

    def generate(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate and return the BOM dict.

        Queries artifacts from the database, adapts each one using the
        registered adapter for its type, and returns the assembled BOM.
        Artifacts whose type has no registered adapter are skipped with a
        warning so that partial BOMs remain useful.

        The artifact list is sorted deterministically by ``(type, name)``
        before being included in the output.

        Args:
            project_id: Optional project identifier to filter artifacts.
                        When ``None`` all artifacts in the session scope are
                        included.

        Returns:
            BOM dict as described in the class docstring.
        """
        start_ts = time.monotonic()
        logger.info(
            "BomGenerator.generate() started (project_id=%r, project_path=%r).",
            project_id,
            self._project_path,
        )

        # Query artifacts — filter by project when an id is provided.
        try:
            query = self._session.query(Artifact)
            if project_id is not None:
                query = query.filter(Artifact.project_id == project_id)
            artifacts: List[Artifact] = query.all()
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to query artifacts from DB: %s", exc)
            raise

        logger.debug("Queried %d artifact(s) from DB.", len(artifacts))

        # Adapt each artifact.
        entries: List[Dict[str, Any]] = []
        skipped_types: List[str] = []

        for artifact in artifacts:
            adapter = self.get_adapter(artifact.type)
            if adapter is None:
                if artifact.type not in skipped_types:
                    logger.warning(
                        "No BOM adapter registered for artifact type %r; "
                        "skipping artifact %r (id=%r).",
                        artifact.type,
                        artifact.name,
                        artifact.id,
                    )
                    skipped_types.append(artifact.type)
                else:
                    logger.debug(
                        "Skipping artifact %r (type=%r): no adapter.",
                        artifact.name,
                        artifact.type,
                    )
                continue

            try:
                entry = adapter.adapt(artifact, self._project_path)
                entries.append(entry)
            except Exception as exc:  # pragma: no cover
                logger.error(
                    "Adapter %r raised an exception for artifact %r (id=%r): %s",
                    adapter.get_artifact_type(),
                    artifact.name,
                    artifact.id,
                    exc,
                    exc_info=True,
                )
                # Skip the artifact rather than crashing the whole BOM.
                continue

        # Sort deterministically: primary key = type, secondary key = name.
        entries.sort(key=lambda e: (e.get("type", ""), e.get("name", "")))

        elapsed_ms = (time.monotonic() - start_ts) * 1000.0
        logger.info(
            "BomGenerator.generate() completed: %d entries in %.1f ms "
            "(%d artifact(s) skipped due to missing adapters).",
            len(entries),
            elapsed_ms,
            len(artifacts) - len(entries),
        )

        return {
            "schema_version": _BOM_SCHEMA_VERSION,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "project_path": str(self._project_path) if self._project_path else None,
            "artifact_count": len(entries),
            "artifacts": entries,
            "metadata": {
                "generator": "skillmeat-bom",
                "elapsed_ms": round(elapsed_ms, 3),
            },
        }
