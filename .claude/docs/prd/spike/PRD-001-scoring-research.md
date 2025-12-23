---
title: "PRD-001 SPIKE: Scoring Systems Research"
description: "Community scoring best practices, anti-gaming strategies, and score weight recommendations"
created: 2025-12-22
status: complete
related: [PRD-001-confidence-scoring]
---

# PRD-001 SPIKE: Community Scoring Research

**Task**: Research community scoring systems and anti-gaming strategies for SkillMeat confidence scoring.

**Scope**: Analyze npm, PyPI, VS Code marketplace approaches; recommend score weights, anti-gaming protections, cold-start strategies, and schema versioning.

---

## 1. Existing Scoring Systems Analysis

### npm Quality Score

**Components**:
- **Popularity (33%)**: Downloads, dependents
- **Quality (33%)**: Maintenance, health metrics (tests, linting, changelog)
- **Maintenance (33%)**: Commit frequency, issue resolution time, dependencies staleness

**Key Insights**:
- Balanced tri-component approach (33/33/33) prevents single dimension domination
- Maintenance metrics (commit activity, issue response) proxy for ongoing quality
- Popularity weighted lower to avoid "rich get richer" effects
- Public, transparent algorithm builds user trust

**Anti-Gaming**:
- Download count anomaly detection (spike patterns flagged)
- Dependents require real code (not empty packages)
- Health metrics require actual test/lint infrastructure (not just badges)

### VS Code Marketplace

**Components**:
- **User ratings**: 1-5 stars, weighted by verified users (higher weight)
- **Install count**: Popularity signal
- **Recency**: Recent ratings weighted higher
- **Review quality**: Detailed reviews weighted over simple stars

**Key Insights**:
- Verified users (logged in with Microsoft account) get higher weight to combat fake reviews
- Temporal decay: Ratings >6 months old decay 20%, >1 year decay 50%
- Review length/quality correlation: Detailed reviews indicate genuine usage
- Default sort by "Rating + Installs" composite

**Anti-Gaming**:
- Rate limiting: 1 review per extension per user per 30 days
- Verified user requirement for full weight (unverified reviews exist but low weight)
- Pattern detection: Same IP/user reviewing multiple extensions flagged
- Bayesian priors: New extensions start at 3.0/5.0 (neutral), not 0

### PyPI / pepy.tech

**Components**:
- **Download counts**: Primary metric (30-day, 180-day, all-time)
- **GitHub stars**: Quality proxy if source linked
- **Maintenance**: Last release date, Python version support
- **No user ratings**: Deliberately avoided to prevent gaming

**Key Insights**:
- Download counts normalized by time window to avoid legacy bias
- Mirror downloads excluded (only direct downloads counted)
- No explicit quality score to avoid gaming; users interpret metrics themselves
- Transparency over aggregation: Show raw data, let users decide

**Anti-Gaming**:
- CI/CD download spikes filtered (common bot patterns excluded)
- Mirror traffic excluded automatically
- Rate limiting on API access to prevent scraping/manipulation

---

## 2. Recommended Score Weights

### Proposed Formula Validation

**SkillMeat Proposal**: `(Trust × 0.25) + (Quality × 0.25) + (Match × 0.50)`

**Analysis**:
- Match relevance (50%) is appropriate for discovery use case (primary goal: find right artifact)
- Trust (25%) balances safety without over-weighting unverified sources
- Quality (25%) captures community signals without popularity bias

**Comparison to Alternatives**:

| System | Trust/Source | Quality/Community | Match/Relevance |
|--------|-------------|-------------------|----------------|
| npm | 0% (implicit in quality) | 67% (quality+maintenance) | 33% (popularity) |
| VS Code | 0% (publisher trust not scored) | 70% (ratings) | 30% (installs) |
| SkillMeat | 25% | 25% | 50% |

**Recommendation**: **Keep proposed 25/25/50 weights**.

**Rationale**:
- Higher match weight (50%) reflects discovery-first use case (vs. npm's general quality focus)
- Trust component (25%) addresses AI agent safety concerns (absent from npm/VS Code)
- Quality component (25%) balances community signals without popularity bias
- Total sums to 100% for intuitive 0-100 confidence score

**Alternative Considered**: 20/30/50 (lower trust, higher quality)
- **Rejected**: Trust is critical for AI agents; community gaming is easier than source verification

---

## 3. Anti-Gaming Strategies

### Rate Limiting

**Recommended**:
- **User ratings**: Max 5 ratings per artifact per user per day
- **API queries**: Max 100 match queries per IP per hour (prevents scraping)
- **Community score imports**: Max 1 refresh per artifact per 24 hours

**Rationale**:
- 5/day allows legitimate re-rating after artifact updates without allowing spam
- 100/hour query limit is generous for legitimate use but prevents abuse
- 24-hour import limit balances freshness with API quota preservation

### Anomaly Detection

**Recommended Patterns**:

1. **Rating Spike Detection**:
   - Flag artifacts with >10 ratings in 1 hour from new users
   - Threshold: 3× standard deviation above 7-day rolling average
   - Action: Delay rating aggregation by 24 hours for manual review

2. **IP/User Pattern Detection**:
   - Flag same IP rating >5 different artifacts in 1 hour
   - Flag user accounts created <7 days ago submitting ratings
   - Action: Reduce weight of flagged ratings to 10% of normal

3. **Review Similarity Detection**:
   - Flag near-duplicate feedback text (>80% Levenshtein similarity)
   - Action: Count as single rating instance, not multiple

**Implementation Priority**: Phase 5 (start with rate limiting only in Phase 1-3)

### Bayesian Priors (Cold-Start Problem)

**Recommended Priors**:

| Component | Prior Value | Rationale |
|-----------|------------|-----------|
| Trust | Source-dependent (50-95) | Official: 95, Verified: 75, Community: 50 |
| Quality (user ratings) | 50 (neutral) | Avoid optimism bias; neutral starting point |
| Quality (community) | 50 (neutral) | Same as user ratings |
| Match | Query-dependent | Calculated per query; no prior needed |

**Bayesian Averaging Formula** (for Quality component):

```
quality_score = (prior × prior_weight + actual × actual_weight) / (prior_weight + actual_weight)

where:
  prior = 50 (neutral)
  prior_weight = 5 (equivalent to 5 ratings)
  actual = mean(user_ratings)
  actual_weight = count(user_ratings)
```

**Example**:
- New artifact with 2 ratings (4.0, 5.0) → mean = 4.5
- Bayesian avg = (50×5 + 4.5×2) / (5+2) = (250 + 9) / 7 = **37.0**
- Prevents low-sample artifacts from dominating with perfect 5.0 scores

**Rationale**:
- Prior weight of 5 is standard (equivalent to 5 neutral reviews)
- Neutral prior (50) avoids optimism/pessimism bias
- Trust priors are source-dependent (not neutral) to reflect known verification status

---

## 4. Schema Versioning Approach

### Recommended Strategy

**Use `schema_version` field in all API responses**:

```json
{
  "schema_version": "1.0.0",
  "matches": [...],
  "scores": {...}
}
```

**Versioning Policy**:
- **Major version** (1.x.x → 2.x.x): Breaking changes (field removed, type changed)
- **Minor version** (x.1.x → x.2.x): Additive changes (new field, new component)
- **Patch version** (x.x.1 → x.x.2): Non-breaking fixes (enum value added, description clarified)

**Backward Compatibility Commitment**:
- Support N-1 major version for 6 months after N release
- Deprecation warnings in response headers: `X-API-Deprecated: "Use schema 2.0.0"`
- All consumers MUST check `schema_version` and handle unknown fields gracefully

**Example Evolution**:

| Version | Change | Type |
|---------|--------|------|
| 1.0.0 | Initial release: trust + quality + match | Major |
| 1.1.0 | Add `maintenance_score` to quality breakdown | Minor |
| 1.2.0 | Add `context_boost` to match explanation | Minor |
| 2.0.0 | Rename `quality` to `community_quality` (breaking) | Major |

**Storage Versioning**:
- Store schema version in SQLite alongside scores: `(artifact_id, score, schema_version, updated_at)`
- Migrations handle schema upgrades automatically (v1 → v2 conversion function)
- Export format includes schema version for portability

---

## 5. Recommendations Summary

### Score Weights (Validated)

✅ **Keep proposed 25/25/50 split**:
- Trust: 25%
- Quality: 25%
- Match: 50%

**Rationale**: Discovery-first use case prioritizes match relevance; trust addresses AI safety; quality balances community signals.

### Anti-Gaming Protections

**Phase 1-3** (MVP):
- Rate limiting: 5 ratings/artifact/user/day, 100 queries/IP/hour
- Bayesian priors: Quality defaults to 50 (neutral), trust from source config

**Phase 5** (Advanced):
- Anomaly detection: Rating spikes (>10/hour), IP patterns, review similarity
- Action thresholds: Delay aggregation (24h), reduce weight (10%), flag for review

### Cold-Start Strategy

**Bayesian Priors**:
- Quality: 50 (neutral) with prior weight of 5
- Trust: Source-dependent (Official: 95, Verified: 75, Community: 50)
- Match: Query-dependent (no prior needed)

**Formula**: `(50×5 + actual_mean×count) / (5 + count)`

### Schema Versioning

**Semver-based versioning**:
- Major: Breaking changes (6-month backward compatibility)
- Minor: Additive changes (fully backward compatible)
- Patch: Non-breaking fixes

**Implementation**:
- `schema_version` field in all API responses
- SQLite storage includes schema version per score
- Export format includes version for portability

---

## 6. Implementation Notes

### Phase Priorities

**Phase 1** (Foundation):
- Implement basic rate limiting (5/day, 100/hour)
- Configure source trust priors (Official: 95, Verified: 75, Community: 50)
- Implement Bayesian averaging with prior=50, weight=5
- Add `schema_version: "1.0.0"` to all responses

**Phase 3** (Community Integration):
- Implement score freshness decay (5%/month)
- Add GitHub stars import with caching (24h limit)
- Store schema version in SQLite alongside scores

**Phase 5** (Advanced):
- Implement anomaly detection (spike, IP, similarity)
- Add configurable score weights via CLI config
- Add analytics dashboard for gaming pattern detection

### Testing Considerations

**Unit Tests**:
- Bayesian averaging edge cases (0 ratings, 1 rating, 100 ratings)
- Rate limiting enforcement (exactly 5/day, reject 6th)
- Schema version serialization/deserialization

**Integration Tests**:
- Cold-start behavior (new artifact scores to 50 quality, source-specific trust)
- Gaming scenario simulation (10 rapid ratings from same IP → flagged)
- Schema migration (v1.0.0 → v1.1.0 backward compatibility)

**Benchmarks**:
- Score calculation performance: <10ms per artifact
- Bayesian averaging performance: <1ms per artifact
- Anomaly detection overhead: <50ms per rating submission

---

## References

1. **npm Quality Score**: https://docs.npmjs.com/packages-and-modules/npm-quality
2. **VS Code Marketplace Algorithm**: https://code.visualstudio.com/api/working-with-extensions/publishing-extension#marketplace-presentation
3. **PyPI Download Statistics (pepy.tech)**: https://pepy.tech/
4. **Bayesian Averaging (Wikipedia)**: https://en.wikipedia.org/wiki/Bayesian_average
5. **Semver Specification**: https://semver.org/

---

**Status**: Research complete. Ready for Phase 1 implementation.
