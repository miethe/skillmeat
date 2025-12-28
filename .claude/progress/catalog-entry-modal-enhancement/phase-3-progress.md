---
type: progress
prd: "catalog-entry-modal-enhancement"
phase: 3
title: "Polish & Testing"
status: pending
progress: 0
total_tasks: 10
completed_tasks: 0
blocked_tasks: 0
created: 2025-12-28
updated: 2025-12-28

tasks:
  - id: "TASK-3.1"
    title: "Auto-select default file"
    status: "pending"
    priority: "medium"
    estimate: "1 pt"
    assigned_to: ["ui-engineer"]
    dependencies: ["TASK-2.5"]
    acceptance: "When Contents tab opens, auto-select first .md file (case-insensitive). Fallback: first file alphabetically."
    files: ["skillmeat/web/components/CatalogEntryModal.tsx"]

  - id: "TASK-3.2"
    title: "Implement file size truncation"
    status: "pending"
    priority: "medium"
    estimate: "1 pt"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.4"]
    acceptance: "Backend: Truncate files >1MB to first 10,000 lines. Return truncated: true in response."
    files: ["skillmeat/core/marketplace/github_scanner.py", "skillmeat/api/schemas/marketplace.py"]

  - id: "TASK-3.3"
    title: "Add truncation UI"
    status: "pending"
    priority: "medium"
    estimate: "1 pt"
    assigned_to: ["ui-engineer"]
    dependencies: ["TASK-3.2"]
    acceptance: "Frontend: Show warning banner 'Large file truncated. [View full file on GitHub]' when truncated: true."
    files: ["skillmeat/web/components/CatalogEntryModal.tsx"]

  - id: "TASK-3.4"
    title: "Integration tests for GitHub errors"
    status: "pending"
    priority: "high"
    estimate: "2 pts"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.3", "TASK-1.4", "TASK-1.6"]
    acceptance: "Test rate limit (403), not found (404), timeout scenarios. Mock GitHub API responses."
    files: ["tests/integration/test_github_client.py"]

  - id: "TASK-3.5"
    title: "E2E test for file preview"
    status: "pending"
    priority: "high"
    estimate: "2 pts"
    assigned_to: ["ui-engineer"]
    dependencies: ["TASK-2.5"]
    acceptance: "Playwright test: Navigate to source detail → click catalog entry → click Contents tab → select file → verify content displays."
    files: ["tests/e2e/catalog-preview.spec.ts"]

  - id: "TASK-3.6"
    title: "Accessibility audit"
    status: "pending"
    priority: "high"
    estimate: "2 pts"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-2.5"]
    acceptance: "Keyboard nav: Tab through file tree, Enter to select, Arrow keys to expand/collapse. Screen reader: ARIA labels for tree items, content pane."
    files: ["skillmeat/web/components/CatalogEntryModal.tsx", "skillmeat/web/components/entity/file-tree.tsx"]

  - id: "TASK-3.7"
    title: "Performance testing"
    status: "pending"
    priority: "medium"
    estimate: "2 pts"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.5", "TASK-2.9"]
    acceptance: "Measure cache hit rate (target >70%), file tree load time (<3s), content load time (<2s cached, <5s uncached)."
    files: ["tests/performance/test_cache_performance.py"]

  - id: "TASK-3.8"
    title: "Security review"
    status: "pending"
    priority: "high"
    estimate: "1 pt"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.3", "TASK-1.4"]
    acceptance: "Validate file paths (no ../), sanitize content before Monaco editor, CSP headers for XSS prevention."
    files: ["skillmeat/api/routers/marketplace_sources.py"]

  - id: "TASK-3.9"
    title: "User documentation"
    status: "pending"
    priority: "low"
    estimate: "1 pt"
    assigned_to: ["documentation-writer"]
    dependencies: ["TASK-2.5"]
    acceptance: "Add 'Previewing Catalog Artifacts' section to user guide. Include screenshots of Contents tab."
    files: ["docs/user-guide.md"]

  - id: "TASK-3.10"
    title: "Create ADR for caching"
    status: "pending"
    priority: "low"
    estimate: "1 pt"
    assigned_to: ["documentation-complex"]
    dependencies: ["TASK-1.5", "TASK-2.9"]
    acceptance: "Document caching strategy: TTLs, invalidation rules, cache key format, LRU eviction policy."
    files: ["docs/architecture/decisions/ADR-XXX-catalog-file-caching.md"]

parallelization:
  batch_1: ["TASK-3.1", "TASK-3.2"]
  batch_2: ["TASK-3.3"]
  batch_3: ["TASK-3.4", "TASK-3.5", "TASK-3.6", "TASK-3.7", "TASK-3.8"]
  batch_4: ["TASK-3.9", "TASK-3.10"]

quality_gate:
  owner: "python-backend-engineer"
  criteria:
    - "First .md file auto-selected in Contents tab (or first alphabetically)"
    - "Files >1MB truncated with 'View full file on GitHub' link"
    - "Integration tests cover GitHub 403, 404, timeout scenarios"
    - "E2E test validates full user workflow (browse → preview → import)"
    - "WCAG 2.1 AA compliance for keyboard nav and screen readers"
    - "Performance test confirms cache hit rate >70%"
    - "Security audit passes (no XSS, path traversal vulnerabilities)"
    - "User documentation and ADR published"

blockers: []

notes:
  - "Phase 3 depends on Phase 2 completion (most tasks need Contents tab)"
  - "TASK-3.2 can start early (only depends on Phase 1)"
---

# Phase 3: Polish & Testing

**Goal**: Ensure production-ready quality with comprehensive testing and documentation.

**Duration**: 3 days | **Effort**: 7 story points

**Dependency**: Phase 2 must be complete (requires full feature implementation)

## Orchestration Quick Reference

### Batch 1 (Parallel - UX Improvements)

```
Task("ui-engineer", "TASK-3.1: Auto-select default file in Contents tab of CatalogEntryModal. When tab activates and file tree loads: find first file ending in .md (case-insensitive), call setSelectedPath. Fallback: select first file alphabetically if no .md files.")

Task("python-backend-engineer", "TASK-3.2: Implement file size truncation in GitHubScanner.get_file_content(). Check decoded content size. If >1MB (1048576 bytes), truncate to first 10,000 lines. Add 'truncated: bool' field to FileContentResponse schema. Set to true when truncated.")
```

### Batch 2 (After TASK-3.2)

```
Task("ui-engineer", "TASK-3.3: Add truncation UI to CatalogEntryModal Contents tab. Check 'truncated' field in file content response. If true, show Alert banner above content: 'Large file truncated. [View full file on GitHub]' with link to upstream_url + file path.")
```

### Batch 3 (Parallel - Testing Suite)

```
Task("python-backend-engineer", "TASK-3.4: Write integration tests for GitHub API errors in tests/integration/test_github_client.py. Test scenarios: rate limit (mock 403 with X-RateLimit-Remaining: 0), file not found (404), request timeout. Use responses or httpx mocking. Verify proper error responses.")

Task("ui-engineer", "TASK-3.5: Write Playwright E2E test for file preview in skillmeat/web/tests/e2e/catalog-preview.spec.ts. Test flow: navigate to /marketplace/sources/{id} → click catalog card → verify modal opens → click Contents tab → verify file tree loads → click file → verify content pane shows code.")

Task("ui-engineer-enhanced", "TASK-3.6: Accessibility audit for Contents tab. Verify: Tab key navigates through file tree items, Enter selects file, Arrow Up/Down moves between files, Arrow Right expands folder, Arrow Left collapses. Add aria-label to tree items, aria-live to content pane for screen readers.")

Task("python-backend-engineer", "TASK-3.7: Performance testing for caching layer. Create test script to: make 100 requests for same file tree, measure cache hit rate (target >70%), measure response times. Log: first request time (<5s), cached request time (<100ms). Output results to console.")

Task("python-backend-engineer", "TASK-3.8: Security review for file endpoints. Validate: reject paths containing '../' or starting with '/', reject paths with null bytes, ensure file content is served with Content-Type: text/plain, verify CSP headers prevent XSS. Add security tests.")
```

### Batch 4 (Parallel - Documentation)

```
Task("documentation-writer", "TASK-3.9: Add 'Previewing Catalog Artifacts' section to docs/user-guide.md. Explain: how to open catalog entry modal, Overview vs Contents tabs, navigating file tree, viewing file contents, rate limit messages. Include placeholder for screenshots.")

Task("documentation-complex", "TASK-3.10: Create ADR for caching strategy at docs/architecture/decisions/ADR-XXX-catalog-file-caching.md. Document: decision to use two-layer cache (TanStack Query + backend LRU), TTL values (5min/30min frontend, 1hr/2hr backend), cache key format, LRU eviction at 1000 entries, invalidation on source rescan.")
```

## Key Files

| File | Purpose |
|------|---------|
| `skillmeat/web/components/CatalogEntryModal.tsx` | Auto-select, truncation UI |
| `skillmeat/core/marketplace/github_scanner.py` | File truncation logic |
| `tests/integration/test_github_client.py` | GitHub error integration tests |
| `tests/e2e/catalog-preview.spec.ts` | E2E workflow test |
| `docs/user-guide.md` | User documentation |
| `docs/architecture/decisions/ADR-XXX-catalog-file-caching.md` | Caching architecture decision |

## Acceptance Criteria

- [ ] First .md file auto-selected in Contents tab (or first alphabetically)
- [ ] Files >1MB truncated with "View full file on GitHub" link
- [ ] Integration tests cover GitHub 403, 404, timeout scenarios
- [ ] E2E test validates full user workflow (browse → preview → import)
- [ ] WCAG 2.1 AA compliance for keyboard nav and screen readers
- [ ] Performance test confirms cache hit rate >70%
- [ ] Security audit passes (no XSS, path traversal vulnerabilities)
- [ ] User documentation and ADR published
