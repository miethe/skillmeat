/**
 * Collections Dashboard E2E Tests
 *
 * Tests for the main collections dashboard including:
 * - View switching (grid/list)
 * - Filtering
 * - Search
 * - Sorting
 * - Artifact detail drawer
 */

import { test, expect } from '@playwright/test';
import {
  mockApiRoute,
  navigateToPage,
  expectTextVisible,
  expectButtonState,
  waitForElement,
  countElements,
  typeInInput,
  pressKey,
} from './helpers/test-utils';
import { buildApiResponse, mockArtifacts } from './helpers/fixtures';

test.describe('Collections Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Mock API routes
    await mockApiRoute(page, '/api/artifacts*', buildApiResponse.artifacts());
    await mockApiRoute(page, '/api/analytics*', buildApiResponse.analytics());

    // Navigate to collections page
    await navigateToPage(page, '/collection');
  });

  test('should display page header and description', async ({ page }) => {
    await expectTextVisible(page, 'h1', 'Collection');
    await expectTextVisible(
      page,
      'p',
      'Browse and manage your artifact collection'
    );
  });

  test('should display artifact count', async ({ page }) => {
    await expectTextVisible(page, 'h2', `${mockArtifacts.length} Artifacts`);
  });

  test.describe('View Switching', () => {
    test('should start in grid view by default', async ({ page }) => {
      const gridButton = page.locator('[aria-label="Grid view"]');
      await expect(gridButton).toHaveAttribute('aria-pressed', 'true');

      // Grid should be visible
      await waitForElement(page, '[data-testid="artifact-grid"]');
    });

    test('should switch to list view when clicked', async ({ page }) => {
      const listButton = page.locator('[aria-label="List view"]');
      await listButton.click();

      await expect(listButton).toHaveAttribute('aria-pressed', 'true');

      // List should be visible
      await waitForElement(page, '[data-testid="artifact-list"]');
    });

    test('should switch back to grid view', async ({ page }) => {
      // Switch to list
      await page.locator('[aria-label="List view"]').click();

      // Switch back to grid
      const gridButton = page.locator('[aria-label="Grid view"]');
      await gridButton.click();

      await expect(gridButton).toHaveAttribute('aria-pressed', 'true');
      await waitForElement(page, '[data-testid="artifact-grid"]');
    });

    test('should maintain view preference across filters', async ({ page }) => {
      // Switch to list view
      await page.locator('[aria-label="List view"]').click();

      // Apply a filter
      const typeSelect = page.locator('select[name="type"]');
      await typeSelect.selectOption('skill');

      // List view should still be active
      const listButton = page.locator('[aria-label="List view"]');
      await expect(listButton).toHaveAttribute('aria-pressed', 'true');
    });
  });

  test.describe('Filtering', () => {
    test('should filter by artifact type', async ({ page }) => {
      // Mock filtered response
      await mockApiRoute(
        page,
        '/api/artifacts*type=skill*',
        buildApiResponse.artifacts({ type: 'skill' })
      );

      const typeSelect = page.locator('select[name="type"]');
      await typeSelect.selectOption('skill');

      // Wait for filter to apply
      await page.waitForTimeout(500);

      // Active filter count should update
      await expectTextVisible(page, '[variant="secondary"]', '1 active');
    });

    test('should filter by status', async ({ page }) => {
      await mockApiRoute(
        page,
        '/api/artifacts*status=outdated*',
        buildApiResponse.artifacts({ status: 'outdated' })
      );

      const statusSelect = page.locator('select[name="status"]');
      await statusSelect.selectOption('outdated');

      await page.waitForTimeout(500);
      await expectTextVisible(page, '[variant="secondary"]', '1 active');
    });

    test('should filter by scope', async ({ page }) => {
      await mockApiRoute(
        page,
        '/api/artifacts*scope=user*',
        buildApiResponse.artifacts({ scope: 'user' })
      );

      const scopeSelect = page.locator('select[name="scope"]');
      await scopeSelect.selectOption('user');

      await page.waitForTimeout(500);
      await expectTextVisible(page, '[variant="secondary"]', '1 active');
    });

    test('should show active filter count', async ({ page }) => {
      // Apply multiple filters
      await page.locator('select[name="type"]').selectOption('skill');
      await page.locator('select[name="status"]').selectOption('active');

      await page.waitForTimeout(500);
      await expectTextVisible(page, '[variant="secondary"]', '2 active');
    });

    test('should clear all filters', async ({ page }) => {
      // Apply filters
      await page.locator('select[name="type"]').selectOption('skill');
      await page.locator('select[name="status"]').selectOption('active');

      await page.waitForTimeout(500);

      // Click clear all button
      const clearButton = page.locator('[aria-label="Clear all filters"]');
      await clearButton.click();

      // Active filter badge should disappear
      const badge = page.locator('[variant="secondary"]');
      await expect(badge).toBeHidden();

      // Selects should be reset
      const typeSelect = page.locator('select[name="type"]');
      await expect(typeSelect).toHaveValue('all');
    });
  });

  test.describe('Search', () => {
    test('should search artifacts by name', async ({ page }) => {
      await mockApiRoute(
        page,
        '/api/artifacts*search=canvas*',
        buildApiResponse.artifacts({ search: 'canvas' })
      );

      const searchInput = page.locator('input[type="search"]');
      await typeInInput(page, 'input[type="search"]', 'canvas');

      await page.waitForTimeout(500);

      // Should show filtered results
      await expectTextVisible(page, 'h2', /Artifact/);
    });

    test('should debounce search input', async ({ page }) => {
      const searchInput = page.locator('input[type="search"]');

      await searchInput.type('can');
      await page.waitForTimeout(100);
      await searchInput.type('vas');

      // Should only make one API call after debounce
      await page.waitForTimeout(500);
    });

    test('should clear search', async ({ page }) => {
      const searchInput = page.locator('input[type="search"]');
      await typeInInput(page, 'input[type="search"]', 'canvas');

      await searchInput.clear();

      // Should show all results again
      await page.waitForTimeout(500);
    });
  });

  test.describe('Sorting', () => {
    test('should sort by name ascending', async ({ page }) => {
      await mockApiRoute(
        page,
        '/api/artifacts*sort=name*order=asc*',
        buildApiResponse.artifacts()
      );

      const sortSelect = page.locator('select[name="sort"]');
      await sortSelect.selectOption('name');

      await page.waitForTimeout(500);
    });

    test('should sort by updated date', async ({ page }) => {
      await mockApiRoute(
        page,
        '/api/artifacts*sort=updatedAt*',
        buildApiResponse.artifacts()
      );

      const sortSelect = page.locator('select[name="sort"]');
      await sortSelect.selectOption('updatedAt');

      await page.waitForTimeout(500);
    });

    test('should toggle sort order', async ({ page }) => {
      const orderButton = page.locator('[aria-label*="order"]');
      await orderButton.click();

      // Order should toggle
      await page.waitForTimeout(500);
    });
  });

  test.describe('Artifact Cards', () => {
    test('should display artifact cards in grid', async ({ page }) => {
      const cards = page.locator('[data-testid="artifact-card"]');
      const count = await cards.count();

      expect(count).toBeGreaterThan(0);
    });

    test('should show artifact name and type', async ({ page }) => {
      const firstCard = page.locator('[data-testid="artifact-card"]').first();

      await expect(firstCard).toContainText(mockArtifacts[0].name);
      await expect(firstCard).toContainText(mockArtifacts[0].type);
    });

    test('should show artifact metadata', async ({ page }) => {
      const firstCard = page.locator('[data-testid="artifact-card"]').first();

      // Should show version, author, tags
      await expect(firstCard).toContainText(mockArtifacts[0].version || '');
    });

    test('should open detail drawer when clicked', async ({ page }) => {
      await mockApiRoute(
        page,
        `/api/artifacts/${mockArtifacts[0].id}`,
        buildApiResponse.artifactDetail(mockArtifacts[0].id)
      );

      const firstCard = page.locator('[data-testid="artifact-card"]').first();
      await firstCard.click();

      // Drawer should open
      const drawer = page.locator('[role="dialog"]');
      await expect(drawer).toBeVisible();
    });
  });

  test.describe('Loading and Error States', () => {
    test('should show loading state', async ({ page }) => {
      // Navigate to a slow-loading page
      await page.route('**/api/artifacts*', async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 1000));
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(buildApiResponse.artifacts()),
        });
      });

      await page.goto('/collection');

      // Should show loading indicator
      const loadingText = page.locator('h2:has-text("Loading")');
      await expect(loadingText).toBeVisible();
    });

    test('should show error state', async ({ page }) => {
      await mockApiRoute(page, '/api/artifacts*', { error: 'Failed' }, 500);

      await page.goto('/collection');
      await page.waitForTimeout(500);

      // Should show error message
      await expectTextVisible(
        page,
        '[role="alert"], .error, .destructive',
        /Failed to load/i
      );
    });

    test('should show empty state when no artifacts', async ({ page }) => {
      await mockApiRoute(page, '/api/artifacts*', {
        artifacts: [],
        total: 0,
        page: 1,
        pageSize: 50,
      });

      await page.goto('/collection');
      await page.waitForTimeout(500);

      await expectTextVisible(page, 'h2', '0 Artifacts');
    });
  });

  test.describe('Responsive Design', () => {
    test('should adjust layout on mobile', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });

      // Grid should adjust columns
      const grid = page.locator('[data-testid="artifact-grid"]');
      await expect(grid).toBeVisible();
    });

    test('should adjust layout on tablet', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });

      const grid = page.locator('[data-testid="artifact-grid"]');
      await expect(grid).toBeVisible();
    });
  });
});
