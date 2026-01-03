---
title: "Bug Fix: Single-File Artifact Detection"
description: "Enable detection of single-file commands and agents inside container directories"
audience: [ai-agents, developers]
tags: [bugfix, marketplace, detection, heuristic]
created: 2026-01-01
updated: 2026-01-01
category: "bugs"
status: active
related:
  - /docs/project_plans/implementation_plans/bugs/marketplace-sources-non_skills-v1.md
---

# Bug Fix: Single-File Artifact Detection

**Plan ID**: `BUGFIX-2026-01-01-SINGLE-FILE-ARTIFACTS`
**Date**: 2026-01-01
**Author**: Opus (Orchestrator)
**Priority**: P0 (blocking marketplace import)

## Executive Summary

The heuristic detector only recognizes **directory-based artifacts** (directories containing manifest files like `COMMAND.md`). It fails to detect **single-file artifacts** - individual `.md` files directly inside container directories that ARE the artifacts themselves.

**Example repository**: `mrgoonie/claudekit-skills`
- **Expected**: 5 commands, 1 agent, many skills
- **Actual**: Only skills detected (and `commands/git` as 1 command instead of 3)

## Root Cause Analysis

### Current Behavior

The detector iterates through `dir_to_files` (directories only):
```python
for dir_path, files in dir_to_files.items():
    # Only directories are considered as potential artifacts
    # Individual files are never analyzed as artifacts
```

### Patterns NOT Supported (but common in wild)

| Pattern | Description | Status |
|---------|-------------|--------|
| `commands/use-mcp.md` | Single-file command directly in container | ❌ NOT detected |
| `commands/git/cm.md` | Single-file command in grouping subdir | ❌ NOT detected |
| `agents/mcp-manager.md` | Single-file agent directly in container | ❌ NOT detected |

### Patterns Supported

| Pattern | Description | Status |
|---------|-------------|--------|
| `skills/aesthetic/SKILL.md` | Directory with manifest | ✅ Works |
| `commands/deploy/COMMAND.md` | Directory with manifest | ✅ Would work |

### Claude Code Conventions

- **Skills**: Always directory-based (SKILL.md + supporting files)
- **Commands**: Often file-based (single `.md` file with prompt)
- **Agents**: Often file-based (single `.md` file with agent definition)

## Implementation Plan

### Task Breakdown

| Task ID | Task | Description | Subagent |
|---------|------|-------------|----------|
| SINGLE-001 | Detect single-file artifacts | Add logic to `analyze_paths()` to detect `.md` files directly in containers | python-backend-engineer |
| SINGLE-002 | Handle grouping directories | Detect `.md` files in subdirectories of containers (e.g., `commands/git/cm.md`) | python-backend-engineer |
| SINGLE-003 | Add test coverage | Test cases for single-file patterns | python-backend-engineer |
| SINGLE-004 | Regression test | Ensure existing detection still works | python-backend-engineer |

### Detailed Specifications

#### SINGLE-001: Detect Single-File Artifacts in Containers

**Location**: `heuristic_detector.py:analyze_paths()` (after line 350)

**Logic**:
```python
# After building container_types mapping (around line 338)
# Add new loop to detect single-file artifacts:

for container_path, container_type in container_types.items():
    container_files = dir_to_files.get(container_path, set())

    for filename in container_files:
        # Skip manifest files - they define directory-based artifacts
        if filename.upper() in {'SKILL.MD', 'COMMAND.MD', 'AGENT.MD', 'MCP.MD', 'HOOK.MD'}:
            continue

        # Only consider .md files as potential single-file artifacts
        if not filename.lower().endswith('.md'):
            continue

        # Skip README and other docs
        if filename.upper() in {'README.MD', 'CHANGELOG.MD', 'LICENSE.MD'}:
            continue

        # This is a single-file artifact!
        artifact_path = f"{container_path}/{filename}"
        artifact_name = filename[:-3]  # Remove .md extension

        # Create match with high confidence (container provides strong type signal)
        match = HeuristicMatch(
            path=artifact_path,
            artifact_type=container_type.value,
            confidence_score=80,  # High confidence from container type
            organization_path=None,  # Directly in container
            match_reasons=[
                f"Single-file {container_type.value} in {container_path}/ container",
                f"File: {filename}"
            ],
            # ... scoring breakdown
        )
        matches.append(match)
```

#### SINGLE-002: Handle Grouping Directories

**Scenario**: `commands/git/cm.md`, `commands/git/cp.md` - files in a subdirectory of container

**Logic** (add after SINGLE-001):
```python
# For subdirectories of containers, check if they contain artifact files
for dir_path, files in dir_to_files.items():
    # Skip if this IS a container
    if dir_path in container_types:
        continue

    # Find if we're inside a container
    container_hint = None
    container_dir = None
    for container_path, c_type in container_types.items():
        if dir_path.startswith(container_path + "/"):
            container_hint = c_type
            container_dir = container_path
            break

    if container_hint is None:
        continue  # Not inside a container

    # Check if this directory has NO manifest file
    has_manifest = any(
        f.upper() in {'SKILL.MD', 'COMMAND.MD', 'AGENT.MD', 'MCP.MD', 'HOOK.MD'}
        for f in files
    )

    if has_manifest:
        continue  # Has manifest, will be handled by normal directory detection

    # No manifest - treat each .md file as a single-file artifact
    for filename in files:
        if not filename.lower().endswith('.md'):
            continue
        if filename.upper() in {'README.MD', 'CHANGELOG.MD'}:
            continue

        artifact_path = f"{dir_path}/{filename}"
        organization_path = self._compute_organization_path(dir_path, container_dir)

        match = HeuristicMatch(
            path=artifact_path,
            artifact_type=container_hint.value,
            confidence_score=75,  # Slightly lower, nested
            organization_path=organization_path,
            match_reasons=[
                f"Single-file {container_hint.value} in nested directory",
                f"Container: {container_dir}",
                f"Organization: {organization_path or 'root'}"
            ],
        )
        matches.append(match)
```

#### SINGLE-003: Test Cases

```python
class TestSingleFileArtifacts:
    """Test detection of single-file artifacts in containers."""

    def test_single_file_command_in_container(self, detector):
        """commands/use-mcp.md → COMMAND"""
        paths = ["commands/use-mcp.md"]
        matches = detector.analyze_paths(paths)
        assert len(matches) == 1
        assert matches[0].artifact_type == "command"
        assert matches[0].path == "commands/use-mcp.md"

    def test_single_file_agent_in_container(self, detector):
        """agents/mcp-manager.md → AGENT"""
        paths = ["agents/mcp-manager.md"]
        matches = detector.analyze_paths(paths)
        assert len(matches) == 1
        assert matches[0].artifact_type == "agent"

    def test_multiple_files_in_grouping_dir(self, detector):
        """commands/git/cm.md, cp.md, pr.md → 3 COMMANDs"""
        paths = [
            "commands/git/cm.md",
            "commands/git/cp.md",
            "commands/git/pr.md",
        ]
        matches = detector.analyze_paths(paths)
        assert len(matches) == 3
        assert all(m.artifact_type == "command" for m in matches)
        assert {m.organization_path for m in matches} == {"git"}

    def test_mixed_single_and_directory_artifacts(self, detector):
        """Mix of single-file and directory-based artifacts"""
        paths = [
            "commands/use-mcp.md",           # Single-file
            "commands/deploy/COMMAND.md",    # Directory-based
            "skills/aesthetic/SKILL.md",     # Directory-based
            "agents/helper.md",              # Single-file
        ]
        matches = detector.analyze_paths(paths)
        assert len(matches) == 4
        # Verify types
        by_path = {m.path: m for m in matches}
        assert by_path["commands/use-mcp.md"].artifact_type == "command"
        assert by_path["commands/deploy"].artifact_type == "command"
        assert by_path["skills/aesthetic"].artifact_type == "skill"
        assert by_path["agents/helper.md"].artifact_type == "agent"
```

## Orchestration

**Single batch** (sequential due to dependencies):

```
SINGLE-001 → SINGLE-002 → SINGLE-003 → SINGLE-004
```

All tasks assigned to: `python-backend-engineer`

## Success Criteria

- [ ] `commands/use-mcp.md` detected as COMMAND
- [ ] `commands/git/cm.md`, `cp.md`, `pr.md` detected as 3 separate COMMANDs
- [ ] `agents/mcp-manager.md` detected as AGENT
- [ ] Existing skill detection unchanged (regression test)
- [ ] All tests pass
