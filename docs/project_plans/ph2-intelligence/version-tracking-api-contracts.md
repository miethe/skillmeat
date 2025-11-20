# Version Tracking API Contracts - Quick Reference

**Version**: 1.0
**Date**: 2025-11-20
**Status**: Specification for Implementation

## Table of Contents

1. [Data Models](#data-models)
2. [API Endpoints](#api-endpoints)
3. [Request/Response Examples](#request-response-examples)
4. [Error Handling](#error-handling)
5. [Frontend Integration](#frontend-integration)

## Data Models

### Backend Models (Python)

#### Deployment (Enhanced)

**File**: `skillmeat/core/deployment.py`

```python
@dataclass
class Deployment:
    """Enhanced deployment tracking with version information."""

    # Core identification
    artifact_name: str
    artifact_type: str  # "skill" | "command" | "agent"
    from_collection: str

    # Deployment metadata
    deployed_at: datetime
    artifact_path: Path

    # Version tracking
    deployed_sha: str  # SHA-256 at deployment time
    current_sha: Optional[str] = None  # Current SHA (computed)
    local_modifications: bool = False

    # Modification tracking
    last_modification_check: Optional[datetime] = None
    modification_detected_at: Optional[datetime] = None
    parent_collection_path: Optional[str] = None

    # Version history
    version_lineage: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to TOML-compatible dict."""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Deployment":
        """Deserialize from TOML dict."""
```

#### ArtifactVersion

**File**: `skillmeat/models.py`

```python
@dataclass
class ArtifactVersion:
    """Represents a specific version of an artifact at a point in time."""

    artifact_name: str
    artifact_type: str
    content_sha: str  # SHA-256 hash
    location: str  # "collection" or absolute project path
    location_type: Literal["collection", "project"]

    # Optional fields
    collection_name: Optional[str] = None
    parent_sha: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata_snapshot: Optional[Dict[str, Any]] = None

    def is_modified(self) -> bool:
        """Check if this version differs from its parent."""
        return self.parent_sha is not None and self.parent_sha != self.content_sha
```

#### VersionGraphNode

**File**: `skillmeat/models.py`

```python
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

    @property
    def is_modified(self) -> bool:
        """True if content differs from parent."""

    @property
    def modification_count(self) -> int:
        """Count of modified children (recursive)."""
```

#### VersionGraph

**File**: `skillmeat/models.py`

```python
@dataclass
class VersionGraph:
    """Complete version graph for an artifact across all projects."""

    artifact_name: str
    artifact_type: str
    root: Optional[VersionGraphNode] = None
    orphaned_nodes: List[VersionGraphNode] = field(default_factory=list)
    total_deployments: int = 0
    modified_count: int = 0
    last_updated: datetime = field(default_factory=datetime.now)

    def get_all_nodes(self) -> List[VersionGraphNode]:
        """Flatten graph to list of all nodes."""
```

### API Schemas (Pydantic)

#### ArtifactVersionInfo

**File**: `skillmeat/api/schemas/versions.py`

```python
class ArtifactVersionInfo(BaseModel):
    """Version information for a single artifact instance."""

    artifact_name: str = Field(description="Artifact name")
    artifact_type: str = Field(description="Artifact type")
    location: str = Field(description="Location (collection or project path)")
    location_type: Literal["collection", "project"]
    content_sha: str = Field(description="SHA-256 content hash")
    parent_sha: Optional[str] = Field(default=None, description="Parent version SHA")
    is_modified: bool = Field(description="Whether content differs from parent")
    created_at: datetime = Field(description="Version creation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

#### VersionGraphNodeResponse

**File**: `skillmeat/api/schemas/versions.py`

```python
class VersionGraphNodeResponse(BaseModel):
    """Node in version graph visualization."""

    id: str = Field(description="Unique node identifier")
    artifact_name: str
    artifact_type: str
    version_info: ArtifactVersionInfo
    children: List["VersionGraphNodeResponse"] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "collection:abc123",
                "artifact_name": "pdf-processor",
                "artifact_type": "skill",
                "version_info": {...},
                "children": [...]
            }
        }
```

#### VersionGraphResponse

**File**: `skillmeat/api/schemas/versions.py`

```python
class VersionGraphResponse(BaseModel):
    """Complete version graph for an artifact."""

    artifact_name: str
    artifact_type: str
    root: Optional[VersionGraphNodeResponse] = None
    statistics: Dict[str, Any] = Field(
        description="Aggregated statistics",
        examples=[{
            "total_deployments": 5,
            "modified_count": 2,
            "unmodified_count": 3,
            "orphaned_count": 0
        }]
    )
    last_updated: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "artifact_name": "pdf-processor",
                "artifact_type": "skill",
                "root": {...},
                "statistics": {...},
                "last_updated": "2025-11-20T16:00:00Z"
            }
        }
```

#### ModificationCheckResponse

**File**: `skillmeat/api/schemas/versions.py`

```python
class ModificationCheckResponse(BaseModel):
    """Response from modification check operation."""

    project_id: str = Field(description="Base64-encoded project path")
    checked_at: datetime = Field(description="Timestamp of check")
    modifications_detected: int = Field(
        description="Number of modified artifacts detected"
    )
    deployments: List[DeploymentModificationStatus] = Field(
        description="Status of each deployment"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "L1VzZXJzL21lL3Byb2plY3Qx",
                "checked_at": "2025-11-20T16:00:00Z",
                "modifications_detected": 2,
                "deployments": [...]
            }
        }
```

#### DeploymentModificationStatus

**File**: `skillmeat/api/schemas/versions.py`

```python
class DeploymentModificationStatus(BaseModel):
    """Modification status for a single deployment."""

    artifact_name: str
    artifact_type: str
    deployed_sha: str = Field(description="SHA at deployment time")
    current_sha: str = Field(description="Current SHA")
    is_modified: bool = Field(description="Whether artifact is modified")
    modification_detected_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when modification was first detected"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "artifact_name": "pdf-processor",
                "artifact_type": "skill",
                "deployed_sha": "abc123def456...",
                "current_sha": "def789ghi012...",
                "is_modified": True,
                "modification_detected_at": "2025-11-20T15:45:00Z"
            }
        }
```

#### DeploymentStatistics (for Artifact Response Enhancement)

**File**: `skillmeat/api/schemas/artifacts.py`

```python
class DeploymentStatistics(BaseModel):
    """Deployment statistics for an artifact."""

    total_deployments: int = Field(
        description="Total number of deployments",
        ge=0
    )
    modified_deployments: int = Field(
        description="Number of deployments with local modifications",
        ge=0
    )
    projects: List[ProjectDeploymentInfo] = Field(
        description="Per-project deployment information"
    )


class ProjectDeploymentInfo(BaseModel):
    """Deployment information for a single project."""

    project_name: str = Field(description="Project name")
    project_path: str = Field(description="Absolute project path")
    is_modified: bool = Field(description="Whether deployment is modified")
    deployed_at: datetime = Field(description="Deployment timestamp")
```

### Frontend Types (TypeScript)

#### Version Tracking Types

**File**: `web/src/types/versions.ts`

```typescript
export interface ArtifactVersionInfo {
  artifact_name: string
  artifact_type: string
  location: string
  location_type: 'collection' | 'project'
  content_sha: string
  parent_sha: string | null
  is_modified: boolean
  created_at: string  // ISO 8601
  metadata: Record<string, any>
}

export interface VersionGraphNode {
  id: string
  artifact_name: string
  artifact_type: string
  version_info: ArtifactVersionInfo
  children: VersionGraphNode[]
  metadata: Record<string, any>
}

export interface VersionGraph {
  artifact_name: string
  artifact_type: string
  root: VersionGraphNode | null
  statistics: {
    total_deployments: number
    modified_count: number
    unmodified_count: number
    orphaned_count: number
  }
  last_updated: string  // ISO 8601
}

export interface ModificationCheckResult {
  project_id: string
  checked_at: string  // ISO 8601
  modifications_detected: number
  deployments: DeploymentModificationStatus[]
}

export interface DeploymentModificationStatus {
  artifact_name: string
  artifact_type: string
  deployed_sha: string
  current_sha: string
  is_modified: boolean
  modification_detected_at: string | null  // ISO 8601
}
```

## API Endpoints

### 1. Check Project Modifications

**Endpoint**: `POST /api/v1/projects/{project_id}/check-modifications`

**Purpose**: Scan all deployments in a project and detect modifications.

**Authentication**: Required (API Key or Bearer Token)

**Rate Limit**: 1 request per minute per project

**Path Parameters**:
- `project_id` (string, required): Base64-encoded project path

**Response**: `ModificationCheckResponse`

**Status Codes**:
- `200 OK`: Check completed successfully
- `401 Unauthorized`: Invalid or missing API key
- `404 Not Found`: Project not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

---

### 2. Get Artifact Version Graph

**Endpoint**: `GET /api/v1/artifacts/{artifact_id}/version-graph`

**Purpose**: Get complete version graph showing all deployments of an artifact.

**Authentication**: Required (API Key or Bearer Token)

**Path Parameters**:
- `artifact_id` (string, required): Format `{type}:{name}` (e.g., `skill:pdf-processor`)

**Query Parameters**:
- `collection` (string, optional): Filter to specific collection

**Response**: `VersionGraphResponse`

**Caching**: 5 minutes (Cache-Control header)

**Status Codes**:
- `200 OK`: Graph retrieved successfully
- `401 Unauthorized`: Invalid or missing API key
- `404 Not Found`: Artifact not found
- `500 Internal Server Error`: Server error

---

### 3. Get Project Modified Artifacts

**Endpoint**: `GET /api/v1/projects/{project_id}/modified-artifacts`

**Purpose**: Get list of all modified artifacts in a project.

**Authentication**: Required (API Key or Bearer Token)

**Path Parameters**:
- `project_id` (string, required): Base64-encoded project path

**Response**:
```json
{
  "project_id": "L1VzZXJzL21lL3Byb2plY3Qx",
  "modified_artifacts": [
    {
      "artifact_name": "pdf-processor",
      "artifact_type": "skill",
      "deployed_sha": "abc123",
      "current_sha": "def456",
      "modification_detected_at": "2025-11-20T15:45:00Z"
    }
  ],
  "total_count": 1,
  "last_checked": "2025-11-20T16:00:00Z"
}
```

**Status Codes**:
- `200 OK`: List retrieved successfully
- `401 Unauthorized`: Invalid or missing API key
- `404 Not Found`: Project not found
- `500 Internal Server Error`: Server error

---

### 4. Enhanced Artifact Detail

**Endpoint**: `GET /api/v1/artifacts/{artifact_id}`

**Purpose**: Get artifact details with optional deployment statistics.

**Authentication**: Required (API Key or Bearer Token)

**Path Parameters**:
- `artifact_id` (string, required): Format `{type}:{name}`

**Query Parameters**:
- `include_deployments` (boolean, optional, default: false): Include deployment statistics
- `collection` (string, optional): Filter to specific collection

**Response** (when `include_deployments=true`):
```json
{
  "id": "skill:pdf-processor",
  "name": "pdf-processor",
  "type": "skill",
  "source": "anthropics/skills/pdf-processor",
  "version": "latest",
  "deployment_stats": {
    "total_deployments": 5,
    "modified_deployments": 2,
    "projects": [
      {
        "project_name": "project1",
        "project_path": "/Users/me/project1",
        "is_modified": true,
        "deployed_at": "2025-11-20T10:30:00Z"
      },
      {
        "project_name": "project2",
        "project_path": "/Users/me/project2",
        "is_modified": false,
        "deployed_at": "2025-11-19T14:20:00Z"
      }
    ]
  },
  // ... other artifact fields
}
```

**Status Codes**:
- `200 OK`: Artifact retrieved successfully
- `401 Unauthorized`: Invalid or missing API key
- `404 Not Found`: Artifact not found
- `500 Internal Server Error`: Server error

## Request/Response Examples

### Example 1: Check Project Modifications

**Request**:
```http
POST /api/v1/projects/L1VzZXJzL21lL3Byb2plY3Qx/check-modifications HTTP/1.1
Host: api.skillmeat.dev
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

**Response** (200 OK):
```json
{
  "project_id": "L1VzZXJzL21lL3Byb2plY3Qx",
  "checked_at": "2025-11-20T16:00:00Z",
  "modifications_detected": 2,
  "deployments": [
    {
      "artifact_name": "pdf-processor",
      "artifact_type": "skill",
      "deployed_sha": "abc123def456789abcdef123456789abcdef123456789abcdef123456789ab",
      "current_sha": "def789ghi012345ghijkl678901234ghijkl678901234ghijkl678901234gh",
      "is_modified": true,
      "modification_detected_at": "2025-11-20T15:45:00Z"
    },
    {
      "artifact_name": "code-reviewer",
      "artifact_type": "agent",
      "deployed_sha": "123abc456def789abc123def456789abc123def456789abc123def456789ab",
      "current_sha": "456def789ghi012def456ghi789012def456ghi789012def456ghi789012de",
      "is_modified": true,
      "modification_detected_at": "2025-11-20T16:00:00Z"
    },
    {
      "artifact_name": "lint",
      "artifact_type": "command",
      "deployed_sha": "789xyz123abc456xyz789abc123456xyz789abc123456xyz789abc123456xy",
      "current_sha": "789xyz123abc456xyz789abc123456xyz789abc123456xyz789abc123456xy",
      "is_modified": false,
      "modification_detected_at": null
    }
  ]
}
```

---

### Example 2: Get Version Graph

**Request**:
```http
GET /api/v1/artifacts/skill:pdf-processor/version-graph?collection=default HTTP/1.1
Host: api.skillmeat.dev
Authorization: Bearer YOUR_API_KEY
```

**Response** (200 OK):
```json
{
  "artifact_name": "pdf-processor",
  "artifact_type": "skill",
  "root": {
    "id": "collection:default:abc123",
    "artifact_name": "pdf-processor",
    "artifact_type": "skill",
    "version_info": {
      "artifact_name": "pdf-processor",
      "artifact_type": "skill",
      "location": "collection",
      "location_type": "collection",
      "content_sha": "abc123def456789abcdef123456789abcdef123456789abcdef123456789ab",
      "parent_sha": null,
      "is_modified": false,
      "created_at": "2025-11-15T10:00:00Z",
      "metadata": {
        "collection_name": "default"
      }
    },
    "children": [
      {
        "id": "project:/Users/me/project1",
        "artifact_name": "pdf-processor",
        "artifact_type": "skill",
        "version_info": {
          "artifact_name": "pdf-processor",
          "artifact_type": "skill",
          "location": "/Users/me/project1",
          "location_type": "project",
          "content_sha": "def789ghi012345ghijkl678901234ghijkl678901234ghijkl678901234gh",
          "parent_sha": "abc123def456789abcdef123456789abcdef123456789abcdef123456789ab",
          "is_modified": true,
          "created_at": "2025-11-20T10:30:00Z",
          "metadata": {
            "project_name": "project1",
            "deployed_at": "2025-11-20T10:30:00Z",
            "modification_detected_at": "2025-11-20T15:45:00Z"
          }
        },
        "children": [],
        "metadata": {}
      },
      {
        "id": "project:/Users/me/project2",
        "artifact_name": "pdf-processor",
        "artifact_type": "skill",
        "version_info": {
          "artifact_name": "pdf-processor",
          "artifact_type": "skill",
          "location": "/Users/me/project2",
          "location_type": "project",
          "content_sha": "abc123def456789abcdef123456789abcdef123456789abcdef123456789ab",
          "parent_sha": "abc123def456789abcdef123456789abcdef123456789abcdef123456789ab",
          "is_modified": false,
          "created_at": "2025-11-19T14:20:00Z",
          "metadata": {
            "project_name": "project2",
            "deployed_at": "2025-11-19T14:20:00Z"
          }
        },
        "children": [],
        "metadata": {}
      }
    ],
    "metadata": {}
  },
  "statistics": {
    "total_deployments": 2,
    "modified_count": 1,
    "unmodified_count": 1,
    "orphaned_count": 0
  },
  "last_updated": "2025-11-20T16:00:00Z"
}
```

---

### Example 3: Get Modified Artifacts

**Request**:
```http
GET /api/v1/projects/L1VzZXJzL21lL3Byb2plY3Qx/modified-artifacts HTTP/1.1
Host: api.skillmeat.dev
Authorization: Bearer YOUR_API_KEY
```

**Response** (200 OK):
```json
{
  "project_id": "L1VzZXJzL21lL3Byb2plY3Qx",
  "modified_artifacts": [
    {
      "artifact_name": "pdf-processor",
      "artifact_type": "skill",
      "deployed_sha": "abc123def456789abcdef123456789abcdef123456789abcdef123456789ab",
      "current_sha": "def789ghi012345ghijkl678901234ghijkl678901234ghijkl678901234gh",
      "modification_detected_at": "2025-11-20T15:45:00Z"
    },
    {
      "artifact_name": "code-reviewer",
      "artifact_type": "agent",
      "deployed_sha": "123abc456def789abc123def456789abc123def456789abc123def456789ab",
      "current_sha": "456def789ghi012def456ghi789012def456ghi789012def456ghi789012de",
      "modification_detected_at": "2025-11-20T16:00:00Z"
    }
  ],
  "total_count": 2,
  "last_checked": "2025-11-20T16:00:00Z"
}
```

## Error Handling

### Standard Error Response

All errors follow the `ErrorResponse` schema:

```json
{
  "status": 404,
  "message": "Project not found",
  "detail": "Project with ID 'invalid_id' does not exist",
  "timestamp": "2025-11-20T16:00:00Z",
  "path": "/api/v1/projects/invalid_id/check-modifications"
}
```

### Common Error Scenarios

#### 1. Invalid Project ID

**Status**: 400 Bad Request

```json
{
  "status": 400,
  "message": "Invalid project ID format",
  "detail": "Project ID must be base64-encoded project path",
  "timestamp": "2025-11-20T16:00:00Z"
}
```

#### 2. Project Not Found

**Status**: 404 Not Found

```json
{
  "status": 404,
  "message": "Project not found",
  "detail": "Project at path '/Users/me/nonexistent' does not exist",
  "timestamp": "2025-11-20T16:00:00Z"
}
```

#### 3. Rate Limit Exceeded

**Status**: 429 Too Many Requests

```json
{
  "status": 429,
  "message": "Rate limit exceeded",
  "detail": "Maximum 1 modification check per minute per project. Try again in 30 seconds.",
  "timestamp": "2025-11-20T16:00:00Z",
  "retry_after": 30
}
```

#### 4. Artifact Not Found

**Status**: 404 Not Found

```json
{
  "status": 404,
  "message": "Artifact not found",
  "detail": "Artifact 'skill:nonexistent' not found in any collection",
  "timestamp": "2025-11-20T16:00:00Z"
}
```

## Frontend Integration

### React Query Hooks

**File**: `web/src/hooks/useVersionTracking.ts`

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchVersionGraph,
  checkProjectModifications,
  fetchModifiedArtifacts
} from '@/lib/api/versions'

// Query keys
export const versionKeys = {
  all: ['versions'] as const,
  graphs: () => [...versionKeys.all, 'graphs'] as const,
  graph: (artifactId: string, collection?: string) =>
    [...versionKeys.graphs(), artifactId, collection] as const,
  modifications: () => [...versionKeys.all, 'modifications'] as const,
  projectModifications: (projectId: string) =>
    [...versionKeys.modifications(), projectId] as const,
}

// Hook: Get version graph
export function useVersionGraph(artifactId: string, collection?: string) {
  return useQuery({
    queryKey: versionKeys.graph(artifactId, collection),
    queryFn: () => fetchVersionGraph(artifactId, collection),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: false,
    enabled: !!artifactId,
  })
}

// Hook: Get project modifications
export function useProjectModifications(projectId: string) {
  return useQuery({
    queryKey: versionKeys.projectModifications(projectId),
    queryFn: () => fetchModifiedArtifacts(projectId),
    staleTime: 1 * 60 * 1000, // 1 minute
    gcTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: true,
    enabled: !!projectId,
  })
}

// Hook: Check for modifications (mutation)
export function useCheckModifications(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => checkProjectModifications(projectId),
    onSuccess: (data) => {
      // Invalidate related queries
      queryClient.invalidateQueries({
        queryKey: versionKeys.projectModifications(projectId)
      })
      queryClient.invalidateQueries({
        queryKey: versionKeys.graphs()
      })

      // Optionally update cache optimistically
      queryClient.setQueryData(
        versionKeys.projectModifications(projectId),
        data
      )
    },
    onError: (error) => {
      console.error('Failed to check modifications:', error)
    }
  })
}
```

### Usage Example

```typescript
import { useVersionGraph, useCheckModifications } from '@/hooks/useVersionTracking'
import { VersionTreeView } from '@/components/versions/VersionTreeView'

function ArtifactDetailPage({ artifactId }: { artifactId: string }) {
  const { data: graph, isLoading, error } = useVersionGraph(artifactId)
  const checkMods = useCheckModifications('project123')

  if (isLoading) return <LoadingSpinner />
  if (error) return <ErrorMessage error={error} />

  return (
    <div>
      <h1>Artifact Version History</h1>

      {graph && (
        <div>
          <VersionTreeView graph={graph} />

          <div className="statistics">
            <p>Total Deployments: {graph.statistics.total_deployments}</p>
            <p>Modified: {graph.statistics.modified_count}</p>
          </div>
        </div>
      )}

      <button
        onClick={() => checkMods.mutate()}
        disabled={checkMods.isPending}
      >
        {checkMods.isPending ? 'Checking...' : 'Check for Modifications'}
      </button>
    </div>
  )
}
```

## Caching Strategy

### API-Level Caching

- **Version Graphs**: 5 minutes (HTTP Cache-Control header)
- **Modification Lists**: 1 minute
- **Artifact Details**: 5 minutes

### Client-Level Caching (React Query)

- **Stale Time**: How long data is considered fresh
- **GC Time**: How long unused data is kept in cache
- **Refetch on Focus**: Whether to refetch when window gains focus

### Invalidation Rules

1. After successful modification check → Invalidate project modifications + version graphs
2. After artifact update → Invalidate artifact details + version graphs
3. After deployment → Invalidate project details + version graphs
4. Manual invalidation via UI action

## Performance Guidelines

### Response Time Targets

- Modification check (single project): <100ms
- Version graph (100 deployments): <500ms
- Modified artifacts list: <50ms
- UI rendering: <200ms

### Optimization Techniques

1. **Lazy Loading**: Only fetch graphs when user navigates to tab
2. **Debouncing**: Prevent rapid successive checks
3. **Parallel Requests**: Use `Promise.all()` for independent queries
4. **Incremental Updates**: Only recompute changed nodes
5. **Virtual Scrolling**: For large version trees (>100 nodes)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-20
**Maintained By**: Lead Architect
