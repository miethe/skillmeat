---
type: progress
schema_version: 2
doc_type: progress
title: Skill-Contained Artifacts - All Phases Progress
prd: skill-contained-artifacts-v1
feature_slug: skill-contained-artifacts-v1
phase: 0
phase_title: All Phases Overview
status: pending
created: 2026-02-21
updated: '2026-02-22'
prd_ref: docs/project_plans/PRDs/features/skill-contained-artifacts-v1.md
plan_ref: docs/project_plans/implementation_plans/features/skill-contained-artifacts-v1.md
commit_refs: []
pr_refs: []
owners: []
contributors: []
tasks:
- id: TASK-1.1
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies: []
- id: TASK-1.2
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-1.1
- id: TASK-1.3
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-1.1
- id: TASK-2.1
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-1.2
  - TASK-1.3
- id: TASK-2.2
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-2.1
- id: TASK-2.3
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-2.1
- id: TASK-3.1
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-2.3
- id: TASK-3.2
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.1
- id: TASK-4.1
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - TASK-3.1
- id: TASK-4.2
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - TASK-3.1
- id: TASK-4.3
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - TASK-4.1
- id: TASK-4.4
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  - python-backend-engineer
  dependencies:
  - TASK-4.3
- id: TASK-5.1
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - TASK-3.1
- id: TASK-5.2
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - TASK-5.1
- id: TASK-5.3
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - TASK-5.2
- id: TASK-6.1
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.1
- id: TASK-6.2
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-6.1
- id: TASK-6.3
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-6.1
- id: TASK-7.1
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.1
  - TASK-6.1
- id: TASK-7.2
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - TASK-7.1
- id: TASK-7.3
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.1
- id: TASK-8.1
  status: pending
  assigned_to:
  - task-completion-validator
  dependencies:
  - TASK-5.3
  - TASK-4.4
  - TASK-6.3
  - TASK-7.2
- id: TASK-8.2
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-8.1
- id: TASK-8.3
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-8.2
parallelization:
  batch_1:
  - TASK-1.1
  batch_2:
  - TASK-1.2
  - TASK-1.3
  batch_3:
  - TASK-2.1
  batch_4:
  - TASK-2.2
  - TASK-2.3
  batch_5:
  - TASK-3.1
  batch_6:
  - TASK-3.2
  batch_7:
  - TASK-4.1
  - TASK-4.2
  - TASK-5.1
  - TASK-6.1
  - TASK-7.3
  batch_8:
  - TASK-4.3
  - TASK-5.2
  - TASK-6.2
  - TASK-7.1
  batch_9:
  - TASK-4.4
  - TASK-5.3
  - TASK-6.3
  - TASK-7.2
  batch_10:
  - TASK-8.1
  batch_11:
  - TASK-8.2
  batch_12:
  - TASK-8.3
total_tasks: 24
completed_tasks: 7
in_progress_tasks: 0
blocked_tasks: 0
progress: 29
---

# Skill-Contained Artifacts - Progress Tracker

## Phase Overview

| Phase | Title | Status | Tasks |
|-------|-------|--------|-------|
| 1 | Schema Extension | pending | TASK-1.1 through TASK-1.3 |
| 2 | Import Pipeline | pending | TASK-2.1 through TASK-2.3 |
| 3 | API Wiring | pending | TASK-3.1, TASK-3.2 |
| 4 | Marketplace UI | pending | TASK-4.1 through TASK-4.4 |
| 5 | Collection UI | pending | TASK-5.1 through TASK-5.3 |
| 6 | Deployment | pending | TASK-6.1 through TASK-6.3 |
| 7 | Version Tracking | pending | TASK-7.1 through TASK-7.3 |
| 8 | Testing & Validation | pending | TASK-8.1 through TASK-8.3 |

## Task Details

### Phase 1: Schema Extension

| ID | Task | Status | Agent | Dependencies |
|----|------|--------|-------|-------------|
| TASK-1.1 | Alembic migration — add "skill" to composite_type CHECK constraint | pending | data-layer-expert | - |
| TASK-1.2 | ORM model update — update CompositeArtifact CHECK constraint literal | pending | python-backend-engineer | TASK-1.1 |
| TASK-1.3 | CompositeService extension — add create_skill_composite() method | pending | python-backend-engineer | TASK-1.1 |

**TASK-1.1 (Alembic migration)**: Add `"skill"` to `check_composite_artifact_type` CHECK constraint using `batch_alter_table` for SQLite compatibility. DROP + re-create pattern. Exit: `alembic upgrade head` and `alembic downgrade -1` both succeed on a DB with existing plugin rows; no existing rows affected. (2 pts)

**TASK-1.2 (ORM model update)**: Update `CompositeArtifact.__table_args__` CHECK constraint literal and model docstring in `skillmeat/cache/models.py` to reflect `('plugin', 'stack', 'suite', 'skill')`. Existing plugin tests still pass. (0.5 pts)

**TASK-1.3 (CompositeService extension)**: Add `create_skill_composite(skill_artifact, embedded_list)` method to `CompositeService`. Creates a `CompositeArtifact` row (`composite_type="skill"`, `metadata_json={"artifact_uuid": skill_uuid}`) and stubs member creation. Unit test verifies row fields. (1 pt)

---

### Phase 2: Import Pipeline Extension

| ID | Task | Status | Agent | Dependencies |
|----|------|--------|-------|-------------|
| TASK-2.1 | Dedup logic in CompositeService | pending | python-backend-engineer | TASK-1.2, TASK-1.3 |
| TASK-2.2 | CompositeMembership creation | pending | python-backend-engineer | TASK-2.1 |
| TASK-2.3 | Atomic transaction wiring in importer.py | pending | python-backend-engineer | TASK-2.1 |

**TASK-2.1 (Dedup logic in CompositeService)**: Complete `create_skill_composite()`: for each `DetectedArtifact` in `embedded_list`, check collection for existing `Artifact` by content hash; reuse UUID if found, else create new `Artifact` row. Integration test: import two skills sharing a command — command `Artifact` row count stays at 1. (2 pts)

**TASK-2.2 (CompositeMembership creation)**: After hash dedup, create `CompositeMembership` row linking the `CompositeArtifact` to each child `Artifact` UUID. Use existing `unique(collection_id, composite_id, child_artifact_uuid)` index for idempotency. Re-import does not create duplicate membership rows. (1 pt)

**TASK-2.3 (Atomic transaction wiring in importer.py)**: Extend `importer.py`: after skill `Artifact` row committed, call `create_skill_composite()` inside the same `Session.begin()` block. Any exception triggers full rollback. Guard with `SKILL_CONTAINED_ARTIFACTS_ENABLED` feature flag. (2 pts)

---

### Phase 3: API Wiring

| ID | Task | Status | Agent | Dependencies |
|----|------|--------|-------|-------------|
| TASK-3.1 | Associations router fix — resolve skill UUID to CompositeArtifact | pending | python-backend-engineer | TASK-2.3 |
| TASK-3.2 | API integration tests | pending | python-backend-engineer | TASK-3.1 |

**TASK-3.1 (Associations router fix)**: Update `GET /api/v1/artifacts/{artifact_id}/associations` in `skillmeat/api/routers/artifacts.py`: when artifact is a skill, look up companion `CompositeArtifact` by `metadata_json->>'artifact_uuid' = artifact_id`, then query `CompositeMembership` rows. Return existing `AssociationsDTO` (no schema change). (1 pt)

**TASK-3.2 (API integration tests)**: Add pytest integration tests: skill with members, skill with no members (empty response), non-skill artifact (existing plugin behavior unchanged), missing skill (404). All 4 scenarios pass. (1 pt)

---

### Phase 4: Marketplace UI

| ID | Task | Status | Agent | Dependencies |
|----|------|--------|-------|-------------|
| TASK-4.1 | Add "Show embedded artifacts" toggle | pending | ui-engineer-enhanced | TASK-3.1 |
| TASK-4.2 | Generalize Plugin Breakdown to Skill Members tab | pending | ui-engineer-enhanced | TASK-3.1 |
| TASK-4.3 | Render embedded artifacts as top-level with parent indicator + dedup | pending | ui-engineer-enhanced | TASK-4.1 |
| TASK-4.4 | Individual import for embedded artifacts | pending | ui-engineer-enhanced, python-backend-engineer | TASK-4.3 |

**TASK-4.1 (Add "Show embedded artifacts" toggle)**: Add toggle to marketplace source view controlling whether embedded artifacts appear as top-level items. Default: ON. Toggle is display-only — detection always runs. When ON: embedded artifacts shown in main list + Skill Members tab (dedup ensures shown once). When OFF: embedded artifacts only in Skill Members tab. (1 pt)

**TASK-4.2 (Generalize Plugin Breakdown to Skill Members tab)**: In `source-artifact-modal.tsx`, drive breakdown tab label from `composite_type`: `"Plugin Members"` for plugin, `"Skill Members"` for skill. Label substitution only — no structural changes. Snapshot test verifies both. (1 pt)

**TASK-4.3 (Render embedded artifacts as top-level with parent indicator + dedup)**: When toggle is ON, render embedded artifacts in the main artifact list with a parent indicator (e.g. "contained in [Skill Name]"). Dedup logic ensures an embedded artifact appearing in multiple skills is shown once. (2 pts)

**TASK-4.4 (Individual import for embedded artifacts)**: Support importing an embedded artifact individually (standalone, no membership) directly from the marketplace list. Backend: endpoint or parameter to import single embedded artifact. Frontend: import button/action on embedded artifact row. (2 pts)

---

### Phase 5: Collection UI

| ID | Task | Status | Agent | Dependencies |
|----|------|--------|-------|-------------|
| TASK-5.1 | Generalize artifact-contains-tab label | pending | ui-engineer-enhanced | TASK-3.1 |
| TASK-5.2 | Verify "Part of" section for skills | pending | ui-engineer-enhanced | TASK-5.1 |
| TASK-5.3 | Collection UI E2E tests | pending | ui-engineer-enhanced | TASK-5.2 |

**TASK-5.1 (Generalize artifact-contains-tab label)**: In `artifact-contains-tab.tsx`, replace hardcoded `"Plugin Members"` with `"{displayType} Members"` derived from `composite_type` via `ARTIFACT_TYPES` config. Handles unknown types with fallback label. Snapshot test verifies plugin and skill labels. (1 pt)

**TASK-5.2 (Verify "Part of" section for skills)**: Verify `artifact-part-of-section.tsx` renders correctly for member artifacts (commands, agents, hooks) belonging to a skill. Confirm with E2E test. Fix any label or query gap if found. E2E: command that is a member of a skill shows "Part of: [Skill Name]". (1 pt)

**TASK-5.3 (Collection UI E2E tests)**: Write Playwright/Jest E2E tests: (1) skill detail modal shows Members tab with correct member count; (2) member artifact shows "Part of" section; (3) plugin detail modal behavior unchanged. All 3 E2E scenarios pass in CI. (2 pts)

---

### Phase 6: Deployment

| ID | Task | Status | Agent | Dependencies |
|----|------|--------|-------|-------------|
| TASK-6.1 | Member-aware DeploymentManager | pending | python-backend-engineer | TASK-3.1 |
| TASK-6.2 | CLI flags for deploy | pending | python-backend-engineer | TASK-6.1 |
| TASK-6.3 | Deployment integration tests | pending | python-backend-engineer | TASK-6.1 |

**TASK-6.1 (Member-aware DeploymentManager)**: Extend `skillmeat/core/deployment.py` `DeploymentManager.deploy()` with `include_members: bool = True`. When `True`: query `CompositeMembership` children via associations, deploy each to type-specific path (`commands/` → `.claude/commands/`, etc.). Atomic operation with rollback on failure. Existing conflict detection applied to member files. (3 pts)

**TASK-6.2 (CLI flags for deploy)**: Add `--members` / `--no-members` boolean flags to `skillmeat deploy`. Default: `--members`. Update `--help` text. (1 pt)

**TASK-6.3 (Deployment integration tests)**: Pytest tests: deploy with members (verify paths), deploy with `--no-members` (verify member paths absent), deploy of non-skill artifact (existing behavior unchanged), conflict detection triggers prompt on locally-modified member file. All 4 scenarios pass. (1 pt)

---

### Phase 7: Version Tracking & Sync

| ID | Task | Status | Agent | Dependencies |
|----|------|--------|-------|-------------|
| TASK-7.1 | Sync diff logic for skill members | pending | python-backend-engineer | TASK-3.1, TASK-6.1 |
| TASK-7.2 | Surface member drift in sync status tab | pending | ui-engineer-enhanced | TASK-7.1 |
| TASK-7.3 | CLI list member count indicator | pending | python-backend-engineer | TASK-3.1 |

**TASK-7.1 (Sync diff logic for skill members)**: Extend sync diff logic to generate per-member version comparison rows for skills. Each member appears as a child row under its parent skill row with `source_version`, `collection_version`, `deployed_version` fields. Unit test: skill with 3 members produces 4 rows. (2 pts)

**TASK-7.2 (Surface member drift in sync status tab)**: Update `sync-status-tab.tsx` to render per-member drift rows as collapsible children under parent skill row. Reuse existing diff row component; add expand/collapse toggle. E2E: skill with drift shows skill row + expandable member rows with version info. (2 pts)

**TASK-7.3 (CLI list member count indicator)**: Extend `skillmeat list` output to show `[+N members]` beside skills with `CompositeMembership` rows. Reuse associations query. Unit test: skill with 3 members shows `[+3 members]`; no indicator for skills without members. (1 pt)

---

### Phase 8: Testing & Validation

| ID | Task | Status | Agent | Dependencies |
|----|------|--------|-------|-------------|
| TASK-8.1 | Full E2E test flow | pending | task-completion-validator | TASK-5.3, TASK-4.4, TASK-6.3, TASK-7.2 |
| TASK-8.2 | Plugin regression suite | pending | python-backend-engineer | TASK-8.1 |
| TASK-8.3 | Performance benchmarks | pending | python-backend-engineer | TASK-8.2 |

**TASK-8.1 (Full E2E test flow)**: End-to-end test: marketplace browse skill → view "Skill Members" tab → import skill → verify collection Members tab → deploy skill + members → verify file placement at correct paths. All steps pass in CI with fixture skill containing 3 embedded artifacts. (2 pts)

**TASK-8.2 (Plugin regression suite)**: Run existing plugin composite tests in full. Fix any regressions introduced by label generalization or associations API changes. All pre-existing plugin composite tests pass without modification. (0.5 pts)

**TASK-8.3 (Performance benchmarks)**: Measure: (1) import skill with 10 embedded artifacts (target <5s); (2) `GET /associations` for skill with 20 members (target P95 <200ms). Add `idx_composite_artifacts_metadata_json` index if needed. Both benchmarks meet targets; results documented in PR. (1 pt)

---

## Orchestration Quick Reference

### Batch Execution

```text
# Batch 1 — Phase 1 start (sequential prerequisite)
Task("data-layer-expert", "TASK-1.1: Alembic migration — add 'skill' to composite_type CHECK constraint.
     File: skillmeat/cache/migrations/ (new migration file)
     Use batch_alter_table for SQLite compatibility (DROP + re-create pattern).
     Existing valid values: ('plugin', 'stack', 'suite') → add 'skill'.
     Must: alembic upgrade head AND downgrade -1 both pass on DB with existing plugin rows.
     Plan ref: docs/project_plans/implementation_plans/features/skill-contained-artifacts-v1.md Phase 1",
     model="sonnet", mode="acceptEdits")

# Batch 2 — Phase 1 parallel (after TASK-1.1)
Task("python-backend-engineer", "TASK-1.2: ORM model update — update CompositeArtifact CHECK constraint literal.
     File: skillmeat/cache/models.py
     Update __table_args__ CHECK to reflect ('plugin', 'stack', 'suite', 'skill').
     Update docstring. Existing plugin tests must still pass.",
     model="sonnet", mode="acceptEdits")

Task("python-backend-engineer", "TASK-1.3: CompositeService extension — add create_skill_composite() method.
     File: skillmeat/core/services/composite_service.py (or equivalent composite service file)
     Add create_skill_composite(skill_artifact, embedded_list) creating CompositeArtifact row
     with composite_type='skill', metadata_json={'artifact_uuid': skill_uuid}.
     Stub member creation (dedup logic lands in Phase 2). Unit test verifies row fields.",
     model="sonnet", mode="acceptEdits")

# Batch 3 — Phase 2 start (after TASK-1.2, TASK-1.3)
Task("python-backend-engineer", "TASK-2.1: Dedup logic in CompositeService.
     Complete create_skill_composite(): for each DetectedArtifact in embedded_list, check
     collection for existing Artifact by content hash; reuse UUID if found, else create new row.
     Integration test: two skills sharing a command → command Artifact row count stays at 1.",
     model="sonnet", mode="acceptEdits")

# Batch 4 — Phase 2 parallel (after TASK-2.1)
Task("python-backend-engineer", "TASK-2.2: CompositeMembership creation.
     After hash dedup, create CompositeMembership row linking CompositeArtifact to each child
     Artifact UUID. Use existing unique(collection_id, composite_id, child_artifact_uuid) index
     for idempotency. Re-import must not create duplicate membership rows.",
     model="sonnet", mode="acceptEdits")

Task("python-backend-engineer", "TASK-2.3: Atomic transaction wiring in importer.py.
     Extend importer.py: after skill Artifact row committed, call create_skill_composite() inside
     same Session.begin() block. Full rollback on any exception. Guard with
     SKILL_CONTAINED_ARTIFACTS_ENABLED feature flag. Rollback integration test required.",
     model="sonnet", mode="acceptEdits")

# Batch 5 — Phase 3 start (after TASK-2.3)
Task("python-backend-engineer", "TASK-3.1: Associations router fix — resolve skill UUID to CompositeArtifact.
     File: skillmeat/api/routers/artifacts.py (GET /api/v1/artifacts/{artifact_id}/associations)
     When artifact is a skill, look up companion CompositeArtifact by
     metadata_json->>'artifact_uuid' = artifact_id, then query CompositeMembership rows.
     Return existing AssociationsDTO (no schema change).",
     model="sonnet", mode="acceptEdits")

# Batch 6 — Phase 3 follow-up (after TASK-3.1)
Task("python-backend-engineer", "TASK-3.2: API integration tests for associations endpoint.
     4 scenarios: skill with members, skill with no members (empty), non-skill artifact
     (plugin behavior unchanged), missing skill (404). All pass.",
     model="sonnet", mode="acceptEdits")

# Batch 7 — Cross-phase parallel (after TASK-3.2 — Phases 4/5/6/7 can start)
Task("ui-engineer-enhanced", "TASK-4.1: Add 'Show embedded artifacts' toggle.
     Add toggle to marketplace source view (default ON) controlling whether embedded artifacts
     appear as top-level items. Display-only — detection always runs.
     ON: embedded artifacts in main list + Skill Members tab (dedup). OFF: Skill Members tab only.",
     model="sonnet", mode="acceptEdits")

Task("ui-engineer-enhanced", "TASK-4.2: Generalize Plugin Breakdown to Skill Members tab.
     File: skillmeat/web/components/marketplace/source-artifact-modal.tsx
     Drive breakdown tab label from composite_type: 'Plugin Members' for plugin,
     'Skill Members' for skill. Label substitution only. Snapshot test verifies both.",
     model="sonnet", mode="acceptEdits")

Task("ui-engineer-enhanced", "TASK-5.1: Generalize artifact-contains-tab label.
     File: skillmeat/web/components/artifact/artifact-contains-tab.tsx
     Replace hardcoded 'Plugin Members' with '{displayType} Members' from ARTIFACT_TYPES config.
     Fallback label for unknown composite_type. Snapshot tests for plugin and skill.",
     model="sonnet", mode="acceptEdits")

Task("python-backend-engineer", "TASK-6.1: Member-aware DeploymentManager.
     File: skillmeat/core/deployment.py — DeploymentManager.deploy()
     Add include_members: bool = True param. Query CompositeMembership children via associations,
     deploy each to type-specific path. Atomic with rollback. Apply conflict detection to member files.",
     model="sonnet", mode="acceptEdits")

Task("python-backend-engineer", "TASK-7.3: CLI list member count indicator.
     Extend skillmeat list output to show '[+N members]' beside skills with CompositeMembership rows.
     Reuse associations query. Unit test: skill with 3 members shows '[+3 members]'.",
     model="sonnet", mode="acceptEdits")

# Batch 8 — (after Batch 7)
Task("ui-engineer-enhanced", "TASK-4.3: Render embedded artifacts as top-level with parent indicator + dedup.
     When toggle is ON, render embedded artifacts in main artifact list with parent indicator
     ('contained in [Skill Name]'). Dedup: embedded artifact in multiple skills shown once.
     Depends on TASK-4.1 toggle being in place.",
     model="sonnet", mode="acceptEdits")

Task("ui-engineer-enhanced", "TASK-5.2: Verify 'Part of' section for skills.
     File: skillmeat/web/components/artifact/artifact-part-of-section.tsx
     Verify renders correctly for member artifacts (commands, agents, hooks) belonging to a skill.
     Fix any label or query gap. E2E: command member shows 'Part of: [Skill Name]'.",
     model="sonnet", mode="acceptEdits")

Task("python-backend-engineer", "TASK-6.2: CLI flags for deploy.
     Add --members / --no-members boolean flags to skillmeat deploy CLI command.
     Default: --members (include members). Update --help text.",
     model="sonnet", mode="acceptEdits")

Task("python-backend-engineer", "TASK-7.1: Sync diff logic for skill members.
     Extend sync diff logic to generate per-member version comparison rows for skills.
     Each member: child row under parent skill with source_version, collection_version,
     deployed_version fields. Unit test: skill with 3 members → 4 diff rows.",
     model="sonnet", mode="acceptEdits")

# Batch 9 — (after Batch 8)
Task("ui-engineer-enhanced", "TASK-4.4: Individual import for embedded artifacts.
     Support importing an embedded artifact individually (standalone, no membership) from marketplace list.
     Backend: endpoint or parameter to import single embedded artifact without skill membership.
     Frontend: import button/action on embedded artifact row. Depends on TASK-4.3.",
     model="sonnet", mode="acceptEdits")

Task("ui-engineer-enhanced", "TASK-5.3: Collection UI E2E tests.
     Playwright/Jest E2E: (1) skill modal shows Members tab with correct member count;
     (2) member artifact shows 'Part of' section; (3) plugin modal behavior unchanged. All pass in CI.",
     model="sonnet", mode="acceptEdits")

Task("python-backend-engineer", "TASK-6.3: Deployment integration tests.
     4 scenarios: deploy with members (verify paths), --no-members (member paths absent),
     non-skill artifact (unchanged behavior), conflict detection triggers on locally-modified member file.",
     model="sonnet", mode="acceptEdits")

Task("ui-engineer-enhanced", "TASK-7.2: Surface member drift in sync status tab.
     File: skillmeat/web/components/sync-status/sync-status-tab.tsx
     Render per-member drift rows as collapsible children under parent skill row.
     Reuse existing diff row component. Add expand/collapse toggle.
     E2E: skill with drift shows expandable member rows with version info.",
     model="sonnet", mode="acceptEdits")

# Batch 10 — Phase 8 validation (after TASK-5.3, TASK-4.4, TASK-6.3, TASK-7.2)
Task("task-completion-validator", "TASK-8.1: Full E2E test flow.
     End-to-end: marketplace browse skill → view 'Skill Members' tab → import skill →
     verify collection Members tab → deploy skill + members → verify file placement.
     Use fixture skill with 3 embedded artifacts. All steps must pass in CI.",
     model="sonnet", mode="plan")

# Batch 11 — (after TASK-8.1)
Task("python-backend-engineer", "TASK-8.2: Plugin regression suite.
     Run existing plugin composite tests in full. Fix any regressions from label generalization
     or associations API changes. All pre-existing plugin composite tests pass without modification.",
     model="sonnet", mode="acceptEdits")

# Batch 12 — (after TASK-8.2)
Task("python-backend-engineer", "TASK-8.3: Performance benchmarks.
     Measure: (1) import skill with 10 embedded artifacts (target <5s);
     (2) GET /associations for skill with 20 members (target P95 <200ms).
     Add idx_composite_artifacts_metadata_json index if needed. Document results in PR.",
     model="sonnet", mode="acceptEdits")
```

### CLI Updates

```bash
# After each batch, update status using the CLI script
# Example: after Batch 1
python /Users/miethe/dev/homelab/development/skillmeat/.claude/skills/artifact-tracking/scripts/update-batch.py \
  -f /Users/miethe/dev/homelab/development/skillmeat/.claude/progress/skill-contained-artifacts-v1/all-phases-progress.md \
  --updates "TASK-1.1:completed"

# After Batch 2
python /Users/miethe/dev/homelab/development/skillmeat/.claude/skills/artifact-tracking/scripts/update-batch.py \
  -f /Users/miethe/dev/homelab/development/skillmeat/.claude/progress/skill-contained-artifacts-v1/all-phases-progress.md \
  --updates "TASK-1.2:completed,TASK-1.3:completed"

# After Batch 3
python /Users/miethe/dev/homelab/development/skillmeat/.claude/skills/artifact-tracking/scripts/update-batch.py \
  -f /Users/miethe/dev/homelab/development/skillmeat/.claude/progress/skill-contained-artifacts-v1/all-phases-progress.md \
  --updates "TASK-2.1:completed"

# After Batch 4
python /Users/miethe/dev/homelab/development/skillmeat/.claude/skills/artifact-tracking/scripts/update-batch.py \
  -f /Users/miethe/dev/homelab/development/skillmeat/.claude/progress/skill-contained-artifacts-v1/all-phases-progress.md \
  --updates "TASK-2.2:completed,TASK-2.3:completed"

# After Batch 5
python /Users/miethe/dev/homelab/development/skillmeat/.claude/skills/artifact-tracking/scripts/update-batch.py \
  -f /Users/miethe/dev/homelab/development/skillmeat/.claude/progress/skill-contained-artifacts-v1/all-phases-progress.md \
  --updates "TASK-3.1:completed"

# After Batch 6
python /Users/miethe/dev/homelab/development/skillmeat/.claude/skills/artifact-tracking/scripts/update-batch.py \
  -f /Users/miethe/dev/homelab/development/skillmeat/.claude/progress/skill-contained-artifacts-v1/all-phases-progress.md \
  --updates "TASK-3.2:completed"

# After Batch 7
python /Users/miethe/dev/homelab/development/skillmeat/.claude/skills/artifact-tracking/scripts/update-batch.py \
  -f /Users/miethe/dev/homelab/development/skillmeat/.claude/progress/skill-contained-artifacts-v1/all-phases-progress.md \
  --updates "TASK-4.1:completed,TASK-4.2:completed,TASK-5.1:completed,TASK-6.1:completed,TASK-7.3:completed"

# After Batch 8
python /Users/miethe/dev/homelab/development/skillmeat/.claude/skills/artifact-tracking/scripts/update-batch.py \
  -f /Users/miethe/dev/homelab/development/skillmeat/.claude/progress/skill-contained-artifacts-v1/all-phases-progress.md \
  --updates "TASK-4.3:completed,TASK-5.2:completed,TASK-6.2:completed,TASK-7.1:completed"

# After Batch 9
python /Users/miethe/dev/homelab/development/skillmeat/.claude/skills/artifact-tracking/scripts/update-batch.py \
  -f /Users/miethe/dev/homelab/development/skillmeat/.claude/progress/skill-contained-artifacts-v1/all-phases-progress.md \
  --updates "TASK-4.4:completed,TASK-5.3:completed,TASK-6.3:completed,TASK-7.2:completed"

# After Batch 10
python /Users/miethe/dev/homelab/development/skillmeat/.claude/skills/artifact-tracking/scripts/update-batch.py \
  -f /Users/miethe/dev/homelab/development/skillmeat/.claude/progress/skill-contained-artifacts-v1/all-phases-progress.md \
  --updates "TASK-8.1:completed"

# After Batch 11
python /Users/miethe/dev/homelab/development/skillmeat/.claude/skills/artifact-tracking/scripts/update-batch.py \
  -f /Users/miethe/dev/homelab/development/skillmeat/.claude/progress/skill-contained-artifacts-v1/all-phases-progress.md \
  --updates "TASK-8.2:completed"

# After Batch 12
python /Users/miethe/dev/homelab/development/skillmeat/.claude/skills/artifact-tracking/scripts/update-batch.py \
  -f /Users/miethe/dev/homelab/development/skillmeat/.claude/progress/skill-contained-artifacts-v1/all-phases-progress.md \
  --updates "TASK-8.3:completed"
```
