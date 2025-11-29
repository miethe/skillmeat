---
name: artifact-tracking
description: "Use this skill when creating, updating, or querying AI-optimized tracking artifacts. Invoke for: creating phase progress tracking, updating task status, querying pending/blocked tasks, generating session handoffs, validating artifacts, or understanding how to use progress files for orchestration. Provides YAML+Markdown hybrid format with 95% token reduction. Core functions: CREATE, UPDATE, QUERY, VALIDATE, ORCHESTRATE."
---

# Artifact Tracking Skill

Token-efficient tracking artifacts for AI agent orchestration.

## Why This Skill

Traditional tracking artifacts (pure markdown) waste tokens:
- Querying "all pending tasks": 92KB file returns everything (98.7% waste)
- Getting blockers: 160KB context for 800B answer (99.5% waste)
- Session handoff: Must read entire file every time

This skill provides a **YAML+Markdown hybrid format** optimized for AI agent consumption:
- Field-level queries: Get exactly what you need (1KB instead of 92KB)
- Structured metadata: Programmatically filter tasks by status, agent, priority
- Efficient updates: Change one field without rewriting entire file
- Token savings: 95-99% reduction in token usage

## When to Use

| Need | Function | Reference |
|------|----------|-----------|
| Create progress/context file | CREATE | `./creating-artifacts.md` |
| Update task status | UPDATE | `./updating-artifacts.md` |
| Find tasks/blockers | QUERY | `./querying-artifacts.md` |
| Validate before completion | VALIDATE | `./validating-artifacts.md` |
| Delegate tasks efficiently | ORCHESTRATE | `./orchestration-reference.md` |

## Quick Start

### CREATE Progress Tracking

```markdown
Task("artifact-tracker", "Create Phase 2 progress for auth-overhaul PRD")
```

Creates `.claude/progress/auth-overhaul/phase-2-progress.md` with structured YAML metadata.

See `./creating-artifacts.md` for detailed creation patterns.

### UPDATE Task Status

```markdown
Task("artifact-tracker", "Update auth-overhaul phase 2: Mark TASK-2.1 complete")
```

Surgical field-level update without full-file rewrite.

See `./updating-artifacts.md` for all update operations.

### QUERY Pending Work

```markdown
Task("artifact-query", "Show all blocked tasks in auth-overhaul phases 1-3")
```

Returns filtered results across multiple files.

See `./querying-artifacts.md` for query patterns.

### VALIDATE Before Completion

```markdown
Task("artifact-validator", "Validate Phase 2 progress for auth-overhaul PRD")
```

Schema compliance and quality checks.

See `./validating-artifacts.md` for validation types.

### ORCHESTRATE Task Delegation

```markdown
# Read progress file YAML → get batch strategy → copy Task() commands
# See ./orchestration-reference.md for complete workflow
```

This is the KEY function for Opus-level orchestration. See `./orchestration-reference.md` for step-by-step guidance on token-efficient task delegation.

## Directory Structure

```
.claude/
├── progress/[prd]/phase-N-progress.md   # ONE per phase
└── worknotes/[prd]/context.md           # ONE per PRD
```

**Policy**: See `.claude/specs/doc-policy-spec.md` for documentation limits.

## Embedded Agents

| Agent | Model | Use For |
|-------|-------|---------|
| artifact-tracker | Haiku | Create/update files |
| artifact-query | Haiku | Find tasks, generate reports |
| artifact-validator | Sonnet | Validate quality |

**Configuration**: See `./agents/` directory for agent prompts.

## Format Overview

YAML+Markdown hybrid with machine-readable frontmatter:

```yaml
---
type: progress
prd: "auth-overhaul"
phase: 2
status: in_progress
progress: 40
total_tasks: 10
completed_tasks: 4

tasks:
  - id: "TASK-2.1"
    status: "complete"
    assigned_to: ["ui-engineer"]     # REQUIRED for orchestration
    dependencies: []                  # REQUIRED for orchestration

parallelization:
  batch_1: ["TASK-2.1", "TASK-2.2"]
  batch_2: ["TASK-2.3"]
---

# Phase 2: Auth Overhaul

## Orchestration Quick Reference
[Pre-built Task() delegation commands here]
```

See `./format-specification.md` for complete field reference and schemas.

## Token Efficiency

| Operation | Traditional | Optimized | Savings |
|-----------|-------------|-----------|---------|
| Task list | 25KB | 2KB | 92% |
| Query blockers | 75KB | 3KB | 96% |
| Session handoff | 150KB | 5KB | 97% |

## Function Reference

For detailed guidance on each function:

- **CREATE**: `./creating-artifacts.md`
  - Creating progress files
  - Creating context files
  - Annotation workflow
  - Template usage

- **UPDATE**: `./updating-artifacts.md`
  - Task status updates
  - Progress percentage
  - Adding/resolving blockers
  - Context notes

- **QUERY**: `./querying-artifacts.md`
  - Finding pending/blocked tasks
  - Agent-specific queries
  - Session handoffs
  - Cross-phase queries

- **VALIDATE**: `./validating-artifacts.md`
  - Schema compliance
  - Metric accuracy
  - Orchestration readiness
  - Quality checks

- **ORCHESTRATE**: `./orchestration-reference.md`
  - Reading YAML metadata
  - Batch execution
  - Task delegation
  - Token optimization

## Scripts

Python utilities in `./scripts/`:

- `convert_to_hybrid.py` - Migrate legacy markdown to hybrid format
- `validate_artifact.py` - Schema validation
- `query_artifacts.py` - Programmatic queries

See `./migration-guide.md` for converting existing tracking files.

## Templates

See `./templates/` directory:

- `progress-template.md` - Phase progress tracking template
- `context-template.md` - PRD context notes template
- `bug-fix-template.md` - Bug fix tracking template
- `observation-log-template.md` - Monthly observation log template

See `./TEMPLATES-INDEX.md` for complete template catalog.

## Schemas

YAML schemas in `./schemas/`:

- `progress.schema.yaml` - Progress file validation schema
- `context.schema.yaml` - Context file validation schema
- `common-fields.yaml` - Shared field definitions

## Advanced Usage

### Query Patterns

See `./query-patterns.md` for:
- Cross-phase aggregation
- Filter combinations
- Timeline queries
- Critical path analysis

### Migration

See `./migration-guide.md` for:
- Converting legacy markdown
- Batch migration strategies
- Data preservation
- Validation after migration

### Format Specification

See `./format-specification.md` for:
- Complete YAML field reference
- Markdown section guidelines
- Status value enumerations
- ID naming conventions

## Best Practices

### CREATE

1. **ONE progress file per phase** - Never create duplicates
2. **Annotate immediately** - Add assigned_to and dependencies right away
3. **Use consistent IDs** - Pattern: TASK-[PHASE].[SEQUENCE]

### UPDATE

1. **Update immediately** after task completion
2. **Include notes** for context on decisions
3. **Use artifact-tracker** (not manual Edit)
4. **Mark blockers** when tasks can't proceed

### QUERY

1. **Query YAML only** for orchestration data
2. **Use filters** to reduce token usage
3. **Generate handoffs** for session transitions

### VALIDATE

1. **Validate before phase completion**
2. **Fix warnings** even if not errors
3. **Check orchestration readiness** before delegating

### ORCHESTRATE

1. **Read YAML frontmatter only** (~2KB vs ~25KB)
2. **Copy Task() commands** from Quick Reference section
3. **Execute batches in parallel** (single message)
4. **Update status immediately** after completion

See `./orchestration-reference.md` for complete orchestration workflow.

## Common Patterns

### Create + Annotate Flow

```markdown
# Step 1: Create progress file
Task("artifact-tracker", "Create Phase 1 progress for sync-redesign PRD.
Tasks: ArtifactFlowBanner, ComparisonSelector, DiffPreviewPanel.
Phase title: 'Sync Status Sub-Components'")

# Step 2: Annotate for orchestration
Task("lead-architect", "Annotate Phase 1 progress for sync-redesign:
- All tasks → ui-engineer-enhanced
- All independent (no dependencies)
- Generate batch_1 with all tasks parallel")
```

### Query + Delegate Flow

```markdown
# Step 1: Query pending tasks
Task("artifact-query", "Show pending tasks in sync-redesign Phase 1 batch_1")

# Step 2: Delegate in parallel (single message)
Task("ui-engineer-enhanced", "TASK-1.1: Create ArtifactFlowBanner...")
Task("ui-engineer-enhanced", "TASK-1.2: Create ComparisonSelector...")
Task("ui-engineer-enhanced", "TASK-1.3: Create DiffPreviewPanel...")

# Step 3: Update after completion
Task("artifact-tracker", "Update sync-redesign phase 1:
- TASK-1.1: complete
- TASK-1.2: complete
- TASK-1.3: complete")
```

### Validate + Complete Flow

```markdown
# Step 1: Validate completeness
Task("artifact-validator", "Validate Phase 1 progress for sync-redesign:
- All tasks complete
- No active blockers
- Progress at 100%")

# Step 2: Mark phase complete
Task("artifact-tracker", "Update sync-redesign phase 1: Set status to complete")
```

## Integration Points

### With Documentation Policy

Artifact tracking files are the ONLY allowed per-phase tracking files:
- `.claude/progress/[prd]/phase-N-progress.md` - ONE per phase
- `.claude/worknotes/[prd]/context.md` - ONE per PRD
- `.claude/worknotes/fixes/bug-fixes-YYYY-MM.md` - ONE per month
- `.claude/worknotes/observations/observation-log-MM-YY.md` - ONE per month

See `.claude/specs/doc-policy-spec.md` for complete policy.

### With Phase Execution

The `/dev:execute-phase` command uses orchestration patterns from this skill:
1. Reads progress file YAML
2. Identifies ready tasks from parallelization batches
3. Delegates using pre-built Task() commands
4. Updates status after completion
5. Validates before marking phase complete

### With Agent Delegation

All specialized agents (ui-engineer-enhanced, python-backend-engineer, etc.) expect:
- Tasks with clear IDs (TASK-X.Y)
- Assigned agent specified
- Dependencies noted
- Status tracking after completion

This skill provides the tracking infrastructure for the entire agent delegation system.

## Related Resources

- **Documentation Policy**: `.claude/specs/doc-policy-spec.md`
- **Agent Prompts**: `.claude/agents/`
- **Phase Execution**: `.claude/commands/execute-phase.md`
- **Task Delegation**: See CLAUDE.md "Agent Delegation" section

## Summary

This skill provides **token-efficient tracking artifacts** that enable Opus-level orchestration with 95% token reduction. The five core functions (CREATE, UPDATE, QUERY, VALIDATE, ORCHESTRATE) cover the complete lifecycle of progress tracking.

**Most Important**:
- For creating files: See `./creating-artifacts.md`
- For updating status: See `./updating-artifacts.md`
- For querying tasks: See `./querying-artifacts.md`
- For validation: See `./validating-artifacts.md`
- **For orchestration: See `./orchestration-reference.md`** (KEY for Opus agents)

Keep YAML frontmatter under 2KB, use surgical updates, and leverage pre-computed Task() commands for maximum token efficiency.
