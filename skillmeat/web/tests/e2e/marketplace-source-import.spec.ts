/**
 * E2E Tests for Marketplace Source Import (TEST-005)
 *
 * Tests the complete user journey for adding a new GitHub source
 * with repo metadata import options and tags.
 *
 * Test Coverage:
 * - Add source modal workflow
 * - Repo description toggle
 * - README import toggle
 * - Tag management (add, remove, validation)
 * - Form submission and verification
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

const mockSourceWithMetadata = {
  id: 'source-new-123',
  owner: 'anthropics',
  repo_name: 'claude-artifacts',
  ref: 'main',
  root_hint: '',
  repo_url: 'https://github.com/anthropics/claude-artifacts',
  trust_level: 'basic',
  artifact_count: 8,
  scan_status: 'success',
  last_sync_at: '2024-12-10T14:00:00Z',
  created_at: '2024-12-10T14:00:00Z',
  description: 'User-added description',
  repo_description: 'Official Claude artifacts repository',
  readme_content: '# Claude Artifacts\n\nThis is the README content.',
  tags: ['official', 'claude', 'artifacts'],
  counts_by_type: {
    skill: 5,
    command: 2,
    agent: 1,
  },
};

const mockEmptySourcesList = {
  items: [],
  total: 0,
  page: 1,
  page_size: 20,
  has_next: false,
};

const mockSourcesListWithNew = {
  items: [mockSourceWithMetadata],
  total: 1,
  page: 1,
  page_size: 20,
  has_next: false,
};

const mockInferResult = {
  success: true,
  repo_url: 'https://github.com/anthropics/claude-artifacts',
  ref: 'main',
  root_hint: '',
};

// ============================================================================
// Helper Functions
// ============================================================================

async function setupMockApiRoutes(page: Page) {
  // Mock empty sources list initially
  await mockApiRoute(page, '/api/v1/marketplace/sources*', mockEmptySourcesList);

  // Mock URL inference
  await mockApiRoute(page, '/api/v1/marketplace/infer-url', mockInferResult);

  // Mock create source (POST)
  await page.route('**/api/v1/marketplace/sources', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify(mockSourceWithMetadata),
      });
    } else {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockSourcesListWithNew),
      });
    }
  });
}

async function navigateToSourcesPage(page: Page) {
  await page.goto('/marketplace/sources');
  await waitForPageLoad(page);
}

async function openAddSourceModal(page: Page) {
  // Click Add Source button - try both Add Source and Add Your First Source
  const addButton = page.getByRole('button', { name: /Add Source/i }).or(
    page.getByRole('button', { name: /Add Your First Source/i })
  );
  await addButton.first().click();
  await expectModalOpen(page, '[role="dialog"]');
}

// ============================================================================
// Test Suite: Source Import Workflow
// ============================================================================

test.describe('Marketplace Source Import (TEST-005)', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
  });

  test('completes full source import flow with metadata options and tags', async ({ page }) => {
    await navigateToSourcesPage(page);

    // Step 1: Open Add Source modal
    await openAddSourceModal(page);
    await expect(page.getByRole('dialog')).toContainText('Add GitHub Source');

    // Step 2: Enter repository URL in quick import section
    const quickImportInput = page.locator('#quick-import-url');
    await quickImportInput.fill('https://github.com/anthropics/claude-artifacts');

    // Wait for URL inference to complete (debounced)
    await page.waitForTimeout(500);

    // Verify the manual entry fields are auto-populated
    await expect(page.locator('#repo-url')).toHaveValue('https://github.com/anthropics/claude-artifacts');
    await expect(page.locator('#ref')).toHaveValue('main');

    // Step 3: Enable "Import repo description" toggle
    const descriptionToggle = page.locator('#import-repo-description');
    await descriptionToggle.click();
    await expect(descriptionToggle).toBeChecked();

    // Step 4: Enable "Import README" toggle
    const readmeToggle = page.locator('#import-repo-readme');
    await readmeToggle.click();
    await expect(readmeToggle).toBeChecked();

    // Step 5: Add tags using the tag input
    const tagInput = page.locator('#tags');

    // Add first tag
    await tagInput.fill('official');
    await tagInput.press('Enter');
    await expect(page.getByText('official').first()).toBeVisible();

    // Add second tag
    await tagInput.fill('claude');
    await tagInput.press(',');
    await expect(page.getByText('claude').first()).toBeVisible();

    // Add third tag
    await tagInput.fill('artifacts');
    await tagInput.press('Enter');
    await expect(page.getByText('artifacts').first()).toBeVisible();

    // Verify tag count display
    await expect(page.getByText('3/20 tags')).toBeVisible();

    // Step 6: Submit the form
    const submitButton = page.getByRole('button', { name: 'Add Source' }).last();
    await submitButton.click();

    // Step 7: Verify modal closes
    await expectModalClosed(page, '[role="dialog"]');

    // Update mock to return the new source
    await mockApiRoute(page, '/api/v1/marketplace/sources*', mockSourcesListWithNew);

    // Verify source appears in list with tags and repo details
    await expect(page.getByText('anthropics/claude-artifacts')).toBeVisible();
  });

  test('adds tags via quick import section', async ({ page }) => {
    await navigateToSourcesPage(page);
    await openAddSourceModal(page);

    // Fill in URL
    const repoUrlInput = page.locator('#repo-url');
    await repoUrlInput.fill('https://github.com/anthropics/claude-artifacts');

    // Scroll to tags section
    const tagInput = page.locator('#tags');
    await tagInput.scrollIntoViewIfNeeded();

    // Add tags
    await tagInput.fill('test-tag');
    await tagInput.press('Enter');

    // Verify tag appears as badge
    const tagBadge = page.locator('text=test-tag').first();
    await expect(tagBadge).toBeVisible();

    // Verify remove button appears
    const removeButton = page.getByRole('button', { name: /Remove tag test-tag/i });
    await expect(removeButton).toBeVisible();
  });

  test('removes tags with X button', async ({ page }) => {
    await navigateToSourcesPage(page);
    await openAddSourceModal(page);

    const tagInput = page.locator('#tags');

    // Add a tag
    await tagInput.fill('removable-tag');
    await tagInput.press('Enter');
    await expect(page.getByText('removable-tag').first()).toBeVisible();

    // Click remove button
    const removeButton = page.getByRole('button', { name: /Remove tag removable-tag/i });
    await removeButton.click();

    // Verify tag is removed
    await expect(page.getByText('removable-tag')).not.toBeVisible();
  });

  test('removes last tag with backspace on empty input', async ({ page }) => {
    await navigateToSourcesPage(page);
    await openAddSourceModal(page);

    const tagInput = page.locator('#tags');

    // Add two tags
    await tagInput.fill('first-tag');
    await tagInput.press('Enter');
    await tagInput.fill('second-tag');
    await tagInput.press('Enter');

    // Verify both tags exist
    await expect(page.getByText('first-tag').first()).toBeVisible();
    await expect(page.getByText('second-tag').first()).toBeVisible();

    // Press backspace on empty input to remove last tag
    await tagInput.press('Backspace');
    await expect(page.getByText('second-tag')).not.toBeVisible();

    // First tag should still be visible
    await expect(page.getByText('first-tag').first()).toBeVisible();
  });

  test('shows validation error for invalid tag format', async ({ page }) => {
    await navigateToSourcesPage(page);
    await openAddSourceModal(page);

    const tagInput = page.locator('#tags');

    // Try to add tag starting with special character
    await tagInput.fill('_invalid');
    await tagInput.press('Enter');

    // Verify error message
    await expect(
      page.getByText(/Tag must start with alphanumeric/i)
    ).toBeVisible();
  });

  test('shows error for duplicate tag', async ({ page }) => {
    await navigateToSourcesPage(page);
    await openAddSourceModal(page);

    const tagInput = page.locator('#tags');

    // Add a tag
    await tagInput.fill('unique-tag');
    await tagInput.press('Enter');

    // Try to add the same tag again
    await tagInput.fill('unique-tag');
    await tagInput.press('Enter');

    // Verify error message
    await expect(page.getByText('Tag already added')).toBeVisible();
  });

  test('enforces maximum tag limit', async ({ page }) => {
    await navigateToSourcesPage(page);
    await openAddSourceModal(page);

    const tagInput = page.locator('#tags');

    // Add 20 tags (max limit)
    for (let i = 1; i <= 20; i++) {
      await tagInput.fill(`tag${i}`);
      await tagInput.press('Enter');
      await page.waitForTimeout(50); // Small delay for state update
    }

    // Verify tag count shows max
    await expect(page.getByText('20/20 tags')).toBeVisible();

    // Input should be disabled
    await expect(tagInput).toBeDisabled();

    // Try to add one more
    await tagInput.fill('extra-tag', { force: true });
    await tagInput.press('Enter');

    // Should show max tags error
    await expect(page.getByText(/Maximum 20 tags allowed/i)).toBeVisible();
  });

  test('enables frontmatter detection toggle', async ({ page }) => {
    await navigateToSourcesPage(page);
    await openAddSourceModal(page);

    // Find and enable frontmatter detection
    const frontmatterToggle = page.locator('#frontmatter-detection');
    await expect(frontmatterToggle).not.toBeChecked();

    await frontmatterToggle.click();
    await expect(frontmatterToggle).toBeChecked();
  });

  test('selects different trust levels', async ({ page }) => {
    await navigateToSourcesPage(page);
    await openAddSourceModal(page);

    // Open trust level dropdown
    const trustSelect = page.getByRole('combobox').last();
    await trustSelect.click();

    // Verify options are available
    await expect(page.getByRole('option', { name: 'Basic' })).toBeVisible();
    await expect(page.getByRole('option', { name: 'Verified' })).toBeVisible();
    await expect(page.getByRole('option', { name: 'Official' })).toBeVisible();

    // Select Official
    await page.getByRole('option', { name: 'Official' }).click();
  });

  test('submits source via quick import button', async ({ page }) => {
    await navigateToSourcesPage(page);
    await openAddSourceModal(page);

    // Fill quick import URL
    const quickImportInput = page.locator('#quick-import-url');
    await quickImportInput.fill('https://github.com/anthropics/claude-artifacts');

    // Wait for inference
    await page.waitForTimeout(500);

    // Click the first Add Source button (quick import)
    const quickImportButton = page.getByRole('button', { name: 'Add Source' }).first();
    await quickImportButton.click();

    // Verify modal closes on success
    await expectModalClosed(page, '[role="dialog"]');
  });

  test('displays tooltips for settings toggles', async ({ page }) => {
    await navigateToSourcesPage(page);
    await openAddSourceModal(page);

    // Scroll to make sure settings are visible
    const settingsSection = page.getByText('Settings').first();
    await settingsSection.scrollIntoViewIfNeeded();

    // Hover over frontmatter detection help icon
    const helpIcons = page.locator('svg.lucide-help-circle');
    await helpIcons.first().hover();

    // Verify tooltip appears
    await expect(
      page.getByText(/markdown files will be scanned for YAML frontmatter/i)
    ).toBeVisible();
  });

  test('closes modal with Cancel button', async ({ page }) => {
    await navigateToSourcesPage(page);
    await openAddSourceModal(page);

    // Click Cancel button
    await page.getByRole('button', { name: 'Cancel' }).click();

    // Verify modal closes
    await expectModalClosed(page, '[role="dialog"]');
  });

  test('closes modal with Escape key', async ({ page }) => {
    await navigateToSourcesPage(page);
    await openAddSourceModal(page);

    // Press Escape
    await pressKey(page, 'Escape');

    // Verify modal closes
    await expectModalClosed(page, '[role="dialog"]');
  });
});

// ============================================================================
// Test Suite: URL Inference
// ============================================================================

test.describe('URL Inference', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
  });

  test('auto-populates fields from pasted URL', async ({ page }) => {
    await navigateToSourcesPage(page);
    await openAddSourceModal(page);

    // Paste URL in quick import
    const quickImportInput = page.locator('#quick-import-url');
    await quickImportInput.fill('https://github.com/anthropics/claude-artifacts/tree/develop/skills');

    // Mock updated inference result
    await mockApiRoute(page, '/api/v1/marketplace/infer-url', {
      success: true,
      repo_url: 'https://github.com/anthropics/claude-artifacts',
      ref: 'develop',
      root_hint: 'skills',
    });

    // Wait for debounced inference
    await page.waitForTimeout(500);

    // Verify fields are populated
    await expect(page.locator('#repo-url')).toHaveValue('https://github.com/anthropics/claude-artifacts');
  });

  test('shows loading indicator during URL inference', async ({ page }) => {
    // Mock slow inference
    await page.route('**/api/v1/marketplace/infer-url', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockInferResult),
      });
    });

    await navigateToSourcesPage(page);
    await openAddSourceModal(page);

    // Enter URL
    const quickImportInput = page.locator('#quick-import-url');
    await quickImportInput.fill('https://github.com/anthropics/test');

    // Verify loading indicator appears
    await expect(page.getByText('Analyzing URL...')).toBeVisible();
  });

  test('shows error for invalid URL format', async ({ page }) => {
    await navigateToSourcesPage(page);
    await openAddSourceModal(page);

    // Enter invalid URL in manual entry
    const repoUrlInput = page.locator('#repo-url');
    await repoUrlInput.fill('not-a-valid-url');

    // Verify validation error
    await expect(
      page.getByText('Enter a valid GitHub URL (https://github.com/owner/repo)')
    ).toBeVisible();

    // Verify submit button is disabled
    const submitButton = page.getByRole('button', { name: 'Add Source' }).last();
    await expect(submitButton).toBeDisabled();
  });
});
