# Artifact Flow Modal - Implementation Plan

## Overview

Refactor the "Sync Status" tab in `unified-entity-modal.tsx` to match the new 3-panel design with artifact flow visualization. This redesign enables full lifecycle management across Source, Collection, and Project tiers from a single location.

**Design Reference**: `docs/dev/designs/artifact-flow-modal-redesign.md`
**Visual Reference**: `docs/dev/designs/renders/artifact-flow-modal.png`

---

## Architecture

### Component Structure

```
components/entity/sync-status/
├── index.ts                      # Public exports
├── sync-status-tab.tsx           # Main composite component
├── artifact-flow-banner.tsx      # 3-tier flow visualization
├── comparison-selector.tsx       # Compare dropdown controls
├── drift-alert-banner.tsx        # Drift detection alert
├── file-preview-pane.tsx         # Right panel preview
├── sync-actions-footer.tsx       # Bottom action bar
└── types.ts                      # Shared types
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          SyncStatusTab                                   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    ArtifactFlowBanner                             │   │
│  │  [SOURCE] ──Pull──> [COLLECTION] ──Deploy──> [PROJECT]           │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌───────────┬──────────────────────────────────┬──────────────────┐    │
│  │ FileTree  │        ComparisonSelector        │                  │    │
│  │           │        DriftAlertBanner          │  FilePreviewPane │    │
│  │           │        DiffViewer                │                  │    │
│  └───────────┴──────────────────────────────────┴──────────────────┘    │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    SyncActionsFooter                              │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Specifications

### 1. ArtifactFlowBanner

**File**: `components/entity/sync-status/artifact-flow-banner.tsx`

**Purpose**: Visualize the 3-tier artifact flow with status indicators and action buttons.

**Props**:
```typescript
interface ArtifactFlowBannerProps {
  entity: Entity;
  sourceInfo: {
    version: string;
    sha: string;
    hasUpdate: boolean;
    source: string; // GitHub source spec
  } | null;
  collectionInfo: {
    version: string;
    sha: string;
  };
  projectInfo: {
    version: string;
    sha: string;
    isModified: boolean;
    projectPath: string;
  } | null;
  onPullFromSource: () => void;
  onDeployToProject: () => void;
  onPushToCollection: () => void;
  isPulling: boolean;
  isDeploying: boolean;
  isPushing: boolean;
}
```

**Visual Elements**:
- Three nodes with icons (GitHub, Layers, Folder)
- Version and SHA display per node
- Status badges (New Update, Modified)
- Curved connectors with directional arrows
- Action buttons on connectors:
  - "Pull from Source" (Source → Collection)
  - "Deploy to Project" (Collection → Project)
  - "Push to Collection" (Project → Collection) - **Coming Soon**

**Data Sources**:
- `sourceInfo`: From `useQuery` calling `/artifacts/{id}/upstream`
- `collectionInfo`: From entity data
- `projectInfo`: From entity data + selected project

---

### 2. ComparisonSelector

**File**: `components/entity/sync-status/comparison-selector.tsx`

**Purpose**: Control which artifact tiers are being compared.

**Props**:
```typescript
type ComparisonScope =
  | 'collection-vs-project'
  | 'source-vs-collection'
  | 'source-vs-project';

interface ComparisonSelectorProps {
  value: ComparisonScope;
  onChange: (scope: ComparisonScope) => void;
  hasSource: boolean;      // Disable source comparisons if no upstream
  hasProject: boolean;     // Disable project comparisons if not deployed
}
```

**Visual Elements**:
- "Compare:" label
- Primary dropdown (currently selected comparison)
- Quick-switch buttons for other comparison modes
- Disabled states with tooltips when data unavailable

**Behavior**:
- Changing selection triggers new diff API call
- Updates DiffViewer and DriftAlertBanner content

---

### 3. DriftAlertBanner

**File**: `components/entity/sync-status/drift-alert-banner.tsx`

**Purpose**: Display drift status with contextual action buttons.

**Props**:
```typescript
interface DriftAlertBannerProps {
  driftStatus: 'none' | 'modified' | 'outdated' | 'conflict';
  comparisonScope: ComparisonScope;
  summary: {
    added: number;
    modified: number;
    deleted: number;
    unchanged: number;
  };
  onViewDiffs: () => void;
  onMerge: () => void;
  onTakeUpstream: () => void;
  onKeepLocal: () => void;
}
```

**Visual Elements**:
- Alert banner (yellow/orange for drift, green for synced)
- Warning icon + "Drift Detected" text
- Action buttons: View Diffs, Merge..., Take Upstream, Keep Local
- Summary stats (X files added, Y modified, Z deleted)

**Status Mapping**:
| Drift Status | Banner Color | Primary Action |
|--------------|--------------|----------------|
| none         | Green        | "All Synced" (no actions) |
| modified     | Yellow       | Keep Local / Take Upstream |
| outdated     | Orange       | Pull Updates |
| conflict     | Red          | Merge... |

---

### 4. FilePreviewPane

**File**: `components/entity/sync-status/file-preview-pane.tsx`

**Purpose**: Render preview of selected file (Markdown rendered, code syntax-highlighted).

**Props**:
```typescript
interface FilePreviewPaneProps {
  filePath: string | null;
  content: string | null;
  tier: 'source' | 'collection' | 'project';
  isLoading: boolean;
}
```

**Visual Elements**:
- Header: "File Preview: {filename}"
- Rendered content area with ScrollArea
- Support for:
  - Markdown: Fully rendered with `@tailwindcss/typography`
  - Code: Syntax highlighted (Python, TypeScript, JSON, YAML)
  - Other: Plain text with monospace font

**Implementation Notes**:
- Use `react-markdown` with `remark-gfm` for Markdown
- Use `prism-react-renderer` or similar for code highlighting
- Show tier indicator (which version being previewed)

---

### 5. SyncActionsFooter

**File**: `components/entity/sync-status/sync-actions-footer.tsx`

**Purpose**: Global sync action buttons and apply/cancel controls.

**Props**:
```typescript
interface SyncActionsFooterProps {
  onPullCollectionUpdates: () => void;
  onPushLocalChanges: () => void;
  onMergeConflicts: () => void;
  onResolveAll: () => void;
  onCancel: () => void;
  onApply: () => void;
  hasPendingActions: boolean;
  hasConflicts: boolean;
  isApplying: boolean;
}
```

**Visual Elements**:
- Left side: Action buttons row
  - "Pull Collection Updates"
  - "Push Local Changes" - **Coming Soon**
  - "Merge Conflicts" (visible only when conflicts exist)
  - "Resolve All"
- Right side:
  - "Cancel" (secondary)
  - "Apply Sync Actions" (primary blue)

**Button States**:
- Disabled when no pending actions
- Loading state during apply
- Coming Soon tooltip for unimplemented features

---

### 6. SyncStatusTab (Composite)

**File**: `components/entity/sync-status/sync-status-tab.tsx`

**Purpose**: Orchestrate all sub-components into the complete 3-panel layout.

**Props**:
```typescript
interface SyncStatusTabProps {
  entity: Entity;
  mode: 'collection' | 'project';
  projectPath?: string;
  onClose: () => void;
}
```

**State Management**:
```typescript
// Comparison state
const [comparisonScope, setComparisonScope] = useState<ComparisonScope>('collection-vs-project');
const [selectedFile, setSelectedFile] = useState<string | null>(null);

// Query hooks
const { data: upstreamDiff } = useUpstreamDiff(entity.id);
const { data: projectDiff } = useProjectDiff(entity.id, projectPath);
const { data: fileContent } = useFileContent(entity.id, selectedFile, tier);

// Mutations
const pullFromSource = useSync({ direction: 'upstream' });
const deployToProject = useDeploy();
const pushToCollection = useSync({ direction: 'reverse' }); // Coming Soon
```

**Layout**:
```tsx
<div className="flex flex-col h-full">
  {/* Top Banner */}
  <ArtifactFlowBanner {...flowProps} />

  {/* 3-Panel Main Content */}
  <div className="flex flex-1 overflow-hidden">
    {/* Left: File Tree (fixed 240px) */}
    <div className="w-60 border-r">
      <FileTree files={files} selected={selectedFile} onSelect={setSelectedFile} />
    </div>

    {/* Middle: Comparison + Diff (flex-1) */}
    <div className="flex-1 flex flex-col overflow-hidden">
      <ComparisonSelector value={comparisonScope} onChange={setComparisonScope} />
      <DriftAlertBanner status={driftStatus} />
      <DiffViewer diff={currentDiff} selectedFile={selectedFile} />
    </div>

    {/* Right: Preview (fixed 320px) */}
    <div className="w-80 border-l">
      <FilePreviewPane filePath={selectedFile} content={previewContent} />
    </div>
  </div>

  {/* Footer */}
  <SyncActionsFooter {...footerProps} />
</div>
```

---

## API Integration

### Existing Endpoints (Wired)

| Action | Endpoint | Hook |
|--------|----------|------|
| Get upstream diff | `GET /artifacts/{id}/upstream-diff` | `useQuery` |
| Get project diff | `GET /artifacts/{id}/diff?project_path=` | `useQuery` |
| Pull from source | `POST /artifacts/{id}/sync` | `useSync` |
| Deploy to project | `POST /artifacts/{id}/deploy` | `useDeploy` |
| Get file content | `GET /artifacts/{id}/files/{path}` | `useQuery` |

### Coming Soon Features

| Action | Status | Tooltip |
|--------|--------|---------|
| Push to Collection | Backend not implemented | "Coming Soon: Push local changes to collection" |
| Push Local Changes | Backend not implemented | "Coming Soon" |
| Merge Conflicts (advanced) | Partial support | Uses existing `MergeWorkflow` component |

---

## Implementation Steps

### Phase 1: Create Sub-Components (Parallel)

1. **ArtifactFlowBanner** (~150 lines)
   - SVG path for curved connectors
   - Node rendering with icons and badges
   - Button placement on connectors

2. **ComparisonSelector** (~80 lines)
   - Select dropdown with shadcn
   - Quick-switch button group

3. **DriftAlertBanner** (~100 lines)
   - Alert variants based on status
   - Action button row

4. **FilePreviewPane** (~120 lines)
   - Markdown rendering
   - Code syntax highlighting
   - Loading skeleton

5. **SyncActionsFooter** (~80 lines)
   - Button layout
   - Loading states
   - Coming Soon tooltips

### Phase 2: Composite Component

6. **SyncStatusTab** (~300 lines)
   - Layout orchestration
   - State management
   - Query/mutation hooks
   - Event handlers

### Phase 3: Integration

7. **Refactor unified-entity-modal.tsx**
   - Replace existing Sync Status tab content
   - Import new `SyncStatusTab` component
   - Preserve tab structure

### Phase 4: Polish

8. **Wire all actions**
   - Connect to existing hooks
   - Add error handling
   - Toast notifications

9. **Add Coming Soon states**
   - Tooltip component for disabled buttons
   - Consistent messaging

---

## File Changes Summary

### New Files
- `components/entity/sync-status/index.ts`
- `components/entity/sync-status/types.ts`
- `components/entity/sync-status/artifact-flow-banner.tsx`
- `components/entity/sync-status/comparison-selector.tsx`
- `components/entity/sync-status/drift-alert-banner.tsx`
- `components/entity/sync-status/file-preview-pane.tsx`
- `components/entity/sync-status/sync-actions-footer.tsx`
- `components/entity/sync-status/sync-status-tab.tsx`

### Modified Files
- `components/entity/unified-entity-modal.tsx` (refactor Sync Status tab)

### Reused Components
- `components/entity/file-tree.tsx` (existing)
- `components/entity/diff-viewer.tsx` (existing)
- `components/entity/merge-workflow.tsx` (existing)

---

## Success Criteria

1. Visual match to design render
2. All buttons wired to real API calls (or Coming Soon tooltip)
3. Comparison selector switches diff views correctly
4. File tree selection updates diff and preview panes
5. Flow banner shows accurate version/SHA data
6. Drift detection displays correct status and actions
7. No hardcoded or mock data
8. Responsive layout within modal constraints
9. Keyboard navigation support
10. Loading and error states handled
