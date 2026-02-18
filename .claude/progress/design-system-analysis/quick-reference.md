# Quick Reference: Design System & UI Primitives

---

## 1. CSS Variables Reference

### Color Tokens (HSL Format)

| Token | Light Mode | Dark Mode | Purpose |
|-------|------------|-----------|---------|
| `--background` | 0 0% 100% (white) | 222.2 84% 4.9% (dark) | Page background |
| `--foreground` | 222.2 84% 4.9% | 210 40% 98% | Text color |
| `--primary` | 222.2 47.4% 11.2% (navy) | 210 40% 98% (white) | Primary actions |
| `--primary-foreground` | 210 40% 98% | 222.2 47.4% 11.2% | Text on primary |
| `--secondary` | 210 40% 96.1% (gray) | 217.2 32.6% 17.5% | Secondary actions |
| `--secondary-foreground` | 222.2 47.4% 11.2% | 210 40% 98% | Text on secondary |
| `--accent` | 210 40% 96.1% (gray) | 217.2 32.6% 17.5% | Highlights |
| `--accent-foreground` | 222.2 47.4% 11.2% | 210 40% 98% | Text on accent |
| `--muted` | 210 40% 96.1% (gray) | 217.2 32.6% 17.5% | Disabled/inactive |
| `--muted-foreground` | 215.4 16.3% 46.9% (gray) | 215 20.2% 65.1% | Text on muted |
| `--destructive` | 0 84.2% 60.2% (red) | 0 62.8% 30.6% | Danger/delete |
| `--destructive-foreground` | 210 40% 98% | 210 40% 98% | Text on destructive |
| `--card` | 0 0% 100% | 222.2 84% 4.9% | Card backgrounds |
| `--card-foreground` | 222.2 84% 4.9% | 210 40% 98% | Card text |
| `--popover` | 0 0% 100% | 222.2 84% 4.9% | Popover backgrounds |
| `--popover-foreground` | 222.2 84% 4.9% | 210 40% 98% | Popover text |
| `--border` | 214.3 31.8% 91.4% | 217.2 32.6% 17.5% | Border color |
| `--input` | 214.3 31.8% 91.4% | 217.2 32.6% 17.5% | Input background |
| `--ring` | 222.2 84% 4.9% | 212.7 26.8% 83.9% | Focus ring |
| `--radius` | 0.5rem | 0.5rem | Border radius |

### Usage in Tailwind

```css
/* All accessible via Tailwind classes */
bg-primary           /* hsl(var(--primary)) */
text-foreground      /* hsl(var(--foreground)) */
border-border        /* hsl(var(--border)) */
ring-ring            /* hsl(var(--ring)) */
```

---

## 2. UI Primitives Inventory

### Core Primitives (Used in Content Components)

| Component | Export | Variants | Sizes | Purpose |
|-----------|--------|----------|-------|---------|
| **Button** | Button | default, ghost, outline, secondary, destructive, link | sm, default, lg, icon | Actions |
| **ScrollArea** | ScrollArea | — | — | Scrollable regions |
| **Skeleton** | Skeleton | — | — | Loading placeholders |
| **Alert** | Alert, AlertDescription, AlertTitle | default, destructive | — | Messages/warnings |
| **Collapsible** | Collapsible, CollapsibleTrigger, CollapsibleContent | — | — | Expandable sections |
| **Tabs** | Tabs, TabsList, TabsTrigger, TabsContent | — | — | Tabbed navigation |

### Additional Primitives (Available)

| Component | Export | Radix Base | Purpose |
|-----------|--------|-----------|---------|
| Card | Card, CardHeader, CardTitle, CardDescription, CardContent | — | Container |
| Badge | Badge | — | Labels/status |
| Input | Input | — | Text input |
| Label | Label | @radix-ui/react-label | Form labels |
| Checkbox | Checkbox | @radix-ui/react-checkbox | Checkboxes |
| RadioGroup | RadioGroup, RadioGroupItem | @radix-ui/react-radio-group | Radio buttons |
| Select | Select, SelectValue, SelectTrigger, SelectContent, SelectItem, SelectGroup, SelectLabel | @radix-ui/react-select | Dropdowns |
| DropdownMenu | DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, etc. | @radix-ui/react-dropdown-menu | Menu |
| Dialog | Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle, DialogDescription | @radix-ui/react-dialog | Modal |
| Popover | Popover, PopoverTrigger, PopoverContent | @radix-ui/react-popover | Popover |
| Tooltip | Tooltip, TooltipTrigger, TooltipContent, TooltipProvider | @radix-ui/react-tooltip | Tooltips |
| Separator | Separator | @radix-ui/react-separator | Dividers |
| Textarea | Textarea | — | Text area |
| Accordion | Accordion, AccordionItem, AccordionTrigger, AccordionContent | @radix-ui/react-accordion | Accordion |
| Slider | Slider | @radix-ui/react-slider | Range input |
| Switch | Switch | @radix-ui/react-switch | Toggle |
| Progress | Progress | @radix-ui/react-progress | Progress bar |
| AlertDialog | AlertDialog, AlertDialogTrigger, AlertDialogContent, AlertDialogHeader, AlertDialogTitle, AlertDialogDescription, AlertDialogAction, AlertDialogCancel | @radix-ui/react-alert-dialog | Confirmation |
| Command | Command, CommandDialog, CommandInput, CommandList, CommandEmpty, CommandGroup, CommandItem, CommandSeparator, CommandShortcut | cmdk library | Command palette |
| Toaster | Toaster | sonner library | Toast notifications |
| Tooltip | Tooltip | @radix-ui/react-tooltip | Tooltips |
| Sheet | Sheet, SheetTrigger, SheetContent, SheetHeader, SheetTitle, SheetDescription | @radix-ui/react-dialog | Side sheet |

### Custom Components

| Component | File | Purpose |
|-----------|------|---------|
| TagInput | components/ui/tag-input.tsx | Tag input field |
| TagFilterPopover | components/ui/tag-filter-popover.tsx | Filter by tags |
| ToolFilterPopover | components/ui/tool-filter-popover.tsx | Filter by tools |

---

## 3. Content Component Breakdown

### ContentPane

| Aspect | Details |
|--------|---------|
| **File** | `components/entity/content-pane.tsx` |
| **Use Case** | Display file contents with optional editing |
| **Supports** | Markdown (split-view), text, code, YAML |
| **UI Primitives** | Button, ScrollArea, Skeleton, Alert |
| **Features** | Line numbers (optional), frontmatter display, truncation warning |
| **Modes** | View (read-only), Edit (markdown only) |
| **Props** | path, content, isLoading, error, readOnly, truncationInfo, isEditing, editedContent, onEditStart, onEditChange, onSave, onCancel |
| **State Lifted** | isEditing, editedContent (parent manages) |

### FileTree

| Aspect | Details |
|--------|---------|
| **File** | `components/entity/file-tree.tsx` |
| **Use Case** | Hierarchical file browser with keyboard navigation |
| **UI Primitives** | Button, Skeleton |
| **Features** | Expand/collapse, file type icons, roving tabindex, delete actions |
| **Keyboard** | Arrow keys, Enter/Space, Home/End |
| **A11y** | ARIA tree pattern, semantic HTML |
| **Props** | entityId, files, selectedPath, onSelect, onAddFile, onDeleteFile, isLoading, readOnly, ariaLabel |
| **State** | expandedPaths, focusedPath, visibleNodes (flattened) |

### FrontmatterDisplay

| Aspect | Details |
|--------|---------|
| **File** | `components/entity/frontmatter-display.tsx` |
| **Use Case** | Display parsed YAML frontmatter as collapsible section |
| **UI Primitives** | Collapsible, Button |
| **Features** | Collapse/expand animation, nested object rendering, array display |
| **Props** | frontmatter (object), defaultCollapsed (bool), className |
| **State** | isOpen (local state) |

### MarkdownEditor

| Aspect | Details |
|--------|---------|
| **File** | `components/editor/markdown-editor.tsx` |
| **Use Case** | CodeMirror-based markdown editor |
| **Libraries** | @codemirror/state, @codemirror/view, @codemirror/lang-markdown, @codemirror/commands |
| **Features** | Syntax highlighting, undo/redo, line wrapping, theme support |
| **Theming** | Auto-detects dark mode via matchMedia, applies theme on init |
| **Props** | initialContent, onChange, readOnly, className |
| **State** | editorRef (imperative) |

### SplitPreview

| Aspect | Details |
|--------|---------|
| **File** | `components/editor/split-preview.tsx` |
| **Use Case** | Markdown editor with live preview (side-by-side or stacked) |
| **Child Components** | MarkdownEditor, ReactMarkdown |
| **UI Primitives** | ScrollArea |
| **Libraries** | react-markdown, remark-gfm, @tailwindcss/typography |
| **Responsive** | Mobile: stacked (flex-col), Desktop: side-by-side (lg:flex-row) |
| **Props** | content, onChange, isEditing, className |
| **CSS** | .prose prose-sm prose-invert (dark mode) |

---

## 4. NPM Dependency Summary

### By Category

#### Styling & Theming
- **tailwindcss** (3.4.14) - Utility-first CSS framework
- **@tailwindcss/typography** (0.5.19) - Prose styling for markdown
- **tailwindcss-animate** (1.0.7) - Animation utilities
- **class-variance-authority** (0.7.0) - Type-safe variant management
- **clsx** (2.1.1) - Conditional classNames
- **tailwind-merge** (2.5.4) - Class merging (avoid conflicts)

#### UI Framework
- **@radix-ui/react-collapsible** (1.1.12)
- **@radix-ui/react-scroll-area** (1.2.10)
- **@radix-ui/react-tabs** (1.1.13)
- **@radix-ui/react-dialog** (1.1.15)
- **@radix-ui/react-slot** (1.2.4)
- **@radix-ui/react-dropdown-menu** (2.1.16)
- Plus 13 more @radix-ui packages

#### Content & Markdown
- **react-markdown** (9.0.1) - Parse markdown to React
- **remark-gfm** (4.0.0) - GitHub Flavored Markdown plugin

#### Code Editor
- **@codemirror/state** (6.4.1) - Editor state management
- **@codemirror/view** (6.35.0) - DOM rendering & themes
- **@codemirror/lang-markdown** (6.3.1) - Markdown language support
- **@codemirror/commands** (6.7.1) - Editor commands (undo/redo)
- **@codemirror/autocomplete** (6.18.3) - Optional autocomplete

#### Icons
- **lucide-react** (0.451.0) - SVG icon library

#### Framework
- **react** (19.0.0)
- **react-dom** (19.0.0)
- **next** (15.0.3)
- **typescript** (5.6.3)

#### Utilities
- **zod** (3.23.8) - Schema validation
- **clsx** (2.1.1) - Conditional className joining

---

## 5. Animation Reference

### Tailwind Custom Animations

| Animation | Duration | Easing | Used In | Keyframes |
|-----------|----------|--------|---------|-----------|
| `accordion-down` | 0.2s | ease-out | Accordion | height: 0 → var(--radix-accordion-content-height) |
| `accordion-up` | 0.2s | ease-out | Accordion | height: var(...) → 0 |
| `collapsible-down` | 0.2s | ease-out | Collapsible | height+opacity: 0,0 → var(...),1 |
| `collapsible-up` | 0.2s | ease-out | Collapsible | height+opacity: var(...),1 → 0,0 |
| `notification-pulse` | 0.5s | ease-in-out | Toast | scale: 1 → 1.1 → 1 |

---

## 6. Keyboard Navigation Reference

### FileTree

| Key | Behavior |
|-----|----------|
| ↑ | Move focus to previous visible item |
| ↓ | Move focus to next visible item |
| → | Expand folder (if collapsed) or move to first child |
| ← | Collapse folder (if expanded) or move to parent |
| Enter | Select file or toggle folder |
| Space | Select file or toggle folder |
| Home | Move focus to first item |
| End | Move focus to last visible item |

### MarkdownEditor (CodeMirror defaults)

| Key | Behavior |
|-----|----------|
| Ctrl/Cmd + Z | Undo |
| Ctrl/Cmd + Y | Redo |
| Tab | Indent |
| Shift + Tab | Dedent |
| Alt + ↑/↓ | Move line up/down |

---

## 7. Accessibility Features

### ARIA Attributes Used

| Attribute | Component | Purpose |
|-----------|-----------|---------|
| `role="tree"` | FileTree | Semantic tree structure |
| `role="treeitem"` | FileTree nodes | Individual tree items |
| `role="group"` | FileTree children | Group of children |
| `aria-level` | FileTree items | Hierarchy depth |
| `aria-expanded` | FileTree folders, Collapsible | Expansion state |
| `aria-selected` | FileTree items | Selection state |
| `aria-setsize` | FileTree items | Total items (visible) |
| `aria-posinset` | FileTree items | Position in set |
| `aria-label` | ContentPane, FileTree | Region/component labels |
| `aria-labelledby` | ContentPane | Associated breadcrumb ID |
| `aria-hidden` | Icons | Decorative elements |
| `aria-current="page"` | ContentPane breadcrumbs | Current file indicator |

### Focus Management

- **focus-visible ring**: `focus-visible:ring-2 focus-visible:ring-ring`
- **Roving tabindex**: FileTree manages single tabindex per level
- **Skip links**: Not visible but `sr-only` utility available

---

## 8. Class Name Patterns

### Common Tailwind Patterns in Components

```jsx
// Spacing & Layout
'flex h-full flex-col gap-4'
'min-h-0 min-w-0 flex-1'
'items-center justify-between'

// Colors (via CSS variables)
'text-foreground bg-background'
'text-muted-foreground'
'border-border'
'hover:bg-accent hover:text-accent-foreground'

// Animations
'transition-colors'
'animate-collapsible-down'

// Focus & Accessibility
'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'

// Responsive
'flex-col gap-4 lg:flex-row lg:gap-6'

// Dark Mode
'dark:bg-slate-900 dark:text-slate-50'

// State Classes
'disabled:opacity-50 disabled:pointer-events-none'
'[&>[data-radix-scroll-area-viewport]>div]:!block'  // Arbitrary CSS
```

---

## 9. Theme Detection & Switching

### Light Mode (Default)

```css
:root {
  --background: 0 0% 100%;
  --foreground: 222.2 84% 4.9%;
  /* 18 more variables */
}
```

### Dark Mode

```css
.dark {
  --background: 222.2 84% 4.9%;
  --foreground: 210 40% 98%;
  /* 18 more variables */
}
```

### Triggering Dark Mode

```html
<!-- Method 1: Class on root -->
<html class="dark">
  ...
</html>

<!-- Method 2: System preference (CodeMirror) -->
<script>
  const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  if (isDark) document.documentElement.classList.add('dark');
</script>
```

---

## 10. Common Gotchas & Solutions

### Issue: Markdown Content Not Wrapping

**Problem**: Long lines in prose don't wrap
**Solution**: Use `prose-headings:break-words prose-p:break-words` classes

### Issue: CodeMirror Theme Not Applying

**Problem**: Theme colors not visible
**Solution**: Ensure CSS variables are defined before editor init

### Issue: Focus Ring Not Visible

**Problem**: Focus indicator missing on tree items
**Solution**: Add `focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1`

### Issue: Collapsible Animation Choppy

**Problem**: Height transition stutters
**Solution**: Use CSS variable `var(--radix-collapsible-content-height)` (Radix provides this)

### Issue: Dark Mode Not Switching

**Problem**: Components still use light colors
**Solution**: Toggle `.dark` class on HTML root and re-render CodeMirror

---

## 11. Export Checklist by File Type

### TypeScript Components (`.tsx`)
```
[ ] components/ui/button.tsx
[ ] components/ui/scroll-area.tsx
[ ] components/ui/skeleton.tsx
[ ] components/ui/alert.tsx
[ ] components/ui/collapsible.tsx
[ ] components/ui/tabs.tsx
[ ] components/ui/card.tsx
[ ] components/ui/[25+ more]
[ ] components/entity/content-pane.tsx
[ ] components/entity/file-tree.tsx
[ ] components/entity/frontmatter-display.tsx
[ ] components/editor/markdown-editor.tsx
[ ] components/editor/split-preview.tsx
[ ] lib/utils.ts
[ ] lib/frontmatter.ts
```

### Configuration Files
```
[ ] tailwind.config.js
[ ] components.json
[ ] app/globals.css
```

### Package Management
```
[ ] package.json (with all deps)
[ ] pnpm-lock.yaml or package-lock.json
```

---

## 12. Version Compatibility Matrix

| Package | Min Version | Current | Compatibility |
|---------|------------|---------|---|
| React | 18.0.0 | 19.0.0 | ✓ (uses hooks) |
| React-DOM | 18.0.0 | 19.0.0 | ✓ |
| Next.js | 13.0.0 | 15.0.3 | ✓ (App Router only) |
| TypeScript | 5.0.0 | 5.6.3 | ✓ |
| Tailwind | 3.0.0 | 3.4.14 | ✓ |
| Node | 18.18.0 | — | ✓ |
| pnpm | 8.0.0 | 8.15.0 | ✓ |

---

## 13. Performance Metrics

| Component | Render Time | Bundle Size | Notes |
|-----------|------------|----------|-------|
| ContentPane | < 100ms | 15KB | Conditional markdown editor |
| FileTree | < 50ms | 12KB | Efficient roving tabindex |
| MarkdownEditor | 200-400ms | 180KB | CodeMirror adds bulk |
| SplitPreview | < 150ms | 45KB | Depends on content size |
| FrontmatterDisplay | < 30ms | 5KB | Simple collapsible |

---

## 14. Common Import Paths

```typescript
// UI Primitives
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

// Components
import { ContentPane } from '@/components/entity/content-pane';
import { FileTree } from '@/components/entity/file-tree';
import { FrontmatterDisplay } from '@/components/entity/frontmatter-display';
import { MarkdownEditor } from '@/components/editor/markdown-editor';
import { SplitPreview } from '@/components/editor/split-preview';

// Utilities
import { cn } from '@/lib/utils';
import { parseFrontmatter, stripFrontmatter } from '@/lib/frontmatter';

// Icons
import { Edit, Save, X, ChevronRight } from 'lucide-react';

// Libraries
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { EditorState, EditorView } from '@codemirror/state';
```

---

**Last Updated**: 2026-02-13
**Analysis Scope**: Content-related components
**Design System Version**: SkillMeat v0.3.0-alpha
