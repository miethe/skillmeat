# Marketplace Sources E2E Testing Guide

**File**: `tests/e2e/marketplace-sources.spec.ts`

Comprehensive end-to-end test suite for GitHub source ingestion functionality in the SkillMeat marketplace.

## Overview

This test suite validates the complete user journey for adding, managing, and importing artifacts from GitHub repository sources. It covers:

- Add source workflow (happy path and validation)
- Source list page functionality
- Source detail page with filtering
- Artifact import (single and bulk)
- Rescan operations
- Error handling scenarios
- Accessibility requirements (WCAG)
- Responsive design (mobile, tablet, desktop)

**Total Test Cases**: 50+
**Test Coverage**: ~1000 lines of comprehensive E2E tests

---

## Running the Tests

### Quick Start

```bash
# Run all marketplace sources tests
pnpm test:e2e tests/e2e/marketplace-sources.spec.ts

# Run in headed mode (see browser)
pnpm test:e2e:headed tests/e2e/marketplace-sources.spec.ts

# Run in UI mode (interactive)
pnpm test:e2e:ui tests/e2e/marketplace-sources.spec.ts

# Run in debug mode
pnpm test:e2e:debug tests/e2e/marketplace-sources.spec.ts
```

### Run Specific Test Suites

```bash
# Run only Add Source tests
pnpm test:e2e tests/e2e/marketplace-sources.spec.ts -g "Add Source Workflow"

# Run only Source Detail tests
pnpm test:e2e tests/e2e/marketplace-sources.spec.ts -g "Source Detail Page"

# Run only Accessibility tests
pnpm test:e2e tests/e2e/marketplace-sources.spec.ts -g "Accessibility"

# Run only Error Handling tests
pnpm test:e2e tests/e2e/marketplace-sources.spec.ts -g "Error Handling"
```

### Cross-Browser Testing

```bash
# Run on Chromium only
pnpm test:e2e:chromium tests/e2e/marketplace-sources.spec.ts

# Run on Firefox only
pnpm test:e2e:firefox tests/e2e/marketplace-sources.spec.ts

# Run on WebKit (Safari) only
pnpm test:e2e:webkit tests/e2e/marketplace-sources.spec.ts

# Run on all browsers
pnpm test:e2e tests/e2e/marketplace-sources.spec.ts
```

### Mobile & Responsive Testing

```bash
# The test suite automatically includes responsive tests
# These run at different viewport sizes:
# - Mobile: 390x844 (iPhone 13)
# - Tablet: 768x1024 (iPad)
# - Desktop: 1920x1080

# To see mobile tests specifically:
pnpm test:e2e tests/e2e/marketplace-sources.spec.ts -g "Responsive Design"
```

---

## Test Structure

### Test Suites

1. **Sources List Page** (8 tests)
   - Page layout and controls
   - Source card display
   - Search filtering
   - Empty states
   - Refresh functionality

2. **Add Source Workflow** (6 tests)
   - Modal open/close
   - URL validation
   - Form submission
   - Trust level selection
   - Optional fields (root hint)
   - Cancel flow

3. **Source Detail Page** (10 tests)
   - Header and navigation
   - Status count badges
   - Type filtering
   - Status filtering
   - Search functionality
   - Artifact card display
   - Confidence scores
   - External links

4. **Rescan Source** (2 tests)
   - Initiate rescan
   - Catalog updates after rescan

5. **Import Artifacts** (7 tests)
   - Single artifact import
   - Multiple selection
   - Bulk import
   - Select/deselect all
   - Disabled states (imported/removed)

6. **Error Handling** (6 tests)
   - Invalid URL validation
   - API errors
   - Private repo access
   - Source not found
   - Network timeouts

7. **Accessibility** (7 tests)
   - Keyboard navigation (list page)
   - Keyboard navigation (modal)
   - Escape key handling
   - ARIA labels
   - Focus management

8. **Responsive Design** (5 tests)
   - Mobile viewport
   - Tablet viewport
   - Desktop viewport
   - Modal responsiveness
   - Filter bar wrapping

9. **Pagination** (3 tests)
   - Load more sources
   - Load more catalog entries
   - Hide button when complete

---

## Mock Data

The test suite uses comprehensive mock data defined at the top of the file:

```typescript
const mockSource = {
  id: 'source-123',
  owner: 'anthropics',
  repo_name: 'anthropic-cookbook',
  ref: 'main',
  // ...
};

const mockCatalogEntry = {
  id: 'entry-1',
  name: 'canvas-design',
  artifact_type: 'skill',
  status: 'new',
  confidence_score: 95,
  // ...
};
```

Mock data covers:
- Sources list with pagination
- Catalog entries (new, updated, imported, removed)
- Scan preview results
- Error responses (400, 403, 404, 500)

---

## Helper Functions

The test suite leverages helper functions from `tests/helpers/test-utils.ts`:

### Navigation Helpers
- `waitForPageLoad(page)` - Wait for full page load
- `navigateToPage(page, path)` - Navigate and wait

### API Mocking
- `mockApiRoute(page, route, response, status)` - Mock API endpoints
- `setupMockApiRoutes(page)` - Setup all marketplace API mocks

### Interaction Helpers
- `typeInInput(page, selector, text)` - Type and verify
- `pressKey(page, key)` - Keyboard interactions
- `expectFocused(page, selector)` - Focus assertions
- `expectModalOpen/Closed(page, selector)` - Modal state checks

### Assertion Helpers
- `expectTextVisible(page, selector, text)` - Visibility + text
- `expectButtonState(page, selector, options)` - Button state checks
- `expectErrorMessage(page, message)` - Error display checks

---

## Critical User Journeys

### Journey 1: Add Source (Happy Path)

```typescript
test('creates source with valid inputs', async ({ page }) => {
  // 1. Navigate to sources page
  await navigateToSourcesPage(page);

  // 2. Click Add Source button
  await page.getByRole('button', { name: /Add Source/i }).click();

  // 3. Fill in form
  await page.locator('#repo-url').fill('https://github.com/owner/repo');
  await page.locator('#ref').fill('main');

  // 4. Submit
  await page.getByRole('button', { name: 'Add Source' }).click();

  // 5. Verify success
  await expect(page.getByText('owner/repo')).toBeVisible();
});
```

### Journey 2: Import Artifacts (Bulk)

```typescript
test('imports selected artifacts in bulk', async ({ page }) => {
  // 1. Navigate to source detail
  await navigateToSourceDetailPage(page);

  // 2. Select multiple artifacts
  const checkboxes = page.getByRole('checkbox');
  await checkboxes.nth(0).check();
  await checkboxes.nth(1).check();

  // 3. Click bulk import
  await page.getByRole('button', { name: /Import 2 selected/i }).click();

  // 4. Verify loading state
  await expect(page.getByText('Importing...')).toBeVisible();
});
```

### Journey 3: Filter and Rescan

```typescript
test('filters catalog by type and rescans', async ({ page }) => {
  // 1. Navigate to source detail
  await navigateToSourceDetailPage(page);

  // 2. Apply type filter
  await page.getByRole('combobox').click();
  await page.getByRole('option', { name: 'Skills' }).click();

  // 3. Initiate rescan
  await page.getByRole('button', { name: /Rescan/i }).click();

  // 4. Verify loading state
  await expect(page.getByText('Scanning...')).toBeVisible();
});
```

---

## Accessibility Checks

### Keyboard Navigation

The test suite verifies full keyboard accessibility:

```typescript
// Tab navigation through interactive elements
await pressKey(page, 'Tab'); // Move to next element
await expectFocused(page, 'button'); // Verify focus

// Escape key to close modals
await pressKey(page, 'Escape');
await expectModalClosed(page, '[role="dialog"]');
```

### ARIA Labels

All interactive elements are verified to have proper ARIA labels:

```typescript
// Buttons with accessible names
await expect(page.getByRole('button', { name: /Add Source/i })).toBeVisible();

// Checkboxes with proper roles
const checkboxes = page.getByRole('checkbox');
await expect(checkboxes.first()).toBeVisible();
```

### Focus Management

Focus is properly managed in modals:

```typescript
// Focus returns to trigger after modal close
const addButton = page.getByRole('button', { name: /Add Source/i });
await addButton.click();
await page.getByRole('button', { name: 'Cancel' }).click();
await expectFocused(page, 'button:has-text("Add Source")');
```

---

## Responsive Design Testing

### Viewport Sizes

The test suite validates layouts at three breakpoints:

1. **Mobile**: 390x844 (iPhone 13)
   - Single column grid
   - Stacked header
   - Full-width cards

2. **Tablet**: 768x1024 (iPad)
   - Two-column grid
   - Wrapped filters

3. **Desktop**: 1920x1080
   - Three-column grid
   - Horizontal header
   - Inline filters

### Example Test

```typescript
test('displays properly on mobile viewport', async ({ page }) => {
  // Set mobile viewport
  await page.setViewportSize({ width: 390, height: 844 });

  await navigateToSourcesPage(page);

  // Verify mobile layout
  await expect(page.getByText('anthropics/cookbook')).toBeVisible();
});
```

---

## Error Scenarios

### Validation Errors

```typescript
test('shows error for invalid GitHub URL', async ({ page }) => {
  await page.locator('#repo-url').fill('invalid-url');

  await expect(
    page.getByText('Enter a valid GitHub URL')
  ).toBeVisible();
});
```

### API Errors

```typescript
test('shows error when API request fails', async ({ page }) => {
  // Mock 500 error
  await mockApiRoute(
    page,
    '/api/v1/marketplace/sources*',
    { error: 'Internal server error' },
    500
  );

  await navigateToSourcesPage(page);

  // Verify error display
  await expect(
    page.getByText('Failed to load sources')
  ).toBeVisible();

  // Verify retry button
  await expect(page.getByRole('button', { name: 'Retry' })).toBeVisible();
});
```

### Network Timeouts

```typescript
test('handles network timeout gracefully', async ({ page }) => {
  // Mock slow response
  await page.route('**/api/v1/marketplace/sources*', async (route) => {
    await new Promise(resolve => setTimeout(resolve, 10000));
    await route.abort();
  });

  await page.goto('/marketplace/sources');

  // Verify loading state persists
  await expect(page.locator('[aria-busy="true"]')).toBeVisible();
});
```

---

## Test Maintenance

### Adding New Tests

When adding new features to marketplace sources:

1. **Add mock data** at the top of the file
2. **Create new test suite** using `test.describe()`
3. **Use helper functions** for common operations
4. **Follow patterns** from existing tests
5. **Verify accessibility** (keyboard nav, ARIA)
6. **Test responsive** at multiple breakpoints

### Updating Mock Data

When API schemas change:

1. Update mock data types in the test file
2. Update `mockApiRoute()` calls with new fields
3. Verify all assertions still work
4. Update documentation if needed

### Debugging Failed Tests

```bash
# Run in debug mode
pnpm test:e2e:debug tests/e2e/marketplace-sources.spec.ts

# View test report
pnpm test:report

# Take screenshots on failure (automatic)
# Screenshots saved to: test-results/screenshots/

# View video recordings (automatic)
# Videos saved to: test-results/videos/
```

---

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run Marketplace Sources E2E Tests
  run: pnpm test:e2e tests/e2e/marketplace-sources.spec.ts

- name: Upload Test Results
  if: failure()
  uses: actions/upload-artifact@v3
  with:
    name: test-results
    path: test-results/
```

### Pre-commit Hook

```bash
# Add to .husky/pre-commit
pnpm test:e2e tests/e2e/marketplace-sources.spec.ts --project=chromium
```

---

## Performance Considerations

### Test Execution Time

- **Average duration**: ~3-5 minutes (all 50+ tests)
- **Single suite**: ~30-60 seconds
- **Parallel execution**: Tests run in parallel across browsers

### Optimization Tips

1. **Use test.describe.serial()** for dependent tests
2. **Mock API responses** to avoid real network calls
3. **Reuse page instances** in beforeEach hooks
4. **Limit viewport changes** to responsive tests only

---

## Success Criteria

All tests must pass for:

- ✅ All critical user journeys
- ✅ Error handling scenarios
- ✅ Keyboard navigation
- ✅ ARIA label compliance
- ✅ Mobile responsive design (390px)
- ✅ Tablet responsive design (768px)
- ✅ Desktop responsive design (1920px)
- ✅ Cross-browser compatibility (Chrome, Firefox, Safari)

---

## Known Issues & Limitations

### Current Limitations

1. **No real API integration**: Tests use mocked API responses
2. **No authentication testing**: Assumes authenticated user
3. **Limited conflict resolution**: Import conflict UI not yet implemented
4. **No scan preview wizard**: Simplified to single-step modal

### Future Enhancements

- [ ] Add tests for scan preview wizard (4-step process)
- [ ] Add tests for catalog override functionality
- [ ] Add tests for conflict resolution dialog
- [ ] Add visual regression testing
- [ ] Add performance benchmarking
- [ ] Add real GitHub API integration tests

---

## Related Files

- **Component**: `app/marketplace/sources/page.tsx`
- **Component**: `app/marketplace/sources/[id]/page.tsx`
- **Component**: `components/marketplace/add-source-modal.tsx`
- **Component**: `components/marketplace/source-card.tsx`
- **Hooks**: `hooks/useMarketplaceSources.ts`
- **Types**: `types/marketplace.ts`
- **Test Utils**: `tests/helpers/test-utils.ts`
- **Test Fixtures**: `tests/helpers/fixtures.ts`

---

## Support

For questions or issues with these tests:

1. Check Playwright documentation: https://playwright.dev/
2. Review existing test patterns in `tests/e2e/`
3. Check test helper functions in `tests/helpers/`
4. Refer to main web CLAUDE.md: `skillmeat/web/CLAUDE.md`

---

**Last Updated**: 2024-12-08
**Test Suite Version**: 1.0.0
**Playwright Version**: ^1.48.2
