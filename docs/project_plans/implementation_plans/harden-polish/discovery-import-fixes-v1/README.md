# Discovery & Import Fixes Implementation Plan - Phase Details

This directory contains detailed implementation plans for the three phases of the Discovery & Import Fixes project.

## Overview

See the main plan document: `../discovery-import-fixes-v1.md`

**Project:** Discovery & Import Fixes and Enhancements
**PRD:** `docs/project_plans/PRDs/harden-polish-discovery-import-fixes-v1.md`
**Request Log:** REQ-20260109-skillmeat (5 items)
**Total Effort:** 45-55 story points across 3 phases
**Timeline:** 5-6 weeks

## Phase Files

### Phase 1: Bug Fixes & Stabilization
**File:** `phase-1-bug-fixes.md`
**Duration:** 2 weeks | **Effort:** 12-16 story points | **Priority:** CRITICAL

**Tasks:**
- P1-T1: Backend artifact validation & graceful error handling (5 pts)
- P1-T2: Collection membership query implementation (4 pts)
- P1-T3: Discovery timestamp tracking fix (3 pts)
- P1-T4: Frontend status display & results (5 pts)

**Goals:**
- Eliminate bulk import 422 errors
- Fix "Already in Collection" status accuracy
- Display valid discovery timestamps
- Stabilize workflow for all artifact types

### Phase 2: Duplicate Detection & Review Workflow
**File:** `phase-2-duplicate-detection.md`
**Duration:** 2 weeks | **Effort:** 18-22 story points | **Priority:** HIGH
**Depends On:** Phase 1 completion

**Tasks:**
- P2-T1: Hash-based deduplication integration (6 pts)
- P2-T2: Duplicate review decision endpoint (5 pts)
- P2-T3: Discovery artifact filtering & grouping (5 pts)
- P2-T4: Duplicate review modal UI (6 pts)

**Goals:**
- Implement hash-based duplicate detection
- Add discovery filtering and artifact grouping
- Create duplicate review workflow modal
- Process and persist review decisions

### Phase 3: Deployment UX Improvements
**File:** `phase-3-deploy-button.md`
**Duration:** 1 week | **Effort:** 6-8 story points | **Priority:** MEDIUM
**Depends On:** Phase 1 completion

**Tasks:**
- P3-T1: Add deploy button to Entity Modal (2 pts)
- P3-T2: Add deploy option to Collection view (2 pts)
- P3-T3: Verify unified dialog consistency (2 pts)

**Goals:**
- Add deployment entry point in Entity Modal
- Add deployment entry point in Collection view
- Unify dialog across all entry points
- Reduce context switching in workflow

## Quick Navigation

### By Task ID
- **P1-T1:** Backend artifact validation → phase-1-bug-fixes.md
- **P1-T2:** Collection membership query → phase-1-bug-fixes.md
- **P1-T3:** Timestamp tracking → phase-1-bug-fixes.md
- **P1-T4:** Frontend status display → phase-1-bug-fixes.md
- **P2-T1:** Hash-based deduplication → phase-2-duplicate-detection.md
- **P2-T2:** Decision endpoint → phase-2-duplicate-detection.md
- **P2-T3:** Discovery filtering → phase-2-duplicate-detection.md
- **P2-T4:** Duplicate modal → phase-2-duplicate-detection.md
- **P3-T1:** Modal deploy button → phase-3-deploy-button.md
- **P3-T2:** Collection deploy option → phase-3-deploy-button.md
- **P3-T3:** Dialog consistency → phase-3-deploy-button.md

### By Subagent
**python-backend-engineer (Opus):**
- P1-T1, P1-T2, P1-T3, P2-T1, P2-T2

**ui-engineer-enhanced (Opus):**
- P1-T4, P2-T3, P2-T4, P3-T1, P3-T2, P3-T3

### By Priority
**CRITICAL:** P1-T1, P1-T2, P1-T3, P1-T4 (Phase 1 - all)
**HIGH:** P2-T1, P2-T2, P2-T3, P2-T4 (Phase 2 - all)
**MEDIUM:** P3-T1, P3-T2, P3-T3 (Phase 3 - all)

## Key Files & Components

### Backend Files Modified

| Phase | Files |
|-------|-------|
| Phase 1 | `skillmeat/core/discovery.py`, `skillmeat/core/importer.py`, `skillmeat/core/collection.py`, `skillmeat/api/routers/artifacts.py` |
| Phase 2 | `skillmeat/core/discovery.py`, `skillmeat/api/routers/artifacts.py` (new endpoint) |
| Phase 3 | Frontend only |

### Frontend Files Modified

| Phase | Files |
|-------|-------|
| Phase 1 | `skillmeat/web/hooks/useProjectDiscovery.ts`, `skillmeat/web/components/discovery/BulkImportModal.tsx`, `skillmeat/web/components/discovery/DiscoveryTab.tsx` |
| Phase 2 | `skillmeat/web/components/discovery/DiscoveryTab.tsx` (NEW: `DuplicateReviewModal.tsx`, `DuplicateReviewTab.tsx`) |
| Phase 3 | `skillmeat/web/components/artifacts/UnifiedEntityModal.tsx`, `skillmeat/web/components/collections/*.tsx` |

## Quality Gates

### Phase 1 Quality Gate
- [ ] Zero 422 errors on bulk import
- [ ] Status display 100% accurate
- [ ] All timestamps valid
- [ ] API response <2 seconds
- [ ] ≥85% test coverage
- [ ] QA sign-off

### Phase 2 Quality Gate
- [ ] Hash matching ≥95% accuracy
- [ ] Duplicate detection 100% effective
- [ ] Modal UX tested and validated
- [ ] Duplicate links persisted
- [ ] Full integration test passes
- [ ] QA sign-off

### Phase 3 Quality Gate
- [ ] Deploy button visible in 3 entry points
- [ ] Dialog unified (no duplicates)
- [ ] Full workflow tested
- [ ] Mobile responsive
- [ ] QA sign-off

## Timeline

### Week 1-2: Phase 1 (Bug Fixes)
- Days 1-9: Implementation and testing
- Day 10: QA and bug fixes
- Day 11: Phase 1 sign-off

### Week 3-4: Phase 2 (Duplicate Detection)
- Days 1-9: Implementation and testing
- Day 10: QA and bug fixes
- Day 11: Phase 2 sign-off

### Week 5: Phase 3 (Deployment UX)
- Days 1-4: Implementation and testing
- Days 5: QA and bug fixes
- Day 6: Phase 3 sign-off and project closure

## Execution Model

**Track:** Full Track (Large Project)
- Opus-powered agents for complex logic
- Sonnet-powered agents for well-scoped tasks
- Haiku-powered agents for mechanical work (validation, testing)

**Parallel Execution:**
- Phase 1: P1-T1, P1-T2, P1-T3 run in parallel (independent backend)
- Phase 2: P2-T1, P2-T2 run in parallel; P2-T3, P2-T4 follow
- Phase 3: All tasks run in parallel (independent frontend)

## Getting Started

1. **Read the main plan:** `../discovery-import-fixes-v1.md`
2. **Review Phase 1 plan:** `phase-1-bug-fixes.md`
3. **Identify subagent assignments:** See main plan Appendix
4. **Start Phase 1 tasks:** Use artifact-tracker for progress
5. **Monitor completion:** Track via phase exit criteria

## Success Metrics

**Phase 1:** 100% success rate on bulk import, zero 422 errors
**Phase 2:** ≥95% hash matching accuracy, <2 min per duplicate review
**Phase 3:** Deploy button available from 3 entry points, 100% success rate

## Questions & Escalation

### Design Decisions Pending (From PRD)
- Duplicate link representation in manifest
- Hash matching confidence threshold
- Timestamp precision (ISO 8601 vs Unix)
- Dialog pre-selection API contract

### Blockers or Issues
- Report in task comments with severity
- Escalate to Opus for complex issues
- Document in progress YAML

---

**Document Status:** Ready for Implementation
**Last Updated:** 2026-01-09
**Created By:** Claude Code (Orchestrator)
