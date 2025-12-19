# Feature Request: Confidence Scoring & Match Analysis System

**Requested**: 2025-12-18
**Priority**: High
**Category**: Core Feature Enhancement
**Related Spec**: `.claude/specs/skillmeat-cli-skill-spec.md`

---

## Summary

Implement a multi-dimensional confidence scoring system that enables high-confidence artifact discovery for both human users and AI agents. The system combines source trustworthiness, user/community ratings, and LLM-powered semantic matching to help users find the right artifacts faster.

---

## Problem Statement

### Current State

1. **Artifact discovery is keyword-based**: Users must know exact names or guess keywords
2. **No quality signals**: All artifacts appear equal regardless of quality or trustworthiness
3. **No semantic understanding**: "process PDFs" doesn't match "pdf skill" well
4. **AI agents lack confidence**: Cannot reliably assess which artifact best fits a need
5. **No user feedback loop**: No way to rate artifacts or share experiences

### Impact

- Users waste time trying multiple artifacts before finding the right one
- AI agents make poor suggestions or over-suggest due to uncertainty
- Community knowledge about artifact quality isn't captured or shared
- Trust decisions are left entirely to the user without guidance

---

## Proposed Solution

### Three-Pillar Scoring System

```
┌─────────────────────────────────────────────────────────────┐
│                    CONFIDENCE SCORE                         │
│                  (Weighted Composite)                       │
├────────────────┬────────────────┬───────────────────────────┤
│  Source Trust  │ Artifact Quality│  Match Relevance          │
│    (25%)       │     (25%)       │      (50%)                │
├────────────────┼────────────────┼───────────────────────────┤
│ • Official src │ • User ratings │ • Keyword match           │
│ • Verified pub │ • Community    │ • Semantic similarity     │
│ • Signatures   │ • Maintenance  │ • Context relevance       │
│ • Usage count  │ • Compatibility│ • Historical success      │
└────────────────┴────────────────┴───────────────────────────┘
```

### Key Features

#### 1. Source Trust Scoring
- Configure trust levels per source in manifest
- Automatic trust boosts for signed artifacts
- Usage-based trust accumulation

#### 2. User Rating System
- 1-5 star ratings stored locally
- Optional feedback text
- Rating prompts after artifact usage
- Export format for community sharing

#### 3. Community Scoring
- Import scores from multiple sources (registry, GitHub stars, npm)
- Weighted aggregation with trust factors
- Score freshness decay over time
- Anti-gaming protections

#### 4. Match Analysis Engine
- Keyword matching against artifact metadata
- Semantic similarity using embeddings
- Project context boosting
- Historical success tracking

#### 5. CLI Commands
```bash
skillmeat match "<query>"      # Find best matches with scores
skillmeat rate <artifact>      # Rate an artifact
skillmeat show --scores        # View artifact scores
skillmeat scores import        # Import community scores
skillmeat scores refresh       # Update all scores
```

#### 6. API Endpoints
```
GET  /api/v1/match?q=<query>              # Match analysis
GET  /api/v1/artifacts/{id}/scores        # Get artifact scores
POST /api/v1/artifacts/{id}/ratings       # Submit rating
GET  /api/v1/scores/community             # Get community scores
POST /api/v1/scores/import                # Import scores
```

---

## User Stories

### Human Users

1. **As a developer**, I want to search for artifacts using natural language so that I find the right tool without knowing exact names.

2. **As a developer**, I want to see trust and quality scores for artifacts so that I can make informed decisions about what to install.

3. **As a developer**, I want to rate artifacts I've used so that my experience helps others.

4. **As a power user**, I want to customize score weights so that I can prioritize factors important to me (e.g., trust over popularity).

### AI Agents

5. **As an AI agent**, I want to query match confidence so that I only suggest artifacts when I'm reasonably sure they're relevant.

6. **As an AI agent**, I want structured match analysis output so that I can explain my recommendations to users.

7. **As an AI agent**, I want context-aware matching so that recommendations consider the project's technology stack.

### Community

8. **As a community member**, I want to share my ratings so that the community benefits from my experience.

9. **As a community member**, I want to see aggregated ratings from multiple sources so that I get a comprehensive quality picture.

---

## Technical Requirements

### Data Model Changes

#### Artifact Metadata Extension
```python
class ArtifactRating(BaseModel):
    user_rating: Optional[float] = None  # 1-5 stars
    user_feedback: Optional[str] = None
    rated_at: Optional[datetime] = None
    community_score: Optional[float] = None  # 0-100
    community_rating_count: Optional[int] = None
    trust_score: Optional[float] = None  # 0-100
    last_score_update: Optional[datetime] = None
```

#### Source Configuration Extension
```python
class SourceConfig(BaseModel):
    # Existing fields...
    trust_score: int = 50  # 0-100 base trust
    verified: bool = False
    trust_modifiers: Dict[str, int] = {}  # e.g., {"signed": 10}
```

### New Components

#### Match Analysis Engine
```python
class MatchAnalyzer:
    def analyze(self, query: str, artifacts: List[Artifact],
                context: ProjectContext) -> List[MatchResult]:
        """Compute match scores for query against artifacts."""

    def compute_keyword_score(self, query: str, artifact: Artifact) -> float:
        """Direct keyword matching."""

    def compute_semantic_score(self, query: str, artifact: Artifact) -> float:
        """Embedding-based similarity."""

    def apply_context_boost(self, score: float, artifact: Artifact,
                           context: ProjectContext) -> float:
        """Boost scores based on project context."""
```

#### Rating Manager
```python
class RatingManager:
    def rate_artifact(self, artifact_id: str, rating: int,
                     feedback: Optional[str] = None) -> None:
        """Store user rating for artifact."""

    def get_ratings(self, artifact_id: str) -> ArtifactRating:
        """Get all ratings for artifact."""

    def export_ratings(self, format: str = "json") -> str:
        """Export ratings for community sharing."""

    def import_community_scores(self, source: str) -> int:
        """Import scores from external source."""
```

#### Score Calculator
```python
class ScoreCalculator:
    def compute_confidence(self, artifact: Artifact, match_score: float,
                          weights: ScoreWeights) -> ConfidenceScore:
        """Compute composite confidence score."""

    def apply_decay(self, score: float, last_update: datetime) -> float:
        """Apply freshness decay to score."""
```

### Storage Requirements

- **Local ratings**: Store in collection manifest (TOML)
- **Community scores**: Cache in local SQLite or JSON file
- **Embeddings**: Pre-computed and cached for artifacts
- **Match history**: Store in analytics database

### External Integrations

| Integration | Purpose | Priority |
|-------------|---------|----------|
| GitHub API | Import stars as quality signal | P1 |
| SkillMeat Registry | Sync community scores | P1 |
| Local embedding model | Semantic similarity | P1 |
| npm Registry | Download counts for JS artifacts | P2 |
| External rating APIs | Import from other tools | P3 |

---

## API Design

### Match Analysis Endpoint

```
GET /api/v1/match?q={query}&limit={n}&min_confidence={score}

Response:
{
  "query": "process PDF and extract tables",
  "matches": [
    {
      "artifact": {
        "id": "pdf",
        "name": "PDF Processing",
        "source": "anthropics/example-skills/pdf"
      },
      "confidence": 89,
      "scores": {
        "trust": 95,
        "quality": 87,
        "match": 89
      },
      "breakdown": {
        "keyword_match": 90,
        "semantic_similarity": 95,
        "context_relevance": 85,
        "historical_success": 80
      },
      "explanation": "High semantic match for PDF processing with table extraction capability"
    }
  ],
  "context": {
    "project_type": "python",
    "existing_artifacts": ["docx"]
  }
}
```

### Rating Submission Endpoint

```
POST /api/v1/artifacts/{artifact_id}/ratings

Request:
{
  "rating": 4,
  "feedback": "Great for extraction, forms could be better",
  "use_case": "table-extraction",
  "share_with_community": true
}

Response:
{
  "success": true,
  "artifact_id": "pdf",
  "new_scores": {
    "user_rating": 4.0,
    "community_score": 87.2
  }
}
```

---

## UI/UX Considerations

### CLI Output

```
$ skillmeat match "spreadsheet processing"

Best matches for "spreadsheet processing":

  1. xlsx (92% confidence) ⭐⭐⭐⭐⭐
     Comprehensive spreadsheet manipulation
     Source: anthropics/example-skills (Trusted ✓)
     Community: 4.7/5 (142 ratings)

  2. csv-tools (67% confidence) ⭐⭐⭐⭐
     CSV-specific processing
     Source: community/data-tools (Verified)
     Community: 4.2/5 (89 ratings)

Would you like to add any of these? [1/2/n]:
```

### Web UI Components

1. **Artifact Card Enhancement**: Show trust badge, quality stars, match %
2. **Search Results**: Sort by confidence, filter by minimum score
3. **Rating Dialog**: Star rating + optional feedback after use
4. **Score Breakdown**: Expandable section showing score components

---

## Implementation Phases

### Phase 1: Foundation (2-3 sprints)
- [ ] Data model extensions (ArtifactRating, SourceConfig)
- [ ] Basic trust score configuration
- [ ] User rating storage (local manifest)
- [ ] `skillmeat rate` CLI command
- [ ] `skillmeat show --scores` command

### Phase 2: Match Analysis (2-3 sprints)
- [ ] Keyword matching engine
- [ ] Semantic similarity with local embeddings
- [ ] Project context detection
- [ ] `skillmeat match` CLI command
- [ ] Match analysis API endpoint

### Phase 3: Community Integration (2 sprints)
- [ ] Score aggregation framework
- [ ] GitHub stars import
- [ ] Score export format
- [ ] `skillmeat scores import/export` commands
- [ ] Score freshness decay

### Phase 4: Web UI (2 sprints)
- [ ] Score display on artifact cards
- [ ] Rating dialog component
- [ ] Search with confidence sorting
- [ ] Score breakdown view

### Phase 5: Advanced (1-2 sprints)
- [ ] Historical success tracking
- [ ] Score weight customization
- [ ] Anti-gaming protections
- [ ] Score analytics dashboard

---

## Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| Match accuracy | >85% top result correct | User feedback sampling |
| User satisfaction correlation | >0.7 | Score vs rating correlation |
| Rating participation | >30% users rate | Analytics tracking |
| Discovery time improvement | >50% faster | A/B testing |
| Agent suggestion acceptance | >80% at high confidence | Analytics tracking |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Gaming of community scores | Medium | Anti-gaming protections, require usage |
| Embedding model performance | High | Start with lightweight local model |
| Score staleness | Medium | Automatic decay + refresh prompts |
| Privacy concerns with ratings | Low | Anonymous by default, opt-in attribution |
| API rate limits (GitHub) | Medium | Caching, batch requests, token auth |

---

## Dependencies

- **Embedding model**: Need to select and integrate (recommend sentence-transformers)
- **SQLite**: For local score caching
- **GitHub API**: For stars import
- **Analytics system**: For tracking success metrics

---

## Open Questions

1. Should we build our own community registry or integrate with existing?
2. What's the minimum viable embedding model for semantic matching?
3. How to handle conflicting scores from different sources?
4. Should scores be versioned with artifact versions?

---

## References

- Skill Spec: `.claude/specs/skillmeat-cli-skill-spec.md` (Section: Confidence Scoring)
- Similar systems: npm quality scores, VS Code extension ratings, Homebrew analytics
