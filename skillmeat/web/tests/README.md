# SkillMeat Web E2E Tests

Comprehensive end-to-end and accessibility tests for the SkillMeat web interface using Playwright and axe-core.

## Quick Start

### Install Dependencies

```bash
# Install all dependencies including Playwright
pnpm install

# Install Playwright browsers
pnpm run playwright:install
```

### Run Tests

```bash
# Run all E2E tests
pnpm run test:e2e

# Run tests in UI mode (interactive)
pnpm run test:e2e:ui

# Run tests in headed mode (visible browser)
pnpm run test:e2e:headed

# Run tests in debug mode
pnpm run test:e2e:debug

# Run accessibility tests only
pnpm run test:a11y

# Run tests in specific browser
pnpm run test:e2e:chromium
pnpm run test:e2e:firefox
pnpm run test:e2e:webkit

# View test report
pnpm run test:report
```

## Test Structure

```
tests/
├── helpers/
│   ├── fixtures.ts           # Mock data and API response builders
│   └── test-utils.ts          # Common test utilities and helpers
├── collections.spec.ts        # Collections dashboard tests
├── deploy-sync.spec.ts        # Deploy and sync workflow tests
├── analytics.spec.ts          # Analytics widgets tests
├── accessibility.spec.ts      # Accessibility compliance tests
├── keyboard-navigation.spec.ts # Keyboard navigation tests
└── README.md                  # This file
```

## Test Categories

### 1. Collections Dashboard Tests (`collections.spec.ts`)

Tests for the main collections page functionality:

- View switching (grid/list)
- Filtering by type, status, scope
- Search functionality
- Sorting
- Artifact cards display
- Artifact detail drawer
- Loading and error states
- Responsive design

**Run:** `pnpm run test:e2e tests/collections.spec.ts`

### 2. Deploy & Sync Tests (`deploy-sync.spec.ts`)

Tests for deployment and synchronization workflows:

- Deploy workflow
- Sync workflow
- Project selection
- Success/error handling
- Modal interactions
- Batch operations

**Run:** `pnpm run test:e2e tests/deploy-sync.spec.ts`

### 3. Analytics Tests (`analytics.spec.ts`)

Tests for analytics dashboard widgets:

- Stats cards (total artifacts, deployments, projects, usage)
- Top artifacts widget
- Usage trends widget
- Live updates via SSE
- Chart interactions
- Loading and error states
- Responsive design

**Run:** `pnpm run test:e2e tests/analytics.spec.ts`

### 4. Accessibility Tests (`accessibility.spec.ts`)

WCAG 2.1 AA compliance tests:

- Zero critical violations
- Zero serious violations
- Semantic HTML structure
- ARIA labels and roles
- Color contrast validation (4.5:1 for text, 3:1 for interactive elements)
- Focus management
- Form accessibility
- Modal/dialog accessibility
- Screen reader support
- Responsive accessibility

**Run:** `pnpm run test:a11y`

### 5. Keyboard Navigation Tests (`keyboard-navigation.spec.ts`)

Comprehensive keyboard accessibility:

- Tab order validation
- All interactive elements reachable
- Escape closes modals
- Enter activates buttons and links
- Space activates buttons and checkboxes
- Arrow key navigation
- Focus visibility
- Skip links
- Form navigation
- Shortcuts (Cmd/Ctrl+K for search)

**Run:** `pnpm run test:e2e tests/keyboard-navigation.spec.ts`

## Test Helpers

### `fixtures.ts`

Provides mock data and API response builders:

- `mockArtifacts`: Sample artifact data
- `mockAnalytics`: Sample analytics data
- `mockProjects`: Sample project data
- `buildApiResponse`: Build API responses for different endpoints
- `buildErrorResponse`: Build error responses

### `test-utils.ts`

Common utilities for tests:

- `mockApiRoute()`: Mock API endpoints
- `navigateToPage()`: Navigate and wait for page load
- `expectTextVisible()`: Assert text is visible
- `expectButtonState()`: Assert button state
- `pressKey()`: Press keyboard key
- `expectFocused()`: Assert element has focus
- `expectModalOpen()`: Assert modal is open
- `expectModalClosed()`: Assert modal is closed
- And many more...

## Writing New Tests

### Example Test

```typescript
import { test, expect } from '@playwright/test';
import { mockApiRoute, navigateToPage } from './helpers/test-utils';
import { buildApiResponse } from './helpers/fixtures';

test.describe('My Feature', () => {
  test.beforeEach(async ({ page }) => {
    // Mock API routes
    await mockApiRoute(page, '/api/artifacts*', buildApiResponse.artifacts());

    // Navigate to page
    await navigateToPage(page, '/collection');
  });

  test('should do something', async ({ page }) => {
    // Your test code
    const button = page.locator('button');
    await button.click();

    await expect(button).toBeVisible();
  });
});
```

### Best Practices

1. **Use data-testid attributes** for stable selectors:
   ```html
   <div data-testid="artifact-card">...</div>
   ```

2. **Mock API responses** for consistent tests:
   ```typescript
   await mockApiRoute(page, '/api/artifacts*', mockData);
   ```

3. **Use semantic selectors** when possible:
   ```typescript
   page.locator('[role="button"]')
   page.locator('[aria-label="Close"]')
   ```

4. **Wait for elements** before interacting:
   ```typescript
   await waitForElement(page, 'selector');
   ```

5. **Test both success and error states**

6. **Test responsive design** with different viewports

7. **Test keyboard navigation** for all interactive elements

8. **Run accessibility tests** with axe-core

## Accessibility Standards

All tests must pass WCAG 2.1 Level AA compliance:

- **No critical violations**: Tests fail if any critical accessibility issues
- **No serious violations**: Tests fail if any serious accessibility issues
- **Color contrast**: 4.5:1 for normal text, 3:1 for large text and interactive elements
- **Keyboard accessible**: All functionality available via keyboard
- **Screen reader friendly**: Proper ARIA labels, semantic HTML, focus management
- **Focus visible**: Clear focus indicators on all interactive elements

## CI Integration

Tests run automatically on:

- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

Tests run in three browsers:
- Chromium
- Firefox
- WebKit (Safari)

Reports are uploaded as artifacts and can be viewed in the GitHub Actions tab.

## Debugging Tests

### UI Mode (Recommended)

```bash
pnpm run test:e2e:ui
```

Provides interactive debugging with:
- Time travel through test execution
- Watch mode
- Pick locators
- View traces

### Debug Mode

```bash
pnpm run test:e2e:debug
```

Opens browser in debug mode with Playwright Inspector.

### Headed Mode

```bash
pnpm run test:e2e:headed
```

Runs tests with visible browser window.

### Screenshots and Videos

Screenshots are automatically captured on test failure.

Videos are captured on first retry.

View in `test-results/` directory.

### Playwright Inspector

```bash
PWDEBUG=1 pnpm run test:e2e
```

Opens Playwright Inspector for step-by-step debugging.

## Test Reports

### View HTML Report

```bash
pnpm run test:report
```

Opens interactive HTML report with:
- Test results
- Screenshots
- Videos
- Traces
- Error messages

### JSON Report

JSON report is generated at `test-results/results.json` for programmatic access.

## Coverage

While Playwright doesn't provide code coverage by default, we test:

- All critical user journeys
- All page types
- All interactive elements
- All form inputs
- All error states
- All loading states
- All responsive breakpoints
- All keyboard interactions
- All accessibility requirements

## Maintenance

### Updating Fixtures

Edit `helpers/fixtures.ts` to update mock data as API changes.

### Updating Helpers

Edit `helpers/test-utils.ts` to add new common test utilities.

### Adding New Tests

1. Create new `.spec.ts` file in `tests/` directory
2. Import helpers and fixtures
3. Write tests following existing patterns
4. Run tests locally
5. Ensure accessibility compliance
6. Submit PR

### Playwright Updates

```bash
# Update Playwright
pnpm update @playwright/test

# Update browsers
pnpm run playwright:install
```

## Troubleshooting

### Tests Timing Out

Increase timeout in `playwright.config.ts`:

```typescript
timeout: 60 * 1000, // 60 seconds
```

### Flaky Tests

Use `test.retry()` or add explicit waits:

```typescript
await page.waitForTimeout(500);
```

### Browser Not Found

Install browsers:

```bash
pnpm run playwright:install
```

### Port Already in Use

Change port in `playwright.config.ts`:

```typescript
webServer: {
  command: 'pnpm run dev',
  url: 'http://localhost:3001',
}
```

## Resources

- [Playwright Documentation](https://playwright.dev)
- [Playwright Testing Best Practices](https://playwright.dev/docs/best-practices)
- [axe-core Documentation](https://github.com/dequelabs/axe-core)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)

## Support

For issues with tests:

1. Check this README
2. Check Playwright documentation
3. Run tests in debug mode
4. Check test reports
5. Ask in team channel
6. Open GitHub issue
