# SkillMeat Marketplace Source Detection & Artifact Scanning Architecture

## Overview

The marketplace source detection system spans backend (Python), frontend (TypeScript/React), and database layers. It enables scanning GitHub repositories for Claude Code artifacts with heuristic detection, confidence scoring, and user controls.

---

## 1. BACKEND: CORE SCANNING LOGIC

### Detection & Scanning
**Location**: `skillmeat/core/marketplace/`

| File | Purpose |
|------|---------|
| `github_scanner.py` | Main GitHub repository scanning service using GitHub API. Uses HeuristicDetector to identify artifacts in repository tree. Returns ScanResultDTO with detected artifacts and metadata. |
| `heuristic_detector.py` | Heuristic detection engine that identifies artifacts based on file patterns, YAML frontmatter, directory structure. Applies scoring algorithm to confidence_score (0-100). |
| `diff_engine.py` | Tracks artifact status changes between scans (new, updated, removed, imported). Compares previous scan results with current scan. |
| `import_coordinator.py` | Orchestrates importing discovered artifacts to user collection. Handles conflict resolution, deduplication, and status transitions. |
| `link_harvester.py` | Extracts relationships/dependencies between artifacts for better organization. |
| `observability.py` | Metrics and logging for marketplace operations. |

### Related Core Modules
| File | Purpose |
|------|---------|
| `skillmeat/core/discovery.py` | Generic artifact discovery service (scans `.claude/` directories). Includes ArtifactDiscoveryService, DiscoveryResult, DiscoveredArtifact models. |
| `skillmeat/core/path_tags.py` | Path-based tag extraction for automatic tagging from artifact paths. |
| `skillmeat/core/github_metadata.py` | GitHub metadata enrichment (stars, forks, etc.). |

---

## 2. DATABASE: MARKETPLACE MODELS

### Location: `skillmeat/cache/models.py`

#### MarketplaceSource (Line 1173)
Represents a GitHub repository source for marketplace artifact discovery.

**Key Fields**:
- `id`: Primary key
- `repo_url`: GitHub repository URL (UNIQUE)
- `owner`, `repo_name`: Parsed from URL
- `ref`: Branch/tag to scan (default: "main")
- `root_hint`: Optional subdirectory hint
- `description`, `notes`: User-provided metadata
- `trust_level`: "untrusted", "basic", "verified", "official"
- `visibility`: "private", "internal", "public"
- `enable_frontmatter_detection`: Parse markdown frontmatter for hints
- `path_tag_config`: JSON config for path-based tag extraction
- `scan_status`: "pending", "scanning", "success", "error"
- `last_sync_at`: Timestamp of last successful scan
- `last_error`: Error message if scan failed
- `artifact_count`: Cached count of discovered artifacts
- `entries`: Relationship to MarketplaceCatalogEntry (cascade delete)

**Indexes**:
- `idx_marketplace_sources_repo_url` (UNIQUE)
- `idx_marketplace_sources_last_sync`
- `idx_marketplace_sources_scan_status`

#### MarketplaceCatalogEntry (Line 1368)
Represents a detected artifact from a marketplace source.

**Key Fields**:
- `id`: Primary key
- `source_id`: Foreign key to MarketplaceSource
- `artifact_type`: "skill", "command", "agent", "mcp_server", "hook"
- `name`: Artifact name from detection
- `path`: Path within repository
- `upstream_url`: Full URL to artifact in repository
- `detected_version`: Extracted version
- `detected_sha`: Git commit SHA at detection time
- `detected_at`: Scan timestamp
- **`confidence_score`**: Heuristic confidence 0-100 (CRITICAL)
- `raw_score`: Before normalization
- `score_breakdown`: JSON breakdown of scoring components
- `status`: "new", "updated", "removed", "imported", "excluded"
- `import_date`: When imported to collection
- `import_id`: Reference to imported artifact
- **`excluded_at`**: Timestamp when marked "not an artifact"
- **`excluded_reason`**: User reason for exclusion
- **`path_segments`**: JSON array of extracted path segments with approval status
- `metadata_json`: Additional detection metadata

**Indexes**:
- `idx_catalog_entries_source_id`
- `idx_catalog_entries_status`
- `idx_catalog_entries_type`
- `idx_catalog_entries_upstream_url` (Deduplication)
- `idx_catalog_entries_source_status`

**Status Enum**:
```
'new' - First detected
'updated' - Changes detected since last import
'removed' - Was detected before, no longer found
'imported' - Already added to collection
'excluded' - User marked as false positive
```

---

## 3. API LAYER

### Routers

**Location**: `skillmeat/api/routers/`

| File | Purpose |
|------|---------|
| `marketplace_sources.py` (Line 1) | Main marketplace sources API router. Handles source CRUD, scanning, catalog listing, artifact import, exclusion, and path tag management. |
| `marketplace.py` | General marketplace operations (Claude marketplace integration). |

### Marketplace Sources API Endpoints

**Prefix**: `/api/v1/marketplace/sources`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/` | Create new GitHub source |
| `GET` | `/` | List all sources (paginated) |
| `GET` | `/{id}` | Get source by ID |
| `PATCH` | `/{id}` | Update source |
| `DELETE` | `/{id}` | Delete source |
| `POST` | `/{id}/rescan` | Trigger rescan |
| `GET` | `/{id}/artifacts` | List artifacts with filters |
| `POST` | `/{id}/import` | Import artifacts to collection |
| `PATCH` | `/{id}/artifacts/{entry_id}/exclude` | Exclude artifact as false positive |
| `DELETE` | `/{id}/artifacts/{entry_id}/exclude` | Restore excluded artifact |
| `GET` | `/{id}/catalog/{entry_id}/path-tags` | Get path-based tag suggestions |
| `PATCH` | `/{id}/catalog/{entry_id}/path-tags` | Update path segment approval status |
| `GET` | `/{id}/artifacts/{path}/files` | Get file tree |
| `GET` | `/{id}/artifacts/{path}/files/{file_path}` | Get file content |

### Key Constants
- `CONFIDENCE_THRESHOLD = 30` (Line 86 of marketplace_sources.py) - Entries below this are hidden from UI

### Schemas

**Location**: `skillmeat/api/schemas/marketplace.py`

| Model | Purpose |
|-------|---------|
| `CreateSourceRequest` | Create source from GitHub URL |
| `UpdateSourceRequest` | Update source metadata |
| `SourceResponse` | Source with metadata and scan status |
| `SourceListResponse` | Paginated source list |
| `CatalogEntryResponse` | Single detected artifact |
| `CatalogListResponse` | Paginated catalog entries |
| `ScanRequest` | Request to rescan source |
| `ScanResultDTO` | Scan result with artifacts and metrics |
| `ImportRequest` | Request to import artifacts |
| `ImportResultDTO` | Import result with status |
| `ExcludeArtifactRequest` | Mark artifact as false positive |
| `PathSegmentsResponse` | Path-based tag extraction results |
| `UpdateSegmentStatusRequest` | Approve/reject path segment |

---

## 4. REPOSITORY LAYER

### Location: `skillmeat/cache/repositories/`

(Inferred from imports in router)

| Component | Purpose |
|-----------|---------|
| `MarketplaceSourceRepository` | CRUD operations on MarketplaceSource |
| `MarketplaceCatalogRepository` | CRUD operations on MarketplaceCatalogEntry |
| `MarketplaceTransactionHandler` | Atomic updates across source and catalog |
| `NotFoundError` | Custom exception for missing resources |

---

## 5. FRONTEND: SOURCE DETAIL PAGE

### Source Detail Page

**Location**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/marketplace/sources/[id]/page.tsx`

Main page component for viewing and managing a marketplace source's catalog.

**Key Features**:
- Display source metadata (URL, owner, repo, trust level)
- Show detected artifacts in tabbed view
- Filter by type, status, confidence
- Sort by name, date, confidence
- View/edit source details
- Rescan source
- Bulk import artifacts
- Exclude false positives

**Sub-components** (same directory in `components/`):

| Component | Purpose |
|-----------|---------|
| `source-toolbar.tsx` | Controls for rescan, sort, filter, view mode toggle |
| `catalog-list.tsx` | List or grid view of detected artifacts |
| `catalog-tabs.tsx` | Tabbed interface (All Artifacts, Imported, Excluded) |
| `excluded-list.tsx` | List of excluded entries with restore option |

### API Client Functions

**Location**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/lib/api/marketplace.ts`

| Function | Purpose |
|-----------|---------|
| `inferUrl(url)` | Parse GitHub URL to extract owner/repo |
| `getPathTags(sourceId, entryId)` | Fetch path-based tag suggestions |
| `updatePathTagStatus(sourceId, entryId, segment, status)` | Approve/reject path segment |

### Custom Hooks

**Location**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/useMarketplaceSources.ts`

| Hook | Purpose |
|------|---------|
| `useSource(sourceId)` | Fetch source metadata |
| `useSourceCatalog(sourceId, filters)` | Fetch paginated artifacts with filtering |
| `useRescanSource(sourceId)` | Trigger and monitor rescan |
| `useImportArtifacts(sourceId)` | Bulk import artifacts |
| `useExcludeCatalogEntry(sourceId)` | Mark artifact as false positive |

### Components

**Location**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/marketplace/`

| Component | Purpose |
|-----------|---------|
| `source-card.tsx` | Card display for source preview |
| `add-source-modal.tsx` | Modal to add new source |
| `edit-source-modal.tsx` | Modal to edit source metadata |
| `delete-source-dialog.tsx` | Confirmation dialog for deletion |
| `exclude-artifact-dialog.tsx` | Dialog to exclude artifact with reason |
| `path-tag-review.tsx` | Component for reviewing path-based tags |

### Type Definitions

**Location**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/types/marketplace.ts`

```typescript
interface Source {
  id: string;
  repo_url: string;
  owner: string;
  repo_name: string;
  ref: string;
  root_hint?: string;
  description?: string;
  notes?: string;
  trust_level: 'untrusted' | 'basic' | 'verified' | 'official';
  visibility: 'private' | 'internal' | 'public';
  scan_status: 'pending' | 'scanning' | 'success' | 'error';
  artifact_count: number;
  last_sync_at?: string;
  last_error?: string;
  created_at: string;
  updated_at: string;
}

interface CatalogEntry {
  id: string;
  source_id: string;
  artifact_type: ArtifactType;
  name: string;
  path: string;
  upstream_url: string;
  detected_version?: string;
  detected_sha?: string;
  detected_at: string;
  confidence_score: number;  // 0-100
  raw_score?: number;
  score_breakdown?: Record<string, number>;
  status: 'new' | 'updated' | 'removed' | 'imported' | 'excluded';
  import_date?: string;
  import_id?: string;
  excluded_at?: string;
  excluded_reason?: string;
  metadata?: Record<string, any>;
}

interface CatalogFilters {
  type?: ArtifactType;
  status?: CatalogStatus;
  minConfidence?: number;
  search?: string;
}
```

---

## 6. KEY ARCHITECTURAL PATTERNS

### Confidence Scoring System

**Location**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/heuristic_detector.py`

1. **Heuristic Detection**: Analyzes files to assign confidence score (0-100)
2. **Score Breakdown**: JSON breakdown of scoring components
3. **Threshold Filtering**: CONFIDENCE_THRESHOLD=30 (entries <30 hidden)
4. **Raw Score**: Pre-normalization value stored for analysis

### Deduplication

**Strategy**:
- `upstream_url` field is unique indexed → prevents duplicate catalog entries
- `status` field tracks import state (already handles duplication across imports)
- UUID primary key ensures no collision

### User Exclusion

**Mechanism**:
- User marks artifact as "not an artifact" with optional reason
- `excluded_at` timestamp set, `status` becomes "excluded"
- `excluded_reason` stored for audit trail
- Separate UI tab for reviewing excluded items

### Path-Based Tag Extraction

**Location**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/path_tags.py`

1. **Extraction**: PathSegmentExtractor analyzes artifact path
2. **Approval**: User approves/rejects individual segments
3. **Storage**: `path_segments` JSON array in CatalogEntry
4. **API**: Endpoints for fetching and updating segment status

### Testing

**Location**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/tests/test_marketplace_performance.py`

Performance tests for marketplace operations.

**E2E Tests**:
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/tests/e2e/marketplace.spec.ts`
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/tests/e2e/marketplace-sources.spec.ts`
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/tests/e2e/marketplace-exclusion.spec.ts`

**Unit Tests**:
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/__tests__/marketplace/SourceDetailPage.test.tsx`
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/__tests__/components/marketplace/path-tag-review.test.tsx`

---

## 7. MIGRATIONS

**Location**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/migrations/versions/`

| Migration | Changes |
|-----------|---------|
| `20251212_1537_add_description_notes_to_marketplace_sources.py` | Added `description` and `notes` fields to MarketplaceSource |

---

## 8. KEY DATA FLOWS

### Scan Flow
1. User creates source → POST `/api/v1/marketplace/sources`
2. Router creates MarketplaceSource record (status='pending')
3. User triggers scan → POST `/api/v1/marketplace/sources/{id}/rescan`
4. GitHubScanner.scan_repository() fetches GitHub tree
5. HeuristicDetector identifies artifacts, assigns confidence scores
6. DiffEngine compares with previous scan → new/updated/removed status
7. Results stored as MarketplaceCatalogEntry records
8. Frontend polls for completion

### Import Flow
1. User selects artifacts → POST `/api/v1/marketplace/sources/{id}/import`
2. ImportCoordinator handles conflict resolution
3. Artifacts copied to collection
4. CatalogEntry.status → "imported", import_date set
5. CatalogEntry.import_id → points to imported artifact

### Exclusion Flow
1. User marks artifact as false positive
2. PATCH `/api/v1/marketplace/sources/{id}/artifacts/{entry_id}/exclude`
3. excluded_at timestamp set, excluded_reason stored
4. status → "excluded"
5. No longer appears in main catalog view, only in Excluded tab
6. Can be restored with DELETE endpoint

---

## 9. COMPLETE FILE PATHS REFERENCE

### Backend Files
- Detection: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/github_scanner.py`
- Scoring: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/heuristic_detector.py`
- Diff Tracking: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/diff_engine.py`
- Import Logic: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/import_coordinator.py`
- Link Extraction: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/link_harvester.py`
- Observability: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/observability.py`
- Path Tags: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/path_tags.py`
- GitHub Metadata: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/github_metadata.py`

### Database
- Models: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/models.py` (lines 1173+)
- Repositories: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/repositories/`

### API
- Router: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/marketplace_sources.py`
- Marketplace Router: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/marketplace.py`
- Schemas: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py`

### Frontend
- Source Detail Page: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/marketplace/sources/[id]/page.tsx`
- Page Sub-components: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/marketplace/sources/[id]/components/`
- API Client: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/lib/api/marketplace.ts`
- Hooks: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/useMarketplaceSources.ts`
- Components: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/marketplace/`
- Types: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/types/marketplace.ts`

### Tests
- Performance: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/tests/test_marketplace_performance.py`
- E2E: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/tests/e2e/marketplace*.spec.ts`
- Unit: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/__tests__/marketplace/`

---

## 10. SUMMARY TABLE

| Aspect | File Location | Key Classes/Functions |
|--------|---------------|----------------------|
| **Detection** | `skillmeat/core/marketplace/github_scanner.py` | GitHubScanner, scan_repository() |
| **Scoring** | `skillmeat/core/marketplace/heuristic_detector.py` | HeuristicDetector, detect_artifacts_in_tree() |
| **DB Models** | `skillmeat/cache/models.py` (lines 1173, 1368) | MarketplaceSource, MarketplaceCatalogEntry |
| **API Router** | `skillmeat/api/routers/marketplace_sources.py` | All endpoints, ~21 handlers |
| **Frontend Page** | `skillmeat/web/app/marketplace/sources/[id]/page.tsx` | Source Detail page + 4 sub-components |
| **Frontend Hooks** | `skillmeat/web/hooks/useMarketplaceSources.ts` | Query/mutation hooks (5 hooks) |
| **Types** | `skillmeat/web/types/marketplace.ts` | Source, CatalogEntry, filters interfaces |
