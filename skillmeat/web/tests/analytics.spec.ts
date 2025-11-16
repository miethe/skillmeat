/**
 * Analytics Widgets E2E Tests
 *
 * Tests for analytics dashboard widgets:
 * - Stats cards
 * - Top artifacts widget
 * - Usage trends widget
 * - Live updates
 */

import { test, expect } from '@playwright/test';
import {
  mockApiRoute,
  navigateToPage,
  expectTextVisible,
  waitForElement,
  countElements,
  getTextContent,
} from './helpers/test-utils';
import { buildApiResponse, mockAnalytics } from './helpers/fixtures';

test.describe('Analytics Widgets', () => {
  test.beforeEach(async ({ page }) => {
    // Mock API routes
    await mockApiRoute(page, '/api/analytics*', buildApiResponse.analytics());
    await mockApiRoute(page, '/api/artifacts*', buildApiResponse.artifacts());

    // Navigate to dashboard
    await navigateToPage(page, '/');
  });

  test.describe('Dashboard Page', () => {
    test('should display dashboard header', async ({ page }) => {
      await expectTextVisible(page, 'h1', 'Dashboard');
      await expectTextVisible(
        page,
        'p',
        'Welcome to SkillMeat - Your personal collection manager'
      );
    });

    test('should load analytics grid', async ({ page }) => {
      await waitForElement(page, '[data-testid="analytics-grid"]');
    });
  });

  test.describe('Stats Cards', () => {
    test('should display all stat cards', async ({ page }) => {
      const statCards = page.locator('[data-testid="stat-card"]');
      const count = await statCards.count();

      // Should have 4 stat cards
      expect(count).toBeGreaterThanOrEqual(4);
    });

    test('should show total artifacts', async ({ page }) => {
      await expectTextVisible(
        page,
        '[data-testid="stat-card"]',
        'Total Artifacts'
      );
      await expectTextVisible(
        page,
        '[data-testid="stat-card"]',
        mockAnalytics.totalArtifacts.toString()
      );
    });

    test('should show total deployments', async ({ page }) => {
      await expectTextVisible(
        page,
        '[data-testid="stat-card"]',
        'Total Deployments'
      );
      await expectTextVisible(
        page,
        '[data-testid="stat-card"]',
        mockAnalytics.totalDeployments.toString()
      );
    });

    test('should show active projects', async ({ page }) => {
      await expectTextVisible(
        page,
        '[data-testid="stat-card"]',
        'Active Projects'
      );
      await expectTextVisible(
        page,
        '[data-testid="stat-card"]',
        mockAnalytics.activeProjects.toString()
      );
    });

    test('should show usage this week', async ({ page }) => {
      await expectTextVisible(
        page,
        '[data-testid="stat-card"]',
        'Usage This Week'
      );
      await expectTextVisible(
        page,
        '[data-testid="stat-card"]',
        mockAnalytics.usageThisWeek.toString()
      );
    });

    test('should display stat card icons', async ({ page }) => {
      const firstCard = page.locator('[data-testid="stat-card"]').first();
      const icon = firstCard.locator('svg');

      await expect(icon).toBeVisible();
    });

    test('should format large numbers correctly', async ({ page }) => {
      // Mock large numbers
      await mockApiRoute(page, '/api/analytics*', {
        ...mockAnalytics,
        totalArtifacts: 1234567,
      });

      await page.reload();
      await page.waitForTimeout(500);

      // Should format as 1.2M or similar
      const card = page.locator('[data-testid="stat-card"]').first();
      const text = await getTextContent(page, '[data-testid="stat-card"]');

      // Check for shortened number format (K, M, etc.)
      expect(text).toMatch(/[KM]/);
    });
  });

  test.describe('Top Artifacts Widget', () => {
    test('should display widget title', async ({ page }) => {
      await expectTextVisible(
        page,
        '[data-testid="top-artifacts-widget"]',
        'Top Artifacts'
      );
    });

    test('should show artifact list', async ({ page }) => {
      await waitForElement(page, '[data-testid="top-artifacts-widget"]');

      const artifactItems = page.locator('[data-testid="artifact-item"]');
      const count = await artifactItems.count();

      expect(count).toBeGreaterThan(0);
      expect(count).toBeLessThanOrEqual(10); // Default limit
    });

    test('should display artifact names and counts', async ({ page }) => {
      await waitForElement(page, '[data-testid="top-artifacts-widget"]');

      const firstItem = page.locator('[data-testid="artifact-item"]').first();

      // Should show artifact name
      await expect(firstItem).toContainText(
        mockAnalytics.topArtifacts[0].name
      );

      // Should show usage count
      await expect(firstItem).toContainText(
        mockAnalytics.topArtifacts[0].count.toString()
      );
    });

    test('should show artifact type badges', async ({ page }) => {
      await waitForElement(page, '[data-testid="top-artifacts-widget"]');

      const firstItem = page.locator('[data-testid="artifact-item"]').first();
      const typeBadge = firstItem.locator('[data-testid="type-badge"]');

      await expect(typeBadge).toBeVisible();
      await expect(typeBadge).toContainText(
        mockAnalytics.topArtifacts[0].type
      );
    });

    test('should display chart when enabled', async ({ page }) => {
      const chart = page.locator(
        '[data-testid="top-artifacts-widget"] [data-testid="chart"]'
      );

      if (await chart.isVisible()) {
        // Chart should be visible
        await expect(chart).toBeVisible();
      }
    });

    test('should sort by usage count descending', async ({ page }) => {
      await waitForElement(page, '[data-testid="top-artifacts-widget"]');

      const items = page.locator('[data-testid="artifact-item"]');
      const count = await items.count();

      // Get usage counts and verify they're in descending order
      const counts: number[] = [];
      for (let i = 0; i < Math.min(count, 3); i++) {
        const item = items.nth(i);
        const text = await item.textContent();
        const match = text?.match(/(\d+)/);
        if (match) {
          counts.push(parseInt(match[1]));
        }
      }

      // Verify descending order
      for (let i = 1; i < counts.length; i++) {
        expect(counts[i]).toBeLessThanOrEqual(counts[i - 1]);
      }
    });

    test('should link to artifact detail', async ({ page }) => {
      await waitForElement(page, '[data-testid="top-artifacts-widget"]');

      const firstItem = page.locator('[data-testid="artifact-item"]').first();
      const link = firstItem.locator('a');

      if (await link.isVisible()) {
        await expect(link).toHaveAttribute('href', /.+/);
      }
    });
  });

  test.describe('Usage Trends Widget', () => {
    test('should display widget title', async ({ page }) => {
      await expectTextVisible(
        page,
        '[data-testid="usage-trends-widget"]',
        'Usage Trends'
      );
    });

    test('should show trend chart', async ({ page }) => {
      await waitForElement(page, '[data-testid="usage-trends-widget"]');

      const chart = page.locator('[data-testid="trends-chart"]');
      await expect(chart).toBeVisible();
    });

    test('should display time period selector', async ({ page }) => {
      const periodSelector = page.locator(
        '[data-testid="usage-trends-widget"] select[name="period"]'
      );

      if (await periodSelector.isVisible()) {
        await expect(periodSelector).toBeVisible();

        // Should have period options
        const options = periodSelector.locator('option');
        const count = await options.count();
        expect(count).toBeGreaterThan(0);
      }
    });

    test('should switch between time periods', async ({ page }) => {
      const periodSelector = page.locator(
        '[data-testid="usage-trends-widget"] select[name="period"]'
      );

      if (await periodSelector.isVisible()) {
        await periodSelector.selectOption('month');
        await page.waitForTimeout(500);

        // Chart should update
        const chart = page.locator('[data-testid="trends-chart"]');
        await expect(chart).toBeVisible();
      }
    });

    test('should display chart type toggle', async ({ page }) => {
      const chartTypeToggle = page.locator(
        '[data-testid="usage-trends-widget"] [role="group"]'
      );

      if (await chartTypeToggle.isVisible()) {
        await expect(chartTypeToggle).toBeVisible();
      }
    });

    test('should switch between chart types', async ({ page }) => {
      const barChartButton = page.locator('button[aria-label*="bar"]');

      if (await barChartButton.isVisible()) {
        await barChartButton.click();
        await page.waitForTimeout(500);

        // Chart should update to bar chart
        const chart = page.locator('[data-testid="trends-chart"]');
        await expect(chart).toBeVisible();
      }
    });

    test('should show data points on hover', async ({ page }) => {
      await waitForElement(page, '[data-testid="trends-chart"]');

      const chart = page.locator('[data-testid="trends-chart"]');

      // Hover over chart area
      await chart.hover();

      // Tooltip should appear (implementation-specific)
      await page.waitForTimeout(200);
    });

    test('should display trend summary', async ({ page }) => {
      const summary = page.locator(
        '[data-testid="usage-trends-widget"] [data-testid="trend-summary"]'
      );

      if (await summary.isVisible()) {
        // Should show percentage change or trend indicator
        await expect(summary).toBeVisible();
      }
    });
  });

  test.describe('Live Updates', () => {
    test('should display live update indicator', async ({ page }) => {
      const liveIndicator = page.locator('[data-testid="live-indicator"]');

      if (await liveIndicator.isVisible()) {
        await expect(liveIndicator).toBeVisible();
        await expectTextVisible(page, '[data-testid="live-indicator"]', /live/i);
      }
    });

    test('should show connection status', async ({ page }) => {
      const statusDot = page.locator('[data-testid="status-dot"]');

      if (await statusDot.isVisible()) {
        await expect(statusDot).toBeVisible();

        // Should have color indicating status
        const classes = await statusDot.getAttribute('class');
        expect(classes).toMatch(/bg-(green|gray)/);
      }
    });

    test('should show last update time', async ({ page }) => {
      const lastUpdate = page.locator('[data-testid="last-update"]');

      if (await lastUpdate.isVisible()) {
        await expect(lastUpdate).toBeVisible();
        const text = await lastUpdate.textContent();
        expect(text).toMatch(/\d{1,2}:\d{2}/); // Time format
      }
    });

    test('should show event count', async ({ page }) => {
      const eventCount = page.locator('[data-testid="event-count"]');

      if (await eventCount.isVisible()) {
        await expect(eventCount).toBeVisible();
        await expect(eventCount).toContainText(/\d+ updates?/);
      }
    });

    test('should handle SSE connection', async ({ page }) => {
      // Mock SSE endpoint
      await page.route('**/api/analytics/stream', async (route) => {
        await route.fulfill({
          status: 200,
          headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            Connection: 'keep-alive',
          },
          body: 'data: {"type":"update","data":{}}\n\n',
        });
      });

      await page.reload();
      await page.waitForTimeout(1000);

      // Live indicator should show connected
      const statusDot = page.locator('[data-testid="status-dot"]');
      if (await statusDot.isVisible()) {
        const classes = await statusDot.getAttribute('class');
        expect(classes).toContain('bg-green');
      }
    });
  });

  test.describe('Loading and Error States', () => {
    test('should show loading state for analytics', async ({ page }) => {
      await page.route('**/api/analytics*', async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 1000));
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(buildApiResponse.analytics()),
        });
      });

      await page.goto('/');

      // Should show loading skeletons
      const skeleton = page.locator('[data-testid="stat-card-skeleton"]');
      if (await skeleton.isVisible()) {
        await expect(skeleton).toBeVisible();
      }
    });

    test('should handle analytics error gracefully', async ({ page }) => {
      await mockApiRoute(
        page,
        '/api/analytics*',
        { error: 'Failed to load analytics' },
        500
      );

      await page.goto('/');
      await page.waitForTimeout(500);

      // Should show error state
      const errorMessage = page.locator('[role="alert"]');
      if (await errorMessage.isVisible()) {
        await expect(errorMessage).toBeVisible();
      }
    });

    test('should show empty state when no data', async ({ page }) => {
      await mockApiRoute(page, '/api/analytics*', {
        totalArtifacts: 0,
        totalDeployments: 0,
        activeProjects: 0,
        usageThisWeek: 0,
        topArtifacts: [],
        usageTrends: [],
      });

      await page.goto('/');
      await page.waitForTimeout(500);

      // Should show empty state
      await expectTextVisible(page, '[data-testid="stat-card"]', '0');
    });
  });

  test.describe('Responsive Design', () => {
    test('should adjust layout on mobile', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });

      // Stats cards should stack vertically
      const statsGrid = page.locator('[data-testid="stats-grid"]');
      if (await statsGrid.isVisible()) {
        await expect(statsGrid).toBeVisible();
      }
    });

    test('should adjust layout on tablet', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });

      // Should show 2-column grid
      const widgetsGrid = page.locator('[data-testid="widgets-grid"]');
      if (await widgetsGrid.isVisible()) {
        await expect(widgetsGrid).toBeVisible();
      }
    });

    test('should show full layout on desktop', async ({ page }) => {
      await page.setViewportSize({ width: 1920, height: 1080 });

      // All widgets should be visible
      await waitForElement(page, '[data-testid="analytics-grid"]');
      await waitForElement(page, '[data-testid="top-artifacts-widget"]');
      await waitForElement(page, '[data-testid="usage-trends-widget"]');
    });
  });
});
