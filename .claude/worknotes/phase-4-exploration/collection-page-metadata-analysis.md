# Collection Page Metadata Loading - Deep Exploration

## Summary

The `/collection` page implements a dual-fetch pattern to handle artifact metadata enrichment, but there's a critical architectural difference between how it handles specific collections vs "All Collections" view. The issue stems from metadata availability in different API responses.

## Key Finding: Two Different Response Shapes

### Specific Collection View (Lightweight Summaries)
- **Endpoint**: `/user-collections/{id}/artifacts`
- **Response Type**: `ArtifactSummary` (lightweight)
- **Contains**: `name`, `type`, `version`, `source` **ONLY**
- **Missing**: All metadata (description, tags, title, author, license)
- **Pagination**: Cursor-based with `page_info`

**File**: `/skillmeat/web/lib/api/collections.ts:217-240`
```typescript
// ArtifactSummary interface (minimal data)
export interface CollectionArtifactsPaginatedResponse {
  items: Array<{
    name: string;
    type: string;
    version?: string | null;
    source: string;  // THIS IS SYNTHETIC: "type:name" format if missing
  }>;
  page_info: { ... }
}
```

### All Collections View (Full Artifacts)
- **Endpoint**: `/artifacts`
- **Response Type**: `Artifact` (full data)
- **Contains**: All metadata fields (description, tags, title, author, license, metadata object)
- **Pagination**: Cursor-based with `page_info`

**File**: `/skillmeat/web/hooks/useArtifacts.ts:47-70`
```typescript
interface ApiArtifact {
  id: string;
  name: string;
  type: ArtifactType;
  source: string;
  metadata?: {
    title?: string;
    description?: string;
    license?: string;
    author?: string;
    version?: string;
    tags?: string[];
  };
  upstream?: ApiArtifactUpstream;
  // ... more fields
}
```

## The Enrichment Strategy (Lines 45-97 in collection/page.tsx)

The `/collection` page uses `enrichArtifactSummary()` to solve the metadata problem:

```typescript
function enrichArtifactSummary(
  summary: { name: string; type: string; version?: string | null; source: string },
  allArtifacts: Artifact[],
  collectionInfo?: { id: string; name: string }
): Artifact {
  // 1. Find matching artifact in full catalog
  const fullArtifact = allArtifacts.find((a) =>
    a.name === summary.name && a.type === summary.type
  );

  if (fullArtifact) {
    // Use full artifact and attach collection context
    if (collectionInfo && !fullArtifact.collection) {
      return { ...fullArtifact, collection: collectionInfo };
    }
    return fullArtifact;
  }

  // Fallback: Convert summary to artifact-like structure with defaults
  return {
    id: `${summary.type}:${summary.name}`,
    name: summary.name,
    type: summary.type,
    source: isSourceMissingOrSynthetic ? undefined : summary.source,
    metadata: {
      title: summary.name,
      description: '', // EMPTY!
      tags: [],        // EMPTY!
    },
    // ... other defaults
  };
}
```

### Key Issue: Source Field Detection (Lines 65-67)

The page detects when `source` is synthetic and clears it:

```typescript
const isSourceMissingOrSynthetic =
  !summary.source ||
  summary.source === artifactId ||           // "skill:canvas-design"
  summary.source === summary.name;           // "canvas-design"
```

**Problem**: The backend may be returning `source` in `"type:name"` format when the real source is missing from the collection artifact data.

## Data Fetching Pattern (Lines 310-338)

### For Specific Collection
```typescript
const {
  data: infiniteCollectionData,
  fetchNextPage: fetchNextCollectionPage,
  hasNextPage: hasNextCollectionPage,
} = useInfiniteCollectionArtifacts(
  isSpecificCollection ? selectedCollectionId : undefined,
  { limit: 20, enabled: isSpecificCollection }
);
```

### For All Collections (Always Runs)
```typescript
const {
  data: infiniteAllArtifactsData,
  fetchNextPage: fetchNextAllPage,
  hasNextPage: hasNextAllPage,
} = useInfiniteArtifacts({
  limit: 20,
  artifact_type: filters.type !== 'all' ? filters.type : undefined,
  enabled: true,  // ALWAYS enabled
});
```

**Critical Detail**: The "All Collections" fetch runs regardless of selected view. This means the page **always loads the full artifact catalog** to enrich specific collection artifacts.

## Comparison with /manage Page

The `/manage` page (manage/page.tsx) uses a **completely different architecture**:

### Manage Page Strategy
1. Uses `EntityLifecycleProvider` (useEntityLifecycle hook)
2. Fetches from `/artifacts` endpoint only (never collection-specific endpoint)
3. Gets **full artifact data with metadata** directly
4. No enrichment needed - metadata is always present
5. No dual-fetch pattern

**File**: `/skillmeat/web/hooks/useEntityLifecycle.tsx:628-668`
```typescript
async function fetchCollectionEntities(
  typeFilter: EntityType | null,
  searchQuery: string,
  collectionId?: string
): Promise<Entity[]> {
  const params = new URLSearchParams({ limit: '100' });
  if (typeFilter) {
    params.set('artifact_type', typeFilter);
  }

  // Fetches from /artifacts endpoint, gets FULL data including metadata
  const response = await apiRequest<ArtifactListResponse>(
    `/artifacts?${params.toString()}`
  );

  const entities = response.items.map((item) =>
    mapApiArtifactToEntity(item, 'collection', undefined, collectionId)
  );
  // ...
}
```

### Key Differences

| Aspect | /collection | /manage |
|--------|-----------|---------|
| **Hook** | `useInfiniteCollectionArtifacts` + `useInfiniteArtifacts` | `useEntityLifecycle` |
| **Endpoints** | `/user-collections/{id}/artifacts` + `/artifacts` | `/artifacts` only |
| **Data Shape** | Lightweight + Full | Full |
| **Metadata** | Requires enrichment | Direct (no enrichment) |
| **Pagination** | Infinite scroll (cursor) | Single page (limit: 100) |
| **Cache Mode** | Infinite queries | Standard query |
| **Filtering** | Client-side after fetch | Client-side after fetch |

## Pagination & Cache Configuration

### Collection Hooks (useCollections.ts)

**useInfiniteCollectionArtifacts**:
```typescript
export const collectionKeys = {
  infiniteArtifacts: (id: string, options?: { artifact_type?: string }) =>
    [...collectionKeys.detail(id), 'infinite-artifacts', options] as const,
};

return useInfiniteQuery({
  queryKey: collectionKeys.infiniteArtifacts(id!, { artifact_type }),
  queryFn: async ({ pageParam }) =>
    fetchCollectionArtifactsPaginated(id!, {
      limit,
      after: pageParam,
      artifact_type,
    }),
  initialPageParam: undefined as string | undefined,
  getNextPageParam: (lastPage) =>
    lastPage.page_info.has_next_page ? lastPage.page_info.end_cursor : undefined,
  enabled: !!id && enabled,
  staleTime: 5 * 60 * 1000,  // 5 minutes
});
```

**useInfiniteArtifacts** (useArtifacts.ts):
```typescript
return useInfiniteQuery({
  queryKey: ['artifacts', 'infinite', filters],
  queryFn: async ({ pageParam }) =>
    fetchArtifactsPaginated({
      limit,
      after: pageParam,
      artifact_type: filters.artifact_type,
      status: filters.status,
      scope: filters.scope,
      search: filters.search,
    }),
  initialPageParam: undefined as string | undefined,
  getNextPageParam: (lastPage) =>
    lastPage.page_info.has_next_page ? lastPage.page_info.end_cursor : undefined,
  enabled,
  staleTime: 5 * 60 * 1000,  // 5 minutes
});
```

## The Metadata Issue: Root Cause

Looking at the backend (based on API contract), the collection artifact response returns:

```json
{
  "items": [
    {
      "name": "canvas-design",
      "type": "skill",
      "version": "v2.1.0",
      "source": "skill:canvas-design"  // SYNTHETIC if real source missing!
    }
  ],
  "page_info": { ... }
}
```

The `source` field is being set to the synthetic `type:name` format by the backend when:
1. The artifact summary doesn't have the real source
2. The backend generates it as a fallback ID

**Collection artifact summary is missing metadata because**:
- The collection stores lightweight references (name, type, version)
- Metadata lives on the full Artifact object in the catalog
- The collection endpoint doesn't JOIN with artifact metadata
- Must fetch full artifacts from `/artifacts` to get metadata

## Flow Diagram

```
Collection Page Load
│
├─ View: Specific Collection
│  ├─ useInfiniteCollectionArtifacts('/user-collections/{id}/artifacts')
│  │  └─ Returns: [ArtifactSummary, ...] (no metadata)
│  │
│  └─ useInfiniteArtifacts('/artifacts')
│     ├─ Returns: [Artifact, ...] (with metadata)
│     │
│     └─ enrichArtifactSummary(summary, allArtifacts)
│        ├─ Match by name+type
│        └─ Fallback: Empty metadata if no match
│
└─ View: All Collections
   └─ useInfiniteArtifacts('/artifacts') only
      └─ Returns: [Artifact, ...] (with metadata, ready to display)
```

## Caching Implications

Both hooks use **separate cache keys**:
- `['collections', 'detail', 'collection-id', 'infinite-artifacts', { artifact_type }]`
- `['artifacts', 'infinite', { ... }]`

This means:
1. Changes to collection membership don't invalidate artifact metadata cache
2. Changes to artifact metadata don't invalidate collection artifact cache
3. No automatic cache sync between the two data sources
4. Manual `refetch()` required after mutations

## TanStack Query Configuration

### Stale Time: 5 minutes (both)
- Fresh data within 5 minutes
- Old data used from cache after 5 minutes stale

### GC Time: 30 minutes (implicit default)
- Cached queries removed after 30 minutes of no access
- Prevents unbounded memory growth

### Enabled Strategy
- Specific collection: `enabled: !!id && enabled`
- All artifacts: `enabled: true` (always fetches to support enrichment)

## Import/Export Patterns

### Collection Page (page.tsx)
```typescript
import {
  useCollectionContext,
  useInfiniteArtifacts,
  useInfiniteCollectionArtifacts,
  // ... other hooks
} from '@/hooks';
```

### Hooks Index (hooks/index.ts)
All hooks are exported from a barrel export for centralized management.

### API Client Functions
- `fetchCollectionArtifactsPaginated()` - collections.ts
- `fetchArtifactsPaginated()` - artifacts.ts
- Both use cursor-based pagination

## Related Type Files

### Type: Artifact (types/artifact.ts)
- Full artifact with metadata and collections
- Supports both single collection and array of collections

### Type: Collection (types/collections.ts)
- Represents collection metadata only
- Uses `ArtifactSummary` for artifacts in response

### Type: Entity (types/entity.ts)
- Used by /manage page
- Maps both Artifact and project deployments to unified entity type

## Summary of Files

| File | Purpose | Key Function |
|------|---------|--------------|
| `/collection/page.tsx` | Main page component | `enrichArtifactSummary()`, dual-fetch pattern |
| `/manage/page.tsx` | Entity management page | Single query, full metadata |
| `/hooks/use-collections.ts` | Collection queries | `useInfiniteCollectionArtifacts()` |
| `/hooks/useArtifacts.ts` | Artifact queries | `useInfiniteArtifacts()` |
| `/hooks/useEntityLifecycle.tsx` | Entity management | `useEntityLifecycle()` hook |
| `/context/collection-context.tsx` | Collection selection state | Selected collection ID persistence |
| `/lib/api/collections.ts` | API client | `fetchCollectionArtifactsPaginated()` |
| `/lib/api/artifacts.ts` | API client | `fetchArtifactsPaginated()` |
| `/types/artifact.ts` | Type definitions | `Artifact`, `ArtifactSummary` |
| `/types/collections.ts` | Type definitions | `Collection`, `ArtifactSummary` |

## What Works vs. What's Missing

### Works
- View switches between specific collection and all collections
- Infinite scroll pagination for both views
- Search and filtering on client-side
- Tag-based filtering
- Sort by confidence, name, updated, usage

### Missing/Issues
- Metadata for specific collection artifacts comes only from enrichment match
- If full artifact not found in catalog, metadata is empty defaults
- No automatic cache synchronization between collection and artifact data
- Backend may return synthetic source IDs instead of real sources
