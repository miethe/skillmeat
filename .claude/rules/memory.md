# Memory Rule (Global)

Invariant:

1. **Pre-task**: Check for relevant memories before substantial implementation:
   `skillmeat memory search "<domain keywords>" --project <id> --json`

2. **During task** (preferred): Capture reusable learnings immediately when discovered.

   **Via CLI** (may fail on `memory item create` — see API fallback):
   `skillmeat memory item create --project <id> --type <type> --content "..." --confidence 0.85 --status candidate --anchor "path:type:start-end" --provenance-branch "<branch>" --provenance-commit "<sha>" --provenance-agent-type "<agent>" --provenance-model "<model>"`

   **Via API** (proven reliable — use when CLI returns 422/400):
   ```bash
   curl -s "http://localhost:8080/api/v1/memory-items?project_id=<BASE64_PROJECT_ID>" \
     -X POST -H "Content-Type: application/json" -d '{
     "type": "<type>", "content": "...", "confidence": 0.85, "status": "candidate",
     "anchors": ["path/to/file:code", "path/to/other:test:100-150"]
   }'
   ```

   **Valid memory types**: `decision`, `constraint`, `gotcha`, `style_rule`, `learning`

   **SkillMeat project ID**: `L1VzZXJzL21pZXRoZS9kZXYvaG9tZWxhYi9kZXZlbG9wbWVudC9za2lsbG1lYXQ=`

   Include one or more `--anchor` flags (CLI) or `"anchors"` array (API) for files you touched.
   Anchor format (always strings): `path:type` or `path:type:start-end`
   Valid anchor `type` values: `code`, `test`, `doc`, `config`, `plan`

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
   For API fallback details, see `skillmeat-cli/workflows/memory-context-workflow.md` § "API Fallback Procedure".
