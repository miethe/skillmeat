---
title: 'Implementation Plan: Cross-Source Artifact Search'
description: Phased implementation of cross-source artifact search with FTS5 and dual-mode
  frontend
audience:
- ai-agents
- developers
tags:
- implementation
- planning
- marketplace
- search
- fts5
created: 2026-01-23
updated: '2026-02-07'
category: product-planning
status: completed
related:
- /docs/project_plans/PRDs/features/cross-source-artifact-search-v1.md
- /docs/project_plans/SPIKEs/cross-source-artifact-search-spike.md
schema_version: 2
doc_type: implementation_plan
feature_slug: cross-source-artifact-search
prd_ref: null
---

# Implementation Plan: Cross-Source Artifact Search

**Plan ID**: `IMPL-2026-01-23-cross-source-artifact-search`
**Date**: 2026-01-23
**Author**: Claude Opus 4.5
**Related Documents**:
- **PRD**: `/docs/project_plans/PRDs/features/cross-source-artifact-search-v1.md`
- **SPIKE**: `/docs/project_plans/SPIKEs/cross-source-artifact-search-spike.md`
- **Phase 0 PRD**: `/docs/project_plans/PRDs/enhancements/configurable-frontmatter-caching-v1.md` (COMPLETE)

**Complexity**: Medium
**Total Estimated Effort**: 31 story points
**Target Timeline**: 7 days

## Executive Summary

This plan implements cross-source artifact search in three phases: (1) database schema + basic LIKE search, (2) FTS5 full-text search enhancement, (3) frontend dual-mode toggle. Phase 0 (configurable indexing) is complete.

**Key Milestones:**
1. Day 1-3: Database migration, frontmatter extraction, basic search API
2. Day 4-5: FTS5 virtual table, advanced search features
3. Day 6-7: Frontend toggle, grouped results, graceful degradation

## Implementation Strategy

### Architecture Sequence

Following SkillMeat layered architecture:
1. **Database Layer** - Add columns, indexes, FTS5 table
2. **Detection Layer** - Modify heuristic detector for frontmatter extraction
3. **Repository Layer** - Search methods with LIKE and FTS5 paths
4. **API Layer** - `/marketplace/catalog/search` endpoint
5. **UI Layer** - Toggle, search hook, results display
6. **Testing Layer** - Unit, integration, component tests
7. **Documentation Layer** - API docs, backfill script docs

### Parallel Work Opportunities

- **Phase 1 & 3 Design**: Frontend design can start during Phase 1 backend work
- **FTS5 Research**: FTS5 implementation can be researched while Phase 1 runs
- **Backfill Script**: Can be developed in parallel with API endpoint

### Critical Path

```
Migration → Frontmatter Extraction → Repository Search → API Endpoint
                                                              ↓
                                                    Frontend Integration
```

## Phase Breakdown

> **Progress Tracking**: Each phase has a dedicated progress file in `.claude/progress/cross-source-artifact-search-v1/`

| Phase | Title | Duration | Progress File |
|-------|-------|----------|---------------|
| 1 | Database + Basic Search | 3 days | [phase-1-progress.md](/.claude/progress/cross-source-artifact-search-v1/phase-1-progress.md) |
| 2 | FTS5 Enhancement | 2 days | [phase-2-progress.md](/.claude/progress/cross-source-artifact-search-v1/phase-2-progress.md) |
| 3 | Frontend UI | 2 days | [phase-3-progress.md](/.claude/progress/cross-source-artifact-search-v1/phase-3-progress.md) |

---

### Phase 1: Database + Basic Search (Est. 3 days)

**Duration**: 3 days
**Dependencies**: Phase 0 complete (DONE)
**Primary Subagent(s)**: data-layer-expert, python-backend-engineer
**Progress**: [phase-1-progress.md](/.claude/progress/cross-source-artifact-search-v1/phase-1-progress.md)

#### Database Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Est | Subagent(s) | Deps |
|---------|-----------|-------------|---------------------|-----|-------------|------|
| DB-001 | Schema Migration | Add title, description, search_tags, search_text columns to MarketplaceCatalogEntry | Migration runs, 4 nullable columns created | 2 pts | data-layer-expert | None |
| DB-002 | Search Indexes | Create indexes for search performance | Indexes on (artifact_type, status), confidence_score, name | 1 pt | data-layer-expert | DB-001 |

**Key Files:**
- `skillmeat/cache/models.py` - Add columns to MarketplaceCatalogEntry
- `skillmeat/api/alembic/versions/` - New migration file

**Migration SQL Template:**
```python
def upgrade():
    op.add_column('marketplace_catalog_entries',
        sa.Column('title', sa.String(200), nullable=True))
    op.add_column('marketplace_catalog_entries',
        sa.Column('description', sa.Text, nullable=True))
    op.add_column('marketplace_catalog_entries',
        sa.Column('search_tags', sa.Text, nullable=True))
    op.add_column('marketplace_catalog_entries',
        sa.Column('search_text', sa.Text, nullable=True))

    op.create_index('idx_catalog_search_name',
        'marketplace_catalog_entries', ['name'])
    op.create_index('idx_catalog_search_type_status',
        'marketplace_catalog_entries', ['artifact_type', 'status'])
    op.create_index('idx_catalog_search_confidence',
        'marketplace_catalog_entries', ['confidence_score'])
```

#### Detection Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Est | Subagent(s) | Deps |
|---------|-----------|-------------|---------------------|-----|-------------|------|
| DET-001 | Frontmatter Extraction | Modify heuristic detector to extract frontmatter during scan | title/description/tags populated when indexing_enabled | 3 pts | python-backend-engineer | DB-001 |
| DET-002 | Conditional Extraction | Check source.indexing_enabled before storing | Only indexed sources have search fields populated | 1 pt | python-backend-engineer | DET-001 |

**Key Files:**
- `skillmeat/marketplace/detection/heuristic_detector.py` - Add extraction logic
- `skillmeat/utils/frontmatter.py` - Use existing `parse_markdown_with_frontmatter()`

**Extraction Logic:**
```python
# In heuristic_detector.py during artifact detection
if source.indexing_enabled and artifact_type == "skill":
    if "SKILL.md" in file_tree:
        content = github_client.get_file_content(repo, path + "/SKILL.md")
        frontmatter = parse_markdown_with_frontmatter(content)

        entry.title = frontmatter.get("title") or frontmatter.get("name")
        entry.description = frontmatter.get("description")
        entry.search_tags = json.dumps(
            frontmatter.get("tags", []) + extract_path_tags(path)
        )
        entry.search_text = f"{name} {entry.title or ''} {entry.description or ''}"
```

#### Repository Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Est | Subagent(s) | Deps |
|---------|-----------|-------------|---------------------|-----|-------------|------|
| REPO-001 | Search Method | Create repository search method with LIKE queries | Returns matching entries with source context | 3 pts | python-backend-engineer | DET-002 |
| REPO-002 | Pagination | Add cursor pagination to search results | Consistent with existing pagination patterns | 1 pt | python-backend-engineer | REPO-001 |

**Key Files:**
- `skillmeat/cache/repositories/marketplace_catalog_repository.py` - Add search method

**Repository Method:**
```python
def search(
    self,
    query: Optional[str] = None,
    artifact_type: Optional[str] = None,
    source_ids: Optional[List[str]] = None,
    min_confidence: int = 0,
    tags: Optional[List[str]] = None,
    limit: int = 50,
    cursor: Optional[str] = None,
) -> Tuple[List[MarketplaceCatalogEntry], PageInfo]:
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

    stmt = (
        select(MarketplaceCatalogEntry)
        .join(MarketplaceSource)
        .where(and_(*filters))
        .order_by(MarketplaceCatalogEntry.confidence_score.desc())
    )

    return self._paginate(stmt, limit, cursor)
```

#### API Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Est | Subagent(s) | Deps |
|---------|-----------|-------------|---------------------|-----|-------------|------|
| API-001 | Search Endpoint | Create /marketplace/catalog/search endpoint | Returns filtered, paginated results | 2 pts | python-backend-engineer | REPO-002 |
| API-002 | Response Schema | Create CatalogSearchResponse schema | Includes items, page_info, source context | 1 pt | python-backend-engineer | API-001 |

**Key Files:**
- `skillmeat/api/routers/marketplace_catalog.py` - New router or extend existing
- `skillmeat/api/schemas/marketplace.py` - Add CatalogSearchRequest/Response

**API Endpoint:**
```python
@router.get("/catalog/search", response_model=CatalogSearchResponse)
async def search_catalog(
    q: Optional[str] = Query(None, description="Search query"),
    type: Optional[str] = Query(None, description="Artifact type filter"),
    source_id: Optional[str] = Query(None, description="Limit to source"),
    min_confidence: int = Query(0, ge=0, le=100),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    limit: int = Query(50, ge=1, le=200),
    cursor: Optional[str] = Query(None),
    session: Session = Depends(get_db_session),
) -> CatalogSearchResponse:
    """Search artifacts across all marketplace sources."""
    repo = MarketplaceCatalogRepository(session)

    tag_list = tags.split(",") if tags else None
    entries, page_info = repo.search(
        query=q,
        artifact_type=type,
        min_confidence=min_confidence,
        tags=tag_list,
        limit=limit,
        cursor=cursor,
    )

    return CatalogSearchResponse(
        items=[entry_to_dto(e) for e in entries],
        page_info=page_info,
    )
```

#### Backfill Task

| Task ID | Task Name | Description | Acceptance Criteria | Est | Subagent(s) | Deps |
|---------|-----------|-------------|---------------------|-----|-------------|------|
| BF-001 | Backfill Script | Create script to populate search fields for existing entries | Script runs, existing entries updated | 2 pts | python-backend-engineer | API-002 |

**Key Files:**
- `scripts/backfill_catalog_search.py` - One-time migration script

**Phase 1 Quality Gates:**
- [ ] Migration runs successfully on existing database
- [ ] Frontmatter extracted for indexed sources during scan
- [ ] Search API returns matching entries
- [ ] Response time <100ms at current scale
- [ ] Backfill script successfully populates existing entries

---

### Phase 2: FTS5 Enhancement (Est. 2 days)

**Duration**: 2 days
**Dependencies**: Phase 1 complete
**Primary Subagent(s)**: data-layer-expert, python-backend-engineer
**Progress**: [phase-2-progress.md](/.claude/progress/cross-source-artifact-search-v1/phase-2-progress.md)

| Task ID | Task Name | Description | Acceptance Criteria | Est | Subagent(s) | Deps |
|---------|-----------|-------------|---------------------|-----|-------------|------|
| FTS-001 | FTS5 Migration | Create FTS5 virtual table with sync triggers | Virtual table exists, triggers sync data | 2 pts | data-layer-expert | API-002 |
| FTS-002 | Feature Detection | Detect FTS5 availability at startup | Fallback flag set correctly | 1 pt | python-backend-engineer | FTS-001 |
| FTS-003 | FTS5 Search Path | Add FTS5 MATCH query to repository | <10ms queries, relevance ranking | 2 pts | python-backend-engineer | FTS-002 |
| FTS-004 | Snippet Generation | Add snippet() for result highlighting | Snippets returned in search results | 1 pt | python-backend-engineer | FTS-003 |

**Key Files:**
- `skillmeat/api/alembic/versions/` - FTS5 migration
- `skillmeat/cache/repositories/marketplace_catalog_repository.py` - FTS5 search path
- `skillmeat/api/utils/fts5.py` - Feature detection utilities

**FTS5 Virtual Table:**
```sql
CREATE VIRTUAL TABLE IF NOT EXISTS catalog_fts USING fts5(
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

**FTS5 Search Query:**
```python
def search_fts(
    self,
    query: str,
    artifact_type: Optional[str] = None,
    limit: int = 50,
) -> List[Dict]:
    """FTS5 full-text search with relevance ranking."""
    sql = text("""
        SELECT
            ce.*,
            ms.owner,
            ms.repo_name,
            ms.id as source_id,
            fts.rank AS relevance,
            snippet(catalog_fts, 2, '<mark>', '</mark>', '...', 32) AS snippet
        FROM marketplace_catalog_entries ce
        JOIN marketplace_sources ms ON ce.source_id = ms.id
        JOIN catalog_fts fts ON ce.rowid = fts.rowid
        WHERE fts MATCH :query
        AND ce.status NOT IN ('excluded', 'removed')
        ORDER BY fts.rank
        LIMIT :limit
    """)
    return self.session.execute(sql, {"query": query, "limit": limit}).fetchall()
```

**Phase 2 Quality Gates:**
- [ ] FTS5 virtual table created
- [ ] Sync triggers work on INSERT/UPDATE/DELETE
- [ ] Feature detection correctly identifies FTS5 availability
- [ ] FTS5 queries return <10ms at 50K scale
- [ ] Snippet highlights match terms correctly
- [ ] Fallback to LIKE works when FTS5 unavailable

---

### Phase 3: Frontend UI (Est. 2 days)

**Duration**: 2 days
**Dependencies**: Phase 2 complete (can start design earlier)
**Primary Subagent(s)**: ui-engineer-enhanced, frontend-developer
**Progress**: [phase-3-progress.md](/.claude/progress/cross-source-artifact-search-v1/phase-3-progress.md)

| Task ID | Task Name | Description | Acceptance Criteria | Est | Subagent(s) | Deps |
|---------|-----------|-------------|---------------------|-----|-------------|------|
| UI-001 | Mode Toggle | Create dual-mode toggle (sources/artifacts) | Toggle switches modes, state in URL | 2 pts | ui-engineer-enhanced | FTS-004 |
| UI-002 | Search Hook | Create React Query hook for artifact search | Hook fetches, caches, handles errors | 2 pts | frontend-developer | UI-001 |
| UI-003 | Results Display | Grouped accordion results component | Results grouped by source, navigable | 2 pts | ui-engineer-enhanced | UI-002 |
| UI-004 | Loading States | Loading skeletons and error handling | Smooth loading UX, clear errors | 1 pt | frontend-developer | UI-003 |
| UI-005 | Graceful Degradation | Handle indexing disabled state | Message shown when indexing off | 1 pt | ui-engineer-enhanced | UI-004 |

**Key Files:**
- `skillmeat/web/app/marketplace/sources/page.tsx` - Update with toggle
- `skillmeat/web/components/marketplace/search-mode-toggle.tsx` - New component
- `skillmeat/web/components/marketplace/artifact-search-results.tsx` - New component
- `skillmeat/web/hooks/use-artifact-search.ts` - New hook

**Mode Toggle Component:**
```tsx
'use client';

import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { Building2, Package } from 'lucide-react';

interface SearchModeToggleProps {
  mode: 'sources' | 'artifacts';
  onModeChange: (mode: 'sources' | 'artifacts') => void;
  disabled?: boolean;
}

export function SearchModeToggle({ mode, onModeChange, disabled }: SearchModeToggleProps) {
  return (
    <ToggleGroup
      type="single"
      value={mode}
      onValueChange={(v) => v && onModeChange(v as 'sources' | 'artifacts')}
      disabled={disabled}
    >
      <ToggleGroupItem value="sources" aria-label="Search sources">
        <Building2 className="mr-2 h-4 w-4" />
        Sources
      </ToggleGroupItem>
      <ToggleGroupItem value="artifacts" aria-label="Search artifacts">
        <Package className="mr-2 h-4 w-4" />
        Artifacts
      </ToggleGroupItem>
    </ToggleGroup>
  );
}
```

**React Query Hook:**
```typescript
import { useQuery } from '@tanstack/react-query';
import { apiRequest } from '@/lib/api';

export interface ArtifactSearchParams {
  query: string;
  type?: string;
  minConfidence?: number;
  tags?: string[];
  limit?: number;
}

export function useArtifactSearch(params: ArtifactSearchParams, enabled = true) {
  return useQuery({
    queryKey: ['marketplace', 'artifacts', 'search', params],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (params.query) searchParams.set('q', params.query);
      if (params.type) searchParams.set('type', params.type);
      if (params.minConfidence) searchParams.set('min_confidence', String(params.minConfidence));
      if (params.tags?.length) searchParams.set('tags', params.tags.join(','));
      if (params.limit) searchParams.set('limit', String(params.limit));

      return apiRequest<ArtifactSearchResponse>(
        `/marketplace/catalog/search?${searchParams.toString()}`
      );
    },
    enabled: enabled && params.query.length >= 2,
    staleTime: 30_000,
  });
}
```

**Grouped Results Component:**
```tsx
'use client';

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Badge } from '@/components/ui/badge';
import { GitBranch } from 'lucide-react';

interface GroupedResultsProps {
  results: ArtifactSearchResult[];
}

export function ArtifactSearchResults({ results }: GroupedResultsProps) {
  // Group results by source
  const grouped = results.reduce((acc, result) => {
    const sourceKey = result.source.id;
    if (!acc[sourceKey]) {
      acc[sourceKey] = { source: result.source, artifacts: [] };
    }
    acc[sourceKey].artifacts.push(result);
    return acc;
  }, {} as Record<string, { source: Source; artifacts: ArtifactSearchResult[] }>);

  const groups = Object.values(grouped);
  const firstSourceId = groups[0]?.source.id;

  return (
    <Accordion type="multiple" defaultValue={firstSourceId ? [firstSourceId] : []}>
      {groups.map(({ source, artifacts }) => (
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
  );
}
```

**Phase 3 Quality Gates:**
- [ ] Toggle switches between sources and artifacts modes
- [ ] Mode persisted in URL query param (?mode=artifacts)
- [ ] Search debounced (wait 300ms before query)
- [ ] Results grouped by source in accordion
- [ ] Click navigates to artifact detail
- [ ] Loading skeleton during fetch
- [ ] "No results" message for empty results
- [ ] "Indexing disabled" message when applicable
- [ ] Accessibility: keyboard navigation, ARIA labels

---

## Testing Strategy

### Unit Tests

| Test Area | Description | Subagent |
|-----------|-------------|----------|
| Frontmatter extraction | Parse various frontmatter formats | python-backend-engineer |
| Repository search | LIKE and FTS5 query paths | python-backend-engineer |
| API endpoint | Request validation, response format | python-backend-engineer |
| Feature detection | FTS5 availability check | python-backend-engineer |

### Integration Tests

| Test Area | Description | Subagent |
|-----------|-------------|----------|
| Full search flow | Query → Repository → Response | python-backend-engineer |
| Pagination | Cursor-based pagination works | python-backend-engineer |
| Filters | Type, confidence, tags filtering | python-backend-engineer |
| Backfill script | Updates existing entries | python-backend-engineer |

### Component Tests

| Test Area | Description | Subagent |
|-----------|-------------|----------|
| SearchModeToggle | Toggle state, accessibility | frontend-developer |
| ArtifactSearchResults | Grouping, accordion behavior | frontend-developer |
| useArtifactSearch hook | Query, caching, error states | frontend-developer |

### E2E Tests

| Test Area | Description | Subagent |
|-----------|-------------|----------|
| Full workflow | Toggle → Search → Results → Navigate | frontend-developer |
| Indexing disabled | Shows message, sources mode works | frontend-developer |

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| FTS5 not available | High | Low | Feature detection with LIKE fallback |
| Large result sets slow | Medium | Medium | Pagination, confidence threshold |
| Frontmatter parsing fails | Low | Medium | Lenient parsing, empty defaults |

### Schedule Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Phase 1 delays Phase 3 | Medium | Low | Start UI design in parallel |
| Backfill takes too long | Low | Medium | Run in batches, background job |

---

## Resource Requirements

### Team Composition
- **Backend Developer**: Full-time (Phase 1-2), part-time (Phase 3)
- **Frontend Developer**: Part-time (Phase 1-2), full-time (Phase 3)

### Skill Requirements
- Python, FastAPI, SQLAlchemy, SQLite FTS5
- TypeScript, React, React Query, Next.js
- Alembic migrations

---

## Success Metrics

### Delivery Metrics
- On-time delivery (±1 day)
- Test coverage >80%
- Search latency <100ms (LIKE) / <10ms (FTS5)

### Business Metrics
- Users can find artifacts cross-source
- 40%+ users try artifact search mode
- Search completion rate >80%

### Technical Metrics
- 95% frontmatter extraction rate
- 99% uptime for search endpoint
- <1% error rate

---

**Progress Tracking:**

| Phase | File | Status |
|-------|------|--------|
| Phase 1 | [phase-1-progress.md](/.claude/progress/cross-source-artifact-search-v1/phase-1-progress.md) | Pending |
| Phase 2 | [phase-2-progress.md](/.claude/progress/cross-source-artifact-search-v1/phase-2-progress.md) | Pending |
| Phase 3 | [phase-3-progress.md](/.claude/progress/cross-source-artifact-search-v1/phase-3-progress.md) | Pending |

Directory: `.claude/progress/cross-source-artifact-search-v1/`

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-01-23
