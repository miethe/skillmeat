/**
 * E2E Tests for Marketplace Source Filtering (TEST-006)
 *
 * Tests the filtering functionality on the marketplace sources page
 * including artifact type, tags, and combined filter logic.
 *
 * Test Coverage:
 * - Artifact type filtering
 * - Tag filtering via filter bar
 * - Tag filtering via source card click
 * - Combined filters (AND logic)
 * - Clear filters functionality
 * - URL state synchronization
 */

import { test, expect, type Page } from '@playwright/test';
import {
  waitForPageLoad,
  mockApiRoute,
} from '../helpers/test-utils';

// ============================================================================
// Mock Data
// ============================================================================

const mockSourceSkillsOnly = {
  id: 'source-skills',
  owner: 'anthropics',
  repo_name: 'skills-repo',
  ref: 'main',
  root_hint: '',
  repo_url: 'https://github.com/anthropics/skills-repo',
  trust_level: 'official',
  artifact_count: 10,
  scan_status: 'success',
  last_sync_at: '2024-12-10T10:00:00Z',
  created_at: '2024-12-01T10:00:00Z',
  tags: ['official', 'skills', 'production'],
  counts_by_type: {
    skill: 10,
  },
};

const mockSourceMixed = {
  id: 'source-mixed',
  owner: 'community',
  repo_name: 'claude-tools',
  ref: 'main',
  root_hint: '',
  repo_url: 'https://github.com/community/claude-tools',
  trust_level: 'verified',
  artifact_count: 15,
  scan_status: 'success',
  last_sync_at: '2024-12-09T10:00:00Z',
  created_at: '2024-12-02T10:00:00Z',
  tags: ['community', 'tools', 'production'],
  counts_by_type: {
    skill: 5,
    command: 7,
    agent: 3,
  },
};

const mockSourceCommands = {
  id: 'source-commands',
  owner: 'devteam',
  repo_name: 'command-library',
  ref: 'develop',
  root_hint: '',
  repo_url: 'https://github.com/devteam/command-library',
  trust_level: 'basic',
  artifact_count: 8,
  scan_status: 'success',
  last_sync_at: '2024-12-08T10:00:00Z',
  created_at: '2024-12-03T10:00:00Z',
  tags: ['development', 'commands'],
  counts_by_type: {
    command: 8,
  },
};

const mockSourceProduction = {
  id: 'source-production',
  owner: 'enterprise',
  repo_name: 'prod-artifacts',
  ref: 'main',
  root_hint: '',
  repo_url: 'https://github.com/enterprise/prod-artifacts',
  trust_level: 'verified',
  artifact_count: 20,
  scan_status: 'success',
  last_sync_at: '2024-12-10T12:00:00Z',
  created_at: '2024-12-04T10:00:00Z',
  tags: ['production', 'enterprise'],
  counts_by_type: {
    skill: 12,
    agent: 5,
    mcp: 3,
  },
};

const mockSourcesList = {
  items: [mockSourceSkillsOnly, mockSourceMixed, mockSourceCommands, mockSourceProduction],
  total: 4,
  page: 1,
  page_size: 20,
  has_next: false,
};

// ============================================================================
// Helper Functions
// ============================================================================

async function setupMockApiRoutes(page: Page) {
  await mockApiRoute(page, '/api/v1/marketplace/sources*', mockSourcesList);
}

async function navigateToSourcesPage(page: Page) {
  await page.goto('/marketplace/sources');
  await waitForPageLoad(page);
}

// ============================================================================
// Test Suite: Artifact Type Filtering
// ============================================================================

test.describe('Artifact Type Filtering (TEST-006)', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
  });

  test('filters sources by skill artifact type', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Verify all sources are visible initially
    await expect(page.getByText('anthropics/skills-repo')).toBeVisible();
    await expect(page.getByText('community/claude-tools')).toBeVisible();
    await expect(page.getByText('devteam/command-library')).toBeVisible();
    await expect(page.getByText('enterprise/prod-artifacts')).toBeVisible();

    // Open artifact type filter dropdown
    const typeSelect = page.locator('#artifact-type-filter');
    await typeSelect.click();

    // Select Skills
    await page.getByRole('option', { name: 'Skills' }).click();

    // Verify only sources with skills are visible
    await expect(page.getByText('anthropics/skills-repo')).toBeVisible();
    await expect(page.getByText('community/claude-tools')).toBeVisible();
    await expect(page.getByText('enterprise/prod-artifacts')).toBeVisible();

    // Source with only commands should not be visible
    await expect(page.getByText('devteam/command-library')).not.toBeVisible();

    // Verify active filter is shown
    await expect(page.getByText('Type: skill')).toBeVisible();
  });

  test('filters sources by command artifact type', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Open artifact type filter dropdown
    const typeSelect = page.locator('#artifact-type-filter');
    await typeSelect.click();

    // Select Commands
    await page.getByRole('option', { name: 'Commands' }).click();

    // Verify only sources with commands are visible
    await expect(page.getByText('community/claude-tools')).toBeVisible();
    await expect(page.getByText('devteam/command-library')).toBeVisible();

    // Sources without commands should not be visible
    await expect(page.getByText('anthropics/skills-repo')).not.toBeVisible();
    await expect(page.getByText('enterprise/prod-artifacts')).not.toBeVisible();
  });

  test('clears artifact type filter', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Apply filter
    const typeSelect = page.locator('#artifact-type-filter');
    await typeSelect.click();
    await page.getByRole('option', { name: 'Commands' }).click();

    // Verify filter is active
    await expect(page.getByText('Type: command')).toBeVisible();

    // Clear the filter via the X button on the badge
    const clearTypeButton = page.locator('[aria-label="Remove artifact type filter: command"]');
    await clearTypeButton.click();

    // Verify all sources are visible again
    await expect(page.getByText('anthropics/skills-repo')).toBeVisible();
    await expect(page.getByText('community/claude-tools')).toBeVisible();
    await expect(page.getByText('devteam/command-library')).toBeVisible();
    await expect(page.getByText('enterprise/prod-artifacts')).toBeVisible();
  });
});

// ============================================================================
// Test Suite: Tag Filtering
// ============================================================================

test.describe('Tag Filtering', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
  });

  test('filters by clicking tag in filter bar', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Wait for filter bar to be populated with available tags
    await expect(page.getByText('Tags')).toBeVisible();

    // Click on 'production' tag in the filter bar
    const productionTagBadge = page.locator('[role="button"][aria-label*="Add tag filter: production"]');
    await productionTagBadge.click();

    // Verify filter is active (tag should now show as selected)
    await expect(productionTagBadge).toHaveAttribute('aria-pressed', 'true');

    // Verify active filter badge is shown
    await expect(page.getByText('production').first()).toBeVisible();

    // Verify only sources with 'production' tag are visible
    await expect(page.getByText('anthropics/skills-repo')).toBeVisible();
    await expect(page.getByText('community/claude-tools')).toBeVisible();
    await expect(page.getByText('enterprise/prod-artifacts')).toBeVisible();

    // Source without 'production' tag should not be visible
    await expect(page.getByText('devteam/command-library')).not.toBeVisible();
  });

  test('filters by clicking tag on source card', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Find a source card and click on one of its tags
    // The 'official' tag only exists on skills-repo
    const officialTagOnCard = page.locator('[role="listitem"]').first().getByText('official');
    await officialTagOnCard.click();

    // Verify filter is applied
    await expect(page.locator('[aria-pressed="true"]').getByText('official')).toBeVisible();

    // Only skills-repo has the 'official' tag
    await expect(page.getByText('anthropics/skills-repo')).toBeVisible();

    // Other sources should not be visible
    await expect(page.getByText('community/claude-tools')).not.toBeVisible();
    await expect(page.getByText('devteam/command-library')).not.toBeVisible();
    await expect(page.getByText('enterprise/prod-artifacts')).not.toBeVisible();
  });

  test('combines multiple tag filters with AND logic', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Apply first tag filter: 'production'
    const productionTag = page.locator('[role="button"][aria-label*="Add tag filter: production"]');
    await productionTag.click();

    // Verify multiple sources with 'production' tag are visible
    await expect(page.getByText('anthropics/skills-repo')).toBeVisible();
    await expect(page.getByText('community/claude-tools')).toBeVisible();

    // Apply second tag filter: 'skills'
    const skillsTag = page.locator('[role="button"][aria-label*="Add tag filter: skills"]');
    if (await skillsTag.isVisible()) {
      await skillsTag.click();

      // Only sources with BOTH 'production' AND 'skills' should be visible
      await expect(page.getByText('anthropics/skills-repo')).toBeVisible();

      // Source with only 'production' but not 'skills' should not be visible
      await expect(page.getByText('community/claude-tools')).not.toBeVisible();
    }
  });

  test('removes tag filter by clicking selected tag', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Apply tag filter
    const productionTag = page.locator('[role="button"][aria-label*="Add tag filter: production"]');
    await productionTag.click();

    // Verify filter is active
    await expect(productionTag).toHaveAttribute('aria-pressed', 'true');

    // Click the same tag again to remove filter
    await productionTag.click();

    // Verify filter is removed
    await expect(productionTag).toHaveAttribute('aria-pressed', 'false');

    // All sources should be visible again
    await expect(page.getByText('devteam/command-library')).toBeVisible();
  });

  test('removes tag filter via active filter badge X button', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Apply tag filter
    const productionTag = page.locator('[role="button"][aria-label*="Add tag filter: production"]');
    await productionTag.click();

    // Verify active filters section shows the tag
    await expect(page.getByText('Active filters:')).toBeVisible();

    // Click X on the active filter badge
    const removeTagButton = page.locator('[aria-label="Remove tag filter: production"]');
    await removeTagButton.click();

    // Verify all sources are visible again
    await expect(page.getByText('devteam/command-library')).toBeVisible();
  });
});

// ============================================================================
// Test Suite: Combined Filters
// ============================================================================

test.describe('Combined Filters', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
  });

  test('combines artifact type and tag filters', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Apply artifact type filter: skill
    const typeSelect = page.locator('#artifact-type-filter');
    await typeSelect.click();
    await page.getByRole('option', { name: 'Skills' }).click();

    // Apply tag filter: production
    const productionTag = page.locator('[role="button"][aria-label*="Add tag filter: production"]');
    await productionTag.click();

    // Verify active filters show both
    await expect(page.getByText('Type: skill')).toBeVisible();
    await expect(page.locator('[aria-pressed="true"]').getByText('production')).toBeVisible();

    // Only sources with skills AND production tag should be visible
    await expect(page.getByText('anthropics/skills-repo')).toBeVisible();
    await expect(page.getByText('community/claude-tools')).toBeVisible();
    await expect(page.getByText('enterprise/prod-artifacts')).toBeVisible();

    // Source without skills should not be visible
    await expect(page.getByText('devteam/command-library')).not.toBeVisible();
  });

  test('shows correct filter count', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Apply artifact type filter
    const typeSelect = page.locator('#artifact-type-filter');
    await typeSelect.click();
    await page.getByRole('option', { name: 'Skills' }).click();

    // Verify 1 filter active
    await expect(page.getByText('(1 filter)')).toBeVisible();

    // Apply tag filter
    const productionTag = page.locator('[role="button"][aria-label*="Add tag filter: production"]');
    await productionTag.click();

    // Verify 2 filters active
    await expect(page.getByText('(2 filters)')).toBeVisible();
  });
});

// ============================================================================
// Test Suite: Clear Filters
// ============================================================================

test.describe('Clear Filters', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
  });

  test('clears all filters with Clear Filters button', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Apply multiple filters
    const typeSelect = page.locator('#artifact-type-filter');
    await typeSelect.click();
    await page.getByRole('option', { name: 'Commands' }).click();

    const productionTag = page.locator('[role="button"][aria-label*="Add tag filter: production"]');
    if (await productionTag.isVisible()) {
      await productionTag.click();
    }

    // Verify filtered state
    await expect(page.getByText('devteam/command-library')).not.toBeVisible();

    // Click Clear Filters button
    const clearButton = page.getByRole('button', { name: /Clear Filters/i });
    await clearButton.click();

    // Verify all sources reappear
    await expect(page.getByText('anthropics/skills-repo')).toBeVisible();
    await expect(page.getByText('community/claude-tools')).toBeVisible();
    await expect(page.getByText('devteam/command-library')).toBeVisible();
    await expect(page.getByText('enterprise/prod-artifacts')).toBeVisible();

    // Verify active filters section is hidden
    await expect(page.getByText('Active filters:')).not.toBeVisible();
  });

  test('clears all filters with Clear all button in filter bar', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Apply filter
    const typeSelect = page.locator('#artifact-type-filter');
    await typeSelect.click();
    await page.getByRole('option', { name: 'Skills' }).click();

    // Verify Clear all button appears
    const clearAllButton = page.getByRole('button', { name: /Clear all/i });
    await expect(clearAllButton).toBeVisible();

    // Click Clear all
    await clearAllButton.click();

    // Verify filters are cleared
    await expect(page.getByText('Active filters:')).not.toBeVisible();
  });

  test('Clear Filters button only appears when filters are active', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Verify Clear Filters button is not visible initially
    const clearButton = page.getByRole('button', { name: /Clear Filters/i });
    await expect(clearButton).not.toBeVisible();

    // Apply a filter
    const typeSelect = page.locator('#artifact-type-filter');
    await typeSelect.click();
    await page.getByRole('option', { name: 'Skills' }).click();

    // Verify Clear Filters button appears
    await expect(clearButton).toBeVisible();

    // Clear the filter
    await clearButton.click();

    // Verify button disappears again
    await expect(clearButton).not.toBeVisible();
  });
});

// ============================================================================
// Test Suite: Search Combined with Filters
// ============================================================================

test.describe('Search and Filters', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
  });

  test('combines search query with filters', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Enter search query
    const searchInput = page.getByPlaceholder('Search repositories...');
    await searchInput.fill('anthropics');

    // Verify only matching sources are shown
    await expect(page.getByText('anthropics/skills-repo')).toBeVisible();
    await expect(page.getByText('community/claude-tools')).not.toBeVisible();

    // Apply artifact type filter
    const typeSelect = page.locator('#artifact-type-filter');
    await typeSelect.click();
    await page.getByRole('option', { name: 'Skills' }).click();

    // Results should still show anthropics/skills-repo (has skills and matches search)
    await expect(page.getByText('anthropics/skills-repo')).toBeVisible();
  });

  test('clears search with X button inside input', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Enter search query
    const searchInput = page.getByPlaceholder('Search repositories...');
    await searchInput.fill('anthropics');

    // Verify filtered results
    await expect(page.getByText('anthropics/skills-repo')).toBeVisible();
    await expect(page.getByText('community/claude-tools')).not.toBeVisible();

    // Click clear search button
    const clearSearchButton = page.locator('[aria-label="Clear search"]');
    await clearSearchButton.click();

    // Verify all sources reappear
    await expect(page.getByText('community/claude-tools')).toBeVisible();
    await expect(page.getByText('devteam/command-library')).toBeVisible();
  });
});

// ============================================================================
// Test Suite: URL State
// ============================================================================

test.describe('URL State Synchronization', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
  });

  test('persists filters in URL', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Apply artifact type filter
    const typeSelect = page.locator('#artifact-type-filter');
    await typeSelect.click();
    await page.getByRole('option', { name: 'Skills' }).click();

    // Verify URL contains filter parameter
    await expect(page).toHaveURL(/artifact_type=skill/);
  });

  test('restores filters from URL on page load', async ({ page }) => {
    // Navigate with filter in URL
    await page.goto('/marketplace/sources?artifact_type=command');
    await waitForPageLoad(page);

    // Verify filter is applied
    await expect(page.getByText('Type: command')).toBeVisible();

    // Verify filtered results
    await expect(page.getByText('community/claude-tools')).toBeVisible();
    await expect(page.getByText('devteam/command-library')).toBeVisible();
    await expect(page.getByText('anthropics/skills-repo')).not.toBeVisible();
  });

  test('restores tag filters from URL', async ({ page }) => {
    // Navigate with tag filter in URL
    await page.goto('/marketplace/sources?tags=production');
    await waitForPageLoad(page);

    // Verify tag filter is applied
    await expect(page.locator('[aria-pressed="true"]').getByText('production')).toBeVisible();

    // Verify filtered results
    await expect(page.getByText('anthropics/skills-repo')).toBeVisible();
    await expect(page.getByText('devteam/command-library')).not.toBeVisible();
  });

  test('restores multiple filters from URL', async ({ page }) => {
    // Navigate with multiple filters in URL
    await page.goto('/marketplace/sources?artifact_type=skill&tags=production');
    await waitForPageLoad(page);

    // Verify both filters are applied
    await expect(page.getByText('Type: skill')).toBeVisible();
    await expect(page.locator('[aria-pressed="true"]').getByText('production')).toBeVisible();
  });
});

// ============================================================================
// Test Suite: Empty States
// ============================================================================

test.describe('Empty States', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
  });

  test('shows empty state when no sources match filters', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Apply filter that matches no sources
    const typeSelect = page.locator('#artifact-type-filter');
    await typeSelect.click();
    await page.getByRole('option', { name: 'Hooks' }).click();

    // Verify empty state message
    await expect(page.getByText('No matching sources')).toBeVisible();
    await expect(
      page.getByText(/No sources match your current search and filter criteria/i)
    ).toBeVisible();

    // Verify Clear All Filters button in empty state
    const clearButton = page.getByRole('button', { name: 'Clear All Filters' });
    await expect(clearButton).toBeVisible();
  });

  test('clears filters from empty state', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Apply filter that matches no sources
    const typeSelect = page.locator('#artifact-type-filter');
    await typeSelect.click();
    await page.getByRole('option', { name: 'Hooks' }).click();

    // Verify empty state
    await expect(page.getByText('No matching sources')).toBeVisible();

    // Click Clear All Filters in empty state
    const clearButton = page.getByRole('button', { name: 'Clear All Filters' });
    await clearButton.click();

    // Verify sources reappear
    await expect(page.getByText('anthropics/skills-repo')).toBeVisible();
  });
});
