"""Tests for compute_deployment_statuses_batch() in DeploymentManager.

Covers:
- Synced status (unmodified deployment)
- Modified status (file changed after deployment)
- Missing path behavior (path does not exist on disk)
- Batch over multiple deployments
- Path-level hash cache reuse (hash computed once per unique path)
- Consistency with detect_modifications() per-artifact API
- Multi-profile disambiguation (key format includes profile suffix)
- File-count early-exit tier (directory artifact with stored file_count)
- Pre-loaded deployments parameter avoids extra TOML read
"""

from datetime import datetime
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType
from skillmeat.core.deployment import Deployment, DeploymentManager
from skillmeat.core.path_resolver import DEFAULT_PROFILE_ROOT_DIR
from skillmeat.storage.deployment import DeploymentTracker
from skillmeat.utils.filesystem import compute_content_hash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_deployment(
    *,
    artifact_name: str,
    artifact_type: str = "skill",
    artifact_path: Path,
    content_hash: str,
    profile_id: str = "claude_code",
    profile_root_dir: str = DEFAULT_PROFILE_ROOT_DIR,
    file_count: int = None,
) -> Deployment:
    """Build a Deployment dataclass for use in tests without hitting the filesystem."""
    dep = Deployment(
        artifact_name=artifact_name,
        artifact_type=artifact_type,
        from_collection="default",
        deployed_at=datetime.now(),
        artifact_path=artifact_path,
        content_hash=content_hash,
        local_modifications=False,
        deployment_profile_id=profile_id,
        profile_root_dir=profile_root_dir,
    )
    if file_count is not None:
        dep.file_count = file_count  # type: ignore[attr-defined]
    return dep


def _record_skill(
    project_path: Path,
    skill_dir: Path,
    name: str = "test-skill",
) -> str:
    """Record a skill deployment in the TOML file.

    Returns the content hash so callers can verify "synced" expectations.
    """
    artifact = Artifact(
        name=name,
        type=ArtifactType.SKILL,
        path=f"skills/{name}",
        origin="local",
        metadata=ArtifactMetadata(),
        added=datetime.now(),
    )
    content_hash = compute_content_hash(skill_dir)
    DeploymentTracker.record_deployment(
        project_path=project_path,
        artifact=artifact,
        collection_name="default",
        collection_sha=content_hash,
    )
    return content_hash


def _record_command(
    project_path: Path,
    command_file: Path,
    name: str = "test-cmd",
) -> str:
    """Record a command deployment in the TOML file.

    Returns the content hash.
    """
    artifact = Artifact(
        name=name,
        type=ArtifactType.COMMAND,
        path=f"commands/{name}.md",
        origin="local",
        metadata=ArtifactMetadata(),
        added=datetime.now(),
    )
    content_hash = compute_content_hash(command_file)
    DeploymentTracker.record_deployment(
        project_path=project_path,
        artifact=artifact,
        collection_name="default",
        collection_sha=content_hash,
    )
    return content_hash


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_collection_mgr():
    """Minimal CollectionManager mock — only needed to instantiate DeploymentManager."""
    mgr = MagicMock()
    mgr.config = MagicMock()
    return mgr


@pytest.fixture
def project_path(tmp_path) -> Path:
    """Temporary project root with .claude/ skeleton."""
    project = tmp_path / "project"
    project.mkdir()
    (project / ".claude" / "skills").mkdir(parents=True)
    (project / ".claude" / "commands").mkdir(parents=True)
    (project / ".claude" / "agents").mkdir(parents=True)
    return project


@pytest.fixture
def manager(mock_collection_mgr) -> DeploymentManager:
    return DeploymentManager(collection_mgr=mock_collection_mgr)


# ---------------------------------------------------------------------------
# 1. Synced status
# ---------------------------------------------------------------------------


class TestSyncedStatus:
    """compute_deployment_statuses_batch returns 'synced' when content matches."""

    def test_skill_synced(self, project_path, manager):
        """Unmodified deployed skill directory reports 'synced'."""
        skill_dir = project_path / ".claude" / "skills" / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# My Skill")

        _record_skill(project_path, skill_dir, name="my-skill")

        status = manager.compute_deployment_statuses_batch(project_path=project_path)

        assert "my-skill::skill" in status
        assert status["my-skill::skill"] == "synced"

    def test_command_synced(self, project_path, manager):
        """Unmodified deployed command file reports 'synced'."""
        cmd_file = project_path / ".claude" / "commands" / "review-cmd.md"
        cmd_file.write_text("# Review")

        _record_command(project_path, cmd_file, name="review-cmd")

        status = manager.compute_deployment_statuses_batch(project_path=project_path)

        assert "review-cmd::command" in status
        assert status["review-cmd::command"] == "synced"

    def test_empty_dict_when_no_deployments(self, project_path, manager):
        """Returns empty dict when no deployments exist."""
        status = manager.compute_deployment_statuses_batch(project_path=project_path)
        assert status == {}


# ---------------------------------------------------------------------------
# 2. Modified status
# ---------------------------------------------------------------------------


class TestModifiedStatus:
    """compute_deployment_statuses_batch returns 'modified' when content differs."""

    def test_skill_modified_after_file_change(self, project_path, manager):
        """Modifying a file in the deployed skill changes status to 'modified'."""
        skill_dir = project_path / ".claude" / "skills" / "my-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("# Original")

        _record_skill(project_path, skill_dir, name="my-skill")

        # Mutate the deployed file after recording
        skill_md.write_text("# Modified by user")

        status = manager.compute_deployment_statuses_batch(project_path=project_path)

        assert status["my-skill::skill"] == "modified"

    def test_command_modified_after_file_change(self, project_path, manager):
        """Modifying a command file changes status to 'modified'."""
        cmd_file = project_path / ".claude" / "commands" / "my-cmd.md"
        cmd_file.write_text("# Original command")

        _record_command(project_path, cmd_file, name="my-cmd")

        cmd_file.write_text("# User changed this command")

        status = manager.compute_deployment_statuses_batch(project_path=project_path)

        assert status["my-cmd::command"] == "modified"

    def test_adding_file_to_skill_marks_modified(self, project_path, manager):
        """Adding a new file to a deployed skill directory marks it 'modified'."""
        skill_dir = project_path / ".claude" / "skills" / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Skill")

        _record_skill(project_path, skill_dir, name="my-skill")

        # Add a new file
        (skill_dir / "extra.md").write_text("# Extra file added by user")

        status = manager.compute_deployment_statuses_batch(project_path=project_path)

        assert status["my-skill::skill"] == "modified"

    def test_stale_hash_in_record_marks_modified(self, project_path, manager):
        """A deployment record with a wrong hash marks the artifact as 'modified'."""
        skill_dir = project_path / ".claude" / "skills" / "stale-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Skill")

        # Record with a deliberately wrong hash
        artifact = Artifact(
            name="stale-skill",
            type=ArtifactType.SKILL,
            path="skills/stale-skill",
            origin="local",
            metadata=ArtifactMetadata(),
            added=datetime.now(),
        )
        DeploymentTracker.record_deployment(
            project_path=project_path,
            artifact=artifact,
            collection_name="default",
            collection_sha="0" * 64,  # wrong hash
        )

        status = manager.compute_deployment_statuses_batch(project_path=project_path)

        assert status["stale-skill::skill"] == "modified"


# ---------------------------------------------------------------------------
# 3. Missing path behavior
# ---------------------------------------------------------------------------


class TestMissingPath:
    """compute_deployment_statuses_batch handles missing on-disk paths."""

    def test_missing_path_returns_synced(self, project_path, manager):
        """A deployment whose on-disk path no longer exists reports 'synced'.

        This mirrors the behaviour of detect_modifications() which returns False
        (not modified) when the path is absent.
        """
        # Build a Deployment record that points to a non-existent path
        nonexistent_rel = Path("skills/ghost-skill")
        deployment = _make_deployment(
            artifact_name="ghost-skill",
            artifact_type="skill",
            artifact_path=nonexistent_rel,
            content_hash="a" * 64,
        )

        status = manager.compute_deployment_statuses_batch(
            project_path=project_path,
            deployments=[deployment],
        )

        assert "ghost-skill::skill" in status
        assert status["ghost-skill::skill"] == "synced"

    def test_nonexistent_command_file_returns_synced(self, project_path, manager):
        """A missing single-file command deployment reports 'synced'."""
        deployment = _make_deployment(
            artifact_name="gone-cmd",
            artifact_type="command",
            artifact_path=Path("commands/gone-cmd.md"),
            content_hash="b" * 64,
        )

        status = manager.compute_deployment_statuses_batch(
            project_path=project_path,
            deployments=[deployment],
        )

        assert status.get("gone-cmd::command") == "synced"


# ---------------------------------------------------------------------------
# 4. Multiple deployments — batch correctness
# ---------------------------------------------------------------------------


class TestMultipleDeployments:
    """Batch call returns correct status for each of several deployments."""

    def test_three_artifacts_all_synced(self, project_path, manager):
        """Three unmodified deployments all report 'synced' in one batch call."""
        # Skill
        skill_dir = project_path / ".claude" / "skills" / "skill-a"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Skill A")
        _record_skill(project_path, skill_dir, name="skill-a")

        # Command
        cmd_file = project_path / ".claude" / "commands" / "cmd-b.md"
        cmd_file.write_text("# Cmd B")
        _record_command(project_path, cmd_file, name="cmd-b")

        # Agent (use command helper with ArtifactType.AGENT)
        agent_file = project_path / ".claude" / "agents" / "agent-c.md"
        agent_file.write_text("# Agent C")
        artifact = Artifact(
            name="agent-c",
            type=ArtifactType.AGENT,
            path="agents/agent-c.md",
            origin="local",
            metadata=ArtifactMetadata(),
            added=datetime.now(),
        )
        DeploymentTracker.record_deployment(
            project_path=project_path,
            artifact=artifact,
            collection_name="default",
            collection_sha=compute_content_hash(agent_file),
        )

        status = manager.compute_deployment_statuses_batch(project_path=project_path)

        assert status["skill-a::skill"] == "synced"
        assert status["cmd-b::command"] == "synced"
        assert status["agent-c::agent"] == "synced"

    def test_mix_of_synced_and_modified(self, project_path, manager):
        """Batch returns per-artifact status when some are modified."""
        # Synced skill
        skill_dir = project_path / ".claude" / "skills" / "clean-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Clean")
        _record_skill(project_path, skill_dir, name="clean-skill")

        # Skill that will be modified
        dirty_dir = project_path / ".claude" / "skills" / "dirty-skill"
        dirty_dir.mkdir()
        dirty_md = dirty_dir / "SKILL.md"
        dirty_md.write_text("# Original")
        _record_skill(project_path, dirty_dir, name="dirty-skill")
        dirty_md.write_text("# Changed by user")

        # Command — missing on disk (should be 'synced' per current semantics)
        cmd_file = project_path / ".claude" / "commands" / "absent-cmd.md"
        cmd_file.write_text("# Absent")
        _record_command(project_path, cmd_file, name="absent-cmd")
        cmd_file.unlink()

        status = manager.compute_deployment_statuses_batch(project_path=project_path)

        assert status["clean-skill::skill"] == "synced"
        assert status["dirty-skill::skill"] == "modified"
        assert status["absent-cmd::command"] == "synced"

    def test_four_artifacts_unique_keys(self, project_path, manager):
        """Four different artifacts each appear under their own key."""
        names_and_types = [
            ("art1", ArtifactType.SKILL, "skills", True),
            ("art2", ArtifactType.COMMAND, "commands", False),
            ("art3", ArtifactType.AGENT, "agents", False),
            ("art4", ArtifactType.SKILL, "skills", True),
        ]

        for name, atype, subdir, is_dir in names_and_types:
            if is_dir:
                p = project_path / ".claude" / subdir / name
                p.mkdir(parents=True, exist_ok=True)
                (p / "SKILL.md").write_text(f"# {name}")
                artifact = Artifact(
                    name=name,
                    type=atype,
                    path=f"{subdir}/{name}",
                    origin="local",
                    metadata=ArtifactMetadata(),
                    added=datetime.now(),
                )
                DeploymentTracker.record_deployment(
                    project_path=project_path,
                    artifact=artifact,
                    collection_name="default",
                    collection_sha=compute_content_hash(p),
                )
            else:
                p = project_path / ".claude" / subdir / f"{name}.md"
                p.write_text(f"# {name}")
                artifact = Artifact(
                    name=name,
                    type=atype,
                    path=f"{subdir}/{name}.md",
                    origin="local",
                    metadata=ArtifactMetadata(),
                    added=datetime.now(),
                )
                DeploymentTracker.record_deployment(
                    project_path=project_path,
                    artifact=artifact,
                    collection_name="default",
                    collection_sha=compute_content_hash(p),
                )

        status = manager.compute_deployment_statuses_batch(project_path=project_path)

        assert len(status) == 4
        for name, atype, _, _ in names_and_types:
            assert f"{name}::{atype.value}" in status
            assert status[f"{name}::{atype.value}"] == "synced"


# ---------------------------------------------------------------------------
# 5. Hash cache reuse
# ---------------------------------------------------------------------------


class TestHashCacheReuse:
    """compute_content_hash is called at most once per unique on-disk path."""

    def test_two_records_same_path_hash_computed_once(self, project_path, manager):
        """Two Deployment records pointing to the same path share one hash computation."""
        skill_dir = project_path / ".claude" / "skills" / "shared-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Shared")

        real_hash = compute_content_hash(skill_dir)
        rel_path = Path("skills/shared-skill")

        # Two records that both resolve to the same absolute directory
        dep_a = _make_deployment(
            artifact_name="shared-skill",
            artifact_type="skill",
            artifact_path=rel_path,
            content_hash=real_hash,
            profile_id="claude_code",
        )
        dep_b = _make_deployment(
            artifact_name="shared-skill",
            artifact_type="skill",
            artifact_path=rel_path,
            content_hash=real_hash,
            profile_id="cursor",  # Different profile, same path resolves identically
        )

        call_count = []

        original_hash_fn = compute_content_hash

        def counting_hash(path):
            call_count.append(str(path))
            return original_hash_fn(path)

        # The function is re-imported locally inside compute_deployment_statuses_batch
        # via `from skillmeat.utils.filesystem import compute_content_hash`, so we
        # must patch the origin module — not the deployment module's module-level name.
        with patch(
            "skillmeat.utils.filesystem.compute_content_hash",
            side_effect=counting_hash,
        ):
            status = manager.compute_deployment_statuses_batch(
                project_path=project_path,
                deployments=[dep_a, dep_b],
            )

        # Hash must have been computed exactly once (cache reuse for duplicate path)
        skill_full = str((project_path / ".claude" / "skills" / "shared-skill").resolve())
        hits = [p for p in call_count if p == skill_full]
        assert len(hits) == 1, (
            f"Expected 1 hash computation for the shared path, got {len(hits)}; "
            f"all calls: {call_count}"
        )

        # Both records should report correctly
        assert "shared-skill::skill::claude_code" in status
        assert "shared-skill::skill::cursor" in status
        assert status["shared-skill::skill::claude_code"] == "synced"
        assert status["shared-skill::skill::cursor"] == "synced"

    def test_three_distinct_paths_hash_computed_three_times(
        self, project_path, manager
    ):
        """Three deployments with different paths each trigger one hash computation."""
        skills = ["alpha", "beta", "gamma"]
        deployments = []
        for name in skills:
            d = project_path / ".claude" / "skills" / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text(f"# {name}")
            deployments.append(
                _make_deployment(
                    artifact_name=name,
                    artifact_type="skill",
                    artifact_path=Path(f"skills/{name}"),
                    content_hash=compute_content_hash(d),
                )
            )

        call_count = []
        original_hash_fn = compute_content_hash

        def counting_hash(path):
            call_count.append(str(path))
            return original_hash_fn(path)

        with patch(
            "skillmeat.utils.filesystem.compute_content_hash",
            side_effect=counting_hash,
        ):
            manager.compute_deployment_statuses_batch(
                project_path=project_path,
                deployments=deployments,
            )

        assert len(call_count) == 3


# ---------------------------------------------------------------------------
# 6. Consistency with detect_modifications()
# ---------------------------------------------------------------------------


class TestConsistencyWithDetectModifications:
    """Batch results must agree with per-artifact detect_modifications()."""

    def _assert_consistency(
        self,
        project_path: Path,
        manager: DeploymentManager,
        names_and_types: List[tuple],
    ) -> None:
        """Check that batch result matches individual detect_modifications() calls."""
        batch_status = manager.compute_deployment_statuses_batch(
            project_path=project_path
        )
        for name, atype in names_and_types:
            key = f"{name}::{atype}"
            is_modified = DeploymentTracker.detect_modifications(
                project_path=project_path,
                artifact_name=name,
                artifact_type=atype,
            )
            expected = "modified" if is_modified else "synced"
            assert batch_status.get(key) == expected, (
                f"Mismatch for {key}: batch={batch_status.get(key)!r}, "
                f"detect_modifications()={'modified' if is_modified else 'synced'!r}"
            )

    def test_all_synced_agrees(self, project_path, manager):
        """Batch and detect_modifications() agree when all artifacts are synced."""
        skill_dir = project_path / ".claude" / "skills" / "sku1"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Sku1")
        _record_skill(project_path, skill_dir, name="sku1")

        cmd_file = project_path / ".claude" / "commands" / "cmd1.md"
        cmd_file.write_text("# Cmd1")
        _record_command(project_path, cmd_file, name="cmd1")

        self._assert_consistency(
            project_path, manager, [("sku1", "skill"), ("cmd1", "command")]
        )

    def test_one_modified_agrees(self, project_path, manager):
        """Batch and detect_modifications() agree when one artifact is modified."""
        skill_dir = project_path / ".claude" / "skills" / "sku2"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("# Original")
        _record_skill(project_path, skill_dir, name="sku2")
        skill_md.write_text("# Changed")  # Mutate after recording

        cmd_file = project_path / ".claude" / "commands" / "cmd2.md"
        cmd_file.write_text("# Cmd2")
        _record_command(project_path, cmd_file, name="cmd2")

        self._assert_consistency(
            project_path, manager, [("sku2", "skill"), ("cmd2", "command")]
        )

    def test_missing_path_agrees(self, project_path, manager):
        """Batch and detect_modifications() agree when deployed path is absent."""
        skill_dir = project_path / ".claude" / "skills" / "ghost"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Ghost")
        _record_skill(project_path, skill_dir, name="ghost")
        # Remove the directory so path is missing
        import shutil
        shutil.rmtree(skill_dir)

        self._assert_consistency(project_path, manager, [("ghost", "skill")])


# ---------------------------------------------------------------------------
# 7. Profile handling / key disambiguation
# ---------------------------------------------------------------------------


class TestProfileHandling:
    """Artifacts deployed to multiple profiles use profile-qualified keys."""

    def test_single_profile_uses_base_key(self, project_path, manager):
        """Single-profile deployment uses 'name::type' key (no profile suffix)."""
        dep = _make_deployment(
            artifact_name="solo",
            artifact_type="skill",
            artifact_path=Path("skills/solo"),
            content_hash="a" * 64,  # missing path → synced
            profile_id="claude_code",
        )

        status = manager.compute_deployment_statuses_batch(
            project_path=project_path,
            deployments=[dep],
        )

        assert "solo::skill" in status
        assert "solo::skill::claude_code" not in status

    def test_two_profiles_use_qualified_keys(self, project_path, manager):
        """Two deployments of the same artifact (different profiles) use qualified keys."""
        dep_cc = _make_deployment(
            artifact_name="shared",
            artifact_type="skill",
            artifact_path=Path("skills/shared"),
            content_hash="a" * 64,
            profile_id="claude_code",
        )
        dep_cx = _make_deployment(
            artifact_name="shared",
            artifact_type="skill",
            artifact_path=Path("skills/shared"),
            content_hash="a" * 64,
            profile_id="cursor",
            profile_root_dir=".cursor",
        )

        status = manager.compute_deployment_statuses_batch(
            project_path=project_path,
            deployments=[dep_cc, dep_cx],
        )

        assert "shared::skill" not in status
        assert "shared::skill::claude_code" in status
        assert "shared::skill::cursor" in status

    def test_profile_id_filter_restricts_results(self, project_path, manager):
        """profile_id parameter returns only matching deployments."""
        skill_dir = project_path / ".claude" / "skills" / "filtered"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Filtered")

        dep_cc = _make_deployment(
            artifact_name="filtered",
            artifact_type="skill",
            artifact_path=Path("skills/filtered"),
            content_hash=compute_content_hash(skill_dir),
            profile_id="claude_code",
        )
        dep_cx = _make_deployment(
            artifact_name="filtered",
            artifact_type="skill",
            artifact_path=Path("skills/filtered"),
            content_hash="b" * 64,  # wrong hash
            profile_id="cursor",
            profile_root_dir=".cursor",
        )

        # Filter to claude_code only
        status = manager.compute_deployment_statuses_batch(
            project_path=project_path,
            profile_id="claude_code",
            deployments=[dep_cc, dep_cx],
        )

        # Only claude_code deployment survives the filter
        assert len(status) == 1
        assert "filtered::skill" in status
        assert status["filtered::skill"] == "synced"


# ---------------------------------------------------------------------------
# 8. File-count early-exit tier
# ---------------------------------------------------------------------------


class TestFileCountEarlyExit:
    """file_count attribute triggers os.scandir check before hash computation."""

    def test_file_count_mismatch_returns_modified_without_hash(
        self, project_path, manager
    ):
        """A directory with wrong file_count reports 'modified' without hashing."""
        skill_dir = project_path / ".claude" / "skills" / "counted"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Counted")
        # One file on disk, but record claims 5
        dep = _make_deployment(
            artifact_name="counted",
            artifact_type="skill",
            artifact_path=Path("skills/counted"),
            content_hash=compute_content_hash(skill_dir),
            file_count=5,  # mismatch
        )

        call_count = []

        original_hash_fn = compute_content_hash

        def counting_hash(path):
            call_count.append(str(path))
            return original_hash_fn(path)

        with patch(
            "skillmeat.core.deployment.compute_content_hash",
            side_effect=counting_hash,
        ):
            status = manager.compute_deployment_statuses_batch(
                project_path=project_path,
                deployments=[dep],
            )

        assert status["counted::skill"] == "modified"
        # Hash should NOT have been computed (early exit via file count)
        assert len(call_count) == 0

    def test_file_count_match_falls_through_to_hash(self, project_path, manager):
        """A correct file_count falls through to the hash tier."""
        skill_dir = project_path / ".claude" / "skills" / "match-count"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Match Count")
        (skill_dir / "helper.md").write_text("# Helper")
        real_hash = compute_content_hash(skill_dir)

        dep = _make_deployment(
            artifact_name="match-count",
            artifact_type="skill",
            artifact_path=Path("skills/match-count"),
            content_hash=real_hash,
            file_count=2,  # correct
        )

        call_count = []
        original_hash_fn = compute_content_hash

        def counting_hash(path):
            call_count.append(str(path))
            return original_hash_fn(path)

        with patch(
            "skillmeat.utils.filesystem.compute_content_hash",
            side_effect=counting_hash,
        ):
            status = manager.compute_deployment_statuses_batch(
                project_path=project_path,
                deployments=[dep],
            )

        assert status["match-count::skill"] == "synced"
        # Hash was computed (fell through file-count tier)
        assert len(call_count) == 1

    def test_no_file_count_attribute_falls_through_to_hash(
        self, project_path, manager
    ):
        """A Deployment without file_count attribute falls through to hash."""
        skill_dir = project_path / ".claude" / "skills" / "no-count"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# No Count")
        real_hash = compute_content_hash(skill_dir)

        # Deployment without file_count attribute (legacy record)
        dep = _make_deployment(
            artifact_name="no-count",
            artifact_type="skill",
            artifact_path=Path("skills/no-count"),
            content_hash=real_hash,
            file_count=None,  # None means attribute absent in getattr default
        )

        call_count = []
        original_hash_fn = compute_content_hash

        def counting_hash(path):
            call_count.append(str(path))
            return original_hash_fn(path)

        with patch(
            "skillmeat.utils.filesystem.compute_content_hash",
            side_effect=counting_hash,
        ):
            status = manager.compute_deployment_statuses_batch(
                project_path=project_path,
                deployments=[dep],
            )

        assert status["no-count::skill"] == "synced"
        assert len(call_count) == 1


# ---------------------------------------------------------------------------
# 9. Pre-loaded deployments parameter
# ---------------------------------------------------------------------------


class TestPreLoadedDeployments:
    """Passing deployments= skips the TOML read entirely."""

    def test_preloaded_deployments_skips_toml_read(self, project_path, manager):
        """When deployments is passed, read_deployments is not called."""
        skill_dir = project_path / ".claude" / "skills" / "preloaded"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Preloaded")
        real_hash = compute_content_hash(skill_dir)

        dep = _make_deployment(
            artifact_name="preloaded",
            artifact_type="skill",
            artifact_path=Path("skills/preloaded"),
            content_hash=real_hash,
        )

        with patch.object(
            DeploymentTracker,
            "read_deployments",
            wraps=DeploymentTracker.read_deployments,
        ) as mock_read:
            status = manager.compute_deployment_statuses_batch(
                project_path=project_path,
                deployments=[dep],
            )

        mock_read.assert_not_called()
        assert status["preloaded::skill"] == "synced"

    def test_preloaded_empty_list_returns_empty_dict(self, project_path, manager):
        """Passing an empty deployments list returns {} without any I/O."""
        with patch.object(
            DeploymentTracker,
            "read_deployments",
        ) as mock_read:
            status = manager.compute_deployment_statuses_batch(
                project_path=project_path,
                deployments=[],
            )

        mock_read.assert_not_called()
        assert status == {}
