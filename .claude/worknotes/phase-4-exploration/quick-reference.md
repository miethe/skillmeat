# Collection Page - Quick Reference

## Problem Statement
The `/collection` page shows artifact cards with metadata (description, tags), but the collection-specific API endpoint only returns lightweight summaries (name, type, version, source). Metadata enrichment is required.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Collection Page (/collection)                   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                   ┌──────────┴──────────┐
                   │                     │
          ┌────────▼────────┐   ┌───────▼───────┐
          │ Specific View   │   │ All Collections│
          │ (Collection ID) │   │ (No ID)        │
          └────────┬────────┘   └───────┬───────┘
                   │                     │
        ┌──────────▼──────────┐   ┌──────▼───────┐
        │useInfiniteCollection│   │useInfinite   │
        │Artifacts()          │   │Artifacts()   │
        └──────────┬──────────┘   └──────┬───────┘
                   │                     │
        ┌──────────▼──────────┐   ┌──────▼───────┐
        │/user-collections/  │   │/artifacts    │
        │{id}/artifacts      │   │(full data)   │
        │(summaries only)     │   │              │
        └──────────┬──────────┘   └──────┬───────┘
                   │                     │
                   │       ┌─────────────┘
                   │       │
                   ▼       ▼
             ┌──────────────────┐
             │enrichArtifact    │
             │Summary()         │ Match by name+type
             └────────┬─────────┘
                      │
            ┌─────────┴────────┐
            │                  │
        ┌───▼────┐      ┌─────▼──┐
        │ Found? │      │Fallback│
        │ Use it │      │Empty   │
        └────────┘      │metadata│
                        └────────┘
```

## Key Files

### Core Page & Logic
- **`/collection/page.tsx`** (869 lines)
  - `enrichArtifactSummary()` - Enriches summaries with full metadata
  - Dual-fetch pattern for specific collections
  - Client-side filtering, search, sort

- **`/manage/page.tsx`** (263 lines)
  - Simple single-fetch approach
  - Uses EntityLifecycleProvider
  - Gets full data directly

### Hooks
- **`/hooks/use-collections.ts`**
  - `useInfiniteCollectionArtifacts()` - Line 263
  - Query key: `['collections', 'detail', collectionId, 'infinite-artifacts', options]`
  - Endpoint: `/user-collections/{id}/artifacts`

- **`/hooks/useArtifacts.ts`**
  - `useInfiniteArtifacts()` - Line 612
  - Query key: `['artifacts', 'infinite', filters]`
  - Endpoint: `/artifacts`

- **`/hooks/useEntityLifecycle.tsx`**
  - `fetchCollectionEntities()` - Line 628
  - Gets full artifacts from `/artifacts`
  - Used by /manage page

### Context & State
- **`/context/collection-context.tsx`**
  - Manages selected collection ID (localStorage)
  - Fetches collection list and groups
  - Provides to whole app via CollectionProvider

### API Functions
- **`/lib/api/collections.ts`**
  - `fetchCollectionArtifactsPaginated()` - Line 217
  - Returns: `ArtifactSummary[]` (minimal data)

- **`/lib/api/artifacts.ts`**
  - `fetchArtifactsPaginated()`
  - Returns: `Artifact[]` (full data)

### Types
- **`/types/collections.ts`**
  - `Collection` - Collection metadata
  - `ArtifactSummary` - Lightweight artifact reference
  - `CollectionArtifactsResponse` - Paginated response

- **`/types/artifact.ts`**
  - `Artifact` - Full artifact with metadata
  - `ArtifactMetadata` - Nested metadata object
  - `ArtifactFilters` - Filter options

## Critical Code Locations

### Enrichment Logic (collection/page.tsx)
```
Lines 45-97:   enrichArtifactSummary() function
Lines 308-352: filteredArtifacts memo (core filtering + enrichment)
Lines 488-505: Enrichment in specific collection view
```

### Fetching Strategy
```
Lines 310-322: useInfiniteCollectionArtifacts (specific collection)
Lines 325-338: useInfiniteArtifacts (all collections - always runs)
Lines 341-351: Unified pagination state
```

### Data Mapping
```
Lines 391-479: mapApiArtifactToArtifact() - Maps API response to Artifact type
Lines 482-587: filteredArtifacts - Combines both data sources
```

## How Metadata Gets There

### Route 1: Specific Collection (With Enrichment)
1. User selects a collection (e.g., "Design Tools")
2. `selectedCollectionId = "design-tools"`
3. `useInfiniteCollectionArtifacts("design-tools")` fetches lightweight summaries
4. `useInfiniteArtifacts()` **always runs** and fetches full artifacts
5. `enrichArtifactSummary()` matches summaries to full artifacts by name+type
6. Metadata comes from matched full artifact
7. If no match found, metadata defaults to empty strings/arrays

### Route 2: All Collections (Direct, No Enrichment)
1. User doesn't select a collection (or selects "all")
2. `selectedCollectionId = null`
3. `useInfiniteCollectionArtifacts()` disabled
4. `useInfiniteArtifacts()` runs and returns full artifacts
5. No enrichment needed - metadata already present

## Query Keys & Cache

### Collection Artifacts
```
Key: ['collections', 'detail', 'design-tools', 'infinite-artifacts', { artifact_type: 'skill' }]
Stale Time: 5 minutes
Endpoint: /user-collections/design-tools/artifacts?artifact_type=skill&limit=20
```

### All Artifacts
```
Key: ['artifacts', 'infinite', { artifact_type: 'skill' }]
Stale Time: 5 minutes
Endpoint: /artifacts?artifact_type=skill&limit=20
```

**Note**: Separate cache keys mean no automatic invalidation between the two data sources.

## API Response Shapes

### Collection Artifacts (Lightweight)
```json
{
  "items": [
    {
      "name": "canvas-design",
      "type": "skill",
      "version": "v2.1.0",
      "source": "skill:canvas-design"
    }
  ],
  "page_info": {
    "total_count": 5,
    "has_next_page": false,
    "end_cursor": null
  }
}
```

### All Artifacts (Full)
```json
{
  "items": [
    {
      "id": "canvas-design",
      "name": "canvas-design",
      "type": "skill",
      "source": "anthropics/skills/canvas-design",
      "version": "v2.1.0",
      "metadata": {
        "title": "Canvas Design",
        "description": "Create and edit visual designs...",
        "author": "Anthropic",
        "license": "MIT",
        "tags": ["design", "visual", "canvas"]
      },
      "added": "2024-11-01T...",
      "updated": "2024-11-15T..."
    }
  ],
  "page_info": { ... }
}
```

## Comparison: /collection vs /manage

| Feature | /collection | /manage |
|---------|-----------|---------|
| **Endpoint** | /user-collections/{id}/artifacts + /artifacts | /artifacts |
| **Fetches** | 2 queries (unless "All Collections") | 1 query |
| **Data Shape** | Lightweight + Full | Full |
| **Enrichment** | Manual via enrichArtifactSummary() | None needed |
| **Metadata Source** | Joined from full artifacts | Direct from API |
| **Pagination** | Infinite scroll | Single page (100 items) |
| **Hook** | useInfiniteCollectionArtifacts + useInfiniteArtifacts | useEntityLifecycle |

## Why /manage Works but /collection Might Not

**`/manage` page**:
- Doesn't use collection-specific endpoint
- Always fetches `/artifacts` endpoint
- Gets full metadata directly
- Simple single-source pattern

**`/collection` page**:
- Fetches collection-specific summaries
- Must enrich with full artifact data
- Enrichment depends on name+type match
- If match fails → empty metadata

## Potential Issues

1. **Missing Metadata**: If full artifact not found in catalog, description/tags are empty
2. **Synthetic Source**: Backend returns `"type:name"` as source when real source unavailable
3. **Cache Misalignment**: No automatic invalidation between collection and artifact caches
4. **Always-On Fetch**: `useInfiniteArtifacts()` runs even in "All Collections" view (slight redundancy)
5. **Pagination Limits**: Each infinite scroll page loads 20 items; matching 20 summaries to full catalog could be slow if catalog is large

## Debug Checklist

- [ ] Check if artifact summary includes real `source` or synthetic `"type:name"`
- [ ] Verify enrichment is finding matches (add console.log in enrichArtifactSummary)
- [ ] Check TanStack Query DevTools for cache keys and stale status
- [ ] Verify `mapApiArtifactToArtifact()` is correctly parsing metadata
- [ ] Check if collection contains artifacts that exist in the catalog
- [ ] Test with "All Collections" view to isolate enrichment from pagination

## Next Steps

To fix metadata loading issues:

1. **Backend**: Ensure collection artifacts response includes real `source` field
2. **Backend**: Optionally return metadata in collection artifacts response (avoid enrichment)
3. **Frontend**: Improve enrichment matching (handle aliases, normalize names)
4. **Frontend**: Add logging to track enrichment failures
5. **Frontend**: Consider caching strategy for artifact catalog refresh
