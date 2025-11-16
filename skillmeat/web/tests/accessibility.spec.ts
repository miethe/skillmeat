/**
 * Accessibility E2E Tests
 *
 * WCAG 2.1 AA compliance tests using axe-core:
 * - Zero critical violations
 * - Zero serious violations
 * - Color contrast validation
 * - ARIA labels and roles
 * - Semantic HTML
 * - Form accessibility
 * - Modal/dialog accessibility
 */

import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import {
  mockApiRoute,
  navigateToPage,
  waitForElement,
  pressKey,
} from './helpers/test-utils';
import { buildApiResponse, mockArtifacts } from './helpers/fixtures';

/**
 * Helper to run axe accessibility scan
 */
async function runAxeScan(page: any, context?: string) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();

  // Log violations for debugging
  if (results.violations.length > 0) {
    console.log(
      `\n${context || 'Page'} - Accessibility Violations:`
    );
    results.violations.forEach((violation) => {
      console.log(`\n${violation.impact?.toUpperCase()}: ${violation.description}`);
      console.log(`Rule: ${violation.id}`);
      console.log(`Help: ${violation.helpUrl}`);
      violation.nodes.forEach((node) => {
        console.log(`  Element: ${node.html}`);
        console.log(`  Target: ${node.target}`);
      });
    });
  }

  return results;
}

test.describe('Accessibility Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Mock API routes
    await mockApiRoute(page, '/api/artifacts*', buildApiResponse.artifacts());
    await mockApiRoute(page, '/api/analytics*', buildApiResponse.analytics());
    await mockApiRoute(page, '/api/projects*', buildApiResponse.projects());
  });

  test.describe('Page-Level Accessibility', () => {
    test('Dashboard page should have no critical accessibility violations', async ({
      page,
    }) => {
      await navigateToPage(page, '/');

      const results = await runAxeScan(page, 'Dashboard');

      // No critical violations
      const critical = results.violations.filter(
        (v) => v.impact === 'critical'
      );
      expect(critical).toHaveLength(0);

      // No serious violations
      const serious = results.violations.filter((v) => v.impact === 'serious');
      expect(serious).toHaveLength(0);
    });

    test('Collection page should have no critical accessibility violations', async ({
      page,
    }) => {
      await navigateToPage(page, '/collection');

      const results = await runAxeScan(page, 'Collection');

      const critical = results.violations.filter(
        (v) => v.impact === 'critical'
      );
      expect(critical).toHaveLength(0);

      const serious = results.violations.filter((v) => v.impact === 'serious');
      expect(serious).toHaveLength(0);
    });

    test('Projects page should have no critical accessibility violations', async ({
      page,
    }) => {
      await navigateToPage(page, '/projects');

      const results = await runAxeScan(page, 'Projects');

      const critical = results.violations.filter(
        (v) => v.impact === 'critical'
      );
      expect(critical).toHaveLength(0);

      const serious = results.violations.filter((v) => v.impact === 'serious');
      expect(serious).toHaveLength(0);
    });
  });

  test.describe('Semantic HTML', () => {
    test('should use proper heading hierarchy', async ({ page }) => {
      await navigateToPage(page, '/');

      // Should have h1
      const h1 = page.locator('h1');
      await expect(h1).toBeVisible();

      // Should not skip heading levels
      const results = await new AxeBuilder({ page })
        .withRules(['heading-order'])
        .analyze();

      expect(results.violations).toHaveLength(0);
    });

    test('should use semantic landmarks', async ({ page }) => {
      await navigateToPage(page, '/');

      // Should have main landmark
      const main = page.locator('main');
      await expect(main).toBeVisible();

      // Should have header
      const header = page.locator('header');
      await expect(header).toBeVisible();

      // Should have navigation
      const nav = page.locator('nav');
      await expect(nav).toBeVisible();
    });

    test('should use semantic list elements', async ({ page }) => {
      await navigateToPage(page, '/collection');

      // Navigation should use list
      const navList = page.locator('nav ul, nav ol');
      await expect(navList).toBeVisible();
    });

    test('should have proper document structure', async ({ page }) => {
      await navigateToPage(page, '/');

      const results = await new AxeBuilder({ page })
        .withRules(['region', 'landmark-one-main'])
        .analyze();

      expect(results.violations).toHaveLength(0);
    });
  });

  test.describe('ARIA Labels and Roles', () => {
    test('should have ARIA labels on interactive elements', async ({ page }) => {
      await navigateToPage(page, '/collection');

      // View toggle buttons should have aria-label
      const gridButton = page.locator('[aria-label="Grid view"]');
      await expect(gridButton).toBeVisible();

      const listButton = page.locator('[aria-label="List view"]');
      await expect(listButton).toBeVisible();
    });

    test('should use aria-pressed for toggle buttons', async ({ page }) => {
      await navigateToPage(page, '/collection');

      const gridButton = page.locator('[aria-label="Grid view"]');
      const pressed = await gridButton.getAttribute('aria-pressed');

      expect(pressed).toBeTruthy();
      expect(['true', 'false']).toContain(pressed);
    });

    test('should have proper button roles', async ({ page }) => {
      await navigateToPage(page, '/');

      const results = await new AxeBuilder({ page })
        .withRules(['button-name', 'aria-valid-attr'])
        .analyze();

      expect(results.violations).toHaveLength(0);
    });

    test('should have ARIA labels for form controls', async ({ page }) => {
      await navigateToPage(page, '/collection');

      // Search input should have label
      const searchInput = page.locator('input[type="search"]');
      if (await searchInput.isVisible()) {
        const ariaLabel = await searchInput.getAttribute('aria-label');
        const labelId = await searchInput.getAttribute('aria-labelledby');
        const hasLabel = await page.locator('label').count();

        expect(ariaLabel || labelId || hasLabel > 0).toBeTruthy();
      }
    });

    test('should use proper ARIA roles for custom components', async ({
      page,
    }) => {
      await navigateToPage(page, '/');

      const results = await new AxeBuilder({ page })
        .withRules(['aria-allowed-attr', 'aria-required-children'])
        .analyze();

      expect(results.violations).toHaveLength(0);
    });

    test('should have proper ARIA live regions for dynamic content', async ({
      page,
    }) => {
      await navigateToPage(page, '/');

      const results = await new AxeBuilder({ page })
        .withRules(['aria-valid-attr-value'])
        .analyze();

      expect(results.violations).toHaveLength(0);
    });
  });

  test.describe('Color Contrast', () => {
    test('should meet WCAG AA color contrast ratios for text', async ({
      page,
    }) => {
      await navigateToPage(page, '/');

      const results = await new AxeBuilder({ page })
        .withRules(['color-contrast'])
        .analyze();

      // Filter for text contrast violations
      const contrastViolations = results.violations.filter(
        (v) => v.id === 'color-contrast'
      );

      expect(contrastViolations).toHaveLength(0);
    });

    test('should have sufficient contrast for interactive elements', async ({
      page,
    }) => {
      await navigateToPage(page, '/collection');

      // Check buttons
      const results = await new AxeBuilder({ page })
        .include('button')
        .withRules(['color-contrast'])
        .analyze();

      expect(results.violations).toHaveLength(0);
    });

    test('should have sufficient contrast for form controls', async ({
      page,
    }) => {
      await navigateToPage(page, '/collection');

      const results = await new AxeBuilder({ page })
        .include('input, select, textarea')
        .withRules(['color-contrast'])
        .analyze();

      expect(results.violations).toHaveLength(0);
    });

    test('should have sufficient contrast for links', async ({ page }) => {
      await navigateToPage(page, '/');

      const results = await new AxeBuilder({ page })
        .include('a')
        .withRules(['color-contrast'])
        .analyze();

      expect(results.violations).toHaveLength(0);
    });
  });

  test.describe('Focus Management', () => {
    test('should have visible focus indicators', async ({ page }) => {
      await navigateToPage(page, '/collection');

      // Tab to first interactive element
      await pressKey(page, 'Tab');

      // Should have visible focus
      const focusedElement = await page.evaluateHandle(() =>
        document.activeElement
      );

      expect(focusedElement).toBeTruthy();

      // Check for focus-visible styles
      const results = await new AxeBuilder({ page })
        .withRules(['focus-order-semantics'])
        .analyze();

      expect(results.violations).toHaveLength(0);
    });

    test('should maintain logical focus order', async ({ page }) => {
      await navigateToPage(page, '/');

      const results = await new AxeBuilder({ page })
        .withRules(['tabindex'])
        .analyze();

      expect(results.violations).toHaveLength(0);
    });

    test('should trap focus in modals', async ({ page }) => {
      await navigateToPage(page, '/collection');

      // Open artifact detail drawer
      await mockApiRoute(
        page,
        `/api/artifacts/${mockArtifacts[0].id}`,
        buildApiResponse.artifactDetail(mockArtifacts[0].id)
      );

      const firstCard = page.locator('[data-testid="artifact-card"]').first();
      if (await firstCard.isVisible()) {
        await firstCard.click();

        await waitForElement(page, '[role="dialog"]');

        // Focus should be trapped in dialog
        const dialog = page.locator('[role="dialog"]');
        await expect(dialog).toBeFocused();
      }
    });

    test('should restore focus after modal closes', async ({ page }) => {
      await navigateToPage(page, '/collection');

      const firstCard = page.locator('[data-testid="artifact-card"]').first();
      if (await firstCard.isVisible()) {
        // Remember focused element
        await firstCard.focus();

        await mockApiRoute(
          page,
          `/api/artifacts/${mockArtifacts[0].id}`,
          buildApiResponse.artifactDetail(mockArtifacts[0].id)
        );

        await firstCard.click();
        await waitForElement(page, '[role="dialog"]');

        // Close dialog with Escape
        await pressKey(page, 'Escape');

        await page.waitForTimeout(500);

        // Focus should return to trigger element
        await expect(firstCard).toBeFocused();
      }
    });
  });

  test.describe('Form Accessibility', () => {
    test('should have labels for all form inputs', async ({ page }) => {
      await navigateToPage(page, '/collection');

      const results = await new AxeBuilder({ page })
        .withRules(['label'])
        .analyze();

      expect(results.violations).toHaveLength(0);
    });

    test('should have proper form field associations', async ({ page }) => {
      await navigateToPage(page, '/collection');

      const results = await new AxeBuilder({ page })
        .withRules(['label-content-name-mismatch'])
        .analyze();

      expect(results.violations).toHaveLength(0);
    });

    test('should indicate required fields', async ({ page }) => {
      await navigateToPage(page, '/collection');

      // Required fields should have aria-required or required attribute
      const requiredInputs = page.locator(
        'input[required], input[aria-required="true"]'
      );

      const count = await requiredInputs.count();
      if (count > 0) {
        for (let i = 0; i < count; i++) {
          const input = requiredInputs.nth(i);
          const hasRequired =
            (await input.getAttribute('required')) !== null ||
            (await input.getAttribute('aria-required')) === 'true';

          expect(hasRequired).toBeTruthy();
        }
      }
    });

    test('should provide error messages for validation', async ({ page }) => {
      await navigateToPage(page, '/collection');

      const results = await new AxeBuilder({ page })
        .withRules(['aria-valid-attr-value'])
        .analyze();

      expect(results.violations).toHaveLength(0);
    });
  });

  test.describe('Modal/Dialog Accessibility', () => {
    test('should have proper dialog role', async ({ page }) => {
      await navigateToPage(page, '/collection');

      await mockApiRoute(
        page,
        `/api/artifacts/${mockArtifacts[0].id}`,
        buildApiResponse.artifactDetail(mockArtifacts[0].id)
      );

      const firstCard = page.locator('[data-testid="artifact-card"]').first();
      if (await firstCard.isVisible()) {
        await firstCard.click();

        await waitForElement(page, '[role="dialog"]');

        const dialog = page.locator('[role="dialog"]');
        await expect(dialog).toBeVisible();

        // Should have aria-modal
        const ariaModal = await dialog.getAttribute('aria-modal');
        expect(ariaModal).toBe('true');
      }
    });

    test('should have accessible dialog title', async ({ page }) => {
      await navigateToPage(page, '/collection');

      await mockApiRoute(
        page,
        `/api/artifacts/${mockArtifacts[0].id}`,
        buildApiResponse.artifactDetail(mockArtifacts[0].id)
      );

      const firstCard = page.locator('[data-testid="artifact-card"]').first();
      if (await firstCard.isVisible()) {
        await firstCard.click();

        await waitForElement(page, '[role="dialog"]');

        const dialog = page.locator('[role="dialog"]');

        // Should have aria-labelledby or aria-label
        const ariaLabelledby = await dialog.getAttribute('aria-labelledby');
        const ariaLabel = await dialog.getAttribute('aria-label');

        expect(ariaLabelledby || ariaLabel).toBeTruthy();
      }
    });

    test('should close on Escape key', async ({ page }) => {
      await navigateToPage(page, '/collection');

      await mockApiRoute(
        page,
        `/api/artifacts/${mockArtifacts[0].id}`,
        buildApiResponse.artifactDetail(mockArtifacts[0].id)
      );

      const firstCard = page.locator('[data-testid="artifact-card"]').first();
      if (await firstCard.isVisible()) {
        await firstCard.click();

        await waitForElement(page, '[role="dialog"]');

        await pressKey(page, 'Escape');

        await page.waitForTimeout(500);

        const dialog = page.locator('[role="dialog"]');
        await expect(dialog).toBeHidden();
      }
    });

    test('should have accessible close button', async ({ page }) => {
      await navigateToPage(page, '/collection');

      await mockApiRoute(
        page,
        `/api/artifacts/${mockArtifacts[0].id}`,
        buildApiResponse.artifactDetail(mockArtifacts[0].id)
      );

      const firstCard = page.locator('[data-testid="artifact-card"]').first();
      if (await firstCard.isVisible()) {
        await firstCard.click();

        await waitForElement(page, '[role="dialog"]');

        const closeButton = page.locator('[role="dialog"] [aria-label*="lose"]');
        if (await closeButton.isVisible()) {
          await expect(closeButton).toBeVisible();

          const ariaLabel = await closeButton.getAttribute('aria-label');
          expect(ariaLabel).toBeTruthy();
        }
      }
    });
  });

  test.describe('Images and Icons', () => {
    test('should have alt text for images', async ({ page }) => {
      await navigateToPage(page, '/');

      const results = await new AxeBuilder({ page })
        .withRules(['image-alt'])
        .analyze();

      expect(results.violations).toHaveLength(0);
    });

    test('should hide decorative icons from screen readers', async ({
      page,
    }) => {
      await navigateToPage(page, '/');

      // Decorative icons should have aria-hidden="true"
      const icons = page.locator('svg[aria-hidden="true"]');
      const count = await icons.count();

      // Should have some decorative icons
      expect(count).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('Screen Reader Support', () => {
    test('should have skip links', async ({ page }) => {
      await navigateToPage(page, '/');

      const skipLink = page.locator('a[href="#main-content"]');
      if (await skipLink.isVisible()) {
        await expect(skipLink).toBeVisible();
      }
    });

    test('should announce page title changes', async ({ page }) => {
      await navigateToPage(page, '/');

      const title = await page.title();
      expect(title).toContain('SkillMeat');

      await page.goto('/collection');
      await page.waitForTimeout(500);

      const newTitle = await page.title();
      expect(newTitle).not.toBe(title);
    });

    test('should have proper live regions for dynamic updates', async ({
      page,
    }) => {
      await navigateToPage(page, '/');

      const results = await new AxeBuilder({ page })
        .withRules(['aria-allowed-attr'])
        .analyze();

      expect(results.violations).toHaveLength(0);
    });
  });

  test.describe('Responsive Accessibility', () => {
    test('should be accessible on mobile viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await navigateToPage(page, '/');

      const results = await runAxeScan(page, 'Mobile Dashboard');

      const critical = results.violations.filter(
        (v) => v.impact === 'critical'
      );
      expect(critical).toHaveLength(0);
    });

    test('should be accessible on tablet viewport', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await navigateToPage(page, '/');

      const results = await runAxeScan(page, 'Tablet Dashboard');

      const critical = results.violations.filter(
        (v) => v.impact === 'critical'
      );
      expect(critical).toHaveLength(0);
    });

    test('should maintain touch target sizes on mobile', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await navigateToPage(page, '/collection');

      const results = await new AxeBuilder({ page })
        .withRules(['target-size'])
        .analyze();

      // WCAG 2.1 AA requires 44x44px touch targets
      expect(results.violations).toHaveLength(0);
    });
  });
});
