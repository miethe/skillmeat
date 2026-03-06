"""Enterprise API-based sync for SkillMeat.

Polls the enterprise API for the latest artifact content hash and applies
file changes when the hash differs from the locally recorded value.

Usage::

    from skillmeat.core.enterprise_sync import EnterpriseSyncer

    syncer = EnterpriseSyncer()

    # Check only (no file writes):
    result = syncer.check("my-skill")

    # Full sync (writes files if hash changed):
    result = syncer.sync("my-skill", target_dir=Path(".claude"))
"""

from __future__ import annotations

import base64
import logging
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w

from skillmeat.core.enterprise_http import enterprise_request

__all__ = [
    "EnterpriseSyncResult",
    "EnterpriseSyncer",
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

_ENTERPRISE_SYNC_FILE = ".skillmeat-enterprise-sync.toml"


@dataclass
class EnterpriseSyncResult:
    """Result of an enterprise sync operation.

    Attributes:
        artifact_name: Name of the artifact that was checked/synced.
        up_to_date: True when the local hash already matches the remote hash.
        updated: True when files were actually written to disk.
        files_updated: Number of files written (0 when ``up_to_date`` is True).
        new_hash: Content hash from the API response (empty string if unknown).
        old_hash: Content hash recorded locally before the sync (empty string
            if no prior sync record exists).
        error: Human-readable error message when the operation failed.
    """

    artifact_name: str
    up_to_date: bool = False
    updated: bool = False
    files_updated: int = 0
    new_hash: str = ""
    old_hash: str = ""
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Internal TOML helpers (self-contained — no import from enterprise_deploy.py
# to avoid cross-module dependency until a later consolidation refactor)
# ---------------------------------------------------------------------------


def _sync_toml_path(target_dir: Path) -> Path:
    """Return path to the enterprise sync-state TOML inside *target_dir*."""
    return target_dir / _ENTERPRISE_SYNC_FILE


def _read_sync_state(target_dir: Path) -> Dict[str, Any]:
    """Read the enterprise sync state from *target_dir*.

    Returns an empty dict when the file does not exist or cannot be parsed.
    The top-level structure is::

        [artifacts.my-skill]
        content_hash = "abc123..."
        synced_at = "2026-01-01T00:00:00+00:00"
    """
    path = _sync_toml_path(target_dir)
    if not path.exists():
        return {}
    try:
        with open(path, "rb") as fh:
            return tomllib.load(fh)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not read enterprise sync state from %s: %s", path, exc)
        return {}


def _write_sync_state(target_dir: Path, state: Dict[str, Any]) -> None:
    """Atomically write *state* to the enterprise sync state TOML file."""
    path = _sync_toml_path(target_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = tomli_w.dumps(state)
    # Atomic write: temp file in same directory then rename.
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=path.parent,
            prefix=".tmp-enterprise-sync-",
            suffix=".toml",
            delete=False,
            encoding="utf-8",
        ) as tmp_fh:
            tmp = Path(tmp_fh.name)
            tmp_fh.write(content)
        tmp.replace(path)
    except Exception:
        if tmp is not None and tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise


def _get_stored_hash(target_dir: Path, artifact_name: str) -> str:
    """Return the locally stored content hash for *artifact_name*, or ``""``."""
    state = _read_sync_state(target_dir)
    artifacts = state.get("artifacts", {})
    return artifacts.get(artifact_name, {}).get("content_hash", "")


def _update_stored_hash(
    target_dir: Path, artifact_name: str, new_hash: str
) -> None:
    """Persist *new_hash* for *artifact_name* in the enterprise sync state."""
    state = _read_sync_state(target_dir)
    artifacts = state.setdefault("artifacts", {})
    artifacts[artifact_name] = {
        "content_hash": new_hash,
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_sync_state(target_dir, state)


# ---------------------------------------------------------------------------
# File materialisation helpers
# ---------------------------------------------------------------------------


def _materialize_files(
    files: List[Dict[str, Any]],
    target_dir: Path,
    artifact_name: str,
) -> int:
    """Write *files* from an API payload into *target_dir*.

    Each entry in *files* is a ``FileEntry`` dict as produced by the
    enterprise content service::

        {
            "path": "relative/posix/path",
            "content": "<utf-8 text or base64 string>",
            "size": <int>,
            "encoding": "utf-8" | "base64",
        }

    Files are written atomically (temp file + rename) to avoid partial writes.
    The ``path`` is treated as relative to *target_dir*.

    Args:
        files: List of file-entry dicts from the API payload.
        target_dir: Root directory into which files will be written.
        artifact_name: Used only for log messages.

    Returns:
        Number of files successfully written.
    """
    written = 0
    for entry in files:
        rel_path: str = entry.get("path", "")
        if not rel_path:
            logger.warning(
                "enterprise_sync: skipping file entry with empty path for %s",
                artifact_name,
            )
            continue

        dest = target_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)

        encoding = entry.get("encoding", "utf-8")
        raw_content = entry.get("content", "")

        # Decode content.
        if encoding == "base64":
            file_bytes = base64.b64decode(raw_content)
        else:
            file_bytes = raw_content.encode("utf-8")

        # Atomic write: temp file in same directory then rename.
        tmp = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=dest.parent,
                prefix=".tmp-ent-sync-",
                delete=False,
            ) as tmp_fh:
                tmp = Path(tmp_fh.name)
                tmp_fh.write(file_bytes)
            tmp.replace(dest)
            written += 1
            logger.debug(
                "enterprise_sync: wrote %s for %s (%d bytes)",
                rel_path,
                artifact_name,
                len(file_bytes),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "enterprise_sync: failed to write %s for %s: %s",
                rel_path,
                artifact_name,
                exc,
            )
            if tmp is not None and tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass

    return written


# ---------------------------------------------------------------------------
# Main syncer
# ---------------------------------------------------------------------------


class EnterpriseSyncer:
    """Poll the enterprise API for artifact updates and apply changes locally.

    This syncer is bandwidth-efficient: it fetches the full payload from the
    download endpoint and compares the returned ``content_hash`` against the
    locally stored value.  Files are only written when the hashes differ.

    The sync state (hash + timestamp per artifact) is persisted in
    ``<target_dir>/.skillmeat-enterprise-sync.toml``.
    """

    # Default target directory (the .claude directory in the current project).
    DEFAULT_TARGET_DIR: Path = Path(".claude")

    def check(
        self,
        artifact_name: str,
        target_dir: Optional[Path] = None,
    ) -> EnterpriseSyncResult:
        """Check whether the local artifact is up-to-date with the API.

        Calls the download endpoint and compares the returned
        ``content_hash`` with the locally stored hash.  **No files are
        written.**

        Args:
            artifact_name: Artifact name or ID to check.
            target_dir: Directory containing the enterprise sync state file.
                Defaults to :attr:`DEFAULT_TARGET_DIR`.

        Returns:
            :class:`EnterpriseSyncResult` with ``updated=False`` always.
        """
        if target_dir is None:
            target_dir = self.DEFAULT_TARGET_DIR

        target_dir = Path(target_dir)
        old_hash = _get_stored_hash(target_dir, artifact_name)

        logger.debug(
            "enterprise_sync.check: artifact=%s target_dir=%s stored_hash=%s",
            artifact_name,
            target_dir,
            old_hash or "<none>",
        )

        try:
            payload = self._fetch_payload(artifact_name)
        except Exception as exc:  # noqa: BLE001
            return EnterpriseSyncResult(
                artifact_name=artifact_name,
                old_hash=old_hash,
                error=str(exc),
            )

        new_hash = payload.get("content_hash", "")
        up_to_date = bool(old_hash) and old_hash == new_hash

        return EnterpriseSyncResult(
            artifact_name=artifact_name,
            up_to_date=up_to_date,
            updated=False,
            files_updated=0,
            new_hash=new_hash,
            old_hash=old_hash,
        )

    def sync(
        self,
        artifact_name: str,
        target_dir: Optional[Path] = None,
    ) -> EnterpriseSyncResult:
        """Sync a local artifact with the enterprise API.

        Fetches the full payload from
        ``GET /api/v1/artifacts/{artifact_name}/download``, compares the
        ``content_hash`` with the locally stored value, and re-materialises
        files when the hashes differ.  If the hashes match no files are
        written (bandwidth efficient).

        After a successful update the new hash and timestamp are persisted in
        ``<target_dir>/.skillmeat-enterprise-sync.toml``.

        Args:
            artifact_name: Artifact name or ID to sync.
            target_dir: Directory into which artifact files are written and
                where the sync state file is stored.  Defaults to
                :attr:`DEFAULT_TARGET_DIR`.

        Returns:
            :class:`EnterpriseSyncResult` describing what happened.
        """
        if target_dir is None:
            target_dir = self.DEFAULT_TARGET_DIR

        target_dir = Path(target_dir)
        old_hash = _get_stored_hash(target_dir, artifact_name)

        logger.debug(
            "enterprise_sync.sync: artifact=%s target_dir=%s stored_hash=%s",
            artifact_name,
            target_dir,
            old_hash or "<none>",
        )

        # Fetch payload from the API.
        try:
            payload = self._fetch_payload(artifact_name)
        except Exception as exc:  # noqa: BLE001
            return EnterpriseSyncResult(
                artifact_name=artifact_name,
                old_hash=old_hash,
                error=str(exc),
            )

        new_hash = payload.get("content_hash", "")

        # No change — skip file writes.
        if old_hash and old_hash == new_hash:
            logger.debug(
                "enterprise_sync.sync: %s is up-to-date (hash=%s)",
                artifact_name,
                new_hash,
            )
            return EnterpriseSyncResult(
                artifact_name=artifact_name,
                up_to_date=True,
                updated=False,
                files_updated=0,
                new_hash=new_hash,
                old_hash=old_hash,
            )

        # Hash differs (or no prior record) — materialise files.
        files: List[Dict[str, Any]] = payload.get("files", [])
        files_written = _materialize_files(files, target_dir, artifact_name)

        # Persist the new hash regardless of how many files were written so
        # that a subsequent check reflects the current API state.
        try:
            _update_stored_hash(target_dir, artifact_name, new_hash)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "enterprise_sync.sync: failed to persist hash for %s: %s",
                artifact_name,
                exc,
            )
            # Non-fatal — files were written; return a partial success.
            return EnterpriseSyncResult(
                artifact_name=artifact_name,
                up_to_date=False,
                updated=True,
                files_updated=files_written,
                new_hash=new_hash,
                old_hash=old_hash,
                error=f"Files written but hash persistence failed: {exc}",
            )

        logger.info(
            "enterprise_sync.sync: updated %s — %d file(s) written"
            " (old_hash=%s new_hash=%s)",
            artifact_name,
            files_written,
            old_hash or "<none>",
            new_hash,
        )

        return EnterpriseSyncResult(
            artifact_name=artifact_name,
            up_to_date=False,
            updated=True,
            files_updated=files_written,
            new_hash=new_hash,
            old_hash=old_hash,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fetch_payload(artifact_name: str) -> Dict[str, Any]:
        """Call the enterprise download endpoint and return the JSON payload.

        Args:
            artifact_name: Artifact name or ID to fetch.

        Returns:
            Parsed JSON dict from the API response.

        Raises:
            requests.HTTPError: When the API returns a non-2xx status.
            requests.RequestException: For network-level failures.
            skillmeat.core.enterprise_config.EnterpriseConfigError: When
                ``SKILLMEAT_API_URL`` or the PAT is not configured.
        """
        path = f"/api/v1/artifacts/{artifact_name}/download"
        logger.debug("enterprise_sync: GET %s", path)
        resp = enterprise_request("GET", path, timeout=30)
        resp.raise_for_status()
        return resp.json()
