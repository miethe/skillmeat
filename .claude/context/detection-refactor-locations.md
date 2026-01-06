---
title: Artifact Detection - Refactor Code Locations
description: Specific line references and code blocks for standardization refactor
references:
  - skillmeat/core/artifact.py
  - skillmeat/core/discovery.py
  - skillmeat/core/marketplace/heuristic_detector.py
  - skillmeat/utils/validator.py
  - skillmeat/defaults.py
last_verified: 2026-01-06
---

# Artifact Detection - Code Locations for Refactor

Quick reference for exact line numbers and patterns to standardize.

---

## 1. ArtifactType Definitions

### Location 1: artifact.py (Primary Definition)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/artifact.py`
**Lines**: 33-46

```python
class ArtifactType(str, Enum):
    """Types of Claude artifacts."""

    SKILL = "skill"
    COMMAND = "command"
    AGENT = "agent"
    # Future: MCP = "mcp", HOOK = "hook"

    # Context entity types (agent-context-entities-v1)
    PROJECT_CONFIG = "project_config"  # CLAUDE.md files
    SPEC_FILE = "spec_file"  # Specification documents (.claude/specs/)
    RULE_FILE = "rule_file"  # Rule files (.claude/rules/)
    CONTEXT_FILE = "context_file"  # Context documents (.claude/context/)
    PROGRESS_TEMPLATE = "progress_template"  # Progress tracking templates (.claude/progress/)
```

**Issue**: Primary definition here, but duplicated in heuristic_detector.py

### Location 2: heuristic_detector.py (Duplicate Definition)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/heuristic_detector.py`
**Lines**: 51-59

```python
class ArtifactType(str, Enum):
    """Supported artifact types."""

    SKILL = "skill"
    COMMAND = "command"
    AGENT = "agent"
    MCP_SERVER = "mcp_server"
    HOOK = "hook"
```

**Duplication Issue**:
- Different enum values (mcp_server vs MCP)
- Different scope (context types excluded)
- Should reference artifact.py instead

---

## 2. Manifest File Definitions

### Location 1: heuristic_detector.py (Source of Truth)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/heuristic_detector.py`
**Lines**: 92-100

```python
manifest_files: Dict[ArtifactType, Set[str]] = field(
    default_factory=lambda: {
        ArtifactType.SKILL: {"SKILL.md", "skill.md"},
        ArtifactType.COMMAND: {"COMMAND.md", "command.md"},
        ArtifactType.AGENT: {"AGENT.md", "agent.md"},
        ArtifactType.MCP_SERVER: {"MCP.md", "mcp.md", "server.json"},
        ArtifactType.HOOK: {"HOOK.md", "hook.md", "hooks.json"},
    }
)
```

**Status**: Current source of truth, but...

### Location 2: discovery.py (Hardcoded Check)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/discovery.py`
**Lines**: 449-470 (approximately)

```python
def _detect_artifact_type(self, artifact_path: Path) -> Optional[str]:
    """Detect artifact type from manifest files."""
    # Checks hardcoded:
    # - SKILL.md
    # - COMMAND.md, command.md
    # - AGENT.md, agent.md
    # - HOOK.md
    # - MCP.md, mcp.json
```

**Issue**: Redundant logic, should reference config

### Location 3: validator.py (Hardcoded Checks)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/utils/validator.py`
**Lines**: 50, 106, 173

```python
# Line 50: skill_md = path / "SKILL.md"
# Line 106: command_md = path / "command.md"
# Line 173: agent_md_upper = path / "AGENT.md"
```

**Issue**: Manifest names not configurable

---

## 3. Directory Pattern Definitions

### Location 1: heuristic_detector.py (Main Config)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/heuristic_detector.py`
**Lines**: 81-89

```python
dir_patterns: Dict[ArtifactType, Set[str]] = field(
    default_factory=lambda: {
        ArtifactType.SKILL: {"skills", "skill", "claude-skills"},
        ArtifactType.COMMAND: {"commands", "command", "claude-commands"},
        ArtifactType.AGENT: {"agents", "agent", "claude-agents"},
        ArtifactType.MCP_SERVER: {"mcp", "mcp-servers", "servers"},
        ArtifactType.HOOK: {"hooks", "hook", "claude-hooks"},
    }
)
```

### Location 2: heuristic_detector.py (Container Mapping)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/heuristic_detector.py`
**Lines**: 63-73

```python
CONTAINER_TYPE_MAPPING: Dict[str, "ArtifactType"] = {
    "commands": ArtifactType.COMMAND,
    "agents": ArtifactType.AGENT,
    "skills": ArtifactType.SKILL,
    "hooks": ArtifactType.HOOK,
    "mcp": ArtifactType.MCP_SERVER,
    "mcp-servers": ArtifactType.MCP_SERVER,
    "servers": ArtifactType.MCP_SERVER,
}
```

**Issue**: Duplication between dir_patterns and CONTAINER_TYPE_MAPPING

### Location 3: discovery.py (Normalization Logic)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/discovery.py`
**Lines**: 449-470 (approximately)

```python
def _normalize_type_from_dirname(self, dirname: str) -> Optional[str]:
    """Normalize directory name to artifact type."""
    # Custom normalization logic, should use config
```

**Issue**: Separate logic from heuristic_detector.py

---

## 4. Type Detection Logic

### Location 1: discovery.py (Local Detection)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/discovery.py`
**Lines**: 449-470

**Function**: `_detect_artifact_type()`

```python
# Check manifest files
# Check parent directory
# Validate structure
# Return type string
```

**Issues**:
- Checks manifest files individually
- Separate from heuristic scoring
- No confidence/ranking

### Location 2: validator.py (Structural Detection)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/utils/validator.py`
**Lines**: 241-279

**Function**: `detect_artifact_type()`

```python
# Check SKILL.md → SKILL
# Check AGENT.md/agent.md → AGENT
# Check .md files → COMMAND (fallback)
# Return None if cannot determine
```

**Issues**:
- Priority order hardcoded
- No integration with discovery.py
- Same logic, different implementation

### Location 3: heuristic_detector.py (Multi-Signal Detection)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/heuristic_detector.py`
**Lines**: 427-700+ (complex algorithm)

**Function**: `_detect_single_file_artifacts()`, `analyze_paths()`, scoring methods

```python
# Multiple signals combined
# Confidence scoring
# Manual mappings with inheritance
```

**Status**: Most sophisticated, but isolated

### Location 4: defaults.py (Name-Based Detection)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/defaults.py`
**Lines**: 32-101

**Function**: `detect_artifact_type()`

```python
_TYPE_PATTERNS = [
    (re.compile(r'.*-(cli|cmd|command)$'), 'command'),
    (re.compile(r'.*-(agent|bot)$'), 'agent'),
]
_DEFAULT_TYPE = 'skill'
```

**Issue**: Pattern matching not integrated with other methods

---

## 5. Confidence Scoring

### Location: heuristic_detector.py (Only Implementation)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/heuristic_detector.py`
**Lines**: 16-48

**Scoring System**:

```python
# Line 16-19: Score ranges
MAX_RAW_SCORE = 120

# Line 27-48: Normalization function
def normalize_score(raw_score: int) -> int:
    """Normalize raw score to 0-100 scale."""
    if raw_score <= 0:
        return 0
    if raw_score >= MAX_RAW_SCORE:
        return 100
    return round((raw_score / MAX_RAW_SCORE) * 100)
```

**Signal Weights** (Lines 117-125):
```python
dir_name_weight: int = 10
manifest_weight: int = 20
extension_weight: int = 5
parent_hint_weight: int = 15
frontmatter_weight: int = 15
container_hint_weight: int = 25
frontmatter_type_weight: int = 30
```

**Issue**: Scoring algorithm isolated to marketplace module

---

## 6. Metadata Extraction

### Location: artifact.py (Metadata Class)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/artifact.py`
**Lines**: 59-104

```python
@dataclass
class ArtifactMetadata:
    """Metadata extracted from artifact files (SKILL.md, COMMAND.md, AGENT.md)."""

    title: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    license: Optional[str] = None
    version: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)
```

**Methods**:
- `to_dict()` (Lines 71-90)
- `from_dict()` (Lines 92-104)

**External Extraction**:
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/utils/metadata.py` (referenced but not provided)

**Function**: `extract_artifact_metadata()`
**Function**: `extract_yaml_frontmatter()`

**Issue**: Metadata extraction scattered, no schema validation

---

## 7. Validation Methods

### Location 1: validator.py (Type-Specific)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/utils/validator.py`

**Functions**:
- `validate_skill()` (Lines 23-74)
- `validate_command()` (Lines 77-141)
- `validate_agent()` (Lines 144-212)
- `validate()` (Lines 215-238) - router
- `detect_artifact_type()` (Lines 241-279) - auto-detection

**Validation Steps**:
1. Check path exists
2. Check structure (directory vs file)
3. Check manifest files
4. Check content non-empty

### Location 2: discovery.py (Validation in Discovery)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/discovery.py`
**Lines**: 410 (approximately)

**Function**: `_validate_artifact()`

```python
# Checks artifact structure
# Delegates to validator.py
```

---

## 8. Container Type Handling

### Location 1: Container Detection
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/heuristic_detector.py`
**Lines**: 324-368

**Functions**:
- `_get_container_type()` (Lines 324-352)
- `_is_container_directory()` (Lines 354-368)

```python
CONTAINER_TYPE_MAPPING: Dict[str, ArtifactType] = {
    "commands": ArtifactType.COMMAND,
    "agents": ArtifactType.AGENT,
    "skills": ArtifactType.SKILL,
    "hooks": ArtifactType.HOOK,
    "mcp": ArtifactType.MCP_SERVER,
    "mcp-servers": ArtifactType.MCP_SERVER,
    "servers": ArtifactType.MCP_SERVER,
}
```

### Location 2: Single-File Artifact Detection
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/heuristic_detector.py`
**Lines**: 427-560+ (approximately)

**Function**: `_detect_single_file_artifacts()`

```python
# Detects .md files as standalone artifacts
# Respects container type hints
# Excludes manifest and documentation files
```

**Issues**:
- Complex logic specific to single-file handling
- Bug fixes embedded (single-file artifact detection)
- Should be generalized

---

## 9. Manual Mapping System

### Location: heuristic_detector.py
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/heuristic_detector.py`
**Lines**: 139-286

**Initialization** (Lines 139-182):
```python
def __init__(
    self,
    config: Optional[DetectionConfig] = None,
    enable_frontmatter_detection: bool = False,
    manual_mappings: Optional[Dict[str, str]] = None,
):
```

**Manual Mapping Checking** (Lines 211-286):
```python
def _check_manual_mapping(
    self, dir_path: str
) -> Optional[Tuple[ArtifactType, str, int]]:
```

**Features**:
- Hierarchical path matching
- Inheritance depth tracking
- Confidence scores by depth:
  - Exact: 95%
  - Depth 1: 92%
  - Depth 2: 89%
  - Depth 3+: 86%

**Issue**: Isolated to heuristic detector, not used by discovery or validator

---

## 10. Error Handling

### Location 1: discovery.py (Collection)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/discovery.py`
**Lines**: 222-238

```python
except PermissionError as e:
    error_msg = f"Permission denied accessing {type_dir}: {e}"
    logger.warning(error_msg)
    errors.append(error_msg)
except Exception as e:
    error_msg = f"Error scanning {type_dir}: {e}"
    logger.error(error_msg, exc_info=True)
    errors.append(error_msg)
```

**Philosophy**: Collect errors, continue scan

### Location 2: validator.py (Binary Result)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/utils/validator.py`
**Lines**: 10-16

```python
@dataclass
class ValidationResult:
    """Result of artifact validation."""

    is_valid: bool
    error_message: Optional[str] = None
    artifact_type: Optional[ArtifactType] = None
```

**Philosophy**: Pass/fail with optional error message

### Location 3: heuristic_detector.py (Graceful Degradation)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/heuristic_detector.py`
**Lines**: 171-175

```python
else:
    logger.warning(
        "Invalid artifact type '%s' in manual mapping for path '%s'",
        type_str,
        path,
    )
```

**Philosophy**: Log and skip, don't fail

---

## Summary: Key Duplication Points

### Type Definitions
- **Primary**: artifact.py:33-46
- **Duplicate**: heuristic_detector.py:51-59
- **Action**: Remove duplicate, import from artifact.py

### Manifest Files
- **Primary**: heuristic_detector.py:92-100
- **Referenced**: discovery.py (hardcoded), validator.py (hardcoded)
- **Action**: Create central registry, import everywhere

### Directory Patterns
- **Primary**: heuristic_detector.py:81-89
- **Mapping**: heuristic_detector.py:63-73
- **Referenced**: discovery.py (custom logic)
- **Action**: Centralize, remove duplication

### Type Detection
- **discovery.py**: Local manifest-based detection
- **validator.py**: Structural detection with fallback
- **heuristic_detector.py**: Multi-signal scoring
- **defaults.py**: Name-based pattern matching
- **Action**: Create abstract interface, implement detectors as strategies

### Metadata Extraction
- **artifact.py**: ArtifactMetadata class
- **utils/metadata.py**: extract_artifact_metadata()
- **discovery.py**: Uses extraction
- **heuristic_detector.py**: Optional frontmatter parsing
- **Action**: Centralize extraction logic, schema validation

