---
type: progress
prd: "memory-extraction-pipeline-v2"
phase: 2
title: "Quality Enhancement - Provenance & Scoring"
status: "planning"
started: null
completed: null

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 4
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["python-backend-engineer"]
contributors: []

tasks:
  - id: "MEX-2.1"
    description: "Extract provenance from JSONL messages - capture sessionId, gitBranch, timestamp, uuid into ExtractionCandidate.provenance dict"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["MEX-1.2"]
    estimated_effort: "1h"
    priority: "high"
    model: "sonnet"

  - id: "MEX-2.2"
    description: "Enhance _score() with content quality signals - first-person learning (+0.05), specificity (+0.03), questions (-0.03), vagueness (-0.04). Widen confidence spread to >=8 distinct values (0.55-0.92)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["MEX-1.4"]
    estimated_effort: "2h"
    priority: "high"
    model: "sonnet"

  - id: "MEX-2.3"
    description: "Add backward compatibility - detect plain-text input (all JSONL parse failures), fall back to legacy _iter_candidate_lines()"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["MEX-1.1", "MEX-1.4"]
    estimated_effort: "1h"
    priority: "medium"
    model: "sonnet"

  - id: "MEX-2.4"
    description: "Tests + documentation for Phase 2 - provenance fields, scoring signals, backward compat, docstrings, troubleshooting guide"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["MEX-2.1", "MEX-2.2", "MEX-2.3"]
    estimated_effort: "1h"
    priority: "high"
    model: "sonnet"

parallelization:
  batch_1: ["MEX-2.1", "MEX-2.2", "MEX-2.3"]
  batch_2: ["MEX-2.4"]
  critical_path: ["MEX-2.2", "MEX-2.4"]
  estimated_total_time: "4h"

blockers: []

success_criteria:
  - { id: "SC-2.1", description: "Provenance fields extracted and stored correctly (no nulls for valid JSONL)", status: "pending" }
  - { id: "SC-2.2", description: "Confidence scores spread to >=8 distinct values in 0.55-0.92 range", status: "pending" }
  - { id: "SC-2.3", description: "Plain-text input detected and handled via legacy fallback", status: "pending" }
  - { id: "SC-2.4", description: ">80% coverage of Phase 2 new/modified code", status: "pending" }

files_modified:
  - "skillmeat/core/services/memory_extractor_service.py"
  - "tests/test_memory/test_memory_extractor_service.py"
---

# memory-extraction-pipeline-v2 - Phase 2: Quality Enhancement - Provenance & Scoring

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/memory-extraction-pipeline-v2/phase-2-progress.md -t MEX-2.1 -s completed
```

---

## Objective

Improve candidate ranking and add session context traceability. After this phase, users can meaningfully sort candidates by confidence and trace memories back to their source session/branch.

---

## Implementation Notes

### Scoring Enhancement Signals
| Signal | Effect | Example |
|--------|--------|---------|
| First-person learning | +0.05 | "I learned that...", "We discovered..." |
| Specificity (paths/functions/numbers) | +0.03 | "schema.py:45", "validate()", "500KB limit" |
| Questions | -0.03 | "Should we use...?" |
| Vague language | -0.04 | "maybe", "probably", "might" |

### Provenance Fields
```python
provenance = {
    "source": "memory_extraction",
    "session_id": msg.get("sessionId"),
    "git_branch": msg.get("gitBranch"),
    "timestamp": msg.get("timestamp"),
    "run_id": msg.get("uuid"),
    "workflow_stage": "extraction",
}
```

---

## Orchestration Quick Reference

```python
# Phase 2 Batch 1 (parallel)
Task("python-backend-engineer", "MEX-2.1: Extract provenance from JSONL messages. Capture sessionId, gitBranch, timestamp, uuid. File: skillmeat/core/services/memory_extractor_service.py", model="sonnet")
Task("python-backend-engineer", "MEX-2.2: Enhance _score() with content quality signals. Add 4 new scoring signals per phase-2-progress.md. Widen spread to 0.55-0.92. File: skillmeat/core/services/memory_extractor_service.py", model="sonnet")
Task("python-backend-engineer", "MEX-2.3: Add backward compatibility layer. If all JSONL parse fails, fall back to _iter_candidate_lines(). File: skillmeat/core/services/memory_extractor_service.py", model="sonnet")

# Phase 2 Batch 2 (after Batch 1)
Task("python-backend-engineer", "MEX-2.4: Tests + docstrings for Phase 2. Test provenance, scoring signals, backward compat. File: tests/test_memory/test_memory_extractor_service.py", model="sonnet")
```
