/**
 * Sync Workflow E2E Tests — SyncConfirmationDialog
 *
 * Tests the unified SyncConfirmationDialog across all 3 sync directions:
 * - SYNC-P02: Deploy (Collection -> Project)
 * - SYNC-P03: Push (Project -> Collection)
 * - SYNC-P04: Pull (Source -> Collection)
 *
 * Each direction verifies:
 * - Dialog opens with correct title and labels
 * - DiffViewer shows file changes
 * - Overwrite action executes and succeeds
 * - Merge button enable/disable gating
 * - Cancel closes the dialog
 */

import { test, expect } from '@playwright/test';
import {
  mockApiRoute,
  navigateToPage,
  waitForElement,
  pressKey,
} from './helpers/test-utils';
import {
  buildApiResponse,
  mockArtifacts,
} from './helpers/fixtures';

// ---------------------------------------------------------------------------
// Shared mock data
// ---------------------------------------------------------------------------

/** Mock diff response with changes (both sides modified) */
const mockDiffWithConflicts = {
  has_changes: true,
  artifact_id: mockArtifacts[0].id,
  project_path: '/home/user/projects/skillmeat-web',
  files: [
    {
      file_path: 'SKILL.md',
      status: 'modified',
      change_origin: 'both',
      left_content: '# Old skill content',
      right_content: '# New skill content',
      unified_diff: '@@ -1,3 +1,3 @@\n-# Old skill content\n+# New skill content',
    },
    {
      file_path: 'config.json',
      status: 'added',
      change_origin: 'upstream',
      left_content: null,
      right_content: '{ "version": "2.0" }',
      unified_diff: '@@ -0,0 +1 @@\n+{ "version": "2.0" }',
    },
  ],
  summary: {
    added: 1,
    modified: 1,
    deleted: 0,
    unchanged: 0,
    conflicts: 1,
  },
};

/** Mock diff response with changes (only source-side changes, no target) */
const mockDiffSourceOnly = {
  has_changes: true,
  artifact_id: mockArtifacts[0].id,
  project_path: '/home/user/projects/skillmeat-web',
  files: [
    {
      file_path: 'SKILL.md',
      status: 'modified',
      change_origin: 'upstream',
      left_content: '# Collection version',
      right_content: '# Project version',
      unified_diff: '@@ -1,3 +1,3 @@\n-# Collection version\n+# Project version',
    },
  ],
  summary: {
    added: 0,
    modified: 1,
    deleted: 0,
    unchanged: 0,
  },
};

/** Mock upstream diff response (source vs collection) with changes */
const mockUpstreamDiffWithChanges = {
  has_changes: true,
  artifact_id: mockArtifacts[0].id,
  upstream_source: 'anthropics/skills/canvas-design',
  upstream_version: '1.3.0',
  files: [
    {
      file_path: 'SKILL.md',
      status: 'modified',
      change_origin: 'both',
      left_content: '# Source version 1.3.0',
      right_content: '# Collection version 1.2.0',
      unified_diff: '@@ -1,3 +1,3 @@\n-# Source version 1.3.0\n+# Collection version 1.2.0',
    },
  ],
  summary: {
    added: 0,
    modified: 1,
    deleted: 0,
    unchanged: 0,
    conflicts: 1,
  },
};

/** Mock upstream diff response with source-only changes (no local mods) */
const mockUpstreamDiffSourceOnly = {
  has_changes: true,
  artifact_id: mockArtifacts[0].id,
  upstream_source: 'anthropics/skills/canvas-design',
  upstream_version: '1.3.0',
  files: [
    {
      file_path: 'SKILL.md',
      status: 'modified',
      change_origin: 'upstream',
      left_content: '# Source version 1.3.0',
      right_content: '# Collection version 1.2.0',
      unified_diff: '@@ -1,3 +1,3 @@\n-# Source version 1.3.0\n+# Collection version 1.2.0',
    },
  ],
  summary: {
    added: 0,
    modified: 1,
    deleted: 0,
    unchanged: 0,
  },
};

/** Mock successful deploy response */
const mockDeploySuccess = {
  success: true,
  message: 'Artifact deployed successfully',
};

/** Mock successful sync (pull/push) response */
const mockSyncSuccess = {
  success: true,
  message: 'Sync completed successfully',
  synced_files: 2,
  conflicts: [],
};

// ---------------------------------------------------------------------------
// Common setup helpers
// ---------------------------------------------------------------------------

/**
 * Set up API mocks and navigate to artifact detail sync tab.
 *
 * This navigates to /collection, clicks the first artifact card to open the
 * detail drawer, then activates the Sync tab inside the drawer.
 */
async function navigateToSyncTab(
  page: import('@playwright/test').Page,
  options?: {
    /** Mock for GET /artifacts/{id}/diff (project diff) */
    projectDiff?: object;
    /** Mock for GET /artifacts/{id}/upstream-diff */
    upstreamDiff?: object;
  }
) {
  const artifactId = mockArtifacts[0].id;

  // Mock common API routes
  await mockApiRoute(page, '/api/artifacts*', buildApiResponse.artifacts());
  await mockApiRoute(page, '/api/projects*', buildApiResponse.projects());
  await mockApiRoute(page, '/api/analytics*', buildApiResponse.analytics());
  await mockApiRoute(
    page,
    `/api/artifacts/${artifactId}`,
    buildApiResponse.artifactDetail(artifactId)
  );

  // Mock diff endpoints based on options
  if (options?.projectDiff) {
    await page.route(`**/api/artifacts/${artifactId}/diff*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(options.projectDiff),
      });
    });
  }

  if (options?.upstreamDiff) {
    await page.route(`**/api/artifacts/${artifactId}/upstream-diff*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(options.upstreamDiff),
      });
    });
  }

  // Navigate to collection page
  await navigateToPage(page, '/collection');

  // Click first artifact card to open detail drawer
  const firstCard = page.locator('[data-testid="artifact-card"]').first();
  await firstCard.click();
  await waitForElement(page, '[role="dialog"]');

  // Click Sync tab
  const syncTab = page.getByRole('tab', { name: /sync/i });
  await syncTab.click();
}

// ===========================================================================
// SYNC-P02: Deploy with Conflicts (Collection -> Project)
// ===========================================================================

test.describe('SYNC-P02: Deploy to Project', () => {
  test('should open SyncConfirmationDialog with deploy direction', async ({ page }) => {
    await navigateToSyncTab(page, {
      projectDiff: mockDiffWithConflicts,
      upstreamDiff: mockUpstreamDiffWithChanges,
    });

    // Mock the conflict-check diff API for the dialog (deploy uses /diff endpoint)
    const artifactId = mockArtifacts[0].id;
    await page.route(`**/api/artifacts/${artifactId}/diff*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockDiffWithConflicts),
      });
    });

    // Click "Deploy to Project" button in the flow banner
    const deployButton = page.getByRole('button', { name: /deploy to project/i });
    await deployButton.click();

    // SyncConfirmationDialog should open with deploy-specific title
    const dialog = page.locator('[role="dialog"]').last();
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText('Deploy to Project');
  });

  test('should show direction-specific labels in deploy dialog', async ({ page }) => {
    await navigateToSyncTab(page, {
      projectDiff: mockDiffWithConflicts,
      upstreamDiff: mockUpstreamDiffWithChanges,
    });

    const artifactId = mockArtifacts[0].id;
    await page.route(`**/api/artifacts/${artifactId}/diff*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockDiffWithConflicts),
      });
    });

    const deployButton = page.getByRole('button', { name: /deploy to project/i });
    await deployButton.click();

    const dialog = page.locator('[role="dialog"]').last();
    await expect(dialog).toBeVisible();

    // Verify deploy-specific warning text
    await expect(dialog).toContainText('overwrite project files with collection versions');

    // Verify file change summary is displayed
    await expect(dialog).toContainText(/\d+ files? changed/);
  });

  test('should show DiffViewer with file diffs in deploy dialog', async ({ page }) => {
    await navigateToSyncTab(page, {
      projectDiff: mockDiffWithConflicts,
      upstreamDiff: mockUpstreamDiffWithChanges,
    });

    const artifactId = mockArtifacts[0].id;
    await page.route(`**/api/artifacts/${artifactId}/diff*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockDiffWithConflicts),
      });
    });

    const deployButton = page.getByRole('button', { name: /deploy to project/i });
    await deployButton.click();

    const dialog = page.locator('[role="dialog"]').last();
    await expect(dialog).toBeVisible();

    // Verify DiffViewer is rendered with changed files
    // Check that file paths from the diff appear
    await expect(dialog).toContainText('SKILL.md');
  });

  test('should execute deploy on Overwrite click', async ({ page }) => {
    await navigateToSyncTab(page, {
      projectDiff: mockDiffWithConflicts,
      upstreamDiff: mockUpstreamDiffWithChanges,
    });

    const artifactId = mockArtifacts[0].id;

    // Mock deploy endpoint
    let deployCalled = false;
    await page.route(`**/api/artifacts/${artifactId}/deploy*`, async (route) => {
      deployCalled = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockDeploySuccess),
      });
    });

    // Mock diff for the dialog
    await page.route(`**/api/artifacts/${artifactId}/diff*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockDiffWithConflicts),
      });
    });

    const deployButton = page.getByRole('button', { name: /deploy to project/i });
    await deployButton.click();

    const dialog = page.locator('[role="dialog"]').last();
    await expect(dialog).toBeVisible();

    // Wait for diff data to load then click the Deploy (overwrite) button
    const overwriteButton = dialog.getByRole('button', { name: /deploy/i }).last();
    await expect(overwriteButton).toBeVisible();
    await overwriteButton.click();

    // Verify deploy API was called
    await page.waitForTimeout(500);
    expect(deployCalled).toBe(true);
  });

  test('should enable Merge button when target (project) has changes', async ({ page }) => {
    await navigateToSyncTab(page, {
      projectDiff: mockDiffWithConflicts,
      upstreamDiff: mockUpstreamDiffWithChanges,
    });

    const artifactId = mockArtifacts[0].id;
    // Diff with change_origin='both' means target has changes
    await page.route(`**/api/artifacts/${artifactId}/diff*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockDiffWithConflicts),
      });
    });

    const deployButton = page.getByRole('button', { name: /deploy to project/i });
    await deployButton.click();

    const dialog = page.locator('[role="dialog"]').last();
    await expect(dialog).toBeVisible();

    // Merge button should be visible and enabled (target has changes via change_origin='both')
    const mergeButton = dialog.getByRole('button', { name: /merge/i });
    await expect(mergeButton).toBeVisible();
    await expect(mergeButton).toBeEnabled();
  });

  test('should disable Merge button when target has no changes', async ({ page }) => {
    await navigateToSyncTab(page, {
      projectDiff: mockDiffSourceOnly,
      upstreamDiff: mockUpstreamDiffSourceOnly,
    });

    const artifactId = mockArtifacts[0].id;
    // Diff with only upstream changes (no local/both) means target has no changes
    await page.route(`**/api/artifacts/${artifactId}/diff*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockDiffSourceOnly),
      });
    });

    const deployButton = page.getByRole('button', { name: /deploy to project/i });
    await deployButton.click();

    const dialog = page.locator('[role="dialog"]').last();
    await expect(dialog).toBeVisible();

    // Merge button should be visible but disabled
    const mergeButton = dialog.getByRole('button', { name: /merge/i });
    await expect(mergeButton).toBeVisible();
    await expect(mergeButton).toBeDisabled();
  });

  test('should close deploy dialog on Cancel', async ({ page }) => {
    await navigateToSyncTab(page, {
      projectDiff: mockDiffWithConflicts,
      upstreamDiff: mockUpstreamDiffWithChanges,
    });

    const artifactId = mockArtifacts[0].id;
    await page.route(`**/api/artifacts/${artifactId}/diff*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockDiffWithConflicts),
      });
    });

    const deployButton = page.getByRole('button', { name: /deploy to project/i });
    await deployButton.click();

    const dialog = page.locator('[role="dialog"]').last();
    await expect(dialog).toBeVisible();

    // Click Cancel
    const cancelButton = dialog.getByRole('button', { name: /cancel/i });
    await cancelButton.click();

    // Dialog title should no longer be visible (dialog closed)
    await expect(page.getByText('Deploy to Project')).toBeHidden();
  });
});

// ===========================================================================
// SYNC-P03: Push with Conflicts (Project -> Collection)
// ===========================================================================

test.describe('SYNC-P03: Push to Collection', () => {
  test('should open SyncConfirmationDialog with push direction', async ({ page }) => {
    await navigateToSyncTab(page, {
      projectDiff: mockDiffWithConflicts,
      upstreamDiff: mockUpstreamDiffWithChanges,
    });

    const artifactId = mockArtifacts[0].id;
    await page.route(`**/api/artifacts/${artifactId}/diff*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockDiffWithConflicts),
      });
    });

    // Click "Push to Collection" button in the flow banner
    const pushButton = page.getByRole('button', { name: /push to collection/i });
    await pushButton.click();

    // SyncConfirmationDialog should open with push-specific title
    const dialog = page.locator('[role="dialog"]').last();
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText('Push to Collection');
  });

  test('should show push-specific labels and warning', async ({ page }) => {
    await navigateToSyncTab(page, {
      projectDiff: mockDiffWithConflicts,
      upstreamDiff: mockUpstreamDiffWithChanges,
    });

    const artifactId = mockArtifacts[0].id;
    await page.route(`**/api/artifacts/${artifactId}/diff*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockDiffWithConflicts),
      });
    });

    const pushButton = page.getByRole('button', { name: /push to collection/i });
    await pushButton.click();

    const dialog = page.locator('[role="dialog"]').last();
    await expect(dialog).toBeVisible();

    // Verify push-specific warning text
    await expect(dialog).toContainText('overwrite collection files with project versions');

    // Verify file change summary
    await expect(dialog).toContainText(/\d+ files? changed/);
  });

  test('should execute push on Overwrite click', async ({ page }) => {
    await navigateToSyncTab(page, {
      projectDiff: mockDiffWithConflicts,
      upstreamDiff: mockUpstreamDiffWithChanges,
    });

    const artifactId = mockArtifacts[0].id;

    // Mock push (sync) endpoint
    let pushCalled = false;
    await page.route(`**/api/artifacts/${artifactId}/sync`, async (route) => {
      pushCalled = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockSyncSuccess),
      });
    });

    await page.route(`**/api/artifacts/${artifactId}/diff*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockDiffWithConflicts),
      });
    });

    const pushButton = page.getByRole('button', { name: /push to collection/i });
    await pushButton.click();

    const dialog = page.locator('[role="dialog"]').last();
    await expect(dialog).toBeVisible();

    // Click "Push Changes" (overwrite) button
    const overwriteButton = dialog.getByRole('button', { name: /push changes/i });
    await expect(overwriteButton).toBeVisible();
    await overwriteButton.click();

    // Verify sync API was called
    await page.waitForTimeout(500);
    expect(pushCalled).toBe(true);
  });

  test('should show conflict warning when both sides changed', async ({ page }) => {
    await navigateToSyncTab(page, {
      projectDiff: mockDiffWithConflicts,
      upstreamDiff: mockUpstreamDiffWithChanges,
    });

    const artifactId = mockArtifacts[0].id;
    await page.route(`**/api/artifacts/${artifactId}/diff*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockDiffWithConflicts),
      });
    });

    const pushButton = page.getByRole('button', { name: /push to collection/i });
    await pushButton.click();

    const dialog = page.locator('[role="dialog"]').last();
    await expect(dialog).toBeVisible();

    // Should show conflict-specific warning about divergence
    await expect(dialog).toContainText(/diverged|merging/i);
  });

  test('should close push dialog on Cancel', async ({ page }) => {
    await navigateToSyncTab(page, {
      projectDiff: mockDiffWithConflicts,
      upstreamDiff: mockUpstreamDiffWithChanges,
    });

    const artifactId = mockArtifacts[0].id;
    await page.route(`**/api/artifacts/${artifactId}/diff*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockDiffWithConflicts),
      });
    });

    const pushButton = page.getByRole('button', { name: /push to collection/i });
    await pushButton.click();

    const dialog = page.locator('[role="dialog"]').last();
    await expect(dialog).toBeVisible();

    const cancelButton = dialog.getByRole('button', { name: /cancel/i });
    await cancelButton.click();

    await expect(page.getByText('Push to Collection')).toBeHidden();
  });

  test('should close push dialog on Escape key', async ({ page }) => {
    await navigateToSyncTab(page, {
      projectDiff: mockDiffWithConflicts,
      upstreamDiff: mockUpstreamDiffWithChanges,
    });

    const artifactId = mockArtifacts[0].id;
    await page.route(`**/api/artifacts/${artifactId}/diff*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockDiffWithConflicts),
      });
    });

    const pushButton = page.getByRole('button', { name: /push to collection/i });
    await pushButton.click();

    const dialog = page.locator('[role="dialog"]').last();
    await expect(dialog).toBeVisible();

    await pressKey(page, 'Escape');

    await expect(page.getByText('Push to Collection')).toBeHidden();
  });
});

// ===========================================================================
// SYNC-P04: Pull with Conflicts (Source -> Collection)
// ===========================================================================

test.describe('SYNC-P04: Pull from Source', () => {
  test('should open SyncConfirmationDialog with pull direction', async ({ page }) => {
    await navigateToSyncTab(page, {
      projectDiff: mockDiffWithConflicts,
      upstreamDiff: mockUpstreamDiffWithChanges,
    });

    const artifactId = mockArtifacts[0].id;
    await page.route(`**/api/artifacts/${artifactId}/upstream-diff*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockUpstreamDiffWithChanges),
      });
    });

    // Click "Pull from Source" button in the flow banner
    const pullButton = page.getByRole('button', { name: /pull from source/i });
    await pullButton.click();

    // SyncConfirmationDialog should open with pull-specific title
    const dialog = page.locator('[role="dialog"]').last();
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText('Pull from Source');
  });

  test('should show pull-specific labels and warning', async ({ page }) => {
    await navigateToSyncTab(page, {
      projectDiff: mockDiffWithConflicts,
      upstreamDiff: mockUpstreamDiffWithChanges,
    });

    const artifactId = mockArtifacts[0].id;
    await page.route(`**/api/artifacts/${artifactId}/upstream-diff*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockUpstreamDiffWithChanges),
      });
    });

    const pullButton = page.getByRole('button', { name: /pull from source/i });
    await pullButton.click();

    const dialog = page.locator('[role="dialog"]').last();
    await expect(dialog).toBeVisible();

    // Verify pull-specific warning text
    await expect(dialog).toContainText('overwrite collection files with upstream source');

    // Verify file change summary
    await expect(dialog).toContainText(/\d+ files? changed/);
  });

  test('should show DiffViewer with upstream changes in pull dialog', async ({ page }) => {
    await navigateToSyncTab(page, {
      projectDiff: mockDiffWithConflicts,
      upstreamDiff: mockUpstreamDiffWithChanges,
    });

    const artifactId = mockArtifacts[0].id;
    await page.route(`**/api/artifacts/${artifactId}/upstream-diff*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockUpstreamDiffWithChanges),
      });
    });

    const pullButton = page.getByRole('button', { name: /pull from source/i });
    await pullButton.click();

    const dialog = page.locator('[role="dialog"]').last();
    await expect(dialog).toBeVisible();

    // Verify file names from the diff appear
    await expect(dialog).toContainText('SKILL.md');
  });

  test('should execute pull on Overwrite click', async ({ page }) => {
    await navigateToSyncTab(page, {
      projectDiff: mockDiffWithConflicts,
      upstreamDiff: mockUpstreamDiffWithChanges,
    });

    const artifactId = mockArtifacts[0].id;

    // Mock sync (pull) endpoint
    let pullCalled = false;
    await page.route(`**/api/artifacts/${artifactId}/sync`, async (route) => {
      pullCalled = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockSyncSuccess),
      });
    });

    await page.route(`**/api/artifacts/${artifactId}/upstream-diff*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockUpstreamDiffWithChanges),
      });
    });

    const pullButton = page.getByRole('button', { name: /pull from source/i });
    await pullButton.click();

    const dialog = page.locator('[role="dialog"]').last();
    await expect(dialog).toBeVisible();

    // Click "Pull Changes" (overwrite) button
    const overwriteButton = dialog.getByRole('button', { name: /pull changes/i });
    await expect(overwriteButton).toBeVisible();
    await overwriteButton.click();

    // Verify sync API was called
    await page.waitForTimeout(500);
    expect(pullCalled).toBe(true);
  });

  test('should enable Merge button when collection has local changes', async ({ page }) => {
    await navigateToSyncTab(page, {
      projectDiff: mockDiffWithConflicts,
      upstreamDiff: mockUpstreamDiffWithChanges,
    });

    const artifactId = mockArtifacts[0].id;
    // change_origin='both' means both source and collection have changes
    await page.route(`**/api/artifacts/${artifactId}/upstream-diff*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockUpstreamDiffWithChanges),
      });
    });

    const pullButton = page.getByRole('button', { name: /pull from source/i });
    await pullButton.click();

    const dialog = page.locator('[role="dialog"]').last();
    await expect(dialog).toBeVisible();

    // Merge button should be enabled (collection has local changes)
    const mergeButton = dialog.getByRole('button', { name: /merge/i });
    await expect(mergeButton).toBeVisible();
    await expect(mergeButton).toBeEnabled();
  });

  test('should disable Merge button when collection has no local changes', async ({ page }) => {
    await navigateToSyncTab(page, {
      projectDiff: mockDiffSourceOnly,
      upstreamDiff: mockUpstreamDiffSourceOnly,
    });

    const artifactId = mockArtifacts[0].id;
    // Only upstream changes, no local modifications
    await page.route(`**/api/artifacts/${artifactId}/upstream-diff*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockUpstreamDiffSourceOnly),
      });
    });

    const pullButton = page.getByRole('button', { name: /pull from source/i });
    await pullButton.click();

    const dialog = page.locator('[role="dialog"]').last();
    await expect(dialog).toBeVisible();

    // Merge button should be disabled (no local changes to merge)
    const mergeButton = dialog.getByRole('button', { name: /merge/i });
    await expect(mergeButton).toBeVisible();
    await expect(mergeButton).toBeDisabled();
  });

  test('should close pull dialog on Cancel', async ({ page }) => {
    await navigateToSyncTab(page, {
      projectDiff: mockDiffWithConflicts,
      upstreamDiff: mockUpstreamDiffWithChanges,
    });

    const artifactId = mockArtifacts[0].id;
    await page.route(`**/api/artifacts/${artifactId}/upstream-diff*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockUpstreamDiffWithChanges),
      });
    });

    const pullButton = page.getByRole('button', { name: /pull from source/i });
    await pullButton.click();

    const dialog = page.locator('[role="dialog"]').last();
    await expect(dialog).toBeVisible();

    const cancelButton = dialog.getByRole('button', { name: /cancel/i });
    await cancelButton.click();

    await expect(page.getByText('Pull from Source')).toBeHidden();
  });

  test('should show conflict warning for pull when both sides changed', async ({ page }) => {
    await navigateToSyncTab(page, {
      projectDiff: mockDiffWithConflicts,
      upstreamDiff: mockUpstreamDiffWithChanges,
    });

    const artifactId = mockArtifacts[0].id;
    await page.route(`**/api/artifacts/${artifactId}/upstream-diff*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockUpstreamDiffWithChanges),
      });
    });

    const pullButton = page.getByRole('button', { name: /pull from source/i });
    await pullButton.click();

    const dialog = page.locator('[role="dialog"]').last();
    await expect(dialog).toBeVisible();

    // Should show conflict-specific warning about merging
    await expect(dialog).toContainText(/source and collection have changes|merging/i);
  });
});
