---
status: inferred_complete
---
 ---
title: "Implementation Plan: Catalog Entry Modal Enhancement with File Contents Preview"
description: "Detailed implementation plan for adding file tree and content preview to marketplace catalog modals"
prd: "docs/project_plans/PRDs/features/catalog-entry-modal-enhancement-v1.md"
complexity: "Large (L)"
track: "Full Track"
estimated_effort: "34 story points"
timeline: "10-12 days (2 weeks with buffer)"
created: 2025-12-28
updated: 2025-12-28
status: "draft"
tags: [implementation-plan, marketplace, ui, github, caching]
related:
  - /docs/project_plans/PRDs/features/catalog-entry-modal-enhancement-v1.md
  - /skillmeat/web/components/CatalogEntryModal.tsx
  - /skillmeat/api/routers/marketplace_sources.py
---

# Implementation Plan: Catalog Entry Modal Enhancement with File Contents Preview

**Complexity**: Large (L) | **Track**: Full Track (Haiku + Sonnet + Opus)
**Estimated Effort**: 34 story points | **Timeline**: 10-12 days (2 weeks with buffer)

---

## Executive Summary

This implementation plan details the transformation of the simple catalog entry modal into a rich preview experience. Users will be able to browse file trees and read syntax-highlighted contents for marketplace artifacts before importing, eliminating blind imports and context switching to GitHub.

**Key Deliverables**:
- Backend API endpoints for GitHub file tree and content fetching
- Intelligent caching layer (frontend: 5min/30min, backend: 1hr/2hr)
- Enhanced catalog modal with Overview + Contents tabs
- Read-only mode for FileTree and ContentPane components
- Rate limit handling and error states
- Comprehensive testing suite (unit, integration, E2E, accessibility)

**Success Metrics**:
- Import conversion rate: +15%
- GitHub API calls: -80% (via caching)
- File content load time: <2s (cached), <5s (uncached)
- Test coverage: >80%

---

## Implementation Phases

### Phase 1: Backend File Fetching (3 days, 13 story points)

**Goal**: Enable GitHub file tree and content fetching with caching layer.

**Dependencies**: None (can start immediately)

**Layer Sequencing**:
1. **Service Layer**: GitHubClient enhancements (TASK-1.1, TASK-1.2)
2. **Caching Layer**: Backend cache implementation (TASK-1.5)
3. **API Layer**: Router endpoints (TASK-1.3, TASK-1.4)
4. **Validation**: Rate limit handling (TASK-1.6)
5. **Testing**: Unit tests (TASK-1.7)
6. **Documentation**: OpenAPI spec (TASK-1.8)

**Acceptance Criteria**:
- [ ] GitHubClient can fetch file trees and individual file contents
- [ ] Backend cache reduces GitHub API calls by 70%+ for repeated requests
- [ ] Rate limit errors (HTTP 403) are detected and handled gracefully
- [ ] All endpoints return proper DTOs (Pydantic models)
- [ ] Unit tests achieve >80% coverage for new code
- [ ] OpenAPI spec updated with new endpoints

### Phase 2: Frontend Modal Enhancement (4 days, 14 story points)

**Goal**: Create tabbed catalog modal with file browser and content viewer.

**Dependencies**: Phase 1 complete (requires backend endpoints)

**UI Sequencing**:
1. **Component Preparation**: Add read-only props to FileTree and ContentPane (TASK-2.1, TASK-2.2)
2. **Modal Refactor**: Add tab layout to CatalogEntryModal (TASK-2.3, TASK-2.4)
3. **Contents Tab**: Integrate FileTree + ContentPane (TASK-2.5)
4. **Data Layer**: TanStack Query hooks (TASK-2.6)
5. **UX Polish**: Loading states and error handling (TASK-2.7, TASK-2.8)
6. **Caching**: Configure staleTime and cacheTime (TASK-2.9)
7. **Styling**: Match unified-entity-modal design (TASK-2.10)

**Acceptance Criteria**:
- [ ] Modal has Overview and Contents tabs with proper navigation
- [ ] FileTree displays artifact file structure in read-only mode
- [ ] ContentPane shows syntax-highlighted file contents (no edit controls)
- [ ] TanStack Query caches file trees (5min) and contents (30min)
- [ ] Loading skeletons appear during data fetch
- [ ] Rate limit errors show user-friendly retry UI
- [ ] Design matches unified-entity-modal patterns (Radix UI, Tailwind)

### Phase 3: Polish & Testing (3 days, 7 story points)

**Goal**: Ensure production-ready quality with comprehensive testing and documentation.

**Dependencies**: Phase 2 complete (requires full feature implementation)

**Quality Sequencing**:
1. **UX Polish**: Auto-select default file, truncation handling (TASK-3.1, TASK-3.2, TASK-3.3)
2. **Integration Testing**: GitHub API error scenarios (TASK-3.4)
3. **E2E Testing**: User workflow validation (TASK-3.5)
4. **Accessibility**: Keyboard nav, screen reader audit (TASK-3.6)
5. **Performance**: Cache hit rate and load time validation (TASK-3.7)
6. **Security**: XSS and path traversal review (TASK-3.8)
7. **Documentation**: User guide and ADR (TASK-3.9, TASK-3.10)

**Acceptance Criteria**:
- [ ] First .md file auto-selected in Contents tab (or first alphabetically)
- [ ] Files >1MB truncated with "View full file on GitHub" link
- [ ] Integration tests cover GitHub 403, 404, timeout scenarios
- [ ] E2E test validates full user workflow (browse → preview → import)
- [ ] WCAG 2.1 AA compliance for keyboard nav and screen readers
- [ ] Performance test confirms cache hit rate >70%
- [ ] Security audit passes (no XSS, path traversal vulnerabilities)
- [ ] User documentation and ADR published

---

## Task Breakdown

### Phase 1: Backend File Fetching

| Task ID | Description | Acceptance Criteria | Estimate | Assigned Agent | Dependencies |
|---------|-------------|-------------------|----------|----------------|--------------|
| TASK-1.1 | Add `get_file_tree()` to GitHubClient | Method returns list of file paths, types, sizes from GitHub Tree API. Handles recursive trees. | 0.5d (2 pts) | python-backend-engineer | None |
| TASK-1.2 | Add `get_file_content()` to GitHubClient | Method returns file content (base64-decoded), encoding, size, SHA from GitHub Contents API. | 0.5d (2 pts) | python-backend-engineer | None |
| TASK-1.3 | Create file tree endpoint | `GET /marketplace/sources/{id}/artifacts/{path}/files` returns cached file tree DTO. | 1d (3 pts) | python-backend-engineer | TASK-1.1, TASK-1.5 |
| TASK-1.4 | Create file content endpoint | `GET /marketplace/sources/{id}/artifacts/{path}/files/{file_path}` returns cached content DTO. | 1d (3 pts) | python-backend-engineer | TASK-1.2, TASK-1.5 |
| TASK-1.5 | Implement backend caching layer | LRU cache with max 1000 entries. TTL: 1hr (trees), 2hr (contents). Keys: `tree:{source_id}:{artifact_path}:{sha}`, `content:{source_id}:{artifact_path}:{file_path}:{sha}`. | 0.5d (2 pts) | python-backend-engineer | None |
| TASK-1.6 | Add rate limit detection | Detect GitHub HTTP 403 with `X-RateLimit-Remaining: 0`. Return HTTP 429 with `Retry-After` header. | 0.25d (1 pt) | python-backend-engineer | TASK-1.3, TASK-1.4 |
| TASK-1.7 | Unit tests for file endpoints | Test happy path, 404 errors, rate limits, cache hits/misses. Coverage >80%. | 0.25d (1 pt) | python-backend-engineer | TASK-1.3, TASK-1.4, TASK-1.6 |
| TASK-1.8 | Update OpenAPI spec | Add `/files` and `/files/{file_path}` endpoints to OpenAPI schema with request/response models. | 0.25d (1 pt) | documentation-writer | TASK-1.3, TASK-1.4 | ✓ COMPLETE |

**Phase 1 Total**: 3 days, 13 story points

**Parallelization Opportunities**:
- **Batch 1** (Parallel): TASK-1.1, TASK-1.2, TASK-1.5 (no dependencies)
- **Batch 2** (Sequential): TASK-1.3, TASK-1.4 (depends on Batch 1)
- **Batch 3** (Sequential): TASK-1.6, TASK-1.7, TASK-1.8 (depends on Batch 2)

### Phase 2: Frontend Modal Enhancement

| Task ID | Description | Acceptance Criteria | Estimate | Assigned Agent | Dependencies |
|---------|-------------|-------------------|----------|----------------|--------------|
| TASK-2.1 | Add read-only mode to FileTree | Add `readOnly: boolean` prop. When true, hide create/delete file buttons. | 0.5d (2 pts) | ui-engineer-enhanced | None |
| TASK-2.2 | Add read-only mode to ContentPane | Add `readOnly: boolean` prop. When true, hide edit/save buttons, disable Monaco editor editing. | 0.5d (2 pts) | ui-engineer-enhanced | None |
| TASK-2.3 | Refactor CatalogEntryModal for tabs | Add Radix UI Tabs component with Overview and Contents tabs. Maintain existing layout. | 0.5d (2 pts) | ui-engineer-enhanced | None |
| TASK-2.4 | Implement Overview tab | Migrate existing metadata display (badges, confidence scores, metadata grid, action buttons) to Overview tab. | 0.25d (1 pt) | ui-engineer-enhanced | TASK-2.3 |
| TASK-2.5 | Implement Contents tab | Add FileTree (left) + ContentPane (right) layout. Wire file selection to update content pane. | 1d (3 pts) | ui-engineer-enhanced | TASK-2.1, TASK-2.2, TASK-2.3, TASK-2.6 |
| TASK-2.6 | Create TanStack Query hooks | `useCatalogFileTree(sourceId, artifactPath)` and `useCatalogFileContent(sourceId, artifactPath, filePath)` hooks. | 0.5d (2 pts) | ui-engineer-enhanced | TASK-1.3, TASK-1.4 |
| TASK-2.7 | Add loading skeletons | Skeleton for file tree (3 rows) and content pane (code editor placeholder) during fetch. | 0.25d (1 pt) | ui-engineer | TASK-2.5 |
| TASK-2.8 | Add error states | Rate limit error: "GitHub rate limit reached. Try again in X minutes." Fetch error: "Failed to load file. Try again or View on GitHub." | 0.5d (2 pts) | ui-engineer | TASK-2.5 |
| TASK-2.9 | Configure TanStack Query caching | Set `staleTime: 5 * 60 * 1000` (5min) for file trees, `30 * 60 * 1000` (30min) for file contents. `cacheTime: 30min/2hr`. | 0.25d (1 pt) | ui-engineer | TASK-2.6 |
| TASK-2.10 | Style tab layout | Match unified-entity-modal design: tab triggers in DialogHeader, content area max-w-6xl, proper spacing. | 0.25d (1 pt) | ui-engineer | TASK-2.3, TASK-2.4, TASK-2.5 |

**Phase 2 Total**: 4 days, 14 story points

**Parallelization Opportunities**:
- **Batch 1** (Parallel): TASK-2.1, TASK-2.2, TASK-2.3 (no internal dependencies)
- **Batch 2** (Parallel after Phase 1 + Batch 1): TASK-2.4, TASK-2.6 (depends on Phase 1 endpoints)
- **Batch 3** (Sequential): TASK-2.5 (depends on Batch 1 + Batch 2)
- **Batch 4** (Parallel): TASK-2.7, TASK-2.8, TASK-2.9, TASK-2.10 (depends on TASK-2.5)

### Phase 3: Polish & Testing

| Task ID | Description | Acceptance Criteria | Estimate | Assigned Agent | Dependencies |
|---------|-------------|-------------------|----------|----------------|--------------|
| TASK-3.1 | Auto-select default file | When Contents tab opens, auto-select first `.md` file (case-insensitive). Fallback: first file alphabetically. | 0.25d (1 pt) | ui-engineer | TASK-2.5 |
| TASK-3.2 | Implement file size truncation | Backend: Truncate files >1MB to first 10,000 lines. Return `truncated: true` in response. | 0.25d (1 pt) | python-backend-engineer | TASK-1.4 |
| TASK-3.3 | Add truncation UI | Frontend: Show warning banner "Large file truncated. [View full file on GitHub]" when `truncated: true`. | 0.25d (1 pt) | ui-engineer | TASK-3.2 |
| TASK-3.4 | Integration tests for GitHub errors | Test rate limit (403), not found (404), timeout scenarios. Mock GitHub API responses. | 0.5d (2 pts) | python-backend-engineer | TASK-1.3, TASK-1.4, TASK-1.6 |
| TASK-3.5 | E2E test for file preview | Playwright test: Navigate to source detail → click catalog entry → click Contents tab → select file → verify content displays. | 0.5d (2 pts) | ui-engineer | TASK-2.5 |
| TASK-3.6 | Accessibility audit | Keyboard nav: Tab through file tree, Enter to select, Arrow keys to expand/collapse. Screen reader: ARIA labels for tree items, content pane. | 0.5d (2 pts) | ui-engineer-enhanced | TASK-2.5 |
| TASK-3.7 | Performance testing | Measure cache hit rate (target >70%), file tree load time (<3s), content load time (<2s cached, <5s uncached). | 0.5d (2 pts) | python-backend-engineer | TASK-1.5, TASK-2.9 |
| TASK-3.8 | Security review | Validate file paths (no `../`), sanitize content before Monaco editor, CSP headers for XSS prevention. | 0.25d (1 pt) | python-backend-engineer | TASK-1.3, TASK-1.4 |
| TASK-3.9 | User documentation | Add "Previewing Catalog Artifacts" section to user guide. Include screenshots of Contents tab. | 0.25d (1 pt) | documentation-writer | TASK-2.5 |
| TASK-3.10 | Create ADR for caching | Document caching strategy: TTLs, invalidation rules, cache key format, LRU eviction policy. | 0.25d (1 pt) | documentation-complex | TASK-1.5, TASK-2.9 |

**Phase 3 Total**: 3 days, 7 story points

**Parallelization Opportunities**:
- **Batch 1** (Parallel): TASK-3.1, TASK-3.2 (independent UX improvements)
- **Batch 2** (Sequential): TASK-3.3 (depends on TASK-3.2)
- **Batch 3** (Parallel): TASK-3.4, TASK-3.5, TASK-3.6, TASK-3.7, TASK-3.8 (testing suite, all depend on Phase 2)
- **Batch 4** (Parallel): TASK-3.9, TASK-3.10 (documentation, depends on feature completion)

---

## Dependency Mapping

### Cross-Phase Dependencies

```
Phase 1 (Backend) → Phase 2 (Frontend)
  TASK-1.3 → TASK-2.6 (file tree endpoint → TanStack Query hook)
  TASK-1.4 → TASK-2.6 (file content endpoint → TanStack Query hook)

Phase 2 (Frontend) → Phase 3 (Testing)
  TASK-2.5 → TASK-3.1, TASK-3.5, TASK-3.6 (Contents tab → UX polish and E2E)
  TASK-2.9 → TASK-3.7 (caching config → performance tests)

Phase 1 (Backend) → Phase 3 (Testing)
  TASK-1.5 → TASK-3.7 (backend cache → performance tests)
  TASK-1.6 → TASK-3.4 (rate limit handling → integration tests)
```

### Intra-Phase Dependencies

**Phase 1**:
- TASK-1.1, TASK-1.2, TASK-1.5 (no dependencies) → TASK-1.3, TASK-1.4 → TASK-1.6 → TASK-1.7, TASK-1.8

**Phase 2**:
- TASK-2.1, TASK-2.2, TASK-2.3 (no dependencies) → TASK-2.4, TASK-2.6 → TASK-2.5 → TASK-2.7, TASK-2.8, TASK-2.9, TASK-2.10

**Phase 3**:
- TASK-3.1, TASK-3.2 (no dependencies) → TASK-3.3 → TASK-3.4, TASK-3.5, TASK-3.6, TASK-3.7, TASK-3.8 → TASK-3.9, TASK-3.10

---

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation Strategy | Contingency Plan |
|------|--------|------------|-------------------|------------------|
| GitHub rate limits exceeded frequently | High | Medium | Aggressive caching (5min/30min frontend, 1hr/2hr backend). Encourage PAT usage in UI. | Queue requests with exponential backoff. Show "high demand" message with retry timer. |
| Large artifacts (>100 files) cause slow loads | Medium | Low | Lazy-load file tree (fetch on expand). Show file count warning for >50 files. | Implement pagination for file list. Add "View on GitHub" fallback. |
| GitHub API downtime blocks preview | Medium | Low | Graceful degradation: show cached data if available. Prominent "View on GitHub" fallback button. | Display last-cached timestamp. Allow import even if preview unavailable. |
| XSS via malicious file contents | High | Low | Sanitize all content before Monaco editor. Use CSP headers. Trusted syntax highlighter only. | Code review all content rendering. Add security tests. |
| Users confused by read-only mode | Low | Medium | Clear UI indicators: "Preview only - import to edit" banner. Tooltips on disabled buttons. | Add onboarding tooltip on first Contents tab visit. |
| Backend cache memory bloat | Medium | Medium | LRU eviction with max 1000 entries. Monitor memory usage. | Reduce cache TTL if memory issues. Add cache size alerts. |
| Complex file tree hierarchy causes UI issues | Low | Low | Limit tree depth visualization to 5 levels. Collapse deeply nested folders by default. | Add breadcrumb navigation for deep paths. |

---

## Quality Gates

### Phase 1 Quality Gate (Backend)
- [ ] All unit tests pass (>80% coverage)
- [ ] OpenAPI spec validates (no schema errors)
- [ ] Rate limit handling tested with mocked GitHub 403 responses
- [ ] Backend cache hit rate >70% in local testing
- [ ] No security vulnerabilities (path traversal, injection)

**Gate Owner**: python-backend-engineer
**Approval Required**: Code review by Opus (architecture validation)

### Phase 2 Quality Gate (Frontend)
- [ ] Modal renders correctly on all screen sizes (mobile, tablet, desktop)
- [ ] TanStack Query hooks configured with correct staleTime/cacheTime
- [ ] Loading skeletons appear during data fetch (no blank screens)
- [ ] Error states display user-friendly messages (no raw error objects)
- [ ] Design matches unified-entity-modal patterns (Radix UI, Tailwind)

**Gate Owner**: ui-engineer-enhanced
**Approval Required**: Visual review by Opus (UX consistency)

### Phase 3 Quality Gate (Testing & Documentation)
- [ ] All tests pass: unit (>80% coverage), integration, E2E, accessibility
- [ ] Performance benchmarks met: <3s file tree, <2s content (cached)
- [ ] Security audit complete: no XSS, path traversal, or injection vulnerabilities
- [ ] Documentation complete: user guide, ADR, OpenAPI spec
- [ ] Feature flag `ENABLE_CATALOG_FILE_PREVIEW` toggles feature correctly

**Gate Owner**: python-backend-engineer (backend tests), ui-engineer (frontend tests), documentation-complex (docs)
**Approval Required**: Final review by Opus (comprehensive validation)

---

## Orchestration Quick Reference

### Phase 1: Backend File Fetching

**Batch 1 (Parallel)**:
```
Task("python-backend-engineer", "TASK-1.1: Add get_file_tree() method to GitHubClient class in skillmeat/core/marketplace/github_client.py. Use GitHub Tree API (/repos/{owner}/{repo}/git/trees/{sha}?recursive=1). Return list of {path, type, size}. Handle rate limits.")
Task("python-backend-engineer", "TASK-1.2: Add get_file_content() method to GitHubClient class. Use GitHub Contents API (/repos/{owner}/{repo}/contents/{path}?ref={sha}). Decode base64 content. Return {content, encoding, size, sha}.")
Task("python-backend-engineer", "TASK-1.5: Implement backend caching layer in skillmeat/api/utils/cache.py. LRU cache with max 1000 entries. TTL: 1hr (trees), 2hr (contents). Key format: tree:{source_id}:{artifact_path}:{sha}, content:{source_id}:{artifact_path}:{file_path}:{sha}.")
```

**Batch 2 (Sequential after Batch 1)**:
```
Task("python-backend-engineer", "TASK-1.3: Create GET /marketplace/sources/{id}/artifacts/{path}/files endpoint in skillmeat/api/routers/marketplace_sources.py. Call GitHubClient.get_file_tree(). Return cached DTO with file list. Dependencies: TASK-1.1, TASK-1.5.")
Task("python-backend-engineer", "TASK-1.4: Create GET /marketplace/sources/{id}/artifacts/{path}/files/{file_path} endpoint. Call GitHubClient.get_file_content(). Return cached DTO with file content. Dependencies: TASK-1.2, TASK-1.5.")
```

**Batch 3 (Sequential after Batch 2)**:
```
Task("python-backend-engineer", "TASK-1.6: Add rate limit detection to file endpoints. Detect GitHub HTTP 403 with X-RateLimit-Remaining: 0. Return HTTP 429 with Retry-After header. Dependencies: TASK-1.3, TASK-1.4.")
Task("python-backend-engineer", "TASK-1.7: Write unit tests for file endpoints in tests/api/routers/test_marketplace_sources.py. Test happy path, 404, rate limits, cache hits/misses. Coverage >80%. Dependencies: TASK-1.3, TASK-1.4, TASK-1.6.")
Task("documentation-writer", "TASK-1.8: Update OpenAPI spec in skillmeat/api/server.py with new /files endpoints. Add request/response schemas. Dependencies: TASK-1.3, TASK-1.4.")
```

### Phase 2: Frontend Modal Enhancement

**Batch 1 (Parallel)**:
```
Task("ui-engineer-enhanced", "TASK-2.1: Add readOnly prop to FileTree component in skillmeat/web/components/entity/file-tree.tsx. When true, hide create/delete file buttons. Disable drag-and-drop.")
Task("ui-engineer-enhanced", "TASK-2.2: Add readOnly prop to ContentPane component in skillmeat/web/components/entity/content-pane.tsx. When true, hide edit/save buttons, set Monaco editor readOnly: true.")
Task("ui-engineer-enhanced", "TASK-2.3: Refactor CatalogEntryModal in skillmeat/web/components/CatalogEntryModal.tsx to use Radix UI Tabs. Add Overview and Contents tabs.")
```

**Batch 2 (Parallel after Phase 1 + Batch 1)**:
```
Task("ui-engineer-enhanced", "TASK-2.4: Implement Overview tab in CatalogEntryModal. Migrate existing metadata display (badges, confidence scores, metadata grid, action buttons). Dependencies: TASK-2.3.")
Task("ui-engineer-enhanced", "TASK-2.6: Create TanStack Query hooks in skillmeat/web/hooks/use-catalog-files.ts. useCatalogFileTree(sourceId, artifactPath) and useCatalogFileContent(sourceId, artifactPath, filePath). Dependencies: TASK-1.3, TASK-1.4.")
```

**Batch 3 (Sequential)**:
```
Task("ui-engineer-enhanced", "TASK-2.5: Implement Contents tab in CatalogEntryModal. Add FileTree (left) + ContentPane (right) layout. Wire file selection to update content pane. Dependencies: TASK-2.1, TASK-2.2, TASK-2.3, TASK-2.6.")
```

**Batch 4 (Parallel)**:
```
Task("ui-engineer", "TASK-2.7: Add loading skeletons to Contents tab. File tree: 3 skeleton rows. Content pane: code editor placeholder. Dependencies: TASK-2.5.")
Task("ui-engineer", "TASK-2.8: Add error states to Contents tab. Rate limit: 'GitHub rate limit reached. Try again in X minutes.' Fetch error: 'Failed to load file. Try again or View on GitHub.' Dependencies: TASK-2.5.")
Task("ui-engineer", "TASK-2.9: Configure TanStack Query caching in use-catalog-files.ts. staleTime: 5min (trees), 30min (contents). cacheTime: 30min/2hr. Dependencies: TASK-2.6.")
Task("ui-engineer", "TASK-2.10: Style tab layout in CatalogEntryModal to match unified-entity-modal. Tab triggers in DialogHeader, content area max-w-6xl, proper spacing. Dependencies: TASK-2.3, TASK-2.4, TASK-2.5.")
```

### Phase 3: Polish & Testing

**Batch 1 (Parallel)**:
```
Task("ui-engineer", "TASK-3.1: Auto-select default file in Contents tab. Select first .md file (case-insensitive), fallback to first file alphabetically. Dependencies: TASK-2.5.")
Task("python-backend-engineer", "TASK-3.2: Implement file size truncation in GitHubClient.get_file_content(). Truncate files >1MB to first 10,000 lines. Return truncated: true in DTO. Dependencies: TASK-1.4.")
```

**Batch 2 (Sequential)**:
```
Task("ui-engineer", "TASK-3.3: Add truncation UI to ContentPane. Show warning banner 'Large file truncated. [View full file on GitHub]' when truncated: true. Dependencies: TASK-3.2.")
```

**Batch 3 (Parallel)**:
```
Task("python-backend-engineer", "TASK-3.4: Write integration tests for GitHub API errors in tests/integration/test_github_client.py. Test rate limit (403), not found (404), timeout. Mock GitHub responses. Dependencies: TASK-1.3, TASK-1.4, TASK-1.6.")
Task("ui-engineer", "TASK-3.5: Write E2E test for file preview in tests/e2e/catalog-preview.spec.ts. Playwright: Navigate to source detail → click catalog entry → click Contents tab → select file → verify content. Dependencies: TASK-2.5.")
Task("ui-engineer-enhanced", "TASK-3.6: Accessibility audit for Contents tab. Keyboard nav: Tab through tree, Enter to select, Arrow keys for expand/collapse. Screen reader: ARIA labels. Dependencies: TASK-2.5.")
Task("python-backend-engineer", "TASK-3.7: Performance testing for caching. Measure cache hit rate (>70%), file tree load (<3s), content load (<2s cached, <5s uncached). Dependencies: TASK-1.5, TASK-2.9.")
Task("python-backend-engineer", "TASK-3.8: Security review for file endpoints. Validate paths (no ../), sanitize content, CSP headers for XSS. Dependencies: TASK-1.3, TASK-1.4.")
```

**Batch 4 (Parallel)**:
```
Task("documentation-writer", "TASK-3.9: Add 'Previewing Catalog Artifacts' section to user guide in docs/user-guide.md. Include screenshots of Contents tab. Dependencies: TASK-2.5.")
Task("documentation-complex", "TASK-3.10: Create ADR for caching strategy in docs/architecture/decisions/ADR-XXX-catalog-file-caching.md. Document TTLs, invalidation, cache keys, LRU eviction. Dependencies: TASK-1.5, TASK-2.9.")
```

---

## Architecture Validation Notes

**MeatyPrompts Layered Architecture Compliance**:
- **Database Layer**: Not applicable (file-based GitHub source)
- **Repository Layer**: GitHubClient serves as repository for GitHub data
- **Service Layer**: GitHubClient enhancements (get_file_tree, get_file_content)
- **API Layer**: Router endpoints in marketplace_sources.py
- **UI Layer**: CatalogEntryModal enhancement with FileTree + ContentPane
- **Testing Layer**: Unit, integration, E2E tests across all phases
- **Documentation Layer**: OpenAPI spec, user guide, ADR
- **Deployment Layer**: Feature flag `ENABLE_CATALOG_FILE_PREVIEW`

**Sequencing Rationale**:
1. **Backend First**: API endpoints must exist before frontend can consume them
2. **Component Prep**: Read-only mode added to reusable components before integration
3. **Modal Refactor**: Tab structure before tab content implementation
4. **Integration**: Wire data fetching after both backend and component layers ready
5. **Polish**: UX improvements and testing after core functionality complete

**Caching Strategy**:
- **Two-Layer Cache**: Frontend (TanStack Query) + Backend (LRU)
- **Aggressive TTLs**: Balance freshness (5min/30min) vs API conservation (1hr/2hr)
- **Invalidation**: Source rescan clears all cache for that source_id
- **Overflow Protection**: LRU eviction at 1000 entries prevents memory bloat

**Error Handling Strategy**:
- **Rate Limits**: Detect GitHub 403 → Return HTTP 429 with Retry-After
- **Frontend**: Display countdown timer, suggest PAT authentication
- **Fallback**: "View on GitHub" button always available as escape hatch
- **Graceful Degradation**: Show cached data during revalidation failures

---

## Success Criteria Summary

**Functional Success**:
- [ ] Users can browse file tree and view contents for catalog artifacts
- [ ] Read-only mode prevents editing until artifact is imported
- [ ] Caching reduces GitHub API calls by 80%
- [ ] Rate limits handled gracefully with user feedback

**Technical Success**:
- [ ] Follows SkillMeat layered architecture (Router → Manager → GitHubClient)
- [ ] All responses use DTOs (Pydantic models)
- [ ] Components reuse FileTree and ContentPane with read-only props
- [ ] TanStack Query manages all data fetching and caching

**Quality Success**:
- [ ] Test coverage >80% (unit, integration, E2E)
- [ ] WCAG 2.1 AA accessibility compliance
- [ ] No security vulnerabilities (XSS, path traversal)
- [ ] Performance targets met (<3s tree, <2s content cached)

**Documentation Success**:
- [ ] OpenAPI spec complete and validated
- [ ] User guide updated with preview feature
- [ ] ADR documents caching architecture decisions
- [ ] Component documentation includes read-only mode usage

---

## Linear Import Data

**Epic Structure**:
- **EPIC-1**: Backend File API (TASK-1.1 to TASK-1.8)
- **EPIC-2**: Frontend Modal Enhancement (TASK-2.1 to TASK-2.10)
- **EPIC-3**: Polish & Quality (TASK-3.1 to TASK-3.10)

**Task Import Format** (CSV):
```csv
ID,Title,Description,Estimate,Status,Epic,Dependencies
TASK-1.1,Add get_file_tree() to GitHubClient,Method returns list of file paths/types/sizes from GitHub Tree API. Handles recursive trees.,2,To Do,EPIC-1,
TASK-1.2,Add get_file_content() to GitHubClient,Method returns file content (base64-decoded) with encoding/size/SHA from GitHub Contents API.,2,To Do,EPIC-1,
TASK-1.3,Create file tree endpoint,GET /marketplace/sources/{id}/artifacts/{path}/files returns cached file tree DTO.,3,To Do,EPIC-1,TASK-1.1 TASK-1.5
TASK-1.4,Create file content endpoint,GET /marketplace/sources/{id}/artifacts/{path}/files/{file_path} returns cached content DTO.,3,To Do,EPIC-1,TASK-1.2 TASK-1.5
TASK-1.5,Implement backend caching layer,LRU cache with max 1000 entries. TTL: 1hr (trees) 2hr (contents).,2,To Do,EPIC-1,
TASK-1.6,Add rate limit detection,Detect GitHub HTTP 403 with X-RateLimit-Remaining: 0. Return HTTP 429 with Retry-After.,1,To Do,EPIC-1,TASK-1.3 TASK-1.4
TASK-1.7,Unit tests for file endpoints,Test happy path 404 rate limits cache hits/misses. Coverage >80%.,1,To Do,EPIC-1,TASK-1.3 TASK-1.4 TASK-1.6
TASK-1.8,Update OpenAPI spec,Add /files endpoints to OpenAPI schema with request/response models.,1,To Do,EPIC-1,TASK-1.3 TASK-1.4
TASK-2.1,Add read-only mode to FileTree,Add readOnly prop. When true hide create/delete buttons.,2,To Do,EPIC-2,
TASK-2.2,Add read-only mode to ContentPane,Add readOnly prop. When true hide edit/save buttons disable Monaco editing.,2,To Do,EPIC-2,
TASK-2.3,Refactor CatalogEntryModal for tabs,Add Radix UI Tabs with Overview and Contents tabs.,2,To Do,EPIC-2,
TASK-2.4,Implement Overview tab,Migrate existing metadata display to Overview tab.,1,To Do,EPIC-2,TASK-2.3
TASK-2.5,Implement Contents tab,Add FileTree + ContentPane layout. Wire file selection.,3,To Do,EPIC-2,TASK-2.1 TASK-2.2 TASK-2.3 TASK-2.6
TASK-2.6,Create TanStack Query hooks,useCatalogFileTree and useCatalogFileContent hooks.,2,To Do,EPIC-2,TASK-1.3 TASK-1.4
TASK-2.7,Add loading skeletons,Skeleton for file tree and content pane during fetch.,1,To Do,EPIC-2,TASK-2.5
TASK-2.8,Add error states,Rate limit and fetch error user-friendly messages.,2,To Do,EPIC-2,TASK-2.5
TASK-2.9,Configure TanStack Query caching,Set staleTime: 5min (trees) 30min (contents). cacheTime: 30min/2hr.,1,To Do,EPIC-2,TASK-2.6
TASK-2.10,Style tab layout,Match unified-entity-modal design: tabs in DialogHeader max-w-6xl.,1,To Do,EPIC-2,TASK-2.3 TASK-2.4 TASK-2.5
TASK-3.1,Auto-select default file,Select first .md file or fallback to first alphabetically.,1,To Do,EPIC-3,TASK-2.5
TASK-3.2,Implement file size truncation,Truncate files >1MB to first 10000 lines. Return truncated: true.,1,To Do,EPIC-3,TASK-1.4
TASK-3.3,Add truncation UI,Show warning banner for truncated files with GitHub link.,1,To Do,EPIC-3,TASK-3.2
TASK-3.4,Integration tests for GitHub errors,Test rate limit 404 timeout scenarios. Mock GitHub API.,2,To Do,EPIC-3,TASK-1.3 TASK-1.4 TASK-1.6
TASK-3.5,E2E test for file preview,Playwright test: navigate to source → open entry → view file.,2,To Do,EPIC-3,TASK-2.5
TASK-3.6,Accessibility audit,Keyboard nav and screen reader compliance for Contents tab.,2,To Do,EPIC-3,TASK-2.5
TASK-3.7,Performance testing,Measure cache hit rate load times. Target: >70% hits <3s tree <2s content.,2,To Do,EPIC-3,TASK-1.5 TASK-2.9
TASK-3.8,Security review,Validate paths sanitize content CSP headers for XSS prevention.,1,To Do,EPIC-3,TASK-1.3 TASK-1.4
TASK-3.9,User documentation,Add Previewing Catalog Artifacts section to user guide.,1,To Do,EPIC-3,TASK-2.5
TASK-3.10,Create ADR for caching,Document caching strategy: TTLs invalidation cache keys LRU eviction.,1,To Do,EPIC-3,TASK-1.5 TASK-2.9
```

---

## Appendices

### Related Files

**Backend**:
- `/skillmeat/api/routers/marketplace_sources.py` - Add file endpoints here
- `/skillmeat/core/marketplace/github_client.py` - Add GitHubClient methods
- `/skillmeat/api/utils/cache.py` - Add backend caching layer
- `/skillmeat/api/schemas/marketplace.py` - Add file DTOs

**Frontend**:
- `/skillmeat/web/components/CatalogEntryModal.tsx` - Refactor for tabs
- `/skillmeat/web/components/entity/unified-entity-modal.tsx` - Reference for design
- `/skillmeat/web/components/entity/file-tree.tsx` - Add read-only mode
- `/skillmeat/web/components/entity/content-pane.tsx` - Add read-only mode
- `/skillmeat/web/hooks/use-catalog-files.ts` - Create TanStack Query hooks
- `/skillmeat/web/lib/api/catalog.ts` - Create API client functions

**Testing**:
- `/tests/api/routers/test_marketplace_sources.py` - Add unit tests
- `/tests/integration/test_github_client.py` - Add integration tests
- `/tests/e2e/catalog-preview.spec.ts` - Add E2E test

**Documentation**:
- `/docs/user-guide.md` - Add preview feature section
- `/docs/architecture/decisions/ADR-XXX-catalog-file-caching.md` - Create caching ADR

### Reference Documentation

- **PRD**: `/docs/project_plans/PRDs/features/catalog-entry-modal-enhancement-v1.md`
- **API Router Patterns**: `/.claude/rules/api/routers.md`
- **API Client Patterns**: `/.claude/rules/web/api-client.md`
- **TanStack Query Patterns**: `/.claude/rules/web/hooks.md`
- **Debugging Rules**: `/.claude/rules/debugging.md`

### Open Questions for Implementation

- [ ] **Q1**: Should backend cache use in-memory LRU or Redis? **Decision**: Start with in-memory (simpler), migrate to Redis if memory issues.
- [ ] **Q2**: Should file tree support search/filter? **Decision**: Not in Phase 1 (YAGNI), revisit if >50 files common.
- [ ] **Q3**: How to handle binary files (images, PDFs)? **Decision**: Show placeholder icon + download link. Inline preview in Phase 2.
- [ ] **Q4**: Rate limit alert threshold? **Decision**: 90% (suggest PAT upgrade in alert).
- [ ] **Q5**: Should Monaco editor be lazy-loaded? **Decision**: Yes, use dynamic import to reduce bundle size.

---

**Next Steps**:
1. Review this plan with team/stakeholders
2. Create Linear epics and tasks using CSV import data
3. Execute Phase 1 with orchestrated batch execution (see Orchestration Quick Reference)
4. Conduct Phase 1 Quality Gate review before proceeding to Phase 2
5. Track progress in `.claude/progress/catalog-entry-modal-enhancement-v1/`
