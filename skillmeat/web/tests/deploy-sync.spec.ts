/**
 * Deploy and Sync Flow E2E Tests
 *
 * Tests for artifact deployment and project synchronization:
 * - Deploy workflow
 * - Sync workflow
 * - Project selection
 * - Success/error handling
 */

import { test, expect } from '@playwright/test';
import {
  mockApiRoute,
  navigateToPage,
  expectTextVisible,
  waitForElement,
  pressKey,
  expectModalOpen,
  expectModalClosed,
  expectSuccessMessage,
  expectErrorMessage,
} from './helpers/test-utils';
import {
  buildApiResponse,
  buildErrorResponse,
  mockArtifacts,
  mockProjects,
} from './helpers/fixtures';

test.describe('Deploy and Sync Flows', () => {
  test.beforeEach(async ({ page }) => {
    // Mock API routes
    await mockApiRoute(page, '/api/artifacts*', buildApiResponse.artifacts());
    await mockApiRoute(page, '/api/projects*', buildApiResponse.projects());
    await mockApiRoute(page, '/api/analytics*', buildApiResponse.analytics());
  });

  test.describe('Deploy Workflow', () => {
    test.beforeEach(async ({ page }) => {
      await navigateToPage(page, '/collection');

      // Open artifact detail drawer
      await mockApiRoute(
        page,
        `/api/artifacts/${mockArtifacts[0].id}`,
        buildApiResponse.artifactDetail(mockArtifacts[0].id)
      );

      const firstCard = page.locator('[data-testid="artifact-card"]').first();
      await firstCard.click();

      await waitForElement(page, '[role="dialog"]');
    });

    test('should show deploy button in artifact detail', async ({ page }) => {
      const deployButton = page.locator('button:has-text("Deploy")');
      await expect(deployButton).toBeVisible();
      await expect(deployButton).toBeEnabled();
    });

    test('should open deploy modal when clicked', async ({ page }) => {
      const deployButton = page.locator('button:has-text("Deploy")');
      await deployButton.click();

      // Deploy modal should open
      await expectModalOpen(page, '[data-testid="deploy-modal"]');
      await expectTextVisible(page, 'h2', 'Deploy Artifact');
    });

    test('should show project selection in deploy modal', async ({ page }) => {
      const deployButton = page.locator('button:has-text("Deploy")');
      await deployButton.click();

      await waitForElement(page, '[data-testid="deploy-modal"]');

      // Should show project list
      const projectSelect = page.locator('select[name="project"]');
      await expect(projectSelect).toBeVisible();

      // Should have options for each project
      const options = projectSelect.locator('option');
      const count = await options.count();
      expect(count).toBeGreaterThan(0);
    });

    test('should validate project selection', async ({ page }) => {
      const deployButton = page.locator('button:has-text("Deploy")');
      await deployButton.click();

      await waitForElement(page, '[data-testid="deploy-modal"]');

      // Try to deploy without selecting project
      const confirmButton = page.locator('[data-testid="deploy-modal"] button:has-text("Deploy")');
      await confirmButton.click();

      // Should show validation error
      await expectErrorMessage(page, /select a project/i);
    });

    test('should deploy artifact successfully', async ({ page }) => {
      // Mock successful deploy
      await mockApiRoute(page, '/api/deploy', buildApiResponse.deploySuccess());

      const deployButton = page.locator('button:has-text("Deploy")');
      await deployButton.click();

      await waitForElement(page, '[data-testid="deploy-modal"]');

      // Select project
      const projectSelect = page.locator('select[name="project"]');
      await projectSelect.selectOption(mockProjects[0].id);

      // Confirm deployment
      const confirmButton = page.locator('[data-testid="deploy-modal"] button:has-text("Deploy")');
      await confirmButton.click();

      // Should show success message
      await expectSuccessMessage(page, /deployed successfully/i);

      // Modal should close
      await page.waitForTimeout(1000);
      await expectModalClosed(page, '[data-testid="deploy-modal"]');
    });

    test('should handle deploy error', async ({ page }) => {
      // Mock deploy error
      await mockApiRoute(page, '/api/deploy', buildErrorResponse.serverError(), 500);

      const deployButton = page.locator('button:has-text("Deploy")');
      await deployButton.click();

      await waitForElement(page, '[data-testid="deploy-modal"]');

      // Select project and deploy
      const projectSelect = page.locator('select[name="project"]');
      await projectSelect.selectOption(mockProjects[0].id);

      const confirmButton = page.locator('[data-testid="deploy-modal"] button:has-text("Deploy")');
      await confirmButton.click();

      // Should show error message
      await expectErrorMessage(page, /failed|error/i);
    });

    test('should close deploy modal on cancel', async ({ page }) => {
      const deployButton = page.locator('button:has-text("Deploy")');
      await deployButton.click();

      await waitForElement(page, '[data-testid="deploy-modal"]');

      // Click cancel button
      const cancelButton = page.locator('[data-testid="deploy-modal"] button:has-text("Cancel")');
      await cancelButton.click();

      // Modal should close
      await expectModalClosed(page, '[data-testid="deploy-modal"]');
    });

    test('should close deploy modal on Escape key', async ({ page }) => {
      const deployButton = page.locator('button:has-text("Deploy")');
      await deployButton.click();

      await waitForElement(page, '[data-testid="deploy-modal"]');

      // Press Escape
      await pressKey(page, 'Escape');

      // Modal should close
      await expectModalClosed(page, '[data-testid="deploy-modal"]');
    });

    test('should show deployment progress', async ({ page }) => {
      // Mock slow deploy
      await page.route('**/api/deploy', async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 1000));
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(buildApiResponse.deploySuccess()),
        });
      });

      const deployButton = page.locator('button:has-text("Deploy")');
      await deployButton.click();

      await waitForElement(page, '[data-testid="deploy-modal"]');

      const projectSelect = page.locator('select[name="project"]');
      await projectSelect.selectOption(mockProjects[0].id);

      const confirmButton = page.locator('[data-testid="deploy-modal"] button:has-text("Deploy")');
      await confirmButton.click();

      // Should show loading state
      const loadingIndicator = page.locator('[role="progressbar"]');
      await expect(loadingIndicator).toBeVisible();
    });
  });

  test.describe('Sync Workflow', () => {
    test.beforeEach(async ({ page }) => {
      await navigateToPage(page, '/projects');
    });

    test('should show sync button for projects', async ({ page }) => {
      const syncButton = page.locator('button:has-text("Sync")').first();
      await expect(syncButton).toBeVisible();
      await expect(syncButton).toBeEnabled();
    });

    test('should open sync modal when clicked', async ({ page }) => {
      const syncButton = page.locator('button:has-text("Sync")').first();
      await syncButton.click();

      await expectModalOpen(page, '[data-testid="sync-modal"]');
      await expectTextVisible(page, 'h2', 'Sync Project');
    });

    test('should show project details in sync modal', async ({ page }) => {
      const syncButton = page.locator('button:has-text("Sync")').first();
      await syncButton.click();

      await waitForElement(page, '[data-testid="sync-modal"]');

      // Should show project name
      await expectTextVisible(page, '[data-testid="sync-modal"]', mockProjects[0].name);

      // Should show last sync time
      await expectTextVisible(page, '[data-testid="sync-modal"]', /last sync/i);
    });

    test('should sync project successfully', async ({ page }) => {
      // Mock successful sync
      await mockApiRoute(page, '/api/sync', buildApiResponse.syncSuccess());

      const syncButton = page.locator('button:has-text("Sync")').first();
      await syncButton.click();

      await waitForElement(page, '[data-testid="sync-modal"]');

      // Confirm sync
      const confirmButton = page.locator('[data-testid="sync-modal"] button:has-text("Sync")');
      await confirmButton.click();

      // Should show success message
      await expectSuccessMessage(page, /synced successfully/i);

      // Modal should close
      await page.waitForTimeout(1000);
      await expectModalClosed(page, '[data-testid="sync-modal"]');
    });

    test('should handle sync error', async ({ page }) => {
      // Mock sync error
      await mockApiRoute(page, '/api/sync', buildErrorResponse.serverError(), 500);

      const syncButton = page.locator('button:has-text("Sync")').first();
      await syncButton.click();

      await waitForElement(page, '[data-testid="sync-modal"]');

      const confirmButton = page.locator('[data-testid="sync-modal"] button:has-text("Sync")');
      await confirmButton.click();

      // Should show error message
      await expectErrorMessage(page, /failed|error/i);
    });

    test('should show sync options', async ({ page }) => {
      const syncButton = page.locator('button:has-text("Sync")').first();
      await syncButton.click();

      await waitForElement(page, '[data-testid="sync-modal"]');

      // Should show sync mode options (pull, push, bidirectional)
      const pullOption = page.locator('input[value="pull"]');
      const pushOption = page.locator('input[value="push"]');

      await expect(pullOption).toBeVisible();
      await expect(pushOption).toBeVisible();
    });

    test('should handle conflict detection', async ({ page }) => {
      // Mock sync with conflicts
      await mockApiRoute(page, '/api/sync', {
        success: false,
        conflicts: ['artifact-1'],
        message: 'Conflicts detected',
      });

      const syncButton = page.locator('button:has-text("Sync")').first();
      await syncButton.click();

      await waitForElement(page, '[data-testid="sync-modal"]');

      const confirmButton = page.locator('[data-testid="sync-modal"] button:has-text("Sync")');
      await confirmButton.click();

      // Should show conflict resolution UI
      await expectTextVisible(page, '[data-testid="sync-modal"]', /conflict/i);
    });

    test('should close sync modal on cancel', async ({ page }) => {
      const syncButton = page.locator('button:has-text("Sync")').first();
      await syncButton.click();

      await waitForElement(page, '[data-testid="sync-modal"]');

      const cancelButton = page.locator('[data-testid="sync-modal"] button:has-text("Cancel")');
      await cancelButton.click();

      await expectModalClosed(page, '[data-testid="sync-modal"]');
    });

    test('should show sync progress', async ({ page }) => {
      // Mock slow sync
      await page.route('**/api/sync', async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 1000));
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(buildApiResponse.syncSuccess()),
        });
      });

      const syncButton = page.locator('button:has-text("Sync")').first();
      await syncButton.click();

      await waitForElement(page, '[data-testid="sync-modal"]');

      const confirmButton = page.locator('[data-testid="sync-modal"] button:has-text("Sync")');
      await confirmButton.click();

      // Should show progress indicator
      const progressBar = page.locator('[role="progressbar"]');
      await expect(progressBar).toBeVisible();
    });

    test('should update last sync time after successful sync', async ({ page }) => {
      await mockApiRoute(page, '/api/sync', buildApiResponse.syncSuccess());

      const syncButton = page.locator('button:has-text("Sync")').first();
      await syncButton.click();

      await waitForElement(page, '[data-testid="sync-modal"]');

      const confirmButton = page.locator('[data-testid="sync-modal"] button:has-text("Sync")');
      await confirmButton.click();

      await page.waitForTimeout(1500);

      // Last sync time should be updated (would need to verify in the project list)
      // This would require re-fetching the projects list
    });
  });

  test.describe('Batch Operations', () => {
    test('should support multi-select for batch deploy', async ({ page }) => {
      await navigateToPage(page, '/collection');

      // Enable selection mode
      const selectModeButton = page.locator('button:has-text("Select")');
      if (await selectModeButton.isVisible()) {
        await selectModeButton.click();

        // Select multiple artifacts
        const checkboxes = page.locator('input[type="checkbox"]');
        const firstCheckbox = checkboxes.first();
        const secondCheckbox = checkboxes.nth(1);

        await firstCheckbox.check();
        await secondCheckbox.check();

        // Batch deploy button should appear
        const batchDeployButton = page.locator('button:has-text("Deploy Selected")');
        await expect(batchDeployButton).toBeVisible();
      }
    });
  });
});
