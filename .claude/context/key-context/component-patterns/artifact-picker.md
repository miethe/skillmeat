# Artifact Picker Pattern

Standard pattern for any UI that browses or selects artifacts (dialogs, dropdowns, pickers). Use `useInfiniteArtifacts` for server-side filtering and pagination.

## Core Rules

- Use `useInfiniteArtifacts` with server-side filters for any browse/select UI
- Use `useDebounce(search, 300)` for search inputs to avoid excessive API calls
- Use `useIntersectionObserver` for scroll-triggered loading in grid/list views
- Never use `useArtifacts({ limit: N })` where N > 50 for picker UIs
- Map API responses with `mapApiResponseToArtifact(item, 'collection')`

## Full Dialog Pattern (Grid with Scroll Loading)

```typescript
import { useMemo, useEffect } from 'react';
import { useInfiniteArtifacts, useIntersectionObserver, useDebounce } from '@/hooks';
import { mapApiResponseToArtifact } from '@/lib/api/mappers';

interface ArtifactPickerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (artifact: Artifact) => void;
}

export function ArtifactPickerDialog({
  open,
  onOpenChange,
  onSelect,
}: ArtifactPickerDialogProps) {
  const [search, setSearch] = useState('');
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set());

  // Debounce search to reduce API calls
  const debouncedSearch = useDebounce(search, 300);

  // Fetch artifacts with filters
  const { data, isLoading, isFetchingNextPage, hasNextPage, fetchNextPage } =
    useInfiniteArtifacts({
      limit: 20,
      search: debouncedSearch || undefined,
      artifact_type: selectedTypes.size > 0
        ? Array.from(selectedTypes).join(',')
        : undefined,
      enabled: open,
    });

  // Map API responses to artifact types
  const items = useMemo(() => {
    if (!data?.pages) return [];
    return data.pages.flatMap((page) =>
      page.items.map((item) => mapApiResponseToArtifact(item, 'collection'))
    );
  }, [data]);

  // Intersection observer for scroll-triggered loading
  const { targetRef, isIntersecting } = useIntersectionObserver({
    rootMargin: '100px',
    enabled: !!hasNextPage && !isFetchingNextPage,
  });

  // Fetch next page when sentinel becomes visible
  useEffect(() => {
    if (isIntersecting) fetchNextPage();
  }, [isIntersecting, fetchNextPage]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Select Artifact</DialogTitle>
        </DialogHeader>

        {/* Search input */}
        <input
          type="text"
          placeholder="Search artifacts..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="px-4 py-2 border rounded-md"
        />

        {/* Type filters */}
        <div className="flex gap-2">
          {['skill', 'command', 'agent'].map((type) => (
            <button
              key={type}
              onClick={() => {
                const next = new Set(selectedTypes);
                if (next.has(type)) next.delete(type);
                else next.add(type);
                setSelectedTypes(next);
              }}
              className={cn(
                'px-3 py-1 rounded-full text-sm',
                selectedTypes.has(type)
                  ? 'bg-primary text-primary-foreground'
                  : 'border'
              )}
            >
              {type}
            </button>
          ))}
        </div>

        {/* Scrollable artifact grid */}
        <div className="flex-1 overflow-y-auto space-y-2">
          {isLoading ? (
            <div className="text-center py-8">Loading...</div>
          ) : items.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No artifacts found
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-2">
              {items.map((item) => (
                <div
                  key={item.id}
                  className="p-3 border rounded-md cursor-pointer hover:bg-accent"
                  onClick={() => onSelect(item)}
                >
                  <div className="font-medium text-sm">{item.name}</div>
                  <div className="text-xs text-muted-foreground">{item.type}</div>
                </div>
              ))}
            </div>
          )}

          {/* Sentinel for scroll-triggered loading */}
          {hasNextPage && <div ref={targetRef} className="h-1" />}
        </div>

        {isFetchingNextPage && (
          <div className="text-center py-2 text-sm text-muted-foreground">
            Loading more...
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
```

## Dropdown/Autocomplete Pattern (First Page Only)

For compact UI where you only show the first page of results:

```typescript
import { useMemo } from 'react';
import { useInfiniteArtifacts, useDebounce } from '@/hooks';
import { mapApiResponseToArtifact } from '@/lib/api/mappers';

export function ArtifactSearchDropdown({ onSelect }: Props) {
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, 300);

  // Only fetch on demand, first page only
  const { data, isLoading } = useInfiniteArtifacts({
    limit: 10,
    search: debouncedQuery || undefined,
    enabled: debouncedQuery.length >= 1,
  });

  const items = useMemo(() => {
    if (!data?.pages) return [];
    return data.pages.flatMap((page) =>
      page.items.map((item) => mapApiResponseToArtifact(item, 'collection'))
    );
  }, [data]);

  return (
    <div className="relative">
      <input
        type="text"
        placeholder="Search..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      {query && (
        <div className="absolute top-full mt-2 w-full border rounded-md bg-popover shadow-lg">
          {isLoading ? (
            <div className="p-2 text-sm text-muted-foreground">Loading...</div>
          ) : items.length === 0 ? (
            <div className="p-2 text-sm text-muted-foreground">No results</div>
          ) : (
            <ul className="py-1">
              {items.map((item) => (
                <li
                  key={item.id}
                  className="px-3 py-2 cursor-pointer hover:bg-accent text-sm"
                  onClick={() => onSelect(item)}
                >
                  {item.name}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
```

## Reference Implementations

- **Full dialog with scroll**: `skillmeat/web/components/deployment-sets/add-member-dialog.tsx`
- **Dropdown search**: `skillmeat/web/components/shared/member-search-input.tsx`
- **Collection page (original)**: `skillmeat/web/app/collection/page.tsx`

## Hook Details

### useInfiniteArtifacts

Infinite query hook for artifact browsing.

**Props:**
- `limit: number` - Items per page (20-50 recommended)
- `search?: string` - Search query (filtered server-side)
- `artifact_type?: string` - Comma-separated type filter (e.g., 'skill,command')
- `enabled?: boolean` - Enable/disable the query

**Returns:**
- `data?.pages` - Array of pages, each with `items` and `nextCursor`
- `isLoading` - Initial load state
- `isFetchingNextPage` - Currently fetching next page
- `hasNextPage` - More pages available
- `fetchNextPage()` - Load next page

### useDebounce

Debounce a value to reduce API call frequency.

**Props:**
- `value: T` - Value to debounce
- `delay: number` - Delay in milliseconds (300-500 recommended)

**Returns:**
- Debounced value (unchanged while typing, updates after delay)

### useIntersectionObserver

Detect when a DOM element becomes visible (for infinite scroll).

**Props:**
- `rootMargin?: string` - Trigger before element is fully visible (e.g., '100px')
- `enabled?: boolean` - Enable/disable observation

**Returns:**
- `targetRef` - Ref to attach to sentinel element
- `isIntersecting` - Currently visible in viewport
