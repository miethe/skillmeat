---
type: progress
schema_version: 2
doc_type: progress
prd: marketplace-embedded-artifacts
feature_slug: marketplace-embedded-artifacts
prd_ref: null
plan_ref: docs/project_plans/implementation_plans/bugs/marketplace-embedded-artifacts-v1.md
phase: 2
title: Defensive Fixes and Testing
status: completed
started: '2026-02-21'
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: on-track
total_tasks: 5
completed_tasks: 5
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
- ui-engineer-enhanced
contributors:
- task-completion-validator
tasks:
- id: P2-T1
  description: Defensive path resolution in file serving endpoint
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 2pt
  priority: high
- id: P2-T2
  description: Defensive URL construction in frontend SDK
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 1pt
  priority: medium
- id: P2-T3
  description: Update source detail page to render embedded artifacts as children
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 2pt
  priority: medium
- id: P2-T4
  description: Unit tests for heuristic detector embedded artifact handling
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 2pt
  priority: high
- id: P2-T5
  description: API integration tests for file serving endpoint
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-T1
  estimated_effort: 1pt
  priority: medium
parallelization:
  batch_1:
  - P2-T1
  - P2-T2
  - P2-T3
  - P2-T4
  batch_2:
  - P2-T5
  critical_path:
  - P2-T1
  - P2-T5
  estimated_total_time: 4-5h
blockers: []
success_criteria:
- id: SC-1
  description: File serving endpoint returns 200 for embedded artifact file requests
  status: pending
- id: SC-2
  description: Frontend SDK generates correct URLs for file-path artifacts
  status: pending
- id: SC-3
  description: Source detail page renders embedded artifacts as children
  status: pending
- id: SC-4
  description: All new unit and integration tests pass
  status: pending
- id: SC-5
  description: pnpm type-check passes
  status: pending
files_modified:
- skillmeat/api/routers/marketplace_sources.py
- skillmeat/web/sdk/services/MarketplaceSourcesService.ts
- skillmeat/web/app/marketplace/sources/[id]/page.tsx
progress: 100
updated: '2026-02-21'
---

# marketplace-embedded-artifacts - Phase 2: Defensive Fixes and Testing

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/marketplace-embedded-artifacts/phase-2-progress.md -t P2-T1 -s completed
```

---

## Objective

Add defensive path resolution in the API endpoint and frontend SDK to handle edge cases. Cover all embedded artifact scenarios with comprehensive tests. Ensure UI renders embedded artifacts correctly under their parent Skills.

---

## Implementation Notes

### Architectural Decisions

- **Defensive fallback, not replacement**: The API fix adds a fallback for file-path artifact paths, keeping existing directory-path behavior unchanged.
- **Frontend guard**: SDK detects file extensions in artifact paths to prevent URL duplication - only fires for known extensions.

### Known Gotchas

- File extension detection must cover `.md`, `.py`, `.yaml`, `.json`, `.toml` at minimum
- Source detail page rendering may use a flat list - need to restructure for hierarchical display
- Existing tests may mock `DetectedArtifact` without `embedded_artifacts` field - need backward-compat

## Orchestration Quick Reference

Backend and frontend run in parallel (batch_1):

```python
# See implementation plan for full Task() prompts
Task("python-backend-engineer", """...""")  # P2-T1, P2-T4, P2-T5
Task("ui-engineer-enhanced", """...""")     # P2-T2, P2-T3
```

Batch update after completion:
```bash
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/marketplace-embedded-artifacts/phase-2-progress.md \
  --updates "P2-T1:completed,P2-T2:completed,P2-T3:completed,P2-T4:completed,P2-T5:completed"
```
