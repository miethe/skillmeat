"""Tests for README link harvester.

Tests cover:
- GitHub URL extraction from markdown
- Link normalization and deduplication
- Confidence scoring based on context
- Cycle protection for recursive discovery
- Edge cases (malformed URLs, relative links, etc.)
"""

import pytest

from skillmeat.core.marketplace.link_harvester import (
    HarvestConfig,
    HarvestedLink,
    ReadmeLinkHarvester,
    harvest_readme_links,
)


class TestHarvestConfig:
    """Test suite for HarvestConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = HarvestConfig()
        assert config.max_depth == 1
        assert len(config.github_patterns) > 0
        assert len(config.ignore_patterns) > 0
        assert len(config.artifact_keywords) > 0

    def test_custom_config(self):
        """Test custom configuration."""
        config = HarvestConfig(
            max_depth=3,
            artifact_keywords={"test", "custom"},
        )
        assert config.max_depth == 3
        assert "test" in config.artifact_keywords
        assert "custom" in config.artifact_keywords


class TestReadmeLinkHarvester:
    """Test suite for ReadmeLinkHarvester."""

    @pytest.fixture
    def harvester(self):
        """Create a link harvester with default config."""
        return ReadmeLinkHarvester()

    def test_harvest_single_link(self, harvester):
        """Test harvesting a single GitHub link."""
        content = "Check out https://github.com/anthropics/skills"
        links = harvester.harvest_links(content, "https://github.com/source/repo")

        assert len(links) == 1
        assert links[0].owner == "anthropics"
        assert links[0].repo == "skills"
        assert links[0].url == "https://github.com/anthropics/skills"

    def test_harvest_multiple_links(self, harvester):
        """Test harvesting multiple GitHub links."""
        content = """
        - https://github.com/user1/repo1
        - https://github.com/user2/repo2
        - https://github.com/user3/repo3
        """
        links = harvester.harvest_links(content, "https://github.com/source/repo")

        assert len(links) == 3
        assert {link.owner for link in links} == {"user1", "user2", "user3"}

    def test_harvest_link_without_https(self, harvester):
        """Test harvesting links without https:// prefix."""
        content = "See github.com/anthropics/skills for more"
        links = harvester.harvest_links(content, "https://github.com/source/repo")

        assert len(links) == 1
        assert links[0].url == "https://github.com/anthropics/skills"

    def test_harvest_markdown_links(self, harvester):
        """Test harvesting links from markdown syntax."""
        content = """
        # Resources
        - [Skills](https://github.com/anthropics/skills)
        - [Commands](https://github.com/anthropics/commands)
        """
        links = harvester.harvest_links(content, "https://github.com/source/repo")

        assert len(links) == 2
        repos = {link.repo for link in links}
        assert "skills" in repos
        assert "commands" in repos

    def test_normalize_url_basic(self, harvester):
        """Test basic URL normalization."""
        url = "https://github.com/user/repo"
        normalized = harvester._normalize_url(url)
        assert normalized == "https://github.com/user/repo"

    def test_normalize_url_with_git_suffix(self, harvester):
        """Test normalization removes .git suffix."""
        url = "https://github.com/user/repo.git"
        normalized = harvester._normalize_url(url)
        assert normalized == "https://github.com/user/repo"

    def test_normalize_url_without_scheme(self, harvester):
        """Test normalization adds https:// scheme."""
        url = "github.com/user/repo"
        normalized = harvester._normalize_url(url)
        assert normalized == "https://github.com/user/repo"

    def test_normalize_url_with_www(self, harvester):
        """Test normalization handles www subdomain."""
        url = "https://www.github.com/user/repo"
        normalized = harvester._normalize_url(url)
        assert normalized == "https://github.com/user/repo"

    def test_normalize_url_with_trailing_path(self, harvester):
        """Test normalization extracts only owner/repo."""
        url = "https://github.com/user/repo/tree/main/skills"
        normalized = harvester._normalize_url(url)
        # Should normalize to just owner/repo
        assert normalized == "https://github.com/user/repo"

    def test_normalize_url_invalid_domain(self, harvester):
        """Test normalization rejects non-GitHub domains."""
        url = "https://gitlab.com/user/repo"
        normalized = harvester._normalize_url(url)
        assert normalized is None

    def test_ignore_patterns_issues(self, harvester):
        """Test that issue URLs are ignored."""
        content = """
        - https://github.com/user/repo
        - https://github.com/user/repo/issues/123
        - https://github.com/user/repo/issues
        """
        links = harvester.harvest_links(content, "https://github.com/source/repo")

        # Only the base repo URL should be captured
        assert len(links) == 1
        assert links[0].repo == "repo"

    def test_ignore_patterns_pulls(self, harvester):
        """Test that pull request URLs are ignored."""
        content = """
        - https://github.com/user/repo
        - https://github.com/user/repo/pull/456
        - https://github.com/user/repo/pulls
        """
        links = harvester.harvest_links(content, "https://github.com/source/repo")

        assert len(links) == 1

    def test_ignore_patterns_blob_tree(self, harvester):
        """Test that blob/tree URLs are ignored."""
        content = """
        - https://github.com/user/repo
        - https://github.com/user/repo/blob/main/file.py
        - https://github.com/user/repo/tree/main/dir
        """
        links = harvester.harvest_links(content, "https://github.com/source/repo")

        assert len(links) == 1

    def test_deduplication(self, harvester):
        """Test that duplicate URLs are deduplicated."""
        content = """
        - https://github.com/user/repo
        - https://github.com/user/repo
        - https://github.com/user/repo.git
        """
        links = harvester.harvest_links(content, "https://github.com/source/repo")

        # All three should normalize to the same URL
        assert len(links) == 1

    def test_confidence_scoring_artifact_keywords(self, harvester):
        """Test confidence increases with artifact keywords in context."""
        content_high = "This Claude skill repository has great skills: https://github.com/user/claude-skills"
        content_low = "Some random repository: https://github.com/user/random-repo"

        links_high = harvester.harvest_links(
            content_high, "https://github.com/source/repo"
        )
        links_low = harvester.harvest_links(
            content_low, "https://github.com/source/repo"
        )

        assert len(links_high) == 1
        assert len(links_low) == 1
        assert links_high[0].confidence > links_low[0].confidence

    def test_confidence_scoring_repo_name(self, harvester):
        """Test confidence increases for artifact keywords in repo name."""
        content = """
        - https://github.com/user/claude-skills
        - https://github.com/user/random-lib
        """
        links = harvester.harvest_links(content, "https://github.com/source/repo")

        assert len(links) == 2
        skills_link = next(l for l in links if "skills" in l.repo)
        random_link = next(l for l in links if "random" in l.repo)
        assert skills_link.confidence > random_link.confidence

    def test_confidence_scoring_trusted_org(self, harvester):
        """Test confidence bonus for trusted organizations."""
        content = """
        - https://github.com/anthropics/skills
        - https://github.com/random-user/skills
        """
        links = harvester.harvest_links(content, "https://github.com/source/repo")

        assert len(links) == 2
        anthropic_link = next(l for l in links if l.owner == "anthropics")
        random_link = next(l for l in links if l.owner == "random-user")
        assert anthropic_link.confidence > random_link.confidence

    def test_context_extraction(self, harvester):
        """Test that context around links is extracted."""
        content = (
            "This is a long text about artifacts. "
            + "A" * 200  # Padding
            + "Check out https://github.com/user/repo for skills. "
            + "B" * 200  # Padding
        )
        links = harvester.harvest_links(content, "https://github.com/source/repo")

        assert len(links) == 1
        assert "skills" in links[0].context.lower()
        # Context should be truncated
        assert len(links[0].context) <= 220  # 100 before + 100 after + url

    def test_cycle_protection_visited(self, harvester):
        """Test that visited URLs are not returned again."""
        content1 = "https://github.com/user/repo1"
        content2 = "https://github.com/user/repo1"  # Same URL

        links1 = harvester.harvest_links(content1, "https://github.com/source/repo")
        links2 = harvester.harvest_links(content2, "https://github.com/source/repo")

        assert len(links1) == 1
        assert len(links2) == 0  # Already visited

    def test_cycle_protection_source_url(self, harvester):
        """Test that source URL is marked as visited."""
        content = "https://github.com/source/repo"
        links = harvester.harvest_links(content, "https://github.com/source/repo")

        # Source URL should be skipped
        assert len(links) == 0

    def test_reset_visited(self, harvester):
        """Test resetting visited set."""
        content = "https://github.com/user/repo"

        links1 = harvester.harvest_links(content, "https://github.com/source/repo")
        assert len(links1) == 1

        harvester.reset_visited()

        links2 = harvester.harvest_links(content, "https://github.com/source/repo2")
        assert len(links2) == 1

    def test_add_visited(self, harvester):
        """Test pre-seeding visited URLs."""
        harvester.add_visited(
            [
                "https://github.com/user/repo1",
                "https://github.com/user/repo2.git",
            ]
        )

        content = """
        - https://github.com/user/repo1
        - https://github.com/user/repo2
        - https://github.com/user/repo3
        """
        links = harvester.harvest_links(content, "https://github.com/source/repo")

        # Only repo3 should be returned
        assert len(links) == 1
        assert links[0].repo == "repo3"

    def test_max_depth_zero(self, harvester):
        """Test that depth 0 returns empty list."""
        content = "https://github.com/user/repo"
        links = harvester.harvest_links(content, "https://github.com/source/repo", current_depth=0)

        # Should find links at depth 0
        assert len(links) == 1

        # But depth 1 (max_depth=1) should be skipped
        links = harvester.harvest_links(content, "https://github.com/source/repo", current_depth=1)
        assert len(links) == 0

    def test_depth_tracking(self, harvester):
        """Test that discovery depth is tracked."""
        content = "https://github.com/user/repo"
        links = harvester.harvest_links(content, "https://github.com/source/repo", current_depth=0)

        assert len(links) == 1
        assert links[0].depth == 1  # depth increments by 1

    def test_parse_github_url_success(self, harvester):
        """Test successful URL parsing."""
        url = "https://github.com/anthropics/skills"
        owner, repo = harvester._parse_github_url(url)

        assert owner == "anthropics"
        assert repo == "skills"

    def test_parse_github_url_invalid(self, harvester):
        """Test parsing invalid URL."""
        url = "https://github.com/"
        result = harvester._parse_github_url(url)

        assert result is None

    def test_sort_by_confidence(self, harvester):
        """Test that results are sorted by confidence descending."""
        content = """
        - https://github.com/random/repo (just a repo)
        - https://github.com/anthropics/claude-skills (Claude skills collection)
        - https://github.com/user/my-skill (my skill)
        """
        links = harvester.harvest_links(content, "https://github.com/source/repo")

        assert len(links) == 3
        # Should be sorted with highest confidence first
        for i in range(len(links) - 1):
            assert links[i].confidence >= links[i + 1].confidence

    def test_empty_content(self, harvester):
        """Test handling of empty content."""
        content = ""
        links = harvester.harvest_links(content, "https://github.com/source/repo")

        assert len(links) == 0

    def test_no_github_links(self, harvester):
        """Test content with no GitHub links."""
        content = """
        # My Project
        This is a project about things.
        Visit https://example.com for more info.
        """
        links = harvester.harvest_links(content, "https://github.com/source/repo")

        assert len(links) == 0

    def test_mixed_link_formats(self, harvester):
        """Test various link formats in same content."""
        content = """
        - https://github.com/user1/repo1
        - [Repo 2](https://github.com/user2/repo2)
        - github.com/user3/repo3
        - Check out user4/repo4 on GitHub: https://github.com/user4/repo4.git
        """
        links = harvester.harvest_links(content, "https://github.com/source/repo")

        assert len(links) == 4
        owners = {link.owner for link in links}
        assert owners == {"user1", "user2", "user3", "user4"}


class TestHarvestReadmeLinks:
    """Test suite for harvest_readme_links convenience function."""

    def test_basic_harvest(self):
        """Test basic link harvesting."""
        content = "Check out https://github.com/anthropics/skills"
        links = harvest_readme_links(content, "https://github.com/source/repo")

        assert len(links) == 1
        assert links[0].owner == "anthropics"

    def test_custom_max_depth(self):
        """Test with custom max_depth."""
        content = "https://github.com/user/repo"
        config = HarvestConfig(max_depth=5)
        harvester = ReadmeLinkHarvester(config)

        # At depth 5, should still find links
        links = harvester.harvest_links(content, "https://github.com/source/repo", current_depth=4)
        assert len(links) == 1

        # At depth 6, should skip
        links = harvester.harvest_links(content, "https://github.com/source/repo", current_depth=5)
        assert len(links) == 0

    def test_readme_with_sections(self):
        """Test harvesting from a realistic README structure."""
        content = """
        # My Project

        ## Installation
        Install dependencies...

        ## Related Projects
        - [Anthropic Skills](https://github.com/anthropics/skills) - Official skills
        - [My Skills](https://github.com/user/my-skills) - Custom collection
        - [Another Project](https://github.com/other/project)

        ## Contributing
        See [issues](https://github.com/user/repo/issues) for details.
        """

        links = harvest_readme_links(content, "https://github.com/user/repo")

        # Should find 3 repo links (issues URL should be filtered)
        assert len(links) == 3
        repos = {link.repo for link in links}
        assert "skills" in repos
        assert "my-skills" in repos
        assert "project" in repos


class TestEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    def test_url_with_special_characters(self):
        """Test URLs with special characters in repo name."""
        harvester = ReadmeLinkHarvester()
        content = "https://github.com/user/my-repo-v2"
        links = harvester.harvest_links(content, "https://github.com/source/repo")

        assert len(links) == 1
        assert links[0].repo == "my-repo-v2"

    def test_url_with_numbers(self):
        """Test URLs with numbers in owner/repo."""
        harvester = ReadmeLinkHarvester()
        content = "https://github.com/user123/repo456"
        links = harvester.harvest_links(content, "https://github.com/source/repo")

        assert len(links) == 1
        assert links[0].owner == "user123"
        assert links[0].repo == "repo456"

    def test_url_with_dots_dashes(self):
        """Test URLs with dots and dashes."""
        harvester = ReadmeLinkHarvester()
        content = "https://github.com/my.user/my-repo.name"
        links = harvester.harvest_links(content, "https://github.com/source/repo")

        assert len(links) == 1
        assert links[0].owner == "my.user"
        assert links[0].repo == "my-repo.name"

    def test_malformed_url_incomplete(self):
        """Test handling of incomplete URLs."""
        harvester = ReadmeLinkHarvester()
        content = "https://github.com/user"  # Missing repo
        links = harvester.harvest_links(content, "https://github.com/source/repo")

        # Should not match (requires owner/repo)
        assert len(links) == 0

    def test_confidence_score_bounds(self):
        """Test that confidence scores are within bounds."""
        harvester = ReadmeLinkHarvester()
        content = """
        Claude skill agent command artifact template prompt
        https://github.com/anthropics/claude-skills-artifacts-commands
        """
        links = harvester.harvest_links(content, "https://github.com/source/repo")

        assert len(links) == 1
        # Confidence should be capped at 1.0
        assert 0.0 <= links[0].confidence <= 1.0

    def test_very_long_readme(self):
        """Test harvesting from a very long README."""
        harvester = ReadmeLinkHarvester()

        # Create long content with links scattered throughout
        parts = []
        for i in range(100):
            parts.append(f"Some text here. More text. " * 10)
            if i % 10 == 0:
                parts.append(f"https://github.com/user/repo{i}")

        content = "\n".join(parts)
        links = harvester.harvest_links(content, "https://github.com/source/repo")

        # Should find all 10 unique links
        assert len(links) == 10

    def test_unicode_in_context(self):
        """Test handling of unicode in surrounding context."""
        harvester = ReadmeLinkHarvester()
        content = "日本語のテキスト https://github.com/user/repo でスキルを共有"
        links = harvester.harvest_links(content, "https://github.com/source/repo")

        assert len(links) == 1
        assert "日本語" in links[0].context

    def test_multiple_patterns_same_url(self):
        """Test that same URL matched by different patterns is deduplicated."""
        harvester = ReadmeLinkHarvester()
        content = """
        https://github.com/user/repo
        github.com/user/repo
        """
        links = harvester.harvest_links(content, "https://github.com/source/repo")

        # Both should normalize to same URL
        assert len(links) == 1
