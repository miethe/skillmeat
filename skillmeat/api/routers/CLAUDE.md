# CLAUDE.md - api/routers

Scope: FastAPI endpoint handlers in `skillmeat/api/routers/`.

## Invariants

- Routers define HTTP surface and delegate business logic.
- Keep status codes and error behavior explicit and consistent.
- Do not make routers the source of contract truth; OpenAPI is canonical.
- Every mutation endpoint must sync the DB cache after filesystem writes — use `refresh_single_artifact_cache()` for general mutations or `populate_collection_artifact_from_import()` for marketplace imports (both delegate to `create_or_update_collection_artifact()`).
- **Artifact ID Resolution (ADR-007)**: Path parameter `artifact_id` arrives as `type:name` (e.g., `skill:frontend-design`). Services/repositories expect `artifact_uuid` (hex UUID). Routers must resolve via `Artifact.filter_by(id=artifact_id).first()` → use `db_art.uuid` for downstream calls.

## Read When

- Router conventions: `.claude/context/key-context/router-patterns.md`
- Contract checks: `.claude/context/key-context/api-contract-source-of-truth.md`
- Discovery and impact: `.claude/context/key-context/symbols-query-playbook.md`
- Marketplace import/source flows: `.claude/context/key-context/marketplace-import-flows.md`
