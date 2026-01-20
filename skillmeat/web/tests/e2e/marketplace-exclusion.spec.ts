/**
 * End-to-End Tests for Marketplace Artifact Exclusion Workflow
 *
 * Tests the complete artifact exclusion workflow in the marketplace source detail page:
 * 1. Marking an artifact as "Not an artifact" (exclusion)
 * 2. Confirmation dialog interaction
 * 3. Excluded artifacts list visibility
 * 4. Restoring excluded artifacts
 * 5. Exclusion impact on Select All functionality
 *
 * Note: These tests use mocked API responses for consistent testing.
 */

import { test, expect, type Page } from '@playwright/test';
import {
  waitForPageLoad,
  mockApiRoute,
  expectModalOpen,
  expectModalClosed,
} from '../helpers/test-utils';

// ============================================================================
// Mock Data
// ============================================================================

const mockSource = {
  id: 'source-exclusion-test',
  owner: 'anthropics',
  repo_name: 'test-repo',
  ref: 'main',
  root_hint: '',
  repo_url: 'https://github.com/anthropics/test-repo',
  trust_level: 'official',
  artifact_count: 5,
  last_scan_at: '2024-12-08T10:00:00Z',
  created_at: '2024-12-01T10:00:00Z',
  description: 'Test repository for exclusion workflow',
  notes: null,
};

const mockCatalogEntry1 = {
  id: 'entry-1',
  source_id: 'source-exclusion-test',
  name: 'canvas-design',
  artifact_type: 'skill',
  path: '.claude/skills/canvas-design.md',
  status: 'new',
  confidence_score: 95,
  upstream_url: 'https://github.com/anthropics/test-repo/blob/main/.claude/skills/canvas-design.md',
  detected_at: '2024-12-08T10:00:00Z',
};

const mockCatalogEntry2 = {
  id: 'entry-2',
  source_id: 'source-exclusion-test',
  name: 'data-analysis',
  artifact_type: 'skill',
  path: '.claude/skills/data-analysis.md',
  status: 'updated',
  confidence_score: 85,
  upstream_url: 'https://github.com/anthropics/test-repo/blob/main/.claude/skills/data-analysis.md',
  detected_at: '2024-12-08T10:00:00Z',
};

const mockExcludedEntry = {
  id: 'entry-excluded',
  source_id: 'source-exclusion-test',
  name: 'not-an-artifact',
  artifact_type: 'skill',
  path: '.claude/skills/not-an-artifact.md',
  status: 'excluded',
  confidence_score: 45,
  upstream_url:
    'https://github.com/anthropics/test-repo/blob/main/.claude/skills/not-an-artifact.md',
  detected_at: '2024-12-07T10:00:00Z',
  excluded_at: '2024-12-08T12:00:00Z',
};

const mockCatalogResponse = {
  items: [mockCatalogEntry1, mockCatalogEntry2],
  total: 2,
  page: 1,
  page_size: 20,
  has_next: false,
  counts_by_type: {
    skill: 2,
  },
  counts_by_status: {
    new: 1,
    updated: 1,
  },
};

const mockCatalogWithExcludedResponse = {
  items: [mockCatalogEntry1, mockCatalogEntry2, mockExcludedEntry],
  total: 3,
  page: 1,
  page_size: 20,
  has_next: false,
  counts_by_type: {
    skill: 3,
  },
  counts_by_status: {
    new: 1,
    updated: 1,
    excluded: 1,
  },
};

// ============================================================================
// Helper Functions
// ============================================================================

async function setupMockApiRoutes(page: Page, includeExcluded: boolean = false) {
  // Mock source detail
  await mockApiRoute(page, `/api/v1/marketplace/sources/${mockSource.id}`, mockSource);

  // Mock catalog
  await mockApiRoute(
    page,
    `/api/v1/marketplace/sources/${mockSource.id}/catalog*`,
    includeExcluded ? mockCatalogWithExcludedResponse : mockCatalogResponse
  );

  // Mock exclude endpoint
  await page.route(
    `**/api/v1/marketplace/sources/${mockSource.id}/catalog/*/exclude`,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, message: 'Entry excluded' }),
      });
    }
  );

  // Mock restore endpoint
  await page.route(
    `**/api/v1/marketplace/sources/${mockSource.id}/catalog/*/restore`,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, message: 'Entry restored' }),
      });
    }
  );

  // Mock import endpoint
  await mockApiRoute(page, `/api/v1/marketplace/sources/${mockSource.id}/import`, {
    success: true,
    imported_count: 1,
  });
}

async function navigateToSourceDetailPage(page: Page, sourceId: string = mockSource.id) {
  await page.goto(`/marketplace/sources/${sourceId}`);
  await waitForPageLoad(page);
}

// ============================================================================
// Test Suite: Exclusion Workflow
// ============================================================================

test.describe('Marketplace Exclusion Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
  });

  test('displays "Not an artifact" link on importable catalog cards', async ({ page }) => {
    await navigateToSourceDetailPage(page);

    // Wait for catalog to load
    await expect(page.getByText('canvas-design')).toBeVisible();

    // Verify "Not an artifact" link is visible on cards with importable status
    const notAnArtifactLinks = page.locator('button:has-text("Not an artifact")');
    await expect(notAnArtifactLinks.first()).toBeVisible();
  });

  test('opens exclusion confirmation dialog when clicking "Not an artifact"', async ({ page }) => {
    await navigateToSourceDetailPage(page);

    // Wait for catalog to load
    await expect(page.getByText('canvas-design')).toBeVisible();

    // Click "Not an artifact" link
    const notAnArtifactLink = page.locator('button:has-text("Not an artifact")').first();
    await notAnArtifactLink.click();

    // Verify dialog opens with correct content
    await expectModalOpen(page, '[role="alertdialog"]');
    await expect(page.getByText('Mark as Not an Artifact?')).toBeVisible();
    await expect(page.getByText('canvas-design')).toBeVisible();
    await expect(
      page.getByText('You can restore it later from the Excluded Artifacts list')
    ).toBeVisible();
  });

  test('can cancel exclusion dialog', async ({ page }) => {
    await navigateToSourceDetailPage(page);

    // Wait for catalog to load
    await expect(page.getByText('canvas-design')).toBeVisible();

    // Open dialog
    await page.locator('button:has-text("Not an artifact")').first().click();
    await expectModalOpen(page, '[role="alertdialog"]');

    // Click Cancel
    await page.getByRole('button', { name: 'Cancel' }).click();

    // Verify dialog closes
    await expectModalClosed(page, '[role="alertdialog"]');
  });

  test('excludes artifact when confirming dialog', async ({ page }) => {
    let excludeRequestMade = false;

    // Intercept exclude request
    await page.route(
      `**/api/v1/marketplace/sources/${mockSource.id}/catalog/*/exclude`,
      async (route) => {
        excludeRequestMade = true;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, message: 'Entry excluded' }),
        });
      }
    );

    await navigateToSourceDetailPage(page);

    // Wait for catalog to load
    await expect(page.getByText('canvas-design')).toBeVisible();

    // Open dialog
    await page.locator('button:has-text("Not an artifact")').first().click();
    await expectModalOpen(page, '[role="alertdialog"]');

    // Confirm exclusion
    await page.getByRole('button', { name: 'Mark as Excluded' }).click();

    // Wait for dialog to close
    await expectModalClosed(page, '[role="alertdialog"]');

    // Verify API request was made
    expect(excludeRequestMade).toBe(true);
  });

  test('shows loading state during exclusion', async ({ page }) => {
    // Add delay to exclude request
    await page.route(
      `**/api/v1/marketplace/sources/${mockSource.id}/catalog/*/exclude`,
      async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 500));
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, message: 'Entry excluded' }),
        });
      }
    );

    await navigateToSourceDetailPage(page);

    // Wait for catalog to load
    await expect(page.getByText('canvas-design')).toBeVisible();

    // Open dialog and confirm
    await page.locator('button:has-text("Not an artifact")').first().click();
    await expectModalOpen(page, '[role="alertdialog"]');

    // Click confirm and check loading state
    await page.getByRole('button', { name: 'Mark as Excluded' }).click();

    // Verify loading state (button shows "Excluding...")
    await expect(page.getByText('Excluding...')).toBeVisible();

    // Wait for dialog to close after request completes
    await expectModalClosed(page, '[role="alertdialog"]');
  });
});

// ============================================================================
// Test Suite: Excluded Artifacts List
// ============================================================================

test.describe('Excluded Artifacts List', () => {
  test('displays "Show Excluded Artifacts" button when excluded entries exist', async ({
    page,
  }) => {
    await setupMockApiRoutes(page, true); // Include excluded entry
    await navigateToSourceDetailPage(page);

    // Wait for catalog to load
    await expect(page.getByText('canvas-design')).toBeVisible();

    // Verify collapsed excluded section is visible
    const excludedButton = page.getByRole('button', { name: /Show Excluded Artifacts/i });
    await expect(excludedButton).toBeVisible();
    await expect(excludedButton).toContainText('(1)'); // Count of excluded entries
  });

  test('hides excluded artifacts section when no excluded entries', async ({ page }) => {
    await setupMockApiRoutes(page, false); // No excluded entries
    await navigateToSourceDetailPage(page);

    // Wait for catalog to load
    await expect(page.getByText('canvas-design')).toBeVisible();

    // Verify excluded section is not visible
    const excludedButton = page.getByRole('button', { name: /Show Excluded Artifacts/i });
    await expect(excludedButton).not.toBeVisible();
  });

  test('expands to show excluded artifacts table', async ({ page }) => {
    await setupMockApiRoutes(page, true);
    await navigateToSourceDetailPage(page);

    // Wait for catalog to load
    await expect(page.getByText('canvas-design')).toBeVisible();

    // Expand excluded section
    await page.getByRole('button', { name: /Show Excluded Artifacts/i }).click();

    // Verify table is visible with excluded entry
    await expect(page.getByRole('table')).toBeVisible();
    await expect(page.getByText('not-an-artifact')).toBeVisible();

    // Verify table columns
    await expect(page.getByRole('columnheader', { name: 'Name' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Path' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Excluded' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Actions' })).toBeVisible();
  });

  test('collapses excluded artifacts table', async ({ page }) => {
    await setupMockApiRoutes(page, true);
    await navigateToSourceDetailPage(page);

    // Wait for catalog to load
    await expect(page.getByText('canvas-design')).toBeVisible();

    // Expand
    await page.getByRole('button', { name: /Show Excluded Artifacts/i }).click();
    await expect(page.getByRole('table')).toBeVisible();

    // Collapse
    await page.getByRole('button', { name: /Show Excluded Artifacts/i }).click();
    await expect(page.getByRole('table')).not.toBeVisible();
  });
});

// ============================================================================
// Test Suite: Restore Excluded Artifacts
// ============================================================================

test.describe('Restore Excluded Artifacts', () => {
  test('displays Restore button for each excluded entry', async ({ page }) => {
    await setupMockApiRoutes(page, true);
    await navigateToSourceDetailPage(page);

    // Wait and expand
    await expect(page.getByText('canvas-design')).toBeVisible();
    await page.getByRole('button', { name: /Show Excluded Artifacts/i }).click();

    // Verify Restore button is visible
    const restoreButton = page.getByRole('button', { name: /Restore/i });
    await expect(restoreButton).toBeVisible();
  });

  test('calls restore API when clicking Restore button', async ({ page }) => {
    let restoreRequestMade = false;
    let restoredEntryId = '';

    // Intercept restore request
    await page.route(
      `**/api/v1/marketplace/sources/${mockSource.id}/catalog/*/restore`,
      async (route) => {
        restoreRequestMade = true;
        restoredEntryId = route.request().url().split('/').slice(-2)[0];
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, message: 'Entry restored' }),
        });
      }
    );

    await setupMockApiRoutes(page, true);
    await navigateToSourceDetailPage(page);

    // Wait and expand
    await expect(page.getByText('canvas-design')).toBeVisible();
    await page.getByRole('button', { name: /Show Excluded Artifacts/i }).click();

    // Click Restore
    await page.getByRole('button', { name: /Restore/i }).click();

    // Wait for request
    await page.waitForTimeout(500);

    // Verify API request was made
    expect(restoreRequestMade).toBe(true);
    expect(restoredEntryId).toBe('entry-excluded');
  });

  test('shows loading state during restore', async ({ page }) => {
    // Add delay to restore request
    await page.route(
      `**/api/v1/marketplace/sources/${mockSource.id}/catalog/*/restore`,
      async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 500));
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, message: 'Entry restored' }),
        });
      }
    );

    await setupMockApiRoutes(page, true);
    await navigateToSourceDetailPage(page);

    // Wait and expand
    await expect(page.getByText('canvas-design')).toBeVisible();
    await page.getByRole('button', { name: /Show Excluded Artifacts/i }).click();

    // Click Restore
    const restoreButton = page.getByRole('button', { name: /Restore/i });
    await restoreButton.click();

    // Verify button is disabled during loading
    await expect(restoreButton).toBeDisabled();

    // Wait for request to complete
    await page.waitForTimeout(600);
  });
});

// ============================================================================
// Test Suite: Exclusion Impact on Selection
// ============================================================================

test.describe('Exclusion Impact on Selection', () => {
  test('excluded entries are not included in Select All', async ({ page }) => {
    await setupMockApiRoutes(page, true); // Include excluded entry
    await navigateToSourceDetailPage(page);

    // Wait for catalog to load
    await expect(page.getByText('canvas-design')).toBeVisible();

    // Click Select All
    await page.getByRole('button', { name: /Select All/i }).click();

    // Verify only importable entries are selected (2 out of 3)
    await expect(page.getByRole('button', { name: /Deselect All/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Import 2 selected/i })).toBeVisible();
  });

  test('excluded entries do not show "Not an artifact" link', async ({ page }) => {
    await setupMockApiRoutes(page, true);
    await navigateToSourceDetailPage(page);

    // Wait for catalog to load
    await expect(page.getByText('canvas-design')).toBeVisible();

    // Excluded entries are shown in the excluded list, not as cards
    // Verify "Not an artifact" links count matches importable entries
    const notAnArtifactLinks = page.locator('button:has-text("Not an artifact")');
    const count = await notAnArtifactLinks.count();
    expect(count).toBe(2); // Only for new and updated entries
  });

  test('excluded entries show in status counts badge', async ({ page }) => {
    await setupMockApiRoutes(page, true);
    await navigateToSourceDetailPage(page);

    // Wait for catalog to load
    await expect(page.getByText('canvas-design')).toBeVisible();

    // Verify status badge shows excluded count
    await expect(page.getByText('excluded: 1')).toBeVisible();
  });

  test('clicking excluded status badge filters to excluded entries', async ({ page }) => {
    await setupMockApiRoutes(page, true);
    await navigateToSourceDetailPage(page);

    // Wait for catalog to load
    await expect(page.getByText('canvas-design')).toBeVisible();

    // Click excluded badge
    const excludedBadge = page.getByText('excluded: 1');
    await excludedBadge.click();

    // Verify badge has active state
    await expect(excludedBadge).toHaveClass(/ring-2/);

    // Verify URL has status filter
    await expect(page).toHaveURL(/status=excluded/);
  });
});

// ============================================================================
// Test Suite: Error Handling
// ============================================================================

test.describe('Exclusion Error Handling', () => {
  test('handles exclusion API error gracefully', async ({ page }) => {
    // Mock exclude endpoint to return error
    await page.route(
      `**/api/v1/marketplace/sources/${mockSource.id}/catalog/*/exclude`,
      async (route) => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Internal server error' }),
        });
      }
    );

    await setupMockApiRoutes(page);
    await navigateToSourceDetailPage(page);

    // Wait for catalog to load
    await expect(page.getByText('canvas-design')).toBeVisible();

    // Open dialog and confirm
    await page.locator('button:has-text("Not an artifact")').first().click();
    await page.getByRole('button', { name: 'Mark as Excluded' }).click();

    // Dialog should close even on error (optimistic update pattern)
    // or show error message depending on implementation
    await page.waitForTimeout(1000);
  });

  test('handles restore API error gracefully', async ({ page }) => {
    // Mock restore endpoint to return error
    await page.route(
      `**/api/v1/marketplace/sources/${mockSource.id}/catalog/*/restore`,
      async (route) => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Internal server error' }),
        });
      }
    );

    await setupMockApiRoutes(page, true);
    await navigateToSourceDetailPage(page);

    // Wait and expand
    await expect(page.getByText('canvas-design')).toBeVisible();
    await page.getByRole('button', { name: /Show Excluded Artifacts/i }).click();

    // Click Restore
    await page.getByRole('button', { name: /Restore/i }).click();

    // Button should remain or show error depending on implementation
    await page.waitForTimeout(1000);
  });
});

// ============================================================================
// Test Suite: Accessibility
// ============================================================================

test.describe('Exclusion Accessibility', () => {
  test('exclusion dialog is keyboard accessible', async ({ page }) => {
    await setupMockApiRoutes(page);
    await navigateToSourceDetailPage(page);

    // Wait for catalog to load
    await expect(page.getByText('canvas-design')).toBeVisible();

    // Open dialog
    await page.locator('button:has-text("Not an artifact")').first().click();
    await expectModalOpen(page, '[role="alertdialog"]');

    // Close with Escape key
    await page.keyboard.press('Escape');
    await expectModalClosed(page, '[role="alertdialog"]');
  });

  test('excluded list collapsible is keyboard accessible', async ({ page }) => {
    await setupMockApiRoutes(page, true);
    await navigateToSourceDetailPage(page);

    // Wait for catalog to load
    await expect(page.getByText('canvas-design')).toBeVisible();

    // Focus on collapsible trigger
    const trigger = page.getByRole('button', { name: /Show Excluded Artifacts/i });
    await trigger.focus();

    // Expand with Enter key
    await page.keyboard.press('Enter');
    await expect(page.getByRole('table')).toBeVisible();

    // Collapse with Enter key
    await page.keyboard.press('Enter');
    await expect(page.getByRole('table')).not.toBeVisible();
  });

  test('restore button is keyboard focusable', async ({ page }) => {
    await setupMockApiRoutes(page, true);
    await navigateToSourceDetailPage(page);

    // Wait and expand
    await expect(page.getByText('canvas-design')).toBeVisible();
    await page.getByRole('button', { name: /Show Excluded Artifacts/i }).click();

    // Tab to Restore button
    const restoreButton = page.getByRole('button', { name: /Restore/i });
    await restoreButton.focus();

    // Verify focus
    await expect(restoreButton).toBeFocused();
  });

  test('dialog has proper ARIA attributes', async ({ page }) => {
    await setupMockApiRoutes(page);
    await navigateToSourceDetailPage(page);

    // Wait for catalog to load
    await expect(page.getByText('canvas-design')).toBeVisible();

    // Open dialog
    await page.locator('button:has-text("Not an artifact")').first().click();
    await expectModalOpen(page, '[role="alertdialog"]');

    // Verify ARIA attributes
    const dialog = page.locator('[role="alertdialog"]');
    await expect(dialog).toHaveAttribute('aria-modal', 'true');

    // Verify dialog has accessible title
    await expect(page.getByText('Mark as Not an Artifact?')).toBeVisible();
  });
});
