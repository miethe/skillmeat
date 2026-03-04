# Tags Endpoint 404 Bug Investigation

**Date**: 2026-03-04
**Issue**: GET/POST/DELETE `/artifacts/{artifact_id}/tags` returns 404 when artifact IDs contain colons

## Root Cause Analysis

The bug is a **path parameter encoding/decoding mismatch** between frontend and backend for artifact IDs with colons (e.g., `skill:frontend-design`).

### Frontend (Web Client) - ENCODING

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/lib/api/tags.ts`

The frontend **correctly encodes** artifact IDs using `encodeURIComponent()`:

```typescript
// Line 126: Get artifact tags
export async function getArtifactTags(artifactId: string): Promise<Tag[]> {
  const response = await fetch(
    buildUrl(`/artifacts/${encodeURIComponent(artifactId)}/tags`)
  );
  // ...
}

// Line 138: Add tag to artifact
export async function addTagToArtifact(artifactId: string, tagId: string): Promise<void> {
  const response = await fetch(
    buildUrl(`/artifacts/${encodeURIComponent(artifactId)}/tags/${encodeURIComponent(tagId)}`),
    { method: 'POST' }
  );
  // ...
}

// Line 154: Remove tag from artifact
export async function removeTagFromArtifact(artifactId: string, tagId: string): Promise<void> {
  const response = await fetch(
    buildUrl(`/artifacts/${encodeURIComponent(artifactId)}/tags/${encodeURIComponent(tagId)}`),
    { method: 'DELETE' }
  );
  // ...
}
```

**What gets sent**:
- Input artifact ID: `skill:frontend-design`
- Encoded in URL: `/artifacts/skill%3Afrontend-design/tags`

### Backend (API Router) - DECODING ISSUE

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/artifacts.py`

The three tags endpoints (lines 7469-7755) receive the `artifact_id` path parameter:

```python
@router.get("/{artifact_id}/tags", ...)
async def get_artifact_tags(artifact_id: str, artifact_repo: ArtifactRepoDep):
    # artifact_id arrives as 'skill%3Afrontend-design' (URL-encoded)
    # FastAPI auto-decodes to 'skill:frontend-design' ✅

    # Line 7498: Try to look up artifact using repository
    artifact_dto = artifact_repo.get(artifact_id)  # ← PASSES 'skill:frontend-design'
    if not artifact_dto or not artifact_dto.uuid:
        raise HTTPException(404, f"Artifact '{artifact_id}' not found")  # ❌ 404 ERROR

@router.post("/{artifact_id}/tags/{tag_id}", ...)
async def add_tag_to_artifact(artifact_id: str, tag_id: str, artifact_repo: ArtifactRepoDep):
    # Same issue: artifact_id decoded from URL but lookup fails
    artifact_dto = artifact_repo.get(artifact_id)  # ← Line 7686
    if not artifact_dto or not artifact_dto.uuid:
        raise HTTPException(404, f"Artifact '{artifact_id}' not found")

@router.delete("/{artifact_id}/tags/{tag_id}", ...)
async def remove_tag_from_artifact(artifact_id: str, tag_id: str, artifact_repo: ArtifactRepoDep):
    # Same issue: artifact_id decoded from URL but lookup fails
    artifact_dto = artifact_repo.get(artifact_id)  # ← Line similar
```

### The Problem: Repository Lookup Fails

The issue is likely in **how the repository's `get()` method handles artifact IDs**:

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/repositories/local_artifact.py`

The `LocalArtifactRepository.get(artifact_id)` method probably:
1. Expects artifact_id in format `type:name` ✅
2. Splits on `:` to get type and name ✅
3. Searches filesystem/DB for artifact matching type and name ❌ **← This lookup may be case-sensitive or not handling edge cases**

### Artifact ID Path Parameter Contract (ADR-007)

**Reference**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/CLAUDE.md`

The CLAUDE.md file for routers documents:

> **Artifact ID Resolution (ADR-007)**: Path parameter `artifact_id` arrives as `type:name` (e.g., `skill:frontend-design`). Services/repositories expect `artifact_uuid` (hex UUID). Routers must resolve via `Artifact.filter_by(id=artifact_id).first()` → use `db_art.uuid` for downstream calls.

The tags endpoints ARE following this pattern correctly by:
1. Receiving `artifact_id` in path (auto-decoded by FastAPI)
2. Calling `artifact_repo.get(artifact_id)` to resolve to UUID
3. Using `artifact_dto.uuid` for downstream operations

**But the lookup is failing** for some artifact IDs.

## Suspected Root Cause

### Hypothesis 1: Case Sensitivity
The artifact ID in the URL might be encoded differently than how it's stored. For example:
- Frontend sends: `skill%3AFrontend-Design` (capital F/D)
- DB stores: `skill:frontend-design` (lowercase)
- Lookup fails due to case mismatch

### Hypothesis 2: Special Characters in Name
If artifact names contain special characters beyond colons (e.g., spaces, underscores), the encoding might not match filesystem/DB storage:
- Frontend sends: `agent%3Aprd-writer%202.0` (space encoded as %20)
- DB stores: `agent:prd-writer_2.0` (space as underscore)

### Hypothesis 3: Repository Implementation Bug
The `LocalArtifactRepository.get()` method might:
- Be using wrong comparison logic
- Not handle all artifact types
- Have a bug in the split logic for `type:name` parsing

## Affected Endpoints

All three artifact-tag association endpoints are at risk:

1. **GET** `/artifacts/{artifact_id}/tags` - Get tags for artifact
   - Line 7469-7509 in artifacts.py
   - Uses `artifact_repo.get(artifact_id)` at line 7498

2. **POST** `/artifacts/{artifact_id}/tags/{tag_id}` - Add tag to artifact
   - Line 7652-7739 in artifacts.py
   - Uses `artifact_repo.get(artifact_id)` at line 7686

3. **DELETE** `/artifacts/{artifact_id}/tags/{tag_id}` - Remove tag from artifact
   - Line 7742-7785 in artifacts.py
   - Uses `artifact_repo.get(artifact_id)` at line similar location

4. **PUT** `/artifacts/{artifact_id}/tags` - Update all tags for artifact
   - Line 7512-7649 in artifacts.py
   - Uses `artifact_repo.get(artifact_id)` indirectly through artifact lookup

## Investigation Needed

1. **Check LocalArtifactRepository.get() implementation**
   - File: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/repositories/local_artifact.py`
   - Verify it correctly handles `type:name` format
   - Check if lookup is case-sensitive
   - Verify it searches both filesystem and DB

2. **Test artifact ID resolution**
   - Create artifact with ID like `skill:frontend-design`
   - Test GET endpoint with encoded ID
   - Verify lookup returns artifact DTO
   - Check if uuid field is populated

3. **Check parse_artifact_id function**
   - File: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/artifacts.py:304`
   - This function splits artifact_id on `:` separator
   - Used in other endpoints (PUT /parameters, etc.)
   - May need to be applied to tags endpoints

4. **Verify URL encoding consistency**
   - Frontend uses `encodeURIComponent(artifactId)`
   - Backend receives URL-decoded value from FastAPI
   - Verify no intermediate encoding/decoding issues

## Files Involved

### Backend
- **Main Routers**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/artifacts.py` (lines 7469-7785)
- **Repository Interface**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/interfaces/repositories.py`
- **Repository Implementation**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/repositories/local_artifact.py`
- **Artifact Model**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/artifact.py`

### Frontend
- **API Client**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/lib/api/tags.ts` (lines 125-165)
- **Hooks**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/use-tags.ts` (lines 90-97)

## Next Steps

1. Delegate to codebase-explorer to find LocalArtifactRepository.get() implementation
2. Test artifact ID resolution with various ID formats
3. Add logging to tags endpoints to see what artifact_id values are received
4. Create unit tests for artifact ID resolution with colons and special characters
5. Run integration tests for all three artifact-tag endpoints
