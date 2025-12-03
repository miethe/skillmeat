---
description: Plan new features with PRD, implementation plan, and progress tracking using planning and artifact-tracking skills
allowed-tools: Task, Skill, Read, Write, Edit, Bash
argument-hint: [request-or-file] [--impl-only|-i] [--plan-progress|-p] [--all|-a]
---

**You are Opus. Tokens are expensive. You orchestrate; subagents execute.**

You must use subagents to perform all tasks, only delegating work. Use them wisely to optimize for reasoning, with all token-heavy work being delegated.

**Commit often.**

---

## Mode Selection

Parse mode from "$ARGUMENTS":

- `--impl-only` or `-i`: Implementation Plan only (skip PRD)
- `--plan-progress` or `-p`: Plan + Progress tracking artifacts only
- `--all` or `-a` (default if no flag): Full process - PRD (if complex), Implementation Plan, and tracking artifacts

## Workflow

### Mode: --all (Default)

1. **Invoke planning skill**:
   - If complex feature: Generate PRD from feature request
   - Always generate Implementation Plan
   - Break plans >800 lines into phase files

2. **Invoke artifact-tracking skill**:
   - Create progress tracking files (ONE per phase)
   - Create context file (ONE per PRD)
   - Include assigned_to and dependencies for orchestration

### Mode: --impl-only

1. **Invoke planning skill**:
   - Skip PRD generation
   - Generate Implementation Plan from provided request/file
   - Break plans >800 lines into phase files

### Mode: --plan-progress

1. **Invoke planning skill**:
   - Generate Implementation Plan from provided request/file
   - Break plans >800 lines into phase files

2. **Invoke artifact-tracking skill**:
   - Create progress tracking files (ONE per phase)
   - Create context file (ONE per PRD)
   - Include assigned_to and dependencies for orchestration

## Execution

For all modes:

```markdown
# Step 1: Planning
skill: "planning"
[Wait for planning skill completion]

# Step 2: Tracking (if not --impl-only)
skill: "artifact-tracking"
[Wait for tracking skill completion]
```

The skills will handle all token-heavy work. Your role is orchestration only.

## Input Handling

"$ARGUMENTS" may contain:
- Inline feature description
- Path to PRD file
- Path to feature request document
- Mode flags (--impl-only, --plan-progress, --all)

Pass the full input to the skills - they will parse appropriately.

## Critical Reminders

- **Never write code directly** - delegate to specialized subagents
- **Never explore codebases yourself** - use codebase-explorer
- **Focus on reasoning** - all implementation is delegated
- **Update progress immediately** after task completion
- **Commit after changes** - don't batch commits

Use Task() commands from progress file Quick Reference sections for maximum efficiency.
