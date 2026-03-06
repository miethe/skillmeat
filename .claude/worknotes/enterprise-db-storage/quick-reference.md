# Enterprise DB Storage - Quick Reference

## Current State Analysis

### File Locations
| What | Location | Size |
|------|----------|------|
| DB Models (30+) | `skillmeat/cache/models.py` | 177KB |
| Repositories (partial) | `skillmeat/cache/repositories.py` | 274KB |
| Legacy CacheRepository | `skillmeat/cache/repository.py` | 42KB |
| Deployment tracking | `skillmeat/core/deployment.py` | ~600 LOC |
| Deployment storage | `skillmeat/storage/deployment.py` | ~400 LOC |
| Alembic migrations | `skillmeat/cache/migrations/versions/` | 65+ files |
| API Routers | `skillmeat/api/routers/` | 36 files |
| CLI entry point | `skillmeat/cli/__init__.py` | 494KB |

### Key Tables (13 Main + 20 Supporting)
```
projects          ← Project metadata
artifacts         ← Artifact CRUD + versions
collections       ← User collections
collection_artifacts ← M-M with artifacts
deployment_sets   ← Batch deployment groups
marketplace_*     ← GitHub marketplace sync
workflows         ← Workflow orchestration
deployment_profiles ← Reusable profiles
artifact_tags     ← Tagging system
(+ 20 more for ratings, similarity, entity configs, etc.)
```

### Repository Pattern Status
✓ **Implemented**: MarketplaceSourceRepository, MarketplaceCatalogRepository, WorkflowRepository, CompositeRepository (9 total)

❌ **Missing (Critical for PRD)**: ArtifactRepository, ProjectRepository, CollectionRepository, CollectionArtifactRepository, DeploymentSetRepository, TagRepository

## Key Classes & Methods

### Core Deployment Class
```python
@dataclass
class Deployment:
    artifact_name: str
    artifact_type: str
    deployed_at: datetime
    artifact_path: Path  # Relative within profile
    content_hash: str  # SHA-256
    local_modifications: bool
    parent_hash: Optional[str]
    version_lineage: List[str]
    deployment_profile_id: Optional[str]
    platform: Optional[Platform]
```

### Deployment Tracker (Filesystem Persistence)
```python
class DeploymentTracker:
    DEPLOYMENT_FILE = ".skillmeat-deployed.toml"

    @staticmethod
    def read_deployments(project_path: Path) -> List[Deployment]
    @staticmethod
    def write_deployments(project_path: Path, deployments: List[Deployment]) -> None
```

### Base Repository (Partial Pattern)
```python
class BaseRepository(Generic[T]):
    def _get_session() -> Session
    def create(entity: T) -> T
    def read(id: str) -> T
    def update(entity: T) -> T
    def delete(id: str) -> bool
    @contextmanager
    def transaction() -> Generator[Session]
```

### Cache Manager (Service Layer)
```python
# skillmeat/cache/manager.py (55KB)
class CacheManager:
    def refresh_single_artifact_cache(artifact_id: str, project_path: Path)
    def sync_collection_artifacts(collection_id: str)
    def invalidate_related_caches(artifact_id: str)
```

## Critical APIs

### List Artifacts (Paginated)
```
GET /artifacts
  ?project_id={id}
  &collection_id={id}
  &cursor={base64}
  &limit=50
  &type={type}
  &sort={updated|name}
```

### Get Artifact with Full Content
```
GET /artifacts/{id}
  ?include_content=true
  &include_version_graph=true
  &include_deployment_stats=true
```

### Discover Artifacts in Project
```
POST /artifacts/discover
  Body: {
    "project_path": "/path/to/project",
    "artifact_types": ["skill", "command"],
    "dry_run": true
  }
```

### Bulk Import
```
POST /artifacts/bulk-import
  Body: {
    "artifacts": [
      {"id": "...", "collection_id": "..."},
      ...
    ],
    "deployment_set_id": "..."  # Optional
  }
```

### Check Upstream
```
GET /artifacts/{id}/check-upstream
  → {
    "has_upstream": true,
    "upstream_version": "v1.2.0",
    "upstream_hash": "abc123...",
    "local_hash": "def456...",
    "is_outdated": true
  }
```

## Write-Through Pattern

1. **CLI Deploy**: Copy files to `.claude/` + record hash
2. **Sync to DB**: Call `refresh_single_artifact_cache(artifact_id)`
3. **Cache Manager**: Updates `artifacts` table + related entity caches
4. **Query Invalidation**: Clears upstream, similar, and stat caches

## PRD Dependencies

```
PRD 1: Repository Pattern (IN-PROGRESS)
  ↓ Builds on (provides interfaces)
PRD 2: AAA & RBAC (PLANNED)
  ↓ Builds on (uses interfaces + auth)
PRD 3: Enterprise DB Storage (TARGET)
  ↓ Implements EnterpriseDBRepository for each interface
```

## Enterprise DB Requirements (PRD 3)

### Database Schema Additions
```sql
-- Multi-tenant support
ALTER TABLE artifacts ADD COLUMN tenant_id VARCHAR NOT NULL;
ALTER TABLE projects ADD COLUMN tenant_id VARCHAR NOT NULL;
ALTER TABLE collections ADD COLUMN tenant_id VARCHAR NOT NULL;

-- Cloud-native fields
ALTER TABLE artifacts ADD COLUMN remote_storage_id VARCHAR;  -- S3/GCS ref
ALTER TABLE artifacts ADD COLUMN deployment_url VARCHAR;  -- API stream URL
ALTER TABLE deployment_sets ADD COLUMN remote_git_url VARCHAR;  -- For CD pipelines
```

### Enterprise Repository Implementation
```python
class EnterpriseArtifactRepository(IArtifactRepository):
    def __init__(self, db_session: Session, context: RequestContext):
        self.session = db_session
        self.tenant_id = context.tenant_id  # Auto-filter in all queries

    def get_artifact(self, id: str) -> ArtifactDTO:
        return session.query(Artifact)
            .filter(Artifact.id == id, Artifact.tenant_id == self.tenant_id)
            .one()

    # ... all methods auto-filter by tenant_id
```

### New API Endpoint (for enterprise deployment)
```
GET /api/v1/artifacts/{id}/download
  ← {
    "artifact": ArtifactDTO,
    "files": [
      {
        "path": "commands/review.md",
        "content": "...",
        "size": 1024
      },
      ...
    ],
    "total_size": 10240
  }
```

## Testing Considerations

### Current Test Gaps
- Routers require real filesystem + SQLite DB
- No mocking support without repository abstraction
- Integration tests are slow and brittle

### Post-PRD 1 Testing
```python
# Mock repository injections
mock_artifact_repo = MagicMock(spec=IArtifactRepository)
mock_artifact_repo.list.return_value = [artifact_dto_1, artifact_dto_2]

# Inject into test client
test_client = TestClient(app)
test_client.app.dependency_overrides[IArtifactRepository] = lambda: mock_artifact_repo

# Test without filesystem/DB
response = test_client.get("/artifacts")
assert response.status_code == 200
```

### Enterprise DB Testing
```python
# Use test database with tenant_id scoping
@pytest.fixture
def enterprise_repo(test_session, test_context):
    return EnterpriseArtifactRepository(test_session, test_context)

def test_enterprise_isolation(enterprise_repo):
    # Create artifacts in different tenants
    tenant_a_artifacts = enterprise_repo.list()  # Only sees tenant_a
    assert all(a.tenant_id == "tenant_a" for a in tenant_a_artifacts)
```

## Migration Path (Local → Enterprise)

### Phase 1: Generate Artifact Metadata
```bash
skillmeat enterprise export --output artifacts.json
```

### Phase 2: Authenticate
```bash
skillmeat config set enterprise-api-key <PAT>
skillmeat config set enterprise-db-url postgresql://...
```

### Phase 3: Push to Cloud
```bash
skillmeat enterprise migrate \
  --input artifacts.json \
  --target-tenant production-org \
  --dry-run
```

### Phase 4: Verify & Cleanup
```bash
skillmeat enterprise verify
skillmeat enterprise cleanup --local-after-success
```

## Rollback Strategy

Enterprise DB doesn't replace filesystem — it augments it:
- Local filesystem remains source of truth for CLI
- Enterprise DB becomes source for web UI only
- Bidirectional sync available during transition
- Rollback: Disable enterprise DB endpoint, revert to filesystem

## Compliance & Security

- Multi-tenant isolation via `tenant_id` filters
- No cross-tenant data leakage (database level)
- Audit logging on all data access (RequestContext)
- Encryption at rest (database provider feature)
- GDPR compliance: tenant data deletion cascade
