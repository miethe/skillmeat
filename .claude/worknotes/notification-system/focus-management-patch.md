# Focus Management Implementation Patch

## Status: Partial Implementation

**What's Done**:
- ✅ `/skillmeat/web/hooks/useFocusTrap.ts` - Created and working
- ⚠️ `/skillmeat/web/components/notifications/NotificationCenter.tsx` - Needs manual updates

**Issue**: The NotificationCenter.tsx file appears to have been modified by a linter or auto-formatter after the changes were applied. The hook was created successfully but the component integration needs to be completed manually.

## Required Manual Changes

### 1. Add Import (Line ~28, after formatDistanceToNow import)

```typescript
import { formatDistanceToNow } from 'date-fns';
import { useFocusTrap } from '@/hooks/useFocusTrap';  // ADD THIS LINE
import type {
```

### 2. Update NotificationBell Component (~Line 87-150)

**Find this section**:
```typescript
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
```

**Replace with**:
```typescript
export function NotificationBell({
  unreadCount,
  notifications,
  onMarkAllRead,
  onClearAll,
  onNotificationClick,
  onDismiss,
}: NotificationBellProps) {
  const [open, setOpen] = React.useState(false);
  const triggerRef = React.useRef<HTMLButtonElement>(null);

  // Restore focus to trigger when dropdown closes
  const handleOpenChange = (isOpen: boolean) => {
    setOpen(isOpen);
    if (!isOpen && triggerRef.current) {
      // Delay to ensure dropdown close animation completes
      setTimeout(() => {
        triggerRef.current?.focus();
      }, 0);
    }
  };

  return (
    <>
      <NotificationAnnouncer notifications={notifications} />
      <DropdownMenu open={open} onOpenChange={handleOpenChange}>
```

**And update the Button component** (add ref and focus classes):
```typescript
<Button
  ref={triggerRef}  // ADD THIS
  variant="ghost"
  size="icon"
  className="relative focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"  // UPDATE THIS
  aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ''}`}
>
```

**And update DropdownMenuContent onCloseAutoFocus**:
```typescript
<DropdownMenuContent
  align="end"
  className={cn(
    "w-full sm:w-[380px] p-0",
    "max-h-[80vh] sm:max-h-[500px]",
    "transform transition-all duration-200 ease-out",
    "data-[state=open]:animate-in data-[state=closed]:animate-out",
    "data-[state=open]:fade-in-0 data-[state=open]:slide-in-from-top-2",
    "data-[state=closed]:fade-out-0 data-[state=closed]:slide-out-to-top-2",
    "motion-reduce:transition-none motion-reduce:animate-none"
  )}
  sideOffset={8}
  onCloseAutoFocus={(e) => {
    // Prevent default to manually control focus restoration
    e.preventDefault();
  }}
>
  <NotificationDropdown
    notifications={notifications}
    onMarkAllRead={onMarkAllRead}
    onClearAll={onClearAll}
    onNotificationClick={onNotificationClick}
    onDismiss={onDismiss}
    onClose={() => setOpen(false)}
    isOpen={open}  // ADD THIS PROP
  />
</DropdownMenuContent>
</DropdownMenu>
</>  // ADD THIS (closing the fragment)
```

### 3. Update NotificationDropdown Interface and Component (~Line 152-244)

**Update the interface**:
```typescript
interface NotificationDropdownProps {
  notifications: NotificationData[];
  onMarkAllRead: () => void;
  onClearAll: () => void;
  onNotificationClick: (id: string) => void;
  onDismiss: (id: string) => void;
  onClose: () => void;
  isOpen: boolean;  // ADD THIS
}
```

**Update the component**:
```typescript
function NotificationDropdown({
  notifications,
  onMarkAllRead,
  onClearAll,
  onNotificationClick,
  onDismiss,
  onClose,
  isOpen,  // ADD THIS
}: NotificationDropdownProps) {
  const hasNotifications = notifications.length > 0;
  const hasUnread = notifications.some((n) => n.status === 'unread');
  const containerRef = useFocusTrap(isOpen);  // ADD THIS
  const itemRefs = React.useRef<Map<string, HTMLDivElement>>(new Map());  // ADD THIS

  // ADD THIS ENTIRE FUNCTION
  // Enhanced dismiss handler with focus management
  const handleDismiss = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const currentIndex = notifications.findIndex(n => n.id === id);

    // Dismiss the notification
    onDismiss(id);

    // Manage focus after dismiss
    requestAnimationFrame(() => {
      const remainingNotifications = notifications.filter(n => n.id !== id);

      if (remainingNotifications.length === 0) {
        // No notifications left, focus on close button or header
        const closeButton = containerRef.current?.querySelector('button[aria-label*="Clear"]') as HTMLElement;
        closeButton?.focus();
      } else {
        // Focus on next notification, or previous if dismissed was last
        const nextIndex = Math.min(currentIndex, remainingNotifications.length - 1);
        const nextId = remainingNotifications[nextIndex]?.id;
        const nextElement = itemRefs.current.get(nextId);

        if (nextElement) {
          const focusableInNext = nextElement.querySelector('button') as HTMLElement;
          focusableInNext?.focus();
        }
      }
    });
  };

  return (
    <div ref={containerRef} className="flex flex-col">  // UPDATE THIS (add ref)
```

**Update the NotificationItem calls** (inside the map):
```typescript
{notifications.map((notification) => (
  <NotificationItem
    key={notification.id}
    ref={(el) => {  // ADD THIS REF CALLBACK
      if (el) {
        itemRefs.current.set(notification.id, el);
      } else {
        itemRefs.current.delete(notification.id);
      }
    }}
    notification={notification}
    onClick={() => {
      onNotificationClick(notification.id);
      onClose();
    }}
    onDismiss={(e) => handleDismiss(notification.id, e)}  // UPDATE THIS (use handleDismiss)
  />
))}
```

**Add focus-visible classes to action buttons**:
```typescript
<Button
  variant="ghost"
  size="sm"
  className="h-7 text-xs focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"  // UPDATE THIS
  onClick={(e) => {
    e.stopPropagation();
    onMarkAllRead();
  }}
>
  Mark all read
</Button>

<Button
  variant="ghost"
  size="sm"
  className="h-7 text-xs text-muted-foreground hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"  // UPDATE THIS
  onClick={(e) => {
    e.stopPropagation();
    onClearAll();
  }}
>
  Clear all
</Button>
```

### 4. Convert NotificationItem to forwardRef (~Line 246-352)

**Find**:
```typescript
function NotificationItem({ notification, onClick, onDismiss }: NotificationItemProps) {
```

**Replace with**:
```typescript
const NotificationItem = React.forwardRef<HTMLDivElement, NotificationItemProps>(
  ({ notification, onClick, onDismiss }, ref) => {
```

**Update the container div** (add ref):
```typescript
<div
  ref={ref}  // ADD THIS
  className={cn(
    'group relative px-4 py-3 cursor-pointer',
    'transition-all duration-150',
    'hover:bg-accent/50 hover:shadow-sm',
    'focus-within:bg-accent/50 focus-within:ring-2 focus-within:ring-ring',
    'motion-reduce:transition-none',
    isUnread && 'bg-accent/30'
  )}
  onClick={onClick}
  role="article"  // ADD THIS
  aria-label={`${notification.type} notification: ${notification.title}`}  // ADD THIS
>
```

**Update the icon div**:
```typescript
<div className={cn('mt-0.5 flex-shrink-0', iconColor)} aria-hidden="true">  // ADD aria-hidden
  {icon}
</div>
```

**Update dismiss button**:
```typescript
<Button
  variant="ghost"
  size="icon"
  className={cn(
    "h-6 w-6 flex-shrink-0",
    "opacity-60 hover:opacity-100 focus-visible:opacity-100",
    "transition-opacity duration-150",
    "hover:bg-background/80",
    "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",  // ADD THESE
    "motion-reduce:transition-none"
  )}
  onClick={onDismiss}
  aria-label={`Dismiss ${notification.title} notification`}  // UPDATE THIS
>
  <X className="h-3.5 w-3.5" />
</Button>
```

**Update details toggle button**:
```typescript
<Button
  variant="ghost"
  size="sm"
  className="h-7 px-2 text-xs focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"  // UPDATE THIS
  onClick={handleToggleExpand}
  aria-expanded={expanded}  // ADD THIS
  aria-label={expanded ? "Hide notification details" : "Show notification details"}  // ADD THIS
>
```

**At the end of the NotificationItem component** (after the closing div, before the closing parenthesis of forwardRef):
```typescript
    </div>
  );
}
);  // Close the forwardRef

NotificationItem.displayName = 'NotificationItem';  // ADD THIS
```

## Verification Steps

After applying these changes:

1. **Check TypeScript compilation**:
   ```bash
   cd skillmeat/web && pnpm run type-check
   ```

2. **Test keyboard navigation**:
   - Click notification bell
   - Press Tab to cycle through elements
   - Press Shift+Tab to go backwards
   - Verify focus stays trapped in dropdown

3. **Test focus restoration**:
   - Open dropdown
   - Press Escape
   - Verify focus returns to bell button

4. **Test dismiss focus**:
   - Open dropdown with multiple notifications
   - Tab to dismiss button
   - Press Enter to dismiss
   - Verify focus moves to next notification

## Alternative: Apply Changes via Git Patch

If manual edits are error-prone, you can:

1. Copy the backup file over current:
   ```bash
   cp skillmeat/web/components/notifications/NotificationCenter.tsx.backup skillmeat/web/components/notifications/NotificationCenter.tsx
   ```

2. Apply changes incrementally using the sections above

3. Run formatter:
   ```bash
   cd skillmeat/web && pnpm run format
   ```

## Testing Checklist

- [ ] Import useFocusTrap added
- [ ] NotificationBell has triggerRef and handleOpenChange
- [ ] NotificationDropdown has focus trap and smart dismiss
- [ ] NotificationItem is forwardRef with ARIA attributes
- [ ] All buttons have focus-visible rings
- [ ] TypeScript compiles without errors
- [ ] Keyboard navigation works (Tab, Shift+Tab, Enter, Escape)
- [ ] Focus restoration works on close
- [ ] Focus management works after dismiss

## If You Get Stuck

The key files are:
- Hook (complete): `/skillmeat/web/hooks/useFocusTrap.ts`
- Component (needs updates): `/skillmeat/web/components/notifications/NotificationCenter.tsx`
- Backup: `/skillmeat/web/components/notifications/NotificationCenter.tsx.backup`

You can compare the backup and current file to see what was auto-formatted:
```bash
diff skillmeat/web/components/notifications/NotificationCenter.tsx.backup skillmeat/web/components/notifications/NotificationCenter.tsx
```
