# Enhancement Plan: Codebase Graph Grouping Improvements

Purpose: improve grouping quality for the visualization app by adding stable, multi-source groupings and metadata without destabilizing the unified graph schema.

## Goals
- Provide multiple, explicit grouping sets (structural, semantic, ownership, computed) that the UI can switch between.
- Keep grouping deterministic and diffable across runs.
- Preserve the unified graph as the canonical structure and keep grouping data in a separate artifact.

## Proposed Outputs
- `docs/architecture/codebase-graph.groupings.json` (new)
  - `generated_at`, `source_commit`
  - `group_sets`: metadata for each grouping strategy
  - `groups`: list of groups with node ids and group-level metadata
- Optional: `docs/architecture/codebase-graph.runtime.json` (future)
  - runtime-only edges for tracing-driven grouping

## Group Set Definitions
1. `structure`
   - Source: workspace/package/root + directory path.
   - Input: `pnpm-workspace.yaml`, `nx.json`, `package.json`, `pyproject.toml`.
   - Output: hierarchical grouping (workspace -> package -> directory).

2. `layer`
   - Source: node `type`.
   - Purpose: stable layout anchors for visualization (route/page/hook/api/handler/service/model).

3. `ownership`
   - Source: `CODEOWNERS` and overrides.
   - Output: group nodes by owning team (multi-membership allowed).

4. `semantic`
   - Source: overrides first, then tags in docstrings/JSDoc (`@domain`, `@module`).
   - Validation: optional registry of allowed domains/modules.
   - Output: multi-valued `domains`/`modules` groups.

5. `computed`
   - Source: clustering on weighted edges (Louvain/Leiden).
   - Metadata: `algorithm`, `params`, `seed`, `run_id`, `edge_weights`.
   - Output: cluster groups with deterministic IDs.

6. `runtime` (future)
   - Source: OpenTelemetry or tracing data in a separate edge layer.
   - Output: runtime clusters, time-windowed.

## Edge Metadata Enhancements
- Add `inferred: true` and `confidence: 0..1` for heuristic edges (tests, feature flags).
- Maintain `type` and `source` fields to distinguish extracted vs inferred edges.

## Implementation Phases

### Phase 1: Grouping Artifact + Deterministic Structure
- Add a new script `scripts/code_map/build_groupings.py`.
- Emit `codebase-graph.groupings.json` with `structure` and `layer` group sets.
- Extend `scripts/code_map/build_outputs.py` to write the grouping artifact.

### Phase 2: Semantic + Ownership Grouping
- Add overrides support for `domains`/`modules` in `codebase-graph.overrides.yaml`.
- Parse `@domain`/`@module` tags from docstrings/JSDoc into node metadata.
- Add `ownership` group set from `CODEOWNERS` with overrides to adjust ownership.

### Phase 3: Computed Clustering
- Implement weighted clustering on the unified graph edges.
- Record algorithm metadata and seed to guarantee determinism.
- Output `computed` group set with stable group IDs.

### Phase 4: Heuristic Link Enrichment
- Add heuristic edges (tests-to-source, feature flags) with `inferred` and `confidence`.
- Use as low-weight input to clustering; expose for UI filtering.

### Phase 5: Runtime Grouping (Future)
- Integrate tracing edges into `codebase-graph.runtime.json`.
- Add a runtime group set derived from time-windowed traces.

## Data Model Sketch
```json
{
  "generated_at": "...",
  "source_commit": "...",
  "group_sets": [
    {
      "id": "structure",
      "label": "Workspace/Package/Directory",
      "source": "extractor",
      "multi_membership": false
    }
  ],
  "groups": [
    {
      "group_set": "structure",
      "id": "workspace:skillmeat/package:skillmeat.web/dir:web/app",
      "label": "web/app",
      "nodes": ["page:/marketplace/sources", "hook:useSources"],
      "metadata": {"package": "skillmeat.web"}
    }
  ]
}
```

## UI Integration Notes
- Allow user to choose group set; default to `structure` + `layer` overlays.
- Support multi-membership with tags or stacked pills.
- Surface `confidence` for inferred groupings and edges.

## Validation
- Ensure all `groups.nodes` exist in `codebase-graph.unified.json`.
- Ensure group ids are deterministic across runs.
- Ensure `group_sets` metadata includes provenance and versioning.

## Risks
- Clustering instability without fixed seeds and edge weights.
- Overly noisy heuristics if confidence is not used for filtering.
- Tag drift without a registry or override layer.

## Next Steps
- Confirm desired group sets and artifact location.
- Decide whether to allow multi-membership in the UI.
- Decide on a domain/module registry source (YAML or overrides).
