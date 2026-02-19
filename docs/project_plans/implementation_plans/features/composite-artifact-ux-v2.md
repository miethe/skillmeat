---
title: 'Implementation Plan: Composite Artifact UX v2'
description: Phased implementation plan for making composite artifacts (Plugins) first-class
  citizens in the SkillMeat web app with full type-system integration, marketplace
  discovery, CRUD API, and collection management UI.
audience:
- ai-agents
- developers
tags:
- implementation
- planning
- phases
- composite-artifacts
- plugins
- ux
- api
- frontend
created: 2026-02-19
updated: '2026-02-19'
category: product-planning
status: in-progress
schema_version: 2
doc_type: implementation_plan
feature_slug: composite-artifact-ux-v2
feature_version: v2
prd_ref: /docs/project_plans/PRDs/features/composite-artifact-ux-v2.md
plan_ref: null
scope: Add 'composite' to frontend type system, wire marketplace discovery and import
  flows, implement CRUD API endpoints, build collection UI for plugin management,
  integrate with CLI.
effort_estimate: 41 story points across 5 phases
architecture_summary: Phased rollout layering type-system integration → marketplace
  → import flow → collection UI → CLI. All work builds on completed v1 infrastructure
  (CompositeService, CompositeMembershipRepository, ORM models, relationships API).
related_documents:
- /docs/project_plans/PRDs/features/composite-artifact-ux-v2.md
- /docs/project_plans/implementation_plans/features/composite-artifact-infrastructure-v1.md
- /docs/project_plans/implementation_plans/features/composite-artifact-ux-v2/ui-specs.md
owner: null
contributors: []
priority: high
risk_level: medium
milestone: null
commit_refs: []
pr_refs: []
files_affected: []
---
# Implementation Plan: Composite Artifact UX v2

**Plan ID**: `CUX-IMPL-2026-02-19`
**Date**: 2026-02-19
**Author**: Claude (Haiku 4.5) — Implementation Planner
**Related Documents**:
- **PRD**: `/docs/project_plans/PRDs/features/composite-artifact-ux-v2.md`
- **UI Specs**: `/docs/project_plans/implementation_plans/features/composite-artifact-ux-v2/ui-specs.md`
- **v1 Plan**: `/docs/project_plans/implementation_plans/features/composite-artifact-infrastructure-v1.md`
- **Design Spec**: `/docs/project_plans/design-specs/composite-artifact-infrastructure.md`

**Complexity**: Large (L)
**Total Estimated Effort**: 41 story points across 5 phases
**Target Timeline**: 20-25 days (4-5 weeks at 1 FTE backend + 1 FTE frontend)

---

## Executive Summary

v1 delivered the relational database infrastructure, discovery heuristics, and read-only UI tabs for composite artifacts. v2 makes Plugins genuinely first-class across the entire SkillMeat ecosystem by integrating them into the frontend type system, enabling marketplace discovery and import, exposing CRUD endpoints for API consumers, and building a comprehensive collection UI for plugin creation and management. No new business logic is needed — this work is purely surface-level wiring and UI implementation building on the v1 foundation.

**Key outcomes**:
1. **Phase 1** adds `'composite'` to the frontend `ArtifactType` union, `ARTIFACT_TYPES` config, ID parsing/formatting, and platform defaults so plugins are type-safe throughout.
2. **Phase 2** enables marketplace browsing of plugins with type filters and member-count badges, surfacing plugin classification on source detail pages.
3. **Phase 3** wires pre-built `CompositePreview` and `ConflictResolutionDialog` components into the marketplace and collection import flows.
4. **Phase 4** implements a comprehensive collection UI with plugin cards, creation flow, and member management (add/remove/reorder).
5. **Phase 5** adds CLI commands to list and create plugins.

**Success is measured by**: Type-safe composite support throughout the frontend, plugins discoverable and importable from the marketplace with a clear breakdown dialog, full plugin CRUD API, and complete collection management UI.

---

## Implementation Strategy

### Architecture Sequence

Following MeatyPrompts layered architecture:

1. **Type System Layer** (Phase 1) — Frontend type union, config, platform defaults
2. **API Layer** (Phase 1) — CRUD routers wired to existing CompositeService
3. **Marketplace Layer** (Phase 2) — Type filtering, plugin detection, member badges
4. **Import Orchestration** (Phase 3) — CompositePreview and ConflictResolutionDialog wiring
5. **UI Collection Layer** (Phase 4) — Plugin cards, creation form, detail/edit, member management
6. **CLI Layer** (Phase 5) — List and create commands
7. **Testing Layer** (All phases) — Unit, integration, E2E coverage >80%
8. **Documentation Layer** (All phases) — JSDoc, OpenAPI, CHANGELOG

### Parallel Work Opportunities

- **Phase 1 & 2**: While type system integrates, marketplace discovery can be implemented in parallel (both depend on v1 infrastructure being stable).
- **Phase 3 & 4**: UI implementation can start as soon as API contract is stable; import flow design can proceed in parallel with Phase 2 completion.
- **Phase 5**: CLI can be implemented in parallel with Phase 4 once the API endpoints are finalized.

### Critical Path

1. **Phase 1** (Type system + CRUD router) → unblocks all downstream work
2. **Phase 2** (Marketplace discovery) → required before Phase 3 import wiring
3. **Phase 3** (Import flow wiring) → required before Phase 4 collection UI
4. **Phase 4** (Collection UI) → depends on Phase 1 types + Phase 3 import working
5. **Phase 5** (CLI) → can be parallelized; depends on Phase 1 types + CRUD API

---

## Phase Breakdown

### Phase 1: Type System + Backend CRUD

**Duration**: 3-4 days
**Dependencies**: v1 infrastructure complete (CompositeService, CompositeMembershipRepository exist and are functional)
**Assigned Subagent(s)**: frontend-developer, python-backend-engineer

**Overview**: Make plugins type-safe by adding `'composite'` to the frontend type system and wire CRUD endpoints to the existing backend service layer. This unblocks all downstream work.

**Key Deliverables**:
- `'composite'` added to `ArtifactType` union in `skillmeat/web/types/artifact.ts`
- `composite` entry in `ARTIFACT_TYPES` config with icon (`Blocks`), label (`Plugin`), color (`text-indigo-500`), and form schema
- Update `parseArtifactId()` and `formatArtifactId()` to handle `'composite'` type
- Add `'composite'` to platform defaults in `skillmeat/web/lib/constants/platform-defaults.ts`
- **New router**: `skillmeat/api/routers/composites.py` with 6 endpoints (CRUD + member management)
- Pydantic request/response schemas for all endpoints
- Regenerate `openapi.json`
- Unit and integration tests for all new endpoints
- Update `skillmeat/core/services/composite_service.py` if any methods are missing

See detailed phase breakdown: [Phase 1: Type System + Backend CRUD](./composite-artifact-ux-v2/phase-1-type-system.md)

**Phase 1 Quality Gates**:
- [ ] `pnpm type-check` passes with zero new TypeScript errors
- [ ] `parseArtifactId('composite:my-plugin')` returns `{type: 'composite', name: 'my-plugin'}`
- [ ] All 6 CRUD endpoints return correct status codes (201/200/204)
- [ ] Integration tests for all endpoints pass
- [ ] `openapi.json` regenerated and committed
- [ ] No regression in existing artifact type paths

---

### Phase 2: Marketplace Plugin Discovery

**Duration**: 2-3 days
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: ui-engineer-enhanced, python-backend-engineer

**Overview**: Surface plugins in marketplace browsing with type filters, member-count badges, and source classification. Backend marketplace listing already returns `artifact_type`; frontend just needs to filter and display.

**Key Deliverables**:
- Add `composite` option to marketplace type filter UI (`ArtifactTypeFilter` component)
- Verify marketplace listing endpoint supports `artifact_type=composite` query parameter
- Embed or fetch `member_count` and `child_types` in marketplace listing response (avoid N+1 fetches)
- Plugin card in marketplace grid: member count badge + type breakdown (e.g., "2 skills, 1 command")
- Marketplace source detail: "Plugin" badge when source is detected as composite type
- Unit tests for filter logic and plugin detection

See detailed phase breakdown: [Phase 2: Marketplace Plugin Discovery](./composite-artifact-ux-v2/phase-2-marketplace.md)

**Phase 2 Quality Gates**:
- [ ] Marketplace browse filters to plugins when `composite` selected
- [ ] Plugin cards show correct member counts
- [ ] Marketplace source detail shows "Plugin" badge for qualifying repos
- [ ] Marketplace listing query accepts `artifact_type=composite` filter
- [ ] No N+1 fetches for member data

---

### Phase 3: Import Flow Wiring

**Duration**: 2-3 days
**Dependencies**: Phase 1 complete, Phase 2 complete
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer

**Overview**: Connect pre-built components (`CompositePreview`, `ConflictResolutionDialog`, `useArtifactAssociations` hook) into the marketplace and collection import flows.

**Key Deliverables**:
- Wire `CompositePreview` component into marketplace import dialog (conditionally rendered when `source.artifact_type === 'composite'`)
- Wire `CompositePreview` into collection `skillmeat add` flow
- Wire `ConflictResolutionDialog` for hash-mismatch conflict resolution
- Ensure import calls correct backend endpoint (transaction for atomic child + composite creation)
- Add `useMutation` hooks with TanStack Query and error rollback
- E2E test for marketplace import flow (preview → confirm → collection updated)
- E2E test for conflict resolution dialog

See detailed phase breakdown: [Phase 3: Import Flow Wiring](./composite-artifact-ux-v2/phase-3-import-flow.md)

**Phase 3 Quality Gates**:
- [ ] CompositePreview renders in import modal for composite sources
- [ ] ConflictResolutionDialog appears on hash mismatch
- [ ] Import transaction creates composite + children atomically
- [ ] Mutation hooks handle errors and rollback optimistic updates
- [ ] Core import flow E2E test passes

---

### Phase 4: Collection Plugin Management UI

**Duration**: 3-4 days
**Dependencies**: Phase 1 complete, Phase 3 complete (for import wiring)
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer

**Overview**: Build comprehensive collection UI for plugin browsing, creation, and member management. Most components (`PluginMemberIcons`, `CreatePluginDialog`, `PluginMembersTab`, `MemberSearchInput`, `MemberList`) are specified in UI specs and require implementation from scratch (not wrapped from existing atomic patterns).

**Key Deliverables**:
- Plugin card variant in collection grid (icon, member-type chips, member count badge)
- "Create Plugin" button in collection toolbar
- Bulk selection "Create Plugin" action (when 2+ artifacts selected)
- `CreatePluginDialog`: form with name, description, tags, and pre-populated/editable member list
- `MemberSearchInput` component for adding artifacts to a plugin
- `MemberList` component with drag-to-reorder and remove actions
- Plugin detail page with "Members" tab (add/remove/reorder members)
- `PluginMembersTab` component with member table and actions menu
- `useCreateComposite`, `useUpdateComposite`, `useDeleteComposite`, `useManageCompositeMembers` mutation hooks
- Accessibility audit: all new UI meets WCAG 2.1 AA (keyboard nav, ARIA labels, screen reader support)
- E2E test for plugin creation from selection, add member, remove member

See detailed phase breakdown: [Phase 4: Collection Plugin Management](./composite-artifact-ux-v2/phase-4-collection-ui.md)

**Phase 4 Quality Gates**:
- [ ] Plugin card renders in collection grid with correct styling and member info
- [ ] Plugin creation form creates composite via `POST /api/v1/composites` and updates collection
- [ ] Member add/remove/reorder updates call correct endpoints
- [ ] Plugin detail view shows all members with edit capabilities
- [ ] Keyboard navigation works (Tab, Enter, Escape, Arrow keys)
- [ ] Screen readers announce plugin info correctly
- [ ] E2E test passes: create → add → remove → verify in collection

---

### Phase 5: CLI Integration + Polish

**Duration**: 1-2 days
**Dependencies**: Phase 1 complete (CRUD API), Phase 4 complete (collection UI reference)
**Assigned Subagent(s)**: python-backend-engineer

**Overview**: Extend CLI to list and create plugins, completing the first-class artifact experience at the command line.

**Key Deliverables**:
- Update `skillmeat list` command to include composite artifacts in output (labeled with type)
- Implement `skillmeat composite create <name> [artifact-ids...]` Click command
- CLI integration tests for both commands
- Update `skillmeat --help` output
- CHANGELOG entry documenting v2 feature additions

See detailed phase breakdown: [Phase 5: CLI Integration](./composite-artifact-ux-v2/phase-5-cli.md)

**Phase 5 Quality Gates**:
- [ ] `skillmeat list` output includes composite artifacts
- [ ] `skillmeat composite create my-plugin skill:canvas command:git-commit` creates composite
- [ ] CLI integration tests pass
- [ ] `--help` output includes new commands

---

## Task Breakdown (Consolidated View)

### Phase 1: Type System + Backend CRUD

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| CUX-P1-01 | Type Union Extension | Add `'composite'` to `ArtifactType` union in `types/artifact.ts` | Union includes `'composite'`; all switch statements updated | 1 pt | frontend-developer | None |
| CUX-P1-02 | ARTIFACT_TYPES Config | Add `composite` entry with icon, label, color, form schema | Config entry accessible; `getArtifactTypeConfig('composite')` returns valid config | 1 pt | frontend-developer | CUX-P1-01 |
| CUX-P1-03 | ID Parsing & Formatting | Update `parseArtifactId()` and `formatArtifactId()` for composite | `parseArtifactId('composite:foo')` returns `{type:'composite',name:'foo'}`; no null returns | 1 pt | frontend-developer | CUX-P1-01 |
| CUX-P1-04 | Platform Defaults | Add `'composite'` to platform defaults constant | Composite participates in platform filtering; no TS errors | 1 pt | frontend-developer | CUX-P1-01 |
| CUX-P1-05 | Verify CompositeService | Check `CompositeService` has `create_composite`, `update_composite`, `delete_composite` methods; implement if missing | All 3 methods exist and are tested | 1 pt | python-backend-engineer | None |
| CUX-P1-06 | Verify Position Column | Check `CompositeMembership` has `position` column for ordering; add if missing | `position` column exists, nullable int, accessible via repo | 1 pt | python-backend-engineer | None |
| CUX-P1-07 | New Router: composites.py | Create `/api/routers/composites.py` with 6 endpoints | Router file created, endpoints registered in main app | 2 pts | python-backend-engineer | CUX-P1-05, CUX-P1-06 |
| CUX-P1-08 | POST /api/v1/composites | Create composite with initial member list | 201 response; composite + memberships created in DB | 2 pts | python-backend-engineer | CUX-P1-07 |
| CUX-P1-09 | PUT /api/v1/composites/{id} | Update composite metadata (name, description) | 200 response; composite updated in DB | 1 pt | python-backend-engineer | CUX-P1-07 |
| CUX-P1-10 | DELETE /api/v1/composites/{id} | Delete composite; cascade option unlinks members (default) | 204 response; composite deleted; children remain unless cascade specified | 1 pt | python-backend-engineer | CUX-P1-07 |
| CUX-P1-11 | POST /api/v1/composites/{id}/members | Add member to composite | 201 response; membership created with correct position | 1 pt | python-backend-engineer | CUX-P1-07 |
| CUX-P1-12 | DELETE /api/v1/composites/{id}/members/{member_id} | Remove member from composite | 204 response; membership deleted | 1 pt | python-backend-engineer | CUX-P1-07 |
| CUX-P1-13 | PATCH /api/v1/composites/{id}/members | Reorder members (accepts array of `{artifact_id, position}`) | 200 response; member positions updated | 1 pt | python-backend-engineer | CUX-P1-07 |
| CUX-P1-14 | Pydantic Schemas | Create request/response schemas for all endpoints | Schemas validate correctly; OpenAPI docs generated | 1 pt | python-backend-engineer | CUX-P1-07 |
| CUX-P1-15 | Regenerate OpenAPI | Run FastAPI schema generation; commit updated `openapi.json` | `openapi.json` includes all 6 new endpoints with correct schemas | 1 pt | python-backend-engineer | CUX-P1-14 |
| CUX-P1-16 | Integration Tests | Test all 6 endpoints (happy path, error cases, status codes) | All endpoint tests pass; >80% coverage | 2 pts | python-backend-engineer | CUX-P1-15 |

**Phase 1 Total**: 18 story points

---

### Phase 2: Marketplace Plugin Discovery

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| CUX-P2-01 | Type Filter UI Extension | Add `composite` option to marketplace `ArtifactTypeFilter` | Filter includes `composite` option; filtering works | 1 pt | ui-engineer-enhanced | CUX-P1-02 |
| CUX-P2-02 | Backend Query Parameter | Verify marketplace listing endpoint accepts `artifact_type=composite` query param | Backend listing query accepts filter; returns only composite-type sources | 1 pt | python-backend-engineer | None |
| CUX-P2-03 | Member Data Fetch | Embed or fetch `member_count` and `child_types` in marketplace listing response | Marketplace listing includes member metadata; no N+1 fetches | 1 pt | python-backend-engineer | CUX-P2-02 |
| CUX-P2-04 | Plugin Card Badge | Add member count badge to marketplace plugin card ("5 artifacts") | Badge displays correct count; distinct styling from atomic cards | 2 pts | ui-engineer-enhanced | CUX-P2-03 |
| CUX-P2-05 | Member Type Breakdown | Display member type breakdown on marketplace plugin cards ("2 skills, 1 command") | Breakdown displays correctly; responsive on mobile (icons + counts) | 2 pts | ui-engineer-enhanced | CUX-P2-03 |
| CUX-P2-06 | Source Classification Badge | Surface "Plugin" badge on marketplace source detail when composite detected | Badge appears for qualifying repos; uses correct styling | 1 pt | ui-engineer-enhanced | CUX-P2-02 |
| CUX-P2-07 | Unit Tests | Test plugin detection logic, filtering, badge rendering | All tests pass; >80% coverage | 1 pt | frontend-developer | CUX-P2-06 |

**Phase 2 Total**: 9 story points

---

### Phase 3: Import Flow Wiring

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| CUX-P3-01 | Wire CompositePreview (Marketplace) | Import `CompositePreview` into marketplace import dialog; conditionally render when composite detected | Preview renders for composite sources; shows correct breakdown | 2 pts | ui-engineer-enhanced | CUX-P1-01, CUX-P2-06 |
| CUX-P3-02 | Wire CompositePreview (Collection) | Import `CompositePreview` into collection `skillmeat add` flow | Preview available in add flow; conditional on source type | 1 pt | frontend-developer | CUX-P3-01 |
| CUX-P3-03 | Wire ConflictResolutionDialog | Trigger `ConflictResolutionDialog` on hash mismatch; connect to backend API | Dialog appears on conflict; resolution options work | 2 pts | frontend-developer | CUX-P1-01 |
| CUX-P3-04 | Import Mutation Hooks | Create `useMutation` hooks with TanStack Query for composite import; implement error rollback | Hooks handle loading/error/success; optimistic updates roll back on error | 2 pts | frontend-developer | CUX-P1-08 |
| CUX-P3-05 | Transaction Verification | Ensure import calls correct endpoint; create composite + children in single transaction | Import succeeds atomically; partial failure rolls back | 1 pt | python-backend-engineer | CUX-P1-08 |
| CUX-P3-06 | Marketplace Import E2E | Playwright E2E test for marketplace plugin import flow | Test passes: filter → view → preview → confirm → collection updated | 2 pts | ui-engineer-enhanced | CUX-P3-01 |
| CUX-P3-07 | Conflict Resolution E2E | Playwright E2E test for conflict resolution during import | Test passes: conflict detected → resolve → import succeeds | 2 pts | frontend-developer | CUX-P3-03 |

**Phase 3 Total**: 12 story points

---

### Phase 4: Collection Plugin Management UI

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| CUX-P4-01 | PluginMemberIcons Component | Build component to display type icons for plugin members (up to 5, with +N overflow) | Component renders correctly; responsive sizing; accessibility | 1 pt | ui-engineer-enhanced | CUX-P1-02 |
| CUX-P4-02 | Plugin Card Variant | Extend `ArtifactBrowseCard` for plugin display (icon, name, member icons, count badge) | Plugin cards render in collection grid with correct styling | 2 pts | ui-engineer-enhanced | CUX-P4-01 |
| CUX-P4-03 | MemberSearchInput Component | Build searchable artifact picker for adding members to plugins | Input filters collection artifacts; debounced search; excludes already-added | 2 pts | frontend-developer | CUX-P1-01 |
| CUX-P4-04 | MemberList Component | Build sortable member list with drag-to-reorder and remove actions | List renders with drag handles; keyboard arrow keys work; a11y compliant | 2 pts | ui-engineer-enhanced | CUX-P4-03 |
| CUX-P4-05 | CreatePluginDialog | Dialog form: name, description, tags, pre-populated members (from bulk select or empty) | Dialog creates plugin via `POST /api/v1/composites`; validates; handles errors | 3 pts | ui-engineer-enhanced | CUX-P4-03, CUX-P4-04 |
| CUX-P4-06 | Create Plugin Button | Add "New Plugin" button to collection toolbar and bulk action bar | Button visible; opens CreatePluginDialog with correct context | 1 pt | ui-engineer-enhanced | CUX-P4-05 |
| CUX-P4-07 | PluginMembersTab Component | Detail page members tab: member table with add/remove/reorder/actions menu | Tab shows members with edit capabilities; actions work | 2 pts | ui-engineer-enhanced | CUX-P4-04 |
| CUX-P4-08 | Member Actions Menu | Menu for each member: View Details, Deploy, Remove from Plugin | Menu renders; actions work; "Remove" shows destructive styling | 1 pt | ui-engineer-enhanced | CUX-P4-07 |
| CUX-P4-09 | Plugin Detail Modal | Extend `BaseArtifactModal` for plugins with Members tab + existing tabs | Detail view shows plugin info and member management interface | 1 pt | ui-engineer-enhanced | CUX-P4-07 |
| CUX-P4-10 | Mutation Hooks | Create `useCreateComposite`, `useUpdateComposite`, `useDeleteComposite`, `useManageCompositeMembers` | All hooks work with TanStack Query; handle loading/error/success | 2 pts | frontend-developer | CUX-P1-08 |
| CUX-P4-11 | Accessibility Audit | WCAG 2.1 AA compliance for all plugin UI components | axe checks pass; keyboard nav works; screen reader support | 2 pts | ui-engineer-enhanced | CUX-P4-10 |
| CUX-P4-12 | Collection Plugin E2E | Playwright E2E test: create plugin from selection, add member, remove member | Test passes: create → add → remove → verify in collection | 2 pts | frontend-developer | CUX-P4-10 |

**Phase 4 Total**: 21 story points

---

### Phase 5: CLI Integration + Polish

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| CUX-P5-01 | CLI List Composites | Update `skillmeat list` to include composite artifacts | Output includes composites; correctly labeled with type | 1 pt | python-backend-engineer | CUX-P1-05 |
| CUX-P5-02 | CLI Create Composite | Implement `skillmeat composite create <name> [artifact-ids...]` Click command | Command creates composite via service; exits 0; appears in list | 1 pt | python-backend-engineer | CUX-P1-05 |
| CUX-P5-03 | CLI Integration Tests | Test both new commands (happy path, error cases) | All tests pass; commands work correctly | 1 pt | python-backend-engineer | CUX-P5-02 |
| CUX-P5-04 | Help Output | Update `skillmeat --help` to document new commands | Help text includes `list` composite support and `composite create` | 1 pt | python-backend-engineer | CUX-P5-02 |
| CUX-P5-05 | CHANGELOG Entry | Document v2 feature additions in CHANGELOG | Entry covers all 5 phases, breaking changes (if any), migration notes | 1 pt | python-backend-engineer | None |

**Phase 5 Total**: 5 story points

---

## Story ID Cross-Reference

Mapping from PRD requirements to implementation task IDs:

| PRD Req ID | Implementation Tasks |
|-----------|---------------------|
| FR-1 | CUX-P1-01 |
| FR-2 | CUX-P1-02 |
| FR-3 | CUX-P1-03 |
| FR-4 | CUX-P1-04 |
| FR-5 | CUX-P2-01, CUX-P2-02 |
| FR-6 | CUX-P2-04, CUX-P2-05 |
| FR-7 | CUX-P2-06 |
| FR-8 | CUX-P3-01 |
| FR-9 | CUX-P3-03 |
| FR-10 | CUX-P3-05 |
| FR-11 | CUX-P1-08 |
| FR-12 | CUX-P1-09 |
| FR-13 | CUX-P1-10 |
| FR-14 | CUX-P1-11 |
| FR-15 | CUX-P1-12 |
| FR-16 | CUX-P1-13 |
| FR-17 | CUX-P4-02 |
| FR-18 | CUX-P4-05, CUX-P4-06 |
| FR-19 | CUX-P4-07, CUX-P4-08, CUX-P4-09 |
| FR-20 | CUX-P5-01 |
| FR-21 | CUX-P5-02 |

---

## Overall Summary

| Phase | Title | Duration | Effort | Key Deliverables |
|-------|-------|----------|--------|------------------|
| 1 | Type System + Backend CRUD | 3-4 days | 18 pts | `'composite'` in ArtifactType, ARTIFACT_TYPES, ID parsing; 6 CRUD endpoints wired to CompositeService |
| 2 | Marketplace Plugin Discovery | 2-3 days | 9 pts | Plugin type filter, member count badges, source classification |
| 3 | Import Flow Wiring | 2-3 days | 12 pts | CompositePreview and ConflictResolutionDialog integrated into import flows |
| 4 | Collection Plugin Management | 3-4 days | 21 pts | Plugin cards, creation form, member management UI, mutation hooks |
| 5 | CLI Integration | 1-2 days | 5 pts | `skillmeat list` with composites, `skillmeat composite create` command |
| **Total** | **Composite Artifact UX v2** | **12-17 days** | **65 pts** | **Full first-class plugin support across type system, marketplace, API, collection UI, CLI** |

---

## Dependency Graph

```
Phase 1: Type System + CRUD
├── CUX-P1-01 (Type Union)
├── CUX-P1-02 (ARTIFACT_TYPES config)
├── CUX-P1-03 (ID parsing)
├── CUX-P1-04 (Platform defaults)
├── CUX-P1-05 (Verify CompositeService)
├── CUX-P1-06 (Verify Position column)
└── CUX-P1-07+ (Router + endpoints)
    └── CUX-P1-16 (Integration tests)

Phase 2: Marketplace Discovery
├── CUX-P2-01 (Type filter UI) - depends on CUX-P1-02
├── CUX-P2-02 (Backend query param) - no dependency
├── CUX-P2-03 (Member data) - depends on CUX-P2-02
├── CUX-P2-04+ (Plugin cards) - depends on CUX-P2-03
└── CUX-P2-07 (Unit tests) - depends on CUX-P2-06

Phase 3: Import Flow Wiring
├── CUX-P3-01 (Wire CompositePreview) - depends on CUX-P1-01, CUX-P2-06
├── CUX-P3-02 (CompositePreview in collection) - depends on CUX-P3-01
├── CUX-P3-03 (ConflictDialog) - depends on CUX-P1-01
├── CUX-P3-04 (Mutation hooks) - depends on CUX-P1-08
├── CUX-P3-05 (Transaction verify) - depends on CUX-P1-08
└── CUX-P3-06, CUX-P3-07 (E2E tests) - depends on CUX-P3-01, CUX-P3-03

Phase 4: Collection UI
├── CUX-P4-01 (PluginMemberIcons) - depends on CUX-P1-02
├── CUX-P4-02 (Plugin card) - depends on CUX-P4-01
├── CUX-P4-03+ (Form components) - depends on CUX-P1-01
├── CUX-P4-10 (Mutation hooks) - depends on CUX-P1-08
├── CUX-P4-11 (A11y audit) - depends on CUX-P4-10
└── CUX-P4-12 (E2E test) - depends on CUX-P4-10

Phase 5: CLI Integration
├── CUX-P5-01 (List composites) - depends on CUX-P1-05
├── CUX-P5-02 (Create composite) - depends on CUX-P1-05
└── CUX-P5-03+ (Tests + docs) - depends on CUX-P5-02
```

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Adding `'composite'` breaks exhaustive switch/match in existing components | High | Medium | Audit all TypeScript switch statements in Phase 1; type-check CI catches missed cases; PR review enforces exhaustiveness |
| `ARTIFACT_TYPES[type]` lookups fail if FR-1 and FR-2 not deployed atomically | High | Low | Deploy as single PR; `ARTIFACT_TYPES` config must include `composite` before runtime code uses it |
| CompositeService methods missing or incomplete | High | Medium | Verify methods exist in CUX-P1-05; if absent, implement as thin wrapper over CompositeMembershipRepository |
| Plugin card visually indistinguishable from atomic card | Medium | Medium | Use distinct icon (Blocks), indigo color, member-count badge; design review before merge |
| Import flow regression for atomic artifact imports | High | Low | Composite detection is conditional (`if (source.artifact_type === 'composite')`); atomic path unchanged; cover with existing import E2E tests |
| Position column migration required for reordering | Medium | Medium | Verify column exists in CUX-P1-06; if absent, lightweight Alembic migration in Phase 1 |
| Marketplace N+1 fetches for member data | Medium | Medium | Embed member metadata in listing response (CUX-P2-03) or add dedicated endpoint; avoid per-card associations call |
| UI component complexity scope creep | Medium | Medium | Follow UI specs exactly; define component contracts upfront; phased component delivery per Phase 4 task breakdown |

### Schedule Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| TypeScript changes block other work in Phase 1 | High | Low | Land Phase 1 as first PR; unblock other work before CRUD/UI PRs |
| Marketplace changes conflict with other marketplace work | Medium | Medium | Coordinate with other marketplace initiatives; Phase 2 is isolated to plugin type filtering |
| Import flow integration reveals missing v1 functionality | Medium | Low | v1 is marked complete; verify all dependencies functional before Phase 3 kickoff |
| Collection UI exceeds 21 points in Phase 4 | High | Medium | Break Phase 4 into detailed component tasks; delegate to ui-engineer-enhanced early; plan for overflow into Phase 4b if needed |
| CLI phase slips due to API contract changes | Low | Low | Phase 1 finalizes API contract; Phase 5 depends on stable contract |

---

## Key Files & Implementation References

### Frontend Type System
- `skillmeat/web/types/artifact.ts` — Extend `ArtifactType` union, `ARTIFACT_TYPES` registry
- `skillmeat/web/lib/constants/platform-defaults.ts` — Add `'composite'` to platform filtering

### Backend API & Services
- `skillmeat/core/services/composite_service.py` — Verify/implement create/update/delete methods
- `skillmeat/api/routers/composites.py` — NEW router with 6 endpoints (to be created)
- `skillmeat/api/schemas/` — Pydantic request/response schemas
- `skillmeat/cache/composite_repository.py` — Already has CRUD; verify position column support

### Marketplace
- `skillmeat/web/components/marketplace/MarketplaceFilters.tsx` — Extend type filter
- `skillmeat/web/components/marketplace/MarketplaceListingCard.tsx` — Extend for composite type
- `skillmeat/api/routers/marketplace.py` — Verify `artifact_type` parameter support

### Collection UI
- `skillmeat/web/components/collection/artifact-browse-card.tsx` — Extend for plugin variant
- `skillmeat/web/components/shared/artifact-type-tabs.tsx` — Extend for composite tab
- `skillmeat/web/components/entity/unified-entity-modal.tsx` — Base for plugin detail modal

### Import & Wiring
- `skillmeat/web/components/import/composite-preview.tsx` — Already built; wire in Phase 3
- `skillmeat/web/components/deployment/conflict-resolution-dialog.tsx` — Already built; wire in Phase 3
- `skillmeat/web/hooks/useArtifactAssociations.ts` — Already functional; extend with mutation hooks

### CLI
- `skillmeat/cli.py` — Update `list` command, add `composite create` group

### Testing
- `tests/test_composites_api.py` — Integration tests for CRUD endpoints
- `skillmeat/web/__tests__/` — Unit and component tests for UI components
- `skillmeat/web/tests/e2e/composites.spec.ts` — E2E tests for import and collection flows

---

## Parallelization Strategy

### Batch 1 (Phase 1 Foundation)
- **Tasks**: CUX-P1-01, CUX-P1-02, CUX-P1-03, CUX-P1-04 (Type system)
- **Agents**: `frontend-developer` (parallel)
- **Duration**: 1 day
- **Unblocks**: All downstream tasks

### Batch 2 (Phase 1 Backend Parallel with Batch 1)
- **Tasks**: CUX-P1-05, CUX-P1-06 (Verify service/position), CUX-P2-02 (Backend query)
- **Agents**: `python-backend-engineer` (parallel)
- **Duration**: 1 day
- **Can run simultaneously with Batch 1**

### Batch 3 (Phase 1 Router & Endpoints)
- **Tasks**: CUX-P1-07, CUX-P1-08, CUX-P1-09, CUX-P1-10, CUX-P1-11, CUX-P1-12, CUX-P1-13 (Endpoints)
- **Agents**: `python-backend-engineer` (distributed per endpoint)
- **Duration**: 2 days
- **Depends on**: Batch 2

### Batch 4 (Phase 1 Finalization)
- **Tasks**: CUX-P1-14, CUX-P1-15, CUX-P1-16 (Schemas, OpenAPI, tests)
- **Agents**: `python-backend-engineer`
- **Duration**: 1 day
- **Depends on**: Batch 3

### Batch 5 (Phase 2 Marketplace)
- **Tasks**: CUX-P2-01, CUX-P2-03, CUX-P2-04, CUX-P2-05, CUX-P2-06, CUX-P2-07
- **Agents**: `ui-engineer-enhanced`, `python-backend-engineer` (for CUX-P2-03)
- **Duration**: 2-3 days
- **Depends on**: Phase 1 complete, can start CUX-P2-02 in parallel with Phase 1

### Batch 6 (Phase 3 Import Wiring)
- **Tasks**: CUX-P3-01, CUX-P3-02, CUX-P3-03, CUX-P3-04, CUX-P3-05
- **Agents**: `ui-engineer-enhanced`, `frontend-developer`, `python-backend-engineer`
- **Duration**: 2-3 days
- **Depends on**: Phase 1 + 2 complete
- **Can parallelize**: Frontend UI wiring (CUX-P3-01, CUX-P3-02, CUX-P3-03, CUX-P3-04) while backend verification runs

### Batch 7 (Phase 3 E2E Tests)
- **Tasks**: CUX-P3-06, CUX-P3-07
- **Agents**: `ui-engineer-enhanced`, `frontend-developer`
- **Duration**: 1 day
- **Depends on**: Batch 6

### Batch 8 (Phase 4 UI Components - Foundation)
- **Tasks**: CUX-P4-01, CUX-P4-03, CUX-P4-04 (Components that don't depend on each other)
- **Agents**: `ui-engineer-enhanced`, `frontend-developer` (parallel)
- **Duration**: 2 days
- **Depends on**: Phase 1 type system

### Batch 9 (Phase 4 UI - Forms & Dialogs)
- **Tasks**: CUX-P4-05, CUX-P4-06, CUX-P4-02 (CreatePluginDialog, buttons, card variant)
- **Agents**: `ui-engineer-enhanced`
- **Duration**: 2 days
- **Depends on**: Batch 8

### Batch 10 (Phase 4 UI - Detail & Hooks)
- **Tasks**: CUX-P4-07, CUX-P4-08, CUX-P4-09, CUX-P4-10 (Detail page, mutation hooks)
- **Agents**: `ui-engineer-enhanced`, `frontend-developer` (parallel for hooks)
- **Duration**: 2 days
- **Depends on**: Batch 9

### Batch 11 (Phase 4 Polish & Testing)
- **Tasks**: CUX-P4-11, CUX-P4-12 (A11y audit, E2E tests)
- **Agents**: `ui-engineer-enhanced`, `frontend-developer`
- **Duration**: 1-2 days
- **Depends on**: Batch 10

### Batch 12 (Phase 5 CLI - Parallel with Phase 4 late stages)
- **Tasks**: CUX-P5-01, CUX-P5-02, CUX-P5-03, CUX-P5-04, CUX-P5-05
- **Agents**: `python-backend-engineer`
- **Duration**: 1-2 days
- **Depends on**: Phase 1 complete (can start while Phase 4 is in progress)
- **Can run in parallel with**: Batch 10 (Phase 4 mid-stage)

---

## Success Metrics

### Functional Success
- [ ] `ArtifactType` union includes `'composite'`; `pnpm type-check` passes with zero new errors
- [ ] `parseArtifactId('composite:my-plugin')` returns `{type: 'composite', name: 'my-plugin'}`
- [ ] Marketplace browse filters to plugins; plugin cards show member counts
- [ ] Import modal renders CompositePreview for composite sources
- [ ] ConflictResolutionDialog appears on hash mismatch during import
- [ ] Collection grid renders plugin cards with member icons and count badges
- [ ] Plugin creation form creates composite via `POST /api/v1/composites` and updates collection
- [ ] Plugin detail view shows members with add/remove/reorder capabilities
- [ ] `skillmeat list` includes composites; `skillmeat composite create` works

### Technical Success
- [ ] All 6 CRUD endpoints return correct status codes (201/200/204/404/400)
- [ ] `openapi.json` regenerated with all new endpoints and schemas
- [ ] Integration tests for all endpoints pass; >80% coverage
- [ ] E2E tests pass: marketplace import, conflict resolution, collection creation/management
- [ ] No regression in existing artifact type paths
- [ ] All new UI components pass WCAG 2.1 AA axe checks
- [ ] Keyboard navigation works (Tab, Enter, Escape, Arrow keys)
- [ ] Screen readers announce plugin info correctly

### Quality Success
- [ ] Zero P0/P1 regressions in existing tests
- [ ] Unit test coverage >80% for all new code
- [ ] `pnpm lint` passes with no new warnings
- [ ] Feature flag properly gates new behavior (if flag added)
- [ ] All acceptance criteria from PRD met

### Documentation Success
- [ ] `types/artifact.ts` JSDoc updated with `'composite'` type documentation
- [ ] New CRUD endpoints documented in `openapi.json` with examples
- [ ] `skillmeat --help` includes new CLI commands
- [ ] CHANGELOG updated with v2 additions and breaking changes (if any)

---

## Progress Tracking

See detailed progress tracking (one file per phase):
- `.claude/progress/composite-artifact-ux-v2/phase-1-progress.md`
- `.claude/progress/composite-artifact-ux-v2/phase-2-progress.md`
- `.claude/progress/composite-artifact-ux-v2/phase-3-progress.md`
- `.claude/progress/composite-artifact-ux-v2/phase-4-progress.md`
- `.claude/progress/composite-artifact-ux-v2/phase-5-progress.md`

These files will be created and updated as work progresses through each phase using the artifact-tracking CLI scripts.

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-02-19
**Status**: Draft (awaiting approval)
