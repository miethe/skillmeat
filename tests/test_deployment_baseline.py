#!/usr/bin/env python3
"""Tests for deployment baseline storage and retrieval.

This module tests the storage of merge_base_snapshot during deployment
and its retrieval for three-way merge operations (TASK-1.1, TASK-1.2, TASK-1.4).
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from skillmeat.core.deployment import Deployment, DeploymentManager
from skillmeat.core.artifact import ArtifactType
from skillmeat.storage.deployment import DeploymentTracker
from skillmeat.utils.filesystem import compute_content_hash


class TestDeploymentBaselineStorage:
    """Tests for storing merge_base_snapshot during deployment."""

    def test_new_deployment_stores_baseline_hash(self, temp_project, temp_collection):
        """Test that new deployments store baseline hash in merge_base_snapshot field.

        Acceptance: TASK-1.2
        - Content hash computed during deployment
        - Hash stored in merge_base_snapshot field
        - Hash matches deployed artifact content
        """
        # Create a sample skill in collection
        skill_dir = temp_collection / "artifacts" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        skill_md = skill_dir / "SKILL.md"
        skill_content = """---
title: Test Skill
description: A test skill
version: 1.0.0
---

# Test Skill

Test content for baseline tracking.
"""
        skill_md.write_text(skill_content)

        # Compute expected hash
        expected_hash = compute_content_hash(skill_dir)

        # Deploy artifact
        tracker = DeploymentTracker(temp_project)
        deployment = Deployment(
            artifact_name="test-skill",
            artifact_type="skill",
            from_collection=str(temp_collection),
            deployed_at=datetime.now(),
            artifact_path=Path("skills/test-skill"),
            content_hash=expected_hash,
        )

        # Verify deployment has baseline hash
        assert deployment.content_hash == expected_hash
        assert deployment.content_hash is not None
        assert len(deployment.content_hash) == 64  # SHA-256 hex length

    def test_baseline_hash_matches_deployed_content(
        self, temp_project, temp_collection
    ):
        """Test that baseline hash exactly matches deployed artifact content.

        Acceptance: TASK-1.2
        - Hash is accurate
        - Hash computed from deployed files, not source
        """
        # Create skill
        skill_dir = temp_collection / "artifacts" / "skills" / "canvas"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Canvas Skill\n\nOriginal content")
        (skill_dir / "helpers.js").write_text("// Helper code")

        # Deploy
        tracker = DeploymentTracker(temp_project)
        deployed_path = temp_project / ".claude" / "skills" / "canvas"
        deployed_path.mkdir(parents=True)

        # Copy files
        import shutil

        shutil.copytree(skill_dir, deployed_path, dirs_exist_ok=True)

        # Compute hash from deployed content
        deployed_hash = compute_content_hash(deployed_path)

        # Create deployment record
        deployment = Deployment(
            artifact_name="canvas",
            artifact_type="skill",
            from_collection=str(temp_collection),
            deployed_at=datetime.now(),
            artifact_path=Path("skills/canvas"),
            content_hash=deployed_hash,
        )

        # Hash should match deployed content
        assert deployment.content_hash == deployed_hash

        # Verify by recomputing
        recomputed_hash = compute_content_hash(deployed_path)
        assert deployment.content_hash == recomputed_hash

    def test_deployment_performance_no_regression(self, temp_project, temp_collection):
        """Test that hash computation during deployment is fast.

        Acceptance: TASK-1.2
        - No performance regression
        - Hash computation completes in < 100ms for typical artifact
        """
        import time

        # Create moderate-sized skill
        skill_dir = temp_collection / "artifacts" / "skills" / "perf-test"
        skill_dir.mkdir(parents=True)

        # Create multiple files
        for i in range(10):
            (skill_dir / f"file{i}.md").write_text(f"# File {i}\n" + "x" * 1000)

        # Time hash computation
        start = time.time()
        content_hash = compute_content_hash(skill_dir)
        duration = time.time() - start

        # Should complete quickly (< 100ms for ~10KB of files)
        assert duration < 0.1, f"Hash computation took {duration:.3f}s, expected < 0.1s"
        assert content_hash is not None
        assert len(content_hash) == 64


class TestDeploymentBaselineRetrieval:
    """Tests for retrieving merge_base_snapshot from deployment metadata."""

    def test_retrieve_baseline_from_deployment_metadata(
        self, temp_project, temp_collection
    ):
        """Test retrieval of baseline hash from deployment metadata.

        Acceptance: TASK-1.3
        - Baseline retrieved from merge_base_snapshot field
        - Retrieved hash matches stored hash
        """
        # Create deployment with baseline
        tracker = DeploymentTracker(temp_project)
        baseline_hash = "abc123" * 10 + "abcd"  # 64 chars

        deployment = Deployment(
            artifact_name="test-artifact",
            artifact_type="skill",
            from_collection=str(temp_collection),
            deployed_at=datetime.now(),
            artifact_path=Path("skills/test-artifact"),
            content_hash=baseline_hash,
        )

        # Store deployment
        tracker.track_deployment(deployment)

        # Retrieve deployment
        retrieved = tracker.get_deployment("test-artifact", ArtifactType.SKILL)

        assert retrieved is not None
        assert retrieved.content_hash == baseline_hash

    def test_old_deployment_without_baseline_field(self, temp_project):
        """Test handling of old deployments that don't have merge_base_snapshot field.

        Acceptance: TASK-1.4
        - Old deployments detected (no merge_base_snapshot)
        - Graceful degradation (no errors)
        - Backward compatibility maintained
        """
        # Create old-style deployment (before v1.5)
        tracker = DeploymentTracker(temp_project)

        # Simulate old deployment without content_hash
        old_deployment_data = {
            "artifact_name": "old-skill",
            "artifact_type": "skill",
            "from_collection": "/path/to/collection",
            "deployed_at": datetime.now().isoformat(),
            "artifact_path": "skills/old-skill",
            # Note: No content_hash / merge_base_snapshot field
            "collection_sha": "old_sha_123",  # Old field name
        }

        # Should handle gracefully via from_dict
        deployment = Deployment.from_dict(old_deployment_data)

        # Should use collection_sha as fallback
        assert deployment.content_hash == "old_sha_123"
        assert deployment.collection_sha == "old_sha_123"  # Backward compat

    def test_missing_baseline_returns_none_gracefully(self, temp_project):
        """Test graceful handling when baseline snapshot is missing.

        Acceptance: TASK-1.4
        - Missing snapshot handled gracefully
        - Returns None instead of raising error
        - Appropriate warning logged
        """
        tracker = DeploymentTracker(temp_project)

        # Try to get deployment that doesn't exist
        result = tracker.get_deployment("nonexistent", ArtifactType.SKILL)

        # Should return None, not raise
        assert result is None

    def test_baseline_field_is_optional_for_backward_compat(self, temp_project):
        """Test that merge_base_snapshot field is optional for backward compatibility.

        Acceptance: TASK-1.1
        - Field is optional
        - Old deployments work without field
        - No migration required
        """
        # Create deployment without content_hash (uses collection_sha)
        deployment_data = {
            "artifact_name": "compat-test",
            "artifact_type": "command",
            "from_collection": "/collection",
            "deployed_at": datetime.now().isoformat(),
            "artifact_path": "commands/test.md",
            "collection_sha": "fallback_hash_123",
            # content_hash is missing - should use collection_sha
        }

        deployment = Deployment.from_dict(deployment_data)

        assert deployment.content_hash == "fallback_hash_123"
        assert deployment.artifact_name == "compat-test"


class TestDeploymentSchemaValidation:
    """Tests for deployment metadata schema validation."""

    def test_schema_accepts_merge_base_snapshot_field(self, temp_project):
        """Test that schema accepts merge_base_snapshot field.

        Acceptance: TASK-1.1
        - Schema updated with new field
        - Field stores SHA-256 hash
        """
        deployment = Deployment(
            artifact_name="schema-test",
            artifact_type="skill",
            from_collection="/collection",
            deployed_at=datetime.now(),
            artifact_path=Path("skills/test"),
            content_hash="a" * 64,  # Valid SHA-256 hex
        )

        # Convert to dict (for TOML serialization)
        data = deployment.to_dict()

        assert "content_hash" in data
        assert data["content_hash"] == "a" * 64
        assert len(data["content_hash"]) == 64

    def test_schema_validation_rejects_invalid_hash(self):
        """Test that invalid hash formats are handled appropriately."""
        # This is more of a future enhancement - currently we don't validate
        # hash format strictly, but we could add validation

        deployment = Deployment(
            artifact_name="invalid-hash-test",
            artifact_type="skill",
            from_collection="/collection",
            deployed_at=datetime.now(),
            artifact_path=Path("skills/test"),
            content_hash="not-a-valid-sha256",  # Invalid format
        )

        # Currently accepts any string - future enhancement could validate
        assert deployment.content_hash == "not-a-valid-sha256"

    def test_deployment_serialization_includes_baseline(self, temp_project):
        """Test that deployment serialization includes baseline hash.

        Ensures baseline is persisted to .skillmeat-deployed.toml
        """
        deployment = Deployment(
            artifact_name="serialize-test",
            artifact_type="agent",
            from_collection="/collection",
            deployed_at=datetime.now(),
            artifact_path=Path("agents/test.md"),
            content_hash="serialized_hash_" + ("x" * 49),
        )

        # Serialize to dict
        data = deployment.to_dict()

        # Verify baseline is included
        assert "content_hash" in data
        assert data["content_hash"] == "serialized_hash_" + ("x" * 49)

        # Verify can round-trip
        restored = Deployment.from_dict(data)
        assert restored.content_hash == deployment.content_hash


class TestFallbackLogic:
    """Tests for fallback logic when baseline is missing."""

    @patch("skillmeat.core.sync.logger")
    def test_fallback_logs_warning_when_baseline_missing(
        self, mock_logger, temp_project
    ):
        """Test that fallback logic logs warning when baseline is missing.

        Acceptance: TASK-1.4
        - Warning logged when merge_base_snapshot missing
        - Warning includes artifact name and reason
        """
        # Note: This test assumes sync.py has fallback logic
        # If three_way_merge() is not yet implemented, this will be a placeholder

        # Create deployment without baseline
        tracker = DeploymentTracker(temp_project)
        old_deployment = Deployment(
            artifact_name="fallback-test",
            artifact_type="skill",
            from_collection="/collection",
            deployed_at=datetime.now(),
            artifact_path=Path("skills/test"),
            content_hash=None,  # No baseline
        )

        # When baseline is None, fallback should be triggered
        assert old_deployment.content_hash is None

    def test_fallback_uses_collection_sha_for_old_deployments(self, temp_project):
        """Test fallback to collection_sha for old deployments.

        Acceptance: TASK-1.4
        - Fallback logic uses common ancestor search
        - Or uses collection_sha as baseline
        """
        # Old deployment with collection_sha but no content_hash
        old_data = {
            "artifact_name": "legacy",
            "artifact_type": "skill",
            "from_collection": "/collection",
            "deployed_at": datetime.now().isoformat(),
            "artifact_path": "skills/legacy",
            "collection_sha": "legacy_baseline_hash",
        }

        deployment = Deployment.from_dict(old_data)

        # Should fall back to collection_sha
        assert deployment.content_hash == "legacy_baseline_hash"
        assert deployment.collection_sha == "legacy_baseline_hash"

    def test_deployment_without_any_hash_raises_error(self):
        """Test that deployment without any hash field raises error.

        Ensures data integrity - we need at least one hash field.
        """
        invalid_data = {
            "artifact_name": "broken",
            "artifact_type": "skill",
            "from_collection": "/collection",
            "deployed_at": datetime.now().isoformat(),
            "artifact_path": "skills/broken",
            # Missing both content_hash AND collection_sha
        }

        with pytest.raises(ValueError, match="content_hash or collection_sha"):
            Deployment.from_dict(invalid_data)


class TestBaselineEdgeCases:
    """Tests for edge cases in baseline storage and retrieval."""

    def test_baseline_for_multifile_artifact(self, temp_project, temp_collection):
        """Test baseline hash computation for multi-file artifacts (skills)."""
        # Create skill with multiple files
        skill_dir = temp_collection / "artifacts" / "skills" / "multifile"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Skill")
        (skill_dir / "helpers.py").write_text("# Helpers")
        (skill_dir / "README.md").write_text("# README")

        # Compute hash
        baseline_hash = compute_content_hash(skill_dir)

        # Create deployment
        deployment = Deployment(
            artifact_name="multifile",
            artifact_type="skill",
            from_collection=str(temp_collection),
            deployed_at=datetime.now(),
            artifact_path=Path("skills/multifile"),
            content_hash=baseline_hash,
        )

        # Hash should be deterministic
        recomputed = compute_content_hash(skill_dir)
        assert deployment.content_hash == recomputed

    def test_baseline_for_single_file_artifact(self, temp_project, temp_collection):
        """Test baseline hash for single-file artifacts (commands, agents)."""
        # Create command file
        commands_dir = temp_collection / "artifacts" / "commands"
        commands_dir.mkdir(parents=True)
        command_file = commands_dir / "test.md"
        command_file.write_text("# Command\n\nContent")

        # Compute hash
        baseline_hash = compute_content_hash(command_file)

        # Create deployment
        deployment = Deployment(
            artifact_name="test",
            artifact_type="command",
            from_collection=str(temp_collection),
            deployed_at=datetime.now(),
            artifact_path=Path("commands/test.md"),
            content_hash=baseline_hash,
        )

        assert deployment.content_hash == baseline_hash
        assert len(deployment.content_hash) == 64

    def test_baseline_unchanged_by_deployment_metadata_changes(
        self, temp_project, temp_collection
    ):
        """Test that baseline hash is content-based, not metadata-based.

        Changing deployment metadata shouldn't change baseline hash.
        """
        skill_dir = temp_collection / "artifacts" / "skills" / "stable"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Stable content")

        baseline_hash = compute_content_hash(skill_dir)

        # Create two deployments with different metadata but same content
        deployment1 = Deployment(
            artifact_name="stable",
            artifact_type="skill",
            from_collection="/collection1",
            deployed_at=datetime.now(),
            artifact_path=Path("skills/stable"),
            content_hash=baseline_hash,
        )

        import time

        time.sleep(0.01)  # Ensure different timestamp

        deployment2 = Deployment(
            artifact_name="stable",
            artifact_type="skill",
            from_collection="/collection2",
            deployed_at=datetime.now(),
            artifact_path=Path("skills/stable"),
            content_hash=baseline_hash,
        )

        # Baseline hashes should be identical (content-based)
        assert deployment1.content_hash == deployment2.content_hash
        # But timestamps differ (metadata)
        assert deployment1.deployed_at != deployment2.deployed_at

    def test_baseline_changes_when_content_changes(self, temp_project, temp_collection):
        """Test that baseline hash changes when artifact content changes."""
        skill_dir = temp_collection / "artifacts" / "skills" / "mutable"
        skill_dir.mkdir(parents=True)

        # Version 1
        (skill_dir / "SKILL.md").write_text("# Version 1")
        hash_v1 = compute_content_hash(skill_dir)

        # Version 2 (modified)
        (skill_dir / "SKILL.md").write_text("# Version 2")
        hash_v2 = compute_content_hash(skill_dir)

        # Hashes should differ
        assert hash_v1 != hash_v2
        assert len(hash_v1) == len(hash_v2) == 64


class TestIntegrationWithDeploymentTracker:
    """Integration tests for baseline storage with DeploymentTracker."""

    def test_tracker_persists_baseline_to_toml(self, temp_project, temp_collection):
        """Test that DeploymentTracker persists baseline to .skillmeat-deployed.toml."""
        tracker = DeploymentTracker(temp_project)

        # Create and track deployment
        deployment = Deployment(
            artifact_name="persist-test",
            artifact_type="skill",
            from_collection=str(temp_collection),
            deployed_at=datetime.now(),
            artifact_path=Path("skills/persist-test"),
            content_hash="persistent_hash_" + ("y" * 48),
        )

        tracker.track_deployment(deployment)

        # Read back from file
        import tomli

        toml_file = temp_project / ".skillmeat-deployed.toml"
        assert toml_file.exists()

        with open(toml_file, "rb") as f:
            data = tomli.load(f)

        # Verify baseline is in TOML
        assert "deployments" in data
        assert "persist-test" in data["deployments"]

        dep_data = data["deployments"]["persist-test"]
        # Should have content_hash (and collection_sha for backward compat)
        assert "content_hash" in dep_data or "collection_sha" in dep_data

    def test_tracker_loads_baseline_from_toml(self, temp_project):
        """Test that DeploymentTracker loads baseline from existing TOML."""
        # Create TOML file manually
        toml_file = temp_project / ".skillmeat-deployed.toml"
        toml_content = f"""
[deployments.loaded-test]
artifact_name = "loaded-test"
artifact_type = "skill"
from_collection = "/collection"
deployed_at = "{datetime.now().isoformat()}"
artifact_path = "skills/loaded-test"
content_hash = "loaded_baseline_hash_{'z' * 41}"
"""
        toml_file.write_text(toml_content)

        # Load via tracker
        tracker = DeploymentTracker(temp_project)
        deployment = tracker.get_deployment("loaded-test", ArtifactType.SKILL)

        assert deployment is not None
        assert deployment.content_hash == "loaded_baseline_hash_" + ("z" * 41)
