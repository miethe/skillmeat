---
feature: Search Results Ranking Enhancement
status: completed
created: 2026-01-27
completed: 2026-01-27
related_prd: cross-source-artifact-search-v1
scope: 1 file
estimated_effort: single-session
schema_version: 2
doc_type: quick_feature
feature_slug: search-ranking-enhancement
---

# Search Results Ranking Enhancement

## Overview

Enhance artifact search results on `/marketplace/sources` by implementing field-weighted ranking. Results will be ranked based on WHERE the search term was found (name/title > description > tags > deep content).

## Technical Approach

### Current State

- FTS5 full-text search indexes: name (unindexed), title, description, search_text, search_tags, deep_search_text
- Ranking: Only uses `confidence_score` (artifact detection quality)
- `fts.rank` is selected but ignored in ORDER BY

### Solution: FTS5 bm25() Column Weights

FTS5's `bm25()` function supports per-column weights. Higher weights = higher ranking for matches in that column.

```sql
-- Column order in FTS5 table:
-- 0: name (UNINDEXED - no weight)
-- 1: artifact_type (UNINDEXED - no weight)
-- 2: title (high priority - 10.0)
-- 3: description (medium priority - 5.0)
-- 4: search_text (low priority - 2.0)
-- 5: search_tags (medium priority - 3.0)
-- 6: deep_search_text (lowest priority - 1.0)

bm25(catalog_fts, 0, 0, 10.0, 5.0, 2.0, 3.0, 1.0)
```

### Ranking Strategy

| Priority | Field | Weight | Rationale |
|----------|-------|--------|-----------|
| 1 | title | 10.0 | User expects name matches first |
| 2 | description | 5.0 | Clear artifact summary |
| 3 | search_tags | 3.0 | Explicit categorization |
| 4 | search_text | 2.0 | Concatenated metadata |
| 5 | deep_search_text | 1.0 | File content matches |

### Future Extensibility

Weights stored as constants for easy adjustment:
- Future "Advanced Search" can expose weight toggles
- Users could boost/demote specific field priorities
- A/B testing different weight configurations

## Implementation Tasks

### TASK-1: Add bm25 weighted ranking to FTS5 search

**File**: `skillmeat/cache/repositories.py`
**Change**:
- Replace `fts.rank` with `bm25(catalog_fts, 0, 0, 10.0, 5.0, 2.0, 3.0, 1.0) AS relevance`
- Change ORDER BY to: `relevance ASC, confidence_score DESC, id ASC`
  (bm25 returns negative values; closer to 0 = better match)

### TASK-2: Define ranking weights as constants

**File**: `skillmeat/cache/repositories.py` (top of file or in a constants section)
**Change**: Add constants for weights to enable future configurability:
```python
# FTS5 bm25 column weights for search ranking
# Column indices: 0=name(unindexed), 1=type(unindexed), 2=title, 3=description, 4=search_text, 5=tags, 6=deep
SEARCH_WEIGHT_TITLE = 10.0
SEARCH_WEIGHT_DESCRIPTION = 5.0
SEARCH_WEIGHT_SEARCH_TEXT = 2.0
SEARCH_WEIGHT_TAGS = 3.0
SEARCH_WEIGHT_DEEP = 1.0
```

### TASK-3: Update cursor-based pagination

**File**: `skillmeat/cache/repositories.py`
**Change**: Cursor format needs to include relevance score for consistent pagination:
- Current: `"{confidence_score}:{entry_id}"`
- New: `"{relevance}:{confidence_score}:{entry_id}"`

Pagination filter update:
```sql
(relevance > :cursor_relevance OR
 (relevance = :cursor_relevance AND confidence_score < :cursor_confidence) OR
 (relevance = :cursor_relevance AND confidence_score = :cursor_confidence AND id > :cursor_id))
```

## Quality Gates

```bash
pytest tests/api/test_marketplace_catalog.py -v
pnpm test --filter=web -- --grep="search"
pnpm typecheck
pnpm lint
```

## Out of Scope

- UI changes to expose ranking configuration (future Advanced Search)
- Changes to the LIKE fallback search (maintains current behavior)
- Schema/migration changes (no database changes needed)

## Notes

- bm25() returns negative values (closer to 0 = better relevance)
- ORDER BY relevance ASC puts best matches first
- Confidence score remains secondary tie-breaker
- LIKE fallback unchanged (non-FTS5 environments)
