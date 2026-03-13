---
schema_version: 2
doc_type: progress
type: progress
prd: skillbom-attestation
feature_slug: skillbom-attestation
phase: 9-10
status: completed
created: '2026-03-10'
updated: '2026-03-13'
prd_ref: docs/project_plans/PRDs/features/skillbom-attestation-v1.md
plan_ref: docs/project_plans/implementation_plans/features/skillbom-attestation-v1/phase-9-10-web-backstage.md
commit_refs:
- 579df599
- 4020af8d
- 52ed41db
- 3a53f9f9
pr_refs: []
owners:
- ui-engineer-enhanced
- python-backend-engineer
contributors: []
tasks:
- id: TASK-9.1
  name: Implement ProvenanceTab component for artifact detail pages (name, owner,
    timestamp, signature status, related artifacts)
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimate: 2 pts
- id: TASK-9.2
  name: Implement BomViewer component displaying context.lock contents as structured
    table/tree with type filtering and JSON export
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimate: 2 pts
- id: TASK-9.3
  name: Implement AttestationBadge inline component showing owner scope and signature
    status with tooltip
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimate: 1 pt
- id: TASK-9.4
  name: Implement HistoryTimeline component with expandable events, diff preview,
    keyboard navigation (arrow keys), and ARIA labels (WCAG 2.1 AA)
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimate: 2 pts
- id: TASK-9.5
  name: Implement attestation filter panel (owner_scope, date range, artifact_id)
    integrated with existing filter UI patterns
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimate: 1 pt
- id: TASK-9.6
  name: Implement useArtifactHistory React hook fetching from /api/v1/bom/history
    with cursor pagination and filter support
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimate: 2 pts
- id: TASK-9.7
  name: Implement useBomSnapshot and useAttestations React hooks, integrate ProvenanceTab
    into artifact detail page, add BOM history section to project dashboard, and implement
    cache invalidation for attestation mutations
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - TASK-9.1
  - TASK-9.2
  - TASK-9.3
  - TASK-9.4
  - TASK-9.5
  - TASK-9.6
  estimate: 6 pts
- id: TASK-10.1
  name: Implement /integrations/idp/bom-card/{project_id} API endpoint with Backstage-renderable
    payload (snapshot + recent events + attestations)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 2 pts
- id: TASK-10.2
  name: Define Backstage entity card data shape (catalog-info.yaml compatible) with
    projectId, artifactCount, lastBomSnapshot, recentEvents count, attestationStatus
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-10.1
  estimate: 1 pt
- id: TASK-10.3
  name: Implement Backstage EntityPage SkillBOMCard React component showing BOM data
    styled to Backstage theme
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - TASK-10.1
  - TASK-10.2
  estimate: 2 pts
- id: TASK-10.4
  name: Implement skillmeat:attest scaffolder action (artifact multi-select, compliance
    notes, calls /api/v1/attestations)
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - TASK-10.1
  estimate: 2 pts
- id: TASK-10.5
  name: Implement skillmeat:bom-generate scaffolder action, register both actions
    in scaffolder template system, add E2E test verifying Backstage card loads in
    < 500ms, add WCAG 2.1 AA accessibility audit for all web components
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - TASK-10.3
  - TASK-10.4
  estimate: 5 pts
parallelization:
  batch_1:
  - TASK-9.1
  - TASK-9.2
  - TASK-9.3
  batch_2:
  - TASK-9.4
  - TASK-9.5
  - TASK-9.6
  batch_3:
  - TASK-9.7
  - TASK-10.1
  - TASK-10.2
  batch_4:
  - TASK-10.3
  - TASK-10.4
  - TASK-10.5
total_tasks: 12
completed_tasks: 12
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
---

# Phase 9-10 Progress: Web & Backstage — Frontend Surfaces

**Objective**: Build React components for in-app BOM/history/attestation viewing (ProvenanceTab, BomViewer, HistoryTimeline) and extend the Backstage plugin with a live BOM entity card and scaffolder actions.

## Entry Criteria

- Phase 7 API endpoints stable, tested, and documented in `skillmeat/api/openapi.json`
- Phase 8 CLI commands functional
- OpenAPI spec finalized — no further breaking changes to Phase 7 endpoints

## Exit Criteria

- `ProvenanceTab` renders on artifact detail pages alongside existing tabs (no regressions)
- `BomViewer` displays structured `context.lock` contents with type filtering and JSON export
- `AttestationBadge` renders on artifact cards with owner scope and signature status tooltip
- `HistoryTimeline` shows time-ordered events with expandable diffs, arrow-key navigation, and ARIA labels
- `useArtifactHistory`, `useBomSnapshot`, `useAttestations` hooks tested and cached with correct stale times (history 30s, attestations 2min)
- Cache invalidated on attestation create and BOM generate mutations
- All components responsive on mobile and visually consistent with design system (shadcn/Radix)
- WCAG 2.1 AA compliance verified for all new components
- `/integrations/idp/bom-card/{project_id}` returns Backstage-renderable JSON payload with current snapshot + recent events + attestation summary
- `SkillBOMCard` Backstage EntityPage component renders live BOM data matching Backstage theme
- `skillmeat:attest` and `skillmeat:bom-generate` scaffolder actions registered and callable from templates
- Backstage card E2E test: load time < 500ms
- Web component test coverage >= 80%
- No direct DB access from web components (Phase 7 API exclusively)

## Phase Plan Reference

`docs/project_plans/implementation_plans/features/skillbom-attestation-v1/phase-9-10-web-backstage.md`
