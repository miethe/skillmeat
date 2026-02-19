---
title: 'Phases 7-8: Testing & Documentation'
description: Quality assurance, testing, and documentation for marketplace sources
  enhancement
parent: ../marketplace-sources-enhancement-v1.md
phases:
- 7
- 8
status: inferred_complete
schema_version: 2
doc_type: phase_plan
feature_slug: marketplace-sources-enhancement
prd_ref: null
plan_ref: null
---
# Phases 7-8: Testing & Documentation

**Parent Plan**: [Marketplace Sources Enhancement v1](../marketplace-sources-enhancement-v1.md)

---

## Phase 7: Testing & Quality Assurance

**Duration**: 3 days
**Dependencies**: All implementation phases complete
**Assigned Subagent(s)**: python-backend-engineer, frontend-developer, testing specialist, web-accessibility-checker
**Start after**: Phase 6 complete

### Phase 7A: Unit & Integration Tests (1 day)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| TEST-001 | Backend Unit Tests | Unit tests for tag validation, counts_by_type computation, filter logic | Tests cover: tag format validation (alphanumeric+hyphens+underscores), tag limit enforcement (max 20), counts_by_type aggregation, filter AND logic | 3 pts | python-backend-engineer | SVC-005 |
| TEST-002 | Backend Integration Tests | Integration tests for API endpoints with various filter combinations | Tests cover: GET /marketplace/sources with all filter params, filter composition (multiple params), pagination, error cases | 2 pts | python-backend-engineer | API-009 |
| TEST-003 | Frontend Unit Tests | Unit tests for components and hooks | Tests cover: SourceFilterBar filter state changes, tag badge overflow logic, count badge tooltip display, filter change callbacks | 2 pts | frontend-developer | DIALOG-006 |
| TEST-004 | Frontend Integration Tests | Integration tests for pages and component interactions | Tests cover: sources list page with filters, URL state sync, source detail page artifact filtering, modal display | 2 pts | frontend-developer | DIALOG-006 |

### Phase 7B: End-to-End & Accessibility Tests (1 day)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| TEST-005 | E2E Tests - Source Import | User journey: import source with details and tags, verify stored correctly | Test: navigate to add source, enable toggles, add tags, submit, verify source appears in list with details | 2 pts | testing specialist | DIALOG-006 |
| TEST-006 | E2E Tests - Filtering | User journey: apply filters, verify results match criteria | Test: apply artifact_type filter, apply tags filter, combine filters, verify results; click tag on card to filter | 2 pts | testing specialist | PAGE-007 |
| TEST-007 | E2E Tests - Repo Details | User journey: view source detail, open repo details modal, verify content | Test: click "Repo Details" button, modal opens, displays description and README, scrollable | 1 pt | testing specialist | PAGE-007 |
| TEST-008 | Accessibility Audit | WCAG 2.1 AA compliance testing for all new components and pages | Tests cover: color contrast (4.5:1 for text), keyboard navigation (Tab through all interactive elements), screen reader compatibility, focus visible, ARIA labels | 2 pts | web-accessibility-checker | TEST-007 |

### Phase 7C: Performance & Security Testing (1 day)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| TEST-009 | Performance Testing | Verify response times meet targets | Tests: GET /marketplace/sources with 500+ sources returns <200ms; detail fetch completes <5s | 1 pt | python-backend-engineer | TEST-004 |
| TEST-010 | Security Testing | Validate tag input sanitization, XSS prevention, rate limiting | Tests: tag validation whitelist enforced, no special chars accepted, XSS attempts fail, rate limiting on GitHub API calls | 1 pt | python-backend-engineer | TEST-008 |
| TEST-011 | Coverage Report | Generate coverage reports for all layers | Acceptance: backend coverage >80%, frontend coverage >80%, no critical gaps | 1 pt | testing specialist | TEST-010 |

### Phase 7 Quality Gates

- [ ] All unit tests passing (backend + frontend)
- [ ] All integration tests passing
- [ ] E2E test suite covers critical user journeys
- [ ] Accessibility audit passed (WCAG 2.1 AA)
- [ ] Performance benchmarks met (<200ms for source list, <5s for detail fetch)
- [ ] Security validation passed (tag sanitization, XSS prevention)
- [ ] Code coverage >80% across all layers
- [ ] No P0 or P1 bugs
- [ ] All tests runnable in CI/CD pipeline

**Notes**: Use pytest + pytest-cov for backend testing; Jest + React Testing Library for frontend unit/integration tests; Playwright for E2E tests. Accessibility testing can use axe-core automated + manual testing.

---

## Phase 8: Documentation & Release

**Duration**: 1 day
**Dependencies**: Phase 7 complete (all implementation done, tests passing)
**Assigned Subagent(s)**: documentation-writer, api-documenter
**Start after**: Phase 7 testing complete and all tests passing

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| DOC-001 | API Documentation | Complete OpenAPI spec documentation for all new endpoints | Docs include: SourceResponse schema, CreateSourceRequest/UpdateSourceRequest, all filter parameters, example requests/responses | 1 pt | api-documenter | TEST-011 |
| DOC-002 | Component Documentation | Create Storybook docs for new components | Docs include: SourceFilterBar, SourceCard, RepoDetailsModal, TagBadge, CountBadge with examples and states | 1 pt | documentation-writer | TEST-011 |
| DOC-003 | User Guide - Source Import | Write user guide for importing sources with details and tags | Guide explains: how to enable repo details fetch, how to add tags, expectations for when details fetch | 1 pt | documentation-writer | TEST-011 |
| DOC-004 | User Guide - Filtering | Write user guide for filtering sources in marketplace | Guide explains: available filters (artifact type, tags, trust level), how to combine filters, how to clear filters | 1 pt | documentation-writer | TEST-011 |
| DOC-005 | ADR - Repository Metadata Storage | Create ADR documenting decision on storing description/README in manifest | ADR explains: why separate from user description, truncation strategy for README, backwards compatibility approach | 1 pt | documentation-writer | TEST-011 |
| DOC-006 | ADR - Filtering Implementation | Create ADR documenting filter design and AND logic choice | ADR explains: why AND semantics chosen over OR, query parameter format, future considerations (OR, advanced search) | 1 pt | documentation-writer | TEST-011 |
| DOC-007 | Release Notes | Write release notes with migration guidance | Notes include: new fields in SourceResponse, new query parameters, UI changes, backward compatibility info | 1 pt | documentation-writer | TEST-011 |
| DOC-008 | Development Guide - Extending | Write guide for developers to extend filtering or add new source metadata | Guide explains: how to add new filters, how to add new source fields, backwards compatibility considerations | 1 pt | documentation-writer | TEST-011 |

### Phase 8 Quality Gates

- [ ] All API endpoints documented with examples
- [ ] All components documented with usage examples
- [ ] User guides cover all major workflows
- [ ] ADRs explain key decisions (metadata storage, filtering)
- [ ] Release notes complete and accurate
- [ ] No documentation TODOs or placeholders
- [ ] Documentation reviewed and approved

**Notes**: Leverage existing documentation patterns in the codebase. API docs should be auto-generated from OpenAPI spec (FastAPI Swagger). Component docs should use Storybook or similar component documentation tool.

---

## Documentation Files

| File | Phase | New/Update |
|------|-------|-----------|
| `docs/api/endpoints/marketplace-sources.md` | 8 | Update with new endpoints and parameters |
| `docs/components/source-components.md` | 8 | Document SourceCard, FilterBar, Modal |
| `docs/guides/user/source-import.md` | 8 | User guide for importing with details |
| `docs/guides/user/source-filtering.md` | 8 | User guide for filtering sources |
| `.claude/adrs/metadata-storage-strategy.md` | 8 | ADR on repository metadata storage |
| `.claude/adrs/filtering-implementation.md` | 8 | ADR on filter design |
| `CHANGELOG.md` | 8 | Release notes |

---

## Test Scenarios Checklist

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
- [ ] POST /marketplace/sources without toggles skips detail fetch
- [ ] POST /marketplace/sources with tags stores tags
- [ ] PUT /marketplace/sources/{id} updates tags
- [ ] GET /marketplace/sources/{id}/details returns description and README

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

## OpenAPI Specification Preview

```yaml
paths:
  /api/v1/marketplace/sources:
    get:
      summary: List marketplace sources with optional filtering
      parameters:
        - name: artifact_type
          in: query
          schema: { type: string }
          description: "Filter by artifact type (skill, command, agent, etc.)"
        - name: tags
          in: query
          schema: { type: array, items: { type: string } }
          description: "Filter by tags (AND logic - all tags must match)"
        - name: trust_level
          in: query
          schema: { type: string, enum: [verified, trusted, community] }
          description: "Filter by trust level"
        - name: search
          in: query
          schema: { type: string }
          description: "Search by source name or user description"
        - name: cursor
          in: query
          schema: { type: string }
          description: "Pagination cursor"
      responses:
        '200':
          description: Paginated list of sources

  /api/v1/marketplace/sources/{id}/details:
    get:
      summary: Get repository details (description and README)
      parameters:
        - name: id
          in: path
          required: true
          schema: { type: string }
      responses:
        '200':
          description: Repository details
          content:
            application/json:
              schema:
                type: object
                properties:
                  repo_description:
                    type: string
                    nullable: true
                  repo_readme:
                    type: string
                    nullable: true

components:
  schemas:
    SourceResponse:
      type: object
      properties:
        id: { type: string }
        repo_url: { type: string }
        counts_by_type:
          type: object
          additionalProperties: { type: integer }
        repo_description:
          type: string
          nullable: true
          maxLength: 2000
        repo_readme:
          type: string
          nullable: true
          maxLength: 51200
        tags:
          type: array
          items: { type: string }
          maxItems: 20
```
