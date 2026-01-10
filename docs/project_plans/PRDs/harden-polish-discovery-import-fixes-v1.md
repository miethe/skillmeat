# PRD: Project Discovery & Import Fixes and Enhancements

**Filepath:** `harden-polish-discovery-import-fixes-v1.md`

**Date:** 2026-01-09

**Author:** Claude Code (AI Agent)

**Version:** 1.0

**Status:** Ready for Implementation

**Request Log:** REQ-20260109-skillmeat (5 items)

**Related Documents:**
- SkillMeat Architecture Overview (CLAUDE.md)
- Marketplace Deduplication Engine (`skillmeat/core/marketplace/deduplication_engine.py`)
- Collection Management API (`skillmeat/core/collection.py`)
- Discovery & Import Services (`skillmeat/core/discovery.py`, `skillmeat/core/importer.py`)

---

## 1. Executive Summary

This PRD addresses critical bugs and UX enhancements in SkillMeat's Project Discovery & Import workflow. The feature enables developers to discover artifacts from local projects, import them into their personal collection, and deploy them across projects. Current implementation has five issues spanning API robustness, data accuracy, and user experience.

**Priority:** HIGH (2 bugs) + MEDIUM (3 enhancements tied to bug context)

**Key Outcomes:**
- Stabilize bulk import with graceful error handling (Phase 1)
- Fix status display, timestamps, and incorrect collection membership queries (Phase 1)
- Implement intelligent duplicate detection using marketplace hash-matching engine (Phase 2)
- Add review workflow for duplicate and discovered artifacts (Phase 2)
- Streamline deployment UX from multiple entry points (Phase 3)

**Target Impact:**
- Zero failures on bulk import with invalid artifacts (graceful degradation)
- Accurate Collection membership status in discovery UI
- 90% reduction in user confusion about duplicate/already-imported artifacts
- Single-click deployment from Entity Modal and Collection views

---

## 2. Context & Background

### Current State

**Discovery Workflow (Phase 1 Complete):**
- Endpoint: `POST /api/v1/artifacts/discover` - detects artifacts in local project directories
- Supports Skills, Commands, Agents, MCP servers detection from `.claude/` directory structure
- Returns list of candidate artifacts with metadata (name, type, path, etc.)
- Frontend displays in "Discovery" tab of Unified Entity Modal

**Bulk Import Flow (Phase 1 Complete):**
- Endpoint: `POST /api/v1/artifacts/bulk-import` - imports multiple artifacts to collection
- Request format: list of artifact paths with optional metadata overrides
- Returns success/failure list with error details per artifact
- Frontend: `BulkImportModal.tsx` with progress tracking

**Current Limitations:**
1. Status display shows "Already in Collection" for all artifacts regardless of actual membership
2. Bulk import fails completely with 422 when any artifact has invalid structure or YAML parsing error
3. No duplicate detection; artifacts in collection still show as "Ready to Import"
4. Discovery timestamps default to "-1 days ago" for all locally detected artifacts
5. No "Deploy to Project" button in Entity Modal or Collection views

### Problem Space

**Discovery Tab User Experience:**
User (Dev Dan) discovers artifacts in project's `.claude/` directory. The Discovery tab shows:
- All artifacts marked "Already in Collection" (incorrect status)
- Timestamp of "-1 days ago" (incorrect timestamp)
- No warning if artifact is already in collection from previous import
- No quick deployment path from discovery to projects

When user clicks bulk import:
- Single invalid artifact or YAML parsing error fails entire batch
- API returns 422 without specifying which artifacts are invalid
- User has no way to skip invalid artifacts and import the rest

**Collection Management:**
When user has already imported an artifact into collection from a project:
- Same artifact still appears in "Ready to Import" list on subsequent discovery runs
- No hash-based matching to detect duplicates
- No dedicated UI to review and confirm duplicates before import

**Deployment Workflow:**
After discovering/importing artifacts, user wants to deploy them to projects:
- Must navigate away from Entity Modal to /manage view to find Deploy button
- Meatballs menu in Collection view has no Deploy option
- No streamlined path from discovery → import → deploy

### Architectural Context

**Three-Tier System:**
```
Project (.claude/ directories)
  ↑ discover + import
Collection (~/.skillmeat/artifacts)
  ↑ deploy
Projects (target .claude/ paths)
```

**Relevant Systems:**
- **Deduplication Engine** (`skillmeat/core/marketplace/deduplication_engine.py`): Hash-based artifact matching used for marketplace sources
- **Content Hash** (`skillmeat/core/marketplace/content_hash.py`): Generate/compare artifact content hashes
- **Collection Manager** (`skillmeat/core/collection.py`): Collection CRUD and artifact metadata tracking
- **Discovery Service** (`skillmeat/core/discovery.py`): Detect artifacts in project directories
- **Importer Service** (`skillmeat/core/importer.py`): Validate and import artifacts to collection

**Frontend Hooks (React Query):**
- `useProjectDiscovery()` - manage discovery + bulk import mutations
- `useDiscovery()` - read-only artifact list
- `useCollections()` - collection data

**Frontend Components:**
- `DiscoveryTab.tsx` - main discovery UI in Entity Modal
- `BulkImportModal.tsx` - bulk import flow and progress
- `UnifiedEntityModal.tsx` - modal container with tabs
- Collection list and artifact cards

---

## 3. Problem Statement

### Issue 1: Incorrect "Already in Collection" Status (Bug, Medium)

**REQ-20260109-skillmeat-01**

**Current Behavior:**
- Discovery endpoint returns all locally detected artifacts
- Frontend displays status "Already in Collection, will add to Project" for all artifacts
- Status does not reflect actual collection membership

**Root Cause:**
- Query or hook logic incorrectly assumes all discovered artifacts exist in collection
- Collection membership check not performed or incorrectly implemented
- Likely issue in `useProjectDiscovery()` hook or discovery component

**Impact:**
- User confusion about whether artifact is truly in collection
- Cannot make informed decision about import vs. skip
- Blocks accurate duplicate detection workflow

---

### Issue 2: Bulk Import Fails on Invalid Artifacts (Bug, High)

**REQ-20260109-skillmeat-02**

**Current Behavior:**
- Bulk import endpoint (`POST /api/v1/artifacts/bulk-import`) fails with 422 error
- Single invalid artifact or YAML parsing error fails entire batch
- No graceful degradation; all artifacts rejected

**Root Cause Examples:**
1. Invalid artifact paths (e.g., `.claude/hooks/check-style.sh` - shell script, not artifact)
2. YAML frontmatter parsing failures:
   - Malformed YAML syntax in artifact headers
   - Special characters causing YAML parser errors (e.g., `-` in unexpected places)
3. Missing required metadata in artifact headers

**Error Trace:**
```
[API] WARNING: skillmeat.api.routers.artifacts - Invalid artifact structure: /path/to/file
[API] WARNING: skillmeat.core.discovery - Failed to extract frontmatter: ... Expected a comment or line break, but found '-'
```

**Impact:**
- Entire bulk import blocked if project has any invalid artifacts
- User cannot import any valid artifacts from the project
- No way to skip invalid artifacts and proceed
- API returns generic 422 without specifying root cause

---

### Issue 3: No Duplicate Detection Workflow (Enhancement, High)

**REQ-20260109-skillmeat-03**

**Current Behavior:**
- Discovery returns all locally detected artifacts
- No check for existing collection membership via exact link
- No hash-based duplicate detection
- No UI to review and confirm duplicates before import

**Problem Scenario:**
1. User discovers artifacts in project A
2. User bulk imports artifact X to collection
3. User later discovers same project again (or different project with same artifact)
4. Same artifact X appears in "Ready to Import" list
5. User must manually track and skip already-imported artifacts

**Required Capabilities:**
1. Exact link matching: Hide artifacts with direct collection reference from discovered list
2. Hash-based deduplication: Use marketplace deduplication engine to find content-identical artifacts
3. Name+type partial matching: Show "Possible Duplicates" group for review
4. Review workflow: Dedicated modal with matched artifact preview and action buttons
5. Discovery tab integration: Button to open review modal, workflow to process reviews

---

### Issue 4: Invalid Discovery Timestamp (Bug, Low)

**REQ-20260109-skillmeat-04**

**Current Behavior:**
- All locally detected artifacts display "Discovered: -1 days ago"
- Timestamp does not change between discovery runs
- User cannot see when artifact was actually discovered

**Root Cause:**
- Discovery service likely returns invalid or default timestamp for local artifacts
- Timestamp may be calculated incorrectly (negative offset)
- May not track per-artifact discovery timestamp in collection metadata

**Impact:**
- Minimal user impact (low priority)
- Blocks accurate artifact freshness signals
- Confusing UI element ("-1 days ago" is nonsensical)

---

### Issue 5: Missing "Deploy to Project" Button (Enhancement, Medium)

**REQ-20260109-skillmeat-05**

**Current Behavior:**
- Entity Modal "Deployments" tab shows existing deployments
- No button to add new deployment from modal
- Meatballs menu in Collection view has no deployment option
- User must navigate to separate `/manage` view to deploy

**Required Locations:**
1. Entity Modal → Deployments tab → top right "Deploy to Project" button
2. Collection view → artifact meatballs menu → "Deploy to Project" option
3. Update existing `/manage` view button to use same dialog

**Expected Behavior:**
- Button opens "Add to Project" dialog with artifact pre-selected
- User selects target project
- Artifact deployed to correct `.claude/` path location
- Equivalent to running: `skillmeat deploy {ARTIFACT}` in project directory

**Impact:**
- Improves UX flow from discovery → import → deploy
- Reduces context switching between views
- Makes deployment more discoverable

---

## 4. Goals & Success Metrics

### Phase 1: Bug Fixes (Stabilization)

| Goal | Metric | Target |
|------|--------|--------|
| **Eliminate bulk import failures** | Zero 422 errors on bulk import (graceful skip of invalid) | 100% success rate on valid artifacts in batch with invalid items |
| **Accurate collection status** | Status display matches actual membership | Deployed + collection artifacts match verified inventory |
| **Valid timestamps** | All discovered artifacts show real discovery timestamp | No "-1 days ago" timestamps; only new/changed artifacts updated |

### Phase 2: Duplicate Detection

| Goal | Metric | Target |
|------|--------|--------|
| **Hide exact duplicates** | Artifacts with direct collection link not shown | 100% of exact matches hidden from "Ready to Import" |
| **Hash-based deduplication** | Content-identical artifacts detected and linked | 95%+ accuracy of hash-based matches |
| **Review workflow usability** | User can review and approve duplicates in modal | <2 minute average review time per artifact |

### Phase 3: Deployment UX

| Goal | Metric | Target |
|------|--------|--------|
| **Single-click deployment** | "Deploy to Project" button available from multiple entry points | Available in Entity Modal + Collection view |
| **Reduced context switching** | Deploy without leaving Entity Modal | 100% of deployments from modal completion without navigation |

---

## 5. Functional Requirements

### Phase 1: Bug Fixes

#### REQ-P1-1: Validate Artifact Structure Before Bulk Import

**Description:** Backend must validate artifact structure and skip invalid artifacts gracefully instead of failing entire batch.

**Acceptance Criteria:**
- ✓ Invalid artifact paths (e.g., shell scripts without artifact headers) are skipped with warning
- ✓ YAML parsing failures are caught and logged without halting batch
- ✓ Bulk import endpoint returns 200 (not 422) with per-artifact status
- ✓ Response includes:
  - List of successfully imported artifacts
  - List of skipped artifacts with reason (invalid structure, YAML error, etc.)
  - Summary counts (imported: N, skipped: M, failed: 0)
- ✓ Frontend displays import results with clear feedback for each artifact
- ✓ User can see which artifacts were skipped and why

**API Contract:**

Request (unchanged):
```json
POST /api/v1/artifacts/bulk-import
{
  "artifacts": [
    { "path": "/path/to/artifact", ... },
    ...
  ]
}
```

Response (enhanced):
```json
{
  "status": "partial_success",
  "summary": {
    "total": 10,
    "imported": 8,
    "skipped": 2,
    "failed": 0
  },
  "results": [
    {
      "path": "/path/to/valid_artifact",
      "status": "imported",
      "artifact_id": "abc123"
    },
    {
      "path": "/path/to/invalid_artifact",
      "status": "skipped",
      "reason": "Invalid artifact structure: missing frontmatter"
    },
    {
      "path": "/path/to/yaml_error",
      "status": "skipped",
      "reason": "Failed to parse YAML frontmatter: Expected a comment or line break, but found '-'"
    }
  ]
}
```

---

#### REQ-P1-2: Display Accurate Collection Membership Status

**Description:** Discovery UI must display accurate "Already in Collection" status reflecting actual collection membership.

**Acceptance Criteria:**
- ✓ Collection membership check performed for each discovered artifact
- ✓ Status correctly shows:
  - "New - Ready to Import" (not in collection, can import)
  - "Already in Collection" (linked artifact exists in collection)
  - "Possible Duplicate" (hash or name+type match found)
- ✓ Status display reflects discovered artifact metadata vs. collection query result
- ✓ Hook `useProjectDiscovery()` implements membership check before rendering
- ✓ Frontend component `DiscoveryTab.tsx` displays correct status for each artifact

**Implementation Notes:**
- Use collection inventory API or local manifest to check membership
- Check against artifact name, type, and optional source link
- Defer exact/hash matching to Phase 2

---

#### REQ-P1-3: Fix Discovery Timestamp Display

**Description:** Discovery service must provide accurate discovery timestamps, updated only for new/changed artifacts.

**Acceptance Criteria:**
- ✓ Discovery endpoint returns valid ISO 8601 timestamp for each artifact
- ✓ Timestamp reflects actual discovery time (not "-1 days ago")
- ✓ Timestamps only updated when artifact is new or content changed since last discovery
- ✓ Historical timestamp preserved if artifact unchanged
- ✓ Frontend displays timestamp in human-readable format (e.g., "2 days ago", "5 hours ago")

**Data Model:**
- Add `discovered_at` field to artifact metadata in collection manifest
- Track per-artifact, not per-discovery-run
- Update only if artifact is new or hash differs from previous run

---

### Phase 2: Duplicate Detection

#### REQ-P2-1: Implement Hash-Based Duplicate Detection

**Description:** Backend must detect content-identical artifacts using existing deduplication engine.

**Acceptance Criteria:**
- ✓ Discovery service uses `marketplace/deduplication_engine.py` to compute and match artifact hashes
- ✓ Content hash computed for discovered artifacts using `content_hash.py`
- ✓ Hash compared against all collection artifacts
- ✓ Exact hash match detected (same content, likely duplicate)
- ✓ Hash mismatch recorded (different content)
- ✓ Hash match result returned in discovery response payload
- ✓ Performance: hash matching completes <500ms for typical collection (100+ artifacts)

**API Contract Enhancement:**

Discovery endpoint response includes hash metadata:
```json
{
  "artifacts": [
    {
      "path": "/path/to/artifact",
      "name": "skill-name",
      "type": "skill",
      "content_hash": "abc123def456",
      "collection_match": {
        "type": "exact",  // "exact", "name_type", "none"
        "matched_artifact_id": "existing-id",
        "matched_name": "skill-name",
        "confidence": 0.95
      }
    }
  ]
}
```

---

#### REQ-P2-2: Filter Discovered Artifacts by Match Status

**Description:** Discovery tab must hide exact matches and show "Possible Duplicates" group.

**Acceptance Criteria:**
- ✓ Artifacts with exact collection link are hidden from "Ready to Import" list
- ✓ Artifacts with hash-based match are hidden and linked to existing collection artifact
- ✓ "Possible Duplicates in Collection" group shown separately with:
  - Artifact name, type, path
  - Matched artifact from collection
  - Link to matched artifact
  - Option to confirm match or skip
- ✓ "Ready to Import" group shows only new/unmatched artifacts
- ✓ User can toggle visibility of hidden matched artifacts

---

#### REQ-P2-3: Add "Review Discovered Artifacts" Modal

**Description:** Dedicated UI modal for reviewing and confirming duplicate matches.

**Acceptance Criteria:**
- ✓ Button in Discovery tab: "Review Discovered Artifacts" (visible when possible duplicates exist)
- ✓ Modal opens with three tabs:
  1. "New Artifacts" - unmatched, ready to import
  2. "Possible Duplicates" - name/type matches for review
  3. "Exact Matches" - content-identical artifacts already linked
- ✓ Duplicate review tab shows:
  - Left panel: Discovered artifact (name, type, path, preview)
  - Right panel: Dropdown selector with potential matches
  - Default match pre-selected (highest confidence match)
  - Option to select any artifact of same type from collection
  - Toggles:
    - "Skip this artifact" (exclude from import)
    - "Mark as New Artifact" (treat as new, not duplicate)
- ✓ Action buttons:
  - "Confirm Matches" (link matched duplicates, skip confirmed)
  - "Import New Only" (import only artifacts marked as new)
  - "Cancel" (abandon review)
- ✓ Modal shows summary: "2 new artifacts, 3 possible duplicates, 1 already linked"

**UI Mockup Concept:**

```
┌─────────────────────────────────────────────────────────┐
│ Review Discovered Artifacts                      [Close] │
├─────────────────────────────────────────────────────────┤
│ [New Artifacts] [Possible Duplicates] [Exact Matches]   │
├──────────────────────────────┬──────────────────────────┤
│ Discovered Artifact          │ Collection Match         │
├──────────────────────────────┼──────────────────────────┤
│ Name: awesome-skill          │ [Dropdown v]             │
│ Type: skill                  │ - awesome-skill (exact)  │
│ Path: .claude/skills/...     │ - similar-skill          │
│                              │ - other-skill           │
│ Preview:                     │                          │
│ [File content preview]       │ Match Confidence: 95%   │
│                              │                          │
│                              │ ☑ Skip this artifact    │
│                              │ ☐ Mark as New           │
├──────────────────────────────┴──────────────────────────┤
│ [Cancel] [Import New Only]              [Confirm Match] │
└─────────────────────────────────────────────────────────┘
```

---

#### REQ-P2-4: Process Duplicate Review Results

**Description:** Backend must process duplicate review decisions and update artifact states.

**Acceptance Criteria:**
- ✓ Endpoint accepts review decisions: `POST /api/v1/artifacts/confirm-duplicates`
- ✓ Request includes:
  - List of confirmed matches (discovered_path → collection_artifact_id)
  - List of artifacts to mark as new
  - List of artifacts to skip
- ✓ Process:
  - Create duplicate links in collection metadata (store link relationship)
  - Skip matched artifacts from import
  - Import artifacts marked as new
  - Record review decision in audit log
- ✓ Response indicates success and updated artifact counts

**API Contract:**

```json
POST /api/v1/artifacts/confirm-duplicates
{
  "project_path": "/path/to/project",
  "matches": [
    {
      "discovered_path": "/path/to/discovered/artifact",
      "collection_artifact_id": "existing-id",
      "action": "link"
    }
  ],
  "new_artifacts": [
    "/path/to/new/artifact"
  ],
  "skipped": [
    "/path/to/skip/artifact"
  ]
}

Response:
{
  "status": "success",
  "linked_count": 2,
  "imported_count": 1,
  "skipped_count": 1,
  "message": "2 duplicates linked, 1 new artifact imported, 1 skipped"
}
```

---

### Phase 3: Deployment UX

#### REQ-P3-1: Add Deploy Button to Entity Modal

**Description:** Entity Modal "Deployments" tab must include "Deploy to Project" button.

**Acceptance Criteria:**
- ✓ Button added to Deployments tab header (top right)
- ✓ Button text: "Deploy to Project" or "Add to Project"
- ✓ Button click opens "Add to Project" dialog (reuses existing component)
- ✓ Dialog pre-selects current artifact
- ✓ Dialog workflow:
  1. User selects target project from dropdown
  2. User confirms deployment location (optional customization)
  3. Artifact deployed to target project
  4. Dialog closes, Deployments tab refreshes to show new deployment
- ✓ Visual consistency with existing deployment workflow

---

#### REQ-P3-2: Add Deploy Option to Collection View Meatballs Menu

**Description:** Artifact meatballs menu in Collection view must include deployment action.

**Acceptance Criteria:**
- ✓ Menu option added: "Deploy to Project" (or icon indicating deployment)
- ✓ Click opens same "Add to Project" dialog as Entity Modal button
- ✓ Artifact pre-selected in dialog
- ✓ Same deployment workflow as Phase 3.1
- ✓ Consistency across all deployment entry points

---

#### REQ-P3-3: Update Existing /manage View Button

**Description:** Existing "Deploy to Project" button in `/manage` view must be updated to use unified dialog.

**Acceptance Criteria:**
- ✓ Button behavior unchanged (opens "Add to Project" dialog)
- ✓ Dialog pre-selects artifact and implements same UX as new entry points
- ✓ All deployment entry points (Entity Modal, Collection, /manage) use same component
- ✓ No duplicate dialog implementations or divergent workflows

---

## 6. Non-Functional Requirements

| Category | Requirement | Notes |
|----------|-------------|-------|
| **Performance** | Bulk import with 20+ items completes <2sec | Validation before 422 error |
| **Performance** | Hash matching for 100 collection artifacts <500ms | Marketplace engine already optimized |
| **Resilience** | Single invalid artifact doesn't fail batch | Graceful degradation, partial success response |
| **Data Integrity** | Duplicate link relationships preserved in metadata | Collection manifest tracking |
| **Logging** | All skipped/failed artifacts logged with reason | Audit trail for troubleshooting |
| **API Backward Compat** | Bulk import endpoint maintains request schema | Response schema extended, not changed |
| **Frontend UX** | Modal responsive on mobile (90%+ of viewport) | Duplicate review must be usable on small screens |
| **Accessibility** | Modal keyboard navigable (Tab, Enter, Escape) | WCAG 2.1 AA compliance |

---

## 7. Scope

### In Scope (Phase 1, 2, 3)

✓ **Phase 1 - Bug Fixes:**
- REQ-P1-1: Graceful bulk import validation and error handling
- REQ-P1-2: Accurate collection membership status display
- REQ-P1-3: Fix discovery timestamp calculation and display

✓ **Phase 2 - Duplicate Detection:**
- REQ-P2-1: Hash-based duplicate detection using marketplace engine
- REQ-P2-2: Filter discovered artifacts by match status
- REQ-P2-3: "Review Discovered Artifacts" modal with duplicate review tab
- REQ-P2-4: Process and persist duplicate review decisions

✓ **Phase 3 - Deployment UX:**
- REQ-P3-1: Deploy button in Entity Modal Deployments tab
- REQ-P3-2: Deploy option in Collection view meatballs menu
- REQ-P3-3: Update /manage view button for consistency

### Out of Scope

✗ Marketplace sources duplicate detection updates (separate PRD)
✗ Collection metadata schema refactor (Phase 4)
✗ Artifact versioning or version pinning
✗ Multi-project bulk operations beyond single discovery run
✗ Collection storage format changes (manifest/lock file refactor)

---

## 8. Dependencies & Assumptions

### Dependencies

| Dependency | Owner | Status | Notes |
|------------|-------|--------|-------|
| Marketplace deduplication engine | Core | ✓ Exists | `skillmeat/core/marketplace/deduplication_engine.py` |
| Content hash utility | Core | ✓ Exists | `skillmeat/core/marketplace/content_hash.py` |
| Collection inventory API | Core | ✓ Exists | For membership check |
| YAML frontmatter parser robustness | Core | ⚠ Partial | May need error handling improvements |
| Collection manifest schema | Core | ✓ Current | Supports artifact metadata tracking |
| React Query (TanStack Query) | Frontend | ✓ Exists | Cache management for discovery/collection |
| "Add to Project" dialog component | Frontend | ✓ Exists | Reuse for Phase 3 |
| FastAPI router layer | API | ✓ Exists | For bulk import and discovery endpoints |

### Assumptions

| Assumption | Justification | Risk |
|-----------|---------------|------|
| Marketplace hash matching algorithm already handles Skills/Commands/etc. | Engine used for sources | Low - algorithm proven |
| Collection manifest can store duplicate link relationships | Standard metadata pattern | Low - similar to current tracking |
| Invalid artifacts (e.g., shell scripts) can be reliably detected via structure validation | Discovery service already validates | Low - implemented in Phase 1 |
| Users will review duplicates before bulk import | UX best practice | Low - optional modal, not blocking |
| YAML parsing failures are catchable exceptions | Standard Python behavior | Low - well-understood error handling |
| Bulk import endpoint supports partial success response | REST API pattern | Low - no auth/security concerns |
| "Add to Project" dialog can pre-select artifact parameter | Current dialog design | Medium - requires dialog API review |

---

## 9. Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| **Hash collision**: Different artifacts match same hash | Low | High | Use marketplace engine (proven), add confidence scoring, require name+type match for partial duplicates |
| **Timestamp sync**: Artifact timestamps inconsistent across runs | Medium | Low | Validate timestamp logic during Phase 1 testing, log all timestamp updates |
| **YAML parser edge cases**: New syntax errors appear after deployment | Medium | Medium | Extensive YAML test suite, fallback error handling, user feedback channel |
| **Modal UX complexity**: Users confused by duplicate review workflow | Medium | Medium | Clear labels, tooltips, preview artifact content, single-click defaults |
| **Performance**: Hash matching slow for large collections (1000+ artifacts) | Low | Medium | Batch hash computation, async processing, progress indicator |
| **Backward compatibility**: Bulk import response schema breaks clients | Low | High | Extend response schema (add fields), don't remove; communicate change |
| **Dialog pre-selection**: "Add to Project" dialog doesn't support artifact param | Low | Medium | Fallback to user selection, document API contract clearly |

---

## 10. Target State

### After Phase 1 (Bug Fixes)

**Bulk Import Workflow:**
1. User clicks "Import Artifacts" in Discovery tab
2. Backend validates all artifacts before processing
3. Valid artifacts imported to collection
4. Invalid/malformed artifacts skipped with clear reason
5. Response shows: "8 imported, 2 skipped (invalid structure)"
6. Frontend displays results with per-artifact feedback
7. User can view skipped artifacts and reasons
8. Zero 422 errors on valid artifact batches

**Discovery Status Accuracy:**
1. Discovery tab shows accurate "Already in Collection" status for each artifact
2. Status reflects actual collection membership via inventory check
3. User can make informed decision about import vs. skip

**Timestamp Accuracy:**
1. All discovered artifacts show real discovery timestamp (not "-1 days ago")
2. Timestamp only updates for new or changed artifacts
3. UI displays human-readable format: "2 days ago", "5 hours ago", "just now"

---

### After Phase 2 (Duplicate Detection)

**Enhanced Discovery Tab:**
1. Artifacts with exact collection link hidden from "Ready to Import"
2. Hash-based matching identifies content-identical artifacts
3. "Possible Duplicates in Collection" group shows name+type matches
4. Button "Review Discovered Artifacts" visible when duplicates exist

**Duplicate Review Modal:**
1. Modal opens with tabs: New Artifacts, Possible Duplicates, Exact Matches
2. User reviews each duplicate with side-by-side comparison
3. User confirms matches or marks as new
4. Modal shows summary of decisions (2 new, 3 confirmed, 1 skipped)

**Import Decision Processing:**
1. User clicks "Confirm Matches" or "Import New Only"
2. Backend processes decisions: links duplicates, imports new, skips confirmed
3. Collection updated with duplicate link relationships
4. Discovery tab refreshes showing only unmatched artifacts
5. Audit log records all decisions for future reference

---

### After Phase 3 (Deployment UX)

**Multiple Deployment Entry Points:**
1. Entity Modal Deployments tab → "Deploy to Project" button (top right)
2. Collection view artifact → meatballs menu → "Deploy to Project"
3. /manage view artifact → meatballs menu → "Deploy to Project" (updated)

**Unified Deployment Dialog:**
1. All entry points open same "Add to Project" dialog
2. Artifact pre-selected (user can change if desired)
3. User selects target project
4. Artifact deployed to project's `.claude/` directory
5. Dialog closes, UI refreshes to show new deployment
6. No context switching required

---

## 11. Acceptance Criteria

### Phase 1 Completion

- [ ] All bulk import tests pass: valid + invalid artifact batches
- [ ] 422 errors eliminated: only 200 responses with partial success handling
- [ ] Status display in Discovery tab matches collection inventory
- [ ] All artifacts have valid timestamps (no "-1 days ago")
- [ ] Integration test: Bulk import with 20 valid + 3 invalid items → 20 imported, 3 skipped
- [ ] Frontend error handling: User sees clear feedback for all skipped artifacts
- [ ] API response schema documented and tested
- [ ] Logging shows all skipped artifacts with root cause

### Phase 2 Completion

- [ ] Hash matching implementation integrated and tested
- [ ] Discovery endpoint returns collection_match metadata for all artifacts
- [ ] Exact matches filtered from "Ready to Import" list
- [ ] "Possible Duplicates in Collection" group populated correctly
- [ ] "Review Discovered Artifacts" modal opens and displays duplicates
- [ ] User can confirm, skip, or mark-as-new in modal
- [ ] Duplicate decisions persisted in collection metadata
- [ ] Integration test: 10 discovered artifacts (3 exact, 2 partial, 5 new) → correct grouping and review workflow
- [ ] Modal responsive on mobile screens
- [ ] Keyboard navigation works (Tab, Enter, Escape)

### Phase 3 Completion

- [ ] "Deploy to Project" button visible in Entity Modal Deployments tab
- [ ] Button click opens "Add to Project" dialog with artifact pre-selected
- [ ] Deployment workflow completes without leaving modal
- [ ] Collection view meatballs menu includes "Deploy to Project" option
- [ ] /manage view button updated to use unified dialog
- [ ] All entry points use same dialog component (no duplicate implementations)
- [ ] Integration test: Deploy from Entity Modal → artifact appears in target project
- [ ] Integration test: Deploy from Collection view → artifact deployed successfully

---

## 12. Implementation Phases

### Phase 1: Bug Fixes & Stabilization (Target: 2 sprints)

**Goals:** Eliminate 422 errors, fix status/timestamp, stabilize bulk import

**Stories:**
1. **P1-S1:** Backend - Validate artifact structure before bulk import
   - Implement validation logic in `skillmeat/api/routers/artifacts.py`
   - Update response schema to include per-artifact status
   - Add logging for skipped artifacts
   - Tests: valid artifacts, invalid structure, YAML errors, mixed batches

2. **P1-S2:** Backend - Fix collection membership query
   - Review and fix collection inventory check
   - Implement in discovery service or manager layer
   - Return membership status in discovery response
   - Tests: artifacts in collection vs. not in collection

3. **P1-S3:** Backend - Fix discovery timestamp calculation
   - Implement per-artifact timestamp tracking in collection metadata
   - Update only for new/changed artifacts
   - Tests: timestamp accuracy, preservation across runs

4. **P1-S4:** Frontend - Display accurate status and results
   - Update `BulkImportModal.tsx` to show per-artifact results
   - Update `DiscoveryTab.tsx` to display correct status
   - Add error/warning UI for skipped artifacts
   - Tests: Status display matches backend, clear error messaging

---

### Phase 2: Duplicate Detection & Review (Target: 2 sprints)

**Goals:** Implement hash-based deduplication, add review workflow

**Stories:**
1. **P2-S1:** Backend - Integrate hash-based deduplication
   - Use marketplace deduplication engine
   - Compute hashes for discovered artifacts
   - Match against collection artifacts
   - Update discovery response schema
   - Tests: hash matching accuracy, performance with large collections

2. **P2-S2:** Backend - Implement duplicate decision processing
   - Add endpoint: `POST /api/v1/artifacts/confirm-duplicates`
   - Process matches, new, skipped decisions
   - Update collection metadata with links
   - Tests: decision persistence, audit logging

3. **P2-S3:** Frontend - Filter and group artifacts by match status
   - Update Discovery tab to show groups: New, Possible Duplicates, Exact Matches
   - Hide exact matches from "Ready to Import"
   - Add "Review Discovered Artifacts" button
   - Tests: correct grouping, filtering logic

4. **P2-S4:** Frontend - Build duplicate review modal
   - Create modal component with three tabs
   - Implement duplicate review UI (left/right comparison)
   - Add decision toggles and action buttons
   - Tests: modal rendering, tab switching, decision submission

---

### Phase 3: Deployment UX Improvements (Target: 1 sprint)

**Goals:** Add deployment buttons to multiple entry points

**Stories:**
1. **P3-S1:** Frontend - Add Deploy button to Entity Modal
   - Add button to Deployments tab header
   - Wire to existing "Add to Project" dialog
   - Test artifact pre-selection
   - Tests: button visibility, dialog launch, pre-selection

2. **P3-S2:** Frontend - Add Deploy option to Collection view
   - Update meatballs menu component
   - Add deployment action
   - Wire to dialog
   - Tests: menu rendering, dialog launch

3. **P3-S3:** Frontend - Update /manage view button
   - Verify button uses unified dialog
   - Ensure consistency with new entry points
   - Tests: all buttons use same dialog component

---

## 13. Testing Strategy

### Unit Tests

- **Backend:**
  - Artifact validation logic (valid/invalid structures, YAML parsing)
  - Collection membership queries
  - Timestamp calculation and tracking
  - Hash matching and deduplication
  - Decision processing and persistence

- **Frontend:**
  - Status display logic
  - Modal grouping and filtering
  - Decision button actions
  - Timestamp formatting

### Integration Tests

- **Bulk import workflow:** Valid + invalid artifacts in single batch
- **Discovery to import:** Full workflow from discovery → bulk import → collection update
- **Duplicate review:** Full workflow from discovery → modal → decision → import
- **Deployment from modal:** Full workflow from Entity Modal → deploy → project update
- **API response contracts:** Verify response schemas match documentation

### E2E Tests

- **Phase 1:** Bulk import with mixed artifacts, verify results and logging
- **Phase 2:** Discover → review duplicates → import, verify collection state
- **Phase 3:** Deploy from Entity Modal and Collection view

### Test Data

- **Sample artifacts:** Valid skills, commands, agents, invalid shell scripts
- **YAML parsing test cases:** Malformed YAML, edge case syntax
- **Collection state:** Various artifact counts (10, 100, 1000+) for performance
- **Duplicate scenarios:** Exact matches, partial matches, no matches

---

## 14. Open Questions & Notes

### Design Decisions Pending

1. **Duplicate link representation:** How to store relationship in collection manifest? New metadata field or separate index?
2. **Hash matching confidence threshold:** What confidence % constitutes "match"? Current marketplace default acceptable?
3. **Timestamp precision:** Store ISO 8601 or Unix timestamp? Timezone handling?
4. **Partial success 200 vs 202:** Use 200 OK or 202 Accepted for partial success? (RESTful convention question)
5. **Dialog reuse:** Can existing "Add to Project" dialog accept artifact pre-selection parameter? Requires interface review.

### Assumptions to Validate

- [ ] Marketplace deduplication engine works for all artifact types (not just skills)
- [ ] Collection manifest schema supports duplicate link relationships
- [ ] YAML parser errors are catchable and descriptive
- [ ] "Add to Project" dialog architecture supports pre-selection

### Dependencies to Confirm

- [ ] Core team confirms marketplace engine API contract
- [ ] Data team confirms collection metadata schema versioning approach
- [ ] Frontend team confirms "Add to Project" dialog component interface

---

## 15. Appendix: Detailed API Specifications

### Bulk Import Enhanced Response

**Endpoint:** `POST /api/v1/artifacts/bulk-import`

**Request:**
```json
{
  "artifacts": [
    {
      "path": "/absolute/path/to/artifact",
      "artifact_type": "skill",  // optional override
      "custom_name": "custom-name"  // optional override
    }
  ],
  "target_collection": "default"  // optional, defaults to user's primary
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "summary": {
    "total": 10,
    "imported": 8,
    "skipped": 2,
    "failed": 0
  },
  "results": [
    {
      "path": "/path/to/artifact_1",
      "name": "artifact-1",
      "type": "skill",
      "status": "imported",
      "artifact_id": "id_001",
      "message": "Successfully imported"
    },
    {
      "path": "/path/to/artifact_2",
      "status": "skipped",
      "reason": "invalid_structure",
      "details": "Artifact does not contain required frontmatter"
    },
    {
      "path": "/path/to/artifact_3",
      "status": "skipped",
      "reason": "yaml_parse_error",
      "details": "Failed to parse YAML frontmatter: Expected a comment or line break, but found '-'"
    }
  ],
  "timestamp": "2026-01-09T20:15:03.256Z"
}
```

### Discovery Response with Hash Metadata

**Endpoint:** `POST /api/v1/artifacts/discover`

**Response:**
```json
{
  "project": {
    "path": "/path/to/project",
    "name": "my-project"
  },
  "artifacts": [
    {
      "path": "/path/to/artifact",
      "name": "awesome-skill",
      "type": "skill",
      "content_hash": "sha256_hash_value",
      "discovered_at": "2026-01-09T20:15:03.256Z",
      "collection_status": {
        "in_collection": true,
        "match_type": "exact",  // "exact", "hash", "name_type", "none"
        "matched_artifact_id": "collection_id_123",
        "matched_name": "awesome-skill",
        "confidence": 1.0
      }
    },
    {
      "path": "/path/to/another",
      "name": "helper-command",
      "type": "command",
      "content_hash": "different_hash",
      "discovered_at": "2026-01-09T20:15:03.256Z",
      "collection_status": {
        "in_collection": false,
        "match_type": "none",
        "matched_artifact_id": null,
        "confidence": 0.0
      }
    }
  ],
  "timestamp": "2026-01-09T20:15:03.256Z"
}
```

### Confirm Duplicates Endpoint

**Endpoint:** `POST /api/v1/artifacts/confirm-duplicates`

**Request:**
```json
{
  "project_path": "/path/to/project",
  "matches": [
    {
      "discovered_path": "/path/to/discovered",
      "collection_artifact_id": "existing_id_123",
      "action": "link"
    }
  ],
  "new_artifacts": [
    "/path/to/new_artifact"
  ],
  "skipped": [
    "/path/to/skipped_artifact"
  ]
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "linked_count": 1,
  "imported_count": 1,
  "skipped_count": 1,
  "message": "1 duplicate linked, 1 new artifact imported, 1 skipped",
  "timestamp": "2026-01-09T20:15:03.256Z"
}
```

---

**End of PRD**
