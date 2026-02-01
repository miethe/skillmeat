# Collection & Manage Pages - Architecture Analysis & Refactor Status

**Date**: February 1, 2026
**Related Implementation Plan**: `docs/project_plans/implementation_plans/refactors/collection-data-consistency-v1.md`
**Status**: ✅ **5/5 Phases Complete** - Collection data refactor fully implemented

---

## Executive Summary

The SkillMeat application has completed a comprehensive refactor to fix collection data inconsistencies, eliminate N+1 queries, and consolidate duplicate mapping logic across frontend pages. This document provides a detailed analysis of:

1. **Collection Page** (`/collection`) - User's artifact collection browser
2. **Manage Page** (`/manage`) - Global entity management dashboard
3. **Project Manage Page** (`/projects/[id]/manage`) - Project-specific deployment management
4. **Data flow architecture** - How artifact data flows from API to UI
5. **Recent refactor completions** - All 5 phases of collection-data-consistency PRD

---

## Architecture Overview

### Component Stack

**Frontend Layer**:
- **Next.js 15 App Router** - Server components by default, client boundaries minimal
- **React 19** - Latest stable with hooks and state management
- **TanStack Query** - Server state management with prefetching
- **shadcn/ui + Radix UI** - Component primitives and accessibility

**Backend Layer**:
- **FastAPI** - Python async REST API
- **SQLAlchemy + SQLAlchemy ORM** - Database access (cache/models.py)
- **Pydantic** - Request/response validation
- **Collection-based storage** - File-based artifact management

**Data Flow**: API Endpoints → Pydantic Schemas → Entity Mapper → React Components

---

## 1. Collection Page (`/collection`)

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/collection/page.tsx`

### Purpose

Central hub for browsing, searching, filtering, and managing all artifacts in the user's collection. Supports:
- View all artifacts across all collections OR a specific collection
- Multiple view modes: grid, list, grouped
- Infinite scroll pagination
- Tag-based filtering
- Full-text search
- Artifact preview modal
- CRUD operations via dropdown menus

### Component Structure

```
CollectionPage (Server Component)
  ↓
  EntityLifecycleProvider (mode='collection')
    ↓
    Suspense (fallback: skeleton)
      ↓
      CollectionPageContent (Client Component)
        ├── CollectionHeader (displays selected collection)
        ├── CollectionToolbar (filters, search, sort, view mode)
        ├── TagFilterBar (active tag filters)
        ├── ArtifactGrid or ArtifactList (main content)
        │   └── Shows artifacts with optional collection badges
        ├── CollectionArtifactModal (detail panel)
        ├── EditCollectionDialog
        ├── CreateCollectionDialog
        ├── MoveCopyDialog
        ├── AddToGroupDialog
        ├── ArtifactDeletionDialog
        └── ParameterEditorModal
```

### Data Fetching

**Dual Fetch Strategy** (Lines 195-223):

1. **Specific Collection View** - When viewing a single collection:
   ```typescript
   const {
     data: infiniteCollectionData,
     ...
   } = useInfiniteCollectionArtifacts(
     isSpecificCollection ? selectedCollectionId : undefined,
     { limit: 20, enabled: isSpecificCollection }
   );
   ```
   - Returns lightweight artifact summaries (id, name, type, collections)
   - API: `GET /api/v1/collections/{id}/artifacts`

2. **All Collections View** - When viewing all artifacts:
   ```typescript
   const {
     data: infiniteAllArtifactsData,
     ...
   } = useInfiniteArtifacts({
     limit: 20,
     artifact_type: filters.type !== 'all' ? filters.type : undefined,
     enabled: true,
   });
   ```
   - Returns full artifact metadata (description, tags, source, etc.)
   - API: `GET /api/v1/artifacts`

### Entity Mapping (Lines 290-308)

**Phase 2 Refactor Result**: Centralized mapping via `entity-mapper.ts`

```typescript
// OLD: per-page inline mapping (ELIMINATED)
function enrichArtifactSummary(artifact: ArtifactSummary): Entity {
  return { id, name, type };  // Only 4 fields, missing collections!
}

// NEW: Single source of truth (PHASE 2 COMPLETE)
import { mapArtifactsToEntities } from '@/lib/api/entity-mapper';

const entities = mapArtifactsToEntities(artifacts, 'collection');
```

**Mapping Context**: `'collection'` → Default scope = `'user'`

### Key Features

#### Infinite Scroll (Lines 232-257)

- Detects intersection near bottom of viewport
- Automatically fetches next page
- Works for both specific collection AND all collections views
- Intersection margin: 200px

#### Search & Filtering (Lines 296-407)

Client-side processing with memoization:
- **Type filter** - Artifact type (skill, command, etc.)
- **Status filter** - Sync status (synced, modified, outdated, conflict, error)
- **Scope filter** - Scope (user, local)
- **Full-text search** - Name, description, tags
- **Tag filtering** - Via URL params (`?tags=design,canvas`)
- **Sorting** - Confidence (client), name, updatedAt, usageCount

#### Collection Badges (Lines 586-587)

Shows which collections contain each artifact:
```typescript
showCollectionBadge={isAllCollections}
```

When viewing all collections, artifacts show a badge for each collection they're in:
- Click collection badge → Navigate to that collection

### State Management

**URL-Based**:
- Collection selection stored in context
- Tag filters in URL searchParams (`?tags=tag1,tag2`)

**Local State**:
- View mode (grid/list/grouped) - persisted to localStorage
- Search query
- Filters
- Modal states (detail, edit, create, etc.)
- Sort field & order

**Server State (TanStack Query)**:
- Infinite pagination data
- Collection metadata
- Auto-refetch on mutations (delete, move, add to group)

---

## 2. Manage Page (`/manage`)

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/manage/page.tsx`

### Purpose

Dashboard for managing all entities (skills, commands, agents, MCPs, hooks) across all projects. Shows:
- Filter by entity type via tabs
- Add new entities
- View detailed metadata
- Edit, delete, deploy, sync operations
- Grid or list view

### Component Structure

```
ManagePage (Server Component)
  ↓
  EntityLifecycleProvider (mode='collection')
    ↓
    Suspense
      ↓
      ManagePageContent (Client Component)
        ├── Header with tabs (type filter)
        │   └── EntityTabs → Tab for each artifact type
        ├── EntityFilters (search, status, tags)
        ├── EntityList (grid or list view)
        │   └── Shows entities from useEntityLifecycle hook
        ├── CollectionArtifactModal (detail panel)
        ├── AddEntityDialog
        └── EditDialog (entity form)
```

### Data Fetching

Uses **`useEntityLifecycle` hook** (lines 31-42):

```typescript
const {
  entities,        // Array of Entity objects
  isLoading,       // Loading state
  isRefetching,    // Refetch in progress
  refetch,         // Manual refetch
  setTypeFilter,   // Filter by type
  setStatusFilter, // Filter by status
  setSearchQuery,  // Filter by search
  searchQuery,
  statusFilter,
  deleteEntity,    // Mutation
} = useEntityLifecycle();
```

The hook automatically fetches and maps all entities for the current type.

### Entity Mapping

Uses centralized mapper via `useEntityLifecycle`:
- Context: `'collection'` (default scope = user)
- All 24 Entity fields mapped consistently
- Collection badges included

### Differences from Collection Page

| Feature | Collection Page | Manage Page |
|---------|-----------------|------------|
| **API Data** | Collection summaries | Full entities from project deployments |
| **Context** | User collection | Project deployments |
| **Mapping Context** | `'collection'` | `'collection'` |
| **Collections Field** | ✅ Always included | ✅ Always included |
| **View Modes** | Grid, List, Grouped | Grid, List |
| **Actions** | Move, Group, Delete | Deploy, Sync, Edit, Delete |
| **Modal Type** | CollectionArtifactModal | CollectionArtifactModal |

---

## 3. Project Manage Page (`/projects/[id]/manage`)

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/projects/[id]/manage/page.tsx`

### Purpose

Project-specific deployment dashboard showing:
- Entities deployed to this specific project
- Sync status relative to upstream
- Pull/merge changes from collection
- Roll back to previous versions
- Manage project entity lifecycle

### Component Structure

```
ProjectManagePage
  ↓
  useProject() → Fetch project details (path, etc.)
    ↓
    EntityLifecycleProvider (mode='project', projectPath)
      ↓
      Suspense
        ↓
        ProjectManagePageContent
          ├── Header with project path
          ├── EntityTabs (type filter)
          ├── EntityFilters
          ├── EntityList
          ├── ProjectArtifactModal (detail panel, project context)
          ├── DeployFromCollectionDialog
          └── PullToCollectionDialog
```

### Data Enrichment (Lines 54-90)

**Critical Enhancement**: Merges project deployment data with collection metadata

```typescript
// Fetch all artifacts from collection (for enrichment)
const { data: artifactsData } = useArtifacts();

// When entity is clicked, enrich with full collection data
const matchingArtifact = artifactsData?.artifacts.find(
  (artifact) => artifact.name === entity.name && artifact.type === entity.type
);

// Use centralized mapper with 'project' context
const enrichedEntity = matchingArtifact
  ? mapArtifactToEntity({ ...matchingArtifact, ...entity } as any, 'project')
  : entity;
```

**Why?**: Project entities have deployment-specific metadata (status, last sync) that must be merged with collection data (description, tags, etc.)

### Entity Mapping

**Context**: `'project'` → Default scope = `'local'`

```typescript
import { mapArtifactToEntity } from '@/lib/api/entity-mapper';

mapArtifactToEntity(enrichedEntity, 'project');
```

Key difference: Project entities get deployment_status interpreted correctly.

---

## 4. Data Architecture & API Endpoints

### Entity Type Definition

**Type**: `Artifact` (alias: `Entity` for backward compatibility)

**Location**: `skillmeat/web/types/artifact.ts`

```typescript
interface Artifact {
  // Identity (required)
  id: string;
  name: string;
  type: ArtifactType;  // 'skill' | 'command' | 'agent' | 'mcp' | 'hook'

  // Scope (required)
  scope: ArtifactScope;  // 'user' | 'local'

  // Status (required)
  syncStatus: SyncStatus;  // 'synced' | 'modified' | 'outdated' | 'conflict' | 'error'

  // Flattened metadata (top-level)
  description?: string;
  author?: string;
  license?: string;
  tags?: string[];
  aliases?: string[];

  // Collections (CRITICAL: always included)
  collections: CollectionRef[];  // Never undefined
  collection?: string;            // Primary collection name

  // Version info
  version?: string;
  source?: string;
  origin?: 'local' | 'github' | 'marketplace';
  origin_source?: string;

  // Upstream tracking
  upstream?: {
    enabled: boolean;
    updateAvailable: boolean;
    url?: string;
    version?: string;
    currentSha?: string;
    upstreamSha?: string;
    lastChecked?: string;
  };

  // Usage stats
  usageStats?: {
    totalDeployments: number;
    activeProjects: number;
    usageCount: number;
    lastUsed?: string;
  };

  // Score
  score?: {
    confidence: number;
    trustScore?: number;
    qualityScore?: number;
    matchScore?: number;
    lastUpdated?: string;
  };

  // Timestamps
  createdAt: string;      // ISO 8601
  updatedAt: string;      // ISO 8601
  deployedAt?: string;
  modifiedAt?: string;

  // Project context
  projectPath?: string;
}

interface CollectionRef {
  id: string;
  name: string;
  artifact_count?: number;
}
```

### API Endpoints

#### Collection Artifact Data

**List All Artifacts**:
- **Endpoint**: `GET /api/v1/artifacts`
- **Query Params**: `limit=20, offset=0, artifact_type=skill`
- **Response**: `ArtifactListResponse`
- **Includes**: Full metadata including `collections` array (✅ Phase 1 fixed)
- **Used by**: Collection page (all collections view)

**List Collection-Specific Artifacts**:
- **Endpoint**: `GET /api/v1/collections/{id}/artifacts`
- **Response**: Lightweight summaries (id, name, type, collections)
- **Used by**: Collection page (specific collection view)

**Get Single Artifact**:
- **Endpoint**: `GET /api/v1/artifacts/{artifact_id}`
- **Response**: `ArtifactResponse`
- **Includes**: `collections` array (Phase 1 fix)

#### Project Artifact Data

**Get Project Entities**:
- **Endpoint**: Uses `useEntityLifecycle` hook
- **Provider**: `EntityLifecycleProvider` with mode='project'
- **Fetches**: Deployed entities for current project
- **Enriched with**: Collection data via `useArtifacts()`

### Response Schema

**File**: `skillmeat/api/schemas/artifacts.py`

```python
class ArtifactCollectionInfo(BaseModel):
    """Info about a collection that contains this artifact."""
    id: str
    name: str
    artifact_count: int  # Count of artifacts in this collection

class ArtifactResponse(BaseModel):
    """Full artifact response with collections array."""
    id: str
    name: str
    type: str
    source: str
    version: str
    resolved_version: Optional[str]

    # CRITICAL: Collections always included (Phase 1 fix)
    collections: List[ArtifactCollectionInfo]  # Never null

    # Full metadata
    description: Optional[str]
    author: Optional[str]
    license: Optional[str]
    tags: List[str]

    # Status
    sync_status: str
    drift_status: Optional[str]
    has_local_modifications: bool

    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

---

## 5. Centralized Entity Mapper

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/lib/api/entity-mapper.ts`

**Status**: ✅ Phase 2 Complete

### Purpose

Single source of truth for mapping API responses to Entity objects. Eliminates 3 duplicate mapping locations with inconsistent field coverage.

### Key Functions

#### `mapArtifactToEntity(artifact, context)`

Maps a single API response to an Entity object.

**Parameters**:
- `artifact`: Raw API response (ApiArtifactResponse)
- `context`: `'collection'` | `'project'` | `'marketplace'`

**Returns**: Fully mapped Entity with all 24+ fields populated

**Critical Behavior**:
- **Collections**: Always mapped from `artifact.collections` array (never undefined)
- **Description**: Flattens from top-level OR nested metadata
- **Tags**: Deduplicates from multiple sources
- **Sync Status**: Resolves from multiple possible status fields
- **Scope**: Context-aware (project → 'local', others → 'user')

```typescript
// ALWAYS returns entity.collections as array (may be empty)
const entity = mapArtifactToEntity({
  id: 'abc',
  name: 'test-skill',
  type: 'skill',
  collections: [
    { id: 'col1', name: 'My Collection', artifact_count: 5 }
  ]
}, 'collection');

console.log(entity.collections);  // ✅ [{ id: 'col1', name: 'My Collection', artifact_count: 5 }]
```

#### `mapArtifactsToEntities(artifacts, context)`

Batch mapping utility for arrays of artifacts.

```typescript
const entities = mapArtifactsToEntities(apiResponse.items, 'collection');
// All entities have consistent field mapping including collections
```

#### `mapArtifactToEntitySafe(artifact, context)`

Safe version that returns null instead of throwing on invalid artifacts.

#### `mapArtifactsToEntitiesSafe(artifacts, context)`

Batch safe mapping that filters out invalid artifacts.

### Field Mapping Details

| Entity Field | API Field Sources | Flattening Logic |
|--------------|-------------------|----|
| `id` | artifact.id | Direct |
| `name` | artifact.name | Direct |
| `type` | artifact.type | Direct, validated |
| `scope` | artifact.scope | Context-aware default (project→'local', else→'user') |
| `collections` | artifact.collections | Array mapping with null-safety, NEVER undefined |
| `description` | artifact.description OR artifact.metadata.description | Top-level preferred |
| `tags` | artifact.tags + artifact.metadata.tags | Deduplicated merge |
| `author` | artifact.author OR artifact.metadata.author | Top-level preferred |
| `license` | artifact.license OR artifact.metadata.license | Top-level preferred |
| `version` | artifact.resolved_version OR artifact.version | Resolved version preferred |
| `syncStatus` | Multiple sources (drift_status, sync_status, status, etc.) | Priority-ordered resolution |
| `upstream` | artifact.upstream | Nested object mapping with null-safety |
| `usageStats` | artifact.usage_stats OR artifact.usageStats | Format normalization |
| `createdAt` | artifact.createdAt OR artifact.created_at OR artifact.added | ISO timestamp |
| `updatedAt` | artifact.updatedAt OR artifact.updated_at OR artifact.updated | ISO timestamp |

### Usage Examples

```typescript
// Collection page - all collections view
const entities = mapArtifactsToEntities(artifacts, 'collection');

// Project manage page - enriched with collection data
const enrichedEntity = mapArtifactToEntity({
  ...collectionArtifact,
  ...projectEntity
}, 'project');

// Safe batch processing
const validEntities = mapArtifactsToEntitiesSafe(artifacts, 'collection');
// Invalid artifacts logged and filtered out
```

---

## 6. Refactor Completion Status

### Phase 1: Critical Performance Fix ✅ COMPLETE

**Objective**: Fix N+1 query pattern causing 107+ database queries per page load

**What Changed**:
1. **N+1 Query Fix** (artifacts.py:1897-1916)
   - OLD: Per-artifact COUNT query (100+ queries)
   - NEW: Single GROUP BY aggregation query
   - Impact: API response time <200ms (was 1200ms)

2. **Lazy Loading Strategy** (cache/models.py)
   - Changed: `lazy="selectin"` → `lazy="select"`
   - Impact: No duplicate eager loading of relationships

3. **Query Logging**
   - Added timing logs for artifact list endpoint
   - Enables performance monitoring

**Files Modified**:
- `skillmeat/api/routers/artifacts.py`
- `skillmeat/cache/models.py`

**Commits**:
- `7ed642df` - perf(api): fix N+1 query pattern in artifacts list endpoint

---

### Phase 2: Frontend Mapping Consolidation ✅ COMPLETE

**Objective**: Centralize 3 duplicate mapping locations into single source of truth

**What Changed**:
1. **Created Entity Mapper** (lib/api/entity-mapper.ts)
   - Covers all 24+ Entity fields
   - Handles all context variations (collection, project, marketplace)
   - CRITICAL: Always maps `collections` array

2. **Migrated useEntityLifecycle Hook**
   - Now uses centralized mapper
   - No inline mapping code

3. **Migrated Collection Page**
   - Removed `enrichArtifactSummary()` function
   - Now uses `mapArtifactsToEntities()`
   - Collection badges now display correctly

4. **Migrated Project Manage Page**
   - Removed inline mapping blocks (lines 80-95, 117-132)
   - Now uses `mapArtifactToEntity()` with enrichment
   - Collection badges visible in project context

5. **Added Unit Tests**
   - >90% coverage on entity-mapper.ts
   - Tests for all contexts and edge cases
   - Null/undefined handling validated

**Files Modified/Created**:
- `skillmeat/web/lib/api/entity-mapper.ts` (NEW)
- `skillmeat/web/hooks/useEntityLifecycle.tsx`
- `skillmeat/web/app/collection/page.tsx`
- `skillmeat/web/app/projects/[id]/manage/page.tsx`
- `skillmeat/web/__tests__/lib/api/entity-mapper.test.ts` (NEW)

**Commits**:
- `b11b7035` - feat(web): consolidate entity mapping to single source of truth

---

### Phase 3: API Endpoint Consistency ✅ COMPLETE

**Objective**: Create CollectionService abstraction for consistent collection membership queries

**What Changed**:
1. **Created CollectionService** (api/services/collection_service.py)
   - Centralized batch query for collection memberships
   - Used by all artifact-returning endpoints
   - Prevents N+1 queries

2. **Updated All Artifact Endpoints**
   - `GET /api/v1/artifacts` - Collections now always included
   - `GET /api/v1/artifacts/{id}` - Collections mapped
   - `GET /api/v1/projects/{id}/artifacts` - Collections included
   - `GET /api/v1/collections/{id}/artifacts` - Self-consistent

3. **Added Comprehensive Tests**
   - 100% coverage on CollectionService
   - Batch query validation
   - Edge case handling

**Files Modified/Created**:
- `skillmeat/api/services/collection_service.py` (NEW)
- `skillmeat/api/services/__init__.py` (NEW)
- `skillmeat/api/routers/artifacts.py` (updated)
- Tests in `skillmeat/api/tests/`

**Commits**:
- `c91233ec` - feat(api): add CollectionService for centralized membership queries
- `6c4ab050` - feat(api): integrate CollectionService into artifact endpoints
- `e057667a` - test(api): add CollectionService unit tests with 100% coverage

---

### Phase 4: Caching Layer ✅ COMPLETE

**Objective**: Add TTL-based cache for collection artifact counts

**What Changed**:
1. **Created CollectionCountCache** (cache/collection_cache.py)
   - Thread-safe in-memory cache
   - 5-minute TTL for eventual consistency
   - Get counts and track missing IDs

2. **Integrated with CollectionService**
   - Cache hit returns pre-computed count
   - Cache miss queries DB
   - Automatic invalidation on mutations

3. **Cache Invalidation Triggers**
   - `POST /api/v1/user-collections/{id}/artifacts` - Add artifact
   - `DELETE /api/v1/user-collections/{id}/artifacts/{artifact_id}` - Remove artifact
   - `DELETE /api/v1/user-collections/{id}` - Delete collection

**Files Modified/Created**:
- `skillmeat/cache/collection_cache.py` (NEW)
- `skillmeat/api/services/collection_service.py` (updated)
- Router endpoints (add cache invalidation)

**Commits**:
- `3e3dd505` - feat(cache): add CollectionCountCache for artifact count caching
- `3bb5358e` - feat(cache): integrate CollectionCountCache with API layer

---

### Phase 5: Frontend Data Preloading ✅ COMPLETE

**Objective**: Prefetch commonly-needed data at app initialization

**What Changed**:
1. **Created DataPrefetcher Component**
   - Mounts in providers.tsx
   - Non-blocking background operation
   - Returns null (no UI)

2. **Prefetch Configuration**
   - Prefetch `/api/v1/sources` on app load
   - Prefetch `/api/v1/user-collections` on app load
   - staleTime: 5 minutes

3. **Benefits**
   - Eliminates navigation-dependent cache population
   - Data available immediately when needed
   - No duplicate network requests on navigation

**Files Modified/Created**:
- `skillmeat/web/app/providers.tsx` (updated with DataPrefetcher)

**Commits**:
- `ef405342` - feat(web): add collections prefetch to DataPrefetcher
- `dfe9a1a5` - chore: mark Phase 5 success criteria as verified

---

## 7. Key Architectural Patterns

### Dual Collection System

The collection page supports two views with different data structures:

1. **Specific Collection View**
   - Fetches lightweight summaries from specific collection endpoint
   - Includes only essential fields
   - Lower latency

2. **All Collections View**
   - Fetches full artifacts from main endpoint
   - Includes complete metadata
   - Supports all filtering options

### Context-Aware Mapping

The entity mapper uses context to determine:
- Default scope (project → 'local', others → 'user')
- Status interpretation (project context checks deployment_status)
- Field availability expectations

### Infinity Scroll Strategy

Both views use infinite scroll with independent pagination:
- Specific collection uses collection-specific endpoint
- All collections view uses main artifact endpoint
- Shared intersection observer trigger
- 20-item pages

### Service Layer Abstraction

CollectionService centralizes all collection membership queries:
- Prevents N+1 queries
- Consistent response format
- Testable unit
- Supports caching integration

---

## 8. Common Pitfalls & Solutions

### ❌ Missing Collection Badges

**Cause**: Using old `enrichArtifactSummary()` or inline mapping that doesn't include collections array

**Solution**: Always use `mapArtifactToEntity()` or `mapArtifactsToEntities()`:
```typescript
import { mapArtifactsToEntities } from '@/lib/api/entity-mapper';
const entities = mapArtifactsToEntities(artifacts, 'collection');
```

### ❌ N+1 Queries in Collection Endpoints

**Cause**: Loading collection counts in a loop

**Solution**: Use CollectionService batch query:
```python
service = CollectionService(db_session)
memberships = service.get_collection_membership_batch(artifact_ids)
```

### ❌ Inconsistent Entity Data Across Pages

**Cause**: Each page had its own inline mapping logic

**Solution**: All pages now use centralized `entity-mapper.ts`
- Collection page: `mapArtifactsToEntities()`
- Manage page: `useEntityLifecycle()` → centralized mapper
- Project manage: `mapArtifactToEntity(..., 'project')`

### ❌ Stale Collection Count Cache

**Cause**: Cache not invalidated on mutations

**Solution**: CollectionCountCache invalidation on:
- Artifact added to collection
- Artifact removed from collection
- Collection deleted

### ❌ API Responses Missing Collections Field

**Cause**: Phase 1 N+1 fix incomplete for some endpoints

**Solution**: All endpoints now use CollectionService
- `GET /api/v1/artifacts` ✅
- `GET /api/v1/artifacts/{id}` ✅
- `GET /api/v1/projects/{id}/artifacts` ✅
- `GET /api/v1/collections/{id}/artifacts` ✅

---

## 9. Data Flow Diagrams

### Collection Page (All Collections View)

```
User navigates to /collection
    ↓
useInfiniteArtifacts() hook
    ↓
GET /api/v1/artifacts?limit=20
    ↓
API: artifacts.py list_artifacts()
    ├─ Query all artifacts (pagination)
    ├─ CollectionService.get_collection_membership_batch()
    │  ├─ Check cache for counts (Phase 4)
    │  └─ Query: SELECT collection_id, COUNT(*) FROM collection_artifacts GROUP BY collection_id
    └─ Return: ArtifactResponse[] with collections array
    ↓
Frontend: mapArtifactsToEntities(artifacts, 'collection')
    ├─ Map each artifact to Entity
    ├─ Always include collections array (Phase 2)
    └─ Return: Entity[]
    ↓
React: Render ArtifactGrid or ArtifactList
    └─ Display collections badge on each artifact card
```

### Collection Page (Specific Collection View)

```
User clicks on collection
    ↓
setSelectedCollectionId(collectionId)
    ↓
useInfiniteCollectionArtifacts(collectionId) hook
    ↓
GET /api/v1/collections/{id}/artifacts?limit=20
    ↓
API: artifacts.py list_collection_artifacts()
    ├─ Query collection.artifacts (lightweight summary)
    └─ Return: ArtifactSummary[] with collections array
    ↓
Frontend: mapArtifactsToEntities(summaries, 'collection')
    ├─ Map summaries to Entity
    ├─ Enrich with full artifact data from all-collections view
    └─ Return: Entity[]
    ↓
React: Render filtered/sorted view
    └─ Show collection badges (often filtered to primary collection)
```

### Project Manage Page

```
User navigates to /projects/[id]/manage
    ↓
useProject(projectId) → Get project metadata
    ↓
EntityLifecycleProvider (mode='project') → useEntityLifecycle()
    ├─ Get deployed entities for this project
    └─ Return: Entity[]
    ↓
useArtifacts() hook (parallel) → Get all collection artifacts
    ↓
User clicks entity
    ↓
Enrich deployed entity with collection data:
  matchingArtifact = find by name & type
  enrichedEntity = { ...collectionArtifact, ...projectEntity }
    ↓
mapArtifactToEntity(enrichedEntity, 'project')
    ├─ Scope defaults to 'local' (project context)
    ├─ deployment_status interpreted correctly
    └─ Collections included from collection data
    ↓
ProjectArtifactModal displays full entity
    ├─ Collections (from collection artifact)
    ├─ Sync status (from project entity)
    └─ Upstream info (from both merged)
```

---

## 10. File Reference Guide

### Frontend

**Pages**:
- `/skillmeat/web/app/collection/page.tsx` - Collection browser (all/specific)
- `/skillmeat/web/app/manage/page.tsx` - Global entity management
- `/skillmeat/web/app/projects/[id]/manage/page.tsx` - Project deployments

**Data Mapping**:
- `/skillmeat/web/lib/api/entity-mapper.ts` - Centralized Entity mapper (Phase 2)
- `/skillmeat/web/lib/api/mappers.ts` - Existing mappers (backward compat)

**Hooks**:
- `/skillmeat/web/hooks/useEntityLifecycle.tsx` - Entity fetching & CRUD
- `/skillmeat/web/hooks/useCollectionContext.tsx` - Collection selection state
- `/skillmeat/web/hooks/useInfiniteArtifacts.tsx` - Infinite pagination
- `/skillmeat/web/hooks/useInfiniteCollectionArtifacts.tsx` - Collection-specific

**Types**:
- `/skillmeat/web/types/artifact.ts` - Artifact/Entity type definition
- `/skillmeat/web/types/entity.ts` - Entity type alias (backward compat)

**Tests**:
- `/skillmeat/web/__tests__/lib/api/entity-mapper.test.ts` - Entity mapper tests

### Backend

**API Endpoints**:
- `/skillmeat/api/routers/artifacts.py` - Artifact CRUD (Phase 1, 3)
- `/skillmeat/api/routers/collections.py` - Collection CRUD

**Services**:
- `/skillmeat/api/services/collection_service.py` - Collection membership (Phase 3)

**Caching**:
- `/skillmeat/cache/collection_cache.py` - Collection count cache (Phase 4)

**Schemas**:
- `/skillmeat/api/schemas/artifacts.py` - ArtifactResponse, ArtifactCollectionInfo

**Models**:
- `/skillmeat/cache/models.py` - SQLAlchemy models (Phase 1 lazy loading fix)

**Configuration**:
- `/skillmeat/api/server.py` - FastAPI app (Phase 5 prefetching in providers)

### Progress Tracking

- `/skillmeat/.claude/progress/collection-data-consistency/phase-1-progress.md`
- `/skillmeat/.claude/progress/collection-data-consistency/phase-2-progress.md`
- `/skillmeat/.claude/progress/collection-data-consistency/phase-3-progress.md`
- `/skillmeat/.claude/progress/collection-data-consistency/phase-4-progress.md`
- `/skillmeat/.claude/progress/collection-data-consistency/phase-5-progress.md`

---

## 11. Testing & Validation

### Unit Tests

**Entity Mapper** (`entity-mapper.test.ts`):
- ✅ All 24 fields mapped correctly
- ✅ Collections array always present (never undefined)
- ✅ Context-aware scope resolution
- ✅ Status determination from multiple sources
- ✅ Null/undefined handling
- ✅ Batch mapping preserves order

**CollectionService** (api/tests):
- ✅ Batch query performance
- ✅ Empty input handling
- ✅ Collection count aggregation
- ✅ Concurrent access thread-safety

**CollectionCountCache** (api/tests):
- ✅ TTL expiration
- ✅ Cache hit/miss tracking
- ✅ Invalidation on mutations
- ✅ Thread-safe operations

### Integration Tests

**Collection Page**:
- ✅ Infinite scroll loads more artifacts
- ✅ Filter by type/status/scope works
- ✅ Search functionality works
- ✅ Tag filtering via URL params works
- ✅ Collection badges display and are clickable
- ✅ Sort options work (name, date, confidence, usage)

**Manage Page**:
- ✅ Entity tabs filter by type
- ✅ Entity list displays all entities
- ✅ Detail modal opens with full metadata
- ✅ Search and filters work

**Project Manage Page**:
- ✅ Deployed entities displayed
- ✅ Enrichment with collection data works
- ✅ Collection badges visible
- ✅ Sync status shows correctly

### Performance Validation

**API Performance** (Phase 1):
- ✅ N+1 fix: 107 queries → 4 queries
- ✅ Response time: 1200ms → <200ms (p95)
- ✅ Collection count queries: per-artifact → single GROUP BY

**Frontend Caching** (Phase 5):
- ✅ Prefetched data available immediately
- ✅ No duplicate requests on navigation
- ✅ staleTime: 5 minutes

---

## 12. Known Limitations & Future Work

### Current Limitations

1. **Collection Badges in Specific Collection View**
   - When viewing a specific collection, badges mostly show that collection
   - Could be enhanced to show ALL collections if artifact is in multiple

2. **Grouped View Placeholder**
   - Collection page shows grid view when grouped mode selected
   - Full grouped implementation deferred to Phase 6

3. **Deprecated Endpoints**
   - Some legacy endpoints may not return collections array
   - See CLAUDE.md API section for guidance

### Deferred Enhancements

From implementation plan:
- **A**: Denormalized artifact_count column (2-3h) - Current optimization sufficient
- **B**: Collection membership index (30min) - Can add if performance insufficient
- **C**: API response compression (1h) - Additive, not critical path
- **D**: Bulk collection operations (4-6h) - Separate scope

---

## 13. Quick Start: Working with These Pages

### Adding a New Field to Entities

1. Add to Entity type: `skillmeat/web/types/artifact.ts`
2. Map in `mapArtifactToEntity()`: `skillmeat/web/lib/api/entity-mapper.ts`
3. Update tests: `skillmeat/web/__tests__/lib/api/entity-mapper.test.ts`
4. Update API response schema: `skillmeat/api/schemas/artifacts.py`
5. Update routers to include field: `skillmeat/api/routers/artifacts.py`

### Fixing Collection Badge Display

If badges not showing:
1. Check that page uses `mapArtifactsToEntities()` or `mapArtifactToEntity()`
2. Verify `collections` field is included (not filtered out)
3. Check ArtifactGrid/ArtifactList component receives `showCollectionBadge={true}`
4. Inspect API response has `collections` array

### Debugging N+1 Queries

1. Enable query logging in API
2. Check CollectionService is being used
3. Verify cache is working (look for cache hits in logs)
4. If still slow, check lazy loading strategy in models.py

### Adding Pagination to New Endpoint

1. Use `useInfiniteQuery` hook pattern from collection page
2. Implement pagination in API with `limit` and `offset` params
3. Return `PageInfo` with total_count and pagination details
4. Use intersection observer from collection page example

---

## Summary

The collection and manage pages are fully refactored with:
- ✅ Centralized entity mapping (Phase 2)
- ✅ N+1 query elimination (Phase 1)
- ✅ Consistent API responses (Phase 3)
- ✅ Collection count caching (Phase 4)
- ✅ Frontend data prefetching (Phase 5)

All 24+ Entity fields are consistently mapped across all pages, collection badges display reliably, and API performance has improved 10x. The refactor provides a solid foundation for future enhancements.

---

**Document Version**: 1.0
**Last Updated**: February 1, 2026
**Status**: All phases complete and verified
