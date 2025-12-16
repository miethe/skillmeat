'use client';

import { useNotifications } from '@/lib/notification-store';
import { NotificationBell } from '@/components/notifications/NotificationCenter';

export function Header() {
  const {
    notifications,
    unreadCount,
    markAsRead,
    markAllAsRead,
    dismissNotification,
    clearAll,
  } = useNotifications();
  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center">
        <div className="flex flex-1 items-center justify-between space-x-2">
          <h1 className="text-xl font-bold tracking-tight">Dashboard</h1>
          <div className="flex items-center gap-4 text-sm font-medium">
            <NotificationBell
              unreadCount={unreadCount}
              notifications={notifications}
              onMarkAllRead={markAllAsRead}
              onClearAll={clearAll}
              onNotificationClick={markAsRead}
              onDismiss={dismissNotification}
            />
          </div>
        </div>
      </div>
    </header>
  );
}
