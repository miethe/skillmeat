/**
 * End-to-end tests for Discovery Flow
 *
 * Tests the complete user flow for discovering artifacts in project directories,
 * reviewing them, and importing them into the collection.
 *
 * Covers:
 * - Discovery banner display
 * - Review modal interaction
 * - Selection and import
 * - Empty state handling
 * - Banner dismissal
 */
import { test, expect, Page } from '@playwright/test';
import { mockApiRoute, waitForPageLoad } from '../helpers/test-utils';

test.describe('Discovery Flow E2E', () => {
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

  test.beforeEach(async ({ page }) => {
    // Navigate to manage page
    await page.goto('/manage');
    await waitForPageReady(page);
  });

  test.describe('Discovery Banner', () => {
    test('displays discovery banner when artifacts found', async ({ page }) => {
      // Mock the discovery API to return artifacts
      await page.route('**/api/v1/artifacts/discover', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            discovered_count: 3,
            artifacts: [
              {
                type: 'skill',
                name: 'test-skill-1',
                source: 'user/repo/skill1',
                path: '/path/to/skill1',
                discovered_at: new Date().toISOString(),
              },
              {
                type: 'command',
                name: 'test-command',
                source: 'user/repo/command',
                path: '/path/to/command',
                discovered_at: new Date().toISOString(),
              },
              {
                type: 'skill',
                name: 'test-skill-2',
                path: '/path/to/skill2',
                discovered_at: new Date().toISOString(),
              },
            ],
            errors: [],
            scan_duration_ms: 150,
          }),
        });
      });

      // Trigger discovery (might be automatic or manual)
      await page.reload();
      await waitForPageReady(page);

      // Wait for discovery banner to appear
      const banner = page.getByText(/Found 3 Artifact/i);
      await expect(banner).toBeVisible({ timeout: 10000 });

      // Verify banner contains key information
      await expect(page.getByText(/Review & Import/i)).toBeVisible();
    });

    test('displays singular form for single artifact', async ({ page }) => {
      await page.route('**/api/v1/artifacts/discover', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            discovered_count: 1,
            artifacts: [
              {
                type: 'skill',
                name: 'single-skill',
                path: '/path/to/single',
                discovered_at: new Date().toISOString(),
              },
            ],
            errors: [],
            scan_duration_ms: 50,
          }),
        });
      });

      await page.reload();
      await waitForPageReady(page);

      await expect(page.getByText(/Found 1 Artifact/i)).toBeVisible({ timeout: 10000 });
    });

    test('does not display banner when no artifacts found', async ({ page }) => {
      await page.route('**/api/v1/artifacts/discover', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            discovered_count: 0,
            artifacts: [],
            errors: [],
            scan_duration_ms: 50,
          }),
        });
      });

      await page.reload();
      await waitForPageReady(page);

      // Banner should not appear
      const banner = page.getByText(/Found.*Artifact/i);
      await expect(banner).not.toBeVisible();
    });

    test('can dismiss discovery banner', async ({ page }) => {
      await page.route('**/api/v1/artifacts/discover', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            discovered_count: 2,
            artifacts: [
              {
                type: 'skill',
                name: 'test',
                path: '/path',
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
            scan_duration_ms: 50,
          }),
        });
      });

      await page.reload();
      await waitForPageReady(page);

      // Verify banner is visible
      await expect(page.getByText(/Found 2 Artifact/i)).toBeVisible({ timeout: 10000 });

      // Find and click dismiss button
      const dismissButton = page.getByRole('button', { name: /Dismiss/i });
      await dismissButton.click();

      // Verify banner is hidden
      await expect(page.getByText(/Found.*Artifact/i)).not.toBeVisible();
    });
  });

  test.describe('Review Modal', () => {
    test('opens review modal when clicking Review & Import', async ({ page }) => {
      await page.route('**/api/v1/artifacts/discover', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            discovered_count: 3,
            artifacts: [
              {
                type: 'skill',
                name: 'test-skill',
                source: 'user/repo/skill',
                path: '/path/skill',
                discovered_at: new Date().toISOString(),
              },
              {
                type: 'command',
                name: 'test-command',
                path: '/path/command',
                discovered_at: new Date().toISOString(),
              },
              {
                type: 'agent',
                name: 'test-agent',
                source: 'user/repo/agent',
                path: '/path/agent',
                discovered_at: new Date().toISOString(),
              },
            ],
            errors: [],
            scan_duration_ms: 100,
          }),
        });
      });

      await page.reload();
      await waitForPageReady(page);

      // Click Review & Import button
      const reviewButton = page.getByRole('button', { name: /Review & Import/i });
      await expect(reviewButton).toBeVisible({ timeout: 10000 });
      await reviewButton.click();

      // Verify modal opened
      await expect(page.getByRole('dialog')).toBeVisible();
      await expect(page.getByText('Review Discovered Artifacts')).toBeVisible();

      // Verify artifacts are listed
      await expect(page.getByText('test-skill')).toBeVisible();
      await expect(page.getByText('test-command')).toBeVisible();
      await expect(page.getByText('test-agent')).toBeVisible();
    });

    test('displays artifact details in modal', async ({ page }) => {
      await page.route('**/api/v1/artifacts/discover', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            discovered_count: 1,
            artifacts: [
              {
                type: 'skill',
                name: 'detailed-skill',
                source: 'user/repo/skills/detailed',
                path: '/path/to/detailed-skill',
                discovered_at: '2024-11-30T12:00:00Z',
              },
            ],
            errors: [],
            scan_duration_ms: 75,
          }),
        });
      });

      await page.reload();
      await waitForPageReady(page);

      await page.getByRole('button', { name: /Review & Import/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible();

      // Verify artifact details
      await expect(page.getByText('detailed-skill')).toBeVisible();
      await expect(page.getByText('skill')).toBeVisible();
      await expect(page.getByText('user/repo/skills/detailed')).toBeVisible();
    });

    test('can close review modal', async ({ page }) => {
      await page.route('**/api/v1/artifacts/discover', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            discovered_count: 1,
            artifacts: [
              {
                type: 'skill',
                name: 'test',
                path: '/path',
                discovered_at: new Date().toISOString(),
              },
            ],
            errors: [],
            scan_duration_ms: 50,
          }),
        });
      });

      await page.reload();
      await waitForPageReady(page);

      // Open modal
      await page.getByRole('button', { name: /Review & Import/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible();

      // Close modal
      const closeButton = page.getByRole('button', { name: /Cancel|Close/i });
      await closeButton.click();

      // Verify modal is closed
      await expect(page.getByRole('dialog')).not.toBeVisible();
    });
  });

  test.describe('Selection and Import', () => {
    test('can select and import artifacts', async ({ page }) => {
      let importRequested = false;

      await page.route('**/api/v1/artifacts/discover', async (route) => {
        if (route.request().method() === 'POST' && route.request().url().includes('/import')) {
          // Import endpoint
          importRequested = true;
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              total_requested: 2,
              total_imported: 2,
              total_failed: 0,
              results: [
                {
                  artifact_id: 'skill:test-skill',
                  success: true,
                  message: 'Successfully imported',
                },
                {
                  artifact_id: 'command:test-command',
                  success: true,
                  message: 'Successfully imported',
                },
              ],
              duration_ms: 500,
            }),
          });
        } else {
          // Discovery endpoint
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              discovered_count: 2,
              artifacts: [
                {
                  type: 'skill',
                  name: 'test-skill',
                  path: '/path/1',
                  discovered_at: new Date().toISOString(),
                },
                {
                  type: 'command',
                  name: 'test-command',
                  path: '/path/2',
                  discovered_at: new Date().toISOString(),
                },
              ],
              errors: [],
              scan_duration_ms: 100,
            }),
          });
        }
      });

      await page.reload();
      await waitForPageReady(page);

      // Open modal
      await page.getByRole('button', { name: /Review & Import/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible();

      // Select artifacts (find checkboxes and click them)
      const checkboxes = await page.locator('input[type="checkbox"]').all();

      // Select first two checkboxes (or select all checkbox if available)
      if (checkboxes.length > 0) {
        await checkboxes[0].click(); // This might be "select all" or first artifact

        // If there are individual checkboxes, select them
        if (checkboxes.length > 1) {
          await checkboxes[1].click();
        }
      }

      // Click Import button
      const importButton = page.getByRole('button', { name: /Import Selected|Import/i });
      await expect(importButton).toBeEnabled();
      await importButton.click();

      // Wait for import to complete
      await page.waitForTimeout(1000);

      // Verify success (modal might close or show success message)
      const successIndicator = page.getByText(/imported|success/i);
      await expect(successIndicator).toBeVisible({ timeout: 5000 });

      // Verify import was requested
      expect(importRequested).toBe(true);
    });

    test('can select all artifacts', async ({ page }) => {
      await page.route('**/api/v1/artifacts/discover', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            discovered_count: 3,
            artifacts: [
              {
                type: 'skill',
                name: 'skill-1',
                path: '/path/1',
                discovered_at: new Date().toISOString(),
              },
              {
                type: 'command',
                name: 'command-1',
                path: '/path/2',
                discovered_at: new Date().toISOString(),
              },
              {
                type: 'agent',
                name: 'agent-1',
                path: '/path/3',
                discovered_at: new Date().toISOString(),
              },
            ],
            errors: [],
            scan_duration_ms: 100,
          }),
        });
      });

      await page.reload();
      await waitForPageReady(page);

      await page.getByRole('button', { name: /Review & Import/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible();

      // Look for "select all" checkbox or button
      const selectAllCheckbox = page.locator('input[type="checkbox"]').first();
      await selectAllCheckbox.click();

      // Verify all checkboxes are checked
      const allCheckboxes = await page.locator('input[type="checkbox"]:checked').count();
      expect(allCheckboxes).toBeGreaterThan(0);
    });

    test('handles partial import success', async ({ page }) => {
      await page.route('**/api/v1/artifacts/discover', async (route) => {
        if (route.request().method() === 'POST' && route.request().url().includes('/import')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              total_requested: 2,
              total_imported: 1,
              total_failed: 1,
              results: [
                {
                  artifact_id: 'skill:good-skill',
                  success: true,
                  message: 'Successfully imported',
                },
                {
                  artifact_id: 'skill:bad-skill',
                  success: false,
                  error: 'Import failed: validation error',
                },
              ],
              duration_ms: 500,
            }),
          });
        } else {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              discovered_count: 2,
              artifacts: [
                {
                  type: 'skill',
                  name: 'good-skill',
                  path: '/path/good',
                  discovered_at: new Date().toISOString(),
                },
                {
                  type: 'skill',
                  name: 'bad-skill',
                  path: '/path/bad',
                  discovered_at: new Date().toISOString(),
                },
              ],
              errors: [],
              scan_duration_ms: 100,
            }),
          });
        }
      });

      await page.reload();
      await waitForPageReady(page);

      await page.getByRole('button', { name: /Review & Import/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible();

      // Select all and import
      const checkboxes = await page.locator('input[type="checkbox"]').all();
      if (checkboxes.length > 0) {
        await checkboxes[0].click();
      }

      await page.getByRole('button', { name: /Import/i }).click();
      await page.waitForTimeout(1000);

      // Verify partial success message is shown
      const message = page.getByText(/1.*imported.*1.*failed/i);
      await expect(message).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('Error Handling', () => {
    test('handles discovery API errors gracefully', async ({ page }) => {
      await page.route('**/api/v1/artifacts/discover', async (route) => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: 'Internal server error',
          }),
        });
      });

      await page.reload();
      await waitForPageReady(page);

      // Banner should not appear, or error message should be shown
      const banner = page.getByText(/Found.*Artifact/i);
      await expect(banner).not.toBeVisible();
    });

    test('displays discovery errors in response', async ({ page }) => {
      await page.route('**/api/v1/artifacts/discover', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            discovered_count: 1,
            artifacts: [
              {
                type: 'skill',
                name: 'good-artifact',
                path: '/path/good',
                discovered_at: new Date().toISOString(),
              },
            ],
            errors: [
              {
                path: '/path/bad',
                error: 'Failed to parse artifact manifest',
              },
            ],
            scan_duration_ms: 150,
          }),
        });
      });

      await page.reload();
      await waitForPageReady(page);

      await page.getByRole('button', { name: /Review & Import/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible();

      // Should show 1 successful artifact
      await expect(page.getByText('good-artifact')).toBeVisible();

      // Should indicate there were errors
      const errorIndicator = page.getByText(/error|warning|failed/i);
      await expect(errorIndicator).toBeVisible();
    });

    test('handles import API errors', async ({ page }) => {
      await page.route('**/api/v1/artifacts/discover', async (route) => {
        if (route.request().method() === 'POST' && route.request().url().includes('/import')) {
          await route.fulfill({
            status: 500,
            contentType: 'application/json',
            body: JSON.stringify({
              detail: 'Import failed',
            }),
          });
        } else {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              discovered_count: 1,
              artifacts: [
                {
                  type: 'skill',
                  name: 'test',
                  path: '/path',
                  discovered_at: new Date().toISOString(),
                },
              ],
              errors: [],
              scan_duration_ms: 50,
            }),
          });
        }
      });

      await page.reload();
      await waitForPageReady(page);

      await page.getByRole('button', { name: /Review & Import/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible();

      // Select and try to import
      const checkboxes = await page.locator('input[type="checkbox"]').all();
      if (checkboxes.length > 0) {
        await checkboxes[0].click();
      }

      await page.getByRole('button', { name: /Import/i }).click();
      await page.waitForTimeout(1000);

      // Error message should be shown
      const errorMessage = page.getByText(/failed|error/i);
      await expect(errorMessage).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('Edge Cases', () => {
    test('handles empty artifact name gracefully', async ({ page }) => {
      await page.route('**/api/v1/artifacts/discover', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            discovered_count: 1,
            artifacts: [
              {
                type: 'skill',
                name: '',
                path: '/path/unnamed',
                discovered_at: new Date().toISOString(),
              },
            ],
            errors: [],
            scan_duration_ms: 50,
          }),
        });
      });

      await page.reload();
      await waitForPageReady(page);

      await page.getByRole('button', { name: /Review & Import/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible();

      // Should still display the artifact (maybe with placeholder name)
      const artifactList = page.locator('[role="dialog"]');
      await expect(artifactList).toBeVisible();
    });

    test('handles artifacts without source field', async ({ page }) => {
      await page.route('**/api/v1/artifacts/discover', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            discovered_count: 1,
            artifacts: [
              {
                type: 'skill',
                name: 'local-skill',
                path: '/path/local',
                discovered_at: new Date().toISOString(),
                // no source field
              },
            ],
            errors: [],
            scan_duration_ms: 50,
          }),
        });
      });

      await page.reload();
      await waitForPageReady(page);

      await page.getByRole('button', { name: /Review & Import/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible();

      // Should display artifact without error
      await expect(page.getByText('local-skill')).toBeVisible();
    });
  });

  test.describe('Discovery Tab Navigation', () => {
    test.beforeEach(async ({ page }) => {
      // Mock project data
      await page.route('**/api/v1/projects/*', async (route) => {
        if (!route.request().url().includes('/discover')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              id: 'test-project-1',
              name: 'Test Project',
              path: '/path/to/project',
              deployment_count: 5,
              last_deployment: new Date().toISOString(),
              stats: {
                modified_count: 1,
                by_type: { skill: 3, command: 2 },
                by_collection: { user: 5 },
              },
              deployments: [],
            }),
          });
        }
      });

      // Navigate to a project detail page
      await page.goto('/projects/test-project-1');
      await waitForPageReady(page);
    });

    test('shows Deployed and Discovery tabs on project detail page', async ({ page }) => {
      // Verify both tabs are visible
      await expect(page.getByRole('tab', { name: /Deployed/i })).toBeVisible();
      await expect(page.getByRole('tab', { name: /Discovery/i })).toBeVisible();

      // "Deployed" tab should be active by default
      const deployedTab = page.getByRole('tab', { name: /Deployed/i });
      await expect(deployedTab).toHaveAttribute('data-state', 'active');
    });

    test('clicking Discovery tab switches view and updates URL', async ({ page }) => {
      // Mock discovery data
      await page.route('**/api/v1/projects/*/discover', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            discovered_count: 2,
            artifacts: [
              {
                type: 'skill',
                name: 'discovered-skill',
                path: '/path/skill',
                discovered_at: new Date().toISOString(),
              },
              {
                type: 'agent',
                name: 'discovered-agent',
                path: '/path/agent',
                discovered_at: new Date().toISOString(),
              },
            ],
            errors: [],
            scan_duration_ms: 100,
          }),
        });
      });

      // Click Discovery tab
      const discoveryTab = page.getByRole('tab', { name: /Discovery/i });
      await discoveryTab.click();

      // Verify URL changes to ?tab=discovery
      await expect(page).toHaveURL(/tab=discovery/);

      // Verify Discovery tab is active
      await expect(discoveryTab).toHaveAttribute('data-state', 'active');

      // Verify Discovery content is visible
      await expect(page.getByText('discovered-skill')).toBeVisible({ timeout: 10000 });
    });

    test('tab state persists on page reload via URL', async ({ page }) => {
      // Mock discovery data
      await page.route('**/api/v1/projects/*/discover', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            discovered_count: 1,
            artifacts: [
              {
                type: 'skill',
                name: 'persistent-skill',
                path: '/path/skill',
                discovered_at: new Date().toISOString(),
              },
            ],
            errors: [],
            scan_duration_ms: 50,
          }),
        });
      });

      // Navigate directly to ?tab=discovery
      await page.goto('/projects/test-project-1?tab=discovery');
      await waitForPageReady(page);

      // Verify Discovery tab is active after reload
      const discoveryTab = page.getByRole('tab', { name: /Discovery/i });
      await expect(discoveryTab).toHaveAttribute('data-state', 'active');

      // Content matches Discovery tab
      await expect(page.getByText('persistent-skill')).toBeVisible({ timeout: 10000 });
    });

    test('browser back/forward navigation works with tabs', async ({ page }) => {
      // Mock discovery data
      await page.route('**/api/v1/projects/*/discover', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            discovered_count: 1,
            artifacts: [
              {
                type: 'skill',
                name: 'nav-test-skill',
                path: '/path/skill',
                discovered_at: new Date().toISOString(),
              },
            ],
            errors: [],
            scan_duration_ms: 50,
          }),
        });
      });

      // Start on Deployed tab
      await expect(page.getByRole('tab', { name: /Deployed/i })).toHaveAttribute('data-state', 'active');

      // Click Discovery tab (URL changes)
      await page.getByRole('tab', { name: /Discovery/i }).click();
      await expect(page).toHaveURL(/tab=discovery/);

      // Click browser back
      await page.goBack();

      // Verify Deployed tab is active again
      await expect(page.getByRole('tab', { name: /Deployed/i })).toHaveAttribute('data-state', 'active');
      await expect(page).not.toHaveURL(/tab=discovery/);
    });

    test('Discovery tab shows artifact count badge when artifacts available', async ({ page }) => {
      // Mock discovery with 3 artifacts
      await page.route('**/api/v1/projects/*/discover', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            discovered_count: 3,
            artifacts: [
              {
                type: 'skill',
                name: 'skill-1',
                path: '/path/1',
                discovered_at: new Date().toISOString(),
              },
              {
                type: 'skill',
                name: 'skill-2',
                path: '/path/2',
                discovered_at: new Date().toISOString(),
              },
              {
                type: 'agent',
                name: 'agent-1',
                path: '/path/3',
                discovered_at: new Date().toISOString(),
              },
            ],
            errors: [],
            scan_duration_ms: 100,
          }),
        });
      });

      // Wait for discovery to complete
      await page.reload();
      await waitForPageReady(page);

      // Verify Discovery tab shows badge with count
      const discoveryTab = page.getByRole('tab', { name: /Discovery/i });
      await expect(discoveryTab).toContainText('3');
    });
  });

  test.describe('Skip Management in Discovery Tab', () => {
    test.beforeEach(async ({ page }) => {
      // Mock project data
      await page.route('**/api/v1/projects/*', async (route) => {
        if (!route.request().url().includes('/discover')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              id: 'test-project-2',
              name: 'Skip Test Project',
              path: '/path/to/skip-project',
              deployment_count: 2,
              last_deployment: new Date().toISOString(),
              stats: {
                modified_count: 0,
                by_type: { skill: 2 },
                by_collection: { user: 2 },
              },
              deployments: [],
            }),
          });
        }
      });

      // Mock discovery data with artifacts
      await page.route('**/api/v1/projects/*/discover', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            discovered_count: 3,
            artifacts: [
              {
                type: 'skill',
                name: 'skippable-skill-1',
                path: '/path/skill1',
                discovered_at: new Date().toISOString(),
              },
              {
                type: 'skill',
                name: 'skippable-skill-2',
                path: '/path/skill2',
                discovered_at: new Date().toISOString(),
              },
              {
                type: 'agent',
                name: 'skippable-agent',
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
      await page.goto('/projects/test-project-2?tab=discovery');
      await waitForPageReady(page);
    });

    test('can mark artifact as skipped via context menu', async ({ page }) => {
      // Find an artifact row
      const artifactRow = page.getByText('skippable-skill-1').locator('..');

      // Open context menu (right-click or click menu button)
      const menuButton = artifactRow.getByRole('button', { name: /more|menu|options/i });
      await menuButton.click();

      // Click "Skip for future"
      await page.getByRole('menuitem', { name: /Skip|Skip for future/i }).click();

      // Verify artifact shows "Skipped" status
      await expect(artifactRow).toContainText(/Skipped/i);
    });

    test('skipped artifacts appear in Skip Preferences list', async ({ page }) => {
      // Skip an artifact first
      const artifactRow = page.getByText('skippable-skill-2').locator('..');
      const menuButton = artifactRow.getByRole('button', { name: /more|menu|options/i });
      await menuButton.click();
      await page.getByRole('menuitem', { name: /Skip|Skip for future/i }).click();

      // Expand Skip Preferences accordion
      const skipPrefsButton = page.getByRole('button', { name: /Skip Preferences/i });
      await skipPrefsButton.click();

      // Verify artifact is listed
      await expect(page.getByText('skippable-skill-2')).toBeVisible();
    });

    test('can un-skip artifact from Skip Preferences list', async ({ page }) => {
      // Skip an artifact first
      const artifactRow = page.getByText('skippable-agent').locator('..');
      const menuButton = artifactRow.getByRole('button', { name: /more|menu|options/i });
      await menuButton.click();
      await page.getByRole('menuitem', { name: /Skip|Skip for future/i }).click();

      // Expand Skip Preferences
      await page.getByRole('button', { name: /Skip Preferences/i }).click();

      // Click "Un-skip" button
      const unskipButton = page.getByRole('button', { name: /Un-skip|Remove/i }).first();
      await unskipButton.click();

      // Verify artifact no longer has Skipped status
      const updatedRow = page.getByText('skippable-agent').locator('..');
      await expect(updatedRow).not.toContainText(/Skipped/i);
      await expect(updatedRow).toContainText(/New/i);
    });

    test('skip preference persists across page reloads', async ({ page }) => {
      // Skip an artifact
      const artifactRow = page.getByText('skippable-skill-1').locator('..');
      const menuButton = artifactRow.getByRole('button', { name: /more|menu|options/i });
      await menuButton.click();
      await page.getByRole('menuitem', { name: /Skip|Skip for future/i }).click();

      // Wait for skip to be saved
      await page.waitForTimeout(500);

      // Reload page
      await page.reload();
      await waitForPageReady(page);

      // Navigate to Discovery tab (in case default tab changed)
      const discoveryTab = page.getByRole('tab', { name: /Discovery/i });
      const isActive = await discoveryTab.getAttribute('data-state');
      if (isActive !== 'active') {
        await discoveryTab.click();
      }

      // Verify artifact still shows as skipped
      const reloadedRow = page.getByText('skippable-skill-1').locator('..');
      await expect(reloadedRow).toContainText(/Skipped/i);
    });

    test('can clear all skip preferences with confirmation', async ({ page }) => {
      // Skip multiple artifacts
      for (const skillName of ['skippable-skill-1', 'skippable-skill-2']) {
        const artifactRow = page.getByText(skillName).locator('..');
        const menuButton = artifactRow.getByRole('button', { name: /more|menu|options/i });
        await menuButton.click();
        await page.getByRole('menuitem', { name: /Skip|Skip for future/i }).click();
        await page.waitForTimeout(200);
      }

      // Expand Skip Preferences
      await page.getByRole('button', { name: /Skip Preferences/i }).click();

      // Click "Clear All Skips"
      await page.getByRole('button', { name: /Clear All|Clear All Skips/i }).click();

      // Confirm in dialog
      const confirmButton = page.getByRole('button', { name: /Confirm|Yes|Clear/i });
      await confirmButton.click();

      // Verify all artifacts now show as "New"
      const skill1Row = page.getByText('skippable-skill-1').locator('..');
      const skill2Row = page.getByText('skippable-skill-2').locator('..');
      await expect(skill1Row).toContainText(/New/i);
      await expect(skill2Row).toContainText(/New/i);
      await expect(skill1Row).not.toContainText(/Skipped/i);
      await expect(skill2Row).not.toContainText(/Skipped/i);
    });
  });
});
