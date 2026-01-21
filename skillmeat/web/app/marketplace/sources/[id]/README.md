# Marketplace Source Detail Page

**Path**: `/marketplace/sources/[id]`

## Overview

This page displays detailed information about a GitHub marketplace source, including its artifact catalog, filtering/sorting tools, and management actions.

---

## Key Features

### 1. Source Information Display

- Owner/repo name and GitHub link
- Branch/ref and root hint
- Description and notes
- Status badges (new, updated, imported counts)

### 2. Toolbar (`SourceToolbar` component)

Located in `components/source-toolbar.tsx`

**Features**:

- Search artifacts by name/path
- Filter by artifact type (skill, agent, command, mcp, hook)
- Sort by confidence, name, or date
- Confidence range filter (min/max %)
- Include low-confidence toggle
- Select all importable artifacts
- View mode toggle (grid/list)
- Clear all filters
- **Map Directories** button (opens DirectoryMapModal)

**Props**:

```typescript
interface SourceToolbarProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  selectedType: ArtifactType | null;
  onTypeChange: (type: ArtifactType | null) => void;
  countsByType: Record<string, number>;
  sortOption: SortOption;
  onSortChange: (option: SortOption) => void;
  minConfidence: number;
  maxConfidence: number;
  onMinConfidenceChange: (value: number) => void;
  onMaxConfidenceChange: (value: number) => void;
  includeBelowThreshold: boolean;
  onIncludeBelowThresholdChange: (value: boolean) => void;
  selectedCount: number;
  totalSelectableCount: number;
  allSelected: boolean;
  onSelectAll: () => void;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  hasActiveFilters: boolean;
  onClearFilters: () => void;
  onMapDirectories?: () => void; // Opens DirectoryMapModal
}
```

### 3. Catalog Display

- **Grid View**: Card-based layout (default)
- **List View**: Dense table layout
- Infinite scroll pagination
- Per-artifact actions (import, exclude, view details)
- Bulk import (selected artifacts)
- Entry details modal

### 4. Directory Mapping (`DirectoryMapModal`)

**Location**: `components/marketplace/DirectoryMapModal.tsx`

Allows users to manually map repository directories to artifact types, improving detection accuracy.

**Integration**:

```typescript
// Open modal and fetch GitHub tree data
const handleOpenDirectoryMap = async () => {
  setDirectoryMapModalOpen(true);
  setIsLoadingTree(true);

  const response = await fetch(
    `https://api.github.com/repos/${owner}/${repo}/git/trees/${ref}?recursive=1`
  );

  const data = await response.json();
  setTreeData(data.tree || []);
  setIsLoadingTree(false);
};

// Save mappings only
const handleConfirmMappings = async (mappings: Record<string, string>) => {
  await updateSourceMutation.mutateAsync({ manual_map: mappings });
};

// Save mappings and trigger rescan
const handleConfirmAndRescan = async (mappings: Record<string, string>) => {
  await updateSourceMutation.mutateAsync({ manual_map: mappings });
  await rescanMutation.mutateAsync({ manual_map: mappings });
};
```

**Usage**:

```tsx
<DirectoryMapModal
  open={directoryMapModalOpen}
  onOpenChange={setDirectoryMapModalOpen}
  sourceId={sourceId}
  repoInfo={{ owner, repo, ref }}
  treeData={treeData}
  isLoadingTree={isLoadingTree}
  treeError={treeError}
  initialMappings={source?.manual_map || {}}
  onConfirm={handleConfirmMappings}
  onConfirmAndRescan={handleConfirmAndRescan}
/>
```

### 5. Source Actions

- **Rescan**: Re-detect artifacts in repository
- **Edit**: Update source metadata (ref, root_hint, description, notes)
- **Delete**: Remove source and all catalog entries
- **View Repo**: Open GitHub repository in new tab

---

## Component Structure

```
page.tsx (main component)
├── Header
│   ├── Back button
│   ├── Source info (owner/repo, ref, description)
│   └── Action buttons (Rescan, View Repo, Edit, Delete)
├── Status Badges
│   └── Counts by status (new, updated, imported, etc.)
├── SourceToolbar (filtering, sorting, view mode, directory mapping)
├── Bulk Import Button (shown when items selected)
├── Notes Section (if source.notes exists)
├── Catalog Display
│   ├── Grid View (CatalogCard components)
│   └── List View (CatalogList component)
├── Load More Button (infinite scroll)
├── ExcludedArtifactsList (collapsed section)
└── Modals
    ├── EditSourceModal
    ├── DeleteSourceDialog
    ├── CatalogEntryModal (artifact details)
    └── DirectoryMapModal (directory mapping)
```

---

## State Management

### URL State (synced with URL params)

- `type`: Selected artifact type filter
- `status`: Selected status filter
- `minConfidence`: Minimum confidence threshold
- `maxConfidence`: Maximum confidence threshold
- `includeBelowThreshold`: Include low-confidence artifacts
- `sort`: Sort option

### Local State

- `searchQuery`: Search text (debounced)
- `selectedEntries`: Set of selected artifact IDs
- `editModalOpen`: Edit modal visibility
- `deleteDialogOpen`: Delete dialog visibility
- `selectedEntry`: Currently selected catalog entry
- `modalOpen`: Entry details modal visibility
- `directoryMapModalOpen`: Directory mapping modal visibility
- `treeData`: GitHub repository tree data
- `isLoadingTree`: Tree loading state
- `treeError`: Tree fetch error message
- `confidenceFilters`: Min/max confidence and threshold toggle
- `sortOption`: Current sort configuration
- `viewMode`: Grid or list view (persisted to localStorage)

---

## Data Fetching

### Queries (TanStack Query)

```typescript
// Source metadata
const { data: source } = useSource(sourceId);

// Catalog entries (infinite scroll)
const { data: catalogData, fetchNextPage, hasNextPage } = useSourceCatalog(sourceId, filters);
```

### Mutations

```typescript
// Rescan source
const rescanMutation = useRescanSource(sourceId);

// Import artifacts
const importMutation = useImportArtifacts(sourceId);

// Update source metadata
const updateSourceMutation = useUpdateSource(sourceId);

// Exclude catalog entry
const excludeMutation = useExcludeCatalogEntry(sourceId);
```

---

## Filtering Logic

### Client-Side Filters

- **Search**: Filters by artifact name or path (case-insensitive)
- **Sort**: Sorts entries by confidence, name, or date

### Server-Side Filters

- **Type**: `artifact_type` filter
- **Status**: `status` filter (new, updated, imported, removed, excluded)
- **Confidence Range**: `min_confidence`, `max_confidence`
- **Below Threshold**: `include_below_threshold` flag

---

## Common Tasks

### Add a New Filter

1. Add state variable in `page.tsx`
2. Add prop to `SourceToolbarProps` interface
3. Add UI control in `SourceToolbar` component
4. Wire prop to state handler
5. Add filter to `mergedFilters` object
6. Update `hasActiveFilters` logic
7. Update `onClearFilters` to reset new filter

### Add a New Action Button

1. Import icon from `lucide-react`
2. Add mutation hook (if needed)
3. Add button to header or toolbar
4. Implement handler function
5. Wire button `onClick` to handler
6. Add loading/disabled states

### Customize Catalog Card

1. Edit `CatalogCard` component in `page.tsx`
2. Update `CatalogCardProps` interface if needed
3. Maintain accessibility (ARIA labels, keyboard navigation)
4. Update loading skeleton to match

---

## Testing

### Unit Tests

```bash
pnpm test -- source-toolbar
```

### E2E Tests

```bash
pnpm test:e2e -- marketplace/sources
```

### Manual Testing Checklist

- [ ] Toolbar filters work correctly
- [ ] Search filters artifacts in real-time
- [ ] Sort changes order of artifacts
- [ ] Confidence range filters properly
- [ ] View mode toggle persists
- [ ] Bulk import works with selected items
- [ ] Directory mapping modal opens and saves
- [ ] Rescan updates catalog
- [ ] Edit/delete source works
- [ ] Infinite scroll loads more items
- [ ] URL syncs with filter state
- [ ] Back button navigates correctly

---

## Troubleshooting

### Tree Data Not Loading

- **Symptom**: DirectoryMapModal shows error or empty tree
- **Cause**: GitHub API rate limit or network error
- **Solution**: Check GitHub API rate limit, verify network connection, ensure source.ref is valid

### Filters Not Updating Catalog

- **Symptom**: Changing filters doesn't update visible artifacts
- **Cause**: URL params not syncing or server-side filters not working
- **Solution**: Check `mergedFilters` object, verify URL params update, check backend API response

### Selection Not Working

- **Symptom**: Cannot select artifacts or bulk import fails
- **Cause**: Removed/imported artifacts are not selectable
- **Solution**: Check artifact status, ensure only new/updated artifacts are selectable

### Modal Not Closing

- **Symptom**: DirectoryMapModal or other modals won't close
- **Cause**: State not updating or unsaved changes warning
- **Solution**: Check modal `open` and `onOpenChange` props, verify dirty state logic

---

## Performance Considerations

1. **Debounced Search**: Search input debounces for 300ms to reduce re-renders
2. **Memoized Filtering**: `filteredEntries` uses `useMemo` to avoid recalculation
3. **Infinite Scroll**: Catalog uses pagination to load items incrementally
4. **View Mode Persistence**: Saves to localStorage to avoid flickering on reload
5. **Deduplication**: Catalog entries deduplicated to prevent duplicate React keys

---

## Related Documentation

- **DirectoryMapModal Component**: `components/marketplace/DirectoryMapModal.tsx`
- **API Hooks**: `hooks/useMarketplaceSources.ts`
- **Types**: `types/marketplace.ts`
- **Backend API**: `skillmeat/api/app/routers/marketplace_sources.py`
- **Phase 4 Docs**: `.claude/worknotes/phase-4/toolbar-integration-summary.md`
