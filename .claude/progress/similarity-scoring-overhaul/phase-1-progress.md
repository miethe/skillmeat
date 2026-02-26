---
schema_version: 2
doc_type: progress
type: progress
prd: "similarity-scoring-overhaul"
feature_slug: "similarity-scoring-overhaul"
prd_ref: "docs/project_plans/PRDs/features/similarity-scoring-overhaul-v1.md"
plan_ref: "docs/project_plans/implementation_plans/features/similarity-scoring-overhaul-v1.md"
phase: 1
title: "Fix Scoring Algorithm"
status: "planning"
started: "2026-02-26"
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: "on-track"
total_tasks: 6
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners: ["python-backend-engineer", "ui-engineer-enhanced"]
contributors: []

# === TASKS (SOURCE OF TRUTH) ===
tasks:
  - id: "SSO-1.1"
    description: "Create text_similarity.py with bigram_similarity() and bm25_description_similarity() functions"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "2 pts"
    priority: "high"

  - id: "SSO-1.2"
    description: "Fix _compute_metadata_score() with bigram_similarity() for titles and bm25 for descriptions; rebalance sub-weights"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SSO-1.1"]
    estimated_effort: "2 pts"
    priority: "high"

  - id: "SSO-1.3"
    description: "Rebalance composite weights (keyword=0.25, metadata=0.30, content=0.20, structure=0.15, semantic=0.10)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SSO-1.2"]
    estimated_effort: "1 pt"
    priority: "high"

  - id: "SSO-1.4"
    description: "Add text_score optional field to SimilarityBreakdownDTO in API schemas"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SSO-1.3"]
    estimated_effort: "1 pt"
    priority: "high"

  - id: "SSO-1.5"
    description: "Update frontend similar-artifacts-tab.tsx to display text_score in score breakdown"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["SSO-1.4"]
    estimated_effort: "1 pt"
    priority: "high"

  - id: "SSO-1.6"
    description: "Write Phase 1 tests: test_text_similarity.py and update test_match_analyzer.py"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SSO-1.1", "SSO-1.3"]
    estimated_effort: "2 pts"
    priority: "high"

# Parallelization Strategy (computed from dependencies)
parallelization:
  batch_1: ["SSO-1.1"]
  batch_2: ["SSO-1.2"]
  batch_3: ["SSO-1.3"]
  batch_4: ["SSO-1.4"]
  batch_5: ["SSO-1.5", "SSO-1.6"]
  critical_path: ["SSO-1.1", "SSO-1.2", "SSO-1.3", "SSO-1.4", "SSO-1.5"]
  estimated_total_time: "~1.5 days (9 pts)"

# Critical Blockers
blockers: []

# Success Criteria
success_criteria:
  - id: "SC-1"
    description: "Similar artifacts tab shows differentiated, meaningful results — same-type artifacts with related names rank above unrelated ones"
    status: "pending"
  - id: "SC-2"
    description: "Description content matters: artifacts with identical descriptions rank highly regardless of name differences"
    status: "pending"
  - id: "SC-3"
    description: "Name similarity is prominent: canvas-design and canvas-layout rank higher than unrelated artifacts"
    status: "pending"
  - id: "SC-4"
    description: "All existing similarity tests pass after scoring changes"
    status: "pending"
  - id: "SC-5"
    description: "No new Python package dependencies added in Phase 1"
    status: "pending"

# Files Modified
files_modified:
  - "skillmeat/core/scoring/text_similarity.py"
  - "skillmeat/core/scoring/match_analyzer.py"
  - "skillmeat/core/similarity.py"
  - "skillmeat/api/schemas/artifacts.py"
  - "skillmeat/api/routers/artifacts.py"
  - "skillmeat/web/components/collection/similar-artifacts-tab.tsx"
  - "tests/test_text_similarity.py"
  - "tests/test_match_analyzer.py"
---

# Similarity Scoring Overhaul - Phase 1: Fix Scoring Algorithm

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/similarity-scoring-overhaul/phase-1-progress.md \
  -t SSO-1.1 -s completed
```

---

## Objective

Fix the broken scoring algorithm to produce meaningful, differentiated results. The Similar Artifacts tab should show ranked results where name and description content actually matter. This phase introduces character bigram Jaccard for title similarity and BM25-style TF-IDF for description matching, with rebalanced composite weights. No database schema changes.

---

## Implementation Notes

### Architectural Decisions

**Text Similarity Functions**
- Use character bigram Jaccard for name/title similarity (zero dependencies, robust to hyphens/underscores)
- Use pure-Python BM25-style approach or bigram Jaccard for description similarity (no scikit-learn, no rank_bm25)
- Rationale: Minimize dependencies while maintaining algorithm quality. FTS5 pre-filtering (Phase 2) will handle larger corpus efficiency.

**Weight Rebalancing**
- New metadata sub-weights: tags=0.30, type=0.15, title_bigram=0.25, description_content=0.25, length_sanity=0.05
- New composite weights: keyword=0.25, metadata=0.30, content=0.20, structure=0.15, semantic=0.10
- Fallback redistribution (when semantic unavailable): keyword=0.278, metadata=0.333, content=0.222, structure=0.167
- Rationale: Elevate description/name matching from minor signals to primary ranking factors. Semantic scoring deferred to Phase 3.

**API Field Addition**
- Add optional `text_score: Optional[float]` to `SimilarityBreakdownDTO` (backward compatible)
- Populate from scoring result in artifacts router
- Rationale: Gradual API expansion allows frontend to display improved scores independently

### Patterns and Best Practices

- **Text Similarity Module**: New `skillmeat/core/scoring/text_similarity.py` provides two pure functions with no side effects
- **Test Coverage**: Unit tests verify edge cases (empty strings, identical inputs, partial overlap, special characters)
- **Backward Compatibility**: Existing API clients receiving `null` for text_score are unaffected
- **Algorithm Verification**: Similar artifacts computed live in Phase 1 (caching added in Phase 2)

### Known Gotchas

- **Bigram Handling**: Character bigrams should strip hyphens and underscores before comparison to handle domain-specific naming (e.g., `canvas-design` vs `canvas_design`)
- **Empty String Behavior**: Both similarity functions must handle empty/null descriptions gracefully, returning 0.0
- **Weight Normalization**: When semantic=0.10 is redistributed, all remaining weights must sum to 1.0 (verify in unit tests)
- **Domain-Specific Stop Words**: BM25 may over-score common words ("skill", "tool", "command") — consider a small stop-word list in SSO-1.1 acceptance criteria
- **Floating Point Precision**: Ensure scores are normalized to [0.0, 1.0] range; test for NaN/Inf edge cases

### Development Setup

No additional setup required for Phase 1. All work is pure Python with standard library only.

**Test Execution**:
```bash
pytest tests/test_text_similarity.py -v
pytest tests/test_match_analyzer.py -v
```

**Manual Verification**:
After Phase 1 is complete, load the Similar Artifacts tab in the UI and verify:
1. Same-description artifacts score >= 0.6 in metadata_score
2. Canvas-like artifacts (canvas-design, canvas-layout) rank related results above unrelated ones
3. Different names + identical descriptions = high score

---

## Completion Notes

_To be filled in when phase is complete._

- What was built
- Key learnings
- Unexpected challenges
- Recommendations for next phase
