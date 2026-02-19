---
title: "Composite Artifact Infrastructure"
description: "Architecture and developer guide for composite artifacts (Plugins) - multi-artifact packages with relational model, smart import, and deduplication"
audience: [developers]
tags: [composite-artifacts, plugins, architecture, import, deduplication]
created: 2026-02-19
updated: 2026-02-19
category: "feature-documentation"
status: published
related:
  - /docs/project_plans/PRDs/features/composite-artifact-infrastructure-v1.md
  - /docs/dev/architecture/decisions/ADR-007-artifact-uuid-identity.md
---

# Composite Artifact Infrastructure

## Overview

Composite artifacts are collection-scoped entities that bundle multiple atomic artifacts (skills, commands, agents, hooks, MCP servers) into a single installable package, commonly referred to as Plugins.

Key characteristics:

- **Type**: `COMPOSITE` with `subtype: PLUGIN`
- **Scope**: Collection-level (not project-level)
- **Relationships**: Metadata-only links between parent and children
- **Dependencies**: Enabled by ADR-007 UUID-based artifact identity for proper foreign key references
- **Child Artifacts**: Remain fully independent after import; parent is purely organizational

### When to Use Composites

Composites are ideal for:
- **Plugin bundles**: A skill + command + agent working together
- **Themed collections**: Related utilities grouped by domain
- **Versioned packages**: Multi-artifact releases with synchronized versions
- **Marketplace distributions**: Pre-packaged solutions for common use cases

Composites are NOT appropriate for:
- Single artifacts (use atomic types instead)
- Artifacts with hard dependencies (relationships are metadata-only)
- Temporary groupings (decompose or use manifests instead)

---

## Data Model

### CompositeArtifact ORM Model

Located in `skillmeat/cache/models.py`

```python
class CompositeArtifact(Base):
    """Collection-scoped composite artifact entity."""

    __tablename__ = "composite_artifacts"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=generate_ulid
    )
    collection_id: Mapped[str] = mapped_column(
        String, ForeignKey("collections.id"), nullable=False
    )
    artifact_uuid: Mapped[str] = mapped_column(
        String, unique=True, nullable=False
    )
    composite_type: Mapped[str] = mapped_column(
        String, default="PLUGIN", nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    collection: Mapped["Collection"] = relationship(back_populates="composites")
    memberships: Mapped[List["CompositeMembership"]] = relationship(
        back_populates="composite", cascade="all, delete-orphan"
    )
```

### CompositeMembership Join Table

Stores parent-child relationships with metadata.

```python
class CompositeMembership(Base):
    """Association between composite and child artifact."""

    __tablename__ = "composite_memberships"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=generate_ulid
    )
    composite_id: Mapped[str] = mapped_column(
        String, ForeignKey("composite_artifacts.id"), nullable=False
    )
    artifact_uuid: Mapped[str] = mapped_column(
        String, ForeignKey("artifacts.artifact_uuid"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(
        String, default="MEMBER", nullable=False
    )
    pinned_version_hash: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    composite: Mapped["CompositeArtifact"] = relationship(
        back_populates="memberships"
    )
    artifact: Mapped["Artifact"] = relationship()
```

### Key Fields

| Field | Purpose |
|-------|---------|
| `composite_id` | PK of parent composite artifact |
| `artifact_uuid` | FK to child artifact (UUID-based, per ADR-007) |
| `relationship_type` | Semantics of relationship (MEMBER, OPTIONAL, REQUIRED) |
| `pinned_version_hash` | SHA-256 hash of deployed child version for conflict detection |

---

## Discovery

Composite detection identifies plugin.json manifests or heuristically detects multi-artifact packages.

### detect_composites() Function

Located in the detection layer (typically `skillmeat/core/discovery.py`)

```python
def detect_composites(
    repo_owner: str,
    repo_name: str,
    path: str = "",
    client: GitHubClient | None = None
) -> DiscoveredGraph:
    """
    Discover composite artifacts (plugins) and their child artifacts.

    Returns a DiscoveredGraph containing:
    - Parent composite metadata
    - List of child artifacts with linkage info
    - Relationship metadata
    """
```

### Detection Strategies

1. **Manifest-based**: Look for `plugin.json` or `composite.json` at artifact root
   - Contains explicit child listings
   - Defines relationship semantics
   - Provides metadata overrides

2. **Heuristic-based**: Detect 2+ artifact-type subdirectories
   - Example: `skills/` + `commands/` + `agents/`
   - Auto-link discovered artifacts by directory
   - No manifest required

### DiscoveredGraph Return Type

```typescript
interface DiscoveredGraph {
  parent: {
    path: string;
    name: string;
    type: "composite";
    subtype: "plugin";
    confidence: number;
  };
  children: Array<{
    path: string;
    name: string;
    type: "skill" | "command" | "agent" | "hook" | "mcp_server";
    confidence: number;
    relationshipType: "MEMBER" | "OPTIONAL" | "REQUIRED";
  }>;
  discoveredAt: string;
}
```

### Feature Flagging

Composite detection is controlled via feature flag:

```python
from skillmeat.core.config import feature_flags

if feature_flags.composite_detection_enabled:
    graph = detect_composites(owner, repo, path)
```

---

## Import Flow

Composite import uses transactional semantics to ensure atomic success/failure across all children.

### Step-by-Step Process

```
1. User initiates composite import
    ├─ UI fetches composite manifest
    └─ Shows preview: New / Existing / Conflict buckets

2. Deduplication check
    ├─ For each child: compute SHA-256 content hash
    ├─ Query DB: SELECT hash FROM artifact_versions
    ├─ Categorize: NEW, EXISTING (same hash), CONFLICT (different hash)
    └─ Display 3-bucket preview

3. User confirms import
    ├─ Start DB transaction
    └─ For each child (in order):
        ├─ If NEW: Insert artifact row
        ├─ If EXISTING: Link to existing artifact
        ├─ If CONFLICT: Ask user (retry or skip)
        ├─ Create CompositeMembership record
        └─ Record pinned_version_hash in membership

4. Write parent composite
    ├─ Insert CompositeArtifact row
    ├─ Insert all CompositeMembership rows
    └─ Commit transaction (all-or-nothing)

5. On failure: Entire transaction rolls back (no partial imports)
```

### API Request Flow

```python
@router.post("/artifacts/import/composite")
async def import_composite(
    request: CompositeImportRequest,
    db: AsyncSession = Depends(get_db),
) -> CompositeImportResponse:
    """
    Import composite artifact with all children.

    Atomically imports parent + all children or rolls back entirely.
    """
    async with db.begin():  # Transaction
        # 1. Validate children exist or can be fetched
        # 2. Check for conflicts
        # 3. Insert composite parent
        # 4. Insert all memberships with pinned hashes
        # 5. Return full tree with import status
```

### Deduplication Logic

Content hash deduplication prevents duplicate artifact installations:

```python
def compute_artifact_hash(content: str) -> str:
    """SHA-256 hash of artifact content for dedup."""
    return hashlib.sha256(content.encode()).hexdigest()

async def check_artifact_exists(
    hash: str,
    db: AsyncSession
) -> ArtifactVersion | None:
    """Query DB for existing artifact by content hash."""
    result = await db.execute(
        select(ArtifactVersion).where(
            ArtifactVersion.content_hash == hash
        )
    )
    return result.scalar_one_or_none()
```

### Error Handling

Transactional guarantees ensure:
- On any child import error: entire transaction rolled back
- No partial composites in database
- User sees clear error message with failed child details
- Import can be retried without cleanup

---

## API Endpoints

### Get Artifact Associations

```
GET /api/v1/artifacts/{artifact_id}/associations
```

**Purpose**: Return parent/child associations for an artifact

**Response**:
```json
{
  "parents": [
    {
      "id": "comp-uuid-123",
      "name": "Canvas Plugin Bundle",
      "type": "COMPOSITE",
      "subtype": "PLUGIN",
      "relationship_type": "MEMBER",
      "pinned_version_hash": "abc123def456..."
    }
  ],
  "children": [
    {
      "artifact_uuid": "skill-uuid-456",
      "name": "Canvas Design Skill",
      "type": "skill",
      "relationship_type": "MEMBER",
      "pinned_version_hash": "xyz789..."
    }
  ]
}
```

**Status Codes**:
- `200 OK`: Associations retrieved
- `404 NOT FOUND`: Artifact not found
- `500 INTERNAL SERVER ERROR`: Database error

### List Composite Artifacts

```
GET /api/v1/artifacts?artifact_type=composite
```

**Purpose**: List all composite artifacts in collection

**Query Parameters**:
- `artifact_type=composite` (required)
- `collection_id` (optional, defaults to active collection)
- `subtype=PLUGIN` (optional filter)

**Response**:
```json
{
  "items": [
    {
      "id": "comp-123",
      "artifact_uuid": "uuid-123",
      "name": "Canvas Plugin Bundle",
      "type": "COMPOSITE",
      "subtype": "PLUGIN",
      "child_count": 3,
      "created_at": "2026-02-19T10:00:00Z",
      "updated_at": "2026-02-19T10:00:00Z"
    }
  ],
  "total": 1,
  "count": 1
}
```

### Import Composite

```
POST /api/v1/artifacts/import/composite
```

**Request Body**:
```json
{
  "source": "username/repo/plugins/canvas-bundle",
  "version": "latest",
  "include_children": true,
  "skip_conflicts": false
}
```

**Response** (202 Accepted - async):
```json
{
  "transaction_id": "txn-abc123",
  "status": "in_progress",
  "parent": {
    "name": "Canvas Plugin Bundle",
    "pending": true
  },
  "children": [
    {
      "name": "Canvas Skill",
      "status": "imported",
      "hash_status": "new"
    },
    {
      "name": "Canvas Command",
      "status": "imported",
      "hash_status": "existing"
    },
    {
      "name": "Canvas Agent",
      "status": "conflict",
      "hash_status": "conflict",
      "existing_hash": "abc123..."
    }
  ]
}
```

---

## Web UI

### Contains Tab

Visible on artifact detail pages for composites.

- **Title**: "Contains" or "Includes"
- **Location**: Horizontal tab strip alongside Info, Versions, History
- **Content**: List of child artifacts
  - Artifact name, type icon, version
  - "View" button to navigate to child detail
  - Sync status (same hash, conflict indicator)
- **Interaction**: Click row to navigate to child

### Part of Section

Visible on artifact detail pages for children of a composite.

- **Title**: "Part of"
- **Location**: Below header, above description
- **Content**: List of parent composites
  - Parent name, type indicator
  - "Open" button to navigate to parent
  - Relationship type badge (MEMBER, REQUIRED, etc.)

### Import Preview Dialog

Three-bucket display when importing composites.

```
┌─────────────────────────────────────────────┐
│ Import Canvas Plugin Bundle (3 artifacts)   │
├─────────────────────────────────────────────┤
│                                             │
│ NEW (Will be added)              [1]       │
│ ✓ Canvas Skill                             │
│                                             │
│ EXISTING (Already in collection) [1]       │
│ ✓ Canvas Command                           │
│                                             │
│ CONFLICT (Version mismatch)      [1]       │
│ ⚠ Canvas Agent (different version)         │
│    Current: v1.0  →  New: v2.0             │
│    [Overwrite] [Skip] [View Diff]          │
│                                             │
├─────────────────────────────────────────────┤
│          [Cancel]  [Import All]             │
└─────────────────────────────────────────────┘
```

### Version Conflict Dialog

For `CONFLICT` bucket items during import.

- **Title**: "Resolve Conflict: Canvas Agent"
- **Content**:
  - Current version details (creator, updated_at, hash)
  - New version details (creator, updated_at, hash)
  - Side-by-side diff if available
- **Actions**:
  - "Overwrite": Use new version
  - "Skip": Keep current version
  - "View Full Diff": Expand detailed comparison

---

## CLI

### List Composites

```bash
skillmeat list --type composite
```

Output includes composites alongside atomic artifacts, filtered by platform profile.

```
NAME                     TYPE       SUBTYPE  SCOPE   VERSION
canvas-bundle           composite   plugin   local   @main
my-utilities            composite   plugin   user    @v1.0.0
```

### Export Composite

```bash
skillmeat export canvas-bundle
```

Exports composite metadata + all child artifacts as a distributable bundle:

```
canvas-bundle/
├── plugin.json              # Composite manifest
├── skills/
│   └── canvas-design/
│       ├── SKILL.md
│       └── src/
├── commands/
│   └── canvas-command/
│       └── COMMAND.json
└── agents/
    └── canvas-agent/
        └── AGENT.json
```

### Add Composite

```bash
skillmeat add anthropics/plugins/canvas-bundle
```

Transparently handles composite import with dependency graph validation.

---

## Storage Layout

### Collection Storage

Composites metadata stored alongside atomic artifacts:

```
~/.skillmeat/collections/{collection_name}/
├── artifacts/
│   ├── skills/
│   │   └── canvas-design/
│   ├── commands/
│   │   └── canvas-command/
│   └── agents/
│       └── canvas-agent/
├── plugins/
│   └── canvas-bundle/
│       ├── plugin.json
│       └── manifest.toml
└── manifest.toml
```

### Project Storage

Deployed composites use same structure within project:

```
{project}/.claude/
├── plugins/
│   └── canvas-bundle/
│       ├── plugin.json
│       └── deployment.toml
├── skills/
│   └── canvas-design/
├── commands/
│   └── canvas-command/
└── agents/
    └── canvas-agent/
```

### Manifest Format

`plugin.json` (or `composite.json`):

```json
{
  "name": "Canvas Plugin Bundle",
  "type": "composite",
  "subtype": "plugin",
  "version": "1.0.0",
  "description": "Canvas design tools for Claude Code",
  "members": [
    {
      "path": "skills/canvas-design",
      "type": "skill",
      "relationship": "REQUIRED"
    },
    {
      "path": "commands/canvas-command",
      "type": "command",
      "relationship": "MEMBER"
    },
    {
      "path": "agents/canvas-agent",
      "type": "agent",
      "relationship": "OPTIONAL"
    }
  ],
  "tags": ["design", "canvas", "ui"],
  "created_at": "2025-11-20",
  "updated_at": "2026-02-19"
}
```

---

## Observability

### OpenTelemetry Spans

Structured spans for composite operations:

| Span Name | Attributes | Duration |
|-----------|------------|----------|
| `composite.detect` | `plugin_name`, `repo_path`, `strategy` (manifest/heuristic) | 500-2000ms |
| `composite.dedup_check` | `child_count`, `new_count`, `conflict_count` | 100-500ms per child |
| `composite.import` | `transaction_id`, `parent_name`, `child_count` | 1-5s total |
| `composite.association_write` | `membership_count`, `db_operation_time` | 50-200ms |

### Structured Logging

All composite operations log structured fields:

```python
logger.info(
    "composite_import_complete",
    extra={
        "plugin_name": "canvas-bundle",
        "child_count": 3,
        "new_count": 1,
        "existing_count": 1,
        "conflict_count": 1,
        "transaction_id": "txn-abc123",
        "duration_ms": 2500,
    }
)
```

### Metrics

Prometheus-style metrics for monitoring:

| Metric | Type | Description |
|--------|------|-------------|
| `plugin_import_duration_seconds` | Histogram | Time to import composite (all children) |
| `plugin_import_total` | Counter | Total composite imports |
| `dedup_hit_total` | Counter | Child artifacts found in existing DB |
| `dedup_miss_total` | Counter | Child artifacts that are new |
| `composite_conflict_total` | Counter | Version conflicts during import |

---

## Related Documentation

- **PRD**: `/docs/project_plans/PRDs/features/composite-artifact-infrastructure-v1.md` — Complete feature specification and requirements
- **ADR-007**: `/docs/dev/architecture/decisions/ADR-007-artifact-uuid-identity.md` — UUID-based artifact identity enabling FK relationships
- **Design Spec**: `/docs/project_plans/design-specs/composite-artifact-infrastructure.md` — Visual designs and interaction flows
- **Cache Architecture**: `/docs/dev/features/cache/README.md` — Database schema and ORM patterns
- **API Reference**: `/docs/dev/api/discovery-endpoints.md` — Full API endpoint specifications
