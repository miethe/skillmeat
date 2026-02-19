---
schema_version: 2
doc_type: phase_plan
title: 'Phase 2: Marketplace Plugin Discovery'
status: inferred_complete
created: 2026-02-19
updated: 2026-02-19
feature_slug: composite-artifact-ux-v2
feature_version: v2
phase: 2
phase_title: Marketplace Plugin Discovery
prd_ref: /docs/project_plans/PRDs/features/composite-artifact-ux-v2.md
plan_ref: /docs/project_plans/implementation_plans/features/composite-artifact-ux-v2.md
entry_criteria:
- Phase 1 complete and merged (type system, CRUD API)
- Marketplace listing endpoint returns artifact_type field
exit_criteria:
- Marketplace browse filters to plugins; cards display member counts
- Source detail shows "Plugin" badge for qualifying repos
- No N+1 fetches for member data
- Unit tests pass
related_documents:
- /docs/project_plans/implementation_plans/features/composite-artifact-ux-v2.md
---
# Phase 2: Marketplace Plugin Discovery

**Duration**: 2-3 days
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: ui-engineer-enhanced, python-backend-engineer

## Overview

Surface plugins in the marketplace with type filters, member-count badges, and source classification. The backend marketplace listing already supports `artifact_type` filtering; frontend work is primarily UI integration and optional backend member metadata embedding.

## Tasks

### CUX-P2-01: Type Filter UI Extension
Add `composite` option to marketplace `ArtifactTypeFilter` component. Selection should filter marketplace to show only plugin-type sources.

**AC**: Filter includes `composite` option; filtering works; layout adjusts for 7 types
**Est**: 1 pt
**Subagent**: ui-engineer-enhanced

---

### CUX-P2-02: Backend Query Parameter
Verify marketplace listing endpoint (`GET /api/v1/marketplace` or similar) accepts `artifact_type=composite` query parameter. If not implemented, add support.

**AC**: Backend listing query accepts filter; returns only composite-type sources; 404 or empty if filter invalid
**Est**: 1 pt
**Subagent**: python-backend-engineer

---

### CUX-P2-03: Member Data Fetch
Embed `member_count` and `child_types` in marketplace listing response or create a dedicated endpoint to fetch member metadata. Goal: avoid N+1 fetches when rendering plugin cards.

**AC**: Marketplace listing includes member metadata for plugins; single request returns all needed data
**Est**: 1 pt
**Subagent**: python-backend-engineer

---

### CUX-P2-04: Plugin Card Badge
Add member count badge to marketplace plugin card (e.g., "5 artifacts"). Badge should be visually distinct and positioned correctly per UI specs.

**AC**: Badge displays correct count; distinct styling from atomic cards; responsive
**Est**: 2 pts
**Subagent**: ui-engineer-enhanced

---

### CUX-P2-05: Member Type Breakdown
Display member type breakdown on plugin cards (e.g., "2 skills, 1 command"). Responsive on mobile (icons + counts).

**AC**: Breakdown displays correctly; responsive; matches UI spec styling
**Est**: 2 pts
**Subagent**: ui-engineer-enhanced

---

### CUX-P2-06: Source Classification Badge
Surface "Plugin" badge on marketplace source detail when source is detected as composite type by backend heuristic.

**AC**: Badge appears for qualifying repos; correct styling; v1 source detection heuristic used
**Est**: 1 pt
**Subagent**: ui-engineer-enhanced

---

### CUX-P2-07: Unit Tests
Test plugin detection logic, filtering, and badge rendering.

**AC**: All tests pass; >80% coverage
**Est**: 1 pt
**Subagent**: frontend-developer

---

## Quality Gates

- [ ] Marketplace browse filters to plugins when `composite` selected
- [ ] Plugin cards show correct member counts
- [ ] Member type breakdown displays as per specs
- [ ] Source detail shows "Plugin" badge for qualifying repos
- [ ] No N+1 fetches (verify with network profiler)
- [ ] Unit tests pass
- [ ] Responsive on mobile/tablet

---

## Files Modified

### Frontend
- **Modified**: `skillmeat/web/components/marketplace/MarketplaceFilters.tsx` (extend type filter)
- **Modified**: `skillmeat/web/components/marketplace/MarketplaceListingCard.tsx` (extend for plugin variant)

### Backend
- **Modified**: `skillmeat/api/routers/marketplace.py` (verify/add query param support)
- **Modified**: Marketplace listing schema (add member metadata)

### Tests
- **Created**: `skillmeat/web/__tests__/components/marketplace/plugin-discovery.test.tsx`

---

**Phase 2 Version**: 1.0
**Last Updated**: 2026-02-19
