# SkillMeat Tag Systems Analysis

## Overview

SkillMeat implements **two separate but related tag systems**:

1. **Artifact Tags** - For categorizing and organizing artifacts (skills, commands, agents, etc.)
2. **Deployment Set Tags** - String-based tags for organizing deployment sets

Both systems are fully functional but use fundamentally different architectures.

---

## 1. ARTIFACT TAGS SYSTEM

### Database Models

**File**: `skillmeat/cache/models.py`

#### Tag Model (Lines 1181-1269)
```python
class Tag(Base):
    """Tag for categorizing and organizing artifacts."""
    __tablename__ = "tags"

    # Primary key
    id: Mapped[str]  # UUID hex, unique

    # Core fields
    name: Mapped[str]  # Unique, max 100 chars
    slug: Mapped[str]  # URL-friendly, unique, kebab-case
    color: Mapped[Optional[str]]  # Hex color (e.g., "#FF5733")

    # Timestamps
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    # Relationships
    artifacts: Mapped[List["Artifact"]]  # via artifact_tags junction
```

**Key Characteristics**:
- UUID-based primary key (generated via `uuid.uuid4().hex`)
- Unique constraints on both `name` and `slug`
- Optional hex color (7 chars: `#RRGGBB`)
- Color validation: must be null or match `^#[0-9a-fA-F]{6}$`

#### ArtifactTag Model (Lines 1271-1321)
```python
class ArtifactTag(Base):
    """Many-to-many junction table for Artifact ↔ Tag association."""
    __tablename__ = "artifact_tags"

    # Composite primary key
    artifact_uuid: Mapped[str]  # FK → artifacts.uuid (CASCADE delete)
    tag_id: Mapped[str]         # FK → tags.id (CASCADE delete)

    # Timestamp
    created_at: Mapped[datetime]
```

**Key Characteristics**:
- Composite primary key: `(artifact_uuid, tag_id)`
- Uses `artifact_uuid` (not `id`), following ADR-007 stable identity pattern
- CASCADE delete on both sides: removing artifact or tag removes the association
- Indexed on both columns and created_at for fast lookups/sorting

### API Endpoints

**File**: `skillmeat/api/routers/tags.py`

#### Tag CRUD Operations
- **POST** `/api/v1/tags` - Create tag
  - Request: `TagCreateRequest` (name, slug, color)
  - Response: `TagResponse`
  - Validation: Enforces unique name/slug; writes-through to manifest

- **GET** `/api/v1/tags` - List all tags (paginated)
  - Query params: `limit` (1-100), `after` (cursor)
  - Response: `TagListResponse` (items, pagination)
  - Supports cursor-based pagination with base64-encoded cursors

- **GET** `/api/v1/tags/{tag_id}` - Get tag by ID
  - Response: `TagResponse` with artifact count

- **GET** `/api/v1/tags/slug/{slug}` - Get tag by slug
  - Response: `TagResponse` with artifact count

- **PUT** `/api/v1/tags/{tag_id}` - Update tag
  - Request: `TagUpdateRequest` (all fields optional)
  - Behavior: Writes name changes back to filesystem (collection.toml + artifact frontmatter)
  - Response: `TagResponse`

- **DELETE** `/api/v1/tags/{tag_id}` - Delete tag
  - Behavior: Removes from filesystem first (collection.toml + artifact frontmatter)
  - Then deletes from DB (CASCADE removes artifact_tags rows)
  - Status: 204 No Content

#### Tag Search
- **GET** `/api/v1/tags/search?q={query}&limit={limit}`
  - Case-insensitive substring match
  - Response: `List[TagResponse]`

#### Artifact-Tag Association Endpoints
**Note**: Currently NOT implemented in tags router.
Should be in artifacts router:
- GET `/artifacts/{artifact_id}/tags` - Get artifact's tags
- POST `/artifacts/{artifact_id}/tags/{tag_id}` - Add tag to artifact
- DELETE `/artifacts/{artifact_id}/tags/{tag_id}` - Remove tag from artifact

### Services

**File**: `skillmeat/core/services/tag_service.py`

- `TagService.create_tag()` - Validates uniqueness, creates tag
- `TagService.get_tag()` - Fetch by ID
- `TagService.get_tag_by_slug()` - Fetch by slug
- `TagService.list_tags()` - Cursor-based pagination
- `TagService.update_tag()` - Update fields
- `TagService.delete_tag()` - Delete and cascade
- `TagService.search_tags()` - Name substring search

**File**: `skillmeat/core/services/tag_write_service.py`

- `TagWriteService.rename_tag()` - Update tag name in filesystem sources
- `TagWriteService.delete_tag()` - Remove tag from filesystem sources
- `TagWriteService.update_tags_json_cache()` - Sync changes to artifact tags cache

### Pydantic Schemas

**File**: `skillmeat/api/schemas/tags.py`

```python
class TagCreateRequest(BaseModel):
    name: str                    # Required, unique
    slug: str                    # Required, unique, kebab-case
    color: Optional[str] = None  # Optional hex

class TagUpdateRequest(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    color: Optional[str] = None

class TagResponse(BaseModel):
    id: str
    name: str
    slug: str
    color: Optional[str]
    artifact_count: int         # Computed field
    created_at: datetime
    updated_at: datetime
```

### Frontend Implementation

**Types**: `skillmeat/web/types/artifact.ts`

```typescript
// Artifact has:
tags: string[]  // Array of tag names
```

**No dedicated tag UI components yet** (as of current state)
- Artifact tags are read-only in collection view
- Tag management happens via API endpoints
- Tag association via artifact detail modal (planned/partial)

### Data Flow

```
User Action
    ↓
API Router (/tags or /artifacts/{id}/tags)
    ↓
Service (TagService or TagWriteService)
    ↓
[DB Write] ← SQLAlchemy (artifact_tags junction)
    ↓
[Filesystem Write] ← Write-through to collection.toml/artifact frontmatter
    ↓
Cache Refresh ← refresh_single_artifact_cache()
    ↓
Query Invalidation ← Frontend hooks invalidate tag-related queries
```

### Key Rules

1. **Unique Constraints**: Both `name` and `slug` must be globally unique
2. **Write-Through Pattern**: Tag mutations update filesystem first, then DB
3. **Cascade Deletes**: Removing artifact or tag removes the association
4. **ADR-007**: Uses `artifact_uuid` (not `id`) for foreign key stability
5. **Cursor Pagination**: Base64-encoded tag IDs for stateless pagination

---

## 2. DEPLOYMENT SET TAGS SYSTEM

### Database Model

**File**: `skillmeat/cache/models.py` (Lines 3173-3280)

#### DeploymentSet Model
```python
class DeploymentSet(Base):
    """Named, ordered set of artifacts/groups for batch deployment."""
    __tablename__ = "deployment_sets"

    # Primary key
    id: Mapped[str]  # UUID hex

    # Core fields
    name: Mapped[str]  # Max 255 chars
    description: Mapped[Optional[str]]
    tags_json: Mapped[str]  # JSON-serialized list, default "[]"
    icon: Mapped[Optional[str]]  # Emoji or identifier
    color: Mapped[Optional[str]]  # Hex or token name

    # Ownership
    owner_id: Mapped[str]  # User/collection ID

    # Timestamps
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    # Relationships
    members: Mapped[List["DeploymentSetMember"]]
```

**Tag Storage Implementation**:
```python
def get_tags(self) -> List[str]:
    """Parse and return tags as a list."""
    if not self.tags_json:
        return []
    try:
        parsed = json.loads(self.tags_json)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []

def set_tags(self, tags: List[str]) -> None:
    """Persist tags from a list as JSON text."""
    self.tags_json = json.dumps(tags or [])
```

**Key Characteristics**:
- Tags stored as JSON array in single `tags_json` TEXT column
- No separate junction table (unlike Artifact tags)
- No tag validation or uniqueness checks
- No color/slug properties (unlike Artifact tags)
- Simple string list: `["tag1", "tag2", "tag3"]`

### API Endpoints

**File**: `skillmeat/api/routers/deployment_sets.py`

#### DeploymentSet CRUD
- **POST** `/api/v1/deployment-sets` - Create set
  - Request: `DeploymentSetCreate` (name, description, icon, color, **tags**)
  - Response: `DeploymentSet`
  - Tag handling: Direct JSON serialization in request

- **GET** `/api/v1/deployment-sets` - List sets
  - Query params: `name`, `tag` (filter by tag), `limit`, `offset`
  - Response: `DeploymentSetListResponse`
  - Note: `tag` query param for filtering by individual tag

- **GET** `/api/v1/deployment-sets/{set_id}` - Get set
  - Response: `DeploymentSet` (includes tags)

- **PUT** `/api/v1/deployment-sets/{set_id}` - Update set
  - Request: `DeploymentSetUpdate` (all fields optional, including tags)
  - Tag handling: Replaces entire tags array if provided
  - Response: `DeploymentSet`

- **DELETE** `/api/v1/deployment-sets/{set_id}` - Delete set
  - Status: 204 No Content

### Pydantic Schemas

**File**: `skillmeat/api/schemas/deployment_sets.py`

```python
class DeploymentSetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    tags: Optional[List[str]] = None  # Direct string list

class DeploymentSetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    tags: Optional[List[str]] = None  # Replaces entire list

class DeploymentSet(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    tags: List[str]  # Computed from tags_json
    owner_id: Optional[str] = None
    member_count: int
    created_at: datetime
    updated_at: datetime
```

### TypeScript Types

**File**: `skillmeat/web/types/deployment-sets.ts`

```typescript
export interface DeploymentSet {
  id: string;
  name: string;
  description: string | null;
  icon: string | null;
  color: string | null;
  tags: string[];  // Simple string array
  owner_id: string | null;
  member_count: number;
  created_at: string;
  updated_at: string;
}

export interface DeploymentSetCreate {
  name: string;
  description?: string | null;
  icon?: string | null;
  color?: string | null;
  tags?: string[] | null;  // Optional tag list
}

export interface DeploymentSetUpdate {
  name?: string | null;
  description?: string | null;
  icon?: string | null;
  color?: string | null;
  tags?: string[] | null;  // Replaces entire list
}

export interface DeploymentSetListParams {
  name?: string;
  tag?: string;  // Filter by single tag
  limit?: number;
  offset?: number;
}
```

### Frontend Implementation

#### Edit Dialog
**File**: `skillmeat/web/components/deployment-sets/edit-deployment-set-dialog.tsx`

- Text input with "Add" button for entering new tags
- Badge display showing current tags with X button to remove
- Tags validation: trimmed, deduplicated
- Enter or comma key to add tag
- Submits entire tags array on save

#### Card Display & Inline Editing
**File**: `skillmeat/web/components/deployment-sets/deployment-set-card.tsx`

- Inline tag editing via popover on card
- Command component for search/filter
- Click to remove existing tags
- Type to add new tags
- Tag color via `getTagColor()` utility

**Features**:
- Real-time mutation on add/remove
- Search/filter current tags
- Tag display with colored badges

### Hooks

**File**: `skillmeat/web/hooks/deployment-sets.ts`

```typescript
export function useUpdateDeploymentSet() {
  return useMutation({
    mutationFn: async ({ id, data }: UpdateParams) => {
      const response = await fetch(`/api/v1/deployment-sets/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['deploymentSets']
      });
    },
  });
}
```

### Data Flow

```
User adds tag to set
    ↓
Input field + "Add" button / Popover with Command
    ↓
Tag added to local state (tags: string[])
    ↓
handleSave() / handleAddTag()
    ↓
useUpdateDeploymentSet().mutateAsync()
    ↓
PUT /api/v1/deployment-sets/{id}
    ↓
Backend: tags_json = json.dumps(tags)
    ↓
DB Write: Update deployment_sets.tags_json
    ↓
Query Invalidation: deploymentSets
```

### Key Differences from Artifact Tags

| Aspect | Artifact Tags | Deployment Set Tags |
|--------|---------------|---------------------|
| **Storage** | Separate `tags` table + junction table | Single JSON column |
| **Primary Key** | UUID + unique name/slug | String list |
| **Validation** | Unique name/slug enforced | No validation |
| **Color** | Per-tag color support | Per-set color only |
| **Query** | By tag ID or slug | By tag string directly |
| **CRUD** | Dedicated `/tags` endpoints | Part of `/deployment-sets` |
| **Constraints** | Database constraints | Application-level |
| **Filtering** | Complex tag joins | Simple string containment |

---

## 3. COMPARISON MATRIX

### Storage Architecture
```
Artifact Tags:
  tags (table)
    ├─ id (UUID, PK)
    ├─ name (unique string)
    ├─ slug (unique string)
    ├─ color (hex)
    └─ timestamps

  artifact_tags (junction)
    ├─ artifact_uuid (FK, CASCADE)
    ├─ tag_id (FK, CASCADE)
    └─ created_at

Deployment Set Tags:
  deployment_sets (table)
    ├─ id (UUID, PK)
    ├─ name (string)
    ├─ tags_json (TEXT, "[]" default)
    └─ ...other fields
```

### UI Implementation
```
Artifact Tags:
  - No dedicated UI yet
  - Planned for artifact detail modals
  - Read-only in list views

Deployment Set Tags:
  - Edit dialog with input + badges
  - Inline popover on card with Command combobox
  - Real-time update via mutation
```

### Query Patterns
```
Artifact Tags:
  - Find all tags: SELECT * FROM tags
  - Find artifacts with tag: SELECT * FROM artifacts
                             JOIN artifact_tags ON ...
                             WHERE tag_id = ?
  - Search by name: WHERE name LIKE ?
  - Filter by slug: WHERE slug = ?

Deployment Set Tags:
  - List by tag: WHERE tags_json LIKE ?
  - Get set's tags: JSON_EXTRACT(tags_json, '$')
  - Filter in memory: client-side array operations
```

---

## 4. KEY IMPLEMENTATION FILES

### Database & Models
- `skillmeat/cache/models.py`
  - Tag (1181-1269), ArtifactTag (1271-1321)
  - DeploymentSet (3173-3280), DeploymentSetMember (3282-...)

### API Layer
- `skillmeat/api/routers/tags.py` - Tag CRUD endpoints
- `skillmeat/api/routers/deployment_sets.py` - DeploymentSet endpoints
- `skillmeat/api/schemas/tags.py` - Tag schemas
- `skillmeat/api/schemas/deployment_sets.py` - DeploymentSet schemas
- `skillmeat/core/services/tag_service.py` - Tag business logic
- `skillmeat/core/services/tag_write_service.py` - Filesystem write-back

### Frontend
- `skillmeat/web/types/deployment-sets.ts` - DeploymentSet types
- `skillmeat/web/types/artifact.ts` - Artifact types (includes tags array)
- `skillmeat/web/components/deployment-sets/edit-deployment-set-dialog.tsx`
- `skillmeat/web/components/deployment-sets/deployment-set-card.tsx`
- `skillmeat/web/hooks/deployment-sets.ts` - useUpdateDeploymentSet

### Migrations
- `skillmeat/cache/migrations/versions/20251218_0001_add_tags_schema.py`
- `skillmeat/cache/migrations/versions/20260104_1000_add_path_based_tag_extraction.py`
- `skillmeat/cache/migrations/versions/20260219_1300_migrate_artifact_tags_to_uuid.py`
- `skillmeat/cache/migrations/versions/20260224_1000_add_deployment_set_tables.py`

---

## 5. FUTURE ENHANCEMENTS

### For Artifact Tags
1. Complete Frontend Implementation - tag management UI in artifact modals
2. Implement Association Endpoints - `/artifacts/{id}/tags/*` endpoints
3. Tag Search UI - searchable tag picker in detail modals
4. Colored Badges - render hex colors from DB
5. Filesystem Sync - ensure frontmatter updates persist

### For Deployment Set Tags
1. Validation - constraints on length/characters
2. Color Support - per-tag colors or inherit from set
3. Standardization - consider migrating to Artifact Tag model
4. Filter UI - tag filter chips in list view
5. Autocomplete - fetch existing tags for suggestions

### Unified Strategy
1. Global Tag Registry - centralize definitions
2. Tag Hierarchy - support categories/parents
3. Tag Aliases - multiple names for same tag
4. Bulk Operations - tag multiple items at once
5. Analytics - track tag usage across system
