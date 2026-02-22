# Sync/Diff Rule (Pointer)

Path scope:
- `skillmeat/web/components/sync-status/sync-status-tab.tsx`
- `skillmeat/web/components/entity/diff-viewer.tsx`
- `skillmeat/web/components/manage/artifact-operations-modal.tsx`

Use `.claude/context/key-context/sync-diff-patterns.md` for full sync/diff implementation patterns.

Invariants:

- **DiffViewer lazy parsing**: Use `parseCacheRef` for on-demand unified diff parsing; defer expensive parsing until user scrolls into view.
- **Diff query stale times**: All diff queries (upstream, project, source-project) must use 30s staleTime / 5min gcTime for interactive freshness.
- **Deployment fanout gated**: Deployment hooks and fanout mutations only fire when `activeTab === 'deployments'` to avoid redundant cache refresh on scope switches.
- **Upstream validation**: Upstream diff queries only enabled when `hasValidUpstreamSource(artifact)` returns true (GitHub origin + upstream tracking enabled + valid remote source).
