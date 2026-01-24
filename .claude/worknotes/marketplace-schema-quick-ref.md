# Marketplace Schema & Search Quick Reference

**For**: Cross-Source Artifact Search Implementation

---

## MarketplaceCatalogEntry Column Status

### ✅ READY (Existing)
```python
id                  # UUID primary key
source_id          # FK to MarketplaceSource
artifact_type      # skill, command, agent, mcp_server, hook
name               # Artifact name (indexed)
path               # Path in repo (indexed)
upstream_url       # GitHub URL (indexed, unique)
confidence_score   # 0-100 quality metric
status             # new, updated, removed, imported, excluded
detected_version   # Version from metadata
detected_sha       # Git SHA at detection
detected_at        # Detection timestamp
path_segments      # JSON array with path-based tags
metadata_json      # Additional metadata JSON
```

### ❌ MISSING (Needed for Search)
```python
title              # Add: Extracted from frontmatter or artifact name
description        # Add: From frontmatter.description
search_tags        # Add: JSON array of all tags (path + frontmatter)
search_text        # Add: Denormalized text for full-text search
frontmatter_json   # Optional: Full parsed frontmatter for reference
```

---

## Key Index Gaps

**Existing**:
- idx_catalog_entries_source_id (source FK)
- idx_catalog_entries_status (status)
- idx_catalog_entries_type (artifact_type)
- idx_catalog_entries_upstream_url (deduplication)

**Needed**:
- idx_catalog_search_text (full-text search)
- idx_catalog_title (title filtering)
- idx_catalog_tags (tag filtering)
- Composite: (source_id, search_tags) for source + tag queries

---

## MarketplaceSource Search Config

✅ **Already Available**:
```python
indexing_enabled   # None | True | False (new in commit b1d55253)
enable_frontmatter_detection  # Boolean flag
tags               # Manual category tags (JSON)
auto_tags          # GitHub topics (JSON)
path_tag_config    # Path extraction rules (JSON)
```

**Global Config**:
- `artifact_search.indexing_mode` = "off" | "on" | "opt_in"
- Use `get_indexing_mode()` to check
- Combine with per-source `indexing_enabled` for final state

---

## Repository Methods Needed

**Add to MarketplaceCatalogRepository**:

```python
def search(
    query: str,
    source_id: Optional[str] = None,
    artifact_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
    min_confidence: int = 30,
    limit: int = 50,
    offset: int = 0
) -> List[MarketplaceCatalogEntry]

def count_search_results(
    query: str,
    source_id: Optional[str] = None,
    artifact_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
    min_confidence: int = 30
) -> int
```

---

## Frontmatter Parser Ready

**File**: `skillmeat/core/parsers/markdown_parser.py`

✅ **Already available**:
```python
from skillmeat.core.parsers import parse_markdown_with_frontmatter, ParseResult

result = parse_markdown_with_frontmatter(content: str) -> ParseResult
# result.frontmatter  # dict or None
# result.content      # body text
# result.raw          # original content
```

**Usage during scanning**:
```python
# In GitHubScanner, after reading markdown file:
parse_result = parse_markdown_with_frontmatter(file_content)
if parse_result.frontmatter:
    title = parse_result.frontmatter.get('title', artifact_name)
    description = parse_result.frontmatter.get('description', '')
    tags = parse_result.frontmatter.get('tags', [])
    # Store in MarketplaceCatalogEntry
```

---

## API Endpoint Pattern

**New Endpoint** (following existing marketplace patterns):

```
GET /api/v1/marketplace/artifacts/search
  ?query=<text>                   # Required: search term
  &sources=<id1,id2>             # Optional: source IDs (comma-separated)
  &type=skill,command            # Optional: artifact types
  &tags=python,testing           # Optional: tags (comma-separated)
  &min_confidence=30             # Optional: confidence threshold
  &limit=50                       # Optional: page size (max 100)
  &cursor=<pagination_token>     # Optional: cursor for pagination
```

**Response**:
```python
{
  "items": [
    {
      "id": "entry-123",
      "name": "My Skill",
      "title": "Better skill title",
      "description": "Skill description",
      "type": "skill",
      "source": {
        "id": "source-456",
        "name": "User/Repo",
        "trust_level": "basic"
      },
      "tags": ["python", "testing"],
      "confidence_score": 95,
      "status": "new",
      "upstream_url": "https://github.com/...",
      "detected_at": "2026-01-23T..."
    }
  ],
  "total_count": 123,
  "has_more": true,
  "next_cursor": "next_page_token"
}
```

---

## Alembic Migration Template

**File Location**: `skillmeat/cache/migrations/versions/20260123_****_add_searchable_fields_to_catalog.py`

```python
"""Add searchable fields to marketplace_catalog_entries for cross-source search."""

from alembic import op
import sqlalchemy as sa

revision = "20260123_****"
down_revision = "previous_migration_hash"

def upgrade():
    op.add_column(
        "marketplace_catalog_entries",
        sa.Column("title", sa.String(255), nullable=True)
    )
    op.add_column(
        "marketplace_catalog_entries",
        sa.Column("description", sa.Text, nullable=True)
    )
    op.add_column(
        "marketplace_catalog_entries",
        sa.Column("search_tags", sa.Text, nullable=True)  # JSON array
    )
    op.add_column(
        "marketplace_catalog_entries",
        sa.Column("search_text", sa.Text, nullable=True)  # Denormalized FTS
    )

    op.create_index(
        "idx_catalog_search_text",
        "marketplace_catalog_entries",
        ["search_text"]
    )
    op.create_index(
        "idx_catalog_title",
        "marketplace_catalog_entries",
        ["title"]
    )
    op.create_index(
        "idx_catalog_search_tags",
        "marketplace_catalog_entries",
        ["search_tags"]
    )

def downgrade():
    op.drop_index("idx_catalog_search_tags")
    op.drop_index("idx_catalog_title")
    op.drop_index("idx_catalog_search_text")
    op.drop_column("marketplace_catalog_entries", "search_text")
    op.drop_column("marketplace_catalog_entries", "search_tags")
    op.drop_column("marketplace_catalog_entries", "description")
    op.drop_column("marketplace_catalog_entries", "title")
```

---

## Integration Checklist

### 1. Database Layer
- [ ] Extend MarketplaceCatalogEntry model with 4 columns
- [ ] Create Alembic migration
- [ ] Add indexes
- [ ] Add search methods to MarketplaceCatalogRepository

### 2. Scanner Layer
- [ ] Modify GitHub scanner to extract frontmatter
- [ ] Store title, description, search_tags, search_text
- [ ] Check indexing_enabled before indexing

### 3. API Layer
- [ ] Add search endpoint to marketplace_sources.py router
- [ ] Create search schemas (request/response)
- [ ] Add query builders for filtering
- [ ] Handle pagination

### 4. Frontend Layer
- [ ] Create search component
- [ ] Add to /marketplace page
- [ ] Show search results with filtering
- [ ] Link to CatalogEntryModal

### 5. Testing
- [ ] Unit tests for search methods
- [ ] API integration tests
- [ ] E2E tests for search flow

---

## Files to Check First

1. **Schema**: `skillmeat/cache/models.py:1516-1707`
2. **Repository**: `skillmeat/cache/repositories.py:1559-1800`
3. **API Router**: `skillmeat/api/routers/marketplace_sources.py:1-200`
4. **Scanner**: `skillmeat/core/marketplace/github_scanner.py`
5. **Frontmatter Parser**: `skillmeat/core/parsers/markdown_parser.py:41-105`
6. **Config**: `skillmeat/config.py` (for indexing_mode)

---

## Query Examples

### Simple Search (Across All Indexed Sources)
```sql
SELECT * FROM marketplace_catalog_entries
WHERE search_text LIKE '%python%'
  AND confidence_score >= 30
  AND status != 'excluded'
ORDER BY confidence_score DESC
LIMIT 50;
```

### With Source Filter
```sql
SELECT * FROM marketplace_catalog_entries
WHERE search_text LIKE '%python%'
  AND source_id IN ('source-1', 'source-2')
  AND artifact_type = 'skill'
  AND confidence_score >= 30
ORDER BY confidence_score DESC;
```

### With Tag Filter (JSON array contains)
```sql
SELECT * FROM marketplace_catalog_entries
WHERE search_text LIKE '%python%'
  AND search_tags LIKE '%"python"%'  -- SQLite LIKE for JSON
  AND confidence_score >= 30;
```

---

## Performance Notes

- **FTS Optimization**: For large datasets, consider moving to FTS5 virtual table
- **Denormalization**: search_text includes name + title + description + tags for fast queries
- **Pagination**: Use cursor-based, not offset-based, for consistency
- **Caching**: Cache popular searches with 5-minute TTL
- **Indexing Control**: Respect `get_effective_indexing_state(source)` when importing

---

## Status Indicators

### What's Ready ✅
- Frontmatter parser working
- Configuration infrastructure (indexing_enabled, indexing_mode)
- Path-based tags system
- Repository patterns established
- API patterns established

### What Needs Building ⚠️
- Searchable columns in schema
- Alembic migration
- Search methods in repository
- Search endpoint in API
- Frontend search UI
- Integration test suite
