---
status: inferred_complete
---
# Implementation Plan: Sourcing Algorithm Plugin Detection Enhancement v1

**Date:** 2025-12-28
**Status:** Ready for Implementation
**Complexity:** Small (S)
**Estimated Effort:** 8 story points (~1 week)

---

## Executive Summary

Enhance the heuristic detector to correctly identify plugin directory structures and skip entity-type container directories (commands/, agents/, skills/, hooks/, rules/) from being detected as entities themselves. This is a minimal algorithm logic enhancement - NOT full plugin support as first-class artifacts.

### Current Behavior (Wrong)

```
plugin/
├── commands/           ← Detected as entity named "commands" (WRONG)
│   ├── deploy/        ← Detected as entity named "deploy"
│   └── analyze/       ← Detected as entity named "analyze"
```

### Expected Behavior (Correct)

```
plugin/
├── commands/          ← Recognized as CONTAINER, skipped
│   ├── deploy/        ← Detected as command entity named "deploy"
│   └── analyze/       ← Detected as command entity named "analyze"
```

---

## Problem Statement

The sourcing algorithm in `heuristic_detector.py` incorrectly treats entity-type container directories (commands/, agents/, skills/, hooks/, rules/) as potential entity names when they appear inside plugin directories. This creates false positives where directory names like "commands" are detected as command entities, when they should be recognized as organizational containers.

### Root Cause

The `_score_directory()` method scores directories based on name matching patterns without considering whether the directory is a container for multiple entities (indicating a plugin structure) versus an actual entity directory.

### Impact

- False positive detections of container directories as entities
- Cluttered artifact listings with non-entities
- Confusion between actual entities and organizational folders

---

## Solution Design

### 1. Plugin Detection Logic

Add a new method `_is_plugin_directory()` that identifies plugin structures:

```python
def _is_plugin_directory(self, dir_path: str, dir_to_files: Dict[str, Set[str]]) -> bool:
    """Detect if a directory is a plugin (contains multiple entity-type subdirectories).

    Args:
        dir_path: Path to check
        dir_to_files: Map of all directories to their files

    Returns:
        True if directory contains 2+ entity-type subdirectories
    """
    # Check immediate children for entity-type directories
    entity_type_names = {"commands", "agents", "skills", "hooks", "rules", "mcp"}

    child_dirs = set()
    for path in dir_to_files.keys():
        if path.startswith(dir_path + "/"):
            # Get immediate child directory name
            relative = path[len(dir_path) + 1:]
            first_part = relative.split("/")[0].lower()
            if first_part in entity_type_names:
                child_dirs.add(first_part)

    # Plugin detected if 2+ entity-type subdirectories
    return len(child_dirs) >= 2
```

### 2. Container Directory Detection

Add a new method `_is_container_directory()` that identifies entity-type containers:

```python
def _is_container_directory(self, dir_path: str, dir_to_files: Dict[str, Set[str]]) -> bool:
    """Detect if a directory is an entity-type container (not an entity itself).

    Args:
        dir_path: Path to check
        dir_to_files: Map of all directories to their files

    Returns:
        True if directory is a container (e.g., "commands/", "skills/")
    """
    posix_path = PurePosixPath(dir_path)
    dir_name = posix_path.name.lower()

    # Check if this is an entity-type directory name
    entity_type_names = {"commands", "agents", "skills", "hooks", "rules", "mcp"}
    if dir_name not in entity_type_names:
        return False

    # Check if parent is a plugin
    parent_path = str(posix_path.parent)
    if parent_path == ".":
        # Top-level entity-type directory - could be container
        return True

    return self._is_plugin_directory(parent_path, dir_to_files)
```

### 3. Modify `analyze_paths()` to Skip Containers

Update the main analysis loop in `analyze_paths()`:

```python
# Analyze each directory
for dir_path, files in dir_to_files.items():
    # Skip root directory
    if dir_path == ".":
        continue

    # Skip if container directory (NEW)
    if self._is_container_directory(dir_path, dir_to_files):
        continue

    # Skip if too deep
    depth = len(PurePosixPath(dir_path).parts)
    if depth > self.config.max_depth:
        continue

    # ... rest of existing logic
```

### 4. Maintain Backward Compatibility

- Non-plugin repositories (single commands/, skills/ at root) continue to work
- Entity directories within containers are still detected correctly
- No changes to scoring algorithm weights or thresholds

---

## Implementation Tasks

| Task ID | Description | Assignee | Estimate | Dependencies |
|---------|-------------|----------|----------|--------------|
| TASK-1.1 | Add `_is_plugin_directory()` method | python-backend-engineer | 2h | - |
| TASK-1.2 | Add `_is_container_directory()` method | python-backend-engineer | 2h | TASK-1.1 |
| TASK-1.3 | Modify `analyze_paths()` to skip containers | python-backend-engineer | 1h | TASK-1.2 |
| TASK-1.4 | Add test cases for plugin detection | python-backend-engineer | 3h | TASK-1.3 |
| TASK-1.5 | Add test cases for container skipping | python-backend-engineer | 3h | TASK-1.3 |
| TASK-1.6 | Add test cases for backward compatibility | python-backend-engineer | 2h | TASK-1.3 |
| TASK-1.7 | Update docstrings and comments | python-backend-engineer | 1h | TASK-1.3 |

**Total Estimated Effort:** 14 hours (~8 story points)

---

## Test Requirements

### Test Suite Additions

All tests should be added to `tests/core/marketplace/test_heuristic_detector.py`:

#### 1. Plugin Detection Tests (`TestPluginDetection`)

```python
def test_detect_plugin_with_multiple_entity_types():
    """Test that plugin with commands/ and agents/ is recognized."""
    files = [
        "my-plugin/commands/deploy/COMMAND.md",
        "my-plugin/agents/helper/AGENT.md",
    ]
    artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

    # Should detect 2 entities (deploy command, helper agent)
    assert len(artifacts) == 2
    # Should NOT detect "commands" or "agents" as entities
    names = {a.name for a in artifacts}
    assert "commands" not in names
    assert "agents" not in names

def test_detect_plugin_with_three_entity_types():
    """Test plugin with commands/, agents/, skills/."""
    files = [
        "plugin/commands/cmd1/COMMAND.md",
        "plugin/agents/agent1/AGENT.md",
        "plugin/skills/skill1/SKILL.md",
    ]
    artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

    assert len(artifacts) == 3
    types = {a.artifact_type for a in artifacts}
    assert types == {"command", "agent", "skill"}
```

#### 2. Container Skipping Tests (`TestContainerSkipping`)

```python
def test_skip_commands_container_in_plugin():
    """Test that commands/ directory is skipped in plugin."""
    files = [
        "plugin/commands/deploy/COMMAND.md",
        "plugin/commands/analyze/COMMAND.md",
    ]
    artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

    # Should detect deploy and analyze, NOT commands
    assert len(artifacts) == 2
    names = {a.name for a in artifacts}
    assert names == {"deploy", "analyze"}

def test_skip_all_container_types():
    """Test skipping of all entity-type containers."""
    files = [
        "plugin/commands/cmd/COMMAND.md",
        "plugin/agents/agent/AGENT.md",
        "plugin/skills/skill/SKILL.md",
        "plugin/hooks/hook/HOOK.md",
        "plugin/rules/rule/rule.md",
    ]
    artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

    # Should detect entities, not containers
    names = {a.name for a in artifacts}
    assert "commands" not in names
    assert "agents" not in names
    assert "skills" not in names
    assert "hooks" not in names
    assert "rules" not in names
```

#### 3. Backward Compatibility Tests (`TestBackwardCompatibility`)

```python
def test_non_plugin_repo_still_works():
    """Test that non-plugin repos continue to work correctly."""
    files = [
        "skills/skill1/SKILL.md",
        "commands/cmd1/COMMAND.md",
    ]
    artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

    # Should still detect both entities
    assert len(artifacts) == 2

def test_nested_skills_in_non_plugin():
    """Test nested skills without plugin structure."""
    files = [
        "skills/skill1/SKILL.md",
        "skills/skill2/SKILL.md",
    ]
    artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

    # Should detect both skills
    assert len(artifacts) == 2
    names = {a.name for a in artifacts}
    assert names == {"skill1", "skill2"}

def test_single_entity_type_not_plugin():
    """Test that single entity-type directory is not a plugin."""
    files = [
        "commands/cmd1/COMMAND.md",
        "commands/cmd2/COMMAND.md",
        "commands/cmd3/COMMAND.md",
    ]
    artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

    # Should detect all 3 commands
    assert len(artifacts) == 3
    # "commands" should not be detected as entity
    names = {a.name for a in artifacts}
    assert "commands" not in names
```

#### 4. Edge Case Tests (`TestPluginEdgeCases`)

```python
def test_plugin_with_minimal_threshold():
    """Test plugin detection with exactly 2 entity types."""
    files = [
        "plugin/commands/cmd/COMMAND.md",
        "plugin/agents/agent/AGENT.md",
    ]
    # Should detect as plugin (threshold = 2)
    artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")
    assert len(artifacts) == 2

def test_nested_plugins():
    """Test plugin within plugin structure."""
    files = [
        "outer-plugin/commands/cmd/COMMAND.md",
        "outer-plugin/agents/inner-plugin/commands/cmd2/COMMAND.md",
        "outer-plugin/agents/inner-plugin/skills/skill/SKILL.md",
    ]
    artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

    # Should handle nested structure correctly
    names = {a.name for a in artifacts}
    assert "commands" not in names
    assert "agents" not in names

def test_mixed_container_and_direct_entities():
    """Test plugin with both container and direct entities."""
    files = [
        "plugin/commands/cmd1/COMMAND.md",
        "plugin/agents/agent1/AGENT.md",
        "plugin/standalone-skill/SKILL.md",  # Direct entity
    ]
    artifacts = detect_artifacts_in_tree(files, "https://github.com/test/repo")

    # Should detect all entities
    assert len(artifacts) == 3
    names = {a.name for a in artifacts}
    assert names == {"cmd1", "agent1", "standalone-skill"}
```

### Test Execution

Run tests with:
```bash
pytest tests/core/marketplace/test_heuristic_detector.py::TestPluginDetection -v
pytest tests/core/marketplace/test_heuristic_detector.py::TestContainerSkipping -v
pytest tests/core/marketplace/test_heuristic_detector.py::TestBackwardCompatibility -v
pytest tests/core/marketplace/test_heuristic_detector.py::TestPluginEdgeCases -v
```

---

## Success Criteria

1. **Plugin Detection Works**
   - Directories with 2+ entity-type subdirectories are recognized as plugins
   - Container directories (commands/, agents/, etc.) are skipped from entity detection

2. **Entity Detection Remains Accurate**
   - Entities within containers are still correctly detected
   - Confidence scores for real entities remain unchanged

3. **Backward Compatibility Maintained**
   - Non-plugin repositories continue to work as before
   - Single entity-type directories at root level still work

4. **Test Coverage Complete**
   - All new logic paths covered by tests
   - Edge cases validated (nested plugins, mixed structures)
   - Backward compatibility verified

---

## Out of Scope

This is a **minimal enhancement**. The following are explicitly excluded:

- ❌ Full plugin support as first-class artifact type
- ❌ Plugin metadata extraction or storage
- ❌ Plugin-specific API endpoints
- ❌ UI changes for plugin display
- ❌ New artifact types (hooks, rules, context entities)
- ❌ Plugin bundling or deployment features

---

## Orchestration Quick Reference

**Implementation Phase** (Sequential):

```python
# TASK-1.1 to TASK-1.3: Core implementation
Task("python-backend-engineer", """
TASK-1.1 to TASK-1.3: Implement plugin detection logic

Files to modify:
- skillmeat/core/marketplace/heuristic_detector.py

Changes:
1. Add _is_plugin_directory() method (detects 2+ entity-type subdirs)
2. Add _is_container_directory() method (identifies entity-type containers)
3. Update analyze_paths() to skip containers before scoring

Implementation notes:
- Entity type names: {"commands", "agents", "skills", "hooks", "rules", "mcp"}
- Plugin threshold: 2+ entity-type subdirectories
- Skip containers BEFORE scoring to avoid false positives
- Maintain all existing scoring logic unchanged

Reference: See solution design section for method signatures
""")

# TASK-1.4 to TASK-1.6: Test suite
Task("python-backend-engineer", """
TASK-1.4 to TASK-1.6: Add comprehensive test coverage

File: tests/core/marketplace/test_heuristic_detector.py

Add test classes:
1. TestPluginDetection - verify plugin structure recognition
2. TestContainerSkipping - verify containers are skipped
3. TestBackwardCompatibility - verify non-plugin repos still work
4. TestPluginEdgeCases - verify edge cases (nested, mixed)

Reference: See Test Requirements section for specific test cases
Expected: ~15 new test methods, all passing
""")

# TASK-1.7: Documentation
Task("python-backend-engineer", """
TASK-1.7: Update documentation and docstrings

Files to update:
- skillmeat/core/marketplace/heuristic_detector.py (method docstrings)
- Add inline comments explaining plugin detection logic

Ensure docstrings include:
- Purpose of each new method
- Args and return types
- Example directory structures
""")
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Breaking backward compatibility | Low | High | Comprehensive backward compatibility tests |
| False negatives (missing entities) | Low | Medium | Test with diverse repository structures |
| Performance regression | Low | Low | Plugin detection is O(n) over existing dir map |
| Edge case handling | Medium | Medium | Extensive edge case test coverage |

---

## Validation Checklist

Before marking complete:

- [ ] All test suites pass (`pytest tests/core/marketplace/test_heuristic_detector.py -v`)
- [ ] Backward compatibility verified (existing tests still pass)
- [ ] Plugin detection correctly identifies container directories
- [ ] Entities within containers are still detected
- [ ] No performance regression (benchmark against large repos)
- [ ] Code formatted (`black skillmeat/`)
- [ ] Docstrings updated for new methods
- [ ] No new linting errors (`flake8 skillmeat/core/marketplace/`)

---

## References

**Source Files:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/heuristic_detector.py`
- `/Users/miethe/dev/homelab/development/skillmeat/tests/core/marketplace/test_heuristic_detector.py`

**Related Documents:**
- `docs/project_plans/ideas/sourcing-algorithm-v2.md` - Original requirements
- Future: Full plugin support as first-class artifacts (Phase 2)

**Assignee:**
- All tasks: `python-backend-engineer` (Sonnet-powered)

---

**Plan Created:** 2025-12-28
**Plan Version:** v1.0
**Track:** Fast (Small complexity, single-phase)
