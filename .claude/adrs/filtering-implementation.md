---
title: "ADR-0002: Source Filtering Implementation with AND Semantics"
status: accepted
date: 2026-01-18
deciders: ["lead-architect", "backend-architect", "frontend-architect"]
tags: [adr, marketplace, filtering, query-parameters, search]
related:
  - /docs/project_plans/PRDs/enhancements/marketplace-sources-enhancement-v1.md
  - /skillmeat/api/routers/marketplace_sources.py
  - /skillmeat/web/app/marketplace/sources/page.tsx
---

# ADR-0002 — Source Filtering Implementation with AND Semantics

## Context

The Marketplace Sources Enhancement requires filtering capabilities to help users discover relevant sources from potentially hundreds of entries. Users need to narrow down by:

- **Artifact Type** (skill, command, agent, etc.)
- **Tags** (user-created labels like "ui-ux", "testing", "internal")
- **Trust Level** (verified, community, experimental)
- **Text Search** (repository name, description)

Key design questions:

1. **Filter Composition Logic**: When applying multiple filters (e.g., type=skill AND tags=ui-ux), should they combine with AND (all must match) or OR (any can match)?
2. **URL State Management**: How are filters persisted for bookmarkable/shareable URLs?
3. **Query Parameter Structure**: What's the parameter syntax for multi-value filters like tags?
4. **Frontend State**: How is filter state synchronized between URL and UI components?
5. **Scalability**: How do filters perform with 10K+ sources?

## Decision

We implement **source filtering with AND semantics** and **URL-based state management**:

### 1. Filter Composition Logic (AND Semantics)

All applied filters use AND logic: sources must match **all** active filters simultaneously.

**Example**: `artifact_type=skill&tags=ui-ux&tags=testing&trust_level=verified`

Result: Only sources that are:
- Artifact type = skill **AND**
- Tags include "ui-ux" **AND**
- Tags include "testing" **AND**
- Trust level = verified

**Rationale**:
- AND logic is more predictable and aligns with mental model of "narrowing down" results
- Users expect that adding more filters further constrains results, not expands them
- Prevents accidentally "opening up" results by adding filters
- Simpler to explain and implement initially

### 2. Query Parameter Syntax

Use repeated query parameters for multi-value filters:

```
GET /api/v1/marketplace/sources?artifact_type=skill&tags=ui-ux&tags=testing&trust_level=verified
```

**Parameter Reference**:

| Parameter | Values | Semantics | Optional |
|-----------|--------|-----------|----------|
| `artifact_type` | skill, command, agent, hook, mcp | Single value (OR within type future) | Yes |
| `tags` | string (alphanumeric, hyphens, underscores) | Multiple values, AND logic | Yes |
| `trust_level` | verified, community, experimental | Single value | Yes |
| `search` | string (free-text) | Full-text search on name + description | Yes |
| `limit` | 1-100 | Pagination page size | Yes (default: 25) |
| `cursor` | string (opaque token) | Pagination cursor | Yes (first page omits cursor) |

**All filters are optional**. Omitting all filters returns all sources (pagination applies).

### 3. Pagination with Filters

Use **cursor-based pagination** (not offset-based):

```json
{
  "items": [
    { "id": "...", "repo_name": "...", "tags": [...], "artifact_type": "skill" },
    ...
  ],
  "pageInfo": {
    "hasNextPage": true,
    "endCursor": "abc123xyz789",
    "totalCount": 47
  }
}
```

**Rationale for Cursor**:
- Works correctly with dynamic filtering (filter results don't change between page requests)
- Handles deletions between page requests gracefully
- More efficient than offset-based for large datasets

### 4. Frontend State Management

Use **Next.js `useSearchParams()` + `useRouter()`** for URL state:

```typescript
// Read filters from URL
const searchParams = useSearchParams();
const artifact_type = searchParams.get('artifact_type');
const tags = searchParams.getAll('tags');
const trust_level = searchParams.get('trust_level');
const search = searchParams.get('search');

// Update URL when filters change
const router = useRouter();
const applyFilters = (newFilters: FilterState) => {
  const params = new URLSearchParams();
  if (newFilters.artifact_type) params.set('artifact_type', newFilters.artifact_type);
  newFilters.tags.forEach(tag => params.append('tags', tag));
  if (newFilters.trust_level) params.set('trust_level', newFilters.trust_level);
  if (newFilters.search) params.set('search', newFilters.search);

  router.push(`/marketplace/sources?${params.toString()}`);
};
```

**Benefits**:
- Filters are bookmarkable (users can share filtered views)
- Browser back/forward navigation works intuitively
- Deep linking supported ("Send me a link with these filters applied")
- TanStack Query (useQuery) automatically includes URL params as cache key

### 5. Filter UI Components

**SourceFilterBar Component** (reusable across pages):

```typescript
interface SourceFilterBarProps {
  onFiltersChange: (filters: SourceFilterState) => void;
  initialFilters?: SourceFilterState;
  compact?: boolean; // Mobile layout
}

interface SourceFilterState {
  artifact_type?: string;
  tags: string[];
  trust_level?: string;
  search?: string;
}
```

**UI Elements**:
- **Artifact Type**: Dropdown (single select)
- **Tags**: Combobox with chips (multi-select, autocomplete from existing tag list)
- **Trust Level**: Radio buttons or dropdown (single select)
- **Search**: Text input with debounce (500ms)
- **Clear All**: Button to reset all filters
- **Active Filters Display**: Pill badges showing applied filters, each with close button

### 6. Backend Implementation

**Router endpoint** (`skillmeat/api/routers/marketplace_sources.py`):

```python
@router.get("/sources", response_model=SourceListResponse)
async def list_sources(
    artifact_type: Optional[str] = Query(None),
    tags: Optional[List[str]] = Query(None),
    trust_level: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(25, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    db: Session = Depends(get_db_session),
) -> SourceListResponse:
    # Repository layer builds WHERE clause with AND logic
    results = SourceRepository.list_filtered(
        db=db,
        artifact_type=artifact_type,
        tags=tags,
        trust_level=trust_level,
        search=search,
        limit=limit,
        cursor=cursor,
    )
    return SourceListResponse(items=results.items, pageInfo=results.pageInfo)
```

**Repository layer** builds efficient SQL with indexed queries:

```python
def list_filtered(self, db: Session, **filters) -> PaginatedResult:
    query = db.query(Source)

    # All filters use AND logic (each adds WHERE clause)
    if filters.get('artifact_type'):
        query = query.filter(Source.artifact_type == filters['artifact_type'])

    if filters.get('tags'):
        # Filter sources where ALL specified tags are present
        for tag in filters['tags']:
            query = query.filter(Source.tags.contains(tag))

    if filters.get('trust_level'):
        query = query.filter(Source.trust_level == filters['trust_level'])

    if filters.get('search'):
        search_term = f"%{filters['search']}%"
        query = query.filter(
            or_(
                Source.repo_name.ilike(search_term),
                Source.repo_description.ilike(search_term),
                Source.user_description.ilike(search_term),
            )
        )

    # Cursor pagination
    return self._paginate(query, limit=filters['limit'], cursor=filters['cursor'])
```

### 7. Database Indexing

Create indexes for filter performance:

```sql
CREATE INDEX idx_source_artifact_type ON sources(artifact_type);
CREATE INDEX idx_source_trust_level ON sources(trust_level);
CREATE INDEX idx_source_tags ON sources USING GIN(tags);  -- For tag filtering
CREATE INDEX idx_source_name_search ON sources(repo_name);  -- Text search
```

## Consequences

### Positive

- ✅ **Intuitive Behavior**: AND semantics match user expectations of "narrowing down"
- ✅ **URL Bookmarkable**: Filters in query parameters enable sharing and deep linking
- ✅ **Efficient Pagination**: Cursor-based pagination handles dynamic results correctly
- ✅ **Scalable**: Database indexes on filter columns enable <200ms queries on 10K+ sources
- ✅ **Extensible**: Can add new filter types (e.g., `last_sync_after`, `artifact_count_min`) without UI changes
- ✅ **Mobile Friendly**: Compact filter UI adapts to small screens
- ✅ **Accessible**: Semantic HTML with proper labels and ARIA attributes

### Negative

- ❌ **Cannot Express OR Logic**: Users cannot say "sources with tag A **or** tag B"; must see sources matching both
- ❌ **No Advanced Syntax**: Power users cannot use boolean operators (AND, OR, NOT); limited to simple filters
- ❌ **Tag List Explosion**: Without OR logic, users may struggle to find sources if many tags exist
- ❌ **URL Length**: Many tags can create long URLs (mitigation: browser/server URL length limits are generous for typical use)

### Mitigations

1. **OR Logic (v2)**: Add query parameter `tags_mode=any` to support "any of these tags" filtering
2. **Tag Suggestions**: Implement tag autocomplete and suggestions to guide users toward common tags
3. **Saved Filters**: Allow users to save/bookmark frequently-used filter combinations
4. **Documentation**: Clear UI tooltips explaining AND semantics

## Alternatives Considered

### Alternative A: OR Logic for Tags

**Approach**: Multiple tags with `tags_mode=any` → sources with **any** of the specified tags.

**Considered But Deferred**:
- More complex SQL and frontend state management
- "OR" mode unclear from UI alone (requires mode parameter)
- Can be implemented in v2 once AND logic is validated
- Mitigates "tag explosion" concern after user research on adoption

### Alternative B: Advanced Query Syntax

**Approach**: Support complex syntax like `artifact_type:skill AND tags:ui-ux OR tags:testing`.

**Rejected Because**:
- Too complex for initial release
- Requires query parser implementation
- Confusing UI for non-technical users
- Query parameter encoding becomes messy

### Alternative C: Hybrid Offset + Cursor Pagination

**Approach**: Offer both offset (for sorting) and cursor (for data changes).

**Rejected Because**:
- Adds implementation complexity
- Offset is less efficient with filters
- Cursor-only approach sufficient for marketplace use case

## Follow-Up Actions

1. **v1.1 Enhancement**: Add `tags_mode=any` parameter for OR logic if user feedback indicates demand
2. **Observability**: Track filter parameter usage; measure which filters are most frequently applied
3. **Performance Monitoring**: Set up alerts if source list query exceeds 200ms (index tuning trigger)
4. **User Research**: Survey users on filter experience; validate AND semantics intuitive
5. **Documentation**: Add filter examples to API docs and user guide

## Design Principles Summary

| Principle | Implementation |
|-----------|-----------------|
| **Composability** | All filters work simultaneously with AND logic |
| **URL State** | Filters reflected in query parameters for deep linking |
| **Pagination** | Cursor-based to handle dynamic filtered results |
| **Performance** | Database indexes on all filter columns |
| **Extensibility** | Can add new filters without changing core logic |
| **Discoverability** | UI clearly shows what filters are applied and how to clear |

## Decision Record

**Decided**: 2026-01-18
**Approved By**: Lead Architect, Backend Architect, Frontend Architect
**Implementation Status**: Accepted for Phase 3 (Backend API Endpoints & Filtering) and Phase 5 (Frontend Marketplace List Integration)
