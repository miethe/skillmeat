---
title: 'Phase 1 Implementation: Bug Fixes & Stabilization'
description: Detailed task breakdown for bulk import validation, collection membership
  accuracy, and timestamp fixes
parent: discovery-import-fixes-v1.md
phase: 1
duration: 2 weeks
effort: 12-16 story points
priority: CRITICAL
status: inferred_complete
---
# Phase 1: Bug Fixes & Stabilization

**Duration:** 2 weeks | **Effort:** 12-16 story points | **Priority:** CRITICAL

**Objectives:**
- Fix bulk import 422 errors with graceful validation
- Display accurate Collection membership status
- Fix invalid discovery timestamps
- Stabilize workflow for all artifact types

---

## Phase 1 Task Breakdown

### Task P1-T1: Backend - Validate Artifact Structure & Handle Errors Gracefully

**Task ID:** P1-T1
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Story Points:** 5
**Dependencies:** None
**Estimated Time:** 3-4 hours implementation + 2 hours testing

**Description:**

Modify the bulk import endpoint to validate artifact structure upfront and gracefully skip invalid artifacts instead of failing the entire batch. This requires:

1. Enhanced validation logic in `skillmeat/api/routers/artifacts.py` POST /artifacts/bulk-import handler
2. Updated `skillmeat/core/importer.py` to catch and log YAML parsing errors
3. Response schema change to report per-artifact status with reasons
4. Comprehensive error logging for troubleshooting

**Acceptance Criteria:**

- ✓ Invalid artifact paths (e.g., shell scripts without frontmatter) are skipped with clear reason
- ✓ YAML parsing failures are caught and reported without halting batch
- ✓ Malformed YAML syntax errors result in "skipped" status (not 422 error)
- ✓ Missing required metadata fields logged but artifact still processed if structure valid
- ✓ Bulk import endpoint returns HTTP 200 with "partial_success" status (not 422)
- ✓ Response includes summary: total, imported, skipped, failed counts
- ✓ Response includes results array with per-artifact status and reason codes
- ✓ Reasons include: invalid_structure, yaml_parse_error, missing_metadata, import_error
- ✓ Unit tests cover: valid artifacts, invalid structure, YAML errors, mixed batches
- ✓ Integration test: 20 valid + 3 invalid artifacts → 20 imported, 3 skipped, 0 failed
- ✓ No artifacts imported when batch processing fails
- ✓ Logging shows all skipped artifacts with root cause (for debugging)

**Files to Modify:**

| File | Changes | Reason |
|------|---------|--------|
| `skillmeat/api/routers/artifacts.py` | Enhance POST /bulk-import handler to catch exceptions per-artifact | Entry point for validation |
| `skillmeat/core/importer.py` | Add try/except for YAML parsing, validation; return status tuple | Core import logic |
| `skillmeat/api/schemas/discovery.py` | Add BulkImportResult, ArtifactStatus schemas | Response type definition |

**Implementation Notes:**

**Current Code (Reference):**
```python
# skillmeat/api/routers/artifacts.py (current - fails on error)
@router.post("/bulk-import")
async def bulk_import_artifacts(
    request: BulkImportRequest,
    manager: ArtifactManagerDep,
) -> BulkImportResponse:
    # Current logic: imports all or fails
    results = manager.import_artifacts(request.artifacts)
    return BulkImportResponse(artifacts=results)
```

**Updated Approach:**
```python
# skillmeat/api/routers/artifacts.py (new - graceful handling)
@router.post("/bulk-import", status_code=200)
async def bulk_import_artifacts(
    request: BulkImportRequest,
    manager: ArtifactManagerDep,
) -> BulkImportResponse:
    # Process each artifact with error handling
    results = []
    imported_count = 0
    skipped_count = 0

    for artifact_path in request.artifacts:
        try:
            result = manager.import_artifact(artifact_path)
            results.append(result)
            imported_count += 1
        except YAMLParseError as e:
            results.append({
                "path": artifact_path,
                "status": "skipped",
                "reason": "yaml_parse_error",
                "details": str(e)
            })
            skipped_count += 1
        except ValueError as e:
            results.append({
                "path": artifact_path,
                "status": "skipped",
                "reason": "invalid_structure",
                "details": str(e)
            })
            skipped_count += 1

    return BulkImportResponse(
        status="partial_success" if skipped_count > 0 else "success",
        summary={
            "total": len(request.artifacts),
            "imported": imported_count,
            "skipped": skipped_count,
            "failed": 0
        },
        results=results
    )
```

**Testing Plan:**

| Test Case | Setup | Expected Result |
|-----------|-------|-----------------|
| Valid artifacts only | 5 valid skill artifacts | All imported, status 200 |
| Invalid structure | Shell script (no frontmatter) | Skipped with "invalid_structure" |
| YAML parsing error | Frontmatter with malformed YAML | Skipped with "yaml_parse_error" |
| Mixed batch (20 valid + 3 invalid) | Valid + invalid in same batch | 20 imported, 3 skipped, 200 response |
| Empty batch | Empty artifact list | Empty response, 200 status |
| Missing required fields | Artifact with incomplete metadata | Skipped or handled gracefully |

**Performance Targets:**
- 20 artifacts processed in <2 seconds
- Per-artifact validation <100ms average
- No timeout issues on slow systems

**Potential Issues & Mitigations:**

| Issue | Mitigation |
|-------|-----------|
| YAML parser doesn't catch all errors | Add comprehensive error handling, test with edge case YAML |
| Performance degradation with validation | Batch validation upfront, cache metadata |
| Incorrect reason codes | Document all reason codes, add to schema |
| Partial import leaves collection inconsistent | Validate collection state after each import |

---

### Task P1-T2: Backend - Implement Accurate Collection Membership Query

**Task ID:** P1-T2
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Story Points:** 4
**Dependencies:** None
**Estimated Time:** 2-3 hours implementation + 1 hour testing

**Description:**

Implement a query in the discovery service to check whether each discovered artifact already exists in the user's collection. This requires:

1. Query or lookup function in `skillmeat/core/collection.py` or `skillmeat/core/discovery.py`
2. Integration with collection manifest/inventory
3. Accurate matching logic (name + type, or artifact source link)
4. Performance: <1ms per artifact lookup
5. Discovery endpoint enhanced to include membership status

**Acceptance Criteria:**

- ✓ Discovery service accepts collection context (manifest or manager instance)
- ✓ For each discovered artifact, queries collection membership
- ✓ Membership check based on: artifact name + type + optional source link
- ✓ Returns accurate boolean: in_collection (true/false)
- ✓ Handles artifacts with same name but different type correctly
- ✓ Performance: <500ms total for 100+ artifacts
- ✓ Discovery response includes collection_status object per artifact
- ✓ collection_status includes: in_collection (bool), match_type (exact|hash|name_type|none), matched_artifact_id
- ✓ Unit tests: artifacts in collection, not in collection, edge cases
- ✓ Integration test: Discover artifacts from project, verify status matches collection inventory

**Files to Modify:**

| File | Changes | Reason |
|------|---------|--------|
| `skillmeat/core/collection.py` | Add query method: `artifact_in_collection(name, type, source_link)` | Collection membership check |
| `skillmeat/core/discovery.py` | Enhance `discover_artifacts()` to call membership query for each artifact | Discovery integration |
| `skillmeat/api/routers/artifacts.py` | Pass collection context to discovery service | Route handler integration |
| `skillmeat/api/schemas/discovery.py` | Add CollectionStatus schema to discovery response | Response type definition |

**Implementation Notes:**

**Query Logic:**
```python
def artifact_in_collection(
    self,
    name: str,
    artifact_type: str,
    source_link: Optional[str] = None
) -> bool:
    """Check if artifact exists in collection by name/type or source link."""

    # Exact match: artifact with direct source link
    if source_link:
        for artifact in self.artifacts:
            if artifact.get("source_link") == source_link:
                return True

    # Name + type match
    for artifact in self.artifacts:
        if artifact.get("name") == name and artifact.get("type") == artifact_type:
            return True

    return False
```

**Discovery Integration:**
```python
def discover_artifacts(self, collection=None) -> List[Dict]:
    """Discover artifacts in project, with optional collection membership check."""

    artifacts = []
    for artifact_path in self._find_artifacts():
        metadata = self._parse_artifact_metadata(artifact_path)

        collection_status = None
        if collection:
            in_collection = collection.artifact_in_collection(
                name=metadata['name'],
                artifact_type=metadata['type'],
                source_link=metadata.get('source_link')
            )
            collection_status = {
                "in_collection": in_collection,
                "match_type": "exact" if in_collection else "none"
            }

        artifacts.append({
            **metadata,
            "collection_status": collection_status
        })

    return artifacts
```

**Testing Plan:**

| Test Case | Setup | Expected Result |
|-----------|-------|-----------------|
| Artifact in collection | Skill "awesome" in manifest | in_collection = true |
| Artifact not in collection | Discovered skill not in manifest | in_collection = false |
| Same name, different type | Skill "tool" and Command "tool" | Correctly distinguished |
| Source link match | Artifact with exact source link match | Detected as in collection |
| Empty collection | No artifacts in manifest | All discovered = not in collection |

**Edge Cases:**
- Artifacts with special characters in name
- Case sensitivity (name matching)
- Unicode characters in artifact metadata

---

### Task P1-T3: Backend - Fix Discovery Timestamp Tracking

**Task ID:** P1-T3
**Assigned To:** `python-backend-engineer`
**Model:** Sonnet (well-scoped timestamp logic)
**Story Points:** 3
**Dependencies:** None
**Estimated Time:** 2 hours implementation + 1 hour testing

**Description:**

Fix the timestamp tracking for discovered artifacts. Currently all artifacts show "-1 days ago". Need to:

1. Add `discovered_at` field to collection artifact metadata
2. Track timestamp when artifact is first discovered or content changes
3. Preserve timestamp if artifact unchanged in subsequent discovery runs
4. Return valid ISO 8601 timestamps from discovery endpoint

**Acceptance Criteria:**

- ✓ Discovery endpoint returns valid ISO 8601 timestamp for each artifact (not "-1 days ago")
- ✓ Timestamp set to current time when artifact first discovered
- ✓ Timestamp updated when artifact content changes (hash differs)
- ✓ Timestamp preserved when artifact unchanged between runs
- ✓ All discovered artifacts have valid, sensible timestamps
- ✓ Frontend displays timestamp in human-readable format: "2 days ago", "5 hours ago", "just now"
- ✓ Collection manifest stores ISO 8601 timestamp per artifact
- ✓ Unit tests: new artifact, unchanged artifact, modified artifact timestamps
- ✓ Integration test: Discover same project twice, timestamps preserved on unchanged artifacts

**Files to Modify:**

| File | Changes | Reason |
|------|---------|--------|
| `skillmeat/core/discovery.py` | Add timestamp tracking logic | Core discovery logic |
| `skillmeat/core/collection.py` | Add `discovered_at` field to artifact metadata | Collection storage |
| `skillmeat/api/schemas/discovery.py` | Add discovered_at to response schema | Response type definition |

**Implementation Notes:**

**Timestamp Logic:**
```python
def discover_artifacts(self) -> List[Dict]:
    """Discover artifacts with accurate timestamps."""

    artifacts = []
    now = datetime.utcnow()

    for artifact_path in self._find_artifacts():
        metadata = self._parse_artifact_metadata(artifact_path)
        artifact_hash = self._compute_hash(artifact_path)

        # Check if artifact already in collection
        existing = self._get_existing_artifact(metadata['name'], metadata['type'])

        if existing and existing.get('content_hash') == artifact_hash:
            # Unchanged: preserve timestamp
            metadata['discovered_at'] = existing.get('discovered_at', now.isoformat())
        else:
            # New or changed: set current timestamp
            metadata['discovered_at'] = now.isoformat()

        artifacts.append(metadata)

    return artifacts
```

**Collection Metadata:**
```toml
[[artifacts]]
name = "awesome-skill"
type = "skill"
discovered_at = "2026-01-09T20:15:03.256Z"  # ISO 8601 format
content_hash = "sha256_value"               # For change detection
```

**Frontend Display:**
```typescript
function formatDiscoveryTime(isoTimestamp: string): string {
  const discovered = new Date(isoTimestamp);
  const now = new Date();
  const diffMs = now.getTime() - discovered.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffMinutes = Math.floor(diffMs / (1000 * 60));

  if (diffMinutes < 1) return "just now";
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return discovered.toLocaleDateString();
}
```

**Testing Plan:**

| Test Case | Setup | Expected Result |
|-----------|-------|-----------------|
| First discovery | Artifact not in manifest | Timestamp = now, ISO 8601 format |
| Second discovery (unchanged) | Same artifact, same content | Timestamp unchanged from first |
| Modified artifact | Artifact content changed (hash differs) | Timestamp updated to now |
| Human-readable display | Artifact from 2 hours ago | Displays "2h ago" |
| Old artifact timestamp | Artifact from 30 days ago | Displays "30d ago" |

---

### Task P1-T4: Frontend - Display Accurate Status and Import Results

**Task ID:** P1-T4
**Assigned To:** `ui-engineer-enhanced`
**Model:** Opus
**Story Points:** 5
**Dependencies:** P1-T1, P1-T2, P1-T3 (all backend tasks)
**Estimated Time:** 3-4 hours implementation + 2 hours testing

**Description:**

Update frontend components to display accurate Collection membership status and detailed bulk import results. This includes:

1. Update `useProjectDiscovery` hook to handle new bulk import response format
2. Update `BulkImportModal.tsx` to show per-artifact status and results
3. Update `DiscoveryTab.tsx` to display correct status for each artifact
4. Add error/warning UI for skipped artifacts
5. Format and display timestamps correctly

**Acceptance Criteria:**

- ✓ Discovery tab shows accurate "New - Ready to Import" vs "Already in Collection" status
- ✓ Status correctly reflects backend collection_status data
- ✓ BulkImportModal displays progress as artifacts are imported
- ✓ After import completes, shows results summary: "N imported, M skipped, 0 failed"
- ✓ Skipped artifacts listed with clear reason: "Invalid structure", "YAML parse error", etc.
- ✓ User can see which artifacts failed and why
- ✓ Timestamps display in human-readable format: "2 days ago", "5 hours ago", etc.
- ✓ Modal responsive on desktop + tablet + mobile (tested at 1024px, 768px, 375px)
- ✓ No console errors or warnings
- ✓ Unit tests for status display logic
- ✓ Integration test: BulkImportModal with 20 valid + 3 invalid → correct display

**Files to Modify:**

| File | Changes | Reason |
|------|---------|--------|
| `skillmeat/web/hooks/useProjectDiscovery.ts` | Handle new bulk import response, update cache | Mutation hook for bulk import |
| `skillmeat/web/components/discovery/BulkImportModal.tsx` | Show per-artifact results, summary | Import progress UI |
| `skillmeat/web/components/discovery/DiscoveryTab.tsx` | Display correct status per artifact | Discovery list UI |
| `skillmeat/web/lib/api/discovery.ts` | Update if needed for new response format | API client |

**Implementation Notes:**

**Hook Update (useProjectDiscovery):**
```typescript
export function useProjectDiscovery() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: BulkImportRequest) => {
      const response = await fetch('/api/v1/artifacts/bulk-import', {
        method: 'POST',
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        throw new Error('Import failed');
      }

      return response.json() as BulkImportResponse;
    },
    onSuccess: (data) => {
      // Invalidate discovery cache so it shows updated counts
      queryClient.invalidateQueries({
        queryKey: ['discovery']
      });
    },
  });
}
```

**Component Update (BulkImportModal):**
```typescript
function BulkImportModal({ artifacts, onClose }: Props) {
  const [results, setResults] = useState<BulkImportResponse | null>(null);
  const { mutate, isPending } = useProjectDiscovery();

  if (results) {
    return (
      <Dialog open>
        <DialogHeader>Import Results</DialogHeader>
        <DialogContent>
          <div>Imported: {results.summary.imported}</div>
          <div>Skipped: {results.summary.skipped}</div>

          {results.results.map((result) => (
            <div key={result.path}>
              {result.status === 'imported' ? (
                <span className="text-green-600">✓ {result.name}</span>
              ) : (
                <div>
                  <span className="text-yellow-600">⚠ {result.path}</span>
                  <p className="text-sm text-gray-600">{result.reason}</p>
                  <p className="text-xs text-gray-500">{result.details}</p>
                </div>
              )}
            </div>
          ))}
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open>
      <DialogHeader>Import Artifacts</DialogHeader>
      <button onClick={() => mutate({ artifacts })}>
        Import {artifacts.length} Artifacts
      </button>
    </Dialog>
  );
}
```

**Status Display (DiscoveryTab):**
```typescript
function DiscoveryTab({ artifacts }: Props) {
  return (
    <div>
      {artifacts.map((artifact) => (
        <ArtifactCard key={artifact.path}>
          <div>{artifact.name}</div>
          <div>
            {artifact.collection_status?.in_collection ? (
              <Badge variant="secondary">Already in Collection</Badge>
            ) : (
              <Badge variant="default">New - Ready to Import</Badge>
            )}
          </div>
          <div className="text-sm text-gray-500">
            Discovered: {formatDiscoveryTime(artifact.discovered_at)}
          </div>
        </ArtifactCard>
      ))}
    </div>
  );
}
```

**Testing Plan:**

| Test Case | Setup | Expected Result |
|-----------|-------|-----------------|
| Status display - in collection | Artifact with in_collection=true | Shows "Already in Collection" |
| Status display - not in collection | Artifact with in_collection=false | Shows "New - Ready to Import" |
| Import success | Valid artifacts | Shows results with all "imported" |
| Import with skipped | 20 valid + 3 invalid | Shows 20 imported, 3 skipped with reasons |
| Timestamp formatting | Artifact from 2 hours ago | Displays "2h ago" |
| Mobile responsive | Modal on 375px width | Text readable, buttons clickable |

---

## Phase 1 Summary

| Task | Effort | Status | Owner |
|------|--------|--------|-------|
| P1-T1: Backend validation | 5 pts | Ready | python-backend-engineer |
| P1-T2: Collection membership | 4 pts | Ready | python-backend-engineer |
| P1-T3: Timestamp tracking | 3 pts | Ready | python-backend-engineer |
| P1-T4: Frontend display | 5 pts | Ready | ui-engineer-enhanced |
| **Total Phase 1** | **17 pts** | Ready | 2 engineers |

**Phase 1 Exit Criteria:**
- [ ] All 4 tasks completed and tested
- [ ] QA sign-off on all acceptance criteria
- [ ] Zero 422 errors on test batches
- [ ] Status display matches backend data
- [ ] All timestamps valid (no "-1 days ago")
- [ ] Ready for Phase 2 dependency tasks

---

## Parallel Execution Plan

Tasks P1-T1, P1-T2, and P1-T3 can run in parallel (independent backend work):
- **Week 1:** All three backend tasks progress simultaneously
- **Week 1-2:** P1-T4 starts after backend APIs stabilized (by mid-week 1)
- **Week 2:** Integration testing and QA

**Recommended Sequence:**
1. Day 1-2: P1-T1, P1-T2, P1-T3 started in parallel
2. Day 3-4: P1-T1, P1-T2 complete and tested
3. Day 5: P1-T3 complete, P1-T4 starts (depends on all backend APIs)
4. Day 6-9: P1-T4 implementation and testing
5. Day 10: QA and bug fixes

**Next Phase Gate:**
Phase 2 cannot start until Phase 1 QA is complete and all acceptance criteria met.
