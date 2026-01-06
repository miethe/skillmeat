---
title: Artifact Detection Code Patterns - SkillMeat
description: Comprehensive analysis of detection mechanisms across five core modules
references:
  - skillmeat/core/artifact.py
  - skillmeat/core/discovery.py
  - skillmeat/core/marketplace/heuristic_detector.py
  - skillmeat/utils/validator.py
  - skillmeat/defaults.py
last_verified: 2026-01-06
---

# Artifact Detection Code Patterns

## Overview

SkillMeat uses a multi-layered detection system across five modules to identify, validate, and classify artifacts. This document maps current patterns for standardization refactoring.

**Total Code**: 4,837 lines across 5 files
- Core artifact definitions: 1,903 lines
- Discovery service: 786 lines
- Heuristic detection: 1,675 lines
- Validation: 279 lines
- Smart defaults: 194 lines

---

## 1. Core Artifact Definitions (`skillmeat/core/artifact.py`)

**File Size**: 1,903 lines | **Type**: Core data model + manager

### ArtifactType Enum (Lines 33-46)

Currently supported types:
```python
class ArtifactType(str, Enum):
    SKILL = "skill"              # Full implementations
    COMMAND = "command"           # CLI commands
    AGENT = "agent"               # AI agents
    # Future: MCP = "mcp"

    # Context entity types (agent-context-entities-v1)
    PROJECT_CONFIG = "project_config"    # CLAUDE.md
    SPEC_FILE = "spec_file"               # .claude/specs/
    RULE_FILE = "rule_file"               # .claude/rules/
    CONTEXT_FILE = "context_file"         # .claude/context/
    PROGRESS_TEMPLATE = "progress_template" # .claude/progress/
```

**Status**: 7 active types (3 primary + 4 context types)

### Artifact Metadata (Lines 59-104)

```python
@dataclass
class ArtifactMetadata:
    title: Optional[str]
    description: Optional[str]
    author: Optional[str]
    license: Optional[str]
    version: Optional[str]
    tags: List[str]
    dependencies: List[str]
    extra: Dict[str, Any]
```

**Extraction**: Via TOML serialization/deserialization

### Artifact Class (Lines 108-224)

Core unified representation:
```python
@dataclass
class Artifact:
    name: str                      # Artifact name
    type: ArtifactType             # Type classification
    path: str                       # Relative to collection root
    origin: str                     # "local" or "github"
    metadata: ArtifactMetadata      # Extracted metadata
    added: datetime                 # Creation timestamp
    upstream: Optional[str]         # GitHub URL if from GitHub
    version_spec: Optional[str]     # "latest", "v1.0.0", branch
    resolved_sha: Optional[str]     # Git SHA
    resolved_version: Optional[str] # Resolved version string
```

**Security**: Path traversal validation on instantiation
- Name cannot contain `/`, `\`, `..`, or start with `.`

---

## 2. Local Discovery (`skillmeat/core/discovery.py`)

**File Size**: 786 lines | **Type**: Service layer

### Supported Types (Line 109)
```python
supported_types: List[str] = ["skill", "command", "agent", "hook", "mcp"]
```

### Detection Modes (Lines 111-140)

Three scan modes:
1. **Project mode**: Scans `.claude/` subdirectories
2. **Collection mode**: Scans `collection/artifacts/` subdirectories
3. **Auto mode**: Detects based on directory structure

### Detection Flow (`discover_artifacts()`)

1. **Type directory normalization** (Line 211):
   ```python
   artifact_type = self._normalize_type_from_dirname(type_dir.name)
   ```

2. **Artifact scanning** (Lines 218-221):
   - Scans type directory for artifacts
   - Detects artifact type from structure
   - Extracts metadata
   - Validates structure

3. **Filtering**:
   - **Existence check** (Line 250): Filters already-imported artifacts
   - **Skip preferences** (Lines 284-329): Respects user skip list
   - **Importability** (Line 257): Returns only new artifacts

### Detection Logic (`_detect_artifact_type()`)

Priority order:
1. Check for manifest files (`SKILL.md`, `COMMAND.md`, `AGENT.md`)
2. Infer from directory structure
3. Fallback to type from parent directory name

---

## 3. Marketplace Heuristic Detection (`skillmeat/core/marketplace/heuristic_detector.py`)

**File Size**: 1,675 lines | **Type**: Complex heuristic engine

### Scoring System

**Max Raw Score**: 120 points (normalized to 0-100)

Signal breakdown:
```
dir_name:           10 points  (10%)
manifest:           20 points  (17%)
extensions:          5 points  (4%)
parent_hint:        15 points  (13%)
frontmatter:        15 points  (13%)
container_hint:     25 points  (21%)
frontmatter_type:   30 points  (25%)
```

**Normalization** (Lines 27-48):
```python
def normalize_score(raw_score: int) -> int:
    """Normalize raw score to 0-100 scale."""
    if raw_score <= 0:
        return 0
    if raw_score >= MAX_RAW_SCORE:
        return 100
    return round((raw_score / MAX_RAW_SCORE) * 100)
```

### Detection Configuration (Lines 77-125)

```python
@dataclass
class DetectionConfig:
    # Directory name patterns
    dir_patterns: Dict[ArtifactType, Set[str]] = {
        ArtifactType.SKILL: {"skills", "skill", "claude-skills"},
        ArtifactType.COMMAND: {"commands", "command", "claude-commands"},
        ArtifactType.AGENT: {"agents", "agent", "claude-agents"},
        ArtifactType.MCP_SERVER: {"mcp", "mcp-servers", "servers"},
        ArtifactType.HOOK: {"hooks", "hook", "claude-hooks"},
    }

    # Manifest filenames
    manifest_files: Dict[ArtifactType, Set[str]] = {
        ArtifactType.SKILL: {"SKILL.md", "skill.md"},
        ArtifactType.COMMAND: {"COMMAND.md", "command.md"},
        ArtifactType.AGENT: {"AGENT.md", "agent.md"},
        ArtifactType.MCP_SERVER: {"MCP.md", "mcp.md", "server.json"},
        ArtifactType.HOOK: {"HOOK.md", "hook.md", "hooks.json"},
    }

    # Thresholds
    min_confidence: int = 30    # Minimum score to report
    max_depth: int = 10          # Max directory depth
```

### Container Type Mapping (Lines 61-73)

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

### Multi-Signal Scoring Algorithm

1. **Directory Name Signal** (10pts):
   - Matches dir pattern for artifact type
   - Applied when dir name matches config patterns

2. **Manifest File Signal** (20pts):
   - Strongest structural indicator
   - Looks for `SKILL.md`, `COMMAND.md`, etc.

3. **Extension Signal** (5pts):
   - File extensions: `.md`, `.py`, `.ts`, `.js`, `.json`, `.yaml`, `.yml`

4. **Parent Hint Signal** (15pts):
   - Type hint from parent directory name
   - Applied hierarchically up the path

5. **Frontmatter Signal** (15pts):
   - YAML frontmatter extraction
   - Looks for metadata blocks

6. **Container Hint Signal** (25pts):
   - Bonus when detected type matches container
   - Example: Found in `commands/` directory → infer COMMAND

7. **Frontmatter Type Signal** (30pts):
   - Strongest signal: explicit type in metadata
   - Direct field in YAML frontmatter

### Manual Mappings (Lines 211-286)

Hierarchical path override system:
```python
manual_mappings: Dict[str, str] = {
    "path/to/dir": "skill",
    "another/path": "command"
}
```

Confidence scores by match depth:
- Exact match: 95%
- Depth 1: 92%
- Depth 2: 89%
- Depth 3+: 86%

### Single-File Detection (Lines 427-499)

Detects `.md` files as standalone artifacts:
- Respects container type hints
- Excludes manifest files (`skill.md`, `command.md`, etc.)
- Filters out documentation files
- Prevents false positives inside artifact directories

---

## 4. Structural Validation (`skillmeat/utils/validator.py`)

**File Size**: 279 lines | **Type**: Validation utilities

### Validation by Type

#### Skill Validation (Lines 23-74)
Requirements:
- Must be a **directory**
- Must contain `SKILL.md` in root
- `SKILL.md` must have non-empty content

```python
@staticmethod
def validate_skill(path: Path) -> ValidationResult:
    # Check is_dir()
    # Check SKILL.md exists
    # Check content is non-empty
```

#### Command Validation (Lines 77-141)
Requirements:
- Can be `.md` file OR directory
- If file: must be `.md` extension
- If directory: must contain `.md` file (prefer `command.md`)
- File must have content

```python
@staticmethod
def validate_command(path: Path) -> ValidationResult:
    # Check is_file() or is_dir()
    # Look for .md files (prefer command.md)
    # Validate content
```

#### Agent Validation (Lines 144-212)
Requirements:
- Can be `.md` file OR directory
- If directory: prefer `AGENT.md` or `agent.md`
- Fallback to any `.md` file
- Content must be non-empty

### Auto-Detection (Lines 241-279)

Priority order:
1. Contains `SKILL.md` → SKILL
2. Contains `AGENT.md` or `agent.md` → AGENT
3. Is `.md` file or contains `.md` files → COMMAND (fallback)
4. Return None if cannot determine

**Note**: Detection is structural only, no heuristic scoring

---

## 5. Smart Name-Based Inference (`skillmeat/defaults.py`)

**File Size**: 194 lines | **Type**: CLI defaults engine

### Pattern-Based Detection (Lines 32-35)

```python
_TYPE_PATTERNS = [
    (re.compile(r'.*-(cli|cmd|command)$'), 'command'),
    (re.compile(r'.*-(agent|bot)$'), 'agent'),
]
_DEFAULT_TYPE = 'skill'
```

### Detection Logic (`detect_artifact_type()`)

1. Check suffix patterns in order (first match wins)
2. Apply regex matching (case-insensitive)
3. Fallback to 'skill' for everything else

**Examples**:
```
"my-cli"      → "command"
"helper-cmd"  → "command"
"bot-agent"   → "agent"
"my-bot"      → "agent"
"canvas"      → "skill"    (default)
"widget-tool" → "skill"    (no match)
```

### Integration (`apply_defaults()`)

Applied when `--smart-defaults` flag is set:
1. Detects output format (TTY vs piped)
2. Gets default project path
3. Gets default collection name
4. **Detects artifact type from name** if type not specified

---

## Detection Decision Tree

```
Input: File/directory path

├─ Is it a GitHub repository?
│  └─→ Use Heuristic Detector (marketplace)
│       • Multi-signal scoring
│       • 0-100 confidence
│       • Handles nested structures
│
├─ Is it in .claude/ or collection/artifacts/?
│  └─→ Use Local Discovery (discovery.py)
│       • Type from parent directory
│       • Manifest file detection
│       • Validation
│
├─ Is it a specific artifact file?
│  └─→ Use Validator (validator.py)
│       • Structural validation only
│       • No heuristics
│       • Type detection from structure
│
└─ CLI operation with artifact name?
   └─→ Use Smart Defaults (defaults.py)
        • Name-based pattern matching
        • Suffix inference
        • Fallback to 'skill'
```

---

## Key Patterns

### 1. Type Normalization

All modules normalize type names consistently:
```
"skill", "skill" → ArtifactType.SKILL
"command" → ArtifactType.COMMAND
"agent" → ArtifactType.AGENT
```

### 2. Manifest File Identification

Primary detection signal across all modules:
```
SKILL.md, skill.md          → Skill
COMMAND.md, command.md      → Command
AGENT.md, agent.md          → Agent
HOOK.md, hook.md            → Hook
MCP.md, mcp.md, server.json → MCP Server
```

### 3. Directory Structure Hints

Container directories imply type:
```
.claude/skills/      → Skills container
.claude/commands/    → Commands container
.claude/agents/      → Agents container
.claude/hooks/       → Hooks container
.claude/mcp/         → MCP servers container
```

### 4. Metadata Extraction

Consistent metadata structure:
- Title, description, author, license, version
- Tags and dependencies
- Extra fields for extensibility

### 5. Confidence/Validation Levels

- **100%**: Manifest file found (e.g., SKILL.md)
- **95%**: Manual mapping (exact match)
- **92%**: Manual mapping (parent dir)
- **30-80%**: Heuristic scoring
- **N/A**: Structural validation (pass/fail only)

---

## Integration Points

### Detection Flow

1. **Upload/Import** → Validator (structural check)
2. **Marketplace Scan** → Heuristic Detector (scoring)
3. **Project Scan** → Local Discovery (type inference)
4. **CLI Operations** → Smart Defaults (name inference)

### Artifact Instance Creation

All detection methods feed into unified `Artifact` dataclass:
```python
artifact = Artifact(
    name=detected_name,
    type=detected_type,      # From any detection module
    path=artifact_path,
    origin="local" | "github",
    metadata=extracted_metadata,
    added=datetime.utcnow()
)
```

---

## Standardization Opportunities

### Current Inconsistencies

1. **Type Definition Duplication**:
   - `ArtifactType` enum in `artifact.py`
   - `ArtifactType` enum in `heuristic_detector.py`
   - Both define same types with slightly different subsets

2. **Manifest Files**:
   - Hardcoded in multiple locations
   - No single source of truth for valid manifest names

3. **Directory Patterns**:
   - Stored in `DetectionConfig` dataclass
   - Should be centralized with validation config

4. **Detection Logic**:
   - Four separate implementations of type detection
   - No common interface or base class
   - Duplicate logic for manifest file checking

### Proposed Standardization

1. **Central Registry**:
   - Single source for artifact types
   - Centralized manifest file definitions
   - Unified container directory mapping

2. **Abstract Detector Interface**:
   - Common base class for all detectors
   - Standard `detect()` return type
   - Confidence/validation scores normalized

3. **Metadata Extraction**:
   - Centralize frontmatter parsing
   - Consistent field mapping
   - Validation against schema

4. **Configuration Model**:
   - Single `ArtifactDetectionConfig` class
   - Covers all detection patterns
   - Easily extensible for new types

