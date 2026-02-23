# UI Component Specifications: /manage and /collection Page Refactor

## Overview

This document provides detailed component specifications for the SkillMeat page refactor, separating the `/collection` page (discovery-focused) from the `/manage` page (operations-focused).

**Design System**: Next.js 15 + shadcn/ui + Radix UI + Tailwind CSS
**Type System**: Unified `Artifact` type from `@/types/artifact`

---

## 1. Page-Specific Cards

### 1.1 ArtifactBrowseCard (Collection Page)

**Purpose**: Discovery and understanding - helps users explore and learn about artifacts before adding them to their workflow.

**File Location**: `/skillmeat/web/components/collection/artifact-browse-card.tsx`

#### Props Interface

```typescript
interface ArtifactBrowseCardProps {
  /** The artifact to display */
  artifact: Artifact;

  /** Click handler for opening detail modal */
  onClick: () => void;

  /** Handler for quick deploy action */
  onQuickDeploy?: () => void;

  /** Handler for adding artifact to a group */
  onAddToGroup?: () => void;

  /** Handler for viewing artifact details */
  onViewDetails?: () => void;

  /** Whether to show collection badge (All Collections view) */
  showCollectionBadge?: boolean;

  /** Handler when collection badge is clicked */
  onCollectionClick?: (collectionId: string) => void;

  /** Additional CSS classes */
  className?: string;
}
```

#### Visual Layout

```
+------------------------------------------------------------------+
| [Type Icon]  Artifact Name                    [Quick Actions...] |
|              author/source                                        |
+------------------------------------------------------------------+
|                                                                   |
| Description text that can span multiple lines with proper         |
| truncation after 2-3 lines using line-clamp...                   |
|                                                                   |
+------------------------------------------------------------------+
| [tag1] [tag2] [tag3] [+N more]                                   |
+------------------------------------------------------------------+
| [Tool: Bash] [Tool: Read] [Tool: Write]           [Score Badge]  |
+------------------------------------------------------------------+
```

#### Component States

| State | Visual Treatment |
|-------|-----------------|
| Default | Standard card with subtle hover state |
| Hover | `hover:border-primary/50 hover:shadow-md` elevation |
| Focus | `focus:ring-2 focus:ring-ring focus:outline-none` |
| Loading | Skeleton with matching dimensions |

#### Interaction Patterns

1. **Card Click**: Opens `ArtifactDetailsModal` (discovery modal)
2. **Quick Actions Menu** (three-dot menu):
   - View Details
   - Quick Deploy (opens deploy dialog)
   - Add to Group (opens group picker)
   - Copy CLI Command
3. **Collection Badge Click**: Navigates to that collection

#### Accessibility

- `role="button"` with `tabIndex={0}`
- `aria-label` describing the artifact
- Keyboard navigation: Enter/Space to activate
- Icon buttons have `aria-label` attributes

#### Implementation Notes

- Uses `cn()` for conditional class merging
- Type-specific border accent from `artifactTypeBorderAccents`
- Show "Deployed (N)" badge when artifact has deployments; no sync/drift indicators (those belong on /manage)
- Tool badges extracted from artifact metadata (Tools API PRD required)

---

### 1.2 ArtifactOperationsCard (Manage Page)

**Purpose**: Status and actions at-a-glance - enables quick operational decisions and actions.

**File Location**: `/skillmeat/web/components/manage/artifact-operations-card.tsx`

#### Props Interface

```typescript
interface ArtifactOperationsCardProps {
  /** The artifact to display */
  artifact: Artifact;

  /** Click handler for opening operations modal */
  onClick: () => void;

  /** Handler for sync action */
  onSync?: () => void;

  /** Handler for deploy action */
  onDeploy?: () => void;

  /** Handler for viewing diff */
  onViewDiff?: () => void;

  /** Handler for manage action */
  onManage?: () => void;

  /** Whether card is selected (for bulk operations) */
  selected?: boolean;

  /** Selection change handler */
  onSelect?: (selected: boolean) => void;

  /** Whether selection is enabled */
  selectable?: boolean;

  /** Additional CSS classes */
  className?: string;
}

/** Health status derived from artifact state */
type HealthStatus = 'healthy' | 'needs-update' | 'has-drift' | 'error';
```

#### Visual Layout

```
+------------------------------------------------------------------+
| [Checkbox?] [Type Icon]  Artifact Name       [Status Badge]      |
|                          v1.2.0 -> v1.3.0    [Health Indicator]  |
+------------------------------------------------------------------+
| Deployed to: [Project A] [Project B] [+2]                        |
+------------------------------------------------------------------+
| [Drift Badge]  [Update Available]  [Last Synced: 2h ago]         |
+------------------------------------------------------------------+
| [Sync] [Deploy] [View Diff] [Manage...]                          |
+------------------------------------------------------------------+
```

#### Health Indicators

```typescript
const healthIndicators: Record<HealthStatus, { icon: LucideIcon; color: string; label: string }> = {
  'healthy': { icon: CheckCircle2, color: 'text-green-500', label: 'Synced' },
  'needs-update': { icon: ArrowUp, color: 'text-orange-500', label: 'Update Available' },
  'has-drift': { icon: GitBranch, color: 'text-yellow-500', label: 'Has Drift' },
  'error': { icon: AlertCircle, color: 'text-red-500', label: 'Error' },
};
```

#### Component States

| State | Visual Treatment |
|-------|-----------------|
| Default | Standard card |
| Selected | `ring-2 ring-primary` selection ring |
| Hover | `hover:border-primary/50 hover:shadow-md` |
| Needs Attention | Amber/orange border accent |
| Error | Red border accent with error badge |
| Syncing | Loading spinner on sync button |

#### Status Badges

```typescript
interface StatusBadgeConfig {
  syncStatus: SyncStatus;
  variant: 'default' | 'secondary' | 'outline' | 'destructive';
  className: string;
}

const statusBadgeConfig: Record<SyncStatus, StatusBadgeConfig> = {
  synced: { variant: 'default', className: 'bg-green-500/10 text-green-600' },
  modified: { variant: 'secondary', className: 'bg-yellow-500/10 text-yellow-600' },
  outdated: { variant: 'outline', className: 'border-orange-500 text-orange-600' },
  conflict: { variant: 'destructive', className: '' },
  error: { variant: 'destructive', className: '' },
};
```

#### Deployment Project Badges

```typescript
interface DeploymentBadge {
  projectName: string;
  projectPath: string;
  syncStatus: ArtifactSyncStatus;
  onClick: () => void;
}
```

Display rules:
- Show up to 2 project badges
- If more than 2, show `+N` overflow badge
- Clicking badge navigates to project management

#### Accessibility

- Checkbox has `aria-label` for selection
- Status indicators have `aria-live="polite"` for screen readers
- Action buttons have clear labels
- Focus management for keyboard navigation

---

## 2. Page-Specific Modals

### 2.1 ArtifactDetailsModal (Collection Page)

**Purpose**: Deep exploration of an artifact's purpose, usage, and metadata for discovery.

**File Location**: `/skillmeat/web/components/collection/artifact-details-modal.tsx`

#### Props Interface

```typescript
interface ArtifactDetailsModalProps {
  /** The artifact to display */
  artifact: Artifact | null;

  /** Whether the modal is open */
  open: boolean;

  /** Handler when modal should close */
  onClose: () => void;

  /** Handler to navigate to manage page for this artifact */
  onNavigateToManage?: (artifactId: string) => void;

  /** Handler for deploying artifact */
  onDeploy?: () => void;

  /** Handler for adding to group */
  onAddToGroup?: () => void;
}
```

#### Tab Structure

```typescript
type DetailsTab =
  | 'overview'    // Default tab
  | 'contents'
  | 'links'
  | 'collections'
  | 'sources'
  | 'history';    // General artifact timeline
```

**Tab policy**: v1 reuses existing UnifiedEntityModal data and tab content. Net-new tabs
(Documentation/Dependencies/Advanced) are future expansion and explicitly out of scope.

##### Overview Tab

Content sections:
1. **Header Area**
   - Artifact name and type icon
   - Author with link to source
   - License badge
   - Score/confidence indicator

2. **Description Section**
   - Full description (no truncation)
   - Purpose and use cases

3. **Tags Section**
   - All tags displayed as badges
   - Clickable to filter collection

4. **Tools Section (Future API)**
   - Claude Code tools this artifact uses
   - Tool icons with labels
   - **Depends on Tools API PRD** (see `/docs/project_plans/PRDs/tools-api-support-v1.md`)

5. **Upstream Status Summary**
   - Update available indicator (if tracking enabled)
   - Last upstream check timestamp
   - Keeps discovery view focused on upstream context

6. **Quick Actions**
   - Deploy to Project button
   - Add to Group button
   - "Manage Artifact →" cross-navigation button

##### Contents Tab

Content sections:
1. **File Tree**
   - Tree view of artifact contents (existing file tree)
2. **Content Pane**
   - Read-only viewer of selected file contents

##### Links Tab

Content sections:
1. **Linked Artifacts**
   - Linked artifacts list (existing linked artifacts section)
2. **Unlinked References**
   - Unlinked references list for follow-up

##### Collections Tab

Content sections:
1. **Collections & Groups**
   - Collection membership and group badges (existing ModalCollectionsTab)
2. **Collection Actions**
   - Add to Collection / Add to Group actions

##### Sources Tab

Content sections:
1. **Source Information**
   - Repository URL, source path, commit SHA (existing Source tab data)

##### History Tab (`history`)

Content sections:
1. **General Artifact History**
   - Deploy/sync/rollback events (existing history timeline)
   - Read-only view for discovery context
   - Note: Distinguished from `version-history` tab on operations modal

#### Visual Layout (Overview Tab)

```
+------------------------------------------------------------------+
| [X Close]                           [Manage Artifact ->]         |
+------------------------------------------------------------------+
| [Tab: Overview] [Tab: Contents] [Tab: Links] [Tab: Collections] ...
+------------------------------------------------------------------+
|                                                                   |
| [Type Icon]  ARTIFACT NAME                                        |
|              by author-name  |  MIT License  |  [Score: 0.95]    |
|                                                                   |
+------------------------------------------------------------------+
| DESCRIPTION                                                       |
| Full description text that can span multiple paragraphs...        |
|                                                                   |
+------------------------------------------------------------------+
| TAGS                                                              |
| [tag1] [tag2] [tag3] [tag4] [tag5]                               |
+------------------------------------------------------------------+
| TOOLS USED (Tools API)                                            |
| [Bash] [Read] [Write] [WebSearch]                                |
+------------------------------------------------------------------+
|                                                                   |
| [Deploy to Project]  [Add to Group]                              |
+------------------------------------------------------------------+
```

#### Accessibility

- Dialog has `aria-labelledby` pointing to title
- Tab navigation follows WAI-ARIA tab pattern
- Close button has `aria-label="Close dialog"`
- Focus trapped within modal
- ESC key closes modal

---

### 2.2 ArtifactOperationsModal (Manage Page)

**Purpose**: Operational management - sync, deploy, view changes, and manage artifact lifecycle.

**File Location**: `/skillmeat/web/components/manage/artifact-operations-modal.tsx`

#### Props Interface

```typescript
interface ArtifactOperationsModalProps {
  /** The artifact to display */
  artifact: Artifact | null;

  /** Whether the modal is open */
  open: boolean;

  /** Handler when modal should close */
  onClose: () => void;

  /** Handler to navigate to collection page for full details */
  onNavigateToCollection?: (collectionId: string, artifactId: string) => void;

  /** Handler when sync completes successfully */
  onSyncComplete?: () => void;

  /** Handler when deploy completes successfully */
  onDeployComplete?: () => void;
}
```

#### Tab Structure

```typescript
type OperationsTab =
  | 'overview'
  | 'contents'
  | 'status'         // Default tab
  | 'sync'
  | 'deployments'
  | 'version-history';  // Version timeline with rollback options
```

**Tab policy**: v1 reuses existing UnifiedEntityModal content. Net-new operational
views are composed from existing status, sync, history, and deployment data.

##### Overview Tab

Content sections:
1. **Metadata Summary**
   - Artifact name, type, author, version
2. **Operational Highlights**
   - Sync status badge
   - Update available indicator

##### Contents Tab

Content sections:
1. **File Tree**
   - Tree view of artifact contents
2. **Content Pane**
   - Read-only viewer of selected file contents

##### Status Tab

Content sections:
1. **Detailed Status Overview**
   - Large status indicator (synced/modified/outdated/conflict/error)
   - Current version vs available version
   - Last sync timestamp
2. **Upstream Information**
   - Source repository
   - Tracked branch/version
   - Last upstream check

**Default tab** for operations modal.

##### Sync Status Tab

Content sections:
1. **Sync Status Detail**
   - Drift status badge
   - Summary of changes (files added/modified/deleted)
   - Diff viewer entry point
2. **Quick Actions**
   - Sync from Upstream
   - Pull Latest (if outdated)
   - Resolve Conflicts (if conflict)

##### Deployments Tab

Content sections:
1. **Active Deployments**
   - List of projects where deployed
   - Each shows:
     - Project name and path
     - Deployment date
     - Local sync status
     - Actions: View in Project, Undeploy

2. **Deployment Actions**
   - "Deploy to New Project" button
   - Bulk undeploy (if multiple)

```typescript
interface DeploymentListItem {
  projectPath: string;
  projectName: string;
  deployedAt: string;
  syncStatus: ArtifactSyncStatus;
  localModifications: boolean;
  onViewInProject: () => void;
  onUndeploy: () => void;
}
```

##### Version History Tab (`version-history`)

Content sections:
1. **Version Timeline**
   - List of versions with dates
   - Changelog for each version
   - "Currently installed" indicator

2. **Actions per Version**
   - Roll back to version
   - View diff from current

```typescript
interface VersionHistoryEntry {
  version: string;
  date: string;
  changelog?: string;
  isCurrent: boolean;
  sha?: string;
}
```

Note: Diff viewing is accessed through Sync Status (existing diff viewer and file tree),
keeping the Operations modal focused on operational context without introducing new data.

#### Visual Layout (Status Tab)

```
+------------------------------------------------------------------+
| [X Close]                        [Collection Details ->]          |
+------------------------------------------------------------------+
| [Tab: Overview] [Tab: Contents] [Tab: Status] [Tab: Sync Status] |
| [Tab: Deployments] [Tab: Version History]                        |
+------------------------------------------------------------------+
|                                                                   |
| STATUS: [Modified]                                                |
|                                                                   |
| Current Version: v1.2.0                                           |
| Available Version: v1.3.0  [Update Available Badge]               |
| Last Synced: 2 hours ago                                          |
|                                                                   |
+------------------------------------------------------------------+
| DRIFT DETECTION                                                   |
| [Has Drift Badge]                                                 |
| 2 files modified, 1 file added                                    |
| [View Diff]                                                       |
+------------------------------------------------------------------+
| UPSTREAM                                                          |
| Source: anthropics/skills/canvas-design                           |
| Branch: main                                                       |
| Last Check: 5 minutes ago                                         |
+------------------------------------------------------------------+
|                                                                   |
| [Sync from Upstream]  [Pull Latest]  [View Changes]              |
+------------------------------------------------------------------+
```

#### Cross-Navigation

The modal header includes a "Collection Details" button that:
1. Closes the current modal
2. Navigates to `/collection?artifact=[id]` (optionally `&collection=[collectionId]`)
3. Opens the ArtifactDetailsModal on that page

---

## 3. Navigation Components

### 3.1 ModalCollectionsTab

**Purpose**: Show collection and group membership and provide collection actions.

**File Location**: `/skillmeat/web/components/entity/modal-collections-tab.tsx`

#### Props Interface

```typescript
interface ModalCollectionsTabProps {
  /** Artifact to render membership for */
  artifact: Artifact;

  /** Optional handler to view in collection page */
  onViewInCollection?: (collectionId: string, artifactId: string) => void;

  /** Optional handler to open in manage page */
  onOpenInManage?: (artifactId: string) => void;
}
```

#### Visual Layout

```
+------------------------------------------------------------------+
| COLLECTIONS & GROUPS                                              |
+------------------------------------------------------------------+
| [Collection Name 1]                                              |
|   [View in Collection]  [Manage Artifact]                        |
+------------------------------------------------------------------+
| [Collection Name 2]                                              |
|   [View in Collection]  [Manage Artifact]                        |
+------------------------------------------------------------------+
```

#### Button Behaviors

| Button | Action | Navigation Target |
|--------|--------|------------------|
| View in Collection | Close modal, navigate | `/collection?collection=[id]&artifact=[artifactId]` |
| Manage Artifact | Close modal, navigate | `/manage?artifact=[artifactId]` |

---

### 3.2 CrossNavigationButtons

**Purpose**: Consistent cross-page navigation buttons in modal headers.

**File Location**: `/skillmeat/web/components/shared/cross-navigation-buttons.tsx`

#### Props Interface

```typescript
interface CrossNavigationButtonsProps {
  /** Current page context */
  currentPage: 'collection' | 'manage';

  /** Artifact ID for navigation */
  artifactId: string;

  /** Collection ID (if in collection context) */
  collectionId?: string;

  /** Handler for navigation */
  onNavigate: (target: 'collection' | 'manage') => void;
}
```

#### Visual Layout

Positioned in modal header, top-right:

```
Collection Page Modal:
  [Settings Icon] Manage Artifact ->

Manage Page Modal:
  [Book Icon] Collection Details ->
```

#### Styling

```typescript
// Button styles for cross-navigation
const crossNavButtonStyles = cn(
  'flex items-center gap-2',
  'text-sm text-muted-foreground',
  'hover:text-foreground',
  'transition-colors'
);
```

**Navigation state**: include `returnTo` query param when switching contexts
to preserve filters and collection selection (e.g., `/manage?artifact=...&returnTo=/collection?...`).

---

## 4. Filter Components

### 4.1 ManagePageFilters

**Purpose**: Operations-focused filtering for the manage page.

**File Location**: `/skillmeat/web/components/manage/manage-page-filters.tsx`

#### Props Interface

```typescript
interface ManagePageFiltersProps {
  /** Currently selected project filter */
  projectFilter: string | null;

  /** Handler for project filter change */
  onProjectFilterChange: (projectId: string | null) => void;

  /** Currently selected status filter */
  statusFilter: OperationalStatus | null;

  /** Handler for status filter change */
  onStatusFilterChange: (status: OperationalStatus | null) => void;

  /** Currently selected type filter */
  typeFilter: ArtifactType | null;

  /** Handler for type filter change */
  onTypeFilterChange: (type: ArtifactType | null) => void;

  /** Available projects for dropdown */
  projects: ProjectOption[];

  /** Optional tag filter (retained from existing manage filters) */
  tagFilter?: string[];

  /** Handler for tag filter change */
  onTagFilterChange?: (tags: string[]) => void;

  /** Search query */
  searchQuery: string;

  /** Handler for search change */
  onSearchChange: (query: string) => void;
}

type OperationalStatus = 'all' | 'needs-update' | 'has-drift' | 'deployed' | 'error';

interface ProjectOption {
  id: string;
  name: string;
  path: string;
}
```

#### Visual Layout

```
+------------------------------------------------------------------+
| [Search: Filter artifacts...]                                     |
+------------------------------------------------------------------+
| Project: [All Projects v]  Status: [All v]  Type: [All v]        |
+------------------------------------------------------------------+
| Tags: [tag-a x] [tag-b x]                                         |
+------------------------------------------------------------------+
| Active Filters: [Project: MyApp x] [Status: Needs Update x]      |
+------------------------------------------------------------------+
```

#### Filter Dropdown Options

**Project Filter**:
- All Projects (default)
- [List of projects from useProjects hook]

**Status Filter**:
- All
- Needs Update (syncStatus === 'outdated' || upstream.updateAvailable)
- Has Drift (syncStatus === 'modified')
- Deployed (has deployments)
- Error (syncStatus === 'error')

**Type Filter**:
- All
- Skills
- Commands
- Agents
- MCP Servers
- Hooks

**Tags Filter (optional)**:
- Multi-select chips with clear actions

---

### 4.2 CollectionPageFilters

**Purpose**: Discovery-focused filtering for the collection page.

**File Location**: `/skillmeat/web/components/collection/collection-page-filters.tsx`

#### Props Interface

```typescript
interface CollectionPageFiltersProps {
  /** Currently selected collection */
  collectionId: string | null;

  /** Handler for collection change */
  onCollectionChange: (collectionId: string | null) => void;

  /** Currently selected group filter */
  groupFilter: string | null;

  /** Handler for group filter change */
  onGroupFilterChange: (groupId: string | null) => void;

  /** Currently selected type filter */
  typeFilter: ArtifactType | null;

  /** Handler for type filter change */
  onTypeFilterChange: (type: ArtifactType | null) => void;

  /** Currently selected tags */
  selectedTags: string[];

  /** Handler for tags change */
  onTagsChange: (tags: string[]) => void;

  /** Available tags with counts */
  availableTags: TagWithCount[];

  /** Available groups for current collection */
  groups: GroupOption[];

  /** Search query */
  searchQuery: string;

  /** Handler for search change */
  onSearchChange: (query: string) => void;

  /** Available tools for filtering */
  availableTools?: string[];

  /** Currently selected tools */
  selectedTools?: string[];

  /** Handler for tools change */
  onToolsChange?: (tools: string[]) => void;
}

interface TagWithCount {
  name: string;
  artifact_count: number;
}

interface GroupOption {
  id: string;
  name: string;
  artifact_count: number;
}
```

#### Visual Layout

```
+------------------------------------------------------------------+
| [Search: Search artifacts...]                                     |
+------------------------------------------------------------------+
| Collection: [My Collection v]  Group: [All Groups v]              |
| Type: [All v]  [Tags Filter]  [Tools Filter]                     |
+------------------------------------------------------------------+
| Active: [Tag: python x] [Tag: automation x] [Tool: Bash x]       |
+------------------------------------------------------------------+
```

#### Tag Filter Popover

Uses existing `TagFilterPopover` component with:
- Tag search input
- Tag list with counts
- Multi-select checkboxes
- "Clear All" action

#### Tools Filter (New)

**Dependency**: Tools API support PRD (`/docs/project_plans/PRDs/tools-api-support-v1.md`).
If tools are not returned by the API, this filter should be hidden or disabled
with a clear empty state.

```typescript
interface ToolFilterProps {
  tools: string[];
  selectedTools: string[];
  onChange: (tools: string[]) => void;
}
```

Display as popover with tool checkboxes:
- Bash
- Read
- Write
- Edit
- WebSearch
- WebFetch
- etc.

---

## 5. Shared Component Utilities

### 5.1 StatusBadge

**File Location**: `/skillmeat/web/components/shared/status-badge.tsx`

```typescript
interface StatusBadgeProps {
  status: SyncStatus;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  showLabel?: boolean;
}

export function StatusBadge({
  status,
  size = 'md',
  showIcon = true,
  showLabel = true,
}: StatusBadgeProps) {
  const config = statusConfigs[status];

  return (
    <Badge
      variant="outline"
      className={cn(config.className, sizeClasses[size])}
    >
      {showIcon && <config.icon className="h-3 w-3 mr-1" />}
      {showLabel && config.label}
    </Badge>
  );
}
```

### 5.2 HealthIndicator

**File Location**: `/skillmeat/web/components/shared/health-indicator.tsx`

```typescript
interface HealthIndicatorProps {
  artifact: Artifact;
  size?: 'sm' | 'md' | 'lg';
  showTooltip?: boolean;
}

export function HealthIndicator({
  artifact,
  size = 'md',
  showTooltip = true,
}: HealthIndicatorProps) {
  const health = deriveHealthStatus(artifact);

  const indicator = (
    <div className={cn('flex items-center gap-1', healthColors[health])}>
      <HealthIcon health={health} size={size} />
    </div>
  );

  if (showTooltip) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>{indicator}</TooltipTrigger>
          <TooltipContent>{healthDescriptions[health]}</TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return indicator;
}

function deriveHealthStatus(artifact: Artifact): HealthStatus {
  if (artifact.syncStatus === 'error') return 'error';
  if (artifact.syncStatus === 'conflict') return 'error';
  if (artifact.upstream?.updateAvailable) return 'needs-update';
  if (artifact.syncStatus === 'modified') return 'has-drift';
  return 'healthy';
}
```

### 5.3 DeploymentBadgeStack

**File Location**: `/skillmeat/web/components/shared/deployment-badge-stack.tsx`

```typescript
interface DeploymentBadgeStackProps {
  deployments: ArtifactDeploymentInfo[];
  maxBadges?: number;
  onBadgeClick?: (deployment: ArtifactDeploymentInfo) => void;
  /** Called when overflow badge is clicked; should open modal on deployments tab */
  onOverflowClick?: () => void;
}

export function DeploymentBadgeStack({
  deployments,
  maxBadges = 2,
  onBadgeClick,
  onOverflowClick,
}: DeploymentBadgeStackProps) {
  const visible = deployments.slice(0, maxBadges);
  const overflow = deployments.length - maxBadges;
  const hiddenDeployments = deployments.slice(maxBadges);

  return (
    <div className="flex flex-wrap items-center gap-1">
      {visible.map((deployment) => (
        <Badge
          key={deployment.project_path}
          variant="secondary"
          className="cursor-pointer text-xs hover:bg-secondary/80"
          onClick={() => onBadgeClick?.(deployment)}
        >
          {extractProjectName(deployment.project_path)}
        </Badge>
      ))}
      {overflow > 0 && (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Badge
                variant="outline"
                className="cursor-pointer text-xs hover:bg-muted"
                onClick={() => onOverflowClick?.()}
              >
                +{overflow}
              </Badge>
            </TooltipTrigger>
            <TooltipContent>
              <div className="space-y-1">
                {hiddenDeployments.map((d) => (
                  <div key={d.project_path} className="text-xs">
                    {extractProjectName(d.project_path)}
                  </div>
                ))}
              </div>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}
    </div>
  );
}

// Overflow click handler opens modal on deployments tab
```

---

## 6. Implementation Checklist

### Component State Requirements

Each card and modal component must handle:

- [ ] Default state
- [ ] Hover/Focus states
- [ ] Active/Pressed state
- [ ] Disabled state
- [ ] Loading state (skeleton)
- [ ] Error state
- [ ] Empty state
- [ ] Dark mode variant

### Accessibility Checklist

- [ ] All interactive elements keyboard accessible
- [ ] ARIA labels on icon-only buttons
- [ ] Focus management in modals
- [ ] Screen reader announcements for status changes
- [ ] Color contrast meets WCAG AA
- [ ] Reduced motion support

### Testing Requirements

- [ ] Unit tests for each component
- [ ] RTL queries use accessible selectors
- [ ] Mock data follows Artifact type
- [ ] Snapshot tests for visual regression
- [ ] E2E tests for critical flows

---

## 7. Migration Notes

### Existing Components to Update

1. **UnifiedCard** (`/components/shared/unified-card.tsx`)
   - Consider splitting into `ArtifactBrowseCard` and `ArtifactOperationsCard`
   - Or add a `variant` prop: `'browse' | 'operations'`

2. **UnifiedEntityModal** (`/components/entity/unified-entity-modal.tsx`)
   - Very large (25K+ tokens) - consider refactoring
   - Split into `ArtifactDetailsModal` and `ArtifactOperationsModal`
   - Extract tab content into separate components

3. **CollectionArtifactModal** (`/components/shared/CollectionArtifactModal.tsx`)
   - Currently a thin wrapper around UnifiedEntityModal
   - Update to use new ArtifactDetailsModal

### Breaking Changes

1. **Card Props**: New card components have different prop signatures
2. **Modal Structure**: Tab structure differs between discovery and operations
3. **Filter State**: New filter types for operational status

### Migration Path

1. Create new components alongside existing ones
2. Gradually migrate pages to new components (no feature flags)
3. Remove old components after migration complete

---

## 8. Related Files

### Types
- `/skillmeat/web/types/artifact.ts` - Artifact type definition
- `/skillmeat/web/types/collections.ts` - Collection types
- `/skillmeat/web/types/groups.ts` - Group types
- `/skillmeat/web/types/deployments.ts` - Deployment types
- `/skillmeat/web/types/drift.ts` - Drift detection types

### Existing Components (Reference)
- `/skillmeat/web/components/shared/unified-card.tsx`
- `/skillmeat/web/components/entity/unified-entity-modal.tsx`
- `/skillmeat/web/components/collection/artifact-grid.tsx`
- `/skillmeat/web/components/shared/CollectionArtifactModal.tsx`

### Pages
- `/skillmeat/web/app/collection/page.tsx`
- `/skillmeat/web/app/manage/page.tsx`

### Patterns Documentation
- `/.claude/context/key-context/component-patterns.md`
- `/.claude/rules/web/components.md`
