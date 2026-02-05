# CLAUDE.md - api/services

Scope: Backend service-layer logic in `skillmeat/api/services/`.

## Invariants

- Services own business orchestration and policy decisions.
- Keep transport-specific concerns out of services.
- Maintain clear inputs/outputs for router integration.

## Read When

- Router to service boundaries: `.claude/context/key-context/router-patterns.md`
- Debugging cross-layer flows: `.claude/context/key-context/debugging-patterns.md`
