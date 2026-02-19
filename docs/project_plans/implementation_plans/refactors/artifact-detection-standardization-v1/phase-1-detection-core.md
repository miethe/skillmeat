---
status: inferred_complete
---
# Phase 1: Create Shared Detection Core Module

**Duration:** 1 week
**Story Points:** 13
**Status:** Ready for Implementation
**Assigned To:** `python-backend-engineer` (Opus)

---

## Overview

Phase 1 creates the foundation: a unified `artifact_detection.py` module that defines canonical types, artifact signatures, and core detection functions. This becomes the single source of truth for all artifact detection logic across the codebase.

**Key Outputs:**
- New `skillmeat/core/artifact_detection.py` (~400 lines)
- Updated `skillmeat/core/artifact.py` (import ArtifactType from new module)
- Initial test suite (20+ test cases)

---

## Task Breakdown

### TASK-1.1: Define Core Data Structures
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** None
**Story Points:** 3
**Effort:** 4-5 hours

**Description:**
Create the `ArtifactType` enum, `DetectionResult` dataclass, and `ArtifactSignature` dataclass in new module.

**Acceptance Criteria:**
- [ ] `ArtifactType` enum defined with 5 primary types: SKILL, COMMAND, AGENT, HOOK, MCP
- [ ] `ArtifactType` extends `str` and `Enum` for API compatibility
- [ ] `DetectionResult` dataclass includes: artifact_type, name, path, container_type, detection_mode, confidence, manifest_file, metadata, detection_reasons, deprecation_warning
- [ ] `ArtifactSignature` dataclass defined with: artifact_type, container_names, is_directory, requires_manifest, manifest_names, allowed_nesting
- [ ] All dataclasses have proper type hints and docstrings
- [ ] No import errors from other modules

**Details:**
```python
# artifact_detection.py structure:
class ArtifactType(str, Enum):
    SKILL = "skill"
    COMMAND = "command"
    AGENT = "agent"
    HOOK = "hook"
    MCP = "mcp"
    # Context entity types (placeholder for future)
    PROJECT_CONFIG = "project_config"
    # ... etc

@dataclass
class DetectionResult:
    artifact_type: ArtifactType
    name: str
    path: str
    container_type: str
    detection_mode: Literal["strict", "heuristic"]
    confidence: int  # 0-100
    # ... optional fields
```

---

### TASK-1.2: Create Artifact Signatures Registry
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-1.1 (ArtifactType enum)
**Story Points:** 3
**Effort:** 4-5 hours

**Description:**
Define `ARTIFACT_SIGNATURES` dictionary mapping ArtifactType to signature requirements (directory vs file, manifest requirements, etc.).

**Acceptance Criteria:**
- [ ] `ARTIFACT_SIGNATURES` dict created with all 5 primary types
- [ ] Each signature includes: is_directory, requires_manifest, manifest_names, allowed_nesting
- [ ] SKILL: directory=True, requires_manifest=True, manifests={SKILL.md, skill.md}
- [ ] COMMAND: directory=False, requires_manifest=False, nesting=True
- [ ] AGENT: directory=False, requires_manifest=False, nesting=True
- [ ] HOOK: directory=False, requires_manifest=False, manifest_names={settings.json}
- [ ] MCP: directory=False, requires_manifest=False, manifest_names={.mcp.json}
- [ ] Registry fully documented with examples
- [ ] No overlapping or conflicting signature definitions

**Details:**
The signatures define the structural rules for each artifact type. These are used by all detection layers.

---

### TASK-1.3: Define Container Alias Registries
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-1.1 (ArtifactType enum)
**Story Points:** 2
**Effort:** 2-3 hours

**Description:**
Create `CONTAINER_ALIASES` and `MANIFEST_FILES` registries with all supported aliases per type.

**Acceptance Criteria:**
- [ ] `CONTAINER_ALIASES` dict created: maps ArtifactType → Set[str] of all aliases
- [ ] SKILL aliases: {skills, skill, claude-skills}
- [ ] COMMAND aliases: {commands, command, claude-commands}
- [ ] AGENT aliases: {agents, agent, subagents, claude-agents}
- [ ] HOOK aliases: {hooks, hook, claude-hooks}
- [ ] MCP aliases: {mcp, mcp-servers, servers, mcp_servers, claude-mcp}
- [ ] `MANIFEST_FILES` dict created: maps ArtifactType → Set[str] of valid manifest filenames
- [ ] Both registries documented and validated (no duplicates across types)

**Details:**
These registries are used for normalization and validation. CONTAINER_ALIASES supports 20+ different names for the same artifact type.

---

### TASK-1.4: Implement normalize_container_name() Function
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-1.3 (container aliases)
**Story Points:** 2
**Effort:** 2-3 hours

**Description:**
Implement `normalize_container_name(name: str, artifact_type: ArtifactType) -> str` function for normalizing container directory names.

**Acceptance Criteria:**
- [ ] Function accepts any container name (case-insensitive)
- [ ] Returns canonical container name (lowercase, singular or plural as per type)
- [ ] Raises `InvalidContainerError` if name not recognized for type
- [ ] Case insensitivity: "Commands", "COMMANDS", "commands" all normalize to "commands"
- [ ] Supports all aliases from CONTAINER_ALIASES registry
- [ ] Proper error messages with suggestions
- [ ] Comprehensive docstring with examples

**Details:**
Example mappings:
- normalize_container_name("subagents", ArtifactType.AGENT) → "agents"
- normalize_container_name("mcp-servers", ArtifactType.MCP) → "mcp"
- normalize_container_name("SKILLS", ArtifactType.SKILL) → "skills"
- normalize_container_name("invalid", ArtifactType.SKILL) → raises InvalidContainerError

---

### TASK-1.5: Implement Core Detection Functions
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-1.1-1.4 (all registry and data structures)
**Story Points:** 3
**Effort:** 5-6 hours

**Description:**
Implement core detection functions: `infer_artifact_type()`, `detect_artifact()`, and `extract_manifest_file()`.

**Acceptance Criteria:**
- [ ] `infer_artifact_type(path: Path) -> Optional[ArtifactType]` implemented
  - Checks for manifest files (SKILL.md, COMMAND.md, etc.)
  - Falls back to directory structure analysis
  - Returns None if no clear type detected
- [ ] `detect_artifact(path: Path, container_type: Optional[str] = None, mode: str = "strict") -> DetectionResult` implemented
  - Strict mode: Returns 100% confidence if rules match, 0% otherwise
  - Heuristic mode: Returns confidence 0-100 (used by marketplace)
  - Includes detection_reasons list for debugging
  - Handles deprecation warnings for legacy patterns
- [ ] `extract_manifest_file(path: Path, artifact_type: ArtifactType) -> Optional[Path]` implemented
  - Looks for all known manifest names for given type
  - Returns first found or None
  - Case-insensitive search
- [ ] All functions have proper error handling and logging
- [ ] Comprehensive docstrings with examples
- [ ] No external dependencies (uses only stdlib + existing SkillMeat modules)

**Details:**
These are the core functions used by all detection layers. Focus on clarity and maintainability.

---

### TASK-1.6: Create Custom Exceptions
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** None
**Story Points:** 1
**Effort:** 1 hour

**Description:**
Define custom exceptions for detection module: `InvalidContainerError`, `InvalidArtifactTypeError`, `DetectionError`.

**Acceptance Criteria:**
- [ ] `InvalidContainerError` raised by normalize_container_name()
- [ ] `InvalidArtifactTypeError` raised for invalid ArtifactType values
- [ ] `DetectionError` base exception for other detection failures
- [ ] All exceptions have clear error messages
- [ ] Proper inheritance hierarchy

---

### TASK-1.7: Update artifact.py to Import from New Module
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-1.1 (ArtifactType enum)
**Story Points:** 1
**Effort:** 1-2 hours

**Description:**
Update `skillmeat/core/artifact.py` to import `ArtifactType` from the new detection module.

**Acceptance Criteria:**
- [ ] `from skillmeat.core.artifact_detection import ArtifactType` added to artifact.py
- [ ] Remove any local ArtifactType definition if present
- [ ] Artifact class still works with imported ArtifactType
- [ ] No circular import errors
- [ ] All artifact.py tests pass
- [ ] Type hints remain correct (using imported ArtifactType)

---

### TASK-1.8: Write Unit Tests for Core Module
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-1.1-1.7 (all core implementation)
**Story Points:** 2
**Effort:** 3-4 hours

**Description:**
Create initial test suite for artifact_detection.py with 20+ test cases covering all major functions and edge cases.

**Acceptance Criteria:**
- [ ] `tests/core/test_artifact_detection.py` created
- [ ] 20+ test cases covering:
  - ArtifactType enum values (5 tests)
  - normalize_container_name() with all aliases (8 tests)
  - Container name validation and error handling (4 tests)
  - Artifact signature definitions (3 tests)
- [ ] All tests pass (100% pass rate)
- [ ] Tests cover both happy path and error cases
- [ ] Proper pytest fixtures for temp directories
- [ ] Docstrings explaining test purpose

**Test Categories:**
- Type system tests (enum values, string conversion)
- Container alias tests (all 20+ aliases, case sensitivity)
- Signature validation tests (directory rules, manifest rules)
- Detection function tests (strict mode, confidence scores)

---

### TASK-1.9: Documentation and Module Docstrings
**Status:** Not Started
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Dependencies:** TASK-1.1-1.8 (all implementation)
**Story Points:** 1
**Effort:** 2 hours

**Description:**
Add comprehensive module-level docstrings and inline documentation to artifact_detection.py.

**Acceptance Criteria:**
- [ ] Module docstring explains purpose and key exports
- [ ] All classes have complete docstrings with examples
- [ ] All functions have docstrings with parameters, returns, raises, examples
- [ ] Inline comments explain complex logic (e.g., normalization algorithm)
- [ ] Container alias philosophy documented (why certain aliases supported)
- [ ] Examples provided for common detection patterns

---

## Quality Gates

### Phase 1 Completion Checklist

**Code Quality:**
- [ ] All 9 tasks completed
- [ ] No linting errors (black, flake8, mypy)
- [ ] Code follows SkillMeat patterns (see CLAUDE.md)
- [ ] All type hints present and correct

**Testing:**
- [ ] 20+ unit tests all passing
- [ ] >90% code coverage on artifact_detection.py
- [ ] No test failures or skipped tests
- [ ] pytest runs successfully with no warnings

**Integration:**
- [ ] artifact.py imports ArtifactType correctly
- [ ] No circular import errors
- [ ] Other modules can import from artifact_detection
- [ ] All artifact.py tests still pass

**Documentation:**
- [ ] Module docstrings complete
- [ ] All public APIs documented
- [ ] Examples provided for key functions
- [ ] README or guide references detection module

---

## Implementation Notes

### Key Design Decisions

1. **Enum extends str**: `ArtifactType(str, Enum)` allows direct JSON serialization and backwards compatibility with existing string-based code.

2. **Registries over functions**: ARTIFACT_SIGNATURES and CONTAINER_ALIASES as dicts (not code) makes updates easier and enables future configuration.

3. **Strict vs Heuristic modes**: Single `detect_artifact()` function with mode parameter avoids code duplication between local (strict) and marketplace (heuristic) detection.

4. **No external dependencies**: Keep detection module lightweight; use only stdlib and existing SkillMeat imports.

5. **Deprecation in result**: Store deprecation warning in DetectionResult instead of raising errors; allows graceful handling upstream.

### Dependency Graph

```
TASK-1.1 (ArtifactType enum)
  ↓
TASK-1.2 (Signatures) + TASK-1.3 (Aliases)
  ↓
TASK-1.4 (normalize_container_name) + TASK-1.5 (detect_artifact)
  ↓
TASK-1.6 (Exceptions)
  ↓
TASK-1.7 (Update artifact.py)
  ↓
TASK-1.8 (Unit tests)
  ↓
TASK-1.9 (Documentation)
```

Tasks can start in parallel once dependencies are clear. Recommend sequential for clean integration.

---

## Success Criteria

### Functional
- ✓ ArtifactType enum is canonical and imported everywhere
- ✓ ARTIFACT_SIGNATURES registry is complete and validated
- ✓ CONTAINER_ALIASES support all 20+ known aliases
- ✓ normalize_container_name() handles all cases
- ✓ detect_artifact() works in both strict and heuristic modes
- ✓ artifact.py successfully imports from new module

### Quality
- ✓ 20+ unit tests passing (100% pass rate)
- ✓ >90% code coverage
- ✓ No linting errors
- ✓ Comprehensive docstrings
- ✓ Zero circular imports

### Backwards Compatibility
- ✓ No changes to Artifact dataclass public interface
- ✓ artifact.py tests unchanged and passing
- ✓ All existing code importing artifact.ArtifactType continues to work (via re-export if needed)

---

## Review Checklist

Before marking Phase 1 complete, verify:

- [ ] Code review: All implementation matches PRD requirements
- [ ] Test coverage: 20+ tests, >90% coverage
- [ ] Integration: artifact.py imports work, no import errors
- [ ] Performance: No performance regression in type detection
- [ ] Backwards compatibility: Existing tests pass
- [ ] Documentation: Docstrings complete and clear
- [ ] Next phase ready: Phase 2 can start immediately after

---

**Document Version:** 1.0
**Status:** Ready for Implementation
**Last Updated:** 2026-01-06
