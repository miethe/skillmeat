"""Enterprise API-based artifact deploy for SkillMeat.

Downloads artifact files from the enterprise API (``GET
/api/v1/artifacts/{name}/download``) and materialises them under the project's
``.claude/`` directory, then records the deployment in the standard
``.skillmeat-deployed.toml`` tracking file.

Usage::

    from skillmeat.core.enterprise_deploy import EnterpriseDeployer, DeployResult

    result = EnterpriseDeployer().deploy("my-skill", target_dir=Path(".claude"))
    if result.success:
        print(f"Deployed {result.artifact_name} -> {result.target_path}")
"""

from __future__ import annotations

import logging
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w

from skillmeat.core.enterprise_http import enterprise_request
from skillmeat.core.path_resolver import DEFAULT_ARTIFACT_PATH_MAP

logger = logging.getLogger(__name__)

__all__ = [
    "DeployResult",
    "EnterpriseDeployer",
]

# Fallback artifact type subdirectory when the API returns an unknown type.
_DEFAULT_SUBDIR = "skills"


@dataclass
class DeployResult:
    """Result of an enterprise deploy operation."""

    success: bool
    artifact_name: str
    artifact_type: str
    version: str
    files_written: List[str] = field(default_factory=list)
    target_path: Optional[Path] = None
    error: Optional[str] = None


class EnterpriseDeployer:
    """Download and materialise an artifact from the enterprise API.

    The deployer:

    1. Calls ``GET /api/v1/artifacts/{name}/download`` on the configured
       enterprise API server.
    2. Writes each file from the response ``files`` array atomically into
       ``target_dir/<subdir>/<artifact_name>/``.
    3. Appends a deployment record to
       ``target_dir/.skillmeat-deployed.toml`` using the standard format
       understood by :class:`~skillmeat.storage.deployment.DeploymentTracker`.
    """

    def deploy(
        self,
        artifact_name: str,
        target_dir: Path = Path(".claude"),
    ) -> DeployResult:
        """Download an artifact from the enterprise API and materialise it.

        Args:
            artifact_name: Name (or ``type:name`` id) of the artifact to deploy.
            target_dir: Root directory to deploy into (defaults to ``.claude``).

        Returns:
            :class:`DeployResult` describing the outcome.

        Raises:
            requests.HTTPError: When the API returns a non-2xx response.
            EnterpriseConfigError: When PAT or API URL is not configured.
        """
        target_dir = Path(target_dir).resolve()

        # ------------------------------------------------------------------ #
        # 1.  Fetch artifact from enterprise API                               #
        # ------------------------------------------------------------------ #
        try:
            resp = enterprise_request(
                "GET",
                f"/api/v1/artifacts/{artifact_name}/download",
                timeout=30,
            )
            resp.raise_for_status()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "?"
            msg = f"Enterprise API returned HTTP {status} for artifact '{artifact_name}'"
            logger.error(msg)
            return DeployResult(
                success=False,
                artifact_name=artifact_name,
                artifact_type="unknown",
                version="unknown",
                error=msg,
            )

        payload: Dict[str, Any] = resp.json()

        # ------------------------------------------------------------------ #
        # 2.  Parse the API response                                           #
        # ------------------------------------------------------------------ #
        # Expected shape: {artifact_id, files[], metadata{name, type, version}}
        metadata: Dict[str, Any] = payload.get("metadata") or {}
        resolved_name: str = metadata.get("name") or artifact_name
        artifact_type: str = str(metadata.get("type") or "skill").lower()
        version: str = str(metadata.get("version") or "unknown")

        files: List[Dict[str, Any]] = payload.get("files") or []

        # ------------------------------------------------------------------ #
        # 3.  Determine target subdirectory                                    #
        # ------------------------------------------------------------------ #
        subdir = DEFAULT_ARTIFACT_PATH_MAP.get(artifact_type, _DEFAULT_SUBDIR)
        artifact_root = target_dir / subdir / resolved_name
        artifact_root.mkdir(parents=True, exist_ok=True)

        # ------------------------------------------------------------------ #
        # 4.  Write files atomically                                           #
        # ------------------------------------------------------------------ #
        written_paths: List[str] = []

        for file_entry in files:
            rel_path: str = file_entry.get("path") or ""
            content: str = file_entry.get("content") or ""

            if not rel_path:
                logger.warning("Skipping file entry with empty path in API response")
                continue

            dest = artifact_root / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)

            _atomic_write(dest, content)
            relative_to_target = dest.relative_to(target_dir)
            written_paths.append(str(relative_to_target))
            logger.debug("Wrote %s", dest)

        # ------------------------------------------------------------------ #
        # 5.  Update .skillmeat-deployed.toml                                  #
        # ------------------------------------------------------------------ #
        _record_enterprise_deployment(
            target_dir=target_dir,
            artifact_name=resolved_name,
            artifact_type=artifact_type,
            version=version,
            files_written=written_paths,
        )

        return DeployResult(
            success=True,
            artifact_name=resolved_name,
            artifact_type=artifact_type,
            version=version,
            files_written=written_paths,
            target_path=artifact_root,
        )


# --------------------------------------------------------------------------- #
# Internal helpers                                                             #
# --------------------------------------------------------------------------- #


def _atomic_write(dest: Path, content: str) -> None:
    """Write *content* to *dest* atomically via a sibling temp file.

    Uses :func:`tempfile.NamedTemporaryFile` in the same directory as *dest*
    so that the ``os.replace`` call is an atomic rename on POSIX systems.

    Args:
        dest: Final destination path.
        content: Text content to write (UTF-8 encoded).
    """
    parent = dest.parent
    parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=parent,
        prefix=".tmp_sm_",
        delete=False,
        suffix=dest.suffix or ".tmp",
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    tmp_path.replace(dest)


_ENTERPRISE_DEPLOYED_FILE = ".skillmeat-deployed.toml"


def _record_enterprise_deployment(
    target_dir: Path,
    artifact_name: str,
    artifact_type: str,
    version: str,
    files_written: List[str],
) -> None:
    """Append (or update) an enterprise deploy record in ``.skillmeat-deployed.toml``.

    The file lives at ``target_dir/.skillmeat-deployed.toml`` and uses the
    canonical ``[[deployed]]`` array format understood by
    :class:`~skillmeat.storage.deployment.DeploymentTracker`.

    Args:
        target_dir: Root directory (typically ``.claude/``).
        artifact_name: Name of the deployed artifact.
        artifact_type: Artifact type string (e.g. ``"skill"``, ``"command"``).
        version: Version string from the API response.
        files_written: Relative paths of all written files.
    """
    deployed_file = target_dir / _ENTERPRISE_DEPLOYED_FILE
    now_iso = datetime.now(timezone.utc).isoformat()

    # Read existing records
    existing: List[Dict[str, Any]] = []
    if deployed_file.exists():
        try:
            with open(deployed_file, "rb") as fh:
                data = tomllib.load(fh)
            existing = list(data.get("deployed", []))
        except Exception:
            logger.warning(
                "Could not parse %s — starting fresh", deployed_file, exc_info=True
            )

    # Remove stale entry for the same artifact (replace, don't duplicate)
    existing = [
        rec
        for rec in existing
        if not (
            rec.get("artifact_name") == artifact_name
            and rec.get("from_collection") == "enterprise"
        )
    ]

    # Build a record compatible with Deployment.from_dict()
    subdir = DEFAULT_ARTIFACT_PATH_MAP.get(artifact_type, _DEFAULT_SUBDIR)
    artifact_relative_path = f"{subdir}/{artifact_name}"

    new_record: Dict[str, Any] = {
        "artifact_name": artifact_name,
        "artifact_type": artifact_type,
        "from_collection": "enterprise",
        "deployed_at": now_iso,
        "artifact_path": artifact_relative_path,
        # Use version as content_hash placeholder — no FS hash available here
        "content_hash": version,
        "collection_sha": version,
        "local_modifications": False,
        # Enterprise-specific metadata
        "enterprise_version": version,
        "enterprise_files": files_written,
    }

    existing.append(new_record)

    # Write atomically
    tmp_file = deployed_file.with_suffix(".tmp")
    with open(tmp_file, "wb") as fh:
        tomli_w.dump({"deployed": existing}, fh)
    tmp_file.replace(deployed_file)

    logger.debug("Updated %s with enterprise deployment of '%s'", deployed_file, artifact_name)
