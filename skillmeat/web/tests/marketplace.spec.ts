/**
 * Marketplace E2E Tests
 *
 * End-to-end tests for marketplace browsing, filtering, and installation flows
 */

import { test, expect } from '@playwright/test';
import {
  mockApiRoute,
  navigateToPage,
  waitForElement,
  pressKey,
} from './helpers/test-utils';

const mockListings = [
  {
    listing_id: 'skill-canvas',
    name: 'Canvas Design',
    description: 'Create and edit visual designs with an interactive canvas',
    category: 'skill',
    version: '2.1.0',
    publisher: {
      name: 'Anthropic',
      verified: true,
    },
    license: 'MIT',
    tags: ['design', 'visual', 'canvas'],
    artifact_count: 3,
    downloads: 5000,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-02-15T00:00:00Z',
  },
  {
    listing_id: 'command-git',
    name: 'Git Helper',
    description: 'Custom git workflow commands',
    category: 'command',
    version: '1.0.0',
    publisher: {
      name: 'Community',
      verified: false,
    },
    license: 'MIT',
    tags: ['git', 'vcs', 'workflow'],
    artifact_count: 2,
    downloads: 1200,
    created_at: '2024-01-15T00:00:00Z',
    updated_at: '2024-02-10T00:00:00Z',
  },
];

const mockListingDetail = {
  listing_id: 'skill-canvas',
  name: 'Canvas Design',
  description: 'Create and edit visual designs with an interactive canvas',
  category: 'skill',
  version: '2.1.0',
  publisher: {
    name: 'Anthropic',
    email: 'contact@anthropic.com',
    website: 'https://anthropic.com',
    verified: true,
  },
  license: 'MIT',
  tags: ['design', 'visual', 'canvas'],
  artifact_count: 3,
  downloads: 5000,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-02-15T00:00:00Z',
  homepage: 'https://github.com/anthropics/skills/canvas-design',
  repository: 'https://github.com/anthropics/skills/canvas-design',
  source_url: 'https://marketplace.skillmeat.com/listing/skill-canvas',
  bundle_url: 'https://marketplace.skillmeat.com/bundles/skill-canvas.tar.gz',
  price: 0,
  signature: 'test-signature',
};

test.describe('Marketplace', () => {
  test.beforeEach(async ({ page }) => {
    // Mock API responses
    await mockApiRoute(page, '/api/v1/marketplace/listings*', {
      items: mockListings,
      page_info: {
        has_next_page: false,
        has_previous_page: false,
        total_count: mockListings.length,
      },
    });
  });

  test('displays marketplace catalog', async ({ page }) => {
    await navigateToPage(page, '/marketplace');

    // Check page title
    await expect(page.locator('h1')).toContainText('Marketplace');

    // Check search bar is visible
    await expect(page.locator('input[placeholder*="Search"]')).toBeVisible();

    // Check listings are displayed
    await expect(page.locator('text=Canvas Design')).toBeVisible();
    await expect(page.locator('text=Git Helper')).toBeVisible();
  });

  test('filters listings by search query', async ({ page }) => {
    await navigateToPage(page, '/marketplace');

    // Type in search box
    const searchInput = page.locator('input[placeholder*="Search"]');
    await searchInput.fill('canvas');

    // Should show matching results
    await expect(page.locator('text=Canvas Design')).toBeVisible();

    // Can clear search
    const clearButton = page.locator('button[aria-label="Clear search"]');
    await clearButton.click();
    await expect(searchInput).toHaveValue('');
  });

  test('filters listings by artifact type', async ({ page }) => {
    await navigateToPage(page, '/marketplace');

    // Select artifact type filter
    const typeSelect = page.locator('select#artifact-type');
    await typeSelect.selectOption('skill');

    // Should update URL and filter results
    await expect(page).toHaveURL(/type=skill/);
  });

  test('sorts listings', async ({ page }) => {
    await navigateToPage(page, '/marketplace');

    // Change sort order
    const sortSelect = page.locator('select[aria-label="Sort listings"]');
    await sortSelect.selectOption('downloads');

    // Should update URL
    await expect(page).toHaveURL(/sort=downloads/);
  });

  test('navigates to listing detail page', async ({ page }) => {
    // Mock detail API
    await mockApiRoute(page, '/api/v1/marketplace/listings/skill-canvas', mockListingDetail);

    await navigateToPage(page, '/marketplace');

    // Click on listing card
    await page.locator('text=Canvas Design').first().click();

    // Should navigate to detail page
    await expect(page).toHaveURL(/\/marketplace\/skill-canvas/);
    await expect(page.locator('h1')).toContainText('Canvas Design');
  });

  test('displays listing detail information', async ({ page }) => {
    await mockApiRoute(page, '/api/v1/marketplace/listings/skill-canvas', mockListingDetail);

    await navigateToPage(page, '/marketplace/skill-canvas');

    // Check all key information is displayed
    await expect(page.locator('text=Canvas Design')).toBeVisible();
    await expect(page.locator('text=Anthropic')).toBeVisible();
    await expect(page.locator('text=Verified')).toBeVisible();
    await expect(page.locator('text=v2.1.0')).toBeVisible();
    await expect(page.locator('text=MIT')).toBeVisible();
    await expect(page.locator('text=5K')).toBeVisible(); // Downloads formatted
    await expect(page.locator('text=Free')).toBeVisible();

    // Check tags
    await expect(page.locator('text=design')).toBeVisible();
    await expect(page.locator('text=visual')).toBeVisible();
  });

  test('opens trust prompt when install button is clicked', async ({ page }) => {
    await mockApiRoute(page, '/api/v1/marketplace/listings/skill-canvas', mockListingDetail);

    await navigateToPage(page, '/marketplace/skill-canvas');

    // Click install button
    const installButton = page.locator('button:has-text("Install")').first();
    await installButton.click();

    // Trust prompt should open
    await expect(page.locator('text=Install from Marketplace')).toBeVisible();
    await expect(page.locator('text=High Trust Level')).toBeVisible();
  });

  test('requires acknowledgment before installing', async ({ page }) => {
    await mockApiRoute(page, '/api/v1/marketplace/listings/skill-canvas', mockListingDetail);

    await navigateToPage(page, '/marketplace/skill-canvas');

    // Open trust prompt
    const installButton = page.locator('button:has-text("Install")').first();
    await installButton.click();

    // Install button in dialog should be disabled
    const dialogInstallButton = page.locator('dialog button:has-text("Install")');
    await expect(dialogInstallButton).toBeDisabled();

    // Check acknowledgment checkbox
    const acknowledgmentCheckbox = page.locator('input#understood');
    await acknowledgmentCheckbox.check();

    // Install button should now be enabled
    await expect(dialogInstallButton).toBeEnabled();
  });

  test('displays trust levels correctly', async ({ page }) => {
    // Test high trust (verified + signature)
    await mockApiRoute(page, '/api/v1/marketplace/listings/high-trust', {
      ...mockListingDetail,
      listing_id: 'high-trust',
      publisher: { ...mockListingDetail.publisher, verified: true },
      signature: 'sig',
    });

    await navigateToPage(page, '/marketplace/high-trust');
    await page.locator('button:has-text("Install")').first().click();
    await expect(page.locator('text=High Trust Level')).toBeVisible();

    // Test medium trust (verified, no signature)
    await page.goto('/marketplace');
    await mockApiRoute(page, '/api/v1/marketplace/listings/medium-trust', {
      ...mockListingDetail,
      listing_id: 'medium-trust',
      publisher: { ...mockListingDetail.publisher, verified: true },
      signature: undefined,
    });

    await navigateToPage(page, '/marketplace/medium-trust');
    await page.locator('button:has-text("Install")').first().click();
    await expect(page.locator('text=Medium Trust Level')).toBeVisible();
  });

  test('keyboard navigation works', async ({ page }) => {
    await navigateToPage(page, '/marketplace');

    // Focus search input with keyboard
    await pressKey(page, 'Tab');
    const searchInput = page.locator('input[placeholder*="Search"]');
    await expect(searchInput).toBeFocused();

    // Can type in search
    await searchInput.fill('test');
    await expect(searchInput).toHaveValue('test');
  });

  test('mobile filters are accessible', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    await navigateToPage(page, '/marketplace');

    // Mobile filter button should be visible
    const filterButton = page.locator('button:has-text("Filters")');
    await expect(filterButton).toBeVisible();

    // Click to open filter sheet
    await filterButton.click();

    // Filter sheet should open
    await expect(page.locator('text=Popular Tags')).toBeVisible();
  });

  test('pagination works', async ({ page }) => {
    // Mock paginated response
    await mockApiRoute(page, '/api/v1/marketplace/listings*', {
      items: mockListings,
      page_info: {
        has_next_page: true,
        has_previous_page: false,
        total_count: 50,
      },
    });

    await navigateToPage(page, '/marketplace');

    // Next button should be enabled
    const nextButton = page.locator('button:has-text("Next")');
    await expect(nextButton).toBeEnabled();

    // Previous button should be disabled
    const prevButton = page.locator('button:has-text("Previous")');
    await expect(prevButton).toBeDisabled();
  });
});

test.describe('Marketplace Accessibility', () => {
  test('marketplace catalog is accessible', async ({ page }) => {
    await mockApiRoute(page, '/api/v1/marketplace/listings*', {
      items: mockListings,
      page_info: {
        has_next_page: false,
        has_previous_page: false,
        total_count: mockListings.length,
      },
    });

    await navigateToPage(page, '/marketplace');

    // Check ARIA labels
    await expect(page.locator('input[aria-label="Search marketplace listings"]')).toBeVisible();
    await expect(page.locator('select[aria-label="Sort listings"]')).toBeVisible();
  });

  test('trust prompt is keyboard accessible', async ({ page }) => {
    await mockApiRoute(page, '/api/v1/marketplace/listings/skill-canvas', mockListingDetail);

    await navigateToPage(page, '/marketplace/skill-canvas');

    // Open trust prompt with keyboard
    await pressKey(page, 'Tab');
    await pressKey(page, 'Enter');

    // Should be able to navigate with keyboard
    await pressKey(page, 'Tab');
    const acknowledgmentCheckbox = page.locator('input#understood');
    await pressKey(page, 'Space');

    await expect(acknowledgmentCheckbox).toBeChecked();
  });
});
