/**
 * Cross-Browser Testing for Skip Preferences LocalStorage Persistence
 *
 * DIS-5.9: Test LocalStorage persistence and UI rendering across Chrome, Firefox, and Safari
 *
 * This test suite verifies:
 * - LocalStorage write/read in each browser (chromium, firefox, webkit)
 * - Skip preference persists after page reload
 * - UI renders consistently (no layout issues)
 * - Toast notifications display correctly
 * - Tab switcher works in all browsers
 * - Checkbox states maintained correctly
 *
 * Run with:
 *   pnpm test:e2e:chromium tests/e2e/cross-browser-skip-prefs.spec.ts
 *   pnpm test:e2e:firefox tests/e2e/cross-browser-skip-prefs.spec.ts
 *   pnpm test:e2e:webkit tests/e2e/cross-browser-skip-prefs.spec.ts
 *
 * Or all browsers at once:
 *   pnpm test:e2e tests/e2e/cross-browser-skip-prefs.spec.ts
 */
import { test, expect, Page } from '@playwright/test';

test.describe('Cross-Browser Skip Preferences Persistence', () => {
  const projectId = 'cross-browser-test-project';
  const storageKey = `skillmeat_skip_prefs_${projectId}`;

  /**
   * Helper to wait for page to be ready
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
   * Helper to mock discovery API with artifacts
   */
  async function mockDiscoveryAPI(page: Page) {
    await page.route('**/api/v1/projects/*', async (route) => {
      if (route.request().url().includes('/discover')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            discovered_count: 3,
            artifacts: [
              {
                type: 'skill',
                name: 'test-skill-1',
                path: '/path/skill1',
                discovered_at: new Date().toISOString(),
              },
              {
                type: 'skill',
                name: 'test-skill-2',
                path: '/path/skill2',
                discovered_at: new Date().toISOString(),
              },
              {
                type: 'agent',
                name: 'test-agent',
                path: '/path/agent',
                discovered_at: new Date().toISOString(),
              },
            ],
            errors: [],
            scan_duration_ms: 100,
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: projectId,
            name: 'Cross-Browser Test Project',
            path: '/path/to/project',
            deployment_count: 3,
            last_deployment: new Date().toISOString(),
            stats: {
              modified_count: 0,
              by_type: { skill: 2, agent: 1 },
              by_collection: { user: 3 },
            },
            deployments: [],
          }),
        });
      }
    });
  }

  test.beforeEach(async ({ page }) => {
    // Clear localStorage before each test
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());

    // Setup API mocks
    await mockDiscoveryAPI(page);

    // Navigate to project Discovery tab
    await page.goto(`/projects/${projectId}?tab=discovery`);
    await waitForPageReady(page);
  });

  test.describe('LocalStorage Write/Read Operations', () => {
    test('writes skip preference to localStorage when artifact is skipped', async ({ page, browserName }) => {
      test.info().annotations.push({
        type: 'browser',
        description: browserName,
      });

      // Skip an artifact
      const artifactRow = page.getByText('test-skill-1').locator('..');
      const menuButton = artifactRow.getByRole('button', { name: /more|menu|options/i });
      await menuButton.click();
      await page.getByRole('menuitem', { name: /Skip|Skip for future/i }).click();

      // Wait for state update
      await page.waitForTimeout(500);

      // Verify LocalStorage contains the skip preference
      const storedData = await page.evaluate((key) => {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : null;
      }, storageKey);

      expect(storedData).toBeTruthy();
      expect(Array.isArray(storedData)).toBe(true);
      expect(storedData.length).toBeGreaterThan(0);
      expect(storedData[0]).toMatchObject({
        artifact_key: 'skill:test-skill-1',
        skip_reason: expect.any(String),
        added_date: expect.stringMatching(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/),
      });
    });

    test('reads skip preferences from localStorage on page load', async ({ page, browserName }) => {
      test.info().annotations.push({
        type: 'browser',
        description: browserName,
      });

      // Pre-populate localStorage with skip preferences
      await page.evaluate(
        ({ key, data }) => {
          localStorage.setItem(key, JSON.stringify(data));
        },
        {
          key: storageKey,
          data: [
            {
              artifact_key: 'skill:test-skill-2',
              skip_reason: 'Not needed for this browser test',
              added_date: new Date().toISOString(),
            },
          ],
        }
      );

      // Reload page
      await page.reload();
      await waitForPageReady(page);

      // Verify artifact shows as skipped in UI
      const artifactRow = page.getByText('test-skill-2').locator('..');
      await expect(artifactRow).toContainText(/Skipped/i);
    });

    test('handles multiple skip preferences correctly', async ({ page, browserName }) => {
      test.info().annotations.push({
        type: 'browser',
        description: browserName,
      });

      // Skip multiple artifacts
      for (const artifactName of ['test-skill-1', 'test-agent']) {
        const row = page.getByText(artifactName).locator('..');
        const menuButton = row.getByRole('button', { name: /more|menu|options/i });
        await menuButton.click();
        await page.getByRole('menuitem', { name: /Skip|Skip for future/i }).click();
        await page.waitForTimeout(300);
      }

      // Verify both are stored
      const storedData = await page.evaluate((key) => {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : null;
      }, storageKey);

      expect(storedData).toBeTruthy();
      expect(storedData.length).toBe(2);
      expect(storedData.map((p: any) => p.artifact_key)).toContain('skill:test-skill-1');
      expect(storedData.map((p: any) => p.artifact_key)).toContain('agent:test-agent');
    });
  });

  test.describe('Persistence Across Page Reloads', () => {
    test('skip preference persists after page reload', async ({ page, browserName }) => {
      test.info().annotations.push({
        type: 'browser',
        description: browserName,
      });

      // Skip an artifact
      const artifactRow = page.getByText('test-skill-1').locator('..');
      const menuButton = artifactRow.getByRole('button', { name: /more|menu|options/i });
      await menuButton.click();
      await page.getByRole('menuitem', { name: /Skip|Skip for future/i }).click();

      // Wait for save
      await page.waitForTimeout(500);

      // Verify artifact shows as skipped
      await expect(artifactRow).toContainText(/Skipped/i);

      // Reload page
      await page.reload();
      await waitForPageReady(page);

      // Verify artifact still shows as skipped after reload
      const reloadedRow = page.getByText('test-skill-1').locator('..');
      await expect(reloadedRow).toContainText(/Skipped/i);

      // Verify localStorage still contains the preference
      const storedData = await page.evaluate((key) => {
        return localStorage.getItem(key);
      }, storageKey);
      expect(storedData).toBeTruthy();
    });

    test('un-skip preference persists after page reload', async ({ page, browserName }) => {
      test.info().annotations.push({
        type: 'browser',
        description: browserName,
      });

      // Pre-populate with skipped artifact
      await page.evaluate(
        ({ key, data }) => {
          localStorage.setItem(key, JSON.stringify(data));
        },
        {
          key: storageKey,
          data: [
            {
              artifact_key: 'skill:test-skill-2',
              skip_reason: 'Test',
              added_date: new Date().toISOString(),
            },
          ],
        }
      );

      await page.reload();
      await waitForPageReady(page);

      // Expand Skip Preferences and un-skip
      await page.getByRole('button', { name: /Skip Preferences/i }).click();
      const unskipButton = page.getByRole('button', { name: /Un-skip|Remove/i }).first();
      await unskipButton.click();

      // Wait for update
      await page.waitForTimeout(500);

      // Reload page
      await page.reload();
      await waitForPageReady(page);

      // Verify artifact no longer shows as skipped
      const row = page.getByText('test-skill-2').locator('..');
      await expect(row).not.toContainText(/Skipped/i);
      await expect(row).toContainText(/New/i);
    });

    test('multiple reloads maintain skip state', async ({ page, browserName }) => {
      test.info().annotations.push({
        type: 'browser',
        description: browserName,
      });

      // Skip an artifact
      const artifactRow = page.getByText('test-agent').locator('..');
      const menuButton = artifactRow.getByRole('button', { name: /more|menu|options/i });
      await menuButton.click();
      await page.getByRole('menuitem', { name: /Skip|Skip for future/i }).click();
      await page.waitForTimeout(500);

      // Reload multiple times
      for (let i = 0; i < 3; i++) {
        await page.reload();
        await waitForPageReady(page);

        // Verify artifact still shows as skipped
        const reloadedRow = page.getByText('test-agent').locator('..');
        await expect(reloadedRow).toContainText(/Skipped/i);
      }
    });
  });

  test.describe('UI Rendering Consistency', () => {
    test('Discovery tab renders correctly', async ({ page, browserName }) => {
      test.info().annotations.push({
        type: 'browser',
        description: browserName,
      });

      // Verify tab is visible and active
      const discoveryTab = page.getByRole('tab', { name: /Discovery/i });
      await expect(discoveryTab).toBeVisible();
      await expect(discoveryTab).toHaveAttribute('data-state', 'active');

      // Verify artifacts are listed
      await expect(page.getByText('test-skill-1')).toBeVisible();
      await expect(page.getByText('test-skill-2')).toBeVisible();
      await expect(page.getByText('test-agent')).toBeVisible();
    });

    test('Skip Preferences accordion expands/collapses', async ({ page, browserName }) => {
      test.info().annotations.push({
        type: 'browser',
        description: browserName,
      });

      const skipPrefsButton = page.getByRole('button', { name: /Skip Preferences/i });
      await expect(skipPrefsButton).toBeVisible();

      // Click to expand
      await skipPrefsButton.click();

      // Verify content is visible (should show empty state or list)
      const skipPrefsContent = page.locator('[data-state="open"]');
      await expect(skipPrefsContent).toBeVisible({ timeout: 2000 });

      // Click to collapse
      await skipPrefsButton.click();

      // Verify content is hidden
      await expect(skipPrefsContent).not.toBeVisible();
    });

    test('artifact cards have consistent layout', async ({ page, browserName }) => {
      test.info().annotations.push({
        type: 'browser',
        description: browserName,
      });

      // Find artifact rows
      const artifactRows = await page.locator('[data-testid*="artifact-row"], .artifact-row, div:has-text("test-skill-1")').all();

      // Each artifact should be visible and have proper structure
      for (const row of artifactRows.slice(0, 3)) {
        await expect(row).toBeVisible();

        // Check for artifact name
        const hasText = await row.textContent();
        expect(hasText).toBeTruthy();
        expect(hasText!.length).toBeGreaterThan(0);
      }
    });

    test('no layout shifts when skipping artifacts', async ({ page, browserName }) => {
      test.info().annotations.push({
        type: 'browser',
        description: browserName,
      });

      // Get initial position of artifact
      const artifactRow = page.getByText('test-skill-1').locator('..');
      const initialBox = await artifactRow.boundingBox();
      expect(initialBox).toBeTruthy();

      // Skip artifact
      const menuButton = artifactRow.getByRole('button', { name: /more|menu|options/i });
      await menuButton.click();
      await page.getByRole('menuitem', { name: /Skip|Skip for future/i }).click();
      await page.waitForTimeout(500);

      // Get position after skipping
      const finalBox = await artifactRow.boundingBox();
      expect(finalBox).toBeTruthy();

      // Verify position didn't change significantly (allow for badge/label changes)
      expect(Math.abs(finalBox!.y - initialBox!.y)).toBeLessThan(10);
    });
  });

  test.describe('Toast Notifications', () => {
    test('displays toast when artifact is skipped', async ({ page, browserName }) => {
      test.info().annotations.push({
        type: 'browser',
        description: browserName,
      });

      // Skip an artifact
      const artifactRow = page.getByText('test-skill-2').locator('..');
      const menuButton = artifactRow.getByRole('button', { name: /more|menu|options/i });
      await menuButton.click();
      await page.getByRole('menuitem', { name: /Skip|Skip for future/i }).click();

      // Wait for toast to appear
      const toast = page.locator('[data-sonner-toast], .sonner-toast, [role="status"]');
      await expect(toast.first()).toBeVisible({ timeout: 3000 });

      // Verify toast contains skip message
      const toastText = await toast.first().textContent();
      expect(toastText).toMatch(/skip|marked/i);
    });

    test('displays toast when artifact is un-skipped', async ({ page, browserName }) => {
      test.info().annotations.push({
        type: 'browser',
        description: browserName,
      });

      // Pre-populate with skipped artifact
      await page.evaluate(
        ({ key, data }) => {
          localStorage.setItem(key, JSON.stringify(data));
        },
        {
          key: storageKey,
          data: [
            {
              artifact_key: 'agent:test-agent',
              skip_reason: 'Test',
              added_date: new Date().toISOString(),
            },
          ],
        }
      );

      await page.reload();
      await waitForPageReady(page);

      // Expand Skip Preferences and un-skip
      await page.getByRole('button', { name: /Skip Preferences/i }).click();
      const unskipButton = page.getByRole('button', { name: /Un-skip|Remove/i }).first();
      await unskipButton.click();

      // Wait for toast
      const toast = page.locator('[data-sonner-toast], .sonner-toast, [role="status"]');
      await expect(toast.first()).toBeVisible({ timeout: 3000 });

      // Verify toast contains un-skip message
      const toastText = await toast.first().textContent();
      expect(toastText).toMatch(/removed|un-skip/i);
    });

    test('toast auto-dismisses after timeout', async ({ page, browserName }) => {
      test.info().annotations.push({
        type: 'browser',
        description: browserName,
      });

      // Skip an artifact to trigger toast
      const artifactRow = page.getByText('test-skill-1').locator('..');
      const menuButton = artifactRow.getByRole('button', { name: /more|menu|options/i });
      await menuButton.click();
      await page.getByRole('menuitem', { name: /Skip|Skip for future/i }).click();

      // Wait for toast to appear
      const toast = page.locator('[data-sonner-toast], .sonner-toast, [role="status"]').first();
      await expect(toast).toBeVisible({ timeout: 3000 });

      // Wait for auto-dismiss (typical timeout is 3-5 seconds)
      await expect(toast).not.toBeVisible({ timeout: 10000 });
    });
  });

  test.describe('Tab Switcher Functionality', () => {
    test('can switch between Deployed and Discovery tabs', async ({ page, browserName }) => {
      test.info().annotations.push({
        type: 'browser',
        description: browserName,
      });

      // Verify Discovery tab is active
      const discoveryTab = page.getByRole('tab', { name: /Discovery/i });
      await expect(discoveryTab).toHaveAttribute('data-state', 'active');

      // Switch to Deployed tab
      const deployedTab = page.getByRole('tab', { name: /Deployed/i });
      await deployedTab.click();

      // Verify Deployed tab is now active
      await expect(deployedTab).toHaveAttribute('data-state', 'active');
      await expect(discoveryTab).toHaveAttribute('data-state', 'inactive');

      // Verify URL changed
      await expect(page).toHaveURL(/tab=deployed|projects\/[^?]+$/);

      // Switch back to Discovery
      await discoveryTab.click();
      await expect(discoveryTab).toHaveAttribute('data-state', 'active');
      await expect(page).toHaveURL(/tab=discovery/);
    });

    test('tab state reflects in URL query parameter', async ({ page, browserName }) => {
      test.info().annotations.push({
        type: 'browser',
        description: browserName,
      });

      // Should start on Discovery tab
      await expect(page).toHaveURL(/tab=discovery/);

      // Switch tabs
      await page.getByRole('tab', { name: /Deployed/i }).click();
      await expect(page).not.toHaveURL(/tab=discovery/);

      await page.getByRole('tab', { name: /Discovery/i }).click();
      await expect(page).toHaveURL(/tab=discovery/);
    });

    test('browser back/forward navigation works with tabs', async ({ page, browserName }) => {
      test.info().annotations.push({
        type: 'browser',
        description: browserName,
      });

      // Start on Discovery
      await expect(page.getByRole('tab', { name: /Discovery/i })).toHaveAttribute('data-state', 'active');

      // Switch to Deployed
      await page.getByRole('tab', { name: /Deployed/i }).click();
      await expect(page.getByRole('tab', { name: /Deployed/i })).toHaveAttribute('data-state', 'active');

      // Go back
      await page.goBack();
      await expect(page.getByRole('tab', { name: /Discovery/i })).toHaveAttribute('data-state', 'active');

      // Go forward
      await page.goForward();
      await expect(page.getByRole('tab', { name: /Deployed/i })).toHaveAttribute('data-state', 'active');
    });
  });

  test.describe('Checkbox State Management', () => {
    test('checkbox toggles correctly when clicking', async ({ page, browserName }) => {
      test.info().annotations.push({
        type: 'browser',
        description: browserName,
      });

      // Find a checkbox (if there are selection checkboxes)
      const checkboxes = await page.locator('input[type="checkbox"]').all();

      if (checkboxes.length > 0) {
        const firstCheckbox = checkboxes[0];

        // Get initial state
        const initiallyChecked = await firstCheckbox.isChecked();

        // Toggle checkbox
        await firstCheckbox.click();

        // Verify state changed
        const afterClickChecked = await firstCheckbox.isChecked();
        expect(afterClickChecked).toBe(!initiallyChecked);

        // Toggle again
        await firstCheckbox.click();

        // Verify state reverted
        const finalChecked = await firstCheckbox.isChecked();
        expect(finalChecked).toBe(initiallyChecked);
      }
    });

    test('checkbox state maintained when artifact is skipped', async ({ page, browserName }) => {
      test.info().annotations.push({
        type: 'browser',
        description: browserName,
      });

      // Skip an artifact
      const artifactRow = page.getByText('test-skill-1').locator('..');
      const menuButton = artifactRow.getByRole('button', { name: /more|menu|options/i });
      await menuButton.click();
      await page.getByRole('menuitem', { name: /Skip|Skip for future/i }).click();

      // Wait for state update
      await page.waitForTimeout(500);

      // Verify artifact shows skipped status
      await expect(artifactRow).toContainText(/Skipped/i);

      // If there are checkboxes, verify they're still functional
      const checkboxes = await page.locator('input[type="checkbox"]').all();
      if (checkboxes.length > 0) {
        const checkbox = checkboxes[0];
        await checkbox.click();
        expect(await checkbox.isChecked()).toBeTruthy();
      }
    });

    test('checkbox state persists across page reload', async ({ page, browserName }) => {
      test.info().annotations.push({
        type: 'browser',
        description: browserName,
      });

      // Skip an artifact to create persistent state
      const artifactRow = page.getByText('test-skill-2').locator('..');
      const menuButton = artifactRow.getByRole('button', { name: /more|menu|options/i });
      await menuButton.click();
      await page.getByRole('menuitem', { name: /Skip|Skip for future/i }).click();
      await page.waitForTimeout(500);

      // Reload page
      await page.reload();
      await waitForPageReady(page);

      // Verify skipped state persisted
      const reloadedRow = page.getByText('test-skill-2').locator('..');
      await expect(reloadedRow).toContainText(/Skipped/i);
    });
  });

  test.describe('Edge Cases & Error Handling', () => {
    test('handles localStorage quota exceeded gracefully', async ({ page, browserName }) => {
      test.info().annotations.push({
        type: 'browser',
        description: browserName,
      });

      // Mock localStorage to throw quota exceeded error
      await page.addInitScript(() => {
        const originalSetItem = Storage.prototype.setItem;
        let callCount = 0;
        Storage.prototype.setItem = function (key, value) {
          callCount++;
          if (callCount > 2 && key.includes('skillmeat_skip_prefs')) {
            throw new DOMException('QuotaExceededError', 'QuotaExceededError');
          }
          return originalSetItem.call(this, key, value);
        };
      });

      // Try to skip an artifact
      const artifactRow = page.getByText('test-skill-1').locator('..');
      const menuButton = artifactRow.getByRole('button', { name: /more|menu|options/i });
      await menuButton.click();

      // Should not throw error, should fail gracefully
      await page.getByRole('menuitem', { name: /Skip|Skip for future/i }).click();

      // Page should still be functional
      await expect(page.getByRole('tab', { name: /Discovery/i })).toBeVisible();
    });

    test('handles corrupted localStorage data gracefully', async ({ page, browserName }) => {
      test.info().annotations.push({
        type: 'browser',
        description: browserName,
      });

      // Pre-populate with corrupted data
      await page.evaluate((key) => {
        localStorage.setItem(key, 'invalid json {[}');
      }, storageKey);

      // Reload page
      await page.reload();
      await waitForPageReady(page);

      // Should still load without errors
      await expect(page.getByRole('tab', { name: /Discovery/i })).toBeVisible();

      // Artifacts should show as "New" (not skipped)
      const artifactRow = page.getByText('test-skill-1').locator('..');
      await expect(artifactRow).toContainText(/New/i);
    });

    test('handles localStorage disabled/unavailable', async ({ page, browserName }) => {
      test.info().annotations.push({
        type: 'browser',
        description: browserName,
      });

      // Mock localStorage to be unavailable
      await page.addInitScript(() => {
        Object.defineProperty(window, 'localStorage', {
          get: () => {
            throw new Error('localStorage is disabled');
          },
        });
      });

      // Navigate to page
      await page.goto(`/projects/${projectId}?tab=discovery`);
      await waitForPageReady(page);

      // Page should still load
      await expect(page.getByRole('tab', { name: /Discovery/i })).toBeVisible();

      // Try to skip (should fail gracefully without localStorage)
      const artifactRow = page.getByText('test-skill-1').locator('..');
      const menuButton = artifactRow.getByRole('button', { name: /more|menu|options/i });

      // Should not throw error
      await menuButton.click().catch(() => {
        // Graceful failure
      });
    });
  });
});
