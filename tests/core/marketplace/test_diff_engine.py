"""Tests for catalog diff engine."""

import pytest

from skillmeat.api.schemas.marketplace import DetectedArtifact
from skillmeat.core.marketplace.diff_engine import (
    CatalogDiffEngine,
    ChangeType,
    DiffEntry,
    DiffResult,
    compute_catalog_diff,
)


class TestDiffEngine:
    """Test suite for CatalogDiffEngine."""

    def test_compute_diff_all_new_entries(self):
        """Test diff when all artifacts are new."""
        existing = []
        new_artifacts = [
            DetectedArtifact(
                artifact_type="skill",
                name="skill-a",
                path="skills/skill-a",
                upstream_url="https://github.com/user/repo/skills/skill-a",
                detected_sha="sha1",
                confidence_score=90,
            ),
            DetectedArtifact(
                artifact_type="command",
                name="cmd-b",
                path="commands/cmd-b",
                upstream_url="https://github.com/user/repo/commands/cmd-b",
                detected_sha="sha2",
                confidence_score=85,
            ),
        ]

        result = compute_catalog_diff(existing, new_artifacts, "source-123")

        assert len(result.new_entries) == 2
        assert len(result.updated_entries) == 0
        assert len(result.removed_entries) == 0
        assert len(result.unchanged_entries) == 0
        assert result.total_changes == 2
        assert result.summary["new"] == 2

    def test_compute_diff_all_removed_entries(self):
        """Test diff when all existing entries are removed."""
        existing = [
            {
                "id": "e1",
                "upstream_url": "https://github.com/user/repo/skills/skill-a",
                "detected_sha": "sha1",
                "artifact_type": "skill",
                "name": "skill-a",
                "path": "skills/skill-a",
            },
            {
                "id": "e2",
                "upstream_url": "https://github.com/user/repo/commands/cmd-b",
                "detected_sha": "sha2",
                "artifact_type": "command",
                "name": "cmd-b",
                "path": "commands/cmd-b",
            },
        ]
        new_artifacts = []

        result = compute_catalog_diff(existing, new_artifacts, "source-123")

        assert len(result.new_entries) == 0
        assert len(result.updated_entries) == 0
        assert len(result.removed_entries) == 2
        assert len(result.unchanged_entries) == 0
        assert result.total_changes == 2
        assert result.summary["removed"] == 2

    def test_compute_diff_all_unchanged_entries(self):
        """Test diff when all entries are unchanged."""
        existing = [
            {
                "id": "e1",
                "upstream_url": "https://github.com/user/repo/skills/skill-a",
                "detected_sha": "sha1",
                "artifact_type": "skill",
                "name": "skill-a",
                "path": "skills/skill-a",
            },
        ]
        new_artifacts = [
            DetectedArtifact(
                artifact_type="skill",
                name="skill-a",
                path="skills/skill-a",
                upstream_url="https://github.com/user/repo/skills/skill-a",
                detected_sha="sha1",  # Same SHA
                confidence_score=90,
            ),
        ]

        result = compute_catalog_diff(existing, new_artifacts, "source-123")

        assert len(result.new_entries) == 0
        assert len(result.updated_entries) == 0
        assert len(result.removed_entries) == 0
        assert len(result.unchanged_entries) == 1
        assert result.total_changes == 0
        assert result.summary["unchanged"] == 1

    def test_compute_diff_updated_entries(self):
        """Test diff when entries have updated SHAs."""
        existing = [
            {
                "id": "e1",
                "upstream_url": "https://github.com/user/repo/skills/skill-a",
                "detected_sha": "sha1-old",
                "detected_version": "v1.0.0",
                "artifact_type": "skill",
                "name": "skill-a",
                "path": "skills/skill-a",
            },
        ]
        new_artifacts = [
            DetectedArtifact(
                artifact_type="skill",
                name="skill-a",
                path="skills/skill-a",
                upstream_url="https://github.com/user/repo/skills/skill-a",
                detected_sha="sha1-new",  # Different SHA
                detected_version="v2.0.0",
                confidence_score=90,
            ),
        ]

        result = compute_catalog_diff(existing, new_artifacts, "source-123")

        assert len(result.new_entries) == 0
        assert len(result.updated_entries) == 1
        assert len(result.removed_entries) == 0
        assert len(result.unchanged_entries) == 0
        assert result.total_changes == 1

        updated = result.updated_entries[0]
        assert updated.change_type == ChangeType.UPDATED
        assert updated.old_sha == "sha1-old"
        assert updated.new_sha == "sha1-new"
        assert updated.old_version == "v1.0.0"
        assert updated.new_version == "v2.0.0"
        assert updated.existing_entry_id == "e1"

    def test_compute_diff_mixed_changes(self):
        """Test diff with new, updated, removed, and unchanged entries."""
        existing = [
            {
                "id": "e1",
                "upstream_url": "https://github.com/user/repo/skills/unchanged",
                "detected_sha": "sha1",
                "artifact_type": "skill",
                "name": "unchanged",
                "path": "skills/unchanged",
            },
            {
                "id": "e2",
                "upstream_url": "https://github.com/user/repo/skills/updated",
                "detected_sha": "sha2-old",
                "artifact_type": "skill",
                "name": "updated",
                "path": "skills/updated",
            },
            {
                "id": "e3",
                "upstream_url": "https://github.com/user/repo/skills/removed",
                "detected_sha": "sha3",
                "artifact_type": "skill",
                "name": "removed",
                "path": "skills/removed",
            },
        ]
        new_artifacts = [
            DetectedArtifact(
                artifact_type="skill",
                name="unchanged",
                path="skills/unchanged",
                upstream_url="https://github.com/user/repo/skills/unchanged",
                detected_sha="sha1",  # Same
                confidence_score=90,
            ),
            DetectedArtifact(
                artifact_type="skill",
                name="updated",
                path="skills/updated",
                upstream_url="https://github.com/user/repo/skills/updated",
                detected_sha="sha2-new",  # Updated
                confidence_score=85,
            ),
            DetectedArtifact(
                artifact_type="skill",
                name="new",
                path="skills/new",
                upstream_url="https://github.com/user/repo/skills/new",
                detected_sha="sha4",  # New
                confidence_score=95,
            ),
            # Note: "removed" is missing
        ]

        result = compute_catalog_diff(existing, new_artifacts, "source-123")

        assert len(result.new_entries) == 1
        assert len(result.updated_entries) == 1
        assert len(result.removed_entries) == 1
        assert len(result.unchanged_entries) == 1
        assert result.total_changes == 3
        assert result.summary == {
            "new": 1,
            "updated": 1,
            "removed": 1,
            "unchanged": 1,
            "total": 4,
        }

    def test_compute_diff_empty_sha_not_updated(self):
        """Test that empty new SHA doesn't trigger update."""
        existing = [
            {
                "id": "e1",
                "upstream_url": "https://github.com/user/repo/skills/skill-a",
                "detected_sha": "sha1",
                "artifact_type": "skill",
                "name": "skill-a",
                "path": "skills/skill-a",
            },
        ]
        new_artifacts = [
            DetectedArtifact(
                artifact_type="skill",
                name="skill-a",
                path="skills/skill-a",
                upstream_url="https://github.com/user/repo/skills/skill-a",
                detected_sha=None,  # Empty SHA
                confidence_score=90,
            ),
        ]

        result = compute_catalog_diff(existing, new_artifacts, "source-123")

        # Should be unchanged because new_sha is empty
        assert len(result.updated_entries) == 0
        assert len(result.unchanged_entries) == 1

    def test_diff_entry_new_data_includes_source_id(self):
        """Test that new_data dict includes source_id."""
        existing = []
        new_artifacts = [
            DetectedArtifact(
                artifact_type="skill",
                name="test-skill",
                path="skills/test-skill",
                upstream_url="https://github.com/user/repo/skills/test-skill",
                detected_sha="sha1",
                detected_version="v1.0.0",
                confidence_score=95,
                metadata={"description": "Test skill"},
            ),
        ]

        result = compute_catalog_diff(existing, new_artifacts, "source-123")

        assert len(result.new_entries) == 1
        new_data = result.new_entries[0].new_data
        assert new_data is not None
        assert new_data["source_id"] == "source-123"
        assert new_data["artifact_type"] == "skill"
        assert new_data["name"] == "test-skill"
        assert new_data["path"] == "skills/test-skill"
        assert (
            new_data["upstream_url"] == "https://github.com/user/repo/skills/test-skill"
        )
        assert new_data["detected_sha"] == "sha1"
        assert new_data["detected_version"] == "v1.0.0"
        assert new_data["confidence_score"] == 95
        assert new_data["metadata"] == {"description": "Test skill"}

    def test_to_catalog_diff_conversion(self):
        """Test conversion from DiffResult to CatalogDiff."""
        existing = [
            {
                "id": "e1",
                "upstream_url": "https://github.com/user/repo/skills/updated",
                "detected_sha": "sha1-old",
                "artifact_type": "skill",
                "name": "updated",
                "path": "skills/updated",
            },
            {
                "id": "e2",
                "upstream_url": "https://github.com/user/repo/skills/removed",
                "detected_sha": "sha2",
                "artifact_type": "skill",
                "name": "removed",
                "path": "skills/removed",
            },
            {
                "id": "e3",
                "upstream_url": "https://github.com/user/repo/skills/unchanged",
                "detected_sha": "sha3",
                "artifact_type": "skill",
                "name": "unchanged",
                "path": "skills/unchanged",
            },
        ]
        new_artifacts = [
            DetectedArtifact(
                artifact_type="skill",
                name="new",
                path="skills/new",
                upstream_url="https://github.com/user/repo/skills/new",
                detected_sha="sha4",
                confidence_score=90,
            ),
            DetectedArtifact(
                artifact_type="skill",
                name="updated",
                path="skills/updated",
                upstream_url="https://github.com/user/repo/skills/updated",
                detected_sha="sha1-new",
                confidence_score=85,
            ),
            DetectedArtifact(
                artifact_type="skill",
                name="unchanged",
                path="skills/unchanged",
                upstream_url="https://github.com/user/repo/skills/unchanged",
                detected_sha="sha3",
                confidence_score=95,
            ),
        ]

        result = compute_catalog_diff(existing, new_artifacts, "source-123")
        catalog_diff = result.to_catalog_diff()

        # Verify structure
        assert len(catalog_diff.new) == 1
        assert len(catalog_diff.updated) == 1
        assert len(catalog_diff.removed) == 1
        assert len(catalog_diff.unchanged) == 1

        # Verify new entries are dicts
        assert isinstance(catalog_diff.new[0], dict)
        assert catalog_diff.new[0]["name"] == "new"

        # Verify updated entries are (id, dict) tuples
        assert isinstance(catalog_diff.updated[0], tuple)
        assert catalog_diff.updated[0][0] == "e1"
        assert isinstance(catalog_diff.updated[0][1], dict)
        assert catalog_diff.updated[0][1]["name"] == "updated"

        # Verify removed entries are IDs
        assert catalog_diff.removed == ["e2"]

        # Verify unchanged entries are IDs
        assert catalog_diff.unchanged == ["e3"]

    def test_diff_entry_change_types(self):
        """Test that DiffEntry has correct change types."""
        new_entry = DiffEntry(
            change_type=ChangeType.NEW,
            upstream_url="https://github.com/test",
            artifact_type="skill",
            name="test",
            path="test",
        )
        assert new_entry.change_type == ChangeType.NEW

        updated_entry = DiffEntry(
            change_type=ChangeType.UPDATED,
            upstream_url="https://github.com/test",
            artifact_type="skill",
            name="test",
            path="test",
        )
        assert updated_entry.change_type == ChangeType.UPDATED

        removed_entry = DiffEntry(
            change_type=ChangeType.REMOVED,
            upstream_url="https://github.com/test",
            artifact_type="skill",
            name="test",
            path="test",
        )
        assert removed_entry.change_type == ChangeType.REMOVED

        unchanged_entry = DiffEntry(
            change_type=ChangeType.UNCHANGED,
            upstream_url="https://github.com/test",
            artifact_type="skill",
            name="test",
            path="test",
        )
        assert unchanged_entry.change_type == ChangeType.UNCHANGED

    def test_diff_result_summary_counts(self):
        """Test that DiffResult summary provides correct counts."""
        result = DiffResult()
        result.new_entries.append(
            DiffEntry(
                change_type=ChangeType.NEW,
                upstream_url="https://github.com/test/1",
                artifact_type="skill",
                name="new1",
                path="new1",
            )
        )
        result.updated_entries.extend(
            [
                DiffEntry(
                    change_type=ChangeType.UPDATED,
                    upstream_url="https://github.com/test/2",
                    artifact_type="skill",
                    name="updated1",
                    path="updated1",
                ),
                DiffEntry(
                    change_type=ChangeType.UPDATED,
                    upstream_url="https://github.com/test/3",
                    artifact_type="skill",
                    name="updated2",
                    path="updated2",
                ),
            ]
        )
        result.removed_entries.append(
            DiffEntry(
                change_type=ChangeType.REMOVED,
                upstream_url="https://github.com/test/4",
                artifact_type="skill",
                name="removed1",
                path="removed1",
            )
        )
        result.unchanged_entries.extend(
            [
                DiffEntry(
                    change_type=ChangeType.UNCHANGED,
                    upstream_url="https://github.com/test/5",
                    artifact_type="skill",
                    name="unchanged1",
                    path="unchanged1",
                ),
                DiffEntry(
                    change_type=ChangeType.UNCHANGED,
                    upstream_url="https://github.com/test/6",
                    artifact_type="skill",
                    name="unchanged2",
                    path="unchanged2",
                ),
                DiffEntry(
                    change_type=ChangeType.UNCHANGED,
                    upstream_url="https://github.com/test/7",
                    artifact_type="skill",
                    name="unchanged3",
                    path="unchanged3",
                ),
            ]
        )

        assert result.total_changes == 4  # 1 new + 2 updated + 1 removed
        assert result.summary == {
            "new": 1,
            "updated": 2,
            "removed": 1,
            "unchanged": 3,
            "total": 7,
        }

    def test_convenience_function(self):
        """Test compute_catalog_diff convenience function."""
        existing = []
        new_artifacts = [
            DetectedArtifact(
                artifact_type="skill",
                name="test",
                path="test",
                upstream_url="https://github.com/user/repo/test",
                detected_sha="sha1",
                confidence_score=90,
            ),
        ]

        # Should work the same as using CatalogDiffEngine directly
        result = compute_catalog_diff(existing, new_artifacts, "source-123")
        assert len(result.new_entries) == 1
