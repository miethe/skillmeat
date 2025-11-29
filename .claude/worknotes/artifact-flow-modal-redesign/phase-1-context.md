# Artifact Flow Modal Redesign - Phase 1 Context

**Document Purpose**: Capture architectural decisions, API integration patterns, and implementation constraints for the artifact-flow-modal-redesign PRD.

**Reference Documents**:
- PRD: `docs/designs/artifact-flow-modal-redesign.md`
- Implementation Plan: `docs/designs/artifact-flow-modal-implementation-plan.md`
- Visual Reference: `docs/designs/renders/artifact-flow-modal.png`

---

## 1. Component Architecture

### 1.1 Layout Structure

The redesigned Sync Status tab uses a **3-panel responsive layout** within modal constraints:

| Panel | Width | Content | Scrollable |
|-------|-------|---------|-----------|
| Left (FileTree) | 240px fixed | Artifact file hierarchy with status indicators | Yes (overflow-y) |
| Middle (Main) | Flex-1 | Comparison controls, diff viewer, drift alerts | Yes (entire section) |
| Right (Preview) | 320px fixed | Rendered file preview | Yes (overflow-y) |

**Key Decision**: Fixed sidebars (240px + 320px) with flex-1 middle ensures predictable layout. Modal max-width constraints (max-w-6xl) prevent excessive width.

**Implementation Reference**:
```tsx
<div className="flex flex-1 overflow-hidden">
  {/* Left: File Tree (fixed 240px) */}
  <div className="w-60 border-r overflow-y-auto">
    <FileTree {...props} />
  </div>

  {/* Middle: Comparison + Diff (flex-1) */}
  <div className="flex-1 flex flex-col overflow-hidden">
    <ComparisonSelector {...props} />
    <DriftAlertBanner {...props} />
    <DiffViewer {...props} />
  </div>

  {/* Right: Preview (fixed 320px) */}
  <div className="w-80 border-l overflow-y-auto">
    <FilePreviewPane {...props} />
  </div>
</div>
```

### 1.2 Component Structure

Create a new **sync-status subdirectory** instead of single file for better code organization:

```
components/entity/sync-status/
├── index.ts                      # Public exports (re-exports all components)
├── types.ts                      # Shared TypeScript interfaces
├── sync-status-tab.tsx           # Main composite component (orchestrator)
├── artifact-flow-banner.tsx      # 3-tier flow visualization
├── comparison-selector.tsx       # Comparison scope controls
├── drift-alert-banner.tsx        # Status alerts with actions
├── file-preview-pane.tsx         # File content renderer
└── sync-actions-footer.tsx       # Footer action buttons
```

**Why subdirectory**:
- Keeps related UI logic grouped
- Easier to locate during refactoring
- Follows established pattern (e.g., `collection/`, `marketplace/`)
- Allows incremental component loading

### 1.3 Presentational Components Pattern

All sync-status components use **props-driven presentational pattern** (minimal internal state):

```typescript
// Good: Presentational (props-driven)
interface ArtifactFlowBannerProps {
  entity: Entity;
  sourceInfo: SourceInfo | null;
  collectionInfo: CollectionInfo;
  projectInfo: ProjectInfo | null;
  onPullFromSource: () => void;
  onDeployToProject: () => void;
  isPulling: boolean;
  isDeploying: boolean;
}

export function ArtifactFlowBanner(props: ArtifactFlowBannerProps) {
  // Pure presentation, no data fetching, minimal state
  return <div>{/* render based on props */}</div>;
}

// Bad: Monolithic (data fetching inside)
// Don't do this - orchestration happens in parent
```

**Rationale**: Parent component (SyncStatusTab) owns data fetching and state management. Child components are stateless and reusable.

### 1.4 Reusing Existing Components

**FileTree Component** (`components/entity/file-tree.tsx`):
- Already used in Contents tab
- Props: `files`, `selectedPath`, `onSelect`, `isLoading`
- Status indicators: Uses extension-based icons
- No modification needed - direct reuse

**DiffViewer Component** (`components/entity/diff-viewer.tsx`):
- Already used in Sync Status tab (upstream section)
- Props: `files`, `leftLabel`, `rightLabel`
- Renders unified diff with side-by-side highlighting
- No modification needed - direct reuse

**Existing Merge Workflow** (`components/entity/merge-workflow.tsx`):
- Used for conflict resolution (triggered from footer actions)
- Keep separate - advanced feature for full-modal dialogs
- Link from drift alert banner when conflicts detected

---

## 2. API Integration Strategy

### 2.1 Wired Endpoints (Already Implemented)

| Action | Endpoint | Hook | Response Type | Usage |
|--------|----------|------|---------------|-------|
| Get upstream diff | `GET /artifacts/{id}/upstream-diff` | `useQuery` | `ArtifactUpstreamDiffResponse` | ArtifactFlowBanner, DriftAlertBanner |
| Get project diff | `GET /artifacts/{id}/diff?project_path=` | `useQuery` | `ArtifactDiffResponse` | DiffViewer, DriftAlertBanner |
| Pull from source | `POST /artifacts/{id}/sync` | Hook (useSync or direct) | Synced artifact | ArtifactFlowBanner button |
| Deploy to project | `POST /artifacts/{id}/deploy` | Hook (useDeploy) | Deployed artifact | ArtifactFlowBanner button |
| Get file content | `GET /artifacts/{id}/files/{path}` | `useQuery` | `FileContentResponse` | FilePreviewPane |

**Query Example** (from `unified-entity-modal.tsx`):
```typescript
const { data: upstreamDiff, isLoading: upstreamLoading, error: upstreamError } =
  useQuery<ArtifactUpstreamDiffResponse>({
    queryKey: ['upstream-diff', entity?.id, entity?.collection],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (entity.collection) params.set('collection', entity.collection);
      return await apiRequest<ArtifactUpstreamDiffResponse>(
        `/artifacts/${entity.id}/upstream-diff?${params.toString()}`
      );
    },
    enabled: activeTab === 'sync' && !!entity?.id,
    staleTime: 60 * 1000, // Cache 1 minute (upstream less volatile)
    gcTime: 5 * 60 * 1000, // Keep 5 minutes
    retry: 2,
  });
```

### 2.2 Coming Soon Features (Backend Not Implemented)

| Feature | Endpoint Status | UI Handling | Tooltip |
|---------|-----------------|-------------|---------|
| Push to Collection | Not implemented | Disabled button with tooltip | "Coming Soon: Push local changes to collection" |
| Push Local Changes | Not implemented | Disabled button in footer | "Coming Soon: Sync local changes upstream" |
| Advanced merge strategies | Partial support | Uses existing MergeWorkflow for basic cases | "Full merge strategies coming soon" |

**Disabled Button Pattern**:
```tsx
<Button
  disabled={true}
  title="Coming Soon: Push local changes to collection"
  className="opacity-50"
>
  Push to Collection
</Button>
```

Or with Tooltip component:
```tsx
<Tooltip content="Coming Soon: Push local changes to collection">
  <Button disabled={true}>Push to Collection</Button>
</Tooltip>
```

### 2.3 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────┐
│              SyncStatusTab (Orchestrator)                │
│  ┌──────────────────────────────────────────────────┐   │
│  │ State: comparisonScope, selectedFile             │   │
│  │ Queries:                                         │   │
│  │  - upstreamDiff (upstream vs collection)         │   │
│  │  - projectDiff (collection vs project)           │   │
│  │  - fileContent (preview content)                 │   │
│  └──────────────────────────────────────────────────┘   │
│                           |                              │
│    ┌──────────────────────┼──────────────────────┐      │
│    ↓                      ↓                       ↓      │
│ ┌──────────┐      ┌──────────────┐     ┌──────────┐    │
│ │  Banner  │      │  DiffViewer  │     │ Preview  │    │
│ │ (status) │      │ (comparison) │     │ (render) │    │
│ └──────────┘      └──────────────┘     └──────────┘    │
└─────────────────────────────────────────────────────────┘

Entity Data Flow:
  entity.version → upstream_version → compare → show diff
  entity.version → project.version → compare → show diff
  selected file path → fetch content → render preview
```

### 2.4 Error Handling Pattern

Use toast notifications for all user-facing errors:

```typescript
// In SyncStatusTab or child component
const { toast } = useToast();

// When diff fetch fails
useEffect(() => {
  if (diffError && shouldFetchDiff) {
    toast({
      title: 'Diff Load Failed',
      description: diffError instanceof Error ? diffError.message : 'Unknown error',
      variant: 'destructive',
    });
  }
}, [diffError, shouldFetchDiff, toast]);

// When API action fails
const handlePullFromSource = async () => {
  try {
    await syncEntity(entity.id, { direction: 'upstream' });
    toast({ title: 'Sync Successful' });
  } catch (error) {
    toast({
      title: 'Sync Failed',
      description: error.message,
      variant: 'destructive',
    });
  }
};
```

---

## 3. State Management Approach

### 3.1 SyncStatusTab State

Owner component manages minimal required state:

```typescript
export function SyncStatusTab({ entity, mode, projectPath, onClose }: SyncStatusTabProps) {
  // Comparison scope state
  const [comparisonScope, setComparisonScope] = useState<ComparisonScope>(
    'collection-vs-project'
  );

  // Selected file state (shared between FileTree, DiffViewer, FilePreviewPane)
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  // Query hooks (data fetching)
  const { data: upstreamDiff, isLoading: upstreamLoading } =
    useQuery({ /* upstream diff */ });

  const { data: projectDiff, isLoading: projectLoading } =
    useQuery({ /* project diff */ });

  const { data: fileContent, isLoading: contentLoading } =
    useQuery({ /* file content */ });

  // Mutations (actions)
  const pullFromSource = useSync({ direction: 'upstream' });
  const deployToProject = useDeploy();
  // pushToCollection = useSync({ direction: 'reverse' }); // Coming Soon
}
```

**No Redux/Context needed** for this feature:
- Data fetching centralized in parent
- Props drilled to presentational children
- Simple state (2 booleans, 1 string enum, 1 string)

### 3.2 React Query Strategy

**Cache Settings**:

| Query | staleTime | gcTime | refetch Trigger |
|-------|-----------|--------|-----------------|
| upstream-diff | 60s | 5min | Tab active + entity ID change |
| project-diff | 5min | 30min | Tab active + comparison change |
| file-content | 5min | 30min | File selection change |

**Invalidation on Actions**:
```typescript
const queryClient = useQueryClient();

const handlePullFromSource = async () => {
  await pullFromSource.mutateAsync(entity.id);

  // Invalidate stale data after action
  queryClient.invalidateQueries({ queryKey: ['upstream-diff', entity.id] });
  queryClient.invalidateQueries({ queryKey: ['artifact-diff', entity.id] });
};
```

### 3.3 When to Use useState vs React Query

| Scenario | Tool | Example |
|----------|------|---------|
| UI-only state (UI toggle, mode) | useState | `comparisonScope`, `selectedFile`, form inputs |
| Server state (entity data, diffs, content) | React Query | `upstreamDiff`, `projectDiff`, `fileContent` |
| Side effects from user action | useQuery + mutation | Deploy/sync operations |
| Local derived state | useMemo | Calculated diff summary, file stats |

---

## 4. Design System Decisions

### 4.1 shadcn/ui Components Used

- **Dialog**: Modal container (used by UnifiedEntityModal parent)
- **Tabs**: Tab navigation (used by UnifiedEntityModal parent)
- **Button**: All action buttons
- **Select**: Comparison scope dropdown
- **Badge**: Status indicators (synced, modified, outdated, conflict)
- **Alert**: Drift alert banner
- **ScrollArea**: Scrollable file tree and preview panes
- **Skeleton**: Loading states

**No custom CSS** - only Tailwind utilities.

### 4.2 Status Color Mapping

Consistent with existing design system:

| Status | Color Class | Icon | Usage |
|--------|-------------|------|-------|
| Synced | `text-green-500`, `bg-green-500/10` | CheckCircle2 | ✓ All in sync |
| Modified | `text-yellow-500`, `bg-yellow-500/10` | AlertCircle | ⚠ Local changes |
| Outdated | `text-blue-500`, `bg-blue-500/10` | Clock | ⏱ Update available |
| Conflict | `text-red-500`, `bg-red-500/10` | AlertCircle | ✗ Merge needed |

Example badge:
```tsx
<Badge variant="secondary" className="gap-1">
  <Clock className="h-3 w-3" />
  Update Available
</Badge>
```

### 4.3 SVG Curved Flow Connectors

Flow banner uses SVG paths for curved arrows between tiers:

```tsx
// In ArtifactFlowBanner
<svg width="100%" height="60" className="absolute inset-0">
  {/* Source → Collection curved arrow */}
  <path
    d={`M ${source.x + 150} ${source.y + 30} Q ${(source.x + collection.x) / 2} 10 ${collection.x} ${collection.y + 30}`}
    stroke="currentColor"
    strokeWidth="2"
    fill="none"
    markerEnd="url(#arrowhead)"
  />

  {/* Collection → Project curved arrow */}
  <path
    d={`M ${collection.x + 150} ${collection.y + 30} Q ${(collection.x + project.x) / 2} 10 ${project.x} ${project.y + 30}`}
    stroke="currentColor"
    strokeWidth="2"
    fill="none"
    markerEnd="url(#arrowhead)"
  />

  {/* Project → Collection reverse arrow (dashed, greyed) */}
  <path
    d={`M ${project.x - 150} ${project.y + 30} Q ${(project.x + collection.x) / 2} 50 ${collection.x - 150} ${collection.y + 30}`}
    stroke="currentColor"
    strokeWidth="2"
    strokeDasharray="5,5"
    fill="none"
    opacity="0.5"
    markerEnd="url(#arrowhead-faded)"
  />

  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
      <polygon points="0 0, 10 3, 0 6" fill="currentColor" />
    </marker>
  </defs>
</svg>
```

**Positioning**: Buttons overlay paths using absolute positioning.

### 4.4 Dark Mode Support

All colors use Tailwind dark: variants:

```tsx
// Example from DriftAlertBanner
<div className="rounded-lg border border-yellow-500/20 bg-yellow-500/10 dark:border-yellow-600/30 dark:bg-yellow-600/10 p-4">
  <p className="text-yellow-700 dark:text-yellow-400">Drift Detected</p>
</div>
```

CSS variables inherited from `app/globals.css` handle dark mode toggle.

### 4.5 Keyboard Navigation

All components must support keyboard navigation:

- **FileTree**: Arrow keys expand/collapse, Enter selects file, Tab navigates
- **Comparison Selector**: Tab through dropdowns, Space/Enter to activate
- **Buttons**: Standard Tab focus, Enter/Space to activate
- **Focus Management**: Use `autoFocus` for primary action buttons

Reference: Radix UI primitives automatically provide a11y support.

---

## 5. Technical Constraints & Trade-offs

### 5.1 File Preview Implementation

**Markdown Rendering**:
- Library: `react-markdown` with `remark-gfm` (GitHub Flavored Markdown)
- Rendering: HTML with Tailwind prose classes
- Configuration:
  ```tsx
  import ReactMarkdown from 'react-markdown';
  import remarkGfm from 'remark-gfm';

  <ReactMarkdown
    remarkPlugins={[remarkGfm]}
    className="prose dark:prose-invert max-w-none"
  >
    {fileContent}
  </ReactMarkdown>
  ```

**Code Syntax Highlighting**:
- Library: `prism-react-renderer` (lightweight, no WASM)
- Supported languages: Python, TypeScript, JavaScript, JSON, YAML, Bash
- Fallback: Monospace plain text for unknown languages

**Other Formats**:
- Plain text: Monospace font in ScrollArea
- Binary files: Show "Binary file not shown" message

### 5.2 Flow Banner Constraints

**Responsive Handling** (within modal):
- Minimum modal width: 600px (min-w-[600px])
- Flow banner scales horizontally with modal
- Node positioning: Calculated as `(x / totalWidth) * 100%`
- Button positioning: Overlaid with absolute positioning

**No Full-Page Responsive Design**:
- Modal locks to fixed height (90vh max)
- Sidebars stay fixed width (240px + 320px)
- Not designed for mobile (intended for desktop only)

### 5.3 Lazy Loading Strategy

**FilePreviewPane**: Only fetch content when file selected:
```typescript
const { data: fileContent } = useQuery({
  queryKey: ['artifact-file-content', entity.id, selectedFile],
  queryFn: async () => { /* ... */ },
  enabled: !!selectedFile,  // Only fetch if file selected
  staleTime: 5 * 60 * 1000,
});
```

**DiffViewer**: Memoized to prevent re-renders on unrelated state changes:
```tsx
const MemoizedDiffViewer = useMemo(
  () => <DiffViewer files={diffData.files} selectedFile={selectedFile} />,
  [diffData, selectedFile]
);
```

### 5.4 Memoization for Expensive Calculations

```typescript
// In SyncStatusTab
const driftStatus = useMemo(() => {
  if (!projectDiff) return 'none';
  if (projectDiff.has_conflicts) return 'conflict';
  if (projectDiff.has_changes) return 'modified';
  return 'synced';
}, [projectDiff]);

const diffSummary = useMemo(() => {
  if (!projectDiff) return { added: 0, modified: 0, deleted: 0, unchanged: 0 };
  return {
    added: projectDiff.files.filter(f => f.status === 'added').length,
    modified: projectDiff.files.filter(f => f.status === 'modified').length,
    deleted: projectDiff.files.filter(f => f.status === 'deleted').length,
    unchanged: projectDiff.files.filter(f => f.status === 'unchanged').length,
  };
}, [projectDiff]);
```

---

## 6. Performance Considerations

### 6.1 Query Caching Strategy

```typescript
// From unified-entity-modal.tsx pattern
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,   // 5 minutes
      gcTime: 30 * 60 * 1000,     // 30 minutes (garbage collect)
      refetchOnWindowFocus: false,
      retry: 2,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
  },
});
```

**Specific Overrides for Sync Tab**:
- `upstream-diff`: `staleTime: 60s` (upstream changes less frequently, refresh manually)
- `artifact-diff`: `staleTime: 5min` (comparison less volatile)
- `file-content`: `staleTime: 5min` (content rarely changes)

### 6.2 Render Optimization

**Component Splitting**:
- Each sub-component (Banner, Selector, DriftAlert, DiffViewer, Footer) renders independently
- Avoid passing entire `entity` object to sub-components - only pass required fields
- Use React.memo for presentational components if needed:
  ```tsx
  export const ArtifactFlowBanner = React.memo(function ArtifactFlowBanner(props) {
    // Component body
  });
  ```

**Key Stability**:
- File list rendered with stable keys (file path)
- Diff lines use index-based keys (acceptable for unified diffs)

### 6.3 Modal Performance

- Modal max-width: `max-w-6xl` (1152px) to prevent excessive rendering
- ScrollArea components prevent rendering off-screen content
- Tab content lazily evaluated (only active tab content mounts)

---

## 7. Coming Soon Features & Placeholders

### 7.1 Feature Flags / Disabled States

```typescript
// Push to Collection button (Phase 2)
<Button
  disabled={true}
  title="Coming Soon: Push local changes to collection"
  className="opacity-50 cursor-not-allowed"
>
  <ArrowUp className="mr-2 h-4 w-4" />
  Push to Collection
</Button>

// Or with explicit Coming Soon badge
<div className="flex items-center gap-2">
  <Button disabled={true}>Push Local Changes</Button>
  <Badge variant="outline" className="text-xs">Coming Soon</Badge>
</div>
```

### 7.2 Placeholder Implementation

For unimplemented backend features, use explicit "Coming Soon" approach:

```typescript
const handlePushToCollection = () => {
  toast({
    title: 'Feature Coming Soon',
    description: 'Push to collection will be available in Phase 2',
    variant: 'default',
  });
};
```

### 7.3 Documented Phase 2 Features

- Push to Collection (backend endpoint not implemented)
- Advanced merge strategies (only basic merge workflow available)
- Partial syncs (sync individual files instead of artifact-wide)

---

## 8. Integration Points with Existing Code

### 8.1 UnifiedEntityModal Integration

**Location**: `components/entity/unified-entity-modal.tsx`

**Current Structure**:
```tsx
<Tabs value={activeTab} onValueChange={handleTabChange}>
  <TabsTrigger value="overview">Overview</TabsTrigger>
  <TabsTrigger value="contents">Contents</TabsTrigger>
  <TabsTrigger value="sync">Sync Status</TabsTrigger>
  <TabsTrigger value="history">History</TabsTrigger>

  <TabsContent value="sync">
    {/* Current inline Sync Status implementation */}
    {/* REPLACE with <SyncStatusTab /> */}
  </TabsContent>
</Tabs>
```

**Change Required**:
```tsx
// Import new component
import { SyncStatusTab } from '@/components/entity/sync-status';

// In TabsContent
<TabsContent value="sync" className="mt-0 flex-1">
  <SyncStatusTab
    entity={entity}
    mode={entity.collection ? 'collection' : 'project'}
    projectPath={entity.projectPath}
    onClose={onClose}
  />
</TabsContent>
```

**Preserved Tabs**:
- Overview: No changes
- Contents: No changes
- History: No changes

### 8.2 EntityDetailPanel Future Integration

**Location**: `components/entity/entity-detail-panel.tsx`

**Future Work** (Phase 2):
- Apply same 3-panel layout pattern
- Reuse same sync-status components
- Currently not in scope - only UnifiedEntityModal updated in Phase 1

### 8.3 Existing Merge Workflow Integration

**Component**: `components/entity/merge-workflow.tsx`

**Usage**: When conflict status detected in DriftAlertBanner:
```tsx
// From DriftAlertBanner when status === 'conflict'
<Button onClick={onMerge} variant="default">
  <GitMerge className="mr-2 h-4 w-4" />
  Resolve Conflicts
</Button>

// In SyncStatusTab parent
const [showMergeWorkflow, setShowMergeWorkflow] = useState(false);

<Dialog open={showMergeWorkflow} onOpenChange={setShowMergeWorkflow}>
  <DialogContent className="max-h-[90vh] max-w-4xl">
    <MergeWorkflow
      entityId={entity.id}
      projectPath={entity.projectPath}
      direction="upstream"
      onComplete={() => {
        setShowMergeWorkflow(false);
        // Invalidate diffs
      }}
    />
  </DialogContent>
</Dialog>
```

**Key**: Don't modify existing MergeWorkflow - compose through parent component.

---

## 9. Success Criteria for Phase 1

### Visible
1. Visual match to design render (3-panel layout, flow banner with curved arrows)
2. File tree filters files by status (synced vs modified)
3. Comparison selector works (changes diff view)
4. Flow banner shows accurate version/SHA data
5. File preview renders Markdown and code correctly

### Functional
6. All buttons wired to real API calls (except "Coming Soon" features)
7. Error toast notifications on API failures
8. Loading states during data fetch
9. Keyboard navigation support (Tab through interactive elements)
10. File selection updates diff and preview panes simultaneously

### Technical
11. No hardcoded or mock data (all from API)
12. React Query caching working (stale times respected)
13. Responsive within modal constraints (not full-page)
14. Dark mode support (all colors using dark: variants)
15. TypeScript types fully defined (no `any`)

---

## 10. Implementation Checklist

### Files to Create
- [ ] `components/entity/sync-status/index.ts` - Public exports
- [ ] `components/entity/sync-status/types.ts` - Shared TypeScript interfaces
- [ ] `components/entity/sync-status/artifact-flow-banner.tsx` - Flow visualization
- [ ] `components/entity/sync-status/comparison-selector.tsx` - Comparison dropdown
- [ ] `components/entity/sync-status/drift-alert-banner.tsx` - Status alerts
- [ ] `components/entity/sync-status/file-preview-pane.tsx` - File renderer
- [ ] `components/entity/sync-status/sync-actions-footer.tsx` - Action buttons
- [ ] `components/entity/sync-status/sync-status-tab.tsx` - Composite component

### Files to Modify
- [ ] `components/entity/unified-entity-modal.tsx` - Replace sync tab content

### Files to Verify (No Changes)
- [ ] `components/entity/file-tree.tsx` - Direct reuse
- [ ] `components/entity/diff-viewer.tsx` - Direct reuse
- [ ] `components/entity/merge-workflow.tsx` - Integration only

### Testing Approach
- Unit tests for individual components (props → output)
- Integration test for SyncStatusTab (data flow)
- E2E test for user workflows (select file → view diff → preview)

---

## 11. Reference Links

**Existing Patterns**:
- File tree pattern: `components/entity/file-tree.tsx` (lines 1-200)
- Diff viewer pattern: `components/entity/diff-viewer.tsx` (lines 1-200)
- Query hook pattern: `hooks/useEntityLifecycle.tsx`
- Modal pattern: `components/entity/unified-entity-modal.tsx` (lines 1120-1600)

**Design System**:
- shadcn/ui docs: https://ui.shadcn.com
- Tailwind utilities: https://tailwindcss.com/docs
- Radix UI primitives: https://www.radix-ui.com

**Project Documentation**:
- CLAUDE.md: `.claude/CLAUDE.md` (root)
- Web CLAUDE.md: `skillmeat/web/CLAUDE.md`
