"""README link harvester for secondary repository discovery.

Parses README files to find GitHub repository links that may contain
Claude Code artifacts, with deduplication and cycle protection.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class HarvestConfig:
    """Configuration for README link harvesting."""

    # Maximum depth for recursive discovery
    max_depth: int = 1

    # Patterns to match GitHub repo URLs
    github_patterns: List[str] = field(
        default_factory=lambda: [
            r"https?://github\.com/[\w.-]+/[\w.-]+",
            r"github\.com/[\w.-]+/[\w.-]+",
        ]
    )

    # URL patterns to ignore (forks, issues, pulls, etc.)
    ignore_patterns: List[str] = field(
        default_factory=lambda: [
            r"/issues(/|$)",
            r"/pull(/|$)",
            r"/pulls(/|$)",
            r"/actions(/|$)",
            r"/releases(/|$)",
            r"/wiki(/|$)",
            r"/commit(/|$)",
            r"/blob(/|$)",
            r"/tree(/|$)",
            r"/compare(/|$)",
        ]
    )

    # Keywords that indicate artifact-related repos
    artifact_keywords: Set[str] = field(
        default_factory=lambda: {
            "skill",
            "skills",
            "claude",
            "artifact",
            "artifacts",
            "command",
            "commands",
            "agent",
            "agents",
            "mcp",
            "prompt",
            "prompts",
            "template",
            "templates",
        }
    )


@dataclass
class HarvestedLink:
    """A discovered GitHub repository link."""

    url: str  # Normalized GitHub URL
    owner: str
    repo: str
    context: str  # Text surrounding the link
    confidence: float  # 0.0-1.0 based on context relevance
    depth: int  # Discovery depth (0 = original, 1 = from README, etc.)


class ReadmeLinkHarvester:
    """Harvests GitHub repository links from README content.

    Extracts links, filters to relevant repositories, deduplicates,
    and provides cycle protection for recursive discovery.

    Example:
        >>> harvester = ReadmeLinkHarvester()
        >>> links = harvester.harvest_links(readme_content, source_url)
        >>> for link in links:
        ...     print(f"Found: {link.owner}/{link.repo} (confidence: {link.confidence})")
    """

    def __init__(self, config: Optional[HarvestConfig] = None):
        """Initialize harvester with optional custom configuration."""
        self.config = config or HarvestConfig()
        self._visited: Set[str] = set()  # Cycle protection

    def harvest_links(
        self,
        content: str,
        source_url: str,
        current_depth: int = 0,
    ) -> List[HarvestedLink]:
        """Extract GitHub repository links from README content.

        Args:
            content: README markdown content
            source_url: URL of the source repository (for dedup)
            current_depth: Current discovery depth

        Returns:
            List of HarvestedLink objects sorted by confidence (highest first)
        """
        if current_depth >= self.config.max_depth:
            logger.debug(f"Max depth {self.config.max_depth} reached, skipping")
            return []

        # Mark source as visited
        normalized_source = self._normalize_url(source_url)
        self._visited.add(normalized_source)

        links: List[HarvestedLink] = []

        # Find all GitHub URLs in content
        for pattern in self.config.github_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                url = match.group(0)

                # Get context (surrounding text)
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 100)
                context = content[start:end]

                # Process the URL
                link = self._process_url(url, context, current_depth + 1)
                if link and link.url not in self._visited:
                    links.append(link)
                    self._visited.add(link.url)

        # Sort by confidence
        links.sort(key=lambda l: l.confidence, reverse=True)

        logger.info(f"Harvested {len(links)} links from {source_url}")
        return links

    def _process_url(
        self,
        url: str,
        context: str,
        depth: int,
    ) -> Optional[HarvestedLink]:
        """Process a URL and create a HarvestedLink if valid."""
        # Normalize URL
        normalized = self._normalize_url(url)
        if not normalized:
            return None

        # Check ignore patterns
        for pattern in self.config.ignore_patterns:
            if re.search(pattern, normalized, re.IGNORECASE):
                return None

        # Parse owner/repo
        parsed = self._parse_github_url(normalized)
        if not parsed:
            return None

        owner, repo = parsed

        # Calculate confidence based on context
        confidence = self._calculate_confidence(context, owner, repo)

        return HarvestedLink(
            url=normalized,
            owner=owner,
            repo=repo,
            context=context.strip(),
            confidence=confidence,
            depth=depth,
        )

    def _normalize_url(self, url: str) -> Optional[str]:
        """Normalize a GitHub URL to standard format."""
        # Add scheme if missing
        if not url.startswith("http"):
            url = "https://" + url

        # Parse and reconstruct
        try:
            parsed = urlparse(url)
            if parsed.netloc not in ("github.com", "www.github.com"):
                return None

            # Extract path parts
            path_parts = parsed.path.strip("/").split("/")
            if len(path_parts) < 2:
                return None

            owner, repo = path_parts[0], path_parts[1]

            # Remove .git suffix
            repo = repo.removesuffix(".git")

            return f"https://github.com/{owner}/{repo}"

        except Exception:
            return None

    def _parse_github_url(self, url: str) -> Optional[Tuple[str, str]]:
        """Parse owner and repo from GitHub URL."""
        try:
            parsed = urlparse(url)
            path_parts = parsed.path.strip("/").split("/")
            if len(path_parts) >= 2:
                return path_parts[0], path_parts[1]
        except Exception:
            pass
        return None

    def _calculate_confidence(
        self,
        context: str,
        owner: str,
        repo: str,
    ) -> float:
        """Calculate confidence score based on context relevance."""
        score = 0.3  # Base score

        context_lower = context.lower()
        repo_lower = repo.lower()

        # Check for artifact keywords in context
        keyword_matches = sum(
            1 for kw in self.config.artifact_keywords if kw in context_lower
        )
        score += min(keyword_matches * 0.15, 0.45)  # Max 0.45 from keywords

        # Check if repo name contains artifact keywords
        repo_keyword_matches = sum(
            1 for kw in self.config.artifact_keywords if kw in repo_lower
        )
        score += min(repo_keyword_matches * 0.1, 0.2)  # Max 0.2 from repo name

        # Known trusted organizations
        trusted_orgs = {"anthropics", "anthropic", "anthropic-ai"}
        if owner.lower() in trusted_orgs:
            score += 0.15

        return min(score, 1.0)

    def reset_visited(self) -> None:
        """Clear the visited set for a new discovery session."""
        self._visited.clear()

    def add_visited(self, urls: List[str]) -> None:
        """Add URLs to visited set (for pre-seeding known repos)."""
        for url in urls:
            normalized = self._normalize_url(url)
            if normalized:
                self._visited.add(normalized)


def harvest_readme_links(
    content: str,
    source_url: str,
    max_depth: int = 1,
) -> List[HarvestedLink]:
    """Convenience function to harvest links from README content.

    Args:
        content: README markdown content
        source_url: URL of the source repository
        max_depth: Maximum discovery depth

    Returns:
        List of discovered repository links

    Example:
        >>> readme = "Check out [anthropic skills](https://github.com/anthropics/skills)"
        >>> links = harvest_readme_links(readme, "https://github.com/user/repo")
        >>> print(links[0].repo)
        skills
    """
    config = HarvestConfig(max_depth=max_depth)
    harvester = ReadmeLinkHarvester(config)
    return harvester.harvest_links(content, source_url)


if __name__ == "__main__":
    # Test the harvester
    test_readme = """
    # My Project

    Check out these related projects:
    - [Anthropic Skills](https://github.com/anthropics/skills) - Official Claude skills
    - [My Skills](https://github.com/user/claude-skills) - Custom skills collection
    - [Some Library](https://github.com/other/library) - Unrelated project

    See also: github.com/test/artifacts for more artifacts.

    Issues: https://github.com/anthropics/skills/issues/123
    """

    links = harvest_readme_links(test_readme, "https://github.com/source/repo")

    print(f"Found {len(links)} links:")
    for link in links:
        print(f"  - {link.owner}/{link.repo}: {link.confidence:.2f}")
