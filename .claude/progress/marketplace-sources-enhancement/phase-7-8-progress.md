---
type: progress
prd: marketplace-sources-enhancement
phase: 7
title: 'Phases 7-8: Testing & Documentation'
status: planning
started: '2025-01-18'
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 9
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
- frontend-developer
- testing specialist
contributors:
- ui-engineer-enhanced
- documentation-writer
- api-documenter
tasks:
- id: TEST-001
  description: Unit tests for new schema fields and filtering logic
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - API-004
  estimated_effort: 3h
  priority: high
- id: TEST-002
  description: Integration tests for source filtering endpoint
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TEST-001
  estimated_effort: 2h
  priority: high
- id: TEST-003
  description: Unit tests for new frontend components
  status: pending
  assigned_to:
  - frontend-developer
  dependencies:
  - UI-010
  estimated_effort: 2h
  priority: high
- id: TEST-004
  description: E2E tests for full filtering workflow
  status: pending
  assigned_to:
  - testing specialist
  dependencies:
  - TEST-002
  - TEST-003
  estimated_effort: 3h
  priority: high
- id: TEST-005
  description: Accessibility tests for new components (WCAG 2.1 AA)
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - TEST-003
  estimated_effort: 2h
  priority: medium
- id: TEST-006
  description: Performance tests for filtering with 500+ sources
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TEST-002
  estimated_effort: 1h
  priority: medium
- id: DOC-001
  description: Update API documentation for new endpoints and parameters
  status: pending
  assigned_to:
  - api-documenter
  dependencies:
  - TEST-006
  estimated_effort: 1h
  priority: high
- id: DOC-002
  description: Update component documentation (Storybook or equivalent)
  status: pending
  assigned_to:
  - documentation-writer
  dependencies:
  - TEST-005
  estimated_effort: 1h
  priority: medium
- id: DOC-003
  description: Create/update user guides for source import and filtering
  status: pending
  assigned_to:
  - documentation-writer
  dependencies:
  - DOC-001
  - DOC-002
  estimated_effort: 2h
  priority: medium
parallelization:
  batch_1:
  - TEST-001
  - TEST-003
  batch_2:
  - TEST-002
  - TEST-005
  batch_3:
  - TEST-004
  - TEST-006
  batch_4:
  - DOC-001
  - DOC-002
  batch_5:
  - DOC-003
  critical_path:
  - TEST-001
  - TEST-002
  - TEST-004
  - DOC-001
  - DOC-003
  estimated_total_time: 10h
blockers: []
success_criteria:
- id: SC-1
  description: All unit tests passing (backend + frontend)
  status: pending
- id: SC-2
  description: All integration tests passing
  status: pending
- id: SC-3
  description: E2E test suite covers critical user journeys
  status: pending
- id: SC-4
  description: Accessibility audit passed (WCAG 2.1 AA)
  status: pending
- id: SC-5
  description: Performance benchmarks met (<200ms for source list)
  status: pending
- id: SC-6
  description: Code coverage >80% across all layers
  status: pending
- id: SC-7
  description: All API endpoints documented with examples
  status: pending
files_modified:
- tests/unit/backend/test_tags_validation.py
- tests/unit/backend/test_filtering.py
- tests/integration/api/test_sources_filtering.py
- tests/unit/frontend/source-filter-bar.test.tsx
- tests/e2e/marketplace/source-import.spec.ts
- tests/e2e/marketplace/source-filtering.spec.ts
- tests/a11y/marketplace-components.test.ts
- docs/api/endpoints/marketplace-sources.md
- docs/guides/user/source-import.md
- docs/guides/user/source-filtering.md
schema_version: 2
doc_type: progress
feature_slug: marketplace-sources-enhancement
---

# marketplace-sources-enhancement - Phases 7-8: Testing & Documentation

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/marketplace-sources-enhancement/phase-7-8-progress.md -t TEST-001 -s completed
```

---

## Objective

Complete quality assurance and documentation for marketplace sources enhancement: unit tests for backend (tag validation, filtering logic) and frontend (components, hooks), integration tests for API endpoints, E2E tests for critical user journeys, accessibility audit, performance verification, and comprehensive documentation updates.

---

## Implementation Notes

### Testing Stack

| Layer | Tool | Location |
|-------|------|----------|
| Backend Unit | pytest + pytest-cov | `tests/unit/backend/` |
| Backend Integration | pytest + httpx | `tests/integration/api/` |
| Frontend Unit | Jest + RTL | `skillmeat/web/__tests__/` |
| E2E | Playwright | `skillmeat/web/tests/` |
| Accessibility | axe-core | `tests/a11y/` |

### Test Coverage Targets

| Metric | Target |
|--------|--------|
| Backend statements | >80% |
| Backend branches | >75% |
| Frontend statements | >80% |
| Frontend branches | >75% |

### Known Gotchas

- TanStack Query: Use fresh `QueryClient` per test with `retry: false`
- Async operations: Use `waitFor()` or `findBy` queries in RTL
- E2E timing: Wait for network requests to complete before assertions
- Accessibility: Some automated tools miss dynamic content, manual verification needed

### Performance Targets

| Operation | Target |
|-----------|--------|
| GET /marketplace/sources (500+ sources) | <200ms |
| Detail fetch with README | <5s |
| Filter UI response | <100ms |

---

## Test Scenarios Reference

### Unit Test Scenarios

- [ ] Tag validation: alphanumeric + hyphens/underscores only
- [ ] Tag limit: max 20 per source
- [ ] Tag length: 1-50 chars each
- [ ] Counts by type: accurate sum across all types
- [ ] Filter AND logic: multiple filters compose correctly
- [ ] Description truncation: repo_description capped at 2000 chars
- [ ] README truncation: repo_readme capped at 50KB

### Integration Test Scenarios

- [ ] GET /marketplace/sources with no filters returns all sources
- [ ] GET /marketplace/sources?artifact_type=skill returns only skills
- [ ] GET /marketplace/sources?tags=ui returns sources with ui tag
- [ ] GET /marketplace/sources?artifact_type=skill&tags=ui returns intersection
- [ ] POST /marketplace/sources with toggles fetches repo details
- [ ] PUT /marketplace/sources/{id} updates tags

### E2E Test Scenarios

- [ ] User imports source with repo details enabled, details appear on detail page
- [ ] User imports source with tags, tags appear on card
- [ ] User filters sources by artifact type, results update
- [ ] User clicks tag on card, filter applies
- [ ] User opens Repo Details modal, description and README display
- [ ] User clears filters, all sources reappear

### Accessibility Test Scenarios

- [ ] Color contrast on tags meets 4.5:1
- [ ] Tab navigation through filters works
- [ ] Escape key closes repo details modal
- [ ] Screen reader announces artifact count breakdown
- [ ] Filter labels associated with inputs

---

## Orchestration Quick Reference

### Batch Execution Commands

**Batch 1 (parallel)** - Unit tests:
```
Task("python-backend-engineer", "Implement TEST-001: Unit tests for tag validation (alphanumeric+hyphens+underscores, max 20, 1-50 chars), counts_by_type computation, filter AND logic. Files: tests/unit/backend/test_tags_validation.py, tests/unit/backend/test_filtering.py", model="opus")
Task("frontend-developer", "Implement TEST-003: Unit tests for SourceFilterBar (filter state changes), TagBadge (overflow logic), CountBadge (tooltip display), filter change callbacks. Files: skillmeat/web/__tests__/source-filter-bar.test.tsx, skillmeat/web/__tests__/tag-badge.test.tsx", model="opus")
```

**Batch 2 (after Batch 1, parallel)** - Integration and accessibility:
```
Task("python-backend-engineer", "Implement TEST-002: Integration tests for GET /marketplace/sources with all filter params, filter composition, pagination, error cases. Files: tests/integration/api/test_sources_filtering.py", model="opus")
Task("ui-engineer-enhanced", "Implement TEST-005: Accessibility tests using axe-core. Test color contrast (4.5:1), keyboard navigation, ARIA labels, focus visible, screen reader compatibility. Files: tests/a11y/marketplace-components.test.ts", model="opus")
```

**Batch 3 (after Batch 2, parallel)** - E2E and performance:
```
Task("testing specialist", "Implement TEST-004: E2E tests for source import with details/tags, filtering workflow, tag click to filter, Repo Details modal display. Use Playwright. Files: tests/e2e/marketplace/source-import.spec.ts, tests/e2e/marketplace/source-filtering.spec.ts", model="opus")
Task("python-backend-engineer", "Implement TEST-006: Performance tests verifying GET /marketplace/sources returns <200ms with 500+ sources. Generate test data, measure response times. Files: tests/integration/api/test_sources_performance.py", model="opus")
```

**Batch 4 (after Batch 3, parallel)** - Documentation:
```
Task("api-documenter", "Implement DOC-001: Update OpenAPI spec and API documentation for new endpoints (/marketplace/sources with filters, /marketplace/sources/{id}/details). Include example requests/responses. Files: skillmeat/api/openapi.json, docs/api/endpoints/marketplace-sources.md", model="sonnet")
Task("documentation-writer", "Implement DOC-002: Create component documentation with usage examples for SourceFilterBar, SourceCard, RepoDetailsModal, TagBadge, CountBadge. Files: docs/components/source-components.md", model="sonnet")
```

**Batch 5 (after Batch 4)** - User guides:
```
Task("documentation-writer", "Implement DOC-003: Create user guides for source import (how to enable repo details, add tags) and source filtering (available filters, how to combine, clear filters). Files: docs/guides/user/source-import.md, docs/guides/user/source-filtering.md", model="sonnet")
```

---

## Completion Notes

Summary of phase completion (fill in when phase is complete):

- What was built
- Key learnings
- Unexpected challenges
- Recommendations for release
