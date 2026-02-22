# Tag Mutation Patterns Analysis

## Overview

This document describes the patterns used throughout the SkillMeat web frontend for managing artifact tags, focusing on mutations, cache invalidation, and how the `/collection` and `/manage` pages handle tag updates.

---

## 1. Mutation Hook: `use-tags.ts`

**Location**: `skillmeat/web/hooks/use-tags.ts`

The core tag management hook provides query and mutation hooks for tags. Key functions:

### Query Hooks

| Hook | Purpose | Stale Time |
|------|---------|-----------|
| `useTags(limit?, after?)` | Fetch all tags with pagination | 5 minutes (standard browsing) |
| `useSearchTags(query, enabled?)` | Search tags by query string | 30 seconds (interactive) |
| `useArtifactTags(artifactId)` | Fetch tags for a specific artifact | 5 minutes (standard browsing) |

### Mutation Hooks

#### `useAddTagToArtifact()`

```typescript
const addTag = useAddTagToArtifact();
await addTag.mutateAsync({ artifactId, tagId });
```

**Cache Invalidation** (onSuccess):
```typescript
queryClient.invalidateQueries({ queryKey: tagKeys.artifact(artifactId) });
queryClient.invalidateQueries({ queryKey: ['artifacts'] });
queryClient.invalidateQueries({ queryKey: ['collections'] });
```

**Why these invalidations**:
- `tagKeys.artifact(artifactId)` — Refreshes artifact's tag list
- `['artifacts']` — Artifact list embeds tags for filtering/display
- `['collections']` — Collection page cards embed tags in browse cards

#### `useRemoveTagFromArtifact()`

```typescript
const removeTag = useRemoveTagFromArtifact();
await removeTag.mutateAsync({ artifactId, tagId });
```

**Cache Invalidation** (onSuccess): Same as add operation above

#### `useCreateTag()`

```typescript
const createTag = useCreateTag();
await createTag.mutateAsync({ name, slug, color });
```

**Cache Invalidation** (onSuccess):
```typescript
queryClient.invalidateQueries({ queryKey: tagKeys.all });
```

**Why**: Creates a new tag that may be applied by the user or discovered in searches.

#### `useUpdateTag()`

```typescript
const updateTag = useUpdateTag();
await updateTag.mutateAsync({ id, data: { name?, slug?, color? } });
```

**Cache Invalidation** (onSuccess):
```typescript
queryClient.invalidateQueries({ queryKey: tagKeys.all });
queryClient.invalidateQueries({ queryKey: ['artifacts'] });
queryClient.invalidateQueries({ queryKey: ['collections'] });
```

**Why**: Tag updates (e.g., color change) affect all artifacts with that tag and cards that display it.

#### `useDeleteTag()`

```typescript
const deleteTag = useDeleteTag();
await deleteTag.mutateAsync(tagId);
```

**Cache Invalidation** (onSuccess):
```typescript
queryClient.invalidateQueries({ queryKey: tagKeys.all });
queryClient.invalidateQueries({ queryKey: ['artifacts'] });
queryClient.invalidateQueries({ queryKey: ['collections'] });
queryClient.invalidateQueries({ queryKey: ['tags', 'artifact'] });
```

**Why**: Tag deletion affects global tag lists, artifacts, cards, and per-artifact tag queries.

---

## 2. Tag Selector Component: `tag-selector-popover.tsx`

**Location**: `skillmeat/web/components/collection/tag-selector-popover.tsx`

A reusable popover component for adding/removing tags from artifacts. Used in both collection and manage pages.

### Props

```typescript
interface TagSelectorPopoverProps {
  artifactId: string;        // Artifact ID to manage tags for
  trigger: React.ReactNode;  // The trigger element (typically the '+' button)
  onTagsChanged?: () => void; // Optional callback after tags are changed
}
```

### Usage Example (Collection Page)

```tsx
<TagSelectorPopover
  artifactId={artifact.id}
  trigger={
    <Button variant="ghost" size="icon" className="h-5 w-5 rounded-full">
      <Plus className="h-3 w-3" />
    </Button>
  }
/>
```

### Internal Logic

1. **Fetches Data**:
   - All available tags via `useTags(100)`
   - Artifact's applied tags via `useArtifactTags(artifactId)`
   - Only loads when popover is open

2. **Mutations**:
   - Uses `useAddTagToArtifact()` to add tags
   - Uses `useRemoveTagFromArtifact()` to remove tags
   - Uses `useCreateTag()` for inline tag creation

3. **Tag Toggle Flow**:
   ```typescript
   const handleToggle = async (tag: Tag) => {
     setPendingTagIds(prev => new Set(prev).add(tag.id));
     try {
       if (isCurrentlyApplied) {
         await removeTag.mutateAsync({ artifactId, tagId: tag.id });
       } else {
         await addTag.mutateAsync({ artifactId, tagId: tag.id });
       }
       onTagsChanged?.();
     } finally {
       setPendingTagIds(prev => {
         const next = new Set(prev);
         next.delete(tag.id);
         return next;
       });
     }
   };
   ```

4. **Inline Tag Creation**:
   - When search term doesn't match existing tag, shows "Create [tag]" option
   - Creates new tag with auto-generated slug and hash-based color
   - Automatically applies the new tag to the artifact

---

## 3. Collection Page: `/collection`

**Location**: `skillmeat/web/app/collection/page.tsx`

### Tag Display: `ArtifactBrowseCard`

**Location**: `skillmeat/web/components/collection/artifact-browse-card.tsx`

The card component used in grid/list views on the collection page displays tags and includes tag manipulation.

#### Tag Display Logic

```typescript
// Extract tools and display tags
const tools = extractToolsFromTags(artifact.tags);
const displayTags = extractDisplayTags(artifact.tags);
const sortedDisplayTags = [...displayTags].sort((a, b) => a.localeCompare(b));
const visibleTags = sortedDisplayTags.slice(0, 3);
const remainingTagsCount = sortedDisplayTags.length - visibleTags.length;
```

**Note**: Tool tags (matching known Tool enum values) are filtered out and displayed separately as platform/tool icons.

#### Tag Color Resolution

```typescript
// Fetch all tags to build a name->color map from DB
const { data: allTagsResponse } = useTags(100);
const dbTagColorMap = React.useMemo(() => {
  const map = new Map<string, string>();
  if (allTagsResponse?.items) {
    for (const tag of allTagsResponse.items) {
      if (tag.color) {
        map.set(tag.name, tag.color);
      }
    }
  }
  return map;
}, [allTagsResponse?.items]);

const resolveTagColor = (tagName: string): string => {
  return dbTagColorMap.get(tagName) || getTagColor(tagName);
};
```

**Why this pattern**:
- Prefers database-configured colors (if set)
- Falls back to deterministic hash-based colors for consistency
- Ensures visual stability across sessions

#### Tag Rendering

```tsx
<div className="flex min-h-[28px] flex-wrap items-center gap-1 px-4 pb-3">
  {visibleTags.map((tag) => (
    <Badge
      key={tag}
      colorStyle={resolveTagColor(tag)}
      className="text-xs"
      onClick={onTagClick ? (e) => {
        e.stopPropagation();
        onTagClick(tag);
      } : undefined}
    >
      {tag}
    </Badge>
  ))}
  {remainingTagsCount > 0 && (
    <Badge variant="secondary" className="text-xs">
      +{remainingTagsCount} more
    </Badge>
  )}
  <TagSelectorPopover
    artifactId={artifact.id}
    trigger={
      <Button variant="ghost" size="icon" className="h-5 w-5 rounded-full">
        <Plus className="h-3 w-3" />
      </Button>
    }
  />
</div>
```

#### Cache Invalidation on Collection Page

When `TagSelectorPopover` calls `useAddTagToArtifact()` or `useRemoveTagFromArtifact()`:

```typescript
// From use-tags.ts onSuccess handler
queryClient.invalidateQueries({ queryKey: tagKeys.artifact(artifactId) });
queryClient.invalidateQueries({ queryKey: ['artifacts'] });
queryClient.invalidateQueries({ queryKey: ['collections'] });
```

**Result**: The `ArtifactBrowseCard` will re-fetch artifact data through the `['artifacts']` query, causing the card to re-render with updated tags.

---

## 4. Manage Page: `/manage`

**Location**: `skillmeat/web/app/manage/page.tsx`

### Tag Display: `ArtifactOperationsModal`

**Location**: `skillmeat/web/components/manage/artifact-operations-modal.tsx`

The operations-focused modal shows tags in the "Overview" tab along with other artifact metadata.

#### Tag Section (Overview Tab)

```tsx
<div>
  <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
    <Tag className="h-4 w-4" aria-hidden="true" />
    Tags
  </h3>
  {isTagsLoading ? (
    <div className="flex items-center gap-1">
      <div className="h-5 w-16 animate-pulse rounded-md bg-muted" />
      <div className="h-5 w-12 animate-pulse rounded-md bg-muted" />
    </div>
  ) : (
    <div className="flex flex-wrap items-center gap-1.5">
      {[...(artifact.tags ?? [])].sort((a, b) => a.localeCompare(b)).map((tag) => (
        <Badge key={tag} colorStyle={getTagColor(tag)} className="text-xs">
          {tag}
        </Badge>
      ))}
      <TagSelectorPopover
        artifactId={artifact.id}
        trigger={
          <Button variant="outline" size="sm" className="h-6 w-6 rounded-full p-0">
            <Plus className="h-3 w-3" />
          </Button>
        }
      />
    </div>
  )}
</div>
```

#### Cache Invalidation on Manage Page

**Key difference from Collection page**: The modal receives the `artifact` prop from the parent page state, which is updated when queries are invalidated.

1. `TagSelectorPopover` calls `useAddTagToArtifact()` or `useRemoveTagFromArtifact()`
2. These mutations invalidate:
   - `tagKeys.artifact(artifactId)` — Artifact's tag list
   - `['artifacts']` — Full artifact list (includes entity list on manage page)
   - `['collections']` — Cross-page consistency

3. The `useEntityLifecycle()` hook (used in manage page) refetches the artifact, updating the modal's displayed data

#### Tag Selector Loading State

The modal shows a loading skeleton while tags are being fetched:

```typescript
const { isLoading: isTagsLoading } = useTags(100);
```

This prevents UI flicker and provides visual feedback during the fetch.

---

## 5. Entity Form Component: `entity-form.tsx`

**Location**: `skillmeat/web/components/entity/entity-form.tsx`

Used for both create and edit modes. Handles tag selection with different behaviors per mode.

### Create Mode

- Shows `TagInput` component with tag suggestions
- User selects tags before artifact creation
- Tags are applied as part of initial artifact creation (passed to API)
- No mutations needed during creation

### Edit Mode

- Shows `TagInput` component with currently applied tags
- Changes trigger mutations via `useAddTagToArtifact()` and `useRemoveTagFromArtifact()`
- Per-tag add/remove operations

#### Tag Change Handler (Edit Mode)

```typescript
const handleTagsChange = async (newTagIds: string[]) => {
  if (!entity?.id) {
    // In create mode, just update state
    setSelectedTagIds(newTagIds);
    return;
  }

  // In edit mode, apply changes to backend
  try {
    const added = newTagIds.filter((id) => !selectedTagIds.includes(id));
    const removed = selectedTagIds.filter((id) => !newTagIds.includes(id));

    for (const tagId of added) {
      await addTag.mutateAsync({ artifactId: entity.id, tagId });
    }
    for (const tagId of removed) {
      await removeTag.mutateAsync({ artifactId: entity.id, tagId });
    }

    setSelectedTagIds(newTagIds);
  } catch (err) {
    console.error('Failed to update tags:', err);
    setError(err instanceof Error ? err.message : 'Failed to update tags');
  }
};
```

---

## 6. Query Key Structure

From `use-tags.ts`:

```typescript
export const tagKeys = {
  all: ['tags'] as const,
  lists: () => [...tagKeys.all, 'list'] as const,
  list: (filters?: { limit?: number; after?: string }) =>
    [...tagKeys.lists(), filters] as const,
  search: (query: string) =>
    [...tagKeys.all, 'search', query] as const,
  artifact: (artifactId: string) =>
    [...tagKeys.all, 'artifact', artifactId] as const,
};
```

### Invalidation Strategy

| Query | Invalidated By | Reason |
|-------|---|---|
| `tagKeys.all` | `useCreateTag`, `useUpdateTag`, `useDeleteTag` | Global tag list changes |
| `tagKeys.artifact(id)` | `useAddTagToArtifact`, `useRemoveTagFromArtifact` | Artifact's tags changed |
| `['artifacts']` | All tag mutations | Artifact list contains tag data |
| `['collections']` | All tag mutations | Collection cards contain tag data |

---

## 7. Key Differences: Collection vs. Manage

| Aspect | Collection Page | Manage Page |
|--------|---|---|
| **Card Component** | `ArtifactBrowseCard` | `ArtifactOperationsModal` |
| **Tag Display** | Grid/list with 3 visible tags | Modal overview section |
| **Tag Interactions** | Click to filter, selector popover | Selector popover only |
| **Primary Purpose** | Discovery/browsing | Operations/monitoring |
| **Cache Invalidation** | Via `['artifacts']` and `['collections']` | Via `['artifacts']` and entity lifecycle |

### Cache Invalidation Flow

**Collection Page**:
1. TagSelectorPopover mutation fires
2. Invalidates `['artifacts']` and `['collections']`
3. Artifact list refetches
4. ArtifactBrowseCard component receives updated props
5. Card re-renders with new tags

**Manage Page**:
1. TagSelectorPopover mutation fires
2. Invalidates `['artifacts']` and `['collections']`
3. Entity list refetches via `useEntityLifecycle()`
4. Modal's artifact prop updates from parent state
5. Modal re-renders with new tags

---

## 8. Color Assignment Patterns

### Deterministic Hash-Based Colors

**File**: `skillmeat/web/lib/utils/tag-colors.ts`

Used for tags without explicit database colors:

```typescript
const getTagColor = (tagName: string): string => {
  // Hash-based color assignment for consistency
  // Same tag name always gets the same color across sessions
  // Falls back to a predefined color palette
};
```

### Database Colors

When a tag has an explicit `color` field set in the database, that color is always preferred:

```typescript
// In ArtifactBrowseCard:
const resolveTagColor = (tagName: string): string => {
  return dbTagColorMap.get(tagName) || getTagColor(tagName);
};
```

---

## 9. API Contract

### Endpoints Used

```
POST /api/v1/artifacts/{artifactId}/tags/{tagId}  — Add tag
DELETE /api/v1/artifacts/{artifactId}/tags/{tagId}  — Remove tag
GET /api/v1/tags  — List all tags
GET /api/v1/tags/{artifactId}  — Get artifact's tags
POST /api/v1/tags  — Create tag
PUT /api/v1/tags/{tagId}  — Update tag
DELETE /api/v1/tags/{tagId}  — Delete tag
```

**Important**: All artifact-tag operations use `artifact.id` (type:name format), not `artifact.uuid`. The API accepts both formats due to the dual-identity system (ADR-007).

---

## 10. Stale Time Configuration

All tag queries follow the standard stale time rules:

| Query Type | Stale Time | Reason |
|---|---|---|
| Tag lists (`useTags`) | 5 minutes | Standard browsing |
| Tag search (`useSearchTags`) | 30 seconds | Interactive search |
| Artifact tags (`useArtifactTags`) | 5 minutes | Standard browsing |

---

## 11. Common Patterns to Follow

When adding tag functionality to new components:

1. **Import hooks from barrel export**:
   ```typescript
   import { useTags, useAddTagToArtifact, useRemoveTagFromArtifact } from '@/hooks';
   ```

2. **Use TagSelectorPopover for mutations**:
   ```tsx
   <TagSelectorPopover
     artifactId={artifact.id}
     trigger={<Button>Add Tags</Button>}
   />
   ```

3. **Fetch all tags for color mapping**:
   ```typescript
   const { data: allTagsResponse } = useTags(100);
   ```

4. **Handle color resolution**:
   ```typescript
   const resolveTagColor = (tagName: string) =>
     dbTagColorMap.get(tagName) || getTagColor(tagName);
   ```

5. **Display tags sorted for consistency**:
   ```tsx
   {[...artifact.tags].sort((a, b) => a.localeCompare(b)).map(tag => ...)}
   ```

---

## 12. Related Files Summary

| File | Purpose |
|------|---------|
| `skillmeat/web/hooks/use-tags.ts` | Core query and mutation hooks |
| `skillmeat/web/lib/api/tags.ts` | API client functions |
| `skillmeat/web/components/collection/tag-selector-popover.tsx` | Reusable tag selector component |
| `skillmeat/web/components/collection/artifact-browse-card.tsx` | Card component for collection page |
| `skillmeat/web/components/manage/artifact-operations-modal.tsx` | Modal component for manage page |
| `skillmeat/web/components/entity/entity-form.tsx` | Form for creating/editing artifacts |
| `skillmeat/web/lib/utils/tag-colors.ts` | Tag color utilities |

