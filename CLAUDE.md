# CLAUDE.md

SkillMeat: Personal collection manager for Claude Code artifacts with web UI

## Prime Directives

| Directive | Implementation |
|-----------|---------------|
| **Delegate everything** | Opus reasons & orchestrates; subagents implement |
| Token efficient | Symbol system, codebase-explorer |
| Rapid iteration | PRD → code → deploy fast |
| No over-architecture | YAGNI until proven |

### Opus Delegation Principle

**You are Opus. Tokens are expensive. You orchestrate; subagents execute.**

- ✗ **Never** write code directly (Read/Edit/Write for implementation)
- ✗ **Never** do token-heavy exploration yourself
- ✗ **Never** read full implementation files before delegating
- ✓ **Always** delegate implementation to specialized subagents
- ✓ **Always** use codebase-explorer for pattern discovery
- ✓ **Focus** on reasoning, analysis, planning, and orchestration

**Delegation Pattern**:

```text
1. Analyze task → identify what needs to change
2. Delegate exploration → codebase-explorer finds files/patterns
3. Read progress YAML → get assigned_to and batch strategy
4. Delegate implementation → use Task() from Orchestration Quick Reference
5. Update progress → artifact-tracker marks tasks complete
6. Commit → only direct action Opus takes
```

**When you catch yourself about to edit a file**: STOP. Delegate instead.

**File context for subagents**: Provide file paths, not file contents. Subagents read files themselves. Only read files directly when planning decisions require understanding current state.

## Documentation Policy

**Reference**: `.claude/specs/doc-policy-spec.md`

**Allowed**:

- `/docs/` → User/dev/architecture docs (with frontmatter)
- `.claude/progress/[prd]/` → ONE per phase (YAML+Markdown hybrid)
- `.claude/worknotes/[prd]/` → ONE context.md per PRD (agent worknotes)
- `.claude/worknotes/fixes/` → ONE per month
- `.claude/worknotes/observations/` → ONE per month

**README Updates**: When changing features, CLI commands, screenshots, or version → rebuild README. See `.claude/specs/script-usage/readme-build.md`

**Prohibited**:

- Debugging summaries → git commit
- Multiple progress per phase
- Daily/weekly reports
- Session notes as docs

---

## Command-Skill Bindings

**Commands do not automatically load skills.** When executing `/dev:*` or other workflow commands, you MUST explicitly invoke required skills using the `Skill` tool before proceeding.

### Required Skill Invocations

| Command                    | Required Skills                  | Invoke First                                               |
| -------------------------- | -------------------------------- | ---------------------------------------------------------- |
| `/dev:execute-phase`       | dev-execution, artifact-tracking | `Skill("dev-execution")` then `Skill("artifact-tracking")` |
| `/dev:quick-feature`       | dev-execution                    | `Skill("dev-execution")`                                   |
| `/dev:implement-story`     | dev-execution, artifact-tracking | `Skill("dev-execution")` then `Skill("artifact-tracking")` |
| `/dev:complete-user-story` | dev-execution, artifact-tracking | `Skill("dev-execution")` then `Skill("artifact-tracking")` |
| `/dev:create-feature`      | dev-execution                    | `Skill("dev-execution")`                                   |
| `/plan:*`                  | planning                         | `Skill("planning")`                                        |
| `/analyze:symbols:*`       | symbols                          | CLI scripts (automatic via commands)                       |
| `/mc`                      | (self-contained)                 | No additional skills needed                                |

### Symbol-First Exploration

**Pattern discovery uses symbols automatically** via `codebase-explorer` agent delegation.

When exploring code patterns before implementation:
1. Delegate to `Task("codebase-explorer", "Find [pattern]")` - uses symbols internally
2. Direct queries: `jq '.symbols[] | select(.layer == "service")' ai/symbols-api.json`
3. Token savings: ~150 tokens (symbols) vs 5-15K tokens (file reads)

### Enforcement Protocol

1. **First action** after receiving a listed command: Call `Skill()` for each required skill
2. **Do not proceed** with any other actions until skills are loaded
3. **Skill content** provides execution guidance that the command references

### Why This Matters

Commands are prompt templates. Skills are knowledge repositories. Without explicit invocation:

- Referenced file paths like `[.claude/skills/dev-execution/modes/phase-execution.md]` are NOT auto-read
- Skill guidance is NOT automatically loaded into context
- The agent operates without the intended workflow knowledge

---

## Agent Delegation

**Mandatory**: All implementation work MUST be delegated. Opus orchestrates only.

### Model Selection (Post-Refactor)

| Model | Budget | Use When |
|-------|--------|----------|
| **Opus 4.6** | $15/$75/M | Orchestration, deep reasoning, architectural decisions |
| **Sonnet 4.6** | $3/$15/M | Implementation, review, moderate reasoning (DEFAULT for subagents) |
| **Haiku 4.5** | $0.80/$4/M | Mechanical search, extraction, simple queries |

**Default: Sonnet 4.6** — Sonnet is now near-Opus for coding (79.6% SWE-bench). Use Opus only for deep reasoning.

### Multi-Model Integration

External models are available as **opt-in** supplements to Claude. Claude Opus remains the sole orchestrator; external models are execution targets.

**Configuration**: `.claude/config/multi-model.toml` — controls model routing, effort policies, checkpoints, and asset pipeline.

| Capability | Model | Trigger |
|-----------|-------|---------|
| Plan review (second opinion) | GPT-5.3-Codex | Opt-in checkpoint |
| PR cross-validation | Gemini 3.1 Pro / Flash | Opt-in checkpoint |
| Debug escalation | GPT-5.3-Codex | After 2+ failed Claude cycles |
| Web research | Gemini 3.1 Pro | Current web info needed |
| Image generation | Nano Banana Pro | Task requires image output |
| SVG/animation (complex) | Gemini 3.1 Pro | Multi-element visual tasks |
| Video generation | Sora 2 | Explicit request |
| Privacy-sensitive | Local LLM | Configured + requested |

**Effort Policy**: Thinking/reasoning is a budgeted policy layer. Claude uses adaptive thinking by default; escalate to extended only when **blocked with concrete artifacts**. Codex uses graduated reasoning (`none`/`low`/`medium`/`high`/`xhigh`). `budget_tokens` is deprecated on Opus 4.6.

**Disagreement Protocol**: When models conflict, tests decide — not model preference. CI is the neutral arbiter. See `.claude/skills/dev-execution/orchestration/disagreement-protocol.md`.

**Key references**:
- Spec: `.claude/specs/multi-model-usage-spec.md`
- Config: `.claude/config/multi-model.toml`
- Model selection: `.claude/skills/dev-execution/orchestration/model-selection-guide.md`
- Checkpoints: `.claude/skills/dev-execution/orchestration/cross-model-review.md`
- Escalation: `.claude/skills/dev-execution/orchestration/escalation-protocols.md`
- Creative workflows: `.claude/skills/dev-execution/orchestration/creative-workflows.md`

### Implementation Agents

| Agent | Model | Skills | Permission | Memory |
|-------|-------|--------|------------|--------|
| python-backend-engineer | sonnet | skillmeat-cli, artifact-tracking | acceptEdits | project |
| ui-engineer-enhanced | sonnet | frontend-design, aesthetic, artifact-tracking | acceptEdits | project |
| ui-engineer | sonnet | frontend-design, aesthetic | acceptEdits | - |
| frontend-developer | sonnet | frontend-design | acceptEdits | - |
| frontend-architect | sonnet | - | acceptEdits | - |
| backend-architect | sonnet | - | acceptEdits | - |
| backend-typescript-architect | sonnet | - | acceptEdits | - |
| nextjs-architecture-expert | sonnet | - | acceptEdits | - |
| data-layer-expert | sonnet | - | acceptEdits | - |
| refactoring-expert | sonnet | - | acceptEdits | - |
| openapi-expert | sonnet | artifact-tracking | acceptEdits | - |
| ai-engineer | sonnet | - | acceptEdits | - |
| documentation-complex | sonnet | - | acceptEdits | - |

### Exploration & Analysis

| Agent | Model | Skills | Permission | Memory |
|-------|-------|--------|------------|--------|
| codebase-explorer | haiku | symbols | plan | project |
| search-specialist | haiku | - | plan | - |
| symbols-engineer | haiku | - | plan | - |
| task-decomposition-expert | haiku | - | plan | - |
| implementation-planner | haiku | planning | plan | - |

### Review & Validation

| Agent | Model | Permission | disallowedTools | Memory |
|-------|-------|------------|-----------------|--------|
| senior-code-reviewer | sonnet | plan | Write, Edit, MultiEdit, Bash | project |
| task-completion-validator | sonnet | plan | Write, Edit, MultiEdit | project |
| karen | opus | plan | Write, Edit, MultiEdit | - |
| api-librarian | sonnet | plan | Write, Edit, MultiEdit | - |
| telemetry-auditor | sonnet | plan | Write, Edit, MultiEdit | - |
| code-reviewer | - | plan | Write, Edit, MultiEdit, Bash | - |
| a11y-sheriff | - | plan | - | - |

### Orchestration (Opus Only)

| Agent | Model | Skills | Permission | Memory |
|-------|-------|--------|------------|--------|
| lead-architect | opus | planning | default | - |
| lead-pm | opus | planning, artifact-tracking, meatycapture-capture | default | project |
| spike-writer | opus | planning | default | - |
| ultrathink-debugger | opus | - | acceptEdits | project |
| documentation-planner | opus | - | plan | - |

### Documentation

| Agent | Model | Permission |
|-------|-------|------------|
| documentation-writer | haiku | acceptEdits |
| documentation-expert | haiku | acceptEdits |
| api-documenter | haiku | acceptEdits |
| changelog-generator | haiku | acceptEdits |
| technical-writer | haiku | - |

### PM & Planning

| Agent | Model | Skills |
|-------|-------|--------|
| prd-writer | sonnet | planning |
| feature-planner | sonnet | planning, artifact-tracking |

### Agent Teams (Experimental)

For multi-component features, use Agent Teams instead of sequential subagents:

| Team Template | Lead | Teammates | Use When |
|---------------|------|-----------|----------|
| feature-team | Opus orchestrator | python-backend-engineer, ui-engineer-enhanced, task-completion-validator | Full feature (API + frontend + tests) |
| debug-team | ultrathink-debugger | codebase-explorer, python-backend-engineer | Complex debugging with parallel investigation |
| refactor-team | Opus orchestrator | python-backend-engineer, ui-engineer-enhanced, code-reviewer | Cross-layer refactoring |

**Use Subagents for**: Single-file fixes, batch ops, exploration, docs, review, quick features (< 3 files).
**Use Agent Teams for**: Full features (5+ files), cross-cutting refactors, multi-system integration, phase execution with 3+ batches.

### Background Execution

Subagents can run in the background, allowing parallel work:

| Parameter | Purpose |
|-----------|---------|
| `run_in_background: true` | Launch agent without blocking |
| `TaskOutput(task_id)` | Retrieve results (blocking by default) |
| `TaskOutput(task_id, block: false)` | Check status without waiting |

**When to Use Background Execution**:

- Large batch parallelization (5+ independent tasks)
- When Opus needs to do work between launching and collecting results
- Long-running tasks where Opus can productively continue

**When NOT to Use**:

- Small batches (2-3 tasks) - standard parallel is simpler
- When results are immediately needed
- When tasks have dependencies requiring sequential execution

### Context Budget Discipline

**Invariants**: `.claude/rules/context-budget.md` (auto-loaded every session)

**Budget**: ~52K baseline leaves ~148K for work. Budget ~25-30K per phase.

**Key rules**: No `TaskOutput()` for file-writing agents (verify on disk instead). Task prompts < 500 words (paths, not contents). Don't explore for work you'll delegate. Always scope Glob with `path`.

**Verification pattern for background agents**: See `dev-execution/orchestration/batch-delegation.md`.

### Example Delegation

```text
# Bug: API returns 422 error

1. DELEGATE exploration:
   Task("codebase-explorer", "Find ListItemCreate schema and where it's used")
   # codebase-explorer is pre-configured as haiku with plan permissionMode

2. DELEGATE fix:
   Task("python-backend-engineer", "Fix ListItemCreate schema - make list_id optional.
        File: services/api/app/schemas/list_item.py
        Change: list_id from required to optional (int | None = None)
        Reason: list_id comes from URL path, not request body")
   # python-backend-engineer is pre-configured as sonnet with acceptEdits

3. COMMIT (Opus does this directly):
   git add ... && git commit
```

---

## Orchestration-Driven Development

**Reference**: Use `artifact-tracking` skill for progress tracking.

### File Locations

| Type | Location | Limit |
|------|----------|-------|
| Progress | `.claude/progress/[prd]/phase-N-progress.md` | ONE per phase |
| Context | `.claude/worknotes/[prd]/context.md` | ONE per PRD |

### CLI-First Updates

**Use CLI scripts for status updates** (0 agent tokens):

```bash
# Single task
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/prd/phase-1-progress.md -t TASK-1.1 -s completed

# Batch update
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f FILE --updates "TASK-1.1:completed,TASK-1.2:completed"
```

**Use agents only for**: Creating files, updates with context/notes, recording blockers.

### Plan Status Management

**Manage PRD/implementation plan status fields** (draft → approved → in-progress → completed):

```bash
python .claude/skills/artifact-tracking/scripts/manage-plan-status.py \
  [--read FILE | --file FILE --status STATUS | --query --status STATUS --type TYPE]
```

**Use `artifact-tracking` skill for detailed guidance.**

### Orchestration Workflow

1. **Read YAML frontmatter** → get `parallelization.batch_N` and `tasks[].assigned_to`
2. **Execute batch in parallel** → single message with multiple Task() calls
3. **Update via CLI** → `update-batch.py` after tasks complete
4. **Validate** → `artifact-validator` before marking phase complete

### Commands

| Command | Purpose |
|---------|---------|
| `/dev:execute-phase N` | Execute phase N with orchestration |
| `Skill("artifact-tracking")` | Load skill for complex operations |

### Token Efficiency

| Operation | Traditional | CLI-First | Savings |
|-----------|-------------|-----------|---------|
| Status update | 25KB | 50 bytes | 99.8% |
| Batch update (5) | 50KB | 100 bytes | 99.8% |
| Query blockers | 75KB | 3KB | 96% |

Full format spec: `.claude/skills/artifact-tracking/SKILL.md`

---

## Development Tracking

Track bugs/enhancements via MeatyCapture request-logs.

**Structure**: Docs contain Items. Bugs aggregate daily ("Bug Log - YYYY-MM-DD"); other types create one doc per request.

**Quick capture** (~50 tokens): `mc-quick.sh TYPE DOMAIN SUBDOMAIN "Title" "Problem" "Goal"`

**Full guidance**: `.claude/context/development-tracking-playbook.md` — read when capturing bugs, using `/mc` or generally meatycapture, or working with request-logs.

---

## Memory System (Project Knowledge)

SkillMeat's memory system stores project-level development knowledge (patterns, decisions, gotchas, constraints) in the DB cache.

**In-session** (preferred): Capture learnings immediately when discovered during work.
**Pre-task**: Load relevant memories before substantial implementation work.
**Post-task** (fallback): Extract from session logs if in-session capture wasn't done.

| Operation | Command |
|-----------|---------|
| Quick capture (CLI) | `skillmeat memory item create --project <id> --type <type> --content "..." --confidence 0.85 --status candidate --anchor "skillmeat/core/services/foo.py:code:42-58" --provenance-branch "<branch>" --provenance-commit "<sha>" --provenance-agent-type "<agent>" --provenance-model "<model>"` |
| Quick capture (API) | `curl -s "http://localhost:8080/api/v1/memory-items?project_id=<BASE64_ID>" -X POST -H "Content-Type: application/json" -d '{"type":"<type>","content":"...","confidence":0.85,"status":"candidate","anchors":["path:type"]}'` |
| Search memories | `skillmeat memory search "<query>" --project <id>` |
| Preview context pack | `skillmeat memory pack preview --project <id> --budget 4000` |
| Extract from logs | `skillmeat memory extract preview --project <id> --run-log <path>` |
| Triage candidates | `skillmeat memory item list --project <id> --status candidate` |

**Valid memory types**: `decision`, `constraint`, `gotcha`, `style_rule`, `learning`
**Capture triggers**: Root cause discoveries, API gotchas, decision rationale, pattern findings.
**Anchor format**: `path:type` or `path:type:start-end` where `type` is one of `code|test|doc|config|plan`.
**API note**: CLI `memory item create` may return 422 — use API fallback with base64 project ID. See `.claude/rules/memory.md`.
**Full guidance**: Use `skillmeat-cli` skill (route 6: Memory capture/consumption flows).
**Safety**: All memories start as `candidate` — never auto-promote.

---

## Architecture Overview

**Full-Stack Web Application** (v0.3.0-beta)

```
skillmeat/
├── cli.py              # Click-based CLI (collection, web commands)
├── core/               # Business logic (artifact, deployment, sync, discovery, analytics)
│   └── github_client.py # Centralized GitHub API client wrapper
├── cache/              # SQLAlchemy ORM, repositories, Alembic migrations
├── api/                # FastAPI backend → See skillmeat/api/CLAUDE.md
├── web/                # Next.js 15 frontend → See skillmeat/web/CLAUDE.md
├── sources/            # GitHub, local artifact sources
├── storage/            # Manifest, lockfile, snapshot, deployment managers
├── marketplace/        # Marketplace brokers, compliance, publishing
└── observability/      # Logging, metrics, tracing
```

### Data Flow Principles

Dual-stack: **filesystem** (CLI source of truth) + **DB cache** (web source of truth). Six canonical principles govern all data flow:

1. **DB Cache = Web's Source of Truth** -- Frontend reads from DB-backed API endpoints, never filesystem directly (exception: individual file content)
2. **Filesystem = CLI's Source of Truth** -- CLI reads/writes filesystem directly; DB cache is a derived view
3. **Write-Through for Web Mutations** -- Write FS first, sync to DB via `refresh_single_artifact_cache()`, invalidate frontend caches
4. **Cache Refresh = Sync Mechanism** -- Full sync at startup, targeted per mutation, manual via `POST /cache/refresh`
5. **Standardized Stale Times** -- 5min browsing, 30sec interactive/monitoring, 2min deployments
6. **Mutations Invalidate Related Caches** -- Every mutation must invalidate all affected query keys per the invalidation graph

**Detailed reference** (stale time table, invalidation graph, flow diagrams):
**Read**: `.claude/context/key-context/data-flow-patterns.md`

**Collection-Based Architecture** (Active):

```
~/.skillmeat/collection/    # User's personal collection
  ├── artifacts/            # All artifact types
  ├── manifest.toml         # Collection metadata
  └── snapshots/            # Version history

Projects (.claude/ directories)
  └── deployed artifacts
```

**Artifact Types Supported**:
- Skills (full support)
- Commands, Agents, MCP servers, Hooks (partial support)
- Composites/Plugins (multi-artifact packages with relational model, smart import, deduplication)

---

## Development Commands

### Setup

| Command | Purpose |
|---------|---------|
| `pip install -e ".[dev]"` | Install in dev mode |
| `uv tool install --editable .` | Install with uv (recommended) |

### CLI (Collection Management)

| Command | Purpose |
|---------|---------|
| `skillmeat init` | Initialize collection/project |
| `skillmeat add <source>` | Add artifact from GitHub/local |
| `skillmeat deploy <artifact>` | Deploy to project |
| `skillmeat sync` | Sync collection with upstream |
| `skillmeat list` | List artifacts |
| `skillmeat search <query>` | Search artifacts |

### Web Interface

| Command | Purpose |
|---------|---------|
| `skillmeat web dev` | Start dev servers (API + Next.js) |
| `skillmeat web dev --api-only` | Start only API server |
| `skillmeat web dev --web-only` | Start only Next.js |
| `skillmeat web build` | Build for production |
| `skillmeat web start` | Start production servers |
| `skillmeat web doctor` | Diagnose environment issues |

### Testing

| Command | Purpose |
|---------|---------|
| `pytest -v --cov=skillmeat` | Run all tests with coverage |
| `pytest tests/test_cli_core.py` | Run specific test file |
| `pytest -k test_name` | Run specific test |

### Code Quality

| Command | Purpose |
|---------|---------|
| `black skillmeat` | Format code (required) |
| `flake8 skillmeat --select=E9,F63,F7,F82` | Lint errors only |
| `mypy skillmeat --ignore-missing-imports` | Type checking |

---

## Key Cross-Cutting Patterns

### Version Compatibility (Python)

```python
# Required: Python 3.9+
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib
```

### Artifact Source Format

```
username/repo/path/to/artifact[@version]

# Examples:
anthropics/skills/canvas-design@latest
anthropics/skills/document-skills/docx@v1.2.0
user/repo/nested/path/skill@abc1234
```

**Version Options**: `@latest`, `@1.2.0` (tag), `@abc1234` (SHA), or omitted (defaults to latest)

### Manifest Structure (TOML)

```toml
[tool.skillmeat]
version = "1.0.0"

[[artifacts]]
name = "canvas"
type = "skill"
source = "anthropics/skills/canvas-design"
version = "latest"
scope = "user"  # "user" (global) or "local" (project)
aliases = ["design"]
```

### Lock File Structure (TOML)

```toml
[lock]
version = "1.0.0"

[lock.entries.canvas]
source = "anthropics/skills/canvas-design"
version_spec = "latest"
resolved_sha = "abc123def456..."
resolved_version = "v2.1.0"
locked_at = "2024-11-29T10:00:00Z"
```

### Security Patterns

- **Atomic Operations**: Use temp directories → atomic move
- **Validation**: All artifacts validated before installation
- **Permissions**: Warning before installation (skip with `--dangerously-skip-permissions`)
- **Rate Limiting**: GitHub token recommended for private repos

### Error Handling

```python
# CLI: Exit with sys.exit(1) on failure
# API: Raise HTTPException with status code
# Core: Raise domain-specific exceptions
```

### GitHub Client

**File**: `core/github_client.py`

All GitHub API operations must use the centralized `GitHubClient` wrapper:

```python
from skillmeat.core.github_client import get_github_client, GitHubClient

# Get singleton client (automatic token resolution)
client = get_github_client()

# Common operations
metadata = client.get_repo_metadata("owner/repo")
content = client.get_file_content("owner/repo", "path/to/file")
tree = client.get_repo_tree("owner/repo", ref="main")
sha = client.resolve_version("owner/repo", "latest")
rate_limit = client.get_rate_limit()

# Token priority (automatic resolution)
# 1. ConfigManager (settings.github-token)
# 2. SKILLMEAT_GITHUB_TOKEN env var
# 3. GITHUB_TOKEN env var
# 4. Unauthenticated (60 req/hr fallback)
```

**Exception Handling**:

```python
from skillmeat.core.github_client import (
    GitHubClientError,
    GitHubRateLimitError,
    GitHubAuthError,
    GitHubNotFoundError,
)

try:
    content = client.get_file_content("owner/repo", "path")
except GitHubAuthError:
    # Handle invalid/missing token
except GitHubRateLimitError as e:
    # Check e.reset_at for rate limit reset time
except GitHubNotFoundError:
    # Handle missing repo/file
except GitHubClientError:
    # Catch-all for other GitHub errors
```

Never use PyGithub directly; always go through the wrapper.

---

## Domain-Specific Documentation

**Backend/API**: `skillmeat/api/CLAUDE.md`
- FastAPI server setup and configuration
- API routers (23 endpoints) and schemas
- Middleware and dependency injection patterns
- Database integration (via `skillmeat/cache/`)

**Frontend/Web**: `skillmeat/web/CLAUDE.md`
- Next.js 15 app structure
- React component patterns
- Radix UI + shadcn
- API client usage
- Testing strategies

---

## Progressive Disclosure Context

**Context loading ladder**:
1. Runtime truth (`skillmeat/api/openapi.json`, `skillmeat/web/hooks/index.ts`, `ai/symbols-*.json`)
2. Entry `CLAUDE.md` for scope + invariants
3. Key-context playbooks for task routing
4. Deep context docs only when unresolved
5. Historical plans/reports only for rationale (verify behavior from runtime truth)

**Global rules** (minimal):
- `.claude/rules/debugging.md` - Universal symbol-first debugging pointer

**Key Context** (read when working in domain):
- `.claude/context/key-context/context-loading-playbook.md` - Trigger matrix for what to read first
- `.claude/context/key-context/api-contract-source-of-truth.md` - OpenAPI-first contract workflow
- `.claude/context/key-context/hook-selection-and-deprecations.md` - Hook selection + deprecation routing
- `.claude/context/key-context/fe-be-type-sync-playbook.md` - Type/model sync workflow
- `.claude/context/key-context/symbols-query-playbook.md` - Symbols-first discovery recipes
- `.claude/context/key-context/codebase-map-query-playbook.md` - Graph artifact usage policy
- `.claude/context/key-context/notebooklm-usage-policy.md` - NotebookLM verification policy
- `.claude/context/key-context/deprecation-and-sunset-registry.md` - Active deprecations + sunset dates
- `.claude/context/key-context/layered-context-governance.md` - Layer policy and token budgets
- `.claude/context/key-context/data-flow-patterns.md` - Stale times, cache invalidation graph, write-through patterns
- `.claude/context/key-context/marketplace-import-flows.md` - Import endpoints, source display, DB sync invariants
- `.claude/context/key-context/debugging-patterns.md` - Bug categories, delegation patterns
- `.claude/context/key-context/router-patterns.md` - Full FastAPI examples
- `.claude/context/key-context/component-patterns.md` - React/shadcn patterns
- `.claude/context/key-context/nextjs-patterns.md` - App Router patterns
- `.claude/context/key-context/testing-patterns.md` - Jest/Playwright templates
- `.claude/context/key-context/agent-teams-patterns.md` - Agent Teams vs subagents decision framework

**Reference Context** (load as needed):
- `.claude/context/api-endpoint-mapping.md` - Full API reference
- `.claude/context/symbol-usage-guide.md` - Symbol query patterns
- `.claude/context/stub-patterns.md` - Frontend stubs catalog

**Staleness Hook**: `.claude/hooks/check-context-staleness.sh` (pre-commit warning)

---

## Important Notes

- **Scopes**: `user` scope (~/.claude/skills/user/) is global; `local` scope (./.claude/skills/) is per-project
- **Lock Files**: Always update when modifying manifests for reproducibility
- **GitHub Rate Limits**: Use token: `skillmeat config set github-token <token>`
- **Rich Output**: Use Rich library (ASCII-compatible, no Unicode box-drawing)
- **CI/CD**: Tests run on Python 3.9-3.12, Ubuntu/Windows/macOS
