---
schema_version: 2
doc_type: progress
type: progress
prd: similarity-scoring-overhaul
feature_slug: similarity-scoring-overhaul
prd_ref: docs/project_plans/PRDs/features/similarity-scoring-overhaul-v1.md
plan_ref: docs/project_plans/implementation_plans/features/similarity-scoring-overhaul-v1.md
phase: 3
title: Optional Embedding Enhancement
status: completed
started: null
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: on-track
total_tasks: 6
completed_tasks: 6
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- ai-engineer
- python-backend-engineer
- data-layer-expert
- ui-engineer-enhanced
contributors: []
tasks:
- id: SSO-3.1
  description: Create SentenceTransformerEmbedder in embedder.py implementing EmbeddingProvider
    interface; rename HaikuEmbedder to AnthropicEmbedder with is_available() returning
    False
  status: completed
  assigned_to:
  - ai-engineer
  dependencies:
  - SSO-2.9
  estimated_effort: 2 pts
  priority: high
- id: SSO-3.2
  description: Add [semantic] optional dependency to pyproject.toml with sentence-transformers>=2.7.0
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SSO-3.1
  estimated_effort: 0.5 pts
  priority: high
- id: SSO-3.3
  description: Add ArtifactEmbedding ORM model to cache/models.py with artifact_uuid,
    embedding BLOB, model_name, embedding_dim, computed_at
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - SSO-3.1
  estimated_effort: 2 pts
  priority: high
- id: SSO-3.4
  description: 'Integrate embedder into SimilarityCacheManager: compute embeddings
    when available, store in ArtifactEmbedding, compute semantic scores, use full
    composite weights'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SSO-3.2
  - SSO-3.3
  estimated_effort: 2 pts
  priority: high
- id: SSO-3.5
  description: Update frontend similar-artifacts-tab.tsx to show real semantic percentages
    when non-null; add embedding availability indicator
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SSO-3.4
  estimated_effort: 1 pt
  priority: medium
- id: SSO-3.6
  description: 'Write Phase 3 tests: test_embedder.py with mocking, composite score
    tests, AnthropicEmbedder.is_available() test'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SSO-3.4
  estimated_effort: 2 pts
  priority: high
parallelization:
  batch_1:
  - SSO-3.1
  batch_2:
  - SSO-3.2
  - SSO-3.3
  batch_3:
  - SSO-3.4
  batch_4:
  - SSO-3.5
  - SSO-3.6
  critical_path:
  - SSO-3.1
  - SSO-3.2
  - SSO-3.3
  - SSO-3.4
  - SSO-3.5
  estimated_total_time: ~1 day (9.5 pts)
blockers: []
success_criteria:
- id: SC-1
  description: pip install skillmeat[semantic] enables embedding-based scoring without
    any other changes
  status: pending
- id: SC-2
  description: pip install skillmeat (without extras) works identically to Phase 2
  status: pending
- id: SC-3
  description: Semantic score shows real percentages in UI when embeddings are enabled
  status: pending
- id: SC-4
  description: First request after startup incurs model load (~1s), subsequent requests
    complete < 50ms
  status: pending
- id: SC-5
  description: Phase 3 tests pass in CI without sentence-transformers installed (via
    mocking)
  status: pending
files_modified:
- skillmeat/core/scoring/embedder.py
- skillmeat/core/scoring/haiku_embedder.py
- skillmeat/cache/models.py
- skillmeat/cache/similarity_cache.py
- skillmeat/core/similarity.py
- skillmeat/api/schemas/artifacts.py
- skillmeat/web/components/collection/similar-artifacts-tab.tsx
- pyproject.toml
- alembic/versions/XXXX_add_artifact_embedding.py
- tests/test_embedder.py
progress: 100
updated: '2026-02-26'
---

# Similarity Scoring Overhaul - Phase 3: Optional Embedding Enhancement

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/similarity-scoring-overhaul/phase-3-progress.md \
  -t SSO-3.1 -s completed
```

---

## Objective

Replace non-functional `HaikuEmbedder` with local `sentence-transformers` embedding support. Purely optional — system must work identically without it. When installed via `[semantic]` extras, enables real semantic similarity scoring. Model is lazily loaded on first request.

---

## Implementation Notes

### Architectural Decisions

**Embedding Provider Selection**
- Provider priority order: `SentenceTransformerEmbedder` first (if installed), then `AnthropicEmbedder` (always False), then None (fallback)
- `SentenceTransformerEmbedder.is_available()` returns True only when `sentence_transformers` importable
- `AnthropicEmbedder.is_available()` always returns False (no API as of Feb 2026)
- Rationale: Optional dependency allows semantic scoring without requiring all users to install heavy ML libraries

**Model Loading**
- Model loads lazily on first `get_embedding()` call, not at import
- Uses thread executor to avoid blocking event loop during inference
- Caching infrastructure reuses existing `~/.skillmeat/embeddings.db` pattern
- Rationale: Lazy load prevents startup latency cost; thread executor prevents blocking async operations

**Model Selection**
- `all-MiniLM-L6-v2`: 80MB download, 384 dimensions, sub-ms CPU inference after load
- Rationale: Excellent quality/size tradeoff for local deployment, widely available via HuggingFace

**Storage**
- Add `ArtifactEmbedding` ORM table to cache/models.py
- Store embeddings as BLOB, model_name, embedding_dim, computed_at
- Alternative: Check if existing `~/.skillmeat/embeddings.db` already stores embeddings; reuse if present
- Rationale: Database-backed storage integrates with existing cache invalidation patterns

### Patterns and Best Practices

- **Optional Dependencies**: `[semantic]` extras in pyproject.toml; graceful degradation when not installed
- **Lazy Loading**: Model downloads only on first embedding request, not on startup
- **Thread Executor**: Use `asyncio` executor pattern for non-blocking embeddings
- **Mocking in Tests**: Tests pass in CI without `sentence_transformers` via unittest.mock patches
- **Provider Interface**: Both embedders implement `EmbeddingProvider` interface for clean swapping
- **Composite Weights**: System uses full weights (semantic=0.10) when embeddings available; fallback weights otherwise

### Known Gotchas

- **HuggingFace Model Download**: First call to `get_embedding()` downloads ~80MB model to `~/.cache/huggingface/`. May take 5-10s on first load. Log informational message to user.
- **Thread Executor Overhead**: Small embeddings (single description) may not benefit from executor; still use it for consistency.
- **Model Versioning**: `sentence-transformers` version pins are important. Lock at >=2.7.0 for stability.
- **Cosine Similarity Computation**: Verify embeddings are normalized before cosine similarity. Check for NaN/Inf in embedding vectors.
- **CI Mocking**: Mock the `SentenceTransformer` class at import time (`patch('sentence_transformers.SentenceTransformer', ...)`), not at runtime.
- **AnthropicEmbedder Rename**: This is a cleanup task; ensure old references are updated throughout codebase.

### Development Setup

**Optional Dependency Installation**:
```bash
# Install with semantic extras
pip install -e ".[semantic]"

# Verify SentenceTransformerEmbedder is available
python -c "from skillmeat.core.scoring.embedder import SentenceTransformerEmbedder; print(SentenceTransformerEmbedder.is_available())"
```

**Test Execution**:
```bash
# Tests should pass without sentence_transformers installed
pytest tests/test_embedder.py -v

# Tests should also pass with sentence_transformers installed
pip install sentence-transformers
pytest tests/test_embedder.py -v
```

**Manual Verification**:
After Phase 3 is complete:
1. Uninstall optional dependency: `pip uninstall sentence-transformers`
2. Verify system still works: API returns no semantic scores (null)
3. Install optional dependency: `pip install ".[semantic]"`
4. Verify embeddings enabled: UI shows real semantic percentages, first request takes ~1s, subsequent < 50ms

---

## Completion Notes

_To be filled in when phase is complete._

- What was built
- Key learnings
- Unexpected challenges
- Feature is now complete — Phases 1-3 all landed
