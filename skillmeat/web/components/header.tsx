'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useNotifications } from '@/lib/notification-store';
import { NotificationBell } from '@/components/notifications/NotificationCenter';

export function Header() {
  const { notifications, unreadCount, markAsRead, markAllAsRead, dismissNotification, clearAll } =
    useNotifications();
  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2">
          <Image
            src="/logo.svg"
            alt="SkillMeat Logo"
            width={32}
            height={32}
            className="h-8 w-auto"
          />
          <span className="font-bold">SkillMeat</span>
        </Link>
        <NotificationBell
          unreadCount={unreadCount}
          notifications={notifications}
          onMarkAllRead={markAllAsRead}
          onClearAll={clearAll}
          onNotificationClick={markAsRead}
          onDismiss={dismissNotification}
        />
      </div>
    </header>
  );
}
