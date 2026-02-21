---
type: progress
schema_version: 2
doc_type: progress
prd: "marketplace-embedded-artifacts"
feature_slug: "marketplace-embedded-artifacts"
prd_ref: null
plan_ref: "docs/project_plans/implementation_plans/bugs/marketplace-embedded-artifacts-v1.md"
phase: 1
title: "Detection Fix - Heuristic Detector"
status: "planning"
started: "2026-02-21"
completed: null
commit_refs: []
pr_refs: []

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 5
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["python-backend-engineer"]
contributors: []

tasks:
  - id: "P1-T1"
    description: "Build skill directory exclusion set after Skill detection"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "1pt"
    priority: "high"

  - id: "P1-T2"
    description: "Guard _detect_single_file_artifacts() against skill subtrees"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1-T1"]
    estimated_effort: "2pt"
    priority: "high"

  - id: "P1-T3"
    description: "Add embedded_artifacts field to DetectedArtifact model"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "1pt"
    priority: "high"

  - id: "P1-T4"
    description: "Populate embedded_artifacts on parent Skill artifacts"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1-T1", "P1-T2", "P1-T3"]
    estimated_effort: "2pt"
    priority: "high"

  - id: "P1-T5"
    description: "Verify scanner orchestration propagates embedded artifacts to storage"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1-T4"]
    estimated_effort: "1pt"
    priority: "medium"

parallelization:
  batch_1: ["P1-T1", "P1-T3"]
  batch_2: ["P1-T2"]
  batch_3: ["P1-T4"]
  batch_4: ["P1-T5"]
  critical_path: ["P1-T1", "P1-T2", "P1-T4", "P1-T5"]
  estimated_total_time: "4-5h"

blockers: []

success_criteria:
  - { id: "SC-1", description: "_detect_single_file_artifacts() skips files inside detected Skill directories", status: "pending" }
  - { id: "SC-2", description: "Parent Skill embedded_artifacts populated with correct children", status: "pending" }
  - { id: "SC-3", description: "No regression in top-level Command/Agent detection", status: "pending" }

files_modified: [
  "skillmeat/core/marketplace/heuristic_detector.py",
  "skillmeat/core/marketplace/github_scanner.py"
]
---

# marketplace-embedded-artifacts - Phase 1: Detection Fix - Heuristic Detector

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/marketplace-embedded-artifacts/phase-1-progress.md -t P1-T1 -s completed
```

---

## Objective

Fix the root cause in the heuristic detector so that embedded artifacts within Skills (Commands, Agents, nested Skills) are not promoted as top-level artifacts. Instead, they should be attached to the parent Skill's `embedded_artifacts` field.

---

## Implementation Notes

### Architectural Decisions

- **Exclusion set approach**: Build a set of detected Skill paths, then filter single-file candidates against it. This is O(n*m) but acceptable for typical repo sizes.
- **Mirror composites pattern**: The `embedded_artifacts` field mirrors how composites expose children, maintaining consistency.
- **One-level nesting limit**: Phase 1 limits embedded artifact population to 1 level of depth to avoid recursion complexity.

### Patterns and Best Practices

- Follow existing `DetectedArtifact` dataclass patterns in `heuristic_detector.py`
- Use `str.startswith()` for path ancestor checking
- Ensure embedded artifacts carry correct repo-relative paths

### Known Gotchas

- Skills may be detected at various directory depths (not just `skills/`)
- Some repos have nested skills (skill-within-skill) - limit to 1 level for now
- The `_detect_single_file_artifacts()` method runs independently - must receive skill_dirs as parameter

## Orchestration Quick Reference

```python
Task("python-backend-engineer", """...""")  # See implementation plan for full prompt
```

Batch update after completion:
```bash
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/marketplace-embedded-artifacts/phase-1-progress.md \
  --updates "P1-T1:completed,P1-T2:completed,P1-T3:completed,P1-T4:completed,P1-T5:completed"
```
