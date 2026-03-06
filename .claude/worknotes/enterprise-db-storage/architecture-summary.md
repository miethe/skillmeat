# SkillMeat Storage & Repository Architecture Summary

**Date**: 2026-03-06
**Project**: SkillMeat v0.3.0-beta
**Scope**: Foundation for Enterprise DB Storage feature planning

---

## 1. Current Architecture Overview

SkillMeat uses a **dual-stack data model**:

1. **Filesystem (CLI source of truth)**
   - Location: `~/.skillmeat/collection/`
   - Format: TOML manifests, Markdown files, artifact directories
   - Primary users: CLI commands

2. **SQLite Cache (Web source of truth)**
   - Location: Database file (typically `~/.skillmeat/skillmeat.db`)
   - 177KB models file with 30+ SQLAlchemy ORM models
   - 65+ Alembic migrations (latest: `20260303_1100_add_workflow_to_artifact_type_check.py`)
   - Primary users: FastAPI web UI

**Write-Through Pattern**: All mutations write filesystem first, then sync DB via `refresh_single_artifact_cache()`.

---

## 2. Repository Architecture

### Current State: Partial Implementation

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/repositories.py` (274KB)

Implements **Repository pattern** for marketplace entities only:

#### Base Repository Class
```python
class BaseRepository[T]:
    """Generic CRUD with session management"""
    - _get_session(): SQLAlchemy Session
    - create(), read(), update(), delete()
    - Context managers for transactions
```

#### Implemented Repositories
1. **MarketplaceSourceRepository**
   - `get_by_repo_url(url: str) -> MarketplaceSource`
   - `list_all() -> List[MarketplaceSource]`
   - `bulk_create(sources: List) -> List[MarketplaceSource]`
   - Methods: create, update, delete, find by various filters

2. **MarketplaceCatalogRepository**
   - `list_by_source(source_id: str) -> List[MarketplaceCatalogEntry]`
   - `bulk_create(entries: List) -> MergeResult`
   - Merge operations with import/exclusion tracking

#### NOT Implemented (Core Gap)
- ❌ ArtifactRepository
- ❌ ProjectRepository
- ❌ CollectionRepository
- ❌ CollectionArtifactRepository
- ❌ DeploymentSetRepository
- ❌ TagRepository

---

### Secondary Repository Classes

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/repository.py` (42KB)

**CacheRepository** - Legacy pattern for Projects/Artifacts:
- Direct session management per operation
- Methods: `get_projects_by_status()`, `list_outdated_artifacts()`, `transaction()` context manager
- Custom exceptions: `CacheError`, `CacheNotFoundError`, `CacheConstraintError`

---

## 3. Database Schema (30+ Tables)

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/models.py` (177KB)

### Core Entity Tables

#### Projects Table (`projects`)
```
- id: VARCHAR (PRIMARY KEY)
- name: VARCHAR NOT NULL
- path: VARCHAR NOT NULL
- description: TEXT
- created_at: DATETIME NOT NULL
- updated_at: DATETIME NOT NULL
- last_fetched: DATETIME
- status: VARCHAR NOT NULL
- error_message: TEXT
```

#### Artifacts Table (`artifacts`)
```
- id: VARCHAR (PRIMARY KEY)
- uuid: VARCHAR NOT NULL (UNIQUE)
- project_id: VARCHAR FK(projects.id)
- name: VARCHAR NOT NULL
- type: VARCHAR NOT NULL
- source: VARCHAR
- deployed_version: VARCHAR
- upstream_version: VARCHAR
- is_outdated: BOOLEAN NOT NULL
- local_modified: BOOLEAN NOT NULL
- path_pattern: TEXT
- auto_load: BOOLEAN NOT NULL
- category: TEXT
- content_hash: TEXT
- content: TEXT
- core_content: TEXT
- description: TEXT
- target_platforms: JSON
- created_at: DATETIME NOT NULL
- updated_at: DATETIME NOT NULL
```

#### Collections Table (`collections`)
```
- id: VARCHAR (PRIMARY KEY)
- name: VARCHAR(255) NOT NULL
- description: TEXT
- created_by: VARCHAR
- collection_type: VARCHAR
- context_category: VARCHAR
- created_at: DATETIME NOT NULL
- updated_at: DATETIME NOT NULL
```

#### Collection_Artifacts Table (`collection_artifacts`)
```
- collection_id: VARCHAR FK(collections.id)
- artifact_uuid: VARCHAR FK(artifacts.uuid)
- added_at: DATETIME NOT NULL
- description: TEXT
- author: VARCHAR
- license: VARCHAR
- tags_json: TEXT
- tools_json: TEXT
- deployments_json: TEXT
- version: VARCHAR
- artifact_content_hash: VARCHAR(64)
- artifact_structure_hash: VARCHAR(64)
- artifact_file_count: INTEGER NOT NULL
- artifact_total_size: INTEGER NOT NULL
- source: VARCHAR
- origin: VARCHAR
- origin_source: VARCHAR
- resolved_sha: VARCHAR(64)
- resolved_version: VARCHAR
- synced_at: DATETIME
```

#### Marketplace Tables
- **marketplace_sources** (76 columns): GitHub repo sources, access tokens, trust levels, webhook support
- **marketplace_catalog_entries**: Detected artifacts from marketplace sources
- **marketplace_entries**: Cached marketplace artifact listings

#### Deployment Tables
- **deployment_sets**: Named, ordered sets of artifacts/groups for batch deployment
- **deployment_set_members**: Polymorphic member entries within deployment sets
- **deployment_profiles**: Reusable deployment profiles with target platforms

#### Extended Schema
- **artifact_tags**, **artifact_versions**: Versioning and tagging
- **tags**, **groups**, **group_artifacts**: Custom grouping
- **composite_artifacts**, **composite_memberships**: Multi-artifact bundles
- **project_templates**, **template_entities**: Reusable deployment templates
- **user_ratings**, **community_scores**: Rating/feedback system
- **similarity_cache**, **duplicate_pairs**: Similarity analysis
- **workflows**, **workflow_executions**, **workflow_steps**: Workflow orchestration
- **entity_type_configs**, **entity_categories**: Custom entity configuration
- **custom_colors**: User-defined hex colors
- **context_entities**, **context_modules**: Context packing for AI models

---

## 4. Deployment Engine

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/deployment.py` (600+ lines)

### Deployment Class
```python
@dataclass
class Deployment:
    # Core identification
    artifact_name: str
    artifact_type: str
    from_collection: str

    # Deployment metadata
    deployed_at: datetime
    artifact_path: Path  # Relative within profile root

    # Version tracking (ADR-004)
    content_hash: str  # SHA-256
    local_modifications: bool = False
    parent_hash: Optional[str]
    version_lineage: List[str]
    last_modified_check: Optional[datetime]
    modification_detected_at: Optional[datetime]
    merge_base_snapshot: Optional[str]  # For 3-way merges

    # Profile/platform context
    deployment_profile_id: Optional[str]
    platform: Optional[Platform]
    profile_root_dir: Optional[str]
```

### Deployment Manager (in storage/deployment.py)
- **Read**: `DeploymentTracker.read_deployments(project_path)` → List[Deployment]
- **Write**: `DeploymentTracker.write_deployments(project_path, deployments)`
- **Track**: Persists to `.skillmeat-deployed.toml` in project root
- **Hash computation**: SHA-256 content hashing for drift detection

**Key Methods**:
- `_count_files_recursive()`: Fast pre-check (inode scan, no content read)
- `compute_deployment_statuses_batch()`: Batch hash comparison
- Version lineage tracking with merge base snapshots

---

## 5. CLI Deploy/Sync Commands

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cli/__init__.py` (494KB)

### Entry Point
```python
skillmeat = "skillmeat.cli:main"  # From pyproject.toml
```

### Main CLI Structure
- **Collection management**: `init`, `add`, `list`, `search`, `sync`
- **Deployment**: `deploy`, `undeploy`
- **Web UI**: `web dev`, `web build`, `web start`
- **Configuration**: `config set github-token`, etc.

### Deploy Command Logic
1. Accepts artifact ID and project path
2. Resolves artifact from collection
3. Computes content hash (SHA-256)
4. Copies files to target deployment path
5. Records deployment metadata in `.skillmeat-deployed.toml`
6. Syncs to SQLite cache via `refresh_single_artifact_cache()`

### Sync Command Logic
1. Compares filesystem vs collection state
2. Detects new/updated/removed artifacts
3. Updates `.skillmeat-deployed.toml`
4. Triggers cache refresh
5. Supports dry-run and interactive modes

---

## 6. API Routers (FastAPI Layer)

**Location**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/`

### Core Artifact Router
**File**: `artifacts.py` (1000+ lines)

**Endpoints**:
- `POST /artifacts/discover` - Discover artifacts in project
- `POST /artifacts/discover-project` - Discover by project
- `POST /artifacts/bulk-import` - Bulk import artifacts
- `POST /artifacts/confirm-duplicates` - Handle detected duplicates
- `POST /artifacts/create` - Create new artifact
- `GET /artifacts` - List artifacts (with pagination, filtering)
- `GET /artifacts/{id}` - Get single artifact
- `GET /artifacts/{id}/check-upstream` - Check for upstream updates
- `PUT /artifacts/{id}` - Update artifact
- `DELETE /artifacts/{id}` - Delete artifact
- `GET /artifacts/{id}/similar` - Find similar artifacts

**Helper Functions**:
```python
def parse_artifact_id(artifact_id: str) -> tuple[str, str]
def resolve_project_path(project_id: str) -> PathLib
def artifact_to_response(artifact_obj, include_full_content=False) -> ArtifactResponse
async def build_deployment_statistics(artifact, project_path) -> DeploymentStats
async def build_version_graph(artifact) -> VersionGraph
```

### Other Key Routers
- **deployments.py**: Deployment CRUD and sync operations
- **collections.py**: Collection and collection-artifact management
- **projects.py**: Project listing and metadata
- **deployment_sets.py**: Named deployment set operations
- **marketplace.py**: Marketplace catalog and import
- **cache.py**: Cache refresh and invalidation
- **deployment_profiles.py**: Deployment profile management
- **workflows.py**: Workflow execution

---

## 7. Alembic Migrations

**Location**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/migrations/versions/`

**Total**: 65+ migrations from 2025-12-18 to 2026-03-03

### Key Migration Sequence
1. **20251218_0001_add_tags_schema.py** - Initial tagging system
2. **20251215_1200_add_project_templates_and_template_entities.py** - Template support
3. **20260124_1200_add_fts5_catalog_search.py** - Full-text search (FTS5)
4. **20260207_1400_add_deployment_profiles_and_target_platforms.py** - Deployment profiles
5. **20260226_1000_add_similarity_cache_schema.py** - Similarity scoring
6. **20260227_0900_add_workflow_tables.py** - Workflow orchestration
7. **20260228_1000_add_entity_type_configs_table.py** - Custom entity configs
8. **20260301_1000_add_custom_type_fields.py** - Custom artifact types
9. **20260303_1000_add_remote_git_platform_and_deployment_set_remote_fields.py** - Remote platform support
10. **20260303_1100_add_workflow_to_artifact_type_check.py** - Latest

**Env Config** (`env.py`):
- SQLAlchemy 2.0+ compatible
- Supports online and offline migrations
- Target metadata from `skillmeat.cache.models.Base`

---

## 8. Existing Related PRDs

### PRD 1: Repository Pattern Refactor (IN-PROGRESS)
**File**: `docs/project_plans/PRDs/refactors/repo-pattern-refactor-v1.md`

**Status**: Currently implementing hexagonal architecture

**Scope**:
- Create abstract repository interfaces in `skillmeat/core/interfaces/repositories.py`
- Implement `LocalFileSystemRepository` for all core entities
- Wire FastAPI DI for repository injection
- Eliminate direct filesystem/SQL access from routers

**Current Gaps Identified**:
- 15 routers directly access filesystem or SQLite
- 9 partial repositories exist (marketplace/workflow only)
- 5 core repository interfaces missing

### PRD 2: AAA & RBAC Foundation (PLANNED)
**File**: `docs/project_plans/PRDs/features/aaa-rbac-foundation-v1.md`

**Dependency**: Requires PRD 1 (repository interfaces)

**Scope**: Add authentication, authorization, and multi-tenant RBAC

### PRD 3: Enterprise Database Storage (TARGET FOR THIS FEATURE)
**File**: `docs/project_plans/PRDs/refactors/enterprise-db-storage-v1.md`

**Dependency**: Requires PRD 1 (repository interfaces) and PRD 2 (RBAC)

**Scope**:
1. Implement `EnterpriseDBRepository` classes for cloud DB (PostgreSQL/DocumentDB)
2. Eliminate filesystem vault dependency for SaaS users
3. Update deployment engine to stream from API
4. Provide migration tooling for local→cloud transition

---

## 9. Key Architectural Patterns

### Write-Through Cache Pattern
```
User Action (API/CLI)
    ↓
Write Filesystem (~/.skillmeat/)
    ↓
Compute Content Hash
    ↓
Sync to SQLite Cache
    ↓
Invalidate Related Query Caches
```

### Dual Source of Truth
- **Filesystem**: Source for CLI, local persistence
- **SQLite**: Source for web UI, query optimization
- **Sync Point**: `refresh_single_artifact_cache()` function

### Single-User Assumption (Current)
**Note**: No user_id in core tables — extension path documented in `repositories.py`:

```python
# Future multi-tenant extension:
# 1. Add user_id to MarketplaceSource, MarketplaceCatalogEntry
# 2. Add user_id parameter to all repository methods
# 3. Filter queries with WHERE user_id = context.user_id
# 4. Migrate to PostgreSQL for RLS support
```

### Hexagonal Architecture (In Progress)
```
API Routers (Interface adapters)
    ↓
Service Layer (Business logic)
    ↓
Repository Interfaces (Ports)
    ↓
LocalFileSystemRepository / SQLiteRepository (Adapters)
    ↓
Filesystem / SQLite (External systems)
```

---

## 10. Critical Files Reference

| File | Size | Purpose |
|------|------|---------|
| `skillmeat/cache/models.py` | 177KB | 30+ SQLAlchemy ORM models |
| `skillmeat/cache/repositories.py` | 274KB | Repository pattern (partial) |
| `skillmeat/cache/repository.py` | 42KB | Legacy CacheRepository |
| `skillmeat/cache/manager.py` | 55KB | Service layer for cache operations |
| `skillmeat/core/deployment.py` | 600+ lines | Deployment tracking & versioning |
| `skillmeat/storage/deployment.py` | 400+ lines | Filesystem persistence of deployments |
| `skillmeat/api/routers/artifacts.py` | 1000+ lines | Core artifact endpoints |
| `skillmeat/cli/__init__.py` | 494KB | CLI commands (all entry points) |
| `docs/project_plans/PRDs/refactors/repo-pattern-refactor-v1.md` | - | Architecture refactor plan |
| `docs/project_plans/PRDs/refactors/enterprise-db-storage-v1.md` | - | Enterprise DB feature spec |

---

## 11. Deployment & Sync Flow

### Current Deploy Flow
```
CLI: skillmeat deploy <artifact-id> <project-path>
    ↓
Resolve artifact from collection
    ↓
Compute SHA-256 content hash
    ↓
Copy files to .claude/ directory
    ↓
Record metadata in .skillmeat-deployed.toml
    ↓
Call refresh_single_artifact_cache()
    ↓
SQLite cache updated
```

### Current Sync Flow
```
CLI: skillmeat sync <project-path>
    ↓
Read .skillmeat-deployed.toml
    ↓
Compare with filesystem (drift detection)
    ↓
Detect local modifications, new versions upstream
    ↓
Present merge options to user
    ↓
Update cache and deployment records
```

### Enterprise DB Variant (PRD 3)
```
CLI: skillmeat deploy <artifact-id> <project-path>  [ENTERPRISE MODE]
    ↓
Call GET /api/v1/artifacts/{id}/download
    ↓
API returns JSON payload with file tree + contents
    ↓
Parse response and materialize files to .claude/
    ↓
No local filesystem vault needed for SaaS users
```

---

## 12. Summary Table: Current Repositories

| Repository | File | Status | Entity | Methods |
|------------|------|--------|--------|---------|
| BaseRepository | repositories.py | ✓ Implemented | Generic[T] | create, read, update, delete, query |
| MarketplaceSourceRepository | repositories.py | ✓ Implemented | MarketplaceSource | get_by_repo_url, list_all, bulk_create, etc |
| MarketplaceCatalogRepository | repositories.py | ✓ Implemented | MarketplaceCatalogEntry | list_by_source, bulk_create, merge, etc |
| ExecutionStepRepository | execution_step_repository.py | ✓ Implemented | ExecutionStep | CRUD for workflow steps |
| WorkflowExecutionRepository | workflow_execution_repository.py | ✓ Implemented | WorkflowExecution | CRUD for workflow executions |
| WorkflowRepository | workflow_repository.py | ✓ Implemented | Workflow | CRUD for workflow definitions |
| CompositeRepository | composite_repository.py | ✓ Implemented | CompositeArtifact | CRUD for composite artifacts |
| MemoryRepositories | memory_repositories.py | ✓ Implemented | MemoryItem, etc | CRUD for memory system |
| CacheRepository | repository.py | ✓ Implemented | Project, Artifact | Legacy pattern, direct queries |
| **ArtifactRepository** | — | ❌ **MISSING** | Artifact | Needed for PRD 1 |
| **ProjectRepository** | — | ❌ **MISSING** | Project | Needed for PRD 1 |
| **CollectionRepository** | — | ❌ **MISSING** | Collection | Needed for PRD 1 |
| **CollectionArtifactRepository** | — | ❌ **MISSING** | CollectionArtifact | Needed for PRD 1 |
| **DeploymentSetRepository** | — | ❌ **MISSING** | DeploymentSet | Needed for PRD 1 |
| **TagRepository** | — | ❌ **MISSING** | Tag, ArtifactTag | Needed for PRD 1 |

---

## 13. Key Statistics

- **Database**: SQLite with 65+ migrations
- **ORM Models**: 30+ SQLAlchemy models in single models.py file
- **API Routers**: 36 routers, 15 accessing filesystem/SQL directly
- **Repositories**: 9 implemented, 5 core ones missing
- **API Endpoints**: 100+ total endpoints
- **Collection Tables**: 13 main entity tables + 20 supporting tables

---

## 14. Recommendations for Enterprise DB Storage PRD

### Phase 1: Complete Repository Pattern (PRD 1 Foundation)
- [ ] Create `skillmeat/core/interfaces/repositories.py` with interfaces for:
  - `IArtifactRepository`
  - `IProjectRepository`
  - `ICollectionRepository`
  - `ICollectionArtifactRepository`
  - `IDeploymentSetRepository`
  - `ITagRepository`
  - `IDeploymentRepository` (new)

- [ ] Implement concrete `LocalFileSystemRepository` classes
- [ ] Wire FastAPI DI for all repository dependencies
- [ ] Refactor 15 routers to use injected repositories

### Phase 2: Enterprise DB Repositories (PRD 3 Core)
- [ ] Implement `EnterpriseDBRepository` classes for each interface
- [ ] Add multi-tenant filtering via `RequestContext.tenant_id`
- [ ] Schema design for cloud DB (PostgreSQL JSONB or DocumentDB)
- [ ] Alembic migrations for enterprise schema
- [ ] Migration tooling: `skillmeat enterprise migrate`

### Phase 3: Deployment Engine Refactor
- [ ] Add API endpoint: `GET /api/v1/artifacts/{id}/download`
- [ ] Returns JSON with file tree + contents
- [ ] Update CLI deploy command to detect enterprise mode
- [ ] Use API streaming in enterprise mode, filesystem in local mode

### Phase 4: Authentication & RBAC (PRD 2)
- [ ] Integrate with enterprise authentication system
- [ ] Add `RequestContext` to all data access calls
- [ ] Implement tenant isolation via database queries
- [ ] Multi-tenant testing and validation
