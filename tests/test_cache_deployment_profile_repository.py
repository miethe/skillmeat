"""Tests for DeploymentProfileRepository and Phase 1 migration surfaces."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

from skillmeat.cache.models import Project, create_db_engine, create_tables
from skillmeat.cache.repositories import DeploymentProfileRepository


@pytest.fixture
def temp_db():
    """Create a temporary SQLite DB path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    try:
        Path(db_path).unlink()
    except FileNotFoundError:
        pass


@pytest.fixture
def seeded_project(temp_db):
    """Create base schema and one project row for FK-backed profile tests."""
    create_tables(temp_db)
    engine = create_db_engine(temp_db)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    try:
        session.add(
            Project(
                id="proj-1",
                name="Project One",
                path="/tmp/project-one",
                status="active",
            )
        )
        session.commit()
    finally:
        session.close()
        engine.dispose()
    return "proj-1"


def test_deployment_profile_repository_crud(temp_db, seeded_project):
    """Repository should support create/read/list/update/delete lifecycle."""
    repo = DeploymentProfileRepository(db_path=temp_db)

    created = repo.create(
        project_id=seeded_project,
        profile_id="codex-default",
        platform="codex",
        root_dir=".codex",
        artifact_path_map={"skill": "skills"},
        config_filenames=["CODEX.md"],
        context_prefixes=[".codex/context/"],
        supported_types=["skill", "command"],
    )
    assert created.profile_id == "codex-default"
    assert created.platform == "codex"

    by_id = repo.read_by_id(created.id)
    assert by_id is not None
    assert by_id.profile_id == "codex-default"

    by_project_profile = repo.read_by_project_and_profile_id(
        seeded_project, "codex-default"
    )
    assert by_project_profile is not None
    assert by_project_profile.root_dir == ".codex"

    listed = repo.list_by_project(seeded_project)
    assert len(listed) == 1
    assert listed[0].profile_id == "codex-default"

    updated = repo.update(
        seeded_project,
        "codex-default",
        root_dir=".codex-custom",
        supported_types=["skill"],
    )
    assert updated is not None
    assert updated.root_dir == ".codex-custom"
    assert updated.supported_types == ["skill"]

    assert repo.delete(seeded_project, "codex-default") is True
    assert repo.read_by_project_and_profile_id(seeded_project, "codex-default") is None


def test_phase1_schema_contains_profile_table_and_target_platforms_column(temp_db):
    """Current schema should include Phase 1 structures."""
    create_tables(temp_db)

    conn = sqlite3.connect(temp_db)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "deployment_profiles" in tables

        artifact_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(artifacts)").fetchall()
        }
        assert "target_platforms" in artifact_columns
    finally:
        conn.close()


def test_phase1_migration_file_contains_expected_operations():
    """Migration file should include required table and column operations."""
    migration_file = (
        Path(__file__).parents[1]
        / "skillmeat"
        / "cache"
        / "migrations"
        / "versions"
        / "20260207_1400_add_deployment_profiles_and_target_platforms.py"
    )
    text = migration_file.read_text(encoding="utf-8")
    assert 'batch_op.add_column(sa.Column("target_platforms"' in text
    assert 'op.create_table(\n        "deployment_profiles"' in text
    assert 'op.drop_table("deployment_profiles")' in text
