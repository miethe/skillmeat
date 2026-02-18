# Design System Architecture & Dependency Graph

## Visual Dependency Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│ Application Layer (React Components)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ContentPane ─┬─→ MarkdownEditor                                │
│               ├─→ SplitPreview                                  │
│               ├─→ FrontmatterDisplay                            │
│               └─→ FileTree                                      │
│                                                                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│ Component Layer (shadcn/ui Primitives)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Button  ┐                                                       │
│  ScrollArea ├─→ [Composition]                                    │
│  Skeleton   │                                                    │
│  Alert  ┘                                                        │
│                                                                   │
│  Collapsible (CollapsibleTrigger, CollapsibleContent)          │
│  Tabs (TabsList, TabsTrigger, TabsContent)                     │
│  Dialog, Card, Badge, etc. [30 total primitives]               │
│                                                                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│ Radix UI Layer (Unstyled Accessible Primitives)                │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  @radix-ui/react-collapsible    (CollapsiblePrimitive)         │
│  @radix-ui/react-scroll-area    (ScrollAreaPrimitive)          │
│  @radix-ui/react-tabs          (TabsPrimitive)                 │
│  @radix-ui/react-dialog        (DialogPrimitive)               │
│  @radix-ui/react-slot          (SlotComposition)               │
│  @radix-ui/react-dropdown-menu (MenuPrimitive)                 │
│  [+12 more unstyled components]                                │
│                                                                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│ Styling & Theming Layer                                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ CSS Variables (14 theme tokens)                          │  │
│  │ ├─ --background / --foreground                          │  │
│  │ ├─ --primary / --primary-foreground                     │  │
│  │ ├─ --secondary / --secondary-foreground                 │  │
│  │ ├─ --accent / --accent-foreground                       │  │
│  │ ├─ --muted / --muted-foreground                         │  │
│  │ ├─ --destructive / --destructive-foreground             │  │
│  │ ├─ --card / --card-foreground                           │  │
│  │ ├─ --popover / --popover-foreground                     │  │
│  │ ├─ --border, --input, --ring, --radius                  │  │
│  │ └─ Light mode root + Dark mode .dark class              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Tailwind CSS Configuration (tailwind.config.js)         │  │
│  │ ├─ Color Mapping (var(--primary) → primary)             │  │
│  │ ├─ Custom Animations (accordion, collapsible)           │  │
│  │ ├─ Border Radius (lg, md, sm)                           │  │
│  │ ├─ Font Families (system-ui stack)                      │  │
│  │ └─ Typography Plugin (@tailwindcss/typography)          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Global Styles (app/globals.css)                         │  │
│  │ ├─ Base layer (border colors, body defaults)            │  │
│  │ ├─ Utilities (.sr-only, .scrollbar-hide)                │  │
│  │ ├─ Theme dark mode selectors (.dark {...})              │  │
│  │ └─ @tailwind directives                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│ Content & Editor Libraries                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Markdown Rendering:                                             │
│  ├─ react-markdown (9.0.1) ──→ parses markdown to React        │
│  ├─ remark-gfm (4.0.0) ──────→ GitHub Flavored Markdown plugin│
│  └─ @tailwindcss/typography ─→ .prose styling for output       │
│                                                                   │
│  Code Editor (CodeMirror 6):                                     │
│  ├─ @codemirror/state (6.4.1) ────────→ EditorState mgmt       │
│  ├─ @codemirror/view (6.35.0) ────────→ DOM rendering & themes │
│  ├─ @codemirror/lang-markdown (6.3.1)─→ Markdown syntax        │
│  ├─ @codemirror/commands (6.7.1) ─────→ undo/redo/keymaps      │
│  └─ @codemirror/autocomplete (6.18.3)─→ Optional: completions  │
│                                                                   │
│  Icons:                                                           │
│  └─ lucide-react (0.451.0) ──→ SVG icon components             │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│ Build & Runtime (Framework Layer)                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  TypeScript (5.6.3) ──────────→ Type safety                     │
│  Next.js (15.0.3) ────────────→ App Router, server components  │
│  React (19.0.0) ──────────────→ Component model                │
│  React-DOM (19.0.0) ──────────→ Browser rendering              │
│  Tailwind CSS (3.4.14) ───────→ CSS compilation                │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Usage Dependencies

### ContentPane Dependencies

```
ContentPane
├─ Props:
│  ├─ path: string
│  ├─ content: string
│  ├─ isEditing: boolean
│  ├─ editedContent: string
│  └─ callbacks: onEditStart, onEditChange, onSave, onCancel
│
├─ UI Components:
│  ├─ Button (ghost, default variants)
│  ├─ ScrollArea
│  ├─ Skeleton
│  ├─ Alert / AlertDescription / AlertTitle
│  └─ HTML <pre>, <nav>, <div>
│
├─ Child Components:
│  ├─ SplitPreview (for markdown files)
│  └─ FrontmatterDisplay (when frontmatter exists)
│
├─ External Libraries:
│  ├─ lucide-react (icons)
│  ├─ @/lib/utils (cn() function)
│  └─ @/lib/frontmatter (parsing utilities)
│
└─ CSS Classes:
   ├─ Tailwind utilities (flex, h-full, min-w-0, etc.)
   ├─ Theme variables (muted-foreground, accent, etc.)
   └─ Animations (none in ContentPane itself)
```

### FileTree Dependencies

```
FileTree
├─ UI Components:
│  ├─ Button (ghost, icon variants)
│  └─ Skeleton
│
├─ Child Components:
│  └─ TreeNode (recursive)
│
├─ External Libraries:
│  ├─ lucide-react (ChevronRight, ChevronDown, Folder, File*)
│  └─ @/lib/utils (cn() function)
│
├─ Accessibility:
│  ├─ role="tree"
│  ├─ role="treeitem"
│  ├─ Roving tabindex for keyboard navigation
│  ├─ aria-level, aria-expanded, aria-selected
│  └─ aria-setsize, aria-posinset
│
├─ Keyboard Support:
│  ├─ Arrow Up/Down (navigate)
│  ├─ Arrow Left/Right (collapse/expand)
│  ├─ Enter/Space (select/toggle)
│  ├─ Home/End (first/last)
│  └─ Focus visible ring styling
│
└─ CSS Classes:
   ├─ Tailwind utilities (grid, padding, gap)
   ├─ Theme variables (accent, muted-foreground)
   └─ Focus ring (focus-visible:ring-2)
```

### SplitPreview Dependencies

```
SplitPreview
├─ Child Components:
│  ├─ MarkdownEditor (left side, edit mode only)
│  └─ Raw markdown rendering (right side, always visible)
│
├─ UI Components:
│  └─ ScrollArea (for preview pane)
│
├─ External Libraries:
│  ├─ react-markdown (9.0.1)
│  ├─ remark-gfm (4.0.0)
│  └─ @tailwindcss/typography (.prose classes)
│
├─ CSS Classes:
│  ├─ prose prose-sm (markdown styling)
│  ├─ dark:prose-invert (dark mode)
│  ├─ prose-headings:break-words (word breaking)
│  ├─ prose-pre:overflow-x-auto (code block scroll)
│  └─ Tailwind utilities (flex, gap, min-w-0)
│
└─ Responsive:
   ├─ Mobile: stacked (flex-col)
   └─ Desktop (lg+): side-by-side (lg:flex-row)
```

### MarkdownEditor Dependencies

```
MarkdownEditor
├─ External Libraries:
│  ├─ @codemirror/state (6.4.1)
│  ├─ @codemirror/view (6.35.0)
│  ├─ @codemirror/lang-markdown (6.3.1)
│  ├─ @codemirror/commands (6.7.1)
│  └─ @codemirror/autocomplete (6.18.3) [optional]
│
├─ CSS Variables (via EditorView.theme):
│  ├─ --background
│  ├─ --foreground
│  ├─ --accent
│  ├─ --muted
│  └─ --muted-foreground
│
├─ Theme Detection:
│  └─ window.matchMedia('(prefers-color-scheme: dark)')
│
├─ Features:
│  ├─ Markdown syntax highlighting
│  ├─ Undo/redo with history
│  ├─ Line wrapping
│  ├─ Read-only mode support
│  └─ onChange callback
│
└─ CSS:
   └─ CodeMirror classes (.cm-content, .cm-cursor, .cm-gutters)
```

### FrontmatterDisplay Dependencies

```
FrontmatterDisplay
├─ UI Components:
│  ├─ Collapsible / CollapsibleTrigger / CollapsibleContent
│  └─ Button (ghost variant)
│
├─ External Libraries:
│  ├─ lucide-react (ChevronDown, ChevronUp)
│  └─ @/lib/utils (cn() function)
│
├─ Animations:
│  └─ animate-collapsible-down / animate-collapsible-up
│
└─ CSS Classes:
   ├─ Tailwind utilities (p, rounded, border, bg)
   ├─ Theme variables (border, muted, foreground)
   └─ Custom animations (0.2s ease-out)
```

---

## CSS Variable Consumption Map

```
Component Layer            │ CSS Variables Used
──────────────────────────┼────────────────────────────────────
Button                    │ --primary, --primary-foreground
                          │ --secondary, --secondary-foreground
                          │ --destructive, --destructive-foreground
                          │ --accent, --accent-foreground
                          │ --input, --ring
──────────────────────────┼────────────────────────────────────
ScrollArea                │ --background (via Radix)
──────────────────────────┼────────────────────────────────────
Alert                     │ --foreground, --border
                          │ Custom: amber-500/50, amber-50 (override)
──────────────────────────┼────────────────────────────────────
Collapsible               │ --border, --muted, --foreground
──────────────────────────┼────────────────────────────────────
MarkdownEditor            │ --background, --foreground
                          │ --accent, --muted, --muted-foreground
──────────────────────────┼────────────────────────────────────
Prose (Markdown)          │ All 14 variables (via Tailwind)
──────────────────────────┼────────────────────────────────────
FileTree                  │ --accent, --accent-foreground
                          │ --muted-foreground, --foreground
                          │ --ring (focus visible)
──────────────────────────┼────────────────────────────────────
Global (body)             │ --background, --foreground
```

---

## Theme Mode Switch Flow

```
┌─────────────────────────────────────────────────────┐
│ User Preference or System Settings                   │
│ (prefers-color-scheme: light/dark)                  │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│ Root Element <html> or <body>                       │
│ Add/Remove: class="dark"                            │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│ CSS Cascade                                          │
│ :root { --primary: 222.2 47.4% 11.2%; ... }        │
│ .dark { --primary: 210 40% 98%; ... }               │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│ Components Read Variables                            │
│ className="bg-primary text-primary-foreground"     │
│ → Tailwind compiles: bg-[hsl(var(--primary))]      │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│ CodeMirror Theme Selection (MarkdownEditor)         │
│ isDarkMode = window.matchMedia(...).matches        │
│ → Apply: isDarkMode ? darkTheme : lightTheme       │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│ Rendered Output (Light or Dark Mode)                │
└─────────────────────────────────────────────────────┘
```

---

## Data Flow: Edit → Save

```
ContentPane (isEditing=false, editedContent='')
│
├─ User clicks Edit button
│  └─ onEditStart() callback
│      └─ Parent sets isEditing=true
│
├─ isEditing=true, editedContent updated
│  └─ Renders SplitPreview with MarkdownEditor
│
├─ User types in MarkdownEditor
│  └─ MarkdownEditor onChange fires
│      └─ onEditChange(newContent) callback
│          └─ Parent updates editedContent
│
├─ Preview updates in real-time (SplitPreview watches isEditing + editedContent)
│
├─ User clicks Save button
│  └─ onSave(editedContent) callback
│      ├─ API call to save content
│      ├─ isSaving=true (loading state)
│      └─ onCancel() callback after success
│
└─ isEditing=false, back to view mode
   └─ Renders SplitPreview in read-only mode (preview only)
```

---

## Animation Sequence

### Collapsible (FrontmatterDisplay)

```
Closed State (height: 0)
    │
    ├─ keyframe: collapsible-down
    │  ├─ from: { height: 0, opacity: 0 }
    │ └─ to: { height: var(--radix-collapsible-content-height), opacity: 1 }
    │
    ▼
Open State (height: var(...), opacity: 1)
    │
    ├─ duration: 0.2s
    ├─ easing: ease-out
    │
    ▼
    Fully Expanded
    │
    ├─ keyframe: collapsible-up (reverse)
    │  ├─ from: { height: var(...), opacity: 1 }
    │  └─ to: { height: 0, opacity: 0 }
    │
    ▼
Closed State (height: 0, opacity: 0)
```

---

## Accessibility Tree (FileTree)

```
<div role="tree" aria-label="File browser">
  ├─ <div role="treeitem" aria-level="1" aria-expanded="true">
  │  ├─ Folder icon
  │  ├─ "src" label
  │  └─ <div role="group">
  │     ├─ <div role="treeitem" aria-level="2" aria-expanded="false">
  │     │  ├─ File icon
  │     │  └─ "index.ts" label
  │     └─ <div role="treeitem" aria-level="2" aria-expanded="false">
  │        ├─ File icon
  │        └─ "utils.ts" label
  └─ <div role="treeitem" aria-level="1" aria-expanded="false">
     ├─ Folder icon
     └─ "tests" label
```

**Keyboard Navigation**:
- ↓/↑: Next/previous visible item (roving tabindex)
- →: Expand folder (if collapsed) or move to first child
- ←: Collapse folder (if expanded) or move to parent
- Home/End: First/last item
- Enter/Space: Select file or toggle folder

---

## Export Checklist

### Files to Export
- [ ] `/components/ui/*` - All 30 primitive components
- [ ] `/components/editor/markdown-editor.tsx`
- [ ] `/components/editor/split-preview.tsx`
- [ ] `/components/entity/content-pane.tsx`
- [ ] `/components/entity/file-tree.tsx`
- [ ] `/components/entity/frontmatter-display.tsx`
- [ ] `/lib/utils.ts` - cn() utility
- [ ] `/lib/frontmatter.ts` - Parsing utilities
- [ ] `/app/globals.css` - Theme definitions
- [ ] `tailwind.config.js` - Configuration
- [ ] `components.json` - shadcn config
- [ ] `package.json` - Dependencies

### Dependencies to Include
- [ ] react (19.0.0+)
- [ ] react-dom (19.0.0+)
- [ ] next (15.0.3+) or remove if no SSR needed
- [ ] tailwindcss (3.4.14+)
- [ ] @tailwindcss/typography (0.5.19+)
- [ ] @radix-ui/react-* (all 6 packages)
- [ ] lucide-react (0.451.0+)
- [ ] react-markdown (9.0.1+)
- [ ] remark-gfm (4.0.0+)
- [ ] @codemirror/* (4 core packages)
- [ ] class-variance-authority (0.7.0+)
- [ ] clsx (2.1.1+)
- [ ] tailwind-merge (2.5.4+)

### Configuration to Export
- [ ] CSS variable definitions (light + dark modes)
- [ ] Tailwind color mapping
- [ ] Custom animation keyframes
- [ ] Typography plugin configuration
- [ ] Border radius calculations
- [ ] Font stack definitions
