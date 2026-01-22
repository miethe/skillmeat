# Enhanced Frontmatter Utilization - Context

## Feature Summary

Extract, cache, and leverage Claude Code frontmatter metadata for artifact discovery, enrichment, and intelligent linking within the marketplace.

## Key Deliverables

1. **Platform & Tool Enums** - Track artifact platform targets and tool dependencies
2. **Frontmatter Extraction** - Auto-populate description and tools from frontmatter during import
3. **Artifact Linking** - Auto-link artifacts by name within same source, with manual linking UI
4. **UI Improvements** - Exclude raw frontmatter from ContentPane, add LinkedArtifactsSection

## Architecture Context

### Backend Files
- `skillmeat/core/artifact.py` - Artifact, ArtifactMetadata dataclasses
- `skillmeat/core/artifact_detection.py` - ArtifactType enum, detection logic
- `skillmeat/api/schemas/artifact.py` - Pydantic schemas

### Frontend Files
- `skillmeat/web/types/artifact.ts` - TypeScript interfaces
- `skillmeat/web/lib/frontmatter.ts` - Parsing utilities
- `skillmeat/web/components/entity/content-pane.tsx` - Content display
- `skillmeat/web/components/entity/frontmatter-display.tsx` - Formatted FM display

## Claude Code Tool Reference

Tools for enum: AskUserQuestion, Bash, TaskOutput, Edit, ExitPlanMode, Glob, Grep, KillShell, MCPSearch, NotebookEdit, Read, Skill, Task, TodoWrite, WebFetch, WebSearch, Write

## Frontmatter Fields to Extract

**Agents**: name, description, tools, disallowedTools, model, permissionMode, skills, hooks
**Skills/Commands**: name, description, argument-hint, disable-model-invocation, user-invocable, allowed-tools, model, context, agent, hooks

## Key Decisions

- Default Platform: CLAUDE_CODE
- Unmatched references: Store for manual linking (don't discard)
- Auto-link scope: Within same Source only
- Frontend first for Phase 0 types to unblock UI work

## Progress Location

`.claude/progress/enhanced-frontmatter-utilization/all-phases-progress.md`
