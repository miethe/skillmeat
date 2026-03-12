# Agentic README Skill Plan: `managing-readmes`

## Vision & Scope

### What This Skill Does

`managing-readmes` is a comprehensive agentic workflow skill for initializing, building, maintaining, and validating README.md files using a modular Handlebars-based build system. It extracts and generalizes SkillMeat's battle-tested `.github/readme/` pipeline into a reusable pattern applicable to any project.

The skill covers the full README lifecycle:
- **Bootstrap**: Scaffold the build system for a new or existing project
- **Screenshot Planning**: Generate structured visual asset specs
- **Content Strategy**: Audience analysis and section architecture
- **Build & Rebuild**: Assemble README from partials + data
- **Validate**: Link checking, screenshot existence, freshness
- **Workflow Integration**: CI, hooks, trigger wiring

### Target Users and Use Cases

| User | Scenario |
|------|----------|
| OSS maintainer | Initialize modular README system for a new project |
| Developer | Rebuild README after adding features |
| Agent workflow | Auto-update README as part of version bump |
| Team | Validate README before PR merge |
| Any AI agent | Screenshot planning for web app or CLI tool |

### Cross-Tool Compatibility

**Primary**: Claude Code — full workflow support via Skill invocation, MCP tool integration, hook wiring.

**Secondary**: Codex, Gemini, and other agents can use the scripts directly (Node.js, no Claude-specific APIs). The build system itself is portable; only the agentic workflow layer (Route 6) and MCP screenshot capture are Claude Code-specific.

**Deployment**: Project-level (`.claude/skills/managing-readmes/`). Extracted from SkillMeat and deployed per-project via SkillMeat catalog.

---

## Skill Architecture

### Directory Structure

```
managing-readmes/
├── SKILL.md                            # Core instructions, route index, <500 lines
├── bootstrapping-readme-system.md      # Route 1: scaffold workflow details
├── screenshot-planning-guide.md        # Route 2: visual asset spec generation
├── content-strategy-guide.md          # Route 3: audience analysis, section design (self-contained, includes project-type templates + style guide)
├── build-and-rebuild-workflow.md       # Route 4: build commands, section-update patterns
├── validation-workflow.md             # Route 5: link/screenshot/freshness checks
├── ci-and-hook-integration.md          # Route 6: CI workflow, pre-commit hooks, triggers
├── templates/
│   ├── README.hbs                      # Generalized main template (project-type variants)
│   ├── feature-grid.hbs
│   ├── screenshot-table.hbs
│   ├── command-list.hbs
│   └── hero-section.hbs               # NEW: extracted from hero.md pattern
├── data-schemas/
│   ├── features.schema.json            # Canonical features.json schema
│   ├── screenshots.schema.json         # Canonical screenshots.json schema
│   └── version.schema.json            # Canonical version.json schema
└── scripts/
    ├── build-readme.js                 # Generalized from SkillMeat (CJS → ESM)
    ├── validate-links.js               # Direct extract, parametric root
    ├── check-screenshots.js            # Direct extract, parametric root
    ├── sync-features.js                # Direct extract, parametric root
    ├── update-version.js               # Direct extract, parametric root
    ├── bootstrap.js                    # NEW: scaffold directory + seed data
    ├── analyze-project.js              # NEW: inspect project to seed features.json
    └── generate-screenshot-spec.js     # NEW: output structured screenshot plan JSON
```

### SKILL.md Outline (Progressive Disclosure)

```
---
name: managing-readmes
description: [trigger-focused, see §Description below]
---

# Managing READMEs

## When to Use This Skill
[Route selection table]

## Route 1: Bootstrap
[3-5 line summary → see ./bootstrapping-readme-system.md]

## Route 2: Screenshot Planning
[3-5 line summary → see ./screenshot-planning-guide.md]

## Route 3: Content Strategy
[3-5 line summary → see ./content-strategy-guide.md]

## Route 4: Build & Rebuild
[Quick reference commands — inline, no delegation needed]

## Route 5: Validate
[Quick reference commands — inline, no delegation needed]

## Route 6: Workflow Integration
[3-5 line summary → see ./ci-and-hook-integration.md]

## Data File Reference
[Schema field quick-ref, key constraints]

## Handlebars Helper Reference
[7 built-in helpers, usage examples]
```

### Description (Invocation-Critical)

```yaml
description: >
  Use this skill when creating, rebuilding, or maintaining a project README using
  a modular Handlebars build system. Covers bootstrapping the .github/readme/
  scaffold for any project, planning screenshot and GIF visual assets, crafting
  content strategy (audience analysis, section structure, success metrics),
  assembling or rebuilding README.md from partials and data files, validating
  links and screenshots, and wiring CI workflows or pre-commit hooks for
  README freshness. Also use when a version bump, feature addition, or
  screenshot update requires regenerating README content. Supports CLI tools,
  web apps, libraries, and SaaS products.
```

(~720 chars, well under 1024 limit, keyword-dense.)

---

## Workflow Routes

### Route 1: Bootstrap — Init README System for New Project

**Trigger phrases**: "set up README build system", "initialize modular README", "scaffold README for new project"

**Workflow**:
1. Run `node scripts/bootstrap.js --project-type [cli|web|library|saas] --output .github/readme`
   - Creates full directory tree: `scripts/`, `templates/`, `partials/`, `data/`
   - Seeds `package.json` with `{ "dependencies": { "handlebars": "^4.7" } }`
   - Seeds `features.json`, `screenshots.json`, `version.json` with project-type defaults
2. Run `node scripts/analyze-project.js` to auto-populate features from:
   - `package.json` commands/scripts
   - CLI help output (`--help` scraping)
   - Existing docs or CLAUDE.md
3. Prompt agent to review and edit seeded data files
4. Run `node scripts/build-readme.js --dry-run` to preview
5. Write `README.md`

**Agent delegation**: `python-backend-engineer` or direct agent execution — bootstrap is purely scripted.

**Files**: `./bootstrapping-readme-system.md` (project-type template matrix, seeding heuristics)

---

### Route 2: Screenshot Planning — Generate Visual Asset Specs

**Trigger phrases**: "plan screenshots", "create screenshot spec", "what screenshots do I need", "GIF recording plan"

**Workflow**:
1. Agent analyzes project to enumerate capturable surfaces:
   - Web UI: read route files (`app/`, `pages/`) or `openapi.json`
   - CLI: run `--help` recursively, parse commands
   - API: parse `openapi.json` for key endpoints
2. Run `node scripts/generate-screenshot-spec.js` to produce structured output
3. Output a `screenshots.json`-compatible spec with:
   - `status: "pending"` for all items
   - `notes` fields with capture instructions
   - `tool` recommendation per item (Chrome DevTools MCP vs asciinema)
   - `sequence` arrays for GIF recordings
4. Write to `data/screenshots.json` (or dry-run preview)

**Capture tool — Chrome MCP primary** (future `--platform` flag for alternatives):

| Asset Type | Tool | MCP Tools Used |
|-----------|------|----------------|
| Web UI screenshots | `mcp__claude-in-chrome__computer` | `action=screenshot` with viewport sizing via `mcp__claude-in-chrome__resize_window` |
| Web GIF workflows | `mcp__claude-in-chrome__gif_creator` | `start_recording` → actions → `stop_recording` → `export` |
| CLI terminal output | `mcp__claude-in-chrome__computer` (terminal tab) | Screenshot of terminal, or future `--platform asciinema` flag |
| CLI GIF demos | `mcp__claude-in-chrome__gif_creator` (terminal tab) | Record terminal session |
| Page text extraction | `mcp__claude-in-chrome__get_page_text` | For verifying page state before capture |

**GIF recording spec format** (output per workflow):
```json
{
  "id": "quickstart-workflow",
  "file": "docs/screenshots/gifs/quickstart-workflow.gif",
  "tool": "mcp__claude-in-chrome__gif_creator",
  "config": {
    "showClickIndicators": true,
    "showActionLabels": true,
    "showProgressBar": true,
    "quality": 10
  },
  "sequence": [
    { "action": "navigate", "url": "/", "label": "Dashboard overview", "hold": 2000 },
    { "action": "click", "target": "Collection link", "label": "Browse collection", "hold": 2000 },
    { "action": "screenshot", "hold": 3000 }
  ]
}
```

**Files**: `./screenshot-planning-guide.md` (Chrome MCP capture workflows, GIF sequence spec format, viewport presets, sample data requirements, future platform flag spec)

---

### Route 3: Content Strategy — Craft README Architecture

**Trigger phrases**: "README content strategy", "structure my README", "audience analysis", "what sections should my README have"

**Workflow**:
1. Gather project context:
   - Project type (CLI, web app, library, SaaS)
   - Primary audience (developers, end users, Claude Code users)
   - Key differentiators vs. alternatives
   - Existing README (if any) — audit strengths/weaknesses
2. Apply audience-to-section mapping (table in `./content-strategy-guide.md`)
3. Define section priority order (above-the-fold budget: 3 decisions in <30s)
4. Define success metrics (time-to-understand, scroll depth, visual asset count)
5. Output a content plan document with:
   - Recommended section order and rationale
   - Copy direction for hero tagline and value prop
   - Visual hierarchy notes (what goes in hero, feature grid, etc.)
   - Prose guidance (project-type templates, section checklists, style guide — all self-contained)

**Self-contained**: All content strategy guidance is inlined in `./content-strategy-guide.md` — no dependency on external skills. Includes project-type templates (OSS, personal, internal, config), section checklists, and prose style guide (extracted from `crafting-effective-readmes` patterns).

**Files**: `./content-strategy-guide.md` (audience matrix, section priority tables, success metric templates)

---

### Route 4: Build & Rebuild — Assemble/Update README

**Trigger phrases**: "rebuild README", "regenerate README", "update README", "build README from templates"

**Quick reference** (inline in SKILL.md — no delegation needed):

```bash
cd .github/readme

# Full rebuild
node scripts/build-readme.js

# Preview without writing
node scripts/build-readme.js --dry-run

# Override version
node scripts/build-readme.js --version 1.2.0

# Update data then rebuild
# 1. Edit: data/features.json  → add/modify features
# 2. Edit: data/screenshots.json → add screenshots, update status
# 3. Edit: partials/<section>.md → edit section prose
# 4. node scripts/build-readme.js
```

**When to rebuild**:

| Change | Action Required |
|--------|----------------|
| New feature | Edit `features.json`, rebuild |
| Screenshot added | Edit `screenshots.json` status to `captured`, rebuild |
| Version bump | Run `node scripts/update-version.js --version X.Y.Z`, rebuild |
| Section content | Edit relevant `partials/*.md`, rebuild |
| Structure change | Edit `templates/README.hbs`, rebuild |

**Files**: `./build-and-rebuild-workflow.md` (section-only build patterns, template authoring guide, Handlebars helper reference)

---

### Route 5: Validate — Links, Screenshots, Freshness

**Trigger phrases**: "validate README", "check README links", "are screenshots up to date", "README health check"

**Quick reference** (inline in SKILL.md):

```bash
cd .github/readme

# Validate internal links (always run after rebuild)
node scripts/validate-links.js

# Validate external URLs too (slower)
node scripts/validate-links.js --check-external

# Check all screenshots exist
node scripts/check-screenshots.js

# Check only README-category screenshots
node scripts/check-screenshots.js --category readme

# Skip pending screenshots (CI mode)
node scripts/check-screenshots.js --required-only

# Validate features.json schema
node scripts/sync-features.js --check-refs --verbose

# Full pre-commit suite
node scripts/validate-links.js && node scripts/check-screenshots.js --required-only
```

**Exit codes**: All scripts exit 0 on pass, 1 on failure — CI-compatible.

**Files**: `./validation-workflow.md` (freshness heuristics, staleness detection patterns, triage guide for common failures)

---

### Route 6: Workflow Integration — CI, Hooks, Triggers

**Trigger phrases**: "README CI check", "pre-commit README validation", "auto-update README on version bump", "hook README to releases"

**Workflow patterns**:

1. **Pre-commit hook**: Warn when README is stale vs. `features.json`
2. **CI workflow**: Run full validation suite on PRs that touch docs or feature data
3. **Version bump trigger**: `update-version.js` → `build-readme.js` in release script
4. **Feature addition trigger**: Post-feature-merge, agent rebuilds README and opens PR

**Claude Code hook** (`.claude/hooks/check-readme-staleness.sh`):
```bash
# Warn if features.json newer than README.md
FEATURES=".github/readme/data/features.json"
README="README.md"
if [ "$FEATURES" -nt "$README" ]; then
  echo "WARNING: features.json is newer than README.md — consider rebuilding"
fi
```

**GitHub Actions snippet** (seeded by bootstrap):
```yaml
- name: Validate README
  run: |
    cd .github/readme && npm ci
    node scripts/validate-links.js
    node scripts/check-screenshots.js --required-only
```

**Files**: `./ci-and-hook-integration.md` (full GitHub Actions workflow, pre-commit hook template, version bump script integration patterns)

---

## Claude Code-Specific Features

### Invocation Triggers

| User Says | Route |
|-----------|-------|
| "set up README build" / "scaffold README system" | Route 1: Bootstrap |
| "plan screenshots for my app" / "what screenshots do I need" | Route 2: Screenshot Planning |
| "help me structure my README" / "README content strategy" | Route 3: Content Strategy |
| "rebuild README" / "regenerate README" / "update README" | Route 4: Build |
| "validate README" / "check README links" / "README broken" | Route 5: Validate |
| "README CI" / "auto-update README" / "README hook" | Route 6: Workflow Integration |

### Agent Delegation Patterns

| Task | Delegate To | Notes |
|------|-------------|-------|
| Scaffold bootstrap | `python-backend-engineer` | Run `bootstrap.js` + seed data |
| Analyze project for features | `codebase-explorer` (haiku) | Enumerate commands, routes, endpoints |
| Content strategy drafting | Direct (Sonnet) | Inline reasoning task, no file reads needed |
| Screenshot planning | Direct (Sonnet) + `generate-screenshot-spec.js` | Output structured JSON |
| CI workflow authoring | `python-backend-engineer` | Write YAML, wire hooks |
| Web screenshot capture | Direct (Claude Code Chrome MCP) | `mcp__claude-in-chrome__computer` + `resize_window` |
| Web GIF recording | Direct (Claude Code Chrome MCP) | `mcp__claude-in-chrome__gif_creator` workflow |
| CLI screenshot capture | Direct (Chrome MCP on terminal tab) | Future: `--platform asciinema` flag |
| Validation | Direct (Node.js scripts) | Zero-delegation, just run scripts |

### MCP Tool Usage (Claude in Chrome)

Screenshot and GIF capture uses `mcp__claude-in-chrome__*` tools directly:

**Screenshot capture workflow**:
```
1. mcp__claude-in-chrome__tabs_context_mcp          # Get current tabs
2. mcp__claude-in-chrome__tabs_create_mcp            # Open new tab (or reuse)
3. mcp__claude-in-chrome__resize_window              # Set viewport (1280x720)
4. mcp__claude-in-chrome__navigate url=<target>      # Navigate to page
5. mcp__claude-in-chrome__computer action=screenshot  # Capture
6. Move screenshot to screenshots.json `file` path
7. Update screenshots.json: status → "captured", add captured date
```

**GIF recording workflow**:
```
1. mcp__claude-in-chrome__navigate url=<start-page>
2. mcp__claude-in-chrome__gif_creator action=start_recording
3. mcp__claude-in-chrome__computer action=screenshot   # Extra frames for smooth start
4. [Execute sequence steps: navigate, click, type, wait]
5. mcp__claude-in-chrome__computer action=screenshot   # Extra frames for smooth end
6. mcp__claude-in-chrome__gif_creator action=stop_recording
7. mcp__claude-in-chrome__gif_creator action=export download=true filename="<id>.gif"
   config: { showClickIndicators: true, showActionLabels: true, quality: 10 }
```

**Page verification before capture**:
- Use `mcp__claude-in-chrome__get_page_text` to verify correct page state
- Use `mcp__claude-in-chrome__find` to locate specific elements before clicking
- Use `mcp__claude-in-chrome__read_console_messages` to check for errors

**Important**: Never trigger JavaScript alerts/confirms — they block the extension. Use `mcp__claude-in-chrome__javascript_tool` to dismiss any existing dialogs before capture.

### Hook Integration

Pre-commit hook for README staleness detection lives at `.claude/hooks/check-readme-staleness.sh`. Bootstrap script seeds this file. Wire it in `settings.json`:

```json
{
  "hooks": {
    "PreCommit": [".claude/hooks/check-readme-staleness.sh"]
  }
}
```

---

## Cross-Tool Compatibility

### What Works Everywhere (Scripts + Templates)

All scripts in `managing-readmes/scripts/` are plain Node.js (ESM, no Claude-specific APIs):

| Component | Codex | Gemini | Cursor | Notes |
|-----------|-------|--------|--------|-------|
| `build-readme.js` | Yes | Yes | Yes | Pure Node.js + Handlebars |
| `validate-links.js` | Yes | Yes | Yes | Node.js + fs/https |
| `check-screenshots.js` | Yes | Yes | Yes | Node.js + fs |
| `sync-features.js` | Yes | Yes | Yes | Node.js + fs |
| `update-version.js` | Yes | Yes | Yes | Node.js + fs |
| `bootstrap.js` | Yes | Yes | Yes | Node.js scaffolding |
| Handlebars templates | Yes | Yes | Yes | Standard Handlebars |
| Data JSON schemas | Yes | Yes | Yes | Plain JSON |

### What's Claude Code-Specific

| Feature | Alternative for Other Tools |
|---------|----------------------------|
| Skill invocation (`Skill("managing-readmes")`) | Manual: read SKILL.md, follow route |
| Chrome MCP screenshot/GIF capture (`mcp__claude-in-chrome__*`) | Future `--platform` flag: Puppeteer, Playwright, asciinema |
| Pre-commit hooks via `settings.json` | Standard git hooks or husky |
| Agent delegation patterns | Manual subprocess calls |
| `analyze-project.js` context read | Run script directly, review output |

### Graceful Degradation

For non-Claude-Code environments: all routes reduce to running the Node.js scripts directly. The `bootstrap.js` script is the entry point. The supporting markdown files (`bootstrapping-readme-system.md`, etc.) serve as human-readable workflow guides when the agentic layer isn't available.

---

## Extractable Assets from SkillMeat

### Scripts — Direct Extracts (with Generalization)

| Source | Target | Generalization Required |
|--------|--------|------------------------|
| `.github/readme/scripts/build-readme.js` | `scripts/build-readme.js` | CJS → ESM; `PROJECT_ROOT` parameterized via `--root` flag |
| `.github/readme/scripts/validate-links.js` | `scripts/validate-links.js` | `PROJECT_ROOT` parameterized; default to `process.cwd()` |
| `.github/readme/scripts/check-screenshots.js` | `scripts/check-screenshots.js` | `PROJECT_ROOT` parameterized |
| `.github/readme/scripts/sync-features.js` | `scripts/sync-features.js` | Minor: remove SkillMeat-specific stats fields |
| `.github/readme/scripts/update-version.js` | `scripts/update-version.js` | None — already generic |

**Key change for all scripts**: Replace hardcoded `path.join(SCRIPT_DIR, '..', '..', '..')` PROJECT_ROOT with a `--root` CLI flag that defaults to `process.cwd()`. This makes scripts portable without relying on assumed directory depth.

### Templates — Generalize

| Source | Target | Generalization Required |
|--------|--------|------------------------|
| `.github/readme/templates/README.hbs` | `templates/README.hbs` | Replace SkillMeat-specific sections with generic placeholders; add project-type variants |
| `.github/readme/templates/feature-grid.hbs` | `templates/feature-grid.hbs` | None — already generic |
| `.github/readme/templates/screenshot-table.hbs` | `templates/screenshot-table.hbs` | None — already generic |
| `.github/readme/templates/command-list.hbs` | `templates/command-list.hbs` | None — already generic |
| `.github/readme/partials/hero.md` | Inline in `templates/README.hbs` | Parameterize project name, tagline, logo path |

### Data Schemas — Standardize

Extract formal JSON Schema files from the implicit structure in SkillMeat's data files:

| Schema | Key Fields to Formalize |
|--------|------------------------|
| `features.schema.json` | `categories[].id`, `categories[].features[].id/name/description/since/cliCommand/webPage/screenshot/highlight` |
| `screenshots.schema.json` | `screenshots[].id/file/alt/width/height/category/page/features/captured/status/notes`, `gifs[].id/file/tool/sequence` |
| `version.schema.json` | `current`, `releaseDate`, `previousVersions[]`, `upcoming` |

### Handlebars Helpers — Document and Generalize

The 8 registered helpers in `build-readme.js` are already generic:

| Helper | Purpose | Portable? |
|--------|---------|-----------|
| `formatDate` | Locale date string | Yes |
| `isoDate` | Current ISO timestamp | Yes |
| `filter` | Array filter by key/value | Yes |
| `eq` | Equality conditional | Yes |
| `count` | Array length | Yes |
| `join` | Array join with separator | Yes |
| `isOdd` | Alternating rows | Yes |
| `highlightedFeatures` | Flatten highlighted features across categories | Yes |
| `screenshotsByCategory` | Filter screenshots by category | Yes |
| `totalFeatures` | Count all features | Yes |
| `hasCliCommands` | Boolean: any feature has CLI command | Yes |
| `cliCommands` | Comma-joined CLI commands list | Yes |

All 12 helpers are project-agnostic — copy verbatim.

### Patterns to Document

From SkillMeat's planning docs, these reusable patterns should be captured in skill supporting files:

| Pattern | Source | Documents In |
|---------|--------|-------------|
| Audience analysis framework (primary/secondary with needs matrix) | `readme-improvement-plan.md` §Audience | `content-strategy-guide.md` |
| Section priority structure (above-the-fold budget) | `readme-improvement-plan.md` §Structure | `content-strategy-guide.md` |
| Screenshot categories (readme/features/cli/gifs) | `screenshots.json` structure | `screenshot-planning-guide.md` |
| GIF sequence spec format (tool + sequence array + labels) | `screenshots.json` `gifs[]` | `screenshot-planning-guide.md` |
| Capture method decision matrix (Chrome vs asciinema) | Implicit in `check-screenshots.js` notes | `screenshot-planning-guide.md` |
| Success metrics table (time-to-understand, scroll depth) | `readme-improvement-plan.md` §Metrics | `content-strategy-guide.md` |
| CI-compatible exit code convention (0/1) | All scripts | `validation-workflow.md` |

---

## New Scripts to Build

Three scripts have no SkillMeat equivalent and need to be authored:

### `bootstrap.js`

**Purpose**: Scaffold `.github/readme/` for a new project.

**Inputs**: `--project-type [cli|web|library|saas]`, `--output <dir>`, `--name <project-name>`

**Outputs**:
- Full directory tree
- `package.json` with handlebars dependency
- Seeded `features.json` with 2-3 placeholder categories per project type
- Seeded `screenshots.json` with project-type-appropriate placeholders
- Seeded `version.json` at `0.1.0`
- `partials/` directory with stub `.md` files
- `templates/README.hbs` from canonical template

**Complexity**: Medium — file scaffolding + project-type seed data matrices.

---

### `analyze-project.js`

**Purpose**: Inspect a project to pre-populate `features.json` categories and features.

**Inputs**: `--root <project-root>`, `--output <path-to-features.json>`

**Analysis heuristics**:

| Project Signal | Extracted As |
|----------------|-------------|
| `package.json` scripts | features with `cliCommand` |
| `--help` output (if executable) | CLI feature descriptions |
| `openapi.json` tag groups | feature categories |
| Next.js `app/` route files | `webPage` references |
| Existing `CLAUDE.md` or `README.md` headings | section seeds |

**Output**: Populated `features.json` with `status: "draft"` marker on all features.

**Complexity**: Medium-High — heuristic file analysis with multiple detection paths.

---

### `generate-screenshot-spec.js`

**Purpose**: Analyze a project and produce a `screenshots.json`-compatible spec.

**Inputs**: `--root <project-root>`, `--type [cli|web|library|saas]`, `--output <path>`

**Analysis**:
- Web: Parse route files → generate one screenshot entry per page
- CLI: Run `--help` recursively → generate one CLI screenshot per command group
- Derive GIF specs for top-3 key workflows (heuristic: most commands / most routes)

**Output**: `screenshots.json` with all entries at `status: "pending"` + detailed `notes` capture instructions.

**Complexity**: Medium — route/CLI enumeration + spec templating.

---

## Implementation Order

| Order | Component | Depends On | Complexity | Priority |
|-------|-----------|-----------|-----------|----------|
| 1 | Extract + generalize 5 scripts (`--root` flag) | Nothing | Low | Critical |
| 2 | Formalize 3 JSON schemas | Nothing | Low | Critical |
| 3 | Generalize Handlebars templates | Scripts done | Low | Critical |
| 4 | `SKILL.md` core with Route 4 + 5 inline | Scripts done | Low | Critical |
| 5 | `build-and-rebuild-workflow.md` | SKILL.md | Low | High |
| 6 | `validation-workflow.md` | SKILL.md | Low | High |
| 7 | `content-strategy-guide.md` | Nothing | Medium | High |
| 8 | `screenshot-planning-guide.md` | Nothing | Medium | High |
| 9 | `bootstrap.js` (new script) | Schemas, templates | Medium | High |
| 10 | `bootstrapping-readme-system.md` | bootstrap.js | Medium | High |
| 11 | `ci-and-hook-integration.md` | Nothing | Low | Medium |
| 12 | `analyze-project.js` (new script) | bootstrap.js | Medium-High | Medium |
| 13 | `generate-screenshot-spec.js` (new script) | Screenshot guide | Medium | Medium |
| 14 | Full SKILL.md with all 6 routes | All above | Low | Medium |
| 15 | Validate with skill-builder conventions | Full SKILL.md | Low | Final |

**Minimum viable skill** (items 1-8): Covers Routes 3-5 (Content Strategy, Build, Validate) — the highest-frequency operations. Routes 1, 2, 6 are additive.

---

## Resolved Questions

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | Where should this skill live? | **Project-level**: `.claude/skills/managing-readmes/` | Deploy per-project; extract from SkillMeat's local skills for distribution via catalog |
| 2 | Should `analyze-project.js` run `--help` as subprocess or static reads only? | **Static reads in v1; subprocess via `--exec` opt-in flag** | Best practice: limit security surface, add opt-in later |
| 3 | Should `bootstrap.js` overwrite existing files? | **Skip existing + `--force` flag to overwrite** | Safe default, explicit override |
| 4 | Should screenshot spec integrate with capture tools directly? | **Output spec tuned to Claude Code Chrome MCP tools**; future `--platform` flag for other capture tools | Chrome DevTools MCP is primary; spec format references `mcp__claude-in-chrome__*` tools directly. Future flags for Puppeteer/Playwright/asciinema |
| 5 | Should content strategy be self-contained or depend on `crafting-effective-readmes`? | **Self-contained per deployment** | Skill is deployed per-project; cannot assume other skills exist. Inline all content strategy guidance |
| 6 | CJS vs ESM for scripts? | **ESM** | Per skill-builder conventions; convert all extracted scripts from CJS `require()` to ESM `import` |
| 7 | Universal template vs project-type variants? | **One universal template + project-type partial sets**; future `--template` flag for specific variants | Start simple, extensible via flags later |
