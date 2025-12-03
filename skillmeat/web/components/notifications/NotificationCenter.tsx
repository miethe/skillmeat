'use client';

import * as React from 'react';
import {
  Bell,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Info,
  Download,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import { formatDistanceToNow } from 'date-fns';

// ============================================================================
// Types
// ============================================================================

export type NotificationType = 'import' | 'sync' | 'error' | 'info' | 'success';
export type NotificationStatus = 'read' | 'unread';

export interface NotificationData {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  timestamp: Date;
  status: NotificationStatus;
  details?: ImportResultDetails | null;
}

export interface ImportResultDetails {
  total: number;
  succeeded: number;
  failed: number;
  artifacts: ArtifactImportResult[];
}

export interface ArtifactImportResult {
  name: string;
  type: 'skill' | 'command' | 'agent' | 'mcp' | 'hook';
  success: boolean;
  error?: string;
}

// ============================================================================
// NotificationBell Component
// ============================================================================

interface NotificationBellProps {
  unreadCount: number;
  notifications: NotificationData[];
  onMarkAllRead: () => void;
  onClearAll: () => void;
  onNotificationClick: (id: string) => void;
  onDismiss: (id: string) => void;
}

export function NotificationBell({
  unreadCount,
  notifications,
  onMarkAllRead,
  onClearAll,
  onNotificationClick,
  onDismiss,
}: NotificationBellProps) {
  const [open, setOpen] = React.useState(false);

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative"
          aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ''}`}
        >
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <Badge
              variant="destructive"
              className="absolute -right-1 -top-1 flex h-5 min-w-[20px] items-center justify-center rounded-full px-1 text-[10px] font-bold animate-in fade-in zoom-in"
            >
              {unreadCount > 99 ? '99+' : unreadCount}
            </Badge>
          )}
          <span className="sr-only">
            {unreadCount > 0 ? `${unreadCount} unread notifications` : 'No unread notifications'}
          </span>
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent
        align="end"
        className="w-[420px] p-0"
        sideOffset={8}
        onCloseAutoFocus={(e) => e.preventDefault()}
      >
        <NotificationDropdown
          notifications={notifications}
          onMarkAllRead={onMarkAllRead}
          onClearAll={onClearAll}
          onNotificationClick={onNotificationClick}
          onDismiss={onDismiss}
          onClose={() => setOpen(false)}
        />
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// ============================================================================
// NotificationDropdown Component
// ============================================================================

interface NotificationDropdownProps {
  notifications: NotificationData[];
  onMarkAllRead: () => void;
  onClearAll: () => void;
  onNotificationClick: (id: string) => void;
  onDismiss: (id: string) => void;
  onClose: () => void;
}

function NotificationDropdown({
  notifications,
  onMarkAllRead,
  onClearAll,
  onNotificationClick,
  onDismiss,
  onClose,
}: NotificationDropdownProps) {
  const hasNotifications = notifications.length > 0;
  const hasUnread = notifications.some((n) => n.status === 'unread');

  return (
    <div className="flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-4 py-3">
        <DropdownMenuLabel className="p-0 text-base font-semibold">
          Notifications
        </DropdownMenuLabel>
        <div className="flex items-center gap-2">
          {hasUnread && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs"
              onClick={(e) => {
                e.stopPropagation();
                onMarkAllRead();
              }}
            >
              Mark all read
            </Button>
          )}
          {hasNotifications && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs text-muted-foreground hover:text-foreground"
              onClick={(e) => {
                e.stopPropagation();
                onClearAll();
              }}
            >
              Clear all
            </Button>
          )}
        </div>
      </div>

      {/* Notification List */}
      {hasNotifications ? (
        <ScrollArea className="max-h-[500px]">
          <div className="divide-y">
            {notifications.map((notification) => (
              <NotificationItem
                key={notification.id}
                notification={notification}
                onClick={() => {
                  onNotificationClick(notification.id);
                  onClose();
                }}
                onDismiss={(e) => {
                  e.stopPropagation();
                  onDismiss(notification.id);
                }}
              />
            ))}
          </div>
        </ScrollArea>
      ) : (
        <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
          <Bell className="h-12 w-12 text-muted-foreground/40 mb-3" />
          <p className="text-sm font-medium text-muted-foreground">No notifications</p>
          <p className="text-xs text-muted-foreground/60 mt-1">
            You'll see updates about imports, syncs, and errors here
          </p>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// NotificationItem Component
// ============================================================================

interface NotificationItemProps {
  notification: NotificationData;
  onClick: () => void;
  onDismiss: (e: React.MouseEvent) => void;
}

function NotificationItem({ notification, onClick, onDismiss }: NotificationItemProps) {
  const [expanded, setExpanded] = React.useState(false);
  const isUnread = notification.status === 'unread';
  const hasDetails = notification.details != null;

  const icon = getNotificationIcon(notification.type);
  const iconColor = getNotificationIconColor(notification.type);

  const handleToggleExpand = (e: React.MouseEvent) => {
    e.stopPropagation();
    setExpanded(!expanded);
  };

  return (
    <div
      className={cn(
        'relative px-4 py-3 transition-colors cursor-pointer hover:bg-accent/50',
        isUnread && 'bg-accent/30'
      )}
      onClick={onClick}
    >
      {/* Unread indicator */}
      {isUnread && (
        <div className="absolute left-0 top-0 bottom-0 w-1 bg-primary" aria-hidden="true" />
      )}

      <div className="flex gap-3">
        {/* Icon */}
        <div className={cn('mt-0.5 flex-shrink-0', iconColor)}>{icon}</div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium leading-tight">{notification.title}</p>
              <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                {notification.message}
              </p>
              <p className="text-xs text-muted-foreground/70 mt-1.5">
                {formatDistanceToNow(notification.timestamp, { addSuffix: true })}
              </p>
            </div>

            {/* Dismiss button */}
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 flex-shrink-0 opacity-0 group-hover:opacity-100 hover:bg-background/80"
              onClick={onDismiss}
              aria-label="Dismiss notification"
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>

          {/* Expandable details */}
          {hasDetails && (
            <div className="mt-2">
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2 text-xs"
                onClick={handleToggleExpand}
              >
                {expanded ? (
                  <>
                    <ChevronUp className="h-3.5 w-3.5 mr-1" />
                    Hide details
                  </>
                ) : (
                  <>
                    <ChevronDown className="h-3.5 w-3.5 mr-1" />
                    Show details
                  </>
                )}
              </Button>

              {expanded && notification.details && (
                <ImportResultDetails details={notification.details} />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// ImportResultDetails Component
// ============================================================================

interface ImportResultDetailsProps {
  details: ImportResultDetails;
}

function ImportResultDetails({ details }: ImportResultDetailsProps) {
  return (
    <div className="mt-3 space-y-3 rounded-md border bg-muted/30 p-3">
      {/* Summary */}
      <div className="flex items-center gap-4 text-xs">
        <div className="flex items-center gap-1.5">
          <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
          <span className="font-medium">{details.succeeded} succeeded</span>
        </div>
        <div className="flex items-center gap-1.5">
          <XCircle className="h-3.5 w-3.5 text-red-500" />
          <span className="font-medium">{details.failed} failed</span>
        </div>
        <div className="text-muted-foreground">
          Total: {details.total}
        </div>
      </div>

      {/* Artifact list */}
      <div className="space-y-1.5 max-h-[200px] overflow-y-auto">
        {details.artifacts.map((artifact, index) => (
          <div
            key={`${artifact.name}-${index}`}
            className="flex items-start gap-2 rounded px-2 py-1.5 text-xs hover:bg-background/60"
          >
            {/* Status icon */}
            {artifact.success ? (
              <CheckCircle2 className="h-3.5 w-3.5 text-green-500 flex-shrink-0 mt-0.5" />
            ) : (
              <XCircle className="h-3.5 w-3.5 text-red-500 flex-shrink-0 mt-0.5" />
            )}

            {/* Artifact info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <Badge
                  variant="outline"
                  className="h-4 px-1 text-[10px] font-medium"
                >
                  {artifact.type}
                </Badge>
                <span className="font-medium truncate">{artifact.name}</span>
              </div>
              {!artifact.success && artifact.error && (
                <p className="text-muted-foreground mt-0.5 line-clamp-2">
                  {artifact.error}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Helper Functions
// ============================================================================

function getNotificationIcon(type: NotificationType): React.ReactNode {
  switch (type) {
    case 'import':
      return <Download className="h-4 w-4" />;
    case 'sync':
      return <RefreshCw className="h-4 w-4" />;
    case 'error':
      return <XCircle className="h-4 w-4" />;
    case 'success':
      return <CheckCircle2 className="h-4 w-4" />;
    case 'info':
      return <Info className="h-4 w-4" />;
    default:
      return <Bell className="h-4 w-4" />;
  }
}

function getNotificationIconColor(type: NotificationType): string {
  switch (type) {
    case 'import':
      return 'text-blue-500';
    case 'sync':
      return 'text-teal-500';
    case 'error':
      return 'text-red-500';
    case 'success':
      return 'text-green-500';
    case 'info':
      return 'text-muted-foreground';
    default:
      return 'text-muted-foreground';
  }
}

// ============================================================================
// Example Usage Hook (for reference)
// ============================================================================

/**
 * Example hook for managing notifications
 *
 * Usage:
 * ```tsx
 * const { notifications, unreadCount, markAsRead, markAllAsRead, clearAll, addNotification, dismissNotification } = useNotifications();
 *
 * return (
 *   <NotificationBell
 *     unreadCount={unreadCount}
 *     notifications={notifications}
 *     onMarkAllRead={markAllAsRead}
 *     onClearAll={clearAll}
 *     onNotificationClick={markAsRead}
 *     onDismiss={dismissNotification}
 *   />
 * );
 * ```
 */
export function useNotifications() {
  const [notifications, setNotifications] = React.useState<NotificationData[]>([]);

  const addNotification = React.useCallback((notification: Omit<NotificationData, 'id'>) => {
    setNotifications((prev) => [
      {
        ...notification,
        id: Math.random().toString(36).substring(7),
      },
      ...prev,
    ].slice(0, 50)); // Keep max 50 notifications
  }, []);

  const markAsRead = React.useCallback((id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, status: 'read' as const } : n))
    );
  }, []);

  const markAllAsRead = React.useCallback(() => {
    setNotifications((prev) =>
      prev.map((n) => ({ ...n, status: 'read' as const }))
    );
  }, []);

  const clearAll = React.useCallback(() => {
    setNotifications([]);
  }, []);

  const dismissNotification = React.useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const unreadCount = React.useMemo(
    () => notifications.filter((n) => n.status === 'unread').length,
    [notifications]
  );

  return {
    notifications,
    unreadCount,
    markAsRead,
    markAllAsRead,
    clearAll,
    addNotification,
    dismissNotification,
  };
}
