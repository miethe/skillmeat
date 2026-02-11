# CLAUDE.md - api/routers

Scope: FastAPI endpoint handlers in `skillmeat/api/routers/`.

## Invariants

- Routers define HTTP surface and delegate business logic.
- Keep status codes and error behavior explicit and consistent.
- Do not make routers the source of contract truth; OpenAPI is canonical.
- Every import/mutation endpoint must call `refresh_single_artifact_cache()` after filesystem writes.

## Read When

- Router conventions: `.claude/context/key-context/router-patterns.md`
- Contract checks: `.claude/context/key-context/api-contract-source-of-truth.md`
- Discovery and impact: `.claude/context/key-context/symbols-query-playbook.md`
- Marketplace import/source flows: `.claude/context/key-context/marketplace-import-flows.md`
