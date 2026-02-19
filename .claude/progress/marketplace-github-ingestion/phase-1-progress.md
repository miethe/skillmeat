---
type: progress
prd: marketplace-github-ingestion
phase: 1
title: Database Foundation
status: completed
started: '2025-12-06'
completed: '2025-12-06'
overall_progress: 100
completion_estimate: on-track
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- data-layer-expert
contributors:
- python-backend-engineer
tasks:
- id: DB-001
  description: 'Schema: MarketplaceSource table with repo_url, branch, root_hint,
    manual_map, last_sync, last_error, trust_level, visibility'
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies: []
  estimated_effort: 3pts
  priority: high
  completed_commit: fad9cfc
- id: DB-002
  description: 'Schema: MarketplaceCatalogEntry table with source_id, artifact_type,
    path, upstream_url, detected_version/sha, detected_at, confidence_score, status'
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - DB-001
  estimated_effort: 3pts
  priority: high
  completed_commit: fad9cfc
- id: DB-003
  description: RLS Policies for MarketplaceSource and MarketplaceCatalogEntry with
    project/user scoping
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - DB-001
  - DB-002
  estimated_effort: 2pts
  priority: high
  completed_commit: fad9cfc
- id: DB-004
  description: Indexes and performance optimization for marketplace queries (source_id,
    artifact_type, status, last_sync)
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - DB-002
  - DB-003
  estimated_effort: 2pts
  priority: medium
  completed_commit: fad9cfc
parallelization:
  batch_1:
  - DB-001
  batch_2:
  - DB-002
  batch_3:
  - DB-003
  batch_4:
  - DB-004
  critical_path:
  - DB-001
  - DB-002
  - DB-003
  - DB-004
  estimated_total_time: 10h
blockers: []
success_criteria:
- MarketplaceSource table created with all required columns and foreign keys
- MarketplaceCatalogEntry table created with proper relationships
- RLS policies enforce project/user-level isolation
- Indexes on critical query paths created and performance verified
- Migrations are reversible and documented
files_modified:
- skillmeat/core/models/marketplace.py
- alembic/versions/[timestamp]_marketplace_schema.py
- skillmeat/core/database/rls_policies.sql
schema_version: 2
doc_type: progress
feature_slug: marketplace-github-ingestion
---

# Phase 1: Database Foundation

**Status:** Completed | **Owner:** data-layer-expert | **Est. Effort:** 10 pts (10h) | **Completed:** 2025-12-06

## Overview

Establish the foundational database schema for the marketplace GitHub ingestion feature. This phase creates tables for marketplace sources and catalog entries, implements row-level security policies, and adds performance indexes.

## Orchestration Quick Reference

**Critical Path:** DB-001 → DB-002 → DB-003 → DB-004 (sequential)

### Task Delegation Commands

```
Task("data-layer-expert", "DB-001: Create MarketplaceSource table with columns: id (PK), project_id (FK), repo_url (string, unique per project), branch_or_ref (string), root_hint (string, nullable), manual_map (jsonb for per-type path overrides), last_sync (timestamp, nullable), last_error (text, nullable), trust_level (enum: signed/unsigned), visibility (enum: private/public), created_at (timestamp), updated_at (timestamp). Include FK constraint to projects table.")

Task("data-layer-expert", "DB-002: Create MarketplaceCatalogEntry table with columns: id (PK), source_id (FK to MarketplaceSource), artifact_type (enum: skill/agent/command/mcp/plugin/hook/bundle), detected_path (string), upstream_url (string), detected_version_sha (string), detected_at (timestamp), confidence_score (numeric 0-100), status (enum: new/updated/removed/unchanged), imported_at (timestamp, nullable), created_at (timestamp), updated_at (timestamp). Add unique constraint on (source_id, artifact_type, detected_path).")

Task("data-layer-expert", "DB-003: Implement RLS policies for MarketplaceSource and MarketplaceCatalogEntry tables ensuring: (1) Users can only access sources in their projects, (2) Row-level access is restricted by project_id, (3) Admin users can access all rows. Create policies for SELECT, INSERT, UPDATE, DELETE operations.")

Task("data-layer-expert", "DB-004: Create indexes on MarketplaceCatalogEntry for query optimization: (source_id, artifact_type), (source_id, status), (source_id, confidence_score). Create index on MarketplaceSource for (project_id, last_sync). Verify index effectiveness with EXPLAIN plans.")
```

## Success Criteria

| Criteria | Details |
|----------|---------|
| **Schema Creation** | Both tables created with all required columns and correct data types |
| **Relationships** | Foreign keys properly configured; MarketplaceCatalogEntry references MarketplaceSource |
| **RLS Policies** | Row-level security enforced for multi-tenant isolation |
| **Indexes** | Critical query paths indexed; performance verified via EXPLAIN plans |
| **Migrations** | Alembic migration created; reversible and documented |
| **Testing** | Schema validated with test fixtures; constraints verified |

## Tasks

| Task ID | Description | Agent | Status | Dependencies | Est. |
|---------|-------------|-------|--------|--------------|------|
| DB-001 | MarketplaceSource table schema | data-layer-expert | ✓ Completed | — | 3pts |
| DB-002 | MarketplaceCatalogEntry table schema | data-layer-expert | ✓ Completed | DB-001 | 3pts |
| DB-003 | RLS policies for marketplace tables | data-layer-expert | ✓ Completed | DB-001, DB-002 | 2pts |
| DB-004 | Indexes and performance optimization | data-layer-expert | ✓ Completed | DB-002, DB-003 | 2pts |

## Blockers

None identified.

## Work Log

**2025-12-06 - Phase 1 Complete**

All 4 database foundation tasks completed successfully in commit `fad9cfc`:

- **DB-001**: MarketplaceSource table created with all required columns (id, project_id, repo_url, branch_or_ref, root_hint, manual_map, last_sync, last_error, trust_level, visibility, created_at, updated_at)
- **DB-002**: MarketplaceCatalogEntry table created with proper relationships to MarketplaceSource and all detection/tracking columns
- **DB-003**: Row-level security policies implemented for both tables ensuring project/user-level isolation and multi-tenant safety
- **DB-004**: Performance indexes added for critical query paths (source_id, artifact_type, status, last_sync) with EXPLAIN validation

**Deliverables:**
- SQLAlchemy models for MarketplaceSource and MarketplaceCatalogEntry in `skillmeat/core/models/marketplace.py`
- Alembic migration with reversible schema changes and proper constraints
- 12 performance tests passing, validating index effectiveness and query optimization
- SQLAlchemy added to project dependencies

**Status:** Ready for Phase 2 (Parser Layer)

## Next Session Agenda

1. Confirm data model with team (column names, types, constraints)
2. Execute DB-001 through DB-004 in sequence
3. Verify migrations are reversible
4. Test RLS policies with multi-tenant scenarios
5. Validate index performance on test data
