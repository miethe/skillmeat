/**
 * @jest-environment jsdom
 */
import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react';
import { NotificationProvider, useNotifications } from '@/lib/notification-store';
import type { NotificationCreateInput, NotificationData } from '@/types/notification';

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <NotificationProvider>{children}</NotificationProvider>
);

// localStorage mock
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: jest.fn((key: string) => store[key] || null),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value;
    }),
    clear: jest.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(window, 'localStorage', { value: localStorageMock });

beforeEach(() => {
  localStorageMock.clear();
  jest.clearAllMocks();
});

describe('useNotifications', () => {
  describe('Initial State', () => {
    it('should initialize with empty notifications array', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      expect(result.current.notifications).toEqual([]);
    });

    it('should initialize with unreadCount of 0', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      expect(result.current.unreadCount).toBe(0);
    });

    it('should throw error when used outside NotificationProvider', () => {
      // Suppress console.error for this test
      const originalError = console.error;
      console.error = jest.fn();

      expect(() => {
        renderHook(() => useNotifications());
      }).toThrow('useNotifications must be used within a NotificationProvider');

      console.error = originalError;
    });
  });

  describe('addNotification', () => {
    it('should add notification to the store', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      const notification: NotificationCreateInput = {
        type: 'info',
        title: 'Test Notification',
        message: 'This is a test',
      };

      act(() => {
        result.current.addNotification(notification);
      });

      expect(result.current.notifications).toHaveLength(1);
      expect(result.current.notifications[0]).toMatchObject({
        type: 'info',
        title: 'Test Notification',
        message: 'This is a test',
      });
    });

    it('should generate unique id for each notification', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'First',
          message: 'First message',
        });
        result.current.addNotification({
          type: 'info',
          title: 'Second',
          message: 'Second message',
        });
      });

      const ids = result.current.notifications.map((n) => n.id);
      expect(ids[0]).not.toBe(ids[1]);
      expect(ids[0]).toMatch(/^\d+-[a-z0-9]+$/);
      expect(ids[1]).toMatch(/^\d+-[a-z0-9]+$/);
    });

    it('should generate timestamp for notification', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      const before = new Date();

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'Test',
          message: 'Test message',
        });
      });

      const after = new Date();
      const timestamp = result.current.notifications[0].timestamp;

      expect(timestamp).toBeInstanceOf(Date);
      expect(timestamp.getTime()).toBeGreaterThanOrEqual(before.getTime());
      expect(timestamp.getTime()).toBeLessThanOrEqual(after.getTime());
    });

    it('should add notification to front of array (newest first)', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'First',
          message: 'First message',
        });
        result.current.addNotification({
          type: 'info',
          title: 'Second',
          message: 'Second message',
        });
      });

      expect(result.current.notifications[0].title).toBe('Second');
      expect(result.current.notifications[1].title).toBe('First');
    });

    it('should default status to unread when not provided', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'Test',
          message: 'Test message',
        });
      });

      expect(result.current.notifications[0].status).toBe('unread');
    });

    it('should respect provided status', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'Test',
          message: 'Test message',
          status: 'read',
        });
      });

      expect(result.current.notifications[0].status).toBe('read');
    });

    it('should preserve details field', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      const details = {
        total: 3,
        succeeded: 2,
        failed: 1,
        artifacts: [
          { name: 'skill1', type: 'skill' as const, success: true },
          { name: 'skill2', type: 'skill' as const, success: true },
          { name: 'skill3', type: 'skill' as const, success: false, error: 'Failed' },
        ],
      };

      act(() => {
        result.current.addNotification({
          type: 'import',
          title: 'Import Results',
          message: 'Import completed',
          details,
        });
      });

      expect(result.current.notifications[0].details).toEqual(details);
    });

    it('should handle null details', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'Test',
          message: 'Test message',
          details: null,
        });
      });

      expect(result.current.notifications[0].details).toBeNull();
    });

    it('should handle undefined details', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'Test',
          message: 'Test message',
        });
      });

      expect(result.current.notifications[0].details).toBeUndefined();
    });
  });

  describe('markAsRead', () => {
    it('should mark specific notification as read', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'First',
          message: 'First message',
        });
        result.current.addNotification({
          type: 'info',
          title: 'Second',
          message: 'Second message',
        });
      });

      const idToMark = result.current.notifications[0].id;

      act(() => {
        result.current.markAsRead(idToMark);
      });

      expect(result.current.notifications[0].status).toBe('read');
      expect(result.current.notifications[1].status).toBe('unread');
    });

    it('should not affect other notifications', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'First',
          message: 'First message',
        });
        result.current.addNotification({
          type: 'info',
          title: 'Second',
          message: 'Second message',
        });
        result.current.addNotification({
          type: 'info',
          title: 'Third',
          message: 'Third message',
        });
      });

      const idToMark = result.current.notifications[1].id;

      act(() => {
        result.current.markAsRead(idToMark);
      });

      expect(result.current.notifications[0].status).toBe('unread');
      expect(result.current.notifications[1].status).toBe('read');
      expect(result.current.notifications[2].status).toBe('unread');
    });

    it('should do nothing for non-existent id', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'Test',
          message: 'Test message',
        });
      });

      const notificationsBefore = [...result.current.notifications];

      act(() => {
        result.current.markAsRead('non-existent-id');
      });

      expect(result.current.notifications).toEqual(notificationsBefore);
    });

    it('should not change notification that is already read', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'Test',
          message: 'Test message',
          status: 'read',
        });
      });

      const notificationId = result.current.notifications[0].id;
      const notificationBefore = result.current.notifications[0];

      act(() => {
        result.current.markAsRead(notificationId);
      });

      expect(result.current.notifications[0]).toEqual(notificationBefore);
    });
  });

  describe('markAllAsRead', () => {
    it('should mark all notifications as read', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'First',
          message: 'First message',
        });
        result.current.addNotification({
          type: 'info',
          title: 'Second',
          message: 'Second message',
        });
        result.current.addNotification({
          type: 'info',
          title: 'Third',
          message: 'Third message',
        });
      });

      expect(result.current.unreadCount).toBe(3);

      act(() => {
        result.current.markAllAsRead();
      });

      expect(result.current.notifications.every((n) => n.status === 'read')).toBe(true);
      expect(result.current.unreadCount).toBe(0);
    });

    it('should handle empty notifications array', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.markAllAsRead();
      });

      expect(result.current.notifications).toEqual([]);
      expect(result.current.unreadCount).toBe(0);
    });

    it('should handle mixed read/unread notifications', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'First',
          message: 'First message',
          status: 'read',
        });
        result.current.addNotification({
          type: 'info',
          title: 'Second',
          message: 'Second message',
        });
        result.current.addNotification({
          type: 'info',
          title: 'Third',
          message: 'Third message',
        });
      });

      expect(result.current.unreadCount).toBe(2);

      act(() => {
        result.current.markAllAsRead();
      });

      expect(result.current.notifications.every((n) => n.status === 'read')).toBe(true);
      expect(result.current.unreadCount).toBe(0);
    });
  });

  describe('dismissNotification', () => {
    it('should remove specific notification', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'First',
          message: 'First message',
        });
        result.current.addNotification({
          type: 'info',
          title: 'Second',
          message: 'Second message',
        });
      });

      const idToDismiss = result.current.notifications[0].id;

      act(() => {
        result.current.dismissNotification(idToDismiss);
      });

      expect(result.current.notifications).toHaveLength(1);
      expect(result.current.notifications[0].title).toBe('First');
    });

    it('should preserve other notifications', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'First',
          message: 'First message',
        });
        result.current.addNotification({
          type: 'info',
          title: 'Second',
          message: 'Second message',
        });
        result.current.addNotification({
          type: 'info',
          title: 'Third',
          message: 'Third message',
        });
      });

      const idToDismiss = result.current.notifications[1].id;

      act(() => {
        result.current.dismissNotification(idToDismiss);
      });

      expect(result.current.notifications).toHaveLength(2);
      expect(result.current.notifications[0].title).toBe('Third');
      expect(result.current.notifications[1].title).toBe('First');
    });

    it('should do nothing for non-existent id', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'Test',
          message: 'Test message',
        });
      });

      const lengthBefore = result.current.notifications.length;

      act(() => {
        result.current.dismissNotification('non-existent-id');
      });

      expect(result.current.notifications).toHaveLength(lengthBefore);
    });

    it('should update unreadCount when dismissing unread notification', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'First',
          message: 'First message',
        });
        result.current.addNotification({
          type: 'info',
          title: 'Second',
          message: 'Second message',
        });
      });

      expect(result.current.unreadCount).toBe(2);

      const idToDismiss = result.current.notifications[0].id;

      act(() => {
        result.current.dismissNotification(idToDismiss);
      });

      expect(result.current.unreadCount).toBe(1);
    });

    it('should not change unreadCount when dismissing read notification', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'First',
          message: 'First message',
          status: 'read',
        });
        result.current.addNotification({
          type: 'info',
          title: 'Second',
          message: 'Second message',
        });
      });

      expect(result.current.unreadCount).toBe(1);

      const idToDismiss = result.current.notifications[1].id;

      act(() => {
        result.current.dismissNotification(idToDismiss);
      });

      expect(result.current.unreadCount).toBe(1);
    });
  });

  describe('clearAll', () => {
    it('should clear all notifications', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'First',
          message: 'First message',
        });
        result.current.addNotification({
          type: 'info',
          title: 'Second',
          message: 'Second message',
        });
      });

      expect(result.current.notifications).toHaveLength(2);

      act(() => {
        result.current.clearAll();
      });

      expect(result.current.notifications).toEqual([]);
      expect(result.current.unreadCount).toBe(0);
    });

    it('should handle empty notifications array', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.clearAll();
      });

      expect(result.current.notifications).toEqual([]);
      expect(result.current.unreadCount).toBe(0);
    });
  });

  describe('FIFO Eviction', () => {
    it('should evict oldest notification when exceeding 50 limit', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      // Add 51 notifications
      act(() => {
        for (let i = 0; i < 51; i++) {
          result.current.addNotification({
            type: 'info',
            title: `Notification ${i}`,
            message: `Message ${i}`,
          });
        }
      });

      expect(result.current.notifications).toHaveLength(50);
      // Newest should be at index 0
      expect(result.current.notifications[0].title).toBe('Notification 50');
      // Oldest remaining should be at index 49
      expect(result.current.notifications[49].title).toBe('Notification 1');
      // Notification 0 should be evicted
      expect(
        result.current.notifications.find((n) => n.title === 'Notification 0')
      ).toBeUndefined();
    });

    it('should evict oldest read notification first', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      // Add 48 unread notifications
      act(() => {
        for (let i = 0; i < 48; i++) {
          result.current.addNotification({
            type: 'info',
            title: `Unread ${i}`,
            message: `Message ${i}`,
          });
        }
      });

      // Add 2 read notifications
      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'Read 0',
          message: 'Read message 0',
          status: 'read',
        });
        result.current.addNotification({
          type: 'info',
          title: 'Read 1',
          message: 'Read message 1',
          status: 'read',
        });
      });

      expect(result.current.notifications).toHaveLength(50);

      // Add one more notification to trigger eviction
      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'Trigger Eviction',
          message: 'This should evict oldest read',
        });
      });

      expect(result.current.notifications).toHaveLength(50);
      // Read 0 should be evicted (oldest read)
      expect(result.current.notifications.find((n) => n.title === 'Read 0')).toBeUndefined();
      // Read 1 should still exist
      expect(result.current.notifications.find((n) => n.title === 'Read 1')).toBeDefined();
      // All unread should be preserved
      expect(result.current.notifications.find((n) => n.title === 'Unread 0')).toBeDefined();
    });

    it('should evict oldest unread when all notifications are unread', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      // Add 51 unread notifications
      act(() => {
        for (let i = 0; i < 51; i++) {
          result.current.addNotification({
            type: 'info',
            title: `Unread ${i}`,
            message: `Message ${i}`,
          });
        }
      });

      expect(result.current.notifications).toHaveLength(50);
      // Oldest unread (Unread 0) should be evicted
      expect(result.current.notifications.find((n) => n.title === 'Unread 0')).toBeUndefined();
      // Newest unread should be at index 0
      expect(result.current.notifications[0].title).toBe('Unread 50');
      // Second oldest unread should be at index 49
      expect(result.current.notifications[49].title).toBe('Unread 1');
    });

    it('should evict multiple read notifications when needed', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      // Add 45 unread notifications
      act(() => {
        for (let i = 0; i < 45; i++) {
          result.current.addNotification({
            type: 'info',
            title: `Unread ${i}`,
            message: `Message ${i}`,
          });
        }
      });

      // Add 5 read notifications
      act(() => {
        for (let i = 0; i < 5; i++) {
          result.current.addNotification({
            type: 'info',
            title: `Read ${i}`,
            message: `Read message ${i}`,
            status: 'read',
          });
        }
      });

      expect(result.current.notifications).toHaveLength(50);

      // Add 3 more notifications to trigger multiple evictions
      act(() => {
        for (let i = 0; i < 3; i++) {
          result.current.addNotification({
            type: 'info',
            title: `Trigger ${i}`,
            message: `Trigger message ${i}`,
          });
        }
      });

      expect(result.current.notifications).toHaveLength(50);
      // Read 0, 1, 2 should be evicted (3 oldest read)
      expect(result.current.notifications.find((n) => n.title === 'Read 0')).toBeUndefined();
      expect(result.current.notifications.find((n) => n.title === 'Read 1')).toBeUndefined();
      expect(result.current.notifications.find((n) => n.title === 'Read 2')).toBeUndefined();
      // Read 3, 4 should still exist
      expect(result.current.notifications.find((n) => n.title === 'Read 3')).toBeDefined();
      expect(result.current.notifications.find((n) => n.title === 'Read 4')).toBeDefined();
    });
  });

  describe('localStorage Persistence', () => {
    it('should save notifications to localStorage on change', async () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'Test',
          message: 'Test message',
        });
      });

      await waitFor(() => {
        expect(localStorageMock.setItem).toHaveBeenCalledWith(
          'skillmeat-notifications',
          expect.any(String)
        );
      });

      const savedData = JSON.parse(
        localStorageMock.setItem.mock.calls[localStorageMock.setItem.mock.calls.length - 1][1]
      );
      expect(savedData).toHaveLength(1);
      expect(savedData[0].title).toBe('Test');
    });

    it('should load notifications from localStorage on mount', () => {
      const storedNotifications: NotificationData[] = [
        {
          id: '1',
          type: 'info',
          title: 'Stored Notification',
          message: 'This was stored',
          timestamp: new Date('2024-01-01T00:00:00Z'),
          status: 'unread',
        },
      ];

      localStorageMock.setItem('skillmeat-notifications', JSON.stringify(storedNotifications));

      const { result } = renderHook(() => useNotifications(), { wrapper });

      expect(result.current.notifications).toHaveLength(1);
      expect(result.current.notifications[0].title).toBe('Stored Notification');
    });

    it('should deserialize timestamp as Date object', () => {
      const storedNotifications = [
        {
          id: '1',
          type: 'info',
          title: 'Test',
          message: 'Test message',
          timestamp: '2024-01-01T00:00:00Z',
          status: 'unread',
        },
      ];

      localStorageMock.setItem('skillmeat-notifications', JSON.stringify(storedNotifications));

      const { result } = renderHook(() => useNotifications(), { wrapper });

      expect(result.current.notifications[0].timestamp).toBeInstanceOf(Date);
      expect(result.current.notifications[0].timestamp.toISOString()).toBe(
        '2024-01-01T00:00:00.000Z'
      );
    });

    it('should handle corrupted localStorage data gracefully', () => {
      localStorageMock.setItem('skillmeat-notifications', 'invalid json');

      const { result } = renderHook(() => useNotifications(), { wrapper });

      expect(result.current.notifications).toEqual([]);
      expect(result.current.unreadCount).toBe(0);
    });

    it('should handle missing localStorage data', () => {
      localStorageMock.clear();

      const { result } = renderHook(() => useNotifications(), { wrapper });

      expect(result.current.notifications).toEqual([]);
      expect(result.current.unreadCount).toBe(0);
    });

    it('should handle localStorage setItem errors gracefully', async () => {
      const consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
      localStorageMock.setItem.mockImplementationOnce(() => {
        throw new Error('QuotaExceededError');
      });

      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'Test',
          message: 'Test message',
        });
      });

      await waitFor(() => {
        expect(consoleWarnSpy).toHaveBeenCalledWith(
          'Failed to save notifications to localStorage:',
          expect.any(Error)
        );
      });

      consoleWarnSpy.mockRestore();
    });

    it('should persist details field in localStorage', async () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      const details = {
        total: 2,
        succeeded: 1,
        failed: 1,
        artifacts: [
          { name: 'skill1', type: 'skill' as const, success: true },
          { name: 'skill2', type: 'skill' as const, success: false, error: 'Error' },
        ],
      };

      act(() => {
        result.current.addNotification({
          type: 'import',
          title: 'Import Results',
          message: 'Import completed',
          details,
        });
      });

      await waitFor(() => {
        expect(localStorageMock.setItem).toHaveBeenCalled();
      });

      const savedData = JSON.parse(
        localStorageMock.setItem.mock.calls[localStorageMock.setItem.mock.calls.length - 1][1]
      );
      expect(savedData[0].details).toEqual(details);
    });
  });

  describe('unreadCount Computation', () => {
    it('should compute correct unreadCount', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'Unread 1',
          message: 'Message 1',
        });
        result.current.addNotification({
          type: 'info',
          title: 'Unread 2',
          message: 'Message 2',
        });
        result.current.addNotification({
          type: 'info',
          title: 'Read 1',
          message: 'Message 3',
          status: 'read',
        });
      });

      expect(result.current.unreadCount).toBe(2);
    });

    it('should update unreadCount when marking as read', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'Test 1',
          message: 'Message 1',
        });
        result.current.addNotification({
          type: 'info',
          title: 'Test 2',
          message: 'Message 2',
        });
      });

      expect(result.current.unreadCount).toBe(2);

      const idToMark = result.current.notifications[0].id;

      act(() => {
        result.current.markAsRead(idToMark);
      });

      expect(result.current.unreadCount).toBe(1);
    });

    it('should set unreadCount to 0 when marking all as read', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'Test 1',
          message: 'Message 1',
        });
        result.current.addNotification({
          type: 'info',
          title: 'Test 2',
          message: 'Message 2',
        });
      });

      expect(result.current.unreadCount).toBe(2);

      act(() => {
        result.current.markAllAsRead();
      });

      expect(result.current.unreadCount).toBe(0);
    });

    it('should update unreadCount when dismissing unread notification', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'Test 1',
          message: 'Message 1',
        });
        result.current.addNotification({
          type: 'info',
          title: 'Test 2',
          message: 'Message 2',
        });
      });

      expect(result.current.unreadCount).toBe(2);

      const idToDismiss = result.current.notifications[0].id;

      act(() => {
        result.current.dismissNotification(idToDismiss);
      });

      expect(result.current.unreadCount).toBe(1);
    });

    it('should set unreadCount to 0 when clearing all', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'Test 1',
          message: 'Message 1',
        });
        result.current.addNotification({
          type: 'info',
          title: 'Test 2',
          message: 'Message 2',
        });
      });

      expect(result.current.unreadCount).toBe(2);

      act(() => {
        result.current.clearAll();
      });

      expect(result.current.unreadCount).toBe(0);
    });

    it('should correctly count unread after adding new notification', () => {
      const { result } = renderHook(() => useNotifications(), { wrapper });

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'Test 1',
          message: 'Message 1',
          status: 'read',
        });
      });

      expect(result.current.unreadCount).toBe(0);

      act(() => {
        result.current.addNotification({
          type: 'info',
          title: 'Test 2',
          message: 'Message 2',
        });
      });

      expect(result.current.unreadCount).toBe(1);
    });
  });
});
