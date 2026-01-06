---
type: progress
prd: "artifact-detection-standardization"
phase: 1
phase_title: "Create Shared Detection Core Module"
status: pending
progress: 0
total_tasks: 9
completed_tasks: 0
story_points: 13
duration: "1 week"

tasks:
  - id: "TASK-1.1"
    title: "Define Core Data Structures"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: []
    story_points: 3
    description: "Create ArtifactType enum, DetectionResult dataclass, ArtifactSignature dataclass"

  - id: "TASK-1.2"
    title: "Create Artifact Signatures Registry"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-1.1"]
    story_points: 3
    description: "Define ARTIFACT_SIGNATURES dict mapping ArtifactType to signature requirements"

  - id: "TASK-1.3"
    title: "Define Container Alias Registries"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-1.1"]
    story_points: 2
    description: "Create CONTAINER_ALIASES and MANIFEST_FILES registries"

  - id: "TASK-1.4"
    title: "Implement normalize_container_name()"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-1.3"]
    story_points: 2
    description: "Container name normalization function with all aliases support"

  - id: "TASK-1.5"
    title: "Implement Core Detection Functions"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-1.1", "TASK-1.2", "TASK-1.3", "TASK-1.4"]
    story_points: 3
    description: "Implement infer_artifact_type(), detect_artifact(), extract_manifest_file()"

  - id: "TASK-1.6"
    title: "Create Custom Exceptions"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: []
    story_points: 1
    description: "Define InvalidContainerError, InvalidArtifactTypeError, DetectionError"

  - id: "TASK-1.7"
    title: "Update artifact.py Imports"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-1.1"]
    story_points: 1
    description: "Import ArtifactType from new detection module"

  - id: "TASK-1.8"
    title: "Write Unit Tests"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-1.1", "TASK-1.2", "TASK-1.3", "TASK-1.4", "TASK-1.5", "TASK-1.6", "TASK-1.7"]
    story_points: 2
    description: "Create 20+ test cases covering all major functions"

  - id: "TASK-1.9"
    title: "Documentation and Docstrings"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-1.8"]
    story_points: 1
    description: "Add comprehensive module-level docstrings"

parallelization:
  batch_1: ["TASK-1.1", "TASK-1.6"]
  batch_2: ["TASK-1.2", "TASK-1.3", "TASK-1.7"]
  batch_3: ["TASK-1.4"]
  batch_4: ["TASK-1.5"]
  batch_5: ["TASK-1.8"]
  batch_6: ["TASK-1.9"]

blockers: []
notes: []
---

# Phase 1: Create Shared Detection Core Module

## Overview

Create the unified `artifact_detection.py` module with canonical types, artifact signatures, and core detection functions. This becomes the single source of truth for all artifact detection.

## Key Outputs

- New `skillmeat/core/artifact_detection.py` (~400 lines)
- Updated `skillmeat/core/artifact.py` (import ArtifactType)
- Initial test suite (20+ test cases)

## Orchestration Quick Reference

**Batch 1** (Parallel - no dependencies):
```python
Task("python-backend-engineer", """TASK-1.1: Define Core Data Structures

Create skillmeat/core/artifact_detection.py with:
1. ArtifactType(str, Enum) with values: SKILL, COMMAND, AGENT, HOOK, MCP
2. DetectionResult dataclass with fields: artifact_type, name, path, container_type, detection_mode, confidence, manifest_file, metadata, detection_reasons, deprecation_warning
3. ArtifactSignature dataclass with fields: artifact_type, container_names, is_directory, requires_manifest, manifest_names, allowed_nesting

All dataclasses need proper type hints and docstrings.""")

Task("python-backend-engineer", """TASK-1.6: Create Custom Exceptions

In skillmeat/core/artifact_detection.py add:
1. InvalidContainerError - raised by normalize_container_name()
2. InvalidArtifactTypeError - raised for invalid type values
3. DetectionError - base exception for detection failures

Proper inheritance hierarchy with clear error messages.""")
```

**Batch 2** (After TASK-1.1):
```python
Task("python-backend-engineer", """TASK-1.2: Create Artifact Signatures Registry

Add ARTIFACT_SIGNATURES dict to artifact_detection.py:
- SKILL: is_directory=True, requires_manifest=True, manifest_names={SKILL.md, skill.md}, allowed_nesting=False
- COMMAND: is_directory=False, requires_manifest=False, allowed_nesting=True
- AGENT: is_directory=False, requires_manifest=False, allowed_nesting=True
- HOOK: is_directory=False, requires_manifest=False, manifest_names={settings.json}
- MCP: is_directory=False, requires_manifest=False, manifest_names={.mcp.json}""")

Task("python-backend-engineer", """TASK-1.3: Define Container Alias Registries

Add to artifact_detection.py:
1. CONTAINER_ALIASES dict mapping ArtifactType to Set[str]:
   - SKILL: {skills, skill, claude-skills}
   - COMMAND: {commands, command, claude-commands}
   - AGENT: {agents, agent, subagents, claude-agents}
   - HOOK: {hooks, hook, claude-hooks}
   - MCP: {mcp, mcp-servers, servers, mcp_servers, claude-mcp}

2. MANIFEST_FILES dict mapping ArtifactType to Set[str] of valid manifest filenames""")

Task("python-backend-engineer", """TASK-1.7: Update artifact.py Imports

Update skillmeat/core/artifact.py:
1. Add: from skillmeat.core.artifact_detection import ArtifactType
2. Remove any local ArtifactType definition
3. Ensure Artifact class works with imported ArtifactType
4. Verify no circular imports
5. All artifact.py tests must pass""")
```

**Batch 3** (After TASK-1.3):
```python
Task("python-backend-engineer", """TASK-1.4: Implement normalize_container_name()

Add to artifact_detection.py:
def normalize_container_name(name: str, artifact_type: ArtifactType) -> str
- Case-insensitive normalization
- Returns canonical container name
- Raises InvalidContainerError if unrecognized
- Supports all CONTAINER_ALIASES

Examples:
- normalize_container_name("subagents", ArtifactType.AGENT) -> "agents"
- normalize_container_name("SKILLS", ArtifactType.SKILL) -> "skills"
- normalize_container_name("mcp-servers", ArtifactType.MCP) -> "mcp" """)
```

**Batch 4** (After TASK-1.4):
```python
Task("python-backend-engineer", """TASK-1.5: Implement Core Detection Functions

Add to artifact_detection.py:
1. infer_artifact_type(path: Path) -> Optional[ArtifactType]
   - Check manifest files, fallback to directory structure

2. detect_artifact(path: Path, container_type: Optional[str], mode: str = "strict") -> DetectionResult
   - Strict mode: 100% confidence if rules match
   - Heuristic mode: 0-100 confidence
   - Include detection_reasons list

3. extract_manifest_file(path: Path, artifact_type: ArtifactType) -> Optional[Path]
   - Case-insensitive manifest search""")
```

**Batch 5** (After TASK-1.5):
```python
Task("python-backend-engineer", """TASK-1.8: Write Unit Tests

Create tests/core/test_artifact_detection.py with 20+ test cases:
- ArtifactType enum (5 tests): values, string conversion, from string
- Container normalization (8 tests): all aliases, case sensitivity, errors
- Signatures (4 tests): all types defined, correct values
- Detection functions (3 tests): basic detection, modes

Use pytest fixtures for temp directories. All tests must pass.""")
```

**Batch 6** (After TASK-1.8):
```python
Task("python-backend-engineer", """TASK-1.9: Documentation and Docstrings

Add comprehensive documentation to artifact_detection.py:
- Module docstring explaining purpose and key exports
- All classes have complete docstrings with examples
- All functions have docstrings with parameters, returns, raises
- Inline comments for complex logic
- Examples for common detection patterns""")
```

## Quality Gates

- [ ] All 9 tasks completed
- [ ] No linting errors (black, flake8, mypy)
- [ ] 20+ unit tests passing
- [ ] >90% coverage on artifact_detection.py
- [ ] No circular imports
- [ ] artifact.py imports work correctly

## Files to Create/Modify

| Action | File |
|--------|------|
| CREATE | `skillmeat/core/artifact_detection.py` |
| MODIFY | `skillmeat/core/artifact.py` |
| CREATE | `tests/core/test_artifact_detection.py` |
