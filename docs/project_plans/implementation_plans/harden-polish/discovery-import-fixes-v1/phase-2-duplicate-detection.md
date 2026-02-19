---
title: 'Phase 2 Implementation: Duplicate Detection & Review Workflow'
description: Detailed task breakdown for hash-based deduplication, discovery filtering,
  and duplicate review modal
parent: discovery-import-fixes-v1.md
phase: 2
duration: 2 weeks
effort: 18-22 story points
priority: HIGH
depends_on: phase-1-bug-fixes.md
status: inferred_complete
schema_version: 2
doc_type: phase_plan
feature_slug: discovery-import-fixes
prd_ref: null
plan_ref: null
---
# Phase 2: Duplicate Detection & Review Workflow

**Duration:** 2 weeks | **Effort:** 18-22 story points | **Priority:** HIGH | **Depends On:** Phase 1 completion

**Objectives:**
- Implement hash-based duplicate detection using marketplace engine
- Filter and group discovered artifacts by match status
- Create duplicate review modal with decision workflow
- Process and persist duplicate review decisions

---

## Phase 2 Task Breakdown

### Task P2-T1: Backend - Integrate Hash-Based Deduplication

**Task ID:** P2-T1
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Story Points:** 6
**Dependencies:** Phase 1 (collection membership working)
**Estimated Time:** 4-5 hours implementation + 2 hours testing

**Description:**

Integrate the existing marketplace deduplication engine into the discovery service to detect content-identical and similar artifacts. This requires:

1. Reuse `skillmeat/core/marketplace/deduplication_engine.py` to compute hashes
2. Use `skillmeat/core/marketplace/content_hash.py` to generate artifact hashes
3. Compare discovered artifacts against collection artifacts
4. Track match type: exact (hash match), partial (name+type match), or none
5. Include match metadata in discovery response
6. Optimize for performance: <500ms for 100+ artifacts

**Acceptance Criteria:**

- ✓ Discovery service uses marketplace deduplication engine
- ✓ Content hash computed for each discovered artifact
- ✓ Hash compared against all collection artifacts
- ✓ Exact hash match detected (content-identical)
- ✓ Partial name+type match detected (different content, same identity)
- ✓ Match confidence score calculated (0.0-1.0)
- ✓ Discovery response includes collection_match object per artifact:
  - type: "exact" | "hash" | "name_type" | "none"
  - matched_artifact_id: ID of matched collection artifact (if match found)
  - matched_name: Name of matched artifact
  - confidence: 0.0-1.0 confidence score
- ✓ Hash matching completes <500ms for typical 100+ artifact collection
- ✓ No artifacts modified during hash computation
- ✓ Unit tests for hash matching: exact match, partial match, no match
- ✓ Integration test: 10 discovered (3 exact, 2 partial, 5 new) → correct matches

**Files to Modify:**

| File | Changes | Reason |
|------|---------|--------|
| `skillmeat/core/discovery.py` | Integrate hash matching, add to response | Core discovery logic |
| `skillmeat/api/routers/artifacts.py` | Pass collection to discovery service | Route handler |
| `skillmeat/api/schemas/discovery.py` | Add collection_match schema to response | Response type definition |

**Implementation Notes:**

**Integration Pattern:**
```python
from skillmeat.core.marketplace.deduplication_engine import DeduplicationEngine
from skillmeat.core.marketplace.content_hash import compute_artifact_hash

def discover_artifacts(self, collection=None) -> List[Dict]:
    """Discover artifacts with hash-based deduplication."""

    artifacts = []
    dedup_engine = DeduplicationEngine()

    for artifact_path in self._find_artifacts():
        metadata = self._parse_artifact_metadata(artifact_path)
        content_hash = compute_artifact_hash(artifact_path)

        collection_match = None
        if collection:
            # Exact hash match
            for col_artifact in collection.artifacts:
                if col_artifact.get('content_hash') == content_hash:
                    collection_match = {
                        "type": "exact",
                        "matched_artifact_id": col_artifact['id'],
                        "matched_name": col_artifact['name'],
                        "confidence": 1.0
                    }
                    break

            # Partial name+type match (if no exact match)
            if not collection_match:
                for col_artifact in collection.artifacts:
                    if (col_artifact.get('name') == metadata['name'] and
                        col_artifact.get('type') == metadata['type']):
                        collection_match = {
                            "type": "name_type",
                            "matched_artifact_id": col_artifact['id'],
                            "matched_name": col_artifact['name'],
                            "confidence": 0.85  # Partial match confidence
                        }
                        break

        artifacts.append({
            **metadata,
            "content_hash": content_hash,
            "collection_match": collection_match or {
                "type": "none",
                "matched_artifact_id": None,
                "confidence": 0.0
            }
        })

    return artifacts
```

**Response Schema:**
```json
{
  "artifacts": [
    {
      "path": "/path/to/artifact",
      "name": "awesome-skill",
      "type": "skill",
      "content_hash": "sha256_hash_abc123",
      "discovered_at": "2026-01-09T20:15:03.256Z",
      "collection_status": {
        "in_collection": true,
        "match_type": "exact"
      },
      "collection_match": {
        "type": "exact",
        "matched_artifact_id": "col_id_123",
        "matched_name": "awesome-skill",
        "confidence": 1.0
      }
    }
  ]
}
```

**Performance Optimization:**
- Hash computation in parallel (thread pool)
- Cache hashes for repeated runs
- Short-circuit on exact match (don't check partial if exact found)
- Lazy load collection artifacts if large collection

**Testing Plan:**

| Test Case | Setup | Expected Result |
|-----------|-------|-----------------|
| Exact hash match | Discovered artifact with same content as collection | type: "exact", confidence: 1.0 |
| Partial name+type match | Same name/type, different content | type: "name_type", confidence: 0.85 |
| No match | Artifact not in collection | type: "none", confidence: 0.0 |
| Multiple matches (take first exact) | Exact + partial both possible | Returns exact match only |
| Performance: 100 artifacts | Collection of 100 artifacts | <500ms total time |

---

### Task P2-T2: Backend - Implement Duplicate Review Decision Endpoint

**Task ID:** P2-T2
**Assigned To:** `python-backend-engineer`
**Model:** Opus
**Story Points:** 5
**Dependencies:** P2-T1 (hash matching working)
**Estimated Time:** 3-4 hours implementation + 1.5 hours testing

**Description:**

Create a new backend endpoint to process user decisions from the duplicate review modal. This endpoint receives:
- List of confirmed duplicate links
- List of new artifacts to import
- List of artifacts to skip

And performs:
- Create duplicate link relationships in collection metadata
- Import marked-as-new artifacts
- Skip confirmed duplicates
- Record audit log of all decisions

**Acceptance Criteria:**

- ✓ New endpoint: POST /api/v1/artifacts/confirm-duplicates
- ✓ Endpoint accepts project_path, matches list, new_artifacts list, skipped list
- ✓ Validates input (all artifacts exist, proper types)
- ✓ Processes matches: creates duplicate link relationships in collection metadata
- ✓ Processes new: imports marked-as-new artifacts to collection
- ✓ Processes skipped: marks artifacts as reviewed/skipped (don't re-show)
- ✓ Returns 200 with summary: linked_count, imported_count, skipped_count
- ✓ Idempotent: calling twice with same data doesn't create duplicates
- ✓ Audit log records all decisions with timestamp and user context
- ✓ All collection metadata updates are atomic (no partial state)
- ✓ Unit tests: link creation, import handling, skip logic
- ✓ Integration test: Process 3 matches, 1 import, 1 skip → collection updated correctly

**Files to Modify:**

| File | Changes | Reason |
|------|---------|--------|
| `skillmeat/api/routers/artifacts.py` | Add POST /confirm-duplicates endpoint | New HTTP handler |
| `skillmeat/core/collection.py` | Add method to link duplicate artifacts | Duplicate link storage |
| `skillmeat/core/importer.py` | Use existing import logic for new artifacts | Reuse import logic |
| `skillmeat/api/schemas/discovery.py` | Add ConfirmDuplicatesRequest/Response schemas | Request/response types |

**Implementation Notes:**

**Endpoint Handler:**
```python
@router.post("/confirm-duplicates", status_code=200)
async def confirm_duplicates(
    request: ConfirmDuplicatesRequest,
    collection_mgr: CollectionManagerDep,
    importer: ImporterDep,
    logger: Logger = Depends(get_logger),
) -> ConfirmDuplicatesResponse:
    """Process duplicate review decisions and update collection."""

    linked_count = 0
    imported_count = 0
    skipped_count = 0

    # Process duplicate links
    for match in request.matches:
        try:
            collection_mgr.link_duplicates(
                discovered_path=match.discovered_path,
                collection_artifact_id=match.collection_artifact_id
            )
            linked_count += 1
            logger.info(f"Linked duplicate: {match.discovered_path} -> {match.collection_artifact_id}")
        except Exception as e:
            logger.error(f"Failed to link duplicate: {e}")

    # Process new artifacts
    for artifact_path in request.new_artifacts:
        try:
            importer.import_artifact(artifact_path)
            imported_count += 1
            logger.info(f"Imported new artifact: {artifact_path}")
        except Exception as e:
            logger.error(f"Failed to import artifact {artifact_path}: {e}")

    # Process skipped
    skipped_count = len(request.skipped)
    for artifact_path in request.skipped:
        logger.info(f"Skipped artifact: {artifact_path}")

    return ConfirmDuplicatesResponse(
        status="success",
        linked_count=linked_count,
        imported_count=imported_count,
        skipped_count=skipped_count,
        message=f"{linked_count} duplicates linked, {imported_count} new artifacts imported, {skipped_count} skipped"
    )
```

**Duplicate Link Storage (Collection):**
```python
def link_duplicates(self, discovered_path: str, collection_artifact_id: str):
    """Create link between discovered artifact and collection artifact."""

    # Add to target artifact's duplicate_links
    for artifact in self.artifacts:
        if artifact['id'] == collection_artifact_id:
            if 'duplicate_links' not in artifact:
                artifact['duplicate_links'] = []

            # Only add if not already linked
            if discovered_path not in artifact['duplicate_links']:
                artifact['duplicate_links'].append(discovered_path)

            self._save_manifest()  # Atomic save
            return

    raise ValueError(f"Artifact {collection_artifact_id} not found in collection")
```

**Request/Response Schemas:**
```python
class DuplicateMatch(BaseModel):
    discovered_path: str
    collection_artifact_id: str
    action: str = "link"

class ConfirmDuplicatesRequest(BaseModel):
    project_path: str
    matches: List[DuplicateMatch]
    new_artifacts: List[str]
    skipped: List[str]

class ConfirmDuplicatesResponse(BaseModel):
    status: str  # "success" | "partial" | "failed"
    linked_count: int
    imported_count: int
    skipped_count: int
    message: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
```

**Testing Plan:**

| Test Case | Setup | Expected Result |
|-----------|-------|-----------------|
| Link duplicate | Discovered + collection artifact IDs | Duplicate link created |
| Import new | Artifact path | Artifact imported to collection |
| Skip artifact | Artifact path | Logged, not imported |
| Mixed decision | 2 links, 1 import, 1 skip | All processed correctly |
| Idempotency | Call same endpoint twice | No duplicate links created |

---

### Task P2-T3: Frontend - Filter and Group Discovered Artifacts

**Task ID:** P2-T3
**Assigned To:** `ui-engineer-enhanced`
**Model:** Opus
**Story Points:** 5
**Dependencies:** P2-T1 (backend hash matching)
**Estimated Time:** 3-4 hours implementation + 1.5 hours testing

**Description:**

Update the Discovery tab component to display artifacts in groups based on collection match status:
- "New Artifacts" - not in collection, ready to import
- "Possible Duplicates in Collection" - name+type or content-similar matches
- "Exact Matches" - content-identical artifacts already in collection

Also add filtering controls to show/hide groups.

**Acceptance Criteria:**

- ✓ Discovery tab filters artifacts into three groups by match type
- ✓ "New Artifacts" group shows only artifacts with match_type: "none"
- ✓ "Possible Duplicates" group shows artifacts with match_type: "name_type" or "hash"
- ✓ "Exact Matches" group shows artifacts with match_type: "exact"
- ✓ Each group shows count: "New Artifacts (5)"
- ✓ Exact matches hidden from "Ready to Import" by default
- ✓ Possible duplicates shown with matched artifact reference
- ✓ Toggle button to show/hide exact matches
- ✓ "Review Discovered Artifacts" button visible when duplicates exist
- ✓ Button opens duplicate review modal (P2-T4)
- ✓ Clean UI with visual distinction between groups
- ✓ Responsive on mobile (tested at 375px)
- ✓ Unit tests for grouping logic
- ✓ Integration test: 10 artifacts (3 exact, 2 partial, 5 new) → correct grouping

**Files to Modify:**

| File | Changes | Reason |
|------|---------|--------|
| `skillmeat/web/components/discovery/DiscoveryTab.tsx` | Add grouping logic, display groups | Main discovery UI |
| `skillmeat/web/hooks/useProjectDiscovery.ts` | If needed, pass match data to component | Mutation hook |
| `skillmeat/web/types/discovery.ts` | Add/update types for collection_match | Type definitions |

**Implementation Notes:**

**Grouping Component:**
```typescript
interface GroupedArtifacts {
  new: DiscoveredArtifact[];
  possible_duplicates: DiscoveredArtifact[];
  exact_matches: DiscoveredArtifact[];
}

function groupArtifacts(artifacts: DiscoveredArtifact[]): GroupedArtifacts {
  return {
    new: artifacts.filter(a => a.collection_match?.type === 'none'),
    possible_duplicates: artifacts.filter(
      a => a.collection_match?.type === 'name_type' || a.collection_match?.type === 'hash'
    ),
    exact_matches: artifacts.filter(a => a.collection_match?.type === 'exact'),
  };
}

export function DiscoveryTab({ artifacts }: Props) {
  const [showExactMatches, setShowExactMatches] = useState(false);
  const grouped = groupArtifacts(artifacts);
  const hasDuplicates = grouped.possible_duplicates.length > 0 || grouped.exact_matches.length > 0;

  return (
    <div className="space-y-6">
      {/* New Artifacts Section */}
      <div>
        <h3 className="text-lg font-semibold">
          New Artifacts ({grouped.new.length})
        </h3>
        <div className="space-y-2">
          {grouped.new.map(artifact => (
            <ArtifactCard key={artifact.path} artifact={artifact} />
          ))}
        </div>
      </div>

      {/* Possible Duplicates Section */}
      {grouped.possible_duplicates.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded p-4">
          <h3 className="text-lg font-semibold text-yellow-900">
            Possible Duplicates in Collection ({grouped.possible_duplicates.length})
          </h3>
          <p className="text-sm text-yellow-700 mb-3">
            These artifacts might already be in your collection.
            Review them in the duplicate detection modal.
          </p>
          <div className="space-y-2">
            {grouped.possible_duplicates.map(artifact => (
              <div key={artifact.path} className="bg-white p-3 rounded border border-yellow-200">
                <div className="flex justify-between">
                  <div>
                    <div className="font-medium">{artifact.name}</div>
                    <div className="text-sm text-gray-600">{artifact.type}</div>
                  </div>
                  <div className="text-sm text-gray-600">
                    Matches: {artifact.collection_match?.matched_name}
                    ({(artifact.collection_match?.confidence || 0) * 100}%)
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Exact Matches Section (toggleable) */}
      {grouped.exact_matches.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded p-4">
          <button
            onClick={() => setShowExactMatches(!showExactMatches)}
            className="flex items-center gap-2 text-blue-900 font-semibold"
          >
            {showExactMatches ? '▼' : '▶'} Exact Matches in Collection ({grouped.exact_matches.length})
          </button>
          {showExactMatches && (
            <div className="mt-3 space-y-2">
              {grouped.exact_matches.map(artifact => (
                <div key={artifact.path} className="bg-white p-3 rounded border border-blue-200">
                  <div className="flex justify-between">
                    <div>
                      <div className="font-medium">{artifact.name}</div>
                      <div className="text-xs text-gray-600">{artifact.path}</div>
                    </div>
                    <div className="text-sm text-gray-600">
                      Exact match: {artifact.collection_match?.matched_name}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3 pt-4">
        {hasDuplicates && (
          <button
            onClick={() => openDuplicateReviewModal()}
            className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700"
          >
            Review Discovered Artifacts
          </button>
        )}
        <button
          onClick={() => bulkImportNewOnly(grouped.new)}
          disabled={grouped.new.length === 0}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-300"
        >
          Import New Artifacts ({grouped.new.length})
        </button>
      </div>
    </div>
  );
}
```

**Testing Plan:**

| Test Case | Setup | Expected Result |
|-----------|-------|-----------------|
| Grouping: 10 artifacts (3 exact, 2 partial, 5 new) | Mixed artifacts | Correct group assignment |
| Display: "New Artifacts" | 5 new artifacts | Shows "New Artifacts (5)" |
| Display: "Possible Duplicates" | 2 partial matches | Shows section with count |
| Display: "Exact Matches" | 3 exact matches | Shows section, hidden by default |
| Toggle: Show/hide exact matches | Click toggle button | Exact matches appear/disappear |
| Button: Review Duplicates | Duplicates exist | Button visible and clickable |
| Mobile responsive | Viewport 375px | Groups readable, buttons clickable |

---

### Task P2-T4: Frontend - Build Duplicate Review Modal

**Task ID:** P2-T4
**Assigned To:** `ui-engineer-enhanced`
**Model:** Opus
**Story Points:** 6
**Dependencies:** P2-T1 (backend hash matching), P2-T2 (decision endpoint)
**Estimated Time:** 4-5 hours implementation + 2 hours testing

**Description:**

Create a comprehensive duplicate review modal component with three tabs for reviewing discovered artifacts against collection artifacts. Users can confirm matches, mark as new, or skip artifacts.

**Acceptance Criteria:**

- ✓ Modal title: "Review Discovered Artifacts"
- ✓ Shows summary: "5 new artifacts, 2 possible duplicates, 3 exact matches"
- ✓ Three tabs: "New Artifacts", "Possible Duplicates", "Exact Matches"
- ✓ Tab: "New Artifacts"
  - Shows list of unmatched artifacts
  - Simple preview: name, type, path
  - Bulk action: "Import All" button
  - Per-artifact toggle: "Skip this artifact"
- ✓ Tab: "Possible Duplicates"
  - Left panel: Discovered artifact (name, type, path, preview)
  - Right panel: Matched artifact info + dropdown to select different match
  - Pre-selected match (highest confidence)
  - Can change matched artifact or mark as "Not a duplicate"
  - Per-artifact toggles: "Skip", "Mark as New"
- ✓ Tab: "Exact Matches"
  - List of content-identical artifacts
  - Matched collection artifact shown
  - Option to create link or skip
- ✓ Action buttons:
  - "Confirm Matches" - link duplicates, skip confirmed
  - "Import New Only" - import only artifacts marked as new
  - "Cancel" - close without changes
- ✓ Artifact content preview (truncated file content)
- ✓ Modal responsive on mobile (90%+ viewport, scrollable)
- ✓ Keyboard navigation: Tab, Enter, Escape
- ✓ Loading state while processing decisions
- ✓ Success message after processing
- ✓ Error handling with clear messages
- ✓ Unit tests for tab switching, decision tracking
- ✓ Integration test: Modal workflow (review → decide → submit) completes successfully

**Files to Create:**

| File | Purpose |
|------|---------|
| `skillmeat/web/components/discovery/DuplicateReviewModal.tsx` | **NEW** Main modal component |
| `skillmeat/web/components/discovery/DuplicateReviewTab.tsx` | **NEW** Duplicate review tab |
| `skillmeat/web/hooks/useDuplicateReview.ts` | **NEW** Hook for modal state (optional) |

**Implementation Notes:**

**Modal Structure:**
```typescript
export interface DuplicateReviewState {
  matches: Map<string, string>;  // discovered_path -> collection_id
  newArtifacts: Set<string>;     // discovered_path
  skipped: Set<string>;          // discovered_path
}

export function DuplicateReviewModal({
  artifacts,
  onConfirm,
  onClose,
}: Props) {
  const [activeTab, setActiveTab] = useState<'new' | 'possible' | 'exact'>('possible');
  const [decisions, setDecisions] = useState<DuplicateReviewState>({
    matches: new Map(),
    newArtifacts: new Set(),
    skipped: new Set(),
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const grouped = groupArtifacts(artifacts);
  const summary = {
    new: grouped.new.length,
    possible: grouped.possible_duplicates.length,
    exact: grouped.exact_matches.length,
  };

  const handleConfirm = async () => {
    setIsSubmitting(true);
    try {
      await onConfirm({
        matches: Array.from(decisions.matches.entries()).map(([path, id]) => ({
          discovered_path: path,
          collection_artifact_id: id,
        })),
        new_artifacts: Array.from(decisions.newArtifacts),
        skipped: Array.from(decisions.skipped),
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogHeader>
        <DialogTitle>Review Discovered Artifacts</DialogTitle>
        <DialogDescription>
          {summary.new} new artifacts, {summary.possible} possible duplicates, {summary.exact} exact matches
        </DialogDescription>
      </DialogHeader>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        {/* New Artifacts Tab */}
        <TabsContent value="new">
          <NewArtifactsPanel artifacts={grouped.new} decisions={decisions} onChange={setDecisions} />
        </TabsContent>

        {/* Possible Duplicates Tab */}
        <TabsContent value="possible">
          <DuplicateReviewTab
            artifacts={grouped.possible_duplicates}
            decisions={decisions}
            onChange={setDecisions}
          />
        </TabsContent>

        {/* Exact Matches Tab */}
        <TabsContent value="exact">
          <ExactMatchesPanel artifacts={grouped.exact_matches} decisions={decisions} onChange={setDecisions} />
        </TabsContent>
      </Tabs>

      <DialogFooter>
        <Button variant="outline" onClick={onClose} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button
          onClick={() => handleConfirm()}
          disabled={isSubmitting}
          loading={isSubmitting}
        >
          Confirm Matches
        </Button>
      </DialogFooter>
    </Dialog>
  );
}
```

**Duplicate Review Tab Component:**
```typescript
export function DuplicateReviewTab({
  artifacts,
  decisions,
  onChange,
}: {
  artifacts: DiscoveredArtifact[];
  decisions: DuplicateReviewState;
  onChange: (state: DuplicateReviewState) => void;
}) {
  const [selectedArtifactIndex, setSelectedArtifactIndex] = useState(0);
  const artifact = artifacts[selectedArtifactIndex];

  const handleSelectMatch = (collectionId: string) => {
    const newDecisions = { ...decisions };
    newDecisions.matches.set(artifact.path, collectionId);
    onChange(newDecisions);
  };

  const handleToggleSkip = () => {
    const newDecisions = { ...decisions };
    if (newDecisions.skipped.has(artifact.path)) {
      newDecisions.skipped.delete(artifact.path);
    } else {
      newDecisions.skipped.add(artifact.path);
    }
    onChange(newDecisions);
  };

  return (
    <div className="grid grid-cols-[300px_1fr] gap-4">
      {/* Artifact List */}
      <div className="border rounded overflow-y-auto max-h-96">
        {artifacts.map((art, idx) => (
          <button
            key={art.path}
            onClick={() => setSelectedArtifactIndex(idx)}
            className={`w-full text-left p-3 border-b hover:bg-gray-50 ${
              idx === selectedArtifactIndex ? 'bg-blue-50 border-l-4 border-l-blue-600' : ''
            }`}
          >
            <div className="font-medium text-sm">{art.name}</div>
            <div className="text-xs text-gray-600">{art.type}</div>
          </button>
        ))}
      </div>

      {/* Artifact Details & Match Selection */}
      {artifact && (
        <div className="space-y-4">
          <div>
            <h4 className="font-semibold mb-2">Discovered Artifact</h4>
            <div className="bg-gray-50 p-3 rounded text-sm space-y-1">
              <div><strong>Name:</strong> {artifact.name}</div>
              <div><strong>Type:</strong> {artifact.type}</div>
              <div><strong>Path:</strong> <code className="text-xs bg-gray-200 px-2 py-1">{artifact.path}</code></div>
              <div><strong>Hash:</strong> {artifact.content_hash?.substring(0, 16)}...</div>
            </div>
          </div>

          <div>
            <h4 className="font-semibold mb-2">Collection Match</h4>
            <select
              value={decisions.matches.get(artifact.path) || artifact.collection_match?.matched_artifact_id || ''}
              onChange={(e) => handleSelectMatch(e.target.value)}
              className="w-full border rounded p-2"
            >
              <option value="">-- Select a match or mark as new --</option>
              {/* Populate with matching collection artifacts of same type */}
            </select>
            {artifact.collection_match && (
              <div className="text-sm text-gray-600 mt-1">
                Match confidence: {(artifact.collection_match.confidence * 100).toFixed(0)}%
              </div>
            )}
          </div>

          <div className="space-y-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={decisions.skipped.has(artifact.path)}
                onChange={handleToggleSkip}
              />
              <span className="text-sm">Skip this artifact</span>
            </label>
          </div>
        </div>
      )}
    </div>
  );
}
```

**Testing Plan:**

| Test Case | Setup | Expected Result |
|-----------|-------|-----------------|
| Modal opens | Click "Review" button | Modal shows with correct summary |
| Tab switching | Click tabs | Correct content displayed per tab |
| Artifact selection | Click artifact in list | Details shown on right panel |
| Match selection | Select from dropdown | Match updated in decisions |
| Toggle skip | Click skip checkbox | Artifact marked as skipped |
| Confirm workflow | Make decisions, click Confirm | API called, modal closes |
| Mobile responsive | Viewport 375px | Content scrollable, readable |
| Keyboard navigation | Tab key | Focus moves through fields |
| Escape key | Press Escape | Modal closes |

---

## Phase 2 Summary

| Task | Effort | Status | Owner |
|------|--------|--------|-------|
| P2-T1: Hash-based dedup | 6 pts | Ready | python-backend-engineer |
| P2-T2: Decision endpoint | 5 pts | Ready | python-backend-engineer |
| P2-T3: Discovery filtering | 5 pts | Ready | ui-engineer-enhanced |
| P2-T4: Duplicate modal | 6 pts | Ready | ui-engineer-enhanced |
| **Total Phase 2** | **22 pts** | Ready | 2 engineers |

**Phase 2 Exit Criteria:**
- [ ] All 4 tasks completed and tested
- [ ] Hash matching accuracy ≥95%
- [ ] Discovery filtering correctly groups artifacts
- [ ] Duplicate review modal UX tested
- [ ] Decision processing persists to collection
- [ ] QA sign-off on all acceptance criteria
- [ ] Ready for Phase 3

---

## Parallel Execution Plan

Tasks P2-T1 and P2-T2 can run in parallel (both backend, independent):
- **Week 1:** P2-T1 and P2-T2 progress simultaneously
- **Week 1-2:** P2-T3 and P2-T4 start after P2-T1 backend API stabilized
- **Week 2:** Integration testing and QA

**Recommended Sequence:**
1. Day 1-2: P2-T1 and P2-T2 started in parallel
2. Day 3: P2-T1 complete, P2-T3 starts (depends on hash matching)
3. Day 4: P2-T2 complete (decision endpoint)
4. Day 5-9: P2-T3 and P2-T4 progress in parallel
5. Day 10: Integration testing and QA

**Next Phase Gate:**
Phase 3 can start immediately (doesn't depend on Phase 2) but should wait for Phase 1 stability verification.
