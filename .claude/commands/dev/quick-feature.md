---
description: Quick feature implementation - streamlined planning + execution for simple enhancements
allowed-tools: Read, Write, Edit, MultiEdit, Bash(git:*), Bash(pnpm:*), Grep, Glob, Task
argument-hint: [feature-text|file-path|REQ-ID]
---

# /dev:quick-feature

**You are Opus. Tokens are expensive. You orchestrate; subagents execute.**

Streamlined planning and execution for simple features. For complex features requiring phased breakdown, use `/plan:plan-feature` instead.

---

## When NOT to Use

- Multi-phase features (>1 day estimated work)
- Features requiring PRD/stakeholder review
- Cross-cutting concerns affecting >5 files per layer
- Features with unclear requirements needing discovery
- Database migrations requiring careful planning

→ Use `/plan:plan-feature` for these cases instead.

---

## Input Resolution

Parse `$ARGUMENTS` to determine input type:

| Pattern | Type | Action |
|---------|------|--------|
| `REQ-YYYYMMDD-*-XX` | Request Log ID | Use `meatycapture-capture` skill |
| Starts with `./`, `/`, or `~` | File path | Read file contents directly |
| Other | Direct text | Use as feature description |

### For Request Log Input

Invoke skill: **meatycapture-capture**

1. Search for item by ID to get full details (title, type, domain, context, notes)
2. Update status to `in-progress` before starting work
3. Use extracted details as feature requirements

The skill explains all request-log interactions - reading, searching, status updates, and captures.

---

## Phase 1: Minimal Planning (~5 min)

### 1.1 Pattern Discovery

Delegate to **codebase-explorer** agent:

> Find existing patterns related to the feature. Look for similar implementations, relevant file locations, import conventions, and test patterns.

### 1.2 Create Quick Plan

Generate slug from feature description (lowercase, hyphens, max 30 chars).

Write plan to `.claude/progress/quick-features/{feature-slug}.md`:

```markdown
---
type: quick-feature-plan
feature_slug: {slug}
request_log_id: {id if from REQ input, else null}
status: in-progress
created: {ISO date}
estimated_scope: small|medium
---

# {Feature Title}

## Scope
{1-2 sentences describing what this implements}

## Affected Files
- {file1}: {change description}
- {file2}: {change description} 

## Implementation Steps
1. {step} → @{agent-name}
2. {step} → @{agent-name}

## Testing
- {test approach}

## Completion Criteria
- [ ] Implementation complete
- [ ] Tests pass
- [ ] Build succeeds
```

---

## Phase 2: Execution

### 2.1 Agent Selection

Per @CLAUDE.md delegation rules:

| Task Type | Agent |
|-----------|-------|
| React/UI components | **ui-engineer-enhanced** |
| TypeScript backend/core | **backend-typescript-architect** |
| Pattern discovery | **codebase-explorer** |
| Deep analysis | **explore** |
| Debugging issues | **ultrathink-debugger** |
| Validation/review | **task-completion-validator** |

### 2.2 Delegate Implementation

For each step in the plan, delegate to the assigned agent with:
- Feature context and requirements
- Patterns discovered by codebase-explorer
- Files to modify/create
- Reference to @CLAUDE.md architecture patterns

Execute steps that can be parallelized together.

### 2.3 Incremental Verification

After each major step:
- `pnpm typecheck` - No TypeScript errors
- `pnpm test` - Tests pass
- `pnpm lint` - Lint clean

### 2.4 Commit Progress

After logical units of work, commit with:
```
feat({scope}): {description}

Refs: quick-feature/{feature-slug}
```

---

## Phase 3: Quality Gates

Before completion, all gates must pass:

| Gate | Command |
|------|---------|
| Type checking | `pnpm typecheck` |
| Tests | `pnpm test` |
| Lint | `pnpm lint` |
| Build | `pnpm build` |

If any fail, fix before proceeding.

---

## Phase 4: Completion

### 4.1 Update Quick Plan

Edit `.claude/progress/quick-features/{feature-slug}.md`:
- Set `status: completed` and `completed_at: {ISO date}`
- Check all completion criteria boxes

### 4.2 Update Request Log (if applicable)

If input was a REQ ID, use **meatycapture-capture** skill to update status to `done`.

### 4.3 Capture Issues (if any)

If issues arose during implementation that warrant tracking, use **meatycapture-capture** skill to capture as new bug/enhancement item with context about the feature that surfaced the issue.

---

## Output Summary

```
Quick Feature Complete: {feature title}

Plan: .claude/progress/quick-features/{feature-slug}.md
Files Changed: {count}
Tests: {pass/fail count}
Commits: {commit count}

{If from REQ: "Request log item {REQ-ID} marked as done"}
```

---

## Error Recovery

If blocked:
1. Document blocker in quick plan under `## Blockers`
2. Do NOT mark as completed
3. Report to user with clear next steps needed
4. Use **meatycapture-capture** skill to capture blocker if it warrants tracking

---

## Skills & Agents Referenced

| Resource | Type | Purpose |
|----------|------|---------|
| `meatycapture-capture` | Skill | Read/update request log items, capture new issues |
| `codebase-explorer` | Agent | Pattern discovery before implementation |
| `ui-engineer-enhanced` | Agent | React/UI component implementation |
| `backend-typescript-architect` | Agent | Core/backend TypeScript implementation |
| `ultrathink-debugger` | Agent | Debug issues that arise |
| `task-completion-validator` | Agent | Validate implementation completeness |
| `explore` | Agent | Deep analysis when needed |

---

Follow @CLAUDE.md delegation rules. Never write implementation code directly.
