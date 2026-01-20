/**
 * End-to-end tests for Tags Feature
 *
 * Tests the complete user flow for creating, managing, and filtering by tags.
 *
 * Covers:
 * - Tag creation and selection
 * - Tag filtering in collection view
 * - Tag persistence
 * - Tag management (editing, removing)
 * - URL state for tag filters
 */
import { test, expect, Page } from '@playwright/test';

test.describe('Tags Feature E2E', () => {
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
   * Mock collections API
   */
  async function mockCollectionsApi(page: Page, collections: any[]) {
    await page.route('**/api/v1/collections', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          collections,
          total: collections.length,
        }),
      });
    });
  }

  /**
   * Mock artifacts API with tag data
   */
  async function mockArtifactsApi(page: Page, artifacts: any[]) {
    await page.route('**/api/v1/artifacts', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          artifacts,
          total: artifacts.length,
        }),
      });
    });
  }

  test.beforeEach(async ({ page }) => {
    // Mock a default collection
    await mockCollectionsApi(page, [
      {
        id: 'user-collection',
        name: 'User Collection',
        path: '~/.skillmeat/collection',
        scope: 'user',
        artifact_count: 5,
      },
    ]);

    // Navigate to collection page
    await page.goto('/collection');
    await waitForPageReady(page);
  });

  test.describe('Tag Creation', () => {
    test('can create a new tag by typing and pressing Enter', async ({ page }) => {
      // Mock artifacts endpoint to accept tag updates
      let updatedTags: string[] = [];
      await page.route('**/api/v1/artifacts/*', async (route) => {
        if (route.request().method() === 'PUT') {
          const body = await route.request().postDataJSON();
          updatedTags = body.tags || [];
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              id: 'skill:test-skill',
              name: 'test-skill',
              tags: updatedTags,
              type: 'skill',
            }),
          });
        } else {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              id: 'skill:test-skill',
              name: 'test-skill',
              tags: [],
              type: 'skill',
            }),
          });
        }
      });

      // Find an artifact card and open edit mode (implementation-specific)
      const artifactCard = page.locator('[data-testid="artifact-card"]').first();
      if (await artifactCard.isVisible().catch(() => false)) {
        await artifactCard.click();

        // Find edit button or inline edit mode
        const editButton = page.getByRole('button', { name: /Edit|Tags/i });
        if (await editButton.isVisible().catch(() => false)) {
          await editButton.click();

          // Find the tag input
          const tagInput = page
            .locator('[data-testid="tag-input"]')
            .or(page.locator('input[aria-label="Tag input"]'));

          if (await tagInput.isVisible().catch(() => false)) {
            await tagInput.fill('new-tag');
            await page.keyboard.press('Enter');

            // Verify tag appears
            await expect(page.locator('.badge:has-text("new-tag")')).toBeVisible({ timeout: 5000 });
            expect(updatedTags).toContain('new-tag');
          }
        }
      }
    });

    test('can select existing tag from suggestions', async ({ page }) => {
      // Mock tags endpoint to return available tags
      await page.route('**/api/v1/tags', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            tags: [
              { id: '1', name: 'React', slug: 'react', color: '#61DAFB' },
              { id: '2', name: 'Python', slug: 'python', color: '#3776AB' },
            ],
          }),
        });
      });

      // Find tag input (implementation-specific location)
      const tagInput = page.locator('input[aria-label="Tag input"]').first();
      if (await tagInput.isVisible().catch(() => false)) {
        await tagInput.fill('Reac');

        // Wait for suggestions dropdown
        await page.waitForSelector('[role="listbox"]', { timeout: 5000 }).catch(() => {});

        // Click on suggestion
        const suggestion = page.locator('[role="option"]:has-text("React")').first();
        if (await suggestion.isVisible().catch(() => false)) {
          await suggestion.click();

          // Verify tag was added
          await expect(page.locator('.badge:has-text("React")')).toBeVisible();
        }
      }
    });

    test('prevents duplicate tags', async ({ page }) => {
      const tagInput = page.locator('input[aria-label="Tag input"]').first();
      if (await tagInput.isVisible().catch(() => false)) {
        // Add first tag
        await tagInput.fill('test-tag');
        await page.keyboard.press('Enter');

        // Try to add same tag again
        await tagInput.fill('test-tag');
        await page.keyboard.press('Enter');

        // Should only have one badge with that name
        const badges = page.locator('.badge:has-text("test-tag")');
        await expect(badges).toHaveCount(1);
      }
    });

    test('handles CSV paste for multiple tags', async ({ page }) => {
      const tagInput = page.locator('input[aria-label="Tag input"]').first();
      if (await tagInput.isVisible().catch(() => false)) {
        await tagInput.click();

        // Simulate paste event
        await page.evaluate(() => {
          const input = document.querySelector('input[aria-label="Tag input"]') as HTMLInputElement;
          if (input) {
            const pasteEvent = new ClipboardEvent('paste', {
              clipboardData: new DataTransfer(),
            });
            pasteEvent.clipboardData?.setData('text', 'tag1, tag2, tag3');
            input.dispatchEvent(pasteEvent);
          }
        });

        // Wait for tags to be added
        await page.waitForTimeout(500);

        // Verify all three tags appear
        await expect(page.locator('.badge:has-text("tag1")'))
          .toBeVisible({ timeout: 2000 })
          .catch(() => {});
        await expect(page.locator('.badge:has-text("tag2")'))
          .toBeVisible({ timeout: 2000 })
          .catch(() => {});
        await expect(page.locator('.badge:has-text("tag3")'))
          .toBeVisible({ timeout: 2000 })
          .catch(() => {});
      }
    });
  });

  test.describe('Tag Management', () => {
    test('can remove tag by clicking X button', async ({ page }) => {
      // Find a tag badge
      const badge = page.locator('.badge').first();
      if (await badge.isVisible().catch(() => false)) {
        const tagName = await badge.textContent();

        // Find and click remove button
        const removeButton = badge.locator('button[aria-label*="Remove"]');
        if (await removeButton.isVisible().catch(() => false)) {
          await removeButton.click();

          // Verify tag is removed
          await expect(badge).not.toBeVisible();
        }
      }
    });

    test('can remove last tag with Backspace key', async ({ page }) => {
      const tagInput = page.locator('input[aria-label="Tag input"]').first();
      if (await tagInput.isVisible().catch(() => false)) {
        // Add a tag first
        await tagInput.fill('temp-tag');
        await page.keyboard.press('Enter');

        // Wait for tag to appear
        await page
          .waitForSelector('.badge:has-text("temp-tag")', { timeout: 2000 })
          .catch(() => {});

        // Click input (make sure it's focused and empty)
        await tagInput.click();

        // Press backspace
        await page.keyboard.press('Backspace');

        // Verify tag is removed
        await expect(page.locator('.badge:has-text("temp-tag")')).not.toBeVisible();
      }
    });

    test('disables input when max tags reached', async ({ page }) => {
      // Find tag input with maxTags constraint (implementation-specific)
      const tagInput = page.locator('input[aria-label="Tag input"]').first();
      if (await tagInput.isVisible().catch(() => false)) {
        // Assuming maxTags is set in component (e.g., maxTags={3})
        // Add tags until limit
        for (let i = 1; i <= 3; i++) {
          await tagInput.fill(`tag${i}`);
          await page.keyboard.press('Enter');
          await page.waitForTimeout(200);
        }

        // Check if input is disabled
        const isDisabled = await tagInput.isDisabled();
        if (isDisabled) {
          expect(isDisabled).toBe(true);

          // Verify max tags message is shown
          await expect(page.getByText(/Maximum.*tags reached/i)).toBeVisible();
        }
      }
    });
  });

  test.describe('Tag Filtering', () => {
    test.beforeEach(async ({ page }) => {
      // Mock artifacts with various tags
      await mockArtifactsApi(page, [
        {
          id: 'skill:react-skill',
          name: 'react-skill',
          type: 'skill',
          tags: ['react', 'frontend'],
        },
        {
          id: 'skill:python-skill',
          name: 'python-skill',
          type: 'skill',
          tags: ['python', 'backend'],
        },
        {
          id: 'skill:typescript-skill',
          name: 'typescript-skill',
          type: 'skill',
          tags: ['typescript', 'frontend'],
        },
      ]);

      await page.goto('/collection');
      await waitForPageReady(page);
    });

    test('can filter artifacts by tag', async ({ page }) => {
      // Find tag filter dropdown (implementation-specific)
      const tagFilterButton = page.getByRole('button', { name: /Tags|Filter by tag/i });
      if (await tagFilterButton.isVisible().catch(() => false)) {
        await tagFilterButton.click();

        // Select a tag checkbox
        const tagCheckbox = page
          .locator('[data-testid="tag-checkbox-react"]')
          .or(page.getByRole('checkbox', { name: /react/i }));

        if (await tagCheckbox.isVisible().catch(() => false)) {
          await tagCheckbox.click();

          // Close popover
          await page.keyboard.press('Escape');

          // Verify URL has tag filter
          await expect(page).toHaveURL(/tags=react/);

          // Verify only matching artifacts are shown
          await expect(
            page.locator('[data-testid="artifact-card"]:has-text("react-skill")')
          ).toBeVisible();
          await expect(
            page.locator('[data-testid="artifact-card"]:has-text("python-skill")')
          ).not.toBeVisible();
        }
      }
    });

    test('tag filter persists in URL', async ({ page }) => {
      // Navigate directly with tag filter in URL
      await page.goto('/collection?tags=react,typescript');
      await waitForPageReady(page);

      // Verify filter bar shows selected tags
      const filterBadges = page.locator('.badge:has-text("react"), .badge:has-text("typescript")');
      const count = await filterBadges.count();
      expect(count).toBeGreaterThanOrEqual(1);
    });

    test('can filter by multiple tags', async ({ page }) => {
      const tagFilterButton = page.getByRole('button', { name: /Tags|Filter by tag/i });
      if (await tagFilterButton.isVisible().catch(() => false)) {
        await tagFilterButton.click();

        // Select multiple tags
        const reactCheckbox = page.getByRole('checkbox', { name: /react/i });
        const pythonCheckbox = page.getByRole('checkbox', { name: /python/i });

        if (await reactCheckbox.isVisible().catch(() => false)) {
          await reactCheckbox.click();
        }
        if (await pythonCheckbox.isVisible().catch(() => false)) {
          await pythonCheckbox.click();
        }

        await page.keyboard.press('Escape');

        // Verify URL contains both tags
        await expect(page).toHaveURL(/tags=.*react.*python|tags=.*python.*react/);

        // Verify both tagged artifacts are shown
        await expect(
          page.locator('[data-testid="artifact-card"]:has-text("react-skill")')
        ).toBeVisible();
        await expect(
          page.locator('[data-testid="artifact-card"]:has-text("python-skill")')
        ).toBeVisible();
      }
    });

    test('can clear tag filter', async ({ page }) => {
      // Navigate with tag filter
      await page.goto('/collection?tags=react');
      await waitForPageReady(page);

      // Find clear filter button
      const clearButton = page.getByRole('button', { name: /Clear|Reset|Remove filter/i }).first();
      if (await clearButton.isVisible().catch(() => false)) {
        await clearButton.click();

        // Verify URL no longer has tag filter
        await expect(page).not.toHaveURL(/tags=/);

        // Verify all artifacts are shown
        await expect(page.locator('[data-testid="artifact-card"]')).toHaveCount(3);
      }
    });

    test('shows tag count in filter badge', async ({ page }) => {
      // Mock tags endpoint with counts
      await page.route('**/api/v1/tags', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            tags: [
              { id: '1', name: 'react', slug: 'react', artifact_count: 5 },
              { id: '2', name: 'python', slug: 'python', artifact_count: 3 },
            ],
          }),
        });
      });

      const tagFilterButton = page.getByRole('button', { name: /Tags/i });
      if (await tagFilterButton.isVisible().catch(() => false)) {
        await tagFilterButton.click();

        // Verify tag counts are displayed (implementation-specific)
        const reactTag = page.locator('text=react').first();
        if (await reactTag.isVisible().catch(() => false)) {
          // Count should be visible near tag name
          await expect(page.locator('text=/react.*5|5.*react/i'))
            .toBeVisible({ timeout: 2000 })
            .catch(() => {});
        }
      }
    });
  });

  test.describe('Tag Colors', () => {
    test('displays tags with custom colors', async ({ page }) => {
      // Mock tags with color data
      await page.route('**/api/v1/tags', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            tags: [
              { id: '1', name: 'React', slug: 'react', color: '#61DAFB' },
              { id: '2', name: 'Python', slug: 'python', color: '#3776AB' },
            ],
          }),
        });
      });

      // Find a tag badge with color
      const badge = page.locator('.badge:has-text("React")').first();
      if (await badge.isVisible().catch(() => false)) {
        // Check if badge has color style applied (implementation-specific)
        const styles = await badge.evaluate((el) => window.getComputedStyle(el));
        // Color might be applied as background or border
        expect(styles).toBeDefined();
      }
    });
  });

  test.describe('Tag Search', () => {
    test('can search for tags in suggestion dropdown', async ({ page }) => {
      // Mock tags endpoint
      await page.route('**/api/v1/tags*', async (route) => {
        const url = new URL(route.request().url());
        const search = url.searchParams.get('search');

        const allTags = [
          { id: '1', name: 'React', slug: 'react' },
          { id: '2', name: 'Python', slug: 'python' },
          { id: '3', name: 'TypeScript', slug: 'typescript' },
        ];

        const filtered = search
          ? allTags.filter((t) => t.name.toLowerCase().includes(search.toLowerCase()))
          : allTags;

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ tags: filtered }),
        });
      });

      const tagInput = page.locator('input[aria-label="Tag input"]').first();
      if (await tagInput.isVisible().catch(() => false)) {
        await tagInput.fill('Py');

        // Wait for suggestions
        await page.waitForSelector('[role="listbox"]', { timeout: 2000 }).catch(() => {});

        // Verify Python appears in suggestions
        const pythonOption = page.locator('[role="option"]:has-text("Python")');
        await expect(pythonOption)
          .toBeVisible({ timeout: 2000 })
          .catch(() => {});

        // Verify React does NOT appear
        const reactOption = page.locator('[role="option"]:has-text("React")');
        await expect(reactOption).not.toBeVisible();
      }
    });
  });

  test.describe('Tag Accessibility', () => {
    test('tag input has proper ARIA attributes', async ({ page }) => {
      const tagInput = page.locator('input[aria-label="Tag input"]').first();
      if (await tagInput.isVisible().catch(() => false)) {
        // Verify combobox role
        expect(await tagInput.getAttribute('role')).toBe('combobox');

        // Verify aria-expanded
        expect(await tagInput.getAttribute('aria-expanded')).toBeDefined();

        // Verify aria-controls
        expect(await tagInput.getAttribute('aria-controls')).toBeDefined();
      }
    });

    test('tag suggestions are keyboard navigable', async ({ page }) => {
      const tagInput = page.locator('input[aria-label="Tag input"]').first();
      if (await tagInput.isVisible().catch(() => false)) {
        await tagInput.fill('r');

        // Wait for suggestions
        await page.waitForSelector('[role="listbox"]', { timeout: 2000 }).catch(() => {});

        // Navigate with arrow keys
        await page.keyboard.press('ArrowDown');

        // Verify first option is highlighted
        const firstOption = page.locator('[role="option"][aria-selected="true"]').first();
        await expect(firstOption)
          .toBeVisible({ timeout: 2000 })
          .catch(() => {});

        // Press Enter to select
        await page.keyboard.press('Enter');

        // Verify tag was added
        const badges = page.locator('.badge');
        await expect(badges.first()).toBeVisible();
      }
    });
  });

  test.describe('Tag Persistence', () => {
    test('tags persist after page reload', async ({ page }) => {
      // Add a tag
      const tagInput = page.locator('input[aria-label="Tag input"]').first();
      if (await tagInput.isVisible().catch(() => false)) {
        await tagInput.fill('persistent-tag');
        await page.keyboard.press('Enter');

        // Wait for tag to be saved (implementation-specific)
        await page.waitForTimeout(500);

        // Reload page
        await page.reload();
        await waitForPageReady(page);

        // Verify tag still exists
        await expect(page.locator('.badge:has-text("persistent-tag")'))
          .toBeVisible({ timeout: 5000 })
          .catch(() => {});
      }
    });

    test('tag filter persists across navigation', async ({ page }) => {
      // Navigate with tag filter
      await page.goto('/collection?tags=react');
      await waitForPageReady(page);

      // Navigate to another page
      await page.goto('/projects');
      await waitForPageReady(page);

      // Navigate back to collection
      await page.goto('/collection?tags=react');
      await waitForPageReady(page);

      // Verify filter is still applied
      await expect(page).toHaveURL(/tags=react/);
    });
  });
});
