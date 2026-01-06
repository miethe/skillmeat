---
type: progress
prd: "artifact-detection-standardization"
phase: 2
phase_title: "Rebuild Local Discovery with Shared Detector"
status: completed
progress: 100
total_tasks: 9
completed_tasks: 9
completed_at: "2026-01-06"
story_points: 12
duration: "1 week"

tasks:
  - id: "TASK-2.1"
    title: "Analyze Current discovery.py"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: []
    story_points: 2
    description: "Analyze current detection logic and create migration plan"

  - id: "TASK-2.2"
    title: "Import and Wire Shared Module"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-2.1"]
    story_points: 2
    description: "Update imports to use shared detection module"

  - id: "TASK-2.3"
    title: "Replace _detect_artifact_type()"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-2.2"]
    story_points: 3
    description: "Replace with detect_artifact() from shared module"

  - id: "TASK-2.4"
    title: "Add Recursive Directory Traversal"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-2.3"]
    story_points: 3
    description: "Detect nested single-file artifacts in subdirectories"

  - id: "TASK-2.5"
    title: "Implement Deprecation Warnings"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-2.3"]
    story_points: 2
    description: "Warn for directory-based commands/agents"

  - id: "TASK-2.6"
    title: "Update Discovery Tests"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-2.3", "TASK-2.4", "TASK-2.5"]
    story_points: 2
    description: "Update existing tests for shared detector"

  - id: "TASK-2.7"
    title: "Write Nested Discovery Tests"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-2.4"]
    story_points: 2
    description: "10+ tests for nested artifact discovery"

  - id: "TASK-2.8"
    title: "Integration Testing"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-2.6", "TASK-2.7"]
    story_points: 1
    description: "Integration tests with Phase 1 module"

  - id: "TASK-2.9"
    title: "Update Documentation"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-2.8"]
    story_points: 1
    description: "Docstrings for refactored discovery.py"

parallelization:
  batch_1: ["TASK-2.1"]
  batch_2: ["TASK-2.2"]
  batch_3: ["TASK-2.3"]
  batch_4: ["TASK-2.4", "TASK-2.5"]
  batch_5: ["TASK-2.6", "TASK-2.7"]
  batch_6: ["TASK-2.8"]
  batch_7: ["TASK-2.9"]

blockers:
  - description: "Phase 1 must be complete"
    blocking_tasks: ["TASK-2.1", "TASK-2.2", "TASK-2.3"]
    status: "active"

notes: []
---

# Phase 2: Rebuild Local Discovery with Shared Detector

## Overview

Rebuild `discovery.py` to use the unified detection module from Phase 1. Replace fragmented detection with shared detector, add recursive traversal, and implement deprecation warnings.

## Prerequisites

- Phase 1 complete (artifact_detection.py created)
- All Phase 1 tests passing

## Key Outputs

- Updated `skillmeat/core/discovery.py`
- Recursive nested artifact detection
- Deprecation warnings for legacy patterns
- Updated discovery tests

## Orchestration Quick Reference

**Batch 1** (Start after Phase 1 complete):
```python
Task("python-backend-engineer", """TASK-2.1: Analyze Current discovery.py

Analyze skillmeat/core/discovery.py to understand:
1. Current _detect_artifact_type() implementation
2. Container type inference logic
3. Traversal depth (recursive vs non-recursive)
4. Edge cases and special handling

Create migration plan mapping old detection to shared module functions.
Document current performance characteristics.""")
```

**Batch 2** (After TASK-2.1):
```python
Task("python-backend-engineer", """TASK-2.2: Import and Wire Shared Module

Update skillmeat/core/discovery.py:
1. Add imports:
   from skillmeat.core.artifact_detection import (
       ArtifactType, DetectionResult, detect_artifact,
       ARTIFACT_SIGNATURES, normalize_container_name
   )
2. Replace string type names with ArtifactType enum
3. Update LocalArtifact.type to use ArtifactType
4. Update all type hints
5. Verify no circular imports""")
```

**Batch 3** (After TASK-2.2):
```python
Task("python-backend-engineer", """TASK-2.3: Replace _detect_artifact_type()

In skillmeat/core/discovery.py:
1. Create new _detect_artifact() method calling detect_artifact(path, mode="strict")
2. Parse DetectionResult into LocalArtifact
3. Log deprecation warnings from DetectionResult
4. Use normalize_container_name() for container inference
5. Remove or deprecate old _detect_artifact_type()
6. No change to DiscoveryManager public API""")
```

**Batch 4** (Parallel - after TASK-2.3):
```python
Task("python-backend-engineer", """TASK-2.4: Add Recursive Directory Traversal

In skillmeat/core/discovery.py:
1. Implement _discover_nested_artifacts(container_path, container_type)
2. Recursively scan subdirectories under containers
3. Detect nested commands/agents in folders
4. Respect allowed_nesting flag from ARTIFACT_SIGNATURES
5. Add depth limit (max 3-5 levels)
6. Backwards compatible (flat structure still works)""")

Task("python-backend-engineer", """TASK-2.5: Implement Deprecation Warnings

In skillmeat/core/discovery.py:
1. Detect when command/agent is directory (legacy)
2. Log warning with:
   - Location of legacy artifact
   - Recommended migration
   - Timeline (v1.0.0)
   - Link to migration guide
3. Legacy artifacts still discovered (backwards compatible)
4. Make warnings toggleable via config""")
```

**Batch 5** (Parallel - after batch 4):
```python
Task("python-backend-engineer", """TASK-2.6: Update Discovery Tests

Update tests/core/test_discovery.py:
1. All existing tests must pass
2. Update fixtures to use ArtifactType enum
3. Test assertions verify enum values
4. Update mock/patch points for new flow
5. Add backwards compatibility tests""")

Task("python-backend-engineer", """TASK-2.7: Write Nested Discovery Tests

Create 10+ tests in tests/core/test_discovery.py:
1. Detect nested commands in subdirs
2. Detect nested agents in subdirs
3. Skip nested skills (not allowed)
4. Handle multiple nesting levels
5. Handle empty directories
6. Edge cases (symlinks, special chars)""")
```

**Batch 6** (After batch 5):
```python
Task("python-backend-engineer", """TASK-2.8: Integration Testing

Create tests/core/integration/test_discovery_phase1_integration.py:
1. Discovery uses shared detector functions
2. Detection results parsed correctly
3. Cross-module type consistency
4. Container normalization works
5. Performance benchmark before/after""")
```

**Batch 7** (After TASK-2.8):
```python
Task("python-backend-engineer", """TASK-2.9: Update Documentation

Update skillmeat/core/discovery.py:
1. Module docstring explains shared detector usage
2. DiscoveryManager docstring updated
3. All public methods documented
4. Comments explain recursive traversal
5. Reference to ARTIFACT_SIGNATURES""")
```

## Quality Gates

- [ ] All 9 tasks completed
- [ ] No linting errors
- [ ] All existing discovery tests pass
- [ ] New nested discovery tests pass
- [ ] >85% coverage on discovery.py
- [ ] No circular imports with Phase 1

## Files to Modify

| Action | File |
|--------|------|
| MODIFY | `skillmeat/core/discovery.py` |
| MODIFY | `tests/core/test_discovery.py` |
| CREATE | `tests/core/integration/test_discovery_phase1_integration.py` |
