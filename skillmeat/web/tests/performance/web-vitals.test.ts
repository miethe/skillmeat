/**
 * Web Vitals performance tests for SkillMeat web interface.
 *
 * This test suite measures Core Web Vitals using Playwright:
 * - First Contentful Paint (FCP)
 * - Largest Contentful Paint (LCP)
 * - Cumulative Layout Shift (CLS)
 * - First Input Delay (FID)
 * - Time to First Byte (TTFB)
 *
 * Usage:
 *   npm run test:e2e -- tests/performance/web-vitals.test.ts
 */

import { test, expect, Page } from '@playwright/test';

// SLA targets (in milliseconds unless noted)
const SLA_TARGETS = {
  fcp: 1500, // First Contentful Paint <1.5s
  lcp: 2500, // Largest Contentful Paint <2.5s
  cls: 0.1, // Cumulative Layout Shift <0.1
  fid: 100, // First Input Delay <100ms
  ttfb: 600, // Time to First Byte <600ms
  search: 1000, // Search results <1s
  navigation: 500, // Page navigation <500ms
};

/**
 * Measure First Contentful Paint (FCP)
 */
async function measureFCP(page: Page): Promise<number> {
  const fcp = await page.evaluate(() => {
    return new Promise<number>((resolve) => {
      const observer = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        for (const entry of entries) {
          if (entry.name === 'first-contentful-paint') {
            observer.disconnect();
            resolve(entry.startTime);
          }
        }
      });
      observer.observe({ entryTypes: ['paint'] });

      // Timeout after 10 seconds
      setTimeout(() => {
        observer.disconnect();
        resolve(-1);
      }, 10000);
    });
  });

  return fcp;
}

/**
 * Measure Largest Contentful Paint (LCP)
 */
async function measureLCP(page: Page): Promise<number> {
  const lcp = await page.evaluate(() => {
    return new Promise<number>((resolve) => {
      let lastEntry: PerformanceEntry | null = null;

      const observer = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        lastEntry = entries[entries.length - 1];
      });

      observer.observe({ entryTypes: ['largest-contentful-paint'] });

      // Wait for page load to complete
      setTimeout(() => {
        observer.disconnect();
        resolve(lastEntry ? lastEntry.startTime : -1);
      }, 3000);
    });
  });

  return lcp;
}

/**
 * Measure Cumulative Layout Shift (CLS)
 */
async function measureCLS(page: Page): Promise<number> {
  const cls = await page.evaluate(() => {
    return new Promise<number>((resolve) => {
      let clsValue = 0;

      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          // @ts-ignore - LayoutShift is not in standard types
          if (!entry.hadRecentInput) {
            // @ts-ignore
            clsValue += entry.value;
          }
        }
      });

      observer.observe({ entryTypes: ['layout-shift'] });

      // Measure for 3 seconds
      setTimeout(() => {
        observer.disconnect();
        resolve(clsValue);
      }, 3000);
    });
  });

  return cls;
}

/**
 * Measure Time to First Byte (TTFB)
 */
async function measureTTFB(page: Page): Promise<number> {
  const ttfb = await page.evaluate(() => {
    const navTiming = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    return navTiming ? navTiming.responseStart - navTiming.requestStart : -1;
  });

  return ttfb;
}

test.describe('Web Vitals Performance', () => {
  test.beforeEach(async ({ page }) => {
    // Ensure we're starting from a clean state
    await page.goto('/');
  });

  test('Homepage loads within FCP target', async ({ page }) => {
    const startTime = Date.now();
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    const fcp = await measureFCP(page);
    const loadTime = Date.now() - startTime;

    console.log(`Homepage FCP: ${fcp.toFixed(0)}ms (load time: ${loadTime}ms)`);

    expect(fcp).toBeGreaterThan(0);
    expect(fcp).toBeLessThan(SLA_TARGETS.fcp);
  });

  test('Homepage loads within LCP target', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    const lcp = await measureLCP(page);

    console.log(`Homepage LCP: ${lcp.toFixed(0)}ms`);

    expect(lcp).toBeGreaterThan(0);
    expect(lcp).toBeLessThan(SLA_TARGETS.lcp);
  });

  test('Homepage has acceptable CLS', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    const cls = await measureCLS(page);

    console.log(`Homepage CLS: ${cls.toFixed(3)}`);

    expect(cls).toBeLessThan(SLA_TARGETS.cls);
  });

  test('Marketplace page loads within FCP target', async ({ page }) => {
    const startTime = Date.now();
    await page.goto('/marketplace', { waitUntil: 'domcontentloaded' });

    const fcp = await measureFCP(page);
    const loadTime = Date.now() - startTime;

    console.log(`Marketplace FCP: ${fcp.toFixed(0)}ms (load time: ${loadTime}ms)`);

    expect(fcp).toBeGreaterThan(0);
    expect(fcp).toBeLessThan(SLA_TARGETS.fcp);
  });

  test('Marketplace page loads within LCP target', async ({ page }) => {
    await page.goto('/marketplace', { waitUntil: 'networkidle' });

    const lcp = await measureLCP(page);

    console.log(`Marketplace LCP: ${lcp.toFixed(0)}ms`);

    expect(lcp).toBeGreaterThan(0);
    expect(lcp).toBeLessThan(SLA_TARGETS.lcp);
  });

  test('Collections page loads within SLA', async ({ page }) => {
    const startTime = Date.now();
    await page.goto('/collections', { waitUntil: 'domcontentloaded' });

    const fcp = await measureFCP(page);
    const loadTime = Date.now() - startTime;

    console.log(`Collections FCP: ${fcp.toFixed(0)}ms (load time: ${loadTime}ms)`);

    expect(fcp).toBeGreaterThan(0);
    expect(fcp).toBeLessThan(SLA_TARGETS.fcp);
  });

  test('Search interaction is responsive', async ({ page }) => {
    await page.goto('/marketplace');
    await page.waitForLoadState('networkidle');

    // Measure search response time
    const startTime = Date.now();
    await page.fill('input[type="search"]', 'test query');

    // Wait for results to appear
    await page.waitForSelector('.marketplace-card, [data-testid="marketplace-card"]', {
      timeout: SLA_TARGETS.search,
    });

    const responseTime = Date.now() - startTime;

    console.log(`Search response time: ${responseTime}ms`);

    expect(responseTime).toBeLessThan(SLA_TARGETS.search);
  });

  test('Navigation between pages is fast', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Navigate to marketplace
    const startTime = Date.now();
    await page.click('a[href="/marketplace"]');
    await page.waitForURL('/marketplace');
    const navTime = Date.now() - startTime;

    console.log(`Navigation time: ${navTime}ms`);

    // Note: In production with Next.js, this should be very fast due to prefetching
    // We allow a bit more time for test environments
    expect(navTime).toBeLessThan(SLA_TARGETS.navigation * 2);
  });

  test('TTFB is within target', async ({ page }) => {
    await page.goto('/', { waitUntil: 'commit' });

    const ttfb = await measureTTFB(page);

    console.log(`TTFB: ${ttfb.toFixed(0)}ms`);

    expect(ttfb).toBeGreaterThan(0);
    expect(ttfb).toBeLessThan(SLA_TARGETS.ttfb);
  });

  test('Button interactions have low latency', async ({ page }) => {
    await page.goto('/marketplace');
    await page.waitForLoadState('networkidle');

    // Find a button or interactive element
    const button = page.locator('button').first();

    if ((await button.count()) > 0) {
      const startTime = Date.now();
      await button.click();
      const clickLatency = Date.now() - startTime;

      console.log(`Click latency: ${clickLatency}ms`);

      // Click should be nearly instantaneous
      expect(clickLatency).toBeLessThan(SLA_TARGETS.fid);
    } else {
      console.log('No buttons found to test interaction latency');
    }
  });

  test('Scrolling performance is smooth', async ({ page }) => {
    await page.goto('/marketplace');
    await page.waitForLoadState('networkidle');

    // Measure CLS during scroll
    const startCLS = await measureCLS(page);

    // Scroll down the page
    await page.evaluate(() => {
      window.scrollTo({ top: document.body.scrollHeight / 2, behavior: 'smooth' });
    });

    await page.waitForTimeout(1000);

    // Measure CLS after scroll
    const endCLS = await measureCLS(page);
    const clsDelta = endCLS - startCLS;

    console.log(`CLS during scroll: ${clsDelta.toFixed(3)}`);

    // Layout shifts during scroll should be minimal
    expect(clsDelta).toBeLessThan(0.05);
  });
});

test.describe('Performance Regression Tests', () => {
  test('Repeated page loads maintain performance', async ({ page }) => {
    const fcpTimes: number[] = [];

    // Load page 5 times
    for (let i = 0; i < 5; i++) {
      await page.goto('/', { waitUntil: 'domcontentloaded' });
      const fcp = await measureFCP(page);
      fcpTimes.push(fcp);

      // Clear cache between loads
      await page.context().clearCookies();
    }

    const avgFCP = fcpTimes.reduce((a, b) => a + b, 0) / fcpTimes.length;
    const maxFCP = Math.max(...fcpTimes);

    console.log(`Average FCP: ${avgFCP.toFixed(0)}ms, Max: ${maxFCP.toFixed(0)}ms`);

    // Average should be well under target
    expect(avgFCP).toBeLessThan(SLA_TARGETS.fcp * 0.8);

    // Worst case should still meet target
    expect(maxFCP).toBeLessThan(SLA_TARGETS.fcp);
  });

  test('Performance degrades gracefully under load', async ({ page }) => {
    await page.goto('/marketplace');
    await page.waitForLoadState('networkidle');

    const initialFCP = await measureFCP(page);

    // Simulate some load by triggering multiple searches
    const searchTimes: number[] = [];

    for (let i = 0; i < 10; i++) {
      const startTime = Date.now();
      await page.fill('input[type="search"]', `query ${i}`);
      await page.waitForTimeout(100);
      const searchTime = Date.now() - startTime;
      searchTimes.push(searchTime);
    }

    const avgSearchTime = searchTimes.reduce((a, b) => a + b, 0) / searchTimes.length;

    console.log(`Initial FCP: ${initialFCP.toFixed(0)}ms`);
    console.log(`Average search time under load: ${avgSearchTime.toFixed(0)}ms`);

    // Performance should remain reasonable under load
    expect(avgSearchTime).toBeLessThan(SLA_TARGETS.search * 0.5);
  });
});
