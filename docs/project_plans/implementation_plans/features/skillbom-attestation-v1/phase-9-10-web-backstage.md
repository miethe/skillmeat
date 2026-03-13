---
schema_version: 2
doc_type: phase_plan
title: "SkillBOM & Attestation - Phases 9-10: Web & Backstage Backend"
description: >
  Web app provenance UI (Phase 9) + Backstage backend integration (Phase 10).
  Frontend provenance surfaces plus backend/scaffolder integration.
audience:
  - ai-agents
  - developers
  - frontend-engineers
  - ui-engineers
  - platform-engineers
tags:
  - implementation-plan
  - phases
  - skillbom
  - web
  - backstage
  - ui
created: 2026-03-10
updated: 2026-03-11
phase: 9-10
phase_title: "Web & Backstage Backend: Provenance Surfaces"
prd_ref: /docs/project_plans/PRDs/features/skillbom-attestation-v1.md
plan_ref: /docs/project_plans/implementation_plans/features/skillbom-attestation-v1.md
entry_criteria:
  - Phase 7 API endpoints stable and tested
  - Phase 8 CLI commands functional
  - OpenAPI spec and typed client artifacts finalized
exit_criteria:
  - ProvenanceTab component renders on artifact detail pages
  - BomViewer displays `context.lock` contents
  - ActivityTimeline distinguishes provenance activity from existing version history
  - Backstage backend payload contract finalized
  - All new API hooks tested
  - Web component and backend integration tests pass
feature_slug: skillbom-attestation
effort_estimate: "19-23 story points"
timeline: "2 weeks"
parallelization: "Phase 9 and Phase 10 can run in parallel after Phase 7 API stable"
---

# SkillBOM & Attestation System - Phases 9-10: Web & Backstage Backend

## Overview

Phase 9 implements React components and hooks for the web app’s provenance surfaces. Phase 10 extends the existing Backstage backend/scaffolder integration with BOM payloads and actions.

Important UI boundary:

- Existing artifact version-history UI stays in place.
- New provenance/activity UI is added beside it, not as a replacement.
- Backstage frontend EntityPage UI is explicitly out of scope for this plan version and should be tracked separately.

---

## Phase 9: Web App Integration

**Duration**: 2 weeks | **Effort**: 14-16 story points | **Assigned**: ui-engineer-enhanced

### Overview

Add frontend components for viewing BOM, activity history, and attestation data on artifact detail pages and project dashboards. The work should integrate with current artifact detail modals/pages and existing query conventions rather than creating parallel history surfaces.

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Status |
|----|------|-------------|-------------------|----------|--------|
| 9.1 | `ProvenanceTab` component | New tab on artifact detail surfaces showing BOM snapshot and attestation metadata. Displays artifact name/version, owner scope, creation timestamp, signature status, and related artifacts. | Component renders without errors; displays all fields; responsive on mobile; matches design system | 2 | Pending |
| 9.2 | `BomViewer` component | Display `context.lock` contents in structured format with artifact-type filtering and JSON export. | Component renders structured BOM JSON; filtering works; JSON export works; performance acceptable for 100+ artifacts | 2 | Pending |
| 9.3 | `AttestationBadge` component | Inline badge showing attestation status (user/team/enterprise owner, signature status). Appears on artifact cards and detail pages. | Badge renders correctly; tooltip readable; no layout shifts | 1 | Pending |
| 9.4 | `ActivityTimeline` component | Chronological activity log with expandable event details. Shows event type, timestamp, actor, owner scope, and diff preview or metadata. Keyboard navigable and screen-reader friendly. | Timeline renders activity events in order; events expandable; keyboard navigation works; WCAG 2.1 AA compliant | 2 | Pending |
| 9.5 | Attestation filter panel | Sidebar/modal to filter attestations by owner scope, date range, and artifact type. | Panel allows filtering; results update reactively; aligns with existing filter patterns | 1 | Pending |
| 9.6 | API hook: `useArtifactActivityHistory` | React hook to fetch artifact activity history from the new Phase 7 endpoint. | Hook fetches from the activity-history endpoint; pagination works; errors handled correctly | 2 | Pending |
| 9.7 | API hook: `useBomSnapshot` | React hook to fetch current BOM snapshot. | Hook fetches BOM snapshot endpoint; returns BOM JSON and signature metadata; stale time tuned appropriately | 2 | Pending |
| 9.8 | API hook: `useAttestations` | React hook to fetch attestations. | Hook calls attestation endpoint; filters applied; pagination works; owner scope enforced | 1 | Pending |
| 9.9 | Integrate with existing artifact detail surfaces | Add `ProvenanceTab` to existing artifact detail page/modal tab sets. Do not replace the current History tab. | ProvenanceTab renders alongside the current History tab; no breaking changes to existing tabs or URL state | 2 | Pending |
| 9.10 | Project dashboard provenance section | Add section to project dashboard showing latest BOM snapshot, recent activity events, and recent attestations. | Dashboard section renders; shows live data; updates reactively; no performance regression | 2 | Pending |
| 9.11 | Cache invalidation for provenance mutations | Invalidate relevant cache keys after attestation creation or BOM generation. | Cache invalidated correctly after mutations; UI updates without full page reload | 1 | Pending |
| 9.12 | Accessibility audit (WCAG 2.1 AA) | Audit all new components for keyboard navigation, screen reader compatibility, color contrast, and focus management. | Audit report generated; violations fixed; components meet WCAG 2.1 AA | 2 | Pending |
| 9.13 | E2E tests for web components | Tests for rendering, filtering, pagination, data loading, and error states. | Tests cover component functionality; E2E tests pass | 2 | Pending |
| 9.14 | Design system alignment | Ensure all new components follow the existing design system and current artifact-detail interaction patterns. | Components visually consistent with app; integrates cleanly with existing modal/page components | 1 | Pending |

### Wireframes & Component Hierarchy

Visual wireframes and component hierarchy specifications are available for all Phase 9 components:

| Wireframe | File | Component |
|-----------|------|-----------|
| WF-1 | `wireframes/wf-1-provenance-tab.png` | ProvenanceTab in entity modal |
| WF-2 | `wireframes/wf-2-bom-viewer.png` | BomViewer expanded view |
| WF-3 | `wireframes/wf-3-attestation-badge.png` | AttestationBadge variants |
| WF-4 | `wireframes/wf-4-activity-timeline.png` | ActivityTimeline full view |
| WF-5 | `wireframes/wf-5-filter-panel.png` | Attestation filter panel |
| WF-6 | `wireframes/wf-6-dashboard-provenance.png` | Dashboard provenance section |

**Supporting docs** (in `wireframes/`):
- `wireframe-brief.md` — Full specifications, layout ASCII art, and generation instructions
- `gemini-layout-analysis.md` — Integration validation, refined component hierarchies, and shadcn/Radix primitive mapping

**Wireframe usage policy**: These wireframes are AI-generated layout scaffolds, not pixel-perfect design specs. During implementation:

1. **Layout and structure are authoritative** — section ordering, information hierarchy, and component composition should match the wireframes.
2. **Visual styling is NOT authoritative** — fonts, colors, spacing, border radii, shadows, and visual details in the wireframes are approximations. Always defer to:
   - Existing shadcn/ui primitives (`Badge`, `Card`, `Tabs`, `Tooltip`, `Popover`, `ScrollArea`, etc.) — use them as-is, do not hand-style to match wireframe visuals.
   - Existing component patterns — match the look of `entity-card.tsx`, `unified-entity-modal.tsx`, `filters.tsx`, `version-tree.tsx`, and other established components.
   - The `cn()` utility and Tailwind classes already used in the codebase (zinc palette, Inter font, tight spacing).
3. **When wireframe and codebase conflict, codebase wins** — if a wireframe shows a custom filter panel but the codebase already has `TagFilterPopover` with established patterns, follow the codebase pattern.
4. **Component hierarchy from `gemini-layout-analysis.md` is the primary implementation reference** — it maps each wireframe to specific shadcn primitives and React component trees.

### Key Design Notes

- **Do Not Replace Existing History**: Preserve current version-history components and query hooks. Add provenance/activity as a separate tab or panel.
- **Hook Naming**: Use explicit provenance/activity hook names; do not overload the existing `useArtifactHistory`.
- **Query Clients**: Prefer the generated SDK/client artifacts or existing API helper patterns rather than raw one-off fetch helpers.
- **Error UI**: Show user-friendly error messages with retry actions for transient failures.
- **Loading States**: Skeleton loaders for initial load; light spinners for refresh.
- **Tab Integration**: Add `provenance` to the tab bar in `unified-entity-modal.tsx` after History, using the same `rounded-none border-b-2` styling. Use `ShieldCheck` icon from Lucide.
- **Badge Sizing**: AttestationBadge must match existing source/version badge dimensions in entity-card.tsx. Use `Badge` + `Tooltip` from shadcn.

### Deliverables

1. **Code**:
   - `skillmeat/web/components/provenance/provenance-tab.tsx` — ProvenanceTab component
   - `skillmeat/web/components/bom/bom-viewer.tsx` — BomViewer component
   - `skillmeat/web/components/bom/attestation-badge.tsx` — AttestationBadge component
   - `skillmeat/web/components/bom/activity-timeline.tsx` — ActivityTimeline component
   - `skillmeat/web/hooks/useArtifactActivityHistory.ts` — Activity-history hook
   - `skillmeat/web/hooks/useBomSnapshot.ts` — BOM snapshot hook
   - `skillmeat/web/hooks/useAttestations.ts` — Attestation hook
   - Existing artifact detail surfaces under `skillmeat/web/components/collection/` and `skillmeat/web/components/entity/` updated to register the Provenance tab

2. **Tests**:
   - `skillmeat/web/__tests__/provenance-tab.test.tsx` — Component tests
   - `skillmeat/web/__tests__/bom-viewer.test.tsx` — BomViewer tests
   - `skillmeat/web/__tests__/activity-timeline.test.tsx` — ActivityTimeline tests
   - `skillmeat/web/__tests__/useArtifactActivityHistory.test.ts` — Hook tests
   - `skillmeat/web/e2e/bom-workflow.e2e.ts` — End-to-end tests

### Exit Criteria

- [ ] ProvenanceTab renders on artifact detail surfaces
- [ ] BomViewer displays `context.lock` with filtering and export
- [ ] ActivityTimeline shows provenance activity with keyboard navigation and ARIA labels
- [ ] New hooks correctly fetch and cache provenance data
- [ ] Existing version-history UI remains intact
- [ ] All components responsive on mobile
- [ ] WCAG 2.1 AA compliance verified
- [ ] E2E tests pass
- [ ] Design system alignment approved

---

## Phase 10: Backstage Backend Integration

**Duration**: 1 week | **Effort**: 5-7 story points | **Assigned**: python-backend-engineer

### Overview

Extend the existing Backstage backend/scaffolder integration with BOM payloads and scaffolder actions. This phase is explicitly backend-only for this plan version.

Out of scope for this phase:

- Backstage frontend package work
- EntityPage card React component
- Frontend E2E inside a Backstage app shell

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Status |
|----|------|-------------|-------------------|----------|--------|
| 10.1 | Extend `/integrations/idp/bom-card/{project_id}` endpoint | API endpoint returns a BOM payload for Backstage backend/scaffolder consumers. Response includes `projectId`, `bomSnapshot`, recent activity events, attestation summary, and payload metadata. | Endpoint implemented in `idp_integration.py`; payload validated against agreed contract; performance tested | 2 | Pending |
| 10.2 | Define stable payload contract for future frontend consumers | Document the payload shape that a future Backstage frontend card can consume. | Payload contract documented; fields populated correctly; no duplicate storage introduced | 1 | Pending |
| 10.3 | `skillmeat:attest` scaffolder action | New scaffolder action to create attestation from Backstage workflows. | Action appears in Backstage scaffolder backend; attestation created correctly; result shown to user | 2 | Pending |
| 10.4 | `skillmeat:bom-generate` scaffolder action | New scaffolder action to trigger BOM generation. | Action appears in scaffolder backend; parameters respected; BOM generated successfully | 1 | Pending |
| 10.5 | Scaffolder action registration and tests | Register actions in the existing backend module and add automated tests. | Actions registered correctly; callable from Backstage scaffolder; backend tests pass | 1 | Pending |

### Key Design Notes

- **No Separate Storage**: All data comes from SkillMeat APIs; do not duplicate BOM state in Backstage.
- **Backend Only**: Keep this phase inside the existing `backstage-plugin-scaffolder-backend` module.
- **Future Frontend Follow-On**: Track Backstage EntityPage UI in a separate plan or follow-up phase.
- **Error Handling**: Return user-friendly action errors if API calls fail; support fallback messaging.

### Deliverables

1. **Code**:
   - Extended `skillmeat/api/routers/idp_integration.py` — BOM payload endpoint
   - `plugins/backstage-plugin-scaffolder-backend/src/actions/skillmeat-attest.ts` — Attest scaffolder action
   - `plugins/backstage-plugin-scaffolder-backend/src/actions/skillmeat-bom-generate.ts` — BOM generate scaffolder action
   - `plugins/backstage-plugin-scaffolder-backend/src/index.ts` — Action registration updates

2. **Tests**:
   - `skillmeat/api/tests/test_bom_card_endpoint.py` — API endpoint tests
   - `plugins/backstage-plugin-scaffolder-backend/src/__tests__/skillmeat-actions.test.ts` — Action tests

### Exit Criteria

- [ ] `/integrations/idp/bom-card/{project_id}` endpoint implemented and tested
- [ ] Stable backend payload contract defined for future frontend consumers
- [ ] `skillmeat:attest` scaffolder action functional
- [ ] `skillmeat:bom-generate` scaffolder action functional
- [ ] Backend tests pass
- [ ] No separate BOM storage introduced in Backstage

---

## Integration Points

### From Phase 7 API
- Phase 9 hooks call activity-history, BOM, and attestation endpoints
- Phase 10 backend integration consumes the IDP payload endpoint and write endpoints

### Between Phase 9 and 10
- ProvenanceTab may link out to external platform integrations later, but no direct Backstage frontend coupling is required in this plan version
- The Backstage backend payload contract should stay aligned with the web app’s provenance data model

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Users confuse provenance activity with version history | Keep the new UI explicitly labeled and preserve the existing History tab |
| Web component performance with large BOMs | Use filtering, pagination, and lightweight rendering patterns for long lists |
| Backstage scope expands into frontend work mid-phase | Keep frontend EntityPage card explicitly out of scope and track separately |
| Payload contract churn breaks downstream consumers | Define stable payload contract and version changes conservatively |

---

## Success Metrics

- **Web Component Tests**: >= 80% code coverage
- **Accessibility**: WCAG 2.1 AA compliance verified
- **Performance**: ProvenanceTab renders in < 200ms for typical payloads
- **Backend Payload**: IDP payload endpoint responds in < 500ms for typical projects
- **API Adoption**: New provenance surfaces use Phase 7 API/contracts exclusively

---

## Next Steps (Gate to Phase 11)

1. ✅ Phase 9-10 exit criteria verified
2. ✅ Web provenance components tested and accessible
3. ✅ Backstage backend integration tested
4. ✅ Any future Backstage frontend card tracked separately
5. ✅ Phase 11 can begin with all current-scope surfaces stable

---

## References

- **PRD**: `/docs/project_plans/PRDs/features/skillbom-attestation-v1.md` § FR-12, FR-13, FR-14
- **Main Plan**: `/docs/project_plans/implementation_plans/features/skillbom-attestation-v1.md`
- **Web CLAUDE.md**: `skillmeat/web/CLAUDE.md`
- **Component Patterns**: `.claude/context/key-context/component-patterns.md`
- **Testing Patterns**: `.claude/context/key-context/testing-patterns.md`
