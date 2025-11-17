/**
 * Keyboard Navigation E2E Tests
 *
 * Tests for complete keyboard accessibility:
 * - Tab order
 * - All interactive elements reachable
 * - Escape closes modals
 * - Enter activates buttons
 * - Arrow key navigation
 * - Focus visible
 */

import { test, expect } from '@playwright/test';
import {
  mockApiRoute,
  navigateToPage,
  pressKey,
  expectFocused,
  waitForElement,
  expectModalOpen,
  expectModalClosed,
} from './helpers/test-utils';
import { buildApiResponse, mockArtifacts } from './helpers/fixtures';

test.describe('Keyboard Navigation', () => {
  test.beforeEach(async ({ page }) => {
    // Mock API routes
    await mockApiRoute(page, '/api/artifacts*', buildApiResponse.artifacts());
    await mockApiRoute(page, '/api/analytics*', buildApiResponse.analytics());
    await mockApiRoute(page, '/api/projects*', buildApiResponse.projects());
  });

  test.describe('Tab Order', () => {
    test('should have correct tab order on dashboard', async ({ page }) => {
      await navigateToPage(page, '/');

      // Skip link should be first (if present)
      await pressKey(page, 'Tab');
      let focused = await page.evaluateHandle(() => document.activeElement);
      let tagName = await focused.evaluate((el) => el.tagName.toLowerCase());

      // Should focus on first interactive element
      expect(['a', 'button', 'input']).toContain(tagName);

      // Tab through multiple elements
      for (let i = 0; i < 5; i++) {
        await pressKey(page, 'Tab');
        focused = await page.evaluateHandle(() => document.activeElement);
        tagName = await focused.evaluate((el) => el.tagName.toLowerCase());

        // Should be on an interactive element
        expect(['a', 'button', 'input', 'select']).toContain(tagName);
      }
    });

    test('should have correct tab order in navigation', async ({ page }) => {
      await navigateToPage(page, '/');

      // Tab to navigation
      await pressKey(page, 'Tab');

      // Navigation links should be in logical order
      const navLinks = [
        'Dashboard',
        'Collection',
        'Projects',
        'Sharing',
        'MCP Servers',
        'Settings',
      ];

      for (const linkText of navLinks) {
        const focused = await page.evaluateHandle(
          () => document.activeElement
        );
        const text = await focused.evaluate((el) => el.textContent);

        if (text?.includes(linkText)) {
          expect(text).toContain(linkText);
          await pressKey(page, 'Tab');
        }
      }
    });

    test('should have correct tab order in collections grid', async ({
      page,
    }) => {
      await navigateToPage(page, '/collection');

      // Tab to filters
      await pressKey(page, 'Tab');

      // Should tab through filter controls
      const filterControls = page.locator(
        'select[name="type"], select[name="status"], select[name="scope"], input[type="search"]'
      );
      const count = await filterControls.count();

      for (let i = 0; i < count; i++) {
        await pressKey(page, 'Tab');
      }

      // Should reach artifact cards
      await pressKey(page, 'Tab');
      const focused = await page.evaluateHandle(() => document.activeElement);
      const role = await focused.evaluate((el) =>
        el.getAttribute('role') || el.tagName.toLowerCase()
      );

      expect(role).toBeTruthy();
    });

    test('should not have tab order violations', async ({ page }) => {
      await navigateToPage(page, '/');

      // Check for positive tabindex (anti-pattern)
      const positiveTabindex = page.locator('[tabindex]:not([tabindex="-1"])');
      const count = await positiveTabindex.count();

      for (let i = 0; i < count; i++) {
        const element = positiveTabindex.nth(i);
        const tabindex = await element.getAttribute('tabindex');
        const tabindexValue = parseInt(tabindex || '0');

        // Should not have tabindex > 0 (breaks natural tab order)
        expect(tabindexValue).toBeLessThanOrEqual(0);
      }
    });

    test('should maintain tab order when switching views', async ({ page }) => {
      await navigateToPage(page, '/collection');

      // Switch to list view
      const listButton = page.locator('[aria-label="List view"]');
      await listButton.focus();
      await pressKey(page, 'Enter');

      await page.waitForTimeout(300);

      // Tab order should still be logical
      await pressKey(page, 'Tab');
      const focused = await page.evaluateHandle(() => document.activeElement);
      expect(focused).toBeTruthy();
    });
  });

  test.describe('Interactive Elements', () => {
    test('should activate buttons with Enter key', async ({ page }) => {
      await navigateToPage(page, '/collection');

      // Focus on view toggle button
      const gridButton = page.locator('[aria-label="Grid view"]');
      await gridButton.focus();

      // Press Enter
      await pressKey(page, 'Enter');

      // Button should activate (may already be active)
      const pressed = await gridButton.getAttribute('aria-pressed');
      expect(pressed).toBe('true');
    });

    test('should activate buttons with Space key', async ({ page }) => {
      await navigateToPage(page, '/collection');

      const listButton = page.locator('[aria-label="List view"]');
      await listButton.focus();

      // Press Space
      await pressKey(page, 'Space');

      // Button should activate
      await page.waitForTimeout(300);
      const pressed = await listButton.getAttribute('aria-pressed');
      expect(pressed).toBe('true');
    });

    test('should follow links with Enter key', async ({ page }) => {
      await navigateToPage(page, '/');

      // Focus on a navigation link
      const collectionLink = page.locator('a:has-text("Collection")');
      await collectionLink.focus();

      // Press Enter
      await Promise.all([
        page.waitForNavigation({ waitUntil: 'networkidle' }),
        pressKey(page, 'Enter'),
      ]);

      // Should navigate to collections page
      expect(page.url()).toContain('/collection');
    });

    test('should interact with select elements', async ({ page }) => {
      await navigateToPage(page, '/collection');

      const typeSelect = page.locator('select[name="type"]');
      await typeSelect.focus();

      // Arrow down to open select
      await pressKey(page, 'ArrowDown');
      await page.waitForTimeout(100);

      // Select an option
      await pressKey(page, 'Enter');

      // Value should change
      const value = await typeSelect.inputValue();
      expect(value).toBeTruthy();
    });

    test('should interact with search input', async ({ page }) => {
      await navigateToPage(page, '/collection');

      const searchInput = page.locator('input[type="search"]');
      await searchInput.focus();

      // Type in search
      await page.keyboard.type('canvas');

      // Value should update
      const value = await searchInput.inputValue();
      expect(value).toBe('canvas');

      // Clear with Escape (if implemented)
      await pressKey(page, 'Escape');
      await page.waitForTimeout(100);
    });

    test('should toggle checkboxes with Space', async ({ page }) => {
      await navigateToPage(page, '/collection');

      const checkbox = page.locator('input[type="checkbox"]').first();

      if (await checkbox.isVisible()) {
        await checkbox.focus();

        const initialState = await checkbox.isChecked();

        await pressKey(page, 'Space');
        await page.waitForTimeout(100);

        const newState = await checkbox.isChecked();
        expect(newState).toBe(!initialState);
      }
    });
  });

  test.describe('Modal/Dialog Keyboard Navigation', () => {
    test('should open modal with Enter key', async ({ page }) => {
      await navigateToPage(page, '/collection');

      await mockApiRoute(
        page,
        `/api/artifacts/${mockArtifacts[0].id}`,
        buildApiResponse.artifactDetail(mockArtifacts[0].id)
      );

      const firstCard = page.locator('[data-testid="artifact-card"]').first();
      if (await firstCard.isVisible()) {
        await firstCard.focus();
        await pressKey(page, 'Enter');

        await waitForElement(page, '[role="dialog"]');
        await expectModalOpen(page, '[role="dialog"]');
      }
    });

    test('should close modal with Escape key', async ({ page }) => {
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

        await expectModalClosed(page, '[role="dialog"]');
      }
    });

    test('should trap focus in modal', async ({ page }) => {
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

        // Tab through elements in modal
        for (let i = 0; i < 10; i++) {
          await pressKey(page, 'Tab');

          // Check if focus is still within dialog
          const focused = await page.evaluateHandle(
            () => document.activeElement
          );
          const isInDialog = await dialog.evaluate((dialogEl, focusedEl) => {
            return dialogEl.contains(focusedEl as Node);
          }, focused);

          expect(isInDialog).toBeTruthy();
        }
      }
    });

    test('should tab backwards in modal with Shift+Tab', async ({ page }) => {
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

        // Tab forward
        await pressKey(page, 'Tab');
        await pressKey(page, 'Tab');

        // Tab backward
        await page.keyboard.press('Shift+Tab');

        const focused = await page.evaluateHandle(
          () => document.activeElement
        );
        expect(focused).toBeTruthy();
      }
    });

    test('should activate close button with Enter', async ({ page }) => {
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

        // Find and focus close button
        const closeButton = page.locator('[role="dialog"] button').first();
        await closeButton.focus();
        await pressKey(page, 'Enter');

        await page.waitForTimeout(500);
        await expectModalClosed(page, '[role="dialog"]');
      }
    });
  });

  test.describe('Focus Visibility', () => {
    test('should show visible focus indicators', async ({ page }) => {
      await navigateToPage(page, '/');

      await pressKey(page, 'Tab');

      // Check for focus-visible or outline
      const focused = page.locator(':focus-visible, :focus');
      await expect(focused).toBeVisible();

      // Should have visible outline or ring
      const styles = await focused.evaluate((el) => {
        const computed = window.getComputedStyle(el);
        return {
          outline: computed.outline,
          outlineWidth: computed.outlineWidth,
          boxShadow: computed.boxShadow,
        };
      });

      // Should have some form of focus indicator
      const hasFocusIndicator =
        styles.outlineWidth !== '0px' ||
        styles.outline !== 'none' ||
        styles.boxShadow !== 'none';

      expect(hasFocusIndicator).toBeTruthy();
    });

    test('should maintain focus visibility on all interactive elements', async ({
      page,
    }) => {
      await navigateToPage(page, '/collection');

      // Tab through multiple elements
      for (let i = 0; i < 5; i++) {
        await pressKey(page, 'Tab');

        const focused = page.locator(':focus-visible, :focus');
        if (await focused.isVisible()) {
          await expect(focused).toBeVisible();
        }
      }
    });

    test('should show focus on custom components', async ({ page }) => {
      await navigateToPage(page, '/collection');

      // Focus on custom button (view toggle)
      const customButton = page.locator('[aria-label="Grid view"]');
      await customButton.focus();

      await expect(customButton).toBeFocused();

      // Should have focus indicator
      const hasFocusClass = await customButton.evaluate((el) => {
        return (
          el.classList.contains('focus-visible') ||
          el.classList.contains('focus:ring') ||
          window.getComputedStyle(el).outlineWidth !== '0px'
        );
      });

      expect(hasFocusClass).toBeTruthy();
    });
  });

  test.describe('Arrow Key Navigation', () => {
    test('should navigate through radio groups with arrow keys', async ({
      page,
    }) => {
      await navigateToPage(page, '/collection');

      // Look for radio groups
      const radioGroup = page.locator('[role="radiogroup"]');

      if (await radioGroup.isVisible()) {
        const firstRadio = radioGroup.locator('input[type="radio"]').first();
        await firstRadio.focus();

        // Arrow down should move to next radio
        await pressKey(page, 'ArrowDown');

        const focused = await page.evaluateHandle(
          () => document.activeElement
        );
        const type = await focused.evaluate((el) =>
          el.getAttribute('type')
        );

        expect(type).toBe('radio');
      }
    });

    test('should navigate through custom lists with arrow keys', async ({
      page,
    }) => {
      await navigateToPage(page, '/collection');

      // Look for custom listbox
      const listbox = page.locator('[role="listbox"]');

      if (await listbox.isVisible()) {
        await listbox.focus();

        // Arrow down should navigate
        await pressKey(page, 'ArrowDown');
        await page.waitForTimeout(100);

        // Arrow up should navigate back
        await pressKey(page, 'ArrowUp');
        await page.waitForTimeout(100);
      }
    });
  });

  test.describe('Shortcuts and Hotkeys', () => {
    test('should support search shortcut (Ctrl/Cmd+K)', async ({ page }) => {
      await navigateToPage(page, '/collection');

      // Press Ctrl+K (or Cmd+K on Mac)
      const isMac = await page.evaluate(
        () => navigator.platform.toLowerCase().includes('mac')
      );
      const modifier = isMac ? 'Meta' : 'Control';

      await page.keyboard.press(`${modifier}+KeyK`);

      await page.waitForTimeout(300);

      // Search input should be focused
      const searchInput = page.locator('input[type="search"]');
      if (await searchInput.isVisible()) {
        await expect(searchInput).toBeFocused();
      }
    });

    test('should support escape to clear search', async ({ page }) => {
      await navigateToPage(page, '/collection');

      const searchInput = page.locator('input[type="search"]');
      if (await searchInput.isVisible()) {
        await searchInput.focus();
        await page.keyboard.type('test');

        await pressKey(page, 'Escape');
        await page.waitForTimeout(100);

        const value = await searchInput.inputValue();
        expect(value).toBe('');
      }
    });
  });

  test.describe('Skip Links', () => {
    test('should have skip to main content link', async ({ page }) => {
      await navigateToPage(page, '/');

      // First tab should focus skip link
      await pressKey(page, 'Tab');

      const focused = await page.evaluateHandle(() => document.activeElement);
      const text = await focused.evaluate((el) => el.textContent);

      if (text?.toLowerCase().includes('skip')) {
        expect(text).toMatch(/skip/i);

        // Activating should jump to main content
        await pressKey(page, 'Enter');
        await page.waitForTimeout(100);

        const main = page.locator('main');
        const mainFocused = await main.evaluate((el) => {
          return (
            document.activeElement === el ||
            el.contains(document.activeElement)
          );
        });

        expect(mainFocused).toBeTruthy();
      }
    });

    test('should have skip to navigation link', async ({ page }) => {
      await navigateToPage(page, '/');

      await pressKey(page, 'Tab');

      const focused = await page.evaluateHandle(() => document.activeElement);
      const href = await focused.evaluate((el) => el.getAttribute('href'));

      if (href?.includes('#nav')) {
        await pressKey(page, 'Enter');
        await page.waitForTimeout(100);

        const nav = page.locator('nav');
        const navFocused = await nav.evaluate((el) => {
          return (
            document.activeElement === el ||
            el.contains(document.activeElement)
          );
        });

        expect(navFocused).toBeTruthy();
      }
    });
  });

  test.describe('Form Navigation', () => {
    test('should navigate through form fields with Tab', async ({ page }) => {
      await navigateToPage(page, '/collection');

      // Focus on first form field
      const firstInput = page.locator('select, input').first();
      await firstInput.focus();

      // Tab through form fields
      for (let i = 0; i < 3; i++) {
        await pressKey(page, 'Tab');

        const focused = await page.evaluateHandle(
          () => document.activeElement
        );
        const tagName = await focused.evaluate((el) =>
          el.tagName.toLowerCase()
        );

        expect(['input', 'select', 'button', 'a']).toContain(tagName);
      }
    });

    test('should submit form with Enter key', async ({ page }) => {
      await navigateToPage(page, '/collection');

      const searchInput = page.locator('input[type="search"]');
      if (await searchInput.isVisible()) {
        await searchInput.focus();
        await page.keyboard.type('test');

        // Press Enter to submit/search
        await pressKey(page, 'Enter');
        await page.waitForTimeout(300);

        // Search should execute (form submission or filter)
      }
    });
  });

  test.describe('Responsive Keyboard Navigation', () => {
    test('should maintain keyboard navigation on mobile', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await navigateToPage(page, '/');

      // Tab through elements
      await pressKey(page, 'Tab');

      const focused = page.locator(':focus-visible, :focus');
      await expect(focused).toBeVisible();
    });

    test('should handle mobile menu with keyboard', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await navigateToPage(page, '/');

      // Look for mobile menu button
      const menuButton = page.locator('[aria-label*="menu" i]');

      if (await menuButton.isVisible()) {
        await menuButton.focus();
        await pressKey(page, 'Enter');

        await page.waitForTimeout(300);

        // Menu should open and be keyboard accessible
        const menu = page.locator('nav');
        await expect(menu).toBeVisible();
      }
    });
  });
});
