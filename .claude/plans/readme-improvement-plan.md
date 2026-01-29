# SkillMeat README Improvement Plan

## Executive Summary

Transform the root README from a technical reference into the **primary OSS marketing document** for SkillMeat. The goal is to make first-time visitors understand what SkillMeat does, see it in action, and get excited to try it - all within 30 seconds of landing on the GitHub page.

---

## Audit of Current README

### Strengths (Keep)

| Element | Why It Works |
|---------|-------------|
| Clear badges | Shows project health at a glance |
| Before/After section | Immediately communicates value |
| Example workflow | Demonstrates real usage |
| Architecture diagram | Helps understanding |
| FAQ section | Addresses common concerns |
| Roadmap | Shows project direction |

### Weaknesses (Fix)

| Issue | Impact | Priority |
|-------|--------|----------|
| **No screenshots** | Users can't visualize the tool | Critical |
| **No hero image** | Misses "wow" moment | Critical |
| **Buried Web UI** | Key feature hidden at bottom | High |
| **Text-heavy features** | Overwhelming first impression | High |
| **No visual hierarchy** | Hard to scan | Medium |
| **Outdated version refs** | v0.2.0-alpha vs v0.3.0-beta | Medium |
| **Missing logo usage** | Logo exists but not used | Medium |

---

## Target Audience Analysis

### Primary Audience: Claude Code Power Users

**Who they are:**
- Developers using Claude Code daily
- Frustrated with manual artifact management
- Already have 5+ skills/commands they copy between projects

**What they need:**
- "Does this solve MY pain?" answered in 5 seconds
- Visual proof it works
- Quick path to "running it myself"

### Secondary Audience: Claude Code Newcomers

**Who they are:**
- Just discovered Claude Code
- Looking to level up their workflow
- May not know artifact types exist

**What they need:**
- Education on what artifacts are
- Low barrier to entry
- Confidence the tool is maintained

---

## Proposed README Structure

```
1. Hero Section (Above the Fold)
   - Logo + tagline
   - 3-word value prop
   - Hero screenshot/GIF
   - Quick install badge

2. Feature Showcase (Visual)
   - 3-4 screenshots with captions
   - Key capabilities in icons/badges

3. Quick Start (30 seconds to first success)
   - Install (one-liner)
   - Initialize (one command)
   - Add first artifact (one command)
   - See it work (screenshot of result)

4. Why SkillMeat? (Pain → Solution)
   - Before/After comparison (refined)
   - Key differentiators

5. Feature Deep Dive (Expandable/Collapsible)
   - CLI features
   - Web UI features
   - Intelligence features
   - Marketplace

6. Documentation Links (Gateway)
   - User guides
   - Examples
   - API reference

7. Contributing (Community)
   - Quick contribution guide
   - Development setup

8. Footer
   - License, support, acknowledgments
```

---

## Screenshot Requirements

### Must-Have Screenshots (Priority 1)

| Screenshot | Purpose | Status |
|------------|---------|--------|
| **Dashboard Overview** | Show the full app at a glance | Have: `titlebar-revamp.png` |
| **Collection Browser** | Show artifact browsing | Need to capture |
| **Marketplace Source** | Show discovery/import flow | Have: `marketplace-sourcing-filters.png` |
| **Artifact Detail View** | Show file contents/editing | Have: `11-26-contents.png` |

### Nice-to-Have Screenshots (Priority 2)

| Screenshot | Purpose | Status |
|------------|---------|--------|
| **CLI in action** | Terminal workflow | Need to record |
| **Sync status** | Show drift detection | Need to capture |
| **Analytics dashboard** | Show usage insights | Need to capture |
| **Context Entities** | Advanced feature | Have: `context-entities-v1.png` |

### GIF Animations (Priority 3)

| GIF | Purpose |
|-----|---------|
| **30-second demo** | Full workflow from install to deploy |
| **Web UI walkthrough** | Navigate key features |
| **Import from GitHub** | Show marketplace discovery |

---

## Content Sections - Detailed Plan

### 1. Hero Section

**Current:**
```markdown
# SkillMeat: Personal Collection Manager for Claude Code Artifacts
[badges]
**SkillMeat** is your personal Claude Code artifact collection manager...
```

**Proposed:**
```markdown
<p align="center">
  <img src="docs/dev/designs/logo/skillmeat-transparent.png" width="120" alt="SkillMeat">
</p>

<h1 align="center">SkillMeat</h1>
<p align="center">
  <strong>Your personal library for Claude Code artifacts</strong>
</p>

<p align="center">
  Collect. Organize. Deploy anywhere.
</p>

<p align="center">
  [badges]
</p>

<p align="center">
  <img src="docs/screenshots/hero-dashboard.png" alt="SkillMeat Dashboard" width="800">
</p>

<p align="center">
  <a href="#quick-start">Get Started</a> |
  <a href="https://skillmeat.dev">Website</a> |
  <a href="docs/user/quickstart.md">Documentation</a>
</p>
```

### 2. Feature Showcase

**Format:** 2x2 grid of screenshots with captions

```markdown
## See It In Action

<table>
<tr>
<td width="50%">
<img src="docs/screenshots/collection-browse.png" alt="Browse Collection">
<br><strong>Browse Your Collection</strong>
<br>Organize skills, commands, and agents in one place
</td>
<td width="50%">
<img src="docs/screenshots/marketplace.png" alt="Marketplace">
<br><strong>Discover in Marketplace</strong>
<br>Find and import artifacts from GitHub sources
</td>
</tr>
<tr>
<td width="50%">
<img src="docs/screenshots/deploy.png" alt="Deploy">
<br><strong>Deploy Anywhere</strong>
<br>One command to deploy to any project
</td>
<td width="50%">
<img src="docs/screenshots/sync.png" alt="Sync">
<br><strong>Stay in Sync</strong>
<br>Track changes and safely update artifacts
</td>
</tr>
</table>
```

### 3. Quick Start (Refined)

**Current:** 20+ lines before first command
**Proposed:** 4 commands with immediate visual payoff

```markdown
## Quick Start

### Install
```bash
pip install skillmeat  # or: uv tool install skillmeat
```

### Run
```bash
skillmeat init                              # Create your collection
skillmeat add skill anthropics/skills/canvas  # Add from GitHub
skillmeat deploy canvas                     # Deploy to project
```

### Or use the Web UI
```bash
skillmeat web dev  # Opens at localhost:3000
```

<img src="docs/screenshots/quickstart-result.png" alt="Result" width="600">
```

### 4. Why SkillMeat? (Refined)

**Keep the Before/After format but make it more visual:**

```markdown
## Why SkillMeat?

| Without SkillMeat | With SkillMeat |
|:---:|:---:|
| Copy/paste between projects | Deploy from your collection |
| No update tracking | Smart sync with drift detection |
| Manual version management | Snapshots and rollback |
| Scattered artifacts | One organized library |
| Text-only management | Visual Web UI + CLI |
```

### 5. Key Features (Scannable)

**Replace wall of text with icon + one-liner format:**

```markdown
## Features

### CLI Power
- **Collection Management** - Organize artifacts into named collections
- **Smart Search** - Find artifacts across all projects with ripgrep
- **Safe Updates** - Preview changes, auto-merge, rollback on failure
- **Usage Analytics** - Track deployments and identify cleanup candidates

### Visual Interface
- **Dashboard** - See all collections, deployments, and activity at a glance
- **Marketplace** - Browse and import from GitHub sources
- **Sync Status** - Visual drift detection and conflict resolution
- **MCP Server Management** - Install and configure Model Context Protocol servers

### Intelligence
- **Bidirectional Sync** - Changes flow both ways between projects and collection
- **Duplicate Detection** - Find similar artifacts with similarity scoring
- **Quality Ratings** - Community ratings with anti-gaming protection
- **Confidence Scores** - Automated quality assessment
```

---

## Additional Deliverables

### 1. Screenshot Capture Plan

**Location:** `docs/screenshots/` (new directory for README assets)

| File | Source | Capture Notes |
|------|--------|---------------|
| `hero-dashboard.png` | Existing `titlebar-revamp.png` | Crop/resize to 800px wide |
| `collection-browse.png` | New capture | Show grid view with multiple artifacts |
| `marketplace.png` | `marketplace-sourcing-filters.png` | May need new capture |
| `deploy-result.png` | New capture | Terminal showing successful deploy |
| `sync-status.png` | New capture | Show drift detection UI |

### 2. Directory Structure for Assets

```
docs/
├── screenshots/           # NEW: README-specific assets
│   ├── hero-dashboard.png
│   ├── collection-browse.png
│   ├── marketplace.png
│   ├── deploy-result.png
│   └── sync-status.png
├── user/                  # Existing user docs
└── dev/                   # Existing dev docs
    └── designs/
        └── logo/          # Existing logo assets
```

### 3. Landing Page Preparation

The README should link to a future landing page. Placeholder:

```markdown
<p align="center">
  <a href="https://skillmeat.dev">Visit skillmeat.dev for tutorials and demos</a>
</p>
```

---

## Implementation Phases

### Phase 1: Critical Visual Updates (Do First)

1. Add logo to top of README
2. Create `docs/screenshots/` directory
3. Capture/resize key screenshots
4. Add hero screenshot below badges
5. Update version references to v0.3.0-beta

**Estimated effort:** 2-3 hours
**Files touched:** README.md, new screenshot files

### Phase 2: Content Restructure

1. Reorder sections per new structure
2. Refine Quick Start to 4 commands
3. Convert features to scannable format
4. Add feature showcase grid
5. Trim development section (move to CONTRIBUTING.md)

**Estimated effort:** 3-4 hours
**Files touched:** README.md, possibly new CONTRIBUTING.md

### Phase 3: Polish & Additional Assets

1. Create GIF demos (optional but high impact)
2. Add collapsible sections for detailed content
3. Add screenshot alt-text for accessibility
4. Test all links
5. Final prose editing

**Estimated effort:** 2-3 hours
**Files touched:** README.md, GIF files

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Time to understand what it does | ~60s | <15s |
| Visual assets in README | 1 (ASCII) | 5+ screenshots |
| Commands before first success | 6+ | 4 |
| Scroll depth to Web UI | Bottom 20% | Top 40% |

---

## Open Questions

1. **Landing page domain:** Is skillmeat.dev registered/planned?
2. **GIF recording tool:** What should be used for terminal recordings?
3. **Screenshot capture:** Run web dev and capture manually, or automate?
4. **Version in README:** Lock to v0.3.0-beta or use "latest"?

---

## Appendix: Reference Screenshots Available

### Existing Assets That Can Be Used

| File | Description | Usability |
|------|-------------|-----------|
| `docs/dev/designs/logo/skillmeat-transparent.png` | Logo | Ready to use |
| `docs/project_plans/renders/titlebar-revamp.png` | Dashboard | Needs light crop |
| `docs/project_plans/renders/marketplace-sourcing-filters.png` | Marketplace | Usable |
| `docs/user/assets/screenshots/11-26-contents.png` | Artifact detail | Usable |
| `docs/dev/designs/screenshots/context-entities-v1.png` | Context entities | Advanced feature |

### Assets to Capture

1. Collection Browse view (grid layout)
2. Terminal showing successful workflow
3. Sync status with drift indicators
4. Deployment tracking view

---

## Next Steps

1. **Review this plan** - Get feedback on proposed structure
2. **Capture screenshots** - Prioritize hero and feature grid
3. **Draft new README** - Apply structure with placeholder images
4. **Iterate** - Refine copy and visuals based on feedback
