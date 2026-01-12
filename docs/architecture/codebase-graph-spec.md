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
- `extract_backend.py`
- `merge_graphs.py`
- `apply_overrides.py`
- `coverage_summary.py`
- `graph.py` (shared graph model)

Run from repo root:
```bash
python -m scripts.code_map.extract_frontend
python -m scripts.code_map.extract_backend
python -m scripts.code_map.merge_graphs
python -m scripts.code_map.apply_overrides
python -m scripts.code_map.coverage_summary
```

Optional overrides:
```bash
python -m scripts.code_map.extract_frontend --web-root skillmeat/web --out docs/architecture/codebase-graph.frontend.json
python -m scripts.code_map.extract_backend --api-root skillmeat/api --out docs/architecture/codebase-graph.backend.json
python -m scripts.code_map.merge_graphs --frontend docs/architecture/codebase-graph.frontend.json --backend docs/architecture/codebase-graph.backend.json --out docs/architecture/codebase-graph.unified.json
python -m scripts.code_map.apply_overrides --in docs/architecture/codebase-graph.unified.json --overrides docs/architecture/codebase-graph.overrides.yaml --out docs/architecture/codebase-graph.unified.json
python -m scripts.code_map.coverage_summary --graph docs/architecture/codebase-graph.unified.json
```

## Graph Schema (v1)

Root metadata:
- `source`: extractor source (`frontend`, `backend`, `unified`)
- `schema_version`: currently `v1`
- `generated_at`: UTC ISO timestamp
- `source_commit`: git commit SHA (or `unknown`)

Nodes:
- `id`: stable identifier
- `type`: one of `route`, `page`, `hook`, `api_endpoint`, `router`, `handler`
- `label`: human-readable label
- `file`: file path when known
- optional metadata per node type (ex: `method`, `path`, `prefix`)

Edges:
- `from`, `to`: node ids
- `type`: relationship type
  - `route_to_page`
  - `uses_hook`
- `calls_api`
- `router_exposes`
- `handled_by`
- optional metadata (ex: `file`)

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
