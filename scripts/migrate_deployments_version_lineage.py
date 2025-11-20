"""Backfill deployment records with version lineage and sync metadata.

This migration updates .claude/.skillmeat-deployed.toml files to ensure:
- content_hash is populated (fallback to collection_sha or recomputed)
- version_lineage exists and includes the current content_hash as the first element
- sync_status defaults to "synced" when absent
- pending_conflicts exists (empty list) to support future conflict tracking
"""

import argparse
from pathlib import Path
from typing import Any, Dict, List

try:
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

import tomli_w

from skillmeat.models import SyncStatus
from skillmeat.utils.filesystem import compute_content_hash


def _ensure_content_hash(entry: Dict[str, Any], project_root: Path) -> str:
    """Derive content hash from entry or recompute from disk."""
    content_hash = entry.get("content_hash") or entry.get("collection_sha")
    if content_hash:
        return content_hash

    artifact_path = entry.get("artifact_path")
    if not artifact_path:
        raise ValueError("Deployment entry missing artifact_path")

    artifact_absolute = project_root / ".claude" / artifact_path
    if not artifact_absolute.exists():
        raise FileNotFoundError(f"Artifact path not found: {artifact_absolute}")

    return compute_content_hash(artifact_absolute)


def _normalize_entry(entry: Dict[str, Any], project_root: Path) -> Dict[str, Any]:
    """Backfill lineage and sync metadata for a single deployment entry."""
    entry = dict(entry)
    content_hash = _ensure_content_hash(entry, project_root)

    lineage: List[str] = entry.get("version_lineage") or []
    if content_hash not in lineage:
        lineage = [content_hash] + lineage

    entry["content_hash"] = content_hash
    entry["collection_sha"] = content_hash  # maintain backward compatibility
    entry["version_lineage"] = lineage

    if "sync_status" not in entry:
        entry["sync_status"] = SyncStatus.SYNCED.value

    entry.setdefault("pending_conflicts", [])
    return entry


def migrate(project_path: Path) -> Path:
    """Run migration for a single project."""
    deployment_file = project_path / ".claude" / ".skillmeat-deployed.toml"
    if not deployment_file.exists():
        raise FileNotFoundError(f"No deployment file found at {deployment_file}")

    with open(deployment_file, "rb") as f:
        data = tomllib.load(f)

    deployed_entries = data.get("deployed", [])
    if not isinstance(deployed_entries, list):
        raise ValueError("Invalid format for deployed entries")

    normalized = [
        _normalize_entry(entry, project_path) for entry in deployed_entries
    ]
    data["deployed"] = normalized

    with open(deployment_file, "wb") as f:
        tomli_w.dump(data, f)

    return deployment_file


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill deployment records with version lineage and sync metadata."
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Path to project root containing .claude/.skillmeat-deployed.toml",
    )
    args = parser.parse_args()

    deployment_file = migrate(args.project.resolve())
    print(f"Updated {deployment_file}")  # noqa: T201


if __name__ == "__main__":
    main()
