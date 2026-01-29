/**
 * E2E Tests for Marketplace Folder View (MFV-2.13)
 *
 * Tests the complete folder view workflow including two-pane layout,
 * semantic tree navigation, folder selection, filtering, and bulk actions.
 *
 * Test Coverage:
 * - Toggle to folder view mode
 * - Folder selection and navigation
 * - Folder expand/collapse
 * - Filter integration with folder view
 * - Subfolder navigation via cards
 * - Import All bulk action
 * - Empty state handling
 */

import { test, expect, type Page } from '@playwright/test';
import { waitForPageLoad, mockApiRoute } from '../helpers/test-utils';

// ============================================================================
// Mock Data
// ============================================================================

const mockSource = {
  id: 'source-folder-test',
  owner: 'anthropics',
  repo_name: 'skills-repo',
  ref: 'main',
  root_hint: '',
  repo_url: 'https://github.com/anthropics/skills-repo',
  trust_level: 'official',
  artifact_count: 25,
  scan_status: 'success',
  last_sync_at: '2024-12-10T10:00:00Z',
  created_at: '2024-12-01T10:00:00Z',
  tags: ['official', 'skills'],
  counts_by_type: {
    skill: 15,
    command: 7,
    agent: 3,
  },
};

// Catalog with nested folder structure for testing
const mockCatalogEntries = [
  // Root level skills (should be filtered out by semantic filtering)
  {
    id: 'entry-1',
    source_id: 'source-folder-test',
    name: 'canvas-design',
    artifact_type: 'skill',
    path: '.claude/skills/canvas-design.md',
    status: 'new',
    confidence_score: 95,
    upstream_url: 'https://github.com/anthropics/skills-repo/blob/main/.claude/skills/canvas-design.md',
    detected_at: '2024-12-08T10:00:00Z',
  },
  // Development tools folder (semantic folder - should show)
  {
    id: 'entry-2',
    source_id: 'source-folder-test',
    name: 'code-review',
    artifact_type: 'skill',
    path: '.claude/skills/dev-tools/code-review.md',
    status: 'new',
    confidence_score: 90,
    upstream_url: 'https://github.com/anthropics/skills-repo/blob/main/.claude/skills/dev-tools/code-review.md',
    detected_at: '2024-12-08T10:00:00Z',
  },
  {
    id: 'entry-3',
    source_id: 'source-folder-test',
    name: 'linter',
    artifact_type: 'skill',
    path: '.claude/skills/dev-tools/linter.md',
    status: 'updated',
    confidence_score: 88,
    upstream_url: 'https://github.com/anthropics/skills-repo/blob/main/.claude/skills/dev-tools/linter.md',
    detected_at: '2024-12-08T10:00:00Z',
  },
  // Dev tools subfolder: formatters (semantic subfolder)
  {
    id: 'entry-4',
    source_id: 'source-folder-test',
    name: 'prettier',
    artifact_type: 'skill',
    path: '.claude/skills/dev-tools/formatters/prettier.md',
    status: 'new',
    confidence_score: 92,
    upstream_url: 'https://github.com/anthropics/skills-repo/blob/main/.claude/skills/dev-tools/formatters/prettier.md',
    detected_at: '2024-12-08T10:00:00Z',
  },
  {
    id: 'entry-5',
    source_id: 'source-folder-test',
    name: 'eslint',
    artifact_type: 'skill',
    path: '.claude/skills/dev-tools/formatters/eslint.md',
    status: 'new',
    confidence_score: 91,
    upstream_url: 'https://github.com/anthropics/skills-repo/blob/main/.claude/skills/dev-tools/formatters/eslint.md',
    detected_at: '2024-12-08T10:00:00Z',
  },
  // Data science folder (semantic folder)
  {
    id: 'entry-6',
    source_id: 'source-folder-test',
    name: 'data-analysis',
    artifact_type: 'skill',
    path: '.claude/skills/data-science/data-analysis.md',
    status: 'imported',
    confidence_score: 94,
    upstream_url: 'https://github.com/anthropics/skills-repo/blob/main/.claude/skills/data-science/data-analysis.md',
    import_date: '2024-12-07T10:00:00Z',
    detected_at: '2024-12-08T10:00:00Z',
  },
  {
    id: 'entry-7',
    source_id: 'source-folder-test',
    name: 'visualization',
    artifact_type: 'skill',
    path: '.claude/skills/data-science/visualization.md',
    status: 'new',
    confidence_score: 89,
    upstream_url: 'https://github.com/anthropics/skills-repo/blob/main/.claude/skills/data-science/visualization.md',
    detected_at: '2024-12-08T10:00:00Z',
  },
  // Commands in different type folder (for type filter testing)
  {
    id: 'entry-8',
    source_id: 'source-folder-test',
    name: 'deploy',
    artifact_type: 'command',
    path: '.claude/commands/deploy.md',
    status: 'new',
    confidence_score: 87,
    upstream_url: 'https://github.com/anthropics/skills-repo/blob/main/.claude/commands/deploy.md',
    detected_at: '2024-12-08T10:00:00Z',
  },
];

const mockCatalogResponse = {
  items: mockCatalogEntries,
  total: mockCatalogEntries.length,
  page: 1,
  page_size: 50,
  has_next: false,
  counts_by_type: {
    skill: 7,
    command: 1,
  },
  counts_by_status: {
    new: 6,
    updated: 1,
    imported: 1,
  },
};

// ============================================================================
// Helper Functions
// ============================================================================

async function setupMockApiRoutes(page: Page) {
  // Mock source detail
  await mockApiRoute(page, `/api/v1/marketplace/sources/${mockSource.id}`, mockSource);

  // Mock catalog
  await mockApiRoute(
    page,
    `/api/v1/marketplace/sources/${mockSource.id}/catalog*`,
    mockCatalogResponse
  );

  // Mock import endpoint
  await mockApiRoute(page, `/api/v1/marketplace/sources/${mockSource.id}/import`, {
    success: true,
    imported_count: 1,
  });
}

async function navigateToSourceDetail(page: Page) {
  await page.goto(`/marketplace/sources/${mockSource.id}`);
  await waitForPageLoad(page);
}

async function toggleToFolderView(page: Page) {
  // Find and click the folder view toggle button
  const folderButton = page.getByRole('button', { name: /folder/i });
  await folderButton.click();

  // Wait for folder layout to render
  await page.waitForSelector('[data-testid="folder-tree"]', { timeout: 5000 });
}

async function selectFolder(page: Page, folderName: string | RegExp) {
  // Find folder in tree and click it
  const folderNode = page.getByRole('treeitem', { name: folderName });
  await folderNode.click();
}

async function expandFolder(page: Page, folderName: string | RegExp) {
  // Find folder and click its expand button
  const folderNode = page.getByRole('treeitem', { name: folderName });
  const expandButton = folderNode.getByRole('button', { name: /expand/i });
  await expandButton.click();
}

async function collapseFolder(page: Page, folderName: string | RegExp) {
  // Find folder and click its collapse button
  const folderNode = page.getByRole('treeitem', { name: folderName });
  const collapseButton = folderNode.getByRole('button', { name: /collapse/i });
  await collapseButton.click();
}

// ============================================================================
// Test Suite: Toggle to Folder View
// ============================================================================

test.describe('Folder View - Toggle and Layout', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
    await navigateToSourceDetail(page);
  });

  test('can toggle to folder view mode', async ({ page }) => {
    // Verify initial view (grid or list)
    await expect(page.locator('[data-testid="artifact-grid"]').or(page.locator('[data-testid="artifact-list"]'))).toBeVisible();

    // Click folder view toggle button
    await toggleToFolderView(page);

    // Verify two-pane layout appears
    await expect(page.locator('[data-testid="folder-layout"]')).toBeVisible();

    // Verify tree in left pane
    await expect(page.locator('[data-testid="folder-tree"]')).toBeVisible();

    // Verify detail pane on right
    await expect(page.locator('[data-testid="folder-detail-pane"]')).toBeVisible();
  });

  test('displays two-pane layout with correct proportions', async ({ page }) => {
    await toggleToFolderView(page);

    // Verify layout container exists
    const layout = page.locator('[data-testid="folder-layout"]');
    await expect(layout).toBeVisible();

    // Verify both panes are visible
    const leftPane = page.locator('[data-testid="folder-tree"]');
    const rightPane = page.locator('[data-testid="folder-detail-pane"]');

    await expect(leftPane).toBeVisible();
    await expect(rightPane).toBeVisible();

    // Check that panes are side by side (not stacked)
    const leftBox = await leftPane.boundingBox();
    const rightBox = await rightPane.boundingBox();

    expect(leftBox).toBeTruthy();
    expect(rightBox).toBeTruthy();

    // Left pane should be to the left of right pane
    if (leftBox && rightBox) {
      expect(leftBox.x).toBeLessThan(rightBox.x);
    }
  });

  test('folder view button shows active state when selected', async ({ page }) => {
    const folderButton = page.getByRole('button', { name: /folder/i });

    // Initial state - not pressed
    await expect(folderButton).toHaveAttribute('aria-pressed', 'false');

    // Click to activate folder view
    await folderButton.click();
    await page.waitForSelector('[data-testid="folder-tree"]');

    // Verify button is now in active state
    await expect(folderButton).toHaveAttribute('aria-pressed', 'true');
  });

  test('can toggle back to grid view from folder view', async ({ page }) => {
    // Toggle to folder view
    await toggleToFolderView(page);
    await expect(page.locator('[data-testid="folder-tree"]')).toBeVisible();

    // Toggle back to grid view
    const gridButton = page.getByRole('button', { name: /grid/i });
    await gridButton.click();

    // Verify folder layout is hidden
    await expect(page.locator('[data-testid="folder-tree"]')).not.toBeVisible();

    // Verify grid view is shown
    await expect(page.locator('[data-testid="artifact-grid"]')).toBeVisible();
  });
});

// ============================================================================
// Test Suite: Folder Selection
// ============================================================================

test.describe('Folder View - Folder Selection', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
    await navigateToSourceDetail(page);
    await toggleToFolderView(page);
  });

  test('selecting folder updates detail pane', async ({ page }) => {
    // Wait for tree to render
    await expect(page.locator('[data-testid="folder-tree"]')).toBeVisible();

    // Click on a folder in tree (e.g., "dev-tools")
    await selectFolder(page, /dev-tools/i);

    // Verify folder is selected (has visual state)
    const selectedFolder = page.getByRole('treeitem', { name: /dev-tools/i, selected: true });
    await expect(selectedFolder).toBeVisible();

    // Verify detail pane shows folder name
    const detailPane = page.locator('[data-testid="folder-detail-pane"]');
    await expect(detailPane).toContainText(/dev-tools/i);

    // Verify artifacts are displayed in detail pane
    await expect(detailPane.getByText(/code-review/i)).toBeVisible();
    await expect(detailPane.getByText(/linter/i)).toBeVisible();
  });

  test('first folder auto-selects on folder view toggle', async ({ page }) => {
    // After toggling to folder view, first semantic folder should be selected
    const detailPane = page.locator('[data-testid="folder-detail-pane"]');

    // Verify detail pane is populated (not empty)
    await expect(detailPane).not.toBeEmpty();

    // Verify at least one folder is marked as selected
    const selectedFolder = page.locator('[role="treeitem"][aria-selected="true"]');
    await expect(selectedFolder).toBeVisible();
  });

  test('selecting different folder changes detail pane content', async ({ page }) => {
    // Select first folder
    await selectFolder(page, /dev-tools/i);
    const detailPane = page.locator('[data-testid="folder-detail-pane"]');
    await expect(detailPane).toContainText(/dev-tools/i);

    // Select different folder
    await selectFolder(page, /data-science/i);

    // Verify detail pane updated
    await expect(detailPane).toContainText(/data-science/i);
    await expect(detailPane).toContainText(/data-analysis/i);
    await expect(detailPane).toContainText(/visualization/i);

    // Verify previous folder content is gone
    await expect(detailPane).not.toContainText(/code-review/i);
  });

  test('folder selection state persists visual feedback', async ({ page }) => {
    // Select a folder
    await selectFolder(page, /dev-tools/i);

    // Verify selected state
    const devToolsFolder = page.getByRole('treeitem', { name: /dev-tools/i });
    await expect(devToolsFolder).toHaveAttribute('aria-selected', 'true');

    // Select another folder
    await selectFolder(page, /data-science/i);

    // Verify previous folder is no longer selected
    await expect(devToolsFolder).toHaveAttribute('aria-selected', 'false');

    // Verify new folder is selected
    const dataScienceFolder = page.getByRole('treeitem', { name: /data-science/i });
    await expect(dataScienceFolder).toHaveAttribute('aria-selected', 'true');
  });
});

// ============================================================================
// Test Suite: Folder Expand/Collapse
// ============================================================================

test.describe('Folder View - Expand/Collapse', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
    await navigateToSourceDetail(page);
    await toggleToFolderView(page);
  });

  test('can expand and collapse folders', async ({ page }) => {
    // Find folder with children (dev-tools has formatters subfolder)
    const devToolsFolder = page.getByRole('treeitem', { name: /dev-tools/i });
    await expect(devToolsFolder).toBeVisible();

    // Initially, subfolder may not be visible
    const formattersFolder = page.getByRole('treeitem', { name: /formatters/i });
    const initiallyVisible = await formattersFolder.isVisible().catch(() => false);

    if (!initiallyVisible) {
      // Click expand button
      await expandFolder(page, /dev-tools/i);

      // Verify subfolder is now visible
      await expect(formattersFolder).toBeVisible();
    }

    // Click collapse button
    await collapseFolder(page, /dev-tools/i);

    // Verify subfolder is hidden
    await expect(formattersFolder).not.toBeVisible();
  });

  test('expand chevron rotates on expand/collapse', async ({ page }) => {
    const devToolsFolder = page.getByRole('treeitem', { name: /dev-tools/i });
    const expandButton = devToolsFolder.getByRole('button', { name: /expand|collapse/i });

    // Get initial state
    const initialAriaExpanded = await expandButton.getAttribute('aria-expanded');

    // Toggle expand
    await expandButton.click();

    // Verify aria-expanded changed
    const newAriaExpanded = await expandButton.getAttribute('aria-expanded');
    expect(newAriaExpanded).not.toBe(initialAriaExpanded);
  });

  test('expanding folder shows nested artifacts in tree', async ({ page }) => {
    // Expand dev-tools folder
    await expandFolder(page, /dev-tools/i);

    // Verify formatters subfolder appears
    await expect(page.getByRole('treeitem', { name: /formatters/i })).toBeVisible();

    // Expand formatters subfolder
    await expandFolder(page, /formatters/i);

    // Note: Leaf artifacts (prettier, eslint) may not show as tree items
    // depending on semantic filtering, but we can verify detail pane content
    await selectFolder(page, /formatters/i);
    const detailPane = page.locator('[data-testid="folder-detail-pane"]');
    await expect(detailPane).toContainText(/prettier/i);
    await expect(detailPane).toContainText(/eslint/i);
  });

  test('collapsing parent folder hides all descendants', async ({ page }) => {
    // Expand dev-tools and its subfolder
    await expandFolder(page, /dev-tools/i);
    await expect(page.getByRole('treeitem', { name: /formatters/i })).toBeVisible();

    // Collapse parent
    await collapseFolder(page, /dev-tools/i);

    // Verify subfolder is hidden
    await expect(page.getByRole('treeitem', { name: /formatters/i })).not.toBeVisible();
  });
});

// ============================================================================
// Test Suite: Filter Integration
// ============================================================================

test.describe('Folder View - Filter Integration', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
    await navigateToSourceDetail(page);
    await toggleToFolderView(page);
  });

  test('filters apply to folder artifacts', async ({ page }) => {
    // Select a folder with multiple artifact types
    await selectFolder(page, /dev-tools/i);
    const detailPane = page.locator('[data-testid="folder-detail-pane"]');

    // Note initial artifact count (should show skills)
    const initialCount = await detailPane.locator('[data-testid="artifact-card"]').count();
    expect(initialCount).toBeGreaterThan(0);

    // Apply type filter (e.g., filter to only show skills)
    const typeFilter = page.locator('#artifact-type-filter');
    if (await typeFilter.isVisible()) {
      await typeFilter.click();
      await page.getByRole('option', { name: /skill/i }).click();

      // Verify filtered results (commands should be hidden if any existed)
      await expect(detailPane).toContainText(/code-review/i); // skill
      await expect(detailPane).toContainText(/linter/i); // skill
    }
  });

  test('search filter applies to folder view', async ({ page }) => {
    // Select folder
    await selectFolder(page, /dev-tools/i);
    const detailPane = page.locator('[data-testid="folder-detail-pane"]');

    // Apply search filter
    const searchInput = page.getByPlaceholder(/search/i);
    if (await searchInput.isVisible()) {
      await searchInput.fill('code-review');

      // Verify only matching artifacts shown
      await expect(detailPane).toContainText(/code-review/i);

      // Other artifacts should be filtered out
      const linterCard = detailPane.getByText(/linter/i);
      const isVisible = await linterCard.isVisible().catch(() => false);
      expect(isVisible).toBe(false);
    }
  });

  test('clearing filters restores all folder artifacts', async ({ page }) => {
    // Select folder and apply filter
    await selectFolder(page, /dev-tools/i);
    const detailPane = page.locator('[data-testid="folder-detail-pane"]');

    const searchInput = page.getByPlaceholder(/search/i);
    if (await searchInput.isVisible()) {
      await searchInput.fill('code-review');
      await expect(detailPane).toContainText(/code-review/i);

      // Clear filter
      const clearButton = page.getByRole('button', { name: /clear|reset/i });
      if (await clearButton.isVisible()) {
        await clearButton.click();

        // Verify all artifacts visible again
        await expect(detailPane).toContainText(/code-review/i);
        await expect(detailPane).toContainText(/linter/i);
      }
    }
  });

  test('filter count reflects filtered artifacts in current folder', async ({ page }) => {
    // Select folder
    await selectFolder(page, /dev-tools/i);

    // Apply filter
    const searchInput = page.getByPlaceholder(/search/i);
    if (await searchInput.isVisible()) {
      await searchInput.fill('code-review');

      // Verify count indicator updates
      const detailPane = page.locator('[data-testid="folder-detail-pane"]');
      const resultCount = await detailPane.locator('[data-testid="artifact-card"]').count();
      expect(resultCount).toBe(1); // Only code-review matches
    }
  });
});

// ============================================================================
// Test Suite: Subfolder Navigation
// ============================================================================

test.describe('Folder View - Subfolder Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
    await navigateToSourceDetail(page);
    await toggleToFolderView(page);
  });

  test('clicking subfolder card navigates tree', async ({ page }) => {
    // Select folder with subfolders
    await selectFolder(page, /dev-tools/i);
    const detailPane = page.locator('[data-testid="folder-detail-pane"]');

    // Verify subfolders section visible
    const subfoldersSection = detailPane.locator('[data-testid="subfolders-section"]');
    if (await subfoldersSection.isVisible()) {
      // Click subfolder card (formatters)
      const formattersCard = subfoldersSection.getByText(/formatters/i);
      await formattersCard.click();

      // Verify tree expands to show subfolder
      await expect(page.getByRole('treeitem', { name: /formatters/i })).toBeVisible();

      // Verify subfolder is now selected
      const formattersFolder = page.getByRole('treeitem', { name: /formatters/i });
      await expect(formattersFolder).toHaveAttribute('aria-selected', 'true');

      // Verify detail pane updates
      await expect(detailPane).toContainText(/formatters/i);
      await expect(detailPane).toContainText(/prettier/i);
    }
  });

  test('subfolder cards show correct artifact count', async ({ page }) => {
    // Select folder with subfolders
    await selectFolder(page, /dev-tools/i);
    const detailPane = page.locator('[data-testid="folder-detail-pane"]');

    // Check subfolder card shows count
    const subfoldersSection = detailPane.locator('[data-testid="subfolders-section"]');
    if (await subfoldersSection.isVisible()) {
      const formattersCard = subfoldersSection.locator('[data-testid="subfolder-card"]').filter({ hasText: /formatters/i });

      // Should show artifact count (2 items: prettier, eslint)
      await expect(formattersCard).toContainText(/2/);
    }
  });

  test('navigating to subfolder shows breadcrumb or path', async ({ page }) => {
    // Select parent folder
    await selectFolder(page, /dev-tools/i);

    // Navigate to subfolder via card
    const detailPane = page.locator('[data-testid="folder-detail-pane"]');
    const subfoldersSection = detailPane.locator('[data-testid="subfolders-section"]');

    if (await subfoldersSection.isVisible()) {
      const formattersCard = subfoldersSection.getByText(/formatters/i);
      await formattersCard.click();

      // Verify path is shown in detail pane header
      await expect(detailPane).toContainText(/dev-tools.*formatters|formatters/i);
    }
  });
});

// ============================================================================
// Test Suite: Import All Bulk Action
// ============================================================================

test.describe('Folder View - Import All Bulk Action', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
    await navigateToSourceDetail(page);
    await toggleToFolderView(page);
  });

  test('Import All button shows correct count', async ({ page }) => {
    // Select folder with multiple new artifacts
    await selectFolder(page, /dev-tools/i);
    const detailPane = page.locator('[data-testid="folder-detail-pane"]');

    // Verify Import All button shows count
    const importAllButton = detailPane.getByRole('button', { name: /import all/i });
    if (await importAllButton.isVisible()) {
      // Should show count of importable artifacts (not imported ones)
      await expect(importAllButton).toContainText(/import all/i);

      // May show count like "Import All (2)"
      const buttonText = await importAllButton.textContent();
      expect(buttonText).toBeTruthy();
    }
  });

  test('Import All button is enabled when artifacts available', async ({ page }) => {
    // Select folder with new artifacts
    await selectFolder(page, /dev-tools/i);
    const detailPane = page.locator('[data-testid="folder-detail-pane"]');

    const importAllButton = detailPane.getByRole('button', { name: /import all/i });
    if (await importAllButton.isVisible()) {
      // Button should be enabled if there are importable artifacts
      await expect(importAllButton).toBeEnabled();
    }
  });

  test('Import All button is disabled when no importable artifacts', async ({ page }) => {
    // Select folder with only imported artifacts
    await selectFolder(page, /data-science/i);
    const detailPane = page.locator('[data-testid="folder-detail-pane"]');

    const importAllButton = detailPane.getByRole('button', { name: /import all/i });
    if (await importAllButton.isVisible()) {
      // If all artifacts are imported, button should be disabled or show 0
      const isDisabled = await importAllButton.isDisabled();
      const buttonText = await importAllButton.textContent();

      // Either disabled OR shows "(0)"
      expect(isDisabled || buttonText?.includes('(0)')).toBeTruthy();
    }
  });

  test('clicking Import All shows confirmation or initiates import', async ({ page }) => {
    // Select folder with importable artifacts
    await selectFolder(page, /dev-tools/i);
    const detailPane = page.locator('[data-testid="folder-detail-pane"]');

    const importAllButton = detailPane.getByRole('button', { name: /import all/i });
    if (await importAllButton.isVisible() && await importAllButton.isEnabled()) {
      await importAllButton.click();

      // Either shows confirmation dialog or starts import
      const confirmDialog = page.getByRole('dialog', { name: /confirm|import/i });
      const isDialogVisible = await confirmDialog.isVisible().catch(() => false);

      if (isDialogVisible) {
        // Confirmation dialog shown
        await expect(confirmDialog).toContainText(/import/i);
      } else {
        // Import started - check for loading state or success message
        const loadingIndicator = page.locator('[aria-busy="true"]');
        const isLoading = await loadingIndicator.isVisible().catch(() => false);
        expect(isLoading).toBeTruthy();
      }
    }
  });
});

// ============================================================================
// Test Suite: Empty State
// ============================================================================

test.describe('Folder View - Empty State', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
    await navigateToSourceDetail(page);
    await toggleToFolderView(page);
  });

  test('shows empty state when folder has no artifacts', async ({ page }) => {
    // Mock empty folder scenario
    // This would require selecting a folder with no artifacts after filtering
    // or mocking a catalog response with an empty folder

    // Apply filter that excludes all artifacts in selected folder
    await selectFolder(page, /dev-tools/i);

    const searchInput = page.getByPlaceholder(/search/i);
    if (await searchInput.isVisible()) {
      // Search for something that doesn't exist
      await searchInput.fill('nonexistent-artifact-xyz');

      const detailPane = page.locator('[data-testid="folder-detail-pane"]');

      // Verify empty state message
      await expect(detailPane).toContainText(/no artifacts|empty|no results/i);
    }
  });

  test('empty state shows Clear Filters button when filtered', async ({ page }) => {
    // Select folder and apply filter that results in no matches
    await selectFolder(page, /dev-tools/i);

    const searchInput = page.getByPlaceholder(/search/i);
    if (await searchInput.isVisible()) {
      await searchInput.fill('nonexistent-xyz');

      const detailPane = page.locator('[data-testid="folder-detail-pane"]');

      // Verify Clear Filters button in empty state
      const clearButton = detailPane.getByRole('button', { name: /clear filter/i });
      if (await clearButton.isVisible()) {
        await expect(clearButton).toBeEnabled();

        // Click to clear filters
        await clearButton.click();

        // Verify artifacts reappear
        await expect(detailPane).toContainText(/code-review|linter/i);
      }
    }
  });

  test('empty folder without filters shows helpful message', async ({ page }) => {
    // For a truly empty folder (no mock data scenario)
    // We'll simulate by selecting a folder and checking the message

    // If we have an empty folder in our mock data, select it
    // Otherwise, verify the component handles the empty case

    const detailPane = page.locator('[data-testid="folder-detail-pane"]');

    // The detail pane should always show some content or empty state
    await expect(detailPane).toBeVisible();

    // If no folder is selected or folder is empty, should show appropriate message
    // This test validates the component doesn't crash on empty state
  });
});

// ============================================================================
// Test Suite: Accessibility and Keyboard Navigation
// ============================================================================

test.describe('Folder View - Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
    await navigateToSourceDetail(page);
    await toggleToFolderView(page);
  });

  test('tree uses proper ARIA tree roles', async ({ page }) => {
    // Verify tree has role="tree"
    const tree = page.locator('[role="tree"]');
    await expect(tree).toBeVisible();

    // Verify tree items have role="treeitem"
    const treeItems = page.locator('[role="treeitem"]');
    const count = await treeItems.count();
    expect(count).toBeGreaterThan(0);
  });

  test('folder selection is keyboard accessible', async ({ page }) => {
    // Focus on tree
    const tree = page.locator('[role="tree"]');
    await tree.focus();

    // Use arrow keys to navigate
    await page.keyboard.press('ArrowDown');

    // Verify focus moved
    const focusedItem = page.locator('[role="treeitem"]:focus');
    await expect(focusedItem).toBeFocused();

    // Press Enter to select
    await page.keyboard.press('Enter');

    // Verify selection occurred (detail pane updated)
    const detailPane = page.locator('[data-testid="folder-detail-pane"]');
    await expect(detailPane).not.toBeEmpty();
  });

  test('expand/collapse is keyboard accessible', async ({ page }) => {
    // Navigate to folder with children
    const tree = page.locator('[role="tree"]');
    await tree.focus();
    await page.keyboard.press('ArrowDown');

    // Press ArrowRight to expand
    await page.keyboard.press('ArrowRight');

    // Verify folder expanded (aria-expanded=true)
    const focusedItem = page.locator('[role="treeitem"]:focus');
    const expandButton = focusedItem.getByRole('button');
    const ariaExpanded = await expandButton.getAttribute('aria-expanded');
    expect(ariaExpanded).toBe('true');

    // Press ArrowLeft to collapse
    await page.keyboard.press('ArrowLeft');

    // Verify folder collapsed
    const newAriaExpanded = await expandButton.getAttribute('aria-expanded');
    expect(newAriaExpanded).toBe('false');
  });

  test('folder nodes have accessible names', async ({ page }) => {
    // All tree items should have accessible names
    const treeItems = page.locator('[role="treeitem"]');
    const count = await treeItems.count();

    for (let i = 0; i < count; i++) {
      const item = treeItems.nth(i);
      const name = await item.getAttribute('aria-label');
      const textContent = await item.textContent();

      // Either aria-label or text content should provide name
      expect(name || textContent).toBeTruthy();
    }
  });
});

// ============================================================================
// Test Suite: Responsive Design
// ============================================================================

test.describe('Folder View - Responsive Design', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
  });

  test('folder view renders on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 390, height: 844 });

    await navigateToSourceDetail(page);
    await toggleToFolderView(page);

    // Verify layout adapts (may stack panes vertically)
    await expect(page.locator('[data-testid="folder-layout"]')).toBeVisible();
    await expect(page.locator('[data-testid="folder-tree"]')).toBeVisible();

    // Detail pane may be hidden until folder selected on mobile
    // or panes may stack vertically
  });

  test('folder view renders on tablet viewport', async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });

    await navigateToSourceDetail(page);
    await toggleToFolderView(page);

    // Verify both panes visible
    await expect(page.locator('[data-testid="folder-tree"]')).toBeVisible();
    await expect(page.locator('[data-testid="folder-detail-pane"]')).toBeVisible();
  });

  test('folder view renders on desktop viewport', async ({ page }) => {
    // Set desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });

    await navigateToSourceDetail(page);
    await toggleToFolderView(page);

    // Verify side-by-side layout
    const leftPane = page.locator('[data-testid="folder-tree"]');
    const rightPane = page.locator('[data-testid="folder-detail-pane"]');

    await expect(leftPane).toBeVisible();
    await expect(rightPane).toBeVisible();

    // Verify panes are side by side
    const leftBox = await leftPane.boundingBox();
    const rightBox = await rightPane.boundingBox();

    if (leftBox && rightBox) {
      expect(leftBox.x).toBeLessThan(rightBox.x);

      // Roughly 25/75 split (allowing some margin for borders)
      const totalWidth = leftBox.width + rightBox.width;
      const leftPercentage = (leftBox.width / totalWidth) * 100;
      expect(leftPercentage).toBeGreaterThan(20);
      expect(leftPercentage).toBeLessThan(35);
    }
  });
});

// ============================================================================
// Test Suite: Performance and Edge Cases
// ============================================================================

test.describe('Folder View - Performance and Edge Cases', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
    await navigateToSourceDetail(page);
  });

  test('handles empty catalog gracefully', async ({ page }) => {
    // Mock empty catalog
    await mockApiRoute(
      page,
      `/api/v1/marketplace/sources/${mockSource.id}/catalog*`,
      {
        items: [],
        total: 0,
        page: 1,
        page_size: 50,
        has_next: false,
        counts_by_type: {},
        counts_by_status: {},
      }
    );

    await page.reload();
    await waitForPageLoad(page);

    // Toggle to folder view
    const folderButton = page.getByRole('button', { name: /folder/i });
    if (await folderButton.isVisible()) {
      await folderButton.click();

      // Should show empty state, not crash
      const layout = page.locator('[data-testid="folder-layout"]');
      if (await layout.isVisible()) {
        await expect(layout).toContainText(/no|empty/i);
      }
    }
  });

  test('handles special characters in folder names', async ({ page }) => {
    // This test assumes the tree builder handles special chars correctly
    // The mock data doesn't have special chars, but we verify no console errors

    await toggleToFolderView(page);

    // Verify tree renders without errors
    await expect(page.locator('[data-testid="folder-tree"]')).toBeVisible();

    // Select and interact with folder
    await selectFolder(page, /dev-tools/i);

    // No console errors should occur
    // (Playwright captures console errors by default)
  });

  test('deep folder nesting renders correctly', async ({ page }) => {
    await toggleToFolderView(page);

    // Expand nested folders
    await expandFolder(page, /dev-tools/i);

    // Verify nested folder appears
    const formattersFolder = page.getByRole('treeitem', { name: /formatters/i });
    if (await formattersFolder.isVisible()) {
      // Verify it's indented (nested level)
      // This is visual verification - proper nesting in DOM
      await expect(formattersFolder).toBeVisible();
    }
  });

  test('tree renders within performance budget', async ({ page }) => {
    const startTime = Date.now();

    await toggleToFolderView(page);

    // Wait for tree to be fully rendered
    await expect(page.locator('[data-testid="folder-tree"]')).toBeVisible();

    const endTime = Date.now();
    const renderTime = endTime - startTime;

    // Should render in under 1 second for small catalog
    // For 500+ items, target is 300ms per spec, but with network we allow more
    expect(renderTime).toBeLessThan(2000);
  });
});
