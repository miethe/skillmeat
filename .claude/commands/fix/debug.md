---
description: Debug and remediate bugs with Opus delegation, artifact tracking, and request-log integration
argument-hint: "<bug-description> [--severity=critical|high|medium|low] [--component=name]"
allowed-tools: Read, Grep, Glob, Edit, MultiEdit, Write,
  Bash(git:*), Bash(gh:*), Bash(pnpm:*), Bash(npm:*), Bash(pytest:*),
  Bash(uv:*), Bash(pre-commit:*), Bash(ls:*), Bash(find:*), Bash(rm:*),
  Task, mcp__claude-in-chrome__*
model: claude-opus-4-5-20251101
---

# Debug and Remediation

Analyze and fix: `$ARGUMENTS`

## Prime Directive

**You are Opus. Tokens are expensive. Orchestrate; do not implement directly.**

All implementation work MUST be delegated to specialized subagents. You focus on:
- Reasoning and root cause analysis
- Planning remediation strategy
- Orchestrating subagent execution
- Validating fixes and updating tracking

## Git Context

!`git status --porcelain`

!`git log --oneline -5`

!`git branch --show-current`

## Phase 1: Discovery

### 1.1 Search for Related Issues

Check for existing request logs or bug tracking:

```bash
# Search project request logs if meatycapture available
meatycapture log search "$ARGUMENTS" . --json 2>/dev/null || echo "meatycapture not configured"
```

Check existing bug-fixes documentation:

```bash
ls -la .claude/worknotes/fixes/ 2>/dev/null || echo "No fixes directory"
```

### 1.2 Gather Context

Delegate investigation to codebase-explorer:

```
Task("codebase-explorer", "Find files and patterns related to: $ARGUMENTS
Focus on:
- Error messages and stack traces
- Related component files
- Test files that might validate the fix
- Configuration that might affect behavior")
```

### 1.3 Deep Analysis (if needed)

For complex bugs, delegate deep analysis:

```
Task("ultrathink-debugger", "Analyze bug: $ARGUMENTS
Provide:
- Root cause hypothesis
- Affected code paths
- Potential fix strategies
- Risk assessment for each approach")
```

## Phase 2: Planning

### 2.1 Create Request Log Entry

If this is a new bug not already tracked, use `mc-quick.sh` for token-efficient capture:

```bash
# Quick capture with mc-quick.sh (~50 tokens vs ~200+ for JSON)
MC_STATUS=in-progress MC_PRIORITY=[SEVERITY] mc-quick.sh bug [DOMAIN] [COMPONENT] \
  "[BUG_TITLE]" \
  "Root cause: [IDENTIFIED_ROOT_CAUSE]" \
  "Fix strategy: [PLANNED_APPROACH]"

# Example:
MC_STATUS=in-progress MC_PRIORITY=high mc-quick.sh bug api auth \
  "Fix session timeout" \
  "Root cause: Token expiry set to 5min" \
  "Fix strategy: Extend TTL to 24 hours"
```

**Script location**: `.claude/skills/meatycapture-capture/scripts/mc-quick.sh`

### 2.2 Define Remediation Plan

Create a focused remediation plan:

| Step | Action | Agent | Validation |
|------|--------|-------|------------|
| 1 | [Specific change] | [agent-name] | [How to verify] |
| 2 | [Specific change] | [agent-name] | [How to verify] |
| 3 | [Test update] | [agent-name] | [Test command] |

## Phase 3: Implementation

### Agent Selection

| Bug Type | Primary Agent |
|----------|--------------|
| React/UI | ui-engineer-enhanced |
| TypeScript backend | backend-typescript-architect |
| Python backend | python-backend-engineer |
| Database/schema | database-engineer |
| Build/config | devops-engineer |
| Tests | test-engineer |

### 3.1 Execute Remediation

Delegate implementation to appropriate agent(s):

```
Task("[SELECTED_AGENT]", "Fix [BUG_DESCRIPTION]:

Location: [FILE_PATH]
Root Cause: [ROOT_CAUSE]
Required Changes:
- [CHANGE_1]
- [CHANGE_2]

Constraints:
- Do NOT create validation reports or summaries
- Do NOT add temporary test scripts
- Commit changes with clear message: fix([component]): [description]")
```

### 3.2 Cascading Issues

If new issues appear during implementation:

1. Assess severity and impact
2. If blocking: continue to remediate in same session
3. If non-blocking: create separate request log entry for later

## Phase 4: Validation

### Validation Strategy

Validate via direct code review and existing test infrastructure:

1. **Read/Grep**: Verify code changes are correct
2. **Existing tests**: Run `pnpm test` or `pytest`
3. **Type checking**: Run `pnpm typecheck` or `mypy`
4. **Frontend**: Use chrome-devtools skill if needed
5. **API**: Use existing API test infrastructure

### Strict Rules

- **DO NOT** create one-time validation scripts
- **DO NOT** create VALIDATION_SUMMARY.txt or CODE_VERIFICATION_REPORT.md
- **DO NOT** commit screenshots, reports, or artifacts outside bug-fixes doc
- **DO** delete any temporary artifacts before final commit
- **DO** use existing test infrastructure for validation

### 4.1 Run Validation

```bash
# TypeScript projects
pnpm test && pnpm typecheck && pnpm lint

# Python projects
pytest && mypy .

# Check for untracked artifacts to clean up
git status --porcelain | grep "^??"
```

### 4.2 Cleanup

Before final commit, ensure NO temporary artifacts remain:

```bash
# Remove any validation artifacts that were created
rm -f VALIDATION_SUMMARY.txt CODE_VERIFICATION_REPORT.md
rm -f *.screenshot.png debug-*.json
git status --porcelain | grep "^??" | awk '{print $2}' | xargs -I {} sh -c 'file={} && [[ "$file" =~ \.(txt|md|png|json)$ ]] && rm -f "$file"'
```

## Phase 5: Documentation

### 5.1 Update Bug-Fixes Document + Request Log

**Use `update-bug-docs.py`** to automate both updates in one command:

```bash
# After commit: updates bug-fixes doc + marks request-log item done
.claude/scripts/update-bug-docs.py --commits <sha> --req-log REQ-YYYYMMDD-skillmeat

# Preview without editing
.claude/scripts/update-bug-docs.py --commits <sha> --req-log REQ-YYYYMMDD-skillmeat --dry-run

# Multiple commits
.claude/scripts/update-bug-docs.py --commits sha1,sha2,sha3 --req-log REQ-YYYYMMDD-skillmeat
```

**Script location**: `.claude/scripts/update-bug-docs.py`
**Full spec**: `.claude/specs/script-usage/bug-automation-scripts.md`

### 5.2 Manual Updates (Fallback)

Only if script unavailable:

```bash
mkdir -p .claude/worknotes/fixes
meatycapture log item update [DOC_PATH] [ITEM_ID] --status done
meatycapture log note add [DOC_PATH] [ITEM_ID] -c "Fixed in commit [HASH]. Root cause: [BRIEF]"
```

## Phase 6: Commit

### 6.1 Final Verification

```bash
# Ensure clean state
git status

# Verify no temporary artifacts
git diff --cached --name-only | grep -E "\.(screenshot|report|summary)\." && echo "WARNING: Temporary artifacts staged"
```

### 6.2 Commit Changes

Commit with clear, focused message:

```bash
git add -A
git commit -m "fix([component]): [brief description]

[Detailed explanation if needed]

Root cause: [brief explanation]
Resolves: [issue reference if applicable]"
```

## Quality Checklist

- [ ] Root cause identified and documented
- [ ] Fix implemented via subagent delegation
- [ ] Existing tests pass
- [ ] No temporary artifacts committed
- [ ] Bug-fixes document updated
- [ ] Request log updated (if applicable)
- [ ] Clear commit message with component scope

## Agent Reference

| Task | Agent | Model |
|------|-------|-------|
| Find patterns | codebase-explorer | Haiku |
| Deep analysis | ultrathink-debugger | Sonnet |
| React/UI | ui-engineer-enhanced | Sonnet |
| TypeScript | backend-typescript-architect | Sonnet |
| Python | python-backend-engineer | Sonnet |
| Database | database-engineer | Sonnet |
| Validation | task-completion-validator | Sonnet |

## Chrome DevTools (Frontend Debugging)

For frontend bugs, use the chrome-devtools skill:

```
/chrome-devtools screenshot   # Capture current state
/chrome-devtools console      # Check for JS errors
/chrome-devtools network      # Inspect API calls
/chrome-devtools elements     # Debug DOM state
```

## Escalation

If the bug cannot be resolved:

1. Document findings in bug-fixes document with status: BLOCKED
2. Create detailed request log entry with blockers
3. Note specific questions or dependencies needed
4. Suggest next steps for future investigation
