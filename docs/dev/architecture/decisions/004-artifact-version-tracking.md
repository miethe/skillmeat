# Decision: Artifact Version Tracking and Visualization

**Status**: Approved
**Date**: 2025-11-20
**Decider**: Lead Architect

## Context

SkillMeat needs to track when artifacts deployed to projects are modified locally, visualize version relationships between collection artifacts and their deployed instances, and support multiple modified versions of the same artifact across different projects.

### Current State

- Deployments tracked in `.skillmeat-deployed.toml` with basic metadata
- `collection_sha` field stores content hash at deployment time
- `local_modifications` boolean flag exists but is not consistently updated
- No system to track parent-child relationships between collection artifacts and project instances
- No visualization of version graphs or modification history
- No way to query "which projects have modified versions of artifact X"

### Requirements

1. Track when a deployed artifact is modified locally in a project
2. Link modified local versions to their parent artifact in collection
3. Visualize version relationships (parent to modified instances)
4. Show modification status in both Collection and Project views
5. Support multiple modified versions of the same artifact across different projects
6. Detect modifications automatically (content hash comparison)
7. Provide API endpoints for version graph queries
8. Enable frontend visualization of version trees

## Decision

**Implement a version tracking system using content hashing and relational metadata.**

### Data Model

#### 1. Enhanced Deployment Record

Extend existing `Deployment` model in `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/deployment.py`:

```python
@dataclass
class Deployment:
    """Tracks artifact deployment to a project with version tracking."""

    # Existing fields
    artifact_name: str
    artifact_type: str
    from_collection: str
    deployed_at: datetime
    artifact_path: Path
    collection_sha: str
    local_modifications: bool

    # NEW: Version tracking fields
    parent_collection_path: Optional[str] = None  # Absolute path to parent in collection
    deployed_sha: str = None  # SHA at deployment time (rename from collection_sha for clarity)
    current_sha: Optional[str] = None  # Current SHA (computed on demand)
    last_modification_check: Optional[datetime] = None
    modification_detected_at: Optional[datetime] = None
    version_lineage: List[str] = field(default_factory=list)  # History of SHAs
```

#### 2. New ArtifactVersion Model

Create new model in `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/models.py`:

```python
@dataclass
class ArtifactVersion:
    """Represents a specific version of an artifact at a point in time."""

    artifact_name: str
    artifact_type: str  # ArtifactType.value
    content_sha: str  # SHA-256 hash of all content
    location: str  # "collection" or absolute project path
    location_type: Literal["collection", "project"]
    collection_name: Optional[str] = None  # Source collection
    parent_sha: Optional[str] = None  # SHA of parent version (if deployed from collection)
    created_at: datetime = field(default_factory=datetime.now)
    metadata_snapshot: Optional[Dict[str, Any]] = None

    def is_modified(self) -> bool:
        """Check if this version differs from its parent."""
        return self.parent_sha is not None and self.parent_sha != self.content_sha


@dataclass
class VersionGraphNode:
    """Node in the artifact version graph."""

    artifact_name: str
    artifact_type: str
    version: ArtifactVersion
    children: List["VersionGraphNode"] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_collection_root(self) -> bool:
        """True if this is the canonical collection version."""
        return self.version.location_type == "collection"

    @property
    def is_modified(self) -> bool:
        """True if content differs from parent."""
        return self.version.is_modified()

    @property
    def modification_count(self) -> int:
        """Count of modified children (recursive)."""
        count = 0
        for child in self.children:
            if child.is_modified:
                count += 1
            count += child.modification_count
        return count


@dataclass
class VersionGraph:
    """Complete version graph for an artifact across all projects."""

    artifact_name: str
    artifact_type: str
    root: Optional[VersionGraphNode] = None  # Collection version (canonical)
    orphaned_nodes: List[VersionGraphNode] = field(default_factory=list)  # No parent in collection
    total_deployments: int = 0
    modified_count: int = 0
    last_updated: datetime = field(default_factory=datetime.now)

    def get_all_nodes(self) -> List[VersionGraphNode]:
        """Flatten graph to list of all nodes."""
        nodes = []
        if self.root:
            nodes.extend(self._traverse(self.root))
        nodes.extend(self.orphaned_nodes)
        return nodes

    def _traverse(self, node: VersionGraphNode) -> List[VersionGraphNode]:
        """Recursively traverse graph."""
        result = [node]
        for child in node.children:
            result.extend(self._traverse(child))
        return result
```

### Storage Strategy

#### Option A: TOML Storage (Chosen for MVP)

Store in existing `.skillmeat-deployed.toml` with enhanced fields:

```toml
[[deployed]]
artifact_name = "pdf-processor"
artifact_type = "skill"
from_collection = "default"
deployed_at = "2025-11-20T10:30:00Z"
artifact_path = "skills/pdf-processor"
deployed_sha = "abc123def456..."
current_sha = "def789ghi012..."  # Updated on modification check
local_modifications = true
modification_detected_at = "2025-11-20T15:45:00Z"
last_modification_check = "2025-11-20T16:00:00Z"
parent_collection_path = "/Users/me/.skillmeat/collections/default/skills/pdf-processor"

[[deployed.version_lineage]]
sha = "abc123def456..."
timestamp = "2025-11-20T10:30:00Z"
note = "Initial deployment"

[[deployed.version_lineage]]
sha = "def789ghi012..."
timestamp = "2025-11-20T15:45:00Z"
note = "Local modifications detected"
```

**Pros:**
- No new storage mechanism
- Human-readable
- Easy migration path
- No additional dependencies

**Cons:**
- Limited query capabilities
- Must scan all projects to build version graph

#### Option B: SQLite Database (Future Enhancement)

Store in `~/.skillmeat/version_tracking.db`:

```sql
CREATE TABLE artifact_versions (
    id INTEGER PRIMARY KEY,
    artifact_name TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    content_sha TEXT NOT NULL,
    location TEXT NOT NULL,
    location_type TEXT CHECK(location_type IN ('collection', 'project')),
    collection_name TEXT,
    parent_sha TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata_json TEXT,
    UNIQUE(artifact_name, artifact_type, location, content_sha)
);

CREATE INDEX idx_artifact_lookup ON artifact_versions(artifact_name, artifact_type);
CREATE INDEX idx_parent_lookup ON artifact_versions(parent_sha);
CREATE INDEX idx_modified ON artifact_versions(parent_sha) WHERE parent_sha IS NOT NULL;
```

**Pros:**
- Fast queries
- Relational integrity
- Efficient joins for version graphs
- Better scalability

**Cons:**
- New dependency
- More complex migration
- Less transparent to users

**Decision:** Use TOML for MVP (Phase 2), migrate to SQLite in Phase 3 if performance requires.

### Modification Detection

#### Automatic Detection

Implement in `DeploymentTracker.detect_modifications()`:

```python
@staticmethod
def compute_deployment_hash(project_path: Path, deployment: Deployment) -> str:
    """Compute current content hash for deployed artifact."""
    artifact_path = project_path / ".claude" / deployment.artifact_path
    return compute_content_hash(artifact_path)

@staticmethod
def check_and_update_modifications(project_path: Path) -> List[Deployment]:
    """Check all deployments for modifications and update flags."""
    deployments = DeploymentTracker.read_deployments(project_path)
    updated = []

    for deployment in deployments:
        current_sha = DeploymentTracker.compute_deployment_hash(project_path, deployment)

        if current_sha != deployment.deployed_sha:
            # Modification detected
            if not deployment.local_modifications:
                deployment.local_modifications = True
                deployment.modification_detected_at = datetime.now()
            deployment.current_sha = current_sha
            deployment.last_modification_check = datetime.now()
            updated.append(deployment)
        else:
            # No modifications
            if deployment.local_modifications:
                # Previously modified, now restored
                deployment.local_modifications = False
                deployment.modification_detected_at = None
            deployment.current_sha = current_sha
            deployment.last_modification_check = datetime.now()

    if updated:
        DeploymentTracker.write_deployments(project_path, deployments)

    return updated
```

#### Trigger Points

1. **On API read**: Background task checks modifications when project details requested
2. **CLI commands**: `skillmeat status`, `skillmeat sync --check`
3. **Periodic background job**: Optional daemon mode (Phase 3)
4. **Manual trigger**: API endpoint `/projects/{id}/check-modifications`

### Version Graph Construction

#### VersionGraphBuilder Service

Create new service in `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/version_tracker.py`:

```python
class VersionGraphBuilder:
    """Builds version graphs for artifacts across collections and projects."""

    def __init__(self, collection_mgr: CollectionManager):
        self.collection_mgr = collection_mgr

    def build_graph(
        self,
        artifact_name: str,
        artifact_type: ArtifactType,
        collection_name: Optional[str] = None
    ) -> VersionGraph:
        """Build complete version graph for an artifact."""

        # 1. Find canonical version in collection
        root_node = self._find_collection_version(
            artifact_name, artifact_type, collection_name
        )

        # 2. Discover all projects
        project_paths = self._discover_projects()

        # 3. Build child nodes for each deployment
        for project_path in project_paths:
            deployments = DeploymentTracker.read_deployments(project_path)
            for deployment in deployments:
                if (deployment.artifact_name == artifact_name and
                    deployment.artifact_type == artifact_type.value):
                    child_node = self._build_project_node(project_path, deployment)
                    if root_node:
                        root_node.children.append(child_node)

        # 4. Compute statistics
        graph = VersionGraph(
            artifact_name=artifact_name,
            artifact_type=artifact_type.value,
            root=root_node,
            total_deployments=len(root_node.children) if root_node else 0,
            modified_count=root_node.modification_count if root_node else 0
        )

        return graph

    def _find_collection_version(
        self,
        artifact_name: str,
        artifact_type: ArtifactType,
        collection_name: Optional[str]
    ) -> Optional[VersionGraphNode]:
        """Find artifact in collection."""
        # Implementation searches collection for artifact
        pass

    def _build_project_node(
        self,
        project_path: Path,
        deployment: Deployment
    ) -> VersionGraphNode:
        """Build node for deployed artifact."""
        artifact_path = project_path / ".claude" / deployment.artifact_path
        current_sha = compute_content_hash(artifact_path)

        version = ArtifactVersion(
            artifact_name=deployment.artifact_name,
            artifact_type=deployment.artifact_type,
            content_sha=current_sha,
            location=str(project_path),
            location_type="project",
            collection_name=deployment.from_collection,
            parent_sha=deployment.deployed_sha,
            created_at=deployment.deployed_at
        )

        return VersionGraphNode(
            artifact_name=deployment.artifact_name,
            artifact_type=deployment.artifact_type,
            version=version,
            metadata={
                "project_path": str(project_path),
                "project_name": project_path.name,
                "deployed_at": deployment.deployed_at,
                "is_modified": current_sha != deployment.deployed_sha
            }
        )
```

## API Contracts

### New Endpoints

#### 1. Check Project Modifications

```
POST /api/v1/projects/{project_id}/check-modifications
```

**Response:**
```json
{
  "project_id": "abc123",
  "checked_at": "2025-11-20T16:00:00Z",
  "modifications_detected": 3,
  "deployments": [
    {
      "artifact_name": "pdf-processor",
      "artifact_type": "skill",
      "deployed_sha": "abc123",
      "current_sha": "def456",
      "is_modified": true,
      "modification_detected_at": "2025-11-20T15:45:00Z"
    }
  ]
}
```

#### 2. Get Artifact Version Graph

```
GET /api/v1/artifacts/{artifact_id}/version-graph?collection={name}
```

**Response:**
```json
{
  "artifact_name": "pdf-processor",
  "artifact_type": "skill",
  "collection_version": {
    "sha": "abc123",
    "location": "collection",
    "collection_name": "default"
  },
  "deployments": [
    {
      "project_path": "/Users/me/project1",
      "project_name": "project1",
      "deployed_at": "2025-11-20T10:30:00Z",
      "deployed_sha": "abc123",
      "current_sha": "def456",
      "is_modified": true,
      "modification_detected_at": "2025-11-20T15:45:00Z"
    },
    {
      "project_path": "/Users/me/project2",
      "project_name": "project2",
      "deployed_at": "2025-11-19T14:20:00Z",
      "deployed_sha": "abc123",
      "current_sha": "abc123",
      "is_modified": false
    }
  ],
  "statistics": {
    "total_deployments": 2,
    "modified_count": 1,
    "unmodified_count": 1
  }
}
```

#### 3. Get All Modified Artifacts

```
GET /api/v1/projects/{project_id}/modified-artifacts
```

**Response:**
```json
{
  "project_id": "abc123",
  "modified_artifacts": [
    {
      "artifact_name": "pdf-processor",
      "artifact_type": "skill",
      "deployed_sha": "abc123",
      "current_sha": "def456",
      "modification_detected_at": "2025-11-20T15:45:00Z"
    }
  ],
  "total_count": 1
}
```

#### 4. Enhanced Artifact Response

Update `ArtifactResponse` schema to include deployment statistics:

```json
{
  "id": "skill:pdf-processor",
  "name": "pdf-processor",
  "type": "skill",
  "deployment_stats": {
    "total_deployments": 5,
    "modified_deployments": 2,
    "projects": [
      {
        "project_name": "project1",
        "is_modified": true
      },
      {
        "project_name": "project2",
        "is_modified": false
      }
    ]
  }
}
```

### Enhanced Schemas

Create in `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/versions.py`:

```python
class ArtifactVersionInfo(BaseModel):
    """Version information for a single artifact instance."""

    artifact_name: str
    artifact_type: str
    location: str  # "collection" or project path
    location_type: Literal["collection", "project"]
    content_sha: str
    parent_sha: Optional[str] = None
    is_modified: bool
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VersionGraphNodeResponse(BaseModel):
    """Node in version graph visualization."""

    id: str  # Unique node ID (sha or location-based)
    artifact_name: str
    artifact_type: str
    version_info: ArtifactVersionInfo
    children: List["VersionGraphNodeResponse"] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VersionGraphResponse(BaseModel):
    """Complete version graph for an artifact."""

    artifact_name: str
    artifact_type: str
    root: Optional[VersionGraphNodeResponse] = None
    statistics: Dict[str, Any]
    last_updated: datetime


class ModificationCheckResponse(BaseModel):
    """Response from modification check operation."""

    project_id: str
    checked_at: datetime
    modifications_detected: int
    deployments: List[DeploymentModificationStatus]


class DeploymentModificationStatus(BaseModel):
    """Modification status for a single deployment."""

    artifact_name: str
    artifact_type: str
    deployed_sha: str
    current_sha: str
    is_modified: bool
    modification_detected_at: Optional[datetime] = None
```

## Frontend State Management

### React Query Cache Structure

```typescript
// Query keys
const versionKeys = {
  all: ['versions'] as const,
  graphs: () => [...versionKeys.all, 'graphs'] as const,
  graph: (artifactId: string, collection?: string) =>
    [...versionKeys.graphs(), artifactId, collection] as const,
  modifications: () => [...versionKeys.all, 'modifications'] as const,
  projectModifications: (projectId: string) =>
    [...versionKeys.modifications(), projectId] as const,
}

// Hooks
function useVersionGraph(artifactId: string, collection?: string) {
  return useQuery({
    queryKey: versionKeys.graph(artifactId, collection),
    queryFn: () => fetchVersionGraph(artifactId, collection),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

function useProjectModifications(projectId: string) {
  return useQuery({
    queryKey: versionKeys.projectModifications(projectId),
    queryFn: () => fetchProjectModifications(projectId),
    staleTime: 1 * 60 * 1000, // 1 minute
  })
}

function useCheckModifications(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => checkProjectModifications(projectId),
    onSuccess: () => {
      // Invalidate related queries
      queryClient.invalidateQueries({
        queryKey: versionKeys.projectModifications(projectId)
      })
      queryClient.invalidateQueries({
        queryKey: versionKeys.graphs()
      })
    }
  })
}
```

### Zustand Store for UI State

```typescript
interface VersionVisualizationStore {
  selectedNode: string | null
  expandedNodes: Set<string>
  highlightModified: boolean
  viewMode: 'tree' | 'list' | 'graph'

  actions: {
    selectNode: (nodeId: string | null) => void
    toggleNode: (nodeId: string) => void
    setHighlightModified: (highlight: boolean) => void
    setViewMode: (mode: 'tree' | 'list' | 'graph') => void
    reset: () => void
  }
}

const useVersionVisualizationStore = create<VersionVisualizationStore>((set) => ({
  selectedNode: null,
  expandedNodes: new Set(),
  highlightModified: true,
  viewMode: 'tree',

  actions: {
    selectNode: (nodeId) => set({ selectedNode: nodeId }),
    toggleNode: (nodeId) => set((state) => {
      const expanded = new Set(state.expandedNodes)
      if (expanded.has(nodeId)) {
        expanded.delete(nodeId)
      } else {
        expanded.add(nodeId)
      }
      return { expandedNodes: expanded }
    }),
    setHighlightModified: (highlight) => set({ highlightModified: highlight }),
    setViewMode: (mode) => set({ viewMode: mode }),
    reset: () => set({
      selectedNode: null,
      expandedNodes: new Set(),
      highlightModified: true,
      viewMode: 'tree'
    })
  }
}))
```

## Visualization Approach

### UI Components

#### 1. VersionTreeView

Visual tree showing parent-child relationships:

```
Collection: pdf-processor (abc123)
├─ [Modified] project1 (def456) - Modified 1h ago
├─ [Synced] project2 (abc123)
└─ [Modified] project3 (ghi789) - Modified 3d ago
```

**Component Structure:**
- Root node: Collection artifact
- Child nodes: Deployed instances
- Visual indicators: Modified (yellow), Synced (green), Outdated (red)
- Click to expand/collapse
- Hover for details (SHA, timestamps, diff stats)

#### 2. VersionGraphVisualization

D3.js or Vis.js network graph:
- Nodes: Artifact versions
- Edges: Parent-child relationships
- Colors: Status (synced, modified, outdated)
- Size: Number of files or total size
- Interactive: Click to view details, diff, sync

#### 3. ModificationBadge

Small indicator on artifact cards:

```
┌─────────────────────┐
│ pdf-processor       │
│ [Modified in 2/5]   │  <- Badge
└─────────────────────┘
```

#### 4. ModificationTimeline

Timeline view showing modification history:

```
2025-11-20 10:30 - Deployed to project1 (abc123)
2025-11-20 15:45 - Modified in project1 (def456)
2025-11-21 09:00 - Synced from collection (abc123)
```

## Performance Considerations

### Caching Strategy

1. **Version graphs cached in-memory** (5-minute TTL)
2. **Modification checks debounced** (max 1/minute per project)
3. **Lazy loading** (only compute graph on demand)
4. **Background updates** (optional periodic refresh)

### Scaling Limits

- Up to 100 projects: Full scan acceptable (<1s)
- 100-1000 projects: Index required (SQLite migration)
- 1000+ projects: Background indexing service

### Optimization Techniques

1. **Incremental hashing**: Only recompute changed files
2. **Parallel scanning**: Use multiprocessing for project discovery
3. **Smart diffing**: Skip unchanged files by timestamp
4. **Compression**: Store version lineage efficiently

## Migration Plan

### Phase 1: Data Model Enhancement (Week 1)

1. Extend `Deployment` dataclass with new fields
2. Add backward compatibility for existing `.skillmeat-deployed.toml`
3. Migrate existing deployments (set `deployed_sha = collection_sha`)

### Phase 2: Core Logic (Week 2)

1. Implement `VersionGraphBuilder` service
2. Implement modification detection in `DeploymentTracker`
3. Add unit tests for version tracking logic

### Phase 3: API Endpoints (Week 3)

1. Create `/api/v1/projects/{id}/check-modifications`
2. Create `/api/v1/artifacts/{id}/version-graph`
3. Enhance existing artifact endpoints with deployment stats
4. Add integration tests

### Phase 4: Frontend (Week 4)

1. Create version visualization components
2. Implement React Query hooks
3. Add Zustand store for UI state
4. Integrate with existing artifact and project views

### Phase 5: Polish & Testing (Week 5)

1. Performance testing with large project sets
2. UI/UX refinement
3. Documentation
4. Beta user testing

## Alternatives Considered

### Alternative 1: Git-based Tracking

Use Git to track modifications:
- Clone collection as Git repo
- Track deployments as Git submodules
- Use Git diff to detect changes

**Rejected:** Too heavyweight, requires Git knowledge, complex setup

### Alternative 2: File Watcher Service

Background daemon watches project directories:
- Real-time modification detection
- Push notifications to API

**Rejected:** Complex deployment, resource-intensive, overkill for MVP

### Alternative 3: Blockchain Version Ledger

Immutable version history using blockchain:
- Cryptographic proof of modifications
- Tamper-proof history

**Rejected:** Over-engineered, adds unnecessary complexity

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Performance degradation with many projects | High | Implement caching, lazy loading, background indexing |
| Storage bloat from version lineage | Medium | Limit lineage depth, compress old entries |
| Race conditions during modification checks | Medium | Use file locking, atomic updates |
| False positives (timestamp-only changes) | Low | Hash-based comparison is deterministic |
| User confusion about version status | Medium | Clear UI indicators, tooltips, documentation |

## Success Metrics

1. **Modification detection accuracy**: 99%+ correct identification
2. **Performance**: Version graph generation <500ms for 100 projects
3. **UI responsiveness**: Graph rendering <200ms
4. **User satisfaction**: 8+/10 rating for version visualization
5. **Adoption**: 70%+ of users use modification tracking within first month

## Future Enhancements

### Phase 3 (Advanced Features)

1. **Automatic sync proposals**: "Update 3 projects with modified artifact?"
2. **Diff viewer**: Show exact changes between versions
3. **Version history**: Full timeline with rollback capability
4. **Batch operations**: Sync multiple modified artifacts at once
5. **Conflict resolution**: Merge strategies for divergent versions
6. **Version tagging**: User-defined labels (v1.0, production, etc.)
7. **Export/Import**: Share version graphs between teams

### Phase 4 (Enterprise Features)

1. **Database migration**: Move to SQLite/PostgreSQL for scalability
2. **Real-time notifications**: WebSocket updates for modifications
3. **Version policies**: Enforce sync requirements, block deployments
4. **Audit logging**: Track who modified what and when
5. **Integration with CI/CD**: Automatic version tracking in pipelines

## References

- Existing implementation: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/storage/deployment.py`
- Deployment schemas: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/deployments.py`
- Project schemas: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/projects.py`
- Artifact models: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/artifact.py`
