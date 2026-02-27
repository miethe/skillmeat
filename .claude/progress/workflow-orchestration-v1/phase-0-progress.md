---
type: progress
prd: workflow-orchestration-v1
phase: 0
title: Prerequisites & Foundation
status: completed
started: null
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 5
completed_tasks: 5
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- lead-architect
- python-backend-engineer
contributors:
- ui-engineer-enhanced
- codebase-explorer
tasks:
- id: PREP-0.1
  description: Create feature branch feat/workflow-orchestration-v1 from main
  status: completed
  assigned_to:
  - lead-architect
  dependencies: []
  estimated_effort: 0.5 pts
  priority: critical
- id: PREP-0.2
  description: Add WORKFLOW ArtifactType to enum in artifact_detection.py with detection
    heuristic for WORKFLOW.yaml
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - PREP-0.1
  estimated_effort: 1 pt
  priority: critical
- id: PREP-0.3
  description: Install @dnd-kit/core, @dnd-kit/sortable, @dnd-kit/utilities in skillmeat/web
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - PREP-0.1
  estimated_effort: 0.5 pts
  priority: high
- id: PREP-0.4
  description: Review context_entities.py router, BundleBuilder, collection manifest,
    MemoryService/ContextPackerService patterns
  status: completed
  assigned_to:
  - lead-architect
  dependencies: []
  estimated_effort: 1 pt
  priority: high
- id: PREP-0.5
  description: Create workflows/ in collection directory, update collection.toml schema
    for type=workflow
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - PREP-0.2
  estimated_effort: 1 pt
  priority: high
parallelization:
  batch_1:
  - PREP-0.1
  - PREP-0.4
  batch_2:
  - PREP-0.2
  - PREP-0.3
  batch_3:
  - PREP-0.5
  critical_path:
  - PREP-0.1
  - PREP-0.2
  - PREP-0.5
  estimated_total_time: 2-3 days
blockers: []
success_criteria:
- id: SC-0.1
  description: Feature branch created and pushed
  status: pending
- id: SC-0.2
  description: ArtifactType.WORKFLOW in enum, detection working
  status: pending
- id: SC-0.3
  description: '@dnd-kit installed and building'
  status: pending
- id: SC-0.4
  description: Pattern review documented
  status: pending
- id: SC-0.5
  description: Collection directory supports workflows
  status: pending
files_modified:
- skillmeat/core/artifact_detection.py
- skillmeat/web/package.json
- skillmeat/core/collection.py
schema_version: 2
doc_type: progress
feature_slug: workflow-orchestration-v1
progress: 100
updated: '2026-02-27'
---

# workflow-orchestration-v1 - Phase 0: Prerequisites & Foundation

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/workflow-orchestration-v1/phase-0-progress.md -t PREP-0.1 -s completed
```

---

## Objective

Establish the feature branch, extend the artifact type system to include workflows, install frontend DnD dependencies, and review existing patterns that the workflow system will build upon.

---

## Orchestration Quick Reference

```python
# Batch 1: Independent foundation tasks
Task("lead-architect", "Create feature branch feat/workflow-orchestration-v1 from main. Initial commit with plan reference.", model="haiku")
Task("lead-architect", "Review context_entities.py router, BundleBuilder pattern, collection manifest structure, MemoryService/ContextPackerService integration points. Write design notes.", model="opus")

# Batch 2: After branch exists
Task("python-backend-engineer", "Add WORKFLOW = 'workflow' to ArtifactType enum in skillmeat/core/artifact_detection.py. Add detection heuristic for WORKFLOW.yaml/WORKFLOW.json files. File: skillmeat/core/artifact_detection.py")
Task("ui-engineer-enhanced", "Install @dnd-kit: pnpm add @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities in skillmeat/web/. Verify build succeeds.", model="sonnet")

# Batch 3: After ArtifactType extended
Task("python-backend-engineer", "Create workflows/ directory in collection structure. Update collection.toml schema to accept type='workflow' entries. Files: skillmeat/core/collection.py")
```
