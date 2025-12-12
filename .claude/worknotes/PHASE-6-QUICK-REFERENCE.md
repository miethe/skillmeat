# Phase 6 Test Coverage - Quick Reference Card

**Exploration Date**: 2025-12-08
**Status**: Complete
**Coverage Target**: 70% (from current 40%)

---

## Test Gap Summary (119 Tests Needed)

### Backend Python Tests (83 tests needed)

| Module | Location | Tests | Priority | Hours |
|--------|----------|-------|----------|-------|
| **GitHub Scanner** | `tests/core/marketplace/test_github_scanner.py` | 20 | HIGH | 5 |
| **Link Harvester** | `tests/core/marketplace/test_link_harvester.py` | 15 | HIGH | 4 |
| **Import Coordinator** | `tests/core/marketplace/test_import_coordinator.py` | 15 | HIGH | 4 |
| **Marketplace Sources Router** | `tests/api/test_marketplace_sources.py` | 18 | HIGH | 5 |
| **Marketplace Router** | `tests/api/test_marketplace_router.py` | 15 (enhance) | MEDIUM | 3 |

**Backend Subtotal**: 83 tests, 21 hours

### Frontend React Tests (20 tests needed)

| Component | Location | Tests | Priority | Hours |
|-----------|----------|-------|----------|-------|
| **Add Source Modal** | `__tests__/marketplace/AddSourceModal.test.tsx` | 10 | MEDIUM | 2 |
| **Source Card** | `__tests__/marketplace/SourceCard.test.tsx` | 10 | MEDIUM | 2 |

**Frontend Subtotal**: 20 tests, 4 hours

### E2E Tests (16 tests needed)

| Flow | Location | Tests | Priority | Hours |
|------|----------|-------|----------|-------|
| **Source Management** | `tests/e2e/marketplace-sources.spec.ts` | 8 | HIGH | 2 |
| **Import Workflow** | `tests/e2e/marketplace-sources.spec.ts` | 8 | HIGH | 2 |

**E2E Subtotal**: 16 tests, 4 hours

---

## Critical Implementation Files Status

### Core Marketplace Services

```
skillmeat/core/marketplace/
├── heuristic_detector.py        ✓ FULLY TESTED (206 test lines)
├── diff_engine.py               ✓ FULLY TESTED (495 test lines)
├── github_scanner.py            ✗ NOT TESTED (437 implementation lines)
├── link_harvester.py            ✗ NOT TESTED (309 implementation lines)
├── import_coordinator.py         ✗ NOT TESTED (394 implementation lines)
└── observability.py             ? UNKNOWN
```

### API Routers

```
skillmeat/api/routers/
├── marketplace.py               ✓ PARTIAL TEST (489 test lines, 75% coverage)
└── marketplace_sources.py        ✗ NOT TESTED (API layer)
```

### Web Components

```
skillmeat/web/components/marketplace/
├── add-source-modal.tsx         ✗ NOT TESTED
├── source-card.tsx              ✗ NOT TESTED
├── MarketplaceFilters.tsx       △ PARTIAL TEST
├── MarketplaceInstallDialog.tsx △ PARTIAL TEST
└── MarketplaceListingCard.tsx   △ PARTIAL TEST
```

---

## Test Implementation Checklist

### Week 1: Backend Unit Tests

- [ ] **Day 1**: GitHub Scanner tests (20 tests)
  - [ ] Test scan_repository() success flow
  - [ ] Test tree fetching with pagination
  - [ ] Test rate limit handling (429, 403)
  - [ ] Test retry logic with backoff
  - [ ] Test token authentication
  - [ ] Test file path extraction and filtering

- [ ] **Day 2**: Link Harvester tests (15 tests)
  - [ ] Test link extraction from README
  - [ ] Test URL normalization
  - [ ] Test confidence scoring
  - [ ] Test ignore patterns (issues, pulls, wiki)
  - [ ] Test artifact keywords
  - [ ] Test cycle protection

- [ ] **Day 3**: Import Coordinator tests (15 tests)
  - [ ] Test import entry processing
  - [ ] Test conflict detection
  - [ ] Test skip strategy
  - [ ] Test overwrite strategy
  - [ ] Test rename strategy
  - [ ] Test path computation

- [ ] **Day 4**: Marketplace Sources Router tests (18 tests)
  - [ ] Test create source endpoint
  - [ ] Test list sources (pagination)
  - [ ] Test get source by ID
  - [ ] Test update source
  - [ ] Test delete source
  - [ ] Test rescan trigger
  - [ ] Test artifact list with filters
  - [ ] Test import artifacts endpoint

- [ ] **Day 5**: Test review & refinement
  - [ ] Review all test coverage
  - [ ] Verify mocking strategies
  - [ ] Document test patterns
  - [ ] Fix any gaps

### Week 2: Frontend & E2E Tests

- [ ] **Day 1**: Component tests (20 tests)
  - [ ] AddSourceModal.test.tsx (10 tests)
  - [ ] SourceCard.test.tsx (10 tests)

- [ ] **Day 2**: E2E tests (16 tests)
  - [ ] Source management flow
  - [ ] Import workflow
  - [ ] Conflict resolution
  - [ ] Error scenarios

- [ ] **Day 3**: Integration tests
  - [ ] Complete GitHub ingestion flow
  - [ ] Incremental scan with updates

- [ ] **Day 4-5**: Coverage review & documentation

---

## Key Test Patterns

### Backend Mock Pattern

```python
@patch('skillmeat.core.marketplace.github_scanner.requests.Session')
def test_github_scanner(mock_session):
    # Setup mock
    mock_session.return_value.get.return_value = Mock(
        json=lambda: {"tree": [...]},
        status_code=200,
    )
    # Execute & Assert
```

### Frontend Test Pattern

```typescript
describe('AddSourceModal', () => {
  it('submits form with valid data', async () => {
    render(<AddSourceModal open={true} onOpenChange={jest.fn()} />);

    fireEvent.change(screen.getByLabelText('Repository URL'), {
      target: { value: 'https://github.com/user/repo' }
    });

    fireEvent.click(screen.getByRole('button', { name: 'Add Source' }));

    await waitFor(() => {
      expect(mockCreateSource).toHaveBeenCalled();
    });
  });
});
```

### E2E Test Pattern

```typescript
test('complete source lifecycle', async ({ page }) => {
  await page.goto('/marketplace/sources');
  await page.click('button:has-text("Add Source")');
  await page.fill('input[placeholder="https://github.com/..."]',
    'https://github.com/test/repo');
  await page.click('button:has-text("Add Source")');

  await expect(page.getByText('test/repo')).toBeVisible();
});
```

---

## Coverage Goals

### Current State
- Backend unit: 60%
- Backend integration: 40%
- Frontend: 40%
- E2E: 10%
- **Overall: 40%**

### Phase 6 Target
- Backend unit: 85%
- Backend integration: 70%
- Frontend: 75%
- E2E: 50%
- **Overall: 70%**

---

## Documentation References

### Complete Analysis
**File**: `.claude/worknotes/phase-6-test-inventory.md` (18 KB)
- Executive summary
- File-by-file analysis
- Functions needing tests
- Priority assessment
- Coverage gaps
- Testing checklist

### Implementation Specifications
**File**: `.claude/specs/phase-6-test-plan.md` (23 KB)
- Test strategies per module
- Test fixtures (50+ examples)
- Test case implementations
- Mocking strategies
- E2E scenarios
- Timeline & quality gates

### Executive Summary
**File**: `.claude/worknotes/phase-6-exploration-summary.md` (9.2 KB)
- Key findings
- Critical gaps
- Recommendations
- Implementation patterns
- Next steps

---

## Test Execution Commands

### Backend Tests

```bash
# Run all marketplace backend tests
pytest tests/core/marketplace/ tests/api/test_marketplace*.py -v

# Run with coverage
pytest tests/core/marketplace/ \
  --cov=skillmeat.core.marketplace \
  --cov=skillmeat.api.routers.marketplace_sources \
  --cov-report=html

# Run specific test module
pytest tests/core/marketplace/test_github_scanner.py -v
```

### Frontend Tests

```bash
# Run all component tests
pnpm test -- skillmeat/web/__tests__/marketplace

# Run with coverage
pnpm test -- --coverage skillmeat/web/__tests__/marketplace

# Run E2E tests
pnpm test:e2e skillmeat/web/tests/e2e/marketplace-sources.spec.ts
```

---

## Effort Breakdown

| Category | Tests | Hours | Notes |
|----------|-------|-------|-------|
| GitHub Scanner | 20 | 5 | Mock API responses |
| Link Harvester | 15 | 4 | Test regex patterns |
| Import Coordinator | 15 | 4 | Test all strategies |
| Marketplace Router (API) | 18 | 5 | Mock database |
| Components | 20 | 4 | React Testing Library |
| E2E Workflows | 16 | 4 | Playwright |
| Review & Docs | - | 4 | Coverage, patterns |
| **Total** | **119** | **30** | **1 week effort** |

---

## Critical Dependencies

### Before Starting Tests:
1. Ensure heuristic_detector and diff_engine tests pass (baseline)
2. Review existing mock patterns in test_marketplace_router.py
3. Set up fixtures directory for GitHub API mocks
4. Configure test database if needed

### Implementation Order:
1. GitHub Scanner (core blocking dependency)
2. Link Harvester (secondary discovery)
3. Import Coordinator (user-facing feature)
4. API Router (integration layer)
5. Components (UI layer)
6. E2E (integration validation)

---

## Success Criteria

- [ ] All 119 tests pass
- [ ] GitHub Scanner: 85%+ coverage
- [ ] Link Harvester: 85%+ coverage
- [ ] Import Coordinator: 85%+ coverage
- [ ] Marketplace Sources Router: 80%+ coverage
- [ ] Web Components: 70%+ coverage
- [ ] Overall: 70%+ coverage
- [ ] No critical issues (P0/P1)
- [ ] All mocks documented
- [ ] Test patterns documented

---

**Next Step**: Review this inventory with team and begin Phase 6 implementation.

