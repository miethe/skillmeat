---
type: progress
prd: composite-artifact-infrastructure
phase: 2
title: Enhanced Discovery (Core)
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
- python-backend-engineer
- backend-architect
contributors:
- code-reviewer
tasks:
- id: CAI-P2-01
  description: Define DiscoveredGraph dataclass with parent + children + linkage metadata
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CAI-P1-07
  estimated_effort: 1pt
  priority: high
- id: CAI-P2-02
  description: Implement detect_composites() - composite root detection (plugin.json
    OR 2+ artifact-type subdirs)
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - CAI-P2-01
  estimated_effort: 2pt
  priority: high
- id: CAI-P2-03
  description: Update discover_artifacts() to return DiscoveredGraph for composites,
    flat DiscoveryResult for atomic
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CAI-P2-02
  estimated_effort: 2pt
  priority: high
- id: CAI-P2-04
  description: Unit tests with 40+ fixture repos covering true/false positives (<5%
    FP rate)
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - CAI-P2-03
  estimated_effort: 2pt
  priority: medium
- id: CAI-P2-05
  description: Implement composite_artifacts_enabled feature flag gating new discovery
    path
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CAI-P2-04
  estimated_effort: 1pt
  priority: medium
parallelization:
  batch_1:
  - CAI-P2-01
  batch_2:
  - CAI-P2-02
  - CAI-P2-03
  batch_3:
  - CAI-P2-04
  - CAI-P2-05
  critical_path:
  - CAI-P2-01
  - CAI-P2-02
  - CAI-P2-03
  - CAI-P2-04
  estimated_total_time: 2-3 days
blockers: []
success_criteria:
- id: SC-P2-1
  description: Composite detection returns DiscoveredGraph with correct parent/children
    linkage
  status: pending
- id: SC-P2-2
  description: False positive rate <5% on fixture repo set (40+ repos)
  status: pending
- id: SC-P2-3
  description: Existing flat discovery tests pass (no regression)
  status: pending
- id: SC-P2-4
  description: Feature flag properly gates new behavior
  status: pending
- id: SC-P2-5
  description: Discovery scan time adds <500ms overhead
  status: pending
files_modified:
- skillmeat/core/discovery/
- skillmeat/core/artifact_detection.py
- tests/test_composite_detection.py
progress: 100
updated: '2026-02-18'
schema_version: 2
doc_type: progress
feature_slug: composite-artifact-infrastructure
---

# composite-artifact-infrastructure - Phase 2: Enhanced Discovery (Core)

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/composite-artifact-infrastructure/phase-2-progress.md -t CAI-P2-01 -s completed
python .claude/skills/artifact-tracking/scripts/update-batch.py -f .claude/progress/composite-artifact-infrastructure/phase-2-progress.md --updates "CAI-P2-01:completed,CAI-P2-02:completed"
```

---

## Objective

Update the discovery layer to detect composite artifact roots, recursively enumerate children, and return `DiscoveredGraph` structure instead of flat list. Gate behind feature flag.

---

## Orchestration Quick Reference

```text
# Batch 1: Dataclass (python-backend-engineer)
Task("python-backend-engineer", "Define DiscoveredGraph dataclass.
  Files: skillmeat/core/discovery/
  Task: CAI-P2-01
  Acceptance: Dataclass serializable, integrates with existing DiscoveryResult")

# Batch 2: Detection + integration (backend-architect, python-backend-engineer)
Task("backend-architect", "Implement detect_composites() with plugin.json and multi-subdir detection.
  Files: skillmeat/core/discovery/, skillmeat/core/artifact_detection.py
  Tasks: CAI-P2-02, CAI-P2-03
  Acceptance: Correct parent/children for test repos; flat discovery unaffected")

# Batch 3: Tests + flag (backend-architect, python-backend-engineer)
Task("backend-architect", "Create discovery tests with 40+ fixture repos + feature flag.
  Tasks: CAI-P2-04, CAI-P2-05
  Acceptance: <5% FP rate, >90% TP rate, flag gates behavior correctly")
```

---

## Implementation Notes

### Key Files

- `skillmeat/core/discovery/` — Main discovery logic
- `skillmeat/core/artifact_detection.py` — Detection signatures
- Implementation plan details: `docs/project_plans/implementation_plans/features/composite-artifact-infrastructure-v1/phase-2-enhanced-discovery.md`

### Known Gotchas

- Require at least 2 distinct artifact-type children to qualify as composite (prevents false positives)
- Limit composite detection to first 3 directory levels for performance
- `plugin.json` is the authoritative signal; multi-subdir is secondary heuristic

---

## Completion Notes

_Fill in when phase is complete._
