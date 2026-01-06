---
title: Artifact Detection Patterns - Quick Reference Table
description: Side-by-side comparison of detection mechanisms
references:
  - .claude/context/artifact-detection-code-patterns.md
last_verified: 2026-01-06
---

# Artifact Detection Patterns - Quick Reference

## Module Comparison Matrix

| Aspect | artifact.py | discovery.py | heuristic_detector.py | validator.py | defaults.py |
|--------|-------------|--------------|----------------------|--------------|-------------|
| **File Size** | 1,903 lines | 786 lines | 1,675 lines | 279 lines | 194 lines |
| **Purpose** | Core types & models | Local scanning | GitHub marketplace | Structure validation | CLI inference |
| **Confidence** | N/A | High (100%) | Variable (30-95%) | Pass/Fail | Medium (name-based) |
| **Input** | Manifest TOML | Filesystem | File paths, GitHub API | Path reference | Artifact name |
| **Output** | Artifact class | DiscoveredArtifact list | HeuristicMatch list | ValidationResult | str (type) |

---

## Artifact Types Supported

### Core Types (All Modules)
| Type | artifact.py | discovery.py | heuristic_detector.py | validator.py | defaults.py |
|------|:-----------:|:------------:|:--------------------:|:------------:|:-----------:|
| skill | ✓ | ✓ | ✓ | ✓ | ✓ |
| command | ✓ | ✓ | ✓ | ✓ | ✓ |
| agent | ✓ | ✓ | ✓ | ✓ | ✓ |

### Extended Types
| Type | artifact.py | discovery.py | heuristic_detector.py | validator.py | defaults.py |
|------|:-----------:|:------------:|:--------------------:|:------------:|:-----------:|
| hook | ✓ | ✓ | ✓ | - | - |
| mcp | ✓ | ✓ | ✓ (mcp_server) | - | - |
| project_config | ✓ | - | - | - | - |
| spec_file | ✓ | - | - | - | - |
| rule_file | ✓ | - | - | - | - |
| context_file | ✓ | - | - | - | - |
| progress_template | ✓ | - | - | - | - |

---

## Detection Signals

### artifact.py (Type Definition)
- **Input**: TOML manifest data
- **Signals**: None (pure data model)
- **Output**: ArtifactType enum
- **Confidence**: N/A

### discovery.py (Local Discovery)

| Signal | Weight | Priority | Confidence |
|--------|--------|----------|------------|
| Manifest file | Primary | 1st | 100% |
| Directory type | High | 2nd | 90% |
| Parent hint | Medium | 3rd | 80% |
| Skip preferences | - | Filter | - |

**Detection Logic**:
```
Type directory (skills/) → Artifact type
    ↓
Check manifest files (SKILL.md, COMMAND.md, etc.)
    ↓
Validate structure
    ↓
Extract metadata
    ↓
Return DiscoveredArtifact
```

### heuristic_detector.py (Marketplace)

| Signal | Points | % of Total | Confidence |
|--------|--------|-----------|------------|
| Frontmatter type | 30 | 25% | Very High |
| Container hint | 25 | 21% | High |
| Manifest | 20 | 17% | High |
| Parent hint | 15 | 13% | Medium |
| Frontmatter | 15 | 13% | Medium |
| Dir name | 10 | 8% | Low-Medium |
| Extensions | 5 | 4% | Low |
| **Total** | **120** | **100%** | 0-100% |

**Normalization**: `(raw_score / 120) * 100`

**Minimum Threshold**: 30 points (25%)

**Manual Mappings**:
- Exact match: 95%
- Parent (depth 1): 92%
- Grandparent (depth 2): 89%
- Ancestor (depth 3+): 86%

### validator.py (Structural)

| Type | Structure | Manifest | Content | Result |
|------|-----------|----------|---------|--------|
| Skill | Directory | SKILL.md | Non-empty | Pass/Fail |
| Command | File or Dir | .md file | Non-empty | Pass/Fail |
| Agent | File or Dir | AGENT.md or agent.md | Non-empty | Pass/Fail |

**Detection Fallback**:
1. Check for SKILL.md → SKILL
2. Check for AGENT.md/agent.md → AGENT
3. Check for .md files → COMMAND (fallback)

### defaults.py (Name-Based)

| Pattern | Type |
|---------|------|
| `*-cli` | command |
| `*-cmd` | command |
| `*-command` | command |
| `*-agent` | agent |
| `*-bot` | agent |
| *(default)* | skill |

**Case**: Insensitive
**Order**: First match wins

---

## Manifest Files Registry

### Canonical Names

| Type | Primary | Alternate | Config Source |
|------|---------|-----------|---|
| Skill | SKILL.md | skill.md | heuristic_detector.py:94 |
| Command | COMMAND.md | command.md | heuristic_detector.py:95 |
| Agent | AGENT.md | agent.md | heuristic_detector.py:96 |
| Hook | HOOK.md | hook.md, hooks.json | heuristic_detector.py:98 |
| MCP | MCP.md | mcp.md, server.json | heuristic_detector.py:97 |

**Current Issue**: Manifest definitions hardcoded in multiple files
- `DetectionConfig` in heuristic_detector.py (source of truth)
- Checked individually in discovery.py and validator.py
- No single registry

---

## Directory Container Mapping

| Directory | Implied Type | Scope | Source |
|-----------|--------------|-------|--------|
| skills/ | skill | High | heuristic_detector.py:67 |
| skill/ | skill | High | heuristic_detector.py:67 |
| claude-skills/ | skill | High | heuristic_detector.py:67 |
| commands/ | command | High | heuristic_detector.py:65 |
| command/ | command | High | heuristic_detector.py:65 |
| claude-commands/ | command | High | heuristic_detector.py:65 |
| agents/ | agent | High | heuristic_detector.py:66 |
| agent/ | agent | High | heuristic_detector.py:66 |
| claude-agents/ | agent | High | heuristic_detector.py:66 |
| hooks/ | hook | High | heuristic_detector.py:68 |
| hook/ | hook | High | heuristic_detector.py:68 |
| claude-hooks/ | hook | High | heuristic_detector.py:68 |
| mcp/ | mcp_server | High | heuristic_detector.py:69 |
| mcp-servers/ | mcp_server | High | heuristic_detector.py:70 |
| servers/ | mcp_server | Low | heuristic_detector.py:71 |

**Current Issue**:
- Defined in `CONTAINER_TYPE_MAPPING` (heuristic_detector.py:63-73)
- Separate logic in discovery.py for type normalization
- Inconsistent alias coverage

---

## Data Flow by Use Case

### Use Case 1: User Uploads Artifact

```
File/directory
    ↓
validator.py::detect_artifact_type()
    • Checks manifest files
    • Returns ArtifactType
    ↓
validator.py::validate()
    • Structural validation
    • Returns ValidationResult
    ↓
artifact.py::Artifact()
    • Creates instance
    • Validates name/origin
```

### Use Case 2: Scan .claude/ Directory

```
.claude/skills/, .claude/commands/, etc.
    ↓
discovery.py::discover_artifacts()
    • Scans type directories
    • Detects each artifact
    • Extracts metadata
    ↓
discovery.py::_detect_artifact_type()
    • Checks manifest files
    • Validates structure
    ↓
DiscoveredArtifact list
    ↓
Filter (manifest + skip preferences)
```

### Use Case 3: Scan GitHub Repository

```
GitHub repository file tree
    ↓
heuristic_detector.py::analyze_paths()
    • Multi-signal scoring
    • Confidence calculation
    • Manual mapping checks
    ↓
HeuristicMatch list (30+ confidence)
    ↓
User review (confidence 30-100)
```

### Use Case 4: CLI with Name Only

```
$ skillmeat add my-cli
    ↓
defaults.py::detect_artifact_type("my-cli")
    • Suffix pattern matching
    • Returns "command"
    ↓
artifact_type = ArtifactType.COMMAND
```

---

## Metadata Extraction

### Current Approach

| Field | Source | Method |
|-------|--------|--------|
| title | Frontmatter/Config | YAML parse |
| description | Frontmatter | YAML parse |
| author | Frontmatter | YAML parse |
| version | Frontmatter | YAML parse |
| tags | Frontmatter | YAML parse |
| dependencies | Frontmatter | YAML parse |
| license | Frontmatter | YAML parse |

**Extraction Function**: `extract_artifact_metadata()` (utils/metadata.py)

**Frontmatter Format**:
```yaml
---
title: My Skill
description: Does something cool
author: User
version: 1.0.0
tags: [productivity, automation]
---
```

---

## Confidence Score Reference

### By Detection Method

| Method | Confidence | Use Case |
|--------|------------|----------|
| Manifest file found | 100% | Local discovery, validation pass |
| Manual mapping (exact) | 95% | GitHub marketplace with override |
| Manual mapping (parent) | 92% | GitHub marketplace with override |
| Heuristic score 80+ | 80%+ | GitHub marketplace auto-detect |
| Heuristic score 50-80 | 50-80% | GitHub marketplace, needs review |
| Heuristic score 30-50 | 30-50% | GitHub marketplace, low confidence |
| Name-based inference | ~70% | CLI smart defaults |
| Structural detection | Pass/Fail | Validator (no score) |

---

## Error Handling & Fallbacks

### discovery.py

| Error | Fallback | Behavior |
|-------|----------|----------|
| Artifacts dir missing | Return empty result | Log warning |
| Permission denied | Skip directory | Log warning, continue |
| Invalid artifact | Skip artifact | Log warning, continue |
| Manifest parse error | Skip artifact | Log error, continue |

**Philosophy**: Collect errors but continue scan

### heuristic_detector.py

| Error | Fallback | Behavior |
|-------|----------|----------|
| Invalid artifact type string | Log warning | Skip mapping |
| Frontmatter parse error | Skip signal | Use other signals |
| Manual mapping invalid | Log warning | Ignore mapping |

**Philosophy**: Graceful degradation, use available signals

### validator.py

| Error | Result |
|-------|--------|
| Path not found | ValidationResult(is_valid=False) |
| Not directory (Skill) | ValidationResult(is_valid=False) |
| No manifest file | ValidationResult(is_valid=False) |
| Empty manifest file | ValidationResult(is_valid=False) |
| Read permission error | ValidationResult(is_valid=False) |

**Philosophy**: Binary pass/fail, no partial validation

---

## Key Metrics

### Performance Targets

- **discovery.py**: <2 seconds for 50+ artifacts
- **heuristic_detector.py**: Real-time (GitHub file tree scan)
- **validator.py**: <100ms per artifact
- **defaults.py**: <1ms (regex match only)

### Code Statistics

| Module | Lines | Functions | Classes | Dataclasses |
|--------|-------|-----------|---------|-------------|
| artifact.py | 1,903 | ~15 | 1 | 4 |
| discovery.py | 786 | ~8 | 2 | 3 |
| heuristic_detector.py | 1,675 | ~20 | 2 | 1 |
| validator.py | 279 | ~6 | 1 | 1 |
| defaults.py | 194 | ~5 | 1 | - |

