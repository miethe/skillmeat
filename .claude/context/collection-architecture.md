---
title: Core User Collection Management Architecture
description: Comprehensive guide to how SkillMeat manages user collections - storage, API layer, database models, and operations
references:
  - skillmeat/core/collection.py
  - skillmeat/storage/manifest.py
  - skillmeat/storage/lockfile.py
  - skillmeat/core/artifact.py
  - skillmeat/api/routers/collections.py
  - skillmeat/api/routers/user_collections.py
  - skillmeat/cache/models.py
last_verified: 2026-01-11
---

# Core User Collection Management

## Overview

SkillMeat manages collections at two distinct levels:

1. **File-Based Collections** (~/.skillmeat/collection/) - Core persistent storage
2. **Database Collections** (SQLite cache) - User-created organizational collections

---

## Part 1: File-Based Collections

### Storage: ~/.skillmeat/collection/

```
~/.skillmeat/collection/
├── collection.toml               # Single manifest for all artifacts
├── collection.lock               # Lock file for reproducibility
├── skills/                        # Artifact type directories
├── commands/
└── agents/
```

**Key**: All artifacts tracked in single `collection.toml`, not per-artifact files.

### Core Classes

**Collection** (skillmeat/core/collection.py:14)
- `name: str` - Collection name
- `version: str` - Format version (e.g., "1.0.0")
- `artifacts: List[Artifact]` - All artifacts
- `created: datetime`, `updated: datetime`
- `mcp_servers: List[MCPServerMetadata]`

Methods:
- `find_artifact(name, artifact_type)` - Find by name/type
- `add_artifact(artifact)` - Add with duplicate check
- `remove_artifact(name, artifact_type)` - Remove by composite key
- `to_dict() / from_dict()` - TOML serialization

**Artifact** (skillmeat/core/artifact.py:95)
- `name: str` - No path separators (security)!
- `type: ArtifactType` - skill, command, agent, mcp, hook
- `path: str` - Relative path (e.g., "skills/my-skill/")
- `origin: str` - "local" or "github"
- `metadata: ArtifactMetadata` - Title, description, author, etc.
- `upstream: Optional[str]` - GitHub source URL
- `version_spec: Optional[str]` - "latest", "v1.0.0", SHA, branch

Security: Names validated to prevent traversal attacks (no `/`, `\`, `..`, leading `.`)

**ArtifactMetadata** (skillmeat/core/artifact.py:46)
- `title, description, author, license, version`
- `tags: List[str]`
- `dependencies: List[str]` - Artifact dependencies
- `extra: Dict[str, Any]` - Extensible (e.g., duplicate_links)

### Manifest Management

**ManifestManager** (skillmeat/storage/manifest.py)
- `read(collection_path)` → Collection
  - Reads collection.toml, parses TOML
  - Raises FileNotFoundError/ValueError on failure
- `write(collection_path, collection)` → None
  - Serializes to TOML
  - Atomically writes with timestamp update
- `exists(collection_path)` → bool
- `create_empty(collection_path, name)` → Collection
  - Creates directories and initial manifest

### Lock File Management

**LockManager** (skillmeat/storage/lockfile.py)

**LockEntry** - Tracks resolved versions and content hashes
- `name, type, upstream, resolved_sha, resolved_version`
- `content_hash: str` - Detects local modifications
- `fetched: datetime`

Methods:
- `read(collection_path)` → Dict[(name, type), LockEntry]
  - Returns empty dict if lock doesn't exist
  - Key format: "artifact-name::type"
- `write(collection_path, entries)` → None

Lock file format (TOML):
```toml
[lock]
version = "1.0.0"

[lock.entries."artifact-name::skill"]
upstream = "anthropics/skills/canvas-design"
resolved_sha = "abc123..."
resolved_version = "v2.1.0"
content_hash = "sha256:xyz..."
fetched = "2024-12-15T10:00:00Z"
```

### CollectionManager

**File**: skillmeat/core/collection.py:209

Initialization:
```python
manager = CollectionManager(config=None)
# Auto-initializes ManifestManager and LockManager
```

**Lifecycle**:
- `init(name)` - Initialize new collection
- `list_collections()` - List all collections
- `get_active_collection_name()` - Get active
- `switch_collection(name)` - Switch active
- `load_collection(name)` - Load from disk
- `save_collection(collection)` - Save to disk
- `delete_collection(name)` - Delete with confirmation

**Membership Checking** (used by API):
```python
in_coll, matched_id, match_type = artifact_in_collection(
    name="canvas-design",
    artifact_type="skill",
    source_link="anthropics/skills/canvas-design",
    collection_name=None
)
# Returns: (bool, Optional[str], "exact" | "hash" | "name_type" | "none")
```

Priority matching:
1. Exact source_link match → "exact"
2. Content hash match → "hash"
3. Name + type match (case-insensitive type) → "name_type"
4. No match → "none"

**Batch Operations** (optimized for 100+ artifacts):
```python
index = get_collection_membership_index()
# Pre-computes lookups: by_source, by_hash, by_name_type

results = check_membership_batch(artifacts)
# O(n) instead of O(n*m)
```

**Duplicate Linking**:
- `link_duplicate(discovered_path, collection_artifact_id)`
- `get_duplicate_links(collection_artifact_id)`
- `remove_duplicate_link(discovered_path, collection_artifact_id)`

---

## Part 2: Database Collections

### Database Models (skillmeat/cache/models.py)

**Collection** (lines 623-727)
- `id: str` - UUID hex (auto-generated)
- `name: str` - 1-255 chars
- `description: Optional[str]`
- `created_by: Optional[str]` - Future multi-user support
- `collection_type: Optional[str]` - e.g., "context", "artifacts"
- `context_category: Optional[str]` - e.g., "rules", "specs"
- `created_at, updated_at: datetime`
- Relationships:
  - `groups: List[Group]` - One-to-many
  - `collection_artifacts: List[CollectionArtifact]` - Many-to-many
  - `templates: List[ProjectTemplate]`

Indexes: name, created_by, created_at, type

**Group** (lines 729-824)
- `id: str` - UUID hex
- `collection_id: str` - FK (CASCADE delete)
- `name: str` - 1-255 chars, unique per collection
- `description: Optional[str]`
- `position: int` - Display order (0-based)
- `created_at, updated_at: datetime`
- Relationships:
  - `collection: Collection` - Back-reference
  - `group_artifacts: List[GroupArtifact]`

Constraints: Unique(collection_id, name), position >= 0

**GroupArtifact** (lines 827-879)
- Composite PK: `(group_id, artifact_id)`
- `position: int` - Order within group
- `added_at: datetime`
- Note: `artifact_id` has NO FK (external artifacts allowed)

**CollectionArtifact** (lines 881-928)
- Composite PK: `(collection_id, artifact_id)`
- `added_at: datetime`
- Purpose: Many-to-many association
- Note: `artifact_id` has NO FK (external sources)

### Database Session

**File**: skillmeat/api/routers/user_collections.py:50-66

```python
def get_db_session():
    session = get_session()
    try:
        yield session
    finally:
        session.close()

DbSessionDep = Annotated[Session, Depends(get_db_session)]
```

---

## Part 3: API Layer

### Collections Router (DEPRECATED)

**File**: skillmeat/api/routers/collections.py

Status: DEPRECATED (Sunset: 2025-06-01)
Use: `/user-collections` instead

Endpoints (read-only, file-based):
- `GET /collections` - List with pagination
- `GET /collections/{id}` - Get single
- `GET /collections/{id}/artifacts` - List artifacts

### User Collections Router (ACTIVE)

**File**: skillmeat/api/routers/user_collections.py
**Prefix**: /api/v1/user-collections

**CRUD Endpoints**:
1. `GET /` - List (limit, after, search, collection_type)
2. `POST /` - Create
3. `GET /{id}` - Get with groups
4. `PUT /{id}` - Update
5. `DELETE /{id}` - Delete (204)

**Artifact Endpoints**:
1. `GET /{id}/artifacts` - List artifacts (paginated)
2. `POST /{id}/artifacts` - Add artifacts
3. `DELETE /{id}/artifacts/{artifact_id}` - Remove (204)

**Response Models**:
- `UserCollectionResponse` - Basic collection
- `UserCollectionWithGroupsResponse` - With nested groups
- `GroupSummary` - Group with artifact_count
- `ArtifactSummary` - Artifact in collection

**Helper Functions**:
- `collection_to_response(collection, session)` - ORM to DTO
- `collection_to_response_with_groups(collection, session)` - Include groups

---

## Part 4: Operation Flows

### Adding Artifact to File-Based Collection

```
skillmeat add anthropics/skills/canvas-design

1. CollectionManager.load_collection()
   └─ ManifestManager.read() → Collection
2. ArtifactManager.fetch(source) → Artifact
3. Collection.add_artifact(artifact)
   └─ Duplicate check: (name, type) composite key
4. CollectionManager.save_collection()
   └─ ManifestManager.write() → collection.toml (atomic)
   └─ LockManager.write() → collection.lock
```

### Creating Database Collection

```
POST /api/v1/user-collections
{"name": "My Context", "collection_type": "context"}

1. Validate request → UserCollectionCreateRequest
2. Create Collection ORM (auto UUID hex ID)
3. Session.add() + commit() → INSERT
4. Query artifact_count (COUNT collection_artifacts)
5. Response: UserCollectionResponse
```

### Checking Membership

```
API: POST /artifacts/bulk-import

For large batches (100+):
1. Build index: get_collection_membership_index()
   └─ O(m) where m = collection size
2. Check batch: check_membership_batch(artifacts)
   └─ O(n) where n = import size (was O(n*m) before)

Priority: source (exact) > hash > name+type > none
```

---

## Part 5: Key Patterns

### Composite Key

Artifacts identified by **(name, type)**:
- Case-sensitive name
- Type from ArtifactType enum
- Format: "skill:canvas-design"

### Atomic Writes

collection.toml writes:
1. Write to temp file
2. Fsync for durability
3. Atomic rename
→ All-or-nothing, crash-safe

### Priority-Based Matching

1. Source link (exact) - Most reliable
2. Content hash - Detects duplicates
3. Name+type - Case-insensitive type
4. No match

### Many-to-Many

- CollectionArtifact(collection_id, artifact_id)
- GroupArtifact(group_id, artifact_id, position)
- NO FK on artifact_id (allows external sources)

---

## Key File Paths

| Component | Path |
|-----------|------|
| **Collection** | skillmeat/core/collection.py |
| **Artifact** | skillmeat/core/artifact.py |
| **Manifest** | skillmeat/storage/manifest.py |
| **Lock** | skillmeat/storage/lockfile.py |
| **Collections Router** | skillmeat/api/routers/collections.py |
| **User Collections Router** | skillmeat/api/routers/user_collections.py |
| **Models** | skillmeat/cache/models.py |
| **Schemas** | skillmeat/api/schemas/user_collections.py |

---

## Architecture Summary

### Layer 1: File-Based (Core)
- Location: ~/.skillmeat/collection/
- Format: collection.toml + collection.lock + files
- Manager: CollectionManager
- Use: CLI, reproducible
- Matching: Priority-based (exact > hash > name+type)

### Layer 2: Database (Organizational)
- Storage: SQLite
- Models: Collection, Group, GroupArtifact, CollectionArtifact
- API: /api/v1/user-collections (REST)
- Use: Web UI organization
- Support: Pagination, search, filtering

Both layers integrate: DB collections reference file-based artifacts and external sources.
