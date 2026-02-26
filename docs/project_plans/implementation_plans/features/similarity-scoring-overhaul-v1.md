---
schema_version: 2
doc_type: implementation_plan
title: 'Implementation Plan: Similarity Scoring Overhaul'
status: in-progress
created: '2026-02-26'
updated: '2026-02-26'
feature_slug: similarity-scoring-overhaul
feature_version: v1
prd_ref: docs/project_plans/PRDs/features/similarity-scoring-overhaul-v1.md
plan_ref: null
scope: 3 phases fixing broken scoring algorithm, adding pre-computation cache, and
  optional embedding-based semantic matching
effort_estimate: ~5 days (18 tasks)
architecture_summary: Algorithm fixes in core/scoring, schema additions to cache/models,
  FTS5 pre-filter in SimilarityService, optional sentence-transformers via [semantic]
  extras
priority: high
risk_level: medium
category: product-planning
tags:
- implementation
- planning
- similarity
- scoring
- cache
- embeddings
- fts5
milestone: null
owner: null
contributors: []
related_documents:
- docs/project_plans/SPIKEs/similarity-scoring-overhaul-v1.md
- docs/project_plans/PRDs/features/similarity-scoring-overhaul-v1.md
files_affected:
- skillmeat/core/similarity.py
- skillmeat/core/scoring/match_analyzer.py
- skillmeat/core/scoring/text_similarity.py
- skillmeat/core/scoring/embedder.py
- skillmeat/cache/models.py
- skillmeat/cache/similarity_cache.py
- skillmeat/api/routers/artifacts.py
- skillmeat/api/schemas/artifacts.py
- skillmeat/web/hooks/use-similar-artifacts.ts
- skillmeat/web/components/collection/similar-artifacts-tab.tsx
- pyproject.toml
commit_refs: []
pr_refs: []
---

# Implementation Plan: Similarity Scoring Overhaul

**Plan ID**: `IMPL-2026-02-26-SIMILARITY-SCORING-OVERHAUL`
**Date**: 2026-02-26
**Author**: Implementation Planner
**Related Documents**:
- **SPIKE**: `docs/project_plans/SPIKEs/similarity-scoring-overhaul-v1.md`
- **PRD**: `docs/project_plans/PRDs/features/similarity-scoring-overhaul-v1.md`

**Complexity**: Large
**Total Estimated Effort**: ~5 days (18 tasks)
**Target Timeline**: 3 sequential phases, individually deployable

---

## Executive Summary

The current similarity scoring system has five structural deficiencies: description comparison uses string length ratio instead of content, title scoring uses token Jaccard that undervalues partial overlap, the semantic scorer is a non-functional placeholder returning `None`, content/structure hash fields are not persisted to the DB so `_compute_content_score()` returns 0.0 for nearly all artifacts, and every request rescores O(n) candidates live with no caching.

This plan addresses all five deficiencies across three phases. Phase 1 fixes the scoring algorithm with zero schema risk and ships independently as an immediate quality improvement. Phase 2 adds pre-computation caching using a `similarity_cache` table and SQLite FTS5 pre-filtering, making tab loads into sub-200ms cache lookups. Phase 3 adds optional `sentence-transformers` embedding support behind a `[semantic]` extras install target.

Each phase is independently deployable and produces visible value. The SPIKE (`docs/project_plans/SPIKEs/similarity-scoring-overhaul-v1.md`) recommends SQLite FTS5 for BM25 candidate pre-filtering (available in Python's standard `sqlite3`, no new dependencies) and character bigram Jaccard for name similarity (zero dependencies). scikit-learn and `rank_bm25` are explicitly NOT recommended by the SPIKE — FTS5 is preferred.

---

## Implementation Strategy

### Architecture Sequence

This feature spans the following layers in dependency order:

1. **Service Layer (Phase 1)** — Fix scoring algorithm in `core/scoring/`; no DB changes
2. **API Layer (Phase 1)** — Add `text_score` field to `SimilarityBreakdownDTO`
3. **UI Layer (Phase 1)** — Display improved scores in `similar-artifacts-tab.tsx`
4. **Database Layer (Phase 2)** — Add columns to `CollectionArtifact`; create `similarity_cache` table; create FTS5 virtual table
5. **Service Layer (Phase 2)** — `SimilarityCacheManager`, FTS5 pre-filter, cache-hit path in `SimilarityService`
6. **API Layer (Phase 2)** — Update similar endpoint to read from cache; expose cache-age header
7. **UI Layer (Phase 2)** — Cache-age indicator; invalidation on artifact edit
8. **Service Layer (Phase 3)** — `SentenceTransformerEmbedder`, provider selection, embedding storage
9. **UI Layer (Phase 3)** — Show real semantic percentage when embeddings available

### Parallel Work Opportunities

**Phase 1:**
- SSO-1.1 (create `text_similarity.py`) runs in parallel with SSO-1.2/1.3 (update `match_analyzer.py` weights)
- SSO-1.5 (frontend display) can begin once SSO-1.4 (DTO) is complete, in parallel with SSO-1.6 (tests)

**Phase 2:**
- SSO-2.1 (schema columns) and SSO-2.2 (`SimilarityCache` ORM model) can run in parallel — both write to `cache/models.py` and the migration file, but in separate sections
- SSO-2.7 (FTS5 virtual table) can be added to the same migration as SSO-2.1/2.2
- SSO-2.8 (frontend hook) runs in parallel with SSO-2.9 (tests) once SSO-2.6 is complete

**Phase 3:**
- SSO-3.1 (`SentenceTransformerEmbedder`), SSO-3.2 (pyproject.toml), and SSO-3.3 (embedding ORM table) run in parallel
- SSO-3.5 (frontend semantic display) and SSO-3.6 (tests) run in parallel once SSO-3.4 is complete

### Critical Path

```
SSO-1.1 + SSO-1.2 → SSO-1.3 → SSO-1.4 → SSO-1.5 → SSO-1.6
         ↓
SSO-2.1 + SSO-2.2 + SSO-2.7 (migration) → SSO-2.3 → SSO-2.4 → SSO-2.5 → SSO-2.6 → SSO-2.8 + SSO-2.9
         ↓
SSO-3.1 + SSO-3.2 + SSO-3.3 → SSO-3.4 → SSO-3.5 + SSO-3.6
```

Phase 2 depends on Phase 1 completion (SimilarityCacheManager uses the fixed scoring logic). Phase 3 depends on Phase 2 completion (embeddings stored in the Phase 2 ORM infrastructure).

---

## Phase Breakdown

### Phase 1: Fix Scoring Algorithm

**Duration**: ~1.5 days
**Dependencies**: None (zero schema changes)
**Goal**: Make scoring produce meaningful, differentiated results. The Similar Artifacts tab should show ranked results where name and description content actually matter.

**Key SPIKE Findings for This Phase:**
- Use character bigram Jaccard for name/title similarity (zero dependencies, robust to hyphens/underscores)
- Use SQLite FTS5 `bm25()` or a simple TF-IDF-style approach for description similarity — NOT scikit-learn (adds NumPy/SciPy footprint). A pure-Python bigram Jaccard on descriptions is acceptable fallback.
- New metadata sub-weights: tags 30%, type 15%, title bigram 25%, description content 25%, length sanity 5%
- New composite weights: keyword 25%, metadata 30%, content 20%, structure 15%, semantic 10%
- When semantic unavailable, redistribute proportionally

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| SSO-1.1 | Create text_similarity.py | New file `skillmeat/core/scoring/text_similarity.py`. Two public functions: `bigram_similarity(a, b) -> float` (character bigrams, strips hyphens/underscores, normalizes to lowercase) and `bm25_description_similarity(desc_a, desc_b) -> float` (pure-Python BM25-style TF-IDF or bigram Jaccard on description tokens — no sklearn). | Both functions return float in [0.0, 1.0]. Identical inputs return 1.0. Empty inputs return 0.0. | 2 pts | python-backend-engineer | None |
| SSO-1.2 | Fix _compute_metadata_score() | In `skillmeat/core/scoring/match_analyzer.py`: replace description length ratio with `bm25_description_similarity()` from SSO-1.1; replace title token Jaccard with `bigram_similarity()`. Rebalance sub-weights: tags=0.30, type=0.15, title_bigram=0.25, description_content=0.25, length_sanity=0.05. | Unit tests: same-description different-name artifacts score metadata >= 0.6. Same-name different-description score >= 0.4. | 2 pts | python-backend-engineer | SSO-1.1 |
| SSO-1.3 | Rebalance composite weights | In `skillmeat/core/similarity.py`: update `_WEIGHTS` dict to keyword=0.25, metadata=0.30, content=0.20, structure=0.15, semantic=0.10. Update fallback redistribution (when semantic=None) to proportionally redistribute the 0.10 semantic weight: keyword=0.278, metadata=0.333, content=0.222, structure=0.167. | Composite scores sum to 1.0. Fallback scores also sum to 1.0. Scores are differentiated for artifacts with similar names. | 1 pt | python-backend-engineer | SSO-1.2 |
| SSO-1.4 | Add text_score to DTO | In `skillmeat/api/schemas/artifacts.py`: add optional `text_score: Optional[float] = None` field to `SimilarityBreakdownDTO`. In `skillmeat/api/routers/artifacts.py`: populate `text_score` from the scoring result. Ensure backward compatibility (existing clients receiving `null` for text_score are unaffected). | API response for similar endpoint includes `text_score` field. Field is non-null when scoring runs. Existing fields unchanged. | 1 pt | python-backend-engineer | SSO-1.3 |
| SSO-1.5 | Update frontend score display | In `skillmeat/web/components/collection/similar-artifacts-tab.tsx`: display `text_score` as "Text" in the score breakdown when present. Keep showing "N/A" for semantic when null. Ensure layout handles up to 5 score dimensions gracefully. | Score breakdown shows "Text: XX%" when text_score is non-null. Semantic still shows "N/A" when null. No layout breakage. | 1 pt | ui-engineer-enhanced | SSO-1.4 |
| SSO-1.6 | Write Phase 1 tests | New `tests/test_text_similarity.py`: test `bigram_similarity()` and `bm25_description_similarity()` for identical, partial overlap, empty, and hyphenated inputs. Add/update `tests/test_match_analyzer.py`: verify rebalanced metadata sub-weights produce correct relative rankings. | All new tests pass. Existing `test_match_analyzer.py` tests continue to pass. No regressions. | 2 pts | python-backend-engineer | SSO-1.1, SSO-1.3 |

**Phase 1 Quality Gates:**
- [ ] Similar artifacts tab shows differentiated, meaningful results — same-type artifacts with related names rank above unrelated ones
- [ ] Description content matters: artifacts with identical descriptions rank highly regardless of name differences
- [ ] Name similarity is prominent: `canvas-design` and `canvas-layout` rank higher than unrelated artifacts
- [ ] All existing similarity tests pass after scoring changes
- [ ] No new Python package dependencies added in Phase 1

---

### Phase 2: Schema + Pre-computation Cache

**Duration**: ~2.5 days
**Dependencies**: Phase 1 complete
**Goal**: Pre-compute similarity at sync/import time so tab loads become cache lookups. Target: <200ms response from cache, <1s incremental update for single artifact.

**Key SPIKE Findings for This Phase:**
- SQLite FTS5 is available in Python's standard `sqlite3` module — use it for BM25 pre-filtering, not a separate package
- `similarity_cache` table stores top-20 per artifact (O(n) storage, not O(n²))
- Cache invalidation: when `refresh_single_artifact_cache()` runs for artifact X, delete all rows where `source_artifact_uuid = X` or `target_artifact_uuid = X`
- FTS5 virtual table needs `artifact_uuid UNINDEXED, name, title, description, tags` columns with `tokenize='porter ascii'`
- SQLite `batch_alter_operations` mode required for Alembic migrations (SQLite ALTER TABLE limitations)
- Check FTS5 availability at startup: `sqlite3 :memory: "SELECT fts5()"` — log warning and skip pre-filter if unavailable

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| SSO-2.1 | Add fingerprint columns to CollectionArtifact | In `skillmeat/cache/models.py`: add `artifact_content_hash: Mapped[Optional[str]]`, `artifact_structure_hash: Mapped[Optional[str]]`, `artifact_file_count: Mapped[int]` (default 0), `artifact_total_size: Mapped[int]` (default 0) to `CollectionArtifact`. These are distinct from the existing `content_hash` which is for context entities. Create Alembic migration using `batch_alter_table` mode for SQLite compatibility. | Migration runs cleanly via `alembic upgrade head` against existing DB. New columns exist with correct defaults. No existing rows broken. | 2 pts | data-layer-expert | Phase 1 complete |
| SSO-2.2 | Create SimilarityCache ORM model | In `skillmeat/cache/models.py`: add `SimilarityCache` ORM model with columns: `source_artifact_uuid TEXT PK`, `target_artifact_uuid TEXT PK`, `composite_score REAL`, `breakdown_json TEXT`, `computed_at DATETIME DEFAULT CURRENT_TIMESTAMP`. Composite primary key `(source_artifact_uuid, target_artifact_uuid)`. Index on `(source_artifact_uuid, composite_score DESC)`. FK cascade deletes on both UUID columns. Add to Alembic migration from SSO-2.1. | ORM model maps correctly. Migration creates table with indexes. Cascade deletes verified: deleting an artifact removes its cache rows. | 2 pts | data-layer-expert | SSO-2.1 |
| SSO-2.3 | Create SimilarityCacheManager | New file `skillmeat/cache/similarity_cache.py`. Class `SimilarityCacheManager` with methods: `get_similar(artifact_uuid, limit=20, min_score=0.0) -> list[dict]` (cache lookup, returns empty list on miss), `compute_and_store(artifact_uuid, session)` (compute top-20 similar using Phase 1 scoring + FTS5 pre-filter, persist to `SimilarityCache`), `invalidate(artifact_uuid, session)` (delete all rows for artifact), `rebuild_all(session)` (full matrix recompute). FTS5 pre-filter reduces candidates to top-50 before full scoring. | `get_similar()` returns cached results in <10ms when cache is warm. `compute_and_store()` persists exactly top-20 rows. `invalidate()` removes all rows for artifact. Unit tests for all four methods. | 3 pts | python-backend-engineer | SSO-2.2 |
| SSO-2.4 | Populate fingerprint columns at sync/import | In `skillmeat/core/similarity.py` and the cache refresh path (find where `populate_collection_artifact_from_import()` is called): compute and persist `artifact_content_hash`, `artifact_structure_hash`, `artifact_file_count`, `artifact_total_size` from filesystem when available. Update `_fingerprint_from_row()` in `SimilarityService` to read these fields from `CollectionArtifact` rather than the always-empty `Artifact` fields. | Diagnostic query `SELECT COUNT(*), COUNT(artifact_content_hash) FROM collection_artifacts` shows non-zero populated count after a sync. `_compute_content_score()` returns > 0 for artifacts with matching content. | 3 pts | python-backend-engineer | SSO-2.2 |
| SSO-2.5 | Wire cache invalidation into refresh flow | In `skillmeat/core/similarity.py`: after `refresh_single_artifact_cache()` completes for artifact X, call `SimilarityCacheManager.invalidate(X)` and then schedule (or directly call) `SimilarityCacheManager.compute_and_store(X)` to rebuild cache incrementally. Invalidation must run before the next HTTP response for that artifact. | Cache is stale immediately after sync. First request after sync triggers recompute. Second request returns cached result (verifiable via response timing or logging). Incremental update for single artifact < 1s. | 2 pts | python-backend-engineer | SSO-2.3, SSO-2.4 |
| SSO-2.6 | Update similar endpoint to read from cache | In `skillmeat/api/routers/artifacts.py`: update `GET /api/v1/artifacts/{id}/similar` to call `SimilarityCacheManager.get_similar()` first. If cache hit, return immediately. If cache miss, fall back to live computation via existing `SimilarityService`, then persist results via `compute_and_store()`. Return `X-Cache: HIT` or `X-Cache: MISS` and `X-Cache-Age: <seconds>` response headers. | Cached responses return in < 200ms. Cache miss falls back to live computation. Response headers present on all responses. API contract unchanged (same response body shape). | 2 pts | python-backend-engineer | SSO-2.5 |
| SSO-2.7 | Add FTS5 virtual table migration | Add to the Phase 2 Alembic migration: create FTS5 virtual table `artifact_fts` with columns `artifact_uuid UNINDEXED, name, title, description, tags` and `tokenize='porter ascii'`. Add raw SQL migration step (not ORM — FTS5 requires `CREATE VIRTUAL TABLE`). Populate on migration from existing artifact data. Add FTS5 availability check to `SimilarityService.__init__()` with graceful fallback. | FTS5 table exists after migration. `SELECT artifact_uuid FROM artifact_fts WHERE artifact_fts MATCH 'canvas' LIMIT 5` returns results. Availability check logs a warning and skips pre-filter when FTS5 is unavailable. | 2 pts | data-layer-expert | SSO-2.2 |
| SSO-2.8 | Update frontend hook and cache indicator | In `skillmeat/web/hooks/use-similar-artifacts.ts`: handle `X-Cache` and `X-Cache-Age` response headers; expose `cacheStatus` and `cacheAgeSeconds` from the hook. In `skillmeat/web/components/collection/similar-artifacts-tab.tsx`: show a subtle cache-age indicator (e.g., "cached 2m ago") when `cacheStatus === 'HIT'`. Invalidate React Query cache on artifact edit events. | Cache age shows in UI when data is from cache. Indicator disappears when `cacheStatus === 'MISS'` (live computation). Stale time remains 30s per existing data-flow patterns. | 2 pts | ui-engineer-enhanced | SSO-2.6 |
| SSO-2.9 | Write Phase 2 tests | New `tests/test_similarity_cache.py`: test `SimilarityCacheManager` methods (cache hit, cache miss, invalidation, rebuild). Integration test: cache miss triggers computation and subsequent call is cache hit. Migration test: run migration against a fixture DB and verify schema. Test `_compute_content_score()` returns > 0 when fingerprint columns are populated. | All tests pass. Cache hit/miss behavior verified. Migration runs cleanly on fixture DB. No regressions. | 2 pts | python-backend-engineer | SSO-2.6 |

**Phase 2 Quality Gates:**
- [ ] Tab loads in < 200ms from cache for warm cache
- [ ] Cache rebuilds in < 60s for 1000 artifacts (full rebuild)
- [ ] Incremental update for single artifact < 1s
- [ ] `_compute_content_score()` returns > 0 for artifacts with shared content hashes
- [ ] FTS5 pre-filter reduces full-score computation from O(n) to O(50) candidates
- [ ] Alembic migration runs cleanly against existing DB with no data loss
- [ ] `X-Cache` response headers present on all `/similar` responses

---

### Phase 3: Optional Embedding Enhancement

**Duration**: ~1 day
**Dependencies**: Phase 2 complete
**Goal**: Replace non-functional `HaikuEmbedder` with local `sentence-transformers`. Purely optional — system must work identically without it.

**Key SPIKE Findings for This Phase:**
- `all-MiniLM-L6-v2` model: 80MB download, 384 dimensions, sub-ms CPU inference after load
- Existing `HaikuEmbedder` embedding cache infrastructure (`~/.skillmeat/embeddings.db`) can be reused — no cache schema changes needed
- Anthropic does not expose an embedding API as of February 2026; rename `HaikuEmbedder` to `AnthropicEmbedder` and set `is_available()` to return `False` with clear docstring
- Provider selection order: `SentenceTransformerEmbedder` first (if installed), then `AnthropicEmbedder` (always False currently), then None (keyword-only fallback)
- Use thread executor in `get_embedding()` to avoid blocking the event loop

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| SSO-3.1 | Create SentenceTransformerEmbedder | New file `skillmeat/core/scoring/embedder.py`. Class `SentenceTransformerEmbedder` implementing the existing `EmbeddingProvider` interface: `is_available() -> bool` (returns True only when `sentence_transformers` importable), `get_embedding(text: str) -> Optional[List[float]]` (uses thread executor, returns 384-dim vector). Lazy model loading: model loads on first `get_embedding()` call, not at import. Also update `haiku_embedder.py`: rename class to `AnthropicEmbedder`, set `is_available()` to return `False` with docstring "Anthropic does not expose an embedding API as of 2026-02". | `is_available()` returns True when `sentence_transformers` installed, False when not. Two identical texts produce cosine similarity of 1.0. Model loads lazily. `AnthropicEmbedder.is_available()` always returns False. | 2 pts | ai-engineer | Phase 2 complete |
| SSO-3.2 | Add [semantic] optional dependency | In `pyproject.toml`: add `[project.optional-dependencies]` section with `semantic = ["sentence-transformers>=2.7.0"]`. Verify `pip install skillmeat[semantic]` installs the package and `SentenceTransformerEmbedder.is_available()` returns True after install. | `pip install skillmeat[semantic]` succeeds. `pip install skillmeat` (without extras) does not install sentence-transformers. `is_available()` correctly reflects install state. | 0.5 pts | python-backend-engineer | SSO-3.1 |
| SSO-3.3 | Add embedding storage table | In `skillmeat/cache/models.py`: add `ArtifactEmbedding` ORM model with columns: `artifact_uuid TEXT PK`, `embedding BLOB`, `model_name TEXT`, `embedding_dim INTEGER`, `computed_at DATETIME`. FK to artifacts(uuid) with cascade delete. New Alembic migration. Note: reuse the existing embeddings cache pattern from `~/.skillmeat/embeddings.db` if already storing embeddings there — check existing `HaikuEmbedder` cache path before adding a new table. | ORM model maps correctly. Migration creates table. Embeddings can be stored and retrieved as binary blobs. Cascade delete removes embeddings when artifact deleted. | 2 pts | data-layer-expert | SSO-3.1 |
| SSO-3.4 | Integrate embedder into SimilarityCacheManager | In `skillmeat/cache/similarity_cache.py`: update `compute_and_store()` to call `SentenceTransformerEmbedder.get_embedding()` when available. Store embedding in `ArtifactEmbedding` table (or retrieve if already computed). Compute cosine similarity between stored embeddings. Populate `breakdown_json` with semantic score. Recompute composite score using the full weights (with semantic=0.10) when embeddings are available. Update `SimilarityService.__init__()` to try `SentenceTransformerEmbedder` before `AnthropicEmbedder` in provider selection chain. | When `sentence_transformers` installed: composite scores include semantic component. When not installed: system uses fallback weights identically to Phase 2. Embedding computation runs in thread executor (non-blocking). | 2 pts | python-backend-engineer | SSO-3.2, SSO-3.3 |
| SSO-3.5 | Update frontend semantic display | In `skillmeat/web/components/collection/similar-artifacts-tab.tsx`: show semantic score as actual percentage (e.g., "Semantic: 73%") when non-null. Add a small indicator/tooltip showing "Embeddings: enabled" or "Embeddings: not installed" based on a new API field. Keep "N/A" display when semantic score is null (no embeddings installed). | Semantic score shows real percentage when enabled. "N/A" shows when not enabled. Indicator communicates embedding availability without being intrusive. | 1 pt | ui-engineer-enhanced | SSO-3.4 |
| SSO-3.6 | Write Phase 3 tests | New `tests/test_embedder.py`: test `SentenceTransformerEmbedder.is_available()` for both install states (mock importlib). Test `get_embedding()` with mock model (do not download real model in CI). Test `AnthropicEmbedder.is_available()` always returns False. Test composite score computation with and without embeddings in `SimilarityCacheManager`. | All tests pass without requiring `sentence_transformers` to be installed. Mocking pattern allows CI to test embedding code paths. No regressions. | 2 pts | python-backend-engineer | SSO-3.4 |

**Phase 3 Quality Gates:**
- [ ] `pip install skillmeat[semantic]` enables embedding-based scoring without any other changes
- [ ] `pip install skillmeat` (without extras) works identically to Phase 2
- [ ] Semantic score shows real percentages in UI when embeddings are enabled
- [ ] First request after startup incurs model load (~1s), subsequent requests complete < 50ms
- [ ] Phase 3 tests pass in CI without `sentence_transformers` installed (via mocking)

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|---------------------|
| FTS5 not available in deployed Python build | High — Phase 2 pre-filter fails | Low — standard in CPython 3.6+ | Check `sqlite3.sqlite_version` at startup; log warning and skip pre-filter, fall back to full O(n) scan |
| Alembic migration fails on SQLite ALTER TABLE | High — migration blocked | Medium — SQLite has ADD limitations | Use `batch_alter_table` mode for all column additions; test against fixture DB before merging |
| Fingerprint population rate near 0% post-migration | Medium — content scoring stays broken | Medium — possible pipeline bug | Run diagnostic query `SELECT COUNT(*), COUNT(artifact_content_hash) FROM collection_artifacts` before Phase 2 work; fix pipeline bug first if needed |
| `similarity_cache` grows unbounded | Low — SQLite size impact | Low — max 20 rows per artifact = O(n) | Add periodic cleanup based on `computed_at` as a follow-up; cap cache at 20 rows per artifact in `compute_and_store()` |
| sentence-transformers model download blocks startup | Medium — UX degradation | Low — only on first use with [semantic] | Lazy-load model: only download on first `get_embedding()` call; log informational message on first load |
| BM25/bigram over-scores domain stop-words | Medium — noisy top results | Medium — "skill", "tool", "command" are common | Add small stop-word list for domain-specific common words in `text_similarity.py`; include in SSO-1.1 acceptance criteria |
| Phase 2 migration breaks existing data | High — data loss | Low — only adds columns/tables | Use `IF NOT EXISTS` and column defaults; test migration against real-world fixture DB in CI |
| Content hash fields populated incorrectly | Medium — wrong scores | Medium — fingerprint computation bugs | Add unit tests for fingerprint field population; log which fields are populated vs. empty at debug level |

### Schedule Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|---------------------|
| Phase 2 Alembic complexity exceeds estimate | Medium — schedule slip | Medium — FTS5 virtual table via raw SQL is unusual | Spike the FTS5 migration separately if needed; FTS5 can be added as a follow-up if it blocks Phase 2 delivery |
| Phase 1 scoring regression discovered in testing | High — must fix before merge | Low — algorithm changes are isolated | SSO-1.6 tests run before merge; existing tests are the regression gate |
| Phase 3 CI setup for mocked embeddings is complex | Low — test quality only | Low — standard mock patterns | Use `unittest.mock.patch('sentence_transformers.SentenceTransformer', ...)` pattern; defer if complex |

---

## Resource Requirements

### Team Composition

- **python-backend-engineer**: SSO-1.1, 1.2, 1.3, 1.4, 1.6, 2.3, 2.4, 2.5, 2.6, 2.9, 3.2, 3.4, 3.6
- **data-layer-expert**: SSO-2.1, 2.2, 2.7, 3.3
- **ui-engineer-enhanced**: SSO-1.5, 2.8, 3.5
- **ai-engineer**: SSO-3.1

### Skill Requirements

- Python, SQLAlchemy ORM, Alembic migrations (SQLite batch mode)
- SQLite FTS5 virtual tables, raw SQL in Alembic
- FastAPI routers, Pydantic schemas
- React, TypeScript, React Query
- `sentence-transformers` library (Phase 3 only)

---

## Success Metrics

### Phase 1 Success
- Similar artifacts tab shows differentiated results — "canvas-design" artifact ranks related canvas artifacts above unrelated ones
- Description content matters in scoring: same-description artifacts score >= 0.6 in metadata_score
- Zero new Python dependencies added

### Phase 2 Success
- API response time for `/similar` endpoint: < 200ms (cached), < 2s (first compute)
- Cache rebuild for 1000 artifacts: < 60s
- Incremental cache update for single artifact: < 1s
- `_compute_content_score()` returns > 0 for at least 50% of synced artifacts (content hash populated)

### Phase 3 Success
- `pip install skillmeat[semantic]` enables semantic scoring without code changes
- Semantic scores show real percentages in the Similar Artifacts tab
- CI tests pass without `sentence_transformers` installed

### Overall Success
- All five SPIKE-identified deficiencies addressed
- No regression: artifacts that previously returned non-zero similarity scores continue to do so
- All existing similarity unit tests pass

---

## Post-Implementation Notes

### Follow-up ADRs Recommended (from SPIKE)

1. **ADR-SSO-001: SQLite FTS5 as Similarity Pre-Filter** — Document the FTS5 vs. in-memory BM25 tradeoff decision
2. **ADR-SSO-002: Embedding Provider Strategy** — Document `sentence-transformers` as default, cloud APIs as opt-in
3. **ADR-SSO-003: Similarity Cache Invalidation Policy** — Document event-driven invalidation over TTL-based

### Known Follow-up Work

- FTS5 virtual table sync: SQLite FTS5 does not auto-sync from parent tables. The current design rebuilds FTS5 entries during `refresh_single_artifact_cache()`. A more robust trigger-based approach is deferred to a follow-up.
- Cache size management: Phase 2 caps cache at 20 results per artifact but has no TTL-based eviction. A periodic cleanup job is deferred.
- OpenAI/Cohere embedding provider: Phase 3 only ships `SentenceTransformerEmbedder`. Cloud embedding providers are deferred behind a settings-based opt-in.

---

## Parallelization Reference

```yaml
phase: 1
batches:
  batch_1:
    - SSO-1.1  # text_similarity.py (python-backend-engineer)
    - SSO-1.2  # match_analyzer.py metadata weights (python-backend-engineer) -- NOTE: wait for SSO-1.1
  batch_2:
    - SSO-1.3  # composite weights (python-backend-engineer)
  batch_3:
    - SSO-1.4  # DTO text_score (python-backend-engineer)
  batch_4:
    - SSO-1.5  # frontend display (ui-engineer-enhanced)
    - SSO-1.6  # tests (python-backend-engineer)

phase: 2
batches:
  batch_1:
    - SSO-2.1  # CollectionArtifact columns + migration (data-layer-expert)
    - SSO-2.7  # FTS5 virtual table (data-layer-expert) -- add to same migration
  batch_2:
    - SSO-2.2  # SimilarityCache ORM model (data-layer-expert) -- add to same migration
  batch_3:
    - SSO-2.3  # SimilarityCacheManager (python-backend-engineer)
    - SSO-2.4  # populate fingerprint columns (python-backend-engineer)
  batch_4:
    - SSO-2.5  # wire cache invalidation (python-backend-engineer)
  batch_5:
    - SSO-2.6  # update similar endpoint (python-backend-engineer)
  batch_6:
    - SSO-2.8  # frontend hook + cache indicator (ui-engineer-enhanced)
    - SSO-2.9  # tests (python-backend-engineer)

phase: 3
batches:
  batch_1:
    - SSO-3.1  # SentenceTransformerEmbedder + rename AnthropicEmbedder (ai-engineer)
    - SSO-3.2  # pyproject.toml [semantic] extras (python-backend-engineer)
    - SSO-3.3  # ArtifactEmbedding ORM table (data-layer-expert)
  batch_2:
    - SSO-3.4  # integrate embedder into SimilarityCacheManager (python-backend-engineer)
  batch_3:
    - SSO-3.5  # frontend semantic display (ui-engineer-enhanced)
    - SSO-3.6  # tests (python-backend-engineer)
```

---

**Progress Tracking**: See `.claude/progress/similarity-scoring-overhaul/` (create via artifact-tracking skill)

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-02-26
