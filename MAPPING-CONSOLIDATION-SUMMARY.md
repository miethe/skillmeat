# Mapping Consolidation Summary

## Quick Reference: Where API Responses Map to Entities

### GOOD (Using Centralized Mapper)
```
✅ lib/api/mappers.ts (CANONICAL)
   └─ mapApiResponseToArtifact()         → All 30+ fields mapped correctly
   └─ mapApiResponsesToArtifacts()       → Batch wrapper

✅ hooks/useArtifacts.ts
   ├─ fetchArtifactsFromApi()            → Line 293-295
   ├─ fetchArtifactFromApi()             → Line 323
   ├─ useUpdateArtifact()                → Line 376
   └─ useUpdateArtifactTags()            → Line 464

✅ app/collection/page.tsx
   ├─ mapApiArtifactToArtifact()         → Lines 354-356 (wrapper)
   ├─ filteredArtifacts useMemo          → Lines 371, 395
   └─ availableTags useMemo              → Lines 490, 499
```

### NEEDS ATTENTION (Duplicate/Partial Mapping)
```
⚠️ app/collection/page.tsx
   └─ enrichArtifactSummary()            → Lines 69-94
      ❌ Missing: collections array (even though function has access)
      ❌ Hard-coded: empty description, tags, aliases
      ❌ Issue: Creates incomplete fallback artifacts

⚠️ app/projects/[id]/manage/page.tsx
   ├─ URL artifact selection             → Lines 80-95
   │  ❌ Only maps 5 of 30+ fields
   │  ❌ Hard-coded collection name mapping
   │  ❌ Uses spread operator (propagates stale data)
   │
   └─ Entity click handler               → Lines 117-132
      ❌ EXACT DUPLICATE of above
      ❌ Same issues repeated
```

---

## Critical Issues Found

### Issue #1: Missing `collections` Array in Fallback Mapping

**Location**: `app/collection/page.tsx`, line 69-94 (`enrichArtifactSummary()`)

**Problem**:
- Function only populates `collection` (singular string)
- Doesn't populate `collections` (array of objects)
- Even though it has `allArtifacts` parameter with full data

**Impact**:
- Collection badges won't show all artifact memberships
- Inconsistent with API response schema

**Example**:
```typescript
// Current (INCOMPLETE)
return {
  ...
  collection: collectionId,  // Only singular
  // Missing: collections: [{ id, name, artifact_count }]
};
```

---

### Issue #2: Duplicate Enrichment Logic

**Location**: `app/projects/[id]/manage/page.tsx`, lines 80-95 AND 117-132

**Problem**:
- Exact same enrichment code in two handlers
- Manually copies only 5 fields (collections, description, tags, aliases, source)
- Ignores 25+ other fields available in artifact

**Impact**:
- Maintenance burden: Fix in two places
- Incomplete artifact enrichment
- Project detail modals missing metadata

**Missing Fields**:
- Metadata: author, license, version, dependencies
- Origin info: origin, origin_source
- Tracking: upstream, score, usageStats
- Timestamps: deployedAt, modifiedAt

**Example**:
```typescript
// Current (DUPLICATE & INCOMPLETE)
const enrichedEntity: Entity = matchingArtifact
  ? {
      ...entity,
      collections: matchingArtifact.collections,     // Only 1 of 30+ fields
      description: matchingArtifact.description || entity.description,
      tags: matchingArtifact.tags || entity.tags,
      aliases: matchingArtifact.aliases || entity.aliases,
      source: matchingArtifact.source || entity.source,
      // Missing: author, license, origin, upstream, score, usageStats, etc.
    }
  : { ... };
```

---

### Issue #3: Hard-Coded Collection Names

**Location**: `app/projects/[id]/manage/page.tsx`, lines 92-94

**Problem**:
```typescript
collections: entity.collection
  ? [{ id: entity.collection, name: entity.collection === 'default' ? 'Default Collection' : entity.collection }]
  : undefined,
```

**Issues**:
- Hard-coded English name ('Default Collection')
- Not i18n-friendly
- Should get actual collection name from collections API
- What if collection is deleted?

---

## Consolidation Plan

### Step 1: Create Enrichment Helper
```typescript
// lib/api/enrichment.ts
export function enrichEntityWithArtifactData(
  entity: Entity,
  artifact: Artifact | undefined,
  fallbackCollectionId?: string
): Entity {
  if (artifact) {
    return {
      ...entity,
      // Copy ALL relevant fields
      ...artifact,
      // Preserve entity-specific fields
      id: entity.id,  // Keep entity ID
      projectPath: entity.projectPath,
      deployedAt: entity.deployedAt,
      modifiedAt: entity.modifiedAt,
    };
  }

  return entity;  // Return unchanged if no artifact match
}
```

### Step 2: Update Project Manage Page
```typescript
// Replace lines 80-95 AND 117-132 with:
const enrichedEntity = enrichEntityWithArtifactData(
  entity,
  matchingArtifact
);
```

### Step 3: Fix enrichArtifactSummary Fallback
```typescript
// app/collection/page.tsx, lines 69-94
function enrichArtifactSummary(
  summary: SummaryData,
  allArtifacts: Artifact[],
  collectionId?: string
): Artifact {
  const fullArtifact = allArtifacts.find((a) =>
    a.name === summary.name && a.type === summary.type
  );

  if (fullArtifact) {
    // Enrich with collections array if needed
    if (collectionId && !fullArtifact.collections) {
      return {
        ...fullArtifact,
        collections: [{
          id: collectionId,
          name: 'Collection' // Or fetch actual name
        }]
      };
    }
    return fullArtifact;
  }

  // FALLBACK: Use mapper for consistency
  return mapApiResponseToArtifact({
    id: `${summary.type}:${summary.name}`,
    name: summary.name,
    type: summary.type,
    version: summary.version || undefined,
    source: summary.source,
    collection: collectionId,
  }, 'collection');
}
```

### Step 4: Verify Indirect Mappings
Check these files use centralized mapper:
- [ ] `lib/api/artifacts.ts` - `fetchArtifactsPaginated()`
- [ ] `lib/api/context-entities.ts` - entity fetching
- [ ] `hooks/useEntityLifecycle.tsx` - entity lifecycle

---

## Field Mapping Audit Table

| Field | Mapper | enrichArtifactSummary | ProjectManage |
|-------|--------|----------------------|---------------|
| id | ✅ | ❌ | ✅ |
| name | ✅ | ✅ | ✅ |
| type | ✅ | ✅ | ✅ |
| scope | ✅ | ❌ | ✅ |
| **collection** (singular) | ✅ | ✅ | ✅ |
| **collections** (array) | ✅ | ❌ | ✅ |
| description | ✅ | ❌ | ✅ |
| tags | ✅ | ❌ | ✅ |
| author | ✅ | ❌ | ❌ |
| license | ✅ | ❌ | ❌ |
| version | ✅ | ✅ | ❌ |
| source | ✅ | ✅ | ✅ |
| origin | ✅ | ❌ | ❌ |
| origin_source | ✅ | ❌ | ❌ |
| aliases | ✅ | ❌ | ✅ |
| dependencies | ✅ | ❌ | ❌ |
| syncStatus | ✅ | ❌ | ✅ |
| upstream | ✅ | ❌ | ❌ |
| usageStats | ✅ | ❌ | ❌ |
| score | ✅ | ❌ | ❌ |
| createdAt | ✅ | ❌ | ✅ |
| updatedAt | ✅ | ❌ | ✅ |
| deployedAt | ✅ | ❌ | ✅ |
| modifiedAt | ✅ | ❌ | ✅ |
| projectPath | ✅ | ❌ | ✅ |

**Summary**:
- Mapper: 24/24 fields ✅
- enrichArtifactSummary: 4/24 fields (17%) ❌
- ProjectManage: 16/24 fields (67%) ❌

---

## Testing Checklist

After consolidation:

- [ ] Collection detail modal shows all collection badges
- [ ] Project manage page shows full artifact metadata when enriched
- [ ] Entity selection from URL works with enriched data
- [ ] No data loss when enriching project entities
- [ ] Fallback mapping creates valid artifacts
- [ ] Collection names resolve correctly (not hard-coded)
- [ ] Duplicate code removed (verification of unique functions)

---

## Files Affected

### Files to Modify
1. `skillmeat/web/lib/api/enrichment.ts` - CREATE (new file)
2. `skillmeat/web/app/collection/page.tsx` - UPDATE enrichArtifactSummary() (lines 69-94)
3. `skillmeat/web/app/projects/[id]/manage/page.tsx` - REPLACE enrichment logic (lines 80-95, 117-132)

### Files to Verify
1. `skillmeat/web/lib/api/artifacts.ts` - Check fetchArtifactsPaginated()
2. `skillmeat/web/lib/api/context-entities.ts` - Check entity fetching
3. `skillmeat/web/hooks/useEntityLifecycle.tsx` - Check lifecycle mapping

---

## Estimated Impact

**Lines of Code**:
- Code removed: ~30 lines (duplicate enrichment)
- Code added: ~40 lines (enrichment helper + fixes)
- Net change: +10 lines

**Maintenance Benefits**:
- Single source of truth for enrichment logic
- Easier to add new fields (only mapper needs update)
- Consistent behavior across collection/project contexts

**Risk Level**: Low
- Changes are localized to enrichment functions
- Centralized mapper already tested (mappers.test.ts)
- Fallback cases remain unchanged
