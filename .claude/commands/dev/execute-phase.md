---
description: Execute phase development with YAML-driven orchestration
argument-hint: <phase-number> [--plan=path/to/plan.md]
allowed-tools: Read, Grep, Glob, Edit, MultiEdit, Write, Skill,
  Bash(git:*), Bash(gh:*), Bash(pnpm:*), Bash(pytest:*),
  Bash(uv:*), Bash(pre-commit:*)
---

# Execute Phase

Execute phase `$ARGUMENTS` using YAML-driven orchestration.

## Step 0: Load Required Skills (MANDATORY)

**Execute these Skill tool calls NOW before any other action:**

```text
Skill("dev-execution")
Skill("artifact-tracking")
```

⚠️ **DO NOT PROCEED** until both skills are loaded. The guidance below depends on skill content.

---

## Execution Mode

Reference: [.claude/skills/dev-execution/modes/phase-execution.md]

## Actions

### 1. Initialize Context

Extract `{PRD_NAME}` and `{PHASE_NUM}` from `$ARGUMENTS`.

Validate tracking at: `.claude/progress/${PRD_NAME}/phase-${PHASE_NUM}-progress.md`

If missing: `Task("artifact-tracker", "Create Phase ${PHASE_NUM} progress for ${PRD_NAME}")`

### 2. Read Progress YAML (Token-Efficient)

```bash
head -100 ${progress_file} | sed -n '/^---$/,/^---$/p'
```

Identify current batch from `parallelization` field.

### 3. Batch Delegation

Load patterns: [.claude/skills/dev-execution/orchestration/batch-delegation.md]

Execute batch tasks in parallel (single message with multiple Task() calls).

### 4. Continuous Testing

```bash
pnpm test && pnpm typecheck && pnpm lint
```

### 5. Update Tracking

After each task: `Task("artifact-tracker", "Update ${PRD_NAME} phase ${PHASE_NUM}: Mark TASK-X.Y complete")`

Update request-log if applicable: `meatycapture log item update DOC ITEM --status done`

### 6. Milestone Validation

Load criteria: [.claude/skills/dev-execution/validation/milestone-checks.md]

## Quality Gates

- [ ] All batch tasks complete
- [ ] Tests pass
- [ ] No TypeScript errors
- [ ] Progress artifact updated

## Skill References

- Phase execution: [.claude/skills/dev-execution/modes/phase-execution.md]
- Orchestration: [.claude/skills/dev-execution/orchestration/]
- Validation: [.claude/skills/dev-execution/validation/]
- Artifact integration: [.claude/skills/dev-execution/integrations/artifact-tracking.md]
- Request-log: [.claude/skills/dev-execution/integrations/request-log-workflow.md]
