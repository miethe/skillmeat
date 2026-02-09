#!/usr/bin/env python3
"""Migrate legacy deployments to profile-aware metadata.

This script performs two migrations for multi-platform deployments:
1. Ensures legacy projects have a default ``claude_code`` deployment profile.
2. Backfills legacy ``.skillmeat-deployed.toml`` records with:
   - ``deployment_profile_id``
   - ``platform``
   - ``profile_root_dir``

Usage:
    python scripts/migrate_to_deployment_profiles.py
    python scripts/migrate_to_deployment_profiles.py --dry-run --verbose
    python scripts/migrate_to_deployment_profiles.py --db-path /path/to/cache.db
"""

from __future__ import annotations

import argparse
import logging
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w
from sqlalchemy.orm import sessionmaker

from skillmeat.api.routers.projects import discover_projects
from skillmeat.cache.models import Project, create_db_engine, create_tables
from skillmeat.cache.repositories import DeploymentProfileRepository
from skillmeat.core.enums import Platform
from skillmeat.core.path_resolver import (
    DEFAULT_ARTIFACT_PATH_MAP,
    DEFAULT_PROFILE_ROOT_DIR,
    DEFAULT_PROJECT_CONFIG_FILENAMES_BY_PLATFORM,
)
from skillmeat.storage.deployment import DeploymentTracker

logger = logging.getLogger("migrate_to_deployment_profiles")

PROFILE_TO_ROOT = {
    "claude_code": ".claude",
    "codex": ".codex",
    "gemini": ".gemini",
    "cursor": ".cursor",
}
ROOT_TO_PROFILE = {v: k for k, v in PROFILE_TO_ROOT.items()}


@dataclass
class MigrationStats:
    projects_scanned: int = 0
    projects_migrated: int = 0
    profiles_created: int = 0
    records_backfilled: int = 0
    records_already_populated: int = 0
    projects_failed: int = 0


def _infer_profile_from_root(root_dir: str) -> str:
    normalized = root_dir.strip()
    if not normalized:
        return "claude_code"
    if normalized in ROOT_TO_PROFILE:
        return ROOT_TO_PROFILE[normalized]
    return normalized.lstrip(".") or "claude_code"


def _infer_root_from_artifact_path(artifact_path: str) -> Optional[str]:
    normalized = artifact_path.strip()
    if not normalized:
        return None
    for root in PROFILE_TO_ROOT.values():
        prefix = f"{root}/"
        if normalized.startswith(prefix):
            return root
    return None


def _infer_platform(profile_id: str) -> str:
    try:
        return Platform(profile_id).value
    except ValueError:
        return Platform.OTHER.value


def infer_record_profile_metadata(
    record: Dict[str, object],
    fallback_root_dir: str,
) -> Dict[str, str]:
    """Infer profile metadata for a deployment record.

    Existing fields are preserved if present.
    """
    artifact_path = str(record.get("artifact_path") or "")

    existing_root = str(record.get("profile_root_dir") or "").strip()
    inferred_from_path = _infer_root_from_artifact_path(artifact_path)
    root_dir = existing_root or inferred_from_path or fallback_root_dir

    existing_profile = str(record.get("deployment_profile_id") or "").strip()
    inferred_profile = _infer_profile_from_root(root_dir)
    profile_id = existing_profile or inferred_profile

    existing_platform = str(record.get("platform") or "").strip()
    platform = existing_platform or _infer_platform(profile_id)

    return {
        "deployment_profile_id": profile_id,
        "platform": platform,
        "profile_root_dir": root_dir,
    }


def _find_deployment_files(project_path: Path) -> List[Path]:
    files: List[Path] = []

    default_file = project_path / DEFAULT_PROFILE_ROOT_DIR / DeploymentTracker.DEPLOYMENT_FILE
    if default_file.exists():
        files.append(default_file)

    for profile_dir in sorted(project_path.glob(".*")):
        if not profile_dir.is_dir():
            continue
        deployment_file = profile_dir / DeploymentTracker.DEPLOYMENT_FILE
        if deployment_file.exists() and deployment_file not in files:
            files.append(deployment_file)

    return files


def backfill_project_deployment_records(
    project_path: Path,
    *,
    dry_run: bool = False,
    verbose: bool = False,
) -> tuple[int, int]:
    """Backfill deployment profile metadata for one project.

    Returns:
        Tuple of (records_backfilled, records_already_populated)
    """
    deployment_files = _find_deployment_files(project_path)
    if not deployment_files:
        return (0, 0)

    original_bytes: Dict[Path, bytes] = {}
    records_backfilled = 0
    records_already = 0

    try:
        for deployment_file in deployment_files:
            raw = deployment_file.read_bytes()
            original_bytes[deployment_file] = raw
            data = tomllib.loads(raw.decode("utf-8"))
            records = data.get("deployed", [])
            if not isinstance(records, list):
                continue

            changed = False
            fallback_root_dir = deployment_file.parent.name
            updated_records = []

            for record in records:
                if not isinstance(record, dict):
                    updated_records.append(record)
                    continue

                metadata = infer_record_profile_metadata(record, fallback_root_dir)

                has_all_fields = all(
                    record.get(key) not in (None, "")
                    for key in (
                        "deployment_profile_id",
                        "platform",
                        "profile_root_dir",
                    )
                )

                if has_all_fields:
                    records_already += 1
                    updated_records.append(record)
                    continue

                updated = dict(record)
                updated.update(metadata)
                updated_records.append(updated)
                records_backfilled += 1
                changed = True

                if verbose:
                    print(
                        f"  backfilled {project_path}:"
                        f" profile_id={metadata['deployment_profile_id']}"
                        f" platform={metadata['platform']}"
                        f" root={metadata['profile_root_dir']}"
                    )

            if changed and not dry_run:
                payload = {"deployed": updated_records}
                with deployment_file.open("wb") as handle:
                    tomli_w.dump(payload, handle)

    except Exception:
        if not dry_run:
            for file_path, content in original_bytes.items():
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_bytes(content)
        raise

    return (records_backfilled, records_already)


def _ensure_project_row(project_path: Path, db_path: Path, dry_run: bool) -> str:
    """Ensure project exists in cache DB and return project_id."""
    engine = create_db_engine(db_path)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = SessionLocal()
    try:
        existing = session.query(Project).filter(Project.path == str(project_path)).first()
        if existing:
            return existing.id

        project_id = uuid.uuid4().hex
        if not dry_run:
            session.add(
                Project(
                    id=project_id,
                    name=project_path.name,
                    path=str(project_path),
                    status="active",
                )
            )
            session.commit()
        return project_id
    finally:
        session.close()


def ensure_default_profile(
    project_path: Path,
    db_path: Path,
    *,
    dry_run: bool = False,
    verbose: bool = False,
) -> bool:
    """Ensure default claude_code profile exists for project.

    Returns True if a new profile would be/was created.
    """
    project_id = _ensure_project_row(project_path, db_path, dry_run)
    repo = DeploymentProfileRepository(db_path=db_path)

    existing = repo.read_by_project_and_profile_id(project_id, "claude_code")
    if existing is not None:
        return False

    if verbose:
        print(f"  creating default profile for {project_path}")

    if not dry_run:
        repo.create(
            project_id=project_id,
            profile_id="claude_code",
            platform=Platform.CLAUDE_CODE.value,
            root_dir=DEFAULT_PROFILE_ROOT_DIR,
            artifact_path_map=DEFAULT_ARTIFACT_PATH_MAP.copy(),
            config_filenames=DEFAULT_PROJECT_CONFIG_FILENAMES_BY_PLATFORM[
                Platform.CLAUDE_CODE
            ],
            context_prefixes=[f"{DEFAULT_PROFILE_ROOT_DIR}/context/", f"{DEFAULT_PROFILE_ROOT_DIR}/"],
            supported_types=["skill", "command", "agent", "hook", "mcp"],
        )

    return True


def _collect_candidate_projects(search_paths: Optional[List[Path]]) -> List[Path]:
    discovered = discover_projects(search_paths=search_paths)
    deduped: List[Path] = []
    seen = set()
    for project in discovered:
        resolved = Path(project).resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(resolved)
    return deduped


def migrate_projects(
    projects: Iterable[Path],
    *,
    db_path: Path,
    dry_run: bool = False,
    verbose: bool = False,
) -> MigrationStats:
    stats = MigrationStats()

    for project_path in projects:
        stats.projects_scanned += 1
        try:
            created_profile = ensure_default_profile(
                project_path,
                db_path,
                dry_run=dry_run,
                verbose=verbose,
            )
            if created_profile:
                stats.profiles_created += 1

            backfilled, already = backfill_project_deployment_records(
                project_path,
                dry_run=dry_run,
                verbose=verbose,
            )
            stats.records_backfilled += backfilled
            stats.records_already_populated += already

            if created_profile or backfilled:
                stats.projects_migrated += 1

        except Exception as exc:
            stats.projects_failed += 1
            logger.error("Failed migration for %s: %s", project_path, exc)

    return stats


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Migrate legacy deployments to deployment profiles",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing to disk or database",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show per-project migration details",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path.home() / ".skillmeat" / "cache" / "cache.db",
        help="Path to cache database (default: ~/.skillmeat/cache/cache.db)",
    )
    parser.add_argument(
        "--search-path",
        action="append",
        dest="search_paths",
        default=None,
        help="Optional search root (repeatable) used for project discovery",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(message)s",
    )

    db_path = Path(args.db_path).expanduser().resolve()
    create_tables(db_path)

    search_paths = [Path(p).expanduser().resolve() for p in (args.search_paths or [])]
    projects = _collect_candidate_projects(search_paths or None)

    if not projects:
        print("No projects with deployment records discovered.")
        return 0

    mode = "DRY RUN" if args.dry_run else "EXECUTE"
    print(f"Migration mode: {mode}")
    print(f"Projects discovered: {len(projects)}")

    stats = migrate_projects(
        projects,
        db_path=db_path,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    print("\nMigration summary")
    print(f"- projects scanned: {stats.projects_scanned}")
    print(f"- projects migrated: {stats.projects_migrated}")
    print(f"- profiles created: {stats.profiles_created}")
    print(f"- records backfilled: {stats.records_backfilled}")
    print(f"- records already populated: {stats.records_already_populated}")
    print(f"- projects failed: {stats.projects_failed}")

    return 1 if stats.projects_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
