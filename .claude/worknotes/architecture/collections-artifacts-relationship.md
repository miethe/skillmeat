# Collections and Artifacts Relationship - Architecture Analysis

**Date**: 2026-01-11
**Focus**: Understanding how collections and artifacts relate across backend and frontend
**Status**: Complete - Architecture documented

---

## Executive Summary

Collections and artifacts have a **many-to-many relationship** in SkillMeat:
- One artifact can belong to multiple collections
- One collection can contain multiple artifacts
- Association tracked via `CollectionArtifact` junction table
- Backend properly models this; frontend currently has a TODO to fully utilize it

---

## Database Layer (`skillmeat/cache/models.py`)

### Three Core Models

#### 1. Artifact Model (Lines 191-290)

```python
class Artifact(Base):
    """Artifact metadata for a project"""

    # Primary key
    id: Mapped[str]  # Composite key: "type:name"

    # Foreign key (back to projects)
    project_id: Mapped[str]  # FK → projects.id

    # Core fields
    name: str
    type: ArtifactType  # skill, command, agent, mcp, hook
    source: Optional[str]

    # Relationships
    project: Project              # One-to-many: Artifact → Project
    collections: List[Collection] # Many-to-many: Artifact ← CollectionArtifact → Collection
    tags: List[Tag]              # Many-to-many: Artifact ← ArtifactTag → Tag
```

**Key Relationship** (Line 275-282):
```python
collections: Mapped[List["Collection"]] = relationship(
    "Collection",
    secondary="collection_artifacts",
    primaryjoin="foreign(CollectionArtifact.artifact_id) == Artifact.id",
    secondaryjoin="foreign(CollectionArtifact.collection_id) == Collection.id",
    viewonly=True,
    lazy="selectin",  # Eager load collections with artifact
)
```

#### 2. Collection Model (Lines 623-727)

```python
class Collection(Base):
    """User-defined collection of artifacts"""

    # Primary key
    id: str  # UUID hex

    # Core fields
    name: str
    description: Optional[str]
    collection_type: Optional[str]

    # Relationships
    groups: List[Group]                     # One-to-many: Collection → Group
    collection_artifacts: List[CollectionArtifact]  # One-to-many: Collection → CollectionArtifact
    templates: List[ProjectTemplate]       # One-to-many: Collection → ProjectTemplate
```

#### 3. CollectionArtifact Junction Table (Lines 881-932)

```python
class CollectionArtifact(Base):
    """Association between Collection and Artifact (many-to-many)"""

    __tablename__ = "collection_artifacts"

    # Composite primary key (both parts)
    collection_id: str  # FK → collections.id, CASCADE delete
    artifact_id: str    # NO FK constraint (artifacts from external sources)

    # Additional tracking
    added_at: datetime  # When artifact was added to collection

    # Indexes
    - idx_collection_artifacts_collection_id  # Fast lookup: which artifacts in collection?
    - idx_collection_artifacts_artifact_id    # Fast lookup: which collections contain artifact?
    - idx_collection_artifacts_added_at       # Sort by addition date
```

**Why No FK on artifact_id**: Artifacts may come from external sources (GitHub, marketplace) that aren't in the local cache database.

---

## Data Flow: From Backend to Frontend

### API Layer (`skillmeat/api/schemas/artifacts.py`)

#### ArtifactResponse Schema (Lines 153-237)

```python
class ArtifactResponse(BaseModel):
    id: str                            # "type:name"
    name: str
    type: str                          # skill, command, agent, mcp, hook
    source: str
    version: str
    aliases: List[str]
    tags: List[str]
    metadata: Optional[ArtifactMetadataResponse]
    upstream: Optional[ArtifactUpstreamInfo]
    deployment_stats: Optional[DeploymentStatistics]  # When include_deployments=true
    added: datetime
    updated: datetime

    # NOTE: No collections field! This is the gap.
```

#### Router: GET /api/v1/artifacts (Lines 1501-1728)

**Endpoint**: `GET /artifacts` with optional filters

```python
async def list_artifacts(
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    limit: int = Query(default=20, le=100),
    after: Optional[str] = Query(None),  # Cursor pagination
    artifact_type: Optional[str] = Query(None),
    collection: Optional[str] = Query(None),  # Filter by collection name
    tags: Optional[str] = Query(None),
    check_drift: bool = Query(False),
    project_path: Optional[str] = Query(None),
) -> ArtifactListResponse:
```

**Flow**:
1. If `collection` filter provided: list artifacts in that collection
2. If no filter: list artifacts from all collections
3. Sort by type, then name
4. Apply cursor-based pagination
5. Convert to `ArtifactResponse` via `artifact_to_response()` function (Line 432)

**Conversion Function** (`artifact_to_response`, Lines 432-494):
```python
def artifact_to_response(artifact, drift_status=None, has_local_modifications=None):
    """Convert Artifact model to API response schema.

    Current limitations:
    - Does NOT include collections information
    - Does NOT map artifact.collections to response
    - Only converts: metadata, upstream info, version
    """
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
        # NOTE: collections field NOT included
    )
```

---

## Frontend Layer

### Type Definition (`skillmeat/web/types/artifact.ts`)

```typescript
export interface Artifact {
  id: string;
  name: string;
  type: ArtifactType;
  scope: ArtifactScope;
  status: ArtifactStatus;
  version?: string;
  source?: string;
  metadata: ArtifactMetadata;
  upstreamStatus: UpstreamStatus;
  usageStats: UsageStats;
  createdAt: string;
  updatedAt: string;
  aliases?: string[];

  // Single collection (current)
  collection?: {
    id: string;
    name: string;
  };

  // MANY collections (TODO: Backend needs to populate this)
  collections?: {
    id: string;
    name: string;
    artifact_count?: number;
  }[];

  score?: ArtifactScore;
}
```

**Comment** (Lines 64-66):
```typescript
/**
 * All collections this artifact belongs to (many-to-many relationship)
 * TODO: Backend needs to populate this field with data from CollectionArtifact table
 */
collections?: {...}[];
```

### Page Usage (`skillmeat/web/app/collection/page.tsx`)

The `collection/page.tsx` uses the `artifactToEntity()` function (Lines 87-132) to convert artifacts to entity objects:

```typescript
function artifactToEntity(artifact: Artifact): Entity {
  const collectionName = artifact.collection?.name || 'default';

  return {
    id: artifact.id,
    name: artifact.name,
    type: artifact.type,
    collection: collectionName,
    // ...

    // TODO: Backend needs to populate artifact.collections
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
  };
}
```

**Current Logic**:
1. **Primary source**: `artifact.collection` (single collection)
2. **Fallback**: `artifact.collections` array if populated by backend
3. **Issue**: Backend doesn't populate `collections` field, so UI always falls back to single collection

---

## The Gap: What's Missing

### Backend Missing: Collections Population

**File**: `skillmeat/api/routers/artifacts.py`, Line 432 (`artifact_to_response` function)

The function does NOT:
1. Read the `artifact.collections` relationship from the ORM model
2. Convert collection info to response schema
3. Add a `collections` field to `ArtifactResponse`

**What should happen**:
```python
def artifact_to_response(artifact, ...):
    # ... existing code ...

    # NEW: Convert collections relationship
    collections_data = []
    if hasattr(artifact, 'collections') and artifact.collections:
        for collection in artifact.collections:
            collections_data.append({
                'id': collection.id,
                'name': collection.name,
                'artifact_count': len(collection.collection_artifacts),  # Optional
            })

    return ArtifactResponse(
        # ... existing fields ...
        collections=collections_data,  # NEW
    )
```

### Frontend Missing: Collections Tab Display

**File**: `skillmeat/web/app/collection/page.tsx`, Lines 113-130

The `artifactToEntity()` function has a fallback mechanism, but the backend comment indicates:
```typescript
// TODO: Backend needs to populate artifact.collections with ALL collections the artifact belongs to
```

Once backend populates `collections`, the tab will auto-populate via this logic.

---

## Summary: The Data Path

### Current State (Incomplete)

```
Backend (Database):
  Artifact.collections ─→ [List of Collections via CollectionArtifact]
                             (ORM relationship defined, lazy="selectin")
                                ↓
Backend (API):
  artifact_to_response() ─→ ArtifactResponse
                             (DOES NOT include collections field)
                                ↓
Frontend (Types):
  Artifact.collections ─→ Empty (not populated from API)
                             ↓
Frontend (UI):
  artifactToEntity() ─→ Entity.collections
                        (Falls back to single collection)
                             ↓
Display:
  Collections Tab ─→ Shows only the single "primary" collection
```

### Desired State (Complete)

```
Backend (Database):
  Artifact.collections ─→ [List of Collections via CollectionArtifact]
                                ↓
Backend (API):
  artifact_to_response() ─→ ArtifactResponse
                             (INCLUDES collections field with all collections)
                                ↓
Frontend (Types):
  Artifact.collections ─→ Populated array of collection refs
                                ↓
Frontend (UI):
  artifactToEntity() ─→ Entity.collections
                        (Uses fully populated collections array)
                             ↓
Display:
  Collections Tab ─→ Shows ALL collections containing this artifact
```

---

## Architecture Decisions

### 1. Many-to-Many via Junction Table

**Why**: Flexible, standard pattern
- One artifact can be in multiple collections
- One collection contains multiple artifacts
- `CollectionArtifact` tracks `added_at` timestamp

### 2. No FK Constraint on artifact_id

**Why**: Artifacts from external sources (GitHub, marketplace)
- Artifacts don't have to exist in local cache database
- Prevents broken associations when external artifacts are referenced

### 3. Lazy Loading with selectin

**Backend** (Line 281): `lazy="selectin"` on collections relationship
- Collections eagerly loaded with artifact query (no N+1 problem)
- Safe for API responses

### 4. Single Collection Primary Field

**Frontend** currently uses:
```typescript
collection?: { id: string; name: string }
```
- Simplifies UI when artifact only needs one collection reference
- Supplements with `collections[]` array for full relationship

---

## Code References

### Backend Models
- **Artifact**: `/skillmeat/cache/models.py:191-290`
- **Collection**: `/skillmeat/cache/models.py:623-727`
- **CollectionArtifact**: `/skillmeat/cache/models.py:881-932`

### Backend API
- **ArtifactResponse Schema**: `/skillmeat/api/schemas/artifacts.py:153-237`
- **list_artifacts Endpoint**: `/skillmeat/api/routers/artifacts.py:1501-1728`
- **artifact_to_response Function**: `/skillmeat/api/routers/artifacts.py:432-494`

### Frontend Types
- **Artifact Interface**: `/skillmeat/web/types/artifact.ts:1-97`
- **Collection Usage**: `/skillmeat/web/app/collection/page.tsx:87-132`

---

## Next Steps to Complete Integration

1. **Backend**: Extend `ArtifactResponse` schema to include `collections` field
2. **Backend**: Modify `artifact_to_response()` to populate collections
3. **Frontend**: Frontend code already handles it via `artifactToEntity()` fallback
4. **Testing**: Add test cases for multi-collection artifacts
5. **UI**: Collections tab will auto-display once backend populates data
