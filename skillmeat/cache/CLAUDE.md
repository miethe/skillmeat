# CLAUDE.md - cache

Scope: DB cache models, repositories, refresh/sync in `skillmeat/cache/`.

## Invariants

- DB cache is the web runtime source for listable data.
- Preserve write-through + refresh semantics between filesystem and DB.
- Schema/migration changes require compatibility checks.

## Read When

- Cache/write-through model: `.claude/context/key-context/data-flow-patterns.md`
- FE/BE consistency work: `.claude/context/key-context/fe-be-type-sync-playbook.md`
