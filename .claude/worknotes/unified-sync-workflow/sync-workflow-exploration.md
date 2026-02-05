# SkillMeat Sync Workflow: Full Exploration Report

**Date**: 2026-02-04
**Status**: Complete
**Scope**: Full sync orchestration across 3-tier architecture (Source → Collection → Project)

---

## Executive Summary

SkillMeat implements a **unified sync workflow** across three sync directions:

1. **Pull from Source → Collection** (upstream sync)
2. **Push Collection → Project** (deploy)
3. **Pull from Project → Collection** (sync/capture local edits)

The workflow is orchestrated through:
- **SyncStatusTab** (main UI coordinator) - `/components/sync-status/sync-status-tab.tsx`
- **3-tier flow visualization** via ArtifactFlowBanner
- **Diff viewer** for file-level comparison
- **Merge workflow** for conflict resolution
- **API endpoints** for each sync direction

---

## 1. SYNC STATUS TAB (Main Orchestrator)

**File**: `/skillmeat/web/components/sync-status/sync-status-tab.tsx` (830 lines)

### Props
```typescript
interface SyncStatusTabProps {
  entity: Artifact;
  mode: 'collection' | 'project';
  projectPath?: string;
  onClose: () => void;
}
```

### 3-Tier Visualization

**Component**: `ArtifactFlowBanner`
- Shows Source (GitHub) → Collection → Project with version badges
- Displays drift/modification indicators (e.g., "Modified", "New Update")
- Inline action buttons on connectors for quick operations

**Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│  Source (GitHub)  →[Pull]→  Collection  →[Deploy]→  Project │
│  v1.0.0 (abc1234)          v0.9.0                v0.9.0     │
│  "New Update"                                   "Modified"   │
└─────────────────────────────────────────────────────────────┘
```

### Comparison Scope Selector

**Component**: `ComparisonSelector`

Controls which versions are being compared:

```typescript
type ComparisonScope =
  | 'source-vs-collection'  // Upstream diff
  | 'collection-vs-project' // Project diff
  | 'source-vs-project'     // TODO: Not yet implemented
```

**Query enablement logic**:
- Upstream diff query ONLY enabled if `hasValidUpstreamSource(entity)` returns true
- Project diff query enabled if `projectPath` provided
- Scope options in selector reflect available comparisons

### Drift Status Detection

**Function**: `computeDriftStatus()` (lines 61-72)

```typescript
function computeDriftStatus(
  diffData: ArtifactDiffResponse | ArtifactUpstreamDiffResponse | undefined
): DriftStatus {
  if (!diffData || !diffData.has_changes) return 'none';

  // Check for conflict markers in unified diffs
  const hasConflicts = diffData.files.some((f) =>
    f.unified_diff?.includes('<<<<<<< ')
  );

  return hasConflicts ? 'conflict' : 'modified';
}
```

**Status types**: `'none' | 'modified' | 'outdated' | 'conflict'`

### Query Management

**Two parallel queries**:

1. **Upstream diff** (Source vs Collection)
```typescript
useQuery<ArtifactUpstreamDiffResponse>({
  queryKey: ['upstream-diff', entity.id, entity.collection],
  queryFn: () => apiRequest(`/artifacts/${id}/upstream-diff?collection=${collection}`),
  enabled: hasValidUpstreamSource(entity), // Validation check
})
```

2. **Project diff** (Collection vs Project)
```typescript
useQuery<ArtifactDiffResponse>({
  queryKey: ['project-diff', entity.id, projectPath],
  queryFn: () => apiRequest(`/artifacts/${id}/diff?project_path=${projectPath}`),
  enabled: !!projectPath,
})
```

---

## 2. SYNC DIRECTIONS (3 Workflows)

### Direction 1: Pull from Source → Collection (Upstream Sync)

**Trigger**: User clicks "Pull from Source" button in banner or footer

**API Endpoint**: `POST /api/v1/artifacts/{id}/sync`
- Request body: `{}` (empty = upstream sync)
- No `project_path` in request triggers upstream sync

**Mutation**:
```typescript
const syncMutation = useMutation({
  mutationFn: async () => {
    return await apiRequest<ArtifactSyncResponse>(
      `/artifacts/${encodeURIComponent(entity.id)}/sync`,
      {
        method: 'POST',
        body: JSON.stringify({}), // Empty body = pull from upstream
      }
    );
  },
  onSuccess: (data) => {
    if (data.conflicts?.length > 0) {
      toast('Pull completed with conflicts', { variant: 'destructive' });
    } else {
      toast('Sync Successful', { description: data.message });
    }
    // Invalidate all affected caches
    queryClient.invalidateQueries({ queryKey: ['upstream-diff'] });
    queryClient.invalidateQueries({ queryKey: ['project-diff'] });
    queryClient.invalidateQueries({ queryKey: ['artifacts'] });
  },
});
```

**Backend Logic** (lines 3106-3200 of artifacts.py):
1. Parse artifact ID
2. Get collection name (provided or default)
3. Load collection and find artifact
4. Verify artifact has GitHub origin
5. Call `artifact_mgr.fetch_update()` to fetch latest from GitHub
6. Apply strategy (overwrite/skip/merge) based on request
7. Return sync result with conflict info

**Conflict Handling**: If conflicts detected, return with `conflicts` array and let UI handle resolution

---

### Direction 2: Deploy Collection → Project (Push/Overwrite)

**Trigger**: User clicks "Deploy to Project" button in banner

**API Endpoint**: `POST /api/v1/artifacts/{id}/deploy`
- Request body: `{ project_path, overwrite: true }`

**Mutation**:
```typescript
const deployMutation = useMutation({
  mutationFn: async () => {
    const url = `/artifacts/${encodeURIComponent(entity.id)}/deploy`;
    return await apiRequest<{ success: boolean; message: string }>(url, {
      method: 'POST',
      body: JSON.stringify({
        project_path: projectPath,
        overwrite: true, // User confirmed via dialog
      }),
    });
  },
  onSuccess: (data) => {
    if (!data.success) {
      toast('Deploy Failed', { variant: 'destructive' });
      return;
    }
    queryClient.invalidateQueries({ queryKey: ['project-diff', entity.id] });
    toast('Deploy Successful');
  },
});
```

**Backend Logic** (lines 2898-3000 of artifacts.py):
1. Validate project path exists
2. Load collection and find artifact
3. Create DeploymentManager
4. Call `deployment_mgr.deploy_artifacts()` with overwrite flag
5. Update deployment tracker in `.skillmeat-deployed.toml`
6. Return deployment result

**Confirmation Dialog**: Shows artifact name and project path before executing

---

### Direction 3: Push Project → Collection (Capture Local Edits)

**Trigger**: User clicks "Push to Collection" button in banner/footer

**API Endpoint**: `POST /api/v1/artifacts/{id}/sync`
- Request body: `{ project_path, force: false, strategy: 'theirs' }`
- Presence of `project_path` triggers project→collection sync

**Mutation**:
```typescript
const pushToCollectionMutation = useMutation({
  mutationFn: async () => {
    return await apiRequest<ArtifactSyncResponse>(
      `/artifacts/${encodeURIComponent(entity.id)}/sync`,
      {
        method: 'POST',
        body: JSON.stringify({
          project_path: projectPath,
          force: false,
          strategy: 'theirs', // "theirs" = take project version
        }),
      }
    );
  },
  onSuccess: (data) => {
    if (data.conflicts?.length > 0) {
      toast('Push completed with conflicts');
    } else {
      toast('Push Successful');
    }
    queryClient.invalidateQueries({ queryKey: ['project-diff'] });
    queryClient.invalidateQueries({ queryKey: ['artifacts'] });
  },
});
```

**Confirmation Dialog**: Warns that collection version will be overwritten

---

## 3. DIFF VIEWER COMPONENT

**File**: `/skillmeat/web/components/entity/diff-viewer.tsx` (477 lines)

### Props
```typescript
interface DiffViewerProps {
  files: FileDiff[];
  leftLabel?: string;      // e.g., "Collection"
  rightLabel?: string;     // e.g., "Project"
  showResolutionActions?: boolean;
  onResolve?: (resolution: ResolutionType) => void;
  localLabel?: string;     // Custom label for local version
  remoteLabel?: string;    // Custom label for remote version
  previewMode?: boolean;
  isResolving?: boolean;
}

export type ResolutionType = 'keep_local' | 'keep_remote' | 'merge';
```

### Features

1. **File sidebar** with expandable items
   - Status badges (added/modified/deleted/unchanged)
   - Change stats (additions/deletions count)
   - Click to select file for detailed view

2. **Side-by-side diff panels**
   - Left: Collection version
   - Right: Project/Source version
   - Color-coded lines (green=additions, red=deletions)
   - Line numbers for both sides
   - Independent scrollbars

3. **Unified diff parsing**
   ```typescript
   function parseDiff(unifiedDiff: string): ParsedDiffLine[] {
     // Parse @@...@@ hunk headers
     // Track line numbers for left/right sides
     // Handle additions (+), deletions (-), context lines
   }
   ```

4. **Summary statistics**
   ```typescript
   const summary = {
     added: number,
     modified: number,
     deleted: number,
     unchanged: number,
   };
   ```

5. **Resolution actions** (when `showResolutionActions={true}`)
   - "Keep Local (Project)" button
   - "Keep Remote (Collection)" button
   - "Merge" button (placeholder for manual merge)

---

## 4. DRIFT ALERT BANNER

**File**: `/skillmeat/web/components/sync-status/drift-alert-banner.tsx` (200+ lines)

### Status Indicators

| Status | Icon | Background | Meaning |
|--------|------|-----------|---------|
| `'none'` | CheckCircle2 | Green | All synced |
| `'modified'` | Edit | Amber | Drift detected |
| `'outdated'` | Clock | Orange | Updates available |
| `'conflict'` | AlertTriangle | Red | Conflicts exist |

### Actions by Status

**Drift detected** (modified):
- "View Diffs" button
- "Take Upstream" button (apply upstream changes)
- "Keep Local" button (dismiss drift)

**Updates available** (outdated):
- "Pull from Source" button

**Conflicts** (conflict):
- "Merge Conflicts" button (opens MergeWorkflowDialog)
- "Resolve All" button (auto-resolve placeholder)

---

## 5. MERGE/CONFLICT RESOLUTION

**File**: `/skillmeat/web/components/merge/merge-workflow-dialog.tsx` (408 lines)

### 5-Step Workflow

```
1. Analyze → 2. Preview → 3. Resolve → 4. Confirm → 5. Execute
```

**Step 1: Analyze**
- Calls `useAnalyzeMerge()` hook
- Detects conflicts (modified/added/deleted files)
- Shows "Analyzing merge safety..." state

**Step 2: Preview**
- Calls `usePreviewMerge()` hook
- Shows merged file list
- Displays potential conflicts

**Step 3: Resolve**
- Split view: ConflictList (left) + ConflictResolver (right)
- User selects conflict and chooses resolution
- Tracks `unresolvedConflicts` and `resolvedConflicts` in state

**Step 4: Confirm**
- MergeStrategySelector (`'auto' | 'manual'`)
- Summary: files to merge, conflicts resolved, strategy selected

**Step 5: Execute**
- Calls `useExecuteMerge()` mutation
- Shows progress indicator with file statuses
- Auto-snapshot created

### Resolution Request

```typescript
interface ConflictResolveRequest {
  filePath: string;
  resolution: 'keep_local' | 'keep_remote' | 'merge';
}
```

### State Machine

```typescript
type MergeWorkflowState = {
  step: 'analyze' | 'preview' | 'resolve' | 'confirm' | 'execute';
  analysis?: MergeSafetyResponse;
  preview?: MergePreviewResponse;
  unresolvedConflicts: ConflictMetadata[];
  resolvedConflicts: Map<filePath, resolution>;
  strategy: 'auto' | 'manual';
};
```

---

## 6. API ENDPOINTS (Backend)

### Endpoint Summary

| Endpoint | Method | Direction | Purpose |
|----------|--------|-----------|---------|
| `/artifacts/{id}/sync` | POST | Pull Source→Collection or Project→Collection | Sync from upstream or project |
| `/artifacts/{id}/deploy` | POST | Push Collection→Project | Deploy to project |
| `/artifacts/{id}/diff` | GET | Compare Collection vs Project | Show project drift |
| `/artifacts/{id}/upstream-diff` | GET | Compare Source vs Collection | Show upstream updates |

### POST /artifacts/{id}/sync

**Request body**:
```json
{
  "project_path": "/path/to/project",  // Optional: if present, syncs from project
  "force": false,                        // Optional: force without prompts
  "strategy": "theirs"                   // Optional: 'ours', 'theirs', 'manual'
}
```

**Response** (ArtifactSyncResponse):
```json
{
  "success": boolean,
  "message": string,
  "artifact_name": string,
  "artifact_type": string,
  "conflicts": [
    {
      "filePath": "SKILL.md",
      "conflictType": "modified",
      "currentVersion": "...",
      "upstreamVersion": "..."
    }
  ],
  "updated_version": "v1.1.0",
  "synced_files_count": 5
}
```

### POST /artifacts/{id}/deploy

**Request body**:
```json
{
  "project_path": "/path/to/project",
  "overwrite": true
}
```

**Response**:
```json
{
  "success": boolean,
  "message": string,
  "artifact_name": string,
  "artifact_type": string,
  "error_message": "..."
}
```

### GET /artifacts/{id}/diff

**Query params**:
- `project_path` (required): Path to project

**Response** (ArtifactDiffResponse):
```json
{
  "artifact_id": "skill:my-skill",
  "artifact_name": "my-skill",
  "artifact_type": "skill",
  "project_path": "/path",
  "has_changes": true,
  "files": [
    {
      "file_path": "SKILL.md",
      "status": "modified",
      "collection_hash": "abc123",
      "project_hash": "def456",
      "unified_diff": "--- a/SKILL.md\\n+++ b/SKILL.md\\n..."
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

### GET /artifacts/{id}/upstream-diff

**Query params**:
- `collection` (optional): Collection name

**Response** (ArtifactUpstreamDiffResponse):
```json
{
  "artifact_id": "skill:my-skill",
  "artifact_name": "my-skill",
  "artifact_type": "skill",
  "collection_name": "default",
  "upstream_source": "anthropics/skills/pdf",
  "upstream_version": "abc123def456",
  "has_changes": true,
  "files": [...],
  "summary": {...}
}
```

---

## 7. VALIDATION & GUARDS

### hasValidUpstreamSource()

**File**: `/skillmeat/web/lib/sync-utils.ts`

```typescript
export function hasValidUpstreamSource(artifact: Artifact): boolean {
  return (
    artifact.origin === 'github' &&
    artifact.upstream?.enabled === true &&
    !!artifact.source &&
    artifact.source !== 'local' &&
    artifact.source !== 'unknown'
  );
}
```

**Gate conditions**:
- ✓ GitHub origin required (excludes marketplace, local)
- ✓ Upstream tracking must be enabled
- ✓ Source must be a valid remote path
- ✗ Marketplace artifacts: always false
- ✗ Local artifacts: always false

**Used by**:
- ComparisonSelector (enables/disables scope options)
- SyncStatusTab (enables upstream diff query)
- ArtifactFlowBanner (disables Pull button when invalid)

---

## 8. CURRENT STATE BY SYNC DIRECTION

### Pull from Source → Collection ✅ IMPLEMENTED

**Status**: Fully implemented and working

**Flow**:
1. User clicks "Pull from Source" in banner
2. Confirmation dialog shown
3. `syncMutation` called with empty body
4. Backend calls `fetch_update()` and `apply_update_strategy()`
5. Conflicts returned if detected
6. Cache invalidated

**Conflict handling**:
- Detected via unified diff parsing for `<<<<<<< ` markers
- Returned in response
- User prompted to merge via MergeWorkflowDialog

### Deploy Collection → Project ✅ IMPLEMENTED

**Status**: Fully implemented and working

**Flow**:
1. User clicks "Deploy to Project" in banner
2. Confirmation dialog with artifact name and project path
3. `deployMutation` called with `overwrite: true`
4. Backend calls DeploymentManager
5. Files copied to project `.claude/` directory
6. Deployment tracked in `.skillmeat-deployed.toml`
7. Cache invalidated

**Note**: Only one-way push (Collection → Project). No pull from project to collection yet implemented in banner.

### Push Project → Collection (Pull from Project) ⚠️ PARTIAL

**Status**: Partially implemented

**What works**:
- Footer has "Push Local Changes" button
- `pushToCollectionMutation` defined (lines 416-450)
- API endpoint `/artifacts/{id}/sync` with `project_path` parameter
- Backend logic exists (see sync_artifact endpoint)

**What's missing**:
- No confirmation dialog for push operation
- No visual indicator in ArtifactFlowBanner for this direction (arrow is dashed/disabled)
- Pull from Project → Collection NOT yet exposed in main UI
- Limited testing/validation

---

## 9. MISSING FEATURES & GAPS

### 1. **Source vs Project Comparison**
- Code path exists in SyncStatusTab (line 554-555)
- Returns projectDiff as placeholder
- Real implementation would compare Source directly with Project

### 2. **Manual Merge Resolution**
- DiffViewer has "Merge" button
- Title says "coming soon"
- No conflict marker resolution UI implemented

### 3. **Resolve All Button**
- Footer has "Resolve All" button
- Currently shows toast("Coming Soon")
- Should auto-resolve all conflicts with a strategy

### 4. **Project Pull/Capture in Banner**
- Push button in banner uses dashed line (disabled visual)
- No action button on Project→Collection connector
- Requires UX design for this less-common direction

### 5. **Sync Status Persistence**
- Drift status only dismissable via "Keep Local" button
- Dismissed status stored in local React state
- No persistence to backend/localStorage
- Resets on page refresh

### 6. **Conflict Marker Heuristics**
- Current detection looks for `<<<<<<< ` in unified_diff
- Doesn't verify proper 3-way merge structure
- May miss edge cases

---

## 10. FILE LOCATIONS SUMMARY

### Frontend Components
| File | Lines | Purpose |
|------|-------|---------|
| `components/sync-status/sync-status-tab.tsx` | 830 | Main orchestrator |
| `components/sync-status/artifact-flow-banner.tsx` | 292 | 3-tier visualization |
| `components/sync-status/comparison-selector.tsx` | ~100 | Scope selector |
| `components/sync-status/drift-alert-banner.tsx` | ~200 | Status alerts & actions |
| `components/sync-status/sync-actions-footer.tsx` | 99 | Footer buttons |
| `components/entity/diff-viewer.tsx` | 477 | File-level diff display |
| `components/merge/merge-workflow-dialog.tsx` | 408 | Conflict resolution wizard |

### Frontend Hooks
| File | Purpose |
|------|---------|
| `hooks/useSync.ts` | Mutation for sync operations |
| `hooks/use-merge.ts` | Mutations for merge workflow |
| `lib/sync-utils.ts` | Validation helper (hasValidUpstreamSource) |

### Backend Routers
| File | Relevant Lines |
|------|---|
| `api/routers/artifacts.py` | 2898 (deploy), 3061 (sync), 3693 (diff), 4055 (upstream-diff) |

---

## 11. DATA FLOW ORCHESTRATION

### Query Invalidation Graph

After successful sync/deploy/push:

```
Invalidate on PULL from source:
  ✓ ['upstream-diff', entity.id, collection]
  ✓ ['project-diff', entity.id]
  ✓ ['artifacts']
  ✓ ['deployments']
  ✓ ['collections']

Invalidate on DEPLOY to project:
  ✓ ['project-diff', entity.id]
  ✓ ['upstream-diff', entity.id, collection]
  ✓ ['artifacts']
  ✓ ['deployments']

Invalidate on PUSH to collection:
  ✓ ['project-diff', entity.id]
  ✓ ['upstream-diff', entity.id, collection]
  ✓ ['artifacts']
  ✓ ['deployments']
  ✓ ['collections']
```

---

## 12. USER JOURNEY: Drift → Resolution

### Scenario: User sees upstream update available

1. **Discovery**
   - SyncStatusTab opens with artifact
   - `hasValidUpstreamSource()` returns true
   - Upstream diff query fires automatically
   - DriftAlertBanner shows "Updates Available" (orange)

2. **Inspection**
   - User selects "source-vs-collection" in ComparisonSelector
   - DiffViewer shows file changes from Source to Collection
   - User reviews each file

3. **Decision Point**
   - Option A: Click "Pull from Source" button
     - Shows confirmation dialog
     - Sync mutation executes
     - Cache invalidates, page refreshes

   - Option B: Click "Merge Conflicts" (if conflicts detected)
     - MergeWorkflowDialog opens
     - 5-step merge workflow starts
     - After merge, cache invalidates

4. **Completion**
   - Toast notification shows result
   - Drift status updates to 'none'
   - Flow banner shows Collection version updated

---

## 13. KEY INSIGHTS & ARCHITECTURE NOTES

### Design Patterns

1. **Comparison Scope Pattern**
   - Single component switches between 2 diff queries
   - Left/right labels adjusted based on scope
   - Enables flexible 2-way/3-way comparisons

2. **Mutation-Driven Invalidation**
   - No optimistic updates
   - All mutations invalidate related caches
   - Forces full re-fetch after operations

3. **Early Validation**
   - `hasValidUpstreamSource()` gates upstream features
   - Prevents invalid API calls
   - Provides clear UX feedback

4. **Drift Dismissal**
   - Local React state tracks dismissed drifts
   - No backend persistence
   - Temporary during session

### Stale Times

Based on CLAUDE.md:
- **Artifacts**: 5 min
- **Deployments**: 2 min
- **Diffs**: Immediate (no caching, always fresh)

---

## 14. RECOMMENDATIONS

### High Priority

1. **Implement "Source vs Project" comparison**
   - Add query for direct source→project diff
   - Update ComparisonSelector option
   - Bypass collection for direct comparison

2. **Fix Project→Collection Arrow**
   - Make dashed arrow solid when deployment exists
   - Add action button with clear intent
   - Consider secondary action vs primary

3. **Persist Drift Dismissal**
   - Store dismissal preference in localStorage
   - Include collection+artifact as key
   - Clear on update detection

### Medium Priority

1. **Manual Merge UI**
   - Implement conflict marker resolution
   - Visual editor for choosing sections
   - Preview final result

2. **Resolve All Strategy**
   - Add dialog to choose strategy
   - Execute in background
   - Show progress

3. **Bulk Sync Operations**
   - Sync multiple artifacts at once
   - Progress indicator for batch
   - Rollback on first failure

### Low Priority

1. **Sync History**
   - Track sync operations in database
   - Show timeline in modal
   - Revert to previous state

2. **Merge Strategies Documentation**
   - Add tooltips explaining 'ours'/'theirs'/'manual'
   - Link to conflict resolution guide

---

## Conclusion

The SkillMeat sync workflow is **well-architected** with clear separation of concerns:

- **UI orchestration** in SyncStatusTab
- **Diff display** in DiffViewer
- **Conflict resolution** in MergeWorkflowDialog
- **API contracts** via ArtifactSyncResponse/DiffResponse

The **3-tier flow visualization** provides excellent UX clarity. The main gaps are around **Project→Collection direction** (partially exposed in footer, missing from banner) and **manual merge conflict resolution** (UI not yet implemented).

The system is **production-ready** for Source→Collection and Collection→Project flows. Project→Collection would benefit from UX refinement before prominent exposure.
