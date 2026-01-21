# Codebase Graph Expansion Plan

Purpose: expand the Layer 0 graph defined in `docs/architecture/codebase-graph-spec.md`
to cover the full app, preserve key metadata, and enable end-to-end flow mapping
across frontend and backend.

This plan follows the roadmap in the spec and aligns with the layered mapping
recommendations in `docs/project_plans/reports/agentic-code-mapping-recommendations-2026-01-10.md`.

## Goals

- Map complete user flow paths: route -> page -> component -> hook -> api client
  -> endpoint -> handler -> service -> repository -> model -> db/migrations.
- Preserve provenance and metadata from source code (file, symbol, line, docstring,
  owner, canonical/deprecated, introduced_in, replaces).
- Produce a unified, diffable graph for CI checks, agent guidance, and docs output.
- Keep extraction incremental and maintainable (small, composable extractors).

## Guiding Principles

- Stable IDs: use deterministic IDs derived from file paths and symbols.
- Separate facts from annotations: extraction stays pure; overrides add semantics.
- Cross-layer linkage is explicit: no implicit inference in downstream consumers.
- Coverage is measurable: each phase adds nodes/edges + validation checks.

## Repo Anchors (Current)

Use these paths as starting points and update if the structure changes:

- Frontend root: `skillmeat/web`
  - Routes/pages: `skillmeat/web/app/**/page.tsx`
  - Components: `skillmeat/web/components/**`, plus components imported in `app/`
  - Hooks: `skillmeat/web/hooks/**`
  - API client helpers: `skillmeat/web/lib/api/**`, `apiRequest` usage
  - Types: `skillmeat/web/types/**`
- Backend root: `skillmeat/api`
  - Routers: `skillmeat/api/routers/**`
  - OpenAPI: `skillmeat/api/openapi.py`, generated `skillmeat/api/openapi.json`
  - Schemas: `skillmeat/api/schemas/**`
  - Services: `skillmeat/api/services/**`
- Core domain/services: `skillmeat/core/**`
- Repository layer (current): `skillmeat/cache/repositories.py`, `skillmeat/cache/repository.py`
- Migrations: `skillmeat/cache/migrations/versions/**`
- Storage helpers (often data access): `skillmeat/storage/**`

## Target Flow Map (Canonical Paths)

Frontend to backend:
- `route` -> `page` -> `component` -> `hook` -> `api_client` -> `api_endpoint`

Backend to data:
- `api_endpoint` -> `handler` -> `service` -> `repository` -> `model` -> `migration`

Cross-cutting:
- `schema` and `type` nodes connect to both FE and BE constructs.
- `job`/`cli_command` nodes map non-HTTP entry points into services/repositories.

## Schema Extensions (v1)

New node types:
- frontend: `component`, `api_client`, `query_key`, `type`, `schema`
- backend: `service`, `repository`, `model`, `migration`, `schema`, `job`
- platform: `cli_command`, `config`, `env_var`

New edge types:
- `page_uses_component`, `component_uses_hook`, `hook_calls_api_client`
- `api_client_calls_endpoint`, `handler_calls_service`, `service_calls_repository`
- `repository_uses_model`, `model_migrated_by`
- `handler_uses_schema`, `schema_maps_type`, `cli_invokes_service`

Metadata additions (optional per node/edge):
- `symbol`, `line`, `signature`, `doc_hash`
- `owner`, `canonical`, `deprecated`, `introduced_in`, `replaces`
- `layer` (frontend/backend), `module`, `package`, `tags`

## ID, Label, and Metadata Conventions

Use consistent IDs so graphs can merge safely:

- `route:/path` (label is `/path`)
- `page:skillmeat/web/app/.../page.tsx` (label optional)
- `component:skillmeat/web/components/Button.tsx::Button`
- `hook:skillmeat/web/hooks/useFoo.ts::useFoo`
- `api_client:skillmeat/web/lib/api/foo.ts::getFoo`
- `query_key:["foo", "bar"]` (label is JSON string of key)
- `api_endpoint:METHOD /path`
- `router:skillmeat/api/routers/foo.py::router`
- `handler:skillmeat/api/routers/foo.py::get_foo`
- `service:skillmeat/api/services/foo.py::FooService`
- `repository:skillmeat/cache/repositories.py::MarketplaceSourceRepository`
- `schema:skillmeat/api/schemas/foo.py::FooRequest`
- `model:skillmeat/cache/repositories.py::MarketplaceSource` (or `skillmeat/models.py::Name`)
- `migration:skillmeat/cache/migrations/versions/xxxx.py::revision_id`
- `cli_command:scripts/whatever.py::command_name`

Required fields per node:
- Always include `id`, `type`, `label` (where human-readable), and `file` if known.
- Add `symbol` and `line` when a parser can provide it.

Root metadata (add at top-level in JSON):
```json
{
  "source": "unified",
  "schema_version": "v1",
  "generated_at": "2026-01-12T10:00:00Z",
  "source_commit": "abc123",
  "nodes": [],
  "edges": []
}
```

## Agent Instructions (Low-Reasoning Safe Defaults)

If a parser cannot resolve a link:
- Still create the node with `file` and `label`.
- Skip the edge and log a warning to stdout (do not crash).
- Add TODO notes in the coverage summary script for missing links.

## Expansion Phases

### Phase 0: Stabilize + Unify (Baseline)

Why: create a reliable foundation before adding coverage.

Deliverables:
- `scripts/code_map/merge_graphs.py` to combine FE + BE into a unified graph.
- `docs/architecture/codebase-graph.overrides.yaml` for canonical/deprecated/owner.
- Add `source_commit`, `generated_at`, and `schema_version` to graph root metadata.
- Coverage summary script (node/edge counts by type, missing link detection).

Step-by-step tasks:
1) Implement `scripts/code_map/merge_graphs.py`
   - Inputs: `codebase-graph.frontend.json`, `codebase-graph.backend.json`
   - Output: `docs/architecture/codebase-graph.unified.json`
   - Logic: merge nodes by `id`, append all edges, keep `source="unified"`.
2) Implement `scripts/code_map/apply_overrides.py`
   - Reads unified graph + `docs/architecture/codebase-graph.overrides.yaml`.
   - Merges override metadata into matching nodes/edges by `id`.
3) Update `scripts/code_map/graph.py` (or merge script) to emit root metadata:
   - `schema_version` (string), `generated_at` (UTC ISO), `source_commit`.
4) Add `scripts/code_map/coverage_summary.py`
   - Prints counts by node type and edge type.
   - Prints missing links (example: hooks with zero `calls_api` edges).

Overrides file format (YAML):
```yaml
nodes:
  - id: hook:skillmeat/web/hooks/useDeploy.ts::useDeploy
    deprecated: true
    replaces: hook:skillmeat/web/hooks/use-deployments.ts::useDeployArtifact
    owner: web-platform
edges:
  - from: hook:...
    to: api_endpoint:POST /deploy
    canonical: true
```

Acceptance checks:
- Unified graph builds in one command.
- Overrides are applied without modifying raw extractor output.
 - Coverage summary reports counts without errors.

### Phase 1: Frontend Deep Mapping

Why: connect routes/pages to actual UI and hook usage.

Scope:
- Component usage graph (page -> component -> hook).
- API client mapping (hook -> api client -> endpoint).
- React Query key registration mapping.
- FE type/schema references (zod or types in `types/`).

Implementation notes:
- Use a TS/TSX-aware parser (ts-morph or SWC) for imports and JSX usage.
- Map hook usage from components, not only pages.
- Identify API client wrapper(s) (ex: `lib/api`, `apiRequest`) and treat them as
  `api_client` nodes.

Step-by-step tasks:
1) Component extraction (`extract_frontend_components.py`)
   - Scan `skillmeat/web/app/**/page.tsx` and `skillmeat/web/components/**`.
   - Parse imports and JSX to map `page -> component` and `component -> component`.
   - Add nodes: `component:<file>::<ComponentName>`.
   - Add edges: `page_uses_component`, `component_uses_component`.
2) Hook usage from components (`extract_frontend_hooks.py`)
   - Parse each TS/TSX file for `import { useX } from ...` or `useX(...)` usage.
   - Create `component_uses_hook` edges.
   - Always resolve hooks imported from `@/hooks` to actual files in `web/hooks`.
3) API client mapping (`extract_frontend_api_clients.py`)
   - Find `apiRequest` or `fetch` wrappers in `skillmeat/web/lib/api/**`.
   - Create `api_client` nodes for exported functions.
   - Add edges: `hook_calls_api_client`, `api_client_calls_endpoint`.
4) React Query key mapping
   - Find `useQuery`, `useInfiniteQuery`, `queryKey` assignments.
   - Create `query_key` nodes; edge `hook_registers_query_key`.
5) FE type/schema linking
   - Link hooks/components to types in `skillmeat/web/types/**` if imported.
   - Add `type` or `schema` nodes and `uses_type` edges.

Outputs:
- `codebase-graph.frontend.json` updated with new node/edge types.
- Cross-links between hooks and api clients.

Acceptance checks:
- Each page has at least one component (if any are used).
- Hooks referenced in components are captured.
- API clients used by hooks are mapped to endpoints.
 - Query keys are captured for any hook using React Query.

### Phase 2: Backend Source of Truth

Why: ensure backend endpoints and handlers are authoritative and complete.

Scope:
- OpenAPI-driven endpoints (replace regex-only parsing).
- Handler -> service -> repository graph via Python AST/import analysis.
- Schema mapping (Pydantic models, request/response schemas).
- Model/DB mapping (SQLAlchemy models + Alembic migrations).

Implementation notes:
- Prefer OpenAPI output for endpoint inventory; link back to handler functions.
- Use Python AST to track service/repo calls and imports.
- Map models to tables and migrations for data lineage.

Step-by-step tasks:
1) OpenAPI extraction (`extract_backend_openapi.py`)
   - Use `skillmeat/api/openapi.py` to export `openapi.json` if missing.
   - Parse `paths` and `methods` into `api_endpoint` nodes.
   - Preserve `operationId` in endpoint metadata for downstream linking.
2) Handler -> service mapping (`extract_backend_handlers.py`)
   - Parse `skillmeat/api/routers/**` with AST + decorator scan.
   - For each handler function, add `handler` node with `symbol` and `line`.
   - Record direct calls into `skillmeat/api/services/**` and `skillmeat/core/**`.
3) Service -> repository mapping (`extract_backend_services.py`)
   - Parse `skillmeat/api/services/**` and `skillmeat/core/**`.
   - Detect instantiations and method calls on Repository classes
     (ex: `MarketplaceSourceRepository()`).
   - Add `repository` nodes and `service_calls_repository` edges.
4) Schema mapping (`extract_backend_models.py`)
   - Parse `skillmeat/api/schemas/**` for Pydantic classes.
   - Link handlers to request/response schemas via type annotations.
5) DB/migrations mapping
   - Link repository models to Alembic revisions in
     `skillmeat/cache/migrations/versions/**`.

Outputs:
- `codebase-graph.backend.json` with service/repo/model nodes and edges.
- OpenAPI-inferred endpoint list reconciled with router definitions.

Acceptance checks:
- 100% OpenAPI endpoints appear in the graph.
- All handlers resolve to a service or repository (where applicable).
 - Schemas referenced in handlers are linked.

### Phase 3: Unified Graph + Validation

Why: enable cross-layer flow mapping and CI guarantees.

Scope:
- Merge FE + BE graphs with cross-edges (hook -> endpoint -> handler).
- Validation checks:
  - FE endpoints exist in OpenAPI
  - Deprecated nodes are not referenced
  - Route -> page -> component chains are continuous
  - Handlers referenced by OpenAPI exist

Outputs:
- `docs/architecture/codebase-graph.unified.json`
- `docs/architecture/web-app-map.md` auto-generated updates.
- Mermaid snippets for core flows.

Acceptance checks:
- CI passes validations.
- Cross-layer queries work end-to-end (route to handler).

Validation script details (`scripts/code_map/validate_graph.py`):
- Inputs: unified graph + overrides.
- Fail if:
  - `calls_api` or `api_client_calls_endpoint` points to non-existent endpoint.
  - `deprecated: true` node has any incoming edge (unless override allows).
  - OpenAPI endpoint exists with no handler edge.
  - Page has zero component edges (and no `ignore` override).

### Phase 4: Agent Guidance + Registries

Why: close the loop between graph facts and agent/human workflows.

Scope:
- Generate `.claude/rules` inventory tables from the graph (hooks, endpoints, schemas).
- Create canonical registries (ex: `skillmeat/web/hooks/index.ts`).
- Add context docs for complex choices (hook selection, schema migration rules).

Outputs:
- Auto-generated rules tables.
- Registry enforcement via imports and lint checks.
- Context docs in `.claude/context/` for hook selection + schema migration rules.

Acceptance checks:
- Agents can choose canonical hooks/endpoints without deep code search.
- Inventory tables refresh from `scripts/code_map/build_outputs.py`.

Agent-facing artifacts to generate:
- `.claude/rules/web/hooks.md` inventory table (from graph)
- `.claude/rules/web/api-client.md` endpoint table (from graph)
- `.claude/rules/api/schemas.md` schema inventory table (from graph)
- `.claude/context/web-hook-guide.md` (high-level decisions + deprecated list)
- `.claude/context/schema-migration-rules.md` (schema and migration guidance)

## Script Architecture (Proposed)

Create composable extractors and a single orchestrator:

- `scripts/code_map/extract_frontend_routes.py`
- `scripts/code_map/extract_frontend_components.py`
- `scripts/code_map/extract_frontend_hooks.py`
- `scripts/code_map/extract_frontend_api_clients.py`
- `scripts/code_map/extract_backend_openapi.py`
- `scripts/code_map/extract_backend_handlers.py`
- `scripts/code_map/extract_backend_services.py`
- `scripts/code_map/extract_backend_models.py`
- `scripts/code_map/merge_graphs.py`
- `scripts/code_map/apply_overrides.py`
- `scripts/code_map/validate_graph.py`
- `scripts/code_map/build_outputs.py`
- `scripts/code_map/__main__.py` to run all phases end-to-end

Orchestrator behavior:
- `python -m scripts.code_map` runs: extract_frontend -> extract_backend ->
  merge_graphs -> apply_overrides -> validate_graph -> build_outputs.
- Each step writes a JSON artifact so the next step is deterministic.
- If a step fails, stop and report missing inputs.

## Overrides and Metadata

Use a small, human-maintained overrides file:

`docs/architecture/codebase-graph.overrides.yaml`
- Mark `canonical`, `deprecated`, `owner`, `introduced_in`, `replaces`.
- Override labels or IDs when a stable alias is needed.
- Enforce compatibility rules for deprecated nodes (fail CI on usage).

## Validation and Coverage Gates

Add measurable checks after each phase:

- Frontend: % of pages with component edges, % hooks mapped to API clients.
- Backend: % endpoints tied to handlers, % handlers tied to services.
- Cross-layer: % frontend endpoints resolved to backend handlers.
- Drift: diff graph output in CI, flag large unexplained changes.

Coverage report output format (stdout):
- Node counts by type (sorted).
- Edge counts by type (sorted).
- Top 10 missing-link examples with file paths.

## Outputs (Downstream)

Produce consistent, machine-readable artifacts:

- `docs/architecture/web-app-map.md` (human overview)
- `docs/architecture/frontend-endpoints.txt`
- `docs/architecture/backend-endpoints.txt`
- Mermaid flow snippets per domain
- Inventory tables for `.claude/rules/`

## Immediate Next Steps (Aligned With Spec)

1) Implement graph merge + overrides (Phase 0).
2) Add API client mapping and component graph (Phase 1).
3) Switch backend endpoints to OpenAPI extraction (Phase 2).
4) Wire validations in CI (Phase 3).
