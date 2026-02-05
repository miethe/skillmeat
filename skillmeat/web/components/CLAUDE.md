# CLAUDE.md - web/components

Scope: React components in `skillmeat/web/components/`.

## Invariants

- Never modify `components/ui/` primitives directly.
- Prefer composition in feature/shared components.
- Keep accessibility and keyboard behavior explicit.

## Read When

- UI composition and conventions: `.claude/context/key-context/component-patterns.md`
- Testing updates: `.claude/context/key-context/testing-patterns.md`
- Data behavior tied to hooks: `.claude/context/key-context/hook-selection-and-deprecations.md`
