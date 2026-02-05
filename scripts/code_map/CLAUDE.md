# CLAUDE.md - scripts/code_map

Scope: code mapping and graph/symbol maintenance scripts.

## Invariants

- Mapping artifacts must point to real files and current schemas.
- Prefer one supported schema/version per maintained artifact type.
- Treat generated artifacts as runtime aids; regenerate when stale.

## Read When

- Symbol workflows: `.claude/context/key-context/symbols-query-playbook.md`
- Graph usage policy: `.claude/context/key-context/codebase-map-query-playbook.md`
