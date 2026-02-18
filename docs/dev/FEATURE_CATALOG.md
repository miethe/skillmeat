# SkillMeat - Complete Feature Catalog

**Last Updated**: 2026-02-17
**Version**: 0.3.0-beta
**Purpose**: Comprehensive inventory of all UI pages, components, modals, and API endpoints for screenshot planning and feature documentation

---

## Table of Contents

1. [Main Navigation](#main-navigation)
2. [Pages & Views](#pages--views)
3. [Reusable Components](#reusable-components)
4. [Forms & Modals](#forms--modals)
5. [Dashboard Widgets](#dashboard-widgets)
6. [Filtering & Sorting](#filtering--sorting)
7. [API Endpoints](#api-endpoints)

---

## Main Navigation

**Primary Navigation Bar** (Top-level sections accessible from sidebar)

- Dashboard (/)
- Collection (/collection)
- Manage (/manage)
- Projects (/projects)
- Deployments (/deployments)
- Marketplace (/marketplace)
  - Marketplace Listings
  - GitHub Sources
  - Publish Bundle
- Groups (/groups)
- Context Entities (/context-entities)
- Templates (/templates)
- MCP Servers (/mcp)
- Settings (/settings)
- Sharing (/sharing)

---

## Pages & Views

### 1. Dashboard (/)

**Path**: `/app/page.tsx`

**Purpose**: Main landing page with analytics and quick stats

**Key UI Elements**:
- Page title: "Dashboard"
- Subtitle: "Welcome to SkillMeat - Your personal collection manager..."
- Analytics Grid with live updates enabled
  - Total artifacts count
  - Deployment statistics
  - Usage trends widget
  - Tag metrics widget
  - Top artifacts widget

**Features**:
- Real-time analytics updates
- Responsive grid layout
- Summary statistics cards

---

### 2. Collection (/collection)

**Path**: `/app/collection/page.tsx`

**Purpose**: Browse and manage artifacts organized by collections

**View Modes**:
- Grid view (default)
- List view
- Grouped view (Phase 5 placeholder)

**Key UI Elements**:

**Header Section**:
- Collection selector (dropdown)
- Current collection info (name, description)
- Artifact count display
- Edit/Delete buttons (when collection selected)
- Create Collection button

**Toolbar**:
- View mode toggle (Grid/List/Grouped icons)
- Search input (searches name, description, tags)
- Sort dropdown:
  - Confidence (descending)
  - Name (A-Z)
  - Updated date
  - Usage count
- Unified multi-select filter menu:
  - Artifact Type (skill/command/agent/mcp/hook)
  - Status (synced/modified/outdated/conflict/error)
  - Scope (user/local)
  - Groups (all available groups)
  - Filter mode toggle: AND (all filters must match) / OR (any filter matches)
- Tag filter bar
- Refresh button
- Last updated timestamp

**Main Content Area**:

**Empty States**:
- "No artifacts in this collection" (when empty)
- "No artifacts" (when viewing all collections empty)
- "No results found" (when search/filters applied but no matches)

**Artifact Display**:
- **Grid View**: Cards in 3-column responsive layout
  - Card shows: name, type badge, description, group badges (colored), source labels with GitHub links, alphabetically sorted tags, action menu
  - Collection badge (when viewing "All Collections")
  - Click to open detail modal

- **List View**: Table-style rows
  - Columns: Name, Type, Collection, Status, Updated, Actions
  - Sortable column headers
  - Inline action buttons

**Artifact Card Actions**:
- View details (click card)
- Edit parameters
- Delete
- Move to collection
- Manage groups
- Dropdown menu

**Infinite Scroll**:
- Loads 20 artifacts per page
- Trigger at 200px from bottom
- "Loading more..." spinner
- "All {N} artifacts loaded" message

**Modals**:
- Collection Artifact Detail Modal
- Edit Collection Dialog
- Create Collection Dialog
- Move/Copy Dialog
- Add to Group Dialog
- Parameter Editor Modal
- Artifact Deletion Dialog

---

### 3. Manage (/manage)

**Path**: `/app/manage/page.tsx`

**Purpose**: Entity-focused management interface for all artifact types

**Key UI Elements**:

**Header**:
- Title: "Entity Management"
- Tab navigation: Skills | Commands | Agents | MCP | Hooks
- View mode toggle (Grid/List)
- Add Entity button

**Toolbar**:
- Search input
- Filters:
  - Status filter
  - Tag filter

**Main Content**:
- Entity list (grid or list view based on selection)
- Infinite scroll pagination
- Each entity card shows:
  - Name
  - Type
  - Status badge
  - Tags
  - Action menu

**Detail Panel** (Right sidebar when entity selected):
- Entity information
- File tree (if applicable)
- Related actions
- Close button

**Modals & Dialogs**:
- Add Entity Dialog
- Unified Entity Modal (detail view with tabs)
- Entity Form (for editing)
- Entity Deletion Dialog
- File Creation/Deletion Dialogs
- Merge Workflow Dialog
- Rollback Dialog

---

### 4. Projects (/projects)

**Path**: `/app/projects/page.tsx`

**Purpose**: Manage deployed projects and their configurations

**Key UI Elements**:

**Header**:
- Title: "Projects"
- Subtitle: "Manage your deployed projects and configurations"
- Create New Project button

**Toolbar** (ProjectsToolbar):
- Last fetched timestamp
- Stale indicator
- Cache hit/miss indicator
- Refresh button
- Manual refresh capability

**Alerts**:
- Outdated artifacts alert card
  - Shows count of artifacts with available updates
  - "View Details" button
  - Update Available Modal

**Content**:
- Projects list (grid or card layout)
  - Project name
  - Project path
  - Deployment count
  - Last deployment date
  - Action menu

**Dialogs**:
- Create Project Dialog
- Project Detail Dialog (quick view)
- Update Available Modal (for outdated artifacts)

**Sub-pages**:

#### Project Detail (/projects/[id])
- Full project information
- Deployment history
- Configuration details
- Edit project settings

#### Project Settings (/projects/[id]/settings)
- Project configuration
- Deployment settings
- Integration options

#### Project Manage (/projects/[id]/manage)
- Artifact deployments
- Pull from collection
- Deploy from collection
- Sync status
- Drift detection

---

### 5. Deployments (/deployments)

**Path**: `/app/deployments/page.tsx`

**Purpose**: Deployment dashboard with filtering and status overview

**Key UI Elements**:

**Header**:
- Title: "Deployments"

**Summary Cards**:
- Total deployments
- Status breakdown (synced, modified, outdated, conflict, error)

**Toolbar**:
- Search input (artifact name)
- Status filter dropdown (all/synced/modified/outdated/conflict/error)
- Type filter multi-select:
  - Skill
  - Command
  - Agent
  - MCP
  - Hook
- View mode toggle (flat/grouped by project)
- Refresh button

**Main Content**:
- **Flat View**: List of all deployments
  - Deployment cards with status badges
  - Artifact name, type, project, sync status
  - Last deployed date
  - Action menu

- **Grouped View**: Deployments grouped by project
  - Collapsible project sections
  - Deployments within each project
  - Group-level statistics

**Deployment Card**:
- Artifact name
- Type badge
- Project name
- Status badge with color coding
- Last deployment time
- Action menu (view diff, sync, etc.)

---

### 6. Marketplace (/marketplace)

**Path**: `/app/marketplace/page.tsx`

**Purpose**: Browse and install artifacts from marketplace brokers

**Key UI Elements**:

**Header**:
- Title: "Marketplace"
- Subtitle: "Browse and install bundles from marketplace brokers"
- "GitHub Sources" button
- "Publish Bundle" button

**Stats Widget** (MarketplaceStats):
- Total listings count
- Listings by type/category
- Average rating/popularity metrics

**Filters** (MarketplaceFilters):
- Search input
- Broker filter (multi-select)
- Category/Type filter
- Popularity/Rating filter
- Date range filter

**Results**:
- Listings count display
- Error state (if fetch fails)
- Loading state (skeleton cards)
- Empty state (no results)
- Listings grid (3-column responsive)

**Listing Card** (MarketplaceListingCard):
- Bundle name
- Broker name
- Description
- Tags/Categories
- Rating/Popularity badge
- Install button
- "View Details" link

**Dialogs**:
- Marketplace Install Dialog (strategy selection)
- Install Confirmation (merge/fork/skip)

---

#### Marketplace Sources (/marketplace/sources)

**Path**: `/app/marketplace/sources/page.tsx`

**Purpose**: Manage GitHub sources that are scanned for artifacts

**Key UI Elements**:

**Header**:
- Add Source button
- Search/Filter bar

**Search Modes** (SearchModeToggle):
- Sources mode: Filter sources by repository name
- Artifacts mode: Search across all catalog entries (FTS5)

**Filter Bar** (SourceFilterBar):
- Artifact type filter
- Trust level filter
- Tags filter
- Active filter count badge
- Clear filters button

**Source Cards** (SourceCard):
- Repository name
- Last scan date
- Artifact count
- Stars/Repo metrics
- Status badge
- Action menu:
  - Rescan
  - Edit
  - Delete
  - View details

**Artifact Search Results** (when in Artifacts mode):
- Artifact name
- Artifact type
- Source repository
- Tags
- Trust score
- Click to view catalog entry

**Modals**:
- Add Source Modal
- Edit Source Modal
- Delete Source Dialog
- Rescan Updates Dialog (shows new/updated artifacts)
- Artifact Search Results detail
- Catalog Entry Modal (detail view)

**URL State Synchronization**:
- Search query: `?q=query`
- Artifact type: `?artifact_type=skill`
- Trust level: `?trust_level=high`
- Tags: `?tags=tag1,tag2`

---

#### Marketplace Source Detail (/marketplace/sources/[id])

**Path**: `/app/marketplace/sources/[id]/page.tsx`

**Purpose**: Detailed view of a GitHub source with semantic tree navigation

**Key Components**:

**Toolbar** (SourceToolbar):
- Back button
- Refresh/Rescan button
- Search input
- Info icon

**Main Layout**:
- **Semantic Tree** (left/center):
  - Folder hierarchy visualization
  - Collapsible/expandable folders
  - Artifact type indicators
  - Click to select item

- **Detail Pane** (right):
  - Selected folder/artifact details
  - README content (markdown preview)
  - File listing
  - Artifact metadata

**Folder Detail Components**:
- Folder header with name and description
- Subfolder cards (if applicable):
  - Subfolder name
  - Artifact count
  - Description preview
  - Navigate button

- Artifact Type Sections:
  - Grouped by type (Skills, Commands, etc.)
  - Count badge per type
  - Expandable list
  - View/Edit/Exclude buttons

- Excluded Items List:
  - Artifacts that are excluded from import
  - Unexclude button

**Modals**:
- Folder detail modal
- Artifact detail modal
- Exclude artifact dialog
- Bulk tag dialog
- Auto-tags dialog

---

#### Marketplace Listing Detail (/marketplace/[listing_id])

**Path**: `/app/marketplace/[listing_id]/page.tsx`

**Purpose**: Detailed view of a marketplace listing

**Content**:
- Listing title and description
- Broker information
- Artifact bundle contents
- Installation instructions
- Install button
- Related listings

---

#### Marketplace Publish (/marketplace/publish)

**Path**: `/app/marketplace/publish/page.tsx`

**Purpose**: Wizard for publishing artifact bundles to marketplace

**Wizard Steps**:
1. Select artifacts to publish
2. Bundle configuration
3. Broker selection
4. Review and publish
5. Confirmation

**Key Elements**:
- Step indicator
- Next/Back buttons
- Artifact selector
- Bundle name/description input
- Broker dropdown
- Publish button
- Success confirmation

---

### 7. Groups (/groups)

**Path**: `/app/groups/page.tsx`

**Purpose**: Browse and manage artifacts organized by groups with drag-and-drop support

**Key UI Elements**:

**Two-Pane Layout**:

**GroupSidebar** (280px fixed left pane):
- 'All Artifacts' virtual item (displays all ungrouped artifacts)
- 'Ungrouped' virtual item (displays unassigned artifacts)
- Separator
- Group items with:
  - Custom color indicator dot
  - Type icon
  - Group name
  - Artifact count badge
- 'Create Group' button (opens GroupFormDialog)
- 'Manage' button (navigates to /groups/manage)

**ArtifactPane** (flex-1 right pane):
- **PaneHeader**:
  - Selected group name
  - Artifact count in group
  - Refresh button
- **RemoveFromGroupDropZone** (conditional, shows when group selected):
  - Drop zone for removing artifacts from group
  - Visual feedback on hover
- **MiniArtifactCard Grid**:
  - Responsive grid of compact artifact cards
  - Draggable cards (drag to sidebar to add to group)
  - Quick view/edit/delete actions
  - Empty state: "No artifacts in this group"

**Group Management Hub** (/groups/manage):
- Card-based grid layout of GroupCard components
- GroupCard displays:
  - Group color indicator
  - Group icon
  - Group name
  - Artifact count
  - Edit/Delete buttons
- 'Create Group' button (top right)
- GroupFormDialog for create/edit with:
  - Group name input
  - Custom color picker (compact palette)
  - Icon selection
  - Description text field
- GroupDeleteDialog for confirmation with artifact count warning

**Group Metadata**:
- Custom color (compact picker with predefined palette)
- Icon selection (dropdown or icon picker)
- Description field (markdown support)

**Drag & Drop Interactions**:
- **Add to Group**: Drag artifact card from ArtifactPane to group in sidebar
- **Remove from Group**: Drag artifact card to RemoveFromGroupDropZone (only visible when group selected)
- **Animations** (DndAnimations component):
  - Pickup scale animation
  - Drop settle animation
  - Poof effect on remove
  - Particle effects on drop
  - Ghost pulse during drag
  - Drop target pulse on hover
  - Remove zone breathe animation

**Features**:
- Visual group organization with color coding
- Quick group navigation
- One-click group management
- Drag-and-drop artifact assignment
- Smooth, polished animations
- Cross-collection group browsing

---

### 8. Context Entities (/context-entities)

**Path**: `/app/context-entities/page.tsx`

**Purpose**: Manage Claude Code context entities (project config, instructions, etc.)

**Key UI Elements**:

**Header**:
- Title: "Context Entities"
- Add Entity button

**Filters** (ContextEntityFilters):
- Entity type filter
- Status filter
- Search input

**Entity Cards** (ContextEntityCard):
- Entity name
- Type badge
- Description
- Tags
- Last updated
- Action menu

**Empty States**:
- "No context entities" (when empty)
- "No entities match filters" (when filters applied)

**Modals**:
- Context Entity Detail Modal
- Context Entity Editor Modal
- Deploy to Project Dialog
- Delete Confirmation

**Features**:
- Create new entities
- Edit entities
- Preview/View entities
- Deploy to projects
- Delete entities
- Cursor-based pagination

---

### 9. Templates (/templates)

**Path**: `/app/templates/page.tsx`

**Purpose**: Project templates for quick project setup

**Key UI Elements**:

**Header**:
- Title: "Templates"
- Search input

**Template Cards** (TemplateCard):
- Template name
- Description
- Included artifacts count
- Estimated deployment time
- Deploy button
- View details link

**Empty States**:
- "No templates available" (when empty)
- "No templates match filters" (when search applied)

**Modals**:
- Template Detail Modal (TemplateDetail):
  - Full description
  - Included artifacts list
  - Prerequisites
  - Deployment instructions

- Template Deploy Wizard (TemplateDeployWizard):
  - Step 1: Review template
  - Step 2: Configure deployment
  - Step 3: Select project
  - Step 4: Review and deploy
  - Deployment progress

**Features**:
- Search templates
- View details
- Deploy to project
- Cursor-based pagination

---

### 10. MCP Servers (/mcp)

**Path**: `/app/mcp/page.tsx`

**Purpose**: Manage Model Context Protocol server configurations

**Key UI Elements**:

**Header**:
- Title: "MCP Servers"
- Subtitle: "Manage Model Context Protocol server configurations"
- Add Server button

**Server List** (MCPServerList):
- Server cards with:
  - Server name
  - Repository/Source
  - Version
  - Description
  - Status badge
  - Action menu

**Error State**:
- Failure card with error message
- Retry button

**Modals**:
- MCP Server Form Modal:
  - Server name input
  - Repository input
  - Version input
  - Description input
  - Environment variables editor (MCPEnvEditor)
    - Key/Value pair inputs
    - Add/Remove variable buttons

**Features**:
- Add new MCP servers
- View server list
- Configuration management
- Environment variable management

---

#### MCP Server Detail (/mcp/[name])

**Path**: `/app/mcp/[name]/page.tsx`

**Purpose**: Detailed view of a specific MCP server

**Content**:
- Server information
- Configuration details
- Environment variables
- Deploy button
- Edit/Delete options
- Connection status

---

### 11. Settings (/settings)

**Path**: `/app/settings/page.tsx`

**Purpose**: Application preferences and integrations

**Key UI Elements**:

**General Settings Card**:
- Application preferences
- Default scope configuration
- GitHub authentication

**API Configuration Card**:
- API URL display
- Version display

**GitHub Settings Component** (GitHubSettings):
- GitHub token input
- Token status indicator
- Connection test button
- Rate limit information

---

### 12. Sharing (/sharing)

**Path**: `/app/sharing/page.tsx`

**Purpose**: Manage artifact bundles and sharing settings

**Key Features**:
- Bundle list
- Bundle preview
- Export dialog
- Import dialog
- Permission management
- Share link generation

---

## Reusable Components

### Collection-Domain Components

| Component | Path | Purpose |
|-----------|------|---------|
| CollectionHeader | `collection/collection-header.tsx` | Header with collection info and controls |
| CollectionToolbar | `collection/collection-toolbar.tsx` | Search, filter, sort, view mode controls |
| ArtifactGrid | `collection/artifact-grid.tsx` | Responsive grid of artifact cards |
| ArtifactList | `collection/artifact-list.tsx` | Tabular list of artifacts |
| GroupedArtifactView | `collection/grouped-artifact-view.tsx` | Group-based artifact organization |
| CollectionSwitcher | `collection/collection-switcher.tsx` | Collection selection component |
| CollectionBadgeStack | `shared/collection-badge-stack.tsx` | Display multiple collection badges |
| ConflictResolver | `collection/conflict-resolver.tsx` | Handle sync conflicts |
| SyncDialog | `collection/sync-dialog.tsx` | Sync operations with progress |
| VersionTree | `collection/version-tree.tsx` | Version history visualization |

### Entity-Domain Components

| Component | Path | Purpose |
|-----------|------|---------|
| EntityCard | `entity/entity-card.tsx` | Individual entity display card |
| EntityList | `entity/entity-list.tsx` | Entity list view |
| EntityRow | `entity/entity-row.tsx` | Single row in entity table |
| EntityForm | `entity/entity-form.tsx` | Create/edit entity form |
| EntityActions | `entity/entity-actions.tsx` | Action menu for entities |
| ContentPane | `entity/content-pane.tsx` | Entity content display |
| FileTree | `entity/file-tree.tsx` | File hierarchy view |
| DiffViewer | `entity/diff-viewer.tsx` | Show differences between versions |
| MergeWorkflow | `entity/merge-workflow.tsx` | Multi-step merge wizard |
| ArtifactLinkingDialog | `entity/artifact-linking-dialog.tsx` | Link related artifacts |

### Marketplace Components

| Component | Path | Purpose |
|-----------|------|---------|
| MarketplaceListingCard | `marketplace/MarketplaceListingCard.tsx` | Listing preview card |
| MarketplaceListingDetail | `marketplace/MarketplaceListingDetail.tsx` | Detailed listing view |
| MarketplaceFilters | `marketplace/MarketplaceFilters.tsx` | Filter controls |
| MarketplaceStats | `marketplace/MarketplaceStats.tsx` | Statistics widget |
| MarketplaceInstallDialog | `marketplace/MarketplaceInstallDialog.tsx` | Install strategy selection |
| MarketplacePublishWizard | `marketplace/MarketplacePublishWizard.tsx` | Multi-step publish wizard |
| SourceCard | `marketplace/source-card.tsx` | GitHub source preview |
| SourceFilterBar | `marketplace/source-filter-bar.tsx` | Source filtering |
| AddSourceModal | `marketplace/add-source-modal.tsx` | Add new source |
| EditSourceModal | `marketplace/edit-source-modal.tsx` | Edit source config |
| DeleteSourceDialog | `marketplace/delete-source-dialog.tsx` | Confirm deletion |
| SemanticTree | `marketplace/sources/[id]/components/semantic-tree.tsx` | Folder hierarchy for sources |
| FolderDetailPane | `marketplace/sources/[id]/components/folder-detail-pane.tsx` | Folder information display |
| SubfolderCard | `marketplace/sources/[id]/components/subfolder-card.tsx` | Subfolder preview |
| ArtifactTypeSection | `marketplace/sources/[id]/components/artifact-type-section.tsx` | Grouped artifact types |
| SourceToolbar | `marketplace/sources/[id]/components/source-toolbar.tsx` | Source navigation toolbar |
| ExcludedList | `marketplace/sources/[id]/components/excluded-list.tsx` | Excluded artifacts list |
| CatalogList | `marketplace/sources/[id]/components/catalog-list.tsx` | Catalog entries |
| CatalogTabs | `marketplace/sources/[id]/components/catalog-tabs.tsx` | Tabbed catalog view |

### Shared Components

| Component | Path | Purpose |
|-----------|------|---------|
| UnifiedCard | `shared/unified-card.tsx` | Unified artifact card |
| UnifiedCardActions | `shared/unified-card-actions.tsx` | Common card actions |
| CollectionArtifactModal | `shared/CollectionArtifactModal.tsx` | Collection artifact detail modal |
| ProjectArtifactModal | `shared/ProjectArtifactModal.tsx` | Project artifact modal |
| GroupBadgeRow | `shared/group-badge-row.tsx` | Display group badges |
| GroupFilterSelect | `shared/group-filter-select.tsx` | Group selection filter |
| TagEditor | `shared/tag-editor.tsx` | Tag input/editing |
| Header | `header.tsx` | Global header |
| Navigation | `navigation.tsx` | Sidebar navigation |

### Discovery/Import Components

| Component | Path | Purpose |
|-----------|------|---------|
| DiscoveryTab | `discovery/DiscoveryTab.tsx` | Artifact discovery interface |
| BulkImportModal | `discovery/BulkImportModal.tsx` | Bulk import wizard |
| ParameterEditorModal | `discovery/ParameterEditorModal.tsx` | Edit artifact parameters |
| DuplicateReviewModal | `discovery/DuplicateReviewModal.tsx` | Review duplicate artifacts |
| SkipPreferencesList | `discovery/SkipPreferencesList.tsx` | Manage skip rules |
| AutoPopulationForm | `discovery/AutoPopulationForm.tsx` | Auto-population settings |
| DiscoveryBanner | `discovery/DiscoveryBanner.tsx` | Discovery status banner |

### Dashboard Components

| Component | Path | Purpose |
|-----------|------|---------|
| AnalyticsGrid | `dashboard/analytics-grid.tsx` | Main analytics dashboard |
| StatsCards | `dashboard/stats-cards.tsx` | Summary statistics |
| UsageTrendsWidget | `dashboard/usage-trends-widget.tsx` | Usage trends chart |
| TagMetricsWidget | `dashboard/tag-metrics-widget.tsx` | Tag usage metrics |
| TopArtifactsWidget | `dashboard/top-artifacts-widget.tsx` | Most used artifacts |

### MCP Components

| Component | Path | Purpose |
|-----------|------|---------|
| MCPServerList | `mcp/MCPServerList.tsx` | Server list view |
| MCPServerCard | `mcp/MCPServerCard.tsx` | Individual server card |
| MCPServerForm | `mcp/MCPServerForm.tsx` | Server configuration form |
| MCPEnvEditor | `mcp/MCPEnvEditor.tsx` | Environment variables editor |
| MCPDeployButton | `mcp/MCPDeployButton.tsx` | Deploy server button |

### UI Primitives (shadcn)

- Button
- Card
- Dialog
- Dropdown Menu
- Input
- Label
- Badge
- Alert
- Accordion
- Alert Dialog
- Checkbox
- Collapsible
- Command
- Popover
- Progress
- Radio Group
- Scroll Area
- Select
- Separator
- Sheet
- Skeleton
- Switch
- Tabs
- Table
- Tag Filter Popover
- Tag Input
- Textarea
- Tooltip
- Toaster

---

## Forms & Modals

### Collection-Related Dialogs

| Dialog | Path | Purpose |
|--------|------|---------|
| Edit Collection Dialog | `collection/edit-collection-dialog.tsx` | Modify collection metadata |
| Create Collection Dialog | `collection/create-collection-dialog.tsx` | Create new collection |
| Move/Copy Dialog | `collection/move-copy-dialog.tsx` | Move/copy artifacts between collections |
| Add to Group Dialog | `collection/add-to-group-dialog.tsx` | Assign artifacts to groups |
| Manage Groups Dialog | `collection/manage-groups-dialog.tsx` | Manage collection groups |
| Copy Group Dialog | `collection/copy-group-dialog.tsx` | Duplicate group configuration |
| GroupFormDialog | `groups/group-form-dialog.tsx` | Create/edit group with color, icon, description |
| GroupDeleteDialog | `groups/group-delete-dialog.tsx` | Confirm group deletion with artifact count warning |
| Deploy Dialog | `collection/deploy-dialog.tsx` | Deploy artifacts to project |

### Entity-Related Dialogs

| Dialog | Path | Purpose |
|--------|------|---------|
| Unified Entity Modal | `entity/unified-entity-modal.tsx` | Multi-tab entity detail view |
| Entity Deletion Dialog | `entity/artifact-deletion-dialog.tsx` | Confirm artifact deletion |
| Unsaved Changes Dialog | `entity/unsaved-changes-dialog.tsx` | Warn about unsaved edits |
| Rollback Dialog | `history/rollback-dialog.tsx` | Revert to previous version |
| Merge Workflow Dialog | `merge/merge-workflow-dialog.tsx` | Multi-step merge wizard |
| File Creation Dialog | `entity/file-creation-dialog.tsx` | Create new file in artifact |
| File Deletion Dialog | `entity/file-deletion-dialog.tsx` | Remove file from artifact |

### Marketplace Dialogs

| Dialog | Path | Purpose |
|--------|------|---------|
| Add Source Modal | `marketplace/add-source-modal.tsx` | Add GitHub repository |
| Edit Source Modal | `marketplace/edit-source-modal.tsx` | Modify source settings |
| Delete Source Dialog | `marketplace/delete-source-dialog.tsx` | Confirm source removal |
| Rescan Updates Dialog | `marketplace/rescan-updates-dialog.tsx` | Review updated artifacts |
| Exclude Artifact Dialog | `marketplace/exclude-artifact-dialog.tsx` | Exclude from imports |
| Bulk Tag Dialog | `marketplace/bulk-tag-dialog.tsx` | Batch tag artifacts |
| Auto Tags Dialog | `marketplace/auto-tags-dialog.tsx` | Auto-generate tags |
| Directory Map Modal | `marketplace/DirectoryMapModal.tsx` | Directory structure mapping |
| Repo Details Modal | `marketplace/repo-details-modal.tsx` | GitHub repo information |
| Marketplace Install Dialog | `marketplace/MarketplaceInstallDialog.tsx` | Install strategy selection |
| Directory Tag Input | `marketplace/directory-tag-input.tsx` | Tag by directory |
| Path Tag Review | `marketplace/path-tag-review.tsx` | Review path-based tags |
| CatalogEntryModal | `CatalogEntryModal.tsx` | Catalog entry detail |

### Project Dialogs

| Dialog | Path | Purpose |
|--------|------|---------|
| Create Project Dialog | `projects/components/create-project-dialog.tsx` | Create new project |
| Edit Project Dialog | `projects/components/edit-project-dialog.tsx` | Modify project settings |
| Delete Project Dialog | `projects/components/delete-project-dialog.tsx` | Confirm project deletion |
| Project Detail Dialog | Quick view modal on Projects page | Show project overview |

### Context Entity Dialogs

| Dialog | Path | Purpose |
|--------|------|---------|
| Context Entity Detail Modal | `context/context-entity-detail.tsx` | View entity |
| Context Entity Editor Modal | `context/context-entity-editor.tsx` | Edit entity |
| Deploy to Project Dialog | `context/deploy-to-project-dialog.tsx` | Deploy entity to project |

### Discovery Dialogs

| Dialog | Path | Purpose |
|--------|------|---------|
| Bulk Import Modal | `discovery/BulkImportModal.tsx` | Multi-artifact import wizard |
| Parameter Editor Modal | `discovery/ParameterEditorModal.tsx` | Configure artifact parameters |
| Duplicate Review Modal | `discovery/DuplicateReviewModal.tsx` | Handle duplicate detection |

### Update Dialogs

| Dialog | Path | Purpose |
|--------|------|---------|
| Update Available Modal | `UpdateAvailableModal.tsx` | Notify about available updates |
| Rating Dialog | `RatingDialog.tsx` | Rate artifact quality |

### Sharing Dialogs

| Dialog | Path | Purpose |
|--------|------|---------|
| Export Dialog | `sharing/export-dialog.tsx` | Export collection/bundle |
| Import Dialog | `sharing/import-dialog.tsx` | Import bundle |
| Share Link Dialog | `sharing/share-link.tsx` | Generate share URLs |

---

## Dashboard Widgets

### Main Analytics Grid (AnalyticsGrid)

**Widgets Displayed**:

1. **Stats Cards**:
   - Total Artifacts
   - Total Projects
   - Active Deployments
   - Last Sync Time

2. **Usage Trends Widget** (UsageTrendsWidget):
   - Line chart showing usage over time
   - Time range selector
   - Legend with data points
   - Export button

3. **Tag Metrics Widget** (TagMetricsWidget):
   - Tag usage statistics
   - Tag cloud or bar chart
   - Filter by tag
   - Sort options (frequency, alphabetical)

4. **Top Artifacts Widget** (TopArtifactsWidget):
   - Most used artifacts list
   - Usage count per artifact
   - Quick deploy button
   - View details link

5. **Additional Metrics**:
   - Deployment success rate
   - Sync status breakdown
   - Collection statistics

**Features**:
- Real-time updates when `enableLiveUpdates={true}`
- Responsive grid layout
- Loading skeletons
- Empty states
- Responsive charts

---

## Filtering & Sorting

### Collection Page Filters

**Type Filter**:
- All
- Skill
- Command
- Agent
- MCP
- Hook

**Status Filter**:
- All
- Synced
- Modified
- Outdated
- Conflict
- Error

**Scope Filter**:
- All
- User (global)
- Local (project-specific)

**Tag Filter**:
- Multi-select from available tags
- Tag count display
- URL-synchronized (?tags=tag1,tag2)
- Active filter display with clear buttons

**Sorting Options**:
- Confidence (confidence score, descending)
- Name (alphabetical, ascending/descending)
- Updated Date (most recent first)
- Usage Count (most used first)

**Search**:
- Full-text search across name, description, tags
- Real-time filtering
- Case-insensitive

### Deployments Page Filters

**Status Filter**:
- All
- Synced
- Modified
- Outdated
- Conflict
- Error

**Type Filters** (multi-select):
- Skill
- Command
- Agent
- MCP
- Hook

**Search**:
- Artifact name search
- 300ms debounce

**View Modes**:
- Flat: All deployments in single list
- Grouped: Grouped by project path

### Marketplace Filters

**Broker Filter** (multi-select):
- Individual broker options
- Filter by availability

**Category/Type Filter**:
- Artifact type
- Bundle category

**Popularity/Rating**:
- Rating threshold
- Download count
- Usage metrics

**Date Range**:
- Published after
- Updated within

**Search**:
- Full-text search on listings

### Marketplace Sources Filters

**Artifact Type**:
- All
- Skill
- Command
- Agent
- MCP
- Hook

**Trust Level**:
- High
- Medium
- Low

**Tags**:
- Multi-select
- Populated from catalog

**Search Query**:
- URL synchronized (?q=query)
- FTS5 search on artifacts

### Context Entities Filters

**Entity Type**:
- All types
- Specific types

**Status**:
- Active
- Archived
- Unused

**Search**:
- Entity name/description

---

## API Endpoints

### Artifacts Router (`/api/v1/artifacts`)

**Core CRUD**:
- `GET /` - List artifacts (paginated, supports collection_id query parameter for filtering)
- `POST /` - Create artifact
- `GET /{artifact_id}` - Get artifact details
- `PUT /{artifact_id}` - Update artifact
- `DELETE /{artifact_id}` - Delete artifact

**Artifact Management**:
- `GET /{artifact_id}/metadata` - Get artifact metadata
- `GET /{artifact_id}/tags` - Get artifact tags
- `PUT /{artifact_id}/tags` - Update tags
- `GET /{artifact_id}/versions` - Get version history
- `GET /{artifact_id}/files` - List artifact files
- `GET /{artifact_id}/files/{file_path}` - Get file content
- `PUT /{artifact_id}/files/{file_path}` - Update file content

**Deployment**:
- `POST /{artifact_id}/deploy` - Deploy to project
- `GET /{artifact_id}/deployments` - Get deployment history
- `POST /{artifact_id}/deployments/{deployment_id}/rollback` - Rollback deployment

**Sync Operations**:
- `POST /{artifact_id}/sync` - Sync with upstream
- `GET /{artifact_id}/upstream` - Get upstream information
- `GET /{artifact_id}/diff` - Get differences from upstream

**Linking**:
- `POST /{artifact_id}/links` - Create artifact link
- `GET /{artifact_id}/links` - Get linked artifacts
- `DELETE /{artifact_id}/links/{link_id}` - Remove link

**Discovery**:
- `POST /discover` - Discover artifacts from source
- `POST /bulk-import` - Bulk import artifacts
- `POST /parameters/update` - Update artifact parameters

### Collections Router (`/api/v1/collections` - DEPRECATED)

**Read-Only**:
- `GET /` - List collections
- `GET /{collection_id}` - Get collection details
- `GET /{collection_id}/artifacts` - List collection artifacts

**Note**: Use `/user-collections` for full CRUD operations.

### User Collections Router (`/api/v1/user-collections`)

**Full CRUD**:
- `GET /` - List user collections
- `POST /` - Create collection
- `GET /{collection_id}` - Get collection
- `PUT /{collection_id}` - Update collection
- `DELETE /{collection_id}` - Delete collection

**Artifact Management**:
- `GET /{collection_id}/artifacts` - List collection artifacts
- `POST /{collection_id}/artifacts/{artifact_id}` - Add artifact to collection
- `DELETE /{collection_id}/artifacts/{artifact_id}` - Remove artifact

**Group Management**:
- `GET /{collection_id}/groups` - List groups
- `POST /{collection_id}/groups` - Create group
- `PUT /{collection_id}/groups/{group_id}` - Update group
- `DELETE /{collection_id}/groups/{group_id}` - Delete group
- `POST /{collection_id}/groups/{group_id}/artifacts/{artifact_id}` - Add artifact to group

### Groups Router (`/api/v1/groups`)

**Management**:
- `GET /` - List groups
- `POST /` - Create group (with optional color, icon, description)
- `GET /{group_id}` - Get group details
- `PUT /{group_id}` - Update group (supports color, icon, description fields)
- `DELETE /{group_id}` - Delete group

**Group Artifacts**:
- `GET /{group_id}/artifacts` - List group artifacts
- `POST /{group_id}/artifacts/{artifact_id}` - Add artifact
- `DELETE /{group_id}/artifacts/{artifact_id}` - Remove artifact

**Schemas**:
- `GroupCreateRequest` - Includes optional color, icon, and description fields
- `GroupUpdateRequest` - Includes optional color, icon, and description fields

### Projects Router (`/api/v1/projects`)

**Project Management**:
- `GET /` - List projects
- `POST /` - Create project
- `GET /{project_id}` - Get project details
- `PUT /{project_id}` - Update project
- `DELETE /{project_id}` - Delete project

**Project Info**:
- `GET /{project_id}/config` - Get project configuration
- `PUT /{project_id}/config` - Update configuration
- `GET /{project_id}/deployments` - List deployments
- `GET /{project_id}/status` - Get sync/status information

### Deployments Router (`/api/v1/deployments`)

**Deployment Operations**:
- `GET /` - List deployments
- `POST /` - Deploy artifact
- `GET /{deployment_id}` - Get deployment details
- `PUT /{deployment_id}` - Update deployment
- `DELETE /{deployment_id}` - Delete deployment

**Status & Sync**:
- `GET /{deployment_id}/status` - Get deployment status
- `POST /{deployment_id}/sync` - Sync with source
- `POST /{deployment_id}/rollback` - Rollback deployment
- `GET /{deployment_id}/diff` - Show differences

**Bulk Operations**:
- `POST /refresh` - Refresh all deployments
- `GET /summary` - Get deployment summary

### Marketplace Router (`/api/v1/marketplace`)

**Listings**:
- `GET /listings` - List marketplace listings (paginated)
- `GET /listings/{listing_id}` - Get listing details
- `GET /listings/search` - Search listings

**Installation**:
- `POST /listings/{listing_id}/install` - Install listing
- `GET /listings/{listing_id}/preview` - Preview bundle

**Publishing**:
- `POST /publish` - Publish bundle
- `PUT /listings/{listing_id}` - Update listing

**Brokers**:
- `GET /brokers` - List available brokers
- `GET /brokers/{broker_id}` - Get broker info

### Marketplace Catalog Router (`/api/v1/marketplace/catalog`)

**Catalog Management**:
- `GET /` - List catalog entries
- `GET /{entry_id}` - Get entry details
- `POST /` - Create entry
- `PUT /{entry_id}` - Update entry
- `DELETE /{entry_id}` - Delete entry

**Search**:
- `GET /search` - Search catalog (FTS5)
- `GET /by-source/{source_id}` - Get entries by source

### Marketplace Sources Router (`/api/v1/marketplace/sources`)

**Source Management**:
- `GET /` - List sources
- `POST /` - Add source
- `GET /{source_id}` - Get source details
- `PUT /{source_id}` - Update source
- `DELETE /{source_id}` - Delete source

**Source Operations**:
- `POST /{source_id}/scan` - Scan/rescan source
- `GET /{source_id}/tree` - Get directory tree (semantic tree)
- `GET /{source_id}/catalog` - Get catalog for source

**Exclusions**:
- `GET /{source_id}/excluded` - Get excluded artifacts
- `POST /{source_id}/excluded/{artifact_id}` - Exclude artifact
- `DELETE /{source_id}/excluded/{artifact_id}` - Include artifact

**Tagging**:
- `POST /{source_id}/tags/auto` - Auto-generate tags
- `POST /{source_id}/tags/bulk` - Bulk tag artifacts

### MCP Router (`/api/v1/mcp`)

**MCP Server Management**:
- `GET /` - List MCP servers
- `POST /` - Create server config
- `GET /{server_name}` - Get server details
- `PUT /{server_name}` - Update server
- `DELETE /{server_name}` - Delete server

**Server Operations**:
- `POST /{server_name}/deploy` - Deploy server
- `POST /{server_name}/test` - Test connection
- `GET /{server_name}/status` - Get server status

### Context Entities Router (`/api/v1/context-entities`)

**Entity Management**:
- `GET /` - List context entities
- `POST /` - Create entity
- `GET /{entity_id}` - Get entity details
- `PUT /{entity_id}` - Update entity
- `DELETE /{entity_id}` - Delete entity

**Deployment**:
- `POST /{entity_id}/deploy` - Deploy to project
- `GET /{entity_id}/deployments` - Get deployment history

### Project Templates Router (`/api/v1/project-templates`)

**Template Management**:
- `GET /` - List templates
- `GET /{template_id}` - Get template details
- `POST /{template_id}/deploy` - Deploy template

### Tags Router (`/api/v1/tags`)

**Tag Operations**:
- `GET /` - List all tags
- `GET /stats` - Tag statistics
- `POST /bulk-assign` - Bulk assign tags

### Bundles Router (`/api/v1/bundles`)

**Bundle Management**:
- `GET /` - List bundles
- `POST /` - Create bundle
- `GET /{bundle_id}` - Get bundle
- `DELETE /{bundle_id}` - Delete bundle

**Bundle Operations**:
- `POST /{bundle_id}/export` - Export bundle
- `POST /{bundle_id}/share` - Generate share link

### Analytics Router (`/api/v1/analytics`)

**Analytics Data**:
- `GET /usage` - Usage statistics
- `GET /deployments` - Deployment statistics
- `GET /artifacts/trending` - Trending artifacts
- `GET /tags/metrics` - Tag metrics
- `GET /collections/stats` - Collection statistics

### Health Router (`/health`)

**Health Checks**:
- `GET /` - Basic health check
- `GET /ready` - Readiness probe
- `GET /live` - Liveness probe

---

## Summary Statistics

**Total Pages**: 14 main pages + 8 sub-pages = 22 total page routes

**Total Modals/Dialogs**: 40+ modal implementations

**Total Reusable Components**: 100+ components

**Total API Endpoints**: 150+ endpoints across 15 routers

**Supported Artifact Types**: 5 (Skill, Command, Agent, MCP, Hook)

**Artifact States**: 6 sync statuses (Synced, Modified, Outdated, Conflict, Error, Unknown)

**Scopes**: 2 (User/Global, Local/Project)

**Filter Dimensions**: 8+ (Type, Status, Scope, Tags, Search, etc.)

**View Modes**: 3+ (Grid, List, Grouped)

---

## Key UI Patterns

### Data Display Patterns

1. **Infinite Scroll Pagination**
   - Used in: Collection, Deployments, Marketplace
   - Threshold: 200px from bottom
   - Load size: 20 items per page

2. **Cursor-Based Pagination**
   - Used in: Context Entities, Templates
   - Base64 encoded cursors
   - Next/Previous navigation

3. **Grid Layouts**
   - Primary: 3-column responsive grid
   - Tablet: 2-column
   - Mobile: 1-column
   - Gaps: 16px (Tailwind gap-4)

4. **Table Layouts**
   - Sortable columns
   - Inline actions
   - Row hovering/selection

### Interaction Patterns

1. **Action Menus**
   - Dropdown menu per card/row
   - Common actions: Edit, Delete, Deploy, Sync
   - Overflow prevention

2. **Quick Action Buttons**
   - Primary action: Deploy, Install, Add
   - Secondary: Edit, Details
   - Tertiary: More (menu)

3. **Multi-Step Wizards**
   - Progress indicator
   - Next/Back/Cancel buttons
   - Step validation
   - Confirmation review

4. **State Indicators**
   - Status badges with colors
   - Loading spinners
   - Progress bars
   - Empty states

### Modal Patterns

1. **Confirmation Dialogs**
   - Title, description, action
   - Cancel and confirm buttons
   - Danger confirmation for destructive actions

2. **Detail Modals**
   - Tabs for sections (Info, History, Files, etc.)
   - Scrollable content
   - Close button

3. **Form Dialogs**
   - Input fields
   - Validation messages
   - Submit and cancel buttons

4. **Wizard Modals**
   - Multi-step with progress
   - Step indicators
   - Navigation buttons

---

**End of Feature Catalog**
