"""Marketplace catalog API router for cross-source artifact search.

This router provides endpoints for searching across all marketplace catalog entries
regardless of their source. It enables unified artifact discovery across multiple
GitHub repository sources.

API Endpoints:
    GET /marketplace/catalog/search - Search artifacts across all sources
"""

import json
import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from skillmeat.api.schemas.marketplace import (
    CatalogSearchResponse,
    CatalogSearchResult,
)
from skillmeat.cache.models import MarketplaceCatalogEntry, get_session
from skillmeat.cache.repositories import MarketplaceCatalogRepository

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/marketplace/catalog",
    tags=["marketplace-catalog"],
)


def get_db_session():
    """Dependency that provides a database session.

    Yields:
        Session: SQLAlchemy database session
    """
    session = get_session()
    try:
        yield session
    finally:
        session.close()


DbSessionDep = Annotated[Session, Depends(get_db_session)]


def entry_to_search_result(
    entry: MarketplaceCatalogEntry,
    title_snippet: Optional[str] = None,
    description_snippet: Optional[str] = None,
    deep_match: bool = False,
    matched_file: Optional[str] = None,
) -> CatalogSearchResult:
    """Convert MarketplaceCatalogEntry ORM model to CatalogSearchResult DTO.

    Includes source context (owner, repo) from the related MarketplaceSource.

    Args:
        entry: MarketplaceCatalogEntry ORM instance with source relationship loaded
        title_snippet: Optional highlighted title snippet from FTS5 search
        description_snippet: Optional highlighted description snippet from FTS5 search
        deep_match: True if match came from deep-indexed content (not title/description)
        matched_file: Relative file path where match was found (for deep matches)

    Returns:
        CatalogSearchResult DTO for API response
    """
    # Parse search_tags from JSON string if present
    search_tags_list: Optional[List[str]] = None
    if entry.search_tags:
        try:
            search_tags_list = json.loads(entry.search_tags)
        except json.JSONDecodeError:
            search_tags_list = None

    # Get source info - source relationship should be loaded
    source_owner = ""
    source_repo = ""
    if entry.source:
        source_owner = entry.source.owner or ""
        source_repo = entry.source.repo_name or ""

    return CatalogSearchResult(
        id=entry.id,
        name=entry.name,
        artifact_type=entry.artifact_type,
        title=entry.title,
        description=entry.description,
        confidence_score=entry.confidence_score,
        source_owner=source_owner,
        source_repo=source_repo,
        source_id=entry.source_id,
        path=entry.path,
        upstream_url=entry.upstream_url,
        status=entry.status,
        search_tags=search_tags_list,
        title_snippet=title_snippet,
        description_snippet=description_snippet,
        deep_match=deep_match,
        matched_file=matched_file,
    )


@router.get(
    "/search",
    response_model=CatalogSearchResponse,
    summary="Search artifacts across all marketplace sources",
    description="""
Search for artifacts across all configured marketplace sources using text matching
and various filters. Results are ordered by confidence score descending.

**Text Search**: The `q` parameter performs full-text search (FTS5) against:
- Artifact name
- Title (from frontmatter)
- Description (from frontmatter)
- Search tags (from frontmatter)
- Deep-indexed content (full artifact file text, when available)

Matches in title/description rank higher than deep-indexed content matches.
Results include `deep_match=true` and `matched_file` when a match came from
deep-indexed content rather than the artifact metadata.

**Filtering Options**:
- `type`: Filter by artifact type (skill, command, agent, etc.)
- `source_id`: Limit search to a specific source
- `min_confidence`: Only return entries with confidence >= this value
- `tags`: Comma-separated list of tags to filter by (OR logic)

**Pagination**: Uses cursor-based pagination for efficient traversal of large result sets.
The `cursor` value from a previous response can be used to fetch the next page.
    """,
    responses={
        200: {"description": "Successfully retrieved search results"},
        500: {"description": "Database operation failed"},
    },
)
async def search_catalog(
    q: Optional[str] = Query(
        None,
        description="Search query for full-text matching on name, title, description, tags, and deep-indexed content",
        examples=["canvas", "testing", "api"],
    ),
    type: Optional[str] = Query(
        None,
        alias="type",
        description="Filter by artifact type",
        examples=["skill", "command", "agent"],
    ),
    source_id: Optional[str] = Query(
        None,
        description="Limit search to a specific source ID",
        examples=["src_anthropics_quickstarts"],
    ),
    min_confidence: int = Query(
        0,
        ge=0,
        le=100,
        description="Minimum confidence score (0-100)",
    ),
    tags: Optional[str] = Query(
        None,
        description="Comma-separated list of tags to filter by (OR logic)",
        examples=["design,ui", "testing,automation"],
    ),
    limit: int = Query(
        50,
        ge=1,
        le=200,
        description="Maximum number of results per page",
    ),
    cursor: Optional[str] = Query(
        None,
        description="Pagination cursor from previous response",
        examples=["95:cat_abc123"],
    ),
) -> CatalogSearchResponse:
    """Search artifacts across all marketplace sources.

    Performs cross-source search using ILIKE queries on name, title, description,
    and search_tags fields. Supports filtering by type, source, confidence, and tags.

    Results are ordered by confidence_score descending to surface highest-quality
    matches first. Entries with status 'excluded' or 'removed' are automatically
    excluded from results.

    Args:
        q: Optional search query for text matching
        type: Optional artifact type filter
        source_id: Optional source ID to limit search scope
        min_confidence: Minimum confidence score (default: 0)
        tags: Optional comma-separated tag list for filtering
        limit: Maximum results per page (1-200, default: 50)
        cursor: Pagination cursor from previous response

    Returns:
        CatalogSearchResponse with items, next_cursor, and has_more flag

    Raises:
        HTTPException 500: If database operation fails
    """
    catalog_repo = MarketplaceCatalogRepository()

    try:
        # Parse tags if provided
        tag_list: Optional[List[str]] = None
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]

        # Build source_ids list if source_id provided
        source_ids: Optional[List[str]] = None
        if source_id:
            source_ids = [source_id]

        # Execute search with eager loading of source relationship
        result = catalog_repo.search(
            query=q,
            artifact_type=type,
            source_ids=source_ids,
            min_confidence=min_confidence,
            tags=tag_list,
            limit=limit,
            cursor=cursor,
        )

        # Convert entries to DTOs, including snippets if available (FTS5 search)
        items = []
        for entry in result.items:
            # Get snippets for this entry if available (FTS5 search returns snippets)
            # Snippets dict includes: title_snippet, description_snippet, deep_match, matched_file
            snippets = result.snippets.get(entry.id, {}) if result.snippets else {}
            items.append(
                entry_to_search_result(
                    entry,
                    title_snippet=snippets.get("title_snippet"),
                    description_snippet=snippets.get("description_snippet"),
                    deep_match=snippets.get("deep_match", False),
                    matched_file=snippets.get("matched_file"),
                )
            )

        logger.debug(
            f"Catalog search returned {len(items)} results "
            f"(query={q}, type={type}, source_id={source_id}, "
            f"min_confidence={min_confidence}, tags={tags}, "
            f"has_more={result.has_more})"
        )

        return CatalogSearchResponse(
            items=items,
            next_cursor=result.next_cursor,
            has_more=result.has_more,
        )

    except Exception as e:
        logger.exception(f"Catalog search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search operation failed: {str(e)}",
        )
