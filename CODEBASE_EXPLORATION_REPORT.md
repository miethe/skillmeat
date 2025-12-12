# SkillMeat Web Application Architecture Exploration Report

**Date**: December 12, 2025
**Project**: SkillMeat - Personal Collection Manager for Claude Code Artifacts
**Focus**: Web Application Architecture, Navigation, Collection/Manage Pages, Entity Management

---

## Executive Summary

SkillMeat is a full-stack artifact management application built with:
- **Frontend**: Next.js 15 (App Router) + React 19 + TypeScript + Radix UI + shadcn
- **Backend**: FastAPI + Pydantic + SQLAlchemy (planned)
- **State Management**: TanStack Query (React Query) + React Context for entity lifecycle
- **UI Pattern**: Unified modal system for entity details with tabs for Overview, Sync/Deploy, History, and Files

The application uses a collection-based architecture where artifacts (Skills, Commands, Agents, MCP Servers, Hooks) are managed globally and deployed to projects locally.

---

## 1. NAVIGATION & SIDEBAR

### Key Files
- **Navigation Component**: `/skillmeat/web/components/navigation.tsx`
- **Header Component**: `/skillmeat/web/components/header.tsx`
- **Root Layout**: `/skillmeat/web/app/layout.tsx`

### Navigation Structure

```typescript
// Navigation items defined in navigation.tsx
const navItems: NavItem[] = [
  { title: 'Dashboard', href: '/', icon: Home },
  { title: 'Manage', href: '/manage', icon: FolderCog },
  { title: 'Collection', href: '/collection', icon: Package },
  { title: 'Projects', href: '/projects', icon: GitBranch },
  { title: 'Marketplace', href: '/marketplace', icon: ShoppingBag,
    subItems: [
      { title: 'Sources', href: '/marketplace/sources', icon: Github }
    ]
  },
  { title: 'Sharing', href: '/sharing', icon: Users },
  { title: 'MCP Servers', href: '/mcp', icon: Database },
  { title: 'Settings', href: '/settings', icon: Settings },
];
```

### Navigation Features
- **Sidebar Width**: 64 units (256px)
- **Active State Detection**: Uses `usePathname()` to highlight current route
- **Nested Navigation**: Marketplace has submenu for Sources
- **Icon Support**: Uses Lucide icons for all menu items
- **Responsive**: Flex layout with proper spacing

### Header Features
- **Sticky positioning** (top-0, z-50)
- **Notification bell** with unread count badge
- **External links**: GitHub and Documentation
- **Notification center** integration via `useNotifications()` hook

### Layout Structure
```
Root Layout (app/layout.tsx)
├── Header component
├── Flex container
│   ├── Navigation sidebar (64 units wide)
│   └── Main content area (flex-1)
└── Providers wrapper (TanStack Query, Toaster, etc.)
```

---

## 2. COLLECTION PAGE (`/collection`)

### Key Files
- **Page Component**: `/skillmeat/web/app/collection/page.tsx`
- **Filters Component**: `/skillmeat/web/components/collection/filters.tsx`
- **Artifact Grid**: `/skillmeat/web/components/collection/artifact-grid.tsx`
- **Artifact List**: `/skillmeat/web/components/collection/artifact-list.tsx`
- **Hook**: `/skillmeat/web/hooks/useArtifacts.ts`

### Page Features

#### Layout
- Page header with title and description
- Collapsible filters section
- View mode toggle (Grid/List)
- Results display with artifact count
- Error state handling

#### View Modes
1. **Grid View**: Card-based layout (default)
2. **List View**: Table-style rows

#### State Management
```typescript
// Page state
const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
const [isDetailOpen, setIsDetailOpen] = useState(false);

// Filter & sort state
const [filters, setFilters] = useState<ArtifactFilters>({});
const [sort, setSort] = useState<ArtifactSort>({
  field: 'name',
  order: 'asc',
});

// Data fetching
const { data, isLoading, error } = useArtifacts(filters, sort);
```

#### Entity Mapping
Artifacts are converted to Entity type for unified modal:
```typescript
function artifactToEntity(artifact: Artifact): Entity {
  // Maps artifact status to entity status
  // Maps artifact properties to entity interface
  // Includes tags, description, version, source, timestamps
}
```

### Component Hierarchy
```
CollectionPage (EntityLifecycleProvider wrapper)
├── Page Header
├── Filters Component
│   └── Filter controls + Sort options
├── Results Header
│   ├── Count display
│   └── View toggle (Grid/List)
├── Error Alert (conditional)
└── View Container
    ├── ArtifactGrid (grid mode)
    │   └── Grid of artifact cards
    └── ArtifactList (list mode)
        └── Table of artifact rows

UnifiedEntityModal (portal)
└── Artifact detail with tabs
```

---

## 3. MANAGE PAGE (`/manage`)

### Key Files
- **Page Component**: `/skillmeat/web/app/manage/page.tsx`
- **Entity Tabs**: `/skillmeat/web/app/manage/components/entity-tabs.tsx`
- **Entity Filters**: `/skillmeat/web/app/manage/components/entity-filters.tsx`
- **Entity List**: `/skillmeat/web/components/entity/entity-list.tsx`
- **Hook**: `/skillmeat/web/hooks/useEntityLifecycle.tsx`

### Page Structure

#### Full-Height Layout
```
ManagePage (EntityLifecycleProvider)
├── Border-top container (h-screen flex flex-col)
│   ├── Header section (border-b)
│   │   ├── Title & description
│   │   └── Controls (Refresh, View toggle, Add New button)
│   │
│   └── Entity Tabs section (flex-1)
│       ├── Tab triggers (skill, command, agent, mcp, hook)
│       └── Tab content (for active entity type)
│           ├── Filters
│           ├── Entity count
│           └── Entity list (grid or list view)
│
├── UnifiedEntityModal (portal)
├── AddEntityDialog (portal)
└── Edit Dialog (portal - conditional)
```

### Key Features

#### Tabs System
Five tabs for entity types:
- Skill
- Command
- Agent
- MCP Server
- Hook

Each tab loads entities of that type via URL param: `?type=skill`

#### Filters
- **Search**: Full-text search across names, descriptions
- **Status**: synced, modified, outdated, conflict
- **Tags**: Multi-select tag filtering (client-side)

#### Actions per Entity
- **Edit**: Open edit form dialog
- **Delete**: With confirmation
- **Deploy**: Opens modal with sync/deploy tab
- **Sync**: Opens modal with sync tab
- **View Diff**: Opens modal with sync tab showing diff viewer
- **Rollback**: Opens modal with history tab

#### Query Interface
```typescript
interface UseEntityLifecycle {
  entities: Entity[];
  isLoading: boolean;
  isRefetching: boolean;
  searchQuery: string;
  statusFilter: EntityStatus | null;
  setTypeFilter: (type: EntityType) => void;
  setStatusFilter: (status: EntityStatus | null) => void;
  setSearchQuery: (query: string) => void;
  deleteEntity: (id: string) => Promise<void>;
  refetch: () => Promise<void>;
}
```

---

## 4. ARTIFACT CARDS & UNIFIED MODAL

### Key Files
- **Unified Modal**: `/skillmeat/web/components/entity/unified-entity-modal.tsx`
- **Entity Card**: `/skillmeat/web/components/entity/entity-card.tsx`
- **Entity Row**: `/skillmeat/web/components/entity/entity-row.tsx`

### Modal Tabs

#### 1. Overview Tab
Displays:
- Entity name, type, icon
- Status badge (synced/modified/outdated/conflict)
- Tags as badges
- Description
- Version information
- Source (GitHub URL or local)
- Deployment info (when deployed, by whom)
- Last modified timestamp

#### 2. Sync/Deploy Tab
Features:
- **Status Cards**:
  - Collection version
  - Project version (if deployed)
  - Upstream version (if tracking)

- **Comparison Selector**: Choose which versions to compare
- **Diff Viewer**: Side-by-side diff display
- **Action Buttons**: Sync, Deploy, Pull, Push

#### 3. History Tab
Displays:
- Timeline of events (deploy, sync, rollback)
- Event type and direction
- Files changed count
- Timestamp
- User who performed action
- Rollback button per entry

#### 4. Files Tab
Features:
- **File Tree**: Hierarchical view of entity files
- **File Preview**: Selected file content in read-only pane
- **File Actions**:
  - Create new file
  - Delete file
  - Update content (with save)
- **Content Pane**: Monaco editor integration for code files

### Modal Props
```typescript
interface UnifiedEntityModalProps {
  entity: Entity | null;
  open: boolean;
  onClose: () => void;
}
```

### Modal State
```typescript
// Inside modal component
const [activeTab, setActiveTab] = useState('overview');
const [selectedFile, setSelectedFile] = useState<string | null>(null);
const [editingFile, setEditingFile] = useState<string | null>(null);
const [comparisonMode, setComparisonMode] = useState<'upstream' | 'project'>();
const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
```

### Action Menu (Card Right-Click)
- Edit
- Delete
- Deploy to Project
- Sync from Source
- View Diff
- Rollback
- Copy ID
- Copy Source

---

## 5. API ENDPOINTS & BACKEND

### API Base URL Pattern
```
/api/v1/{resource}
```

### Key Routers

#### Artifacts Router (`/api/v1/artifacts`)
```
GET    /artifacts              # List all artifacts
POST   /artifacts              # Create artifact
GET    /artifacts/{id}         # Get artifact details
PUT    /artifacts/{id}         # Update artifact
DELETE /artifacts/{id}         # Delete artifact
GET    /artifacts/{id}/diff    # Get diff between versions
GET    /artifacts/{id}/files   # List artifact files
GET    /artifacts/{id}/files/{path}  # Get file content
POST   /artifacts/{id}/deploy  # Deploy to project
POST   /artifacts/{id}/sync    # Sync from source
POST   /artifacts/{id}/rollback # Rollback to version
```

#### Collections Router (`/api/v1/collections`)
```
GET    /collections            # List all collections
GET    /collections/{id}       # Get collection details
GET    /collections/{id}/artifacts  # List artifacts in collection
```

#### Deployments Router (`/api/v1/deployments`)
```
GET    /deployments            # List all deployments
GET    /deployments/{id}       # Get deployment details
POST   /deployments            # Create deployment
DELETE /deployments/{id}       # Delete deployment
```

#### Marketplace Sources Router (`/api/v1/marketplace/sources`)
```
GET    /sources                # List GitHub sources
POST   /sources                # Create new source
GET    /sources/{id}           # Get source details
PATCH  /sources/{id}           # Update source (description, notes)
DELETE /sources/{id}           # Delete source
POST   /sources/{id}/rescan    # Trigger rescan
GET    /sources/{id}/artifacts # List artifacts from source
POST   /sources/{id}/import    # Import artifacts to collection
```

### Request/Response Types

#### Artifact Response
```typescript
interface ArtifactResponse {
  id: string;
  name: string;
  type: ArtifactType;
  source: string;
  version?: string;
  aliases?: string[];
  metadata?: ArtifactMetadata;
  upstream?: ArtifactUpstreamStatus;
  added: string;  // ISO timestamp
  updated: string;  // ISO timestamp
}
```

#### Collection Response
```typescript
interface CollectionResponse {
  id: string;
  name: string;
  description?: string;
  artifacts_count: number;
  deployments_count: number;
  created_at: string;
  updated_at: string;
}
```

#### Source Response (Marketplace)
```typescript
interface SourceResponse {
  id: string;
  github_url: string;
  owner: string;
  repo: string;
  description?: string;
  notes?: string;
  artifacts_found: number;
  last_scanned: string | null;
  status: 'active' | 'scanning' | 'error';
  error_message?: string;
  created_at: string;
  updated_at: string;
}
```

### Request Types

#### UpdateSourceRequest (Marketplace)
```typescript
interface UpdateSourceRequest {
  description?: string;  # Optional description
  notes?: string;        # Optional notes
}
```

---

## 6. DATABASE MODELS (SQLAlchemy)

### Core Models Location
Primary location for models: `/skillmeat/api/schemas/` (Pydantic models for API)
ORM models in progress: `/skillmeat/cache/models.py`

### Marketplace Models (SQLAlchemy)
```python
class MarketplaceSource(Base):
    __tablename__ = "marketplace_sources"

    id: str (Primary Key)
    github_url: str
    owner: str
    repo: str
    description: str | None
    notes: str | None
    artifacts_found: int
    last_scanned: datetime | None
    status: str (active|scanning|error)
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    # Relationships
    artifacts: List[MarketplaceCatalogEntry]

class MarketplaceCatalogEntry(Base):
    __tablename__ = "marketplace_catalog"

    id: str (Primary Key)
    source_id: str (Foreign Key)
    name: str
    type: str (skill|command|agent|mcp|hook)
    path: str
    description: str | None
    tags: List[str]
    metadata: dict
    created_at: datetime
    updated_at: datetime
```

### Cache Layer
Location: `/skillmeat/cache/models.py` and `/skillmeat/cache/repositories.py`

**Repositories**:
- `MarketplaceSourceRepository`: CRUD for sources
- `MarketplaceCatalogRepository`: CRUD for catalog entries
- `MarketplaceTransactionHandler`: Atomic updates

---

## 7. CACHING MECHANISM

### Frontend Caching (TanStack Query)

#### Query Configuration
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,      # 5 minutes
      cacheTime: 10 * 60 * 1000,     # 10 minutes
      refetchOnWindowFocus: false,    # Don't refetch on tab switch
      retry: 1,                        # Retry once on failure
    },
  },
});
```

#### Query Keys Pattern
```typescript
const artifactKeys = {
  all: ['artifacts'] as const,
  lists: () => [...artifactKeys.all, 'list'] as const,
  list: (filters, sort) => [...artifactKeys.lists(), filters, sort] as const,
  details: () => [...artifactKeys.all, 'detail'] as const,
  detail: (id) => [...artifactKeys.details(), id] as const,
};
```

#### Cache Invalidation
```typescript
// On successful mutation
queryClient.invalidateQueries({ queryKey: artifactKeys.all });
```

### Backend Caching (Python)

#### MetadataCache
Location: `/skillmeat/core/cache.py`
- In-memory cache for artifact metadata
- GitHub metadata extraction caching
- Configurable TTL

#### File System Cache
Location: `/skillmeat/cache/` directory
- Persistent cache for scanned artifacts
- Repository data storage
- SQLite database for relational data

### Local Cache Hooks

#### useProjectCache
- Caches project-specific artifact state
- Location: `/skillmeat/web/hooks/useProjectCache.ts`

#### useCacheRefresh
- Manual cache refresh trigger
- Location: `/skillmeat/web/hooks/useCacheRefresh.ts`

#### useCacheStatus
- Monitor cache freshness
- Location: `/skillmeat/web/hooks/useCacheStatus.ts`

---

## 8. EXISTING PATTERNS

### Collection/Group Management

#### Entity Types (5 supported)
```typescript
export type EntityType = 'skill' | 'command' | 'agent' | 'mcp' | 'hook';
```

#### Entity Type Configuration
```typescript
const ENTITY_TYPES: Record<EntityType, EntityTypeConfig> = {
  skill: {
    type: 'skill',
    label: 'Skill',
    pluralLabel: 'Skills',
    icon: 'Sparkles',
    color: 'text-purple-500',
    requiredFile: 'SKILL.md',
    formSchema: { /* fields */ }
  },
  // ... command, agent, mcp, hook
};
```

### Filtering & Sorting

#### Collection Page Filters
```typescript
interface ArtifactFilters {
  type?: ArtifactType | 'all';
  status?: ArtifactStatus | 'all';
  scope?: ArtifactScope | 'all';
  search?: string;
}

interface ArtifactSort {
  field: 'name' | 'updatedAt' | 'usageCount';
  order: 'asc' | 'desc';
}
```

#### Manage Page Filters
```typescript
interface EntityLifecycleFilters {
  typeFilter: EntityType | null;
  statusFilter: EntityStatus | null;
  searchQuery: string;
  tagFilter?: string[];  // Client-side filtering
}
```

### View Modes
Both Collection and Manage pages support:
1. **Grid View**: Card-based layout with visual prominence
2. **List View**: Table layout for quick scanning

### Modal Tabs Pattern
Unified modal provides contextual tabs based on entity state:
1. **Overview**: Basic metadata
2. **Sync/Deploy**: Version management
3. **History**: Event timeline
4. **Files**: File browser and editor

### Status States
```typescript
export type EntityStatus = 'synced' | 'modified' | 'outdated' | 'conflict';

// Visual indicators
synced:   CheckCircle2 + green badge
modified: AlertCircle + yellow badge
outdated: ArrowUp + orange badge
conflict: GitMerge + red badge
```

### Artifact Status (Collection)
```typescript
export type ArtifactStatus = 'active' | 'outdated' | 'conflict' | 'error';
```

---

## 9. CURRENT MODAL TABS & CARD MENU

### Modal Tab Structure
```
UnifiedEntityModal (Portal)
├── Dialog Container
├── Header
│   ├── Entity name
│   ├── Type badge
│   ├── Status indicator
│   └── Close button (X)
│
├── Tabs Container
│   ├── Overview Tab
│   │   ├── Metadata section
│   │   ├── Status cards
│   │   ├── Tags
│   │   └── Timestamps
│   │
│   ├── Sync/Deploy Tab
│   │   ├── Version comparison
│   │   ├── Diff viewer
│   │   └── Action buttons
│   │
│   ├── History Tab
│   │   ├── Timeline
│   │   └── Event entries
│   │
│   └── Files Tab
│       ├── File tree (left)
│       └── File preview (right)
│
└── Footer Actions
    └── Context-dependent buttons
```

### Card Actions Menu
Accessed via:
- Right-click context menu
- Card menu button (three dots)
- Entity row menu

**Available Actions**:
- ✏️ Edit entity metadata
- 🗑️ Delete entity
- 🚀 Deploy to project
- 🔄 Sync from source
- 👀 View diff
- ⏮️ Rollback to version
- 📋 Copy ID
- 🔗 Copy source
- 📌 Add to favorites (future)
- 🏷️ Edit tags (future)

---

## 10. KEY FILES REFERENCE

### Web Frontend Structure
```
skillmeat/web/
├── app/
│   ├── layout.tsx (Root layout with Header + Navigation)
│   ├── page.tsx (Dashboard)
│   ├── collection/ (Collection browser)
│   │   └── page.tsx
│   ├── manage/ (Entity management)
│   │   ├── page.tsx
│   │   ├── layout.tsx
│   │   └── components/
│   │       ├── entity-tabs.tsx
│   │       ├── entity-filters.tsx
│   │       └── entity-detail-panel.tsx
│   ├── projects/ (Project management)
│   ├── marketplace/ (Claude marketplace)
│   └── mcp/ (MCP server management)
│
├── components/
│   ├── navigation.tsx (Sidebar)
│   ├── header.tsx (Top navigation)
│   ├── entity/
│   │   ├── unified-entity-modal.tsx (Main modal)
│   │   ├── entity-card.tsx (Grid card)
│   │   ├── entity-row.tsx (List row)
│   │   ├── entity-list.tsx (List container)
│   │   ├── diff-viewer.tsx
│   │   ├── file-tree.tsx
│   │   ├── content-pane.tsx
│   │   ├── rollback-dialog.tsx
│   │   ├── merge-workflow.tsx
│   │   └── EntityLifecycleProvider.tsx
│   ├── collection/
│   │   ├── filters.tsx
│   │   ├── artifact-grid.tsx
│   │   ├── artifact-list.tsx
│   │   ├── artifact-detail.tsx
│   │   └── deploy-dialog.tsx
│   ├── marketplace/
│   │   ├── add-source-modal.tsx
│   │   ├── edit-source-modal.tsx
│   │   ├── delete-source-dialog.tsx
│   │   └── source-card.tsx
│   └── ui/ (shadcn components)
│
├── hooks/
│   ├── useArtifacts.ts (Collection data)
│   ├── useEntityLifecycle.tsx (Entity management)
│   ├── useMarketplaceSources.ts
│   ├── useDeploy.ts
│   ├── useSync.ts
│   ├── useCacheRefresh.ts
│   └── (15+ other specialized hooks)
│
├── lib/
│   ├── api.ts (API client wrapper)
│   └── utils.ts (Utility functions)
│
├── types/
│   ├── entity.ts (Entity types + config)
│   ├── artifact.ts (Artifact types)
│   ├── marketplace.ts
│   └── (other types)
│
└── sdk/
    └── (Generated OpenAPI client)
```

### Backend API Structure
```
skillmeat/api/
├── server.py (FastAPI app)
├── config.py (Settings)
├── dependencies.py (DI)
├── openapi.py
├── project_registry.py
│
├── routers/
│   ├── artifacts.py
│   ├── collections.py
│   ├── deployments.py
│   ├── projects.py
│   ├── marketplace.py
│   ├── marketplace_sources.py
│   ├── mcp.py
│   └── bundles.py
│
├── schemas/
│   ├── artifacts.py
│   ├── collections.py
│   ├── marketplace.py
│   ├── deployments.py
│   ├── common.py
│   └── (other schemas)
│
├── middleware/
│   ├── auth.py
│   ├── rate_limit.py
│   └── observability.py
│
└── tests/
    ├── test_artifacts_routes.py
    └── (other tests)
```

---

## 11. TECHNOLOGY STACK

### Frontend
- **Framework**: Next.js 15 (App Router)
- **UI Library**: React 19
- **Language**: TypeScript
- **UI Components**: shadcn/ui + Radix UI
- **Styling**: Tailwind CSS
- **State Management**: TanStack Query (React Query) + React Context
- **Icons**: Lucide React
- **Form Handling**: React Hook Form (used in some places)
- **Testing**: Jest + React Testing Library + Playwright

### Backend
- **Framework**: FastAPI
- **Language**: Python 3.9+
- **ORM** (planned): SQLAlchemy
- **Database**: File-based (collection storage) + SQLite (cache)
- **Validation**: Pydantic
- **Async**: AsyncIO
- **Migrations** (planned): Alembic

### DevOps
- **Package Manager**: pnpm (frontend)
- **Docker**: Support planned
- **GitHub Integration**: Webhook-based scanning

---

## 12. KEY ARCHITECTURAL DECISIONS

### 1. Unified Entity Modal
Instead of separate modals per entity type, all types (Skill, Command, Agent, MCP, Hook) use the same `UnifiedEntityModal` component with context-specific tabs and behaviors.

### 2. Collection vs Project Scope
- **Collection Scope**: Global artifacts (~/.skillmeat/collection)
- **Project Scope**: Project-local artifacts (./.claude/artifacts)
- **EntityLifecycleProvider**: Abstracts both modes with `mode` prop

### 3. File-Based Storage (Current)
Currently uses filesystem + TOML manifests. SQLAlchemy migration in progress for:
- Marketplace sources (already using SQLite)
- Artifact metadata
- Deployment tracking

### 4. Mock Fallback Pattern
All API hooks include mock fallback behavior:
```typescript
if (USE_MOCKS) {
  console.warn('[hook] API failed, using mock fallback', error);
  return mockData;
}
```

### 5. Query Key Pattern
Hierarchical query keys for TanStack Query:
- `['artifacts']` - Root
- `['artifacts', 'list']` - All list operations
- `['artifacts', 'list', filters, sort]` - Specific filtered list
- `['artifacts', 'detail', id]` - Specific artifact

### 6. Tab-Based Details
Instead of separate pages for each detail view (overview, sync, history), use a single modal with tabs. Reduces state management complexity and provides consistent UX.

---

## 13. CURRENT DATA FLOW

### Collection Page Flow
```
CollectionPage
├── useArtifacts(filters, sort) [TanStack Query]
│   └── fetchArtifactsFromApi() → /api/v1/artifacts
│       └── apiRequest<ApiArtifactListResponse>()
│
├── Filter/sort state
│   └── filterAndSortArtifacts(data, filters, sort)
│
└── Select artifact
    └── artifactToEntity()
        └── Open UnifiedEntityModal
```

### Manage Page Flow
```
ManagePage
├── EntityLifecycleProvider (mode="collection")
│   └── useEntityLifecycle()
│       └── Fetch entities from API
│
├── Select entity type (URL param)
│   └── setTypeFilter()
│
├── Apply search/status filters
│   └── Filter entities client-side
│
└── Select entity
    └── Open UnifiedEntityModal
```

### Modal Interaction Flow
```
UnifiedEntityModal (open=true, entity selected)
├── Overview Tab (default)
│   └── Display metadata
│
├── Sync/Deploy Tab
│   ├── Fetch diff: /api/v1/artifacts/{id}/diff
│   ├── Show comparison
│   └── Deploy/Sync buttons → trigger mutations
│
├── History Tab
│   └── Generate mock history (future: fetch from API)
│
└── Files Tab
    ├── Fetch files: /api/v1/artifacts/{id}/files
    ├── Show tree
    ├── Select file → Fetch: /api/v1/artifacts/{id}/files/{path}
    └── Edit/Save file → PUT request
```

---

## 14. MISSING/PLANNED FEATURES

Based on code inspection, the following are planned but not fully implemented:

1. **SQLAlchemy ORM Models** - In progress in `/skillmeat/cache/models.py`
2. **Artifact Groups** - Mentioned in CLAUDE.md but not implemented
3. **Advanced Search** - Only basic text search currently
4. **Favorites/Bookmarks** - UI slots but no backend
5. **Tag Editing** - Display only, no edit capability from modal
6. **Rollback Timestamps** - History generated from metadata, not from persistent history
7. **Multi-language Support** - English only
8. **Dark Mode Persistence** - Dark mode CSS exists but no preference saving
9. **Analytics Dashboard** - Hooks exist but limited backend integration
10. **Collaborative Features** - Single-user application currently

---

## 15. INTEGRATION POINTS FOR NEW FEATURES

### Adding a New Modal Tab
1. Add tab trigger to `UnifiedEntityModal` tabs list
2. Create component for tab content
3. Add case to `getTabContent()` or switch statement
4. Add data fetching hook if needed
5. Wire up actions/mutations

### Adding a New Filter
1. Extend `ArtifactFilters` or `EntityFilters` interface
2. Add filter control in `Filters` or `EntityFilters` component
3. Update filtering logic in hook
4. Add filter badge display in header

### Adding Marketplace Source Feature
1. **Backend**: Add endpoint to `/api/v1/marketplace/sources`
2. **Schema**: Add Pydantic model in `/skillmeat/api/schemas/marketplace.py`
3. **Database**: Update `MarketplaceSource` model in `/skillmeat/cache/models.py`
4. **API Hook**: Create hook in `/skillmeat/web/hooks/useMarketplaceSources.ts`
5. **UI Component**: Add modal or dialog in `/skillmeat/web/components/marketplace/`

### Adding a Deployment Strategy
1. Create component in `/skillmeat/web/components/entity/`
2. Add mutation hook in `/skillmeat/web/hooks/useDeploy.ts`
3. Add API endpoint in `/skillmeat/api/routers/deployments.py`
4. Wire to "Deploy to Project" action in modal

---

## 16. RECOMMENDATIONS FOR ENHANCEMENT

### 1. Collections Navigation Enhancement
- **Current**: All artifacts in one collection view
- **Proposal**: Add hierarchical collections/groups
  - User can organize artifacts by category (Frontend, Backend, DevOps, etc.)
  - Implement as folder-like structure in sidebar
  - Add breadcrumb in collection page header

### 2. Smart Grouping in Manage Page
- **Group by**: Type, Status, Source, Last Updated
- **Add collapsible group headers** showing counts
- **Preserve group state** in localStorage

### 3. Enhanced Filtering
- **Save filter presets** (e.g., "My Outdated Artifacts")
- **Combine multiple filters** with AND/OR logic
- **Date range filtering** for Last Updated

### 4. Collections as First-Class Feature
- **Create collections UI** to organize artifacts
- **Add collection cards** in dashboard
- **Assign artifacts to collections**
- **Share collections as bundles**

### 5. Entity Search Autocomplete
- **As-you-type suggestions** based on:
  - Entity names
  - Aliases
  - Tags
  - Descriptions
- **Recent searches**
- **Search history**

### 6. Deployment to Collections
- **Current**: Deploy artifact from collection to project
- **Proposed**: Deploy entire collection to project with one click
- **Add deployment profiles** (which artifacts to deploy)

---

## SUMMARY

The SkillMeat web application has a well-structured architecture with:
- **Clear separation of concerns** between frontend (Next.js) and backend (FastAPI)
- **Unified entity management** across 5 artifact types
- **Flexible modal system** with tab-based details
- **TanStack Query caching** for efficient data management
- **Mock fallback pattern** for offline development
- **Extensible component architecture** for adding new features

The navigation system is clean and intuitive, with a fixed sidebar and flexible main content area. Both the Collection and Manage pages follow similar patterns (view toggle, filters, list/grid display, unified modal) which provides a consistent user experience.

The codebase is well-positioned for adding collection/group management features by extending the existing filter and organizational patterns.

