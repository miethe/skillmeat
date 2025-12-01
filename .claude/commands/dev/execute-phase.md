---
description: Execute phase development with YAML-driven orchestration and artifact-tracking integration
argument-hint: <phase-number> [--plan=path/to/plan.md]
allowed-tools: Read, Grep, Glob, Edit, MultiEdit, Write,
  Bash(git:*), Bash(gh:*), Bash(pnpm:*), Bash(pytest:*),
  Bash(uv:*), Bash(pre-commit:*)
---

# /dev:execute-phase

You are Claude Code executing Phase `$ARGUMENTS` following the project implementation standards and the layered architecture: **routers → services → repositories → DB**.

This command leverages the **artifact-tracking skill** for YAML-driven orchestration, enabling token-efficient batch delegation and parallel task execution.

---

## Phase Execution Protocol

Remember that all documentation work MUST be delegated to the documentation-writer subagent. You MUST NOT write documentation yourself.

### Phase 0: Initialize Context & Tracking

Extract PRD name as `{PRD_NAME}` from attached plan or PRD and phase number from `$ARGUMENTS` and set up tracking infrastructure:

```bash
# Parse arguments
phase_num="${1}"
plan_path="${2}"

# Default plan path if not provided
if [ -z "$plan_path" ]; then
  plan_path="docs/project_plans/impl_tracking/${PRD_NAME}/phase-${phase_num}-*-implementation-plan.md"
  plan_path=$(ls $plan_path 2>/dev/null | head -1)
fi

if [ ! -f "$plan_path" ]; then
  echo "ERROR: Implementation plan not found at $plan_path"
  echo "Specify plan with: /dev:execute-phase ${phase_num} --plan=<path>"
  exit 1
fi

# Set up tracking directories
mkdir -p .claude/progress/${PRD_NAME}
mkdir -p .claude/worknotes/${PRD_NAME}

progress_file=".claude/progress/${PRD_NAME}/phase-${phase_num}-progress.md"
context_file=".claude/worknotes/${PRD_NAME}/context.md"

echo "📋 Phase ${phase_num} Execution Started"
echo "Plan: $plan_path"
echo "Progress: $progress_file"
echo "Context: $context_file"
```

**Read the implementation plan thoroughly.** This is your execution blueprint. Note:
- **DO NOT** load the linked PRD into context unless specific clarification is needed
- The plan should contain all necessary details
- Reference PRD only for ambiguous requirements

### Phase 1: Initialize Progress & Context Documents

#### 1.1 Create Progress Tracker with Orchestration

Use the **artifact-tracking skill** to create a YAML-orchestrated progress file:

```
Task("artifact-tracker", "Create Phase ${phase_num} progress tracking for ${PRD_NAME} PRD from implementation plan at ${plan_path}. Include all tasks with descriptions from the plan's development checklist.")
```

The artifact-tracker will create a progress file with basic task structure. Next, enhance it with orchestration metadata:

```
Task("lead-architect", "Annotate Phase ${phase_num} progress file for ${PRD_NAME} at ${progress_file}:
- Add 'assigned_to' field to every task (choose from: python-pro, ui-engineer, ui-engineer-enhanced, backend-typescript-architect, data-layer-expert, documentation-writer, code-reviewer, task-completion-validator)
- Add 'dependencies' field to every task (empty array [] if no dependencies)
- Add 'estimated_time' field (e.g., '2h', '4h', '1d')
- Compute parallelization strategy (which tasks can run in parallel vs sequentially)
- Generate batches in 'parallelization' YAML section (batch_1, batch_2, etc.)
- Create 'Orchestration Quick Reference' section with ready-to-copy Task() delegation commands for each batch")
```

**Expected Progress File Structure:**

```yaml
---
prd: ${PRD_NAME}
phase: ${phase_num}
status: in_progress
started: ${timestamp}
updated: ${timestamp}
completion: 0%

tasks:
  - id: TASK-1.1
    title: "Implement X component"
    description: "Create React component with Y pattern"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_time: "2h"
    status: pending

  - id: TASK-1.2
    title: "Add API endpoint for X"
    description: "Create FastAPI endpoint following layered architecture"
    assigned_to: ["python-pro"]
    dependencies: []
    estimated_time: "3h"
    status: pending

  - id: TASK-2.1
    title: "Wire X component to API"
    description: "Integrate component with React Query"
    assigned_to: ["ui-engineer"]
    dependencies: ["TASK-1.1", "TASK-1.2"]
    estimated_time: "1h"
    status: pending

parallelization:
  batch_1: ["TASK-1.1", "TASK-1.2"]  # No dependencies, run in parallel
  batch_2: ["TASK-2.1"]              # Depends on batch_1, run after
  critical_path: ["TASK-1.1", "TASK-2.1"]
  estimated_total_time: "6h"
---

# Phase ${phase_num} Progress Tracker

**Plan:** ${plan_path}
**Started:** ${timestamp}
**Status:** In Progress

## Orchestration Quick Reference

**Batch 1** (Parallel - 3h estimated):
- TASK-1.1 → `ui-engineer-enhanced` (2h)
- TASK-1.2 → `python-pro` (3h)

**Batch 2** (Sequential - 1h estimated):
- TASK-2.1 → `ui-engineer` (1h) - Depends on: TASK-1.1, TASK-1.2

### Task Delegation Commands

**Batch 1:**
```
Task("ui-engineer-enhanced", "TASK-1.1: Implement X component - Create React component with Y pattern following Projectarchitecture")
Task("python-pro", "TASK-1.2: Add API endpoint for X - Create FastAPI endpoint following layered architecture (router → service → repository)")
```

**Batch 2:**
```
Task("ui-engineer", "TASK-2.1: Wire X component to API - Integrate component with React Query, handle loading/error states")
```

---

## Success Criteria
- [ ] [Copy from plan - Performance/Accessibility/Testing requirements]

---

## Work Log

[Session entries added here as tasks complete]

---

## Decisions Log

[Architectural decisions logged here]

---

## Files Changed

[Tracked automatically by artifact-tracker]
```

#### 1.2 Create/Update Working Context Document

Create ONE context file per PRD (not per phase) at `.claude/worknotes/${PRD_NAME}/context.md`:

```markdown
# ${PRD_NAME} Working Context

**Purpose:** Token-efficient context for resuming work across AI turns and phases

---

## Current State

**Active Phase:** ${phase_num}
**Branch:** ${branch_name}
**Last Commit:** ${commit_hash}
**Current Task:** [What you're working on now]

---

## Key Decisions (Across All Phases)

- **Architecture:** [Key architectural choices made]
- **Patterns:** [Projectpatterns being followed]
- **Trade-offs:** [Important trade-offs made]

---

## Important Learnings

- **Gotcha 1:** [Brief description + how to avoid]
- **Gotcha 2:** [Brief description + how to avoid]

---

## Quick Reference

### Environment Setup
\`\`\`bash
# API
export PYTHONPATH="$PWD/services/api"

# Web
pnpm --filter "./apps/web" dev

# Tests
pnpm --filter "./apps/web" test -- --testPathPattern="pattern"
\`\`\`

### Key Files
- Schema: services/api/app/schemas/X.py
- Repository: services/api/app/repositories/X.py
- Service: services/api/app/services/X.py
- Router: services/api/app/api/v1/endpoints/X.py
- UI: apps/web/src/components/X.tsx

---

## Phase ${phase_num} Scope

[Copy executive summary from plan - 2-3 sentences max]

**Success Metric:** [Copy key metric from plan]
```

### Phase 2: Execute Using Orchestration Quick Reference

Work through the plan using the pre-computed parallelization strategy in the progress file.

#### 2.1 Read Progress File YAML Only (Token Efficient)

**DO NOT** read the entire progress file. Instead, extract only the YAML frontmatter:

```bash
# Extract YAML frontmatter (first ~100 lines, ~2KB vs ~25KB for full file)
head -100 ${progress_file} | sed -n '/^---$/,/^---$/p'
```

From YAML, identify:
- Current `tasks` array with `assigned_to`, `dependencies`, `status`
- `parallelization` section with batch groupings
- Tasks ready to execute (all dependencies have `status: completed`)

#### 2.2 Delegate in Batches

**Use the ready-to-copy Task() commands from "Orchestration Quick Reference" section.**

Instead of manually constructing delegation, scroll to the "Orchestration Quick Reference" section and copy the Task() commands for the current batch.

**Batch Execution Strategy:**

1. **Batch 1** (No dependencies):
   - Execute ALL tasks in `parallelization.batch_1` in parallel
   - Use a single message with multiple Task() tool calls
   - Example:
     ```
     Task("ui-engineer-enhanced", "TASK-1.1: Implement X component...")
     Task("python-pro", "TASK-1.2: Add API endpoint for X...")
     ```

2. **Wait** for Batch 1 to complete

3. **Batch 2** (Dependencies from Batch 1):
   - Execute tasks whose dependencies are now met
   - Continue batch-by-batch

4. **Update Task Status** after each task completes:
   ```
   Task("artifact-tracker", "Update ${PRD_NAME} phase ${phase_num}: Mark TASK-1.1 as completed with commit abc1234")
   ```

**Task Delegation Template:**

```
@{agent-from-assigned_to}

Phase ${phase_num}, {task_id}: {task_title}

{task_description}

ProjectPatterns to Follow:
- Layered architecture: routers → services → repositories → DB
- ErrorResponse envelopes for errors
- Cursor pagination for lists
- Telemetry spans and structured JSON logs
- DTOs separate from ORM models

Success criteria:
- [What defines completion]
```

**If subagent invocation fails:** Document in progress tracker and proceed with direct implementation.

#### 2.3 Validate Task Completion

After each major task, validate with the task-completion-validator:

```
@task-completion-validator

Phase ${phase_num}, Task: {task_id}

Expected outcomes:
- [Outcome 1 from task description]
- [Outcome 2 from task description]

Files changed:
- {list files}

Please validate:
1. All acceptance criteria met
2. Projectarchitecture patterns followed
3. Tests exist and pass
4. No regression introduced
```

**Validation checklist per task:**
- [ ] Acceptance criteria met
- [ ] Code follows Projectlayered architecture
- [ ] Tests exist and pass
- [ ] TypeScript/Python types correct
- [ ] Error handling implemented
- [ ] Telemetry/logging added
- [ ] Documentation updated if needed

#### 2.4 Commit Frequently

After each completed task (or logical unit of work), commit:

```bash
# Add changed files
git add {files}

# Commit with conventional commits format
git commit -m "feat(web): implement {feature} following Projectarchitecture

- Added {component/service/etc}
- Wired telemetry spans
- Added tests with {coverage}%

Refs: Phase ${phase_num}, {task_id}"
```

**Commit message guidelines:**
- Use conventional commits: `feat|fix|test|docs|refactor|perf|chore`
- Reference phase and task ID
- Keep focused (1 task per commit preferred)
- Include what was tested

#### 2.5 Update Progress Document

After **every** completed task, update via artifact-tracker:

```
Task("artifact-tracker", "Update ${PRD_NAME} phase ${phase_num}:
- Mark {task_id} as completed
- Add commit {commit_hash}
- Log: Implemented {brief_description}")
```

The artifact-tracker will:
- Update task status in YAML
- Update completion percentage
- Add work log entry
- Track files changed
- Update parallelization batch status

---

## Orchestration Efficiency Guidelines

### Token-Efficient Delegation

**DO:**
- Read only YAML frontmatter for task metadata (~2KB)
- Copy Task() commands from "Orchestration Quick Reference"
- Use artifact-tracker for status updates
- Execute batches in parallel (single message with multiple Task calls)

**DO NOT:**
- Read entire progress file for delegation (~25KB)
- Re-analyze task dependencies (already computed by lead-architect)
- Manually construct Task() commands (use Quick Reference)
- Execute parallel tasks sequentially (wastes time)

### Parallelization Strategy

The progress file YAML includes pre-computed `parallelization` section:

```yaml
parallelization:
  batch_1: ["TASK-1.1", "TASK-1.2", "TASK-1.3"]  # No dependencies
  batch_2: ["TASK-2.1", "TASK-2.2"]              # Depends on batch_1
  batch_3: ["TASK-3.1"]                          # Depends on batch_2
  critical_path: ["TASK-1.1", "TASK-2.1", "TASK-3.1"]
  estimated_total_time: "12h"
```

**Execution Pattern:**
1. Execute all tasks in `batch_1` in **parallel** (single message)
2. **Wait** for batch to complete
3. Execute all tasks in `batch_2` in **parallel**
4. Continue sequentially through batches, tasks within batches in parallel

### Required Task Fields

Every task in progress files MUST have:
- `assigned_to`: Array of agent names for delegation
- `dependencies`: Array of task IDs that must complete first (empty `[]` if none)
- `estimated_time`: Time estimate (e.g., "2h", "4h", "1d")
- `status`: Current status (pending, in_progress, completed, blocked)

**If these fields are missing**, delegate to lead-architect to annotate first:

```
Task("lead-architect", "Annotate progress file ${progress_file} with missing orchestration fields (assigned_to, dependencies, estimated_time)")
```

---

### Phase 3: Continuous Testing

Run tests continuously throughout implementation:

#### Backend Tests (if applicable)

```bash
# Run specific test file
uv run --project services/api pytest app/tests/test_X.py -v

# Run all tests
uv run --project services/api pytest

# Type checking
uv run --project services/api mypy app

# Linting
uv run --project services/api ruff check
```

#### Frontend Tests (if applicable)

```bash
# Run component tests
pnpm --filter "./apps/web" test -- --testPathPattern="ComponentName"

# Run all tests
pnpm --filter "./apps/web" test

# Type checking
pnpm --filter "./apps/web" typecheck

# Linting
pnpm --filter "./apps/web" lint
```

#### UI Package Tests (if applicable)

```bash
# Storybook component tests
pnpm --filter "./packages/ui" test

# A11y tests
pnpm --filter "./packages/ui" test:a11y

# Build stories
pnpm --filter "./packages/ui" storybook
```

**Test failure protocol:**
1. Fix immediately if related to current work
2. Document in progress tracker if unrelated
3. DO NOT proceed to next task if tests fail for current work

### Phase 4: Milestone Validation

At each major milestone (typically after completing a batch):

#### 4.1 Run Full Validation

```bash
#!/bin/bash
set -euo pipefail

echo "🔍 Running Phase ${phase_num} validation..."

# Type checking
echo "Type checking..."
pnpm -r typecheck
uv run --project services/api mypy app

# Linting
echo "Linting..."
pnpm -r lint
uv run --project services/api ruff check

# Tests
echo "Running tests..."
pnpm -r test
uv run --project services/api pytest

# Build check
echo "Build check..."
pnpm --filter "./apps/web" build

echo "✅ Validation complete"
```

#### 4.2 Validate with Subagent

```
@task-completion-validator

Phase ${phase_num} Milestone: Batch {batch_num} Complete

Completed tasks:
- {task_id_1}
- {task_id_2}

Expected outcomes from plan:
- [Outcome 1]
- [Outcome 2]

Please validate:
1. All batch tasks complete
2. Success criteria met
3. No regressions
4. Tests comprehensive
5. Documentation updated
```

#### 4.3 Update Context Document

Update `.claude/worknotes/${PRD_NAME}/context.md` with learnings from milestone:

```markdown
## Important Learnings

- **[New learning]:** Description and how to handle
```

### Phase 5: Final Phase Validation

When ALL tasks in the implementation plan are complete:

#### 5.1 Review Success Criteria

Go through **every** success criterion in the plan and verify:

```markdown
## Success Criteria Review

### Performance Requirements (if applicable)
- [x] Lighthouse Performance score >90 - Score: 92
- [x] FCP <1.5s - Measured: 1.2s
- [x] LCP <2.5s - Measured: 2.1s
[etc...]

### Accessibility Requirements (if applicable)
- [x] WCAG 2.1 AA compliance - Validated with axe
- [x] Zero critical violations - Confirmed
[etc...]

### Testing Requirements
- [x] E2E coverage >80% - Coverage: 85%
- [x] Unit coverage >70% - Coverage: 78%
[etc...]
```

#### 5.2 Final Validation with Subagent

```
@task-completion-validator

Phase ${phase_num} FINAL VALIDATION

Plan: ${plan_path}
Progress: ${progress_file}

Please perform comprehensive validation:
1. All tasks in plan completed
2. All success criteria met
3. All tests passing
4. No critical issues
5. Documentation complete
6. Ready for next phase
```

#### 5.3 Run Quality Gates

```bash
#!/bin/bash
set -euo pipefail

echo "🎯 Phase ${phase_num} Final Quality Gates"

# All tests must pass
pnpm -r test || { echo "❌ Tests failed"; exit 1; }
uv run --project services/api pytest || { echo "❌ API tests failed"; exit 1; }

# Type safety
pnpm -r typecheck || { echo "❌ Type check failed"; exit 1; }
uv run --project services/api mypy app || { echo "❌ Mypy failed"; exit 1; }

# Linting
pnpm -r lint || { echo "❌ Lint failed"; exit 1; }
uv run --project services/api ruff check || { echo "❌ Ruff failed"; exit 1; }

# Build
pnpm --filter "./apps/web" build || { echo "❌ Build failed"; exit 1; }

# A11y (if UI phase)
if [ "${phase_num}" != "api-only" ]; then
  pnpm --filter "./packages/ui" test:a11y || { echo "❌ A11y failed"; exit 1; }
fi

echo "✅ All quality gates passed"
```

#### 5.4 Final Progress Update

Update progress tracker with final status via artifact-tracker:

```
Task("artifact-tracker", "Finalize ${PRD_NAME} phase ${phase_num}:
- Mark phase as completed
- Update completion to 100%
- Generate phase completion summary")
```

Expected final state:

```yaml
---
status: completed
completion: 100%
completed_at: ${timestamp}
---

## Phase Completion Summary

**Total Tasks:** X
**Completed:** X
**Success Criteria Met:** X/X
**Tests Passing:** ✅
**Quality Gates:** ✅

**Key Achievements:**
- [Achievement 1]
- [Achievement 2]

**Technical Debt Created:**
- [Any intentional shortcuts with tracking issue]

**Recommendations for Next Phase:**
- [Suggestion 1]
- [Suggestion 2]
```

#### 5.5 Push All Changes

```bash
# Ensure all commits are pushed
git push origin ${branch_name}

echo "✅ Phase ${phase_num} complete and pushed"
echo "Progress: ${progress_file}"
echo "Context: ${context_file}"
```

---

## Error Recovery Protocol

If ANY task fails or blocks:

### 1. Document the Issue

Update progress tracker via artifact-tracker:

```
Task("artifact-tracker", "Update ${PRD_NAME} phase ${phase_num}:
- Mark {task_id} as blocked
- Log blocker: {description}
- Add to blockers section")
```

### 2. Attempt Recovery

Common recovery strategies:

**Git conflicts:**
```bash
git stash
git pull --rebase origin ${branch_name}
git stash pop
# Resolve conflicts
git add .
git rebase --continue
```

**Test failures:**
- Fix immediately if related to current work
- Document and skip if unrelated (create tracking issue)
- Use debugger subagent for complex failures

**Build failures:**
```bash
# Clean and rebuild
rm -rf .next node_modules/.cache
pnpm install
pnpm build
```

**Subagent failures:**
- Retry once
- If fails again, document and proceed with direct implementation
- Note in decisions log why direct approach was taken

### 3. If Unrecoverable

Update progress file:

```yaml
---
status: blocked
---

**Blocker Details:**
- Task: {task_id}
- Issue: {description}
- Attempted Solutions: {list}
- Needs: {what's needed to unblock}
```

Stop execution and report to user with:
- Clear description of blocker
- What was attempted
- What's needed to proceed
- Current state of work (all committed)

---

## ProjectArchitecture Compliance Checklist

Ensure every implementation follows Projectpatterns:

### Backend Implementation
- [ ] **Layered architecture:** router → service → repository → DB
- [ ] **DTOs separate** from ORM models (app/schemas vs app/models)
- [ ] **ErrorResponse** envelope for all errors
- [ ] **Cursor pagination** for list endpoints with `{ items, pageInfo }`
- [ ] **Telemetry spans** named `{route}.{operation}`
- [ ] **Structured logs** with trace_id, span_id, user_id, request_id
- [ ] **RLS patterns** in repository layer
- [ ] **Alembic migration** if schema changed
- [ ] **OpenAPI docs** updated for new endpoints

### Frontend Implementation
- [ ] **Import from @meaty/ui** only (no direct Radix)
- [ ] **React Query** for data fetching
- [ ] **Error boundaries** around new components
- [ ] **Loading states** handled
- [ ] **Accessibility** checked (keyboard nav, ARIA, contrast)
- [ ] **Responsive design** (mobile, tablet, desktop)
- [ ] **TypeScript** strict mode, no `any`
- [ ] **Storybook story** if in packages/ui
- [ ] **Tests** for components and hooks

### Testing Requirements
- [ ] **Unit tests** for business logic
- [ ] **Integration tests** for API flows
- [ ] **E2E tests** for critical paths
- [ ] **Negative test cases** included
- [ ] **Edge cases** covered
- [ ] **A11y tests** for UI components
- [ ] **Coverage** meets phase requirements

---

## Phase Completion Definition

Phase is **ONLY** complete when:

1. ✅ **All tasks** in implementation plan completed
2. ✅ **All success criteria** met (verified)
3. ✅ **All tests** passing (backend + frontend + e2e)
4. ✅ **Quality gates** passed (types, lint, build)
5. ✅ **Documentation** updated (code comments, ADRs if needed)
6. ✅ **Progress tracker** shows `status: completed`
7. ✅ **Context document** updated with learnings
8. ✅ **All commits** pushed to branch
9. ✅ **Validation** completed by task-completion-validator
10. ✅ **No critical blockers** or P0 issues

**DO NOT** mark phase complete if any of above are incomplete.

---

## Output Format

Provide clear, structured status updates throughout:

```
📋 Phase ${phase_num} Execution Update

**Orchestration Status:**
- Batch 1: ✅ Complete (3/3 tasks)
- Batch 2: 🔄 In Progress (1/2 tasks)
- Batch 3: ⏳ Pending (2 tasks)
- Critical Path: 60% complete

**Current Batch (2):**
- ✅ TASK-2.1 → ui-engineer-enhanced
- 🔄 TASK-2.2 → python-pro (in progress)

**Completed This Session:**
- TASK-1.1: Implemented X component
- TASK-1.2: Added API endpoint for Y

**Blocked:**
- None

**Recent Commits:**
- abc1234 feat(web): implement X component
- def5678 feat(api): add Y endpoint

**Next Actions:**
- Wait for TASK-2.2 completion
- Launch Batch 3: TASK-3.1, TASK-3.2

**Progress:** 60% (6/10 tasks complete)
```

---

## Quickstart Examples

```bash
# Execute phase 4 with default plan location
/dev:execute-phase 4

# Execute phase 1 with explicit plan path
/dev:execute-phase 1 --plan=docs/project_plans/impl_tracking/web-v2/phase-1-foundation-implementation-plan.md

# Resume phase 2 (will pick up from progress tracker)
/dev:execute-phase 2
```

---

## Integration with Artifact-Tracking Skill

This command integrates with the **artifact-tracking skill** for:

1. **Progress Creation**: `artifact-tracker` creates initial progress files from implementation plans
2. **Orchestration**: `lead-architect` annotates tasks with delegation metadata
3. **Status Updates**: `artifact-tracker` updates task status, completion, and work logs
4. **Finalization**: `artifact-tracker` generates phase completion summaries

**Skill Reference:** `.claude/skills/artifact-tracking/SKILL.md`

---

Remember: **Follow the orchestration plan, delegate in batches, validate continuously, commit frequently, and track everything efficiently.**
