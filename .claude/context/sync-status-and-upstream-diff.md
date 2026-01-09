---
title: Sync Status Tab and Upstream-Diff API
description: Comprehensive reference for Sync Status UI component and upstream-diff API endpoint
references:
  - skillmeat/web/components/sync-status/sync-status-tab.tsx
  - skillmeat/web/components/sync-status/
  - skillmeat/api/routers/artifacts.py
  - skillmeat/api/schemas/artifacts.py
  - skillmeat/web/components/entity/unified-entity-modal.tsx
  - skillmeat/web/lib/api.ts
  - skillmeat/web/hooks/use-context-sync.ts
last_verified: 2026-01-09
---

# Sync Status Tab and Upstream-Diff API

## Overview

The **Sync Status Tab** is the main UI component for comparing artifacts across three layers (Source → Collection → Project) and managing synchronization. It communicates with the **upstream-diff** API endpoint to fetch file-level differences between collection and GitHub sources.

### Key Components & Files

| Component | File Path | Purpose |
|-----------|-----------|---------|
| **SyncStatusTab** | `skillmeat/web/components/sync-status/sync-status-tab.tsx` | Main orchestration component (lines 210-705) |
| **ComparisonSelector** | `skillmeat/web/components/sync-status/comparison-selector.tsx` | 3-way scope selector (source-vs-collection, collection-vs-project, source-vs-project) |
| **DriftAlertBanner** | `skillmeat/web/components/sync-status/drift-alert-banner.tsx` | Status alerts with action buttons |
| **ArtifactFlowBanner** | `skillmeat/web/components/sync-status/artifact-flow-banner.tsx` | Visual flow showing 3-tier structure |
| **SyncActionsFooter** | `skillmeat/web/components/sync-status/sync-actions-footer.tsx` | Bottom action buttons (Pull, Push, Merge, Resolve) |
| **DiffViewer** | `skillmeat/web/components/entity/diff-viewer.tsx` | File-level diff display (full width) |
| **ContextSyncStatus** | `skillmeat/web/components/entity/context-sync-status.tsx` | Alternative for context entities |

---

## Component Architecture

### SyncStatusTab (Main Component)

**File**: `skillmeat/web/components/sync-status/sync-status-tab.tsx` (lines 210-705)

**Props**:
```typescript
export interface SyncStatusTabProps {
  entity: Entity;
  mode: 'collection' | 'project';
  projectPath?: string;
  onClose: () => void;
}
```

**Layout**:
```
┌──────────────────────────────────────────┐
│  ArtifactFlowBanner                      │
├──────────────────────────────────────────┤
│  ComparisonSelector                      │
│  DriftAlertBanner                        │
│  DiffViewer (full width)                 │
├──────────────────────────────────────────┤
│  SyncActionsFooter                       │
└──────────────────────────────────────────┘
```

### Key State Management

**Line 259-266: Comparison Scope Selection**:
```typescript
const [comparisonScope, setComparisonScope] = useState<ComparisonScope>(
  mode === 'project'
    ? 'collection-vs-project'
    : hasRealSource
      ? 'source-vs-collection'
      : 'collection-vs-project'
);
```

**Comparison Scope Options** (from `comparison-selector.tsx` lines 16-57):
- `'collection-vs-project'` - Requires project path, compares Collection vs. Project
- `'source-vs-collection'` - Requires upstream source, compares Source vs. Collection
- `'source-vs-project'` - Requires both source and project, compares Source vs. Project

---

## API Layer: Upstream-Diff Endpoint

### GET `/api/v1/artifacts/{artifact_id}/upstream-diff`

**File**: `skillmeat/api/routers/artifacts.py` (lines 3435-3839)

**Handler Function**: `get_artifact_upstream_diff()` (lines 3451-3839)

**Response Model**: `ArtifactUpstreamDiffResponse` (from `skillmeat/api/schemas/artifacts.py` line 894)

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `artifact_id` | str (path) | Required | Artifact identifier in format "type:name" (e.g., "skill:pdf-processor") |
| `collection` | str (query) | None | Optional collection filter; searches all if not specified |

### Response Format

```typescript
interface ArtifactUpstreamDiffResponse {
  artifact_id: string;              // e.g., "skill:pdf-processor"
  artifact_name: string;            // e.g., "pdf-processor"
  artifact_type: string;            // e.g., "skill"
  collection_name: string;          // Collection where artifact resides
  upstream_source: string;          // GitHub source spec (e.g., "anthropics/skills/pdf")
  upstream_version: string;         // SHA or tag from upstream
  has_changes: boolean;             // Whether diff detected any changes
  files: FileDiff[];                // Array of file-level diffs
  summary: {
    added: number;
    modified: number;
    deleted: number;
    unchanged: number;
  };
}
```

### FileDiff Structure

```typescript
interface FileDiff {
  file_path: string;                // Relative path within artifact
  status: 'added' | 'modified' | 'deleted' | 'unchanged';
  collection_hash?: string;         // SHA-256 hash in collection version
  project_hash?: string;            // SHA-256 hash in project version
  unified_diff?: string;            // Unified diff content (for modified files)
}
```

### Example Request & Response

**Request**:
```
GET /api/v1/artifacts/skill:pdf-processor/upstream-diff?collection=default
```

**Response**:
```json
{
  "artifact_id": "skill:pdf-processor",
  "artifact_name": "pdf-processor",
  "artifact_type": "skill",
  "collection_name": "default",
  "upstream_source": "anthropics/skills/pdf",
  "upstream_version": "abc123def456",
  "has_changes": true,
  "files": [
    {
      "file_path": "SKILL.md",
      "status": "modified",
      "collection_hash": "abc123",
      "project_hash": "def456",
      "unified_diff": "--- a/SKILL.md\n+++ b/SKILL.md\n..."
    }
  ],
  "summary": {
    "added": 0,
    "modified": 1,
    "deleted": 0,
    "unchanged": 3
  }
}
```

### Error Responses

| Status | Condition | Detail |
|--------|-----------|--------|
| 400 | Invalid artifact ID format | "Invalid artifact ID format. Expected 'type:name'" |
| 400 | Collection not found | `f"Collection '{collection}' not found"` |
| 400 | No upstream source | `f"Artifact origin '{artifact.origin}' does not support upstream diff. Only GitHub artifacts are supported."` |
| 404 | Artifact not found | `f"Artifact '{artifact_id}' not found in collection"` |
| 401 | Unauthorized | Missing or invalid API token |
| 500 | Server error | `f"Failed to get artifact upstream diff: {str(e)}"` |

---

## API Client Integration

### Query Hook (Lines 273-288)

**File**: `skillmeat/web/components/sync-status/sync-status-tab.tsx`

```typescript
const {
  data: upstreamDiff,
  isLoading: upstreamLoading,
  error: upstreamError,
} = useQuery<ArtifactUpstreamDiffResponse>({
  queryKey: ['upstream-diff', entity.id],
  queryFn: async () => {
    return await apiRequest<ArtifactUpstreamDiffResponse>(
      `/artifacts/${encodeURIComponent(entity.id)}/upstream-diff`
    );
  },
  enabled: !!entity.id
    && entity.collection !== 'discovered'
    && hasValidUpstreamSource(entity.source),
});
```

### Query Key Strategy

- **queryKey**: `['upstream-diff', entity.id]`
- Used for cache invalidation on successful sync (line 325)
- Also invalidates `['project-diff', entity.id]` and `['artifacts']`

### API Request Function

**File**: `skillmeat/web/lib/api.ts` (lines 66-92)

```typescript
export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const requestInit: RequestInit = {
    ...init,
    headers: buildApiHeaders(init?.headers),
  };

  const url = buildApiUrl(path);
  const response = await fetch(url, requestInit);
  const contentType = response.headers.get('content-type');
  const isJson = contentType?.includes('application/json');
  const body = isJson ? await response.json() : undefined;

  if (!response.ok) {
    throw new ApiError('Request failed', response.status, body);
  }

  return body as T;
}
```

**Error Handling**: Throws `ApiError` with status code and body. Frontend handles error in mutation onError callback (lines 333-339).

---

## UI Messages & Error States

### "No comparison data available for this scope"

**File**: `skillmeat/web/components/sync-status/sync-status-tab.tsx` (line 643)

**Triggered When**:
- Selected comparison scope has no diff data loaded
- `!currentDiff && !isLoading && !shouldBlockWithError` (line 630)

**Possible Causes**:
1. **No upstream source**: Entity doesn't have a valid remote source (line 644)
2. **No project deployment**: Entity not deployed to selected project path (line 645)
3. **Query disabled**: Upstream query disabled due to `entity.collection === 'discovered'` (line 286)

**Rendered Component** (lines 639-648):
```tsx
<div className="flex flex-1 items-center justify-center p-8">
  <Alert className="max-w-md">
    <AlertCircle className="h-4 w-4" />
    <AlertDescription>
      No comparison data available for this scope.
      {!hasRealSource && " This artifact has no remote source."}
      {!projectPath && " No project deployment found."}
    </AlertDescription>
  </Alert>
</div>
```

### "No Project deployment found"

**File**: Same location (line 645)

**Triggered When**:
- `!projectPath` is true AND user selected a comparison scope that requires project data
- Example: "collection-vs-project" or "source-vs-project" with no `projectPath` prop

**Related Check** (line 303):
```typescript
enabled: !!entity.id && !!projectPath && mode === 'project' && entity.collection !== 'discovered',
```

---

## Source Validation

### Valid Upstream Source Check (Lines 140-146)

```typescript
function hasValidUpstreamSource(source: string | undefined | null): boolean {
  if (!source) return false;
  if (source === 'local' || source === 'unknown') return false;
  if (source.startsWith('local:')) return false;
  // Must look like a remote source (GitHub pattern with '/')
  return source.includes('/') && !source.startsWith('local');
}
```

**Invalid Sources**:
- `null`, `undefined`, empty string
- `'local'`, `'unknown'`
- `'local:*'` (local with path)

**Valid Sources**:
- Any string with `/` that doesn't start with `'local'`
- Examples: `'anthropics/skills/pdf'`, `'user/repo/path'`

---

## Mutations & State Updates

### Sync Mutation (Lines 310-340)

Pulls latest from upstream source:
```typescript
const syncMutation = useMutation({
  mutationFn: async () => {
    return await apiRequest(
      `/artifacts/${encodeURIComponent(entity.id)}/sync`,
      {
        method: 'POST',
        body: JSON.stringify({
          // Empty body syncs from upstream source (not project)
        }),
      }
    );
  },
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['upstream-diff', entity.id] });
    queryClient.invalidateQueries({ queryKey: ['project-diff', entity.id] });
    queryClient.invalidateQueries({ queryKey: ['artifacts'] });
    // Toast notification
  },
});
```

### Deploy Mutation (Lines 342-373)

Deploys artifact to project:
```typescript
const deployMutation = useMutation({
  mutationFn: async () => {
    return await apiRequest(
      `/artifacts/${encodeURIComponent(entity.id)}/deploy`,
      {
        method: 'POST',
        body: JSON.stringify({
          project_path: projectPath,
          overwrite: false,
        }),
      }
    );
  },
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['project-diff', entity.id] });
    queryClient.invalidateQueries({ queryKey: ['upstream-diff', entity.id] });
    queryClient.invalidateQueries({ queryKey: ['artifacts'] });
    queryClient.invalidateQueries({ queryKey: ['deployments'] });
  },
});
```

---

## Computed Values & Drift Detection

### Current Diff Selection (Lines 474-487)

```typescript
const currentDiff = useMemo(() => {
  switch (comparisonScope) {
    case 'source-vs-collection':
      return upstreamDiff;
    case 'collection-vs-project':
      return projectDiff;
    case 'source-vs-project':
      // TODO: Implement source-vs-project diff query
      return projectDiff;
    default:
      return projectDiff;
  }
}, [comparisonScope, upstreamDiff, projectDiff]);
```

**Note**: `source-vs-project` currently falls back to `projectDiff` (not yet implemented).

### Drift Status Computation (Lines 88-101)

```typescript
function computeDriftStatus(
  diffData: ArtifactDiffResponse | ArtifactUpstreamDiffResponse | undefined
): DriftStatus {
  if (!diffData) return 'none';
  if (!diffData.has_changes) return 'none';

  // Check if any file has conflicts (basic heuristic: look for conflict markers)
  const hasConflicts = diffData.files.some(
    (f: FileDiff) => f.unified_diff?.includes('<<<<<<< ')
  );

  if (hasConflicts) return 'conflict';
  return 'modified';
}
```

**DriftStatus Values**:
- `'none'` - No changes detected
- `'modified'` - Changes present but no conflicts
- `'conflict'` - Contains merge conflict markers

---

## Special Cases

### Discovered Artifacts (Lines 501-512)

Early return for artifacts in 'discovered' collection:
```typescript
if (entity.collection === 'discovered') {
  return (
    <div className="flex h-full items-center justify-center p-8">
      <Alert className="max-w-md">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Sync status is not available for discovered artifacts. Import this artifact to your collection to enable sync tracking.
        </AlertDescription>
      </Alert>
    </div>
  );
}
```

**Rationale**: Discovered artifacts haven't been imported yet; sync tracking requires artifact in a collection.

### Entity to Artifact Conversion (Lines 50-83)

Helper function converts Entity type to Artifact type for SyncDialog compatibility:
```typescript
function entityToArtifact(
  entity: Entity,
  upstreamDiff?: ArtifactUpstreamDiffResponse
): Artifact {
  return {
    id: entity.id,
    name: entity.name,
    type: entity.type,
    scope: 'user',
    status: entity.status === 'conflict' ? 'conflict' : 'active',
    version: entity.version,
    source: entity.source,
    metadata: {
      description: entity.description,
      tags: entity.tags,
    },
    upstreamStatus: {
      hasUpstream: !!entity.source && entity.source !== 'local',
      upstreamUrl: entity.source,
      upstreamVersion: upstreamDiff?.upstream_version,
      currentVersion: entity.version,
      isOutdated: upstreamDiff?.has_changes ?? false,
      lastChecked: new Date().toISOString(),
    },
    // ... other fields
  };
}
```

---

## Modal Integration

### Usage in Unified Entity Modal

**File**: `skillmeat/web/components/entity/unified-entity-modal.tsx` (line 50, 1586)

```typescript
import { SyncStatusTab } from '@/components/sync-status';

// Later in render:
<SyncStatusTab
  entity={entity}
  mode={mode}
  projectPath={projectPath}
  onClose={() => onOpenChange(false)}
/>
```

---

## Type Definitions

### From SDK

**File**: `skillmeat/web/sdk/models/ArtifactUpstreamDiffResponse.ts` (auto-generated)

Key imports in component (lines 6-8):
```typescript
import type { ArtifactDiffResponse } from '@/sdk/models/ArtifactDiffResponse';
import type { ArtifactUpstreamDiffResponse } from '@/sdk/models/ArtifactUpstreamDiffResponse';
import type { FileDiff } from '@/sdk/models/FileDiff';
```

### Context-Specific Types

**File**: `skillmeat/web/hooks/use-context-sync.ts` (lines 1-29)

```typescript
export function useContextSyncStatus(projectPath: string | undefined, enabled: boolean = true) {
  return useQuery<SyncStatus>({
    queryKey: ['context-sync-status', projectPath],
    queryFn: () => getSyncStatus(projectPath),
    enabled: enabled && !!projectPath,
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  });
}
```

---

## Common Patterns

### URL Encoding

**Line 282, 300, 314, 346**:
```typescript
`/artifacts/${encodeURIComponent(entity.id)}/upstream-diff`
```

Ensures artifact IDs with special characters (colons, slashes) are properly encoded.

### Loading State Management

**Lines 596-602**:
```typescript
const hasUpstreamData = !upstreamError && !!upstreamDiff;
const hasProjectData = !projectError && !!projectDiff;
const canShowAnyData = hasUpstreamData || hasProjectData;

// Only show loading if we're loading AND don't have any data yet
const isLoading = (upstreamLoading || projectLoading) && !canShowAnyData;
```

Shows loading skeleton only when actually loading (avoids blocking when one query fails but other has data).

### Error Prioritization

**Lines 606-609**:
```typescript
const shouldBlockWithError =
  (projectError && !hasUpstreamData) ||  // Project failed and no upstream
  (upstreamError && projectError) ||     // Both failed
  (!hasValidUpstreamSource(entity.source) && projectError);  // Local artifact and project failed
```

Only blocks UI if error is truly blocking (e.g., both queries failed).

---

## Related Hooks & API Clients

### ContextSyncStatus Hook

**File**: `skillmeat/web/hooks/use-context-sync.ts`

For context entities (spec files, etc.):
- `useContextSyncStatus()` - Fetch sync status
- `usePullContextChanges()` - Pull from project
- `usePushContextChanges()` - Push to project
- `useResolveContextConflict()` - Resolve conflicts

### Query Client Invalidation Pattern

**Lines 325-327, 357-360, 693-695**:
```typescript
queryClient.invalidateQueries({ queryKey: ['upstream-diff', entity.id] });
queryClient.invalidateQueries({ queryKey: ['project-diff', entity.id] });
queryClient.invalidateQueries({ queryKey: ['artifacts'] });
queryClient.invalidateQueries({ queryKey: ['deployments'] }); // for deploy
```

Systematic invalidation ensures all related data refreshes after mutations.

---

## Testing Considerations

### Mocking the API Response

```typescript
// Mock upstream diff response
const mockUpstreamDiff: ArtifactUpstreamDiffResponse = {
  artifact_id: 'skill:test',
  artifact_name: 'test',
  artifact_type: 'skill',
  collection_name: 'default',
  upstream_source: 'anthropics/skills/test',
  upstream_version: 'abc123',
  has_changes: true,
  files: [
    {
      file_path: 'SKILL.md',
      status: 'modified',
      collection_hash: 'abc123',
      project_hash: 'def456',
      unified_diff: '--- a/SKILL.md\n+++ b/SKILL.md\n...',
    },
  ],
  summary: {
    added: 0,
    modified: 1,
    deleted: 0,
    unchanged: 3,
  },
};
```

### Testing No Comparison Data State

```typescript
// Test with no upstream source and no project path
render(
  <SyncStatusTab
    entity={{ ...entity, source: 'local' }}
    mode="collection"
    projectPath={undefined}
    onClose={jest.fn()}
  />
);

// Should show: "No comparison data available for this scope. This artifact has no remote source. No project deployment found."
```

---

## Known Limitations & TODOs

1. **source-vs-project comparison**: Currently not implemented (line 482)
   - Falls back to `projectDiff` instead
   - Requires separate API endpoint or refactored diff logic

2. **Batch sync actions**: Not yet implemented (line 462)
   - Toast shows "Batch actions not yet implemented"
   - Infrastructure exists in `pendingActions` state

3. **Pull from project**: Not yet implemented (line 578)
   - Toast shows "Coming Soon"

4. **Push to collection**: Not yet implemented (line 542)
   - Toast shows "Coming Soon"

---

## Reference: Related Endpoints

### GET `/api/v1/artifacts/{artifact_id}/diff`

**Purpose**: Compare collection vs. project deployment

**Query Parameters**:
- `project_path`: Path to project directory

**Response**: `ArtifactDiffResponse` (same structure as ArtifactUpstreamDiffResponse)

### POST `/api/v1/artifacts/{artifact_id}/sync`

**Purpose**: Pull latest from upstream source

**Body**: `{ project_path?: str }` (optional; omit for upstream sync)

### POST `/api/v1/artifacts/{artifact_id}/deploy`

**Purpose**: Deploy artifact to project

**Body**: `{ project_path: str, overwrite: bool }`

---

## Summary

The **Sync Status Tab** provides a comprehensive UI for managing artifact synchronization across the 3-layer stack:

- **Frontend**: React component with TanStack Query for data management
- **API**: RESTful endpoint returning structured diffs with file-level details
- **State**: Three comparison scopes with smart defaults based on artifact type
- **UX**: Progressive loading states, targeted error messages, contextual action buttons

Key insight: The "No comparison data available" and "No Project deployment found" messages help users understand why a particular comparison scope is unavailable, guiding them to use alternative scopes or import/deploy artifacts as needed.
