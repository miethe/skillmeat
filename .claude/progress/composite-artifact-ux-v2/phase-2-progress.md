---
type: progress
schema_version: 2
doc_type: progress
prd: composite-artifact-ux-v2
feature_slug: composite-artifact-ux-v2
phase: 2
title: Marketplace Plugin Discovery
status: completed
created: '2026-02-19'
updated: '2026-02-19'
prd_ref: docs/project_plans/PRDs/features/composite-artifact-ux-v2.md
plan_ref: docs/project_plans/implementation_plans/features/composite-artifact-ux-v2.md
overall_progress: 0
completion_estimate: on-track
total_tasks: 7
completed_tasks: 7
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- ui-engineer-enhanced
- python-backend-engineer
- frontend-developer
contributors: []
tasks:
- id: CUX-P2-01
  description: Add composite option to marketplace ArtifactTypeFilter component
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 1pt
  priority: high
- id: CUX-P2-02
  description: Verify/add artifact_type=composite query parameter support on marketplace
    listing endpoint
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 1pt
  priority: high
- id: CUX-P2-03
  description: Embed member_count and child_types in marketplace listing response
    to avoid N+1 fetches
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 1pt
  priority: high
- id: CUX-P2-04
  description: Add member count badge to marketplace plugin card (e.g., '5 artifacts')
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - CUX-P2-03
  estimated_effort: 2pt
  priority: medium
- id: CUX-P2-05
  description: Display member type breakdown on plugin cards (e.g., '2 skills, 1 command');
    responsive on mobile
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - CUX-P2-03
  estimated_effort: 2pt
  priority: medium
- id: CUX-P2-06
  description: Surface 'Plugin' badge on marketplace source detail for composite-type
    repos
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - CUX-P2-02
  estimated_effort: 1pt
  priority: medium
- id: CUX-P2-07
  description: Unit tests for plugin detection logic, filtering, and badge rendering
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - CUX-P2-04
  - CUX-P2-05
  - CUX-P2-06
  estimated_effort: 1pt
  priority: high
parallelization:
  batch_1:
  - CUX-P2-01
  - CUX-P2-02
  - CUX-P2-03
  batch_2:
  - CUX-P2-04
  - CUX-P2-05
  - CUX-P2-06
  batch_3:
  - CUX-P2-07
  critical_path:
  - CUX-P2-03
  - CUX-P2-04
  - CUX-P2-07
  estimated_total_time: 2-3 days
blockers: []
success_criteria:
- id: SC-P2-1
  description: Marketplace browse filters to plugins when composite selected
  status: pending
- id: SC-P2-2
  description: Plugin cards show correct member counts
  status: pending
- id: SC-P2-3
  description: Member type breakdown displays as per specs
  status: pending
- id: SC-P2-4
  description: Source detail shows 'Plugin' badge for qualifying repos
  status: pending
- id: SC-P2-5
  description: No N+1 fetches (verify with network profiler)
  status: pending
- id: SC-P2-6
  description: Unit tests pass
  status: pending
- id: SC-P2-7
  description: Responsive on mobile/tablet
  status: pending
files_modified: []
progress: 100
commit_refs:
- 9b4df27a
---
# Phase 2: Marketplace Plugin Discovery

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/composite-artifact-ux-v2/phase-2-progress.md -t CUX-P2-01 -s completed

python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/composite-artifact-ux-v2/phase-2-progress.md \
  --updates "CUX-P2-01:completed,CUX-P2-02:completed,CUX-P2-03:completed"
```

---

## Objective

Surface plugins in the marketplace with type filters, member-count badges, and source classification. The backend marketplace listing already supports `artifact_type` filtering; frontend work is primarily UI integration and optional backend member metadata embedding.

---

## Orchestration Quick Reference

### Batch 1 (No dependencies — launch immediately)

```
Task("ui-engineer-enhanced", "CUX-P2-01: Add composite option to marketplace ArtifactTypeFilter.
  File: skillmeat/web/components/marketplace/MarketplaceFilters.tsx
  Add composite filter option. Layout should adjust for 7 types.")

Task("python-backend-engineer", "CUX-P2-02: Verify marketplace listing accepts artifact_type=composite.
  File: skillmeat/api/routers/marketplace.py
  Add filter support if not implemented.")

Task("python-backend-engineer", "CUX-P2-03: Embed member_count and child_types in marketplace listing response.
  File: skillmeat/api/routers/marketplace.py, marketplace listing schema
  Avoid N+1 fetches for member data.")
```

### Batch 2 (After Batch 1)

```
Task("ui-engineer-enhanced", "CUX-P2-04 + CUX-P2-05: Plugin card badge and member type breakdown.
  File: skillmeat/web/components/marketplace/MarketplaceListingCard.tsx
  Add member count badge and type breakdown. Responsive on mobile.")

Task("ui-engineer-enhanced", "CUX-P2-06: Source classification 'Plugin' badge on source detail.
  File: skillmeat/web/components/marketplace/ (source detail component)
  Badge for qualifying repos using v1 detection heuristic.")
```

### Batch 3 (After Batch 2)

```
Task("frontend-developer", "CUX-P2-07: Unit tests for plugin detection, filtering, badge rendering.
  File: skillmeat/web/__tests__/components/marketplace/plugin-discovery.test.tsx
  >80% coverage target.")
```

---

## Known Gotchas

- Phase 1 must be complete before starting (type system and CRUD API required).
- Marketplace listing endpoint may already return `artifact_type` -- verify before implementing.
- Avoid N+1 fetches: embed member metadata in listing response, not via separate calls.
- Mobile responsiveness: icons + counts instead of full text on small screens.
