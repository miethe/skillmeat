# Collections Tab Not Displaying - Investigation Results

**Date**: 2026-01-11
**Status**: Root cause identified
**Issue**: Collections tab in unified entity modal shows empty "This artifact is not in any collection" message for artifacts that should have collection data.

---

## Problem Summary

The Collections tab (`modal-collections-tab.tsx`) displays no collection data even when artifacts belong to multiple collections. Users cannot see or manage collection membership through the UI.

---

## Root Cause Analysis

The issue is a **data pipeline break** across three layers:

### 1. Backend Layer: `artifact_to_response()` - `artifacts.py:433-512`

**Status**: ✓ Code exists but non-functional

The backend function checks for collections data:
```python
# Line 483-497: artifact_to_response()
collections_response = []
if hasattr(artifact, "collections") and artifact.collections:
    for collection in artifact.collections:
        collections_response.append(
            ArtifactCollectionInfo(...)
        )
```

**Problem**: `artifact.collections` is **never populated** because:
- The codebase uses **file-based storage** (not database)
- Artifact model from `core/artifact.py` doesn't have a many-to-many relationship with collections
- No code builds/populates the `collections` list when loading artifacts

**Impact**: `collections_response` remains empty `[]` in all responses

### 2. API Response Schema: `artifacts.py:164-222`

**Status**: ✓ Schema is correct

The `ArtifactResponse` schema correctly includes:
```python
# Line 213-216: ArtifactResponse
collections: List[ArtifactCollectionInfo] = Field(
    default_factory=list,
    description="Collections this artifact belongs to (many-to-many relationship)",
)
```

**But**: The schema has `default_factory=list`, so when `artifact_to_response()` returns empty list, the response includes `collections: []`

### 3. Frontend Layer: `collection/page.tsx:87-132` & `modal-collections-tab.tsx:47-90`

**Status**: ✓ Conversion logic is correct

The conversion function `artifactToEntity()` properly maps artifact data:
```typescript
// collection/page.tsx:116-130
collections: artifact.collections && artifact.collections.length > 0
  ? artifact.collections.map(collection => ({
      id: collection.id,
      name: collection.name,
      artifact_count: collection.artifact_count || 0,
    }))
  : artifact.collection
    ? [
        {
          id: artifact.collection.id,
          name: artifact.collection.name,
          artifact_count: 0,
        },
      ]
    : [],
```

**With TODO comment**: Line 115 explicitly states the gap:
```typescript
// TODO: Backend needs to populate artifact.collections with ALL collections the artifact belongs to
```

**But**: Since backend always returns `collections: []`, the fallback to `artifact.collection` is used, showing only the primary collection (if available).

### 4. UI Component: `modal-collections-tab.tsx:47-90`

**Status**: ✓ Component logic is correct

The component displays what it receives:
```typescript
// Line 90: ModalCollectionsTab
const artifactCollections = entity.collections || [];
```

**Result**: `entity.collections` is always empty array because:
1. Backend returns `collections: []`
2. Frontend fallback only includes primary collection
3. Artifact may not have `collection` field set in some contexts

---

## Data Flow

```
Backend:
  artifact.load()
    ↓
  artifact.collections = [] (NEVER POPULATED)
    ↓
  artifact_to_response() → collections_response = []
    ↓
API Response:
  {
    "collections": [],
    "collection": { "id": "...", "name": "..." }
  }
    ↓
Frontend:
  mapApiArtifact() → artifact.collections = []
    ↓
  artifactToEntity()
    → Falls back to artifact.collection (single) since collections array is empty
    ↓
  entity.collections = [single collection] or []
    ↓
UI:
  ModalCollectionsTab displays entity.collections
  → Shows empty state if artifact.collection not set
```

---

## Why This Matters

**Intended Design**:
- Each artifact can belong to **multiple collections** (many-to-many)
- Collections tab should list ALL collections containing the artifact
- User can add/remove from multiple collections

**Current Behavior**:
- Only shows primary collection (from `artifact.collection` field)
- Cannot see secondary collections even though API schema supports it
- User cannot manage full collection membership

---

## Backend Data Structure

The backend needs to:
1. **Identify all collections** containing an artifact
   - Currently: Only tracks primary collection in `artifact.collection`
   - Needed: Build list of all collections where artifact exists

2. **Populate `collections` field** in response
   - Currently: `artifact.collections` attribute doesn't exist/isn't set
   - Needed: Query all collections and find which ones contain this artifact

3. **Include artifact count** per collection
   - Currently: Not available in file-based model
   - Needed: Count artifacts in each collection

---

## Affected Files

### Backend (Python)
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/artifacts.py`
  - Line 433-512: `artifact_to_response()` - Checks but never finds `artifact.collections`
  - Line 1706-1711: `list_artifacts()` - Calls `artifact_to_response()` with empty collections

### Frontend (TypeScript)
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/useArtifacts.ts`
  - Line 62-66: API interface expects `collections` field
  - Line 288-347: `mapApiArtifact()` - Maps empty `artifact.collections` from API

- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/collection/page.tsx`
  - Line 87-132: `artifactToEntity()` - Has TODO acknowledging backend gap
  - Falls back to single `artifact.collection` when `artifact.collections` is empty

- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/entity/modal-collections-tab.tsx`
  - Line 47-90: `ModalCollectionsTab` - Displays `entity.collections` (which is empty)
  - Line 140-162: Empty state message shown to users

---

## To Fix This Issue

The fix requires backend work:

1. **In `artifact_to_response()`** (or earlier in loading):
   ```python
   # Build list of ALL collections containing this artifact
   collections_response = []

   # Iterate through all collections and find which ones have this artifact
   for coll_name in collection_mgr.list_collections():
       try:
           coll = collection_mgr.load_collection(coll_name)
           if coll.find_artifact(artifact.name, artifact.type):
               collections_response.append(
                   ArtifactCollectionInfo(
                       id=coll_name,
                       name=coll_name,
                       artifact_count=len(coll.artifacts)
                   )
               )
       except Exception:
           continue
   ```

2. **Add to Artifact model** (if needed):
   ```python
   # In core/artifact.py - Add a method to find all collections
   def get_all_collections(self, collection_mgr) -> List[Collection]:
       """Find all collections containing this artifact"""
       collections = []
       for coll_name in collection_mgr.list_collections():
           coll = collection_mgr.load_collection(coll_name)
           if coll.find_artifact(self.name, self.type):
               collections.append(coll)
       return collections
   ```

3. **Update performance**: Consider caching if querying all collections is slow

---

## Verification Points

To confirm this analysis:

1. **Backend API Test**:
   ```bash
   curl http://localhost:8080/api/v1/artifacts
   # Look for "collections" field in response
   # Currently: "collections": []
   # Expected: "collections": [{"id": "...", "name": "...", "artifact_count": N}, ...]
   ```

2. **Frontend State**:
   - Open browser DevTools → Network tab
   - Click artifact to open modal
   - Check API response body for `/artifacts` endpoint
   - Verify `collections` field (should be non-empty if artifact in multiple collections)

3. **UI Check**:
   - Open Collections tab in modal
   - Should show all collections artifact belongs to
   - Currently shows empty state or single collection

---

## Related Code References

**API Schema Definition**:
- `skillmeat/api/schemas/artifacts.py:213-216` - ArtifactResponse.collections field

**Frontend Type Mapping**:
- `skillmeat/web/hooks/useArtifacts.ts:62-66` - ApiArtifact.collections interface
- `skillmeat/web/types/artifact.ts` - Artifact type definition (if exists)

**Collection Relationship**:
- `skillmeat/web/types/collections.ts` - Collection type (should match backend ArtifactCollectionInfo)
- `skillmeat/web/types/entity.ts:331` - Entity.collections field definition

---

## Summary

**Gap**: Backend doesn't populate artifact.collections with list of ALL collections containing the artifact

**Impact**: Collections tab shows empty state even when artifact belongs to multiple collections

**Fix Location**: `skillmeat/api/routers/artifacts.py` - `artifact_to_response()` function needs to query and populate the collections list

**Estimated Effort**: Medium
- Need to understand collection loading/querying in backend
- Performance impact depends on collection count and artifact lookup time
- May need caching layer

