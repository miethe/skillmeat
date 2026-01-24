---
type: progress
prd: "cross-source-artifact-search-v1"
phase: 1
title: "Database + Basic Search API"
status: "pending"
started: null
completed: null

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 8
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["data-layer-expert", "python-backend-engineer"]
contributors: []

tasks:
  # Database Tasks
  - id: "DB-001"
    description: "Add title, description, search_tags, search_text columns to MarketplaceCatalogEntry"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: []
    estimated_effort: "2h"
    priority: "critical"
    file: "skillmeat/api/alembic/versions/xxx_add_catalog_search_columns.py"

  - id: "DB-002"
    description: "Create search indexes on name, (artifact_type, status), confidence_score"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["DB-001"]
    estimated_effort: "1h"
    priority: "high"
    file: "skillmeat/api/alembic/versions/xxx_add_catalog_search_columns.py"

  # Detection Tasks
  - id: "DET-001"
    description: "Modify heuristic detector to extract frontmatter during scan"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["DB-001"]
    estimated_effort: "3h"
    priority: "critical"
    file: "skillmeat/marketplace/detection/heuristic_detector.py"

  - id: "DET-002"
    description: "Check source.indexing_enabled before storing search fields"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["DET-001"]
    estimated_effort: "1h"
    priority: "high"
    file: "skillmeat/marketplace/detection/heuristic_detector.py"

  # Repository Tasks
  - id: "REPO-001"
    description: "Create repository search method with LIKE queries"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["DET-002"]
    estimated_effort: "3h"
    priority: "critical"
    file: "skillmeat/cache/repositories/marketplace_catalog_repository.py"

  - id: "REPO-002"
    description: "Add cursor pagination to search results"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["REPO-001"]
    estimated_effort: "1h"
    priority: "high"
    file: "skillmeat/cache/repositories/marketplace_catalog_repository.py"

  # API Tasks
  - id: "API-001"
    description: "Create /marketplace/catalog/search endpoint"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["REPO-002"]
    estimated_effort: "2h"
    priority: "critical"
    file: "skillmeat/api/routers/marketplace_catalog.py"

  - id: "API-002"
    description: "Create CatalogSearchRequest/Response schemas"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["API-001"]
    estimated_effort: "1h"
    priority: "high"
    file: "skillmeat/api/schemas/marketplace.py"

parallelization:
  batch_1: ["DB-001"]
  batch_2: ["DB-002", "DET-001"]
  batch_3: ["DET-002"]
  batch_4: ["REPO-001"]
  batch_5: ["REPO-002"]
  batch_6: ["API-001"]
  batch_7: ["API-002"]
  critical_path: ["DB-001", "DET-001", "DET-002", "REPO-001", "API-001"]
  estimated_total_time: "14h"

blockers: []

success_criteria:
  - id: "SC-1"
    description: "Migration runs successfully on existing database"
    status: "pending"
  - id: "SC-2"
    description: "Frontmatter extracted for indexed sources during scan"
    status: "pending"
  - id: "SC-3"
    description: "Search API returns matching entries"
    status: "pending"
  - id: "SC-4"
    description: "Response time <100ms at current scale"
    status: "pending"

files_modified:
  - "skillmeat/cache/models.py"
  - "skillmeat/api/alembic/versions/"
  - "skillmeat/marketplace/detection/heuristic_detector.py"
  - "skillmeat/cache/repositories/marketplace_catalog_repository.py"
  - "skillmeat/api/routers/marketplace_catalog.py"
  - "skillmeat/api/schemas/marketplace.py"
---

# Phase 1: Database + Basic Search API

**Objective**: Add searchable columns to MarketplaceCatalogEntry, extract frontmatter during scanning, and create basic search API endpoint with LIKE queries.

## Orchestration Quick Reference

**Batch 1** (Start):
- DB-001 → Schema migration (2h, data-layer-expert)

**Batch 2** (After DB-001):
- DB-002 → Create indexes (1h, data-layer-expert)
- DET-001 → Frontmatter extraction (3h, python-backend-engineer)

**Batch 3** (After DET-001):
- DET-002 → Conditional extraction (1h, python-backend-engineer)

**Batch 4-7** (Sequential):
- REPO-001 → Search method (3h)
- REPO-002 → Pagination (1h)
- API-001 → Endpoint (2h)
- API-002 → Schemas (1h)

**Total**: ~14 hours sequential, ~8 hours with parallelization

### Task Delegation Commands

```bash
# Batch 1 - Database migration
Task("data-layer-expert", "DB-001: Create Alembic migration adding title (String 200), description (Text), search_tags (Text), search_text (Text) columns to marketplace_catalog_entries table. All nullable. File: skillmeat/api/alembic/versions/")

# Batch 2 - Parallel after DB-001
Task("data-layer-expert", "DB-002: Add indexes to migration: idx_catalog_search_name on (name), idx_catalog_search_type_status on (artifact_type, status), idx_catalog_search_confidence on (confidence_score)")

Task("python-backend-engineer", "DET-001: Modify heuristic_detector.py to extract frontmatter from SKILL.md during artifact detection. Use parse_markdown_with_frontmatter() to extract title, description, tags. Populate entry.title, entry.description, entry.search_tags (JSON), entry.search_text (denormalized).")

# After DET-001
Task("python-backend-engineer", "DET-002: Add check for source.indexing_enabled before populating search fields. If false, leave fields as NULL.")

# Sequential chain
Task("python-backend-engineer", "REPO-001: Create search() method in MarketplaceCatalogRepository with LIKE queries on name, title, description, search_tags. Support artifact_type, min_confidence, source_ids filters.")

Task("python-backend-engineer", "REPO-002: Add cursor pagination to search() method following existing _paginate() pattern.")

Task("python-backend-engineer", "API-001: Create GET /marketplace/catalog/search endpoint with q, type, source_id, min_confidence, tags, limit, cursor params.")

Task("python-backend-engineer", "API-002: Create CatalogSearchRequest and CatalogSearchResponse Pydantic schemas with source context included.")
```

## Implementation Notes

### Schema Migration

```python
def upgrade():
    op.add_column('marketplace_catalog_entries',
        sa.Column('title', sa.String(200), nullable=True))
    op.add_column('marketplace_catalog_entries',
        sa.Column('description', sa.Text, nullable=True))
    op.add_column('marketplace_catalog_entries',
        sa.Column('search_tags', sa.Text, nullable=True))  # JSON array
    op.add_column('marketplace_catalog_entries',
        sa.Column('search_text', sa.Text, nullable=True))  # Denormalized

    op.create_index('idx_catalog_search_name',
        'marketplace_catalog_entries', ['name'])
    op.create_index('idx_catalog_search_type_status',
        'marketplace_catalog_entries', ['artifact_type', 'status'])
    op.create_index('idx_catalog_search_confidence',
        'marketplace_catalog_entries', ['confidence_score'])
```

### Frontmatter Extraction Pattern

```python
# In heuristic_detector.py
from skillmeat.utils.frontmatter import parse_markdown_with_frontmatter

if source.indexing_enabled and "SKILL.md" in file_tree:
    content = github_client.get_file_content(repo, path + "/SKILL.md")
    frontmatter = parse_markdown_with_frontmatter(content)

    entry.title = frontmatter.get("title") or frontmatter.get("name")
    entry.description = frontmatter.get("description")
    entry.search_tags = json.dumps(frontmatter.get("tags", []))
    entry.search_text = f"{name} {entry.title or ''} {entry.description or ''}"
```

### Known Gotchas

- Frontmatter parser may fail on malformed YAML - wrap in try/except
- search_tags should be JSON array string, not Python list
- search_text should include artifact name for name-based searches
- Ensure migration is reversible (downgrade)

---

## Completion Notes

(Fill in when phase is complete)
