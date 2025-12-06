'use client';

import * as React from 'react';
import type {
  NotificationData,
  NotificationCreateInput,
  NotificationStoreState,
  NotificationStoreActions,
} from '@/types/notification';

/**
 * Maximum number of notifications to keep in memory
 * Oldest notifications are removed when limit is exceeded (FIFO)
 */
const MAX_NOTIFICATIONS = 50;

/**
 * localStorage key for persisting notifications
 */
const STORAGE_KEY = 'skillmeat-notifications';

/**
 * Notification store context
 * Provides notifications state and actions to manage them
 */
const NotificationContext = React.createContext<{
  state: NotificationStoreState;
  actions: NotificationStoreActions;
} | null>(null);

/**
 * Generate a unique ID for a notification
 * Format: timestamp-randomhash
 */
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(7)}`;
}

/**
 * Safely load notifications from localStorage
 * Handles SSR, parsing errors, and date deserialization
 *
 * @returns Stored notifications or null if unavailable/error
 */
function getStorageItem(): NotificationData[] | null {
  try {
    if (typeof window === 'undefined') return null;
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return null;
    const parsed = JSON.parse(stored);
    // Convert ISO strings back to Date objects
    return parsed.map((n: any) => ({
      ...n,
      timestamp: new Date(n.timestamp),
    }));
  } catch {
    return null;
  }
}

/**
 * Safely save notifications to localStorage
 * Handles SSR, quota exceeded, and serialization errors
 *
 * @param notifications - Notifications to save
 */
function setStorageItem(notifications: NotificationData[]): void {
  try {
    if (typeof window === 'undefined') return;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(notifications));
  } catch (e) {
    console.warn('Failed to save notifications to localStorage:', e);
  }
}

/**
 * Smart FIFO eviction - prioritizes keeping unread notifications
 *
 * When notifications exceed MAX_NOTIFICATIONS:
 * 1. First try to evict read notifications (oldest first)
 * 2. If all unread, evict oldest unread
 *
 * @param notifications - Current notifications
 * @returns Evicted notifications (max MAX_NOTIFICATIONS)
 */
function evictOldest(notifications: NotificationData[]): NotificationData[] {
  if (notifications.length <= MAX_NOTIFICATIONS) return notifications;

  // Separate read and unread
  const unread = notifications.filter((n) => n.status === 'unread');
  const read = notifications.filter((n) => n.status === 'read');

  // If we have read notifications, remove oldest read first
  if (read.length > 0) {
    // Remove oldest read notifications until under limit
    const toRemove = notifications.length - MAX_NOTIFICATIONS;
    const sortedRead = [...read].sort(
      (a, b) => a.timestamp.getTime() - b.timestamp.getTime()
    );
    const idsToRemove = new Set(sortedRead.slice(0, toRemove).map((n) => n.id));
    return notifications.filter((n) => !idsToRemove.has(n.id));
  }

  // All unread - remove oldest
  return notifications.slice(0, MAX_NOTIFICATIONS);
}

/**
 * NotificationProvider component
 * Manages notification state using React Context + hooks pattern
 *
 * Usage:
 * ```tsx
 * <NotificationProvider>
 *   <App />
 * </NotificationProvider>
 * ```
 */
export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [notifications, setNotifications] = React.useState<NotificationData[]>([]);

  /**
   * Add a new notification to the store
   * - Generates unique ID and timestamp
   * - Adds to front of array (newest first)
   * - Uses smart eviction (prioritizes keeping unread)
   * - Defaults status to 'unread' if not provided
   */
  const addNotification = React.useCallback((input: NotificationCreateInput) => {
    setNotifications((prev) => {
      const newNotification: NotificationData = {
        ...input,
        id: generateId(),
        timestamp: new Date(),
        status: input.status ?? 'unread',
      };

      // Add to front, apply smart eviction
      const updated = [newNotification, ...prev];
      return evictOldest(updated);
    });
  }, []);

  /**
   * Mark a specific notification as read
   */
  const markAsRead = React.useCallback((id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, status: 'read' as const } : n))
    );
  }, []);

  /**
   * Mark all notifications as read
   */
  const markAllAsRead = React.useCallback(() => {
    setNotifications((prev) =>
      prev.map((n) => ({ ...n, status: 'read' as const }))
    );
  }, []);

  /**
   * Remove a specific notification
   */
  const dismissNotification = React.useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  /**
   * Clear all notifications
   */
  const clearAll = React.useCallback(() => {
    setNotifications([]);
  }, []);

  /**
   * Load notifications from localStorage on mount
   */
  React.useEffect(() => {
    const stored = getStorageItem();
    if (stored && stored.length > 0) {
      setNotifications(stored);
    }
  }, []);

  /**
   * Save notifications to localStorage whenever they change
   */
  React.useEffect(() => {
    setStorageItem(notifications);
  }, [notifications]);

  /**
   * Compute unread count as derived state
   * Automatically updates when notifications change
   */
  const unreadCount = React.useMemo(
    () => notifications.filter((n) => n.status === 'unread').length,
    [notifications]
  );

  // Combine state and actions
  const state: NotificationStoreState = {
    notifications, // Already sorted by timestamp (newest first)
    unreadCount,
  };

  const actions: NotificationStoreActions = {
    addNotification,
    markAsRead,
    markAllAsRead,
    dismissNotification,
    clearAll,
  };

  return (
    <NotificationContext.Provider value={{ state, actions }}>
      {children}
    </NotificationContext.Provider>
  );
}

/**
 * Hook to access notification store
 *
 * Returns combined state and actions:
 * - notifications: NotificationData[] (newest first)
 * - unreadCount: number
 * - addNotification: (notification: NotificationCreateInput) => void
 * - markAsRead: (id: string) => void
 * - markAllAsRead: () => void
 * - dismissNotification: (id: string) => void
 * - clearAll: () => void
 *
 * Usage:
 * ```tsx
 * function MyComponent() {
 *   const { notifications, unreadCount, addNotification } = useNotifications();
 *   // ...
 * }
 * ```
 *
 * @throws {Error} If used outside NotificationProvider
 */
export function useNotifications() {
  const context = React.useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return { ...context.state, ...context.actions };
}
