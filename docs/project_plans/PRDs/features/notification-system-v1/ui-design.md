# Notification System UI Design

**Feature**: Notification Center for SkillMeat
**Version**: 1.0
**Status**: Design Complete
**Created**: 2025-12-03

---

## Overview

A refined notification system for SkillMeat that provides real-time feedback for imports, syncs, errors, and other system events. The design follows SkillMeat's dark theme aesthetic with zinc/slate grays and teal accents, prioritizing clarity and minimal distraction.

---

## Design Principles

1. **Minimal Distraction**: Notifications appear only when needed, with subtle animations
2. **Information Hierarchy**: Clear visual distinction between notification types
3. **Contextual Details**: Expandable sections for complex operations (imports, syncs)
4. **Purposeful Motion**: Animations serve function, not decoration
5. **Accessible**: Full keyboard navigation, ARIA labels, screen reader support

---

## Component Architecture

```
NotificationBell (Header Component)
  └─> DropdownMenu
       └─> NotificationDropdown (Panel)
            ├─> Header (Actions)
            ├─> ScrollArea
            │    └─> NotificationItem[] (List)
            │         └─> ImportResultDetails (Expandable)
            └─> EmptyState (No Notifications)
```

---

## Visual Design Specifications

### Color Palette

```
Notification Types:
- Import:   text-blue-500   (#3b82f6)
- Sync:     text-teal-500   (#14b8a6)
- Error:    text-red-500    (#ef4444)
- Success:  text-green-500  (#22c55e)
- Info:     text-muted-foreground

UI Elements:
- Background:     bg-background (zinc-950)
- Popover:        bg-popover (zinc-900)
- Border:         border (zinc-800)
- Muted:          bg-muted/30 (zinc-800/30)
- Accent Hover:   bg-accent/50 (zinc-800/50)
- Unread:         bg-accent/30 (zinc-800/30)
- Unread Stripe:  bg-primary (teal-500)
```

### Typography

```
Header:           text-base font-semibold
Notification:     text-sm font-medium
Message:          text-xs text-muted-foreground
Timestamp:        text-xs text-muted-foreground/70
Badge (count):    text-[10px] font-bold
Badge (type):     text-[10px] font-medium
```

### Spacing

```
Dropdown Width:    420px
Max Height:        500px
Padding:           px-4 py-3 (items)
Gap:               gap-3 (icon/content)
Icon Size:         h-4 w-4 / h-5 w-5 (bell)
Badge Size:        h-5 min-w-[20px]
Border Radius:     rounded-md (8px)
```

---

## Component States & Interactions

### 1. NotificationBell (Header Icon)

#### Default State
```
┌─────────────────────────────────────┐
│  [SkillMeat]         [GitHub] [Docs] │
│                                  🔔  │
└─────────────────────────────────────┘
     Bell icon, no badge
```

#### With Unread Count
```
┌─────────────────────────────────────┐
│  [SkillMeat]         [GitHub] [Docs] │
│                                🔔(3) │
└─────────────────────────────────────┘
     Bell with red badge showing count
     Badge: destructive variant, rounded-full
     Animation: fade-in zoom-in on new notification
```

#### States
- **Default**: `variant="ghost"` button with bell icon
- **Hover**: Subtle background highlight
- **Active**: Dropdown opens below
- **Badge**: Appears at `-right-1 -top-1` position
  - Shows count (1-99) or "99+" if more
  - `variant="destructive"` for visibility
  - Hidden when `unreadCount === 0`

---

### 2. NotificationDropdown (Panel)

#### Structure
```
┌────────────────────────────────────────┐
│ Notifications    [Mark all read] [Clear all] │
├────────────────────────────────────────┤
│ [Scroll Area - max 500px height]      │
│                                        │
│ ┌────────────────────────────────┐   │
│ │ 🔵 Import Complete              │   │
│ │    6 artifacts imported          │   │
│ │    2 min ago                     │   │
│ │    [Show details ▼]              │   │
│ └────────────────────────────────┘   │
│                                        │
│ ┌────────────────────────────────┐   │
│ │ ⚪ Sync Completed                │   │
│ │    All artifacts up to date      │   │
│ │    10 min ago                    │   │
│ └────────────────────────────────┘   │
│                                        │
│ ┌────────────────────────────────┐   │
│ │ 🔴 Import Failed                 │   │
│ │    3 artifacts failed to import  │   │
│ │    1 hour ago                    │   │
│ │    [Show details ▼]              │   │
│ └────────────────────────────────┘   │
│                                        │
└────────────────────────────────────────┘
```

#### Header
```
┌────────────────────────────────────────┐
│ Notifications    [Mark all read] [Clear all] │
├────────────────────────────────────────┤
```
- **Title**: `text-base font-semibold`
- **Actions**:
  - "Mark all read": Shows only if unread notifications exist
  - "Clear all": Shows only if any notifications exist
  - Both: `variant="ghost" size="sm"` buttons

#### Empty State
```
┌────────────────────────────────────────┐
│ Notifications             [Clear all]  │
├────────────────────────────────────────┤
│                                        │
│             🔔                         │
│       No notifications                 │
│   You'll see updates about imports,    │
│   syncs, and errors here               │
│                                        │
└────────────────────────────────────────┘
```
- Large bell icon: `h-12 w-12 text-muted-foreground/40`
- Text: Centered, muted colors

---

### 3. NotificationItem

#### Default (Read)
```
┌──────────────────────────────────────┐
│ 🔵 Import Complete              [×] │
│    6 artifacts imported              │
│    2 min ago                         │
│    [Show details ▼]                  │
└──────────────────────────────────────┘
```

#### Unread (with indicator stripe)
```
┌──────────────────────────────────────┐
█ 🔵 Import Complete              [×] │
█    6 artifacts imported              │
█    2 min ago                         │
█    [Show details ▼]                  │
└──────────────────────────────────────┘
  ↑ 1px teal stripe on left edge
    + bg-accent/30 background tint
```

#### Expanded (showing details)
```
┌──────────────────────────────────────┐
│ 🔵 Import Complete              [×] │
│    6 artifacts imported              │
│    2 min ago                         │
│    [Hide details ▲]                  │
│  ┌──────────────────────────────┐   │
│  │ ✓ 6 succeeded  ✗ 0 failed    │   │
│  │ Total: 6                      │   │
│  │                               │   │
│  │ ✓ [skill] canvas-design       │   │
│  │ ✓ [command] deploy            │   │
│  │ ✓ [agent] code-reviewer       │   │
│  │ ...                           │   │
│  └──────────────────────────────┘   │
└──────────────────────────────────────┘
```

#### Visual Hierarchy
1. **Icon** (left, colored by type)
   - 4x4 size, colored by notification type
   - Fixed width for alignment

2. **Title** (primary line)
   - `text-sm font-medium`
   - Single line, no truncation

3. **Message** (secondary line)
   - `text-xs text-muted-foreground`
   - Max 2 lines, line-clamp-2

4. **Timestamp** (tertiary)
   - `text-xs text-muted-foreground/70`
   - Relative format: "2 min ago", "1 hour ago"

5. **Dismiss Button** (right)
   - `size="icon" h-6 w-6`
   - Shows on hover: `opacity-0 group-hover:opacity-100`
   - X icon, subtle

#### Interaction States
- **Default**: `bg-background` (or `bg-accent/30` if unread)
- **Hover**: `hover:bg-accent/50`
- **Active/Focus**: Ring outline for keyboard nav
- **Click**: Marks as read, can trigger detail view

---

### 4. ImportResultDetails (Expandable Section)

#### Structure
```
┌────────────────────────────────────┐
│ ✓ 6 succeeded  ✗ 2 failed         │
│ Total: 8                           │
│                                    │
│ ✓ [skill] canvas-design            │
│ ✓ [skill] doc-writer               │
│ ✓ [command] deploy                 │
│ ✓ [agent] code-reviewer            │
│ ✗ [skill] broken-skill             │
│   Error: Invalid manifest format    │
│ ✗ [command] missing-deps           │
│   Error: Dependency not found       │
└────────────────────────────────────┘
```

#### Summary Section
```
┌────────────────────────────────────┐
│ ✓ 6 succeeded  ✗ 2 failed         │
│ Total: 8                           │
└────────────────────────────────────┘
```
- Green checkmark icon + count
- Red X icon + count
- Muted text for total
- `text-xs` size

#### Artifact List
```
┌────────────────────────────────────┐
│ ✓ [skill] canvas-design            │
│ ✓ [command] deploy                 │
│ ✗ [skill] broken-skill             │
│   Error: Invalid manifest format    │
└────────────────────────────────────┘
```
- Each item shows:
  - Status icon (green ✓ or red ✗)
  - Type badge: `variant="outline" h-4 px-1 text-[10px]`
  - Artifact name: `font-medium truncate`
  - Error message (if failed): `text-muted-foreground line-clamp-2`
- Scrollable if > ~8 items: `max-h-[200px] overflow-y-auto`
- Hover effect: `hover:bg-background/60`

---

## Animations & Transitions

### Badge Appearance (New Notification)
```css
animate-in fade-in zoom-in
duration: ~150ms
```
Subtle pop-in effect when badge appears or count increases.

### Dropdown Open/Close
```css
/* Built into Radix DropdownMenu */
data-[state=open]:animate-in
data-[state=closed]:animate-out
fade + zoom + slide (from top)
duration: ~200ms
```

### Notification Item Transitions
```css
transition-colors
duration: ~150ms
```
Smooth background color change on hover/read state.

### Expand/Collapse Details
```css
/* Built into Radix Collapsible or manual */
height animation
duration: ~200ms ease-out
```

---

## Responsive Behavior

### Desktop (Default)
- Dropdown width: 420px
- Positioned below bell icon, aligned right
- Max 50 notifications stored
- Scrollable list at 500px height

### Mobile/Tablet Considerations
For future iterations:
- Full-width panel or modal
- Touch-friendly target sizes (min 44px)
- Swipe-to-dismiss gestures
- Bottom sheet on mobile

---

## Accessibility Features

### Keyboard Navigation
- **Tab**: Focus bell button
- **Enter/Space**: Open dropdown
- **Arrow Keys**: Navigate notification items
- **Enter**: Click notification
- **Escape**: Close dropdown

### Screen Reader Support
- Bell button: `aria-label` with count
- Unread indicator: `aria-hidden="true"` (visual only)
- Notification items: Semantic HTML (role="button")
- Dismiss buttons: `aria-label="Dismiss notification"`
- Empty state: Descriptive text

### Focus Management
- Trap focus within dropdown when open
- Return focus to bell on close
- Visible focus indicators on all interactive elements

---

## Notification Type Specifications

### Import
- **Icon**: Download (🔵 blue)
- **Title**: "Import Complete" / "Import Failed"
- **Message**: "{count} artifacts imported" / "{count} failed"
- **Details**: Import results with artifact list

### Sync
- **Icon**: RefreshCw (⚪ teal)
- **Title**: "Sync Complete" / "Sync Failed"
- **Message**: "All artifacts up to date" / "Failed to sync"
- **Details**: Optional list of updated artifacts

### Error
- **Icon**: XCircle (🔴 red)
- **Title**: Error description
- **Message**: Error message
- **Details**: Stack trace or debug info (optional)

### Success
- **Icon**: CheckCircle2 (🟢 green)
- **Title**: Success message
- **Message**: Brief description
- **Details**: None typically

### Info
- **Icon**: Info (⚪ muted)
- **Title**: Info title
- **Message**: Info message
- **Details**: Optional additional context

---

## Implementation Notes

### Dependencies
- Radix UI: `@radix-ui/react-dropdown-menu`, `@radix-ui/react-scroll-area`
- shadcn/ui: Button, Badge, DropdownMenu, ScrollArea
- lucide-react: Icons
- date-fns: Relative time formatting (`formatDistanceToNow`)

### State Management
Example using local React state (see `useNotifications` hook in component):
- Notifications array (max 50)
- Mark as read
- Clear all
- Dismiss individual

For production, consider:
- Global state (Zustand, Jotai)
- Persistence (localStorage, IndexedDB)
- Server sync (WebSocket, polling)

### Performance
- Virtualized list for 100+ notifications (react-window)
- Memoize notification items
- Debounce rapid notification additions
- Lazy load details on expand

---

## Edge Cases

### Long Content
- Titles: Single line, no truncation (assumed short)
- Messages: Max 2 lines with `line-clamp-2`
- Artifact names: Truncate with ellipsis
- Error messages: Max 2 lines in details

### High Volume
- Max 50 notifications displayed
- Older notifications automatically removed
- Consider "View all" link to dedicated page

### No JavaScript
- Bell icon visible
- Link to dedicated notifications page (/notifications)
- Progressive enhancement

---

## Future Enhancements

1. **Categories/Filters**
   - Filter by type (imports, syncs, errors)
   - Search notifications

2. **Notification Settings**
   - Mute certain types
   - Desktop notifications (Web Notifications API)
   - Email digest

3. **Action Buttons**
   - "Retry import" on failed imports
   - "View details" link to full page
   - Quick actions in notification

4. **Real-time Updates**
   - WebSocket connection for live updates
   - Toast notifications for critical events

5. **Rich Content**
   - Preview images (for visual artifacts)
   - Code snippets (for skill updates)
   - Diff view (for sync changes)

---

## Design Assets

### Icon Mapping
```typescript
import {
  Bell,          // Main bell icon
  CheckCircle2,  // Success
  XCircle,       // Error/Failed
  AlertCircle,   // Warning
  Info,          // Info
  Download,      // Import
  RefreshCw,     // Sync
  ChevronDown,   // Expand
  ChevronUp,     // Collapse
  X,             // Dismiss
} from 'lucide-react';
```

### Color Tokens (Tailwind)
```css
/* Notification types */
.icon-import { @apply text-blue-500; }
.icon-sync { @apply text-teal-500; }
.icon-error { @apply text-red-500; }
.icon-success { @apply text-green-500; }
.icon-info { @apply text-muted-foreground; }

/* Unread indicator */
.unread-stripe { @apply bg-primary; /* teal */ }
.unread-bg { @apply bg-accent/30; }

/* Badge */
.badge-count { @apply bg-destructive text-destructive-foreground; }
```

---

## Usage Example

```tsx
import { NotificationBell, useNotifications } from '@/components/notifications/NotificationCenter';

export function Header() {
  const {
    notifications,
    unreadCount,
    markAsRead,
    markAllAsRead,
    clearAll,
    dismissNotification,
  } = useNotifications();

  return (
    <header>
      <div className="flex items-center justify-between">
        <Logo />
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
```

---

## Design Checklist

- [x] Component states defined (default, hover, active, disabled)
- [x] Loading state considered (via parent component)
- [x] Error state defined (error notification type)
- [x] Empty state designed
- [x] Dark mode support (native via design tokens)
- [x] Keyboard navigation specified
- [x] Screen reader support defined
- [x] Focus management documented
- [x] Responsive considerations noted
- [x] Animation specifications included
- [x] Color system aligned with SkillMeat theme
- [x] Typography scales defined
- [x] Spacing consistency (4px/8px grid)
- [x] Icon usage standardized (lucide-react)
- [x] Edge cases documented

---

## Sign-off

**Design Complete**: 2025-12-03
**Components**: NotificationBell, NotificationDropdown, NotificationItem, ImportResultDetails
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/notifications/NotificationCenter.tsx`

Ready for integration into SkillMeat header and backend notification system.
