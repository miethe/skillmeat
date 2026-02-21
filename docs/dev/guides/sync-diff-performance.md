---
title: "Sync Diff Performance Guide"
description: "Developer guide for understanding sync diff performance optimizations, including summary-first mode, DiffViewer thresholds, and gated queries"
audience: "developers"
tags: ["sync", "performance", "diff", "api", "frontend", "optimization"]
created: 2026-02-21
updated: 2026-02-21
category: "developer-guides"
status: "published"
related_documents:
  - "docs/dev/guides/artifact-data-fetching.md"
  - "skillmeat/api/routers/artifacts.py"
  - "skillmeat/web/components/sync/sync-status-tab.tsx"
  - "skillmeat/web/components/diff/diff-viewer.tsx"
---

# Sync Diff Performance Guide

Developer guide for understanding sync diff performance optimizations in SkillMeat's sync workflow, including summary-first diff mode, DiffViewer thresholds, and best practices for adding new diff queries.

## Overview

The sync status UI was optimized across backend and frontend to reduce unnecessary API calls and improve diff rendering performance:

- **Backend**: Summary-first diff mode (`?mode=summary`) returns metadata without diff content, reducing payload size and compute time
- **Frontend**: Deployment queries only run on the Deployments tab; diff loading is scoped to active comparison; large diffs are paginated and files are parsed on-demand
- **Result**: Modal opens instantly; diff viewer only parses files you actually open; 50+ file diffs are handled with pagination

## Summary-First Diff Mode

### What It Is

The `/artifacts/{id}/upstream/diff` endpoint supports two modes:

| Mode | Response | Use Case |
|------|----------|----------|
| `?mode=summary` | File count, status summary, no content | Initial diff load, conflict detection, scope switching |
| `?mode=full` (default) | Complete diff with all file contents | Detailed review, showing all changes inline |

### Request Examples

**Summary mode** (fastest, used on initial load):
```typescript
const response = await fetch(
  `/api/v1/artifacts/${artifactId}/upstream/diff?mode=summary`,
  { headers: { 'Authorization': `Bearer ${token}` } }
);

// Response contains file metadata but no diff content
const summary = await response.json();
// {
//   status: 'conflict' | 'ahead' | 'behind' | 'diverged',
//   summary: { added: 2, modified: 5, deleted: 0 },
//   files: [
//     { path: 'file.ts', status: 'modified' },
//     { path: 'new.ts', status: 'added' }
//   ]
// }
```

**Full mode** (when user opens DiffViewer):
```typescript
const response = await fetch(
  `/api/v1/artifacts/${artifactId}/upstream/diff?mode=full`,
  { headers: { 'Authorization': `Bearer ${token}` } }
);

const fullDiff = await response.json();
// Includes file contents and side-by-side diffs
```

### When to Use Each

**Use `?mode=summary`**:
- Opening sync modal (get status without blocking)
- Switching between comparison scopes (source-vs-collection, collection-vs-project, source-vs-project)
- Checking for conflicts before merge
- Initial conflict detection

**Use `?mode=full`**:
- User explicitly opens DiffViewer component
- Performing a detailed review
- After merging (to verify changes)

## DiffViewer Thresholds

The DiffViewer component has built-in thresholds for handling large diffs gracefully:

### Threshold Constants

**File:** `skillmeat/web/components/diff/diff-viewer.tsx`

```typescript
// Pagination threshold: if diff contains >50 files, show paginated view
const LARGE_DIFF_FILE_THRESHOLD = 50;

// Per-file threshold: if a single file has >1000 lines, show "Load Diff" button
const LARGE_DIFF_LINE_THRESHOLD = 1000;

// File size threshold: if a file is >50KB, defer parsing until load button clicked
const LARGE_DIFF_BYTES_THRESHOLD = 50 * 1024; // 50KB
```

### How Thresholds Work

#### 1. File Count Pagination (>50 files)

```typescript
// DiffViewer automatically paginate if files.length > LARGE_DIFF_FILE_THRESHOLD
if (files.length > 50) {
  return <PaginatedDiffList files={files} pageSize={20} />;
}

// User sees: "Showing 1-20 of 156 files" with Next/Previous buttons
// Only 20 file diffs parsed and rendered at a time
```

#### 2. Per-File Line Count Limit (>1000 lines)

```typescript
// If a single file has >1000 lines, show load button instead of inline diff
if (file.diffLines > LARGE_DIFF_LINE_THRESHOLD) {
  return (
    <FileCard key={file.path}>
      <div>{file.path}</div>
      <div className="text-sm text-gray-600">
        {file.diffLines} lines changed
      </div>
      <button onClick={() => loadDiff(file.path)}>Load Diff</button>
    </FileCard>
  );
}
```

#### 3. File Size Limit (>50KB)

```typescript
// If file size >50KB, defer parsing until explicitly loaded
if (file.sizeBytes > LARGE_DIFF_BYTES_THRESHOLD) {
  return (
    <FileCard key={file.path}>
      <div>{file.path}</div>
      <div className="text-sm">({formatBytes(file.sizeBytes)})</div>
      <button onClick={() => parseLargeFileDiff(file.path)}>
        Load {formatBytes(file.sizeBytes)} Diff
      </button>
    </FileCard>
  );
}
```

### Adjusting Thresholds

If your project has different requirements (e.g., very large artifacts or fast connections):

```typescript
// In diff-viewer.tsx
export const LARGE_DIFF_FILE_THRESHOLD = 50;  // Change to 100 for more files per page
export const LARGE_DIFF_LINE_THRESHOLD = 1000; // Change to 2000 for longer files
export const LARGE_DIFF_BYTES_THRESHOLD = 50 * 1024; // Change to 100 * 1024 for larger files
```

Then rebuild:
```bash
pnpm build
```

## Adding New Diff Queries

When implementing new sync-related diff queries in components, follow this pattern:

### Required Query Configuration

```typescript
import { useQuery } from '@tanstack/react-query';
import { hasValidUpstreamSource } from '@/lib/sync-utils';

// Inside your component
const { data: diffSummary } = useQuery({
  queryKey: ['artifacts', artifactId, 'diff-summary'],

  // Always use the gate check first
  enabled: !!artifactId && hasValidUpstreamSource(artifact),

  // 30 second stale time - diffs change rarely during a session
  staleTime: 30_000,

  // 5 minute garbage collection - keep in cache for up to 5 mins
  gcTime: 300_000,

  queryFn: async () => {
    const response = await fetch(
      `/api/v1/artifacts/${encodeURIComponent(artifactId)}/upstream/diff?mode=summary`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    if (!response.ok) throw new Error('Failed to fetch diff');
    return response.json();
  },
});
```

### Key Configuration Points

| Setting | Value | Why |
|---------|-------|-----|
| `enabled` | Must include `hasValidUpstreamSource()` gate | Prevents querying if no valid upstream |
| `staleTime` | `30_000` (30 seconds) | Diffs don't change often; reduces unnecessary refetch |
| `gcTime` | `300_000` (5 minutes) | Keeps data in cache longer for tab switches |
| Mode | `?mode=summary` initially | Faster response; load full later if needed |

### Gate Function

**File:** `skillmeat/web/lib/sync-utils.ts`

```typescript
// Always use this gate before making upstream diff requests
export function hasValidUpstreamSource(artifact: Artifact | null | undefined): boolean {
  if (!artifact) return false;

  // Check that upstream tracking is enabled and has valid source
  return !!(
    artifact.upstream?.tracking_enabled &&
    artifact.upstream?.current_sha
  );
}
```

### Example: Scope-Aware Diff Loading

```typescript
// In sync-status-tab.tsx - load diffs only for active scope
const [activeScope, setActiveScope] = useState<'source-vs-collection' | 'collection-vs-project' | 'source-vs-project'>('source-vs-collection');

const { data: diffSummary, isLoading } = useQuery({
  queryKey: ['artifacts', artifactId, 'diff', activeScope],
  enabled: !!artifactId && hasValidUpstreamSource(artifact),
  staleTime: 30_000,
  gcTime: 300_000,
  queryFn: () => fetchDiffForScope(artifactId, activeScope),
});

// Only one scope's diff loads at a time
// Switching scopes fetches new diff (or loads from 5-min cache)
```

## Testing Patterns

### Testing Gated Queries

See `skillmeat/web/__tests__/sync-modal-integration.test.tsx` for patterns:

```typescript
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SyncStatusTab } from '@/components/sync/sync-status-tab';

describe('SyncStatusTab - Diff Query Gating', () => {
  it('should not load diff if upstream source is invalid', () => {
    const mockArtifact = {
      id: 'skill:test',
      upstream: {
        tracking_enabled: false,
        current_sha: undefined,
      },
    };

    const { container } = render(
      <QueryClientProvider client={new QueryClient()}>
        <SyncStatusTab artifact={mockArtifact} />
      </QueryClientProvider>
    );

    // Query should not have been initiated
    expect(screen.queryByText(/Loading diff/i)).not.toBeInTheDocument();
  });

  it('should load summary diff on mount if upstream source is valid', async () => {
    const mockArtifact = {
      id: 'skill:test',
      upstream: {
        tracking_enabled: true,
        current_sha: 'abc123',
      },
    };

    const { rerender } = render(
      <QueryClientProvider client={new QueryClient()}>
        <SyncStatusTab artifact={mockArtifact} />
      </QueryClientProvider>
    );

    // Wait for summary to load
    expect(await screen.findByText(/2 files modified/i)).toBeInTheDocument();
  });

  it('should refetch diff when scope changes', async () => {
    // Test that activeScope change triggers new query
    const user = userEvent.setup();

    const { rerender } = render(
      <QueryClientProvider client={new QueryClient()}>
        <SyncStatusTab artifact={validArtifact} scope="source-vs-collection" />
      </QueryClientProvider>
    );

    // Switch scope
    await user.click(screen.getByRole('tab', { name: /collection vs project/ }));

    // New query should be initiated
    expect(await screen.findByText(/fetching diff/i)).toBeInTheDocument();
  });
});
```

## Summary

When optimizing sync diff performance:

1. **Use `?mode=summary`** for initial loads and scope switches
2. **Respect DiffViewer thresholds** (50 files, 1000 lines, 50KB) — adjust if needed
3. **Gate all queries** with `hasValidUpstreamSource()` to avoid unnecessary API calls
4. **Set stale/gc times correctly** — 30s stale, 5m gc for diff queries
5. **Test gating behavior** to ensure queries don't run without valid upstream
6. **Monitor large diffs** — pagination and load buttons prevent UI slowdowns

For detailed architecture, see [Artifact Data Fetching Guide](/docs/dev/guides/artifact-data-fetching.md).
