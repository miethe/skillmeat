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

### Model Selection Philosophy

**Default: Opus** — Use Opus for subagents unless criteria below indicate otherwise.

| Model | Use When | Examples |
|-------|----------|----------|
| **Opus** (default) | Complex reasoning, architecture decisions, multi-file changes, nuanced judgment | Feature implementation, refactoring, debugging, cross-cutting concerns |
| **Sonnet** | Moderate complexity, well-scoped tasks, cost-sensitive batches | Single-file fixes, straightforward CRUD, bulk operations |
| **Haiku** | Simple/mechanical tasks, high-volume ops, quick discovery | File search, status queries, simple doc updates, progress tracking |

### Exploration & Analysis

| Task | Agent | Model | Rationale |
|------|-------|-------|-----------|
| Find files/patterns | codebase-explorer | Haiku | Mechanical search, high volume |
| Deep analysis | explore | Opus | Complex reasoning needed |
| Debug investigation | ultrathink-debugger | Opus | Root cause analysis requires depth |
| Progress tracking | artifact-tracker | Haiku | Structured updates, low complexity |
| Query status | artifact-query | Haiku | Simple data retrieval |

### Implementation

| Task | Agent | Model | Rationale |
|------|-------|-------|-----------|
| Backend Python | python-backend-engineer | Opus | Architecture awareness, multi-layer changes |
| Frontend React | ui-engineer | Opus | Component design, state management |
| Full-stack TS | backend-typescript-architect | Opus | System-wide considerations |
| UI components | ui-engineer-enhanced | Opus | Design system coherence |
| Simple bug fixes | python-backend-engineer | Sonnet | Well-scoped, single-file changes |
| Bulk/batch ops | (any) | Sonnet | Cost efficiency for repetitive tasks |

### Documentation

| Task | Agent | Model | Rationale |
|------|-------|-------|-----------|
| Simple docs | documentation-writer | Haiku | Structured, template-based |
| Feature docs | documentation-writer | Sonnet | Moderate analysis needed |
| Complex docs | documentation-complex | Opus | Multi-system synthesis |
| AI artifacts | ai-artifacts-engineer | Opus | Prompt engineering requires nuance |

### Model Override Guidelines

**Downgrade to Sonnet** when:
- Task is well-defined with clear boundaries
- Single file or limited scope
- Following established patterns (no design decisions)
- Running 3+ similar tasks in parallel (cost optimization)

**Downgrade to Haiku** when:
- Task is purely mechanical (search, copy, format)
- High-volume operations (10+ items)
- Simple status updates or queries
- Template-based output

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

### Example Delegation

```text
# Bug: API returns 422 error

1. DELEGATE exploration (Haiku - mechanical search):
   Task("codebase-explorer", "Find ListItemCreate schema and where it's used", model="haiku")

2. DELEGATE fix (Opus default - requires understanding context):
   Task("python-backend-engineer", "Fix ListItemCreate schema - make list_id optional.
        File: services/api/app/schemas/list_item.py
        Change: list_id from required to optional (int | None = None)
        Reason: list_id comes from URL path, not request body")

3. COMMIT (Opus does this directly):
   git add ... && git commit

# Feature: Add 5 similar CRUD endpoints (use Sonnet for batch efficiency)
Task("python-backend-engineer", "Add GET /widgets endpoint", model="sonnet")
Task("python-backend-engineer", "Add POST /widgets endpoint", model="sonnet")
# ... parallel batch
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

**Full guidance**: `.claude/rules/development-tracking.md` — read when capturing bugs, using `/mc`, or working with request-logs.

---

## Architecture Overview

**Full-Stack Web Application** (v0.3.0-beta)

```
skillmeat/
├── cli.py              # Click-based CLI (collection, web commands)
├── core/               # Business logic (artifact, deployment, sync, analytics)
│   └── github_client.py # Centralized GitHub API client wrapper
├── api/                # FastAPI backend → See skillmeat/api/CLAUDE.md
├── web/                # Next.js 15 frontend → See skillmeat/web/CLAUDE.md
├── sources/            # GitHub, local artifact sources
├── storage/            # Manifest, lockfile, snapshot managers
├── marketplace/        # Claude marketplace integration
└── observability/      # Logging, monitoring
```

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
- Commands, Agents, MCP servers, Hooks (planned)

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
- FastAPI server setup
- SQLAlchemy models
- Alembic migrations
- API routers and schemas
- Middleware patterns

**Frontend/Web**: `skillmeat/web/CLAUDE.md`
- Next.js 15 app structure
- React component patterns
- Radix UI + shadcn
- API client usage
- Testing strategies

---

## Progressive Disclosure Context

**Rules** (always loaded into context):
- `.claude/rules/debugging.md` - Symbol-first debugging (30 lines)
- `.claude/rules/development-tracking.md` - MeatyCapture workflow (34 lines)
- `.claude/rules/api/routers.md` - Router layer contract (44 lines)
- `.claude/rules/web/` - Component, page, testing conventions (~130 lines)

**Key Context** (read when working in domain):
- `.claude/context/key-context/debugging-patterns.md` - Bug categories, delegation patterns
- `.claude/context/key-context/router-patterns.md` - Full FastAPI examples
- `.claude/context/key-context/component-patterns.md` - React/shadcn patterns
- `.claude/context/key-context/nextjs-patterns.md` - App Router patterns
- `.claude/context/key-context/testing-patterns.md` - Jest/Playwright templates

**Reference Context** (load as needed):
- `.claude/context/api-endpoint-mapping.md` - Full API reference
- `.claude/context/symbol-usage-guide.md` - Symbol query patterns
- `.claude/context/stub-patterns.md` - Frontend stubs catalog
- `.claude/context/key-context/schemas.md` - Schema definitions (76KB)
- `.claude/context/key-context/hooks.md` - React hooks reference (71KB)

**Staleness Hook**: `.claude/hooks/check-context-staleness.sh` (pre-commit warning)

---

## Important Notes

- **Scopes**: `user` scope (~/.claude/skills/user/) is global; `local` scope (./.claude/skills/) is per-project
- **Lock Files**: Always update when modifying manifests for reproducibility
- **GitHub Rate Limits**: Use token: `skillmeat config set github-token <token>`
- **Rich Output**: Use Rich library (ASCII-compatible, no Unicode box-drawing)
- **CI/CD**: Tests run on Python 3.9-3.12, Ubuntu/Windows/macOS
