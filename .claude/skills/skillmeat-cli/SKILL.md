---
name: skillmeat-cli
description: |
  Manage SkillMeat and Claude Code environments through natural language.
  Use this skill when users want to:
  - discover, add, deploy, or manage Claude Code artifacts
  - manage Memory & Context features (memory items, modules, context packs)
  - automate pre-run context generation and post-run memory capture
  - navigate project and memory workflows in CLI/web/API
  Supports both current commands and planned `skillmeat memory ...` CLI flows.
---

# SkillMeat CLI Skill

Natural language interface for SkillMeat operations, including artifact management and Memory & Context workflows.

## Core Operating Principle

When memory features are requested, prefer the `skillmeat memory ...` CLI surface.

If the command is unavailable in the current installation:
1. Detect this quickly (`skillmeat memory --help` or command failure).
2. Fall back to equivalent API endpoints.
3. Tell the user you used API fallback and why.

Do not pretend unavailable CLI commands succeeded.

---

## Main Capability Areas

- Artifact discovery/deployment (`search`, `add`, `deploy`, `sync`, `bundle`, etc.)
- Memory item lifecycle management
- Context module composition
- Context pack preview/generation
- Auto-extraction preview/apply from run artifacts
- Project/global memory visibility workflows

---

## Memory Command Model (Target)

### Item Lifecycle

```bash
skillmeat memory item create --project <project> --type decision --content "..."
skillmeat memory item list --project <project> --status candidate
skillmeat memory item show <item-id>
skillmeat memory item update <item-id> --confidence 0.9
skillmeat memory item promote <item-id> --reason "validated"
skillmeat memory item deprecate <item-id> --reason "superseded"
skillmeat memory item merge --source <id> --target <id> --strategy combine
skillmeat memory item bulk-promote --ids <id1,id2>
```

### Module Composition

```bash
skillmeat memory module create --project <project> --name "API Debug"
skillmeat memory module list --project <project>
skillmeat memory module add-item <module-id> --item <item-id>
skillmeat memory module remove-item <module-id> --item <item-id>
```

### Pack Consumption

```bash
skillmeat memory pack preview --project <project> --module <module-id> --budget 4000 --json
skillmeat memory pack generate --project <project> --module <module-id> --output ./context-pack.md
```

### Auto-Extraction

```bash
skillmeat memory extract preview --project <project> --run-log ./run.log
skillmeat memory extract apply --project <project> --run-log ./run.log
```

### Search

```bash
skillmeat memory search "oauth timeout" --project <project>
skillmeat memory search "postgres lock" --all-projects
```

---

## API Fallback Map (When CLI Memory Commands Are Missing)

- Item CRUD/lifecycle/merge:
  - `/api/v1/memory-items`
  - `/api/v1/memory-items/{id}/promote`
  - `/api/v1/memory-items/{id}/deprecate`
  - `/api/v1/memory-items/merge`
- Module management:
  - `/api/v1/context-modules`
- Pack operations:
  - `/api/v1/context-packs/preview`
  - `/api/v1/context-packs/generate`

Use project scoping explicitly (`project_id` query) to avoid cross-project mistakes.

---

## Agent Workflows

## 1) Pre-Run Context Consumption

When user starts a substantial task:

1. Determine project scope.
2. Preview memory pack for relevant module.
3. If utilization is poor, adjust filters/budget.
4. Generate pack and provide/attach result.

Prompt pattern:
- "I can generate a context pack from your active memories before we start."

## 2) Post-Run Memory Capture

After significant implementation/debugging:

1. Offer extraction from run notes/logs.
2. Create candidates only.
3. Route user to triage (or summarize candidates in CLI).

Prompt pattern:
- "I can extract candidate memories from this run and queue them for review."

## 3) Triage Loop

- Promote high-confidence validated learnings.
- Deprecate stale/incorrect entries.
- Merge near-duplicates with explicit confirmation.

---

## Permission & Safety Protocol

- Ask before mutating memory state in bulk.
- Ask before applying extraction (preview can run without mutation).
- For merges, show source/target and selected strategy before execution.
- Never auto-promote extracted candidates in unattended mode.

---

## Suggestion Guidelines

Use concise value framing:

```
This workflow can benefit from Memory Context.
I can:
1) generate a pack for this task,
2) run capture after completion,
3) leave extracted items in candidate status for review.
Proceed?
```

---

## Quick Checks

Before memory operations:

```bash
skillmeat --version
skillmeat memory --help
```

If memory commands unavailable, switch to API fallback and state it.

---

## Related References

- `./references/command-quick-reference.md`
- `./references/agent-integration.md`
- `./workflows/memory-context-workflow.md`
