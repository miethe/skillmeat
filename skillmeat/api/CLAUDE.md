# CLAUDE.md - API Backend

FastAPI backend for SkillMeat web interface

## Architecture

**Stack**: FastAPI + SQLAlchemy + Alembic + Uvicorn

```
api/
├── server.py               # FastAPI app + lifespan
├── config.py               # APISettings (Pydantic BaseSettings)
├── dependencies.py         # Dependency injection
├── openapi.py              # OpenAPI spec generation
├── project_registry.py     # Project path resolution
├── routers/                # API endpoints
│   ├── artifacts.py
│   ├── collections.py
│   ├── deployments.py
│   ├── projects.py
│   ├── analytics.py
│   ├── marketplace.py
│   ├── mcp.py
│   ├── bundles.py
│   └── health.py
├── schemas/                # Pydantic request/response models
│   ├── artifacts.py
│   ├── collections.py
│   ├── deployments.py
│   └── common.py
├── middleware/             # Request/response processing
│   ├── auth.py             # Token authentication
│   ├── rate_limit.py       # Rate limiting
│   └── observability.py    # Logging/monitoring
├── tests/                  # API integration tests
└── utils/                  # API utilities
```

---

## Server Lifecycle

**File**: `server.py`

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: Load config, init managers, configure logging"""
    settings = get_settings()
    app.state.settings = settings
    app.state.artifact_manager = ArtifactManager(...)
    app.state.collection_manager = CollectionManager(...)
    # ... init other managers
    yield
    # Cleanup on shutdown
```

**App Creation**:

```python
app = FastAPI(
    title="SkillMeat API",
    version=skillmeat_version,
    lifespan=lifespan,
    openapi_tags=TAGS_METADATA,
)
```

**Run Server**:

```bash
# Development
uvicorn skillmeat.api.server:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn skillmeat.api.server:app --workers 4 --host 0.0.0.0 --port 8000
```

---

## Configuration

**File**: `config.py`

**Environment Variables**:

| Variable | Default | Description |
|----------|---------|-------------|
| `SKILLMEAT_COLLECTION_PATH` | `~/.skillmeat/collection` | Collection root |
| `SKILLMEAT_API_HOST` | `0.0.0.0` | API bind address |
| `SKILLMEAT_API_PORT` | `8000` | API port |
| `SKILLMEAT_API_RELOAD` | `false` | Auto-reload in dev |
| `SKILLMEAT_LOG_LEVEL` | `INFO` | Logging level |
| `SKILLMEAT_CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed origins |

**Settings Class**:

```python
class APISettings(BaseSettings):
    collection_path: Path
    api_host: str
    api_port: int
    cors_origins: List[str]
    log_level: str

    class Config:
        env_prefix = "SKILLMEAT_"
        env_file = ".env"
```

---

## Dependency Injection

**File**: `dependencies.py`

**Pattern**: Use `app.state` for shared managers, Depends() for injection

```python
# Global state (initialized in lifespan)
app_state = {"initialized": False}

# Dependency functions
def get_artifact_manager(request: Request) -> ArtifactManager:
    return request.app.state.artifact_manager

def get_collection_manager(request: Request) -> CollectionManager:
    return request.app.state.collection_manager

# Type aliases for cleaner signatures
ArtifactManagerDep = Annotated[ArtifactManager, Depends(get_artifact_manager)]
CollectionManagerDep = Annotated[CollectionManager, Depends(get_collection_manager)]
```

**Usage in Routes**:

```python
@router.get("/artifacts")
async def list_artifacts(
    artifact_mgr: ArtifactManagerDep,
    token: TokenDep = Depends(verify_api_key),
) -> ArtifactListResponse:
    artifacts = artifact_mgr.list_artifacts()
    return ArtifactListResponse(artifacts=artifacts)
```

---

## Routers

**Pattern**: One router per domain, register in `server.py`

### Router Structure

**File**: `routers/artifacts.py`

```python
router = APIRouter(
    prefix="/api/v1/artifacts",
    tags=["artifacts"],
)

@router.get("/", response_model=ArtifactListResponse)
async def list_artifacts(...): ...

@router.post("/", response_model=ArtifactCreateResponse, status_code=201)
async def create_artifact(...): ...

@router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(...): ...

@router.put("/{artifact_id}", response_model=ArtifactResponse)
async def update_artifact(...): ...

@router.delete("/{artifact_id}", status_code=204)
async def delete_artifact(...): ...
```

### Available Routers

| Router | Prefix | Purpose |
|--------|--------|---------|
| `artifacts` | `/api/v1/artifacts` | Artifact CRUD, deployment |
| `collections` | `/api/v1/collections` | Collection management |
| `deployments` | `/api/v1/deployments` | Deployment operations |
| `projects` | `/api/v1/projects` | Project registry |
| `analytics` | `/api/v1/analytics` | Usage analytics |
| `marketplace` | `/api/v1/marketplace` | Claude marketplace |
| `mcp` | `/api/v1/mcp` | MCP server management |
| `bundles` | `/api/v1/bundles` | Artifact bundles |
| `health` | `/health` | Health checks |

---

## Schemas (Pydantic Models)

**File**: `schemas/artifacts.py`

**Pattern**: Separate request/response models

```python
# Request models
class ArtifactCreateRequest(BaseModel):
    name: str
    artifact_type: ArtifactType
    source: str
    version: str = "latest"
    scope: ScopeType = "user"
    aliases: List[str] = []

# Response models
class ArtifactResponse(BaseModel):
    id: str
    name: str
    artifact_type: ArtifactType
    source: str
    version: str
    scope: ScopeType
    aliases: List[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # ORM mode

# List responses
class ArtifactListResponse(BaseModel):
    artifacts: List[ArtifactResponse]
    total: int
    page: int = 1
    page_size: int = 50
```

**Common Types** (`schemas/common.py`):

```python
class ArtifactType(str, Enum):
    SKILL = "skill"
    COMMAND = "command"
    AGENT = "agent"
    MCP = "mcp"
    HOOK = "hook"

class ScopeType(str, Enum):
    USER = "user"
    LOCAL = "local"

class ArtifactSourceType(str, Enum):
    GITHUB = "github"
    LOCAL = "local"
```

---

## Middleware

**Registration** (in `server.py`):

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(ObservabilityMiddleware)
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)
```

### Authentication Middleware

**File**: `middleware/auth.py`

```python
# Token dependency
TokenDep = Annotated[str, Depends(get_token)]

def get_token(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid token")
    return authorization.removeprefix("Bearer ")

async def verify_api_key(token: TokenDep) -> bool:
    # Verify token against config/database
    if not is_valid_token(token):
        raise HTTPException(401, "Invalid API key")
    return True
```

### Rate Limiting

**File**: `middleware/rate_limit.py`

```python
class RateLimitMiddleware:
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        self.app = app
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # IP -> [(timestamp, count)]

    async def __call__(self, scope, receive, send):
        client_ip = scope["client"][0]
        # Check rate limit, raise 429 if exceeded
```

### Observability

**File**: `middleware/observability.py`

```python
class ObservabilityMiddleware:
    async def __call__(self, scope, receive, send):
        start_time = time.time()
        # Process request
        await self.app(scope, receive, send)
        # Log request duration, status, etc.
        duration = time.time() - start_time
        logger.info(f"{method} {path} {status} {duration:.2f}s")
```

---

## Error Handling

**Pattern**: Use HTTPException with appropriate status codes

```python
# 400 Bad Request
raise HTTPException(
    status_code=400,
    detail="Invalid artifact source format"
)

# 404 Not Found
raise HTTPException(
    status_code=404,
    detail=f"Artifact '{artifact_id}' not found"
)

# 422 Unprocessable Entity (validation errors)
# Automatically handled by Pydantic

# 500 Internal Server Error
try:
    result = dangerous_operation()
except Exception as e:
    logger.exception(f"Operation failed: {e}")
    raise HTTPException(500, "Internal server error")
```

**Global Exception Handler** (optional):

```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
```

---

## Testing

**File**: `tests/test_artifacts_routes.py`

**Pattern**: Use TestClient, mock managers

```python
from fastapi.testclient import TestClient
from skillmeat.api.server import app

client = TestClient(app)

def test_list_artifacts(monkeypatch):
    # Mock artifact manager
    mock_artifacts = [...]
    monkeypatch.setattr(
        "skillmeat.api.dependencies.get_artifact_manager",
        lambda: MockArtifactManager(artifacts=mock_artifacts)
    )

    response = client.get("/api/v1/artifacts")
    assert response.status_code == 200
    assert len(response.json()["artifacts"]) == len(mock_artifacts)

def test_create_artifact():
    response = client.post("/api/v1/artifacts", json={
        "name": "test-skill",
        "artifact_type": "skill",
        "source": "user/repo/skill",
    })
    assert response.status_code == 201
    assert response.json()["name"] == "test-skill"
```

**Run Tests**:

```bash
pytest skillmeat/api/tests/ -v
```

---

## OpenAPI Documentation

**Auto-Generated**: Available at `/docs` (Swagger UI) and `/redoc` (ReDoc)

**Custom OpenAPI Schema** (`openapi.py`):

```python
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="SkillMeat API",
        version=skillmeat_version,
        description="Personal collection manager for Claude Code artifacts",
        routes=app.routes,
    )

    # Add custom tags, security schemes, etc.
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

**Export OpenAPI JSON**:

```bash
python -c "from skillmeat.api.server import app; import json; print(json.dumps(app.openapi()))" > openapi.json
```

---

## Key Patterns

### Async Handlers

All route handlers should be async:

```python
@router.get("/artifacts")
async def list_artifacts(...) -> ArtifactListResponse:
    # Even if not using await, mark as async for consistency
    artifacts = artifact_mgr.list_artifacts()
    return ArtifactListResponse(artifacts=artifacts)
```

### Query Parameters

```python
@router.get("/artifacts")
async def list_artifacts(
    artifact_type: Optional[ArtifactType] = Query(None),
    scope: Optional[ScopeType] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> ArtifactListResponse:
    ...
```

### Path Parameters

```python
@router.get("/artifacts/{artifact_id}")
async def get_artifact(
    artifact_id: str,
    artifact_mgr: ArtifactManagerDep,
) -> ArtifactResponse:
    artifact = artifact_mgr.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(404, f"Artifact '{artifact_id}' not found")
    return ArtifactResponse.from_orm(artifact)
```

### Request Body

```python
@router.post("/artifacts")
async def create_artifact(
    request: ArtifactCreateRequest,
    artifact_mgr: ArtifactManagerDep,
) -> ArtifactCreateResponse:
    artifact = artifact_mgr.create_artifact(
        name=request.name,
        artifact_type=request.artifact_type,
        source=request.source,
    )
    return ArtifactCreateResponse.from_orm(artifact)
```

---

## Database (Future)

**Note**: Currently using file-based storage. SQLAlchemy + Alembic integration planned.

**When Implemented**:

```python
# models.py (SQLAlchemy models)
class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    artifact_type = Column(Enum(ArtifactType), nullable=False)
    # ...

# Alembic migrations
alembic init migrations
alembic revision --autogenerate -m "Create artifacts table"
alembic upgrade head
```

---

## Production Deployment

**Docker** (future):

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .
CMD ["uvicorn", "skillmeat.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Environment**:

```bash
export SKILLMEAT_COLLECTION_PATH=/data/collection
export SKILLMEAT_LOG_LEVEL=INFO
export SKILLMEAT_CORS_ORIGINS='["https://skillmeat.example.com"]'
uvicorn skillmeat.api.server:app --workers 4 --host 0.0.0.0 --port 8000
```

---

## Important Notes

- **Stateless**: API should be stateless; state in collection/filesystem
- **Thread Safety**: Use locks when modifying collection files
- **Error Logging**: Always log exceptions before raising HTTPException
- **CORS**: Configure origins carefully in production
- **API Versioning**: Use `/api/v1` prefix for future compatibility
- **Rate Limiting**: Adjust limits based on usage patterns
- **Authentication**: Currently basic token auth; consider OAuth2 for production
