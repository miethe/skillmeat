---
title: 'Implementation Plan: PostgreSQL Full-Text Search'
schema_version: 2
doc_type: implementation_plan
status: completed
created: 2026-03-09
updated: '2026-03-10'
feature_slug: pg-fulltext-search
feature_version: v1
prd_ref: null
plan_ref: null
scope: Native PostgreSQL tsvector/GIN full-text search parallel to SQLite FTS5, maintaining
  dual-backend support
effort_estimate: ~13 story points
architecture_summary: Parallel _search_tsvector() path in MarketplaceCatalogRepository
  using PostgreSQL tsvector/GIN with automatic trigger-based updates, dialect-aware
  search backend detection, and identical API surface to existing FTS5/LIKE paths
related_documents:
- docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1.md
owner: python-backend-engineer
contributors:
- data-layer-expert
priority: high
risk_level: medium
category: product-planning
tags:
- postgresql
- full-text-search
- tsvector
- fts5
- dual-backend
- search
milestone: null
commit_refs: []
pr_refs: []
files_affected: []
---
# Implementation Plan: PostgreSQL Full-Text Search

## Executive Summary

This plan adds native PostgreSQL tsvector/GIN full-text search as a parallel backend alongside the existing SQLite FTS5 search. PostgreSQL deployments currently receive LIKE-only search, which lacks relevance ranking and snippets. The implementation preserves SQLite FTS5 as the primary path for local deployments while transparently enabling tsvector on PostgreSQL-backed enterprise instances.

**Key Outcomes:**
- PostgreSQL tsvector column with GIN index on `marketplace_catalog_entries`
- Dialect-aware search backend detection (FTS5 for SQLite, tsvector for PostgreSQL, LIKE fallback)
- `_search_tsvector()` implementation with relevance ranking via `ts_rank_cd`, snippet generation, and cursor pagination
- Identical API surface — consumers don't know which backend is active
- Zero regression to existing SQLite FTS5 path
- Full test coverage (unit, integration, regression)

**Complexity:** Small | **Phase:** 1 (Single Phase) | **Estimated Effort:** ~13 story points | **Estimated Timeline:** 2-3 weeks

---

## Implementation Strategy

### Architecture & Sequencing

**Critical Dependency:**
- **enterprise-db-storage Phase 8** (migration compatibility) must land first
  - Provides dialect guards (`is_postgresql()`) for migrations
  - Ensures Alembic can handle dialect-specific operations
  - No blocker on PRD 2 (AAA/RBAC) — search is stateless and tenant-agnostic at this layer

**Layered Sequence (MP Architecture):**
1. **Database Layer** (PG-FTS-1.1): Alembic migration adds `search_vector` TSVector column, GIN index, trigger function, and backfill
2. **Model Layer** (PG-FTS-1.3): SQLAlchemy TSVector column (dialect-conditional)
3. **Utils Layer** (PG-FTS-1.2): Dialect-aware search backend detection enum and factory
4. **Repository Layer** (PG-FTS-1.4): `_search_tsvector()` implementation parallel to `_search_fts5()`
5. **API Layer** (PG-FTS-1.5): Endpoint passes backend type to repository
6. **Testing Layer** (PG-FTS-1.6, PG-FTS-1.7, PG-FTS-1.8): Unit (mocked), integration (real PG), regression (FTS5)

**Parallelization Strategy:**
- Batch 1 (parallel): Migration (1.1) and backend detection (1.2) — independent
- Batch 2: Model addition (1.3) — depends on migration
- Batch 3 (parallel): Implementation (1.4) and endpoint update (1.5) — independent
- Batch 4 (parallel): Unit tests (1.6) and integration tests (1.7) — independent
- Batch 5: Regression test (1.8) — depends on all implementation tasks

**Critical Path:** 1.1 → 1.3 → 1.4 → 1.8 (sequential on path); 1.2, 1.5, 1.6, 1.7 can overlap

---

## Phase Breakdown

### Phase 1: PostgreSQL Full-Text Search (Single Phase)

#### Phase Summary

| Task | Title | Dependencies | Effort | Subagent(s) |
|------|-------|--------------|--------|-------------|
| PG-FTS-1.1 | Alembic migration — add `search_vector` column, GIN index, trigger | None | 2sp | python-backend-engineer |
| PG-FTS-1.2 | Refactor `fts5.py` — add `SearchBackendType` enum and dialect detection | None | 1sp | python-backend-engineer |
| PG-FTS-1.3 | Add TSVector column to MarketplaceCatalogEntry model | PG-FTS-1.1 | 1sp | python-backend-engineer |
| PG-FTS-1.4 | Implement `_search_tsvector()` in MarketplaceCatalogRepository | PG-FTS-1.2, PG-FTS-1.3 | 3sp | python-backend-engineer |
| PG-FTS-1.5 | Update `search_catalog()` endpoint to pass backend type | PG-FTS-1.2 | 1sp | python-backend-engineer |
| PG-FTS-1.6 | Unit tests for tsvector search (mocked PostgreSQL dialect) | PG-FTS-1.4 | 2sp | python-backend-engineer |
| PG-FTS-1.7 | Integration tests for tsvector search (real PostgreSQL) | PG-FTS-1.4 | 2sp | python-backend-engineer |
| PG-FTS-1.8 | SQLite regression test — verify FTS5 path unchanged | PG-FTS-1.4, PG-FTS-1.5 | 1sp | python-backend-engineer |

**Total Estimated Effort:** 13 story points | **Timeline:** 2-3 weeks

---

## Detailed Task Breakdown

### Task PG-FTS-1.1: Alembic Migration — tsvector Column, GIN Index, Trigger

**Assigned:** python-backend-engineer
**Estimated Effort:** 2 story points
**Priority:** Critical
**Dependencies:** None

**Description:**
Create an Alembic migration that adds PostgreSQL full-text search infrastructure to `marketplace_catalog_entries` table without affecting SQLite deployments.

**Acceptance Criteria:**
- [ ] Migration file `skillmeat/cache/migrations/versions/YYYYMMDD_HHMM_add_pg_fulltext_search.py` created
- [ ] Upgrade path:
  - [ ] `search_vector` TSVector column added to `marketplace_catalog_entries` (nullable)
  - [ ] GIN index created on `search_vector` column for query performance
  - [ ] Trigger function created that computes weighted tsvector from title→A, tags→B, description→C, search_text+deep→D
  - [ ] Trigger installed to auto-update `search_vector` on INSERT and UPDATE
  - [ ] All existing rows backfilled with tsvector values via `UPDATE ... SET search_vector = to_tsvector(...)`
- [ ] Downgrade path:
  - [ ] Trigger dropped
  - [ ] Trigger function dropped
  - [ ] GIN index dropped
  - [ ] Column dropped
- [ ] Migration guarded with `is_postgresql()` check — no-op on SQLite
- [ ] Migration execution time <30s on 10K+ row catalog (benchmarked)
- [ ] No breaking changes to SQLite schema or migrations

**Implementation Notes:**
- Use dialect helpers from `skillmeat/cache/migrations/dialect_helpers.py` (Phase 8 pattern)
- Trigger function signature: `marketplace_catalog_entries_update_search_vector()`
- Weight mapping: FTS5 weights 10/3/5/2/1 → PG classes A/B/C/D
- Backfill uses `SET RETURNING rowid` to validate completion
- Test against both PostgreSQL and SQLite containers

**Files:**
- `skillmeat/cache/migrations/versions/[timestamp]_add_pg_fulltext_search.py` (new)

---

### Task PG-FTS-1.2: Refactor fts5.py — Search Backend Detection

**Assigned:** python-backend-engineer
**Estimated Effort:** 1 story point
**Priority:** Critical
**Dependencies:** None

**Description:**
Extend `skillmeat/api/utils/fts5.py` to support dialect-aware search backend detection without removing existing FTS5 functionality.

**Acceptance Criteria:**
- [ ] `SearchBackendType` enum created with values: FTS5, TSVECTOR, LIKE
- [ ] `detect_search_backend(session) -> SearchBackendType` function added:
  - [ ] Checks `session.connection().dialect.name`
  - [ ] If PostgreSQL: checks for `search_vector` column in `marketplace_catalog_entries` → returns TSVECTOR
  - [ ] If SQLite: runs existing FTS5 check via `sqlite_master` query → returns FTS5 or LIKE
  - [ ] Falls back to LIKE if detection uncertain
- [ ] `get_search_backend() -> SearchBackendType` factory function added:
  - [ ] Detects backend once at API startup (via lifespan event)
  - [ ] Caches result in module-level singleton
  - [ ] Returns cached value on subsequent calls
- [ ] Existing `is_fts5_available()` function preserved:
  - [ ] Still returns `True` if FTS5 is available
  - [ ] Still returns `False` if LIKE fallback is active
  - [ ] All existing callers continue to work unchanged
- [ ] New `is_tsvector_available()` function added (parallel to `is_fts5_available`)
- [ ] No breaking changes to public API of fts5.py

**Implementation Notes:**
- Use SQLAlchemy session's connection dialect for detection
- Cache detection result at module level: `_search_backend_cache = None`
- Detection is idempotent — safe to call multiple times
- Test with mock SQLAlchemy sessions for both dialects

**Files:**
- `skillmeat/api/utils/fts5.py` (modified)

---

### Task PG-FTS-1.3: Add TSVector Column to MarketplaceCatalogEntry Model

**Assigned:** python-backend-engineer
**Estimated Effort:** 1 story point
**Priority:** Critical
**Dependencies:** PG-FTS-1.1

**Description:**
Add SQLAlchemy TSVector column to `MarketplaceCatalogEntry` model in a dialect-conditional way so it appears in the model definition without breaking SQLite.

**Acceptance Criteria:**
- [ ] `search_vector` column added to `MarketplaceCatalogEntry` in `skillmeat/cache/models.py`
- [ ] Column type is `sqlalchemy.dialects.postgresql.TSVector`
- [ ] Column is nullable (`nullable=True`)
- [ ] Column does not break SQLite deployments:
  - [ ] SQLite simply doesn't have the column (migration guards it)
  - [ ] Model can be imported by SQLite runtime without errors
  - [ ] Column references in code are guarded by dialect checks
- [ ] Column has appropriate metadata: `comment="Full-text search vector for PostgreSQL"`
- [ ] Model migration creates schema that matches migration PG-FTS-1.1
- [ ] SQLite tests still pass (column is silently ignored)

**Implementation Notes:**
- Import: `from sqlalchemy.dialects.postgresql import TSVector`
- Use conditional approach: column exists in model but is dialect-aware
- Alternative: Use `ColumnDefault` with dialect-specific logic (verify approach with backend-architect)
- Test SQLite import and instantiation to confirm no breakage

**Files:**
- `skillmeat/cache/models.py` (modified)

---

### Task PG-FTS-1.4: Implement _search_tsvector() in MarketplaceCatalogRepository

**Assigned:** python-backend-engineer
**Estimated Effort:** 3 story points
**Priority:** Critical
**Dependencies:** PG-FTS-1.2, PG-FTS-1.3

**Description:**
Implement PostgreSQL tsvector search as a parallel path in `MarketplaceCatalogRepository.search()` method, using the same interface and cursor format as the existing `_search_fts5()` method.

**Acceptance Criteria:**
- [ ] `_search_tsvector()` method added to `MarketplaceCatalogRepository`
- [ ] Query parsing:
  - [ ] User query cleaned (special characters stripped, leading/trailing whitespace trimmed)
  - [ ] Query passed to `websearch_to_tsquery('english', query)` for forgiving parsing
  - [ ] Prefix matching supported via `:*` suffix in tsquery
- [ ] Relevance ranking:
  - [ ] Uses `ts_rank_cd(search_vector, query)` for cover density ranking
  - [ ] Weights inherited from tsvector (A/B/C/D classes set by trigger)
  - [ ] Ranking is negated for cursor sort compatibility (FTS5 also uses negative BM25)
- [ ] Snippet generation:
  - [ ] Title snippet via `ts_headline('english', title, query, options)` with `<mark>` tags
  - [ ] Description snippet via `ts_headline('english', description, query, options)`
  - [ ] Options include: `StartSel=<mark>, StopSel=</mark>, MaxWords=75, MinWords=50, MaxFragments=1`
  - [ ] HTML-safe markup in snippets
- [ ] Deep search detection:
  - [ ] Computes separate `ts_rank` for title vs description vs content columns
  - [ ] Sets `deep_match=True` if match is only in `search_text`/`deep_search_text` (not title/description)
  - [ ] Matches to `_search_fts5()` deep detection logic
- [ ] Cursor pagination:
  - [ ] Cursor format: `"{relevance}:{confidence_score}:{entry_id}"` (same as FTS5)
  - [ ] Enables seamless API consumer experience regardless of backend
  - [ ] `relevance` is negated `ts_rank_cd` score
  - [ ] `confidence_score` is secondary sort key (same as FTS5)
  - [ ] `entry_id` is tertiary sort key for determinism
- [ ] Return type matches `_search_fts5()` return signature:
  - [ ] List of `SearchResult` objects (or equivalent DTO)
  - [ ] Each result includes: `artifact_id`, `artifact_type`, `title`, `description`, `title_snippet`, `description_snippet`, `relevance`, `confidence_score`, `deep_match`, `cursor`
- [ ] Search branching in `search()` method:
  - [ ] Detects backend via `get_search_backend()`
  - [ ] Routes to `_search_tsvector()` if TSVECTOR
  - [ ] Routes to `_search_fts5()` if FTS5
  - [ ] Falls back to `_search_like()` if LIKE
- [ ] Query limits respected: `limit` and `offset` parameters passed through
- [ ] No breaking changes to existing `search()` method signature

**Implementation Notes:**
- Mirror `_search_fts5()` structure closely for consistency
- Use `session.execute()` for raw SQL where needed (tsquery generation is complex in ORM)
- Cover density ranking (`ts_rank_cd`) preferred over simple `ts_rank` for better relevance
- Prefix matching: append `:*` to last lexeme for partial word matching
- Deep match detection: compute per-column ranks and compare to determine source
- Test with real PostgreSQL in integration phase (PG-FTS-1.7)

**Files:**
- `skillmeat/cache/repositories.py` (modified, MarketplaceCatalogRepository class)

---

### Task PG-FTS-1.5: Update search_catalog() Endpoint

**Assigned:** python-backend-engineer
**Estimated Effort:** 1 story point
**Priority:** High
**Dependencies:** PG-FTS-1.2

**Description:**
Update the `search_catalog()` endpoint in `skillmeat/api/routers/marketplace_catalog.py` to detect and pass the search backend type to the repository.

**Acceptance Criteria:**
- [ ] `get_search_backend()` imported from `skillmeat.api.utils.fts5`
- [ ] Backend type detected at request time (or cached from startup)
- [ ] Backend type passed to `repository.search()` method
- [ ] No changes to request schema or response schema:
  - [ ] Query parameter `q` unchanged
  - [ ] Query parameter `limit` unchanged
  - [ ] Query parameter `cursor` unchanged
  - [ ] Response includes same fields: results, next_cursor, total_estimate
- [ ] Optional: Add `X-Search-Backend` response header for debugging (non-breaking)
  - [ ] Header value: "fts5", "tsvector", or "like"
  - [ ] Helps clients understand which backend processed their query
- [ ] API contract fully backward-compatible
  - [ ] Consumers neither know nor care which backend is active
  - [ ] Search results have same relevance and format
- [ ] Error handling: gracefully falls back if backend detection fails

**Implementation Notes:**
- Backend detection happens once at startup and is cached
- Passing backend to repository avoids repeated detection
- SQLite deployments transparently get FTS5, PostgreSQL get tsvector
- Both paths converge at API response serialization

**Files:**
- `skillmeat/api/routers/marketplace_catalog.py` (modified, search_catalog function)

---

### Task PG-FTS-1.6: Unit Tests for tsvector Search (Mocked)

**Assigned:** python-backend-engineer
**Estimated Effort:** 2 story points
**Priority:** High
**Dependencies:** PG-FTS-1.4

**Description:**
Create comprehensive unit tests for tsvector search using mocked PostgreSQL dialect (no real database required).

**Acceptance Criteria:**
- [ ] Test file `skillmeat/cache/tests/test_tsvector_search.py` created
- [ ] Query building tests:
  - [ ] Simple query parsing: "python" → valid tsquery
  - [ ] Multi-word query: "full text search" → valid compound tsquery
  - [ ] Special characters stripped: "python & | !" → safe tsquery
  - [ ] Prefix matching: "python" → ":*" suffix appended
  - [ ] Empty query handling: returns empty results or appropriate error
- [ ] Snippet generation tests:
  - [ ] Title snippet includes `<mark>` tags around matched terms
  - [ ] Description snippet includes `<mark>` tags
  - [ ] MaxWords/MinWords options respected
  - [ ] HTML entities properly escaped
- [ ] Cursor pagination tests:
  - [ ] Cursor format validation: `"{relevance}:{confidence}:{id}"`
  - [ ] Cursor parsing and offset calculation
  - [ ] Cursor compatibility with FTS5 format
  - [ ] Pagination across result sets
- [ ] Deep match detection tests:
  - [ ] `deep_match=True` when match only in search_text/deep_search_text
  - [ ] `deep_match=False` when match in title/description
  - [ ] Mixed matches handled correctly
- [ ] Fallback tests:
  - [ ] Graceful fallback to LIKE when tsvector column unavailable
  - [ ] Error logging on fallback
- [ ] Uses mock-based approach:
  - [ ] `MagicMock(spec=Session)` for SQLAlchemy session
  - [ ] Mock `connection()` with PostgreSQL dialect
  - [ ] Mock `execute()` to return tsvector results
- [ ] No real PostgreSQL required
- [ ] All tests pass with pytest

**Implementation Notes:**
- Mirror test structure of `test_fts5_search.py` (if exists)
- Use pytest fixtures for common mocks
- Parametrize test cases for query variations
- Focus on SQLAlchemy mock accuracy

**Files:**
- `skillmeat/cache/tests/test_tsvector_search.py` (new)

---

### Task PG-FTS-1.7: Integration Tests for tsvector Search (Real PostgreSQL)

**Assigned:** python-backend-engineer
**Estimated Effort:** 2 story points
**Priority:** High
**Dependencies:** PG-FTS-1.4

**Description:**
Create integration tests that validate tsvector search against a real PostgreSQL database (docker-compose container).

**Acceptance Criteria:**
- [ ] Test file `skillmeat/cache/tests/test_pg_search_integration.py` created
- [ ] Marked with `@pytest.mark.integration` (skipped in fast test runs, included in CI)
- [ ] PostgreSQL container setup:
  - [ ] Uses `docker-compose` PostgreSQL service (or pytest-postgresql fixture)
  - [ ] Migrations automatically applied before tests run
- [ ] Migration validation tests:
  - [ ] `search_vector` column created
  - [ ] GIN index created and queryable
  - [ ] Trigger function created and callable
  - [ ] Existing rows backfilled with tsvector values
- [ ] Basic search tests:
  - [ ] Insert test catalog entries with various titles, descriptions, tags
  - [ ] Search by title: results ranked with title matches first
  - [ ] Search by tag: tag matches appear with appropriate ranking
  - [ ] Search by description content
  - [ ] Search by deep content (search_text/deep_search_text)
- [ ] Relevance ranking tests:
  - [ ] Title matches rank higher than description matches
  - [ ] Description matches rank higher than content matches
  - [ ] Multiple matches in same field rank higher than single matches
  - [ ] `ts_rank_cd` scores are sensible and consistent
- [ ] Snippet tests:
  - [ ] Snippets contain `<mark>` tags around matched terms
  - [ ] Snippets are truncated at MaxWords
  - [ ] Multiple snippets generated for long content
  - [ ] HTML escaping works correctly
- [ ] Pagination tests:
  - [ ] Cursor-based pagination works across multiple pages
  - [ ] Cursor format compatible with FTS5 cursors
  - [ ] Pagination handles edge cases (empty results, single page)
- [ ] Special query tests:
  - [ ] Empty query: returns empty results
  - [ ] Single character query: handled gracefully
  - [ ] Very long query: truncated or handled gracefully
  - [ ] SQL injection attempts: safely rejected
- [ ] Comparison with LIKE fallback:
  - [ ] tsvector results are a superset of LIKE results (all LIKE matches included)
  - [ ] tsvector results ranked better than LIKE results
  - [ ] Both backends return same set of matching artifacts (different order OK)
- [ ] Performance baseline established:
  - [ ] Search query <100ms for 10K entries (measured)
  - [ ] Index scan used (EXPLAIN ANALYZE confirms)
  - [ ] No full table scans on indexed queries
- [ ] All tests pass

**Implementation Notes:**
- Use pytest fixtures to create and tear down test database
- Seed test data with realistic catalog entries
- Use `EXPLAIN ANALYZE` to verify query plans
- Run as part of CI with PostgreSQL service
- Can be run locally with `pytest -m integration`

**Files:**
- `skillmeat/cache/tests/test_pg_search_integration.py` (new)

---

### Task PG-FTS-1.8: SQLite Regression Test — Verify FTS5 Path Unchanged

**Assigned:** python-backend-engineer
**Estimated Effort:** 1 story point
**Priority:** Critical
**Dependencies:** PG-FTS-1.4, PG-FTS-1.5

**Description:**
Create regression tests that verify the existing SQLite FTS5 search path is completely unaffected by the tsvector refactoring.

**Acceptance Criteria:**
- [ ] Test file `skillmeat/cache/tests/test_fts5_regression.py` created
- [ ] FTS5 detection still works:
  - [ ] `is_fts5_available()` returns `True` for SQLite with FTS5 table
  - [ ] `is_fts5_available()` returns `False` for SQLite without FTS5 table
  - [ ] FTS5 detection unchanged from before refactor
- [ ] Search results identical to pre-refactor:
  - [ ] Same queries return same results
  - [ ] Results ranked identically (BM25 scores match)
  - [ ] Pagination cursors compatible
- [ ] Snippet generation unchanged:
  - [ ] Snippets have `<mark>` tags
  - [ ] Snippet content matches pre-refactor output
  - [ ] Truncation at MaxWords works as before
- [ ] Pagination unchanged:
  - [ ] Cursor format `"{relevance}:{confidence}:{id}"` preserved
  - [ ] Pagination logic unchanged
  - [ ] Edge cases handled identically
- [ ] Deep search detection unchanged:
  - [ ] `deep_match` flag set correctly
  - [ ] Deep content search results match pre-refactor
- [ ] LIKE fallback still works:
  - [ ] When FTS5 unavailable, LIKE fallback activates
  - [ ] LIKE results correct (subset of FTS5 results)
  - [ ] Fallback graceful with no errors
- [ ] All tests pass (run as part of standard pytest suite)
- [ ] No `@pytest.mark.integration` — runs in fast mode

**Implementation Notes:**
- Use SQLite in-memory database for fast testing
- Create FTS5 virtual table in test setup
- Insert pre-refactor test data and run same queries
- Compare results before/after refactoring (if previous run available)
- This is the safety net — critical to verify no regression

**Files:**
- `skillmeat/cache/tests/test_fts5_regression.py` (new)

---

## Feature Parity Matrix

| Capability | SQLite FTS5 | PostgreSQL tsvector | LIKE Fallback |
|-----------|-------------|---------------------|---------------|
| Relevance ranking | BM25 | ts_rank_cd | None (confidence only) |
| Snippet highlights | snippet() with `<mark>` | ts_headline() with `<mark>` | None |
| Stemming | Porter tokenizer | English dictionary | None |
| Prefix matching | term* syntax | :* suffix | % wildcard |
| Deep content search | deep_search_text column | search_vector includes deep text | ILIKE on deep_search_text |
| Column weights | BM25 numeric weights | A/B/C/D tsvector weights | Equal weighting |
| Cursor pagination | relevance:confidence:id | relevance:confidence:id | confidence:id |
| Performance | <100ms for 10K entries | <100ms for 10K entries | ~500ms for 10K entries |

---

## Weight Mapping

| Field | FTS5 Weight | PG Weight Class | Mapping Rationale |
|-------|-------------|-----------------|-------------------|
| title | 10.0 | A (highest) | Title matches most relevant — highest priority in both systems |
| search_tags | 3.0 | B | Tag matches highly relevant — second priority |
| description | 5.0 | C | Description contextually important — third priority |
| search_text | 2.0 | D (lowest) | Content matches useful but noisy — lowest priority |
| deep_search_text | 1.0 | D (lowest) | Deep content least specific — lowest priority |

**Note:** PostgreSQL tsvector only supports 4 weight classes (A-D), while FTS5 supports continuous numeric weights. The mapping preserves the ranking intent (title > tags ≈ description > content) despite slight reordering in middle tiers. This is acceptable — users will see functionally equivalent relevance ranking.

---

## Key Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| Add method, don't abstract | `_search_tsvector()` lives parallel to `_search_fts5()` in repository — YAGNI, no strategy pattern abstraction. Single-path routing is clearer. |
| Same cursor format across backends | API consumers don't need to know which backend is active. Both FTS5 and tsvector return `"{relevance}:{confidence}:{id}"` cursors. |
| Trigger-based tsvector updates | Automatic sync via database trigger — no application-layer overhead. Trigger fires on INSERT/UPDATE, eliminating staleness. |
| `websearch_to_tsquery` vs `to_tsquery` | `websearch_to_tsquery` is more forgiving of user input (handles `&`, `\|` naturally). `to_tsquery` requires explicit operators. |
| Skip FTS5 on PG, skip tsvector on SQLite | Clean separation — PostgreSQL deployments use native tsvector, SQLite deployments use native FTS5. No cross-dialect code paths. |
| Column in model, guarded in queries | SQLAlchemy model defines the superset of columns (FTS5 and tsvector both). Queries are dialect-aware — repository checks backend type before using tsvector column. |
| Single-phase implementation | Feature is self-contained — doesn't depend on other PRDs. Can be implemented, tested, and deployed independently. |

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| Weight mapping imprecision (4 PG classes vs 5 FTS5 weights) | MEDIUM | MEDIUM | Ranking intent preserved (title > tags > desc > content). Results won't be identical but UX is equivalent. Validate via integration tests (PG-FTS-1.7). |
| Trigger overhead on bulk catalog inserts | LOW | LOW | Acceptable — catalog syncs are infrequent batch operations. Benchmark in PG-FTS-1.7 to confirm <100ms impact. |
| SQLite regression — accidentally breaking FTS5 | CRITICAL | LOW | Regression test (PG-FTS-1.8) is critical safety net. Run as part of standard test suite. Verify every CI run. |
| Query injection via tsquery parsing | MEDIUM | LOW | `websearch_to_tsquery` is safe (designed for user input). Unit test edge cases (PG-FTS-1.6). Integration test SQL injection attempts (PG-FTS-1.7). |
| PostgreSQL connection pool saturation | LOW | LOW | Search queries are read-only and fast (<100ms). Connection pooling is existing infrastructure (enterprise-db-storage Phase 3). Monitor as part of operational baseline. |
| Model column breaks SQLite import | MEDIUM | LOW | Dialect-conditional approach — column exists in model but is ignored by SQLite. Test SQLite import in unit tests (PG-FTS-1.6). |

### Schedule Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| enterprise-db-storage Phase 8 delayed | HIGH | MEDIUM | Work is blocked on migration compatibility. Coordinate with database team early. Consider interim workaround if delay >1 week. |
| PostgreSQL test environment setup | MEDIUM | MEDIUM | Use docker-compose PostgreSQL (already in enterprise-db-storage infrastructure). Automated fixture setup in pytest (PG-FTS-1.7). |

### Organizational Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| Knowledge silo (tsvector logic) | LOW | LOW | Implementation is straightforward — no exotic PostgreSQL features. Code comments explain weight mapping and ranking logic. |

---

## Quality Gates

### Phase 1 Complete When:

- [ ] All 8 tasks completed and merged to main
- [ ] Migration (PG-FTS-1.1) tested against both PostgreSQL and SQLite
  - [ ] PostgreSQL: search_vector column, GIN index, trigger all present and functional
  - [ ] SQLite: migration is no-op, no new columns or functions created
  - [ ] Backfill completes successfully for 10K+ rows (<30s)
  - [ ] Downgrade path tested and works
- [ ] Backend detection (PG-FTS-1.2) returns correct values
  - [ ] PostgreSQL instance: returns TSVECTOR or LIKE (if tsvector unavailable)
  - [ ] SQLite instance: returns FTS5 or LIKE
  - [ ] Caching works (repeated calls don't re-detect)
- [ ] tsvector search implementation (PG-FTS-1.4) passes all tests
  - [ ] Unit tests pass (mocked dialect)
  - [ ] Integration tests pass (real PostgreSQL)
  - [ ] Query results ranked sensibly
  - [ ] Snippets include `<mark>` tags
  - [ ] Cursor pagination works
  - [ ] Deep match detection accurate
- [ ] API endpoint (PG-FTS-1.5) passes all tests
  - [ ] Backend type detected and passed to repository
  - [ ] API contract unchanged (request/response schemas identical)
  - [ ] Both SQLite and PostgreSQL deployments return identical API responses
- [ ] SQLite regression (PG-FTS-1.8) passes
  - [ ] FTS5 path completely unchanged
  - [ ] Search results identical to pre-refactor baseline
  - [ ] Pagination and snippets unchanged
  - [ ] No performance regression
- [ ] Code review passed
  - [ ] All code follows project style guide
  - [ ] Comments explain weight mapping and ranking strategy
  - [ ] No TODOs or technical debt introduced
- [ ] Test coverage >90% for all new code
  - [ ] Unit tests: 100% of tsvector methods tested
  - [ ] Integration tests: real PostgreSQL validation
  - [ ] Regression tests: FTS5 unchanged
- [ ] Documentation updated
  - [ ] Code comments explain trigger function logic
  - [ ] ADR added for architectural decisions (weight mapping, cursor format, etc.)
  - [ ] API docs note that search_catalog endpoint transparently uses different backends per deployment

---

## Success Metrics

**Delivery Metrics:**
- All 8 tasks delivered on schedule ✓
- Zero regressions to SQLite FTS5 search ✓
- 100% test coverage of new code paths ✓

**Quality Metrics:**
- PostgreSQL search results ranked correctly (title > tags > description > content) ✓
- Search performance <100ms for 10K entries (PostgreSQL and SQLite both) ✓
- Cursor pagination compatible between backends ✓
- Snippet generation consistent (both backends produce `<mark>` tags) ✓

**Operational Metrics:**
- Zero multi-backend compatibility issues in production ✓
- Zero SQLite deployments affected by PostgreSQL tsvector logic ✓
- Migration completes <30s for typical catalog sizes ✓

---

## Pre-Implementation Checklist

Before Phase 1 begins:

- [ ] Confirm enterprise-db-storage Phase 8 (migration compatibility) is >90% complete
- [ ] Verify `is_postgresql()` dialect guard available in `skillmeat/cache/migrations/dialect_helpers.py`
- [ ] Set up docker-compose PostgreSQL for local development/testing
- [ ] Review existing `_search_fts5()` implementation in `MarketplaceCatalogRepository`
- [ ] Review existing FTS5 tests in `skillmeat/cache/tests/` (use as template)
- [ ] Identify where `search_catalog()` endpoint is defined (marketplace_catalog.py)
- [ ] Confirm SQLAlchemy version supports `TSVector` from `sqlalchemy.dialects.postgresql`
- [ ] Schedule kickoff with python-backend-engineer and data-layer-expert
- [ ] Create GitHub branch for feature development
- [ ] Set up CI to run integration tests with PostgreSQL

---

## Integration Points

### Upstream Integrations

- **enterprise-db-storage Phase 8**: Provides migration dialect guards (`is_postgresql()` and dialect-aware migration utilities)
- **Database Models**: Uses `MarketplaceCatalogEntry` model and `marketplace_catalog_entries` table
- **Existing FTS5 Logic**: Mirrors `_search_fts5()` implementation, cursor format, and pagination
- **API Layer**: Integrates with `search_catalog()` endpoint in marketplace_catalog router

### Downstream Integrations

- **Frontend Web UI**: No changes required — API response schema unchanged, consumers don't know which backend is active
- **CLI Users**: No changes required — search functionality unchanged from CLI perspective
- **Analytics/Monitoring**: Can optionally log `X-Search-Backend` header to understand which path is used
- **Future Enhancements**: Opens door for other PostgreSQL-specific features (advanced filtering, full-text weighting tuning, etc.)

---

## File Organization

```
skillmeat/
├── cache/
│   ├── migrations/
│   │   └── versions/
│   │       └── YYYYMMDD_HHMM_add_pg_fulltext_search.py  [PG-FTS-1.1]
│   ├── models.py                                         [PG-FTS-1.3]
│   ├── repositories.py                                   [PG-FTS-1.4]
│   └── tests/
│       ├── test_tsvector_search.py                       [PG-FTS-1.6]
│       ├── test_pg_search_integration.py                 [PG-FTS-1.7]
│       └── test_fts5_regression.py                       [PG-FTS-1.8]
├── api/
│   ├── utils/
│   │   └── fts5.py                                       [PG-FTS-1.2]
│   └── routers/
│       └── marketplace_catalog.py                        [PG-FTS-1.5]
```

---

## Key Architecture Decisions (Detailed)

### Decision 1: Parallel Implementation Path (Not Strategy Pattern)

**Choice:** Add `_search_tsvector()` method parallel to existing `_search_fts5()` and `_search_like()` methods in `MarketplaceCatalogRepository`.

**Rationale:**
- YAGNI (You Aren't Gonna Need It) — feature is unlikely to expand to other backends in near future
- Explicit is better than implicit — readers can easily see the three search paths branching in `search()` method
- No abstraction overhead — each method is ~100 lines, clear and straightforward
- Easy to test — each method is independently testable
- Easy to maintain — changes to tsvector logic don't risk FTS5 or LIKE paths

**Trade-off:** Three similar methods slightly violate DRY. But the cost of a strategy pattern is higher than the cost of duplication here.

### Decision 2: Trigger-Based tsvector Updates

**Choice:** Use PostgreSQL trigger to automatically update `search_vector` column on INSERT/UPDATE.

**Rationale:**
- Automatic sync — no application-layer coordination needed
- Consistent — trigger always fires, impossible to forget to update
- Low latency — happens in database, no round-trip
- Acceptable overhead — catalog inserts are infrequent (batch syncs)

**Trade-off:** Trigger logic is in SQL (hard to version-control and test in isolation). But migration (PG-FTS-1.1) is comprehensive and includes downgrade path.

### Decision 3: Weight Mapping Strategy

**Choice:** Map FTS5 numeric weights (10.0, 3.0, 5.0, 2.0, 1.0) to PostgreSQL weight classes (A, B, C, D).

**Mapping:**
- title (10.0) → A
- search_tags (3.0) → B
- description (5.0) → C
- search_text + deep_search_text (2.0, 1.0) → D

**Rationale:**
- PostgreSQL only supports 4 weight classes (A-D); FTS5 supports continuous weights
- Mapping preserves intent: title > tags ≈ description > content
- Results won't be numerically identical but UX will be equivalent
- Validated via integration tests (PG-FTS-1.7)

**Trade-off:** Description and tags slightly reorder relative to FTS5 numeric weights. But the difference is imperceptible to users.

### Decision 4: Cursor Format Compatibility

**Choice:** Both FTS5 and tsvector use same cursor format: `"{relevance}:{confidence_score}:{entry_id}"`

**Rationale:**
- API consumers don't need to know which backend is active
- Pagination seamlessly works across backend transitions (if enabled in future)
- Cursor format is opaque to clients — can be updated in future without breaking API

**Trade-off:** PostgreSQL `ts_rank_cd` scores are on different scale than FTS5 BM25. But we negate both for consistency, and consumers only care about ordering (not absolute values).

---

## Next Steps After Approval

1. **Day 1-2:** Confirm enterprise-db-storage Phase 8 readiness, set up docker-compose PostgreSQL
2. **Day 3-5:** Implement PG-FTS-1.1 (migration) and PG-FTS-1.2 (backend detection) in parallel
3. **Day 6-7:** Implement PG-FTS-1.3 (model) and PG-FTS-1.4/1.5 (search logic) in parallel
4. **Day 8-10:** Implement tests (PG-FTS-1.6, 1.7, 1.8) in parallel, start integration validation
5. **Day 11-12:** Code review, regression testing, final validation against both SQLite and PostgreSQL
6. **Day 13-15:** Deploy to staging, run smoke tests, prepare production rollout
7. **Day 16+:** Monitor in production, gather performance metrics, document learnings
