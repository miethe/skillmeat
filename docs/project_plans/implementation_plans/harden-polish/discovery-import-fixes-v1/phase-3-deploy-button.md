---
title: 'Phase 3 Implementation: Deployment UX Improvements'
description: Detailed task breakdown for adding deployment entry points to Entity
  Modal and Collection view
parent: discovery-import-fixes-v1.md
phase: 3
duration: 1 week
effort: 6-8 story points
priority: MEDIUM
depends_on: phase-1-bug-fixes.md
status: inferred_complete
schema_version: 2
doc_type: phase_plan
feature_slug: discovery-import-fixes
prd_ref: null
plan_ref: null
---
# Phase 3: Deployment UX Improvements

**Duration:** 1 week | **Effort:** 6-8 story points | **Priority:** MEDIUM | **Depends On:** Phase 1 completion

**Objectives:**
- Add deployment entry point in Entity Modal Deployments tab
- Add deployment entry point in Collection view
- Unify deployment dialog across all entry points
- Reduce context switching in discovery → import → deploy workflow

---

## Phase 3 Task Breakdown

### Task P3-T1: Frontend - Add Deploy Button to Entity Modal

**Task ID:** P3-T1
**Assigned To:** `ui-engineer-enhanced`
**Model:** Sonnet (well-scoped UI change)
**Story Points:** 2
**Dependencies:** Phase 1 (stable discovery workflow)
**Estimated Time:** 1.5-2 hours implementation + 1 hour testing

**Description:**

Add a "Deploy to Project" button to the Entity Modal's Deployments tab. When clicked, it should open the existing "Add to Project" dialog with the current artifact pre-selected, allowing users to deploy without leaving the modal.

**Acceptance Criteria:**

- ✓ Button "Deploy to Project" or "Add to Project" visible in Deployments tab header (top right)
- ✓ Button position: top right of tab content area
- ✓ Button visible only when viewing an artifact (modal is open with artifact selected)
- ✓ Button click opens "Add to Project" dialog
- ✓ Dialog pre-selects current artifact (user can change if desired)
- ✓ User can select target project from dropdown
- ✓ User confirms deployment location
- ✓ After confirmation, artifact deployed to target project
- ✓ Dialog closes, Deployments tab refreshes to show new deployment
- ✓ Button text and styling consistent with SkillMeat design system
- ✓ Disabled state when artifact cannot be deployed (if applicable)
- ✓ No console errors or warnings
- ✓ Mobile responsive (button visible on narrow screens)
- ✓ Unit tests for button visibility and click handler
- ✓ Integration test: Click button → deploy → artifact appears in Deployments list

**Files to Modify:**

| File | Changes | Reason |
|------|---------|--------|
| `skillmeat/web/components/artifacts/UnifiedEntityModal.tsx` | Add deploy button to Deployments tab | Modal tab container |
| `skillmeat/web/components/artifacts/DeploymentsTab.tsx` | Or directly in this file if separate | Deployments tab content |

**Implementation Notes:**

**Button Placement:**
```typescript
// In UnifiedEntityModal.tsx or DeploymentsTab.tsx
export function DeploymentsTab({ artifact }: Props) {
  return (
    <div className="space-y-4">
      {/* Tab Header with Button */}
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">Deployments</h3>
        <button
          onClick={handleDeployClick}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Deploy to Project
        </button>
      </div>

      {/* Deployments List */}
      <DeploymentsList deployments={deployments} />
    </div>
  );
}

const handleDeployClick = () => {
  // Open "Add to Project" dialog with artifact pre-selected
  openAddToProjectDialog({
    artifactId: artifact.id,
    artifactName: artifact.name,
  });
};
```

**Dialog Integration:**
```typescript
// Assuming AddToProjectDialog or similar component exists
function AddToProjectDialog({
  isOpen,
  preSelectedArtifactId,
  onClose,
  onSuccess,
}: Props) {
  const [selectedArtifactId, setSelectedArtifactId] = useState(preSelectedArtifactId || null);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);

  // User can change artifact if desired
  // Or if pre-selected, use that by default

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogHeader>Add to Project</DialogHeader>
      <DialogContent>
        {/* Artifact selector - pre-filled if passed */}
        <div>
          <label>Artifact</label>
          <select
            value={selectedArtifactId || ''}
            onChange={(e) => setSelectedArtifactId(e.target.value)}
          >
            <option>-- Select Artifact --</option>
            {/* Artifact options */}
          </select>
        </div>

        {/* Project selector */}
        <div>
          <label>Target Project</label>
          <select
            value={selectedProjectId || ''}
            onChange={(e) => setSelectedProjectId(e.target.value)}
          >
            <option>-- Select Project --</option>
            {/* Project options */}
          </select>
        </div>

        {/* Submit button */}
        <button onClick={handleDeploy}>Deploy</button>
      </DialogContent>
    </Dialog>
  );
}
```

**Testing Plan:**

| Test Case | Setup | Expected Result |
|-----------|-------|-----------------|
| Button visible | Deployments tab open | Button appears in top right |
| Button click | Click "Deploy to Project" | Dialog opens with artifact pre-selected |
| Dialog submit | Select project, click Deploy | Artifact deployed, dialog closes |
| Deployment appears | After deploy completes | New deployment shows in Deployments tab |
| Mobile viewport | Viewport 375px | Button visible and clickable |

---

### Task P3-T2: Frontend - Add Deploy Option to Collection View Meatballs Menu

**Task ID:** P3-T2
**Assigned To:** `ui-engineer-enhanced`
**Model:** Sonnet (UI pattern follow)
**Story Points:** 2
**Dependencies:** Phase 1 (collection view stable)
**Estimated Time:** 1.5-2 hours implementation + 1 hour testing

**Description:**

Add a "Deploy to Project" option to the meatballs menu (context menu) for artifacts in the Collection view. Clicking should open the same "Add to Project" dialog with the artifact pre-selected.

**Acceptance Criteria:**

- ✓ Meatballs menu (three-dots) visible on artifact cards in Collection view
- ✓ Menu includes option: "Deploy to Project"
- ✓ Click opens "Add to Project" dialog
- ✓ Dialog pre-selects current artifact
- ✓ Same workflow as P3-T1: select project → confirm → deploy
- ✓ After deploy, menu closes and view refreshes
- ✓ Consistent with other menu options (download, delete, etc.)
- ✓ Works on desktop and mobile long-press
- ✓ Menu doesn't interfere with other options
- ✓ Unit tests for menu option visibility
- ✓ Integration test: Collection view → meatballs menu → Deploy → success

**Files to Modify:**

| File | Changes | Reason |
|------|---------|--------|
| `skillmeat/web/components/collections/ArtifactCard.tsx` | Add deploy option to meatballs menu | Card menu component |
| Or relevant collection component file | Same deploy menu implementation | Collection view artifact display |

**Implementation Notes:**

**Menu Option Addition:**
```typescript
// In ArtifactCard.tsx or similar
export function ArtifactCard({ artifact }: Props) {
  const [menuOpen, setMenuOpen] = useState(false);

  const handleDeployClick = () => {
    setMenuOpen(false);
    openAddToProjectDialog({
      artifactId: artifact.id,
      artifactName: artifact.name,
    });
  };

  return (
    <div className="border rounded p-4 hover:shadow-lg">
      <div className="flex justify-between items-start">
        <div>
          <h4 className="font-semibold">{artifact.name}</h4>
          <p className="text-sm text-gray-600">{artifact.type}</p>
        </div>

        {/* Meatballs Menu */}
        <DropdownMenu open={menuOpen} onOpenChange={setMenuOpen}>
          <DropdownMenuTrigger asChild>
            <button className="text-gray-500 hover:text-gray-700">
              ⋯
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={handleDeployClick}>
              Deploy to Project
            </DropdownMenuItem>
            <DropdownMenuItem onClick={handleDownload}>
              Download
            </DropdownMenuItem>
            <DropdownMenuItem onClick={handleDelete} className="text-red-600">
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Artifact preview, metadata, etc. */}
    </div>
  );
}
```

**Testing Plan:**

| Test Case | Setup | Expected Result |
|-----------|-------|-----------------|
| Menu visible | Hover over artifact card | Meatballs menu visible |
| Menu option | Click menu, see options | "Deploy to Project" is listed |
| Click deploy | Select "Deploy to Project" | Dialog opens with artifact pre-selected |
| Dialog workflow | Complete deployment | Artifact deployed successfully |
| Menu closes | After deploy | Menu closes automatically |

---

### Task P3-T3: Frontend - Verify Unified Dialog Consistency

**Task ID:** P3-T3
**Assigned To:** `ui-engineer-enhanced`
**Model:** Sonnet (verification task)
**Story Points:** 2
**Dependencies:** P3-T1, P3-T2 (both entry points)
**Estimated Time:** 1.5 hours implementation + 1 hour testing

**Description:**

Verify that all three deployment entry points (Entity Modal button, Collection view menu, existing /manage view) use the same "Add to Project" dialog component. Ensure consistency in:
- Dialog behavior and workflow
- Visual styling and branding
- Artifact pre-selection
- Error handling
- Success feedback

This is primarily a code review and refactoring task to ensure no duplicate implementations.

**Acceptance Criteria:**

- ✓ All three entry points (Modal button, Collection menu, /manage button) use same dialog component
- ✓ No duplicate dialog implementations exist in codebase
- ✓ Dialog accepts optional `preSelectedArtifactId` parameter
- ✓ Dialog handles artifact pre-selection consistently across all entry points
- ✓ All entry points use identical error handling
- ✓ Success behavior consistent: dialog closes, view refreshes, artifact appears
- ✓ Styling consistent across all usage contexts
- ✓ Mobile responsive in all contexts
- ✓ Code review confirms single source of truth for dialog logic
- ✓ Unit tests verify dialog behavior in all contexts
- ✓ Integration tests confirm all three paths work identically

**Files to Review/Modify:**

| File | Changes | Reason |
|------|---------|--------|
| `skillmeat/web/components/artifacts/AddToProjectDialog.tsx` | Ensure exists and handles pre-selection | Dialog component (single source of truth) |
| `skillmeat/web/components/artifacts/UnifiedEntityModal.tsx` | Uses dialog (P3-T1) | Modal integration |
| `skillmeat/web/components/collections/*.tsx` | Uses same dialog (P3-T2) | Collection view integration |
| `skillmeat/web/app/manage/page.tsx` | Verify uses same dialog | /manage view integration |

**Implementation Notes:**

**Unified Dialog Component Pattern:**
```typescript
// skillmeat/web/components/artifacts/AddToProjectDialog.tsx
interface AddToProjectDialogProps {
  isOpen: boolean;
  preSelectedArtifactId?: string;
  onClose: () => void;
  onSuccess: (artifact: Artifact, project: Project) => void;
}

export function AddToProjectDialog({
  isOpen,
  preSelectedArtifactId,
  onClose,
  onSuccess,
}: AddToProjectDialogProps) {
  // Single implementation used by all entry points
  // Dialog handles pre-selection, workflow, errors
}
```

**Usage Pattern (All Entry Points):**
```typescript
// Entity Modal button (P3-T1)
const handleDeploy = () => {
  openAddToProjectDialog({
    preSelectedArtifactId: artifact.id,
    onSuccess: handleDeploySuccess,
  });
};

// Collection menu (P3-T2)
const handleDeployClick = () => {
  openAddToProjectDialog({
    preSelectedArtifactId: artifact.id,
    onSuccess: handleDeploySuccess,
  });
};

// /manage view (existing, P3-T3 verify)
const handleDeployButton = () => {
  openAddToProjectDialog({
    preSelectedArtifactId: artifact.id,
    onSuccess: handleDeploySuccess,
  });
};
```

**Testing Plan:**

| Test Case | Setup | Expected Result |
|-----------|-------|-----------------|
| Dialog from Modal | Click Modal deploy button | Dialog opens with artifact pre-selected |
| Dialog from Collection | Click Collection menu deploy | Dialog opens with artifact pre-selected |
| Dialog from /manage | Click /manage deploy button | Dialog opens with artifact pre-selected |
| Same dialog instance | All three entry points | Same component, no duplicates |
| Consistency test | Complete deploy from each | All result in same final state |

---

## Phase 3 Summary

| Task | Effort | Status | Owner |
|------|--------|--------|-------|
| P3-T1: Modal deploy button | 2 pts | Ready | ui-engineer-enhanced |
| P3-T2: Collection menu option | 2 pts | Ready | ui-engineer-enhanced |
| P3-T3: Dialog consistency | 2 pts | Ready | ui-engineer-enhanced |
| **Total Phase 3** | **6 pts** | Ready | 1 engineer |

**Phase 3 Exit Criteria:**
- [ ] All 3 tasks completed and tested
- [ ] Deploy button visible in Entity Modal
- [ ] Deploy option visible in Collection meatballs menu
- [ ] All three entry points use same dialog (no duplicates)
- [ ] Full workflow tested from all entry points
- [ ] QA sign-off on all acceptance criteria
- [ ] Ready for deployment

---

## Parallel Execution Plan

All three tasks can run in parallel (independent frontend work on different components):

**Recommended Sequence:**
1. Day 1-2: P3-T1 (Modal button) and P3-T2 (Collection menu) implemented in parallel
2. Day 3-4: P3-T3 verification and refactoring
3. Day 5: Integration testing and QA

---

## Post-Phase 3 Verification

### Final System Verification (All Phases)

After all three phases are complete, perform comprehensive verification:

**Workflow: Discovery → Import → Deploy**

1. Navigate to Project with artifacts in `.claude/`
2. Open Unified Entity Modal
3. Click Discovery tab
4. See "New Artifacts" vs "Possible Duplicates" vs "Exact Matches" groups
5. Click "Review Discovered Artifacts" (if duplicates exist)
6. Make decisions in duplicate review modal
7. Click "Confirm Matches" (or "Import New Only")
8. See results: N imported, M skipped
9. In Deployments tab, click "Deploy to Project"
10. Select target project and deploy
11. Verify artifact appears in target project `.claude/` directory
12. Verify no context switching required

**Verification Checklist:**

- [ ] Discovery detects artifacts accurately
- [ ] Status shows correct "New" vs "Already in Collection"
- [ ] Timestamps display correctly
- [ ] Bulk import handles invalid artifacts gracefully (no 422)
- [ ] Per-artifact results shown after import
- [ ] Duplicate detection works (hash matching accurate)
- [ ] Duplicate review modal is usable and responsive
- [ ] Deployment succeeds from Entity Modal
- [ ] Deployment succeeds from Collection view
- [ ] All three entry points use same dialog
- [ ] No console errors or warnings
- [ ] Mobile responsive (all screens from 375px-2560px)
- [ ] Keyboard navigation works (Tab, Enter, Escape)
- [ ] User feedback channels in place for edge cases

---

## Success Criteria Summary (All Phases)

### Phase 1 Success Metrics
- [ ] 100% bulk import success rate (no 422 on valid batches)
- [ ] Status display accuracy 100%
- [ ] No invalid timestamps
- [ ] API response time <2 seconds

### Phase 2 Success Metrics
- [ ] Hash matching accuracy ≥95%
- [ ] Duplicate detection rate 100%
- [ ] Duplicate review modal usability (<2 min per artifact)
- [ ] Duplicate links persisted in collection

### Phase 3 Success Metrics
- [ ] Deploy button available from 3 entry points
- [ ] Dialog reuse 100% (no duplicates)
- [ ] User context switches 0 (full workflow in modal)
- [ ] Deployment success 100%

### Overall Success Criteria
- [ ] All 11 tasks completed on time
- [ ] All acceptance criteria met
- [ ] QA sign-off for each phase
- [ ] Zero critical bugs in initial deployment
- [ ] Positive user feedback on UX improvements
- [ ] Zero regression in existing functionality

---

## Appendix: Integration Test Scenario

**Complete End-to-End Test: Discovery → Duplicate Review → Deploy**

**Setup:**
- User has a collection with 3 skills
- Project A contains 8 artifacts (5 new, 2 duplicates, 1 exact match)

**Scenario:**
1. User opens Unified Entity Modal in project context
2. Clicks Discovery tab → sees 8 discovered artifacts
3. Artifacts grouped: "5 New", "2 Possible Duplicates", "1 Exact Match"
4. Clicks "Review Discovered Artifacts"
5. Modal shows three tabs with summary
6. Reviews "Possible Duplicates" tab, confirms matches
7. Clicks "Confirm Matches"
8. Modal closes, Discovery tab refreshes
9. Sees results: "5 imported, 2 linked, 1 skipped"
10. Clicks Deployments tab
11. Clicks "Deploy to Project" button
12. "Add to Project" dialog opens
13. Selects target project
14. Confirms deployment
15. Artifact deployed successfully

**Expected Outcomes:**
- All 5 new artifacts in collection
- 2 duplicates linked to existing artifacts
- 1 exact match skipped
- Artifact deployed to target project
- No 422 errors
- No console errors
- Total time: <30 seconds
- Mobile responsive (tested at 375px and 1024px)

---

## Document Control

| Field | Value |
|-------|-------|
| Created | 2026-01-09 |
| Phase | 3 of 3 |
| Total Effort | 6 story points |
| Duration | 1 week |
| Status | Ready for Implementation |
