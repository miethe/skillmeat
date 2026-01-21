/**
 * End-to-End Tests for Path Tag Review Workflow
 *
 * Tests the complete user workflow for reviewing, approving, and rejecting
 * path-based tag suggestions in the catalog entry modal.
 *
 * Test Coverage:
 * - Opening catalog entry and viewing suggested tags
 * - Approving pending segments
 * - Rejecting pending segments
 * - Excluded segments display (non-interactive)
 * - Changes persist after modal close/reopen
 * - Summary counts update correctly
 * - Error handling and loading states
 * - Accessibility (keyboard navigation, ARIA)
 */

import { test, expect, type Page } from '@playwright/test';
import {
  waitForPageLoad,
  mockApiRoute,
  expectModalOpen,
  expectModalClosed,
} from '../helpers/test-utils';

// ============================================================================
// Mock Data
// ============================================================================

const mockSource = {
  id: 'source-123',
  owner: 'anthropics',
  repo_name: 'skills',
  ref: 'main',
  root_hint: '',
  repo_url: 'https://github.com/anthropics/skills',
  trust_level: 'official',
  artifact_count: 3,
  last_scan_at: '2025-01-04T10:00:00Z',
  created_at: '2025-01-01T10:00:00Z',
};

const mockCatalogEntry = {
  id: 'entry-1',
  source_id: 'source-123',
  name: 'ai-engineer',
  artifact_type: 'skill',
  path: 'categories/05-data-ai/ai-engineer',
  status: 'new',
  confidence_score: 95,
  upstream_url: 'https://github.com/anthropics/skills/tree/main/categories/05-data-ai/ai-engineer',
  detected_at: '2025-01-04T10:00:00Z',
  detected_sha: 'abc1234567890',
  detected_version: 'v1.0.0',
  score_breakdown: {
    has_readme: { score: 20, max: 20, reason: 'README.md found' },
    file_structure: { score: 15, max: 20, reason: 'Standard structure' },
    metadata: { score: 30, max: 30, reason: 'Complete metadata' },
    content_quality: { score: 30, max: 30, reason: 'High quality content' },
  },
};

const mockCatalogResponse = {
  items: [mockCatalogEntry],
  total: 1,
  page: 1,
  page_size: 20,
  has_next: false,
  counts_by_type: { skill: 1 },
  counts_by_status: { new: 1 },
};

const mockPathSegments = {
  entry_id: 'entry-1',
  raw_path: 'categories/05-data-ai/ai-engineer',
  extracted: [
    {
      segment: 'categories',
      normalized: 'categories',
      status: 'pending',
      depth: 0,
      reason: null,
    },
    {
      segment: '05-data-ai',
      normalized: 'data-ai',
      status: 'pending',
      depth: 1,
      reason: null,
    },
    {
      segment: 'ai-engineer',
      normalized: 'ai-engineer',
      status: 'pending',
      depth: 2,
      reason: null,
    },
  ],
  extracted_at: '2025-01-04T10:00:00Z',
};

const mockPathSegmentsWithExcluded = {
  entry_id: 'entry-2',
  raw_path: 'src/lib/utils/helpers.ts',
  extracted: [
    {
      segment: 'src',
      normalized: 'src',
      status: 'excluded',
      depth: 0,
      reason: 'Common build directory',
    },
    {
      segment: 'lib',
      normalized: 'lib',
      status: 'excluded',
      depth: 1,
      reason: 'Common library directory',
    },
    {
      segment: 'utils',
      normalized: 'utils',
      status: 'pending',
      depth: 2,
      reason: null,
    },
  ],
  extracted_at: '2025-01-04T10:00:00Z',
};

// ============================================================================
// Helper Functions
// ============================================================================

async function setupMockApiRoutes(page: Page) {
  // Mock sources list
  await mockApiRoute(page, '/api/v1/marketplace/sources*', {
    items: [mockSource],
    total: 1,
    page: 1,
    page_size: 20,
    has_next: false,
  });

  // Mock source detail
  await mockApiRoute(page, `/api/v1/marketplace/sources/${mockSource.id}`, mockSource);

  // Mock catalog
  await mockApiRoute(
    page,
    `/api/v1/marketplace/sources/${mockSource.id}/catalog*`,
    mockCatalogResponse
  );

  // Mock path segments endpoint (GET)
  await mockApiRoute(
    page,
    `/api/v1/marketplace/sources/${mockSource.id}/catalog/${mockCatalogEntry.id}/path-segments`,
    mockPathSegments
  );
}

async function navigateToSourceDetailPage(page: Page, sourceId: string = mockSource.id) {
  await page.goto(`/marketplace/sources/${sourceId}`);
  await waitForPageLoad(page);
}

async function openCatalogEntryModal(page: Page) {
  // Wait for catalog entries to load
  await expect(page.getByText('ai-engineer')).toBeVisible({ timeout: 10000 });

  // Click on the catalog entry to open modal
  const entryCard = page.locator('[role="button"]').filter({ hasText: 'ai-engineer' }).first();
  await entryCard.click();

  // Verify modal opened
  const modal = page.locator('[role="dialog"]');
  await expect(modal).toBeVisible({ timeout: 5000 });
}

async function navigateToSuggestedTagsTab(page: Page) {
  // Click on "Suggested Tags" tab
  const tagsTab = page.locator('[role="tab"]').filter({ hasText: 'Suggested Tags' });
  await tagsTab.click();

  // Wait for tab content to be visible
  await expect(page.getByText('Path-Based Tag Suggestions')).toBeVisible();
}

// ============================================================================
// Test Suite
// ============================================================================

test.describe('Path Tag Review Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApiRoutes(page);
    await navigateToSourceDetailPage(page);
  });

  test.describe('Opening and Viewing', () => {
    test('user can open catalog entry and navigate to Suggested Tags tab', async ({ page }) => {
      await openCatalogEntryModal(page);
      await navigateToSuggestedTagsTab(page);

      // Verify tab is active
      const tagsTab = page.locator('[role="tab"]').filter({ hasText: 'Suggested Tags' });
      await expect(tagsTab).toHaveAttribute('data-state', 'active');

      // Verify content is displayed
      await expect(page.getByText('Path-Based Tag Suggestions')).toBeVisible();
      await expect(
        page.getByText('Review and approve tags extracted from the artifact path')
      ).toBeVisible();
    });

    test('displays all extracted segments with correct statuses', async ({ page }) => {
      await openCatalogEntryModal(page);
      await navigateToSuggestedTagsTab(page);

      // Verify all segments are displayed
      await expect(page.getByText('categories')).toBeVisible();
      await expect(page.getByText('05-data-ai')).toBeVisible();
      await expect(page.getByText('ai-engineer')).toBeVisible();

      // Verify normalized values are shown
      await expect(page.getByText('data-ai')).toBeVisible();

      // Verify pending badges are displayed
      const pendingBadges = page.locator('text=Pending');
      await expect(pendingBadges).toHaveCount(3);
    });

    test('displays summary with correct counts', async ({ page }) => {
      await openCatalogEntryModal(page);
      await navigateToSuggestedTagsTab(page);

      // Verify summary footer is present
      await expect(page.getByText(/3 pending/)).toBeVisible();
      await expect(page.getByText(/0 approved/)).toBeVisible();
      await expect(page.getByText(/0 rejected/)).toBeVisible();
    });
  });

  test.describe('Approving Segments', () => {
    test('user can approve a pending segment', async ({ page }) => {
      // Mock PATCH endpoint for status update
      let patchCalled = false;
      let patchRequestBody: any = null;

      await page.route(
        `**/api/v1/marketplace/sources/${mockSource.id}/catalog/${mockCatalogEntry.id}/path-segments`,
        async (route) => {
          if (route.request().method() === 'PATCH') {
            patchCalled = true;
            patchRequestBody = await route.request().postDataJSON();

            // Return updated segments with approved status
            const updatedSegments = { ...mockPathSegments };
            updatedSegments.extracted = mockPathSegments.extracted.map((seg) =>
              seg.segment === patchRequestBody.segment
                ? { ...seg, status: patchRequestBody.status }
                : seg
            );

            await route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify({
                segment: patchRequestBody.segment,
                status: patchRequestBody.status,
                updated_at: new Date().toISOString(),
              }),
            });
          } else {
            await route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify(mockPathSegments),
            });
          }
        }
      );

      await openCatalogEntryModal(page);
      await navigateToSuggestedTagsTab(page);

      // Find the approve button for "categories" segment
      const categoriesRow = page.locator('div', { has: page.locator('text="categories"') }).first();
      const approveButton = categoriesRow.locator('button[aria-label="Approve segment"]');

      await approveButton.click();

      // Verify PATCH was called with correct data
      await expect.poll(() => patchCalled).toBe(true);
      expect(patchRequestBody).toEqual({
        segment: 'categories',
        status: 'approved',
      });

      // Verify loading spinner appears during request (if we can catch it)
      // This is timing-sensitive, so we'll skip for now

      // Verify status badge changes to "Approved"
      await expect(categoriesRow.locator('text=Approved')).toBeVisible({ timeout: 5000 });
      await expect(categoriesRow.locator('text=Pending')).not.toBeVisible();
    });

    test('approve button shows loading state while request is pending', async ({ page }) => {
      // Mock slow PATCH endpoint
      await page.route(
        `**/api/v1/marketplace/sources/${mockSource.id}/catalog/${mockCatalogEntry.id}/path-segments`,
        async (route) => {
          if (route.request().method() === 'PATCH') {
            // Delay response
            await page.waitForTimeout(1000);
            await route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify({
                segment: 'categories',
                status: 'approved',
                updated_at: new Date().toISOString(),
              }),
            });
          } else {
            await route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify(mockPathSegments),
            });
          }
        }
      );

      await openCatalogEntryModal(page);
      await navigateToSuggestedTagsTab(page);

      const categoriesRow = page.locator('div', { has: page.locator('text="categories"') }).first();
      const approveButton = categoriesRow.locator('button[aria-label="Approve segment"]');

      await approveButton.click();

      // Verify loading spinner is visible
      await expect(categoriesRow.locator('[class*="animate-spin"]')).toBeVisible();

      // Verify button is disabled during loading
      await expect(approveButton).toBeDisabled();
    });

    test('summary counts update after approving segment', async ({ page }) => {
      await page.route(
        `**/api/v1/marketplace/sources/${mockSource.id}/catalog/${mockCatalogEntry.id}/path-segments`,
        async (route) => {
          if (route.request().method() === 'PATCH') {
            await route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify({
                segment: 'categories',
                status: 'approved',
                updated_at: new Date().toISOString(),
              }),
            });
          } else {
            await route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify(mockPathSegments),
            });
          }
        }
      );

      await openCatalogEntryModal(page);
      await navigateToSuggestedTagsTab(page);

      // Verify initial counts
      await expect(page.getByText(/3 pending/)).toBeVisible();
      await expect(page.getByText(/0 approved/)).toBeVisible();

      // Approve a segment
      const categoriesRow = page.locator('div', { has: page.locator('text="categories"') }).first();
      const approveButton = categoriesRow.locator('button[aria-label="Approve segment"]');
      await approveButton.click();

      // Wait for status update
      await expect(categoriesRow.locator('text=Approved')).toBeVisible({ timeout: 5000 });

      // Verify counts updated
      await expect(page.getByText(/2 pending/)).toBeVisible();
      await expect(page.getByText(/1 approved/)).toBeVisible();
    });
  });

  test.describe('Rejecting Segments', () => {
    test('user can reject a pending segment', async ({ page }) => {
      let patchCalled = false;
      let patchRequestBody: any = null;

      await page.route(
        `**/api/v1/marketplace/sources/${mockSource.id}/catalog/${mockCatalogEntry.id}/path-segments`,
        async (route) => {
          if (route.request().method() === 'PATCH') {
            patchCalled = true;
            patchRequestBody = await route.request().postDataJSON();

            await route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify({
                segment: patchRequestBody.segment,
                status: patchRequestBody.status,
                updated_at: new Date().toISOString(),
              }),
            });
          } else {
            await route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify(mockPathSegments),
            });
          }
        }
      );

      await openCatalogEntryModal(page);
      await navigateToSuggestedTagsTab(page);

      // Find the reject button for "05-data-ai" segment
      const dataAiRow = page.locator('div', { has: page.locator('text="05-data-ai"') }).first();
      const rejectButton = dataAiRow.locator('button[aria-label="Reject segment"]');

      await rejectButton.click();

      // Verify PATCH was called
      await expect.poll(() => patchCalled).toBe(true);
      expect(patchRequestBody).toEqual({
        segment: '05-data-ai',
        status: 'rejected',
      });

      // Verify status badge changes
      await expect(dataAiRow.locator('text=Rejected')).toBeVisible({ timeout: 5000 });
      await expect(dataAiRow.locator('text=Pending')).not.toBeVisible();
    });

    test('summary counts update after rejecting segment', async ({ page }) => {
      await page.route(
        `**/api/v1/marketplace/sources/${mockSource.id}/catalog/${mockCatalogEntry.id}/path-segments`,
        async (route) => {
          if (route.request().method() === 'PATCH') {
            await route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify({
                segment: '05-data-ai',
                status: 'rejected',
                updated_at: new Date().toISOString(),
              }),
            });
          } else {
            await route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify(mockPathSegments),
            });
          }
        }
      );

      await openCatalogEntryModal(page);
      await navigateToSuggestedTagsTab(page);

      // Verify initial counts
      await expect(page.getByText(/3 pending/)).toBeVisible();
      await expect(page.getByText(/0 rejected/)).toBeVisible();

      // Reject a segment
      const dataAiRow = page.locator('div', { has: page.locator('text="05-data-ai"') }).first();
      const rejectButton = dataAiRow.locator('button[aria-label="Reject segment"]');
      await rejectButton.click();

      // Wait for status update
      await expect(dataAiRow.locator('text=Rejected')).toBeVisible({ timeout: 5000 });

      // Verify counts updated
      await expect(page.getByText(/2 pending/)).toBeVisible();
      await expect(page.getByText(/1 rejected/)).toBeVisible();
    });
  });

  test.describe('Excluded Segments', () => {
    test('excluded segments display with badge and no action buttons', async ({ page }) => {
      // Override mock to use segments with excluded items
      await page.route(
        `**/api/v1/marketplace/sources/${mockSource.id}/catalog/${mockCatalogEntry.id}/path-segments`,
        async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockPathSegmentsWithExcluded),
          });
        }
      );

      await openCatalogEntryModal(page);
      await navigateToSuggestedTagsTab(page);

      // Verify excluded segments are displayed
      const srcRow = page.locator('div', { has: page.locator('text="src"') }).first();
      await expect(srcRow.locator('text=Excluded')).toBeVisible();

      // Verify exclusion reason is shown
      await expect(srcRow.getByText('Common build directory')).toBeVisible();

      // Verify no approve/reject buttons on excluded segments
      await expect(srcRow.locator('button[aria-label="Approve segment"]')).not.toBeVisible();
      await expect(srcRow.locator('button[aria-label="Reject segment"]')).not.toBeVisible();

      // Verify pending segments still have action buttons
      const utilsRow = page.locator('div', { has: page.locator('text="utils"') }).first();
      await expect(utilsRow.locator('button[aria-label="Approve segment"]')).toBeVisible();
      await expect(utilsRow.locator('button[aria-label="Reject segment"]')).toBeVisible();
    });

    test('excluded segments are included in summary counts', async ({ page }) => {
      await page.route(
        `**/api/v1/marketplace/sources/${mockSource.id}/catalog/${mockCatalogEntry.id}/path-segments`,
        async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockPathSegmentsWithExcluded),
          });
        }
      );

      await openCatalogEntryModal(page);
      await navigateToSuggestedTagsTab(page);

      // Verify summary counts
      await expect(page.getByText(/1 pending/)).toBeVisible();
      await expect(page.getByText(/2 excluded/)).toBeVisible();
    });
  });

  test.describe('Persistence', () => {
    test('changes persist after closing and reopening modal', async ({ page }) => {
      let approvedSegment: string | null = null;

      await page.route(
        `**/api/v1/marketplace/sources/${mockSource.id}/catalog/${mockCatalogEntry.id}/path-segments`,
        async (route) => {
          if (route.request().method() === 'PATCH') {
            const body = await route.request().postDataJSON();
            approvedSegment = body.segment;

            await route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify({
                segment: body.segment,
                status: body.status,
                updated_at: new Date().toISOString(),
              }),
            });
          } else {
            // Return segments with approved status if it was approved
            const segments = {
              ...mockPathSegments,
              extracted: mockPathSegments.extracted.map((seg) =>
                seg.segment === approvedSegment ? { ...seg, status: 'approved' } : seg
              ),
            };

            await route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify(segments),
            });
          }
        }
      );

      // Open modal and approve a segment
      await openCatalogEntryModal(page);
      await navigateToSuggestedTagsTab(page);

      const categoriesRow = page.locator('div', { has: page.locator('text="categories"') }).first();
      const approveButton = categoriesRow.locator('button[aria-label="Approve segment"]');
      await approveButton.click();

      // Wait for approval to complete
      await expect(categoriesRow.locator('text=Approved')).toBeVisible({ timeout: 5000 });

      // Close modal
      const modal = page.locator('[role="dialog"]');
      const closeButton = modal.locator('button[aria-label*="Close"]').first();
      await closeButton.click();
      await expect(modal).not.toBeVisible();

      // Reopen modal
      await openCatalogEntryModal(page);
      await navigateToSuggestedTagsTab(page);

      // Verify approved status persists
      const categoriesRowAfterReopen = page
        .locator('div', { has: page.locator('text="categories"') })
        .first();
      await expect(categoriesRowAfterReopen.locator('text=Approved')).toBeVisible();
      await expect(categoriesRowAfterReopen.locator('text=Pending')).not.toBeVisible();

      // Verify no action buttons on approved segment
      await expect(
        categoriesRowAfterReopen.locator('button[aria-label="Approve segment"]')
      ).not.toBeVisible();
      await expect(
        categoriesRowAfterReopen.locator('button[aria-label="Reject segment"]')
      ).not.toBeVisible();
    });
  });

  test.describe('Error Handling', () => {
    test('displays error state when path segments fail to load', async ({ page }) => {
      // Mock path segments endpoint to return error
      await page.route(
        `**/api/v1/marketplace/sources/${mockSource.id}/catalog/${mockCatalogEntry.id}/path-segments`,
        async (route) => {
          await route.fulfill({
            status: 500,
            contentType: 'application/json',
            body: JSON.stringify({
              detail: 'Failed to load path segments',
            }),
          });
        }
      );

      await openCatalogEntryModal(page);
      await navigateToSuggestedTagsTab(page);

      // Verify error message is displayed
      await expect(page.getByText(/Failed to load/)).toBeVisible();
      await expect(page.locator('button:has-text("Try again")')).toBeVisible();
    });

    test('displays error when status update fails', async ({ page }) => {
      await page.route(
        `**/api/v1/marketplace/sources/${mockSource.id}/catalog/${mockCatalogEntry.id}/path-segments`,
        async (route) => {
          if (route.request().method() === 'PATCH') {
            await route.fulfill({
              status: 500,
              contentType: 'application/json',
              body: JSON.stringify({
                detail: 'Failed to update segment status',
              }),
            });
          } else {
            await route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify(mockPathSegments),
            });
          }
        }
      );

      await openCatalogEntryModal(page);
      await navigateToSuggestedTagsTab(page);

      // Try to approve a segment
      const categoriesRow = page.locator('div', { has: page.locator('text="categories"') }).first();
      const approveButton = categoriesRow.locator('button[aria-label="Approve segment"]');
      await approveButton.click();

      // Verify error message appears (implementation-specific)
      // This depends on how the component handles mutation errors
      // For now, we just verify the status didn't change
      await page.waitForTimeout(1000);
      await expect(categoriesRow.locator('text=Pending')).toBeVisible();
      await expect(categoriesRow.locator('text=Approved')).not.toBeVisible();
    });
  });

  test.describe('Loading States', () => {
    test('displays loading skeleton while path segments are loading', async ({ page }) => {
      // Mock slow path segments endpoint
      await page.route(
        `**/api/v1/marketplace/sources/${mockSource.id}/catalog/${mockCatalogEntry.id}/path-segments`,
        async (route) => {
          await page.waitForTimeout(2000);
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockPathSegments),
          });
        }
      );

      await openCatalogEntryModal(page);
      await navigateToSuggestedTagsTab(page);

      // Verify loading state is displayed
      // Check for skeleton or loading indicator
      const loadingIndicator = page
        .locator('[class*="animate-pulse"], [aria-label*="Loading"]')
        .first();
      await expect(loadingIndicator).toBeVisible();

      // Wait for content to load
      await expect(page.getByText('categories')).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('Accessibility', () => {
    test('approve and reject buttons have proper ARIA labels', async ({ page }) => {
      await openCatalogEntryModal(page);
      await navigateToSuggestedTagsTab(page);

      // Verify ARIA labels
      const approveButton = page.locator('button[aria-label="Approve segment"]').first();
      const rejectButton = page.locator('button[aria-label="Reject segment"]').first();

      await expect(approveButton).toBeVisible();
      await expect(rejectButton).toBeVisible();
    });

    test('tab navigation works correctly', async ({ page }) => {
      await openCatalogEntryModal(page);

      // Navigate to Suggested Tags tab using keyboard
      await page.keyboard.press('Tab'); // Focus first focusable element
      await page.keyboard.press('ArrowRight'); // Move to Contents tab
      await page.keyboard.press('ArrowRight'); // Move to Suggested Tags tab

      // Verify Suggested Tags tab is now active
      const tagsTab = page.locator('[role="tab"]').filter({ hasText: 'Suggested Tags' });
      await expect(tagsTab).toHaveAttribute('data-state', 'active');
    });
  });
});
