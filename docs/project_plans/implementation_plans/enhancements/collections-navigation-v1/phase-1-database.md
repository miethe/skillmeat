---
title: "Phase 1: Database Layer - Collections & Navigation Enhancement"
phase: 1
status: pending
assigned_to:
  - data-layer-expert
  - python-backend-engineer
dependencies: []
story_points: 8
duration: 1 week
---

# Phase 1: Database Layer

**Complexity**: Database design and ORM implementation
**Story Points**: 8 | **Duration**: 1 week | **Status**: Pending

---

## Phase Objective

Establish the SQLAlchemy ORM models and Alembic database migrations for supporting Collections and Groups functionality. This phase creates the data persistence layer that underpins all subsequent phases.

## Deliverables

### 1. Collection Model (TASK-1.1)
**Description**: SQLAlchemy ORM model for user collections

**Acceptance Criteria**:
- [ ] `Collection` model created with fields: id, name, description, created_at, updated_at, created_by
- [ ] Timestamps auto-managed (created_at, updated_at)
- [ ] Relationships: one-to-many with Groups, many-to-many with Artifacts
- [ ] Proper foreign key constraints and cascade rules
- [ ] String representation and to_dict() method implemented
- [ ] Indexes created for frequently queried fields (name, created_by)

**Files to Create/Modify**:
- `/skillmeat/cache/models.py` - Add Collection model class

**Estimated Effort**: 2 points

---

### 2. Group Model (TASK-1.2)
**Description**: SQLAlchemy ORM model for custom groups within collections

**Acceptance Criteria**:
- [ ] `Group` model created with fields: id, collection_id, name, description, position
- [ ] Timestamps auto-managed
- [ ] Foreign key to Collection with CASCADE delete
- [ ] Relationship: one-to-many with Artifacts (through association table)
- [ ] Unique constraint: (collection_id, name) - one group name per collection
- [ ] Position field for ordering groups within collection
- [ ] String representation and to_dict() method implemented
- [ ] Indexes created for (collection_id, position) composite query

**Files to Create/Modify**:
- `/skillmeat/cache/models.py` - Add Group model class

**Estimated Effort**: 2 points

---

### 3. CollectionArtifact Association Model (TASK-1.3)
**Description**: Many-to-many association table for Collection ↔ Artifact relationships

**Acceptance Criteria**:
- [ ] `CollectionArtifact` association model created
- [ ] Composite primary key: (collection_id, artifact_id)
- [ ] Added_at timestamp for tracking membership date
- [ ] Foreign keys with CASCADE delete on collection deletion
- [ ] Lazy loading configured for relationship traversal
- [ ] Back_populates configured in Collection and Artifact models
- [ ] Indexes on (collection_id) and (artifact_id) for join performance
- [ ] String representation implemented

**Files to Create/Modify**:
- `/skillmeat/cache/models.py` - Add CollectionArtifact association
- Update existing Artifact model to include relationship

**Estimated Effort**: 1.5 points

---

### 4. GroupArtifact Association Model (TASK-1.4)
**Description**: Many-to-many association table for Group ↔ Artifact relationships

**Acceptance Criteria**:
- [ ] `GroupArtifact` association model created
- [ ] Composite primary key: (group_id, artifact_id)
- [ ] Position field for ordering artifacts within group
- [ ] Added_at timestamp for tracking membership date
- [ ] Foreign keys with CASCADE delete on group deletion
- [ ] Lazy loading configured for relationship traversal
- [ ] Back_populates configured in Group and Artifact models
- [ ] Indexes on (group_id, position) for ordered queries
- [ ] String representation implemented

**Files to Create/Modify**:
- `/skillmeat/cache/models.py` - Add GroupArtifact association

**Estimated Effort**: 1.5 points

---

### 5. Alembic Migration: Create Collections Tables (TASK-1.5)
**Description**: Alembic migration to create collections, groups, and association tables

**Acceptance Criteria**:
- [ ] Migration file created in `/skillmeat/cache/migrations/versions/`
- [ ] Migration creates collections table with all fields and constraints
- [ ] Migration creates groups table with all fields and constraints
- [ ] Migration creates collection_artifacts association table
- [ ] Migration creates group_artifacts association table
- [ ] All foreign keys created with proper constraints
- [ ] All indexes created for query optimization
- [ ] Migration includes downgrade path (drop tables)
- [ ] Migration tested: `alembic upgrade head` succeeds
- [ ] Migration rollback tested: `alembic downgrade -1` succeeds

**Files to Create/Modify**:
- `/skillmeat/cache/migrations/versions/TIMESTAMP_create_collections_schema.py`

**Estimated Effort**: 1.5 points

---

## Task Breakdown Table

| Task ID | Task Name | Description | Acceptance Criteria Count | Story Points | Assigned To | Status |
|---------|-----------|-------------|--------------------------|---------------|-------------|--------|
| TASK-1.1 | Collection Model | SQLAlchemy ORM model for collections | 6 | 2 | data-layer-expert | Pending |
| TASK-1.2 | Group Model | SQLAlchemy ORM model for groups | 6 | 2 | data-layer-expert | Pending |
| TASK-1.3 | CollectionArtifact Association | M2M association for Collection↔Artifact | 8 | 1.5 | data-layer-expert | Pending |
| TASK-1.4 | GroupArtifact Association | M2M association for Group↔Artifact | 8 | 1.5 | data-layer-expert | Pending |
| TASK-1.5 | Alembic Migration | Database migration for new schema | 10 | 1.5 | python-backend-engineer | Pending |

**Total**: 8 story points

---

## Database Schema

### Collections Table

```sql
CREATE TABLE collections (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    CHECK (length(name) > 0 AND length(name) <= 255)
);

CREATE INDEX idx_collections_name ON collections(name);
CREATE INDEX idx_collections_created_by ON collections(created_by);
CREATE INDEX idx_collections_created_at ON collections(created_at);
```

### Groups Table

```sql
CREATE TABLE groups (
    id TEXT PRIMARY KEY,
    collection_id TEXT NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    position INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(collection_id, name),
    CHECK (length(name) > 0 AND length(name) <= 255),
    CHECK (position >= 0)
);

CREATE INDEX idx_groups_collection_id ON groups(collection_id);
CREATE INDEX idx_groups_position ON groups(collection_id, position);
CREATE INDEX idx_groups_created_at ON groups(created_at);
```

### CollectionArtifacts Association Table

```sql
CREATE TABLE collection_artifacts (
    collection_id TEXT NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    artifact_id TEXT NOT NULL,
    added_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(collection_id, artifact_id)
);

CREATE INDEX idx_collection_artifacts_artifact_id ON collection_artifacts(artifact_id);
CREATE INDEX idx_collection_artifacts_added_at ON collection_artifacts(added_at);
```

### GroupArtifacts Association Table

```sql
CREATE TABLE group_artifacts (
    group_id TEXT NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    artifact_id TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    added_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(group_id, artifact_id),
    CHECK (position >= 0)
);

CREATE INDEX idx_group_artifacts_artifact_id ON group_artifacts(artifact_id);
CREATE INDEX idx_group_artifacts_position ON group_artifacts(group_id, position);
CREATE INDEX idx_group_artifacts_added_at ON group_artifacts(added_at);
```

---

## ORM Model Code Structure

### Collection Model

```python
class Collection(Base):
    """User-defined collection of artifacts."""

    __tablename__ = "collections"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    groups: Mapped[List["Group"]] = relationship(
        "Group",
        back_populates="collection",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    artifacts: Mapped[List["Artifact"]] = relationship(
        "Artifact",
        secondary="collection_artifacts",
        back_populates="collections",
        lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint("length(name) > 0 AND length(name) <= 255"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "group_count": len(self.groups),
            "artifact_count": len(self.artifacts),
        }
```

### Group Model

```python
class Group(Base):
    """Custom grouping of artifacts within a collection."""

    __tablename__ = "groups"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    collection_id: Mapped[str] = mapped_column(
        String, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    collection: Mapped["Collection"] = relationship(
        "Collection", back_populates="groups"
    )
    artifacts: Mapped[List["Artifact"]] = relationship(
        "Artifact",
        secondary="group_artifacts",
        back_populates="groups",
        lazy="selectin"
    )

    __table_args__ = (
        UniqueConstraint("collection_id", "name", name="uq_group_name_per_collection"),
        CheckConstraint("length(name) > 0 AND length(name) <= 255"),
        CheckConstraint("position >= 0"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "collection_id": self.collection_id,
            "name": self.name,
            "description": self.description,
            "position": self.position,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "artifact_count": len(self.artifacts),
        }
```

### Association Models

```python
class CollectionArtifact(Base):
    """Association between Collection and Artifact."""

    __tablename__ = "collection_artifacts"

    collection_id: Mapped[str] = mapped_column(
        String, ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True
    )
    artifact_id: Mapped[str] = mapped_column(String, primary_key=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )


class GroupArtifact(Base):
    """Association between Group and Artifact with position."""

    __tablename__ = "group_artifacts"

    group_id: Mapped[str] = mapped_column(
        String, ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True
    )
    artifact_id: Mapped[str] = mapped_column(String, primary_key=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    added_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        CheckConstraint("position >= 0"),
    )
```

---

## Key Design Decisions

### 1. ID Generation
- Use UUID strings for all IDs (consistent with existing Artifact model)
- Auto-generate in Python using `uuid.uuid4().hex`

### 2. Relationships
- **One-to-Many**: Collection → Groups (with CASCADE delete)
- **Many-to-Many**: Collection ↔ Artifacts and Group ↔ Artifacts
- **Cascade**: Delete collection → delete groups and associations

### 3. Indexes
- Single-field: (name), (created_by), (artifact_id)
- Composite: (collection_id, name), (group_id, position), (collection_id, position)
- Strategy: Optimize for common queries (list, filter, sort)

### 4. Constraints
- Unique: (collection_id, group_name) - prevent duplicate group names in collection
- Check: Validate string lengths, position >= 0
- Foreign keys: CASCADE delete for data consistency

### 5. Lazy Loading
- Groups and artifacts loaded eagerly (selectin) to avoid N+1 queries
- Can be optimized later if performance issues arise

---

## Testing Strategy

### Unit Tests

**File**: `/skillmeat/cache/tests/test_collections_models.py`

```python
def test_collection_creation():
    """Test creating a collection."""
    collection = Collection(
        id="col-123",
        name="My Collection",
        description="Test collection"
    )
    assert collection.name == "My Collection"
    assert collection.created_at is not None

def test_group_creation():
    """Test creating a group within collection."""
    group = Group(
        id="grp-123",
        collection_id="col-123",
        name="Important Skills",
        position=0
    )
    assert group.collection_id == "col-123"
    assert group.position == 0

def test_collection_group_relationship():
    """Test one-to-many relationship between Collection and Group."""
    collection = Collection(id="col-123", name="Test")
    group1 = Group(id="grp-1", collection_id="col-123", name="Group 1", position=0)
    group2 = Group(id="grp-2", collection_id="col-123", name="Group 2", position=1)
    collection.groups = [group1, group2]

    assert len(collection.groups) == 2
    assert collection.groups[0].name == "Group 1"

def test_group_unique_name_constraint():
    """Test unique constraint on group names within collection."""
    # This should be enforced at database level
    # Test by attempting to insert duplicate and catching error

def test_cascade_delete():
    """Test cascade delete when collection is deleted."""
    # Verify groups are deleted when collection is deleted
```

### Integration Tests

**File**: `/skillmeat/cache/tests/test_collections_queries.py`

```python
def test_list_collections():
    """Test querying all collections."""
    # Create test collections, verify query returns all

def test_filter_groups_by_collection():
    """Test filtering groups by collection_id."""
    # Create multiple collections and groups, verify filtering works

def test_add_artifact_to_collection():
    """Test adding artifact to collection via association."""
    # Verify CollectionArtifact association is created

def test_add_artifact_to_group():
    """Test adding artifact to group via association."""
    # Verify GroupArtifact association with position is created
```

### Migration Tests

**File**: `/skillmeat/cache/tests/test_collections_migration.py`

```python
def test_migration_up():
    """Test migration up creates all tables and constraints."""
    # Run migration, verify tables exist and constraints are applied

def test_migration_down():
    """Test migration down removes tables."""
    # Run migration up, then down, verify tables are dropped

def test_migration_idempotent():
    """Test migration can be run multiple times safely."""
    # Run migration up multiple times, verify no errors
```

---

## Quality Gates

### Code Review Checklist
- [ ] Models follow SQLAlchemy 2.0+ best practices
- [ ] Type hints are complete and accurate (no `Any`)
- [ ] Foreign keys and constraints properly defined
- [ ] Relationships use lazy="selectin" to avoid N+1
- [ ] to_dict() methods implemented for all models
- [ ] Documentation strings explain relationships and constraints
- [ ] No hardcoded values or magic numbers

### Database Review Checklist
- [ ] Schema designed for query efficiency
- [ ] Indexes created for common access patterns
- [ ] Constraints prevent invalid data
- [ ] Cascade rules appropriate and safe
- [ ] Composite keys chosen where needed
- [ ] No unnecessary normalization

### Testing Checklist
- [ ] All model relationships tested
- [ ] Constraints validated at database level
- [ ] Migration tested up and down
- [ ] Performance queries verified with EXPLAIN PLAN
- [ ] Cascade deletes verified
- [ ] Test coverage > 90% for models

---

## Files to Create

### New Files

1. **Migration file**: `/skillmeat/cache/migrations/versions/{timestamp}_create_collections_schema.py`
   - Alembic migration with up/down operations
   - ~150 lines of SQL/Python

### Modified Files

1. **Models**: `/skillmeat/cache/models.py`
   - Add Collection class (~40 lines)
   - Add Group class (~40 lines)
   - Add CollectionArtifact class (~10 lines)
   - Add GroupArtifact class (~12 lines)
   - Update Artifact model relationships (~5 lines)

---

## Dependencies

### Runtime Dependencies
- SQLAlchemy 2.0+ (already in project)
- Python 3.9+ (already required)

### Development Dependencies
- pytest (for testing)
- alembic (for migrations)

### Database
- SQLite 3.30+ (with WAL mode support)

---

## Effort Breakdown

| Task | Hours | Notes |
|------|-------|-------|
| Collection Model | 3 | Includes design, implementation, docstrings |
| Group Model | 3 | Similar to Collection but with position |
| Association Models | 2 | Simpler, mostly constraints and relationships |
| Alembic Migration | 3 | Create migration file, test up/down |
| Testing | 4 | Unit + integration + migration tests |
| Code Review & Fixes | 2 | Feedback and revisions |
| **Total** | **17 hours** | ~2.1 days actual work, ~5 business days calendar |

---

## Rollback Procedure

If issues arise during Phase 1:

```bash
# Rollback migration
alembic downgrade -1

# Verify rollback
alembic current

# Delete migration file
rm /skillmeat/cache/migrations/versions/{timestamp}_create_collections_schema.py

# Revert model changes
git checkout -- skillmeat/cache/models.py
```

---

## Orchestration Quick Reference

### Task Delegation Commands

Batch 1 (Parallel):
- **TASK-1.1** → `data-layer-expert` (2h) - Create Collection model
- **TASK-1.2** → `data-layer-expert` (2h) - Create Group model

Batch 2 (Parallel, after Batch 1):
- **TASK-1.3** → `data-layer-expert` (1.5h) - Create CollectionArtifact association
- **TASK-1.4** → `data-layer-expert` (1.5h) - Create GroupArtifact association

Batch 3 (Sequential, after Batch 2):
- **TASK-1.5** → `python-backend-engineer` (1.5h) - Create migration and test

---

## Success Criteria

Phase 1 is complete when:

1. **Database Models**: All 5 models created and tested
2. **Migrations**: Alembic migration created and tested (up/down)
3. **Relationships**: All foreign keys and relationships verified
4. **Constraints**: All CHECK and UNIQUE constraints enforced
5. **Tests**: 90%+ test coverage achieved
6. **Documentation**: All models documented with docstrings
7. **Performance**: Indexes created and query plans verified
8. **Code Review**: Approved by data-layer-expert

---

## Next Phase

Phase 2 (Backend API) depends on Phase 1 being complete. It will:
- Create FastAPI routers for collections and groups
- Implement CRUD operations using the new models
- Define Pydantic schemas for requests/responses
- Add deployment summary endpoints

**Phase 1 → Phase 2 Handoff**:
- Provide list of model classes and their methods
- Document relationship navigation patterns
- Share test fixtures for use in Phase 2 tests
