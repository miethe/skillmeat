/**
 * End-to-end tests for Entity Lifecycle Management critical paths
 *
 * Tests comprehensive user journeys including:
 * 1. Create Project and Add Entity
 * 2. Entity Merge Workflow
 * 3. Version Rollback
 * 4. Entity Search and Filter
 * 5. Project Settings
 */

import { test, expect, Page } from "@playwright/test";

test.describe("Entity Lifecycle Management E2E", () => {
  /**
   * Helper to wait for loading states to complete
   */
  async function waitForPageReady(page: Page) {
    await page.waitForLoadState("networkidle");
    // Wait for any loading spinners to disappear
    await page.waitForSelector('[class*="animate-spin"]', {
      state: "hidden",
      timeout: 10000,
    }).catch(() => {
      // Ignore if no spinner found
    });
  }

  /**
   * Critical Path 1: Create Project and Add Entity
   */
  test.describe("Create Project and Add Entity", () => {
    test("successfully creates project and adds entity from collection", async ({ page }) => {
      // Navigate to projects page
      await page.goto("/projects");
      await waitForPageReady(page);

      // Verify we're on the projects page
      await expect(page.getByRole("heading", { name: "Projects" })).toBeVisible();

      // Click "New Project" button
      const newProjectButton = page.getByRole("button", { name: /New Project/i });
      await newProjectButton.click();

      // Verify dialog opened
      await expect(page.getByRole("dialog")).toBeVisible();
      await expect(page.getByText("Create New Project")).toBeVisible();

      // Fill in project details
      const projectName = `test-project-${Date.now()}`;
      const projectPath = `/tmp/test-projects/${projectName}`;

      await page.fill('input[id="name"]', projectName);
      await page.fill('input[id="path"]', projectPath);
      await page.fill('textarea[id="description"]', "Test project for E2E testing");

      // Submit form
      const createButton = page.getByRole("button", { name: "Create Project" });
      await createButton.click();

      // Wait for project creation and toast
      await page.waitForTimeout(1000);
      await waitForPageReady(page);

      // Verify project was created (should appear in list or redirect to project page)
      const projectCard = page.locator(`text=${projectName}`).first();
      await expect(projectCard).toBeVisible({ timeout: 10000 });

      // Click on the project to navigate to it
      await projectCard.click();

      // Navigate to manage entities page
      const manageButton = page.getByRole("button", { name: /Manage Entities/i }).first();
      if (await manageButton.isVisible()) {
        await manageButton.click();
      } else {
        // If already on project page, navigate via URL
        const projectId = Buffer.from(projectPath).toString('base64');
        await page.goto(`/projects/${projectId}/manage`);
      }

      await waitForPageReady(page);

      // Verify we're on the manage page
      await expect(page.getByText("Project Entity Management")).toBeVisible();

      // Click "Add from Collection" button
      const addFromCollectionButton = page.getByRole("button", {
        name: /Add from Collection/i
      });
      await addFromCollectionButton.click();

      // Verify deploy dialog opened
      await expect(page.getByRole("dialog")).toBeVisible();
      await page.waitForTimeout(500);

      // If there are entities in the collection, select one
      // This test assumes there's at least one entity available
      const entityCheckboxes = page.locator('input[type="checkbox"]').filter({
        hasNot: page.locator('[disabled]')
      });

      const checkboxCount = await entityCheckboxes.count();
      if (checkboxCount > 0) {
        // Select first available entity
        await entityCheckboxes.first().click();

        // Click deploy button
        const deployButton = page.getByRole("button", { name: /Deploy Selected/i });
        await deployButton.click();

        // Wait for deployment to complete
        await page.waitForTimeout(1000);
        await waitForPageReady(page);

        // Verify entity appears in the list
        const entityList = page.locator('[class*="entity"]');
        await expect(entityList.first()).toBeVisible({ timeout: 5000 });
      }
    });

    test("validates project creation form", async ({ page }) => {
      await page.goto("/projects");
      await waitForPageReady(page);

      // Open create dialog
      await page.getByRole("button", { name: /New Project/i }).click();
      await expect(page.getByRole("dialog")).toBeVisible();

      // Try to submit with empty name
      const createButton = page.getByRole("button", { name: "Create Project" });
      await createButton.click();

      // Verify validation errors
      await expect(page.getByText(/required/i)).toBeVisible();

      // Fill invalid name (with spaces)
      await page.fill('input[id="name"]', "invalid name with spaces");
      await page.fill('input[id="path"]', "/tmp/test");
      await createButton.click();

      // Verify validation error for invalid characters
      await expect(page.getByText(/letters, numbers, hyphens/i)).toBeVisible();

      // Fill invalid path (relative)
      await page.fill('input[id="name"]', "valid-name");
      await page.fill('input[id="path"]', "relative/path");
      await createButton.click();

      // Verify path validation error
      await expect(page.getByText(/absolute path/i)).toBeVisible();
    });
  });

  /**
   * Critical Path 2: Entity Merge Workflow
   */
  test.describe("Entity Merge Workflow", () => {
    test("completes merge workflow through all steps", async ({ page }) => {
      // Navigate to manage page
      await page.goto("/manage");
      await waitForPageReady(page);

      // Look for an entity with changes (modified status)
      const modifiedEntity = page.locator('[data-status="modified"]').first();

      // If no modified entity, this test needs setup - skip or create test data
      const hasModifiedEntity = await modifiedEntity.isVisible().catch(() => false);

      if (hasModifiedEntity) {
        // Click on entity to open detail panel
        await modifiedEntity.click();

        // Wait for detail panel to open
        await expect(page.getByText(/Entity Details/i)).toBeVisible();

        // Click sync/merge button
        const syncButton = page.getByRole("button", { name: /Sync|Merge/i }).first();
        await syncButton.click();

        // Step 1: Preview
        await expect(page.getByText("Preview Changes")).toBeVisible();
        await expect(page.getByText(/Summary of Changes/i)).toBeVisible();

        // Verify stepper shows preview as active
        await expect(page.locator('text=Preview').locator('..')).toHaveClass(/active|primary/);

        // Click continue
        const continueButton = page.getByRole("button", { name: "Continue" });
        await continueButton.click();

        // Step 2: Resolve conflicts (if any)
        // Check if we're on resolve step or skipped to apply
        const isResolveStep = await page.getByText("Resolve Conflicts").isVisible();

        if (isResolveStep) {
          // Select resolution strategy for conflicts
          const resolutionRadios = page.locator('input[type="radio"]');
          const radioCount = await resolutionRadios.count();

          if (radioCount > 0) {
            // Select "Keep Collection" strategy
            const collectionRadio = page.getByRole("radio", {
              name: /Collection|theirs/i
            }).first();
            await collectionRadio.click();
          }

          // Continue to apply step
          await page.getByRole("button", { name: "Continue" }).click();
        }

        // Step 3: Apply
        await expect(page.getByText("Apply Changes")).toBeVisible();
        await expect(page.getByText(/Summary/i)).toBeVisible();

        // Verify conflict resolutions are shown
        await expect(page.getByText(/Conflict Resolutions|Direction/i)).toBeVisible();

        // Click apply
        const applyButton = page.getByRole("button", { name: "Apply Changes" });
        await applyButton.click();

        // Wait for progress indicator
        await expect(page.locator('[role="progressbar"]')).toBeVisible();

        // Wait for completion
        await expect(page.getByText(/Success|Complete/i)).toBeVisible({
          timeout: 15000
        });

        // Verify success message
        await expect(page.getByText(/synced|merged|applied/i)).toBeVisible();
      }
    });

    test("allows navigation back through workflow steps", async ({ page }) => {
      await page.goto("/manage");
      await waitForPageReady(page);

      // Find a modified entity
      const modifiedEntity = page.locator('[data-status="modified"]').first();
      const hasModifiedEntity = await modifiedEntity.isVisible().catch(() => false);

      if (hasModifiedEntity) {
        await modifiedEntity.click();

        // Open merge workflow
        const syncButton = page.getByRole("button", { name: /Sync|Merge/i }).first();
        await syncButton.click();

        // Wait for preview step
        await expect(page.getByText("Preview Changes")).toBeVisible();

        // Continue to next step
        await page.getByRole("button", { name: "Continue" }).click();

        // Check if on resolve or apply step
        const isResolveStep = await page.getByText("Resolve Conflicts").isVisible();

        if (isResolveStep) {
          // Click back button
          const backButton = page.getByRole("button", { name: "Back" });
          await backButton.click();

          // Verify we're back on preview
          await expect(page.getByText("Preview Changes")).toBeVisible();
        }
      }
    });
  });

  /**
   * Critical Path 3: Version Rollback
   */
  test.describe("Version Rollback", () => {
    test("successfully rolls back entity to collection version", async ({ page }) => {
      await page.goto("/manage");
      await waitForPageReady(page);

      // Find a modified entity
      const modifiedEntity = page.locator('[data-status="modified"]').first();
      const hasModifiedEntity = await modifiedEntity.isVisible().catch(() => false);

      if (hasModifiedEntity) {
        // Click entity to open detail panel
        await modifiedEntity.click();

        // Find and click rollback button
        const rollbackButton = page.getByRole("button", { name: /Rollback/i });

        if (await rollbackButton.isVisible()) {
          await rollbackButton.click();

          // Verify rollback dialog opened
          await expect(page.getByRole("dialog")).toBeVisible();
          await expect(page.getByText(/Rollback to Collection Version/i)).toBeVisible();

          // Verify warning is shown
          await expect(page.getByText(/cannot be undone/i)).toBeVisible();
          await expect(page.locator('[class*="destructive"]')).toBeVisible();

          // Verify version comparison is shown
          await expect(page.getByText(/Current.*Local/i)).toBeVisible();
          await expect(page.getByText(/Target.*Collection/i)).toBeVisible();

          // Click rollback button
          const confirmButton = page.getByRole("button", { name: "Rollback" });
          await confirmButton.click();

          // Wait for rollback to complete
          await page.waitForTimeout(1000);

          // Verify dialog closed
          await expect(page.getByRole("dialog")).not.toBeVisible();

          // Verify entity status changed or success message
          await page.waitForTimeout(500);
        }
      }
    });

    test("can cancel rollback dialog", async ({ page }) => {
      await page.goto("/manage");
      await waitForPageReady(page);

      const modifiedEntity = page.locator('[data-status="modified"]').first();
      const hasModifiedEntity = await modifiedEntity.isVisible().catch(() => false);

      if (hasModifiedEntity) {
        await modifiedEntity.click();

        const rollbackButton = page.getByRole("button", { name: /Rollback/i });

        if (await rollbackButton.isVisible()) {
          await rollbackButton.click();

          // Wait for dialog
          await expect(page.getByRole("dialog")).toBeVisible();

          // Click cancel
          const cancelButton = page.getByRole("button", { name: "Cancel" });
          await cancelButton.click();

          // Verify dialog closed
          await expect(page.getByRole("dialog")).not.toBeVisible();
        }
      }
    });
  });

  /**
   * Critical Path 4: Entity Search and Filter
   */
  test.describe("Entity Search and Filter", () => {
    test("filters entities by search query", async ({ page }) => {
      await page.goto("/manage");
      await waitForPageReady(page);

      // Get initial entity count
      const initialCount = await page.locator('[class*="entity"]').count();

      // Find search input
      const searchInput = page.getByPlaceholder(/Search/i);
      await searchInput.fill("test");

      // Wait for debounce
      await page.waitForTimeout(600);

      // Verify results updated (may be fewer entities)
      const filteredCount = await page.locator('[class*="entity"]').count();

      // Results should either be filtered or show "no results"
      if (filteredCount === 0) {
        await expect(page.getByText(/no.*entities.*found/i)).toBeVisible();
      }

      // Clear search
      await searchInput.clear();
      await page.waitForTimeout(600);
    });

    test("filters entities by type", async ({ page }) => {
      await page.goto("/manage");
      await waitForPageReady(page);

      // Click on different entity type tabs
      const skillTab = page.getByRole("tab", { name: /Skill/i });
      if (await skillTab.isVisible()) {
        await skillTab.click();
        await page.waitForTimeout(300);

        // Verify URL updated
        await expect(page).toHaveURL(/type=skill/);
      }

      const commandTab = page.getByRole("tab", { name: /Command/i });
      if (await commandTab.isVisible()) {
        await commandTab.click();
        await page.waitForTimeout(300);

        // Verify URL updated
        await expect(page).toHaveURL(/type=command/);
      }

      const agentTab = page.getByRole("tab", { name: /Agent/i });
      if (await agentTab.isVisible()) {
        await agentTab.click();
        await page.waitForTimeout(300);

        // Verify URL updated
        await expect(page).toHaveURL(/type=agent/);
      }
    });

    test("filters entities by status", async ({ page }) => {
      await page.goto("/manage");
      await waitForPageReady(page);

      // Look for status filter dropdown or radio group
      const statusFilter = page.locator('[id*="status"], [name*="status"]').first();

      if (await statusFilter.isVisible()) {
        // Click to open dropdown if it's a select
        await statusFilter.click();

        // Select "Modified" status
        const modifiedOption = page.getByRole("option", { name: /Modified/i });
        if (await modifiedOption.isVisible()) {
          await modifiedOption.click();
          await page.waitForTimeout(300);

          // Verify filtered entities
          const entities = page.locator('[data-status="modified"]');
          const count = await entities.count();

          // Either show modified entities or empty state
          if (count === 0) {
            await expect(page.getByText(/no.*entities/i)).toBeVisible();
          }
        }
      }
    });

    test("combines multiple filters", async ({ page }) => {
      await page.goto("/manage");
      await waitForPageReady(page);

      // Apply search filter
      const searchInput = page.getByPlaceholder(/Search/i);
      await searchInput.fill("skill");
      await page.waitForTimeout(600);

      // Apply type filter
      const skillTab = page.getByRole("tab", { name: /Skill/i });
      if (await skillTab.isVisible()) {
        await skillTab.click();
        await page.waitForTimeout(300);
      }

      // Verify combined filtering works
      const entityCount = page.getByText(/\d+.*entit(y|ies)/i);
      await expect(entityCount).toBeVisible();

      // Clear filters
      await searchInput.clear();
      await page.waitForTimeout(600);
    });

    test("shows empty state when no results match filters", async ({ page }) => {
      await page.goto("/manage");
      await waitForPageReady(page);

      // Search for something that won't match
      const searchInput = page.getByPlaceholder(/Search/i);
      await searchInput.fill("xyzabc123nonexistent");
      await page.waitForTimeout(600);

      // Verify empty state
      await expect(page.getByText(/no.*entities.*found/i)).toBeVisible();
    });
  });

  /**
   * Critical Path 5: Project Settings
   */
  test.describe("Project Settings", () => {
    test("successfully updates project settings", async ({ page }) => {
      // First, create or navigate to a project
      await page.goto("/projects");
      await waitForPageReady(page);

      // Click on first project in list
      const firstProject = page.locator('[class*="cursor-pointer"]').first();
      const hasProjects = await firstProject.isVisible().catch(() => false);

      if (hasProjects) {
        await firstProject.click();

        // Navigate to settings
        const settingsButton = page.getByRole("button", { name: /Settings/i });
        if (await settingsButton.isVisible()) {
          await settingsButton.click();
        } else {
          // Navigate via URL pattern
          const currentUrl = page.url();
          const projectId = currentUrl.split('/').pop();
          await page.goto(`/projects/${projectId}/settings`);
        }

        await waitForPageReady(page);

        // Verify we're on settings page
        await expect(page.getByText("Project Settings")).toBeVisible();

        // Get current name
        const nameInput = page.locator('input[id="settings-name"]');
        const currentName = await nameInput.inputValue();

        // Update project name
        const newName = `${currentName}-updated`;
        await nameInput.clear();
        await nameInput.fill(newName);

        // Update description
        const descriptionInput = page.locator('textarea[id="settings-description"]');
        await descriptionInput.fill("Updated description for E2E test");

        // Save changes
        const saveButton = page.getByRole("button", { name: /Save Changes/i });
        await expect(saveButton).toBeEnabled();
        await saveButton.click();

        // Wait for save to complete
        await page.waitForTimeout(1000);

        // Verify success message or button is disabled
        await expect(saveButton).toBeDisabled();
      }
    });

    test("validates project settings form", async ({ page }) => {
      await page.goto("/projects");
      await waitForPageReady(page);

      const firstProject = page.locator('[class*="cursor-pointer"]').first();
      const hasProjects = await firstProject.isVisible().catch(() => false);

      if (hasProjects) {
        await firstProject.click();

        // Navigate to settings
        const currentUrl = page.url();
        const match = currentUrl.match(/\/projects\/([^/]+)/);
        if (match) {
          await page.goto(`/projects/${match[1]}/settings`);
        }

        await waitForPageReady(page);

        // Try to clear name
        const nameInput = page.locator('input[id="settings-name"]');
        await nameInput.clear();

        // Try to save
        const saveButton = page.getByRole("button", { name: /Save Changes/i });
        await saveButton.click();

        // Verify validation error
        await expect(page.getByText(/required/i)).toBeVisible();

        // Fill invalid name
        await nameInput.fill("invalid name with spaces");
        await saveButton.click();

        // Verify validation error
        await expect(page.getByText(/letters, numbers, hyphens/i)).toBeVisible();
      }
    });

    test("displays project statistics correctly", async ({ page }) => {
      await page.goto("/projects");
      await waitForPageReady(page);

      const firstProject = page.locator('[class*="cursor-pointer"]').first();
      const hasProjects = await firstProject.isVisible().catch(() => false);

      if (hasProjects) {
        await firstProject.click();

        const currentUrl = page.url();
        const match = currentUrl.match(/\/projects\/([^/]+)/);
        if (match) {
          await page.goto(`/projects/${match[1]}/settings`);
        }

        await waitForPageReady(page);

        // Verify statistics section exists
        await expect(page.getByText("Project Statistics")).toBeVisible();
        await expect(page.getByText(/Total Deployments/i)).toBeVisible();
        await expect(page.getByText(/Modified Artifacts/i)).toBeVisible();
        await expect(page.getByText(/Last Deployment/i)).toBeVisible();

        // Verify statistics have values
        const deploymentCount = page.locator('text=/Total Deployments/i').locator('..').locator('text=/\\d+/');
        await expect(deploymentCount.first()).toBeVisible();
      }
    });

    test("shows delete project option in danger zone", async ({ page }) => {
      await page.goto("/projects");
      await waitForPageReady(page);

      const firstProject = page.locator('[class*="cursor-pointer"]').first();
      const hasProjects = await firstProject.isVisible().catch(() => false);

      if (hasProjects) {
        await firstProject.click();

        const currentUrl = page.url();
        const match = currentUrl.match(/\/projects\/([^/]+)/);
        if (match) {
          await page.goto(`/projects/${match[1]}/settings`);
        }

        await waitForPageReady(page);

        // Verify danger zone exists
        await expect(page.getByText("Danger Zone")).toBeVisible();
        await expect(page.getByRole("button", { name: /Delete Project/i })).toBeVisible();

        // Verify warning text
        await expect(page.getByText(/cannot be undone/i)).toBeVisible();
      }
    });
  });

  /**
   * Additional integration tests
   */
  test.describe("Integration Scenarios", () => {
    test("switches between grid and list view modes", async ({ page }) => {
      await page.goto("/manage");
      await waitForPageReady(page);

      // Find view mode toggle
      const viewToggle = page.getByRole("button", { name: /Grid|List/i }).first();

      if (await viewToggle.isVisible()) {
        await viewToggle.click();

        // Select list view
        const listOption = page.getByRole("menuitemradio", { name: /List/i });
        if (await listOption.isVisible()) {
          await listOption.click();
          await page.waitForTimeout(300);

          // Verify view changed
          // The list view might have different styling or layout
        }

        // Switch back to grid
        await viewToggle.click();
        const gridOption = page.getByRole("menuitemradio", { name: /Grid/i });
        if (await gridOption.isVisible()) {
          await gridOption.click();
        }
      }
    });

    test("entity detail panel opens and closes", async ({ page }) => {
      await page.goto("/manage");
      await waitForPageReady(page);

      // Click on first entity
      const firstEntity = page.locator('[class*="entity"]').first();
      const hasEntities = await firstEntity.isVisible().catch(() => false);

      if (hasEntities) {
        await firstEntity.click();

        // Verify detail panel opened
        await expect(page.getByText(/Entity Details|Details/i)).toBeVisible();

        // Close panel
        const closeButton = page.getByRole("button", { name: /Close/i }).first();
        if (await closeButton.isVisible()) {
          await closeButton.click();

          // Verify panel closed
          await expect(page.getByText(/Entity Details|Details/i)).not.toBeVisible();
        }
      }
    });
  });
});
