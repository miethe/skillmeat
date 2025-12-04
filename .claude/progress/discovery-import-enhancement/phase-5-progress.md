---
type: progress
prd: "discovery-import-enhancement"
phase: 5
title: "Integration & End-to-End Testing"
status: "planning"
started: null
completed: null

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 12
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["testing-specialist", "web-accessibility-checker"]
contributors: ["frontend-developer", "documentation-writer"]

tasks:
  - id: "DIS-5.1"
    description: "Integration test - full discovery workflow (discovery → pre-scan → filter → import → notification)"
    status: "pending"
    assigned_to: ["testing-specialist"]
    dependencies: []
    estimated_effort: "1.5d"
    priority: "critical"

  - id: "DIS-5.2"
    description: "Verify Notification System integration with new ImportResult.status enum and breakdown display"
    status: "pending"
    assigned_to: ["testing-specialist"]
    dependencies: []
    estimated_effort: "1d"
    priority: "critical"

  - id: "DIS-5.3"
    description: "Performance validation - discovery scan <2 seconds on typical project (500 Collection, 200 Project)"
    status: "pending"
    assigned_to: ["testing-specialist"]
    dependencies: []
    estimated_effort: "1d"
    priority: "high"

  - id: "DIS-5.4"
    description: "E2E test full skip workflow - mark skip → import → verify saved → future discovery excludes"
    status: "pending"
    assigned_to: ["testing-specialist"]
    dependencies: []
    estimated_effort: "1d"
    priority: "high"

  - id: "DIS-5.5"
    description: "E2E test Discovery Tab interactions - view → filter → sort → manage skips → re-scan"
    status: "pending"
    assigned_to: ["testing-specialist"]
    dependencies: []
    estimated_effort: "1d"
    priority: "high"

  - id: "DIS-5.6"
    description: "Accessibility audit - Discovery Tab keyboard navigation, screen reader compatibility"
    status: "pending"
    assigned_to: ["web-accessibility-checker"]
    dependencies: []
    estimated_effort: "1d"
    priority: "high"

  - id: "DIS-5.7"
    description: "Accessibility audit - skip checkboxes labels, keyboard access, screen reader support"
    status: "pending"
    assigned_to: ["web-accessibility-checker"]
    dependencies: []
    estimated_effort: "0.5d"
    priority: "high"

  - id: "DIS-5.8"
    description: "Load test - discovery on large project (500+ Collection, 300+ Project artifacts)"
    status: "pending"
    assigned_to: ["testing-specialist"]
    dependencies: []
    estimated_effort: "1d"
    priority: "medium"

  - id: "DIS-5.9"
    description: "Cross-browser testing - LocalStorage persistence and UI rendering (Chrome, Firefox, Safari)"
    status: "pending"
    assigned_to: ["testing-specialist"]
    dependencies: []
    estimated_effort: "0.5d"
    priority: "medium"

  - id: "DIS-5.10"
    description: "Error handling & edge cases - network failure, corrupted files, missing directory"
    status: "pending"
    assigned_to: ["testing-specialist"]
    dependencies: []
    estimated_effort: "1d"
    priority: "high"

  - id: "DIS-5.11"
    description: "Update Notification to show detailed breakdown (Imported:N | Skipped:N | Failed:N)"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: []
    estimated_effort: "1d"
    priority: "high"

  - id: "DIS-5.12"
    description: "Update OpenAPI documentation with ImportResult enum, skip endpoints, DiscoveryResult filtering"
    status: "pending"
    assigned_to: ["documentation-writer"]
    dependencies: []
    estimated_effort: "0.5d"
    priority: "medium"

parallelization:
  batch_1: ["DIS-5.1", "DIS-5.2", "DIS-5.3", "DIS-5.4", "DIS-5.5", "DIS-5.6", "DIS-5.7", "DIS-5.8", "DIS-5.9", "DIS-5.10"]
  batch_2: ["DIS-5.11", "DIS-5.12"]
  critical_path: ["DIS-5.1", "DIS-5.2", "DIS-5.3", "DIS-5.6"]
  estimated_total_time: "8-10 days"

blockers: []

success_criteria:
  - id: "SC-1"
    description: "End-to-end discovery → import → notification flow completes without errors"
    status: "pending"
  - id: "SC-2"
    description: "Notification System displays new status enum values correctly"
    status: "pending"
  - id: "SC-3"
    description: "Skip preferences persist across all browsers (LocalStorage validated)"
    status: "pending"
  - id: "SC-4"
    description: "Performance: discovery <2 seconds on typical project"
    status: "pending"
  - id: "SC-5"
    description: "Load test passes: 500+ artifacts handled smoothly"
    status: "pending"
  - id: "SC-6"
    description: "Accessibility: Discovery Tab keyboard navigable, screen reader compatible"
    status: "pending"
  - id: "SC-7"
    description: "Error handling: network failures, corrupted files, missing directories handled gracefully"
    status: "pending"
  - id: "SC-8"
    description: "All E2E tests pass: skip workflow, tab interactions, discovery filtering"
    status: "pending"
  - id: "SC-9"
    description: "OpenAPI documentation updated and accurate"
    status: "pending"

files_modified:
  - "tests/integration/test_discovery_full_workflow.py"
  - "tests/integration/test_notification_integration.py"
  - "skillmeat/web/tests/e2e/full-discovery-workflow.spec.ts"
  - "skillmeat/web/tests/e2e/skip-workflow.spec.ts"
  - "skillmeat/web/tests/e2e/discovery-tab-interactions.spec.ts"
  - "skillmeat/web/components/notifications/NotificationItem.tsx"
  - "docs/api/openapi.json"
---

# Discovery & Import Enhancement - Phase 5: Integration & End-to-End Testing

**Phase**: 5 of 6
**Status**: 📋 Planning (0% complete)
**Duration**: Estimated 2-3 days
**Owner**: testing-specialist, web-accessibility-checker
**Contributors**: frontend-developer, documentation-writer
**Dependency**: Phases 2, 3, 4 ✓ Complete

---

## Orchestration Quick Reference

> **For Orchestration Agents**: Launch Phase 5 after Phases 2-4 complete. This is the validation phase where all pieces integrate.

### Parallelization Strategy

**Batch 1** (Highly Parallel - All Independent):
- DIS-5.1 → `testing-specialist` (1.5d) - Full discovery workflow integration
- DIS-5.2 → `testing-specialist` (1d) - Notification System integration
- DIS-5.3 → `testing-specialist` (1d) - Performance validation
- DIS-5.4 → `testing-specialist` (1d) - Full skip workflow E2E
- DIS-5.5 → `testing-specialist` (1d) - Discovery Tab interactions E2E
- DIS-5.6 → `web-accessibility-checker` (1d) - Accessibility audit: Discovery Tab
- DIS-5.7 → `web-accessibility-checker` (0.5d) - Accessibility audit: skip checkboxes
- DIS-5.8 → `testing-specialist` (1d) - Load testing
- DIS-5.9 → `testing-specialist` (0.5d) - Cross-browser testing
- DIS-5.10 → `testing-specialist` (1d) - Error handling & edge cases

**Batch 2** (Parallel - After Batch 1):
- DIS-5.11 → `frontend-developer` (1d) - Notification detail breakdown
- DIS-5.12 → `documentation-writer` (0.5d) - OpenAPI documentation

**Critical Path**: DIS-5.1 → DIS-5.2 → (others can overlap) (8-10 days)

### Task Delegation Commands

```
# Batch 1 (All launch in parallel)
Task("testing-specialist", "DIS-5.1: Integration test - full discovery workflow. File: tests/integration/test_discovery_full_workflow.py (new). Test: project discovery → pre-scan filters → filtered results → user imports → notification created with breakdown. Acceptance: (1) Discovery endpoint called; (2) Pre-scan filters correctly; (3) Import mutations execute; (4) Notification with breakdown; (5) All state consistent")

Task("testing-specialist", "DIS-5.2: Notification System integration test. File: tests/integration/test_notification_integration.py (new). Verify: Notification consumes new status enum, displays breakdown (Imported:N | Skipped:N | Failed:N), skip reasons visible. Acceptance: (1) Notification created; (2) Shows counts; (3) Shows skip reasons; (4) Persists in center")

Task("testing-specialist", "DIS-5.3: Performance validation - discovery <2 seconds. File: tests/performance/test_discovery_performance.py (new). Benchmark: discovery scan with pre-scan checks on typical project (500 Collection, 200 Project). Acceptance: (1) Benchmark run; (2) Time measured; (3) <2 seconds; (4) Optimizations applied if needed")

Task("testing-specialist", "DIS-5.4: E2E test full skip workflow. File: skillmeat/web/tests/e2e/skip-workflow.spec.ts (new). Test: discovery → mark skip checkboxes → import with skips → verify skip prefs saved → future discovery excludes. Acceptance: (1) Skips marked; (2) Skip list sent; (3) Prefs persisted; (4) Future discovery filters; (5) All state consistent")

Task("testing-specialist", "DIS-5.5: E2E test Discovery Tab interactions. File: skillmeat/web/tests/e2e/discovery-tab-interactions.spec.ts (new). Test: navigate to tab → view artifacts → filter/sort → manage skips → re-scan → tab updated. Acceptance: (1) Tab displays; (2) Filters/sorts work; (3) Skips managed; (4) Re-scan updates; (5) Consistent state")

Task("web-accessibility-checker", "DIS-5.6: Accessibility audit - Discovery Tab. File: accessibility-audit-report.md. Audit: keyboard navigation (Tab, Enter, Arrows), screen reader compatibility, ARIA labels. Acceptance: (1) All elements keyboard accessible; (2) Tab order logical; (3) Screen reader announces; (4) ARIA labels present; (5) Color not only indicator")

Task("web-accessibility-checker", "DIS-5.7: Accessibility audit - skip checkboxes. File: accessibility-audit-report.md. Verify: proper label associations, keyboard access, screen reader support. Acceptance: (1) <label for> correct; (2) Keyboard nav works; (3) Screen reader announces state; (4) Focus visible")

Task("testing-specialist", "DIS-5.8: Load test - large project discovery. File: tests/performance/test_load.py (new). Test: 500+ Collection, 300+ Project artifacts with skip preferences. Acceptance: (1) Completes successfully; (2) <2 seconds (or optimized); (3) All artifacts processed; (4) No memory leaks; (5) UI responsive")

Task("testing-specialist", "DIS-5.9: Cross-browser testing - LocalStorage persistence. Test: Chrome, Firefox, Safari. Focus: LocalStorage working, UI renders, toasts display, tabs functional. Acceptance: (1) LocalStorage on all browsers; (2) UI consistent; (3) Toasts display; (4) Tabs functional")

Task("testing-specialist", "DIS-5.10: Error handling & edge cases. File: tests/error_handling/test_discovery_errors.py (new). Test: network failure during import, corrupted skip prefs file, project directory missing, permission denied. Acceptance: (1) Network error: graceful fallback; (2) Corrupted file: skipped gracefully; (3) Missing project: clear error; (4) Permission denied: retry or abort")

# Batch 2 (After Batch 1 completes)
Task("frontend-developer", "DIS-5.11: Update Notification detail breakdown. File: skillmeat/web/components/notifications/NotificationItem.tsx. Show: 'Imported to Collection: 3 | Added to Project: 5 | Skipped: 2' with click-through for details. Acceptance: (1) Shows summary; (2) Click shows detail list; (3) Skip reasons visible; (4) Styling consistent")

Task("documentation-writer", "DIS-5.12: Update OpenAPI documentation. File: docs/api/openapi.json. Update: ImportResult enum, skip endpoints, DiscoveryResult filtering. Acceptance: (1) Schema accurate; (2) Examples with new enum; (3) Skip reason documented; (4) Endpoints described")
```

---

## Overview

**Phase 5** is the comprehensive validation phase where all four implementation phases integrate into a cohesive system. This phase runs end-to-end workflows, validates Notification System integration, performs accessibility audits, and ensures performance meets requirements.

**Why This Phase**: Phases 1-4 implement individual components in isolation. Phase 5 verifies they work together correctly, handle errors gracefully, perform acceptably, and meet accessibility standards.

**Scope**:
- **IN**: Integration tests, E2E tests, accessibility audits, performance validation, load testing, cross-browser testing, error handling, documentation updates
- **OUT**: Bug fixes and optimizations (Phase 6), release preparation (Phase 6)

---

## Success Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| SC-1 | End-to-end discovery → import → notification flow completes | ⏳ Pending |
| SC-2 | Notification System displays new status enum correctly | ⏳ Pending |
| SC-3 | Skip preferences persist across all browsers | ⏳ Pending |
| SC-4 | Performance: discovery <2 seconds on typical project | ⏳ Pending |
| SC-5 | Load test passes: 500+ artifacts handled smoothly | ⏳ Pending |
| SC-6 | Accessibility: Discovery Tab keyboard navigable | ⏳ Pending |
| SC-7 | Error handling: graceful failure for all scenarios | ⏳ Pending |
| SC-8 | All E2E tests pass | ⏳ Pending |
| SC-9 | OpenAPI documentation updated and accurate | ⏳ Pending |

---

## Tasks

| ID | Task | Status | Agent | Dependencies | Est | Notes |
|----|------|--------|-------|--------------|-----|-------|
| DIS-5.1 | Integration test - full workflow | ⏳ | testing-specialist | None | 1.5d | discovery → import → notification |
| DIS-5.2 | Notification System integration | ⏳ | testing-specialist | None | 1d | Status enum + breakdown |
| DIS-5.3 | Performance validation | ⏳ | testing-specialist | None | 1d | <2 seconds |
| DIS-5.4 | E2E skip workflow | ⏳ | testing-specialist | None | 1d | Mark → import → future |
| DIS-5.5 | E2E Discovery Tab interactions | ⏳ | testing-specialist | None | 1d | Tab → filter → skip → rescan |
| DIS-5.6 | Accessibility audit - Tab | ⏳ | web-accessibility-checker | None | 1d | Keyboard + screen reader |
| DIS-5.7 | Accessibility audit - checkboxes | ⏳ | web-accessibility-checker | None | 0.5d | Labels + keyboard |
| DIS-5.8 | Load test | ⏳ | testing-specialist | None | 1d | 500+ artifacts |
| DIS-5.9 | Cross-browser testing | ⏳ | testing-specialist | None | 0.5d | Chrome, Firefox, Safari |
| DIS-5.10 | Error handling tests | ⏳ | testing-specialist | None | 1d | Network, files, permissions |
| DIS-5.11 | Notification detail breakdown | ⏳ | frontend-developer | None | 1d | Show counts & reasons |
| DIS-5.12 | OpenAPI documentation | ⏳ | documentation-writer | None | 0.5d | Update specs |

---

## Architecture Context

### Current State

After Phase 4, all implementation components exist:
- Backend: status enum, pre-scan, skip preferences, endpoints
- Frontend: types updated, skip checkboxes, Discovery Tab, toast breakdown
- No integration testing yet; Notification System integration pending

**Key Files**:
- All Phase 1-4 files
- Notification System components (skillmeat/web/components/notifications/)
- OpenAPI spec (docs/api/openapi.json or equivalent)

### Reference Patterns

Integration testing patterns:
- Full workflow tests in existing test suites
- E2E tests using Playwright or Cypress
- Accessibility audits using axe or WAVE tools

---

## Implementation Details

### Technical Approach

1. **Full Workflow Integration (DIS-5.1)**:
   - Create realistic test project with artifacts
   - Call discovery endpoint
   - Verify pre-scan filters correctly
   - Call import endpoint
   - Verify notification created with breakdown
   - Check database/file state consistency

2. **Notification System Integration (DIS-5.2)**:
   - Get notification system's type definitions
   - Verify it accepts new status enum values
   - Test breakdown display format
   - Verify notification persists in Notification Center

3. **Performance Validation (DIS-5.3)**:
   - Create test project: 500 Collection, 200 Project artifacts
   - Measure discovery endpoint time (including pre-scan)
   - Target: <2 seconds (or document optimization needed)
   - Profile to identify bottlenecks

4. **Skip Workflow E2E (DIS-5.4)**:
   - Real browser test: open Discovery Tab
   - Mark artifacts with skip checkbox
   - Click Import
   - Verify skip preferences persisted (check LocalStorage)
   - Re-run discovery
   - Verify skipped artifacts excluded

5. **Discovery Tab E2E (DIS-5.5)**:
   - Navigate to Project Detail
   - Click Discovery tab
   - Apply filters and sorts
   - Click Un-skip on skipped artifact
   - Re-scan
   - Verify tab updated

6. **Accessibility Audits (DIS-5.6, DIS-5.7)**:
   - Manual keyboard navigation (Tab, Shift+Tab, Enter, Arrows)
   - Screen reader testing (NVDA or JAWS on Windows, VoiceOver on Mac)
   - Check ARIA labels, roles, live regions
   - Generate accessibility report

7. **Load Testing (DIS-5.8)**:
   - Simulate 500+ discovered artifacts
   - Verify UI doesn't freeze
   - Check for memory leaks
   - Measure performance

8. **Cross-browser Testing (DIS-5.9)**:
   - Test LocalStorage in Chrome, Firefox, Safari
   - Verify UI renders consistently
   - Test touch interactions on mobile

9. **Error Handling (DIS-5.10)**:
   - Network failure during import
   - Corrupted skip preferences file
   - Missing project directory
   - Permission denied on file write
   - Verify graceful handling

10. **Notification Detail Breakdown (DIS-5.11)**:
    - Update NotificationItem to display detailed counts
    - Add click-through to show per-artifact details
    - Verify formatting

11. **OpenAPI Documentation (DIS-5.12)**:
    - Update schema with new ImportResult enum
    - Document skip preference endpoints
    - Add example responses
    - Verify schema validity

### Known Gotchas

- **Flaky E2E Tests**: Use explicit waits, avoid sleep(), mock datetime
- **LocalStorage Quota**: Large skip preference lists might exceed quota
- **Accessibility Tools**: Different tools catch different violations
- **Cross-browser Compatibility**: LocalStorage is universal; focus on UI rendering
- **Performance Variance**: Run benchmarks multiple times to account for variance

### Development Setup

- Test fixtures for 500+ artifacts
- Mocked Notification System for testing
- Real browser automation (Playwright/Cypress)
- Accessibility checker tools (axe, WAVE)
- Performance profiling tools

---

## Blockers

### Active Blockers

- **Phases 2-4 Dependency**: Awaiting completion of all implementation phases

---

## Dependencies

### External Dependencies

- **Notification System**: Must be ready to receive new status enum values
- **Performance Requirements**: <2 seconds baseline (may need optimization)

### Internal Integration Points

- **All Phase 1-4 Components**: Discovery, import, skip preferences, UI
- **Notification System** - Integration point for breakdown display
- **OpenAPI Spec** - Accuracy critical for API consumers

---

## Testing Strategy

| Test Type | Scope | Coverage | Status |
|-----------|-------|----------|--------|
| Integration | Full discovery → import → notification workflow | Happy path + errors | ⏳ |
| E2E - Skip | Mark skip → import → future discovery | Happy path + edge cases | ⏳ |
| E2E - Tab | Tab nav, filter, sort, skip mgmt, rescan | All interactions | ⏳ |
| Performance | Discovery scan with pre-scan | <2 seconds | ⏳ |
| Load | 500+ artifacts with skip preferences | Responsive UI | ⏳ |
| Accessibility | Keyboard nav, screen reader, ARIA | WCAG 2.1 AA | ⏳ |
| Error Handling | Network, file, permission failures | Graceful degradation | ⏳ |
| Cross-browser | LocalStorage, UI rendering | Chrome, Firefox, Safari | ⏳ |

---

## Next Session Agenda

### Immediate Actions (Next Session - After Phase 4 Complete)
1. [ ] Launch all Batch 1 tests in parallel (they're independent)
2. [ ] Setup test fixtures for integration tests
3. [ ] Configure performance benchmarking environment
4. [ ] Coordinate with Notification System team on integration points

### Upcoming Critical Items

- **Day 1-3**: Batch 1 tests run in parallel
- **Day 3-4**: Bug fixes from test failures
- **Day 5**: Batch 2 updates (notification detail, OpenAPI)
- **Day 6**: Quality gate check - all tests passing, accessibility report complete

### Context for Continuing Agent

Phase 5 is heavily testing-focused. Key coordination:
1. DIS-5.1 and DIS-5.2 are on critical path - prioritize these
2. Accessibility audits (DIS-5.6, DIS-5.7) may reveal UI issues needing fixes
3. Performance benchmarking (DIS-5.3) must happen to validate <2s requirement
4. Error handling tests (DIS-5.10) should uncover edge cases for Phase 6 fixes
5. Cross-browser testing might reveal LocalStorage issues

---

## Session Notes

*None yet - Phase 5 not started*

---

## Additional Resources

- **Phase 1-4 Results**: All implementation files and components
- **Notification System API**: Integration points for breakdown display
- **Performance Baseline**: Phase 1 pre-scan benchmark data
- **Accessibility Tools**: axe, WAVE, screen readers (NVDA, JAWS, VoiceOver)
- **E2E Test Framework**: Playwright or Cypress configuration
