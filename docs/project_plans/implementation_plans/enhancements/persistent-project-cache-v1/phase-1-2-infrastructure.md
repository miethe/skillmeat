---
title: 'Persistent Project Cache - Phases 1-2: Infrastructure'
description: Database layer and service layer implementation for cache infrastructure
audience:
- ai-agents
- developers
tags:
- implementation-plan
- cache
- database
- service-layer
- background-jobs
created: 2025-11-30
updated: 2025-12-01
category: implementation
status: inferred_complete
parent_plan: /docs/project_plans/implementation_plans/enhancements/persistent-project-cache-v1.md
prd_reference: /docs/project_plans/PRDs/enhancements/persistent-project-cache-v1.md
schema_version: 2
doc_type: phase_plan
feature_slug: persistent-project-cache
prd_ref: null
plan_ref: null
---
# Phases 1-2: Cache Infrastructure

**Parent Plan:** [Persistent Project Cache Implementation Plan](../persistent-project-cache-v1.md)

---

## Phase 1: Cache Infrastructure (Database & ORM)

**Duration:** 1 week | **Story Points:** 21 | **Assigned:** data-layer-expert, python-backend-engineer

### Task 1.1: Design & Create SQLite Schema

**Task ID:** CACHE-1.1
**Assigned To:** data-layer-expert
**Story Points:** 5
**Dependencies:** None
**Duration:** 2 days

**Description:**
Design the SQLite database schema for caching project and artifact metadata. Create schema.py with table definitions.

**Acceptance Criteria:**
- [ ] Schema includes projects, artifacts, artifact_metadata, marketplace, cache_metadata tables
- [ ] Appropriate indexes created for performance (project_id, type, is_outdated, updated_at)
- [ ] Foreign key relationships defined
- [ ] Schema supports both local and marketplace artifacts
- [ ] Documentation of schema design rationale included

**Implementation Notes:**
- Use SQLAlchemy declarative models
- Define all tables with proper types (TEXT, TIMESTAMP, JSON, BOOLEAN)
- Create composite indexes for common queries (project_id + type, is_outdated + type)
- Add PRAGMA optimizations for concurrent access (WAL mode)

**File to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/schema.py`

**Key Schema Components:**
```
projects: id, name, path, description, created_at, updated_at, last_fetched, status, error_message
artifacts: id, project_id, name, type, source, deployed_version, upstream_version, is_outdated, local_modified, created_at, updated_at
artifact_metadata: artifact_id, metadata (JSON), description, tags, aliases
marketplace: id, name, type, url, description, cached_at, data (JSON)
cache_metadata: key, value, updated_at
```

---

### Task 1.2: Create Alembic Migrations

**Task ID:** CACHE-1.2
**Assigned To:** python-backend-engineer
**Story Points:** 3
**Dependencies:** CACHE-1.1
**Duration:** 1 day

**Description:**
Create Alembic migration scripts to initialize the cache database schema. Ensure migrations are idempotent and support schema updates in future.

**Acceptance Criteria:**
- [ ] Initial migration creates all cache tables
- [ ] Migration supports upgrade and downgrade
- [ ] Migration is idempotent (safe to run multiple times)
- [ ] Migration tested against fresh database
- [ ] Foreign key constraints enforced
- [ ] Indexes created in migration

**Implementation Notes:**
- Use `alembic revision --autogenerate` to detect changes
- Ensure migration is checked into version control
- Include descriptive docstrings
- Test rollback scenario

**Files to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/migrations/versions/001_initial_schema.py`

---

### Task 1.3: Create SQLAlchemy Models (ORM Layer)

**Task ID:** CACHE-1.3
**Assigned To:** python-backend-engineer
**Story Points:** 5
**Dependencies:** CACHE-1.1
**Duration:** 2 days

**Description:**
Implement SQLAlchemy ORM models for all cache tables. Define models in models.py with proper relationships, validators, and serialization methods.

**Acceptance Criteria:**
- [ ] Models created for Project, Artifact, ArtifactMetadata, MarketplaceEntry, CacheMetadata
- [ ] Relationships defined (Project.artifacts, Artifact.metadata, etc.)
- [ ] Timestamps auto-updated (created_at, updated_at)
- [ ] Models include to_dict() or Pydantic schemas for JSON serialization
- [ ] Validation added (e.g., artifact type enum)
- [ ] Type hints throughout

**Implementation Notes:**
- Use SQLAlchemy 2.0+ declarative syntax
- Define __repr__ for debugging
- Use column_property for computed fields if needed
- Add __table_args__ for indexes and constraints

**Files to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/models.py`

**Key Models:**
```python
class Project(Base):
    id: str, name: str, path: str, created_at: datetime, updated_at: datetime,
    last_fetched: datetime, status: str, error_message: Optional[str],
    artifacts: relationship

class Artifact(Base):
    id: str, project_id: str, name: str, type: str, source: Optional[str],
    deployed_version: Optional[str], upstream_version: Optional[str],
    is_outdated: bool, local_modified: bool, created_at: datetime, updated_at: datetime,
    metadata: relationship

class ArtifactMetadata(Base):
    artifact_id: str, metadata: dict (JSON), description: str, tags: str, aliases: str

class MarketplaceEntry(Base):
    id: str, name: str, type: str, url: str, description: str, cached_at: datetime, data: dict

class CacheMetadata(Base):
    key: str, value: str, updated_at: datetime
```

---

### Task 1.4: Implement CacheRepository (Data Access Layer)

**Task ID:** CACHE-1.4
**Assigned To:** python-backend-engineer
**Story Points:** 5
**Dependencies:** CACHE-1.3
**Duration:** 2 days

**Description:**
Implement CacheRepository class for low-level database operations (CRUD, queries, transactions). This is the repository pattern layer that abstracts SQLAlchemy.

**Acceptance Criteria:**
- [ ] CRUD operations: create_project, read_project, update_project, delete_project
- [ ] CRUD operations: create_artifacts, read_artifacts, update_artifacts, delete_artifacts
- [ ] Batch operations: bulk_insert_artifacts, bulk_update_artifacts
- [ ] Query methods: get_projects_needing_refresh, get_outdated_artifacts, search_artifacts
- [ ] Transaction support: all writes wrapped in transactions
- [ ] Error handling: graceful database errors with custom exceptions
- [ ] Logging: debug logs for all operations
- [ ] Type hints throughout

**Implementation Notes:**
- Use dependency injection for session management
- Implement connection pooling
- Add retry logic for transient failures
- Use context managers for transactions
- Define custom exceptions: CacheError, CacheNotFoundError, CacheConstraintError

**Files to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/repository.py`

**Key Methods:**
```python
# Projects
def create_project(project: Project) -> Project
def get_project(project_id: str) -> Optional[Project]
def list_projects(skip: int = 0, limit: int = 100) -> List[Project]
def update_project(project_id: str, **kwargs) -> Project
def delete_project(project_id: str) -> None
def get_stale_projects(ttl_minutes: int = 360) -> List[Project]

# Artifacts
def create_artifact(artifact: Artifact) -> Artifact
def get_artifact(artifact_id: str) -> Optional[Artifact]
def list_artifacts_by_project(project_id: str) -> List[Artifact]
def list_outdated_artifacts() -> List[Artifact]
def bulk_update_artifacts(artifacts: List[Artifact]) -> None
def get_artifacts_by_type(artifact_type: str) -> List[Artifact]

# Metadata
def get_cache_metadata(key: str) -> Optional[str]
def set_cache_metadata(key: str, value: str) -> None

# Transactions
def begin_transaction() -> context manager
def commit_transaction()
def rollback_transaction()
```

---

### Task 1.5: Unit Tests for Database Layer

**Task ID:** CACHE-1.5
**Assigned To:** python-backend-engineer
**Story Points:** 3
**Dependencies:** CACHE-1.4
**Duration:** 1.5 days

**Description:**
Write comprehensive unit tests for CacheRepository, testing all CRUD operations, edge cases, and error handling.

**Acceptance Criteria:**
- [ ] Test coverage >80% for repository.py
- [ ] Tests for CRUD operations (create, read, update, delete)
- [ ] Tests for batch operations
- [ ] Tests for query filtering and search
- [ ] Tests for transaction rollback on errors
- [ ] Tests for concurrent read/write scenarios
- [ ] Tests for error handling (missing records, constraint violations)
- [ ] Tests use fixtures for test data setup
- [ ] Tests run in isolation (no test interdependencies)

**Implementation Notes:**
- Use pytest with SQLite in-memory database for speed
- Create fixtures for test database setup/teardown
- Mock external dependencies
- Use parametrized tests for similar test cases

**Files to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/tests/test_cache_repository.py`

---

## Phase 2: Cache Service Layer & Background Refresh

**Duration:** 1.5 weeks | **Story Points:** 28 | **Assigned:** python-backend-engineer, backend-architect

### Task 2.1: Implement CacheManager (Service Layer)

**Task ID:** CACHE-2.1
**Assigned To:** python-backend-engineer
**Story Points:** 8
**Dependencies:** CACHE-1.4
**Duration:** 3 days

**Description:**
Implement CacheManager class, the main service layer for cache operations. Provides high-level methods for reading, writing, invalidating cache. Manages concurrent access with locking.

**Acceptance Criteria:**
- [ ] Methods: populate_cache, load_projects, load_artifacts, invalidate_cache, refresh_cache_if_stale
- [ ] Locking mechanism for concurrent access (read/write locks)
- [ ] Fallback to API if cache empty
- [ ] Cache hit/miss tracking and logging
- [ ] Graceful error handling with recovery options
- [ ] Transaction management (atomic operations)
- [ ] Configuration support (TTL, max size)
- [ ] Type hints and comprehensive docstrings
- [ ] No direct repository usage outside of CacheManager in other modules

**Implementation Notes:**
- Use threading.RLock or similar for synchronization
- Implement cache invalidation strategies (time-based, manual, event-driven)
- Add observability: log cache hits/misses, query times
- Support graceful cache rebuilding on corruption
- Handle SQLite locks gracefully (timeout, retry)

**Files to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/manager.py`

**Key Methods:**
```python
class CacheManager:
    def __init__(self, db_path: str, ttl_minutes: int = 360)
    def initialize_cache(self) -> bool  # Create DB if needed

    # Read operations
    def get_projects(self) -> List[Project]
    def get_project(self, project_id: str) -> Optional[Project]
    def get_artifacts(self, project_id: str) -> List[Artifact]
    def get_outdated_artifacts(self) -> List[Artifact]
    def search_artifacts(self, query: str, filters: dict) -> List[Artifact]

    # Write operations
    def populate_projects(self, projects: List[Project]) -> None
    def populate_artifacts(self, project_id: str, artifacts: List[Artifact]) -> None
    def update_artifact_versions(self, artifact_id: str, deployed: str, upstream: str) -> None

    # Cache management
    def invalidate_cache(self, project_id: Optional[str] = None) -> None
    def refresh_if_stale(self, project_id: str, force: bool = False) -> bool
    def clear_cache(self) -> None

    # Status
    def get_cache_status(self) -> dict  # age, size, hit_rate, etc.
    def get_last_refresh_time(self, project_id: str) -> Optional[datetime]

    # Locking
    @contextmanager
    def read_lock(self)
    @contextmanager
    def write_lock()
```

---

### Task 2.2: Implement RefreshJob (Background Worker)

**Task ID:** CACHE-2.2
**Assigned To:** python-backend-engineer
**Story Points:** 8
**Dependencies:** CACHE-2.1
**Duration:** 3 days

**Description:**
Implement RefreshJob class for background cache refresh. Uses APScheduler or similar to run periodic updates. Handles TTL-based refresh, error recovery, event emission.

**Acceptance Criteria:**
- [ ] Background job scheduled to run every 6 hours (configurable)
- [ ] Checks each project's TTL and queues stale projects for refresh
- [ ] Fetches fresh data from API (or files for local projects)
- [ ] Compares with cached version and updates only if changed
- [ ] Emits events for UI real-time updates (changes detected)
- [ ] Handles API failures gracefully (retry logic, uses stale data)
- [ ] Low CPU priority to avoid blocking user operations
- [ ] Graceful shutdown on application termination
- [ ] Comprehensive error logging
- [ ] Unit testable (decoupled from scheduler)

**Implementation Notes:**
- Use APScheduler for scheduling (or BackgroundTasks from FastAPI)
- Implement exponential backoff for retries
- Track refresh progress in cache_metadata table
- Use event system to notify UI of changes
- Support manual refresh trigger from API

**Files to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/refresh.py`

**Key Methods:**
```python
class RefreshJob:
    def __init__(self, cache_manager: CacheManager, api_client: APIClient)
    def start_scheduler(self) -> None  # Start APScheduler
    def stop_scheduler(self) -> None  # Graceful shutdown
    def refresh_all(self) -> RefreshResult  # Manual refresh all projects
    def refresh_project(self, project_id: str) -> RefreshResult

    @scheduled_job('interval', hours=6)
    def periodic_refresh(self) -> None  # Periodic job

    async def emit_refresh_event(self, event: RefreshEvent) -> None
```

**RefreshEvent Types:**
```python
class RefreshStarted(BaseEvent):
    timestamp: datetime
    project_ids: List[str]

class RefreshCompleted(BaseEvent):
    timestamp: datetime
    project_id: str
    changes_detected: bool

class RefreshError(BaseEvent):
    timestamp: datetime
    project_id: str
    error: str
```

---

### Task 2.3: Implement FileWatcher (Change Detection)

**Task ID:** CACHE-2.3
**Assigned To:** python-backend-engineer
**Story Points:** 8
**Dependencies:** CACHE-2.1
**Duration:** 3 days

**Description:**
Implement FileWatcher class using watchdog library to monitor manifest.toml and deployment files. Detects changes and triggers cache invalidation.

**Acceptance Criteria:**
- [ ] Monitors ~/.skillmeat and ./.claude directories for changes
- [ ] Detects manifest.toml modifications
- [ ] Detects deployment directory changes
- [ ] Debounced event handling (wait 100ms for multiple changes)
- [ ] Cross-platform support (Windows, macOS, Linux)
- [ ] Graceful error handling for permission issues
- [ ] Configurable watch paths
- [ ] Proper resource cleanup on shutdown
- [ ] Event logging for debugging
- [ ] Unit tests with mock filesystem events

**Implementation Notes:**
- Use watchdog.observers.Observer for file monitoring
- Implement debouncing to avoid rapid cascading refreshes
- Map file changes to project_ids for selective invalidation
- Handle symlinks and moved files
- Implement path normalization for cross-platform compatibility

**Files to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/watcher.py`

**Key Methods:**
```python
class FileWatcher:
    def __init__(self, cache_manager: CacheManager, watch_paths: List[str])
    def start(self) -> None  # Start observer
    def stop(self) -> None  # Stop observer (cleanup)

    def on_manifest_modified(self, project_id: str) -> None
    def on_deployment_modified(self, project_id: str) -> None

    # Private methods for debouncing
    def _queue_invalidation(self, project_id: str) -> None
    def _debounce_invalidations(self) -> None
```

---

### Task 2.4: API Endpoints for Cache Management

**Task ID:** CACHE-2.4
**Assigned To:** python-backend-engineer
**Story Points:** 5
**Dependencies:** CACHE-2.1, CACHE-2.2
**Duration:** 2 days

**Description:**
Create FastAPI endpoints for cache operations: manual refresh, cache status, invalidation. Integrate CacheManager and RefreshJob.

**Acceptance Criteria:**
- [ ] POST /api/v1/cache/refresh - Trigger manual refresh
- [ ] GET /api/v1/cache/status - Get cache age, size, hit rate
- [ ] GET /api/v1/cache/projects - List cached projects
- [ ] GET /api/v1/cache/artifacts - List cached artifacts with filtering
- [ ] POST /api/v1/cache/invalidate - Invalidate specific project cache
- [ ] GET /api/v1/cache/stale-artifacts - List outdated artifacts
- [ ] Proper error handling (404, 500)
- [ ] Request/response validation with Pydantic schemas
- [ ] Authentication/authorization (if needed)
- [ ] Comprehensive docstrings

**Implementation Notes:**
- Dependency inject CacheManager and RefreshJob
- Return appropriate HTTP status codes
- Include timestamps in responses
- Support filtering/pagination for list endpoints

**Files to Create/Modify:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/cache.py` (new)
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/projects.py` (modify for cache integration)

**Endpoints:**
```
POST   /api/v1/cache/refresh
GET    /api/v1/cache/status
GET    /api/v1/cache/projects
GET    /api/v1/cache/artifacts?project_id=X&type=skill
POST   /api/v1/cache/invalidate
GET    /api/v1/cache/stale-artifacts
```

---

### Task 2.5: Integration Tests for Cache & Refresh

**Task ID:** CACHE-2.5
**Assigned To:** python-backend-engineer
**Story Points:** 5
**Dependencies:** CACHE-2.4
**Duration:** 2 days

**Description:**
Write integration tests for CacheManager, RefreshJob, FileWatcher, and API endpoints. Test end-to-end cache population, refresh, and invalidation workflows.

**Acceptance Criteria:**
- [ ] Test cache population from API data
- [ ] Test TTL-based refresh triggers
- [ ] Test file watcher triggering cache invalidation
- [ ] Test manual refresh endpoint
- [ ] Test concurrent read/write access
- [ ] Test fallback to API when cache empty
- [ ] Test refresh events emission
- [ ] Test error recovery and retries
- [ ] Test cache status endpoint
- [ ] All tests pass, documented, no flakiness

**Implementation Notes:**
- Use test fixtures for API mocking
- Use pytest-asyncio for async endpoint testing
- Use temp directories for file watcher tests
- Isolate tests from system directories

**Files to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/tests/integration/test_cache_integration.py`
- `/Users/miethe/dev/homelab/development/skillmeat/tests/test_refresh_job.py`
- `/Users/miethe/dev/homelab/development/skillmeat/tests/test_file_watcher.py`

---

## Phase 1-2 Orchestration Quick Reference

### Phase 1 Parallelization
- CACHE-1.1 (Schema design) → CACHE-1.2 (Migrations) & CACHE-1.3 (Models)
- CACHE-1.4 (Repository) depends on CACHE-1.3
- CACHE-1.5 (Tests) depends on CACHE-1.4

### Phase 2 Parallelization
- CACHE-2.1 (CacheManager) in parallel with CACHE-2.3 (FileWatcher)
- CACHE-2.2 (RefreshJob) depends on CACHE-2.1
- CACHE-2.4 (API) depends on CACHE-2.1, CACHE-2.2
- CACHE-2.5 (Tests) depends on CACHE-2.4

### Task Delegation Commands

**Phase 1 Batch (Parallel):**

```
Task("data-layer-expert", "CACHE-1.1: Design SQLite cache schema.
  Location: skillmeat/cache/schema.py
  Include: projects, artifacts, artifact_metadata, marketplace, cache_metadata tables
  Add indexes for: project_id, type, is_outdated, updated_at
  Reason: Foundational database design for entire cache system")

Task("python-backend-engineer", "CACHE-1.2: Create Alembic migrations for cache schema.
  Location: skillmeat/cache/migrations/versions/001_initial_schema.py
  Requirements: Idempotent, supports rollback, tested on fresh DB
  Reason: Enable reproducible schema changes and version control")

Task("python-backend-engineer", "CACHE-1.3: Implement SQLAlchemy ORM models.
  Location: skillmeat/cache/models.py
  Models needed: Project, Artifact, ArtifactMetadata, MarketplaceEntry, CacheMetadata
  Relationships: Project.artifacts, Artifact.metadata
  Reason: Type-safe database access layer")
```

**Phase 1 Sequential (after batch):**

```
Task("python-backend-engineer", "CACHE-1.4: Implement CacheRepository data access layer.
  Location: skillmeat/cache/repository.py
  CRUD operations for: projects, artifacts, metadata, marketplace
  Query methods: get_stale_projects, list_outdated_artifacts, search_artifacts
  Reason: Abstract database operations from business logic")

Task("python-backend-engineer", "CACHE-1.5: Write unit tests for CacheRepository.
  Location: tests/test_cache_repository.py
  Coverage: >80% of repository.py
  Test scenarios: CRUD, batch ops, queries, error handling, transactions
  Reason: Ensure data layer reliability and correctness")
```

**Phase 2 Batch (Parallel):**

```
Task("python-backend-engineer", "CACHE-2.1: Implement CacheManager service layer.
  Location: skillmeat/cache/manager.py
  Core methods: populate_cache, load_projects, load_artifacts, invalidate_cache, refresh_if_stale
  Concurrency: Read/write locks for thread safety
  Logging: Hit/miss rates, query times, errors
  Reason: High-level cache operations and lifecycle management")

Task("python-backend-engineer", "CACHE-2.3: Implement FileWatcher for change detection.
  Location: skillmeat/cache/watcher.py
  Library: watchdog for cross-platform file monitoring
  Watching: ~/.skillmeat/ and ./.claude/ directories
  Debouncing: 100ms to avoid cascading refreshes
  Reason: Detect filesystem changes and trigger cache invalidation")
```

**Phase 2 Sequential (after batch):**

```
Task("python-backend-engineer", "CACHE-2.2: Implement RefreshJob background worker.
  Location: skillmeat/cache/refresh.py
  Scheduler: APScheduler or FastAPI BackgroundTasks
  Frequency: Every 6 hours by default (configurable)
  Events: Emit refresh_started, refresh_completed, refresh_error
  Reason: Keep cache fresh without blocking user operations")

Task("python-backend-engineer", "CACHE-2.4: Add API endpoints for cache management.
  Location: skillmeat/api/routers/cache.py
  Endpoints: POST /cache/refresh, GET /cache/status, GET /cache/projects, POST /cache/invalidate
  Modify: skillmeat/api/routers/projects.py to use cache fallback
  Reason: Expose cache operations via REST API for web app and external tools")

Task("python-backend-engineer", "CACHE-2.5: Write integration tests for cache system.
  Location: tests/integration/test_cache_integration.py
  Test scenarios: Cache population, TTL refresh, file watcher, concurrent access, recovery
  Reason: Verify end-to-end cache workflows and error handling")
```

---

## Task Summary - Phases 1-2

| Phase | Task ID | Task Title | Effort | Duration | Assigned To |
|-------|---------|-----------|--------|----------|------------|
| 1 | CACHE-1.1 | Design SQLite Schema | 5 pts | 2d | data-layer-expert |
| 1 | CACHE-1.2 | Create Alembic Migrations | 3 pts | 1d | python-backend-engineer |
| 1 | CACHE-1.3 | Implement SQLAlchemy Models | 5 pts | 2d | python-backend-engineer |
| 1 | CACHE-1.4 | Implement CacheRepository | 5 pts | 2d | python-backend-engineer |
| 1 | CACHE-1.5 | Unit Tests for DB Layer | 3 pts | 1.5d | python-backend-engineer |
| 2 | CACHE-2.1 | Implement CacheManager | 8 pts | 3d | python-backend-engineer |
| 2 | CACHE-2.2 | Implement RefreshJob | 8 pts | 3d | python-backend-engineer |
| 2 | CACHE-2.3 | Implement FileWatcher | 8 pts | 3d | python-backend-engineer |
| 2 | CACHE-2.4 | API Endpoints for Cache | 5 pts | 2d | python-backend-engineer |
| 2 | CACHE-2.5 | Integration Tests | 5 pts | 2d | python-backend-engineer |

**Phases 1-2 Total: 49 Story Points**

---

*[Back to Parent Plan](../persistent-project-cache-v1.md)*
