---
type: progress
prd: "collections-navigation"
phase: 1
title: "Database Layer - Collections & Navigation"
status: "pending"
overall_progress: 0
total_tasks: 5
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
owners: ["data-layer-expert"]
contributors: ["python-backend-engineer"]

tasks:
  - id: "TASK-1.1"
    name: "Collection Model"
    description: "SQLAlchemy ORM model for user collections"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: []
    estimated_effort: "2h"
    priority: "high"

  - id: "TASK-1.2"
    name: "Group Model"
    description: "SQLAlchemy ORM model for custom groups within collections"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: []
    estimated_effort: "2h"
    priority: "high"

  - id: "TASK-1.3"
    name: "CollectionArtifact Association Model"
    description: "Many-to-many association table for Collection ↔ Artifact relationships"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["TASK-1.1"]
    estimated_effort: "1.5h"
    priority: "high"

  - id: "TASK-1.4"
    name: "GroupArtifact Association Model"
    description: "Many-to-many association table for Group ↔ Artifact relationships"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["TASK-1.2"]
    estimated_effort: "1.5h"
    priority: "high"

  - id: "TASK-1.5"
    name: "Alembic Migration: Create Collections Tables"
    description: "Alembic migration to create collections, groups, and association tables"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.1", "TASK-1.2", "TASK-1.3", "TASK-1.4"]
    estimated_effort: "1.5h"
    priority: "high"

parallelization:
  batch_1: ["TASK-1.1", "TASK-1.2"]
  batch_2: ["TASK-1.3", "TASK-1.4"]
  batch_3: ["TASK-1.5"]
  critical_path: ["TASK-1.1", "TASK-1.3", "TASK-1.5"]
  estimated_total_time: "1w"

blockers: []

success_criteria:
  - id: "SC-1"
    description: "SQLite schema created with proper indexes for performance"
    status: "pending"
  - id: "SC-2"
    description: "Alembic migrations support upgrade/downgrade"
    status: "pending"
  - id: "SC-3"
    description: "SQLAlchemy models include all relationships and validation"
    status: "pending"
  - id: "SC-4"
    description: "All models include to_dict() methods for serialization"
    status: "pending"
  - id: "SC-5"
    description: "Test coverage >90% for models"
    status: "pending"

files_modified: []
---

# collections-navigation - Phase 1: Database Layer

**Phase**: 1 of 6
**Status**: Pending (0% complete)
**Owner**: data-layer-expert
**Contributors**: python-backend-engineer

---

## Phase Objective

Establish the SQLAlchemy ORM models and Alembic database migrations for supporting Collections and Groups functionality. This phase creates the data persistence layer that underpins all subsequent phases.

---

## Orchestration Quick Reference

**Batch 1** (Parallel - Models):
- TASK-1.1 → `data-layer-expert` (2h) - Collection model
- TASK-1.2 → `data-layer-expert` (2h) - Group model

**Batch 2** (Parallel - Associations, after Batch 1):
- TASK-1.3 → `data-layer-expert` (1.5h) - CollectionArtifact association
- TASK-1.4 → `data-layer-expert` (1.5h) - GroupArtifact association

**Batch 3** (Sequential - Migration, after Batch 2):
- TASK-1.5 → `python-backend-engineer` (1.5h) - Alembic migration

### Task Delegation Commands

```
# Batch 1 (Parallel)
Task("data-layer-expert", "TASK-1.1: Create Collection SQLAlchemy ORM model with fields: id, name, description, created_at, updated_at, created_by. Include timestamps auto-management, relationships (one-to-many with Groups, many-to-many with Artifacts), proper foreign key constraints and cascade rules, string representation, to_dict() method, and indexes on name and created_by. File: /skillmeat/cache/models.py")

Task("data-layer-expert", "TASK-1.2: Create Group SQLAlchemy ORM model with fields: id, collection_id, name, description, position. Include timestamps auto-management, foreign key to Collection with CASCADE delete, relationship (one-to-many with Artifacts through association table), unique constraint on (collection_id, name), position field for ordering, string representation, to_dict() method, and indexes on (collection_id, position). File: /skillmeat/cache/models.py")

# Batch 2 (Parallel, after Batch 1)
Task("data-layer-expert", "TASK-1.3: Create CollectionArtifact association model with composite primary key (collection_id, artifact_id), added_at timestamp, foreign keys with CASCADE delete on collection deletion, lazy loading configuration, back_populates in Collection and Artifact models, indexes on both IDs, and string representation. File: /skillmeat/cache/models.py")

Task("data-layer-expert", "TASK-1.4: Create GroupArtifact association model with composite primary key (group_id, artifact_id), position field for ordering, added_at timestamp, foreign keys with CASCADE delete on group deletion, lazy loading configuration, back_populates in Group and Artifact models, indexes on (group_id, position), and string representation. File: /skillmeat/cache/models.py")

# Batch 3 (Sequential, after Batch 2)
Task("python-backend-engineer", "TASK-1.5: Create Alembic migration to create collections, groups, collection_artifacts, and group_artifacts tables with all fields, constraints, foreign keys, and indexes. Include downgrade path and test both upgrade and rollback. File: /skillmeat/cache/migrations/versions/TIMESTAMP_create_collections_schema.py")
```

---

## Task Details

### TASK-1.1: Collection Model
- **Status**: pending
- **Assigned**: data-layer-expert
- **Estimated Effort**: 2h
- **Priority**: high

**Description**: SQLAlchemy ORM model for user collections

**Acceptance Criteria**:
- [ ] `Collection` model created with fields: id, name, description, created_at, updated_at, created_by
- [ ] Timestamps auto-managed (created_at, updated_at)
- [ ] Relationships: one-to-many with Groups, many-to-many with Artifacts
- [ ] Proper foreign key constraints and cascade rules
- [ ] String representation and to_dict() method implemented
- [ ] Indexes created for frequently queried fields (name, created_by)

**Files**: `/skillmeat/cache/models.py`

---

### TASK-1.2: Group Model
- **Status**: pending
- **Assigned**: data-layer-expert
- **Estimated Effort**: 2h
- **Priority**: high

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

**Files**: `/skillmeat/cache/models.py`

---

### TASK-1.3: CollectionArtifact Association Model
- **Status**: pending
- **Assigned**: data-layer-expert
- **Estimated Effort**: 1.5h
- **Priority**: high
- **Dependencies**: TASK-1.1

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

**Files**: `/skillmeat/cache/models.py`

---

### TASK-1.4: GroupArtifact Association Model
- **Status**: pending
- **Assigned**: data-layer-expert
- **Estimated Effort**: 1.5h
- **Priority**: high
- **Dependencies**: TASK-1.2

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

**Files**: `/skillmeat/cache/models.py`

---

### TASK-1.5: Alembic Migration: Create Collections Tables
- **Status**: pending
- **Assigned**: python-backend-engineer
- **Estimated Effort**: 1.5h
- **Priority**: high
- **Dependencies**: TASK-1.1, TASK-1.2, TASK-1.3, TASK-1.4

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

**Files**: `/skillmeat/cache/migrations/versions/TIMESTAMP_create_collections_schema.py`

---

## Progress Summary

**Completed**: 0/5 tasks (0%)
**In Progress**: 0/5 tasks
**Blocked**: 0/5 tasks
**Pending**: 5/5 tasks

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

---

## Testing Requirements

### Unit Tests
**File**: `/skillmeat/cache/tests/test_collections_models.py`

- Collection creation and validation
- Group creation with position
- Collection-Group relationship (one-to-many)
- Group unique name constraint per collection
- Cascade delete verification
- Association table operations

### Integration Tests
**File**: `/skillmeat/cache/tests/test_collections_queries.py`

- List collections with pagination
- Filter groups by collection_id
- Add/remove artifacts from collections
- Add/remove artifacts from groups with position

### Migration Tests
**File**: `/skillmeat/cache/tests/test_collections_migration.py`

- Migration up creates all tables and constraints
- Migration down removes tables
- Migration idempotency

---

## Phase Completion Criteria

Phase 1 is complete when:

1. **Database Models**: All 5 models created and tested
2. **Migrations**: Alembic migration created and tested (up/down)
3. **Relationships**: All foreign keys and relationships verified
4. **Constraints**: All CHECK and UNIQUE constraints enforced
5. **Tests**: 90%+ test coverage achieved
6. **Documentation**: All models documented with docstrings
7. **Performance**: Indexes created and query plans verified
8. **Code Review**: Approved by data-layer-expert
