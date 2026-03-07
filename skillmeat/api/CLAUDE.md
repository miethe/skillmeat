# CLAUDE.md - API Backend

FastAPI backend for SkillMeat web interface with SQLAlchemy cache layer.

## Architecture

**Stack**: FastAPI + SQLAlchemy + Alembic + Uvicorn

```
api/
├── server.py               # FastAPI app + lifespan
├── config.py               # APISettings (Pydantic BaseSettings)
├── dependencies.py         # AppState, dependency injection
├── openapi.py              # OpenAPI spec generation
├── project_registry.py     # Project path resolution
├── middleware/             # Request/response processing
│   ├── auth.py             # Token/API key authentication
│   ├── rate_limit.py       # Rate limiting
│   ├── observability.py    # Logging/monitoring
│   └── burst_detection.py  # Burst detection
├── routers/                # API endpoints (25 routers)
│   ├── artifacts.py, user_collections.py, collections.py, groups.py
│   ├── deployments.py, projects.py, analytics.py, marketplace.py
│   ├── marketplace_sources.py, marketplace_catalog.py, mcp.py
│   ├── bundles.py, tags.py, versions.py, context_entities.py
│   ├── context_sync.py, match.py, merge.py, ratings.py
│   ├── settings.py, config.py, project_templates.py, cache.py, health.py
│   └── __init__.py
├── schemas/                # Pydantic request/response models (26 files)
├── services/               # Service layer
│   ├── artifact_cache_service.py
│   ├── artifact_metadata_service.py
│   ├── background_tasks.py
│   └── collection_service.py
├── utils/                  # Utilities
│   ├── cache.py
│   ├── error_handlers.py
│   ├── fts5.py
│   └── github_cache.py
└── tests/                  # Integration tests
```

---

## Server Lifecycle

**File**: `server.py`

**Pattern**: Uses `AppState` container initialized in lifespan function.

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: Initialize AppState with managers from skillmeat.core"""
    app.state = AppState()
    app.state.initialize(get_settings())
    yield
    app.state.shutdown()

app = FastAPI(
    title="SkillMeat API",
    version=skillmeat_version,
    lifespan=lifespan,
    openapi_tags=TAGS_METADATA,
)
```

**Run Server**:

```bash
# Development (with auto-reload)
uvicorn skillmeat.api.server:app --reload --host 127.0.0.1 --port 8080

# Production
uvicorn skillmeat.api.server:app --workers 4 --host 0.0.0.0 --port 8080
```

---

## Configuration

**File**: `config.py`

**APISettings Class** (Pydantic BaseSettings):

| Field | Default | Description |
|-------|---------|-------------|
| `env` | `development` | Environment: development, production, testing |
| `host` | `127.0.0.1` | Server bind address |
| `port` | `8080` | Server port |
| `reload` | `false` | Auto-reload on code changes |
| `workers` | `1` | Worker processes |
| `cors_enabled` | `true` | Enable CORS |
| `cors_origins` | `["http://localhost:3000", "http://localhost:3001", ...]` | Allowed CORS origins |
| `api_key_enabled` | `false` | Enable API key authentication |
| `api_key` | `null` | API key value (if enabled) |
| `auth_enabled` | `false` | Require bearer token auth |
| `rate_limit_enabled` | `false` | Enable rate limiting |
| `rate_limit_requests` | `100` | Max requests per minute |
| `log_level` | `INFO` | DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `log_format` | `json` | Log format: json or text |
| `collection_dir` | `~/.skillmeat/collections` | Override collection path |
| `github_token` | `null` | GitHub PAT for higher rate limits |
| `enable_auto_discovery` | `true` | Artifact auto-discovery feature |
| `enable_auto_population` | `true` | Auto-populate GitHub metadata |
| `discovery_cache_ttl` | `3600` | Cache TTL in seconds |
| `workflow_engine_enabled` | `true` | Enable workflow orchestration engine |

**Environment Variables** (prefix `SKILLMEAT_`):

```bash
export SKILLMEAT_ENV=production
export SKILLMEAT_HOST=0.0.0.0
export SKILLMEAT_PORT=8080
export SKILLMEAT_CORS_ORIGINS='["https://example.com"]'
export SKILLMEAT_API_KEY_ENABLED=true
export SKILLMEAT_API_KEY=your_key_here
export SKILLMEAT_GITHUB_TOKEN=ghp_xxx
```

---

## Repository Pattern (Hexagonal Architecture)

**File**: See `.claude/context/key-context/repository-architecture.md` for complete guide.

**Quick Overview**: SkillMeat uses hexagonal architecture with abstract repository interfaces (ABCs) between routers and storage backends. This decouples the API from filesystem/database details and enables future multi-backend support.

**Key Invariants**:
1. **No direct filesystem access in routers** — use `Annotated[I*Repository, Depends(...)]` dependency injection
2. **DTOs are the data contract** — never pass ORM models to routers
3. **Write-through pattern** — mutations write filesystem first, then sync DB via `refresh_single_artifact_cache()`
4. **Mock repositories in tests** — update `tests/mocks/repositories.py` when ABCs change

**Module Map**:
- **Interfaces**: `skillmeat/core/interfaces/repositories.py` (10 ABCs), `dtos.py` (frozen dataclasses)
- **Implementations**: `skillmeat/core/repositories/local_*.py` (filesystem + SQLAlchemy)
- **Factories**: `skillmeat/api/dependencies.py` (DI providers with edition-based routing)
- **Mocks**: `tests/mocks/repositories.py` (in-memory test doubles)

**DI Aliases** (in dependencies.py):
```python
ArtifactRepoDep = Annotated[IArtifactRepository, Depends(get_artifact_repository)]
ProjectRepoDep = Annotated[IProjectRepository, Depends(get_project_repository)]
CollectionRepoDep = Annotated[ICollectionRepository, Depends(get_collection_repository)]
DeploymentRepoDep = Annotated[IDeploymentRepository, Depends(get_deployment_repository)]
TagRepoDep = Annotated[ITagRepository, Depends(get_tag_repository)]
SettingsRepoDep = Annotated[ISettingsRepository, Depends(get_settings_repository)]
GroupRepoDep = Annotated[IGroupRepository, Depends(get_group_repository)]
ContextEntityRepoDep = Annotated[IContextEntityRepository, Depends(get_context_entity_repository)]
MarketplaceSourceRepoDep = Annotated[IMarketplaceSourceRepository, Depends(get_marketplace_source_repository)]
ProjectTemplateRepoDep = Annotated[IProjectTemplateRepository, Depends(get_project_template_repository)]
```

**When Adding an Endpoint**: Read `.claude/context/key-context/repository-architecture.md` § "Recipe 1" for step-by-step guide.

---

## Dependency Injection

**File**: `dependencies.py`

**AppState Container**: Holds singleton instances initialized in lifespan.

**Type Aliases** (for cleaner route signatures):

| Alias | Type | Purpose |
|-------|------|---------|
| `ConfigManagerDep` | `Annotated[ConfigManager, Depends(...)]` | Configuration manager |
| `CollectionManagerDep` | `Annotated[CollectionManager, Depends(...)]` | Collection operations |
| `ArtifactManagerDep` | `Annotated[ArtifactManager, Depends(...)]` | Artifact operations |
| `TokenManagerDep` | `Annotated[TokenManager, Depends(...)]` | Token verification |
| `SyncManagerDep` | `Annotated[SyncManager, Depends(...)]` | Sync operations |
| `ContextSyncServiceDep` | `Annotated[ContextSyncService, Depends(...)]` | Context sync |
| `SettingsDep` | `Annotated[APISettings, Depends(get_settings)]` | Configuration settings |
| `APIKeyDep` | `Annotated[Optional[str], Security(api_key_header)]` | API key auth |

**Usage in Routes**:

```python
@router.get("/artifacts")
async def list_artifacts(
    artifact_mgr: ArtifactManagerDep,
    settings: SettingsDep,
) -> ArtifactListResponse:
    artifacts = artifact_mgr.list_artifacts()
    return ArtifactListResponse(artifacts=artifacts)
```

---

## Routers

**Pattern**: One router per domain. All registered in `server.py` with `/api/v1/` prefix.

### Available Routers (27 total)

| Router | Prefix | Purpose |
|--------|--------|---------|
| `artifacts` | `/api/v1/artifacts` | Artifact CRUD, deployment |
| `user_collections` | `/api/v1/user-collections` | User collection operations |
| `collections` | `/api/v1/collections` | Collection management (DEPRECATED) |
| `groups` | `/api/v1/groups` | Group management and filtering |
| `deployments` | `/api/v1/deployments` | Deployment operations |
| `projects` | `/api/v1/projects` | Project registry |
| `analytics` | `/api/v1/analytics` | Usage analytics |
| `marketplace` | `/api/v1/marketplace` | Claude marketplace |
| `marketplace_sources` | `/api/v1/marketplace-sources` | Marketplace sources |
| `marketplace_catalog` | `/api/v1/marketplace-catalog` | Marketplace catalog |
| `mcp` | `/api/v1/mcp` | MCP server management |
| `bundles` | `/api/v1/bundles` | Artifact bundles |
| `tags` | `/api/v1/tags` | Tag management |
| `versions` | `/api/v1/versions` | Version tracking |
| `context_entities` | `/api/v1/context-entities` | Context entity management |
| `context_sync` | `/api/v1/context-sync` | Context synchronization |
| `match` | `/api/v1/match` | Artifact matching |
| `merge` | `/api/v1/merge` | Artifact merging |
| `ratings` | `/api/v1/ratings` | Artifact ratings |
| `settings` | `/api/v1/settings` | User settings, entity type configs, entity categories |
| `config` | `/api/v1/config` | Configuration endpoints |
| `project_templates` | `/api/v1/project-templates` | Project templates |
| `workflows` | `/api/v1/workflows` | Workflow definition management |
| `workflow_executions` | `/api/v1/workflow-executions` | Workflow execution runtime |
| `cache` | `/api/v1/cache` | Cache management |
| `health` | `/health` | Health checks |

### Router Pattern

```python
from fastapi import APIRouter
from .schemas import ArtifactCreateRequest, ArtifactResponse

router = APIRouter(prefix="/api/v1/artifacts", tags=["artifacts"])

@router.get("/", response_model=List[ArtifactResponse])
async def list_artifacts(...): ...

@router.post("/", response_model=ArtifactResponse, status_code=201)
async def create_artifact(request: ArtifactCreateRequest, ...): ...

@router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(artifact_id: str, ...): ...

@router.put("/{artifact_id}", response_model=ArtifactResponse)
async def update_artifact(artifact_id: str, request: ArtifactCreateRequest, ...): ...

@router.delete("/{artifact_id}", status_code=204)
async def delete_artifact(artifact_id: str, ...): ...
```

See `.claude/context/key-context/router-patterns.md` for layer contract and HTTP patterns.

### Settings Router Endpoints

The `settings` router includes endpoints for managing entity type configurations and categories:

**Entity Type Configs**:
- `GET /api/v1/settings/entity-type-configs` - List all entity type configurations
- `POST /api/v1/settings/entity-type-configs` - Create new entity type config
- `PUT /api/v1/settings/entity-type-configs/{slug}` - Update entity type config by slug
- `DELETE /api/v1/settings/entity-type-configs/{slug}` - Delete entity type config

**Entity Categories**:
- `GET /api/v1/settings/entity-categories` - List all entity categories
- `POST /api/v1/settings/entity-categories` - Create new entity category

These endpoints support multi-select entity categories via the `entity_category_associations` join table.

---

## Schemas (Pydantic Models)

**Location**: `schemas/` directory (26 files)

**Pattern**: Separate request/response models with ORM mode enabled.

```python
class ArtifactCreateRequest(BaseModel):
    name: str
    artifact_type: ArtifactType
    source: str
    version: str = "latest"

class ArtifactResponse(BaseModel):
    id: str
    name: str
    artifact_type: ArtifactType
    source: str
    version: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

**Schema Files**:
- `artifacts.py`, `user_collections.py`, `collections.py`, `groups.py`
- `deployments.py`, `projects.py`, `analytics.py`, `marketplace.py`
- `tags.py`, `versions.py`, `context_entity.py`, `context_sync.py`
- `settings.py`, `config.py`, `project_template.py`, `mcp.py`
- `bundles.py`, `match.py`, `merge.py`, `ratings.py`
- `discovery.py`, `drift.py`, `errors.py`, `scoring.py`, `cache.py`, `common.py`
- `workflows.py`, `workflow_executions.py` (workflow orchestration)

See actual files for complete schema definitions.

---

## Middleware

**File**: `middleware/`

**Registration Order** (in `server.py`):

```python
app.add_middleware(ObservabilityMiddleware)
app.add_middleware(RateLimitMiddleware, burst_threshold=10, window_seconds=60)
app.add_middleware(CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)
```

### Authentication

**Files**: `middleware/auth.py` (legacy), `middleware/enterprise_auth.py`, `middleware/tenant_context.py`, `auth/` (provider implementations)

**Key invariant**: All `/api/v1/*` routes are protected by default via the registered `AuthProvider`. `LocalAuthProvider` must always remain as the default fallback (zero-config local dev + single-tenant mode).

**New endpoints**: Use `AuthContextDep` / `require_auth()` from `dependencies.py` — not the legacy `TokenDep` from `middleware/auth.py`.

**Full reference**: `.claude/context/key-context/auth-architecture.md` — provider selection, `AuthContext` fields, Role/Scope tables, tenant context, owner_id type mismatch, anti-patterns.

### Rate Limiting

**File**: `middleware/rate_limit.py`

- IP-based rate limiting
- Configurable via `rate_limit_enabled` and `rate_limit_requests` settings
- Returns 429 when exceeded

### Burst Detection

**File**: `middleware/burst_detection.py`

- Detects sudden traffic spikes
- Configurable burst threshold
- Helps identify attack patterns

### Observability

**File**: `middleware/observability.py`

- Request/response timing
- Structured JSON logging
- Status code tracking

---

## Error Handling

**Pattern**: Use HTTPException with appropriate status codes and logging.

```python
# Before raising HTTPException, always log
logger.exception(f"Operation failed: {e}")
raise HTTPException(status_code=500, detail="Internal server error")

# Validation errors (automatic via Pydantic)
# 422 Unprocessable Entity

# Authorization
raise HTTPException(status_code=401, detail="Unauthorized")

# Not found
raise HTTPException(status_code=404, detail=f"Resource '{id}' not found")

# Validation
raise HTTPException(status_code=400, detail="Invalid request")
```

See `utils/error_handlers.py` for centralized error handling patterns.

---

## Database Layer

**Location**: `skillmeat/cache/` module

**Architecture**:

```
Routers → Repository DI (I*Repository ABCs) → Local*Repository implementations
    ↓                                                  ↓
  (or legacy path)                          SQLAlchemy ORM (cache/models.py)
    ↓                                                  ↓
Services (api/services/)                   SQLite Database
    ↓
cache/repositories.py (internal helpers)
```

**Note**: Routers access the database exclusively through repository DI aliases (`*RepoDep`). Direct `session.query()` calls in routers are prohibited — all DB access is mediated by `I*Repository` implementations in `skillmeat/core/repositories/`.

**Components**:

| Component | File | Purpose |
|-----------|------|---------|
| **Models** | `cache/models.py` | SQLAlchemy ORM models (15+ entities) |
| **Repositories** | `cache/repositories.py` | Data access layer |
| **Manager** | `cache/manager.py` | Cache lifecycle management |
| **Migrations** | `cache/migrations/` | Alembic schema version control |
| **Refresh** | `cache/refresh.py` | Cache sync mechanism |

**Write-Through Pattern**:

1. Write to filesystem first
2. Call `refresh_single_artifact_cache()` to sync database
3. Return to client

See root `CLAUDE.md` → "Data Flow Principles" for full pattern.

---

## Testing

**File**: `tests/`

**Pattern**: Use TestClient with mocked dependencies.

```python
from fastapi.testclient import TestClient
from skillmeat.api.server import app

client = TestClient(app)

def test_list_artifacts(monkeypatch):
    mock_artifacts = [...]
    monkeypatch.setattr(
        "skillmeat.api.dependencies.get_artifact_manager",
        lambda: MockArtifactManager(artifacts=mock_artifacts)
    )
    response = client.get("/api/v1/artifacts")
    assert response.status_code == 200
```

**Run Tests**:

```bash
pytest skillmeat/api/tests/ -v
```

---

## OpenAPI Documentation

**Auto-Generated**: Available at `/docs` (Swagger UI) and `/redoc` (ReDoc)

**Custom OpenAPI** (`openapi.py`):

- Custom tags and security schemes
- API version and description configuration
- Schema modifications for better documentation

---

## External Services

### GitHub API

Use centralized client for all GitHub operations:

```python
from skillmeat.core.github_client import get_github_client

@router.get("/metadata/{owner}/{repo}")
async def get_metadata(owner: str, repo: str) -> MetadataResponse:
    client = get_github_client()
    metadata = client.get_repo_metadata(f"{owner}/{repo}")
    return MetadataResponse(**metadata)
```

See root `CLAUDE.md` → "GitHub Client" section for full API reference and error handling.

---

## Data Flow Standard

All endpoints must comply with canonical data flow principles. See root `CLAUDE.md` for 6 principles.

### Backend Rules

- **Read endpoints**: Query DB cache (`CollectionArtifact` table) with filesystem fallback
- **Write-through**: Mutations write filesystem first, then call `refresh_single_artifact_cache()` to sync
- **File mutations**: create/update/delete on artifact files must call `refresh_single_artifact_cache()`
- **DB-native writes**: Collections, groups, tags write DB first; tags write back to filesystem where applicable

### Cache Refresh Triggers

| Trigger | Scope | Mechanism |
|---------|-------|-----------|
| Server startup | Full | FS → DB sync in `lifespan()` |
| Single mutation | Targeted | `refresh_single_artifact_cache()` |
| Manual refresh | Full | `POST /api/v1/cache/refresh` |

**Stale times & invalidation graph**:
**Read**: `.claude/context/key-context/data-flow-patterns.md`

---

## Key Patterns

### Status Codes

| Method | Code | Meaning |
|--------|------|---------|
| GET | 200 | Success |
| POST | 201 | Created |
| PUT | 200 | Updated |
| DELETE | 204 | Deleted (no content) |
| Errors | 400, 401, 404, 422, 500 | See error handling |

### Query Parameters

```python
@router.get("/artifacts")
async def list_artifacts(
    artifact_type: Optional[ArtifactType] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> ArtifactListResponse: ...
```

### Path Parameters

```python
@router.get("/artifacts/{artifact_id}")
async def get_artifact(
    artifact_id: str,
    artifact_mgr: ArtifactManagerDep,
) -> ArtifactResponse: ...
```

### Request Body

```python
@router.post("/artifacts")
async def create_artifact(
    request: ArtifactCreateRequest,
    artifact_mgr: ArtifactManagerDep,
) -> ArtifactResponse: ...
```

---

## Context Files

| File | Load When |
|------|-----------|
| `.claude/context/key-context/auth-architecture.md` | Adding auth to endpoints, modifying auth middleware, debugging 401/403, working with RBAC/scopes |
| `.claude/context/key-context/repository-architecture.md` | **NEW**: Adding endpoints, refactoring routers to repository DI, designing new storage backends |
| `.claude/context/key-context/context-loading-playbook.md` | Select minimal context by task |
| `.claude/context/key-context/api-contract-source-of-truth.md` | Endpoint/schema validation and drift checks |
| `.claude/context/key-context/fe-be-type-sync-playbook.md` | Backend schema changes affecting frontend payloads |
| `.claude/context/key-context/data-flow-patterns.md` | Cache sync, write-through, invalidation rules |
| `.claude/context/api-endpoint-mapping.md` | Adding/debugging endpoints |

---

## Important Notes

- **AppState Pattern**: Shared manager instances initialized in lifespan, not stateless
- **Contract Authority**: `skillmeat/api/openapi.json` is the source of truth for endpoint contracts
- **Default Port**: 8080 (not 8000)
- **Default Host**: 127.0.0.1 (dev) or 0.0.0.0 (production)
- **Cache Layer**: SQLAlchemy + Alembic fully implemented in `skillmeat/cache/`
- **Write-Through**: All mutations must sync filesystem first, then database
- **Error Logging**: Always log before raising HTTPException
- **API Versioning**: `/api/v1` prefix for future compatibility
- **Authentication**: Configurable via `api_key_enabled` and `auth_enabled` settings
- **Rate Limiting**: IP-based, configurable per-minute requests
