---
# === MARKETPLACE NON-SKILLS DETECTION FIX ===
# Single-phase bug fix tracking for heuristic detector improvements
# REQUIRED FIELDS: assigned_to, dependencies for EVERY task

# Metadata: Identification and Classification
type: progress
prd: "marketplace-sources-non_skills-v1"
phase: 1
title: "Detection Algorithm Fix"
status: "planning"
started: "2025-12-31"
completed: null

# Overall Progress: Status and Estimates
overall_progress: 0
completion_estimate: "on-track"

# Task Counts: Machine-readable task state
total_tasks: 5
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

# Ownership: Primary and secondary agents
owners: ["python-backend-engineer"]
contributors: ["code-reviewer"]

# === ORCHESTRATION QUICK REFERENCE ===
# All tasks with assignments and dependencies
tasks:
  - id: "FIX-001"
    description: "Container Type Propagation - Modify container logic to propagate type hints to children"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "3h"
    priority: "high"

  - id: "FIX-002"
    description: "Frontmatter Parsing - Add YAML frontmatter parsing to extract artifact type"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "3h"
    priority: "high"

  - id: "FIX-003"
    description: "Scoring Weight Adjustment - Increase container hint weight, reduce depth penalty"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["FIX-001"]
    estimated_effort: "2h"
    priority: "medium"

  - id: "FIX-004"
    description: "Multi-Type Test Suite - Comprehensive tests for Commands, Agents, Hooks, MCP detection"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["FIX-001", "FIX-002", "FIX-003"]
    estimated_effort: "3h"
    priority: "high"

  - id: "FIX-005"
    description: "Regression Testing - Run full test suite, verify no skill detection regressions"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["FIX-004"]
    estimated_effort: "2h"
    priority: "high"

# Parallelization Strategy (computed from dependencies)
parallelization:
  batch_1: ["FIX-001", "FIX-002"]
  batch_2: ["FIX-003"]
  batch_3: ["FIX-004"]
  batch_4: ["FIX-005"]
  critical_path: ["FIX-001", "FIX-003", "FIX-004", "FIX-005"]
  estimated_total_time: "9h"

# Critical Blockers: None currently
blockers: []

# Success Criteria: Acceptance conditions for phase completion
success_criteria:
  - id: "SC-1"
    description: "All existing tests pass (no regressions)"
    status: "pending"
  - id: "SC-2"
    description: "Commands detection accuracy >= 95%"
    status: "pending"
  - id: "SC-3"
    description: "Agents detection accuracy >= 95%"
    status: "pending"
  - id: "SC-4"
    description: "Hooks detection accuracy >= 95%"
    status: "pending"
  - id: "SC-5"
    description: "MCP Servers detection accuracy >= 95%"
    status: "pending"
  - id: "SC-6"
    description: "Test coverage for heuristic_detector.py > 85%"
    status: "pending"

# Files Modified: What's being changed in this phase
files_modified:
  - "skillmeat/core/marketplace/heuristic_detector.py"
  - "tests/core/marketplace/test_heuristic_detector.py"
---

# marketplace-sources-non_skills-v1 - Phase 1: Detection Algorithm Fix

**Phase**: 1 of 1
**Status**: Planning (0% complete)
**Duration**: Started 2025-12-31
**Owner**: python-backend-engineer
**Contributors**: code-reviewer

---

## Orchestration Quick Reference

> **For Orchestration Agents**: Use this section to delegate tasks without reading the full file.

### Parallelization Strategy

**Batch 1** (Parallel - No Dependencies):
- FIX-001 → `python-backend-engineer` (3h) - Container type propagation
- FIX-002 → `python-backend-engineer` (3h) - Frontmatter parsing

**Batch 2** (Sequential - Depends on Batch 1):
- FIX-003 → `python-backend-engineer` (2h) - **Blocked by**: FIX-001

**Batch 3** (Sequential - Depends on Batch 2):
- FIX-004 → `python-backend-engineer` (3h) - **Blocked by**: FIX-001, FIX-002, FIX-003

**Batch 4** (Sequential - Depends on Batch 3):
- FIX-005 → `python-backend-engineer` (2h) - **Blocked by**: FIX-004

**Critical Path**: FIX-001 → FIX-003 → FIX-004 → FIX-005 (9h total if serial)

### Task Delegation Commands

```python
# Batch 1 (Launch in parallel)
Task("python-backend-engineer", """FIX-001: Container Type Propagation

Modify skillmeat/core/marketplace/heuristic_detector.py:

1. Change _is_container_directory to _get_container_type returning Optional[ArtifactType]
2. Create mapping: commands→COMMAND, agents→AGENT, skills→SKILL, hooks→HOOK, mcp→MCP_SERVER
3. Update analyze_paths to pass container_type to _score_directory for children
4. Update _score_directory signature to accept Optional[ArtifactType] container_hint
5. When container_hint is set, add container_hint_weight (25 pts) if detected type matches hint

Reference lines: 160-190 (container logic), 192-289 (analyze_paths)
""")

Task("python-backend-engineer", """FIX-002: Frontmatter Parsing

Add frontmatter parsing to skillmeat/core/marketplace/heuristic_detector.py:

1. Add method _parse_manifest_frontmatter(content: str) -> Optional[str]
   - Parse YAML frontmatter (--- delimited at start of file)
   - Return value of 'type:' field if present (normalized to lowercase)
   - Return None if no frontmatter or no type field
   - Handle malformed YAML gracefully (return None)

2. Integrate into _score_manifest:
   - If manifest file found, read its content
   - Parse frontmatter, extract type
   - If frontmatter type found, add frontmatter_type_weight (30 pts)
   - If frontmatter type contradicts directory signals, frontmatter wins

Reference lines: 483-486 (manifest scoring), 383-399 (extension handling)
""")

# Batch 2 (After Batch 1)
Task("python-backend-engineer", """FIX-003: Scoring Weight Adjustment

Update scoring in skillmeat/core/marketplace/heuristic_detector.py:

1. Add to DetectionConfig (line 91-96):
   - container_hint_weight: int = 25
   - frontmatter_type_weight: int = 30

2. Update MAX_RAW_SCORE to account for new max: 65 + 25 + 30 = 120

3. In _score_directory, when container_hint is provided and matches detected type:
   - Add container_hint_weight to raw score
   - Skip or reduce depth penalty (line 553-583)

4. Update normalize_score to use new MAX_RAW_SCORE

Reference: DetectionConfig class, _score_directory method, depth penalty logic
""")

# Batch 3 (After Batch 2)
Task("python-backend-engineer", """FIX-004: Multi-Type Test Suite

Add tests to tests/core/marketplace/test_heuristic_detector.py:

New test class: TestMultiTypeDetection

Test cases:
1. test_commands_in_container - commands/git/COMMAND.md → COMMAND
2. test_agents_in_container - agents/helper/AGENT.md → AGENT
3. test_hooks_in_container - hooks/pre-commit/HOOK.md → HOOK
4. test_mcp_in_container - mcp/server/MCP.md → MCP_SERVER
5. test_nested_plugin_structure - plugin with commands/, skills/ subdirs
6. test_frontmatter_type_override - SKILL.md with type: command → COMMAND
7. test_mixed_types_same_level - artifacts with different manifests
8. test_deep_nesting_in_container - commands/group/subgroup/cmd/COMMAND.md → COMMAND
9. test_case_insensitive_container - Commands/git/COMMAND.md → COMMAND
10. test_malformed_frontmatter_fallback - bad YAML falls back to heuristic

Each test should verify:
- Correct artifact_type detection
- Confidence score >= 70 for typed containers
- No false positives for other types
""")

# Batch 4 (After Batch 3)
Task("python-backend-engineer", """FIX-005: Regression Testing

Run full test suite and verify no regressions:

1. Run: pytest tests/core/marketplace/test_heuristic_detector.py -v
2. Run: pytest tests/ -k "marketplace" -v
3. Verify all existing tests pass
4. Check coverage: pytest --cov=skillmeat.core.marketplace --cov-report=term-missing

If any test fails:
- Document the failure
- Determine if it's a real regression or test needs updating
- Fix as appropriate

Report final test results and coverage numbers.
""")
```

---

## Overview

Fix the marketplace source detection system to properly classify non-skill artifacts (Commands, Agents, Hooks, MCP Servers) instead of misclassifying them as Skills.

**Why This Phase**: The detection algorithm has a bias toward Skills because:
1. Container directories (commands/, agents/) are skipped but type hints aren't propagated to children
2. No frontmatter content validation to confirm artifact types
3. Parent hint weights are too low compared to depth penalties

**Scope**:
- **IN SCOPE**: heuristic_detector.py algorithm fixes, comprehensive test coverage
- **OUT OF SCOPE**: Schema changes, UI changes, database changes

---

## Success Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| SC-1 | All existing tests pass (no regressions) | Pending |
| SC-2 | Commands detection accuracy >= 95% | Pending |
| SC-3 | Agents detection accuracy >= 95% | Pending |
| SC-4 | Hooks detection accuracy >= 95% | Pending |
| SC-5 | MCP Servers detection accuracy >= 95% | Pending |
| SC-6 | Test coverage for heuristic_detector.py > 85% | Pending |

---

## Tasks

| ID | Task | Status | Agent | Dependencies | Est | Notes |
|----|------|--------|-------|--------------|-----|-------|
| FIX-001 | Container Type Propagation | Pending | python-backend-engineer | None | 3h | High priority |
| FIX-002 | Frontmatter Parsing | Pending | python-backend-engineer | None | 3h | Can run parallel with FIX-001 |
| FIX-003 | Scoring Weight Adjustment | Pending | python-backend-engineer | FIX-001 | 2h | Depends on container changes |
| FIX-004 | Multi-Type Test Suite | Pending | python-backend-engineer | FIX-001,002,003 | 3h | Comprehensive tests |
| FIX-005 | Regression Testing | Pending | python-backend-engineer | FIX-004 | 2h | Final validation |

**Status Legend**:
- `Pending` Not Started
- `In Progress` Currently being worked on
- `Complete` Done
- `Blocked` Waiting on dependency
- `At Risk` May not meet deadline

---

## Architecture Context

### Current State

The heuristic detector uses a 5-signal scoring system:
- **Directory name** (10 pts): Matches type-specific directory patterns
- **Manifest** (20 pts): Presence of SKILL.md, COMMAND.md, etc.
- **Extensions** (5 pts): Expected file types present
- **Parent hint** (15 pts): Parent directory naming patterns
- **Frontmatter** (15 pts): Currently only checks file presence, not content

**Key Files**:
- `skillmeat/core/marketplace/heuristic_detector.py` - Main detection logic (686 lines)
- `tests/core/marketplace/test_heuristic_detector.py` - Existing test suite

### Reference Patterns

**Container Detection** (lines 160-190):
```python
def _is_container_directory(self, dir_name: str) -> bool:
    return dir_name.lower() in {"commands", "agents", "skills", "hooks", "rules", "mcp"}
```

**Scoring Flow** (lines 306-414):
1. Group files by parent directory
2. Check if container directory (skip if true)
3. Score each directory via 5 signals
4. Apply depth penalty
5. Normalize to 0-100 scale

---

## Implementation Details

### Technical Approach

1. **Container Type Propagation**:
   - Change `_is_container_directory` to `_get_container_type` returning `Optional[ArtifactType]`
   - When analyzing children, pass the container's implied type as a hint
   - Add new signal weight for container hint (25 pts)

2. **Frontmatter Parsing**:
   - Add YAML frontmatter parser (handle `---` delimiters)
   - Extract `type:` field if present
   - Make this the highest-weight signal (30 pts)
   - Override heuristic detection if frontmatter explicitly declares type

3. **Scoring Adjustments**:
   - New MAX_RAW_SCORE = 120 (was 65)
   - Reduce/eliminate depth penalty when inside typed container
   - Frontmatter type wins over all other signals

### Known Gotchas

- **YAML parsing**: Must handle malformed frontmatter gracefully (return None)
- **Case sensitivity**: Container names should be case-insensitive
- **Backwards compatibility**: Skill detection must remain unchanged

---

## Blockers

### Active Blockers

None currently.

### Resolved Blockers

None yet.

---

## Dependencies

### External Dependencies

None - this is a self-contained backend fix.

### Internal Integration Points

- Detection results flow into `import_coordinator.py` which uses `artifact_type` directly
- If detection is wrong, import creates wrongly-typed artifacts

---

## Testing Strategy

| Test Type | Scope | Coverage | Status |
|-----------|-------|----------|--------|
| Unit | Individual scoring functions | 85%+ | Pending |
| Integration | Full detection pipeline | All artifact types | Pending |
| Regression | Existing skill detection | All existing tests | Pending |

---

## Next Session Agenda

### Immediate Actions (Next Session)
1. [ ] Execute Batch 1: FIX-001 and FIX-002 in parallel
2. [ ] Execute Batch 2: FIX-003 after Batch 1 completes
3. [ ] Execute Batch 3: FIX-004 comprehensive test suite

### Context for Continuing Agent

The implementation plan at `docs/project_plans/implementation_plans/bugs/marketplace-sources-non_skills-v1.md` contains detailed task specifications including exact code changes needed. Use the Task() delegation commands in the Quick Reference section above.

---

## Session Notes

### 2025-12-31

**Completed**:
- Created implementation plan with root cause analysis
- Created progress tracking artifact

**In Progress**:
- Ready to begin implementation

**Next Session**:
- Execute Batch 1 tasks (FIX-001, FIX-002)

---

## Additional Resources

- **Bug Report**: `docs/project_plans/bugs/marketplace-sources-non_skills-v1.md`
- **Implementation Plan**: `docs/project_plans/implementation_plans/bugs/marketplace-sources-non_skills-v1.md`
- **Key File**: `skillmeat/core/marketplace/heuristic_detector.py`
