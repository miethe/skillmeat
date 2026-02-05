# CLAUDE.md - web/hooks

Scope: Query/mutation hooks in `skillmeat/web/hooks/`.

## Invariants

- `skillmeat/web/hooks/index.ts` is the canonical import surface.
- Define stable query keys and explicit invalidation.
- Use domain stale times from data-flow guidance.

## Read When

- Hook choice/deprecations: `.claude/context/key-context/hook-selection-and-deprecations.md`
- Cache behavior: `.claude/context/key-context/data-flow-patterns.md`
- Discovery/impact analysis: `.claude/context/key-context/symbols-query-playbook.md`
