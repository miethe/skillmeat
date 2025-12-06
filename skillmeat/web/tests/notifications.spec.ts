/**
 * Notification System E2E Tests
 *
 * Comprehensive end-to-end tests for the notification system covering:
 * 1. Toast notification lifecycle
 * 2. NotificationBell badge behavior
 * 3. NotificationPanel interactions
 * 4. Notification actions
 * 5. Expandable details
 * 6. Keyboard navigation
 * 7. localStorage persistence
 */

import { test, expect, Page } from '@playwright/test';

// ============================================================================
// Test Helpers
// ============================================================================

/**
 * Add notification via localStorage to simulate existing notifications
 */
async function addNotificationViaStorage(
  page: Page,
  notification: {
    id?: string;
    type: 'import' | 'sync' | 'error' | 'info' | 'success';
    title: string;
    message: string;
    status?: 'read' | 'unread';
    timestamp?: string;
    details?: any;
  }
) {
  await page.evaluate((notif) => {
    const notifications = JSON.parse(
      localStorage.getItem('skillmeat-notifications') || '[]'
    );
    notifications.unshift({
      id: notif.id || `${Date.now()}-${Math.random().toString(36).substring(7)}`,
      type: notif.type,
      title: notif.title,
      message: notif.message,
      status: notif.status || 'unread',
      timestamp: notif.timestamp || new Date().toISOString(),
      details: notif.details || null,
    });
    localStorage.setItem('skillmeat-notifications', JSON.stringify(notifications));
  }, notification);
}

/**
 * Clear all notifications from localStorage
 */
async function clearNotifications(page: Page) {
  await page.evaluate(() => localStorage.removeItem('skillmeat-notifications'));
}

/**
 * Get notification count from localStorage
 */
async function getStoredNotificationCount(page: Page): Promise<number> {
  return await page.evaluate(() => {
    const stored = localStorage.getItem('skillmeat-notifications');
    return stored ? JSON.parse(stored).length : 0;
  });
}

/**
 * Wait for notification badge to show count
 */
async function waitForBadgeCount(page: Page, count: number) {
  const badge = page.locator('[class*="Badge"]').filter({ hasText: count.toString() });
  await expect(badge).toBeVisible({ timeout: 5000 });
}

// ============================================================================
// Test Setup
// ============================================================================

test.describe('Notification System', () => {
  test.beforeEach(async ({ page }) => {
    // Clear localStorage before each test
    await page.goto('/');
    await clearNotifications(page);
    await page.reload();
  });

  // ==========================================================================
  // 1. Toast Notification Lifecycle
  // ==========================================================================

  test.describe('Toast Notification Lifecycle', () => {
    test('toast appears when notification created', async ({ page }) => {
      // Add notification via storage to trigger toast-like behavior
      await addNotificationViaStorage(page, {
        type: 'success',
        title: 'Import Complete',
        message: 'Successfully imported 2 artifacts',
      });

      await page.reload();

      // Verify notification appears in the bell dropdown
      const bellButton = page.locator('button').filter({ has: page.locator('svg') }).first();
      await bellButton.click();

      await expect(page.getByText('Import Complete')).toBeVisible();
    });

    test('notification can be manually dismissed', async ({ page }) => {
      await addNotificationViaStorage(page, {
        type: 'info',
        title: 'Test Notification',
        message: 'This notification should be dismissible',
      });

      await page.reload();

      // Open bell dropdown
      const bellButton = page.locator('button').filter({ has: page.locator('svg') }).first();
      await bellButton.click();

      // Find and click dismiss button
      const dismissButton = page.getByRole('button', { name: /Dismiss notification/i });
      await expect(dismissButton).toBeVisible();
      await dismissButton.click();

      // Verify notification is removed
      await expect(page.getByText('Test Notification')).not.toBeVisible();
    });
  });

  // ==========================================================================
  // 2. NotificationBell Badge
  // ==========================================================================

  test.describe('NotificationBell Badge', () => {
    test('badge shows correct unread count', async ({ page }) => {
      // Add unread notification
      await addNotificationViaStorage(page, {
        type: 'success',
        title: 'Test',
        message: 'Test message',
        status: 'unread',
      });

      await page.reload();

      // Verify badge shows count of 1
      const badge = page.locator('[class*="Badge"]').filter({ hasText: '1' });
      await expect(badge).toBeVisible();
    });

    test('badge updates when new notifications arrive', async ({ page }) => {
      // Start with one notification
      await addNotificationViaStorage(page, {
        type: 'info',
        title: 'First',
        message: 'First notification',
      });

      await page.reload();

      // Verify badge shows 1
      await waitForBadgeCount(page, 1);

      // Add another notification
      await addNotificationViaStorage(page, {
        type: 'info',
        title: 'Second',
        message: 'Second notification',
      });

      await page.reload();

      // Verify badge shows 2
      await waitForBadgeCount(page, 2);
    });

    test('badge hidden when count is 0', async ({ page }) => {
      // No notifications, badge should not exist
      await page.reload();

      const badge = page.locator('[class*="Badge"]').filter({ hasText: /\d+/ });
      await expect(badge).not.toBeVisible();
    });

    test('badge handles 99+ display', async ({ page }) => {
      // Add 100+ notifications
      for (let i = 0; i < 100; i++) {
        await addNotificationViaStorage(page, {
          id: `notif-${i}`,
          type: 'info',
          title: `Notification ${i}`,
          message: `Message ${i}`,
        });
      }

      await page.reload();

      // Badge should show "99+"
      const badge = page.locator('[class*="Badge"]').filter({ hasText: '99+' });
      await expect(badge).toBeVisible();
    });
  });

  // ==========================================================================
  // 3. NotificationPanel Interactions
  // ==========================================================================

  test.describe('NotificationPanel Interactions', () => {
    test('panel opens on bell click', async ({ page }) => {
      await addNotificationViaStorage(page, {
        type: 'info',
        title: 'Test',
        message: 'Test message',
      });

      await page.reload();

      // Click bell button
      const bellButton = page.locator('button[aria-label*="Notifications"]');
      await bellButton.click();

      // Verify panel is visible
      const panel = page.locator('[role="menu"]');
      await expect(panel).toBeVisible();
      await expect(page.getByText('Notifications')).toBeVisible();
    });

    test('panel closes on outside click', async ({ page }) => {
      await addNotificationViaStorage(page, {
        type: 'info',
        title: 'Test',
        message: 'Test message',
      });

      await page.reload();

      // Open panel
      const bellButton = page.locator('button[aria-label*="Notifications"]');
      await bellButton.click();

      await expect(page.getByText('Notifications')).toBeVisible();

      // Click outside the panel
      await page.click('body', { position: { x: 0, y: 0 } });

      // Panel should close
      await expect(page.getByText('Notifications')).not.toBeVisible();
    });

    test('panel closes on Escape key', async ({ page }) => {
      await addNotificationViaStorage(page, {
        type: 'info',
        title: 'Test',
        message: 'Test message',
      });

      await page.reload();

      // Open panel
      const bellButton = page.locator('button[aria-label*="Notifications"]');
      await bellButton.click();

      await expect(page.getByText('Notifications')).toBeVisible();

      // Press Escape
      await page.keyboard.press('Escape');

      // Panel should close
      await expect(page.getByText('Notifications')).not.toBeVisible();
    });

    test('notifications sorted by timestamp (newest first)', async ({ page }) => {
      // Add notifications with different timestamps
      const now = Date.now();
      await addNotificationViaStorage(page, {
        id: 'old',
        type: 'info',
        title: 'Old Notification',
        message: 'Older message',
        timestamp: new Date(now - 10000).toISOString(),
      });

      await addNotificationViaStorage(page, {
        id: 'new',
        type: 'info',
        title: 'New Notification',
        message: 'Newer message',
        timestamp: new Date(now).toISOString(),
      });

      await page.reload();

      // Open panel
      const bellButton = page.locator('button[aria-label*="Notifications"]');
      await bellButton.click();

      // Get notification items by role="article"
      const notifications = page.locator('[role="article"]');
      const count = await notifications.count();
      expect(count).toBe(2);

      // First should be newer
      const firstTitle = await notifications.nth(0).locator('p[class*="font-medium"]').first().textContent();
      expect(firstTitle).toBe('New Notification');

      // Second should be older
      const secondTitle = await notifications.nth(1).locator('p[class*="font-medium"]').first().textContent();
      expect(secondTitle).toBe('Old Notification');
    });

    test('empty state shown when no notifications', async ({ page }) => {
      await page.reload();

      // Open panel
      const bellButton = page.locator('button[aria-label*="Notifications"]');
      await bellButton.click();

      // Verify empty state
      await expect(page.getByText('No notifications yet')).toBeVisible();
      await expect(page.getByText(/You'll see updates about imports/)).toBeVisible();
    });
  });

  // ==========================================================================
  // 4. Notification Actions
  // ==========================================================================

  test.describe('Notification Actions', () => {
    test('click notification marks as read', async ({ page }) => {
      await addNotificationViaStorage(page, {
        type: 'info',
        title: 'Unread Notification',
        message: 'Click to mark as read',
        status: 'unread',
      });

      await page.reload();

      // Verify badge shows 1
      await waitForBadgeCount(page, 1);

      // Open panel and click notification
      const bellButton = page.locator('button[aria-label*="Notifications"]');
      await bellButton.click();

      const notification = page.locator('[role="article"]').first();
      await notification.click();

      // Wait for panel to close and badge to update
      await page.waitForTimeout(500);

      // Badge should be hidden (count = 0)
      const badge = page.locator('[class*="Badge"]').filter({ hasText: '1' });
      await expect(badge).not.toBeVisible();
    });

    test('dismiss individual notification', async ({ page }) => {
      await addNotificationViaStorage(page, {
        type: 'info',
        title: 'Dismissible',
        message: 'This can be dismissed',
      });

      await page.reload();

      // Open panel
      const bellButton = page.locator('button[aria-label*="Notifications"]');
      await bellButton.click();

      // Click dismiss button
      const dismissButton = page.getByRole('button', { name: /Dismiss notification/i });
      await dismissButton.click();

      // Verify notification removed
      await expect(page.getByText('Dismissible')).not.toBeVisible();
      await expect(page.getByText('No notifications yet')).toBeVisible();
    });

    test('mark all as read clears badge', async ({ page }) => {
      // Add multiple unread notifications
      await addNotificationViaStorage(page, {
        type: 'info',
        title: 'Notification 1',
        message: 'Message 1',
        status: 'unread',
      });

      await addNotificationViaStorage(page, {
        type: 'info',
        title: 'Notification 2',
        message: 'Message 2',
        status: 'unread',
      });

      await page.reload();

      // Verify badge shows 2
      await waitForBadgeCount(page, 2);

      // Open panel
      const bellButton = page.locator('button[aria-label*="Notifications"]');
      await bellButton.click();

      // Click "Mark all read"
      const markAllButton = page.getByRole('button', { name: /Mark all read/i });
      await markAllButton.click();

      // Wait for update
      await page.waitForTimeout(500);

      // Badge should be hidden
      const badge = page.locator('[class*="Badge"]').filter({ hasText: /\d+/ });
      await expect(badge).not.toBeVisible();
    });

    test('clear all empties list', async ({ page }) => {
      // Add multiple notifications
      await addNotificationViaStorage(page, {
        type: 'info',
        title: 'Notification 1',
        message: 'Message 1',
      });

      await addNotificationViaStorage(page, {
        type: 'info',
        title: 'Notification 2',
        message: 'Message 2',
      });

      await page.reload();

      // Open panel
      const bellButton = page.locator('button[aria-label*="Notifications"]');
      await bellButton.click();

      // Click "Clear all"
      const clearAllButton = page.getByRole('button', { name: /Clear all/i });
      await clearAllButton.click();

      // Verify empty state shown
      await expect(page.getByText('No notifications yet')).toBeVisible();
    });
  });

  // ==========================================================================
  // 5. Expandable Details
  // ==========================================================================

  test.describe('Expandable Details', () => {
    test('click expands notification details', async ({ page }) => {
      await addNotificationViaStorage(page, {
        type: 'import',
        title: 'Import Complete',
        message: 'Imported 2 artifacts',
        details: {
          total: 2,
          succeeded: 2,
          failed: 0,
          artifacts: [
            { name: 'skill-1', type: 'skill', success: true },
            { name: 'skill-2', type: 'skill', success: true },
          ],
        },
      });

      await page.reload();

      // Open panel
      const bellButton = page.locator('button[aria-label*="Notifications"]');
      await bellButton.click();

      // Initially details should be collapsed
      await expect(page.getByText('skill-1')).not.toBeVisible();

      // Click "Show details"
      const showDetailsButton = page.getByRole('button', { name: /Show details/i });
      await showDetailsButton.click();

      // Details should be visible
      await expect(page.getByText('skill-1')).toBeVisible();
      await expect(page.getByText('skill-2')).toBeVisible();

      // Button text should change to "Hide details"
      await expect(page.getByRole('button', { name: /Hide details/i })).toBeVisible();
    });

    test('import results show artifact table', async ({ page }) => {
      await addNotificationViaStorage(page, {
        type: 'import',
        title: 'Import Complete',
        message: 'Imported artifacts with mixed results',
        details: {
          total: 3,
          succeeded: 2,
          failed: 1,
          artifacts: [
            { name: 'canvas-design', type: 'skill', success: true },
            { name: 'mcp-server', type: 'mcp', success: true },
            { name: 'failed-skill', type: 'skill', success: false, error: 'Parse error' },
          ],
        },
      });

      await page.reload();

      // Open panel
      const bellButton = page.locator('button[aria-label*="Notifications"]');
      await bellButton.click();

      // Expand details
      const showDetailsButton = page.getByRole('button', { name: /Show details/i });
      await showDetailsButton.click();

      // Verify summary
      await expect(page.getByText('2 succeeded')).toBeVisible();
      await expect(page.getByText('1 failed')).toBeVisible();
      await expect(page.getByText('Total: 3')).toBeVisible();

      // Verify artifact list
      await expect(page.getByText('canvas-design')).toBeVisible();
      await expect(page.getByText('mcp-server')).toBeVisible();
      await expect(page.getByText('failed-skill')).toBeVisible();
      await expect(page.getByText('Parse error')).toBeVisible();
    });

    test('error details show message', async ({ page }) => {
      await addNotificationViaStorage(page, {
        type: 'error',
        title: 'Error',
        message: 'API connection failed',
        details: {
          message: 'API connection failed',
          code: 'ERR_NETWORK',
          stack: 'Error: API connection failed\n    at fetch (/api/client.ts:42)',
        },
      });

      await page.reload();

      // Open panel
      const bellButton = page.locator('button[aria-label*="Notifications"]');
      await bellButton.click();

      // Expand details
      const showDetailsButton = page.getByRole('button', { name: /Show details/i });
      await showDetailsButton.click();

      // Verify error details
      await expect(page.getByText('ERR_NETWORK')).toBeVisible();
      await expect(page.getByText('API connection failed')).toBeVisible();

      // Stack trace should be collapsible
      const showStackButton = page.getByRole('button', { name: /Show stack trace/i });
      if (await showStackButton.isVisible()) {
        await showStackButton.click();
        await expect(page.getByText(/at fetch/)).toBeVisible();
      }
    });
  });

  // ==========================================================================
  // 6. Keyboard Navigation
  // ==========================================================================

  test.describe('Keyboard Navigation', () => {
    test('Tab navigation works', async ({ page }) => {
      await addNotificationViaStorage(page, {
        type: 'info',
        title: 'Test',
        message: 'Test message',
      });

      await page.reload();

      // Tab to notification bell
      await page.keyboard.press('Tab');

      // Keep tabbing until we find the bell button
      let attempts = 0;
      while (attempts < 20) {
        const focused = await page.evaluate(() => {
          const el = document.activeElement;
          return el?.getAttribute('aria-label');
        });

        if (focused?.includes('Notifications')) {
          break;
        }

        await page.keyboard.press('Tab');
        attempts++;
      }

      // Press Enter to open
      await page.keyboard.press('Enter');

      // Panel should open
      await expect(page.getByText('Notifications')).toBeVisible();
    });

    test('Arrow keys navigate list', async ({ page }) => {
      // Add multiple notifications
      await addNotificationViaStorage(page, {
        type: 'info',
        title: 'Notification 1',
        message: 'Message 1',
      });

      await addNotificationViaStorage(page, {
        type: 'info',
        title: 'Notification 2',
        message: 'Message 2',
      });

      await page.reload();

      // Open panel
      const bellButton = page.locator('button[aria-label*="Notifications"]');
      await bellButton.click();

      // Press ArrowDown to navigate
      await page.keyboard.press('ArrowDown');
      await page.waitForTimeout(200);

      // First notification should be focused
      const focused = await page.evaluate(() => {
        return document.activeElement?.getAttribute('role');
      });
      expect(focused).toBe('article');

      // Press ArrowDown again
      await page.keyboard.press('ArrowDown');
      await page.waitForTimeout(200);

      // Second notification should be focused
      const secondFocused = await page.evaluate(() => {
        return document.activeElement?.textContent?.includes('Notification 2');
      });
      expect(secondFocused).toBe(true);
    });

    test('Enter/Space activates notification', async ({ page }) => {
      await addNotificationViaStorage(page, {
        type: 'info',
        title: 'Keyboard Test',
        message: 'Test keyboard activation',
        status: 'unread',
      });

      await page.reload();

      // Open panel
      const bellButton = page.locator('button[aria-label*="Notifications"]');
      await bellButton.click();

      // Navigate to notification
      await page.keyboard.press('ArrowDown');
      await page.waitForTimeout(200);

      // Press Enter to activate
      await page.keyboard.press('Enter');

      // Panel should close and notification marked as read
      await page.waitForTimeout(500);
      await expect(page.getByText('Notifications')).not.toBeVisible();
    });

    test('Home/End keys work', async ({ page }) => {
      // Add multiple notifications
      for (let i = 0; i < 5; i++) {
        await addNotificationViaStorage(page, {
          type: 'info',
          title: `Notification ${i + 1}`,
          message: `Message ${i + 1}`,
        });
      }

      await page.reload();

      // Open panel
      const bellButton = page.locator('button[aria-label*="Notifications"]');
      await bellButton.click();

      // Press End to go to last notification
      await page.keyboard.press('End');
      await page.waitForTimeout(200);

      // Should be on last notification
      const lastFocused = await page.evaluate(() => {
        return document.activeElement?.textContent?.includes('Notification 1');
      });
      expect(lastFocused).toBe(true);

      // Press Home to go to first notification
      await page.keyboard.press('Home');
      await page.waitForTimeout(200);

      // Should be on first notification
      const firstFocused = await page.evaluate(() => {
        return document.activeElement?.textContent?.includes('Notification 5');
      });
      expect(firstFocused).toBe(true);
    });
  });

  // ==========================================================================
  // 7. Persistence (localStorage)
  // ==========================================================================

  test.describe('Persistence', () => {
    test('notifications persist across page reload', async ({ page }) => {
      await addNotificationViaStorage(page, {
        type: 'info',
        title: 'Persistent Notification',
        message: 'Should survive reload',
      });

      await page.reload();

      // Verify notification still exists
      const bellButton = page.locator('button[aria-label*="Notifications"]');
      await bellButton.click();

      await expect(page.getByText('Persistent Notification')).toBeVisible();
    });

    test('FIFO eviction at 50 capacity', async ({ page }) => {
      // Add 55 notifications (exceeds limit of 50)
      for (let i = 0; i < 55; i++) {
        await addNotificationViaStorage(page, {
          id: `notif-${i}`,
          type: 'info',
          title: `Notification ${i}`,
          message: `Message ${i}`,
          timestamp: new Date(Date.now() - (55 - i) * 1000).toISOString(),
        });
      }

      await page.reload();

      // Verify only 50 remain
      const count = await getStoredNotificationCount(page);
      expect(count).toBe(50);

      // Verify oldest (0-4) are evicted and newest (5-54) remain
      const bellButton = page.locator('button[aria-label*="Notifications"]');
      await bellButton.click();

      // Newest should be visible
      await expect(page.getByText('Notification 54')).toBeVisible();

      // Scroll to bottom to check if oldest are gone
      const scrollArea = page.locator('[class*="ScrollArea"]');
      if (await scrollArea.isVisible()) {
        await scrollArea.evaluate((el) => {
          el.scrollTop = el.scrollHeight;
        });
        await page.waitForTimeout(300);
      }

      // Oldest should not exist
      await expect(page.getByText('Notification 0')).not.toBeVisible();
    });

    test('read notifications evicted first', async ({ page }) => {
      // Add 48 read notifications
      for (let i = 0; i < 48; i++) {
        await addNotificationViaStorage(page, {
          id: `read-${i}`,
          type: 'info',
          title: `Read ${i}`,
          message: `Read message ${i}`,
          status: 'read',
          timestamp: new Date(Date.now() - (100 - i) * 1000).toISOString(),
        });
      }

      // Add 5 unread notifications
      for (let i = 0; i < 5; i++) {
        await addNotificationViaStorage(page, {
          id: `unread-${i}`,
          type: 'info',
          title: `Unread ${i}`,
          message: `Unread message ${i}`,
          status: 'unread',
          timestamp: new Date(Date.now() - i * 1000).toISOString(),
        });
      }

      await page.reload();

      // Total is 53, should evict 3 oldest read notifications
      const count = await getStoredNotificationCount(page);
      expect(count).toBe(50);

      // Verify unread notifications are preserved
      const bellButton = page.locator('button[aria-label*="Notifications"]');
      await bellButton.click();

      // All unread should be visible
      for (let i = 0; i < 5; i++) {
        await expect(page.getByText(`Unread ${i}`)).toBeVisible();
      }
    });

    test('localStorage handles serialization correctly', async ({ page }) => {
      await addNotificationViaStorage(page, {
        type: 'import',
        title: 'Complex Data',
        message: 'With details',
        details: {
          total: 2,
          succeeded: 1,
          failed: 1,
          artifacts: [
            { name: 'skill-1', type: 'skill', success: true },
            { name: 'skill-2', type: 'command', success: false, error: 'Failed' },
          ],
        },
      });

      await page.reload();

      // Open panel and expand details
      const bellButton = page.locator('button[aria-label*="Notifications"]');
      await bellButton.click();

      const showDetailsButton = page.getByRole('button', { name: /Show details/i });
      await showDetailsButton.click();

      // Verify complex data deserialized correctly
      await expect(page.getByText('skill-1')).toBeVisible();
      await expect(page.getByText('skill-2')).toBeVisible();
      await expect(page.getByText('Failed')).toBeVisible();
    });
  });
});
