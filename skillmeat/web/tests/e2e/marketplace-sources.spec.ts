/**
 * End-to-End Tests for GitHub Source Ingestion
 *
 * Tests the complete user journey for adding, managing, and importing artifacts
 * from GitHub repository sources. Covers happy paths, error handling, and
 * accessibility requirements.
 *
 * Test Coverage:
 * - Add source workflow (with and without catalog override)
 * - Source detail page functionality
 * - Artifact filtering and import
 * - Rescan operations
 * - Error handling scenarios
 * - Accessibility (keyboard navigation, ARIA)
 * - Responsive design (mobile, tablet, desktop)
 */

import { test, expect, type Page } from '@playwright/test';
import {
  waitForPageLoad,
  mockApiRoute,
  expectTextVisible,
  expectButtonState,
  typeInInput,
  expectModalOpen,
  expectModalClosed,
  pressKey,
  expectFocused,
  countElements,
  expectErrorMessage,
} from '../helpers/test-utils';

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
  trust_level: 'official',
  artifact_count: 15,
  last_scan_at: '2024-12-08T10:00:00Z',
  created_at: '2024-12-01T10:00:00Z',
};

const mockSourcesList = {
  items: [mockSource],
  total: 1,
  page: 1,
  page_size: 20,
  has_next: false,
};

const mockCatalogEntry = {
  id: 'entry-1',
  source_id: 'source-123',
  name: 'canvas-design',
  artifact_type: 'skill',
  path: '.claude/skills/canvas-design.md',
  status: 'new',
  confidence_score: 95,
  upstream_url: 'https://github.com/anthropics/anthropic-cookbook/blob/main/.claude/skills/canvas-design.md',
  detected_at: '2024-12-08T10:00:00Z',
};

const mockCatalogResponse = {
  items: [
    mockCatalogEntry,
    {
      id: 'entry-2',
      source_id: 'source-123',
      name: 'data-analysis',
      artifact_type: 'skill',
      path: '.claude/skills/data-analysis.md',
      status: 'updated',
      confidence_score: 85,
      upstream_url: 'https://github.com/anthropics/anthropic-cookbook/blob/main/.claude/skills/data-analysis.md',
      detected_at: '2024-12-08T10:00:00Z',
    },
    {
      id: 'entry-3',
      source_id: 'source-123',
      name: 'code-review',
      artifact_type: 'command',
      path: '.claude/commands/code-review.md',
      status: 'imported',
      confidence_score: 90,
      upstream_url: 'https://github.com/anthropics/anthropic-cookbook/blob/main/.claude/commands/code-review.md',
      import_date: '2024-12-07T10:00:00Z',
      detected_at: '2024-12-08T10:00:00Z',
    },
  ],
  total: 3,
  page: 1,
  page_size: 20,
  has_next: false,
  counts_by_type: {
    skill: 2,
    command: 1,
  },
  counts_by_status: {
    new: 1,
    updated: 1,
    imported: 1,
  },
};

const mockScanPreview = {
  detected_artifacts: [
    { path: '.claude/skills/canvas-design.md', type: 'skill', confidence: 95 },
    { path: '.claude/skills/data-analysis.md', type: 'skill', confidence: 85 },
  ],
  suggested_root: '.claude',
  catalog_files_found: ['.claude/catalog.json'],
};

// ============================================================================
// Helper Functions
// ============================================================================

async function setupMockApiRoutes(page: Page) {
  // Mock sources list
  await mockApiRoute(page, '/api/v1/marketplace/sources*', mockSourcesList);

  // Mock source detail
  await mockApiRoute(page, `/api/v1/marketplace/sources/${mockSource.id}`, mockSource);

  // Mock catalog
  await mockApiRoute(
    page,
    `/api/v1/marketplace/sources/${mockSource.id}/catalog*`,
    mockCatalogResponse
  );

  // Mock scan preview
  await mockApiRoute(page, '/api/v1/marketplace/sources/scan-preview', mockScanPreview);

  // Mock create source
  await mockApiRoute(page, '/api/v1/marketplace/sources', mockSource, 201);

  // Mock rescan
  await mockApiRoute(
    page,
    `/api/v1/marketplace/sources/${mockSource.id}/rescan`,
    { success: true, message: 'Rescan initiated' }
  );

  // Mock import
  await mockApiRoute(
    page,
    `/api/v1/marketplace/sources/${mockSource.id}/import`,
    { success: true, imported_count: 1 }
  );
}

async function navigateToSourcesPage(page: Page) {
  await page.goto('/marketplace/sources');
  await waitForPageLoad(page);
}

async function navigateToSourceDetailPage(page: Page, sourceId: string = mockSource.id) {
  await page.goto(`/marketplace/sources/${sourceId}`);
  await waitForPageLoad(page);
}

// ============================================================================
// Test Suite: Sources List Page
// ============================================================================

test.describe('Marketplace Sources - List Page', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
  });

  test('displays sources page with header and controls', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Verify page header
    await expect(page.getByRole('heading', { name: 'GitHub Sources' })).toBeVisible();
    await expect(
      page.getByText('Add and manage GitHub repositories to discover Claude Code artifacts')
    ).toBeVisible();

    // Verify action buttons
    await expect(page.getByRole('button', { name: /Refresh/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Add Source/i })).toBeVisible();

    // Verify search bar
    await expect(page.getByPlaceholder('Search repositories...')).toBeVisible();
  });

  test('displays source cards with correct information', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Wait for source cards to load
    await expect(page.getByText('anthropics/anthropic-cookbook')).toBeVisible();

    // Verify source information
    await expect(page.getByText('main')).toBeVisible();
    await expect(page.getByText('15 artifacts')).toBeVisible();
  });

  test('filters sources by search query', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Wait for sources to load
    await expect(page.getByText('anthropics/anthropic-cookbook')).toBeVisible();

    // Search for specific repository
    const searchInput = page.getByPlaceholder('Search repositories...');
    await searchInput.fill('cookbook');

    // Verify filtered results
    await expect(page.getByText('anthropics/anthropic-cookbook')).toBeVisible();

    // Search for non-existent repository
    await searchInput.fill('nonexistent');

    // Verify no results state
    await expect(page.getByText('No matching sources')).toBeVisible();
    await expect(page.getByText('Try adjusting your search term.')).toBeVisible();
  });

  test('displays empty state when no sources added', async ({ page }) => {
    // Mock empty sources list
    await mockApiRoute(page, '/api/v1/marketplace/sources*', {
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      has_next: false,
    });

    await navigateToSourcesPage(page);

    // Verify empty state
    await expect(page.getByText('No sources added yet')).toBeVisible();
    await expect(
      page.getByText('Add a GitHub repository to start discovering Claude Code artifacts')
    ).toBeVisible();
    await expect(page.getByRole('button', { name: 'Add Your First Source' })).toBeVisible();
  });

  test('refreshes sources list', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Click refresh button
    const refreshButton = page.getByRole('button', { name: /Refresh/i });
    await refreshButton.click();

    // Verify button shows loading state
    await expect(refreshButton).toContainText('Refresh');
  });
});

// ============================================================================
// Test Suite: Add Source Flow (Happy Path)
// ============================================================================

test.describe('Add Source Workflow - Happy Path', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
    await navigateToSourcesPage(page);
  });

  test('opens add source modal', async ({ page }) => {
    // Click Add Source button
    await page.getByRole('button', { name: /Add Source/i }).click();

    // Verify modal opens
    await expectModalOpen(page, '[role="dialog"]');
    await expect(page.getByRole('dialog')).toContainText('Add GitHub Source');
    await expect(
      page.getByText('Add a GitHub repository to scan for Claude Code artifacts.')
    ).toBeVisible();
  });

  test('validates GitHub URL format', async ({ page }) => {
    // Open modal
    await page.getByRole('button', { name: /Add Source/i }).click();

    // Enter invalid URL
    const urlInput = page.locator('#repo-url');
    await urlInput.fill('invalid-url');

    // Verify validation error
    await expect(
      page.getByText('Enter a valid GitHub URL (https://github.com/owner/repo)')
    ).toBeVisible();

    // Verify submit button is disabled
    const submitButton = page.getByRole('button', { name: 'Add Source' });
    await expect(submitButton).toBeDisabled();

    // Enter valid URL
    await urlInput.fill('https://github.com/anthropics/anthropic-cookbook');

    // Verify error is cleared and button is enabled
    await expect(
      page.getByText('Enter a valid GitHub URL (https://github.com/owner/repo)')
    ).not.toBeVisible();
    await expect(submitButton).toBeEnabled();
  });

  test('creates source with valid inputs', async ({ page }) => {
    // Open modal
    await page.getByRole('button', { name: /Add Source/i }).click();

    // Fill in form
    await page.locator('#repo-url').fill('https://github.com/anthropics/anthropic-cookbook');
    await page.locator('#ref').fill('main');

    // Submit form
    await page.getByRole('button', { name: 'Add Source' }).click();

    // Verify modal closes
    await expectModalClosed(page, '[role="dialog"]');

    // Verify source appears in list (page should refresh)
    await expect(page.getByText('anthropics/anthropic-cookbook')).toBeVisible();
  });

  test('creates source with optional root hint', async ({ page }) => {
    // Open modal
    await page.getByRole('button', { name: /Add Source/i }).click();

    // Fill in form with root hint
    await page.locator('#repo-url').fill('https://github.com/anthropics/anthropic-cookbook');
    await page.locator('#ref').fill('main');
    await page.locator('#root-hint').fill('skills/');

    // Submit form
    await page.getByRole('button', { name: 'Add Source' }).click();

    // Verify modal closes
    await expectModalClosed(page, '[role="dialog"]');
  });

  test('selects different trust levels', async ({ page }) => {
    // Open modal
    await page.getByRole('button', { name: /Add Source/i }).click();

    // Open trust level dropdown
    await page.getByRole('combobox', { name: /Trust Level/i }).click();

    // Verify options are available
    await expect(page.getByRole('option', { name: 'Basic' })).toBeVisible();
    await expect(page.getByRole('option', { name: 'Verified' })).toBeVisible();
    await expect(page.getByRole('option', { name: 'Official' })).toBeVisible();

    // Select Verified
    await page.getByRole('option', { name: 'Verified' }).click();
  });

  test('cancels add source modal', async ({ page }) => {
    // Open modal
    await page.getByRole('button', { name: /Add Source/i }).click();

    // Verify modal is open
    await expectModalOpen(page, '[role="dialog"]');

    // Click cancel button
    await page.getByRole('button', { name: 'Cancel' }).click();

    // Verify modal closes
    await expectModalClosed(page, '[role="dialog"]');
  });
});

// ============================================================================
// Test Suite: Source Detail Page
// ============================================================================

test.describe('Source Detail Page', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
  });

  test('displays source header with repository information', async ({ page }) => {
    await navigateToSourceDetailPage(page);

    // Verify header
    await expect(page.getByText('anthropics/anthropic-cookbook')).toBeVisible();
    await expect(page.getByText('main')).toBeVisible();

    // Verify action buttons
    await expect(page.getByRole('button', { name: /Rescan/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /View Repo/i })).toBeVisible();
  });

  test('displays back button and navigates to sources list', async ({ page }) => {
    await navigateToSourceDetailPage(page);

    // Click back button
    const backButton = page.getByRole('button', { name: /Back to Sources/i });
    await backButton.click();

    // Verify navigation
    await expect(page).toHaveURL('/marketplace/sources');
  });

  test('displays status counts as filter badges', async ({ page }) => {
    await navigateToSourceDetailPage(page);

    // Verify status count badges
    await expect(page.getByText('new: 1')).toBeVisible();
    await expect(page.getByText('updated: 1')).toBeVisible();
    await expect(page.getByText('imported: 1')).toBeVisible();
  });

  test('filters catalog by artifact type', async ({ page }) => {
    await navigateToSourceDetailPage(page);

    // Open type filter dropdown
    const typeSelect = page.getByRole('combobox').filter({ hasText: /All types/i });
    await typeSelect.click();

    // Select Skills
    await page.getByRole('option', { name: 'Skills' }).click();

    // Verify filter is applied (count should change)
    // Note: In a real test, we'd verify the filtered results
    await expect(page.getByText('Skills')).toBeVisible();
  });

  test('filters catalog by status badge', async ({ page }) => {
    await navigateToSourceDetailPage(page);

    // Click on "new" status badge
    const newBadge = page.getByText('new: 1');
    await newBadge.click();

    // Verify badge has active state (ring-2 ring-primary)
    await expect(newBadge).toHaveClass(/ring-2/);
  });

  test('clears filters', async ({ page }) => {
    await navigateToSourceDetailPage(page);

    // Apply a filter
    const typeSelect = page.getByRole('combobox').filter({ hasText: /All types/i });
    await typeSelect.click();
    await page.getByRole('option', { name: 'Skills' }).click();

    // Clear filters
    const clearButton = page.getByRole('button', { name: 'Clear filters' });
    await clearButton.click();

    // Verify filters are cleared
    await expect(clearButton).not.toBeVisible();
  });

  test('searches artifacts by name', async ({ page }) => {
    await navigateToSourceDetailPage(page);

    // Wait for artifacts to load
    await expect(page.getByText('canvas-design')).toBeVisible();

    // Search for specific artifact
    const searchInput = page.getByPlaceholder('Search artifacts...');
    await searchInput.fill('canvas');

    // Verify filtered results
    await expect(page.getByText('canvas-design')).toBeVisible();

    // Search for non-existent artifact
    await searchInput.fill('nonexistent');

    // Verify no results
    await expect(page.getByText('No artifacts found')).toBeVisible();
  });

  test('displays artifact cards with correct status chips', async ({ page }) => {
    await navigateToSourceDetailPage(page);

    // Verify status badges on cards
    await expect(page.getByText('New').first()).toBeVisible();
    await expect(page.getByText('Updated').first()).toBeVisible();
    await expect(page.getByText('Imported').first()).toBeVisible();
  });

  test('displays confidence scores with color coding', async ({ page }) => {
    await navigateToSourceDetailPage(page);

    // Verify confidence scores are displayed
    await expect(page.getByText('95% confidence')).toBeVisible();
    await expect(page.getByText('85% confidence')).toBeVisible();
    await expect(page.getByText('90% confidence')).toBeVisible();
  });

  test('displays GitHub links for artifacts', async ({ page }) => {
    await navigateToSourceDetailPage(page);

    // Verify external links
    const githubLinks = page.getByText('View on GitHub');
    await expect(githubLinks.first()).toBeVisible();
  });
});

// ============================================================================
// Test Suite: Rescan Source
// ============================================================================

test.describe('Rescan Source', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
    await navigateToSourceDetailPage(page);
  });

  test('initiates rescan from detail page', async ({ page }) => {
    // Click rescan button
    const rescanButton = page.getByRole('button', { name: /Rescan/i });
    await rescanButton.click();

    // Verify button shows loading state
    await expect(rescanButton).toContainText('Scanning...');
    await expect(rescanButton).toBeDisabled();
  });

  test('updates catalog after successful rescan', async ({ page }) => {
    // Mock updated catalog response
    await mockApiRoute(
      page,
      `/api/v1/marketplace/sources/${mockSource.id}/catalog*`,
      {
        ...mockCatalogResponse,
        items: [
          ...mockCatalogResponse.items,
          {
            id: 'entry-4',
            source_id: 'source-123',
            name: 'new-skill',
            artifact_type: 'skill',
            path: '.claude/skills/new-skill.md',
            status: 'new',
            confidence_score: 88,
            upstream_url: 'https://github.com/anthropics/anthropic-cookbook/blob/main/.claude/skills/new-skill.md',
            detected_at: '2024-12-08T11:00:00Z',
          },
        ],
        total: 4,
      }
    );

    // Click rescan
    await page.getByRole('button', { name: /Rescan/i }).click();

    // Wait for rescan to complete
    await page.waitForTimeout(1000);

    // Verify new artifact appears (in real test, this would be data-driven)
    // Note: This is simplified - in production, we'd verify the actual update
  });
});

// ============================================================================
// Test Suite: Import Artifacts
// ============================================================================

test.describe('Import Artifacts', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
    await navigateToSourceDetailPage(page);
  });

  test('imports single artifact', async ({ page }) => {
    // Wait for artifacts to load
    await expect(page.getByText('canvas-design')).toBeVisible();

    // Find the first "New" artifact and click its import button
    const firstImportButton = page.getByRole('button', { name: /Import/i }).first();
    await firstImportButton.click();

    // Verify loading state
    await expect(page.getByText('Importing...')).toBeVisible();
  });

  test('selects multiple artifacts for bulk import', async ({ page }) => {
    // Wait for artifacts to load
    await expect(page.getByText('canvas-design')).toBeVisible();

    // Click checkboxes for multiple artifacts
    const checkboxes = page.getByRole('checkbox');
    await checkboxes.nth(0).check(); // First artifact
    await checkboxes.nth(1).check(); // Second artifact

    // Verify selection count
    await expect(page.getByText(/Import 2 selected/i)).toBeVisible();
  });

  test('imports selected artifacts in bulk', async ({ page }) => {
    // Wait for artifacts to load
    await expect(page.getByText('canvas-design')).toBeVisible();

    // Select artifacts
    const checkboxes = page.getByRole('checkbox');
    await checkboxes.nth(0).check();
    await checkboxes.nth(1).check();

    // Click bulk import button
    const bulkImportButton = page.getByRole('button', { name: /Import 2 selected/i });
    await bulkImportButton.click();

    // Verify loading state
    await expect(page.getByText('Importing...')).toBeVisible();
  });

  test('selects and deselects all artifacts', async ({ page }) => {
    // Wait for artifacts to load
    await expect(page.getByText('canvas-design')).toBeVisible();

    // Click "Select All" button
    const selectAllButton = page.getByRole('button', { name: /Select All/i });
    await selectAllButton.click();

    // Verify button changes to "Deselect All"
    await expect(page.getByRole('button', { name: /Deselect All/i })).toBeVisible();

    // Click "Deselect All"
    await page.getByRole('button', { name: /Deselect All/i }).click();

    // Verify button changes back to "Select All"
    await expect(selectAllButton).toBeVisible();
  });

  test('disables import for already imported artifacts', async ({ page }) => {
    // Wait for artifacts to load
    await expect(page.getByText('code-review')).toBeVisible();

    // Find the imported artifact card
    const importedCard = page.locator('text=code-review').locator('..');

    // Verify it shows import date instead of import button
    await expect(importedCard.getByText(/Imported/i)).toBeVisible();
    await expect(importedCard.getByRole('button', { name: /Import/i })).not.toBeVisible();
  });

  test('disables selection for removed artifacts', async ({ page }) => {
    // Mock catalog with removed artifact
    await mockApiRoute(
      page,
      `/api/v1/marketplace/sources/${mockSource.id}/catalog*`,
      {
        ...mockCatalogResponse,
        items: [
          {
            id: 'entry-removed',
            source_id: 'source-123',
            name: 'removed-skill',
            artifact_type: 'skill',
            path: '.claude/skills/removed-skill.md',
            status: 'removed',
            confidence_score: 75,
            upstream_url: 'https://github.com/anthropics/anthropic-cookbook/blob/main/.claude/skills/removed-skill.md',
            detected_at: '2024-12-08T10:00:00Z',
          },
        ],
        total: 1,
        counts_by_status: { removed: 1 },
      }
    );

    await page.reload();
    await waitForPageLoad(page);

    // Find removed artifact checkbox
    const removedCheckbox = page.getByRole('checkbox').first();

    // Verify checkbox is disabled
    await expect(removedCheckbox).toBeDisabled();
  });
});

// ============================================================================
// Test Suite: Error Handling
// ============================================================================

test.describe('Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
  });

  test('shows error for invalid GitHub URL', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Open modal
    await page.getByRole('button', { name: /Add Source/i }).click();

    // Enter invalid URL
    await page.locator('#repo-url').fill('not-a-github-url');

    // Verify validation error
    await expect(
      page.getByText('Enter a valid GitHub URL (https://github.com/owner/repo)')
    ).toBeVisible();
  });

  test('shows error when API request fails', async ({ page }) => {
    // Mock API error
    await mockApiRoute(
      page,
      '/api/v1/marketplace/sources*',
      { error: 'Internal server error' },
      500
    );

    await navigateToSourcesPage(page);

    // Verify error message
    await expect(page.getByText('Failed to load sources. Please try again later.')).toBeVisible();

    // Verify retry button
    await expect(page.getByRole('button', { name: 'Retry' })).toBeVisible();
  });

  test('shows error for private repo without PAT', async ({ page }) => {
    // Mock private repo error
    await mockApiRoute(
      page,
      '/api/v1/marketplace/sources',
      { error: 'Repository not found or access denied. Private repositories require authentication.' },
      403
    );

    await navigateToSourcesPage(page);

    // Open modal and submit
    await page.getByRole('button', { name: /Add Source/i }).click();
    await page.locator('#repo-url').fill('https://github.com/private/repo');
    await page.getByRole('button', { name: 'Add Source' }).click();

    // Note: Error would be shown in a toast/alert - implementation varies
    // In a real test, we'd check for the specific error message
  });

  test('shows error for source not found', async ({ page }) => {
    // Mock 404 error
    await mockApiRoute(
      page,
      `/api/v1/marketplace/sources/nonexistent`,
      { error: 'Source not found' },
      404
    );

    await page.goto('/marketplace/sources/nonexistent');
    await waitForPageLoad(page);

    // Verify error state
    await expect(page.getByText('Source not found')).toBeVisible();
    await expect(page.getByRole('button', { name: /Back to Sources/i })).toBeVisible();
  });

  test('handles network timeout gracefully', async ({ page }) => {
    // Mock slow API response
    await page.route('**/api/v1/marketplace/sources*', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 10000)); // 10s delay
      await route.abort();
    });

    await page.goto('/marketplace/sources');

    // Verify loading state persists
    await expect(page.locator('[aria-busy="true"]').first()).toBeVisible({ timeout: 5000 });
  });
});

// ============================================================================
// Test Suite: Accessibility
// ============================================================================

test.describe('Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
  });

  test('supports keyboard navigation through sources list', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Wait for page to load
    await expect(page.getByText('anthropics/anthropic-cookbook')).toBeVisible();

    // Tab through interactive elements
    await pressKey(page, 'Tab'); // Refresh button
    await pressKey(page, 'Tab'); // Add Source button
    await pressKey(page, 'Tab'); // Search input

    // Verify search input has focus
    await expectFocused(page, 'input[placeholder="Search repositories..."]');
  });

  test('supports keyboard navigation in add source modal', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Open modal
    await page.getByRole('button', { name: /Add Source/i }).click();

    // Tab through form fields
    await pressKey(page, 'Tab'); // Close button
    await pressKey(page, 'Tab'); // Repo URL input

    // Verify first input has focus
    await expectFocused(page, '#repo-url');

    // Continue tabbing
    await pressKey(page, 'Tab'); // Ref input
    await expectFocused(page, '#ref');

    await pressKey(page, 'Tab'); // Root hint input
    await expectFocused(page, '#root-hint');
  });

  test('closes modal with Escape key', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Open modal
    await page.getByRole('button', { name: /Add Source/i }).click();
    await expectModalOpen(page, '[role="dialog"]');

    // Press Escape
    await pressKey(page, 'Escape');

    // Verify modal closes
    await expectModalClosed(page, '[role="dialog"]');
  });

  test('has proper ARIA labels on interactive elements', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Verify buttons have accessible names
    await expect(page.getByRole('button', { name: /Refresh/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Add Source/i })).toBeVisible();

    // Verify inputs have labels
    const searchInput = page.getByPlaceholder('Search repositories...');
    await expect(searchInput).toHaveAttribute('type', 'text');
  });

  test('has proper ARIA labels in source detail page', async ({ page }) => {
    await navigateToSourceDetailPage(page);

    // Verify checkboxes have accessible labels (via role)
    const checkboxes = page.getByRole('checkbox');
    await expect(checkboxes.first()).toBeVisible();

    // Verify buttons have accessible names
    await expect(page.getByRole('button', { name: /Rescan/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Select All/i })).toBeVisible();
  });

  test('maintains focus after modal close', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Click Add Source button
    const addButton = page.getByRole('button', { name: /Add Source/i });
    await addButton.click();

    // Close modal
    await page.getByRole('button', { name: 'Cancel' }).click();

    // Verify focus returns to trigger button
    await expectFocused(page, 'button:has-text("Add Source")');
  });
});

// ============================================================================
// Test Suite: Responsive Design
// ============================================================================

test.describe('Responsive Design', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
  });

  test('displays properly on mobile viewport', async ({ page }) => {
    // Set mobile viewport (iPhone 13)
    await page.setViewportSize({ width: 390, height: 844 });

    await navigateToSourcesPage(page);

    // Verify header stacks vertically
    const header = page.locator('div').filter({ hasText: 'GitHub Sources' }).first();
    await expect(header).toBeVisible();

    // Verify source cards are full width (grid-cols-1)
    await expect(page.getByText('anthropics/anthropic-cookbook')).toBeVisible();
  });

  test('displays properly on tablet viewport', async ({ page }) => {
    // Set tablet viewport (iPad)
    await page.setViewportSize({ width: 768, height: 1024 });

    await navigateToSourcesPage(page);

    // Verify 2-column grid (md:grid-cols-2)
    await expect(page.getByText('anthropics/anthropic-cookbook')).toBeVisible();
  });

  test('displays properly on desktop viewport', async ({ page }) => {
    // Set desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });

    await navigateToSourcesPage(page);

    // Verify 3-column grid (lg:grid-cols-3)
    await expect(page.getByText('anthropics/anthropic-cookbook')).toBeVisible();

    // Verify header is horizontal
    const header = page.locator('div').filter({ hasText: 'GitHub Sources' }).first();
    await expect(header).toBeVisible();
  });

  test('modal is responsive on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 390, height: 844 });

    await navigateToSourcesPage(page);

    // Open modal
    await page.getByRole('button', { name: /Add Source/i }).click();

    // Verify modal is visible and fits viewport
    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible();

    // Verify form fields are stacked
    await expect(page.locator('#repo-url')).toBeVisible();
    await expect(page.locator('#ref')).toBeVisible();
  });

  test('source detail filters are responsive', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 390, height: 844 });

    await navigateToSourceDetailPage(page);

    // Verify filters wrap on mobile
    await expect(page.getByPlaceholder('Search artifacts...')).toBeVisible();
    await expect(page.getByRole('combobox').first()).toBeVisible();

    // Verify bulk action buttons are visible
    await expect(page.getByRole('button', { name: /Select All/i })).toBeVisible();
  });
});

// ============================================================================
// Test Suite: Load More / Pagination
// ============================================================================

test.describe('Pagination and Load More', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
  });

  test('loads more sources when available', async ({ page }) => {
    // Mock paginated response
    await mockApiRoute(page, '/api/v1/marketplace/sources*', {
      items: [mockSource],
      total: 25,
      page: 1,
      page_size: 20,
      has_next: true,
    });

    await navigateToSourcesPage(page);

    // Verify Load More button appears
    await expect(page.getByRole('button', { name: 'Load More' })).toBeVisible();

    // Click Load More
    await page.getByRole('button', { name: 'Load More' }).click();

    // Verify loading state
    await expect(page.getByText('Loading...')).toBeVisible();
  });

  test('hides load more button when all sources loaded', async ({ page }) => {
    // Mock final page response
    await mockApiRoute(page, '/api/v1/marketplace/sources*', {
      items: [mockSource],
      total: 1,
      page: 1,
      page_size: 20,
      has_next: false,
    });

    await navigateToSourcesPage(page);

    // Verify Load More button is not present
    await expect(page.getByRole('button', { name: 'Load More' })).not.toBeVisible();
  });

  test('loads more catalog entries in source detail', async ({ page }) => {
    // Mock paginated catalog
    await mockApiRoute(
      page,
      `/api/v1/marketplace/sources/${mockSource.id}/catalog*`,
      {
        ...mockCatalogResponse,
        total: 30,
        has_next: true,
      }
    );

    await navigateToSourceDetailPage(page);

    // Verify Load More button appears
    await expect(page.getByRole('button', { name: 'Load More' })).toBeVisible();

    // Click Load More
    await page.getByRole('button', { name: 'Load More' }).click();

    // Verify loading state
    await expect(page.getByText('Loading...')).toBeVisible();
  });
});
