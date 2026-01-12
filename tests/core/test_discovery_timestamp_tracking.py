"""Tests for discovery timestamp tracking.

Tests that artifacts have valid ISO 8601 timestamps that:
- Are set to current time when artifact first discovered
- Are updated when artifact content changes
- Are preserved when artifact unchanged between discovery runs
"""

import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from skillmeat.core.collection import Collection, CollectionManager
from skillmeat.core.discovery import ArtifactDiscoveryService
from skillmeat.storage.lockfile import LockEntry, LockManager
from skillmeat.storage.manifest import ManifestManager


@pytest.fixture
def temp_project(tmp_path):
    """Create temporary project with .claude directory structure."""
    project_root = tmp_path / "test_project"
    project_root.mkdir()

    # Create .claude structure
    claude_dir = project_root / ".claude"
    claude_dir.mkdir()
    (claude_dir / "skills").mkdir()
    (claude_dir / "commands").mkdir()

    return project_root


@pytest.fixture
def temp_collection(tmp_path):
    """Create temporary collection."""
    collection_root = tmp_path / "test_collection"
    collection_root.mkdir()

    # Initialize collection
    manifest_mgr = ManifestManager()
    lock_mgr = LockManager()

    collection = manifest_mgr.create_empty(collection_root, "test")
    lock_mgr.write(collection_root, {})

    return collection_root


def create_skill(skill_dir: Path, name: str, description: str = "Test skill"):
    """Helper to create a test skill."""
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        f"""---
name: {name}
description: {description}
---

# {name}

{description}
"""
    )


def test_new_artifact_gets_current_timestamp(temp_project):
    """Test that newly discovered artifact gets current timestamp."""
    # Create a skill
    skill_dir = temp_project / ".claude" / "skills" / "test-skill"
    create_skill(skill_dir, "test-skill")

    # Run discovery
    discovery = ArtifactDiscoveryService(temp_project, scan_mode="project")
    result = discovery.discover_artifacts()

    # Verify artifact was discovered
    assert result.discovered_count == 1
    artifact = result.artifacts[0]

    # Check timestamp is recent (within last 5 seconds)
    now = datetime.now(timezone.utc)
    time_diff = (now - artifact.discovered_at).total_seconds()
    assert time_diff < 5, f"Timestamp should be recent, but {time_diff}s ago"

    # Check timestamp is ISO 8601 format (has timezone info)
    assert artifact.discovered_at.tzinfo is not None, "Timestamp should have timezone"


def test_unchanged_artifact_preserves_timestamp(temp_project, temp_collection):
    """Test that unchanged artifact preserves original timestamp."""
    from skillmeat.utils.filesystem import compute_content_hash

    # Create a skill
    skill_dir = temp_project / ".claude" / "skills" / "test-skill"
    create_skill(skill_dir, "test-skill")

    # Compute initial hash
    initial_hash = compute_content_hash(skill_dir)

    # Create collection with artifact that was discovered 1 hour ago
    from datetime import timedelta

    from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType

    old_timestamp = datetime.now(timezone.utc) - timedelta(hours=1)

    artifact = Artifact(
        name="test-skill",
        type=ArtifactType.SKILL,
        path="skills/test-skill",
        origin="local",
        metadata=ArtifactMetadata(description="Test skill"),
        added=old_timestamp,
    )
    artifact.discovered_at = old_timestamp  # Store discovery timestamp

    collection = Collection(
        name="test",
        version="1.0.0",
        artifacts=[artifact],
        created=old_timestamp,
        updated=old_timestamp,
    )

    # Create lockfile entry with hash
    lock_mgr = LockManager()
    lock_entry = LockEntry(
        name="test-skill",
        type="skill",
        upstream=None,
        resolved_sha=None,
        resolved_version=None,
        content_hash=initial_hash,
        fetched=old_timestamp,
    )
    lock_mgr.write(temp_project, {("test-skill", "skill"): lock_entry})

    # Save collection
    manifest_mgr = ManifestManager()
    manifest_mgr.write(temp_collection, collection)

    # Run discovery again with manifest
    discovery = ArtifactDiscoveryService(temp_project, scan_mode="project")
    result = discovery.discover_artifacts(manifest=collection)

    # Verify artifact was discovered
    assert result.discovered_count == 1
    artifact = result.artifacts[0]

    # Check timestamp was preserved (within 1 second of original)
    time_diff = abs((artifact.discovered_at - old_timestamp).total_seconds())
    assert time_diff < 1, f"Timestamp should be preserved, diff: {time_diff}s"


def test_modified_artifact_updates_timestamp(temp_project, temp_collection):
    """Test that modified artifact gets new timestamp."""
    from skillmeat.utils.filesystem import compute_content_hash

    # Create a skill
    skill_dir = temp_project / ".claude" / "skills" / "test-skill"
    create_skill(skill_dir, "test-skill", "Original description")

    # Compute initial hash
    initial_hash = compute_content_hash(skill_dir)

    # Create collection with artifact that was discovered 1 hour ago
    from datetime import timedelta

    from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType

    old_timestamp = datetime.now(timezone.utc) - timedelta(hours=1)

    artifact = Artifact(
        name="test-skill",
        type=ArtifactType.SKILL,
        path="skills/test-skill",
        origin="local",
        metadata=ArtifactMetadata(description="Original description"),
        added=old_timestamp,
    )
    artifact.discovered_at = old_timestamp

    collection = Collection(
        name="test",
        version="1.0.0",
        artifacts=[artifact],
        created=old_timestamp,
        updated=old_timestamp,
    )

    # Create lockfile entry with OLD hash
    lock_mgr = LockManager()
    lock_entry = LockEntry(
        name="test-skill",
        type="skill",
        upstream=None,
        resolved_sha=None,
        resolved_version=None,
        content_hash=initial_hash,
        fetched=old_timestamp,
    )
    lock_mgr.write(temp_project, {("test-skill", "skill"): lock_entry})

    # Modify the artifact (change description)
    create_skill(skill_dir, "test-skill", "MODIFIED description")

    # Verify hash changed
    new_hash = compute_content_hash(skill_dir)
    assert new_hash != initial_hash, "Hash should change after modification"

    # Run discovery again
    discovery = ArtifactDiscoveryService(temp_project, scan_mode="project")
    result = discovery.discover_artifacts(manifest=collection)

    # Verify artifact was discovered
    assert result.discovered_count == 1
    artifact = result.artifacts[0]

    # Check timestamp was updated (should be recent)
    now = datetime.now(timezone.utc)
    time_diff = (now - artifact.discovered_at).total_seconds()
    assert time_diff < 5, f"Modified artifact should get new timestamp, {time_diff}s ago"

    # Verify it's NOT the old timestamp
    old_time_diff = abs((artifact.discovered_at - old_timestamp).total_seconds())
    assert old_time_diff > 3000, "Timestamp should be updated, not preserved"


def test_discovery_twice_same_project_preserves_timestamps(temp_project):
    """Integration test: Discover same project twice, timestamps should match."""
    # Create skills
    skill1_dir = temp_project / ".claude" / "skills" / "skill-1"
    skill2_dir = temp_project / ".claude" / "skills" / "skill-2"
    create_skill(skill1_dir, "skill-1")
    create_skill(skill2_dir, "skill-2")

    # First discovery
    discovery = ArtifactDiscoveryService(temp_project, scan_mode="project")
    result1 = discovery.discover_artifacts()

    assert result1.discovered_count == 2

    # Save timestamps from first discovery
    first_timestamps = {a.name: a.discovered_at for a in result1.artifacts}

    # Create lockfile entries for both (simulating import)
    from skillmeat.utils.filesystem import compute_content_hash

    lock_mgr = LockManager()
    lock_entries = {}
    for artifact in result1.artifacts:
        artifact_path = Path(artifact.path)
        content_hash = compute_content_hash(artifact_path)
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

    lock_mgr.write(temp_project, lock_entries)

    # Create collection manifest with timestamps
    from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType

    collection_artifacts = []
    for discovered in result1.artifacts:
        artifact = Artifact(
            name=discovered.name,
            type=ArtifactType(discovered.type),
            path=f"skills/{discovered.name}",
            origin="local",
            metadata=ArtifactMetadata(description=discovered.description or ""),
            added=discovered.discovered_at,
        )
        artifact.discovered_at = discovered.discovered_at
        collection_artifacts.append(artifact)

    collection = Collection(
        name="test",
        version="1.0.0",
        artifacts=collection_artifacts,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )

    # Wait a bit to ensure timestamps would differ if not preserved
    time.sleep(0.1)

    # Second discovery with manifest
    result2 = discovery.discover_artifacts(manifest=collection)

    assert result2.discovered_count == 2

    # Verify timestamps match (within 1 second tolerance)
    for artifact in result2.artifacts:
        first_ts = first_timestamps[artifact.name]
        second_ts = artifact.discovered_at

        time_diff = abs((second_ts - first_ts).total_seconds())
        assert (
            time_diff < 1
        ), f"Timestamp for {artifact.name} should be preserved, diff: {time_diff}s"


def test_timestamp_is_iso8601_format(temp_project):
    """Test that timestamp is valid ISO 8601 format with timezone."""
    # Create a skill
    skill_dir = temp_project / ".claude" / "skills" / "test-skill"
    create_skill(skill_dir, "test-skill")

    # Run discovery
    discovery = ArtifactDiscoveryService(temp_project, scan_mode="project")
    result = discovery.discover_artifacts()

    artifact = result.artifacts[0]

    # Check it's a datetime object
    assert isinstance(artifact.discovered_at, datetime)

    # Check it has timezone info (required for ISO 8601)
    assert artifact.discovered_at.tzinfo is not None

    # Check it can be serialized to ISO 8601 string
    iso_string = artifact.discovered_at.isoformat()
    assert "T" in iso_string, "ISO 8601 should have T separator"
    assert (
        "+" in iso_string or "Z" in iso_string or "-" in iso_string[-6:]
    ), "ISO 8601 should have timezone offset"

    # Check it can be deserialized
    parsed = datetime.fromisoformat(iso_string)
    assert parsed == artifact.discovered_at
