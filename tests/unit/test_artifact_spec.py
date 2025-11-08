"""Tests for GitHub ArtifactSpec parsing."""

import pytest

from skillmeat.sources.github import ArtifactSpec


class TestArtifactSpecParsing:
    """Test ArtifactSpec parsing from spec strings."""

    def test_parse_simple_spec(self):
        """Test parsing simple username/repo spec."""
        spec = ArtifactSpec.parse("anthropics/skills")
        assert spec.username == "anthropics"
        assert spec.repo == "skills"
        assert spec.path == ""
        assert spec.version == "latest"

    def test_parse_spec_with_path(self):
        """Test parsing spec with single path component."""
        spec = ArtifactSpec.parse("anthropics/skills/python")
        assert spec.username == "anthropics"
        assert spec.repo == "skills"
        assert spec.path == "python"
        assert spec.version == "latest"

    def test_parse_spec_with_nested_path(self):
        """Test parsing spec with nested path."""
        spec = ArtifactSpec.parse("obra/superpowers/agents/code-review")
        assert spec.username == "obra"
        assert spec.repo == "superpowers"
        assert spec.path == "agents/code-review"
        assert spec.version == "latest"

    def test_parse_spec_with_version(self):
        """Test parsing spec with version tag."""
        spec = ArtifactSpec.parse("anthropics/skills/python@v1.0.0")
        assert spec.username == "anthropics"
        assert spec.repo == "skills"
        assert spec.path == "python"
        assert spec.version == "v1.0.0"

    def test_parse_spec_with_sha(self):
        """Test parsing spec with commit SHA."""
        spec = ArtifactSpec.parse("anthropics/skills@abc123def456")
        assert spec.username == "anthropics"
        assert spec.repo == "skills"
        assert spec.path == ""
        assert spec.version == "abc123def456"

    def test_parse_spec_with_branch(self):
        """Test parsing spec with branch name."""
        spec = ArtifactSpec.parse("anthropics/skills@main")
        assert spec.username == "anthropics"
        assert spec.repo == "skills"
        assert spec.path == ""
        assert spec.version == "main"

    def test_parse_spec_with_latest(self):
        """Test parsing spec with explicit @latest."""
        spec = ArtifactSpec.parse("anthropics/skills@latest")
        assert spec.username == "anthropics"
        assert spec.repo == "skills"
        assert spec.path == ""
        assert spec.version == "latest"

    def test_parse_invalid_spec_single_part(self):
        """Test parsing invalid spec with single component."""
        with pytest.raises(ValueError, match="Invalid artifact spec"):
            ArtifactSpec.parse("anthropics")

    def test_parse_invalid_spec_empty(self):
        """Test parsing empty spec."""
        with pytest.raises(ValueError, match="Invalid artifact spec"):
            ArtifactSpec.parse("")

    def test_repo_url_property(self):
        """Test repo_url property."""
        spec = ArtifactSpec.parse("anthropics/skills")
        assert spec.repo_url == "https://github.com/anthropics/skills"

    def test_artifact_path_property_with_path(self):
        """Test artifact_path property with path."""
        spec = ArtifactSpec.parse("anthropics/skills/python")
        assert spec.artifact_path == "python"

    def test_artifact_path_property_without_path(self):
        """Test artifact_path property without path."""
        spec = ArtifactSpec.parse("anthropics/skills")
        assert spec.artifact_path == "."

    def test_str_representation_with_path(self):
        """Test string representation with path."""
        spec = ArtifactSpec.parse("anthropics/skills/python@v1.0.0")
        assert str(spec) == "anthropics/skills/python@v1.0.0"

    def test_str_representation_without_path(self):
        """Test string representation without path."""
        spec = ArtifactSpec.parse("anthropics/skills@v1.0.0")
        assert str(spec) == "anthropics/skills@v1.0.0"

    def test_multiple_at_symbols(self):
        """Test spec with multiple @ symbols (should use last one)."""
        spec = ArtifactSpec.parse("user/repo@feature@v1.0.0")
        assert spec.username == "user"
        assert spec.repo == "repo@feature"  # @ before last @ is part of repo name
        assert spec.version == "v1.0.0"

    def test_deeply_nested_path(self):
        """Test spec with deeply nested path."""
        spec = ArtifactSpec.parse("user/repo/level1/level2/level3/artifact@v1.0.0")
        assert spec.username == "user"
        assert spec.repo == "repo"
        assert spec.path == "level1/level2/level3/artifact"
        assert spec.version == "v1.0.0"
