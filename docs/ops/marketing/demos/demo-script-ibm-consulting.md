---
title: "SkillMeat Demo Script — IBM Consulting Agentic SDLC"
audience: "IBM Consulting — Agentic SDLC Modernization Teams"
target_runtime: "6:30–7:30"
recording_resolution: "1920x1080"
browser_window: "1440x900 (leave taskbar visible)"
date: "2026-02"
---

# SkillMeat Demo Script
## IBM Consulting — Agentic SDLC Modernization Presentation

**Total Target Runtime**: 6:30–7:30
**Primary Message**: SkillMeat is the package manager and lifecycle platform for AI development artifacts — the infrastructure layer that makes agentic teams repeatable, scalable, and governable.
**CTA**: Deploy SkillMeat alongside your next Claude Code project as the artifact management backbone.

---

## Pre-Recording Staging Checklist

Complete all of these before opening the recording tool.

### Environment Setup
- [ ] Run `skillmeat web dev` and confirm both servers are healthy: `localhost:3000` (web) and `localhost:8080` (API)
- [ ] Open a terminal with a clean shell — no prior command history visible (`clear`)
- [ ] Set terminal font size to 18pt minimum (readable in compressed video)
- [ ] Set terminal theme to dark (matches the web UI)
- [ ] Browser: Chrome, no extensions visible, bookmarks bar hidden (`Cmd+Shift+B`)
- [ ] Browser zoom: 100%
- [ ] Browser window: 1440x900 (use the resize tool if available)
- [ ] Open `localhost:3000` in the browser — confirm the Dashboard loads fully

### Demo Data Requirements
The demo reads best with realistic-looking data in the collection. Confirm or seed:
- [ ] At least 12–15 artifacts in the collection, across types: `skill`, `agent`, `command`, `mcp`, `hook`
- [ ] At least 3 projects registered (e.g., "agentic-sdlc-pilot", "insurance-claims-bot", "code-review-pipeline")
- [ ] At least one artifact in an `outdated` or `modified` sync state (to show drift detection)
- [ ] At least 5–8 memory items across 2 projects, including at least one `gotcha` and one `decision` type
- [ ] At least 2 artifacts with tags (e.g., "ibm-consulting", "production", "experimental")

### Good Demo Artifacts to Have
These read well for the IBM Consulting audience:
- `dev-execution` skill (the one that drives phase execution — directly relevant to their work)
- `artifact-tracking` skill
- `planning` skill
- `code-reviewer` agent
- `ultrathink-debugger` agent
- An MCP server (e.g., a GitHub MCP)

### Staging Verification
- [ ] `skillmeat list` returns a clean, readable table output
- [ ] `skillmeat status` shows at least one project
- [ ] Collection page (`/collection`) shows cards with descriptions, tags, and badges
- [ ] Health & Sync page (`/manage`) shows at least one artifact with a non-`synced` state
- [ ] Dashboard analytics widgets are populated (not all-zeros)
- [ ] Memories page (`/memories`) shows items grouped by project

---

## SCENE 1: The Problem (0:00–0:45)

**Automation**: Manual — requires live terminal interaction

### Shot Description
Terminal window, full screen. Show a realistic directory tree of a Claude Code project.

### Terminal Commands to Run
```bash
# Show what "managing" AI artifacts looks like without SkillMeat
ls -la ~/.claude/skills/
ls -la .claude/skills/
```

Let the output sit for a beat. The audience should see a flat pile of files with no structure, versioning, or metadata visible.

### Narration

"In the age of AI Agent-driven development, the SDLC now revolves around effective context management. From custom AGENTS.md/CLAUDE.md instructions to skills, agents, and commands — these are the building blocks of your delivery patterns. They are the "artifacts" of your AI development process."

"If your team is using Claude Code for agentic development — writing custom skills, agents, and commands to encode your delivery patterns — you already know this problem.

Every project has its own copy of these files. There is no version. There is no inventory. When the canvas-design skill gets updated upstream, you find out the hard way, three weeks later, when a junior consultant gets unexpected behavior.

And when a new engagement starts, someone asks the Slack channel: 'Does anyone have a working code-review agent I can copy?'"

**Pause beat.**

"This is the dependency management problem. We solved it for code with npm and pip. We have not yet solved it for AI artifacts."

### Timing: ~0:45
### Emotion: Recognition, mild frustration

---

## SCENE 2: Solution Introduction (0:45–1:15)

**Automation**: Fully automatable — browser navigation only

### Shot Description
Navigate to `localhost:3000`. The Dashboard loads. Show the full page — stats cards at top, analytics widgets below, live update indicator active (green pulse dot).

### Key UI Elements to Highlight
- Stats cards: total artifacts count, active projects, sync success rate
- The green "Live updates active" pulse dot (top right of analytics section)
- The Enterprise Insights widget showing deployment frequency

### Narration
"SkillMeat is a package manager and lifecycle platform for Claude Code artifacts.

Think of it as Homebrew meets npm — but purpose-built for the AI artifacts that power your agentic workflows.

This is the dashboard. It gives your team a live view of your artifact inventory, deployment health, and sync status across every project you are running."

**Hover briefly over the stats cards — artifact count, projects, sync success rate.**

"In one view: how many AI capabilities your team has built and is actively managing. Let me show you how it works."

### Timing: ~0:30
### Emotion: Curiosity, confidence

---

## SCENE 3: The Collection (1:15–2:10)

**Automation**: Semi-automatable — navigation and filter clicks can be scripted; hover interactions are manual

### Shot Description
Navigate to `/collection` (click "Collections" in the left nav).

The collection grid loads — artifact browse cards in a 3-column grid. Each card shows:
- Type icon and name
- Author / source
- Description (2–3 line clamp)
- Tags (colored badges)
- A deployment indicator badge

### Key Interactions to Perform
1. Click the "Skills" tab filter at the top (ArtifactTypeTabs) — collection filters to skills only
2. Hover over one artifact card to show the action menu
3. Click on one artifact card to open the detail modal

### In the Detail Modal, Show
- The "Overview" tab: description, metadata, file count, source (GitHub path)
- The "Files" tab briefly: the file tree of the artifact
- The "Sync" tab: the 3-way comparison controls

### Narration
"Your collection is your personal artifact library. Everything your team has discovered, built, or imported lives here — versioned, tagged, and tracked.

These are skills. Each one is a Claude Code instruction set that encodes a delivery pattern — dev execution, artifact tracking, frontend design, planning.

When I click into one..."

**Click to open the detail modal.**

"...I get the full picture. What it does, where it came from, which GitHub repo it tracks, how many files it contains, and whether it is in sync with its upstream source.

This is the artifact-as-code pattern. Your team's AI capabilities are now first-class versioned artifacts, not loose files."

**Switch to the Sync tab in the modal.**

"More on sync in a moment. Let me show you how artifacts get in here in the first place."

### Timing: ~0:55
### Emotion: Discovery, clarity

---

## SCENE 4: CLI — Adding Artifacts (2:10–2:55)

**Automation**: Semi-automatable — can pre-stage the command; the terminal output is the key visual

### Shot Description
Switch to the terminal (side-by-side with browser, or full terminal view).

### Terminal Commands to Run (in sequence, with pauses)

```bash
# Search available artifacts
skillmeat search code-review
```

Wait for output. Show the table of results.

```bash
# Add an artifact from GitHub
skillmeat add agent miethe/skillmeat-artifacts/agents/code-reviewer
```

Show the Rich output: security warning prompt, then progress indicators, then "Added successfully" confirmation.

```bash
# Verify it landed in the collection
skillmeat list --type agent
```

Show the table. The new artifact appears.

### Back to Browser
Navigate back to `/collection`, filter by "Agents". The `code-reviewer` agent now appears in the grid.

### Narration
"Adding artifacts is a single command.

I search for what I need. I add it with `skillmeat add`. The tool resolves the GitHub source, validates the content, warns me if it needs permission to run, and adds it to my collection.

And immediately..."

**Switch back to browser, show the agent now visible in the collection grid.**

"...it appears in the web UI. The filesystem and the database stay in sync automatically.

Your team can point SkillMeat at any GitHub repo that follows the artifact structure — your own internal repos, community repos, or the upstream Anthropic skills library."

### Timing: ~0:45
### Emotion: Simplicity, power

---

## SCENE 5: Projects and Deployment (2:55–3:50)

**Automation**: Semi-automatable — navigation is scriptable; the deploy action requires a confirmation click

### Shot Description
Navigate to `/projects` in the web UI.

Show the projects list — at least 3 projects visible with their metadata: path, artifact count, last sync timestamp.

Click on a project to open its detail view or dialog.

### Key Interactions to Perform
1. Show the project detail — deployed artifacts list, project path
2. Navigate back, then open a collection artifact
3. In the artifact detail modal, find the "Deploy" action
4. Trigger the deploy flow — show the project selector dialog
5. Complete the deploy

### Narration
"Deployment connects your collection to your active projects.

Here are the projects SkillMeat is tracking — each one a live engagement directory. I can see which artifacts are deployed to which project, and whether they are current.

When I want to deploy the code-reviewer agent to the insurance claims project..."

**Trigger the deploy flow.**

"...I select the artifact, choose the project, and choose the scope — global to my entire Claude Code setup, or local to just this project.

SkillMeat writes the artifact to the correct `.claude/` directory structure and registers the deployment. Now the team working on that project has access to this agent, and SkillMeat knows it's there."

**Show the deployment registered in the projects view.**

"This is how you go from 'someone has a good agent somewhere' to 'every project has access to the right artifacts, versioned and tracked.'"

### Timing: ~0:55
### Emotion: Control, governance

---

## SCENE 6: Sync and Drift Detection (3:50–4:50)

**Automation**: Semi-automatable — the diff viewer and 3-way comparison are the key visuals; navigate to /manage

### Shot Description
Navigate to `/manage` (Health & Sync in the nav).

Show the artifact list with sync status indicators. At least one artifact should show a non-synced state (outdated, modified, or conflict badge).

### Key Interactions to Perform
1. Show the status filter tabs at the top — click "Outdated" to filter to drifted artifacts
2. Click on an outdated artifact to open the Operations Modal
3. Switch to the "Sync" tab in the modal
4. Show the 3-way comparison: Source vs Collection vs Project
5. Show the diff viewer — unified diff with additions/deletions highlighted in green/red
6. Briefly show the merge workflow trigger

### Narration
"This is where SkillMeat earns its place in a production agentic workflow.

Artifacts drift. Upstream sources get updated. Someone modifies a deployed skill locally. Projects fall out of sync with each other.

The Health and Sync view gives you a continuous audit of your entire artifact estate.

This artifact is outdated — the upstream GitHub source has moved ahead of what I have in my collection."

**Click through to the sync/diff view.**

"SkillMeat gives me a three-way diff: the upstream source, my collection version, and what is actually deployed in the project.

I can see exactly what changed — additions in green, removals in red, line by line.

And when I am ready to take the update, the merge workflow walks me through resolving any local modifications before applying the change."

**Briefly trigger the merge workflow to show it exists.**

"This is version control for AI capabilities. The same discipline you apply to code, applied to the instructions that drive your agents."

### Timing: ~1:00
### Emotion: Confidence, governance, rigor

---

## SCENE 7: Memory System (4:50–5:45)

**Automation**: Semi-automatable — navigate to /memories; show filter interactions

### Shot Description
Navigate to `/memories` in the nav (under Projects section).

Show the memories list — items grouped by project, with type badges (`decision`, `gotcha`, `constraint`, `learning`), confidence scores, and content previews.

### Key Interactions to Perform
1. Show the memories list with the project grouping
2. Filter to one project
3. Click on a memory item to open its detail view
4. Show the `content` field — a specific technical decision or gotcha captured in prose
5. Show the `anchors` — links to the specific files the memory relates to
6. Briefly show the Context Pack Generator (if accessible) — the idea of loading relevant memories before a task

### Narration
"The memory system addresses a problem that every team running long-running agentic workflows hits: institutional knowledge evaporates between sessions.

Claude Code agents are stateless by default. Each session starts fresh. The patterns your team discovered, the gotchas you hit, the decisions you made — none of that survives the context window.

SkillMeat's memory system is a persistent knowledge store for your projects."

**Click on a memory item.**

"This is a `gotcha` memory — something the agent discovered during implementation that would be expensive to rediscover. It is anchored to the specific file where it applies, tagged with the confidence level, and versioned to the commit where it was captured.

Before any substantial task, an agent can query the memory system: load everything relevant to what I am about to do. That context pack gets injected at session start.

Your team's hard-won knowledge becomes reusable infrastructure."

### Timing: ~0:55
### Emotion: Insight, institutional value

---

## SCENE 8: The Bigger Picture — Agentic SDLC (5:45–6:30)

**Automation**: Fully automatable — browser screenshots of dashboard + CLI, can be a GIF or slideshow

### Shot Description
Return to the Dashboard. Show the full view with analytics populated.

Then cut to a side-by-side: terminal on the left running `skillmeat status`, browser on the right showing the Dashboard.

### Terminal Command
```bash
skillmeat status
```

Show the rich output: collection summary, project count, artifact counts by type, outdated count, last sync timestamp.

### Narration
"Here is what this means for an IBM Consulting Agentic SDLC practice.

Your team builds Claude Code skills and agents to encode your delivery patterns — code review, architecture analysis, test generation, documentation. These are your AI capabilities.

SkillMeat is the infrastructure layer that makes those capabilities manageable at scale.

Every artifact versioned. Every deployment tracked. Every piece of institutional knowledge persisted. Every drift detected before it causes an incident.

The `skillmeat status` command gives you the health of your entire AI capability estate in two seconds."

**Pause on the status output.**

"This is what artifact-as-code looks like in practice. The same rigor you apply to your software delivery pipeline, applied to the AI capabilities that are increasingly driving it."

### Timing: ~0:45
### Emotion: Strategic clarity, confidence

---

## SCENE 9: Call to Action (6:30–7:00)

**Automation**: Manual — this should be conversational, not scripted-feeling

### Shot Description
Return to browser. Navigate back to the collection view — the full artifact grid. This is the "abundance" shot: a rich, organized library of capabilities.

### Narration
"SkillMeat is available now.

If your team is already using Claude Code for agentic workflows, you can drop SkillMeat in alongside your existing setup with a single `skillmeat init`.

We would like to work with two or three IBM Consulting teams to run a structured pilot — bring your artifact sprawl problem and we will show you how to operationalize it.

The ask is simple: if you have a project where AI artifact management is becoming a pain point, let's talk."

### Timing: ~0:30
### Emotion: Invitation, momentum

---

## Full Scene Summary

| Scene | Title | Timing | Duration | Automation |
|-------|-------|--------|----------|------------|
| 1 | The Problem | 0:00 | 0:45 | Manual (terminal) |
| 2 | Solution Introduction | 0:45 | 0:30 | Fully automatable |
| 3 | The Collection | 1:15 | 0:55 | Semi-automatable |
| 4 | CLI — Adding Artifacts | 2:10 | 0:45 | Semi-automatable |
| 5 | Projects and Deployment | 2:55 | 0:55 | Semi-automatable |
| 6 | Sync and Drift Detection | 3:50 | 1:00 | Semi-automatable |
| 7 | Memory System | 4:50 | 0:55 | Semi-automatable |
| 8 | The Bigger Picture | 5:45 | 0:45 | Fully automatable |
| 9 | Call to Action | 6:30 | 0:30 | Manual |
| **Total** | | | **~7:00** | |

---

## Automation Assessment Detail

### Fully Automatable Scenes (can use GIF recorder + browser automation)
- **Scene 2**: Dashboard load + stats card hover
- **Scene 8**: Dashboard + split-screen with terminal output

**How**: Use the claude-in-chrome GIF recorder. Navigate to `localhost:3000`, take a screenshot immediately after the recorder starts to capture the initial frame. Add hover interactions over stats cards. Stop recording and export.

### Semi-Automatable Scenes
- **Scene 3** (Collection): Navigation click is automatable; the hover-reveal of the action menu is manual
- **Scene 4** (CLI): Terminal commands must be typed live but can be pre-staged in a script; the browser refresh to show the new artifact is automatable
- **Scene 5** (Deployment): Navigation automatable; the deploy confirmation dialog requires a manual click
- **Scene 6** (Sync): Navigation and filter clicks are automatable; scrolling through the diff viewer is manual
- **Scene 7** (Memories): Navigation and filter automatable; clicking a memory item and reading its content is manual

**Recommended approach**: Record each semi-automatable scene in a single continuous take. Do not attempt to stitch browser automation with live typing — the seams are visible. Use the GIF recorder for the browser portions and a separate terminal recording tool for CLI scenes.

### Manual Scenes
- **Scene 1**: Live terminal interaction — no shortcuts here; the "pile of files" visual needs to feel authentic
- **Scene 9**: Live narration — keep it conversational, not scripted

---

## Production Notes

### Screen and Window Setup
- **Resolution**: 1920x1080 recording, scaled to 1440x900 browser window
- **Browser**: Chrome, zoom 100%, bookmarks bar hidden, no extensions visible
- **Terminal**: iTerm2 or Warp, dark theme, 18pt font, full black background
- **Padding**: Leave 20px margin around the browser/terminal so nothing is cropped in compression

### Speed and Pacing
- **Web UI interactions**: Do not rush clicks. Pause 1–2 seconds on each meaningful screen state before moving on.
- **Terminal output**: Let the Rich formatted output fully render before cutting. The color formatting is part of the visual.
- **Diff viewer**: Scroll slowly through the diff — this is a key visual and viewers need time to read it.
- **Post-processing**: Add 1.5x speed to any loading states or transitions. Do not speed up narration or meaningful interactions.

### What to Avoid
- Do not show any real API keys, tokens, or credentials in the terminal
- Do not show error states or loading failures — stage with a healthy environment
- Avoid scrolling through the nav sidebar rapidly — the section labels are part of the story
- Do not show empty states (zero artifacts, no projects) — stage with realistic data first

### Voice-over Recording
- Record narration separately from screen capture
- Use a consistent room and microphone setup for all scenes
- Aim for a measured, consultative tone — not a sales pitch cadence
- Allow 0.5–1 second of silence at the start and end of each narration clip for editing headroom

### Post-Production Assembly Order
1. Scene 1 (terminal) — opens cold, no intro card needed
2. Crossfade or hard cut to Scene 2 (browser dashboard)
3. Scenes 3–7: maintain browser continuity; cut between scenes at navigation clicks
4. Scene 8: brief split-screen — left panel terminal, right panel browser
5. Scene 9: return to collection view (rich, full library visible)
6. End on the collection grid — not a blank screen

### Thumbnail / Opening Frame
Use the Dashboard view with the analytics grid fully loaded and the green "Live updates active" dot visible. This communicates: production-ready, real-time, data-driven.

---

## Talking Points for Q&A (Not in the Video)

These are likely questions from the IBM Consulting audience. Prepare these for the live session.

**"How is this different from just using git submodules?"**
Git tracks files. SkillMeat tracks artifacts — with type-aware metadata, deployment scope, sync state, and runtime memory. Git has no concept of "this skill is deployed to 3 projects and one of them has local modifications." SkillMeat does.

**"Can this work with our internal GitHub Enterprise?"**
Yes. SkillMeat uses a centralized GitHub client that supports custom base URLs. Configure `skillmeat config set github-token` with a GHE token and it works against private repos.

**"What about artifacts that are specific to one client engagement?"**
The scope system handles this. `local` scope keeps artifacts in the project's `.claude/` directory — they never go into the global collection. `user` scope makes them available across all your projects. You can also have private collections that never touch a public registry.

**"How does the memory system interact with Claude Code's built-in memory?"**
Complementary. Claude Code's `CLAUDE.md` and project memory are session-oriented instructions. SkillMeat's memory system is a queryable, versioned, confidence-scored knowledge graph that persists across agents and sessions. The two work together — you can inject SkillMeat memory context into a `CLAUDE.md` dynamically.

**"What's the governance story — who controls what gets into the collection?"**
Currently: the individual developer controls their own collection. The marketplace layer (in development) adds organizational governance — admins can publish approved artifacts to a private registry that team members can pull from but not modify without review. This mirrors the npm private registry pattern.

---

## Appendix: Recommended Demo Data Setup

If your environment does not have sufficient data, use these commands to stage realistic artifacts:

```bash
# Initialize with the Claude Code profile
skillmeat init --profile claude_code

# Add production-quality skills
skillmeat add skill miethe/skillmeat/.claude/skills/dev-execution
skillmeat add skill miethe/skillmeat/.claude/skills/artifact-tracking
skillmeat add skill miethe/skillmeat/.claude/skills/planning

# Add agents
skillmeat add agent miethe/skillmeat/.claude/agents/code-reviewer
skillmeat add agent miethe/skillmeat/.claude/agents/ultrathink-debugger
skillmeat add agent miethe/skillmeat/.claude/agents/codebase-explorer

# Register demo projects
# (Use actual project paths on your machine)
skillmeat project register /path/to/agentic-sdlc-pilot
skillmeat project register /path/to/insurance-claims-bot
skillmeat project register /path/to/code-review-pipeline

# Deploy a skill to one project to show deployment state
skillmeat deploy dev-execution --project /path/to/agentic-sdlc-pilot

# Verify staging
skillmeat status
skillmeat list
```

To create memory items for the demo (use the API endpoint directly for reliability):
```bash
curl -s "http://localhost:8080/api/v1/memory-items?project_id=YOUR_PROJECT_ID" \
  -X POST -H "Content-Type: application/json" -d '{
  "type": "gotcha",
  "content": "Phase execution agents require the artifact-tracking skill to be loaded before they can update progress YAML. Missing this causes silent failures where task status never updates.",
  "confidence": 0.92,
  "status": "active",
  "anchors": [".claude/skills/artifact-tracking/SKILL.md:plan"]
}'
```
