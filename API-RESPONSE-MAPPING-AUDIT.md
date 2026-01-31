# API Response Mapping Audit - SkillMeat Web Frontend

## Executive Summary

This audit identifies all locations in the SkillMeat web frontend where API responses are mapped to Entity/Artifact objects. The codebase uses a centralized mapper (`mapApiResponseToArtifact`) in most places, but there are **3 critical locations with duplicate/inconsistent inline enrichment logic** that should be consolidated.

**Key Finding**: The `collections` field is frequently missing or constructed inline in 2+ places, creating data inconsistency and maintenance burden.

---

## 1. Centralized Mapping Function (CANONICAL)

**File**: `skillmeat/web/lib/api/mappers.ts`
**Lines**: 265-423 (main mapper), 444-449 (batch wrapper)

### Primary Functions

#### `mapApiResponseToArtifact(response, context)`
**Lines**: 265-423

**Purpose**: Converts raw API `ArtifactResponse` to unified `Artifact` type

**Fields Mapped**:
- ✅ Identity: `id`, `name`, `type`
- ✅ Scope: `scope` (defaults to 'user' for collection context, 'local' for project context)
- ✅ Collection (singular): `collection` string
- ✅ Collections (plural): `collections[]` with `id`, `name`, `artifact_count`
- ✅ Metadata (flattened): `description`, `author`, `license`, `version`, `tags`, `dependencies`
- ✅ Source & Origin: `source`, `origin`, `origin_source`, `aliases`
- ✅ Status: `syncStatus` (via `determineSyncStatus()`)
- ✅ Upstream tracking: `upstream` (object with `enabled`, `url`, `version`, `currentSha`, `upstreamSha`, `updateAvailable`, `lastChecked`)
- ✅ Usage stats: `usageStats` (object with `totalDeployments`, `activeProjects`, `lastUsed`, `usageCount`)
- ✅ Score: `score` (object with `confidence`, `trustScore`, `qualityScore`, `matchScore`, `lastUpdated`)
- ✅ Timestamps: `createdAt`, `updatedAt`, `deployedAt` (project context only), `modifiedAt` (project context only)
- ✅ Project path: `projectPath` (project context only)

**Collections Mapping** (Lines 314-332):
```typescript
// Singular collection property
if (response.collection) {
  if (typeof response.collection === 'string') {
    collectionName = response.collection;
  } else {
    collectionName = response.collection.name;
  }
}

// Plural collections array
if (response.collections && response.collections.length > 0) {
  collections = response.collections.map((c) => ({
    id: c.id,
    name: c.name,
    ...(c.artifact_count !== undefined && { artifact_count: c.artifact_count }),
  }));
}
```

#### `mapApiResponsesToArtifacts(responses, context)`
**Lines**: 444-449

Batch wrapper around `mapApiResponseToArtifact`. Maps arrays of responses.

#### `determineSyncStatus(response, context)`
**Lines**: 181-233

Determines sync status with priority:
1. Error (if `syncStatus === 'error'` or `error` field present)
2. Conflict (if `syncStatus === 'conflict'` or `conflictState.hasConflict`)
3. Modified (project context only, if `modifiedAt > deployedAt`)
4. Outdated (if `upstream.updateAvailable` or SHA mismatch)
5. Default: 'synced'

---

## 2. Hook-Based Mappers

### 2.1 useArtifacts Hook

**File**: `skillmeat/web/hooks/useArtifacts.ts`

#### Usage Location 1: `fetchArtifactsFromApi()`
**Lines**: 277-318

**Context**: Fetches artifacts list from `/artifacts` endpoint

**Mapping Code**:
```typescript
const mappedArtifacts = response.items.map((item) =>
  mapApiResponseToArtifact(item, 'collection')
);
```

**Status**: ✅ Uses centralized mapper

---

#### Usage Location 2: `fetchArtifactFromApi()`
**Lines**: 320-331

**Context**: Fetches single artifact by ID

**Mapping Code**:
```typescript
const artifact = await apiRequest<ArtifactResponse>(`/artifacts/${encodeURIComponent(id)}`);
return mapApiResponseToArtifact(artifact, 'collection');
```

**Status**: ✅ Uses centralized mapper

---

#### Usage Location 3: `useUpdateArtifact()` mutation
**Lines**: 368-390

**Context**: PUT request to update artifact

**Mapping Code**:
```typescript
const response = await apiRequest<ArtifactResponse>(`/artifacts/${encodeURIComponent(artifact.id)}`, {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(artifact),
});
return mapApiResponseToArtifact(response, 'collection');
```

**Status**: ✅ Uses centralized mapper

---

#### Usage Location 4: `useUpdateArtifactTags()` mutation
**Lines**: 437-473

**Context**: PUT request to `/artifacts/:id/tags` endpoint

**Mapping Code**:
```typescript
const response = await apiRequest<ArtifactResponse>(url, {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ tags }),
});
return mapApiResponseToArtifact(response, 'collection');
```

**Status**: ✅ Uses centralized mapper

---

#### Usage Location 5: `useInfiniteArtifacts()` hook
**Lines**: 520-542

**Context**: Infinite scroll pagination via `fetchArtifactsPaginated()`

**Mapping Code**:
```typescript
return fetchArtifactsPaginated({
  limit,
  after: pageParam,
  artifact_type: filters.artifact_type,
  status: filters.status,
  scope: filters.scope,
  search: filters.search,
  tools: filters.tools,
});
```

**Status**: ⚠️ **INDIRECT** - Delegates to `fetchArtifactsPaginated()` (in `lib/api/artifacts.ts`)
**Note**: Verify mapping happens in that module

---

### 2.2 Collection Page

**File**: `skillmeat/web/app/collection/page.tsx`

#### Usage Location 6: Wrapper function `mapApiArtifactToArtifact()`
**Lines**: 352-356

**Context**: Collection page component uses a wrapper to map single artifacts

**Mapping Code**:
```typescript
const mapApiArtifactToArtifact = (apiArtifact: ArtifactResponse): Artifact => {
  return mapApiResponseToArtifact(apiArtifact, 'collection');
};
```

**Status**: ✅ Uses centralized mapper (via wrapper)

---

#### Usage Location 7: Inline mapping in `filteredArtifacts` useMemo
**Lines**: 371 and 395

**Context**: Mapping API responses from infinite scroll pages

**Mapping Code**:
```typescript
// Line 371 - specific collection view enrichment
const fullArtifacts: Artifact[] = infiniteAllArtifactsData?.pages
  ? infiniteAllArtifactsData.pages.flatMap((page) => page.items.map(mapApiArtifactToArtifact))
  : [];

// Line 395 - all collections view
artifacts = infiniteAllArtifactsData.pages.flatMap((page) =>
  page.items.map(mapApiArtifactToArtifact)
);
```

**Status**: ✅ Uses centralized mapper

---

#### Usage Location 8: Inline mapping in `availableTags` useMemo
**Lines**: 490 and 499

**Context**: Tag computation from all loaded artifacts

**Mapping Code**:
```typescript
// Line 490
const fullArtifacts: Artifact[] = infiniteAllArtifactsData?.pages
  ? infiniteAllArtifactsData.pages.flatMap((page) => page.items.map(mapApiArtifactToArtifact))
  : [];

// Line 499
allArtifacts = infiniteAllArtifactsData.pages.flatMap((page) =>
  page.items.map(mapApiArtifactToArtifact)
);
```

**Status**: ✅ Uses centralized mapper

---

#### Usage Location 9: `enrichArtifactSummary()` function
**Lines**: 45-95

**Context**: Enriches lightweight `ArtifactSummary` objects with full catalog data

**Mapping Code** (MANUAL CONSTRUCTION - NOT USING CENTRALIZED MAPPER):
```typescript
return {
  id: artifactId,
  name: summary.name,
  type: summary.type as any,
  scope: 'user',
  syncStatus: 'synced',
  version: summary.version || undefined,
  source: isSourceMissingOrSynthetic ? undefined : summary.source,
  // Flattened metadata fields
  description: '',
  tags: [],
  upstream: {
    enabled: false,
    updateAvailable: false,
  },
  usageStats: {
    totalDeployments: 0,
    activeProjects: 0,
    usageCount: 0,
  },
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  aliases: [],
  collection: collectionId,
};
```

**Status**: ⚠️ **DUPLICATE MAPPING LOGIC**
**Missing Fields**:
- ❌ `collections` array (NOT populated, even though parameter provided)
- ❌ `author`, `license` (metadata fields)
- ❌ `origin`, `origin_source`
- ❌ `dependencies`
- ❌ `score` object
- ❌ `deployedAt`, `modifiedAt` (project timestamps)
- ❌ `projectPath` (project context)

**Issue**: This is a fallback for when full artifact data isn't available, but it creates incomplete artifacts. The `collections` field should be populated from the `allArtifacts` lookup.

---

## 3. Project/Manage Pages - CRITICAL DUPLICATIONS

### 3.1 Project Manage Page

**File**: `skillmeat/web/app/projects/[id]/manage/page.tsx`

#### Usage Location 10: URL artifact selection handler
**Lines**: 70-100

**Context**: Enriches project entities with collection data when URL specifies artifact

**Mapping Code** (INLINE ENRICHMENT - NOT USING MAPPER):
```typescript
const matchingArtifact = artifactsData?.artifacts.find(
  (artifact) => artifact.name === entity.name && artifact.type === entity.type
);

const enrichedEntity: Entity = matchingArtifact
  ? {
      ...entity,
      collections: matchingArtifact.collections,  // COPY FROM ARTIFACT
      description: matchingArtifact.description || entity.description,
      tags: matchingArtifact.tags || entity.tags,
      aliases: matchingArtifact.aliases || entity.aliases,
      source: matchingArtifact.source || entity.source,
    }
  : {
      ...entity,
      // CONSTRUCT from single property when no match
      collections: entity.collection
        ? [{ id: entity.collection, name: entity.collection === 'default' ? 'Default Collection' : entity.collection }]
        : undefined,
    };
```

**Status**: ⚠️ **DUPLICATE ENRICHMENT LOGIC**
**Issues**:
- Hard-coded 'Default Collection' name mapping
- Only copies 5 fields from artifact (missing `source`, `origin`, `dependencies`, `score`, etc.)
- Uses spread `...entity` (which has project-specific fields) then selectively overwrites

---

#### Usage Location 11: Entity click handler
**Lines**: 109-138

**Context**: Enriches entities when clicked to view detail modal

**Mapping Code** (INLINE ENRICHMENT - NOT USING MAPPER):
```typescript
const matchingArtifact = artifactsData?.artifacts.find(
  (artifact) => artifact.name === entity.name && artifact.type === entity.type
);

const enrichedEntity: Entity = matchingArtifact
  ? {
      ...entity,
      collections: matchingArtifact.collections,  // COPY FROM ARTIFACT
      description: matchingArtifact.description || entity.description,
      tags: matchingArtifact.tags || entity.tags,
      aliases: matchingArtifact.aliases || entity.aliases,
      source: matchingArtifact.source || entity.source,
    }
  : {
      ...entity,
      // CONSTRUCT from single property when no match
      collections: entity.collection
        ? [{ id: entity.collection, name: entity.collection === 'default' ? 'Default Collection' : entity.collection }]
        : undefined,
    };
```

**Status**: ⚠️ **EXACT DUPLICATE** of Location 10
**Issue**: Copy-paste duplication

---

### 3.2 Collection Management Page

**File**: `skillmeat/web/app/manage/page.tsx`

**Note**: This page uses `useEntityLifecycle()` hook which returns `entities: Artifact[]` directly, so it doesn't perform inline enrichment. Artifacts are already fully mapped by the time they reach this component.

**Status**: ✅ No duplicate mapping here

---

## 4. Summary Table

| Location | File | Lines | Mapper Used | Status | Issues |
|----------|------|-------|------------|--------|--------|
| **Centralized** | `lib/api/mappers.ts` | 265-423 | `mapApiResponseToArtifact()` | ✅ CANONICAL | Maps all fields including `collections` |
| Hook: fetchArtifactsFromApi | `hooks/useArtifacts.ts` | 293-295 | ✅ Centralized | ✅ | — |
| Hook: fetchArtifactFromApi | `hooks/useArtifacts.ts` | 323 | ✅ Centralized | ✅ | — |
| Hook: useUpdateArtifact | `hooks/useArtifacts.ts` | 376 | ✅ Centralized | ✅ | — |
| Hook: useUpdateArtifactTags | `hooks/useArtifacts.ts` | 464 | ✅ Centralized | ✅ | — |
| Hook: useInfiniteArtifacts | `hooks/useArtifacts.ts` | 525-534 | ⚠️ Indirect | ✅ | Via `fetchArtifactsPaginated()` |
| Collection: wrapper function | `app/collection/page.tsx` | 354-356 | ✅ Centralized | ✅ | — |
| Collection: filteredArtifacts | `app/collection/page.tsx` | 371, 395 | ✅ Centralized | ✅ | — |
| Collection: availableTags | `app/collection/page.tsx` | 490, 499 | ✅ Centralized | ✅ | — |
| **Collection: enrichArtifactSummary** | `app/collection/page.tsx` | 69-94 | ❌ INLINE | ⚠️ | **Missing `collections` array** |
| **ProjectManage: URL artifact** | `app/projects/[id]/manage/page.tsx` | 80-95 | ❌ INLINE | ⚠️ | **Duplicate logic, partial mapping** |
| **ProjectManage: entity click** | `app/projects/[id]/manage/page.tsx` | 117-132 | ❌ INLINE | ⚠️ | **Exact duplicate of above** |

---

## 5. Detailed Analysis: Duplicate Enrichment Logic

### Problem 1: Collection Enrichment in Project Manage (Locations 10 & 11)

**Current Code** (both locations are identical):
```typescript
const enrichedEntity: Entity = matchingArtifact
  ? {
      ...entity,
      collections: matchingArtifact.collections,
      description: matchingArtifact.description || entity.description,
      tags: matchingArtifact.tags || entity.tags,
      aliases: matchingArtifact.aliases || entity.aliases,
      source: matchingArtifact.source || entity.source,
    }
  : {
      ...entity,
      collections: entity.collection
        ? [{ id: entity.collection, name: entity.collection === 'default' ? 'Default Collection' : entity.collection }]
        : undefined,
    };
```

**Issues**:
1. **Incomplete Mapping**: Only copies 5 fields (collections, description, tags, aliases, source)
   - Missing: `author`, `license`, `version`, `origin`, `origin_source`, `dependencies`, `score`, `upstream`, `usageStats`, deployment timestamps
2. **Hard-coded Collection Name**: `'Default Collection'` for 'default' ID
   - Should get actual collection name from collection lookup
3. **Duplicated Twice**: Same code in lines 80-95 AND 117-132
4. **Uses Spread Operator**: Spreads entire `entity` then overwrites - could propagate stale data

**Solution**: Use centralized `mapApiResponseToArtifact()` or create entity enrichment helper.

---

### Problem 2: Fallback Mapping in Collection Page (Location 9)

**Current Code** (enrichArtifactSummary fallback):
```typescript
return {
  id: artifactId,
  name: summary.name,
  type: summary.type as any,
  scope: 'user',
  syncStatus: 'synced',
  version: summary.version || undefined,
  source: isSourceMissingOrSynthetic ? undefined : summary.source,
  description: '',
  tags: [],
  upstream: { enabled: false, updateAvailable: false },
  usageStats: { totalDeployments: 0, activeProjects: 0, usageCount: 0 },
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  aliases: [],
  collection: collectionId,
};
```

**Issues**:
1. **Missing `collections` Array**: Only has `collection` (singular), not `collections` (plural)
   - Function has access to `allArtifacts` which should have this data
2. **Empty Metadata**: `description: ''`, `tags: []` hardcoded
   - These could be populated from matching artifact
3. **No Timestamps**: Uses current date for `createdAt/updatedAt`
   - Should come from the full artifact (if found) or API response

**Solution**: Look up artifact in `allArtifacts` array and merge/enrich its data, using centralized mapper as source of truth for field mappings.

---

## 6. Consolidation Recommendations

### Action 1: Create Entity Enrichment Helper

Create a new function to standardize the enrichment pattern:

```typescript
// lib/api/enrichment.ts
export function enrichEntityWithArtifactData(
  entity: Entity,
  artifact: Artifact | undefined,
  fallback?: { collectionId: string; collectionName: string }
): Entity {
  if (artifact) {
    return {
      ...entity,
      // Copy all relevant fields from artifact
      collections: artifact.collections,
      description: artifact.description || entity.description,
      tags: artifact.tags || entity.tags,
      aliases: artifact.aliases || entity.aliases,
      source: artifact.source || entity.source,
      author: artifact.author || entity.author,
      license: artifact.license || entity.license,
      version: artifact.version || entity.version,
      origin: artifact.origin || entity.origin,
      origin_source: artifact.origin_source || entity.origin_source,
      dependencies: artifact.dependencies || entity.dependencies,
      score: artifact.score || entity.score,
      upstream: artifact.upstream || entity.upstream,
      usageStats: artifact.usageStats || entity.usageStats,
      // Don't override project-specific fields (deployedAt, modifiedAt, projectPath)
    };
  }

  // Fallback when no matching artifact found
  return {
    ...entity,
    collections: fallback?.collectionId
      ? [{ id: fallback.collectionId, name: fallback.collectionName }]
      : undefined,
  };
}
```

**Usage**:
```typescript
// In project manage page (replace both locations 10 & 11)
const enrichedEntity = enrichEntityWithArtifactData(
  entity,
  matchingArtifact,
  {
    collectionId: entity.collection || undefined,
    collectionName: entity.collection === 'default' ? 'Default Collection' : entity.collection
  }
);
```

---

### Action 2: Fix enrichArtifactSummary Fallback

Use artifact data when available:

```typescript
function enrichArtifactSummary(
  summary: { name: string; type: string; version?: string | null; source: string },
  allArtifacts: Artifact[],
  collectionId?: string
): Artifact {
  // Try to find matching full artifact by name and type
  const fullArtifact = allArtifacts.find((a) => a.name === summary.name && a.type === summary.type);

  if (fullArtifact) {
    // If we have collection context and the full artifact lacks it, add it
    if (collectionId && !fullArtifact.collection && !fullArtifact.collections) {
      return {
        ...fullArtifact,
        collection: collectionId,
        collections: [{ id: collectionId, name: ... }]  // POPULATE FROM LOOKUP
      };
    }
    return fullArtifact;
  }

  // Fallback: Use centralized mapper to create minimal artifact
  return mapApiResponseToArtifact({
    id: `${summary.type}:${summary.name}`,
    name: summary.name,
    type: summary.type,
    version: summary.version || undefined,
    source: isSourceMissingOrSynthetic ? undefined : summary.source,
    collection: collectionId,
  }, 'collection');
}
```

---

### Action 3: Verify Indirect Mappings

**Files to check**:
- `lib/api/artifacts.ts` - Check `fetchArtifactsPaginated()` implementation
- `lib/api/context-entities.ts` - If used for entity fetching

Ensure these also use `mapApiResponseToArtifact()` for consistency.

---

## 7. Fields NOT Currently Mapped

**Potential missing fields from API responses**:
- `created_by`, `updated_by` (if API returns these)
- `category` (if API groups artifacts)
- `rating` or `reviews` (if marketplace-integrated)
- `deployment_config` (if project-specific configs)
- Any new fields added to API without mapper update

---

## 8. Impact Assessment

### Affected Components
1. **Collection Detail Modal**: Uses enriched artifacts, missing `collections` would show incomplete data
2. **Project Manage Page**: 2 duplicated enrichment functions, maintenance burden
3. **Entity Selection**: Cross-feature enrichment inconsistent between project and collection contexts

### Risk Level
- **Medium**: Missing `collections` array would cause UI to not show all collection memberships
- **Low**: Hard-coded collection names work but not i18n-friendly

---

## 9. Consolidation Checklist

- [ ] Create `enrichEntityWithArtifactData()` helper in `lib/api/enrichment.ts`
- [ ] Replace Location 10 (`app/projects/[id]/manage/page.tsx` lines 80-95) with helper
- [ ] Replace Location 9 (same file, lines 117-132) with helper (or remove if redundant)
- [ ] Update `enrichArtifactSummary()` to use mapper for fallback case
- [ ] Add `collections` array population in `enrichArtifactSummary()` fallback
- [ ] Verify `fetchArtifactsPaginated()` uses centralized mapper
- [ ] Add tests for enrichment helper
- [ ] Test collection badges render correctly with enriched data
- [ ] Update CLAUDE.md documentation with enrichment pattern

---

## 10. Appendix: Field Mapping Reference

### From API Response (`ArtifactResponse`)
```typescript
{
  id: string;
  name: string;
  type: string;
  scope?: string;                                    // → scope
  collection?: { id: string; name: string } | string;  // → collection (singular)
  collections?: Array<{ id: string; name: string; artifact_count?: number }>;  // → collections (array)
  project_path?: string;                              // → projectPath (project only)
  source?: string;                                    // → source
  origin?: string;                                    // → origin
  origin_source?: string | null;                      // → origin_source
  aliases?: string[];                                 // → aliases
  status?: string;                                    // → (via syncStatus)
  syncStatus?: string;                                // → syncStatus
  sync_status?: string;                               // → syncStatus
  error?: string | null;                              // → (affects syncStatus)
  conflictState?: { hasConflict: boolean; ... };      // → (affects syncStatus)
  metadata?: { description?, tags?, author?, license?, version? };
  description?: string;                               // → description (or from metadata)
  tags?: string[];                                    // → tags (or from metadata)
  author?: string;                                    // → author
  license?: string;                                   // → license
  version?: string;                                   // → version
  dependencies?: string[];                            // → dependencies
  upstream?: { tracking_enabled, current_sha, ... };  // → upstream
  usage_stats?: { total_deployments, ... };           // → usageStats
  usageStats?: { ... };                               // → usageStats
  score?: { confidence, trust_score, ... };           // → score
  added?: string;                                     // → (for createdAt fallback)
  updated?: string;                                   // → (for updatedAt fallback)
  created_at?: string;                                // → createdAt
  createdAt?: string;                                 // → createdAt
  updated_at?: string;                                // → updatedAt
  updatedAt?: string;                                 // → updatedAt
  deployed_at?: string;                               // → deployedAt
  deployedAt?: string;                                // → deployedAt
  modified_at?: string;                               // → modifiedAt
  modifiedAt?: string;                                // → modifiedAt
}
```

### To Artifact Type
```typescript
{
  id: string;
  name: string;
  type: ArtifactType;
  scope: ArtifactScope;
  collection?: string;
  collections?: CollectionRef[];
  projectPath?: string;                    // (project context)
  description?: string;
  tags?: string[];
  author?: string;
  license?: string;
  version?: string;
  dependencies?: string[];
  source?: string;
  origin?: 'local' | 'github' | 'marketplace';
  origin_source?: string;
  aliases?: string[];
  syncStatus: SyncStatus;
  upstream?: { enabled, url, version, currentSha, upstreamSha, updateAvailable, lastChecked };
  usageStats?: { totalDeployments, activeProjects, lastUsed, usageCount };
  score?: { confidence, trustScore, qualityScore, matchScore, lastUpdated };
  createdAt: string;
  updatedAt: string;
  deployedAt?: string;                      // (project context)
  modifiedAt?: string;                      // (project context)
}
```
