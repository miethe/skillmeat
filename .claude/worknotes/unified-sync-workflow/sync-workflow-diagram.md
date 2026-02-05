# SkillMeat Sync Workflow: Visual Architecture

## 1. 3-Tier Sync Architecture (Data Flow)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GITHUB (Upstream Source)                            │
│                            github.com/user/repo                            │
└──────────────────────────────────────────┬──────────────────────────────────┘
                                           │
                        ↓ Pull (sync_artifact, no project_path)
                        ↑ (upstream-diff query)
                                           │
┌──────────────────────────────────────────▼──────────────────────────────────┐
│                      COLLECTION (Local ~/.skillmeat)                        │
│                         Default: ~/.skillmeat/artifacts                     │
│                                                                             │
│  artifact.json  ←← Metadata, version, origin="github"                      │
│  SKILL.md       ←← Artifact files                                          │
│  ...                                                                        │
└──────────────────────────────────────────┬──────────────────────────────────┘
                                           │
                        ↓ Deploy (deploy_artifact, overwrite: true)
                        ↑ (project-diff query)
                                           │
┌──────────────────────────────────────────▼──────────────────────────────────┐
│                         PROJECT (.claude directory)                         │
│                       ~/my-project/.claude/skills/my-skill                 │
│                                                                             │
│  SKILL.md                 ← Deployed artifact files                        │
│  ...                                                                        │
│                                                                             │
│  .skillmeat-deployed.toml  ← Deployment tracker (created on deploy)        │
│                             Records: from_collection, artifact_path        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Hierarchy (SyncStatusTab)

```
SyncStatusTab (orchestrator)
│
├─ ArtifactFlowBanner (3-tier visualization)
│  ├─ Source Node (GitHub icon)
│  │  ├─ Version badge
│  │  ├─ SHA display
│  │  └─ "New Update" badge (if has changes)
│  │
│  ├─ Connector 1: Source → Collection
│  │  └─ Button: "Pull from Source" (onClick: handlePullFromSource)
│  │
│  ├─ Collection Node (Layers icon)
│  │  ├─ Version badge
│  │  └─ SHA display
│  │
│  ├─ Connector 2: Collection → Project
│  │  └─ Button: "Deploy to Project" (onClick: handleDeployToProject)
│  │
│  ├─ Project Node (Folder icon)
│  │  ├─ Version badge
│  │  ├─ SHA display
│  │  └─ "Modified" badge (if isModified)
│  │
│  └─ Connector 3: Project → Collection (dashed/disabled)
│     └─ Button: "Push to Collection" (onClick: handlePushToCollection)
│
├─ ComparisonSelector
│  └─ Radio/Select
│     ├─ "Source vs Collection" (enabled if hasValidUpstreamSource)
│     ├─ "Collection vs Project" (enabled if hasProject)
│     └─ "Source vs Project" (TODO: disabled)
│
├─ DriftAlertBanner
│  ├─ Status icon (CheckCircle / Edit / Clock / AlertTriangle)
│  ├─ Status text ("All Synced" / "Drift Detected" / etc.)
│  ├─ Summary (added: 2, modified: 1, deleted: 0)
│  └─ Action buttons
│     ├─ "View Diffs"
│     ├─ "Take Upstream" (if drift)
│     ├─ "Keep Local" (if drift)
│     ├─ "Merge Conflicts" (if conflict)
│     └─ "Resolve All" (if conflict)
│
├─ DiffViewer
│  ├─ File sidebar
│  │  ├─ File 1
│  │  │  ├─ Expand toggle
│  │  │  ├─ File path
│  │  │  ├─ Status badge (Added/Modified/Deleted)
│  │  │  └─ Stats (1 addition, 2 deletions)
│  │  └─ File 2
│  │     ...
│  │
│  ├─ Left panel: [leftLabel] (e.g., "Collection")
│  │  └─ Unified diff lines (with line numbers)
│  │     ├─ Context lines (gray)
│  │     ├─ Deleted lines (red with -)
│  │     └─ Header lines (@@...@@)
│  │
│  └─ Right panel: [rightLabel] (e.g., "Project")
│     └─ Unified diff lines (with line numbers)
│        ├─ Context lines (gray)
│        ├─ Added lines (green with +)
│        └─ Header lines (@@...@@)
│
└─ SyncActionsFooter
   ├─ Left: Action buttons
   │  ├─ "Pull Collection Updates" (primary blue)
   │  ├─ "Push Local Changes" (ghost)
   │  ├─ "Merge Conflicts" (orange, if hasConflicts)
   │  └─ "Resolve All" (outline, if hasConflicts)
   │
   └─ Right: Control buttons
      ├─ "Cancel" (outline)
      └─ "Apply Sync Actions" (primary, if hasPendingActions)

SyncDialog (overlay for merge workflow)
└─ MergeWorkflowDialog
   ├─ Step 1: Analyze
   │  └─ Spinner + "Analyzing merge safety..."
   │
   ├─ Step 2: Preview
   │  └─ MergePreviewView (files added/changed)
   │
   ├─ Step 3: Resolve
   │  ├─ ConflictList (left panel)
   │  │  └─ Conflicts with resolution status
   │  │
   │  └─ ConflictResolver (right panel)
   │     ├─ Selected conflict details
   │     ├─ Current version preview
   │     ├─ Upstream version preview
   │     └─ Resolution buttons
   │        ├─ "Keep Local (Project)"
   │        ├─ "Keep Remote (Collection)"
   │        └─ "Merge" (manual editor - TODO)
   │
   ├─ Step 4: Confirm
   │  ├─ MergeStrategySelector ("auto" / "manual")
   │  └─ Summary box
   │     ├─ Files to merge: N
   │     ├─ Conflicts resolved: M
   │     └─ Strategy: [badge]
   │
   └─ Step 5: Execute
      └─ MergeProgressIndicator
         ├─ Total files: N
         ├─ Processed: 0
         └─ File statuses [pending...]
```

---

## 3. API Call Sequence (Pull from Source)

```
User clicks "Pull from Source"
│
├─ Show confirmation dialog
│  └─ User confirms
│
├─ POST /api/v1/artifacts/{id}/sync
│  │
│  └─ Request body: {}
│     (empty = pull from upstream)
│
└─ Backend logic:
   ├─ Parse artifact ID
   ├─ Load collection, find artifact
   ├─ Verify artifact.origin == "github"
   ├─ fetch_update()
   │  └─ GitHub API: get latest version
   │
   ├─ apply_update_strategy()
   │  ├─ Strategy = "overwrite" (default)
   │  └─ Copy files from upstream to collection
   │
   ├─ Detect conflicts
   │  └─ Check for <<<<<<< markers in unified_diff
   │
   └─ Return ArtifactSyncResponse
      ├─ success: true/false
      ├─ message: "Sync Successful" / "Conflicts detected"
      ├─ conflicts: [...]  (if any)
      └─ updated_version: "v1.1.0"

Frontend receives response
│
├─ Check data.conflicts
│  ├─ If conflicts: show toast warning, open MergeWorkflowDialog
│  └─ If no conflicts: show toast success
│
└─ Invalidate caches
   ├─ ['upstream-diff', id, collection]
   ├─ ['project-diff', id]
   ├─ ['artifacts']
   ├─ ['deployments']
   └─ ['collections']
```

---

## 4. API Call Sequence (Deploy to Project)

```
User clicks "Deploy to Project"
│
├─ Show confirmation dialog
│  │  Message: "Overwrite project version with collection?"
│  │  Details: artifact name, project path
│  │
│  └─ User confirms
│
├─ POST /api/v1/artifacts/{id}/deploy
│  │
│  └─ Request body:
│     {
│       "project_path": "/Users/me/project",
│       "overwrite": true
│     }
│
└─ Backend logic:
   ├─ Validate project_path exists
   ├─ Load collection, find artifact
   ├─ Create DeploymentManager
   ├─ deploy_artifacts()
   │  ├─ Copy artifact files to project/.claude/
   │  ├─ Update .skillmeat-deployed.toml
   │  └─ Return deployment record
   │
   └─ Return ArtifactDeployResponse
      ├─ success: true/false
      ├─ message: "Deployment successful"
      └─ error_message?: "..." (if failed)

Frontend receives response
│
├─ Check data.success
│  ├─ If success: show toast "Deploy Successful"
│  └─ If failed: show toast error
│
└─ Invalidate caches
   ├─ ['project-diff', id]
   ├─ ['upstream-diff', id, collection]
   ├─ ['artifacts']
   └─ ['deployments']
```

---

## 5. Query Flow (Diff Data)

```
SyncStatusTab component mounts
│
├─ Read props
│  ├─ entity (artifact)
│  ├─ mode ("collection" | "project")
│  ├─ projectPath (optional)
│  └─ onClose
│
├─ Initialize state
│  ├─ comparisonScope = "collection-vs-project" (default if mode=project)
│  │                    "source-vs-collection" (default if mode=collection AND hasSource)
│  ├─ dismissedDriftIds = Set()
│  └─ pendingActions = []
│
├─ Upstream diff query (enabled: hasValidUpstreamSource(entity))
│  │
│  └─ GET /api/v1/artifacts/{id}/upstream-diff?collection={name}
│     ├─ Compare: Source → Collection
│     ├─ Returns: files[], has_changes, summary
│     └─ Stale time: 5 min (default)
│        Cache key: ['upstream-diff', id, collection]
│
├─ Project diff query (enabled: !!projectPath)
│  │
│  └─ GET /api/v1/artifacts/{id}/diff?project_path={path}
│     ├─ Compare: Collection → Project
│     ├─ Returns: files[], has_changes, summary
│     └─ Stale time: 5 min (default)
│        Cache key: ['project-diff', id, projectPath]
│
└─ User changes comparisonScope
   │
   ├─ Switch displayed diff to currentDiff
   │  (upstreamDiff | projectDiff based on scope)
   │
   ├─ Compute driftStatus = computeDriftStatus(currentDiff)
   │  ├─ Check has_changes
   │  ├─ Check for <<<<<<< markers
   │  └─ Return: 'none' | 'modified' | 'conflict'
   │
   └─ DriftAlertBanner re-renders with new status
```

---

## 6. Validation Gate: hasValidUpstreamSource()

```
function hasValidUpstreamSource(artifact: Artifact): boolean {

  ┌─ Check 1: Origin must be "github"
  │  ├─ "github" ✓
  │  ├─ "marketplace" ✗
  │  ├─ "local" ✗
  │  └─ "unknown" ✗
  │
  ├─ Check 2: Upstream tracking must be enabled
  │  ├─ artifact.upstream.enabled === true ✓
  │  └─ artifact.upstream.enabled === false ✗
  │
  └─ Check 3: Source must be a valid remote path
     ├─ "user/repo" ✓
     ├─ "anthropics/skills/pdf" ✓
     ├─ "local" ✗
     ├─ "unknown" ✗
     └─ "" ✗
}
```

**Used to:**
- Gate upstream diff queries
- Enable/disable "Pull from Source" button
- Show/hide "Source vs Collection" comparison option
- Prevent invalid API calls

---

## 7. Drift Detection & Actions

```
Upstream diff loaded
│
├─ Has changes? has_changes: true
│  │
│  ├─ Has conflict markers (<<<<<<< ) in unified_diff?
│  │  │
│  │  ├─ YES → Status = "conflict"
│  │  │         Actions: [Merge Conflicts] [Resolve All]
│  │  │
│  │  └─ NO → Status = "modified" or "outdated"
│  │          Actions: [Take Upstream] [Keep Local] [Merge]
│  │
│  └─ If dismissed by user
│     └─ Status = "none" (local state override)
│
└─ No changes? has_changes: false
   │
   └─ Status = "none"
      Actions: [] (no drift actions shown)
```

---

## 8. Merge Workflow: State Progression

```
Initial state:
{
  step: "analyze",
  unresolvedConflicts: [],
  resolvedConflicts: Map(),
  strategy: "auto"
}

↓ Click Next / handleAnalyze()

{
  step: "preview",
  analysis: MergeSafetyResponse,
  unresolvedConflicts: analysis.conflicts,
  resolvedConflicts: Map(),
  strategy: "auto"
}

↓ Click Next / handlePreview()

{
  step: "resolve",
  preview: MergePreviewResponse,
  unresolvedConflicts: [...],  // User resolves one by one
  resolvedConflicts: Map(filePath -> resolution),
  strategy: "auto"
}

↓ User resolves all conflicts / handleResolveConflict()

{
  step: "resolve",
  unresolvedConflicts: [],  // Empty!
  resolvedConflicts: Map(all files),
  strategy: "auto"
}

↓ Click Next / canProceed() returns true

{
  step: "confirm",
  unresolvedConflicts: [],
  resolvedConflicts: Map(),
  strategy: "auto" | "manual"  // User can change here
}

↓ Click "Execute Merge" / handleExecute()

{
  step: "execute",
  unresolvedConflicts: [],
  resolvedConflicts: Map(),
  strategy: "auto" | "manual"
}

↓ executeMerge.mutateAsync() completes

Dialog closes
Cache invalidates
Toast shows: "Merged 5 files successfully"
```

---

## 9. Cache Invalidation Graph

```
SYNC (Pull from Source)
│
├─ upstreamDiff invalidated
├─ projectDiff invalidated
├─ artifacts invalidated
├─ deployments invalidated
└─ collections invalidated

DEPLOY (Push to Project)
│
├─ projectDiff invalidated
├─ upstreamDiff invalidated
├─ artifacts invalidated
└─ deployments invalidated

PUSH (Pull from Project)
│
├─ projectDiff invalidated
├─ upstreamDiff invalidated
├─ artifacts invalidated
├─ deployments invalidated
└─ collections invalidated

MERGE
│
├─ snapshots invalidated
└─ collections[specific] invalidated
```

---

## 10. File Status Icons & Colors

```
┌────────────┬────────────┬──────────────────┐
│   Status   │    Icon    │      Color       │
├────────────┼────────────┼──────────────────┤
│   Added    │     ✚      │   Green (#10b981)│
│ Modified   │     ~      │    Blue (#3b82f6)│
│  Deleted   │     ✕      │    Red (#ef4444) │
│ Unchanged  │     ·      │  Gray (#9ca3af)  │
└────────────┴────────────┴──────────────────┘

Diff lines:
  Green background (green-500/10): Additions
  Red background (red-500/10): Deletions
  Gray background: Context (unchanged)
  Gray background: Header (@@ ... @@)
```

---

## 11. Error Handling Flow

```
API Call
│
├─ Network error
│  └─ Toast: "Failed to load diff: {error.message}"
│     Render: <Alert variant="destructive">
│
├─ 404 Not Found
│  └─ Toast: "Artifact not found"
│     Check: !hasUpstreamData && !projectError
│     Show: Error alert
│
├─ 400 Bad Request
│  └─ Toast: "Invalid request: {error.message}"
│     Example: Missing project_path
│
├─ 500 Internal Server Error
│  └─ Toast: "Server error"
│     Render: <Alert>Failed to load diff...</Alert>
│
└─ Success
   └─ Show DiffViewer with data
```

---

## 12. Edge Cases & Handling

```
Scenario: Artifact has no upstream source
│
├─ hasValidUpstreamSource() = false
├─ Upstream diff query: disabled
├─ ComparisonSelector
│  ├─ "Source vs Collection" option: disabled
│  └─ Default: "Collection vs Project"
└─ ArtifactFlowBanner
   └─ Source node: "Not configured" + dashed border

Scenario: Artifact has no project deployment
│
├─ projectPath = undefined
├─ Project diff query: disabled
├─ ComparisonSelector
│  ├─ "Collection vs Project" option: disabled
│  └─ Default: "Source vs Collection"
└─ ArtifactFlowBanner
   └─ Project node: "Not deployed" + dashed border

Scenario: Discovered artifact (collection = "discovered")
│
├─ Early return in SyncStatusTab (line 573)
├─ Message: "Sync status is not available for discovered artifacts"
├─ Action: "Import this artifact to your collection to enable sync tracking"
└─ No diff queries, no sync operations

Scenario: Collection version matches upstream (no updates)
│
├─ upstream_diff.has_changes = false
├─ upstreamDiff query returns empty files[]
├─ driftStatus = "none"
└─ DriftAlertBanner shows "All Synced" (green)
```

---

## Summary

The SkillMeat sync workflow is organized as:

1. **Single orchestrator** (SyncStatusTab) managing all sync operations
2. **Three distinct API flows** (pull/push/deploy) with clear request/response contracts
3. **Layered diff visualization** (ArtifactFlowBanner → ComparisonSelector → DriftAlertBanner → DiffViewer)
4. **Conflict resolution wizard** (MergeWorkflowDialog with 5-step state machine)
5. **Validation gates** (hasValidUpstreamSource) preventing invalid operations
6. **Cache invalidation** triggering full refreshes on all mutations
