# GitHub Ingestion Test Coverage Inventory - Phase 6

**Date**: 2025-12-08
**Status**: Exploration Complete
**Purpose**: Comprehensive inventory of existing tests vs implementation files needing tests

---

## Executive Summary

**Total Implementation Files**: 10
**Files with Tests**: 2
**Test Coverage**: 20%

The GitHub ingestion feature has foundational tests for heuristic detection and diff engine, but significant coverage gaps exist for:
- GitHub scanner and API interaction
- Link harvester (README parsing)
- Import coordinator (collection integration)
- API router endpoints
- Web UI components (sources, imports)
- E2E user flows

---

## Backend Implementation Files

### Core Marketplace Services

#### 1. Heuristic Detector
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/heuristic_detector.py`

**Key Functions/Classes**:
- `HeuristicDetector` - Multi-signal scoring for artifact detection
- `DetectionConfig` - Configuration for detection heuristics
- `ArtifactType` enum - Skill, command, agent, mcp_server, hook
- `analyze_paths()` - Main detection method
- `detect_artifact_type()` - Single path detection
- `matches_to_artifacts()` - Convert matches to artifacts
- `detect_artifacts_in_tree()` - Convenience function

**Lines of Code**: 529
**Complexity**: Medium (4 nested scoring methods + recursion)
**Test File**: `/Users/miethe/dev/homelab/development/skillmeat/tests/core/marketplace/test_heuristic_detector.py`
**Test Status**: COMPLETE ✓

**Test Coverage**: 206 lines of tests
- Test detection of all artifact types (skill, command, agent, mcp_server)
- Test manifest file detection
- Test directory name patterns
- Test depth penalty calculations
- Test root hint filtering
- Test multiple artifact types in single scan
- Test upstream URL generation
- Test confidence score breakdown
- Test custom configuration
- Test deduplication
- Test match reasons population

**Estimated Coverage**: 85% (all critical paths covered)

---

#### 2. Diff Engine
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/diff_engine.py`

**Key Functions/Classes**:
- `CatalogDiffEngine` - Compare old vs new catalog states
- `ChangeType` enum - new, updated, removed, unchanged
- `DiffEntry` - Single change entry
- `DiffResult` - Collection of changes
- `compute_diff()` - Main diff computation
- `_artifact_to_dict()` - Convert artifact to DB dict

**Lines of Code**: 334
**Complexity**: Medium (URL-based matching, SHA comparison)
**Test File**: `/Users/miethe/dev/homelab/development/skillmeat/tests/core/marketplace/test_diff_engine.py`
**Test Status**: COMPLETE ✓

**Test Coverage**: 495 lines of tests
- Test all new entries detection
- Test all removed entries detection
- Test all unchanged entries
- Test updated entries with SHA changes
- Test mixed changes (new + updated + removed + unchanged)
- Test empty SHA handling
- Test new_data dict includes source_id
- Test conversion to CatalogDiff
- Test DiffEntry change types
- Test DiffResult summary counts
- Test convenience function

**Estimated Coverage**: 90% (excellent edge case coverage)

---

#### 3. GitHub Scanner
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/github_scanner.py`

**Key Functions/Classes**:
- `GitHubScanner` - Main scanner service
- `ScanConfig` - Configuration for scanning
- `GitHubAPIError` - Custom error
- `RateLimitError` - Rate limit exception
- `scan_repository()` - Main scan method
- `_fetch_tree()` - Fetch repo file tree via GitHub API
- `_extract_file_paths()` - Filter tree to file paths
- `_get_ref_sha()` - Get commit SHA for reference
- `_request_with_retry()` - HTTP request with retry logic
- `get_file_content()` - Fetch specific file content
- `scan_github_source()` - Convenience function

**Lines of Code**: 437
**Complexity**: High (async GitHub API, rate limiting, retry logic)
**Test File**: NONE - NEEDS TESTS

**Functions Needing Tests**:
- `scan_repository()` - Main entry point
- `_fetch_tree()` - Tree fetching with pagination
- `_extract_file_paths()` - Path filtering logic
- `_get_ref_sha()` - SHA resolution
- `_request_with_retry()` - Retry logic and rate limit handling
- `get_file_content()` - File content fetching
- Error handling (GitHubAPIError, RateLimitError)
- Token authentication
- Rate limit handling
- Timeout handling
- Max files truncation

**Test Scope**: ~15-20 tests needed
**Priority**: HIGH

---

#### 4. Link Harvester
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/link_harvester.py`

**Key Functions/Classes**:
- `ReadmeLinkHarvester` - Extract GitHub links from README
- `HarvestConfig` - Configuration for harvesting
- `HarvestedLink` - Discovered link data class
- `harvest_links()` - Main harvesting method
- `_process_url()` - Process individual URL
- `_normalize_url()` - Normalize GitHub URL
- `_parse_github_url()` - Parse owner/repo from URL
- `_calculate_confidence()` - Confidence scoring based on context
- `reset_visited()` - Clear visited set
- `add_visited()` - Pre-seed visited URLs
- `harvest_readme_links()` - Convenience function

**Lines of Code**: 309
**Complexity**: Medium (regex patterns, confidence scoring)
**Test File**: NONE - NEEDS TESTS

**Functions Needing Tests**:
- `harvest_links()` - Main extraction
- `_process_url()` - URL processing pipeline
- `_normalize_url()` - URL normalization (with/without scheme, .git suffix)
- `_parse_github_url()` - Owner/repo parsing
- `_calculate_confidence()` - Confidence based on keywords and org
- Ignore patterns (issues, pulls, wiki, etc.)
- Artifact keywords matching
- Trusted organization bonus
- Cycle protection (visited tracking)
- Max depth handling

**Test Scope**: ~12-15 tests needed
**Priority**: HIGH

---

#### 5. Import Coordinator
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/import_coordinator.py`

**Key Functions/Classes**:
- `ImportCoordinator` - Coordinate imports from catalog
- `ImportStatus` enum - pending, success, skipped, conflict, error
- `ConflictStrategy` enum - skip, overwrite, rename
- `ImportEntry` - Single entry in import
- `ImportResult` - Result of import operation
- `import_entries()` - Main import method
- `_process_entry()` - Process single entry
- `_get_existing_artifacts()` - Get existing artifacts in collection
- `_compute_local_path()` - Compute target path
- `check_conflicts()` - Check for conflicts without importing
- `import_from_catalog()` - Convenience function

**Lines of Code**: 394
**Complexity**: Medium (conflict detection, path computation, strategy application)
**Test File**: NONE - NEEDS TESTS

**Functions Needing Tests**:
- `import_entries()` - Main entry point with strategy
- `_process_entry()` - Entry processing with all strategies
- `_get_existing_artifacts()` - Artifact discovery (old and new structure)
- `_compute_local_path()` - Path computation (old vs new structure)
- `check_conflicts()` - Conflict detection without side effects
- Conflict strategies (skip, overwrite, rename)
- Local path generation
- Collection directory structure handling
- Artifact type pluralization
- Error handling and status tracking

**Test Scope**: ~13-15 tests needed
**Priority**: HIGH

---

#### 6. Observability Module
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/observability.py`

**Lines of Code**: ~100 (not fully examined)
**Test File**: NONE - NEEDS TESTS

**Priority**: MEDIUM (logging/monitoring)

---

### API Layer

#### 7. Marketplace Sources Router
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/marketplace_sources.py`

**Key Functions**:
- `parse_repo_url()` - Parse GitHub URL
- `source_to_response()` - ORM to DTO conversion
- `POST /marketplace/sources` - Create source
- `GET /marketplace/sources` - List sources (paginated)
- `GET /marketplace/sources/{id}` - Get source by ID
- `PATCH /marketplace/sources/{id}` - Update source
- `DELETE /marketplace/sources/{id}` - Delete source
- `POST /marketplace/sources/{id}/rescan` - Trigger rescan
- `GET /marketplace/sources/{id}/artifacts` - List artifacts with filters
- `POST /marketplace/sources/{id}/import` - Import artifacts

**Lines of Code**: 100+ (partial read)
**Complexity**: High (database operations, transaction handling)
**Test File**: NONE - NEEDS TESTS

**Endpoints Needing Tests**:
- Create source (validation, URL parsing)
- List sources (pagination, filtering)
- Get source details
- Update source
- Delete source
- Trigger rescan (async)
- List artifacts (filtering, pagination)
- Import artifacts (conflict handling)
- Error cases (not found, invalid URL, etc.)

**Test Scope**: ~15-18 tests needed
**Priority**: HIGH

---

#### 8. Marketplace Router (Main)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/marketplace.py`

**Test File**: `/Users/miethe/dev/homelab/development/skillmeat/tests/api/test_marketplace_router.py`
**Test Status**: PARTIAL ✓

**Test Coverage**: 489 lines of tests covering:
- List listings (success, filters, pagination, caching)
- Get listing detail
- Install listing (success, broker not found, validation)
- Publish bundle (success, not found, broker error)
- List brokers (enabled/disabled)
- Broker selection
- ETag caching

**Estimated Coverage**: 75% (good coverage but missing some edge cases)

**Potential Gaps**:
- Error handling for network failures
- Rate limiting behavior
- Long-running operations (async)
- Concurrent installs

---

### Web Frontend Components

#### 9. Add Source Modal
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/marketplace/add-source-modal.tsx`

**Key Functions**:
- `AddSourceModal` - Multi-step form for adding GitHub source
- Form state management (repo URL, ref, root hint, trust level)
- Form submission and error handling
- URL validation

**Lines of Code**: 80+ (partial read)
**Complexity**: Medium (form state, async submission)
**Test File**: NONE - NEEDS TESTS

**Tests Needed**:
- Modal opens/closes
- Form fields render (repo URL, ref, root hint, trust level)
- URL validation (valid/invalid formats)
- Form submission
- Success callback
- Error handling
- Form reset after submission
- Loading state during submission

**Test Scope**: ~8-10 tests needed
**Priority**: MEDIUM

---

#### 10. Source Card Component
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/marketplace/source-card.tsx`

**Key Functions**:
- `SourceCard` - Display GitHub source with stats
- `TrustBadge` - Trust level badge (untrusted, basic, verified, official)
- Status indicator (scanning, error, success)
- Quick action buttons (rescan, view details)
- Artifact count display

**Lines of Code**: 80+ (partial read)
**Complexity**: Low-Medium (presentational component)
**Test File**: NONE - NEEDS TESTS

**Tests Needed**:
- Renders source information (name, URL, artifact count)
- Trust badge displays with correct level
- Status indicator updates (scanning, error, success)
- Action buttons appear (rescan, details)
- Rescan trigger
- Navigation to source details
- Trust level tooltips
- Artifact count display

**Test Scope**: ~8-10 tests needed
**Priority**: MEDIUM

---

#### 11. Other Components
- `MarketplaceFilters` - Partially tested (3 tests shown)
- `MarketplaceInstallDialog` - Test file exists but content not examined
- `MarketplaceListingCard` - Test file exists but content not examined

**Status**: Need full review

---

## Summary by Category

### Backend (Python)

| Module | Status | Test File | Coverage | Tests | Priority |
|--------|--------|-----------|----------|-------|----------|
| Heuristic Detector | Complete | ✓ exists | 85% | 14 | - |
| Diff Engine | Complete | ✓ exists | 90% | 19 | - |
| GitHub Scanner | Incomplete | MISSING | 0% | 0 | HIGH |
| Link Harvester | Incomplete | MISSING | 0% | 0 | HIGH |
| Import Coordinator | Incomplete | MISSING | 0% | 0 | HIGH |
| Marketplace Sources Router | Incomplete | MISSING | 0% | 0 | HIGH |
| Marketplace Router (Main) | Partial | ✓ exists | 75% | 17 | - |
| Observability | Unknown | MISSING | 0% | 0 | MEDIUM |

**Backend Summary**:
- 2 complete modules with comprehensive tests (375 tests total)
- 4 modules with NO tests (40-45 tests needed)
- 1 partial module (needs enhancement)

---

### Frontend (React/TypeScript)

| Component | Status | Test File | Coverage | Tests | Priority |
|-----------|--------|-----------|----------|-------|----------|
| Add Source Modal | Incomplete | MISSING | 0% | 0 | MEDIUM |
| Source Card | Incomplete | MISSING | 0% | 0 | MEDIUM |
| Filters | Partial | ✓ exists | 40% | ? | - |
| Install Dialog | Partial | ✓ exists | ? | ? | - |
| Listing Card | Partial | ✓ exists | ? | ? | - |

**Frontend Summary**:
- 3 components with existing tests (partial coverage)
- 2 components with NO tests (16-20 tests needed)
- Need full E2E flow tests (8-10 tests)

---

### E2E Tests

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/tests/e2e/marketplace.spec.ts`

**Existing Tests**:
- Displays marketplace page
- Filters by search query
- Filters by tags
- Clears all filters

**Status**: Basic coverage only
**Needs**:
- Source management flow (add, view, rescan)
- Import flow (select artifacts, handle conflicts)
- Error scenarios
- Navigation between views

---

## Test File Locations

### Existing Tests

**Backend Tests**:
- `/Users/miethe/dev/homelab/development/skillmeat/tests/core/marketplace/test_heuristic_detector.py` - 206 lines
- `/Users/miethe/dev/homelab/development/skillmeat/tests/core/marketplace/test_diff_engine.py` - 495 lines
- `/Users/miethe/dev/homelab/development/skillmeat/tests/api/test_marketplace_router.py` - 489 lines
- `/Users/miethe/dev/homelab/development/skillmeat/tests/unit/test_github_source.py` - exists
- `/Users/miethe/dev/homelab/development/skillmeat/tests/marketplace/test_security_scanner.py` - exists

**Frontend Tests**:
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/__tests__/marketplace/MarketplaceFilters.test.tsx`
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/__tests__/marketplace/MarketplaceInstallDialog.test.tsx`
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/__tests__/marketplace/MarketplaceListingCard.test.tsx`

**E2E Tests**:
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/tests/e2e/marketplace.spec.ts`

---

## Test Gap Analysis

### Critical Gaps (Phase 6 Blockers)

1. **GitHub Scanner Tests** (HIGH)
   - No tests for API interaction
   - No tests for rate limiting
   - No tests for retry logic
   - No tests for authentication
   - **Impact**: Core functionality not validated

2. **Link Harvester Tests** (HIGH)
   - No tests for URL extraction
   - No tests for confidence scoring
   - No tests for cycle protection
   - **Impact**: Secondary discovery not validated

3. **Import Coordinator Tests** (HIGH)
   - No tests for conflict detection
   - No tests for strategy application
   - No tests for path computation
   - **Impact**: User-facing import functionality not validated

4. **Marketplace Sources Router Tests** (HIGH)
   - No tests for endpoints
   - No tests for database integration
   - No tests for pagination
   - **Impact**: API layer not tested

### Medium Priority Gaps

5. **Add Source Modal Tests** (MEDIUM)
   - No tests for form handling
   - No tests for validation
   - **Impact**: User cannot create sources without tests

6. **Source Card Tests** (MEDIUM)
   - No tests for rendering
   - No tests for interactions
   - **Impact**: Source list display untested

7. **E2E Flow Tests** (MEDIUM)
   - No complete user workflows
   - No error scenario testing
   - **Impact**: Integration not validated

---

## Recommendations for Phase 6

### Immediate (High Priority)

1. **Create `tests/core/marketplace/test_github_scanner.py`**
   - ~18-20 tests covering all public methods
   - Mock GitHub API responses
   - Test rate limiting, retry logic, errors
   - Estimated time: 4-5 hours

2. **Create `tests/core/marketplace/test_link_harvester.py`**
   - ~12-15 tests for link extraction
   - Test confidence scoring
   - Test ignore patterns and cycle protection
   - Estimated time: 3-4 hours

3. **Create `tests/core/marketplace/test_import_coordinator.py`**
   - ~13-15 tests for import logic
   - Test all conflict strategies
   - Test path computation
   - Estimated time: 3-4 hours

4. **Create `tests/api/test_marketplace_sources.py`**
   - ~15-18 tests for API endpoints
   - Mock database layer
   - Test pagination and filtering
   - Estimated time: 4-5 hours

### Secondary (Medium Priority)

5. **Create web component tests**
   - `__tests__/marketplace/AddSourceModal.test.tsx` (~8-10 tests)
   - `__tests__/marketplace/SourceCard.test.tsx` (~8-10 tests)
   - Estimated time: 3-4 hours

6. **Enhance E2E tests**
   - Add source management flow
   - Add import workflow
   - Add error scenarios
   - Estimated time: 3-4 hours

---

## Test Infrastructure Needs

### Backend

- **Fixtures**: GitHub API response mocks, database fixtures
- **Utilities**: Test database setup/teardown, mock builders
- **Databases**: SQLite for tests (if using ORM)

### Frontend

- **Fixtures**: Mock API responses, mock data builders
- **Utilities**: Render helpers, query builders
- **Environment**: jsdom configured, API mocks with MSW

---

## Coverage Goals for Phase 6

| Category | Current | Target | Gap |
|----------|---------|--------|-----|
| Backend Unit | 60% | 85% | 25% |
| Backend Integration | 40% | 70% | 30% |
| Frontend Unit | 40% | 75% | 35% |
| E2E | 10% | 50% | 40% |
| **Overall** | **40%** | **70%** | **30%** |

---

## Testing Checklist for Phase 6

- [ ] GitHub Scanner unit tests (20 tests)
- [ ] Link Harvester unit tests (15 tests)
- [ ] Import Coordinator unit tests (15 tests)
- [ ] Marketplace Sources Router tests (18 tests)
- [ ] Add Source Modal component tests (10 tests)
- [ ] Source Card component tests (10 tests)
- [ ] E2E source management flow (8 tests)
- [ ] E2E import workflow (10 tests)
- [ ] Error scenario tests (8 tests)
- [ ] Performance tests (if applicable)
- [ ] Integration tests for full flow (5 tests)

**Total Tests to Create**: ~119 tests
**Estimated Effort**: 25-30 hours
**Target Coverage**: 70% overall

