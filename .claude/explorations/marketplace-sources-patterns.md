# Marketplace Sources - Architectural Patterns & Integration Guide

Summary of key architectural patterns, layering, and recommended integration points for confidence score enhancements.

---

## Architecture Overview

### Layered Architecture (Router → Service → Repository → Database)

```
┌─────────────────────────────────────────────────────┐
│ HTTP Layer (FastAPI Routers)                        │
│ - marketplace_sources.py (10 endpoints)             │
│ - Input validation (Pydantic schemas)               │
│ - Error handling (HTTPException)                    │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│ Service Layer (Business Logic)                      │
│ - GitHubScanner: repository scanning                │
│ - ImportCoordinator: conflict resolution            │
│ - TransactionHandler: atomic operations             │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│ Repository Layer (Data Access)                      │
│ - MarketplaceSourceRepository                       │
│ - MarketplaceCatalogRepository                      │
│ - MarketplaceTransactionHandler                     │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│ Database Layer (SQLAlchemy ORM)                     │
│ - MarketplaceSource model                           │
│ - MarketplaceCatalogEntry model                     │
└─────────────────────────────────────────────────────┘
```

### Data Flow: Scan Operation

```
1. HTTP Request (POST /sources/{id}/rescan)
   ↓
2. Router: rescan_source()
   - Fetch source from DB
   - Update status = "scanning"
   ↓
3. Service: GitHubScanner.scan_repository()
   - Fetch repository tree from GitHub
   - Apply heuristic detection
   - Calculate confidence scores
   - Return list of detected artifacts
   ↓
4. Repository: TransactionHandler context manager
   - Update source: status, artifact_count, timestamps
   - Create new catalog entries with detected artifacts
   - Atomic replacement of old entries
   ↓
5. Database: sqlite3
   - Write updated source
   - Write new catalog entries
   ↓
6. HTTP Response (ScanResultDTO)
   - Status, counts, timing
```

### Data Flow: Artifact Filtering

```
1. HTTP Request (GET /sources/{id}/artifacts?min_confidence=50)
   ↓
2. Router: list_artifacts()
   - Validate source exists
   - Apply confidence threshold logic:
     * Default: min = 30 (CONFIDENCE_THRESHOLD)
     * Override: min = user-provided or 30 (whichever stricter)
     * include_below_threshold overrides threshold
   ↓
3. Repository: CatalogRepository.get_source_catalog()
   - Filter by:
     * source_id
     * artifact_type(s)
     * status(es)
     * confidence_score >= min, <= max
   - Return list of entries
   ↓
4. Response: CatalogListResponse
   - Paginated items
   - Status/type aggregations
```

---

## Confidence Score System

### Scoring & Storage

```
Detection (github_scanner.py)
├── Heuristic matching: file patterns, names, structures
├── Frontmatter parsing: optional markdown metadata
├── Multiple signals: README, pyproject.toml, package.json, etc.
└── Produces: confidence_score (0-100), raw_score, score_breakdown

Storage (MarketplaceCatalogEntry)
├── confidence_score: PRIMARY filtering criterion (0-100 INT)
├── raw_score: Pre-normalization score (optional INT)
└── score_breakdown: Component breakdown (JSON)

Filtering (marketplace_sources.py)
├── Default threshold: 30% (CONFIDENCE_THRESHOLD)
├── Query parameter: min_confidence, max_confidence, include_below_threshold
├── Applied at: catalog entry query time (not detection time)
└── Aggregation: counts_by_status + counts_by_type in response
```

### Threshold Logic Implementation

**Location**: `marketplace_sources.py` lines 839-854

```python
CONFIDENCE_THRESHOLD = 30  # Constant at module level

# In list_artifacts() endpoint:
effective_min_confidence = min_confidence

if not include_below_threshold:
    # Apply threshold by default
    if effective_min_confidence is None:
        effective_min_confidence = CONFIDENCE_THRESHOLD
    else:
        # If user provided min_confidence, take the stricter of the two
        effective_min_confidence = max(
            effective_min_confidence, CONFIDENCE_THRESHOLD
        )

# Then query catalog with effective_min_confidence
entries = catalog_repo.get_source_catalog(
    source_id=source_id,
    min_confidence=effective_min_confidence,
    max_confidence=max_confidence,
)
```

---

## Skip Preferences Pattern

### Current Implementation

**File**: `skillmeat/core/skip_preferences.py`

**Storage**: `.claude/.skillmeat_skip_prefs.toml` (per-project)

**Structure**:
```toml
[metadata]
version = "1.0.0"
last_updated = "2025-12-04T10:00:00Z"

[[skips]]
artifact_key = "skill:canvas-design"
skip_reason = "Already in collection"
added_date = "2025-12-04T10:00:00Z"

[[skips]]
artifact_key = "command:my-command"
skip_reason = "Using alternative implementation"
added_date = "2025-12-04T11:00:00Z"
```

**API**:
```python
manager = SkipPreferenceManager(project_path)

# Add skip
manager.add_skip("skill:my-skill", "Already in collection")

# Check skip
is_skipped = manager.is_skipped("skill:my-skill")

# Get skip reason
skip = manager.get_skip_by_key("skill:my-skill")
if skip:
    print(skip.skip_reason)

# List all skips
all_skips = manager.get_skipped_list()

# Remove skip
manager.remove_skip("skill:my-skill")

# Clear all
manager.clear_skips()
```

### Thread Safety

- Uses `threading.Lock` for all file operations
- Load + modify + save pattern within lock
- Atomic write with temp file + rename

---

## Transaction Pattern

### Pattern for Atomic Updates

**Location**: `marketplace_sources.py` lines 688-716 (scan), 1034-1055 (import)

```python
# Context manager ensures atomicity
with transaction_handler.scan_update_transaction(source_id) as ctx:
    # Update source metadata
    ctx.update_source_status(
        status="success",
        artifact_count=scan_result.artifacts_found,
        error_message=None,
    )

    # Replace catalog entries
    ctx.replace_catalog_entries(new_entries)

    # Both operations committed together or both rolled back on error
```

### Use Cases

1. **Scan Update**:
   - Update MarketplaceSource status + timestamp
   - Replace all MarketplaceCatalogEntry records
   - Prevents partial updates if scan fails midway

2. **Import Update**:
   - Mark successfully imported entries with status="imported", import_id
   - Mark failed entries with error messages
   - Prevents orphaned entries

---

## Status Lifecycle

### Source Status

```
┌─────────┐
│ pending │ (initial state after creation)
└────┬────┘
     │ (rescan triggered)
     ▼
┌────────┐
│scanning│ (scan in progress)
└────┬────┘
     │
     ├─────────────┬──────────────┐
     │             │              │
     ▼             ▼              ▼
┌─────────┐  ┌────────┐      ┌─────────┐
│ success │  │ error  │      │ pending │
└─────────┘  └────────┘      └─────────┘
    │            │              │
    └────────────┴──────────────┘
         (retry rescan)
```

### Catalog Entry Status

```
Detection:   new
             ↓
On Update:   updated (if found again with new SHA)
             ↓
On Import:   imported (moved to user collection)
             ↓
On Removal:  removed (no longer found in repo)
```

---

## Confidence Score Enhancement Patterns

### Current Pattern for Filtering

```python
# Router receives query parameters
list_artifacts(
    min_confidence=Optional[int],
    max_confidence=Optional[int],
    include_below_threshold=bool,
)

# Router applies threshold logic
if not include_below_threshold and min_confidence is None:
    min_confidence = CONFIDENCE_THRESHOLD

# Repository performs query with filters
entries = catalog_repo.get_source_catalog(
    min_confidence=min_confidence,
    max_confidence=max_confidence,
)
```

### Recommended Integration Point for Enhancements

**For new confidence-related features:**

1. **Detection Time** (`core/marketplace/heuristic_detector.py`):
   - Modify scoring algorithm
   - Update score_breakdown
   - Change confidence calculation

2. **Storage Time** (`cache/models.py` MarketplaceCatalogEntry):
   - Add new columns if needed (e.g., `maturity_level`, `reviewer_score`)
   - Extend score_breakdown structure

3. **Query Time** (`cache/repositories.py` get_source_catalog()):
   - Add new filter parameters
   - Implement new filtering logic

4. **API Time** (`api/routers/marketplace_sources.py`):
   - Add new query parameters
   - Update schema responses
   - Implement new filtering options

5. **Threshold Configuration** (`api/routers/marketplace_sources.py` lines 71-72):
   - Make `CONFIDENCE_THRESHOLD` configurable
   - Consider per-source thresholds
   - Support role-based thresholds

---

## Path Traversal Prevention

### Validation Points

**1. Router Layer** (`marketplace_sources.py` lines 85-156):
```python
validate_file_path(artifact_path)
```

Checks:
- No null bytes (`\x00`)
- No parent directory references (`..`)
- No absolute paths (starting with `/`)
- No URL-encoded traversal (`%2e%2e`)
- Only forward slashes in normalized paths

**2. Schema Layer** (`marketplace.py` lines 569-608):
```python
@field_validator("root_hint")
def validate_root_hint(cls, v: str | None) -> str | None:
```

Checks:
- URL decode before checking
- No `..` sequences
- No absolute paths
- No null bytes
- No invalid characters: `<>"|?*`

### Pattern for Future Enhancements

Use same validation pattern:
1. URL decode input
2. Check for traversal sequences
3. Check for absolute paths
4. Check for null bytes
5. Check for invalid characters
6. Normalize path separators
7. Return cleaned value

---

## Error Handling Patterns

### HTTP Exception Pattern

```python
# 400 Bad Request
raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Descriptive error message"
)

# 404 Not Found
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail=f"Resource '{id}' not found"
)

# 409 Conflict
raise HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail="Resource already exists"
)

# 422 Unprocessable Entity
raise HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail="Validation failed: ..."
)

# 500 Internal Server Error
try:
    operation()
except Exception as e:
    logger.exception(f"Operation failed: {e}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to {operation}: {str(e)}"
    )
```

### Logging Pattern

Always log before raising:
```python
logger.warning(f"Specific issue: {details}")
raise HTTPException(status_code=404, detail="Not found")

logger.error(f"Operation failed: {e}", exc_info=True)
raise HTTPException(status_code=500, detail="Internal error")
```

---

## Pagination Pattern

### Cursor-Based Pagination

```python
# List request
list_sources(
    limit: int = Query(50, ge=1, le=100),  # Max 100 per page
    cursor: Optional[str] = Query(None),   # From previous response
)

# Repository returns
PaginatedResult(
    items: List[T],           # Current page items
    has_more: bool,           # Whether more pages exist
)

# Response includes
PageInfo(
    has_next_page: bool,      # From has_more
    has_previous_page: bool,  # True if cursor provided
    start_cursor: str,        # First item ID
    end_cursor: str,          # Last item ID for next query
    total_count: Optional[int], # Usually None for efficiency
)
```

---

## Key Integration Checklist

### For Implementing Confidence Score Enhancements:

- [ ] Update heuristic detector to calculate enhanced score
- [ ] Add new fields to MarketplaceCatalogEntry if needed
- [ ] Update score_breakdown JSON structure
- [ ] Add query filters to CatalogRepository.get_source_catalog()
- [ ] Add query parameters to list_artifacts() endpoint
- [ ] Update CatalogEntryResponse schema
- [ ] Add tests for new filtering logic
- [ ] Document threshold logic in endpoint descriptions
- [ ] Consider backward compatibility with existing filters
- [ ] Test path traversal validation with new parameters
- [ ] Update API documentation and examples

### For Implementing Exclusion/Ignore Features:

- [ ] Decide: per-source excludes vs global skip list vs both
- [ ] If per-source: extend MarketplaceSource.manual_map or add new field
- [ ] If global: integrate with existing SkipPreferenceManager
- [ ] Add exclusion logic to list_artifacts() filtering
- [ ] Update CatalogListResponse with excluded count
- [ ] Add API endpoints for managing exclusions
- [ ] Add tests for exclusion logic
- [ ] Document in endpoint descriptions
- [ ] Consider: should excluded entries still appear with flag?

---

## Testing Patterns

### Router Tests

```python
from fastapi.testclient import TestClient

client = TestClient(app)

def test_list_artifacts_with_confidence_filter():
    response = client.get(
        "/marketplace/sources/src-123/artifacts?min_confidence=50"
    )
    assert response.status_code == 200
    data = response.json()
    assert all(e["confidence_score"] >= 50 for e in data["items"])

def test_path_traversal_prevention():
    response = client.get(
        "/marketplace/sources/src-123/artifacts/../../../etc/passwd/files"
    )
    assert response.status_code == 400
```

### Repository Tests

```python
def test_filter_by_confidence():
    entries = catalog_repo.get_source_catalog(
        source_id="src-123",
        min_confidence=50,
    )
    assert all(e.confidence_score >= 50 for e in entries)
```

---

## Migration Guide for New Features

### Adding a New Confidence-Related Filter:

1. **Step 1**: Add parameter to `CreateSourceRequest` or `UpdateSourceRequest`
   - File: `api/schemas/marketplace.py`
   - Add field with validator if needed

2. **Step 2**: Update `MarketplaceSource` or `MarketplaceCatalogEntry` model
   - File: `cache/models.py`
   - Add column with appropriate constraints

3. **Step 3**: Update repository method
   - File: `cache/repositories.py`
   - Add parameter to `get_source_catalog()`
   - Implement filtering logic

4. **Step 4**: Update router endpoint
   - File: `api/routers/marketplace_sources.py`
   - Add query parameter
   - Implement filtering logic
   - Document in endpoint docstring

5. **Step 5**: Update response schemas
   - File: `api/schemas/marketplace.py`
   - Add field to `CatalogEntryResponse` if exposing new data

6. **Step 6**: Add tests
   - File: `tests/api/test_marketplace_sources.py`
   - Test filtering, validation, edge cases

7. **Step 7**: Update API documentation
   - Update endpoint descriptions
   - Add examples to schema

8. **Step 8**: Migration if needed
   - File: `cache/migrations/versions/`
   - Create Alembic migration for schema changes

---

## Summary

**Architecture**: Strict layered design (Router → Service → Repository → DB)

**Data Pattern**: Confidence stored in DB, filtering at query time

**Exclusion Pattern**: Skip preferences system (thread-safe, per-project TOML)

**Atomic Pattern**: Transaction context managers for multi-step operations

**Validation Pattern**: Multi-layer (schema + router), path traversal hardened

**Pagination**: Cursor-based for efficiency, no total counts

**Error Handling**: Always log before raising, descriptive detail messages

**Testing**: FastAPI TestClient for router, direct repo calls for unit tests

