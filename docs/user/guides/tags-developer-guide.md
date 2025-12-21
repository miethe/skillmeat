---
title: Tags Developer Guide
description: Architecture and integration guide for the SkillMeat tags system
audience: developers
tags: [tags, architecture, api, integration, database]
created: 2025-12-18
updated: 2025-12-18
category: guides
status: published
related:
  - skillmeat/api/CLAUDE.md
  - skillmeat/web/CLAUDE.md
  - .claude/rules/api/routers.md
  - .claude/rules/web/api-client.md
---

# Tags Developer Guide

This guide covers the architecture, API, and integration patterns for the SkillMeat tags system. It's intended for developers extending or integrating with the tags feature.

## Architecture Overview

The tags system follows SkillMeat's layered architecture with clear separation of concerns:

```
Database Layer (SQLAlchemy models)
    ↓
Repository Layer (Data access)
    ↓
Service Layer (Business logic)
    ↓
API Layer (FastAPI routers)
    ↓
Frontend API Client (TypeScript)
    ↓
React Hooks (TanStack Query)
    ↓
Components (UI)
```

## Database Schema

### Tags Table

Stores tag definitions with metadata:

```sql
CREATE TABLE tags (
  id VARCHAR PRIMARY KEY,              -- Unique identifier
  name VARCHAR(100) UNIQUE NOT NULL,   -- Display name (e.g., "Python")
  slug VARCHAR(100) UNIQUE NOT NULL,   -- URL slug (e.g., "python")
  color VARCHAR(7),                    -- Optional hex color (#RRGGBB)
  created_at TIMESTAMP NOT NULL,       -- Creation timestamp
  updated_at TIMESTAMP NOT NULL,       -- Last modification timestamp
  deleted_at TIMESTAMP                 -- Soft delete timestamp (if using)
);
```

**Constraints**:
- `name` and `slug` must be globally unique
- `slug` must match pattern: `^[a-z0-9]+(?:-[a-z0-9]+)*$` (kebab-case)
- `color` must be valid hex: `^#[0-9A-Fa-f]{6}$`

### Artifact-Tag Junction Table

Maps artifacts to tags (many-to-many relationship):

```sql
CREATE TABLE artifact_tags (
  artifact_id VARCHAR NOT NULL,
  tag_id VARCHAR NOT NULL,
  created_at TIMESTAMP NOT NULL,
  PRIMARY KEY (artifact_id, tag_id),
  FOREIGN KEY (artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE,
  FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);
```

**Design Notes**:
- Composite primary key ensures one tag per artifact
- Cascading deletes ensure cleanup when artifacts or tags are deleted
- `created_at` tracks when tag was added to artifact

### Database Indexes

For optimal performance:

```sql
-- Tag lookups by ID, name, slug
CREATE INDEX idx_tags_id ON tags(id);
CREATE INDEX idx_tags_slug ON tags(slug);

-- Artifact-tag lookups
CREATE INDEX idx_artifact_tags_artifact_id ON artifact_tags(artifact_id);
CREATE INDEX idx_artifact_tags_tag_id ON artifact_tags(tag_id);
```

## Core Components

### Models (SQLAlchemy)

**File**: `skillmeat/cache/models.py`

```python
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship

class Tag(Base):
    """Tag model for artifact organization."""

    __tablename__ = "tags"

    id: str = Column(String, primary_key=True)
    name: str = Column(String(100), unique=True, nullable=False)
    slug: str = Column(String(100), unique=True, nullable=False)
    color: Optional[str] = Column(String(7))  # Hex color
    created_at: datetime = Column(DateTime, nullable=False)
    updated_at: datetime = Column(DateTime, nullable=False)

    # Relationship to artifacts (many-to-many)
    artifacts = relationship("Artifact", secondary="artifact_tags", back_populates="tags")


# Junction table for many-to-many relationship
artifact_tags = Table(
    "artifact_tags",
    Base.metadata,
    Column("artifact_id", String, ForeignKey("artifacts.id", ondelete="CASCADE")),
    Column("tag_id", String, ForeignKey("tags.id", ondelete="CASCADE")),
    Column("created_at", DateTime, nullable=False),
)


class Artifact(Base):
    """Artifact model with tag relationship."""

    __tablename__ = "artifacts"

    id: str = Column(String, primary_key=True)
    name: str = Column(String, nullable=False)
    # ... other fields

    # Relationship to tags (many-to-many)
    tags = relationship("Tag", secondary="artifact_tags", back_populates="artifacts")
```

### Service Layer

**File**: `skillmeat/core/services/tag_service.py`

The service layer contains business logic for tag operations:

```python
class TagService:
    """Service for tag management operations."""

    def __init__(self):
        self.repository = TagRepository()

    def create_tag(self, name: str, slug: str, color: Optional[str] = None) -> Tag:
        """Create new tag with validation."""
        # Validate uniqueness
        if self.repository.get_by_name(name):
            raise ValueError(f"Tag name '{name}' already exists")
        if self.repository.get_by_slug(slug):
            raise ValueError(f"Tag slug '{slug}' already exists")

        # Validate slug format
        if not self._is_valid_slug(slug):
            raise ValueError("Slug must be lowercase kebab-case")

        # Create and return
        return self.repository.create(name, slug, color)

    def search_tags(self, query: str, limit: int = 50) -> List[Tag]:
        """Search tags by name (case-insensitive substring match)."""
        return self.repository.search(query, limit)

    def get_tag_artifact_count(self, tag_id: str) -> int:
        """Get number of artifacts with this tag."""
        return self.repository.count_artifacts(tag_id)

    def add_tag_to_artifact(self, artifact_id: str, tag_id: str) -> None:
        """Add tag to artifact (creates association)."""
        # Validate both exist
        if not self.repository.get_by_id(tag_id):
            raise LookupError(f"Tag '{tag_id}' not found")

        # Add association (no duplicate check needed due to PK constraint)
        self.repository.add_artifact_tag(artifact_id, tag_id)

    def remove_tag_from_artifact(self, artifact_id: str, tag_id: str) -> None:
        """Remove tag from artifact (deletes association)."""
        self.repository.remove_artifact_tag(artifact_id, tag_id)

    @staticmethod
    def _is_valid_slug(slug: str) -> bool:
        """Validate slug format."""
        import re
        return bool(re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", slug))
```

### Repository Layer

**File**: `skillmeat/cache/repositories.py`

Handles all database access:

```python
class TagRepository:
    """Data access layer for tags."""

    def create(self, name: str, slug: str, color: Optional[str]) -> Tag:
        """Create new tag."""
        tag = Tag(
            id=self.generate_id(),
            name=name,
            slug=slug,
            color=color,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(tag)
        session.commit()
        return tag

    def get_by_id(self, tag_id: str) -> Optional[Tag]:
        """Fetch tag by ID."""
        return session.query(Tag).filter(Tag.id == tag_id).first()

    def get_by_slug(self, slug: str) -> Optional[Tag]:
        """Fetch tag by slug."""
        return session.query(Tag).filter(Tag.slug == slug).first()

    def search(self, query: str, limit: int) -> List[Tag]:
        """Search tags by name (case-insensitive)."""
        return session.query(Tag)\
            .filter(Tag.name.ilike(f"%{query}%"))\
            .order_by(Tag.name)\
            .limit(limit)\
            .all()

    def count_artifacts(self, tag_id: str) -> int:
        """Count artifacts with this tag."""
        return session.query(artifact_tags)\
            .filter(artifact_tags.c.tag_id == tag_id)\
            .count()

    def add_artifact_tag(self, artifact_id: str, tag_id: str) -> None:
        """Create artifact-tag association."""
        session.execute(
            artifact_tags.insert().values(
                artifact_id=artifact_id,
                tag_id=tag_id,
                created_at=datetime.utcnow(),
            )
        )
        session.commit()
```

## API Layer

### Endpoints

**Base Path**: `/api/v1/tags`

#### List All Tags (Paginated)

```http
GET /api/v1/tags
Query Parameters:
  - limit: int (1-100, default 50)
  - after: str (cursor for pagination)

Response: TagListResponse
```

**Example**:
```bash
curl "http://localhost:8080/api/v1/tags?limit=20&after=Y3Vyc29yOjEw"
```

#### Get Tag by ID

```http
GET /api/v1/tags/{tag_id}

Response: TagResponse
Error Codes: 404 (Not Found)
```

#### Get Tag by Slug

```http
GET /api/v1/tags/slug/{slug}

Response: TagResponse
Error Codes: 404 (Not Found)
```

#### Create Tag

```http
POST /api/v1/tags
Content-Type: application/json

Request:
{
  "name": "Python",
  "slug": "python",
  "color": "#3776ab"
}

Response: TagResponse (201 Created)
Error Codes: 400 (Invalid), 409 (Duplicate)
```

**Tag Creation Rules**:
- `name`: 1-100 characters, required, unique
- `slug`: 1-100 characters, required, unique, kebab-case
- `color`: Optional, hex code format (#RRGGBB)

#### Update Tag

```http
PUT /api/v1/tags/{tag_id}
Content-Type: application/json

Request:
{
  "name": "Python 3",
  "color": "#3776ab"
}

Response: TagResponse
Error Codes: 400 (Invalid), 404 (Not Found), 409 (Duplicate slug)
```

#### Delete Tag

```http
DELETE /api/v1/tags/{tag_id}

Response: 204 No Content
Error Codes: 404 (Not Found)
```

#### Search Tags

```http
GET /api/v1/tags/search
Query Parameters:
  - q: str (search query, 1-100 chars, required)
  - limit: int (1-100, default 50)

Response: List[TagResponse]
Error Codes: 400 (Invalid query)
```

### Artifact-Tag Association Endpoints

These endpoints are implemented in the artifacts router:

#### Get Artifact Tags

```http
GET /api/v1/artifacts/{artifact_id}/tags

Response: List[TagResponse]
```

#### Add Tag to Artifact

```http
POST /api/v1/artifacts/{artifact_id}/tags/{tag_id}

Response: 204 No Content
Error Codes: 404 (Artifact or tag not found)
```

#### Remove Tag from Artifact

```http
DELETE /api/v1/artifacts/{artifact_id}/tags/{tag_id}

Response: 204 No Content
Error Codes: 404 (Artifact or tag not found)
```

### Schemas

**File**: `skillmeat/api/schemas/tags.py`

```python
class TagCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


class TagUpdateRequest(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    color: Optional[str] = None


class TagResponse(BaseModel):
    id: str
    name: str
    slug: str
    color: Optional[str]
    created_at: datetime
    updated_at: datetime
    artifact_count: Optional[int]


class TagListResponse(BaseModel):
    items: List[TagResponse]
    page_info: PageInfo
```

## Frontend Integration

### API Client

**File**: `skillmeat/web/lib/api/tags.ts`

```typescript
export async function fetchTags(limit?: number, after?: string): Promise<TagListResponse> {
  const params = new URLSearchParams();
  if (limit) params.set('limit', limit.toString());
  if (after) params.set('after', after);

  const url = buildUrl(`/tags${params.toString() ? `?${params.toString()}` : ''}`);
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch tags: ${response.statusText}`);
  }
  return response.json();
}

export async function searchTags(query: string, limit?: number): Promise<Tag[]> {
  const params = new URLSearchParams({ q: query });
  if (limit) params.set('limit', limit.toString());

  const response = await fetch(buildUrl(`/tags/search?${params.toString()}`));
  if (!response.ok) {
    throw new Error(`Failed to search tags: ${response.statusText}`);
  }
  return response.json();
}

export async function createTag(data: TagCreateRequest): Promise<Tag> {
  const response = await fetch(buildUrl('/tags'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to create tag: ${response.statusText}`);
  }
  return response.json();
}

export async function addTagToArtifact(artifactId: string, tagId: string): Promise<void> {
  const response = await fetch(buildUrl(`/artifacts/${artifactId}/tags/${tagId}`), {
    method: 'POST',
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to add tag: ${response.statusText}`);
  }
}

export async function removeTagFromArtifact(artifactId: string, tagId: string): Promise<void> {
  const response = await fetch(buildUrl(`/artifacts/${artifactId}/tags/${tagId}`), {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(`Failed to remove tag: ${response.statusText}`);
  }
}
```

### React Hooks

**File**: `skillmeat/web/hooks/use-tags.ts`

Uses TanStack Query for data management:

```typescript
export const tagKeys = {
  all: ['tags'] as const,
  lists: () => [...tagKeys.all, 'list'] as const,
  list: (filters?: { limit?: number; after?: string }) =>
    [...tagKeys.lists(), filters] as const,
  search: (query: string) => [...tagKeys.all, 'search', query] as const,
  artifact: (artifactId: string) => [...tagKeys.all, 'artifact', artifactId] as const,
};

export function useTags(limit?: number, after?: string) {
  return useQuery({
    queryKey: tagKeys.list({ limit, after }),
    queryFn: () => fetchTags(limit, after),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useAddTagToArtifact() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ artifactId, tagId }: { artifactId: string; tagId: string }) =>
      addTagToArtifact(artifactId, tagId),
    onSuccess: (_, { artifactId }) => {
      queryClient.invalidateQueries({ queryKey: tagKeys.artifact(artifactId) });
    },
  });
}
```

## Extending the Tags System

### Adding Tags to New Entities

To add tags to a new entity type (e.g., Collections or Projects):

#### 1. Create Junction Table

```sql
CREATE TABLE collection_tags (
  collection_id VARCHAR REFERENCES collections(id) ON DELETE CASCADE,
  tag_id VARCHAR REFERENCES tags(id) ON DELETE CASCADE,
  created_at TIMESTAMP NOT NULL,
  PRIMARY KEY (collection_id, tag_id)
);
```

#### 2. Add Model Relationship

```python
class Collection(Base):
    __tablename__ = "collections"
    id: str = Column(String, primary_key=True)
    # ... other fields

    tags = relationship("Tag", secondary="collection_tags")
```

#### 3. Add Repository Methods

```python
class CollectionRepository:
    def add_tag(self, collection_id: str, tag_id: str) -> None:
        session.execute(
            collection_tags.insert().values(
                collection_id=collection_id,
                tag_id=tag_id,
                created_at=datetime.utcnow(),
            )
        )
        session.commit()
```

#### 4. Add Service Methods

```python
class CollectionService:
    def add_tag_to_collection(self, collection_id: str, tag_id: str) -> None:
        if not self.repository.get_by_id(collection_id):
            raise LookupError("Collection not found")
        self.repository.add_tag(collection_id, tag_id)
```

#### 5. Add API Endpoints

```python
@router.post("/collections/{collection_id}/tags/{tag_id}")
async def add_tag_to_collection(collection_id: str, tag_id: str):
    service = CollectionService()
    service.add_tag_to_collection(collection_id, tag_id)
```

### Typed Tags

To support multiple tag categories (e.g., "technology" vs "status"):

#### Add Tag Type Column

```sql
ALTER TABLE tags ADD COLUMN tag_type VARCHAR DEFAULT 'general';
CREATE INDEX idx_tags_type ON tags(tag_type);
```

#### Filter by Type

```python
class TagRepository:
    def search_by_type(self, tag_type: str, query: str, limit: int):
        return session.query(Tag)\
            .filter(Tag.tag_type == tag_type)\
            .filter(Tag.name.ilike(f"%{query}%"))\
            .limit(limit)\
            .all()
```

#### Type Definitions

```typescript
export type TagType = 'technology' | 'status' | 'team' | 'general';

export interface Tag {
  id: string;
  name: string;
  slug: string;
  tag_type: TagType;
  color?: string;
}
```

## Performance Considerations

### Query Optimization

1. **Use Indexes**: All search queries benefit from indexes on `name`, `slug`, and `tag_id`
2. **Pagination**: Use cursor-based pagination for large tag lists
3. **Caching**: Frontend caches tags for 5 minutes via TanStack Query
4. **Lazy Loading**: Load artifact tags only when needed

### Database Indexes

```sql
-- Essential indexes for common queries
CREATE INDEX idx_tags_name ON tags(name);
CREATE INDEX idx_tags_slug ON tags(slug);
CREATE INDEX idx_artifact_tags_artifact ON artifact_tags(artifact_id);
CREATE INDEX idx_artifact_tags_tag ON artifact_tags(tag_id);
```

### Frontend Caching Strategy

```typescript
// TanStack Query configuration
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,      // 5 minutes
      cacheTime: 10 * 60 * 1000,     // 10 minutes
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});
```

## Error Handling

### Common Error Scenarios

| Error | Status | Cause | Resolution |
|-------|--------|-------|-----------|
| `Tag name already exists` | 409 | Duplicate tag name | Use existing tag or choose different name |
| `Tag slug already exists` | 409 | Duplicate slug | Use different slug |
| `Invalid slug format` | 400 | Slug not kebab-case | Use lowercase with hyphens |
| `Tag not found` | 404 | Tag ID doesn't exist | Verify tag ID |
| `Artifact not found` | 404 | Artifact doesn't exist | Verify artifact ID |
| `Invalid color format` | 400 | Color not hex code | Use format #RRGGBB |

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Tag slug must be lowercase",
    "detail": "Slug contains uppercase letters"
  },
  "request_id": "req-123abc"
}
```

## Testing

### Unit Tests

```python
def test_create_tag_validates_slug():
    service = TagService()
    with pytest.raises(ValueError, match="lowercase"):
        service.create_tag("Test", "INVALID-SLUG")

def test_add_tag_to_artifact_requires_valid_ids():
    service = TagService()
    with pytest.raises(LookupError):
        service.add_tag_to_artifact("invalid-artifact", "invalid-tag")
```

### API Integration Tests

```typescript
describe('Tags API', () => {
  it('creates tag successfully', async () => {
    const tag = await createTag({
      name: 'Python',
      slug: 'python',
      color: '#3776ab',
    });
    expect(tag.name).toBe('Python');
    expect(tag.slug).toBe('python');
  });

  it('rejects duplicate tag name', async () => {
    await expect(
      createTag({ name: 'Python', slug: 'python-lang' })
    ).rejects.toThrow('already exists');
  });
});
```

## Migration Guide

### Adding Tags to Existing Installation

1. **Create database tables** (run migration):
   ```bash
   alembic upgrade head  # Includes tags table creation
   ```

2. **Seed common tags** (optional):
   ```python
   service = TagService()
   common_tags = [
       ("Python", "python", "#3776ab"),
       ("TypeScript", "typescript", "#3178c6"),
       ("Testing", "testing", "#76d275"),
       ("Documentation", "documentation", "#e67e22"),
   ]
   for name, slug, color in common_tags:
       service.create_tag(name, slug, color)
   ```

3. **Update artifacts** (optional):
   ```python
   # Tag existing artifacts based on naming conventions
   service.add_tag_to_artifact("artifact-id", "python-tag-id")
   ```

## See Also

- [Router Patterns](../../.claude/rules/api/routers.md) - FastAPI router conventions
- [API Client Patterns](../../.claude/rules/web/api-client.md) - Frontend API integration
- [TanStack Query Docs](https://tanstack.com/query/latest) - Data fetching library
- [Tags User Guide](./tags-user-guide.md) - End-user documentation
