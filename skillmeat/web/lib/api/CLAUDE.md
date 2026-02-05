# CLAUDE.md - web/lib/api

Scope: Frontend API clients and mappers in `skillmeat/web/lib/api/`.

## Invariants

- Align endpoint behavior with `skillmeat/api/openapi.json`.
- Keep transport concerns in API client layer; avoid UI logic here.
- Preserve mapper compatibility for backend field evolution.

## Read When

- Contract verification: `.claude/context/key-context/api-contract-source-of-truth.md`
- FE/BE type alignment: `.claude/context/key-context/fe-be-type-sync-playbook.md`
- Cross-layer tracing: `.claude/context/key-context/symbols-query-playbook.md`
