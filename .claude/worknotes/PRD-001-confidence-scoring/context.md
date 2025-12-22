---
type: context
prd: "PRD-001-confidence-scoring"
title: "Confidence Scoring System Context"
created: 2025-12-22
last_updated: 2025-12-22
status: active
---

# PRD-001: Confidence Scoring System - Context

## Overview

Multi-dimensional confidence scoring system combining source trust (25%), artifact quality (25%), and semantic match relevance (50%) to enable high-confidence artifact discovery.

## Key Technical Decisions

### Embedding Provider Strategy
- **Primary**: Haiku 4.5 sub-skill (default)
- **Fallback**: Keyword-only matching
- **Future**: Local embeddings, external API

### Score Storage
- **User ratings**: Local SQLite + manifest metadata
- **Community scores**: SQLite cache with decay
- **Match history**: Analytics database

### Formula
```
Confidence = (Trust × 0.25) + (Quality × 0.25) + (Match × 0.50)
```

### API Schema Version
- Include `schema_version: "v1"` in all responses
- Backward compatibility via version negotiation

## File Locations

### Core Components
- `skillmeat/core/scoring.py` - ScoreCalculator, QualityScorer
- `skillmeat/core/match_analyzer.py` - MatchAnalyzer, KeywordScorer
- `skillmeat/core/semantic_scorer.py` - SemanticScorer
- `skillmeat/core/context_booster.py` - ContextBooster
- `skillmeat/storage/rating_store.py` - RatingManager

### CLI Commands
- `skillmeat/cli/commands/match.py`
- `skillmeat/cli/commands/rate.py`
- `skillmeat/cli/commands/scores.py`

### API Endpoints
- `skillmeat/api/routers/match.py`
- `skillmeat/api/routers/scores.py`

## Dependencies

- **Phase 0 SPIKE**: Research embedding models, weights
- **External**: GitHub API (for stars import)
- **Internal**: Existing artifact model, FastAPI infrastructure

## Open Questions (Resolved)

| Question | Decision |
|----------|----------|
| Embedding model? | Haiku sub-skill default, with fallback |
| Score weights? | 25/25/50 (trust/quality/match) |
| Decay rate? | 5%/month for community, none for user |
| Anti-gaming? | Rate limiting + anomaly detection |

## Session Notes

[Add session-specific notes here as work progresses]
