# Exact Code Locations: API Response to Entity Mapping

## Complete Location Index

### CANONICAL MAPPER (Source of Truth)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/lib/api/mappers.ts`

```
Line 1-8      : File header and documentation
Line 10-16    : Imports
Line 18-141   : Type definitions (ApiResponse interfaces)
Line 144-152  : MappingContext type definition

Line 181-233  : determineSyncStatus() function
                Determines if artifact is synced, outdated, modified, conflicted, or has error
                Uses priority: error > conflict > modified > outdated > synced

Line 265-423  : mapApiResponseToArtifact(response, context) - MAIN MAPPER
                ✅ Maps all 30+ fields from ArtifactResponse to Artifact
                ✅ Handles snake_case to camelCase conversion
                ✅ Flattens nested metadata to top-level
                ✅ Normalizes collection references (singular + array)
                ✅ Resolves timestamps with fallbacks
                ✅ Context-aware (collection vs project)

  Sub-sections:
  - Line 269-284   : Validate required fields (id, name, type)
  - Line 286-297   : Resolve timestamps
  - Line 299-332   : Flatten metadata + normalize collections
  - Line 334-335   : Determine sync status
  - Line 338-420   : Build artifact object with all fields
  - Line 422       : Return artifact

Line 444-449  : mapApiResponsesToArtifacts(responses, context)
                ✅ Batch wrapper for multiple responses

Line 470-490  : validateArtifactMapping(artifact)
                Validates required fields and timestamp format

Line 502-514  : createMinimalArtifact(overrides)
                Factory function for testing/placeholders
```

---

### HOOK-BASED MAPPINGS
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/useArtifacts.ts`

```
Line 1-21     : File header and imports
               ✅ Imports mapApiResponseToArtifact from mappers

Line 277-318  : fetchArtifactsFromApi(filters, sort) FUNCTION
               ❌ API: GET /artifacts
               Line 293-295: ✅ mapApiResponseToArtifact(item, 'collection')
                            Maps response.items array to Artifact[]

Line 320-331  : fetchArtifactFromApi(id) FUNCTION
               ❌ API: GET /artifacts/{id}
               Line 323: ✅ mapApiResponseToArtifact(artifact, 'collection')
                        Maps single response to Artifact

Line 336-347  : useArtifacts(filters, sort) HOOK
               Uses fetchArtifactsFromApi()

Line 352-360  : useArtifact(id) HOOK
               Uses fetchArtifactFromApi()

Line 365-390  : useUpdateArtifact() MUTATION HOOK
               ❌ API: PUT /artifacts/{id}
               Line 376: ✅ mapApiResponseToArtifact(response, 'collection')
                        Maps PUT response to Artifact

Line 437-473  : useUpdateArtifactTags() MUTATION HOOK
               ❌ API: PUT /artifacts/{id}/tags
               Line 464: ✅ mapApiResponseToArtifact(response, 'collection')
                        Maps PUT response to Artifact

Line 520-542  : useInfiniteArtifacts(options) HOOK
               ⚠️ Uses fetchArtifactsPaginated() (indirect)
               Need to verify mapping in lib/api/artifacts.ts
```

---

### COLLECTION PAGE MAPPINGS
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/collection/page.tsx`

```
Line 30       : Import statement
               ✅ import { mapApiResponseToArtifact, type ArtifactResponse }

Line 45-95    : enrichArtifactSummary(summary, allArtifacts, collectionId) FUNCTION
               ❌ DUPLICATE MANUAL MAPPING (NOT USING MAPPER)
               ❌ MISSING 'collections' array field
               ❌ HARD-CODED empty description, tags, aliases

               Implementation breakdown:
               Line 50-51   : Find matching artifact by name+type
               Line 52-59   : If found, return with collection added
               Line 61-95   : FALLBACK - Create minimal artifact from scratch
                             ❌ Missing: collections, author, license, origin, upstream, score, usageStats, dependencies

Line 354-356  : mapApiArtifactToArtifact(apiArtifact) FUNCTION
               ✅ Wrapper function
               ✅ return mapApiResponseToArtifact(apiArtifact, 'collection')

Line 359-479  : filteredArtifacts useMemo()
               Line 371      : ✅ page.items.map(mapApiArtifactToArtifact)
                             Maps collection-specific view artifacts
               Line 395      : ✅ page.items.map(mapApiArtifactToArtifact)
                             Maps all-collections view artifacts

Line 483-521  : availableTags useMemo()
               Line 490      : ✅ page.items.map(mapApiArtifactToArtifact)
                             Maps full artifacts for tag extraction
               Line 499      : ✅ page.items.map(mapApiArtifactToArtifact)
                             Maps full artifacts for tag extraction
```

---

### PROJECT DETAIL PAGE MAPPINGS
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/projects/[id]/page.tsx`

```
Line 31       : import type { Entity, EntityType } from '@/types/entity'
               (Legacy imports, but Entity is now alias for Artifact)

Line 76-300+  : ProjectDetailPageContent() COMPONENT
               ℹ️ Displays deployed artifacts
               ℹ️ Handles discovery modal
               ℹ️ NOT using enrichment logic (uses project-specific DeployedArtifact type)
```

---

### PROJECT MANAGE PAGE MAPPINGS
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/projects/[id]/manage/page.tsx`

```
Line 1-32     : File header, imports, types

Line 34-279   : ProjectManagePageContent(props) COMPONENT

  ❌ DUPLICATE MAPPING LOCATION #1
  Line 70-100    : useEffect() - Handle URL-based artifact selection
                  Line 77     : const matchingArtifact = artifactsData?.artifacts.find(...)
                  Line 80-88  : ❌ MANUAL ENRICHMENT (if artifact found)
                               ✅ Copies: collections, description, tags, aliases, source
                               ❌ Missing: author, license, version, origin, upstream, score, usageStats, dependencies
                  Line 89-95  : ❌ FALLBACK ENRICHMENT (no artifact match)
                               ❌ Hard-coded collection name: 'Default Collection'
                               ❌ Doesn't populate 'collections' array
                               Problem code:
                               ```
                               collections: entity.collection
                                 ? [{ id: entity.collection, name: entity.collection === 'default' ? 'Default Collection' : entity.collection }]
                                 : undefined,
                               ```

  ❌ DUPLICATE MAPPING LOCATION #2
  Line 109-138   : useCallback(handleEntityClick) - Handle entity click
                  Line 112    : const matchingArtifact = artifactsData?.artifacts.find(...)
                  Line 117-125: ❌ MANUAL ENRICHMENT - EXACT DUPLICATE of lines 80-88
                               Same issues as above
                  Line 126-132: ❌ FALLBACK ENRICHMENT - EXACT DUPLICATE of lines 89-95
                               Same issues as above

  Note: These two blocks are functionally identical - copy-paste duplication
```

---

### COLLECTION MANAGEMENT PAGE
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/manage/page.tsx`

```
Line 1-50     : File header, imports, component setup

Line 27-200+  : ManagePageContent() COMPONENT
               ✅ Uses useEntityLifecycle() hook which handles mapping
               ✅ No inline enrichment logic here
               ✅ Entities come pre-mapped from useEntityLifecycle()

               Note: The enrichment happens in the hook, not in the page
```

---

## Collection Badge Rendering

**Files that render collections**:
```
skillmeat/web/components/shared/collection-badge-stack.tsx
  → Expects artifact.collections: CollectionRef[]
  → Shows badges for each collection membership

skillmeat/web/components/shared/unified-card.tsx (Lines 60-61)
  → Imports CollectionBadgeStack
  → Renders if collections exist
```

**Issue**: If `collections` array is missing (as in enrichArtifactSummary fallback), badges won't render.

---

## Field Mapping Flow Diagram

```
API Response (snake_case)
       ↓
mapApiResponseToArtifact()
       ↓
   ↙     ↘
✅      ⚠️
Centralized  Inline/Fallback
Mapper       Enrichment
  (24        (4-16 fields)
  fields)         ↓
             enrichArtifactSummary()
                  enrichedEntity
                  (project manage)

Unified Artifact Type (camelCase)
             ↓
        Components
        - CollectionArtifactModal
        - ProjectArtifactModal
        - ArtifactCard
        - ArtifactList
```

---

## Summary: All Mapping Locations

| # | File | Function | Line(s) | Uses Mapper? | Issues |
|---|------|----------|---------|-------------|--------|
| 1 | `lib/api/mappers.ts` | `mapApiResponseToArtifact()` | 265-423 | N/A (IS mapper) | ✅ None |
| 2 | `lib/api/mappers.ts` | `mapApiResponsesToArtifacts()` | 444-449 | ✅ Calls #1 | ✅ None |
| 3 | `hooks/useArtifacts.ts` | `fetchArtifactsFromApi()` | 293-295 | ✅ Calls #1 | ✅ None |
| 4 | `hooks/useArtifacts.ts` | `fetchArtifactFromApi()` | 323 | ✅ Calls #1 | ✅ None |
| 5 | `hooks/useArtifacts.ts` | `useUpdateArtifact()` | 376 | ✅ Calls #1 | ✅ None |
| 6 | `hooks/useArtifacts.ts` | `useUpdateArtifactTags()` | 464 | ✅ Calls #1 | ✅ None |
| 7 | `hooks/useArtifacts.ts` | `useInfiniteArtifacts()` | 525-534 | ⚠️ Indirect | ⚠️ Verify |
| 8 | `app/collection/page.tsx` | `mapApiArtifactToArtifact()` | 354-356 | ✅ Calls #1 | ✅ None |
| 9 | `app/collection/page.tsx` | `filteredArtifacts` memo | 371, 395 | ✅ Uses #8 | ✅ None |
| 10 | `app/collection/page.tsx` | `availableTags` memo | 490, 499 | ✅ Uses #8 | ✅ None |
| 11 | `app/collection/page.tsx` | `enrichArtifactSummary()` | 69-94 | ❌ None | ⚠️ See Issues |
| 12 | `app/projects/[id]/manage/page.tsx` | URL artifact handler | 80-95 | ❌ None | ⚠️ CRITICAL |
| 13 | `app/projects/[id]/manage/page.tsx` | Entity click handler | 117-132 | ❌ None | ⚠️ CRITICAL |

**Issues in details**:

| Location | Missing Fields | Hard-coded Values | Duplication | Fix Priority |
|----------|-----------------|-------------------|-------------|--------------|
| #11 enrichArtifactSummary | collections, author, license, origin, upstream, score, usageStats (18 fields) | description: '', tags: [] | No (but incomplete) | Medium |
| #12 URL artifact handler | author, license, origin, upstream, score, usageStats (9+ fields) | 'Default Collection' name | YES (#13 identical) | HIGH |
| #13 Entity click handler | author, license, origin, upstream, score, usageStats (9+ fields) | 'Default Collection' name | YES (#12 identical) | HIGH |

---

## Quick Navigation

### To Use Mapper Correctly
1. Import: `import { mapApiResponseToArtifact } from '@/lib/api/mappers'`
2. Call: `const artifact = mapApiResponseToArtifact(apiResponse, 'collection')`
3. Context: `'collection'` or `'project'` determines scope and sync status logic

### To Fix Location #11
File: `app/collection/page.tsx`, Function: `enrichArtifactSummary()`
- Look up artifact in `allArtifacts` array
- Merge data using artifact as primary source
- Fall back to mapper for truly missing data

### To Fix Locations #12 & #13
File: `app/projects/[id]/manage/page.tsx`
- Create enrichment helper function
- Replace both handlers with single helper call
- Enrich with all artifact fields, not just 5

---

## Test Files

**Unit tests for mapper**:
`skillmeat/web/lib/api/mappers.test.ts` (Lines 1-250+)
- Tests all field mappings
- Tests timestamp resolution
- Tests metadata flattening
- Tests collection normalization
- Tests sync status determination
