/**
 * End-to-end tests for Marketplace functionality
 *
 * Tests the complete user flow for browsing, filtering, viewing, and installing listings
 */
import { test, expect } from "@playwright/test";

test.describe("Marketplace", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to marketplace page
    await page.goto("/marketplace");
  });

  test("displays marketplace page with listings", async ({ page }) => {
    // Check page title
    await expect(page.getByRole("heading", { name: "Marketplace" })).toBeVisible();

    // Check stats are displayed
    await expect(page.getByText("Total Listings")).toBeVisible();
    await expect(page.getByText("Total Artifacts")).toBeVisible();

    // Wait for listings to load
    await expect(page.getByRole("button", { name: /View Details/i }).first()).toBeVisible({
      timeout: 10000,
    });
  });

  test("filters listings by search query", async ({ page }) => {
    // Wait for page to load
    await page.waitForLoadState("networkidle");

    // Enter search query
    const searchInput = page.getByPlaceholder("Search marketplace listings...");
    await searchInput.fill("testing");

    // Wait for filtered results
    await page.waitForTimeout(500); // Debounce delay

    // Verify results contain search term (case-insensitive check)
    const listingCards = page.locator('[role="button"]').filter({ hasText: /testing/i });
    await expect(listingCards.first()).toBeVisible({ timeout: 5000 });
  });

  test("filters listings by tags", async ({ page }) => {
    // Wait for page to load
    await page.waitForLoadState("networkidle");

    // Find and click a suggested tag
    const pythonTag = page.locator('[role="button"]', { hasText: "python" }).first();
    await pythonTag.click();

    // Wait for filtered results
    await page.waitForTimeout(500);

    // Verify filter is active
    await expect(page.getByText("1 filter active")).toBeVisible();
  });

  test("clears all filters", async ({ page }) => {
    // Wait for page to load
    await page.waitForLoadState("networkidle");

    // Add some filters
    const searchInput = page.getByPlaceholder("Search marketplace listings...");
    await searchInput.fill("test");

    const pythonTag = page.locator('[role="button"]', { hasText: "python" }).first();
    await pythonTag.click();

    // Wait for filters to apply
    await page.waitForTimeout(500);

    // Click clear all button
    const clearButton = page.getByRole("button", { name: "Clear all" });
    await clearButton.click();

    // Verify filters are cleared
    await expect(page.getByText(/\d+ filter(s)? active/)).not.toBeVisible();
  });

  test("navigates to listing detail page", async ({ page }) => {
    // Wait for listings to load
    await expect(page.getByRole("button", { name: /View Details/i }).first()).toBeVisible({
      timeout: 10000,
    });

    // Click on first listing card
    const firstCard = page.locator('[role="button"][aria-label*="View listing"]').first();
    await firstCard.click();

    // Wait for navigation
    await page.waitForURL(/\/marketplace\/[^/]+$/);

    // Verify we're on detail page
    await expect(page.getByRole("button", { name: "Back to Marketplace" })).toBeVisible();
    await expect(page.getByText("Artifacts")).toBeVisible();
  });

  test("opens install dialog from listing card", async ({ page }) => {
    // Wait for listings to load
    await expect(page.getByRole("button", { name: /View Details/i }).first()).toBeVisible({
      timeout: 10000,
    });

    // Click on first listing
    const firstCard = page.locator('[role="button"][aria-label*="View listing"]').first();
    await firstCard.click();

    // Click install button on detail page
    const installButton = page.getByRole("button", { name: /Install Bundle/i });
    await installButton.click();

    // Verify install dialog opens
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByText("Install Bundle")).toBeVisible();
    await expect(page.getByText("Conflict Resolution Strategy")).toBeVisible();
  });

  test("selects conflict strategy in install dialog", async ({ page }) => {
    // Navigate to detail page and open install dialog
    await expect(page.getByRole("button", { name: /View Details/i }).first()).toBeVisible({
      timeout: 10000,
    });

    const firstCard = page.locator('[role="button"][aria-label*="View listing"]').first();
    await firstCard.click();

    const installButton = page.getByRole("button", { name: /Install Bundle/i });
    await installButton.click();

    // Select fork strategy
    const strategySelect = page.locator('select[id="strategy-select"]');
    await strategySelect.selectOption("fork");

    // Verify description updates
    await expect(
      page.getByText("Conflicts will be resolved by creating renamed copies.")
    ).toBeVisible();
  });

  test("cancels install dialog", async ({ page }) => {
    // Navigate to detail page and open install dialog
    await expect(page.getByRole("button", { name: /View Details/i }).first()).toBeVisible({
      timeout: 10000,
    });

    const firstCard = page.locator('[role="button"][aria-label*="View listing"]').first();
    await firstCard.click();

    const installButton = page.getByRole("button", { name: /Install Bundle/i });
    await installButton.click();

    // Click cancel button
    const cancelButton = page.getByRole("button", { name: "Cancel" });
    await cancelButton.click();

    // Verify dialog closes
    await expect(page.getByRole("dialog")).not.toBeVisible();
  });

  test("navigates to publish page", async ({ page }) => {
    // Click publish button
    const publishButton = page.getByRole("button", { name: "Publish Bundle" });
    await publishButton.click();

    // Wait for navigation
    await page.waitForURL("/marketplace/publish");

    // Verify we're on publish page
    await expect(page.getByRole("heading", { name: "Publish Bundle" })).toBeVisible();
    await expect(page.getByText("Select Bundle to Publish")).toBeVisible();
  });

  test("navigates through publish wizard steps", async ({ page }) => {
    // Navigate to publish page
    await page.goto("/marketplace/publish");

    // Step 1: Enter bundle path
    const bundlePathInput = page.locator('input[id="bundle-path"]');
    await bundlePathInput.fill("/path/to/test-bundle.tar.gz");

    const nextButton = page.getByRole("button", { name: /Next/i });
    await nextButton.click();

    // Step 2: Should show broker selection
    await expect(page.getByText("Choose Broker")).toBeVisible();

    // Go back
    const backButton = page.getByRole("button", { name: /Back/i });
    await backButton.click();

    // Verify we're back on step 1
    await expect(page.getByText("Select Bundle to Publish")).toBeVisible();
  });

  test("loads more listings when scrolling", async ({ page }) => {
    // Wait for initial listings
    await expect(page.getByRole("button", { name: /View Details/i }).first()).toBeVisible({
      timeout: 10000,
    });

    // Count initial listings
    const initialCount = await page.locator('[role="button"][aria-label*="View listing"]').count();

    // Click load more button if available
    const loadMoreButton = page.getByRole("button", { name: "Load More" });
    const isVisible = await loadMoreButton.isVisible();

    if (isVisible) {
      await loadMoreButton.click();
      await page.waitForTimeout(1000);

      // Count listings after loading more
      const newCount = await page.locator('[role="button"][aria-label*="View listing"]').count();

      // Verify more listings were loaded
      expect(newCount).toBeGreaterThan(initialCount);
    }
  });

  test("displays empty state when no results", async ({ page }) => {
    // Enter a search query that should return no results
    const searchInput = page.getByPlaceholder("Search marketplace listings...");
    await searchInput.fill("xyzabc123nonexistent");

    // Wait for results
    await page.waitForTimeout(1000);

    // Verify empty state is shown
    await expect(page.getByText("No listings found")).toBeVisible();
    await expect(
      page.getByText("Try adjusting your filters or search terms")
    ).toBeVisible();
  });
});
