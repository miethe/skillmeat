# Enhancement Report: Improving Codebase Graph Grouping Accuracy

This report outlines methods to enhance the [codebase-graph.json](file:///Users/miethe/dev/homelab/development/codebase-map/codebase-graph.json) data structure to enable more accurate and comprehensive grouping, particularly for logical connections that are not strictly file-path based.

## 1. Graph-Based Community Detection (Structural Grouping)
Currently, grouping relies on **Folder Structure** (Directory Reflection). However, code often crosses semantic boundaries.

**Enhancement:**
Run a community detection algorithm (e.g., **Louvain** or **Leiden**) on the edge list during the extraction phase (`script/code_map/`).
- **Input:** The raw graph of nodes and edges.
- **Output:** A `clusterId` property for every node in [codebase-graph.json](file:///Users/miethe/dev/homelab/development/codebase-map/codebase-graph.json).
- **UI Application:** Use `clusterId` to color nodes or create "Computed Groups" that defy folder structure (e.g., a "User Management" cluster that spans `frontend/features/users`, `backend/routers/users`, and `db/models/user`).

## 2. Explicit Semantic Annotation (Logical Grouping)
Files often lack a clear "Domain" in their path. We can support explicit annotations in code comments.

**Enhancement:**
Update extractors to parse `@module` or `@domain` tags from JSDoc/Docstrings.

**Example Code:**
```typescript
/**
 * @domain Billing
 * @module PaymentProcessing
 */
export const processPayment = () => { ... }
```

**Graph Data Update:**
```json
{
  "id": "func:processPayment",
  "domain": "Billing",
  "module": "PaymentProcessing"
}
```
**UI Application:** Add a "Domain View" that groups strictly by these tags, overriding file paths.

## 3. Heuristic Link Enrichment (Indirect Linking)
Some files are linked conceptually but not directly (e.g., a Redux slice and a React component that uses a selector, or coverage of a feature by a test file with a different name).

**Enhancement:**
- **Test-to-Source Mapping:** Heuristically link `foo.test.ts` to `foo.ts` with a `tests` edge type.
- **Feature Flag Mapping:** If using a feature flag system, extract flag usage and group nodes by the flag key (e.g., `feature_flag:new-checkout`).

## 4. Workspaces & Monorepo Support
If the codebase uses workspaces (e.g., `pnpm-workspace.yaml` or `nx.json`), these define stricter boundaries than folders.

**Enhancement:**
parse [package.json](file:///Users/miethe/dev/homelab/development/codebase-map/package.json) files during extraction to assign a `package` property to every file node.
- **Data:** `node.package = "@skillmeat/ui-kit"`
- **Grouping:** Group by `node.package` first, then directory.

## 5. Runtime / Dynamic Tracing (Future)
Static analysis misses dynamic calls (e.g., event buses, dynamic imports).

**Enhancement:**
Integrate OpenTelemetry or other tracing data to add `dynamic_call` edges. This reveals "runtime clusters"—code that actually executes together.

## Summary of Recommended Next Steps
1.  **Immediate**: Implement **Tag Parsing** (`@domain`) in extractors. This enables humans to fix bad grouping manually.
2.  **Mid-term**: Implement **Community Detection** to identify "natural" clusters.
3.  **Long-term**: Integrate **Runtime Tracing** for "execution clusters".
