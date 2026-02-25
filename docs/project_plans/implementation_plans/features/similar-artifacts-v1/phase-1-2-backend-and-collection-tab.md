---
title: "Similar Artifacts — Phase 1–2: Core Similarity Engine + Collection Tab"
schema_version: 2
doc_type: phase_plan
status: draft
created: 2026-02-25
updated: 2026-02-25
feature_slug: similar-artifacts
feature_version: v1
phase: 1
phase_title: "Core Similarity Engine + Collection Tab"
prd_ref: docs/project_plans/PRDs/features/similar-artifacts-v1.md
plan_ref: docs/project_plans/implementation_plans/features/similar-artifacts-v1.md
entry_criteria:
  - "PRD approved"
  - "Branch feat/similar-artifacts created from main"
exit_criteria:
  - "All Phase 1 and Phase 2 tasks marked completed"
  - "SimilarityService unit tests pass at ≥80% coverage"
  - "GET /api/v1/artifacts/{id}/similar returns correct DTO list with score breakdown"
  - "Similar tab renders in ArtifactDetailsModal on known-similar artifact pair"
  - "task-completion-validator sign-off"
priority: medium
risk_level: medium
category: product-planning
tags:
  - phase-plan
  - backend
  - service-layer
  - api-layer
  - database
  - frontend
  - similar-artifacts
---

# Phase 1–2: Core Similarity Engine + Collection Tab

**Parent Plan**: [similar-artifacts-v1.md](../similar-artifacts-v1.md)
**Phases Covered**: Phase 1 (Core Similarity Engine) + Phase 2 (Similar Artifacts Tab — Collection)
**Combined Effort**: 18 story points
**Estimated Duration**: 5–7 days
**Assigned Primary Subagents**: `data-layer-expert`, `python-backend-engineer`, `backend-architect`, `ui-engineer-enhanced`, `frontend-developer`

---

## Entry Criteria

- PRD `docs/project_plans/PRDs/features/similar-artifacts-v1.md` approved.
- Branch `feat/similar-artifacts` created from `main`.
- Existing scoring infrastructure confirmed stable: `ArtifactFingerprint` (models.py:458-570), `MatchAnalyzer`, `SemanticScorer`.

---

## Phase 1: Core Similarity Engine

### Overview

Phase 1 builds the backend foundation: an additive DB migration, the new `SimilarityService`, Pydantic schemas, and the `GET /api/v1/artifacts/{id}/similar` endpoint. No frontend work in this phase. Phase 2 is unblocked once the API endpoint is merged.

**Duration**: 3–4 days
**Dependencies**: None

### Parallelization Opportunities

- **P1-A (DB + migration)**: `data-layer-expert` can work independently from day 1.
- **P1-B (SimilarityService + schemas)**: `python-backend-engineer` + `backend-architect` can start immediately and work in parallel with P1-A.
- **P1-C (API router + endpoint)**: blocked until P1-B (service + schemas) is complete.
- **P1-D (Unit + integration tests)**: blocked until P1-B and P1-C are merged.

### Task Table — Phase 1

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---|---|---|---|---|---|---|
| SA-P1-001 | DuplicatePair.ignored migration | Add `ignored` boolean column (default `false`) to `DuplicatePair` in `skillmeat/cache/models.py`. Create Alembic migration. | Migration runs cleanly; `alembic downgrade` is safe (column dropped); existing rows default to `false`. | 1 pt | `data-layer-expert` | None |
| SA-P1-002 | SimilarityResult dataclass | Define `SimilarityResult` and `ScoreBreakdown` dataclasses in `skillmeat/core/similarity.py`. Fields: `artifact_id`, `artifact`, `composite_score`, `breakdown` (content_score, structure_score, metadata_score, keyword_score, semantic_score). | Dataclasses instantiate correctly; all fields typed; imports clean. | 1 pt | `python-backend-engineer` | None |
| SA-P1-003 | MatchAnalyzer.compare() helper | Add `compare(artifact_a, artifact_b) -> ScoreBreakdown` method to `MatchAnalyzer` (`skillmeat/core/scoring/match_analyzer.py`). Produces keyword score between two artifacts using existing TF-IDF logic. | Method returns float in [0, 1]; existing `score()` behavior unchanged; unit test for compare(). | 2 pts | `python-backend-engineer` | SA-P1-002 |
| SA-P1-004 | SimilarityService — core | Implement `SimilarityService` in `skillmeat/core/similarity.py`. Method `find_similar(artifact_id, limit=10, min_score=0.3, source='collection') -> list[SimilarityResult]`. Orchestrates: (1) fetch target artifact, (2) fetch candidate artifacts by source param, (3) score each via ArtifactFingerprint + MatchAnalyzer.compare() + optional SemanticScorer with 800 ms timeout, (4) filter by min_score, (5) sort descending, (6) return top N. | Returns ranked list; SemanticScorer timeout (800 ms) falls back to keyword-only transparently; returns empty list (not error) when no candidates meet min_score; unit tests for happy path, fallback, empty result, score filter. | 5 pts | `backend-architect`, `python-backend-engineer` | SA-P1-002, SA-P1-003 |
| SA-P1-005 | Pydantic schemas | Add `SimilarArtifactDTO` and `SimilarityBreakdownDTO` to `skillmeat/api/schemas/artifacts.py`. Fields mirror `SimilarityResult`. Include `match_type` enum: `exact`, `near_duplicate`, `similar`, `related`. | Schemas serialize to JSON correctly; all fields documented with descriptions for OpenAPI. | 1 pt | `python-backend-engineer` | SA-P1-002 |
| SA-P1-006 | API endpoint | Implement `GET /api/v1/artifacts/{id}/similar` in `skillmeat/api/routers/artifacts.py`. Query params: `limit` (int, default 10, max 50), `min_score` (float, 0–1, default 0.3), `source` (enum: `collection`\|`marketplace`\|`all`, default `collection`), `cursor` (str, optional). Returns `list[SimilarArtifactDTO]` with cursor pagination. 404 if artifact not found. Ownership enforced (user can only query own artifacts). | 200 with DTO list on happy path; 404 on unknown artifact; 422 on invalid params; ErrorResponse envelope on errors; OpenAPI docs populated. | 2 pts | `python-backend-engineer` | SA-P1-004, SA-P1-005 |
| SA-P1-007 | OpenTelemetry instrumentation | Add OTel spans to `SimilarityService.find_similar()`, `MatchAnalyzer.compare()`, and SemanticScorer invocation. Structured JSON log per query: `artifact_id`, `result_count`, `latency_ms`, `scorer_used`. | Spans visible in trace output; log entries include all required fields; scorer fallback logs `scorer_used: keyword_only`. | 1 pt | `backend-architect` | SA-P1-004 |
| SA-P1-008 | Unit tests — SimilarityService | pytest unit tests covering: happy path (results returned), empty result (no candidates meet min_score), SemanticScorer timeout triggers keyword-only fallback, score filtering by min_score, result limit enforcement. Mock ArtifactFingerprint, MatchAnalyzer, SemanticScorer. | ≥80% line coverage on `skillmeat/core/similarity.py`; all test cases pass. | 2 pts | `python-backend-engineer` | SA-P1-004 |
| SA-P1-009 | Integration tests — similar endpoint | pytest integration tests against the new endpoint: happy path (200 with results), empty results (200 with empty list), unknown artifact (404), `min_score` filter, `source` filter, `limit` param. Use test DB with known-similar artifact fixture pair. | All integration test cases pass; endpoint behaves consistently with unit-tested service. | 2 pts | `python-backend-engineer` | SA-P1-006, SA-P1-008 |
| SA-P1-010 | OpenAPI spec update | Regenerate or manually update `skillmeat/api/openapi.json` to include the new `/api/v1/artifacts/{id}/similar` endpoint and `SimilarArtifactDTO`/`SimilarityBreakdownDTO` schemas. | `openapi.json` validates; new endpoint and schemas visible in Swagger UI. | 1 pt | `openapi-expert` | SA-P1-006 |

**Phase 1 Story Points**: 18 pts → corrected: SA-P1-001 through SA-P1-010 = **18 pts**

> Note: PRD story SA-001 = 5 pts (engine), SA-002 = 3 pts (endpoint), SA-003 = 1 pt (migration). Phase 1 total reconciles to ~18 pts including instrumentation, schemas, and tests.

### Phase 1 Quality Gates

- [ ] Alembic migration runs forward and backward cleanly.
- [ ] `SimilarityService.find_similar()` unit tests pass at ≥80% coverage.
- [ ] `GET /api/v1/artifacts/{id}/similar` integration tests pass (happy path, 404, filters).
- [ ] SemanticScorer 800 ms timeout enforced and fallback logged.
- [ ] OpenAPI spec updated and validates.
- [ ] OTel spans present and structured log entries correct.
- [ ] `task-completion-validator` sign-off before Phase 2 begins.

---

## Phase 2: Similar Artifacts Tab — Collection

### Overview

Phase 2 adds the "Similar" tab to `ArtifactDetailsModal`. The tab uses a new React Query hook to call the Phase 1 endpoint and renders results in a `MiniArtifactCard` grid. Score overlay and breakdown tooltip are added to `MiniArtifactCard` via an opt-in `showScore` prop.

**Duration**: 2–3 days
**Dependencies**: Phase 1 API endpoint merged to branch (SA-P1-006).

### Parallelization Opportunities

- Frontend development can start with a mocked response while Phase 1 integration tests finalize.
- Hook and component work (**P2-A**) can proceed in parallel once contract is agreed.
- Accessibility audit (**P2-F**) runs after component implementation.
- E2E tests (**P2-E**) require Phase 1 endpoint in staging environment.

### Task Table — Phase 2

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---|---|---|---|---|---|---|
| SA-P2-001 | TypeScript types | Create `skillmeat/web/types/similarity.ts` with `SimilarArtifact`, `SimilarityBreakdown`, `SimilarArtifactsResponse`, `SimilaritySource` enum mirroring backend DTOs. | Types compile cleanly; no `any`; exported from `types/index.ts`. | 0.5 pt | `frontend-developer` | SA-P1-010 (OpenAPI spec) |
| SA-P2-002 | useSimilarArtifacts hook | Create `skillmeat/web/hooks/similarity.ts` with `useSimilarArtifacts(artifactId: string, options?: { limit?: number; minScore?: number; source?: SimilaritySource })`. Uses React Query `useQuery`. `staleTime: 5 * 60 * 1000` (5 min). Enabled only when `artifactId` is defined. | Hook returns `{ data, isLoading, isError }`; disabled when no artifactId; staleTime=5min confirmed in test. | 1 pt | `frontend-developer` | SA-P2-001 |
| SA-P2-003 | MiniArtifactCard — showScore prop | Add optional `showScore?: boolean` and `similarityScore?: number` props to `skillmeat/web/components/collection/mini-artifact-card.tsx`. When `showScore=true`, render a small percentage badge in the card's top-right corner. Wrap badge in Radix UI Tooltip showing score breakdown fields (content, structure, metadata, keyword percentages). | Badge renders when `showScore=true`; no badge when `showScore=false` (default); tooltip shows breakdown; keyboard accessible (Escape closes tooltip); existing MiniArtifactCard tests still pass. | 2 pts | `ui-engineer-enhanced` | SA-P2-001 |
| SA-P2-004 | SimilarArtifactsTab component | Create `skillmeat/web/components/collection/similar-artifacts-tab.tsx`. Uses `useSimilarArtifacts(artifactId)`. Renders: (a) loading skeleton (grid of 6 placeholder cards), (b) empty state with descriptive message and suggestion to lower threshold, (c) result grid using `grid grid-cols-2 gap-3 pb-1 pr-1 sm:grid-cols-3` of `MiniArtifactCard` with `showScore=true`. Clicking a card opens that artifact's `ArtifactDetailsModal`. | All three states render correctly; grid layout matches spec; card click opens correct modal; keyboard navigation works (Tab through cards, Enter/Space to open). | 3 pts | `ui-engineer-enhanced` | SA-P2-002, SA-P2-003 |
| SA-P2-005 | ArtifactDetailsModal tab registration | Extend `BASE_TABS` constant in `skillmeat/web/components/collection/artifact-details-modal.tsx` with a new "Similar" tab entry. Icon: `GitCompare` (Lucide). Wire `TabContentWrapper` to render `SimilarArtifactsTab` with the current `artifactId`. | "Similar" tab appears in modal tab bar; tab renders `SimilarArtifactsTab` content; other existing tabs unaffected; `ArtifactDetailsTab` type updated. | 1 pt | `ui-engineer-enhanced` | SA-P2-004 |
| SA-P2-006 | Error state handling | When `useSimilarArtifacts` returns `isError=true`, the tab renders a non-blocking inline error state (not a full modal crash). Includes a retry button. Error must not propagate to parent modal. | Error boundary or conditional render prevents modal crash; error message visible in tab area; retry button re-triggers query. | 0.5 pt | `frontend-developer` | SA-P2-004 |
| SA-P2-007 | Component tests | Jest/React Testing Library tests for `SimilarArtifactsTab`: loading state renders skeleton, empty state renders message, result state renders card grid, card click triggers modal open, error state renders retry. Tests for MiniArtifactCard new props: score badge visible when `showScore=true`. | All component tests pass; no regressions in existing MiniArtifactCard tests. | 1 pt | `frontend-developer` | SA-P2-004, SA-P2-003 |
| SA-P2-008 | E2E test — Similar tab | Playwright E2E test: navigate to Collection page → open ArtifactDetailsModal for a known artifact → click "Similar" tab → verify MiniArtifactCard grid renders with at least one result (requires known-similar artifact pair in test fixture). | E2E test passes in CI with known-similar fixture; tab is reachable by keyboard. | 1 pt | `frontend-developer` | SA-P2-005 |

**Phase 2 Story Points**: ~9 pts (aligns with PRD SA-004 = 3 pts, SA-005 = 2 pts, plus hook, types, tests, E2E)

### Phase 2 Quality Gates

- [ ] `SimilarArtifactsTab` renders all three states (loading, empty, results) correctly.
- [ ] "Similar" tab appears in `ArtifactDetailsModal` without breaking existing tabs.
- [ ] Score badge and breakdown tooltip pass keyboard accessibility test.
- [ ] Component tests pass; no existing MiniArtifactCard test regressions.
- [ ] E2E test passes with known-similar fixture pair.
- [ ] Error state does not crash parent modal.
- [ ] `task-completion-validator` sign-off.

---

## Key Files

| File | Role | Change Type |
|---|---|---|
| `skillmeat/cache/models.py` | DuplicatePair model | Additive column |
| `skillmeat/core/similarity.py` | SimilarityService (new) | New file |
| `skillmeat/core/scoring/match_analyzer.py` | MatchAnalyzer | Add `compare()` method |
| `skillmeat/api/routers/artifacts.py` | API router | New endpoint |
| `skillmeat/api/schemas/artifacts.py` | Pydantic schemas | New DTOs |
| `skillmeat/api/openapi.json` | OpenAPI contract | Update |
| `skillmeat/web/types/similarity.ts` | TS types | New file |
| `skillmeat/web/hooks/similarity.ts` | React Query hook | New file |
| `skillmeat/web/components/collection/mini-artifact-card.tsx` | Card component | Additive props |
| `skillmeat/web/components/collection/similar-artifacts-tab.tsx` | Tab component | New file |
| `skillmeat/web/components/collection/artifact-details-modal.tsx` | Modal host | Tab registration |
| `tests/test_similarity_service.py` | Unit tests | New file |
| `tests/test_api_similar.py` | Integration tests | New file |

---

**Back to parent plan**: [similar-artifacts-v1.md](../similar-artifacts-v1.md)
**Next phase file**: [phase-3-4-marketplace.md](./phase-3-4-marketplace.md)
