# Collections-Artifacts Relationship - Visual Reference

---

## Database Schema

```
┌─────────────────────────────────────────────────────────────────┐
│                    ARTIFACT (cache database)                     │
├──────────────────────────────────────────────────────────────────┤
│ PK  id (str)                    "skill:pdf"                       │
│ FK  project_id (str)            →─→ projects.id                  │
│                                                                   │
│ Core:                                                             │
│   name: str                     "pdf"                            │
│   type: ArtifactType            "skill"                          │
│   source: Optional[str]         "anthropics/skills/pdf"          │
│   deployed_version: str         "1.2.3"                          │
│   upstream_version: str         "1.3.0"                          │
│   is_outdated: bool             true                             │
│   local_modified: bool          false                            │
│                                                                   │
│ Relationships (ORM):                                              │
│   collections ──→ [List[Collection]]  ← via CollectionArtifact   │
│   project ──→ Project                                            │
│   tags ──→ [List[Tag]]                                           │
│   artifact_metadata ──→ ArtifactMetadata                         │
└──────────────────────────────────────────────────────────────────┘
           │
           │ Many-to-many through CollectionArtifact
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│              COLLECTION_ARTIFACTS (junction table)                │
├──────────────────────────────────────────────────────────────────┤
│ PK  collection_id (str)         UUID hex (FK → collections.id)   │
│ PK  artifact_id (str)           "skill:pdf" (NO FK constraint)   │
│                                                                   │
│ Tracking:                                                         │
│   added_at: datetime            2024-12-15T10:30:00Z             │
│                                                                   │
│ Indexes:                                                          │
│   idx_collection_artifacts_collection_id   ← Fast: artifacts in  │
│   idx_collection_artifacts_artifact_id     ← Fast: collections   │
│   idx_collection_artifacts_added_at        ← Sort by date        │
└──────────────────────────────────────────────────────────────────┘
           ▲
           │ Many-to-many through CollectionArtifact
           │
           └──────────────────────────────────────────┐
                                                      │
┌──────────────────────────────────────────────────────────────────┐
│                      COLLECTION (cache database)                 │
├──────────────────────────────────────────────────────────────────┤
│ PK  id (str)                    UUID hex                          │
│                                                                   │
│ Core:                                                             │
│   name: str                     "default"                        │
│   description: Optional[str]    "My collection"                  │
│   collection_type: Optional[str] "user"                          │
│                                                                   │
│ Relationships (ORM):                                              │
│   collection_artifacts ──→ [List[CollectionArtifact]]            │
│   groups ──→ [List[Group]]                                       │
│   templates ──→ [List[ProjectTemplate]]                          │
│                                                                   │
│ (artifacts accessible via collection_artifacts)                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## API Request Flow

```
Frontend
   │
   │ GET /api/v1/artifacts
   │   ?limit=20&collection=default&tags=data-processing
   │
   ▼
┌──────────────────────────────────────────────────────────────────┐
│           FastAPI Endpoint (routers/artifacts.py:1512)            │
│              async def list_artifacts(...)                        │
├──────────────────────────────────────────────────────────────────┤
│ 1. Parse filters                                                  │
│    - collection: "default"                                        │
│    - artifact_type: None                                          │
│    - tags: ["data-processing"]                                    │
│                                                                   │
│ 2. Get artifacts from collection(s)                               │
│    IF collection specified:                                       │
│      artifacts = artifact_mgr.list_artifacts(                     │
│          collection_name="default",                               │
│          artifact_type=None,                                      │
│          tags=["data-processing"]                                 │
│      )                                                            │
│    ELSE:                                                          │
│      artifacts = [combine from ALL collections]                   │
│                                                                   │
│ 3. Paginate (cursor-based)                                        │
│    - start_idx = decode_cursor(after) or 0                        │
│    - end_idx = start_idx + limit                                  │
│    - page_artifacts = artifacts[start_idx:end_idx]                │
│                                                                   │
│ 4. Convert to response schema                                     │
│    for each artifact in page_artifacts:                           │
│      response = artifact_to_response(artifact)                    │
│      items.append(response)                                       │
└──────────────────────────────────────────────────────────────────┘
   │
   │ Each artifact converted to ArtifactResponse
   │ (but collections NOT included)
   │
   ▼
┌──────────────────────────────────────────────────────────────────┐
│              ArtifactResponse (schemas/artifacts.py:153)          │
├──────────────────────────────────────────────────────────────────┤
│ {                                                                 │
│   "id": "skill:pdf",                                              │
│   "name": "pdf",                                                  │
│   "type": "skill",                                                │
│   "source": "anthropics/skills/pdf",                              │
│   "version": "1.2.3",                                             │
│   "tags": ["data-processing", "document"],                        │
│   "metadata": { ... },                                            │
│   "upstream": { ... },                                            │
│   "added": "2024-11-15T10:00:00Z",                                │
│   "updated": "2024-11-20T15:30:00Z"                               │
│   // NOTE: No "collections" field!                                │
│ }                                                                 │
└──────────────────────────────────────────────────────────────────┘
   │
   │ HTTP 200 OK with ArtifactListResponse
   │
   ▼
Frontend (fetch in hook)
   │
   └─ Response received
   │
   ▼
┌──────────────────────────────────────────────────────────────────┐
│           artifactToEntity() (app/collection/page.tsx:87)         │
├──────────────────────────────────────────────────────────────────┤
│ Input:  artifact.collection = { id, name }  ← Single collection   │
│         artifact.collections = undefined    ← Not populated yet   │
│                                                                   │
│ Output: Entity with collections array                            │
│         - If artifact.collections exists:                         │
│           → use artifact.collections                              │
│         - Else if artifact.collection exists:                     │
│           → create array with single collection                   │
│         - Else:                                                   │
│           → empty array                                           │
│                                                                   │
│ Current Result:                                                   │
│ {                                                                 │
│   collections: [                                                  │
│     { id: "col-1", name: "default", artifact_count: 0 }           │
│   ]                                                               │
│ }                                                                 │
└──────────────────────────────────────────────────────────────────┘
```

---

## Relationship Diagram

```
                         Collections Tab (UI)
                                │
                                │ Displays all collections
                                │ containing this artifact
                                │
                                ▼
                    ┌─────────────────────────┐
                    │    Entity.collections   │
                    │  [Array of Collections] │
                    └─────────────────────────┘
                                ▲
                                │
                        ┌───────┴───────┐
                        │               │
                 No data yet      (TODO: Populate)
                (Falls back to        │
                single collection)    │
                        │             │
            artifact.collection ◄─ artifact.collections
            (Single ref)         (Multiple refs array)
                        │             │
                        └───────┬─────┘
                                │
                        ArtifactResponse
                        (from API endpoint)
                                │
                    ┌───────────┴────────────┐
                    │                        │
                    │ collection ✓           │ collections ✗
                    │ (Populated)            │ (NOT populated - TODO)
                    │                        │
                    └───────────┬────────────┘
                                │
                        artifact_to_response()
                        (API router function)
                                │
                        ┌───────┴──────────────┐
                        │                      │
               Artifact.collections      Artifact.collection
               (Many-to-many via          (Single collection
                CollectionArtifact)        context)
               (Available in ORM!)        (Available in ORM!)
                        │                      │
                        └──────────┬───────────┘
                                   │
                    SQLAlchemy ORM Model (Artifact)
                    with collections relationship
                    lazy="selectin"
```

---

## Current vs. Expected Data Structure

### Current (Incomplete)

```typescript
// From API response
artifact: Artifact = {
  id: "skill:pdf",
  name: "pdf",
  type: "skill",
  source: "...",

  // Single collection provided
  collection: {
    id: "col-1",
    name: "default"
  },

  // Multiple collections NOT provided
  collections: undefined
}

// In UI, collections tab shows:
[
  { id: "col-1", name: "default" }  // Only this one
]
```

### Expected (Complete)

```typescript
// From API response
artifact: Artifact = {
  id: "skill:pdf",
  name: "pdf",
  type: "skill",
  source: "...",

  // Single collection (primary)
  collection: {
    id: "col-1",
    name: "default"
  },

  // All collections containing this artifact
  collections: [
    {
      id: "col-1",
      name: "default",
      artifact_count: 42
    },
    {
      id: "col-2",
      name: "data-processing",
      artifact_count: 15
    },
    {
      id: "col-3",
      name: "document-tools",
      artifact_count: 8
    }
  ]
}

// In UI, collections tab shows:
[
  { id: "col-1", name: "default" },
  { id: "col-2", name: "data-processing" },
  { id: "col-3", name: "document-tools" }
]  // All three
```

---

## File Structure

```
Backend:
├── skillmeat/cache/models.py
│   ├── class Artifact (line 191)
│   │   ├── project: Project relationship
│   │   ├── collections: List[Collection] relationship ◄─ MANY-TO-MANY
│   │   └── metadata, tags relationships
│   ├── class Collection (line 623)
│   │   ├── collection_artifacts: List[CollectionArtifact]
│   │   ├── groups: List[Group]
│   │   └── templates relationship
│   └── class CollectionArtifact (line 881)
│       ├── collection_id: str (FK)
│       ├── artifact_id: str (NO FK - external artifacts)
│       └── added_at: datetime
│
├── skillmeat/api/routers/artifacts.py
│   ├── def artifact_to_response (line 432)
│   │   └── CONVERTS Artifact → ArtifactResponse
│   │       (Does NOT include collections field)
│   │
│   └── async def list_artifacts (line 1512)
│       └── GET /artifacts endpoint
│           └── Uses artifact_to_response()
│
└── skillmeat/api/schemas/artifacts.py
    └── class ArtifactResponse (line 153)
        ├── id, name, type, source, version
        ├── tags, metadata, upstream
        ├── added, updated
        └── (NO collections field)

Frontend:
├── skillmeat/web/types/artifact.ts
│   └── interface Artifact
│       ├── collection?: {...}  ← Single collection
│       └── collections?: [...]  ◄─ TODO: Needs backend data
│
├── skillmeat/web/hooks/useArtifacts.ts
│   └── Fetches from GET /artifacts
│       └── Returns Artifact[] with collections field undefined
│
└── skillmeat/web/app/collection/page.tsx
    ├── function enrichArtifactSummary (line 39)
    │   └── Enriches summary with full Artifact data
    │
    └── function artifactToEntity (line 87)
        └── Converts Artifact → Entity
            └── Handles collections array:
                1. If collections provided → use it
                2. Else if collection provided → wrap in array
                3. Else → empty array
```

---

## Query Patterns

### Pattern 1: Get All Collections for an Artifact

**Database Query** (via ORM):
```python
artifact = session.query(Artifact).filter_by(id="skill:pdf").first()
collections = artifact.collections  # Lazy loaded via selectin
for col in collections:
    print(col.id, col.name)
```

**Result**:
```
col-1 default
col-2 data-processing
col-3 document-tools
```

### Pattern 2: Get All Artifacts in a Collection

**Database Query**:
```python
collection = session.query(Collection).filter_by(name="default").first()
artifacts = [ca.artifact_id for ca in collection.collection_artifacts]
# Or with full data:
# artifacts = [ca.artifact for ca in collection.collection_artifacts]  # Needs FK
```

### Pattern 3: Check if Artifact is in Collection

**Database Query**:
```python
exists = session.query(CollectionArtifact).filter_by(
    collection_id="col-1",
    artifact_id="skill:pdf"
).first() is not None
```

---

## Summary Table

| Aspect | Current | Needed |
|--------|---------|--------|
| **DB Relationship** | ✅ Many-to-many via CollectionArtifact | ✅ Already exists |
| **ORM Model** | ✅ Artifact.collections defined | ✅ Already exists |
| **ORM Loading** | ✅ lazy="selectin" (eager load) | ✅ Already configured |
| **API Response Schema** | ❌ No collections field | ❌ Add collections field |
| **API Response Population** | ❌ Not converted | ❌ Populate in artifact_to_response() |
| **Frontend Type** | ✅ Artifact.collections defined | ✅ Type exists |
| **Frontend UI Logic** | ✅ Fallback handling works | ✅ Ready for data |
| **Collections Tab Display** | ⚠️ Shows only single collection | ✅ Will auto-populate once data arrives |

