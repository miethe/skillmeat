---
title: Collection Management - Quick Reference
description: Fast lookup for classes, methods, file locations, and API endpoints
references:
  - skillmeat/core/collection.py
  - skillmeat/api/routers/user_collections.py
last_verified: 2026-01-11
---

# Collection Management Quick Reference

## File Locations

| Component | Path | Purpose |
|-----------|------|---------|
| Collection class | skillmeat/core/collection.py:14 | File-based collection model |
| CollectionManager | skillmeat/core/collection.py:209 | Manage file collections |
| Artifact class | skillmeat/core/artifact.py:95 | Artifact model |
| ArtifactMetadata | skillmeat/core/artifact.py:46 | Artifact metadata |
| ManifestManager | skillmeat/storage/manifest.py | Read/write collection.toml |
| LockManager | skillmeat/storage/lockfile.py | Read/write collection.lock |
| Collection ORM | skillmeat/cache/models.py:623 | Database collection model |
| Group ORM | skillmeat/cache/models.py:729 | Database group model |
| GroupArtifact | skillmeat/cache/models.py:827 | Group-artifact association |
| CollectionArtifact | skillmeat/cache/models.py:881 | Collection-artifact association |
| Collections Router | skillmeat/api/routers/collections.py | Deprecated endpoints |
| User Collections Router | skillmeat/api/routers/user_collections.py | Active endpoints |
| Collection Schemas | skillmeat/api/schemas/user_collections.py | Response DTOs |

## Core Classes

### Collection (File-Based)

```python
@dataclass
class Collection:
    name: str
    version: str                           # "1.0.0"
    artifacts: List[Artifact]
    created: datetime
    updated: datetime
    mcp_servers: List[MCPServerMetadata]
```

Methods:
- `find_artifact(name, artifact_type=None)` → Artifact | None
- `add_artifact(artifact)` → None
- `remove_artifact(name, artifact_type)` → bool
- `find_mcp_server(name)` → MCPServerMetadata | None
- `add_mcp_server(server)` → None
- `remove_mcp_server(name)` → bool
- `to_dict()` → Dict
- `from_dict(data)` → Collection

### Artifact

```python
@dataclass
class Artifact:
    name: str                              # No path separators!
    type: ArtifactType                    # skill, command, agent, mcp, hook
    path: str                              # Relative path
    origin: str                            # "local" or "github"
    metadata: ArtifactMetadata
    added: datetime
    upstream: Optional[str]                # GitHub URL
    version_spec: Optional[str]            # "latest", "v1.0.0", SHA
    resolved_sha: Optional[str]
    resolved_version: Optional[str]
    last_updated: Optional[datetime]
    discovered_at: Optional[datetime]
    tags: List[str]
```

Security: Names validated (no `/`, `\`, `..`, leading `.`)

### CollectionManager

```python
class CollectionManager:
    def __init__(self, config=None)
    
    # Lifecycle
    init(name: str) → Collection
    list_collections() → List[str]
    get_active_collection_name() → str
    switch_collection(name: str) → None
    load_collection(name: Optional[str]) → Collection
    save_collection(collection: Collection) → None
    delete_collection(name: str, confirm: bool) → None
    
    # Membership
    artifact_in_collection(
        name: str,
        artifact_type: str,
        source_link: Optional[str],
        content_hash: Optional[str],
        collection_name: Optional[str]
    ) → (bool, Optional[str], str)  # match_type: exact|hash|name_type|none
    
    get_collection_membership_index(
        collection_name: Optional[str]
    ) → Dict[str, Any]  # {by_source, by_hash, by_name_type, artifacts}
    
    check_membership_batch(
        artifacts: List[Dict],
        collection_name: Optional[str]
    ) → List[tuple]
    
    # Duplicate linking
    link_duplicate(
        discovered_path: str,
        collection_artifact_id: str,
        collection_name: Optional[str]
    ) → bool
    
    get_duplicate_links(
        collection_artifact_id: str,
        collection_name: Optional[str]
    ) → List[str]
    
    remove_duplicate_link(
        discovered_path: str,
        collection_artifact_id: str,
        collection_name: Optional[str]
    ) → bool
```

### ManifestManager

```python
class ManifestManager:
    MANIFEST_FILENAME = "collection.toml"
    
    read(collection_path: Path) → Collection
    write(collection_path: Path, collection: Collection) → None
    exists(collection_path: Path) → bool
    create_empty(collection_path: Path, name: str) → Collection
```

### LockManager

```python
class LockManager:
    LOCK_FILENAME = "collection.lock"
    
    read(collection_path: Path) → Dict[(str, str), LockEntry]
    write(collection_path: Path, entries: Dict) → None
```

## Database Models (SQLAlchemy)

### Collection

```python
class Collection(Base):
    id: Mapped[str]                        # UUID hex (PK)
    name: Mapped[str]                      # 1-255 chars
    description: Mapped[Optional[str]]
    created_by: Mapped[Optional[str]]
    collection_type: Mapped[Optional[str]] # e.g., "context"
    context_category: Mapped[Optional[str]]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    groups: Mapped[List["Group"]]
    collection_artifacts: Mapped[List["CollectionArtifact"]]
```

Indexes: name, created_by, created_at, collection_type

### Group

```python
class Group(Base):
    id: Mapped[str]                        # UUID hex (PK)
    collection_id: Mapped[str]             # FK → Collection (CASCADE)
    name: Mapped[str]                      # Unique per collection
    description: Mapped[Optional[str]]
    position: Mapped[int]                  # 0-based order
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    collection: Mapped["Collection"]
    group_artifacts: Mapped[List["GroupArtifact"]]
```

Constraints: UNIQUE(collection_id, name), position >= 0

### GroupArtifact

```python
class GroupArtifact(Base):
    group_id: Mapped[str]                  # FK → Group (CASCADE) (PK)
    artifact_id: Mapped[str]               # NO FK (PK)
    position: Mapped[int]                  # 0-based order
    added_at: Mapped[datetime]
```

### CollectionArtifact

```python
class CollectionArtifact(Base):
    collection_id: Mapped[str]             # FK → Collection (CASCADE) (PK)
    artifact_id: Mapped[str]               # NO FK (PK)
    added_at: Mapped[datetime]
```

## API Endpoints

### User Collections Router

**Prefix**: `/api/v1/user-collections`

| Method | Endpoint | Request | Response | Status |
|--------|----------|---------|----------|--------|
| GET | `/` | limit, after, search, collection_type | UserCollectionListResponse | 200 |
| POST | `/` | UserCollectionCreateRequest | UserCollectionResponse | 201 |
| GET | `/{id}` | - | UserCollectionWithGroupsResponse | 200 |
| PUT | `/{id}` | UserCollectionUpdateRequest | UserCollectionResponse | 200 |
| DELETE | `/{id}` | - | - | 204 |
| GET | `/{id}/artifacts` | limit, after, search | CollectionArtifactsResponse | 200 |
| POST | `/{id}/artifacts` | AddArtifactsRequest | UserCollectionResponse | 200 |
| DELETE | `/{id}/artifacts/{artifact_id}` | - | - | 204 |

### Collections Router (Deprecated)

**Prefix**: `/api/v1/collections` (Sunset: 2025-06-01)

| Method | Endpoint | Status |
|--------|----------|--------|
| GET | `/` | 200 |
| GET | `/{id}` | 200 |
| GET | `/{id}/artifacts` | 200 |

## Response Models

```python
class UserCollectionResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_by: Optional[str]
    collection_type: Optional[str]
    context_category: Optional[str]
    created_at: datetime
    updated_at: datetime
    group_count: int
    artifact_count: int

class UserCollectionWithGroupsResponse(UserCollectionResponse):
    groups: List[GroupSummary]

class GroupSummary(BaseModel):
    id: str
    name: str
    description: Optional[str]
    position: int
    artifact_count: int

class ArtifactSummary(BaseModel):
    id: str
    name: str
    artifact_type: str
    added_at: datetime

class UserCollectionListResponse(BaseModel):
    items: List[UserCollectionResponse]
    page_info: PageInfo

class PageInfo(BaseModel):
    after: Optional[str]
    next_cursor: Optional[str]
```

## Storage Structure

### File-Based Collection

```
~/.skillmeat/collection/
├── collection.toml          # Single manifest
├── collection.lock          # Lock file (reproducibility)
├── skills/
│   ├── skill-1/
│   └── skill-2/
├── commands/
├── agents/
└── [other types]/
```

### Lock File Format

```toml
[lock]
version = "1.0.0"

[lock.entries."artifact-name::skill"]
upstream = "anthropics/skills/canvas-design"
resolved_sha = "abc123def456..."
resolved_version = "v2.1.0"
content_hash = "sha256:xyz..."
fetched = "2024-12-15T10:00:00Z"
```

## Enums

### ArtifactType

```python
class ArtifactType(str, Enum):
    SKILL = "skill"
    COMMAND = "command"
    AGENT = "agent"
    MCP = "mcp"
    HOOK = "hook"
```

## Common Operations

### Load & Check Membership

```python
manager = CollectionManager()
in_coll, matched_id, match_type = manager.artifact_in_collection(
    name="canvas-design",
    artifact_type="skill",
    source_link="anthropics/skills/canvas-design"
)
```

### Batch Check (100+ artifacts)

```python
index = manager.get_collection_membership_index()
results = manager.check_membership_batch(artifacts)
```

### Get Collection with Groups

```python
session = get_session()
collection = session.query(Collection).filter_by(id="abc123").first()
for group in sorted(collection.groups, key=lambda g: g.position):
    for artifact in group.group_artifacts:
        print(artifact.artifact_id)
```

### Create Database Collection

```python
collection = Collection(
    name="My Context",
    collection_type="context",
    created_at=datetime.utcnow(),
    updated_at=datetime.utcnow()
)
session.add(collection)
session.commit()
```

## Priority Matching (for membership)

1. **Exact** (source_link) - Most reliable, detects same upstream
2. **Hash** (content) - Detects exact duplicates
3. **Name+Type** - Case-insensitive type matching
4. **None** - No match

Return format: `(in_collection: bool, artifact_id: Optional[str], match_type: str)`

## Thread Safety Notes

- File-based collections: Use locks when modifying (atomic_write handles this)
- Database: SQLAlchemy manages connections
- Multiple managers can coexist safely (each has own session)

## Error Handling

| Exception | Cause | Solution |
|-----------|-------|----------|
| FileNotFoundError | collection.toml missing | Initialize collection with `init()` |
| ValueError (parse) | Corrupted TOML | Check file syntax |
| ValueError (duplicate) | Artifact already exists | Check composite key (name, type) |
| ValueError (ambiguous) | Multiple artifacts same name | Specify type explicitly |
| HTTPException 404 | Collection not found | Check ID or create first |
| HTTPException 422 | Validation failed | Check required fields |
| IntegrityError | DB constraint violated | Check unique constraints |

## Composite Key Format

Artifacts: `"{artifact.type.value}:{artifact.name}"`

Examples:
- `"skill:canvas-design"`
- `"command:run-tests"`
- `"agent:code-analyzer"`

Lock entries: `"artifact-name::type"`

Examples:
- `"canvas-design::skill"`
- `"run-tests::command"`

