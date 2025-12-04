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
import type {
  NotificationData,
  NotificationType,
  ImportResultDetails,
  ErrorDetails,
  GenericDetails,
} from '@/types/notification';

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
                <NotificationDetailView details={notification.details} />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Type Guard Functions
// ============================================================================

function isImportResultDetails(details: unknown): details is ImportResultDetails {
  return (
    details !== null &&
    typeof details === 'object' &&
    'artifacts' in details &&
    'total' in details &&
    'succeeded' in details &&
    'failed' in details
  );
}

function isErrorDetails(details: unknown): details is ErrorDetails {
  return (
    details !== null &&
    typeof details === 'object' &&
    'message' in details &&
    !('artifacts' in details)
  );
}

function isGenericDetails(details: unknown): details is GenericDetails {
  return (
    details !== null &&
    typeof details === 'object' &&
    'metadata' in details
  );
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Sanitize error messages to prevent XSS and improve readability
 * - Removes/escapes HTML tags
 * - Truncates to max 200 characters
 * - Handles null/undefined gracefully
 */
function sanitizeErrorMessage(message: string | null | undefined): string {
  if (!message) return 'Unknown error';

  // Remove HTML tags
  const stripped = message.replace(/<[^>]*>/g, '');

  // Truncate if too long
  if (stripped.length > 200) {
    return stripped.substring(0, 197) + '...';
  }

  return stripped;
}

// ============================================================================
// NotificationDetailView Component (Router)
// ============================================================================

interface NotificationDetailViewProps {
  details: ImportResultDetails | ErrorDetails | GenericDetails;
}

function NotificationDetailView({ details }: NotificationDetailViewProps) {
  if (isImportResultDetails(details)) {
    return <ImportResultDetails details={details} />;
  }

  if (isErrorDetails(details)) {
    return <ErrorDetail details={details} />;
  }

  if (isGenericDetails(details)) {
    return <GenericDetail details={details} />;
  }

  return null;
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
            className={cn(
              'flex items-start gap-2 rounded px-2 py-1.5 text-xs transition-colors',
              'hover:bg-background/80 dark:hover:bg-background/40'
            )}
          >
            {/* Status icon */}
            {artifact.success ? (
              <CheckCircle2 className="h-3.5 w-3.5 text-green-500 flex-shrink-0 mt-0.5" />
            ) : (
              <XCircle className="h-3.5 w-3.5 text-red-500 flex-shrink-0 mt-0.5" />
            )}

            {/* Artifact info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
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
                  {sanitizeErrorMessage(artifact.error)}
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
// ErrorDetail Component
// ============================================================================

interface ErrorDetailProps {
  details: ErrorDetails;
  onRetry?: () => void;
}

function ErrorDetail({ details, onRetry }: ErrorDetailProps) {
  const [showStack, setShowStack] = React.useState(false);

  return (
    <div className="mt-3 space-y-3 rounded-md border border-red-200 dark:border-red-900 bg-red-50/50 dark:bg-red-950/20 p-3">
      {/* Error code and message */}
      <div className="space-y-2">
        {details.code && (
          <div className="flex items-center gap-2">
            <Badge variant="destructive" className="h-5 px-2 text-xs font-mono">
              {details.code}
            </Badge>
          </div>
        )}
        <p className="text-sm font-medium text-red-900 dark:text-red-200">
          {sanitizeErrorMessage(details.message)}
        </p>
      </div>

      {/* Stack trace (collapsible) */}
      {details.stack && (
        <div className="space-y-1">
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-xs text-red-700 dark:text-red-300 hover:text-red-900 dark:hover:text-red-100"
            onClick={() => setShowStack(!showStack)}
          >
            {showStack ? (
              <>
                <ChevronUp className="h-3 w-3 mr-1" />
                Hide stack trace
              </>
            ) : (
              <>
                <ChevronDown className="h-3 w-3 mr-1" />
                Show stack trace
              </>
            )}
          </Button>
          {showStack && (
            <pre className="mt-2 rounded bg-red-100/50 dark:bg-red-950/50 p-2 text-[10px] font-mono text-red-900 dark:text-red-200 overflow-x-auto max-h-32 overflow-y-auto">
              {details.stack}
            </pre>
          )}
        </div>
      )}

      {/* Retry button */}
      {details.retryable && onRetry && (
        <Button
          variant="outline"
          size="sm"
          className="h-7 text-xs border-red-300 dark:border-red-800 text-red-700 dark:text-red-300 hover:bg-red-100 dark:hover:bg-red-950/40"
          onClick={onRetry}
        >
          <RefreshCw className="h-3 w-3 mr-1" />
          Retry
        </Button>
      )}
    </div>
  );
}

// ============================================================================
// GenericDetail Component
// ============================================================================

interface GenericDetailProps {
  details: GenericDetails;
}

function GenericDetail({ details }: GenericDetailProps) {
  if (!details.metadata || Object.keys(details.metadata).length === 0) {
    return null;
  }

  return (
    <div className="mt-3 space-y-2 rounded-md border bg-muted/30 p-3">
      <div className="space-y-1.5">
        {Object.entries(details.metadata).map(([key, value]) => (
          <div
            key={key}
            className="flex items-start gap-2 text-xs rounded px-2 py-1.5 hover:bg-background/60 dark:hover:bg-background/40 transition-colors"
          >
            <span className="font-medium text-muted-foreground min-w-[80px]">
              {key}:
            </span>
            <span className="flex-1 break-words">
              {typeof value === 'boolean' ? (value ? 'Yes' : 'No') : String(value)}
            </span>
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

