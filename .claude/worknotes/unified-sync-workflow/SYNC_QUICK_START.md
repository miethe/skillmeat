# SkillMeat Sync Workflow: Quick Start Guide

## For Quick Navigation

**Main documentation**: `sync-workflow-exploration.md`
**Visual diagrams**: `sync-workflow-diagram.md`
**API reference**: `sync-endpoints-reference.md`

---

## The 3-Tier Sync Flows (One Sentence Each)

1. **Pull from Source → Collection**: User clicks "Pull from Source" → Backend fetches latest from GitHub → Conflicts returned if changes conflict
2. **Deploy Collection → Project**: User clicks "Deploy to Project" → Backend copies files to project `.claude/` → Updates deployment tracker
3. **Push Project → Collection**: User clicks "Push Local Changes" → Backend copies project version back to collection

---

## File Locations (Copy-Paste Ready)

### Main Orchestrator
```
/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/sync-status/sync-status-tab.tsx
```
Lines 197-827: Main component
- Line 224-243: Upstream diff query setup
- Line 246-259: Project diff query setup
- Line 266-298: Sync mutation (pull from source)
- Line 301-342: Deploy mutation
- Line 416-450: Push to collection mutation

### 3-Tier Flow Visualization
```
/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/sync-status/artifact-flow-banner.tsx
```
Lines 65-291: Main component
- Source → Collection button (line 113-149)
- Collection → Project button (line 166-202)
- Project → Collection button (line 249-287)

### Diff Viewer (File-by-File Comparison)
```
/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/entity/diff-viewer.tsx
```
Lines 191-476: DiffViewer component
- Line 76-128: parseDiff() function
- Line 282-343: File sidebar with selection
- Line 356-409: Side-by-side diff panels

### Conflict Resolution Wizard
```
/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/merge/merge-workflow-dialog.tsx
```
Lines 53-407: MergeWorkflowDialog component
- State machine: analyze → preview → resolve → confirm → execute
- Line 91-103: handleAnalyze
- Line 119-152: handleResolveConflict

### API Endpoints (Backend)
```
/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/artifacts.py
```
- Line 3061: `async def sync_artifact()` - Pull from upstream OR project
- Line 2898: `async def deploy_artifact()` - Deploy to project
- Line 3693: `async def get_artifact_diff()` - Collection vs Project
- Line 4055: `async def get_artifact_upstream_diff()` - Source vs Collection

---

## Common Tasks

### Add a Pull from Source Button
1. Location: `artifact-flow-banner.tsx` lines 113-149
2. Already exists as "Pull from Source" on connector 1
3. Calls `onPullFromSource()` prop (line 131)
4. Disabled when `!sourceInfo` (line 133)

### Add Manual Merge Editor
1. Location: `diff-viewer.tsx` line 462-470
2. "Merge" button currently placeholder
3. Need to implement `onResolve?.('merge')` handler
4. Show conflict markers and allow selection

### Fix Project→Collection in Banner
1. Location: `artifact-flow-banner.tsx` lines 248-287
2. Currently dashed line (disabled visual)
3. Change: `strokeDasharray={projectInfo ? undefined : '4 4'}` (line 256)
4. Add confirmation dialog in SyncStatusTab

### Expose Push Button Prominently
1. Location: `artifact-flow-banner.tsx` line 267-286
2. Already exists but looks disabled (dashed line)
3. SyncStatusTab footer also has "Push Local Changes" (line 651)
4. Recommendation: Add to main action buttons with confirmation

---

## State Machine: Merge Workflow

```javascript
// Initial
{ step: 'analyze', unresolvedConflicts: [], strategy: 'auto' }

// After analyze
{ step: 'preview', analysis: {...}, unresolvedConflicts: [...] }

// After preview
{ step: 'resolve', unresolvedConflicts: [...] }

// User resolves each conflict
{ step: 'resolve', unresolvedConflicts: [], resolvedConflicts: Map(...) }

// After confirm
{ step: 'confirm', strategy: 'auto' | 'manual' }

// After execute
{ step: 'execute' }

// Done: dialog closes
```

---

## Query Key Invalidation (Cache Bust)

**After pulling from source**:
```javascript
queryClient.invalidateQueries({ queryKey: ['upstream-diff'] });
queryClient.invalidateQueries({ queryKey: ['project-diff'] });
queryClient.invalidateQueries({ queryKey: ['artifacts'] });
queryClient.invalidateQueries({ queryKey: ['deployments'] });
queryClient.invalidateQueries({ queryKey: ['collections'] });
```

**After deploying to project**:
```javascript
queryClient.invalidateQueries({ queryKey: ['project-diff'] });
queryClient.invalidateQueries({ queryKey: ['upstream-diff'] });
queryClient.invalidateQueries({ queryKey: ['artifacts'] });
queryClient.invalidateQueries({ queryKey: ['deployments'] });
```

---

## API Endpoints Cheat Sheet

### Pull from Source
```bash
POST /api/v1/artifacts/{id}/sync
Content-Type: application/json

{}  # Empty body = pull from upstream
```

### Deploy to Project
```bash
POST /api/v1/artifacts/{id}/deploy
Content-Type: application/json

{
  "project_path": "/path/to/project",
  "overwrite": true
}
```

### Get Collection vs Project Diff
```bash
GET /api/v1/artifacts/{id}/diff?project_path=/path/to/project
```

### Get Source vs Collection Diff
```bash
GET /api/v1/artifacts/{id}/upstream-diff?collection=default
```

---

## Validation: When Upstream Sync is Allowed

```javascript
function hasValidUpstreamSource(artifact) {
  return (
    artifact.origin === 'github' &&
    artifact.upstream?.enabled === true &&
    !!artifact.source &&
    artifact.source !== 'local' &&
    artifact.source !== 'unknown'
  );
}
```

**Used to**:
- Enable/disable "Pull from Source" button
- Gate upstream diff queries
- Show/hide "Source vs Collection" comparison option

---

## Conflict Detection

**Location**: `sync-status-tab.tsx` lines 61-72

```javascript
function computeDriftStatus(diffData) {
  if (!diffData || !diffData.has_changes) return 'none';

  // Check for conflict markers
  const hasConflicts = diffData.files.some((f) =>
    f.unified_diff?.includes('<<<<<<< ')
  );

  return hasConflicts ? 'conflict' : 'modified';
}
```

Returns: `'none' | 'modified' | 'outdated' | 'conflict'`

---

## Current Limitations

### ❌ Not Yet Implemented
1. **Manual merge UI** - ConflictResolver shows "Merge" button but no editor
2. **Source vs Project** - Code path exists but no real implementation
3. **Resolve All** - Button shows "Coming Soon"
4. **Persistent dismissal** - Drift dismissal stored only in React state

### ⚠️ Partial Implementation
1. **Push to Collection** - Button in footer, not in banner
   - No confirmation dialog
   - Dashed/disabled visual in flow banner
   - Needs UX enhancement

---

## Testing Checklist

- [ ] Pull from source with no conflicts → syncs successfully
- [ ] Pull from source with conflicts → shows merge workflow
- [ ] Deploy to project → files copied to `.claude/`
- [ ] Deploy with overwrite=true → updates existing files
- [ ] Diff viewer → shows file-level changes correctly
- [ ] Comparison scope change → switches between upstream/project diffs
- [ ] Drift dismissal → "Keep Local" removes drift alert (session only)
- [ ] Merge workflow → all 5 steps navigate correctly
- [ ] Cache invalidation → page refreshes after operations

---

## Key Insights

### Design Pattern: Comparison Scope
One component switches between 2 diff queries:
- `'source-vs-collection'` → upstream diff query
- `'collection-vs-project'` → project diff query
- Labels adjust: "Source" vs "Project" on left/right panels

### Write-Through Cache
All mutations:
1. Call API endpoint
2. API modifies filesystem
3. Cache key invalidated
4. Frontend refetches

No optimistic updates.

### Early Validation
`hasValidUpstreamSource()` prevents:
- Invalid API calls
- Confusing UI states
- GitHub API quota waste

---

## Next Implementation Tasks

### High Priority
1. **Expose Push to Collection in banner**
   - Make arrow solid (not dashed) when projectPath exists
   - Add action button on Project → Collection connector
   - Show confirmation dialog

2. **Implement manual merge UI**
   - Show conflict markers (<<<<<<< >>>>>>>)
   - Allow visual selection of which side to keep
   - Preview result before applying

3. **Add Source vs Project comparison**
   - Query endpoint (code path exists)
   - Add ComparisonSelector option
   - Bypass collection for direct comparison

### Medium Priority
1. **Persist drift dismissal**
   - localStorage key: `skillmeat-drift-dismissal-{id}`
   - Clear on update detection

2. **Resolve All helper**
   - Dialog: "Resolve conflicts with strategy: [ours/theirs]"
   - Apply to all unresolved
   - Show progress

3. **Bulk sync**
   - Multi-artifact selection
   - Batch progress indicator
   - Rollback on error

---

## Debug Tips

### Check if upstream sync is gated
```javascript
import { hasValidUpstreamSource } from '@/lib/sync-utils';
console.log(hasValidUpstreamSource(artifact));
```

### Inspect diff query state
```javascript
const { data: upstreamDiff, isLoading: upstreamLoading, error: upstreamError } = useQuery(...);
console.log({ upstreamDiff, upstreamLoading, upstreamError });
```

### Check cache after mutation
```javascript
const queryClient = useQueryClient();
queryClient.getQueryData(['upstream-diff', entity.id, entity.collection]);
```

### Test conflict detection
Look for `<<<<<<< ` in unified_diff output

---

## Production Readiness

**✅ Ready**: Pull from source, Deploy to project
**⚠️ Needs work**: Push to collection (backend ready, UI needs enhancement)
**❌ Not ready**: Manual merge editor, Source vs Project comparison
