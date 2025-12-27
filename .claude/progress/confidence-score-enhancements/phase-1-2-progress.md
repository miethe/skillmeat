---
type: progress
prd: "confidence-score-enhancements"
phase: "1-2"
status: pending
progress: 0
total_tasks: 15
completed_tasks: 0

tasks:
  - id: "TASK-1.1"
    name: "Define normalization constant"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimate: "0.5h"

  - id: "TASK-1.2"
    name: "Refactor _score_directory() return value"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.1"]
    estimate: "1h"

  - id: "TASK-1.3"
    name: "Implement breakdown construction"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.2"]
    estimate: "1h"

  - id: "TASK-1.4"
    name: "Integrate normalization into detector"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.1", "TASK-1.3"]
    estimate: "1h"

  - id: "TASK-1.5"
    name: "Add comprehensive unit tests"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.4"]
    estimate: "1.5h"

  - id: "TASK-1.6"
    name: "Update HeuristicMatch TypedDict"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.3"]
    estimate: "0.5h"

  - id: "TASK-2.1"
    name: "Create Alembic migration"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimate: "1h"

  - id: "TASK-2.2"
    name: "Update MarketplaceCatalogEntry model"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-2.1"]
    estimate: "0.5h"

  - id: "TASK-2.3"
    name: "Update CatalogEntryResponse schema"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.6"]
    estimate: "0.5h"

  - id: "TASK-2.4"
    name: "Modify catalog query to hydrate breakdown"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-2.2"]
    estimate: "0.5h"

  - id: "TASK-2.5"
    name: "Add filter query parameters"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimate: "1h"

  - id: "TASK-2.6"
    name: "Implement confidence range filter logic"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-2.5"]
    estimate: "1h"

  - id: "TASK-2.7"
    name: "Implement low-confidence toggle"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-2.5"]
    estimate: "1h"

  - id: "TASK-2.8"
    name: "Write integration tests"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-2.4", "TASK-2.6", "TASK-2.7"]
    estimate: "2h"

  - id: "TASK-2.9"
    name: "Create data migration"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-2.1"]
    estimate: "1h"

parallelization:
  batch_1: ["TASK-1.1", "TASK-2.1", "TASK-2.5"]
  batch_2: ["TASK-1.2", "TASK-2.2", "TASK-2.9", "TASK-2.6", "TASK-2.7"]
  batch_3: ["TASK-1.3", "TASK-1.6"]
  batch_4: ["TASK-1.4", "TASK-2.3", "TASK-2.4"]
  batch_5: ["TASK-1.5", "TASK-2.8"]
---

# Phase 1-2: Score Normalization & Database Backend

## Overview

Fix the broken confidence score normalization (max 65 on 0-100 scale) and add database support for raw scores and breakdown data. This phase establishes the foundation for frontend transparency features.

**Duration**: 14-18 hours | **Story Points**: 11

## Orchestration Quick Reference

**Batch 1** (Parallel - 2.5h):
- TASK-1.1 → `python-backend-engineer` (0.5h) - Define MAX_RAW_SCORE = 65 and normalize_score()
- TASK-2.1 → `python-backend-engineer` (1h) - Create Alembic migration for raw_score and score_breakdown columns
- TASK-2.5 → `python-backend-engineer` (1h) - Add filter query parameters to API

**Batch 2** (Parallel - 3.5h, requires Batch 1):
- TASK-1.2 → `python-backend-engineer` (1h) - Refactor _score_directory() to return breakdown dict
- TASK-2.2 → `python-backend-engineer` (0.5h) - Update MarketplaceCatalogEntry ORM model
- TASK-2.9 → `python-backend-engineer` (1h) - Create data migration to populate raw_score
- TASK-2.6 → `python-backend-engineer` (1h) - Implement confidence range filter logic
- TASK-2.7 → `python-backend-engineer` (1h) - Implement low-confidence toggle

**Batch 3** (Parallel - 1.5h, requires Batch 2):
- TASK-1.3 → `python-backend-engineer` (1h) - Implement breakdown construction
- TASK-1.6 → `python-backend-engineer` (0.5h) - Update HeuristicMatch TypedDict

**Batch 4** (Parallel - 2h, requires Batch 3):
- TASK-1.4 → `python-backend-engineer` (1h) - Integrate normalization into detector
- TASK-2.3 → `python-backend-engineer` (0.5h) - Update CatalogEntryResponse schema
- TASK-2.4 → `python-backend-engineer` (0.5h) - Modify catalog query to hydrate breakdown

**Batch 5** (Parallel - 3.5h, requires Batch 4):
- TASK-1.5 → `python-backend-engineer` (1.5h) - Add comprehensive unit tests
- TASK-2.8 → `python-backend-engineer` (2h) - Write integration tests

### Task Delegation Commands

```
# Batch 1
Task("python-backend-engineer", "TASK-1.1: Define normalization constant in heuristic_detector.py. Add MAX_RAW_SCORE = 65 constant and normalize_score() function that converts raw score to 0-100 scale. Function should return 100 for input 65, ~46 for input 30. File: skillmeat/core/marketplace/heuristic_detector.py")

Task("python-backend-engineer", "TASK-2.1: Create Alembic migration for new catalog columns. Add raw_score (Integer, nullable=True) and score_breakdown (JSON, nullable=True) columns to marketplace_catalog_entries table. File: skillmeat/alembic/versions/")

Task("python-backend-engineer", "TASK-2.5: Add filter query parameters to marketplace catalog API. Add min_confidence, max_confidence, include_below_threshold params to list_catalog_entries() endpoint. Document in docstring. File: skillmeat/api/routers/marketplace_sources.py")

# Batch 2 (after Batch 1)
Task("python-backend-engineer", "TASK-1.2: Refactor _score_directory() return value. Modify to return dict with all signal scores instead of just total: {dir_name: 10, manifest: 20, extensions: 5, parent_hint: 15, frontmatter: 15, depth_penalty: -X}. File: skillmeat/core/marketplace/heuristic_detector.py")

Task("python-backend-engineer", "TASK-2.2: Update MarketplaceCatalogEntry ORM model. Add raw_score and score_breakdown SQLAlchemy columns (Integer and JSON types). Ensure backward compatible. File: skillmeat/cache/models.py")

Task("python-backend-engineer", "TASK-2.9: Create data migration to populate raw_score. Migration script sets raw_score = LEAST(65, confidence_score) for all existing entries. File: skillmeat/alembic/versions/")

Task("python-backend-engineer", "TASK-2.6: Implement confidence range filter logic. Add WHERE clause to filter by confidence_score between min_confidence and max_confidence. File: skillmeat/api/routers/marketplace_sources.py")

Task("python-backend-engineer", "TASK-2.7: Implement low-confidence toggle. Add logic to show/hide entries <30 based on include_below_threshold parameter. Default false (filters out <30), true includes all. File: skillmeat/api/routers/marketplace_sources.py")

# Batch 3 (after Batch 2)
Task("python-backend-engineer", "TASK-1.3: Implement breakdown construction. Build breakdown dict with signal names and normalized calculation matching JSON structure: {dir_name_score, manifest_score, extensions_score, parent_hint_score, frontmatter_score, depth_penalty, raw_total, normalized_score}. File: skillmeat/core/marketplace/heuristic_detector.py")

Task("python-backend-engineer", "TASK-1.6: Update HeuristicMatch TypedDict. Add raw_score and breakdown fields to model with proper type hints reflecting breakdown dict structure. File: skillmeat/core/marketplace/heuristic_detector.py")

# Batch 4 (after Batch 3)
Task("python-backend-engineer", "TASK-1.4: Integrate normalization into detector. Update detect_artifacts() to normalize before returning HeuristicMatch. All returned matches should have normalized_score = round((raw_score / 65) * 100). File: skillmeat/core/marketplace/heuristic_detector.py")

Task("python-backend-engineer", "TASK-2.3: Update CatalogEntryResponse schema. Add optional raw_score (int) and score_breakdown (dict) fields. Schema validates JSON breakdown structure. File: skillmeat/api/schemas/marketplace.py")

Task("python-backend-engineer", "TASK-2.4: Modify catalog query to hydrate breakdown. Update list_catalog_entries() to include raw_score and score_breakdown columns in SELECT statement. File: skillmeat/api/routers/marketplace_sources.py")

# Batch 5 (after Batch 4)
Task("python-backend-engineer", "TASK-1.5: Add comprehensive unit tests for normalization. Test cases: raw=65→100, raw=30→46, raw=0→0, penalties applied correctly. File: tests/test_marketplace_*.py")

Task("python-backend-engineer", "TASK-2.8: Write integration tests for filter endpoints. Test: filters work correctly, responses include raw_score and breakdown, threshold logic works, min/max range filtering. File: tests/test_marketplace_*.py")
```

## Quality Gates

**Phase 1 (Normalization)**:
- [ ] Normalization formula verified mathematically (65→100%, 30→46%)
- [ ] Unit tests pass for all signal combinations
- [ ] Breakdown dict is JSON-serializable
- [ ] No breaking changes to detect_artifacts() interface

**Phase 2 (Database & API)**:
- [ ] Migration runs without errors on test database
- [ ] API returns score_breakdown in CatalogEntryResponse
- [ ] Filter parameters properly parse from query string
- [ ] include_below_threshold=true shows all artifacts, false hides <30
- [ ] Data migration preserves existing confidence_score values
- [ ] Integration tests pass for all filter combinations

## Key Files

**Backend (Phase 1)**:
- `skillmeat/core/marketplace/heuristic_detector.py` (lines ~50-150)

**Backend (Phase 2)**:
- `skillmeat/api/routers/marketplace_sources.py` (list_catalog_entries function)
- `skillmeat/cache/models.py` (MarketplaceCatalogEntry ORM model)
- `skillmeat/api/schemas/marketplace.py` (CatalogEntryResponse schema)
- `skillmeat/alembic/versions/` (new migration files)

**Tests**:
- `tests/test_marketplace_*.py` (unit and integration tests)

## Success Criteria

- [ ] MAX_RAW_SCORE = 65 defined and used consistently
- [ ] _score_directory() returns breakdown dict with all signals
- [ ] normalize_score() correctly converts raw to 0-100 scale
- [ ] Database migration creates raw_score and score_breakdown columns
- [ ] CatalogEntryResponse includes raw_score and score_breakdown
- [ ] API filter parameters work: min_confidence, max_confidence, include_below_threshold
- [ ] Unit tests for normalization pass; integration tests for filters pass
- [ ] Data migration populates raw_score for existing entries

## Notes

- Phase 1 and Phase 2 initial tasks can run in parallel
- Phase 2 completion required before frontend work can begin
- Normalization is transparent to existing API (backward compatible)
- Data migration sets raw_score from current confidence_score as fallback
