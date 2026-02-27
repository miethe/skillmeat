---
type: progress
schema_version: 2
doc_type: progress
prd: similar-artifacts
feature_slug: similar-artifacts
prd_ref: docs/project_plans/PRDs/features/similar-artifacts-v1.md
plan_ref: docs/project_plans/implementation_plans/features/similar-artifacts-v1.md
phase: 1
title: Core Similarity Engine + Collection Tab
status: completed
started: '2026-02-25'
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: on-track
total_tasks: 18
completed_tasks: 18
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
- backend-architect
contributors:
- data-layer-expert
- openapi-expert
- ui-engineer-enhanced
- frontend-developer
tasks:
- id: SA-P1-001
  description: DuplicatePair.ignored migration - Add ignored boolean column to DuplicatePair
    model
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies: []
  estimated_effort: 1pt
  priority: high
- id: SA-P1-002
  description: SimilarityResult dataclass - Define SimilarityResult and ScoreBreakdown
    dataclasses
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 1pt
  priority: high
- id: SA-P1-003
  description: MatchAnalyzer.compare() helper - Add compare(artifact_a, artifact_b)
    method
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SA-P1-002
  estimated_effort: 2pts
  priority: high
- id: SA-P1-005
  description: Pydantic schemas - Add SimilarArtifactDTO and SimilarityBreakdownDTO
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SA-P1-002
  estimated_effort: 1pt
  priority: high
- id: SA-P1-004
  description: SimilarityService core - Implement similarity matching, filtering,
    and ranking logic
  status: completed
  assigned_to:
  - backend-architect
  - python-backend-engineer
  dependencies:
  - SA-P1-002
  - SA-P1-003
  estimated_effort: 5pts
  priority: critical
- id: SA-P1-006
  description: API endpoint - Implement GET /api/v1/artifacts/{id}/similar
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SA-P1-004
  - SA-P1-005
  estimated_effort: 2pts
  priority: high
- id: SA-P1-007
  description: OpenTelemetry instrumentation - Add OTel spans to SimilarityService
    and MatchAnalyzer
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - SA-P1-004
  estimated_effort: 1pt
  priority: medium
- id: SA-P1-008
  description: Unit tests - SimilarityService - Comprehensive test coverage for similarity
    logic
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SA-P1-004
  estimated_effort: 2pts
  priority: high
- id: SA-P1-009
  description: Integration tests - similar endpoint - End-to-end API tests
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SA-P1-006
  - SA-P1-008
  estimated_effort: 2pts
  priority: high
- id: SA-P1-010
  description: OpenAPI spec update - Update skillmeat/api/openapi.json with endpoint
    and schemas
  status: completed
  assigned_to:
  - openapi-expert
  dependencies:
  - SA-P1-006
  estimated_effort: 1pt
  priority: high
- id: SA-P2-001
  description: TypeScript types - Generate types from OpenAPI spec for frontend consumption
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - SA-P1-010
  estimated_effort: 0.5pt
  priority: high
- id: SA-P2-002
  description: useSimilarArtifacts hook - Create custom hook for fetching and managing
    similar artifacts
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - SA-P2-001
  estimated_effort: 1pt
  priority: high
- id: SA-P2-003
  description: MiniArtifactCard - showScore prop - Extend MiniArtifactCard to display
    similarity score
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SA-P2-001
  estimated_effort: 2pts
  priority: high
- id: SA-P2-004
  description: SimilarArtifactsTab component - Main collection tab with list and filtering
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SA-P2-002
  - SA-P2-003
  estimated_effort: 3pts
  priority: critical
- id: SA-P2-005
  description: ArtifactDetailsModal tab registration - Register SimilarArtifactsTab
    in modal
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SA-P2-004
  estimated_effort: 1pt
  priority: high
- id: SA-P2-006
  description: Error state handling - Empty, loading, and error states for similar
    tab
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - SA-P2-004
  estimated_effort: 0.5pt
  priority: medium
- id: SA-P2-007
  description: Component tests - SimilarArtifactsTab and MiniArtifactCard with score
    rendering
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - SA-P2-004
  - SA-P2-003
  estimated_effort: 1pt
  priority: high
- id: SA-P2-008
  description: E2E test - Similar tab - Playwright test for full user workflow
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - SA-P2-005
  estimated_effort: 1pt
  priority: high
parallelization:
  batch_1:
  - SA-P1-001
  - SA-P1-002
  batch_2:
  - SA-P1-003
  - SA-P1-005
  batch_3:
  - SA-P1-004
  batch_4:
  - SA-P1-006
  - SA-P1-007
  - SA-P1-008
  batch_5:
  - SA-P1-009
  - SA-P1-010
  batch_6:
  - SA-P2-001
  batch_7:
  - SA-P2-002
  - SA-P2-003
  batch_8:
  - SA-P2-004
  batch_9:
  - SA-P2-005
  - SA-P2-006
  - SA-P2-007
  batch_10:
  - SA-P2-008
  critical_path:
  - SA-P1-002
  - SA-P1-003
  - SA-P1-004
  - SA-P1-006
  - SA-P1-010
  - SA-P2-001
  - SA-P2-002
  - SA-P2-004
  - SA-P2-005
  - SA-P2-008
  estimated_total_time: 22pts (optimal parallel execution)
blockers: []
success_criteria:
- id: SC-1
  description: SimilarityService calculates pairwise similarity scores across all
    artifacts
  status: pending
- id: SC-2
  description: GET /api/v1/artifacts/{id}/similar returns ranked similar artifacts
    with scores
  status: pending
- id: SC-3
  description: All unit and integration tests pass with >80% coverage
  status: pending
- id: SC-4
  description: SimilarArtifactsTab renders in artifact details modal with filtering
    and sorting
  status: pending
- id: SC-5
  description: E2E tests verify similar artifacts discovery workflow end-to-end
  status: pending
- id: SC-6
  description: OpenAPI spec reflects all new endpoints and schemas
  status: pending
files_modified:
- skillmeat/cache/models.py
- skillmeat/core/similarity.py
- skillmeat/core/scoring/match_analyzer.py
- skillmeat/api/schemas/artifacts.py
- skillmeat/api/routers/artifacts.py
- skillmeat/api/openapi.json
- tests/test_similarity_service.py
- tests/test_api_similar.py
- skillmeat/web/components/artifact/similar-artifacts-tab.tsx
- skillmeat/web/hooks/use-similar-artifacts.ts
- skillmeat/web/__tests__/similar-artifacts-tab.test.tsx
- skillmeat/web/e2e/similar-artifacts.spec.ts
updated: '2026-02-25'
progress: 100
---

# similar-artifacts - Phase 1-2: Core Similarity Engine + Collection Tab

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/similar-artifacts/phase-1-2-progress.md -t TASK-ID -s completed
```

Batch update:

```bash
python .claude/skills/artifact-tracking/scripts/update-batch.py -f .claude/progress/similar-artifacts/phase-1-2-progress.md --updates "SA-P1-001:completed,SA-P1-002:completed"
```

---

## Objective

Implement a similarity discovery engine that identifies semantically similar artifacts based on metadata, tags, and content patterns, then expose it via REST API and surface in the web UI as a "Similar Artifacts" tab in the artifact details modal.

---

## Implementation Notes

### Architectural Decisions

**Similarity Algorithm**: Uses a multi-factor matching approach via `MatchAnalyzer.compare()` that scores artifacts based on:
- Tag overlap (exact + partial matches)
- Type alignment (same artifact type preferred)
- Name/description lexical similarity
- Category/scope alignment

**Storage**: Results stored as `DuplicatePair` records with an `ignored` flag to allow users to suppress false positives. This avoids expensive recalculation on every request while maintaining data freshness through periodic background recomputation.

**Frontend Integration**: Tab-based UI in `ArtifactDetailsModal` follows existing patterns (Status, Deployments tabs). Uses `useSimilarArtifacts` hook for data fetching and React Query for caching.

### Patterns and Best Practices

- **OpenTelemetry instrumentation** at service level: all similarity calculations emit spans for observability
- **Pydantic schemas** for API validation: `SimilarArtifactDTO` and `SimilarityBreakdownDTO` with score breakdowns
- **Hook-based state management**: `useSimilarArtifacts` mirrors `useSyncStatus` pattern
- **MiniArtifactCard reuse**: Extend existing component rather than creating new, following DRY principle
- **Test-driven API endpoints**: Unit tests for `SimilarityService`, integration tests for endpoint

### Known Gotchas

- **Score normalization**: Different similarity factors (tags, name, type) need consistent 0-1 scaling
- **Query performance**: Pairwise comparison is O(n²) — consider caching/indexing for large collections
- **Accessibility**: Score display needs screen reader support; use semantic HTML + `aria-label`
- **Type sync**: Keep TypeScript types synchronized with Pydantic schemas via OpenAPI codegen

### Development Setup

No special environment setup beyond existing SkillMeat development environment. Requires:
- Running API server (`skillmeat web dev --api-only`)
- Running web dev server (`skillmeat web dev --web-only`)
- All tests passing before merging Phase 1

---

## Orchestration Quick Reference

### Phase 1: Core API Implementation

#### Batch 1 (parallel — no dependencies)
```bash
Task("data-layer-expert", "SA-P1-001: Add ignored boolean column to DuplicatePair. File: skillmeat/cache/models.py. Create Alembic migration.")
Task("python-backend-engineer", "SA-P1-002: Define SimilarityResult and ScoreBreakdown dataclasses in skillmeat/core/similarity.py.")
```

#### Batch 2 (parallel — depends on SA-P1-002)
```bash
Task("python-backend-engineer", "SA-P1-003: Add compare(artifact_a, artifact_b) method to MatchAnalyzer. File: skillmeat/core/scoring/match_analyzer.py.")
Task("python-backend-engineer", "SA-P1-005: Add SimilarArtifactDTO and SimilarityBreakdownDTO to skillmeat/api/schemas/artifacts.py.")
```

#### Batch 3 (sequential — depends on SA-P1-002, SA-P1-003)
```bash
Task("python-backend-engineer", "SA-P1-004: Implement SimilarityService in skillmeat/core/similarity.py. See phase plan for full spec.")
```

#### Batch 4 (parallel — depends on SA-P1-004)
```bash
Task("python-backend-engineer", "SA-P1-006: Implement GET /api/v1/artifacts/{id}/similar in skillmeat/api/routers/artifacts.py.")
Task("backend-architect", "SA-P1-007: Add OTel spans to SimilarityService and MatchAnalyzer.compare().")
Task("python-backend-engineer", "SA-P1-008: Unit tests for SimilarityService. File: tests/test_similarity_service.py.")
```

#### Batch 5 (parallel — depends on SA-P1-006)
```bash
Task("python-backend-engineer", "SA-P1-009: Integration tests for similar endpoint. File: tests/test_api_similar.py.")
Task("openapi-expert", "SA-P1-010: Update skillmeat/api/openapi.json with new endpoint and schemas.")
```

### Phase 2: Frontend Collection Tab

#### Batch 6 (depends on SA-P1-010)
```bash
Task("frontend-developer", "SA-P2-001: Generate TypeScript types from OpenAPI spec. Update skillmeat/web/types/artifacts.ts.")
```

#### Batch 7 (parallel — depends on SA-P2-001)
```bash
Task("frontend-developer", "SA-P2-002: Create useSimilarArtifacts hook in skillmeat/web/hooks/use-similar-artifacts.ts with caching.")
Task("ui-engineer-enhanced", "SA-P2-003: Extend MiniArtifactCard with showScore prop. File: skillmeat/web/components/ui/mini-artifact-card.tsx.")
```

#### Batch 8 (depends on SA-P2-002, SA-P2-003)
```bash
Task("ui-engineer-enhanced", "SA-P2-004: Implement SimilarArtifactsTab component with filtering and sorting. File: skillmeat/web/components/artifact/similar-artifacts-tab.tsx.")
```

#### Batch 9 (parallel — depends on SA-P2-004)
```bash
Task("ui-engineer-enhanced", "SA-P2-005: Register SimilarArtifactsTab in ArtifactDetailsModal. File: skillmeat/web/components/modal/artifact-details-modal.tsx.")
Task("frontend-developer", "SA-P2-006: Implement error and loading states for similar tab.")
Task("frontend-developer", "SA-P2-007: Add component tests for SimilarArtifactsTab and MiniArtifactCard. File: skillmeat/web/__tests__/similar-artifacts-tab.test.tsx.")
```

#### Batch 10 (depends on SA-P2-005)
```bash
Task("frontend-developer", "SA-P2-008: Add E2E test for similar artifacts workflow. File: skillmeat/web/e2e/similar-artifacts.spec.ts.")
```

---

## Completion Notes

*(Fill in when phase is complete)*

- What was built
- Key learnings
- Unexpected challenges
- Recommendations for next phase
