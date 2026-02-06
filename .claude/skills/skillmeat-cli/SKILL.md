---
name: skillmeat-cli
description: |
  Manage SkillMeat and Claude Code environments through natural language.
  Use this skill for artifact discovery/deployment/management, bundles,
  MCP and context entity operations, and Memory & Context workflows.
  This skill uses progressive disclosure: load only the specific workflow or
  reference docs needed for the current user request.
---

# SkillMeat CLI Skill

High-level orchestrator for SkillMeat capabilities.

This file is intentionally concise. Use it to route to focused docs in
`references/` and `workflows/` based on user intent.

## Progressive Disclosure Rules

1. Start from user intent, not from command memorization.
2. Open only the minimal docs needed for the task.
3. Do not load every workflow file by default.
4. Prefer one primary workflow doc plus one reference doc when needed.
5. If memory CLI commands are unavailable, fall back to API equivalents and
   state that fallback explicitly.

Use routing map:
- `./references/capability-router.md`

## Capability Coverage

This skill covers:

- Artifact discovery and recommendations
- Artifact deployment and update management
- Collection and sync operations
- Bundle create/import/sign/inspect workflows
- MCP and context entity command usage
- Confidence scoring, context boosting, gap detection
- Caching/performance-aware operation
- Error handling and recovery patterns
- Memory & Context workflows (item/module/pack/extract/search)

## Intent Routing

When a request arrives, route it first:

1. Capability discovery/search/recommendation:
- Open `./workflows/discovery-workflow.md`
- Optional: `./workflows/gap-detection.md`

2. Deploy/add artifact to project:
- Open `./workflows/deployment-workflow.md`

3. Inspect/update/remove/sync artifacts:
- Open `./workflows/management-workflow.md`

4. Share/import setups and signing:
- Open `./workflows/bundle-workflow.md`

5. Confidence/context-aware recommendation logic:
- Open `./workflows/context-boosting.md`
- Optional: `./workflows/confidence-integration.md`

6. Memory capture/consumption flows:
- Open `./workflows/memory-context-workflow.md`
- Optional: `./references/agent-integration.md` (integration pattern)

7. CLI command syntax quick lookup:
- Open `./references/command-quick-reference.md`

8. Troubleshooting failures:
- Open `./workflows/error-handling.md`

9. claudectl alias behavior/setup:
- Open `./references/claudectl-setup.md`

## Memory & Context Handling Policy

When user asks for memory operations:

1. Prefer target CLI surface:
- `skillmeat memory item ...`
- `skillmeat memory module ...`
- `skillmeat memory pack ...`
- `skillmeat memory extract ...`
- `skillmeat memory search ...`

2. Verify availability quickly:
```bash
skillmeat memory --help
```

3. If unavailable, use API fallback and explain:
- `/api/v1/memory-items`
- `/api/v1/context-modules`
- `/api/v1/context-packs/preview`
- `/api/v1/context-packs/generate`

4. Safety defaults:
- Keep extracted memories as `candidate`
- Do not auto-promote extracted items
- Confirm before bulk/deprecate/merge operations

## Permission Protocol

For mutating actions, require explicit user confirmation:

- Deploying artifacts
- Bulk updates/removals
- Memory extraction apply
- Memory merges and bulk lifecycle changes

Allowed without extra confirmation (read-only):

- Search/list/show/preview commands
- Diagnostics and health checks

## Output Expectations

- Be explicit about what command/action is being taken.
- Report important command results clearly and briefly.
- When using fallback paths, state fallback reason in one sentence.
- Keep recommendations concrete and tied to current task context.

## Recommended Starting Point

For most tasks:

1. Open `./references/capability-router.md`
2. Select one primary workflow file
3. Execute and report results
