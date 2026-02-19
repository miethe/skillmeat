---
status: inferred_complete
---
# Phase 3: Refactor Marketplace Heuristics Detection

**Duration:** 2 weeks
**Story Points:** 18
**Status:** Ready for Implementation
**Assigned To:** `python-backend-engineer` (Opus)

---

## Overview

Phase 3 refactors `heuristic_detector.py` to reuse 80%+ of detection logic from Phase 1's shared core while maintaining marketplace-specific confidence scoring and manual mapping features. Key changes:
- Remove duplicate `ArtifactType` enum
- Import and use shared signatures, aliases, and detection functions
- Rewrite confidence scoring to use shared baseline + marketplace extensions
- Keep manual directory mapping and GitHub heuristics
- Maintain backwards compatibility of scoring results

**Key Outputs:**
- Refactored `skillmeat/core/marketplace/heuristic_detector.py`
- Updated marketplace tests
- Verification that confidence scores match previous behavior

---

## Task Breakdown

### TASK-3.1: Analyze Current heuristic_detector.py Implementation
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** Phase 1 complete
**Story Points:** 2
**Effort:** 2-3 hours

**Description:**
Deep analysis of current heuristic_detector.py to understand:
- 7-signal scoring system
- Manual directory mapping override mechanism
- GitHub path heuristics
- Confidence scoring aggregation
- Edge cases and special handling

**Acceptance Criteria:**
- [ ] Understand current 7-signal scoring system:
  1. dir_name signal
  2. manifest signal
  3. extensions signal
  4. parent_hint signal
  5. frontmatter signal
  6. container_hint signal
  7. frontmatter_type signal
- [ ] Document scoring weights for each signal
- [ ] Understand manual mapping mechanism (how overrides work)
- [ ] Understand GitHub path heuristics (depth penalties, etc.)
- [ ] Identify which signals are "shared baseline" vs "marketplace-specific"
- [ ] Create mapping: old 7-signal system → new hybrid (shared + marketplace)

**Details:**
Current scoring distribution:
- Some signals are generic (manifest, dir_name) → shared baseline
- Some signals are marketplace-specific (GitHub path, frontmatter) → keep as extensions
- Confidence aggregation logic needs refactoring to separate concerns

---

### TASK-3.2: Remove Duplicate ArtifactType Enum
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-3.1, Phase 1 complete
**Story Points:** 1
**Effort:** 1-2 hours

**Description:**
Remove local `ArtifactType` enum from heuristic_detector.py and import from shared module.

**Acceptance Criteria:**
- [ ] Locate and remove duplicate ArtifactType enum in heuristic_detector.py
- [ ] Add import: `from skillmeat.core.artifact_detection import ArtifactType`
- [ ] Update all references from local enum to imported enum
- [ ] No breaking changes to MarketplaceDetector API (enum values same)
- [ ] Type hints updated throughout file
- [ ] All marketplace tests still pass

**Details:**
This is straightforward enum replacement. Should not affect logic, only imports/references.

---

### TASK-3.3: Import Shared Detection Components
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-3.2
**Story Points:** 2
**Effort:** 2-3 hours

**Description:**
Import all necessary shared components from Phase 1 module and wire them into heuristic_detector.py.

**Acceptance Criteria:**
- [ ] Add imports:
  ```python
  from skillmeat.core.artifact_detection import (
      ArtifactType, DetectionResult, ARTIFACT_SIGNATURES,
      CONTAINER_ALIASES, normalize_container_name,
      detect_artifact, extract_manifest_file
  )
  ```
- [ ] Remove any local implementations that duplicate shared code
- [ ] Update type hints to use shared dataclasses
- [ ] No circular imports
- [ ] All imports working and accessible

**Details:**
Key components to import:
- ARTIFACT_SIGNATURES: For manifest and structure rules
- CONTAINER_ALIASES: For directory name normalization
- normalize_container_name(): For standardizing container names
- detect_artifact(): For baseline detection (will extend with scoring)
- extract_manifest_file(): For manifest file location

---

### TASK-3.4: Refactor Confidence Scoring Architecture
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-3.1, TASK-3.3
**Story Points:** 4
**Effort:** 6-8 hours

**Description:**
Redesign confidence scoring to separate "shared baseline detection" from "marketplace-specific signals". Create new scoring module structure.

**Acceptance Criteria:**
- [ ] New method `_get_baseline_detection(path: Path, container_type: str) -> DetectionResult` implemented
  - Calls `detect_artifact(path, mode="heuristic")` from shared module
  - Returns baseline type and confidence
- [ ] New method `_calculate_marketplace_confidence(result: DetectionResult, path: Path, ...) -> int` implemented
  - Takes baseline DetectionResult
  - Applies marketplace-specific signals (GitHub heuristics, depth penalties)
  - Returns final confidence 0-100
- [ ] Marketplace signals identified and isolated:
  - GitHub path depth penalties
  - Manual mapping overrides
  - Signature completeness scoring
  - Confidence aggregation logic
- [ ] Scoring logic documented with comments explaining signal weights
- [ ] No changes to final confidence score distribution (backwards compatible)
- [ ] Comprehensive docstrings for scoring methods

**Details:**
New scoring flow:
```python
def detect(self, path: Path, container_type: str) -> DetectionResult:
    # Step 1: Get baseline detection from shared module
    baseline = self._get_baseline_detection(path, container_type)

    # Step 2: Apply marketplace-specific signals
    marketplace_confidence = self._calculate_marketplace_confidence(
        baseline, path, container_type
    )

    # Step 3: Return result with marketplace confidence
    result = DetectionResult(
        artifact_type=baseline.artifact_type,
        confidence=marketplace_confidence,
        detection_mode="heuristic",
        detection_reasons=baseline.detection_reasons + [marketplace signals]
    )
    return result
```

---

### TASK-3.5: Implement Baseline Detection Using Shared Module
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-3.4
**Story Points:** 2
**Effort:** 3-4 hours

**Description:**
Implement `_get_baseline_detection()` method that calls shared detection and handles marketplace context.

**Acceptance Criteria:**
- [ ] Method calls `detect_artifact(path, mode="heuristic")`
- [ ] Passes container_type hint to shared detector
- [ ] Returns DetectionResult from shared module
- [ ] Handles cases where shared detector returns None/0% confidence
- [ ] Preserves detection_reasons from shared module
- [ ] Logs baseline detection for debugging
- [ ] Error handling for detection failures
- [ ] Unit tests for baseline detection

**Details:**
This method should be thin wrapper around `detect_artifact()` with error handling and logging.

---

### TASK-3.6: Implement Marketplace-Specific Confidence Scoring
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-3.4, TASK-3.5
**Story Points:** 3
**Effort:** 4-5 hours

**Description:**
Implement `_calculate_marketplace_confidence()` with all marketplace-specific signals.

**Acceptance Criteria:**
- [ ] Marketplace signals implemented:
  1. **GitHub path heuristics**: Depth penalties, path patterns
  2. **Manual mapping overrides**: Apply configured overrides
  3. **Signature completeness**: Score based on matching artifact signature
  4. **Frontmatter confidence**: Additional signal from markdown metadata
  5. **Container hint confidence**: Signal from parent directory name
  6. **Extension scoring**: Additional signal from file types present
- [ ] Scoring weights documented and tuned
- [ ] Confidence aggregation logic clear and testable
- [ ] Backwards compatible: Same artifacts score similarly to Phase 3 start
- [ ] Comprehensive docstring with scoring explanation
- [ ] Unit tests for each signal

**Details:**
Signal weights should be tuned to match previous behavior. If Phase 2 had "dir_name=40, manifest=30, extensions=10, ...", ensure new implementation produces similar scores.

---

### TASK-3.7: Maintain Manual Directory Mapping
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-3.6
**Story Points:** 2
**Effort:** 2-3 hours

**Description:**
Ensure manual directory mapping overrides continue to work with refactored code.

**Acceptance Criteria:**
- [ ] Manual mapping configuration still accessible
- [ ] Overrides applied correctly after shared baseline detection
- [ ] Manual mapping takes precedence over heuristic scoring
- [ ] Manual mapping confidence is 100% (full override)
- [ ] Tests verify manual mappings work
- [ ] Documentation updated for manual mapping mechanism

**Details:**
Manual mapping example:
```python
# If /path/to/repo/.claude/commands/ is manually mapped to COMMAND
# Then all .md files in that directory are COMMAND artifacts
# Confidence = 100% (override, not heuristic)
```

---

### TASK-3.8: Update marketplace Tests
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-3.1-3.7
**Story Points:** 2
**Effort:** 3-4 hours

**Description:**
Update all marketplace heuristics tests to work with refactored implementation.

**Acceptance Criteria:**
- [ ] All existing marketplace tests pass (100% pass rate)
- [ ] Test fixtures updated for refactored scoring
- [ ] Mock/patch points updated for new architecture
- [ ] Confidence score assertions verified (should match pre-refactor)
- [ ] New tests for baseline + marketplace scoring separation
- [ ] Manual mapping tests still pass
- [ ] GitHub heuristics tests still pass
- [ ] No regression in test coverage

**Details:**
Tests should verify:
- Baseline detection matches shared module behavior
- Marketplace signals applied correctly
- Final confidence scores match previous implementation
- Manual mappings override correctly
- Edge cases handled (unknown types, etc.)

---

### TASK-3.9: Integration Testing with Phase 1 & 2
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** All Phase 3 tasks + Phase 1-2 complete
**Story Points:** 1
**Effort:** 2 hours

**Description:**
Create integration tests verifying Phase 1, 2, and 3 work together correctly.

**Acceptance Criteria:**
- [ ] Create `tests/core/integration/test_detection_cross_module.py`
- [ ] Test same artifact detected consistently across layers:
  - Local discovery (strict mode)
  - Marketplace detection (heuristic mode)
- [ ] Verify marketplace confidence > local confidence for ambiguous cases
- [ ] Cross-module type consistency (same ArtifactType enum)
- [ ] Detection reasons traceable through both layers
- [ ] Performance benchmark: marketplace detection before/after refactor

---

### TASK-3.10: Documentation and Code Comments
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** All Phase 3 implementation tasks
**Story Points:** 1
**Effort:** 1-2 hours

**Description:**
Add/update docstrings and comments for refactored heuristic_detector.py.

**Acceptance Criteria:**
- [ ] Module docstring explains detection architecture (baseline + marketplace)
- [ ] Scoring system documented with signal explanation
- [ ] All public methods have clear docstrings
- [ ] Inline comments explain complex scoring logic
- [ ] Examples provided for common detection patterns
- [ ] Reference to shared detection module documented
- [ ] Migration notes for developers familiar with old code

---

## Quality Gates

### Phase 3 Completion Checklist

**Code Quality:**
- [ ] All 10 tasks completed
- [ ] No linting errors (black, flake8, mypy)
- [ ] Code follows SkillMeat patterns
- [ ] No circular imports with Phase 1-2 modules
- [ ] Duplicate ArtifactType enum removed

**Testing:**
- [ ] All existing marketplace tests pass (100% pass rate)
- [ ] New baseline + marketplace scoring tests pass
- [ ] Integration tests pass
- [ ] >85% code coverage on refactored heuristic_detector.py
- [ ] No test failures or skipped tests

**Functionality:**
- [ ] 80%+ of detection logic reuses shared module
- [ ] Manual mappings still work correctly
- [ ] GitHub heuristics still work correctly
- [ ] Confidence scores match pre-refactor behavior
- [ ] Detection results include proper reasons

**Backwards Compatibility:**
- [ ] MarketplaceDetector public API unchanged
- [ ] Confidence scores compatible (same ranges, similar values)
- [ ] All existing marketplace scanning tests pass
- [ ] Manual mappings fully functional

---

## Implementation Notes

### Key Design Decisions

1. **Baseline + Extension model**: Separate shared baseline detection from marketplace signals; easier to test and maintain.

2. **ArtifactType enum**: Canonical enum used everywhere (no more local duplicate); enum values unchanged.

3. **Confidence preservation**: Marketplace confidence scores should match pre-refactor implementation to avoid surprises; scoring is tuned separately if needed.

4. **Manual mapping override**: Remains highest priority; manual mappings are not heuristic, they are policy decisions.

5. **GitHub heuristics**: Marketplace-specific signals kept local to heuristic_detector.py (not in shared core).

### Potential Issues & Mitigations

| Issue | Likelihood | Mitigation |
|---|---|---|
| Confidence scores drift from previous | Medium | Detailed scoring comparison tests, tuning phase |
| Baseline detection too strict | Low | Use heuristic mode in detect_artifact(), not strict |
| Manual mappings broken | Low | Comprehensive manual mapping tests |
| Regression in marketplace accuracy | Medium | Phase 5 integration tests with real repos |

---

## Success Criteria

### Functional
- ✓ Duplicate ArtifactType enum removed
- ✓ 80%+ detection logic reuses shared module
- ✓ Manual directory mappings work correctly
- ✓ GitHub heuristics work correctly
- ✓ Confidence scores match pre-refactor behavior

### Quality
- ✓ All existing marketplace tests pass (100% pass rate)
- ✓ New baseline + marketplace tests pass
- ✓ >85% code coverage
- ✓ Comprehensive docstrings
- ✓ No circular imports

### Backwards Compatibility
- ✓ MarketplaceDetector API unchanged
- ✓ Confidence scores compatible
- ✓ All existing marketplace tests pass

---

## Review Checklist

Before marking Phase 3 complete:

- [ ] Code review: Refactoring matches PRD requirements
- [ ] Test coverage: All existing tests pass, new tests added
- [ ] Integration: Shared module reused correctly (80%+ detection)
- [ ] Scoring: Confidence scores match pre-refactor or improvements justified
- [ ] Backwards compatibility: Manual mappings and GitHub heuristics work
- [ ] Documentation: Docstrings clear and explain baseline + marketplace separation
- [ ] Next phase: Phase 4 can start (validators independent)

---

**Document Version:** 1.0
**Status:** Ready for Implementation
**Last Updated:** 2026-01-06
