# Marketplace Sources Backend - File Reference

Quick lookup for all marketplace source-related files with line number references.

---

## Core Backend Files

### API Routers

| File | Lines | Purpose |
|------|-------|---------|
| `skillmeat/api/routers/marketplace_sources.py` | Full file | GitHub source CRUD endpoints (10 endpoints) |
| `skillmeat/api/routers/marketplace.py` | Full file | Broker-based marketplace endpoints |

### Database Models

| File | Lines | Content |
|------|-------|---------|
| `skillmeat/cache/models.py` | 1173-1272 | MarketplaceSource ORM model |
| `skillmeat/cache/models.py` | 1363-1462 | MarketplaceCatalogEntry ORM model |

### Request/Response Schemas

| File | Lines | Content |
|------|-------|---------|
| `skillmeat/api/schemas/marketplace.py` | 483-622 | CreateSourceRequest model |
| `skillmeat/api/schemas/marketplace.py` | 625-707 | UpdateSourceRequest model |
| `skillmeat/api/schemas/marketplace.py` | 754-867 | SourceResponse model |
| `skillmeat/api/schemas/marketplace.py` | 869-923 | CatalogEntryResponse model |
| `skillmeat/api/schemas/marketplace.py` | 925-997 | CatalogListResponse model |

### Data Access Layer

| File | Content |
|------|---------|
| `skillmeat/cache/repositories.py` | MarketplaceSourceRepository class |
| `skillmeat/cache/repositories.py` | MarketplaceCatalogRepository class |
| `skillmeat/cache/repositories.py` | MarketplaceTransactionHandler class |

### Core Business Logic

| File | Purpose |
|------|---------|
| `skillmeat/core/marketplace/github_scanner.py` | Repository scanning & detection |
| `skillmeat/core/marketplace/import_coordinator.py` | Artifact import orchestration |
| `skillmeat/core/marketplace/diff_engine.py` | Change detection (new/updated/removed) |
| `skillmeat/core/marketplace/heuristic_detector.py` | Confidence scoring |
| `skillmeat/core/marketplace/observability.py` | Logging/monitoring |

### Skip Preferences System (Existing)

| File | Lines | Content |
|------|-------|---------|
| `skillmeat/core/skip_preferences.py` | 1-50 | Constants & file format |
| `skillmeat/core/skip_preferences.py` | 48-128 | SkipPreference model |
| `skillmeat/core/skip_preferences.py` | 131-156 | SkipPreferenceMetadata model |
| `skillmeat/core/skip_preferences.py` | 159-333 | SkipPreferenceFile model |
| `skillmeat/core/skip_preferences.py` | 356-396 | Helper functions |
| `skillmeat/core/skip_preferences.py` | 411-674 | SkipPreferenceManager class |

### Source Abstraction

| File | Purpose |
|------|---------|
| `skillmeat/sources/base.py` | Abstract source interface |
| `skillmeat/sources/github.py` | GitHub API client |
| `skillmeat/sources/local.py` | Local filesystem source |

---

## Key Functions & Methods

### Router Helper Functions (marketplace_sources.py)

| Function | Lines | Purpose |
|----------|-------|---------|
| `validate_file_path()` | 85-156 | Security: path traversal prevention |
| `validate_source_id()` | 159-178 | Validate source ID format |
| `parse_repo_url()` | 181-204 | Extract owner/repo from URL |
| `source_to_response()` | 207-234 | ORM to API response conversion |
| `entry_to_response()` | 237-262 | Catalog entry ORM to response |
| `parse_rate_limit_retry_after()` | 265-287 | Extract retry time from errors |

### Router Endpoints (marketplace_sources.py)

| Endpoint | Lines | Method | Status |
|----------|-------|--------|--------|
| `create_source` | 309-375 | POST | ✅ Implemented |
| `list_sources` | 391-433 | GET | ✅ Implemented |
| `get_source` | 446-478 | GET | ✅ Implemented |
| `update_source` | 494-568 | PATCH | ✅ Implemented |
| `delete_source` | 584-613 | DELETE | ✅ Implemented |
| `rescan_source` | 641-760 | POST | ✅ Implemented |
| `list_artifacts` | 787-922 | GET | ✅ Implemented |
| `import_artifacts` | 953-1094 | POST | ✅ Implemented |
| `get_artifact_file_tree` | 1122-1254 | GET | ✅ Implemented |
| `get_artifact_file_content` | 1282-1403 | GET | ✅ Implemented |

### Schema Validators

| Class | Method | Lines | Validation |
|-------|--------|-------|-----------|
| CreateSourceRequest | validate_description_length | 533-549 | Max 500 chars |
| CreateSourceRequest | validate_notes_length | 551-567 | Max 2000 chars |
| CreateSourceRequest | validate_root_hint | 569-608 | Path traversal, null bytes, invalid chars |
| UpdateSourceRequest | validate_root_hint | 665-707+ | Same as CreateSourceRequest |

### SkipPreferenceManager Methods

| Method | Lines | Purpose |
|--------|-------|---------|
| `__init__` | 435-442 | Initialize manager |
| `load_skip_prefs()` | 453-508 | Load from TOML file |
| `save_skip_prefs()` | 510-561 | Save to file (atomic) |
| `add_skip()` | 563-589 | Add skip preference |
| `remove_skip()` | 591-612 | Remove skip preference |
| `is_skipped()` | 614-627 | Check if artifact is skipped |
| `get_skip_by_key()` | 629-642 | Get skip by artifact_key |
| `get_skipped_list()` | 644-654 | Get all skips |
| `clear_skips()` | 656-674 | Clear all skips |

---

## Important Constants

| Constant | Value | File | Line |
|----------|-------|------|------|
| `CONFIDENCE_THRESHOLD` | 30 | marketplace_sources.py | 72 |
| `SKIP_PREFS_VERSION` | "1.0.0" | skip_preferences.py | 40 |
| `SKIP_PREFS_FILENAME` | ".skillmeat_skip_prefs.toml" | skip_preferences.py | 33 |
| `SKIP_PREFS_RELATIVE_PATH` | ".claude/.skillmeat_skip_prefs.toml" | skip_preferences.py | 37 |
| `DEFAULT_TREE_TTL` | 3600 | github_cache.py | N/A |
| `DEFAULT_CONTENT_TTL` | 7200 | github_cache.py | N/A |

---

## Database Tables & Relationships

### marketplace_sources Table

```
Columns:
- id (PRIMARY KEY)
- repo_url (UNIQUE)
- owner
- repo_name
- ref
- root_hint
- description
- notes
- manual_map
- access_token_id
- trust_level
- visibility
- enable_frontmatter_detection
- last_sync_at
- last_error
- scan_status
- artifact_count
- created_at
- updated_at

Indexes:
- idx_marketplace_sources_repo_url
- idx_marketplace_sources_last_sync
- idx_marketplace_sources_scan_status

Relationships:
- entries (MarketplaceCatalogEntry) - cascade delete
```

### marketplace_catalog_entries Table

```
Columns:
- id (PRIMARY KEY)
- source_id (FOREIGN KEY → marketplace_sources.id CASCADE)
- artifact_type
- name
- path
- upstream_url
- detected_version
- detected_sha
- detected_at
- confidence_score
- raw_score
- score_breakdown (JSON)
- status
- import_date
- import_id
- metadata_json
- created_at
- updated_at

Indexes:
- idx_catalog_entries_source_id
- idx_catalog_entries_status
- idx_catalog_entries_type
- idx_catalog_entries_upstream_url
- idx_catalog_entries_source_status

Constraints:
- artifact_type IN (defined list)
- status IN ('new', 'updated', 'removed', 'imported')
- confidence_score >= 0 AND <= 100
```

---

## Directory Structure

```
skillmeat/
├── api/
│   ├── routers/
│   │   ├── marketplace_sources.py          ← Main marketplace sources API
│   │   └── marketplace.py
│   └── schemas/
│       └── marketplace.py                  ← All marketplace request/response models
├── cache/
│   ├── models.py                           ← ORM models (MarketplaceSource, entry)
│   └── repositories.py                     ← Data access layer
├── core/
│   ├── marketplace/
│   │   ├── github_scanner.py              ← Repository scanning
│   │   ├── import_coordinator.py          ← Import orchestration
│   │   ├── diff_engine.py
│   │   ├── heuristic_detector.py          ← Confidence scoring
│   │   └── observability.py
│   └── skip_preferences.py                ← Skip preferences system
└── sources/
    ├── base.py
    ├── github.py
    └── local.py
```

---

## Key Integration Points

### Confidence Threshold Logic

**Location**: `marketplace_sources.py` lines 839-854

```python
CONFIDENCE_THRESHOLD = 30  # Default hiding threshold

# Applied when filtering catalog entries
if not include_below_threshold:
    if min_confidence is None:
        min_confidence = CONFIDENCE_THRESHOLD
    else:
        # Take stricter threshold
        min_confidence = max(min_confidence, CONFIDENCE_THRESHOLD)
```

### Transaction Pattern

**Location**: `marketplace_sources.py` lines 688-716

```python
with transaction_handler.scan_update_transaction(source_id) as ctx:
    ctx.update_source_status(...)
    ctx.replace_catalog_entries(...)
```

### Skip List Integration Point

**File**: `skillmeat/core/skip_preferences.py`

**Usage Pattern**:
```python
manager = SkipPreferenceManager(project_path)
is_skipped = manager.is_skipped("skill:canvas-design")
manager.add_skip("skill:my-skill", "Already in collection")
```

---

## Testing Files

| File | Purpose |
|------|---------|
| `tests/api/test_marketplace_sources.py` | API endpoint tests |
| `tests/api/test_marketplace_router.py` | Marketplace endpoint tests |
| `tests/security/test_marketplace_security.py` | Security tests |
| `tests/performance/test_marketplace_performance.py` | Performance benchmarks |
| `tests/unit/test_github_source.py` | GitHub integration tests |
| `tests/core/test_skip_integration.py` | Skip preferences integration |

---

## Excluded/Ignored Artifact Patterns

### Current Implementation: Skip Preferences

**File**: `skillmeat/core/skip_preferences.py`

- Per-project skip list stored in `.claude/.skillmeat_skip_prefs.toml`
- Thread-safe CRUD operations
- Artifact key format: `"type:name"` (e.g., "skill:canvas-design")
- Reasons tracked for audit trail
- No existing integration with marketplace sources scanner yet

### Confidence-Based Filtering

**File**: `marketplace_sources.py`

- Default threshold: 30% confidence
- Can be overridden with `include_below_threshold=True`
- Allows user-provided `min_confidence` and `max_confidence` ranges
- Applied during catalog entry filtering, not at detection time

### Not Yet Implemented

- Excluded artifact types list (could be stored in MarketplaceSource.manual_map)
- Blocklist for specific sources (could extend trust_level system)
- Temporal exclusions (e.g., exclude until specific date)
- Pattern-based exclusions (e.g., exclude all from specific author)

