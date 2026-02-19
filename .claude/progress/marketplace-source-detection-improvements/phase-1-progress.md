---
type: progress
prd: marketplace-source-detection-improvements
phase: 1
phase_name: Database & Schema
status: completed
progress: 100
total_tasks: 4
completed_tasks: 4
effort: 5-8 pts
created: 2026-01-05
updated: 2026-01-05
completed_at: 2026-01-05
assigned_to:
- data-layer-expert
dependencies: []
tasks:
- id: P1.1
  name: Validate manual_map column
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies: []
  effort: 2 pts
- id: P1.2
  name: Validate metadata_json column
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies: []
  effort: 2 pts
- id: P1.3
  name: Document manual_map schema
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies: []
  effort: 2 pts
- id: P1.4
  name: Create Pydantic validation schemas
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - P1.1
  - P1.2
  - P1.3
  effort: 3 pts
parallelization:
  batch_1:
  - P1.1
  - P1.2
  - P1.3
  batch_2:
  - P1.4
schema_version: 2
doc_type: progress
feature_slug: marketplace-source-detection-improvements
---

# Phase 1: Database & Schema

## Overview

Validate existing database schema and create Pydantic validation schemas. No migrations needed - reusing existing columns.

**Duration**: 1 day
**Effort**: 5-8 pts
**Assigned**: data-layer-expert
**Dependencies**: None (foundation phase)

## Orchestration Quick Reference

**Batch 1.1** (Parallel - 3 tasks):
```
Task("data-layer-expert", "P1.1: Validate MarketplaceSource.manual_map column exists and supports JSON storage. P1.2: Validate MarketplaceCatalogEntry.metadata_json can store content_hash field. P1.3: Document manual_map JSON schema structure with directory paths as keys and artifact types as values", model="haiku")
```

**Batch 1.2** (Sequential - 1 task):
```
Task("data-layer-expert", "P1.4: Create Pydantic validation schemas for manual_map structure and deduplication response in skillmeat/api/schemas/marketplace.py", model="haiku")
```

## Task Details

### P1.1: Validate manual_map Column
- **File**: `skillmeat/cache/models.py` (line 1173)
- **Action**: Verify MarketplaceSource.manual_map column exists and supports JSON storage
- **Expected**: Column type is JSON or compatible type (e.g., Text with JSON serialization)

### P1.2: Validate metadata_json Column
- **File**: `skillmeat/cache/models.py` (line 1368)
- **Action**: Verify MarketplaceCatalogEntry.metadata_json can store content_hash field
- **Expected**: Column supports arbitrary JSON data including new content_hash key

### P1.3: Document manual_map Schema
- **Action**: Create schema documentation showing structure
- **Format**:
  ```json
  {
    "path/to/directory": "skill",
    "another/path": "command",
    "nested/parent": "agent"
  }
  ```
- **Valid Types**: skill, command, agent, mcp_server, hook

### P1.4: Create Pydantic Validation Schemas
- **File**: `skillmeat/api/schemas/marketplace.py`
- **Schemas**:
  - `ManualMapEntry` - validate directory path → artifact type mapping
  - `DeduplicationResponse` - validate dedup counts (duplicates_removed, cross_source_duplicates)

## Quality Gates

- [ ] manual_map column validated in MarketplaceSource model
- [ ] metadata_json column validated in MarketplaceCatalogEntry model
- [ ] Schema documentation created with examples
- [ ] Pydantic schemas compile and validate test data

## Key Files

- `skillmeat/cache/models.py` - MarketplaceSource (line 1173), MarketplaceCatalogEntry (line 1368)
- `skillmeat/api/schemas/marketplace.py` - Pydantic schemas

## Notes

- **PRD**: `/docs/project_plans/PRDs/features/marketplace-source-detection-improvements-v1.md`
- **Implementation Plan**: `/docs/project_plans/implementation_plans/features/marketplace-source-detection-improvements-v1.md`
- No database migrations required - reusing existing columns
- Foundation phase for all subsequent work
