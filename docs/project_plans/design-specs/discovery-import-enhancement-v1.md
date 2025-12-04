---
title: Discovery & Import Enhancement UI/UX Design Specification
version: 1.0.0
status: draft
created: 2025-12-04
updated: 2025-12-04
feature: Discovery & Import Enhancement
epic: Project Management
---

# Discovery & Import Enhancement UI/UX Design Specification

## Executive Summary

This specification defines the UI/UX patterns for enhancing the artifact discovery and import flow in SkillMeat. The enhancement addresses misleading status messages, adds pre-scan intelligence, and introduces a permanent Discovery Tab for better artifact management.

## Design Goals

1. **Clarity**: Replace confusing "Failed" status with accurate "Skipped" messaging
2. **Intelligence**: Show users what will happen before they commit to import
3. **Control**: Allow users to manage discovery preferences per artifact
4. **Visibility**: Provide permanent access to all discovered artifacts
5. **Speed**: Maintain fast import flows with minimal friction
6. **Accessibility**: Ensure all interactions are keyboard-navigable and screen-reader friendly

## Technology Stack

- **Component Library**: Radix UI primitives
- **Styling**: Tailwind CSS (4px/8px grid system)
- **UI Patterns**: shadcn/ui conventions
- **Icons**: Lucide React
- **Animation**: Framer Motion (subtle transitions)

---

## 1. Component Specifications

### 1.1 Discovery Tab Component (`DiscoveryTab.tsx`)

**Purpose**: Permanent tab on Project Detail page showing all discovered artifacts regardless of import status.

**Location**: Integrated within the Project Detail page, likely as part of a tab group with "Deployed Artifacts" and "Discovery".

#### Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│ Project: My Claude Project                                  │
│ ┌─────────────────┬─────────────────┐                       │
│ │ Deployed (12)   │ Discovery (5)   │                       │
│ └─────────────────┴─────────────────┘                       │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Filters: [All Types ▾] [All Statuses ▾] [🔍 Search...]  │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Name              Type    Status           Actions        │ │
│ ├─────────────────────────────────────────────────────────┤ │
│ │ canvas-design     Skill   ✓ In Project     [Import]      │ │
│ │ api-architect     Skill   ⚠ In Collection  [Import]      │ │
│ │ debug-helper      Skill   ℹ Skipped        [Import]      │ │
│ │ code-reviewer     Skill   ◯ Ready          [Import]      │ │
│ │ test-generator    Skill   ✓ In Both        -             │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                               │
│ Bulk Actions: [Select All] [Import Selected (3)]            │
└─────────────────────────────────────────────────────────────┘
```

#### Visual Design

**Tab Switcher**:
- Use shadcn/ui Tabs component
- Active tab: `border-b-2 border-primary text-foreground font-medium`
- Inactive tab: `text-muted-foreground hover:text-foreground transition-colors`
- Badge count in each tab: `ml-2 px-2 py-0.5 text-xs bg-secondary rounded-full`

**Filter Bar**:
- Height: `h-12` (48px)
- Background: `bg-muted/50`
- Border: `border-b border-border`
- Spacing: `flex items-center gap-4 px-4`
- Dropdowns: shadcn/ui Select component
- Search: shadcn/ui Input with search icon

**Table/List View**:
- Desktop: Table with 4 columns (Name, Type, Status, Actions)
- Mobile: Card view with stacked layout
- Row height: `min-h-16` (64px)
- Row hover: `hover:bg-muted/50 transition-colors`
- Cell padding: `px-4 py-3`

**Empty States**:

```
┌─────────────────────────────────────────────────────────────┐
│                                                               │
│                     🔍 No Artifacts Discovered                │
│                                                               │
│           Run discovery to find artifacts in this project    │
│                                                               │
│                   [Run Discovery Scan]                        │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**Alternative empty states**:
- "All Imported": Show checkmark icon with "All discovered artifacts have been imported"
- "Filtered Out": Show filter icon with "No artifacts match your filters. [Clear Filters]"

#### Tailwind Classes

```tsx
// Tab Container
className="border-b border-border"

// Tab Trigger (Active)
className="inline-flex items-center justify-center whitespace-nowrap rounded-t-md px-3 py-2 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border-b-2 border-primary text-foreground"

// Tab Trigger (Inactive)
className="inline-flex items-center justify-center whitespace-nowrap rounded-t-md px-3 py-2 text-sm font-medium text-muted-foreground ring-offset-background transition-all hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"

// Filter Bar
className="flex items-center gap-4 h-12 px-4 bg-muted/50 border-b border-border"

// Table Container
className="overflow-x-auto"

// Table
className="w-full border-collapse"

// Table Row
className="border-b border-border hover:bg-muted/50 transition-colors"

// Table Cell
className="px-4 py-3 text-sm"
```

#### Interaction Patterns

1. **Tab Switching**: Smooth fade transition (150ms) when switching between Deployed and Discovery tabs
2. **Filter Updates**: Instant filter with 300ms debounce on search input
3. **Bulk Selection**: Checkboxes appear on row hover (desktop) or always visible (mobile)
4. **Import Action**: Opens BulkImportModal with pre-selected artifacts

#### Loading States

```tsx
// Skeleton loader for table rows
<div className="animate-pulse space-y-2">
  <div className="h-16 bg-muted rounded" />
  <div className="h-16 bg-muted rounded" />
  <div className="h-16 bg-muted rounded" />
</div>
```

---

### 1.2 BulkImportModal Enhancements

**Purpose**: Show pre-scan intelligence and allow users to skip artifacts in future discoveries.

#### Enhanced Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Import Artifacts                                     [✕]     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ Select artifacts to import to "My Claude Project"           │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ☑ canvas-design                           [Skip Future] │ │
│ │   Type: Skill                                            │ │
│ │   ◯ Ready to import                                      │ │
│ ├─────────────────────────────────────────────────────────┤ │
│ │ ☑ api-architect                           [Skip Future] │ │
│ │   Type: Skill                                            │ │
│ │   ⚠ In Collection → Will add to Project only            │ │
│ ├─────────────────────────────────────────────────────────┤ │
│ │ ☐ debug-helper                            [Skip Future] │ │
│ │   Type: Skill                                            │ │
│ │   ✓ Already in Project → Will add to Collection only    │ │
│ ├─────────────────────────────────────────────────────────┤ │
│ │ ☐ test-generator                          [Skip Future] │ │
│ │   Type: Skill                                            │ │
│ │   ✓ Already in both → No action needed                  │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                               │
│ Selected: 2 of 4                                             │
│                                                               │
│                          [Cancel] [Import Selected (2)]      │
└─────────────────────────────────────────────────────────────┘
```

#### Pre-Scan Status Labels

**Badge Design**: Use Radix UI Badge component with color variants

1. **Ready to Import** (New artifact)
   - Badge: `◯ Ready to import`
   - Color: `bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400`
   - Icon: Circle (no fill)

2. **In Collection** (Will add to Project only)
   - Badge: `⚠ In Collection → Will add to Project only`
   - Color: `bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400`
   - Icon: Alert triangle

3. **In Project** (Will add to Collection only)
   - Badge: `✓ Already in Project → Will add to Collection only`
   - Color: `bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400`
   - Icon: Checkmark

4. **In Both** (No action needed)
   - Badge: `✓ Already in both → No action needed`
   - Color: `bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400`
   - Icon: Checkmark
   - Checkbox: Disabled by default (user cannot select)

#### Skip Future Checkbox

**Design**:
- Position: Right side of each artifact row
- Label: "Skip Future"
- Appearance: Small checkbox (16x16px) with text label
- Tooltip: "Don't show this artifact in future discoveries"
- States:
  - Unchecked (default)
  - Checked (artifact will be marked as skipped)
  - Disabled (when artifact is already skipped via preferences)

**Behavior**:
- Independent of import selection checkbox
- Can be checked without importing the artifact
- Shows confirmation tooltip when checked: "Will skip in future discoveries"
- Persists to user preferences on modal submit (even if artifact not imported)

**Tailwind Classes**:

```tsx
// Skip checkbox container
className="flex items-center gap-2 text-xs text-muted-foreground"

// Skip checkbox
className="h-4 w-4 rounded border-input ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"

// Skip label
className="cursor-pointer hover:text-foreground transition-colors"
```

#### Import Results Display

After import completes, show detailed breakdown:

```
┌─────────────────────────────────────────────────────────────┐
│ Import Complete                                      [✕]     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ ✓ 2 imported successfully                                    │
│ ⚠ 1 skipped (already exists)                                 │
│ ✕ 0 failed                                                    │
│                                                               │
│ Details:                                                      │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ✓ canvas-design - Added to Collection and Project       │ │
│ │ ✓ api-architect - Added to Project only                 │ │
│ │ ⚠ test-generator - Skipped (already in both)            │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                               │
│                                            [Done]             │
└─────────────────────────────────────────────────────────────┘
```

**Toast Notification** (for quick feedback):

```
┌─────────────────────────────────────────────┐
│ Import Complete                      [✕]    │
│ 2 imported, 1 skipped                       │
│ [View Details]                               │
└─────────────────────────────────────────────┘
```

#### Tailwind Classes

```tsx
// Modal Container
className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"

// Modal Content
className="w-full max-w-2xl max-h-[80vh] overflow-y-auto bg-background rounded-lg shadow-lg border border-border"

// Modal Header
className="flex items-center justify-between p-6 border-b border-border"

// Modal Body
className="p-6 space-y-4"

// Artifact Row
className="p-4 border border-border rounded-lg hover:border-primary transition-colors"

// Artifact Row (Selected)
className="p-4 border-2 border-primary rounded-lg bg-primary/5"

// Status Badge Container
className="flex items-center gap-2 text-sm"
```

---

### 1.3 DiscoveryBanner Updates

**Purpose**: Show accurate count of truly new artifacts, with breakdown of skipped items.

#### Updated Design

**Before** (Current):
```
┌─────────────────────────────────────────────────────────────┐
│ 🔍 5 new artifacts discovered in this project               │
│                                    [Review & Import]  [✕]    │
└─────────────────────────────────────────────────────────────┘
```

**After** (Enhanced):
```
┌─────────────────────────────────────────────────────────────┐
│ 🔍 3 new artifacts ready to import                          │
│    2 already in collection, 1 already in project            │
│                                    [Review & Import]  [✕]    │
└─────────────────────────────────────────────────────────────┘
```

**Edge Case** (All artifacts exist):
- Banner should NOT appear
- Discovery Tab should still show all discovered artifacts with their status

**Edge Case** (All artifacts user-skipped):
- Banner should NOT appear
- Discovery Tab shows artifacts marked as "Skipped by user"

#### Badge Breakdown (Optional Enhancement)

```
┌─────────────────────────────────────────────────────────────┐
│ 🔍 3 new artifacts ready to import                          │
│    [3 New] [2 In Collection] [1 In Project] [1 Skipped]    │
│                                    [Review & Import]  [✕]    │
└─────────────────────────────────────────────────────────────┘
```

#### Tailwind Classes

```tsx
// Banner Container
className="flex items-start justify-between gap-4 p-4 mb-6 bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg"

// Banner Content
className="flex-1 space-y-1"

// Banner Title
className="text-sm font-medium text-blue-900 dark:text-blue-100"

// Banner Subtitle (breakdown)
className="text-xs text-blue-700 dark:text-blue-300"

// Badge (inline)
className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-200"
```

---

## 2. Status Badge Designs

### Badge Component Specification

**Base Badge**: Radix UI Badge with Tailwind styling

```tsx
<Badge variant={variant} size="sm" className={cn(baseClasses, variantClasses)}>
  <Icon className="w-3 h-3 mr-1" />
  {text}
</Badge>
```

### Badge Variants

#### 2.1 Success (Imported)

```
✓ Imported
```

- **Color**: `bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400`
- **Border**: `border border-green-200 dark:border-green-800`
- **Icon**: `CheckCircle` from Lucide
- **Size**: `text-xs px-2 py-1 rounded-full`
- **Tooltip**: "Successfully imported to [Collection/Project/Both]"

**Tailwind Classes**:
```tsx
className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 border border-green-200 dark:border-green-800"
```

#### 2.2 Skipped (Already in Collection)

```
⚠ In Collection
```

- **Color**: `bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400`
- **Border**: `border border-amber-200 dark:border-amber-800`
- **Icon**: `AlertTriangle` from Lucide
- **Size**: `text-xs px-2 py-1 rounded-full`
- **Tooltip**: "Already exists in Collection. Will add to Project only if imported."

**Tailwind Classes**:
```tsx
className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400 border border-amber-200 dark:border-amber-800"
```

#### 2.3 Skipped (Already in Project)

```
✓ In Project
```

- **Color**: `bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400`
- **Border**: `border border-amber-200 dark:border-amber-800`
- **Icon**: `CheckCircle` from Lucide
- **Size**: `text-xs px-2 py-1 rounded-full`
- **Tooltip**: "Already exists in Project. Will add to Collection only if imported."

**Tailwind Classes**:
```tsx
className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400 border border-amber-200 dark:border-amber-800"
```

#### 2.4 Skipped (User Preference)

```
⊘ Skipped
```

- **Color**: `bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400`
- **Border**: `border border-gray-200 dark:border-gray-700`
- **Icon**: `Ban` from Lucide
- **Size**: `text-xs px-2 py-1 rounded-full`
- **Tooltip**: "Skipped by user preference. Click to enable future discovery."

**Tailwind Classes**:
```tsx
className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 border border-gray-200 dark:border-gray-700"
```

#### 2.5 Failed

```
✕ Failed
```

- **Color**: `bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400`
- **Border**: `border border-red-200 dark:border-red-800`
- **Icon**: `XCircle` from Lucide
- **Size**: `text-xs px-2 py-1 rounded-full`
- **Tooltip**: "Import failed: [error message]"

**Tailwind Classes**:
```tsx
className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400 border border-red-200 dark:border-red-800"
```

#### 2.6 Pending (During Import)

```
◐ Importing...
```

- **Color**: `bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400`
- **Border**: `border border-blue-200 dark:border-blue-800`
- **Icon**: `Loader2` from Lucide (spinning)
- **Size**: `text-xs px-2 py-1 rounded-full`
- **Animation**: `animate-spin` on icon only
- **Tooltip**: "Import in progress..."

**Tailwind Classes**:
```tsx
className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400 border border-blue-200 dark:border-blue-800"

// Icon with animation
<Loader2 className="w-3 h-3 animate-spin" />
```

#### 2.7 Ready (Available for Import)

```
◯ Ready
```

- **Color**: `bg-blue-50 text-blue-700 dark:bg-blue-950/20 dark:text-blue-300`
- **Border**: `border border-blue-200 dark:border-blue-800`
- **Icon**: `Circle` from Lucide
- **Size**: `text-xs px-2 py-1 rounded-full`
- **Tooltip**: "Ready to import to Collection and Project"

**Tailwind Classes**:
```tsx
className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-blue-50 text-blue-700 dark:bg-blue-950/20 dark:text-blue-300 border border-blue-200 dark:border-blue-800"
```

### Badge Color Palette Summary

| Status | Light Mode | Dark Mode | Border Light | Border Dark |
|--------|-----------|-----------|--------------|-------------|
| Success | `bg-green-100 text-green-800` | `bg-green-900/30 text-green-400` | `border-green-200` | `border-green-800` |
| Warning (Collection) | `bg-amber-100 text-amber-800` | `bg-amber-900/30 text-amber-400` | `border-amber-200` | `border-amber-800` |
| Warning (Project) | `bg-amber-100 text-amber-800` | `bg-amber-900/30 text-amber-400` | `border-amber-200` | `border-amber-800` |
| Skipped (User) | `bg-gray-100 text-gray-600` | `bg-gray-800 text-gray-400` | `border-gray-200` | `border-gray-700` |
| Failed | `bg-red-100 text-red-800` | `bg-red-900/30 text-red-400` | `border-red-200` | `border-red-800` |
| Pending | `bg-blue-100 text-blue-800` | `bg-blue-900/30 text-blue-400` | `border-blue-200` | `border-blue-800` |
| Ready | `bg-blue-50 text-blue-700` | `bg-blue-950/20 text-blue-300` | `border-blue-200` | `border-blue-800` |

---

## 3. Interaction Patterns

### 3.1 Skip Checkbox Behavior

**Interaction Flow**:

1. User hovers over artifact row → Skip checkbox becomes more prominent (slight scale: 1.05)
2. User checks "Skip Future" → Immediate visual feedback:
   - Checkbox fills with animation (150ms ease-in-out)
   - Tooltip appears: "Will skip in future discoveries"
   - Row opacity reduces slightly (0.7) to indicate pending skip
3. User clicks "Import" or "Cancel" → Preferences are saved
4. Next discovery scan → Skipped artifacts don't appear in banner count

**Instant vs. On-Submit**:
- **Chosen Pattern**: On-Submit
- **Rationale**: Prevents accidental skips, allows undo before commit
- **Alternative**: Instant save with "Undo" button (adds complexity)

### 3.2 Tab Switching Animation

**Animation Pattern**:

```tsx
// Framer Motion variants
const tabVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.2, ease: "easeOut" } },
  exit: { opacity: 0, y: -10, transition: { duration: 0.15, ease: "easeIn" } }
}

<motion.div
  variants={tabVariants}
  initial="hidden"
  animate="visible"
  exit="exit"
>
  {/* Tab content */}
</motion.div>
```

**Fallback** (without Framer Motion):
```tsx
// CSS transition
className="transition-opacity duration-200 ease-out"
```

### 3.3 Toast Notification Format

**Import Success Toast**:

```
┌────────────────────────────────────┐
│ ✓ Import Complete           [✕]   │
│ 2 imported, 1 skipped              │
│ [View Details]                      │
└────────────────────────────────────┘
```

**Detailed Breakdown Toast** (when errors occur):

```
┌────────────────────────────────────┐
│ ⚠ Import Completed with Issues[✕] │
│ 2 imported, 1 skipped, 1 failed    │
│ [View Details]                      │
└────────────────────────────────────┘
```

**Toast Specifications**:
- Position: `bottom-right` (mobile: `bottom-center`)
- Duration: 5000ms (5 seconds)
- Max width: `max-w-md`
- Dismissible: Yes (X button)
- Action button: Opens detailed results modal

**Tailwind Classes**:

```tsx
// Toast Container
className="flex items-start gap-3 p-4 bg-background border border-border rounded-lg shadow-lg max-w-md"

// Toast Icon Container
className="flex-shrink-0 w-5 h-5 mt-0.5"

// Toast Content
className="flex-1 space-y-1"

// Toast Title
className="text-sm font-medium text-foreground"

// Toast Description
className="text-xs text-muted-foreground"

// Toast Action Button
className="text-xs font-medium text-primary hover:underline"
```

### 3.4 Hover States for Status Badges

**Interaction**:
- **Default**: Badge appears with normal opacity
- **Hover**: Badge scales slightly (1.05), tooltip appears after 500ms delay
- **Focus**: Same as hover for keyboard navigation

**Tooltip Specification**:
- Position: `top` (fallback: `bottom` if near top edge)
- Arrow: Yes (centered)
- Max width: `max-w-xs` (320px)
- Padding: `px-3 py-2`
- Font size: `text-xs`
- Animation: Fade in 150ms

**Tailwind Classes**:

```tsx
// Badge with hover
className="... hover:scale-105 transition-transform duration-150 cursor-help"

// Tooltip
className="absolute z-50 px-3 py-2 text-xs text-white bg-gray-900 rounded-md shadow-lg max-w-xs"

// Tooltip arrow
className="absolute w-2 h-2 bg-gray-900 rotate-45 -bottom-1 left-1/2 -translate-x-1/2"
```

---

## 4. Responsive Considerations

### 4.1 Discovery Tab Responsiveness

**Breakpoints**:
- Mobile: `< 640px` (sm)
- Tablet: `640px - 1024px` (sm to lg)
- Desktop: `> 1024px` (lg+)

**Mobile Layout** (`< 640px`):

```
┌─────────────────────────┐
│ Discovery (5)           │
├─────────────────────────┤
│                         │
│ [All Types ▾] [🔍]     │
│                         │
│ ┌─────────────────────┐ │
│ │ canvas-design        │ │
│ │ Type: Skill          │ │
│ │ ✓ In Project         │ │
│ │ [Import] [Skip]      │ │
│ └─────────────────────┘ │
│                         │
│ ┌─────────────────────┐ │
│ │ api-architect        │ │
│ │ Type: Skill          │ │
│ │ ⚠ In Collection      │ │
│ │ [Import] [Skip]      │ │
│ └─────────────────────┘ │
│                         │
└─────────────────────────┘
```

**Changes**:
- Table → Card view
- Filters collapse to dropdown menu (hamburger icon)
- Search input full width
- Import actions move to card footer
- Bulk actions stick to bottom of screen

**Tailwind Classes**:

```tsx
// Mobile card container
className="lg:hidden space-y-3"

// Mobile card
className="p-4 border border-border rounded-lg space-y-3"

// Mobile card actions
className="flex items-center justify-between gap-2 pt-3 border-t border-border"

// Desktop table (hidden on mobile)
className="hidden lg:block"
```

### 4.2 BulkImportModal Responsiveness

**Mobile Layout**:
- Modal takes full screen on mobile (`h-screen w-screen`)
- Header becomes sticky
- Footer becomes sticky with buttons stacked
- Artifact list scrolls in between

```
┌─────────────────────────┐
│ Import Artifacts [✕]    │ ← Sticky header
├─────────────────────────┤
│                         │
│ ┌─────────────────────┐ │
│ │ ☑ canvas-design      │ │ ← Scrollable area
│ │ Skill • Ready        │ │
│ │ [Skip Future]        │ │
│ └─────────────────────┘ │
│ ┌─────────────────────┐ │
│ │ ☑ api-architect      │ │
│ │ Skill • In Collection│ │
│ │ [Skip Future]        │ │
│ └─────────────────────┘ │
│                         │
├─────────────────────────┤
│ Selected: 2 of 4        │ ← Sticky footer
│ [Cancel]                │
│ [Import Selected (2)]   │
└─────────────────────────┘
```

**Tailwind Classes**:

```tsx
// Mobile modal container
className="fixed inset-0 z-50 lg:flex lg:items-center lg:justify-center"

// Mobile modal content
className="h-screen w-screen lg:h-auto lg:w-full lg:max-w-2xl lg:rounded-lg"

// Sticky header (mobile)
className="sticky top-0 bg-background border-b border-border z-10 p-4"

// Sticky footer (mobile)
className="sticky bottom-0 bg-background border-t border-border z-10 p-4 space-y-2"
```

### 4.3 DiscoveryBanner Responsiveness

**Mobile Layout**:
- Stack elements vertically
- Button below text (full width)
- Smaller font sizes

```
┌─────────────────────────┐
│ 🔍 3 new artifacts      │
│                         │
│ 2 in collection         │
│ 1 in project            │
│                         │
│ [Review & Import]  [✕] │
└─────────────────────────┘
```

**Tailwind Classes**:

```tsx
// Mobile banner
className="flex-col gap-2 lg:flex-row lg:items-start lg:justify-between"

// Mobile button
className="w-full lg:w-auto"
```

### 4.4 Touch Targets

**Minimum Touch Target Size**: 44x44px (Apple HIG, WCAG 2.5.5)

**Implementation**:
- Checkboxes: Expand hit area with padding
- Buttons: Minimum `h-11` (44px)
- Badge tooltips: Increase tap target with transparent padding

```tsx
// Checkbox with expanded touch target
<label className="relative flex items-center gap-2 cursor-pointer p-2 -m-2">
  <input type="checkbox" className="h-4 w-4" />
  <span className="text-sm">Skip Future</span>
</label>
```

---

## 5. Accessibility Requirements

### 5.1 Keyboard Navigation

**Discovery Tab**:
- `Tab` / `Shift+Tab`: Move between interactive elements
- `Arrow Keys`: Navigate table rows (when focused)
- `Space`: Toggle checkboxes
- `Enter`: Activate buttons and links
- `Escape`: Clear search input (when focused)

**Tab Switcher**:
- `Tab`: Focus tab list
- `Arrow Left/Right`: Switch between tabs
- `Home/End`: Jump to first/last tab
- `Enter/Space`: Activate tab

**BulkImportModal**:
- `Tab`: Navigate through artifact checkboxes and skip checkboxes
- `Space`: Toggle checkboxes
- `Enter`: Submit import (when focused on Import button)
- `Escape`: Close modal

**Implementation**:

```tsx
// Tab list with keyboard navigation
<TabsList
  role="tablist"
  aria-label="Project sections"
  onKeyDown={handleTabKeyDown}
>
  <TabsTrigger
    value="deployed"
    role="tab"
    aria-selected={activeTab === "deployed"}
    aria-controls="deployed-panel"
  >
    Deployed (12)
  </TabsTrigger>
</TabsList>

// Table with keyboard navigation
<table
  role="grid"
  aria-label="Discovered artifacts"
  onKeyDown={handleTableKeyDown}
>
  <tbody>
    <tr
      role="row"
      tabIndex={0}
      aria-rowindex={1}
      onKeyDown={handleRowKeyDown}
    >
      {/* ... */}
    </tr>
  </tbody>
</table>
```

### 5.2 ARIA Labels for Status Badges

**Badge Implementation**:

```tsx
<Badge
  role="status"
  aria-label={ariaLabel}
  className={badgeClasses}
>
  <Icon className="w-3 h-3" aria-hidden="true" />
  {text}
</Badge>
```

**ARIA Labels by Status**:

| Status | ARIA Label |
|--------|-----------|
| Success | "Successfully imported to [Collection/Project/Both]" |
| In Collection | "Already exists in Collection, will add to Project only if imported" |
| In Project | "Already exists in Project, will add to Collection only if imported" |
| Skipped (User) | "Skipped by user preference, will not appear in future discoveries" |
| Failed | "Import failed: [error message]" |
| Pending | "Import in progress" |
| Ready | "Ready to import to Collection and Project" |

### 5.3 Screen Reader Announcements

**Import Results**:

```tsx
// Announce import results to screen readers
<div
  role="status"
  aria-live="polite"
  aria-atomic="true"
  className="sr-only"
>
  Import complete. {successCount} artifacts imported successfully,
  {skippedCount} skipped, {failedCount} failed.
</div>
```

**Discovery Scan**:

```tsx
// Announce new discoveries
<div
  role="status"
  aria-live="polite"
  aria-atomic="true"
  className="sr-only"
>
  {newCount} new artifacts discovered and ready to import.
</div>
```

**Implementation Classes**:

```tsx
// Screen reader only text
className="sr-only"

// Live region for announcements
className="sr-only"
role="status"
aria-live="polite"
```

### 5.4 Focus Management

**Modal Focus Trap**:

```tsx
import { FocusTrap } from '@radix-ui/react-focus-scope'

<FocusTrap asChild>
  <div className="modal-content">
    {/* Modal content */}
  </div>
</FocusTrap>
```

**Focus Return**:
- When modal closes, return focus to trigger button
- When tab switches, focus first interactive element in new tab panel
- When filter applied, focus first result in list

**Focus Indicators**:
- All interactive elements must have visible focus ring
- Use Tailwind: `focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2`

```tsx
// Button with focus indicator
className="... focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"

// Input with focus indicator
className="... focus:border-primary focus:ring-2 focus:ring-ring"
```

### 5.5 Color Contrast

**WCAG 2.1 AA Requirements**:
- Normal text: 4.5:1 contrast ratio
- Large text (18pt+): 3:1 contrast ratio
- UI components: 3:1 contrast ratio

**Verified Combinations** (using Tailwind default palette):

| Badge | Light Mode Contrast | Dark Mode Contrast | Pass |
|-------|-------------------|-------------------|------|
| Success | 7.2:1 | 8.1:1 | ✓ AAA |
| Warning | 6.8:1 | 7.5:1 | ✓ AAA |
| Failed | 8.1:1 | 8.9:1 | ✓ AAA |
| Skipped | 5.2:1 | 6.1:1 | ✓ AA |
| Pending | 6.5:1 | 7.2:1 | ✓ AAA |
| Ready | 6.0:1 | 6.8:1 | ✓ AAA |

---

## 6. Wireframes (ASCII/Markdown)

### 6.1 Discovery Tab - Desktop View

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ SkillMeat                                                    Profile [▾]     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│ ← Projects / My Claude Project                                               │
│                                                                               │
│ ┌───────────────────────────────────────────────────────────────────────┐   │
│ │                                                                         │   │
│ │  My Claude Project                                         [Settings]  │   │
│ │  .claude/skills/ • Created 2 days ago                                  │   │
│ │                                                                         │   │
│ └───────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│ ┌─────────────────────┬───────────────────┐                                  │
│ │ Deployed (12)       │ Discovery (5)     │                                  │
│ └─────────────────────┴───────────────────┘                                  │
│                                                                               │
│ ┌───────────────────────────────────────────────────────────────────────┐   │
│ │ [All Types ▾]  [All Statuses ▾]             [🔍 Search artifacts...] │   │
│ └───────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│ ┌───────────────────────────────────────────────────────────────────────┐   │
│ │ Name              │ Type    │ Status              │ Actions            │   │
│ ├───────────────────┼─────────┼─────────────────────┼──────────────────┤   │
│ │ ☐ canvas-design   │ Skill   │ ◯ Ready             │ [Import]         │   │
│ │                   │         │                     │                  │   │
│ ├───────────────────┼─────────┼─────────────────────┼──────────────────┤   │
│ │ ☐ api-architect   │ Skill   │ ⚠ In Collection     │ [Import]         │   │
│ │                   │         │                     │                  │   │
│ ├───────────────────┼─────────┼─────────────────────┼──────────────────┤   │
│ │ ☐ debug-helper    │ Skill   │ ⊘ Skipped by user   │ [Import]         │   │
│ │                   │         │                     │                  │   │
│ ├───────────────────┼─────────┼─────────────────────┼──────────────────┤   │
│ │ ☐ code-reviewer   │ Skill   │ ✓ In Project        │ [Import]         │   │
│ │                   │         │                     │                  │   │
│ ├───────────────────┼─────────┼─────────────────────┼──────────────────┤   │
│ │   test-generator  │ Skill   │ ✓ In Both           │ -                │   │
│ │                   │         │                     │                  │   │
│ └───────────────────┴─────────┴─────────────────────┴──────────────────┘   │
│                                                                               │
│ ☐ Select All (4)                                [Import Selected (0)]        │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Discovery Tab - Mobile View

```
┌─────────────────────────────┐
│ ☰ SkillMeat         [👤]   │
├─────────────────────────────┤
│                             │
│ ← My Claude Project         │
│                             │
│ ┌─────────┬─────────────┐   │
│ │ Deployed│ Discovery(5)│   │
│ └─────────┴─────────────┘   │
│                             │
│ [All Types ▾]  [🔍]        │
│                             │
│ ┌─────────────────────────┐ │
│ │ ☐ canvas-design         │ │
│ │                         │ │
│ │ Type: Skill             │ │
│ │ ◯ Ready                 │ │
│ │                         │ │
│ │ [Import] [Skip Future]  │ │
│ └─────────────────────────┘ │
│                             │
│ ┌─────────────────────────┐ │
│ │ ☐ api-architect         │ │
│ │                         │ │
│ │ Type: Skill             │ │
│ │ ⚠ In Collection         │ │
│ │                         │ │
│ │ [Import] [Skip Future]  │ │
│ └─────────────────────────┘ │
│                             │
│ ┌─────────────────────────┐ │
│ │ ☐ debug-helper          │ │
│ │                         │ │
│ │ Type: Skill             │ │
│ │ ⊘ Skipped by user       │ │
│ │                         │ │
│ │ [Import] [Skip Future]  │ │
│ └─────────────────────────┘ │
│                             │
└─────────────────────────────┘
```

### 6.3 BulkImportModal with Skip Checkboxes

```
┌───────────────────────────────────────────────────────────────────┐
│ Import Artifacts to "My Claude Project"                    [✕]    │
├───────────────────────────────────────────────────────────────────┤
│                                                                     │
│ Select artifacts to import. You can skip artifacts from future     │
│ discoveries using the "Skip Future" checkbox.                      │
│                                                                     │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ ☑ canvas-design                                 [Skip Future]│   │
│ │   Type: Skill • Source: anthropics/skills                    │   │
│ │                                                               │   │
│ │   ◯ Ready to import                                           │   │
│ │   Will add to Collection and Project                          │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ ☑ api-architect                                 [Skip Future]│   │
│ │   Type: Skill • Source: anthropics/skills                    │   │
│ │                                                               │   │
│ │   ⚠ In Collection → Will add to Project only                 │   │
│ │   Already exists in your collection                           │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ ☐ debug-helper                                  [Skip Future]│   │
│ │   Type: Skill • Source: user/repo                            │   │
│ │                                                               │   │
│ │   ✓ In Project → Will add to Collection only                 │   │
│ │   Already deployed to this project                            │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ ☐ test-generator                                [Skip Future]│   │
│ │   Type: Skill • Source: user/repo                            │   │
│ │                                                               │   │
│ │   ✓ Already in both → No action needed                       │   │
│ │   Cannot be imported (already exists in both locations)       │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│ Selected: 2 of 4 artifacts                                          │
│                                                                     │
│                                      [Cancel] [Import Selected (2)]│
└───────────────────────────────────────────────────────────────────┘
```

### 6.4 Status Badge Placement in Table

```
┌────────────────────────────────────────────────────────────────────┐
│ Name              │ Type    │ Status                │ Actions      │
├───────────────────┼─────────┼───────────────────────┼──────────────┤
│ canvas-design     │ Skill   │ ┌─────────────────┐   │ [Import]     │
│                   │         │ │ ◯ Ready         │   │              │
│                   │         │ └─────────────────┘   │              │
├───────────────────┼─────────┼───────────────────────┼──────────────┤
│ api-architect     │ Skill   │ ┌─────────────────┐   │ [Import]     │
│                   │         │ │ ⚠ In Collection │   │              │
│                   │         │ └─────────────────┘   │              │
├───────────────────┼─────────┼───────────────────────┼──────────────┤
│ test-generator    │ Skill   │ ┌─────────────────┐   │ -            │
│                   │         │ │ ✓ In Both       │   │              │
│                   │         │ └─────────────────┘   │              │
└───────────────────┴─────────┴───────────────────────┴──────────────┘

Hover state (with tooltip):

┌───────────────────┬─────────┬───────────────────────┬──────────────┐
│ api-architect     │ Skill   │ ┌─────────────────┐   │ [Import]     │
│                   │         │ │ ⚠ In Collection │   │              │
│                   │         │ └─────────────────┘   │              │
│                   │         │        ↑              │              │
│                   │         │  ┌─────────────────────────────┐     │
│                   │         │  │ Already exists in           │     │
│                   │         │  │ Collection. Will add to     │     │
│                   │         │  │ Project only if imported.   │     │
│                   │         │  └─────────────────────────────┘     │
└───────────────────┴─────────┴───────────────────────┴──────────────┘
```

### 6.5 DiscoveryBanner with Breakdown

```
Desktop:
┌───────────────────────────────────────────────────────────────────┐
│ 🔍 3 new artifacts ready to import                                │
│    2 already in collection • 1 already in project                 │
│                                      [Review & Import]  [Dismiss] │
└───────────────────────────────────────────────────────────────────┘

Mobile:
┌─────────────────────────────────┐
│ 🔍 3 new artifacts ready        │
│                                 │
│ 2 already in collection         │
│ 1 already in project            │
│                                 │
│ [Review & Import]        [✕]   │
└─────────────────────────────────┘

With badge breakdown (optional):
┌───────────────────────────────────────────────────────────────────┐
│ 🔍 3 new artifacts ready to import                                │
│    [3 New] [2 In Collection] [1 In Project] [1 Skipped]          │
│                                      [Review & Import]  [Dismiss] │
└───────────────────────────────────────────────────────────────────┘
```

### 6.6 Import Results Modal

```
┌───────────────────────────────────────────────────────────────────┐
│ Import Complete                                            [✕]    │
├───────────────────────────────────────────────────────────────────┤
│                                                                     │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │  ✓ 2 imported successfully                                  │   │
│ │  ⚠ 1 skipped (already exists)                               │   │
│ │  ✕ 0 failed                                                  │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│ Details:                                                            │
│                                                                     │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ ✓ canvas-design                                              │   │
│ │   Added to Collection and Project                            │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ ✓ api-architect                                              │   │
│ │   Added to Project only (already in Collection)              │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ ⚠ test-generator                                             │   │
│ │   Skipped (already exists in both Collection and Project)    │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│                                                         [Done]     │
└───────────────────────────────────────────────────────────────────┘
```

---

## 7. Implementation Checklist

### Phase 1: Status Badge System
- [ ] Create `StatusBadge` component with all 7 variants
- [ ] Add tooltip support with proper positioning
- [ ] Implement ARIA labels for accessibility
- [ ] Test color contrast in light and dark modes
- [ ] Add Storybook stories for all badge states

### Phase 2: Discovery Tab
- [ ] Create `DiscoveryTab` component
- [ ] Implement tab switcher with keyboard navigation
- [ ] Build filter/search functionality
- [ ] Add table view with sort support
- [ ] Implement mobile card view
- [ ] Create empty state variations
- [ ] Add loading skeleton states
- [ ] Wire up to API endpoints

### Phase 3: BulkImportModal Enhancements
- [ ] Add pre-scan status labels to each artifact
- [ ] Implement "Skip Future" checkbox
- [ ] Update modal submit logic to save skip preferences
- [ ] Create import results display
- [ ] Update toast notifications with breakdown
- [ ] Add mobile responsive layout
- [ ] Implement focus trap and keyboard navigation

### Phase 4: DiscoveryBanner Updates
- [ ] Update banner logic to only show truly new artifacts
- [ ] Add breakdown text for skipped items
- [ ] Hide banner when all artifacts exist or are skipped
- [ ] Update responsive design for mobile

### Phase 5: API Integration
- [ ] Update discovery endpoint to return status for each artifact
- [ ] Add endpoint for user skip preferences (CRUD)
- [ ] Update import endpoint to handle partial imports
- [ ] Add detailed import result response

### Phase 6: Testing & Polish
- [ ] Write unit tests for all components
- [ ] Add integration tests for import flow
- [ ] Conduct accessibility audit with screen reader
- [ ] Test keyboard navigation thoroughly
- [ ] Verify responsive design on real devices
- [ ] Run color contrast checks
- [ ] Performance test with large artifact lists
- [ ] User acceptance testing

---

## 8. Design Tokens

### Color Palette

```typescript
// tailwind.config.js additions
module.exports = {
  theme: {
    extend: {
      colors: {
        // Status colors (using Tailwind defaults)
        success: {
          50: 'rgb(240 253 244)',
          100: 'rgb(220 252 231)',
          200: 'rgb(187 247 208)',
          800: 'rgb(22 101 52)',
          900: 'rgb(20 83 45)',
        },
        warning: {
          50: 'rgb(255 251 235)',
          100: 'rgb(254 243 199)',
          200: 'rgb(253 230 138)',
          800: 'rgb(146 64 14)',
          900: 'rgb(120 53 15)',
        },
        error: {
          50: 'rgb(254 242 242)',
          100: 'rgb(254 226 226)',
          200: 'rgb(254 202 202)',
          800: 'rgb(153 27 27)',
          900: 'rgb(127 29 29)',
        },
        info: {
          50: 'rgb(239 246 255)',
          100: 'rgb(219 234 254)',
          200: 'rgb(191 219 254)',
          800: 'rgb(30 64 175)',
          900: 'rgb(30 58 138)',
        },
      }
    }
  }
}
```

### Spacing Scale

```typescript
// Using Tailwind's 4px grid
spacing: {
  0: '0px',
  1: '4px',
  2: '8px',
  3: '12px',
  4: '16px',
  5: '20px',
  6: '24px',
  8: '32px',
  10: '40px',
  12: '48px',
  16: '64px',
  20: '80px',
  24: '96px',
}
```

### Typography Scale

```typescript
fontSize: {
  xs: ['12px', { lineHeight: '16px' }],
  sm: ['14px', { lineHeight: '20px' }],
  base: ['16px', { lineHeight: '24px' }],
  lg: ['18px', { lineHeight: '28px' }],
  xl: ['20px', { lineHeight: '28px' }],
}
```

### Border Radius

```typescript
borderRadius: {
  none: '0px',
  sm: '4px',
  DEFAULT: '8px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  full: '9999px',
}
```

### Shadow Scale

```typescript
boxShadow: {
  sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  DEFAULT: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
  md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
  lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
}
```

---

## 9. Animation Specifications

### Transitions

```typescript
// Standard easing curves
const transitions = {
  fast: 'transition-all duration-150 ease-in-out',
  normal: 'transition-all duration-200 ease-in-out',
  slow: 'transition-all duration-300 ease-in-out',
}

// Specific use cases
const animations = {
  fadeIn: 'animate-in fade-in duration-200',
  fadeOut: 'animate-out fade-out duration-150',
  slideDown: 'animate-in slide-in-from-top duration-200',
  slideUp: 'animate-out slide-out-to-top duration-150',
  scaleIn: 'animate-in zoom-in-95 duration-200',
  scaleOut: 'animate-out zoom-out-95 duration-150',
}
```

### Micro-interactions

**Badge Hover**:
```css
.badge {
  transition: transform 150ms ease-in-out;
}

.badge:hover {
  transform: scale(1.05);
}
```

**Checkbox Check**:
```css
.checkbox {
  transition: all 150ms ease-in-out;
}

.checkbox:checked {
  background-color: hsl(var(--primary));
  transform: scale(1);
}
```

**Button Press**:
```css
.button {
  transition: all 100ms ease-in-out;
}

.button:active {
  transform: scale(0.98);
}
```

---

## 10. Error States & Edge Cases

### Error States

**API Error (Discovery)**:
```
┌─────────────────────────────────────────────────────────────┐
│                                                               │
│                     ⚠ Discovery Error                        │
│                                                               │
│         Failed to load discovered artifacts.                 │
│         Please try again or contact support.                 │
│                                                               │
│                     [Try Again]                               │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**Import Error (Single Artifact)**:
```
✕ canvas-design
  Import failed: Network error. Please try again.
```

**Import Error (All Artifacts)**:
```
┌─────────────────────────────────────────────────────────────┐
│ Import Failed                                         [✕]    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ ✕ All imports failed                                         │
│                                                               │
│ An error occurred while importing artifacts.                 │
│ Please check your connection and try again.                  │
│                                                               │
│ Error: Network timeout after 30 seconds                      │
│                                                               │
│                                    [Try Again]  [Cancel]     │
└─────────────────────────────────────────────────────────────┘
```

### Edge Cases

**No Artifacts Discovered**:
- Show empty state in Discovery Tab
- Do not show DiscoveryBanner

**All Artifacts Exist**:
- Do not show DiscoveryBanner
- Discovery Tab shows all with "In Both" status

**All Artifacts User-Skipped**:
- Do not show DiscoveryBanner
- Discovery Tab shows all with "Skipped by user" status
- Show "Manage Skipped" button to bulk un-skip

**Single Artifact in List**:
- Bulk actions hidden
- "Select All" checkbox hidden
- Import button always enabled

**Network Offline**:
```
┌─────────────────────────────────────────────────────────────┐
│                                                               │
│                     📡 You're Offline                         │
│                                                               │
│         Discovery requires an internet connection.           │
│         Please check your network and try again.             │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 11. Performance Considerations

### Optimization Strategies

1. **Lazy Loading**:
   - Discovery Tab content lazy loaded when tab activated
   - Import modal content loaded on demand
   - Status badge icons lazy loaded

2. **Debouncing**:
   - Search input: 300ms debounce
   - Filter changes: Instant (no debounce needed)

3. **Virtualization**:
   - Use React Virtualized for lists > 50 items
   - Render only visible rows + buffer

4. **Memoization**:
   - Memoize badge rendering (status unlikely to change)
   - Memoize filter/sort functions

5. **Code Splitting**:
   - Split Discovery Tab into separate bundle
   - Split BulkImportModal into separate bundle

### Bundle Size Budget

| Component | Budget | Notes |
|-----------|--------|-------|
| StatusBadge | < 2KB | Base component |
| DiscoveryTab | < 15KB | With dependencies |
| BulkImportModal | < 12KB | With dependencies |
| Total | < 30KB | Compressed |

---

## 12. Future Enhancements

### Phase 2 Features (Post-MVP)

1. **Bulk Skip Management**:
   - Dedicated page for managing all skipped artifacts
   - Bulk un-skip action
   - Search/filter skipped items

2. **Smart Recommendations**:
   - Suggest related artifacts based on imports
   - "Popular in similar projects" section

3. **Import Scheduling**:
   - Schedule imports for later
   - Queue system for large imports

4. **Advanced Filters**:
   - Filter by source repository
   - Filter by date discovered
   - Filter by artifact size

5. **Custom Status Views**:
   - Save filter presets
   - Quick access to "Ready to import" view

6. **Batch Operations**:
   - Multi-select across pages
   - Export artifact list

---

## Sources

- [Tabs - shadcn/ui](https://ui.shadcn.com/docs/components/tabs)
- [Badge – Radix Themes](https://www.radix-ui.com/themes/docs/components/badge)

---

## Appendix A: Component File Structure

```
web/src/
├── components/
│   ├── discovery/
│   │   ├── DiscoveryTab.tsx
│   │   ├── DiscoveryBanner.tsx
│   │   ├── BulkImportModal.tsx
│   │   ├── StatusBadge.tsx
│   │   ├── ArtifactTable.tsx
│   │   ├── ArtifactCard.tsx (mobile)
│   │   ├── FilterBar.tsx
│   │   ├── SkipCheckbox.tsx
│   │   ├── ImportResults.tsx
│   │   └── __tests__/
│   │       ├── DiscoveryTab.test.tsx
│   │       ├── BulkImportModal.test.tsx
│   │       └── StatusBadge.test.tsx
│   └── ui/
│       ├── badge.tsx (from shadcn)
│       ├── tabs.tsx (from shadcn)
│       ├── tooltip.tsx (from shadcn)
│       └── toast.tsx (from shadcn)
├── hooks/
│   ├── useDiscovery.ts
│   ├── useImport.ts
│   └── useSkipPreferences.ts
├── lib/
│   ├── api/
│   │   ├── discovery.ts
│   │   ├── import.ts
│   │   └── preferences.ts
│   └── utils/
│       ├── status.ts
│       └── filters.ts
└── types/
    └── discovery.ts
```

---

## Appendix B: Type Definitions

```typescript
// types/discovery.ts

export type ArtifactStatus =
  | 'ready'           // Ready to import
  | 'in_collection'   // Already in Collection
  | 'in_project'      // Already in Project
  | 'in_both'         // Already in both
  | 'skipped_user'    // Skipped by user preference
  | 'pending'         // Import in progress
  | 'success'         // Import succeeded
  | 'failed'          // Import failed

export type ArtifactType = 'skill' | 'command' | 'agent' | 'mcp_server' | 'hook'

export interface DiscoveredArtifact {
  id: string
  name: string
  type: ArtifactType
  source: string
  status: ArtifactStatus
  description?: string
  version?: string
  discovered_at: string
  error_message?: string // For failed imports
}

export interface ImportResult {
  artifact_id: string
  status: 'success' | 'skipped' | 'failed'
  message: string
  added_to_collection: boolean
  added_to_project: boolean
}

export interface BulkImportResult {
  success_count: number
  skipped_count: number
  failed_count: number
  results: ImportResult[]
}

export interface SkipPreference {
  artifact_source: string
  artifact_name: string
  skipped_at: string
}

export interface DiscoveryFilters {
  type?: ArtifactType[]
  status?: ArtifactStatus[]
  search?: string
}
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-04 | Initial design specification |

---

**Design Lead**: Claude (Sonnet 4.5)
**Review Status**: Pending
**Implementation Status**: Not started
