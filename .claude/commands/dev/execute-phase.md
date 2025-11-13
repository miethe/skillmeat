---
description: Execute phase development following MP implementation plan and tracking patterns
argument-hint: <phase-number> [--plan=path/to/plan.md]
allowed-tools: Read, Grep, Glob, Edit, MultiEdit, Write,
  Bash(git:*), Bash(gh:*), Bash(pnpm:*), Bash(pytest:*),
  Bash(uv:*), Bash(pre-commit:*)
---

# /dev:execute-phase

You are Claude Code executing Phase `$ARGUMENTS` following MeatyPrompts implementation standards and the layered architecture: **routers → services → repositories → DB**.

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
mkdir -p docs/project_plans/impl_tracking/${PRD_NAME}/{progress,context}

progress_file="docs/project_plans/impl_tracking/${PRD_NAME}/progress/phase-${phase_num}-progress.md"
context_file="docs/project_plans/impl_tracking/${PRD_NAME}/context/phase-${phase_num}-context.md"

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

#### 1.1 Create Progress Tracker

Create `${progress_file}` if it doesn't exist, or resume from existing state:

```markdown
# Phase ${phase_num} Progress Tracker

**Plan:** ${plan_path}
**Started:** ${timestamp}
**Last Updated:** ${timestamp}
**Status:** In Progress

---

## Completion Status

### Success Criteria
- [ ] [Copy from plan - Performance/Accessibility/Testing requirements]
- [ ] [Update checkboxes as tasks complete]

### Development Checklist
- [ ] [Task 1 from implementation plan]
- [ ] [Task 2 from implementation plan]
- [ ] [Task 3 from implementation plan]

---

## Work Log

### ${date} - Session ${n}

**Completed:**
- Task X: Brief description
- Task Y: Brief description

**Subagents Used:**
- @backend-typescript-architect - API design
- @ui-engineer - Component implementation
- @debugger - Fixed issue with X

**Commits:**
- abc1234 feat(web): implement X following MP architecture
- def5678 test(web): add tests for X with coverage

**Blockers/Issues:**
- None

**Next Steps:**
- Continue with Task Z
- Validate completion of milestone M

---

## Decisions Log

- **[${timestamp}]** Chose approach X over Y because Z
- **[${timestamp}]** Modified plan to account for constraint C

---

## Files Changed

### Created
- /path/to/new/file1.tsx - Brief purpose

### Modified
- /path/to/existing/file1.ts - What changed

### Deleted
- /path/to/obsolete/file.ts - Why removed
```

#### 1.2 Create Working Context Document

Create `${context_file}` with implementation-specific context (aim for <2000 tokens):

```markdown
# Phase ${phase_num} Working Context

**Purpose:** Token-efficient context for resuming work across AI turns

---

## Current State

**Branch:** ${branch_name}
**Last Commit:** ${commit_hash}
**Current Task:** [What you're working on now]

---

## Key Decisions

- **Architecture:** [Key architectural choices made]
- **Patterns:** [MP patterns being followed]
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

## Phase Scope (From Plan)

[Copy executive summary from plan - 2-3 sentences max]

**Success Metric:** [Copy key metric from plan]
```

### Phase 2: Execute Implementation Plan

Work through the plan's development checklist **sequentially**. For each major task:

#### 2.1 Identify Required Expertise

Determine which subagent(s) to use based on task type:

| Task Type | Subagent |
|-----------|----------|
| Orchestrate Work/Key Architecture Decisions | lead-architect |
| ALL Documentation | documentation-writer |
| API/Backend work | python-pro |
| UI/Component Design | ui-designer |
| UI/React components | ui-engineer |
| Frontend analysis | frontend-architect |
| Frontend development | frontend-developer |
| Fixing issues | debugger |
| Code quality review | code-reviewer |
| Task Validation | task-completion-validator |
| Testing | Direct implementation (or test-engineer if complex) |

#### 2.2 Execute Task with Subagent

Delegate to appropriate subagent with clear context:

```
@{subagent-name}

Phase ${phase_num}, Task: {task_name}

Requirements:
- [Specific requirement from plan]
- [Specific requirement from plan]

MP Patterns to Follow:
- Layered architecture: routers → services → repositories → DB
- ErrorResponse envelopes for errors
- Cursor pagination for lists
- Telemetry spans and structured JSON logs
- DTOs separate from ORM models

Files to modify:
- {file_path_1}
- {file_path_2}

Success criteria:
- [What defines completion]
```

**If subagent invocation fails:** Document in progress tracker and proceed with direct implementation.

#### 2.3 Validate Task Completion

After each major task, validate with the task-completion-validator:

```
@task-completion-validator

Phase ${phase_num}, Task: {task_name}

Expected outcomes:
- [Outcome 1 from plan]
- [Outcome 2 from plan]

Files changed:
- {list files}

Please validate:
1. All acceptance criteria met
2. MP architecture patterns followed
3. Tests exist and pass
4. No regression introduced
```

**Validation checklist per task:**
- [ ] Acceptance criteria met
- [ ] Code follows MP layered architecture
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
git commit -m "feat(web): implement {feature} following MP architecture

- Added {component/service/etc}
- Wired telemetry spans
- Added tests with {coverage}%

Refs: Phase ${phase_num}, Task {task_name}"
```

**Commit message guidelines:**
- Use conventional commits: `feat|fix|test|docs|refactor|perf|chore`
- Reference phase and task
- Keep focused (1 task per commit preferred)
- Include what was tested

#### 2.5 Update Progress Document

After **every** completed task, update progress tracker:

```markdown
### ${date} - Session ${n}

**Completed:**
- ✅ Task X: Implemented Y with Z pattern

**Commits:**
- abc1234 feat(web): implement X

**Next:** Task Y
```

Update relevant checklists by changing `- [ ]` to `- [x]`.

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

At each major milestone (typically after completing a section in the plan):

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

Phase ${phase_num} Milestone: {milestone_name}

Completed tasks:
- [Task 1]
- [Task 2]
- [Task 3]

Expected outcomes from plan:
- [Outcome 1]
- [Outcome 2]

Please validate:
1. All milestone tasks complete
2. Success criteria met
3. No regressions
4. Tests comprehensive
5. Documentation updated
```

#### 4.3 Update Context Document

Update `${context_file}` with learnings from milestone:

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

Update progress tracker with final status:

```markdown
**Status:** ✅ Complete

**Completion Date:** ${date}

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

Update progress tracker immediately:

```markdown
**Blockers/Issues:**
- **[${timestamp}]** Task X blocked by Y
  - Error: {error message}
  - Attempted: {what you tried}
  - Status: {blocked|investigating|resolved}
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

```markdown
**Status:** ⚠️ Blocked

**Blocker Details:**
- Task: {task_name}
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

## MP Architecture Compliance Checklist

Ensure every implementation follows MP patterns:

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
6. ✅ **Progress tracker** shows complete status
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

Current Task: {task_name}
Status: {in_progress|completed|blocked}

Progress:
- ✅ Task A
- ✅ Task B
- 🔄 Task C (current)
- ⏳ Task D (pending)

Recent Commits:
- abc1234 feat(web): implement X

Subagents Used:
- @backend-typescript-architect (API design)
- @ui-engineer (Component implementation)

Next Steps:
- Complete Task C
- Validate with task-completion-validator
- Begin Task D
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

Remember: **Follow the plan, validate continuously, commit frequently, and track everything.**
