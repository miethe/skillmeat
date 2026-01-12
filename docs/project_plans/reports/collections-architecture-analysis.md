# Collections Architecture Analysis Report

**Date**: 2026-01-11
**Scope**: Artifact management across Upstream, Collection, and Project levels
**Status**: Comprehensive analysis complete

---

## Executive Summary

SkillMeat implements a **three-tier artifact management architecture** that separates concerns between external sources (Upstream), centralized user storage (Collection), and deployment targets (Projects). This design enables:

- **Reproducible deployments** via version locking and content hashing
- **Flexible organization** through database-backed user collections and groups
- **Drift detection** for synchronization between tiers
- **Multiple source integrations** (GitHub, local, marketplace)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           UPSTREAM SOURCES                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   GitHub     │  │    Local     │  │  Marketplace │  │  Custom      │    │
│  │   Repos      │  │    Files     │  │   Brokers    │  │  Brokers     │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                 │                 │             │
│         └─────────────────┴─────────────────┴─────────────────┘             │
│                                    │                                         │
│                            ArtifactSource.fetch()                           │
│                                    │                                         │
│                            ┌───────▼───────┐                                │
│                            │  FetchResult  │                                │
│                            │  - path       │                                │
│                            │  - metadata   │                                │
│                            │  - sha        │                                │
│                            │  - version    │                                │
│                            └───────┬───────┘                                │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          USER COLLECTION                                     │
│                      (~/.skillmeat/collection/)                             │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  collection.toml (Manifest)                                          │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐│   │
│  │  │ [[artifacts]]                                                    ││   │
│  │  │ name = "canvas-design"                                           ││   │
│  │  │ type = "skill"                                                   ││   │
│  │  │ upstream = "anthropics/skills/canvas-design"                     ││   │
│  │  │ resolved_sha = "abc123..."                                       ││   │
│  │  │ version_spec = "latest"                                          ││   │
│  │  └─────────────────────────────────────────────────────────────────┘│   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  collection.lock (Version Lock)                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐│   │
│  │  │ [lock.entries."canvas-design::skill"]                            ││   │
│  │  │ content_hash = "sha256:..."                                      ││   │
│  │  │ resolved_sha = "abc123..."                                       ││   │
│  │  │ resolved_version = "v2.1.0"                                      ││   │
│  │  │ fetched = "2026-01-11T12:00:00Z"                                 ││   │
│  │  └─────────────────────────────────────────────────────────────────┘│   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────┐        │
│  │  artifacts/                                                     │        │
│  │  ├── skills/          ← Artifact files organized by type       │        │
│  │  │   └── canvas-design/                                         │        │
│  │  │       ├── SKILL.md                                           │        │
│  │  │       └── supporting-files/                                  │        │
│  │  ├── commands/                                                  │        │
│  │  ├── agents/                                                    │        │
│  │  ├── mcp/                                                       │        │
│  │  └── hooks/                                                     │        │
│  └────────────────────────────────────────────────────────────────┘        │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────┐        │
│  │  Database Layer (SQLite)                                        │        │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │        │
│  │  │ Collection   │  │    Group     │  │ Artifact     │          │        │
│  │  │ (user-made)  │◄─┤ (organizer)  │  │ (cache)      │          │        │
│  │  └──────────────┘  └──────────────┘  └──────────────┘          │        │
│  └────────────────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                          DeploymentManager.deploy()
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PROJECT                                         │
│                         (any directory with .claude/)                        │
│                                                                             │
│  project-root/                                                              │
│  └── .claude/                                                               │
│      ├── .skillmeat-deployed.toml   ← Deployment tracking                   │
│      │   ┌─────────────────────────────────────────────────────────────┐   │
│      │   │ [[deployed]]                                                 │   │
│      │   │ artifact_name = "canvas-design"                              │   │
│      │   │ artifact_type = "skill"                                      │   │
│      │   │ from_collection = "default"                                  │   │
│      │   │ deployed_at = "2026-01-11T..."                               │   │
│      │   │ content_hash = "sha256:..."                                  │   │
│      │   │ merge_base_snapshot = "..."   ← For 3-way drift resolution  │   │
│      │   └─────────────────────────────────────────────────────────────┘   │
│      │                                                                      │
│      ├── .skillmeat-project.toml    ← Optional project metadata            │
│      │                                                                      │
│      ├── skills/                    ← Deployed artifacts by type           │
│      │   └── canvas-design/                                                 │
│      ├── commands/                                                          │
│      └── settings.json              ← Claude Code configuration            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tier 1: Upstream Sources

### Purpose
External repositories and sources from which artifacts are fetched into the user's collection.

### Supported Source Types

| Source | Module | Spec Format | Version Support |
|--------|--------|-------------|-----------------|
| **GitHub** | `skillmeat/sources/github.py` | `user/repo/path[@version]` | Tags, SHAs, branches, "latest" |
| **Local** | `skillmeat/sources/local.py` | Filesystem path | None (development use) |
| **Marketplace** | `skillmeat/marketplace/brokers/` | Broker-specific | Varies by marketplace |

### Key Classes

```python
# skillmeat/sources/base.py
class ArtifactSource(ABC):
    def fetch(spec: str, artifact_type: ArtifactType) -> FetchResult
    def check_updates(artifact: Artifact) -> Optional[UpdateInfo]
    def validate(path: Path, artifact_type: ArtifactType) -> bool

@dataclass
class FetchResult:
    artifact_path: Path           # Temp dir with artifact content
    metadata: ArtifactMetadata    # Extracted metadata
    resolved_sha: Optional[str]   # Concrete commit SHA
    resolved_version: Optional[str]  # Tag name if applicable
    upstream_url: Optional[str]   # Source URL for traceability

# skillmeat/sources/github.py
class ArtifactSpec:
    """Parser for 'user/repo/path[@version]' format"""
    @classmethod
    def parse(cls, spec: str) -> 'ArtifactSpec'

class GitHubClient:
    """GitHub API interactions with retry logic"""
    def resolve_version(spec: ArtifactSpec) -> Tuple[str, Optional[str]]
    def fetch_artifact(spec: ArtifactSpec) -> FetchResult
```

### Version Resolution Flow (GitHub)

1. **Parse spec**: `anthropics/skills/canvas@v2.0` → `ArtifactSpec(user, repo, path, version)`
2. **Resolve version**:
   - `latest` → Query default branch, get HEAD SHA
   - `v2.0` → Query `/git/ref/tags/v2.0`, extract SHA
   - `abc123` → Validate via `/commits/abc123`
3. **Clone and checkout**: Shallow clone → checkout SHA
4. **Validate structure**: Ensure SKILL.md/COMMAND.md exists
5. **Extract metadata**: Parse frontmatter, build `FetchResult`

### Update Checking

```python
# Check if upstream has newer version
update_info = github_source.check_updates(artifact)
if update_info.has_update:
    print(f"Update available: {update_info.current_sha} → {update_info.latest_sha}")
```

---

## Tier 2: User Collection

### Purpose
Centralized storage for all artifacts the user has imported, with organizational features.

### Storage Location
```
~/.skillmeat/collection/
├── collection.toml      # Manifest (artifact metadata)
├── collection.lock      # Version locks (reproducibility)
├── snapshots/           # Version history
└── artifacts/           # Artifact files
    ├── skills/
    ├── commands/
    ├── agents/
    ├── mcp/
    └── hooks/
```

### Two-Layer Architecture

#### Layer 1: File-Based (Primary Storage)

**Manifest** (`collection.toml`):
```toml
[collection]
version = "1.0.0"
created_at = "2026-01-01T00:00:00Z"

[[artifacts]]
name = "canvas-design"
type = "skill"
upstream = "anthropics/skills/canvas-design"
resolved_sha = "abc123def456..."
resolved_version = "v2.1.0"
version_spec = "latest"
origin = "github"
```

**Lock File** (`collection.lock`):
```toml
[lock]
version = "1.0.0"

[lock.entries."canvas-design::skill"]
upstream = "https://github.com/anthropics/skills/tree/abc123/canvas-design"
resolved_sha = "abc123def456..."
resolved_version = "v2.1.0"
content_hash = "sha256:xyz789..."
fetched = "2026-01-11T12:34:56Z"
```

**Key Classes**:
```python
# skillmeat/core/collection.py
@dataclass
class Collection:
    artifacts: List[Artifact]
    created_at: datetime
    updated_at: datetime

class CollectionManager:
    def add_artifact(spec: str, artifact_type: ArtifactType) -> Artifact
    def remove_artifact(name: str, artifact_type: ArtifactType) -> bool
    def list_artifacts(artifact_type: Optional[ArtifactType]) -> List[Artifact]
    def get_artifact(name: str, artifact_type: ArtifactType) -> Optional[Artifact]

# skillmeat/storage/manifest.py
class ManifestManager:
    def read() -> Collection
    def write(collection: Collection) -> None
    def create_empty() -> Collection

# skillmeat/storage/lockfile.py
@dataclass
class LockEntry:
    upstream: str
    resolved_sha: Optional[str]
    resolved_version: Optional[str]
    content_hash: str
    fetched: datetime

class LockManager:
    def read() -> Dict[str, LockEntry]
    def update_entry(key: str, entry: LockEntry) -> None
```

#### Layer 2: Database (Organizational)

User-created collections for organizing artifacts into logical groups.

**Models** (`skillmeat/cache/models.py`):

```python
class Collection(Base):
    """User-created organizational collection"""
    id: int
    name: str
    description: Optional[str]
    source_type: str  # 'file' | 'user' | 'marketplace'
    collection_path: Optional[str]
    created_at: datetime
    groups: List[Group]  # Nested organization

class Group(Base):
    """Custom grouping within a collection"""
    id: int
    name: str
    collection_id: int
    parent_id: Optional[int]  # Nested groups
    artifacts: List[GroupArtifact]

class CollectionArtifact(Base):
    """Association table for collection membership"""
    collection_id: int
    artifact_id: Optional[int]
    source_link: Optional[str]  # External reference
    content_hash: Optional[str]  # For matching
```

**Membership Matching Priority**:
1. Exact `source_link` match
2. `content_hash` match (same content, different source)
3. `name + type` match
4. No match

### API Endpoints

| Operation | Endpoint | Method | Layer |
|-----------|----------|--------|-------|
| List collections | `/api/v1/collections` | GET | File (read-only) |
| List user collections | `/api/v1/user-collections` | GET | Database |
| Create collection | `/api/v1/user-collections` | POST | Database |
| Get collection | `/api/v1/user-collections/{id}` | GET | Database |
| Update collection | `/api/v1/user-collections/{id}` | PUT | Database |
| Delete collection | `/api/v1/user-collections/{id}` | DELETE | Database |
| List artifacts | `/api/v1/user-collections/{id}/artifacts` | GET | Database |
| Add artifact | `/api/v1/user-collections/{id}/artifacts` | POST | Database |
| Remove artifact | `/api/v1/user-collections/{id}/artifacts/{aid}` | DELETE | Database |

---

## Tier 3: Project

### Purpose
Deployment targets where artifacts are actually used (`.claude/` directories in codebases).

### Project Definition

A "project" is any directory containing a `.claude/` subdirectory:
```
my-project/
└── .claude/
    ├── .skillmeat-deployed.toml  # Deployment tracking (required for management)
    ├── .skillmeat-project.toml   # Project metadata (optional)
    ├── settings.json             # Claude Code configuration
    ├── skills/                   # Deployed skills
    ├── commands/                 # Deployed commands
    └── rules/                    # Deployed rules
```

### Deployment Metadata

**`.skillmeat-deployed.toml`**:
```toml
[[deployed]]
artifact_name = "canvas-design"
artifact_type = "skill"
from_collection = "default"
deployed_at = "2026-01-11T14:30:00Z"
artifact_path = "skills/canvas-design"
content_hash = "sha256:abc123..."
version_lineage = ["sha256:abc123..."]  # History for rollback
merge_base_snapshot = "snap_abc123"      # For 3-way merge
```

### Key Classes

```python
# skillmeat/core/deployment.py
class DeploymentManager:
    def deploy(artifact: Artifact, project_path: Path, scope: str) -> DeploymentResult
    def undeploy(artifact_name: str, artifact_type: str, project_path: Path) -> bool
    def list_deployments(project_path: Path) -> List[DeployedArtifact]
    def get_deployment(name: str, type: str, project_path: Path) -> Optional[DeployedArtifact]

# skillmeat/storage/deployment.py
class DeploymentTracker:
    def read(project_path: Path) -> List[DeployedArtifact]
    def write(project_path: Path, deployments: List[DeployedArtifact]) -> None
    def add_deployment(project_path: Path, deployment: DeployedArtifact) -> None
    def remove_deployment(project_path: Path, name: str, type: str) -> bool

# skillmeat/api/project_registry.py
class ProjectRegistry:
    """Discovers and caches projects across filesystem"""
    def discover_projects() -> List[ProjectInfo]  # Cached 5-min TTL
    def get_project(path: Path) -> Optional[ProjectInfo]
```

### Artifact Scopes

| Scope | Location | Visibility | Use Case |
|-------|----------|------------|----------|
| `user` | `~/.claude/skills/user/` | All projects | Shared utilities |
| `local` | `./.claude/skills/` | Single project | Project-specific |

### API Endpoints

| Operation | Endpoint | Method |
|-----------|----------|--------|
| Deploy artifact | `/api/v1/deploy` | POST |
| Undeploy artifact | `/api/v1/deploy/undeploy` | POST |
| List deployments | `/api/v1/deploy` | GET |
| List projects | `/api/v1/projects` | GET |
| Get project | `/api/v1/projects/{path}` | GET |
| Check drift | `/api/v1/projects/{path}/drift` | GET |

---

## Cross-Tier Operations

### Sync (Collection ↔ Project)

**Drift Detection** (`skillmeat/core/sync.py`):

Three-way comparison:
- **Baseline**: Content hash at deployment time
- **Collection**: Current artifact in collection
- **Project**: Current artifact in project

**Drift Types**:
| Type | Collection Changed | Project Changed | Recommendation |
|------|-------------------|-----------------|----------------|
| `outdated` | Yes | No | Pull from collection |
| `modified` | No | Yes | Push to collection |
| `conflict` | Yes | Yes | Manual review |
| `added` | N/A | N/A | Deploy to project |
| `removed` | N/A | N/A | Remove from project |

**Sync Strategies**:
```python
class SyncManager:
    def check_drift(project_path: Path) -> List[DriftDetectionResult]
    def sync_from_project(project_path: Path, strategy: str) -> SyncResult
    # Strategies: "overwrite", "merge", "fork", "prompt"
```

### Update Flow (Upstream → Collection → Project)

```
1. Check for updates
   github_source.check_updates(artifact) → UpdateInfo

2. Update collection
   collection_manager.update_artifact(artifact.name, artifact.type)
   lock_manager.update_entry(key, new_lock_entry)

3. Detect drift in projects
   sync_manager.check_drift(project_path) → [DriftDetectionResult]

4. Apply updates to project
   deployment_manager.deploy(updated_artifact, project_path, scope)
```

---

## Data Flow Summary

```
┌──────────────────────────────────────────────────────────────────────┐
│                         ADD ARTIFACT FLOW                             │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  User: skillmeat add anthropics/skills/canvas@latest                 │
│                            │                                          │
│                            ▼                                          │
│  ┌─────────────────────────────────────────────────┐                 │
│  │ 1. Parse spec → ArtifactSpec                    │                 │
│  │ 2. Resolve version → SHA abc123                 │  GitHubSource   │
│  │ 3. Clone repo (shallow)                         │                 │
│  │ 4. Checkout SHA                                 │                 │
│  │ 5. Validate structure                           │                 │
│  │ 6. Extract metadata                             │                 │
│  └─────────────────────────────────────────────────┘                 │
│                            │                                          │
│                            ▼ FetchResult                              │
│  ┌─────────────────────────────────────────────────┐                 │
│  │ 1. Copy to ~/.skillmeat/collection/artifacts/   │                 │
│  │ 2. Update collection.toml                       │ CollectionMgr   │
│  │ 3. Update collection.lock                       │                 │
│  │ 4. Create snapshot (optional)                   │                 │
│  └─────────────────────────────────────────────────┘                 │
│                            │                                          │
│                            ▼ Artifact in collection                   │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                         DEPLOY ARTIFACT FLOW                          │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  User: skillmeat deploy canvas-design --project /path/to/proj        │
│                            │                                          │
│                            ▼                                          │
│  ┌─────────────────────────────────────────────────┐                 │
│  │ 1. Look up artifact in collection               │                 │
│  │ 2. Determine target path based on scope         │ DeploymentMgr   │
│  │ 3. Copy artifact files to .claude/skills/       │                 │
│  │ 4. Record deployment in .skillmeat-deployed.toml│                 │
│  │ 5. Calculate content hash for drift detection   │                 │
│  └─────────────────────────────────────────────────┘                 │
│                            │                                          │
│                            ▼ Artifact deployed to project             │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                           SYNC FLOW                                   │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  User: skillmeat sync --project /path/to/proj                        │
│                            │                                          │
│                            ▼                                          │
│  ┌─────────────────────────────────────────────────┐                 │
│  │ For each deployed artifact:                     │                 │
│  │ 1. Read deployment baseline (content_hash)      │                 │
│  │ 2. Calculate current project hash               │  SyncManager    │
│  │ 3. Calculate current collection hash            │                 │
│  │ 4. Compare: baseline vs project vs collection   │                 │
│  │ 5. Classify drift type                          │                 │
│  │ 6. Apply sync strategy                          │                 │
│  └─────────────────────────────────────────────────┘                 │
│                            │                                          │
│                            ▼ DriftDetectionResult[]                   │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

### 1. Single Manifest vs Per-Artifact Files

**Decision**: Single `collection.toml` manifest

**Rationale**:
- Atomic consistency (single file update)
- Fast sequential reads
- Simpler version tracking
- Smaller file count

**Trade-off**: Larger manifest file for large collections (mitigated by TOML efficiency)

### 2. Composite Keys for Artifacts

**Pattern**: `name::type` (e.g., `canvas-design::skill`)

**Rationale**:
- Same name can exist for different artifact types
- Simple string key for lookups
- Clear in logs and debugging

### 3. Content Hash for Drift Detection

**Pattern**: SHA-256 of artifact content (not file metadata)

**Rationale**:
- Detects modifications regardless of timestamps
- Works across platforms
- Independent of version control

### 4. Lock File Separation

**Pattern**: Separate `collection.lock` from manifest

**Rationale**:
- Manifest is user-editable (version specs)
- Lock file is machine-managed (exact versions)
- Clear separation of intent vs resolution

### 5. Database for Organization, Files for Storage

**Pattern**: Database layer for user collections, file layer for artifact storage

**Rationale**:
- File system is authoritative for artifact content
- Database enables fast queries, relationships, groups
- Decouples organization from storage

---

## Security Considerations

| Area | Implementation |
|------|----------------|
| **GitHub Auth** | Optional token via env var (`GITHUB_TOKEN`) |
| **Content Validation** | Artifacts validated before installation |
| **Atomic Writes** | Temp file → fsync → atomic rename |
| **Signature Validation** | Framework for marketplace bundles |
| **Permission Warnings** | Pre-install review (skip with `--dangerously-skip-permissions`) |

---

## Performance Characteristics

| Operation | Typical Time | Notes |
|-----------|-------------|-------|
| Collection load | <50ms | Single file read |
| Artifact lookup | O(n) | Linear scan, n = artifact count |
| Database query | <10ms | Indexed lookups |
| Project discovery | 5-30s uncached, <50ms cached | 5-min TTL |
| GitHub fetch | 2-10s | Shallow clone + checkout |
| Drift detection | O(n*m) | n = projects, m = deployments |

---

## File Reference

| Component | Primary File | Key Classes |
|-----------|-------------|-------------|
| **GitHub Source** | `skillmeat/sources/github.py` | `GitHubSource`, `GitHubClient`, `ArtifactSpec` |
| **Local Source** | `skillmeat/sources/local.py` | `LocalSource` |
| **Collection Core** | `skillmeat/core/collection.py` | `Collection`, `CollectionManager` |
| **Artifact Model** | `skillmeat/core/artifact.py` | `Artifact`, `ArtifactMetadata` |
| **Manifest Storage** | `skillmeat/storage/manifest.py` | `ManifestManager` |
| **Lock Storage** | `skillmeat/storage/lockfile.py` | `LockManager`, `LockEntry` |
| **Deployment Core** | `skillmeat/core/deployment.py` | `DeploymentManager` |
| **Deployment Storage** | `skillmeat/storage/deployment.py` | `DeploymentTracker` |
| **Sync System** | `skillmeat/core/sync.py` | `SyncManager` |
| **DB Models** | `skillmeat/cache/models.py` | `Collection`, `Group`, `CollectionArtifact` |
| **Collection Router** | `skillmeat/api/routers/user_collections.py` | Router endpoints |
| **Deployment Router** | `skillmeat/api/routers/deployments.py` | Router endpoints |
| **Project Registry** | `skillmeat/api/project_registry.py` | `ProjectRegistry` |

---

## Related Documentation

- **Context Files** (auto-generated by exploration):
  - `.claude/context/collection-architecture.md`
  - `.claude/context/collection-patterns.md`
  - `.claude/context/collection-quick-reference.md`
  - `.claude/context/project-artifact-management.md`
  - `.claude/context/project-management-quick-ref.md`
  - `.claude/context/projects-index.md`

- **API Reference**: `/api/v1/docs` (OpenAPI)

- **Architecture Specs**: `docs/project_plans/design-specs/`
