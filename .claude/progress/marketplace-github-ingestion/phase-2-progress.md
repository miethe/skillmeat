---
type: progress
prd: marketplace-github-ingestion
phase: 2
title: Repository Layer
status: completed
started: '2025-12-06T10:00:00Z'
completed: '2025-12-06T11:30:00Z'
overall_progress: 100
completion_estimate: completed
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
contributors:
- data-layer-expert
tasks:
- id: REPO-001
  description: MarketplaceSourceRepository with CRUD operations and query methods
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - DB-004
  estimated_effort: 3pts
  priority: high
  commit: 10307db
- id: REPO-002
  description: MarketplaceCatalogRepository with filtering, sorting, and bulk operations
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - DB-004
  estimated_effort: 4pts
  priority: high
  commit: 10307db
- id: REPO-003
  description: Query methods for source lookup, catalog filtering by type/status,
    and joined queries
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - REPO-001
  - REPO-002
  estimated_effort: 2pts
  priority: high
  commit: 10307db
- id: REPO-004
  description: Transaction handling for multi-table operations (catalog updates, status
    transitions)
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - REPO-002
  estimated_effort: 2pts
  priority: medium
  commit: 10307db
parallelization:
  batch_1:
  - REPO-001
  - REPO-002
  batch_2:
  - REPO-003
  - REPO-004
  critical_path:
  - REPO-001
  - REPO-002
  - REPO-003
  - REPO-004
  estimated_total_time: 11h
blockers: []
success_criteria:
- MarketplaceSourceRepository provides all CRUD operations
- MarketplaceCatalogRepository supports filtering, sorting, and bulk updates
- Query methods handle complex joins and filters efficiently
- Transaction handling ensures data consistency during bulk operations
- Repository methods are tested with unit and integration tests
files_modified:
- skillmeat/cache/repositories.py
- skillmeat/cache/__init__.py
- skillmeat/api/schemas/marketplace.py
schema_version: 2
doc_type: progress
feature_slug: marketplace-github-ingestion
---

# Phase 2: Repository Layer

**Status:** Planning | **Owner:** python-backend-engineer | **Est. Effort:** 11 pts (11h)

## Overview

Implement data access layers for marketplace sources and catalog entries. This phase builds repositories with CRUD operations, advanced query methods, and transaction support to manage marketplace data consistently.

## Orchestration Quick Reference

**Batch 1 (Parallel):** REPO-001, REPO-002 (3h + 4h)
**Batch 2 (Parallel after Batch 1):** REPO-003, REPO-004 (2h + 2h)

### Task Delegation Commands

```
Task("python-backend-engineer", "REPO-001: Create MarketplaceSourceRepository extending BaseRepository with methods: create_source(project_id, repo_url, branch, root_hint, manual_map, trust_level), get_source(id), list_sources(project_id, filters), update_source(id, fields), delete_source(id). Include filtering by visibility and trust_level. Handle project isolation via RLS.")

Task("python-backend-engineer", "REPO-002: Create MarketplaceCatalogRepository with methods: create_entry(source_id, artifact_type, path, upstream_url, version_sha, confidence), list_entries(source_id, filters=type/status), update_entry(id, status, imported_at), bulk_update_status(source_id, old_status, new_status), get_by_upstream_url(source_id, type, url). Include pagination and sorting.")

Task("python-backend-engineer", "REPO-003: Add query methods to repositories: find_entries_by_type(source_id, artifact_type), find_new_entries(source_id), find_updated_entries(source_id), get_source_with_entries(source_id, filters), count_entries_by_status(source_id). Optimize with eager loading and projections.")

Task("data-layer-expert", "REPO-004: Implement transaction handling in repositories for multi-step operations: (1) Atomic catalog refresh (delete old + insert new), (2) Atomic status transition across multiple entries, (3) Atomic import marking with timestamp. Use context managers and rollback logic. Include logging and error handling.")
```

## Success Criteria

| Criteria | Details |
|----------|---------|
| **CRUD Operations** | All Create, Read, Update, Delete operations implemented for both repositories |
| **Query Methods** | Complex queries working: filtering by type/status, joined queries, pagination |
| **Bulk Operations** | Bulk update methods implemented with efficiency and consistency |
| **Transactions** | Multi-table operations wrapped in transactions with proper rollback |
| **Project Isolation** | All queries properly scoped to project via RLS and application logic |
| **Tests** | Unit and integration tests covering all methods, edge cases, and error paths |

## Tasks

| Task ID | Description | Agent | Status | Dependencies | Est. |
|---------|-------------|-------|--------|--------------|------|
| REPO-001 | MarketplaceSourceRepository CRUD | python-backend-engineer | ⏳ Pending | DB-004 | 3pts |
| REPO-002 | MarketplaceCatalogRepository with filters | python-backend-engineer | ⏳ Pending | DB-004 | 4pts |
| REPO-003 | Advanced query methods and joins | python-backend-engineer | ⏳ Pending | REPO-001, REPO-002 | 2pts |
| REPO-004 | Transaction handling and bulk updates | data-layer-expert | ⏳ Pending | REPO-002 | 2pts |

## Blockers

None identified.

## Next Session Agenda

1. Begin REPO-001 and REPO-002 in parallel after DB phase completes
2. Implement efficient query methods in REPO-003
3. Add transaction support for atomic operations
4. Write comprehensive repository tests with fixtures
5. Verify query performance with test data
