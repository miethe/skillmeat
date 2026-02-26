---
type: context
prd: "similarity-scoring-overhaul"
title: "Similarity Scoring Overhaul - Development Context"
status: "active"
created: "2026-02-26"
updated: "2026-02-26"
critical_notes_count: 3
implementation_decisions_count: 0
active_gotchas_count: 0
agent_contributors: []
agents: []
---

# Similarity Scoring Overhaul - Development Context

**Status**: Active Development (Planning Phase)
**Created**: 2026-02-26
**Last Updated**: 2026-02-26

> **Purpose**: This is a shared worknotes file for all AI agents working on the Similarity Scoring Overhaul feature. Add brief observations, decisions, gotchas, and implementation notes that future agents should know. Think of this as a sticky-note pad for the development team.

---

## Quick Reference

**Related Files**:
- **PRD**: `docs/project_plans/PRDs/features/similarity-scoring-overhaul-v1.md`
- **Implementation Plan**: `docs/project_plans/implementation_plans/features/similarity-scoring-overhaul-v1.md`
- **SPIKE**: `docs/project_plans/SPIKEs/similarity-scoring-overhaul-v1.md`
- **Progress Tracking**: `.claude/progress/similarity-scoring-overhaul/phase-{1,2,3}-progress.md`

**Feature Overview**: Three-phase overhaul of broken similarity scoring system. Phase 1 fixes algorithms (0 schema changes), Phase 2 adds caching with FTS5 pre-filter, Phase 3 adds optional embedding support.

**Critical Timeline**: ~5 days total (18 tasks across 3 phases)

---

## Five Root Cause Deficiencies (from SPIKE)

These are the core problems being addressed:

1. **Description Comparison by Length**: Current code uses string length ratio instead of content similarity. Fix: Use BM25-style TF-IDF or bigram Jaccard on description tokens (Phase 1)

2. **Title Scoring via Token Jaccard**: Token-level Jaccard undervalues partial overlap (e.g., `canvas-design` vs `canvas-layout`). Fix: Use character bigram Jaccard instead (Phase 1)

3. **Semantic Scorer is Non-Functional Placeholder**: `HaikuEmbedder` returns `None` unconditionally. Fix: Replace with `SentenceTransformerEmbedder` using `all-MiniLM-L6-v2` model (Phase 3)

4. **Content/Structure Hashes Not Persisted**: `_compute_content_score()` reads from always-empty `Artifact` fields. Fix: Add columns to `CollectionArtifact` and populate at sync/import time (Phase 2)

5. **Live O(n) Rescoring per Request**: Every Similar Artifacts request rescores all candidates with no caching. Fix: Pre-compute top-20 at sync time, serve from `similarity_cache` table (Phase 2)

---

## Architecture Summary

### Phase 1: Fix Scoring Algorithm (~1.5 days)

**Goal**: Meaningful, differentiated results. No schema changes.

**Key Changes**:
- New `skillmeat/core/scoring/text_similarity.py` with two functions:
  - `bigram_similarity(a, b) -> float`: Character bigram Jaccard for titles/names
  - `bm25_description_similarity(desc_a, desc_b) -> float`: BM25-style or bigram TF-IDF for descriptions
- Update `_compute_metadata_score()` in `match_analyzer.py` to use these functions
- Rebalance composite weights: keyword=0.25, metadata=0.30, content=0.20, structure=0.15, semantic=0.10
- Add `text_score` field to `SimilarityBreakdownDTO`
- Update UI to display `text_score` in breakdown

**Critical Constraint**: Zero new Python dependencies. Use only standard library.

**Tests**:
- `tests/test_text_similarity.py`: Test both similarity functions
- Update `tests/test_match_analyzer.py`: Verify new weights produce correct rankings

---

### Phase 2: Schema + Pre-computation Cache (~2.5 days)

**Goal**: Cache hits in <200ms, full rebuild in <60s for 1000 artifacts.

**Key Changes**:
- Add columns to `CollectionArtifact`: `artifact_content_hash`, `artifact_structure_hash`, `artifact_file_count`, `artifact_total_size`
- Create `SimilarityCache` ORM model: (source_uuid, target_uuid) PK, composite_score, breakdown_json, computed_at
- Create `SimilarityCacheManager` class with methods: `get_similar()`, `compute_and_store()`, `invalidate()`, `rebuild_all()`
- Add FTS5 virtual table `artifact_fts` with columns: artifact_uuid UNINDEXED, name, title, description, tags (tokenizer: porter ascii)
- Update `GET /api/v1/artifacts/{id}/similar` to read cache first, return `X-Cache` headers
- Populate fingerprint columns during `refresh_single_artifact_cache()` flow
- Wire cache invalidation: when artifact X refreshes, delete + recompute cache for X

**Alembic Migration**: Use `batch_alter_table` mode for SQLite compatibility. FTS5 table created via raw SQL.

**FTS5 Pre-filter**: Reduces full-score computation from O(n) to ~50 candidates via BM25 ranking.

**Tests**:
- `tests/test_similarity_cache.py`: Cache hit/miss, invalidation, rebuild
- Integration test: Migration runs cleanly on fixture DB
- Verify fingerprint population: diagnostic query shows non-zero counts

---

### Phase 3: Optional Embedding Enhancement (~1 day)

**Goal**: Enable semantic scoring via optional `[semantic]` extras. System must work identically without it.

**Key Changes**:
- Create `SentenceTransformerEmbedder` in `skillmeat/core/scoring/embedder.py`
  - Uses `all-MiniLM-L6-v2` model (384-dim, sub-ms inference)
  - Lazy loads on first `get_embedding()` call
  - Returns True from `is_available()` only if `sentence_transformers` importable
- Rename `HaikuEmbedder` to `AnthropicEmbedder`, set `is_available()` to return False
- Add `ArtifactEmbedding` ORM table: artifact_uuid, embedding BLOB, model_name, embedding_dim, computed_at
- Integrate embedder into `SimilarityCacheManager`: compute embeddings when available, store, use full weights
- Add `[semantic]` optional dependency to `pyproject.toml`
- Update UI to show real semantic percentages (not "N/A") when enabled

**Provider Selection Order**: `SentenceTransformerEmbedder` → `AnthropicEmbedder` → None (fallback)

**Tests**:
- Mock `sentence_transformers.SentenceTransformer` in CI so tests pass without package installed
- Test `is_available()` for both install states
- Test composite scores with/without embeddings

---

## Critical Implementation Notes

### Text Similarity (Phase 1)

**Bigram Similarity for Titles**:
- Use character bigrams (not word bigrams) to handle hyphenated names
- Strip hyphens/underscores before comparison: `canvas-design` → `canvas_design` → bigrams
- Handle empty strings: return 0.0
- Return value: float in [0.0, 1.0]

**BM25-Style Description Similarity**:
- Option 1: Pure-Python BM25 using term frequencies (no sklearn, no rank_bm25 package)
- Option 2: Character bigram Jaccard on description tokens (simpler, still effective)
- SPIKE recommends simplicity over perfect BM25 — either approach acceptable
- Handle empty descriptions gracefully
- Return value: float in [0.0, 1.0]

**Weight Redistribution Logic**:
- When semantic=None (unavailable), redistribute the 0.10 semantic weight proportionally:
  - keyword: 0.25 → 0.25 / 0.90 = 0.278
  - metadata: 0.30 → 0.30 / 0.90 = 0.333
  - content: 0.20 → 0.20 / 0.90 = 0.222
  - structure: 0.15 → 0.15 / 0.90 = 0.167
- Verify all weights sum to 1.0 in unit tests

### Schema & Caching (Phase 2)

**Fingerprint Columns**:
- `artifact_content_hash`: SHA256 or MD5 of artifact content
- `artifact_structure_hash`: SHA256 or MD5 of directory structure
- `artifact_file_count`: Total files in artifact
- `artifact_total_size`: Total bytes
- Populated from filesystem during sync/import
- Used by `_compute_content_score()` instead of always-empty `Artifact` fields

**Cache Invalidation Strategy**:
- After `refresh_single_artifact_cache(artifact_uuid, session)`:
  1. Call `SimilarityCacheManager.invalidate(artifact_uuid, session)`
  2. Call `SimilarityCacheManager.compute_and_store(artifact_uuid, session)`
  3. Do not wait for full rebuild — invalidate + queue incremental recompute
- Cache is stale immediately after sync; first request triggers recompute; second request hits cache

**FTS5 Availability**:
- Check at startup: `sqlite3.execute("SELECT fts5()")`
- If unavailable: log warning, skip FTS5 pre-filter, fall back to full O(n) scan
- Pre-filter reduces candidates to ~50 before full scoring

**Response Headers**:
- `X-Cache: HIT` or `X-Cache: MISS`
- `X-Cache-Age: <seconds>` (time since computed_at)
- Present on all `/similar` responses

### Embeddings (Phase 3)

**Model Selection**:
- `all-MiniLM-L6-v2` from HuggingFace
- 384-dimensional vectors
- ~80MB download (cached in `~/.cache/huggingface/`)
- First inference takes ~1s (model load), subsequent < 50ms

**Lazy Loading**:
- Model loads on first `get_embedding()` call, not at import
- Use thread executor to avoid blocking async event loop
- Log informational message on first load

**Composite Weights with Embeddings**:
- When `SentenceTransformerEmbedder.is_available()` returns True:
  - Use full weights: keyword=0.25, metadata=0.30, content=0.20, structure=0.15, semantic=0.10
- When False:
  - Use fallback weights (see above): keyword=0.278, metadata=0.333, content=0.222, structure=0.167

---

## Key Files & Locations

| File | Purpose | Phase | Touch? |
|------|---------|-------|--------|
| `skillmeat/core/scoring/text_similarity.py` | Two similarity functions | 1 | Create new |
| `skillmeat/core/scoring/match_analyzer.py` | Update `_compute_metadata_score()` | 1 | Edit |
| `skillmeat/core/similarity.py` | Rebalance composite weights, update fallback logic | 1,2 | Edit |
| `skillmeat/api/schemas/artifacts.py` | Add `text_score` to DTO | 1 | Edit |
| `skillmeat/api/routers/artifacts.py` | Populate `text_score`, wire cache lookup | 1,2 | Edit |
| `skillmeat/web/components/collection/similar-artifacts-tab.tsx` | Display `text_score`, cache age indicator | 1,2,3 | Edit |
| `skillmeat/cache/models.py` | Add fingerprint columns, `SimilarityCache`, `ArtifactEmbedding` | 2,3 | Edit |
| `skillmeat/cache/similarity_cache.py` | New `SimilarityCacheManager` class | 2 | Create new |
| `skillmeat/core/scoring/embedder.py` | Create `SentenceTransformerEmbedder` | 3 | Create new |
| `skillmeat/core/scoring/haiku_embedder.py` | Rename to `AnthropicEmbedder`, update logic | 3 | Edit |
| `pyproject.toml` | Add `[semantic]` optional dependency | 3 | Edit |
| `skillmeat/web/hooks/use-similar-artifacts.ts` | Handle cache headers | 2 | Edit |
| `alembic/versions/` | Migrations for Phase 2 & 3 | 2,3 | Create |
| `tests/test_text_similarity.py` | Phase 1 unit tests | 1 | Create new |
| `tests/test_similarity_cache.py` | Phase 2 unit tests | 2 | Create new |
| `tests/test_embedder.py` | Phase 3 unit tests (with mocking) | 3 | Create new |

---

## Known Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|-----------|
| FTS5 not available in deployed Python | High | Low | Check at startup, graceful fallback to O(n) |
| Alembic migration fails on SQLite | High | Medium | Use batch_alter_table; test against fixture DB |
| Fingerprint population rate ~0% | Medium | Medium | Diagnostic query before Phase 2; fix pipeline bug if needed |
| BM25 over-scores domain stop-words | Medium | Medium | Add small stop-word list in text_similarity.py |
| Phase 2 migration breaks existing data | High | Low | Use IF NOT EXISTS, column defaults; test with real DB |
| Content hash fields populated incorrectly | Medium | Medium | Unit tests for fingerprint population; debug logs |
| sentence-transformers model download blocks startup | Medium | Low | Lazy load + thread executor; log when first load occurs |

---

## Testing Strategy

### Phase 1 Tests
- `test_bigram_similarity()`: Identical, partial overlap, empty, hyphenated inputs
- `test_bm25_description_similarity()`: Identical, partial overlap, empty inputs
- `test_metadata_score_rebalance()`: Verify new weights produce correct relative rankings

### Phase 2 Tests
- `test_cache_hit()`: Warm cache returns < 10ms
- `test_cache_miss()`: Missing cache triggers live computation
- `test_cache_invalidation()`: Deleting artifact removes cache rows
- `test_migration()`: Alembic migration runs cleanly
- `test_fingerprint_population()`: Diagnostic query shows non-zero count

### Phase 3 Tests
- `test_sentence_transformer_available()`: Returns True when installed
- `test_sentence_transformer_unavailable()`: Returns False when not installed (via mock)
- `test_anthropic_embedder_always_false()`: Always returns False
- `test_composite_scores_with_embeddings()`: Full weights when available
- `test_composite_scores_without_embeddings()`: Fallback weights when unavailable
- All tests use mocking to avoid downloading model in CI

---

## Integration Points

### Phase 1 → Phase 2
- Phase 2's `SimilarityCacheManager` uses the Phase 1 fixed scoring logic
- No breaking changes; Phase 1 ships independently

### Phase 2 → Phase 3
- Phase 3's `SentenceTransformerEmbedder` stores embeddings in Phase 2's `ArtifactEmbedding` table
- Cache invalidation from Phase 2 works unchanged

### Frontend Integration
- Phase 1: Display `text_score` in breakdown
- Phase 2: Show cache-age indicator, invalidate on artifact edit
- Phase 3: Show real semantic percentages, embedding availability

---

## References

**Related Planning Documents**:
- SPIKE: `docs/project_plans/SPIKEs/similarity-scoring-overhaul-v1.md` (analysis & code examples)
- PRD: `docs/project_plans/PRDs/features/similarity-scoring-overhaul-v1.md` (requirements & success metrics)
- Implementation Plan: `docs/project_plans/implementation_plans/features/similarity-scoring-overhaul-v1.md` (detailed breakdown)

**Existing Codebase References**:
- `skillmeat/core/similarity.py` — Main SimilarityService (80+ lines)
- `skillmeat/core/scoring/match_analyzer.py` — Scoring logic (~200 lines)
- `skillmeat/core/scoring/haiku_embedder.py` — Existing embedder (rename + fix)
- `skillmeat/cache/models.py` — ORM models (add columns + tables)
- `skillmeat/api/routers/artifacts.py` — Similar endpoint (wire cache)
- `skillmeat/web/components/collection/similar-artifacts-tab.tsx` — UI component (display scores)

**Progress Tracking**:
- Phase 1: `.claude/progress/similarity-scoring-overhaul/phase-1-progress.md`
- Phase 2: `.claude/progress/similarity-scoring-overhaul/phase-2-progress.md`
- Phase 3: `.claude/progress/similarity-scoring-overhaul/phase-3-progress.md`
