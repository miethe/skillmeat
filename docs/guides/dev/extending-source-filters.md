---
title: "Extending Source Filters and Metadata"
description: "Developer guide for extending marketplace source filtering capabilities and adding new source metadata fields"
audience: "developers"
tags: ["marketplace", "sources", "filters", "metadata", "extension", "guide"]
created: 2026-01-18
updated: 2026-01-18
category: "developer-guides"
status: "published"
related_documents:
  - "docs/project_plans/PRDs/enhancements/marketplace-sources-enhancement-v1.md"
  - "docs/dev/architecture/decisions/ADR-marketplace-filtering.md"
  - "skillmeat/api/routers/marketplace_sources.py"
  - "skillmeat/api/schemas/marketplace.py"
---

# Extending Source Filters and Metadata

Guide for developers extending marketplace source filtering capabilities and adding new source metadata fields to the SkillMeat platform.

## Table of Contents

- [Overview](#overview)
- [Adding a New Filter Type](#adding-a-new-filter-type)
- [Adding New Source Metadata Fields](#adding-new-source-metadata-fields)
- [Extending Tag Functionality](#extending-tag-functionality)
- [Backward Compatibility](#backward-compatibility-considerations)
- [Testing New Filters and Metadata](#testing-new-filters-and-metadata)
- [Performance Considerations](#performance-considerations)
- [Common Patterns](#common-patterns)

## Overview

The marketplace sources enhancement provides a extensible filtering and metadata system. This guide explains how to:

1. Add new filter types to the sources list (e.g., new status types, metadata fields)
2. Add new source metadata fields (e.g., owner, license, last updated)
3. Extend tag functionality (e.g., tag categories, tag hierarchies)
4. Maintain backward compatibility while extending the system
5. Test new filters and fields properly

### Architecture Overview

The filtering system follows SkillMeat's layered architecture:

```
Router Layer (HTTP)
    ↓ (parse query parameters, validate filters)
Service Layer (Business Logic)
    ↓ (compose filter criteria, apply AND/OR logic)
Repository Layer (Database I/O)
    ↓ (execute filtered queries, paginate results)
DTO Layer (Response Serialization)
    ↓ (return filtered SourceResponse objects)
Frontend Layer (UI)
    ↓ (render filter UI, apply URL state)
```

**Key Files:**

- `skillmeat/api/routers/marketplace_sources.py` - HTTP endpoints and query parameter parsing
- `skillmeat/api/schemas/marketplace.py` - Request/response DTOs and validation
- `skillmeat/api/managers/marketplace_source_manager.py` - Business logic for filtering
- `skillmeat/database/repositories/marketplace_source_repository.py` - Database queries
- `skillmeat/web/components/marketplace/source-filter-bar.tsx` - Filter UI component
- `skillmeat/web/types/marketplace.ts` - Frontend TypeScript types

## Adding a New Filter Type

### Example: Adding an "Owner" Filter

**Step 1: Update the Database Schema**

Add the field to the `marketplace_sources` table if it doesn't already exist:

```python
# skillmeat/database/models/marketplace.py
class MarketplaceSource(Base):
    __tablename__ = "marketplace_sources"

    id: Mapped[str] = mapped_column(primary_key=True)
    # ... existing fields ...
    owner: Mapped[str] = mapped_column(String(255), nullable=False)  # GitHub username

    __table_args__ = (
        Index("idx_marketplace_sources_owner", "owner"),  # Index for fast filtering
    )
```

**Step 2: Create Alembic Migration**

```bash
alembic revision --autogenerate -m "Add owner filter to marketplace_sources"
```

Verify the migration creates the proper index and column with sensible defaults.

**Step 3: Update API Schemas**

```python
# skillmeat/api/schemas/marketplace.py
from pydantic import Field

class SourceResponse(BaseModel):
    """Enhanced source response with new fields."""
    id: str
    repo_url: str
    owner: str = Field(..., description="GitHub repository owner username")
    repo_name: str
    # ... other fields ...

    class Config:
        from_attributes = True

class SourceListQuery(BaseModel):
    """Query parameters for listing sources."""
    artifact_type: Optional[str] = Field(
        None,
        description="Filter by artifact type: skill, command, agent, mcp, hook"
    )
    tags: Optional[str] = Field(
        None,
        description="Comma-separated tags (AND logic)"
    )
    owner: Optional[str] = Field(
        None,
        description="Filter by repository owner username"
    )
    trust_level: Optional[str] = Field(
        None,
        description="Filter by trust level: basic, verified, official"
    )
    search: Optional[str] = Field(
        None,
        description="Full-text search on name and description"
    )
```

**Step 4: Update Repository Query Logic**

```python
# skillmeat/database/repositories/marketplace_source_repository.py
from sqlalchemy import and_, or_, func

async def list_sources_with_filters(
    self,
    artifact_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
    owner: Optional[str] = None,
    trust_level: Optional[str] = None,
    search: Optional[str] = None,
    cursor: Optional[str] = None,
    limit: int = 20,
) -> PaginatedResponse[SourceResponse]:
    """
    List marketplace sources with advanced filtering.

    Filter Logic:
    - artifact_type: Match any specified types (OR)
    - tags: Must match all tags (AND)
    - owner: Exact username match
    - trust_level: Filter by trust level
    - search: Full-text search on name/description

    Args:
        artifact_type: Single or comma-separated artifact types
        tags: Comma-separated tags (AND logic)
        owner: GitHub owner username
        trust_level: Trust level filter
        search: Search query string
        cursor: Pagination cursor
        limit: Results per page (max 100)

    Returns:
        PaginatedResponse with filtered sources and pageInfo
    """
    query = select(MarketplaceSource)
    filters = []

    # Owner filter (new)
    if owner:
        filters.append(MarketplaceSource.owner == owner)

    # Artifact type filter
    if artifact_type:
        types = [t.strip() for t in artifact_type.split(",")]
        # Join with catalog entries to check artifact types
        query = query.join(
            MarketplaceCatalogEntry,
            MarketplaceSource.id == MarketplaceCatalogEntry.source_id
        )
        filters.append(
            MarketplaceCatalogEntry.artifact_type.in_(types)
        )

    # Tags filter (AND logic)
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        for tag in tag_list:
            filters.append(
                func.json_contains(MarketplaceSource.tags, f'"{tag}"')
            )

    # Trust level filter
    if trust_level:
        filters.append(MarketplaceSource.trust_level == trust_level)

    # Search filter
    if search:
        search_pattern = f"%{search}%"
        filters.append(
            or_(
                MarketplaceSource.repo_name.ilike(search_pattern),
                MarketplaceSource.repo_description.ilike(search_pattern)
            )
        )

    # Apply all filters with AND logic
    if filters:
        query = query.where(and_(*filters))

    # Execute query with pagination
    result = await self.session.execute(
        query.limit(limit + 1)  # Fetch one extra for hasNextPage
    )
    sources = result.scalars().all()

    # Build paginated response
    has_next = len(sources) > limit
    items = sources[:limit]

    return PaginatedResponse(
        items=[SourceResponse.from_orm(s) for s in items],
        pageInfo=PageInfo(
            hasNextPage=has_next,
            endCursor=encode_cursor(items[-1].id) if items else None,
        )
    )
```

**Step 5: Update Router Endpoint**

```python
# skillmeat/api/routers/marketplace_sources.py
from fastapi import Query

@router.get("/marketplace/sources", response_model=PaginatedResponse[SourceResponse])
async def list_sources(
    artifact_type: Optional[str] = Query(
        None,
        description="Filter by artifact type (comma-separated)"
    ),
    tags: Optional[str] = Query(
        None,
        description="Filter by tags (comma-separated, AND logic)"
    ),
    owner: Optional[str] = Query(
        None,
        description="Filter by repository owner"
    ),
    trust_level: Optional[str] = Query(
        None,
        description="Filter by trust level"
    ),
    search: Optional[str] = Query(
        None,
        description="Full-text search"
    ),
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    manager: SourceManager = Depends(get_source_manager),
) -> PaginatedResponse[SourceResponse]:
    """
    List marketplace sources with filtering.

    Query Parameters:
    - owner: Filter by GitHub username (e.g., "anthropics")
    - artifact_type: Filter by type (e.g., "skill,command")
    - tags: Filter by tags with AND logic (e.g., "production,verified")
    - trust_level: Filter by trust (basic, verified, official)
    - search: Search by name or description

    All filters are composable (AND logic across different filter types).

    Example:
    GET /api/v1/marketplace/sources?owner=anthropics&artifact_type=skill&tags=production
    """
    try:
        return await manager.list_sources_with_filters(
            artifact_type=artifact_type,
            tags=tags,
            owner=owner,
            trust_level=trust_level,
            search=search,
            cursor=cursor,
            limit=limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

**Step 6: Update Frontend Types**

```typescript
// skillmeat/web/types/marketplace.ts
export interface SourceFilterParams {
  artifactType?: string;
  tags?: string[];
  owner?: string;  // New filter
  trustLevel?: string;
  search?: string;
}

export interface SourceListQuery {
  artifact_type?: string;
  tags?: string;
  owner?: string;  // New filter
  trust_level?: string;
  search?: string;
  cursor?: string;
  limit?: number;
}
```

**Step 7: Update Frontend Filter Component**

```typescript
// skillmeat/web/components/marketplace/source-filter-bar.tsx
export function SourceFilterBar() {
  const [filters, setFilters] = useSourceFilters();

  return (
    <div className="flex gap-4">
      {/* Existing filters */}
      <Select
        value={filters.artifactType || ""}
        onValueChange={(value) => {
          setFilters({ ...filters, artifactType: value || undefined });
        }}
      >
        <SelectTrigger className="w-32">
          <SelectValue placeholder="Artifact Type" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="">All Types</SelectItem>
          <SelectItem value="skill">Skills</SelectItem>
          <SelectItem value="command">Commands</SelectItem>
        </SelectContent>
      </Select>

      {/* New owner filter */}
      <Input
        placeholder="Filter by owner..."
        value={filters.owner || ""}
        onChange={(e) => {
          setFilters({ ...filters, owner: e.target.value || undefined });
        }}
        className="w-40"
      />

      {/* Clear filters button */}
      <Button
        variant="outline"
        onClick={() => setFilters({})}
      >
        Clear All
      </Button>
    </div>
  );
}
```

## Adding New Source Metadata Fields

### Example: Adding "License" Metadata

**Step 1: Update Database Schema**

```python
# skillmeat/database/models/marketplace.py
class MarketplaceSource(Base):
    __tablename__ = "marketplace_sources"

    # ... existing fields ...
    license: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
```

**Step 2: Create Migration**

```bash
alembic revision --autogenerate -m "Add license and last_updated_at to sources"
```

**Step 3: Update Schemas**

```python
# skillmeat/api/schemas/marketplace.py
class SourceResponse(BaseModel):
    """Source response with new metadata fields."""
    id: str
    repo_url: str
    license: Optional[str] = Field(None, description="SPDX license identifier")
    last_updated_at: Optional[datetime] = Field(
        None,
        description="When the source was last updated"
    )
    # ... other fields ...

class CreateSourceRequest(BaseModel):
    """Request to create a new source."""
    repo_url: str
    import_repo_description: bool = True
    import_repo_readme: bool = True
    tags: Optional[List[str]] = []
    # Optional metadata that can be imported from GitHub
    import_license: bool = False  # New
    import_last_updated: bool = False  # New
```

**Step 4: Update GitHub Scanner**

```python
# skillmeat/core/marketplace/github_scanner.py
class GitHubScanner:
    async def scan_repository(
        self,
        repo_url: str,
        import_repo_description: bool = True,
        import_repo_readme: bool = True,
        import_license: bool = False,  # New parameter
        import_last_updated: bool = False,  # New parameter
    ) -> RepositoryScanResult:
        """
        Scan repository for artifacts and metadata.

        Args:
            repo_url: GitHub repository URL
            import_repo_description: Whether to import repository description
            import_repo_readme: Whether to import README content
            import_license: Whether to fetch SPDX license identifier (new)
            import_last_updated: Whether to fetch last update timestamp (new)

        Returns:
            RepositoryScanResult with artifacts and optional metadata
        """
        metadata = {}

        # Existing metadata collection
        if import_repo_description:
            metadata["description"] = await self.get_repo_description(repo_url)

        if import_repo_readme:
            metadata["readme"] = await self.get_readme(repo_url)

        # New metadata collection
        if import_license:
            metadata["license"] = await self.get_license_identifier(repo_url)

        if import_last_updated:
            metadata["last_updated_at"] = await self.get_last_updated(repo_url)

        # ... existing artifact scanning ...

        return RepositoryScanResult(
            artifacts=artifacts,
            metadata=metadata,
        )

    async def get_license_identifier(self, repo_url: str) -> Optional[str]:
        """Fetch SPDX license identifier from GitHub API."""
        repo_data = await self.github_client.get_repo_metadata(repo_url)
        return repo_data.get("license", {}).get("spdx_id")

    async def get_last_updated(self, repo_url: str) -> Optional[datetime]:
        """Fetch repository last update timestamp."""
        repo_data = await self.github_client.get_repo_metadata(repo_url)
        return datetime.fromisoformat(repo_data.get("updated_at", ""))
```

**Step 5: Validate Field Format**

Add validation for new fields in schemas:

```python
# skillmeat/api/schemas/marketplace.py
from pydantic import validator

class CreateSourceRequest(BaseModel):
    license: Optional[str] = None

    @validator('license')
    def validate_license(cls, v):
        """Validate SPDX license format."""
        if v is None:
            return v

        # List of common SPDX identifiers
        valid_licenses = {'MIT', 'Apache-2.0', 'GPL-3.0', 'BSD-3-Clause', ...}
        if v not in valid_licenses:
            raise ValueError(f"License {v} is not a valid SPDX identifier")
        return v
```

## Extending Tag Functionality

### Example: Adding Tag Hierarchies

**Current State**: Tags are flat strings (e.g., "production", "verified")

**Goal**: Support tag categories (e.g., "environment:production", "status:verified")

**Step 1: Update Data Model**

```python
# skillmeat/database/models/marketplace.py
class MarketplaceSource(Base):
    # Current: tags stored as JSON array
    # tags: List[str] = ["production", "verified"]

    # New: tags stored with category structure
    # tags: List[str] = ["environment:production", "status:verified", "api:rest"]

    # Still stored as JSON array, but with semantic structure
```

**Step 2: Update Tag Validation**

```python
# skillmeat/utils/validators.py
def validate_tags(tags: List[str], max_tags: int = 20) -> List[str]:
    """
    Validate and normalize tags.

    Supports:
    - Simple tags: "production", "verified"
    - Hierarchical tags: "environment:production", "status:verified"

    Format: alphanumeric, hyphens, underscores, colons (1-50 chars total)
    """
    if len(tags) > max_tags:
        raise ValueError(f"Maximum {max_tags} tags allowed, got {len(tags)}")

    validated = []
    tag_pattern = re.compile(r'^[a-z0-9_-]+(:[a-z0-9_-]+)?$')

    for tag in tags:
        normalized = tag.strip().lower()
        if not normalized:
            raise ValueError("Empty tags not allowed")
        if len(normalized) > 50:
            raise ValueError(f"Tag too long: {normalized} (max 50 chars)")
        if not tag_pattern.match(normalized):
            raise ValueError(
                f"Invalid tag format: {tag}\n"
                f"Use alphanumeric, hyphens, underscores, colons: "
                f"'production' or 'environment:production'"
            )
        validated.append(normalized)

    return sorted(list(set(validated)))  # Deduplicate and sort
```

**Step 3: Update Tag Display Component**

```typescript
// skillmeat/web/components/marketplace/tag-badge.tsx
interface TagBadgeProps {
  tag: string;
  onFilter?: (tag: string) => void;
}

export function TagBadge({ tag, onFilter }: TagBadgeProps) {
  // Parse hierarchical tag
  const [category, value] = tag.includes(':')
    ? tag.split(':', 2)
    : [null, tag];

  return (
    <button
      onClick={() => onFilter?.(tag)}
      className="px-2 py-1 text-xs rounded-full"
      style={{
        backgroundColor: getCategoryColor(category),
        color: 'white',
      }}
    >
      {value}
      {category && <span className="opacity-70"> ({category})</span>}
    </button>
  );
}

function getCategoryColor(category: string | null): string {
  const colors: Record<string, string> = {
    environment: '#3B82F6',  // blue
    status: '#10B981',       // green
    api: '#F59E0B',          // amber
    null: '#6B7280',         // gray
  };
  return colors[category || 'null'] || colors.null;
}
```

**Step 4: Add Tag Autocomplete**

```typescript
// skillmeat/web/hooks/useTagAutocomplete.ts
export function useTagAutocomplete(sources: SourceResponse[]) {
  const allTags = new Set<string>();
  sources.forEach(source => {
    source.tags?.forEach(tag => allTags.add(tag));
  });

  return (inputValue: string): string[] => {
    const lowerInput = inputValue.toLowerCase();
    return Array.from(allTags)
      .filter(tag => tag.startsWith(lowerInput))
      .sort()
      .slice(0, 5);
  };
}
```

## Backward Compatibility Considerations

### Making Changes Without Breaking Existing Clients

**Principle 1: Optional New Fields**

```python
# New fields must be optional
class SourceResponse(BaseModel):
    id: str
    # Existing fields
    artifact_count: int

    # New fields - make optional with defaults
    counts_by_type: Optional[Dict[str, int]] = None
    owner: Optional[str] = None
    license: Optional[str] = None
```

**Principle 2: Additive, Not Subtractive**

```python
# Good: Add new endpoint without removing old one
GET /api/v1/marketplace/sources  # Original (keep working)
GET /api/v1/marketplace/sources?owner=x  # Enhanced (adds filter)

# Bad: Remove field from response
# SourceResponse.artifact_count removed and replaced with counts_by_type
```

**Principle 3: Provide Migration Path**

```python
# Keep old field for transition period
class SourceResponse(BaseModel):
    # Old field (deprecated but working)
    artifact_count: int

    # New field (computed from counts_by_type)
    counts_by_type: Dict[str, int]

    @property
    def artifact_count(self) -> int:
        """Deprecated: Use counts_by_type instead."""
        return sum(self.counts_by_type.values())
```

**Principle 4: Document Deprecation**

```python
class SourceResponse(BaseModel):
    artifact_count: int = Field(
        ...,
        description="DEPRECATED: Use counts_by_type instead. Total artifact count.",
        deprecated=True,
    )
    counts_by_type: Dict[str, int] = Field(
        ...,
        description="Artifact count breakdown by type. Recommended field."
    )
```

### Migration Script Example

```python
# scripts/migrate_sources.py
"""
Migration helper: Update existing sources with new metadata.

This is a one-time operation to populate optional fields in existing sources.
It's safe to run multiple times (idempotent).
"""

async def populate_license_metadata():
    """Backfill license field for existing sources."""
    async with get_db_session() as session:
        # Find sources without license
        sources_without_license = await session.execute(
            select(MarketplaceSource).where(
                MarketplaceSource.license.is_(None)
            )
        )

        sources = sources_without_license.scalars().all()
        updated_count = 0

        for source in sources:
            try:
                license = await github_client.get_license(source.repo_url)
                source.license = license
                session.add(source)
                updated_count += 1
            except Exception as e:
                logger.warning(f"Failed to get license for {source.repo_url}: {e}")

        await session.commit()
        return f"Updated {updated_count} sources with license metadata"

# Run migration
if __name__ == "__main__":
    asyncio.run(populate_license_metadata())
```

## Testing New Filters and Metadata

### Unit Tests

```python
# tests/unit/test_marketplace_filters.py
import pytest

class TestSourceFiltering:
    """Unit tests for source filtering logic."""

    @pytest.mark.asyncio
    async def test_filter_by_owner(self):
        """Filter sources by repository owner."""
        repo = SourceRepository(session)

        # Create test data
        source1 = MarketplaceSource(
            repo_url="https://github.com/anthropics/cookbook",
            owner="anthropics",
        )
        source2 = MarketplaceSource(
            repo_url="https://github.com/other/project",
            owner="other",
        )

        # Test filter
        result = await repo.list_sources_with_filters(owner="anthropics")
        assert len(result.items) == 1
        assert result.items[0].owner == "anthropics"

    @pytest.mark.asyncio
    async def test_filter_by_license(self):
        """Filter sources by SPDX license."""
        repo = SourceRepository(session)

        # Create test data with different licenses
        mit_source = MarketplaceSource(license="MIT")
        apache_source = MarketplaceSource(license="Apache-2.0")

        result = await repo.list_sources_with_filters(license="MIT")
        assert all(s.license == "MIT" for s in result.items)

    @pytest.mark.asyncio
    async def test_combined_filters_and_logic(self):
        """Test combining multiple filters with AND logic."""
        repo = SourceRepository(session)

        # Create test sources
        # - Source A: owner=anthropics, license=MIT, tags=[production]
        # - Source B: owner=anthropics, license=Apache-2.0, tags=[production]
        # - Source C: owner=other, license=MIT, tags=[staging]

        # Filter: owner=anthropics AND license=MIT
        result = await repo.list_sources_with_filters(
            owner="anthropics",
            license="MIT"
        )
        assert len(result.items) == 1
        assert result.items[0].owner == "anthropics"
        assert result.items[0].license == "MIT"

class TestTagValidation:
    """Unit tests for tag validation."""

    def test_validate_simple_tags(self):
        """Validate simple alphanumeric tags."""
        validated = validate_tags(["production", "verified"])
        assert validated == ["production", "verified"]

    def test_validate_hierarchical_tags(self):
        """Validate hierarchical category:value tags."""
        validated = validate_tags([
            "environment:production",
            "status:verified",
        ])
        assert "environment:production" in validated

    def test_tag_normalization(self):
        """Tags are normalized (lowercase, whitespace stripped)."""
        validated = validate_tags([" PRODUCTION ", "Verified"])
        assert validated == ["production", "verified"]

    def test_reject_invalid_tags(self):
        """Reject tags with invalid characters."""
        with pytest.raises(ValueError):
            validate_tags(["invalid tag!"])  # space and exclamation not allowed

        with pytest.raises(ValueError):
            validate_tags(["a" * 51])  # exceeds 50 char limit

    def test_max_tags_limit(self):
        """Reject sources with too many tags."""
        with pytest.raises(ValueError):
            validate_tags(["tag" + str(i) for i in range(25)])  # exceeds 20
```

### Integration Tests

```python
# tests/integration/test_source_filter_api.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
class TestSourceFilterAPI:
    """Integration tests for source filtering API."""

    async def test_get_sources_with_owner_filter(self, client: AsyncClient):
        """Test GET /marketplace/sources?owner=X endpoint."""
        response = await client.get(
            "/api/v1/marketplace/sources?owner=anthropics"
        )
        assert response.status_code == 200
        data = response.json()
        assert all(s["owner"] == "anthropics" for s in data["items"])

    async def test_combined_filters_endpoint(self, client: AsyncClient):
        """Test combining multiple filter parameters."""
        response = await client.get(
            "/api/v1/marketplace/sources?"
            "owner=anthropics&"
            "artifact_type=skill&"
            "tags=production,verified"
        )
        assert response.status_code == 200
        data = response.json()

        for source in data["items"]:
            assert source["owner"] == "anthropics"
            # artifact_type filter verified through join query
            # tags verified through tag matching

    async def test_invalid_filter_value(self, client: AsyncClient):
        """Test invalid filter values return 400."""
        response = await client.get(
            "/api/v1/marketplace/sources?artifact_type=invalid_type"
        )
        assert response.status_code == 400
        assert "invalid_type" in response.json()["error"]["message"]
```

### E2E Tests

```typescript
// tests/e2e/marketplace-filter.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Marketplace Source Filtering', () => {
  test('should filter sources by owner', async ({ page }) => {
    await page.goto('/marketplace/sources');

    // Open filter dropdown
    await page.click('text=Filter by owner');

    // Select an owner
    await page.click('text=anthropics');

    // Verify results are filtered
    const sources = await page.locator('[data-testid="source-card"]').all();
    for (const source of sources) {
      const owner = await source.locator('[data-testid="owner"]').textContent();
      expect(owner).toBe('anthropics');
    }
  });

  test('should apply multiple filters with AND logic', async ({ page }) => {
    await page.goto('/marketplace/sources');

    // Apply owner filter
    await page.selectOption('[data-testid="owner-filter"]', 'anthropics');

    // Apply license filter
    await page.selectOption('[data-testid="license-filter"]', 'MIT');

    // Verify URL has both filters
    expect(page.url()).toContain('owner=anthropics');
    expect(page.url()).toContain('license=MIT');

    // Verify all results match both filters
    const sources = await page.locator('[data-testid="source-card"]').all();
    for (const source of sources) {
      const owner = await source.locator('[data-testid="owner"]').textContent();
      const license = await source.locator('[data-testid="license"]').textContent();

      expect(owner).toBe('anthropics');
      expect(license).toBe('MIT');
    }
  });

  test('should clear individual filters', async ({ page }) => {
    await page.goto('/marketplace/sources?owner=anthropics&license=MIT');

    // Click clear button for owner filter
    await page.click('[data-testid="clear-owner-filter"]');

    // Verify owner filter removed from URL but license remains
    expect(page.url()).not.toContain('owner=');
    expect(page.url()).toContain('license=MIT');
  });

  test('should clear all filters at once', async ({ page }) => {
    await page.goto('/marketplace/sources?owner=anthropics&license=MIT&tags=production');

    // Click clear all button
    await page.click('text=Clear All');

    // Verify URL has no filter parameters
    expect(page.url()).not.toContain('?');

    // Verify all sources are displayed
    const sources = await page.locator('[data-testid="source-card"]').all();
    expect(sources.length).toBeGreaterThan(3);
  });
});
```

## Performance Considerations

### Database Indexes

```python
# skillmeat/database/models/marketplace.py
class MarketplaceSource(Base):
    __tablename__ = "marketplace_sources"

    owner: Mapped[str] = mapped_column(String(255))
    license: Mapped[Optional[str]] = mapped_column(String(100))
    tags: Mapped[Dict] = mapped_column(JSON)

    __table_args__ = (
        # Single-field indexes for fast filtering
        Index("idx_marketplace_sources_owner", "owner"),
        Index("idx_marketplace_sources_license", "license"),

        # Composite index for common filter combinations
        Index(
            "idx_marketplace_sources_owner_license",
            "owner",
            "license",
        ),
    )
```

### Query Optimization

```python
# skillmeat/database/repositories/marketplace_source_repository.py
async def list_sources_with_filters(...) -> PaginatedResponse[SourceResponse]:
    """
    Optimized query using indexes and eager loading.

    Performance targets:
    - Single filter: <50ms for 1000+ sources
    - Multiple filters (AND): <100ms for 1000+ sources
    - Full-text search: <200ms for 1000+ sources
    """
    query = select(MarketplaceSource)

    # Eager load related catalog entries to avoid N+1 queries
    query = query.options(
        selectinload(MarketplaceSource.catalog_entries)
    )

    # Apply indexed filters first (most selective)
    if owner:
        query = query.where(MarketplaceSource.owner == owner)

    if license:
        query = query.where(MarketplaceSource.license == license)

    # Apply less selective filters
    if tags:
        for tag in tag_list:
            query = query.where(
                func.json_contains(MarketplaceSource.tags, f'"{tag}"')
            )

    # Full-text search last (least selective, most expensive)
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                MarketplaceSource.repo_name.ilike(search_pattern),
                MarketplaceSource.repo_description.ilike(search_pattern),
            )
        )

    # Execute with cursor pagination
    result = await self.session.execute(query)
    return build_paginated_response(result, cursor, limit)
```

### Caching Strategy

```python
# skillmeat/cache/marketplace_cache.py
class MarketplaceCache:
    """Cache frequently accessed filter values."""

    async def get_available_owners(self, ttl: int = 3600) -> List[str]:
        """Cache list of available repository owners (1 hour TTL)."""
        cache_key = "marketplace:owners"

        if cached := await self.redis.get(cache_key):
            return json.loads(cached)

        # Query database for distinct owners
        result = await session.execute(
            select(func.distinct(MarketplaceSource.owner))
        )
        owners = sorted(result.scalars().all())

        # Cache result
        await self.redis.setex(
            cache_key,
            ttl,
            json.dumps(owners),
        )

        return owners

    async def invalidate_on_source_change(self, source_id: str):
        """Invalidate relevant caches when source is modified."""
        await self.redis.delete("marketplace:owners")
        await self.redis.delete(f"marketplace:source:{source_id}")
```

## Common Patterns

### Pattern 1: Composable Filter Builders

```python
# Build filters incrementally
class SourceFilterBuilder:
    """Fluent API for building source filters."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.query = select(MarketplaceSource)
        self.filters = []

    def by_owner(self, owner: str) -> "SourceFilterBuilder":
        """Filter by repository owner."""
        self.filters.append(MarketplaceSource.owner == owner)
        return self

    def by_license(self, license: str) -> "SourceFilterBuilder":
        """Filter by SPDX license."""
        self.filters.append(MarketplaceSource.license == license)
        return self

    def by_tags(self, tags: List[str]) -> "SourceFilterBuilder":
        """Filter by tags (AND logic)."""
        for tag in tags:
            self.filters.append(
                func.json_contains(MarketplaceSource.tags, f'"{tag}"')
            )
        return self

    async def execute(self) -> List[SourceResponse]:
        """Execute the query."""
        if self.filters:
            self.query = self.query.where(and_(*self.filters))

        result = await self.session.execute(self.query)
        return [SourceResponse.from_orm(s) for s in result.scalars()]

# Usage
sources = await (
    SourceFilterBuilder(session)
    .by_owner("anthropics")
    .by_license("MIT")
    .by_tags(["production"])
    .execute()
)
```

### Pattern 2: Filter Validation and Normalization

```python
# Validate filters before executing queries
def validate_source_filters(
    artifact_type: Optional[str] = None,
    owner: Optional[str] = None,
    license: Optional[str] = None,
    tags: Optional[str] = None,
) -> Dict[str, Any]:
    """Validate and normalize filter parameters."""
    validated = {}

    if artifact_type:
        valid_types = {"skill", "command", "agent", "mcp", "hook"}
        types = {t.strip() for t in artifact_type.split(",")}
        invalid = types - valid_types
        if invalid:
            raise ValueError(
                f"Invalid artifact types: {invalid}. "
                f"Valid types: {valid_types}"
            )
        validated["artifact_type"] = list(types)

    if owner:
        owner = owner.strip()
        if not re.match(r'^[a-zA-Z0-9-]+$', owner):
            raise ValueError(f"Invalid owner format: {owner}")
        validated["owner"] = owner

    if license:
        # Validate against known SPDX identifiers
        if not is_valid_spdx(license.upper()):
            raise ValueError(f"Unknown SPDX license: {license}")
        validated["license"] = license.upper()

    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        validated["tags"] = validate_tags(tag_list)

    return validated
```

## Summary

When extending source filters and metadata:

1. **Update all layers**: Database → Repository → Service → Router → Frontend
2. **Maintain backward compatibility**: Keep old fields, add new ones optionally
3. **Add proper validation**: Validate at schema and service layers
4. **Use database indexes**: Index frequently filtered fields
5. **Test thoroughly**: Unit, integration, and E2E tests for all filters
6. **Document migration**: Provide clear upgrade paths for existing deployments
7. **Monitor performance**: Track query times, ensure filters remain fast

For detailed architectural decisions, see [ADR-marketplace-filtering](./decisions/ADR-marketplace-filtering.md).
