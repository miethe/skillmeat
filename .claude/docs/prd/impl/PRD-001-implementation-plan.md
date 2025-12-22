---
title: "PRD-001 Implementation Plan: Confidence Scoring System"
description: "Detailed implementation plan for multi-dimensional confidence scoring system with phased delivery"
prd_reference: "PRD-001-confidence-scoring.md"
complexity: "Large"
track: "Full"
estimated_total_effort: "52 story points"
estimated_timeline: "12-14 weeks"
created: 2025-12-22
last_updated: 2025-12-22
phases: 6
---

# Implementation Plan: Confidence Scoring System (PRD-001)

**Complexity**: L (Large) | **Track**: Full (Opus + Sonnet + Haiku)
**Estimated Effort**: 52 story points | **Timeline**: 12-14 weeks (6 phases)
**Status**: DRAFT

---

## Executive Summary

The Confidence Scoring System enables SkillMeat users to discover artifacts with high confidence by combining source trustworthiness (25%), artifact quality (25%), and semantic match relevance (50%). Implemented across 6 phases over 12-14 weeks, this feature addresses the critical gap where users currently spend 15-20 minutes manually researching each artifact.

### Key Milestones

| Phase | Duration | Key Deliverable | Story Points |
|-------|----------|-----------------|--------------|
| **Phase 0** | 1 week | SPIKE: Research + embedding strategy | 0 (research) |
| **Phase 1** | 2-3 weeks | MVP: Local ratings + score display | 13 pts |
| **Phase 2** | 2-3 weeks | Match engine: keyword + semantic + context | 16 pts |
| **Phase 3** | 2 weeks | Community: GitHub import + aggregation | 10 pts |
| **Phase 4** | 2 weeks | Web UI: Score display + rating dialogs | 10 pts |
| **Phase 5** | 1-2 weeks | Advanced: Analytics + weight customization | 3 pts |

### Critical Path

```
Phase 0 (SPIKE)
    ↓ (blocking)
Phase 1 (Foundation: Models + Rating system)
    ↓ (blocking)
Phase 2 (Match Analyzer + MatchAnalyzer + ScoreCalculator)
    ↓ (can parallelize)
Phase 3 (Community scores) + Phase 4 (Web UI)
    ↓ (sequential)
Phase 5 (Advanced features)
```

### Success Criteria

- Match accuracy: 85%+ (top result correct) measured via sampling
- User rating participation: >30% of active users
- Performance: Match analysis <500ms for 100 artifacts
- API response includes `schema_version` for compatibility
- Semantic matching degrades gracefully to keyword-only if unavailable

---

## Implementation Phases

### Phase 0: SPIKE & Foundation Research

**Duration**: 1 week | **Story Points**: Research (no code) | **Type**: Research

#### Phase Overview

Research community scoring practices, embedding model options, and anti-gaming strategies to inform Phases 1-5 design decisions.

#### Objectives

1. Analyze npm, VS Code, PyPI scoring systems for best practices
2. Evaluate embedding model options: Haiku sub-skill vs. local models vs. API
3. Document anti-gaming strategies (rate limiting, anomaly detection)
4. Recommend baseline confidence score weights
5. Define schema_version strategy for API compatibility

#### Deliverables

- Spike summary document with:
  - Recommended score weights (default 25/25/50)
  - Embedding model recommendation: Haiku 4.5 sub-skill as default
  - Anti-gaming strategy: rate limiting (5/user/artifact/day) + anomaly detection
  - Schema version strategy: version 1 in Phase 1, backward compatibility approach
  - Cold-start prior strategy: Bayesian with trust-based defaults

#### Quality Gates

- [ ] Research findings documented
- [ ] Weights and strategy agreed upon
- [ ] Embedding provider decision made
- [ ] Anti-gaming approach documented

#### Dependencies

None (start here)

---

### Phase 1: Foundation - Data Models & Local Ratings

**Duration**: 2-3 weeks | **Story Points**: 13 | **Type**: Backend foundation

#### Phase Overview

Establish the data model, local rating storage, and basic score display. Implements core scoring infrastructure that all subsequent phases depend on.

#### Objectives

1. Extend artifact data model with rating fields
2. Create SQLite schema for user ratings and community scores
3. Implement `RatingManager` for storing/exporting ratings
4. Implement basic quality scoring (user ratings + maintenance signals)
5. Add CLI commands: `skillmeat rate`, `skillmeat show --scores`
6. Add API endpoints: `/artifacts/{id}/scores`, `/artifacts/{id}/ratings`

#### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Story Points | Assigned Agent(s) |
|---------|-----------|-------------|-------------------|--------------|------------------|
| P1-T1 | Extend ArtifactRating Schema | Add fields: `user_rating`, `community_score`, `trust_score`, `last_updated`, `maintenance_score` to artifact model | Schema deployed, migrations created, model tests pass (>80% coverage) | 3 | `data-layer-expert`, `python-backend-engineer` |
| P1-T2 | Create SQLite Schema for Ratings | Design and migrate SQLite database with tables: `user_ratings`, `community_scores`, `match_history` | Schema created, migrations applied, schema document generated | 3 | `data-layer-expert`, `python-backend-engineer` |
| P1-T3 | Implement RatingManager | Storage layer for user ratings with read/write/export methods | Manager class in `skillmeat/storage/rating_store.py`, unit tests >80% coverage | 4 | `python-backend-engineer` |
| P1-T4 | Implement Quality Scorer | Aggregate user ratings (40%) + community scores (30%) + maintenance metrics (20%) + compatibility (10%) | `QualityScorer` class returns 0-100 score, handles missing data with priors | 3 | `python-backend-engineer` |
| P1-T5 | CLI: skillmeat rate command | Implement rating submission CLI: `skillmeat rate <artifact> [--rating 1-5] [--feedback "..."]` | Command works, ratings persisted, JSON output support, help text | 2 | `python-backend-engineer` |
| P1-T6 | CLI: skillmeat show --scores | Extend show command to display scores: `skillmeat show <artifact> --scores` | Output shows trust, quality, match breakdown, human-readable format | 2 | `python-backend-engineer` |
| P1-T7 | API: GET /artifacts/{id}/scores | New endpoint returning `{trust_score, quality_score, user_rating, community_score, last_updated, schema_version}` | Endpoint works, schema documented, 404 on missing artifact, pagination N/A | 2 | `python-backend-engineer`, `backend-architect` |
| P1-T8 | API: POST /artifacts/{id}/ratings | Submit user rating with optional feedback: `{rating: 1-5, feedback?: string, share_with_community?: bool}` | Endpoint works, rate limiting applied (5/day), 204 response, structured logging | 2 | `python-backend-engineer`, `backend-architect` |
| P1-T9 | Add OpenTelemetry Instrumentation | Add spans for rating operations: rate submission, score fetch, quality aggregation | Spans include trace_id, span_id, timing metrics, exportable to observability backend | 1 | `python-backend-engineer` |

#### Quality Gates

- [ ] All P1 tasks completed with >80% unit test coverage
- [ ] API responses include `schema_version: "1"` field
- [ ] Manual testing: `skillmeat rate` and `skillmeat show --scores` work end-to-end
- [ ] Performance baseline: API endpoints respond <100ms (excluding network)
- [ ] Database migration strategy documented (can rollback)

#### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| SQLite schema design needs changes in later phases | Medium | Design schema extensible for community scores; document migration path |
| User privacy concerns with ratings storage | Low | Anonymous by default; opt-in for attribution; clear consent in CLI help |
| Rating distribution skewed (mostly 5-star or 1-star) | Medium | Log rating patterns; use rating count in quality score formula |

#### Dependencies

- Phase 0 SPIKE completion (weights and schema version strategy)
- Existing artifact model in `skillmeat/core/artifact.py`
- FastAPI infrastructure already in place (`skillmeat/api/`)

---

### Phase 2: Match Analysis Engine

**Duration**: 2-3 weeks | **Story Points**: 16 | **Type**: Core algorithm

#### Phase Overview

Implement the match analysis engine combining keyword matching, semantic similarity (via embeddings), and context-aware boosting to produce ranked results with confidence scores.

#### Objectives

1. Implement `MatchAnalyzer` with keyword scoring
2. Implement `SemanticScorer` using Haiku 4.5 sub-skill or local model
3. Implement `ContextBooster` to detect project type and boost scores
4. Implement `ScoreCalculator` for composite confidence formula
5. Add CLI command: `skillmeat match "<query>"` and `--json` flag
6. Add API endpoint: `GET /api/v1/match`
7. Comprehensive error handling with graceful degradation

#### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Story Points | Assigned Agent(s) |
|---------|-----------|-------------|-------------------|--------------|------------------|
| P2-T1 | Implement MatchAnalyzer (Keyword) | Score artifacts based on keyword match: title, description, tags, aliases | Query "pdf" matches pdf skill >80%, non-matches <30%, O(n) performance | 4 | `python-backend-engineer` |
| P2-T2 | Implement SemanticScorer (Embeddings) | Use Haiku 4.5 sub-skill for semantic similarity with caching | Query "process PDF" matches pdf skill >90%, graceful degradation if unavailable | 6 | `python-backend-engineer`, `backend-architect` |
| P2-T3 | Implement ContextBooster | Detect project language/type from manifest, boost relevant artifacts | React project boosts React artifacts, Python boosts Python artifacts, multiplier configurable | 3 | `python-backend-engineer` |
| P2-T4 | Implement ScoreCalculator | Compute composite: (Trust×0.25) + (Quality×0.25) + (Match×0.50) | Formula produces 0-100 scores, weights configurable via feature flags, edge cases handled | 2 | `python-backend-engineer` |
| P2-T5 | CLI: skillmeat match command | User-facing match command: `skillmeat match "process PDF" --limit 5` | Returns ranked results with confidence, human-readable table output, colored scores | 3 | `python-backend-engineer` |
| P2-T6 | CLI: skillmeat match --json | Agent-friendly JSON output with schema_version and structured explanation | JSON valid, schema documented, agents can parse, explanation field included | 2 | `python-backend-engineer` |
| P2-T7 | API: GET /api/v1/match | Match endpoint: `GET /api/v1/match?q=<query>&limit=<n>&min_confidence=<score>` | Returns matches array with confidence, scores object, explanation, 200/400/500 responses | 4 | `python-backend-engineer`, `backend-architect` |
| P2-T8 | Error Handling & Degradation | Graceful fallback to keyword-only if embeddings unavailable, timeout handling | Embedding service down → keyword-only works, query completes <500ms max | 1 | `python-backend-engineer` |
| P2-T9 | OpenTelemetry Instrumentation | Add spans for match analysis: keyword score, semantic score, context boost, composite score | Spans include timing, confidence threshold decisions, decision path | 1 | `python-backend-engineer` |

#### Quality Gates

- [ ] All P2 tasks completed with >80% unit test coverage
- [ ] Integration tests for match API endpoint (with mock embeddings)
- [ ] E2E test: `skillmeat match "pdf"` returns ranked results
- [ ] Performance: Match analysis <500ms for 100 artifacts
- [ ] Semantic scorer: Graceful fallback to keyword if Haiku unavailable
- [ ] API response schema documented (OpenAPI)

#### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Embedding service slow or unavailable | High | Implement caching, timeout <2s, fallback to keyword-only immediately |
| Match accuracy low (semantic matching not helpful) | High | Validate semantic similarity empirically; adjust weighting if needed; keyword fallback ensures basic functionality |
| Context detection false positives (wrong language boost) | Medium | Conservative boosting (1.1x max); test with diverse projects; log context decisions for debugging |

#### Dependencies

- Phase 1 completion (RatingManager, score storage)
- Phase 0 spike (embedding model decision)
- Embedding provider available (Haiku sub-skill or local model)

---

### Phase 3: Community Integration & Score Aggregation

**Duration**: 2 weeks | **Story Points**: 10 | **Type**: Backend integration

#### Phase Overview

Import community scores from GitHub and other sources, implement score aggregation framework, and manage score freshness decay.

*(Detailed breakdown in separate file: `PRD-001-phase-3-5.md`)*

#### Objectives

1. Implement score aggregation framework (weighted Bayesian averaging)
2. Add GitHub stars import via API
3. Implement score freshness decay (5%/month for community scores)
4. Add CLI commands: `skillmeat scores import` and `skillmeat scores refresh`
5. Define export format for future community registry

#### Quality Gates

- [ ] Community scores successfully imported and aggregated
- [ ] Score decay applied correctly (5%/month verified)
- [ ] Caching strategy prevents rate limit issues
- [ ] All imported scores have source attribution

#### Dependencies

- Phase 2 completion (match analysis working)
- GitHub API access (user provides token)

---

### Phase 4: Web UI Implementation

**Duration**: 2 weeks | **Story Points**: 10 | **Type**: Frontend

#### Phase Overview

Integrate confidence scoring into the web UI with score display, rating dialogs, and search improvements.

*(Detailed breakdown in separate file: `PRD-001-phase-3-5.md`)*

#### Objectives

1. Display confidence scores on artifact cards
2. Implement rating dialog component (star picker + feedback)
3. Sort search results by confidence by default
4. Add score breakdown expandable view
5. Display trust badges (Official/Verified/Community)

#### Quality Gates

- [ ] All score components visible on artifact cards
- [ ] Rating dialog accessible via keyboard
- [ ] Search results sort correctly by confidence
- [ ] Score breakdown explains all three components

#### Dependencies

- Phase 1 completion (score storage)
- Phase 2 completion (match analysis)
- Can parallelize with Phase 3

---

### Phase 5: Advanced Features & Customization

**Duration**: 1-2 weeks | **Story Points**: 3 | **Type**: Advanced features

#### Phase Overview

Add weight customization, analytics tracking, and anti-gaming protections.

*(Detailed breakdown in separate file: `PRD-001-phase-3-5.md`)*

#### Objectives

1. Support score weight customization: `skillmeat config set score-weights`
2. Implement historical success tracking (user confirmations)
3. Add anti-gaming protections (anomaly detection, rate limiting enforcement)
4. Optional rating export for community sharing
5. Score analytics dashboard

#### Quality Gates

- [ ] Weight customization works end-to-end
- [ ] Anti-gaming detections don't have false positives
- [ ] Analytics data collected and queryable

#### Dependencies

- Phases 1-4 complete

---

## Technical Design Decisions

### 1. Embedding Provider Strategy

**Decision**: Default to Haiku 4.5 sub-skill; allow local model fallback

**Rationale**:
- Haiku sub-skill: No setup required, proven quality, uses existing token budget
- Local model fallback: Offline capability, zero API cost if preferred
- API provider option: Deferred to future phases

**Implementation**:
- Feature flag: `EMBEDDING_PROVIDER` (values: "haiku", "local", "api")
- Graceful fallback: If Haiku unavailable, try local; if both unavailable, use keyword-only
- Caching: Per-artifact version to minimize API calls

**Files**:
- `skillmeat/core/scoring/embedding_provider.py` (abstract interface)
- `skillmeat/core/scoring/haiku_embedder.py` (sub-skill implementation)
- `skillmeat/core/scoring/local_embedder.py` (local model, Phase 2+)

---

### 2. Score Storage Architecture

**Decision**: SQLite local cache + optional manifest metadata

**Rationale**:
- SQLite: Efficient, no external dependencies, suitable for single-user desktop app
- Manifest metadata: Store high-level scores in manifest.toml for offline discovery
- Local-first: Respect privacy; never auto-export ratings

**Schema**:
```sql
-- ~/.skillmeat/collection/db/ratings.db

CREATE TABLE user_ratings (
  id INTEGER PRIMARY KEY,
  artifact_id TEXT NOT NULL,
  rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
  feedback TEXT,
  rated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  share_with_community BOOLEAN DEFAULT FALSE
);

CREATE TABLE community_scores (
  id INTEGER PRIMARY KEY,
  artifact_id TEXT NOT NULL,
  source TEXT NOT NULL,  -- "github_stars", "registry", "user_export"
  score REAL NOT NULL,   -- 0-100
  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  imported_from TEXT,    -- URL or export file
  UNIQUE(artifact_id, source)
);

CREATE TABLE match_history (
  id INTEGER PRIMARY KEY,
  query TEXT NOT NULL,
  artifact_id TEXT NOT NULL,
  confidence REAL NOT NULL,
  user_confirmed BOOLEAN,
  matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Files**:
- `skillmeat/storage/rating_store.py` (SQLite access layer)
- `skillmeat/core/scoring/score_calculator.py` (aggregation logic)

---

### 3. API Response Schema & Compatibility

**Decision**: Include `schema_version` field in all scoring responses; support versioning

**Rationale**:
- Future-proof: If scoring formula changes, agents can detect version
- Backward compatibility: Maintain old versions temporarily
- Extensibility: Room for additional fields without breaking clients

**Schema Example**:
```json
{
  "schema_version": "1",
  "matches": [
    {
      "artifact_id": "pdf-skill",
      "name": "pdf",
      "confidence": 92,
      "scores": {
        "trust": 95,
        "quality": 87,
        "match": 92
      },
      "rating_summary": {
        "user_rating": 4.5,
        "community_score": 87,
        "rating_count": 42
      },
      "explanation": "Comprehensive PDF processing with table extraction. Trusted source (Anthropic). 92 ratings. Excellent semantic match for your query."
    }
  ],
  "context": {
    "project_type": "python",
    "query": "process PDF"
  }
}
```

**Migration Path** (Phase 5+):
- Version 2: Add `versioned_scores` field for per-artifact-version scores
- Maintain v1 endpoint for backward compatibility
- Document v1 deprecation timeline (12+ months)

**Files**:
- `skillmeat/api/schemas/match_response.py`
- `skillmeat/api/schemas/scores_response.py`

---

### 4. Score Freshness & Decay

**Decision**: Apply 5%/month decay to community scores only; user ratings never decay

**Rationale**:
- Community scores represent trend signals (stale if artifact not updated)
- User ratings represent personal experience (timeless)
- Gradual decay prevents sudden score drops
- Manual refresh available for users who want immediate updates

**Formula**:
```python
# Community score decay
months_old = (now - last_updated).days / 30.0
decay_factor = (0.95 ** months_old)  # 5% decay per month
decayed_score = original_score * decay_factor

# Example: 80-point score from 3 months ago
# decayed_score = 80 * (0.95 ** 3) = 80 * 0.857 = 68.5
```

**Refresh Strategy**:
- Automatic refresh on `skillmeat match` if any score >60 days old
- Manual `skillmeat scores refresh` for immediate update
- Cache results for 1 day to prevent thrashing GitHub API

**Files**:
- `skillmeat/core/scoring/score_calculator.py` (decay logic)
- `skillmeat/cli/commands/scores.py` (refresh command)

---

### 5. Composite Confidence Formula

**Decision**: (Trust × 0.25) + (Quality × 0.25) + (Match × 0.50)

**Rationale**:
- Match relevance (50%): Most important; ensures user gets right tool
- Trust & Quality equal weight (25% each): Confidence in recommendation
- Weights configurable via feature flags (Phase 5)

**Component Details**:

| Component | Source | Range | Weight | Notes |
|-----------|--------|-------|--------|-------|
| Trust (0-100) | Source config | 50-100 | 0.25 | Official: 100, Verified: 80, Community: 60 |
| Quality (0-100) | User ratings (40%) + community (30%) + maintenance (20%) + compat (10%) | 0-100 | 0.25 | Averages with Bayesian priors for cold-start |
| Match (0-100) | Keyword (30%) + semantic (70%) if available, keyword-only fallback | 0-100 | 0.50 | Boosted by context detector (max 1.2x) |

**Cold-Start Priors** (artifacts with no ratings):
```
Quality = (user_rating × 0.4 + 50 × 0.3 + maintenance × 0.2 + compat × 0.1)
         = (missing + 15 + maintenance + compat)
         ≥ 30 (minimum)

Trust = source_config_value (mandatory)
```

**Files**:
- `skillmeat/core/scoring/score_calculator.py`
- Feature flags: `skillmeat/core/config.py`

---

## Quality Gates & Testing Strategy

### Unit Testing

**Target Coverage**: >80% across all scoring modules

| Module | Test Focus | Priority |
|--------|-----------|----------|
| `MatchAnalyzer` | Keyword scoring accuracy, edge cases (empty query, special chars) | Critical |
| `SemanticScorer` | Graceful degradation, caching, timeout handling | Critical |
| `QualityScorer` | Missing data handling, prior application, aggregation formula | High |
| `ScoreCalculator` | Composite formula, weight application, edge cases (all-zero scores) | High |
| `RatingManager` | CRUD operations, export format, privacy flag | High |

**Tools**:
- `pytest` with `pytest-cov` for coverage reporting
- Mock Haiku embeddings for reproducible tests
- Fixtures for artifact catalogs with known properties

### Integration Testing

| Test Scenario | Expected Outcome | Status |
|---------------|-----------------|--------|
| `skillmeat rate <artifact> --rating 5` | Rating persisted, visible in `skillmeat show --scores` | Phase 1 |
| `skillmeat match "pdf"` without embeddings | Returns keyword-only results, no errors | Phase 2 |
| `skillmeat match "pdf"` with embeddings | Returns semantic results with higher confidence | Phase 2 |
| Import GitHub stars for 100 artifacts | Scores imported, decay applied, <5s total time | Phase 3 |

### E2E Testing

**User Journey**: Search → Deploy → Rate → Verify score updates

```bash
# Setup
skillmeat init
skillmeat add anthropics/skills/pdf@latest

# Test Phase 2
skillmeat match "extract tables from PDF" --limit 3
# Expected: pdf skill in top result, confidence >85%

# Test Phase 1
skillmeat rate pdf --rating 5 --feedback "Great extraction"
skillmeat show pdf --scores
# Expected: User rating 5 visible in quality breakdown

# Test Phase 3
skillmeat scores refresh
skillmeat show pdf --scores
# Expected: Community score updated, decay applied
```

### Performance Benchmarks

**Target Metrics**:

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Match (100 artifacts, no embeddings) | <200ms | Keyword-only baseline |
| Match (100 artifacts, with embeddings) | <500ms | Including caching hits |
| API: GET /match | <200ms | Excluding network latency |
| Rating submission | <100ms | DB write only |
| Score aggregation (20 sources) | <50ms | Per-artifact calculation |

**Tools**:
- `pytest-benchmark` for automated timing
- Load testing with 500+ artifacts
- Profile with `cProfile` to identify bottlenecks

---

## Risk Management

### Phase-Level Risks

| Phase | Risk | Impact | Likelihood | Mitigation |
|-------|------|--------|-----------|-----------|
| **0** | Embedding model research inconclusive | High | Low | Document multiple options; implement abstraction layer for easy switching |
| **1** | SQLite schema needs redesign mid-development | Medium | Medium | Design for extensibility; document migration path before Phase 2 |
| **1** | Privacy concerns delay user adoption | Medium | Medium | Anonymous by default; clear opt-in for attribution; highlight privacy in docs |
| **2** | Semantic similarity poor quality | High | Low | Extensive testing with real queries; Haiku proven quality; keyword fallback ensures baseline |
| **2** | Embedding service rate limits hit | High | Medium | Aggressive caching; batch requests; GitHub token strategy for GitHub API |
| **3** | Community score sources unavailable | Medium | Medium | Start with GitHub only; add registry integration Phase 4; graceful handling if source down |
| **4** | Web UI rating dialog complex | Medium | Low | Use existing Radix UI star component; keep feedback optional; iterate if feedback >UX issues |
| **5** | Anti-gaming false positives | Medium | Medium | Conservative thresholds; monitor with analytics; easy override for legitimate bulk operations |

### Cross-Phase Dependencies

```
Phase 0 (SPIKE)
    ├─ Decision: Embedding model → Phase 2 blocker
    ├─ Decision: Score weights → Phase 1 blocker
    └─ Decision: Schema strategy → Phase 1 blocker
        ↓
Phase 1 (Foundation)
    ├─ RatingManager → Phase 3 blocker
    ├─ Score storage schema → Phase 3 blocker
    └─ Quality scorer → Phase 2 input
        ↓
Phase 2 (Match)
    ├─ MatchAnalyzer → Phase 4 blocker (search sorting)
    ├─ ScoreCalculator → Phase 3 blocker
    └─ Match API → Phase 4 input
        ↓
Phase 3 & 4 (Parallel)
    ├─ Community scores → Phase 4 display
    └─ Web UI → Phase 5 enhancements
        ↓
Phase 5 (Advanced)
    └─ All prior phases must be complete
```

---

## Orchestration Quick Reference

This section is for Opus orchestration of subagent work. Each phase has defined batches for parallel execution.

### Phase 1 Orchestration

**Parallel Batch 1** (Design & Setup):
```
Task("data-layer-expert", "P1-T1: Extend ArtifactRating schema and create migrations")
Task("data-layer-expert", "P1-T2: Create SQLite schema for ratings database with migrations")
```

**Sequential After Batch 1**:
```
Task("python-backend-engineer", "P1-T3: Implement RatingManager in skillmeat/storage/rating_store.py")
Task("python-backend-engineer", "P1-T4: Implement QualityScorer class for rating aggregation")
```

**Parallel Batch 2** (CLI & API):
```
Task("python-backend-engineer", "P1-T5: Implement 'skillmeat rate' CLI command")
Task("python-backend-engineer", "P1-T6: Implement 'skillmeat show --scores' CLI enhancement")
Task("python-backend-engineer", "P1-T7: API endpoint GET /artifacts/{id}/scores")
Task("python-backend-engineer", "P1-T8: API endpoint POST /artifacts/{id}/ratings")
```

**Final**:
```
Task("python-backend-engineer", "P1-T9: Add OpenTelemetry instrumentation for rating operations")
```

### Phase 2 Orchestration

**Parallel Batch 1** (Core Scoring):
```
Task("python-backend-engineer", "P2-T1: Implement MatchAnalyzer with keyword scoring")
Task("python-backend-engineer", "P2-T2: Implement SemanticScorer with Haiku embeddings")
Task("python-backend-engineer", "P2-T3: Implement ContextBooster for project type detection")
Task("python-backend-engineer", "P2-T4: Implement ScoreCalculator for composite formula")
```

**Parallel Batch 2** (CLI & API):
```
Task("python-backend-engineer", "P2-T5: Implement 'skillmeat match' CLI command")
Task("python-backend-engineer", "P2-T6: Implement 'skillmeat match --json' agent output")
Task("python-backend-engineer", "P2-T7: API endpoint GET /api/v1/match")
```

**Final**:
```
Task("python-backend-engineer", "P2-T8: Error handling and degradation to keyword-only")
Task("python-backend-engineer", "P2-T9: OpenTelemetry instrumentation for match operations")
```

### Phase 3-5 Orchestration

*See `PRD-001-phase-3-5.md` for detailed task breakdown and orchestration commands*

### Testing & Documentation Orchestration

**Throughout all phases**:
```
Task("ui-engineer-enhanced", "[Web UI tasks] - Phase 4 components")
Task("documentation-writer", "[Documentation] - API docs, user guides, ADRs")
```

---

## Files & Components Reference

### Core Scoring Module

**Location**: `skillmeat/core/scoring/`

```
scoring/
├── __init__.py
├── embedding_provider.py          # Abstract interface for embeddings
├── haiku_embedder.py              # Haiku 4.5 sub-skill implementation
├── local_embedder.py              # Local embedding model (Phase 2+)
├── match_analyzer.py              # Keyword + semantic matching
├── score_calculator.py            # Composite confidence formula
├── quality_scorer.py              # User ratings + community aggregation
├── context_booster.py             # Project context detection
└── trust_config.py                # Source trust configuration
```

### Storage Layer

**Location**: `skillmeat/storage/`

- `rating_store.py` - SQLite access for user ratings, community scores, match history

### CLI Commands

**Location**: `skillmeat/cli/commands/`

```
commands/
├── match.py                       # `skillmeat match "<query>"`
├── rate.py                        # `skillmeat rate <artifact>`
└── scores.py                      # `skillmeat scores import/refresh`
```

### API Routers

**Location**: `skillmeat/api/routers/`

```
routers/
├── match.py                       # GET /api/v1/match
├── ratings.py                     # POST /api/v1/artifacts/{id}/ratings
└── scores.py                      # GET /api/v1/artifacts/{id}/scores
```

### API Schemas

**Location**: `skillmeat/api/schemas/`

```
schemas/
├── match_response.py              # Match query response schema
├── scores_response.py             # Score fetch response schema
└── rating_request.py              # Rating submission request schema
```

---

## Acceptance Criteria Summary

### Functional Acceptance

- [ ] Phase 1: `skillmeat rate` and `skillmeat show --scores` work end-to-end
- [ ] Phase 2: `skillmeat match` returns ranked results with confidence >85% for common queries
- [ ] Phase 3: Community scores imported, decay applied, `skillmeat scores refresh` works
- [ ] Phase 4: Web UI displays scores on cards, rating dialog functional, search sorts by confidence
- [ ] Phase 5: Weight customization works, analytics data collected

### Technical Acceptance

- [ ] All new components in `skillmeat/core/scoring/` follow MeatyPrompts layered architecture
- [ ] Database schema extensible for future versions (migration path documented)
- [ ] All API responses include `schema_version: "1"` field
- [ ] Semantic similarity gracefully degrades to keyword-only if unavailable
- [ ] All scoring components >80% unit test coverage with integration tests

### Quality Acceptance

- [ ] Performance: Match <500ms for 100 artifacts, API endpoints <200ms
- [ ] Match accuracy: Top result correct 85%+ of the time (sampling-based measurement)
- [ ] User rating participation: >30% of active users use `skillmeat rate`
- [ ] Privacy: User ratings local-only, no auto-export without explicit consent
- [ ] Security: Rate limiting enforced, input validation on all API endpoints

---

## Documentation & Knowledge Transfer

### For Implementation Teams

1. **Architecture Overview**: `PRD-001-implementation-plan.md` (this file)
2. **Phase-Specific Details**: `PRD-001-phase-3-5.md` (phases 3-5 detailed breakdown)
3. **Progress Tracking**: `.claude/progress/PRD-001-confidence-scoring/phase-N-progress.md` (created per phase)
4. **API Documentation**: Docstrings in routers, OpenAPI spec at `/api/v1/docs`
5. **Component Design**: ADR in `.claude/docs/adr/` (created per major decision)

### For Users

1. **User Guide**: How to search with match, rate artifacts, understand score breakdown
2. **CLI Help Text**: `skillmeat match --help`, `skillmeat rate --help`, `skillmeat scores --help`
3. **Web UI**: In-app tooltips explaining scores and confidence thresholds
4. **Troubleshooting**: FAQ section in docs covering common issues (embeddings unavailable, etc.)

---

## Success Measurement

### Quantitative Metrics

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|-------------------|
| Match accuracy (top result) | 0% (n/a) | 85%+ | Sample 20 user queries post-release |
| User rating participation | 0% | >30% | Track `skillmeat rate` CLI invocations |
| Discovery time | 15-20 min | 7-10 min | A/B test with pre/post launch |
| Confidence score accuracy | N/A | 0.7+ Pearson correlation with user satisfaction | Correlate system scores vs. user ratings |
| Community score coverage | 0% | 60%+ of artifacts | Count non-null `community_score` values |

### Qualitative Metrics

- User feedback on score transparency and trust-building
- Agent developer satisfaction with confidence signals for recommendations
- Community engagement: exports and cross-collection sharing

---

## Sign-Off & Next Steps

**Document Status**: DRAFT (pending Phase 0 SPIKE completion and team review)

### Approval Checkpoints

1. **PRD Review** (Pre-Phase 0): Confirm requirements and scope
2. **SPIKE Review** (End of Phase 0): Approve embedding model and weight decisions
3. **Phase 1 Planning** (Start of Phase 1): Detailed task estimation and resource allocation
4. **Phase 2 Kickoff** (Start of Phase 2): Confirm MatchAnalyzer design before implementation

### Next Actions

1. Conduct Phase 0 SPIKE research (1 week)
2. Create Phase 1 progress tracking file (`.claude/progress/PRD-001-confidence-scoring/phase-1-progress.md`)
3. Begin Phase 1 data model work (data-layer-expert, python-backend-engineer)
4. Document decisions in Architecture Decision Records

**Implementation Lead**: Claude Code (Opus)
**Phases 1-2 Owner**: python-backend-engineer (Sonnet)
**Phases 3-4 Owner**: python-backend-engineer + ui-engineer-enhanced (Sonnet)
**Phase 5 Owner**: All teams (optimization and integration)

**Created**: 2025-12-22
**Last Updated**: 2025-12-22
