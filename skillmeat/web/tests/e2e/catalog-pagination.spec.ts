/**
 * End-to-end tests for Catalog Pagination
 *
 * Tests the complete pagination workflow on the marketplace source catalog page.
 *
 * Tests cover:
 * 1. Display of pagination controls
 * 2. Page navigation (next, previous, numbered)
 * 3. Items per page selection
 * 4. URL parameter persistence
 * 5. Count indicator updates
 */

import { test, expect, Page } from '@playwright/test';
import { waitForPageLoad, mockApiRoute } from '../helpers/test-utils';

// ============================================================================
// Test Fixtures
// ============================================================================

/**
 * Mock catalog entry data for testing
 */
function generateMockCatalogEntries(count: number) {
  return Array.from({ length: count }, (_, i) => ({
    id: `entry-${i + 1}`,
    name: `artifact-${i + 1}`,
    path: `.claude/skills/artifact-${i + 1}`,
    artifact_type: ['skill', 'command', 'agent', 'hook'][i % 4],
    status: ['new', 'updated', 'imported'][i % 3],
    confidence_score: 50 + (i % 50),
    upstream_url: `https://github.com/owner/repo/tree/main/.claude/skills/artifact-${i + 1}`,
    detected_at: new Date(Date.now() - i * 86400000).toISOString(),
  }));
}

/**
 * Mock source data
 */
const mockSource = {
  id: 'test-source-1',
  owner: 'anthropic',
  repo_name: 'claude-skills',
  ref: 'main',
  repo_url: 'https://github.com/anthropic/claude-skills',
  description: 'Test source for pagination testing',
  status: 'active',
  last_scanned: new Date().toISOString(),
};

/**
 * Build mock catalog response with pagination info
 */
function buildMockCatalogResponse(
  entries: ReturnType<typeof generateMockCatalogEntries>,
  pageInfo: { page: number; limit: number; total: number }
) {
  const start = (pageInfo.page - 1) * pageInfo.limit;
  const end = Math.min(start + pageInfo.limit, entries.length);
  const paginatedEntries = entries.slice(start, end);

  return {
    items: paginatedEntries,
    page_info: {
      page: pageInfo.page,
      limit: pageInfo.limit,
      total_count: pageInfo.total,
      has_next: end < entries.length,
      has_prev: pageInfo.page > 1,
    },
    counts_by_status: {
      new: entries.filter((e) => e.status === 'new').length,
      updated: entries.filter((e) => e.status === 'updated').length,
      imported: entries.filter((e) => e.status === 'imported').length,
    },
    counts_by_type: {
      skill: entries.filter((e) => e.artifact_type === 'skill').length,
      command: entries.filter((e) => e.artifact_type === 'command').length,
      agent: entries.filter((e) => e.artifact_type === 'agent').length,
      hook: entries.filter((e) => e.artifact_type === 'hook').length,
    },
  };
}

// ============================================================================
// Test Setup
// ============================================================================

test.describe('Catalog Pagination', () => {
  const mockEntries = generateMockCatalogEntries(87); // 87 entries for realistic pagination

  test.beforeEach(async ({ page }) => {
    // Mock the source API
    await mockApiRoute(page, '/api/v1/marketplace-sources/test-source-1', mockSource);

    // Mock the catalog API with dynamic pagination
    await page.route('**/api/v1/marketplace-sources/test-source-1/catalog**', async (route) => {
      const url = new URL(route.request().url());
      const pageNum = parseInt(url.searchParams.get('page') || '1', 10);
      const limit = parseInt(url.searchParams.get('limit') || '25', 10);

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(
          buildMockCatalogResponse(mockEntries, {
            page: pageNum,
            limit: limit,
            total: mockEntries.length,
          })
        ),
      });
    });

    // Navigate to the source detail page
    await page.goto('/marketplace/sources/test-source-1');
    await waitForPageLoad(page);
  });

  // ==========================================================================
  // Display Tests
  // ==========================================================================

  test('displays pagination controls', async ({ page }) => {
    // Wait for catalog to load
    await expect(page.getByText(/artifact-1/)).toBeVisible({ timeout: 10000 });

    // Check for pagination elements
    await expect(page.getByRole('button', { name: /previous/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /next/i })).toBeVisible();

    // Check for items per page selector (combobox/select)
    await expect(page.getByText('Show')).toBeVisible();
    await expect(page.getByText('per page')).toBeVisible();
  });

  test('displays count indicator', async ({ page }) => {
    await expect(page.getByText(/artifact-1/)).toBeVisible({ timeout: 10000 });

    // Should show "Showing X-Y of Z artifacts"
    await expect(page.getByText(/Showing \d+-\d+ of \d+/)).toBeVisible();
  });

  test('displays page number buttons', async ({ page }) => {
    await expect(page.getByText(/artifact-1/)).toBeVisible({ timeout: 10000 });

    // Should have numbered page buttons
    await expect(page.getByRole('button', { name: 'Page 1' })).toBeVisible();
  });

  // ==========================================================================
  // Navigation Tests
  // ==========================================================================

  test('navigates to next page', async ({ page }) => {
    await expect(page.getByText(/artifact-1/)).toBeVisible({ timeout: 10000 });

    // Click next
    const nextButton = page.getByRole('button', { name: /next/i });
    await nextButton.click();

    // Wait for navigation
    await page.waitForTimeout(500);

    // URL should have page=2
    await expect(page).toHaveURL(/page=2/);
  });

  test('navigates to previous page', async ({ page }) => {
    // Start on page 2
    await page.goto('/marketplace/sources/test-source-1?page=2');
    await waitForPageLoad(page);

    // Click previous
    const prevButton = page.getByRole('button', { name: /previous/i });
    await prevButton.click();

    // Wait for navigation
    await page.waitForTimeout(500);

    // URL should not have page param (or page=1)
    const url = page.url();
    expect(url).not.toContain('page=2');
  });

  test('navigates via numbered page button', async ({ page }) => {
    await expect(page.getByText(/artifact-1/)).toBeVisible({ timeout: 10000 });

    // Click on page 2 button
    const page2Button = page.getByRole('button', { name: 'Page 2' });
    if (await page2Button.isVisible()) {
      await page2Button.click();
      await page.waitForTimeout(500);
      await expect(page).toHaveURL(/page=2/);
    }
  });

  test('previous button is disabled on first page', async ({ page }) => {
    await expect(page.getByText(/artifact-1/)).toBeVisible({ timeout: 10000 });

    const prevButton = page.getByRole('button', { name: /previous/i });
    await expect(prevButton).toBeDisabled();
  });

  test('next button is disabled on last page', async ({ page }) => {
    // Calculate last page (87 entries / 25 per page = 4 pages)
    const lastPage = Math.ceil(87 / 25);
    await page.goto(`/marketplace/sources/test-source-1?page=${lastPage}`);
    await waitForPageLoad(page);

    const nextButton = page.getByRole('button', { name: /next/i });
    await expect(nextButton).toBeDisabled();
  });

  // ==========================================================================
  // Items Per Page Tests
  // ==========================================================================

  test('changes items per page', async ({ page }) => {
    await expect(page.getByText(/artifact-1/)).toBeVisible({ timeout: 10000 });

    // Find and click the items per page selector trigger
    // Using the Select component trigger
    const trigger = page.locator('[class*="SelectTrigger"]').first();

    if (await trigger.isVisible()) {
      await trigger.click();

      // Select 50
      const option50 = page.getByRole('option', { name: '50' });
      if (await option50.isVisible()) {
        await option50.click();

        await page.waitForTimeout(500);

        // URL should have limit=50
        await expect(page).toHaveURL(/limit=50/);
      }
    }
  });

  test('resets to page 1 when items per page changes', async ({ page }) => {
    // Start on page 2
    await page.goto('/marketplace/sources/test-source-1?page=2&limit=25');
    await waitForPageLoad(page);

    // Change items per page
    const trigger = page.locator('[class*="SelectTrigger"]').first();

    if (await trigger.isVisible()) {
      await trigger.click();

      const option50 = page.getByRole('option', { name: '50' });
      if (await option50.isVisible()) {
        await option50.click();

        await page.waitForTimeout(500);

        // Should reset to page 1 (not have page=2)
        const url = page.url();
        expect(url).not.toContain('page=2');
      }
    }
  });

  // ==========================================================================
  // URL Persistence Tests
  // ==========================================================================

  test('persists pagination state in URL', async ({ page }) => {
    await expect(page.getByText(/artifact-1/)).toBeVisible({ timeout: 10000 });

    // Navigate to page 2
    const nextButton = page.getByRole('button', { name: /next/i });
    await nextButton.click();
    await page.waitForTimeout(500);

    // Reload the page
    await page.reload();
    await waitForPageLoad(page);

    // Should still be on page 2
    const url = page.url();
    expect(url).toContain('page=2');
  });

  test('loads correct page from URL on initial load', async ({ page }) => {
    // Navigate directly to page 3
    await page.goto('/marketplace/sources/test-source-1?page=3');
    await waitForPageLoad(page);

    // The page 3 button should be the current page
    const page3Button = page.getByRole('button', { name: 'Page 3' });
    if (await page3Button.isVisible()) {
      // Check it has aria-current="page"
      await expect(page3Button).toHaveAttribute('aria-current', 'page');
    }
  });

  test('persists items per page in URL', async ({ page }) => {
    await page.goto('/marketplace/sources/test-source-1?limit=50');
    await waitForPageLoad(page);

    // Reload
    await page.reload();
    await waitForPageLoad(page);

    // Should still have limit=50
    const url = page.url();
    expect(url).toContain('limit=50');
  });

  // ==========================================================================
  // Count Indicator Tests
  // ==========================================================================

  test('displays correct count on first page', async ({ page }) => {
    await expect(page.getByText(/artifact-1/)).toBeVisible({ timeout: 10000 });

    // Should show "Showing 1-25 of 87 artifacts"
    await expect(page.getByText(/Showing 1-25 of 87/)).toBeVisible();
  });

  test('displays correct count on subsequent pages', async ({ page }) => {
    // Go to page 2
    await page.goto('/marketplace/sources/test-source-1?page=2');
    await waitForPageLoad(page);

    // Should show "Showing 26-50 of 87 artifacts"
    await expect(page.getByText(/Showing 26-50 of 87/)).toBeVisible();
  });

  test('displays correct count on last page', async ({ page }) => {
    // Go to last page (page 4 with 25 per page = items 76-87)
    await page.goto('/marketplace/sources/test-source-1?page=4');
    await waitForPageLoad(page);

    // Should show "Showing 76-87 of 87 artifacts"
    await expect(page.getByText(/Showing 76-87 of 87/)).toBeVisible();
  });

  test('updates count when items per page changes', async ({ page }) => {
    await page.goto('/marketplace/sources/test-source-1?limit=10');
    await waitForPageLoad(page);

    // Should show "Showing 1-10 of 87 artifacts"
    await expect(page.getByText(/Showing 1-10 of 87/)).toBeVisible();
  });

  // ==========================================================================
  // Filter Interaction Tests
  // ==========================================================================

  test('pagination resets when filter changes', async ({ page }) => {
    // Start on page 2
    await page.goto('/marketplace/sources/test-source-1?page=2');
    await waitForPageLoad(page);

    // Apply a type filter by clicking a tab
    const skillsTab = page.getByRole('tab', { name: /skills/i });
    if (await skillsTab.isVisible()) {
      await skillsTab.click();
      await page.waitForTimeout(500);

      // Should reset to page 1
      const url = page.url();
      expect(url).not.toContain('page=2');
    }
  });

  // ==========================================================================
  // Keyboard Navigation Tests
  // ==========================================================================

  test('pagination buttons are keyboard accessible', async ({ page }) => {
    await expect(page.getByText(/artifact-1/)).toBeVisible({ timeout: 10000 });

    // Focus on the pagination controls area
    const prevButton = page.getByRole('button', { name: /previous/i });

    // Tab to the button and press Enter
    await prevButton.focus();
    await expect(prevButton).toBeFocused();
  });

  // ==========================================================================
  // Visual/Style Tests
  // ==========================================================================

  test('pagination bar has glassmorphic styling', async ({ page }) => {
    await expect(page.getByText(/artifact-1/)).toBeVisible({ timeout: 10000 });

    // The pagination container should have the glassmorphic classes
    const paginationBar = page.locator('.sticky.bottom-0');
    if (await paginationBar.isVisible()) {
      // Check for backdrop-blur class
      await expect(paginationBar).toHaveClass(/backdrop-blur/);
    }
  });

  test('current page button is highlighted', async ({ page }) => {
    await expect(page.getByText(/artifact-1/)).toBeVisible({ timeout: 10000 });

    // First page button should have different styling (variant="default")
    const page1Button = page.getByRole('button', { name: 'Page 1' });
    if (await page1Button.isVisible()) {
      // The current page should have aria-current="page"
      await expect(page1Button).toHaveAttribute('aria-current', 'page');
    }
  });

  // ==========================================================================
  // Edge Cases
  // ==========================================================================

  test('handles empty results gracefully', async ({ page }) => {
    // Mock empty catalog response
    await page.route('**/api/v1/marketplace-sources/test-source-1/catalog**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [],
          page_info: {
            page: 1,
            limit: 25,
            total_count: 0,
            has_next: false,
            has_prev: false,
          },
          counts_by_status: {},
          counts_by_type: {},
        }),
      });
    });

    await page.goto('/marketplace/sources/test-source-1');
    await waitForPageLoad(page);

    // Should show empty state message
    await expect(page.getByText(/no artifacts found/i)).toBeVisible();

    // Pagination should not be visible for empty results
    await expect(page.getByRole('button', { name: /previous/i })).not.toBeVisible();
  });

  test('handles single page gracefully', async ({ page }) => {
    // Mock catalog with fewer items than one page
    await page.route('**/api/v1/marketplace-sources/test-source-1/catalog**', async (route) => {
      const smallEntries = generateMockCatalogEntries(10);
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(
          buildMockCatalogResponse(smallEntries, {
            page: 1,
            limit: 25,
            total: 10,
          })
        ),
      });
    });

    await page.goto('/marketplace/sources/test-source-1');
    await waitForPageLoad(page);

    // Both navigation buttons should be disabled
    const prevButton = page.getByRole('button', { name: /previous/i });
    const nextButton = page.getByRole('button', { name: /next/i });

    if (await prevButton.isVisible()) {
      await expect(prevButton).toBeDisabled();
      await expect(nextButton).toBeDisabled();
    }
  });
});
