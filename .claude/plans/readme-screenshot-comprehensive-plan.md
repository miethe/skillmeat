# SkillMeat README & Screenshot Comprehensive Plan

**Created**: 2026-01-29
**Version**: 1.0
**Purpose**: Complete specification for README overhaul with screenshot capture, GIF recording, and modular structure for programmatic updates

---

## Table of Contents

1. [Screenshot Strategy](#screenshot-strategy)
2. [README Screenshots (Primary)](#readme-screenshots-primary)
3. [Feature Coverage Screenshots (Extended)](#feature-coverage-screenshots-extended)
4. [GIF Recording Plan](#gif-recording-plan)
5. [Complete Feature Inventory](#complete-feature-inventory)
6. [Modular README Architecture](#modular-readme-architecture)
7. [Implementation Workflow](#implementation-workflow)

---

## Screenshot Strategy

### Principles

1. **Consistent Environment**: All screenshots use same sample data, collection names, themes
2. **Optimal Viewport**: 1280x800 for full-page, 800px wide for README display
3. **Clean State**: No errors, loading spinners, or debug info visible
4. **Populated Data**: Show realistic artifact counts (15-30), not empty or sparse
5. **Dark/Light**: Capture in light mode for README (dark mode for docs)

### File Organization

```
docs/
└── screenshots/
    ├── readme/              # README-specific (optimized for GitHub display)
    │   ├── hero-dashboard.png
    │   ├── feature-collection.png
    │   ├── feature-marketplace.png
    │   ├── feature-deploy.png
    │   └── feature-sync.png
    ├── features/            # All features (comprehensive coverage)
    │   ├── dashboard/
    │   ├── collection/
    │   ├── manage/
    │   ├── projects/
    │   ├── deployments/
    │   ├── marketplace/
    │   ├── context/
    │   ├── templates/
    │   ├── mcp/
    │   ├── settings/
    │   └── sharing/
    ├── cli/                 # Terminal screenshots
    │   ├── init.png
    │   ├── add.png
    │   ├── deploy.png
    │   ├── sync.png
    │   └── analytics.png
    └── gifs/                # Animated demos
        ├── quickstart-workflow.gif
        ├── marketplace-import.gif
        └── sync-conflict.gif
```

### Sample Data Requirements

**Before capturing, ensure these exist:**

- Collection "default" with 25+ artifacts
- Collection "work" with 10+ artifacts
- At least 3 projects with deployments
- Mix of artifact types: Skills (15), Commands (5), Agents (3), MCP (2)
- Tags: "python", "frontend", "testing", "productivity", "automation"
- Some artifacts with "modified" and "outdated" status
- At least 2 GitHub sources added
- Some marketplace listings available

---

## README Screenshots (Primary)

These are the **must-have** screenshots for the README.

### 1. Hero Dashboard

| Attribute | Value |
|-----------|-------|
| **ID** | `hero-dashboard` |
| **File** | `docs/screenshots/readme/hero-dashboard.png` |
| **Page** | Dashboard (`/`) |
| **Viewport** | 1280x720 |
| **Purpose** | First impression, show app at a glance |

**What to Show:**
- Full dashboard with sidebar visible
- Stats cards: Total Artifacts (29), Active Deployments (43), Recent Activity, Last Sync
- Top Artifacts widget with 5+ items and usage bars
- Usage Trends chart with data (last 30 days)
- Tags widget showing tag distribution
- Clean, populated state

**Visual Requirements:**
- Light mode
- No modals/dialogs open
- Sidebar collapsed or narrow
- "Live updates active" indicator visible

**Information Conveyed:**
- "This is a professional, polished app"
- "Analytics and insights are built-in"
- "Real-time tracking of artifacts"

---

### 2. Collection Browser

| Attribute | Value |
|-----------|-------|
| **ID** | `feature-collection` |
| **File** | `docs/screenshots/readme/feature-collection.png` |
| **Page** | Collection (`/collection`) |
| **Viewport** | 1280x720 |
| **Purpose** | Show artifact organization and browsing |

**What to Show:**
- Grid view with 9+ artifact cards visible
- Collection selector showing "All Collections" or "default"
- Toolbar with: View mode toggle, Search, Sort dropdown, Filters
- Artifact cards showing: name, type badge, description, tags
- Mix of artifact types visible (skills, commands, agents)
- At least one card with sync status badge
- Tag filter bar with active tags

**Visual Requirements:**
- Grid view (not list)
- At least 3 rows of cards visible
- Some cards showing confidence scores
- Filter bar visible but not dominating

**Information Conveyed:**
- "Organize artifacts in collections"
- "Multiple view modes and powerful filtering"
- "See status at a glance"

---

### 3. Marketplace Sources

| Attribute | Value |
|-----------|-------|
| **ID** | `feature-marketplace` |
| **File** | `docs/screenshots/readme/feature-marketplace.png` |
| **Page** | Marketplace Sources (`/marketplace/sources`) |
| **Viewport** | 1280x720 |
| **Purpose** | Show discovery and import from GitHub |

**What to Show:**
- Source cards showing GitHub repositories
- Filter bar with artifact type and trust level filters
- At least 3-4 source cards visible
- Each card showing: repo name, artifact count, last scan, status
- "Add Source" button prominent
- Search mode toggle visible

**Visual Requirements:**
- Show diversity of sources (different authors)
- Show artifact counts (e.g., "23 artifacts", "8 artifacts")
- Status indicators (synced, needs rescan)

**Information Conveyed:**
- "Import from any GitHub repository"
- "Automatic scanning and discovery"
- "Trust and quality indicators"

---

### 4. Deployment Tracking

| Attribute | Value |
|-----------|-------|
| **ID** | `feature-deploy` |
| **File** | `docs/screenshots/readme/feature-deploy.png` |
| **Page** | Deployments (`/deployments`) |
| **Viewport** | 1280x720 |
| **Purpose** | Show deployment management and status |

**What to Show:**
- Summary cards: Total (43), Synced (35), Modified (5), Outdated (3)
- Deployment list with mixed statuses
- Status filter dropdown or badges
- Type filter visible
- Deployment cards showing: artifact, project, status, date

**Visual Requirements:**
- Mix of status badges (green synced, yellow modified, orange outdated)
- Flat view (not grouped)
- Clear visual hierarchy

**Information Conveyed:**
- "Track deployments across all projects"
- "See sync status instantly"
- "Know what needs attention"

---

### 5. Sync & Drift Detection

| Attribute | Value |
|-----------|-------|
| **ID** | `feature-sync` |
| **File** | `docs/screenshots/readme/feature-sync.png` |
| **Page** | Artifact Detail Modal (Sync Tab) or Project Manage |
| **Viewport** | 1000x700 (modal) |
| **Purpose** | Show bidirectional sync and diff preview |
| **Artifact to Use** | 'meatycapture-capture' Skill |

**What to Show:**
- Diff viewer showing changes (colored diff)
- Sync status indicator
- "Pull" and "Push" buttons
- Conflict resolution UI (if possible)
- Before/after comparison

**Visual Requirements:**
- Clear diff highlighting (red/green)
- Action buttons visible
- Context around the modal visible (dimmed background)

**Information Conveyed:**
- "See exactly what changed"
- "Preview before applying"
- "Bidirectional sync support"

---

### 6. Terminal Quickstart (Optional but High Impact)

| Attribute | Value |
|-----------|-------|
| **ID** | `cli-quickstart` |
| **File** | `docs/screenshots/readme/cli-quickstart.png` |
| **Source** | Terminal recording |
| **Viewport** | 800x400 |
| **Purpose** | Show CLI in action |

**What to Show:**
- 4 commands: init, add, deploy, list
- Colored output with Rich formatting
- Success messages
- Table output from `list`

**Visual Requirements:**
- Clean terminal theme (not busy)
- Readable font size
- Clear command separation

**Information Conveyed:**
- "Simple CLI interface"
- "Quick to get started"
- "Beautiful terminal output"

---

## Feature Coverage Screenshots (Extended)

These screenshots cover ALL features for documentation and marketing.

### Dashboard (4 screenshots)

| ID | Page | What to Capture |
|----|------|-----------------|
| `dashboard-full` | `/` | Full dashboard with all widgets |
| `dashboard-stats` | `/` | Close-up of stats cards |
| `dashboard-trends` | `/` | Usage trends chart focused |
| `dashboard-top-artifacts` | `/` | Top artifacts widget focused |

### Collection (10 screenshots)

| ID | Page | What to Capture |
|----|------|-----------------|
| `collection-grid` | `/collection` | Grid view with 12+ cards |
| `collection-list` | `/collection` | List view with table |
| `collection-grouped` | `/collection` | Grouped view (if implemented) |
| `collection-filters-open` | `/collection` | Filter dropdown expanded |
| `collection-search-results` | `/collection` | Search with results highlighted |
| `collection-card-detail` | `/collection` | Single card hover/focus state |
| `collection-empty` | `/collection` | Empty state (for docs) |
| `collection-selector` | `/collection` | Collection dropdown open |
| `collection-create-modal` | `/collection` | Create collection dialog |
| `collection-artifact-modal` | `/collection` | Artifact detail modal open |

### Manage (6 screenshots)

| ID | Page | What to Capture |
|----|------|-----------------|
| `manage-skills-tab` | `/manage` | Skills tab selected |
| `manage-commands-tab` | `/manage` | Commands tab |
| `manage-agents-tab` | `/manage` | Agents tab |
| `manage-mcp-tab` | `/manage` | MCP tab |
| `manage-entity-modal` | `/manage` | Unified entity modal |
| `manage-add-entity` | `/manage` | Add entity dialog |

### Projects (6 screenshots)

| ID | Page | What to Capture |
|----|------|-----------------|
| `projects-list` | `/projects` | Project list/grid |
| `projects-create` | `/projects` | Create project dialog |
| `projects-detail` | `/projects/[id]` | Project detail page |
| `projects-manage` | `/projects/[id]/manage` | Deployment management |
| `projects-sync-status` | `/projects/[id]/manage` | Sync status indicators |
| `projects-outdated-alert` | `/projects` | Outdated artifacts alert |

### Deployments (4 screenshots)

| ID | Page | What to Capture |
|----|------|-----------------|
| `deployments-flat` | `/deployments` | Flat view with filters |
| `deployments-grouped` | `/deployments` | Grouped by project view |
| `deployments-filters` | `/deployments` | Status/type filters expanded |
| `deployments-summary` | `/deployments` | Summary cards close-up |

### Marketplace (12 screenshots)

| ID | Page | What to Capture |
|----|------|-----------------|
| `marketplace-listings` | `/marketplace` | Listings grid |
| `marketplace-filters` | `/marketplace` | Filter panel |
| `marketplace-listing-card` | `/marketplace` | Single listing card |
| `marketplace-install-dialog` | `/marketplace` | Install strategy dialog |
| `marketplace-sources` | `/marketplace/sources` | Sources list |
| `marketplace-source-card` | `/marketplace/sources` | Single source card |
| `marketplace-add-source` | `/marketplace/sources` | Add source modal |
| `marketplace-source-detail` | `/marketplace/sources/[id]` | Semantic tree view |
| `marketplace-folder-detail` | `/marketplace/sources/[id]` | Folder detail pane |
| `marketplace-artifact-import` | `/marketplace/sources/[id]` | Import flow |
| `marketplace-publish-wizard` | `/marketplace/publish` | Publish wizard |
| `marketplace-catalog-entry` | Modal | Catalog entry detail |

### Context Entities (4 screenshots)

| ID | Page | What to Capture |
|----|------|-----------------|
| `context-entities-list` | `/context-entities` | Entity list with filters |
| `context-entities-editor` | `/context-entities` | Entity editor form |
| `context-entities-types` | `/context-entities` | Type filter options |
| `context-entities-deploy` | Modal | Deploy to project dialog |

### Templates (3 screenshots)

| ID | Page | What to Capture |
|----|------|-----------------|
| `templates-list` | `/templates` | Template browser |
| `templates-preview` | `/templates` | Template preview |
| `templates-deploy-wizard` | `/templates` | Deployment wizard |

### MCP Servers (4 screenshots)

| ID | Page | What to Capture |
|----|------|-----------------|
| `mcp-list` | `/mcp` | MCP server list |
| `mcp-add-form` | `/mcp` | Add server form |
| `mcp-config` | `/mcp` | Server configuration |
| `mcp-status` | `/mcp` | Health/status indicators |

### Settings (3 screenshots)

| ID | Page | What to Capture |
|----|------|-----------------|
| `settings-general` | `/settings` | General settings |
| `settings-github` | `/settings` | GitHub authentication |
| `settings-api` | `/settings` | API configuration |

### Sharing (3 screenshots)

| ID | Page | What to Capture |
|----|------|-----------------|
| `sharing-export` | `/sharing` | Export bundle UI |
| `sharing-import` | `/sharing` | Import bundle UI |
| `sharing-link` | `/sharing` | Share link generation |

### Modals & Dialogs (10 screenshots)

| ID | Context | What to Capture |
|----|---------|-----------------|
| `modal-artifact-detail` | Collection | Full artifact detail modal |
| `modal-diff-viewer` | Sync | Colored diff view |
| `modal-conflict-resolver` | Sync | Conflict resolution UI |
| `modal-merge-workflow` | Sync | Merge strategy selection |
| `modal-delete-confirm` | Any | Deletion confirmation |
| `modal-rating` | Marketplace | Rating dialog |
| `modal-tags-editor` | Collection | Tag management |
| `modal-parameter-editor` | Entity | Parameter configuration |
| `modal-version-history` | Entity | Version timeline |
| `modal-rollback` | Entity | Rollback confirmation |

### CLI Terminal (8 screenshots)

| ID | Command | What to Capture |
|----|---------|-----------------|
| `cli-init` | `skillmeat init` | Initialization output |
| `cli-add` | `skillmeat add skill` | Add artifact output |
| `cli-deploy` | `skillmeat deploy` | Deployment output |
| `cli-list` | `skillmeat list` | Table of artifacts |
| `cli-sync-check` | `skillmeat sync check` | Drift detection |
| `cli-analytics` | `skillmeat analytics usage` | Usage report |
| `cli-search` | `skillmeat search` | Search results |
| `cli-status` | `skillmeat status` | Status output |

---

## GIF Recording Plan

### Tool: Claude in Chrome MCP

The `mcp__claude-in-chrome__gif_creator` tool provides native GIF recording:

```
Actions:
- start_recording: Begin capturing frames
- stop_recording: Stop capturing (keeps frames)
- export: Generate GIF with overlays
- clear: Discard frames
```

**Configuration Options:**
- `showClickIndicators`: Orange circles at click locations
- `showDragPaths`: Red arrows for drags
- `showActionLabels`: Black labels describing actions
- `showProgressBar`: Orange progress bar at bottom
- `showWatermark`: Claude logo watermark
- `quality`: 1-30 (lower = better, 10 default)

### GIF Specifications

#### 1. Quickstart Workflow (`quickstart-workflow.gif`)

| Attribute | Value |
|-----------|-------|
| **Duration** | 20-30 seconds |
| **Resolution** | 1280x720 |
| **Actions** | 8-10 steps |

**Sequence:**
1. Open SkillMeat dashboard (2s)
2. Navigate to Collection (click) (2s)
3. Show collection grid (2s)
4. Click "Add" or search (2s)
5. Show artifact detail modal (3s)
6. Close modal, navigate to Deployments (2s)
7. Show deployment list with statuses (3s)
8. Navigate back to dashboard (2s)

**Labels to Show:**
- "Dashboard overview"
- "Browse your collection"
- "View artifact details"
- "Track deployments"

#### 2. Marketplace Import (`marketplace-import.gif`)

| Attribute | Value |
|-----------|-------|
| **Duration** | 25-35 seconds |
| **Resolution** | 1280x720 |
| **Actions** | 10-12 steps |

**Sequence:**
1. Navigate to Marketplace Sources (2s)
2. Click "Add Source" (2s)
3. Enter GitHub URL (3s)
4. Click Scan (2s)
5. Show scanning progress (2s)
6. View discovered artifacts (3s)
7. Click on an artifact (2s)
8. Show catalog entry detail (3s)
9. Click Import (2s)
10. Show success (2s)

**Labels to Show:**
- "Add GitHub source"
- "Automatic scanning"
- "Browse discovered artifacts"
- "Import to collection"

#### 3. Sync & Conflict Resolution (`sync-conflict.gif`)

| Attribute | Value |
|-----------|-------|
| **Duration** | 30-40 seconds |
| **Resolution** | 1000x700 (modal focused) |
| **Actions** | 12-15 steps |

**Sequence:**
1. Show artifact with "modified" status (2s)
2. Click to open (2s)
3. Navigate to Sync tab (2s)
4. Show diff preview (4s)
5. Show merge options (3s)
6. Select merge strategy (2s)
7. Show conflict highlight (3s)
8. Resolve conflict (3s)
9. Click "Apply" (2s)
10. Show success state (2s)

**Labels to Show:**
- "Detect changes"
- "Preview diff"
- "Choose merge strategy"
- "Resolve conflicts"
- "Apply safely"

#### 4. CLI Demo (`cli-demo.gif`)

| Attribute | Value |
|-----------|-------|
| **Duration** | 15-20 seconds |
| **Tool** | Terminal recording (asciinema or similar) |
| **Actions** | 4-5 commands |

**Sequence:**
1. `skillmeat init` → show output (3s)
2. `skillmeat add skill anthropics/skills/canvas` → show progress (4s)
3. `skillmeat list` → show table (3s)
4. `skillmeat deploy canvas` → show success (3s)
5. Show final state (2s)

---

## Complete Feature Inventory

### Web UI Features (22 Pages)

#### Core Collection Management
| Feature | Page | Description |
|---------|------|-------------|
| Dashboard Analytics | `/` | Real-time stats, trends, top artifacts |
| Collection Browser | `/collection` | Grid/list/grouped views, search, filter, sort |
| Entity Management | `/manage` | Type-based tabs, unified detail modal |
| Group Organization | `/groups` | Cross-collection grouping |

#### Project & Deployment
| Feature | Page | Description |
|---------|------|-------------|
| Project Management | `/projects` | Create, list, configure projects |
| Project Detail | `/projects/[id]` | Deployments, config, history |
| Deployment Sync | `/projects/[id]/manage` | Pull/push, drift detection |
| Deployment Dashboard | `/deployments` | Filter by status/type, flat/grouped |

#### Marketplace & Discovery
| Feature | Page | Description |
|---------|------|-------------|
| Marketplace Listings | `/marketplace` | Browse published bundles |
| GitHub Sources | `/marketplace/sources` | Add, scan, manage sources |
| Source Explorer | `/marketplace/sources/[id]` | Semantic tree, folder navigation |
| Bundle Publishing | `/marketplace/publish` | Multi-step publish wizard |

#### Configuration
| Feature | Page | Description |
|---------|------|-------------|
| Context Entities | `/context-entities` | Project config artifacts |
| Templates | `/templates` | Quick setup templates |
| MCP Servers | `/mcp` | Protocol server management |
| Settings | `/settings` | GitHub auth, API config |
| Sharing | `/sharing` | Bundle export/import |

### CLI Features (116+ Commands)

#### Core Commands
| Command | Description |
|---------|-------------|
| `init` | Initialize collection |
| `list` | List artifacts |
| `show` | Show artifact details |
| `add skill/command/agent` | Add artifacts |
| `deploy` | Deploy to project |
| `remove` | Remove artifact |

#### Sync & Intelligence
| Command | Description |
|---------|-------------|
| `sync check` | Check for drift |
| `sync pull` | Pull from upstream |
| `sync preview` | Preview changes |
| `search` | Search across projects |
| `find-duplicates` | Find similar artifacts |

#### Analytics
| Command | Description |
|---------|-------------|
| `analytics usage` | Usage statistics |
| `analytics top` | Most used artifacts |
| `analytics cleanup` | Cleanup suggestions |
| `analytics trends` | Usage trends |
| `analytics export` | Export reports |

#### Versioning
| Command | Description |
|---------|-------------|
| `snapshot` | Create snapshot |
| `history` | View history |
| `rollback` | Rollback to snapshot |

#### Quality & Trust
| Command | Description |
|---------|-------------|
| `rate` | Rate artifact |
| `scores import` | Import scores |
| `match` | Find similar |

#### Advanced
| Command | Description |
|---------|-------------|
| `mcp add/list/deploy/test` | MCP server management |
| `context add/list/deploy` | Context entity management |
| `bundle create/import/export` | Bundle operations |
| `vault encrypt/decrypt/list` | Secure vault |
| `marketplace search/install` | Marketplace operations |
| `web dev/build/start/doctor` | Web interface |

### API Endpoints (150+)

See `FEATURE_CATALOG_SUMMARY.md` for complete API reference.

---

## Modular README Architecture

### Goals

1. **Single Source of Truth**: Features defined once, rendered everywhere
2. **Programmatic Updates**: Scripts can update sections independently
3. **Version Aware**: Content can vary by version
4. **Template-Driven**: Consistent formatting across sections

### Proposed Structure

```
README.md                    # Main entry point (assembles partials)
.github/
└── readme/
    ├── partials/            # Reusable content blocks
    │   ├── hero.md          # Logo, tagline, badges
    │   ├── features.md      # Feature list
    │   ├── quickstart.md    # Installation & first steps
    │   ├── screenshots.md   # Screenshot grid
    │   ├── cli-reference.md # CLI command summary
    │   ├── documentation.md # Doc links
    │   ├── contributing.md  # Contribution guide
    │   └── footer.md        # License, support, credits
    ├── data/                # Structured data for rendering
    │   ├── features.json    # Feature definitions
    │   ├── screenshots.json # Screenshot metadata
    │   ├── commands.json    # CLI command catalog
    │   └── version.json     # Version info
    ├── templates/           # Handlebars/Mustache templates
    │   ├── feature-grid.hbs
    │   ├── screenshot-table.hbs
    │   └── command-list.hbs
    └── scripts/
        ├── build-readme.js  # Assembles README from partials
        ├── update-version.js # Updates version references
        ├── validate-links.js # Checks all links
        └── sync-features.js # Syncs features.json from code
```

### Data Schema: `features.json`

```json
{
  "version": "0.3.0-beta",
  "categories": [
    {
      "id": "collection",
      "name": "Collection Management",
      "icon": "package",
      "features": [
        {
          "id": "multi-collection",
          "name": "Multi-Collection Support",
          "description": "Organize artifacts into named collections",
          "cli_command": "skillmeat collection create",
          "web_page": "/collection",
          "since": "0.1.0",
          "screenshot": "collection-selector.png"
        }
      ]
    }
  ]
}
```

### Data Schema: `screenshots.json`

```json
{
  "screenshots": [
    {
      "id": "hero-dashboard",
      "file": "docs/screenshots/readme/hero-dashboard.png",
      "alt": "SkillMeat Dashboard showing analytics and artifact overview",
      "width": 800,
      "category": "readme",
      "page": "/",
      "features": ["dashboard", "analytics"],
      "captured": "2026-01-29",
      "version": "0.3.0-beta"
    }
  ]
}
```

### README.md Template Structure

```markdown
<!-- AUTO-GENERATED: Do not edit directly. See .github/readme/ -->
<!-- GENERATED: 2026-01-29T10:00:00Z -->
<!-- VERSION: 0.3.0-beta -->

<!-- BEGIN:hero -->
{{> hero }}
<!-- END:hero -->

<!-- BEGIN:screenshots -->
{{> screenshots }}
<!-- END:screenshots -->

<!-- BEGIN:quickstart -->
{{> quickstart }}
<!-- END:quickstart -->

<!-- BEGIN:features -->
{{#each categories}}
### {{name}}
{{#each features}}
- **{{name}}** - {{description}}
{{/each}}
{{/each}}
<!-- END:features -->

<!-- BEGIN:documentation -->
{{> documentation }}
<!-- END:documentation -->

<!-- BEGIN:contributing -->
{{> contributing }}
<!-- END:contributing -->

<!-- BEGIN:footer -->
{{> footer }}
<!-- END:footer -->
```

### Update Script: `build-readme.js`

```javascript
#!/usr/bin/env node
/**
 * Assembles README.md from partials and data files
 *
 * Usage: node .github/readme/scripts/build-readme.js
 *
 * Options:
 *   --version <ver>  Override version
 *   --dry-run        Print to stdout instead of writing
 *   --section <name> Update only specific section
 */

const fs = require('fs');
const path = require('path');
const Handlebars = require('handlebars');

// Load data
const features = require('../data/features.json');
const screenshots = require('../data/screenshots.json');
const version = require('../data/version.json');

// Load partials
const partialsDir = path.join(__dirname, '../partials');
fs.readdirSync(partialsDir).forEach(file => {
  const name = path.basename(file, '.md');
  const content = fs.readFileSync(path.join(partialsDir, file), 'utf8');
  Handlebars.registerPartial(name, content);
});

// Load and compile main template
const template = fs.readFileSync(
  path.join(__dirname, '../templates/README.hbs'),
  'utf8'
);
const compiled = Handlebars.compile(template);

// Render
const output = compiled({
  features: features.categories,
  screenshots: screenshots.screenshots.filter(s => s.category === 'readme'),
  version: version.current,
  generated: new Date().toISOString()
});

// Write
fs.writeFileSync(
  path.join(__dirname, '../../../README.md'),
  output
);

console.log('README.md updated successfully');
```

### CI Integration

```yaml
# .github/workflows/readme-check.yml
name: README Validation

on:
  push:
    paths:
      - '.github/readme/**'
      - 'README.md'
      - 'docs/screenshots/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        run: cd .github/readme && npm install

      - name: Validate links
        run: node .github/readme/scripts/validate-links.js

      - name: Check screenshots exist
        run: node .github/readme/scripts/check-screenshots.js

      - name: Verify generated matches source
        run: |
          node .github/readme/scripts/build-readme.js --dry-run > /tmp/generated.md
          diff README.md /tmp/generated.md
```

### Update Workflows

#### Adding a New Feature

1. Add entry to `features.json`
2. Capture screenshot (if applicable)
3. Add to `screenshots.json`
4. Run `npm run readme:build`
5. Commit all changes

#### New Version Release

1. Update `version.json`
2. Run `npm run readme:update-version`
3. Capture fresh screenshots (if UI changed)
4. Run `npm run readme:build`
5. Commit

#### Screenshot Refresh

1. Run web dev server
2. Execute screenshot capture script
3. Update `screenshots.json` timestamps
4. Run `npm run readme:build`
5. Commit

---

## Implementation Workflow

### Phase 1: Setup & Data Preparation (Day 1)

1. Create directory structure
2. Create `features.json` from feature catalog
3. Create `screenshots.json` schema
4. Set up sample data in dev environment (should already be completed)
5. Install recording dependencies

### Phase 2: Screenshot Capture (Day 1-2)

1. Start web dev server
2. Capture README screenshots (6 primary)
3. Capture feature screenshots (by category)
4. Capture CLI screenshots
5. Validate and resize images

### Phase 3: GIF Recording (Day 2)

1. Record quickstart workflow
2. Record marketplace import
3. Record sync flow
4. Export and optimize GIFs

### Phase 4: Build Modular System (Day 2-3)

1. Create partials from current README
2. Build Handlebars templates
3. Create build script
4. Test full assembly
5. Set up CI validation

### Phase 5: Final README Assembly (Day 3)

1. Run build script
2. Review rendered output
3. Fine-tune copy and formatting
4. Validate all links
5. Final commit

---

## Appendix: Capture Commands

### Chrome DevTools Screenshot

```bash
cd .claude/skills/chrome-devtools/scripts
node screenshot.js \
  --url http://localhost:3000 \
  --output ../../../docs/screenshots/readme/hero-dashboard.png \
  --width 1280 \
  --height 720 \
  --wait-until networkidle2
```

### Claude in Chrome GIF Recording

```
1. mcp__claude-in-chrome__tabs_context_mcp (get tab ID)
2. mcp__claude-in-chrome__navigate (go to page)
3. mcp__claude-in-chrome__gif_creator action=start_recording
4. mcp__claude-in-chrome__computer action=screenshot (capture initial frame)
5. [Perform actions]
6. mcp__claude-in-chrome__computer action=screenshot (capture final frame)
7. mcp__claude-in-chrome__gif_creator action=stop_recording
8. mcp__claude-in-chrome__gif_creator action=export download=true filename="workflow.gif"
```

### Terminal Recording (asciinema)

```bash
# Install
pip install asciinema

# Record
asciinema rec cli-demo.cast

# Convert to GIF (requires agg or similar)
agg cli-demo.cast cli-demo.gif --theme monokai
```

---

## Summary

This plan provides:

1. **10 README screenshots** with detailed specifications
2. **60+ feature screenshots** covering all pages
3. **4 GIF workflows** using Claude in Chrome MCP
4. **Complete feature inventory** (22 pages, 116+ CLI commands)
5. **Modular README architecture** for programmatic updates
6. **Implementation workflow** with clear phases

The modular structure enables:
- Automated version updates
- CI validation of links/images
- Partial section updates
- Consistent formatting
- Easy feature additions
