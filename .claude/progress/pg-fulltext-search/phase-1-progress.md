---
type: progress
schema_version: 2
doc_type: progress
prd: pg-fulltext-search
feature_slug: pg-fulltext-search
prd_ref: null
plan_ref: null
phase: 1
title: PostgreSQL Full-Text Search (Dual-Backend)
status: pending
started: null
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: on-track
total_tasks: 8
completed_tasks: 5
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
depends_on:
- enterprise-db-storage/phase-8
owners:
- python-backend-engineer
contributors:
- data-layer-expert
parallelization:
  strategy: batched
  max_concurrent: 3
  batch_1:
  - PG-FTS-1.1
  - PG-FTS-1.2
  batch_2:
  - PG-FTS-1.3
  batch_3:
  - PG-FTS-1.4
  - PG-FTS-1.5
  batch_4:
  - PG-FTS-1.6
  - PG-FTS-1.7
  batch_5:
  - PG-FTS-1.8
tasks:
- id: PG-FTS-1.1
  description: Create Alembic migration for tsvector column, GIN index, and trigger
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 2sp
  priority: critical
  files:
  - skillmeat/cache/migrations/versions/YYYYMMDD_HHMM_add_pg_fulltext_search.py
  notes: "PostgreSQL-only migration (guard with `if not is_postgresql(): return`).\n\
    \n1. Add `search_vector` column (type `TSVector`) to `marketplace_catalog_entries`\
    \ table\n2. Create GIN index on `search_vector` column\n3. Create trigger function\
    \ that builds tsvector from weighted columns:\n   - title: weight 'A' (highest)\n\
    \   - search_tags: weight 'B'\n   - description: weight 'C'\n   - search_text\
    \ + deep_search_text: weight 'D'\n4. Create trigger to auto-update search_vector\
    \ on INSERT/UPDATE\n5. Backfill existing rows: UPDATE ... SET search_vector =\
    \ to_tsvector(...)\n\nWeight mapping (SQLite FTS5 → PostgreSQL):\n- SEARCH_WEIGHT_TITLE\
    \ (10.0) → 'A'\n- SEARCH_WEIGHT_TAGS (3.0) → 'B'\n- SEARCH_WEIGHT_DESCRIPTION\
    \ (5.0) → 'C' (PG has only A/B/C/D)\n- SEARCH_WEIGHT_SEARCH_TEXT (2.0) → 'D'\n\
    - SEARCH_WEIGHT_DEEP (1.0) → 'D'\n\nDowngrade: drop trigger, function, index,\
    \ column.\n"
- id: PG-FTS-1.2
  description: Refactor search backend detection from FTS5-only to dialect-aware
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 1sp
  priority: critical
  files:
  - skillmeat/api/utils/fts5.py
  notes: "Extend (not replace) fts5.py to support dialect-aware search backend detection.\n\
    \nCurrent: `check_fts5_available()` checks sqlite_master for catalog_fts table.\n\
    \nNew behavior:\n1. Add `SearchBackendType` enum: FTS5, TSVECTOR, LIKE\n2. Add\
    \ `detect_search_backend(session) -> SearchBackendType`:\n   - If dialect is PostgreSQL:\
    \ check for search_vector column → TSVECTOR\n   - If dialect is SQLite: existing\
    \ FTS5 check → FTS5 or LIKE\n3. Add `get_search_backend() -> SearchBackendType`\
    \ (cached, like current is_fts5_available)\n4. Keep `is_fts5_available()` working\
    \ for backward compatibility (returns True if FTS5)\n5. Add `is_tsvector_available()`\
    \ for PostgreSQL path\n\nThe detection runs once at API startup (lifespan), same\
    \ as current FTS5 check.\n"
- id: PG-FTS-1.3
  description: Add SQLAlchemy TSVector column to MarketplaceCatalogEntry model
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - PG-FTS-1.1
  estimated_effort: 1sp
  priority: critical
  files:
  - skillmeat/cache/models.py
  notes: 'Add `search_vector` column to MarketplaceCatalogEntry model.


    Must be dialect-conditional — only present on PostgreSQL:

    - Use `Column(TSVector(), nullable=True)` from sqlalchemy.dialects.postgresql

    - The column must not break SQLite (column just won''t exist in SQLite schema)

    - Consider using a deferred column or conditional model mixin


    Alternative: Since SQLAlchemy models define the "desired" schema and migrations

    handle the actual DB, the column can exist in the model — SQLite simply won''t

    have it. The model should use `server_default=None` and the column should be

    excluded from SQLite queries via the repository layer.

    '
- id: PG-FTS-1.4
  description: Implement _search_tsvector() in MarketplaceCatalogRepository
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - PG-FTS-1.2
  - PG-FTS-1.3
  estimated_effort: 3sp
  priority: critical
  files:
  - skillmeat/cache/repositories.py
  notes: "Add `_search_tsvector()` method parallel to existing `_search_fts5()`.\n\
    \nImplementation:\n1. Query building:\n   - Parse user query → `plainto_tsquery('english',\
    \ query)` or `websearch_to_tsquery`\n   - Same special char stripping as `_build_fts5_query()`\n\
    \   - Prefix matching: use `to_tsquery` with `:*` suffix for partial matches\n\
    \n2. Relevance ranking:\n   - `ts_rank_cd(search_vector, query)` — uses cover\
    \ density ranking\n   - Weights already baked into tsvector via trigger (A/B/C/D)\n\
    \   - Negate rank for cursor compatibility (FTS5 uses negative BM25)\n\n3. Snippet\
    \ generation:\n   - `ts_headline('english', title, query, 'StartSel=<mark>, StopSel=</mark>')`\
    \ for title_snippet\n   - `ts_headline('english', description, query, ...)` for\
    \ description_snippet\n   - Set MaxWords/MinWords/MaxFragments options for reasonable\
    \ snippets\n\n4. Deep search detection:\n   - If match is only in search_text/deep_search_text\
    \ (not title/description):\n     set `deep_match=True`\n   - Use separate `ts_rank`\
    \ calls per field to determine match location\n\n5. Cursor pagination:\n   - Same\
    \ format as FTS5: `\"{relevance}:{confidence_score}:{entry_id}\"`\n   - Ensures\
    \ API consumers don't need to know which backend is active\n\n6. Update `search()`\
    \ method branching:\n   ```python\n   if backend == SearchBackendType.TSVECTOR:\n\
    \       return self._search_tsvector(...)\n   elif backend == SearchBackendType.FTS5:\n\
    \       return self._search_fts5(...)\n   else:\n       return self._search_like(...)\n\
    \   ```\n"
- id: PG-FTS-1.5
  description: Update search endpoint to pass backend type to repository
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - PG-FTS-1.2
  estimated_effort: 1sp
  priority: high
  files:
  - skillmeat/api/routers/marketplace_catalog.py
  notes: 'Update `search_catalog()` endpoint:

    1. Import `get_search_backend` from utils

    2. Pass backend type to repository `search()` method

    3. No changes to API contract — request/response schemas unchanged

    4. Optionally: add `x-search-backend` response header for debugging


    The endpoint remains identical from the consumer''s perspective.

    SQLite deployments get FTS5, PostgreSQL deployments get tsvector,

    and both fall back to LIKE if their respective FTS is unavailable.

    '
- id: PG-FTS-1.6
  description: Unit tests for tsvector search (mocked)
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - PG-FTS-1.4
  estimated_effort: 2sp
  priority: high
  files:
  - skillmeat/cache/tests/test_tsvector_search.py
  notes: 'Unit tests with mocked PostgreSQL dialect:

    1. Query building: verify tsquery generation from user input

    2. Special character handling: same edge cases as FTS5 tests

    3. Snippet generation: verify ts_headline SQL construction

    4. Cursor pagination: verify format compatibility with FTS5 cursors

    5. Deep match detection: verify deep_match flag logic

    6. Fallback: verify LIKE fallback when tsvector unavailable


    Use mock-based approach (MagicMock(spec=Session)) per enterprise test patterns.

    '
- id: PG-FTS-1.7
  description: Integration tests for tsvector search (PostgreSQL)
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - PG-FTS-1.4
  estimated_effort: 2sp
  priority: high
  files:
  - skillmeat/cache/tests/test_pg_search_integration.py
  notes: '@pytest.mark.integration tests against real PostgreSQL:

    1. Run migration → verify search_vector column + GIN index created

    2. Insert catalog entries → verify trigger populates search_vector

    3. Search by title → verify relevance ranking (title matches rank highest)

    4. Search by tags → verify tag matches rank appropriately

    5. Search deep content → verify deep_match flag set correctly

    6. Pagination → verify cursor-based pagination works

    7. Snippet markup → verify <mark> tags in snippets

    8. Empty/special queries → verify graceful handling

    9. Compare results with LIKE fallback for same query → verify superset

    '
- id: PG-FTS-1.8
  description: SQLite regression test — verify FTS5 path unchanged
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - PG-FTS-1.4
  - PG-FTS-1.5
  estimated_effort: 1sp
  priority: critical
  files:
  - skillmeat/cache/tests/test_fts5_regression.py
  notes: 'Verify the existing SQLite FTS5 search path is completely unaffected:

    1. FTS5 detection still works

    2. Search results identical to before refactor

    3. Snippets, pagination, deep search all unchanged

    4. LIKE fallback still works when FTS5 unavailable


    This is the safety net — dual-backend must not regress the primary path.

    Run as part of standard pytest suite (no @pytest.mark.integration needed).

    '
progress: 62
updated: '2026-03-10'
---

# Phase 1: PostgreSQL Full-Text Search (Dual-Backend)

## Context

SkillMeat supports both SQLite (local/personal) and PostgreSQL (enterprise) deployments. The current full-text search uses SQLite FTS5 with LIKE fallback. PostgreSQL deployments currently get LIKE-only search. This phase adds native PostgreSQL tsvector/GIN full-text search as a parallel backend.

**Prerequisite**: `enterprise-db-storage/phase-8` (migration compatibility) must complete first so migrations can use dialect guards.

**Critical constraint**: Both backends must remain fully functional. SQLite users keep FTS5, PostgreSQL users get tsvector. Neither path may regress.

## Architecture

```
search_catalog() endpoint (unchanged API contract)
  │
  ├─ detect_search_backend() at startup
  │   ├─ PostgreSQL? → check search_vector column → TSVECTOR
  │   └─ SQLite? → check catalog_fts table → FTS5 or LIKE
  │
  └─ repository.search()
      ├─ TSVECTOR → _search_tsvector()    [NEW]
      │   ├─ websearch_to_tsquery()
      │   ├─ ts_rank_cd() for relevance
      │   └─ ts_headline() for snippets
      │
      ├─ FTS5 → _search_fts5()            [EXISTING, unchanged]
      │   ├─ FTS5 MATCH query
      │   ├─ bm25() for relevance
      │   └─ snippet() for highlights
      │
      └─ LIKE → _search_like()            [EXISTING, unchanged]
          └─ ILIKE pattern matching
```

## Feature Parity Matrix

| Capability | SQLite FTS5 | PostgreSQL tsvector | LIKE Fallback |
|-----------|-------------|---------------------|---------------|
| Relevance ranking | BM25 | ts_rank_cd | None (confidence only) |
| Snippet highlights | snippet() with `<mark>` | ts_headline() with `<mark>` | None |
| Stemming | Porter tokenizer | English dictionary | None |
| Prefix matching | term* syntax | :* suffix | % wildcard |
| Deep content search | deep_search_text column | search_vector includes deep text | ILIKE on deep_search_text |
| Column weights | BM25 column weights | A/B/C/D tsvector weights | Equal weighting |
| Cursor pagination | relevance:confidence:id | relevance:confidence:id | confidence:id |

## Weight Mapping

| Field | FTS5 Weight | PG Weight Class | Rationale |
|-------|-------------|-----------------|-----------|
| title | 10.0 | A (highest) | Title matches most relevant |
| search_tags | 3.0 | B | Tag matches highly relevant |
| description | 5.0 | C | Description contextually important |
| search_text | 2.0 | D (lowest) | Content matches useful but noisy |
| deep_search_text | 1.0 | D (lowest) | Deep content least specific |

Note: PostgreSQL only has 4 weight classes (A-D), so description and tags swap relative positions compared to FTS5 numeric weights. This is acceptable — the ranking intent (title > tags ≈ desc > content) is preserved.

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Add method, don't abstract | `_search_tsvector()` parallel to `_search_fts5()` — YAGNI, no strategy pattern |
| Same cursor format | API consumers don't need to know which backend is active |
| Trigger-based tsvector updates | Automatic, no application-layer sync needed |
| `websearch_to_tsquery` | More forgiving than `to_tsquery`, handles user input naturally |
| Skip FTS5 on PG, skip tsvector on SQLite | Clean separation — each dialect uses its native FTS |
| Column in model, guarded in queries | SQLAlchemy model defines superset; queries are dialect-aware |

## Orchestration Quick Reference

```bash
# Single task update
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/pg-fulltext-search/phase-1-progress.md -t PG-FTS-1.1 -s completed

# Batch update
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/pg-fulltext-search/phase-1-progress.md \
  --updates "PG-FTS-1.1:completed,PG-FTS-1.2:completed"
```
