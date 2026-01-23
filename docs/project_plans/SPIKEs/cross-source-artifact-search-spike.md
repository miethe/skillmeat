---
title: "SPIKE: Cross-Source Artifact Search"
spike_id: "SPIKE-2026-01-20-cross-source-artifact-search"
date: 2026-01-20
status: research-complete
complexity: medium
related_request: "Marketplace search enhancement"
tags: [spike, search, marketplace, fts5, artifacts, cross-source]
---

# SPIKE: Cross-Source Artifact Search

**Goal**: Research and design the enhancement of the /marketplace/sources page to support searching detected artifacts across all sources from a single location, enabling users to find specific artifacts without knowing which source contains them.

## Executive Summary

**Feasibility: HIGH** - This feature is technically feasible with moderate complexity.

The recommended approach uses a phased implementation:
1. **Phase 1**: Extend existing SQLite schema with denormalized search columns + API-level search endpoint (~3 days)
2. **Phase 2**: Add SQLite FTS5 full-text search if basic search proves insufficient (~2 days)
3. **Phase 3**: Frontend dual-mode toggle between source search and artifact search (~2 days)

**Key constraints addressed:**
- GitHub API impact: Extract frontmatter during existing scan process (no additional API calls)
- Storage: ~850 bytes per artifact, ~42MB for 50K entries (acceptable)
- Query performance: <50ms at 50K scale with proper indexes; <10ms with FTS5
- Caching: Persists to database; no additional caching layer required

---

## Current State Analysis

### Frontend Implementation
- **Location**: `skillmeat/web/app/marketplace/sources/page.tsx`
- **Current search**: Client-side filtering on `owner`/`repo_name` only
- **No search parameter** passed to API - all sources fetched then filtered locally
- **React Query**: Sources list cached with 60-second staleTime

### API Layer
- **Location**: `skillmeat/api/routers/marketplace_sources.py`
- **List endpoint**: Supports only `cursor` and `limit` parameters
- **No full-text search endpoint** exists
- **Catalog entries**: Per-source filtering available (type, status, confidence)

### Database Schema
- **MarketplaceSource** (`cache/models.py:1182-1468`):
  - Columns: `repo_url`, `owner`, `repo_name`, `description`, `tags`, `trust_level`
  - Indexed: `repo_url` (unique), `last_sync_at`, `scan_status`

- **MarketplaceCatalogEntry** (`cache/models.py:1470+`):
  - Columns: `name`, `path`, `artifact_type`, `confidence_score`, `status`, `metadata_json`
  - Indexed: `source_id + status`, `artifact_type`
  - **Frontmatter parsed but not persisted** for search

### GitHub Caching
- **Location**: `skillmeat/api/utils/github_cache.py`
- In-memory LRU cache (max 1000 entries)
- TTL: Trees=1hr, Contents=2hr
- Designed for browsing, not search indexing

---

## Requirements

### Functional Requirements
1. Search artifacts by name, tags, and type across ALL marketplace sources
2. Support filtering by artifact type, confidence score, trust level
3. Search frontmatter fields (title, description, tags from SKILL.md)
4. Toggle between "search sources" and "search artifacts" modes
5. Display results grouped by source with context

### Non-Functional Requirements
1. **GitHub API**: No additional API calls beyond existing scan process
2. **Storage**: Minimize local cache size (target <100MB for 50K artifacts)
3. **Performance**: Search latency <100ms at 50K artifact scale
4. **Compute**: Avoid expensive runtime operations; pre-index during scan

---

## Design Options Evaluated

### Option A: Extend Existing SQLite Schema (RECOMMENDED for Phase 1)

**Approach**: Add denormalized search columns to `MarketplaceCatalogEntry` table.

**New Columns**:
```python
title: Optional[str]           # From frontmatter 'title' field
description: Optional[str]     # From frontmatter 'description' field
search_tags: Optional[str]     # JSON array combining frontmatter tags + path_tags
search_text: Optional[str]     # Denormalized searchable text blob
```

**Storage Estimate**:
- Per artifact: ~850 bytes
- Per source (50 artifacts avg): ~42 KB
- 1000 sources: ~42 MB (acceptable)

**Pros**:
- Uses existing SQLAlchemy infrastructure
- Transactional consistency with catalog entries
- Simple JOIN operations for filtering

**Cons**:
- Limited fuzzy matching capability
- LIKE queries slower than FTS at very large scale

### Option B: SQLite FTS5 Full-Text Search (RECOMMENDED for Phase 2)

**Approach**: Create FTS5 virtual table for advanced text search.

```sql
CREATE VIRTUAL TABLE catalog_fts USING fts5(
    name UNINDEXED,
    artifact_type UNINDEXED,
    title,
    description,
    search_text,
    tags,
    content='marketplace_catalog_entries',
    content_rowid='rowid',
    tokenize='porter unicode61 remove_diacritics 2'
);
```

**Features**:
- Boolean operators: AND, OR, NOT
- Phrase search: `"exact phrase"`
- Prefix search: `design*`
- BM25 relevance ranking
- Snippet generation for result highlighting

**Performance**:
- Simple term: <10ms at 50K entries
- Complex boolean: 10-50ms
- Index overhead: ~30-50% of content size

**Pros**:
- Excellent full-text search performance
- Built-in relevance ranking
- Prefix/phrase/boolean support

**Cons**:
- Requires sync triggers with main table
- FTS5 not guaranteed compiled into all SQLite builds
- Additional complexity

### Option C: In-Memory Index (NOT RECOMMENDED)

Building custom Trie/inverted index would require:
- Memory proportional to dataset (~50MB for 50K entries)
- Custom synchronization with persistent storage
- Unnecessary complexity when SQLite handles this scale efficiently

**Verdict**: SQLite handles this scale efficiently; avoid custom indexing.

---

## Technical Design

### Phase 1: Schema Extension + Basic Search

#### Database Migration

```python
# Alembic migration
def upgrade():
    op.add_column('marketplace_catalog_entries',
        sa.Column('title', sa.String(200), nullable=True))
    op.add_column('marketplace_catalog_entries',
        sa.Column('description', sa.Text, nullable=True))
    op.add_column('marketplace_catalog_entries',
        sa.Column('search_tags', sa.Text, nullable=True))
    op.add_column('marketplace_catalog_entries',
        sa.Column('search_text', sa.Text, nullable=True))

    # Create search indexes
    op.create_index('idx_catalog_search_name',
        'marketplace_catalog_entries', ['name'])
    op.create_index('idx_catalog_search_type_status',
        'marketplace_catalog_entries', ['artifact_type', 'status'])
    op.create_index('idx_catalog_search_confidence',
        'marketplace_catalog_entries', ['confidence_score'])
```

#### Repository Method

```python
class MarketplaceCatalogRepository(BaseRepository):
    def search(
        self,
        query: Optional[str] = None,
        artifact_type: Optional[str] = None,
        source_ids: Optional[List[str]] = None,
        min_confidence: Optional[int] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[MarketplaceCatalogEntry], int]:
        """Cross-source artifact search."""
        filters = [
            MarketplaceCatalogEntry.status.notin_(['excluded', 'removed'])
        ]

        if query:
            pattern = f"%{query}%"
            filters.append(or_(
                MarketplaceCatalogEntry.name.ilike(pattern),
                MarketplaceCatalogEntry.title.ilike(pattern),
                MarketplaceCatalogEntry.description.ilike(pattern),
                MarketplaceCatalogEntry.search_tags.ilike(pattern),
            ))

        if artifact_type:
            filters.append(MarketplaceCatalogEntry.artifact_type == artifact_type)

        if min_confidence:
            filters.append(MarketplaceCatalogEntry.confidence_score >= min_confidence)

        # Execute with JOIN for source context
        stmt = (
            select(MarketplaceCatalogEntry)
            .join(MarketplaceSource)
            .where(and_(*filters))
            .order_by(MarketplaceCatalogEntry.confidence_score.desc())
            .limit(limit)
            .offset(offset)
        )

        return session.execute(stmt).scalars().all(), total_count
```

#### API Endpoint

```python
@router.get("/catalog/search")
async def search_catalog(
    q: Optional[str] = Query(None, description="Search query"),
    type: Optional[str] = Query(None, description="Artifact type filter"),
    source_id: Optional[str] = Query(None, description="Limit to source"),
    min_confidence: int = Query(0, ge=0, le=100),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    limit: int = Query(50, ge=1, le=200),
    cursor: Optional[str] = Query(None),
) -> CatalogSearchResponse:
    """Search artifacts across all marketplace sources."""
```

#### Frontmatter Extraction (During Scan)

**Modify existing heuristic detector** to extract and persist frontmatter:

```python
# In heuristic_detector.py during artifact detection
if artifact_type == "skill" and "SKILL.md" in file_tree:
    content = github_client.get_file_content(repo, path + "/SKILL.md")
    frontmatter = parse_frontmatter(content)

    return DetectedArtifact(
        name=name,
        artifact_type="skill",
        path=path,
        confidence_score=score,
        # NEW: Persist searchable fields
        title=frontmatter.get("title"),
        description=frontmatter.get("description"),
        search_tags=json.dumps(frontmatter.get("tags", []) + path_tags),
        search_text=f"{name} {frontmatter.get('title', '')} {frontmatter.get('description', '')}",
    )
```

**GitHub API Impact**: Zero additional calls - SKILL.md is already fetched during detection for confidence scoring.

### Phase 2: FTS5 Full-Text Search

Add FTS5 virtual table with sync triggers when:
- Search latency exceeds 100ms at scale
- Users request advanced search features (phrase, prefix, boolean)

```sql
-- Create FTS5 table with external content
CREATE VIRTUAL TABLE catalog_fts USING fts5(
    name UNINDEXED,
    artifact_type UNINDEXED,
    title,
    description,
    search_text,
    tags,
    content='marketplace_catalog_entries',
    content_rowid='rowid',
    tokenize='porter unicode61 remove_diacritics 2'
);

-- Sync triggers
CREATE TRIGGER catalog_fts_insert AFTER INSERT ON marketplace_catalog_entries BEGIN
    INSERT INTO catalog_fts(rowid, name, artifact_type, title, description, search_text, tags)
    VALUES (new.rowid, new.name, new.artifact_type, new.title, new.description, new.search_text, new.search_tags);
END;

CREATE TRIGGER catalog_fts_delete AFTER DELETE ON marketplace_catalog_entries BEGIN
    INSERT INTO catalog_fts(catalog_fts, rowid, name, artifact_type, title, description, search_text, tags)
    VALUES ('delete', old.rowid, old.name, old.artifact_type, old.title, old.description, old.search_text, old.search_tags);
END;

CREATE TRIGGER catalog_fts_update AFTER UPDATE ON marketplace_catalog_entries BEGIN
    INSERT INTO catalog_fts(catalog_fts, rowid, name, artifact_type, title, description, search_text, tags)
    VALUES ('delete', old.rowid, old.name, old.artifact_type, old.title, old.description, old.search_text, old.search_tags);
    INSERT INTO catalog_fts(rowid, name, artifact_type, title, description, search_text, tags)
    VALUES (new.rowid, new.name, new.artifact_type, new.title, new.description, new.search_text, new.search_tags);
END;
```

**FTS5 Query**:
```python
def search_fts(session: Session, query: str, limit: int = 50):
    sql = text("""
        SELECT
            ce.*,
            ms.owner,
            ms.repo_name,
            fts.rank AS relevance,
            snippet(catalog_fts, 2, '<mark>', '</mark>', '...', 32) AS snippet
        FROM marketplace_catalog_entries ce
        JOIN marketplace_sources ms ON ce.source_id = ms.id
        JOIN catalog_fts fts ON ce.rowid = fts.rowid
        WHERE fts MATCH :query
        ORDER BY fts.rank
        LIMIT :limit
    """)
    return session.execute(sql, {"query": query, "limit": limit})
```

### Phase 3: Frontend UI

#### Dual-Mode Toggle

```tsx
<ToggleGroup type="single" value={searchMode} onValueChange={setSearchMode}>
  <ToggleGroupItem value="sources" aria-label="Search sources">
    <Building2 className="mr-2 h-4 w-4" />
    Sources
  </ToggleGroupItem>
  <ToggleGroupItem value="artifacts" aria-label="Search artifacts">
    <Package className="mr-2 h-4 w-4" />
    Artifacts
  </ToggleGroupItem>
</ToggleGroup>
```

#### React Query Hook

```typescript
export function useArtifactSearch(params: ArtifactSearchParams) {
  return useQuery({
    queryKey: ['marketplace', 'artifacts', 'search', params],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (params.query) searchParams.set('q', params.query);
      if (params.type) searchParams.set('type', params.type);
      if (params.minConfidence) searchParams.set('min_confidence', String(params.minConfidence));

      return apiRequest<ArtifactSearchResponse>(
        `/marketplace/catalog/search?${searchParams.toString()}`
      );
    },
    enabled: params.query.length >= 2,
    keepPreviousData: true,
    staleTime: 30_000,
  });
}
```

#### Result Display

Results grouped by source using shadcn Accordion:

```tsx
<Accordion type="multiple" defaultValue={[firstSourceId]}>
  {groupedResults.map(({ source, artifacts }) => (
    <AccordionItem key={source.id} value={source.id}>
      <AccordionTrigger>
        <div className="flex items-center gap-3">
          <GitBranch className="h-4 w-4" />
          <span>{source.owner}/{source.repo_name}</span>
          <Badge variant="secondary">{artifacts.length} results</Badge>
        </div>
      </AccordionTrigger>
      <AccordionContent>
        <div className="grid gap-4 pt-4">
          {artifacts.map(artifact => (
            <ArtifactCard key={artifact.id} artifact={artifact} source={source} />
          ))}
        </div>
      </AccordionContent>
    </AccordionItem>
  ))}
</Accordion>
```

---

## Performance Analysis

### Query Performance Benchmarks (Estimated)

| Query Type | 5K entries | 50K entries | 500K entries |
|------------|------------|-------------|--------------|
| LIKE prefix search | <5ms | <20ms | 100-200ms |
| FTS5 MATCH | <2ms | <10ms | <50ms |
| Type + Confidence filter | <3ms | <15ms | <75ms |
| Complex JOIN + filter | <10ms | <50ms | 200-500ms |

### Storage Overhead

| Scale | Entries | Schema Extension | + FTS5 Index |
|-------|---------|------------------|--------------|
| Small | 5K | 4 MB | 6 MB |
| Medium | 50K | 42 MB | 63 MB |
| Large | 500K | 420 MB | 630 MB |

**Target scale**: 1000 sources * 50 artifacts = 50K entries (Medium)

### GitHub API Impact

**Zero additional API calls** - frontmatter extracted during existing scan process.

| Operation | Current API Calls | With Search | Savings |
|-----------|-------------------|-------------|---------|
| Source scan | ~50-100/source | ~50-100/source | 0% |
| Search query | 0 | 0 | N/A |
| Rescan | Same | Same | 0% |

---

## Implementation Plan

### Phase 0: Configurable Frontmatter Indexing (✅ COMPLETE)

**Status**: Implementation complete as of January 2026

The configurable indexing foundation has been implemented to support flexible artifact indexing across sources. This phase provides the infrastructure that Phase 1+ depends on:

**Features Implemented**:
- Global indexing mode configuration (`artifact_search.indexing_mode`) - controls how frontmatter is extracted
- Per-source `indexing_enabled` override flag - allows fine-grained control per data source
- UI toggles in add/edit source modals - enables users to control indexing behavior
- API endpoint for frontend mode detection - allows frontend to adapt based on configuration

**Why This Matters for Phase 1+**:
- Provides the groundwork for extracting and persisting frontmatter
- Supports hybrid indexing strategies (some sources indexed, others not)
- Allows users to control compute/storage trade-offs per source
- Sets up infrastructure for future search enhancements

**Related Documents**:
- [Configurable Frontmatter Caching PRD](/docs/project_plans/PRDs/enhancements/configurable-frontmatter-caching-v1.md)
- [Implementation Plan](/docs/project_plans/implementation_plans/enhancements/configurable-frontmatter-caching-v1.md)

---

### Phase 1: Foundation (Est. 3 days)

1. **Database migration** - Add search columns to `MarketplaceCatalogEntry`
2. **Modify heuristic detector** - Extract and persist frontmatter during scan
3. **Repository method** - Implement `search()` with LIKE queries
4. **API endpoint** - Create `/marketplace/catalog/search`
5. **Backfill script** - Populate search fields for existing entries

### Phase 2: FTS5 Enhancement (Est. 2 days)

*Trigger: Search latency >100ms or advanced search features requested*

1. **Migration** - Create FTS5 virtual table and sync triggers
2. **Repository method** - Add FTS5 search path with MATCH queries
3. **Snippet generation** - Add result highlighting support
4. **Rebuild endpoint** - Admin endpoint to rebuild FTS index

### Phase 3: Frontend UI (Est. 2 days)

1. **Toggle component** - Dual-mode search switcher
2. **Search hook** - React Query hook for artifact search
3. **Result cards** - Artifact card with source context
4. **Grouped display** - Accordion-based grouping by source
5. **Filter integration** - Mode-aware filter toolbar

---

## Open Questions

1. **Search depth**: Should content indexing include README/SKILL.md body text, or just frontmatter metadata?
   - **Recommendation**: Start with frontmatter only; expand if users request body search

2. **Confidence threshold**: Should low-confidence artifacts appear in cross-source search?
   - **Recommendation**: Default min_confidence=50, allow override via filter

3. **Trust level inheritance**: Should source trust_level affect artifact search ranking?
   - **Recommendation**: Include trust_level in response; let frontend sort/filter

4. **Search history**: Should we track popular searches for suggestions?
   - **Recommendation**: Defer to Phase 4 if usage warrants

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| FTS5 not available in SQLite build | Low | High | Feature-detect at startup; fall back to LIKE queries |
| Large sources overwhelm search | Medium | Medium | Default confidence threshold; pagination |
| Frontmatter inconsistent across sources | High | Low | Graceful handling of missing fields |
| Search performance degrades at scale | Low | Medium | FTS5 Phase 2 provides 5-10x improvement |
| Index size exceeds expectations | Low | Low | Monitor; implement pruning for old/low-quality entries |

---

## Related Work

- **REQ-20260103**: Marketplace Source Filter/Sort/Search Bar (DONE) - Established filter toolbar patterns
- **REQ-20260104**: Marketplace Source Detection Improvements (DONE) - SHA256-based deduplication
- **REQ-20260109**: Project Discovery & Import Issues (MIXED) - Duplicate detection workflow

---

## ADR Recommendations

If implementing, create ADRs for:

1. **ADR: SQLite FTS5 vs External Search Service**
   - Decision: Use SQLite FTS5 for simplicity and single-database architecture
   - Alternative considered: Elasticsearch, MeiliSearch
   - Rationale: Scale (50K entries) doesn't warrant external service complexity

2. **ADR: Frontmatter Extraction Timing**
   - Decision: Extract during scan, not lazily on search
   - Alternative considered: Lazy extraction on first search
   - Rationale: Consistent search results; no latency spike on first search

---

## Conclusion

Cross-source artifact search is **highly feasible** with the recommended phased approach. The implementation:

- **Reuses existing infrastructure** (SQLite, SQLAlchemy, React Query)
- **Has zero GitHub API impact** (frontmatter already available during scan)
- **Provides acceptable performance** (<50ms at 50K scale with Phase 1; <10ms with Phase 2)
- **Follows SkillMeat architecture patterns** (repository → service → router)

**Recommended next step**: Create PRD and implementation plan for Phase 1 delivery.
