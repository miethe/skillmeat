---
title: "PRD-001 Phase 3-5 Details: Community Integration, Web UI, Advanced Features"
description: "Detailed task breakdown for phases 3-5 of confidence scoring system implementation"
prd_reference: "PRD-001-confidence-scoring.md"
implementation_plan_reference: "PRD-001-implementation-plan.md"
created: 2025-12-22
---

# Phase 3-5 Detailed Implementation Guide

This document provides detailed task breakdowns for phases 3, 4, and 5 of the Confidence Scoring System. Refer to `PRD-001-implementation-plan.md` for phase 0-2 details and overall orchestration strategy.

---

## Phase 3: Community Integration & Score Aggregation

**Duration**: 2 weeks | **Story Points**: 10 | **Type**: Backend integration
**Parallel With**: Phase 4 (Web UI) - can proceed independently

### Phase Overview

Phase 3 extends the scoring system with community sources, implementing imports from GitHub and other platforms, aggregating scores with Bayesian methods, and managing score freshness through decay algorithms. This phase provides the data foundation for Phase 4's Web UI display.

### Objectives

1. Implement score aggregation framework supporting multiple sources
2. Add GitHub stars import with caching strategy
3. Implement 5%/month decay for community scores
4. Add CLI commands for manual imports and cache refresh
5. Document export format for future community registry

### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Story Points | Assigned Agent(s) |
|---------|-----------|-------------|-------------------|--------------|------------------|
| P3-T1 | Implement Score Aggregation Framework | Framework for combining scores from multiple sources (user ratings, GitHub, registry) with Bayesian weighting | `ScoreAggregator` class handles 3+ sources, preserves per-source scores, applies weights, unit tests >80% | 3 | `python-backend-engineer` |
| P3-T2 | GitHub Stars Import | Fetch artifact repository stars via GitHub API, map to quality signal (1000+ stars = higher score) | Import works for public repos, caching <1 day old, handles missing repos gracefully (404 → skip) | 3 | `python-backend-engineer`, `backend-architect` |
| P3-T3 | Score Freshness Decay | Apply 5%/month decay formula to community scores, preserve user ratings (no decay) | Decay calculated correctly, refresh resets age, decay applied on score retrieval | 2 | `python-backend-engineer` |
| P3-T4 | CLI: skillmeat scores import | Manual import of community scores from external source: `skillmeat scores import --file external-scores.json` | Command validates schema, imports successfully, shows import summary, dry-run flag supported | 2 | `python-backend-engineer` |
| P3-T5 | CLI: skillmeat scores refresh | Refresh cached community scores: `skillmeat scores refresh [--force] [--artifact <id>]` | Command triggers imports for all/specific artifacts, shows progress, completes <5min for 100 artifacts | 2 | `python-backend-engineer` |
| P3-T6 | Export Format Documentation | Document signed JSON format for community score export (for Phase 6+ registry) | Format spec includes: artifact_id, scores_by_source, signatures, version, migration_path | 1 | `documentation-writer` |
| P3-T7 | OpenTelemetry Instrumentation | Add spans for community imports, score aggregation, decay application | Spans include source, artifact count, duration, aggregation weights | 1 | `python-backend-engineer` |

### Technical Details

#### Score Aggregation Algorithm

**Bayesian Weighted Averaging**:

```python
def aggregate_scores(sources_scores: Dict[str, float], weights: Dict[str, float]) -> float:
    """
    Aggregate scores from multiple sources using Bayesian weighted averaging.

    Args:
        sources_scores: {"user_rating": 4.5, "github": 82, "registry": 78}
        weights: {"user_rating": 0.4, "github": 0.3, "registry": 0.3}

    Returns:
        Aggregated score (0-100)
    """
    # Apply priors for missing sources (neutral = 50)
    all_scores = {
        "user_rating": sources_scores.get("user_rating", 50) * 20,  # Scale 1-5 to 0-100
        "github": sources_scores.get("github", 50),
        "registry": sources_scores.get("registry", 50),
    }

    # Weighted average
    total_weight = sum(weights.values())
    aggregated = sum(
        all_scores.get(source, 50) * weight
        for source, weight in weights.items()
    ) / total_weight

    return min(100, max(0, aggregated))
```

#### GitHub Stars Mapping

```python
def stars_to_quality_score(stars: int) -> float:
    """Map GitHub stars to quality score (0-100)."""
    if stars >= 5000:
        return 100
    elif stars >= 1000:
        return 85
    elif stars >= 500:
        return 70
    elif stars >= 100:
        return 60
    elif stars >= 10:
        return 45
    else:
        return 30  # New repos
```

#### Decay Formula

```python
def apply_decay(score: float, age_days: int) -> float:
    """Apply 5%/month decay to community score."""
    months = age_days / 30.0
    decay_factor = 0.95 ** months
    return score * decay_factor

# Example: 80-point score from 3 months ago
# decayed = 80 * (0.95 ** 3) = 80 * 0.857 = 68.5
```

#### Import Format (JSON)

```json
{
  "version": "1",
  "exported_at": "2025-12-22T14:30:00Z",
  "scores": [
    {
      "artifact_id": "pdf-skill",
      "source": "github",
      "score": 92,
      "stars": 1250,
      "last_updated": "2025-12-22T10:00:00Z"
    },
    {
      "artifact_id": "pdf-skill",
      "source": "registry",
      "score": 87,
      "registry": "npm",
      "downloads_monthly": 15000,
      "last_updated": "2025-12-22T09:00:00Z"
    }
  ],
  "signature": "base64-encoded-hmac-sha256"
}
```

#### Caching Strategy

**Location**: `~/.skillmeat/collection/db/ratings.db` (existing SQLite)

**Table**:
```sql
CREATE TABLE community_scores_cache (
  id INTEGER PRIMARY KEY,
  artifact_id TEXT NOT NULL,
  source TEXT NOT NULL,
  score REAL NOT NULL,
  raw_value REAL,  -- e.g., star count for GitHub
  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  cache_expires_at TIMESTAMP,
  UNIQUE(artifact_id, source)
);

-- Index for cache expiry checks
CREATE INDEX idx_cache_expires ON community_scores_cache(cache_expires_at);
```

**Cache Policy**:
- TTL: 24 hours for most sources
- Manual refresh: `skillmeat scores refresh` bypasses cache
- Force refresh: `skillmeat scores refresh --force` resets all TTLs

### Quality Gates

- [ ] Score aggregation handles missing sources gracefully (fills with priors)
- [ ] GitHub import successful for 100+ public repositories (test with known repos)
- [ ] Decay formula verified: 3-month-old 80-point score → ~68.5 points
- [ ] Import/refresh commands complete within performance targets
- [ ] All imported scores have source attribution in database

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| GitHub API rate limits (60/hour unauthenticated) | Medium | Batch imports, recommend user provide GitHub token, cache for 24 hours |
| Imported scores stale or inaccurate | Medium | Decay formula keeps scores fresh; decay visible to users; documentation clear on age |
| Registry API unavailable | Medium | Graceful error handling; cache provides fallback; skip unavailable sources |
| Import schema drift | Medium | Version field in export format; migration path documented; backward compatible parsing |

### Dependencies

- Phase 1 completion: RatingManager and SQLite schema
- Phase 2 completion: ScoreCalculator integration
- External: GitHub API (user provides token for higher rate limits)

### Files Affected

**New Files**:
- `skillmeat/core/scoring/score_aggregator.py` - Aggregation framework
- `skillmeat/core/scoring/github_importer.py` - GitHub stars fetching
- `skillmeat/cli/commands/scores.py` - import/refresh commands

**Modified Files**:
- `skillmeat/storage/rating_store.py` - Add community_scores_cache table queries
- `skillmeat/core/scoring/score_calculator.py` - Integrate community scores
- `skillmeat/api/server.py` - Register scores router (if needed for community API)

---

## Phase 4: Web UI Implementation

**Duration**: 2 weeks | **Story Points**: 10 | **Type**: Frontend
**Parallel With**: Phase 3 (can proceed independently once API contracts defined)

### Phase Overview

Phase 4 integrates confidence scoring into the web UI, enabling users to see scores on artifact cards, rate artifacts, understand score breakdowns, and find artifacts more easily through confidence-sorted search. This phase makes scoring visible and usable to end users.

### Objectives

1. Display confidence scores on artifact cards
2. Implement star rating dialog component with optional feedback
3. Sort search results by confidence by default
4. Add expandable score breakdown view showing trust/quality/match
5. Display source trust badges (Official/Verified/Community)
6. Implement rating prompts after artifact deployment

### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Story Points | Assigned Agent(s) |
|---------|-----------|-------------|-------------------|--------------|------------------|
| P4-T1 | Display Scores on Artifact Cards | Show confidence score prominently on collection/search cards, styled with confidence-appropriate colors | Score visible, color-coded (green >70, yellow 50-70, red <50), accessible contrast ratio >4.5:1 | 2 | `ui-engineer-enhanced` |
| P4-T2 | Trust Badge Component | Display trust badges (Official ✓, Verified ✓, Community) based on source config | Badge appears on card, tooltip explains meaning, multiple badges can coexist | 2 | `ui-engineer-enhanced` |
| P4-T3 | Rating Dialog Component | Star picker (1-5 stars) + optional feedback text field, submit button | Dialog launches from card, keyboard accessible (arrow keys, space), accessibility labels present | 3 | `ui-engineer-enhanced` |
| P4-T4 | Rating Submission & Feedback | Wire rating dialog to API endpoint, submit stars + feedback, show confirmation | Submission POSTs to `/artifacts/{id}/ratings`, feedback optional, 204 response handled correctly | 2 | `ui-engineer-enhanced`, `frontend-developer` |
| P4-T5 | Score Breakdown View | Expandable card showing trust/quality/match components with visual breakdown | Expands to show three sliders/bars (one per component), label explains weight, visual hierarchy clear | 2 | `ui-engineer-enhanced` |
| P4-T6 | Search Sort by Confidence | Update search results to default sort by confidence (descending), allow custom sort | Results ordered by confidence score, other sort options (name, date) available, sort param reflected in URL | 2 | `ui-engineer-enhanced`, `frontend-developer` |
| P4-T7 | Post-Deployment Rating Prompt | Show rating prompt toast after artifact deployment succeeds | Prompt appears after 2-3 seconds, dismissible, rate button launches dialog, no repeated prompts (30-min cooldown) | 2 | `ui-engineer-enhanced` |
| P4-T8 | Rating History & Display | Show existing user rating on cards, link to rating history view | Existing rating visible (e.g., "You rated: ⭐⭐⭐⭐⭐"), update rating overwrites previous | 1 | `ui-engineer-enhanced` |
| P4-T9 | Web UI Accessibility Testing | Keyboard navigation for star picker, screen reader labels for scores/badges, color contrast | Rating dialog fully keyboard accessible (TAB, arrow keys, ENTER), ARIA labels on all interactive elements | 1 | `ui-engineer-enhanced` |

### Technical Details

#### Component Structure

**ArtifactCard Component** (enhanced):
```typescript
interface ArtifactCardProps {
  artifact: Artifact;
  scores?: {
    confidence: number;
    trust: number;
    quality: number;
    match: number;
    user_rating?: number;
  };
  onRate?: (rating: number, feedback?: string) => Promise<void>;
}

// Key additions:
// - <ScoreBadge confidence={scores.confidence} />
// - <TrustBadges source={artifact.source} />
// - <RatingButton artifact={artifact} onRate={onRate} />
```

**ScoreBadge Component**:
```typescript
interface ScoreBadgeProps {
  confidence: number;  // 0-100
  trustLevel?: "official" | "verified" | "community";
}

// Color mapping:
// confidence > 70: green (#22c55e)
// confidence 50-70: yellow (#eab308)
// confidence < 50: red (#ef4444)
// Text: confidence rounded to nearest 5 (e.g., 87 → "85")
```

**RatingDialog Component**:
```typescript
interface RatingDialogProps {
  artifact: Artifact;
  onSubmit: (rating: number, feedback?: string) => Promise<void>;
  existingRating?: number;
  onClose: () => void;
}

// Features:
// - Star picker: 1-5 stars, hover preview, keyboard support
// - Feedback field: optional textarea, character limit 500
// - Submit button: disabled during request
// - Error state: show error message if submission fails
```

**ScoreBreakdown Component**:
```typescript
interface ScoreBreakdownProps {
  confidence: number;      // 0-100, final composite score
  trust: number;           // 0-100, source trustworthiness
  quality: number;         // 0-100, user/community ratings + maintenance
  match: number;           // 0-100, semantic relevance to query
  weights?: {
    trust: number;         // default 0.25
    quality: number;       // default 0.25
    match: number;         // default 0.50
  };
}

// Display:
// - Three horizontal bars (one per component)
// - Each bar labeled with component name + score (e.g., "Trust: 95")
// - Tooltip on each bar explaining what it measures
// - Composite formula shown at bottom: (T×0.25) + (Q×0.25) + (M×0.50) = C
```

#### API Integration

**Fetch artifact with scores**:
```typescript
// GET /api/v1/collections/{collectionId}/artifacts/{artifactId}
// Response includes scores field:
{
  artifact: { /* ... */ },
  scores: {
    confidence: 92,
    trust: 95,
    quality: 87,
    match: 92,
    user_rating: 4.5,
    community_score: 87,
    rating_count: 42
  }
}
```

**Submit rating**:
```typescript
// POST /api/v1/artifacts/{artifactId}/ratings
{
  rating: 5,
  feedback: "Great extraction, forms could be better",
  share_with_community: false
}

// Response:
204 No Content
```

#### Search Integration

**Update search results hook**:
```typescript
// In hooks/use-search.ts or equivalent
export function useSearch(query: string) {
  return useQuery({
    queryKey: searchKeys.artifacts(query),
    queryFn: async () => {
      const response = await fetch(
        buildUrl(`/match?q=${encodeURIComponent(query)}&limit=20`)
      );
      // Response includes matches with confidence scores
      // Sort by confidence descending (already sorted on backend)
      return response.json();
    },
  });
}
```

### UI Mockup (Text Description)

```
┌─────────────────────────────────────────────────────┐
│ [Official ✓]  PDF Skill                     92% ●   │ ← Score badge, trust badge
│ ⭐⭐⭐⭐⭐ (5 stars, 142 ratings)       [You: ⭐⭐⭐⭐⭐]│ ← Rating display & history
│                                                     │
│ Comprehensive PDF processing with table extraction │
│ Source: anthropics/example-skills                  │
│                                                     │
│ [Rate ★] [Show Details ▼]                          │ ← Action buttons
│                                                     │
│ ┌─ Score Breakdown (expanded)                       │
│ │ Trust:   ████████████████░░ (95)                  │
│ │ Quality: ███████████████░░░ (87) ⓘ                │
│ │ Match:   ████████████████░░ (92)                  │
│ │                                                   │
│ │ Formula: (T×0.25) + (Q×0.25) + (M×0.50) = 92%    │
│ └─────────────────────────────────────────────────┘
```

### Quality Gates

- [ ] All score components visible and accessible on artifact cards
- [ ] Rating dialog fully keyboard accessible (arrow keys, space, enter)
- [ ] Search results sort by confidence correctly
- [ ] Color contrast meets WCAG AA standard (4.5:1 for normal text)
- [ ] No console errors or accessibility violations in automated testing
- [ ] Performance: Card rendering <50ms per artifact (even with scores)
- [ ] Rating submission works end-to-end with Phase 1 API

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Star picker UX confusing to users | Medium | Usability testing with 5+ users pre-release, iterate on feedback |
| Score colors misinterpreted (not colorblind friendly) | Medium | Use patterns + text in addition to color, pass WCAG contrast checks |
| Ratings not submitted (network issues) | Low | Show clear error message, allow retry, save draft locally |
| Score data not loaded on card render | Medium | Lazy load scores after card render, show skeleton loading state |

### Dependencies

- Phase 1 completion: API endpoints for scores and ratings
- Phase 2 completion: Match endpoint for search sorting
- Phase 3 completion: Community scores available for display (but Phase 4 can proceed with user ratings only)
- React Query, Radix UI already available

### Files Affected

**New Components** (`skillmeat/web/components/`):
- `ScoreBadge.tsx` - Display confidence score with color
- `TrustBadges.tsx` - Display official/verified/community badges
- `RatingDialog.tsx` - Star picker + feedback dialog
- `ScoreBreakdown.tsx` - Expandable score component breakdown
- `RatingButton.tsx` - Button to launch rating dialog

**Modified Components** (`skillmeat/web/components/`):
- `ArtifactCard.tsx` - Add score badge, trust badges, rating button
- `SearchResults.tsx` - Add confidence sort option, update query params
- `CollectionView.tsx` - Fetch scores for artifacts, show rating prompts

**Modified Hooks** (`skillmeat/web/hooks/`):
- `use-search.ts` - Wire to match API, extract confidence scores
- `use-collection.ts` - Fetch artifact scores on view load

**Modified API Client** (`skillmeat/web/lib/api/`):
- `artifacts.ts` - Add getArtifactScores() function
- `ratings.ts` - Add submitRating() function

---

## Phase 5: Advanced Features & Customization

**Duration**: 1-2 weeks | **Story Points**: 3 | **Type**: Advanced features
**Sequential After**: Phases 1-4

### Phase Overview

Phase 5 adds weight customization, historical success tracking, anti-gaming protections, and analytics dashboards. These features support power users and provide insights into the scoring system's effectiveness.

### Objectives

1. Support weight customization via CLI config
2. Track successful matches (user confirmations) for analytics
3. Implement anti-gaming protections (anomaly detection)
4. Optional rating export for community sharing
5. Score analytics dashboard (optional)

### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Story Points | Assigned Agent(s) |
|---------|-----------|-------------|-------------------|--------------|------------------|
| P5-T1 | Weight Customization Config | Support custom score weights: `skillmeat config set score-weights trust=0.3 quality=0.2 match=0.5` | Config command validates sum=1.0, weights apply to future matches, `skillmeat config get` shows current weights | 1 | `python-backend-engineer` |
| P5-T2 | Historical Success Tracking | Track matches users confirmed: store `(query, artifact_id, confidence, confirmed)` in SQLite | Track on successful deploy after match, calculate accuracy over time, exportable for analysis | 1 | `python-backend-engineer` |
| P5-T3 | Anti-Gaming Protections | Detect anomalies: >5 ratings/hour per artifact, ratings all 5-star in quick succession | Flag suspicious patterns, log for review, rate limiting enforced (max 5/day/user/artifact) | 1 | `python-backend-engineer` |
| P5-T4 | Rating Export | Export user ratings: `skillmeat rate --export ratings.json [--community]` | Export includes artifact_id, rating, feedback, timestamp, optional anonymization | 0.5 | `python-backend-engineer` |
| P5-T5 | Analytics Dashboard (Optional) | Web UI showing confidence distribution, rating participation, match accuracy trends | Dashboard reads from SQLite analytics, shows charts (histogram of confidence scores, line chart of rating volume over time) | 0.5 | `ui-engineer-enhanced` |

### Technical Details

#### Weight Customization

**Storage**: `.skillmeat/config.toml` (or existing config location)

```toml
[scoring]
trust_weight = 0.3       # default 0.25
quality_weight = 0.2     # default 0.25
match_weight = 0.5       # default 0.50

# Validation: sum must equal 1.0
# If sum != 1.0, normalize or error
```

**CLI Implementation**:
```bash
skillmeat config set score-weights trust=0.3 quality=0.2 match=0.5
# Validates: 0.3 + 0.2 + 0.5 = 1.0 ✓

skillmeat config get
# Output:
# Scoring weights:
#   Trust:   0.30
#   Quality: 0.20
#   Match:   0.50

skillmeat config reset score-weights
# Reset to defaults: 0.25, 0.25, 0.50
```

#### Historical Success Tracking

**Schema Extension**:
```sql
CREATE TABLE match_history_enhanced (
  id INTEGER PRIMARY KEY,
  query TEXT NOT NULL,
  artifact_id TEXT NOT NULL,
  confidence REAL NOT NULL,
  top_result BOOLEAN,         -- Was this in top 3 results?
  user_confirmed BOOLEAN,     -- Did user deploy this artifact?
  actually_used BOOLEAN,      -- (Phase 5+) Did user actually use it after deploy?
  user_satisfaction INTEGER,  -- (Phase 5+) User's post-use rating (1-5)
  matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  confirmed_at TIMESTAMP,

  INDEX(query),
  INDEX(user_confirmed)
);
```

**Analytics Queries**:
```python
def match_accuracy_at_confidence_threshold(min_confidence: float) -> float:
    """Return accuracy of matches above confidence threshold."""
    results = db.execute("""
        SELECT
            COUNT(CASE WHEN user_confirmed THEN 1 END) as confirmations,
            COUNT(*) as total
        FROM match_history_enhanced
        WHERE confidence >= ?
    """, (min_confidence,))
    confirmations, total = results.fetchone()
    return confirmations / total if total > 0 else 0.0

# Example: 85% of matches >80% confidence were user-confirmed
accuracy = match_accuracy_at_confidence_threshold(80)  # → 0.85
```

#### Anti-Gaming Protections

**Anomaly Detection**:
```python
def detect_suspicious_rating_pattern(artifact_id: str) -> List[str]:
    """Detect suspicious rating patterns."""
    alerts = []

    # Alert 1: Too many ratings in short time
    recent_ratings = db.execute("""
        SELECT COUNT(*) FROM user_ratings
        WHERE artifact_id = ? AND rated_at > datetime('now', '-1 hour')
    """, (artifact_id,)).fetchone()[0]

    if recent_ratings > 5:
        alerts.append(f"Anomaly: {recent_ratings} ratings in last hour")

    # Alert 2: All 5-star in rapid succession
    recent_5star = db.execute("""
        SELECT COUNT(*) FROM user_ratings
        WHERE artifact_id = ?
          AND rating = 5
          AND rated_at > datetime('now', '-1 day')
    """, (artifact_id,)).fetchone()[0]

    recent_total = db.execute("""
        SELECT COUNT(*) FROM user_ratings
        WHERE artifact_id = ? AND rated_at > datetime('now', '-1 day')
    """, (artifact_id,)).fetchone()[0]

    if recent_total >= 3 and recent_5star / recent_total > 0.9:
        alerts.append(f"Anomaly: 90%+ 5-star ratings in last day")

    return alerts
```

**Rate Limiting Enforcement**:
```python
def check_rate_limit(artifact_id: str, user_id: Optional[str] = None) -> bool:
    """Check if user can submit rating (max 5 per artifact per day)."""
    count = db.execute("""
        SELECT COUNT(*) FROM user_ratings
        WHERE artifact_id = ?
          AND rated_at > datetime('now', '-1 day')
          AND user_id IS ?
    """, (artifact_id, user_id or "anonymous")).fetchone()[0]

    return count < 5  # Allow rating if under limit
```

#### Rating Export

**Export Schema**:
```json
{
  "version": "1",
  "exported_at": "2025-12-22T14:30:00Z",
  "ratings": [
    {
      "artifact_id": "pdf-skill",
      "rating": 5,
      "feedback": "Great extraction, forms could be better",
      "rated_at": "2025-12-15T10:00:00Z",
      "user_id": null,
      "anonymized": true
    }
  ],
  "metadata": {
    "total_ratings": 23,
    "average_rating": 4.2,
    "rating_count_by_value": {
      "1": 1,
      "2": 0,
      "3": 2,
      "4": 6,
      "5": 14
    }
  }
}
```

**CLI**:
```bash
skillmeat rate --export ratings.json
# Exports all user's ratings, anonymized by default

skillmeat rate --export ratings.json --with-identity
# Includes user_id (if set) for community sharing with attribution

skillmeat rate --export ratings.json --community
# Formats for community registry submission
```

### Quality Gates

- [ ] Weight customization validates sum=1.0
- [ ] Historical tracking shows >80% of user-confirmed matches were in top 3 results
- [ ] Anti-gaming detections do not have false positives on legitimate bulk operations
- [ ] Rating export maintains privacy (anonymous by default)
- [ ] Analytics queries complete in <100ms

### Dependencies

- Phases 1-4 complete (all scoring components working)
- Optional: Analytics visualization library (e.g., Chart.js, Recharts)

### Files Affected

**New Files**:
- `skillmeat/core/scoring/analytics.py` - Queries and calculations for match accuracy
- `skillmeat/core/scoring/anti_gaming.py` - Anomaly detection and rate limiting
- `skillmeat/web/components/AnalyticsDashboard.tsx` (optional) - Chart visualizations

**Modified Files**:
- `skillmeat/core/config.py` - Add scoring weights configuration
- `skillmeat/storage/rating_store.py` - Extend schema for match_history_enhanced
- `skillmeat/cli/commands/rate.py` - Add export functionality
- `skillmeat/cli/commands/config.py` - Add weight customization commands

---

## Phase 3-5 Orchestration Quick Reference

### Phase 3 Execution Plan

**Sequential Batch 1** (Framework & Import):
```
Task("python-backend-engineer", "P3-T1: Implement ScoreAggregator with Bayesian weighting")
Task("python-backend-engineer", "P3-T2: Implement GitHub stars import with caching strategy")
```

**Sequential Batch 2** (CLI & Management):
```
Task("python-backend-engineer", "P3-T3: Implement score freshness decay (5%/month)")
Task("python-backend-engineer", "P3-T4: Implement 'skillmeat scores import' CLI command")
Task("python-backend-engineer", "P3-T5: Implement 'skillmeat scores refresh' CLI command")
```

**Parallel Final**:
```
Task("documentation-writer", "P3-T6: Document community score export format for future registry")
Task("python-backend-engineer", "P3-T7: Add OpenTelemetry instrumentation for Phase 3 operations")
```

### Phase 4 Execution Plan

**Parallel Batch 1** (Display Components):
```
Task("ui-engineer-enhanced", "P4-T1: Display scores on artifact cards with color-coding")
Task("ui-engineer-enhanced", "P4-T2: Implement trust badge component (Official/Verified/Community)")
Task("ui-engineer-enhanced", "P4-T5: Implement score breakdown expandable view")
```

**Parallel Batch 2** (Interaction & Integration):
```
Task("ui-engineer-enhanced", "P4-T3: Implement rating dialog component (star picker + feedback)")
Task("ui-engineer-enhanced", "P4-T4: Wire rating submission to API endpoint")
Task("ui-engineer-enhanced", "P4-T6: Update search results to sort by confidence")
```

**Sequential Final**:
```
Task("ui-engineer-enhanced", "P4-T7: Implement post-deployment rating prompts")
Task("ui-engineer-enhanced", "P4-T8: Show existing user ratings on cards")
Task("ui-engineer-enhanced", "P4-T9: Accessibility testing (keyboard navigation, ARIA labels)")
```

### Phase 5 Execution Plan

**Sequential** (Smaller tasks, low parallelization potential):
```
Task("python-backend-engineer", "P5-T1: Implement weight customization config system")
Task("python-backend-engineer", "P5-T2: Implement historical success tracking for analytics")
Task("python-backend-engineer", "P5-T3: Implement anti-gaming protections and anomaly detection")
Task("python-backend-engineer", "P5-T4: Implement rating export functionality")
Task("ui-engineer-enhanced", "P5-T5: (Optional) Analytics dashboard visualization")
```

---

## Cross-Phase Testing Strategy

### Integration Tests (Run after each phase)

**Phase 3 Integration**:
```bash
# Test community score import and display
pytest tests/integration/test_community_scores.py -v
# - Import GitHub stars for 10 test artifacts
# - Verify aggregation with user ratings
# - Verify decay calculation
```

**Phase 4 Integration**:
```bash
# Test Web UI with scores
pytest tests/web/e2e/test_artifact_scores.cy.ts -v
# - Load collection with scores
# - Display scores on cards
# - Submit rating via dialog
# - Verify API call and success confirmation
```

**Phase 5 Integration**:
```bash
# Test analytics and customization
pytest tests/integration/test_analytics.py -v
# - Track match history
# - Verify accuracy calculations
# - Test weight customization
# - Verify anti-gaming detections
```

### E2E User Journey (Phase 5 complete)

```bash
# Full user flow: Search → Rate → Analytics
./tests/e2e/full_flow_test.sh
# 1. skillmeat match "extract tables"
# 2. Deploy top result
# 3. skillmeat rate pdf --rating 5 --feedback "Great!"
# 4. skillmeat config set score-weights trust=0.3 quality=0.2 match=0.5
# 5. skillmeat scores refresh
# 6. Navigate to Web UI, verify scores and analytics
```

---

## Sign-Off & Final Notes

**Document Status**: DRAFT (pending Phase 0 SPIKE and Phase 1-2 completion)

**Phase 3-5 Owner**: python-backend-engineer (Sonnet) for Phase 3, ui-engineer-enhanced (Sonnet) for Phase 4, both for Phase 5

**Next Steps**:
1. Phase 1-2 implementation and completion
2. Refinement of Phase 3 community sources based on Phase 0 findings
3. Finalize Web UI design mockups (Phase 4 pre-kickoff)
4. Determine optional Phase 5 features based on project capacity

**Last Updated**: 2025-12-22
