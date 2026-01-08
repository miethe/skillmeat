---
title: Artifact Detection Standards
references:
  - skillmeat/core/artifact_detection.py
last_verified: 2026-01-07
---

# Artifact Detection Standards

This document defines the standards and implementation patterns for detecting and identifying Claude Code artifacts within the SkillMeat ecosystem. All modules (CLI discovery, marketplace heuristics, validators) must use the shared logic in `skillmeat/core/artifact_detection.py`.

## Architecture Overview

SkillMeat uses a tiered detection architecture to ensure consistency while allowing for flexibility in different contexts:

1.  **Shared Core (`skillmeat.core.artifact_detection`)**: Canonical source of truth for enums, structural rules (signatures), and detection logic.
2.  **Local Discovery**: Uses the core in `strict` mode to scan local directories and projects.
3.  **Marketplace Heuristics**: Uses the core in `heuristic` mode to identify artifacts in external repositories with varying structures.
4.  **Validators**: Use core signatures to verify that artifacts meet structural requirements before deployment or syncing.

## Artifact Types

The `ArtifactType` enum defines all entities recognized by SkillMeat.

### Primary Artifacts (Deployable)
These are artifacts that can be deployed to Claude Code projects:
- `SKILL`: Multi-file extensions (directories with `SKILL.md`).
- `COMMAND`: Slash commands (single `.md` files).
- `AGENT`: Agent prompts (single `.md` files).
- `HOOK`: Lifecycle hook configurations.
- `MCP`: Model Context Protocol server configurations.

### Context Entities (Non-Deployable)
Internal entities used for project management:
- `PROJECT_CONFIG`: `CLAUDE.md` files.
- `SPEC_FILE`: Specifications in `.claude/specs/`.
- `RULE_FILE`: Rule files in `.claude/rules/`.
- `CONTEXT_FILE`: Context documents in `.claude/context/`.
- `PROGRESS_TEMPLATE`: Progress tracking in `.claude/progress/`.

## Container Aliases

To support various repository structures, SkillMeat recognizes multiple directory names for each artifact type and normalizes them to a canonical form.

| Artifact Type | Canonical Name | Recognized Aliases |
| :--- | :--- | :--- |
| **SKILL** | `skills` | `skills`, `skill`, `claude-skills` |
| **COMMAND** | `commands` | `commands`, `command`, `claude-commands` |
| **AGENT** | `agents` | `agents`, `agent`, `subagents`, `claude-agents` |
| **HOOK** | `hooks` | `hooks`, `hook`, `claude-hooks` |
| **MCP** | `mcp` | `mcp`, `mcp-servers`, `servers`, `mcp_servers`, `claude-mcp` |

## Detection Functions

### `detect_artifact(path, container_type=None, mode="strict")`
The primary API for artifact identification. Analyzes a path and returns a `DetectionResult`.
- **Strict Mode**: Requires high confidence (matches signatures exactly). Returns 100% confidence or raises `DetectionError`.
- **Heuristic Mode**: Performs fuzzy matching and returns a confidence score (0-100).

### `infer_artifact_type(path)`
Identifies the type based on:
1.  Presence of specific manifest files (e.g., `SKILL.md`).
2.  Parent directory names matching container aliases.
3.  File extension patterns (for commands/agents).

### `normalize_container_name(name, artifact_type=None)`
Converts any alias (e.g., "subagents") to its canonical form (e.g., "agents").

### `extract_manifest_file(path, artifact_type)`
Finds the manifest file (e.g., `SKILL.md`, `settings.json`) within an artifact's path.

## Detection Modes

### Strict Mode (100% Confidence)
Used for local operations where structural integrity is required.
- Matches `ArtifactSignature` rules (is_directory, manifest presence).
- Validates against known container aliases.
- Fails fast if rules are not met.

### Heuristic Mode (Variable Confidence)
Used for external sources where structure may vary.
- Scores detections based on directory naming, file naming, and content clues.
- Returns a `confidence` level (80+ is considered "confident").
- Fallbacks to defaults when clues are ambiguous.

## Structural Signatures

Each primary type follows a structural signature:

| Type | Structure | Manifest Requirement | Manifest Names |
| :--- | :--- | :--- | :--- |
| **SKILL** | Directory | **Required** | `SKILL.md`, `skill.md` |
| **COMMAND** | File | Optional | `COMMAND.md`, `command.md` |
| **AGENT** | File | Optional | `AGENT.md`, `agent.md` |
| **HOOK** | File | Optional | `settings.json` |
| **MCP** | File | Optional | `.mcp.json`, `mcp.json` |

> **Note**: Commands and Agents allow nesting in subdirectories if the root matches a container alias.
