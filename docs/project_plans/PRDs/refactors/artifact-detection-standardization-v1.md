---
title: 'PRD: Artifact Detection Standardization Refactor'
description: Unified detection core for skill, command, agent, hook, and MCP artifacts
  with consistent type definitions, container aliases, and detection rules across
  local discovery, marketplace scanning, and validation layers
audience:
- ai-agents
- developers
- architects
tags:
- prd
- planning
- refactor
- detection
- architecture
- standardization
created: 2026-01-06
updated: 2026-01-06
category: product-planning
status: inferred_complete
related:
- /docs/project_plans/reports/artifact-detection-standardization-2026-01-06.md
- /.claude/context/artifact-detection-code-patterns.md
---
# PRD: Artifact Detection Standardization Refactor

**Feature Name:** Artifact Detection Standardization

**Filepath Name:** `artifact-detection-standardization-v1`

**Date:** 2026-01-06

**Author:** Claude Code (AI Agent)

**Version:** 1.0

**Status:** Planned

**Priority:** HIGH

**Scope:** Internal refactor (no external API changes)

---

## 1. Executive Summary

SkillMeat's artifact detection logic is currently fragmented across five independent modules (4,837 lines total) with duplicated type definitions, inconsistent container naming, fragmented detection rules, and conflicting signatures. This refactor consolidates detection logic into a unified core module that all detection layers (local discovery, marketplace scanning, validation, and CLI defaults) use as a single source of truth.

**Key Outcomes:**
- Single canonical `ArtifactType` enum used everywhere (deprecates duplicates in heuristic_detector.py)
- Shared detection signatures and container alias normalization (eliminates hardcoding in 3 locations)
- Common detection result structure with optional confidence scoring
- Local detection strict mode (100% confidence when rules match, no scoring needed)
- Marketplace detection extended mode (confidence scoring for GitHub sources)
- Comprehensive test coverage with backwards compatibility safeguards
- Clear deprecation warnings for legacy patterns (directory-based commands/agents)

**Success Metrics:**
- Zero ArtifactType enum duplicates across codebase
- 100% local discovery rebuilt on shared detector (0 legacy code paths)
- Marketplace heuristics reuse 80%+ shared detection rules
- All validators use shared signatures
- CLI defaults route through shared inference helper
- 5 independent detection modules consolidated to 2 (detection core + extension layers)
- 100 test cases covering detection consistency across all contexts

---

## 2. Context & Background

### Current State

**What Exists Today:**

**Detection Modules (4,837 lines across 5 files):**

1. **Core Artifact Definitions** (`skillmeat/core/artifact.py` - 1,903 lines)
   - `ArtifactType` enum: SKILL, COMMAND, AGENT + context entity types
   - Unified `Artifact` dataclass with metadata
   - Type validation and security checks
   - No container alias normalization

2. **Local Discovery** (`skillmeat/core/discovery.py` - 786 lines)
   - Scans `.claude/` and `collection/artifacts/` directories
   - Supports types: skill, command, agent, hook, mcp (as strings, not enum)
   - Detects manifests: SKILL.md, COMMAND.md, AGENT.md
   - Type inference from parent directory name (strips trailing 's')
   - No confidence scoring; hard filters only
   - Does not recognize container aliases (e.g., `subagents`)

3. **Marketplace Heuristics** (`skillmeat/core/marketplace/heuristic_detector.py` - 1,675 lines)
   - Duplicates `ArtifactType` enum with extended types: MCP_SERVER, HOOK
   - 7-signal scoring system: dir_name, manifest, extensions, parent_hint, frontmatter, container_hint, frontmatter_type
   - Uses `CONTAINER_TYPE_MAPPING`: commands, agents, skills, hooks, mcp, mcp-servers, servers
   - Confidence scoring (0-100) with manual mapping overrides
   - Detects nested single-file commands/agents under containers
   - Depth penalties for scoring

4. **Structural Validation** (`skillmeat/utils/validator.py` - 279 lines)
   - Validates skill/command/agent structure
   - Auto-detection priority: SKILL.md > AGENT.md > any .md file
   - Falls back to checking for `.md` files (can misclassify)
   - No heuristic scoring; pass/fail only

5. **Smart Defaults** (`skillmeat/defaults.py` - 194 lines)
   - Name-based type inference: `-cli`/`-cmd`/`-command` → command, `-agent`/`-bot` → agent
   - Fallback: skill
   - Used by CLI operations
   - Inconsistent type names with other modules

**Type Definition Inconsistencies:**
- `artifact.py`: SKILL, COMMAND, AGENT (+ context types)
- `heuristic_detector.py`: SKILL, COMMAND, AGENT, MCP_SERVER, HOOK
- `discovery.py`: "skill", "command", "agent", "hook", "mcp" (strings)
- Database/API: Uses mcp_server, hook (snake_case)

**Container Alias Inconsistencies:**
- Marketplace knows: commands, agents, skills, hooks, mcp, mcp-servers, servers
- Local discovery only recognizes singular/plural pairs (strips trailing 's')
- No support for `subagents` or other aliases
- Hardcoded in three locations

**Detection Result Inconsistencies:**
- Local discovery: `type: str` (no confidence)
- Marketplace: `confidence: int` (0-100), `score_breakdown: dict`
- Validators: boolean (pass/fail)
- CLI: string or None

### Problem Space

**Pain Points:**

1. **Type Definition Duplication**
   - ArtifactType enum defined in both artifact.py and heuristic_detector.py
   - Marketplace types diverge (includes MCP_SERVER, HOOK)
   - Local discovery uses strings instead of enum
   - Creates risk of type mismatches when one module is updated

2. **Manifest Files Hardcoded in Multiple Places**
   - Local discovery: Hardcoded manifest lookups
   - Marketplace: Hardcoded in DetectionConfig dataclass
   - Validators: Fallback logic with no central reference
   - No single source of truth for valid manifest names

3. **Container Directory Patterns Not Centralized**
   - Marketplace has explicit `CONTAINER_TYPE_MAPPING`
   - Local discovery infers by stripping trailing 's' (fragile, limited)
   - No support for aliases (subagents, mcp-servers, claude-commands, etc.)
   - Three separate normalization approaches

4. **Type Detection Logic Fragmented**
   - Four independent implementations of type detection
   - Different priority orders (manifest-first vs directory-first)
   - Different fallback behaviors
   - No common interface or shared algorithms

5. **Confidence Scoring Divergence**
   - Marketplace: Complex multi-signal scoring (0-100)
   - Local discovery: No scoring (hard filters only)
   - Validators: No scoring (boolean only)
   - Same artifact in same repo yields different confidence depending on detection layer

6. **Deprecated Patterns Not Enforced**
   - Directory-based commands/agents still accepted by local discovery
   - Should be deprecated (only skills can be directories)
   - No centralized deprecation warnings
   - Legacy collections may break if validation logic tightens

7. **Inconsistent Metadata Extraction**
   - Manifest file resolution splits across modules
   - Frontmatter parsing varies
   - No centralized extraction rules

### Architectural Context

**Current Architecture:**

```
┌─────────────────────────────────────┐
│  Artifact Detection (Fragmented)    │
├─────────────────────────────────────┤
│                                     │
│  Local Discovery ──┬──> ArtifactType│
│  (discovery.py)    │    (artifact.py)
│                    │
│  Marketplace ──────┼──> ArtifactType
│  (heuristic_detector.py)  (duplicated)
│                    │
│  Validators ───────┤
│  (validator.py)    │
│                    │
│  CLI Defaults ─────┘
│  (defaults.py)
│
└─────────────────────────────────────┘
   ↓ (all feed into)
   Artifact (dataclass)
```

**Target Architecture:**

```
┌──────────────────────────────────────────┐
│  Unified Artifact Detection Core         │
│  (artifact_detection.py) - NEW MODULE    │
├──────────────────────────────────────────┤
│                                          │
│  • Canonical ArtifactType enum           │
│  • Artifact signatures (dir vs file)     │
│  • Container alias normalization         │
│  • Common detection result structure     │
│  • Shared detection algorithms           │
│                                          │
└──────────────────────────────────────────┘
   ↑ (used by all detection layers)
   │
   ├─→ Local Discovery (rebuilt)
   ├─→ Marketplace Heuristics (refactored)
   ├─→ Validators (aligned)
   └─→ CLI Defaults (standardized)
```

---

## 3. Goals & Success Criteria

### Functional Goals

| Goal | Acceptance Criteria |
|------|-------------------|
| **Single canonical type system** | One ArtifactType enum, imported everywhere; no duplicates in codebase |
| **Centralized artifact signatures** | All modules reference shared signatures (dir vs file, required manifests) |
| **Unified container aliases** | Shared normalization; supports: commands, agents, skills, hooks, mcp, subagents, mcp-servers, servers, claude-commands, claude-agents, claude-skills, claude-hooks |
| **Common detection result** | Standard `DetectionResult` dataclass with optional confidence, used across all detectors |
| **Consistent local detection** | All artifacts detected by local discovery have strict mode (100% confidence when rules match) |
| **Consistent marketplace detection** | Marketplace heuristics reuse shared rules for 80%+ of baseline detection, extend with confidence scoring |
| **Backwards compatible** | Existing collections continue to work; no breaking changes to Artifact class or public APIs |
| **Deprecated patterns flagged** | Directory-based commands/agents emit clear deprecation warnings |

### Non-Functional Goals

| Goal | Acceptance Criteria |
|------|-------------------|
| **Code consolidation** | Reduce detection-related code from 4,837 lines to ~2,500 lines (core + extensions) |
| **Test coverage** | 100+ test cases covering all detection contexts and edge cases |
| **Backwards compatibility** | All existing unit tests pass; no changes to external interfaces |
| **Clear migration path** | Deprecation warnings guide users away from legacy patterns |
| **Documentation** | All shared detection rules documented in core module docstrings |

---

## 4. Requirements

### Functional Requirements

#### 4.1 Canonical Type System

**FR-1.1: Single ArtifactType Enum**
- Create unified `ArtifactType` enum in shared detection module
- Include: SKILL, COMMAND, AGENT, HOOK, MCP (standardized names)
- Deprecate `MCP_SERVER` name; use `MCP` internally, translate to `mcp_server` in API/DB only
- Import and use in: artifact.py, discovery.py, heuristic_detector.py, validators
- Remove duplicate enum from heuristic_detector.py

**FR-1.2: Consistent Type Names**
- Local detection: Use enum, not strings
- Marketplace: Use shared enum, no local override
- API responses: Accept both enum and snake_case variants for backwards compatibility
- Database: Continue using mcp_server in schemas (handled by enum __str__)

#### 4.2 Artifact Signatures & Container Aliases

**FR-2.1: Shared Artifact Signatures**
- Define mapping: Artifact type → Container directory → Required manifest → File type
- Examples:
  - SKILL: container=skills, manifest=SKILL.md, type=directory
  - COMMAND: container=commands, manifest=none, type=file-only
  - AGENT: container=agents, manifest=none, type=file-only
  - HOOK: container=hooks, manifest=none, type=json-config (settings.json)
  - MCP: container=mcp, manifest=none, type=json-config (.mcp.json)

**FR-2.2: Container Alias Normalization**
- Accept aliases per type:
  - SKILL: skills, skill, claude-skills
  - COMMAND: commands, command, claude-commands
  - AGENT: agents, agent, subagents, claude-agents
  - HOOK: hooks, hook, claude-hooks
  - MCP: mcp, mcp-servers, servers, mcp_servers, claude-mcp
- Function: `normalize_container_name(name: str, artifact_type: ArtifactType) -> str`
- Returns canonical container name or raises InvalidContainerError

**FR-2.3: Manifest Files Configuration**
- Centralized manifest definitions:
  ```
  MANIFEST_FILES = {
      ArtifactType.SKILL: {"SKILL.md", "skill.md"},
      ArtifactType.COMMAND: {},  # No manifest required
      ArtifactType.AGENT: {},    # No manifest required
      ArtifactType.HOOK: {},     # JSON config only
      ArtifactType.MCP: {},      # JSON config only
  }
  ```
- Used by: validators, discovery, marketplace heuristics

#### 4.3 Common Detection Result Structure

**FR-3.1: DetectionResult Dataclass**
```python
@dataclass
class DetectionResult:
    artifact_type: ArtifactType
    name: str                       # Artifact name
    path: str                       # Relative path
    container_type: str             # Canonical container name
    detection_mode: str             # "strict" or "heuristic"
    confidence: int                 # 0-100, optional per mode
    manifest_file: Optional[str]    # Path to manifest (if found)
    metadata: Optional[ArtifactMetadata]
    detection_reasons: List[str]    # Why this type was chosen
    deprecation_warning: Optional[str]  # If pattern is deprecated
```

**FR-3.2: Detection Modes**
- `strict`: Local detection (rules match = 100% confidence, no scoring)
- `heuristic`: Marketplace detection (multi-signal scoring, 0-100 confidence)

#### 4.4 Detection Rules & Algorithms

**FR-4.1: Local Detection Rules (Strict Mode)**

Rules enforced uniformly across all artifacts:
- Container directory must be one of recognized names (normalized)
- SKILL: Must be directory with SKILL.md in root
- COMMAND: Single .md file only; no directories allowed
- AGENT: Single .md file only; no directories allowed
- HOOK: JSON in settings.json only
- MCP: JSON in .mcp.json only
- Nested artifacts (except skills) not detected at top level; found under container directories

Confidence: Always 100% when rules match; 0% otherwise.

**FR-4.2: Marketplace Detection Rules (Heuristic Mode)**

Reuse shared rules for baseline classification:
1. Directory/file structure validation (use shared signatures)
2. Manifest file detection (use shared manifests)
3. Container type mapping (use shared aliases)

Extend with marketplace-specific signals:
4. GitHub path heuristics (depth penalties)
5. Manual directory mapping overrides
6. Confidence scoring aggregation (0-100)

---

### Requirements Matrix

| ID | Requirement | Phase | Status |
|---|---|---|---|
| **FR-1.1** | Single ArtifactType enum | 1 | New |
| **FR-1.2** | Consistent type names everywhere | 1, 3, 4 | New |
| **FR-2.1** | Shared artifact signatures | 1 | New |
| **FR-2.2** | Container alias normalization | 1 | New |
| **FR-2.3** | Centralized manifest files | 1 | New |
| **FR-3.1** | DetectionResult dataclass | 1 | New |
| **FR-3.2** | Detection modes (strict/heuristic) | 1 | New |
| **FR-4.1** | Local detection rules | 2 | Refactor |
| **FR-4.2** | Marketplace detection rules | 3 | Refactor |
| **FR-5** | Validators use shared signatures | 4 | Refactor |
| **FR-6** | CLI defaults use shared inference | 4 | Refactor |
| **NFR-1** | 100+ test cases | 5 | New |
| **NFR-2** | Deprecation warnings for legacy patterns | 5 | New |

---

## 5. Detailed Design

### 5.1 Core Module: `skillmeat/core/artifact_detection.py`

**Exports:**
```python
# Type definitions
ArtifactType(Enum)
DetectionResult(dataclass)
ArtifactSignature(dataclass)
DetectionConfig(dataclass)

# Container & manifest definitions
ARTIFACT_SIGNATURES: Dict[ArtifactType, ArtifactSignature]
MANIFEST_FILES: Dict[ArtifactType, Set[str]]
CONTAINER_ALIASES: Dict[ArtifactType, Set[str]]

# Detection functions
normalize_container_name(name: str, artifact_type: ArtifactType) -> str
infer_artifact_type(path: Path) -> Optional[ArtifactType]
detect_artifact(path: Path, container_type: Optional[str] = None, mode: str = "strict") -> DetectionResult
extract_manifest_file(path: Path, artifact_type: ArtifactType) -> Optional[Path]
```

**Signature Definition:**
```python
@dataclass
class ArtifactSignature:
    type: ArtifactType
    container_names: Set[str]  # Canonical + aliases
    is_directory: bool
    requires_manifest: bool
    manifest_names: Set[str]
    allowed_nesting: bool  # Can be nested under container
    metadata_extractors: List[Callable]
```

**Detection Thresholds:**
- Local (strict mode): Type matches rules → 100% confidence
- Marketplace (heuristic): Aggregated scoring 0-100

### 5.2 Phase 1: Create Shared Detection Module

**Module Structure:**
```
skillmeat/core/
├── artifact_detection.py (NEW - ~400 lines)
│   ├── ArtifactType enum
│   ├── DetectionResult dataclass
│   ├── ARTIFACT_SIGNATURES registry
│   ├── MANIFEST_FILES registry
│   ├── CONTAINER_ALIASES registry
│   ├── normalize_container_name()
│   ├── infer_artifact_type()
│   ├── detect_artifact()
│   └── extract_manifest_file()
│
└── artifact.py (UPDATED - remove ArtifactType duplicate)
    └── Import ArtifactType from artifact_detection
```

**Key Decisions:**
- Container aliases are **configurable per type** (no global mapping)
- Detection result includes **reasons list** for debugging
- Mode parameter enables switching between strict/heuristic without changing function signature
- Deprecation warnings stored in result for logging

### 5.3 Phase 2: Rebuild Local Discovery

**Changes to `skillmeat/core/discovery.py`:**

1. Import shared module:
   ```python
   from skillmeat.core.artifact_detection import (
       ArtifactType, DetectionResult, detect_artifact, ARTIFACT_SIGNATURES
   )
   ```

2. Replace `_detect_artifact_type()` with shared detector:
   ```python
   def _detect_artifact(self, path: Path) -> DetectionResult:
       # Use detect_artifact() with strict mode
       return detect_artifact(path, mode="strict", container_type=self._inferred_container)
   ```

3. Recursively traverse container directories:
   - Current: Scans only immediate children
   - New: Recursively finds nested single-file artifacts (commands, agents)

4. Deprecation warnings:
   - Log warning if directory-based command/agent detected
   - Mark as "legacy" in results for future cleanup

### 5.4 Phase 3: Refactor Marketplace Heuristics

**Changes to `skillmeat/core/marketplace/heuristic_detector.py`:**

1. Remove local ArtifactType enum:
   ```python
   # REMOVE: Duplicate ArtifactType class
   # IMPORT: from skillmeat.core.artifact_detection import ArtifactType
   ```

2. Reuse shared signatures:
   ```python
   from skillmeat.core.artifact_detection import (
       ArtifactType, ARTIFACT_SIGNATURES, CONTAINER_ALIASES,
       normalize_container_name, detect_artifact
   )
   ```

3. Keep marketplace-specific features:
   - Confidence scoring (extend shared result)
   - Manual directory mapping (policy layer)
   - GitHub path heuristics (GitHub-specific)

4. Refactor scoring to use shared baseline:
   - Call `detect_artifact(path, mode="heuristic")` to get base type
   - Add marketplace-specific signals (depth, manual mapping)
   - Output confidence 0-100

### 5.5 Phase 4: Align Validators & Defaults

**Changes to `skillmeat/utils/validator.py`:**

1. Import shared signatures:
   ```python
   from skillmeat.core.artifact_detection import (
       ArtifactType, ARTIFACT_SIGNATURES, extract_manifest_file
   )
   ```

2. Replace ad-hoc validation with shared rules:
   ```python
   @staticmethod
   def validate_skill(path: Path) -> ValidationResult:
       sig = ARTIFACT_SIGNATURES[ArtifactType.SKILL]
       # Check: is_directory, has manifest_file
   ```

3. Deprecation warnings for legacy command/agent directories

**Changes to `skillmeat/defaults.py`:**

1. Import shared inference:
   ```python
   from skillmeat.core.artifact_detection import infer_artifact_type
   ```

2. Standardize return types:
   - Route through shared inference
   - Ensure consistent enum values

### 5.6 Phase 5: Testing & Safeguards

**Test Coverage (100+ test cases):**

| Context | Test Count | Examples |
|---|---|---|
| Type system | 12 | Enum values, name normalization, type conversions |
| Container aliases | 20 | All aliases, invalid names, case sensitivity |
| Artifact signatures | 30 | Directory validation, manifest detection, nesting rules |
| Local detection | 25 | All artifact types, nested discovery, deprecation warnings |
| Marketplace detection | 15 | Scoring, manual mappings, GitHub heuristics |
| Validators | 10 | Validation rules, error handling |
| CLI defaults | 8 | Name-based inference, fallbacks |

**Backwards Compatibility Safeguards:**
- Run all existing unit tests before/after each phase
- No changes to `Artifact` dataclass public interface
- API responses backwards compatible (accept old type names)
- Deprecation warnings only; no errors for legacy patterns (Phase 1-4)
- Removal of legacy patterns deferred to Phase 6+

---

## 6. Implementation Plan

### Phase Overview

| Phase | Focus | Duration | Tasks |
|---|---|---|---|
| **Phase 1** | Create shared detection module | 1 week | Types, signatures, core detection functions |
| **Phase 2** | Rebuild local discovery | 1 week | Import shared detector, recursive traversal, deprecation warnings |
| **Phase 3** | Refactor marketplace heuristics | 2 weeks | Remove duplicate enum, reuse shared rules, extend with scoring |
| **Phase 4** | Align validators and defaults | 1 week | Use shared signatures, standardize type names |
| **Phase 5** | Tests and migration safeguards | 2 weeks | Comprehensive testing, deprecation docs, migration guides |

### Phase 1: Shared Detection Module

**Deliverables:**
- `skillmeat/core/artifact_detection.py` (new module)
- Updated `skillmeat/core/artifact.py` (import ArtifactType from detection module)
- Initial unit tests (20+ test cases)

**Acceptance Criteria:**
- All test cases pass
- No import errors from other modules
- ArtifactType used consistently in artifact.py

### Phase 2: Local Discovery Rebuild

**Deliverables:**
- Updated `skillmeat/core/discovery.py`
- Recursive directory traversal
- Integration tests with Phase 1 module

**Acceptance Criteria:**
- All existing discovery tests pass
- New artifacts detected in nested directories
- Deprecation warnings logged for legacy patterns
- No regression in performance

### Phase 3: Marketplace Heuristics Refactor

**Deliverables:**
- Updated `skillmeat/core/marketplace/heuristic_detector.py`
- Removed duplicate ArtifactType enum
- Confidence scoring rewritten to use shared baseline

**Acceptance Criteria:**
- All existing marketplace tests pass
- 80%+ of detection logic uses shared rules
- Confidence scores match previous behavior
- Manual mappings still work

### Phase 4: Validators & Defaults Alignment

**Deliverables:**
- Updated `skillmeat/utils/validator.py`
- Updated `skillmeat/defaults.py`
- Type normalization tests

**Acceptance Criteria:**
- All validation tests pass
- Consistent type names across modules
- CLI defaults use shared inference
- No breaking changes to public APIs

### Phase 5: Tests & Migration Safeguards

**Deliverables:**
- Comprehensive test suite (100+ test cases)
- Migration guide for deprecated patterns
- Deprecation warning documentation
- Cross-context integration tests

**Acceptance Criteria:**
- 100+ test cases all passing
- Code coverage >90% for detection module
- All existing unit tests pass
- Migration guide reviewed

---

## 7. Data Models & Schemas

### ArtifactType Enum

```python
class ArtifactType(str, Enum):
    """Canonical artifact types supported by SkillMeat."""

    SKILL = "skill"       # Directory-based with SKILL.md
    COMMAND = "command"   # Single .md file
    AGENT = "agent"       # Single .md file
    HOOK = "hook"         # JSON in settings.json
    MCP = "mcp"           # JSON in .mcp.json

    # Context entity types (from agent-context-entities-v1)
    PROJECT_CONFIG = "project_config"
    SPEC_FILE = "spec_file"
    RULE_FILE = "rule_file"
    CONTEXT_FILE = "context_file"
    PROGRESS_TEMPLATE = "progress_template"
```

### DetectionResult

```python
@dataclass
class DetectionResult:
    artifact_type: ArtifactType
    name: str
    path: str
    container_type: str
    detection_mode: Literal["strict", "heuristic"]
    confidence: int  # 0-100
    manifest_file: Optional[str] = None
    metadata: Optional[ArtifactMetadata] = None
    detection_reasons: List[str] = field(default_factory=list)
    deprecation_warning: Optional[str] = None
```

### ArtifactSignature

```python
@dataclass
class ArtifactSignature:
    artifact_type: ArtifactType
    container_names: Set[str]
    is_directory: bool
    requires_manifest: bool
    manifest_names: Set[str]
    allowed_nesting: bool
```

### Registry Examples

```python
ARTIFACT_SIGNATURES: Dict[ArtifactType, ArtifactSignature] = {
    ArtifactType.SKILL: ArtifactSignature(
        artifact_type=ArtifactType.SKILL,
        container_names={"skills", "skill", "claude-skills"},
        is_directory=True,
        requires_manifest=True,
        manifest_names={"SKILL.md", "skill.md"},
        allowed_nesting=False,
    ),
    ArtifactType.COMMAND: ArtifactSignature(
        artifact_type=ArtifactType.COMMAND,
        container_names={"commands", "command", "claude-commands"},
        is_directory=False,
        requires_manifest=False,
        manifest_names=set(),
        allowed_nesting=True,
    ),
    # ... other types
}

CONTAINER_ALIASES: Dict[ArtifactType, Set[str]] = {
    ArtifactType.SKILL: {"skills", "skill", "claude-skills"},
    ArtifactType.COMMAND: {"commands", "command", "claude-commands"},
    ArtifactType.AGENT: {"agents", "agent", "subagents", "claude-agents"},
    ArtifactType.HOOK: {"hooks", "hook", "claude-hooks"},
    ArtifactType.MCP: {"mcp", "mcp-servers", "servers", "mcp_servers", "claude-mcp"},
}
```

---

## 8. API Contracts

### Shared Detection Functions

**`normalize_container_name(name: str, artifact_type: ArtifactType) -> str`**
- Input: Container directory name (any case, with/without aliases)
- Output: Canonical container name
- Raises: `InvalidContainerError` if name not recognized for type

**`infer_artifact_type(path: Path) -> Optional[ArtifactType]`**
- Input: Path to potential artifact
- Output: Detected type or None
- Logic: Check manifest files, then fallback to directory structure

**`detect_artifact(path: Path, container_type: Optional[str] = None, mode: str = "strict") -> DetectionResult`**
- Input: Path, optional container hint, detection mode
- Output: DetectionResult with confidence and reasons
- Modes: "strict" (local, 100% or 0%), "heuristic" (marketplace, 0-100%)

**`extract_manifest_file(path: Path, artifact_type: ArtifactType) -> Optional[Path]`**
- Input: Directory path, artifact type
- Output: Path to manifest file or None
- Checks all known manifest names for type

---

## 9. Backwards Compatibility & Migration

### Breaking Changes (None)

This refactor introduces **zero breaking changes**:
- `Artifact` dataclass unchanged (ArtifactType imported from new location)
- API responses continue to accept old type names
- Local discovery behavior preserved (same detection results)
- Marketplace scoring unchanged

### Backwards Compatible Additions

- Type name normalization (mcp_server → mcp internally, mcp_server in DB)
- New container aliases supported (subagents, mcp-servers, etc.)
- Deprecation warnings for legacy patterns (logged, not errored)

### Migration Guidance

**For existing collections:**
- No action required
- Directory-based commands/agents continue to work (with deprecation warnings)
- Recommend moving to single-file format for commands/agents

**For new collections:**
- Follow current conventions (skills as directories, commands/agents as files)
- Use standard container names (commands, agents, skills, hooks, mcp)

**For developers:**
- Import ArtifactType from `artifact_detection` module
- Use `detect_artifact()` for new detection logic
- Reference `ARTIFACT_SIGNATURES` for valid artifact structures

---

## 10. Testing Strategy

### Test Suite Organization

```
tests/
├── core/
│   ├── test_artifact_detection.py (NEW - 45 test cases)
│   │   ├── test_artifact_type_enum
│   │   ├── test_container_normalization
│   │   ├── test_artifact_signatures
│   │   ├── test_strict_mode_detection
│   │   └── test_detection_result_structure
│   │
│   ├── test_discovery_refactored.py (UPDATED)
│   │   ├── test_local_discovery_with_shared_detector
│   │   ├── test_nested_artifact_detection
│   │   ├── test_deprecation_warnings
│   │   └── test_backwards_compatibility
│   │
│   ├── marketplace/
│   │   └── test_heuristic_detector_refactored.py (UPDATED)
│   │       ├── test_heuristic_uses_shared_rules
│   │       ├── test_confidence_scoring
│   │       └── test_marketplace_backwards_compatibility
│   │
│   └── integration/
│       └── test_detection_consistency.py (NEW - 30 test cases)
│           ├── test_same_artifact_local_vs_marketplace
│           ├── test_all_artifact_types
│           ├── test_container_aliases
│           └── test_cross_module_consistency
│
└── utils/
    └── test_validator_refactored.py (UPDATED)
        ├── test_validators_use_shared_signatures
        └── test_type_normalization
```

### Test Coverage Requirements

- Unit tests: 80%+ coverage for artifact_detection.py
- Integration tests: All detection contexts covered
- Backwards compatibility: All existing tests pass
- Cross-module consistency: Same artifact yields same type everywhere

### Example Test Cases

```python
def test_skill_detection_strict_mode():
    """Skill with SKILL.md detected as SKILL with 100% confidence."""
    path = create_temp_skill(manifest="SKILL.md")
    result = detect_artifact(path, mode="strict")
    assert result.artifact_type == ArtifactType.SKILL
    assert result.confidence == 100

def test_container_alias_normalization():
    """All container aliases normalize to canonical form."""
    aliases = {"agents", "agent", "subagents", "claude-agents"}
    for alias in aliases:
        normalized = normalize_container_name(alias, ArtifactType.AGENT)
        assert normalized == "agents"

def test_local_discovery_uses_shared_detector():
    """Local discovery detects all artifacts via shared detector."""
    # Create directory with multiple artifact types
    # Run discovery
    # Verify all types detected correctly

def test_marketplace_scoring_based_on_shared_rules():
    """Marketplace scoring extends shared detection, not duplicates it."""
    # Detect same artifact with heuristic mode
    # Verify baseline matches shared rules
    # Verify confidence includes marketplace signals
```

---

## 11. Documentation & Communication

### Documentation Changes

**New Docs:**
- `.claude/context/artifact-detection-standards.md` - Developer reference
- `docs/architecture/detection-system-design.md` - Architecture overview
- `docs/migration/deprecated-artifact-patterns.md` - Migration guide

**Updated Docs:**
- `skillmeat/core/artifact_detection.py` - Comprehensive module docstrings
- `skillmeat/core/discovery.py` - Updated with deprecation notes
- `skillmeat/core/artifact.py` - Updated import source for ArtifactType

### Deprecation Warnings

**Log Format:**
```
DEPRECATED: Directory-based command/agent artifacts will no longer be supported.
  Location: ./.claude/commands/my_command/
  Migration: Move to single .md file under ./.claude/commands/
  Deadline: SkillMeat v1.0.0 (2026-Q3)
```

**Where Logged:**
- Local discovery: When directory-based command/agent detected
- Validators: When validating legacy patterns
- CLI: When processing legacy collections

---

## 12. Risk Assessment & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Type mismatch in marketplace | Low | High | Phase 5 integration tests; verify confidence scores unchanged |
| Regression in local discovery | Medium | Medium | Run all existing discovery tests in Phase 2; backwards compatibility safeguards |
| Container alias normalization breaks existing scans | Low | High | Centralize aliases; phase 5 testing with real repos |
| Deprecation warnings too aggressive | Medium | Low | Log warnings, don't error; clear migration path |
| Performance regression | Low | Medium | Benchmark detection times before/after each phase |

---

## 13. Success Metrics

### Quantitative Metrics

- **Code reduction**: 4,837 → 2,500 lines (48% reduction)
- **Test coverage**: 100+ test cases, >90% coverage on detection module
- **Type duplication**: 0 (from 2 enums)
- **Manifest file definitions**: 1 location (from 3)
- **Container alias definitions**: 1 location (from 3)

### Qualitative Metrics

- Developers report consistent artifact detection across tools
- No issues with type mismatches in changelog
- Marketplace and local discovery yield same classifications
- Clear, documented migration path for legacy patterns

---

## 14. Open Questions & Assumptions

### Open Questions

**Q1: Should MCP_SERVER be renamed to MCP in all APIs?**
- A: Not in this phase. Keep mcp_server in API/DB for backwards compatibility.
- Enum internally uses MCP, but API response can say mcp_server.
- Deferred to Phase 6 cleanup if needed.

**Q2: Should directory-based commands/agents be errors or warnings in Phase 1?**
- A: Warnings only (deprecation). Become errors only in Phase 6+.
- Allows existing collections to continue working during transition.

**Q3: Are container aliases user-configurable or fixed?**
- A: Fixed in v1. Future phases could make configurable via settings.

### Assumptions

**A1: Local detection is always strict mode**
- Assumption: .claude/ directories always follow strict rules (manifest files, proper containers)
- Rationale: Developers control their own .claude/ structure
- Risk: Custom directory structures may not be recognized (mitigated by deprecation warnings)

**A2: Marketplace detection extends local rules**
- Assumption: GitHub repo structures don't strictly follow manifests, but have same type patterns
- Rationale: GitHub users have diverse naming; heuristics capture intent
- Risk: Confidence scores may still vary (mitigated by integration tests)

**A3: No breaking changes to external APIs**
- Assumption: All changes are internal; public Artifact class, routers, schemas unchanged
- Rationale: This is a refactor, not a feature change
- Risk: If external APIs must change, deferred to Phase 6+

---

## 15. Appendices

### A. Container Alias Reference

| Type | Canonical | Aliases |
|---|---|---|
| SKILL | skills | skill, claude-skills |
| COMMAND | commands | command, claude-commands |
| AGENT | agents | agent, subagents, claude-agents |
| HOOK | hooks | hook, claude-hooks |
| MCP | mcp | mcp-servers, servers, mcp_servers, claude-mcp |

### B. Manifest File Reference

| Type | Manifest Files | Required |
|---|---|---|
| SKILL | SKILL.md, skill.md | Yes (directory must have one) |
| COMMAND | — | No (single .md file) |
| AGENT | — | No (single .md file) |
| HOOK | settings.json | No (JSON config only) |
| MCP | .mcp.json | No (JSON config only) |

### C. Artifact Signature Summary

| Type | Container | Structure | Manifest | Nesting |
|---|---|---|---|---|
| SKILL | skills | Directory | SKILL.md | No (top-level) |
| COMMAND | commands | Single .md file | — | Yes (under container) |
| AGENT | agents | Single .md file | — | Yes (under container) |
| HOOK | hooks | JSON (settings.json) | — | No (in-place) |
| MCP | mcp | JSON (.mcp.json) | — | No (in-place) |

### D. Phase-by-Phase Checklist

**Phase 1 Completion:**
- [ ] `artifact_detection.py` module created
- [ ] ArtifactType enum defined (5 primary types)
- [ ] DetectionResult dataclass defined
- [ ] ARTIFACT_SIGNATURES registry complete
- [ ] CONTAINER_ALIASES registry complete
- [ ] normalize_container_name() function implemented
- [ ] detect_artifact() function implemented
- [ ] 20+ unit tests pass
- [ ] Import errors resolved in artifact.py

**Phase 2 Completion:**
- [ ] discovery.py updated to use shared detector
- [ ] Recursive traversal added
- [ ] Deprecation warnings logged
- [ ] All existing discovery tests pass
- [ ] New nested artifact tests pass

**Phase 3 Completion:**
- [ ] heuristic_detector.py imports shared types
- [ ] Duplicate ArtifactType enum removed
- [ ] Confidence scoring rewritten
- [ ] Manual mappings still work
- [ ] All marketplace tests pass

**Phase 4 Completion:**
- [ ] validator.py uses shared signatures
- [ ] defaults.py uses shared inference
- [ ] Type normalization consistent
- [ ] All validation tests pass
- [ ] No breaking API changes

**Phase 5 Completion:**
- [ ] 100+ test cases all passing
- [ ] >90% code coverage
- [ ] All existing unit tests pass
- [ ] Migration guide documented
- [ ] Deprecation warnings clear

---

## 16. References

- **Report:** /docs/project_plans/reports/artifact-detection-standardization-2026-01-06.md
- **Code Analysis:** /.claude/context/artifact-detection-code-patterns.md
- **Claude Code Artifact Specs:** https://claude.com/docs/artifacts (authoritative types)
- **Current Detection Code:**
  - skillmeat/core/artifact.py (1,903 lines)
  - skillmeat/core/discovery.py (786 lines)
  - skillmeat/core/marketplace/heuristic_detector.py (1,675 lines)
  - skillmeat/utils/validator.py (279 lines)
  - skillmeat/defaults.py (194 lines)

---

**Document Version:** 1.0
**Last Updated:** 2026-01-06
**Status:** Ready for Phase 1 implementation
