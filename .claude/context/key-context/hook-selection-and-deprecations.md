# Hook Selection and Deprecations

Canonical guidance for choosing hooks and handling deprecated patterns.

## Source of Truth

1. `skillmeat/web/hooks/index.ts` (canonical imports).
2. Hook implementation files in `skillmeat/web/hooks/`.
3. `ai/symbols-web.json` for discovery.

## Selection Rules

- Import hooks from `@/hooks` only.
- Reuse existing domain hook before adding new one.
- New hooks must declare stable query keys and invalidation behavior.
- Keep stale times aligned with `data-flow-patterns.md`.

## Deprecation Workflow

1. Mark the hook/type/endpoints in `deprecation-and-sunset-registry.md`.
2. Document replacement and migration deadline.
3. Update references in `skillmeat/web/CLAUDE.md` and affected local `CLAUDE.md` entry files.
4. Remove deprecated path after deadline when references are zero.
