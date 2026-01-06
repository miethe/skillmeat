---
type: progress
prd: "artifact-detection-standardization"
phase: 4
phase_title: "Align Validators and CLI Defaults"
status: pending
progress: 0
total_tasks: 10
completed_tasks: 0
story_points: 10
duration: "1 week"

tasks:
  - id: "TASK-4.1"
    title: "Analyze Current validator.py"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: []
    story_points: 1
    description: "Understand current validation logic"

  - id: "TASK-4.2"
    title: "Import Shared Components to validator.py"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-4.1"]
    story_points: 1
    description: "Add imports from shared detection module"

  - id: "TASK-4.3"
    title: "Refactor validator.py to Use Shared Signatures"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-4.2"]
    story_points: 3
    description: "Replace ad-hoc validation with ARTIFACT_SIGNATURES"

  - id: "TASK-4.4"
    title: "Implement Type Validation and Normalization"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-4.3"]
    story_points: 2
    description: "normalize_artifact_type() and validate_artifact_type()"

  - id: "TASK-4.5"
    title: "Deprecation Warning Support in Validators"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-4.3", "TASK-4.4"]
    story_points: 1
    description: "Warn for legacy directory-based patterns"

  - id: "TASK-4.6"
    title: "Analyze Current defaults.py"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: []
    story_points: 1
    description: "Understand CLI type inference logic"

  - id: "TASK-4.7"
    title: "Refactor defaults.py to Use Shared Inference"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-4.6"]
    story_points: 2
    description: "Route through shared infer_artifact_type()"

  - id: "TASK-4.8"
    title: "Update validator.py Tests"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-4.3", "TASK-4.4", "TASK-4.5"]
    story_points: 1
    description: "Update tests for shared signatures"

  - id: "TASK-4.9"
    title: "Update defaults.py Tests"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-4.7"]
    story_points: 1
    description: "Update tests for shared inference"

  - id: "TASK-4.10"
    title: "Documentation for Validators and Defaults"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-4.8", "TASK-4.9"]
    story_points: 1
    description: "Update docstrings and documentation"

parallelization:
  batch_1: ["TASK-4.1", "TASK-4.6"]
  batch_2: ["TASK-4.2", "TASK-4.7"]
  batch_3: ["TASK-4.3"]
  batch_4: ["TASK-4.4"]
  batch_5: ["TASK-4.5", "TASK-4.8", "TASK-4.9"]
  batch_6: ["TASK-4.10"]

blockers:
  - description: "Phase 1 must be complete"
    blocking_tasks: ["TASK-4.1", "TASK-4.6"]
    status: "active"

notes:
  - "Can run in parallel with Phases 2 and 3 after Phase 1 completes"
---

# Phase 4: Align Validators and CLI Defaults

## Overview

Align `validator.py` and `defaults.py` with the unified detection system. Replace ad-hoc validation with shared signatures and route CLI defaults through shared inference.

## Prerequisites

- Phase 1 complete (artifact_detection.py created)
- Note: Can run in parallel with Phases 2 and 3

## Key Outputs

- Updated `skillmeat/utils/validator.py`
- Updated `skillmeat/defaults.py`
- Type normalization functions
- Updated tests

## Orchestration Quick Reference

**Batch 1** (Parallel - start after Phase 1):
```python
Task("python-backend-engineer", """TASK-4.1: Analyze Current validator.py

Analyze skillmeat/utils/validator.py:
1. Understand validation for each type (SKILL, COMMAND, AGENT, HOOK, MCP)
2. Identify validation rules: manifest files, directory structure
3. Map current logic to ARTIFACT_SIGNATURES
4. Identify edge cases and special rules
5. Document type name handling (snake_case, enum, strings)""")

Task("python-backend-engineer", """TASK-4.6: Analyze Current defaults.py

Analyze skillmeat/defaults.py:
1. Understand name-based type inference:
   - "-cli", "-cmd", "-command" -> COMMAND
   - "-agent", "-bot" -> AGENT
   - Fallback: SKILL
2. Identify all inference rules
3. Map to shared infer_artifact_type()""")
```

**Batch 2** (After batch 1):
```python
Task("python-backend-engineer", """TASK-4.2: Import Shared Components to validator.py

Update skillmeat/utils/validator.py:
1. Add imports:
   from skillmeat.core.artifact_detection import (
       ArtifactType, ARTIFACT_SIGNATURES, extract_manifest_file
   )
2. Verify no circular imports
3. All imports accessible""")

Task("python-backend-engineer", """TASK-4.7: Refactor defaults.py to Use Shared Inference

Update skillmeat/defaults.py:
1. Import infer_artifact_type() from shared module
2. Refactor CLI default functions to use shared inference
3. Maintain name-based heuristics as fallback
4. Return ArtifactType enum (not string)
5. All defaults tests must pass""")
```

**Batch 3** (After TASK-4.2):
```python
Task("python-backend-engineer", """TASK-4.3: Refactor validator.py to Use Shared Signatures

Update skillmeat/utils/validator.py:
1. New validation structure:
   def validate_artifact(path, artifact_type):
       sig = ARTIFACT_SIGNATURES[artifact_type]
       # Check is_directory matches sig.is_directory
       # Check manifest requirements (if sig.requires_manifest)
       # Check other structural rules

2. All type validators use shared signatures
3. Manifest files located via extract_manifest_file()
4. Clear validation messages
5. All existing validation tests must pass""")
```

**Batch 4** (After TASK-4.3):
```python
Task("python-backend-engineer", """TASK-4.4: Implement Type Validation and Normalization

Add to validator.py:
1. normalize_artifact_type(type_value) -> ArtifactType
   - Accepts: ArtifactType enum, strings, snake_case
   - Returns: ArtifactType enum
   - Raises: InvalidArtifactTypeError if invalid

2. validate_artifact_type(type_value) -> bool
   - Returns True/False for validity

3. Support both "mcp" and "mcp_server" for backwards compat
4. Clear error messages
5. Comprehensive docstrings with examples""")
```

**Batch 5** (Parallel - after batch 4):
```python
Task("python-backend-engineer", """TASK-4.5: Deprecation Warning Support in Validators

Update validator.py:
1. Detect when command/agent is directory (legacy)
2. Include deprecation_warning in ValidationResult
3. Clear, actionable warning message
4. Warnings toggleable via config
5. Legacy artifacts still validate (valid=True, deprecation_warning=True)
6. Tests verify deprecation warnings""")

Task("python-backend-engineer", """TASK-4.8: Update validator.py Tests

Update tests/utils/test_validator.py:
1. All existing tests must pass
2. Fixtures use ArtifactType enum
3. Assertions verify correct validation results
4. Mock/patch points updated for shared signatures
5. New tests for type normalization
6. New tests for deprecation warnings""")

Task("python-backend-engineer", """TASK-4.9: Update defaults.py Tests

Update tests for defaults.py:
1. All existing tests must pass
2. Assertions verify ArtifactType enum returns
3. New tests verify shared inference usage
4. Name-based heuristics still work
5. Fallback behavior tested""")
```

**Batch 6** (After batch 5):
```python
Task("python-backend-engineer", """TASK-4.10: Documentation for Validators and Defaults

Update documentation:
1. validator.py docstrings explain shared signature usage
2. All validation functions have clear docstrings
3. defaults.py functions documented with examples
4. Type normalization documented with examples
5. Deprecation warnings documented
6. Reference to shared detection module""")
```

## Quality Gates

- [ ] All 10 tasks completed
- [ ] No linting errors
- [ ] All existing validator tests pass
- [ ] All existing defaults tests pass
- [ ] New type normalization tests pass
- [ ] >85% coverage on refactored modules
- [ ] No circular imports

## Files to Modify

| Action | File |
|--------|------|
| MODIFY | `skillmeat/utils/validator.py` |
| MODIFY | `skillmeat/defaults.py` |
| MODIFY | `tests/utils/test_validator.py` |
