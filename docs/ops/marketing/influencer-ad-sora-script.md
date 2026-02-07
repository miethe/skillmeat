# Influencer Ad Script: SkillMeat for Sora

**Date**: 2026-02-07
**Author**: GPT-5.3-Codex
**Target**: Sora

**20–45s Script (Approx. 34s)**

1. `0:00–0:05`
Narration: “Your AI workflow is powerful, but your artifacts are scattered.”
On-screen text: “Skills. Commands. Agents. MCP. Everywhere.”

2. `0:05–0:10`
Narration: “SkillMeat gives you one control layer across projects.”
On-screen text: “One source of truth for Claude Code artifacts.”

3. `0:10–0:16`
Narration: “Deploy fast. Track drift. Sync changes without losing local edits.”
On-screen text: “`deploy` • `sync-check` • `sync-pull`”

4. `0:16–0:22`
Narration: “And when updates go sideways, snapshot and roll back in seconds.”
On-screen text: “Safety-first: `snapshot` → `rollback`”

5. `0:22–0:29`
Narration: “Run MCP servers, manage memory items, generate context packs.”
On-screen text: “MCP + Memory + Context Packs”

6. `0:29–0:34`
Narration: “If you’re building serious agent workflows, this is the operating layer.”
On-screen text (single CTA): “Run `skillmeat init` and deploy your first shared artifact.”

**Shot List (6 shots)**

1. Glitchy split-screen of multiple repos and `.claude` folders; quick zooms and jitter cuts; text: “Fragmented AI workflows.”
2. Clean terminal-to-dashboard transition; camera dolly-in from CLI output to web cards; text: “Centralize once.”
3. Diff-heavy sync sequence; side-by-side collection vs project with highlighted drift; text: “See drift. Sync with intent.”
4. Timeline UI with “Snapshot created” then controlled reverse animation to “Rollback complete”; text: “Ship faster, recover faster.”
5. MCP panel + memory/module/pack UI montage; smooth parallax and card reveals; text: “Operational depth, not just storage.”
6. Hero lockup with product name and one button-style command; slow push-in, hold; text: “`skillmeat init`”.

**Safe Claims (Repo-grounded)**

- SkillMeat is positioned as a manager for skills/commands/agents/hooks/MCP across projects with CLI + web interface.
Evidence: `/Users/miethe/.codex/worktrees/280b/skillmeat/README.md:15`, `/Users/miethe/.codex/worktrees/280b/skillmeat/README.md:45`
- Snapshot and rollback are implemented CLI commands.
Evidence: `/Users/miethe/.codex/worktrees/280b/skillmeat/skillmeat/cli.py:2270`, `/Users/miethe/.codex/worktrees/280b/skillmeat/skillmeat/cli.py:2370`
- Drift/sync flows are implemented (`sync-check`, `sync-pull`, `sync-preview`) with rollback option in sync pull.
Evidence: `/Users/miethe/.codex/worktrees/280b/skillmeat/skillmeat/cli.py:5675`, `/Users/miethe/.codex/worktrees/280b/skillmeat/skillmeat/cli.py:5853`, `/Users/miethe/.codex/worktrees/280b/skillmeat/skillmeat/cli.py:6016`
- MCP lifecycle is implemented in CLI (add/deploy/undeploy/list/health) and API routers include MCP endpoints.
Evidence: `/Users/miethe/.codex/worktrees/280b/skillmeat/skillmeat/cli.py:1436`, `/Users/miethe/.codex/worktrees/280b/skillmeat/skillmeat/cli.py:1450`, `/Users/miethe/.codex/worktrees/280b/skillmeat/skillmeat/api/server.py:356`
- Memory workflows are implemented in CLI (item/module/pack/extract groups) and mounted in API.
Evidence: `/Users/miethe/.codex/worktrees/280b/skillmeat/skillmeat/cli.py:11606`, `/Users/miethe/.codex/worktrees/280b/skillmeat/skillmeat/cli.py:12043`, `/Users/miethe/.codex/worktrees/280b/skillmeat/skillmeat/api/server.py:372`

**Assumptions (Labeled)**

- `A1`: “Native multi-platform deployment profiles” are not claimed as shipped; that plan is draft.
Evidence: `/Users/miethe/.codex/worktrees/280b/skillmeat/docs/project_plans/implementation_plans/features/multi-platform-project-deployments-v1.md:9`
- `A2`: Current cross-platform story in this concept treats the symlink adapter script as the present capability.
Evidence: `/Users/miethe/.codex/worktrees/280b/skillmeat/scripts/setup_agent_platform_links.sh:114`
- `A3`: Quant counts used for framing were repo-snapshot checks (23 web pages, ~158 `/api/v1` paths, ~148 CLI command/group decorators), not live runtime telemetry.
