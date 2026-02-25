---
title: "Implementation Plan: Similar Artifacts \u2014 Detection, Comparison & Consolidation"
schema_version: 2
doc_type: implementation_plan
status: in-progress
created: 2026-02-25
updated: '2026-02-25'
feature_slug: similar-artifacts
feature_version: v1
prd_ref: docs/project_plans/PRDs/features/similar-artifacts-v1.md
plan_ref: null
scope: 'Build artifact-to-artifact similarity engine on existing scoring stack; expose
  via new API endpoint, Similar Artifacts tab in ArtifactDetailsModal and marketplace
  panels, color-coded marketplace badges with configurable thresholds, a Consolidation
  view for duplicate cluster management, and CLI parity via `skillmeat similar` and
  `skillmeat consolidate` commands.

  '
effort_estimate: 42 pts
architecture_summary: 'SimilarityService (new service layer) wraps ArtifactFingerprint
  + MatchAnalyzer + optional SemanticScorer (800 ms timeout / keyword-only fallback).
  A single new endpoint GET /api/v1/artifacts/{id}/similar is added to the artifacts
  router. Frontend adds React Query hooks, SimilarArtifactsTab, SimilarityBadge, SimilaritySettings
  sub-tab, and a full-page /collection/consolidate route. DuplicatePair gains an `ignored`
  boolean column via an additive Alembic migration. CLI gains `similar` and `consolidate`
  Click commands wired directly to SimilarityService.

  '
phases:
- 'Phase 1: Core Similarity Engine (backend service + API + DB migration)'
- "Phase 2: Similar Artifacts Tab \u2014 Collection (frontend tab + hooks)"
- "Phase 3: Similar Artifacts Tab \u2014 Marketplace (reuse tab in marketplace context)"
- 'Phase 4: Marketplace Similarity Badges (badges + settings sub-tab)'
- 'Phase 5: Collection Consolidation View (consolidation page + cluster API)'
- 'Phase 6: CLI Integration (similar + consolidate commands)'
test_strategy: 'Unit tests on SimilarityService (scorer fallback, score filtering,
  empty results). Integration tests on new API endpoints (happy path, 404, filter
  params). E2E tests covering Similar tab render, marketplace badge, and consolidation
  merge with auto-snapshot verification. Performance test: similar endpoint under
  2000 ms for 500-artifact collection.

  '
related_documents:
- docs/project_plans/PRDs/features/similar-artifacts-v1.md
- docs/project_plans/implementation_plans/features/similar-artifacts-v1/phase-1-2-backend-and-collection-tab.md
- docs/project_plans/implementation_plans/features/similar-artifacts-v1/phase-3-4-marketplace.md
- docs/project_plans/implementation_plans/features/similar-artifacts-v1/phase-5-6-consolidation-and-cli.md
- skillmeat/models.py
- skillmeat/core/scoring/match_analyzer.py
- skillmeat/core/scoring/semantic_scorer.py
- skillmeat/api/routers/match.py
- skillmeat/web/components/collection/artifact-details-modal.tsx
- skillmeat/web/components/collection/mini-artifact-card.tsx
- skillmeat/web/components/marketplace/source-card.tsx
- skillmeat/web/components/discovery/duplicate-review-modal.tsx
owner: null
contributors: []
priority: medium
risk_level: medium
category: product-planning
tags:
- implementation
- planning
- similarity
- deduplication
- consolidation
- marketplace
- collection
- cli
milestone: null
commit_refs: []
pr_refs: []
files_affected:
- skillmeat/models.py
- skillmeat/core/similarity.py
- skillmeat/core/scoring/match_analyzer.py
- skillmeat/cache/models.py
- skillmeat/cache/repositories.py
- skillmeat/api/routers/artifacts.py
- skillmeat/api/schemas/artifacts.py
- skillmeat/api/openapi.json
- skillmeat/web/hooks/similarity.ts
- skillmeat/web/types/similarity.ts
- skillmeat/web/components/collection/similar-artifacts-tab.tsx
- skillmeat/web/components/collection/artifact-details-modal.tsx
- skillmeat/web/components/marketplace/similarity-badge.tsx
- skillmeat/web/components/marketplace/source-card.tsx
- skillmeat/web/app/settings/components/similarity-settings.tsx
- skillmeat/web/app/collection/consolidate/page.tsx
- skillmeat/cli.py
---

# Implementation Plan: Similar Artifacts — Detection, Comparison & Consolidation

**Plan ID**: `IMPL-2026-02-25-SIMILAR-ARTIFACTS`
**Date**: 2026-02-25
**Author**: Implementation Planning Orchestrator (Sonnet 4.6)
**Related Documents**:
- **PRD**: `docs/project_plans/PRDs/features/similar-artifacts-v1.md`
- **Cross-source search PRD**: `docs/project_plans/PRDs/features/cross-source-artifact-search-v1.md`
- **Entity lifecycle PRD**: `docs/project_plans/PRDs/features/entity-lifecycle-management-v1.md`

**Complexity**: Large (L)
**Total Estimated Effort**: 42 story points
**Target Timeline**: ~3–4 weeks (phases can partially overlap)

---

## Executive Summary

Similar Artifacts surfaces SkillMeat's existing similarity scoring stack (ArtifactFingerprint, MatchAnalyzer, SemanticScorer) through purpose-built UX and CLI commands. Implementation follows SkillMeat's layered architecture — new service layer first, then API endpoint, then frontend components, then CLI — with phases grouped to enable parallel frontend/backend work where dependencies allow.

The six PRD phases map to three phase files to stay within the 800-line token budget:

| Phase file | Phases covered | Effort |
|---|---|---|
| [phase-1-2-backend-and-collection-tab.md](./similar-artifacts-v1/phase-1-2-backend-and-collection-tab.md) | Phase 1 (engine + API + DB) + Phase 2 (collection tab) | 18 pts |
| [phase-3-4-marketplace.md](./similar-artifacts-v1/phase-3-4-marketplace.md) | Phase 3 (marketplace tab) + Phase 4 (badges + settings) | 12 pts |
| [phase-5-6-consolidation-and-cli.md](./similar-artifacts-v1/phase-5-6-consolidation-and-cli.md) | Phase 5 (consolidation view) + Phase 6 (CLI) | 12 pts |

---

## Implementation Strategy

### Architecture Sequence

Following SkillMeat's layered architecture:

1. **Database Layer** — Additive Alembic migration: `DuplicatePair.ignored` boolean column (default `false`).
2. **Service Layer** — `SimilarityService` (`skillmeat/core/similarity.py`) orchestrating ArtifactFingerprint + MatchAnalyzer + SemanticScorer with 800 ms timeout.
3. **Repository Layer** — Repository method updates: mark/unmark `DuplicatePair.ignored`; fetch cluster data.
4. **API Layer** — New endpoint `GET /api/v1/artifacts/{id}/similar` in `artifacts.py` router; consolidation clusters endpoint.
5. **UI Layer** — React Query hooks, `SimilarArtifactsTab`, `SimilarityBadge`, `SimilaritySettings`, consolidation page.
6. **Testing Layer** — Unit, integration, E2E, and performance tests across all new code.
7. **Documentation Layer** — OpenAPI spec update; CLI `--help` strings; settings inline help.
8. **Deployment Layer** — Feature flags `SIMILAR_ARTIFACTS_ENABLED` and `SEMANTIC_SCORING_ENABLED`.

### Parallel Work Opportunities

- **Phase 2 frontend** (Similar tab) can begin once Phase 1 API endpoint is merged and the hook contract is agreed. Frontend can work against a mock response in parallel.
- **Phase 3** (marketplace tab reuse) is a minimal lift once Phase 2's `SimilarArtifactsTab` is stable; can run in parallel with Phase 4's badge work.
- **Phase 6** (CLI) depends only on `SimilarityService` being available; it does not require any frontend phases to complete first.
- **Documentation tasks** across all phases can be done by `documentation-writer` in parallel with final review of each phase.

### Critical Path

```
Phase 1 (DB + Service + API)
  → Phase 2 (Collection Tab)
      → Phase 3 (Marketplace Tab — reuse tab)
  → Phase 4 (Marketplace Badges + Settings — needs API + settings infrastructure)
  → Phase 5 (Consolidation — needs clusters API from Phase 1 service work)
  → Phase 6 (CLI — needs SimilarityService from Phase 1)
```

Phase 1 is the hard blocker for all other phases. Phases 2, 4, 5, and 6 can proceed in parallel after Phase 1.

---

## Phase Overview

| Phase | Title | Effort | Duration | Dependencies | Phase File |
|---|---|---|---|---|---|
| 1 | Core Similarity Engine | 11 pts | 3–4 days | None | [phase-1-2...](./similar-artifacts-v1/phase-1-2-backend-and-collection-tab.md) |
| 2 | Similar Tab — Collection | 7 pts | 2–3 days | Phase 1 API merged | [phase-1-2...](./similar-artifacts-v1/phase-1-2-backend-and-collection-tab.md) |
| 3 | Similar Tab — Marketplace | 2 pts | 1 day | Phase 2 tab stable | [phase-3-4...](./similar-artifacts-v1/phase-3-4-marketplace.md) |
| 4 | Marketplace Badges + Settings | 8 pts | 2–3 days | Phase 1 API merged | [phase-3-4...](./similar-artifacts-v1/phase-3-4-marketplace.md) |
| 5 | Collection Consolidation | 10 pts | 3–4 days | Phase 1 service + DB | [phase-5-6...](./similar-artifacts-v1/phase-5-6-consolidation-and-cli.md) |
| 6 | CLI Integration | 4 pts | 1–2 days | Phase 1 SimilarityService | [phase-5-6...](./similar-artifacts-v1/phase-5-6-consolidation-and-cli.md) |
| — | Testing (cross-phase) | Included above | — | Per phase | See each phase file |
| — | Documentation | Included above | — | Per phase | See each phase file |

**Total**: 42 story points

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| SemanticScorer latency causes Similar tab to feel slow | High | Medium | Hard 800 ms timeout; fall back to keyword-only; show progressive loading skeleton |
| Marketplace N+1 badge fetches degrade page performance | High | High | Batch badge queries via viewport-aware IntersectionObserver; deduplicate by source artifact ID |
| Similarity thresholds produce noisy results by default | Medium | Medium | Conservative defaults (floor ≥0.20); empty-state guidance to adjust threshold |
| Consolidation merge destroys data if snapshot fails | Critical | Low | Abort merge if snapshot fails; surface blocking error; never proceed without confirmed snapshot |
| Large collection (500+ artifacts) exceeds 2 s SLA | Medium | Medium | Limit full fingerprint comparison to top-N candidates by keyword score; 5-min staleTime cache |
| DuplicatePair schema extension causes migration issues | Low | Low | Additive migration only (add `ignored` boolean, default `false`); backward-compatible |
| CLI interactive wizard fails in non-TTY environments | Low | Medium | Detect non-TTY; fall back to `--non-interactive` JSON output mode |

### Schedule Risks

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Phase 1 backend complexity underestimated | High | Low | SimilarityService delegates to existing scorers; new code is orchestration only |
| Consolidation merge/snapshot UX iteration required | Medium | Medium | Reuse existing VersionMergeService and DiffViewer; minimal net-new merge logic |
| Marketplace badge IntersectionObserver batching is complex | Medium | Medium | Spike if needed; fallback to per-card query with rate limiting |

---

## Success Metrics

### Delivery Metrics

- All 6 phases complete with test suite passing in CI.
- Unit test coverage ≥80% on `SimilarityService` and new router handlers.
- Zero P0/P1 bugs in first 48 hours post-deploy.

### Feature Metrics

| Metric | Target | Measurement |
|---|---|---|
| Similar artifacts API p95 latency | <2 000 ms | API timing log |
| Marketplace badge paint overhead | <100 ms added | Lighthouse perf audit |
| Duplicate pair recall (vs manual review) | >80% of known duplicates surfaced | Manual spot-check |
| CLI `skillmeat similar` latency | <3 000 ms | CLI timing output |
| Consolidation actions per session (adoption) | >1 after launch | Event telemetry |

### Technical Metrics

- OpenAPI spec updated for new endpoint before merge.
- All badge variants meet WCAG 2.1 AA contrast.
- SemanticScorer timeout enforced; no uncaught scorer exceptions.

---

## Feature Flags

| Flag | Default | Controls |
|---|---|---|
| `SIMILAR_ARTIFACTS_ENABLED` | `true` | Similar tab, marketplace badge, consolidation view |
| `SEMANTIC_SCORING_ENABLED` | `true` (if HaikuEmbedder configured) | SemanticScorer usage within SimilarityService |

---

## Overall Quality Gates (Definition of Done)

- [ ] FR-1 through FR-16 (PRD) implemented and end-to-end tested.
- [ ] Similar tab renders in ArtifactDetailsModal with at least one result for a known-similar artifact pair.
- [ ] Marketplace badge appears on source cards for artifacts with similarity ≥ floor threshold.
- [ ] Consolidation merge, replace, and skip actions complete without data loss (snapshot verified).
- [ ] CLI `skillmeat similar` and `skillmeat consolidate` exit 0 with expected output.
- [ ] OpenAPI spec updated with new endpoint and schemas.
- [ ] DuplicatePair `ignored` migration is backward-compatible.
- [ ] SemanticScorer timeout enforced at 800 ms with keyword-only fallback.
- [ ] Accessibility: badges have `aria-label`; Similar tab is keyboard-navigable; WCAG 2.1 AA contrast on badge colors.
- [ ] `task-completion-validator` sign-off on each phase before proceeding.

---

## Phase File Links

- **Phases 1–2** (Core Engine + Collection Tab): [phase-1-2-backend-and-collection-tab.md](./similar-artifacts-v1/phase-1-2-backend-and-collection-tab.md)
- **Phases 3–4** (Marketplace Tab + Badges): [phase-3-4-marketplace.md](./similar-artifacts-v1/phase-3-4-marketplace.md)
- **Phases 5–6** (Consolidation + CLI): [phase-5-6-consolidation-and-cli.md](./similar-artifacts-v1/phase-5-6-consolidation-and-cli.md)

---

**Progress Tracking**: `.claude/progress/similar-artifacts/all-phases-progress.md`

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-02-25
