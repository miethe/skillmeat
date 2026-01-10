"""Integration test for discovery timestamp tracking.

Tests end-to-end flow:
1. Discover artifacts for first time → get current timestamp
2. Import artifacts (creates lockfile entries)
3. Re-discover same artifacts → timestamps preserved
4. Modify artifact → timestamp updates
"""

import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType
from skillmeat.core.collection import Collection
from skillmeat.core.discovery import ArtifactDiscoveryService
from skillmeat.storage.lockfile import LockEntry, LockManager
from skillmeat.utils.filesystem import compute_content_hash


def create_test_skill(skill_dir: Path, name: str, content: str = "Test content"):
    """Create a test skill artifact."""
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"""---
name: {name}
description: Test skill {name}
---
# {name}

{content}
"""
    )


def test_discovery_timestamp_end_to_end():
    """Test complete discovery timestamp tracking flow."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir) / "project"
        project.mkdir()
        claude_dir = project / ".claude" / "skills"
        claude_dir.mkdir(parents=True)

        # Step 1: Create skills
        skill1_dir = claude_dir / "skill-1"
        skill2_dir = claude_dir / "skill-2"
        create_test_skill(skill1_dir, "skill-1", "Original content 1")
        create_test_skill(skill2_dir, "skill-2", "Original content 2")

        # Step 2: First discovery - should get current timestamps
        discovery = ArtifactDiscoveryService(project, scan_mode="project")
        result1 = discovery.discover_artifacts()

        assert result1.discovered_count == 2
        assert len(result1.artifacts) == 2

        # Verify timestamps are recent
        now = datetime.now(timezone.utc)
        for artifact in result1.artifacts:
            time_diff = (now - artifact.discovered_at).total_seconds()
            assert time_diff < 5, f"Timestamp should be recent for {artifact.name}"
            assert artifact.discovered_at.tzinfo is not None, "Should have timezone"

        # Save timestamps from first discovery
        first_timestamps = {a.name: a.discovered_at for a in result1.artifacts}

        # Step 3: Simulate import - create lockfile entries
        lock_mgr = LockManager()
        lock_entries = {}
        for artifact in result1.artifacts:
            content_hash = compute_content_hash(Path(artifact.path))
            lock_entry = LockEntry(
                name=artifact.name,
                type=artifact.type,
                upstream=None,
                resolved_sha=None,
                resolved_version=None,
                content_hash=content_hash,
                fetched=artifact.discovered_at,
            )
            lock_entries[(artifact.name, artifact.type)] = lock_entry
        lock_mgr.write(project, lock_entries)

        # Create collection manifest with artifacts
        collection_artifacts = []
        for disc_art in result1.artifacts:
            artifact = Artifact(
                name=disc_art.name,
                type=ArtifactType(disc_art.type),
                path=f"skills/{disc_art.name}",
                origin="local",
                metadata=ArtifactMetadata(
                    description=disc_art.description or "Test skill"
                ),
                added=disc_art.discovered_at,
                discovered_at=disc_art.discovered_at,
            )
            collection_artifacts.append(artifact)

        collection = Collection(
            name="test",
            version="1.0.0",
            artifacts=collection_artifacts,
            created=now,
            updated=now,
        )

        # Wait to ensure timestamps would differ if not preserved
        time.sleep(0.2)

        # Step 4: Re-discover (no changes) - timestamps should be preserved
        result2 = discovery.discover_artifacts(manifest=collection)

        # Verify timestamps are preserved (within 1s tolerance)
        for artifact in result2.artifacts:
            first_ts = first_timestamps[artifact.name]
            second_ts = artifact.discovered_at
            time_diff = abs((second_ts - first_ts).total_seconds())
            assert (
                time_diff < 1
            ), f"{artifact.name}: timestamp should be preserved, diff={time_diff}s"

        # Step 5: Modify one artifact
        create_test_skill(skill1_dir, "skill-1", "MODIFIED CONTENT")

        # Update lockfile with old hash (simulate it hasn't been refreshed yet)
        # But now hash will differ, so timestamp should update
        time.sleep(0.2)

        # Step 6: Re-discover after modification
        result3 = discovery.discover_artifacts(manifest=collection)

        # Find the modified artifact
        skill1_artifact = next(a for a in result3.artifacts if a.name == "skill-1")
        skill2_artifact = next(a for a in result3.artifacts if a.name == "skill-2")

        # Skill-1 should have NEW timestamp (recent)
        now_after_mod = datetime.now(timezone.utc)
        skill1_time_diff = (now_after_mod - skill1_artifact.discovered_at).total_seconds()
        assert (
            skill1_time_diff < 5
        ), f"Modified artifact should have new timestamp, {skill1_time_diff}s ago"

        # Skill-2 should still have OLD timestamp (preserved)
        skill2_original_ts = first_timestamps["skill-2"]
        skill2_time_diff = abs(
            (skill2_artifact.discovered_at - skill2_original_ts).total_seconds()
        )
        assert (
            skill2_time_diff < 1
        ), f"Unchanged artifact should preserve timestamp, diff={skill2_time_diff}s"


def test_timestamp_format_in_api_response():
    """Test that timestamps are properly formatted for API responses."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir) / "project"
        project.mkdir()
        claude_dir = project / ".claude" / "skills"
        claude_dir.mkdir(parents=True)

        # Create skill
        skill_dir = claude_dir / "test-skill"
        create_test_skill(skill_dir, "test-skill")

        # Discover
        discovery = ArtifactDiscoveryService(project, scan_mode="project")
        result = discovery.discover_artifacts()

        artifact = result.artifacts[0]

        # Verify timestamp is ISO 8601 format
        iso_string = artifact.discovered_at.isoformat()

        # Check format
        assert "T" in iso_string, "ISO 8601 should have T separator"
        assert (
            "+" in iso_string or "Z" in iso_string or iso_string.endswith("00")
        ), "ISO 8601 should have timezone"

        # Verify it can round-trip
        parsed = datetime.fromisoformat(iso_string)
        assert parsed == artifact.discovered_at

        # Verify Pydantic model serialization works
        from skillmeat.api.schemas.discovery import DiscoveredArtifact as APIDiscoveredArtifact

        api_artifact = APIDiscoveredArtifact(
            type=artifact.type,
            name=artifact.name,
            path=artifact.path,
            discovered_at=artifact.discovered_at,
        )

        # Should serialize to JSON
        json_data = api_artifact.model_dump(mode="json")
        assert "discovered_at" in json_data
        # Pydantic converts datetime to string in JSON mode
        assert isinstance(json_data["discovered_at"], str)
