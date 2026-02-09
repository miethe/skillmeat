# Memory Rule (Global)

Invariant:

1. **Pre-task**: Check for relevant memories before substantial implementation:
   `skillmeat memory search "<domain keywords>" --project <id> --json`

2. **During task** (preferred): Capture reusable learnings immediately when discovered:
   `skillmeat memory item create --project <id> --type <type> --content "..." --confidence 0.85 --status candidate --anchor "path:type:start-end" --provenance-branch "<branch>" --provenance-commit "<sha>" --provenance-agent-type "<agent>" --provenance-model "<model>"`

   Include one or more `--anchor` flags for files you touched or where the learning was discovered.
   Anchor format:
   - `path:type`
   - `path:type:start-end`
   Valid `type` values: `code`, `test`, `doc`, `config`, `plan`

   Anchor type heuristic:
   - `test`: paths under `tests/` or basenames like `test_*.py`
   - `doc`: markdown under `docs/` or `project_plans/`
   - `plan`: markdown under `.claude/progress/` or `.claude/worknotes/`
   - `config`: `.toml`, `.yaml`, `.yml`, `.json`, `.ini`, `.cfg`, `.env*`
   - `code`: everything else

   Trigger capture when encountering:
   - Root cause discoveries ("bug was caused by X")
   - API/framework gotchas ("function X requires Y")
   - Decision rationale ("chose A over B because")
   - Pattern discoveries ("codebase uses X for Y")
   - File-specific learnings ("this fix depends on X in Y.py")

3. **Post-task** (fallback): If in-session capture wasn't done, extract from session logs:
   `skillmeat memory extract preview --project <id> --run-log <path>`

4. Never auto-promote extracted memories — keep as `candidate` until human review.

5. For full memory workflows, use `skillmeat-cli` skill (Memory & Context handling policy).
