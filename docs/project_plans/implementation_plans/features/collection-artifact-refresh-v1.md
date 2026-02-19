---
title: 'Implementation Plan: Collection Artifact Refresh'
description: Phased implementation for refreshing metadata of existing collection
  artifacts from upstream GitHub sources, resolving stale data issues with automatic
  field updates and drift detection
audience:
- ai-agents
- developers
tags:
- implementation
- planning
- phases
- tasks
- backend
- api
- cli
- metadata-refresh
- drift-detection
created: 2025-01-21
updated: 2025-01-21
category: product-planning
status: completed
related:
- /docs/project_plans/PRDs/features/collection-artifact-refresh-v1.md
- /skillmeat/core/sync.py
- /skillmeat/core/github_metadata.py
- /skillmeat/api/routers/collections.py
schema_version: 2
doc_type: implementation_plan
feature_slug: collection-artifact-refresh
prd_ref: null
---

# Implementation Plan: Collection Artifact Refresh

**Plan ID**: `IMPL-2025-01-21-COLLECTION-REFRESH`

**Date**: 2025-01-21

**Author**: Claude Code (Implementation Orchestrator)

**Related Documents**:
- **PRD**: `/docs/project_plans/PRDs/features/collection-artifact-refresh-v1.md`
- **Sync Manager**: `/skillmeat/core/sync.py` (drift detection reference)
- **GitHub Metadata Extractor**: `/skillmeat/core/github_metadata.py` (existing extraction)
- **Collections Router**: `/skillmeat/api/routers/collections.py` (API integration point)

**Complexity**: Large (L)

**Total Estimated Effort**: 18 story points

**Target Timeline**: 4-5 weeks

**Workflow Track**: Full (Haiku + Sonnet + Opus agents with architecture validation)

---

## Executive Summary

This implementation plan delivers the Collection Artifact Refresh feature for SkillMeat, enabling users to update stale metadata for existing collection artifacts from their upstream GitHub sources. The solution leverages existing infrastructure (GitHubMetadataExtractor, SyncManager, GitHubClient) to build a comprehensive refresh system with dry-run capabilities, detailed change tracking, and update detection.

**Key Outcomes**:
- ✅ Core `CollectionRefresher` class that refreshes artifact metadata
- ✅ CLI `skillmeat collection refresh` command with `--metadata-only`, `--dry-run`, and `--check` flags
- ✅ API endpoint `POST /api/v1/collections/{collection_id}/refresh` with detailed results
- ✅ Update detection that compares upstream SHAs with resolved versions
- ✅ Detailed change tracking showing old/new values for each field
- ✅ Full test coverage (unit, integration, E2E)
- ✅ Rich console output with progress tracking and change summaries

**Impact**:
- Resolves the stale data problem in imported artifacts
- Enables users to bulk refresh collections without manual re-importing
- Provides transparency into what changed with before/after values
- Supports safe experimentation with `--dry-run` mode
- Integrates seamlessly with existing sync and version management systems

---

## Architecture Overview

### Implementation Strategy

**Layer-by-Layer Bottom-Up Construction** (following MeatyPrompts patterns):

1. **Database/Repository Layer**: No changes needed - uses existing artifact storage
2. **Service Layer**: `CollectionRefresher` class in `skillmeat/core/refresher.py`
   - Orchestrates metadata extraction and updates
   - Handles change tracking and result compilation
   - Integrates with `GitHubMetadataExtractor` for upstream data
3. **API Layer**: New endpoint in `skillmeat/api/routers/collections.py`
   - Request/response schemas in `skillmeat/api/schemas/collections.py`
   - Error handling and status codes
4. **CLI Layer**: New command group in `skillmeat/cli.py`
   - Rich output formatting
   - Flag support for dry-run and filtering
5. **Testing Layer**: Unit, integration, and E2E tests

**Dependency Tree**:
```
CollectionRefresher (core service)
  ├── Depends: GitHubMetadataExtractor (fetch metadata)
  ├── Depends: GitHubClient (GitHub API)
  ├── Depends: Artifact model (field updates)
  ├── Depends: CollectionManager (save updates)
  └── Depends: SyncManager (drift detection - Phase 4 only)

RefreshResult (data class)
  └── Depends: RefreshEntryResult (per-artifact tracking)

API Endpoint
  ├── Depends: CollectionRefresher
  ├── Depends: RefreshRequest/RefreshResponse schemas
  └── Depends: CollectionManagerDep (dependency injection)

CLI Command
  ├── Depends: CollectionRefresher
  ├── Depends: CollectionManager
  └── Depends: Rich library (output formatting)
```

### Data Flow

```
User Input (CLI/API)
  ↓
Validate collection and artifacts exist
  ↓
For each artifact with GitHub source:
  ├─ Extract source spec (owner/repo/path/version)
  ├─ Fetch GitHub metadata (extract frontmatter + repo info)
  ├─ Compare with current artifact metadata
  ├─ Track changes (description, tags, author, license, origin_source)
  ├─ Store old/new values for reporting
  └─ Return RefreshEntryResult
  ↓
Compile results (counts, duration, error tracking)
  ↓
If not dry-run: Save updates to collection manifest
  ↓
Return RefreshResult with detailed change summary
  ↓
Format output (CLI: Rich table, API: JSON)
```

### Parallel Work Opportunities

- **Phase 1**: Core refresher class and tests can proceed independently
- **Phase 2**: CLI and API can be built in parallel (both depend on Phase 1)
- **Phase 3**: Test suite expansion can proceed as Phase 1/2 complete
- **Phase 4**: Update checking can begin after Phase 1 skeleton is established

---

## Phase Breakdown

### Phase 1: Core CollectionRefresher Class & Data Models

**Duration**: 5-7 days

**Dependencies**: None (all infrastructure already exists)

**Assigned Subagent(s)**: python-backend-engineer (primary), codebase-explorer (pattern discovery)

**Critical Path**: Yes - all other phases depend on this

#### 1.1: Data Models & Schemas

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| BE-101 | Create RefreshEntryResult dataclass | Define data model for per-artifact refresh results | Dataclass with artifact_id, status, changes, old_values, new_values, error, reason fields; optional fields marked correctly | 0.5 pts | python-backend-engineer | None |
| BE-102 | Create RefreshResult dataclass | Define aggregated refresh results | Dataclass with counts (refreshed, unchanged, skipped, error), entries list, duration_ms; helper methods for summary stats | 0.5 pts | python-backend-engineer | None |
| BE-103 | Create RefreshMode enum | Define refresh operation modes | Enum with METADATA_ONLY, CHECK_ONLY, SYNC modes; used by CLI and API | 0.25 pts | python-backend-engineer | None |
| BE-104 | Define field mapping config | Map Artifact fields to GitHub metadata fields | Dict config mapping 'description'→'description', 'tags'→'topics', 'origin_source'→'url', etc. | 0.25 pts | python-backend-engineer | None |

**Subtotal**: 1.5 story points

#### 1.2: CollectionRefresher Core Implementation

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| BE-105 | Create CollectionRefresher class skeleton | Initialize class with managers and dependencies | Class __init__ accepts CollectionManager, GitHubMetadataExtractor, GitHubClient; lazy initialization patterns used | 0.5 pts | python-backend-engineer | None |
| BE-106 | Implement _parse_source_spec() | Parse GitHub source spec format (owner/repo/path[@version]) | Returns GitHubSourceSpec with owner, repo, path, version; handles invalid formats with exceptions | 0.75 pts | python-backend-engineer | None |
| BE-107 | Implement _fetch_upstream_metadata() | Fetch metadata from GitHub for single artifact | Calls GitHubMetadataExtractor.extract(), handles rate limits and 404s, returns GitHubMetadata or None | 1 pt | python-backend-engineer | None |
| BE-108 | Implement _detect_changes() | Compare artifact metadata with upstream metadata | Returns dict of changed fields with old/new values, handles None comparisons and empty lists | 0.75 pts | python-backend-engineer | None |
| BE-109 | Implement _apply_updates() | Update artifact object with new metadata (in-memory) | Updates artifact fields based on change dict, preserves unchanged fields, returns modified artifact | 0.75 pts | python-backend-engineer | None |
| BE-110 | Implement refresh_metadata() | Main refresh operation for single artifact | Orchestrates parse→fetch→detect→apply, returns RefreshEntryResult with status and changes | 1.5 pts | python-backend-engineer | BE-106, BE-107, BE-108, BE-109 |
| BE-111 | Implement refresh_collection() | Refresh all artifacts in collection | Iterates collection.artifacts, calls refresh_metadata() per artifact, compiles RefreshResult with counts and duration | 1 pt | python-backend-engineer | BE-110 |
| BE-112 | Add error handling and logging | Comprehensive try-catch and logging | Errors captured in RefreshEntryResult.error, logged to logger, non-blocking (continues processing) | 0.75 pts | python-backend-engineer | BE-110, BE-111 |

**Subtotal**: 7.5 story points

#### 1.3: Unit Tests for Core Implementation

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| BE-113 | Unit tests for _parse_source_spec() | Test parsing various source formats | Valid specs parse correctly, invalid formats raise ValueError, all fields extracted | 1 pt | python-backend-engineer | BE-106 |
| BE-114 | Unit tests for _detect_changes() | Test change detection logic | Returns correct old/new values, handles None, empty lists, string comparisons | 1 pt | python-backend-engineer | BE-108 |
| BE-115 | Unit tests for _apply_updates() | Test field updates | Artifact fields updated correctly, unchanged fields preserved, order maintained | 1 pt | python-backend-engineer | BE-109 |
| BE-116 | Unit tests for refresh_metadata() | Test single artifact refresh | Calls correct methods, handles errors, returns correct RefreshEntryResult | 1.5 pts | python-backend-engineer | BE-110 |
| BE-117 | Unit tests for refresh_collection() | Test collection refresh | Processes all artifacts, aggregates results, calculates duration, counts correct | 1.5 pts | python-backend-engineer | BE-111 |
| BE-118 | Mock GitHub API tests | Test error handling for rate limits, 404s, network errors | Graceful handling of GitHubClientError, GitHubRateLimitError, GitHubNotFoundError | 1 pt | python-backend-engineer | BE-107, BE-110 |

**Subtotal**: 6.5 story points

#### Phase 1 Quality Gates

- [ ] All dataclasses defined with correct type hints
- [ ] RefreshResult accurately tracks counts and durations
- [ ] _parse_source_spec() correctly parses all supported source formats
- [ ] _detect_changes() identifies all changed fields with old/new values
- [ ] refresh_metadata() returns RefreshEntryResult with correct status
- [ ] refresh_collection() aggregates results and maintains error summary
- [ ] Unit tests pass with >90% code coverage for refresher module
- [ ] No TypeScript/Pylint errors
- [ ] Error handling prevents crashes; all errors captured in RefreshResult
- [ ] Integration with existing managers (CollectionManager, GitHubMetadataExtractor) works correctly

**Phase 1 Total**: 15.5 story points

---

### Phase 2: CLI Command Implementation

**Duration**: 3-4 days

**Dependencies**: Phase 1 complete (CollectionRefresher tested)

**Assigned Subagent(s)**: python-backend-engineer (primary)

#### 2.1: CLI Command Group & Subcommands

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| BE-201 | Create collection refresh command | Add `skillmeat collection refresh` command | Command accepts collection name, --dry-run, --metadata-only, --check flags | 1 pt | python-backend-engineer | Phase 1 |
| BE-202 | Implement --metadata-only flag | Restrict refresh to metadata fields only | Flag excludes source/path/version updates, filters change dict | 0.5 pts | python-backend-engineer | BE-201 |
| BE-203 | Implement --dry-run flag | Preview changes without saving | Flag skips manifest save, returns RefreshResult with what-if data | 0.75 pts | python-backend-engineer | BE-201 |
| BE-204 | Implement --check flag | Detect available updates only | Flag compares upstream SHAs, returns update availability without applying changes | 1 pt | python-backend-engineer | Phase 1 |
| BE-205 | Implement --collection option | Allow refresh of specific collection | Option resolves collection path, validates exists, targets single collection | 0.5 pts | python-backend-engineer | BE-201 |
| BE-206 | Add artifact filtering | Support --type, --name filters | Filters artifacts before refresh, reduces scope | 0.5 pts | python-backend-engineer | BE-201 |

**Subtotal**: 4.25 story points

#### 2.2: Rich Console Output

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| BE-207 | Implement progress tracking | Show refresh progress as it processes artifacts | Progress bar or spinner, current artifact name, count (X/Y) | 0.75 pts | python-backend-engineer | BE-201 |
| BE-208 | Implement results summary table | Display summary statistics and per-artifact results | Table with artifact_id, status, changes, old_values, new_values columns | 1 pt | python-backend-engineer | BE-201 |
| BE-209 | Implement change details output | Show detailed before/after for changed fields | Formatted output showing field name, old value, new value for each change | 0.75 pts | python-backend-engineer | BE-201 |
| BE-210 | Implement error reporting | Display errors in separate section with context | Error artifact_id, error message, reason for skipping | 0.5 pts | python-backend-engineer | BE-201 |
| BE-211 | Implement dry-run indicator | Clearly show when in dry-run mode | Header message "[DRY RUN]", changes not saved indicator | 0.25 pts | python-backend-engineer | BE-203 |
| BE-212 | Color-code status badges | Visual indicators for refreshed/unchanged/skipped/error | Green for refreshed, gray for unchanged, yellow for skipped, red for error | 0.5 pts | python-backend-engineer | BE-201 |

**Subtotal**: 3.75 story points

#### 2.3: CLI Integration Tests

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| BE-213 | Integration test: basic refresh | Test CLI invocation with real collection | Command executes, refreshes artifacts, displays summary | 1.5 pts | python-backend-engineer | BE-201 |
| BE-214 | Integration test: --dry-run mode | Verify dry-run doesn't save changes | Manifest unchanged after dry-run, RefreshResult still returned | 1 pt | python-backend-engineer | BE-203 |
| BE-215 | Integration test: --metadata-only flag | Verify metadata-only filtering works | Only metadata fields changed, source/version unchanged | 1 pt | python-backend-engineer | BE-202 |
| BE-216 | Integration test: --check mode | Verify update detection without applying changes | Updates detected and returned, manifest unchanged | 1 pt | python-backend-engineer | BE-204 |
| BE-217 | Integration test: error handling | Test CLI graceful error handling | Invalid collection name caught, error message displayed, exit code 1 | 0.75 pts | python-backend-engineer | BE-201 |

**Subtotal**: 5.25 story points

#### Phase 2 Quality Gates

- [ ] `skillmeat collection refresh` command executes without errors
- [ ] All flags (--dry-run, --metadata-only, --check, --collection) work correctly
- [ ] Progress output shows current artifact and progress count
- [ ] Results table displays all refreshed artifacts with changes
- [ ] Change details show old/new values in readable format
- [ ] Errors captured and displayed without crashing CLI
- [ ] Dry-run mode prevents manifest writes
- [ ] --metadata-only filters non-metadata fields
- [ ] --check mode detects updates without applying
- [ ] Integration tests pass with real collection data
- [ ] Exit codes correct (0 for success, 1 for errors)

**Phase 2 Total**: 13.25 story points

---

### Phase 3: API Endpoint Implementation

**Duration**: 3-4 days

**Dependencies**: Phase 1 complete (CollectionRefresher tested)

**Assigned Subagent(s)**: python-backend-engineer (primary)

#### 3.1: API Schemas & Models

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| BE-301 | Create RefreshRequest schema | Define POST request body schema | Schema with mode (metadata_only|check|sync), artifact_filter optional | 0.5 pts | python-backend-engineer | Phase 1 |
| BE-302 | Create RefreshResponse schema | Define API response schema | Schema with RefreshResult data, status code, timestamp, request_id | 0.75 pts | python-backend-engineer | Phase 1 |
| BE-303 | Create RefreshError schema | Define error response format | Schema with error code, message, details for invalid requests | 0.25 pts | python-backend-engineer | Phase 1 |

**Subtotal**: 1.5 story points

#### 3.2: API Endpoint Implementation

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| BE-304 | Add refresh endpoint signature | Define POST /api/v1/collections/{collection_id}/refresh | Endpoint accepts collection_id path param, RefreshRequest body, returns RefreshResponse | 0.75 pts | python-backend-engineer | BE-301, BE-302 |
| BE-305 | Implement collection validation | Verify collection_id exists | Returns 404 if collection not found | 0.5 pts | python-backend-engineer | BE-304 |
| BE-306 | Implement query parameter support | Support ?mode=metadata|check|sync | Query parameter overrides request body, validated against enum | 0.5 pts | python-backend-engineer | BE-304 |
| BE-307 | Wire CollectionRefresher to endpoint | Call refresher.refresh_collection() | Endpoint invokes refresher, passes mode parameter | 0.75 pts | python-backend-engineer | BE-304 |
| BE-308 | Implement result serialization | Convert RefreshResult to JSON | RefreshEntryResult list serialized with all fields, null handling correct | 0.5 pts | python-backend-engineer | BE-304 |
| BE-309 | Add error handling | Comprehensive error responses | GitHub errors→500, validation errors→422, not found→404 | 0.75 pts | python-backend-engineer | BE-304 |
| BE-310 | Add logging | Log refresh operations | Log collection_id, artifact count, duration, changes made | 0.5 pts | python-backend-engineer | BE-304 |

**Subtotal**: 4.25 story points

#### 3.3: API Tests

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| BE-311 | Unit test: endpoint signature | Test route registration and parameter binding | Endpoint responds to POST, accepts collection_id and body, returns 200 | 0.75 pts | python-backend-engineer | BE-304 |
| BE-312 | Unit test: collection validation | Test 404 handling for invalid collection | Returns 404 with appropriate error message | 0.5 pts | python-backend-engineer | BE-305 |
| BE-313 | Unit test: request body handling | Test request deserialization | Valid RefreshRequest deserializes, invalid body returns 422 | 0.75 pts | python-backend-engineer | BE-301 |
| BE-314 | Unit test: query parameter handling | Test mode parameter override | ?mode=check works, invalid mode returns 422 | 0.75 pts | python-backend-engineer | BE-306 |
| BE-315 | Integration test: full endpoint | Test complete refresh operation | E2E test with real collection, verify RefreshResponse contains results | 1.5 pts | python-backend-engineer | BE-304 |
| BE-316 | Integration test: error handling | Test error responses from refresher | GitHub errors surfaced as 500, validations as 422 | 1 pt | python-backend-engineer | BE-309 |
| BE-317 | Performance test: scalability | Test with large collection (100+ artifacts) | Endpoint returns response in <30s, handles concurrent requests | 1 pt | python-backend-engineer | BE-304 |

**Subtotal**: 6.25 story points

#### Phase 3 Quality Gates

- [ ] RefreshRequest and RefreshResponse schemas valid and documented
- [ ] POST /api/v1/collections/{collection_id}/refresh endpoint registered
- [ ] Collection validation returns 404 for invalid IDs
- [ ] Query parameter mode override works correctly
- [ ] CollectionRefresher integrated and called correctly
- [ ] Results serialized to JSON with all fields present
- [ ] Error handling returns appropriate status codes (400, 422, 404, 500)
- [ ] Refresh operations logged with collection_id and duration
- [ ] Unit tests pass with >85% endpoint coverage
- [ ] Integration tests pass with real collection data
- [ ] Performance acceptable for large collections (<30s)
- [ ] OpenAPI spec updated with new endpoint

**Phase 3 Total**: 12 story points

---

### Phase 4: Update Detection & Advanced Features

**Duration**: 4-5 days

**Dependencies**: Phase 1 complete; Phase 2/3 optional (feature works independently)

**Assigned Subagent(s)**: python-backend-engineer (primary), codebase-explorer (pattern discovery)

#### 4.1: SHA-Based Update Detection

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| BE-401 | Implement check_updates() method | Compare upstream SHAs with artifact.resolved_sha | Returns list of UpdateAvailableResult with artifact_id, current_sha, upstream_sha, update_available | 1.5 pts | python-backend-engineer | Phase 1 |
| BE-402 | Integrate with SyncManager.check_drift() | Leverage existing three-way merge logic | Calls SyncManager for drift detection, maps to update availability | 1 pt | python-backend-engineer | BE-401 |
| BE-403 | Implement --check-only CLI flag | Detect updates without applying changes | Flag runs check_updates(), displays summary, exits | 0.75 pts | python-backend-engineer | BE-401 |
| BE-404 | Add API query parameter mode=check | API mode for update detection | ?mode=check runs check_updates(), returns UpdateCheckResponse | 0.75 pts | python-backend-engineer | BE-401 |

**Subtotal**: 4 story points

#### 4.2: Selective Field Refresh

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| BE-405 | Add field whitelist configuration | Allow users to refresh only specific fields | Config dict mapping field names, used by refresh_metadata() | 0.75 pts | python-backend-engineer | Phase 1 |
| BE-406 | Implement field-selective CLI flag | Add --fields flag to CLI | --fields "description,tags" refreshes only those fields | 0.75 pts | python-backend-engineer | BE-405 |
| BE-407 | Add field validation | Validate allowed field names | Rejects invalid field names, provides helpful error message | 0.5 pts | python-backend-engineer | BE-405 |

**Subtotal**: 2 story points

#### 4.3: Rollback Support

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| BE-408 | Implement refresh snapshot creation | Save pre-refresh collection state | Creates snapshot before refresh, tagged with "pre-refresh" | 0.75 pts | python-backend-engineer | Phase 1 |
| BE-409 | Add --rollback flag to CLI | Restore collection to pre-refresh state | Flag rolls back to most recent pre-refresh snapshot | 0.75 pts | python-backend-engineer | BE-408 |
| BE-410 | Document rollback procedure | User-facing documentation | Doc explains snapshot tagging and rollback process | 0.5 pts | python-backend-engineer | BE-408 |

**Subtotal**: 2 story points

#### 4.4: Advanced Tests & Performance

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| BE-411 | Unit tests: update detection | Test SHA comparison and drift detection | Returns correct update_available status for various scenarios | 1 pt | python-backend-engineer | BE-401 |
| BE-412 | Unit tests: field selective refresh | Test field whitelist filtering | Only whitelisted fields refreshed, others unchanged | 0.75 pts | python-backend-engineer | BE-405 |
| BE-413 | Integration test: end-to-end update flow | Test detect→decide→refresh→verify | Updates detected, applied, verified in manifest | 1.5 pts | python-backend-engineer | BE-401 |
| BE-414 | Performance: large collection refresh | Benchmark refresh_collection() | <5s per 50 artifacts (100 artifacts <10s) | 1 pt | python-backend-engineer | Phase 1 |
| BE-415 | Stress test: concurrent refreshes | Test thread safety and rate limiting | Multiple simultaneous collections refresh without conflicts | 1 pt | python-backend-engineer | Phase 1 |

**Subtotal**: 5.25 story points

#### Phase 4 Quality Gates

- [ ] check_updates() correctly compares SHAs and detects available updates
- [ ] SyncManager integration provides accurate drift detection
- [ ] --check-only CLI flag works and displays update summary
- [ ] API mode=check query parameter returns correct results
- [ ] Field whitelist configuration recognized and applied
- [ ] --fields CLI flag filters refresh to specified fields only
- [ ] Invalid field names rejected with helpful error message
- [ ] Pre-refresh snapshots created and tagged correctly
- [ ] Rollback restores collection to pre-refresh state
- [ ] All unit tests pass with >90% coverage
- [ ] Integration tests pass with real-world scenarios
- [ ] Performance acceptable for large collections
- [ ] Thread-safe and handles concurrent operations

**Phase 4 Total**: 13.25 story points

---

## Cross-Phase Concerns

### Error Handling Strategy

All phases must implement comprehensive error handling:

1. **GitHub API Errors**:
   - Rate limit: Captured, returned in RefreshEntryResult with reason "Rate limited"
   - 404 Not Found: Captured, returned with reason "GitHub resource not found"
   - Auth errors: Captured, surfaced as helpful message
   - Network errors: Captured, with retry guidance

2. **Validation Errors**:
   - Invalid source spec: Return error with expected format
   - Collection not found: 404 (API) or CLI error message
   - Invalid artifact type: Skip with reason "Unsupported type"

3. **File I/O Errors**:
   - Manifest save failure: Rolled back, error returned
   - Permission errors: Clear error message with guidance

4. **Non-Blocking**: All errors captured in RefreshResult, processing continues

### Thread Safety & Concurrency

- CollectionRefresher must be thread-safe (use locks for shared state)
- GitHubClient is already thread-safe (centralized wrapper)
- Manifest reads/writes must use atomic operations
- No modifications to shared managers during refresh

### Rate Limiting Integration

- Respect GitHubClient rate limiting (automatic)
- Implement backoff strategy if rate limited
- Store last rate limit check time
- Log rate limit warnings

---

## Success Metrics & Acceptance Criteria

### Functional Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Artifacts refreshed per collection | 100% processable | All artifacts with GitHub sources successfully refreshed or error logged |
| Metadata accuracy | 100% | All fields match upstream GitHub sources |
| Change detection | 100% | All actual changes detected and reported |
| False positives | 0% | No spurious changes reported |

### Performance Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Single artifact refresh | <500ms | Time to fetch + parse + update one artifact |
| Collection refresh (50 artifacts) | <5s | End-to-end time for 50-artifact collection |
| Collection refresh (100+ artifacts) | <30s | End-to-end time for 100+ artifacts with parallelization if needed |
| Memory usage | <100MB | Peak memory during large collection refresh |
| GitHub API rate limits | Respected | No 429 errors, backoff implemented if needed |

### Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Test coverage | >90% | Unit test coverage for core modules |
| Integration test pass rate | 100% | All integration tests passing |
| Error handling | No crashes | All errors caught and reported gracefully |
| Documentation | Complete | All public APIs documented with examples |

### User Experience Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| CLI clarity | Easy to use | Users understand --dry-run, --metadata-only flags without help |
| API documentation | Clear | OpenAPI spec complete with examples |
| Error messages | Actionable | Users understand what went wrong and how to fix it |
| Dry-run confidence | High | Users trust dry-run correctly predicts actual changes |

---

## Risk Mitigation

### Risk 1: Stale Cache Data

**Risk**: CollectionManager's cache might return stale artifact data during refresh

**Mitigation**:
- Always read fresh from filesystem for refresh operations (bypass cache)
- Invalidate cache after updates applied
- Use `--no-cache` flag during refresh in CLI

**Assigned to**: Phase 1 testing

---

### Risk 2: Incomplete Metadata Extraction

**Risk**: GitHub metadata extraction might fail for some artifact types or formats

**Mitigation**:
- Graceful fallback if extraction fails
- Log all extraction failures with artifact details
- Don't fail entire collection if single artifact fails
- Return RefreshEntryResult with status "error" and error message

**Assigned to**: Phase 1 BE-112 (error handling)

---

### Risk 3: Breaking Changes to Artifact Metadata

**Risk**: Refreshing might overwrite user customizations

**Mitigation**:
- Implement --dry-run to preview changes first
- Show old/new values in results so users can verify
- Optional --metadata-only to avoid touching source/version
- Create snapshots for rollback if needed

**Assigned to**: Phase 2, Phase 4

---

### Risk 4: Rate Limiting on GitHub API

**Risk**: Refreshing large collections might hit GitHub rate limits (60/hr unauthenticated)

**Mitigation**:
- Require GitHub token for production (5000/hr authenticated)
- Implement exponential backoff if rate limited
- Cache metadata for 1 hour to reduce requests
- Surface rate limit status to user

**Assigned to**: Phase 1 BE-107

---

### Risk 5: API Endpoint Latency

**Risk**: Large collection refresh might timeout (default HTTP timeout ~30s)

**Mitigation**:
- Implement streaming response or background job for large collections
- Return partial results if timeout occurs
- Document expected duration for large collections
- Provide --async mode (Phase 4+ enhancement)

**Assigned to**: Phase 3 BE-317

---

## Integration Points

### Existing Infrastructure Used

1. **GitHubMetadataExtractor** (`skillmeat/core/github_metadata.py`)
   - Used by: BE-107 (fetch metadata)
   - Function: Extracts frontmatter + repo metadata from GitHub
   - No changes needed

2. **GitHubClient** (`skillmeat/core/github_client.py`)
   - Used by: GitHubMetadataExtractor (internal)
   - Function: Centralized GitHub API wrapper
   - No changes needed

3. **CollectionManager** (`skillmeat/core/collection.py`)
   - Used by: BE-111 (save updates to manifest)
   - Function: Loads/saves collections
   - No changes needed

4. **SyncManager** (`skillmeat/core/sync.py`)
   - Used by: Phase 4 BE-402 (drift detection)
   - Function: check_drift() for three-way merge
   - No changes needed

5. **Artifact Model** (`skillmeat/core/artifact.py`)
   - Used by: BE-109 (update fields)
   - Function: Field updates, field access
   - No changes needed

### New Files Created

| File | Purpose | Phase |
|------|---------|-------|
| `skillmeat/core/refresher.py` | Core CollectionRefresher class | Phase 1 |
| `skillmeat/api/schemas/refresh.py` | RefreshRequest, RefreshResponse schemas | Phase 3 |
| `tests/unit/test_refresher.py` | Unit tests for refresher | Phase 1 |
| `tests/integration/test_refresh_cli.py` | CLI integration tests | Phase 2 |
| `tests/integration/test_refresh_api.py` | API integration tests | Phase 3 |
| `docs/guides/artifact-refresh-guide.md` | User documentation | Phase 4 |

### Files Modified

| File | Changes | Phase |
|------|---------|-------|
| `skillmeat/cli.py` | Add `collection refresh` command group | Phase 2 |
| `skillmeat/api/routers/collections.py` | Add `POST /collections/{id}/refresh` endpoint | Phase 3 |
| `skillmeat/api/schemas/collections.py` | Add refresh-related schemas | Phase 3 |

---

## Deliverables by Phase

### Phase 1 Deliverables
- `skillmeat/core/refresher.py` with CollectionRefresher class
- RefreshEntryResult and RefreshResult dataclasses
- Unit test suite (>90% coverage)
- Internal documentation (docstrings)

### Phase 2 Deliverables
- CLI command: `skillmeat collection refresh`
- Support for --dry-run, --metadata-only, --check, --collection flags
- Rich console output with progress tracking
- CLI integration tests
- User-facing CLI help text

### Phase 3 Deliverables
- API endpoint: `POST /api/v1/collections/{collection_id}/refresh`
- Request/response schemas for Pydantic validation
- API tests (unit + integration)
- OpenAPI spec updates
- API documentation and examples

### Phase 4 Deliverables
- Update detection with SHA comparison
- Selective field refresh capability
- Snapshot/rollback support
- Advanced tests and performance benchmarks
- User guide documentation

---

## Testing Strategy

### Unit Tests (Phase 1, 3, 4)

**Coverage Target**: >90% for core modules

**Test Organization**:
```
tests/unit/
  test_refresher.py
    - TestRefreshEntryResult (dataclass validation)
    - TestRefreshResult (aggregation)
    - TestCollectionRefresher
      - test_parse_source_spec_valid()
      - test_parse_source_spec_invalid()
      - test_fetch_upstream_metadata()
      - test_detect_changes()
      - test_apply_updates()
      - test_refresh_metadata()
      - test_refresh_collection()
      - test_error_handling()
```

**Mocking Strategy**:
- Mock GitHubMetadataExtractor with predefined metadata
- Mock GitHubClient for rate limit and 404 scenarios
- Mock CollectionManager for save operations
- Use fixtures for test artifacts and collections

### Integration Tests (Phase 2, 3)

**Coverage Target**: All major workflows end-to-end

**Test Organization**:
```
tests/integration/
  test_refresh_cli.py
    - test_refresh_cli_basic()
    - test_refresh_cli_dry_run()
    - test_refresh_cli_metadata_only()
    - test_refresh_cli_check_mode()
    - test_refresh_cli_error_handling()
  test_refresh_api.py
    - test_refresh_endpoint_basic()
    - test_refresh_endpoint_dry_run()
    - test_refresh_endpoint_collection_not_found()
    - test_refresh_endpoint_mode_parameter()
    - test_refresh_endpoint_error_handling()
```

**Test Data**:
- Real collection fixtures with GitHub sources
- Mock GitHub API responses for predictable testing
- Error scenarios (rate limit, network, auth)

### E2E Tests (Phase 3, 4)

**Scope**: Full workflow from CLI invocation to manifest update

**Scenarios**:
1. User runs `skillmeat collection refresh` on real collection
2. User uses --dry-run to preview changes
3. User applies changes and verifies manifest updated
4. User detects updates with --check mode
5. User selectively refreshes specific fields
6. User rolls back from snapshot

---

## Documentation Plan

### User-Facing Documentation

1. **CLI Help Text** (Phase 2)
   - Auto-generated from Click decorators
   - Examples for common usage patterns

2. **User Guide** (Phase 4)
   - File: `docs/guides/artifact-refresh-guide.md`
   - Topics:
     - When to use refresh vs re-import
     - Understanding the diff output
     - Dry-run workflow
     - Troubleshooting common issues
     - Performance considerations

3. **API Documentation** (Phase 3)
   - Auto-generated OpenAPI spec
   - Example requests/responses
   - Error code reference

### Developer Documentation

1. **Code Documentation** (All phases)
   - Docstrings for all public methods
   - Type hints throughout
   - Design decisions in module docstrings

2. **Architecture Documentation**
   - Data flow diagrams
   - Integration points with existing systems
   - Dependency tree

---

## Timeline & Milestones

```
Week 1:   Phase 1 - Core CollectionRefresher (Days 1-5)
Week 2:   Phase 1 completion + Phase 2 start (Days 6-10)
Week 3:   Phase 2 completion + Phase 3 start (Days 11-15)
Week 4:   Phase 3 completion + Phase 4 start (Days 16-20)
Week 5:   Phase 4 completion, polish, and merge (Days 21-25)

Critical Path:
  Phase 1 (5 days) → Phase 2/3 in parallel (7 days) → Phase 4 (5 days) = 17 days total
  With testing and polish: 20-25 days (4-5 weeks)
```

### Key Milestones

1. **M1 (Day 5)**: Phase 1 complete - CollectionRefresher tested and ready
2. **M2 (Day 10)**: Phase 2 complete - CLI command functional
3. **M3 (Day 15)**: Phase 3 complete - API endpoint ready
4. **M4 (Day 20)**: Phase 4 complete - Advanced features ready
5. **M5 (Day 25)**: All phases merged, documentation complete, ready for release

---

## Quality Assurance Checklist

### Pre-Merge Checklist

- [ ] All tests pass (unit, integration, E2E)
- [ ] Code coverage >90% for core modules
- [ ] No TypeScript/Pylint errors
- [ ] Type hints complete and correct
- [ ] Docstrings complete for all public APIs
- [ ] Error messages clear and actionable
- [ ] Performance benchmarks met
- [ ] GitHub API rate limits respected
- [ ] Thread safety verified
- [ ] Security review completed (no credential leaks)
- [ ] Documentation updated
- [ ] API schema validated against OpenAPI spec
- [ ] Backward compatibility maintained (no breaking changes)
- [ ] Code review completed and approved

### Rollout Checklist

- [ ] Feature flag enabled (if applicable)
- [ ] Monitoring/alerting configured
- [ ] User documentation published
- [ ] Release notes prepared
- [ ] Changelog updated
- [ ] Database migrations tested (if applicable)
- [ ] Rollback plan documented

---

## Appendix: Data Structures

### RefreshEntryResult

```python
@dataclass
class RefreshEntryResult:
    """Result for refreshing a single artifact."""

    artifact_id: str                          # "skill:canvas"
    status: str                               # "refreshed", "unchanged", "skipped", "error"
    changes: List[str]                        # ["description", "tags"]
    old_values: Optional[Dict[str, Any]]      # {"description": "old", "tags": []}
    new_values: Optional[Dict[str, Any]]      # {"description": "new", "tags": ["tag1"]}
    error: Optional[str]                      # Error message if status="error"
    reason: Optional[str]                     # "No GitHub source", "Rate limited", etc.
    duration_ms: float                        # Time to refresh this artifact
```

### RefreshResult

```python
@dataclass
class RefreshResult:
    """Aggregated result for collection refresh."""

    refreshed_count: int                      # Number of artifacts refreshed
    unchanged_count: int                      # Number with no changes
    skipped_count: int                        # Number skipped (no GitHub source, etc.)
    error_count: int                          # Number with errors
    entries: List[RefreshEntryResult]         # Per-artifact results
    duration_ms: float                        # Total time

    @property
    def total_processed(self) -> int:
        return self.refreshed_count + self.unchanged_count + self.skipped_count + self.error_count

    @property
    def success_rate(self) -> float:
        if self.total_processed == 0:
            return 1.0
        return (self.refreshed_count + self.unchanged_count) / self.total_processed
```

### RefreshRequest (API Schema)

```python
class RefreshRequest(BaseModel):
    """Request to refresh collection artifacts."""

    mode: str = Field(
        default="metadata_only",
        enum=["metadata_only", "check_only", "sync"],
        description="Refresh mode"
    )
    artifact_filter: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Filter artifacts by type, name, etc."
    )
```

### RefreshResponse (API Schema)

```python
class RefreshResponse(BaseModel):
    """Response from refresh endpoint."""

    status: str                        # "success", "partial", "error"
    timestamp: datetime
    request_id: str
    result: RefreshResult              # Full RefreshResult data
    took_ms: float
```

---

## Known Limitations & Future Enhancements

### Limitations (Phase 1)

1. **No async processing**: Refresh blocks until complete
   - Enhancement: Phase 4+ could add background job support

2. **No incremental updates**: Each refresh is full refresh
   - Enhancement: Could track last refresh time and do incremental

3. **Limited to GitHub sources**: Only refreshes artifacts with GitHub source URLs
   - Enhancement: Phase 4+ could add support for other sources

4. **No webhook support**: No real-time update notifications
   - Enhancement: Future GitHub webhook integration

### Future Enhancements

1. **Scheduled Refreshes**: Automatically refresh on schedule
2. **Selective Updates**: Only update changed fields
3. **Batch Operations**: Refresh multiple collections at once
4. **Update Notifications**: Notify users when updates available
5. **Conflict Resolution**: Enhanced merge strategies for conflicting changes
6. **Custom Field Mapping**: Allow users to customize which fields to refresh

---

**Plan Status**: DRAFT

**Last Updated**: 2025-01-21

**Next Review**: After Phase 1 completion (estimated 2025-02-04)
