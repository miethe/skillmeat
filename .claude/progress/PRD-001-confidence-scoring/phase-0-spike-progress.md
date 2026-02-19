---
type: progress
prd: PRD-001-confidence-scoring
phase: 0
phase_title: SPIKE Research
status: completed
progress: 100
total_tasks: 1
completed_tasks: 1
estimated_effort: 1 week
completed_at: '2025-12-22'
tasks:
- id: P0-T1
  title: Conduct SPIKE Research
  status: completed
  assigned_to:
  - lead-architect
  - backend-architect
  dependencies: []
  story_points: 0
  description: Research community scoring practices, embedding models, anti-gaming
    strategies
  completed_at: '2025-12-22'
  deliverables:
  - .claude/docs/prd/spike/PRD-001-embedding-research.md
  - .claude/docs/prd/spike/PRD-001-scoring-research.md
parallelization:
  batch_1:
  - P0-T1
schema_version: 2
doc_type: progress
feature_slug: prd-001-confidence-scoring
---

# Phase 0: SPIKE Research

## Orchestration Quick Reference

**Batch 1** (Complete):
- P0-T1 → `lead-architect`, `backend-architect` ✅

## Quality Gates

- [x] Research findings documented
- [x] Embedding provider decision made
- [x] Baseline weights agreed upon
- [x] Anti-gaming approach documented

## Deliverables

### 1. Embedding Research (`.claude/docs/prd/spike/PRD-001-embedding-research.md`)

**Recommendation**: Local sentence-transformers (`all-MiniLM-L6-v2`) with SQLite caching

**Key Decisions**:
- Primary: Local embeddings for offline capability, zero cost, <10ms latency
- Fallback: TF-IDF/BM25 if ML dependencies unavailable
- Not recommended: Haiku skill (no embedding API, high latency), OpenAI/Cohere (cost, latency, privacy)
- Caching: SQLite with content hash invalidation

### 2. Scoring Research (`.claude/docs/prd/spike/PRD-001-scoring-research.md`)

**Validated Weights**: 25/25/50 (Trust/Quality/Match)

**Key Decisions**:
- Rate limiting: 5 ratings/artifact/user/day, 100 queries/IP/hour
- Cold-start: Bayesian priors (Quality: 50, Trust: source-dependent 50-95)
- Formula: `(prior×5 + actual_mean×count) / (5 + count)`
- Schema versioning: Semver with `schema_version` field in all responses
- Anti-gaming: Phase 5 (anomaly detection), Phase 1-3 (rate limiting only)

## Notes

**Phase 0 Complete**: SPIKE research delivered comprehensive analysis of:
1. Embedding models (sentence-transformers recommended)
2. Scoring systems (npm/VS Code/PyPI patterns analyzed)
3. Anti-gaming strategies (rate limits, Bayesian priors)
4. Schema versioning (semver approach)

**Ready for Phase 1**: Foundation implementation can proceed with validated decisions.
