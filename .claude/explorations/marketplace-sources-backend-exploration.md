# Marketplace Sources Backend - Exploration Report

## Overview

Complete inventory of backend API files related to marketplace sources, including CRUD endpoints, catalog detection/scanning logic, existing exclusion patterns, and database models.

**Date**: 2025-12-31
**Status**: Complete exploration of all marketplace source-related backend infrastructure

---

## 1. Router Layer (API Endpoints)

### Primary Marketplace Sources Router

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/marketplace_sources.py`

**Purpose**: Full CRUD operations for GitHub repository sources and marketplace catalog browsing

**HTTP Endpoints**:

| Endpoint | Method | Status | Purpose |
|----------|--------|--------|---------|
| `/marketplace/sources` | POST | ✅ Implemented | Create new GitHub source (API-001) |
| `/marketplace/sources` | GET | ✅ Implemented | List all sources with pagination (API-001) |
| `/marketplace/sources/{id}` | GET | ✅ Implemented | Get source by ID (API-001) |
| `/marketplace/sources/{id}` | PATCH | ✅ Implemented | Update source configuration (API-001) |
| `/marketplace/sources/{id}` | DELETE | ✅ Implemented | Delete source and catalog entries (API-001) |
| `/marketplace/sources/{id}/rescan` | POST | ✅ Implemented | Trigger repository rescan (API-002) |
| `/marketplace/sources/{id}/artifacts` | GET | ✅ Implemented | List artifacts with filters (API-003) |
| `/marketplace/sources/{id}/import` | POST | ✅ Implemented | Import artifacts to collection (API-004) |
| `/marketplace/sources/{id}/artifacts/{path}/files` | GET | ✅ Implemented | Get file tree for artifact (API-005) |
| `/marketplace/sources/{id}/artifacts/{path}/files/{file_path}` | GET | ✅ Implemented | Get file content (API-006) |

**Key Features**:
- Cursor-based pagination for efficiency
- Confidence score filtering (30% threshold for hiding low-quality entries)
- Path traversal attack prevention (validation in lines 85-156)
- GitHub API rate limit handling with retry-after headers
- File content caching (1-2 hour TTL)
- Atomic transaction handling for scan and import operations

**Key Helper Functions**:
- `validate_file_path()` - Security: prevent path traversal attacks
- `validate_source_id()` - Validate source ID format
- `parse_repo_url()` - Extract owner/repo from GitHub URL
- `source_to_response()` - ORM to API response conversion (lines 207-234)
- `entry_to_response()` - Catalog entry ORM to API response (lines 237-262)
- `parse_rate_limit_retry_after()` - Extract retry time from GitHub errors

---

### Secondary Marketplace Router

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/marketplace.py`

**Purpose**: Broker-based marketplace listings, installation, and publishing

**Endpoints**:
- `GET /marketplace/listings` - Browse listings with filtering
- `GET /marketplace/listings/{listing_id}` - Get listing details
- `POST /marketplace/install` - Install from marketplace
- `POST /marketplace/publish` - Publish bundle to marketplace
- `GET /marketplace/brokers` - List available brokers
- `POST /marketplace/compliance/*` - Compliance scanning and consent tracking

**Note**: This is separate from the sources router; handles broker integration, not direct source scanning.

---

## 2. Database Models (SQLAlchemy ORM)

### MarketplaceSource Model

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/models.py`
**Lines**: 1173-1272

**Table**: `marketplace_sources`

**Core Attributes**:
```python
id                          # UUID primary key
repo_url                    # GitHub URL (UNIQUE)
owner                       # Repo owner name
repo_name                   # Repo name
ref                         # Branch/tag/SHA (default: "main")
root_hint                   # Optional subdirectory hint
description                 # User description (max 500 chars)
notes                       # Internal notes (max 2000 chars)
manual_map                  # JSON override paths
access_token_id             # Encrypted PAT reference
trust_level                 # "untrusted", "basic", "verified", "official"
visibility                  # "private", "internal", "public"
enable_frontmatter_detection # Boolean - parse MD frontmatter for hints
last_sync_at                # Last successful scan timestamp
last_error                  # Error message if scan failed
scan_status                 # "pending", "scanning", "success", "error"
artifact_count              # Cached count of discovered artifacts
created_at                  # Timestamp
updated_at                  # Timestamp
```

**Relationships**:
- `entries: List[MarketplaceCatalogEntry]` - Discovered artifacts from this source (cascade delete)

**Indexes**:
- `idx_marketplace_sources_repo_url` (UNIQUE)
- `idx_marketplace_sources_last_sync` (TTL queries)
- `idx_marketplace_sources_scan_status`

---

### MarketplaceCatalogEntry Model

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/models.py`
**Lines**: 1363-1462

**Table**: `marketplace_catalog_entries`

**Core Attributes**:
```python
id                      # UUID primary key
source_id              # FK to marketplace_sources (cascade delete)
artifact_type          # "skill", "command", "agent", "mcp_server", "hook", etc.
name                   # Artifact name from detection
path                   # Path within repository
upstream_url           # Full GitHub URL to artifact
detected_version       # Extracted version if available
detected_sha           # Git commit SHA at detection
detected_at            # Detection timestamp
confidence_score       # Heuristic confidence 0-100 (validated 0-100)
raw_score             # Raw score before normalization
score_breakdown       # JSON breakdown of scoring components
status                # "new", "updated", "removed", "imported"
import_date           # When imported to collection
import_id             # Reference to imported artifact ID
metadata_json         # Additional detection metadata
created_at            # Timestamp
updated_at            # Timestamp
```

**Relationships**:
- `source: MarketplaceSource` - Parent source

**Indexes**:
- `idx_catalog_entries_source_id` (query by source)
- `idx_catalog_entries_status` (filter by status)
- `idx_catalog_entries_type` (filter by artifact type)
- `idx_catalog_entries_upstream_url` (deduplication)
- `idx_catalog_entries_source_status` (composite)

**Constraints**:
- Artifact type must be in defined list
- Status must be "new", "updated", "removed", or "imported"
- Confidence score must be 0-100

---

## 3. Request/Response Schemas

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py`

### CreateSourceRequest (Lines 483-622)

**Fields**:
- `repo_url` (str) - Full GitHub repository URL
- `ref` (str, default="main") - Branch, tag, or SHA
- `root_hint` (Optional[str]) - Subdirectory path hint
- `access_token` (Optional[str]) - GitHub PAT (not stored)
- `manual_map` (Optional[Dict]) - Manual override paths
- `trust_level` (Literal) - "untrusted", "basic", "verified", "official"
- `description` (Optional[str], max 500) - User description
- `notes` (Optional[str], max 2000) - Internal notes
- `enable_frontmatter_detection` (bool) - Parse markdown frontmatter

**Validators**:
- `validate_description_length()` - Max 500 characters
- `validate_notes_length()` - Max 2000 characters
- `validate_root_hint()` - Path traversal prevention (lines 569-608)
  - Blocks `..` sequences
  - Blocks absolute paths
  - Blocks null bytes
  - Blocks invalid characters: `<>"|?*`

### UpdateSourceRequest (Lines 625-707)

**Fields**: Same as CreateSourceRequest but all optional (PATCH semantics)

**Validators**: Same validation as CreateSourceRequest

### SourceResponse (Lines 754-867)

**Fields**:
- All MarketplaceSource attributes converted to API response
- Includes timestamps in ISO 8601 format

### CatalogEntryResponse (Lines 869-923)

**Fields**:
- All MarketplaceCatalogEntry attributes for API responses
- `confidence_score` - Primary sorting/filtering criterion

### CatalogListResponse (Lines 925-997)

**Fields**:
- `items: List[CatalogEntryResponse]` - Paginated entries
- `page_info: PageInfo` - Cursor-based pagination metadata
- `counts_by_status: Dict[str, int]` - Aggregated status counts
- `counts_by_type: Dict[str, int]` - Aggregated type counts

---

## 4. Core Business Logic

### Scanning & Detection

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/github_scanner.py`

**Key Functions**:
- `scan_github_source()` - Main entry point for repository scanning
- Heuristic detection to identify artifacts in repository
- Confidence score calculation based on multiple signals

**Detection Features**:
- File pattern matching (SKILL.md, pyproject.toml, etc.)
- Frontmatter parsing for artifact type hints (when enabled)
- Confidence score breakdown for debugging

### Import Coordination

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/import_coordinator.py`

**Key Classes**:
- `ImportCoordinator` - Orchestrates artifact import operations
- `ConflictStrategy` - Enum: "skip", "overwrite", "rename"

**Features**:
- Handles conflict resolution during import
- Updates catalog entry statuses atomically
- Tracks import IDs for audit trail

### Transaction Handling

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/repositories.py`

**Key Classes**:
- `MarketplaceTransactionHandler` - Atomic operation support
  - `scan_update_transaction()` - Update source and catalog atomically
  - `import_transaction()` - Mark entries as imported atomically
  - `replace_catalog_entries()` - Full catalog replacement after scan

---

## 5. Existing Exclusion/Skip Patterns

### Skip Preferences System

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/skip_preferences.py`

**Purpose**: User skip list for discovery operations (already implemented)

**Key Components**:

#### SkipPreference Model
```python
artifact_key: str          # Format: "type:name"
skip_reason: str           # Human-readable reason
added_date: datetime       # When skip was added
```

#### SkipPreferenceFile
- Stored at `.claude/.skillmeat_skip_prefs.toml`
- Contains metadata and list of skips
- No duplicates validation

#### SkipPreferenceManager
- Thread-safe file operations
- Methods:
  - `add_skip(artifact_key, reason)` - Add skip preference
  - `remove_skip(artifact_key)` - Remove skip preference
  - `is_skipped(artifact_key)` - Check if artifact is skipped
  - `get_skipped_list()` - Get all skip preferences
  - `clear_skips()` - Clear all preferences
  - `load_skip_prefs()` - Load from file
  - `save_skip_prefs()` - Save to file (atomic)

**Thread Safety**:
- Uses `threading.Lock` for all file operations
- Atomic writes with temp file + rename pattern

---

## 6. Confidence Score System

### Filtering in API

**Router**: `/marketplace/sources/{id}/artifacts` endpoint (lines 787-922)

**Key Parameters**:
- `min_confidence` (0-100) - Filter entries >= this score
- `max_confidence` (0-100) - Filter entries <= this score
- `include_below_threshold` (bool) - Override 30% default threshold

**Threshold Logic** (lines 839-854):
- Default behavior: Hide entries below 30% confidence
- When `include_below_threshold=True`: Show ALL entries
- User-provided `min_confidence` takes stricter threshold

**Constant**:
```python
CONFIDENCE_THRESHOLD = 30  # Line 72
```

### Score Storage in Database

**CatalogEntry Fields**:
- `confidence_score` (int, 0-100) - Primary score
- `raw_score` (Optional[int]) - Before normalization
- `score_breakdown` (Optional[dict]) - Component breakdown (JSON)

---

## 7. Repositories & Data Access

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/repositories.py`

**Key Classes**:

### MarketplaceSourceRepository
- `create(source)` - Create new source
- `get_by_id(source_id)` - Fetch by ID
- `get_by_repo_url(repo_url)` - Fetch by URL (UNIQUE constraint)
- `update(source)` - Update source
- `delete(source_id)` - Delete source and cascade catalog
- `list_paginated(limit, cursor)` - Cursor-based pagination

### MarketplaceCatalogRepository
- `create(entry)` - Create catalog entry
- `get_by_id(entry_id)` - Fetch by ID
- `list_paginated(source_id, limit, cursor)` - Paginated query
- `get_source_catalog(source_id, artifact_types, statuses, min_confidence, max_confidence)` - Filtered catalog
- `count_by_status(source_id)` - Status aggregation
- `count_by_type(source_id)` - Type aggregation
- `replace_catalog_entries(entries)` - Bulk replacement after scan

### MarketplaceTransactionHandler
- `scan_update_transaction(source_id)` - Context manager for atomic scan updates
  - `update_source_status(status, artifact_count, error_message)`
  - `replace_catalog_entries(new_entries)`
- `import_transaction(source_id)` - Context manager for import updates
  - `mark_imported(entry_ids, import_id)`
  - `mark_failed(entry_ids, error_message)`

---

## 8. File Structure Summary

```
skillmeat/
├── api/
│   ├── routers/
│   │   ├── marketplace.py              # Broker-based marketplace endpoints
│   │   └── marketplace_sources.py      # GitHub source CRUD + scanning
│   └── schemas/
│       └── marketplace.py              # All marketplace request/response models
├── cache/
│   ├── models.py                       # MarketplaceSource & MarketplaceCatalogEntry ORM
│   └── repositories.py                 # Data access layer for marketplace
├── core/
│   ├── marketplace/
│   │   ├── github_scanner.py           # Repository scanning & detection
│   │   ├── import_coordinator.py       # Import orchestration
│   │   ├── diff_engine.py              # Change detection (new/updated/removed)
│   │   ├── heuristic_detector.py       # Confidence scoring
│   │   └── observability.py            # Logging/monitoring
│   └── skip_preferences.py             # User skip list system (existing)
└── sources/
    ├── base.py                         # Abstract source interface
    ├── github.py                       # GitHub API client
    └── local.py                        # Local filesystem source
```

---

## 9. Scanning & Catalog Entry Flow

### Source Creation (POST /sources)
1. Validate repository URL
2. Parse owner/repo from URL
3. Check for duplicate URLs
4. Create MarketplaceSource with status="pending"
5. Return SourceResponse

### Catalog Rescan (POST /sources/{id}/rescan)
1. Fetch source by ID
2. Update status="scanning"
3. Call `GitHubScanner.scan_repository()`
4. For each detected artifact:
   - Create MarketplaceCatalogEntry with:
     - status="new" (initial detection)
     - confidence_score (heuristic result)
     - detected_at (scan timestamp)
     - detected_sha (commit SHA)
5. Replace catalog entries atomically (transaction)
6. Update source: status="success", artifact_count, last_sync_at
7. Return ScanResultDTO

### Artifact Filtering (GET /sources/{id}/artifacts)
1. Apply confidence threshold (default 30%)
2. Filter by artifact_type, status, confidence range
3. Return paginated CatalogListResponse with:
   - items: filtered entries
   - counts_by_status, counts_by_type (aggregates)

### Artifact Import (POST /sources/{id}/import)
1. Validate all entry_ids belong to source
2. Fetch catalog entries
3. Call `ImportCoordinator.import_entries()`
4. Mark successfully imported with status="imported", import_id
5. Mark failures with error messages
6. Return ImportResultDTO with counts and IDs

---

## 10. Key Security Features

### Path Traversal Prevention

**Validation Layers**:

1. **In Router** (`marketplace_sources.py` lines 85-156):
   - Reject null bytes
   - Normalize path separators
   - Reject absolute paths
   - Reject parent directory references (`..`)
   - Reject URL-encoded traversal (`%2e%2e`)

2. **In Schema** (`marketplace.py` lines 569-608):
   - Additional root_hint validation
   - Block invalid characters
   - URL decode before checking

### GitHub API Security

- Rate limit handling with retry-after headers
- Optional PAT support for private repos (not stored)
- Read-only file access via GitHub API

### Atomic Transactions

- Scan updates within transaction context
- Import updates within transaction context
- Prevents partial failures

---

## 11. Existing Patterns & Conventions

### Confidence-Based Filtering Pattern
```python
# Default: hide low-confidence entries
entries = catalog_repo.get_source_catalog(
    min_confidence=30,  # CONFIDENCE_THRESHOLD
)

# Override to show all
entries = catalog_repo.get_source_catalog()  # No filter
if not include_below_threshold and min_confidence is None:
    min_confidence = 30
```

### Status Lifecycle Pattern
- Catalog entries: "new" → "imported" or "updated" → "imported" or "removed"
- Sources: "pending" → "scanning" → "success" or "error"

### Transaction Pattern
```python
with transaction_handler.scan_update_transaction(source_id) as ctx:
    ctx.update_source_status(status="success", artifact_count=N)
    ctx.replace_catalog_entries(new_entries)
```

### Pagination Pattern
```python
# Cursor-based for efficiency
result = repo.list_paginated(limit=50, cursor=None)
# Returns: PaginatedResult(items=[], has_more=True)
# Client uses next_cursor from response for pagination
```

---

## 12. Important Constants & Defaults

| Constant | Value | Location | Purpose |
|----------|-------|----------|---------|
| `CONFIDENCE_THRESHOLD` | 30 | marketplace_sources.py:72 | Default confidence filter |
| `DEFAULT_TREE_TTL` | 3600 | github_cache.py | File tree cache duration |
| `DEFAULT_CONTENT_TTL` | 7200 | github_cache.py | File content cache duration |
| `SKIP_PREFS_VERSION` | "1.0.0" | skip_preferences.py | Skip preferences format version |
| `SKIP_PREFS_FILENAME` | ".skillmeat_skip_prefs.toml" | skip_preferences.py | Skip file location |

---

## Summary

**Total Files**: 16+ core files (routers, models, schemas, services, repositories)

**API Endpoints**: 10 marketplace source endpoints (CRUD, scan, import, file browsing)

**Database Models**: 2 main entities (MarketplaceSource, MarketplaceCatalogEntry)

**Exclusion/Skip System**: SkipPreferenceManager for user skip lists (thread-safe, TOML-based)

**Confidence Filtering**: Implemented with 30% default threshold and overridable option

**Security**: Path traversal prevention, rate limiting, atomic transactions, read-only GitHub access

**Performance**: Cursor-based pagination, file content caching (1-2 hours), efficient queries with indexes

