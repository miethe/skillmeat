/**
 * End-to-End Tests for Marketplace Source Indexing Toggle
 *
 * Tests the indexing toggle behavior in the add-source workflow across all three modes:
 * - 'off': Indexing is disabled, toggle should not be visible
 * - 'on': Indexing is globally enabled, toggle should not be visible
 * - 'opt_in': User can choose, toggle should be visible and unchecked by default
 *
 * TASK-5.3: E2E test for toggle behavior in all three modes
 */

import { test, expect, type Page } from '@playwright/test';
import { waitForPageLoad, expectModalOpen, expectModalClosed } from '../helpers/test-utils';

// ============================================================================
// Mock Data
// ============================================================================

const mockSource = {
  id: 'source-123',
  owner: 'anthropics',
  repo_name: 'anthropic-cookbook',
  ref: 'main',
  root_hint: '',
  repo_url: 'https://github.com/anthropics/anthropic-cookbook',
  trust_level: 'basic',
  visibility: 'public',
  scan_status: 'success',
  artifact_count: 15,
  last_sync_at: '2024-12-08T10:00:00Z',
  created_at: '2024-12-08T10:00:00Z',
  updated_at: '2024-12-08T10:00:00Z',
};

const mockSourcesList = {
  items: [mockSource],
  page_info: {
    has_next_page: false,
    has_previous_page: false,
    total_count: 1,
  },
};

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Setup all API mocks including indexing mode
 * Must be called BEFORE navigation to ensure mocks intercept requests
 */
async function setupAllApiMocks(page: Page, indexingMode: 'off' | 'on' | 'opt_in' = 'opt_in') {
  // Mock indexing mode settings endpoint - must be set up first as it's fetched on page load
  await page.route('**/api/v1/settings/indexing-mode', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ indexing_mode: indexingMode }),
    });
  });

  // Mock sources list (GET)
  await page.route('**/api/v1/marketplace/sources?*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockSourcesList),
    });
  });

  // Mock sources list without query params (GET)
  await page.route('**/api/v1/marketplace/sources', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockSourcesList),
      });
    } else if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify(mockSource),
      });
    } else {
      await route.continue();
    }
  });

  // Mock infer URL endpoint (for quick import)
  await page.route('**/api/v1/marketplace/sources/infer-url', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        repo_url: 'https://github.com/anthropics/anthropic-cookbook',
        ref: 'main',
        root_hint: '',
      }),
    });
  });
}

async function navigateToSourcesPage(page: Page) {
  await page.goto('/marketplace/sources');
  await waitForPageLoad(page);
}

async function openAddSourceModal(page: Page) {
  // Click Add Source button
  await page.getByRole('button', { name: /Add Source/i }).click();
  // Verify modal opens
  await expectModalOpen(page, '[role="dialog"]');
}

// ============================================================================
// Test Suite: Indexing Toggle in opt_in Mode (Default)
// ============================================================================

test.describe('Marketplace Source Indexing - opt_in Mode', () => {
  test.beforeEach(async ({ page }) => {
    await setupAllApiMocks(page, 'opt_in');
    await navigateToSourcesPage(page);
  });

  test('shows indexing toggle in add source modal', async ({ page }) => {
    await openAddSourceModal(page);

    // Verify toggle is visible with accessible name
    const toggle = page.getByRole('switch', { name: /Enable artifact search indexing/i });
    await expect(toggle).toBeVisible();

    // Also verify the label text is shown
    await expect(page.getByText('Enable artifact search indexing')).toBeVisible();
  });

  test('toggle defaults to unchecked in opt_in mode', async ({ page }) => {
    await openAddSourceModal(page);

    // Verify toggle is visible and unchecked by default
    const toggle = page.getByRole('switch', { name: /Enable artifact search indexing/i });
    await expect(toggle).toBeVisible();
    await expect(toggle).not.toBeChecked();
  });

  test('toggle can be enabled and disabled', async ({ page }) => {
    await openAddSourceModal(page);

    const toggle = page.getByRole('switch', { name: /Enable artifact search indexing/i });

    // Initially unchecked
    await expect(toggle).not.toBeChecked();

    // Click to enable
    await toggle.click();
    await expect(toggle).toBeChecked();

    // Click to disable
    await toggle.click();
    await expect(toggle).not.toBeChecked();
  });

  test('shows helper text explaining the toggle', async ({ page }) => {
    await openAddSourceModal(page);

    // Verify helper text is shown
    await expect(
      page.getByText('Enable full-text search across artifacts from this source')
    ).toBeVisible();
  });

  test('submits form with indexing enabled when toggle is checked', async ({ page }) => {
    // Track the request to verify indexing_enabled is sent
    let requestBody: Record<string, unknown> | null = null;
    await page.route('**/api/v1/marketplace/sources', async (route) => {
      if (route.request().method() === 'POST') {
        requestBody = route.request().postDataJSON();
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify(mockSource),
        });
      } else {
        await route.continue();
      }
    });

    await openAddSourceModal(page);

    // Fill in required fields
    await page.locator('#repo-url').fill('https://github.com/anthropics/anthropic-cookbook');

    // Enable indexing toggle
    const toggle = page.getByRole('switch', { name: /Enable artifact search indexing/i });
    await toggle.click();
    await expect(toggle).toBeChecked();

    // Submit form using the submit button in the form (not the quick import button)
    const submitButton = page.locator('form button[type="submit"]').filter({ hasText: 'Add Source' });
    await submitButton.click();

    // Wait for modal to close (indicates success)
    await expectModalClosed(page, '[role="dialog"]');

    // Verify indexing_enabled was sent in request
    expect(requestBody).toBeTruthy();
    expect(requestBody!.indexing_enabled).toBe(true);
  });

  test('submits form with indexing disabled when toggle is unchecked', async ({ page }) => {
    // Track the request to verify indexing_enabled is sent
    let requestBody: Record<string, unknown> | null = null;
    await page.route('**/api/v1/marketplace/sources', async (route) => {
      if (route.request().method() === 'POST') {
        requestBody = route.request().postDataJSON();
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify(mockSource),
        });
      } else {
        await route.continue();
      }
    });

    await openAddSourceModal(page);

    // Fill in required fields
    await page.locator('#repo-url').fill('https://github.com/anthropics/anthropic-cookbook');

    // Ensure toggle is unchecked (default)
    const toggle = page.getByRole('switch', { name: /Enable artifact search indexing/i });
    await expect(toggle).not.toBeChecked();

    // Submit form
    const submitButton = page.locator('form button[type="submit"]').filter({ hasText: 'Add Source' });
    await submitButton.click();

    // Wait for modal to close
    await expectModalClosed(page, '[role="dialog"]');

    // Verify indexing_enabled was sent as false
    expect(requestBody).toBeTruthy();
    expect(requestBody!.indexing_enabled).toBe(false);
  });
});

// ============================================================================
// Test Suite: Indexing Toggle in 'off' Mode
// ============================================================================

test.describe('Marketplace Source Indexing - off Mode', () => {
  test.beforeEach(async ({ page }) => {
    await setupAllApiMocks(page, 'off');
    await navigateToSourcesPage(page);
  });

  test('hides indexing toggle when mode is off', async ({ page }) => {
    await openAddSourceModal(page);

    // Verify toggle is NOT visible
    const toggle = page.getByRole('switch', { name: /Enable artifact search indexing/i });
    await expect(toggle).not.toBeVisible();

    // Also verify the label text is not shown
    await expect(page.getByText('Enable artifact search indexing')).not.toBeVisible();
  });

  test('does not include indexing_enabled in submission when mode is off', async ({ page }) => {
    // Track the request to verify indexing_enabled is NOT sent
    let requestBody: Record<string, unknown> | null = null;
    await page.route('**/api/v1/marketplace/sources', async (route) => {
      if (route.request().method() === 'POST') {
        requestBody = route.request().postDataJSON();
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify(mockSource),
        });
      } else {
        await route.continue();
      }
    });

    await openAddSourceModal(page);

    // Fill in required fields
    await page.locator('#repo-url').fill('https://github.com/anthropics/anthropic-cookbook');

    // Submit form
    const submitButton = page.locator('form button[type="submit"]').filter({ hasText: 'Add Source' });
    await submitButton.click();

    // Wait for modal to close
    await expectModalClosed(page, '[role="dialog"]');

    // Verify indexing_enabled was NOT sent in request
    expect(requestBody).toBeTruthy();
    expect(requestBody!.indexing_enabled).toBeUndefined();
  });
});

// ============================================================================
// Test Suite: Indexing Toggle in 'on' Mode (Globally Enabled)
// ============================================================================

test.describe('Marketplace Source Indexing - on Mode', () => {
  test.beforeEach(async ({ page }) => {
    await setupAllApiMocks(page, 'on');
    await navigateToSourcesPage(page);
  });

  test('hides indexing toggle when mode is on (globally enabled)', async ({ page }) => {
    await openAddSourceModal(page);

    // Verify toggle is NOT visible (no user choice needed when globally enabled)
    const toggle = page.getByRole('switch', { name: /Enable artifact search indexing/i });
    await expect(toggle).not.toBeVisible();

    // Also verify the label text is not shown
    await expect(page.getByText('Enable artifact search indexing')).not.toBeVisible();
  });

  test('does not include indexing_enabled in submission when mode is on', async ({ page }) => {
    // Track the request to verify indexing_enabled is NOT sent
    let requestBody: Record<string, unknown> | null = null;
    await page.route('**/api/v1/marketplace/sources', async (route) => {
      if (route.request().method() === 'POST') {
        requestBody = route.request().postDataJSON();
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify(mockSource),
        });
      } else {
        await route.continue();
      }
    });

    await openAddSourceModal(page);

    // Fill in required fields
    await page.locator('#repo-url').fill('https://github.com/anthropics/anthropic-cookbook');

    // Submit form
    const submitButton = page.locator('form button[type="submit"]').filter({ hasText: 'Add Source' });
    await submitButton.click();

    // Wait for modal to close
    await expectModalClosed(page, '[role="dialog"]');

    // Verify indexing_enabled was NOT sent in request (server handles it automatically)
    expect(requestBody).toBeTruthy();
    expect(requestBody!.indexing_enabled).toBeUndefined();
  });
});

// ============================================================================
// Test Suite: Modal State Reset
// ============================================================================

test.describe('Indexing Toggle State Reset', () => {
  test.beforeEach(async ({ page }) => {
    await setupAllApiMocks(page, 'opt_in');
    await navigateToSourcesPage(page);
  });

  test('toggle resets to unchecked when modal is reopened', async ({ page }) => {
    await openAddSourceModal(page);

    // Enable the toggle
    const toggle = page.getByRole('switch', { name: /Enable artifact search indexing/i });
    await toggle.click();
    await expect(toggle).toBeChecked();

    // Close the modal
    await page.getByRole('button', { name: 'Cancel' }).click();
    await expectModalClosed(page, '[role="dialog"]');

    // Reopen the modal
    await openAddSourceModal(page);

    // Verify toggle is reset to unchecked
    const toggleAfterReopen = page.getByRole('switch', { name: /Enable artifact search indexing/i });
    await expect(toggleAfterReopen).not.toBeChecked();
  });

  test('toggle resets after successful form submission', async ({ page }) => {
    // Setup route to track submissions
    await page.route('**/api/v1/marketplace/sources', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify(mockSource),
        });
      } else {
        await route.continue();
      }
    });

    await openAddSourceModal(page);

    // Fill form and enable toggle
    await page.locator('#repo-url').fill('https://github.com/anthropics/anthropic-cookbook');
    const toggle = page.getByRole('switch', { name: /Enable artifact search indexing/i });
    await toggle.click();
    await expect(toggle).toBeChecked();

    // Submit form
    const submitButton = page.locator('form button[type="submit"]').filter({ hasText: 'Add Source' });
    await submitButton.click();

    // Wait for modal to close (success)
    await expectModalClosed(page, '[role="dialog"]');

    // Reopen the modal
    await openAddSourceModal(page);

    // Verify toggle is reset to unchecked
    const toggleAfterReopen = page.getByRole('switch', { name: /Enable artifact search indexing/i });
    await expect(toggleAfterReopen).not.toBeChecked();
  });
});

// ============================================================================
// Test Suite: Accessibility
// ============================================================================

test.describe('Indexing Toggle Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await setupAllApiMocks(page, 'opt_in');
    await navigateToSourcesPage(page);
  });

  test('toggle has proper aria-label', async ({ page }) => {
    await openAddSourceModal(page);

    const toggle = page.getByRole('switch', { name: /Enable artifact search indexing/i });
    await expect(toggle).toBeVisible();
    await expect(toggle).toHaveAttribute('aria-label', 'Enable artifact search indexing');
  });

  test('toggle is keyboard accessible', async ({ page }) => {
    await openAddSourceModal(page);

    const toggle = page.getByRole('switch', { name: /Enable artifact search indexing/i });

    // Focus the toggle using keyboard navigation
    await toggle.focus();
    await expect(toggle).toBeFocused();

    // Toggle with Space key
    await page.keyboard.press('Space');
    await expect(toggle).toBeChecked();

    // Toggle off with Space key
    await page.keyboard.press('Space');
    await expect(toggle).not.toBeChecked();
  });
});
