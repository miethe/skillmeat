# Debug and Remediation Stub

Analyze the attached list of bugs. Create a remediation plan with designs, then implement it. You must use subagents to perform all tasks, only delegating tasks. You are Opus, so tokens are expensive; use them wisely to optimize for reasoning, with all token-heavy work being delegated. Commit often.

- Validate every fix where applicable with both unit tests (if available) and E2E tests. All web app fixes should be validated via chrome-devtools.
- If new issues appear during testing of your fix, then proceed to analyze and remediate them as well. If builds fail, and you've been so instructed with ITERATE=TRUE, then continue to iterate by analyzing and remediating the build failures as well until it passes with recursive instructions from here.
- You should add a very brief note per bug fix in the monthly bug fixes doc, creating if it doesn't exist yet per the format below:
`bug-fixes-{current_month}-{current_year}.md` - validating current date via tool call, ie `bash: `date +%Y-%m-%d``.

  ```markdown
    ### {BUG DESCRIPTIVE TITLE}

    **Issue**: {Explanation of the bug.}
    - **Date**: {Must validate current date per above.}
    - **Location**: `{filepath:line number or component name}`
    - **Root Cause**: {Brief explanation of the root cause.}
    - **Fix**: {Brief explanation of the fix.}
    - **Tests**: {Brief explanation of tests added or updated to validate the fix.}
    - **Commit**: {Commit id}
    ```

- NO other docs should be created (or must be removed before commit) except the update to the above-noted monthly bug fixes doc, unless explicitly called for in the bug fix itself. You may update existing user/developer docs when relevant from the fix.