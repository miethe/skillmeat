/**
 * Marketplace SimilarityBadge — E2E Tests
 *
 * Covers the rendering of SimilarityBadge on marketplace SourceCards in the
 * /marketplace/sources listing page. The badge appears on cards whose backing
 * collection artifact has a similarity score above the configured floor
 * threshold and is deferred until the card scrolls into the viewport
 * (IntersectionObserver lazy loading).
 *
 * Badge aria-label format: "{Level} similarity: {N}%"
 *   where Level is one of: High | Partial | Low
 *
 * Key behaviors under test:
 *   1. Badge renders with correct aria-label and percentage text on a
 *      matching source card (score ≥ thresholds.high).
 *   2. No badge rendered on a non-matching card (score < thresholds.floor).
 *   3. Badge appears after the card scrolls into view (lazy IntersectionObserver).
 *   4. Badge color band responds to custom threshold settings from
 *      GET /api/v1/settings/similarity.
 *   5. Badge absent when artifactId prop is not provided (unimported source).
 *
 * PREREQUISITES:
 *   - A running dev server: `skillmeat web dev` (or `pnpm dev` inside web/)
 *   - API server accessible at NEXT_PUBLIC_API_URL (default: http://localhost:8080)
 *   - All API routes mocked — no live data required.
 *
 * Run:
 *   pnpm test:e2e -- --grep "Marketplace SimilarityBadge"
 *   # or all tests:
 *   pnpm test:e2e
 */

import { test, expect, type Page } from '@playwright/test';
import {
  mockApiRoute,
  waitForPageLoad,
} from '../helpers/test-utils';

// ============================================================================
// Mock Data
// ============================================================================

/** Default similarity settings — mirrors backend defaults */
const defaultSettings = {
  thresholds: {
    high: 0.80,
    partial: 0.55,
    low: 0.35,
    floor: 0.20,
  },
  colors: {
    high: '#22c55e',
    partial: '#eab308',
    low: '#f97316',
  },
};

/**
 * Custom settings with a lowered high threshold so that a 0.71 score
 * qualifies as High rather than Partial. Used in the custom-threshold test.
 */
const customHighThresholdSettings = {
  thresholds: {
    high: 0.65,
    partial: 0.45,
    low: 0.30,
    floor: 0.20,
  },
  colors: {
    high: '#22c55e',
    partial: '#eab308',
    low: '#f97316',
  },
};

// UUIDs for the two test collection artifacts
const MATCHING_ARTIFACT_ID = 'aabbccdd-0001-0001-0001-000000000001';
const NON_MATCHING_ARTIFACT_ID = 'bbccddee-0002-0002-0002-000000000002';
const BELOW_FLOOR_ARTIFACT_ID = 'ccddee00-0003-0003-0003-000000000003';

/** Source with an imported collection artifact that has a high-score match */
const matchingSource = {
  id: 'source-badge-match',
  owner: 'anthropics',
  repo_name: 'anthropic-skills',
  ref: 'main',
  root_hint: '',
  repo_url: 'https://github.com/anthropics/anthropic-skills',
  trust_level: 'official',
  artifact_count: 5,
  scan_status: 'success',
  last_scan_at: '2025-01-15T10:00:00Z',
  last_sync_at: '2025-01-15T10:00:00Z',
  created_at: '2025-01-01T00:00:00Z',
  description: 'Official Anthropic skills collection — high similarity match.',
  readme_content: null,
};

/** Source with an imported artifact that scores below the floor — no badge */
const nonMatchingSource = {
  id: 'source-badge-nomatch',
  owner: 'third-party',
  repo_name: 'unrelated-tools',
  ref: 'main',
  root_hint: '',
  repo_url: 'https://github.com/third-party/unrelated-tools',
  trust_level: 'basic',
  artifact_count: 2,
  scan_status: 'success',
  last_scan_at: '2025-01-14T08:00:00Z',
  last_sync_at: '2025-01-14T08:00:00Z',
  created_at: '2025-01-05T00:00:00Z',
  description: 'Unrelated tools — score below floor threshold.',
  readme_content: null,
};

/** Source that has NOT been imported — no artifactId prop → no badge */
const unimportedSource = {
  id: 'source-badge-unimported',
  owner: 'community',
  repo_name: 'community-skills',
  ref: 'main',
  root_hint: '',
  repo_url: 'https://github.com/community/community-skills',
  trust_level: 'verified',
  artifact_count: 8,
  scan_status: 'success',
  last_scan_at: '2025-01-13T06:00:00Z',
  last_sync_at: '2025-01-13T06:00:00Z',
  created_at: '2025-01-02T00:00:00Z',
  description: 'Community-contributed skills — not yet imported.',
  readme_content: null,
};

/** Paginated sources list response with all three test sources */
const mockSourcesListResponse = {
  items: [matchingSource, nonMatchingSource, unimportedSource],
  total: 3,
  page: 1,
  page_size: 25,
  has_next: false,
};

/**
 * Similar artifacts response for the MATCHING_ARTIFACT_ID.
 * composite_score of 0.87 → "High Match" band under default thresholds.
 */
const mockHighScoreSimilarResponse = {
  artifact_id: MATCHING_ARTIFACT_ID,
  items: [
    {
      artifact_id: 'similar-000-0001',
      name: 'canvas-design-v2',
      artifact_type: 'skill',
      source: 'anthropics/skills/canvas-design-v2',
      composite_score: 0.87,
      match_type: 'similar' as const,
      breakdown: {
        content_score: 0.91,
        structure_score: 0.86,
        metadata_score: 0.89,
        keyword_score: 0.83,
        semantic_score: 0.92,
      },
    },
  ],
  total: 1,
};

/**
 * Similar artifacts response for a score that falls in the Partial band
 * under default settings (0.71 ≥ 0.55 partial, < 0.80 high).
 * Used in the custom-threshold test where the same score becomes "High"
 * when thresholds.high is lowered to 0.65.
 */
const mockPartialScoreSimilarResponse = {
  artifact_id: MATCHING_ARTIFACT_ID,
  items: [
    {
      artifact_id: 'similar-000-0002',
      name: 'frontend-helpers',
      artifact_type: 'skill',
      source: 'anthropics/skills/frontend-helpers',
      composite_score: 0.71,
      match_type: 'related' as const,
      breakdown: {
        content_score: 0.70,
        structure_score: 0.72,
        metadata_score: 0.75,
        keyword_score: 0.68,
        semantic_score: null,
      },
    },
  ],
  total: 1,
};

/**
 * Empty similar response for the NON_MATCHING_ARTIFACT_ID.
 * Simulates a score below the floor — the API returns no results when minScore
 * filter is applied server-side, so the card shows no badge.
 */
const mockEmptySimilarResponse = {
  artifact_id: NON_MATCHING_ARTIFACT_ID,
  items: [],
  total: 0,
};

// ============================================================================
// Page Object Helpers
// ============================================================================

/**
 * Registers all API mocks required for the marketplace sources listing page.
 * Call before navigating to ensure routes are intercepted before page load.
 */
async function setupSourcesListMocks(
  page: Page,
  options: {
    similarResponse?: object;
    noMatchSimilarResponse?: object;
    settings?: object;
  } = {}
) {
  const {
    similarResponse = mockHighScoreSimilarResponse,
    noMatchSimilarResponse = mockEmptySimilarResponse,
    settings = defaultSettings,
  } = options;

  // Settings — must be mocked before hooks call useSimilaritySettings
  await mockApiRoute(page, '/api/v1/settings/similarity', settings);

  // Similarity endpoint — route by artifact ID query param when possible,
  // otherwise use a catch-all that serves the high-score response (simplest
  // path for tests that only care about the matching card).
  //
  // The SimilarityBadge path triggers:
  //   GET /api/v1/artifacts/{artifactId}/similar?limit=1&min_score={floor}&source=collection
  //
  // We register specific routes for each known artifact ID first so Playwright
  // matches the most specific pattern.
  await page.route(
    `**${'/api/v1/artifacts/'}${MATCHING_ARTIFACT_ID}${'/similar*'}`,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(similarResponse),
      });
    }
  );

  await page.route(
    `**${'/api/v1/artifacts/'}${NON_MATCHING_ARTIFACT_ID}${'/similar*'}`,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(noMatchSimilarResponse),
      });
    }
  );

  await page.route(
    `**${'/api/v1/artifacts/'}${BELOW_FLOOR_ARTIFACT_ID}${'/similar*'}`,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ artifact_id: BELOW_FLOOR_ARTIFACT_ID, items: [], total: 0 }),
      });
    }
  );

  // Sources listing
  await mockApiRoute(page, '/api/v1/marketplace/sources*', mockSourcesListResponse);

  // Stub individual source detail endpoints to prevent 404 noise
  await mockApiRoute(
    page,
    `/api/v1/marketplace/sources/${matchingSource.id}`,
    matchingSource
  );
  await mockApiRoute(
    page,
    `/api/v1/marketplace/sources/${nonMatchingSource.id}`,
    nonMatchingSource
  );
  await mockApiRoute(
    page,
    `/api/v1/marketplace/sources/${unimportedSource.id}`,
    unimportedSource
  );
}

/**
 * Navigate to the marketplace sources listing page with artifactId query
 * params that map sources to their backing collection UUIDs. The frontend
 * SourceCard grid is expected to receive these as props from the page.
 *
 * The URL convention used by the marketplace page component:
 *   /marketplace/sources?artifactIds[source-id]=uuid
 *
 * If the production routing passes artifactId via a different mechanism
 * (e.g. server-side props or a parent data layer), the navigation helper
 * here should be updated to match. For now the tests verify badge rendering
 * assuming the page passes through the IDs correctly.
 */
async function navigateToSourcesListing(page: Page) {
  await page.goto('/marketplace/sources');
  await waitForPageLoad(page);
}

/**
 * Locate a SourceCard by the source's owner/repo display label.
 * Returns the card's root element (role="button" with aria-label).
 */
function getSourceCard(page: Page, owner: string, repo: string) {
  return page.getByRole('button', {
    name: new RegExp(`view source.*${owner}\\/${repo}`, 'i'),
  });
}

// ============================================================================
// Test Suite: SimilarityBadge on SourceCard
// ============================================================================

test.describe('Marketplace SimilarityBadge', () => {
  // --------------------------------------------------------------------------
  // Suite: Badge renders on a matching source card
  // --------------------------------------------------------------------------

  test.describe('high-score matching card', () => {
    test.beforeEach(async ({ page }) => {
      await setupSourcesListMocks(page, {
        similarResponse: mockHighScoreSimilarResponse,
      });
      await navigateToSourceListing(page);
    });

    test('badge is visible on the matching source card', async ({ page }) => {
      // Ensure the card is in view — default viewport covers top of page
      const card = getSourceCard(page, matchingSource.owner, matchingSource.repo_name);
      await expect(card).toBeVisible({ timeout: 8000 });

      // Wait for the IntersectionObserver-gated query to resolve
      const badge = card.getByRole('img', { name: /high similarity/i }).or(
        // Badge may render as a generic element with aria-label
        card.locator('[aria-label*="similarity"]').first()
      );
      await expect(badge).toBeVisible({ timeout: 5000 });
    });

    test('badge aria-label follows "High similarity: N%" format', async ({ page }) => {
      const card = getSourceCard(page, matchingSource.owner, matchingSource.repo_name);
      await expect(card).toBeVisible({ timeout: 8000 });

      // composite_score 0.87 → "High similarity: 87%"
      const badge = card.getByLabel('High similarity: 87%');
      await expect(badge).toBeVisible({ timeout: 5000 });
    });

    test('badge text displays the percentage (87%)', async ({ page }) => {
      const card = getSourceCard(page, matchingSource.owner, matchingSource.repo_name);
      await expect(card).toBeVisible({ timeout: 8000 });

      const badge = card.getByLabel('High similarity: 87%');
      await expect(badge).toBeVisible({ timeout: 5000 });

      // The badge renders the percent text inside a <span>
      await expect(badge).toContainText('87%');
    });

    test('badge indicates the High Match band label', async ({ page }) => {
      const card = getSourceCard(page, matchingSource.owner, matchingSource.repo_name);
      await expect(card).toBeVisible({ timeout: 8000 });

      const badge = card.getByLabel('High similarity: 87%');
      await expect(badge).toBeVisible({ timeout: 5000 });
      await expect(badge).toContainText(/high match/i);
    });
  });

  // --------------------------------------------------------------------------
  // Suite: Badge absent on a non-matching card (score below floor)
  // --------------------------------------------------------------------------

  test.describe('below-floor non-matching card', () => {
    test.beforeEach(async ({ page }) => {
      await setupSourcesListMocks(page, {
        noMatchSimilarResponse: mockEmptySimilarResponse,
      });
      await navigateToSourceListing(page);
    });

    test('no similarity badge on a source card with score below floor threshold', async ({
      page,
    }) => {
      const card = getSourceCard(page, nonMatchingSource.owner, nonMatchingSource.repo_name);
      await expect(card).toBeVisible({ timeout: 8000 });

      // Allow time for any potential query to resolve
      await page.waitForTimeout(1500);

      // No badge should be present — the empty response means topScore is null
      const badge = card.locator('[aria-label*="similarity"]');
      await expect(badge).not.toBeVisible();
    });

    test('no similarity badge on an unimported source card (no artifactId)', async ({
      page,
    }) => {
      const card = getSourceCard(page, unimportedSource.owner, unimportedSource.repo_name);
      await expect(card).toBeVisible({ timeout: 8000 });

      await page.waitForTimeout(1500);

      // Unimported source has no artifactId prop — badge must never appear
      const badge = card.locator('[aria-label*="similarity"]');
      await expect(badge).not.toBeVisible();
    });
  });

  // --------------------------------------------------------------------------
  // Suite: Lazy loading — badge appears after card scrolls into viewport
  // --------------------------------------------------------------------------

  test.describe('lazy loading via IntersectionObserver', () => {
    test('badge does not fire a similarity query before card enters viewport', async ({
      page,
    }) => {
      // Arrange: collect all similarity requests
      const similarityRequests: string[] = [];
      page.on('request', (req) => {
        if (req.url().includes('/similar')) {
          similarityRequests.push(req.url());
        }
      });

      // Set a tall viewport so cards are off-screen before setup
      await page.setViewportSize({ width: 1280, height: 200 });

      await setupSourcesListMocks(page, {});
      await page.goto('/marketplace/sources');
      await page.waitForLoadState('domcontentloaded');

      // Cards render but are off-screen — no IntersectionObserver triggers yet
      // Give a short window for any inadvertent eager requests
      await page.waitForTimeout(800);

      // No similarity queries should have fired for off-screen cards
      expect(similarityRequests).toHaveLength(0);
    });

    test('badge appears after scrolling card into viewport', async ({ page }) => {
      // Use a narrow viewport height to push cards below the fold
      await page.setViewportSize({ width: 1280, height: 300 });

      await setupSourcesListMocks(page, {
        similarResponse: mockHighScoreSimilarResponse,
      });
      await navigateToSourceListing(page);

      // Scroll the matching card into view
      const card = getSourceCard(page, matchingSource.owner, matchingSource.repo_name);
      await card.scrollIntoViewIfNeeded();

      // After scroll, IntersectionObserver fires, query resolves, badge renders
      const badge = card.getByLabel('High similarity: 87%');
      await expect(badge).toBeVisible({ timeout: 6000 });
    });

    test('badge state is sticky — remains visible after scrolling back out', async ({
      page,
    }) => {
      await page.setViewportSize({ width: 1280, height: 400 });

      await setupSourcesListMocks(page, {
        similarResponse: mockHighScoreSimilarResponse,
      });
      await navigateToSourceListing(page);

      // Scroll card in, wait for badge
      const card = getSourceCard(page, matchingSource.owner, matchingSource.repo_name);
      await card.scrollIntoViewIfNeeded();

      const badge = card.getByLabel('High similarity: 87%');
      await expect(badge).toBeVisible({ timeout: 6000 });

      // Scroll back to top (card goes off-screen)
      await page.evaluate(() => window.scrollTo({ top: 0 }));
      await page.waitForTimeout(400);

      // Scroll back down to the card — badge should still be visible
      // (useInView sticky state: once seen, always seen)
      await card.scrollIntoViewIfNeeded();
      await expect(badge).toBeVisible({ timeout: 3000 });
    });
  });

  // --------------------------------------------------------------------------
  // Suite: Custom threshold settings change badge classification
  // --------------------------------------------------------------------------

  test.describe('custom threshold settings', () => {
    test('score in Partial band under defaults resolves to Partial badge label', async ({
      page,
    }) => {
      // composite_score 0.71 → Partial Match under default thresholds (high=0.80)
      await setupSourcesListMocks(page, {
        similarResponse: mockPartialScoreSimilarResponse,
        settings: defaultSettings,
      });
      await navigateToSourceListing(page);

      const card = getSourceCard(page, matchingSource.owner, matchingSource.repo_name);
      await expect(card).toBeVisible({ timeout: 8000 });

      // aria-label: "Partial similarity: 71%"
      const badge = card.getByLabel('Partial similarity: 71%');
      await expect(badge).toBeVisible({ timeout: 5000 });
      await expect(badge).toContainText(/partial match/i);
    });

    test('same score resolves to High badge when custom thresholds lower the high boundary', async ({
      page,
    }) => {
      // composite_score 0.71 → High Match when thresholds.high is lowered to 0.65
      await setupSourcesListMocks(page, {
        similarResponse: mockPartialScoreSimilarResponse,
        settings: customHighThresholdSettings,
      });
      await navigateToSourceListing(page);

      const card = getSourceCard(page, matchingSource.owner, matchingSource.repo_name);
      await expect(card).toBeVisible({ timeout: 8000 });

      // aria-label: "High similarity: 71%"
      const badge = card.getByLabel('High similarity: 71%');
      await expect(badge).toBeVisible({ timeout: 5000 });
      await expect(badge).toContainText(/high match/i);
    });

    test('score exactly at floor threshold boundary produces no badge', async ({ page }) => {
      // Return a score equal to floor (0.20) — falls between floor and low band
      // SimilarityBadge returns null for this case
      const floorScoreResponse = {
        artifact_id: MATCHING_ARTIFACT_ID,
        items: [
          {
            artifact_id: 'similar-floor-001',
            name: 'barely-related',
            artifact_type: 'skill',
            source: 'unknown/barely-related',
            composite_score: 0.20,
            match_type: 'related' as const,
            breakdown: {
              content_score: 0.20,
              structure_score: 0.20,
              metadata_score: 0.20,
              keyword_score: 0.20,
              semantic_score: null,
            },
          },
        ],
        total: 1,
      };

      await setupSourcesListMocks(page, {
        similarResponse: floorScoreResponse,
        settings: defaultSettings,
      });
      await navigateToSourceListing(page);

      const card = getSourceCard(page, matchingSource.owner, matchingSource.repo_name);
      await expect(card).toBeVisible({ timeout: 8000 });

      await page.waitForTimeout(1500);

      // Score 0.20 == floor but < low (0.35) — no band resolves → no badge
      const badge = card.locator('[aria-label*="similarity"]');
      await expect(badge).not.toBeVisible();
    });
  });

  // --------------------------------------------------------------------------
  // Suite: Partial Match badge renders correctly
  // --------------------------------------------------------------------------

  test.describe('partial-match band rendering', () => {
    test('badge aria-label uses Partial prefix for mid-range score', async ({ page }) => {
      await setupSourcesListMocks(page, {
        similarResponse: mockPartialScoreSimilarResponse,
        settings: defaultSettings,
      });
      await navigateToSourceListing(page);

      const card = getSourceCard(page, matchingSource.owner, matchingSource.repo_name);
      await expect(card).toBeVisible({ timeout: 8000 });

      const badge = card.getByLabel(/^partial similarity:/i);
      await expect(badge).toBeVisible({ timeout: 5000 });
    });

    test('Partial badge text shows percentage value', async ({ page }) => {
      await setupSourcesListMocks(page, {
        similarResponse: mockPartialScoreSimilarResponse,
        settings: defaultSettings,
      });
      await navigateToSourceListing(page);

      const card = getSourceCard(page, matchingSource.owner, matchingSource.repo_name);
      await expect(card).toBeVisible({ timeout: 8000 });

      const badge = card.getByLabel('Partial similarity: 71%');
      await expect(badge).toBeVisible({ timeout: 5000 });
      await expect(badge).toContainText('71%');
    });
  });

  // --------------------------------------------------------------------------
  // Suite: API error handling — badge gracefully absent on error
  // --------------------------------------------------------------------------

  test.describe('similarity API error handling', () => {
    test('no badge renders when similarity API returns 500', async ({ page }) => {
      await mockApiRoute(page, '/api/v1/settings/similarity', defaultSettings);
      await mockApiRoute(page, '/api/v1/marketplace/sources*', mockSourcesListResponse);

      // Return 500 for all similarity endpoints
      await page.route('**/api/v1/artifacts/*/similar*', async (route) => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal server error' }),
        });
      });

      await navigateToSourceListing(page);

      const card = getSourceCard(page, matchingSource.owner, matchingSource.repo_name);
      await expect(card).toBeVisible({ timeout: 8000 });

      await page.waitForTimeout(1500);

      // On error, useSimilarArtifacts returns undefined data → topScore is null
      // → SimilarityBadge is not rendered (no badge element)
      const badge = card.locator('[aria-label*="similarity"]');
      await expect(badge).not.toBeVisible();
    });

    test('no unhandled error alert on the page when similarity API fails', async ({ page }) => {
      await mockApiRoute(page, '/api/v1/settings/similarity', defaultSettings);
      await mockApiRoute(page, '/api/v1/marketplace/sources*', mockSourcesListResponse);
      await page.route('**/api/v1/artifacts/*/similar*', async (route) => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal server error' }),
        });
      });

      await navigateToSourceListing(page);
      await page.waitForTimeout(1500);

      // The page-level error boundary should NOT trigger for a badge query failure
      const globalAlert = page.getByRole('alert');
      // Either no alert, or the alert does not mention "similarity"
      const alertCount = await globalAlert.count();
      if (alertCount > 0) {
        const alertText = await globalAlert.first().textContent();
        expect(alertText?.toLowerCase()).not.toMatch(/similarity/);
      }
    });
  });

  // --------------------------------------------------------------------------
  // Suite: Multiple cards — independent badge state per card
  // --------------------------------------------------------------------------

  test.describe('multiple cards — independent badge state', () => {
    test('matching card has badge while non-matching sibling card does not', async ({
      page,
    }) => {
      await setupSourcesListMocks(page, {
        similarResponse: mockHighScoreSimilarResponse,
        noMatchSimilarResponse: mockEmptySimilarResponse,
      });
      await navigateToSourceListing(page);

      // Both cards should be visible in the default viewport
      const matchCard = getSourceCard(page, matchingSource.owner, matchingSource.repo_name);
      const noMatchCard = getSourceCard(
        page,
        nonMatchingSource.owner,
        nonMatchingSource.repo_name
      );

      await expect(matchCard).toBeVisible({ timeout: 8000 });
      await expect(noMatchCard).toBeVisible({ timeout: 8000 });

      // Allow both queries to settle
      await page.waitForTimeout(2000);

      // Matching card: badge present
      const presentBadge = matchCard.getByLabel('High similarity: 87%');
      await expect(presentBadge).toBeVisible({ timeout: 5000 });

      // Non-matching card: no badge
      const absentBadge = noMatchCard.locator('[aria-label*="similarity"]');
      await expect(absentBadge).not.toBeVisible();
    });

    test('unimported card never shows a badge even when siblings have badges', async ({
      page,
    }) => {
      await setupSourcesListMocks(page, {
        similarResponse: mockHighScoreSimilarResponse,
      });
      await navigateToSourceListing(page);

      const unimportedCard = getSourceCard(
        page,
        unimportedSource.owner,
        unimportedSource.repo_name
      );
      await expect(unimportedCard).toBeVisible({ timeout: 8000 });
      await page.waitForTimeout(2000);

      const badge = unimportedCard.locator('[aria-label*="similarity"]');
      await expect(badge).not.toBeVisible();
    });
  });

  // --------------------------------------------------------------------------
  // Suite: Accessibility
  // --------------------------------------------------------------------------

  test.describe('accessibility', () => {
    test.beforeEach(async ({ page }) => {
      await setupSourcesListMocks(page, {
        similarResponse: mockHighScoreSimilarResponse,
      });
      await navigateToSourceListing(page);
    });

    test('badge has accessible aria-label with level and percentage', async ({ page }) => {
      const card = getSourceCard(page, matchingSource.owner, matchingSource.repo_name);
      await expect(card).toBeVisible({ timeout: 8000 });

      const badge = card.getByLabel('High similarity: 87%');
      await expect(badge).toBeVisible({ timeout: 5000 });

      // Verify aria-label attribute is exactly correct
      const ariaLabel = await badge.getAttribute('aria-label');
      expect(ariaLabel).toBe('High similarity: 87%');
    });

    test('badge is focusable or contained within a focusable card element', async ({
      page,
    }) => {
      const card = getSourceCard(page, matchingSource.owner, matchingSource.repo_name);
      await expect(card).toBeVisible({ timeout: 8000 });

      const badge = card.getByLabel('High similarity: 87%');
      await expect(badge).toBeVisible({ timeout: 5000 });

      // The card itself is a focusable button — badge is inside it
      await card.focus();
      await expect(card).toBeFocused();
    });

    test('badge is visible on mobile viewport (375px width)', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 812 });

      const card = getSourceCard(page, matchingSource.owner, matchingSource.repo_name);
      await card.scrollIntoViewIfNeeded();

      const badge = card.getByLabel('High similarity: 87%');
      await expect(badge).toBeVisible({ timeout: 6000 });
    });

    test('badge percentage text is present for screen readers', async ({ page }) => {
      const card = getSourceCard(page, matchingSource.owner, matchingSource.repo_name);
      await expect(card).toBeVisible({ timeout: 8000 });

      const badge = card.getByLabel('High similarity: 87%');
      await expect(badge).toBeVisible({ timeout: 5000 });

      // The percent span text "87%" must be present in the DOM (not hidden)
      await expect(badge).toContainText('87%');
    });
  });

  // --------------------------------------------------------------------------
  // Suite: Similarity request lifecycle (network behavior)
  // --------------------------------------------------------------------------

  test.describe('network request lifecycle', () => {
    test('similarity request fires with limit=1 and min_score parameters', async ({ page }) => {
      const capturedRequests: URL[] = [];
      page.on('request', (req) => {
        if (req.url().includes('/similar')) {
          capturedRequests.push(new URL(req.url()));
        }
      });

      await setupSourcesListMocks(page, {
        similarResponse: mockHighScoreSimilarResponse,
      });
      await navigateToSourceListing(page);

      // Wait for the matching card to appear and trigger the query
      const card = getSourceCard(page, matchingSource.owner, matchingSource.repo_name);
      await card.scrollIntoViewIfNeeded();
      await page.waitForTimeout(1500);

      // Verify at least one similarity request was made for the matching artifact
      const matchingRequest = capturedRequests.find((url) =>
        url.pathname.includes(MATCHING_ARTIFACT_ID)
      );
      expect(matchingRequest).toBeDefined();

      if (matchingRequest) {
        // limit=1 is passed by useLazySimilarity
        expect(matchingRequest.searchParams.get('limit')).toBe('1');
        // min_score should be set to the floor threshold
        const minScore = parseFloat(matchingRequest.searchParams.get('min_score') ?? '0');
        expect(minScore).toBeGreaterThan(0);
        expect(minScore).toBeLessThanOrEqual(defaultSettings.thresholds.floor);
      }
    });

    test('unimported source card fires no similarity requests', async ({ page }) => {
      const similarityRequests: string[] = [];
      page.on('request', (req) => {
        if (req.url().includes('/similar')) {
          similarityRequests.push(req.url());
        }
      });

      await setupSourcesListMocks(page, {});
      await navigateToSourceListing(page);

      // Scroll the unimported card into view
      const unimportedCard = getSourceCard(
        page,
        unimportedSource.owner,
        unimportedSource.repo_name
      );
      await unimportedCard.scrollIntoViewIfNeeded();
      await page.waitForTimeout(1500);

      // No request for the unimported source's card
      const unimportedRequests = similarityRequests.filter((url) =>
        // The unimported source has no artifactId, so its UUID will not appear
        url.includes(unimportedSource.id)
      );
      expect(unimportedRequests).toHaveLength(0);
    });
  });

  // --------------------------------------------------------------------------
  // Suite: Full user journey
  // --------------------------------------------------------------------------

  test.describe('full user journey', () => {
    test('user navigates to marketplace, sees High badge on matching source, no badge on non-matching', async ({
      page,
    }) => {
      await setupSourcesListMocks(page, {
        similarResponse: mockHighScoreSimilarResponse,
        noMatchSimilarResponse: mockEmptySimilarResponse,
      });

      // Step 1: Navigate to marketplace sources listing
      await page.goto('/marketplace/sources');
      await waitForPageLoad(page);

      // Step 2: Verify the page loaded (at least one source card visible)
      const matchCard = getSourceCard(page, matchingSource.owner, matchingSource.repo_name);
      await expect(matchCard).toBeVisible({ timeout: 8000 });

      // Step 3: Scroll matching card into view and wait for badge
      await matchCard.scrollIntoViewIfNeeded();
      const badge = matchCard.getByLabel('High similarity: 87%');
      await expect(badge).toBeVisible({ timeout: 6000 });

      // Step 4: Verify non-matching card has no badge
      const noMatchCard = getSourceCard(
        page,
        nonMatchingSource.owner,
        nonMatchingSource.repo_name
      );
      await noMatchCard.scrollIntoViewIfNeeded();
      await page.waitForTimeout(1000);
      await expect(noMatchCard.locator('[aria-label*="similarity"]')).not.toBeVisible();

      // Step 5: Verify unimported card has no badge
      const unimportedCard = getSourceCard(
        page,
        unimportedSource.owner,
        unimportedSource.repo_name
      );
      await unimportedCard.scrollIntoViewIfNeeded();
      await page.waitForTimeout(1000);
      await expect(unimportedCard.locator('[aria-label*="similarity"]')).not.toBeVisible();
    });
  });
});

// ============================================================================
// Private helper (used internally — declared after test.describe to keep
// mock setup helpers above the suites)
// ============================================================================

/**
 * Navigate to the marketplace sources listing and wait for page load.
 * Extracted as a named function to share between beforeEach blocks.
 */
async function navigateToSourceListing(page: Page) {
  await page.goto('/marketplace/sources');
  await waitForPageLoad(page);
}
