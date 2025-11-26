# Debug and Remediation Stub

Analyze the attached list of bugs. Create a remediation plan with designs, then implement it. You must use subagents to perform all tasks, only delegating tasks. You are Opus, so tokens are expensive; use them wisely to optimize for reasoning, with all token-heavy work being delegated. Commit often.

- **Validation Strategy**: Validate code changes via direct code review (Read/Grep tools). DO NOT create test scripts, automation, or browser screenshots. For web app fixes, inspect the code changes directly to verify correct implementation.

- **NO test automation or validation scripts**: Do not create `.js`, `.py`, or any scripts for validation in the codebase. Do not use chrome-devtools to automate browser tests. Do not generate screenshots or test reports.
- **NO validation reports**: Do not create VALIDATION_SUMMARY.txt, CODE_VERIFICATION_REPORT.md, or any other reports/summaries outside the bug-fixes doc.
- If new issues appear during implementation, continue to analyze and remediate them. If builds fail with ITERATE=TRUE, continue iterating until resolved.

## Documentation Requirements

**Update the monthly bug-fixes document ONLY** (create if doesn't exist):
- File: `docs/project_plans/bugs/bug-fixes-{YYYY}-{MM}.md`
- Example: `bug-fixes-2025-11.md`

Add one section per bug using this template:

```markdown
### {BUG DESCRIPTIVE TITLE}

**Issue**: {Explanation of the bug}
- **Location**: `filepath:line-number` or component name
- **Root Cause**: {Brief explanation}
- **Fix**: {Brief explanation of changes}
- **Commit(s)**: {Commit hash(es)}
- **Status**: RESOLVED
```

## Strict Rules

- ❌ Do NOT create validation scripts or test automation
- ❌ Do NOT create screenshots, reports, or summaries outside bug-fixes doc
- ❌ Do NOT create any files in `docs/screenshots/` unless explicitly required by the bug itself
- ❌ Do NOT add markdown files, PNG files, or JSON reports unless they are part of the actual bug fix
- ✅ DO delete all untracked artifacts (screenshots, reports, scripts) before final commit
- ✅ DO update only the monthly bug-fixes document for all validation notes
- ✅ DO commit frequently with clear, focused commit messages
