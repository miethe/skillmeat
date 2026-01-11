# Collections-Artifacts Integration - Implementation Guide

**Date**: 2026-01-11
**Status**: Analysis complete - Ready for implementation

---

## Current State

The collections-artifacts many-to-many relationship is **fully defined in the database layer** but **incomplete in the API layer**.

**What works**:
- Database has `CollectionArtifact` junction table ✅
- Artifact ORM model has `collections` relationship with eager loading ✅
- Frontend types define `Artifact.collections` field ✅
- Frontend UI logic has fallback to handle missing data ✅

**What's missing**:
- API schema (`ArtifactResponse`) doesn't include `collections` field ❌
- API conversion function (`artifact_to_response`) doesn't populate it ❌

---

## Implementation: Add Collections to API Response

### Step 1: Update API Schema

**File**: `skillmeat/api/schemas/artifacts.py`

**Location**: Around line 153 in `ArtifactResponse` class

**Change**: Add `collections` field to response model

```python
# In ArtifactResponse class (after line 207)
class ArtifactResponse(BaseModel):
    """Response schema for a single artifact."""

    id: str
    name: str
    type: str
    source: str
    version: str
    aliases: List[str] = Field(
        default_factory=list,
        description="Artifact aliases",
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Artifact tags",
    )
    metadata: Optional[ArtifactMetadataResponse] = None
    upstream: Optional[ArtifactUpstreamInfo] = None
    deployment_stats: Optional["DeploymentStatistics"] = None
    added: datetime
    updated: datetime

    # ADD THIS:
    collections: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Collections containing this artifact",
        examples=[
            [
                {"id": "col-1", "name": "default", "artifact_count": 42},
                {"id": "col-2", "name": "data-processing", "artifact_count": 15},
            ]
        ],
    )

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                # ... existing example fields ...
                "collections": [
                    {"id": "col-1", "name": "default"},
                    {"id": "col-2", "name": "data-processing"},
                ],
            }
        }
```

**Why this structure**:
- `Dict[str, Any]` is flexible for optional `artifact_count`
- Alternative: Create a dedicated `CollectionRef` Pydantic model:

```python
class CollectionRef(BaseModel):
    id: str
    name: str
    artifact_count: Optional[int] = None

class ArtifactResponse(BaseModel):
    # ... existing fields ...
    collections: List[CollectionRef] = Field(default_factory=list)
```

### Step 2: Update Conversion Function

**File**: `skillmeat/api/routers/artifacts.py`

**Location**: Line 432 in `artifact_to_response` function

**Current Code** (lines 432-494):
```python
def artifact_to_response(
    artifact,
    drift_status: Optional[str] = None,
    has_local_modifications: Optional[bool] = None,
) -> ArtifactResponse:
    """Convert Artifact model to API response schema."""
    # ... existing conversion logic ...

    return ArtifactResponse(
        id=f"{artifact.type.value}:{artifact.name}",
        name=artifact.name,
        type=artifact.type.value,
        source=artifact.upstream if artifact.origin == "github" else "local",
        version=version,
        aliases=[],
        tags=artifact.tags or [],
        metadata=metadata_response,
        upstream=upstream_response,
        added=artifact.added,
        updated=artifact.last_updated or artifact.added,
    )
```

**Modified Code**:
```python
def artifact_to_response(
    artifact,
    drift_status: Optional[str] = None,
    has_local_modifications: Optional[bool] = None,
) -> ArtifactResponse:
    """Convert Artifact model to API response schema."""
    # ... existing conversion logic ...

    # NEW: Convert collections relationship
    collections_list = []
    if hasattr(artifact, 'collections') and artifact.collections:
        for collection in artifact.collections:
            collection_info = {
                'id': collection.id,
                'name': collection.name,
            }
            # Optional: Add artifact count if relationship loaded
            if hasattr(collection, 'collection_artifacts'):
                collection_info['artifact_count'] = len(collection.collection_artifacts)
            collections_list.append(collection_info)

    return ArtifactResponse(
        id=f"{artifact.type.value}:{artifact.name}",
        name=artifact.name,
        type=artifact.type.value,
        source=artifact.upstream if artifact.origin == "github" else "local",
        version=version,
        aliases=[],
        tags=artifact.tags or [],
        metadata=metadata_response,
        upstream=upstream_response,
        added=artifact.added,
        updated=artifact.last_updated or artifact.added,
        collections=collections_list,  # NEW
    )
```

**What this does**:
1. Checks if `artifact.collections` relationship exists (it will, due to ORM setup)
2. Iterates through each collection in the relationship
3. Extracts `id` and `name` (always available)
4. Optionally adds `artifact_count` if `collection_artifacts` is loaded
5. Returns all collections in the response

### Step 3: Verify Frontend is Ready

**File**: `skillmeat/web/types/artifact.ts`

**Current Code** (lines 60-73):
```typescript
export interface Artifact {
  // ... other fields ...

  collection?: {
    id: string;
    name: string;
  };

  /**
   * All collections this artifact belongs to (many-to-many relationship)
   * TODO: Backend needs to populate this field with data from CollectionArtifact table
   */
  collections?: {
    id: string;
    name: string;
    artifact_count?: number;
  }[];
}
```

**Action**: No changes needed! Frontend is already prepared.

The `artifactToEntity()` function in `app/collection/page.tsx` will automatically use the populated `collections` array once the backend provides it.

### Step 4: Update Frontend Comment (Optional)

**File**: `skillmeat/web/app/collection/page.tsx`

**Location**: Lines 113-115

**Current Comment**:
```typescript
// Collections array for the Collections tab in unified entity modal
// Priority: artifact.collections (array) > artifact.collection (single) > empty array
// TODO: Backend needs to populate artifact.collections with ALL collections the artifact belongs to
```

**Updated Comment** (after implementation):
```typescript
// Collections array for the Collections tab in unified entity modal
// Priority: artifact.collections (array) > artifact.collection (single) > empty array
// Backend now populates artifact.collections from CollectionArtifact junction table
```

---

## Testing Plan

### Unit Tests

**File**: `skillmeat/api/tests/test_artifacts_routes.py`

**Add test**:
```python
def test_artifact_response_includes_collections():
    """Verify ArtifactResponse includes all collections containing artifact."""
    from skillmeat.api.routers.artifacts import artifact_to_response
    from skillmeat.core.artifact import ArtifactType

    # Create mock artifact with collections
    artifact = Mock()
    artifact.type = ArtifactType.SKILL
    artifact.name = "pdf"
    artifact.metadata = Mock(
        title="PDF Processor",
        description="Process PDFs",
        author="Anthropic",
        license="MIT",
        version="1.0.0",
        tags=["document", "pdf"],
        dependencies=[],
    )
    artifact.origin = "local"
    artifact.upstream = None
    artifact.resolved_sha = None
    artifact.version_spec = "latest"
    artifact.added = datetime(2024, 1, 1)
    artifact.last_updated = datetime(2024, 1, 1)

    # Mock collections relationship
    col1 = Mock()
    col1.id = "col-1"
    col1.name = "default"
    col1.collection_artifacts = []

    col2 = Mock()
    col2.id = "col-2"
    col2.name = "data-processing"
    col2.collection_artifacts = []

    artifact.collections = [col1, col2]
    artifact.tags = ["document"]

    # Convert to response
    response = artifact_to_response(artifact)

    # Verify collections are included
    assert response.collections is not None
    assert len(response.collections) == 2
    assert response.collections[0]["id"] == "col-1"
    assert response.collections[0]["name"] == "default"
    assert response.collections[1]["id"] == "col-2"
    assert response.collections[1]["name"] == "data-processing"
```

### Integration Tests

**File**: `skillmeat/api/tests/test_artifacts_routes.py`

**Add test**:
```python
def test_list_artifacts_includes_collections():
    """Verify GET /artifacts endpoint includes collections for each artifact."""
    from fastapi.testclient import TestClient
    from skillmeat.api.server import app

    client = TestClient(app)

    # Mock artifact manager to return artifact with collections
    with patch('skillmeat.api.dependencies.get_artifact_manager') as mock_mgr_dep:
        artifact = Mock()
        artifact.type = ArtifactType.SKILL
        artifact.name = "pdf"
        artifact.metadata = Mock(tags=[])
        artifact.origin = "local"
        artifact.collections = [
            Mock(id="col-1", name="default", collection_artifacts=[]),
            Mock(id="col-2", name="data-processing", collection_artifacts=[]),
        ]
        artifact.tags = []
        artifact.added = datetime.now(timezone.utc)
        artifact.last_updated = datetime.now(timezone.utc)

        mock_mgr = Mock()
        mock_mgr.list_artifacts.return_value = [artifact]
        mock_mgr_dep.return_value = mock_mgr

        # Call endpoint
        response = client.get("/api/v1/artifacts")

        # Verify response includes collections
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1

        artifact_response = data["items"][0]
        assert "collections" in artifact_response
        assert len(artifact_response["collections"]) == 2
        assert artifact_response["collections"][0]["name"] == "default"
        assert artifact_response["collections"][1]["name"] == "data-processing"
```

### Frontend Tests

**File**: `skillmeat/web/__tests__/components/collection/artifact-grid.test.tsx`

**Existing test** (verify it passes with populated collections):
```typescript
describe('ArtifactGrid', () => {
  it('should display artifact collections', () => {
    const artifact: Artifact = {
      id: 'skill:pdf',
      name: 'pdf',
      type: 'skill',
      source: 'anthropics/skills/pdf',
      // ... other fields ...
      collections: [
        { id: 'col-1', name: 'default' },
        { id: 'col-2', name: 'data-processing' },
      ],
    };

    const entity = artifactToEntity(artifact);

    expect(entity.collections).toHaveLength(2);
    expect(entity.collections[0].name).toBe('default');
    expect(entity.collections[1].name).toBe('data-processing');
  });
});
```

---

## Deployment Checklist

- [ ] Update `ArtifactResponse` schema in `skillmeat/api/schemas/artifacts.py`
- [ ] Update `artifact_to_response()` function in `skillmeat/api/routers/artifacts.py`
- [ ] Add unit tests for `artifact_to_response()` conversion
- [ ] Add integration tests for `GET /artifacts` endpoint
- [ ] Run frontend tests to verify no regressions
- [ ] Manual testing: Verify Collections tab shows all collections
- [ ] Update API documentation (if auto-generated, will update automatically)
- [ ] (Optional) Update frontend TODO comments to indicate implementation complete
- [ ] (Optional) Add artifact count in response (requires loading collection_artifacts)

---

## Impact Analysis

### Backend Impact
- **Files changed**: 2 (`schemas/artifacts.py`, `routers/artifacts.py`)
- **Breaking change**: No (adding optional field to response)
- **Performance**: Minimal (collections already eagerly loaded via selectin)
- **Database**: No schema changes needed

### Frontend Impact
- **Files changed**: 0 (UI already handles populated collections)
- **Breaking change**: No
- **User visible**: Collections tab will now show all collections
- **Performance**: No impact (same API call structure)

### API Contract
- **Version**: No version bump required (additive change)
- **Backward compatibility**: Full (new optional field)
- **Client impact**: None (field was optional, now just populated)

---

## Alternative Approaches

### Option A: Add artifact_count Calculation (Current Plan)
```python
collections_info['artifact_count'] = len(collection.collection_artifacts)
```
**Pros**: Complete data for UI
**Cons**: May require eager loading of collection_artifacts

### Option B: Skip artifact_count
```python
collections_info = {'id': collection.id, 'name': collection.name}
```
**Pros**: Simpler, faster
**Cons**: UI may need separate call for counts

### Option C: Separate Endpoint for Collections
```python
GET /artifacts/{artifact_id}/collections
```
**Pros**: Cleaner separation of concerns
**Cons**: Requires additional API call

**Recommendation**: Start with Option A (include basic info). Add artifact_count if performance permits.

---

## Related Code Sections

**Database Models**:
- Artifact.collections relationship: `/skillmeat/cache/models.py:275-282`
- Collection model: `/skillmeat/cache/models.py:623-727`
- CollectionArtifact junction: `/skillmeat/cache/models.py:881-932`

**API Layer**:
- ArtifactResponse schema: `/skillmeat/api/schemas/artifacts.py:153-237`
- artifact_to_response function: `/skillmeat/api/routers/artifacts.py:432-494`
- list_artifacts endpoint: `/skillmeat/api/routers/artifacts.py:1501-1728`

**Frontend**:
- Artifact type definition: `/skillmeat/web/types/artifact.ts:46-74`
- artifactToEntity function: `/skillmeat/web/app/collection/page.tsx:87-132`
- Collections tab usage: `/skillmeat/web/app/collection/page.tsx:113-130`

---

## Summary

This is a **straightforward implementation** to complete an existing architecture:

1. Add one field to an existing response schema
2. Populate that field in an existing conversion function
3. No database changes
4. No frontend logic changes (already prepared)
5. No breaking changes

**Estimated effort**: 1-2 hours including tests
**Risk level**: Low (additive change only)
**User impact**: Collections tab will show complete data

