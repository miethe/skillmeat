---
type: progress
prd: "artifact-detection-standardization"
phase: 3
phase_title: "Refactor Marketplace Heuristics Detection"
status: pending
progress: 0
total_tasks: 10
completed_tasks: 0
story_points: 18
duration: "2 weeks"

tasks:
  - id: "TASK-3.1"
    title: "Analyze Current heuristic_detector.py"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: []
    story_points: 2
    description: "Deep analysis of 7-signal scoring system"

  - id: "TASK-3.2"
    title: "Remove Duplicate ArtifactType Enum"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-3.1"]
    story_points: 1
    description: "Import from shared module instead"

  - id: "TASK-3.3"
    title: "Import Shared Detection Components"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-3.2"]
    story_points: 2
    description: "Wire up shared signatures, aliases, functions"

  - id: "TASK-3.4"
    title: "Refactor Confidence Scoring Architecture"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-3.1", "TASK-3.3"]
    story_points: 4
    description: "Separate baseline detection from marketplace signals"

  - id: "TASK-3.5"
    title: "Implement Baseline Detection"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-3.4"]
    story_points: 2
    description: "Call shared detect_artifact() for baseline"

  - id: "TASK-3.6"
    title: "Implement Marketplace Confidence Scoring"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-3.4", "TASK-3.5"]
    story_points: 3
    description: "GitHub heuristics, depth penalties, scoring"

  - id: "TASK-3.7"
    title: "Maintain Manual Directory Mapping"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-3.6"]
    story_points: 2
    description: "Ensure manual overrides still work"

  - id: "TASK-3.8"
    title: "Update Marketplace Tests"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-3.5", "TASK-3.6", "TASK-3.7"]
    story_points: 2
    description: "Update all tests for refactored scoring"

  - id: "TASK-3.9"
    title: "Integration Testing"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-3.8"]
    story_points: 1
    description: "Cross-module tests with Phase 1 & 2"

  - id: "TASK-3.10"
    title: "Documentation and Comments"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-3.9"]
    story_points: 1
    description: "Explain baseline + marketplace architecture"

parallelization:
  batch_1: ["TASK-3.1"]
  batch_2: ["TASK-3.2"]
  batch_3: ["TASK-3.3"]
  batch_4: ["TASK-3.4"]
  batch_5: ["TASK-3.5"]
  batch_6: ["TASK-3.6"]
  batch_7: ["TASK-3.7"]
  batch_8: ["TASK-3.8"]
  batch_9: ["TASK-3.9"]
  batch_10: ["TASK-3.10"]

blockers:
  - description: "Phase 1 must be complete"
    blocking_tasks: ["TASK-3.1"]
    status: "active"

notes:
  - "Can run in parallel with Phase 2 after Phase 1 completes"
  - "Confidence scores must match pre-refactor behavior"
---

# Phase 3: Refactor Marketplace Heuristics Detection

## Overview

Refactor `heuristic_detector.py` to reuse 80%+ of detection logic from Phase 1's shared core while maintaining marketplace-specific confidence scoring and manual mapping features.

## Prerequisites

- Phase 1 complete (artifact_detection.py created)
- Note: Can run in parallel with Phase 2

## Key Outputs

- Refactored `skillmeat/core/marketplace/heuristic_detector.py`
- Duplicate ArtifactType enum removed
- Confidence scoring rewritten with shared baseline
- Updated marketplace tests

## Orchestration Quick Reference

**Batch 1** (Start after Phase 1 complete):
```python
Task("python-backend-engineer", """TASK-3.1: Analyze Current heuristic_detector.py

Deep analysis of skillmeat/core/marketplace/heuristic_detector.py:
1. Understand 7-signal scoring system:
   - dir_name, manifest, extensions, parent_hint, frontmatter, container_hint, frontmatter_type
2. Document scoring weights for each signal
3. Understand manual mapping mechanism
4. Understand GitHub path heuristics (depth penalties)
5. Identify shared vs marketplace-specific signals
6. Create mapping: old 7-signal -> new hybrid architecture""")
```

**Batch 2** (After TASK-3.1):
```python
Task("python-backend-engineer", """TASK-3.2: Remove Duplicate ArtifactType Enum

In skillmeat/core/marketplace/heuristic_detector.py:
1. Locate and remove duplicate ArtifactType enum
2. Add: from skillmeat.core.artifact_detection import ArtifactType
3. Update all references to imported enum
4. Update type hints throughout
5. All marketplace tests must still pass""")
```

**Batch 3** (After TASK-3.2):
```python
Task("python-backend-engineer", """TASK-3.3: Import Shared Detection Components

In skillmeat/core/marketplace/heuristic_detector.py:
1. Add imports:
   from skillmeat.core.artifact_detection import (
       ArtifactType, DetectionResult, ARTIFACT_SIGNATURES,
       CONTAINER_ALIASES, normalize_container_name,
       detect_artifact, extract_manifest_file
   )
2. Remove any local implementations duplicating shared code
3. Update type hints to use shared dataclasses
4. Verify no circular imports""")
```

**Batch 4** (After TASK-3.3):
```python
Task("python-backend-engineer", """TASK-3.4: Refactor Confidence Scoring Architecture

Redesign scoring in heuristic_detector.py:
1. Create _get_baseline_detection(path, container_type) -> DetectionResult
   - Calls detect_artifact(path, mode="heuristic")

2. Create _calculate_marketplace_confidence(result, path, ...) -> int
   - Takes baseline DetectionResult
   - Applies marketplace-specific signals
   - Returns final confidence 0-100

3. Identify and isolate marketplace signals:
   - GitHub path depth penalties
   - Manual mapping overrides
   - Signature completeness scoring

4. Document scoring weights with comments""")
```

**Batch 5** (After TASK-3.4):
```python
Task("python-backend-engineer", """TASK-3.5: Implement Baseline Detection

In heuristic_detector.py:
1. Implement _get_baseline_detection() method
2. Call detect_artifact(path, mode="heuristic")
3. Pass container_type hint to shared detector
4. Handle cases where shared detector returns 0% confidence
5. Preserve detection_reasons from shared module
6. Add logging for debugging
7. Unit tests for baseline detection""")
```

**Batch 6** (After TASK-3.5):
```python
Task("python-backend-engineer", """TASK-3.6: Implement Marketplace Confidence Scoring

In heuristic_detector.py:
1. Implement _calculate_marketplace_confidence() with signals:
   - GitHub path heuristics (depth penalties)
   - Manual mapping overrides
   - Signature completeness
   - Frontmatter confidence
   - Container hint confidence
   - Extension scoring
2. Document scoring weights
3. Backwards compatible: same artifacts score similarly
4. Unit tests for each signal""")
```

**Batch 7** (After TASK-3.6):
```python
Task("python-backend-engineer", """TASK-3.7: Maintain Manual Directory Mapping

Ensure manual mapping still works:
1. Manual mapping configuration accessible
2. Overrides applied after baseline detection
3. Manual mapping = 100% confidence (full override)
4. Tests verify manual mappings work
5. Documentation updated""")
```

**Batch 8** (After batch 7):
```python
Task("python-backend-engineer", """TASK-3.8: Update Marketplace Tests

Update tests/core/marketplace/test_heuristic_detector.py:
1. All existing tests must pass
2. Update fixtures for refactored scoring
3. Confidence score assertions verified
4. New tests for baseline + marketplace separation
5. Manual mapping tests pass
6. GitHub heuristics tests pass""")
```

**Batch 9** (After TASK-3.8):
```python
Task("python-backend-engineer", """TASK-3.9: Integration Testing

Create tests/core/integration/test_detection_cross_module.py:
1. Same artifact detected consistently across layers
2. Marketplace confidence > local confidence for ambiguous cases
3. Cross-module type consistency
4. Detection reasons traceable
5. Performance benchmark before/after""")
```

**Batch 10** (After TASK-3.9):
```python
Task("python-backend-engineer", """TASK-3.10: Documentation and Comments

Update heuristic_detector.py:
1. Module docstring explains baseline + marketplace architecture
2. Scoring system documented with signal explanation
3. All public methods have docstrings
4. Comments explain scoring logic
5. Reference to shared detection module""")
```

## Quality Gates

- [ ] All 10 tasks completed
- [ ] No linting errors
- [ ] Duplicate ArtifactType enum removed
- [ ] All existing marketplace tests pass
- [ ] 80%+ detection logic reuses shared module
- [ ] Confidence scores match pre-refactor behavior
- [ ] Manual mappings work correctly

## Files to Modify

| Action | File |
|--------|------|
| MODIFY | `skillmeat/core/marketplace/heuristic_detector.py` |
| MODIFY | `tests/core/marketplace/test_heuristic_detector.py` |
| CREATE | `tests/core/integration/test_detection_cross_module.py` |
