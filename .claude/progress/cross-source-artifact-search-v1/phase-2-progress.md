---
type: progress
prd: cross-source-artifact-search-v1
phase: 2
title: FTS5 Enhancement
status: completed
started: null
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- data-layer-expert
- python-backend-engineer
contributors: []
tasks:
- id: FTS-001
  description: Create FTS5 virtual table with sync triggers via Alembic migration
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies: []
  estimated_effort: 2h
  priority: critical
  file: skillmeat/api/alembic/versions/xxx_add_fts5_catalog_search.py
- id: FTS-002
  description: Implement FTS5 feature detection at app startup
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - FTS-001
  estimated_effort: 1h
  priority: high
  file: skillmeat/api/utils/fts5.py
- id: FTS-003
  description: Add FTS5 MATCH query path to repository search method
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - FTS-002
  estimated_effort: 2h
  priority: critical
  file: skillmeat/cache/repositories/marketplace_catalog_repository.py
- id: FTS-004
  description: Add snippet generation for result highlighting
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - FTS-003
  estimated_effort: 1h
  priority: medium
  file: skillmeat/cache/repositories/marketplace_catalog_repository.py
parallelization:
  batch_1:
  - FTS-001
  batch_2:
  - FTS-002
  batch_3:
  - FTS-003
  batch_4:
  - FTS-004
  critical_path:
  - FTS-001
  - FTS-002
  - FTS-003
  estimated_total_time: 6h
blockers: []
success_criteria:
- id: SC-1
  description: FTS5 virtual table created with sync triggers
  status: completed
- id: SC-2
  description: Feature detection correctly identifies FTS5 availability
  status: completed
- id: SC-3
  description: FTS5 queries return <10ms at 50K scale
  status: completed
- id: SC-4
  description: Snippet highlights match terms correctly
  status: completed
- id: SC-5
  description: Fallback to LIKE works when FTS5 unavailable
  status: completed
files_modified:
- skillmeat/api/alembic/versions/
- skillmeat/api/utils/fts5.py
- skillmeat/cache/repositories/marketplace_catalog_repository.py
- skillmeat/api/routers/marketplace_catalog.py
progress: 100
updated: '2026-01-24'
---

# Phase 2: FTS5 Enhancement

**Objective**: Add SQLite FTS5 full-text search capabilities with relevance ranking, snippet generation, and automatic fallback to LIKE queries when FTS5 is unavailable.

## Orchestration Quick Reference

**Batch 1** (Start):
- FTS-001 → FTS5 migration (2h, data-layer-expert)

**Batch 2** (After FTS-001):
- FTS-002 → Feature detection (1h, python-backend-engineer)

**Batch 3** (After FTS-002):
- FTS-003 → FTS5 search path (2h, python-backend-engineer)

**Batch 4** (After FTS-003):
- FTS-004 → Snippet generation (1h, python-backend-engineer)

**Total**: ~6 hours sequential

### Task Delegation Commands

```bash
# FTS5 virtual table migration
Task("data-layer-expert", "FTS-001: Create Alembic migration for FTS5 virtual table catalog_fts with columns (name UNINDEXED, artifact_type UNINDEXED, title, description, search_text, tags). Use content='marketplace_catalog_entries', content_rowid='rowid', tokenize='porter unicode61 remove_diacritics 2'. Add INSERT/UPDATE/DELETE triggers for sync.")

# Feature detection
Task("python-backend-engineer", "FTS-002: Create skillmeat/api/utils/fts5.py with is_fts5_available() function that attempts to create test FTS5 table. Cache result in module-level variable. Call at app startup.")

# FTS5 search path
Task("python-backend-engineer", "FTS-003: Add search_fts() method to MarketplaceCatalogRepository. Use FTS5 MATCH syntax with BM25 ranking. Include JOIN to get source context. Fallback to LIKE-based search() if FTS5 unavailable.")

# Snippet generation
Task("python-backend-engineer", "FTS-004: Add snippet() function call to FTS5 query: snippet(catalog_fts, 2, '<mark>', '</mark>', '...', 32). Include in search response schema.")
```

## Implementation Notes

### FTS5 Virtual Table SQL

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS catalog_fts USING fts5(
    name UNINDEXED,
    artifact_type UNINDEXED,
    title,
    description,
    search_text,
    tags,
    content='marketplace_catalog_entries',
    content_rowid='rowid',
    tokenize='porter unicode61 remove_diacritics 2'
);

-- Sync triggers
CREATE TRIGGER catalog_fts_insert AFTER INSERT ON marketplace_catalog_entries BEGIN
    INSERT INTO catalog_fts(rowid, name, artifact_type, title, description, search_text, tags)
    VALUES (new.rowid, new.name, new.artifact_type, new.title, new.description, new.search_text, new.search_tags);
END;

CREATE TRIGGER catalog_fts_delete AFTER DELETE ON marketplace_catalog_entries BEGIN
    INSERT INTO catalog_fts(catalog_fts, rowid, name, artifact_type, title, description, search_text, tags)
    VALUES ('delete', old.rowid, old.name, old.artifact_type, old.title, old.description, old.search_text, old.search_tags);
END;

CREATE TRIGGER catalog_fts_update AFTER UPDATE ON marketplace_catalog_entries BEGIN
    INSERT INTO catalog_fts(catalog_fts, rowid, name, artifact_type, title, description, search_text, tags)
    VALUES ('delete', old.rowid, old.name, old.artifact_type, old.title, old.description, old.search_text, old.search_tags);
    INSERT INTO catalog_fts(rowid, name, artifact_type, title, description, search_text, tags)
    VALUES (new.rowid, new.name, new.artifact_type, new.title, new.description, new.search_text, new.search_tags);
END;
```

### Feature Detection Pattern

```python
# skillmeat/api/utils/fts5.py
_fts5_available: bool | None = None

def is_fts5_available(engine) -> bool:
    """Check if SQLite FTS5 extension is available."""
    global _fts5_available
    if _fts5_available is not None:
        return _fts5_available

    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE VIRTUAL TABLE _fts5_test USING fts5(x)"))
            conn.execute(text("DROP TABLE _fts5_test"))
            _fts5_available = True
    except Exception:
        _fts5_available = False

    return _fts5_available
```

### FTS5 Search Query

```python
def search_fts(
    self,
    query: str,
    artifact_type: Optional[str] = None,
    limit: int = 50,
) -> List[Dict]:
    """FTS5 full-text search with relevance ranking."""
    sql = text("""
        SELECT
            ce.*,
            ms.owner,
            ms.repo_name,
            ms.id as source_id,
            fts.rank AS relevance,
            snippet(catalog_fts, 2, '<mark>', '</mark>', '...', 32) AS snippet
        FROM marketplace_catalog_entries ce
        JOIN marketplace_sources ms ON ce.source_id = ms.id
        JOIN catalog_fts fts ON ce.rowid = fts.rowid
        WHERE fts MATCH :query
        AND ce.status NOT IN ('excluded', 'removed')
        ORDER BY fts.rank
        LIMIT :limit
    """)
    return self.session.execute(sql, {"query": query, "limit": limit}).fetchall()
```

### Known Gotchas

- FTS5 MATCH syntax differs from LIKE - use double quotes for phrases
- Populate FTS5 table after initial migration using INSERT INTO catalog_fts(catalog_fts) VALUES('rebuild')
- FTS5 rank is negative (more negative = better match)
- Handle SQLite compile-time FTS5 availability gracefully
- Ensure triggers don't fire during initial backfill

---

## Completion Notes

**Completed**: 2026-01-24

### Deliverables

1. **FTS5 Migration** (`skillmeat/cache/migrations/versions/20260124_1200_add_fts5_catalog_search.py`)
   - FTS5 virtual table with porter stemming and unicode support
   - INSERT/UPDATE/DELETE sync triggers
   - Initial data population from existing entries
   - Graceful handling when FTS5 not compiled into SQLite

2. **Feature Detection** (`skillmeat/api/utils/fts5.py`)
   - `check_fts5_available()` - cached detection at startup
   - `is_fts5_available()` - fast lookup for repository
   - `reset_fts5_check()` - testing utility

3. **FTS5 Search Path** (`skillmeat/cache/repositories.py`)
   - `_search_fts5()` - full-text MATCH queries with BM25 ranking
   - `_build_fts5_query()` - query escaping and prefix matching
   - Automatic fallback to `_search_like()` when FTS5 unavailable

4. **Snippet Generation**
   - Title snippets (32 tokens) and description snippets (64 tokens)
   - `<mark>` highlight tags around matched terms
   - Schema fields: `title_snippet`, `description_snippet`

### Test Coverage

- 58 tests pass (repository + FTS5 detection)
- Query builder tests for special character escaping
- Integration tests for FTS5 search with all filters
- Fallback tests when FTS5 unavailable

### Commits

1. `b3ba01d4` - feat(db): Add FTS5 catalog search migration
2. `0c27f555` - feat(api): Add FTS5 feature detection utility
3. `461719f6` - feat(marketplace): Add FTS5 search path to catalog repository
4. `cc426325` - feat(marketplace): Add snippet generation for search highlighting
