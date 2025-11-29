---
# === PROGRESS TRACKING TEMPLATE ===
# Phase-level task tracking optimized for AI agent orchestration
# REQUIRED FIELDS: assigned_to, dependencies for EVERY task
# Copy this template and replace all [PLACEHOLDER] values

# Metadata: Identification and Classification
type: progress
prd: "[PRD_ID]"                          # e.g., "advanced-editing-v2", "artifact-flow-modal-redesign"
phase: [PHASE_NUMBER]                    # e.g., 1, 2, 3 (integer, not string)
title: "[PHASE_TITLE]"                   # e.g., "3-Panel Sync Status Redesign"
status: "planning"                       # planning|in-progress|review|complete|blocked
started: "[YYYY-MM-DD]"                  # Start date of this phase
completed: null                          # "YYYY-MM-DD" when complete, null if in progress

# Overall Progress: Status and Estimates
overall_progress: [0-100]                # 0-100, e.g., 35 for 35% complete
completion_estimate: "on-track"          # on-track|at-risk|blocked|ahead

# Task Counts: Machine-readable task state
total_tasks: [COUNT]                     # Total tasks in this phase, e.g., 10
completed_tasks: [COUNT]                 # Completed count, e.g., 2
in_progress_tasks: [COUNT]               # Currently in progress, e.g., 1
blocked_tasks: [COUNT]                   # Blocked by dependencies, e.g., 0
at_risk_tasks: [COUNT]                   # At risk of missing deadline, e.g., 1

# Ownership: Primary and secondary agents
owners: ["[AGENT_NAME]"]                 # Primary agent(s), e.g., ["ui-engineer-enhanced"]
contributors: ["[AGENT_NAME]"]           # Secondary agents, e.g., ["code-reviewer"]

# === ORCHESTRATION QUICK REFERENCE ===
# For lead-architect and orchestration agents: All tasks with assignments and dependencies
# This section enables minimal-token delegation without reading full file
tasks:
  # Example task structure (REQUIRED for every task):
  - id: "TASK-1.1"
    description: "Brief task description"
    status: "pending"                    # pending|in_progress|complete|blocked|at-risk
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []                     # Empty if no dependencies, or ["TASK-1.0", "TASK-0.9"]
    estimated_effort: "2h"               # Optional: time estimate
    priority: "high"                     # Optional: low|medium|high|critical

  # Parallel tasks (no dependencies):
  - id: "TASK-1.2"
    description: "Another task that can run in parallel"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "1.5h"
    priority: "medium"

  # Sequential task (depends on others):
  - id: "TASK-2.1"
    description: "Task that depends on TASK-1.1 and TASK-1.2"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-1.1", "TASK-1.2"]  # MUST wait for these to complete
    estimated_effort: "3h"
    priority: "high"

# Parallelization Strategy (computed from dependencies)
parallelization:
  batch_1: ["TASK-1.1", "TASK-1.2"]      # Can run simultaneously
  batch_2: ["TASK-2.1"]                  # Sequential, waits for batch_1
  critical_path: ["TASK-1.1", "TASK-2.1"] # Longest dependency chain
  estimated_total_time: "5h"             # If run optimally (parallel batches)

# Critical Blockers: For immediate visibility
blockers: []                             # Array of blocker objects
# Example blocker:
# - id: "BLOCKER-001"
#   title: "Missing API endpoint"
#   severity: "critical"                # critical|high|medium
#   blocking: ["TASK-2.1", "TASK-2.2"]
#   resolution: "Awaiting backend-engineer implementation"
#   created: "YYYY-MM-DD"

# Success Criteria: Acceptance conditions for phase completion
success_criteria: [
  # Example:
  # { id: "SC-1", description: "All components render correctly", status: "pending" },
  # { id: "SC-2", description: "All tests pass", status: "pending" }
]

# Files Modified: What's being changed in this phase
files_modified: [
  # Example:
  # "components/entity/sync-status/artifact-flow-banner.tsx",
  # "components/entity/unified-entity-modal.tsx"
]
---

# [PRD_ID] - Phase [PHASE_NUMBER]: [PHASE_TITLE]

**Phase**: [PHASE_NUMBER] of [TOTAL_PHASES]
**Status**: [Status Emoji] [Status] ([PERCENT]% complete)
**Duration**: Started [START_DATE], estimated completion [EST_DATE]
**Owner**: [AGENT_NAME]
**Contributors**: [AGENT_NAME], [AGENT_NAME]

---

## Orchestration Quick Reference

> **For Orchestration Agents**: Use this section to delegate tasks without reading the full file.

### Parallelization Strategy

**Batch 1** (Parallel - No Dependencies):
- TASK-1.1 → `ui-engineer-enhanced` (2h)
- TASK-1.2 → `ui-engineer-enhanced` (1.5h)

**Batch 2** (Sequential - Depends on Batch 1):
- TASK-2.1 → `ui-engineer-enhanced` (3h) - **Blocked by**: TASK-1.1, TASK-1.2

**Critical Path**: TASK-1.1 → TASK-2.1 (5h total)

### Task Delegation Commands

```
# Batch 1 (Launch in parallel)
Task("ui-engineer-enhanced", "TASK-1.1: [description]")
Task("ui-engineer-enhanced", "TASK-1.2: [description]")

# Batch 2 (After Batch 1 completes)
Task("ui-engineer-enhanced", "TASK-2.1: [description]")
```

---

## Overview

Clear, concise description of what this phase accomplishes.

**Why This Phase**: Explain the strategic importance and what problem it solves.

**Scope**: Clearly delineate what is IN scope and what is OUT of scope.

---

## Success Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| SC-1 | Clear acceptance condition | ⏳ Pending |
| SC-2 | Another acceptance condition | ⏳ Pending |

---

## Tasks

| ID | Task | Status | Agent | Dependencies | Est | Notes |
|----|------|--------|-------|--------------|-----|-------|
| TASK-1.1 | Task description | ⏳ | ui-engineer-enhanced | None | 2h | Brief context |
| TASK-1.2 | Task description | ⏳ | ui-engineer-enhanced | None | 1.5h | Can run parallel |
| TASK-2.1 | Task description | ⏳ | ui-engineer-enhanced | TASK-1.1, TASK-1.2 | 3h | Sequential |
| TASK-2.2 | Task description | 🚫 | backend-engineer | None | 5h | Blocked by BLOCKER-001 |

**Status Legend**:
- `⏳` Not Started (Pending)
- `🔄` In Progress
- `✓` Complete
- `🚫` Blocked
- `⚠️` At Risk

---

## Architecture Context

### Current State

Describe the current implementation state, existing patterns, and what's already in place.

**Key Files**:
- `path/to/file.tsx` - Current implementation pattern
- `path/to/service.py` - Existing service layer

### Reference Patterns

Call out similar implementations elsewhere that should be mirrored for consistency.

**Similar Features**:
- Feature X in [file] uses pattern [description]
- Feature Y in [file] shows integration point [description]

---

## Implementation Details

### Technical Approach

Step-by-step approach to implementation, including:
- Architecture decisions
- Data flow
- Integration points
- Dependencies

### Known Gotchas

Things to watch out for:
- Common mistakes to avoid
- Edge cases to handle
- Browser compatibility issues
- Accessibility considerations

### Development Setup

Any special setup, configuration, or prerequisites needed for this phase.

---

## Blockers

### Active Blockers

| ID | Title | Severity | Blocking | Resolution |
|----|-------|----------|----------|-----------|
| BLOCKER-001 | Brief title | critical | TASK-2.2 | Resolution path |

### Resolved Blockers

Document blockers that have been resolved in this phase.

---

## Dependencies

### External Dependencies

- **Dependency 1**: Required for [reason], assigned to [agent]
- **Dependency 2**: Must be completed before [task], status [status]

### Internal Integration Points

- **Component A** integrates with **Component B** at [location]
- **Service X** calls **Service Y** for [operation]

---

## Testing Strategy

| Test Type | Scope | Coverage | Status |
|-----------|-------|----------|--------|
| Unit | Individual functions | 80%+ | ⏳ |
| Integration | Component interaction | Core flows | ⏳ |
| E2E | Full user workflows | Happy path + error | ⏳ |
| A11y | WCAG 2.1 AA compliance | All interactive elements | ⏳ |

---

## Next Session Agenda

### Immediate Actions (Next Session)
1. [ ] Specific action with clear context
2. [ ] Next step in sequence
3. [ ] Critical path item

### Upcoming Critical Items

- **Week of [DATE]**: [Milestone or deadline]
- **Dependency update**: [When something external completes]

### Context for Continuing Agent

[Specific information that AI agent needs to continue this phase without re-reading all context]

---

## Session Notes

### 2025-11-[DATE]

**Completed**:
- TASK-1.1: Task description with outcome

**In Progress**:
- TASK-1.2: Current status and next step

**Blockers**:
- BLOCKER-001: Description and resolution path

**Next Session**:
- Action item with context

---

## Additional Resources

- **Design Reference**: [Link to design spec or component spec]
- **Architecture Decision**: [Link to ADR if applicable]
- **API Documentation**: [Link to API docs if applicable]
- **Test Plan**: [Link to test strategy doc]
