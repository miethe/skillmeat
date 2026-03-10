---
schema_version: 2
doc_type: phase_plan
title: "SkillBOM & Attestation - Phases 9-10: Web & Backstage"
description: >
  Web app provenance UI (Phase 9) + Backstage plugin integration (Phase 10).
  Frontend surfaces for BOM and attestation data.
audience:
  - ai-agents
  - developers
  - frontend-engineers
  - ui-engineers
tags:
  - implementation-plan
  - phases
  - skillbom
  - web
  - backstage
  - ui
created: 2026-03-10
updated: 2026-03-10
phase: 9-10
phase_title: "Web & Backstage: Frontend Surfaces"
prd_ref: /docs/project_plans/PRDs/features/skillbom-attestation-v1.md
plan_ref: /docs/project_plans/implementation_plans/features/skillbom-attestation-v1.md
entry_criteria:
  - Phase 7 API endpoints stable and tested
  - Phase 8 CLI commands functional
  - OpenAPI spec finalized
exit_criteria:
  - ProvenanceTab component renders on artifact detail pages
  - BomViewer displays context.lock contents
  - HistoryTimeline with keyboard navigation (WCAG 2.1 AA)
  - Backstage BOM card data shape correct
  - All API hooks (useArtifactHistory, etc) tested
  - E2E tests pass for all components
feature_slug: skillbom-attestation
effort_estimate: "22-26 story points"
timeline: "2 weeks"
parallelization: "Phase 9 and Phase 10 can run in parallel after Phase 7 API stable"
---

# SkillBOM & Attestation System - Phases 9-10: Web & Backstage

## Overview

Phase 9 implements React components for the web app (ProvenanceTab, BomViewer, HistoryTimeline, API hooks). Phase 10 extends the Backstage plugin with BOM card data shape and scaffolder actions.

Both phases consume the Phase 7 API endpoints — no duplicate data storage.

---

## Phase 9: Web App Integration

**Duration**: 2 weeks | **Effort**: 14-16 story points | **Assigned**: ui-engineer-enhanced

### Overview

Add frontend components for viewing BOM, history, and attestation data on artifact detail pages and project dashboards.

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Status |
|----|------|-------------|-------------------|----------|--------|
| 9.1 | `ProvenanceTab` component | New tab on artifact detail pages showing BOM snapshot and attestation metadata. Displays: (1) artifact name + version, (2) owner (user/team), (3) creation timestamp, (4) signature status, (5) related artifacts (if any). | Component renders without errors; displays all fields; responsive on mobile; matches design system | 2 | Pending |
| 9.2 | `BomViewer` component | Display context.lock contents in structured format. Shows: (1) BOM version + schema, (2) list of artifacts (name, type, version, hash, metadata), (3) timestamps. Filterable by artifact type. Copyable as JSON. | Component renders BOM JSON as structured table/tree view; filtering works; JSON export works; performance acceptable for 100+ artifacts | 2 | Pending |
| 9.3 | `AttestationBadge` component | Inline badge showing attestation status (user/team owner, signature status). Appears on artifact cards and detail pages. Tooltip shows owner ID and signature details. | Badge renders correctly; displays owner scope and signature status; tooltip readable; no layout shifts | 1 | Pending |
| 9.4 | `HistoryTimeline` component | Chronological event log with expandable event details. Shows: (1) event type (create/update/delete/deploy/sync), (2) timestamp, (3) actor (user/team), (4) diff preview (if available). Keyboard navigable (arrow keys to expand/collapse). Screen-reader friendly (ARIA labels). | Timeline renders events in chronological order; events expandable; keyboard navigation works; WCAG 2.1 AA compliant | 2 | Pending |
| 9.5 | Attestation filter panel | Sidebar/modal to filter attestations by owner scope, date range, artifact type. Integration with existing filter UI patterns. | Panel allows filtering by owner_scope, date range, artifact_id; filters apply to list; results update reactively | 1 | Pending |
| 9.6 | API hooks: `useArtifactHistory` | React hook to fetch artifact history. Signature: `useArtifactHistory(artifactId, filters)`. Returns: `{ events, isLoading, error, hasNextPage, nextCursor, pageSize }`. Handles pagination. | Hook fetches data from `/api/v1/bom/history` endpoint; returns correct shape; pagination works; errors handled | 2 | Pending |
| 9.7 | API hooks: `useBomSnapshot` | React hook to fetch current BOM snapshot. Signature: `useBomSnapshot(projectId, options)`. Returns: `{ bom, isLoading, error, signature }`. | Hook fetches from `/api/v1/bom/snapshot` endpoint; returns BOM JSON and signature; stale-time correctly set (30s for interactive) | 2 | Pending |
| 9.8 | API hooks: `useAttestations` | React hook to fetch attestations. Signature: `useAttestations(filters)`. Returns: `{ attestations, isLoading, error, hasNextPage }`. Owner-scoped by default. | Hook calls `/api/v1/attestations` endpoint; filters applied; pagination works; owner scope enforced | 1 | Pending |
| 9.9 | Integration with artifact detail page | Add ProvenanceTab to artifact detail page tabs. Tab appears alongside existing tabs (metadata, deployment, etc). | ProvenanceTab renders on artifact detail; data loads correctly; no breaking changes to existing tabs | 2 | Pending |
| 9.10 | BOM history timeline on project dashboard | Add new section to project dashboard showing recent BOM generation events and attestations. Shows: (1) last BOM snapshot timestamp, (2) recent history events (5-10), (3) team attestations (if applicable). | Dashboard section renders; shows live data; updates reactively; no performance regression | 2 | Pending |
| 9.11 | Cache invalidation for attestation mutations | When user creates attestation or triggers BOM generation, invalidate relevant cache keys to refresh UI. Uses React Query cache invalidation. | Cache invalidated correctly after mutations; UI updates without full page reload; stale times respected | 1 | Pending |
| 9.12 | Accessibility audit (WCAG 2.1 AA) | Audit all new components for keyboard navigation, screen reader compatibility, color contrast, focus management. Fix any violations. | Audit report generated; all violations fixed; components meet WCAG 2.1 AA; tested with screen readers | 2 | Pending |
| 9.13 | E2E tests for web components | Tests for component rendering, user interactions (filtering, pagination), data loading, error states. Use Playwright or Cypress. | Tests cover all component functionality; E2E tests pass; visual regression tests optional but recommended | 2 | Pending |
| 9.14 | Design system alignment | Ensure all new components match existing design system (colors, typography, spacing, shadows). Use shadcn/Radix primitives. | Components visually consistent with app; no custom CSS needed (use Tailwind); design review approved | 1 | Pending |

### Key Design Notes

- **Stale Times**: History queries 30s (interactive), attestation queries 2min (lighter traffic).
- **Pagination**: React Query cursor-based pagination; show "Load More" button or infinite scroll.
- **Error UI**: Show user-friendly error messages; retry buttons for transient failures.
- **Loading States**: Skeleton loaders for initial load; spinners for refresh.
- **ARIA Labels**: All timeline events and timeline markers have aria-labels for screen readers.
- **Keyboard Navigation**: Arrow keys to expand/collapse timeline events; Tab to navigate buttons.

### Deliverables

1. **Code**:
   - `skillmeat/web/components/provenance/provenance-tab.tsx` — ProvenanceTab component
   - `skillmeat/web/components/bom/bom-viewer.tsx` — BomViewer component
   - `skillmeat/web/components/bom/attestation-badge.tsx` — AttestationBadge component
   - `skillmeat/web/components/bom/history-timeline.tsx` — HistoryTimeline component
   - `skillmeat/web/hooks/useBom.ts` — useArtifactHistory, useBomSnapshot, useAttestations hooks
   - `skillmeat/web/lib/bom-utils.ts` — Utility functions for BOM/history data

2. **Tests**:
   - `skillmeat/web/__tests__/provenance-tab.test.tsx` — Component tests
   - `skillmeat/web/__tests__/bom-viewer.test.tsx` — BomViewer tests
   - `skillmeat/web/__tests__/history-timeline.test.tsx` — HistoryTimeline tests (keyboard nav)
   - `skillmeat/web/__tests__/useBom.test.ts` — Hook tests
   - `skillmeat/web/e2e/bom-workflow.e2e.ts` — End-to-end tests

### Exit Criteria

- [ ] ProvenanceTab renders on artifact detail pages
- [ ] BomViewer displays context.lock with filtering and export
- [ ] HistoryTimeline shows events with keyboard navigation and ARIA labels
- [ ] API hooks correctly fetch and cache data
- [ ] All components responsive on mobile
- [ ] WCAG 2.1 AA compliance verified
- [ ] E2E tests pass
- [ ] Design system alignment approved

---

## Phase 10: Backstage Plugin Integration

**Duration**: 1 week | **Effort**: 8-10 story points | **Assigned**: python-backend-engineer (API), ui-engineer-enhanced (plugin UI)

### Overview

Extend Backstage plugin with BOM card data shape and scaffolder actions. Plugin calls Phase 7 API endpoints to fetch live data without separate storage.

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Status |
|----|------|-------------|-------------------|----------|--------|
| 10.1 | Extend `/integrations/idp/bom-card/{project_id}` endpoint | API endpoint returns Backstage-compatible BOM card payload. Response shape: { projectId, bomSnapshot: { ... }, recentEvents: [...], attestations: [...], cardMetadata: { ... } }. Load time < 500ms. | Endpoint implemented in `idp_integration.py`; response format validated against Backstage spec; performance tested | 2 | Pending |
| 10.2 | Backstage entity card data shape | Define Backstage entity card data shape (catalog-info.yaml compatible). Fields: (1) projectId, (2) artifactCount, (3) lastBomSnapshot timestamp, (4) recentEvents count, (5) attestationStatus. | Data shape matches Backstage EntityPage card requirements; all fields populated correctly | 1 | Pending |
| 10.3 | Backstage EntityPage card component | New React component for Backstage EntityPage showing BOM card data. Displays: (1) project name, (2) artifact list from BOM, (3) recent history events, (4) attestation summary, (5) signature status. Styled to match Backstage theme. | Component renders correctly in Backstage EntityPage; data updates live via API; styling consistent with Backstage | 2 | Pending |
| 10.4 | `skillmeat:attest` scaffolder action | New scaffolder action (template step) to create attestation. Parameters: (1) artifact_ids (multi-select from BOM), (2) compliance_notes (text). Action calls `/api/v1/attestations` endpoint. | Action appears in Backstage scaffolder; artifact selection works; attestation created correctly; result shown to user | 2 | Pending |
| 10.5 | `skillmeat:bom-generate` scaffolder action | New scaffolder action to trigger BOM generation. Parameters: (1) include_memory_items (checkbox), (2) auto_sign (checkbox). Calls `/api/v1/bom/generate` endpoint. | Action appears in scaffolder; parameters respected; BOM generated and artifact created; success message shown | 1 | Pending |
| 10.6 | Scaffolder action integration with plugin | Actions registered in scaffolder template system. Templates can include SkillMeat actions in workflow steps. | Actions registered correctly; callable from Backstage scaffolder; error handling clear | 1 | Pending |
| 10.7 | E2E test: Backstage card renders and loads data | E2E test in Backstage environment: navigate to component catalog entry, verify BOM card appears, loads data from API, updates in real time. Card load time < 500ms. | Test passes; card renders correctly; API calls succeed; card load time measured and logged | 2 | Pending |

### Key Design Notes

- **No Separate Storage**: All data from Phase 7 API; no duplicate BOM storage in Backstage or separate DB.
- **Enterprise PAT Auth**: Use existing `verify_enterprise_pat` middleware for authentication.
- **Backstage Theme**: Match EntityPage card styling; follow Backstage design patterns.
- **Real-Time Updates**: Optional WebSocket polling for live BOM updates (future enhancement).
- **Error Handling**: Show user-friendly errors if API unreachable; fallback to cached snapshot if available.

### Deliverables

1. **Code**:
   - Extended `skillmeat/api/routers/idp_integration.py` — BOM card endpoint
   - `plugins/backstage-plugin-scaffolder-backend/src/actions/skillmeat-attest.ts` — Attest scaffolder action
   - `plugins/backstage-plugin-scaffolder-backend/src/actions/skillmeat-bom-generate.ts` — BOM generate action
   - `plugins/backstage-plugin-scaffolder-backend/src/components/SkillBOMCard.tsx` — EntityPage card component

2. **Tests**:
   - `skillmeat/api/tests/test_bom_card_endpoint.py` — API endpoint tests
   - `plugins/backstage-plugin-scaffolder-backend/src/__tests__/skillmeat-actions.test.ts` — Action tests
   - `plugins/backstage-plugin-scaffolder-backend/e2e/bom-card.e2e.ts` — E2E test in Backstage

### Exit Criteria

- [ ] `/integrations/idp/bom-card/{project_id}` endpoint implemented and tested
- [ ] Backstage card data shape Backstage-compatible
- [ ] EntityPage card component renders correctly
- [ ] `skillmeat:attest` scaffolder action functional
- [ ] `skillmeat:bom-generate` scaffolder action functional
- [ ] Card load time < 500ms
- [ ] E2E test passes in Backstage environment
- [ ] No separate BOM storage (API-driven only)

---

## Integration Points

### From Phase 7 API
- Both phases consume Phase 7 endpoints
- Phase 9 React hooks call Phase 7 endpoints
- Phase 10 Backstage card fetches from Phase 7 endpoint

### Between Phase 9 and 10
- ProvenanceTab can link to Backstage component entry (if applicable)
- Backstage card can link back to SkillMeat web app

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Backstage API rate limit | Cache BOM card data for 5min; implement exponential backoff for retries |
| Web component performance with large BOMs | Virtual scrolling for long lists; paginate history events (50 per page default) |
| WCAG compliance gaps | Accessibility audit by external expert; automated testing with axe-core |
| Backstage plugin breaks on minor API changes | Semantic versioning; backward-compatible API schema; deprecation period before breaking changes |

---

## Success Metrics

- **Web Component Tests**: >= 80% code coverage
- **E2E Tests**: All scenarios pass (rendering, filtering, pagination, error states)
- **Accessibility**: WCAG 2.1 AA compliance verified
- **Performance**: Backstage card loads in < 500ms; ProvenanceTab renders in < 200ms
- **API Adoption**: Phase 9-10 components use Phase 7 API exclusively (no direct DB access)

---

## Next Steps (Gate to Phase 11)

1. ✅ Phase 9-10 exit criteria verified
2. ✅ Web components tested and accessible
3. ✅ Backstage plugin tested in real Backstage environment
4. ✅ Phase 11 (Testing, Docs, Deployment) can begin with all surfaces stable

---

## References

- **PRD**: `/docs/project_plans/PRDs/features/skillbom-attestation-v1.md` § FR-12, FR-13, FR-14
- **Main Plan**: `/docs/project_plans/implementation_plans/features/skillbom-attestation-v1.md`
- **Web CLAUDE.md**: `skillmeat/web/CLAUDE.md`
- **Component Patterns**: `.claude/context/key-context/component-patterns.md`
- **NextJS Patterns**: `.claude/context/key-context/nextjs-patterns.md`
- **Testing Patterns**: `.claude/context/key-context/testing-patterns.md`
- **Backstage Docs**: https://backstage.io/docs/overview/what-is-backstage
