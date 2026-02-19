---
status: inferred_complete
schema_version: 2
doc_type: phase_plan
feature_slug: path-based-tag-extraction
prd_ref: null
plan_ref: null
---
# Phase 3: Import Integration

**Phase**: 3 (Import Integration)
**Duration**: 1 week
**Story Points**: 10-12
**Status**: Ready for Implementation
**Dependencies**: Phase 1 (backend API), Phase 2 (frontend hooks)

---

## Phase Overview

Enable users to opt-in to applying approved path-based tags during bulk import. This phase completes the feature by allowing users to automatically apply reviewed tags when importing multiple artifacts from the marketplace.

### Deliverables

1. Enhanced import request schema with `apply_path_tags` field
2. Backend logic to apply approved tags during import
3. Frontend checkbox in bulk import dialog
4. Integration tests end-to-end
5. Manual QA of complete workflow

### Success Criteria

- <10ms overhead per artifact when applying approved tags
- 100% of approved segments successfully converted to artifact tags
- 50%+ adoption rate of apply_path_tags checkbox in bulk imports (measured post-launch)
- Zero failures or data loss during import process

---

## Task Breakdown

### Task 3.1: Update Import Request Schema

**Assigned To**: python-backend-engineer
**Model**: Sonnet
**Estimation**: 2 story points
**Duration**: 2-3 hours
**Status**: Not Started

#### Description

Add `apply_path_tags` field to the bulk import request schema with sensible defaults.

#### Acceptance Criteria

- [ ] Update `ImportCatalogEntriesRequest` schema (or equivalent bulk import schema)
- [ ] Add field: `apply_path_tags: bool = Field(default=True, description="...")`
  - [ ] Field description explains what it does
  - [ ] Default is `True` (opt-out behavior, easier to adopt)
  - [ ] Optional field (backwards compatible with existing code)
- [ ] Schema file: `skillmeat/api/schemas/discovery.py` or `skillmeat/api/schemas/marketplace.py`
- [ ] Updated docstring explaining field purpose
- [ ] No breaking changes to existing import logic
- [ ] Field validates correctly (bool type)
- [ ] OpenAPI spec updated (auto-generated)

#### Implementation Notes

**File Location**: Find existing `ImportCatalogEntriesRequest` or `BulkImportRequest` schema in either:
- `skillmeat/api/schemas/discovery.py`
- `skillmeat/api/schemas/marketplace.py`

**Pattern**:
```python
from pydantic import BaseModel, Field

class ImportCatalogEntriesRequest(BaseModel):
    """Request to import multiple catalog entries."""
    entry_ids: list[str] = Field(..., description="IDs of catalog entries to import")
    # ... existing fields (collection_id, etc) ...

    apply_path_tags: bool = Field(
        default=True,
        description=(
            "Apply approved path-based tags to imported artifacts. "
            "If true, any segments with status='approved' in entry.path_segments "
            "will be created/found and linked as tags to the imported artifact."
        )
    )
```

#### Dependencies

- Phase 1: Backend API complete (context for understanding import flow)

---

### Task 3.2: Backend Import Logic - Apply Path Tags

**Assigned To**: python-backend-engineer
**Model**: Opus
**Estimation**: 5 story points
**Duration**: 8-10 hours
**Status**: Not Started

#### Description

Implement the backend logic to apply approved path-based tags during the import process.

#### Acceptance Criteria

- [ ] Find and update the import function in `skillmeat/core/importer.py` (or equivalent)
- [ ] Logic adds to import flow:
  - [ ] After artifact is imported successfully
  - [ ] If `request.apply_path_tags == True` AND `entry.path_segments` exists
  - [ ] Parse `path_segments` JSON
  - [ ] Find all segments with `status="approved"`
  - [ ] For each approved segment:
    - [ ] Get `segment.normalized` value (e.g., "data-ai")
    - [ ] Get or create tag with that name
    - [ ] Link tag to imported artifact
  - [ ] If tag creation fails: log error, continue (soft-fail)
  - [ ] Return import result with tag count applied
- [ ] Error handling:
  - [ ] Invalid path_segments JSON: log warning, continue import
  - [ ] Tag creation fails: log error, continue import
  - [ ] Tag linking fails: log error, continue import
  - [ ] No errors should block artifact import
- [ ] Performance:
  - [ ] <10ms overhead per artifact for tag application
  - [ ] Bulk operations (100 artifacts) complete efficiently
  - [ ] No N+1 queries (use batch operations if possible)
- [ ] Data integrity:
  - [ ] Only approved segments applied (not rejected, excluded, or pending)
  - [ ] No duplicate tags created
  - [ ] Transactions ensure atomic operations
- [ ] Logging:
  - [ ] Log successful tag application with count
  - [ ] Log errors with context (entry ID, segment, error detail)
  - [ ] No sensitive data in logs

#### Implementation Notes

**File Location**: `skillmeat/core/importer.py` (or similar import module)

**Pseudo-code**:
```python
def import_catalog_entries(
    request: ImportCatalogEntriesRequest,
    session: Session,
    user_id: str
) -> list[ImportResult]:
    """Import catalog entries with optional path tag application."""
    results = []

    for entry_id in request.entry_ids:
        entry = get_catalog_entry(session, entry_id)

        # Standard import
        try:
            artifact = import_artifact_to_collection(entry, session, user_id)
        except Exception as e:
            logger.error(f"Failed to import entry {entry_id}: {e}")
            results.append(ImportResult(entry_id=entry_id, status="failed", error=str(e)))
            continue

        # Apply path tags if enabled
        tags_applied_count = 0
        if request.apply_path_tags and entry.path_segments:
            try:
                segments_data = json.loads(entry.path_segments)
                approved_segments = [
                    s for s in segments_data.get("extracted", [])
                    if s.get("status") == "approved"
                ]

                for segment in approved_segments:
                    try:
                        tag_name = segment["normalized"]
                        tag = get_or_create_tag(session, tag_name)
                        apply_tag_to_artifact(session, artifact.id, tag.id)
                        tags_applied_count += 1
                    except Exception as e:
                        logger.warning(
                            f"Failed to apply tag '{tag_name}' to artifact {artifact.id}: {e}"
                        )
                        # Continue with other tags; don't fail import

            except json.JSONDecodeError as e:
                logger.error(f"Malformed path_segments for entry {entry_id}: {e}")
            except Exception as e:
                logger.error(f"Error applying path tags for entry {entry_id}: {e}")

        results.append(ImportResult(
            entry_id=entry_id,
            status="success",
            artifact_id=artifact.id,
            tags_applied=tags_applied_count
        ))

    session.commit()
    return results
```

**ImportResult Schema Update**:
```python
class ImportResult(BaseModel):
    """Result of importing a single catalog entry."""
    entry_id: str
    status: Literal["success", "failed"]
    artifact_id: Optional[str] = None
    error: Optional[str] = None
    tags_applied: int = 0  # NEW: Count of tags applied from path segments
```

#### Dependencies

- Task 3.1: Updated import request schema
- Phase 1: PathSegmentExtractor and path_segments data

---

### Task 3.3: Frontend Import Dialog - Checkbox

**Assigned To**: ui-engineer
**Model**: Sonnet
**Estimation**: 2 story points
**Duration**: 2-3 hours
**Status**: Not Started

#### Description

Add the `apply_path_tags` checkbox to the bulk import dialog UI.

#### Acceptance Criteria

- [ ] Find and update import dialog component (likely `components/marketplace/import-dialog.tsx`)
- [ ] Add checkbox control:
  - [ ] Label: "Apply approved path tags"
  - [ ] Default: checked (true)
  - [ ] Help text: "Approved path-based tags from artifacts will be automatically applied"
  - [ ] Visual indicator of how many tags will be applied (if data available)
- [ ] Dynamic helper text:
  - [ ] Example: "(15 tags will be applied to 10 artifacts)"
  - [ ] Text updates based on selected artifacts
  - [ ] Shows "0 tags" if no approved tags available
- [ ] UI layout:
  - [ ] Checkbox positioned logically in import dialog
  - [ ] Below artifact selection, above import button
  - [ ] Consistent with existing form elements
- [ ] Interactions:
  - [ ] Checkbox state updates local state
  - [ ] State passed to import API call
  - [ ] Unchecking disables tag application
- [ ] Responsive:
  - [ ] Works on mobile and desktop
  - [ ] Touch-friendly checkbox (44px minimum)
- [ ] Accessibility:
  - [ ] Checkbox properly labeled (htmlFor connection)
  - [ ] Help text associated with checkbox
  - [ ] Keyboard navigable

#### Implementation Notes

**File Location**: `skillmeat/web/components/marketplace/import-dialog.tsx`

**Pattern**:
```typescript
interface ImportDialogProps {
  entries: CatalogEntry[];
  onImport: (request: ImportRequest) => Promise<void>;
}

export function ImportDialog({ entries, onImport }: ImportDialogProps) {
  const [applyPathTags, setApplyPathTags] = useState(true);

  // Calculate total approved tags across selected entries
  const totalApprovedTags = entries.reduce((sum, entry) => {
    if (!entry.path_segments) return sum;
    try {
      const segments = JSON.parse(entry.path_segments);
      const approved = segments.extracted?.filter((s: any) => s.status === "approved") || [];
      return sum + approved.length;
    } catch {
      return sum;
    }
  }, 0);

  const handleImport = async () => {
    const request = {
      entry_ids: entries.map(e => e.id),
      apply_path_tags: applyPathTags,
      // ... other fields
    };
    await onImport(request);
  };

  return (
    <Dialog>
      <DialogContent>
        {/* Existing import form fields */}

        <div className="space-y-3">
          <label className="flex items-center gap-2 cursor-pointer">
            <Checkbox
              checked={applyPathTags}
              onCheckedChange={(checked) => setApplyPathTags(checked as boolean)}
              id="apply-path-tags"
            />
            <span>Apply approved path tags</span>
          </label>
          {totalApprovedTags > 0 && (
            <p className="text-sm text-muted-foreground ml-6">
              {totalApprovedTags} tags will be applied to {entries.length} artifact{entries.length !== 1 ? 's' : ''}
            </p>
          )}
        </div>

        <Button onClick={handleImport} disabled={isImporting}>
          {isImporting ? 'Importing...' : 'Import'}
        </Button>
      </DialogContent>
    </Dialog>
  );
}
```

#### Dependencies

- Task 3.1: Updated import request schema
- Phase 2: Frontend hooks (may be needed for fetching approved tag counts)

---

### Task 3.4: Update Import API Endpoint

**Assigned To**: python-backend-engineer
**Model**: Sonnet
**Estimation**: 2 story points
**Duration**: 2-3 hours
**Status**: Not Started

#### Description

Update the import API endpoint to accept and use the new `apply_path_tags` field.

#### Acceptance Criteria

- [ ] Find and update the import endpoint (likely `/api/v1/artifacts/discover/import` or similar)
- [ ] Endpoint accepts `ImportCatalogEntriesRequest` with `apply_path_tags` field
- [ ] Field is passed to import function
- [ ] Response includes `tags_applied` count per artifact
- [ ] Documentation updated (docstring and OpenAPI)
- [ ] Backward compatible (old requests without field still work with default)
- [ ] No breaking changes

#### Implementation Notes

**Endpoint Pattern**:
```python
@router.post(
    "/discover/import",
    response_model=BulkImportResponse,
    summary="Import multiple catalog entries to collection",
)
async def import_catalog_entries(
    request: ImportCatalogEntriesRequest,
    session: DbSessionDep,
    current_user: CurrentUserDep,
) -> BulkImportResponse:
    """
    Import multiple catalog entries from marketplace sources.

    Optionally applies approved path-based tags during import via apply_path_tags field.
    """
    results = import_catalog_entries_service(request, session, current_user.id)
    return BulkImportResponse(
        total=len(request.entry_ids),
        successful=sum(1 for r in results if r.status == "success"),
        failed=sum(1 for r in results if r.status == "failed"),
        results=results,
    )
```

#### Dependencies

- Task 3.2: Backend import logic
- Existing import endpoint

---

### Task 3.5: Integration Test - Full Workflow

**Assigned To**: python-backend-engineer
**Model**: Sonnet
**Estimation**: 3 story points
**Duration**: 4-5 hours
**Status**: Not Started

#### Description

Create comprehensive integration test for the complete scan → review → import workflow.

#### Acceptance Criteria

- [ ] Test file created: `tests/integration/test_path_tag_import_workflow.py`
- [ ] Test scenario: "Complete path tag workflow end-to-end"
  - [ ] Create test marketplace source
  - [ ] Add sample artifacts with known paths
  - [ ] Run scanner to extract path segments
  - [ ] Verify path_segments populated correctly
  - [ ] Retrieve path tags via GET endpoint
  - [ ] Update statuses (approve/reject) via PATCH endpoint
  - [ ] Bulk import artifacts with `apply_path_tags=true`
  - [ ] Verify imported artifacts have correct tags applied
  - [ ] Verify tag counts in import result
- [ ] Test scenario: "Import with apply_path_tags=false"
  - [ ] Same setup as above
  - [ ] Approve some segments
  - [ ] Import with `apply_path_tags=false`
  - [ ] Verify NO tags applied (even if approved)
- [ ] Test scenario: "Mixed approval status"
  - [ ] Some segments approved, some rejected, some pending
  - [ ] Import with `apply_path_tags=true`
  - [ ] Verify only approved segments become tags
  - [ ] Verify rejected/pending/excluded are not applied
- [ ] Test data:
  - [ ] Artifacts from different path structures
  - [ ] Include paths with normalized segments (05-data-ai → data-ai)
  - [ ] Include paths with excluded segments
- [ ] Performance:
  - [ ] 100-artifact import with 5+ tags each completes <5s
- [ ] Data integrity:
  - [ ] Artifacts created successfully
  - [ ] Tags created without duplicates
  - [ ] Artifact-tag relationships correct
  - [ ] Database consistent (no orphaned records)

#### Test Structure

```python
import pytest
from sqlalchemy.orm import Session
from skillmeat.cache.models import MarketplaceSource, MarketplaceCatalogEntry
from skillmeat.core.importer import import_catalog_entries
from skillmeat.api.schemas.discovery import ImportCatalogEntriesRequest

class TestPathTagImportWorkflow:
    def test_complete_workflow_scan_to_import(self, db_session: Session):
        """
        Test complete path tag workflow:
        1. Scan repository
        2. Extract path segments
        3. Review and approve segments
        4. Import with apply_path_tags=true
        5. Verify tags on imported artifact
        """
        # Setup
        source = create_test_marketplace_source(db_session)
        entries = create_test_catalog_entries(db_session, source.id)

        # Extract path segments (simulating scanner)
        for entry in entries:
            extract_path_segments_for_entry(entry, db_session)

        # Approve segments
        approve_segments(entries[0].id, db_session)

        # Import
        request = ImportCatalogEntriesRequest(
            entry_ids=[e.id for e in entries],
            apply_path_tags=True,
        )
        results = import_catalog_entries(request, db_session, user_id="test-user")

        # Verify
        assert len(results) == len(entries)
        assert all(r.status == "success" for r in results)
        assert results[0].tags_applied > 0  # First entry had approved tags

        # Verify artifact has tags
        artifact = get_imported_artifact(results[0].artifact_id, db_session)
        assert len(artifact.tags) > 0

    def test_import_with_apply_false(self, db_session: Session):
        """Verify apply_path_tags=false prevents tag application"""
        # ... similar setup ...

        request = ImportCatalogEntriesRequest(
            entry_ids=[entries[0].id],
            apply_path_tags=False,  # Disable
        )
        results = import_catalog_entries(request, db_session, user_id="test-user")

        # Verify NO tags applied
        artifact = get_imported_artifact(results[0].artifact_id, db_session)
        assert len(artifact.tags) == 0
```

#### Dependencies

- Task 3.2: Backend import logic
- Phase 1: Scanner and extraction complete

---

### Task 3.6: Frontend E2E Test - Import Flow

**Assigned To**: ui-engineer
**Model**: Sonnet
**Estimation**: 2 story points
**Duration**: 2-3 hours
**Status**: Not Started

#### Description

Create end-to-end test for the import dialog with path tag checkbox.

#### Acceptance Criteria

- [ ] Test file created: `tests/e2e/test_import_with_path_tags.ts` (Cypress/Playwright)
- [ ] Test scenario: "User imports with path tags enabled"
  - [ ] Open import dialog with 5+ artifacts
  - [ ] Verify "Apply approved path tags" checkbox is visible
  - [ ] Verify helper text shows number of tags
  - [ ] Verify checkbox is checked by default
  - [ ] Click Import button
  - [ ] Verify import succeeds
  - [ ] Verify artifacts appear in collection with tags
- [ ] Test scenario: "User unchecks apply_path_tags"
  - [ ] Open import dialog
  - [ ] Uncheck "Apply approved path tags" checkbox
  - [ ] Click Import button
  - [ ] Verify import succeeds
  - [ ] Verify artifacts do NOT have path tags applied
- [ ] Test data:
  - [ ] Use real catalog entries with path segments
  - [ ] Some with many approved tags, some with few
- [ ] Performance:
  - [ ] Import completes in <5 seconds for 5 artifacts
  - [ ] No timeouts or hangs

#### Dependencies

- Task 3.3: Frontend checkbox
- Phase 2: Complete frontend implementation

---

### Task 3.7: Manual QA & Testing

**Assigned To**: qa-engineer (or developer doing QA)
**Model**: Haiku
**Estimation**: 3 story points
**Duration**: 4-5 hours
**Status**: Not Started

#### Description

Comprehensive manual QA of the complete path tag feature across all three phases.

#### Acceptance Criteria

- [ ] **Marketplace Scanning**:
  - [ ] Scan a repository and verify catalog entries have path_segments
  - [ ] Verify path_segments JSON is valid
  - [ ] Verify extracted segments match expected values
- [ ] **Path Tag Review UI**:
  - [ ] Open catalog entry modal
  - [ ] Verify "Suggested Tags" tab is visible (if path_segments exists)
  - [ ] Verify segments displayed correctly
  - [ ] Approve and reject segments
  - [ ] Verify changes persist after reload
  - [ ] Test with entries having 1, 5, 10+ segments
- [ ] **Import with Path Tags**:
  - [ ] Select 5+ artifacts to import
  - [ ] Open import dialog
  - [ ] Verify checkbox is visible and checked
  - [ ] Verify helper text shows tag count
  - [ ] Uncheck and verify text updates
  - [ ] Import with checkbox checked
  - [ ] Verify artifacts appear in collection with tags
  - [ ] Re-import same artifacts with checkbox unchecked
  - [ ] Verify no duplicate tags are created
- [ ] **Edge Cases**:
  - [ ] Entries with no path_segments (excluded should not show tab)
  - [ ] Entries with all excluded segments (show but all buttons disabled)
  - [ ] Entries with pending/rejected segments (cannot approve/reject again)
  - [ ] Import with mixed approval status (only approved applied)
- [ ] **Error Handling**:
  - [ ] Try to access path tags for non-existent entry (404)
  - [ ] Try to approve already-approved segment (409)
  - [ ] Interrupt network during import (graceful failure)
- [ ] **Performance**:
  - [ ] Marketplace browsing not noticeably slower
  - [ ] Modal opens quickly
  - [ ] Approve/reject completes in <1 second
  - [ ] Import of 10+ artifacts completes in <5 seconds
- [ ] **Cross-browser Testing**:
  - [ ] Chrome/Edge
  - [ ] Firefox
  - [ ] Safari (if macOS)
- [ ] **Mobile Testing** (if applicable):
  - [ ] Modal renders correctly on mobile
  - [ ] Checkbox accessible on touch
  - [ ] No layout issues

#### Test Checklist

```
Marketplace Scanning:
- [ ] Scan repository with path segments
- [ ] Verify JSON in database
- [ ] Extract verification on 3+ repos

Path Tag Review:
- [ ] Modal opens correctly
- [ ] Segments display correctly
- [ ] Approve/reject works
- [ ] Persistence after reload
- [ ] 1-10 segment entries tested

Import Dialog:
- [ ] Checkbox visible and functional
- [ ] Helper text accurate
- [ ] Default state is checked
- [ ] Uncheck works
- [ ] Import succeeds

Tag Application:
- [ ] Tags applied correctly
- [ ] No duplicates
- [ ] Only approved applied
- [ ] Disabled state works

Edge Cases:
- [ ] No path_segments → tab hidden
- [ ] All excluded → disabled buttons
- [ ] Mixed status → correct logic

Errors:
- [ ] 404 handled
- [ ] 409 handled
- [ ] Network error handled

Performance:
- [ ] Browsing speed
- [ ] Modal speed
- [ ] Action speed
- [ ] Import speed

Cross-browser:
- [ ] Chrome
- [ ] Firefox
- [ ] Safari
```

#### Dependencies

- All Phase 1-3 tasks complete

---

### Task 3.8: Documentation - User & Developer

**Assigned To**: documentation-writer
**Model**: Haiku
**Estimation**: 2 story points
**Duration**: 2-3 hours
**Status**: Not Started

#### Description

Update documentation for users and developers on the complete path tag feature.

#### Acceptance Criteria

- [ ] **User Documentation**:
  - [ ] Update "Marketplace Browsing" guide with "Using Suggested Tags" section
  - [ ] Update "Bulk Import" guide with "Applying Path-Based Tags" section
  - [ ] Add screenshots showing:
    - [ ] Suggested Tags tab in modal
    - [ ] Approve/Reject workflow
    - [ ] Import dialog with checkbox
  - [ ] FAQ section:
    - [ ] "How are suggested tags extracted?"
    - [ ] "Why were some path segments excluded?"
    - [ ] "Can I customize extraction rules?" (reference Phase 4)
- [ ] **Developer Documentation**:
  - [ ] Update `docs/api/marketplace.md` with new endpoints
  - [ ] API request/response examples
  - [ ] Example: "Approving segments via API"
  - [ ] Example: "Importing with apply_path_tags"
- [ ] **Architecture**:
  - [ ] Update `docs/architecture/` if applicable
  - [ ] High-level flow diagram (optional)
- [ ] **Changelog**:
  - [ ] Add entry to changelog/release notes
  - [ ] Mention new feature, endpoints, UI
  - [ ] Migration notes (if applicable)

#### Documentation Files

- `docs/user/marketplace.md` (or equivalent)
- `docs/user/import.md` (or equivalent)
- `docs/faq.md`
- `docs/api/marketplace.md`

#### Dependencies

- All Phase 1-3 tasks complete

---

## Phase 3 Summary

### Deliverables Checklist

- [ ] Import request schema updated with `apply_path_tags` field
- [ ] Backend logic to apply approved tags during import
- [ ] Import endpoint updated to handle new field
- [ ] Frontend checkbox in import dialog
- [ ] Integration tests for full workflow
- [ ] E2E tests for import flow
- [ ] Manual QA complete and passed
- [ ] Documentation updated for users and developers

### Definition of Done

Phase 3 is complete when:

1. All 8 tasks have passed code review
2. All acceptance criteria met for each task
3. Integration tests passing
4. E2E tests passing in headless mode
5. Manual QA checklist complete
6. <10ms overhead per artifact (performance target met)
7. No data loss or corruption in import process
8. Backward compatibility verified (old imports still work)
9. Code follows project style guidelines
10. Team approves Phase 3 for deployment

### Post-Launch Monitoring

After Phase 3 deployment, monitor:

1. **Adoption Metrics**:
   - % of users who use apply_path_tags checkbox
   - % of bulk imports with checkbox enabled
   - % of catalog entries with at least one approved segment

2. **Quality Metrics**:
   - % of approved segments later modified or removed (quality indicator)
   - % of entries with no extracted segments (rule tuning needed)
   - Tag distribution consistency

3. **Performance Metrics**:
   - Marketplace scanning time delta (should be <1%)
   - API endpoint latency (should be <200ms)
   - Import operation time delta (should be <1%)

4. **User Feedback**:
   - Support tickets related to path tags
   - Feature requests for Phase 4 (source configuration)
   - Issues with specific repositories or path structures

---

## Appendix: Import Result Schema

Update import response to include tag counts:

```python
class ImportResult(BaseModel):
    """Result of importing a single catalog entry."""
    entry_id: str = Field(..., description="ID of catalog entry")
    status: Literal["success", "failed"] = Field(...)
    artifact_id: Optional[str] = Field(None, description="ID of imported artifact (if success)")
    error: Optional[str] = Field(None, description="Error message (if failed)")
    tags_applied: int = Field(0, description="Number of path-based tags applied")

class BulkImportResponse(BaseModel):
    """Response from bulk import operation."""
    total: int = Field(..., description="Total entries requested")
    successful: int = Field(..., description="Successfully imported")
    failed: int = Field(..., description="Failed to import")
    results: list[ImportResult] = Field(..., description="Per-entry results")
    tags_applied_total: int = Field(0, description="Total tags applied from path segments")
```

---

**Generated with Claude Code** - Implementation Planner Orchestrator
