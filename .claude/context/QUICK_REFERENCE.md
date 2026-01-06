# Artifact Detection - Quick Reference Guide

**For planning standardization refactor**

---

## Module Overview (Absolute Paths)

| Module | Path | Lines | Purpose | Status |
|--------|------|-------|---------|--------|
| **artifact.py** | `/skillmeat/core/artifact.py` | 1,903 | Type definitions, unified Artifact class | Primary source |
| **discovery.py** | `/skillmeat/core/discovery.py` | 786 | Local .claude/ directory scanning | Active detection |
| **heuristic_detector.py** | `/skillmeat/core/marketplace/heuristic_detector.py` | 1,675 | GitHub marketplace detection | Complex heuristics |
| **validator.py** | `/skillmeat/utils/validator.py` | 279 | Structural validation | Validation only |
| **defaults.py** | `/skillmeat/defaults.py` | 194 | CLI smart defaults | Name inference |

---

## Key Code Locations

### ArtifactType Enum Definition
- **Primary**: `artifact.py:33-46` (7 types including context entities)
- **Duplicate**: `heuristic_detector.py:51-59` (5 types, excludes context)
- **Action**: Consolidate, use single enum

### Manifest File Registry
- **Defined**: `heuristic_detector.py:92-100` (Lines 92-100)
  ```python
  manifest_files: Dict[ArtifactType, Set[str]] = {
      ArtifactType.SKILL: {"SKILL.md", "skill.md"},
      ArtifactType.COMMAND: {"COMMAND.md", "command.md"},
      ArtifactType.AGENT: {"AGENT.md", "agent.md"},
      ArtifactType.MCP_SERVER: {"MCP.md", "mcp.md", "server.json"},
      ArtifactType.HOOK: {"HOOK.md", "hook.md", "hooks.json"},
  }
  ```
- **Hardcoded in**: `discovery.py`, `validator.py`
- **Action**: Create central registry

### Directory Pattern Mappings
- **Config**: `heuristic_detector.py:81-89` (dir_patterns)
- **Container Mapping**: `heuristic_detector.py:63-73` (CONTAINER_TYPE_MAPPING)
- **Normalized in**: `discovery.py:211` (_normalize_type_from_dirname)
- **Action**: Consolidate into single ArtifactRegistry

### Scoring System
- **Location**: `heuristic_detector.py:16-48`
- **Max Score**: 120 points (normalized to 0-100)
- **Signal Weights**:
  - Frontmatter type: 30 (25%)
  - Container hint: 25 (21%)
  - Manifest: 20 (17%)
  - Parent hint: 15 (13%)
  - Frontmatter: 15 (13%)
  - Dir name: 10 (8%)
  - Extensions: 5 (4%)

### Type Detection Methods
1. **discovery.py:449+** - Local detection (_detect_artifact_type)
2. **validator.py:241-279** - Structural detection (detect_artifact_type)
3. **heuristic_detector.py:400+** - Multi-signal scoring
4. **defaults.py:69-101** - Name-based inference
- **Action**: Create DetectorStrategy interface

### Validation
- **Skills**: `validator.py:23-74` (validate_skill)
- **Commands**: `validator.py:77-141` (validate_command)
- **Agents**: `validator.py:144-212` (validate_agent)
- **Auto-detect**: `validator.py:241-279` (detect_artifact_type)

### Metadata Extraction
- **Class**: `artifact.py:59-104` (ArtifactMetadata)
- **Extraction function**: `utils/metadata.py` (extract_artifact_metadata)
- **Frontmatter parsing**: `utils/metadata.py` (extract_yaml_frontmatter)

---

## Critical Duplication Points

### 1. Type Definition Duplication
```
artifact.py:33         class ArtifactType
heuristic_detector.py:51  class ArtifactType  ← DUPLICATE
```
**Fix**: Import from artifact.py in heuristic_detector.py

### 2. Manifest File Hardcoding
```
heuristic_detector.py:92  (config - source of truth)
discovery.py:449          (hardcoded check)
validator.py:50, 106, 173 (hardcoded check)
```
**Fix**: Create ArtifactRegistry, reference from all

### 3. Directory Pattern Duplication
```
heuristic_detector.py:81   (dir_patterns config)
heuristic_detector.py:63   (CONTAINER_TYPE_MAPPING)
discovery.py:211           (separate normalization logic)
```
**Fix**: Single unified config in registry

### 4. Type Detection Fragmentation
```
discovery.py:449       detect_artifact_type() ← Local
validator.py:241       detect_artifact_type() ← Structural
heuristic_detector.py  analyze_paths()        ← Marketplace
defaults.py:69         detect_artifact_type() ← Name-based
```
**Fix**: Abstract DetectorStrategy interface

---

## Detection Decision Flow

```
Input artifact/directory
    ├─ CLI with name only?
    │  └─ defaults.py:69 → Name pattern matching
    │
    ├─ Local file/directory?
    │  ├─ discovery.py:449 → Check manifest files
    │  └─ validator.py:241 → Structural detection
    │
    └─ GitHub repository?
       └─ heuristic_detector.py:400+ → Multi-signal scoring

Output: ArtifactType (artifact.py:33)
```

---

## Standardization Phases

### Phase 1: Create Central Registry
```
Create: skillmeat/core/artifact_registry.py
Contains:
  - ArtifactType (import from artifact.py)
  - ManifestRegistry (SKILL.md, COMMAND.md, etc.)
  - DirectoryPatterns (skills/, commands/, etc.)
  - ContainerMapping
```

### Phase 2: Abstract Detection Interface
```
Create: skillmeat/core/detection_strategy.py
Create: skillmeat/core/detection_interface.py
Abstract:
  - DetectorStrategy base class
  - MatchResult dataclass
  - confidence: int (0-100)
Implementations:
  - ManifestDetector (discovery.py logic)
  - StructuralDetector (validator.py logic)
  - HeuristicDetector (refactor current)
  - NameBasedDetector (defaults.py logic)
```

### Phase 3: Consolidate Validation
```
Modify: skillmeat/utils/validator.py
  - Use ArtifactRegistry for manifest files
  - Use DetectorStrategy interface
  - Keep ValidationResult for pass/fail
```

### Phase 4: Update All Consumers
```
Modify: discovery.py → use registry + strategies
Modify: heuristic_detector.py → extend DetectorStrategy
Modify: validator.py → use registry
Modify: defaults.py → use registry
```

---

## Files to Create/Modify

### New Files
- `skillmeat/core/artifact_registry.py` (central configuration)
- `skillmeat/core/detection_interface.py` (abstract base)
- `skillmeat/core/detection_strategies.py` (implementations)

### Modify Existing
- `skillmeat/core/artifact.py` (keep, import in registry)
- `skillmeat/core/discovery.py` (use registry + strategies)
- `skillmeat/core/marketplace/heuristic_detector.py` (extend base)
- `skillmeat/utils/validator.py` (use registry)
- `skillmeat/defaults.py` (use registry)
- `skillmeat/utils/metadata.py` (centralize extraction)

---

## Test Coverage Needs

### Unit Tests
- ArtifactRegistry configuration validation
- Each DetectorStrategy in isolation
- ManifestRegistry completeness
- DirectoryPattern matching

### Integration Tests
- CompositeDetector strategy selection
- Confidence score normalization
- Manual mapping inheritance
- Discovery with all filters

### Regression Tests
- Existing discovery results unchanged
- Existing validation results unchanged
- Existing marketplace results unchanged
- Existing defaults unchanged

---

## Documentation References

1. **artifact-detection-code-patterns.md** (14KB)
   - Comprehensive patterns analysis
   - Integration points
   - Current inconsistencies
   - Opportunities

2. **detection-patterns-summary-table.md** (10KB)
   - Side-by-side comparison
   - Manifest registry reference
   - Confidence scoring
   - Performance metrics

3. **detection-refactor-locations.md** (14KB)
   - Exact line numbers
   - Code blocks
   - Duplication points
   - Refactor targets

All in: `.claude/context/`

