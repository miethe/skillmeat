---
status: inferred_complete
---
# Phase 2: Rebuild Local Discovery with Shared Detector

**Duration:** 1 week
**Story Points:** 12
**Status:** Ready for Implementation
**Assigned To:** `python-backend-engineer` (Opus)

---

## Overview

Phase 2 rebuilds `discovery.py` to use the unified detection module from Phase 1. Key improvements:
- Replace fragmented `_detect_artifact_type()` with `detect_artifact()` from shared core
- Add recursive directory traversal for nested artifacts
- Implement deprecation warnings for legacy directory-based commands/agents
- Maintain backwards compatibility with all existing APIs

**Key Outputs:**
- Updated `skillmeat/core/discovery.py`
- Updated discovery tests (with new nested artifact tests)
- Integration tests with Phase 1 module

---

## Task Breakdown

### TASK-2.1: Review and Analyze Current discovery.py
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** Phase 1 complete
**Story Points:** 2
**Effort:** 2-3 hours

**Description:**
Analyze current discovery.py implementation to understand:
- Current detection logic in `_detect_artifact_type()`
- How container types are inferred
- Recursive vs non-recursive traversal
- Edge cases and special handling

**Acceptance Criteria:**
- [ ] Understand current detection algorithm (container name → artifact type)
- [ ] Map current behavior to shared detection functions
- [ ] Identify all edge cases and fallbacks
- [ ] Document current performance characteristics
- [ ] Create migration plan from old to new detection

**Detailed Analysis:**
Current `_detect_artifact_type()` in discovery.py:
- Infers type from parent directory name (strips trailing 's')
- Supports: skill, command, agent, hook, mcp (strings, not enum)
- No confidence scoring (hard filters only)
- Limited container aliases (only singular/plural pairs)

---

### TASK-2.2: Import and Wire Shared Detection Module
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-2.1
**Story Points:** 2
**Effort:** 2-3 hours

**Description:**
Update discovery.py imports to use shared detection module and wire up the new functions.

**Acceptance Criteria:**
- [ ] Add imports:
  ```python
  from skillmeat.core.artifact_detection import (
      ArtifactType, DetectionResult, detect_artifact,
      ARTIFACT_SIGNATURES, normalize_container_name
  )
  ```
- [ ] Replace string type names with ArtifactType enum
- [ ] Ensure no circular imports
- [ ] Update LocalArtifact dataclass to use ArtifactType (from enum, not string)
- [ ] Update all type hints in discovery.py
- [ ] No breaking changes to public DiscoveryManager API

**Details:**
LocalArtifact should now have `type: ArtifactType` instead of `type: str`. This is internal change; public API (DiscoveryManager methods) returns appropriate types.

---

### TASK-2.3: Replace _detect_artifact_type() with Shared Detector
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-2.2
**Story Points:** 3
**Effort:** 4-5 hours

**Description:**
Replace `_detect_artifact_type()` method with call to `detect_artifact()` from shared module.

**Acceptance Criteria:**
- [ ] Old `_detect_artifact_type()` method removed or deprecated
- [ ] New `_detect_artifact()` method calls `detect_artifact(path, mode="strict")`
- [ ] Detection results parsed and converted to LocalArtifact
- [ ] Deprecation warnings from DetectionResult are logged
- [ ] Container type inference uses `normalize_container_name()` from shared module
- [ ] All detection reasons from result are captured for debugging
- [ ] Performance matches or exceeds previous implementation
- [ ] No change to DiscoveryManager public API

**Details:**
New detection flow:
```python
def _detect_artifact(self, path: Path, container_type: str) -> Optional[LocalArtifact]:
    try:
        result = detect_artifact(path, container_type=container_type, mode="strict")
        if result.confidence == 100:
            # Valid artifact
            artifact = LocalArtifact(
                type=result.artifact_type,  # ArtifactType enum
                name=result.name,
                path=result.path,
                container_type=result.container_type,
                manifest_file=result.manifest_file,
            )
            if result.deprecation_warning:
                logger.warning(result.deprecation_warning)
            return artifact
        else:
            return None
    except Exception as e:
        logger.debug(f"Detection failed for {path}: {e}")
        return None
```

---

### TASK-2.4: Add Recursive Directory Traversal
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-2.3
**Story Points:** 3
**Effort:** 4-5 hours

**Description:**
Implement recursive directory traversal to detect nested single-file artifacts (commands, agents) in subdirectories under container folders.

**Acceptance Criteria:**
- [ ] New method `_discover_nested_artifacts(container_path: Path, container_type: ArtifactType)` implemented
- [ ] Recursively scans subdirectories under container (e.g., commands/)
- [ ] Detects single-file commands/agents in nested folders
- [ ] Respects `allowed_nesting` flag from ARTIFACT_SIGNATURES
- [ ] Skips directories not allowed to nest (e.g., skills)
- [ ] Depth limit applied (max 3-5 levels to prevent excessive scanning)
- [ ] Performance optimized (no redundant file checks)
- [ ] Backwards compatible (old flat structure still works)
- [ ] Unit tests for nested discovery added

**Details:**
Example structure now detected:
```
.claude/
├── commands/
│   ├── cmd1.md          (already detected)
│   └── subdir/
│       └── cmd2.md      (NEW: nested detection)
├── agents/
│   ├── agent1.md
│   └── tools/
│       └── agent2.md    (NEW: nested detection)
└── skills/
    └── skill1/
        └── SKILL.md     (already detected, skills don't support nesting beyond their own dir)
```

---

### TASK-2.5: Implement Deprecation Warnings
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-2.3
**Story Points:** 2
**Effort:** 2-3 hours

**Description:**
Add deprecation warnings for legacy directory-based commands and agents (which should only be files).

**Acceptance Criteria:**
- [ ] Detect when command/agent is a directory (legacy pattern)
- [ ] Log clear deprecation warning with:
  - Location of legacy artifact
  - Recommended migration (move to single file)
  - Timeline (e.g., "will be removed in v1.0.0")
  - Link to migration guide
- [ ] Warning format consistent with SkillMeat logging standards
- [ ] Warnings can be toggled/controlled via discovery config
- [ ] Legacy artifacts still discovered (for backwards compatibility)
- [ ] Detection includes reason: "DEPRECATED: directory-based command/agent"

**Details:**
Warning example:
```
DEPRECATED: Directory-based command/agent artifacts will no longer be supported.
  Location: ./.claude/commands/my_command_dir/
  Recommended: Move to single .md file at ./.claude/commands/my_command.md
  Migration guide: docs/migration/deprecated-artifact-patterns.md
  Deadline: SkillMeat v1.0.0 (2026-Q3)
```

---

### TASK-2.6: Update Discovery Tests for Shared Detector
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-2.3-2.5
**Story Points:** 2
**Effort:** 2-3 hours

**Description:**
Update all existing discovery tests to work with new shared detector-based implementation.

**Acceptance Criteria:**
- [ ] All existing discovery tests pass (100% pass rate)
- [ ] Test fixtures updated to use ArtifactType enum
- [ ] Test assertions verify enum values (not strings)
- [ ] Mock/patch points updated for new detection flow
- [ ] No regression in test coverage
- [ ] Backwards compatibility tests verify old behavior preserved
- [ ] Tests include local vs shared detector comparison (verify same results)

**Details:**
Tests should verify:
- All artifact types detected correctly
- Container type normalization works
- Deprecation warnings logged for legacy patterns
- Detection confidence is 100% for valid artifacts
- Performance metrics comparable to Phase 1

---

### TASK-2.7: Write Tests for Nested Artifact Discovery
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-2.4
**Story Points:** 2
**Effort:** 2-3 hours

**Description:**
Create comprehensive test suite for new nested artifact discovery functionality.

**Acceptance Criteria:**
- [ ] 10+ test cases for nested discovery:
  - Detect nested commands in subdirectories
  - Detect nested agents in subdirectories
  - Skip nested skills (not allowed)
  - Handle multiple nesting levels (up to depth limit)
  - Handle empty directories
  - Handle mixed file/directory structures
- [ ] Temp directory fixtures for test artifacts
- [ ] Tests verify both detection and proper naming
- [ ] Edge cases covered (symlinks, special characters, etc.)

**Example Test Cases:**
```python
def test_discover_nested_commands():
    # Create structure with nested commands
    # Run discovery
    # Verify all commands detected (nested and flat)

def test_skip_nested_skills():
    # Create nested skill structure
    # Verify not detected as multiple artifacts

def test_nesting_depth_limit():
    # Create deeply nested artifacts
    # Verify only up to depth limit discovered
```

---

### TASK-2.8: Integration Testing with Phase 1
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** All previous Phase 2 tasks + Phase 1 complete
**Story Points:** 1
**Effort:** 2 hours

**Description:**
Create integration tests verifying Phase 1 and Phase 2 work together correctly.

**Acceptance Criteria:**
- [ ] Create `tests/core/integration/test_discovery_phase1_integration.py`
- [ ] Test that discovery uses shared detector functions
- [ ] Test that detection results from shared module are correctly parsed
- [ ] Test cross-module type consistency (ArtifactType enum used everywhere)
- [ ] Test container normalization used correctly
- [ ] Test detection confidence scores (100% for valid artifacts in strict mode)
- [ ] Performance benchmark: detection time before/after Phase 1

---

### TASK-2.9: Update discovery.py Documentation
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** All Phase 2 implementation tasks
**Story Points:** 1
**Effort:** 1-2 hours

**Description:**
Add/update docstrings and documentation for refactored discovery.py.

**Acceptance Criteria:**
- [ ] Module docstring explains detection flow and use of shared detector
- [ ] DiscoveryManager docstring updated (if needed)
- [ ] All public methods have clear docstrings
- [ ] Comments explain recursive traversal algorithm
- [ ] Deprecation warnings documented
- [ ] Examples provided for common discovery patterns
- [ ] Reference to ARTIFACT_SIGNATURES documented

---

## Quality Gates

### Phase 2 Completion Checklist

**Code Quality:**
- [ ] All 9 tasks completed
- [ ] No linting errors (black, flake8, mypy)
- [ ] Code follows SkillMeat patterns
- [ ] No circular imports with Phase 1 module

**Testing:**
- [ ] All existing discovery tests pass (100% pass rate)
- [ ] New nested discovery tests pass
- [ ] Integration tests pass
- [ ] >85% code coverage on refactored discovery.py
- [ ] No test failures or skipped tests

**Functionality:**
- [ ] All artifact types detected correctly
- [ ] Nested artifacts discovered and detected
- [ ] Deprecation warnings logged for legacy patterns
- [ ] Container name normalization works
- [ ] Performance matches or exceeds Phase 1 baseline

**Backwards Compatibility:**
- [ ] DiscoveryManager public API unchanged
- [ ] LocalArtifact structure compatible (type is ArtifactType, not string, but this is internal)
- [ ] Existing collections still discoverable
- [ ] All existing tests pass

---

## Implementation Notes

### Key Design Decisions

1. **Strict mode only**: Local discovery uses `mode="strict"` because developers control .claude/ structure; no heuristic scoring needed.

2. **ArtifactType enum internally**: LocalArtifact uses ArtifactType enum internally, but this is internal detail; public discovery API may wrap/convert as needed.

3. **Recursive with depth limit**: Balance between nested artifact discovery and avoiding excessive filesystem traversal.

4. **Deprecation warnings, not errors**: Legacy patterns still work but log warnings; errors deferred to Phase 6+.

5. **Reuse vs rewrite**: Replace only `_detect_artifact_type()` method; keep rest of discovery logic unchanged.

### Potential Issues & Mitigations

| Issue | Likelihood | Mitigation |
|-------|-----------|-----------|
| Nested discovery too slow | Medium | Add depth limit (3-5 levels), cache results |
| Type conversion breaks code | Low | All type conversions happen in discovery; public API stable |
| Deprecation warnings spam logs | Low | Make warnings toggleable via discovery config |
| Edge cases in recursive traversal | Medium | Comprehensive test suite, handle symlinks |

---

## Success Criteria

### Functional
- ✓ All artifacts detected with shared detector
- ✓ Nested artifacts discovered and detected
- ✓ Deprecation warnings logged for legacy patterns
- ✓ Container name normalization works correctly
- ✓ No regression in discovery speed

### Quality
- ✓ All existing tests pass (100% pass rate)
- ✓ New nested discovery tests pass
- ✓ >85% code coverage
- ✓ Comprehensive docstrings
- ✓ Zero circular imports

### Backwards Compatibility
- ✓ DiscoveryManager public API unchanged
- ✓ Existing collections still discoverable
- ✓ Detection results compatible with downstream code

---

## Review Checklist

Before marking Phase 2 complete:

- [ ] Code review: Refactoring matches PRD requirements
- [ ] Test coverage: All existing tests pass, new tests added
- [ ] Integration: Shared detector functions used correctly
- [ ] Performance: No regression in discovery time
- [ ] Backwards compatibility: Existing collections work
- [ ] Documentation: Docstrings clear and complete
- [ ] Next phase: Phase 3 can start (marketplace refactor independent)

---

**Document Version:** 1.0
**Status:** Ready for Implementation
**Last Updated:** 2026-01-06
