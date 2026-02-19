---
title: 'Implementation Plan: Discovery & Import Fixes and Enhancements'
description: Comprehensive implementation plan for stabilizing bulk import, adding
  duplicate detection, and improving deployment UX in SkillMeat discovery workflow
audience:
- ai-agents
- developers
- orchestrators
tags:
- implementation-plan
- discovery
- import
- bulk-operations
- duplicate-detection
- deployment
- harden-polish
created: 2026-01-09
updated: 2026-01-09
category: harden-polish
status: done
prd_reference: docs/project_plans/PRDs/harden-polish-discovery-import-fixes-v1.md
request_log: REQ-20260109-skillmeat
schema_version: 2
doc_type: implementation_plan
feature_slug: discovery-import-fixes
prd_ref: null
---

# Implementation Plan: Discovery & Import Fixes and Enhancements

**Project Type:** Bug Fixes + Feature Enhancements
**Complexity Level:** Large (L) - 3 phases, 11 major tasks, cross-system changes
**Total Estimated Effort:** 45-55 story points
**Target Timeline:** 5-6 weeks (3 phases × 1-2 weeks each)
**Priority:** HIGH (2 critical bugs + 3 value-add enhancements)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Implementation Strategy](#implementation-strategy)
3. [Phase Overview](#phase-overview)
4. [Architecture & Dependencies](#architecture--dependencies)
5. [Risk Assessment](#risk-assessment)
6. [Quality Gates](#quality-gates)
7. [Success Metrics](#success-metrics)
8. [Detailed Phase Plans](#detailed-phase-plans)
9. [Integration & Testing](#integration--testing)
10. [Deployment & Rollout](#deployment--rollout)

---

## Executive Summary

This implementation plan addresses five critical issues in SkillMeat's Project Discovery & Import workflow, enabling developers to reliably discover, import, deduplicate, and deploy artifacts across their collection and projects.

### Problem Statement (From PRD REQ-20260109-skillmeat)

Users experience:
1. **Bulk import failures** with 422 errors on batches containing invalid artifacts
2. **Incorrect collection membership status** showing "Already in Collection" for all discovered artifacts
3. **Invalid timestamps** displaying "-1 days ago" for all discoveries
4. **No duplicate detection** - same artifacts appear as "Ready to Import" on repeated discovery
5. **Fragmented deployment UX** - no "Deploy to Project" button in Entity Modal or Collection view

### Solution Overview

**Phase 1: Stabilization (Bug Fixes)**
- Graceful bulk import error handling with per-artifact status reporting
- Accurate collection membership queries integrated into discovery
- Correct timestamp tracking and display
- Estimated: 12-16 story points, 2 weeks

**Phase 2: Deduplication (Feature)**
- Hash-based duplicate detection using existing marketplace engine
- Discovery tab filtering and artifact grouping
- Dedicated duplicate review modal with decision workflow
- Backend endpoint to process and persist review decisions
- Estimated: 18-22 story points, 2 weeks

**Phase 3: Deployment UX (Enhancement)**
- "Deploy to Project" button in Entity Modal Deployments tab
- Deploy option in Collection view artifact meatballs menu
- Unified dialog across all entry points
- Estimated: 6-8 story points, 1 week

### Key Outcomes

- **Zero 422 failures** on bulk import with invalid artifacts (graceful skip)
- **100% accurate** Collection membership status in UI
- **90% reduction** in user confusion about duplicate/already-imported artifacts
- **Single-click deployment** from Entity Modal and Collection views without navigation

### Target Impact

| Metric | Current | Target | Success Criteria |
|--------|---------|--------|------------------|
| Bulk import success rate | ~60% (fails on invalid artifacts) | 100% (graceful skip) | Zero 422 errors on valid batches with invalid items |
| Status accuracy | 0% (all show "Already in Collection") | 100% | Manual verification matches UI display |
| Duplicate detection | None | 95%+ accuracy | Hash-based matching across all artifact types |
| Deployment UX entry points | 1 (/manage only) | 3 (Modal + Collection + /manage) | All paths complete without context switching |

---

## Implementation Strategy

### Execution Model

**Track Type:** Full Track (Large Project)
- All subagent types utilized (Haiku, Sonnet, Opus)
- Multi-phase orchestration with dependencies
- Parallel task execution within phases, sequential between phases
- Cost optimization through model selection

### Orchestration Approach

```
Phase 1 (Stabilization)
├─ P1-T1: Backend artifact validation (python-backend-engineer, Opus)
├─ P1-T2: Collection membership query (python-backend-engineer, Opus)
├─ P1-T3: Timestamp tracking (python-backend-engineer, Sonnet)
└─ P1-T4: Frontend status display (ui-engineer-enhanced, Opus)

Phase 2 (Deduplication) [depends on Phase 1]
├─ P2-T1: Hash-based deduplication (python-backend-engineer, Opus)
├─ P2-T2: Duplicate decision endpoint (python-backend-engineer, Opus)
├─ P2-T3: Discovery filtering & grouping (ui-engineer-enhanced, Opus)
└─ P2-T4: Duplicate review modal (ui-engineer-enhanced, Opus)

Phase 3 (Deployment UX) [depends on Phase 1]
├─ P3-T1: Entity Modal deploy button (ui-engineer-enhanced, Sonnet)
├─ P3-T2: Collection view deploy option (ui-engineer-enhanced, Sonnet)
└─ P3-T3: Unified dialog consistency (ui-engineer-enhanced, Sonnet)
```

### Parallel Execution Opportunities

**Within Phase 1:**
- P1-T1, P1-T2, P1-T3 can run in parallel (independent backend work)
- P1-T4 depends on P1-T1 + P1-T2 + P1-T3

**Within Phase 2:**
- P2-T1, P2-T2 can run in parallel (both backend, independent)
- P2-T3, P2-T4 depend on P2-T1 backend schema

**Within Phase 3:**
- P3-T1, P3-T2, P3-T3 can run in parallel (all frontend, independent)

### Model Selection Strategy

| Task | Primary Model | Reason |
|------|---------------|--------|
| Backend validation/queries/dedup | Opus | Complex logic, multi-layer architecture |
| Frontend UI components | Opus | Component design, state management complexity |
| Frontend UI updates (atomic) | Sonnet | Well-scoped, following established patterns |
| Testing & integration | Opus | Complex scenarios, edge cases |
| Documentation | Sonnet | Templated, reference materials available |

---

## Phase Overview

### Phase 1: Bug Fixes & Stabilization

**Duration:** 2 weeks | **Effort:** 12-16 story points | **Priority:** CRITICAL

**Goals:**
- Eliminate bulk import 422 errors through graceful validation
- Accurately display Collection membership status
- Fix invalid timestamp display
- Stabilize discovery workflow for all artifact types

**Deliverables:**
- Enhanced bulk import endpoint with partial success response
- Updated discovery response with membership status
- Fixed timestamp tracking in collection metadata
- Frontend UI reflecting accurate status and timestamps
- Full test coverage (unit + integration)

**Success Criteria:**
- Zero 422 errors on bulk import with valid + invalid artifact mix
- All artifacts show correct "Already in Collection" vs "Ready to Import" status
- No "-1 days ago" timestamps anywhere in UI
- 20+ artifacts bulk import completes <2 seconds
- All tests pass, ≥85% code coverage

**Key Files (See Phase 1 Plan):**
- Backend: artifacts.py, discovery.py, importer.py, collection.py
- Frontend: useProjectDiscovery.ts, BulkImportModal.tsx, DiscoveryTab.tsx

---

### Phase 2: Duplicate Detection & Review Workflow

**Duration:** 2 weeks | **Effort:** 18-22 story points | **Priority:** HIGH

**Goals:**
- Implement hash-based duplicate detection
- Add discovery artifact filtering and grouping
- Create duplicate review workflow modal
- Process and persist review decisions

**Deliverables:**
- Discovery endpoint enhanced with hash metadata and collection_status
- Duplicate detection engine integration
- Discovery tab with New/Possible Duplicates/Exact Matches groups
- DuplicateReviewModal component with three tabs
- confirm-duplicates endpoint for decision processing
- Audit logging of duplicate review decisions

**Success Criteria:**
- Hash matching accuracy ≥95% across artifact types
- Exact matches hidden from "Ready to Import" list
- Review modal usable <2 min average per artifact
- Duplicate link relationships persisted in collection metadata
- Full integration test: 10 discovered artifacts (3 exact, 2 partial, 5 new) → correct workflow
- Modal responsive on mobile (90%+ viewport)
- Keyboard navigation functional (Tab, Enter, Escape)

**Depends On:** Phase 1 completion (accurate status foundational)

**Key Files (See Phase 2 Plan):**
- Backend: discovery.py, deduplication_engine.py, content_hash.py, new endpoint
- Frontend: DuplicateReviewModal.tsx, DiscoveryTab.tsx, useProjectDiscovery.ts

---

### Phase 3: Deployment UX Improvements

**Duration:** 1 week | **Effort:** 6-8 story points | **Priority:** MEDIUM

**Goals:**
- Add deployment entry point in Entity Modal
- Add deployment entry point in Collection view
- Unify deployment dialog across all entry points
- Reduce context switching in discovery → import → deploy workflow

**Deliverables:**
- "Deploy to Project" button in Entity Modal Deployments tab
- Meatballs menu "Deploy to Project" option in Collection view
- Updated /manage view button for consistency
- Unified "Add to Project" dialog usage across all entry points

**Success Criteria:**
- Deploy button visible and functional in Entity Modal
- Collection view meatballs menu includes deployment option
- All three entry points use same dialog component (no duplicates)
- Deploy from modal → artifact deployed → no navigation required
- Full integration test: Deploy from Entity Modal and Collection view both succeed

**Depends On:** Phase 1 completion (basic discovery workflow must be stable)

**Key Files (See Phase 3 Plan):**
- Frontend: UnifiedEntityModal.tsx, DiscoveryTab.tsx, Collection components, AddToProjectDialog.tsx

---

## Architecture & Dependencies

### System Context

```
Three-Tier Discovery & Deployment System:

Project (.claude/ directories)
    ↑↓ discover + import
Collection (~/.skillmeat/collection/)
    ↑↓ deploy
Target Projects (.claude/ paths)
```

### Key Components & Interfaces

#### Backend Services (Python/FastAPI)

| Service | File | Responsibility | Status |
|---------|------|-----------------|--------|
| Discovery Service | `skillmeat/core/discovery.py` | Detect artifacts in `.claude/` directories, return metadata | Exists, needs membership check + timestamp fix |
| Importer | `skillmeat/core/importer.py` | Validate and import artifacts to collection | Exists, needs graceful error handling |
| Collection Manager | `skillmeat/core/collection.py` | Collection CRUD, artifact metadata, queries | Exists, needs membership query enhancement |
| Marketplace Dedup Engine | `skillmeat/core/marketplace/deduplication_engine.py` | Hash-based artifact matching | Exists, will reuse |
| Content Hash | `skillmeat/core/marketplace/content_hash.py` | Generate/compare artifact content hashes | Exists, will use |
| API Routers | `skillmeat/api/routers/artifacts.py` | HTTP endpoints for discovery/import | Exists, needs enhancement |

#### Frontend Hooks (React Query/TypeScript)

| Hook | File | Responsibility | Status |
|------|------|-----------------|--------|
| useProjectDiscovery | `skillmeat/web/hooks/useProjectDiscovery.ts` | Discovery + bulk import mutations | Exists, needs status fix + results handling |
| useDiscovery | `skillmeat/web/hooks/useDiscovery.ts` | Read-only discovery data | Exists, may need enhancement |
| useCollections | `skillmeat/web/hooks/useCollections.ts` | Collection data + queries | Exists, used by discovery |

#### Frontend Components (React)

| Component | File | Responsibility | Status |
|-----------|------|-----------------|--------|
| DiscoveryTab | `skillmeat/web/components/discovery/DiscoveryTab.tsx` | Main discovery UI in Entity Modal | Exists, needs grouping + filtering |
| BulkImportModal | `skillmeat/web/components/discovery/BulkImportModal.tsx` | Bulk import workflow | Exists, needs per-artifact results display |
| DuplicateReviewModal | `skillmeat/web/components/discovery/DuplicateReviewModal.tsx` | **NEW** - Duplicate review workflow | To create (P2-T4) |
| UnifiedEntityModal | `skillmeat/web/components/artifacts/UnifiedEntityModal.tsx` | Entity modal container | Exists, needs deploy button (P3-T1) |
| Collection components | `skillmeat/web/components/collections/` | Collection view | Exists, needs deploy option (P3-T2) |

### API Contracts

#### Current State

```
POST /api/v1/artifacts/discover
  Request: { "project_path": "/path" }
  Response: { "artifacts": [{ "path", "name", "type", ... }] }
  Issue: No membership check, invalid timestamps

POST /api/v1/artifacts/bulk-import
  Request: { "artifacts": [{ "path", ... }] }
  Response: { "status": "success|error", "artifacts": [...] }
  Issue: Fails entire batch on validation error (422)

GET /api/v1/collections/{id}
  Used to check artifact membership
```

#### Phase 1 Enhancements

```
POST /api/v1/artifacts/discover
  Response: {
    "artifacts": [{
      "path", "name", "type", "content_hash",
      "discovered_at",
      "collection_status": {
        "in_collection": bool,
        "match_type": "exact" | "hash" | "name_type" | "none"
      }
    }]
  }

POST /api/v1/artifacts/bulk-import
  Response: {
    "status": "partial_success",
    "summary": { "total", "imported", "skipped", "failed" },
    "results": [{
      "path", "status": "imported|skipped",
      "reason": "invalid_structure|yaml_error|..."
    }]
  }
```

#### Phase 2 New Endpoints

```
POST /api/v1/artifacts/confirm-duplicates
  Request: {
    "project_path": "/path",
    "matches": [{ "discovered_path", "collection_artifact_id" }],
    "new_artifacts": [...],
    "skipped": [...]
  }
  Response: { "status", "linked_count", "imported_count", "skipped_count" }
```

### Data Model Changes

#### Collection Metadata (TOML)

**Phase 1 Addition:**
```toml
[[artifacts]]
name = "skill-name"
discovered_at = "2026-01-09T20:15:03Z"  # NEW: timestamp field
```

**Phase 2 Addition:**
```toml
[[artifacts]]
duplicate_links = ["id-123", "id-456"]  # NEW: links to duplicate artifacts
content_hash = "sha256_value"           # NEW: for dedup matching
```

### External Dependencies

| Dependency | Type | Status | Required For |
|-----------|------|--------|--------------|
| TanStack Query v5 | Frontend lib | Installed | Cache management, mutations |
| Pydantic | Backend lib | Installed | Schema validation |
| SQLAlchemy | Backend ORM | Installed | Collection persistence |
| FastAPI | Backend framework | Installed | API endpoints |
| YAML parser | Backend lib | Installed | Frontmatter extraction |
| Radix UI | Frontend lib | Installed | Modal components |
| shadcn/ui | Frontend lib | Installed | UI components |

---

## Risk Assessment

### High-Impact Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| **Hash collision** - Different artifacts match same hash | Low (5%) | High (incorrect dedup) | Use marketplace engine (proven), test with diverse artifacts, add confidence scoring |
| **YAML parser edge cases** - New syntax errors appear in production | Medium (40%) | Medium (bulk import fails) | Comprehensive YAML test suite, fallback error handling, user feedback channel, gradual rollout |
| **Modal UX complexity** - Users confused by duplicate review workflow | Medium (35%) | Medium (low adoption) | Clear labeling, tooltips, artifact preview, single-click defaults, user testing |
| **Backward compatibility break** - Existing clients break on response schema change | Low (10%) | High (API breaking) | Extend schema (add fields), maintain existing fields, communicate change, version API |

### Medium-Impact Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| **Timestamp sync issues** - Artifacts have inconsistent timestamps across runs | Medium (30%) | Low (display issue) | Validate timestamp logic during Phase 1 testing, log all timestamp updates, audit collection manifest |
| **Performance degradation** - Hash matching slow for large collections (1000+) | Low (15%) | Medium (poor UX) | Batch hash computation, async processing, progress indicator, cache results |
| **Dialog pre-selection failure** - "Add to Project" dialog doesn't accept artifact param | Low (20%) | Medium (P3 blocked) | Early testing of dialog API, fallback to manual selection, document interface clearly |
| **Cache invalidation complexity** - React Query invalidation doesn't work as expected | Low (15%) | Medium (stale data) | Careful query key design, test cache behavior early, use debugging tools |

### Low-Impact Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| **Collection manifest corruption** - Duplicate links break existing metadata | Low (5%) | Low (recovery available) | Validate manifest format before write, backup before bulk operations, recovery script |
| **Frontend regression** - Discovery tab breaks on mobile | Medium (30%) | Low (desktop primary) | Responsive design testing, mobile E2E tests, gradual rollout to mobile users |
| **Documentation gaps** - Complex features not well documented | Medium (40%) | Low (developer friction) | Inline code comments, architecture docs, user guide with screenshots |

### Mitigation Strategy

1. **Early Validation:** Test YAML parser robustness and dialog API before Phase 1 completion
2. **Gradual Rollout:** Deploy Phase 1 to limited users, gather feedback before Phase 2
3. **Comprehensive Testing:** Unit + integration + E2E tests for all phases
4. **Monitoring:** Log all skipped artifacts, hash matches, duplicate decisions for analysis
5. **User Feedback:** Dedicated feedback channel for duplicate review workflow

---

## Quality Gates

### Phase 1 Quality Gate Checklist

**Code Quality:**
- [ ] All new code follows SkillMeat architecture patterns (routers → managers → repos)
- [ ] Type hints complete (Python + TypeScript)
- [ ] Docstrings and inline comments for complex logic
- [ ] No lint errors (black, flake8 compliance)

**Testing:**
- [ ] Unit tests: ≥85% code coverage for validation + query logic
- [ ] Integration test: Bulk import 20 valid + 3 invalid artifacts → 20 imported, 3 skipped
- [ ] Integration test: Collection membership check returns accurate status
- [ ] Integration test: Timestamps update correctly on new/changed artifacts
- [ ] No 422 errors on bulk import with valid artifact batches

**API Contract:**
- [ ] Response schema matches PRD Appendix 15.A exactly
- [ ] Status codes correct (200 OK for partial success, not 422)
- [ ] Error messages descriptive and actionable

**Frontend Validation:**
- [ ] Status display matches backend response data
- [ ] Error messages clear and helpful for users
- [ ] Modal responsive on desktop + tablet + mobile (tested at 1024px, 768px, 375px)
- [ ] Accessibility: Tab navigation works, no console errors

**Documentation:**
- [ ] API endpoint documented in code comments
- [ ] Response schema documented in PRD or code
- [ ] Known issues logged for future phases

### Phase 2 Quality Gate Checklist

**Hash Matching Validation:**
- [ ] Hash accuracy test with diverse artifact types (skills, commands, agents)
- [ ] Performance test: 100 artifacts hashed + matched in <500ms
- [ ] Edge cases tested: identical files, minor variations, different types

**Discovery Filtering:**
- [ ] Exact matches correctly hidden from "Ready to Import"
- [ ] "Possible Duplicates" group populated with name+type matches
- [ ] Test scenario: 10 discovered (3 exact, 2 partial, 5 new) → correct grouping

**Duplicate Review Modal:**
- [ ] Modal opens and closes correctly
- [ ] Tab switching works (New Artifacts, Possible Duplicates, Exact Matches)
- [ ] Artifact preview displays correctly
- [ ] Decision buttons function (Confirm Matches, Import New Only, Cancel)
- [ ] Modal responsive on mobile (tested at 375px)
- [ ] Keyboard navigation (Tab, Enter, Escape)

**Backend Decision Processing:**
- [ ] confirm-duplicates endpoint validates input
- [ ] Duplicate links created in collection metadata
- [ ] Audit log records all decisions
- [ ] Response status accurate (linked_count, imported_count, skipped_count)

**Testing:**
- [ ] Unit tests for hash matching logic
- [ ] Integration test: Full discovery → review → decision → import workflow
- [ ] E2E test: User opens duplicate review modal, confirms matches, sees results

### Phase 3 Quality Gate Checklist

**UI/UX Consistency:**
- [ ] Deploy button visible in Entity Modal Deployments tab (top right)
- [ ] Collection view meatballs menu includes "Deploy to Project" option
- [ ] All three entry points (Modal + Collection + /manage) use same dialog
- [ ] No duplicate dialog implementations

**Functionality:**
- [ ] Deploy button opens "Add to Project" dialog with artifact pre-selected
- [ ] User can select target project and confirm deployment
- [ ] Deployment completes and artifact appears in target project
- [ ] No context switching required (modal stays open during process)

**Testing:**
- [ ] Unit tests for button visibility and click handlers
- [ ] Integration test: Deploy from Entity Modal → artifact in target project
- [ ] Integration test: Deploy from Collection view → artifact in target project
- [ ] E2E test: Complete workflow from discovery → import → deploy → deployed

---

## Success Metrics

### Phase 1 Completion Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Bulk import success rate | 100% (no 422 errors on valid batches) | Unit test + integration test |
| Status accuracy | 100% (all artifacts show correct in/not in collection) | Manual verification + automated test |
| Timestamp validity | 0% invalid timestamps (no "-1 days ago") | UI inspection + test assertions |
| API response time | <2 seconds for 20+ artifacts | Performance test |
| Code coverage | ≥85% | pytest --cov report |
| Test pass rate | 100% | CI/CD pipeline |

### Phase 2 Completion Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Hash matching accuracy | ≥95% (across artifact types) | Test with known duplicate sets |
| Duplicate detection rate | 100% (of actual duplicates) | Comparison with manual review |
| Review modal usability | <2 min average per artifact | User testing / time tracking |
| Duplicate link persistence | 100% (all links saved) | Collection manifest inspection |
| Modal responsiveness | Works on 375px-2560px width | Device/browser testing |
| Performance (hash matching) | <500ms for 100 artifacts | Performance test |

### Phase 3 Completion Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Deploy button availability | 3 entry points (Modal + Collection + /manage) | UI inspection |
| Dialog reuse rate | 100% (same component across entry points) | Code review |
| User context switches | 0 (complete deploy workflow in modal) | Workflow testing |
| Deployment success rate | 100% (from all entry points) | Integration test |

### Overall Project Metrics

| Metric | Target | Status |
|--------|--------|--------|
| Total estimation accuracy | Within 10% of actual hours | Track and report post-project |
| Phase 1 on-time completion | 100% (2 weeks) | Monitor weekly |
| Phase 2 on-time completion | 100% (2 weeks) | Monitor weekly |
| Phase 3 on-time completion | 100% (1 week) | Monitor weekly |
| Zero critical bugs in Phase 1 release | 100% | Track post-deployment |
| User adoption of duplicate review | >80% of duplicate scenarios | Analytics tracking |

---

## Detailed Phase Plans

For detailed task breakdowns, acceptance criteria, and implementation notes, see:

- **[Phase 1: Bug Fixes & Stabilization](./discovery-import-fixes-v1/phase-1-bug-fixes.md)**
  - P1-T1: Backend artifact validation
  - P1-T2: Collection membership query
  - P1-T3: Timestamp tracking & display
  - P1-T4: Frontend status display

- **[Phase 2: Duplicate Detection & Review](./discovery-import-fixes-v1/phase-2-duplicate-detection.md)**
  - P2-T1: Hash-based deduplication
  - P2-T2: Duplicate decision endpoint
  - P2-T3: Discovery filtering & grouping
  - P2-T4: Duplicate review modal

- **[Phase 3: Deployment UX](./discovery-import-fixes-v1/phase-3-deploy-button.md)**
  - P3-T1: Entity Modal deploy button
  - P3-T2: Collection view deploy option
  - P3-T3: Unified dialog consistency

---

## Integration & Testing

### Test Strategy

**Unit Tests (Phase-specific)**
- Backend validation, queries, dedup logic
- Frontend component rendering, state management
- Hook behavior, mutation handling

**Integration Tests (Cross-system)**
- Discovery → Import → Collection update workflow
- Hash matching with deduplication engine
- Decision processing and persistence

**E2E Tests (User workflows)**
- Phase 1: Bulk import with mixed valid/invalid artifacts
- Phase 2: Discovery → duplicate review → import decision
- Phase 3: Deploy from Entity Modal and Collection view

**Performance Tests**
- Hash matching: <500ms for 100+ artifacts
- Bulk import: <2 seconds for 20+ artifacts
- Modal rendering: <1 second on initial load

### Test Coverage Requirements

| Layer | Target | Rationale |
|-------|--------|-----------|
| Backend logic | ≥85% | Critical path, error handling |
| Frontend components | ≥80% | UI/UX correctness |
| Routers/Handlers | ≥75% | API contract verification |
| Hooks | ≥75% | State management correctness |

### Test Data Sets

**Artifact types:** Skills, Commands, Agents, MCP servers
**YAML test cases:** Valid, malformed, edge case syntax
**Collection sizes:** 10, 50, 100, 1000+ artifacts
**Duplicate scenarios:** Exact hash, partial name+type, no matches

---

## Deployment & Rollout

### Deployment Sequence

**Phase 1 Deployment (Week 2, Post QA)**
1. Deploy backend changes (discovery, importer, collection)
2. Deploy API changes (endpoints, response schemas)
3. Deploy frontend changes (hooks, components)
4. Monitor for errors in logs and user feedback
5. 100% availability, feature flag optional

**Phase 2 Deployment (Week 4, Post QA)**
1. Deploy discovery endpoint with hash metadata
2. Deploy frontend discovery filtering
3. Deploy duplicate review modal (feature-flagged if needed)
4. Deploy confirm-duplicates endpoint
5. Enable duplicate review button after QA sign-off

**Phase 3 Deployment (Week 5, Post QA)**
1. Deploy Entity Modal deploy button
2. Deploy Collection view deploy option
3. Verify all three entry points work
4. Update documentation for users

### Rollback Plan

**Phase 1 Rollback (if critical issues found)**
- Revert artifacts.py, discovery.py to previous version
- Revert frontend components to previous version
- Restore collection metadata backups if needed
- Clear React Query cache in users' browsers

**Phase 2 Rollback (if duplicate logic fails)**
- Revert discovery endpoint to Phase 1 version
- Disable duplicate review modal
- Keep duplicate decision endpoint in place (harmless if unused)

**Phase 3 Rollback (if deploy buttons break)**
- Hide deploy buttons via feature flag
- Revert UnifiedEntityModal and Collection components
- Users still have /manage view for deployment

### Monitoring & Observability

**Key Metrics to Monitor**
- Bulk import 422 error rate (should be 0%)
- Discovery endpoint response time
- Hash matching performance
- Duplicate review decision completion rate
- Deploy button usage from new entry points
- Error logs for YAML parsing failures

**Logging Enhancements**
- Log all skipped artifacts with reason (P1)
- Log all hash matches with confidence score (P2)
- Log all duplicate review decisions (P2)
- Log all deployments with entry point source (P3)

**User Feedback Channels**
- In-app feedback form for duplicate review workflow
- Support channel for edge cases
- Analytics tracking for feature adoption

---

## Appendix: Subagent Assignment Summary

### Subagent Roster

| Subagent | Model | Role |
|----------|-------|------|
| `python-backend-engineer` | Opus | Backend Python/FastAPI implementation |
| `ui-engineer-enhanced` | Opus | Complex frontend component design |
| `ui-engineer` | Opus | Frontend component implementation |
| `documentation-writer` | Sonnet | Technical documentation |
| `codebase-explorer` | Haiku | File discovery and pattern analysis |
| `artifact-tracker` | Haiku | Progress tracking and task management |
| `validation-checker` | Haiku | Code review and quality validation |

### Task Assignment Map

**Phase 1:**
- P1-T1 (Backend validation): `python-backend-engineer` (Opus)
- P1-T2 (Membership query): `python-backend-engineer` (Opus)
- P1-T3 (Timestamp): `python-backend-engineer` (Sonnet or Opus)
- P1-T4 (Frontend): `ui-engineer-enhanced` (Opus)

**Phase 2:**
- P2-T1 (Hash dedup): `python-backend-engineer` (Opus)
- P2-T2 (Decision endpoint): `python-backend-engineer` (Opus)
- P2-T3 (Filtering): `ui-engineer-enhanced` (Opus)
- P2-T4 (Modal): `ui-engineer-enhanced` (Opus)

**Phase 3:**
- P3-T1 (Modal button): `ui-engineer-enhanced` (Sonnet)
- P3-T2 (Collection option): `ui-engineer-enhanced` (Sonnet)
- P3-T3 (Consistency): `ui-engineer-enhanced` (Sonnet)

---

## Document Control

| Field | Value |
|-------|-------|
| Created | 2026-01-09 |
| Last Updated | 2026-01-09 |
| Author | Claude Code (Orchestrator) |
| Status | Ready for Implementation |
| PRD Reference | harden-polish-discovery-import-fixes-v1.md |
| Request Log | REQ-20260109-skillmeat (5 items) |
| Approval | Pending team review |

---

**Next Steps:**

1. Review and approve main plan
2. Review Phase 1 detailed plan
3. Begin Phase 1 subagent delegation
4. Track progress via artifact-tracker
5. Gate Phase 2 start on Phase 1 QA completion

For Phase-specific details, see the phase subdirectory files.
