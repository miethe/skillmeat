# Memory Rule (Global)

Invariant:

1. **Pre-task**: Check for relevant memories before substantial implementation:
   `skillmeat memory search "<domain keywords>" --project <id> --json`

2. **During task** (preferred): Capture reusable learnings immediately when discovered:
   `skillmeat memory item create --project <id> --type <type> --content "..." --confidence 0.85 --status candidate`

   Trigger capture when encountering:
   - Root cause discoveries ("bug was caused by X")
   - API/framework gotchas ("function X requires Y")
   - Decision rationale ("chose A over B because")
   - Pattern discoveries ("codebase uses X for Y")

3. **Post-task** (fallback): If in-session capture wasn't done, extract from session logs:
   `skillmeat memory extract preview --project <id> --run-log <path>`

4. Never auto-promote extracted memories — keep as `candidate` until human review.

5. For full memory workflows, use `skillmeat-cli` skill (Memory & Context handling policy).
