# Marketplace Models & Search Architecture Analysis

**Date**: 2026-01-23
**Status**: Analysis Complete
**Context**: Understanding current marketplace schema and search infrastructure for cross-source artifact search implementation

---

## 1. Current MarketplaceCatalogEntry Schema

**File**: `skillmeat/cache/models.py:1516-1707`

### Core Columns

| Column | Type | Nullable | Indexed | Purpose |
|--------|------|----------|---------|---------|
| `id` | String | NO | PK | Unique catalog entry identifier (UUID) |
| `source_id` | String | NO | FK | Reference to MarketplaceSource |
| `artifact_type` | String | NO | YES | skill, command, agent, mcp_server, hook |
| `name` | String | NO | YES | Artifact name for display |
| `path` | String | NO | YES | Relative path within repository |
| `upstream_url` | String | NO | YES | Full GitHub URL (deduplication key) |
| `confidence_score` | Integer | NO | NO | 0-100 heuristic quality score |
| `status` | String | NO | YES | new, updated, removed, imported, excluded |
| `detected_at` | DateTime | NO | NO | When artifact was detected |
| `created_at` | DateTime | NO | NO | Entry creation timestamp |
| `updated_at` | DateTime | NO | NO | Last modification timestamp |

### Optional Detection Metadata

| Column | Type | Nullable | Purpose |
|--------|------|----------|---------|
| `detected_version` | String | YES | Version extracted from metadata |
| `detected_sha` | String | YES | Git commit SHA at detection |
| `raw_score` | Integer | YES | Score before normalization |
| `score_breakdown` | JSON | YES | Breakdown of scoring components |
| `metadata_json` | Text | YES | Additional detection metadata |

### Import Tracking Fields

| Column | Type | Nullable | Purpose |
|--------|------|----------|---------|
| `import_date` | DateTime | YES | When imported to local collection |
| `import_id` | String | YES | Reference to imported Artifact.id |
| `excluded_at` | DateTime | YES | When marked as "not an artifact" |
| `excluded_reason` | Text | YES | User-provided exclusion reason |

### Path-Based Tags (NEW for Frontmatter)

| Column | Type | Nullable | Purpose |
|--------|------|----------|---------|
| `path_segments` | Text | YES | JSON array of extracted path segments with approval status |

**Storage Format** (example):
```json
[
  {
    "value": "canvas",
    "normalized": "canvas",
    "status": "approved",
    "source": "path"
  },
  {
    "value": "design",
    "normalized": "design",
    "status": "pending",
    "source": "path"
  }
]
```

### Current Indexes

| Index Name | Columns | Type | Purpose |
|------------|---------|------|---------|
| `idx_catalog_entries_source_id` | source_id | Regular | Query by source |
| `idx_catalog_entries_status` | status | Regular | Filter by status |
| `idx_catalog_entries_type` | artifact_type | Regular | Filter by artifact type |
| `idx_catalog_entries_upstream_url` | upstream_url | Regular | Deduplication lookup |
| `idx_catalog_entries_source_status` | source_id, status | Composite | Filtered queries by source |

---

## 2. What's Missing for Search

### Problem: No Searchable Text Fields

Currently, **MarketplaceCatalogEntry does NOT have**:

1. **No `title` column**
   - Frontend displays `name` but title and description are extracted from frontmatter
   - Not stored in database for cross-source search

2. **No `description` column**
   - Frontmatter description is extracted on-the-fly from markdown files
   - Not persisted for querying

3. **No `search_tags` column**
   - Path-based tags exist (`path_segments`) but not unified with other tags
   - No frontmatter-extracted tags stored for search

4. **No `search_text` column**
   - Full-text search would require denormalized text field
   - Currently must fetch and parse markdown files individually

5. **No Frontmatter Metadata Storage**
   - Frontmatter is parsed from SKILL.md/README.md per-request
   - No indexing of frontmatter keywords or content

### Current Frontmatter Handling

**File**: `skillmeat/core/parsers/markdown_parser.py`

The `parse_markdown_with_frontmatter()` function:
- Parses YAML frontmatter from markdown files
- Returns `ParseResult(frontmatter: dict, content: str, raw: str)`
- Called at request-time (not cached in database)

**Frontend Usage** (CatalogEntryModal):
- Fetches primary markdown file (SKILL.md, README.md, or first .md)
- Parses frontmatter in-browser with `parseFrontmatter()`
- Displays metadata in Overview tab

**Result**: Frontmatter metadata cannot be searched across sources.

---

## 3. Related Models: MarketplaceSource

**File**: `skillmeat/cache/models.py:1182-1499`

### Key Fields for Search

| Field | Type | Purpose | NEW? |
|-------|------|---------|------|
| `enable_frontmatter_detection` | Boolean | Parse markdown frontmatter for hints | NO |
| `indexing_enabled` | Optional[Boolean] | Per-source search indexing override | YES (recent) |
| `tags` | JSON | Manual category tags | NO |
| `auto_tags` | JSON | GitHub topics extracted | NO |
| `path_tag_config` | JSON | Rules for path-based tag extraction | NO |

### Recent Changes (Commit b1d55253)

Added **indexing_enabled** tri-state column:
- `None` = Use global mode (default)
- `True` = Enable indexing regardless of mode
- `False` = Disable indexing regardless of mode

This allows **per-source search configuration** but database still lacks searchable fields.

---

## 4. Repository Patterns

**File**: `skillmeat/cache/repositories.py:1559-1800+`

### MarketplaceCatalogRepository Methods

| Method | Purpose | Search Support |
|--------|---------|-----------------|
| `get_by_id(entry_id)` | Fetch single entry | Primary key only |
| `list_by_source(source_id)` | All entries from source | Source FK only |
| `list_by_status(status)` | Filter by import status | Status field only |
| `find_by_upstream_url(url)` | Deduplication lookup | URL field only |
| `bulk_create(entries)` | Batch insert | N/A |
| `update_status(entry_id, status)` | Update import state | N/A |

**Missing**: No search/filter methods for:
- Text content (name, description, keywords)
- Artifact type + source combination
- Cross-source aggregation

---

## 5. API Layer: Current Search

**File**: `skillmeat/api/routers/marketplace_sources.py`

### GET /marketplace/sources - List with Filters

Supports filtering by:
- `search` - Repo name, description, tags (source-level only)
- `artifact_type` - skill, command, agent, etc.
- `tags` - Source tags
- `trust_level` - untrusted, basic, verified, official

**No endpoint for**: Searching within catalog entries across sources

### GET /marketplace/sources/{id}/artifacts - Catalog Listing

**File Path**: `skillmeat/api/routers/marketplace_sources.py`

Lists catalog entries from **single source** with:
- Status filtering
- Confidence threshold (CONFIDENCE_THRESHOLD = 30)
- Exclusion filtering
- **No text search**

### Typical Query Flow

```python
# Example: List high-confidence artifacts from source
def list_artifacts(
    source_id: str,
    status: Optional[str] = None,
    min_confidence: int = 30
):
    entries = repo.list_by_source(source_id)

    # Client-side filtering
    filtered = [
        e for e in entries
        if (status is None or e.status == status)
        and e.confidence_score >= min_confidence
    ]
    return filtered
```

**Issue**: All filtering happens in Python after fetching; no database-level search.

---

## 6. Frontend Search Components

**File**: `skillmeat/web/app/marketplace/sources/page.tsx` (sources listing)

Current UI supports:
- Filter by source trust level
- Filter by artifact type
- Display source-level metadata

**Missing UI**: Cross-source artifact search (to be implemented)

---

## 7. Frontmatter Indexing Feature (Recent Addition)

**Commit**: `b1d55253` - "Add configurable frontmatter indexing for cross-source search"

### What Was Added

1. **Configuration Layer** (`skillmeat/config.py`)
   - `artifact_search.indexing_mode` config key (off/on/opt_in)
   - `get_indexing_mode()` and `set_indexing_mode()` helpers

2. **Database Layer**
   - `indexing_enabled` nullable boolean on `MarketplaceSource`
   - Alembic migration with rollback support

3. **API Layer**
   - `GET /api/v1/settings/indexing-mode` endpoint
   - Effective state resolution (mode + per-source override)

4. **Frontend**
   - `useIndexingMode` hook
   - Mode-aware toggle in add/edit source modals

### What Wasn't Added

**Database schema NOT extended** with:
- ❌ `title` column
- ❌ `description` column
- ❌ `search_tags` column
- ❌ `search_text` column

**This commit only added configuration infrastructure**, not the actual searchable columns or search functionality.

---

## 8. Existing Frontmatter Parsing Infrastructure

**File**: `skillmeat/core/parsers/markdown_parser.py`

```python
def parse_markdown_with_frontmatter(content: str) -> ParseResult:
    """Extract YAML frontmatter from markdown.

    Returns:
        ParseResult(frontmatter: dict, content: str, raw: str)
    """
```

**Usage in discovery**:
- GitHub scanner reads markdown files
- Parses frontmatter for artifact type hints
- Currently used for **detection hints only**, not searchability

---

## 9. Search Utilities

**File**: `skillmeat/core/search.py`

Provides `SearchManager` class:
- `search_collection()` - Search local collection
- Content search with ripgrep acceleration
- Metadata-based filtering

**Limitation**: Does not support marketplace catalog searching.

---

## 10. Implementation Roadmap for Cross-Source Search

### Phase 1: Extend MarketplaceCatalogEntry Schema

**Migration (Alembic)**:
```python
# New columns
ADD COLUMN title VARCHAR(255) NULL
ADD COLUMN description TEXT NULL
ADD COLUMN search_tags TEXT NULL  # JSON array
ADD COLUMN search_text TEXT NULL  # Denormalized for FTS
ADD COLUMN frontmatter_json TEXT NULL  # Full parsed frontmatter

# New indexes
CREATE INDEX idx_catalog_search_text ON marketplace_catalog_entries(search_text)
CREATE INDEX idx_catalog_title ON marketplace_catalog_entries(title)
CREATE INDEX idx_catalog_tags ON marketplace_catalog_entries(search_tags)
```

### Phase 2: Extract and Index Frontmatter

**During scanning** (`core/marketplace/github_scanner.py`):
```python
# When artifact detected:
1. Read primary markdown file (SKILL.md, README.md, *.md)
2. Parse frontmatter with parse_markdown_with_frontmatter()
3. Extract:
   - title (from frontmatter.title or artifact name)
   - description (from frontmatter.description)
   - tags (merge frontmatter.tags + path_segments)
   - search_text (concatenate all searchable fields)
4. Store in MarketplaceCatalogEntry columns
```

### Phase 3: Add Search Endpoint

**New API endpoint**:
```
GET /api/v1/marketplace/artifacts/search
  ?query=<text>
  &sources=<source_id,source_id>
  &type=<skill|command|agent>
  &tags=<tag1,tag2>
  &min_confidence=30
  &limit=50
  &cursor=<pagination>
```

### Phase 4: Frontend Search UI

**New components**:
- Cross-source search bar in `/marketplace`
- Search results view with facets
- Filters by type, tags, source, confidence

---

## 11. Configuration for Indexing Control

**File**: `skillmeat/config.py`

Current configuration:
```python
# Global indexing mode
artifact_search.indexing_mode = "off" | "on" | "opt_in"

# Per-source override
MarketplaceSource.indexing_enabled = None | True | False
```

### Resolution Logic

```python
def get_effective_indexing_state(source: MarketplaceSource) -> bool:
    mode = get_indexing_mode()  # Global mode

    if source.indexing_enabled is None:
        # Use global mode
        return mode == "on"
    else:
        # Per-source override
        return source.indexing_enabled
```

---

## 12. Summary Table: Current vs. Needed

| Feature | Current Status | Needed for Search |
|---------|---|---|
| MarketplaceCatalogEntry.title | ❌ Missing | ✅ Required |
| MarketplaceCatalogEntry.description | ❌ Missing | ✅ Required |
| MarketplaceCatalogEntry.search_tags | ❌ Missing | ✅ Required |
| MarketplaceCatalogEntry.search_text | ❌ Missing | ✅ Required (FTS) |
| MarketplaceSource.indexing_enabled | ✅ Exists | ✅ Ready to use |
| Frontmatter parsing utility | ✅ Exists | ✅ Ready to use |
| Repository search methods | ❌ Missing | ✅ Required |
| API search endpoint | ❌ Missing | ✅ Required |
| Frontend search UI | ❌ Missing | ✅ Required |

---

## 13. Key Files to Modify

| File | Purpose | Changes Needed |
|------|---------|---|
| `skillmeat/cache/models.py` | Schema definition | Add 4 searchable columns |
| `skillmeat/cache/migrations/versions/*.py` | Schema migration | Alembic migration |
| `skillmeat/cache/repositories.py` | Data access | Add search_catalog_entries() method |
| `skillmeat/api/routers/marketplace_sources.py` | API endpoints | Add search endpoint |
| `skillmeat/api/schemas/marketplace.py` | API schemas | Add search request/response models |
| `skillmeat/core/marketplace/github_scanner.py` | Scanning logic | Extract and store frontmatter |
| `skillmeat/web/app/marketplace/search` | Frontend | New search page/components |

---

## 14. Integration Points

### With Existing Systems

1. **Frontmatter Parser** (`parse_markdown_with_frontmatter()`)
   - Already available, use during scanning

2. **GitHub Scanner** (`GitHubScanner`)
   - Modify to extract and store frontmatter metadata

3. **Configuration** (`get_indexing_mode()`)
   - Already available, use to decide whether to index

4. **API Layer**
   - Extend with new search endpoint following established patterns

---

## 15. Performance Considerations

### Database Efficiency

- Add indexes on `search_text`, `title`, `search_tags`
- Use `LIKE` queries or SQLite FTS if full-text search needed
- Pagination critical (cursor-based preferred)

### Storage

- `search_text`: Denormalized but needed for search performance
- `frontmatter_json`: Optional, store full frontmatter for reference

### Caching

- Search results can be cached per query parameters
- Invalidate cache on rescan/import

---

## Conclusion

**Current State**: MarketplaceCatalogEntry has metadata structure and indexing configuration, but **NO searchable text fields or search methods**.

**Path Forward**:
1. Extend schema with 4 new columns (title, description, search_tags, search_text)
2. Create Alembic migration
3. Update GitHub scanner to extract and store frontmatter
4. Add repository search methods
5. Add API search endpoint
6. Build frontend search UI

**Existing Infrastructure Ready**:
- Frontmatter parser ✅
- Indexing configuration ✅
- Repository patterns ✅
- API architecture ✅
