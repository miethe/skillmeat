# PRD-001 Implementation Plan - Document Index

## Quick Links

| Document | Purpose | Read Time | Size |
|----------|---------|-----------|------|
| **[README.md](README.md)** | Start here: Overview and navigation guide | 5 min | 10 KB |
| **[PRD-001-implementation-plan.md](PRD-001-implementation-plan.md)** | Main plan: Phases 0-2, technical decisions, orchestration | 20 min | 33 KB |
| **[PRD-001-phase-3-5.md](PRD-001-phase-3-5.md)** | Detailed plan: Phases 3-5, component specs, code examples | 20 min | 30 KB |
| **[../PRD-001-confidence-scoring.md](../PRD-001-confidence-scoring.md)** | Original PRD: Requirements, success metrics, rationale | 30 min | 37 KB |

## Phase Navigation

### Phase 0: SPIKE & Research
- **Location**: PRD-001-implementation-plan.md → Phase 0 section
- **Duration**: 1 week (research only)
- **Deliverables**: Embedding model recommendation, weight strategy, anti-gaming approach
- **Blocking**: All other phases depend on Phase 0 decisions

### Phase 1: Foundation - Data Models & Local Ratings
- **Location**: PRD-001-implementation-plan.md → Phase 1 section
- **Duration**: 2-3 weeks
- **Story Points**: 13
- **Tasks**: 9 (schema, RatingManager, CLI commands, API endpoints)
- **Blocking**: Phase 2 depends on Phase 1 completion
- **Key Components**: ArtifactRating schema, SQLite database, rating CLI/API

### Phase 2: Match Analysis Engine
- **Location**: PRD-001-implementation-plan.md → Phase 2 section
- **Duration**: 2-3 weeks
- **Story Points**: 16
- **Tasks**: 9 (keyword scoring, embeddings, context boost, scoring formula)
- **Blocking**: Phases 3 & 4 depend on Phase 2
- **Key Components**: MatchAnalyzer, SemanticScorer, ScoreCalculator

### Phase 3: Community Integration & Score Aggregation
- **Location**: PRD-001-phase-3-5.md → Phase 3 section
- **Duration**: 2 weeks
- **Story Points**: 10
- **Tasks**: 7 (aggregation framework, GitHub import, decay, CLI commands)
- **Parallel With**: Phase 4 (Web UI)
- **Key Components**: ScoreAggregator, GitHub importer, decay algorithm

### Phase 4: Web UI Implementation
- **Location**: PRD-001-phase-3-5.md → Phase 4 section
- **Duration**: 2 weeks
- **Story Points**: 10
- **Tasks**: 9 (score display, rating dialog, search sorting, accessibility)
- **Parallel With**: Phase 3 (Community Integration)
- **Key Components**: ScoreBadge, RatingDialog, ScoreBreakdown, TrustBadges

### Phase 5: Advanced Features & Customization
- **Location**: PRD-001-phase-3-5.md → Phase 5 section
- **Duration**: 1-2 weeks
- **Story Points**: 3
- **Tasks**: 5 (weight customization, analytics, anti-gaming, rating export)
- **Sequential After**: All prior phases
- **Key Components**: Config system, analytics framework, anti-gaming detection

## By Role

### Product Managers / Project Leads
1. Read: [README.md](README.md) (5 min)
2. Read: PRD-001-implementation-plan.md → Executive Summary (5 min)
3. Review: Phase breakdown table and critical path (5 min)
4. Review: Risk Management matrix (10 min)
5. **Total**: ~25 minutes for full overview

### Backend Engineers (Python)
1. Read: [README.md](README.md) → Backend section
2. Phase 1: PRD-001-implementation-plan.md → Phase 1 section (20 min)
3. Phase 2: PRD-001-implementation-plan.md → Phase 2 section (20 min)
4. Phase 3: PRD-001-phase-3-5.md → Phase 3 section (20 min)
5. Phase 5: PRD-001-phase-3-5.md → Phase 5 section (10 min)
6. **Total**: ~70 minutes for backend focus

### Frontend Engineers (React/TypeScript)
1. Read: [README.md](README.md) → Frontend section
2. Phase 4: PRD-001-phase-3-5.md → Phase 4 section (30 min)
3. Phase 5: PRD-001-phase-3-5.md → Phase 5.T5 (5 min, optional)
4. Review: Component structures and code examples (10 min)
5. **Total**: ~45 minutes for frontend focus

### Data / Database Engineers
1. Read: [README.md](README.md) → Data section
2. Phase 1: PRD-001-implementation-plan.md → Score Storage Architecture (10 min)
3. Phase 3: PRD-001-phase-3-5.md → Caching Strategy (10 min)
4. Review: Schema definitions and migration strategy (5 min)
5. **Total**: ~25 minutes for data focus

### Documentation Writers
1. Read: Both implementation plans (30 min)
2. Review: API schemas and component structures (20 min)
3. Check: Docstring patterns and component names (10 min)
4. **Total**: ~60 minutes for documentation focus

## Key Technical Decisions

### 1. Embedding Provider (Phase 0 decision)
**Document**: PRD-001-implementation-plan.md → Technical Design Decisions → Section 1
- Default: Haiku 4.5 sub-skill
- Fallback: Local model
- Implementation: `skillmeat/core/scoring/embedding_provider.py`

### 2. Score Storage (Phase 1 decision)
**Document**: PRD-001-implementation-plan.md → Technical Design Decisions → Section 2
- Primary: SQLite local cache
- Secondary: Manifest metadata (optional)
- Schema: `~/.skillmeat/collection/db/ratings.db`

### 3. API Schema Versioning (All phases)
**Document**: PRD-001-implementation-plan.md → Technical Design Decisions → Section 3
- Include `schema_version: "1"` in all scoring responses
- Migration path documented for future versions

### 4. Score Decay (Phase 3)
**Document**: PRD-001-phase-3-5.md → Phase 3 → Technical Details → Decay Formula
- Formula: `0.95 ^ months_old`
- Example: 80-point score from 3 months ago = 68.5 points

### 5. Composite Scoring Formula (Phase 1+)
**Document**: PRD-001-implementation-plan.md → Technical Design Decisions → Section 5
- Formula: `(Trust × 0.25) + (Quality × 0.25) + (Match × 0.50)`
- Configurable weights (Phase 5)

## Story Points by Phase

```
Phase 0:  0 pts (research only)
Phase 1: 13 pts (Foundation)
Phase 2: 16 pts (Match Analysis)
Phase 3: 10 pts (Community Integration)
Phase 4: 10 pts (Web UI)
Phase 5:  3 pts (Advanced Features)
────────────────
Total:   52 pts (12-14 weeks)
```

## Task Count by Phase

- Phase 0: 1 (research spike)
- Phase 1: 9 tasks
- Phase 2: 9 tasks
- Phase 3: 7 tasks
- Phase 4: 9 tasks
- Phase 5: 5 tasks

**Total: 39 implementation tasks + 1 research spike**

## Orchestration Commands

Ready-to-execute `Task()` commands available in:

- **Phase 1**: PRD-001-implementation-plan.md → Phase 1 Orchestration
- **Phase 2**: PRD-001-implementation-plan.md → Phase 2 Orchestration
- **Phase 3**: PRD-001-phase-3-5.md → Phase 3 Orchestration
- **Phase 4**: PRD-001-phase-3-5.md → Phase 4 Orchestration
- **Phase 5**: PRD-001-phase-3-5.md → Phase 5 Orchestration

Example format:
```
Task("python-backend-engineer", "P1-T1: Extend ArtifactRating schema...")
```

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Match accuracy | 85%+ | Top result correct (sampling) |
| User participation | >30% | `skillmeat rate` usage tracking |
| Discovery time | 50% reduction | Before/after A/B test |
| Confidence correlation | >0.7 Pearson | System scores vs. user satisfaction |
| Community coverage | 60%+ | Artifacts with non-null scores |

## Next Steps

1. **Day 1**: Review PRD-001-confidence-scoring.md (original PRD)
2. **Day 2**: Team approval of PRD-001-implementation-plan.md
3. **Week 1**: Conduct Phase 0 SPIKE (embedding model research)
4. **Week 2**: Phase 1 implementation planning
5. **Week 3**: Begin Phase 1 implementation

## Questions & Support

- **General questions**: Refer to [README.md](README.md)
- **Phase-specific questions**: See phase section in appropriate document
- **Technical decisions**: PRD-001-implementation-plan.md → Technical Design Decisions
- **Code details**: PRD-001-phase-3-5.md → Technical Details sections

## File Locations

All documents stored in:
```
/Users/miethe/dev/homelab/development/skillmeat/.claude/docs/prd/impl/
```

Progress tracking files (created per phase):
```
/Users/miethe/dev/homelab/development/skillmeat/.claude/progress/PRD-001-confidence-scoring/
```

## Document Status

- **PRD-001-implementation-plan.md**: DRAFT (pending Phase 0 completion)
- **PRD-001-phase-3-5.md**: DRAFT (pending Phase 0 completion)
- **README.md**: FINAL
- **INDEX.md**: FINAL

Last Updated: 2025-12-22
