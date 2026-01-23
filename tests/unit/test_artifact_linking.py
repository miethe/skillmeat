"""Tests for artifact linking functions in skillmeat/utils/metadata.py."""

from datetime import datetime

import pytest

from skillmeat.core.artifact import Artifact, ArtifactMetadata, LinkedArtifactReference
from skillmeat.core.artifact_detection import ArtifactType
from skillmeat.utils.metadata import (
    create_linked_artifact_reference,
    extract_artifact_references,
    match_artifact_reference,
    resolve_artifact_references,
)


@pytest.fixture
def sample_artifacts():
    """Create sample artifacts for testing."""
    return [
        Artifact(
            name="code-review",
            type=ArtifactType.SKILL,
            path="skills/code-review/",
            origin="github",
            metadata=ArtifactMetadata(),
            added=datetime.utcnow(),
        ),
        Artifact(
            name="testing",
            type=ArtifactType.SKILL,
            path="skills/testing/",
            origin="github",
            metadata=ArtifactMetadata(),
            added=datetime.utcnow(),
        ),
        Artifact(
            name="my-agent",
            type=ArtifactType.AGENT,
            path="agents/my-agent.md",
            origin="local",
            metadata=ArtifactMetadata(),
            added=datetime.utcnow(),
        ),
        Artifact(
            name="code_formatter",
            type=ArtifactType.SKILL,
            path="skills/code_formatter/",
            origin="local",
            metadata=ArtifactMetadata(),
            added=datetime.utcnow(),
        ),
    ]


class TestExtractArtifactReferences:
    """Tests for extract_artifact_references function."""

    def test_agent_with_skills_list(self):
        """AGENT type extracts skills field as 'requires'."""
        refs = extract_artifact_references(
            {"skills": ["code-review", "testing"], "agent": "my-agent"},
            ArtifactType.AGENT,
        )
        assert refs["requires"] == ["code-review", "testing"]
        assert refs["enables"] == []
        assert refs["related"] == []

    def test_skill_with_agent_string(self):
        """SKILL type extracts agent field as 'enables'."""
        refs = extract_artifact_references(
            {"skills": ["code-review", "testing"], "agent": "my-agent"},
            ArtifactType.SKILL,
        )
        assert refs["requires"] == []
        assert refs["enables"] == ["my-agent"]
        assert refs["related"] == []

    def test_skill_with_agent_list(self):
        """SKILL type extracts agent list as 'enables'."""
        refs = extract_artifact_references(
            {"agent": ["agent1", "agent2"]},
            ArtifactType.SKILL,
        )
        assert refs["enables"] == ["agent1", "agent2"]

    def test_comma_separated_skills(self):
        """Skills as comma-separated string are parsed correctly."""
        refs = extract_artifact_references(
            {"skills": "code-review, testing, formatting"},
            ArtifactType.AGENT,
        )
        assert refs["requires"] == ["code-review", "testing", "formatting"]

    def test_comma_separated_related(self):
        """Related as comma-separated string is parsed correctly."""
        refs = extract_artifact_references(
            {"related": "other-skill, another"},
            ArtifactType.SKILL,
        )
        assert refs["related"] == ["other-skill", "another"]

    def test_related_as_list(self):
        """Related field as list is preserved."""
        refs = extract_artifact_references(
            {"related": ["skill-a", "skill-b"]},
            ArtifactType.SKILL,
        )
        assert refs["related"] == ["skill-a", "skill-b"]

    def test_empty_frontmatter(self):
        """Empty frontmatter returns empty references."""
        refs = extract_artifact_references({}, ArtifactType.AGENT)
        assert refs == {"requires": [], "enables": [], "related": []}

    def test_none_frontmatter(self):
        """None frontmatter returns empty references."""
        refs = extract_artifact_references(None, ArtifactType.AGENT)
        assert refs == {"requires": [], "enables": [], "related": []}

    def test_command_type_no_requires(self):
        """COMMAND type does not extract skills as requires."""
        refs = extract_artifact_references(
            {"skills": ["code-review"]},
            ArtifactType.COMMAND,
        )
        assert refs["requires"] == []

    def test_whitespace_handling(self):
        """Whitespace is stripped from values."""
        refs = extract_artifact_references(
            {"skills": "  code-review  ,  testing  "},
            ArtifactType.AGENT,
        )
        assert refs["requires"] == ["code-review", "testing"]


class TestMatchArtifactReference:
    """Tests for match_artifact_reference function."""

    def test_exact_match_case_insensitive(self, sample_artifacts):
        """Exact match is case-insensitive."""
        matched = match_artifact_reference("Code-Review", sample_artifacts)
        assert matched is not None
        assert matched.name == "code-review"

    def test_exact_match_lowercase(self, sample_artifacts):
        """Lowercase exact match works."""
        matched = match_artifact_reference("code-review", sample_artifacts)
        assert matched is not None
        assert matched.name == "code-review"

    def test_type_filter_skill(self, sample_artifacts):
        """Type filter restricts to SKILL artifacts."""
        matched = match_artifact_reference(
            "code-review", sample_artifacts, ArtifactType.SKILL
        )
        assert matched is not None
        assert matched.name == "code-review"

    def test_type_filter_agent_no_match(self, sample_artifacts):
        """Type filter AGENT does not match SKILL artifact."""
        matched = match_artifact_reference(
            "code-review", sample_artifacts, ArtifactType.AGENT
        )
        assert matched is None

    def test_no_match_returns_none(self, sample_artifacts):
        """Unknown reference returns None."""
        matched = match_artifact_reference("unknown-skill", sample_artifacts)
        assert matched is None

    def test_empty_reference(self, sample_artifacts):
        """Empty reference returns None."""
        matched = match_artifact_reference("", sample_artifacts)
        assert matched is None

    def test_empty_artifacts(self):
        """Empty artifacts list returns None."""
        matched = match_artifact_reference("test", [])
        assert matched is None

    def test_whitespace_only_reference(self, sample_artifacts):
        """Whitespace-only reference returns None."""
        matched = match_artifact_reference("   ", sample_artifacts)
        assert matched is None

    def test_hyphen_underscore_normalization(self, sample_artifacts):
        """Hyphen/underscore normalization works."""
        # code_formatter exists with underscore
        matched = match_artifact_reference("code-formatter", sample_artifacts)
        assert matched is not None
        assert matched.name == "code_formatter"

    def test_plural_singular_match(self, sample_artifacts):
        """Plural/singular forms match."""
        # 'testing' should match 'testings' (if we had it) or vice versa
        # For this test, 'testing' exists, so 'testings' should match it
        matched = match_artifact_reference("testings", sample_artifacts)
        assert matched is not None
        assert matched.name == "testing"


class TestCreateLinkedArtifactReference:
    """Tests for create_linked_artifact_reference function."""

    def test_creates_valid_reference(self, sample_artifacts):
        """Creates a valid LinkedArtifactReference."""
        link = create_linked_artifact_reference(
            sample_artifacts[0], "requires", "test-source"
        )
        assert link.artifact_name == "code-review"
        assert link.artifact_type == ArtifactType.SKILL
        assert link.link_type == "requires"
        assert link.source_name == "test-source"

    def test_default_source_from_origin(self, sample_artifacts):
        """Uses artifact origin as default source_name."""
        link = create_linked_artifact_reference(sample_artifacts[0], "enables")
        assert link.source_name == "github"

    def test_generates_artifact_id(self, sample_artifacts):
        """Generates artifact_id from type and name."""
        link = create_linked_artifact_reference(sample_artifacts[0], "requires")
        assert link.artifact_id == "skill::code-review"

    def test_enables_link_type(self, sample_artifacts):
        """Creates link with 'enables' type."""
        link = create_linked_artifact_reference(sample_artifacts[2], "enables")
        assert link.link_type == "enables"

    def test_related_link_type(self, sample_artifacts):
        """Creates link with 'related' type."""
        link = create_linked_artifact_reference(sample_artifacts[1], "related")
        assert link.link_type == "related"


class TestResolveArtifactReferences:
    """Tests for resolve_artifact_references function."""

    def test_agent_resolves_skills(self, sample_artifacts):
        """AGENT with skills resolves to linked artifacts."""
        linked, unlinked = resolve_artifact_references(
            {"skills": ["code-review", "unknown-skill"]},
            ArtifactType.AGENT,
            sample_artifacts,
        )
        assert len(linked) == 1
        assert linked[0].artifact_name == "code-review"
        assert linked[0].link_type == "requires"
        assert unlinked == ["unknown-skill"]

    def test_skill_resolves_agent(self, sample_artifacts):
        """SKILL with agent resolves to linked artifact."""
        linked, unlinked = resolve_artifact_references(
            {"agent": "my-agent"},
            ArtifactType.SKILL,
            sample_artifacts,
        )
        assert len(linked) == 1
        assert linked[0].artifact_name == "my-agent"
        assert linked[0].link_type == "enables"
        assert unlinked == []

    def test_resolves_related(self, sample_artifacts):
        """Related field resolves to linked artifacts."""
        linked, unlinked = resolve_artifact_references(
            {"related": ["testing", "unknown"]},
            ArtifactType.SKILL,
            sample_artifacts,
        )
        # Should have 1 linked (testing) and 1 unlinked (unknown)
        assert len(linked) == 1
        assert linked[0].artifact_name == "testing"
        assert linked[0].link_type == "related"
        assert unlinked == ["unknown"]

    def test_multiple_link_types(self, sample_artifacts):
        """Resolves multiple link types correctly."""
        linked, unlinked = resolve_artifact_references(
            {"agent": "my-agent", "related": "testing"},
            ArtifactType.SKILL,
            sample_artifacts,
        )
        assert len(linked) == 2
        link_types = {l.link_type for l in linked}
        assert "enables" in link_types
        assert "related" in link_types

    def test_empty_frontmatter(self, sample_artifacts):
        """Empty frontmatter returns empty results."""
        linked, unlinked = resolve_artifact_references(
            {}, ArtifactType.AGENT, sample_artifacts
        )
        assert linked == []
        assert unlinked == []

    def test_empty_artifacts(self):
        """Empty artifacts list returns empty linked."""
        linked, unlinked = resolve_artifact_references(
            {"skills": ["test"]}, ArtifactType.AGENT, []
        )
        assert linked == []
        assert unlinked == []

    def test_source_name_passed_to_links(self, sample_artifacts):
        """Source name is passed to created links."""
        linked, unlinked = resolve_artifact_references(
            {"skills": ["code-review"]},
            ArtifactType.AGENT,
            sample_artifacts,
            source_name="custom-source",
        )
        assert len(linked) == 1
        assert linked[0].source_name == "custom-source"

    def test_all_unresolved(self, sample_artifacts):
        """All unresolved references go to unlinked list."""
        linked, unlinked = resolve_artifact_references(
            {"skills": ["unknown1", "unknown2", "unknown3"]},
            ArtifactType.AGENT,
            sample_artifacts,
        )
        assert linked == []
        assert unlinked == ["unknown1", "unknown2", "unknown3"]

    def test_type_filtering_agent_skills(self, sample_artifacts):
        """AGENT skills are matched against SKILL type artifacts only."""
        # my-agent exists as AGENT, but shouldn't match when looking for skills
        linked, unlinked = resolve_artifact_references(
            {"skills": ["my-agent"]},
            ArtifactType.AGENT,
            sample_artifacts,
        )
        # my-agent is an AGENT, not a SKILL, so should be unlinked
        assert linked == []
        assert unlinked == ["my-agent"]
