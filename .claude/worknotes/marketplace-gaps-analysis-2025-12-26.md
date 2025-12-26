# Marketplace GitHub Ingestion Implementation - Gap Analysis

**Date**: 2025-12-26
**Status**: Comprehensive gap analysis complete
**Scope**: Phase 3 (Service Layer) and Phase 4 (API Layer)

---

## Executive Summary

The marketplace GitHub ingestion feature has **structural completion** (all files exist and compile), but suffers from **critical functional gaps** that prevent end-to-end operations. The implementation follows the plan's architecture but lacks integration between layers.

**Key Issue**: The heuristic detector is fully implemented but **completely decoupled** from the scanning pipeline - it's never called, so all scans return empty artifact lists.

---

## Phase 3: Service Layer Assessment

### SVC-001: DTOs & Models ✅ COMPLETE

**Status**: IMPLEMENTED
**File**: `skillmeat/api/schemas/marketplace.py`

All required Pydantic models exist:
- `CreateSourceRequest`, `SourceResponse`, `SourceListResponse`
- `ScanResultDTO`, `ImportResultDTO`
- `CatalogEntryResponse`, `CatalogListResponse`
- `DetectedArtifact`, `HeuristicMatch`

**Validation**: Full round-trip serialization working.

---

### SVC-002: Heuristic Detector ✅ COMPLETE (BUT DISCONNECTED)

**Status**: FULLY IMPLEMENTED but NEVER CALLED
**File**: `skillmeat/core/marketplace/heuristic_detector.py` (489 lines)

**What's Implemented**:
- ✅ `HeuristicDetector` class with multi-signal scoring
- ✅ `analyze_paths()` - analyzes file tree, applies heuristics
- ✅ Scoring algorithm: dir-name (10pt) + manifest (20pt) + extension (5pt) + parent hint (15pt) - depth penalty
- ✅ Configurable thresholds and weights
- ✅ `matches_to_artifacts()` - converts matches to `DetectedArtifact` objects
- ✅ `detect_artifacts_in_tree()` convenience function
- ✅ Comprehensive test data in `__main__`

**Problem**: Not wired into GitHub scanner:

```python
# In github_scanner.py lines 159-174:
# NOTE: This will be uncommented once SVC-002 (heuristic detector) is implemented
# artifacts = detect_artifacts_in_tree(...)

# Placeholder until heuristic detector is implemented
artifacts = []
logger.warning("Heuristic detector not yet implemented (SVC-002).")
```

**Gap**: Heuristic detector is fully functional but dormant. Scan always returns `artifacts_found=0`.

---

### SVC-003: GitHub Scanning Service ✅ PARTIAL

**Status**: IMPLEMENTED (fetches tree, extracts paths) but RETURNS EMPTY RESULTS
**File**: `skillmeat/core/marketplace/github_scanner.py` (494 lines)

**What's Implemented**:
- ✅ `GitHubScanner` class with GitHub API integration
- ✅ `_fetch_tree()` - recursively fetches repository tree using Git Trees API
- ✅ `_extract_file_paths()` - filters paths by root_hint, caps at max_files
- ✅ `_get_ref_sha()` - resolves git references to commit SHA
- ✅ `_request_with_retry()` - exponential backoff + rate limit handling
- ✅ `get_file_content()` - fetches file contents (for README harvesting)
- ✅ Rate limit detection (403 with empty remaining, 429)
- ✅ Observability: metrics + operation context

**What's Missing**:
- ❌ **Line 170**: Returns empty artifact list
- ❌ **Heuristic detector not called** - commented out lines 161-167
- ❌ **Link harvester never invoked** - no README scanning happens
- ❌ **No error recovery** - scan failures not retried

**Impact**: Scans successfully fetch tree structure but discover 0 artifacts.

---

### SVC-004: README Link Harvester ✅ COMPLETE (BUT UNUSED)

**Status**: FULLY IMPLEMENTED but NEVER CALLED
**File**: `skillmeat/core/marketplace/link_harvester.py` (309 lines)

**What's Implemented**:
- ✅ `ReadmeLinkHarvester` class with pattern matching
- ✅ `harvest_links()` - extracts GitHub URLs from markdown
- ✅ Confidence scoring: base 0.3 + keyword matches + trusted orgs
- ✅ Cycle protection via `_visited` set
- ✅ Ignore patterns (issues, pulls, releases, etc.)
- ✅ `harvest_readme_links()` convenience function
- ✅ Test case with full verification

**Problem**:
- No integration point in scan pipeline
- `GitHubScanner` doesn't call `ReadmeLinkHarvester`
- No mechanism to enqueue secondary scans

**Gap**: Harvester is production-ready but orphaned.

---

### SVC-005: Catalog Diff Engine ✅ COMPLETE (BUT UNUSED)

**Status**: FULLY IMPLEMENTED but NEVER CALLED
**File**: `skillmeat/core/marketplace/diff_engine.py` (334 lines)

**What's Implemented**:
- ✅ `CatalogDiffEngine` class with change detection
- ✅ `compute_diff()` - compares old vs new by upstream_url
- ✅ Categorizes: NEW, UPDATED, REMOVED, UNCHANGED
- ✅ SHA-based update detection
- ✅ Converts to `CatalogDiff` for repository layer
- ✅ Complete test case with mock data

**Problem**:
- **Line 545 in marketplace_sources.py**: `TODO: Use diff engine for incremental updates`
- Currently: `ctx.replace_catalog_entries(new_entries)` - destroys all entries every scan
- Never: `engine.compute_diff(existing, new_scan, source_id)`

**Gap**: Replace strategy is placeholder. True incremental updates never happen.

---

### SVC-006: Import Coordinator ✅ COMPLETE

**Status**: FULLY IMPLEMENTED
**File**: `skillmeat/core/marketplace/import_coordinator.py` (394 lines)

**What's Implemented**:
- ✅ `ImportCoordinator` with conflict detection
- ✅ Strategies: SKIP, OVERWRITE, RENAME
- ✅ `import_entries()` - processes catalog entries
- ✅ `_process_entry()` - applies conflict strategy
- ✅ `_get_existing_artifacts()` - scans collection for conflicts
- ✅ `_compute_local_path()` - handles old/new collection structures
- ✅ `check_conflicts()` - non-destructive conflict detection
- ✅ Full test case with all strategies

**Integration**: Called correctly by `import_artifacts()` endpoint (line 831 in marketplace_sources.py).

**Caveat**: Actual artifact file downloads commented as placeholder:
```python
# In a full implementation, this would:
# 1. Download artifact files from upstream_url
# 2. Write to local_path
# 3. Update manifest
entry.status = ImportStatus.SUCCESS  # Marks as success without downloading
```

---

### SVC-007: Error Handling & Observability ✅ COMPLETE

**Status**: FULLY IMPLEMENTED
**File**: `skillmeat/core/marketplace/observability.py` (469 lines)

**What's Implemented**:
- ✅ `MarketplaceError` + subclasses (ScanError, DetectionError, ImportError, RateLimitError)
- ✅ `operation_context()` context manager with tracing
- ✅ `log_operation_start()`, `log_operation_end()`
- ✅ `log_error()` with structured logging
- ✅ `ErrorResponse` serialization
- ✅ OpenTelemetry integration via `trace_operation()`
- ✅ Metrics: `marketplace_scan_duration_seconds`, `marketplace_scan_errors_total`, etc.

**Integration**: Used correctly in `github_scanner.py` (lines 131-137, 219).

---

## Phase 4: API Layer Assessment

### API-001: Marketplace Sources Router ✅ COMPLETE

**Status**: ALL ENDPOINTS IMPLEMENTED
**File**: `skillmeat/api/routers/marketplace_sources.py` (899 lines)

**Endpoints**:
- ✅ `POST /marketplace/sources` - Create source (lines 151-232)
- ✅ `GET /marketplace/sources` - List sources with pagination (lines 234-290)
- ✅ `GET /marketplace/sources/{id}` - Get source by ID (lines 292-335)
- ✅ `PATCH /marketplace/sources/{id}` - Update source (lines 337-416)
- ✅ `DELETE /marketplace/sources/{id}` - Delete source (lines 418-461)

**Quality**:
- ✅ Proper HTTP status codes (201 Created, 204 No Content)
- ✅ Error handling with HTTPException
- ✅ Helper functions: `parse_repo_url()`, `source_to_response()`

---

### API-002: Rescan Endpoint ✅ IMPLEMENTED (RETURNS EMPTY RESULTS)

**Status**: ENDPOINT EXISTS, LOGIC INCOMPLETE
**Location**: `skillmeat/api/routers/marketplace_sources.py` lines 468-593

**Implemented**:
- ✅ `POST /marketplace/sources/{id}/rescan` endpoint
- ✅ Returns `ScanResultDTO` immediately (202 Accepted pattern noted but not implemented)
- ✅ Calls `GitHubScanner.scan_repository()`
- ✅ Updates source status (pending → scanning → success/error)
- ✅ Transaction handling with `MarketplaceTransactionHandler`

**Problem** (line 545-548):
```python
# TODO: Use diff engine for incremental updates
# Currently heuristic detector returns empty list, so this is a placeholder
new_entries: List[MarketplaceCatalogEntry] = []
ctx.replace_catalog_entries(new_entries)
```

**Gap**:
- Scan returns 0 artifacts (because heuristic detector is disconnected)
- Catalog always becomes empty after rescan
- No diff engine use (all entries replaced, not incrementally updated)

---

### API-003: Artifacts Listing ✅ COMPLETE

**Status**: FULLY IMPLEMENTED
**Location**: `skillmeat/api/routers/marketplace_sources.py` lines 600-727

**Implemented**:
- ✅ `GET /marketplace/sources/{id}/artifacts` endpoint
- ✅ Filters: artifact_type, status, min_confidence
- ✅ Pagination with cursor support
- ✅ Aggregated counts by status and type
- ✅ Proper error handling

**Works For**: Empty catalogs (since scans return 0 artifacts)

---

### API-004: Import Endpoint ✅ COMPLETE

**Status**: FULLY IMPLEMENTED
**Location**: `skillmeat/api/routers/marketplace_sources.py` lines 734-899

**Implemented**:
- ✅ `POST /marketplace/sources/{id}/import` endpoint
- ✅ Single + bulk imports
- ✅ Conflict strategy parameter (skip, overwrite, rename)
- ✅ Calls `ImportCoordinator.import_entries()`
- ✅ Updates catalog entries with import status
- ✅ Returns summary with statistics

**Works For**: Small test imports (limited by empty catalogs)

---

### API-005: Error & Validation ✅ COMPLETE

**Status**: FULLY IMPLEMENTED
**Location**: Distributed across all endpoints

**Implemented**:
- ✅ Request validation (repository URL format via `parse_repo_url()`)
- ✅ Response formatting with HTTPException + status codes
- ✅ Error details extraction and logging
- ✅ Proper error messages for 400/404/409/500

**Gaps**:
- ❌ PAT validation (stored but never validated)
- ❌ Path traversal guard for root_hint (mentioned in plan, not implemented)
- ❌ Rate limiting middleware (mentioned in plan, not implemented)

---

### API-006: Authentication & Security ❌ STUB

**Status**: PLACEHOLDER, NO AUTHENTICATION
**Location**: Every endpoint has `# TODO - Add authentication when multi-user support is implemented`

**Not Implemented**:
- ❌ Clerk integration
- ❌ User isolation (all users see all sources)
- ❌ PAT encryption (stored in plaintext, never used)
- ❌ Input sanitization for root_hint

**Current State**: Single-user mode, assumes all operations are for one user.

---

### API-007: Background Job Integration ❌ NOT IMPLEMENTED

**Status**: NOT IMPLEMENTED
**Location**: Line 477 notes "This operation is currently synchronous"

**Not Implemented**:
- ❌ Celery / APScheduler integration
- ❌ Async scan jobs
- ❌ Job status polling endpoint
- ❌ Timeout handling for long scans
- ❌ 202 Accepted response (plan says return immediately, but still blocking)

**Current Behavior**: Scan blocks request thread until completion (can timeout on large repos).

---

## Integration Gap Analysis

### Gap 1: Heuristic Detector Disconnected from Scanner ⚠️ CRITICAL

**Impact**: All scans return 0 artifacts

**Root Cause**: Commented-out import in `github_scanner.py` (lines 30-34)

```python
# NOTE: This import will be available once SVC-002 (heuristic detector) is implemented
# from skillmeat.core.marketplace.heuristic_detector import (
#     HeuristicDetector,
#     detect_artifacts_in_tree,
# )
```

**Evidence**:
- Heuristic detector exists: ✅ `skillmeat/core/marketplace/heuristic_detector.py` (489 lines)
- Detector is functional: ✅ Has test case with 5 sample artifacts
- Detector is never called: ❌ All calls commented out in `github_scanner.py` (lines 161-167, 464-471)
- Result: Scan returns `artifacts_found=0` (line 170)

**Fix Required**: Uncomment import, enable `detect_artifacts_in_tree()` call.

---

### Gap 2: Catalog Diff Engine Unused, Replace Strategy Only ⚠️ CRITICAL

**Impact**: Incremental updates not working, all catalog entries replaced every scan

**Root Cause**: TODO comment in marketplace_sources.py line 545

```python
# TODO: Use diff engine for incremental updates
# Currently heuristic detector returns empty list, so this is a placeholder
new_entries: List[MarketplaceCatalogEntry] = []
ctx.replace_catalog_entries(new_entries)
```

**Evidence**:
- Diff engine exists: ✅ `skillmeat/core/marketplace/diff_engine.py` (334 lines)
- Diff engine is functional: ✅ Has test case with 4 change types
- Diff engine is never called: ❌ No `compute_diff()` call in scan path
- Result: Every scan wipes catalog (unless artifacts are empty, then it's unnoticed)

**Fix Required**:
1. Get existing entries from DB
2. Call `engine.compute_diff(existing, new_artifacts, source_id)`
3. Apply diff (create new, update changed, mark removed)

---

### Gap 3: README Link Harvester Orphaned ⚠️ MEDIUM

**Impact**: No secondary repository discovery, single-source-only implementation

**Root Cause**: No integration point in scan pipeline

**Evidence**:
- Harvester exists: ✅ `skillmeat/core/marketplace/link_harvester.py` (309 lines)
- Harvester is functional: ✅ Has test case with confidence scoring
- Harvester is never called: ❌ No integration in `GitHubScanner`
- Result: Manifest mentions "enqueue secondary scans", plan but never implemented

**Current State**: Harvester is production-ready but has no caller.

**Fix Required**:
1. After successful scan, fetch README if present
2. Call `harvester.harvest_links(readme_content, source_url)`
3. Enqueue secondary scans for discovered repos (depth=1 only per plan)

---

### Gap 4: Background Jobs Not Implemented ⚠️ MEDIUM

**Impact**: Scans block request thread, large repos can timeout API

**Root Cause**: No job queue infrastructure wired up

**Evidence**:
- Plan requires: ✅ Celery/APScheduler integration (Phase 4, task API-007)
- Code mentions: ✅ "asynchronous background jobs" (line 476)
- Actual implementation: ❌ Synchronous, blocking rescan_source()

**Fix Required**:
1. Create Celery task for `scan_repository()`
2. Return 202 Accepted immediately with job_id
3. Create status polling endpoint: `GET /marketplace/sources/{id}/rescan/{job_id}`

---

### Gap 5: Authentication Stubbed Out ⚠️ MEDIUM

**Impact**: No user isolation, all sources visible to all users

**Root Cause**: Multi-user support not yet implemented

**Evidence**:
- Plan requires: ✅ Clerk integration (Phase 4, task API-006)
- Code has TODOs: ✅ Every endpoint marked "TODO - Add authentication"
- Actual implementation: ❌ No auth checks, no user context
- PAT storage: ❌ Stored but never validated, not encrypted

**Fix Required**:
1. Add Clerk token validation middleware
2. Extract user context for each operation
3. Filter sources by user_id in all queries
4. Add encrypt/decrypt for PAT storage

---

### Gap 6: Import Coordinator Missing File Downloads ⚠️ LOW

**Impact**: Import marks entries as success without downloading artifacts

**Root Cause**: Placeholder comment (lines 216-220 in import_coordinator.py)

```python
# In a full implementation, this would:
# 1. Download artifact files from upstream_url
# 2. Write to local_path
# 3. Update manifest
entry.status = ImportStatus.SUCCESS
```

**Evidence**:
- Coordinator structure: ✅ Conflict detection working
- Coordinator logic: ✅ Path computation working
- Missing: ❌ Actual download + file write (marked SUCCESS without action)

**Fix Required**:
1. Fetch artifact from upstream_url (or use API to download)
2. Write to local_path
3. Update manifest.toml with artifact entry
4. Mark as success only after successful write

---

## Detailed Gap Breakdown by Task

| Task ID | Task Name | Planned | Implemented | Working | Notes |
|---------|-----------|---------|-------------|---------|-------|
| SVC-001 | DTOs & Models | ✅ | ✅ | ✅ | Complete |
| SVC-002 | Heuristic Detector | ✅ | ✅ | ❌ | Implemented but disconnected |
| SVC-003 | GitHub Scanning | ✅ | ✅ | ⚠️ | Returns 0 artifacts (detector not called) |
| SVC-004 | README Harvester | ✅ | ✅ | ❌ | Implemented but unused |
| SVC-005 | Catalog Diff Engine | ✅ | ✅ | ❌ | Implemented but unused (replace strategy only) |
| SVC-006 | Import Coordinator | ✅ | ✅ | ⚠️ | Structure works, file downloads missing |
| SVC-007 | Error Handling | ✅ | ✅ | ✅ | Complete with observability |
| API-001 | Sources Router | ✅ | ✅ | ✅ | All CRUD endpoints working |
| API-002 | Rescan Endpoint | ✅ | ✅ | ❌ | Endpoint exists, returns 0 artifacts |
| API-003 | Artifacts Listing | ✅ | ✅ | ✅ | Works (lists empty catalogs) |
| API-004 | Import Endpoint | ✅ | ✅ | ⚠️ | Works for empty catalogs, downloads missing |
| API-005 | Error & Validation | ✅ | ✅ | ⚠️ | Most validation present, PAT/path guards missing |
| API-006 | Auth & Security | ✅ | ❌ | ❌ | Completely stubbed, no implementation |
| API-007 | Background Jobs | ✅ | ❌ | ❌ | Not implemented, scans are synchronous |

---

## Critical Path to MVP

To achieve **minimum viable product** (one successful end-to-end scan → import):

### Priority 1: Enable Heuristic Detection (30 min) 🔴
1. Uncomment import in `github_scanner.py` line 30-34
2. Uncomment detector initialization line 101
3. Uncomment `detect_artifacts_in_tree()` call line 161-167, 464-471
4. **Result**: Scans will return detected artifacts

### Priority 2: Use Diff Engine (1 hour) 🔴
1. Fetch existing catalog entries in `rescan_source()`
2. Call `CatalogDiffEngine.compute_diff()` with existing + new
3. Update catalog entries using diff results (not replace)
4. **Result**: Incremental updates working

### Priority 3: Import File Downloads (2 hours) 🔴
1. Implement artifact download in `ImportCoordinator._process_entry()`
2. Use GitHub API or direct URL fetch to download artifact
3. Write to computed local_path
4. Update manifest.toml
5. **Result**: Imports actually persist artifacts

### Optional: Secondary Features (not required for MVP)
- Background jobs (nice-to-have for large repos)
- Authentication (blocks multi-user)
- README harvesting (secondary discovery)

---

## Summary of Findings

**Implementation Completeness**: 85% (code exists for all components)
**Functional Completeness**: 35% (major integrations missing)
**Blockers for MVP**:
1. ❌ Heuristic detector disconnected (causes 0 artifacts)
2. ❌ Diff engine unused (missing incremental updates)
3. ❌ Import downloads missing (artifacts not persisted)

**Not Blocking MVP**:
- ⚠️ Background jobs (can be synchronous initially)
- ⚠️ Authentication (single-user mode acceptable)
- ⚠️ README harvesting (advanced feature)

**Recommendation**: Focus on Priority 1-3 above to unlock end-to-end flow. All code exists; just needs to be wired together.

