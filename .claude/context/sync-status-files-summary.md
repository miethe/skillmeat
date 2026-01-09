---
title: Sync Status Files Quick Reference
description: Quick reference guide to all files related to Sync Status tab and upstream-diff API
last_verified: 2026-01-09
---

# Sync Status Files Quick Reference

## Web Frontend Components

### Main Component
- **File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/sync-status/sync-status-tab.tsx`
- **Component**: `SyncStatusTab`
- **Lines**: 210-705 (main render), 243-248 (props)
- **Purpose**: Orchestration component for 3-panel sync UI
- **Key Functions**:
  - Query: upstream-diff and project-diff (lines 273-304)
  - Mutations: sync, deploy, take-upstream, keep-local (lines 310-426)
  - Event handlers: pull, deploy, merge, resolve (lines 429-468)

### Sub-Components
- **Comparison Selector**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/sync-status/comparison-selector.tsx`
  - Type: `ComparisonScope` enum (source-vs-collection, collection-vs-project, source-vs-project)
  - Lines: 16-58 (scope options)

- **Drift Alert Banner**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/sync-status/drift-alert-banner.tsx`
  - Shows drift status and action buttons

- **Artifact Flow Banner**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/sync-status/artifact-flow-banner.tsx`
  - Displays 3-tier architecture visualization

- **Sync Actions Footer**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/sync-status/sync-actions-footer.tsx`
  - Pull, Push, Merge, Resolve buttons

- **File Preview Pane**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/sync-status/file-preview-pane.tsx`
  - Individual file diff display

### Component Index
- **File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/sync-status/index.ts`
- **Lines**: 1-27
- **Purpose**: Re-exports all sync-status components

## Related Entity Components

- **Unified Entity Modal** (imports SyncStatusTab)
  - File: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/entity/unified-entity-modal.tsx`
  - Import: Line 50
  - Usage: Line 1586

- **Context Sync Status** (alternative sync UI for context entities)
  - File: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/entity/context-sync-status.tsx`
  - Lines: 1-60+ (similar pattern to SyncStatusTab)

- **Diff Viewer** (shared by both)
  - File: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/entity/diff-viewer.tsx`
  - Used for file-level diff rendering

## API Backend

### Router (Endpoints)
- **File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/artifacts.py`
- **Endpoint**: GET `/api/v1/artifacts/{artifact_id}/upstream-diff`
  - Handler: `get_artifact_upstream_diff()` (lines 3451-3839)
  - Route decorator: lines 3435-3450
  - Query params: artifact_id (path), collection (query)
  - Response: `ArtifactUpstreamDiffResponse`

- **Related Endpoints** (same file):
  - GET `/api/v1/artifacts/{artifact_id}/diff` - Collection vs. Project comparison
  - POST `/api/v1/artifacts/{artifact_id}/sync` - Pull from upstream
  - POST `/api/v1/artifacts/{artifact_id}/deploy` - Deploy to project

### Schemas (Response Models)
- **File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/artifacts.py`
- **Models**:
  - `FileDiff` (line 819)
    - Fields: file_path, status, collection_hash, project_hash, unified_diff
  - `ArtifactUpstreamDiffResponse` (line 894)
    - Fields: artifact_id, artifact_name, artifact_type, collection_name, upstream_source, upstream_version, has_changes, files, summary
  - `ArtifactDiffResponse` (line 850)
    - Similar structure but for collection vs. project comparison

## Web API Client

- **File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/lib/api.ts`
- **Functions**:
  - `apiRequest<T>(path, init?)` (lines 66-92)
    - Generic fetch wrapper used by SyncStatusTab
  - `buildApiUrl(path)` (lines 28-31)
    - Constructs full API URL
  - `buildApiHeaders(extra?)` (lines 41-64)
    - Adds authentication and content-type headers

## Hooks

- **File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/use-context-sync.ts`
- **Hooks**:
  - `useContextSyncStatus(projectPath, enabled)` - For context entities
  - `usePullContextChanges()` - Pull from project
  - `usePushContextChanges()` - Push to project
  - `useResolveContextConflict()` - Resolve conflicts
  - `usePendingContextChanges(entityId, projectPath)` - Get change count

## Type Definitions

### Generated SDK Types
- **Location**: `skillmeat/web/sdk/models/`
- Key types imported in sync-status-tab.tsx (lines 6-8):
  - `ArtifactDiffResponse`
  - `ArtifactUpstreamDiffResponse`
  - `FileDiff`

### Custom Types
- **Entity**: From `@/types/entity`
  - Used for entity data passed to SyncStatusTab
- **Artifact**: From `@/types/artifact`
  - Used for artifact compatibility in SyncDialog

## OpenAPI Schema

- **File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/openapi.json`
- **Endpoint Schema**: Lines 3094+ (upstream-diff endpoint)
- **Operation ID**: `get_artifact_upstream_diff_api_v1_artifacts__artifact_id__upstream_diff_get`

## Documentation Files

### Architecture/Planning
- `/Users/miethe/dev/homelab/development/skillmeat/docs/architecture/web-app-map.md`
  - References sync-status component and upstream-diff API

- `/Users/miethe/dev/homelab/development/skillmeat/docs/project_plans/implementation_plans/bug-fixes/sync-status-tab-remediation-v1.md`
  - Contains "No comparison data available" message (line 211)

- `/Users/miethe/dev/homelab/development/skillmeat/.claude/plans/sync-status-simplify-plan.md`
  - Simplification plan for sync status

### Progress/Planning
- `/Users/miethe/dev/homelab/development/skillmeat/.claude/progress/quick-features/sync-status-tab-fix.md`
  - Progress tracking for sync-status fixes

### Worknotes
- `/Users/miethe/dev/homelab/development/skillmeat/.claude/worknotes/bug-fixes-2025-01.md`
- `/Users/miethe/dev/homelab/development/skillmeat/.claude/worknotes/bug-fixes-2025-12.md`

## Data Flow

### Query Flow (Fetch Data)
```
SyncStatusTab (component)
  ↓
useQuery('upstream-diff', entity.id)
  ↓
apiRequest('/artifacts/{id}/upstream-diff')
  ↓
fetch(buildApiUrl('/artifacts/{id}/upstream-diff'))
  ↓
GET /api/v1/artifacts/{artifact_id}/upstream-diff
  ↓
ArtifactUpstreamDiffResponse (JSON)
```

### Mutation Flow (Sync Action)
```
handlePullFromSource() → syncMutation.mutate()
  ↓
apiRequest('/artifacts/{id}/sync', { method: 'POST' })
  ↓
POST /api/v1/artifacts/{artifact_id}/sync
  ↓
onSuccess: invalidateQueries(['upstream-diff', 'project-diff', 'artifacts'])
  ↓
Re-fetch with new data
```

## Message Locations

### "No comparison data available for this scope"
- **File**: `skillmeat/web/components/sync-status/sync-status-tab.tsx`
- **Line**: 643
- **Condition**: `!currentDiff && !isLoading && !shouldBlockWithError`
- **Context**: Shown when selected scope has no data (e.g., artifact has no upstream source)

### "No Project deployment found"
- **File**: Same as above
- **Line**: 645
- **Condition**: `!projectPath`
- **Context**: Shown when trying to compare against project but no project path provided

### "Sync status is not available for discovered artifacts"
- **File**: Same as above
- **Lines**: 501-512
- **Condition**: `entity.collection === 'discovered'`
- **Context**: Discovered artifacts can't be synced until imported

## Key Constants & Enums

### ComparisonScope
```typescript
type ComparisonScope =
  | 'collection-vs-project'
  | 'source-vs-collection'
  | 'source-vs-project'
```

### DriftStatus
```typescript
type DriftStatus = 'none' | 'modified' | 'conflict'
```

### FileStatus (in FileDiff)
```typescript
type FileStatus = 'added' | 'modified' | 'deleted' | 'unchanged'
```

## Dependencies

### External Libraries
- `@tanstack/react-query` - Query management
- `lucide-react` - Icons (AlertCircle, GitCompare, etc.)
- `shadcn/ui` - UI components (Alert, Button, Select, etc.)

### Internal Dependencies
- `@/lib/api` - API client
- `@/types/entity` - Entity type definition
- `@/components/ui/*` - UI primitives
- `@/sdk/models/*` - Auto-generated API types

## File Sizes & Complexity

| File | Lines | Complexity | Purpose |
|------|-------|-----------|---------|
| sync-status-tab.tsx | ~705 | High | Main orchestration |
| artifacts.py (router) | ~3839 | High | Multiple endpoints |
| artifacts.py (schemas) | ~1000+ | Medium | Data models |
| comparison-selector.tsx | ~100 | Low | UI selector |
| api.ts | ~92 | Low | Fetch wrapper |
| use-context-sync.ts | ~116 | Medium | Hook definitions |

---

## Quick Navigation

### To Find Code That Handles [Task]

**Display "No comparison data" message**:
→ `sync-status-tab.tsx` line 643

**Fetch upstream diff data**:
→ `sync-status-tab.tsx` lines 273-288

**Define ComparisonScope**:
→ `comparison-selector.tsx` lines 16-20

**Validate upstream source**:
→ `sync-status-tab.tsx` lines 140-146

**Compute drift status**:
→ `sync-status-tab.tsx` lines 88-101

**API endpoint implementation**:
→ `artifacts.py` lines 3451-3839

**Response schema**:
→ `artifacts.py` line 894

**Entity to Artifact conversion**:
→ `sync-status-tab.tsx` lines 50-83

**Query cache invalidation**:
→ `sync-status-tab.tsx` lines 325-327, 357-360, 693-695
