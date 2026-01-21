/**
 * End-to-End Tests for Catalog File Preview
 *
 * Tests the complete user workflow for previewing catalog artifact files.
 * Validates file tree loading, file selection, content display, and error handling.
 *
 * Test Coverage:
 * - Opening CatalogEntryModal from source detail page
 * - Switching to Contents tab
 * - File tree loading and display
 * - File selection and content preview
 * - Auto-selection of default file
 * - Error handling scenarios
 * - Truncation warning display
 * - Accessibility (keyboard navigation, ARIA)
 */

import { test, expect, type Page } from '@playwright/test';
import {
  waitForPageLoad,
  mockApiRoute,
  expectModalOpen,
  expectModalClosed,
  pressKey,
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
  artifact_count: 5,
  last_scan_at: '2024-12-08T10:00:00Z',
  created_at: '2024-12-01T10:00:00Z',
};

const mockCatalogEntry = {
  id: 'entry-1',
  source_id: 'source-123',
  name: 'canvas-design',
  artifact_type: 'skill',
  path: '.claude/skills/canvas-design',
  status: 'new',
  confidence_score: 95,
  upstream_url:
    'https://github.com/anthropics/anthropic-cookbook/tree/main/.claude/skills/canvas-design',
  detected_at: '2024-12-08T10:00:00Z',
  detected_sha: 'abc1234567890',
  detected_version: 'v1.0.0',
  score_breakdown: {
    has_readme: { score: 20, max: 20, reason: 'README.md found' },
    file_structure: { score: 15, max: 20, reason: 'Standard structure' },
    metadata: { score: 30, max: 30, reason: 'Complete metadata' },
    content_quality: { score: 30, max: 30, reason: 'High quality content' },
  },
};

const mockCatalogResponse = {
  items: [mockCatalogEntry],
  total: 1,
  page: 1,
  page_size: 20,
  has_next: false,
  counts_by_type: { skill: 1 },
  counts_by_status: { new: 1 },
};

const mockFileTree = {
  entries: [
    { path: 'README.md', type: 'file', size: 1024 },
    { path: 'SKILL.md', type: 'file', size: 2048 },
    { path: 'examples', type: 'tree', size: 0 },
    { path: 'examples/basic.md', type: 'file', size: 512 },
    { path: 'examples/advanced.md', type: 'file', size: 768 },
    { path: 'config.json', type: 'file', size: 256 },
  ],
  cached: false,
};

const mockFileContent = {
  content:
    '# Canvas Design Skill\n\nThis skill helps you create beautiful canvas designs.\n\n## Usage\n\nSimply describe what you want to create.',
  truncated: false,
  original_size: 150,
};

const mockTruncatedFileContent = {
  content: '# Very Large File\n\nThis is a truncated preview...\n' + '.\n'.repeat(100),
  truncated: true,
  original_size: 1024000, // ~1MB
};

// ============================================================================
// Helper Functions
// ============================================================================

async function setupMockApiRoutes(page: Page) {
  // Mock sources list
  await mockApiRoute(page, '/api/v1/marketplace/sources*', {
    items: [mockSource],
    total: 1,
    page: 1,
    page_size: 20,
    has_next: false,
  });

  // Mock source detail
  await mockApiRoute(page, `/api/v1/marketplace/sources/${mockSource.id}`, mockSource);

  // Mock catalog
  await mockApiRoute(
    page,
    `/api/v1/marketplace/sources/${mockSource.id}/catalog*`,
    mockCatalogResponse
  );

  // Mock file tree endpoint
  await mockApiRoute(page, `/api/v1/marketplace/sources/*/artifacts/*/files`, mockFileTree);

  // Mock file content endpoint
  await mockApiRoute(page, `/api/v1/marketplace/sources/*/artifacts/*/files/*`, mockFileContent);
}

async function navigateToSourceDetailPage(page: Page, sourceId: string = mockSource.id) {
  await page.goto(`/marketplace/sources/${sourceId}`);
  await waitForPageLoad(page);
}

async function openCatalogEntryModal(page: Page) {
  // Wait for catalog entries to load
  await expect(page.getByText('canvas-design')).toBeVisible({ timeout: 10000 });

  // Click on the catalog entry to open modal
  // The entry card should be clickable
  const entryCard = page.locator('[role="button"]').filter({ hasText: 'canvas-design' }).first();
  await entryCard.click();

  // Wait for modal to open
  await expectModalOpen(page, '[role="dialog"]');
}

async function switchToContentsTab(page: Page) {
  // Click on Contents tab
  const contentsTab = page.getByRole('tab', { name: /Contents/i });
  await contentsTab.click();

  // Wait for tab content to be visible
  await expect(page.getByRole('tabpanel')).toBeVisible();
}

// ============================================================================
// Test Suite: File Preview Workflow
// ============================================================================

test.describe('Catalog File Preview - Happy Path', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
    await navigateToSourceDetailPage(page);
  });

  test('user can browse and preview catalog artifact files', async ({ page }) => {
    // Open catalog entry modal
    await openCatalogEntryModal(page);

    // Verify modal header shows entry name
    await expect(page.getByText('Catalog Entry Details')).toBeVisible();
    await expect(page.getByRole('dialog').getByText('canvas-design')).toBeVisible();

    // Switch to Contents tab
    await switchToContentsTab(page);

    // Wait for file tree to load (should see file names)
    await expect(page.getByText('README.md')).toBeVisible({ timeout: 10000 });

    // Verify file tree structure is displayed
    await expect(page.getByText('SKILL.md')).toBeVisible();
    await expect(page.getByText('examples')).toBeVisible();
    await expect(page.getByText('config.json')).toBeVisible();

    // Auto-selection should select first .md file (README.md)
    // and content pane should show the file content
    await expect(page.getByText('Canvas Design Skill')).toBeVisible({ timeout: 5000 });
  });

  test('user can select different files from file tree', async ({ page }) => {
    await openCatalogEntryModal(page);
    await switchToContentsTab(page);

    // Wait for file tree to load
    await expect(page.getByText('README.md')).toBeVisible({ timeout: 10000 });

    // Click on a different file
    const skillFile = page.getByRole('button').filter({ hasText: 'SKILL.md' });
    await skillFile.click();

    // Verify content pane updates (breadcrumb should show SKILL.md)
    await expect(page.getByText('SKILL.md').last()).toBeVisible();
  });

  test('user can expand and collapse directory in file tree', async ({ page }) => {
    await openCatalogEntryModal(page);
    await switchToContentsTab(page);

    // Wait for file tree to load
    await expect(page.getByText('examples')).toBeVisible({ timeout: 10000 });

    // Click on examples directory to expand
    const examplesDir = page.getByRole('button').filter({ hasText: 'examples' }).first();
    await examplesDir.click();

    // Nested files should be visible
    await expect(page.getByText('basic.md')).toBeVisible();
    await expect(page.getByText('advanced.md')).toBeVisible();

    // Click again to collapse
    await examplesDir.click();

    // Nested files should be hidden
    await expect(page.getByText('basic.md')).not.toBeVisible();
  });

  test('displays confidence score breakdown in overview tab', async ({ page }) => {
    await openCatalogEntryModal(page);

    // Should be on Overview tab by default
    await expect(page.getByText('Confidence Score Breakdown')).toBeVisible();

    // Verify score breakdown items are displayed
    await expect(page.getByText(/README.*found/i)).toBeVisible();
    await expect(page.getByText(/Standard structure/i)).toBeVisible();
  });

  test('can switch between Overview and Contents tabs', async ({ page }) => {
    await openCatalogEntryModal(page);

    // Verify Overview tab is active by default
    await expect(page.getByText('Confidence Score Breakdown')).toBeVisible();

    // Switch to Contents tab
    await switchToContentsTab(page);

    // File tree should be visible
    await expect(page.getByText('README.md')).toBeVisible({ timeout: 10000 });

    // Switch back to Overview tab
    const overviewTab = page.getByRole('tab', { name: /Overview/i });
    await overviewTab.click();

    // Confidence breakdown should be visible again
    await expect(page.getByText('Confidence Score Breakdown')).toBeVisible();
  });

  test('displays artifact metadata in overview tab', async ({ page }) => {
    await openCatalogEntryModal(page);

    // Verify metadata is displayed
    await expect(page.getByText('Metadata')).toBeVisible();
    await expect(page.getByText('.claude/skills/canvas-design')).toBeVisible();
    await expect(page.getByText('abc1234')).toBeVisible(); // Shortened SHA
    await expect(page.getByText('v1.0.0')).toBeVisible();
  });
});

// ============================================================================
// Test Suite: Error Handling
// ============================================================================

test.describe('Catalog File Preview - Error Handling', () => {
  test('shows error state when file tree fails to load', async ({ page }) => {
    // Set up base routes
    await mockApiRoute(page, '/api/v1/marketplace/sources*', {
      items: [mockSource],
      total: 1,
      page: 1,
      page_size: 20,
      has_next: false,
    });
    await mockApiRoute(page, `/api/v1/marketplace/sources/${mockSource.id}`, mockSource);
    await mockApiRoute(
      page,
      `/api/v1/marketplace/sources/${mockSource.id}/catalog*`,
      mockCatalogResponse
    );

    // Mock file tree to return error
    await mockApiRoute(
      page,
      `/api/v1/marketplace/sources/*/artifacts/*/files`,
      { error: 'Failed to fetch file tree' },
      500
    );

    await navigateToSourceDetailPage(page);
    await openCatalogEntryModal(page);
    await switchToContentsTab(page);

    // Verify error state is displayed
    await expect(page.getByText('Failed to load file tree')).toBeVisible({ timeout: 10000 });

    // Verify retry button is available
    await expect(page.getByRole('button', { name: /Try again/i })).toBeVisible();

    // Verify GitHub link fallback is available
    await expect(page.getByRole('link', { name: /View on GitHub/i })).toBeVisible();
  });

  test('shows error state when file content fails to load', async ({ page }) => {
    // Set up routes with file tree success but content failure
    await setupMockApiRoutes(page);

    // Override content endpoint to fail
    await mockApiRoute(
      page,
      `/api/v1/marketplace/sources/*/artifacts/*/files/*`,
      { error: 'Failed to fetch file content' },
      500
    );

    await navigateToSourceDetailPage(page);
    await openCatalogEntryModal(page);
    await switchToContentsTab(page);

    // Wait for file tree to load
    await expect(page.getByText('README.md')).toBeVisible({ timeout: 10000 });

    // Verify error state in content pane
    await expect(page.getByText('Failed to load file')).toBeVisible({ timeout: 10000 });

    // Verify retry button is available
    await expect(page.getByRole('button', { name: /Try again/i })).toBeVisible();
  });

  test('shows rate limit error message', async ({ page }) => {
    // Set up routes with file tree success but content failure
    await setupMockApiRoutes(page);

    // Override content endpoint to return rate limit error
    await mockApiRoute(
      page,
      `/api/v1/marketplace/sources/*/artifacts/*/files/*`,
      { error: 'Rate limit exceeded' },
      429
    );

    await navigateToSourceDetailPage(page);
    await openCatalogEntryModal(page);
    await switchToContentsTab(page);

    // Wait for file tree to load
    await expect(page.getByText('README.md')).toBeVisible({ timeout: 10000 });

    // Verify rate limit error message
    await expect(page.getByText(/rate limit/i)).toBeVisible({ timeout: 10000 });
  });
});

// ============================================================================
// Test Suite: Truncation Handling
// ============================================================================

test.describe('Catalog File Preview - Large File Handling', () => {
  test('shows truncation warning for large files', async ({ page }) => {
    // Set up routes with truncated content
    await mockApiRoute(page, '/api/v1/marketplace/sources*', {
      items: [mockSource],
      total: 1,
      page: 1,
      page_size: 20,
      has_next: false,
    });
    await mockApiRoute(page, `/api/v1/marketplace/sources/${mockSource.id}`, mockSource);
    await mockApiRoute(
      page,
      `/api/v1/marketplace/sources/${mockSource.id}/catalog*`,
      mockCatalogResponse
    );
    await mockApiRoute(page, `/api/v1/marketplace/sources/*/artifacts/*/files`, mockFileTree);
    await mockApiRoute(
      page,
      `/api/v1/marketplace/sources/*/artifacts/*/files/*`,
      mockTruncatedFileContent
    );

    await navigateToSourceDetailPage(page);
    await openCatalogEntryModal(page);
    await switchToContentsTab(page);

    // Wait for file tree to load
    await expect(page.getByText('README.md')).toBeVisible({ timeout: 10000 });

    // Verify truncation warning is displayed
    await expect(page.getByText(/Large file truncated/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/1.*MB/i)).toBeVisible();

    // Verify "View full file on GitHub" link is available
    await expect(page.getByRole('link', { name: /View full file on GitHub/i })).toBeVisible();
  });
});

// ============================================================================
// Test Suite: Modal Behavior
// ============================================================================

test.describe('Catalog File Preview - Modal Behavior', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
    await navigateToSourceDetailPage(page);
  });

  test('closes modal when clicking close button', async ({ page }) => {
    await openCatalogEntryModal(page);

    // Click close button (X)
    const closeButton = page.getByRole('button', { name: /close/i });
    await closeButton.click();

    // Verify modal is closed
    await expectModalClosed(page, '[role="dialog"]');
  });

  test('closes modal with Escape key', async ({ page }) => {
    await openCatalogEntryModal(page);

    // Press Escape
    await pressKey(page, 'Escape');

    // Verify modal is closed
    await expectModalClosed(page, '[role="dialog"]');
  });

  test('resets to Overview tab when modal reopens', async ({ page }) => {
    await openCatalogEntryModal(page);

    // Switch to Contents tab
    await switchToContentsTab(page);
    await expect(page.getByText('README.md')).toBeVisible({ timeout: 10000 });

    // Close modal
    await pressKey(page, 'Escape');
    await expectModalClosed(page, '[role="dialog"]');

    // Reopen modal
    await openCatalogEntryModal(page);

    // Should be on Overview tab again
    await expect(page.getByText('Confidence Score Breakdown')).toBeVisible();
  });
});

// ============================================================================
// Test Suite: Import Functionality
// ============================================================================

test.describe('Catalog File Preview - Import', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
    await navigateToSourceDetailPage(page);
  });

  test('displays import button in modal footer', async ({ page }) => {
    await openCatalogEntryModal(page);

    // Verify import button is visible in footer
    const importButton = page.getByRole('button', { name: /Import/i });
    await expect(importButton).toBeVisible();
    await expect(importButton).toBeEnabled();
  });

  test('displays View on GitHub button in modal footer', async ({ page }) => {
    await openCatalogEntryModal(page);

    // Verify GitHub link is visible
    const githubButton = page.getByRole('button', { name: /View on GitHub/i });
    await expect(githubButton).toBeVisible();
  });

  test('disables import button for already imported entries', async ({ page }) => {
    // Update mock to show imported status
    const importedEntry = { ...mockCatalogEntry, status: 'imported' };
    await mockApiRoute(page, `/api/v1/marketplace/sources/${mockSource.id}/catalog*`, {
      ...mockCatalogResponse,
      items: [importedEntry],
      counts_by_status: { imported: 1 },
    });

    await page.reload();
    await waitForPageLoad(page);
    await openCatalogEntryModal(page);

    // Verify import button is disabled
    const importButton = page.getByRole('button', { name: /Import/i });
    await expect(importButton).toBeDisabled();
  });
});

// ============================================================================
// Test Suite: Accessibility
// ============================================================================

test.describe('Catalog File Preview - Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
    await navigateToSourceDetailPage(page);
  });

  test('supports keyboard navigation between tabs', async ({ page }) => {
    await openCatalogEntryModal(page);

    // Focus on tabs
    const overviewTab = page.getByRole('tab', { name: /Overview/i });
    await overviewTab.focus();

    // Press arrow right to move to Contents tab
    await pressKey(page, 'ArrowRight');

    // Press Enter to select Contents tab
    await pressKey(page, 'Enter');

    // Verify Contents tab is now active
    await expect(page.getByText('README.md')).toBeVisible({ timeout: 10000 });
  });

  test('has proper ARIA labels on modal elements', async ({ page }) => {
    await openCatalogEntryModal(page);

    // Verify modal has proper role
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();

    // Verify tabs have proper role
    const tabList = page.getByRole('tablist');
    await expect(tabList).toBeVisible();

    // Verify individual tabs have proper role and labels
    await expect(page.getByRole('tab', { name: /Overview/i })).toBeVisible();
    await expect(page.getByRole('tab', { name: /Contents/i })).toBeVisible();
  });

  test('file tree items are keyboard accessible', async ({ page }) => {
    await openCatalogEntryModal(page);
    await switchToContentsTab(page);

    // Wait for file tree to load
    await expect(page.getByText('README.md')).toBeVisible({ timeout: 10000 });

    // File items should have role="button" and be keyboard focusable
    const fileItem = page.getByRole('button').filter({ hasText: 'SKILL.md' });
    await fileItem.focus();

    // Press Enter to select
    await pressKey(page, 'Enter');

    // Verify file is selected (content pane should update)
    await expect(page.locator('.bg-accent').filter({ hasText: 'SKILL.md' })).toBeVisible();
  });
});

// ============================================================================
// Test Suite: Empty States
// ============================================================================

test.describe('Catalog File Preview - Empty States', () => {
  test('shows empty state when no files in artifact', async ({ page }) => {
    // Set up routes with empty file tree
    await mockApiRoute(page, '/api/v1/marketplace/sources*', {
      items: [mockSource],
      total: 1,
      page: 1,
      page_size: 20,
      has_next: false,
    });
    await mockApiRoute(page, `/api/v1/marketplace/sources/${mockSource.id}`, mockSource);
    await mockApiRoute(
      page,
      `/api/v1/marketplace/sources/${mockSource.id}/catalog*`,
      mockCatalogResponse
    );
    await mockApiRoute(page, `/api/v1/marketplace/sources/*/artifacts/*/files`, {
      entries: [],
      cached: false,
    });

    await navigateToSourceDetailPage(page);
    await openCatalogEntryModal(page);
    await switchToContentsTab(page);

    // Verify empty state message
    await expect(page.getByText('No files found')).toBeVisible({ timeout: 10000 });
  });

  test('shows empty content state when no file selected', async ({ page }) => {
    // This tests the case where file tree loads but auto-selection doesn't happen
    // (e.g., all files are directories)
    await mockApiRoute(page, '/api/v1/marketplace/sources*', {
      items: [mockSource],
      total: 1,
      page: 1,
      page_size: 20,
      has_next: false,
    });
    await mockApiRoute(page, `/api/v1/marketplace/sources/${mockSource.id}`, mockSource);
    await mockApiRoute(
      page,
      `/api/v1/marketplace/sources/${mockSource.id}/catalog*`,
      mockCatalogResponse
    );
    // Only directories, no files
    await mockApiRoute(page, `/api/v1/marketplace/sources/*/artifacts/*/files`, {
      entries: [
        { path: 'folder1', type: 'tree', size: 0 },
        { path: 'folder2', type: 'tree', size: 0 },
      ],
      cached: false,
    });

    await navigateToSourceDetailPage(page);
    await openCatalogEntryModal(page);
    await switchToContentsTab(page);

    // Wait for directory to appear
    await expect(page.getByText('folder1')).toBeVisible({ timeout: 10000 });

    // Content pane should show empty state
    await expect(page.getByText('No file selected')).toBeVisible();
  });
});
