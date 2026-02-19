"""Tests for composite bundle export functionality.

This module tests:
- export_composite_bundle generates a valid zip file
- The zip contains composite.json at root with composite metadata
- The zip contains child artifacts under type subdirectories in artifacts/
- Existing non-composite (regular) BundleBuilder export still works
- Unknown composite ID raises CompositeBundleError
- Composite with no members raises CompositeBundleError
"""

from __future__ import annotations

import json
import tempfile
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session, sessionmaker

from skillmeat.cache.models import (
    Artifact,
    Base,
    CompositeArtifact,
    CompositeMembership,
    Project,
    create_db_engine,
)
from skillmeat.core.sharing.bundle import (
    CompositeBundleError,
    export_composite_bundle,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_db() -> Generator[str, None, None]:
    """Create a temporary SQLite database file.

    Yields:
        Absolute path to the temp database file.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    yield db_path

    try:
        Path(db_path).unlink()
    except FileNotFoundError:
        pass


@pytest.fixture
def engine(temp_db: str):
    """SQLAlchemy engine with all ORM tables created.

    Args:
        temp_db: Path to the temp database file.

    Returns:
        Configured SQLAlchemy Engine.
    """
    eng = create_db_engine(temp_db)
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine) -> Generator[Session, None, None]:
    """Provide a transactional session, closed after each test.

    Yields:
        Active SQLAlchemy Session.
    """
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    sess = SessionLocal()
    try:
        yield sess
    finally:
        sess.close()


@pytest.fixture
def sample_project(session: Session) -> Project:
    """Insert and return a minimal Project row.

    Args:
        session: Active session from the session fixture.

    Returns:
        Persisted Project instance.
    """
    project = Project(
        id="proj-export-test-001",
        name="Export Test Project",
        path="/tmp/export-test-project",
        status="active",
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@pytest.fixture
def collection_with_artifacts(tmp_path: Path) -> Path:
    """Create a temporary collection directory with skill and command child artifacts.

    Directory layout::

        <tmp_path>/
            collection/
                skills/
                    my-skill/
                        SKILL.md
                        README.md
                commands/
                    my-command.md

    Returns:
        Path to the collection root.
    """
    coll = tmp_path / "collection"

    skill_dir = coll / "skills" / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# My Skill\nA test skill.", encoding="utf-8")
    (skill_dir / "README.md").write_text("# README\nSkill docs.", encoding="utf-8")

    cmd_dir = coll / "commands"
    cmd_dir.mkdir(parents=True)
    (cmd_dir / "my-command.md").write_text("# My Command\n", encoding="utf-8")

    return coll


@pytest.fixture
def composite_with_children(
    session: Session,
    sample_project: Project,
    collection_with_artifacts: Path,
) -> CompositeArtifact:
    """Insert a CompositeArtifact with two child Artifact memberships.

    Children:
        - skill:my-skill
        - command:my-command

    Returns:
        Persisted CompositeArtifact instance (with memberships eagerly available).
    """
    # Child artifacts
    skill_artifact = Artifact(
        id="skill:my-skill",
        project_id=sample_project.id,
        name="my-skill",
        type="skill",
        source="github:owner/repo",
        deployed_version="1.0.0",
    )
    cmd_artifact = Artifact(
        id="command:my-command",
        project_id=sample_project.id,
        name="my-command",
        type="command",
        source="github:owner/repo",
        deployed_version="2.0.0",
    )
    session.add(skill_artifact)
    session.add(cmd_artifact)
    session.flush()

    # CompositeArtifact
    composite = CompositeArtifact(
        id="composite:my-plugin",
        collection_id="test-collection",
        composite_type="plugin",
        display_name="My Plugin",
        description="A test composite plugin",
    )
    session.add(composite)
    session.flush()

    # Memberships
    session.add(
        CompositeMembership(
            collection_id="test-collection",
            composite_id="composite:my-plugin",
            child_artifact_uuid=skill_artifact.uuid,
        )
    )
    session.add(
        CompositeMembership(
            collection_id="test-collection",
            composite_id="composite:my-plugin",
            child_artifact_uuid=cmd_artifact.uuid,
        )
    )
    session.commit()

    # Reload to populate relationship attributes
    session.expire(composite)
    fresh_composite = (
        session.query(CompositeArtifact)
        .filter(CompositeArtifact.id == "composite:my-plugin")
        .first()
    )
    return fresh_composite


# =============================================================================
# Helper
# =============================================================================


@contextmanager
def _patch_collection_manager(collection_path: Path):
    """Patch CollectionManager at its source module so deferred imports resolve it.

    The ``export_composite_bundle`` function uses a deferred
    ``from skillmeat.core.collection import CollectionManager`` to avoid
    circular imports.  Patching at the source module ensures the deferred
    import picks up the mock.

    Args:
        collection_path: The directory the mock will return from
            ``config.get_collection_path()``.
    """
    config_mock = MagicMock()
    config_mock.get_collection_path.return_value = collection_path

    col_mock = MagicMock()
    col_mock.name = "test-collection"

    mgr_instance = MagicMock()
    mgr_instance.config = config_mock
    mgr_instance.get_active_collection_name.return_value = "test-collection"
    mgr_instance.load_collection.return_value = col_mock

    mgr_cls = MagicMock(return_value=mgr_instance)

    with patch("skillmeat.core.collection.CollectionManager", mgr_cls):
        yield mgr_instance


# =============================================================================
# Tests — export_composite_bundle
# =============================================================================


class TestExportCompositeBundleGeneratesValidZip:
    """export_composite_bundle creates a valid zip file at the requested path."""

    def test_returns_path_string(
        self,
        tmp_path: Path,
        session: Session,
        composite_with_children: CompositeArtifact,
        collection_with_artifacts: Path,
    ):
        output = tmp_path / "my-plugin.skillmeat-pack"

        with _patch_collection_manager(collection_with_artifacts):
            result = export_composite_bundle(
                composite_id="composite:my-plugin",
                output_path=str(output),
                session=session,
                collection_name="test-collection",
            )

        assert isinstance(result, str)
        assert Path(result).exists()
        assert zipfile.is_zipfile(result)

    def test_output_file_created_at_specified_path(
        self,
        tmp_path: Path,
        session: Session,
        composite_with_children: CompositeArtifact,
        collection_with_artifacts: Path,
    ):
        output = tmp_path / "output" / "exported.zip"

        with _patch_collection_manager(collection_with_artifacts):
            result = export_composite_bundle(
                composite_id="composite:my-plugin",
                output_path=str(output),
                session=session,
                collection_name="test-collection",
            )

        assert Path(result).exists()


class TestExportCompositeZipContainsCompositeMetadata:
    """The generated zip contains composite.json at the root."""

    def test_composite_json_present(
        self,
        tmp_path: Path,
        session: Session,
        composite_with_children: CompositeArtifact,
        collection_with_artifacts: Path,
    ):
        output = tmp_path / "out.skillmeat-pack"

        with _patch_collection_manager(collection_with_artifacts):
            result = export_composite_bundle(
                composite_id="composite:my-plugin",
                output_path=str(output),
                session=session,
                collection_name="test-collection",
            )

        with zipfile.ZipFile(result, "r") as zf:
            assert "composite.json" in zf.namelist()

    def test_composite_json_has_expected_fields(
        self,
        tmp_path: Path,
        session: Session,
        composite_with_children: CompositeArtifact,
        collection_with_artifacts: Path,
    ):
        output = tmp_path / "out.skillmeat-pack"

        with _patch_collection_manager(collection_with_artifacts):
            result = export_composite_bundle(
                composite_id="composite:my-plugin",
                output_path=str(output),
                session=session,
                collection_name="test-collection",
            )

        with zipfile.ZipFile(result, "r") as zf:
            data = json.loads(zf.read("composite.json"))

        assert data["id"] == "composite:my-plugin"
        assert data["composite_type"] == "plugin"
        assert data["display_name"] == "My Plugin"
        assert data["description"] == "A test composite plugin"
        assert data["member_count"] == 2

    def test_manifest_json_present_with_correct_name(
        self,
        tmp_path: Path,
        session: Session,
        composite_with_children: CompositeArtifact,
        collection_with_artifacts: Path,
    ):
        output = tmp_path / "out.skillmeat-pack"

        with _patch_collection_manager(collection_with_artifacts):
            result = export_composite_bundle(
                composite_id="composite:my-plugin",
                output_path=str(output),
                session=session,
                collection_name="test-collection",
            )

        with zipfile.ZipFile(result, "r") as zf:
            assert "manifest.json" in zf.namelist()
            manifest = json.loads(zf.read("manifest.json"))

        assert manifest["name"] == "my-plugin"
        assert "bundle_hash" in manifest
        assert manifest["bundle_hash"].startswith("sha256:")


class TestExportCompositeZipContainsChildArtifacts:
    """The generated zip contains child artifacts in type subdirectories."""

    def test_skill_child_included(
        self,
        tmp_path: Path,
        session: Session,
        composite_with_children: CompositeArtifact,
        collection_with_artifacts: Path,
    ):
        output = tmp_path / "out.skillmeat-pack"

        with _patch_collection_manager(collection_with_artifacts):
            result = export_composite_bundle(
                composite_id="composite:my-plugin",
                output_path=str(output),
                session=session,
                collection_name="test-collection",
            )

        with zipfile.ZipFile(result, "r") as zf:
            names = zf.namelist()

        skill_files = [n for n in names if "artifacts/skills/my-skill/" in n]
        assert len(skill_files) > 0

    def test_command_child_included(
        self,
        tmp_path: Path,
        session: Session,
        composite_with_children: CompositeArtifact,
        collection_with_artifacts: Path,
    ):
        output = tmp_path / "out.skillmeat-pack"

        with _patch_collection_manager(collection_with_artifacts):
            result = export_composite_bundle(
                composite_id="composite:my-plugin",
                output_path=str(output),
                session=session,
                collection_name="test-collection",
            )

        with zipfile.ZipFile(result, "r") as zf:
            names = zf.namelist()

        cmd_files = [n for n in names if "artifacts/commands/my-command/" in n]
        assert len(cmd_files) > 0

    def test_skill_files_have_correct_content(
        self,
        tmp_path: Path,
        session: Session,
        composite_with_children: CompositeArtifact,
        collection_with_artifacts: Path,
    ):
        output = tmp_path / "out.skillmeat-pack"

        with _patch_collection_manager(collection_with_artifacts):
            result = export_composite_bundle(
                composite_id="composite:my-plugin",
                output_path=str(output),
                session=session,
                collection_name="test-collection",
            )

        with zipfile.ZipFile(result, "r") as zf:
            names = zf.namelist()
            skill_md_entries = [n for n in names if n.endswith("SKILL.md")]
            assert len(skill_md_entries) == 1
            content = zf.read(skill_md_entries[0]).decode("utf-8")

        assert "My Skill" in content

    def test_manifest_artifacts_section_lists_all_children(
        self,
        tmp_path: Path,
        session: Session,
        composite_with_children: CompositeArtifact,
        collection_with_artifacts: Path,
    ):
        output = tmp_path / "out.skillmeat-pack"

        with _patch_collection_manager(collection_with_artifacts):
            result = export_composite_bundle(
                composite_id="composite:my-plugin",
                output_path=str(output),
                session=session,
                collection_name="test-collection",
            )

        with zipfile.ZipFile(result, "r") as zf:
            manifest = json.loads(zf.read("manifest.json"))

        artifact_names = {a["name"] for a in manifest["artifacts"]}
        assert "my-skill" in artifact_names
        assert "my-command" in artifact_names


class TestExportCompositeErrorCases:
    """Error handling for invalid inputs."""

    def test_unknown_composite_id_raises_error(
        self,
        tmp_path: Path,
        session: Session,
        collection_with_artifacts: Path,
    ):
        output = tmp_path / "out.skillmeat-pack"

        with _patch_collection_manager(collection_with_artifacts):
            with pytest.raises(CompositeBundleError, match="not found in the database"):
                export_composite_bundle(
                    composite_id="composite:does-not-exist",
                    output_path=str(output),
                    session=session,
                    collection_name="test-collection",
                )

    def test_composite_with_no_members_raises_error(
        self,
        tmp_path: Path,
        session: Session,
        sample_project: Project,
        collection_with_artifacts: Path,
    ):
        # Insert a composite with zero memberships
        empty_composite = CompositeArtifact(
            id="composite:empty-plugin",
            collection_id="test-collection",
            composite_type="plugin",
            display_name="Empty Plugin",
        )
        session.add(empty_composite)
        session.commit()

        output = tmp_path / "out.skillmeat-pack"

        with _patch_collection_manager(collection_with_artifacts):
            with pytest.raises(CompositeBundleError, match="no child members"):
                export_composite_bundle(
                    composite_id="composite:empty-plugin",
                    output_path=str(output),
                    session=session,
                    collection_name="test-collection",
                )

    def test_child_missing_from_filesystem_raises_error(
        self,
        tmp_path: Path,
        session: Session,
        sample_project: Project,
        collection_with_artifacts: Path,
    ):
        # Insert composite with a child whose files don't exist on disk
        ghost_artifact = Artifact(
            id="skill:ghost-skill",
            project_id=sample_project.id,
            name="ghost-skill",
            type="skill",
            deployed_version="1.0.0",
        )
        session.add(ghost_artifact)
        session.flush()

        composite = CompositeArtifact(
            id="composite:ghost-plugin",
            collection_id="test-collection",
            composite_type="plugin",
        )
        session.add(composite)
        session.flush()

        session.add(
            CompositeMembership(
                collection_id="test-collection",
                composite_id="composite:ghost-plugin",
                child_artifact_uuid=ghost_artifact.uuid,
            )
        )
        session.commit()

        output = tmp_path / "out.skillmeat-pack"
        # collection_with_artifacts does NOT contain "ghost-skill"
        with _patch_collection_manager(collection_with_artifacts):
            with pytest.raises(CompositeBundleError, match="not found on disk"):
                export_composite_bundle(
                    composite_id="composite:ghost-plugin",
                    output_path=str(output),
                    session=session,
                    collection_name="test-collection",
                )


class TestExistingBundleBuilderUnaffected:
    """Verify the pre-existing BundleBuilder / Bundle path still works.

    These tests check that the non-composite export infrastructure continues
    to function correctly after the new composite export was added.
    """

    def test_bundle_to_dict_and_hash_still_work(self, tmp_path: Path):
        """Bundle.to_dict() and BundleHasher still produce valid output."""
        from skillmeat.core.sharing.bundle import Bundle, BundleArtifact, BundleMetadata
        from skillmeat.core.sharing.hasher import BundleHasher

        skill_dir = tmp_path / "skills" / "demo"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Demo", encoding="utf-8")

        artifact_hash = BundleHasher.hash_artifact_files(skill_dir, ["SKILL.md"])
        ba = BundleArtifact(
            type="skill",
            name="demo",
            version="1.0.0",
            scope="user",
            path="artifacts/skills/demo/",
            files=["SKILL.md"],
            hash=artifact_hash,
        )
        meta = BundleMetadata(
            name="demo-bundle",
            description="Demo bundle",
            author="test@example.com",
            created_at="2024-01-01T00:00:00",
        )
        bundle = Bundle(metadata=meta, artifacts=[ba])

        manifest_dict = bundle.to_dict()
        bundle_hash = BundleHasher.compute_bundle_hash(manifest_dict, [ba.hash])
        manifest_dict["bundle_hash"] = bundle_hash

        assert manifest_dict["name"] == "demo-bundle"
        assert manifest_dict["bundle_hash"].startswith("sha256:")
        assert len(manifest_dict["artifacts"]) == 1

    def test_bundle_written_to_zip_is_valid(self, tmp_path: Path):
        """A manually assembled Bundle zip can be written and re-read."""
        import json as jsonmod
        import zipfile as zfmod

        from skillmeat.core.sharing.bundle import Bundle, BundleArtifact, BundleMetadata
        from skillmeat.core.sharing.hasher import BundleHasher

        skill_dir = tmp_path / "skills" / "demo"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Demo", encoding="utf-8")

        artifact_hash = BundleHasher.hash_artifact_files(skill_dir, ["SKILL.md"])
        ba = BundleArtifact(
            type="skill",
            name="demo",
            version="1.0.0",
            scope="user",
            path="artifacts/skills/demo/",
            files=["SKILL.md"],
            hash=artifact_hash,
        )
        meta = BundleMetadata(
            name="demo-bundle",
            description="Demo bundle",
            author="test@example.com",
            created_at="2024-01-01T00:00:00",
        )
        bundle = Bundle(metadata=meta, artifacts=[ba])
        manifest_dict = bundle.to_dict()
        bundle_hash = BundleHasher.compute_bundle_hash(manifest_dict, [ba.hash])
        manifest_dict["bundle_hash"] = bundle_hash

        out = tmp_path / "demo.skillmeat-pack"
        with zfmod.ZipFile(out, "w") as zf:
            zf.writestr("manifest.json", jsonmod.dumps(manifest_dict))

        assert out.exists()
        assert zfmod.is_zipfile(out)

        with zfmod.ZipFile(out, "r") as zf:
            loaded = jsonmod.loads(zf.read("manifest.json"))

        assert loaded["name"] == "demo-bundle"
        assert loaded["bundle_hash"].startswith("sha256:")
