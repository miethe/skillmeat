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
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

import requests

from skillmeat.core.enterprise_http import enterprise_request
from skillmeat.core.hashing import _is_excluded  # reuse existing exclusion rules

logger = logging.getLogger(__name__)

__all__ = [
    "ArtifactMigrationResult",
    "ChecksumMismatch",
    "ChecksumValidationResult",
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
class ChecksumMismatch:
    """Details of a single file whose checksums do not agree.

    Attributes:
        path: Relative POSIX path of the file within the artifact.
        local: Client-computed SHA-256 hex digest.
        server: Server-returned SHA-256 hex digest.
    """

    path: str
    local: str
    server: str


@dataclass
class ChecksumValidationResult:
    """Result of comparing client-side and server-side checksums.

    Attributes:
        valid: True when every file's checksum matched.
        mismatches: List of files whose checksums differed (empty on success).
    """

    valid: bool
    mismatches: List[ChecksumMismatch]


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

# HTTP status codes that warrant a retry.
_RETRYABLE_STATUSES: frozenset[int] = frozenset({429, 502, 503, 504})

# HTTP status codes that are definitive client errors — do NOT retry.
_NO_RETRY_STATUSES: frozenset[int] = frozenset({400, 401, 403, 404, 409})

# Maximum number of attempts (first try + 2 retries = 3 total).
_MAX_RETRIES: int = 3

# State file name written inside the collection dir.
_STATE_FILENAME = ".skillmeat-migration-state.toml"

# Error log file name written inside the collection dir on failures.
_ERROR_LOG_FILENAME = "migration-errors.log"

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
# Time helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string (seconds precision)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


# ---------------------------------------------------------------------------
# State file helpers
# ---------------------------------------------------------------------------


def _write_state_file(state_path: Path, data: dict) -> None:
    """Serialise *data* to a minimal TOML file at *state_path*.

    Only scalar values and nested dicts with scalar values are supported —
    enough for the migration state format.

    Args:
        state_path: Destination path for the state file.
        data: Top-level mapping to serialise.
    """
    lines: List[str] = []
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"\n[{key}]")
            for sub_key, sub_val in value.items():
                lines.append(f'{sub_key} = "{sub_val}"')
        else:
            lines.append(f'{key} = "{value}"')
    state_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_state_file(state_path: Path) -> dict:
    """Parse the minimal TOML state file produced by :func:`_write_state_file`.

    Uses stdlib ``tomllib`` (Python 3.11+) or ``tomli`` for older versions.
    Returns an empty dict on any read or parse error.

    Args:
        state_path: Path to the state file.

    Returns:
        Parsed dict, or ``{}`` on failure.
    """
    if not state_path.exists():
        return {}
    try:
        import sys
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib  # type: ignore[no-redef]
        return tomllib.loads(state_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.debug("Could not read migration state file %s: %s", state_path, exc)
        return {}


def _load_completed_artifacts(state_path: Path) -> Set[str]:
    """Return the set of artifact names marked ``done`` in the state file.

    Args:
        state_path: Path to ``.skillmeat-migration-state.toml``.

    Returns:
        Set of artifact name strings (may be empty).
    """
    state = _read_state_file(state_path)
    completed: Set[str] = set()
    for key, value in state.items():
        if isinstance(value, dict) and value.get("status") == "done":
            completed.add(key)
    return completed


def _append_artifact_done(state_path: Path, name: str) -> None:
    """Append a completed-artifact entry to the state file.

    Reads the existing state, adds/updates the artifact entry, and rewrites
    the file atomically (best-effort — write errors are logged but not raised).

    Args:
        state_path: Path to ``.skillmeat-migration-state.toml``.
        name: Artifact name that just completed successfully.
    """
    state = _read_state_file(state_path)
    state[name] = {"status": "done", "completed_at": _now_iso()}
    try:
        _write_state_file(state_path, state)
    except Exception as exc:
        logger.warning("Could not update migration state file: %s", exc)


# ---------------------------------------------------------------------------
# Error log helpers
# ---------------------------------------------------------------------------


def _append_error_log(log_path: Path, name: str, message: str) -> None:
    """Append a single error line to the migration error log.

    Format::

        2026-03-06T12:00:00 ERROR artifact=<name> error=<message>

    Args:
        log_path: Path to ``migration-errors.log``.
        name: Artifact name.
        message: Error description.
    """
    line = f"{_now_iso()} ERROR artifact={name} error={message}\n"
    try:
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(line)
    except Exception as exc:
        logger.warning("Could not write to migration error log %s: %s", log_path, exc)


# ---------------------------------------------------------------------------
# Retry helpers
# ---------------------------------------------------------------------------


def _is_retryable_exception(exc: Exception) -> bool:
    """Return True when *exc* is a transient network error worth retrying."""
    return isinstance(exc, (requests.ConnectionError, requests.Timeout))


def _upload_with_retry(name: str, payload: dict) -> requests.Response:
    """POST *payload* to the upload endpoint with exponential back-off retry.

    Retries up to :data:`_MAX_RETRIES` times (total) on:

    * HTTP 429, 502, 503, 504 responses.
    * ``requests.ConnectionError`` and ``requests.Timeout`` exceptions.

    Client errors (HTTP 400, 401, 403, 404, 409) and any other exception
    types are raised/returned immediately without retrying.

    Back-off formula: ``sleep(2 ** attempt + random.uniform(0, 1))``

    Args:
        name: Artifact name — used for log messages only.
        payload: JSON-serialisable dict to POST.

    Returns:
        The last :class:`requests.Response` received (may still indicate
        failure — callers must check ``response.status_code``).

    Raises:
        requests.RequestException: On a non-retryable network error.
        Exception: On any other unexpected error from ``enterprise_request``.
    """
    last_response: Optional[requests.Response] = None
    last_exc: Optional[Exception] = None

    for attempt in range(_MAX_RETRIES):
        try:
            response = enterprise_request("POST", _UPLOAD_PATH, json=payload)
        except Exception as exc:
            if not _is_retryable_exception(exc):
                raise
            last_exc = exc
            last_response = None
            reason = type(exc).__name__
        else:
            last_exc = None
            last_response = response

            # Immediately return on success or a non-retryable HTTP status.
            if response.status_code in (200, 201):
                return response
            if response.status_code in _NO_RETRY_STATUSES:
                return response
            if response.status_code not in _RETRYABLE_STATUSES:
                return response

            reason = f"HTTP {response.status_code}"

        # More attempts remain — log and sleep with jitter.
        if attempt < _MAX_RETRIES - 1:
            sleep_seconds = 2 ** attempt + random.uniform(0, 1)
            logger.warning(
                "[migration] Retry %d/%d for %s: %s (sleeping %.2fs)",
                attempt + 1,
                _MAX_RETRIES,
                name,
                reason,
                sleep_seconds,
            )
            time.sleep(sleep_seconds)
        else:
            logger.warning(
                "[migration] Retry %d/%d for %s: %s (no more retries)",
                attempt + 1,
                _MAX_RETRIES,
                name,
                reason,
            )

    # All attempts exhausted.
    if last_exc is not None:
        raise last_exc
    assert last_response is not None
    return last_response


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
        resume: bool = False,
    ) -> MigrationResult:
        """Migrate every artifact found under *collection_dir/artifacts/*.

        Iterates all immediate child directories of the ``artifacts/``
        subdirectory.  Each child is treated as a single artifact and passed
        to :meth:`migrate_one`.  Results are aggregated and returned.

        State tracking
        ~~~~~~~~~~~~~~
        A ``.skillmeat-migration-state.toml`` file is maintained in
        *collection_dir* throughout the run.  On completion the top-level
        ``status`` field is set to ``"completed"`` or ``"partial_failure"``.

        If an in-progress state file is found and *resume* is ``True``,
        artifacts already recorded as ``done`` are skipped.  If *resume* is
        ``False``, a warning is logged but the migration proceeds from scratch.

        Error logging
        ~~~~~~~~~~~~~
        Each failed artifact is appended to ``migration-errors.log`` in
        *collection_dir*.  The log path is printed to stdout at the end of
        the run when any failures occurred.

        Args:
            collection_dir: Path to the root of the local SkillMeat collection
                (the directory that contains ``manifest.toml`` and
                ``artifacts/``).
            dry_run: When True, no API calls are made.  The method validates
                and previews what would be uploaded.
            resume: When True and a previous in-progress state file exists,
                skip artifacts already marked as done.

        Returns:
            :class:`MigrationResult` with counts and per-artifact details.
        """
        artifacts_dir = collection_dir / "artifacts"
        state_path = collection_dir / _STATE_FILENAME
        error_log_path = collection_dir / _ERROR_LOG_FILENAME

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

        # --- Handle existing in-progress state --------------------------------
        already_done: Set[str] = set()
        existing_state = _read_state_file(state_path)
        if existing_state.get("status") == "in_progress":
            if resume:
                already_done = _load_completed_artifacts(state_path)
                logger.info(
                    "Resuming migration — %d artifact(s) already completed.",
                    len(already_done),
                )
            else:
                logger.warning(
                    "Found an in-progress migration state at %s. "
                    "Pass resume=True to skip already-completed artifacts. "
                    "Proceeding from scratch.",
                    state_path,
                )

        # --- Write initial state file -----------------------------------------
        if not dry_run:
            initial_state: dict = {
                "started_at": _now_iso(),
                "total_artifacts": str(len(artifact_dirs)),
                "status": "in_progress",
            }
            # Preserve already-done entries when resuming.
            for key, value in existing_state.items():
                if isinstance(value, dict) and value.get("status") == "done":
                    initial_state[key] = value
            try:
                _write_state_file(state_path, initial_state)
            except Exception as exc:
                logger.warning("Could not write migration state file: %s", exc)

        logger.info(
            "Starting migration of %d artifact(s) from %s (dry_run=%s, resume=%s)",
            len(artifact_dirs),
            artifacts_dir,
            dry_run,
            resume,
        )

        total = len(artifact_dirs)
        succeeded = 0
        failed = 0
        skipped = 0
        errors: List[str] = []
        results: List[ArtifactMigrationResult] = []

        for artifact_path in artifact_dirs:
            artifact_name = artifact_path.name

            # Skip artifacts that completed in a previous run (resume mode).
            if artifact_name in already_done:
                skipped += 1
                logger.debug("Skipping already-completed artifact: %s", artifact_name)
                results.append(
                    ArtifactMigrationResult(
                        name=artifact_name,
                        success=True,
                        dry_run=dry_run,
                        files_count=0,
                        total_bytes=0,
                    )
                )
                continue

            result = self.migrate_one(artifact_path, dry_run=dry_run)
            results.append(result)

            if result.files_count == 0 and not result.error:
                skipped += 1
                logger.debug("Skipped empty artifact directory: %s", artifact_name)
            elif result.success:
                succeeded += 1
                if not dry_run:
                    _append_artifact_done(state_path, artifact_name)
            else:
                failed += 1
                error_msg = f"{artifact_name}: {result.error}"
                errors.append(error_msg)
                logger.error(
                    "Failed to migrate artifact %s: %s", artifact_name, result.error
                )
                if not dry_run:
                    _append_error_log(
                        error_log_path, artifact_name, result.error or "unknown error"
                    )

        # --- Update final state -----------------------------------------------
        final_status = "completed" if failed == 0 else "partial_failure"
        if not dry_run:
            final_state = _read_state_file(state_path)
            final_state["status"] = final_status
            try:
                _write_state_file(state_path, final_state)
            except Exception as exc:
                logger.warning("Could not update final migration state: %s", exc)

        logger.info(
            "Migration complete — total=%d succeeded=%d failed=%d skipped=%d",
            total,
            succeeded,
            failed,
            skipped,
        )

        if failed > 0 and not dry_run:
            print(f"Migration errors written to: {error_log_path}")

        return MigrationResult(
            total=total,
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
            errors=errors,
            results=results,
        )

    def validate_checksums(
        self,
        local_checksums: Dict[str, str],
        server_response: Dict,
    ) -> ChecksumValidationResult:
        """Compare client-side SHA-256 digests against server-returned values.

        The server is expected to return a response body of the form::

            {"files": [{"path": "relative/path", "content_hash": "<sha256>"}, ...]}

        Any file present in *local_checksums* but absent from the server
        response is treated as a mismatch with an empty server hash
        (``""``), and vice-versa: any file the server reports that is not in
        *local_checksums* is also flagged.

        Args:
            local_checksums: Mapping of ``relative_posix_path → sha256_hex``
                computed before the upload.
            server_response: Parsed JSON body returned by the upload endpoint.

        Returns:
            :class:`ChecksumValidationResult` — ``valid`` is True only when
            every path agrees on both sides.
        """
        server_files: List[Dict] = server_response.get("files", [])
        server_map: Dict[str, str] = {
            entry["path"]: entry.get("content_hash", "")
            for entry in server_files
            if "path" in entry
        }

        mismatches: List[ChecksumMismatch] = []

        # Check every local file against the server map.
        for rel_path, local_hash in sorted(local_checksums.items()):
            server_hash = server_map.get(rel_path, "")
            if local_hash != server_hash:
                mismatches.append(
                    ChecksumMismatch(
                        path=rel_path,
                        local=local_hash,
                        server=server_hash,
                    )
                )

        # Flag any extra files the server reported that we did not send.
        for rel_path, server_hash in sorted(server_map.items()):
            if rel_path not in local_checksums:
                mismatches.append(
                    ChecksumMismatch(
                        path=rel_path,
                        local="",
                        server=server_hash,
                    )
                )

        return ChecksumValidationResult(
            valid=len(mismatches) == 0,
            mismatches=mismatches,
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

        # --- Upload to enterprise API (with retry) ---------------------------
        try:
            response: requests.Response = _upload_with_retry(name, payload)
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

            # --- Post-upload checksum validation -----------------------------
            # Build a local checksum map from the file entries we uploaded.
            local_checksums: Dict[str, str] = {
                entry["path"]: entry["content_hash"] for entry in file_entries
            }

            try:
                server_body = response.json()
            except Exception:
                server_body = {}

            validation = self.validate_checksums(local_checksums, server_body)
            if not validation.valid:
                mismatch_details = "; ".join(
                    f"{m.path}: local={m.local} server={m.server}"
                    for m in validation.mismatches
                )
                for mismatch in validation.mismatches:
                    logger.error(
                        "File %s: local SHA256=%s, server SHA256=%s",
                        mismatch.path,
                        mismatch.local,
                        mismatch.server,
                    )
                error_msg = (
                    f"Checksum mismatch: {mismatch_details}"
                    if len(validation.mismatches) == 1
                    else (
                        f"Checksum mismatch for {len(validation.mismatches)} file(s): "
                        + mismatch_details
                    )
                )
                logger.warning(
                    "Checksum validation failed for artifact '%s': %s",
                    name,
                    error_msg,
                )
                return ArtifactMigrationResult(
                    name=name,
                    success=False,
                    dry_run=False,
                    files_count=len(file_entries),
                    total_bytes=total_bytes,
                    error=error_msg,
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
