---
title: Memory & Context Intelligence Guide
description: Overview of Memory Inbox, Context Modules, and context pack generation workflows
audience: [users]
tags: [memory, context, triage, modules, context-pack]
created: 2026-02-06
updated: 2026-02-06
category: user-guide
status: published
related:
  - /docs/user/guides/memory-inbox.md
  - /docs/user/guides/context-modules.md
  - /docs/project_plans/PRDs/features/memory-context-system-v1.md
---

# Memory & Context Intelligence Guide

SkillMeat's Memory & Context Intelligence System helps you capture project knowledge, review it quickly, and build reusable context packs for future agent runs.

## What You Can Do

- Triage candidate memories in a keyboard-first inbox (`/projects/[id]/memory`)
- Promote important memories from `candidate` to `active` to `stable`
- Deprecate stale or incorrect memories with reason tracking
- Build reusable context modules with selector rules
- Preview and generate token-budgeted context packs
- Run memory workflows from CLI (`skillmeat memory ...`)
- Extract candidate memories from run logs (`extract preview/apply`)

## Core Concepts

- **Memory item**: A single piece of project knowledge (`decision`, `constraint`, `gotcha`, `style_rule`, `learning`)
- **Lifecycle status**: `candidate`, `active`, `stable`, `deprecated`
- **Context module**: A named set of selector rules for building context
- **Context pack**: The generated output that combines selected memories within a token budget

## Typical Workflow

1. Review new candidates in Memory Inbox and approve high-value items.
2. Edit confidence or content where needed.
3. Create one or more context modules (for example: API work, debugging, release checks).
4. Preview generated packs and adjust selectors.
5. Use generated packs in agent workflows.

## Guides

- [Memory Inbox User Guide](./memory-inbox.md)
- [Working with Context Modules](./context-modules.md)
- [Web UI Guide](./web-ui-guide.md)

## API Surfaces

- `GET/POST/PUT/DELETE /api/v1/memory-items`
- `GET /api/v1/memory-items/search`
- `GET /api/v1/memory-items/global`
- `POST /api/v1/memory-items/{id}/promote`
- `POST /api/v1/memory-items/{id}/deprecate`
- `POST /api/v1/memory-items/merge`
- `POST /api/v1/memory-items/extract/preview`
- `POST /api/v1/memory-items/extract/apply`
- `GET/POST/PUT/DELETE /api/v1/context-modules`
- `POST /api/v1/context-packs/preview`
- `POST /api/v1/context-packs/generate`

Use the full API schema in `skillmeat/api/openapi.json` for request and response details.
