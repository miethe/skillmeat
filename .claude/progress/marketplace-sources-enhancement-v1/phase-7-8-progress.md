---
type: progress
prd: marketplace-sources-enhancement-v1
phase: 7-8
title: Testing and Documentation
status: completed
completed_at: '2026-01-18'
progress: 100
total_tasks: 19
completed_tasks: 19
total_story_points: 29
completed_story_points: 2
tasks:
- id: TEST-001
  title: Backend Unit Tests
  description: Unit tests for tag validation, counts_by_type computation, filter logic
  status: completed
  story_points: 3
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SVC-005
  created_at: '2026-01-18'
- id: TEST-002
  title: Backend Integration Tests
  description: Integration tests for API endpoints with various filter combinations
  status: completed
  story_points: 2
  assigned_to:
  - python-backend-engineer
  dependencies:
  - API-009
  created_at: '2026-01-18'
- id: TEST-003
  title: Frontend Unit Tests
  description: Unit tests for components and hooks
  status: completed
  story_points: 2
  assigned_to:
  - frontend-developer
  dependencies:
  - DIALOG-006
  created_at: '2026-01-18'
- id: TEST-004
  title: Frontend Integration Tests
  description: Integration tests for pages and component interactions
  status: completed
  story_points: 2
  assigned_to:
  - frontend-developer
  dependencies:
  - DIALOG-006
  created_at: '2026-01-18'
- id: TEST-005
  title: E2E Tests - Source Import
  description: User journey - import source with details and tags, verify stored correctly
  status: completed
  story_points: 2
  assigned_to:
  - testing specialist
  dependencies:
  - DIALOG-006
  created_at: '2026-01-18'
- id: TEST-006
  title: E2E Tests - Filtering
  description: User journey - apply filters, verify results match criteria
  status: completed
  story_points: 2
  assigned_to:
  - testing specialist
  dependencies:
  - PAGE-007
  created_at: '2026-01-18'
- id: TEST-007
  title: E2E Tests - Repo Details
  description: User journey - view source detail, open repo details modal, verify
    content
  status: completed
  story_points: 1
  assigned_to:
  - testing specialist
  dependencies:
  - PAGE-007
  created_at: '2026-01-18'
- id: TEST-008
  title: Accessibility Audit
  description: WCAG 2.1 AA compliance testing for all new components and pages
  status: completed
  story_points: 2
  assigned_to:
  - web-accessibility-checker
  dependencies:
  - TEST-007
  created_at: '2026-01-18'
- id: TEST-009
  title: Performance Testing
  description: Verify response times meet targets
  status: completed
  story_points: 1
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TEST-004
  created_at: '2026-01-18'
- id: TEST-010
  title: Security Testing
  description: Validate tag input sanitization, XSS prevention, rate limiting
  status: completed
  story_points: 1
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TEST-008
  created_at: '2026-01-18'
- id: TEST-011
  title: Coverage Report
  description: Generate coverage reports for all layers
  status: completed
  story_points: 1
  assigned_to:
  - testing specialist
  dependencies:
  - TEST-010
  created_at: '2026-01-18'
- id: DOC-001
  title: API Documentation
  description: Complete OpenAPI spec documentation for all new endpoints
  status: completed
  story_points: 1
  assigned_to:
  - api-documenter
  dependencies:
  - TEST-011
  created_at: '2026-01-18'
- id: DOC-002
  title: Component Documentation
  description: Create Storybook docs for new components
  status: completed
  story_points: 1
  assigned_to:
  - documentation-writer
  dependencies:
  - TEST-011
  created_at: '2026-01-18'
- id: DOC-003
  title: User Guide - Source Import
  description: Write user guide for importing sources with details and tags
  status: completed
  story_points: 1
  assigned_to:
  - documentation-writer
  dependencies:
  - TEST-011
  created_at: '2026-01-18'
- id: DOC-004
  title: User Guide - Filtering
  description: Write user guide for filtering sources in marketplace
  status: completed
  story_points: 1
  assigned_to:
  - documentation-writer
  dependencies:
  - TEST-011
  created_at: '2026-01-18'
- id: DOC-005
  title: ADR - Repository Metadata Storage
  description: Create ADR documenting decision on storing description/README in manifest
  status: completed
  story_points: 1
  assigned_to:
  - documentation-writer
  dependencies:
  - TEST-011
  created_at: '2026-01-18'
- id: DOC-006
  title: ADR - Filtering Implementation
  description: Create ADR documenting filter design and AND logic choice
  status: completed
  story_points: 1
  assigned_to:
  - documentation-writer
  dependencies:
  - TEST-011
  created_at: '2026-01-18'
- id: DOC-007
  title: Release Notes
  description: Write release notes with migration guidance
  status: completed
  story_points: 1
  assigned_to:
  - documentation-writer
  dependencies:
  - TEST-011
  created_at: '2026-01-18'
  completed_at: '2026-01-18'
- id: DOC-008
  title: Development Guide - Extending
  description: Write guide for developers to extend filtering or add new source metadata
  status: completed
  story_points: 1
  assigned_to:
  - documentation-writer
  dependencies:
  - TEST-011
  created_at: '2026-01-18'
  completed_at: '2026-01-18'
parallelization:
  batch_1:
  - TEST-001
  - TEST-002
  - TEST-003
  - TEST-004
  batch_2:
  - TEST-005
  - TEST-006
  - TEST-007
  - TEST-008
  batch_3:
  - TEST-009
  - TEST-010
  - TEST-011
  batch_4:
  - DOC-001
  - DOC-002
  - DOC-003
  - DOC-004
  batch_5:
  - DOC-005
  - DOC-006
  - DOC-007
  - DOC-008
context_files:
- tests/
- docs/
blockers: []
notes: 'Phases 7-8 provide comprehensive testing and documentation for marketplace
  sources enhancement. Phase 7 focuses on quality assurance (unit, integration, E2E,
  accessibility, performance, security). Phase 8 documents new features and architectural
  decisions. Total duration: 4 days, 29 story points.'
in_progress_tasks: 0
blocked_tasks: 0
updated: '2026-01-18'
schema_version: 2
doc_type: progress
feature_slug: marketplace-sources-enhancement-v1
---
# Phases 7-8: Testing & Documentation

Comprehensive testing and documentation for the marketplace sources enhancement, including quality assurance across all layers and complete documentation for users and developers.

**Total Duration**: 4 days
**Total Story Points**: 29
**Dependencies**: All implementation phases (1-6) complete
**Assigned Agents**: python-backend-engineer, frontend-developer, testing specialist, web-accessibility-checker, api-documenter, documentation-writer

---

## Phase 7: Testing & Quality Assurance

**Duration**: 3 days
**Story Points**: 18
**Objective**: Comprehensive testing to validate implementation quality, performance, security, and accessibility.

### Phase 7A: Unit & Integration Tests (1 day)

**Batch 1**: TEST-001, TEST-002, TEST-003, TEST-004 (parallel execution)

#### TEST-001: Backend Unit Tests (3 pts)

```markdown
Task("python-backend-engineer", "TEST-001: Backend Unit Tests

Files to Create:
  - tests/unit/services/test_source_service.py
  - tests/unit/schemas/test_source_schemas.py
  - tests/unit/utils/test_tag_validation.py

Coverage Requirement: >80% for all source-related code

Test Scenarios:

1. Tag Validation Tests (test_tag_validation.py)
   - test_validate_tag_alphanumeric_only: Accept alphanumeric
   - test_validate_tag_hyphens_underscores: Accept hyphens, underscores
   - test_validate_tag_reject_special_chars: Reject special characters
   - test_validate_tag_length_1_50: Length 1-50 chars
   - test_validate_tag_reject_empty: Reject empty strings
   - test_validate_tag_max_20_tags: Enforce max 20 per source
   - test_validate_tag_whitespace_stripped: Strip whitespace
   - test_validate_tag_case_normalized: Normalize case

2. Counts by Type Tests (test_source_service.py)
   - test_counts_by_type_all_types: Aggregate correctly
   - test_counts_by_type_zero_count: Handle missing types
   - test_counts_by_type_empty_source: Empty source returns empty dict
   - test_counts_by_type_consistent_with_artifacts: Match artifact list

3. Filter Logic Tests (test_source_service.py)
   - test_filter_by_artifact_type_single: Filter single type
   - test_filter_by_artifact_type_multiple: Multiple types (OR within type)
   - test_filter_by_tags_single: Filter by one tag
   - test_filter_by_tags_multiple: Multiple tags (AND logic)
   - test_filter_by_artifact_type_and_tags: Combine filters
   - test_filter_empty_result: No matches returns empty
   - test_filter_pagination: Cursor pagination works

4. Schema Validation Tests (test_source_schemas.py)
   - test_source_response_serialization: ORM → Pydantic
   - test_source_response_includes_counts: counts_by_type present
   - test_source_response_includes_tags: tags array present
   - test_create_source_request_validation: Valid input accepted
   - test_update_source_request_optional: Partial updates work
   - test_repo_description_truncation: Max 2000 chars
   - test_repo_readme_truncation: Max 50KB
   - test_tag_array_serialization: Correct format

Test Fixtures:
- Sample sources with artifacts
- Sample tags
- Database session fixture
- Clean database before each test

Run Tests:
pytest tests/unit/services/test_source_service.py -v --cov=skillmeat.core.services
")
```

#### TEST-002: Backend Integration Tests (2 pts)

```markdown
Task("python-backend-engineer", "TEST-002: Backend Integration Tests

Files to Create:
  - tests/integration/routers/test_marketplace_sources_router.py

Coverage Requirement: >80% for all endpoints

Test Scenarios:

1. GET /marketplace/sources Endpoint
   - test_get_sources_no_filters: Returns all sources
   - test_get_sources_artifact_type_filter: Filter by type
   - test_get_sources_tags_filter: Filter by tags (AND logic)
   - test_get_sources_combined_filters: Type + tags
   - test_get_sources_pagination: Cursor pagination
   - test_get_sources_invalid_artifact_type: Returns empty
   - test_get_sources_invalid_tags: Returns empty
   - test_get_sources_401_unauthorized: Missing auth
   - test_get_sources_response_format: Correct schema
   - test_get_sources_includes_counts: counts_by_type present
   - test_get_sources_includes_tags: tags array present

2. POST /marketplace/sources Endpoint
   - test_post_sources_basic: Create source with minimal data
   - test_post_sources_with_tags: Create with tags
   - test_post_sources_with_repo_details: Toggle enables fetch
   - test_post_sources_fetch_description: Description fetched
   - test_post_sources_fetch_readme: README fetched
   - test_post_sources_description_truncation: 2000 char limit
   - test_post_sources_readme_truncation: 50KB limit
   - test_post_sources_invalid_tags: Validation error
   - test_post_sources_too_many_tags: Max 20 enforced
   - test_post_sources_duplicate_tags: Duplicates removed
   - test_post_sources_response_201_created: Correct status

3. PUT /marketplace/sources/{id} Endpoint
   - test_put_sources_update_tags: Update tags
   - test_put_sources_update_partial: Partial updates
   - test_put_sources_replace_tags: Replace all tags
   - test_put_sources_404_not_found: Missing source
   - test_put_sources_invalid_tags: Validation error
   - test_put_sources_response_200_ok: Correct status

4. GET /marketplace/sources/{id}/details Endpoint
   - test_get_details_returns_description: Description present
   - test_get_details_returns_readme: README present
   - test_get_details_null_when_not_fetched: Null if not fetched
   - test_get_details_404_not_found: Missing source
   - test_get_details_response_format: Correct schema

5. Error Handling & Status Codes
   - test_400_bad_request: Invalid parameters
   - test_401_unauthorized: Missing auth
   - test_404_not_found: Missing resource
   - test_422_validation_error: Invalid data format
   - test_500_server_error: Database errors

6. Integration with Other Systems
   - test_filter_accuracy_with_multiple_sources: Filters work correctly
   - test_pagination_cursor_validity: Cursor is valid
   - test_concurrent_requests_safe: No race conditions

Run Tests:
pytest tests/integration/routers/test_marketplace_sources_router.py -v --cov=skillmeat.api.app.routers
")
```

#### TEST-003: Frontend Unit Tests (2 pts)

```markdown
Task("frontend-developer", "TEST-003: Frontend Unit Tests

Files to Create:
  - __tests__/components/SourceFilterBar.test.tsx
  - __tests__/components/SourceCard.test.tsx
  - __tests__/components/TagBadge.test.tsx
  - __tests__/components/CountBadge.test.tsx

Framework: Jest + React Testing Library

Coverage Requirement: >80% for all components

Test Scenarios:

1. SourceFilterBar Component Tests
   - test_renders_filter_controls: All controls present
   - test_artifact_type_filter_change: Dropdown changes filter
   - test_tags_filter_change: Tags filter updates state
   - test_multiple_filters_composition: Filters compose correctly
   - test_clear_filters_button: Reset works
   - test_filter_state_update_callback: onChange fires correctly
   - test_filter_state_persistence: State persists
   - test_disabled_state: Disabled prop works
   - test_accessibility_labels: ARIA labels present
   - test_keyboard_navigation: Tab through filters

2. SourceCard Component Tests
   - test_renders_with_source_data: Card displays data
   - test_displays_artifact_type: Type badge shows
   - test_displays_tags: Tag badges display
   - test_tag_badge_colors: Colors applied
   - test_count_badge_display: Artifact counts shown
   - test_tag_overflow_ellipsis: Overflow handled
   - test_click_tag_filters: Tag click triggers filter
   - test_click_card_navigates: Card click navigates
   - test_responsive_layout: Mobile layout works
   - test_accessibility_button_labels: ARIA labels present

3. TagBadge Component Tests
   - test_renders_tag_name: Badge shows name
   - test_applies_background_color: Color applied
   - test_text_color_contrast: White/black text based on bg
   - test_contrast_ratio_4_5_1: Meets WCAG AA
   - test_badge_size_styling: Size correct
   - test_badge_responsive: Responsive on mobile

4. CountBadge Component Tests
   - test_renders_count_value: Number displays
   - test_tooltip_display: Tooltip shows on hover
   - test_tooltip_content: Correct content
   - test_badge_styling: Correct appearance
   - test_accessibility_tooltip: ARIA attributes present

Test Utilities:
- renderWithProviders: Render with QueryClient, Router
- userEvent: Simulate user interactions
- screen: Query rendered elements
- waitFor: Async operations

Run Tests:
npm test -- SourceFilterBar.test.tsx
npm test -- --coverage
")
```

#### TEST-004: Frontend Integration Tests (2 pts)

```markdown
Task("frontend-developer", "TEST-004: Frontend Integration Tests

Files to Create:
  - __tests__/pages/sources.test.tsx
  - __tests__/pages/source-[id].test.tsx

Framework: Jest + React Testing Library + Mock server

Test Scenarios:

1. Sources List Page Tests
   - test_renders_sources_list: Page loads
   - test_displays_all_sources: All sources shown
   - test_apply_artifact_type_filter: Filter works
   - test_apply_tags_filter: Tag filter works
   - test_combine_filters: Filters compose
   - test_filter_updates_url_params: URL state synced
   - test_url_params_restore_filters: Reload restores filters
   - test_pagination_works: Cursor pagination works
   - test_source_card_click_navigates: Navigation works
   - test_loading_state: Skeleton shows during load
   - test_error_state: Error message displays

2. Source Detail Page Tests
   - test_renders_source_detail: Page loads
   - test_displays_source_info: Source data shows
   - test_displays_tags_section: Tags displayed
   - test_artifact_list_displays: Artifacts listed
   - test_artifact_type_filter_on_detail: Can filter artifacts
   - test_filter_url_sync_on_detail: URL params updated
   - test_repo_details_modal_opens: Modal displays
   - test_repo_details_content: Description and README shown
   - test_modal_escape_closes: Escape closes modal
   - test_modal_click_outside_closes: Outside click closes
   - test_responsive_layout: Mobile layout works
   - test_loading_state: Skeleton shows during load
   - test_error_state: Error message displays

Run Tests:
npm test -- sources.test.tsx
npm test -- source-[id].test.tsx
npm test -- --coverage
")
```

### Phase 7B: End-to-End & Accessibility Tests (1 day)

**Batch 2**: TEST-005, TEST-006, TEST-007, TEST-008 (parallel execution)

#### TEST-005: E2E Tests - Source Import (2 pts)

```markdown
Task("testing specialist", "TEST-005: E2E Tests - Source Import

Framework: Playwright

File: tests/e2e/source-import.spec.ts

Test Scenarios:

1. Import Source with Basic Details
   - Navigate to marketplace
   - Click 'Add Source' button
   - Enter repository URL
   - Submit form
   - Verify source appears in list
   - Verify stored correctly in database

2. Import Source with Repo Details
   - Navigate to marketplace
   - Click 'Add Source' button
   - Enter repository URL
   - Enable 'Fetch Repository Details' toggle
   - Submit form
   - Verify source appears
   - Verify description fetched and displayed
   - Verify README fetched and displayed
   - Verify truncation if exceeds limits

3. Import Source with Tags
   - Navigate to marketplace
   - Click 'Add Source' button
   - Enter repository URL
   - Add tags (single and multiple)
   - Submit form
   - Verify source appears with tags
   - Verify tags displayed on card
   - Verify tags stored in database

4. Import Source Full Workflow
   - Navigate to marketplace
   - Click 'Add Source' button
   - Enter URL
   - Enable repo details toggle
   - Add multiple tags
   - Enable other toggles (if applicable)
   - Submit form
   - Verify all details stored
   - Navigate to detail page
   - Verify all information displays

Run Tests:
npx playwright test tests/e2e/source-import.spec.ts
")
```

#### TEST-006: E2E Tests - Filtering (2 pts)

```markdown
Task("testing specialist", "TEST-006: E2E Tests - Filtering

Framework: Playwright

File: tests/e2e/source-filtering.spec.ts

Test Scenarios:

1. Filter by Artifact Type
   - Navigate to sources list
   - Apply artifact type filter (e.g., 'skill')
   - Verify list updates
   - Verify only selected type shows
   - Clear filter
   - Verify all types reappear

2. Filter by Tags (AND Logic)
   - Navigate to sources list
   - Apply single tag filter
   - Verify list updates
   - Apply second tag filter
   - Verify only sources with BOTH tags show (AND logic)
   - Clear filters
   - Verify all sources reappear

3. Combine Multiple Filters
   - Apply artifact type filter
   - Apply tag filters
   - Verify combined filtering works (AND logic across filters)
   - Verify results accurate
   - Clear all filters

4. Click Tag on Card to Filter
   - Navigate to sources list
   - Click tag badge on source card
   - Verify tag filter applied
   - Verify list filtered to sources with that tag
   - Navigate back to card
   - Verify other tags on same source selectable

5. Filter Persistence
   - Apply filters
   - Reload page
   - Verify filters persist from URL
   - Verify results match filters
   - Navigate to detail page
   - Navigate back
   - Verify filters still active

6. Keyboard Navigation in Filters
   - Tab to filter controls
   - Use arrow keys to select options
   - Use Enter to apply
   - Verify no keyboard traps
   - Verify logical tab order

Run Tests:
npx playwright test tests/e2e/source-filtering.spec.ts
")
```

#### TEST-007: E2E Tests - Repo Details (1 pt)

```markdown
Task("testing specialist", "TEST-007: E2E Tests - Repo Details

Framework: Playwright

File: tests/e2e/repo-details-modal.spec.ts

Test Scenarios:

1. Open Repo Details Modal
   - Navigate to source detail page
   - Click 'Repo Details' button
   - Verify modal opens
   - Verify modal displays content

2. Modal Content Display
   - Modal shows repository description
   - Modal shows README content
   - Content is readable and properly formatted
   - Long content scrolls properly
   - No overflow issues

3. Close Modal
   - Open modal
   - Click X button to close
   - Verify modal closes
   - Verify page content underneath is accessible

4. Close with Escape
   - Open modal
   - Press Escape key
   - Verify modal closes

5. Click Outside Modal
   - Open modal
   - Click outside modal area
   - Verify modal closes (if backdrop click enabled)

6. Modal Responsive
   - Test on mobile viewport
   - Test on tablet viewport
   - Test on desktop viewport
   - Verify content readable at all sizes
   - Verify close button always accessible

Run Tests:
npx playwright test tests/e2e/repo-details-modal.spec.ts
")
```

#### TEST-008: Accessibility Audit (2 pts)

```markdown
Task("web-accessibility-checker", "TEST-008: Accessibility Audit

Tools:
  - axe-core (automated)
  - WAVE (manual)
  - Keyboard testing
  - Screen reader testing

Files to Create:
  - tests/accessibility/sources-a11y.test.ts

Automated Testing with axe-core:

1. Component Accessibility Tests
   - SourceFilterBar: All controls accessible
   - SourceCard: All interactive elements keyboard accessible
   - TagBadge: Proper color contrast
   - CountBadge: Proper color contrast
   - RepoDetailsModal: Keyboard accessible

2. Page Accessibility Tests
   - Sources list page: Full WCAG 2.1 AA compliance
   - Source detail page: Full WCAG 2.1 AA compliance

Manual Testing Checklist:

1. Keyboard Navigation
   - [ ] Tab through all components
   - [ ] Focus visible on all elements
   - [ ] No keyboard traps
   - [ ] Logical tab order
   - [ ] Arrow keys work in filters
   - [ ] Escape closes modals
   - [ ] Enter submits filters

2. Screen Reader Testing
   - [ ] All labels announced
   - [ ] Form inputs described
   - [ ] Tag filters described
   - [ ] Count badges described
   - [ ] Modal title announced
   - [ ] Modal content readable
   - [ ] Proper heading hierarchy

3. Color & Contrast
   - [ ] Text on tag badges: 4.5:1 minimum
   - [ ] UI elements: 3:1 minimum
   - [ ] Focus indicators visible (3:1)
   - [ ] No information by color alone
   - [ ] Color blind friendly

4. Responsive & Mobile
   - [ ] Touch targets: 44x44px minimum
   - [ ] Spacing adequate on mobile
   - [ ] Zoom to 200% works
   - [ ] Landscape/portrait modes work
   - [ ] Mobile screen reader works

5. Assistive Technology
   - [ ] Works with: Screen readers (NVDA, JAWS, VoiceOver)
   - [ ] Works with: Speech recognition
   - [ ] Works with: High contrast mode
   - [ ] Works with: Reduced motion

WCAG 2.1 AA Criteria Coverage:

- [ ] 1.4.3 Contrast (Minimum) - 4.5:1 for text
- [ ] 2.1.1 Keyboard - All functionality accessible
- [ ] 2.1.2 No Keyboard Trap - Can escape with keyboard
- [ ] 2.4.3 Focus Order - Logical tab order
- [ ] 2.4.7 Focus Visible - Visual focus indicator
- [ ] 3.2.2 On Input - No context change on input
- [ ] 3.3.1 Error Identification - Errors clearly identified
- [ ] 4.1.2 Name, Role, Value - Proper ARIA attributes

Test Report:
Create accessibility report with:
- Automated test results
- Manual testing results
- Known limitations
- Remediation steps
- WCAG 2.1 AA certification

Run Tests:
npm run test:a11y
")
```

### Phase 7C: Performance & Security Testing (1 day)

**Batch 3**: TEST-009, TEST-010, TEST-011 (parallel execution)

#### TEST-009: Performance Testing (1 pt)

```markdown
Task("python-backend-engineer", "TEST-009: Performance Testing

File: tests/performance/test_marketplace_sources_performance.py

Test Scenarios:

1. API Response Time Tests
   - test_get_sources_no_filters_response_time: <200ms with 500+ sources
   - test_get_sources_with_filters_response_time: <200ms with filters
   - test_get_source_detail_response_time: <5s for detail fetch
   - test_pagination_cursor_generation: <50ms
   - test_tag_filter_performance: <100ms with 20+ tags

2. Database Query Performance
   - test_filter_query_execution_time: <100ms for complex filters
   - test_tag_counts_aggregation_time: <50ms
   - test_artifact_list_join_performance: <100ms

3. Load Testing
   - test_concurrent_filter_requests: 100 requests handle 50+ concurrent
   - test_pagination_under_load: Stable under load
   - test_tag_filter_under_load: Stable under load

Acceptance Criteria:
- GET /marketplace/sources: <200ms
- GET /marketplace/sources with filters: <200ms
- GET /marketplace/sources/{id}/details: <5s
- Database queries: <100ms
- All tests pass under 50+ concurrent requests

Run Tests:
pytest tests/performance/test_marketplace_sources_performance.py -v
")
```

#### TEST-010: Security Testing (1 pt)

```markdown
Task("python-backend-engineer", "TEST-010: Security Testing

File: tests/security/test_marketplace_sources_security.py

Test Scenarios:

1. Tag Input Sanitization
   - test_tag_validation_whitelist: Only alphanumeric, hyphens, underscores
   - test_tag_special_chars_rejected: No special characters accepted
   - test_tag_html_injection_prevented: HTML tags rejected
   - test_tag_sql_injection_prevented: SQL syntax rejected
   - test_tag_xss_attempts_blocked: JavaScript attempts blocked

2. XSS Prevention
   - test_source_description_xss_prevention: Description sanitized
   - test_source_readme_xss_prevention: README sanitized
   - test_tag_display_xss_prevention: Tags escaped on display
   - test_artifact_type_xss_prevention: Type sanitized

3. Rate Limiting
   - test_github_api_rate_limiting: Respects GitHub limits
   - test_rate_limit_headers_present: Headers in response
   - test_exceeding_rate_limit_handled: Graceful fallback

4. Authentication & Authorization
   - test_unauthenticated_access: Appropriate access level
   - test_authorization_enforced: User permissions respected
   - test_token_validation: Invalid tokens rejected

Acceptance Criteria:
- Tag validation whitelist enforced
- All XSS attempts fail
- No special characters accepted in tags
- Rate limiting respected
- All requests properly authorized

Run Tests:
pytest tests/security/test_marketplace_sources_security.py -v
")
```

#### TEST-011: Coverage Report (1 pt)

```markdown
Task("testing specialist", "TEST-011: Coverage Report

Files to Generate:
  - coverage/backend-coverage.html
  - coverage/frontend-coverage.html
  - coverage/COVERAGE_REPORT.md

Coverage Requirements:

Backend:
- test_source_service.py: >80%
- source_repository.py: >80%
- marketplace_sources_router.py: >80%
- schemas/source_schemas.py: >80%
- Overall backend: >80%

Frontend:
- SourceFilterBar.tsx: >80%
- SourceCard.tsx: >80%
- TagBadge.tsx: >80%
- CountBadge.tsx: >80%
- useMarketplaceSources.ts: >80%
- Overall frontend: >80%

Report Contents:
- Coverage summary by module
- Uncovered lines/branches
- Critical gaps analysis
- Recommendations for improvement

Run Tests:
Backend:
pytest tests/ --cov=skillmeat --cov-report=html

Frontend:
npm test -- --coverage --watchAll=false
")
```

### Phase 7 Quality Gates

- [ ] All unit tests passing (backend + frontend)
- [ ] All integration tests passing (backend + frontend)
- [ ] E2E test suite covers critical user journeys
- [ ] Accessibility audit passed (WCAG 2.1 AA)
- [ ] Performance benchmarks met (<200ms for source list, <5s for detail fetch)
- [ ] Security validation passed (tag sanitization, XSS prevention)
- [ ] Code coverage >80% across all layers
- [ ] No P0 or P1 bugs
- [ ] All tests runnable in CI/CD pipeline
- [ ] Test results documented and committed

---

## Phase 8: Documentation & Release

**Duration**: 1 day
**Story Points**: 11
**Objective**: Complete documentation for users and developers, enabling feature adoption and future extension.

### Phase 8A: API & Component Documentation (parallel execution)

**Batch 4**: DOC-001, DOC-002, DOC-003, DOC-004

#### DOC-001: API Documentation (1 pt)

```markdown
Task("api-documenter", "DOC-001: API Documentation

File: docs/api/marketplace-sources.md

Structure:

# Marketplace Sources API Documentation

## Overview
Complete API reference for marketplace sources endpoints.

## Base URL
`https://api.skillmeat.local/api/v1` (or similar)

## Authentication
Document authentication requirements.

## Endpoints

### List Sources
GET /marketplace/sources

Query Parameters:
- artifact_type (string, optional): Filter by type
- tags (string[], optional): Filter by tags (AND logic)
- trust_level (string, optional): Filter by trust level
- search (string, optional): Search by name/description
- cursor (string, optional): Pagination cursor

Response: 200 OK with paginated list

Example:
GET /marketplace/sources?artifact_type=skill&tags=ui,async

### Get Source Details
GET /marketplace/sources/{id}

Response: 200 OK with source details

### Get Repository Details
GET /marketplace/sources/{id}/details

Response: 200 OK with description and README

### Create Source
POST /marketplace/sources

Request Body:
- repo_url (string, required)
- user_description (string, optional)
- fetch_repo_details (boolean, optional)
- tags (string[], optional)

Response: 201 Created

### Update Source
PUT /marketplace/sources/{id}

Request Body:
- user_description (string, optional)
- tags (string[], optional)

Response: 200 OK

## Response Schemas

SourceResponse:
- id: string
- repo_url: string
- counts_by_type: object (type -> count)
- repo_description: string | null (max 2000 chars)
- repo_readme: string | null (max 50KB)
- tags: string[] (max 20 items)
- created_at: ISO 8601 timestamp
- updated_at: ISO 8601 timestamp

## Error Responses
- 400: Invalid parameters
- 401: Unauthorized
- 404: Not found
- 422: Validation error
- 500: Server error

## Common Use Cases
- List all sources
- Filter sources by type
- Filter sources by tags
- View source details
- Import new source with tags

## Rate Limiting
Document limits if applicable.
")
```

#### DOC-002: Component Documentation (1 pt)

```markdown
Task("documentation-writer", "DOC-002: Component Documentation

Files:
  - docs/components/SourceFilterBar.md
  - docs/components/SourceCard.md
  - docs/components/RepoDetailsModal.md
  - docs/components/source-components.md

# SourceFilterBar Component

**File**: skillmeat/web/components/marketplace/SourceFilterBar.tsx

**Purpose**: Multi-control filter bar for filtering marketplace sources

**Usage**:
\`\`\`tsx
import { SourceFilterBar } from '@/components/marketplace/SourceFilterBar';

<SourceFilterBar
  onFilterChange={handleFilterChange}
  loading={isLoading}
/>
\`\`\`

**Props**:
- onFilterChange: (filters: SourceFilters) => void
- loading?: boolean
- disabled?: boolean
- className?: string

**Features**:
- Artifact type filter
- Tags multi-select filter
- Filter clear button
- Responsive design

# SourceCard Component

**File**: skillmeat/web/components/marketplace/SourceCard.tsx

**Purpose**: Display source in list with tags and counts

**Usage**:
\`\`\`tsx
import { SourceCard } from '@/components/marketplace/SourceCard';

<SourceCard source={source} onTagClick={handleTagFilter} />
\`\`\`

**Props**:
- source: Source
- onTagClick?: (tag: string) => void
- className?: string

**Features**:
- Source info display
- Artifact type badge
- Tag badges with colors
- Count breakdown
- Click to navigate detail

# RepoDetailsModal Component

**File**: skillmeat/web/components/marketplace/RepoDetailsModal.tsx

**Purpose**: Modal display of repository description and README

**Usage**:
\`\`\`tsx
import { RepoDetailsModal } from '@/components/marketplace/RepoDetailsModal';

<RepoDetailsModal
  source={source}
  isOpen={showModal}
  onClose={handleClose}
/>
\`\`\`

**Props**:
- source: Source with details
- isOpen: boolean
- onClose: () => void
- className?: string

**Features**:
- Scrollable content
- Keyboard navigation (Escape to close)
- Responsive layout
- Accessible
")
```

#### DOC-003: User Guide - Source Import (1 pt)

```markdown
Task("documentation-writer", "DOC-003: User Guide - Source Import

File: docs/guides/user/source-import.md

# Importing Sources - User Guide

## Overview

The source import feature allows you to add new artifact sources to your marketplace collection. Sources can include repository details (description and README) and custom tags for organization.

## Prerequisites

- Access to SkillMeat web interface
- Repository URL (GitHub, GitHub-like, etc.)

## Basic Import

1. Navigate to Marketplace Sources page
2. Click 'Add Source' button
3. Enter repository URL
4. Click 'Import'
5. Source appears in list

## Import with Repository Details

Repository details include:
- Repository description
- README file content

### Enable Details Fetch

1. Click 'Add Source'
2. Check 'Fetch Repository Details' toggle
3. Enter repository URL
4. Click 'Import'
5. System fetches description and README
6. Details available on source detail page

**Note**: README fetched up to 50KB, description up to 2000 characters.

## Import with Tags

Tags help organize and filter sources.

### Add Tags During Import

1. Click 'Add Source'
2. Enter repository URL
3. Scroll to 'Tags' section
4. Type tag name or select from suggestions
5. Press Enter to add
6. Repeat for additional tags (max 20)
7. Click 'Import'

### Tag Format

- Alphanumeric characters, hyphens, underscores
- 1-50 characters per tag
- Maximum 20 tags per source
- Case-insensitive (lowercase recommended)

### Best Practices for Tags

- Use lowercase (python, not Python)
- Keep short and memorable (async, not asynchronous)
- Consistent naming (backend, not back-end)
- Examples: python, fastapi, testing, cli, library

## Full Import Workflow

Complete example:

1. Navigate to Marketplace Sources
2. Click 'Add Source'
3. Enter: anthropics/claude-tools
4. Check 'Fetch Repository Details'
5. Add tags: claude, ai, tools, verified
6. Click 'Import'
7. Source imported with details and tags
8. View details on detail page

## After Import

- Source appears in list
- Searchable and filterable
- Details available on detail page
- Tags help with organization
- Can be edited after import

## Troubleshooting

**Import failed**: Check repository URL and network access
**Details not fetching**: Check repository is public
**Tags not saving**: Ensure valid tag format (alphanumeric + hyphens/underscores)
")
```

#### DOC-004: User Guide - Filtering (1 pt)

```markdown
Task("documentation-writer", "DOC-004: User Guide - Filtering

File: docs/guides/user/source-filtering.md

# Filtering Sources - User Guide

## Overview

Filtering helps you find sources matching specific criteria. Available filters include artifact type and tags.

## Filter Controls

The filter bar at top of sources list includes:

1. **Artifact Type**: Filter by skill, command, agent, etc.
2. **Tags**: Multi-select filter by tags
3. **Clear**: Reset all filters

## Filtering by Artifact Type

### Single Type

1. Click 'Type' dropdown
2. Select artifact type (e.g., 'skill')
3. List updates to show only that type
4. Count shows number of results

### Clear Type Filter

1. Click 'Type' dropdown
2. Select type again to deselect
3. Or click 'Clear Filters' button

## Filtering by Tags

### Single Tag

1. Click 'Tags' filter button
2. Popover shows all available tags with counts
3. Click checkbox next to tag
4. List updates to show sources with that tag

### Multiple Tags (AND Logic)

1. Click 'Tags' filter button
2. Select multiple tags via checkboxes
3. List shows sources with ALL selected tags
4. Example: Select 'python' AND 'fastapi' = sources with both tags

### Search in Tags

1. Click 'Tags' filter button
2. Type in search box
3. Tag list filters to matches
4. Select desired tags

## Combining Filters

Apply multiple filters together:

1. Select artifact type
2. Select tags
3. List shows sources matching ALL criteria

Example:
- Type: skill
- Tags: python, async
- Result: Skills tagged with both python AND async

## Clear Filters

**Option 1**: Click 'Clear Filters' button

**Option 2**:
- Click filter
- Deselect all selections

## Filter Persistence

Filters persist when:
- Navigating to detail page and back
- Reloading page (stored in URL)
- Sharing URL with others

Filters lost when:
- Clearing filters explicitly
- Navigating to different section

## Click Tag to Filter

Quick filter on source card:

1. On sources list, hover over source card
2. Click tag badge
3. Filter applied automatically
4. List updates to show sources with that tag

## Keyboard Navigation

In filter controls:
- Tab: Move between controls
- Arrow keys: Navigate options
- Space: Select/deselect
- Escape: Close dropdowns

## Tips & Tricks

- **Quick filter**: Click tag on card to filter immediately
- **Multiple tags**: AND logic means more specific results
- **Pagination**: Filters apply across all pages
- **URL sharing**: Filtered URL can be shared

## Common Workflows

### Find Python Async Libraries

1. Click 'Tags' filter
2. Select: python, async, library
3. View filtered results
4. Click result for details

### Find All Skills

1. Click 'Type' dropdown
2. Select: skill
3. View all available skills
4. Filter further by tags if needed

### Find Framework-Specific Tools

1. Click 'Tags' filter
2. Select framework tag (e.g., fastapi)
3. View tools/skills for that framework
4. Click for details

## Troubleshooting

**Filter not working**: Ensure selections are applied (checkboxes checked)
**No results**: Try fewer filters or clear filters
**Tag not showing**: Tag may have zero sources - try different tag

## Need Help?

- Hover over filter icons for tooltips
- Use keyboard shortcuts
- See component documentation for details
")
```

### Phase 8B: Architecture & Release Documentation (parallel execution)

**Batch 5**: DOC-005, DOC-006, DOC-007, DOC-008

#### DOC-005: ADR - Repository Metadata Storage (1 pt)

```markdown
Task("documentation-writer", "DOC-005: ADR - Repository Metadata Storage

File: .claude/adrs/marketplace-sources/metadata-storage-strategy.md

# ADR: Repository Metadata Storage Strategy

## Status
ACCEPTED

## Context

The marketplace sources feature needs to store repository metadata (description and README) alongside source information. Key considerations:

1. **Storage Location**: Store in manifest file vs separate storage
2. **Truncation**: Limit description and README sizes
3. **Backwards Compatibility**: Handle existing sources without metadata
4. **Update Strategy**: How to refresh metadata over time

## Decision

Store repository metadata in the source manifest entry with truncation:
- Description: Maximum 2000 characters
- README: Maximum 50KB (51200 bytes)
- Metadata optional (can be null if not fetched)
- Stored as separate fields, not user description

## Rationale

### Why Not Separate Storage

- Adds complexity
- Requires separate sync/update logic
- Manifest should be self-contained
- Single file simplifies backup/restore

### Why Truncation Limits

- Prevents manifest bloat (1000+ sources = GB scale)
- Keeps responses performant
- Most useful info in first 2000 chars
- Typical README ≤50KB

### Why Optional

- Respects user choice (don't fetch for performance)
- Backwards compatible with existing sources
- Can be added later without migration

### Why Separate Fields

- User description is editable, metadata is read-only
- Clear distinction in API and storage
- Allows independent updates

## Implementation

```python
class Source(BaseModel):
    id: str
    repo_url: str
    user_description: Optional[str] = None  # Editable
    repo_description: Optional[str] = None  # From GitHub
    repo_readme: Optional[str] = None       # From GitHub (up to 50KB)
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime
```

Truncation in service layer:

```python
def truncate_description(desc: str) -> str:
    return desc[:2000] if desc else None

def truncate_readme(readme: str) -> str:
    return readme[:51200] if readme else None
```

## Backwards Compatibility

Existing sources without metadata:
- repo_description: null
- repo_readme: null
- Can be fetched on-demand with update endpoint
- No migration required

## Alternatives Considered

### Alt 1: Dynamic Fetch (No Storage)
- Pros: Always current
- Cons: Slower, rate limit issues, no offline access

### Alt 2: Separate Database Table
- Pros: Flexible schema
- Cons: Added complexity, sync challenges

### Alt 3: Infinite Size
- Pros: No truncation
- Cons: Manifest bloat, performance issues

## Consequences

### Positive
- Simple to implement and maintain
- Self-contained in manifest
- Good performance
- Backwards compatible
- Clear data model

### Negative
- Outdated metadata (won't auto-refresh)
- Some information lost in truncation
- User can't edit metadata (read-only)

### Mitigation
- Document truncation limits clearly
- Provide update endpoint for refresh
- Show full data in browser (fetch on-demand)

## Future Enhancements

1. **Auto-Refresh**: Periodic update of metadata
2. **Version Control**: Track metadata changes
3. **Partial Updates**: Update only metadata
4. **Storage Backend**: Move to separate storage if needed
")
```

#### DOC-006: ADR - Filtering Implementation (1 pt)

```markdown
Task("documentation-writer", "DOC-006: ADR - Filtering Implementation

File: .claude/adrs/marketplace-sources/filtering-implementation.md

# ADR: Source Filtering Implementation

## Status
ACCEPTED

## Context

The marketplace needs to filter sources by artifact type and tags. Key decisions:

1. **Filter Logic**: AND vs OR for multiple tags
2. **Query Format**: How to pass filters in URL/API
3. **Performance**: Efficient filtering with many sources/tags
4. **Extensibility**: Support for future filters

## Decision

### Filter Logic: AND Semantics

Multiple tags use AND logic (intersection):
- Select: python AND fastapi
- Result: Sources tagged with BOTH python AND fastapi
- NOT: Sources with either tag (OR)

### Query Format

URL query parameters:
```
GET /marketplace/sources?artifact_type=skill&tags=python,fastapi
```

API parameters:
```python
artifact_type: Optional[str] = Query(None)
tags: Optional[str] = Query(None)  # CSV format
```

Backend parses as:
```python
tags = ["python", "fastapi"]  # AND logic
```

## Rationale

### Why AND for Tags

- More useful for specific searches
- Intuitive for power users
- Follows database conventions
- Matches UI checkbox behavior (all checked = all must match)

### Why CSV Format

- Compact in URL
- Standard query parameter format
- Easy to parse
- Human-readable

### Why Query Parameters

- RESTful convention
- Browser cacheable
- Shareable URLs
- Stateless

## Implementation

Backend filtering logic:

```python
def filter_sources(
    artifact_type: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> List[Source]:
    query = Source.query()

    # Filter by type (OR within type if multiple)
    if artifact_type:
        query = query.filter(Source.artifact_type == artifact_type)

    # Filter by tags (AND logic - all tags must match)
    if tags:
        for tag in tags:
            query = query.filter(Source.tags.contains(tag))

    return query.all()
```

URL examples:
```
/sources                          # All sources
/sources?artifact_type=skill      # All skills
/sources?tags=python              # Sources with 'python' tag
/sources?tags=python,fastapi      # Sources with BOTH python AND fastapi
/sources?artifact_type=skill&tags=python  # Skills with python tag
```

## Alternatives Considered

### Alt 1: OR Logic for Tags
- Pros: Broader results
- Cons: Less specific, confusing UI
- Rejected: AND is more useful

### Alt 2: Advanced Query Format
- Pros: More flexible
- Cons: Complex parsing, confusing URL
- Rejected: Keep it simple

### Alt 3: JSON Body
- Pros: More flexible
- Cons: Not cacheable, violates REST
- Rejected: Query params are standard

## Backwards Compatibility

- Endpoints without filters work as before
- New filters are optional parameters
- No breaking changes
- Can be added to existing sources

## Future Enhancements

1. **OR Logic**: Support OR for tags (future filter type toggle)
   - UI: Filter type selector (AND/OR)
   - API: &tags_logic=or parameter

2. **Advanced Search**: Full-text search integration
   - &search=query parameter
   - Searches name, description, README

3. **Trust Level**: Filter by trust level
   - &trust_level=verified,trusted parameter

4. **Composite Filters**: Complex expressions
   - Conditional logic
   - Nested filters

## Performance Considerations

### Indexing Strategy

Database indexes needed:
- artifact_type (btree)
- tags (gin for array containment)
- created_at (for sorting)

Query plan:
1. Filter by artifact_type (index seek)
2. Filter by tags (index intersection)
3. Sort by created_at
4. Paginate with cursor

Expected performance:
- 1000 sources: <50ms
- 10000 sources: <100ms
- 100000+ sources: <200ms (with proper indexing)

## Monitoring

Track metrics:
- Filter query latency (P50, P95, P99)
- Most common filters
- Filter cache hit rate (if caching added)

## Documentation

User-facing:
- Filter guide with examples
- Keyboard shortcuts
- URL sharing examples

Developer-facing:
- API parameter documentation
- Filter implementation details
- Extension instructions
")
```

#### DOC-007: Release Notes (1 pt)

```markdown
Task("documentation-writer", "DOC-007: Release Notes

File: CHANGELOG.md (add section for this release)

# Release Notes - Marketplace Sources Enhancement v1.0.0

## Overview

Major feature release adding comprehensive source management with filtering, repository details, and tag-based organization.

## New Features

### Source Filtering (NEW)

Filter marketplace sources by:
- **Artifact Type**: Filter by skill, command, agent, etc.
- **Tags**: Multi-select filter with AND logic
- **Combined**: Use multiple filters together

Filter behavior:
- Multiple tags use AND logic (all must match)
- Filters persist in URL for sharing
- Keyboard accessible
- Mobile friendly

Examples:
- Filter by type: skill
- Filter by tags: python AND fastapi
- Combined: type=skill AND tags=python,fastapi

### Repository Metadata (NEW)

Sources can now include repository information:
- **Description**: Repository description (up to 2000 chars)
- **README**: Repository README file (up to 50KB)

Available on source detail page in 'Repo Details' modal.

Enable during import with 'Fetch Repository Details' toggle.

### Source Tagging (NEW)

Organize sources with tags:
- Create tags during source import
- Add/remove tags on existing sources
- Maximum 20 tags per source
- Tag format: alphanumeric, hyphens, underscores

Tag-based filtering:
- Click tag on card to filter
- Select multiple tags with AND logic
- Auto-complete suggestions

## UI Improvements

### New Components

- **SourceFilterBar**: Multi-control filter interface
- **SourceCard**: Enhanced with tags and type badge
- **RepoDetailsModal**: Display repository description and README
- **TagBadge**: Colored tag display with hover info
- **CountBadge**: Artifact type count breakdown

### Enhanced Pages

- **Marketplace Sources List**: Now with filtering controls
- **Source Detail Page**: Includes tags, repo details modal, artifact filtering

### Responsive Design

- All new components work on mobile
- Touch-friendly controls (44px+ targets)
- Responsive filter bar layout
- Modal works on all screen sizes

## API Changes

### New Endpoints

```
GET /api/v1/marketplace/sources?artifact_type=skill&tags=python,fastapi
GET /api/v1/marketplace/sources/{id}/details
```

### Request/Response Changes

SourceResponse now includes:
- counts_by_type: {type: count}
- repo_description: string (optional, max 2000)
- repo_readme: string (optional, max 50KB)
- tags: string[] (max 20)

CreateSourceRequest:
- fetch_repo_details: boolean (optional)
- tags: string[] (optional)

UpdateSourceRequest:
- tags: string[] (optional)

### Query Parameters

GET /marketplace/sources:
- artifact_type: Optional[str]
- tags: Optional[string] (CSV format)
- search: Optional[str]
- cursor: Optional[str]

## Breaking Changes

None. All changes are additive and backwards compatible.

## Migration Guide

### Existing Integrations

If using marketplace sources API:

1. **No action required** for basic functionality
2. To use new features:
   - Add artifact_type filter: ?artifact_type=skill
   - Add tags filter: ?tags=python,fastapi
   - Fetch details: Pass fetch_repo_details=true

### Existing Sources

Existing sources without metadata:
- Still accessible
- Can be fetched on-demand
- Tags can be added via update endpoint
- No migration required

### URL Format Changes

Sources list filtering via URL:
- Old: /marketplace/sources (no filtering)
- New: /marketplace/sources?artifact_type=skill&tags=python

Filters persist for sharing and bookmarking.

## Performance

Performance benchmarks:
- GET /marketplace/sources: <200ms (500+ sources)
- GET /marketplace/sources with filters: <200ms
- GET /marketplace/sources/{id}/details: <5s (includes GitHub fetch)
- Tag filtering: <100ms (20+ tags)

## Security

Security enhancements:
- Input validation on tags (whitelist format)
- XSS prevention on user content
- Rate limiting on GitHub API calls
- All user input sanitized

## Accessibility

WCAG 2.1 AA compliant:
- Full keyboard navigation
- Screen reader support
- Color contrast 4.5:1
- Touch targets 44px+
- Reduced motion support

## Known Issues

- Repository details fetch limited to public repositories
- README truncated to 50KB for performance
- Description truncated to 2000 chars

## Deprecations

None.

## Future Roadmap

- Advanced search syntax
- OR logic option for tags
- Tag-based access control
- Auto-refresh of repository metadata
- Tag analytics and metrics

## Contributors

- [Development team]

## Upgrade Instructions

### For Users

1. New filter controls available on Marketplace Sources page
2. Import new sources with tags and repository details
3. Filter existing sources by type and tags

### For Developers

1. New API query parameters available
2. SourceResponse includes new fields
3. Can add tags to imported sources
4. New components available for custom integrations

## Support

For issues or questions:
- Check user guides in docs/guides/user/
- See API documentation in docs/api/
- File issues on project repository

## Changelog

See detailed commit history for implementation details.
")
```

#### DOC-008: Development Guide - Extending (1 pt)

```markdown
Task("documentation-writer", "DOC-008: Development Guide - Extending

File: docs/guides/development/extending-marketplace-sources.md

# Development Guide: Extending Marketplace Sources

## Overview

This guide explains how to extend the marketplace sources feature with new filters, fields, or functionality.

## Architecture

### Layer Structure

```
Frontend: React components (SourceFilterBar, SourceCard, etc.)
   ↓
API: FastAPI routers (/marketplace/sources)
   ↓
Service: Business logic (filtering, validation)
   ↓
Repository: Database access (SQL queries)
   ↓
Database: PostgreSQL with artifact/tag/source tables
```

### Data Flow

```
User Action → Component → API → Service → Repository → Database
                  ↑                                          ↓
                  ← Response JSON ←  ← Pydantic Schema ←
```

## Adding a New Filter

Example: Add 'trust_level' filter

### 1. Database

Add filter field if needed:

```python
# models/source.py
class Source(Base):
    trust_level: str = Column(String(50), nullable=True)  # verified, trusted, community
```

### 2. Schema

Update request/response schemas:

```python
# schemas/source_schemas.py
class SourceResponse(BaseModel):
    trust_level: Optional[str] = None

class CreateSourceRequest(BaseModel):
    trust_level: Optional[str] = None
```

### 3. Repository

Add filter method:

```python
# repositories/source_repository.py
def filter_by_trust_level(self, trust_level: str):
    return self.session.query(Source).filter(
        Source.trust_level == trust_level
    )
```

### 4. Service

Update filtering logic:

```python
# services/source_service.py
def list_sources_filtered(
    self,
    artifact_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
    trust_level: Optional[str] = None,  # New
) -> List[Source]:
    query = self.repository.get_all()

    if artifact_type:
        query = query.filter_by_artifact_type(artifact_type)
    if tags:
        query = query.filter_by_tags(tags)
    if trust_level:  # New
        query = query.filter_by_trust_level(trust_level)

    return query.all()
```

### 5. Router

Add query parameter:

```python
# routers/marketplace_sources.py
@router.get('/sources')
async def list_sources(
    artifact_type: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    trust_level: Optional[str] = Query(None),  # New
):
    return service.list_sources_filtered(
        artifact_type=artifact_type,
        tags=tags.split(',') if tags else None,
        trust_level=trust_level,  # New
    )
```

### 6. Frontend

Add filter control:

```typescript
// components/SourceFilterBar.tsx
<select
  value={filters.trustLevel || ''}
  onChange={(e) => onFilterChange({
    ...filters,
    trustLevel: e.target.value || null
  })}
>
  <option value="">All Levels</option>
  <option value="verified">Verified</option>
  <option value="trusted">Trusted</option>
  <option value="community">Community</option>
</select>
```

### 7. Tests

Add test cases for new filter:

```python
# tests/integration/test_trust_level_filter.py
def test_filter_by_trust_level():
    # Setup: Create sources with different trust levels
    # Execute: Filter by trust_level=verified
    # Assert: Only verified sources returned
```

## Adding a New Source Field

Example: Add 'license' field

### 1-5: Same as filter above

### 6. Frontend Display

Add to SourceCard:

```typescript
// components/SourceCard.tsx
<div className="source-license">{source.license}</div>
```

Add to Detail Page:

```typescript
// components/SourceDetail.tsx
<FieldDisplay label="License" value={source.license} />
```

### 7-8: Tests

Test serialization and display.

## Performance Optimization

### Caching Filter Results

If filtering becomes slow:

```python
# services/source_service.py
from functools import lru_cache

@lru_cache(maxsize=128)
def list_sources_filtered(
    artifact_type: Optional[str] = None,
    tags: Optional[Tuple[str]] = None,  # Tuple for hashing
):
    # Implementation
```

### Database Indexing

Add indexes for filters:

```python
# models/source.py
class Source(Base):
    artifact_type = Column(String, index=True)
    trust_level = Column(String, index=True)
    tags = Column(ARRAY(String), index=True)  # GIN index
```

### Pagination Optimization

Use cursor-based pagination:

```python
# Efficient for large datasets
def list_sources_with_cursor(cursor: str = None, limit: int = 50):
    query = Source.query()
    if cursor:
        query = query.filter(Source.id > decode_cursor(cursor))
    return query.limit(limit + 1).all()
```

## Extending Tag System

### More Tags Per Source

Increase from 20:

```python
# Validation logic
if len(tags) > 100:
    raise ValidationError("Maximum 100 tags")
```

### Tag Namespaces

Organize tags by prefix:

```python
# Tags: python:3.9, python:3.10, framework:django
class Tag(Base):
    name: str  # python:3.9
    namespace: str  # python
    value: str  # 3.9
```

### Tag Aliases

Support tag synonyms:

```python
# Aliases: py → python, dj → django
class TagAlias(Base):
    alias: str
    target_tag_id: int
```

## Testing Extensions

### Unit Tests

Test service logic:

```python
def test_filter_with_new_parameter():
    # Arrange
    service = SourceService()
    sources = [create_test_source(...), ...]

    # Act
    filtered = service.filter_sources(new_param=value)

    # Assert
    assert len(filtered) == expected_count
```

### Integration Tests

Test API endpoint:

```python
async def test_new_filter_endpoint():
    response = await client.get('/sources?new_param=value')
    assert response.status_code == 200
    assert len(response.json()['data']) == expected
```

### Frontend Tests

Test component:

```typescript
test('applies new filter', () => {
  const { getByText } = render(<SourceFilterBar />);
  fireEvent.click(getByText('New Filter'));
  expect(mockOnChange).toHaveBeenCalledWith({
    ...expectedFilters,
    newParam: value
  });
});
```

## Backwards Compatibility

When adding fields:

```python
# Old API response
{
  'id': '123',
  'repo_url': 'user/repo',
  'tags': ['python']
}

# New API response (backwards compatible)
{
  'id': '123',
  'repo_url': 'user/repo',
  'tags': ['python'],
  'new_field': 'value'  # Optional, doesn't break old clients
}
```

Ensure new fields are optional in requests:

```python
class CreateSourceRequest(BaseModel):
    repo_url: str  # Required
    new_field: Optional[str] = None  # Optional
```

## Monitoring & Observability

Add logging for extensions:

```python
import logging

logger = logging.getLogger(__name__)

def filter_sources(new_param: str):
    logger.info(f'Filtering with new_param={new_param}')
    # Implementation
```

Track metrics:

```python
from prometheus_client import Counter

filter_counter = Counter(
    'marketplace_sources_filters_applied',
    'Filters applied',
    ['filter_type']
)

filter_counter.labels(filter_type='trust_level').inc()
```

## Documentation

When extending:

1. **Update API docs** - Add new parameters, examples
2. **Update component docs** - New props, usage examples
3. **Update user guides** - How to use new features
4. **Update this guide** - Add extension examples
5. **Update changelog** - New features/changes

## Common Patterns

### Filter with Validation

```python
def filter_by_field(field_value: str) -> List[Source]:
    if not isinstance(field_value, str):
        raise ValidationError('Invalid field type')
    return session.query(Source).filter(
        Source.field == field_value
    ).all()
```

### Optional Nested Field

```python
class SourceDetail(BaseModel):
    id: str
    metadata: Optional[Dict[str, Any]] = None
```

### Pagination Helper

```python
def paginate(query, limit: int, cursor: str):
    if cursor:
        query = query.filter(Source.id > decode_cursor(cursor))
    items = query.limit(limit + 1).all()
    next_cursor = encode_cursor(items[-1].id) if len(items) > limit else None
    return items[:limit], next_cursor
```

## Resources

- Architecture docs: `docs/architecture/`
- API patterns: `.claude/context/key-context/router-patterns.md`
- Component patterns: `.claude/context/key-context/component-patterns.md`
- Testing patterns: `.claude/context/key-context/testing-patterns.md`
- Database models: `skillmeat/storage/models/`
- Implementation plan: Reference the PRD
")
```

### Phase 8 Quality Gates

- [ ] All API endpoints documented with request/response examples
- [ ] All components documented with usage examples and props
- [ ] User guides cover all major workflows (import, filtering, navigation)
- [ ] ADRs explain key decisions (metadata storage, filtering logic)
- [ ] Release notes accurate and complete
- [ ] Development guide enables extension
- [ ] No documentation TODOs or placeholders
- [ ] Documentation reviewed and merged to main
- [ ] All links valid and references correct

---

## Quality Gates Summary

### Phase 7 - Testing (18 pts)

Complete testing layer ensuring quality, performance, security, and accessibility:

**Unit & Integration Testing** (9 pts):
- Backend unit tests (3 pts): >80% coverage for services, schemas, validation
- Backend integration tests (2 pts): >80% coverage for API endpoints
- Frontend unit tests (2 pts): >80% coverage for components and hooks
- Frontend integration tests (2 pts): >80% coverage for pages and interactions

**E2E & Accessibility Testing** (5 pts):
- E2E source import (2 pts): Complete user journey testing
- E2E filtering (2 pts): Filter functionality and combinations
- E2E repo details (1 pt): Modal interaction and content
- Accessibility audit (2 pts): WCAG 2.1 AA compliance validation

**Performance & Security** (4 pts):
- Performance testing (1 pt): <200ms for sources list, <5s for detail fetch
- Security testing (1 pt): Input validation, XSS prevention, sanitization
- Coverage report (1 pt): >80% across all layers, no critical gaps

**Gate Checkpoints**:
- All tests passing (unit, integration, E2E)
- Accessibility compliance verified
- Performance benchmarks met
- Security validation passed
- Code coverage >80%
- No P0/P1 bugs
- CI/CD pipeline green

### Phase 8 - Documentation (11 pts)

Complete documentation enabling feature adoption and extension:

**API & Component Docs** (4 pts):
- API documentation (1 pt): All endpoints, parameters, examples
- Component documentation (1 pt): All components with usage and props
- User guide - import (1 pt): Step-by-step import instructions
- User guide - filtering (1 pt): Filter usage and best practices

**Architecture & Release** (7 pts):
- ADR - metadata storage (1 pt): Explains storage decisions
- ADR - filtering (1 pt): Explains filter design and logic
- Release notes (1 pt): Features, changes, migration guide
- Development guide (1 pt): Extend filters, add fields, testing

**Gate Checkpoints**:
- All documentation complete and accurate
- No TODOs or placeholders
- Links valid and references correct
- User guides clear and comprehensive
- Developer guides enable extension
- Release notes reviewed and accurate

---

## Orchestration Strategy

### Phase 7 Execution Plan (3 days)

**Day 1 - Unit & Integration Tests**:
- Batch 1 (parallel): TEST-001, TEST-002, TEST-003, TEST-004
- 4 subagents working in parallel
- Estimated completion: 1 day

**Day 2 - E2E & Accessibility**:
- Batch 2 (parallel): TEST-005, TEST-006, TEST-007, TEST-008
- 4 subagents working in parallel
- Estimated completion: 1 day

**Day 3 - Performance, Security, Coverage**:
- Batch 3 (parallel): TEST-009, TEST-010, TEST-011
- 3 subagents working in parallel
- Estimated completion: 1 day

### Phase 8 Execution Plan (1 day)

**Day 4 - Documentation**:
- Batch 4 (parallel): DOC-001, DOC-002, DOC-003, DOC-004
  - API documenter + 3 documentation writers
  - Estimated completion: 4-6 hours
- Batch 5 (parallel): DOC-005, DOC-006, DOC-007, DOC-008
  - 4 documentation writers
  - Can start after Batch 4 or in parallel
  - Estimated completion: 2-4 hours

### Dependencies Summary

**Testing Phase**:
- Batch 1 (unit/integration): Independent, can start immediately
- Batch 2 (E2E/a11y): Depends on Batch 1 completion
- Batch 3 (perf/security): Depends on Batch 2 completion

**Documentation Phase**:
- All doc tasks: Depend on Phase 7 completion (TEST-011)
- Batch 4 & 5: Can run in parallel

---

## Progress Tracking

Use this file to track:
- Task status updates (pending → in_progress → completed)
- Completion dates
- Blockers and issues
- Test results
- Coverage metrics

Update via CLI:
```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/marketplace-sources-enhancement-v1/phase-7-8-progress.md \
  -t TEST-001 -s completed
```
