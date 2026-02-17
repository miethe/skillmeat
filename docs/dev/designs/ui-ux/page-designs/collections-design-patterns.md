# Collections Page Design Pattern Reference

**Purpose**: Guide for implementing consistent page layouts and component patterns across SkillMeat web frontend.

**Status**: Verified - Collections page implemented, Context Entities page already follows most patterns.

**Last Verified**: 2026-02-17

---

## Quick Reference: Page Structure Comparison

### Collections Page Layout (Horizontal Toolbar Pattern)
```
┌─────────────────────────────────────────┐
│ CollectionHeader                         │ ← Title, count badge, Add button
├─────────────────────────────────────────┤
│ CollectionToolbar                        │ ← Search, filters, sort, view toggle
├─────────────────────────────────────────┤
│ TagFilterBar (conditional)               │ ← Shows active tag filters
├─────────────────────────────────────────┤
│ Content Area                             │
│  • Error state | Loading skeleton        │
│  • Empty state | Grid/List/Grouped view  │
│  • Pagination controls                   │
└─────────────────────────────────────────┘
```

### Context Entities Page Layout (Sidebar Filter Pattern)
```
┌──────────────────────────────────────────┐
│ Page Header with Add Button               │
├──────────────────────────────────────────┤
│ Two-Column Layout                        │
│ ┌────────────┐ ┌─────────────────────┐  │
│ │  Sidebar   │ │ Main Content        │  │
│ │  Filters   │ │  • Results header   │  │
│ │ (w-64)     │ │  • Error state      │  │
│ │            │ │  • Loading skeleton │  │
│ │            │ │  • Empty state      │  │
│ │            │ │  • Entity grid      │  │
│ │            │ │  • Load more button │  │
│ └────────────┘ └─────────────────────┘  │
└──────────────────────────────────────────┘
```

### Groups Two-Pane Layout Pattern
```
+---------------------+----------------------------------------+
| GroupSidebar        | ArtifactPane                           |
| (280px, fixed)      | (flex-1, independent scroll)           |
|                     |                                        |
| [*] All Artifacts   | [PaneHeader: group name + count]       |
| [ ] Ungrouped       | [RemoveFromGroupDropZone] (conditional)|
| ───────────         |                                        |
| [●] Group A     5   | [MiniArtifactCard] (draggable)         |
| [●] Group B     3   | [MiniArtifactCard]                     |
|                     | [MiniArtifactCard]                     |
| [+ Create Group]    |                                        |
| [Manage]            |                                        |
+---------------------+----------------------------------------+
```

---

## Key File Locations

| Component | Location | Purpose |
|-----------|----------|---------|
| Collections Page | `/skillmeat/web/app/collection/page.tsx` | Main page with layout orchestration |
| CollectionHeader | `/skillmeat/web/components/collection/collection-header.tsx` | Title, count badge, conditional buttons |
| CollectionToolbar | `/skillmeat/web/components/collection/collection-toolbar.tsx` | Search, filters, sort, view toggle |
| CreateCollectionDialog | `/skillmeat/web/components/collection/create-collection-dialog.tsx` | Create modal with validation |
| EditCollectionDialog | `/skillmeat/web/components/collection/edit-collection-dialog.tsx` | Update modal |
| UnifiedEntityModal | `/skillmeat/web/components/entity/unified-entity-modal.tsx` | Detail view modal |
| Context Entities Page | `/skillmeat/web/app/context-entities/page.tsx` | Already follows most patterns |
| GroupSidebar | `/skillmeat/web/components/collection/group-sidebar.tsx` | Fixed sidebar with group navigation and drop targets |
| MiniArtifactCard | `/skillmeat/web/components/collection/mini-artifact-card.tsx` | Draggable artifact card for grouped view |
| RemoveFromGroupDropZone | `/skillmeat/web/components/collection/remove-from-group-zone.tsx` | Drop zone for removing artifacts from groups |
| DndAnimations | `/skillmeat/web/components/collection/dnd-animations.tsx` | Shared animations for drag and drop operations |
| GroupedArtifactView | `/skillmeat/web/components/collection/grouped-artifact-view.tsx` | DndContext container with two-pane layout |
| use-dnd-animations | `/skillmeat/web/hooks/use-dnd-animations.ts` | Hook for DnD animation state management |
| use-artifact-groups | `/skillmeat/web/hooks/use-artifact-groups.ts` | Hook for group state and operations |

---

## Pattern 1: Page Layout Structure

### Collections Pattern (Vertical Stacking)
```typescript
// skillmeat/web/app/collection/page.tsx (lines 242-364)
return (
  <div className="flex h-full flex-col">
    {/* 1. Header */}
    <CollectionHeader {...props} />

    {/* 2. Toolbar */}
    <CollectionToolbar {...props} />

    {/* 3. Conditional Tag Filter Bar */}
    {selectedTags.length > 0 && (
      <div className="border-b px-6 py-2 bg-muted/10">
        <TagFilterBar selectedTags={selectedTags} onChange={handleTagsChange} />
      </div>
    )}

    {/* 4. Content Area - scrollable */}
    <div className="flex-1 overflow-auto p-6">
      {error && <ErrorAlert />}
      {isLoading && <LoadingSkeleton />}
      {!data && <EmptyState />}
      {data && <ArtifactGrid/List/Grouped />}
    </div>

    {/* 5. Modals at bottom */}
    <UnifiedEntityModal {...} />
    <EditCollectionDialog {...} />
    <CreateCollectionDialog {...} />
  </div>
);
```

### Context Entities Pattern (Sidebar Layout)
```typescript
// skillmeat/web/app/context-entities/page.tsx (lines 173-290)
return (
  <div className="space-y-6 p-6">
    {/* 1. Page Header with Add Button */}
    <div className="flex items-start justify-between gap-4">
      <div className="space-y-1">
        <h1 className="text-3xl font-bold">Context Entities</h1>
        <p className="text-muted-foreground">Description...</p>
      </div>
      <Button onClick={handleCreateNew}>
        <Plus className="mr-2 h-4 w-4" />
        Add Entity
      </Button>
    </div>

    {/* 2. Two-Column Layout */}
    <div className="flex gap-6">
      {/* Left: Sidebar Filters */}
      <nav className="w-64 flex-shrink-0">
        <div className="space-y-4 rounded-lg border bg-card p-4">
          <h2 className="text-sm font-semibold">Filters</h2>
          <ContextEntityFilters {...} />
        </div>
      </nav>

      {/* Right: Main Content */}
      <main id="main-content" className="flex-1 space-y-4">
        {/* Results header */}
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">{count} Entities</h2>
        </div>

        {/* Error/Loading/Empty/Content states */}
        {error && <ErrorAlert />}
        {isLoading && <LoadingSkeleton />}
        {!data?.items.length && <EmptyState hasFilters={hasActiveFilters} />}
        {data?.items && (
          <>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {data.items.map(entity => (
                <ContextEntityCard key={entity.id} {...} />
              ))}
            </div>
            {data.page_info.has_next_page && <LoadMoreButton />}
          </>
        )}
      </main>
    </div>

    {/* 3. Modals at bottom */}
    {selectedEntity && <ContextEntityDetail {...} />}
    <ContextEntityEditor {...} />
    {selectedEntity && <DeployToProjectDialog {...} />}
  </div>
);
```

**Choice**: Use sidebar pattern for complex filtering, toolbar pattern for simple filtering.

---

## Pattern 2: Header Component

### Collections Header Pattern
```typescript
// skillmeat/web/components/collection/collection-header.tsx (lines 23-85)

interface CollectionHeaderProps {
  collection: Collection | null;
  artifactCount: number;
  isAllCollections: boolean;
  onEdit?: () => void;
  onDelete?: () => void;
  onCreate?: () => void;
}

export function CollectionHeader({ collection, artifactCount, isAllCollections, ... }) {
  const title = isAllCollections ? 'All Collections' : collection?.name;

  return (
    <div className="border-b bg-background px-6 py-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 space-y-1">
          {/* Title + Badge */}
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">{title}</h1>
            <Badge variant="secondary">
              {artifactCount} {artifactCount === 1 ? 'artifact' : 'artifacts'}
            </Badge>

            {/* Conditional "New Collection" button - only in All Collections mode */}
            {isAllCollections && onCreate && (
              <Button variant="outline" size="sm" onClick={onCreate}>
                <FolderPlus className="mr-2 h-4 w-4" />
                New Collection
              </Button>
            )}
          </div>
          {description && <p className="text-sm text-muted-foreground">{description}</p>}
        </div>

        {/* Actions dropdown - only for single collection */}
        {!isAllCollections && collection && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="Collection actions">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={onEdit}>Edit Collection</DropdownMenuItem>
              <DropdownMenuItem onClick={onDelete} className="text-destructive">
                Delete Collection
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    </div>
  );
}
```

**Key Features**:
- Dynamic title based on mode (All Collections vs specific)
- Badge showing resource count
- Conditional buttons (New/Edit/Delete based on context)
- Left-aligned content, right-aligned actions

---

## Pattern 3: Toolbar Component (Collections-Specific)

### Collections Toolbar Pattern
```typescript
// skillmeat/web/components/collection/collection-toolbar.tsx (lines 86-356)

export function CollectionToolbar({
  viewMode,
  onViewModeChange,
  filters,
  onFiltersChange,
  searchQuery,
  onSearchChange,
  sortField,
  sortOrder,
  onSortChange,
  onRefresh,
  isRefreshing = false,
  lastUpdated = null,
  selectedTags = [],
  onTagsChange,
}: CollectionToolbarProps) {
  return (
    <div className="border-b bg-muted/30 px-6 py-3">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        {/* LEFT SIDE: Search + Filters + Sort + Tag Filter */}
        <div className="flex flex-1 items-center gap-2">
          {/* Search */}
          <div className="relative w-full max-w-sm">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Search artifacts..."
              value={localSearch}
              onChange={(e) => setLocalSearch(e.target.value)}
              className="pl-9 pr-4"
            />
          </div>

          {/* Tag Filter Popover */}
          <TagFilterPopover selectedTags={selectedTags} onChange={onTagsChange} />

          {/* Filters Dropdown with Badge */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="gap-2">
                <Filter className="h-4 w-4" />
                Filters
                {activeFilterCount > 0 && (
                  <Badge variant="secondary" className="ml-1">
                    {activeFilterCount}
                  </Badge>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-56">
              {/* Type, Status, Scope filters */}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Sort Dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="gap-2">
                <ArrowUpDown className="h-4 w-4" />
                Sort
              </Button>
            </DropdownMenuTrigger>
            {/* Sort options */}
          </DropdownMenu>

          {/* Clear Filters Button */}
          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={handleClearFilters}>
              <X className="h-4 w-4" />
              Clear
            </Button>
          )}
        </div>

        {/* RIGHT SIDE: View Mode Toggle + Refresh */}
        <div className="flex items-center gap-2">
          {/* View Mode Buttons */}
          <div className="flex items-center gap-1 rounded-md border bg-background p-1">
            <Button
              variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => onViewModeChange('grid')}
              className="h-8 w-8 p-0"
            >
              <Grid3x3 className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => onViewModeChange('list')}
              className="h-8 w-8 p-0"
            >
              <List className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === 'grouped' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => onViewModeChange('grouped')}
              className="h-8 w-8 p-0"
            >
              <Layers className="h-4 w-4" />
            </Button>
          </div>

          {/* Refresh Button */}
          <div className="flex items-center gap-2">
            {lastUpdated && (
              <span className="text-xs text-muted-foreground">
                Updated {formatRelativeTime(lastUpdated)}
              </span>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={onRefresh}
              disabled={isRefreshing}
            >
              <RefreshCw className={cn('h-4 w-4', isRefreshing && 'animate-spin')} />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
```

**Key Features**:
- Left side: Search (debounced 300ms) + Filters + Sort + Tag Filter + Clear button
- Right side: View mode toggle (grid/list/grouped) + Refresh button with timestamp
- Filter dropdown shows badge with active filter count
- All state handled by parent

---

## Pattern 4: Groups Two-Pane Layout (Grouped View Mode)

The Groups Two-Pane layout provides a fixed sidebar for group navigation combined with a flexible main pane for viewing and organizing artifacts within groups. Unlike the Context Entities sidebar filter pattern, this layout uses navigation and drag-and-drop interaction as its primary pattern.

### Layout Structure
```typescript
// skillmeat/web/components/collection/grouped-artifact-view.tsx

<DndContext>
  <div className="flex h-full gap-4">
    {/* LEFT: Fixed Group Sidebar (280px) */}
    <GroupSidebar
      groups={groups}
      selectedGroup={selectedGroup}
      onGroupSelect={handleGroupSelect}
      onManage={handleManageGroups}
      onCreate={handleCreateGroup}
    />

    {/* RIGHT: Artifact Pane (flex-1, independent scroll) */}
    <div className="flex-1 overflow-auto">
      <PaneHeader
        groupName={selectedGroup?.name}
        artifactCount={selectedGroup?.artifacts.length}
      />

      {selectedGroup?.id === 'ungrouped' && (
        <RemoveFromGroupDropZone />
      )}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
        {artifacts.map(artifact => (
          <MiniArtifactCard
            key={artifact.id}
            artifact={artifact}
            isDragging={activeId === artifact.id}
            isGhost={overGroups.has(artifact.id)}
          />
        ))}
      </div>
    </div>
  </div>
</DndContext>
```

### Key File Locations

| Component | Location | Purpose |
|-----------|----------|---------|
| GroupSidebar | `/skillmeat/web/components/collection/group-sidebar.tsx` | Fixed 280px sidebar displaying groups and counts |
| MiniArtifactCard | `/skillmeat/web/components/collection/mini-artifact-card.tsx` | Draggable card with animation hooks |
| RemoveFromGroupDropZone | `/skillmeat/web/components/collection/remove-from-group-zone.tsx` | Drop zone for ungrouping artifacts |
| DndAnimations | `/skillmeat/web/components/collection/dnd-animations.tsx` | Centralized animation system for DnD operations |
| GroupedArtifactView | `/skillmeat/web/components/collection/grouped-artifact-view.tsx` | DndContext container orchestrating layout |
| use-dnd-animations | `/skillmeat/web/hooks/use-dnd-animations.ts` | Hook managing pickup, drop, settle, poof animations |
| use-artifact-groups | `/skillmeat/web/hooks/use-artifact-groups.ts` | Hook managing group state and mutations |

### Sidebar Component Pattern

```typescript
// skillmeat/web/components/collection/group-sidebar.tsx

export function GroupSidebar({
  groups,
  selectedGroup,
  onGroupSelect,
  onManage,
  onCreate,
}: GroupSidebarProps) {
  return (
    <aside className="w-[280px] flex-shrink-0 overflow-auto border-r bg-muted/20 p-4">
      <div className="space-y-2">
        {/* All Artifacts option */}
        <button
          onClick={() => onGroupSelect(null)}
          className={cn(
            'w-full px-3 py-2 rounded-md text-left text-sm',
            selectedGroup === null
              ? 'bg-primary text-primary-foreground'
              : 'hover:bg-muted'
          )}
        >
          <Check className="mr-2 inline h-4 w-4" />
          All Artifacts
        </button>

        {/* Ungrouped option */}
        <button
          onClick={() => onGroupSelect('ungrouped')}
          className={cn(
            'w-full px-3 py-2 rounded-md text-left text-sm',
            selectedGroup?.id === 'ungrouped'
              ? 'bg-primary text-primary-foreground'
              : 'hover:bg-muted'
          )}
        >
          <Square className="mr-2 inline h-4 w-4" />
          Ungrouped
        </button>

        <Separator />

        {/* Groups list with counts */}
        <div className="space-y-1">
          {groups.map(group => (
            <button
              key={group.id}
              onClick={() => onGroupSelect(group)}
              className={cn(
                'w-full flex items-center justify-between px-3 py-2 rounded-md text-sm',
                selectedGroup?.id === group.id
                  ? 'bg-primary text-primary-foreground'
                  : 'hover:bg-muted'
              )}
            >
              <div className="flex items-center gap-2">
                <Circle className="h-3 w-3 fill-current" />
                <span>{group.name}</span>
              </div>
              <Badge variant="secondary" className="text-xs">
                {group.artifacts.length}
              </Badge>
            </button>
          ))}
        </div>

        <Separator />

        {/* Group management buttons */}
        <Button
          variant="ghost"
          className="w-full justify-start"
          onClick={onCreate}
        >
          <Plus className="mr-2 h-4 w-4" />
          Create Group
        </Button>

        <Button
          variant="ghost"
          className="w-full justify-start"
          onClick={onManage}
        >
          <Settings className="mr-2 h-4 w-4" />
          Manage
        </Button>
      </div>
    </aside>
  );
}
```

### MiniArtifactCard with DnD Integration

```typescript
// skillmeat/web/components/collection/mini-artifact-card.tsx

export function MiniArtifactCard({
  artifact,
  isDragging,
  isGhost,
}: MiniArtifactCardProps) {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id: artifact.id,
    data: { type: 'artifact', artifact },
  });

  const {
    scaleY,
    opacity,
    rotation,
  } = useAnimationStates(isDragging, isGhost);

  const style = transform
    ? {
        transform: `translate3d(${transform.x}px, ${transform.y}px, 0) scaleY(${scaleY}) rotate(${rotation}deg)`,
        opacity,
        transition: isDragging ? 'none' : 'all 200ms cubic-bezier(0.34, 1.56, 0.64, 1)',
      }
    : undefined;

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className={cn(
        'group relative rounded-lg border bg-card p-3 cursor-grab transition-all',
        isDragging && 'z-50 shadow-lg cursor-grabbing',
        isGhost && 'opacity-50'
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <h3 className="font-medium text-sm truncate">{artifact.name}</h3>
          <p className="text-xs text-muted-foreground">{artifact.type}</p>
        </div>
        {artifact.icon && (
          <img src={artifact.icon} alt="" className="h-4 w-4 flex-shrink-0" />
        )}
      </div>

      {/* Drag Handle Indicator */}
      {isDragging && (
        <div className="absolute inset-0 rounded-lg border-2 border-primary pointer-events-none" />
      )}
    </div>
  );
}
```

### Animation System

```typescript
// skillmeat/web/hooks/use-dnd-animations.ts

export function useDndAnimations(activeId: string | null) {
  const [animations, setAnimations] = useState<Map<string, AnimationState>>(new Map());

  // Track active drag
  const addActiveAnimation = (id: string) => {
    setAnimations(prev => new Map(prev).set(id, {
      state: 'pickup',
      scale: 0.95,
      rotate: 5,
      zIndex: 50,
    }));
  };

  // Settle after drop (brief hold before release)
  const addSettleAnimation = (id: string) => {
    setAnimations(prev => new Map(prev).set(id, {
      state: 'settle',
      scale: 1,
      rotate: 0,
      zIndex: 0,
    }));
    setTimeout(() => {
      setAnimations(prev => {
        const next = new Map(prev);
        next.delete(id);
        return next;
      });
    }, 200);
  };

  // Poof effect when removed from group
  const addPoofAnimation = (id: string, x: number, y: number) => {
    setAnimations(prev => new Map(prev).set(id, {
      state: 'poof',
      scale: 0,
      opacity: 0,
      x: x + 20,
      y: y + 20,
      duration: 300,
    }));
  };

  return {
    animations,
    addActiveAnimation,
    addSettleAnimation,
    addPoofAnimation,
  };
}
```

### Drop Zone Pattern

```typescript
// skillmeat/web/components/collection/remove-from-group-zone.tsx

export function RemoveFromGroupDropZone() {
  const { isOver, setNodeRef } = useDroppable({
    id: 'ungrouped-zone',
    data: { type: 'ungrouped' },
  });

  return (
    <div
      ref={setNodeRef}
      className={cn(
        'rounded-lg border-2 border-dashed p-6 text-center transition-all',
        isOver
          ? 'border-destructive bg-destructive/10'
          : 'border-muted-foreground/30'
      )}
    >
      <Trash2 className={cn(
        'mx-auto h-5 w-5 transition-all',
        isOver ? 'text-destructive' : 'text-muted-foreground'
      )} />
      <p className={cn(
        'mt-2 text-sm',
        isOver ? 'text-destructive font-medium' : 'text-muted-foreground'
      )}>
        {isOver ? 'Drop to remove from group' : 'Drag artifact here to remove from group'}
      </p>
    </div>
  );
}
```

### Key Design Distinctions

**Navigation vs Filtering**: Unlike the Context Entities sidebar which *filters* results, the Groups sidebar *navigates* between different views. Selecting a group changes which artifacts are displayed, not the availability of filters.

**Independent Scrolling**: The sidebar and main pane scroll independently. The sidebar remains fixed at 280px width while the pane expands with flex-1. Both can scroll when their content overflows.

**Drop Targets**: Sidebar groups are drop targets for DnD operations. When hovering a group while dragging an artifact, the group highlights. When hovering the "Ungrouped" zone in the main pane (conditional, only shown for ungrouped view), it shows a removal state.

**Animation Layers**: DnD animations include:
- **Pickup Scale**: Card scales to 0.95 and rotates slightly on drag start
- **Drop Settle**: Card returns to 1.0 scale with brief 200ms transition
- **Poof Removal**: Card scales to 0 and fades with particle effects when dropped in ungrouped zone
- **Ghost State**: Card fades to 0.5 opacity when hovering valid drop targets
- **Target Pulse**: Group badges in sidebar pulse when they're valid drop targets
- **Zone Pulse**: Drop zones show color transition and icon emphasis on hover

---

## Pattern 5: State Management

### Collections Page State Pattern (with Groups Hook Integration)

When implementing grouped view mode, integrate the artifact groups hook:

```typescript
// skillmeat/web/app/collection/page.tsx (lines in grouped view mode)

const { groups, selectedGroup, setSelectedGroup } = useArtifactGroups(collectionId);
const { addActiveAnimation, addSettleAnimation } = useDndAnimations();

// Handle DnD operations
const handleDragEnd = async (event: DragEndEvent) => {
  const { active, over } = event;

  if (!over) {
    addSettleAnimation(active.id as string);
    return;
  }

  if (over.data?.type === 'group') {
    // Move artifact to group
    await moveArtifactToGroup(active.id as string, over.data.groupId);
    addSettleAnimation(active.id as string);
  } else if (over.data?.type === 'ungrouped') {
    // Remove artifact from group
    await removeArtifactFromGroup(active.id as string);
    addPoofAnimation(active.id as string, over.data.x, over.data.y);
  }
};
```

### Collections Page State Pattern (Original)
```typescript
// skillmeat/web/app/collection/page.tsx (lines 86-146)

function CollectionPageContent() {
  // View mode with localStorage persistence
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('collection-view-mode');
      if (stored && ['grid', 'list', 'grouped'].includes(stored)) {
        setViewMode(stored as ViewMode);
      }
    }
  }, []);
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('collection-view-mode', viewMode);
    }
  }, [viewMode]);

  // Filters, search, sort
  const [filters, setFilters] = useState<ArtifactFilters>({});
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState('name');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  // Tag filtering from URL
  const selectedTags = useMemo(() => {
    return searchParams.get('tags')?.split(',').filter(Boolean) || [];
  }, [searchParams]);

  // Modal state
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  // Refresh state
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Data fetching
  const { data, isLoading: isLoadingArtifacts, error, refetch } = useArtifacts(
    filters,
    { field: sortField as any, order: sortOrder }
  );

  // Client-side filtering
  const filteredArtifacts = useMemo(() => {
    let artifacts = data?.artifacts ?? [];

    if (searchQuery) {
      // Search filtering
    }

    if (selectedTags.length > 0) {
      // Tag filtering
    }

    return artifacts;
  }, [data?.artifacts, searchQuery, selectedTags]);
}
```

### Context Entities Page State Pattern
```typescript
// skillmeat/web/app/context-entities/page.tsx (lines 67-92)

export default function ContextEntitiesPage() {
  // Filter state
  const [filters, setFilters] = useState<FilterType>({});

  // Modal state
  const [selectedEntity, setSelectedEntity] = useState<ContextEntity | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [isDeployOpen, setIsDeployOpen] = useState(false);
  const [editingEntity, setEditingEntity] = useState<ContextEntity | null>(null);

  // Pagination
  const [paginationCursor, setPaginationCursor] = useState<string | undefined>(undefined);

  // Data fetching with cursor-based pagination
  const {
    data,
    isLoading,
    error,
    refetch,
  } = useContextEntities({ ...filters, after: paginationCursor });

  // Mutations
  const createEntity = useCreateContextEntity();
  const deleteEntity = useDeleteContextEntity();
}
```

---

## Pattern 6: Modal Handlers

### Open Modal Pattern
```typescript
// Collections: Click artifact → Open detail
const handleArtifactClick = (artifact: Artifact) => {
  setSelectedEntity(artifactToEntity(artifact));
  setIsDetailOpen(true);
};

// Context Entities: Preview action
const handlePreview = (entity: ContextEntity) => {
  setSelectedEntity(entity);
  setIsDetailOpen(true);
};

// Collections: Create button
const handleCreate = () => {
  setShowCreateDialog(true);
};

// Context Entities: Create button
const handleCreateNew = () => {
  setEditingEntity(null);  // Clear any previous data
  setIsEditorOpen(true);
};
```

### Close Modal Pattern (with animation delay)
```typescript
// Always use 300ms delay to allow CSS transition
const handleDetailClose = () => {
  setIsDetailOpen(false);
  setTimeout(() => setSelectedEntity(null), 300);
};

const handleEditorClose = () => {
  setIsEditorOpen(false);
  setTimeout(() => setEditingEntity(null), 300);
};
```

---

## Pattern 7: Modal Components

### Create/Edit Dialog Pattern
```typescript
// skillmeat/web/components/collection/create-collection-dialog.tsx (lines 113-190)

<Dialog open={open} onOpenChange={handleClose}>
  <DialogContent className="sm:max-w-[500px]">
    {/* Header with icon */}
    <DialogHeader>
      <div className="flex items-center gap-3">
        <div className="rounded-lg bg-primary/10 p-2">
          <FolderPlus className="h-5 w-5 text-primary" />
        </div>
        <div>
          <DialogTitle>Create Collection</DialogTitle>
          <DialogDescription>
            Create a new collection to organize your artifacts
          </DialogDescription>
        </div>
      </div>
    </DialogHeader>

    {/* Form content */}
    <div className="space-y-4 py-4">
      <div className="space-y-2">
        <Label htmlFor="name">
          Name <span className="text-destructive">*</span>
        </Label>
        <Input
          id="name"
          placeholder="My Collection"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={isPending}
          className={errors.name ? 'border-destructive' : ''}
          autoFocus
        />
        {errors.name && <p className="text-sm text-destructive">{errors.name}</p>}
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">Description (Optional)</Label>
        <Textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>
    </div>

    {/* Footer with buttons */}
    <DialogFooter>
      <Button variant="outline" onClick={handleClose} disabled={isPending}>
        Cancel
      </Button>
      <Button onClick={handleCreate} disabled={isPending}>
        {isPending ? 'Creating...' : 'Create Collection'}
      </Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

---

## Pattern 8: States (Error, Loading, Empty, Content)

### Error State
```typescript
{error && (
  <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
    <p className="text-sm text-destructive">
      Failed to load artifacts. Please try again later.
    </p>
    {/* Optional: Add error detail */}
    {error instanceof Error && (
      <p className="mt-1 text-xs text-destructive/80">{error.message}</p>
    )}
  </div>
)}
```

### Loading State (Skeleton)
```typescript
{isLoading && (
  <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
    {[...Array(6)].map((_, i) => (
      <Skeleton key={i} className="h-48 w-full" />
    ))}
  </div>
)}
```

### Empty State (Conditional message)
```typescript
function EmptyState({ hasFilters }: { hasFilters: boolean }) {
  return (
    <div className="flex h-full items-center justify-center py-12">
      <div className="text-center">
        <FileText className="mx-auto h-12 w-12 text-muted-foreground/50" />
        <h3 className="mt-4 text-lg font-semibold">
          {hasFilters ? 'No entities match filters' : 'No context entities'}
        </h3>
        <p className="mt-2 text-sm text-muted-foreground">
          {hasFilters
            ? "Try adjusting your filters to find what you're looking for."
            : 'Create your first context entity to get started.'}
        </p>
      </div>
    </div>
  );
}

{!isLoading && !error && (!data?.items || data.items.length === 0) && (
  <EmptyState hasFilters={hasActiveFilters} />
)}
```

### Content State (Grid view with cards)
```typescript
{!isLoading && !error && data?.items && data.items.length > 0 && (
  <>
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      {data.items.map((entity) => (
        <ContextEntityCard key={entity.id} entity={entity} {...handlers} />
      ))}
    </div>

    {/* Load More Button */}
    {data.page_info.has_next_page && (
      <div className="flex justify-center pt-6">
        <Button variant="outline" onClick={handleLoadMore} disabled={isLoading}>
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Loading more...
            </>
          ) : (
            'Load More'
          )}
        </Button>
      </div>
    )}
  </>
)}
```

---

## Pattern 9: Filter Handling

### Sidebar Filter Pattern (Context Entities)
```typescript
// skillmeat/web/app/context-entities/page.tsx (lines 198-206)
<nav aria-label="Filter context entities" className="w-64 flex-shrink-0">
  <div className="space-y-4 rounded-lg border bg-card p-4">
    <h2 className="text-sm font-semibold">Filters</h2>
    <ContextEntityFilters filters={filters} onFiltersChange={setFilters} />
  </div>
</nav>

// Determine if filters are active
const hasActiveFilters = Object.keys(filters).some(
  (key) => filters[key as keyof FilterType] !== undefined
);
```

### Toolbar Filter Pattern (Collections)
```typescript
// skillmeat/web/components/collection/collection-toolbar.tsx (lines 171-253)
<DropdownMenu>
  <DropdownMenuTrigger asChild>
    <Button variant="outline" size="sm" className="gap-2">
      <Filter className="h-4 w-4" />
      Filters
      {activeFilterCount > 0 && (
        <Badge variant="secondary" className="ml-1">
          {activeFilterCount}
        </Badge>
      )}
    </Button>
  </DropdownMenuTrigger>
  <DropdownMenuContent align="start" className="w-56">
    {/* Filter options */}
  </DropdownMenuContent>
</DropdownMenu>
```

---

## Pattern 10: Accessibility

### Skip Link
```typescript
<a
  href="#main-content"
  className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50"
>
  Skip to main content
</a>
```

### ARIA Labels & Landmarks
```typescript
// Navigation landmark
<nav aria-label="Filter context entities">

// Main landmark
<main id="main-content">

// Button labels
<Button aria-label="Add new context entity">
  <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
  Add Entity
</Button>

// Loading announcements
<div role="status" aria-live="polite" aria-label="Loading context entities">
  <span className="sr-only">Loading context entities...</span>
</div>
```

---

## Implementation Checklist

When creating a new list/grid page:

- [ ] Page layout (vertical stacking or sidebar pattern)
- [ ] Header with title, count badge, and conditional buttons
- [ ] Filters (toolbar dropdown or sidebar)
- [ ] Conditional tag filter bar (collections pattern)
- [ ] Search with debouncing (300ms)
- [ ] Sort options
- [ ] View mode toggle (if applicable)
- [ ] Refresh button with timestamp (if applicable)
- [ ] Error state with detailed message
- [ ] Loading skeleton matching layout
- [ ] Empty state with conditional messaging
- [ ] Grid/List display with cards
- [ ] Load more or pagination
- [ ] Detail/Preview modal
- [ ] Create/Edit dialog
- [ ] Delete with confirmation
- [ ] Close handlers with 300ms delay
- [ ] Accessibility (skip link, ARIA labels, landmarks)
- [ ] localStorage persistence (view mode, filters)

---

## References

**Collections Page**:
- Page: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/collection/page.tsx`
- Header: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/collection/collection-header.tsx`
- Toolbar: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/collection/collection-toolbar.tsx`
- Create Dialog: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/collection/create-collection-dialog.tsx`

**Context Entities Page**:
- Page: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/context-entities/page.tsx`
- Card: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/context/context-entity-card.tsx`
- Filters: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/context/context-entity-filters.tsx`
- Detail Modal: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/context/context-entity-detail.tsx`
- Editor Dialog: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/context/context-entity-editor.tsx`

---

## Related Documentation

- **Hooks Guide**: `.claude/rules/web/hooks.md`
- **API Client Guide**: `.claude/rules/web/api-client.md`
- **Router Patterns**: `.claude/rules/api/routers.md`
