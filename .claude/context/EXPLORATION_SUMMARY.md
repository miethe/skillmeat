# Marketplace Models Exploration Summary

**Date**: 2026-01-23
**Status**: ✅ Complete
**Findings**: Clear schema gaps identified for cross-source artifact search

---

## Executive Summary

The marketplace infrastructure has strong **detection and storage** capabilities but **lacks searchable columns** needed for cross-source artifact search. The configuration infrastructure for search indexing was added (commit b1d55253), but the database schema and search methods are not yet implemented.

**Key Gap**: MarketplaceCatalogEntry stores artifacts but cannot be searched by title, description, or keywords.

---

## Current State Analysis

### What Exists ✅

| Component | Status | Details |
|-----------|--------|---------|
| MarketplaceCatalogEntry Model | ✅ Complete | 15 columns covering detection, import tracking, quality metrics |
| Frontmatter Parser | ✅ Ready | `parse_markdown_with_frontmatter()` extracts YAML metadata |
| GitHub Scanner | ✅ Working | Detects artifacts, calculates confidence scores |
| Indexing Configuration | ✅ Added | `indexing_enabled` (tri-state) + global `indexing_mode` |
| Repository Base Classes | ✅ Available | CRUD methods, filtering, bulk operations |
| API Router Patterns | ✅ Established | Listing, filtering, nested resource patterns |
| Path-Based Tags | ✅ Functional | `path_segments` JSON column with approval status |

### What's Missing ❌

| Component | Impact | Priority |
|-----------|--------|----------|
| **title** column | Cannot display proper artifact titles | CRITICAL |
| **description** column | Cannot show artifact descriptions in search | CRITICAL |
| **search_tags** column | Cannot filter by tags across sources | HIGH |
| **search_text** column | Cannot do full-text search efficiently | HIGH |
| Search repository methods | Cannot query across entries | CRITICAL |
| Search API endpoint | No cross-source search exposed to frontend | CRITICAL |
| Frontend search UI | No way for users to search | CRITICAL |

---

## Column Recommendations

### Add 4 Columns to MarketplaceCatalogEntry

```sql
-- Required for search
ADD COLUMN title VARCHAR(255) NULL          -- Artifact display title
ADD COLUMN description TEXT NULL             -- Short description for UI
ADD COLUMN search_tags TEXT NULL             -- JSON array: ["tag1", "tag2"]
ADD COLUMN search_text TEXT NULL             -- Denormalized for FTS queries

-- Recommended (optional)
ADD COLUMN frontmatter_json TEXT NULL        -- Full parsed frontmatter reference
```

### New Indexes

```sql
CREATE INDEX idx_catalog_search_text ON marketplace_catalog_entries(search_text)
CREATE INDEX idx_catalog_title ON marketplace_catalog_entries(title)
CREATE INDEX idx_catalog_search_tags ON marketplace_catalog_entries(search_tags)
CREATE INDEX idx_catalog_source_status_type ON marketplace_catalog_entries(source_id, status, artifact_type)
```

---

## Three-Layer Implementation Path

### 1. DATABASE LAYER (Alembic Migration)
- Add 4 searchable columns (title, description, search_tags, search_text)
- Add 3 new indexes
- Backfill existing entries with extracted frontmatter

### 2. SCANNING LAYER (GitHub Scanner)
- During artifact detection, read primary markdown file
- Parse frontmatter with existing `parse_markdown_with_frontmatter()`
- Extract and store: title, description, tags
- Build denormalized search_text
- Respect `get_effective_indexing_state(source)` to decide whether to index

### 3. QUERY LAYER (Repository + API)
- Add search methods to MarketplaceCatalogRepository
- Create API endpoint: `GET /api/v1/marketplace/artifacts/search`
- Support filtering: query, sources, type, tags, confidence, limit, cursor

---

## Existing Infrastructure Ready to Use

### Frontmatter Parsing
```python
from skillmeat.core.parsers import parse_markdown_with_frontmatter

result = parse_markdown_with_frontmatter(markdown_content)
if result.frontmatter:
    title = result.frontmatter.get('title')
    description = result.frontmatter.get('description')
    tags = result.frontmatter.get('tags', [])
```

### Configuration System
```python
from skillmeat.config import get_indexing_mode, get_effective_indexing_state

mode = get_indexing_mode()  # "off", "on", "opt_in"
should_index = get_effective_indexing_state(source)  # Considers mode + per-source
```

### Repository Patterns
```python
class MarketplaceCatalogRepository(BaseRepository[MarketplaceCatalogEntry]):
    def list_by_source(self, source_id) -> List[MarketplaceCatalogEntry]
    def list_by_status(self, status) -> List[MarketplaceCatalogEntry]
    # Add search methods following same pattern
```

### API Patterns
- Cursor-based pagination (similar to marketplace.py:165-307)
- Query parameter filtering
- Structured error responses with HTTPException

---

## Risk Assessment

### Low Risk ✅
- Adding nullable columns (backward compatible)
- New indexes (non-blocking)
- New repository methods (additive)

### Moderate Risk ⚠️
- Migration backfill (need to extract frontmatter from files)
- Indexing control logic (need to respect configuration)

### Mitigation
- Backfill can be async/lazy (frontmatter extracted on-demand)
- Alembic migration includes rollback
- Feature flags via indexing_mode prevent search if disabled

---

## Files Changed Summary

| File | Type | Change |
|------|------|--------|
| `skillmeat/cache/models.py` | Model | Add 4 columns to MarketplaceCatalogEntry |
| `skillmeat/cache/migrations/versions/*.py` | Migration | Alembic: add columns, indexes, backfill |
| `skillmeat/cache/repositories.py` | Repository | Add search methods to MarketplaceCatalogRepository |
| `skillmeat/api/routers/marketplace_sources.py` | Router | Add search endpoint |
| `skillmeat/api/schemas/marketplace.py` | Schema | Add search request/response models |
| `skillmeat/core/marketplace/github_scanner.py` | Scanner | Extract and store frontmatter |
| `skillmeat/web/app/marketplace/search` | Frontend | New search page + components |

---

## Quick Reference

### MarketplaceCatalogEntry Column Status
| Column | Type | Nullable | Indexed | Search? | Status |
|--------|------|----------|---------|---------|--------|
| id | String | NO | PK | ❌ | ✅ Exists |
| source_id | String | NO | FK | ❌ | ✅ Exists |
| name | String | NO | YES | ⚠️ Limited | ✅ Exists |
| artifact_type | String | NO | YES | ✅ | ✅ Exists |
| confidence_score | Integer | NO | NO | ✅ | ✅ Exists |
| status | String | NO | YES | ✅ | ✅ Exists |
| **title** | String | YES | ? | ✅ | ❌ **MISSING** |
| **description** | Text | YES | ? | ✅ | ❌ **MISSING** |
| **search_tags** | Text | YES | YES | ✅ | ❌ **MISSING** |
| **search_text** | Text | YES | YES | ✅ | ❌ **MISSING** |

---

## Next Steps

1. **Review** - User approves schema changes
2. **Design** - Finalize migration strategy (backfill approach)
3. **Implement** - Create migration + code changes
4. **Test** - Unit + integration + E2E tests
5. **Deploy** - Roll out with feature flag

---

## Key Insights

### Pattern: Denormalized Search Text
The `search_text` column concatenates name + title + description + tags for efficient full-text queries. This is a common optimization pattern and worth the storage overhead.

### Pattern: Tri-State Configuration
`indexing_enabled` on MarketplaceSource combined with global `indexing_mode` allows:
- Global disable (opt-out)
- Global enable (opt-in per-source)
- Per-source override (fine-grained control)

### Pattern: Frontmatter Extraction During Scanning
Rather than extracting frontmatter on-demand, store it during scanning:
- Improves search performance
- Reduces GitHub API calls (already fetching markdown)
- Enables configuration-based indexing control

---

## Completion Status

**Exploration**: 100% Complete ✅
- Schema analyzed
- Gaps identified
- Configuration reviewed
- Patterns documented
- Implementation path defined

**Ready for**: Implementation Phase ✅
