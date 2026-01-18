---
title: "Phases 1-3: Backend Implementation"
description: "Database schema, repository layer, and API endpoints for marketplace sources enhancement"
parent: ../marketplace-sources-enhancement-v1.md
phases: [1, 2, 3]
---

# Phases 1-3: Backend Implementation

**Parent Plan**: [Marketplace Sources Enhancement v1](../marketplace-sources-enhancement-v1.md)

---

## Phase 1: Database Schema & Storage Format

**Duration**: 3 days
**Dependencies**: None
**Assigned Subagent(s)**: data-layer-expert
**Start after**: Project kickoff

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| DB-001 | Source Schema Extension | Extend Source object with repo_description, repo_readme, tags, counts_by_type fields | Schema supports new fields with correct types; optional fields nullable; tags as List[str]; counts_by_type as Dict[str, int] | 2 pts | data-layer-expert | None |
| DB-002 | Manifest Format Update | Update source manifest TOML format to persist new fields | Manifest serializes/deserializes new fields; backward compatible with existing sources | 1 pt | data-layer-expert | DB-001 |
| DB-003 | Lock File Updates | Update lock file format to store resolved tag lists and field fetch status | Lock file includes tags, import_repo_description flag, import_repo_readme flag, fetch_timestamp | 1 pt | data-layer-expert | DB-001 |
| DB-004 | Migration Script | Create migration for existing sources (populate empty tags, null descriptions) | Existing sources migrate without data loss; tags default to empty list | 1 pt | data-layer-expert | DB-003 |
| DB-005 | Storage Validation | Add validation for new field constraints | Tags validated (max 20, alphanumeric+hyphens+underscores, 1-50 chars each); descriptions capped at 2000 chars; README capped at 50KB | 1 pt | data-layer-expert | DB-001 |

### Phase 1 Quality Gates

- [ ] Source schema includes all new fields with correct types
- [ ] Manifest format persists and deserializes new fields
- [ ] Lock file stores tags and import flags
- [ ] Migration script handles existing sources gracefully
- [ ] Field validation enforces constraints
- [ ] No data loss in migration

**Notes**: This phase focuses on storage/serialization, not API yet. The Source model in the codebase represents the storage format. No database migrations needed if using manifest-based storage (TOML), but validation layer must be added.

---

## Phase 2: Repository Layer & Data Access

**Duration**: 3 days
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: python-backend-engineer, data-layer-expert
**Start after**: Phase 1 complete

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| REPO-001 | Source Repository Enhancement | Extend source repository with methods for new fields | get_source_by_id() returns full object with new fields; list_sources() includes counts_by_type | 2 pts | python-backend-engineer | DB-005 |
| REPO-002 | Filter Query Methods | Implement filtering methods for artifact_type, tags, trust_level | filter_by_artifact_type(), filter_by_tags(), filter_by_trust_level() methods implemented | 2 pts | python-backend-engineer | REPO-001 |
| REPO-003 | Composite Filtering | Implement AND logic for multiple filters | apply_filters(artifact_type=None, tags=None, trust_level=None) composes filters correctly | 2 pts | python-backend-engineer | REPO-002 |
| REPO-004 | Cursor Pagination | Update pagination to work with filters | paginate_with_filters() supports cursor-based pagination with optional filters | 2 pts | python-backend-engineer | REPO-003 |
| REPO-005 | Tag Management Methods | Implement tag CRUD operations at source level | add_tags(), remove_tags(), update_tags() work correctly; validation enforced | 1 pt | python-backend-engineer | REPO-001 |
| REPO-006 | Counts by Type Computation | Implement counts_by_type aggregation from catalog entries | compute_counts_by_type(source_id) returns accurate breakdown; caches result | 2 pts | python-backend-engineer | REPO-001 |

### Phase 2 Quality Gates

- [ ] All CRUD operations return objects with new fields
- [ ] Filter methods correctly match criteria
- [ ] Composite filters use AND semantics
- [ ] Cursor pagination handles filters correctly
- [ ] Tag operations validate and persist
- [ ] Counts by type computation accurate for all artifact types
- [ ] Repository layer tests >80% coverage

**Notes**: This phase assumes a manifest-based repository layer (reading/writing TOML files). If using a SQL database, this phase would involve SQLAlchemy model updates and Alembic migrations.

---

## Phase 3: Service Layer, API Schemas & Endpoints

**Duration**: 3 days
**Dependencies**: Phase 2 complete
**Assigned Subagent(s)**: python-backend-engineer, backend-architect
**Start after**: Phase 2 complete

### Phase 3A: Schemas & DTOs (1.5 days)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| API-001 | SourceResponse Schema Extension | Extend SourceResponse Pydantic model with new fields | SourceResponse includes repo_description (Optional[str]), repo_readme (Optional[str]), tags (List[str]), counts_by_type (Dict[str, int]) | 1 pt | python-backend-engineer | REPO-006 |
| API-002 | CreateSourceRequest Extension | Add import_repo_description, import_repo_readme toggles and tags field | CreateSourceRequest includes import_repo_description: bool = False, import_repo_readme: bool = False, tags: Optional[List[str]] = None | 1 pt | python-backend-engineer | API-001 |
| API-003 | UpdateSourceRequest Extension | Add tags field and conditional toggles for editing | UpdateSourceRequest includes tags: Optional[List[str]], import_repo_description: Optional[bool], import_repo_readme: Optional[bool] | 1 pt | python-backend-engineer | API-001 |
| API-004 | Tag Validation Schema | Create validation logic for tag constraints | Tags validated: alphanumeric/hyphens/underscores only, max 20 per source, 1-50 chars each | 1 pt | python-backend-engineer | API-002 |

### Phase 3B: API Endpoints (1.5 days)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| API-005 | Source List with Filtering | Implement GET /api/v1/marketplace/sources with query parameters | Endpoint accepts artifact_type, tags, trust_level, search query params; returns paginated SourceResponse objects | 2 pts | python-backend-engineer | API-004 |
| API-006 | Filter Composition Logic | Implement AND logic for multiple filters in endpoint | Multiple filters compose correctly (e.g., ?artifact_type=skill&tags=ui-ux returns sources matching both) | 2 pts | python-backend-engineer | API-005 |
| API-007 | Source Details Endpoint | Implement optional GET /api/v1/marketplace/sources/{id}/details | Endpoint returns repo_description and repo_readme only (separate from main response to avoid bloat) | 1 pt | python-backend-engineer | API-005 |
| API-008 | Create Source with Details | Implement POST endpoint to create source with repo details fetching | POST /api/v1/marketplace/sources with CreateSourceRequest; fetches details if toggles enabled; returns SourceResponse | 2 pts | backend-architect | API-005 |
| API-009 | Update Source & Tags | Implement PUT endpoint to update source tags and toggle settings | PUT /api/v1/marketplace/sources/{id} accepts UpdateSourceRequest; updates tags, toggles; refetches details if toggled on | 1 pt | python-backend-engineer | API-005 |

### Phase 3C: GitHub Integration & Scanning (1 day)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| SVC-001 | GitHub Scanner Extension | Extend GitHubScanner to fetch repo description and README | scanner.scan_repository() fetches description via GitHub API; handles errors gracefully | 2 pts | python-backend-engineer | API-004 |
| SVC-002 | README Fetching & Truncation | Implement README fetch with 50KB truncation and error handling | README fetched via GitHub API; truncated to 50KB if larger; timeout of 5s per source | 2 pts | backend-architect | SVC-001 |
| SVC-003 | Conditional Fetching Logic | Implement conditional fetch based on toggles | Description/README fetched only if import_repo_description/import_repo_readme = true | 1 pt | python-backend-engineer | SVC-002 |
| SVC-004 | Retry & Graceful Degradation | Implement retry logic for failed fetches | Failed GitHub fetches logged; source created without details; details can be populated on next scan | 1 pt | backend-architect | SVC-003 |
| SVC-005 | OpenTelemetry & Logging | Add spans and structured logging for all operations | Spans created for source CRUD, scanning, filtering; logs include source_id, tags, filter_params, error context | 1 pt | backend-architect | SVC-004 |

### Phase 3 Quality Gates

- [ ] SourceResponse schema complete with validation
- [ ] CreateSourceRequest/UpdateSourceRequest accept toggles and tags
- [ ] Tag validation enforced on all inputs
- [ ] GET /marketplace/sources returns filtered, paginated results
- [ ] All filter combinations work correctly (AND logic)
- [ ] GET /marketplace/sources/{id}/details returns description/README (if populated)
- [ ] POST/PUT endpoints accept new fields and persist correctly
- [ ] GitHub API calls use centralized GitHubClient wrapper
- [ ] Failed GitHub fetches don't block source creation
- [ ] OpenTelemetry spans and structured logs in place
- [ ] All API endpoints documented in OpenAPI spec
- [ ] API layer tests >80% coverage

**Notes**: This phase establishes the API contract for frontend integration. After Phase 3 completion, frontend team can begin component design and implementation independently.

---

## Key Backend Files

| File | Phase | Changes |
|------|-------|---------|
| `skillmeat/api/schemas/marketplace.py` | 3 | Add repo_description, repo_readme, tags, counts_by_type to SourceResponse; add toggles to CreateSourceRequest/UpdateSourceRequest |
| `skillmeat/api/routers/marketplace_sources.py` | 3 | Add filtering query params to GET /marketplace/sources; add GET /sources/{id}/details endpoint; update POST/PUT handlers |
| `skillmeat/core/marketplace/github_scanner.py` | 3 | Add repo description and README fetching with error handling and timeout |
| `skillmeat/core/marketplace/source_manager.py` | 3 | Add tag management methods, filter composition logic |
| `skillmeat/storage/source_manifest.py` | 1-2 | Update manifest serialization to include new fields |
| `skillmeat/storage/lockfile.py` | 1-2 | Update lockfile format for tags and import flags |

---

## Backend Testing Files

| File | Phase | Purpose |
|------|-------|---------|
| `tests/unit/backend/test_tags_validation.py` | 7 | Unit tests for tag validation |
| `tests/unit/backend/test_filtering.py` | 7 | Unit tests for filter logic |
| `tests/integration/api/test_sources_filtering.py` | 7 | Integration tests |
