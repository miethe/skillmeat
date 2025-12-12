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

## Documentation Policy

**Reference**: `.claude/specs/doc-policy-spec.md`

**Allowed**:

- `/docs/` → User/dev/architecture docs (with frontmatter)
- `.claude/progress/[prd]/` → ONE per phase (YAML+Markdown hybrid)
- `.claude/worknotes/[prd]/` → ONE context.md per PRD (agent worknotes)
- `.claude/worknotes/fixes/` → ONE per month
- `.claude/worknotes/observations/` → ONE per month

**Prohibited**:

- Debugging summaries → git commit
- Multiple progress per phase
- Daily/weekly reports
- Session notes as docs

---

## Agent Delegation

**Mandatory**: All implementation work MUST be delegated. Opus orchestrates only.

### Exploration & Analysis

| Task | Agent | Model | Use When |
|------|-------|-------|----------|
| Find files/patterns | codebase-explorer | Haiku | Quick discovery |
| Deep analysis | explore | Haiku | Full context needed |
| Debug investigation | ultrathink-debugger | Sonnet | Complex bugs |
| Progress tracking | artifact-tracker | Haiku | Create/update progress |
| Query status | artifact-query | Haiku | Find blockers, pending tasks |

### Implementation

| Task | Agent | Model | Use When |
|------|-------|-------|----------|
| Backend Python | python-backend-engineer | Sonnet | FastAPI, SQLAlchemy, Alembic |
| Frontend React | ui-engineer | Sonnet | Components, hooks, pages |
| Full-stack TS | backend-typescript-architect | Sonnet | Node/TS backend |
| UI components | ui-engineer-enhanced | Sonnet | Design system, Radix |

### Documentation

| Task | Agent | Model | Use When |
|------|-------|-------|----------|
| Most docs (90%) | documentation-writer | Haiku | READMEs, API docs, guides |
| Complex docs | documentation-complex | Sonnet | Multi-system integration |
| AI artifacts | ai-artifacts-engineer | Sonnet | Skills, agents, commands |

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

1. DELEGATE exploration:
   Task("codebase-explorer", "Find ListItemCreate schema and where it's used")

2. DELEGATE fix:
   Task("python-backend-engineer", "Fix ListItemCreate schema - make list_id optional.
        File: services/api/app/schemas/list_item.py
        Change: list_id from required to optional (int | None = None)
        Reason: list_id comes from URL path, not request body")

3. COMMIT (Opus does this directly):
   git add ... && git commit
```

---

## Orchestration-Driven Development

**Reference**: Use `artifact-tracking` skill for progress tracking of implementation plans.

### Progress & Context Files

| File Type | Location | Purpose |
|-----------|----------|---------|
| Progress | `.claude/progress/[prd]/phase-N-progress.md` | ONE per phase, tracks tasks |
| Context | `.claude/worknotes/[prd]/context.md` | ONE per PRD, agent worknotes |

### Progress File Orchestration

Progress files include YAML frontmatter optimized for Opus-level orchestration:

```yaml
tasks:
  - id: "TASK-1.1"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]  # REQUIRED
    dependencies: []                        # REQUIRED

parallelization:
  batch_1: ["TASK-1.1", "TASK-1.2"]  # Run in parallel
  batch_2: ["TASK-2.1"]              # Sequential after batch_1
```

**Key Fields** (REQUIRED for every task):
- `assigned_to`: Array of agents to delegate to
- `dependencies`: Array of task IDs that must complete first

### Orchestration Quick Reference

Every progress file includes a markdown section with ready-to-copy Task() commands:

```markdown
## Orchestration Quick Reference

**Batch 1** (Parallel):
- TASK-1.1 → `ui-engineer-enhanced` (2h)
- TASK-1.2 → `python-pro` (1h)

### Task Delegation Commands
Task("ui-engineer-enhanced", "TASK-1.1: Create component...")
Task("python-pro", "TASK-1.2: Add API endpoint...")
```

**Execute batches**: Parallel tasks in one message, sequential batches wait for completion.

### Commands

| Command | Purpose |
|---------|---------|
| `/dev:execute-phase N` | Execute phase N with orchestration |
| `skill: artifact-tracking` | Create/update/query progress files |

### Token Efficiency

| Operation | Traditional | With Orchestration | Savings |
|-----------|-------------|-------------------|---------|
| Read task list | 25KB | 2KB (YAML only) | 92% |
| Query blockers | 75KB | 3KB | 96% |
| Session handoff | 150KB | 5KB | 97% |

---

## Architecture Overview

**Full-Stack Web Application** (v0.3.0-beta)

```
skillmeat/
├── cli.py              # Click-based CLI (collection, web commands)
├── core/               # Business logic (artifact, deployment, sync, analytics)
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

## Important Notes

- **Scopes**: `user` scope (~/.claude/skills/user/) is global; `local` scope (./.claude/skills/) is per-project
- **Lock Files**: Always update when modifying manifests for reproducibility
- **GitHub Rate Limits**: Use token: `skillmeat config set github-token <token>`
- **Rich Output**: Use Rich library (ASCII-compatible, no Unicode box-drawing)
- **CI/CD**: Tests run on Python 3.9-3.12, Ubuntu/Windows/macOS
