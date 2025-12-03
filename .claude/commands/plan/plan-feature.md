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

## Understanding the Pattern

**The Pattern**:
1. You invoke a skill → skill expands with instructions/tools
2. You read the skill's instructions
3. You follow those instructions, which direct you to delegate to subagents

**Skills contain the logic; this command standardizes the invocation order.**

## Workflow

### Mode: --all (Default)

1. **Invoke planning skill**:
   - Skill expands with planning instructions
   - Skill directs you to delegate to subagents like `prd-writer`, `implementation-planner`
   - Follow skill's instructions to generate PRD (if complex) and Implementation Plan
   - Break plans >800 lines into phase files per skill guidance

2. **Invoke artifact-tracking skill**:
   - Skill expands with tracking artifact instructions
   - Skill provides YAML+Markdown format guidance
   - Follow skill's instructions to create progress files (ONE per phase) and context file (ONE per PRD)
   - Include assigned_to and dependencies per skill templates

### Mode: --impl-only

1. **Invoke planning skill**:
   - Skill expands with planning instructions
   - Follow skill's instructions to skip PRD, generate Implementation Plan only
   - Skill directs which subagents to use for plan generation
   - Break plans >800 lines into phase files per skill guidance

### Mode: --plan-progress

1. **Invoke planning skill**:
   - Skill expands with planning instructions
   - Follow skill's instructions to generate Implementation Plan
   - Break plans >800 lines into phase files per skill guidance

2. **Invoke artifact-tracking skill**:
   - Skill expands with tracking artifact instructions
   - Follow skill's instructions to create progress and context files
   - Include assigned_to and dependencies per skill templates

## Execution

For all modes:

```markdown
# Step 1: Planning
skill: "planning"
[Wait for skill to expand]
[Read skill's instructions]
[Follow instructions - they will direct you to delegate to subagents like ai-artifacts-engineer, prd-writer, implementation-planner]

# Step 2: Tracking (if not --impl-only)
skill: "artifact-tracking"
[Wait for skill to expand]
[Read skill's instructions]
[Follow instructions to create tracking artifacts with subagents]
```

**Your role**: Read skill instructions → follow them → delegate to subagents as directed.

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
