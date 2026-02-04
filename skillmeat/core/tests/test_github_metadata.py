"""Unit tests for GitHub metadata extraction service.

Tests the GitHubMetadataExtractor class including URL parsing, metadata fetching,
frontmatter extraction, and error handling.
"""

import base64
import time
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
import yaml

from skillmeat.core.cache import MetadataCache
from skillmeat.core.github_client import (
    GitHubClientError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)
from skillmeat.core.github_metadata import (
    GitHubMetadata,
    GitHubMetadataExtractor,
    GitHubSourceSpec,
)


class TestGitHubURLParsing:
    """Test URL parsing functionality."""

    def test_parse_standard_format(self):
        """Test parsing user/repo/path format."""
        extractor = GitHubMetadataExtractor(cache=MetadataCache())
        spec = extractor.parse_github_url("anthropics/skills/canvas-design")

        assert spec.owner == "anthropics"
        assert spec.repo == "skills"
        assert spec.path == "canvas-design"
        assert spec.version == "latest"

    def test_parse_standard_format_minimal(self):
        """Test parsing minimal user/repo format."""
        extractor = GitHubMetadataExtractor(cache=MetadataCache())
        spec = extractor.parse_github_url("anthropics/skills")

        assert spec.owner == "anthropics"
        assert spec.repo == "skills"
        assert spec.path == ""
        assert spec.version == "latest"

    def test_parse_https_url_with_path(self):
        """Test parsing https://github.com/... format with path."""
        extractor = GitHubMetadataExtractor(cache=MetadataCache())
        spec = extractor.parse_github_url(
            "https://github.com/anthropics/skills/tree/main/canvas-design"
        )

        assert spec.owner == "anthropics"
        assert spec.repo == "skills"
        assert spec.path == "canvas-design"
        assert spec.version == "latest"

    def test_parse_https_url_nested_path(self):
        """Test parsing https URL with deeply nested path."""
        extractor = GitHubMetadataExtractor(cache=MetadataCache())
        spec = extractor.parse_github_url(
            "https://github.com/user/repo/tree/main/path/to/deep/artifact"
        )

        assert spec.owner == "user"
        assert spec.repo == "repo"
        assert spec.path == "path/to/deep/artifact"
        assert spec.version == "latest"

    def test_parse_https_url_without_tree(self):
        """Test parsing https URL without /tree/ref part."""
        extractor = GitHubMetadataExtractor(cache=MetadataCache())
        spec = extractor.parse_github_url("https://github.com/anthropics/skills")

        assert spec.owner == "anthropics"
        assert spec.repo == "skills"
        assert spec.path == ""
        assert spec.version == "latest"

    def test_parse_with_version_tag(self):
        """Test parsing user/repo/path@v1.0.0 format."""
        extractor = GitHubMetadataExtractor(cache=MetadataCache())
        spec = extractor.parse_github_url("anthropics/skills/canvas@v1.0.0")

        assert spec.owner == "anthropics"
        assert spec.repo == "skills"
        assert spec.path == "canvas"
        assert spec.version == "v1.0.0"

    def test_parse_with_version_sha(self):
        """Test parsing user/repo/path@abc1234 format."""
        extractor = GitHubMetadataExtractor(cache=MetadataCache())
        spec = extractor.parse_github_url("anthropics/skills/canvas@abc1234def567")

        assert spec.owner == "anthropics"
        assert spec.repo == "skills"
        assert spec.path == "canvas"
        assert spec.version == "abc1234def567"

    def test_parse_with_version_latest(self):
        """Test parsing user/repo/path@latest format."""
        extractor = GitHubMetadataExtractor(cache=MetadataCache())
        spec = extractor.parse_github_url("anthropics/skills/canvas@latest")

        assert spec.owner == "anthropics"
        assert spec.repo == "skills"
        assert spec.path == "canvas"
        assert spec.version == "latest"

    def test_parse_nested_path(self):
        """Test parsing user/repo/deep/nested/path format."""
        extractor = GitHubMetadataExtractor(cache=MetadataCache())
        spec = extractor.parse_github_url("user/repo/level1/level2/level3/artifact")

        assert spec.owner == "user"
        assert spec.repo == "repo"
        assert spec.path == "level1/level2/level3/artifact"
        assert spec.version == "latest"

    def test_parse_nested_path_with_version(self):
        """Test parsing nested path with version."""
        extractor = GitHubMetadataExtractor(cache=MetadataCache())
        spec = extractor.parse_github_url("user/repo/path/to/artifact@v2.0.0")

        assert spec.owner == "user"
        assert spec.repo == "repo"
        assert spec.path == "path/to/artifact"
        assert spec.version == "v2.0.0"

    def test_parse_invalid_format_too_few_segments(self):
        """Test that invalid formats raise ValueError (too few segments)."""
        extractor = GitHubMetadataExtractor(cache=MetadataCache())

        with pytest.raises(ValueError, match="Invalid GitHub spec"):
            extractor.parse_github_url("onlyone")

    def test_parse_invalid_format_empty_string(self):
        """Test that empty string raises ValueError."""
        extractor = GitHubMetadataExtractor(cache=MetadataCache())

        with pytest.raises(ValueError, match="Invalid GitHub spec"):
            extractor.parse_github_url("")

    def test_parse_invalid_https_url_too_short(self):
        """Test that invalid HTTPS URL raises ValueError."""
        extractor = GitHubMetadataExtractor(cache=MetadataCache())

        with pytest.raises(ValueError, match="Invalid GitHub URL"):
            extractor.parse_github_url("https://github.com/onlyone")


class TestMetadataFetching:
    """Test metadata fetching functionality with mocked GitHubClient."""

    @pytest.fixture
    def mock_cache(self):
        """Provide a fresh MetadataCache for each test."""
        return MetadataCache()

    @pytest.fixture
    def extractor(self, mock_cache):
        """Provide a GitHubMetadataExtractor with mock cache."""
        return GitHubMetadataExtractor(cache=mock_cache)

    def test_fetch_metadata_success(self, extractor, mock_cache):
        """Test successful metadata fetch with mocked GitHub client."""
        # Mock file content (SKILL.md)
        skill_content = """---
title: Canvas Design
description: Create beautiful visual art
author: Anthropic
tags:
  - design
  - canvas
---

# Canvas Design

Content here...
"""

        def mock_get_file_content(owner_repo, path, ref=None):
            if "SKILL.md" in path:
                return skill_content.encode("utf-8")
            raise GitHubNotFoundError(f"File not found: {path}")

        mock_repo_metadata = {
            "topics": ["design", "art", "canvas"],
            "license": "MIT",
            "stars": 100,
            "description": "A great repo",
        }

        with (
            patch.object(
                extractor._client, "get_file_content", side_effect=mock_get_file_content
            ),
            patch.object(
                extractor._client, "get_repo_metadata", return_value=mock_repo_metadata
            ),
        ):
            metadata = extractor.fetch_metadata("anthropics/skills/canvas")

        assert metadata.title == "Canvas Design"
        assert metadata.description == "Create beautiful visual art"
        assert metadata.author == "Anthropic"
        assert metadata.license == "MIT"
        assert "design" in metadata.topics
        assert "art" in metadata.topics
        assert "github.com" in metadata.url
        assert metadata.source == "auto-populated"
        assert isinstance(metadata.fetched_at, datetime)

    def test_fetch_metadata_with_readme(self, extractor):
        """Test metadata fetch when only README.md has frontmatter."""
        readme_content = """---
title: My Project
description: A great project
---

# My Project
"""

        def mock_get_file_content(owner_repo, path, ref=None):
            if "README.md" in path:
                return readme_content.encode("utf-8")
            raise GitHubNotFoundError(f"File not found: {path}")

        mock_repo_metadata = {"topics": [], "license": None}

        with (
            patch.object(
                extractor._client, "get_file_content", side_effect=mock_get_file_content
            ),
            patch.object(
                extractor._client, "get_repo_metadata", return_value=mock_repo_metadata
            ),
        ):
            metadata = extractor.fetch_metadata("user/repo/project")

        assert metadata.title == "My Project"
        assert metadata.description == "A great project"

    def test_fetch_metadata_no_frontmatter(self, extractor):
        """Test metadata fetch when no files have frontmatter."""

        def mock_get_file_content(owner_repo, path, ref=None):
            raise GitHubNotFoundError(f"File not found: {path}")

        mock_repo_metadata = {
            "topics": ["python"],
            "license": "Apache-2.0",
        }

        with (
            patch.object(
                extractor._client, "get_file_content", side_effect=mock_get_file_content
            ),
            patch.object(
                extractor._client, "get_repo_metadata", return_value=mock_repo_metadata
            ),
        ):
            metadata = extractor.fetch_metadata("user/repo/project")

        # Frontmatter fields should be None
        assert metadata.title is None
        assert metadata.description is None
        assert metadata.author is None
        # But repo metadata should be present
        assert metadata.license == "Apache-2.0"
        assert "python" in metadata.topics

    def test_fetch_metadata_github_error_404(self, extractor):
        """Test handling of 404 Not Found for repository."""

        def mock_get_file_content(owner_repo, path, ref=None):
            raise GitHubNotFoundError(f"File not found: {path}")

        def mock_get_repo_metadata(owner_repo):
            raise GitHubClientError(f"Repository not found: {owner_repo}")

        with (
            patch.object(
                extractor._client, "get_file_content", side_effect=mock_get_file_content
            ),
            patch.object(
                extractor._client,
                "get_repo_metadata",
                side_effect=mock_get_repo_metadata,
            ),
        ):
            metadata = extractor.fetch_metadata("user/nonexistent/project")

        # Should still return metadata with minimal info
        assert metadata.title is None
        assert metadata.topics == []

    def test_fetch_metadata_github_error_500(self, extractor):
        """Test handling of 500 Internal Server Error."""

        def mock_get_file_content(owner_repo, path, ref=None):
            raise GitHubClientError("Internal server error")

        def mock_get_repo_metadata(owner_repo):
            raise GitHubClientError("Internal server error")

        with (
            patch.object(
                extractor._client, "get_file_content", side_effect=mock_get_file_content
            ),
            patch.object(
                extractor._client,
                "get_repo_metadata",
                side_effect=mock_get_repo_metadata,
            ),
        ):
            metadata = extractor.fetch_metadata("user/repo/project")

        # Should handle gracefully and return basic metadata
        assert metadata is not None
        assert metadata.title is None

    def test_fetch_metadata_rate_limited(self, extractor):
        """Test handling of rate limit error."""

        def mock_get_file_content(owner_repo, path, ref=None):
            raise GitHubRateLimitError("Rate limit exceeded")

        def mock_get_repo_metadata(owner_repo):
            raise GitHubRateLimitError("Rate limit exceeded")

        with (
            patch.object(
                extractor._client, "get_file_content", side_effect=mock_get_file_content
            ),
            patch.object(
                extractor._client,
                "get_repo_metadata",
                side_effect=mock_get_repo_metadata,
            ),
        ):
            # Now returns metadata with empty fields instead of raising
            metadata = extractor.fetch_metadata("user/repo/project")

        assert metadata is not None
        assert metadata.title is None
        assert metadata.topics == []

    def test_fetch_metadata_with_cache_hit(self, mock_cache):
        """Test that cached data is returned without API call."""
        # Pre-populate cache
        cached_data = {
            "title": "Cached Artifact",
            "description": "From cache",
            "author": "Cache Author",
            "license": "MIT",
            "topics": ["cached"],
            "url": "https://github.com/user/repo",
            "fetched_at": datetime.now().isoformat(),
            "source": "auto-populated",
        }
        mock_cache.set("github_metadata:user/repo/artifact", cached_data)

        extractor = GitHubMetadataExtractor(cache=mock_cache)

        with (
            patch.object(extractor._client, "get_file_content") as mock_get_file,
            patch.object(extractor._client, "get_repo_metadata") as mock_get_repo,
        ):
            metadata = extractor.fetch_metadata("user/repo/artifact")

            # Verify no API calls made
            mock_get_file.assert_not_called()
            mock_get_repo.assert_not_called()

        assert metadata.title == "Cached Artifact"
        assert metadata.description == "From cache"
        assert metadata.author == "Cache Author"

    def test_fetch_metadata_with_cache_miss(self, mock_cache):
        """Test that fresh data is fetched and cached on miss."""
        extractor = GitHubMetadataExtractor(cache=mock_cache)

        skill_content = """---
title: Fresh Data
description: Newly fetched
---
Content
"""

        def mock_get_file_content(owner_repo, path, ref=None):
            if "SKILL.md" in path:
                return skill_content.encode("utf-8")
            raise GitHubNotFoundError(f"File not found: {path}")

        mock_repo_metadata = {"topics": [], "license": None}

        with (
            patch.object(
                extractor._client, "get_file_content", side_effect=mock_get_file_content
            ),
            patch.object(
                extractor._client, "get_repo_metadata", return_value=mock_repo_metadata
            ),
        ):
            metadata = extractor.fetch_metadata("user/repo/fresh")

        assert metadata.title == "Fresh Data"

        # Verify data was cached
        cached = mock_cache.get("github_metadata:user/repo/fresh")
        assert cached is not None
        assert cached["title"] == "Fresh Data"

    def test_fetch_metadata_single_file_artifact(self, extractor):
        """Test metadata fetch for single-file artifact (e.g., my-agent.md)."""
        # Single file with frontmatter
        agent_content = """---
title: My Agent
description: A single-file agent artifact
author: Test Author
version: 1.0.0
---

# My Agent

This is a single-file agent.
"""

        def mock_get_file_content(owner_repo, path, ref=None):
            if path == "agents/my-agent.md":
                return agent_content.encode("utf-8")
            raise GitHubNotFoundError(f"File not found: {path}")

        mock_repo_metadata = {
            "topics": ["agents", "automation"],
            "license": "MIT",
        }

        with (
            patch.object(
                extractor._client, "get_file_content", side_effect=mock_get_file_content
            ),
            patch.object(
                extractor._client, "get_repo_metadata", return_value=mock_repo_metadata
            ),
        ):
            metadata = extractor.fetch_metadata("user/repo/agents/my-agent.md")

        # Verify frontmatter extracted from single file
        assert metadata.title == "My Agent"
        assert metadata.description == "A single-file agent artifact"
        assert metadata.author == "Test Author"
        # Verify repo metadata still fetched
        assert metadata.license == "MIT"
        assert "agents" in metadata.topics
        assert "automation" in metadata.topics

    def test_fetch_metadata_single_file_no_frontmatter(self, extractor):
        """Test single-file artifact without frontmatter falls back gracefully."""
        # Single file without frontmatter
        agent_content = """# My Agent

This is a single-file agent without frontmatter.
"""

        def mock_get_file_content(owner_repo, path, ref=None):
            if path == "agents/simple.md":
                return agent_content.encode("utf-8")
            raise GitHubNotFoundError(f"File not found: {path}")

        mock_repo_metadata = {
            "topics": ["agents"],
            "license": "Apache-2.0",
        }

        with (
            patch.object(
                extractor._client, "get_file_content", side_effect=mock_get_file_content
            ),
            patch.object(
                extractor._client, "get_repo_metadata", return_value=mock_repo_metadata
            ),
        ):
            metadata = extractor.fetch_metadata("user/repo/agents/simple.md")

        # Frontmatter fields should be None
        assert metadata.title is None
        assert metadata.description is None
        assert metadata.author is None
        # But repo metadata should be present
        assert metadata.license == "Apache-2.0"
        assert "agents" in metadata.topics

    def test_fetch_metadata_invalid_source(self, extractor):
        """Test fetching with invalid source format."""
        with pytest.raises(ValueError, match="Invalid GitHub source"):
            extractor.fetch_metadata("invalid")

    def test_token_authentication(self):
        """Test that GitHub token is properly passed to client."""
        cache = MetadataCache()
        extractor = GitHubMetadataExtractor(cache=cache, token="test_token_123")

        # Token is now managed by GitHubClient
        assert extractor._client.token == "test_token_123"

    def test_token_from_environment(self):
        """Test that token is read from environment variable."""
        cache = MetadataCache()

        with patch.dict(
            "os.environ",
            {"GITHUB_TOKEN": "env_token_456"},
            clear=False,
        ):
            # Clear any cached config token
            with patch(
                "skillmeat.core.github_client.ConfigManager"
            ) as mock_config_class:
                mock_config = Mock()
                mock_config.get.return_value = None
                mock_config_class.return_value = mock_config
                extractor = GitHubMetadataExtractor(cache=cache)

        # Token is managed by GitHubClient and read from env
        assert extractor._client.token == "env_token_456"


class TestFrontmatterExtraction:
    """Test YAML frontmatter extraction."""

    @pytest.fixture
    def extractor(self):
        """Provide a GitHubMetadataExtractor."""
        return GitHubMetadataExtractor(cache=MetadataCache())

    def test_extract_frontmatter_valid(self, extractor):
        """Test extraction of valid YAML frontmatter."""
        content = """---
title: Test Skill
description: A test skill
author: test-author
tags:
  - testing
  - automation
version: 1.0.0
---

# Test Skill

Content here...
"""
        result = extractor._extract_frontmatter(content)

        assert result["title"] == "Test Skill"
        assert result["description"] == "A test skill"
        assert result["author"] == "test-author"
        assert "testing" in result["tags"]
        assert "automation" in result["tags"]
        assert result["version"] == "1.0.0"

    def test_extract_frontmatter_minimal(self, extractor):
        """Test extraction of minimal frontmatter."""
        content = """---
title: Minimal
---

Content
"""
        result = extractor._extract_frontmatter(content)

        assert result["title"] == "Minimal"
        assert len(result) == 1

    def test_extract_frontmatter_complex_nested(self, extractor):
        """Test extraction of complex nested YAML."""
        content = """---
title: Complex
metadata:
  key1: value1
  key2: value2
  nested:
    deep: value
dependencies:
  - dep1
  - dep2
---

Content
"""
        result = extractor._extract_frontmatter(content)

        assert result["title"] == "Complex"
        assert result["metadata"]["key1"] == "value1"
        assert result["metadata"]["nested"]["deep"] == "value"
        assert result["dependencies"] == ["dep1", "dep2"]

    def test_extract_frontmatter_missing(self, extractor):
        """Test handling of content without frontmatter."""
        content = """# Just a heading

No frontmatter here.
"""
        result = extractor._extract_frontmatter(content)

        assert result == {}

    def test_extract_frontmatter_not_at_start(self, extractor):
        """Test that frontmatter not at start is ignored."""
        content = """Some content first

---
title: Not at start
---
"""
        result = extractor._extract_frontmatter(content)

        assert result == {}

    def test_extract_frontmatter_malformed_yaml(self, extractor):
        """Test handling of malformed YAML in frontmatter."""
        content = """---
title: Test
invalid: yaml: here: broken
malformed: [unclosed
---

Content
"""
        result = extractor._extract_frontmatter(content)

        # Should handle gracefully and return empty dict
        assert result == {}

    def test_extract_frontmatter_empty(self, extractor):
        """Test handling of empty frontmatter block."""
        content = """---
---

Content only
"""
        result = extractor._extract_frontmatter(content)

        # Empty YAML returns None, which should be handled
        assert result == {}

    def test_extract_frontmatter_empty_string(self, extractor):
        """Test handling of empty string input."""
        result = extractor._extract_frontmatter("")
        assert result == {}

    def test_extract_frontmatter_whitespace_only(self, extractor):
        """Test handling of whitespace-only input."""
        result = extractor._extract_frontmatter("   \n\n  \n")
        assert result == {}

    def test_extract_frontmatter_none(self, extractor):
        """Test handling of None input."""
        result = extractor._extract_frontmatter(None)
        assert result == {}

    def test_extract_frontmatter_non_dict_yaml(self, extractor):
        """Test handling of YAML that doesn't parse to dict."""
        content = """---
- item1
- item2
---

Content
"""
        result = extractor._extract_frontmatter(content)

        # YAML list instead of dict, should return empty
        assert result == {}

    def test_extract_frontmatter_multiline_values(self, extractor):
        """Test extraction of multiline YAML values."""
        content = """---
title: Test
description: |
  This is a multiline
  description that spans
  several lines.
---

Content
"""
        result = extractor._extract_frontmatter(content)

        assert result["title"] == "Test"
        assert "multiline" in result["description"]
        assert "several lines" in result["description"]

    def test_extract_frontmatter_quoted_values(self, extractor):
        """Test extraction of quoted YAML values."""
        content = """---
title: "Quoted: With Colon"
description: 'Single quotes'
path: "path/to/file"
---

Content
"""
        result = extractor._extract_frontmatter(content)

        assert result["title"] == "Quoted: With Colon"
        assert result["description"] == "Single quotes"
        assert result["path"] == "path/to/file"

    def test_extract_frontmatter_boolean_numeric(self, extractor):
        """Test extraction of boolean and numeric values."""
        content = """---
enabled: true
disabled: false
version: 1.5
count: 42
---

Content
"""
        result = extractor._extract_frontmatter(content)

        assert result["enabled"] is True
        assert result["disabled"] is False
        assert result["version"] == 1.5
        assert result["count"] == 42


class TestFetchFileContent:
    """Test file content fetching from GitHub using GitHubClient."""

    @pytest.fixture
    def extractor(self):
        """Provide a GitHubMetadataExtractor."""
        return GitHubMetadataExtractor(cache=MetadataCache())

    def test_fetch_file_content_success(self, extractor):
        """Test successful file content fetch."""
        content = "# Test Content\n\nThis is a test file."

        with patch.object(
            extractor._client,
            "get_file_content",
            return_value=content.encode("utf-8"),
        ):
            result = extractor._fetch_file_content("owner", "repo", "path/to/file.md")

        assert result == content

    def test_fetch_file_content_404_not_found(self, extractor):
        """Test handling of 404 Not Found."""
        with patch.object(
            extractor._client,
            "get_file_content",
            side_effect=GitHubNotFoundError("File not found"),
        ):
            result = extractor._fetch_file_content("owner", "repo", "missing.md")

        assert result is None

    def test_fetch_file_content_rate_limit(self, extractor):
        """Test handling of rate limit error."""
        with patch.object(
            extractor._client,
            "get_file_content",
            side_effect=GitHubRateLimitError("Rate limit exceeded"),
        ):
            result = extractor._fetch_file_content("owner", "repo", "file.md")

        assert result is None

    def test_fetch_file_content_with_ref(self, extractor):
        """Test fetching file content with specific ref."""
        content = "Content"

        with patch.object(
            extractor._client,
            "get_file_content",
            return_value=content.encode("utf-8"),
        ) as mock_get:
            extractor._fetch_file_content("owner", "repo", "file.md", ref="v1.0.0")

            # Verify ref was passed
            mock_get.assert_called_once_with("owner/repo", "file.md", ref="v1.0.0")

    def test_fetch_file_content_head_ref(self, extractor):
        """Test that HEAD ref is converted to None (default branch)."""
        content = "Content"

        with patch.object(
            extractor._client,
            "get_file_content",
            return_value=content.encode("utf-8"),
        ) as mock_get:
            extractor._fetch_file_content("owner", "repo", "file.md", ref="HEAD")

            # HEAD should be converted to None
            mock_get.assert_called_once_with("owner/repo", "file.md", ref=None)


class TestFetchRepoMetadata:
    """Test repository metadata fetching using GitHubClient."""

    @pytest.fixture
    def extractor(self):
        """Provide a GitHubMetadataExtractor."""
        return GitHubMetadataExtractor(cache=MetadataCache())

    def test_fetch_repo_metadata_success(self, extractor):
        """Test successful repo metadata fetch."""
        mock_metadata = {
            "topics": ["python", "testing"],
            "license": "MIT",
            "description": "A great repo",
            "stars": 100,
        }

        with patch.object(
            extractor._client, "get_repo_metadata", return_value=mock_metadata
        ):
            result = extractor._fetch_repo_metadata("owner", "repo")

        assert result["topics"] == ["python", "testing"]
        # License is converted to dict format for backward compatibility
        assert result["license"]["spdx_id"] == "MIT"
        assert result["description"] == "A great repo"

    def test_fetch_repo_metadata_no_license(self, extractor):
        """Test repo metadata fetch with no license."""
        mock_metadata = {
            "topics": ["python"],
            "license": None,
            "description": "No license",
        }

        with patch.object(
            extractor._client, "get_repo_metadata", return_value=mock_metadata
        ):
            result = extractor._fetch_repo_metadata("owner", "repo")

        assert result["topics"] == ["python"]
        assert result["license"] is None

    def test_fetch_repo_metadata_error(self, extractor):
        """Test handling of repo metadata fetch error."""
        with patch.object(
            extractor._client,
            "get_repo_metadata",
            side_effect=GitHubClientError("API error"),
        ):
            result = extractor._fetch_repo_metadata("owner", "repo")

        assert result == {}

    def test_fetch_repo_metadata_rate_limit(self, extractor):
        """Test handling of rate limit error."""
        with patch.object(
            extractor._client,
            "get_repo_metadata",
            side_effect=GitHubRateLimitError("Rate limit exceeded"),
        ):
            result = extractor._fetch_repo_metadata("owner", "repo")

        assert result == {}


class TestGitHubSourceSpec:
    """Test GitHubSourceSpec Pydantic model."""

    def test_source_spec_creation(self):
        """Test creating a GitHubSourceSpec."""
        spec = GitHubSourceSpec(
            owner="anthropics",
            repo="skills",
            path="canvas-design",
            version="v1.0.0",
        )

        assert spec.owner == "anthropics"
        assert spec.repo == "skills"
        assert spec.path == "canvas-design"
        assert spec.version == "v1.0.0"

    def test_source_spec_default_version(self):
        """Test that version defaults to 'latest'."""
        spec = GitHubSourceSpec(
            owner="user",
            repo="repo",
            path="path",
        )

        assert spec.version == "latest"


class TestGitHubMetadata:
    """Test GitHubMetadata Pydantic model."""

    def test_metadata_creation_full(self):
        """Test creating GitHubMetadata with all fields."""
        now = datetime.now()
        metadata = GitHubMetadata(
            title="Test Artifact",
            description="A test artifact",
            author="Test Author",
            license="MIT",
            topics=["testing", "python"],
            url="https://github.com/user/repo",
            fetched_at=now,
            source="auto-populated",
        )

        assert metadata.title == "Test Artifact"
        assert metadata.description == "A test artifact"
        assert metadata.author == "Test Author"
        assert metadata.license == "MIT"
        assert metadata.topics == ["testing", "python"]
        assert metadata.url == "https://github.com/user/repo"
        assert metadata.fetched_at == now
        assert metadata.source == "auto-populated"

    def test_metadata_creation_minimal(self):
        """Test creating GitHubMetadata with minimal fields."""
        metadata = GitHubMetadata(
            url="https://github.com/user/repo",
            fetched_at=datetime.now(),
        )

        assert metadata.title is None
        assert metadata.description is None
        assert metadata.author is None
        assert metadata.license is None
        assert metadata.topics == []
        assert metadata.source == "auto-populated"

    def test_metadata_serialization(self):
        """Test serializing GitHubMetadata to dict."""
        now = datetime.now()
        metadata = GitHubMetadata(
            title="Test",
            url="https://github.com/user/repo",
            fetched_at=now,
            topics=["test"],
        )

        data = metadata.model_dump()

        assert data["title"] == "Test"
        assert data["url"] == "https://github.com/user/repo"
        assert data["topics"] == ["test"]
