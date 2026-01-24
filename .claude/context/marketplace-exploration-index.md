# Marketplace Models Exploration - Document Index

**Date**: 2026-01-23
**Status**: ✅ Exploration Complete

---

## Generated Context Documents

### 1. **EXPLORATION_SUMMARY.md** 
   - **Purpose**: Executive overview and quick insights
   - **Audience**: Decision makers, project leads
   - **Contents**:
     - Current state analysis (what exists vs. what's missing)
     - Column recommendations with SQL
     - Three-layer implementation path
     - Risk assessment and mitigation

### 2. **marketplace-models-analysis.md** (Full Reference)
   - **Purpose**: Detailed technical analysis
   - **Audience**: Developers implementing search
   - **Contents**:
     - Complete MarketplaceCatalogEntry schema breakdown
     - What's missing for search (detailed explanation)
     - Related models (MarketplaceSource)
     - Repository patterns and current search
     - Frontmatter handling (parsing + storage)
     - Indexing feature (commit b1d55253)
     - Implementation roadmap with phases

### 3. **marketplace-schema-quick-ref.md** (Developer Cheat Sheet)
   - **Purpose**: Quick lookup during implementation
   - **Audience**: Active developers
   - **Contents**:
     - Column status checklist (Ready vs. Missing)
     - Key index gaps
     - Configuration reference
     - Repository methods template
     - Frontmatter parser usage example
     - API endpoint pattern template
     - Alembic migration template
     - Integration checklist
     - Performance notes

---

## Key Findings

### 🔴 Critical Gaps (Blocking Search)

1. **No Searchable Columns**
   - ❌ `title` - Cannot display proper titles
   - ❌ `description` - Cannot show descriptions
   - ❌ `search_tags` - Cannot filter by tags
   - ❌ `search_text` - Cannot search efficiently

2. **No Search Methods**
   - MarketplaceCatalogRepository lacks `search()` method
   - No filtering across sources

3. **No API Endpoint**
   - No `GET /api/v1/marketplace/artifacts/search` endpoint
   - No way to expose search to frontend

### 🟢 Infrastructure Ready

1. **Frontmatter Parser**
   - `parse_markdown_with_frontmatter()` exists and works
   - Returns structured metadata dict

2. **Configuration System**
   - `indexing_enabled` (tri-state) on MarketplaceSource
   - Global `indexing_mode` in config
   - `get_indexing_mode()` and helpers ready

3. **Repository Patterns**
   - BaseRepository class established
   - CRUD methods available
   - Add search methods following existing patterns

4. **API Patterns**
   - Cursor-based pagination established
   - Query filtering patterns
   - Error handling with HTTPException

---

## Implementation Path (3 Layers)

```
DATABASE LAYER
├── Add 4 columns to MarketplaceCatalogEntry
│   ├── title (VARCHAR 255)
│   ├── description (TEXT)
│   ├── search_tags (TEXT - JSON array)
│   └── search_text (TEXT - denormalized FTS)
├── Create Alembic migration
├── Add 3 new indexes
└── Backfill existing data

    ↓

SCANNING LAYER
├── Extract frontmatter during GitHub scan
├── Parse with parse_markdown_with_frontmatter()
├── Store title, description, tags, search_text
├── Check get_effective_indexing_state(source)
└── Respect indexing_enabled configuration

    ↓

QUERY LAYER
├── Add search methods to MarketplaceCatalogRepository
├── Create API endpoint: GET /marketplace/artifacts/search
├── Support filters: query, sources, type, tags, confidence, cursor
└── Implement cursor-based pagination
```

---

## Files to Modify

| File | Change | Complexity |
|------|--------|-----------|
| `skillmeat/cache/models.py` | Add 4 columns | 🟢 Low |
| `skillmeat/cache/migrations/versions/*.py` | Create migration | 🟡 Medium |
| `skillmeat/cache/repositories.py` | Add search methods | 🟢 Low |
| `skillmeat/api/routers/marketplace_sources.py` | Add endpoint | 🟡 Medium |
| `skillmeat/api/schemas/marketplace.py` | Add schemas | 🟢 Low |
| `skillmeat/core/marketplace/github_scanner.py` | Extract frontmatter | 🟡 Medium |
| `skillmeat/web/app/marketplace/search` | New search page | 🟡 Medium |

---

## Quick Column Reference

```python
# EXISTING (Don't Add)
id                  # UUID - primary key
source_id          # FK to MarketplaceSource
artifact_type      # skill, command, agent, etc.
name               # Artifact name (currently indexed)
path               # Path in repository
upstream_url       # GitHub URL
confidence_score   # Quality metric 0-100
status             # new, updated, removed, imported, excluded
path_segments      # JSON array - path-based tags
metadata_json      # Additional metadata

# MISSING (NEED TO ADD)
title              # 🆕 Artifact display title
description        # 🆕 Short description for UI/search
search_tags        # 🆕 JSON array of all tags
search_text        # 🆕 Denormalized for full-text search
```

---

## Recent Related Work

### Commit b1d55253 (2 days ago)
**"Add configurable frontmatter indexing for cross-source search"**

What was added:
- ✅ `indexing_enabled` column (nullable boolean)
- ✅ Configuration: `artifact_search.indexing_mode`
- ✅ API: `GET /api/v1/settings/indexing-mode`
- ✅ Frontend: `useIndexingMode` hook
- ✅ Modals updated with indexing toggle

What was NOT added:
- ❌ Searchable columns (title, description, search_tags, search_text)
- ❌ Search methods
- ❌ Search endpoint
- ❌ Search UI

**Conclusion**: Configuration infrastructure is ready; now need database + search implementation.

---

## Performance Considerations

| Aspect | Consideration |
|--------|---|
| **Denormalization** | `search_text` is redundant but needed for fast queries |
| **Backfill** | Can be lazy/async - extract on-demand if preferred |
| **Indexes** | New indexes on search_text, title, search_tags |
| **Pagination** | Use cursor-based (established pattern) |
| **Caching** | Cache search results with 5-minute TTL |
| **Indexing Control** | Respect global mode + per-source override |

---

## Testing Strategy

- **Unit Tests**: Repository search methods
- **Integration Tests**: API endpoint with various filters
- **E2E Tests**: Search flow from UI to results
- **Performance Tests**: Query times with large datasets

---

## Documents Navigation

```
This Index (marketplace-exploration-index.md)
├── EXPLORATION_SUMMARY.md ..................... Start here for overview
│   ├── Executive Summary
│   ├── Current State Analysis
│   ├── Column Recommendations
│   └── Implementation Path
│
├── marketplace-models-analysis.md ............ Read for detailed analysis
│   ├── Current Schema Breakdown
│   ├── Missing for Search
│   ├── Repository Patterns
│   ├── Frontmatter Handling
│   ├── Configuration System
│   ├── Implementation Roadmap
│   └── Integration Points
│
└── marketplace-schema-quick-ref.md .......... Reference during implementation
    ├── Column Status Checklist
    ├── Index Gaps
    ├── Repository Methods Template
    ├── API Endpoint Pattern
    ├── Alembic Migration Template
    ├── Integration Checklist
    └── Performance Notes
```

---

## Key Takeaways

1. **Schema Gap is Clear**: 4 columns needed (title, description, search_tags, search_text)

2. **Infrastructure Ready**: Parser, configuration, repository patterns, API patterns all in place

3. **Low Risk Migration**: Nullable columns + new indexes + rollback support

4. **High Impact**: Enables cross-source search which was whole point of indexing config

5. **Ready to Build**: All dependencies resolved, path forward clear

---

## Next Steps for Implementation

### Phase 0: Design Review
- [ ] Approve column additions
- [ ] Confirm backfill strategy
- [ ] Review API endpoint design

### Phase 1: Database
- [ ] Create Alembic migration
- [ ] Test rollback
- [ ] Plan backfill approach

### Phase 2: Scanning
- [ ] Modify GitHub scanner
- [ ] Extract frontmatter during scan
- [ ] Add indexing_enabled checks

### Phase 3: Query Layer
- [ ] Add search methods to repository
- [ ] Implement search logic
- [ ] Add API endpoint

### Phase 4: Frontend
- [ ] Create search page
- [ ] Add search component
- [ ] Integrate with existing UI

### Phase 5: Testing
- [ ] Unit tests
- [ ] Integration tests
- [ ] E2E tests
- [ ] Performance validation

---

**Status**: 🟢 Ready for Implementation
**Confidence**: 🟢 High (all patterns confirmed)
**Risk**: 🟢 Low (backward compatible)

