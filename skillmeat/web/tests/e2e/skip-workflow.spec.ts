/**
 * End-to-end tests for Skip Workflow in BulkImportModal
 *
 * Tests the complete skip preference workflow from BulkImportModal:
 * 1. Skip checkbox interaction in modal
 * 2. Skip list sent in import request payload
 * 3. LocalStorage persistence after modal import
 * 4. Import result shows skipped artifacts with skip_reason
 *
 * NOTE: Discovery Tab skip management is already tested in discovery.spec.ts
 * This file focuses specifically on the BulkImportModal skip workflow.
 */
import { test, expect, Page } from '@playwright/test';

test.describe('BulkImportModal Skip Workflow', () => {
  /**
   * Helper to wait for page to be ready
   */
  async function waitForPageReady(page: Page) {
    await page.waitForLoadState('networkidle');
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
   * Helper to extract localStorage skip preferences
   */
  async function getSkipPrefsFromStorage(page: Page, projectId: string): Promise<any[]> {
    return page.evaluate((projId) => {
      const key = `skillmeat_skip_prefs_${projId}`;
      const stored = localStorage.getItem(key);
      return stored ? JSON.parse(stored) : [];
    }, projectId);
  }

  test.beforeEach(async ({ page }) => {
    // Mock project data
    await page.route('**/api/v1/projects/*', async (route) => {
      if (
        !route.request().url().includes('/discover') &&
        !route.request().url().includes('/import')
      ) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'skip-test-project',
            name: 'Skip Test Project',
            path: '/path/to/project',
            deployment_count: 0,
            last_deployment: null,
            stats: {
              modified_count: 0,
              by_type: {},
              by_collection: {},
            },
            deployments: [],
          }),
        });
      }
    });

    // Mock discovery data with multiple artifacts
    await page.route('**/api/v1/projects/*/discover', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          discovered_count: 3,
          artifacts: [
            {
              type: 'skill',
              name: 'importable-skill-1',
              source: 'user/repo/skill1',
              version: '1.0.0',
              path: '/path/skill1',
              discovered_at: new Date().toISOString(),
            },
            {
              type: 'skill',
              name: 'importable-skill-2',
              source: 'user/repo/skill2',
              version: '1.2.0',
              path: '/path/skill2',
              discovered_at: new Date().toISOString(),
            },
            {
              type: 'agent',
              name: 'importable-agent',
              source: 'user/repo/agent',
              version: '2.0.0',
              path: '/path/agent',
              discovered_at: new Date().toISOString(),
            },
          ],
          errors: [],
          scan_duration_ms: 100,
        }),
      });
    });

    // Navigate to Discovery tab
    await page.goto('/projects/skip-test-project?tab=discovery');
    await waitForPageReady(page);
  });

  test('skip checkbox in BulkImportModal can be checked', async ({ page }) => {
    // Wait for discovery to load
    await expect(page.getByText('importable-skill-1')).toBeVisible({ timeout: 10000 });

    // Click "Import All" or similar button to open BulkImportModal
    const importButton = page.getByRole('button', { name: /Import All|Bulk Import/i });
    await importButton.click();

    // Verify modal opened
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText('Review Discovered Artifacts')).toBeVisible();

    // Find the "Skip Future" checkbox for first artifact
    const skipCheckbox = page.locator('input[type="checkbox"][id^="skip-"]').first();
    await expect(skipCheckbox).toBeVisible();

    // Check the Skip checkbox
    await skipCheckbox.check();
    await expect(skipCheckbox).toBeChecked();

    // Verify checkbox can be unchecked
    await skipCheckbox.uncheck();
    await expect(skipCheckbox).not.toBeChecked();
  });

  test('import with skip checkbox checked sends skip_list in request', async ({ page }) => {
    let capturedRequestBody: any = null;

    // Mock import endpoint and capture request body
    await page.route('**/api/v1/projects/*/discover/import', async (route) => {
      const requestBody = route.request().postDataJSON();
      capturedRequestBody = requestBody;

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_requested: 2,
          total_imported: 1,
          total_skipped: 1,
          total_failed: 0,
          imported_to_collection: 1,
          added_to_project: 2,
          results: [
            {
              artifact_id: 'skill:importable-skill-1',
              status: 'success',
              message: 'Successfully imported',
            },
            {
              artifact_id: 'skill:importable-skill-2',
              status: 'skipped',
              message: 'Artifact skipped per user preference',
              skip_reason: 'User marked to skip',
            },
          ],
          duration_ms: 500,
        }),
      });
    });

    // Wait for discovery
    await expect(page.getByText('importable-skill-1')).toBeVisible({ timeout: 10000 });

    // Open BulkImportModal
    const importButton = page.getByRole('button', { name: /Import All|Bulk Import/i });
    await importButton.click();
    await expect(page.getByRole('dialog')).toBeVisible();

    // Select artifacts for import (click checkboxes in "Select" column)
    const selectCheckboxes = page.locator('input[type="checkbox"][aria-label^="Select"]');
    const firstSelect = selectCheckboxes.nth(0);
    const secondSelect = selectCheckboxes.nth(1);

    await firstSelect.check();
    await secondSelect.check();

    // Mark second artifact to skip (find skip checkbox for skill-2)
    const skipCheckboxes = page.locator('input[type="checkbox"][id^="skip-"]');
    const secondSkip = skipCheckboxes.nth(1); // Second artifact's skip checkbox
    await secondSkip.check();

    // Click Import button
    const confirmImportButton = page.getByRole('button', { name: /^Import/ });
    await confirmImportButton.click();

    // Wait for import request to complete
    await page.waitForTimeout(1000);

    // Verify request body contains skip_list
    expect(capturedRequestBody).toBeTruthy();
    expect(capturedRequestBody.skip_list).toBeDefined();
    expect(Array.isArray(capturedRequestBody.skip_list)).toBe(true);
    expect(capturedRequestBody.skip_list).toContain('skill:importable-skill-2');
  });

  test('skip preferences saved to LocalStorage after import with skip checkbox', async ({
    page,
  }) => {
    // Mock import endpoint
    await page.route('**/api/v1/projects/*/discover/import', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_requested: 1,
          total_imported: 0,
          total_skipped: 1,
          total_failed: 0,
          imported_to_collection: 0,
          added_to_project: 0,
          results: [
            {
              artifact_id: 'agent:importable-agent',
              status: 'skipped',
              message: 'Artifact skipped per user preference',
              skip_reason: 'User marked to skip',
            },
          ],
          duration_ms: 300,
        }),
      });
    });

    // Wait for discovery
    await expect(page.getByText('importable-agent')).toBeVisible({ timeout: 10000 });

    // Open modal
    await page.getByRole('button', { name: /Import All|Bulk Import/i }).click();
    await expect(page.getByRole('dialog')).toBeVisible();

    // Select agent artifact
    const agentSelectCheckbox = page.locator(
      'input[type="checkbox"][aria-label*="importable-agent"]'
    );
    await agentSelectCheckbox.check();

    // Check skip checkbox for agent
    const agentSkipCheckbox = page.locator('input[type="checkbox"][id*="agent"]').first();
    await agentSkipCheckbox.check();

    // Import
    await page.getByRole('button', { name: /^Import/ }).click();

    // Wait for import to complete and modal to close
    await page.waitForTimeout(1000);

    // Verify LocalStorage contains skip preference
    const skipPrefs = await getSkipPrefsFromStorage(page, 'skip-test-project');
    expect(skipPrefs.length).toBeGreaterThan(0);

    const agentSkipPref = skipPrefs.find(
      (pref: any) => pref.artifact_key === 'agent:importable-agent'
    );
    expect(agentSkipPref).toBeTruthy();
    expect(agentSkipPref.skip_reason).toBeDefined();
    expect(agentSkipPref.added_date).toBeDefined();
  });

  test('skip preferences persist after page reload', async ({ page }) => {
    // Mock import endpoint
    await page.route('**/api/v1/projects/*/discover/import', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_requested: 1,
          total_imported: 0,
          total_skipped: 1,
          total_failed: 0,
          imported_to_collection: 0,
          added_to_project: 0,
          results: [
            {
              artifact_id: 'skill:importable-skill-1',
              status: 'skipped',
              message: 'Artifact skipped',
              skip_reason: 'User marked to skip',
            },
          ],
          duration_ms: 200,
        }),
      });
    });

    // Wait for discovery
    await expect(page.getByText('importable-skill-1')).toBeVisible({ timeout: 10000 });

    // Open modal and skip an artifact
    await page.getByRole('button', { name: /Import All|Bulk Import/i }).click();
    await expect(page.getByRole('dialog')).toBeVisible();

    const selectCheckbox = page.locator('input[type="checkbox"][aria-label*="importable-skill-1"]');
    await selectCheckbox.check();

    const skipCheckbox = page.locator('input[type="checkbox"][id^="skip-"]').first();
    await skipCheckbox.check();

    await page.getByRole('button', { name: /^Import/ }).click();
    await page.waitForTimeout(1000);

    // Verify skip preference exists
    let skipPrefs = await getSkipPrefsFromStorage(page, 'skip-test-project');
    expect(skipPrefs.length).toBeGreaterThan(0);

    // Reload page
    await page.reload();
    await waitForPageReady(page);

    // Navigate to Discovery tab if needed
    const discoveryTab = page.getByRole('tab', { name: /Discovery/i });
    const isActive = await discoveryTab.getAttribute('data-state');
    if (isActive !== 'active') {
      await discoveryTab.click();
    }

    // Verify skip preferences still exist after reload
    skipPrefs = await getSkipPrefsFromStorage(page, 'skip-test-project');
    expect(skipPrefs.length).toBeGreaterThan(0);
    expect(skipPrefs.some((p: any) => p.artifact_key === 'skill:importable-skill-1')).toBe(true);
  });

  test('import result shows skipped artifacts with skip_reason', async ({ page }) => {
    // Mock import with mixed results
    await page.route('**/api/v1/projects/*/discover/import', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_requested: 3,
          total_imported: 1,
          total_skipped: 2,
          total_failed: 0,
          imported_to_collection: 1,
          added_to_project: 1,
          results: [
            {
              artifact_id: 'skill:importable-skill-1',
              status: 'success',
              message: 'Successfully imported',
            },
            {
              artifact_id: 'skill:importable-skill-2',
              status: 'skipped',
              message: 'Artifact skipped per user preference',
              skip_reason: 'User marked to skip in this import',
            },
            {
              artifact_id: 'agent:importable-agent',
              status: 'skipped',
              message: 'Artifact skipped per user preference',
              skip_reason: 'User marked to skip in this import',
            },
          ],
          duration_ms: 600,
        }),
      });
    });

    // Wait for discovery
    await expect(page.getByText('importable-skill-1')).toBeVisible({ timeout: 10000 });

    // Open modal
    await page.getByRole('button', { name: /Import All|Bulk Import/i }).click();
    await expect(page.getByRole('dialog')).toBeVisible();

    // Select all artifacts
    const selectAllCheckbox = page.locator(
      'input[type="checkbox"][aria-label="Select all artifacts"]'
    );
    await selectAllCheckbox.check();

    // Mark 2nd and 3rd artifacts to skip
    const skipCheckboxes = page.locator('input[type="checkbox"][id^="skip-"]');
    await skipCheckboxes.nth(1).check();
    await skipCheckboxes.nth(2).check();

    // Import
    await page.getByRole('button', { name: /^Import/ }).click();

    // Wait for result notification/toast
    await page.waitForTimeout(1500);

    // Verify success notification appears with summary
    // Toast should show: "1 imported, 2 skipped"
    const notification = page.locator('[role="status"], [role="alert"]').first();
    await expect(notification).toBeVisible({ timeout: 5000 });

    // Verify notification contains import counts
    const notificationText = await notification.textContent();
    expect(notificationText).toMatch(/1.*imported|success/i);
    expect(notificationText).toMatch(/2.*skipped/i);
  });

  test('skip checkbox disabled for already-skipped artifacts', async ({ page }) => {
    // Mock discovery with one artifact already marked as skipped
    await page.route('**/api/v1/projects/*/discover', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          discovered_count: 2,
          artifacts: [
            {
              type: 'skill',
              name: 'new-skill',
              path: '/path/new',
              discovered_at: new Date().toISOString(),
              status: 'success', // New artifact
            },
            {
              type: 'skill',
              name: 'already-skipped',
              path: '/path/skipped',
              discovered_at: new Date().toISOString(),
              status: 'skipped', // Already skipped
            },
          ],
          errors: [],
          scan_duration_ms: 50,
        }),
      });
    });

    await page.reload();
    await waitForPageReady(page);

    // Navigate to Discovery tab
    const discoveryTab = page.getByRole('tab', { name: /Discovery/i });
    await discoveryTab.click();

    // Wait for artifacts to load
    await expect(page.getByText('new-skill')).toBeVisible({ timeout: 10000 });

    // Open modal
    await page.getByRole('button', { name: /Import All|Bulk Import/i }).click();
    await expect(page.getByRole('dialog')).toBeVisible();

    // Find skip checkboxes
    const skipCheckboxes = page.locator('input[type="checkbox"][id^="skip-"]');

    // First artifact (new-skill) skip checkbox should be enabled
    const newSkillSkipCheckbox = skipCheckboxes.first();
    await expect(newSkillSkipCheckbox).toBeEnabled();

    // Second artifact (already-skipped) skip checkbox should be disabled
    const alreadySkippedCheckbox = skipCheckboxes.nth(1);
    await expect(alreadySkippedCheckbox).toBeDisabled();
  });

  test('can un-skip artifact and re-import in future', async ({ page }) => {
    // Pre-populate LocalStorage with skip preference
    await page.evaluate((projectId) => {
      const key = `skillmeat_skip_prefs_${projectId}`;
      const skipPrefs = [
        {
          artifact_key: 'skill:importable-skill-1',
          skip_reason: 'Previously skipped',
          added_date: new Date().toISOString(),
        },
      ];
      localStorage.setItem(key, JSON.stringify(skipPrefs));
    }, 'skip-test-project');

    await page.reload();
    await waitForPageReady(page);

    // Verify skip preference exists
    let skipPrefs = await getSkipPrefsFromStorage(page, 'skip-test-project');
    expect(skipPrefs.length).toBe(1);

    // Navigate to Discovery tab
    const discoveryTab = page.getByRole('tab', { name: /Discovery/i });
    const isActive = await discoveryTab.getAttribute('data-state');
    if (isActive !== 'active') {
      await discoveryTab.click();
    }

    // Expand Skip Preferences section
    const skipPrefsButton = page.getByRole('button', { name: /Skip Preferences/i });
    await skipPrefsButton.click();

    // Un-skip the artifact
    const unskipButton = page.getByRole('button', { name: /Un-skip|Remove/i }).first();
    await unskipButton.click();

    // Verify skip preference removed from LocalStorage
    skipPrefs = await getSkipPrefsFromStorage(page, 'skip-test-project');
    expect(skipPrefs.length).toBe(0);

    // Verify artifact now shows as "New" status (not skipped)
    const artifactRow = page.getByText('importable-skill-1').locator('..');
    await expect(artifactRow).toContainText(/New|Will add/i);
    await expect(artifactRow).not.toContainText(/Skipped/i);
  });
});
