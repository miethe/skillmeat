---
title: "Implementation Plan: Persistent Project Cache"
description: "Detailed task breakdown for implementing a persistent SQLite cache system for project metadata with background refresh and file watching"
audience: [ai-agents, developers]
tags: [implementation-plan, cache, database, background-jobs, performance, cli, web-ui]
created: 2025-11-30
updated: 2025-11-30
category: "implementation"
status: active
prd_reference: /docs/project_plans/PRDs/enhancements/persistent-project-cache-v1.md
related:
  - /docs/project_plans/PRDs/features/entity-lifecycle-management-v1.md
  - /docs/project_plans/PRDs/enhancements/web-ui-consolidation-v1.md
---

# Implementation Plan: Persistent Project Cache

**Feature Name:** Persistent Project Cache
**Complexity Level:** Large (L)
**Estimated Total Effort:** 88 Story Points
**Estimated Timeline:** 6 weeks (6 phases)
**Track:** Full Track (Architecture validation + Opus review)

---

## Executive Summary

This implementation plan breaks down the Persistent Project Cache feature into 6 sequential phases with 25 atomic tasks. The feature eliminates slow web app load times by maintaining a SQLite-backed cache of project metadata, updated intelligently through background jobs and file watching. Implementation follows the MeatyPrompts layered architecture: Database → Repository → Service → API → UI → Testing → Documentation → Deployment.

**Key Outcomes:**
- Web app loads cached data in <100ms (vs 60-90s fresh fetch)
- Background refresh keeps data fresh without UI blocking
- CLI and web app share single cache source of truth
- Cross-platform file watching triggers cache invalidation
- Complete test coverage with performance benchmarks

---

## Architecture Overview

### Layered Architecture (MeatyPrompts Pattern)

```
┌─────────────────────────────────────────┐
│         CLI / Web UI Layer              │ Phase 4-5
├─────────────────────────────────────────┤
│    API Router / HTTP Endpoints          │ Phase 2
├─────────────────────────────────────────┤
│  Service Layer (CacheManager, RefreshJob) │ Phase 1-2
├─────────────────────────────────────────┤
│ Repository Layer (CacheRepository)      │ Phase 1
├─────────────────────────────────────────┤
│    Database Layer (SQLAlchemy ORM)      │ Phase 1
├─────────────────────────────────────────┤
│   SQLite Database (cache.db)            │ Phase 1
└─────────────────────────────────────────┘
```

### File Structure

```
skillmeat/
├── cache/
│   ├── __init__.py
│   ├── manager.py              # CacheManager (service layer)
│   ├── repository.py           # CacheRepository (data access)
│   ├── models.py               # SQLAlchemy models
│   ├── schema.py               # Database schema definition
│   ├── refresh.py              # RefreshJob (background worker)
│   ├── watcher.py              # FileWatcher (change detection)
│   └── migrations/             # Alembic migrations
│       └── versions/
├── api/
│   └── routers/
│       ├── cache.py            # Cache endpoints (new)
│       └── projects.py         # Projects router (enhanced)
├── cli/
│   └── commands/
│       ├── cache.py            # Cache management commands (new)
│       └── list.py             # List command (enhanced)
└── tests/
    ├── test_cache_manager.py
    ├── test_cache_repository.py
    ├── test_refresh_job.py
    ├── test_file_watcher.py
    └── integration/
        └── test_cache_integration.py
```

---

## Detailed Task Breakdown

### Phase 1: Cache Infrastructure (Database & ORM)

**Duration:** 1 week | **Story Points:** 21 | **Assigned:** data-layer-expert, python-backend-engineer

#### Task 1.1: Design & Create SQLite Schema

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

#### Task 1.2: Create Alembic Migrations

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

#### Task 1.3: Create SQLAlchemy Models (ORM Layer)

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

#### Task 1.4: Implement CacheRepository (Data Access Layer)

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

#### Task 1.5: Unit Tests for Database Layer

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

### Phase 2: Cache Service Layer & Background Refresh

**Duration:** 1.5 weeks | **Story Points:** 28 | **Assigned:** python-backend-engineer, backend-architect

#### Task 2.1: Implement CacheManager (Service Layer)

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
    def write_lock(self)
```

---

#### Task 2.2: Implement RefreshJob (Background Worker)

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

#### Task 2.3: Implement FileWatcher (Change Detection)

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

#### Task 2.4: API Endpoints for Cache Management

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

#### Task 2.5: Integration Tests for Cache & Refresh

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

### Phase 3: Web UI Integration

**Duration:** 1 week | **Story Points:** 20 | **Assigned:** ui-engineer-enhanced, frontend-developer

#### Task 3.1: Modify Projects Endpoint for Cache Loading

**Task ID:** CACHE-3.1
**Assigned To:** python-backend-engineer
**Story Points:** 3
**Dependencies:** CACHE-2.1
**Duration:** 1 day

**Description:**
Modify existing /api/v1/projects endpoint to return cached data instead of always fetching fresh. Implement smart fallback to API fetch if cache empty.

**Acceptance Criteria:**
- [ ] Endpoint returns cached projects if available
- [ ] Cache is checked first before API fetch
- [ ] If cache empty, fetches from API and populates cache
- [ ] Response includes cache freshness indicator (last_fetched timestamp)
- [ ] Proper response time (verify <100ms from cache)
- [ ] No breaking changes to response schema
- [ ] Backward compatible with existing clients

**Implementation Notes:**
- Add optional query param: ?force_refresh=true to bypass cache
- Include X-Cache-Hit header in response (hit/miss)
- Log cache performance metrics
- Handle cache corruption gracefully

**Files to Modify:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/projects.py`

---

#### Task 3.2: Create React Hooks for Cache Loading

**Task ID:** CACHE-3.2
**Assigned To:** frontend-developer
**Story Points:** 5
**Dependencies:** CACHE-3.1
**Duration:** 2 days

**Description:**
Create React hooks (useProjectCache, useCacheStatus) for efficient cache loading in web app. Integrate with React Query for revalidation.

**Acceptance Criteria:**
- [ ] useProjectCache hook: loads projects from cache, handles loading/error states
- [ ] useCacheStatus hook: returns cache age, hit rate, freshness
- [ ] Integration with React Query's useQuery
- [ ] Proper TypeScript types
- [ ] Error boundaries and fallback UI
- [ ] Re-validate on focus (React Query behavior)
- [ ] Manual refresh method available
- [ ] Comprehensive JSDoc comments

**Implementation Notes:**
- Use React Query's staleTime and cacheTime options
- Support automatic refetch on mount
- Implement retry logic with exponential backoff
- Cache query results in browser localStorage as secondary fallback

**Files to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/useProjectCache.ts`
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/useCacheStatus.ts`

**Hook Signatures:**
```typescript
function useProjectCache(options?: UseProjectCacheOptions) {
  return { projects, isLoading, error, refetch }
}

function useCacheStatus() {
  return { lastRefetch, cacheAge, hitRate, isStale }
}
```

---

#### Task 3.3: Create Projects Page Component (Cache-enabled)

**Task ID:** CACHE-3.3
**Assigned To:** ui-engineer-enhanced
**Story Points:** 5
**Dependencies:** CACHE-3.2
**Duration:** 2 days

**Description:**
Create or modify Projects page component to load from cache. Implement progressive rendering, loading states, and cache freshness indicators.

**Acceptance Criteria:**
- [ ] Page loads from cache on mount (<100ms)
- [ ] Loading spinner shows while fetching background data
- [ ] Cache freshness badge shows ("Updated 5 min ago")
- [ ] Manual refresh button visible and functional
- [ ] Projects list renders progressively as data loads
- [ ] Error state handled (show fallback UI)
- [ ] Responsive design (mobile/desktop)
- [ ] Accessibility compliant (WCAG 2.1 AA)
- [ ] Proper TypeScript types

**Implementation Notes:**
- Use shadcn/ui Badge for freshness indicator
- Skeleton loaders for progressive rendering
- Toast notifications for refresh completion
- Keyboard shortcuts for manual refresh (Cmd+R or Ctrl+R)

**Files to Create/Modify:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/projects/page.tsx` (modify)
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/ProjectsList.tsx` (new)
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/CacheFreshnessIndicator.tsx` (new)

---

#### Task 3.4: Add Manual Refresh Button & Progress Feedback

**Task ID:** CACHE-3.4
**Assigned To:** ui-engineer-enhanced
**Story Points:** 3
**Dependencies:** CACHE-3.3
**Duration:** 1 day

**Description:**
Add manual refresh button with visual feedback (spinner, toast notifications) during cache refresh process.

**Acceptance Criteria:**
- [ ] Refresh button visible in projects toolbar
- [ ] Button shows spinner while refresh in progress
- [ ] Toast notification shows "Syncing projects..."
- [ ] Toast shows completion "Projects updated"
- [ ] Toast shows error if refresh fails
- [ ] Button disabled during refresh
- [ ] Keyboard shortcut support (Cmd/Ctrl + Shift + R)
- [ ] Proper error handling

**Implementation Notes:**
- Use shadcn/ui Button with loading state
- Use react-hot-toast or similar for toast notifications
- Disable button during refresh
- Show error toast on failure with retry option

**Files to Create/Modify:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/ProjectsToolbar.tsx` (new)
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/useCacheRefresh.ts` (new)

---

#### Task 3.5: Web UI Component Tests

**Task ID:** CACHE-3.5
**Assigned To:** frontend-developer
**Story Points:** 4
**Dependencies:** CACHE-3.4
**Duration:** 1.5 days

**Description:**
Write unit tests for React components and hooks (useProjectCache, ProjectsList, CacheFreshnessIndicator, ProjectsToolbar).

**Acceptance Criteria:**
- [ ] Tests for useProjectCache hook (loading, error, success)
- [ ] Tests for ProjectsList component rendering
- [ ] Tests for CacheFreshnessIndicator badge
- [ ] Tests for refresh button functionality
- [ ] Tests for toast notifications
- [ ] >80% coverage for component code
- [ ] Mocked API calls
- [ ] Snapshot tests for UI consistency
- [ ] Accessibility tests

**Implementation Notes:**
- Use testing-library for component testing
- Use jest.mock for API mocking
- Use userEvent for interaction testing
- Test accessibility with jest-axe

**Files to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/__tests__/useProjectCache.test.ts`
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/__tests__/ProjectsList.test.tsx`
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/__tests__/CacheFreshnessIndicator.test.tsx`

---

### Phase 4: CLI Integration

**Duration:** 1 week | **Story Points:** 16 | **Assigned:** python-backend-engineer

#### Task 4.1: Enhance CLI List Command for Cache

**Task ID:** CACHE-4.1
**Assigned To:** python-backend-engineer
**Story Points:** 3
**Dependencies:** CACHE-2.1
**Duration:** 1 day

**Description:**
Modify CLI `skillmeat list` command to use cache instead of filesystem scan. Implement fallback to files if cache unavailable.

**Acceptance Criteria:**
- [ ] `skillmeat list` reads from cache (much faster than filesystem scan)
- [ ] Fallback to filesystem reading if cache empty
- [ ] Output unchanged from existing behavior (backward compatible)
- [ ] `--no-cache` flag to force fresh read from files
- [ ] Performance improvement measurable (2x+ faster)
- [ ] Proper error handling

**Implementation Notes:**
- Cache hit should take <100ms
- Keep filesystem fallback as safety mechanism
- Add --cache-status flag to show cache freshness
- Update progress bar if cache is being populated in background

**Files to Modify:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cli/commands/list.py`

---

#### Task 4.2: Implement CLI Cache Management Commands

**Task ID:** CACHE-4.2
**Assigned To:** python-backend-engineer
**Story Points:** 5
**Dependencies:** CACHE-2.1, CACHE-2.2
**Duration:** 2 days

**Description:**
Create new cache management commands: cache status, cache clear, cache refresh, cache config.

**Acceptance Criteria:**
- [ ] `skillmeat cache status` - Shows cache age, size, hit rate, stale entries
- [ ] `skillmeat cache clear` - Clears cache database completely
- [ ] `skillmeat cache refresh` - Triggers manual refresh of all projects
- [ ] `skillmeat cache refresh <project>` - Refresh specific project
- [ ] `skillmeat cache config get cache-ttl` - Get TTL configuration
- [ ] `skillmeat cache config set cache-ttl 360` - Set TTL (in minutes)
- [ ] All commands provide clear feedback
- [ ] Proper error messages
- [ ] Help text for each command

**Implementation Notes:**
- Use Click command groups for subcommands
- Pretty print status output (table format)
- Show progress bar for refresh operations
- Confirm before clearing cache (prompt user)

**Files to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cli/commands/cache.py`

**Commands:**
```bash
skillmeat cache status
skillmeat cache clear
skillmeat cache refresh
skillmeat cache refresh <project-id>
skillmeat cache config get cache-ttl
skillmeat cache config set cache-ttl 360
```

---

#### Task 4.3: Integrate Cache Invalidation on CLI Write

**Task ID:** CACHE-4.3
**Assigned To:** python-backend-engineer
**Story Points:** 3
**Dependencies:** CACHE-2.1, CACHE-2.3
**Duration:** 1 day

**Description:**
Ensure CLI write operations (add, deploy, remove) invalidate cache and trigger refresh. Maintain consistency between CLI and web app.

**Acceptance Criteria:**
- [ ] `skillmeat add` invalidates cache after success
- [ ] `skillmeat deploy` invalidates cache after success
- [ ] `skillmeat remove` invalidates cache after success
- [ ] Cache refresh triggered automatically after invalidation
- [ ] User sees feedback about cache update
- [ ] No breaking changes to existing commands
- [ ] Proper error handling

**Implementation Notes:**
- Hook into existing add/deploy/remove commands
- Call cache_manager.invalidate_cache() on success
- Trigger background refresh through RefreshJob
- Show progress indication to user

**Files to Modify:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cli/commands/add.py`
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cli/commands/deploy.py`
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cli/commands/remove.py`

---

#### Task 4.4: CLI Tests and Documentation

**Task ID:** CACHE-4.4
**Assigned To:** python-backend-engineer
**Story Points:** 5
**Dependencies:** CACHE-4.3
**Duration:** 2 days

**Description:**
Write tests for CLI cache commands and document cache configuration/usage.

**Acceptance Criteria:**
- [ ] Tests for `skillmeat cache status` command
- [ ] Tests for `skillmeat cache clear` command
- [ ] Tests for `skillmeat cache refresh` command
- [ ] Tests for cache invalidation on add/deploy/remove
- [ ] >80% coverage for cache CLI module
- [ ] Help text documentation in code
- [ ] User-facing CLI help is clear and complete
- [ ] Integration tests with real cache operations

**Implementation Notes:**
- Use CliRunner from Click for testing
- Mock cache_manager in unit tests
- Use temporary databases for integration tests
- Verify output formatting

**Files to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/tests/cli/test_cache_commands.py`

---

### Phase 5: Advanced Features

**Duration:** 1.5 weeks | **Story Points:** 18 | **Assigned:** python-backend-engineer, ui-engineer-enhanced

#### Task 5.1: Implement Marketplace Metadata Caching

**Task ID:** CACHE-5.1
**Assigned To:** python-backend-engineer
**Story Points:** 5
**Dependencies:** CACHE-2.1
**Duration:** 2 days

**Description:**
Add caching for marketplace metadata (remote artifact collections, update sources). Allows browsing marketplace without network latency.

**Acceptance Criteria:**
- [ ] Marketplace entries cached in marketplace table
- [ ] TTL-based refresh for marketplace cache (configurable)
- [ ] CacheManager.get_marketplace_entries() method
- [ ] CacheManager.update_marketplace_cache() method
- [ ] API endpoint: GET /api/v1/cache/marketplace
- [ ] Fallback to network if cache stale
- [ ] Version comparison with upstream
- [ ] No breaking changes to marketplace browsing

**Implementation Notes:**
- Reuse existing marketplace data fetch logic
- Store raw JSON response for flexibility
- Implement marketplace refresh job alongside project refresh
- Support selective marketplace updates

**Files to Modify:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/manager.py` (add marketplace methods)
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/refresh.py` (add marketplace refresh)
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/cache.py` (add marketplace endpoint)

---

#### Task 5.2: Track Upstream Versions for Update Detection

**Task ID:** CACHE-5.2
**Assigned To:** python-backend-engineer
**Story Points:** 5
**Dependencies:** CACHE-2.1, CACHE-2.2
**Duration:** 2 days

**Description:**
Track upstream artifact versions during refresh and flag outdated artifacts. Enable update indicators in UI.

**Acceptance Criteria:**
- [ ] Upstream version fetched during refresh for each artifact
- [ ] Version comparison logic: deployed vs upstream
- [ ] is_outdated flag set correctly for each artifact
- [ ] CacheManager.get_outdated_artifacts() returns stale artifacts
- [ ] API endpoint: GET /api/v1/cache/stale-artifacts with sorting/filtering
- [ ] Version comparison handles pre-release versions
- [ ] Proper error handling for version fetch failures
- [ ] Performance benchmarked (no N+1 queries)

**Implementation Notes:**
- Reuse existing version comparison logic if available
- Handle cases where upstream version unavailable
- Log version mismatches for observability
- Cache version info along with metadata

**Files to Modify:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/manager.py` (add update detection)
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/refresh.py` (fetch upstream versions)
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/cache.py` (add stale-artifacts endpoint)

---

#### Task 5.3: Add UI Indicators for Outdated Artifacts

**Task ID:** CACHE-5.3
**Assigned To:** ui-engineer-enhanced
**Story Points:** 5
**Dependencies:** CACHE-5.2
**Duration:** 2 days

**Description:**
Add visual indicators in web UI for outdated artifacts. Show version comparison and update suggestions.

**Acceptance Criteria:**
- [ ] Badge component shows "Update available" on artifact cards
- [ ] Badge clickable, shows version comparison modal
- [ ] Modal shows deployed vs upstream versions
- [ ] Modal suggests update action
- [ ] Outdated artifacts filterable in projects list
- [ ] Sorting by update status available
- [ ] Proper visual styling (warning colors)
- [ ] Accessible tooltips and aria labels
- [ ] Responsive design

**Implementation Notes:**
- Use shadcn/ui Badge with warning variant
- Create UpdateAvailableModal component
- Integrate with useProjectCache hook for data
- Show count of outdated artifacts in toolbar

**Files to Create/Modify:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/OutdatedBadge.tsx` (new)
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/UpdateAvailableModal.tsx` (new)
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/projects/page.tsx` (modify)

---

#### Task 5.4: Optimize Search with Cache Queries

**Task ID:** CACHE-5.4
**Assigned To:** python-backend-engineer
**Story Points:** 3
**Dependencies:** CACHE-2.1
**Duration:** 1 day

**Description:**
Implement efficient search queries against cache. Add full-text search support if needed. Benchmark search performance.

**Acceptance Criteria:**
- [ ] CacheManager.search_artifacts(query, filters) method
- [ ] Search by name, type, tags, source
- [ ] Filtering by project, type, status
- [ ] Full-text search on metadata (if needed)
- [ ] Search latency <100ms for typical queries
- [ ] Pagination support (offset/limit)
- [ ] Sorted results (relevance, name, date)
- [ ] Performance benchmarked against old search

**Implementation Notes:**
- Use SQLAlchemy query builder for flexibility
- Add proper indexes for search performance
- Support fuzzy matching for forgiving search
- Cache common searches in memory

**Files to Modify:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/manager.py` (add search methods)
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/cache.py` (add search endpoint)

---

### Phase 6: Testing, Documentation & Polish

**Duration:** 1 week | **Story Points:** 17 | **Assigned:** python-backend-engineer, documentation-writer

#### Task 6.1: Performance Benchmarking & Optimization

**Task ID:** CACHE-6.1
**Assigned To:** python-backend-engineer
**Story Points:** 5
**Dependencies:** All phases
**Duration:** 2 days

**Description:**
Benchmark cache performance against success criteria. Optimize queries and indexes based on results.

**Acceptance Criteria:**
- [ ] Cache read latency: <10ms (measure with perf tests)
- [ ] Cache write latency: <50ms
- [ ] Web app startup with warm cache: <500ms total (including network)
- [ ] Search query latency: <100ms for typical queries
- [ ] Background refresh CPU: <5% (measure with system profiler)
- [ ] Cache database file: <10MB for 100 projects
- [ ] All benchmarks documented in report
- [ ] Optimization recommendations if targets not met

**Implementation Notes:**
- Create benchmark script that tests all operations
- Use Python timeit for micro-benchmarks
- Use pytest-benchmark for automated benchmarking
- Profile database queries with EXPLAIN
- Add query indexes if needed

**Files to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/tests/benchmarks/test_cache_performance.py`
- `/Users/miethe/dev/homelab/development/skillmeat/docs/performance_report.md` (generated)

---

#### Task 6.2: Concurrent Access & Load Testing

**Task ID:** CACHE-6.2
**Assigned To:** python-backend-engineer
**Story Points:** 4
**Dependencies:** All phases
**Duration:** 1.5 days

**Description:**
Test concurrent access scenarios (CLI + web simultaneously). Verify no deadlocks or data corruption. Load test with many projects.

**Acceptance Criteria:**
- [ ] Concurrent read/write tests pass (no deadlocks)
- [ ] Load test with 100 projects, 10k artifacts
- [ ] Simultaneous CLI list + web refresh don't conflict
- [ ] Transaction isolation verified
- [ ] Database integrity maintained
- [ ] No data corruption under concurrent load
- [ ] Clear test report with recommendations
- [ ] All edge cases documented

**Implementation Notes:**
- Use pytest-xdist for parallel test execution
- Use threading for concurrent access simulation
- Use locust or similar for load testing
- Monitor database locks during tests

**Files to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/tests/test_concurrent_access.py`
- `/Users/miethe/dev/homelab/development/skillmeat/tests/load/locustfile.py`

---

#### Task 6.3: Cache Recovery & Error Scenarios

**Task ID:** CACHE-6.3
**Assigned To:** python-backend-engineer
**Story Points:** 3
**Dependencies:** CACHE-2.1
**Duration:** 1 day

**Description:**
Test cache corruption recovery, disk full scenarios, permission errors. Ensure graceful degradation.

**Acceptance Criteria:**
- [ ] Corrupted database detected and rebuilt on startup
- [ ] Permission errors handled gracefully (fallback to memory cache)
- [ ] Disk full handled gracefully (pause refresh, warn user)
- [ ] Stale data used if refresh fails (better than blank)
- [ ] Clear error messages for troubleshooting
- [ ] Recovery tested end-to-end
- [ ] All scenarios documented

**Implementation Notes:**
- Use temporary files to simulate corruption
- Mock file system errors
- Test fallback paths thoroughly
- Add recovery logging

**Files to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/tests/test_cache_recovery.py`

---

#### Task 6.4: Configuration Guide & API Documentation

**Task ID:** CACHE-6.4
**Assigned To:** documentation-writer
**Story Points:** 3
**Dependencies:** All phases
**Duration:** 1.5 days

**Description:**
Write comprehensive documentation for cache feature: configuration guide, API reference, troubleshooting, architecture decisions.

**Acceptance Criteria:**
- [ ] Configuration guide: TTL, cache path, cleanup retention
- [ ] CLI commands reference: cache status, refresh, clear, config
- [ ] API endpoints reference: all cache endpoints with examples
- [ ] Architecture Decision Record (ADR) explaining design choices
- [ ] Troubleshooting guide: common issues and solutions
- [ ] Examples: using cache from Python code, API calls
- [ ] Performance tuning guide
- [ ] All docs searchable and properly indexed

**Implementation Notes:**
- Use frontmatter for proper documentation
- Include code examples
- Include diagrams for architecture
- Link to related docs

**Files to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/docs/cache/configuration-guide.md`
- `/Users/miethe/dev/homelab/development/skillmeat/docs/cache/api-reference.md`
- `/Users/miethe/dev/homelab/development/skillmeat/docs/cache/troubleshooting-guide.md`
- `/Users/miethe/dev/homelab/development/skillmeat/docs/cache/architecture-decision-record.md`

---

#### Task 6.5: End-to-End Integration Tests

**Task ID:** CACHE-6.5
**Assigned To:** python-backend-engineer
**Story Points:** 2
**Dependencies:** All phases
**Duration:** 1 day

**Description:**
Write E2E tests simulating real user workflows: app startup, manual refresh, CLI operations, file changes.

**Acceptance Criteria:**
- [ ] E2E test: fresh app startup → cache populated → fast reload
- [ ] E2E test: manual refresh → cache updated → UI refreshed
- [ ] E2E test: CLI add artifact → cache invalidated → web reflects change
- [ ] E2E test: file change → file watcher triggers → cache updated
- [ ] All tests pass consistently
- [ ] No flaky tests
- [ ] Clear test documentation

**Implementation Notes:**
- Use real FastAPI test client
- Use temp databases for isolation
- Simulate file system changes
- Mock external APIs appropriately

**Files to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/tests/e2e/test_cache_workflow.py`

---

#### Task 6.6: Final Review & Release Preparation

**Task ID:** CACHE-6.6
**Assigned To:** python-backend-engineer, backend-architect
**Story Points:** 2
**Dependencies:** All tasks
**Duration:** 1 day

**Description:**
Final code review, quality checks, feature flag configuration, release notes preparation.

**Acceptance Criteria:**
- [ ] All tests passing (>95% overall coverage target)
- [ ] Code reviewed by 2+ engineers
- [ ] Linting passes (black, flake8, mypy)
- [ ] No critical security issues
- [ ] Feature flags configured correctly
- [ ] Release notes written
- [ ] Known limitations documented
- [ ] Ready for production deployment

**Implementation Notes:**
- Configure FEATURE_CACHE_ENABLED flag
- Set up monitoring/alerting for cache health
- Document rollback procedure
- Prepare migration guide if needed

**Files to Create/Modify:**
- Release notes (part of commit/tag)
- Feature flags configuration

---

## Orchestration Quick Reference

### Phase Execution Guide

**Phase 1 Parallelization:**
- CACHE-1.1 (Schema design) → CACHE-1.2 (Migrations) & CACHE-1.3 (Models)
- CACHE-1.4 (Repository) depends on CACHE-1.3
- CACHE-1.5 (Tests) depends on CACHE-1.4

**Phase 2 Parallelization:**
- CACHE-2.1 (CacheManager) in parallel with CACHE-2.3 (FileWatcher)
- CACHE-2.2 (RefreshJob) depends on CACHE-2.1
- CACHE-2.4 (API) depends on CACHE-2.1, CACHE-2.2
- CACHE-2.5 (Tests) depends on CACHE-2.4

**Phase 3 Parallelization:**
- CACHE-3.1 (Endpoint) → CACHE-3.2 (Hooks) → CACHE-3.3 (Component)
- CACHE-3.4 (Refresh Button) depends on CACHE-3.3
- CACHE-3.5 (Tests) depends on CACHE-3.4

**Phase 4 Sequential:**
- CACHE-4.1 → CACHE-4.2 → CACHE-4.3 → CACHE-4.4

**Phase 5 Parallelization:**
- CACHE-5.1 (Marketplace) and CACHE-5.2 (Versions) in parallel
- CACHE-5.3 (UI) depends on CACHE-5.2
- CACHE-5.4 (Search) independent

**Phase 6 Sequential:**
- CACHE-6.1, CACHE-6.2, CACHE-6.3 in parallel
- CACHE-6.4 (Docs) independent
- CACHE-6.5 (E2E Tests) depends on all phases
- CACHE-6.6 (Review) depends on all tasks

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

**Phase 3 Sequential:**

```
Task("python-backend-engineer", "CACHE-3.1: Modify projects API endpoint for cache loading.
  File: skillmeat/api/routers/projects.py
  Changes: Load from cache first, fallback to API, include freshness indicator
  Add: Optional ?force_refresh=true query param
  Reason: Enable fast cached loads for projects endpoint")

Task("frontend-developer", "CACHE-3.2: Create React hooks for cache loading.
  Location: skillmeat/web/hooks/useProjectCache.ts and useCacheStatus.ts
  Framework: React Query (useQuery)
  Features: Auto-refetch, error handling, manual refresh
  Reason: Efficient client-side cache integration with React")

Task("ui-engineer-enhanced", "CACHE-3.3: Create Projects page component with cache support.
  Location: skillmeat/web/app/projects/page.tsx and skillmeat/web/components/ProjectsList.tsx
  Features: Load from cache, skeleton loaders, freshness badge
  Design: Responsive, accessible (WCAG 2.1 AA)
  Reason: User-facing component for cached project browsing")

Task("ui-engineer-enhanced", "CACHE-3.4: Add manual refresh button with progress feedback.
  New components: ProjectsToolbar.tsx
  New hooks: useCacheRefresh.ts
  Features: Spinner, toast notifications, keyboard shortcut (Cmd/Ctrl+Shift+R)
  Reason: Allow users to manually trigger cache refresh")

Task("frontend-developer", "CACHE-3.5: Write unit tests for React components and hooks.
  Location: skillmeat/web/__tests__/useProjectCache.test.ts, ProjectsList.test.tsx, etc.
  Coverage: >80% for component code
  Tools: testing-library, jest.mock, jest-axe
  Reason: Ensure component reliability and accessibility")
```

**Phase 4 Sequential:**

```
Task("python-backend-engineer", "CACHE-4.1: Enhance CLI list command to use cache.
  File: skillmeat/cli/commands/list.py
  Changes: Read from cache first, fallback to filesystem, add --no-cache flag
  Performance: Target 2x+ speedup
  Reason: Improve CLI performance for frequent list operations")

Task("python-backend-engineer", "CACHE-4.2: Implement CLI cache management commands.
  Location: skillmeat/cli/commands/cache.py
  Commands: cache status, cache clear, cache refresh, cache config
  Output: Pretty-printed status, progress bars, user prompts
  Reason: Enable CLI users to manage cache directly")

Task("python-backend-engineer", "CACHE-4.3: Integrate cache invalidation on CLI write operations.
  Files: skillmeat/cli/commands/add.py, deploy.py, remove.py
  Changes: Invalidate cache after successful add/deploy/remove
  Trigger: Background refresh after invalidation
  Reason: Keep cache consistent with CLI operations")

Task("python-backend-engineer", "CACHE-4.4: Write CLI tests and documentation.
  Location: tests/cli/test_cache_commands.py
  Coverage: >80% for cache CLI module
  Documentation: Help text, user-facing guides
  Reason: Ensure CLI reliability and usability")
```

**Phase 5 Parallel:**

```
Task("python-backend-engineer", "CACHE-5.1: Implement marketplace metadata caching.
  Location: skillmeat/cache/manager.py (add methods), refresh.py (marketplace refresh)
  Endpoints: GET /api/v1/cache/marketplace
  Features: TTL-based refresh, version comparison, fallback to network
  Reason: Accelerate marketplace browsing without network latency")

Task("python-backend-engineer", "CACHE-5.2: Track upstream versions for update detection.
  Files: cache/manager.py, cache/refresh.py, api/routers/cache.py
  Features: Fetch upstream versions, compare deployed vs upstream, flag is_outdated
  Endpoint: GET /api/v1/cache/stale-artifacts
  Reason: Enable automated update detection and indicators")

Task("python-backend-engineer", "CACHE-5.4: Optimize search with cache queries.
  File: skillmeat/cache/manager.py (add search methods)
  Features: search_artifacts(query, filters), pagination, sorting, FTS
  Performance: Target <100ms for typical queries
  Reason: Accelerate artifact discovery")
```

**Phase 5 Sequential (after parallel):**

```
Task("ui-engineer-enhanced", "CACHE-5.3: Add UI indicators for outdated artifacts.
  New components: OutdatedBadge.tsx, UpdateAvailableModal.tsx
  Features: Badge on artifact cards, version comparison modal, sortable/filterable
  Design: Warning colors, accessible, responsive
  Reason: Notify users about available updates")
```

**Phase 6 Parallel:**

```
Task("python-backend-engineer", "CACHE-6.1: Performance benchmarking and optimization.
  Location: tests/benchmarks/test_cache_performance.py
  Targets: Read <10ms, write <50ms, startup <500ms, search <100ms, CPU <5%
  Tools: pytest-benchmark, timeit, EXPLAIN queries
  Reason: Validate performance targets met")

Task("python-backend-engineer", "CACHE-6.2: Concurrent access and load testing.
  Location: tests/test_concurrent_access.py, tests/load/locustfile.py
  Scenarios: CLI + web simultaneously, 100 projects/10k artifacts
  Verification: No deadlocks, data integrity, transaction isolation
  Reason: Ensure robustness under concurrent and heavy load")

Task("python-backend-engineer", "CACHE-6.3: Cache recovery and error scenario testing.
  Location: tests/test_cache_recovery.py
  Scenarios: Corruption, permission errors, disk full, stale data fallback
  Verification: Graceful degradation, clear error messages, recovery works
  Reason: Ensure production reliability")

Task("documentation-writer", "CACHE-6.4: Write configuration guide and API documentation.
  Location: docs/cache/*.md (configuration-guide, api-reference, troubleshooting, ADR)
  Content: CLI config, API endpoints, examples, architecture decisions, troubleshooting
  Reason: Enable users and developers to understand and use cache feature")
```

**Phase 6 Sequential (after parallel):**

```
Task("python-backend-engineer", "CACHE-6.5: Write E2E integration tests.
  Location: tests/e2e/test_cache_workflow.py
  Scenarios: Fresh startup, manual refresh, CLI operations, file changes
  Verification: All workflows work end-to-end consistently
  Reason: Validate complete user workflows")

Task("python-backend-engineer, backend-architect", "CACHE-6.6: Final review and release preparation.
  Activities: Code review, linting, test coverage verification, feature flag setup, release notes
  Criteria: >95% test coverage, no security issues, all PRD acceptance met
  Reason: Gate feature for production release")
```

---

## Task Summary Table

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
| 3 | CACHE-3.1 | Modify Projects Endpoint | 3 pts | 1d | python-backend-engineer |
| 3 | CACHE-3.2 | React Hooks for Cache | 5 pts | 2d | frontend-developer |
| 3 | CACHE-3.3 | Projects Page Component | 5 pts | 2d | ui-engineer-enhanced |
| 3 | CACHE-3.4 | Refresh Button & Feedback | 3 pts | 1d | ui-engineer-enhanced |
| 3 | CACHE-3.5 | Web UI Component Tests | 4 pts | 1.5d | frontend-developer |
| 4 | CACHE-4.1 | Enhance CLI List Command | 3 pts | 1d | python-backend-engineer |
| 4 | CACHE-4.2 | Cache Management Commands | 5 pts | 2d | python-backend-engineer |
| 4 | CACHE-4.3 | CLI Write Invalidation | 3 pts | 1d | python-backend-engineer |
| 4 | CACHE-4.4 | CLI Tests & Documentation | 5 pts | 2d | python-backend-engineer |
| 5 | CACHE-5.1 | Marketplace Metadata Cache | 5 pts | 2d | python-backend-engineer |
| 5 | CACHE-5.2 | Track Upstream Versions | 5 pts | 2d | python-backend-engineer |
| 5 | CACHE-5.3 | Outdated Artifact Indicators | 5 pts | 2d | ui-engineer-enhanced |
| 5 | CACHE-5.4 | Optimize Search with Cache | 3 pts | 1d | python-backend-engineer |
| 6 | CACHE-6.1 | Performance Benchmarking | 5 pts | 2d | python-backend-engineer |
| 6 | CACHE-6.2 | Concurrent Access Testing | 4 pts | 1.5d | python-backend-engineer |
| 6 | CACHE-6.3 | Recovery & Error Testing | 3 pts | 1d | python-backend-engineer |
| 6 | CACHE-6.4 | Docs & Configuration | 3 pts | 1.5d | documentation-writer |
| 6 | CACHE-6.5 | E2E Integration Tests | 2 pts | 1d | python-backend-engineer |
| 6 | CACHE-6.6 | Final Review & Release | 2 pts | 1d | python-backend-engineer, backend-architect |

**Total: 88 Story Points, 6 Weeks**

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| SQLite concurrency issues under load | Medium | Medium | Implement WAL mode, comprehensive locking tests, load testing |
| File watcher missing rapid changes | Low | Medium | Debounce events, periodic consistency checks, fallback TTL |
| Cache invalidation edge cases | Medium | Low | Thorough testing of all invalidation paths, clear logging |
| Migration issues on existing installations | Low | High | Comprehensive migration testing, rollback procedures, versioning |
| Performance regression from cache queries | Low | Medium | Benchmark all queries, profile indexes, optimize hot paths |
| Marketplace caching staleness | Low | Medium | Appropriate TTL, manual refresh option, clear freshness indicators |

---

## Dependencies & Prerequisites

**External Libraries (Already Available):**
- SQLAlchemy (ORM)
- FastAPI (API framework)
- React Query (client-side caching)
- watchdog (file system monitoring)

**To Install:**
- APScheduler (for background job scheduling)
- Alembic (for migrations, likely already available)

**Internal Dependencies:**
- Existing project API endpoints (Entity Lifecycle Management)
- Existing CLI command structure
- Existing React component library (shadcn/ui, Radix)

---

## Success Criteria

### Functional Completeness
- [ ] All 25 tasks completed and tested
- [ ] All acceptance criteria met
- [ ] PRD requirements fully implemented
- [ ] No critical regressions in existing functionality

### Quality Gates
- [ ] Test coverage >80% for critical paths
- [ ] All linting passes (black, flake8, mypy)
- [ ] Performance benchmarks met (load time, query speed, CPU)
- [ ] No security vulnerabilities (SCA passes)
- [ ] Concurrent access tested and verified

### User Experience
- [ ] Web app loads from cache in <100ms
- [ ] Background refresh non-blocking
- [ ] Clear UI indicators for cache status
- [ ] CLI commands intuitive and helpful
- [ ] Documentation complete and searchable

---

## Notes for Subagents

1. **Code Style**: Follow existing patterns in skillmeat codebase
2. **Error Handling**: All operations should fail gracefully with clear error messages
3. **Logging**: Use Python logging module, include context in all messages
4. **Type Safety**: Use type hints throughout (Python 3.9+ compatible)
5. **Testing**: Write tests alongside code, aim for >80% coverage
6. **Documentation**: Include docstrings, API docs, and user guides
7. **Performance**: Profile before optimizing, use pytest-benchmark for benchmarks
8. **Security**: Use parameterized queries, validate all inputs, no hardcoded secrets
9. **Backwards Compatibility**: Maintain API compatibility with existing clients
10. **Architecture**: Follow MeatyPrompts pattern strictly (DB → Repo → Service → API → UI)

---

*Generated for AI agent execution. Implementation estimated at 88 story points over 6 weeks using Full Track (Opus architecture validation included). Break into phase-based progress files for execution coordination.*
