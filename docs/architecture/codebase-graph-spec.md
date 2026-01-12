# Codebase Graph Spec (Layer 0)

Purpose: define how to generate and use the Layer 0 codebase graph as the system-wide
source of truth for routes, hooks, API endpoints, handlers, and (future) services,
repositories, models, and jobs. This graph underpins agent guidance and human
visualization. It complements the 3-layer guidance plan in
`docs/project_plans/reports/agentic-code-mapping-recommendations-2026-01-10.md`.

## Scope (current)

The initial extractors generate two graphs:
- Frontend: routes -> pages -> hooks -> API endpoints
- Backend: routers -> endpoints -> handlers

Outputs live in `docs/architecture/` as JSON graphs:
- `docs/architecture/codebase-graph.frontend.json`
- `docs/architecture/codebase-graph.backend.json`
- `docs/architecture/codebase-graph.unified.json` (merged + overrides applied)

## Source Scripts

Scripts live in `scripts/code_map/`:
- `extract_frontend.py`
- `extract_frontend_components.py`
- `extract_frontend_hooks.py`
- `extract_frontend_api_clients.py`
- `extract_backend.py`
- `extract_backend_openapi.py`
- `extract_backend_handlers.py`
- `extract_backend_services.py`
- `extract_backend_models.py`
- `merge_graphs.py`
- `apply_overrides.py`
- `coverage_summary.py`
- `validate_graph.py`
- `build_outputs.py`
- `__main__.py` (pipeline orchestrator)
- `graph.py` (shared graph model)
- `frontend_utils.py` (shared frontend helpers)
- `backend_utils.py` (shared backend helpers)

Run from repo root:
```bash
python -m scripts.code_map
python -m scripts.code_map.extract_frontend
python -m scripts.code_map.extract_backend
python -m scripts.code_map.extract_frontend_components
python -m scripts.code_map.extract_frontend_hooks
python -m scripts.code_map.extract_frontend_api_clients
python -m scripts.code_map.merge_graphs
python -m scripts.code_map.apply_overrides
python -m scripts.code_map.coverage_summary
python -m scripts.code_map.validate_graph
python -m scripts.code_map.build_outputs
```

Optional overrides:
```bash
python -m scripts.code_map --skip-coverage
python -m scripts.code_map.extract_frontend --web-root skillmeat/web --out docs/architecture/codebase-graph.frontend.json
python -m scripts.code_map.extract_frontend_components --web-root skillmeat/web --out docs/architecture/codebase-graph.frontend.components.json
python -m scripts.code_map.extract_frontend_hooks --web-root skillmeat/web --out docs/architecture/codebase-graph.frontend.hooks.json
python -m scripts.code_map.extract_frontend_api_clients --web-root skillmeat/web --out docs/architecture/codebase-graph.frontend.api-clients.json
python -m scripts.code_map.extract_backend --api-root skillmeat/api --out docs/architecture/codebase-graph.backend.json
python -m scripts.code_map.extract_backend_openapi --openapi skillmeat/api/openapi.json --out docs/architecture/codebase-graph.backend.openapi.json
python -m scripts.code_map.extract_backend_handlers --api-root skillmeat/api --out docs/architecture/codebase-graph.backend.handlers.json
python -m scripts.code_map.extract_backend_services --api-root skillmeat/api --out docs/architecture/codebase-graph.backend.services.json
python -m scripts.code_map.extract_backend_models --repo-root . --out docs/architecture/codebase-graph.backend.models.json
python -m scripts.code_map.merge_graphs --frontend docs/architecture/codebase-graph.frontend.json --backend docs/architecture/codebase-graph.backend.json --out docs/architecture/codebase-graph.unified.json
python -m scripts.code_map.apply_overrides --in docs/architecture/codebase-graph.unified.json --overrides docs/architecture/codebase-graph.overrides.yaml --out docs/architecture/codebase-graph.unified.json
python -m scripts.code_map.coverage_summary --graph docs/architecture/codebase-graph.unified.json
python -m scripts.code_map.validate_graph --graph docs/architecture/codebase-graph.unified.json
python -m scripts.code_map.build_outputs --graph docs/architecture/codebase-graph.unified.json
```

## Graph Schema (v1)

Root metadata:
- `source`: extractor source (`frontend`, `backend`, `unified`)
- `schema_version`: currently `v1`
- `generated_at`: UTC ISO timestamp
- `source_commit`: git commit SHA (or `unknown`)

Nodes:
- `id`: stable identifier
- `type`: one of `route`, `page`, `component`, `hook`, `api_client`, `query_key`, `type`,
  `api_endpoint`, `router`, `handler`, `service`, `repository`, `model`, `migration`, `schema`
- `label`: human-readable label
- `file`: file path when known
- optional metadata per node type (ex: `method`, `path`, `prefix`)

Edges:
- `from`, `to`: node ids
- `type`: relationship type
- `route_to_page`
- `uses_hook`
- `calls_api`
- `page_uses_component`
- `component_uses_component`
- `component_uses_hook`
- `hook_calls_api_client`
- `api_client_calls_endpoint`
- `hook_registers_query_key`
- `uses_type`
- `handler_calls_service`
- `service_calls_repository`
- `repository_uses_model`
- `model_migrated_by`
- `handler_uses_schema`
- `router_exposes`
- `handled_by`
- optional metadata (ex: `file`)

## Frontend Expansion (Phase 1)

Additional frontend coverage includes:
- Page/component relationships (`page_uses_component`, `component_uses_component`)
- Component hook usage (`component_uses_hook`)
- Hook to API client mapping (`hook_calls_api_client`, `api_client_calls_endpoint`)
- React Query keys (`hook_registers_query_key`)
- Imports of shared types (`uses_type`)

Primary extractors:
- `extract_frontend_components.py`: scans `web/app/**/page.tsx` and `web/components/**`
  for component edges and component/type nodes.
- `extract_frontend_hooks.py`: scans component hook usage + hook files for query keys
  and type imports.
- `extract_frontend_api_clients.py`: scans `web/lib/api.ts` + `web/lib/api/**` for
  exported clients, and hook imports of those clients.

## Backend Expansion (Phase 2)

Additional backend coverage includes:
- OpenAPI-driven endpoint inventory (`extract_backend_openapi.py`)
- Handler to service edges (`handler_calls_service`)
- Service to repository edges (`service_calls_repository`)
- Repository to model edges (`repository_uses_model`)
- Model to migration edges (`model_migrated_by`)
- Handler to schema edges (`handler_uses_schema`)

Primary extractors:
- `extract_backend_openapi.py`: reads `skillmeat/api/openapi.json` (or generates it)
  and adds `api_endpoint` nodes.
- `extract_backend_handlers.py`: parses routers for handlers, lines/symbols, and service/schema usage.
- `extract_backend_services.py`: parses service/core modules for repository usage.
- `extract_backend_models.py`: parses schemas, models, repositories, and migrations.

## Validation (Phase 3)

Run validation after merging and applying overrides:
```bash
python -m scripts.code_map.validate_graph --graph docs/architecture/codebase-graph.unified.json
```

Current checks:
- `calls_api`/`api_client_calls_endpoint` edges point to existing endpoints.
- `deprecated: true` nodes are not referenced unless `allow_deprecated` is set on the edge.
- OpenAPI endpoints have `handled_by` edges.
- Pages have `page_uses_component` edges unless ignored.

## Phase 4 Outputs

Generated from the unified graph:
- `.claude/rules/web/hooks.md` inventory table
- `.claude/rules/web/api-client.md` inventory table
- `.claude/rules/api/schemas.md` inventory table

Run:
```bash
python -m scripts.code_map.build_outputs --graph docs/architecture/codebase-graph.unified.json
```

## Unified Graph + Overrides

The unified graph merges frontend + backend nodes by `id` and concatenates edges.
Overrides are layered afterward, without mutating the raw extractor output.

Overrides file:
- `docs/architecture/codebase-graph.overrides.yaml`
- Supports `nodes` and `edges` entries with matching `id` (nodes) or `from`/`to`/`type` (edges).

Apply overrides with:
```bash
python -m scripts.code_map.apply_overrides \
  --in docs/architecture/codebase-graph.unified.json \
  --overrides docs/architecture/codebase-graph.overrides.yaml \
  --out docs/architecture/codebase-graph.unified.json
```

Coverage summary:
```bash
python -m scripts.code_map.coverage_summary --graph docs/architecture/codebase-graph.unified.json
```
Requires the unified graph to exist (run merge + overrides first).

## What It Enables (Use Cases)

Human workflows:
- Route-level discovery: find where a page lives and which hooks it uses.
- Impact analysis: identify hooks or endpoints affected by changes.
- Architecture visualization: generate Mermaid graphs or UI flow diagrams.
- Onboarding: provide a reliable map of how the app is assembled.

Agent workflows:
- Canonical source of truth for choosing hooks and endpoints.
- Fast, targeted navigation (graph query instead of full file reads).
- Detect mismatches (hook calling missing endpoint).
- Deprecation guidance when combined with override metadata.

Engineering workflows:
- CI checks for dangling endpoints and unused handlers.
- Diffable maps per release for review and audits.
- Coverage reports for unmapped areas.

## Relationship to the 3-Layer Guidance Plan

Layer 0 (this graph) provides the machine-readable source of truth used by:
- Layer 1: Code registries (enforce canonical imports).
- Layer 2: Rules files (auto-generated inventory tables).
- Layer 3: Context docs (deep guidance and decision trees).

The Layer 0 graph does not replace those layers; it enables and keeps them consistent.

## Expansion Roadmap (Planned)

Frontend:
- Component usage graph (page -> component -> hook)
- API client mapping (hook -> api client -> endpoint)
- React Query key registration graph
- Cross-references to FE type definitions

Backend:
- OpenAPI-driven endpoint source of truth
- Handler -> service -> repository call graph (AST + import analysis)
- Schema mapping (Pydantic models to endpoints)
- Model/DB layer mapping (SQLAlchemy + Alembic)

Cross-cutting:
- Merge frontend + backend into a unified graph
- Override layer (manual annotations):
  - `canonical`, `deprecated`, `owner`, `introduced_in`, `replaces`
- Validation checks in CI:
  - Hook endpoints exist in OpenAPI
  - Deprecated hooks are not used
  - Routes map to existing pages

Outputs:
- Auto-generate `docs/architecture/web-app-map.md`
- Auto-generate API endpoint tables
- Emit Mermaid diagrams and optional HTML explorer

## Recommended Next Steps

1) Add a merge script to combine frontend + backend graphs.
2) Replace backend regex parsing with OpenAPI extraction.
3) Add an override YAML to annotate canonical and deprecated constructs.
4) Use the graph to generate rules tables in `.claude/rules/`.

## After Running the Scripts (What To Do Next)

Once both graphs are generated, the next steps are:

1) Inspect the raw graphs for coverage and correctness.
2) Use them directly for analysis (routes, hooks, endpoints).
3) Feed them into downstream outputs (docs, rules tables, visuals).
4) Add overrides for semantics (canonical/deprecated/owner).

### Direct Usage Example (Query the JSON)

List all marketplace endpoints found in frontend hooks:
```bash
jq -r '.nodes[] | select(.type=="api_endpoint") | .label' \
  docs/architecture/codebase-graph.frontend.json | rg "marketplace"
```

Find which hooks call a specific endpoint:
```bash
TARGET="GET /marketplace/sources"
jq -r --arg target "$TARGET" '
  .edges[]
  | select(.type=="calls_api" and .to=="endpoint:" + $target)
  | .from
' docs/architecture/codebase-graph.frontend.json
```

### Input for Other Work (Generate Docs/Rules)

Generate a simple endpoint inventory (frontend view):
```bash
jq -r '
  .nodes[]
  | select(.type=="api_endpoint")
  | "\(.label)"
' docs/architecture/codebase-graph.frontend.json \
  | sort -u > docs/architecture/frontend-endpoints.txt
```

Build a basic Mermaid graph snippet (routes -> pages -> hooks):
```bash
jq -r '
  ["flowchart TB"] +
  (.edges[]
   | select(.type=="route_to_page" or .type=="uses_hook")
   | "\(.from) --> \(.to)")
  | .[]
' docs/architecture/codebase-graph.frontend.json \
  > docs/architecture/frontend-flow.mmd
```

### Suggested Workflow (Manual + Automated)

- Manual review: skim the JSON for missing routes or obvious mismatches.
- Add overrides: maintain a small `docs/architecture/codebase-graph.overrides.yaml`
  for canonical/deprecated/owner metadata.
- Generate human docs: use the graph (plus overrides) to update
  `docs/architecture/web-app-map.md` and rules tables in `.claude/rules/`.
- Validate: add CI checks that compare frontend endpoints against backend OpenAPI.

## Notes

- The current graph is intentionally lightweight and conservative.
- It is expected to grow and become more precise as parsers improve.
