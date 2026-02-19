---
status: inferred_complete
---
# Phase 4: Align Validators and CLI Defaults

**Duration:** 1 week
**Story Points:** 10
**Status:** Ready for Implementation
**Assigned To:** `python-backend-engineer` (Opus)

---

## Overview

Phase 4 aligns `validator.py` and `defaults.py` with the unified detection system. Key changes:
- Replace ad-hoc validation logic with shared `ARTIFACT_SIGNATURES`
- Use shared `extract_manifest_file()` for manifest location
- Route CLI defaults through shared type inference
- Ensure consistent type names across all modules
- Maintain backwards compatibility of validation behavior

**Key Outputs:**
- Updated `skillmeat/utils/validator.py`
- Updated `skillmeat/defaults.py`
- Updated validator and defaults tests
- Type normalization documentation

---

## Task Breakdown

### TASK-4.1: Analyze Current validator.py Implementation
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** Phase 1 complete
**Story Points:** 1
**Effort:** 1-2 hours

**Description:**
Analyze current validation logic to understand how it can be refactored to use shared signatures.

**Acceptance Criteria:**
- [ ] Understand current validation for each artifact type (SKILL, COMMAND, AGENT, HOOK, MCP)
- [ ] Identify validation rules: manifest files, directory structure, required fields
- [ ] Map current validation logic to ARTIFACT_SIGNATURES (directory vs file, manifest requirements)
- [ ] Identify edge cases and special validation rules
- [ ] Document current type name handling (snake_case, enum, strings)

**Details:**
Current validator.py likely has:
- `validate_skill(path)`: Checks for SKILL.md, directory structure
- `validate_command(path)`: Checks for .md file
- `validate_agent(path)`: Checks for .md file
- Auto-detection priority: SKILL.md > AGENT.md > any .md file
- Fallback to checking for `.md` files (can misclassify)

---

### TASK-4.2: Import Shared Detection Components into validator.py
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-4.1, Phase 1 complete
**Story Points:** 1
**Effort:** 1-2 hours

**Description:**
Add imports from Phase 1 detection module to validator.py.

**Acceptance Criteria:**
- [ ] Add imports:
  ```python
  from skillmeat.core.artifact_detection import (
      ArtifactType, ARTIFACT_SIGNATURES, extract_manifest_file
  )
  ```
- [ ] No circular imports
- [ ] All imports accessible and working

**Details:**
Key components to import:
- ArtifactType: For consistent type definitions
- ARTIFACT_SIGNATURES: For validation rules (manifest requirements, structure)
- extract_manifest_file(): For finding manifest files

---

### TASK-4.3: Refactor validator.py to Use Shared Signatures
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-4.2
**Story Points:** 3
**Effort:** 4-5 hours

**Description:**
Replace ad-hoc validation logic with shared `ARTIFACT_SIGNATURES` registry.

**Acceptance Criteria:**
- [ ] New validation structure:
  ```python
  def validate_artifact(path: Path, artifact_type: ArtifactType) -> ValidationResult:
      sig = ARTIFACT_SIGNATURES[artifact_type]
      # Check is_directory matches sig.is_directory
      # Check manifest requirements (if sig.requires_manifest)
      # Check other structural rules
  ```
- [ ] All artifact type validators refactored to use shared signatures
- [ ] Validation rules from signatures applied consistently
- [ ] Manifest files located using `extract_manifest_file()`
- [ ] Validation messages clear and helpful
- [ ] Edge cases handled (missing manifests, wrong structure)
- [ ] All existing validation tests pass

**Details:**
Validation logic changes:
- **SKILL**: Must be directory with SKILL.md (check signature.is_directory=True, signature.requires_manifest=True)
- **COMMAND**: Must be file, no manifest required (check signature.is_directory=False)
- **AGENT**: Must be file, no manifest required (check signature.is_directory=False)
- **HOOK**: JSON structure (check signature.manifest_names={settings.json})
- **MCP**: JSON structure (check signature.manifest_names={.mcp.json})

---

### TASK-4.4: Implement Type Validation and Normalization
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-4.3
**Story Points:** 2
**Effort:** 2-3 hours

**Description:**
Add type validation and normalization helpers to ensure consistent type names across validator.

**Acceptance Criteria:**
- [ ] Function `normalize_artifact_type(type_value: Any) -> ArtifactType` implemented
  - Accepts: ArtifactType enum, string names, snake_case variants
  - Returns: ArtifactType enum
  - Raises: InvalidArtifactTypeError if invalid
- [ ] Function `validate_artifact_type(type_value: Any) -> bool` implemented
  - Returns True if valid type, False otherwise
- [ ] Support both canonical (mcp) and API (mcp_server) names
- [ ] Clear error messages for invalid types
- [ ] Comprehensive docstrings with examples

**Details:**
Type mapping examples:
- normalize_artifact_type("skill") → ArtifactType.SKILL
- normalize_artifact_type("command") → ArtifactType.COMMAND
- normalize_artifact_type(ArtifactType.SKILL) → ArtifactType.SKILL
- normalize_artifact_type("mcp_server") → ArtifactType.MCP (backwards compat)
- normalize_artifact_type("unknown") → raises InvalidArtifactTypeError

---

### TASK-4.5: Deprecation Warning Support in Validators
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-4.3, TASK-4.4
**Story Points:** 1
**Effort:** 1-2 hours

**Description:**
Add deprecation warning support for legacy directory-based commands/agents in validators.

**Acceptance Criteria:**
- [ ] Validators detect when command/agent is directory (legacy pattern)
- [ ] Deprecation warning included in ValidationResult
- [ ] Warning message clear and actionable
- [ ] Warnings can be toggled via validator config
- [ ] Legacy artifacts still validate (return valid=True, deprecation_warning=True)
- [ ] Tests verify deprecation warnings

---

### TASK-4.6: Analyze Current defaults.py Implementation
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** Phase 1 complete
**Story Points:** 1
**Effort:** 1 hour

**Description:**
Analyze current CLI defaults logic for type inference.

**Acceptance Criteria:**
- [ ] Understand current name-based type inference (e.g., "-cli" → command)
- [ ] Identify all inference rules and fallback behavior
- [ ] Document current type name handling
- [ ] Map current logic to shared `infer_artifact_type()` function

**Details:**
Current defaults.py likely infers:
- "-cli", "-cmd", "-command" in name → COMMAND
- "-agent", "-bot" in name → AGENT
- Fallback: SKILL

---

### TASK-4.7: Refactor defaults.py to Use Shared Inference
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-4.6, Phase 1 complete
**Story Points:** 2
**Effort:** 2-3 hours

**Description:**
Route CLI defaults through shared type inference functions.

**Acceptance Criteria:**
- [ ] Import `infer_artifact_type()` from shared detection module
- [ ] Refactor CLI default functions to use shared inference
- [ ] Maintain current behavior (name-based heuristics)
- [ ] Return ArtifactType enum (not string)
- [ ] Clear fallback behavior documented
- [ ] All defaults tests pass
- [ ] No breaking changes to CLI

**Details:**
New defaults flow:
```python
from skillmeat.core.artifact_detection import infer_artifact_type

def infer_type_from_name(name: str) -> ArtifactType:
    # Use shared inference first
    inferred = infer_artifact_type(Path(name))
    if inferred:
        return inferred

    # Fallback to name-based heuristics
    if "-cli" in name or "-cmd" in name or "-command" in name:
        return ArtifactType.COMMAND
    if "-agent" in name or "-bot" in name:
        return ArtifactType.AGENT

    # Final fallback
    return ArtifactType.SKILL
```

---

### TASK-4.8: Update validator.py Tests
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-4.3-4.5
**Story Points:** 1
**Effort:** 2 hours

**Description:**
Update all validator tests to work with refactored implementation.

**Acceptance Criteria:**
- [ ] All existing validation tests pass (100% pass rate)
- [ ] Test fixtures updated to use ArtifactType enum
- [ ] Test assertions verify correct validation results
- [ ] Mock/patch points updated for shared signatures
- [ ] New tests for type normalization
- [ ] New tests for deprecation warnings
- [ ] No regression in test coverage

---

### TASK-4.9: Update defaults.py Tests
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-4.7
**Story Points:** 1
**Effort:** 1-2 hours

**Description:**
Update all defaults tests to work with refactored implementation.

**Acceptance Criteria:**
- [ ] All existing defaults tests pass (100% pass rate)
- [ ] Test assertions verify ArtifactType enum returns
- [ ] New tests verify shared inference usage
- [ ] Name-based heuristics still work correctly
- [ ] Fallback behavior tested
- [ ] No regression in test coverage

---

### TASK-4.10: Documentation for Validators and Defaults
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-4.3-4.9
**Story Points:** 1
**Effort:** 1-2 hours

**Description:**
Add/update docstrings and documentation for refactored validator.py and defaults.py.

**Acceptance Criteria:**
- [ ] Module docstrings explain shared signature usage
- [ ] All public validation functions have clear docstrings
- [ ] CLI defaults functions documented with examples
- [ ] Type normalization documented with examples
- [ ] Deprecation warnings documented
- [ ] Examples provided for common validation patterns
- [ ] Reference to shared detection module documented

---

## Quality Gates

### Phase 4 Completion Checklist

**Code Quality:**
- [ ] All 10 tasks completed
- [ ] No linting errors (black, flake8, mypy)
- [ ] Code follows SkillMeat patterns
- [ ] No circular imports with Phase 1-3 modules
- [ ] Type hints correct throughout

**Testing:**
- [ ] All existing validator tests pass (100% pass rate)
- [ ] All existing defaults tests pass (100% pass rate)
- [ ] New type normalization tests pass
- [ ] New deprecation warning tests pass
- [ ] >85% code coverage on refactored modules
- [ ] No test failures or skipped tests

**Functionality:**
- [ ] Validation uses shared ARTIFACT_SIGNATURES
- [ ] Type normalization handles all variants
- [ ] CLI defaults use shared inference
- [ ] Deprecation warnings logged for legacy patterns
- [ ] All artifact types validated correctly

**Backwards Compatibility:**
- [ ] Validator public API unchanged
- [ ] Defaults public API unchanged (returns ArtifactType, not string)
- [ ] All validation behavior preserved
- [ ] All existing tests pass

---

## Implementation Notes

### Key Design Decisions

1. **Shared signatures first**: Validation uses ARTIFACT_SIGNATURES as source of truth; shared rules checked before custom validation.

2. **Type normalization centralized**: All type name conversions happen in normalize_artifact_type(); callers get ArtifactType enum.

3. **Backwards compatible variants**: Support both "mcp" and "mcp_server" names for backwards compatibility; normalize to enum internally.

4. **Deprecation warnings, not errors**: Legacy patterns still validate (with warnings); errors deferred to Phase 6+.

5. **Minimal changes to public APIs**: Validator and defaults public interfaces unchanged; only internal implementation refactored.

### Potential Issues & Mitigations

| Issue | Likelihood | Mitigation |
|---|---|---|
| Type name variants cause confusion | Low | Type normalization function centralizes all conversions |
| Validation strictness changes | Low | All existing tests pass before/after refactor |
| CLI defaults behavior changes | Low | Name-based heuristics preserved, shared inference is extension |
| Deprecation warnings too aggressive | Low | Warnings logged, not errors |

---

## Success Criteria

### Functional
- ✓ Validation uses shared ARTIFACT_SIGNATURES
- ✓ Type normalization handles all variants
- ✓ CLI defaults use shared inference
- ✓ Validation behavior preserved
- ✓ Deprecation warnings for legacy patterns

### Quality
- ✓ All existing tests pass (100% pass rate)
- ✓ New type normalization tests pass
- ✓ >85% code coverage
- ✓ Comprehensive docstrings
- ✓ No circular imports

### Backwards Compatibility
- ✓ Public APIs unchanged
- ✓ Validation behavior preserved
- ✓ Type name variants supported
- ✓ CLI defaults work as before

---

## Review Checklist

Before marking Phase 4 complete:

- [ ] Code review: Refactoring matches PRD requirements
- [ ] Test coverage: All existing tests pass, new tests added
- [ ] Integration: Shared module functions used correctly
- [ ] Type consistency: All modules use same ArtifactType enum
- [ ] Backwards compatibility: All existing validation and defaults work
- [ ] Documentation: Docstrings clear and complete
- [ ] Next phase: Phase 5 can start (comprehensive testing)

---

**Document Version:** 1.0
**Status:** Ready for Implementation
**Last Updated:** 2026-01-06
