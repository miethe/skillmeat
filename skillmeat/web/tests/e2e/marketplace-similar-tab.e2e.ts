/**
 * Marketplace Similar Tab — E2E Tests
 *
 * Covers the full user workflow for the "Similar" tab inside CatalogEntryModal
 * on the /marketplace/sources/[id] (source detail) page.
 *
 * The modal is triggered by clicking a catalog entry card. The "Similar" tab
 * renders one of two states depending on whether the artifact has been imported:
 *   - Imported (entry.import_id present): SimilarArtifactsTab component with
 *     loading → results or empty state, powered by GET /api/v1/artifacts/{id}/similar
 *   - Not imported (entry.import_id absent): "Import to discover similar artifacts"
 *     prompt with guidance text
 *
 * PREREQUISITES:
 *   - A running dev server: `skillmeat web dev` (or `pnpm dev` inside web/)
 *   - API server accessible at NEXT_PUBLIC_API_URL (default: http://localhost:8080)
 *   - All relevant API routes are mocked — no real data is required.
 *
 * Run:
 *   pnpm test:e2e -- --grep "Marketplace Similar Tab"
 *   # or all tests:
 *   pnpm test:e2e
 */

import { test, expect, type Page } from '@playwright/test';
import {
  mockApiRoute,
  waitForPageLoad,
  expectModalOpen,
  expectModalClosed,
  pressKey,
} from '../helpers/test-utils';

// ============================================================================
// Mock Data
// ============================================================================

const SOURCE_ID = 'source-similar-test';

/** Minimal marketplace source for setting up the detail page */
const mockSource = {
  id: SOURCE_ID,
  owner: 'anthropics',
  repo_name: 'anthropic-skills',
  ref: 'main',
  root_hint: '',
  repo_url: 'https://github.com/anthropics/anthropic-skills',
  trust_level: 'official',
  artifact_count: 3,
  scan_status: 'success',
  last_scan_at: '2024-12-10T14:00:00Z',
  created_at: '2024-12-01T10:00:00Z',
  description: 'Official Anthropic skills collection.',
  readme_content: null,
};

/**
 * Catalog entry that has been imported — import_id is set so the
 * SimilarArtifactsTab API query is enabled.
 */
const mockImportedEntry = {
  id: 'entry-imported-1',
  source_id: SOURCE_ID,
  name: 'canvas-design',
  artifact_type: 'skill',
  path: '.claude/skills/canvas-design.md',
  status: 'imported',
  confidence_score: 95,
  upstream_url:
    'https://github.com/anthropics/anthropic-skills/blob/main/.claude/skills/canvas-design.md',
  detected_at: '2024-12-08T10:00:00Z',
  import_date: '2024-12-09T08:00:00Z',
  /** Presence of import_id enables the Similar tab's API query */
  import_id: 'aabbccdd-0000-0000-0000-000000000001',
};

/**
 * Catalog entry that has NOT been imported — import_id is absent, so the
 * Similar tab shows the "Import to discover similar artifacts" empty state.
 */
const mockUnimportedEntry = {
  id: 'entry-new-1',
  source_id: SOURCE_ID,
  name: 'code-review',
  artifact_type: 'command',
  path: '.claude/commands/code-review.md',
  status: 'new',
  confidence_score: 88,
  upstream_url:
    'https://github.com/anthropics/anthropic-skills/blob/main/.claude/commands/code-review.md',
  detected_at: '2024-12-08T10:00:00Z',
  // import_id is intentionally absent
};

/** Catalog response with both entry variants */
const mockCatalogResponse = {
  items: [mockImportedEntry, mockUnimportedEntry],
  total: 2,
  page: 1,
  page_size: 25,
  has_next: false,
  counts_by_type: { skill: 1, command: 1 },
  counts_by_status: { imported: 1, new: 1 },
};

/** Similar artifacts response with results — used when import_id is present */
const mockSimilarResults = [
  {
    artifact_id: 'bbccddee-0000-0000-0000-000000000002',
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
    artifact_id: 'ccddee00-0000-0000-0000-000000000003',
    name: 'frontend-design',
    artifact_type: 'skill',
    source: 'anthropics/skills/frontend-design',
    composite_score: 0.71,
    match_type: 'related' as const,
    breakdown: {
      content_score: 0.7,
      structure_score: 0.72,
      metadata_score: 0.75,
      keyword_score: 0.68,
      semantic_score: null,
    },
  },
];

const mockSimilarResponse = {
  artifact_id: mockImportedEntry.import_id,
  items: mockSimilarResults,
  total: mockSimilarResults.length,
};

const mockEmptySimilarResponse = {
  artifact_id: mockImportedEntry.import_id,
  items: [],
  total: 0,
};

// ============================================================================
// Shared Setup Helpers
// ============================================================================

/**
 * Registers API route mocks for the source detail page.
 * Always call this before navigating to the page.
 */
async function setupSourceDetailMocks(page: Page) {
  await mockApiRoute(page, `/api/v1/marketplace/sources/${SOURCE_ID}`, mockSource);
  await mockApiRoute(
    page,
    `/api/v1/marketplace/sources/${SOURCE_ID}/catalog*`,
    mockCatalogResponse
  );
  // Stub rescan / import endpoints to prevent 404 noise
  await mockApiRoute(page, `/api/v1/marketplace/sources/${SOURCE_ID}/rescan`, {
    success: true,
  });
  await mockApiRoute(page, `/api/v1/marketplace/sources/${SOURCE_ID}/import*`, {
    success: true,
    imported_count: 1,
  });
}

/** Navigate to the source detail page and wait for it to fully render. */
async function navigateToSourceDetail(page: Page) {
  await page.goto(`/marketplace/sources/${SOURCE_ID}`);
  await waitForPageLoad(page);
}

/**
 * Opens the CatalogEntryModal for the specified catalog entry by clicking its
 * card via the "View details" aria-label.
 *
 * Returns the dialog locator once it is visible.
 */
async function openEntryModal(page: Page, entryName: string, artifactType: string) {
  const card = page.getByRole('button', {
    name: new RegExp(`view details for ${entryName} ${artifactType}`, 'i'),
  });
  await expect(card).toBeVisible({ timeout: 8000 });
  await card.click();

  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible({ timeout: 5000 });
  return dialog;
}

/**
 * Locates and clicks the "Similar" tab trigger inside an already-open modal.
 * Returns the tab trigger element.
 */
async function clickSimilarTab(page: Page) {
  const similarTab = page.getByRole('tab', { name: /similar/i });
  await expect(similarTab).toBeVisible();
  await similarTab.click();
  return similarTab;
}

// ============================================================================
// Test Suite: Similar Tab — Tab Navigation & Visibility
// ============================================================================

test.describe('Marketplace Similar Tab', () => {
  test.describe('tab navigation and visibility', () => {
    test.beforeEach(async ({ page }) => {
      await mockApiRoute(
        page,
        '/api/v1/artifacts/*/similar*',
        mockSimilarResponse
      );
      await setupSourceDetailMocks(page);
      await navigateToSourceDetail(page);
    });

    test('Similar tab is visible inside the CatalogEntryModal tab bar', async ({ page }) => {
      await openEntryModal(page, mockImportedEntry.name, mockImportedEntry.artifact_type);

      const similarTab = page.getByRole('tab', { name: /similar/i });
      await expect(similarTab).toBeVisible();
    });

    test('clicking the Similar tab marks it as the active tab', async ({ page }) => {
      await openEntryModal(page, mockImportedEntry.name, mockImportedEntry.artifact_type);
      const similarTab = await clickSimilarTab(page);

      await expect(similarTab).toHaveAttribute('aria-selected', 'true');
    });

    test('Similar tab panel becomes visible after click', async ({ page }) => {
      await openEntryModal(page, mockImportedEntry.name, mockImportedEntry.artifact_type);
      await clickSimilarTab(page);

      // After clicking, either the results list or an empty/non-import state should appear
      const resultsList = page.getByRole('list', { name: /similar artifact/i });
      const emptyState = page.getByText(/no similar artifacts found/i);
      const notImportedState = page.getByText(/import to discover similar artifacts/i);

      await page.waitForTimeout(1500);
      const anyVisible =
        (await resultsList.isVisible()) ||
        (await emptyState.isVisible()) ||
        (await notImportedState.isVisible());
      expect(anyVisible).toBe(true);
    });
  });

  // ============================================================================
  // Test Suite: Imported Artifact — SimilarArtifactsTab with Results
  // ============================================================================

  test.describe('imported artifact — results state', () => {
    test.beforeEach(async ({ page }) => {
      await mockApiRoute(
        page,
        '/api/v1/artifacts/*/similar*',
        mockSimilarResponse
      );
      await setupSourceDetailMocks(page);
      await navigateToSourceDetail(page);
    });

    test('results grid renders after loading resolves', async ({ page }) => {
      await openEntryModal(page, mockImportedEntry.name, mockImportedEntry.artifact_type);
      await clickSimilarTab(page);

      const resultsList = page.getByRole('list', { name: /similar artifact/i });
      await expect(resultsList).toBeVisible({ timeout: 8000 });
    });

    test('results grid shows at least one artifact card', async ({ page }) => {
      await openEntryModal(page, mockImportedEntry.name, mockImportedEntry.artifact_type);
      await clickSimilarTab(page);

      const resultsList = page.getByRole('list', { name: /similar artifact/i });
      await expect(resultsList).toBeVisible({ timeout: 8000 });

      const cards = resultsList.getByRole('listitem');
      expect(await cards.count()).toBeGreaterThan(0);
    });

    test('result cards display artifact names from the similar response', async ({ page }) => {
      await openEntryModal(page, mockImportedEntry.name, mockImportedEntry.artifact_type);
      await clickSimilarTab(page);

      const resultsList = page.getByRole('list', { name: /similar artifact/i });
      await expect(resultsList).toBeVisible({ timeout: 8000 });

      await expect(resultsList).toContainText(mockSimilarResults[0].name);
    });

    test('result cards carry similarity score badges', async ({ page }) => {
      await openEntryModal(page, mockImportedEntry.name, mockImportedEntry.artifact_type);
      await clickSimilarTab(page);

      const resultsList = page.getByRole('list', { name: /similar artifact/i });
      await expect(resultsList).toBeVisible({ timeout: 8000 });

      // Score badges render the composite_score as a percentage, e.g. "87%"
      const scoreBadge = resultsList.getByText(/\d+%/).first();
      await expect(scoreBadge).toBeVisible();
    });
  });

  // ============================================================================
  // Test Suite: Imported Artifact — Empty Similar Results
  // ============================================================================

  test.describe('imported artifact — empty results state', () => {
    test.beforeEach(async ({ page }) => {
      await mockApiRoute(
        page,
        '/api/v1/artifacts/*/similar*',
        mockEmptySimilarResponse
      );
      await setupSourceDetailMocks(page);
      await navigateToSourceDetail(page);
    });

    test('shows "No similar artifacts found" when response has no items', async ({ page }) => {
      await openEntryModal(page, mockImportedEntry.name, mockImportedEntry.artifact_type);
      await clickSimilarTab(page);

      await expect(
        page.getByText(/no similar artifacts found/i)
      ).toBeVisible({ timeout: 8000 });
    });

    test('empty state includes guidance text about threshold', async ({ page }) => {
      await openEntryModal(page, mockImportedEntry.name, mockImportedEntry.artifact_type);
      await clickSimilarTab(page);

      // Wait for loading to clear
      await page.waitForTimeout(1000);
      await expect(
        page.getByText(/adjusting the similarity threshold/i)
      ).toBeVisible({ timeout: 8000 });
    });

    test('results list is not rendered in the empty state', async ({ page }) => {
      await openEntryModal(page, mockImportedEntry.name, mockImportedEntry.artifact_type);
      await clickSimilarTab(page);

      await page.waitForTimeout(1000);
      const resultsList = page.getByRole('list', { name: /similar artifact/i });
      await expect(resultsList).not.toBeVisible();
    });
  });

  // ============================================================================
  // Test Suite: Imported Artifact — Loading State
  // ============================================================================

  test.describe('imported artifact — loading state', () => {
    test('shows loading skeleton while query is in flight', async ({ page }) => {
      // Delay the similar-artifacts endpoint to catch the intermediate loading state
      await page.route('**/api/v1/artifacts/*/similar*', async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockSimilarResponse),
        });
      });

      await setupSourceDetailMocks(page);
      await navigateToSourceDetail(page);
      await openEntryModal(page, mockImportedEntry.name, mockImportedEntry.artifact_type);
      await clickSimilarTab(page);

      // The SimilarArtifactsTab loading skeleton carries aria-busy="true" and
      // aria-label="Loading similar artifacts"
      const skeleton = page.getByLabel('Loading similar artifacts');
      await expect(skeleton).toBeVisible({ timeout: 3000 });
      await expect(skeleton).toHaveAttribute('aria-busy', 'true');
    });
  });

  // ============================================================================
  // Test Suite: Imported Artifact — Error State
  // ============================================================================

  test.describe('imported artifact — error state', () => {
    test.beforeEach(async ({ page }) => {
      await mockApiRoute(
        page,
        '/api/v1/artifacts/*/similar*',
        { detail: 'Internal server error' },
        500
      );
      await setupSourceDetailMocks(page);
      await navigateToSourceDetail(page);
    });

    test('shows error alert when the similar API returns 500', async ({ page }) => {
      await openEntryModal(page, mockImportedEntry.name, mockImportedEntry.artifact_type);
      await clickSimilarTab(page);

      const errorAlert = page.getByRole('alert');
      await expect(errorAlert).toBeVisible({ timeout: 8000 });
      await expect(errorAlert).toContainText(/failed to load similar artifacts/i);
    });

    test('Retry button is rendered and enabled in the error state', async ({ page }) => {
      await openEntryModal(page, mockImportedEntry.name, mockImportedEntry.artifact_type);
      await clickSimilarTab(page);

      await expect(page.getByRole('alert')).toBeVisible({ timeout: 8000 });

      const retryButton = page.getByRole('button', { name: /retry/i });
      await expect(retryButton).toBeVisible();
      await expect(retryButton).toBeEnabled();
    });

    test('clicking Retry re-fires the query and shows results on success', async ({ page }) => {
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

      await setupSourceDetailMocks(page);
      await navigateToSourceDetail(page);
      await openEntryModal(page, mockImportedEntry.name, mockImportedEntry.artifact_type);
      await clickSimilarTab(page);

      // Wait for error state
      await expect(page.getByRole('alert')).toBeVisible({ timeout: 8000 });

      // Click Retry
      await page.getByRole('button', { name: /retry/i }).click();

      // After the second call succeeds, the results grid should appear
      const resultsList = page.getByRole('list', { name: /similar artifact/i });
      await expect(resultsList).toBeVisible({ timeout: 8000 });
    });
  });

  // ============================================================================
  // Test Suite: Not-Imported Artifact — "Import to Discover" State
  // ============================================================================

  test.describe('not-imported artifact — import prompt state', () => {
    test.beforeEach(async ({ page }) => {
      // No similar endpoint needed — import_id is absent on this entry,
      // so SimilarArtifactsTab is not rendered and no API call is made.
      await setupSourceDetailMocks(page);
      await navigateToSourceDetail(page);
    });

    test('Similar tab is visible for a not-yet-imported artifact', async ({ page }) => {
      await openEntryModal(page, mockUnimportedEntry.name, mockUnimportedEntry.artifact_type);

      const similarTab = page.getByRole('tab', { name: /similar/i });
      await expect(similarTab).toBeVisible();
    });

    test('clicking Similar tab activates it', async ({ page }) => {
      await openEntryModal(page, mockUnimportedEntry.name, mockUnimportedEntry.artifact_type);
      const similarTab = await clickSimilarTab(page);

      await expect(similarTab).toHaveAttribute('aria-selected', 'true');
    });

    test('shows "Import to discover similar artifacts" prompt when entry is not imported', async ({
      page,
    }) => {
      await openEntryModal(page, mockUnimportedEntry.name, mockUnimportedEntry.artifact_type);
      await clickSimilarTab(page);

      await expect(
        page.getByText(/import to discover similar artifacts/i)
      ).toBeVisible({ timeout: 5000 });
    });

    test('shows supplementary guidance about collection membership', async ({ page }) => {
      await openEntryModal(page, mockUnimportedEntry.name, mockUnimportedEntry.artifact_type);
      await clickSimilarTab(page);

      await expect(
        page.getByText(/once this artifact is added to your collection/i)
      ).toBeVisible({ timeout: 5000 });
    });

    test('does not make a similar-artifacts API request for unimported entries', async ({
      page,
    }) => {
      const similarRequests: string[] = [];
      page.on('request', (req) => {
        if (req.url().includes('/similar')) {
          similarRequests.push(req.url());
        }
      });

      await openEntryModal(page, mockUnimportedEntry.name, mockUnimportedEntry.artifact_type);
      await clickSimilarTab(page);

      // Allow time for any inadvertent request to appear
      await page.waitForTimeout(1500);
      expect(similarRequests).toHaveLength(0);
    });
  });

  // ============================================================================
  // Test Suite: Keyboard Accessibility
  // ============================================================================

  test.describe('keyboard accessibility', () => {
    test.beforeEach(async ({ page }) => {
      await mockApiRoute(
        page,
        '/api/v1/artifacts/*/similar*',
        mockSimilarResponse
      );
      await setupSourceDetailMocks(page);
      await navigateToSourceDetail(page);
    });

    test('Similar tab is focusable via direct .focus() call', async ({ page }) => {
      await openEntryModal(page, mockImportedEntry.name, mockImportedEntry.artifact_type);

      const similarTab = page.getByRole('tab', { name: /similar/i });
      await similarTab.focus();
      await expect(similarTab).toBeFocused();
    });

    test('pressing Enter on the Similar tab activates it', async ({ page }) => {
      await openEntryModal(page, mockImportedEntry.name, mockImportedEntry.artifact_type);

      const similarTab = page.getByRole('tab', { name: /similar/i });
      await similarTab.focus();
      await page.keyboard.press('Enter');

      await expect(similarTab).toHaveAttribute('aria-selected', 'true');
    });

    test('pressing Space on the Similar tab activates it', async ({ page }) => {
      await openEntryModal(page, mockImportedEntry.name, mockImportedEntry.artifact_type);

      const similarTab = page.getByRole('tab', { name: /similar/i });
      await similarTab.focus();
      await page.keyboard.press('Space');

      await expect(similarTab).toHaveAttribute('aria-selected', 'true');
    });

    test('result cards are reachable via keyboard focus', async ({ page }) => {
      await openEntryModal(page, mockImportedEntry.name, mockImportedEntry.artifact_type);
      await clickSimilarTab(page);

      const resultsList = page.getByRole('list', { name: /similar artifact/i });
      await expect(resultsList).toBeVisible({ timeout: 8000 });

      // Locate the first interactive element inside the first result card
      const firstCard = resultsList.getByRole('listitem').first();
      const interactiveEl = firstCard
        .locator('button, [role="button"], [tabindex="0"]')
        .first();
      await interactiveEl.focus();
      await expect(interactiveEl).toBeFocused();
    });

    test('pressing Escape closes the CatalogEntryModal', async ({ page }) => {
      await openEntryModal(page, mockImportedEntry.name, mockImportedEntry.artifact_type);
      await clickSimilarTab(page);

      await page.keyboard.press('Escape');

      const dialog = page.getByRole('dialog');
      await expect(dialog).not.toBeVisible({ timeout: 3000 });
    });

    test('page remains navigable after modal is dismissed with Escape', async ({ page }) => {
      await openEntryModal(page, mockImportedEntry.name, mockImportedEntry.artifact_type);
      await clickSimilarTab(page);
      await page.keyboard.press('Escape');

      await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 3000 });
      // The source detail page should still have at least one visible heading
      await expect(page.getByRole('heading', { level: 1 }).or(
        page.getByRole('heading', { level: 2 })
      ).first()).toBeVisible();
    });
  });

  // ============================================================================
  // Test Suite: Tab Switching (Similar ↔ Other Tabs)
  // ============================================================================

  test.describe('tab switching', () => {
    test.beforeEach(async ({ page }) => {
      await mockApiRoute(
        page,
        '/api/v1/artifacts/*/similar*',
        mockSimilarResponse
      );
      await setupSourceDetailMocks(page);
      await navigateToSourceDetail(page);
    });

    test('switching to another tab and back to Similar preserves tab state', async ({ page }) => {
      await openEntryModal(page, mockImportedEntry.name, mockImportedEntry.artifact_type);
      await clickSimilarTab(page);

      const resultsList = page.getByRole('list', { name: /similar artifact/i });
      await expect(resultsList).toBeVisible({ timeout: 8000 });

      // Navigate to the Overview / first tab in the modal
      const overviewTab = page.getByRole('tab', { name: /overview/i });
      if (await overviewTab.isVisible()) {
        await overviewTab.click();
        await expect(overviewTab).toHaveAttribute('aria-selected', 'true');
      }

      // Return to Similar
      const similarTab = page.getByRole('tab', { name: /similar/i });
      await similarTab.click();
      await expect(similarTab).toHaveAttribute('aria-selected', 'true');

      // Results should still be available (TanStack Query cache)
      await expect(resultsList).toBeVisible({ timeout: 5000 });
    });
  });

  // ============================================================================
  // Test Suite: Responsive Behavior
  // ============================================================================

  test.describe('responsive layout', () => {
    test('Similar tab is usable on mobile viewport (375px)', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });

      await mockApiRoute(
        page,
        '/api/v1/artifacts/*/similar*',
        mockSimilarResponse
      );
      await setupSourceDetailMocks(page);
      await navigateToSourceDetail(page);
      await openEntryModal(page, mockImportedEntry.name, mockImportedEntry.artifact_type);

      const similarTab = page.getByRole('tab', { name: /similar/i });
      await expect(similarTab).toBeVisible();
      await similarTab.click();
      await expect(similarTab).toHaveAttribute('aria-selected', 'true');

      // Any terminal state (results, empty, error) is acceptable
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

    test('import prompt is visible on mobile for unimported artifact', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });

      await setupSourceDetailMocks(page);
      await navigateToSourceDetail(page);
      await openEntryModal(page, mockUnimportedEntry.name, mockUnimportedEntry.artifact_type);

      const similarTab = page.getByRole('tab', { name: /similar/i });
      await expect(similarTab).toBeVisible();
      await similarTab.click();

      await expect(
        page.getByText(/import to discover similar artifacts/i)
      ).toBeVisible({ timeout: 5000 });
    });
  });

  // ============================================================================
  // Test Suite: Full User Journey
  // ============================================================================

  test.describe('full user journey', () => {
    test('navigate to source detail, open imported artifact, view Similar tab results', async ({
      page,
    }) => {
      await mockApiRoute(
        page,
        '/api/v1/artifacts/*/similar*',
        mockSimilarResponse
      );
      await setupSourceDetailMocks(page);

      // Step 1: Navigate to the marketplace source detail page
      await page.goto(`/marketplace/sources/${SOURCE_ID}`);
      await waitForPageLoad(page);

      // Step 2: Verify the source detail page loaded
      await expect(
        page.getByText(/anthropics\/anthropic-skills/i).or(page.getByText('anthropics'))
      ).toBeVisible({ timeout: 8000 });

      // Step 3: Click the imported artifact card to open the modal
      const card = page.getByRole('button', {
        name: new RegExp(
          `view details for ${mockImportedEntry.name} ${mockImportedEntry.artifact_type}`,
          'i'
        ),
      });
      await expect(card).toBeVisible({ timeout: 8000 });
      await card.click();

      // Step 4: Verify the dialog opens
      const dialog = page.getByRole('dialog');
      await expect(dialog).toBeVisible({ timeout: 5000 });

      // Step 5: Click the Similar tab
      const similarTab = page.getByRole('tab', { name: /similar/i });
      await expect(similarTab).toBeVisible();
      await similarTab.click();
      await expect(similarTab).toHaveAttribute('aria-selected', 'true');

      // Step 6: Verify the results grid appears
      const resultsList = page.getByRole('list', { name: /similar artifact/i });
      await expect(resultsList).toBeVisible({ timeout: 8000 });

      // Step 7: Verify at least one result card is present
      const cards = resultsList.getByRole('listitem');
      expect(await cards.count()).toBeGreaterThan(0);
    });

    test('navigate to source detail, open unimported artifact, see import prompt', async ({
      page,
    }) => {
      await setupSourceDetailMocks(page);

      // Step 1: Navigate
      await page.goto(`/marketplace/sources/${SOURCE_ID}`);
      await waitForPageLoad(page);

      // Step 2: Open the unimported artifact modal
      const card = page.getByRole('button', {
        name: new RegExp(
          `view details for ${mockUnimportedEntry.name} ${mockUnimportedEntry.artifact_type}`,
          'i'
        ),
      });
      await expect(card).toBeVisible({ timeout: 8000 });
      await card.click();

      const dialog = page.getByRole('dialog');
      await expect(dialog).toBeVisible({ timeout: 5000 });

      // Step 3: Click the Similar tab
      const similarTab = page.getByRole('tab', { name: /similar/i });
      await expect(similarTab).toBeVisible();
      await similarTab.click();
      await expect(similarTab).toHaveAttribute('aria-selected', 'true');

      // Step 4: Verify the import prompt is shown (not the API-driven component)
      await expect(
        page.getByText(/import to discover similar artifacts/i)
      ).toBeVisible({ timeout: 5000 });

      await expect(
        page.getByText(/once this artifact is added to your collection/i)
      ).toBeVisible();
    });
  });
});
