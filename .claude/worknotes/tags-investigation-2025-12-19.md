# Tags Feature Investigation - Where Tags Are Being Lost

**Date**: 2025-12-19
**Issue**: Tags saved in ParameterEditorModal are not being displayed on artifact cards or in collection views.

## Executive Summary

Tags are being **saved successfully to the manifest** but are **not being returned by the API**. The backend is missing the `tags` field in the `ArtifactResponse` schema.

## Root Cause Analysis

### Backend (Persistence) - WORKING

Tags ARE saved correctly:
1. **ParameterEditorModal** sends tags via HTTP PUT to `/artifacts/{artifact_id}/parameters` ✅
2. **update_artifact_parameters** router handler receives tags and saves them: `artifact.tags = params.tags` (line 2108 in `/skillmeat/api/routers/artifacts.py`) ✅
3. **Artifact.to_dict()** serializes tags to TOML: `result["tags"] = self.tags` (lines 193-194 in `/skillmeat/core/artifact.py`) ✅
4. **CollectionManager.save_collection()** writes manifest atomically (line 2132) ✅
5. **Artifact.from_dict()** deserializes tags from TOML: `tags=data.get("tags", [])` (line 223 in `/skillmeat/core/artifact.py`) ✅

**Verification**: Tags in manifest.toml after update:
```toml
[[artifacts]]
name = "canvas-design"
type = "skill"
...
tags = ["design", "canvas"]  # Present in manifest
```

### Backend (Retrieval) - BROKEN

Tags are NOT being returned in the API response:
1. **get_artifact()** endpoint calls `artifact_to_response(artifact)` (line 1580) ✅
2. **artifact_to_response()** converts Artifact to ArtifactResponse BUT:
   - Includes metadata tags (from artifact.metadata.tags) ❌ WRONG LOCATION
   - DOES NOT include artifact.tags (the direct tags field) ❌ MISSING
   - ArtifactResponse schema has NO `tags` field ❌ SCHEMA GAP

**Code location**: `/skillmeat/api/routers/artifacts.py:420-481` (artifact_to_response function)

Current response construction (line 470-481):
```python
return ArtifactResponse(
    id=...,
    name=...,
    type=...,
    source=...,
    version=...,
    aliases=...,
    metadata=metadata_response,      # Tags from metadata.tags (wrong)
    upstream=upstream_response,
    added=...,
    updated=...,
    # MISSING: tags=artifact.tags
)
```

### API Schema Gap

**File**: `/skillmeat/api/schemas/artifacts.py`

The `ArtifactResponse` class (lines 153-202) is missing a `tags` field:
- Has: id, name, type, source, version, aliases, metadata, upstream, deployment_stats, added, updated
- Missing: **tags** (should be at root level, not in metadata)

The schema DOES have tags in:
- `ArtifactMetadataResponse` (line 109) - metadata.tags
- `ParameterUpdateRequest` (line 31) - request body
- `ParameterEditorRequest` (line 346) - request body

But NOT in `ArtifactResponse` which is what gets returned to clients.

### Frontend (Cache Invalidation) - WORKING

After tags are saved, cache is properly invalidated:
1. **ParameterEditorModal.onSave()** calls handleSaveParameters() ✅
2. **handleSaveParameters()** calls `await updateParameters()` mutation ✅
3. **useEditArtifactParameters()** hook in hooks/useDiscovery.ts (line 123):
   - Calls PUT endpoint ✅
   - On success, invalidates queries: ✅
     ```typescript
     queryClient.invalidateQueries({ queryKey: ['artifacts', 'detail', artifactId] });
     queryClient.invalidateQueries({ queryKey: ['artifacts', 'list'] });
     ```
4. **unified-entity-modal.tsx** calls `refetch()` after save (line 892) ✅

Everything is being refetched, but the API isn't returning tags in the response.

### Frontend (Display) - READY BUT NO DATA

Frontend types are ready to display tags:
1. **Artifact type** (`/skillmeat/web/types/artifact.ts`):
   - Has metadata.tags (line 19) - for metadata context
   - Missing direct tags field in Artifact interface

2. **Components know about tags**:
   - ParameterEditorModal accepts and sends tags ✅
   - No visible tag display components yet, but infrastructure ready

## Issues Found

### Critical Issues

1. **API Schema Missing `tags` Field** (BLOCKER)
   - File: `/skillmeat/api/schemas/artifacts.py` line 153
   - ArtifactResponse needs `tags: List[str]` field
   - Should be at root level with other artifact properties

2. **artifact_to_response Not Mapping Tags** (BLOCKER)
   - File: `/skillmeat/api/routers/artifacts.py` line 420
   - Function doesn't pass `artifact.tags` to ArtifactResponse
   - Should map artifact.tags → response.tags

### Non-Critical Issues

3. **Frontend Missing Direct Tags Field**
   - File: `/skillmeat/web/types/artifact.ts` line 38
   - Artifact interface should have `tags?: string[]` at root
   - Currently tags only in metadata, but artifact has its own tags storage

4. **Confusion Between Two Tag Locations**
   - artifact.tags (root level in Artifact model) - used for organizational tags
   - artifact.metadata.tags (in metadata) - context-specific metadata tags
   - API needs to return both or clarify which one is used

## Fix Summary

### Required Changes

1. **Add `tags` field to ArtifactResponse schema**
   ```python
   tags: List[str] = Field(
       default_factory=list,
       description="Artifact tags",
   )
   ```

2. **Update artifact_to_response() to map tags**
   ```python
   return ArtifactResponse(
       ...
       tags=artifact.tags,  # Add this line
       metadata=metadata_response,
       ...
   )
   ```

3. **Update frontend Artifact type**
   ```typescript
   export interface Artifact {
       ...
       tags?: string[];  // Add this line
       metadata: ArtifactMetadata;
       ...
   }
   ```

### Verification

After fix, tags will flow:
1. Save: ParameterEditorModal → API endpoint → artifact.tags → manifest.toml ✅
2. Retrieve: manifest.toml → artifact.tags → ArtifactResponse.tags → frontend ✅
3. Display: artifact.tags → component rendering (ready) ✅

## Data Flow Diagram

```
Frontend Save:
ParameterEditorModal → PUT /artifacts/{id}/parameters → artifact.tags = [...]
→ manifest.toml saved ✅

Frontend Retrieve (BROKEN):
manifest.toml → artifact.tags loaded ✅
→ artifact_to_response() MISSING tags field ❌
→ ArtifactResponse has no tags field ❌
→ Frontend receives null/undefined for tags ❌

After Fix:
manifest.toml → artifact.tags loaded ✅
→ artifact_to_response() maps to response.tags ✅
→ ArtifactResponse includes tags field ✅
→ Frontend receives tags in artifact.tags ✅
→ Components render tags ✅
```

## Files Involved

### Backend
- `/skillmeat/api/routers/artifacts.py` (lines 420-481, 2106-2110)
- `/skillmeat/api/schemas/artifacts.py` (lines 153-202)
- `/skillmeat/core/artifact.py` (lines 122, 193-194, 223)

### Frontend
- `/skillmeat/web/components/discovery/ParameterEditorModal.tsx` (working)
- `/skillmeat/web/components/entity/unified-entity-modal.tsx` (line 1811)
- `/skillmeat/web/hooks/useDiscovery.ts` (lines 123-147, working)
- `/skillmeat/web/types/artifact.ts` (line 38)

## Status

- Backend persistence: ✅ WORKING
- Backend retrieval: ❌ BROKEN (schema + mapping)
- Frontend cache: ✅ WORKING
- Frontend display: ⏳ READY (no data coming from API)

## Next Steps

1. Add `tags` field to ArtifactResponse schema
2. Update artifact_to_response() to map artifact.tags
3. Update frontend Artifact type to include tags
4. Test end-to-end: save tags → retrieve → display
