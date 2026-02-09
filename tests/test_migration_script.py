"""Tests for Phase 5 deployment profile migration script."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

if hasattr(__import__("sys"), "version_info") and __import__("sys").version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

from skillmeat.cache.models import Project, create_db_engine, create_tables
from skillmeat.cache.repositories import DeploymentProfileRepository
from sqlalchemy.orm import sessionmaker


def _load_migration_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "migrate_to_deployment_profiles.py"
    spec = importlib.util.spec_from_file_location("migrate_to_deployment_profiles", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_legacy_deployments(project_path: Path) -> Path:
    deployment_file = project_path / ".claude" / ".skillmeat-deployed.toml"
    deployment_file.parent.mkdir(parents=True, exist_ok=True)
    deployment_file.write_text(
        """
[[deployed]]
artifact_name = "legacy-skill"
artifact_type = "skill"
from_collection = "default"
deployed_at = "2026-02-09T10:00:00"
artifact_path = "skills/legacy-skill"
content_hash = "abc123"
local_modifications = false
collection_sha = "abc123"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return deployment_file


def test_infer_record_profile_metadata_defaults_to_claude_root():
    migration = _load_migration_module()

    metadata = migration.infer_record_profile_metadata(
        {
            "artifact_path": "skills/sample",
        },
        ".claude",
    )

    assert metadata["deployment_profile_id"] == "claude_code"
    assert metadata["platform"] == "claude_code"
    assert metadata["profile_root_dir"] == ".claude"


def test_backfill_project_deployment_records_updates_legacy_records(tmp_path: Path):
    migration = _load_migration_module()

    project_path = tmp_path / "legacy-project"
    project_path.mkdir()
    deployment_file = _write_legacy_deployments(project_path)

    backfilled, already = migration.backfill_project_deployment_records(project_path)

    assert backfilled == 1
    assert already == 0

    data = tomllib.loads(deployment_file.read_text(encoding="utf-8"))
    deployed = data["deployed"][0]
    assert deployed["deployment_profile_id"] == "claude_code"
    assert deployed["platform"] == "claude_code"
    assert deployed["profile_root_dir"] == ".claude"


def test_backfill_project_deployment_records_dry_run_is_non_destructive(tmp_path: Path):
    migration = _load_migration_module()

    project_path = tmp_path / "legacy-project"
    project_path.mkdir()
    deployment_file = _write_legacy_deployments(project_path)
    before = deployment_file.read_text(encoding="utf-8")

    backfilled, already = migration.backfill_project_deployment_records(
        project_path,
        dry_run=True,
    )

    assert backfilled == 1
    assert already == 0
    assert deployment_file.read_text(encoding="utf-8") == before


def test_ensure_default_profile_creates_profile_and_project_row(tmp_path: Path):
    migration = _load_migration_module()

    project_path = tmp_path / "project"
    project_path.mkdir()

    db_path = tmp_path / "cache.db"
    create_tables(db_path)

    created = migration.ensure_default_profile(project_path, db_path)
    assert created is True

    repo = DeploymentProfileRepository(db_path=db_path)

    engine = create_db_engine(db_path)
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    session = SessionLocal()
    try:
        project = session.query(Project).filter(Project.path == str(project_path)).first()
        assert project is not None
        profile = repo.read_by_project_and_profile_id(project.id, "claude_code")
    finally:
        session.close()

    assert profile is not None
    assert profile.platform == "claude_code"
    assert profile.root_dir == ".claude"
