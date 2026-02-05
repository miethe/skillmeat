# CLAUDE.md - web/app

Scope: Next.js App Router pages/layouts in `skillmeat/web/app/`.

## Invariants

- Default to server components.
- Add `'use client'` only where client interactivity is required.
- Keep route-level data loading and layout concerns in app layer.

## Read When

- Route/page behavior: `.claude/context/key-context/nextjs-patterns.md`
- Cache/query behavior: `.claude/context/key-context/data-flow-patterns.md`
- Cross-layer tracing: `.claude/context/key-context/symbols-query-playbook.md`
