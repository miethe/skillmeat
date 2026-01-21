/**
 * End-to-end tests for Path Tags Checkbox in BulkImportModal
 *
 * Tests the "Apply approved path tags" checkbox that controls
 * whether path-based tags are applied during artifact import.
 *
 * Test Coverage:
 * - Checkbox visibility and default state
 * - Checkbox toggle functionality
 * - State persistence during artifact selection
 * - Checkbox disabled during import
 * - Import request includes apply_path_tags parameter
 *
 * NOTE: This test focuses on the UI checkbox behavior.
 * Backend path tags logic is tested in integration tests.
 */
import { test, expect, Page } from '@playwright/test';

test.describe('Path Tags Import Checkbox', () => {
  const TEST_PROJECT_ID = 'path-tags-test-project';
  const TEST_PROJECT_PATH = '/path/to/path-tags-project';

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
   * Mock the project API endpoint
   */
  async function mockProjectApi(page: Page) {
    await page.route(`**/api/v1/projects/${TEST_PROJECT_ID}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: TEST_PROJECT_ID,
          name: 'Path Tags Test Project',
          path: TEST_PROJECT_PATH,
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
    });
  }

  /**
   * Mock the artifacts list API
   */
  async function mockArtifactsApi(page: Page) {
    await page.route('**/api/v1/artifacts', async (route) => {
      if (!route.request().url().includes('/discover')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            artifacts: [],
            total: 0,
          }),
        });
      }
    });
  }

  /**
   * Mock the discovery API with specific artifacts
   */
  async function mockDiscoveryApi(page: Page, artifacts: any[]) {
    const encodedPath = encodeURIComponent(TEST_PROJECT_PATH);
    await page.route(`**/api/v1/artifacts/discover/project/${encodedPath}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          discovered_count: artifacts.length,
          importable_count: artifacts.length,
          artifacts,
          errors: [],
          scan_duration_ms: 100,
        }),
      });
    });
  }

  /**
   * Helper to open import modal
   */
  async function openImportModal(page: Page) {
    // Trigger discovery by navigating to Discovery tab
    const discoveryTab = page.getByRole('tab', { name: /Discovery/i });
    await discoveryTab.click();

    // Wait for artifacts to load
    await page.waitForTimeout(500);

    // Click "Import All" button to open modal
    const importAllButton = page.getByRole('button', { name: /Import All|Bulk Import/i });
    await importAllButton.click();

    // Wait for modal to open
    await page.waitForSelector('[role="dialog"]', { timeout: 5000 });
  }

  const mockArtifact = {
    type: 'skill',
    name: 'test-skill',
    source: 'local/skills/category/test-skill',
    version: '1.0.0',
    scope: 'user',
    path: `${TEST_PROJECT_PATH}/.claude/skills/category/test-skill`,
    discovered_at: new Date().toISOString(),
    status: 'success',
  };

  test.beforeEach(async ({ page }) => {
    // Mock APIs before navigation
    await mockProjectApi(page);
    await mockArtifactsApi(page);

    // Navigate to project page
    await page.goto(`/projects/${TEST_PROJECT_ID}`);
    await waitForPageReady(page);
  });

  test('checkbox is visible and checked by default', async ({ page }) => {
    await mockDiscoveryApi(page, [mockArtifact]);
    await openImportModal(page);

    // Find the "Apply approved path tags" checkbox
    const checkbox = page.locator('#apply-path-tags');
    await expect(checkbox).toBeVisible();
    await expect(checkbox).toBeChecked();

    // Verify label is visible
    const label = page.getByText('Apply approved path tags');
    await expect(label).toBeVisible();

    // Verify help text is visible
    const helpText = page.getByText('Automatically tag artifacts based on their source path');
    await expect(helpText).toBeVisible();
  });

  test('checkbox can be toggled', async ({ page }) => {
    await mockDiscoveryApi(page, [mockArtifact]);
    await openImportModal(page);

    const checkbox = page.locator('#apply-path-tags');

    // Initially checked
    await expect(checkbox).toBeChecked();

    // Uncheck the checkbox
    await checkbox.click();
    await expect(checkbox).not.toBeChecked();

    // Check it again
    await checkbox.click();
    await expect(checkbox).toBeChecked();
  });

  test('checkbox state persists during artifact selection', async ({ page }) => {
    const artifacts = [
      mockArtifact,
      {
        ...mockArtifact,
        name: 'test-skill-2',
        path: `${TEST_PROJECT_PATH}/.claude/skills/test-skill-2`,
      },
      {
        ...mockArtifact,
        type: 'command',
        name: 'test-command',
        path: `${TEST_PROJECT_PATH}/.claude/commands/test-command`,
      },
    ];

    await mockDiscoveryApi(page, artifacts);
    await openImportModal(page);

    const checkbox = page.locator('#apply-path-tags');

    // Uncheck the path tags checkbox
    await checkbox.click();
    await expect(checkbox).not.toBeChecked();

    // Select first artifact
    const firstArtifactCheckbox = page.locator(
      'input[type="checkbox"][aria-label="Select test-skill"]'
    );
    await firstArtifactCheckbox.click();

    // Verify path tags checkbox is still unchecked
    await expect(checkbox).not.toBeChecked();

    // Select second artifact
    const secondArtifactCheckbox = page.locator(
      'input[type="checkbox"][aria-label="Select test-skill-2"]'
    );
    await secondArtifactCheckbox.click();

    // Verify path tags checkbox is still unchecked
    await expect(checkbox).not.toBeChecked();

    // Deselect first artifact
    await firstArtifactCheckbox.click();

    // Verify path tags checkbox is still unchecked
    await expect(checkbox).not.toBeChecked();
  });

  test('checkbox is disabled during import', async ({ page }) => {
    await mockDiscoveryApi(page, [mockArtifact]);

    // Mock a slow import response
    await page.route('**/api/v1/artifacts/discover/import**', async (route) => {
      // Delay the response to keep the import state active
      await new Promise((resolve) => setTimeout(resolve, 2000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_requested: 1,
          total_imported: 1,
          total_failed: 0,
          total_tags_applied: 0,
          results: [
            {
              artifact_id: 'skill:test-skill',
              status: 'success',
              message: 'Successfully imported',
            },
          ],
        }),
      });
    });

    await openImportModal(page);

    const checkbox = page.locator('#apply-path-tags');

    // Select artifact
    const artifactCheckbox = page.locator('input[type="checkbox"][aria-label="Select test-skill"]');
    await artifactCheckbox.click();

    // Click Import button
    const importButton = page.getByRole('button', { name: /^Import/ });
    await importButton.click();

    // Wait a bit for import state to activate
    await page.waitForTimeout(500);

    // Verify checkbox is disabled during import
    await expect(checkbox).toBeDisabled();
  });

  test('import sends apply_path_tags=true when checkbox is checked (default)', async ({ page }) => {
    let capturedRequestBody: any = null;

    await mockDiscoveryApi(page, [mockArtifact]);

    // Capture the import request
    await page.route('**/api/v1/artifacts/discover/import**', async (route) => {
      const requestBody = route.request().postDataJSON();
      capturedRequestBody = requestBody;

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_requested: 1,
          total_imported: 1,
          total_failed: 0,
          total_tags_applied: 2,
          results: [
            {
              artifact_id: 'skill:test-skill',
              status: 'success',
              message: 'Successfully imported',
              tags_applied: ['skills', 'category'],
            },
          ],
        }),
      });
    });

    await openImportModal(page);

    // Verify checkbox is checked by default
    const checkbox = page.locator('#apply-path-tags');
    await expect(checkbox).toBeChecked();

    // Select artifact
    const artifactCheckbox = page.locator('input[type="checkbox"][aria-label="Select test-skill"]');
    await artifactCheckbox.click();

    // Click Import
    const importButton = page.getByRole('button', { name: /^Import/ });
    await importButton.click();

    // Wait for request
    await page.waitForTimeout(1000);

    // Verify request body contains apply_path_tags: true
    expect(capturedRequestBody).toBeTruthy();
    expect(capturedRequestBody.apply_path_tags).toBe(true);
  });

  test('import sends apply_path_tags=false when checkbox is unchecked', async ({ page }) => {
    let capturedRequestBody: any = null;

    await mockDiscoveryApi(page, [mockArtifact]);

    // Capture the import request
    await page.route('**/api/v1/artifacts/discover/import**', async (route) => {
      const requestBody = route.request().postDataJSON();
      capturedRequestBody = requestBody;

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_requested: 1,
          total_imported: 1,
          total_failed: 0,
          total_tags_applied: 0,
          results: [
            {
              artifact_id: 'skill:test-skill',
              status: 'success',
              message: 'Successfully imported',
            },
          ],
        }),
      });
    });

    await openImportModal(page);

    // Uncheck the path tags checkbox
    const checkbox = page.locator('#apply-path-tags');
    await checkbox.click();
    await expect(checkbox).not.toBeChecked();

    // Select artifact
    const artifactCheckbox = page.locator('input[type="checkbox"][aria-label="Select test-skill"]');
    await artifactCheckbox.click();

    // Click Import
    const importButton = page.getByRole('button', { name: /^Import/ });
    await importButton.click();

    // Wait for request
    await page.waitForTimeout(1000);

    // Verify request body contains apply_path_tags: false
    expect(capturedRequestBody).toBeTruthy();
    expect(capturedRequestBody.apply_path_tags).toBe(false);
  });

  test('checkbox can be toggled multiple times before import', async ({ page }) => {
    await mockDiscoveryApi(page, [mockArtifact]);
    await openImportModal(page);

    const checkbox = page.locator('#apply-path-tags');

    // Toggle multiple times
    await checkbox.click();
    await expect(checkbox).not.toBeChecked();

    await checkbox.click();
    await expect(checkbox).toBeChecked();

    await checkbox.click();
    await expect(checkbox).not.toBeChecked();

    await checkbox.click();
    await expect(checkbox).toBeChecked();

    // Final state should be checked
    await expect(checkbox).toBeChecked();
  });

  test('checkbox state does not affect artifact selection', async ({ page }) => {
    const artifacts = [
      mockArtifact,
      {
        ...mockArtifact,
        name: 'test-skill-2',
        path: `${TEST_PROJECT_PATH}/.claude/skills/test-skill-2`,
      },
    ];

    await mockDiscoveryApi(page, artifacts);
    await openImportModal(page);

    const checkbox = page.locator('#apply-path-tags');

    // Select all artifacts
    const selectAllCheckbox = page.locator(
      'input[type="checkbox"][aria-label="Select all artifacts"]'
    );
    await selectAllCheckbox.click();

    // Verify both artifacts are selected
    const selectedCount = page.getByText(/2 selected/i);
    await expect(selectedCount).toBeVisible();

    // Uncheck path tags
    await checkbox.click();
    await expect(checkbox).not.toBeChecked();

    // Verify artifacts are still selected
    await expect(selectedCount).toBeVisible();

    // Check path tags again
    await checkbox.click();
    await expect(checkbox).toBeChecked();

    // Verify artifacts are still selected
    await expect(selectedCount).toBeVisible();
  });

  test('import with multiple artifacts respects apply_path_tags setting', async ({ page }) => {
    let capturedRequestBody: any = null;

    const artifacts = [
      mockArtifact,
      {
        ...mockArtifact,
        type: 'command',
        name: 'test-command',
        path: `${TEST_PROJECT_PATH}/.claude/commands/utils/test-command`,
      },
      {
        ...mockArtifact,
        type: 'agent',
        name: 'test-agent',
        path: `${TEST_PROJECT_PATH}/.claude/agents/helpers/test-agent`,
      },
    ];

    await mockDiscoveryApi(page, artifacts);

    // Capture import request
    await page.route('**/api/v1/artifacts/discover/import**', async (route) => {
      const requestBody = route.request().postDataJSON();
      capturedRequestBody = requestBody;

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_requested: 3,
          total_imported: 3,
          total_failed: 0,
          total_tags_applied: 6,
          results: [
            {
              artifact_id: 'skill:test-skill',
              status: 'success',
              message: 'Successfully imported',
              tags_applied: ['skills', 'category'],
            },
            {
              artifact_id: 'command:test-command',
              status: 'success',
              message: 'Successfully imported',
              tags_applied: ['commands', 'utils'],
            },
            {
              artifact_id: 'agent:test-agent',
              status: 'success',
              message: 'Successfully imported',
              tags_applied: ['agents', 'helpers'],
            },
          ],
        }),
      });
    });

    await openImportModal(page);

    // Verify checkbox is checked
    const checkbox = page.locator('#apply-path-tags');
    await expect(checkbox).toBeChecked();

    // Select all artifacts
    const selectAllCheckbox = page.locator(
      'input[type="checkbox"][aria-label="Select all artifacts"]'
    );
    await selectAllCheckbox.click();

    // Click Import
    const importButton = page.getByRole('button', { name: /^Import/ });
    await importButton.click();

    // Wait for request
    await page.waitForTimeout(1000);

    // Verify request has apply_path_tags=true and all artifacts
    expect(capturedRequestBody).toBeTruthy();
    expect(capturedRequestBody.apply_path_tags).toBe(true);
    expect(capturedRequestBody.artifacts).toBeDefined();
    expect(capturedRequestBody.artifacts.length).toBe(3);
  });

  test('checkbox label is clickable and toggles checkbox', async ({ page }) => {
    await mockDiscoveryApi(page, [mockArtifact]);
    await openImportModal(page);

    const checkbox = page.locator('#apply-path-tags');
    const label = page.getByText('Apply approved path tags');

    // Initially checked
    await expect(checkbox).toBeChecked();

    // Click label to uncheck
    await label.click();
    await expect(checkbox).not.toBeChecked();

    // Click label to check again
    await label.click();
    await expect(checkbox).toBeChecked();
  });
});
