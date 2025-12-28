---
type: progress
prd: "sourcing-algorithm-plugin-detection"
phase: 1
title: "Plugin Detection Implementation"
status: pending
progress: 0
total_tasks: 7
completed_tasks: 0

tasks:
  - id: "TASK-1.1"
    title: "Add _is_plugin_directory() method"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimate: "2h"
  - id: "TASK-1.2"
    title: "Add _is_container_directory() method"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.1"]
    estimate: "2h"
  - id: "TASK-1.3"
    title: "Modify analyze_paths() to skip containers"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.2"]
    estimate: "1h"
  - id: "TASK-1.4"
    title: "Add test cases for plugin detection"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.3"]
    estimate: "3h"
  - id: "TASK-1.5"
    title: "Add test cases for container skipping"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.3"]
    estimate: "3h"
  - id: "TASK-1.6"
    title: "Add test cases for backward compatibility"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.3"]
    estimate: "2h"
  - id: "TASK-1.7"
    title: "Update docstrings and comments"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.3"]
    estimate: "1h"

parallelization:
  batch_1: ["TASK-1.1"]
  batch_2: ["TASK-1.2"]
  batch_3: ["TASK-1.3"]
  batch_4: ["TASK-1.4", "TASK-1.5", "TASK-1.6", "TASK-1.7"]

blockers: []
---

# Phase 1: Plugin Detection Implementation

## Overview

This phase implements core plugin detection logic to enhance the heuristic detector's ability to identify plugin directory structures and correctly skip entity-type container directories (commands/, agents/, skills/, hooks/, rules/) from being detected as entities themselves.

The solution adds two new detection methods and modifies the analyze_paths() loop to skip containers before scoring, preventing false positives while maintaining backward compatibility with non-plugin repositories.

---

## Task Breakdown

| ID | Title | Status | Estimate | Dependencies |
|---|---|---|---|---|
| TASK-1.1 | Add `_is_plugin_directory()` method | pending | 2h | - |
| TASK-1.2 | Add `_is_container_directory()` method | pending | 2h | TASK-1.1 |
| TASK-1.3 | Modify `analyze_paths()` to skip containers | pending | 1h | TASK-1.2 |
| TASK-1.4 | Add test cases for plugin detection | pending | 3h | TASK-1.3 |
| TASK-1.5 | Add test cases for container skipping | pending | 3h | TASK-1.3 |
| TASK-1.6 | Add test cases for backward compatibility | pending | 2h | TASK-1.3 |
| TASK-1.7 | Update docstrings and comments | pending | 1h | TASK-1.3 |

**Total Estimated Effort:** 14 hours

---

## Orchestration Quick Reference

### Batch 1 (Sequential)
- TASK-1.1 → `python-backend-engineer` (2h)

**Implementation:**
```python
Task("python-backend-engineer", """
TASK-1.1: Add _is_plugin_directory() method

File: skillmeat/core/marketplace/heuristic_detector.py

Add new method to detect plugin structures:

def _is_plugin_directory(self, dir_path: str, dir_to_files: Dict[str, Set[str]]) -> bool:
    \"\"\"Detect if a directory is a plugin (contains multiple entity-type subdirectories).

    Args:
        dir_path: Path to check
        dir_to_files: Map of all directories to their files

    Returns:
        True if directory contains 2+ entity-type subdirectories
    \"\"\"
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

Placement: Add after existing utility methods, before _score_directory()
""")
```

### Batch 2 (Sequential)
- TASK-1.2 → `python-backend-engineer` (2h)

**Implementation:**
```python
Task("python-backend-engineer", """
TASK-1.2: Add _is_container_directory() method

File: skillmeat/core/marketplace/heuristic_detector.py

Add new method to identify entity-type containers:

def _is_container_directory(self, dir_path: str, dir_to_files: Dict[str, Set[str]]) -> bool:
    \"\"\"Detect if a directory is an entity-type container (not an entity itself).

    Args:
        dir_path: Path to check
        dir_to_files: Map of all directories to their files

    Returns:
        True if directory is a container (e.g., "commands/", "skills/")
    \"\"\"
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

Placement: Add immediately after _is_plugin_directory()
Dependencies: Requires TASK-1.1 to be completed
""")
```

### Batch 3 (Sequential)
- TASK-1.3 → `python-backend-engineer` (1h)

**Implementation:**
```python
Task("python-backend-engineer", """
TASK-1.3: Modify analyze_paths() to skip containers

File: skillmeat/core/marketplace/heuristic_detector.py

Update the main analysis loop in analyze_paths():

In the main loop over dir_to_files, add container skip check:

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

Key points:
- Skip container check happens BEFORE depth check and scoring
- Use existing dir_to_files variable already available
- No changes to existing scoring logic or thresholds
- Maintains all existing functionality

Dependencies: Requires TASK-1.2 to be completed
""")
```

### Batch 4 (Parallel)
- TASK-1.4, TASK-1.5, TASK-1.6, TASK-1.7 → `python-backend-engineer` (9h total)

**Implementation:**
```python
Task("python-backend-engineer", """
TASK-1.4: Add test cases for plugin detection

File: tests/core/marketplace/test_heuristic_detector.py

Add new test class TestPluginDetection with tests:

1. test_detect_plugin_with_multiple_entity_types()
   - Files: "my-plugin/commands/deploy/COMMAND.md", "my-plugin/agents/helper/AGENT.md"
   - Expected: 2 entities detected, "commands" and "agents" NOT detected

2. test_detect_plugin_with_three_entity_types()
   - Files: "plugin/commands/cmd1/COMMAND.md", "plugin/agents/agent1/AGENT.md", "plugin/skills/skill1/SKILL.md"
   - Expected: 3 entities detected with types {"command", "agent", "skill"}

See implementation plan for complete test specifications.

Dependencies: Requires TASK-1.3 to be completed
""")

Task("python-backend-engineer", """
TASK-1.5: Add test cases for container skipping

File: tests/core/marketplace/test_heuristic_detector.py

Add new test class TestContainerSkipping with tests:

1. test_skip_commands_container_in_plugin()
   - Files: "plugin/commands/deploy/COMMAND.md", "plugin/commands/analyze/COMMAND.md"
   - Expected: deploy and analyze detected, NOT "commands"

2. test_skip_all_container_types()
   - Files: Multiple entity types in containers
   - Expected: Only entity names detected, no container names

See implementation plan for complete test specifications.

Dependencies: Requires TASK-1.3 to be completed
""")

Task("python-backend-engineer", """
TASK-1.6: Add test cases for backward compatibility

File: tests/core/marketplace/test_heuristic_detector.py

Add new test class TestBackwardCompatibility with tests:

1. test_non_plugin_repo_still_works()
   - Files: Root-level skills/ and commands/
   - Expected: Both entities detected

2. test_nested_skills_in_non_plugin()
   - Files: Multiple skills without plugin structure
   - Expected: All skills detected

3. test_single_entity_type_not_plugin()
   - Files: Multiple commands without other entity types
   - Expected: All commands detected, "commands" NOT detected

See implementation plan for complete test specifications.

Dependencies: Requires TASK-1.3 to be completed
""")

Task("python-backend-engineer", """
TASK-1.7: Update docstrings and comments

File: skillmeat/core/marketplace/heuristic_detector.py

Updates:

1. Add comprehensive docstrings for:
   - _is_plugin_directory() - explain plugin detection threshold
   - _is_container_directory() - explain entity-type recognition

2. Add inline comments in analyze_paths():
   - Explain container skipping logic
   - Reference the methods used

3. Update class docstring if needed to mention plugin structure support

Ensure all docstrings include:
- Purpose of method
- Args and return types with descriptions
- Example directory structures where applicable

Dependencies: Requires TASK-1.3 to be completed
""")
```

---

## Success Criteria

- [ ] **Plugin Detection Works**
  - Directories with 2+ entity-type subdirectories recognized as plugins
  - Container directories (commands/, agents/, etc.) skipped from entity detection

- [ ] **Entity Detection Accurate**
  - Entities within containers correctly detected
  - Confidence scores for real entities unchanged

- [ ] **Backward Compatibility Maintained**
  - Non-plugin repositories work as before
  - Single entity-type directories at root level still work

- [ ] **Test Coverage Complete**
  - All plugin detection logic covered by tests
  - Container skipping verified
  - Backward compatibility tested
  - Edge cases handled (nested plugins, mixed structures)

- [ ] **Code Quality**
  - All tests passing (`pytest tests/core/marketplace/test_heuristic_detector.py -v`)
  - Docstrings updated for new methods
  - No new linting errors
  - Code formatted with black

---

## Files

### Implementation Files
- `skillmeat/core/marketplace/heuristic_detector.py`

### Test Files
- `tests/core/marketplace/test_heuristic_detector.py`

### Reference
- `docs/project_plans/implementation_plans/enhancements/sourcing-algorithm-plugin-detection-v1.md` - Complete implementation plan
- `docs/project_plans/ideas/sourcing-algorithm-v2.md` - Original requirements
