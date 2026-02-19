---
title: 'PRD: Marketplace Source Detection Improvements'
description: 'Two enhancements to marketplace source detection: manual directory mapping
  for non-skill artifacts and post-detection deduplication using content hashing'
audience:
- ai-agents
- developers
- product-managers
tags:
- prd
- marketplace
- detection
- deduplication
- artifact-types
created: 2026-01-05
updated: '2026-02-07'
category: product-planning
status: completed
related:
- /docs/project_plans/PRDs/features/marketplace-github-ingestion-v1.md
- /docs/project_plans/bugs/marketplace-sources-non_skills-v1.md
- /docs/project_plans/implementation_plans/features/marketplace-sources-crud-enhancement-v1.md
schema_version: 2
doc_type: prd
feature_slug: marketplace-source-detection-improvements
---

# PRD: Marketplace Source Detection Improvements

**Feature Name:** Marketplace Source Detection Improvements

**Filepath Name:** `marketplace-source-detection-improvements-v1`

**Date:** 2026-01-05

**Author:** Claude Code (AI Agent)

**Version:** 1.0

**Status:** Draft

**Priority:** HIGH

**Related Documents:**
- Marketplace GitHub Ingestion PRD (v1.0)
- Marketplace Sources Non-Skills Bug Report (2025-12-31)
- Artifact Type System (in `skillmeat/core/artifact.py`)

---

## 1. Executive Summary

This PRD addresses two critical limitations in the marketplace source detection system:

1. **Manual Source Mapping (REQ-20260104-skillmeat-01):** Enable users to manually map directories to artifact types (commands, agents, mcp_server, hook) when heuristic detection fails or is inaccurate.

2. **Auto-detection De-duplication (REQ-20260104-skillmeat-02):** Eliminate duplicate artifacts detected within a source or matching existing collection entries using SHA256 content hashing.

These enhancements improve detection accuracy for non-skill artifacts and reduce false positives, directly addressing the current limitation where only skills are reliably detected while commands, agents, and other types are misclassified.

**Key Outcomes:**
- Users can explicitly map directories to artifact types, bypassing heuristic limitations
- Duplicate artifacts are automatically deduplicated post-detection
- Scan results are more accurate and actionable
- User experience in marketplace source detail pages is improved with visual feedback and mapping UI

---

## 2. Context & Background

### Current State

**What Exists Today:**

1. **Detection System** (in `skillmeat/core/marketplace/`):
   - `github_scanner.py` - GitHub API scanning and tree traversal
   - `heuristic_detector.py` - Confidence scoring (0-100) based on directory/file patterns
   - `diff_engine.py` - Status tracking (new/updated/removed) by comparing scans
   - `import_coordinator.py` - Import orchestration and conflict resolution

2. **Database Models** (in `skillmeat/cache/models.py`):
   - `MarketplaceSource` (Line 1173):
     - `id`, `repo_url`, `owner`, `repo_name`, `ref`, `root_hint`
     - `manual_map` - JSON field for manual overrides (exists but not fully utilized)
     - `trust_level`, `visibility`, `scan_status`, `artifact_count`
     - `last_sync_at`, `last_error`, `created_at`, `updated_at`
   - `MarketplaceCatalogEntry` (Line 1368):
     - `id`, `source_id`, `artifact_type`, `name`, `path`, `upstream_url`
     - `detected_version`, `detected_sha`, `detected_at`
     - `confidence_score` (0-100), `raw_score`, `score_breakdown`
     - `status` (new/updated/removed/imported)
     - `excluded_at`, `excluded_reason` - For "not an artifact" flow

3. **API & Frontend**:
   - API Router: `skillmeat/api/routers/marketplace_sources.py` (21 endpoints)
   - Frontend: Source Detail at `/marketplace/sources/[id]`
   - Toolbar: `source-toolbar.tsx` (where Map Directories button will go)
   - Types: `skillmeat/web/types/marketplace.ts`
   - Hooks: `useSource()`, `useSourceCatalog()`, `useRescanSource()`

4. **Supported Artifact Types** (from `skillmeat/core/artifact.py`):
   - `skill`
   - `command`
   - `agent`
   - `mcp_server`
   - `hook`

5. **Detection Heuristics** (baseline):
   - Directory hints: `.claude/skills`, `skills/`, `agents/`, `commands/`, `tools/`, `plugins/`, `mcp/`, `mcp-servers/`, `hooks/`
   - File hints: `skill*.md|yaml`, `manifest.(json|yaml|toml)`
   - Scoring: dir-name match + manifest presence + extension + depth penalty
   - Storage: `confidence_score` in catalog entries

6. **Exclusion Flow** (existing):
   - Users can mark entries as "not an artifact" via PATCH endpoint
   - Sets `excluded_at` timestamp and `excluded_reason`
   - Entries remain in DB but hidden from UI when `excluded_at IS NOT NULL`

### Problem Space

**Enhancement 1: Non-Skill Detection Gaps**

**Pain Points:**
1. **Misclassification:** Commands and agents in directories without obvious naming conventions (e.g., `cmd/`, `bots/`) are misclassified as skills or missed entirely.
2. **Directory Structure Variance:** Source repos may use custom directory layouts not matching heuristic patterns (e.g., nested plugins, monorepos with mixed types).
3. **No Manual Override:** When heuristics fail, users must either:
   - Re-scan after manual repository modification (not allowed)
   - Exclude false positives one-by-one (tedious)
   - Accept poor detection results

4. **Evidence:**
   - Bug report (2025-12-31): "Commands in `commands/` directory detected as skills"
   - Directories like `commands/git`, `commands/dev` are parsed as individual skills rather than containers of commands
   - Only skill detection is reliable; other types require manual intervention

**Enhancement 2: Duplicate Artifacts**

**Pain Points:**
1. **Within Same Source:** If a repository contains the same artifact in multiple locations or under different directory structures, both will be detected, creating duplicates in the catalog.
2. **Across Sources:** If the same artifact exists in multiple marketplace sources, the catalog will contain multiple entries pointing to different repositories.
3. **Collection Conflicts:** When importing, users encounter the same artifact multiple times, creating choice paralysis and potential import conflicts.
4. **No Deduplication Logic:** Current system has no mechanism to identify duplicate artifacts (same content, different location/source).

### Current Alternatives / Workarounds

**Enhancement 1 Workarounds:**
- Manually edit source repository directory structure (not allowed by users)
- Contact maintainers to rename directories (slow, external dependency)
- Use heuristic-based fallback and accept lower accuracy
- Manually create artifact entries (not scalable)

**Enhancement 2 Workarounds:**
- Manually inspect catalog and mark duplicates as excluded (tedious, error-prone)
- Users must manage deduplication during import (cognitive overhead)
- No systematic way to handle cross-source duplicates

### Architectural Context

**Current Detection Flow:**

```
User adds source (repo URL, branch, root)
    → GitHub API scan (tree, file listing)
    → Heuristic detection (confidence scoring)
    → Catalog entries created with status="new"
    → User views catalog, filters by type/status
    → User imports selected artifacts to collection
```

**Current Manual Mapping Capability (Incomplete):**

The `MarketplaceSource.manual_map` field exists as a JSON column but is:
- **Not exposed in UI** - No front-end form to edit it
- **Not enforced in detection** - Heuristic detector doesn't check/apply it
- **Not documented** - Schema unclear
- **Single read-only endpoint** - Cannot be updated via PATCH

**Goal: Complete the manual mapping implementation and add deduplication.**

---

## 3. Functional Requirements

### Enhancement 1: Manual Source Mapping (REQ-20260104-skillmeat-01)

#### 3.1.1 Map Directories Modal UI

**Location:** Source Detail page (`/marketplace/sources/{ID}`)

**Trigger:** "Map Directories" button in source-toolbar (new)

**Modal Features:**

1. **File Tree Component:**
   - Display all directories relative to (and including) Root Directory
   - Tree is read-only initially; user selects directories to map
   - Show path relative to root (e.g., `commands/`, `agents/`, `nested/tools/`)
   - Include directory counts: "(3 files)" to hint at content

2. **Artifact Type Selector:**
   - Dropdown menu next to each directory
   - Options: `skill`, `command`, `agent`, `mcp_server`, `hook`, `(none)`
   - Selecting `(none)` disables mapping for that directory

3. **Hierarchical Mapping Logic:**
   - When a directory is mapped, nested subdirectories inherit the mapping
   - Child directories can override parent mapping with explicit selection
   - Example:
     - Map `agents/` → `agent` type
     - Map `agents/llm/` → `mcp_server` type (override)
     - All other dirs under `agents/` use parent mapping (`agent`)

4. **Detection Integration:**
   - Mapping does **NOT** skip heuristic detection
   - Instead, detection now uses: **(1) Manual mapping (if exists) OR (2) Heuristic detection**
   - Within mapped directories, individual artifacts are still identified using heuristic rules (README detection, manifest files, etc.)
   - Non-artifact files (README.md, LICENSE, etc.) are skipped (existing logic)

5. **Persistence & Validation:**
   - Save mappings to `MarketplaceSource.manual_map` (JSON)
   - Schema:
     ```json
     {
       "mappings": [
         { "directory": "commands", "type": "command" },
         { "directory": "agents", "type": "agent" },
         { "directory": "agents/llm", "type": "mcp_server" }
       ]
     }
     ```
   - Validate:
     - Directory path must exist in repository
     - Type must be valid `ArtifactType` value
     - No circular or conflicting mappings
     - Max 100 mappings per source

6. **User Actions in Modal:**
   - **Save:** Persist mappings to DB; return to source detail
   - **Cancel:** Discard unsaved changes
   - **Rescan:** Save mappings and trigger rescan immediately
   - **Auto-Suggest (optional):** Based on directory names, suggest mappings (e.g., dir named `commands/` → suggest `command` type)

#### 3.1.2 Detection Logic Integration

**File:** `skillmeat/core/marketplace/heuristic_detector.py`

**Changes:**

1. **Signature Update:**
   ```python
   def detect_artifacts(
       scanner: GitHubScanner,
       root_path: str,
       manual_mappings: dict[str, str] | None = None,  # NEW: {directory -> artifact_type}
   ) -> list[ArtifactMetadata]:
       """
       Detect artifacts in repository.

       Args:
           scanner: GitHub API client
           root_path: Repository root or user-specified root_hint
           manual_mappings: User-provided directory -> artifact_type overrides
               Example: {"commands": "command", "agents/llm": "mcp_server"}

       Returns:
           List of detected artifacts with confidence scores
       """
   ```

2. **Detection Sequence (per directory):**
   ```
   For each directory in repository:
     1. Check manual_mappings for direct or parent directory match
     2. If match found:
        - Set artifact_type = mapped type
        - Set confidence_score = 95 (manual override confidence)
     3. Else:
        - Run heuristic detection (existing logic)
        - Set artifact_type and confidence_score per heuristics
     4. Scan contents of directory for individual artifacts
        - README, manifest files, nested subdirs
        - Apply heuristic rules per artifact within directory
   ```

3. **Confidence Scoring:**
   - Manual mappings: `confidence_score = 95` (high confidence for user-specified)
   - Parent directory match: `confidence_score = 90`
   - Heuristic match: `confidence_score = calculated per heuristics (0-100)`

#### 3.1.3 API Endpoint: Update Manual Mappings

**Endpoint:** `PATCH /marketplace/sources/{id}` (existing)

**New Request Field:**

```typescript
// In UpdateSourceRequest schema
interface UpdateSourceRequest {
  name?: string;
  description?: string;
  notes?: string;
  root_hint?: string;
  // NEW FIELD:
  manual_map?: {
    mappings: Array<{
      directory: string;      // e.g., "commands", "agents/llm"
      type: ArtifactType;     // "skill", "command", "agent", "mcp_server", "hook"
    }>;
  };
}
```

**Validation (in router):**
- Validate all directory paths exist in source repository (use GitHub API)
- Validate all types are valid `ArtifactType` enum values
- Validate no more than 100 mappings
- Return 400 Bad Request if validation fails

**Response:** Updated `SourceResponse` object

#### 3.1.4 Acceptance Criteria (Enhancement 1)

- [ ] **UI Modal Implemented:** "Map Directories" button visible on source detail page
- [ ] **File Tree Rendering:** Tree component displays all directories under root with depth indentation
- [ ] **Type Selector:** Dropdown shows all `ArtifactType` enum values; can select per directory
- [ ] **Hierarchical Mapping:** Child directories inherit parent mapping unless explicitly overridden
- [ ] **Save & Persist:** Mappings saved to `manual_map` JSON field; survives across page refreshes
- [ ] **API Integration:** PATCH endpoint accepts and validates manual_map field
- [ ] **Detection Integration:** Heuristic detector checks manual_mappings before running heuristics
- [ ] **Confidence Scoring:** Manual mappings generate confidence_score >= 90
- [ ] **Rescan with Mappings:** Triggering rescan after setting mappings applies them to new detection
- [ ] **E2E Test:** Create source, add manual mapping, rescan, verify mapped artifacts have correct type

---

### Enhancement 2: Auto-detection De-duplication (REQ-20260104-skillmeat-02)

#### 3.2.1 Content Hashing & Duplicate Detection

**Scope:** Post-detection deduplication (runs **AFTER** all detection and manual mapping)

**Algorithm:**

1. **Content Hash Computation:**
   - For each detected artifact (file or directory):
     - If single file: compute SHA256(file_content)
     - If directory with multiple files: compute SHA256(sorted JSON of {filename: SHA256(content)} for all files)
   - Store hash in `MarketplaceCatalogEntry.metadata_json` under key `"content_hash"`

2. **Deduplication Stages:**

   **Stage 1: Within Same Source**
   - Group artifacts by (source_id, artifact_type, content_hash)
   - For each group with 2+ entries:
     - Keep artifact with highest confidence_score
     - If tie: keep artifact with earliest file path (alphabetical order)
     - Mark other entries as duplicates (see exclusion logic below)

   **Stage 2: Across Sources (Matching Existing Collection)**
   - For each newly detected artifact:
     - Query collection artifacts with same type
     - Compare content_hash
     - If match found:
       - Mark new entry as duplicate (status, excluded reason)
       - Do NOT exclude silently; show user notification with count

3. **Exclusion Behavior (for duplicates):**
   - Create entries in `MarketplaceCatalogEntry` but set:
     - `excluded_at = NOW()`
     - `excluded_reason = "Duplicate: detected in [source_name] or collection"`
     - Optionally store duplicate group ID in `metadata_json` for tracing
   - These entries are hidden from UI (existing excluded_at logic)
   - Users can still restore them via "Restore Excluded" action if desired

#### 3.2.2 Deduplication Service Implementation

**File:** `skillmeat/core/marketplace/deduplication_engine.py` (new)

**Interface:**

```python
from dataclasses import dataclass

@dataclass
class DeduplicationResult:
    """Result of deduplication process."""
    total_detected: int
    duplicates_within_source: int
    duplicates_across_sources: int
    surviving_entries: list[ArtifactMetadata]
    excluded_entries: list[tuple[ArtifactMetadata, str]]  # (entry, reason)

class DeduplicationEngine:
    def __init__(self, storage_client, collection_manager):
        self.storage_client = storage_client
        self.collection_manager = collection_manager

    async def compute_content_hash(
        self,
        scanner: GitHubScanner,
        artifact: ArtifactMetadata
    ) -> str:
        """
        Compute SHA256 hash of artifact content.

        For single file: hash(file_content)
        For directory: hash(json of {file: hash(content)} for all files, sorted)
        """
        # Implementation uses GitHubScanner to fetch content
        # Caches hash in scanner's local cache

    async def deduplicate(
        self,
        source_id: str,
        detected_artifacts: list[ArtifactMetadata],
        scanner: GitHubScanner,
    ) -> DeduplicationResult:
        """
        Deduplicate detected artifacts.

        Returns:
            DeduplicationResult with surviving entries and excluded duplicates
        """
        # Stage 1: Within source deduplication
        # Stage 2: Cross-source deduplication
        # Return result
```

**Integration Point:**

In `import_coordinator.py` or `github_scanner.py`, add deduplication as final step:

```python
async def scan_github_source(source: MarketplaceSource, ...):
    # ... existing scan logic

    detected = await heuristic_detector.detect_artifacts(
        scanner, root_path, source.manual_map
    )

    # NEW: Deduplication step
    dedup_engine = DeduplicationEngine(storage, collection_mgr)
    dedup_result = await dedup_engine.deduplicate(
        source.id, detected, scanner
    )

    # Split results: surviving and excluded
    surviving_entries = dedup_result.surviving_entries
    excluded_entries = dedup_result.excluded_entries

    # Create catalog entries for all, mark excluded ones appropriately
    for entry in surviving_entries:
        create_catalog_entry(entry, excluded_at=None)

    for entry, reason in excluded_entries:
        create_catalog_entry(entry, excluded_at=NOW(), excluded_reason=reason)

    # Return scan result with dedup counts
    return ScanResult(
        total_detected=dedup_result.total_detected,
        duplicates_within_source=dedup_result.duplicates_within_source,
        duplicates_across_sources=dedup_result.duplicates_across_sources,
    )
```

#### 3.2.3 Notification & User Feedback

**Scan Completion Notification:**

When scan completes, notify user with summary:

```
Scan Complete: 42 artifacts detected
  ✓ 35 new/updated artifacts added to catalog
  ⚠ 4 duplicates within source (hidden)
  ⚠ 3 duplicates from collection (hidden)

View details → [Open Source Detail]
```

**Source Detail UI Updates:**

1. **Scan Result Summary** (in header):
   - Add row: "Duplicates Found: X within source, Y from collection"
   - Link to filter view of only non-excluded entries

2. **Artifact Cards:**
   - Existing excluded entries show badge: "Duplicate"
   - Tooltip: "This artifact is a duplicate. [View original]"

#### 3.2.4 API Changes

**ScanResultDTO (existing schema in `skillmeat/api/schemas/marketplace.py`):**

**New Response Field:**

```typescript
interface ScanResultDTO {
  source_id: string;
  status: "success" | "error";
  total_detected: number;
  // NEW FIELDS:
  duplicates_within_source: number;
  duplicates_across_sources: number;
  artifact_count_by_type: {
    [type: string]: number;  // After deduplication
  };
  message: string;  // Human-readable summary
}
```

**Endpoint:** POST `/marketplace/sources/{id}/rescan` returns updated `ScanResultDTO`

#### 3.2.5 Performance Considerations

**Challenges:**
- Computing SHA256 for all artifacts can be slow (large repos, many files)
- Comparing hashes across sources requires querying collection

**Solutions:**
1. **Lazy Hashing:** Compute content hash **only when needed**:
   - Hash immediately for potential duplicates (same name, type, path)
   - Defer full hash computation for clearly unique artifacts

2. **Batch Operations:** Use GitHub API tree endpoint to fetch file lists efficiently (already done)

3. **Caching:** Store computed hashes in `metadata_json` and `score_breakdown` to avoid recomputation on rescan

4. **Configurable Limits:** Add environment variable `MARKETPLACE_DEDUP_MAX_ARTIFACT_SIZE` (default 10MB) to skip hashing very large files

5. **Async Processing:** Run deduplication asynchronously if scan takes > 30s; notify user when complete

#### 3.2.6 Acceptance Criteria (Enhancement 2)

- [ ] **Hash Computation:** Content hashes computed for all detected artifacts
- [ ] **Within-Source Dedup:** Duplicates within same source correctly identified and marked excluded
- [ ] **Cross-Source Dedup:** Duplicates matching collection artifacts identified
- [ ] **Confidence-Based Dedup:** When multiple duplicates exist, highest-confidence artifact survives
- [ ] **Exclusion Marking:** Duplicate entries marked with excluded_at and excluded_reason
- [ ] **UI Feedback:** Scan result notification shows duplicate counts
- [ ] **Performance:** Deduplication completes in <2x the heuristic detection time
- [ ] **Hash Storage:** Content hashes persisted in metadata_json
- [ ] **Rescan Consistency:** Re-scanning same source produces same dedup results
- [ ] **E2E Test:** Create source with duplicate artifacts, verify dedup, check excluded entries

---

## 4. Non-Functional Requirements

| Requirement | Target | Rationale |
|-------------|--------|-----------|
| **Hash Algorithm** | SHA256 | Industry standard, collision-resistant, fast |
| **Max Mappings per Source** | 100 | Prevent abuse, reasonable for complex repos |
| **Dedup Max File Size** | 10MB | Avoid timeouts on huge binary files |
| **Confidence Threshold (excluded)** | < 30 | Existing threshold for hidden entries |
| **Manual Mapping Confidence** | >= 90 | User intent is strong signal |
| **Scan Timeout** | 120s | Prevent hanging on large repos (tunable) |
| **Backward Compatibility** | 100% | Existing sources without manual_map continue working |
| **Database Migration** | None required | Using existing manual_map column and metadata_json |
| **API Backward Compatibility** | 100% | New fields optional in requests, included in responses |

---

## 5. Implementation Plan

### Phase 1: Database & Schema (No DB Changes Required)

**Duration:** 1 day (mostly validation work)

**Tasks:**
1. Add validation schema for `manual_map` JSON structure
2. Add validation schema for `ScanResultDTO` with new dedup fields
3. Update `MarketplaceCatalogEntry` to document `metadata_json.content_hash` field
4. Write database migration checklist (no changes needed; existing columns sufficient)

**Deliverables:**
- Validation schemas in `skillmeat/api/schemas/marketplace.py`
- Documentation of `manual_map` and `metadata_json` formats
- Migration guide (for documentation)

**Acceptance Criteria:**
- [ ] Schemas compile without errors
- [ ] Existing catalog entries compatible with new field usage
- [ ] No downtime on deployment

---

### Phase 2: Backend Detection Engine (Manual Mapping + Deduplication)

**Duration:** 5-7 days

**Tasks:**

**2.1: Manual Mapping Integration**
- [ ] Add `manual_mappings` parameter to `heuristic_detector.detect_artifacts()`
- [ ] Implement directory matching logic (direct + parent matching)
- [ ] Implement hierarchical inheritance (child overrides parent)
- [ ] Set confidence_score = 95 for manual mappings
- [ ] Add unit tests for detection with manual mappings

**2.2: Content Hashing**
- [ ] Create `deduplication_engine.py` with `DeduplicationEngine` class
- [ ] Implement `compute_content_hash()` for single files
- [ ] Implement `compute_content_hash()` for directories
- [ ] Add hash caching in scanner
- [ ] Add configurable max file size check

**2.3: Deduplication Logic**
- [ ] Implement within-source deduplication (Stage 1)
- [ ] Implement across-source deduplication with collection lookup (Stage 2)
- [ ] Implement confidence-based tie-breaking
- [ ] Implement exclusion marking logic
- [ ] Add unit tests for all dedup scenarios

**2.4: Integration**
- [ ] Wire deduplication into `scan_github_source()` workflow
- [ ] Update `ScanResultDTO` with dedup counts
- [ ] Update scanner to return dedup statistics
- [ ] Add integration tests for full scan → dedup flow

**Deliverables:**
- `skillmeat/core/marketplace/heuristic_detector.py` (updated)
- `skillmeat/core/marketplace/deduplication_engine.py` (new)
- Updated detection integration in scanner
- Unit & integration tests (60%+ coverage)

**Acceptance Criteria:**
- [ ] All detection tests pass
- [ ] All dedup tests pass
- [ ] Manual mappings applied correctly in detection
- [ ] Deduplication correctly identifies and excludes duplicates
- [ ] Confidence scoring works as specified
- [ ] No performance regression on existing scans

---

### Phase 3: API & Backend Routes

**Duration:** 3-4 days

**Tasks:**

**3.1: Update PATCH Endpoint**
- [ ] Add `manual_map` field to `UpdateSourceRequest` schema
- [ ] Validate directory paths against source repository
- [ ] Validate artifact types
- [ ] Update route handler to accept and persist mappings
- [ ] Add error responses for invalid mappings

**3.2: Update GET Endpoint**
- [ ] Include `manual_map` in `SourceResponse` schema
- [ ] Document manual_map field in OpenAPI

**3.3: Update Rescan Endpoint**
- [ ] Pass `manual_map` from source to detection engine
- [ ] Return updated `ScanResultDTO` with dedup counts
- [ ] Update response schema in OpenAPI

**3.4: Tests**
- [ ] Test PATCH endpoint with valid/invalid mappings
- [ ] Test rescan with manual mappings applied
- [ ] Test API response formats

**Deliverables:**
- Updated `skillmeat/api/routers/marketplace_sources.py`
- Updated schemas in `skillmeat/api/schemas/marketplace.py`
- API integration tests
- Updated OpenAPI documentation

**Acceptance Criteria:**
- [ ] PATCH endpoint accepts and validates manual_map
- [ ] GET endpoint returns manual_map
- [ ] Rescan applies manual_map and returns dedup counts
- [ ] All API tests pass
- [ ] OpenAPI documentation accurate

---

### Phase 4: Frontend UI (Manual Mapping Modal + Dedup Display)

**Duration:** 5-7 days

**Tasks:**

**4.1: Modal Component**
- [ ] Create `DirectoryMapModal` component
- [ ] Implement file tree component showing directories
- [ ] Implement artifact type dropdown per directory
- [ ] Implement hierarchical mapping logic (inheritance + override)
- [ ] Add save/cancel/rescan actions
- [ ] Add form validation (max 100 mappings, valid paths)

**4.2: Toolbar Integration**
- [ ] Add "Map Directories" button to `source-toolbar.tsx`
- [ ] Wire button to open modal
- [ ] Add loading states during save/rescan

**4.3: Source Detail Updates**
- [ ] Display manual mappings in source metadata
- [ ] Show scan summary with dedup counts
- [ ] Add "Duplicate" badge to excluded entries in catalog view
- [ ] Add tooltip explaining duplicate reason
- [ ] Add link to filter view of excluded artifacts

**4.4: Notification System**
- [ ] Display scan completion toast with dedup summary
- [ ] Include link to source detail
- [ ] Handle long-running scans (async notification)

**4.5: Types & Hooks**
- [ ] Update `skillmeat/web/types/marketplace.ts` with `DirectoryMapping` type
- [ ] Create hook `useUpdateSourceMapping()` in hooks
- [ ] Update `useRescanSource()` to handle dedup counts

**4.6: Tests**
- [ ] Component tests for modal
- [ ] E2E tests for full mapping workflow
- [ ] Snapshot tests for UI components

**Deliverables:**
- `DirectoryMapModal.tsx` component
- Updated `source-toolbar.tsx`
- Updated source detail page
- Updated hooks and types
- Frontend tests (60%+ coverage)

**Acceptance Criteria:**
- [ ] Modal renders with directory tree
- [ ] Type selectors work (dropdown shows all types)
- [ ] Hierarchical mapping inheritance works
- [ ] Save persists mappings to backend
- [ ] Rescan shows dedup counts in notification
- [ ] UI shows duplicate badges on excluded entries
- [ ] All E2E tests pass
- [ ] No console errors or warnings

---

### Phase 5: Integration Testing & Deployment

**Duration:** 2-3 days

**Tasks:**

**5.1: Full Workflow Tests**
- [ ] Create source with manual mappings
- [ ] Trigger rescan, verify mappings applied
- [ ] Verify dedup detection works (within-source, cross-source)
- [ ] Import some artifacts, verify others marked as duplicates
- [ ] Restore excluded artifact, verify it's no longer hidden

**5.2: Edge Cases**
- [ ] Empty repository (no artifacts detected)
- [ ] Repository with all duplicates (all excluded except one)
- [ ] Large repository (>1000 artifacts)
- [ ] Deeply nested directory structure
- [ ] Circular mapping prevention (if applicable)

**5.3: Performance Testing**
- [ ] Measure scan time with/without deduplication
- [ ] Measure hash computation time vs detection time
- [ ] Verify no UI freezing during modal interaction

**5.4: Backward Compatibility**
- [ ] Existing sources without manual_map still scan correctly
- [ ] Existing catalog entries load without errors
- [ ] Rescan of source created before this feature works

**5.5: Documentation**
- [ ] User guide for manual mapping UI
- [ ] API documentation (manual_map field, dedup counts)
- [ ] Developer guide for detection engine changes

**5.6: Deployment**
- [ ] No database migrations needed (confirm)
- [ ] Deploy backend changes
- [ ] Deploy frontend changes
- [ ] Verify in staging environment
- [ ] Monitor error rates and performance in production

**Deliverables:**
- Integration test suite (fully automated)
- User documentation
- API documentation updates
- Deployment checklist

**Acceptance Criteria:**
- [ ] All integration tests pass
- [ ] Edge cases handled gracefully
- [ ] Performance acceptable (<2x existing scan time with dedup)
- [ ] No breaking changes to existing API
- [ ] Documentation complete
- [ ] Successful deployment to production

---

## 6. User Stories

| Story | User Role | Acceptance Criteria |
|-------|-----------|-------------------|
| **STORY-1.1** | Marketplace Admin | Given a source with misdetected artifacts, when I click "Map Directories" and map `commands/` → `command` type, then rescan shows correctly typed artifacts with high confidence |
| **STORY-1.2** | User | Given a mapped directory, when I add new files to that directory and rescan, then new artifacts in mapped directory use the mapped type automatically |
| **STORY-1.3** | User | Given a mapping for parent directory `agents/`, when I override with `agents/llm/` → `mcp_server`, then artifacts in `agents/llm/` use mcp_server type while other agents/ subdirs use agent type |
| **STORY-2.1** | User | Given a source with 3 identical skill artifacts in different locations, when I rescan, then only 1 (highest confidence) appears in catalog; others hidden as duplicates |
| **STORY-2.2** | User | Given an artifact in source that matches one in my collection, when I rescan, then matching artifact hidden with "Duplicate: detected in collection" reason |
| **STORY-2.3** | Marketplace Admin | Given a completed scan, when scan includes duplicates, then notification shows "4 duplicates within source, 2 from collection" with link to source detail |
| **STORY-2.4** | User | Given an excluded duplicate artifact, when I click "Restore Excluded" in source detail, then artifact appears in catalog and can be imported |

---

## 7. Edge Cases & Risks

### Edge Cases

1. **Empty Directories:**
   - Manual mapping to empty directory
   - **Handling:** Detect artifacts within empty directories (heuristics still apply); allow mapping without error

2. **Very Large Repositories (>10k files):**
   - Hash computation timeout
   - **Handling:** Set configurable timeout (default 120s); skip hashing if timeout reached; log warning

3. **Binary Files:**
   - Hashing very large binary files could be slow
   - **Handling:** Add max file size check (default 10MB); skip hash for oversized files

4. **Circular Mappings (if nested):**
   - User accidentally maps parent and child to different types
   - **Handling:** Child override takes precedence; not a true "circular" case; validate no directory maps to itself

5. **Re-running Dedup on Already-Excluded Entries:**
   - Dedup runs again on rescan; should not double-exclude
   - **Handling:** Check if entry already excluded before applying dedup logic; merge duplicate reasons if needed

6. **Collection Artifacts Not Yet Indexed:**
   - Dedup checks collection for duplicates; what if collection is not fully indexed?
   - **Handling:** Only check artifacts that have been successfully imported (status="imported")

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| **Dedup Performance** | Medium | High | Implement lazy hashing, caching, configurable timeout; phase rollout to 10% users first |
| **Manual Mapping UX Complexity** | Low | Medium | Provide auto-suggest for common directory names; add help text; test with 5+ users in beta |
| **Hash Collisions** | Very Low | High | Use SHA256 (industry standard); document collision risk; monitor for false positives |
| **Backward Compat Breaking** | Low | High | No database changes; new API fields optional; thorough testing before production |
| **Over-Exclusion of Duplicates** | Medium | Medium | Store duplicate reason in excluded_reason; allow restore; test with known duplicate sources |
| **GitHub API Rate Limits** | Medium | Medium | Already handled in scanner; ensure dedup doesn't add extra API calls (use cached data) |

---

## 8. Metrics & Observability

### Success Metrics

| Metric | Target | Rationale |
|--------|--------|-----------|
| **Detection Accuracy (Non-Skill Types)** | >= 85% | Measure % of correctly typed commands/agents/etc. |
| **Duplicate Detection Rate** | >= 90% | Measure % of actual duplicates correctly identified |
| **Manual Mapping Adoption** | > 30% of sources | Indicate feature value to users |
| **Scan Time Regression** | < 10% increase | Dedup should not significantly slow scans |
| **User Satisfaction** | >= 4/5 stars (survey) | Qualitative feedback on UX |

### Observability

**Logging (add to scanner output):**

```
[INFO] Scan started: source_id=src_123, repo=user/repo
[INFO] Detection completed: artifacts=42, time_ms=3200
[INFO] Deduplication started: total_artifacts=42
[INFO] Within-source dedup: duplicates_found=4, surviving=38
[INFO] Cross-source dedup: duplicates_found=3, surviving=35
[INFO] Scan completed: time_ms=4100, duplicates_within=4, duplicates_across=3
```

**Metrics (for dashboards):**

```
marketplace_scan_duration_seconds (histogram)
marketplace_artifacts_detected (counter, tagged by source_id)
marketplace_duplicates_within_source (counter)
marketplace_duplicates_across_sources (counter)
marketplace_manual_mappings_used (counter)
marketplace_scan_errors (counter, tagged by error_type)
```

**Alerts:**

- Scan duration > 120s → Investigate timeout
- Dedup CPU usage > 80% → Consider scaling/optimization
- Duplicate detection rate < 70% → Re-evaluate hash algorithm
- API error rate > 2% on rescan endpoint → Check GitHub rate limits

---

## 9. Assumptions & Open Questions

### Assumptions

1. **Manual Mapping Storage:** Using existing `manual_map` JSON column (confirmed in schema)
2. **Catalog Entry Exclusion:** Using existing `excluded_at` and `excluded_reason` fields (confirmed)
3. **GitHub API Access:** Scanner already has GitHub API client; dedup reuses it (confirmed)
4. **ArtifactType Enum:** Currently 5 types (skill, command, agent, mcp_server, hook); no plans to add more in next sprint
5. **Collection Integration:** Collection has artifacts indexed; can query by type and content_hash (needs confirmation)
6. **Async Scanning:** Scans already run asynchronously; dedup inherits async nature (needs confirmation)

### Open Questions

1. **Question:** Should manual mappings override heuristic detection entirely, or provide a fallback?
   - **Decision:** Provide fallback; heuristics still detect within mapped directories (final design in 3.1.2)

2. **Question:** What's the maximum acceptable dedup latency addition to scan time?
   - **Decision:** < 2x scan time (Phase 5 acceptance criteria); if violated, consider async dedup in separate job

3. **Question:** Should users be able to "whitelist" certain duplicates (intentional copies)?
   - **Decision:** Out of scope for v1; can restore via "Restore Excluded"; v2 can add per-entry whitelist

4. **Question:** How to handle dedup across different artifact versions (v1.0 vs v1.1 of same artifact)?
   - **Decision:** v1 treats different versions as duplicates if content_hash identical; v2 can add version-aware dedup

5. **Question:** Should the "Map Directories" modal allow drag-and-drop of artifact types?
   - **Decision:** Out of scope for v1; use simple dropdown; can add drag-and-drop in v1.1 based on feedback

6. **Question:** Performance: If computing hashes for 1000+ artifacts, will it timeout?
   - **Decision:** Yes, risk identified in edge cases; implement lazy hashing and timeout handling (Phase 2 & 5)

---

## 10. Testing Plan

### Unit Tests

**Detection Engine** (70% coverage target):
- Test manual mapping application
- Test hierarchical inheritance (parent → child override)
- Test confidence score assignment (manual vs heuristic)
- Test edge cases (empty directory, nonexistent path)

**Deduplication Engine** (80% coverage target):
- Test hash computation (single file, directory)
- Test within-source dedup (tie-breaking by confidence, then path)
- Test cross-source dedup (collection lookup)
- Test exclusion marking
- Test edge cases (empty list, all duplicates, no duplicates)

**API Routes** (75% coverage target):
- Test PATCH with valid/invalid mappings
- Test GET includes manual_map
- Test rescan with manual_map applied
- Test response schemas match documentation

### Integration Tests

**End-to-End Workflows:**
1. Create source → Add manual mappings → Rescan → Verify correct types
2. Create source with duplicates → Rescan → Verify dedup exclusions
3. Import artifact from duplicated catalog → Verify only one imported
4. Restore excluded duplicate → Verify it appears in catalog

**UI Workflows:**
1. Open modal → Map directories → Save → Close → Verify saved
2. Rescan after mapping → Check notification → View dedup count
3. Click "Duplicate" badge → Verify tooltip explains duplicate

### Performance Tests

- Scan 100+ artifact repo with dedup: target < 120s
- Hash 1000 files: target < 10s
- Cross-source dedup lookup (100 collection artifacts): target < 2s

### Regression Tests

- Existing sources without manual_map still scan correctly
- Existing catalog entries not corrupted after update
- API backward compatibility (old clients still work)

---

## 11. Deployment Strategy

### Rollout Plan

**Phase 1: Backend Internal Testing** (1 day)
- Deploy backend changes to internal staging
- Run full integration test suite
- Performance testing on staging data

**Phase 2: Canary Deployment** (2-3 days)
- Deploy to 10% of production (if multiple instances)
- Monitor error rates, scan durations, dedup stats
- Collect feedback from early users

**Phase 3: Full Rollout** (1 day)
- Deploy to 100% of production
- Monitor metrics closely for 48 hours
- Keep rollback plan ready (restore previous DB snapshot, code)

### Rollback Plan

If critical issues arise:
1. Revert backend code to previous version
2. Revert frontend code to previous version
3. Restore database from pre-deployment snapshot (if needed; no schema changes, so unlikely)
4. Monitor system for 24 hours post-rollback

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MARKETPLACE_MAX_MAPPINGS_PER_SOURCE` | 100 | Limit for manual mappings |
| `MARKETPLACE_DEDUP_ENABLED` | true | Enable/disable deduplication |
| `MARKETPLACE_DEDUP_MAX_FILE_SIZE_MB` | 10 | Skip hashing files > this size |
| `MARKETPLACE_DEDUP_TIMEOUT_SECONDS` | 120 | Timeout for dedup operations |
| `MARKETPLACE_HASH_ALGORITHM` | sha256 | Algorithm for content hashing |

---

## 12. Documentation Plan

### User Documentation

1. **Marketplace Source Guide** (updated):
   - Section on manual directory mapping
   - Screenshots of modal UI
   - Example: "Mapping commands/ directory to command type"
   - FAQ: "How are duplicates handled?"

2. **Troubleshooting Guide**:
   - "Why are my artifacts detected as wrong type?" → Manual mapping
   - "Why are some artifacts hidden as duplicates?" → Dedup explanation
   - "How do I restore a hidden duplicate?" → Restore action

### Developer Documentation

1. **API Documentation** (updated):
   - Document `manual_map` field (schema, example)
   - Document dedup fields in `ScanResultDTO`
   - Example PATCH request with manual mappings
   - Example response with dedup counts

2. **Architecture Guide** (new section):
   - Detection flow with manual mappings
   - Deduplication algorithm explanation
   - Performance characteristics
   - Extensibility points for future artifact types

3. **Contributor Guide**:
   - How to add new artifact types
   - How to tune heuristic detection
   - How to modify dedup algorithm

---

## 13. Success Criteria & Acceptance

### Go/No-Go Decision Points

**Phase 2 (Backend):** Before proceeding to Phase 3 (API)
- [ ] All unit tests pass (>70% coverage)
- [ ] All integration tests pass
- [ ] No performance regression on existing scans
- [ ] No database errors or migration issues

**Phase 3 (API):** Before proceeding to Phase 4 (Frontend)
- [ ] All API tests pass (>75% coverage)
- [ ] PATCH endpoint accepts manual_map correctly
- [ ] Rescan returns dedup counts accurately
- [ ] OpenAPI documentation complete and accurate

**Phase 4 (Frontend):** Before proceeding to Phase 5 (Integration)
- [ ] All component tests pass (>60% coverage)
- [ ] Modal renders correctly and responds to user input
- [ ] No console errors or TypeScript type errors
- [ ] A11y audit passes (WCAG AA)

**Phase 5 (Integration):** Before production deployment
- [ ] All E2E tests pass
- [ ] Edge cases handled gracefully
- [ ] Performance acceptable on large repos
- [ ] User documentation complete
- [ ] Deployment checklist signed off

### Final Acceptance

Feature is **COMPLETE** when:
1. All phases above pass their acceptance criteria
2. Feature deployed to production without critical issues
3. Metrics show expected adoption and performance
4. User feedback indicates feature solves stated problems

---

## 14. Appendix: Data Structures

### manual_map JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "mappings": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "directory": {
            "type": "string",
            "description": "Path relative to root (e.g., 'commands', 'agents/llm')"
          },
          "type": {
            "type": "string",
            "enum": ["skill", "command", "agent", "mcp_server", "hook"],
            "description": "Artifact type for this directory"
          }
        },
        "required": ["directory", "type"],
        "additionalProperties": false
      },
      "minItems": 0,
      "maxItems": 100
    },
    "last_updated": {
      "type": "string",
      "format": "date-time",
      "description": "When mappings were last updated"
    }
  },
  "required": ["mappings"],
  "additionalProperties": false
}
```

### DeduplicationResult Data Structure

```python
@dataclass
class DeduplicationResult:
    total_detected: int
    duplicates_within_source: int
    duplicates_across_sources: int
    surviving_entries: list[ArtifactMetadata]
    excluded_entries: list[tuple[ArtifactMetadata, str]]
    dedup_time_ms: int
```

### content_hash Storage (in metadata_json)

```json
{
  "content_hash": "sha256:abcd1234...",
  "hash_algorithm": "sha256",
  "hash_computed_at": "2026-01-05T10:00:00Z",
  "hash_files_count": 3,
  "hash_total_size_bytes": 5240,
  "duplicate_reason": "Duplicate within source (highest confidence survives)",
  "duplicate_group_id": "dedup_grp_123"
}
```

---

## 15. References

**Existing Code:**
- `skillmeat/core/marketplace/github_scanner.py` - GitHub API client
- `skillmeat/core/marketplace/heuristic_detector.py` - Detection engine
- `skillmeat/cache/models.py` (Line 1173) - MarketplaceSource model
- `skillmeat/cache/models.py` (Line 1368) - MarketplaceCatalogEntry model
- `skillmeat/api/routers/marketplace_sources.py` - API routes
- `skillmeat/web/types/marketplace.ts` - Frontend types

**Related PRDs:**
- Marketplace GitHub Ingestion PRD (v1.0)
- Marketplace Sources Non-Skills Bug Report (2025-12-31)
- Entity Lifecycle Management PRD

**Standards:**
- SHA256 hashing (FIPS 180-4)
- Hierarchical directory structures (POSIX)
- REST API design (RFC 7231)

---

**End of PRD**
