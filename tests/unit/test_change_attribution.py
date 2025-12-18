"""Unit tests for change origin attribution in drift detection.

Tests the determine_change_origin() function and change_origin field
population in DriftDetectionResult objects.
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from skillmeat.core.sync import SyncManager
from skillmeat.models import DriftDetectionResult, DeploymentMetadata, DeploymentRecord


class TestDetermineChangeOrigin:
    """Test determine_change_origin() drift type mapping."""

    @pytest.fixture
    def sync_manager(self):
        """Create SyncManager instance for testing."""
        return SyncManager(
            collection_manager=Mock(),
            artifact_manager=Mock(),
        )

    def test_modified_drift_returns_local_modification(self, sync_manager):
        """Test that 'modified' drift type maps to 'local_modification' origin."""
        result = sync_manager.determine_change_origin("modified")
        assert result == "local_modification"

    def test_outdated_drift_returns_sync(self, sync_manager):
        """Test that 'outdated' drift type maps to 'sync' origin."""
        result = sync_manager.determine_change_origin("outdated")
        assert result == "sync"

    def test_conflict_drift_returns_local_modification(self, sync_manager):
        """Test that 'conflict' drift type maps to 'local_modification' origin.

        Conflicts are attributed to local_modification because local changes
        are prioritized for version tracking when both sides changed.
        """
        result = sync_manager.determine_change_origin("conflict")
        assert result == "local_modification"

    def test_added_drift_returns_sync(self, sync_manager):
        """Test that 'added' drift type maps to 'sync' origin."""
        result = sync_manager.determine_change_origin("added")
        assert result == "sync"

    def test_removed_drift_returns_sync(self, sync_manager):
        """Test that 'removed' drift type maps to 'sync' origin."""
        result = sync_manager.determine_change_origin("removed")
        assert result == "sync"

    def test_version_mismatch_drift_returns_sync(self, sync_manager):
        """Test that 'version_mismatch' drift type maps to 'sync' origin."""
        result = sync_manager.determine_change_origin("version_mismatch")
        assert result == "sync"

    def test_unknown_drift_type_returns_none(self, sync_manager):
        """Test that unknown drift type returns None."""
        result = sync_manager.determine_change_origin("unknown_type")
        assert result is None

    def test_all_valid_drift_types_have_mappings(self, sync_manager):
        """Test that all valid drift types have change_origin mappings."""
        # Valid drift types from DriftDetectionResult model
        valid_drift_types = [
            "modified",
            "outdated",
            "conflict",
            "added",
            "removed",
            "version_mismatch",
        ]

        for drift_type in valid_drift_types:
            result = sync_manager.determine_change_origin(drift_type)
            assert (
                result is not None
            ), f"Drift type '{drift_type}' has no change_origin mapping"
            assert result in [
                "local_modification",
                "sync",
                "deployment",
            ], f"Drift type '{drift_type}' maps to invalid origin '{result}'"


class TestDriftAttributionFields:
    """Test that drift detection populates attribution fields correctly."""

    @pytest.fixture
    def sync_manager(self):
        """Create SyncManager instance for testing."""
        return SyncManager(
            collection_manager=Mock(),
            artifact_manager=Mock(),
        )

    def test_modified_drift_sets_change_origin(self, sync_manager, tmp_path):
        """Test that check_drift() sets change_origin for 'modified' drift."""
        # Setup project structure
        project_path = tmp_path / "project"
        project_path.mkdir()
        claude_dir = project_path / ".claude"
        claude_dir.mkdir()
        skills_dir = claude_dir / "skills"
        skills_dir.mkdir()

        # Create modified artifact
        artifact_dir = skills_dir / "test-skill"
        artifact_dir.mkdir()
        (artifact_dir / "SKILL.md").write_text("Modified content")

        # Mock deployment metadata
        with patch.object(sync_manager, "_load_deployment_metadata") as mock_load:
            deployment_record = DeploymentRecord(
                name="test-skill",
                artifact_type="skill",
                source="local:test",
                version="1.0.0",
                sha="abc123def456" + "0" * 52,  # Original deployed hash
                deployed_at=datetime.now().isoformat() + "Z",
                deployed_from=str(tmp_path / "collection"),
            )

            mock_metadata = DeploymentMetadata(
                collection="default",
                deployed_at=datetime.now().isoformat() + "Z",
                skillmeat_version="0.3.0",
                artifacts=[deployment_record],
            )
            mock_load.return_value = mock_metadata

            # Mock collection artifacts
            with patch.object(sync_manager, "_get_collection_artifacts") as mock_get:
                mock_get.return_value = [
                    {
                        "name": "test-skill",
                        "type": "skill",
                        "path": tmp_path / "collection" / "skills" / "test-skill",
                        "version": "1.0.0",
                    }
                ]

                # Mock hash computation
                with patch.object(sync_manager, "_compute_artifact_hash") as mock_hash:
                    # Collection unchanged, project modified
                    mock_hash.side_effect = [
                        "abc123def456" + "0" * 52,  # Collection SHA (same as deployed)
                        "modified1234" + "0" * 52,  # Project SHA (different)
                    ]

                    # Execute drift detection
                    drift_results = sync_manager.check_drift(project_path)

                    # Verify change_origin is set
                    assert len(drift_results) == 1
                    drift = drift_results[0]

                    assert drift.drift_type == "modified"
                    assert drift.change_origin == "local_modification"

    def test_outdated_drift_sets_change_origin(self, sync_manager, tmp_path):
        """Test that check_drift() sets change_origin for 'outdated' drift."""
        # Setup project structure
        project_path = tmp_path / "project"
        project_path.mkdir()
        claude_dir = project_path / ".claude"
        claude_dir.mkdir()
        skills_dir = claude_dir / "skills"
        skills_dir.mkdir()

        # Create artifact (unchanged in project)
        artifact_dir = skills_dir / "test-skill"
        artifact_dir.mkdir()
        (artifact_dir / "SKILL.md").write_text("Original content")

        # Mock deployment metadata
        with patch.object(sync_manager, "_load_deployment_metadata") as mock_load:
            deployment_record = DeploymentRecord(
                name="test-skill",
                artifact_type="skill",
                source="local:test",
                version="1.0.0",
                sha="abc123def456" + "0" * 52,
                deployed_at=datetime.now().isoformat() + "Z",
                deployed_from=str(tmp_path / "collection"),
            )

            mock_metadata = DeploymentMetadata(
                collection="default",
                deployed_at=datetime.now().isoformat() + "Z",
                skillmeat_version="0.3.0",
                artifacts=[deployment_record],
            )
            mock_load.return_value = mock_metadata

            # Mock collection artifacts
            with patch.object(sync_manager, "_get_collection_artifacts") as mock_get:
                mock_get.return_value = [
                    {
                        "name": "test-skill",
                        "type": "skill",
                        "path": tmp_path / "collection" / "skills" / "test-skill",
                        "version": "1.0.0",
                    }
                ]

                # Mock hash computation
                with patch.object(sync_manager, "_compute_artifact_hash") as mock_hash:
                    # Collection updated, project unchanged
                    mock_hash.side_effect = [
                        "updated12345" + "0" * 52,  # Collection SHA (different)
                        "abc123def456" + "0" * 52,  # Project SHA (same as deployed)
                    ]

                    # Execute drift detection
                    drift_results = sync_manager.check_drift(project_path)

                    # Verify change_origin is set
                    assert len(drift_results) == 1
                    drift = drift_results[0]

                    assert drift.drift_type == "outdated"
                    assert drift.change_origin == "sync"

    def test_conflict_drift_sets_change_origin(self, sync_manager, tmp_path):
        """Test that check_drift() sets change_origin for 'conflict' drift."""
        # Setup project structure
        project_path = tmp_path / "project"
        project_path.mkdir()
        claude_dir = project_path / ".claude"
        claude_dir.mkdir()
        skills_dir = claude_dir / "skills"
        skills_dir.mkdir()

        # Create modified artifact
        artifact_dir = skills_dir / "test-skill"
        artifact_dir.mkdir()
        (artifact_dir / "SKILL.md").write_text("Modified locally")

        # Mock deployment metadata
        with patch.object(sync_manager, "_load_deployment_metadata") as mock_load:
            deployment_record = DeploymentRecord(
                name="test-skill",
                artifact_type="skill",
                source="local:test",
                version="1.0.0",
                sha="abc123def456" + "0" * 52,
                deployed_at=datetime.now().isoformat() + "Z",
                deployed_from=str(tmp_path / "collection"),
            )

            mock_metadata = DeploymentMetadata(
                collection="default",
                deployed_at=datetime.now().isoformat() + "Z",
                skillmeat_version="0.3.0",
                artifacts=[deployment_record],
            )
            mock_load.return_value = mock_metadata

            # Mock collection artifacts
            with patch.object(sync_manager, "_get_collection_artifacts") as mock_get:
                mock_get.return_value = [
                    {
                        "name": "test-skill",
                        "type": "skill",
                        "path": tmp_path / "collection" / "skills" / "test-skill",
                        "version": "1.0.0",
                    }
                ]

                # Mock hash computation
                with patch.object(sync_manager, "_compute_artifact_hash") as mock_hash:
                    # Both collection and project modified (conflict)
                    mock_hash.side_effect = [
                        "updated12345" + "0" * 52,  # Collection SHA (different)
                        "modified1234" + "0" * 52,  # Project SHA (different)
                    ]

                    # Execute drift detection
                    drift_results = sync_manager.check_drift(project_path)

                    # Verify change_origin is set (prioritizes local)
                    assert len(drift_results) == 1
                    drift = drift_results[0]

                    assert drift.drift_type == "conflict"
                    assert drift.change_origin == "local_modification"

    def test_baseline_hash_set_to_deployed_sha(self, sync_manager, tmp_path):
        """Test that baseline_hash is set to deployed SHA (merge base)."""
        # Setup project structure
        project_path = tmp_path / "project"
        project_path.mkdir()
        claude_dir = project_path / ".claude"
        claude_dir.mkdir()
        skills_dir = claude_dir / "skills"
        skills_dir.mkdir()

        # Create modified artifact
        artifact_dir = skills_dir / "test-skill"
        artifact_dir.mkdir()
        (artifact_dir / "SKILL.md").write_text("Modified content")

        deployed_sha = "abc123def456" + "0" * 52

        # Mock deployment metadata
        with patch.object(sync_manager, "_load_deployment_metadata") as mock_load:
            deployment_record = DeploymentRecord(
                name="test-skill",
                artifact_type="skill",
                source="local:test",
                version="1.0.0",
                sha=deployed_sha,
                deployed_at=datetime.now().isoformat() + "Z",
                deployed_from=str(tmp_path / "collection"),
            )

            mock_metadata = DeploymentMetadata(
                collection="default",
                deployed_at=datetime.now().isoformat() + "Z",
                skillmeat_version="0.3.0",
                artifacts=[deployment_record],
            )
            mock_load.return_value = mock_metadata

            # Mock collection artifacts
            with patch.object(sync_manager, "_get_collection_artifacts") as mock_get:
                mock_get.return_value = [
                    {
                        "name": "test-skill",
                        "type": "skill",
                        "path": tmp_path / "collection" / "skills" / "test-skill",
                        "version": "1.0.0",
                    }
                ]

                # Mock hash computation
                with patch.object(sync_manager, "_compute_artifact_hash") as mock_hash:
                    mock_hash.side_effect = [
                        "abc123def456" + "0" * 52,  # Collection SHA
                        "modified1234" + "0" * 52,  # Project SHA
                    ]

                    # Execute drift detection
                    drift_results = sync_manager.check_drift(project_path)

                    # Verify baseline_hash is the deployed SHA
                    assert len(drift_results) == 1
                    drift = drift_results[0]

                    assert drift.baseline_hash == deployed_sha

    def test_current_hash_set_to_project_sha(self, sync_manager, tmp_path):
        """Test that current_hash is set to current project SHA."""
        # Setup project structure
        project_path = tmp_path / "project"
        project_path.mkdir()
        claude_dir = project_path / ".claude"
        claude_dir.mkdir()
        skills_dir = claude_dir / "skills"
        skills_dir.mkdir()

        # Create modified artifact
        artifact_dir = skills_dir / "test-skill"
        artifact_dir.mkdir()
        (artifact_dir / "SKILL.md").write_text("Modified content")

        current_project_sha = "modified1234" + "0" * 52

        # Mock deployment metadata
        with patch.object(sync_manager, "_load_deployment_metadata") as mock_load:
            deployment_record = DeploymentRecord(
                name="test-skill",
                artifact_type="skill",
                source="local:test",
                version="1.0.0",
                sha="abc123def456" + "0" * 52,
                deployed_at=datetime.now().isoformat() + "Z",
                deployed_from=str(tmp_path / "collection"),
            )

            mock_metadata = DeploymentMetadata(
                collection="default",
                deployed_at=datetime.now().isoformat() + "Z",
                skillmeat_version="0.3.0",
                artifacts=[deployment_record],
            )
            mock_load.return_value = mock_metadata

            # Mock collection artifacts
            with patch.object(sync_manager, "_get_collection_artifacts") as mock_get:
                mock_get.return_value = [
                    {
                        "name": "test-skill",
                        "type": "skill",
                        "path": tmp_path / "collection" / "skills" / "test-skill",
                        "version": "1.0.0",
                    }
                ]

                # Mock hash computation
                with patch.object(sync_manager, "_compute_artifact_hash") as mock_hash:
                    mock_hash.side_effect = [
                        "abc123def456" + "0" * 52,  # Collection SHA
                        current_project_sha,  # Project SHA
                    ]

                    # Execute drift detection
                    drift_results = sync_manager.check_drift(project_path)

                    # Verify current_hash is the project SHA
                    assert len(drift_results) == 1
                    drift = drift_results[0]

                    assert drift.current_hash == current_project_sha


class TestDriftSummaryCalculation:
    """Test drift summary calculation with change_origin attribution."""

    def test_calculate_drift_summary_upstream_changes(self):
        """Test drift summary correctly counts upstream changes."""
        drift_results = [
            DriftDetectionResult(
                artifact_name="skill1",
                artifact_type="skill",
                drift_type="outdated",
                change_origin="sync",
                recommendation="pull_from_collection",
            ),
            DriftDetectionResult(
                artifact_name="skill2",
                artifact_type="skill",
                drift_type="added",
                change_origin="sync",
                recommendation="deploy_to_project",
            ),
            DriftDetectionResult(
                artifact_name="skill3",
                artifact_type="skill",
                drift_type="removed",
                change_origin="sync",
                recommendation="remove_from_project",
            ),
        ]

        # Calculate upstream changes (change_origin == "sync")
        upstream_changes = [d for d in drift_results if d.change_origin == "sync"]

        assert len(upstream_changes) == 3

    def test_calculate_drift_summary_local_changes(self):
        """Test drift summary correctly counts local changes."""
        drift_results = [
            DriftDetectionResult(
                artifact_name="skill1",
                artifact_type="skill",
                drift_type="modified",
                change_origin="local_modification",
                recommendation="push_to_collection",
            ),
            DriftDetectionResult(
                artifact_name="skill2",
                artifact_type="skill",
                drift_type="modified",
                change_origin="local_modification",
                recommendation="push_to_collection",
            ),
        ]

        # Calculate local changes (change_origin == "local_modification")
        local_changes = [
            d for d in drift_results if d.change_origin == "local_modification"
        ]

        assert len(local_changes) == 2

    def test_calculate_drift_summary_conflicts(self):
        """Test drift summary correctly counts conflicts."""
        drift_results = [
            DriftDetectionResult(
                artifact_name="skill1",
                artifact_type="skill",
                drift_type="conflict",
                change_origin="local_modification",
                recommendation="review_manually",
            ),
            DriftDetectionResult(
                artifact_name="skill2",
                artifact_type="skill",
                drift_type="conflict",
                change_origin="local_modification",
                recommendation="review_manually",
            ),
        ]

        # Calculate conflicts (drift_type == "conflict")
        conflicts = [d for d in drift_results if d.drift_type == "conflict"]

        assert len(conflicts) == 2

    def test_calculate_drift_summary_mixed_changes(self):
        """Test drift summary with mix of upstream, local, and conflicts."""
        drift_results = [
            # Upstream changes
            DriftDetectionResult(
                artifact_name="skill1",
                artifact_type="skill",
                drift_type="outdated",
                change_origin="sync",
                recommendation="pull_from_collection",
            ),
            DriftDetectionResult(
                artifact_name="skill2",
                artifact_type="skill",
                drift_type="added",
                change_origin="sync",
                recommendation="deploy_to_project",
            ),
            # Local changes
            DriftDetectionResult(
                artifact_name="skill3",
                artifact_type="skill",
                drift_type="modified",
                change_origin="local_modification",
                recommendation="push_to_collection",
            ),
            # Conflicts
            DriftDetectionResult(
                artifact_name="skill4",
                artifact_type="skill",
                drift_type="conflict",
                change_origin="local_modification",
                recommendation="review_manually",
            ),
        ]

        # Calculate each category
        upstream_changes = [d for d in drift_results if d.change_origin == "sync"]
        local_changes = [
            d
            for d in drift_results
            if d.change_origin == "local_modification" and d.drift_type != "conflict"
        ]
        conflicts = [d for d in drift_results if d.drift_type == "conflict"]

        assert len(upstream_changes) == 2
        assert len(local_changes) == 1
        assert len(conflicts) == 1
        assert len(drift_results) == 4  # Total count

    def test_drift_summary_empty_list(self):
        """Test drift summary with empty drift list."""
        drift_results = []

        upstream_changes = [d for d in drift_results if d.change_origin == "sync"]
        local_changes = [
            d for d in drift_results if d.change_origin == "local_modification"
        ]
        conflicts = [d for d in drift_results if d.drift_type == "conflict"]

        assert len(upstream_changes) == 0
        assert len(local_changes) == 0
        assert len(conflicts) == 0
        assert len(drift_results) == 0


class TestChangeOriginValidation:
    """Test change_origin field validation in DriftDetectionResult."""

    def test_valid_change_origins(self):
        """Test that valid change_origin values are accepted."""
        valid_origins = ["deployment", "sync", "local_modification"]

        for origin in valid_origins:
            drift = DriftDetectionResult(
                artifact_name="test",
                artifact_type="skill",
                drift_type="modified",
                change_origin=origin,
                recommendation="review_manually",
            )
            assert drift.change_origin == origin

    def test_invalid_change_origin_raises_error(self):
        """Test that invalid change_origin raises ValueError."""
        with pytest.raises(ValueError, match="Invalid change_origin"):
            DriftDetectionResult(
                artifact_name="test",
                artifact_type="skill",
                drift_type="modified",
                change_origin="invalid_origin",
                recommendation="review_manually",
            )

    def test_none_change_origin_is_allowed(self):
        """Test that None is allowed for change_origin (optional field)."""
        drift = DriftDetectionResult(
            artifact_name="test",
            artifact_type="skill",
            drift_type="modified",
            change_origin=None,
            recommendation="review_manually",
        )
        assert drift.change_origin is None
