"""Simple integration test demonstrating timestamp tracking works."""

import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from skillmeat.core.discovery import ArtifactDiscoveryService


def create_test_skill(skill_dir: Path, name: str, content: str = "Test"):
    """Create a test skill."""
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"""---
name: {name}
description: Test skill
---
# {name}
{content}
"""
    )


def test_new_artifacts_have_current_timestamp():
    """Test that newly discovered artifacts get current UTC timestamp."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir) / "project"
        project.mkdir()
        claude_dir = project / ".claude" / "skills"
        claude_dir.mkdir(parents=True)

        # Create skills
        create_test_skill(claude_dir / "skill-1", "skill-1")
        create_test_skill(claude_dir / "skill-2", "skill-2")

        # Discover
        discovery = ArtifactDiscoveryService(project, scan_mode="project")
        result = discovery.discover_artifacts()

        assert result.discovered_count == 2

        # Check timestamps are recent and valid ISO 8601
        now = datetime.now(timezone.utc)
        for artifact in result.artifacts:
            # Check it's a datetime with timezone
            assert isinstance(artifact.discovered_at, datetime)
            assert artifact.discovered_at.tzinfo is not None

            # Check it's recent (within last 5 seconds)
            time_diff = (now - artifact.discovered_at).total_seconds()
            assert time_diff < 5

            # Check ISO 8601 format
            iso_str = artifact.discovered_at.isoformat()
            assert "T" in iso_str
            assert "+" in iso_str or "Z" in iso_str

            # Verify round-trip
            parsed = datetime.fromisoformat(iso_str)
            assert parsed == artifact.discovered_at
