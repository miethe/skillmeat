---
type: progress
prd: "PRD-001-confidence-scoring"
phase: 1
phase_title: "Foundation - Data Models & Ratings"
status: not_started
progress: 0
total_tasks: 9
completed_tasks: 0
estimated_effort: "2-3 weeks"
story_points: 13
dependencies:
  - phase: 0
    status: "must_complete"

tasks:
  - id: "P1-T1"
    title: "Extend ArtifactRating Schema"
    status: "pending"
    assigned_to: ["data-layer-expert", "python-backend-engineer"]
    dependencies: []
    story_points: 3

  - id: "P1-T2"
    title: "Create SQLite Schema for Ratings"
    status: "pending"
    assigned_to: ["data-layer-expert", "python-backend-engineer"]
    dependencies: []
    story_points: 3

  - id: "P1-T3"
    title: "Implement RatingManager"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1-T1", "P1-T2"]
    story_points: 4

  - id: "P1-T4"
    title: "Implement Quality Scorer"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1-T3"]
    story_points: 3

  - id: "P1-T5"
    title: "CLI: skillmeat rate command"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1-T3"]
    story_points: 2

  - id: "P1-T6"
    title: "CLI: skillmeat show --scores"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1-T4"]
    story_points: 2

  - id: "P1-T7"
    title: "API: GET /artifacts/{id}/scores"
    status: "pending"
    assigned_to: ["python-backend-engineer", "backend-architect"]
    dependencies: ["P1-T4"]
    story_points: 2

  - id: "P1-T8"
    title: "API: POST /artifacts/{id}/ratings"
    status: "pending"
    assigned_to: ["python-backend-engineer", "backend-architect"]
    dependencies: ["P1-T3"]
    story_points: 2

  - id: "P1-T9"
    title: "OpenTelemetry Instrumentation"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1-T7", "P1-T8"]
    story_points: 1

parallelization:
  batch_1: ["P1-T1", "P1-T2"]
  batch_2: ["P1-T3"]
  batch_3: ["P1-T4", "P1-T5", "P1-T8"]
  batch_4: ["P1-T6", "P1-T7"]
  batch_5: ["P1-T9"]
---

# Phase 1: Foundation - Data Models & Ratings

## Orchestration Quick Reference

**Batch 1** (Parallel - Data Layer):
- P1-T1 (3pts) → `data-layer-expert`, `python-backend-engineer`
- P1-T2 (3pts) → `data-layer-expert`, `python-backend-engineer`

**Batch 2** (Sequential - Core Manager):
- P1-T3 (4pts) → `python-backend-engineer`

**Batch 3** (Parallel - Features):
- P1-T4 (3pts) → `python-backend-engineer`
- P1-T5 (2pts) → `python-backend-engineer`
- P1-T8 (2pts) → `python-backend-engineer`, `backend-architect`

**Batch 4** (Parallel - Display/API):
- P1-T6 (2pts) → `python-backend-engineer`
- P1-T7 (2pts) → `python-backend-engineer`, `backend-architect`

**Batch 5** (Final):
- P1-T9 (1pt) → `python-backend-engineer`

### Task Delegation Commands

Task("data-layer-expert", "P1-T1: Extend ArtifactRating Schema.
Add fields: user_rating, community_score, trust_score, last_updated, maintenance_score.
File: skillmeat/core/artifact.py or new skillmeat/storage/rating_store.py
Acceptance: Schema deployed, migrations created, >80% test coverage")

Task("data-layer-expert", "P1-T2: Create SQLite Schema for Ratings.
Tables: user_ratings, community_scores, match_history.
File: skillmeat/storage/database.py or dedicated rating schema.
Acceptance: Schema created, migrations applied")

Task("python-backend-engineer", "P1-T3: Implement RatingManager.
File: skillmeat/storage/rating_store.py
Methods: rate_artifact(), get_ratings(), export_ratings()
Acceptance: >80% test coverage, stores ratings locally")

Task("python-backend-engineer", "P1-T4: Implement Quality Scorer.
File: skillmeat/core/scoring.py
Formula: user_rating(40%) + community(30%) + maintenance(20%) + compatibility(10%)
Acceptance: Returns 0-100 score, handles missing data with priors")

Task("python-backend-engineer", "P1-T5: CLI skillmeat rate command.
Command: skillmeat rate <artifact> [--rating 1-5] [--feedback '...']
Acceptance: Persists rating, JSON output support, help text")

Task("python-backend-engineer", "P1-T6: CLI skillmeat show --scores.
Extend show command to display trust, quality, match breakdown.
Acceptance: Human-readable format, works with existing show")

Task("python-backend-engineer", "P1-T7: API GET /artifacts/{id}/scores.
Response: {trust_score, quality_score, user_rating, community_score, schema_version}
Acceptance: 404 on missing, schema documented")

Task("python-backend-engineer", "P1-T8: API POST /artifacts/{id}/ratings.
Request: {rating: 1-5, feedback?: string, share_with_community?: bool}
Acceptance: Rate limiting (5/day), 204 response")

Task("python-backend-engineer", "P1-T9: OpenTelemetry Instrumentation.
Add spans for: rate submission, score fetch, quality aggregation.
Acceptance: Spans include trace_id, timing metrics")

## Quality Gates

- [ ] All P1 tasks completed with >80% unit test coverage
- [ ] API responses include `schema_version: "1"` field
- [ ] Manual testing: rate and show --scores work end-to-end
- [ ] Performance baseline: API endpoints respond <100ms
- [ ] Database migration strategy documented

## Notes

[Session notes will be added here]
