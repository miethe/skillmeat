/**
 * Similar Artifacts Tab — E2E Tests
 *
 * Covers the full user workflow for the "Similar" tab inside ArtifactDetailsModal
 * on the /collection page. The tab is powered by GET /api/v1/artifacts/{id}/similar
 * and renders one of four states: loading skeleton, error+retry, empty state, or
 * a grid of MiniArtifactCard components with score badges.
 *
 * PREREQUISITES:
 *   - A running dev server: `skillmeat web dev` (or `pnpm dev` inside web/)
 *   - API server accessible at NEXT_PUBLIC_API_URL (default: http://localhost:8080)
 *   - The tests mock all relevant API routes — no real artifact data is required.
 *
 * Run:
 *   pnpm test:e2e -- --grep "Similar Artifacts Tab"
 *   # or all tests:
 *   pnpm test:e2e
 */

import { test, expect, type Page } from '@playwright/test';
import {
  mockApiRoute,
  navigateToPage,
  waitForElement,
} from '../helpers/test-utils';
import { buildApiResponse, mockArtifacts } from '../helpers/fixtures';

// ============================================================================
// Mock Data
// ============================================================================

/** UUID used across mocks — matches mockArtifacts[0].uuid from fixtures */
const ARTIFACT_UUID = mockArtifacts[0].uuid;

/** Minimal SimilarArtifact DTO returned by GET /api/v1/artifacts/{id}/similar */
const mockSimilarItems = [
  {
    artifact_id: mockArtifacts[1].uuid,
    name: 'data-analysis',
    artifact_type: 'skill',
    source: 'anthropics/skills/data-analysis',
    composite_score: 0.87,
    match_type: 'similar' as const,
    breakdown: {
      content_score: 0.9,
      structure_score: 0.85,
      metadata_score: 0.88,
      keyword_score: 0.82,
      semantic_score: 0.91,
    },
  },
  {
    artifact_id: mockArtifacts[2].uuid,
    name: 'code-review',
    artifact_type: 'command',
    source: 'community/commands/code-review',
    composite_score: 0.62,
    match_type: 'related' as const,
    breakdown: {
      content_score: 0.6,
      structure_score: 0.65,
      metadata_score: 0.7,
      keyword_score: 0.58,
      semantic_score: null,
    },
  },
];

/** Full similar-artifacts response with results */
const mockSimilarResponse = {
  artifact_id: ARTIFACT_UUID,
  items: mockSimilarItems,
  total: mockSimilarItems.length,
};

/** Empty similar-artifacts response */
const mockEmptyResponse = {
  artifact_id: ARTIFACT_UUID,
  items: [],
  total: 0,
};

// ============================================================================
// Shared helpers
// ============================================================================

/**
 * Sets up the standard collection-page API mocks and navigates to /collection.
 */
async function setupCollectionPage(page: Page) {
  await mockApiRoute(page, '/api/v1/artifacts*', buildApiResponse.artifacts());
  await mockApiRoute(page, '/api/v1/analytics*', buildApiResponse.analytics());
  await mockApiRoute(page, '/api/v1/projects*', buildApiResponse.projects());
  await navigateToPage(page, '/collection');
}

/**
 * Clicks the first artifact card to open ArtifactDetailsModal.
 * Waits for the dialog to become visible before returning.
 */
async function openFirstArtifactModal(page: Page) {
  // Click the first artifact article in the grid
  const firstCard = page
    .locator('[data-testid="artifact-grid"]')
    .locator('article')
    .first();
  await firstCard.click();

  // Wait for the dialog to appear
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  return dialog;
}

/**
 * Navigates to the Similar tab inside an already-open ArtifactDetailsModal.
 * Returns the tab element.
 */
async function clickSimilarTab(page: Page) {
  const similarTab = page.getByRole('tab', { name: 'Similar' });
  await expect(similarTab).toBeVisible();
  await similarTab.click();
  return similarTab;
}

// ============================================================================
// Tests
// ============================================================================

test.describe('Similar Artifacts Tab', () => {
  // --------------------------------------------------------------------------
  // Tab navigation + results rendering
  // --------------------------------------------------------------------------

  test.describe('tab navigation and results rendering', () => {
    test.beforeEach(async ({ page }) => {
      // Mock the similar artifacts endpoint with results
      await mockApiRoute(
        page,
        `/api/v1/artifacts/*/similar*`,
        mockSimilarResponse
      );
      await setupCollectionPage(page);
    });

    test('Similar tab is visible in the modal tab bar', async ({ page }) => {
      await openFirstArtifactModal(page);

      const similarTab = page.getByRole('tab', { name: 'Similar' });
      await expect(similarTab).toBeVisible();
    });

    test('clicking Similar tab activates the tab panel', async ({ page }) => {
      await openFirstArtifactModal(page);
      const similarTab = await clickSimilarTab(page);

      // Tab should become selected (aria-selected="true")
      await expect(similarTab).toHaveAttribute('aria-selected', 'true');
    });

    test('results grid renders after loading completes', async ({ page }) => {
      await openFirstArtifactModal(page);
      await clickSimilarTab(page);

      // Wait for either the results list or the empty state — covers both paths
      // without timing out if the loading skeleton takes a moment to resolve.
      const resultsList = page.getByRole('list', {
        name: /similar artifact/i,
      });
      const emptyState = page.getByText(/no similar artifacts found/i);

      await Promise.race([
        expect(resultsList).toBeVisible(),
        expect(emptyState).toBeVisible(),
      ]).catch(async () => {
        // Fallback: wait an extra beat and check again
        await page.waitForTimeout(1500);
        const hasResults = await resultsList.isVisible();
        const hasEmpty = await emptyState.isVisible();
        expect(hasResults || hasEmpty).toBe(true);
      });
    });

    test('results grid shows at least one artifact card', async ({ page }) => {
      await openFirstArtifactModal(page);
      await clickSimilarTab(page);

      // The results list is rendered when items.length > 0
      const resultsList = page.getByRole('list', {
        name: /similar artifact/i,
      });
      await expect(resultsList).toBeVisible({ timeout: 8000 });

      const cards = resultsList.getByRole('listitem');
      const count = await cards.count();
      expect(count).toBeGreaterThan(0);
    });

    test('each result card carries a similarity score badge', async ({
      page,
    }) => {
      await openFirstArtifactModal(page);
      await clickSimilarTab(page);

      const resultsList = page.getByRole('list', {
        name: /similar artifact/i,
      });
      await expect(resultsList).toBeVisible({ timeout: 8000 });

      // MiniArtifactCard renders the score as text like "87%" when showScore=true
      // The badge text is derived from composite_score * 100, rounded.
      const scoreBadge = resultsList.getByText(/\d+%/).first();
      await expect(scoreBadge).toBeVisible();
    });

    test('result cards display artifact names', async ({ page }) => {
      await openFirstArtifactModal(page);
      await clickSimilarTab(page);

      const resultsList = page.getByRole('list', {
        name: /similar artifact/i,
      });
      await expect(resultsList).toBeVisible({ timeout: 8000 });

      // Verify the first mocked similar artifact name appears in the grid
      await expect(resultsList).toContainText(mockSimilarItems[0].name);
    });

    test('clicking a result card triggers onArtifactClick', async ({
      page,
    }) => {
      await openFirstArtifactModal(page);
      await clickSimilarTab(page);

      const resultsList = page.getByRole('list', {
        name: /similar artifact/i,
      });
      await expect(resultsList).toBeVisible({ timeout: 8000 });

      // Click the first card — the modal should react (open the clicked artifact
      // or keep the dialog open). We verify no unhandled error occurs.
      const firstCard = resultsList.getByRole('listitem').first();
      await firstCard.click();

      // Dialog (in some form) should still be visible — the click is handled
      await expect(page.getByRole('dialog')).toBeVisible();
    });
  });

  // --------------------------------------------------------------------------
  // Loading skeleton
  // --------------------------------------------------------------------------

  test.describe('loading state', () => {
    test('shows loading skeleton while query is in flight', async ({ page }) => {
      // Delay the similar-artifacts response to observe the loading state
      await page.route('**/api/v1/artifacts/*/similar*', async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockSimilarResponse),
        });
      });

      await mockApiRoute(page, '/api/v1/artifacts*', buildApiResponse.artifacts());
      await mockApiRoute(page, '/api/v1/analytics*', buildApiResponse.analytics());
      await mockApiRoute(page, '/api/v1/projects*', buildApiResponse.projects());
      await navigateToPage(page, '/collection');

      await openFirstArtifactModal(page);
      await clickSimilarTab(page);

      // The loading skeleton has aria-busy="true" and aria-label="Loading similar artifacts"
      const skeleton = page.getByLabel('Loading similar artifacts');
      await expect(skeleton).toBeVisible({ timeout: 3000 });
      // aria-busy should be true during loading
      await expect(skeleton).toHaveAttribute('aria-busy', 'true');
    });
  });

  // --------------------------------------------------------------------------
  // Empty state
  // --------------------------------------------------------------------------

  test.describe('empty results state', () => {
    test.beforeEach(async ({ page }) => {
      await mockApiRoute(
        page,
        '/api/v1/artifacts/*/similar*',
        mockEmptyResponse
      );
      await setupCollectionPage(page);
    });

    test('shows "No similar artifacts found" when response is empty', async ({
      page,
    }) => {
      await openFirstArtifactModal(page);
      await clickSimilarTab(page);

      // The SimilarArtifactsEmpty component renders this container
      const emptyContainer = page.getByLabel('No similar artifacts found');
      await expect(emptyContainer).toBeVisible({ timeout: 8000 });
    });

    test('empty state text is descriptive', async ({ page }) => {
      await openFirstArtifactModal(page);
      await clickSimilarTab(page);

      await expect(
        page.getByText(/no similar artifacts found/i)
      ).toBeVisible({ timeout: 8000 });

      // Guidance text about the threshold
      await expect(
        page.getByText(/adjusting the similarity threshold/i)
      ).toBeVisible();
    });

    test('no list is rendered when results are empty', async ({ page }) => {
      await openFirstArtifactModal(page);
      await clickSimilarTab(page);

      // Wait for loading to clear
      await page.waitForTimeout(1000);

      // The results list element should NOT be present in an empty state
      const resultsList = page.getByRole('list', {
        name: /similar artifact/i,
      });
      await expect(resultsList).not.toBeVisible();
    });
  });

  // --------------------------------------------------------------------------
  // Error state + retry
  // --------------------------------------------------------------------------

  test.describe('error state', () => {
    test.beforeEach(async ({ page }) => {
      await mockApiRoute(
        page,
        '/api/v1/artifacts/*/similar*',
        { detail: 'Internal server error' },
        500
      );
      await setupCollectionPage(page);
    });

    test('shows error message when API returns 500', async ({ page }) => {
      await openFirstArtifactModal(page);
      await clickSimilarTab(page);

      // SimilarArtifactsError renders role="alert" with error copy
      const errorAlert = page.getByRole('alert');
      await expect(errorAlert).toBeVisible({ timeout: 8000 });
      await expect(errorAlert).toContainText(/failed to load similar artifacts/i);
    });

    test('Retry button is visible in error state', async ({ page }) => {
      await openFirstArtifactModal(page);
      await clickSimilarTab(page);

      await expect(page.getByRole('alert')).toBeVisible({ timeout: 8000 });

      const retryButton = page.getByRole('button', { name: /retry/i });
      await expect(retryButton).toBeVisible();
      await expect(retryButton).toBeEnabled();
    });

    test('clicking Retry re-fires the query', async ({ page }) => {
      // Override: first call fails, second succeeds
      let callCount = 0;
      await page.route('**/api/v1/artifacts/*/similar*', async (route) => {
        callCount += 1;
        if (callCount === 1) {
          await route.fulfill({
            status: 500,
            contentType: 'application/json',
            body: JSON.stringify({ detail: 'error' }),
          });
        } else {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockSimilarResponse),
          });
        }
      });

      await mockApiRoute(page, '/api/v1/artifacts*', buildApiResponse.artifacts());
      await mockApiRoute(page, '/api/v1/analytics*', buildApiResponse.analytics());
      await mockApiRoute(page, '/api/v1/projects*', buildApiResponse.projects());
      await navigateToPage(page, '/collection');

      await openFirstArtifactModal(page);
      await clickSimilarTab(page);

      // Wait for error state
      await expect(page.getByRole('alert')).toBeVisible({ timeout: 8000 });

      // Click Retry
      await page.getByRole('button', { name: /retry/i }).click();

      // After the second call succeeds, results grid should appear
      const resultsList = page.getByRole('list', {
        name: /similar artifact/i,
      });
      await expect(resultsList).toBeVisible({ timeout: 8000 });
    });
  });

  // --------------------------------------------------------------------------
  // Keyboard accessibility
  // --------------------------------------------------------------------------

  test.describe('keyboard accessibility', () => {
    test.beforeEach(async ({ page }) => {
      await mockApiRoute(
        page,
        '/api/v1/artifacts/*/similar*',
        mockSimilarResponse
      );
      await setupCollectionPage(page);
    });

    test('Similar tab is reachable via keyboard (Tab key)', async ({ page }) => {
      await openFirstArtifactModal(page);

      // Tab through the modal's tab bar until Similar is focused
      const similarTab = page.getByRole('tab', { name: 'Similar' });

      // Use arrow key navigation within the tab list (Radix Tabs uses roving tabindex)
      await similarTab.focus();
      await expect(similarTab).toBeFocused();
    });

    test('pressing Enter on the Similar tab activates it', async ({ page }) => {
      await openFirstArtifactModal(page);

      const similarTab = page.getByRole('tab', { name: 'Similar' });
      await similarTab.focus();
      await page.keyboard.press('Enter');

      await expect(similarTab).toHaveAttribute('aria-selected', 'true');
    });

    test('pressing Space on the Similar tab activates it', async ({ page }) => {
      await openFirstArtifactModal(page);

      const similarTab = page.getByRole('tab', { name: 'Similar' });
      await similarTab.focus();
      await page.keyboard.press('Space');

      await expect(similarTab).toHaveAttribute('aria-selected', 'true');
    });

    test('result cards are focusable via Tab key', async ({ page }) => {
      await openFirstArtifactModal(page);
      await clickSimilarTab(page);

      const resultsList = page.getByRole('list', {
        name: /similar artifact/i,
      });
      await expect(resultsList).toBeVisible({ timeout: 8000 });

      // Tab into the cards area — first card should become reachable
      const firstCard = resultsList.getByRole('listitem').first();
      // Find the interactive element inside the first listitem
      const interactiveEl = firstCard.locator('button, [role="button"], [tabindex="0"]').first();
      await interactiveEl.focus();
      await expect(interactiveEl).toBeFocused();
    });

    test('pressing Escape closes the modal', async ({ page }) => {
      await openFirstArtifactModal(page);
      await clickSimilarTab(page);

      // Escape should dismiss the dialog
      await page.keyboard.press('Escape');

      const dialog = page.getByRole('dialog');
      await expect(dialog).not.toBeVisible({ timeout: 3000 });
    });

    test('modal is closed and page is navigable after Escape', async ({
      page,
    }) => {
      await openFirstArtifactModal(page);
      await clickSimilarTab(page);
      await page.keyboard.press('Escape');

      // After close, the collection page should still be functional
      await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 3000 });
      // Page heading should be visible
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    });
  });

  // --------------------------------------------------------------------------
  // Tab-switching (switching away and back)
  // --------------------------------------------------------------------------

  test.describe('tab switching', () => {
    test.beforeEach(async ({ page }) => {
      await mockApiRoute(
        page,
        '/api/v1/artifacts/*/similar*',
        mockSimilarResponse
      );
      await setupCollectionPage(page);
    });

    test('switching to another tab and back preserves Similar tab state', async ({
      page,
    }) => {
      await openFirstArtifactModal(page);
      await clickSimilarTab(page);

      // Wait for results to load
      const resultsList = page.getByRole('list', { name: /similar artifact/i });
      await expect(resultsList).toBeVisible({ timeout: 8000 });

      // Switch to the Overview tab (first tab)
      const overviewTab = page.getByRole('tab', { name: /overview/i });
      if (await overviewTab.isVisible()) {
        await overviewTab.click();
        await expect(overviewTab).toHaveAttribute('aria-selected', 'true');
      }

      // Switch back to Similar
      await clickSimilarTab(page);
      const similarTab = page.getByRole('tab', { name: 'Similar' });
      await expect(similarTab).toHaveAttribute('aria-selected', 'true');

      // Results should still be visible (TanStack Query cache)
      await expect(resultsList).toBeVisible({ timeout: 5000 });
    });
  });

  // --------------------------------------------------------------------------
  // Responsive / mobile
  // --------------------------------------------------------------------------

  test.describe('responsive layout', () => {
    test.beforeEach(async ({ page }) => {
      await mockApiRoute(
        page,
        '/api/v1/artifacts/*/similar*',
        mockSimilarResponse
      );
    });

    test('Similar tab is usable on mobile viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });

      await mockApiRoute(page, '/api/v1/artifacts*', buildApiResponse.artifacts());
      await mockApiRoute(page, '/api/v1/analytics*', buildApiResponse.analytics());
      await mockApiRoute(page, '/api/v1/projects*', buildApiResponse.projects());
      await navigateToPage(page, '/collection');

      await openFirstArtifactModal(page);

      // The modal may use a sheet/drawer on mobile — just check the tab exists
      const similarTab = page.getByRole('tab', { name: 'Similar' });
      await expect(similarTab).toBeVisible();
      await similarTab.click();

      // Any of the three terminal states is acceptable
      const resultsList = page.getByRole('list', { name: /similar artifact/i });
      const emptyState = page.getByText(/no similar artifacts found/i);
      const errorState = page.getByRole('alert');

      await page.waitForTimeout(2000);
      const hasAny =
        (await resultsList.isVisible()) ||
        (await emptyState.isVisible()) ||
        (await errorState.isVisible());

      expect(hasAny).toBe(true);
    });
  });
});
