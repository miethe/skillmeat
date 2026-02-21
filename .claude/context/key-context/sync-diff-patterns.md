# Sync/Diff Implementation Patterns

Reference: `.claude/rules/web/sync-diff.md` for rule scope and invariants.

## DiffViewer Lazy Parsing

**File**: `skillmeat/web/components/entity/diff-viewer.tsx`

### Parsing Cache

DiffViewer uses a `useRef` to cache parsed unified diffs per session:

```typescript
const parseCacheRef = useRef<Record<string, UnifiedDiffBlock[]>>({});
const statsCacheRef = useRef<Record<string, FileDiffStats>>({});
```

**Rationale**: The unified diff response can be 50KB+. Parsing on-demand (when user scrolls into view) saves CPU and avoids unnecessary work for unexpanded files.

**Large Diff Thresholds**:

| Threshold | Value | Check |
|-----------|-------|-------|
| `LARGE_DIFF_FILE_THRESHOLD` | 50 files | Skip parsing if file count exceeds |
| `LARGE_DIFF_LINE_THRESHOLD` | 1000 lines | Skip parsing per-file if line count exceeds |
| `LARGE_DIFF_BYTES_THRESHOLD` | 50 KB | Skip parsing if response bytes exceed |

**Pattern**:

```typescript
// Check threshold before parsing
if (fileList.length > LARGE_DIFF_FILE_THRESHOLD) {
  return <LargeUnifiedDiffWarning />; // User must confirm intent
}

// On user action, parse into blocks
const blocks = parseUnifiedDiff(diffText);
parseCacheRef.current[fileKey] = blocks;
```

---

## SyncStatusTab Scope-Aware Diff Loading

**File**: `skillmeat/web/components/sync-status/sync-status-tab.tsx`

### Query Logic

SyncStatusTab manages three diff queries with **scope-aware loading**:

| Scope | Query Key | Condition to Enable |
|-------|-----------|---------------------|
| **Source vs. Collection** | `upstream-diff` | Active tab OR source-vs-project active (both need upstream) |
| **Collection vs. Project** | `project-diff` | Active tab OR after upstream loads (background prefetch) |
| **Source vs. Project** | `source-project-diff` | Active tab OR after either upstream or project loads (prefetch) |

**Rationale**:

- **Primary scope** (active tab): Enables immediately for direct user interaction
- **Secondary scopes** (inactive tabs): Enable only after primary data loads to support instant tab switch without refetch
- **Upstream always loads first**: Both upstream and source-vs-project need upstream data; requesting once improves latency

### Stale Times & Cache Strategy

| Query | Stale Time | GC Time | Rationale |
|-------|-----------|---------|-----------|
| All diff queries | 30 sec | 5 min | 30s covers interactive tab switches; 5min preserves cache across modal reopen |

### Upstream Validation Gate

The `hasValidUpstreamSource(artifact)` check (from `lib/sync-utils.ts`) gates upstream queries:

```typescript
if (hasValidUpstreamSource(artifact)) {
  enableUpstreamQuery();  // Only GitHub origin + tracking enabled + valid remote source
}
```

Returns `true` ONLY when ALL conditions are met:

| Condition | Details |
|-----------|---------|
| `origin === 'github'` | GitHub origin only (not marketplace, local, unknown) |
| `upstream.enabled` | Tracking must be explicitly enabled |
| `source` valid | Must be a remote path string (contains '/', not 'local' or 'unknown') |

### Scope Selector Options

The scope selector in SyncStatusTab shows available options based on:

- `hasValidUpstreamSource(artifact)` — enables "Source vs. Collection" and "Source vs. Project" scopes
- `hasProject` — enables "Collection vs. Project" scope (artifact has deployments)
- Read-only mode for marketplace/local artifacts (no sync queries, no actions)

---

## ArtifactOperationsModal Deployment Fanout Gate

**File**: `skillmeat/web/components/manage/artifact-operations-modal.tsx`

### Fanout Limitation

Deployment-related hooks and fanout mutations are **gated to the deployments tab only**:

```typescript
const isDeploymentTab = activeTab === 'deployments';

// Only fire deployment hooks when user is actively viewing deployments
useDeploymentHook({
  enabled: isDeploymentTab
});

// Fanout mutations only trigger cache invalidation if on deployments tab
if (isDeploymentTab) {
  fanoutInvalidateDeploymentCaches();
}
```

**Rationale**:

- Prevents redundant cache refreshes when user switches between sync/details tabs
- Keeps deployment operations isolated to their dedicated tab
- Reduces query load when syncing; waits until user explicitly views deployments

### ProjectSelectorForDiff as Canonical Source

For the sync tab within ArtifactOperationsModal:

```typescript
// Use ProjectSelectorForDiff for sync scope in artifact modal
<ProjectSelectorForDiff
  artifact={artifact}
  activeScope={activeScope}
  onScopeChange={handleScopeChange}
/>
```

**ProjectSelectorForDiff** (in `components/sync-status/project-selector-for-diff.tsx`) is the canonical source for sync tab scope selection, providing consistent scope logic across both dedicated sync pages and artifact modals.

---

## Cache Policy Summary

### Diff Queries

- **Stale Time**: 30 seconds (interactive monitoring)
- **GC Time**: 5 minutes
- **Scope**: Reused within modal during tab switches and scope changes
- **Invalidation**: Cleared when artifact is updated or modal is closed

### Deployment Hooks

- **Stale Time**: 2 minutes (deployment domain standard)
- **GC Time**: 5 minutes
- **Gate**: Only enabled when `activeTab === 'deployments'`
- **Fanout**: Only triggers related cache invalidations on the deployments tab

### Parse Cache (DiffViewer)

- **Scope**: Per-modal session (ref-based, cleared on modal close)
- **Trigger**: On-demand when user scrolls into file
- **Eviction**: Auto-cleared on scope switch or modal reopen
