"""Unit tests for content-based metadata extraction utilities."""

import pytest
from unittest.mock import MagicMock, patch

from skillmeat.core.artifact import ArtifactMetadata
from skillmeat.core.artifact_detection import ArtifactType
from skillmeat.core.github_client import (
    GitHubClientError,
    GitHubNotFoundError,
)
from skillmeat.utils.metadata import (
    extract_metadata_from_content,
    fetch_and_extract_github_metadata,
)


class TestExtractMetadataFromContent:
    """Test extract_metadata_from_content function."""

    def test_extract_from_frontmatter_with_description(self):
        """Test extraction from frontmatter with description field."""
        content = """---
description: A useful skill for testing
title: Test Skill
author: Test Author
---

# Test Skill

This is the body content.
"""
        metadata = extract_metadata_from_content(content, ArtifactType.SKILL)

        assert isinstance(metadata, ArtifactMetadata)
        assert metadata.description == "A useful skill for testing"
        assert metadata.title == "Test Skill"
        assert metadata.author == "Test Author"

    def test_extract_from_frontmatter_with_tools(self):
        """Test extraction from frontmatter with tools list."""
        content = """---
description: Skill with tools
tools:
  - Bash
  - Read
  - Write
---

# Test Skill
"""
        metadata = extract_metadata_from_content(content, ArtifactType.SKILL)

        assert isinstance(metadata, ArtifactMetadata)
        assert metadata.description == "Skill with tools"
        assert len(metadata.tools) == 3
        # Tools are stored as Tool enum values
        tool_names = [tool.value for tool in metadata.tools]
        assert "Bash" in tool_names
        assert "Read" in tool_names
        assert "Write" in tool_names

    def test_extract_fallback_description_from_body(self):
        """Test fallback description extraction from body when frontmatter has none."""
        content = """---
title: Test Skill
author: Test Author
---

# Test Skill

This is the first paragraph that should be extracted as the fallback description.
It spans multiple lines and provides context.

This is a second paragraph that should not be included.
"""
        metadata = extract_metadata_from_content(content, ArtifactType.SKILL)

        assert isinstance(metadata, ArtifactMetadata)
        assert metadata.title == "Test Skill"
        assert metadata.description is not None
        # Should extract first paragraph from body
        assert "first paragraph" in metadata.description.lower()
        assert "second paragraph" not in metadata.description.lower()

    def test_extract_empty_content(self):
        """Test extraction from empty content."""
        metadata = extract_metadata_from_content("", ArtifactType.SKILL)

        assert isinstance(metadata, ArtifactMetadata)
        assert metadata.description is None
        assert metadata.title is None
        assert metadata.author is None
        assert len(metadata.tools) == 0

    def test_extract_empty_whitespace_content(self):
        """Test extraction from whitespace-only content."""
        metadata = extract_metadata_from_content("   \n\n  \t  \n", ArtifactType.SKILL)

        assert isinstance(metadata, ArtifactMetadata)
        assert metadata.description is None

    def test_extract_no_frontmatter(self):
        """Test extraction when content has no frontmatter markers."""
        content = """# Test Skill

This is a skill without frontmatter.

It should still try to extract a description from the body.
"""
        metadata = extract_metadata_from_content(content, ArtifactType.SKILL)

        assert isinstance(metadata, ArtifactMetadata)
        # Should extract description from body text
        assert metadata.description is not None
        assert "skill without frontmatter" in metadata.description.lower()

    def test_extract_malformed_yaml(self):
        """Test graceful handling of malformed YAML in frontmatter."""
        content = """---
title: Test
description: [broken yaml
invalid: unclosed bracket
---

# Test Content

First paragraph of body text.
"""
        # Should not crash - gracefully falls back
        metadata = extract_metadata_from_content(content, ArtifactType.SKILL)

        assert isinstance(metadata, ArtifactMetadata)
        # YAML parsing fails, but extract_frontmatter still extracts raw fields
        # The description will be the malformed value "[broken yaml"
        # This is acceptable behavior - not a crash
        assert metadata.description is not None

    def test_extract_frontmatter_with_tags(self):
        """Test extraction of tags from frontmatter."""
        content = """---
description: Skill with tags
tags:
  - python
  - testing
  - automation
---

# Test Skill
"""
        metadata = extract_metadata_from_content(content, ArtifactType.SKILL)

        assert isinstance(metadata, ArtifactMetadata)
        assert len(metadata.tags) == 3
        assert "python" in metadata.tags
        assert "testing" in metadata.tags
        assert "automation" in metadata.tags

    def test_extract_frontmatter_with_dependencies(self):
        """Test extraction of dependencies from frontmatter."""
        content = """---
description: Skill with dependencies
dependencies:
  - skill-a
  - skill-b
---

# Test Skill
"""
        metadata = extract_metadata_from_content(content, ArtifactType.SKILL)

        assert isinstance(metadata, ArtifactMetadata)
        assert len(metadata.dependencies) == 2
        assert "skill-a" in metadata.dependencies
        assert "skill-b" in metadata.dependencies

    def test_extract_frontmatter_with_version_and_license(self):
        """Test extraction of version and license fields."""
        content = """---
description: Versioned skill
version: 1.2.3
license: MIT
---

# Test Skill
"""
        metadata = extract_metadata_from_content(content, ArtifactType.SKILL)

        assert isinstance(metadata, ArtifactMetadata)
        assert metadata.version == "1.2.3"
        assert metadata.license == "MIT"

    def test_extract_incomplete_frontmatter(self):
        """Test handling of incomplete frontmatter (no closing delimiter)."""
        content = """---
title: Test
description: Missing closing delimiter

# Test Content
This should be treated as body since frontmatter is incomplete.
"""
        metadata = extract_metadata_from_content(content, ArtifactType.SKILL)

        assert isinstance(metadata, ArtifactMetadata)
        # Should still attempt to extract something
        # Behavior depends on extract_frontmatter implementation


class TestFetchAndExtractGithubMetadata:
    """Test fetch_and_extract_github_metadata function."""

    def test_fetch_single_file_agent(self):
        """Test fetching metadata from a single .md file path."""
        mock_client = MagicMock()
        content = b"""---
description: Test agent
author: Test Author
---

# Test Agent
"""
        mock_client.get_file_content.return_value = content

        metadata = fetch_and_extract_github_metadata(
            client=mock_client,
            owner="testuser",
            repo="testrepo",
            path="agents/my-agent.md",
            artifact_type=ArtifactType.AGENT,
            ref="main",
        )

        assert metadata is not None
        assert isinstance(metadata, ArtifactMetadata)
        assert metadata.description == "Test agent"
        assert metadata.author == "Test Author"

        # Verify API was called correctly
        mock_client.get_file_content.assert_called_once_with(
            "testuser/testrepo", "agents/my-agent.md", ref="main"
        )

    def test_fetch_directory_skill(self):
        """Test fetching metadata from directory (probes for SKILL.md)."""
        mock_client = MagicMock()
        skill_content = b"""---
description: Test skill from SKILL.md
tools: [Bash, Read]
---

# Test Skill
"""
        mock_client.get_file_content.return_value = skill_content

        metadata = fetch_and_extract_github_metadata(
            client=mock_client,
            owner="testuser",
            repo="testrepo",
            path="skills/my-skill",
            artifact_type=ArtifactType.SKILL,
            ref="HEAD",
        )

        assert metadata is not None
        assert isinstance(metadata, ArtifactMetadata)
        assert metadata.description == "Test skill from SKILL.md"

        # Should probe for SKILL.md in the directory
        mock_client.get_file_content.assert_called_once_with(
            "testuser/testrepo", "skills/my-skill/SKILL.md", ref=None
        )

    def test_fetch_directory_agent(self):
        """Test fetching metadata from directory with agent type (probes AGENT.md first)."""
        mock_client = MagicMock()
        agent_content = b"""---
description: Test agent from AGENT.md
---

# Test Agent
"""
        mock_client.get_file_content.return_value = agent_content

        metadata = fetch_and_extract_github_metadata(
            client=mock_client,
            owner="testuser",
            repo="testrepo",
            path="agents/my-agent-dir",
            artifact_type=ArtifactType.AGENT,
            ref="HEAD",
        )

        assert metadata is not None
        assert metadata.description == "Test agent from AGENT.md"

        # Should probe for AGENT.md first
        mock_client.get_file_content.assert_called_once_with(
            "testuser/testrepo", "agents/my-agent-dir/AGENT.md", ref=None
        )

    def test_fetch_not_found(self):
        """Test graceful handling when file is not found."""
        mock_client = MagicMock()
        mock_client.get_file_content.side_effect = GitHubNotFoundError(
            "File not found"
        )

        metadata = fetch_and_extract_github_metadata(
            client=mock_client,
            owner="testuser",
            repo="testrepo",
            path="agents/nonexistent.md",
            artifact_type=ArtifactType.AGENT,
        )

        assert metadata is None

    def test_fetch_github_client_error(self):
        """Test graceful handling of GitHubClientError."""
        mock_client = MagicMock()
        mock_client.get_file_content.side_effect = GitHubClientError(
            "API rate limit exceeded"
        )

        metadata = fetch_and_extract_github_metadata(
            client=mock_client,
            owner="testuser",
            repo="testrepo",
            path="skills/my-skill.md",
            artifact_type=ArtifactType.SKILL,
        )

        assert metadata is None

    def test_fetch_directory_fallback_to_readme(self):
        """Test fallback to README.md when primary file not found."""
        mock_client = MagicMock()

        # First call (SKILL.md) fails with 404
        # Second call (README.md) succeeds
        readme_content = b"""---
description: Fallback from README
---

# Skill
"""

        def side_effect(owner_repo, path, ref=None):
            if "SKILL.md" in path:
                raise GitHubNotFoundError("Not found")
            elif "README.md" in path:
                return readme_content
            raise GitHubNotFoundError("Not found")

        mock_client.get_file_content.side_effect = side_effect

        metadata = fetch_and_extract_github_metadata(
            client=mock_client,
            owner="testuser",
            repo="testrepo",
            path="skills/my-skill",
            artifact_type=ArtifactType.SKILL,
        )

        assert metadata is not None
        assert metadata.description == "Fallback from README"

        # Should have tried SKILL.md first, then README.md
        assert mock_client.get_file_content.call_count == 2

    def test_fetch_head_ref_normalization(self):
        """Test that 'HEAD' ref is normalized to None (default branch)."""
        mock_client = MagicMock()
        mock_client.get_file_content.return_value = b"""---
description: Test
---
"""

        metadata = fetch_and_extract_github_metadata(
            client=mock_client,
            owner="testuser",
            repo="testrepo",
            path="test.md",
            artifact_type=ArtifactType.SKILL,
            ref="HEAD",
        )

        assert metadata is not None
        # Verify ref=None was passed (HEAD normalized)
        mock_client.get_file_content.assert_called_once_with(
            "testuser/testrepo", "test.md", ref=None
        )

    def test_fetch_latest_ref_normalization(self):
        """Test that 'latest' ref is normalized to None (default branch)."""
        mock_client = MagicMock()
        mock_client.get_file_content.return_value = b"""---
description: Test
---
"""

        metadata = fetch_and_extract_github_metadata(
            client=mock_client,
            owner="testuser",
            repo="testrepo",
            path="test.md",
            artifact_type=ArtifactType.SKILL,
            ref="latest",
        )

        assert metadata is not None
        # Verify ref=None was passed (latest normalized)
        mock_client.get_file_content.assert_called_once_with(
            "testuser/testrepo", "test.md", ref=None
        )

    def test_fetch_specific_ref_preserved(self):
        """Test that specific refs (branches/tags/SHAs) are preserved."""
        mock_client = MagicMock()
        mock_client.get_file_content.return_value = b"""---
description: Test
---
"""

        metadata = fetch_and_extract_github_metadata(
            client=mock_client,
            owner="testuser",
            repo="testrepo",
            path="test.md",
            artifact_type=ArtifactType.SKILL,
            ref="v1.2.3",
        )

        assert metadata is not None
        # Verify specific ref was passed through
        mock_client.get_file_content.assert_called_once_with(
            "testuser/testrepo", "test.md", ref="v1.2.3"
        )

    def test_fetch_generic_exception(self):
        """Test graceful handling of unexpected exceptions."""
        mock_client = MagicMock()
        mock_client.get_file_content.side_effect = Exception("Unexpected error")

        metadata = fetch_and_extract_github_metadata(
            client=mock_client,
            owner="testuser",
            repo="testrepo",
            path="test.md",
            artifact_type=ArtifactType.SKILL,
        )

        assert metadata is None

    def test_fetch_directory_command_type(self):
        """Test fetching from directory with command type (probes COMMAND.md)."""
        mock_client = MagicMock()
        command_content = b"""---
description: Test command
---

# Test Command
"""
        mock_client.get_file_content.return_value = command_content

        metadata = fetch_and_extract_github_metadata(
            client=mock_client,
            owner="testuser",
            repo="testrepo",
            path="commands/my-command",
            artifact_type=ArtifactType.COMMAND,
        )

        assert metadata is not None
        assert metadata.description == "Test command"

        # Should probe for COMMAND.md
        mock_client.get_file_content.assert_called_once_with(
            "testuser/testrepo", "commands/my-command/COMMAND.md", ref=None
        )

    def test_fetch_directory_hook_type(self):
        """Test fetching from directory with hook type (probes HOOK.md)."""
        mock_client = MagicMock()
        hook_content = b"""---
description: Test hook
---

# Test Hook
"""
        mock_client.get_file_content.return_value = hook_content

        metadata = fetch_and_extract_github_metadata(
            client=mock_client,
            owner="testuser",
            repo="testrepo",
            path="hooks/my-hook",
            artifact_type=ArtifactType.HOOK,
        )

        assert metadata is not None
        assert metadata.description == "Test hook"

        # Should probe for HOOK.md
        mock_client.get_file_content.assert_called_once_with(
            "testuser/testrepo", "hooks/my-hook/HOOK.md", ref=None
        )

    def test_fetch_empty_content_returns_none(self):
        """Test that empty file content returns None."""
        mock_client = MagicMock()
        mock_client.get_file_content.return_value = b""

        metadata = fetch_and_extract_github_metadata(
            client=mock_client,
            owner="testuser",
            repo="testrepo",
            path="test.md",
            artifact_type=ArtifactType.SKILL,
        )

        # Empty content is falsy, so function returns None (line 989-991)
        assert metadata is None

    def test_fetch_utf8_decoding(self):
        """Test proper UTF-8 decoding of file content."""
        mock_client = MagicMock()
        # Content with Unicode characters
        content = """---
description: Test with Unicode 世界 🎉
author: François
---

# Test
""".encode("utf-8")
        mock_client.get_file_content.return_value = content

        metadata = fetch_and_extract_github_metadata(
            client=mock_client,
            owner="testuser",
            repo="testrepo",
            path="test.md",
            artifact_type=ArtifactType.SKILL,
        )

        assert metadata is not None
        assert "世界" in metadata.description
        assert "🎉" in metadata.description
        assert metadata.author == "François"
