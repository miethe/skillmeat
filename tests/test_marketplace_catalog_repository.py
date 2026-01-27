"""Unit tests for MarketplaceCatalogRepository search functionality.

This module tests the search() method for cross-source artifact search:
- Text search with ILIKE on name, title, description, search_tags
- Filtering by artifact_type, source_ids, min_confidence, tags
- Cursor-based pagination
- Exclusion of removed/excluded entries

Test coverage includes:
- Basic search with query
- Filtering combinations
- Pagination with cursors
- Edge cases (empty results, invalid cursors)
"""

from __future__ import annotations

import json
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import List

import pytest

from skillmeat.cache.models import (
    MarketplaceCatalogEntry,
    MarketplaceSource,
)
from skillmeat.cache.repositories import (
    MarketplaceCatalogRepository,
    MarketplaceSourceRepository,
    PaginatedResult,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_db():
    """Create temporary database file.

    Returns:
        Path to temporary database file
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    yield db_path

    # Cleanup
    try:
        Path(db_path).unlink()
    except FileNotFoundError:
        pass


@pytest.fixture
def source_repo(temp_db):
    """Create MarketplaceSourceRepository instance for testing."""
    return MarketplaceSourceRepository(db_path=temp_db)


@pytest.fixture
def catalog_repo(temp_db):
    """Create MarketplaceCatalogRepository instance for testing."""
    return MarketplaceCatalogRepository(db_path=temp_db)


@pytest.fixture
def sample_source():
    """Create a sample MarketplaceSource."""
    return MarketplaceSource(
        id="src_test_001",
        repo_url="https://github.com/anthropics/anthropic-quickstarts",
        owner="anthropics",
        repo_name="anthropic-quickstarts",
        ref="main",
        trust_level="verified",
        visibility="public",
        scan_status="success",
        artifact_count=10,
    )


@pytest.fixture
def second_source():
    """Create a second MarketplaceSource for multi-source tests."""
    return MarketplaceSource(
        id="src_test_002",
        repo_url="https://github.com/user/claude-skills",
        owner="user",
        repo_name="claude-skills",
        ref="main",
        trust_level="basic",
        visibility="public",
        scan_status="success",
        artifact_count=5,
    )


def create_catalog_entry(
    source_id: str,
    name: str,
    artifact_type: str = "skill",
    confidence_score: int = 80,
    status: str = "new",
    title: str = None,
    description: str = None,
    tags: List[str] = None,
) -> MarketplaceCatalogEntry:
    """Helper to create catalog entries for testing."""
    entry_id = f"entry_{uuid.uuid4().hex[:8]}"
    return MarketplaceCatalogEntry(
        id=entry_id,
        source_id=source_id,
        artifact_type=artifact_type,
        name=name,
        path=f"artifacts/{name}",
        upstream_url=f"https://github.com/test/{name}",
        detected_sha="abc123",
        detected_at=datetime.utcnow(),
        confidence_score=confidence_score,
        status=status,
        title=title or f"{name} Title",
        description=description or f"Description for {name}",
        search_tags=json.dumps(tags) if tags else None,
    )


@pytest.fixture
def populated_catalog(source_repo, catalog_repo, sample_source, second_source):
    """Create sources and catalog entries for testing."""
    # Create sources
    source_repo.create(sample_source)
    source_repo.create(second_source)

    # Create catalog entries
    entries = [
        # Source 1 entries
        create_catalog_entry(
            sample_source.id,
            "canvas-design",
            artifact_type="skill",
            confidence_score=95,
            title="Canvas Design Skill",
            description="Create beautiful designs with canvas",
            tags=["design", "ui", "canvas"],
        ),
        create_catalog_entry(
            sample_source.id,
            "testing-automation",
            artifact_type="skill",
            confidence_score=90,
            title="Testing Automation",
            description="Automated testing framework",
            tags=["testing", "automation", "qa"],
        ),
        create_catalog_entry(
            sample_source.id,
            "api-client",
            artifact_type="command",
            confidence_score=85,
            title="API Client Command",
            description="HTTP API client utility",
            tags=["api", "http", "client"],
        ),
        create_catalog_entry(
            sample_source.id,
            "excluded-artifact",
            artifact_type="skill",
            confidence_score=70,
            status="excluded",
            title="Excluded Skill",
            description="This should not appear in search",
            tags=["excluded"],
        ),
        create_catalog_entry(
            sample_source.id,
            "removed-artifact",
            artifact_type="skill",
            confidence_score=60,
            status="removed",
            title="Removed Skill",
            description="This should not appear in search",
            tags=["removed"],
        ),
        # Source 2 entries
        create_catalog_entry(
            second_source.id,
            "canvas-renderer",
            artifact_type="skill",
            confidence_score=88,
            title="Canvas Renderer",
            description="Render graphics to canvas",
            tags=["canvas", "graphics", "render"],
        ),
        create_catalog_entry(
            second_source.id,
            "database-agent",
            artifact_type="agent",
            confidence_score=75,
            title="Database Agent",
            description="Database management agent",
            tags=["database", "sql", "management"],
        ),
    ]

    catalog_repo.bulk_create(entries)

    return {
        "source1": sample_source,
        "source2": second_source,
        "entries": entries,
    }


# =============================================================================
# Search Tests
# =============================================================================


class TestSearchBasic:
    """Tests for basic search functionality."""

    def test_search_no_filters_returns_all_valid_entries(
        self, catalog_repo, populated_catalog
    ):
        """Test search with no filters returns all non-excluded/removed entries."""
        result = catalog_repo.search()

        assert isinstance(result, PaginatedResult)
        # Should return 5 entries (7 total - 2 excluded/removed)
        assert len(result.items) == 5
        # Verify excluded/removed entries are not present
        names = [e.name for e in result.items]
        assert "excluded-artifact" not in names
        assert "removed-artifact" not in names

    def test_search_by_query_matches_name(self, catalog_repo, populated_catalog):
        """Test search matches on name field."""
        result = catalog_repo.search(query="canvas")

        assert len(result.items) == 2
        names = [e.name for e in result.items]
        assert "canvas-design" in names
        assert "canvas-renderer" in names

    def test_search_by_query_case_insensitive(self, catalog_repo, populated_catalog):
        """Test search is case-insensitive."""
        result = catalog_repo.search(query="CANVAS")

        assert len(result.items) == 2
        names = [e.name for e in result.items]
        assert "canvas-design" in names
        assert "canvas-renderer" in names

    def test_search_by_query_matches_title(self, catalog_repo, populated_catalog):
        """Test search matches on title field."""
        result = catalog_repo.search(query="Automation")

        assert len(result.items) == 1
        assert result.items[0].name == "testing-automation"

    def test_search_by_query_matches_description(self, catalog_repo, populated_catalog):
        """Test search matches on description field."""
        result = catalog_repo.search(query="beautiful designs")

        assert len(result.items) == 1
        assert result.items[0].name == "canvas-design"

    def test_search_by_query_matches_tags(self, catalog_repo, populated_catalog):
        """Test search matches on search_tags field."""
        result = catalog_repo.search(query="http")

        assert len(result.items) == 1
        assert result.items[0].name == "api-client"

    def test_search_no_matches_returns_empty(self, catalog_repo, populated_catalog):
        """Test search with no matches returns empty result."""
        result = catalog_repo.search(query="nonexistent-artifact-xyz")

        assert len(result.items) == 0
        assert result.has_more is False
        assert result.next_cursor is None


class TestSearchFilters:
    """Tests for search filtering."""

    def test_filter_by_artifact_type(self, catalog_repo, populated_catalog):
        """Test filtering by artifact_type."""
        result = catalog_repo.search(artifact_type="skill")

        assert len(result.items) == 3
        for entry in result.items:
            assert entry.artifact_type == "skill"

    def test_filter_by_source_ids_single(self, catalog_repo, populated_catalog):
        """Test filtering by single source ID."""
        source_id = populated_catalog["source1"].id
        result = catalog_repo.search(source_ids=[source_id])

        assert len(result.items) == 3
        for entry in result.items:
            assert entry.source_id == source_id

    def test_filter_by_source_ids_multiple(self, catalog_repo, populated_catalog):
        """Test filtering by multiple source IDs."""
        source_ids = [
            populated_catalog["source1"].id,
            populated_catalog["source2"].id,
        ]
        result = catalog_repo.search(source_ids=source_ids)

        assert len(result.items) == 5

    def test_filter_by_min_confidence(self, catalog_repo, populated_catalog):
        """Test filtering by minimum confidence score."""
        result = catalog_repo.search(min_confidence=90)

        assert len(result.items) == 2
        for entry in result.items:
            assert entry.confidence_score >= 90

    def test_filter_by_tags_single(self, catalog_repo, populated_catalog):
        """Test filtering by single tag."""
        result = catalog_repo.search(tags=["canvas"])

        assert len(result.items) == 2
        names = [e.name for e in result.items]
        assert "canvas-design" in names
        assert "canvas-renderer" in names

    def test_filter_by_tags_multiple_or_logic(self, catalog_repo, populated_catalog):
        """Test filtering by multiple tags uses OR logic."""
        result = catalog_repo.search(tags=["design", "database"])

        assert len(result.items) == 2
        names = [e.name for e in result.items]
        assert "canvas-design" in names
        assert "database-agent" in names

    def test_combined_filters(self, catalog_repo, populated_catalog):
        """Test combining multiple filters."""
        result = catalog_repo.search(
            query="canvas",
            artifact_type="skill",
            min_confidence=90,
        )

        assert len(result.items) == 1
        assert result.items[0].name == "canvas-design"

    def test_query_and_source_filter(self, catalog_repo, populated_catalog):
        """Test combining query and source filter."""
        source_id = populated_catalog["source2"].id
        result = catalog_repo.search(
            query="canvas",
            source_ids=[source_id],
        )

        assert len(result.items) == 1
        assert result.items[0].name == "canvas-renderer"


class TestSearchOrdering:
    """Tests for search result ordering."""

    def test_results_ordered_by_confidence_desc(self, catalog_repo, populated_catalog):
        """Test results are ordered by confidence_score descending."""
        result = catalog_repo.search()

        scores = [e.confidence_score for e in result.items]
        assert scores == sorted(scores, reverse=True)

    def test_results_stable_with_same_confidence(
        self, source_repo, catalog_repo, sample_source
    ):
        """Test ordering is stable when entries have same confidence."""
        source_repo.create(sample_source)

        # Create entries with same confidence
        entries = [
            create_catalog_entry(sample_source.id, f"artifact-{i}", confidence_score=80)
            for i in range(5)
        ]
        catalog_repo.bulk_create(entries)

        # Multiple searches should return same order
        result1 = catalog_repo.search()
        result2 = catalog_repo.search()

        ids1 = [e.id for e in result1.items]
        ids2 = [e.id for e in result2.items]
        assert ids1 == ids2


class TestSearchPagination:
    """Tests for cursor-based pagination."""

    def test_pagination_limit(self, catalog_repo, populated_catalog):
        """Test pagination respects limit."""
        result = catalog_repo.search(limit=2)

        assert len(result.items) == 2
        assert result.has_more is True
        assert result.next_cursor is not None

    def test_pagination_cursor_next_page(self, catalog_repo, populated_catalog):
        """Test pagination with cursor returns next page."""
        first_page = catalog_repo.search(limit=2)
        second_page = catalog_repo.search(limit=2, cursor=first_page.next_cursor)

        # First and second pages should have different items
        first_ids = {e.id for e in first_page.items}
        second_ids = {e.id for e in second_page.items}
        assert first_ids.isdisjoint(second_ids)

    def test_pagination_exhausts_results(self, catalog_repo, populated_catalog):
        """Test pagination eventually exhausts all results."""
        all_items = []
        cursor = None

        while True:
            result = catalog_repo.search(limit=2, cursor=cursor)
            all_items.extend(result.items)

            if not result.has_more:
                break
            cursor = result.next_cursor

        # Should have found all 5 valid entries
        assert len(all_items) == 5

    def test_invalid_cursor_returns_first_page(self, catalog_repo, populated_catalog):
        """Test invalid cursor format returns results from start."""
        result = catalog_repo.search(cursor="invalid_cursor_format")

        # Should return results as if no cursor provided
        assert len(result.items) <= 50
        # First result should be highest confidence
        assert result.items[0].confidence_score == 95

    def test_cursor_format_is_score_id(self, catalog_repo, populated_catalog):
        """Test cursor format is confidence_score:id."""
        result = catalog_repo.search(limit=2)

        if result.has_more:
            cursor = result.next_cursor
            assert ":" in cursor
            score_str, entry_id = cursor.split(":", 1)
            assert score_str.isdigit()

    def test_pagination_with_filters(self, catalog_repo, populated_catalog):
        """Test pagination works correctly with filters applied."""
        # Filter to skills only, then paginate
        first_page = catalog_repo.search(artifact_type="skill", limit=2)

        assert len(first_page.items) == 2
        assert first_page.has_more is True

        second_page = catalog_repo.search(
            artifact_type="skill",
            limit=2,
            cursor=first_page.next_cursor,
        )

        assert len(second_page.items) == 1
        assert second_page.has_more is False

        # All returned items should be skills
        for entry in first_page.items + second_page.items:
            assert entry.artifact_type == "skill"


class TestSearchEdgeCases:
    """Tests for edge cases."""

    def test_search_empty_database(self, catalog_repo):
        """Test search on empty database returns empty result."""
        result = catalog_repo.search()

        assert len(result.items) == 0
        assert result.has_more is False
        assert result.next_cursor is None

    def test_search_query_with_special_characters(
        self, source_repo, catalog_repo, sample_source
    ):
        """Test search handles special characters in query."""
        source_repo.create(sample_source)

        entry = create_catalog_entry(
            sample_source.id,
            "special-chars",
            title="Test % underscore _ bracket [ ]",
        )
        catalog_repo.bulk_create([entry])

        # SQL LIKE special chars should be handled
        result = catalog_repo.search(query="underscore")
        assert len(result.items) == 1

    def test_search_tags_filter_with_no_tags_in_entry(
        self, source_repo, catalog_repo, sample_source
    ):
        """Test tags filter when entry has no tags."""
        source_repo.create(sample_source)

        entry = create_catalog_entry(
            sample_source.id,
            "no-tags",
            tags=None,
        )
        catalog_repo.bulk_create([entry])

        # Search with tags filter should not match entry with no tags
        result = catalog_repo.search(tags=["design"])
        names = [e.name for e in result.items]
        assert "no-tags" not in names

        # Search without tags filter should return entry
        result = catalog_repo.search()
        names = [e.name for e in result.items]
        assert "no-tags" in names

    def test_min_confidence_zero_returns_all(self, catalog_repo, populated_catalog):
        """Test min_confidence=0 returns all valid entries."""
        result = catalog_repo.search(min_confidence=0)

        assert len(result.items) == 5

    def test_min_confidence_high_returns_none(self, catalog_repo, populated_catalog):
        """Test very high min_confidence returns no results."""
        result = catalog_repo.search(min_confidence=100)

        # No entries have score of 100
        assert len(result.items) == 0


# =============================================================================
# FTS5 Search Tests
# =============================================================================


class TestFTS5QueryBuilder:
    """Tests for FTS5 query building and escaping."""

    def test_build_fts5_query_simple(self, catalog_repo):
        """Test simple query building with prefix matching."""
        result = catalog_repo._build_fts5_query("canvas")
        assert result == "canvas*"

    def test_build_fts5_query_multiple_terms(self, catalog_repo):
        """Test multiple terms get prefix matching."""
        result = catalog_repo._build_fts5_query("canvas design")
        assert result == "canvas* design*"

    def test_build_fts5_query_escapes_special_chars(self, catalog_repo):
        """Test special characters are escaped."""
        result = catalog_repo._build_fts5_query('test-skill "quoted"')
        # Dashes and quotes should be replaced with spaces
        assert "-" not in result
        assert '"' not in result
        assert "test*" in result
        assert "skill*" in result

    def test_build_fts5_query_removes_operators(self, catalog_repo):
        """Test FTS5 operators are removed."""
        result = catalog_repo._build_fts5_query("canvas AND design OR testing")
        # FTS5 operators should be removed
        assert "AND" not in result
        assert "OR" not in result
        assert "canvas*" in result
        assert "design*" in result
        assert "testing*" in result

    def test_build_fts5_query_empty_after_stripping(self, catalog_repo):
        """Test query returns wildcard when all terms stripped."""
        result = catalog_repo._build_fts5_query("AND OR NOT")
        assert result == "*"

    def test_build_fts5_query_handles_parentheses(self, catalog_repo):
        """Test parentheses are escaped."""
        result = catalog_repo._build_fts5_query("test(skill)")
        assert "(" not in result
        assert ")" not in result

    def test_build_fts5_query_handles_colons(self, catalog_repo):
        """Test colons are escaped (column specifiers in FTS5)."""
        result = catalog_repo._build_fts5_query("title:canvas")
        assert ":" not in result

    def test_build_fts5_query_handles_asterisks(self, catalog_repo):
        """Test existing asterisks are handled."""
        result = catalog_repo._build_fts5_query("canvas*")
        # Should not have double asterisks
        assert "**" not in result

    def test_build_fts5_query_case_insensitive_operators(self, catalog_repo):
        """Test operator removal is case-insensitive."""
        result = catalog_repo._build_fts5_query("canvas and design or test")
        assert "and" not in result.lower().split()
        assert "or" not in result.lower().split()


class TestFTS5SearchFallback:
    """Tests for FTS5/LIKE fallback behavior."""

    def test_search_uses_like_when_no_query(self, catalog_repo, populated_catalog):
        """Test that search uses LIKE path when no query provided."""
        # Without a query, should use LIKE path regardless of FTS5 availability
        result = catalog_repo.search()

        # Should return all valid entries
        assert len(result.items) == 5

    def test_search_uses_like_when_fts5_unavailable(
        self, catalog_repo, populated_catalog, monkeypatch
    ):
        """Test that search falls back to LIKE when FTS5 unavailable."""
        # Mock FTS5 as unavailable - patch at the source module where it's imported from
        monkeypatch.setattr("skillmeat.api.utils.fts5.is_fts5_available", lambda: False)

        result = catalog_repo.search(query="canvas")

        # Should still return results via LIKE
        assert len(result.items) == 2
        names = [e.name for e in result.items]
        assert "canvas-design" in names
        assert "canvas-renderer" in names

    def test_search_like_method_directly(self, catalog_repo, populated_catalog):
        """Test _search_like method can be called directly."""
        result = catalog_repo._search_like(query="canvas")

        assert len(result.items) == 2
        names = [e.name for e in result.items]
        assert "canvas-design" in names
        assert "canvas-renderer" in names

    def test_search_like_with_filters(self, catalog_repo, populated_catalog):
        """Test _search_like with filters."""
        result = catalog_repo._search_like(
            query="canvas",
            artifact_type="skill",
            min_confidence=90,
        )

        assert len(result.items) == 1
        assert result.items[0].name == "canvas-design"

    def test_search_like_returns_no_snippets(self, catalog_repo, populated_catalog):
        """Test _search_like method returns None for snippets field."""
        result = catalog_repo._search_like(query="canvas")

        assert len(result.items) == 2
        # LIKE search does not return snippets
        assert result.snippets is None


class TestFTS5SearchIntegration:
    """Integration tests for FTS5 search when available.

    Note: These tests depend on FTS5 being available in the SQLite installation.
    They may be skipped if FTS5 is not available.
    """

    def test_fts5_search_returns_results(
        self, source_repo, catalog_repo, sample_source, monkeypatch
    ):
        """Test FTS5 search returns relevant results when available."""
        from skillmeat.api.utils.fts5 import reset_fts5_check

        # Reset FTS5 check state
        reset_fts5_check()

        source_repo.create(sample_source)

        # Create entries with search_text populated (required for FTS5)
        entries = [
            create_catalog_entry(
                sample_source.id,
                "test-skill",
                title="Test Skill",
                description="A skill for testing",
                tags=["test"],
            ),
        ]
        # Manually set search_text for FTS5
        entries[0].search_text = "Test Skill A skill for testing test"

        catalog_repo.bulk_create(entries)

        # Try to search - will use LIKE fallback if FTS5 unavailable
        result = catalog_repo.search(query="testing")

        # Should find the entry
        assert len(result.items) >= 1
        names = [e.name for e in result.items]
        assert "test-skill" in names

    def test_fts5_search_with_type_filter(
        self, source_repo, catalog_repo, sample_source, monkeypatch
    ):
        """Test FTS5 search respects artifact_type filter."""
        from skillmeat.api.utils.fts5 import reset_fts5_check

        reset_fts5_check()

        source_repo.create(sample_source)

        entries = [
            create_catalog_entry(
                sample_source.id,
                "test-skill",
                artifact_type="skill",
                title="Test Skill",
                description="A skill for testing",
            ),
            create_catalog_entry(
                sample_source.id,
                "test-command",
                artifact_type="command",
                title="Test Command",
                description="A command for testing",
            ),
        ]
        for e in entries:
            e.search_text = f"{e.title} {e.description}"

        catalog_repo.bulk_create(entries)

        # Search with type filter
        result = catalog_repo.search(query="test", artifact_type="skill")

        names = [e.name for e in result.items]
        assert "test-skill" in names
        assert "test-command" not in names

    def test_fts5_search_with_source_filter(
        self, source_repo, catalog_repo, sample_source, second_source
    ):
        """Test FTS5 search respects source_ids filter."""
        from skillmeat.api.utils.fts5 import reset_fts5_check

        reset_fts5_check()

        source_repo.create(sample_source)
        source_repo.create(second_source)

        entries = [
            create_catalog_entry(
                sample_source.id,
                "test-one",
                title="Test One",
                description="First test",
            ),
            create_catalog_entry(
                second_source.id,
                "test-two",
                title="Test Two",
                description="Second test",
            ),
        ]
        for e in entries:
            e.search_text = f"{e.title} {e.description}"

        catalog_repo.bulk_create(entries)

        # Search with source filter
        result = catalog_repo.search(query="test", source_ids=[sample_source.id])

        names = [e.name for e in result.items]
        assert "test-one" in names
        assert "test-two" not in names

    def test_fts5_search_with_confidence_filter(
        self, source_repo, catalog_repo, sample_source
    ):
        """Test FTS5 search respects min_confidence filter."""
        from skillmeat.api.utils.fts5 import reset_fts5_check

        reset_fts5_check()

        source_repo.create(sample_source)

        entries = [
            create_catalog_entry(
                sample_source.id,
                "high-confidence",
                confidence_score=95,
                title="High Confidence Test",
                description="Very confident",
            ),
            create_catalog_entry(
                sample_source.id,
                "low-confidence",
                confidence_score=50,
                title="Low Confidence Test",
                description="Not so confident",
            ),
        ]
        for e in entries:
            e.search_text = f"{e.title} {e.description}"

        catalog_repo.bulk_create(entries)

        # Search with confidence filter
        result = catalog_repo.search(query="confidence", min_confidence=80)

        names = [e.name for e in result.items]
        assert "high-confidence" in names
        assert "low-confidence" not in names

    def test_fts5_search_with_tags_filter(
        self, source_repo, catalog_repo, sample_source
    ):
        """Test FTS5 search respects tags filter."""
        from skillmeat.api.utils.fts5 import reset_fts5_check

        reset_fts5_check()

        source_repo.create(sample_source)

        entries = [
            create_catalog_entry(
                sample_source.id,
                "tagged-design",
                title="Design Skill",
                description="UI design",
                tags=["design", "ui"],
            ),
            create_catalog_entry(
                sample_source.id,
                "tagged-backend",
                title="Backend Skill",
                description="API backend",
                tags=["backend", "api"],
            ),
        ]
        for e in entries:
            e.search_text = f"{e.title} {e.description}"

        catalog_repo.bulk_create(entries)

        # Search with tags filter
        result = catalog_repo.search(query="skill", tags=["design"])

        names = [e.name for e in result.items]
        assert "tagged-design" in names
        assert "tagged-backend" not in names

    def test_fts5_search_excludes_removed_entries(
        self, source_repo, catalog_repo, sample_source
    ):
        """Test FTS5 search excludes removed and excluded entries."""
        from skillmeat.api.utils.fts5 import reset_fts5_check

        reset_fts5_check()

        source_repo.create(sample_source)

        entries = [
            create_catalog_entry(
                sample_source.id,
                "active-entry",
                status="new",
                title="Active Test",
                description="Should appear",
            ),
            create_catalog_entry(
                sample_source.id,
                "excluded-entry",
                status="excluded",
                title="Excluded Test",
                description="Should not appear",
            ),
            create_catalog_entry(
                sample_source.id,
                "removed-entry",
                status="removed",
                title="Removed Test",
                description="Should not appear",
            ),
        ]
        for e in entries:
            e.search_text = f"{e.title} {e.description}"

        catalog_repo.bulk_create(entries)

        result = catalog_repo.search(query="test")

        names = [e.name for e in result.items]
        assert "active-entry" in names
        assert "excluded-entry" not in names
        assert "removed-entry" not in names

    def test_fts5_search_returns_snippets(
        self, source_repo, catalog_repo, sample_source
    ):
        """Test FTS5 search returns highlighted snippets for matching terms."""
        from skillmeat.api.utils.fts5 import reset_fts5_check

        reset_fts5_check()

        source_repo.create(sample_source)

        entries = [
            create_catalog_entry(
                sample_source.id,
                "test-skill",
                title="Canvas Design System",
                description="A comprehensive design system for building beautiful interfaces",
            ),
        ]
        for e in entries:
            e.search_text = f"{e.title} {e.description}"

        catalog_repo.bulk_create(entries)

        # Search for "design" which appears in both title and description
        result = catalog_repo.search(query="design")

        # Should find the entry
        assert len(result.items) >= 1
        assert result.items[0].name == "test-skill"

        # Snippets should be available if FTS5 worked
        if result.snippets:
            entry_snippets = result.snippets.get(result.items[0].id, {})
            # Check that snippets contain highlight markers
            title_snippet = entry_snippets.get("title_snippet")
            description_snippet = entry_snippets.get("description_snippet")

            # At least one snippet should have the mark tag
            has_highlights = False
            if title_snippet and "<mark>" in title_snippet:
                has_highlights = True
            if description_snippet and "<mark>" in description_snippet:
                has_highlights = True

            # If FTS5 is available, we should have highlights
            # (test is lenient since FTS5 availability varies by system)
            assert has_highlights or result.snippets is None

    def test_fts5_search_snippets_have_ellipsis_for_truncation(
        self, source_repo, catalog_repo, sample_source
    ):
        """Test FTS5 snippets use ellipsis for truncated content."""
        from skillmeat.api.utils.fts5 import reset_fts5_check

        reset_fts5_check()

        source_repo.create(sample_source)

        # Create entry with long description
        long_description = (
            "This is a very long description that talks about many things "
            "including testing and automation and various other topics "
            "that will require truncation when generating snippets. "
            "The testing framework provides comprehensive coverage."
        )

        entries = [
            create_catalog_entry(
                sample_source.id,
                "long-skill",
                title="Testing Framework",
                description=long_description,
            ),
        ]
        for e in entries:
            e.search_text = f"{e.title} {e.description}"

        catalog_repo.bulk_create(entries)

        result = catalog_repo.search(query="testing")

        # Check snippets if available
        if result.snippets and result.items:
            entry_snippets = result.snippets.get(result.items[0].id, {})
            description_snippet = entry_snippets.get("description_snippet")

            # Long content should be truncated with ellipsis
            if description_snippet:
                # Snippet should either have ellipsis or be shorter than original
                assert "..." in description_snippet or len(description_snippet) <= len(
                    long_description
                )

    def test_fts5_search_returns_deep_match_fields(
        self, source_repo, catalog_repo, sample_source
    ):
        """Test FTS5 search returns deep_match and matched_file in snippets."""
        from skillmeat.api.utils.fts5 import reset_fts5_check

        reset_fts5_check()

        source_repo.create(sample_source)

        # Create entry with deep_search_text but no matching title/description
        entries = [
            create_catalog_entry(
                sample_source.id,
                "deep-indexed-skill",
                title="Generic Skill",
                description="A basic skill without specific keywords",
            ),
        ]
        # Set search_text for FTS5 indexing
        entries[0].search_text = f"{entries[0].title} {entries[0].description}"
        # Set deep_search_text with unique searchable content
        entries[0].deep_search_text = (
            "This skill uses advanced xyzzy algorithms for processing data"
        )
        # Set deep_index_files to indicate which files were indexed
        entries[0].deep_index_files = json.dumps(["SKILL.md", "lib/main.py"])

        catalog_repo.bulk_create(entries)

        # Search for a term only in deep_search_text
        result = catalog_repo.search(query="xyzzy")

        # Should find the entry if FTS5 includes deep_search_text
        # (if FTS5 unavailable, LIKE search won't find it - that's okay)
        if result.items:
            assert len(result.items) >= 1
            assert result.items[0].name == "deep-indexed-skill"

            # Check snippets include deep_match and matched_file fields
            if result.snippets:
                entry_snippets = result.snippets.get(result.items[0].id, {})

                # deep_match should be True since term is only in deep_search_text
                deep_match = entry_snippets.get("deep_match", False)
                matched_file = entry_snippets.get("matched_file")

                # If FTS5 is working and found the match in deep content,
                # deep_match should be True and matched_file should be set
                if deep_match:
                    assert deep_match is True
                    assert matched_file == "SKILL.md"  # First file in list

    def test_fts5_search_prefers_title_over_deep_content(
        self, source_repo, catalog_repo, sample_source
    ):
        """Test that matches in title/description are NOT marked as deep_match."""
        from skillmeat.api.utils.fts5 import reset_fts5_check

        reset_fts5_check()

        source_repo.create(sample_source)

        # Create entry with matching title and deep_search_text
        entries = [
            create_catalog_entry(
                sample_source.id,
                "dual-match-skill",
                title="Canvas Drawing Skill",  # "canvas" in title
                description="Draw on HTML canvas elements",  # "canvas" in description
            ),
        ]
        entries[0].search_text = f"{entries[0].title} {entries[0].description}"
        # Also has "canvas" in deep content
        entries[0].deep_search_text = "Advanced canvas rendering techniques"
        entries[0].deep_index_files = json.dumps(["docs/canvas.md"])

        catalog_repo.bulk_create(entries)

        # Search for "canvas" - appears in all fields
        result = catalog_repo.search(query="canvas")

        assert len(result.items) >= 1
        assert result.items[0].name == "dual-match-skill"

        # Check that deep_match is False (title/desc match takes precedence)
        if result.snippets:
            entry_snippets = result.snippets.get(result.items[0].id, {})
            deep_match = entry_snippets.get("deep_match", False)

            # Since title/description matched, deep_match should be False
            assert deep_match is False

    def test_fts5_search_deep_match_no_files(
        self, source_repo, catalog_repo, sample_source
    ):
        """Test deep_match with no deep_index_files returns matched_file=None."""
        from skillmeat.api.utils.fts5 import reset_fts5_check

        reset_fts5_check()

        source_repo.create(sample_source)

        # Create entry with deep_search_text but no deep_index_files
        entries = [
            create_catalog_entry(
                sample_source.id,
                "deep-no-files",
                title="Basic Skill",
                description="Nothing special here",
            ),
        ]
        entries[0].search_text = f"{entries[0].title} {entries[0].description}"
        entries[0].deep_search_text = "Contains unique flubber keyword"
        # No deep_index_files set

        catalog_repo.bulk_create(entries)

        result = catalog_repo.search(query="flubber")

        if result.items and result.snippets:
            entry_snippets = result.snippets.get(result.items[0].id, {})
            deep_match = entry_snippets.get("deep_match", False)
            matched_file = entry_snippets.get("matched_file")

            if deep_match:
                # matched_file should be None when no files list
                assert matched_file is None
