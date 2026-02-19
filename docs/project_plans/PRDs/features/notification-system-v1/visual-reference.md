---
status: inferred_complete
schema_version: 2
doc_type: prd
feature_slug: visual-reference
---
# Notification System Visual Reference

**Quick visual guide to the notification system design**

---

## Color Palette

```
Notification Type Colors:
┌─────────────────────────────────────────┐
│ 🔵 Import      text-blue-500   #3b82f6  │
│ ⚪ Sync        text-teal-500   #14b8a6  │
│ 🔴 Error       text-red-500    #ef4444  │
│ 🟢 Success     text-green-500  #22c55e  │
│ ⚪ Info        text-muted      #71717a  │
└─────────────────────────────────────────┘

UI Colors:
┌─────────────────────────────────────────┐
│ Background       zinc-950      #09090b  │
│ Popover          zinc-900      #18181b  │
│ Border           zinc-800      #27272a  │
│ Muted            zinc-800/30            │
│ Accent (hover)   zinc-800/50            │
│ Unread BG        zinc-800/30            │
│ Unread Stripe    teal-500      #14b8a6  │
│ Badge (count)    red-500       #ef4444  │
└─────────────────────────────────────────┘
```

---

## Component States

### 1. Bell Icon (Header)

**Default (No Notifications)**
```
┌──────────────────────────────────────┐
│  SkillMeat              GitHub  Docs │
│                                   🔔 │
└──────────────────────────────────────┘
```

**With Unread Count**
```
┌──────────────────────────────────────┐
│  SkillMeat              GitHub  Docs │
│                               🔔 (3) │
└──────────────────────────────────────┘
       Badge: red circle with number
       Animation: fade-in + zoom-in
```

**Badge States**
```
1-9:   Single digit  (3)
10-99: Two digits    (42)
100+:  "99+"         (99+)
0:     Hidden        (no badge)
```

---

### 2. Dropdown Panel

**Full Panel Structure**
```
┌────────────────────────────────────────────┐
│ Notifications  [Mark all read] [Clear all]│ ← Header
├────────────────────────────────────────────┤
│                                            │
│ ┌────────────────────────────────────────┐│
│ │ 🔵 Import Complete               [×]  ││ ← Notification Item
│ │    6 artifacts imported successfully   ││
│ │    2 min ago                           ││
│ │    [Show details ▼]                    ││
│ └────────────────────────────────────────┘│
│                                            │
│ ┌────────────────────────────────────────┐│
│ │ ⚪ Sync Complete                  [×]  ││
│ │    All artifacts up to date            ││
│ │    10 min ago                          ││
│ └────────────────────────────────────────┘│
│                                            │
│ ┌────────────────────────────────────────┐│
│ │ 🔴 Import Failed                 [×]  ││
│ │    3 artifacts failed to import        ││
│ │    1 hour ago                          ││
│ │    [Show details ▼]                    ││
│ └────────────────────────────────────────┘│
│                                            │
│ ... more notifications ...                │
│                                            │
└────────────────────────────────────────────┘
         420px wide, max 500px tall
         Scrollable if > 6-7 items
```

**Empty State**
```
┌────────────────────────────────────────────┐
│ Notifications                 [Clear all] │
├────────────────────────────────────────────┤
│                                            │
│                                            │
│                   🔔                       │
│            No notifications                │
│                                            │
│   You'll see updates about imports,        │
│   syncs, and errors here                   │
│                                            │
│                                            │
└────────────────────────────────────────────┘
```

---

### 3. Notification Item States

**Read (Default)**
```
┌────────────────────────────────────────┐
│ 🔵 Import Complete              [×]   │
│    6 artifacts imported                │
│    2 min ago                           │
│    [Show details ▼]                    │
└────────────────────────────────────────┘
   bg-background
```

**Unread**
```
┌────────────────────────────────────────┐
█ 🔵 Import Complete              [×]   │
█    6 artifacts imported                │
█    2 min ago                           │
█    [Show details ▼]                    │
└────────────────────────────────────────┘
↑ bg-accent/30 + teal stripe (1px left)
```

**Hover**
```
┌────────────────────────────────────────┐
│ 🔵 Import Complete              [×]   │ ← Shows [×] on hover
│    6 artifacts imported                │
│    2 min ago                           │
│    [Show details ▼]                    │
└────────────────────────────────────────┘
   bg-accent/50 (lighter)
```

**Expanded**
```
┌────────────────────────────────────────┐
│ 🔵 Import Complete              [×]   │
│    6 artifacts imported                │
│    2 min ago                           │
│    [Hide details ▲]                    │
│  ┌──────────────────────────────────┐ │
│  │ ✓ 6 succeeded  ✗ 2 failed       │ │
│  │ Total: 8                         │ │
│  │                                  │ │
│  │ ✓ [skill] canvas-design          │ │
│  │ ✓ [skill] doc-writer             │ │
│  │ ✓ [command] deploy               │ │
│  │ ✓ [agent] code-reviewer          │ │
│  │ ✓ [mcp] postgres-mcp             │ │
│  │ ✓ [hook] pre-commit              │ │
│  │ ✗ [skill] broken-skill           │ │
│  │   Error: Invalid manifest format │ │
│  │ ✗ [command] missing-deps         │ │
│  │   Error: Dependency not found    │ │
│  └──────────────────────────────────┘ │
└────────────────────────────────────────┘
   Details: muted bg, rounded border
   Scrollable if > 8 artifacts
```

---

### 4. Notification Types

**Import (Blue)**
```
┌────────────────────────────────────────┐
│ 🔵 Import Complete              [×]   │
│    6 artifacts imported successfully   │
│    2 min ago                           │
│    [Show details ▼]                    │
└────────────────────────────────────────┘
Icon: Download (🔵)
Color: text-blue-500
```

**Sync (Teal)**
```
┌────────────────────────────────────────┐
│ ⚪ Sync Complete                 [×]   │
│    All artifacts up to date            │
│    10 min ago                          │
└────────────────────────────────────────┘
Icon: RefreshCw (⚪)
Color: text-teal-500
```

**Error (Red)**
```
┌────────────────────────────────────────┐
│ 🔴 Connection Failed             [×]   │
│    Unable to connect to GitHub API     │
│    1 hour ago                          │
└────────────────────────────────────────┘
Icon: XCircle (🔴)
Color: text-red-500
```

**Success (Green)**
```
┌────────────────────────────────────────┐
│ 🟢 Artifact Deployed             [×]   │
│    canvas-design deployed to project   │
│    5 min ago                           │
└────────────────────────────────────────┘
Icon: CheckCircle2 (🟢)
Color: text-green-500
```

**Info (Gray)**
```
┌────────────────────────────────────────┐
│ ⚪ Update Available               [×]   │
│    New version of SkillMeat available  │
│    2 hours ago                         │
└────────────────────────────────────────┘
Icon: Info (⚪)
Color: text-muted-foreground
```

---

### 5. Import Details Component

**Summary Section**
```
┌────────────────────────────────────────┐
│ ✓ 6 succeeded  ✗ 2 failed             │
│ Total: 8                               │
└────────────────────────────────────────┘
   Green ✓ + Red ✗
   text-xs
```

**Artifact List (Success)**
```
┌────────────────────────────────────────┐
│ ✓ [skill] canvas-design                │
│ ✓ [command] deploy                     │
│ ✓ [agent] code-reviewer                │
└────────────────────────────────────────┘
   Green checkmark
   Type badge: outlined, small
   Name: truncate if too long
```

**Artifact List (Failure)**
```
┌────────────────────────────────────────┐
│ ✗ [skill] broken-skill                 │
│   Error: Invalid manifest format       │
│ ✗ [command] missing-deps               │
│   Error: Dependency not found          │
└────────────────────────────────────────┘
   Red X
   Error message: muted, smaller text
   Max 2 lines per error
```

---

## Typography Scale

```
┌─────────────────────────────────────────┐
│ Component        Size      Weight       │
├─────────────────────────────────────────┤
│ Header           text-base  font-semibold
│ Notification     text-sm    font-medium │
│ Message          text-xs    normal      │
│ Timestamp        text-xs    normal      │
│ Badge (count)    text-[10px] font-bold │
│ Badge (type)     text-[10px] font-medium│
│ Details summary  text-xs    normal      │
│ Error message    text-xs    normal      │
└─────────────────────────────────────────┘
```

---

## Spacing & Sizing

```
┌─────────────────────────────────────────┐
│ Element              Value              │
├─────────────────────────────────────────┤
│ Dropdown width       420px              │
│ Dropdown max height  500px              │
│ Item padding         px-4 py-3 (16/12)  │
│ Icon/Content gap     gap-3 (12px)       │
│ Icon size            h-4 w-4 (16px)     │
│ Bell icon size       h-5 w-5 (20px)     │
│ Badge size           h-5 min-w-[20px]   │
│ Dismiss button       h-6 w-6 (24px)     │
│ Border radius        rounded-md (8px)   │
│ Badge radius         rounded-full       │
└─────────────────────────────────────────┘
```

---

## Icon Reference

```
Notification Icons:
┌─────────────────────────────────────────┐
│ Bell          Main notification icon    │
│ Download      Import operation          │
│ RefreshCw     Sync operation            │
│ XCircle       Error/Failed              │
│ CheckCircle2  Success                   │
│ Info          Info message              │
│ ChevronDown   Expand details            │
│ ChevronUp     Collapse details          │
│ X             Dismiss notification      │
└─────────────────────────────────────────┘

Badge Icons:
┌─────────────────────────────────────────┐
│ CheckCircle2  Success (green)           │
│ XCircle       Failed (red)              │
└─────────────────────────────────────────┘

All from lucide-react
```

---

## Animations

**Badge Appearance** (new notification)
```
Duration: 150ms
Effect: fade-in + zoom-in
Trigger: unreadCount increases
```

**Dropdown Open**
```
Duration: 200ms
Effect: fade-in + zoom-in + slide-from-top
Trigger: Bell click
```

**Dropdown Close**
```
Duration: 200ms
Effect: fade-out + zoom-out + slide-to-top
Trigger: Escape key or click outside
```

**Notification Hover**
```
Duration: 150ms
Effect: background color transition
Trigger: Mouse enter/leave
```

**Details Expand/Collapse**
```
Duration: 200ms
Effect: height animation (ease-out)
Trigger: Toggle button click
```

---

## Responsive Behavior

### Desktop (Default - 420px)
```
┌────────────────────────────────────────┐
│ Notifications  [Mark all] [Clear all] │
├────────────────────────────────────────┤
│ Full notification with all details     │
└────────────────────────────────────────┘
```

### Tablet (Same as desktop)
```
Same 420px dropdown
Position: aligned right to bell icon
```

### Mobile (Future - Full Width)
```
┌────────────────────────────────────────┐
│ Notifications                      [×] │
├────────────────────────────────────────┤
│ Full-width modal or bottom sheet       │
│ Swipe to dismiss gestures             │
│ Larger touch targets (min 44px)       │
└────────────────────────────────────────┘
```

---

## Accessibility Features

**Keyboard Navigation**
```
Tab         → Focus bell button
Enter/Space → Open dropdown
Arrow Down  → Next notification
Arrow Up    → Previous notification
Enter       → Click notification
Escape      → Close dropdown
```

**Screen Reader Announcements**
```
Bell button: "Notifications, 3 unread"
Badge:       Announced with button label
Items:       "Import Complete, 2 minutes ago"
Dismiss:     "Dismiss notification"
Empty:       "No notifications. You'll see updates..."
```

**Focus Management**
```
1. Open dropdown → focus first notification
2. Navigate → visible focus ring
3. Close → return focus to bell button
4. Trap focus within dropdown when open
```

---

## Edge Cases Handled

**Long Content**
```
Title:        No truncation (assumed short)
Message:      line-clamp-2 (max 2 lines)
Artifact:     truncate with ellipsis
Error:        line-clamp-2 in details
```

**Many Notifications**
```
Display:      Max 50 stored
Scroll:       Vertical scroll at 500px
Performance:  Consider virtualization at 100+
```

**Very Long Time Ago**
```
"2 min ago"     → Recent
"1 hour ago"    → Hour
"2 days ago"    → Days
"Jan 15, 2024"  → Absolute date (old)
```

**No JavaScript**
```
Bell icon visible
Link to /notifications page
Progressive enhancement
```

---

## Visual Hierarchy

```
Primary (Most Important)
  ↓
┌─────────────────────────┐
│ 🔵 Title (font-medium)  │ ← User sees first
├─────────────────────────┤
│    Message (muted)      │ ← Context
├─────────────────────────┤
│    Timestamp (lighter)  │ ← When
└─────────────────────────┘
       ↓
Secondary (On Demand)
  ↓
┌─────────────────────────┐
│ [Details button]        │ ← User clicks
├─────────────────────────┤
│  Details panel          │ ← Expandable
└─────────────────────────┘
```

---

## Implementation Checklist

Design Complete:
- [x] Component states defined
- [x] Color system aligned
- [x] Typography scales set
- [x] Spacing consistent (8px grid)
- [x] Icons standardized
- [x] Animations specified
- [x] Accessibility features
- [x] Keyboard navigation
- [x] Screen reader support
- [x] Focus management
- [x] Empty state designed
- [x] Error states defined
- [x] Loading states (via parent)
- [x] Dark mode native
- [x] Edge cases documented

Ready for Integration:
- [x] Component file created
- [x] Types defined
- [x] Hook implemented
- [x] Examples provided
- [x] Integration guide written
- [x] Dependency added (date-fns)

---

## Quick Reference

**Component Location**:
`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/notifications/NotificationCenter.tsx`

**Key Files**:
- Component: `NotificationCenter.tsx`
- Design: `ui-design.md`
- Integration: `integration-example.md`
- README: `README.md`

**Dependencies**:
- date-fns (timestamp formatting)
- lucide-react (icons)
- Radix UI (dropdown, scroll area)
- shadcn/ui (Button, Badge, etc.)

**Install**:
```bash
cd skillmeat/web
pnpm install
```

**Usage**:
```tsx
import { NotificationBell, useNotifications } from '@/components/notifications/NotificationCenter';

const { notifications, unreadCount, ... } = useNotifications();

<NotificationBell
  unreadCount={unreadCount}
  notifications={notifications}
  {...handlers}
/>
```

---

**Visual design complete and ready for implementation!**
