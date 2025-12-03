'use client';

import Link from 'next/link';
import { Package2 } from 'lucide-react';
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
        <div className="mr-4 flex">
          <Link href="/" className="mr-6 flex items-center space-x-2">
            <Package2 className="h-6 w-6" />
            <span className="font-bold">SkillMeat</span>
          </Link>
        </div>
        <div className="flex flex-1 items-center justify-between space-x-2 md:justify-end">
          <nav className="flex items-center space-x-6 text-sm font-medium">
            <NotificationBell
              unreadCount={unreadCount}
              notifications={notifications}
              onMarkAllRead={markAllAsRead}
              onClearAll={clearAll}
              onNotificationClick={markAsRead}
              onDismiss={dismissNotification}
            />
            <Link
              href="https://github.com/miethe/skillmeat"
              target="_blank"
              rel="noreferrer"
              className="text-foreground/60 transition-colors hover:text-foreground/80"
            >
              GitHub
            </Link>
            <Link
              href="https://github.com/miethe/skillmeat#readme"
              target="_blank"
              rel="noreferrer"
              className="text-foreground/60 transition-colors hover:text-foreground/80"
            >
              Documentation
            </Link>
          </nav>
        </div>
      </div>
    </header>
  );
}
