"""Unit tests for GitHub metadata extraction service.

Tests the GitHubMetadataExtractor class including URL parsing, metadata fetching,
frontmatter extraction, and error handling.
"""

import base64
import time
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
import requests
import yaml

from skillmeat.core.cache import MetadataCache
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
    """Test metadata fetching functionality with mocked HTTP."""

    @pytest.fixture
    def mock_cache(self):
        """Provide a fresh MetadataCache for each test."""
        return MetadataCache()

    @pytest.fixture
    def extractor(self, mock_cache):
        """Provide a GitHubMetadataExtractor with mock cache."""
        return GitHubMetadataExtractor(cache=mock_cache)

    def test_fetch_metadata_success(self, extractor, mock_cache):
        """Test successful metadata fetch with mocked GitHub API."""
        # Mock file content endpoint (SKILL.md)
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
        encoded_content = base64.b64encode(skill_content.encode("utf-8")).decode("utf-8")

        file_response = Mock()
        file_response.status_code = 200
        file_response.json.return_value = {"content": encoded_content}
        file_response.raise_for_status = Mock()

        # Mock repo metadata endpoint
        repo_response = Mock()
        repo_response.status_code = 200
        repo_response.json.return_value = {
            "topics": ["design", "art", "canvas"],
            "license": {"spdx_id": "MIT"},
        }
        repo_response.raise_for_status = Mock()

        with patch.object(extractor.session, "get") as mock_get:
            mock_get.side_effect = [file_response, repo_response]

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
        encoded_content = base64.b64encode(readme_content.encode("utf-8")).decode("utf-8")

        # Mock 404 for SKILL.md, COMMAND.md, AGENT.md, then success for README.md
        not_found_response = Mock()
        not_found_response.status_code = 404

        readme_response = Mock()
        readme_response.status_code = 200
        readme_response.json.return_value = {"content": encoded_content}
        readme_response.raise_for_status = Mock()

        repo_response = Mock()
        repo_response.status_code = 200
        repo_response.json.return_value = {"topics": [], "license": None}
        repo_response.raise_for_status = Mock()

        with patch.object(extractor.session, "get") as mock_get:
            # SKILL.md, COMMAND.md, AGENT.md return 404, README.md succeeds, then repo
            mock_get.side_effect = [
                not_found_response,  # SKILL.md
                not_found_response,  # COMMAND.md
                not_found_response,  # AGENT.md
                readme_response,     # README.md
                repo_response,       # repo metadata
            ]

            metadata = extractor.fetch_metadata("user/repo/project")

        assert metadata.title == "My Project"
        assert metadata.description == "A great project"

    def test_fetch_metadata_no_frontmatter(self, extractor):
        """Test metadata fetch when no files have frontmatter."""
        # Mock all files return 404
        not_found_response = Mock()
        not_found_response.status_code = 404

        repo_response = Mock()
        repo_response.status_code = 200
        repo_response.json.return_value = {
            "topics": ["python"],
            "license": {"spdx_id": "Apache-2.0"},
        }
        repo_response.raise_for_status = Mock()

        with patch.object(extractor.session, "get") as mock_get:
            # All metadata files 404, then repo metadata
            mock_get.side_effect = [
                not_found_response,
                not_found_response,
                not_found_response,
                not_found_response,
                repo_response,
            ]

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
        not_found_response = Mock()
        not_found_response.status_code = 404

        error_response = Mock()
        error_response.status_code = 404
        error_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=Mock(status_code=404)
        )

        with patch.object(extractor.session, "get") as mock_get:
            # All file requests 404, repo metadata also fails (with retries)
            mock_get.side_effect = [
                not_found_response,  # SKILL.md
                not_found_response,  # COMMAND.md
                not_found_response,  # AGENT.md
                not_found_response,  # README.md
                error_response,      # repo metadata attempt 1
                error_response,      # repo metadata attempt 2
                error_response,      # repo metadata attempt 3
            ]

            with patch("time.sleep"):  # Mock sleep to speed up test
                metadata = extractor.fetch_metadata("user/nonexistent/project")

        # Should still return metadata with minimal info
        assert metadata.title is None
        assert metadata.topics == []

    def test_fetch_metadata_github_error_500(self, extractor):
        """Test handling of 500 Internal Server Error."""
        error_response = Mock()
        error_response.status_code = 500
        error_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=Mock(status_code=500)
        )

        with patch.object(extractor.session, "get") as mock_get:
            mock_get.return_value = error_response

            metadata = extractor.fetch_metadata("user/repo/project")

        # Should handle gracefully and return basic metadata
        assert metadata is not None
        assert metadata.title is None

    def test_fetch_metadata_rate_limited_429(self, extractor):
        """Test handling of 429 rate limit response."""
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429

        with patch.object(extractor.session, "get") as mock_get:
            mock_get.return_value = rate_limit_response

            with pytest.raises(RuntimeError, match="rate limit exceeded"):
                extractor.fetch_metadata("user/repo/project")

    def test_fetch_metadata_rate_limited_403(self, extractor):
        """Test handling of 403 with rate limit message."""
        forbidden_response = Mock()
        forbidden_response.status_code = 403
        forbidden_response.text = "API rate limit exceeded for your IP"
        forbidden_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=Mock(status_code=403)
        )

        with patch.object(extractor.session, "get") as mock_get:
            mock_get.return_value = forbidden_response

            with pytest.raises(RuntimeError, match="rate limit exceeded"):
                extractor.fetch_metadata("user/repo/project")

    def test_fetch_metadata_timeout(self, extractor):
        """Test handling of request timeout."""
        with patch.object(extractor.session, "get") as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

            # Should handle gracefully after retries
            metadata = extractor.fetch_metadata("user/repo/project")

        assert metadata is not None
        assert metadata.title is None

    def test_fetch_metadata_network_error(self, extractor):
        """Test handling of network connection errors."""
        with patch.object(extractor.session, "get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

            # Should handle gracefully after retries
            metadata = extractor.fetch_metadata("user/repo/project")

        assert metadata is not None
        assert metadata.title is None

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

        with patch.object(extractor.session, "get") as mock_get:
            metadata = extractor.fetch_metadata("user/repo/artifact")

            # Verify no HTTP requests made
            mock_get.assert_not_called()

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
        encoded_content = base64.b64encode(skill_content.encode("utf-8")).decode("utf-8")

        file_response = Mock()
        file_response.status_code = 200
        file_response.json.return_value = {"content": encoded_content}
        file_response.raise_for_status = Mock()

        repo_response = Mock()
        repo_response.status_code = 200
        repo_response.json.return_value = {"topics": [], "license": None}
        repo_response.raise_for_status = Mock()

        with patch.object(extractor.session, "get") as mock_get:
            mock_get.side_effect = [file_response, repo_response]

            metadata = extractor.fetch_metadata("user/repo/fresh")

        assert metadata.title == "Fresh Data"

        # Verify data was cached
        cached = mock_cache.get("github_metadata:user/repo/fresh")
        assert cached is not None
        assert cached["title"] == "Fresh Data"

    def test_fetch_metadata_invalid_source(self, extractor):
        """Test fetching with invalid source format."""
        with pytest.raises(ValueError, match="Invalid GitHub source"):
            extractor.fetch_metadata("invalid")

    def test_token_authentication(self):
        """Test that GitHub token is properly configured."""
        cache = MetadataCache()
        extractor = GitHubMetadataExtractor(cache=cache, token="test_token_123")

        assert extractor.token == "test_token_123"
        assert "Authorization" in extractor.session.headers
        assert extractor.session.headers["Authorization"] == "token test_token_123"

    def test_token_from_environment(self):
        """Test that token is read from environment variable."""
        cache = MetadataCache()

        with patch.dict("os.environ", {"GITHUB_TOKEN": "env_token_456"}):
            extractor = GitHubMetadataExtractor(cache=cache)

        assert extractor.token == "env_token_456"
        assert extractor.session.headers["Authorization"] == "token env_token_456"


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


class TestRetryWithBackoff:
    """Test retry mechanism with exponential backoff."""

    @pytest.fixture
    def extractor(self):
        """Provide a GitHubMetadataExtractor."""
        return GitHubMetadataExtractor(cache=MetadataCache())

    def test_retry_success_first_attempt(self, extractor):
        """Test successful function call on first attempt."""
        mock_func = Mock(return_value="success")

        result = extractor._retry_with_backoff(mock_func, max_retries=3)

        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_success_after_failure(self, extractor):
        """Test successful function call after initial failures."""
        mock_func = Mock()
        mock_func.side_effect = [
            requests.exceptions.RequestException("First failure"),
            requests.exceptions.RequestException("Second failure"),
            "success",
        ]

        with patch("time.sleep"):  # Mock sleep to speed up test
            result = extractor._retry_with_backoff(mock_func, max_retries=3)

        assert result == "success"
        assert mock_func.call_count == 3

    def test_retry_max_retries_exceeded(self, extractor):
        """Test that exception is raised after max retries."""
        mock_func = Mock()
        mock_func.side_effect = requests.exceptions.RequestException("Persistent error")

        with patch("time.sleep"):
            with pytest.raises(requests.exceptions.RequestException, match="Persistent error"):
                extractor._retry_with_backoff(mock_func, max_retries=3)

        assert mock_func.call_count == 3

    def test_retry_exponential_backoff(self, extractor):
        """Test that backoff timing increases exponentially."""
        mock_func = Mock()
        mock_func.side_effect = [
            requests.exceptions.RequestException("Error 1"),
            requests.exceptions.RequestException("Error 2"),
            "success",
        ]

        with patch("time.sleep") as mock_sleep:
            result = extractor._retry_with_backoff(mock_func, max_retries=3)

        # Should have called sleep with 2^0=1 and 2^1=2 seconds
        assert mock_sleep.call_count == 2
        sleep_times = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_times == [1, 2]  # 2^0, 2^1

    def test_retry_non_request_exception_not_retried(self, extractor):
        """Test that non-RequestException errors are not retried."""
        mock_func = Mock(side_effect=ValueError("Not a request error"))

        with pytest.raises(ValueError, match="Not a request error"):
            extractor._retry_with_backoff(mock_func, max_retries=3)

        assert mock_func.call_count == 1


class TestFetchFileContent:
    """Test file content fetching from GitHub."""

    @pytest.fixture
    def extractor(self):
        """Provide a GitHubMetadataExtractor."""
        return GitHubMetadataExtractor(cache=MetadataCache())

    def test_fetch_file_content_success(self, extractor):
        """Test successful file content fetch."""
        content = "# Test Content\n\nThis is a test file."
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        response = Mock()
        response.status_code = 200
        response.json.return_value = {"content": encoded}
        response.raise_for_status = Mock()

        with patch.object(extractor.session, "get", return_value=response):
            result = extractor._fetch_file_content("owner", "repo", "path/to/file.md")

        assert result == content

    def test_fetch_file_content_404_not_found(self, extractor):
        """Test handling of 404 Not Found."""
        response = Mock()
        response.status_code = 404

        with patch.object(extractor.session, "get", return_value=response):
            result = extractor._fetch_file_content("owner", "repo", "missing.md")

        assert result is None

    def test_fetch_file_content_no_content_field(self, extractor):
        """Test handling of response without content field."""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {}  # No content field
        response.raise_for_status = Mock()

        with patch.object(extractor.session, "get", return_value=response):
            result = extractor._fetch_file_content("owner", "repo", "file.md")

        assert result is None

    def test_fetch_file_content_with_ref(self, extractor):
        """Test fetching file content with specific ref."""
        content = "Content"
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        response = Mock()
        response.status_code = 200
        response.json.return_value = {"content": encoded}
        response.raise_for_status = Mock()

        with patch.object(extractor.session, "get", return_value=response) as mock_get:
            extractor._fetch_file_content("owner", "repo", "file.md", ref="v1.0.0")

            # Verify ref was passed in params
            call_args = mock_get.call_args
            assert call_args[1]["params"] == {"ref": "v1.0.0"}


class TestFetchRepoMetadata:
    """Test repository metadata fetching."""

    @pytest.fixture
    def extractor(self):
        """Provide a GitHubMetadataExtractor."""
        return GitHubMetadataExtractor(cache=MetadataCache())

    def test_fetch_repo_metadata_success(self, extractor):
        """Test successful repo metadata fetch."""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "topics": ["python", "testing"],
            "license": {"spdx_id": "MIT"},
            "description": "A great repo",
            "stargazers_count": 100,
        }
        response.raise_for_status = Mock()

        with patch.object(extractor.session, "get", return_value=response):
            result = extractor._fetch_repo_metadata("owner", "repo")

        assert result["topics"] == ["python", "testing"]
        assert result["license"]["spdx_id"] == "MIT"
        assert result["description"] == "A great repo"

    def test_fetch_repo_metadata_error(self, extractor):
        """Test handling of repo metadata fetch error."""
        response = Mock()
        response.raise_for_status.side_effect = requests.exceptions.HTTPError()

        with patch.object(extractor.session, "get", return_value=response):
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
