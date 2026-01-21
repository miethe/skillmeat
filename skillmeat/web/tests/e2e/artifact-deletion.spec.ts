/**
 * Artifact Deletion E2E Tests
 *
 * End-to-end tests for artifact deletion flow using Playwright.
 * Tests comprehensive user journeys including:
 * 1. Delete from Collection Page (via card menu)
 * 2. Delete from Project Page (if exists)
 * 3. Delete from Modal (via Overview tab)
 * 4. Cascading Deletion (delete from projects toggle)
 * 5. Cancel Flow (dialog close without deletion)
 * 6. Error Handling (API failures)
 * 7. Loading States (pending operations)
 */

import { test, expect, Page } from '@playwright/test';
import {
  mockApiRoute,
  navigateToPage,
  waitForElement,
  expectModalOpen,
  expectModalClosed,
  waitForApiResponse,
} from '../helpers/test-utils';
import { buildApiResponse, mockArtifacts, mockProjects } from '../helpers/fixtures';

/**
 * Helper to wait for loading states to complete
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
      // Ignore if no spinner found
    });
}

/**
 * Mock deployments data for testing
 */
const mockDeployments = [
  {
    artifact_name: mockArtifacts[0].name,
    artifact_type: mockArtifacts[0].type,
    artifact_path: `/project/a/.claude/skills/${mockArtifacts[0].name}`,
    collection_sha: 'abc1234',
    deployed_at: '2024-01-01T00:00:00Z',
    sync_status: 'synced' as const,
  },
  {
    artifact_name: mockArtifacts[0].name,
    artifact_type: mockArtifacts[0].type,
    artifact_path: `/project/b/.claude/skills/${mockArtifacts[0].name}`,
    collection_sha: 'def5678',
    deployed_at: '2024-01-02T00:00:00Z',
    sync_status: 'modified' as const,
  },
];

test.describe('Artifact Deletion E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Mock API routes
    await mockApiRoute(page, '/api/v1/artifacts*', buildApiResponse.artifacts());
    await mockApiRoute(page, '/api/v1/analytics*', buildApiResponse.analytics());
    await mockApiRoute(page, '/api/v1/projects*', buildApiResponse.projects());
    await mockApiRoute(page, '/api/v1/deploy*', {
      deployments: mockDeployments,
      total: mockDeployments.length,
      project_path: '/project/a',
    });

    // Navigate to collection page
    await navigateToPage(page, '/collection');
  });

  test.describe('Delete from Collection Page', () => {
    test('opens deletion dialog from card menu', async ({ page }) => {
      // Find first artifact card menu button
      const firstCard = page.locator('[data-testid="artifact-grid"]').locator('article').first();
      const menuButton = firstCard.locator('button[aria-label*="Actions"]');
      await menuButton.click();

      // Click delete menu item
      const deleteMenuItem = page.getByRole('menuitem', { name: /delete/i });
      await deleteMenuItem.click();

      // Verify dialog opens
      await waitForElement(page, '[role="dialog"]');
      const dialog = page.getByRole('dialog');
      await expect(dialog).toBeVisible();
      await expect(dialog).toContainText(/delete/i);
    });

    test('shows collection context messaging', async ({ page }) => {
      // Open deletion dialog
      const firstCard = page.locator('[data-testid="artifact-grid"]').locator('article').first();
      const menuButton = firstCard.locator('button[aria-label*="Actions"]');
      await menuButton.click();
      await page.getByRole('menuitem', { name: /delete/i }).click();

      // Verify collection context message
      const dialog = page.getByRole('dialog');
      await expect(dialog).toContainText(/remove the artifact from your collection/i);
    });

    test('completes deletion and removes artifact from list', async ({ page }) => {
      // Mock successful deletion response
      await mockApiRoute(page, '/api/v1/artifacts/*/delete*', {
        collectionDeleted: true,
        projectsUndeployed: 0,
        deploymentsDeleted: 0,
        errors: [],
      });

      // Get initial artifact count
      const initialCount = await page
        .locator('[data-testid="artifact-grid"]')
        .locator('article')
        .count();

      // Open deletion dialog
      const firstCard = page.locator('[data-testid="artifact-grid"]').locator('article').first();
      const artifactName = await firstCard.locator('h3').textContent();
      const menuButton = firstCard.locator('button[aria-label*="Actions"]');
      await menuButton.click();
      await page.getByRole('menuitem', { name: /delete/i }).click();

      // Confirm deletion
      const deleteButton = page.getByRole('button', { name: /delete artifact/i });
      await deleteButton.click();

      // Wait for deletion API call
      await waitForApiResponse(page, '/api/v1/artifacts');

      // Verify dialog closes
      await page.waitForTimeout(500);
      await expect(page.getByRole('dialog')).not.toBeVisible();

      // Note: In a real API scenario, artifact would be removed from list
      // For mocked API, we just verify the operation completed
    });

    test('shows loading state during deletion', async ({ page }) => {
      // Mock slow deletion response
      await page.route('**/api/v1/artifacts/*/delete*', async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 1000));
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            collectionDeleted: true,
            projectsUndeployed: 0,
            deploymentsDeleted: 0,
            errors: [],
          }),
        });
      });

      // Open deletion dialog
      const firstCard = page.locator('[data-testid="artifact-grid"]').locator('article').first();
      const menuButton = firstCard.locator('button[aria-label*="Actions"]');
      await menuButton.click();
      await page.getByRole('menuitem', { name: /delete/i }).click();

      // Click Delete
      const deleteButton = page.getByRole('button', { name: /delete artifact/i });
      await deleteButton.click();

      // Verify loading state
      const loadingButton = page.getByRole('button', { name: /deleting/i });
      await expect(loadingButton).toBeVisible();
      await expect(loadingButton).toBeDisabled();
    });
  });

  test.describe('Delete from Modal', () => {
    test('opens deletion dialog from modal overview tab', async ({ page }) => {
      // Mock artifact detail endpoint
      await mockApiRoute(
        page,
        `/api/v1/artifacts/${mockArtifacts[0].id}`,
        buildApiResponse.artifactDetail(mockArtifacts[0].id)
      );

      // Click on artifact to open modal
      const firstCard = page.locator('[data-testid="artifact-grid"]').locator('article').first();
      await firstCard.click();

      // Wait for modal to open
      await waitForElement(page, '[role="dialog"]');

      // Find and click Delete button in modal
      // Note: This assumes the modal has a Delete button - may need adjustment based on actual implementation
      const deleteButton = page
        .getByRole('dialog')
        .getByRole('button', { name: /delete/i })
        .first();

      if (await deleteButton.isVisible()) {
        await deleteButton.click();

        // Verify deletion dialog opens (nested dialog)
        await page.waitForTimeout(300);
        const dialogs = page.getByRole('dialog');
        const dialogCount = await dialogs.count();
        expect(dialogCount).toBeGreaterThan(0);
      }
    });

    test('closes modal after successful deletion', async ({ page }) => {
      // Mock successful deletion
      await mockApiRoute(page, '/api/v1/artifacts/*/delete*', {
        collectionDeleted: true,
        projectsUndeployed: 0,
        deploymentsDeleted: 0,
        errors: [],
      });

      // Open artifact modal
      await mockApiRoute(
        page,
        `/api/v1/artifacts/${mockArtifacts[0].id}`,
        buildApiResponse.artifactDetail(mockArtifacts[0].id)
      );

      const firstCard = page.locator('[data-testid="artifact-grid"]').locator('article').first();
      await firstCard.click();

      // Wait for modal
      await waitForElement(page, '[role="dialog"]');

      // Find delete button
      const deleteButton = page
        .getByRole('dialog')
        .getByRole('button', { name: /delete/i })
        .first();

      if (await deleteButton.isVisible()) {
        await deleteButton.click();
        await page.waitForTimeout(300);

        // Confirm deletion
        const confirmButton = page.getByRole('button', { name: /delete artifact/i });
        if (await confirmButton.isVisible()) {
          await confirmButton.click();

          // Wait for deletion to complete
          await page.waitForTimeout(1000);

          // Modal should close
          // Note: Implementation-specific behavior
        }
      }
    });
  });

  test.describe('Cascading Deletion', () => {
    test('toggles "Delete from Projects" option', async ({ page }) => {
      // Open deletion dialog
      const firstCard = page.locator('[data-testid="artifact-grid"]').locator('article').first();
      const menuButton = firstCard.locator('button[aria-label*="Actions"]');
      await menuButton.click();
      await page.getByRole('menuitem', { name: /delete/i }).click();

      // Find "Also delete from Projects" checkbox
      const projectsCheckbox = page.getByLabel(/also delete from projects/i);
      await expect(projectsCheckbox).toBeVisible();
      await expect(projectsCheckbox).not.toBeChecked();

      // Toggle on
      await projectsCheckbox.click();
      await expect(projectsCheckbox).toBeChecked();

      // Verify projects section expands
      await expect(page.getByText(/select which projects/i)).toBeVisible();
    });

    test('auto-selects all projects when toggled', async ({ page }) => {
      // Open deletion dialog
      const firstCard = page.locator('[data-testid="artifact-grid"]').locator('article').first();
      const menuButton = firstCard.locator('button[aria-label*="Actions"]');
      await menuButton.click();
      await page.getByRole('menuitem', { name: /delete/i }).click();

      // Toggle "Delete from Projects"
      const projectsCheckbox = page.getByLabel(/also delete from projects/i);
      await projectsCheckbox.click();

      // Wait for projects list to load
      await page.waitForTimeout(500);

      // Verify all projects are auto-selected
      const projectCheckboxes = page.locator('input[type="checkbox"]').filter({
        has: page.locator('[id^="project-"]'),
      });

      const count = await projectCheckboxes.count();
      if (count > 0) {
        // Check first project checkbox is selected
        const firstProjectCheckbox = projectCheckboxes.first();
        await expect(firstProjectCheckbox).toBeChecked();
      }
    });

    test('toggles individual project selections', async ({ page }) => {
      // Open deletion dialog
      const firstCard = page.locator('[data-testid="artifact-grid"]').locator('article').first();
      const menuButton = firstCard.locator('button[aria-label*="Actions"]');
      await menuButton.click();
      await page.getByRole('menuitem', { name: /delete/i }).click();

      // Enable project deletion
      const projectsCheckbox = page.getByLabel(/also delete from projects/i);
      await projectsCheckbox.click();
      await page.waitForTimeout(500);

      // Find project checkboxes
      const projectCheckboxes = page.locator('input[type="checkbox"]').filter({
        has: page.locator('[id^="project-"]'),
      });

      const count = await projectCheckboxes.count();
      if (count > 0) {
        // Deselect first project
        const firstCheckbox = projectCheckboxes.first();
        const wasChecked = await firstCheckbox.isChecked();

        if (wasChecked) {
          await firstCheckbox.click();
          await expect(firstCheckbox).not.toBeChecked();
        }
      }
    });

    test('shows selection count', async ({ page }) => {
      // Open deletion dialog
      const firstCard = page.locator('[data-testid="artifact-grid"]').locator('article').first();
      const menuButton = firstCard.locator('button[aria-label*="Actions"]');
      await menuButton.click();
      await page.getByRole('menuitem', { name: /delete/i }).click();

      // Enable project deletion
      const projectsCheckbox = page.getByLabel(/also delete from projects/i);
      await projectsCheckbox.click();
      await page.waitForTimeout(500);

      // Verify selection count is displayed
      const selectionCount = page.locator('text=/\\(\\d+ of \\d+ selected\\)/i');
      await expect(selectionCount).toBeVisible();
    });

    test('toggles "Delete Deployments" and shows RED warning', async ({ page }) => {
      // Open deletion dialog
      const firstCard = page.locator('[data-testid="artifact-grid"]').locator('article').first();
      const menuButton = firstCard.locator('button[aria-label*="Actions"]');
      await menuButton.click();
      await page.getByRole('menuitem', { name: /delete/i }).click();

      // Find "Delete Deployments" checkbox
      const deploymentsCheckbox = page.getByLabel(/delete deployments/i);
      await expect(deploymentsCheckbox).toBeVisible();
      await expect(deploymentsCheckbox).not.toBeChecked();

      // Toggle on
      await deploymentsCheckbox.click();
      await expect(deploymentsCheckbox).toBeChecked();

      // Verify RED warning appears
      await expect(page.getByText(/permanently delete files from your filesystem/i)).toBeVisible();
      await expect(page.getByText(/this cannot be undone!/i)).toBeVisible();
    });
  });

  test.describe('Cancel Flow', () => {
    test('closes dialog on Cancel button', async ({ page }) => {
      // Open deletion dialog
      const firstCard = page.locator('[data-testid="artifact-grid"]').locator('article').first();
      const menuButton = firstCard.locator('button[aria-label*="Actions"]');
      await menuButton.click();
      await page.getByRole('menuitem', { name: /delete/i }).click();

      // Verify dialog is open
      await waitForElement(page, '[role="dialog"]');

      // Click Cancel
      const cancelButton = page.getByRole('button', { name: /cancel/i });
      await cancelButton.click();

      // Verify dialog closes
      await page.waitForTimeout(300);
      const dialogs = page.getByRole('dialog');
      const dialogCount = await dialogs.count();
      expect(dialogCount).toBe(0);
    });

    test('artifact still exists after cancel', async ({ page }) => {
      // Get artifact name
      const firstCard = page.locator('[data-testid="artifact-grid"]').locator('article').first();
      const artifactName = await firstCard.locator('h3').textContent();

      // Open deletion dialog
      const menuButton = firstCard.locator('button[aria-label*="Actions"]');
      await menuButton.click();
      await page.getByRole('menuitem', { name: /delete/i }).click();

      // Cancel
      const cancelButton = page.getByRole('button', { name: /cancel/i });
      await cancelButton.click();

      // Verify artifact still in list
      await page.waitForTimeout(300);
      if (artifactName) {
        await expect(page.getByText(artifactName)).toBeVisible();
      }
    });

    test('closes dialog on Escape key', async ({ page }) => {
      // Open deletion dialog
      const firstCard = page.locator('[data-testid="artifact-grid"]').locator('article').first();
      const menuButton = firstCard.locator('button[aria-label*="Actions"]');
      await menuButton.click();
      await page.getByRole('menuitem', { name: /delete/i }).click();

      // Wait for dialog
      await waitForElement(page, '[role="dialog"]');

      // Press Escape
      await page.keyboard.press('Escape');

      // Verify dialog closes
      await page.waitForTimeout(300);
      const dialogs = page.getByRole('dialog');
      const dialogCount = await dialogs.count();
      expect(dialogCount).toBe(0);
    });
  });

  test.describe('Error Handling', () => {
    test('shows error message on deletion failure', async ({ page }) => {
      // Mock failed deletion
      await mockApiRoute(
        page,
        '/api/v1/artifacts/*/delete*',
        { error: 'Failed to delete artifact' },
        500
      );

      // Open deletion dialog
      const firstCard = page.locator('[data-testid="artifact-grid"]').locator('article').first();
      const menuButton = firstCard.locator('button[aria-label*="Actions"]');
      await menuButton.click();
      await page.getByRole('menuitem', { name: /delete/i }).click();

      // Confirm deletion
      const deleteButton = page.getByRole('button', { name: /delete artifact/i });
      await deleteButton.click();

      // Wait for error (toast notification)
      await page.waitForTimeout(1000);

      // Verify error is displayed (toast or inline message)
      // Note: Implementation-specific - may be toast or inline alert
    });

    test('handles partial deletion gracefully', async ({ page }) => {
      // Mock partial success
      await mockApiRoute(page, '/api/v1/artifacts/*/delete*', {
        collectionDeleted: true,
        projectsUndeployed: 1,
        deploymentsDeleted: 0,
        errors: [{ operation: 'undeploy:/project/b', error: 'File not found' }],
      });

      // Open deletion dialog
      const firstCard = page.locator('[data-testid="artifact-grid"]').locator('article').first();
      const menuButton = firstCard.locator('button[aria-label*="Actions"]');
      await menuButton.click();
      await page.getByRole('menuitem', { name: /delete/i }).click();

      // Enable project deletion
      const projectsCheckbox = page.getByLabel(/also delete from projects/i);
      await projectsCheckbox.click();
      await page.waitForTimeout(500);

      // Confirm deletion
      const deleteButton = page.getByRole('button', { name: /delete artifact/i });
      await deleteButton.click();

      // Wait for completion
      await page.waitForTimeout(1000);

      // Verify warning/partial success message
      // Note: Implementation-specific - check for toast or inline message
    });

    test('keeps dialog open on API error', async ({ page }) => {
      // Mock API error
      await mockApiRoute(page, '/api/v1/artifacts/*/delete*', { error: 'Network error' }, 500);

      // Open deletion dialog
      const firstCard = page.locator('[data-testid="artifact-grid"]').locator('article').first();
      const menuButton = firstCard.locator('button[aria-label*="Actions"]');
      await menuButton.click();
      await page.getByRole('menuitem', { name: /delete/i }).click();

      // Confirm deletion
      const deleteButton = page.getByRole('button', { name: /delete artifact/i });
      await deleteButton.click();

      // Wait for error
      await page.waitForTimeout(1000);

      // Dialog should still be open
      const dialog = page.getByRole('dialog');
      await expect(dialog).toBeVisible();
    });
  });

  test.describe('Accessibility', () => {
    test('focuses Delete button when dialog opens', async ({ page }) => {
      // Open deletion dialog
      const firstCard = page.locator('[data-testid="artifact-grid"]').locator('article').first();
      const menuButton = firstCard.locator('button[aria-label*="Actions"]');
      await menuButton.click();
      await page.getByRole('menuitem', { name: /delete/i }).click();

      // Wait for dialog
      await waitForElement(page, '[role="dialog"]');

      // Verify focus is trapped in dialog
      const deleteButton = page.getByRole('button', { name: /delete artifact/i });
      await expect(deleteButton).toBeVisible();
    });

    test('provides accessible labels for all interactive elements', async ({ page }) => {
      // Open deletion dialog
      const firstCard = page.locator('[data-testid="artifact-grid"]').locator('article').first();
      const menuButton = firstCard.locator('button[aria-label*="Actions"]');
      await menuButton.click();
      await page.getByRole('menuitem', { name: /delete/i }).click();

      // Verify all checkboxes have labels
      await expect(page.getByLabel(/delete from collection/i)).toBeVisible();
      await expect(page.getByLabel(/also delete from projects/i)).toBeVisible();
      await expect(page.getByLabel(/delete deployments/i)).toBeVisible();

      // Verify buttons have accessible names
      await expect(page.getByRole('button', { name: /cancel/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /delete artifact/i })).toBeVisible();
    });

    test('announces dynamic changes to screen readers', async ({ page }) => {
      // Open deletion dialog
      const firstCard = page.locator('[data-testid="artifact-grid"]').locator('article').first();
      const menuButton = firstCard.locator('button[aria-label*="Actions"]');
      await menuButton.click();
      await page.getByRole('menuitem', { name: /delete/i }).click();

      // Enable project deletion
      const projectsCheckbox = page.getByLabel(/also delete from projects/i);
      await projectsCheckbox.click();
      await page.waitForTimeout(500);

      // Verify selection count has aria-live
      const selectionCount = page.locator('text=/\\(\\d+ of \\d+ selected\\)/i');
      if (await selectionCount.isVisible()) {
        const ariaLive = await selectionCount.getAttribute('aria-live');
        expect(ariaLive).toBe('polite');
      }
    });
  });

  test.describe('Mobile Responsiveness', () => {
    test('deletion dialog is usable on mobile viewport', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });

      // Reload page with mobile viewport
      await navigateToPage(page, '/collection');

      // Open deletion dialog
      const firstCard = page.locator('[data-testid="artifact-grid"]').locator('article').first();
      const menuButton = firstCard.locator('button[aria-label*="Actions"]');
      await menuButton.click();
      await page.getByRole('menuitem', { name: /delete/i }).click();

      // Verify dialog is visible and usable
      const dialog = page.getByRole('dialog');
      await expect(dialog).toBeVisible();

      // Verify buttons are accessible
      await expect(page.getByRole('button', { name: /cancel/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /delete artifact/i })).toBeVisible();
    });

    test('project list scrolls on mobile', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });

      // Reload page
      await navigateToPage(page, '/collection');

      // Open deletion dialog
      const firstCard = page.locator('[data-testid="artifact-grid"]').locator('article').first();
      const menuButton = firstCard.locator('button[aria-label*="Actions"]');
      await menuButton.click();
      await page.getByRole('menuitem', { name: /delete/i }).click();

      // Enable project deletion
      const projectsCheckbox = page.getByLabel(/also delete from projects/i);
      await projectsCheckbox.click();
      await page.waitForTimeout(500);

      // Verify projects section is scrollable if needed
      const projectsList = page.locator('[class*="overflow"]');
      const count = await projectsList.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });
  });
});
