---
title: 'Implementation Plan: Marketplace Source Detection Improvements'
description: Detailed implementation plan for manual source mapping and auto-detection
  deduplication features
author: Claude Code (Implementation Planning Orchestrator)
date: 2026-01-05
status: inferred_complete
complexity: Medium (M)
estimated_effort: 55-70 story points
estimated_timeline: 4-5 weeks
schema_version: 2
doc_type: implementation_plan
feature_slug: marketplace-source-detection-improvements
prd_ref: null
---
# Implementation Plan: Marketplace Source Detection Improvements

**Feature:** Marketplace Source Detection Improvements (Manual Mapping + Auto-Deduplication)

**PRD:** `/docs/project_plans/PRDs/features/marketplace-source-detection-improvements-v1.md`

**Complexity:** Medium (M) - 55-70 story points, 4-5 weeks

**Team:** Backend (Python) + Frontend (React/TypeScript) + QA

---

## Executive Summary

This implementation plan provides detailed task breakdowns across 5 phases to deliver two critical marketplace source detection enhancements:

1. **Manual Source Mapping** - Enable users to explicitly map directories to artifact types via a modal UI, persisted in the database and applied during detection with 90+ confidence scoring.

2. **Auto-detection Deduplication** - Eliminate duplicate artifacts using SHA256 content hashing, with within-source dedup and cross-source matching against existing collection artifacts.

The plan follows MeatyPrompts layered architecture, with clear dependencies, quality gates, and rollback procedures. Estimated delivery: 4-5 weeks with parallel phase execution where possible.

---

## Architecture Overview

### Current State

**Detection System Files:**
- `skillmeat/core/marketplace/github_scanner.py` - GitHub API scanning and tree traversal
- `skillmeat/core/marketplace/heuristic_detector.py` - Confidence scoring (0-100)
- `skillmeat/core/marketplace/diff_engine.py` - Status tracking (new/updated/removed)
- `skillmeat/core/marketplace/import_coordinator.py` - Import orchestration

**Database Models:**
- `skillmeat/cache/models.py` (Line 1173) - `MarketplaceSource` with existing `manual_map` JSON column
- `skillmeat/cache/models.py` (Line 1368) - `MarketplaceCatalogEntry` with `confidence_score`, `excluded_at`, `excluded_reason`

**API Layer:**
- `skillmeat/api/routers/marketplace_sources.py` - 21 endpoints for source management
- `skillmeat/api/schemas/marketplace.py` - Request/response models
- Existing endpoint: `PATCH /marketplace/sources/{id}` for updates

**Frontend:**
- `skillmeat/web/app/marketplace/sources/[id]/page.tsx` - Source detail page
- `skillmeat/web/components/source-toolbar.tsx` - Toolbar (will add "Map Directories" button)
- `skillmeat/web/types/marketplace.ts` - TypeScript types
- Hooks: `useSource()`, `useSourceCatalog()`, `useRescanSource()`

### MeatyPrompts Layered Architecture Alignment

```
Phase 1: Database & Schema (Foundation)
    ↓
Phase 2: Backend Detection Engine (Service Layer)
    ├── Heuristic detector modifications
    └── Deduplication engine
    ↓
Phase 3: API Layer (Router/Schema updates)
    └── PATCH endpoint updates
    └── Rescan endpoint updates
    ↓
Phase 4: Frontend UI (Presentation Layer)
    ├── DirectoryMapModal component
    ├── Source detail updates
    └── Notification system
    ↓
Phase 5: Testing & Documentation (Quality & Deployment)
    ├── Integration tests
    ├── E2E tests
    └── User/developer docs
```

---

## Phase 1: Database & Schema (1 day, 5-8 points)

**Duration:** 1 day | **Story Points:** 5-8 | **Assigned To:** `data-layer-expert`

### Overview

Validate existing database schema and confirm no migrations are needed. Add documentation for extended usage of existing columns (`manual_map`, `metadata_json`). Create validation schemas for API layer.

### Deliverables

- Schema validation document in `.claude/context/marketplace-schema.md`
- Pydantic validation schemas in `skillmeat/api/schemas/marketplace.py`
- Migration checklist confirming no DB changes needed

### Tasks Summary

- **P1.1:** Validate `manual_map` column exists and is usable for JSON storage (2 pts)
- **P1.2:** Validate `metadata_json` column for content_hash storage (2 pts)
- **P1.3:** Document `manual_map` JSON schema (2 pts)
- **P1.4:** Create Pydantic validation models (3 pts)

**Full task details:** See `.claude/progress/marketplace-source-detection-improvements/phase-1-progress.md`

### Dependencies

None (foundation phase)

### Risks & Mitigations

**Risk:** Existing `manual_map` field has incompatible data
**Mitigation:** Query production DB; migrate any existing data if needed

---

## Phase 2: Backend Detection Engine (5-7 days, 20-30 points)

**Duration:** 5-7 days | **Story Points:** 20-30 | **Assigned To:** `python-backend-engineer`

### Overview

Implement manual mapping integration in heuristic detector and create new deduplication engine. Wire both into the marketplace scanning workflow. Focus on correct handling of hierarchical mappings, content hashing, and confidence scoring.

### Deliverables

- Modified `skillmeat/core/marketplace/heuristic_detector.py`
- New `skillmeat/core/marketplace/deduplication_engine.py`
- Updated `skillmeat/core/marketplace/import_coordinator.py` or `github_scanner.py` with integration
- Unit & integration test suite (400+ lines)
- Performance benchmark results

### Tasks Summary

**P2.1: Manual Mapping (15 pts)**
- Update detector signature; implement directory matching
- Apply hierarchical inheritance; set confidence scoring
- Unit tests for mapping scenarios

**P2.2: Content Hashing (10 pts)**
- SHA256 hashing for files and directories
- Hash caching; file size limits; unit tests

**P2.3: Deduplication Logic (14 pts)**
- DeduplicationEngine class
- Within-source dedup (Stage 1); cross-source dedup (Stage 2)
- Exclusion marking; unit tests

**P2.4: Integration (10 pts)**
- Wire into scan workflow; return dedup counts
- Integration tests; performance validation

**Full task details:** See `.claude/progress/marketplace-source-detection-improvements/phase-2-progress.md`

### Dependencies

- Phase 1 (schema validation)

### Risks & Mitigations

**Risk:** Dedup timeout on large repos (>10k files)
**Mitigation:** Implement lazy hashing, caching, configurable timeout (120s default)

**Risk:** Hash collisions (very low probability)
**Mitigation:** Use SHA256 industry standard; log collisions for monitoring

---

## Phase 3: API Layer (3-4 days, 12-18 points)

**Duration:** 3-4 days | **Story Points:** 12-18 | **Assigned To:** `python-backend-engineer`

### Overview

Update existing PATCH endpoint to accept and validate manual_map field. Update GET endpoint to return manual_map. Modify rescan endpoint to apply mappings and return dedup counts. Add comprehensive API documentation.

### Deliverables

- Modified `skillmeat/api/routers/marketplace_sources.py` (PATCH, GET, POST /rescan endpoints)
- Updated `skillmeat/api/schemas/marketplace.py` (UpdateSourceRequest, SourceResponse, ScanResultDTO)
- API integration test suite (200+ lines)
- OpenAPI documentation updates

### Tasks Summary

**P3.1: Update PATCH Endpoint (10 pts)**
- Add `manual_map` to request schema
- Validate directory paths and artifact types
- Persist mappings; update route handler

**P3.2: Update GET Endpoint (2 pts)**
- Include `manual_map` in response
- Test GET response after PATCH

**P3.3: Update Rescan Endpoint (6 pts)**
- Pass `manual_map` to detector
- Return dedup counts; update response schema
- Integration test

**P3.4: Error Handling & Documentation (4 pts)**
- Add error responses; update OpenAPI docs

**Full task details:** See `.claude/progress/marketplace-source-detection-improvements/phase-3-progress.md`

### Dependencies

- Phase 2 (backend detection engine)

### Risks & Mitigations

**Risk:** GitHub API rate limits during directory validation
**Mitigation:** Reuse scanner's cached tree data; batch validate directories

---

## Phase 4: Frontend UI (5-7 days, 20-28 points)

**Duration:** 5-7 days | **Story Points:** 20-28 | **Assigned To:** `ui-engineer-enhanced`

### Overview

Create DirectoryMapModal component with file tree and type selectors. Integrate into source detail page. Add toolbar button. Update source detail to show mappings and dedup counts. Add notification system for scan completion.

### Deliverables

- `DirectoryMapModal.tsx` component (~400 lines)
- Updated `source-toolbar.tsx` with "Map Directories" button
- Updated source detail page with mappings/dedup display
- Updated `skillmeat/web/types/marketplace.ts`
- Updated hooks: `useUpdateSourceMapping()`, `useRescanSource()`
- Frontend test suite (400+ lines, >60% coverage)
- Design/accessibility verification

### Tasks Summary

**P4.1: Modal Component (21 pts)**
- DirectoryMapModal with file tree, type selectors
- Implement hierarchical logic; form validation
- Save/Cancel/Rescan actions; component tests

**P4.2: Toolbar Integration (5 pts)**
- Add "Map Directories" button to toolbar
- Wire to modal; handle save/rescan

**P4.3: Source Detail Updates (8 pts)**
- Show manual mappings; show dedup stats
- Add duplicate badge with tooltip
- Link to excluded filter

**P4.4: Notification System (4 pts)**
- Scan completion notification with dedup counts
- Async scan notification; link to source detail

**P4.5: Types & Hooks (6 pts)**
- Update marketplace types
- Create mapping update hook; update rescan hook

**P4.6: UI Tests (8 pts)**
- E2E test for mapping workflow
- Snapshot tests; accessibility audit

**Full task details:** See `.claude/progress/marketplace-source-detection-improvements/phase-4-progress.md`

### Dependencies

- Phase 3 (API layer)

### Risks & Mitigations

**Risk:** Modal performance with 1000+ directories
**Mitigation:** Implement virtual scrolling; lazy load subtrees

**Risk:** Complex hierarchical mapping UI confusion
**Mitigation:** Add inline help text; example mapping; visual feedback

---

## Phase 5: Integration Testing & Deployment (2-3 days, 8-12 points)

**Duration:** 2-3 days | **Story Points:** 8-12 | **Assigned To:** `python-backend-engineer`, `documentation-writer`

### Overview

Execute end-to-end workflow tests, edge case testing, performance validation, and backward compatibility verification. Create user and developer documentation. Prepare deployment checklist.

### Deliverables

- Integration test suite (600+ lines, fully automated)
- Edge case test results and documentation
- Performance benchmark report
- User documentation (guide + FAQ)
- API documentation updates
- Developer guide (architecture, extension points)
- Troubleshooting guide
- Deployment checklist
- Rollback playbook

### Tasks Summary

**P5.1: Full Workflow Tests (5 pts)**
- Create & map source; rescan with mapping
- Dedup detection; import after dedup; restore excluded

**P5.2: Edge Cases (6 pts)**
- Empty repository; all duplicates
- Large repository; deeply nested dirs; invalid mappings

**P5.3: Performance Testing (4 pts)**
- Scan time regression; hash computation time
- Cross-source lookup; modal responsiveness

**P5.4: Backward Compatibility (3 pts)**
- Sources without mapping; existing catalog entries
- API compatibility

**P5.5: Documentation (6 pts)**
- User guide; API documentation
- Developer guide; troubleshooting guide

**P5.6: Deployment (3 pts)**
- Deployment checklist; environment setup; rollback plan

**Full task details:** See `.claude/progress/marketplace-source-detection-improvements/phase-5-progress.md`

### Dependencies

- Phases 1-4 (all previous phases)

### Risks & Mitigations

**Risk:** Critical issue found after partial deployment
**Mitigation:** Canary rollout to 10% first; monitor error rates closely

---

## Task Dependencies & Critical Path

### Dependency Graph

```
Phase 1 (Database & Schema)
    ↓ (required for all later phases)
Phase 2 (Backend Engine)
    ├─ P2.1 (Manual mapping) → must complete before P3
    ├─ P2.2 (Hashing) → can be parallel
    ├─ P2.3 (Dedup logic) → depends on P2.2
    └─ P2.4 (Integration) → depends on P2.1, P2.3
        ↓ (required for P3 & P4)
Phase 3 (API Layer)
    ├─ P3.1 (PATCH) → can be parallel with P3.2
    ├─ P3.2 (GET & Rescan) → depends on P2.4
    └─ P3.3 (Error handling & docs) → depends on P3.1, P3.2
        ↓ (required for Phase 4)
Phase 4 (Frontend)
    ├─ P4.1 (Modal) → can be parallel with P4.2
    ├─ P4.2 (Toolbar) → depends on Phase 3
    ├─ P4.3 (Notifications) → can be parallel
    └─ P4.4 (Tests) → depends on P4.1-P4.3
        ↓ (required for Phase 5)
Phase 5 (Integration & Deployment)
    └─ All phases must pass before deployment
```

### Critical Path (Longest dependency chain)

```
Phase 1 (1 day)
  → Phase 2.1 (Manual mapping: 3-4 days)
    → Phase 2.4 (Integration: 2-3 days)
      → Phase 3 (API: 3-4 days)
        → Phase 4.2 (Toolbar: 1 day)
          → Phase 5.1 (E2E tests: 1 day)
            → Deployment (0.5 days)

Total Critical Path: ~12-15 days
(Parallel execution reduces actual timeline to ~10-12 days)
```

### Optimization Opportunities

**Run in Parallel:**
- Phase 2.1 (mapping) + Phase 2.2 (hashing) can run simultaneously after Phase 1
- Phase 3.1 (PATCH) + Phase 3.2 (GET/Rescan) can run simultaneously
- Phase 4.1 (Modal) + Phase 4.2 (Toolbar) can run simultaneously after Phase 3
- Phase 4.1-4.3 (UI tasks) can run in parallel
- Phase 5.4-5.6 (Docs & deployment) can start as soon as code is stable

**Expected Timeline:** 4-5 weeks with optimal parallelization

---

## Quality Assurance Gates

See [Quality Gates](./marketplace-source-detection-improvements-v1/quality-gates.md) for detailed QA checkpoints for each phase.

---

## Risk Management

### High-Priority Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|-----------|--------|-----------|-------|
| Dedup performance timeout on large repos | Medium | High | Implement lazy hashing, caching, configurable timeout (120s); test with 1000+ artifacts | Backend |
| Manual mapping UI confusion (hierarchical logic) | Low | Medium | Add inline help text, examples, visual feedback; user testing with 5+ testers | Frontend |
| Hash collisions (SHA256) | Very Low | High | Use industry-standard SHA256; log collisions for monitoring; document risk | Backend |
| Backward compatibility breaking | Low | High | No DB changes; optional API fields; thorough testing of existing sources | QA |
| Over-exclusion of valid duplicates | Medium | Medium | Store duplicate reason in excluded_reason; allow restore; test with known duplicates | Backend/QA |

### Mitigation Strategies

1. **Performance:** Implement incremental hashing with caching; lazy evaluation for non-obvious duplicates
2. **UX:** Provide auto-suggestions for common directory names; add help modal; test with 5+ users
3. **Compatibility:** Run full regression test suite before deployment; canary rollout to 10% users first
4. **Monitoring:** Add metrics for scan time, dedup stats, error rates; set up alerts
5. **Rollback:** Keep previous code version; have database backup; document rollback procedure

---

## Metrics & Success Criteria

See [Metrics](./marketplace-source-detection-improvements-v1/metrics.md) for detailed implementation and production metrics, observability configuration, and success criteria.

---

## Environment Configuration & Deployment

See [Deployment](./marketplace-source-detection-improvements-v1/deployment.md) for environment variables, deployment procedure, and rollback plan.

---

## References & Related Documents

### Key Files

**Backend:**
- `skillmeat/core/marketplace/github_scanner.py` - GitHub API scanning
- `skillmeat/core/marketplace/heuristic_detector.py` - Detection engine (to be modified)
- `skillmeat/core/marketplace/deduplication_engine.py` - NEW file
- `skillmeat/cache/models.py` (Lines 1173-1366) - Database models
- `skillmeat/api/routers/marketplace_sources.py` - API endpoints
- `skillmeat/api/schemas/marketplace.py` - Request/response schemas

**Frontend:**
- `skillmeat/web/components/DirectoryMapModal.tsx` - NEW component
- `skillmeat/web/components/source-toolbar.tsx` - Toolbar (to be modified)
- `skillmeat/web/app/marketplace/sources/[id]/page.tsx` - Source detail
- `skillmeat/web/types/marketplace.ts` - TypeScript types
- `skillmeat/web/hooks/` - React hooks (to be created/modified)

**Documentation:**
- `skillmeat/core/artifact.py` - Artifact types (skill, command, agent, mcp_server, hook)
- `skillmeat/api/CLAUDE.md` - API architecture guide
- `skillmeat/web/CLAUDE.md` - Frontend architecture guide

### Related PRDs

- [Marketplace GitHub Ingestion PRD](/docs/project_plans/PRDs/features/marketplace-github-ingestion-v1.md)
- [Marketplace Sources Non-Skills Bug Report](/docs/project_plans/bugs/marketplace-sources-non_skills-v1.md)

### Standards & References

- SHA256 (FIPS 180-4)
- REST API design (RFC 7231)
- WCAG AA accessibility standards

---

## Appendix: Data Structures

See [Data Structures](./marketplace-source-detection-improvements-v1/data-structures.md) for detailed JSON schemas and data structure specifications.

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-05 | Claude Code | Initial implementation plan created from PRD |
| 1.1 | 2026-01-05 | Claude Code | Optimized for token efficiency: extracted sections to subdirectory |

---

**End of Implementation Plan**
