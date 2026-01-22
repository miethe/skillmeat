# Collection Page Implementation - Complete File Manifest

## Absolute File Paths & Purposes

### Pages
- **`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/collection/page.tsx`** (869 lines)
  - Main collection page component
  - Dual-fetch pattern (specific collection + all artifacts)
  - Enrichment logic via `enrichArtifactSummary()`
  - Handles grid/list view switching, infinite scroll
  - Key functions:
    - `enrichArtifactSummary()` (lines 45-97) - Enriches lightweight summaries with metadata
    - `artifactToEntity()` (lines 99-148) - Converts for modal display
    - `mapApiArtifactToArtifact()` (lines 391-479) - API response mapping
    - `filteredArtifacts` memo (lines 482-587) - Core filtering + enrichment

- **`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/manage/page.tsx`** (263 lines)
  - Entity management page (for comparison)
  - Uses EntityLifecycleProvider (simpler pattern)
  - Single endpoint fetch (`/artifacts`)
  - Full metadata available directly

### Hooks (Data Fetching)

- **`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/use-collections.ts`** (448 lines)
  - `useCollections()` - Fetch all collections
  - `useCollection()` - Fetch single collection by ID
  - `useCollectionArtifacts()` - Fetch collection artifacts (paginated, non-infinite)
  - `useInfiniteCollectionArtifacts()` (line 263) - **Infinite scroll for specific collection**
    - Returns: Lightweight `ArtifactSummary[]`
    - Endpoint: `/user-collections/{id}/artifacts`
    - Query key: `['collections', 'detail', collectionId, 'infinite-artifacts', options]`
    - Cache: 5 minute staleTime
  - Mutations: create, update, delete collection
  - Mutations: add/remove artifact from collection

- **`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/useArtifacts.ts`** (634 lines)
  - `useArtifacts()` - Single-page fetch with filtering
  - `useArtifact()` - Fetch single artifact by ID
  - `useUpdateArtifact()` - Update artifact mutation
  - `useDeleteArtifact()` - Delete artifact mutation
  - `useInfiniteArtifacts()` (line 612) - **Infinite scroll for all artifacts**
    - Returns: Full `Artifact[]` with metadata
    - Endpoint: `/artifacts`
    - Query key: `['artifacts', 'infinite', filters]`
    - Cache: 5 minute staleTime
    - Always enabled to support enrichment

- **`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/useEntityLifecycle.tsx`** (825 lines)
  - `EntityLifecycleProvider` - Context provider for entity management
  - `useEntityLifecycle()` - Hook to access entity lifecycle
  - `fetchCollectionEntities()` (line 628) - Fetches full artifacts (used by /manage)
  - `fetchProjectEntities()` (line 670) - Fetches project-specific entities
  - Mock data generators for development fallback

- **`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/use-collection-context.ts`** (49 lines)
  - `useCollectionContext()` - Hook to access collection context
  - Simple context accessor, no complex logic

### Context
- **`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/context/collection-context.tsx`** (150+ lines)
  - `CollectionProvider` - Context provider for collection state
  - Manages selected collection ID (with localStorage persistence)
  - Fetches collections list and groups
  - Key state:
    - `selectedCollectionId` - Current selected collection
    - `collections` - All available collections
    - `currentCollection` - Details of selected collection
    - `currentGroups` - Groups in selected collection

### API Client Functions

- **`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/lib/api/collections.ts`** (240+ lines)
  - `fetchCollections()` - Get all collections
  - `fetchCollection()` - Get single collection
  - `createCollection()` - Create new collection
  - `updateCollection()` - Update collection metadata
  - `deleteCollection()` - Delete collection
  - `addArtifactToCollection()` - Add artifact to collection
  - `removeArtifactFromCollection()` - Remove artifact from collection
  - `fetchCollectionArtifactsPaginated()` (line 217) - **Core function for specific collection artifacts**
    - Returns cursor-based paginated response
    - Response: `CollectionArtifactsPaginatedResponse` with lightweight summaries

- **`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/lib/api/artifacts.ts`** (150+ lines, estimate)
  - `fetchArtifactsPaginated()` - Core function for all artifacts
  - `apiRequest()` - Centralized HTTP client
  - API configuration and error handling

### Types & Interfaces

- **`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/types/collections.ts`** (92 lines)
  - `Collection` - Collection metadata
  - `CreateCollectionRequest` - Creation input
  - `UpdateCollectionRequest` - Update input
  - `ArtifactGroupMembership` - Group reference in artifact
  - `ArtifactSummary` (line 56) - **Lightweight artifact in collection**
    - Fields: name, type, version, source, groups
    - Missing: metadata (description, tags, author, license)
  - `CollectionListResponse` - Paginated collections
  - `CollectionArtifactsResponse` - Paginated collection artifacts

- **`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/types/artifact.ts`** (105 lines)
  - `ArtifactType` - Type union (skill, command, agent, mcp, hook)
  - `ArtifactScope` - Scope union (user, local)
  - `ArtifactStatus` - Status union (active, outdated, conflict, error)
  - `ArtifactMetadata` (line 13) - **Metadata object**
    - Fields: title, description, license, author, version, tags
  - `Artifact` (line 46) - **Full artifact with metadata**
  - `UpstreamStatus` - Upstream tracking info
  - `UsageStats` - Usage tracking
  - `ArtifactScore` - Confidence scoring
  - `ArtifactFilters` - Filter options
  - `ArtifactSort` - Sort options

- **`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/types/entity.ts`** (estimate 150+ lines)
  - `Entity` - Unified entity type (used by /manage page)
  - Maps both Artifact and ProjectDeployment to single type
  - `EntityType`, `EntityStatus` - Type unions

### Components (Related)

- **`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/collection/artifact-grid.tsx`** - Grid view for artifacts
- **`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/collection/artifact-list.tsx`** - List view for artifacts
- **`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/collection/collection-header.tsx`** - Page header
- **`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/collection/collection-toolbar.tsx`** - Filter/search toolbar
- **`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/entity/unified-entity-modal.tsx`** - Detail modal for artifact
- **`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/entity/artifact-deletion-dialog.tsx`** - Delete confirmation
- **`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/entity/EntityLifecycleProvider.tsx`** - Provider component for /manage page

### Hooks (Other)

- **`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/use-intersection-observer.ts`** - Infinite scroll trigger
- **`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/useEditArtifactParameters.ts`** - Parameter editor mutation
- **`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/index.ts`** - Barrel export (canonical import point)

### Utilities

- **`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/lib/utils.ts`** - Utility functions (cn, etc.)
- **`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/lib/api/index.ts`** - API client setup and exports

## Data Flow Summary

```
Collection Page Load
│
├─ Collection Selected
│  ├─ useCollection(selectedCollectionId)
│  │  └─ Fetch /user-collections/{id}
│  │     └─ Response: Collection metadata
│  │
│  ├─ useInfiniteCollectionArtifacts(selectedCollectionId)
│  │  └─ Fetch /user-collections/{id}/artifacts?limit=20
│  │     └─ Response: ArtifactSummary[] (lightweight)
│  │
│  └─ useInfiniteArtifacts() [always runs]
│     └─ Fetch /artifacts?limit=20
│        └─ Response: Artifact[] (with metadata)
│
├─ filteredArtifacts memo
│  ├─ Flatten infiniteCollectionData pages
│  ├─ enrichArtifactSummary(summary, allArtifacts)
│  │  ├─ Match by name + type
│  │  └─ Fallback: Empty metadata
│  └─ Apply filters (search, tags, sort)
│
└─ Render artifacts with metadata
   ├─ Grid or List view
   └─ Cards show description, tags, etc.
```

## Key Query Keys for Debugging

```
Collections list:
  ['collections', 'list', filters]

Specific collection detail:
  ['collections', 'detail', 'design-tools']

Collection artifacts (infinite):
  ['collections', 'detail', 'design-tools', 'infinite-artifacts', { artifact_type: 'skill' }]

All artifacts (infinite):
  ['artifacts', 'infinite', { artifact_type: 'skill' }]

Context entities (manage page):
  ['entities', 'collection', undefined, null, null, '']
```

## Important Configuration Values

- **Infinite scroll page size**: 20 items
- **Intersection observer margin**: 200px (lines 348-351 in collection/page.tsx)
- **Fetch page size for /manage**: 100 items (useEntityLifecycle.tsx line 634)
- **TanStack Query staleTime**: 5 minutes (both collection and artifact hooks)
- **TanStack Query gcTime**: 30 minutes (implicit)
- **Collection storage key**: `'skillmeat-selected-collection'` (collection-context.tsx line 40)

## How to Find Specific Logic

| Need | File | Location |
|------|------|----------|
| Metadata enrichment | collection/page.tsx | 45-97 |
| Infinite scroll trigger | collection/page.tsx | 348-358 |
| Artifact API mapping | collection/page.tsx | 391-479 |
| Filtering logic | collection/page.tsx | 482-587 |
| Query hooks | use-collections.ts | 263-284 |
| All artifacts hook | useArtifacts.ts | 612-633 |
| Entity fetching | useEntityLifecycle.tsx | 628-668 |
| Collection context | collection-context.tsx | 46-160 |
| API functions | lib/api/collections.ts | 217-240 |
| Type definitions | types/artifact.ts | 46-105 |
| Collection types | types/collections.ts | 56-92 |
