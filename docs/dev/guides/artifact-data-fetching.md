---
title: "Artifact Data Fetching Guide"
description: "Developer guide for understanding how artifact data flows from API endpoints to frontend components, including the dual-collection architecture and modal data sources"
audience: "developers"
tags: ["artifacts", "api", "frontend", "data-flow", "hooks", "modals", "guide"]
created: 2026-02-02
updated: 2026-02-02
category: "developer-guides"
status: "published"
related_documents:
  - "docs/project_plans/reports/dual-collection-system-architecture-analysis.md"
  - "docs/project_plans/reports/manage-collection-page-architecture-analysis.md"
  - "skillmeat/api/routers/artifacts.py"
  - "skillmeat/api/routers/user_collections.py"
  - "skillmeat/web/hooks/useArtifacts.ts"
  - "skillmeat/web/components/entity/unified-entity-modal.tsx"
---

# Artifact Data Fetching Guide

Guide for developers working with artifact data in SkillMeat. Covers API endpoints, frontend hooks, modal components, and the dual-collection architecture.

## Table of Contents

- [Overview](#overview)
- [Dual-Collection Architecture](#dual-collection-architecture)
- [API Endpoints](#api-endpoints)
- [Response Schemas](#response-schemas)
- [Frontend Hooks](#frontend-hooks)
- [Modal Components](#modal-components)
- [Data Source Comparison: /collection vs /manage](#data-source-comparison-collection-vs-manage)
- [Data Flow Diagrams](#data-flow-diagrams)
- [Common Patterns](#common-patterns)

## Overview

SkillMeat uses a **dual-collection architecture** with file-based artifacts (CLI) synced to database collections (Web). Understanding this architecture is essential for working with artifact data.

### Key Concepts

| Concept | Description |
|---------|-------------|
| **File-based artifacts** | Stored in `~/.skillmeat/collection/`, managed by `CollectionManager` |
| **Database collections** | Stored in SQLite/PostgreSQL, managed by SQLAlchemy models |
| **One-way sync** | File → Database on server startup |
| **Dual endpoints** | `/artifacts` (file-based) vs `/user-collections/{id}/artifacts` (database) |

### Key Files

**Backend:**
- `skillmeat/api/routers/artifacts.py` - Primary artifacts endpoint (file-based)
- `skillmeat/api/routers/user_collections.py` - Collection-scoped endpoint (database)
- `skillmeat/api/schemas/artifacts.py` - Response schemas
- `skillmeat/core/collection.py` - CollectionManager (file-based)

**Frontend:**
- `skillmeat/web/hooks/useArtifacts.ts` - TanStack Query hooks
- `skillmeat/web/hooks/use-collections.ts` - Collection-scoped hooks
- `skillmeat/web/components/entity/unified-entity-modal.tsx` - Core modal component
- `skillmeat/web/components/shared/CollectionArtifactModal.tsx` - Collection page wrapper
- `skillmeat/web/components/shared/ProjectArtifactModal.tsx` - Project page wrapper

## Dual-Collection Architecture

SkillMeat intentionally maintains two parallel collection systems:

### File-Based System (CollectionManager)

```
~/.skillmeat/collection/
├── collection.toml      # Manifest with artifact metadata
├── collection.lock      # Pinned versions and content hashes
├── skills/              # Deployed skill artifacts
├── commands/            # Deployed command artifacts
└── agents/              # Deployed agent artifacts
```

**Strengths:**
- Offline-capable (no server required)
- Version pinning via lock files
- Git-friendly (TOML files can be version controlled)
- CLI-first workflow (`skillmeat add`, `skillmeat deploy`, etc.)

**Used by:** `/manage` page, CLI commands

### Database System (SQLAlchemy)

**Tables:** `collections`, `collection_artifacts`, `groups`

**Strengths:**
- Visual organization (groups, hierarchy)
- Full-text search (FTS5)
- Sharing features (future)
- Rich filtering and analytics

**Used by:** `/collection` page, web UI

### Sync Mechanism

**Direction:** One-way (File → Database)
**Trigger:** Server startup (`skillmeat/api/server.py:143-154`)

```python
# On lifespan startup
result = migrate_artifacts_to_default_collection(
    session=session,
    artifact_mgr=app_state.artifact_manager,
    collection_mgr=app_state.collection_manager,
)
```

**What syncs:**
- Artifact IDs from file collection → "default" database collection
- Enables web UI to display CLI-added artifacts

**What does NOT sync:**
- Database changes do NOT flow back to files
- Custom database collections are web-only
- Groups are database-only

For detailed analysis, see: [Dual Collection System Architecture Analysis](/docs/project_plans/reports/dual-collection-system-architecture-analysis.md)

## API Endpoints

### Primary Endpoints

| Endpoint | Method | Data Source | Purpose |
|----------|--------|-------------|---------|
| `/api/v1/artifacts` | GET | CollectionManager (file-based) | List all artifacts with full metadata |
| `/api/v1/artifacts/{id}` | GET | CollectionManager + optional DB | Single artifact details |
| `/api/v1/artifacts/{id}/files` | GET | File system | Artifact file tree and content |
| `/api/v1/artifacts/{id}/upstream/diff` | GET | GitHub API + file system | Version comparison |
| `/api/v1/user-collections/{id}/artifacts` | GET | Database (SQLAlchemy) | Collection-scoped lightweight list |
| `/api/v1/deployments` | GET | Database | Deployment tracking |

### GET /api/v1/artifacts

**Route Handler:** `list_artifacts()` (artifacts.py:1680)

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 20 | Pagination limit (max 100) |
| `after` | string | null | Cursor for next page |
| `artifact_type` | string | null | Filter: skill, command, agent, mcp, hook |
| `collection` | string | null | Filter by collection name |
| `tags` | string | null | Comma-separated tag filters |
| `tools` | string | null | Filter by tools used |
| `check_drift` | bool | false | Check for local modifications |
| `project_path` | string | null | Required if check_drift=true |
| `has_unlinked` | bool | null | Filter for unlinked references |
| `import_id` | string | null | Filter by marketplace import batch |

**Response:** `ArtifactListResponse` (paginated list of `ArtifactResponse`)

### GET /api/v1/artifacts/{id}

**Route Handler:** `get_artifact()` (artifacts.py:1993)

**Path Parameters:**
- `artifact_id` (required) - Format: `type:name` (e.g., `skill:pdf`)

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `collection` | string | null | Collection name (searches all if not specified) |
| `include_deployments` | bool | false | Include deployment statistics |

**Response:** `ArtifactResponse` (single artifact with full details)

### GET /api/v1/user-collections/{id}/artifacts

**Route Handler:** `list_collection_artifacts()` (user_collections.py)

**Path Parameters:**
- `id` (required) - Collection ID

**Response:** `ArtifactSummary[]` (lightweight list with groups)

### Additional Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/artifacts` | Create artifact |
| PUT | `/api/v1/artifacts/{id}` | Update artifact |
| DELETE | `/api/v1/artifacts/{id}` | Delete artifact |
| POST | `/api/v1/artifacts/{id}/deploy` | Deploy to project |
| POST | `/api/v1/artifacts/{id}/sync` | Sync with upstream |
| POST | `/api/v1/artifacts/{id}/undeploy` | Remove from project |
| GET | `/api/v1/artifacts/{id}/diff` | Local vs upstream diff |
| GET | `/api/v1/artifacts/{id}/version-graph` | Version history graph |
| GET | `/api/v1/artifacts/{id}/files` | List artifact files |
| GET | `/api/v1/artifacts/{id}/files/{path}` | Get file content |
| PUT | `/api/v1/artifacts/{id}/files/{path}` | Update file |
| POST | `/api/v1/artifacts/{id}/files` | Create new file |
| DELETE | `/api/v1/artifacts/{id}/files/{path}` | Delete file |

## Response Schemas

### ArtifactResponse (Full)

Returned by `/api/v1/artifacts` and `/api/v1/artifacts/{id}`.

```typescript
interface ArtifactResponse {
  // Identity
  id: string;                    // Composite key: "type:name"
  name: string;                  // Artifact name
  type: string;                  // Type: skill | command | agent | mcp | hook

  // Source information
  source: string;                // Source spec: "owner/repo/path" or "local"
  origin: string;                // Category: "github" | "local" | "marketplace"
  origin_source?: string;        // Platform for marketplace
  version: string;               // Version spec: "latest" | "v1.2.3" | SHA

  // Organization
  aliases: string[];             // Alternative names
  tags: string[];                // Organizational tags

  // Metadata (from SKILL.md / COMMAND.md)
  metadata?: {
    title?: string;              // Display title
    description?: string;        // Human-readable description
    author?: string;             // Creator/maintainer
    license?: string;            // License (MIT, Apache-2.0, etc.)
    version?: string;            // Artifact version from metadata
    tags: string[];              // Categorization tags
    dependencies: string[];      // Required dependencies
    tools: string[];             // Claude Code tools used
    linked_artifacts: LinkedArtifact[];
    unlinked_references: string[];
  };

  // Upstream tracking
  upstream?: {
    tracking_enabled: boolean;
    current_version: string;
    current_sha: string;
    upstream_version?: string;
    upstream_sha?: string;
    update_available: boolean;
    has_local_modifications: boolean;
    last_checked: string;        // ISO 8601
  };

  // Deployment tracking (if include_deployments=true)
  deployment_stats?: {
    total_projects: number;
    active_deployments: number;
    last_deployed?: string;
    projects: DeploymentProject[];
  };

  // Collection membership
  collections: CollectionInfo[];

  // Timestamps
  added: string;                 // ISO 8601
  updated: string;               // ISO 8601
  import_id?: string;            // Batch import ID
}
```

### ArtifactSummary (Lightweight)

Returned by `/api/v1/user-collections/{id}/artifacts`.

```typescript
interface ArtifactSummary {
  id: string;
  name: string;
  type: string;
  version: string;
  source: string;
  description: string;           // Flattened from metadata
  author: string;                // Flattened from metadata
  groups?: GroupMembership[];    // Database-specific
}
```

### Field Availability Comparison

| Field Category | `/artifacts` (Full) | `/user-collections/{id}/artifacts` (Summary) |
|----------------|---------------------|---------------------------------------------|
| **Identity** | id, name, type, source, version | id, name, type, source, version |
| **Organization** | aliases, tags, collections | groups (database-specific) |
| **Metadata** | Full nested object | description, author (flattened) |
| **Upstream** | Full tracking info | Not available |
| **Deployments** | Optional (include_deployments) | Not available |
| **Timestamps** | added, updated, import_id | Not available |

## Frontend Hooks

### useArtifacts()

**File:** `skillmeat/web/hooks/useArtifacts.ts`

```typescript
function useArtifacts(
  filters: ArtifactFilters = {},
  sort: ArtifactSort = { field: 'name', order: 'asc' }
) {
  return useQuery({
    queryKey: artifactKeys.list(filters, sort),
    queryFn: () => fetchArtifactsFromApi(filters, sort),
    staleTime: 30000,  // 30 seconds
  });
}
```

**Filters:**
- `artifact_type` - Filter by type
- `collection` - Filter by collection
- `tags` - Filter by tags
- `searchQuery` - Full-text search
- `has_unlinked` - Filter for unlinked references

**Sort Options:**
- `field`: 'name' | 'type' | 'created' | 'updated' | 'confidence'
- `order`: 'asc' | 'desc'

### useArtifact()

```typescript
function useArtifact(id: string) {
  return useQuery({
    queryKey: artifactKeys.detail(id),
    queryFn: () => fetchArtifactFromApi(id),
    enabled: !!id,
  });
}
```

### useInfiniteArtifacts()

```typescript
function useInfiniteArtifacts(filters: ArtifactFilters = {}) {
  return useInfiniteQuery({
    queryKey: artifactKeys.infinite(filters),
    queryFn: ({ pageParam = null }) =>
      fetchArtifactsPaginated(filters, pageParam),
    getNextPageParam: (lastPage) => lastPage.page_info.end_cursor,
    initialPageParam: null,
  });
}
```

### useInfiniteCollectionArtifacts()

**File:** `skillmeat/web/hooks/use-collections.ts`

```typescript
function useInfiniteCollectionArtifacts(collectionId: string, options: CollectionArtifactOptions) {
  return useInfiniteQuery({
    queryKey: collectionKeys.artifacts(collectionId, options.filters),
    queryFn: ({ pageParam }) =>
      fetchCollectionArtifacts(collectionId, options.filters, pageParam),
    getNextPageParam: (lastPage) => lastPage.page_info.end_cursor,
    enabled: !!collectionId,
  });
}
```

### useUpdateArtifact()

```typescript
function useUpdateArtifact() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (artifact: Partial<Artifact> & { id: string }) => {
      const response = await apiRequest<ArtifactResponse>(
        `/artifacts/${encodeURIComponent(artifact.id)}`,
        { method: 'PUT', body: JSON.stringify(artifact) }
      );
      return mapApiResponseToArtifact(response, 'collection');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: artifactKeys.lists() });
    },
  });
}
```

### Hook Usage by Page

| Page | Primary Hook | Endpoint Used |
|------|--------------|---------------|
| `/collection` | `useInfiniteCollectionArtifacts()` | `/user-collections/{id}/artifacts` |
| `/manage` | `useEntityLifecycle()` + `useArtifacts()` | `/artifacts` |
| `/projects/[id]/manage` | `useEntityLifecycle()` + `useArtifacts()` | `/artifacts` + `/deployments` |

## Modal Components

### Component Hierarchy

```
CollectionArtifactModal / ProjectArtifactModal (wrapper)
    └── UnifiedEntityModal (core)
        ├── Info Tab
        ├── Files Tab (lazy)
        ├── Deployments Tab (lazy)
        ├── Sync Status Tab (lazy)
        ├── Collections Tab
        └── Linked Artifacts Tab
```

### CollectionArtifactModal

**File:** `skillmeat/web/components/shared/CollectionArtifactModal.tsx`

**Used on:** `/collection` page

**Props:**
```typescript
interface CollectionArtifactModalProps {
  artifact: Artifact | null;
  open: boolean;
  onClose: () => void;
}
```

**Navigation handlers:**
- `onNavigateToSource` → `/marketplace/sources/{id}?artifact={path}`
- `onNavigateToDeployment` → `/projects/{path}/manage?artifact={id}`

### ProjectArtifactModal

**File:** `skillmeat/web/components/shared/ProjectArtifactModal.tsx`

**Used on:** `/projects/[id]/manage` page

**Props:**
```typescript
interface ProjectArtifactModalProps {
  artifact: Artifact | null;
  open: boolean;
  onClose: () => void;
  currentProjectPath?: string;
}
```

**Navigation handlers:**
- `onNavigateToSource` → `/marketplace/sources/{id}?artifact={path}`
- `onNavigateToDeployment` → Same project: no-op; Different project: navigate

### UnifiedEntityModal

**File:** `skillmeat/web/components/entity/unified-entity-modal.tsx`

**Props:**
```typescript
interface UnifiedEntityModalProps {
  artifact?: Artifact | null;
  entity?: Artifact | null;        // Deprecated (backward compat)
  open: boolean;
  onClose: () => void;
  onNavigateToSource?: (sourceId: string, artifactPath: string) => void;
  onNavigateToDeployment?: (projectPath: string, artifactId: string) => void;
}
```

### Tab Data Sources

| Tab | Data Source | Fetching |
|-----|-------------|----------|
| **Info** | `artifact.metadata` | Immediate (from props) |
| **Files** | `GET /artifacts/{id}/files` | Lazy (on tab open) |
| **Deployments** | `GET /deployments?artifact_id=` | Lazy (on tab open) |
| **Sync Status** | `GET /artifacts/{id}/upstream/diff` | Lazy (on tab open) |
| **Collections** | `artifact.collections` | Immediate (from props) |
| **Linked Artifacts** | `artifact.metadata.linked_artifacts` | Immediate (from props) |

## Data Source Comparison: /collection vs /manage

This table shows where data comes from for each field/tab in the artifact modal on each page.

| Field/Tab | `/collection` Page | `/manage` Page |
|-----------|-------------------|----------------|
| **Modal Wrapper** | `CollectionArtifactModal` | `ProjectArtifactModal` |
| **Core Component** | `UnifiedEntityModal` | `UnifiedEntityModal` |
| **Primary Hook** | `useInfiniteCollectionArtifacts()` | `useEntityLifecycle()` + `useArtifacts()` |
| **Primary Endpoint** | `/user-collections/{id}/artifacts` (DB) | `/artifacts` (file-based) |
| **Data Enrichment** | None (uses API response directly) | Merges collection artifact with project deployment data |
| | | |
| **--- OVERVIEW TAB ---** | | |
| Name, Type | From list response (`ArtifactSummary`) | From merged entity data |
| Description | From list `description` (flattened) | From `artifact.metadata.description` |
| Author | From list `author` (flattened) | From `artifact.metadata.author` |
| License | **Not in summary** (fetch on expand) | From `artifact.metadata.license` |
| Tags | **Not in summary** | From `artifact.tags` |
| Tools | **Not in summary** | From `artifact.metadata.tools` |
| Upstream Status | **Not in summary** | From `artifact.upstream` |
| | | |
| **--- FILES TAB ---** | | |
| File Tree | Lazy: `GET /artifacts/{id}/files` | Lazy: `GET /artifacts/{id}/files` |
| File Content | Lazy: `GET /artifacts/{id}/files/{path}` | Lazy: `GET /artifacts/{id}/files/{path}` |
| | | |
| **--- DEPLOYMENTS TAB ---** | | |
| Deployment List | Lazy: `GET /deployments?artifact_id=` | Available via `useEntityLifecycle()` context |
| Deploy Action | Via dialog → `POST /artifacts/{id}/deploy` | Via dialog → `POST /artifacts/{id}/deploy` |
| | | |
| **--- SYNC STATUS TAB ---** | | |
| Drift Detection | **Not available** (no file-based data) | From `artifact.upstream.has_local_modifications` |
| Version Diff | Lazy: `GET /artifacts/{id}/upstream/diff` | Lazy: `GET /artifacts/{id}/upstream/diff` |
| Sync Action | Via `POST /artifacts/{id}/sync` | Via `POST /artifacts/{id}/sync` |
| | | |
| **--- COLLECTIONS TAB ---** | | |
| Collection Membership | From list `groups[]` (database) | From `artifact.collections[]` |
| Group Management | Database-only groups | **Not primary focus** |
| | | |
| **--- LINKED ARTIFACTS ---** | | |
| Dependencies | **Not in summary** | From `artifact.metadata.linked_artifacts` |
| Unlinked Refs | **Not in summary** | From `artifact.metadata.unlinked_references` |
| | | |
| **--- NAVIGATION ---** | | |
| "View Source" → | `/marketplace/sources/{id}?artifact=` | `/marketplace/sources/{id}?artifact=` |
| "View in Project" → | `/projects/{path}/manage?artifact=` | No-op if same project; navigates if different |
| Cross-page link | "Manage Artifact →" button | "Collection Details →" button |

### Key Insight

The `/collection` page modal has **less metadata available** initially because it uses the lightweight database-backed endpoint (`ArtifactSummary`). The `/manage` page modal has **full artifact data** including upstream tracking and drift detection because it uses the file-based `CollectionManager` endpoint (`ArtifactResponse`).

## Data Flow Diagrams

### Collection Page Flow

```
User opens /collection
    │
    ▼
useInfiniteCollectionArtifacts(collectionId)
    │
    ▼
GET /api/v1/user-collections/{id}/artifacts
    │
    ▼
Returns ArtifactSummary[] (lightweight)
    │
    ▼
User clicks artifact card
    │
    ▼
setSelectedArtifact(artifact)  // from list response
    │
    ▼
<CollectionArtifactModal artifact={selectedArtifact} />
    │
    ▼
<UnifiedEntityModal /> renders tabs
    │
    ├── Info Tab: displays artifact.description, artifact.author
    │              (missing: license, tags, tools, upstream)
    │
    ├── Files Tab: lazy fetches GET /artifacts/{id}/files
    │
    ├── Deployments Tab: lazy fetches GET /deployments?artifact_id=
    │
    ├── Sync Status: lazy fetches GET /artifacts/{id}/upstream/diff
    │                (drift detection NOT available in initial data)
    │
    └── Collections Tab: displays artifact.groups[]
```

### Manage Page Flow

```
User opens /manage
    │
    ▼
useEntityLifecycle() + useArtifacts()
    │
    ▼
GET /api/v1/artifacts  // full metadata
    │
    ▼
Returns ArtifactResponse[] (full)
    │
    ▼
User clicks artifact card
    │
    ▼
setSelectedArtifact(artifact)  // full ArtifactResponse
    │
    ▼
<ProjectArtifactModal artifact={selectedArtifact} />
    │
    ▼
<UnifiedEntityModal /> renders tabs
    │
    ├── Info Tab: displays full metadata
    │              (license, tags, tools, upstream all available)
    │
    ├── Files Tab: lazy fetches GET /artifacts/{id}/files
    │
    ├── Deployments Tab: from useEntityLifecycle() or lazy fetch
    │
    ├── Sync Status: drift detection from artifact.upstream
    │                lazy fetches diff for details
    │
    └── Collections Tab: displays artifact.collections[]
```

## Common Patterns

### Pattern 1: Lazy Tab Loading

```typescript
// Inside UnifiedEntityModal
const [activeTab, setActiveTab] = useState('info');

// Files query - only runs when Files tab is active
const { data: files } = useQuery({
  queryKey: fileKeys.list(artifact?.id),
  queryFn: () => fetchArtifactFiles(artifact?.id),
  enabled: !!artifact?.id && activeTab === 'files',
});

// Deployments query - only runs when Deployments tab is active
const { data: deployments } = useQuery({
  queryKey: deploymentKeys.forArtifact(artifact?.id),
  queryFn: () => listDeployments({ artifact_id: artifact?.id }),
  enabled: !!artifact?.id && activeTab === 'deployments',
});
```

### Pattern 2: Data Enrichment on Manage Page

```typescript
// Merge collection artifact data with project deployment data
const enrichedEntity = useMemo(() => {
  if (!selectedEntity || !artifactsData) return selectedEntity;

  const matchingArtifact = artifactsData.artifacts.find(
    (a) => a.name === selectedEntity.name && a.type === selectedEntity.type
  );

  if (!matchingArtifact) return selectedEntity;

  return {
    ...selectedEntity,
    ...matchingArtifact,
    // Keep project-specific fields from selectedEntity
    deploymentInfo: selectedEntity.deploymentInfo,
  };
}, [selectedEntity, artifactsData]);
```

### Pattern 3: Query Key Factories

```typescript
// hooks/useArtifacts.ts
export const artifactKeys = {
  all: ['artifacts'] as const,
  lists: () => [...artifactKeys.all, 'list'] as const,
  list: (filters: ArtifactFilters, sort: ArtifactSort) =>
    [...artifactKeys.lists(), { filters, sort }] as const,
  details: () => [...artifactKeys.all, 'detail'] as const,
  detail: (id: string) => [...artifactKeys.details(), id] as const,
  infinite: (filters: ArtifactFilters) =>
    [...artifactKeys.all, 'infinite', { filters }] as const,
};

// Usage for cache invalidation
queryClient.invalidateQueries({ queryKey: artifactKeys.lists() });
```

### Pattern 4: URL-Driven Modal State

```typescript
// Auto-open modal if artifact param in URL
useEffect(() => {
  const artifactId = searchParams.get('artifact');
  if (artifactId && artifacts.length > 0) {
    const artifact = artifacts.find(a => a.id === artifactId);
    if (artifact) {
      setSelectedArtifact(artifact);
      setIsDetailOpen(true);
    }
  }
}, [searchParams, artifacts]);

// Update URL when modal opens
const handleArtifactClick = (artifact: Artifact) => {
  setSelectedArtifact(artifact);
  setIsDetailOpen(true);
  router.push(`?artifact=${encodeURIComponent(artifact.id)}`, { shallow: true });
};
```

## Performance Considerations

### Stale Times

| Hook | Stale Time | Rationale |
|------|------------|-----------|
| `useArtifacts()` | 30 seconds | Artifact data changes infrequently |
| `useInfiniteArtifacts()` | 30 seconds | Same as above |
| `useDeployments()` | 10 seconds | Deployments can change during session |
| `useArtifactFiles()` | 60 seconds | File content rarely changes |

### Token Efficiency

| Endpoint | Payload Size | Use Case |
|----------|--------------|----------|
| `/user-collections/{id}/artifacts` | ~150 bytes/item | Browse, discovery, lightweight lists |
| `/artifacts` | ~2KB/item | Full details, drift detection, sync |
| `/artifacts/{id}?include_deployments=true` | ~3KB | Modal with deployment info |

### Pagination Strategy

- **Cursor-based** (recommended) - More efficient for large collections
- **Limit default**: 20 items
- **Limit max**: 100 items

```typescript
// Cursor pagination
const { data, fetchNextPage, hasNextPage } = useInfiniteArtifacts(filters);

// Load more on scroll
const handleScroll = () => {
  if (hasNextPage && !isFetching) {
    fetchNextPage();
  }
};
```

## Summary

When working with artifact data:

1. **Know your endpoint**: `/artifacts` for full data, `/user-collections/{id}/artifacts` for lightweight
2. **Understand the trade-off**: Full data = more tokens, lightweight = missing fields
3. **Lazy load heavy data**: Files, deployments, diffs fetched on-demand
4. **Use query key factories**: Enables precise cache invalidation
5. **Enrich when needed**: Merge data sources on project pages

For architectural decisions, see:
- [Dual Collection System Architecture](/docs/project_plans/reports/dual-collection-system-architecture-analysis.md)
- [Manage vs Collection Page Architecture](/docs/project_plans/reports/manage-collection-page-architecture-analysis.md)
