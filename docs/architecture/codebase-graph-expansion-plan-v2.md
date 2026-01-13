# Codebase Graph Expansion Plan (v2)

Purpose: extend the Layer 0 graph to support richer flow visualization and
programmatic analysis with minimal ambiguity, while keeping the unified graph
compact. This plan adds metadata to nodes/edges and introduces a parallel
"details" artifact for deep dives.

## Goals

- Preserve flow integrity across FE/BE with normalized identifiers.
- Enrich nodes/edges with compact, high-value metadata for visualization.
- Provide an optional details file for deep inspection without bloating the
  unified graph.
- Support a deterministic pipeline and clear coverage checks.

## Guiding Principles

- Keep the unified graph lean; add deep detail to a separate artifact.
- Use deterministic, stable IDs so nodes/edges can be merged safely.
- Prefer metadata that materially improves path tracing or UI explanations.
- Favor extractors that can be incrementally improved without breaking schema.

## Proposed Metadata Additions (Unified Graph)

### Common (Nodes + Edges)
- `symbol`: symbol name (function/class/component/etc)
- `line`: primary line (1-based)
- `span`: `{ start: { line, column }, end: { line, column } }`
- `signature`: compact signature (function/method/class)
- `doc_summary`: first line of docstring/JSdoc
- `module`: module path (python module, TS module)
- `package`: package/bundle (e.g., `skillmeat.api`, `skillmeat.web`)

### API Endpoints (Nodes)
- `operation_id`: OpenAPI operationId
- `tags`: OpenAPI tags
- `auth_required`: bool or list of schemes
- `request_schema`: primary request model/schema
- `response_schema`: primary response model/schema
- `status_codes`: list of status codes

### Handlers (Nodes)
- `async`: bool
- `decorators`: list of decorator names
- `dependencies`: list of FastAPI Depends symbols
- `response_model`: response model symbol

### Services / Repositories (Nodes)
- `async`: bool
- `base_class`: parent/base class
- `dependencies`: injected repos/clients
- `side_effects`: list (db/network/queue)

### Models (Nodes)
- `table`: table name
- `columns`: list of `{ name, type, nullable, pk }`
- `relationships`: list of `{ target, cardinality }`
- `indexes`: list of index names

### Migrations (Nodes)
- `revision`: revision id
- `down_revision`: down revision
- `tables`: list of touched tables

### Edge Metadata
- `callsite_file`, `callsite_line`, `awaited`, `method_name`
- `role`: for schema edges (`request`, `response`, `param`)
- `via`: for hook → endpoint edges (`direct`, `api_client`)
- `raw_path`, `normalized_path`, `method_inferred`

## New Artifact: `codebase-graph.details.json`

A parallel file keyed by node/edge id for deeper metadata, to keep
`codebase-graph.unified.json` compact.

Suggested shape:
```json
{
  "generated_at": "...",
  "source_commit": "...",
  "nodes": {
    "node_id": {
      "docstring": "...",
      "signature": "...",
      "decorators": ["..."],
      "params": ["..."],
      "returns": "...",
      "imports": ["..."]
    }
  },
  "edges": {
    "edge_id": {
      "callsite": { "file": "...", "line": 0 },
      "notes": "..."
    }
  }
}
```

## Implementation Approach

### Phase A: Schema + Normalization
1) Extend schema documentation in `docs/architecture/codebase-graph-spec.md`.
2) Define details artifact schema in a new doc section.
3) Ensure endpoint normalization rules are consistent (prefixing, param formats).

### Phase B: Extractors
1) **Frontend**
   - Add `signature`, `doc_summary`, `symbol`, `span` for components/hooks.
   - Capture `via` metadata on edges:
     - `calls_api` -> `via=direct`
     - `hook_calls_api_client` -> `via=api_client`
   - Store raw vs normalized paths when extracting endpoints.

2) **Backend**
   - Extend OpenAPI extraction for `operation_id`, `tags`, `status_codes`.
   - Use AST to capture handler `async`, `decorators`, `dependencies`.
   - Record schema `role` on edges from handler to schema.
   - Parse SQLAlchemy models for columns, relationships, indexes.
   - Parse migrations for `revision`, `down_revision`, `tables`.

3) **Details Artifact**
   - Add a new extractor step `extract_details.py` or extend existing ones to
     emit `codebase-graph.details.json`.
   - Optionally integrate `.claude/skills/symbols` as a data source.

### Phase C: Validation + Coverage
1) Add coverage buckets for:
   - handlers missing schema edges
   - services missing repo edges
   - models missing migrations
2) Add validation for:
   - endpoint OpenAPI mismatch
   - schema edges missing `role`
   - deprecated nodes referenced by edges without override

### Phase D: Outputs
- Extend `build_outputs.py` to reference details file for hover/context
  (optional but recommended).

## Deliverables

- Updated schema docs
- Extractor enhancements
- `codebase-graph.details.json`
- Expanded coverage summary
- Validation updates

## Acceptance Checks

- Unified graph remains stable and diffable.
- Details artifact includes docstrings + signatures for all major nodes.
- Visualizer can trace full flows without external context.
- Coverage summary surfaces missing links by category.
