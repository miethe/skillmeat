# SkillMeat - Complete Feature Index

**Date**: 2026-02-06 | **Status**: Comprehensive Catalog Complete | **Scope**: Full Web UI

## Executive Summary

SkillMeat is a personal collection manager for Claude Code artifacts (Skills, Commands, Agents, MCP servers, Hooks) with marketplace integration, deployment tracking, and project management.

**Total Inventory**:
- **23 Pages**: Core features + sub-routes
- **40+ Modals**: CRUD operations and workflows
- **100+ Components**: UI building blocks
- **150+ API Endpoints**: Full backend coverage
- **5 Artifact Types**: Skill, Command, Agent, MCP, Hook
- **8+ Filter Dimensions**: Type, Status, Scope, Tags, Search, etc.

---

## Feature Matrix

### Navigation Structure

```
Root (/)
├── Dashboard              Main landing, analytics overview
├── Collection            Browse & manage artifacts
│   └── Collections selector
│   └── Artifact grid/list/grouped
│   └── Tag filtering
├── Manage                Entity management by type
│   └── Skill/Command/Agent/MCP/Hook tabs
│   └── Unified detail modal
├── Projects              Project registry & deployments
│   ├── List with summary
│   ├── [id]/                Detail view
│   │   ├── page           Project info
│   │   ├── settings/      Configuration
│   │   └── manage/        Deployment sync
│   │   └── memory/        Memory inbox + context modules
│   └── Outdated artifacts alert
├── Deployments           Deployment dashboard
│   └── Flat/Grouped views
│   └── Status & type filters
├── Marketplace           Bundle marketplace
│   ├── Browse listings
│   ├── Statistics
│   ├── sources/
│   │   ├── page          GitHub sources list
│   │   └── [id]/         Semantic tree viewer
│   ├── [listing_id]/     Listing detail
│   └── publish/          Publish wizard
├── Groups                Group-based browsing
├── Context Entities      Project context config
├── Templates             Quick setup templates
├── MCP Servers           Protocol server management
├── Settings              App configuration
└── Sharing               Bundle export/import
```

---

## Complete Page Inventory

### Collection Management (1 page)

**Collection (/collection)**
- Grid/List/Grouped views
- Infinite scroll (20 items)
- Search full-text (name, desc, tags)
- Filters: Type, Status, Scope
- Sort: Confidence, Name, Date, Usage
- Tag filter with URL sync (?tags=)
- View toggles: Grid, List, Grouped
- Modals: Detail, Create, Edit, Move, Group, Delete, Params
- Infinite scroll trigger: 200px threshold

---

### Entity Management (2 pages)

**Manage (/manage)**
- Type tabs: Skill/Command/Agent/MCP/Hook
- View modes: Grid, List
- Search and filter
- Detail panel with tabs
- Modals: Add, Detail, Form, Delete, File ops, Merge

**Groups (/groups)**
- Collection selector
- Group selector
- Grid display
- Same artifact interactions as Collection

---

### Project Management (4 pages)

**Projects (/projects)**
- Project list with metrics
- Create project button
- Cache toolbar (stale indicator)
- Outdated artifacts alert
- Quick detail dialog
- Modals: Create, Detail, Update available

**Projects Detail (/projects/[id])**
- Project info
- Deployment history
- Configuration
- Status information

**Projects Manage (/projects/[id]/manage)**
- Pull from collection
- Deploy from collection
- Sync status
- Drift detection
- Modals: Pull/Deploy dialogs

**Projects Memory (/projects/[id]/memory)**
- Memory Inbox triage interface
- Type/status/confidence/search filters
- Keyboard-first review shortcuts
- Lifecycle actions: promote, deprecate, merge
- Context Modules tab with selector-based composition
- Context pack preview and generation

---

### Deployment Tracking (1 page)

**Deployments (/deployments)**
- Summary stats cards
- Status/Type filtering
- Search filter (300ms debounce)
- View modes: Flat, Grouped by project
- Deployment cards with status
- Last deployed timestamps
- Action menus
- Refresh capability

---

### Marketplace (4 pages + sub-pages)

**Marketplace (/marketplace)**
- Listing grid (3-col responsive)
- Stats widget
- Broker/Category/Rating filters
- Search input
- Load more pagination
- Install dialog (strategy select)
- Listing cards with action buttons

**Marketplace Sources (/marketplace/sources)**
- Add source button
- Search mode toggle: Sources | Artifacts
- Filter bar: Type, Trust level, Tags
- Source cards with actions
- Artifact search results (FTS5)
- Modals: Add, Edit, Delete, Rescan, Catalog detail

**Marketplace Sources Detail (/marketplace/sources/[id])**
- Semantic tree (left/center)
  - Folder hierarchy
  - Collapsible/expandable
  - Click to select
- Detail pane (right)
  - Folder info
  - README markdown
  - Subfolder cards
  - Artifact type sections
  - Excluded items list
- Toolbar: Back, Search, Refresh, Info
- Modals: Folder detail, Artifact detail, Exclude, Bulk tag, Auto-tags

**Marketplace Listing Detail (/marketplace/[listing_id])**
- Listing full details
- Bundle contents
- Installation guide
- Install button
- Related listings

**Marketplace Publish (/marketplace/publish)**
- Multi-step wizard (5 steps)
- Progress indicator
- Artifact selector
- Bundle config form
- Broker selection
- Review and publish
- Success confirmation

---

### Configuration & Context (3 pages)

**Context Entities (/context-entities)**
- Filter bar: Type, Status, Search
- Entity cards
- Create button
- Detail modal
- Editor modal
- Deploy to project dialog
- Delete confirmation
- Cursor pagination

**Templates (/templates)**
- Search input
- Template cards
- Deploy button per card
- Detail modal (full info)
- Deploy wizard (multi-step)
- Cursor pagination

**MCP Servers (/mcp)**
- Server list
- Add server button
- Server card for each
- Error state handling
- Modals: Server form with env vars editor
- Click to navigate to [name]

**MCP Server Detail (/mcp/[name])**
- Server information
- Configuration display
- Environment variables
- Deploy/Edit/Delete options
- Connection status

---

### App Configuration (2 pages)

**Settings (/settings)**
- General settings card
- API configuration card
- GitHub settings component
- Token management
- Connection status

**Sharing (/sharing)**
- Bundle list
- Bundle preview
- Export dialog (format selection)
- Import dialog (file upload)
- Permission management
- Share link generator

---

### Dashboard (1 page)

**Dashboard (/)**
- Analytics grid
- Stats cards
  - Total artifacts
  - Total projects
  - Active deployments
  - Last sync
- Usage trends chart
- Tag metrics widget
- Top artifacts widget
- Live updates toggle

---

## Complete Modal Inventory

### Collection Domain (7 modals)

1. **Create Collection Dialog**: Name, description, default settings
2. **Edit Collection Dialog**: Modify metadata, delete option
3. **Move/Copy Dialog**: Select destination, operation type
4. **Add to Group Dialog**: Select group, assign artifact
5. **Manage Groups Dialog**: Create, edit, delete groups
6. **Copy Group Dialog**: Clone group configuration
7. **Deployment Dialog**: Select project, schedule options

---

### Entity Domain (10 modals)

1. **Unified Entity Modal**: Tabs - Info, Content, Files, History, Sync, Deployment
2. **Entity Detail Modal**: Read-only preview
3. **Entity Form Modal**: Edit entity properties
4. **Entity Deletion Dialog**: Confirm removal
5. **File Creation Dialog**: Create new file in artifact
6. **File Deletion Dialog**: Remove file
7. **Merge Workflow Dialog**: Multi-step merge with strategy selection
8. **Rollback Dialog**: Select version to revert
9. **Unsaved Changes Dialog**: Confirm discard before navigation
10. **Artifact Linking Dialog**: Link related artifacts

---

### Marketplace Domain (10 modals)

1. **Add Source Modal**: GitHub repo URL + config
2. **Edit Source Modal**: Modify source settings
3. **Delete Source Dialog**: Confirm removal
4. **Rescan Updates Dialog**: Review new/updated artifacts
5. **Install Dialog**: Select merge/fork/skip strategy
6. **Publish Wizard Modal**: Multi-step (artifacts → config → broker → review → publish)
7. **Exclude Artifact Dialog**: Hide from import
8. **Bulk Tag Dialog**: Apply tags to multiple items
9. **Auto Tags Dialog**: Generate tags with preview
10. **Catalog Entry Modal**: Artifact detail in catalog

---

### Project Domain (5 modals)

1. **Create Project Dialog**: Project name, path
2. **Edit Project Dialog**: Modify settings
3. **Delete Project Dialog**: Confirm removal
4. **Project Detail Dialog**: Quick view with metrics
5. **Update Available Modal**: Show outdated artifacts with update info

---

### Other Domains (8 modals)

1. **Context Entity Editor**: Create/edit entities
2. **Deploy to Project Dialog**: Select target project
3. **Template Deploy Wizard**: Multi-step template deployment
4. **Rating Dialog**: Submit quality rating
5. **MCP Server Form**: Add server with env vars
6. **Export Bundle Dialog**: Select format, download
7. **Import Bundle Dialog**: Upload and import
8. **Directory Map Modal**: Map GitHub directory structure

---

## Component Hierarchy

### Top-Level Layout (2 components)

- **Header**: Logo, navigation, user menu
- **Navigation**: Sidebar with main routes

### Collection Domain (11 components)

- CollectionHeader
- CollectionToolbar
- ArtifactGrid (3-col responsive)
- ArtifactList (tabular)
- GroupedArtifactView
- CollectionSwitcher
- ConflictResolver
- SyncDialog
- VersionTree
- CollectionBadgeStack
- GroupBadgeRow

### Entity Domain (15 components)

- EntityCard, EntityList, EntityRow
- EntityForm, EntityActions
- ContentPane, FileTree
- DiffViewer (unified and colored)
- MergeWorkflow, MergePreviewView
- MergeConflictResolver
- FrontmatterDisplay
- LinkedArtifactsSection
- EntityLifecycleProvider

### Marketplace Components (18 components)

- MarketplaceListingCard, MarketplaceListingDetail
- MarketplaceFilters, MarketplaceStats
- MarketplaceInstallDialog, MarketplacePublishWizard
- SourceCard, SourceFilterBar
- SemanticTree, FolderDetailPane
- SubfolderCard, ArtifactTypeSection
- SourceToolbar
- ExcludedList, CatalogList, CatalogTabs
- ArtifactSearchResults
- CatalogEntryModal

### Dashboard Components (5 components)

- AnalyticsGrid
- StatsCards
- UsageTrendsWidget
- TagMetricsWidget
- TopArtifactsWidget

### MCP Components (5 components)

- MCPServerList, MCPServerCard
- MCPServerForm
- MCPEnvEditor
- MCPDeployButton

### Context Components (4 components)

- ContextEntityCard, ContextEntityDetail
- ContextEntityEditor
- ContextEntityFilters

### Template Components (3 components)

- TemplateCard, TemplateDetail
- TemplateDeployWizard

### Shared Components (8 components)

- UnifiedCard, UnifiedCardActions
- CollectionArtifactModal, ProjectArtifactModal
- GroupFilterSelect, TagEditor
- ProgressIndicator
- CacheFreshnessIndicator

### UI Primitives (24+ from shadcn/ui)

- Button, Card, Dialog, Input, Label
- Badge, Alert, Tabs, Table
- Dropdown Menu, Popover, Select
- Accordion, Collapsible, Checkbox
- Radio Group, Textarea, Tooltip
- Skeleton, Switch, Progress, etc.

---

## API Endpoint Organization

### By Router (15 routers)

1. **Artifacts** (50+ endpoints)
   - CRUD, metadata, tags, versions, files, deployment, sync, linking, discovery

2. **Collections** (12 endpoints - deprecated)
   - Read-only endpoints, migration to user-collections

3. **User Collections** (20+ endpoints)
   - Full CRUD, artifacts, groups

4. **Groups** (15+ endpoints)
   - Management, artifact assignment

5. **Projects** (15+ endpoints)
   - CRUD, deployments, config, status

6. **Deployments** (20+ endpoints)
   - CRUD, sync, rollback, diff, refresh

7. **Marketplace** (25+ endpoints)
   - Listings, installation, publishing, brokers

8. **Marketplace Catalog** (10+ endpoints)
   - Catalog CRUD, search, source-based queries

9. **Marketplace Sources** (20+ endpoints)
   - Source CRUD, scan, tree, catalog, exclusions, tagging

10. **MCP** (10+ endpoints)
    - Server CRUD, deployment, testing

11. **Context Entities** (12+ endpoints)
    - CRUD, deployment

12. **Project Templates** (8+ endpoints)
    - Listing, detail, deployment

13. **Tags** (5+ endpoints)
    - Listing, stats, bulk operations

14. **Bundles** (8+ endpoints)
    - CRUD, export, share

15. **Analytics** (10+ endpoints)
    - Usage, deployments, trending, tags, collections

### By Operation Type

**Read (GET)**: ~70+ endpoints
**Create (POST)**: ~35+ endpoints
**Update (PUT)**: ~20+ endpoints
**Delete (DELETE)**: ~15+ endpoints

---

## Filter & Sort Matrix

### Collection Page

**Filters**:
- Type (6 options: All, Skill, Command, Agent, MCP, Hook)
- Status (6 options: All, Synced, Modified, Outdated, Conflict, Error)
- Scope (3 options: All, User, Local)
- Tags (Multi-select, dynamic)
- Search (Full-text)

**Sort**:
- Confidence (score, desc)
- Name (alphabetical, toggle asc/desc)
- Updated Date (newest, toggle)
- Usage Count (most used, toggle)

**View Modes**: Grid (3-col), List, Grouped

---

### Deployments Page

**Filters**:
- Status (6 options)
- Type (5 options with multi-select)
- Search (artifact name)

**Sort**: By project, by date (implicit)

**View Modes**: Flat, Grouped by project

---

### Marketplace

**Filters**:
- Broker (multi-select)
- Category/Type
- Rating/Popularity
- Date range

**Search**: Full-text on listings

---

### Marketplace Sources

**Search Modes**: Sources, Artifacts (FTS5)

**Filters**:
- Artifact Type
- Trust Level
- Tags (multi-select)

---

## Data Model Summary

### Artifact

```
id, name, type, scope, syncStatus
description, author, license
tags, version, sourceUrl
createdAt, updatedAt
score, usageStats, upstream, collections, aliases
```

### Collection

```
id, name, description
artifacts[], groups[]
createdAt, updatedAt
```

### Group

```
id, collectionId, name
description, color
artifacts[]
createdAt, updatedAt
```

### Deployment

```
id, artifactId, projectId
syncStatus, version
deployedAt, lastSyncAt
```

### Listing

```
listing_id, name, description
brokerId, artifacts[], rating
downloads, publishedAt, updatedAt
```

### ContextEntity

```
id, name, type, content
description, tags
deployments[]
createdAt, updatedAt
```

### MCPServer

```
name, repo, version
description
env_vars, status
```

---

## Statistics & Metrics

| Metric | Count |
|--------|-------|
| **Pages** | 22 (main + sub-routes) |
| **Modals** | 40+ |
| **Components** | 100+ |
| **API Endpoints** | 150+ |
| **Artifact Types** | 5 |
| **Sync States** | 6 |
| **Filter Dimensions** | 8+ |
| **View Modes** | 3+ |
| **Routers** | 15 |
| **UI Primitives** | 24+ |
| **Artifact Type Filters** | 6 |
| **Status Filters** | 6 |
| **Scope Options** | 2-3 |

---

## Technology Stack

**Frontend**:
- Next.js 15 (App Router)
- React 19
- TypeScript
- Radix UI + shadcn/ui
- TanStack Query (React Query)
- Tailwind CSS
- Lucide Icons
- Jest + React Testing Library
- Playwright (E2E)

**Backend**:
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- Python 3.9+

**Key Libraries**:
- OpenAPI/FastAPI for API docs
- Markdown editor components
- Version control/diff viewers
- Graph visualization (versions)

---

## Navigation Patterns

### Primary Navigation

- Sidebar with 12 main routes
- Header with logo and user menu
- Active route highlighting
- Responsive mobile menu (likely)

### Sub-navigation

- URL-driven (Next.js App Router)
- Query parameters for filters (?tags=, ?q=)
- Dynamic routes for detail views ([id], [name])

### Breadcrumbs

- Likely in detail views
- Shows current path in navigation

---

## Common User Workflows

1. **Browse Collection**
   - Navigate to Collection
   - Select view mode (grid/list)
   - Search/filter artifacts
   - Click card for detail
   - View/edit in modal

2. **Deploy Artifact**
   - Collection or Manage page
   - Click artifact
   - Select Deploy from modal
   - Choose project
   - Confirm

3. **Sync from Upstream**
   - Collection → Modified artifacts
   - Click artifact → Sync tab
   - View diff
   - Resolve conflicts
   - Complete sync

4. **Import GitHub Source**
   - Marketplace Sources → Add
   - Enter repo URL
   - Configure settings
   - Scan
   - Review artifacts
   - Import to collection

5. **Manage Projects**
   - Projects page → Create or select
   - View deployments
   - Track status
   - Refresh/sync

---

## Accessibility Considerations

- ARIA labels on icon buttons
- Semantic HTML structure
- Keyboard navigation throughout
- Tab focus management in modals
- Role attributes on custom elements
- Color contrast compliance (WCAG)
- Loading/status announcements

---

## Performance Optimizations

- Infinite scroll (avoid loading all at once)
- Cursor-based pagination (stateless)
- Client-side search debouncing (300ms)
- Component memoization (prevent re-renders)
- LocalStorage for view preferences
- TanStack Query caching
- Lazy loading for modals
- Image optimization

---

## Responsive Design

**Breakpoints**:
- Mobile: < 640px (1 column)
- Tablet: 640-1024px (2 columns)
- Desktop: > 1024px (3 columns)

**Components**:
- Sidebar collapses on mobile
- Modals full-screen on mobile
- Tables horizontal scroll on small screens
- Touch-friendly button sizes (48px min)

---

## Internationalization (i18n)

- Currently English-only
- Strings hardcoded in components
- Opportunity for future i18n integration

---

## Documentation Files

- `CLAUDE.md` - Comprehensive feature catalog with all details
- `FEATURE_CATALOG_SUMMARY.md` - Quick reference guide
- `FEATURE_INDEX.md` - This file, organizational overview

---

**End of Feature Index**

For detailed information on specific features, see:
- **FEATURE_CATALOG.md** - Complete detailed reference (40+ pages)
- **FEATURE_CATALOG_SUMMARY.md** - Quick lookup tables and checklists
