# SkillMeat Components Quick Reference

**Last Updated**: December 12, 2025
**Purpose**: Fast lookup of component locations, props, and usage patterns

---

## Navigation & Layout

### Navigation Component
**File**: `/skillmeat/web/components/navigation.tsx`

```typescript
export function Navigation(): JSX.Element

// Props: None (uses usePathname internally)

// Usage:
import { Navigation } from '@/components/navigation';

<Navigation />

// Renders 8 nav items with optional sub-items
// Active state via pathname comparison
// Icons: Lucide
```

### Header Component
**File**: `/skillmeat/web/components/header.tsx`

```typescript
export function Header(): JSX.Element

// Props: None (uses useNotifications hook)

// Features:
// - Logo + Title
// - Notification bell with unread count
// - External links (GitHub, Docs)
// - Sticky positioning (top-0 z-50)
```

### Root Layout
**File**: `/skillmeat/web/app/layout.tsx`

```typescript
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}): JSX.Element

// Wraps app with:
// - Providers (TanStack Query, Toast, etc.)
// - Header
// - Navigation
// - Main content area
```

---

## Collection Page Components

### Collection Page
**File**: `/skillmeat/web/app/collection/page.tsx`

```typescript
export default function CollectionPage(): JSX.Element

// State:
const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
const [isDetailOpen, setIsDetailOpen] = useState(false);
const [filters, setFilters] = useState<ArtifactFilters>({});
const [sort, setSort] = useState<ArtifactSort>({ field: 'name', order: 'asc' });

// Data:
const { data, isLoading, error } = useArtifacts(filters, sort);

// Renders:
// - Page header
// - Filters
// - View toggle (grid/list)
// - ArtifactGrid or ArtifactList
// - UnifiedEntityModal
```

### Artifact Grid
**File**: `/skillmeat/web/components/collection/artifact-grid.tsx`

```typescript
interface ArtifactGridProps {
  artifacts: Artifact[];
  isLoading: boolean;
  onArtifactClick: (artifact: Artifact) => void;
}

export function ArtifactGrid(props): JSX.Element

// Renders grid of artifact cards
// Shows loading skeletons while isLoading
// Calls onArtifactClick when card clicked
```

### Artifact List
**File**: `/skillmeat/web/components/collection/artifact-list.tsx`

```typescript
interface ArtifactListProps {
  artifacts: Artifact[];
  isLoading: boolean;
  onArtifactClick: (artifact: Artifact) => void;
}

export function ArtifactList(props): JSX.Element

// Renders table of artifact rows
// Same props as ArtifactGrid
// Uses artifact-row component for each item
```

### Filters Component
**File**: `/skillmeat/web/components/collection/filters.tsx`

```typescript
interface FiltersProps {
  filters: ArtifactFilters;
  sort: ArtifactSort;
  onFiltersChange: (filters: ArtifactFilters) => void;
  onSortChange: (sort: ArtifactSort) => void;
}

export function Filters(props): JSX.Element

// Filter controls:
// - Type select (skill|command|agent|mcp|hook)
// - Status select (active|outdated|conflict)
// - Scope select (user|local)
// - Search text input
// - Sort field select (name|updatedAt|usageCount)
// - Sort order toggle (asc|desc)
```

---

## Manage Page Components

### Manage Page
**File**: `/skillmeat/web/app/manage/page.tsx`

```typescript
export default function ManagePage(): JSX.Element

// State:
const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
const [detailPanelOpen, setDetailPanelOpen] = useState(false);
const [addDialogOpen, setAddDialogOpen] = useState(false);
const [editingEntity, setEditingEntity] = useState<Entity | null>(null);
const [tagFilter, setTagFilter] = useState<string[]>([]);

// From EntityLifecycleProvider:
const {
  entities,
  isLoading,
  isRefetching,
  refetch,
  setTypeFilter,
  setStatusFilter,
  setSearchQuery,
  searchQuery,
  statusFilter,
  deleteEntity,
} = useEntityLifecycle();

// Renders:
// - Header (title, refresh, view toggle, add button)
// - EntityTabs (5 tabs for entity types)
// - EntityFilters (search, status, tags)
// - EntityList (grid or list view)
// - UnifiedEntityModal
// - AddEntityDialog
// - Edit Dialog (conditional)
```

### Entity Tabs
**File**: `/skillmeat/web/app/manage/components/entity-tabs.tsx`

```typescript
interface EntityTabsProps {
  children: (entityType: EntityType) => React.ReactNode;
}

export function EntityTabs(props): JSX.Element

// Renders 5 tabs for:
// - skill (Sparkles icon)
// - command (Terminal icon)
// - agent (Bot icon)
// - mcp (Server icon)
// - hook (Webhook icon)

// Updates URL param: ?type={entityType}
// Children receive current entityType via callback
```

### Entity Filters
**File**: `/skillmeat/web/app/manage/components/entity-filters.tsx`

```typescript
interface EntityFiltersProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  statusFilter: EntityStatus | null;
  onStatusFilterChange: (status: EntityStatus | null) => void;
  tagFilter: string[];
  onTagFilterChange: (tags: string[]) => void;
}

export function EntityFilters(props): JSX.Element

// Renders:
// - Search input (debounced)
// - Status dropdown (synced|modified|outdated|conflict)
// - Tag multi-select
```

### Entity List
**File**: `/skillmeat/web/components/entity/entity-list.tsx`

```typescript
interface EntityListProps {
  viewMode: 'grid' | 'list';
  entities: Entity[];
  onEntityClick: (entity: Entity) => void;
  onEdit: (entity: Entity) => void;
  onDelete: (entity: Entity) => void;
  onDeploy: (entity: Entity) => void;
  onSync: (entity: Entity) => void;
  onViewDiff: (entity: Entity) => void;
  onRollback: (entity: Entity) => void;
}

export function EntityList(props): JSX.Element

// Routes to EntityGrid or EntityListTable based on viewMode
// Passes all callbacks to child components
```

---

## Unified Entity Modal

### Unified Entity Modal
**File**: `/skillmeat/web/components/entity/unified-entity-modal.tsx`

```typescript
interface UnifiedEntityModalProps {
  entity: Entity | null;
  open: boolean;
  onClose: () => void;
}

export function UnifiedEntityModal(props): JSX.Element

// Renders tabbed modal with:
// - Overview (metadata, status, tags, timestamps)
// - Sync/Deploy (version comparison, diff viewer, actions)
// - History (timeline of events)
// - Files (file tree, preview, editor)

// State:
const [activeTab, setActiveTab] = useState('overview');
const [selectedFile, setSelectedFile] = useState<string | null>(null);
const [editingFile, setEditingFile] = useState<string | null>(null);
const [comparisonMode, setComparisonMode] = useState<'upstream' | 'project'>();

// Features:
// - Diff viewer with 3-way merge
// - File tree with preview
// - Rollback dialog
// - Merge workflow
// - Unsaved changes warning
```

### Diff Viewer
**File**: `/skillmeat/web/components/entity/diff-viewer.tsx`

```typescript
interface DiffViewerProps {
  diff: ArtifactDiffResponse;
  baseLabel: string;
  compareLabel: string;
}

export function DiffViewer(props): JSX.Element

// Side-by-side diff display
// Shows added/removed/modified lines
// Color-coded (green/red)
```

### File Tree
**File**: `/skillmeat/web/components/entity/file-tree.tsx`

```typescript
interface FileTreeProps {
  files: FileNode[];
  selectedFile: string | null;
  onSelectFile: (path: string) => void;
  onCreateFile?: (path: string, content: string) => Promise<void>;
  onDeleteFile?: (path: string) => Promise<void>;
}

export function FileTree(props): JSX.Element

// Hierarchical file browser
// Expandable directories
// File icons based on extension
// Selected file highlighted
// Actions: create, delete (if handlers provided)
```

### Content Pane
**File**: `/skillmeat/web/components/entity/content-pane.tsx`

```typescript
interface ContentPaneProps {
  file: FileNode;
  content: string;
  isEditing: boolean;
  onEdit: (path: string, newContent: string) => Promise<void>;
  onCancel: () => void;
}

export function ContentPane(props): JSX.Element

// File preview pane (right side)
// Read-only display or Monaco editor
// Syntax highlighting
// Save/Cancel buttons when editing
```

### Rollback Dialog
**File**: `/skillmeat/web/components/entity/rollback-dialog.tsx`

```typescript
interface RollbackDialogProps {
  entity: Entity;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onRollback: (version: string) => Promise<void>;
}

export function RollbackDialog(props): JSX.Element

// Dialog for selecting version to rollback to
// Shows available versions from history
// Confirmation before rollback
// Loading state during operation
```

---

## Marketplace Components

### Add Source Modal
**File**: `/skillmeat/web/components/marketplace/add-source-modal.tsx`

```typescript
interface AddSourceModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: (source: SourceResponse) => void;
}

export function AddSourceModal(props): JSX.Element

// Form for adding GitHub source
// Fields:
// - GitHub URL (required)
// - Description (optional)
// - Notes (optional)
// Validates URL format
// Calls POST /api/v1/marketplace/sources
```

### Edit Source Modal
**File**: `/skillmeat/web/components/marketplace/edit-source-modal.tsx`

```typescript
interface EditSourceModalProps {
  source: SourceResponse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: (source: SourceResponse) => void;
}

export function EditSourceModal(props): JSX.Element

// Form for editing source metadata
// Editable fields:
// - Description
// - Notes
// Calls PATCH /api/v1/marketplace/sources/{id}
// with UpdateSourceRequest body
```

### Delete Source Dialog
**File**: `/skillmeat/web/components/marketplace/delete-source-dialog.tsx`

```typescript
interface DeleteSourceDialogProps {
  source: SourceResponse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function DeleteSourceDialog(props): JSX.Element

// Confirmation dialog for deletion
// Shows source name
// Delete button with loading state
// Calls DELETE /api/v1/marketplace/sources/{id}
```

### Source Card
**File**: `/skillmeat/web/components/marketplace/source-card.tsx`

```typescript
interface SourceCardProps {
  source: SourceResponse;
  onEdit?: (source: SourceResponse) => void;
  onDelete?: (source: SourceResponse) => void;
  onRescan?: (source: SourceResponse) => void;
}

export function SourceCard(props): JSX.Element

// Card displaying source info
// Shows:
// - Repository name (owner/repo)
// - Description
// - Artifacts found count
// - Last scanned timestamp
// - Status badge (active|scanning|error)
// - Action menu (edit, delete, rescan)
```

---

## Hooks

### useArtifacts
**File**: `/skillmeat/web/hooks/useArtifacts.ts`

```typescript
export function useArtifacts(
  filters: ArtifactFilters = {},
  sort: ArtifactSort = { field: 'name', order: 'asc' }
): UseQueryResult<ArtifactsResponse, Error>

// Fetches from: GET /api/v1/artifacts?limit=100&artifact_type={type}
// Filters applied client-side: type, status, scope, search
// Cache: 30 second staleTime
// Returns: { data, isLoading, error }

// Usage:
const { data, isLoading, error } = useArtifacts(filters, sort);
```

### useEntityLifecycle
**File**: `/skillmeat/web/hooks/useEntityLifecycle.tsx`

```typescript
export function useEntityLifecycle(): EntityLifecycleContextValue

// Centralized entity management
// Returns:
// - entities: Entity[]
// - selectedEntities: string[]
// - isLoading: boolean
// - isRefetching: boolean
// - typeFilter: EntityType | null
// - statusFilter: EntityStatus | null
// - searchQuery: string
// - mode: 'collection' | 'project'
// - setTypeFilter(type)
// - setStatusFilter(status)
// - setSearchQuery(query)
// - deleteEntity(id)
// - refetch()

// Usage:
const {
  entities,
  isLoading,
  searchQuery,
  setSearchQuery,
  setTypeFilter,
} = useEntityLifecycle();
```

### useUpdateArtifact
**File**: `/skillmeat/web/hooks/useArtifacts.ts`

```typescript
export function useUpdateArtifact(): UseMutationResult<
  Artifact,
  Error,
  Partial<Artifact> & { id: string }
>

// Calls: PUT /api/v1/artifacts/{id}
// Invalidates artifact cache on success
// Returns: { mutate, mutateAsync, isLoading, error }

// Usage:
const updateArtifact = useUpdateArtifact();
await updateArtifact.mutateAsync({
  id: '123',
  name: 'new-name',
});
```

### useMarketplaceSources
**File**: `/skillmeat/web/hooks/useMarketplaceSources.ts`

```typescript
export function useMarketplaceSources()

// Fetches from: GET /api/v1/marketplace/sources
// Returns: { data: SourceResponse[], isLoading, error }

export function useAddMarketplaceSource()

// Mutation for: POST /api/v1/marketplace/sources
// Body: CreateSourceRequest { github_url, description?, notes? }
// Returns: UseMutationResult

export function useUpdateMarketplaceSource()

// Mutation for: PATCH /api/v1/marketplace/sources/{id}
// Body: UpdateSourceRequest { description?, notes? }

export function useDeleteMarketplaceSource()

// Mutation for: DELETE /api/v1/marketplace/sources/{id}

export function useRescanMarketplaceSource()

// Mutation for: POST /api/v1/marketplace/sources/{id}/rescan
```

---

## Entity Types & Configurations

### Entity Type Definition
**File**: `/skillmeat/web/types/entity.ts`

```typescript
export type EntityType = 'skill' | 'command' | 'agent' | 'mcp' | 'hook';

export interface EntityTypeConfig {
  type: EntityType;
  label: string;              // "Skill"
  pluralLabel: string;        // "Skills"
  icon: string;               // Lucide icon name
  color: string;              // Tailwind class
  requiredFile: string;       // "SKILL.md"
  formSchema: EntityFormSchema;
}

export const ENTITY_TYPES: Record<EntityType, EntityTypeConfig>

// Usage:
const skillConfig = ENTITY_TYPES['skill'];
const Icon = LucideIcons[skillConfig.icon];
```

### Entity Interface
**File**: `/skillmeat/web/types/entity.ts`

```typescript
export interface Entity {
  id: string;                 // "type:name"
  name: string;
  type: EntityType;
  collection?: string;
  projectPath?: string;
  status?: EntityStatus;      // synced|modified|outdated|conflict
  tags?: string[];
  description?: string;
  version?: string;
  source?: string;
  deployedAt?: string;        // ISO timestamp
  modifiedAt?: string;        // ISO timestamp
  aliases?: string[];
}
```

### Artifact Interface
**File**: `/skillmeat/web/types/artifact.ts`

```typescript
export interface Artifact {
  id: string;
  name: string;
  type: ArtifactType;
  scope: ArtifactScope;       // user|local
  status: ArtifactStatus;     // active|outdated|conflict|error
  version?: string;
  source?: string;
  metadata: ArtifactMetadata;
  upstreamStatus: UpstreamStatus;
  usageStats: UsageStats;
  createdAt: string;
  updatedAt: string;
  aliases?: string[];
}
```

---

## API Request Utilities

### API Request Function
**File**: `/skillmeat/web/lib/api.ts`

```typescript
export async function apiRequest<T>(
  path: string,
  init?: RequestInit
): Promise<T>

// Builds URL: {BASE_URL}/api/{VERSION}{path}
// Adds headers:
// - Accept: application/json
// - Content-Type: application/json
// - Authorization: Bearer {TOKEN} (if set)
// - X-API-Key: {KEY} (if set)
// Throws ApiError on non-2xx response

// Usage:
const artifacts = await apiRequest<ArtifactListResponse>('/artifacts');
const result = await apiRequest('/artifacts/123', {
  method: 'PUT',
  body: JSON.stringify({ name: 'new-name' }),
});
```

### API Config
**File**: `/skillmeat/web/lib/api.ts`

```typescript
export const apiConfig = {
  baseUrl: string;      // from NEXT_PUBLIC_API_URL
  version: string;      // from NEXT_PUBLIC_API_VERSION
  apiKey?: string;      // from NEXT_PUBLIC_API_KEY
  apiToken?: string;    // from NEXT_PUBLIC_API_TOKEN
  useMocks: boolean;    // from NEXT_PUBLIC_ENABLE_API_MOCKS
  trace: boolean;       // from NEXT_PUBLIC_API_TRACE
}
```

---

## Type Definitions Summary

### Status Types
```typescript
// Entity status (manage page)
type EntityStatus = 'synced' | 'modified' | 'outdated' | 'conflict';

// Artifact status (collection page)
type ArtifactStatus = 'active' | 'outdated' | 'conflict' | 'error';

// Artifact scope
type ArtifactScope = 'user' | 'local';

// Marketplace source status
type SourceStatus = 'active' | 'scanning' | 'error';
```

### Filter Types
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

---

## Environment Variables

**Location**: `.env.local` (gitignored, create from `.env.example`)

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8080
NEXT_PUBLIC_API_VERSION=v1
NEXT_PUBLIC_API_KEY=            # Optional
NEXT_PUBLIC_API_TOKEN=          # Optional

# Development
NEXT_PUBLIC_ENABLE_API_MOCKS=false
NEXT_PUBLIC_API_TRACE=false
```

---

## Common Component Patterns

### Using UnifiedEntityModal
```tsx
const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
const [isOpen, setIsOpen] = useState(false);

const handleSelectEntity = (artifact: Artifact) => {
  setSelectedEntity(artifactToEntity(artifact));
  setIsOpen(true);
};

return (
  <>
    <ArtifactList onArtifactClick={handleSelectEntity} />
    <UnifiedEntityModal
      entity={selectedEntity}
      open={isOpen}
      onClose={() => setIsOpen(false)}
    />
  </>
);
```

### Using Filters with Artifacts
```tsx
const [filters, setFilters] = useState<ArtifactFilters>({});
const [sort, setSort] = useState<ArtifactSort>({ field: 'name', order: 'asc' });
const { data, isLoading } = useArtifacts(filters, sort);

return (
  <>
    <Filters
      filters={filters}
      sort={sort}
      onFiltersChange={setFilters}
      onSortChange={setSort}
    />
    {isLoading ? <Skeleton /> : <ArtifactGrid artifacts={data?.artifacts} />}
  </>
);
```

### Using EntityLifecycleProvider
```tsx
<EntityLifecycleProvider mode="collection">
  <ManagePage />
</EntityLifecycleProvider>

// Inside ManagePage:
const {
  entities,
  isLoading,
  searchQuery,
  setSearchQuery,
  deleteEntity,
} = useEntityLifecycle();
```

---

## API Response Types (Common)

### List Response Pattern
```typescript
interface ArtifactListResponse {
  items: ApiArtifact[];
  page_info: PageInfo;  // has_next_page, start_cursor, end_cursor, total_count
}
```

### Entity Response Pattern
```typescript
interface Entity {
  id: string;
  name: string;
  type: EntityType;
  // ... other fields
  created_at?: string;
  updated_at?: string;
}
```

### Marketplace Source Response
```typescript
interface SourceResponse {
  id: string;
  github_url: string;
  owner: string;
  repo: string;
  description?: string;
  notes?: string;
  artifacts_found: number;
  last_scanned?: string;
  status: 'active' | 'scanning' | 'error';
  error_message?: string;
  created_at: string;
  updated_at: string;
}
```

---

**This reference is auto-generated from code inspection on December 12, 2025**

