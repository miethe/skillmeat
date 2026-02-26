---
schema_version: "1.1"
doc_type: spike
title: "Similarity Scoring System Overhaul"
status: draft
created: 2026-02-26
updated: 2026-02-26
feature_slug: similarity-scoring-overhaul
complexity: Large
estimated_research_time: "4 hours"
research_questions:
  - "Best text-based similarity algorithm for artifact names/descriptions without embeddings"
  - "Improved content similarity beyond hash comparison"
  - "Pre-computation strategy for SQLite backend"
  - "SQLite FTS5 and vector extension feasibility"
  - "Embedding strategy for optional semantic enhancement"
prd_ref: null
plan_ref: null
related_documents: []
---

# SPIKE: Similarity Scoring System Overhaul

**SPIKE ID**: `SPIKE-2026-02-26-SIMILARITY-SCORING`
**Date**: 2026-02-26
**Related Files**:
- `skillmeat/core/similarity.py`
- `skillmeat/core/scoring/match_analyzer.py`
- `skillmeat/models.py` (ArtifactFingerprint ~line 458)
- `skillmeat/api/routers/artifacts.py` (GET /api/v1/artifacts/{id}/similar)
- `skillmeat/api/schemas/artifacts.py` (SimilarityBreakdownDTO, SimilarArtifactDTO)
- `skillmeat/cache/models.py` (Artifact, CollectionArtifact, DuplicatePair ORM models)
- `skillmeat/web/hooks/use-similar-artifacts.ts`
- `skillmeat/web/components/collection/similar-artifacts-tab.tsx`

---

## Executive Summary

The current similarity scoring system has five structural deficiencies: description comparison uses length ratio (not content), the semantic scorer is a non-functional placeholder, content scoring is too conservative with missing hashes, structure and file-count fields are absent from the `Artifact` ORM model, and every query rescores O(n) candidates live with no caching. The recommended overhaul proceeds in three phases: (1) fix the scoring algorithm using TF-IDF cosine for text and n-gram shingling for content, (2) add a lightweight SQLite FTS5 pre-filter to reduce O(n) to O(k), and (3) optionally wire up `sentence-transformers` (local) or OpenAI embeddings as an opt-in enhancement. No PostgreSQL migration is warranted; SQLite's built-in FTS5 extension and a simple `similarity_cache` table are sufficient for the target collection size of 100-1000 artifacts.

---

## Research Scope and Objectives

This SPIKE answers six research questions that directly block implementation:

1. What is the best text similarity algorithm for artifact names and descriptions without LLM calls?
2. How can content similarity be improved beyond binary hash equality?
3. What can be pre-computed at import/sync time versus computed live?
4. What SQLite-specific features (FTS5, sqlite-vss, sqlite-vec) are feasible in this stack?
5. Should we migrate to PostgreSQL for vector search, or is SQLite sufficient?
6. What is the best lightweight embedding strategy for the optional semantic enhancement?

---

## Findings: Current System Deficiencies

### Deficiency 1: Description Comparison Uses Length Ratio

**File**: `skillmeat/core/scoring/match_analyzer.py`, `_compute_metadata_score()`, line 479-483

The description component of `metadata_score` uses:
```python
desc_ratio = min(len_a, len_b) / max(len_a, len_b)
score += desc_ratio * 0.10
```

This means "Canvas Design Tool — A skill for creating beautiful UI designs" and "Canvas Drawing Tool — A completely different skill" score identically if their character lengths are the same. Description content is the strongest natural-language signal for artifact similarity and is being completely ignored.

**Effective contribution of description to composite score**: At 10% of metadata_score and metadata_score weighted at 15% of composite, description contributes a maximum of **1.5%** to the final score — and that 1.5% is computed from string length, not content.

### Deficiency 2: Title Is Tokenized But Never Semantically Compared

**File**: `skillmeat/core/scoring/match_analyzer.py`, `_compute_metadata_score()`, line 470-475

Title uses Jaccard over a small token set. For a title like "Canvas Design" vs "Canvas Layout", Jaccard = 0.33, giving 0.33 * 0.15 * 0.15 = **0.0075 contribution** to composite score. Short titles with partial word overlap score near zero despite being clearly related.

### Deficiency 3: Semantic Scorer Is a Non-Functional Placeholder

**File**: `skillmeat/core/scoring/haiku_embedder.py`, `_generate_embedding()`, lines 301-337

The entire `_generate_embedding` method returns `None` unconditionally with a comment: "This is a placeholder implementation." Since `HaikuEmbedder.is_available()` requires a valid `ANTHROPIC_API_KEY`, and the `_generate_embedding()` always returns `None`, the semantic scorer never contributes. The 10% semantic weight is always redistributed to the other components.

### Deficiency 4: Content and Structure Hashes Are Missing From the Artifact ORM

**File**: `skillmeat/cache/models.py`, `Artifact` class, lines 218-355

The `Artifact` model has:
- `content_hash`: Mapped[Optional[str]] — present, but stores context entity content hash (for context entities like .claude/context files), not artifact file content hash
- Missing: `structure_hash`, `file_count`, `total_size`

The `ArtifactFingerprint` model (`skillmeat/models.py`, lines 457-485) has all five fields, but these are computed on-demand from the filesystem, not persisted to the DB. When `SimilarityService._fingerprint_from_row()` builds a fingerprint from a DB row, it always reads empty strings for `structure_hash` and zeros for `file_count`/`total_size`, causing every content and structure comparison to fall through to the weakest branch (0.0 return when no size data either).

### Deficiency 5: No Pre-Computation or Caching

**File**: `skillmeat/core/similarity.py`, `_find_similar_impl()`, lines 379-475

Every call to `/api/v1/artifacts/{id}/similar`:
1. Fetches all collection artifacts from the DB
2. Builds a fingerprint for each
3. Scores every candidate against the target
4. Sorts results

With 500 artifacts, this is 499 full score computations per request. Each `_compute_keyword_score()` call tokenizes and cross-scores two combined text documents. This is O(n) work with non-trivial constant factors.

The `DuplicatePair` table exists for consolidated similarity pairs but is only used by `get_consolidation_clusters()`, not by `find_similar()`. The live scoring path does not consult pre-computed pairs.

---

## Technical Analysis

### MP Layer Impact Assessment

- **UI Layer Changes**: Minimal. Add a "name/description similarity" label in score breakdown display if desired. The `SimilarityBreakdownDTO` can add a `text_score` field alongside the existing breakdown.
- **API Layer Changes**: Add an optional `text_score` field to `SimilarityBreakdownDTO`. Optionally expose a `POST /api/v1/artifacts/{id}/similarity-cache/rebuild` endpoint for manual cache invalidation.
- **Database Layer Changes**: Add `structure_hash`, `file_count`, `total_size`, `name_tokens` (FTS5 virtual table or JSON column for pre-indexed tokens) to Artifact or CollectionArtifact. Add a `SimilarityCache` table for pre-computed pairwise scores. Add FTS5 virtual table for fast candidate pre-filtering.
- **Infrastructure Changes**: Optional: `sentence-transformers` Python package for local embeddings. No service changes required.

### Architecture Compliance Review

The layered architecture (router → service → repository → DB) is well-preserved by the current design. All proposed changes remain in `core/scoring/` (service layer) and `cache/` (repository/DB layer). No router changes are required for the core improvement; the API surface can remain unchanged.

---

## Research Question Analysis

### RQ1: Text Similarity Algorithm Without Embeddings

**Options evaluated**:

| Algorithm | Quality | Complexity | Latency (100 artifacts) |
|-----------|---------|------------|------------------------|
| Token Jaccard (current) | Low — treats all tokens as equal weight | None | ~1ms |
| TF-IDF cosine (sklearn) | Good — downweights common terms | Medium — requires corpus for IDF | ~5ms build + ~0.5ms per pair |
| BM25 (rank_bm25 package) | Very good — length normalization, IDF weighting | Low — stateless, no corpus required | ~2ms per pair |
| Character n-gram overlap | Good for short texts, handles typos | Low | ~1ms per pair |
| Edit distance (Levenshtein) | Good for name comparison only | Low | ~0.5ms per pair |
| Sentence-transformers (local) | Excellent | High — 150MB+ model download | ~50ms per pair (first run), ~5ms cached |

**Recommended**: BM25 for description similarity, character bigram Jaccard for name similarity.

**Rationale for BM25 over TF-IDF**:
- BM25 handles short artifact descriptions better than TF-IDF because it applies a length normalization factor that prevents long descriptions from dominating just by having more word occurrences.
- `rank_bm25` is a single-file, zero-dependency Python package (BSD license). It adds ~8KB to the installed size.
- For a corpus of 100-1000 artifacts, BM25 index rebuilds in under 10ms at import time.
- No `sklearn` dependency required — this matters because `sklearn` pulls NumPy/SciPy and significantly increases the install footprint.

**Implementation sketch** (BM25 for descriptions):
```python
from rank_bm25 import BM25Okapi

# At service initialization or cache-warm time:
corpus_tokens = [tokenize(a.description or a.name) for a in all_artifacts]
bm25 = BM25Okapi(corpus_tokens)

# Per-query:
query_tokens = tokenize(target.description or target.name)
scores = bm25.get_scores(query_tokens)  # one float per candidate
```

**Rationale for character bigram Jaccard for names**:
- Artifact names like `canvas-design` and `canvas-layout` share high bigram overlap (ca, an, nv, va, as) even though their Jaccard over full tokens is only 0.33.
- Bigrams are robust to hyphen vs. underscore variants and partial prefix matches.
- Zero dependencies, ~5 lines of code.

**Recommended new `metadata_score` weights**:

| Component | Current | Recommended |
|-----------|---------|-------------|
| Tag Jaccard | 50% | 30% |
| Type match | 25% | 15% |
| Title BM25/bigram | 15% | 25% |
| Description BM25 | 0% (was length ratio) | 25% |
| Description length ratio | 10% | 5% (sanity signal only) |

This increases the effective description contribution from 1.5% to 3.75% of composite score, and makes the contribution meaningful (content-based) rather than noise.

### RQ2: Improved Content Similarity

**Problem statement**: `content_hash` in the `Artifact` ORM is a context-entity field, not an artifact content hash. `structure_hash`, `file_count`, and `total_size` are not persisted. The `_compute_content_score()` falls through to return 0.0 for nearly all collection artifacts.

**Options evaluated**:

| Approach | Quality | Complexity | DB Changes |
|----------|---------|------------|------------|
| Fix: Persist content/structure hashes at import time | Fixes root cause | Low — hook into sync/refresh | Add 3 columns to CollectionArtifact |
| MinHash/LSH for approximate Jaccard | High quality for near-duplicates | High — requires shingling pipeline | Store MinHash signatures |
| SimHash for near-duplicate detection | Good for text similarity | Medium | Store 64-bit hash |
| File-level content comparison via resolved_sha | Useful for GitHub-sourced artifacts | Low | Use existing `resolved_sha` column |

**Recommended**: Fix the root cause by persisting artifact-specific `content_hash`, `structure_hash`, `file_count`, and `total_size` in `CollectionArtifact` at sync/import time.

**Rationale**: MinHash and SimHash are powerful but add significant engineering complexity for a collection of 100-1000 artifacts. The primary issue is that these fields are simply not being populated. Once populated, the existing hash-comparison logic gives correct exact-match detection. Add a size-ratio score tuned from (0.5 max) to (0.7 max) when hashes differ but sizes are close, since same-size artifacts with different content are more likely related than different-size artifacts.

**Schema additions to `CollectionArtifact`**:
```sql
ALTER TABLE collection_artifacts ADD COLUMN artifact_content_hash TEXT;
ALTER TABLE collection_artifacts ADD COLUMN artifact_structure_hash TEXT;
ALTER TABLE collection_artifacts ADD COLUMN artifact_file_count INTEGER DEFAULT 0;
ALTER TABLE collection_artifacts ADD COLUMN artifact_total_size INTEGER DEFAULT 0;
```

These should be populated by the existing `populate_collection_artifact_from_import()` path in `cache/refresh.py`.

The `_fingerprint_from_row()` method in `SimilarityService` already has the right fallback chain but needs to check `CollectionArtifact` fields in preference to the (always-empty) `Artifact` fields for these values.

### RQ3: Pre-Computation Strategy

**Options evaluated**:

| Strategy | Benefit | Cost | TTL Complexity |
|----------|---------|------|---------------|
| Pre-compute all N×N pairs | Fastest queries | O(n²) storage and compute | High — any import invalidates |
| FTS5 virtual table pre-filter + live score top-k | Good — reduces O(n) to O(k) | Low | Low — FTS5 auto-updates |
| Materialized similarity cache (top-20 per artifact) | Fast reads, bounded storage | O(n×20) = O(n) | Medium — rebuild per artifact on change |
| BM25 in-memory index at service startup | Fast queries, no DB changes | Memory: ~1KB per artifact | Low — rebuild on startup |

**Recommended**: Two-tier approach

**Tier 1 (immediate, no schema changes)**: BM25 in-memory index built at `SimilarityService` initialization. This reduces the O(n) per-request cost to: BM25 pre-filter selects top-k candidates (k=50), then the full multi-component scorer runs only on those k. With 500 artifacts, this reduces full scoring from 499 to 50 calls — a 10x reduction.

**Tier 2 (schema change)**: Add a `similarity_cache` table that stores the top-20 most similar artifacts per artifact, with a `computed_at` timestamp. The API endpoint checks this table first. A background job (or a hook in `refresh_single_artifact_cache()`) invalidates stale entries when an artifact is updated.

```sql
CREATE TABLE IF NOT EXISTS similarity_cache (
    source_artifact_uuid TEXT NOT NULL,
    target_artifact_uuid TEXT NOT NULL,
    composite_score REAL NOT NULL,
    breakdown_json TEXT NOT NULL,  -- JSON blob of ScoreBreakdown
    computed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source_artifact_uuid, target_artifact_uuid),
    FOREIGN KEY (source_artifact_uuid) REFERENCES artifacts(uuid) ON DELETE CASCADE,
    FOREIGN KEY (target_artifact_uuid) REFERENCES artifacts(uuid) ON DELETE CASCADE
);
CREATE INDEX idx_similarity_cache_source ON similarity_cache(source_artifact_uuid);
CREATE INDEX idx_similarity_cache_computed ON similarity_cache(source_artifact_uuid, composite_score DESC);
```

Cache invalidation logic: when `refresh_single_artifact_cache()` runs for artifact X, delete all `similarity_cache` rows where `source_artifact_uuid = X` or `target_artifact_uuid = X`. The next request for X rebuilds and persists the cache.

**Why not full N×N pre-computation**: With n=1000, N×N = 1,000,000 pairs. At 100 bytes per row, that is 100MB — acceptable in absolute terms, but invalidation becomes expensive. A top-20-per-artifact cache requires only 20,000 rows and has simpler invalidation semantics.

### RQ4: SQLite-Specific Feature Feasibility

**SQLite FTS5 (Full-Text Search)**:

SQLite FTS5 is available in Python's standard `sqlite3` module without any additional installation. SkillMeat's SQLAlchemy stack can use FTS5 via raw SQL for the virtual table, with the ORM used for everything else.

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS artifact_fts USING fts5(
    artifact_uuid UNINDEXED,
    name,
    title,
    description,
    tags,
    tokenize='porter ascii'
);
```

FTS5 supports BM25 scoring via `bm25(artifact_fts)` in the ORDER BY clause. This enables a pre-filter query like:

```sql
SELECT artifact_uuid, bm25(artifact_fts) AS score
FROM artifact_fts
WHERE artifact_fts MATCH ?
ORDER BY score
LIMIT 50;
```

FTS5 is lightweight, auto-updated via triggers or explicit `INSERT/UPDATE/DELETE` on the virtual table, and eliminates the need for a separate BM25 library entirely. **This is the preferred approach over the `rank_bm25` package.**

**sqlite-vss and sqlite-vec**:

`sqlite-vss` (vector similarity search) and `sqlite-vec` are external SQLite extension libraries that must be compiled and loaded at runtime. They are NOT part of Python's standard library. Loading them requires:
1. A compiled `.so`/`.dylib` extension
2. `conn.enable_load_extension(True)` which is disabled by default in Python's `sqlite3` module for security reasons
3. Platform-specific binary distribution

**Assessment**: Too complex for this use case. The target scale (100-1000 artifacts) does not justify the operational complexity of managing native SQLite extensions. SQLite FTS5 is sufficient.

### RQ5: PostgreSQL Migration Cost-Benefit

**Costs of migration**:
- Alembic migrations would need full rewrite (PostgreSQL-flavored)
- `pgvector` requires a separate PostgreSQL server process
- SkillMeat is a personal tool with embedded SQLite — changing to PostgreSQL requires a server setup, connection management, and backup strategy
- The current `~/.skillmeat/` data directory pattern does not translate to PostgreSQL
- All developer environments would require PostgreSQL installation

**Benefits of migration**:
- `pgvector` provides native vector similarity search with HNSW indexing
- `pg_trgm` provides trigram-based text similarity with gin indexes
- PostgreSQL FTS is more powerful than SQLite FTS5

**Conclusion**: Migration to PostgreSQL is not warranted for this feature. The benefits are real but they address scale problems this tool does not have (>10,000 artifacts, concurrent users). SQLite FTS5 + a similarity cache table achieves 90% of the benefit at 5% of the migration cost. If SkillMeat ever targets multi-user deployment or a hosted service, a PostgreSQL migration should be revisited as a standalone ADR.

### RQ6: Embedding Strategy for Optional Semantic Enhancement

**Current state**: `HaikuEmbedder._generate_embedding()` is an explicit placeholder returning `None`. The embedding cache infrastructure (SQLite `embeddings.db`, binary serialization) is well-built and ready to use.

**Problem**: Anthropic's API does not expose a dedicated embeddings endpoint as of February 2026. Claude models can generate text but not embedding vectors directly. Using `claude-haiku-4.5-20250929` for embeddings would require a prompt-engineering approach to extract a fixed-size vector representation, which is expensive, unreliable, and not what the existing code implies.

**Options for embeddings**:

| Approach | Quality | Setup Complexity | Cost | Offline? |
|----------|---------|-----------------|------|---------|
| `sentence-transformers` (local, `all-MiniLM-L6-v2`) | Good — 384-dim, fast | One `pip install` + 80MB model | Free | Yes |
| OpenAI `text-embedding-3-small` | Excellent — 1536-dim | API key required | ~$0.02/1M tokens | No |
| Cohere `embed-english-light-v3.0` | Good — 384-dim | API key required | Free tier available | No |
| Voyage AI `voyage-3-lite` | Very good — 512-dim | API key required | Free tier (100M tokens) | No |
| Ollama (local, `nomic-embed-text`) | Good — 768-dim | Ollama daemon required | Free | Yes |

**Recommended**: Replace `HaikuEmbedder` with a pluggable `EmbeddingProvider` strategy that defaults to `sentence-transformers` when installed, falls back to the existing keyword-only path when not installed.

```python
# Preferred provider selection order:
# 1. sentence-transformers (local, no API key, best for offline/personal tool)
# 2. OpenAI embeddings (if OPENAI_API_KEY set)
# 3. None (keyword-only fallback)
```

The `sentence-transformers` library with `all-MiniLM-L6-v2` model:
- 80MB first download, cached to `~/.cache/huggingface/`
- Sub-millisecond inference on CPU after first load
- No API key, no internet after initial download
- Directly usable with the existing `cosine_similarity()` method in `SemanticScorer`
- This is the industry-standard choice for lightweight semantic similarity in personal tools

**For the existing `HaikuEmbedder`**: Rename to `AnthropicEmbedder`, remove the broken `_generate_embedding()` stub, and change `is_available()` to return `False` always until Anthropic exposes a real embedding API. This makes the fallback behavior explicit rather than failing silently.

---

## Alternative Approaches Considered

### Approach A: Full Rewrite — Drop All Hash-Based Scoring

Replace the entire scoring pipeline with a pure text-based approach using only name, description, and tags. Discard content_hash, structure_hash, file_count, total_size.

**Pros**: Simpler, works immediately without schema changes, better for artifacts without hash data.
**Cons**: Loses exact-duplicate detection capability (content_hash = 1.0 is valuable), misses structural similarity signal for multi-file artifacts.
**Decision**: Rejected. The hash-based duplicate detection is correct and valuable; the problem is that hashes are not persisted, not that the logic is wrong.

### Approach B: Postgres + pgvector Migration

Migrate the entire DB backend to PostgreSQL for native vector search.

**Pros**: Production-grade vector search, trigram similarity built-in, better for future scale.
**Cons**: Major infrastructure change, breaks the embedded personal-tool model, no current scale need.
**Decision**: Rejected. See RQ5 analysis above.

### Approach C: Minimal Patch — Fix Description Comparison Only

Only fix the description comparison (replace length ratio with BM25/bigram), leave everything else unchanged.

**Pros**: Minimal scope, lowest risk.
**Cons**: Leaves content scoring broken (still returns 0.0), semantic scorer still placeholder, no pre-computation.
**Decision**: Viable as Phase 1 only. Recommended as first PR to unblock visible quality improvement while the larger work proceeds.

### Recommended Approach: Phased Pragmatic Enhancement

Phase 1 fixes scoring quality with zero schema changes. Phase 2 adds structural persistence and FTS5 pre-filtering. Phase 3 adds optional semantic embeddings. Each phase is independently deployable and valuable.

---

## Implementation Design

### Phase 1: Fix Scoring Algorithm (No Schema Changes)

**Files touched**:
- `skillmeat/core/scoring/match_analyzer.py` — replace `_compute_metadata_score()` description component
- `skillmeat/core/scoring/match_analyzer.py` — add character bigram function for name/title comparison
- `skillmeat/api/schemas/artifacts.py` — add optional `text_score` field to `SimilarityBreakdownDTO`
- `skillmeat/core/similarity.py` — update weight constants and breakdown construction

**Changes**:

1. Replace description length ratio with BM25 cosine similarity using SQLite FTS5 or `rank_bm25`:
   ```python
   # New _compute_text_score() method
   def _compute_text_score(self, a: ArtifactFingerprint, b: ArtifactFingerprint) -> float:
       desc_a = a.description or ""
       desc_b = b.description or ""
       if not desc_a or not desc_b:
           # Fall back to character bigram on names
           return self._bigram_jaccard(a.artifact_name, b.artifact_name)
       # BM25 with single-document corpus
       tokens_a = self._tokenize(desc_a)
       tokens_b = self._tokenize(desc_b)
       return self._bm25_similarity(tokens_a, tokens_b)
   ```

2. Replace title Jaccard with character bigram Jaccard for better partial-name matching:
   ```python
   def _bigram_jaccard(self, text_a: str, text_b: str) -> float:
       def bigrams(t: str) -> set:
           t = t.lower().replace("-", "").replace("_", "")
           return {t[i:i+2] for i in range(len(t) - 1)} if len(t) > 1 else set()
       bg_a, bg_b = bigrams(text_a), bigrams(text_b)
       if not bg_a and not bg_b:
           return 0.0
       return len(bg_a & bg_b) / len(bg_a | bg_b)
   ```

3. Rebalance `metadata_score` weights: tags=0.30, type=0.15, title_bigram=0.25, desc_bm25=0.25, length_ratio=0.05.

4. Rebalance composite weights: keyword=0.25, metadata=0.30, content=0.20, structure=0.15, semantic=0.10. Rationale: metadata now has meaningful text content, deserves higher weight; keyword and content slightly reduced.

**Acceptance criteria for Phase 1**:
- Two artifacts with identical descriptions but different names score >= 0.6 in metadata_score
- Two artifacts with the same name and different descriptions score >= 0.4 in metadata_score
- Existing unit tests for `compare()` pass
- No schema migrations required

### Phase 2: Persist Hashes and Add FTS5 Pre-Filter

**Files touched**:
- `skillmeat/cache/models.py` — add 4 columns to `CollectionArtifact`
- `skillmeat/cache/migrations/` — new Alembic migration
- `skillmeat/cache/refresh.py` — populate new columns during import/sync
- `skillmeat/core/similarity.py` — add FTS5 pre-filter step, add similarity_cache table lookup
- New migration: `similarity_cache` table

**Changes**:

1. Add to `CollectionArtifact`:
   ```python
   artifact_content_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
   artifact_structure_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
   artifact_file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
   artifact_total_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
   ```

2. Create FTS5 virtual table (raw SQL in migration, not ORM):
   ```sql
   CREATE VIRTUAL TABLE IF NOT EXISTS artifact_fts USING fts5(
       artifact_uuid UNINDEXED,
       name,
       title,
       description,
       tags,
       tokenize='porter ascii'
   );
   ```

3. Create similarity_cache table:
   ```sql
   CREATE TABLE IF NOT EXISTS similarity_cache (
       source_artifact_uuid TEXT NOT NULL,
       target_artifact_uuid TEXT NOT NULL,
       composite_score REAL NOT NULL,
       breakdown_json TEXT NOT NULL,
       computed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
       PRIMARY KEY (source_artifact_uuid, target_artifact_uuid)
   );
   CREATE INDEX idx_similarity_cache_source_score
       ON similarity_cache(source_artifact_uuid, composite_score DESC);
   ```

4. Modify `_find_similar_impl()` in `SimilarityService`:
   - Check `similarity_cache` first; if entries exist and are fresh (< 1 hour old), return cached results
   - On cache miss: use FTS5 to pre-filter candidates to top-50 by text relevance, then run full scoring on those 50
   - Persist results to `similarity_cache` after computing

5. Add `_invalidate_similarity_cache()` call to `refresh_single_artifact_cache()`.

**Acceptance criteria for Phase 2**:
- `Artifact` ORM rows built from `CollectionArtifact` now have non-zero `content_hash`, `file_count`, `total_size` values
- `_compute_content_score()` returns > 0 for artifacts with shared content
- Second request for same artifact returns results from cache (verifiable via logging)
- Migration runs cleanly against existing DB via `alembic upgrade head`

### Phase 3: Optional Semantic Embeddings

**Files touched**:
- `skillmeat/core/scoring/haiku_embedder.py` — rename and disable
- New file: `skillmeat/core/scoring/sentence_transformer_embedder.py`
- `skillmeat/core/similarity.py` — update provider selection logic
- `pyproject.toml` or `setup.py` — add `sentence-transformers` as optional dependency

**Changes**:

1. Create `SentenceTransformerEmbedder` implementing `EmbeddingProvider`:
   ```python
   class SentenceTransformerEmbedder(EmbeddingProvider):
       MODEL_NAME = "all-MiniLM-L6-v2"
       EMBEDDING_DIMENSION = 384

       def is_available(self) -> bool:
           try:
               from sentence_transformers import SentenceTransformer
               return True
           except ImportError:
               return False

       async def get_embedding(self, text: str) -> Optional[List[float]]:
           # Use thread executor to avoid blocking event loop
           ...
   ```

2. Add `[semantic]` optional dependency group:
   ```toml
   [project.optional-dependencies]
   semantic = ["sentence-transformers>=2.7.0"]
   ```

3. Update `SimilarityService.__init__()` to try `SentenceTransformerEmbedder` before `HaikuEmbedder` in the provider selection chain.

**Acceptance criteria for Phase 3**:
- Running `pip install skillmeat[semantic]` enables semantic scoring
- Without `[semantic]`, the system falls back gracefully to keyword+text scoring
- Semantic scorer uses the existing `HaikuEmbedder` SQLite cache for result persistence (reuse cache infrastructure)
- Performance: first request after startup incurs model load (~1s), subsequent requests complete in < 50ms

### Phase 4: Testing and Observability

**Files touched**:
- `tests/` — unit tests for new BM25/bigram scoring methods
- `skillmeat/core/similarity.py` — add timing metrics for cache hit/miss

**Test coverage targets**:
- `_compute_text_score()`: test identical descriptions, partial overlap, no overlap, missing description fallback
- `_bigram_jaccard()`: test hyphenated names, prefix variants, single characters
- `_find_similar_impl()` with cache: test cache hit path, cache miss path, stale cache invalidation
- FTS5 pre-filter: integration test that pre-filter reduces candidate count

---

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| FTS5 not available in deployed Python build | High — Phase 2 fails | Low — standard in CPython 3.6+ | Check `sqlite3.sqlite_version` at startup; log warning and fall back to full scan |
| BM25 over-scores common words (e.g., "tool", "skill") | Medium — noisy results | Medium — artifact names are often similar | Add a small stop-word list for domain-specific common words: "skill", "tool", "command", "agent" |
| similarity_cache grows unbounded over time | Low — SQLite size | Low — max 20 rows per artifact | Add a periodic cleanup job or LRU eviction based on `computed_at` |
| sentence-transformers model download blocks startup | Medium — UX degradation | Low — only on first use | Lazy-load; only download when first similarity request with semantic enabled arrives |
| Phase 2 migration breaks existing DB on upgrade | High — data loss | Low — only adds columns | Use `ADD COLUMN IF NOT EXISTS` pattern; test against existing fixture DB in CI |
| Content hash fields populated incorrectly | Medium — wrong scores | Medium — fingerprint computation has bugs | Add unit tests for fingerprint field population; log which fields are populated vs empty |

---

## Success Criteria

- [ ] Two artifacts with the same description but different names produce metadata_score >= 0.6
- [ ] Two artifacts with similar names (e.g., `canvas-design` and `canvas-layout`) produce metadata_score >= 0.4
- [ ] Content scoring returns > 0 for collection artifacts when content_hash is populated
- [ ] Second similarity request for the same artifact hits the cache (< 10ms response time)
- [ ] FTS5 pre-filter reduces full-score computation from O(n) to O(50) candidates
- [ ] Semantic scoring is enabled by `pip install skillmeat[semantic]` and works without API key
- [ ] All existing similarity unit tests pass after refactor
- [ ] No regression in composite score for artifacts that were previously returning non-zero scores

---

## Effort Estimation

| Phase | Description | Estimate | Confidence |
|-------|-------------|----------|------------|
| Phase 1 | Fix scoring algorithm (BM25/bigram, rebalance weights) | 1.5 days | High |
| Phase 2 | Schema changes, FTS5 pre-filter, similarity_cache | 2.5 days | Medium |
| Phase 3 | sentence-transformers embedder | 1 day | High |
| Phase 4 | Tests and observability | 1 day | High |
| **Total** | | **6 days** | Medium |

**Notes**:
- Phase 1 can ship independently and immediately improves quality
- Phase 2 has the most uncertainty due to Alembic migration coordination and FTS5 virtual table management in SQLAlchemy
- Phase 3 is well-bounded because the EmbeddingProvider interface and cache infrastructure are already correct

---

## Dependencies and Prerequisites

- **Python packages**: `rank_bm25` (optional, can use FTS5 instead), `sentence-transformers` (optional, Phase 3 only)
- **SQLite**: FTS5 extension — available in Python standard library's `sqlite3` module when compiled with FTS5 support (default on macOS, Linux). Verify with: `sqlite3 :memory: "SELECT fts5()"`.
- **Alembic**: Existing migration chain must be clean before Phase 2 migration can be added
- **Existing infrastructure reuse**: `HaikuEmbedder` SQLite cache (`~/.skillmeat/embeddings.db`) is well-built and can be reused by `SentenceTransformerEmbedder` with no changes to the cache schema

---

## Recommendations

### Immediate Actions

1. **Ship Phase 1 as a standalone PR** — replace description length ratio with bigram/BM25 similarity and rebalance metadata weights. This is a 1.5-day change with high confidence, zero schema risk, and immediately visible quality improvement.

2. **Fix fingerprint persistence** — the `ArtifactFingerprint` fields (`content_hash`, `structure_hash`, `file_count`, `total_size`) must be populated during `populate_collection_artifact_from_import()`. Trace the fingerprint computation call in `sources/` and verify these values are written to `CollectionArtifact`. This may be a data pipeline bug that predates the scoring system.

3. **Disable `HaikuEmbedder` without ceremony** — change `is_available()` to return `False` with a clear docstring explaining that Anthropic does not expose an embedding API. Remove the misleading placeholder `_generate_embedding()` stub.

### Architecture Decision Records Needed

- **ADR-SSO-001: SQLite FTS5 as Similarity Pre-Filter** — Decide between FTS5 virtual table vs. in-memory BM25 index for candidate pre-filtering. Key tradeoff: FTS5 persists across restarts and auto-updates via triggers; in-memory BM25 requires no schema changes but rebuilds on every service restart.

- **ADR-SSO-002: Embedding Provider Strategy** — Decide between `sentence-transformers` (local, no API key) vs. cloud embedding APIs (OpenAI, Cohere, Voyage). Key factors: offline capability, install size, first-run latency, cost. Recommended default: `sentence-transformers` with cloud as opt-in override via settings.

- **ADR-SSO-003: Similarity Cache Invalidation Policy** — Decide on cache TTL (1 hour vs. artifact-update-triggered) and maximum cache size. Key tradeoff: time-based TTL is simple but can serve stale results after import; event-driven invalidation is more complex but always correct.

### Follow-up Research Questions

- **Can the FTS5 virtual table be kept synchronized automatically?** SQLite FTS5 does not support foreign key cascades or automatic sync from a parent table. Triggers would need to be created manually. Investigate whether Alembic can manage trigger creation, or whether the FTS5 table should be rebuilt entirely on each `refresh_single_artifact_cache()` call (acceptable at n=1000).

- **What is the actual fingerprint population rate?** Before investing in Phase 2, run a diagnostic query against a real collection: `SELECT COUNT(*), COUNT(artifact_content_hash), COUNT(artifact_structure_hash) FROM collection_artifacts`. If the population rate is near 0%, the fingerprint computation pipeline may need a separate fix before Phase 2 is useful.

---

## Appendices

### A. Expert Consultation Summary

**Architecture analysis**: The current system is well-designed with clean layering. The problems are localized to two places: (1) the scoring algorithm in `match_analyzer.py` uses proxy metrics where content metrics would be better, and (2) the data pipeline does not persist fingerprint fields to the DB. No architectural changes are required — only algorithm improvements and schema additions within the existing layered pattern.

**Backend analysis**: The FTS5 recommendation is preferred over the `rank_bm25` package because FTS5 is already available, the SQLite connection is already open, and there is no additional dependency. FTS5's `porter ascii` tokenizer handles the common artifact naming patterns (hyphenated slugs, compound words) correctly.

**Database analysis**: The `similarity_cache` table design mirrors the existing `DuplicatePair` pattern in the same `cache/models.py` file, so it is architecturally consistent. The choice to cache top-20 per artifact rather than all N×N pairs is deliberate: it bounds storage to O(n) and makes invalidation per-artifact rather than requiring a full rebuild.

### B. Code Examples

**BM25-style similarity using FTS5**:
```python
# In SimilarityService._find_similar_impl():
def _fts5_prefilter(self, session: Session, target_fp: ArtifactFingerprint, k: int = 50) -> List[str]:
    """Return top-k candidate UUIDs by FTS5 BM25 relevance."""
    query_text = f"{target_fp.artifact_name} {target_fp.title or ''} {target_fp.description or ''}"
    # Escape FTS5 special chars
    query_text = query_text.replace('"', '""')
    rows = session.execute(
        text("""
            SELECT artifact_uuid, bm25(artifact_fts) as score
            FROM artifact_fts
            WHERE artifact_fts MATCH :query
            ORDER BY score
            LIMIT :k
        """),
        {"query": query_text, "k": k}
    ).fetchall()
    return [row[0] for row in rows]
```

**Character bigram Jaccard for names**:
```python
def _bigram_jaccard(self, text_a: str, text_b: str) -> float:
    def bigrams(t: str) -> set:
        t = re.sub(r'[^a-z0-9]', '', t.lower())
        return {t[i:i+2] for i in range(len(t) - 1)} if len(t) >= 2 else {t} if t else set()
    bg_a, bg_b = bigrams(text_a), bigrams(text_b)
    if not bg_a and not bg_b:
        return 1.0  # Both empty = identical
    if not bg_a or not bg_b:
        return 0.0
    return len(bg_a & bg_b) / len(bg_a | bg_b)
```

**Updated composite weight constants** (in `similarity.py`):
```python
_WEIGHTS: dict[str, float] = {
    "keyword": 0.25,   # was 0.30
    "metadata": 0.30,  # was 0.15 — now includes text similarity
    "content": 0.20,   # unchanged
    "structure": 0.15, # was 0.20 — slightly reduced
    "semantic": 0.10,  # unchanged
}
```

### C. Reference Materials

- SQLite FTS5 documentation: https://www.sqlite.org/fts5.html
- BM25 algorithm overview: Robertson and Zaragoza (2009), "The Probabilistic Relevance Framework: BM25 and Beyond"
- `rank_bm25` Python package: https://github.com/dorianbrown/rank_bm25
- `sentence-transformers` library: https://www.sbert.net — model `all-MiniLM-L6-v2` is the recommended lightweight option
- Character n-gram similarity for short texts: Cavnar & Trenkle (1994), "N-Gram-Based Text Categorization"
- Existing SkillMeat FTS5 usage: `skillmeat/api/utils/fts5.py` — this file already provides FTS5 utilities for the artifact search feature; the similarity pre-filter should reuse these utilities
