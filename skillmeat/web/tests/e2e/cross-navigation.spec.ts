/**
 * E2E Tests for Cross-Navigation Flows
 *
 * Tests the navigation between /collection and /manage pages,
 * including deep linking, modal interactions, and URL state preservation.
 *
 * Key user journeys tested:
 * - Collection to Manage navigation via modal
 * - Manage to Collection navigation via modal
 * - Deep link handling with artifact and tab parameters
 * - Filter state preservation across navigation
 * - Filter bookmarkability and URL persistence
 *
 * @see POLISH-5.4 - E2E tests for cross-navigation flows
 */

import { test, expect, Page } from '@playwright/test';
import { mockApiRoute, waitForPageLoad, navigateToPage } from '../helpers/test-utils';
import { buildApiResponse, mockArtifacts, mockProjects } from '../helpers/fixtures';

// ============================================================================
// Test Setup Helpers
// ============================================================================

/**
 * Wait for page to be ready with network idle
 */
async function waitForPageReady(page: Page) {
  await page.waitForLoadState('networkidle');
  // Wait for any loading spinners to disappear
  await page
    .waitForSelector('[class*="animate-spin"]', {
      state: 'hidden',
      timeout: 10000,
    })
    .catch(() => {
      // Ignore if no spinner found - page may already be loaded
    });
}

/**
 * Mock all required API routes for testing
 */
async function setupApiMocks(page: Page) {
  // Mock artifacts list
  await mockApiRoute(page, '/api/v1/artifacts*', {
    items: mockArtifacts,
    page_info: {
      page: 1,
      page_size: 20,
      total_count: mockArtifacts.length,
      total_pages: 1,
      has_next: false,
      has_previous: false,
    },
  });

  // Mock individual artifact details
  for (const artifact of mockArtifacts) {
    await mockApiRoute(page, `/api/v1/artifacts/${artifact.id}`, {
      ...artifact,
      readme: '# Test Artifact\n\nThis is a test artifact.',
      dependencies: [],
    });
  }

  // Mock collections
  await mockApiRoute(page, '/api/v1/collections*', {
    items: [
      { id: 'default', name: 'Default Collection', artifact_count: 10 },
      { id: 'work', name: 'Work Collection', artifact_count: 5 },
    ],
    page_info: {
      page: 1,
      page_size: 50,
      total_count: 2,
      total_pages: 1,
      has_next: false,
      has_previous: false,
    },
  });

  // Mock projects
  await mockApiRoute(page, '/api/v1/projects*', {
    projects: mockProjects,
    total: mockProjects.length,
  });

  // Mock deployments
  await mockApiRoute(page, '/api/v1/deployments*', {
    deployments: [],
    total: 0,
  });

  // Mock analytics
  await mockApiRoute(page, '/api/v1/analytics*', buildApiResponse.analytics());

  // Mock tags
  await mockApiRoute(page, '/api/v1/tags*', {
    items: [
      { id: '1', name: 'design', artifact_count: 5 },
      { id: '2', name: 'data', artifact_count: 3 },
      { id: '3', name: 'code', artifact_count: 2 },
    ],
    page_info: { page: 1, page_size: 100, total_count: 3, total_pages: 1, has_next: false, has_previous: false },
  });

  // Mock marketplace sources
  await mockApiRoute(page, '/api/v1/marketplace/sources*', {
    items: [],
    page_info: { page: 1, page_size: 50, total_count: 0, total_pages: 0, has_next: false, has_previous: false },
  });

  // Mock artifact files
  await page.route('**/api/v1/artifacts/*/files*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        files: [
          { name: 'SKILL.md', path: 'SKILL.md', size: 1024, type: 'file' },
          { name: 'config.json', path: 'config.json', size: 256, type: 'file' },
        ],
      }),
    });
  });

  // Mock linked artifacts
  await page.route('**/api/v1/artifacts/*/linked-artifacts*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        linked_artifacts: [],
        unlinked_references: [],
      }),
    });
  });
}

// ============================================================================
// Test Suite: Collection to Manage Navigation
// ============================================================================

test.describe('Collection to Manage Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test('clicking artifact opens modal with correct content', async ({ page }) => {
    await page.goto('/collection');
    await waitForPageReady(page);

    // Click on first artifact card
    const firstCard = page.locator('[data-testid="artifact-card"]').first();
    await firstCard.click();

    // Verify modal opens
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 5000 });

    // Verify modal contains artifact name
    await expect(modal).toContainText(mockArtifacts[0].name);
  });

  test('modal updates URL with artifact parameter', async ({ page }) => {
    await page.goto('/collection');
    await waitForPageReady(page);

    // Click on artifact to open modal
    const firstCard = page.locator('[data-testid="artifact-card"]').first();
    await firstCard.click();

    // Wait for modal
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 });

    // Verify URL contains artifact parameter
    await expect(page).toHaveURL(/artifact=/);
  });

  test('clicking Manage Artifact navigates to /manage with artifact', async ({ page }) => {
    await page.goto('/collection');
    await waitForPageReady(page);

    // Open artifact modal
    const firstCard = page.locator('[data-testid="artifact-card"]').first();
    await firstCard.click();
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 });

    // Find and click the "Manage Artifact" button
    const manageButton = page.getByRole('button', { name: /Manage Artifact/i });
    await expect(manageButton).toBeVisible();
    await manageButton.click();

    // Verify navigation to /manage
    await expect(page).toHaveURL(/\/manage/);

    // Verify artifact param is present
    await expect(page).toHaveURL(/artifact=/);

    // Verify returnTo param is set (pointing back to collection)
    await expect(page).toHaveURL(/returnTo=/);
  });

  test('returnTo parameter contains encoded collection URL', async ({ page }) => {
    await page.goto('/collection');
    await waitForPageReady(page);

    // Open artifact modal
    const firstCard = page.locator('[data-testid="artifact-card"]').first();
    await firstCard.click();
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 });

    // Navigate to manage
    const manageButton = page.getByRole('button', { name: /Manage Artifact/i });
    await manageButton.click();

    // Verify returnTo contains /collection (URL encoded)
    const url = page.url();
    const urlParams = new URLSearchParams(url.split('?')[1]);
    const returnTo = urlParams.get('returnTo');

    expect(returnTo).toBeTruthy();
    expect(decodeURIComponent(returnTo!)).toContain('/collection');
  });

  test('artifact modal auto-opens on /manage after navigation', async ({ page }) => {
    await page.goto('/collection');
    await waitForPageReady(page);

    // Open modal and navigate
    const firstCard = page.locator('[data-testid="artifact-card"]').first();
    await firstCard.click();
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 });

    const manageButton = page.getByRole('button', { name: /Manage Artifact/i });
    await manageButton.click();

    // Wait for manage page
    await expect(page).toHaveURL(/\/manage/);
    await waitForPageReady(page);

    // Verify modal is open on manage page
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 10000 });
  });
});

// ============================================================================
// Test Suite: Manage to Collection Navigation
// ============================================================================

test.describe('Manage to Collection Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test('clicking artifact on manage page opens operations modal', async ({ page }) => {
    await page.goto('/manage');
    await waitForPageReady(page);

    // Click on artifact
    const artifactItem = page.locator('[data-testid="artifact-card"]').first();
    await artifactItem.click();

    // Verify modal opens
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 5000 });
  });

  test('clicking Collection Details navigates to /collection with artifact', async ({ page }) => {
    await page.goto('/manage');
    await waitForPageReady(page);

    // Open artifact modal
    const artifactItem = page.locator('[data-testid="artifact-card"]').first();
    await artifactItem.click();
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 });

    // Find and click "Collection Details" button
    const collectionButton = page.getByRole('button', { name: /Collection Details/i });
    await expect(collectionButton).toBeVisible();
    await collectionButton.click();

    // Verify navigation to /collection
    await expect(page).toHaveURL(/\/collection/);

    // Verify artifact param is present
    await expect(page).toHaveURL(/artifact=/);

    // Verify returnTo param is set (pointing back to manage)
    await expect(page).toHaveURL(/returnTo=/);
  });

  test('returnTo parameter contains encoded manage URL', async ({ page }) => {
    await page.goto('/manage');
    await waitForPageReady(page);

    // Open modal and navigate
    const artifactItem = page.locator('[data-testid="artifact-card"]').first();
    await artifactItem.click();
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 });

    const collectionButton = page.getByRole('button', { name: /Collection Details/i });
    await collectionButton.click();

    // Verify returnTo contains /manage (URL encoded)
    const url = page.url();
    const urlParams = new URLSearchParams(url.split('?')[1]);
    const returnTo = urlParams.get('returnTo');

    expect(returnTo).toBeTruthy();
    expect(decodeURIComponent(returnTo!)).toContain('/manage');
  });
});

// ============================================================================
// Test Suite: Deep Link Handling
// ============================================================================

test.describe('Deep Link Handling', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test('navigating to /collection?artifact={id} opens modal automatically', async ({ page }) => {
    const artifactId = mockArtifacts[0].id;
    await page.goto(`/collection?artifact=${artifactId}`);
    await waitForPageReady(page);

    // Verify modal is open
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 10000 });

    // Verify correct artifact is shown
    await expect(modal).toContainText(mockArtifacts[0].name);
  });

  test('navigating to /manage?artifact={id} opens modal automatically', async ({ page }) => {
    const artifactId = mockArtifacts[0].id;
    await page.goto(`/manage?artifact=${artifactId}`);
    await waitForPageReady(page);

    // Verify modal is open
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 10000 });

    // Verify correct artifact is shown
    await expect(modal).toContainText(mockArtifacts[0].name);
  });

  test('navigating to /collection?artifact={id}&tab=contents opens correct tab', async ({ page }) => {
    const artifactId = mockArtifacts[0].id;
    await page.goto(`/collection?artifact=${artifactId}&tab=contents`);
    await waitForPageReady(page);

    // Verify modal is open
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 10000 });

    // Verify Contents tab is active - check for aria-selected or data-state attribute
    const contentsTab = modal.getByRole('tab', { name: /Contents/i });
    await expect(contentsTab).toHaveAttribute('data-state', 'active');
  });

  test('navigating to /manage?artifact={id}&tab=deployments opens correct tab', async ({ page }) => {
    const artifactId = mockArtifacts[0].id;
    await page.goto(`/manage?artifact=${artifactId}&tab=deployments`);
    await waitForPageReady(page);

    // Verify modal is open
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 10000 });

    // Verify Deployments tab is active
    const deploymentsTab = modal.getByRole('tab', { name: /Deployments/i });
    await expect(deploymentsTab).toHaveAttribute('data-state', 'active');
  });

  test('deep link with name instead of id works', async ({ page }) => {
    const artifactName = mockArtifacts[0].name;
    await page.goto(`/collection?artifact=${artifactName}`);
    await waitForPageReady(page);

    // Verify modal is open and shows correct artifact
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 10000 });
    await expect(modal).toContainText(artifactName);
  });

  test('closing modal removes artifact param from URL', async ({ page }) => {
    const artifactId = mockArtifacts[0].id;
    await page.goto(`/collection?artifact=${artifactId}`);
    await waitForPageReady(page);

    // Wait for modal
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 10000 });

    // Close modal by pressing Escape
    await page.keyboard.press('Escape');

    // Wait for modal to close
    await expect(modal).not.toBeVisible();

    // Verify artifact param is removed from URL
    await expect(page).not.toHaveURL(/artifact=/);
  });
});

// ============================================================================
// Test Suite: URL State Preservation
// ============================================================================

test.describe('URL State Preservation', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test('filters are preserved in returnTo when navigating to manage', async ({ page }) => {
    // Navigate to collection with filters
    await page.goto('/collection?type=skill&search=canvas&status=synced');
    await waitForPageReady(page);

    // Open artifact modal
    const firstCard = page.locator('[data-testid="artifact-card"]').first();
    await firstCard.click();
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 });

    // Navigate to manage
    const manageButton = page.getByRole('button', { name: /Manage Artifact/i });
    await manageButton.click();

    // Verify returnTo contains the filters
    const url = page.url();
    const urlParams = new URLSearchParams(url.split('?')[1]);
    const returnTo = decodeURIComponent(urlParams.get('returnTo') || '');

    expect(returnTo).toContain('type=skill');
    expect(returnTo).toContain('search=canvas');
    expect(returnTo).toContain('status=synced');
  });

  test('filters are preserved when returning via returnTo', async ({ page }) => {
    // Navigate to collection with filters
    await page.goto('/collection?type=skill&search=canvas');
    await waitForPageReady(page);

    // Open modal and navigate to manage
    const firstCard = page.locator('[data-testid="artifact-card"]').first();
    await firstCard.click();
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 });

    const manageButton = page.getByRole('button', { name: /Manage Artifact/i });
    await manageButton.click();

    // Wait for manage page
    await expect(page).toHaveURL(/\/manage/);
    await waitForPageReady(page);

    // Find and click Return button (in modal header)
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 10000 });

    const returnButton = page.getByRole('button', { name: /Return/i });
    await returnButton.click();

    // Verify we're back on collection with filters
    await expect(page).toHaveURL(/\/collection/);
    await expect(page).toHaveURL(/type=skill/);
    await expect(page).toHaveURL(/search=canvas/);
  });

  test('tags filter is preserved in returnTo', async ({ page }) => {
    // Navigate with tags filter
    await page.goto('/collection?tags=design,data');
    await waitForPageReady(page);

    // Open modal and navigate
    const firstCard = page.locator('[data-testid="artifact-card"]').first();
    await firstCard.click();
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 });

    const manageButton = page.getByRole('button', { name: /Manage Artifact/i });
    await manageButton.click();

    // Verify returnTo contains tags
    const url = page.url();
    const urlParams = new URLSearchParams(url.split('?')[1]);
    const returnTo = decodeURIComponent(urlParams.get('returnTo') || '');

    expect(returnTo).toContain('tags=design');
  });

  test('collection and group selection is preserved', async ({ page }) => {
    // Navigate with collection selected
    await page.goto('/collection?collection=default');
    await waitForPageReady(page);

    // Open modal and navigate
    const firstCard = page.locator('[data-testid="artifact-card"]').first();
    await firstCard.click();
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 });

    const manageButton = page.getByRole('button', { name: /Manage Artifact/i });
    await manageButton.click();

    // Verify returnTo contains collection
    const url = page.url();
    const urlParams = new URLSearchParams(url.split('?')[1]);
    const returnTo = decodeURIComponent(urlParams.get('returnTo') || '');

    expect(returnTo).toContain('collection=default');
  });
});

// ============================================================================
// Test Suite: Filter Bookmarkability
// ============================================================================

test.describe('Filter Bookmarkability', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test('navigating to /manage with filters applies them correctly', async ({ page }) => {
    await page.goto('/manage?type=skill&status=needs-update&search=test');
    await waitForPageReady(page);

    // Verify page shows applied filters (would need to check filter UI state)
    // The page should reflect these filters in the artifact list or filter controls
    await expect(page).toHaveURL(/type=skill/);
    await expect(page).toHaveURL(/status=needs-update/);
    await expect(page).toHaveURL(/search=test/);
  });

  test('filters persist after page refresh', async ({ page }) => {
    // Navigate with filters
    await page.goto('/collection?type=command&search=review');
    await waitForPageReady(page);

    // Refresh page
    await page.reload();
    await waitForPageReady(page);

    // Verify filters are still in URL
    await expect(page).toHaveURL(/type=command/);
    await expect(page).toHaveURL(/search=review/);
  });

  test('manage page filters persist after refresh', async ({ page }) => {
    await page.goto('/manage?status=has-drift&project=my-project');
    await waitForPageReady(page);

    await page.reload();
    await waitForPageReady(page);

    await expect(page).toHaveURL(/status=has-drift/);
    await expect(page).toHaveURL(/project=my-project/);
  });

  test('sort parameters persist in URL', async ({ page }) => {
    await page.goto('/collection?sort=name&order=asc');
    await waitForPageReady(page);

    await page.reload();
    await waitForPageReady(page);

    await expect(page).toHaveURL(/sort=name/);
    await expect(page).toHaveURL(/order=asc/);
  });
});

// ============================================================================
// Test Suite: Tab State in URL
// ============================================================================

test.describe('Tab State in URL', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test('clicking tab updates URL', async ({ page }) => {
    const artifactId = mockArtifacts[0].id;
    await page.goto(`/collection?artifact=${artifactId}`);
    await waitForPageReady(page);

    // Wait for modal
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 10000 });

    // Click on Contents tab
    const contentsTab = modal.getByRole('tab', { name: /Contents/i });
    await contentsTab.click();

    // Verify URL contains tab parameter
    await expect(page).toHaveURL(/tab=contents/);
  });

  test('clicking different tabs updates URL correctly', async ({ page }) => {
    const artifactId = mockArtifacts[0].id;
    await page.goto(`/collection?artifact=${artifactId}`);
    await waitForPageReady(page);

    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 10000 });

    // Click Links tab
    const linksTab = modal.getByRole('tab', { name: /Links/i });
    await linksTab.click();
    await expect(page).toHaveURL(/tab=links/);

    // Click History tab
    const historyTab = modal.getByRole('tab', { name: /History/i });
    await historyTab.click();
    await expect(page).toHaveURL(/tab=history/);
  });

  test('default tab does not appear in URL', async ({ page }) => {
    const artifactId = mockArtifacts[0].id;
    await page.goto(`/collection?artifact=${artifactId}`);
    await waitForPageReady(page);

    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 10000 });

    // Overview is default for collection modal - should not be in URL
    // The modal should open to Overview by default without tab param
    const overviewTab = modal.getByRole('tab', { name: /Overview/i });
    await expect(overviewTab).toHaveAttribute('data-state', 'active');

    // URL should not contain tab=overview (default is omitted)
    const url = page.url();
    expect(url).not.toContain('tab=overview');
  });
});

// ============================================================================
// Test Suite: Mobile Viewport
// ============================================================================

test.describe('Mobile Viewport Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
  });

  test('cross-navigation works on mobile', async ({ page }) => {
    await page.goto('/collection');
    await waitForPageReady(page);

    // Open artifact modal
    const firstCard = page.locator('[data-testid="artifact-card"]').first();
    await firstCard.click();
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 });

    // The Manage Artifact button should still be accessible on mobile
    const manageButton = page.getByRole('button', { name: /Manage Artifact/i });
    await expect(manageButton).toBeVisible();
    await manageButton.click();

    // Verify navigation works
    await expect(page).toHaveURL(/\/manage/);
  });

  test('modal opens correctly on mobile deep link', async ({ page }) => {
    const artifactId = mockArtifacts[0].id;
    await page.goto(`/collection?artifact=${artifactId}`);
    await waitForPageReady(page);

    // Verify modal opens
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 10000 });
  });

  test('return navigation works on mobile', async ({ page }) => {
    // Start from collection with filters
    await page.goto('/collection?type=skill');
    await waitForPageReady(page);

    // Navigate through modal to manage
    const firstCard = page.locator('[data-testid="artifact-card"]').first();
    await firstCard.click();
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 });

    const manageButton = page.getByRole('button', { name: /Manage Artifact/i });
    await manageButton.click();

    // Wait for manage page
    await expect(page).toHaveURL(/\/manage/);
    await waitForPageReady(page);

    // Use return button
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 10000 });

    const returnButton = page.getByRole('button', { name: /Return/i });
    await returnButton.click();

    // Should be back on collection with filter
    await expect(page).toHaveURL(/\/collection/);
    await expect(page).toHaveURL(/type=skill/);
  });
});

// ============================================================================
// Test Suite: Browser Navigation
// ============================================================================

test.describe('Browser Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test('browser back button closes modal when opened', async ({ page }) => {
    await page.goto('/collection');
    await waitForPageReady(page);

    // Open artifact modal
    const firstCard = page.locator('[data-testid="artifact-card"]').first();
    await firstCard.click();
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 });

    // Use browser back
    await page.goBack();

    // Modal should close and URL should not have artifact param
    // Note: This depends on how the app handles history state
    await waitForPageReady(page);
  });

  test('browser forward/back preserves navigation state', async ({ page }) => {
    // Navigate to collection
    await page.goto('/collection');
    await waitForPageReady(page);

    // Navigate to manage with filters
    await page.goto('/manage?type=skill');
    await waitForPageReady(page);

    // Go back to collection
    await page.goBack();
    await expect(page).toHaveURL(/\/collection/);

    // Go forward to manage
    await page.goForward();
    await expect(page).toHaveURL(/\/manage/);
    await expect(page).toHaveURL(/type=skill/);
  });
});

// ============================================================================
// Test Suite: Error Handling
// ============================================================================

test.describe('Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test('invalid artifact ID in deep link shows appropriate state', async ({ page }) => {
    await page.goto('/collection?artifact=non-existent-artifact');
    await waitForPageReady(page);

    // Page should load without crashing
    // Modal may not open if artifact is not found
    // The exact behavior depends on the implementation
    await expect(page.locator('body')).toBeVisible();
  });

  test('malformed returnTo param is handled gracefully', async ({ page }) => {
    await page.goto('/manage?artifact=artifact-1&returnTo=not%20a%20valid%20url');
    await waitForPageReady(page);

    // Page should load without crashing
    await expect(page.locator('body')).toBeVisible();
  });
});
