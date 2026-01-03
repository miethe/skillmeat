---
title: "Implementation Plan: Marketplace Sources Non-Skills Detection Fix"
description: "Fix heuristic detector to properly classify Commands, Agents, Hooks, and MCP Servers"
audience: [ai-agents, developers]
tags: [bugfix, marketplace, detection, heuristic]
created: 2025-12-31
updated: 2025-12-31
category: "bugs"
status: draft
related:
  - /docs/project_plans/bugs/marketplace-sources-non_skills-v1.md
---

# Implementation Plan: Marketplace Sources Non-Skills Detection Fix

**Plan ID**: `IMPL-2025-12-31-MARKETPLACE-DETECTION-FIX`
**Date**: 2025-12-31
**Author**: Opus (Orchestrator)
**Related Documents**:
- **Bug Report**: `/docs/project_plans/bugs/marketplace-sources-non_skills-v1.md`
- **Key File**: `skillmeat/core/marketplace/heuristic_detector.py`

**Complexity**: Medium
**Total Estimated Effort**: 16 story points
**Target Timeline**: Single phase (bug fix)

## Executive Summary

The marketplace source detection system currently misclassifies non-skill artifacts (Commands, Agents, Hooks, MCP Servers) as Skills. The root cause is that container directory logic incorrectly skips parent directories (like `commands/`) and then evaluates children without proper type context. Additionally, there's no content/frontmatter validation to confirm artifact type.

**Fix Strategy**:
1. Improve container directory handling to propagate type hints to children
2. Add frontmatter content parsing to validate artifact types
3. Increase weight of directory structure signals for non-skill types
4. Add `organization_path` field to capture directory structure between container and artifact
5. Add comprehensive tests for multi-type detection scenarios

## Root Cause Analysis

From codebase exploration:

### Issue 1: Container Directory Skip Logic (HIGH)
**File**: `heuristic_detector.py:160-190`
**Problem**: When a directory like `commands/` is detected as a container, it's skipped. Children are then evaluated independently without the parent's type context.
**Effect**: `commands/git/COMMAND.md` loses the `commands/` parent hint.

### Issue 2: No Frontmatter Content Validation (HIGH)
**File**: `heuristic_detector.py:383-399`
**Problem**: Manifest detection only checks file presence, not content.
**Effect**: A directory with `SKILL.md` is assumed to be a skill even if the file says `type: command`.

### Issue 3: Parent Hint Matching Too Weak (MEDIUM)
**File**: `heuristic_detector.py:513-551`
**Problem**: Parent hint only contributes 15 points vs directory name's 10 points.
**Effect**: Deep nesting dilutes parent hint signal below threshold.

### Issue 4: Depth Penalty Applied Uniformly (MEDIUM)
**File**: `heuristic_detector.py:553-583`
**Problem**: Depth penalty doesn't consider that nested artifacts in typed containers are valid.
**Effect**: `commands/dev/feature-command/COMMAND.md` gets penalized for depth.

## Implementation Strategy

### Approach

1. **Propagate Type Context**: When a container directory is identified, propagate its implied type to child directories
2. **Parse Frontmatter**: Read and parse YAML frontmatter from manifest files to validate type claims
3. **Adjust Signal Weights**: Increase parent hint weight for typed containers
4. **Reduce False Depth Penalties**: Don't penalize depth when inside a typed container

### Files to Modify

| File | Changes | Priority |
|------|---------|----------|
| `skillmeat/core/marketplace/heuristic_detector.py` | Container logic, frontmatter parsing, scoring, organization_path | P0 |
| `skillmeat/api/schemas/marketplace.py` | Add `organization_path` field to HeuristicMatch | P0 |
| `tests/core/marketplace/test_heuristic_detector.py` | New test cases including organization_path | P0 |

## Phase 1: Detection Algorithm Fix

**Duration**: 1 sprint
**Dependencies**: None
**Assigned Subagent(s)**: python-backend-engineer

### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| FIX-001 | Container Type Propagation | Modify `_is_container_directory` to return the implied type, propagate to child scoring | Children inherit parent container type as strong hint | 3 pts | python-backend-engineer | None |
| FIX-002 | Frontmatter Parsing | Add `_parse_manifest_frontmatter` to read YAML frontmatter from manifest files and extract `type:` field | Type from frontmatter overrides heuristic detection | 3 pts | python-backend-engineer | None |
| FIX-003 | Scoring Weight Adjustment | Increase parent_hint_weight from 15 to 25 for typed containers; reduce depth penalty when inside typed container | Non-skill types score correctly in their containers | 2 pts | python-backend-engineer | FIX-001 |
| FIX-004 | Organization Path Metadata | Add `organization_path` field to HeuristicMatch schema; compute and populate with path segments between container and artifact | Field captures 'dev' for commands/dev/execute-phase.md | 3 pts | python-backend-engineer | FIX-001 |
| FIX-005 | Multi-Type Test Suite | Add comprehensive tests for Commands, Agents, Hooks, MCP in various directory structures including organization_path | 100% pass rate for all artifact types, organization_path populated correctly | 3 pts | python-backend-engineer | FIX-001, FIX-002, FIX-003, FIX-004 |
| FIX-006 | Regression Testing | Run full test suite, verify existing skill detection unchanged | No regressions in skill detection | 2 pts | python-backend-engineer | FIX-005 |

### Detailed Task Specifications

#### FIX-001: Container Type Propagation

**Current Behavior**:
```python
def _is_container_directory(self, dir_name: str) -> bool:
    return dir_name.lower() in {"commands", "agents", "skills", "hooks", "rules", "mcp"}
```

**Target Behavior**:
```python
def _get_container_type(self, dir_name: str) -> Optional[ArtifactType]:
    """Return the implied artifact type if this is a typed container."""
    mapping = {
        "commands": ArtifactType.COMMAND,
        "command": ArtifactType.COMMAND,
        "agents": ArtifactType.AGENT,
        "agent": ArtifactType.AGENT,
        "skills": ArtifactType.SKILL,
        "skill": ArtifactType.SKILL,
        "hooks": ArtifactType.HOOK,
        "hook": ArtifactType.HOOK,
        "mcp": ArtifactType.MCP_SERVER,
        "mcp-servers": ArtifactType.MCP_SERVER,
    }
    return mapping.get(dir_name.lower())
```

**Integration Point**: Pass container type hint to `_score_directory` when analyzing children.

#### FIX-002: Frontmatter Parsing

**New Method**:
```python
def _parse_manifest_frontmatter(self, manifest_content: str) -> Optional[str]:
    """Extract artifact type from YAML frontmatter in manifest file."""
    # Parse YAML frontmatter (--- delimited)
    # Return value of 'type:' field if present
    # Return None if no frontmatter or no type field
```

**Integration Points**:
- Call during manifest scoring phase
- Type from frontmatter should have weight 30 (highest signal)

#### FIX-003: Scoring Weight Adjustment

**Changes to DetectionConfig**:
```python
# Current
parent_hint_weight: int = 15

# New
parent_hint_weight: int = 15  # Base weight
container_hint_weight: int = 25  # When parent is typed container
frontmatter_type_weight: int = 30  # When frontmatter has explicit type
```

**Depth Penalty Modification**:
```python
# Don't apply depth penalty if within typed container
if container_type is not None:
    depth_penalty = 0  # or reduced penalty
```

#### FIX-004: Organization Path Metadata

**Purpose**: Capture the directory structure between the container and the artifact for future filtering, auto-tagging, and organizational context.

**Schema Addition** (in `skillmeat/api/schemas/marketplace.py`):
```python
class HeuristicMatch(BaseModel):
    # ... existing fields ...
    path: str  # Full path (unchanged)
    organization_path: Optional[str] = Field(
        default=None,
        description="Path segments between container directory and artifact, e.g., 'dev' for commands/dev/execute-phase.md",
        examples=["dev", "ui-ux", "dev/subgroup"],
    )
```

**Computation Logic** (in `heuristic_detector.py`):
```python
def _compute_organization_path(
    self,
    artifact_path: str,
    container_dir: str,
    container_type: ArtifactType
) -> Optional[str]:
    """
    Extract the path segments between container and artifact.

    Examples:
      - commands/dev/execute-phase.md → "dev"
      - commands/test.md → None (directly in container)
      - agents/ui-ux/ui-designer.md → "ui-ux"
      - commands/dev/subgroup/my-cmd.md → "dev/subgroup"
      - skills/planning/SKILL.md → None (planning IS the artifact)
    """
    # Get path relative to container
    # Strip artifact name (file or artifact directory)
    # Return intermediate path or None
```

**Examples**:

| Full Path | Container | Artifact | organization_path |
|-----------|-----------|----------|-------------------|
| `commands/dev/execute-phase.md` | `commands/` | `execute-phase.md` | `dev` |
| `commands/test.md` | `commands/` | `test.md` | `None` |
| `commands/dev/subgroup/my-cmd.md` | `commands/` | `my-cmd.md` | `dev/subgroup` |
| `agents/ui-ux/ui-designer.md` | `agents/` | `ui-designer.md` | `ui-ux` |
| `skills/planning/SKILL.md` | `skills/` | `planning/` | `None` |

**Integration Points**:
- Compute during `_score_directory` when container_type is known
- Store in HeuristicMatch result
- Propagate to catalog entries for downstream use

#### FIX-005: Multi-Type Test Suite

**Test Scenarios to Add**:

1. **Commands in `commands/` container**:
   ```
   commands/
     git/
       COMMAND.md
     dev/
       feature.md
   ```
   Expected: Both detected as COMMAND

2. **Agents in `agents/` container**:
   ```
   agents/
     helper/
       AGENT.md
     assistant/
       AGENT.md
   ```
   Expected: Both detected as AGENT

3. **Nested type directories (plugin structure)**:
   ```
   claude-plugin/
     commands/
       cmd1/
         COMMAND.md
     skills/
       skill1/
         SKILL.md
   ```
   Expected: cmd1 = COMMAND, skill1 = SKILL

4. **Frontmatter override**:
   ```
   skills/
     actually-a-command/
       SKILL.md  # contains "type: command" in frontmatter
   ```
   Expected: Detected as COMMAND (frontmatter wins)

5. **Mixed types at same level**:
   ```
   artifacts/
     my-skill/
       SKILL.md
     my-command/
       COMMAND.md
     my-agent/
       AGENT.md
   ```
   Expected: Each detected correctly by manifest

6. **Organization path - nested commands**:
   ```
   commands/
     dev/
       execute-phase.md
       create-feature.md
     test/
       run-tests.md
   ```
   Expected:
   - `execute-phase.md` → COMMAND, organization_path="dev"
   - `create-feature.md` → COMMAND, organization_path="dev"
   - `run-tests.md` → COMMAND, organization_path="test"

7. **Organization path - deeply nested**:
   ```
   commands/
     dev/
       subgroup/
         my-command.md
   ```
   Expected: `my-command.md` → COMMAND, organization_path="dev/subgroup"

8. **Organization path - direct in container**:
   ```
   commands/
     test.md
   ```
   Expected: `test.md` → COMMAND, organization_path=None

9. **Organization path - agents with grouping**:
   ```
   agents/
     ui-ux/
       ui-designer.md
       ux-researcher.md
   ```
   Expected:
   - `ui-designer.md` → AGENT, organization_path="ui-ux"
   - `ux-researcher.md` → AGENT, organization_path="ui-ux"

10. **Organization path - skills (directory is artifact)**:
    ```
    skills/
      planning/
        SKILL.md
        README.md
    ```
    Expected: `planning/` → SKILL, organization_path=None (planning IS the artifact)

### Quality Gates

- [ ] All existing tests pass (no regressions)
- [ ] New multi-type tests pass (100%)
- [ ] Commands detection accuracy ≥95%
- [ ] Agents detection accuracy ≥95%
- [ ] Hooks detection accuracy ≥95%
- [ ] MCP Servers detection accuracy ≥95%
- [ ] `organization_path` field populated correctly for all detected artifacts
- [ ] Test coverage for heuristic_detector.py >85%

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Skill detection regression | High | Medium | Run full test suite before/after, add regression tests |
| Frontmatter parsing edge cases | Medium | Medium | Handle malformed YAML gracefully, default to heuristic |
| Performance impact from frontmatter reads | Low | Low | Only read frontmatter for manifest files already detected |

### Schedule Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Scope creep to schema changes | Medium | Medium | Keep changes focused on detector, defer schema updates |

---

## Success Metrics

### Technical Metrics
- Zero regressions in existing skill detection
- ≥95% detection accuracy for all artifact types
- Test coverage ≥85% for heuristic_detector.py

### Business Metrics
- Users can import Commands, Agents, Hooks, MCP Servers from marketplace sources

---

## Orchestration Quick Reference

**Batch 1** (Parallel - no dependencies):
- FIX-001 → `python-backend-engineer` (3 pts) - Container Type Propagation
- FIX-002 → `python-backend-engineer` (3 pts) - Frontmatter Parsing

**Batch 2** (After Batch 1, parallel):
- FIX-003 → `python-backend-engineer` (2 pts) [depends: FIX-001] - Scoring Weights
- FIX-004 → `python-backend-engineer` (3 pts) [depends: FIX-001] - Organization Path

**Batch 3** (After Batch 2):
- FIX-005 → `python-backend-engineer` (3 pts) [depends: FIX-001, FIX-002, FIX-003, FIX-004] - Multi-Type Tests

**Batch 4** (After Batch 3):
- FIX-006 → `python-backend-engineer` (2 pts) [depends: FIX-005] - Regression Testing

### Task Delegation Commands

```python
# Batch 1 (run in parallel)
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

# Batch 2 (after Batch 1, run in parallel)
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

Task("python-backend-engineer", """FIX-004: Organization Path Metadata

Add organization_path field to capture directory structure between container and artifact.

1. Update skillmeat/api/schemas/marketplace.py - Add to HeuristicMatch:
   organization_path: Optional[str] = Field(
       default=None,
       description="Path segments between container directory and artifact",
       examples=["dev", "ui-ux", "dev/subgroup"],
   )

2. Add method to skillmeat/core/marketplace/heuristic_detector.py:
   def _compute_organization_path(self, artifact_path: str, container_dir: str) -> Optional[str]:
       # Get path relative to container
       # Strip artifact name (file or directory)
       # Return intermediate path segments or None if directly in container

3. Call _compute_organization_path when building HeuristicMatch results

Examples:
- commands/dev/execute-phase.md → organization_path="dev"
- commands/test.md → organization_path=None
- commands/dev/subgroup/my-cmd.md → organization_path="dev/subgroup"
- agents/ui-ux/ui-designer.md → organization_path="ui-ux"
- skills/planning/SKILL.md → organization_path=None (planning IS the artifact)

Reference: HeuristicMatch class, analyze_paths method
""")

# Batch 3 (after Batch 2)
Task("python-backend-engineer", """FIX-005: Multi-Type Test Suite

Add tests to tests/core/marketplace/test_heuristic_detector.py:

New test class: TestMultiTypeDetection

Test cases for type detection:
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

Test cases for organization_path:
11. test_organization_path_nested - commands/dev/execute-phase.md → "dev"
12. test_organization_path_direct - commands/test.md → None
13. test_organization_path_deeply_nested - commands/dev/subgroup/my-cmd.md → "dev/subgroup"
14. test_organization_path_agents - agents/ui-ux/ui-designer.md → "ui-ux"
15. test_organization_path_skills - skills/planning/SKILL.md → None

Each test should verify:
- Correct artifact_type detection
- Correct organization_path value
- Confidence score ≥ 70 for typed containers
- No false positives for other types
""")

# Batch 4 (after Batch 3)
Task("python-backend-engineer", """FIX-006: Regression Testing

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

**Progress Tracking**: See `.claude/progress/marketplace-sources-non_skills-v1/phase-1-progress.md`

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2025-12-31
