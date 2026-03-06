"""Enterprise migration service for uploading local artifacts to the enterprise API.

Reads artifacts from the local filesystem collection and uploads them to the
enterprise API endpoint.  Each artifact's files are read, checksummed with
SHA-256, and bundled into a structured upload payload.  One failed artifact
never aborts the whole migration — failures are collected and reported at the
end.

Usage::

    from pathlib import Path
    from skillmeat.core.enterprise_migration import EnterpriseMigrationService

    svc = EnterpriseMigrationService()
    result = svc.migrate_all(Path("~/.skillmeat/collection").expanduser())
    print(f"Migrated {result.succeeded}/{result.total} artifacts")
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import requests

from skillmeat.core.enterprise_http import enterprise_request
from skillmeat.core.hashing import _is_excluded  # reuse existing exclusion rules

logger = logging.getLogger(__name__)

__all__ = [
    "ArtifactMigrationResult",
    "MigrationResult",
    "EnterpriseMigrationService",
]

# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ArtifactMigrationResult:
    """Outcome of migrating a single artifact.

    Attributes:
        name: Artifact name (directory name under ``artifacts/``).
        success: True when the upload was accepted (status 200 or 201).
        dry_run: True when the migration was a dry-run (no API call made).
        files_count: Number of files included in the upload payload.
        total_bytes: Total raw byte size of all included files.
        error: Human-readable error message when ``success`` is False.
    """

    name: str
    success: bool
    dry_run: bool
    files_count: int
    total_bytes: int
    error: Optional[str] = None


@dataclass
class MigrationResult:
    """Aggregated outcome of a full collection migration.

    Attributes:
        total: Total number of artifact directories processed.
        succeeded: Number that uploaded successfully (or validated in dry-run).
        failed: Number that encountered an error.
        skipped: Number that were intentionally skipped (e.g. empty dirs).
        errors: Short error strings, one per failed artifact.
        results: Per-artifact detailed results.
    """

    total: int
    succeeded: int
    failed: int
    skipped: int
    errors: List[str]
    results: List[ArtifactMigrationResult]


# ---------------------------------------------------------------------------
# Upload endpoint
# ---------------------------------------------------------------------------

_UPLOAD_PATH = "/api/v1/artifacts/upload"

# Known text file extensions — everything else gets base64-encoded.
_TEXT_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".md",
        ".txt",
        ".py",
        ".yaml",
        ".yml",
        ".toml",
        ".json",
        ".sh",
        ".bash",
        ".zsh",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".css",
        ".html",
        ".xml",
        ".rst",
        ".cfg",
        ".ini",
        ".env",
        ".gitignore",
    }
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest of *path*'s raw bytes.

    Args:
        path: Absolute path to a regular file.

    Returns:
        64-character lowercase hex string.
    """
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65_536), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_file_entry(root: Path, file_path: Path) -> Dict:
    """Build the upload payload entry for a single file.

    Text files (determined by extension) are included as UTF-8 strings.
    All other files are base64-encoded so that the JSON payload stays valid.

    Args:
        root: Artifact root directory (used to compute the relative path).
        file_path: Absolute path to the file.

    Returns:
        Dict with keys ``path``, ``content``, ``content_hash``, and
        ``encoding`` (``"utf-8"`` or ``"base64"``).
    """
    rel = file_path.relative_to(root).as_posix()
    raw = file_path.read_bytes()
    content_hash = hashlib.sha256(raw).hexdigest()

    suffix = file_path.suffix.lower()
    if suffix in _TEXT_EXTENSIONS:
        try:
            content = raw.decode("utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            # Fallback: treat as binary even though extension looks textual.
            content = base64.b64encode(raw).decode("ascii")
            encoding = "base64"
    else:
        content = base64.b64encode(raw).decode("ascii")
        encoding = "base64"

    return {
        "path": rel,
        "content": content,
        "content_hash": content_hash,
        "encoding": encoding,
    }


def _collect_artifact_files(artifact_path: Path) -> List[Dict]:
    """Walk *artifact_path* and return one payload entry per included file.

    Excluded files (determined by :func:`skillmeat.core.hashing._is_excluded`)
    are silently skipped.  Sub-directory structure is preserved via relative
    POSIX paths.

    Args:
        artifact_path: Root directory of the artifact.

    Returns:
        Sorted list of file entry dicts (sorted by relative path for
        determinism).
    """
    entries: List[Dict] = []

    for dirpath, dirnames, filenames in os.walk(artifact_path, followlinks=True):
        # Prune excluded directories in-place.
        dirnames[:] = sorted(d for d in dirnames if not _is_excluded(d))

        for filename in sorted(filenames):
            if _is_excluded(filename):
                continue

            full_path = Path(dirpath) / filename
            try:
                if not full_path.is_file():
                    continue
                entry = _read_file_entry(artifact_path, full_path)
                entries.append(entry)
            except (OSError, PermissionError) as exc:
                logger.warning(
                    "Skipping unreadable file %s: %s",
                    full_path,
                    exc,
                )

    # Sort deterministically by relative path.
    entries.sort(key=lambda e: e["path"])
    return entries


def _infer_artifact_type(artifact_path: Path) -> str:
    """Guess the artifact type from well-known marker files.

    Falls back to ``"unknown"`` when no marker is found.

    Args:
        artifact_path: Root directory of the artifact.

    Returns:
        Lowercase artifact type string (``"skill"``, ``"agent"``, etc.).
    """
    markers: Dict[str, str] = {
        "SKILL.md": "skill",
        "AGENT.md": "agent",
        "COMMAND.md": "command",
        "MCP.md": "mcp",
        "HOOK.md": "hook",
    }
    for filename, artifact_type in markers.items():
        if (artifact_path / filename).exists():
            return artifact_type
    return "unknown"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class EnterpriseMigrationService:
    """Migrates local collection artifacts to the enterprise API.

    The service is intentionally stateless — create one instance and reuse it
    across multiple calls, or create a fresh instance per invocation.

    Example::

        svc = EnterpriseMigrationService()
        result = svc.migrate_all(collection_dir, dry_run=False)
    """

    def migrate_all(
        self,
        collection_dir: Path,
        dry_run: bool = False,
    ) -> MigrationResult:
        """Migrate every artifact found under *collection_dir/artifacts/*.

        Iterates all immediate child directories of the ``artifacts/``
        subdirectory.  Each child is treated as a single artifact and passed
        to :meth:`migrate_one`.  Results are aggregated and returned.

        Args:
            collection_dir: Path to the root of the local SkillMeat collection
                (the directory that contains ``manifest.toml`` and
                ``artifacts/``).
            dry_run: When True, no API calls are made.  The method validates
                and previews what would be uploaded.

        Returns:
            :class:`MigrationResult` with counts and per-artifact details.
        """
        artifacts_dir = collection_dir / "artifacts"

        if not artifacts_dir.is_dir():
            logger.warning(
                "Artifacts directory not found: %s — nothing to migrate.",
                artifacts_dir,
            )
            return MigrationResult(
                total=0,
                succeeded=0,
                failed=0,
                skipped=0,
                errors=[],
                results=[],
            )

        artifact_dirs = sorted(
            p for p in artifacts_dir.iterdir() if p.is_dir()
        )

        logger.info(
            "Starting migration of %d artifact(s) from %s (dry_run=%s)",
            len(artifact_dirs),
            artifacts_dir,
            dry_run,
        )

        total = len(artifact_dirs)
        succeeded = 0
        failed = 0
        skipped = 0
        errors: List[str] = []
        results: List[ArtifactMigrationResult] = []

        for artifact_path in artifact_dirs:
            result = self.migrate_one(artifact_path, dry_run=dry_run)
            results.append(result)

            if result.files_count == 0 and not result.error:
                skipped += 1
                logger.debug("Skipped empty artifact directory: %s", artifact_path.name)
            elif result.success:
                succeeded += 1
            else:
                failed += 1
                error_msg = f"{artifact_path.name}: {result.error}"
                errors.append(error_msg)
                logger.error("Failed to migrate artifact %s: %s", artifact_path.name, result.error)

        logger.info(
            "Migration complete — total=%d succeeded=%d failed=%d skipped=%d",
            total,
            succeeded,
            failed,
            skipped,
        )

        return MigrationResult(
            total=total,
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
            errors=errors,
            results=results,
        )

    def migrate_one(
        self,
        artifact_path: Path,
        dry_run: bool = False,
    ) -> ArtifactMigrationResult:
        """Migrate a single artifact directory to the enterprise API.

        Reads all files in *artifact_path*, computes SHA-256 checksums,
        builds the upload payload, and POSTs it to
        ``POST /api/v1/artifacts/upload``.

        When *dry_run* is True the payload is built and validated locally but
        no HTTP request is made.

        Args:
            artifact_path: Absolute path to the artifact's root directory.
            dry_run: When True, skip the API call and return a preview result.

        Returns:
            :class:`ArtifactMigrationResult` describing the outcome.
        """
        name = artifact_path.name
        logger.debug("Processing artifact: %s", name)

        # --- Collect files ---------------------------------------------------
        try:
            file_entries = _collect_artifact_files(artifact_path)
        except Exception as exc:
            return ArtifactMigrationResult(
                name=name,
                success=False,
                dry_run=dry_run,
                files_count=0,
                total_bytes=0,
                error=f"Failed to read artifact files: {exc}",
            )

        if not file_entries:
            logger.debug("Artifact %s has no files — skipping.", name)
            return ArtifactMigrationResult(
                name=name,
                success=True,
                dry_run=dry_run,
                files_count=0,
                total_bytes=0,
            )

        # --- Compute aggregate stats -----------------------------------------
        total_bytes = sum(
            len(e["content"].encode("utf-8")) if e["encoding"] == "utf-8"
            else len(base64.b64decode(e["content"]))
            for e in file_entries
        )

        # --- Infer artifact type and collect metadata ------------------------
        artifact_type = _infer_artifact_type(artifact_path)

        metadata: Dict = {}
        # Attempt to pull basic metadata from TOML manifest if present.
        manifest_path = artifact_path / "manifest.toml"
        if manifest_path.exists():
            try:
                import sys
                if sys.version_info >= (3, 11):
                    import tomllib
                else:
                    import tomli as tomllib  # type: ignore[no-redef]

                manifest_data = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
                metadata = manifest_data.get("tool", {}).get("skillmeat", manifest_data)
            except Exception as exc:
                logger.debug(
                    "Could not parse manifest.toml for %s: %s", name, exc
                )

        # --- Build upload payload --------------------------------------------
        payload = {
            "name": name,
            "type": artifact_type,
            "files": file_entries,
            "metadata": metadata,
        }

        # --- Dry-run: return preview without uploading -----------------------
        if dry_run:
            logger.info(
                "[dry-run] Would upload artifact '%s' (%s, %d file(s), %d bytes)",
                name,
                artifact_type,
                len(file_entries),
                total_bytes,
            )
            return ArtifactMigrationResult(
                name=name,
                success=True,
                dry_run=True,
                files_count=len(file_entries),
                total_bytes=total_bytes,
            )

        # --- Upload to enterprise API ----------------------------------------
        try:
            response: requests.Response = enterprise_request(
                "POST",
                _UPLOAD_PATH,
                json=payload,
            )
        except Exception as exc:
            return ArtifactMigrationResult(
                name=name,
                success=False,
                dry_run=False,
                files_count=len(file_entries),
                total_bytes=total_bytes,
                error=f"Network error during upload: {exc}",
            )

        if response.status_code in (200, 201):
            logger.info(
                "Uploaded artifact '%s' (%d file(s), %d bytes) — status %d",
                name,
                len(file_entries),
                total_bytes,
                response.status_code,
            )
            return ArtifactMigrationResult(
                name=name,
                success=True,
                dry_run=False,
                files_count=len(file_entries),
                total_bytes=total_bytes,
            )
        else:
            error_detail = _extract_error_detail(response)
            logger.warning(
                "Upload of artifact '%s' rejected — status %d: %s",
                name,
                response.status_code,
                error_detail,
            )
            return ArtifactMigrationResult(
                name=name,
                success=False,
                dry_run=False,
                files_count=len(file_entries),
                total_bytes=total_bytes,
                error=f"HTTP {response.status_code}: {error_detail}",
            )


# ---------------------------------------------------------------------------
# Internal utilities
# ---------------------------------------------------------------------------


def _extract_error_detail(response: requests.Response) -> str:
    """Extract a human-readable error string from an API error response.

    Tries to parse JSON ``{"detail": "..."}`` first, then falls back to the
    raw response text (truncated to 200 characters).

    Args:
        response: The failed HTTP response.

    Returns:
        A short error string suitable for logging and ``ArtifactMigrationResult.error``.
    """
    try:
        body = response.json()
        if isinstance(body, dict):
            return str(body.get("detail") or body.get("message") or body)
        return str(body)
    except Exception:
        text = response.text or ""
        return text[:200] if text else f"<empty body>"
