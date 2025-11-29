# Testing Guide for SkillMeat Web

## Overview

This document provides complete testing setup and usage instructions for the SkillMeat web interface E2E and accessibility tests.

## Installation

### 1. Install Dependencies

```bash
cd skillmeat/web
pnpm install
```

This will install:

- `@playwright/test` - Playwright test framework
- `@axe-core/playwright` - Accessibility testing with axe-core

### 2. Install Playwright Browsers

```bash
pnpm run playwright:install
```

This installs Chromium, Firefox, and WebKit browsers with their dependencies.

## Running Tests

### Quick Start

```bash
# Run all tests
pnpm run test:e2e

# Run tests with UI (recommended for development)
pnpm run test:e2e:ui

# Run accessibility tests only
pnpm run test:a11y
```

### All Test Commands

```bash
# Run all E2E tests
pnpm run test:e2e

# Run tests in interactive UI mode
pnpm run test:e2e:ui

# Run tests in headed mode (visible browser)
pnpm run test:e2e:headed

# Run tests in debug mode
pnpm run test:e2e:debug

# Run tests in specific browser
pnpm run test:e2e:chromium
pnpm run test:e2e:firefox
pnpm run test:e2e:webkit

# Run only accessibility tests
pnpm run test:a11y

# View test report
pnpm run test:report
```

## Test Structure

```
tests/
├── helpers/
│   ├── fixtures.ts           # Mock data and API builders
│   └── test-utils.ts          # Common test utilities
├── collections.spec.ts        # Collections dashboard tests
├── deploy-sync.spec.ts        # Deploy/sync workflow tests
├── analytics.spec.ts          # Analytics widgets tests
├── accessibility.spec.ts      # WCAG 2.1 AA compliance tests
├── keyboard-navigation.spec.ts # Keyboard accessibility tests
└── README.md                  # Detailed test documentation
```

## Test Coverage

### 1. Collections Dashboard (`collections.spec.ts`)

- View switching (grid/list)
- Filtering by type, status, scope
- Search functionality
- Sorting
- Artifact cards/list display
- Detail drawer
- Loading/error states
- Responsive design

### 2. Deploy & Sync (`deploy-sync.spec.ts`)

- Deploy workflow
- Sync workflow
- Project selection
- Success/error handling
- Modal interactions
- Batch operations

### 3. Analytics (`analytics.spec.ts`)

- Stats cards
- Top artifacts widget
- Usage trends widget
- Live updates (SSE)
- Chart interactions
- Loading/error states

### 4. Accessibility (`accessibility.spec.ts`)

- WCAG 2.1 AA compliance
- Zero critical violations
- Zero serious violations
- Color contrast (4.5:1 for text)
- Semantic HTML
- ARIA labels and roles
- Focus management
- Screen reader support

### 5. Keyboard Navigation (`keyboard-navigation.spec.ts`)

- Tab order
- All elements reachable
- Escape closes modals
- Enter activates buttons
- Space activates buttons/checkboxes
- Arrow key navigation
- Focus visibility
- Skip links

## Accessibility Standards

All tests must pass:

- **WCAG 2.1 Level AA** compliance
- **No critical violations** from axe-core
- **No serious violations** from axe-core
- **4.5:1 color contrast** for normal text
- **3:1 color contrast** for large text and interactive elements
- **Keyboard accessible** - all functionality via keyboard
- **Screen reader friendly** - proper ARIA, semantic HTML
- **Focus visible** - clear indicators on all interactive elements

## CI Integration

Tests run automatically on:

- Push to `main` or `develop`
- Pull requests to `main` or `develop`

Tests run in three browsers:

- Chromium
- Firefox
- WebKit (Safari)

See `.github/workflows/web-e2e-tests.yml` for configuration.

## Debugging Tests

### UI Mode (Recommended)

```bash
pnpm run test:e2e:ui
```

Features:

- Time travel through test execution
- Watch mode
- Pick locators
- View traces
- Interactive debugging

### Debug Mode

```bash
pnpm run test:e2e:debug
```

Opens Playwright Inspector for step-by-step debugging.

### Headed Mode

```bash
pnpm run test:e2e:headed
```

Runs tests with visible browser window.

### View Reports

```bash
pnpm run test:report
```

Opens interactive HTML report with:

- Test results
- Screenshots
- Videos
- Traces
- Error messages

## Writing Tests

### Example Test

```typescript
import { test, expect } from '@playwright/test';
import { mockApiRoute, navigateToPage } from './helpers/test-utils';
import { buildApiResponse } from './helpers/fixtures';

test.describe('My Feature', () => {
  test.beforeEach(async ({ page }) => {
    await mockApiRoute(page, '/api/artifacts*', buildApiResponse.artifacts());
    await navigateToPage(page, '/collection');
  });

  test('should work correctly', async ({ page }) => {
    const button = page.locator('button');
    await button.click();
    await expect(button).toBeVisible();
  });
});
```

### Best Practices

1. **Use data-testid** for stable selectors
2. **Mock API responses** for consistent tests
3. **Use semantic selectors** when possible
4. **Wait for elements** before interacting
5. **Test success and error states**
6. **Test responsive design**
7. **Test keyboard navigation**
8. **Run accessibility tests**

## Common Issues

### Port Already in Use

Change port in `playwright.config.ts`:

```typescript
webServer: {
  url: 'http://localhost:3001',
}
```

### Tests Timing Out

Increase timeout in `playwright.config.ts`:

```typescript
timeout: 60 * 1000,
```

### Browsers Not Found

```bash
pnpm run playwright:install
```

### Flaky Tests

Add explicit waits:

```typescript
await page.waitForTimeout(500);
```

Or use `test.retry()`.

## Test Data

Mock data is defined in `tests/helpers/fixtures.ts`:

- `mockArtifacts` - Sample artifacts
- `mockAnalytics` - Sample analytics data
- `mockProjects` - Sample projects
- `buildApiResponse` - API response builders
- `buildErrorResponse` - Error response builders

## Test Utilities

Common utilities in `tests/helpers/test-utils.ts`:

- `mockApiRoute()` - Mock API endpoints
- `navigateToPage()` - Navigate with wait
- `expectTextVisible()` - Assert text visible
- `pressKey()` - Press keyboard key
- `expectFocused()` - Assert element focused
- `expectModalOpen()` - Assert modal open
- `waitForElement()` - Wait for element

See `tests/README.md` for complete API documentation.

## Continuous Integration

GitHub Actions workflow at `.github/workflows/web-e2e-tests.yml`:

- Runs on push/PR to main/develop
- Tests in Chromium, Firefox, WebKit
- Separate job for accessibility tests
- Uploads test results and reports
- Fails on critical accessibility violations

## Resources

- [Playwright Documentation](https://playwright.dev)
- [axe-core Documentation](https://github.com/dequelabs/axe-core)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [Test README](./tests/README.md) - Detailed test documentation

## Support

For test-related issues:

1. Check this guide and test README
2. Run tests in debug mode
3. Check test reports
4. Review Playwright documentation
5. Open GitHub issue with test details
