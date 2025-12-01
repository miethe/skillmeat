/**
 * End-to-end tests for Auto-Population Flow
 *
 * Tests the automatic population of form fields when users enter a GitHub URL
 * in the artifact creation/edit forms. Includes metadata fetching, field population,
 * user override handling, and error states.
 *
 * Covers:
 * - Auto-population from GitHub URL
 * - Field update behavior
 * - User edit preservation
 * - Error handling
 * - Loading states
 */
import { test, expect, Page } from '@playwright/test';
import { mockApiRoute, waitForPageLoad } from '../helpers/test-utils';

test.describe('Auto-Population Flow E2E', () => {
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
   * Helper to open add artifact form
   */
  async function openAddArtifactForm(page: Page) {
    // Look for Add button/link to open the form
    const addButton = page.getByRole('button', { name: /Add Artifact|Add|New Artifact/i });

    if (await addButton.isVisible()) {
      await addButton.click();
    } else {
      // If no button, form might already be visible or we need to navigate
      const createButton = page.getByRole('link', { name: /Create|Add/i });
      if (await createButton.isVisible()) {
        await createButton.click();
      }
    }

    // Wait for form to appear
    await page.waitForTimeout(500);
  }

  test.beforeEach(async ({ page }) => {
    // Navigate to manage page where artifact forms are likely located
    await page.goto('/manage');
    await waitForPageReady(page);
  });

  test.describe('Basic Auto-Population', () => {
    test('auto-populates form from GitHub URL', async ({ page }) => {
      // Mock GitHub metadata endpoint
      await page.route('**/api/v1/artifacts/metadata/github*', async (route) => {
        const url = new URL(route.request().url());
        const source = url.searchParams.get('source');

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            metadata: {
              title: 'Test Skill',
              description: 'A test skill for automation testing',
              author: 'test-user',
              topics: ['testing', 'automation', 'e2e'],
              url: `https://github.com/${source}`,
              fetched_at: new Date().toISOString(),
            },
          }),
        });
      });

      // Open add artifact form
      await openAddArtifactForm(page);

      // Find source input field (might have different placeholder text)
      const sourceInput = page.locator(
        'input[placeholder*="GitHub"], input[name="source"], input[id="source"]'
      );

      // Verify source input exists
      await expect(sourceInput).toBeVisible();

      // Enter GitHub URL/source
      await sourceInput.fill('test-user/repo/skills/test');

      // Wait for debounce and API call (typically 500ms debounce)
      await page.waitForTimeout(700);

      // Verify fields are populated
      const nameInput = page.locator('input[name="name"], input[id="name"]');
      await expect(nameInput).toHaveValue('Test Skill');

      const descriptionInput = page.locator(
        'textarea[name="description"], textarea[id="description"]'
      );
      await expect(descriptionInput).toHaveValue('A test skill for automation testing');
    });

    test('populates multiple fields from metadata', async ({ page }) => {
      await page.route('**/api/v1/artifacts/metadata/github*', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            metadata: {
              title: 'Comprehensive Skill',
              description: 'Full metadata skill',
              author: 'comprehensive-user',
              topics: ['tag1', 'tag2', 'tag3'],
              url: 'https://github.com/comprehensive-user/repo/skill',
              version: '2.1.0',
              fetched_at: new Date().toISOString(),
            },
          }),
        });
      });

      await openAddArtifactForm(page);

      const sourceInput = page.locator(
        'input[placeholder*="GitHub"], input[name="source"], input[id="source"]'
      );
      await sourceInput.fill('comprehensive-user/repo/skill');
      await page.waitForTimeout(700);

      // Check name
      await expect(page.locator('input[name="name"], input[id="name"]')).toHaveValue(
        'Comprehensive Skill'
      );

      // Check description
      await expect(
        page.locator('textarea[name="description"], textarea[id="description"]')
      ).toHaveValue('Full metadata skill');

      // Check if tags/topics are populated (might be displayed as chips or text)
      const pageContent = await page.content();
      expect(pageContent).toContain('tag1');
    });

    test('handles different GitHub URL formats', async ({ page }) => {
      const testCases = [
        {
          input: 'user/repo/path/to/skill',
          expectedSource: 'user/repo/path/to/skill',
        },
        {
          input: 'user/repo/skill@v1.0.0',
          expectedSource: 'user/repo/skill@v1.0.0',
        },
        {
          input: 'https://github.com/user/repo/skill',
          expectedSource: 'user/repo/skill',
        },
      ];

      for (const testCase of testCases) {
        await page.route('**/api/v1/artifacts/metadata/github*', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              success: true,
              metadata: {
                title: 'Format Test Skill',
                description: 'Testing URL format handling',
                fetched_at: new Date().toISOString(),
              },
            }),
          });
        });

        await openAddArtifactForm(page);

        const sourceInput = page.locator(
          'input[placeholder*="GitHub"], input[name="source"], input[id="source"]'
        );
        await sourceInput.fill(testCase.input);
        await page.waitForTimeout(700);

        // Verify auto-population occurred
        const nameInput = page.locator('input[name="name"], input[id="name"]');
        await expect(nameInput).toHaveValue('Format Test Skill');

        // Close form or reset for next iteration
        const cancelButton = page.getByRole('button', { name: /Cancel|Close/i });
        if (await cancelButton.isVisible()) {
          await cancelButton.click();
          await page.waitForTimeout(300);
        }
      }
    });
  });

  test.describe('User Edit Preservation', () => {
    test('preserves user edits over auto-populated values', async ({ page }) => {
      await page.route('**/api/v1/artifacts/metadata/github*', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            metadata: {
              title: 'Auto Name',
              description: 'Auto Description',
              topics: ['auto-tag'],
              fetched_at: new Date().toISOString(),
            },
          }),
        });
      });

      await openAddArtifactForm(page);

      // Fill name manually first
      const nameInput = page.locator('input[name="name"], input[id="name"]');
      await nameInput.fill('My Custom Name');

      // Verify manual entry
      await expect(nameInput).toHaveValue('My Custom Name');

      // Then enter source (triggers auto-population)
      const sourceInput = page.locator(
        'input[placeholder*="GitHub"], input[name="source"], input[id="source"]'
      );
      await sourceInput.fill('user/repo/skill');

      // Wait for auto-population attempt
      await page.waitForTimeout(700);

      // Name should NOT be overwritten (user already filled it)
      await expect(nameInput).toHaveValue('My Custom Name');

      // But empty fields should be populated
      const descriptionInput = page.locator(
        'textarea[name="description"], textarea[id="description"]'
      );
      await expect(descriptionInput).toHaveValue('Auto Description');
    });

    test('allows user to override auto-populated values', async ({ page }) => {
      await page.route('**/api/v1/artifacts/metadata/github*', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            metadata: {
              title: 'Auto Title',
              description: 'Auto Description',
              fetched_at: new Date().toISOString(),
            },
          }),
        });
      });

      await openAddArtifactForm(page);

      // Trigger auto-population first
      const sourceInput = page.locator(
        'input[placeholder*="GitHub"], input[name="source"], input[id="source"]'
      );
      await sourceInput.fill('user/repo/skill');
      await page.waitForTimeout(700);

      // Verify auto-populated
      const nameInput = page.locator('input[name="name"], input[id="name"]');
      await expect(nameInput).toHaveValue('Auto Title');

      // User overrides
      await nameInput.clear();
      await nameInput.fill('User Override Title');

      // Verify override persists
      await expect(nameInput).toHaveValue('User Override Title');
    });

    test('does not overwrite fields when source changes after user edits', async ({ page }) => {
      await page.route('**/api/v1/artifacts/metadata/github*', async (route) => {
        const url = new URL(route.request().url());
        const source = url.searchParams.get('source') || '';

        const title = source.includes('first') ? 'First Skill' : 'Second Skill';

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            metadata: {
              title,
              description: `Description for ${title}`,
              fetched_at: new Date().toISOString(),
            },
          }),
        });
      });

      await openAddArtifactForm(page);

      const sourceInput = page.locator(
        'input[placeholder*="GitHub"], input[name="source"], input[id="source"]'
      );
      const nameInput = page.locator('input[name="name"], input[id="name"]');

      // First auto-population
      await sourceInput.fill('user/repo/first-skill');
      await page.waitForTimeout(700);
      await expect(nameInput).toHaveValue('First Skill');

      // User edits the name
      await nameInput.clear();
      await nameInput.fill('My Custom Skill Name');

      // User changes source (should not overwrite manual edit)
      await sourceInput.clear();
      await sourceInput.fill('user/repo/second-skill');
      await page.waitForTimeout(700);

      // Name should still be user's custom value
      await expect(nameInput).toHaveValue('My Custom Skill Name');
    });
  });

  test.describe('Error Handling', () => {
    test('handles fetch errors gracefully', async ({ page }) => {
      await page.route('**/api/v1/artifacts/metadata/github*', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: false,
            error: 'Repository not found',
          }),
        });
      });

      await openAddArtifactForm(page);

      const sourceInput = page.locator(
        'input[placeholder*="GitHub"], input[name="source"], input[id="source"]'
      );
      await sourceInput.fill('nonexistent/repo/path');
      await page.waitForTimeout(700);

      // Error should be shown
      const errorMessage = page.getByText(/not found|error/i);
      await expect(errorMessage).toBeVisible({ timeout: 5000 });

      // Form should still work - user can fill manually
      const nameInput = page.locator('input[name="name"], input[id="name"]');
      await nameInput.fill('Manual Entry');
      await expect(nameInput).toHaveValue('Manual Entry');
    });

    test('handles network errors', async ({ page }) => {
      await page.route('**/api/v1/artifacts/metadata/github*', async (route) => {
        await route.abort('failed');
      });

      await openAddArtifactForm(page);

      const sourceInput = page.locator(
        'input[placeholder*="GitHub"], input[name="source"], input[id="source"]'
      );
      await sourceInput.fill('user/repo/skill');
      await page.waitForTimeout(700);

      // Form should remain functional despite network error
      const nameInput = page.locator('input[name="name"], input[id="name"]');
      await expect(nameInput).toBeEnabled();

      // User can still fill form manually
      await nameInput.fill('Fallback Name');
      await expect(nameInput).toHaveValue('Fallback Name');
    });

    test('handles malformed metadata response', async ({ page }) => {
      await page.route('**/api/v1/artifacts/metadata/github*', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            metadata: {
              // Missing expected fields
              fetched_at: new Date().toISOString(),
            },
          }),
        });
      });

      await openAddArtifactForm(page);

      const sourceInput = page.locator(
        'input[placeholder*="GitHub"], input[name="source"], input[id="source"]'
      );
      await sourceInput.fill('user/repo/skill');
      await page.waitForTimeout(700);

      // Form should not crash, fields should remain empty/editable
      const nameInput = page.locator('input[name="name"], input[id="name"]');
      await expect(nameInput).toBeEnabled();
      await nameInput.fill('Manual Name');
      await expect(nameInput).toHaveValue('Manual Name');
    });

    test('handles 404 errors', async ({ page }) => {
      await page.route('**/api/v1/artifacts/metadata/github*', async (route) => {
        await route.fulfill({
          status: 404,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: 'Not found',
          }),
        });
      });

      await openAddArtifactForm(page);

      const sourceInput = page.locator(
        'input[placeholder*="GitHub"], input[name="source"], input[id="source"]'
      );
      await sourceInput.fill('missing/repo/skill');
      await page.waitForTimeout(700);

      // Should show appropriate error message
      const errorIndicator = page.getByText(/not found|unable to fetch/i);
      await expect(errorIndicator).toBeVisible({ timeout: 5000 });
    });

    test('handles 500 server errors', async ({ page }) => {
      await page.route('**/api/v1/artifacts/metadata/github*', async (route) => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: 'Internal server error',
          }),
        });
      });

      await openAddArtifactForm(page);

      const sourceInput = page.locator(
        'input[placeholder*="GitHub"], input[name="source"], input[id="source"]'
      );
      await sourceInput.fill('user/repo/skill');
      await page.waitForTimeout(700);

      // Should handle gracefully, not crash the form
      const nameInput = page.locator('input[name="name"], input[id="name"]');
      await expect(nameInput).toBeEnabled();
    });
  });

  test.describe('Loading States', () => {
    test('shows loading indicator while fetching metadata', async ({ page }) => {
      let resolveMetadata: (value: unknown) => void;
      const metadataPromise = new Promise((resolve) => {
        resolveMetadata = resolve;
      });

      await page.route('**/api/v1/artifacts/metadata/github*', async (route) => {
        await metadataPromise; // Wait before responding

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            metadata: {
              title: 'Delayed Skill',
              description: 'This took a while to fetch',
              fetched_at: new Date().toISOString(),
            },
          }),
        });
      });

      await openAddArtifactForm(page);

      const sourceInput = page.locator(
        'input[placeholder*="GitHub"], input[name="source"], input[id="source"]'
      );
      await sourceInput.fill('user/repo/skill');

      // Wait for debounce
      await page.waitForTimeout(600);

      // Loading indicator should be visible
      const loadingIndicator = page.locator(
        '[class*="loading"], [class*="spinner"], [aria-busy="true"]'
      );
      await expect(loadingIndicator).toBeVisible({ timeout: 2000 });

      // Resolve the metadata fetch
      resolveMetadata!(null);

      // Wait for response
      await page.waitForTimeout(500);

      // Loading should be gone
      await expect(loadingIndicator).not.toBeVisible();

      // Fields should be populated
      await expect(page.locator('input[name="name"], input[id="name"]')).toHaveValue(
        'Delayed Skill'
      );
    });

    test('does not block form interaction while fetching', async ({ page }) => {
      await page.route('**/api/v1/artifacts/metadata/github*', async (route) => {
        // Slow response
        await new Promise((resolve) => setTimeout(resolve, 2000));

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            metadata: {
              title: 'Slow Skill',
              fetched_at: new Date().toISOString(),
            },
          }),
        });
      });

      await openAddArtifactForm(page);

      const sourceInput = page.locator(
        'input[placeholder*="GitHub"], input[name="source"], input[id="source"]'
      );
      await sourceInput.fill('user/repo/skill');
      await page.waitForTimeout(600);

      // User should still be able to interact with other fields
      const descriptionInput = page.locator(
        'textarea[name="description"], textarea[id="description"]'
      );
      await descriptionInput.fill('User can still edit while fetching');
      await expect(descriptionInput).toHaveValue('User can still edit while fetching');
    });
  });

  test.describe('Debouncing', () => {
    test('debounces metadata requests', async ({ page }) => {
      let requestCount = 0;

      await page.route('**/api/v1/artifacts/metadata/github*', async (route) => {
        requestCount++;

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            metadata: {
              title: `Skill ${requestCount}`,
              fetched_at: new Date().toISOString(),
            },
          }),
        });
      });

      await openAddArtifactForm(page);

      const sourceInput = page.locator(
        'input[placeholder*="GitHub"], input[name="source"], input[id="source"]'
      );

      // Type quickly (simulating user typing)
      await sourceInput.fill('u');
      await page.waitForTimeout(100);
      await sourceInput.fill('us');
      await page.waitForTimeout(100);
      await sourceInput.fill('use');
      await page.waitForTimeout(100);
      await sourceInput.fill('user/repo/skill');

      // Wait for debounce period + request
      await page.waitForTimeout(1000);

      // Should have only made 1 request (debounced)
      expect(requestCount).toBeLessThanOrEqual(1);
    });

    test('cancels previous requests when source changes', async ({ page }) => {
      const requests: string[] = [];

      await page.route('**/api/v1/artifacts/metadata/github*', async (route) => {
        const url = new URL(route.request().url());
        const source = url.searchParams.get('source') || '';
        requests.push(source);

        // Slow response
        await new Promise((resolve) => setTimeout(resolve, 1000));

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            metadata: {
              title: `Skill for ${source}`,
              fetched_at: new Date().toISOString(),
            },
          }),
        });
      });

      await openAddArtifactForm(page);

      const sourceInput = page.locator(
        'input[placeholder*="GitHub"], input[name="source"], input[id="source"]'
      );

      // Change source multiple times
      await sourceInput.fill('user/repo/first');
      await page.waitForTimeout(600);

      await sourceInput.clear();
      await sourceInput.fill('user/repo/second');
      await page.waitForTimeout(600);

      await sourceInput.clear();
      await sourceInput.fill('user/repo/final');

      // Wait for all requests to complete
      await page.waitForTimeout(2000);

      // Only the last request's data should be shown
      const nameInput = page.locator('input[name="name"], input[id="name"]');
      const finalValue = await nameInput.inputValue();

      // Should be from final source, not intermediate ones
      expect(finalValue).toContain('final');
    });
  });

  test.describe('Edge Cases', () => {
    test('handles empty metadata response', async ({ page }) => {
      await page.route('**/api/v1/artifacts/metadata/github*', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            metadata: {},
          }),
        });
      });

      await openAddArtifactForm(page);

      const sourceInput = page.locator(
        'input[placeholder*="GitHub"], input[name="source"], input[id="source"]'
      );
      await sourceInput.fill('user/repo/skill');
      await page.waitForTimeout(700);

      // Fields should remain empty but editable
      const nameInput = page.locator('input[name="name"], input[id="name"]');
      await nameInput.fill('Manual Name');
      await expect(nameInput).toHaveValue('Manual Name');
    });

    test('handles very long metadata values', async ({ page }) => {
      const longDescription = 'A'.repeat(5000);

      await page.route('**/api/v1/artifacts/metadata/github*', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            metadata: {
              title: 'Long Metadata Skill',
              description: longDescription,
              fetched_at: new Date().toISOString(),
            },
          }),
        });
      });

      await openAddArtifactForm(page);

      const sourceInput = page.locator(
        'input[placeholder*="GitHub"], input[name="source"], input[id="source"]'
      );
      await sourceInput.fill('user/repo/skill');
      await page.waitForTimeout(700);

      // Should populate without error (might be truncated)
      const descriptionInput = page.locator(
        'textarea[name="description"], textarea[id="description"]'
      );
      const value = await descriptionInput.inputValue();
      expect(value.length).toBeGreaterThan(0);
    });

    test('handles special characters in metadata', async ({ page }) => {
      await page.route('**/api/v1/artifacts/metadata/github*', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            metadata: {
              title: 'Skill with "quotes" & <brackets>',
              description: "Description with 'apostrophes' and\nnewlines",
              fetched_at: new Date().toISOString(),
            },
          }),
        });
      });

      await openAddArtifactForm(page);

      const sourceInput = page.locator(
        'input[placeholder*="GitHub"], input[name="source"], input[id="source"]'
      );
      await sourceInput.fill('user/repo/skill');
      await page.waitForTimeout(700);

      // Should handle special characters correctly
      const nameInput = page.locator('input[name="name"], input[id="name"]');
      await expect(nameInput).toHaveValue('Skill with "quotes" & <brackets>');
    });
  });
});
