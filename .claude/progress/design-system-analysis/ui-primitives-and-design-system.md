# SkillMeat Web Design System & UI Primitives Analysis

**Status**: Complete Analysis
**Date**: 2026-02-13
**Scope**: Content-related components (ContentPane, FileTree, FrontmatterDisplay, MarkdownEditor, SplitPreview) and their design system dependencies

---

## Executive Summary

The SkillMeat web application uses a comprehensive design system built on:

- **UI Foundation**: shadcn/ui primitives (30 components) wrapping Radix UI
- **Styling**: Tailwind CSS 3.4.14 with CSS variables for theming
- **Component Architecture**: CVA (class-variance-authority) for variant management
- **Markdown Rendering**: react-markdown + remark-gfm with custom prose styling
- **Code Editor**: CodeMirror 6 with theme extensions
- **Icons**: Lucide React (0.451.0)

Content-related components rely on **12 core shadcn primitives** and **6 markdown/editor npm packages**. To extract a component library, all dependencies would need to ship with the foundations.

---

## Part 1: shadcn/UI Primitives Used

### A. Direct Usage in Content Components

#### 1. **Button** (`@/components/ui/button`)
- **Used in**: ContentPane, FileTree, FrontmatterDisplay
- **Variants**: `default`, `destructive`, `outline`, `secondary`, `ghost`, `link`
- **Sizes**: `default` (h-9), `sm` (h-8), `lg` (h-10), `icon` (h-9 w-9)
- **Purpose**: Edit/Save/Cancel buttons, delete actions, toggle buttons
- **CVA Structure**: Managed via `class-variance-authority` with base classes + variant combinations
- **Key Classes**: `focus-visible:ring-1 focus-visible:ring-ring`, `disabled:opacity-50`

**Example Usage**:
```tsx
<Button variant="ghost" size="sm" onClick={handleEditClick}>
  <Edit className="mr-2 h-4 w-4" />
  Edit
</Button>
```

#### 2. **ScrollArea** (`@/components/ui/scroll-area`)
- **Used in**: ContentPane, SplitPreview
- **Purpose**: Scrollable content regions with custom scrollbar styling
- **Radix Base**: `@radix-ui/react-scroll-area` (1.2.10)
- **Key Feature**: Wraps content to provide styled scrollbars that respect Tailwind theme
- **Usage Pattern**: Wraps overflow content; children auto-flex

**Example Usage**:
```tsx
<ScrollArea className="min-h-0 min-w-0 flex-1">
  <div className="p-4">
    {/* Content */}
  </div>
</ScrollArea>
```

#### 3. **Skeleton** (`@/components/ui/skeleton`)
- **Used in**: ContentPane, FileTree
- **Purpose**: Loading state placeholders with shimmer animation
- **Structure**: Simple div with animated background gradient
- **Usage**: Array of skeleton elements to show loading state shape

**Example Usage**:
```tsx
<Skeleton className="h-4 w-full" />
```

#### 4. **Alert** (`@/components/ui/alert`)
- **Components**: Alert, AlertDescription, AlertTitle
- **Used in**: ContentPane (error states, truncation banner)
- **Variants**: `default`, `destructive`
- **Structure**: Icon + Title + Description layout
- **Purpose**: Error messages, warnings, large file notifications

**Example Usage**:
```tsx
<Alert className="mb-4 border-amber-500/50 bg-amber-50 dark:bg-amber-950/30">
  <AlertTriangle className="h-4 w-4" />
  <AlertTitle>Large file truncated</AlertTitle>
  <AlertDescription>...</AlertDescription>
</Alert>
```

#### 5. **Collapsible** (`@/components/ui/collapsible`)
- **Components**: Collapsible, CollapsibleTrigger, CollapsibleContent
- **Used in**: FrontmatterDisplay
- **Radix Base**: `@radix-ui/react-collapsible` (1.1.12)
- **Purpose**: Expand/collapse frontmatter metadata section
- **Animation**: `animate-collapsible-down` / `animate-collapsible-up` (0.2s)
- **State**: Controlled via useState hook with `open` prop

**Example Usage**:
```tsx
<Collapsible open={isOpen} onOpenChange={setIsOpen}>
  <CollapsibleTrigger asChild>
    <Button variant="ghost">Toggle</Button>
  </CollapsibleTrigger>
  <CollapsibleContent className="animate-collapsible-down">
    {/* Content */}
  </CollapsibleContent>
</Collapsible>
```

#### 6. **Tabs** (`@/components/ui/tabs`)
- **Components**: Tabs, TabsList, TabsTrigger, TabsContent
- **Radix Base**: `@radix-ui/react-tabs` (1.1.13)
- **Used in**: Various modals and page layouts (not directly in ContentPane but referenced in related components)
- **Purpose**: Tabbed navigation interfaces
- **Pattern**: Controlled via state; triggers control active tab

---

### B. UI Primitives Installed but Not Used in Content Components

These are available in the project and used elsewhere:

- **Accordion** - Radix-based collapsible groups
- **AlertDialog** - Confirmation dialogs
- **Badge** - Label/status indicators
- **Card** - Container component (CardHeader, CardContent, CardDescription, CardTitle)
- **Checkbox** - Form input
- **Command** - Searchable command menu
- **Dialog** - Modal dialog base
- **DropdownMenu** - Radix-based menu
- **Input** - Text input field
- **Label** - Form label
- **Popover** - Radix popover
- **Progress** - Progress bar
- **RadioGroup** - Radio buttons
- **Select** - Select dropdown
- **Separator** - Visual divider
- **Sheet** - Side sheet panel
- **Switch** - Toggle switch
- **Table** - Table component
- **Textarea** - Multiline text input
- **Tooltip** - Radix-based tooltip
- **Toaster** - Toast notifications

**Custom Extensions**:
- **TagInput** - Custom tag input component
- **TagFilterPopover** - Custom filter component
- **ToolFilterPopover** - Custom filter component

---

## Part 2: CSS Variables & Theme System

### A. CSS Variable Definitions (globals.css)

The design system uses **14 CSS variables** for theming, defined in HSL color space. All are declared in `:root` (light mode) and `.dark` (dark mode).

#### Light Mode (`:root`)
```css
--background: 0 0% 100%;           /* White */
--foreground: 222.2 84% 4.9%;      /* Dark slate */
--card: 0 0% 100%;
--card-foreground: 222.2 84% 4.9%;
--popover: 0 0% 100%;
--popover-foreground: 222.2 84% 4.9%;
--primary: 222.2 47.4% 11.2%;      /* Navy */
--primary-foreground: 210 40% 98%; /* Off-white */
--secondary: 210 40% 96.1%;        /* Light gray */
--secondary-foreground: 222.2 47.4% 11.2%;
--muted: 210 40% 96.1%;            /* Light gray */
--muted-foreground: 215.4 16.3% 46.9%; /* Medium gray */
--accent: 210 40% 96.1%;           /* Light gray (subtle) */
--accent-foreground: 222.2 47.4% 11.2%;
--destructive: 0 84.2% 60.2%;      /* Red */
--destructive-foreground: 210 40% 98%;
--border: 214.3 31.8% 91.4%;       /* Light gray */
--input: 214.3 31.8% 91.4%;
--ring: 222.2 84% 4.9%;            /* Dark slate (focus ring) */
--radius: 0.5rem;                  /* Border radius */
```

#### Dark Mode (`.dark`)
```css
--background: 222.2 84% 4.9%;      /* Dark slate */
--foreground: 210 40% 98%;         /* Off-white */
--card: 222.2 84% 4.9%;
--card-foreground: 210 40% 98%;
/* ... (inverted color values) */
--radius: 0.5rem;                  /* Same as light */
```

### B. Tailwind Configuration Extensions

**File**: `tailwind.config.js`

#### Color Mapping
All CSS variables are mapped to Tailwind color names:
```javascript
colors: {
  border: 'hsl(var(--border))',
  input: 'hsl(var(--input))',
  ring: 'hsl(var(--ring))',
  background: 'hsl(var(--background))',
  foreground: 'hsl(var(--foreground))',
  primary: {
    DEFAULT: 'hsl(var(--primary))',
    foreground: 'hsl(var(--primary-foreground))',
  },
  secondary: { DEFAULT, foreground },
  destructive: { DEFAULT, foreground },
  muted: { DEFAULT, foreground },
  accent: { DEFAULT, foreground },
  popover: { DEFAULT, foreground },
  card: { DEFAULT, foreground },
}
```

#### Custom Animations (Keyframes)
```javascript
keyframes: {
  'accordion-down': { /* from height:0 to height:var(--radix-accordion-content-height) */ },
  'accordion-up': { /* from height:var(...) to height:0 */ },
  'collapsible-down': { /* height+opacity 0→var & 0→1 */ },
  'collapsible-up': { /* height+opacity var→0 & 1→0 */ },
  'notification-pulse': { /* scale 1 → 1.1 → 1 */ },
}
```

#### Border Radius
```javascript
borderRadius: {
  lg: 'var(--radius)',           /* 0.5rem */
  md: 'calc(var(--radius) - 2px)',  /* 0.25rem */
  sm: 'calc(var(--radius) - 4px)',  /* -0.125rem, typically ignored */
}
```

#### Font Configuration
```javascript
fontFamily: {
  sans: ['system-ui', '-apple-system', 'BlinkMacSystemFont', /* ... */]
}
```

### C. Base Layer Styles (globals.css)
```css
@layer base {
  * { @apply border-border; }           /* All elements use --border color */
  body { @apply bg-background text-foreground; }  /* Body bg/text */
}
```

### D. Utilities Layer (globals.css)
```css
.sr-only { /* Screen reader only utility */ }
.scrollbar-hide { /* Hide scrollbar while maintaining scroll */ }
```

---

## Part 3: NPM Dependencies for Content Rendering

### A. Markdown Rendering

#### 1. **react-markdown** (9.0.1)
- **Purpose**: Parse and render markdown strings as React components
- **Usage in**: SplitPreview, ContentPane (for markdown file preview)
- **Key Features**:
  - Component-based rendering (each markdown element → React component)
  - Plugin system via `remarkPlugins`
  - Custom component overrides supported
- **Used with**:
  ```tsx
  <ReactMarkdown remarkPlugins={[remarkGfm]}>
    {content}
  </ReactMarkdown>
  ```

#### 2. **remark-gfm** (4.0.0)
- **Purpose**: GitHub Flavored Markdown plugin for remark
- **Features**: Tables, strikethrough, autolinks, task lists
- **Integrated with**: react-markdown via `remarkPlugins` prop
- **Usage**:
  ```tsx
  <ReactMarkdown remarkPlugins={[remarkGfm]}>
    {markdownContent}
  </ReactMarkdown>
  ```

### B. Code Editor

#### 1. **@codemirror/state** (6.4.1)
- **Purpose**: EditorState management and extensions
- **Usage in**: MarkdownEditor component
- **Key Class**: `EditorState.create({ doc, extensions })`

#### 2. **@codemirror/view** (6.35.0)
- **Purpose**: EditorView (DOM rendering) and theming
- **Usage**: View initialization, theme extensions, line wrapping
- **Key Methods**:
  ```tsx
  EditorView.theme({...})  // CSS-in-JS theming
  EditorView.lineWrapping  // Enable word wrap
  EditorView.editable.of(!readOnly)  // Read-only toggle
  ```

#### 3. **@codemirror/lang-markdown** (6.3.1)
- **Purpose**: Markdown language support with syntax highlighting
- **Usage**: Extension passed to EditorState
  ```tsx
  markdown()  // In extensions array
  ```

#### 4. **@codemirror/commands** (6.7.1)
- **Purpose**: Standard editor commands (undo, redo, indent, etc.)
- **Usage**: Keymaps and command definitions
  ```tsx
  keymap.of([...defaultKeymap, ...historyKeymap])
  ```

#### 5. **@codemirror/autocomplete** (6.18.3)
- **Status**: Installed but not used in current content components
- **Purpose**: Autocomplete support (available for future enhancement)

#### 6. **@codemirror/language** (6.10.6)
- **Status**: Transitive dependency, provides language infrastructure
- **Purpose**: Base classes for language plugins

### C. Theme Support

**CodeMirror Theme Implementation**:
```tsx
// Light theme
const lightTheme = EditorView.theme({
  '&': { backgroundColor: 'hsl(var(--background))', ... },
  '.cm-content': { fontFamily: 'ui-monospace, ...', fontSize: '14px' },
  '.cm-cursor, .cm-dropCursor': { borderLeftColor: 'hsl(var(--foreground))' },
  '.cm-gutters': { backgroundColor: 'hsl(var(--muted))' },
})

// Dark theme
const darkTheme = EditorView.theme({ ... }, { dark: true })
```

**Dynamic Theme Selection**:
```tsx
const isDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
// Then: isDarkMode ? darkTheme : lightTheme
```

---

## Part 4: Prose/Markdown Styling

### A. Tailwind Typography Plugin

**Plugin**: `@tailwindcss/typography` (0.5.19)

Provides the `.prose` class system for styled markdown rendering.

#### Implementation in SplitPreview
```tsx
<div className="prose prose-sm max-w-none overflow-x-hidden break-words p-6
                 [overflow-wrap:anywhere] [word-break:break-word]
                 dark:prose-invert
                 prose-headings:break-words prose-p:break-words
                 prose-code:break-all prose-pre:overflow-x-auto">
  <ReactMarkdown remarkPlugins={[remarkGfm]}>
    {content}
  </ReactMarkdown>
</div>
```

#### Key Classes Used
- `.prose` - Base prose styling
- `.prose-sm` - Smaller variant (optimized for narrow columns)
- `.dark:prose-invert` - Dark mode colors
- `prose-headings:break-words` - Break heading text
- `prose-p:break-words` - Break paragraph text
- `prose-code:break-all` - Break inline code
- `prose-pre:overflow-x-auto` - Horizontal scroll for code blocks
- `[overflow-wrap:anywhere]` - Arbitrary utility for word wrapping
- `[word-break:break-word]` - Arbitrary utility for word breaking

#### Prose Defaults (via @tailwindcss/typography)
- Font size: ~1rem
- Line height: ~1.75
- Margins: Auto adjusted for headings, paragraphs, lists
- Colors: Inherit from design system CSS variables
- Code blocks: Monospace font, padding, background

---

## Part 5: Icon Library

### **lucide-react** (0.451.0)

**Purpose**: SVG icon library with React components

**Icons Used in Content Components**:
```
FileText, AlertCircle, AlertTriangle, Edit, ChevronRight, Save, X, ExternalLink
ChevronDown, ChevronUp, Folder, FolderOpen, FileCode, File, Braces, Trash2, Plus
```

**Usage Pattern**:
```tsx
import { FileText, Edit, ChevronRight } from 'lucide-react';

<FileText className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
```

**Configuration**:
- SVG-based (scales infinitely)
- Size controlled via `h-*` and `w-*` Tailwind classes
- Color via Tailwind color classes
- `aria-hidden="true"` for decorative icons

---

## Part 6: Utility Functions & Integration

### A. Class Merging Utility

**File**: `lib/utils.ts`

```typescript
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

**Purpose**: Merge Tailwind classes while avoiding conflicts
- `clsx`: Conditionally combine classNames
- `twMerge`: Remove conflicting Tailwind classes

**Usage Throughout**:
```tsx
className={cn(
  'flex items-center gap-1',
  isSelected && 'bg-accent text-accent-foreground',
  'focus-visible:outline-none focus-visible:ring-2'
)}
```

### B. CVA (class-variance-authority)

**Purpose**: Type-safe variant management for components

**Used in All UI Primitives**:
```typescript
const buttonVariants = cva(
  // Base classes
  'inline-flex items-center justify-center whitespace-nowrap rounded-md ...',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground shadow ...',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
      },
      size: {
        sm: 'h-8 rounded-md px-3 text-xs',
        default: 'h-9 px-4 py-2',
        icon: 'h-9 w-9',
      },
    },
  }
);
```

---

## Part 7: Component Architecture Patterns

### A. Composition Pattern (SplitPreview Example)

**Structure**:
```tsx
// Parent component
<SplitPreview isEditing={true}>
  // Uses child components internally
  {isEditing && <MarkdownEditor />}
  <div className="prose">
    <ReactMarkdown />
  </div>
</SplitPreview>
```

**Design Principles**:
1. Leaf components are primitive (MarkdownEditor, raw markdown)
2. Composite components orchestrate layout and state
3. State lifting to ContentPane for edit/view coordination

### B. Accessibility Integration

All components follow WCAG 2.1 AA standards:
- **Semantic HTML**: `role`, `aria-*` attributes
- **Focus Management**: `focus-visible` ring styling
- **Keyboard Navigation**: Arrow keys, Enter, Space, Home/End
- **Screen Readers**: `aria-label`, `aria-hidden`, `aria-current`
- **Color Contrast**: Ensured by CSS variable choices

**Example** (FileTree):
```tsx
<div role="tree" aria-label="File browser">
  <div role="treeitem" aria-level={level} aria-expanded={isExpanded}>
    {/* ... */}
  </div>
</div>
```

---

## Part 8: Dependencies Summary Table

| Category | Package | Version | Purpose | Status |
|----------|---------|---------|---------|--------|
| **UI Framework** | radix-ui (6 packages) | 1.x | Unstyled accessible components | Core |
| **Styling** | tailwindcss | 3.4.14 | Utility-first CSS | Core |
| **Styling** | tailwindcss-animate | 1.0.7 | Animation utilities | Core |
| **Styling** | @tailwindcss/typography | 0.5.19 | Prose styling | Core |
| **Styling** | class-variance-authority | 0.7.0 | Variant management | Core |
| **Styling** | tailwind-merge | 2.5.4 | Class merging utility | Core |
| **Styling** | clsx | 2.1.1 | Conditional classNames | Core |
| **Icons** | lucide-react | 0.451.0 | SVG icons | Core |
| **Markdown** | react-markdown | 9.0.1 | Markdown rendering | Content |
| **Markdown** | remark-gfm | 4.0.0 | GFM plugin for remark | Content |
| **Code Editor** | @codemirror/state | 6.4.1 | Editor state | Content |
| **Code Editor** | @codemirror/view | 6.35.0 | Editor DOM rendering | Content |
| **Code Editor** | @codemirror/lang-markdown | 6.3.1 | Markdown syntax highlighting | Content |
| **Code Editor** | @codemirror/commands | 6.7.1 | Editor commands | Content |
| **Code Editor** | @codemirror/autocomplete | 6.18.3 | Autocomplete (unused) | Available |
| **Framework** | next | 15.0.3 | Next.js App Router | Core |
| **Framework** | react | 19.0.0 | React library | Core |
| **Framework** | react-dom | 19.0.0 | React DOM binding | Core |
| **State Mgmt** | @tanstack/react-query | 5.90.9 | Server state caching | Not in components |

---

## Part 9: Design System Foundations Required for Export

### A. **Must Ship with Component Library**

1. **CSS Variables** (14 color variables + 1 border-radius)
   - Light mode definitions
   - Dark mode definitions
   - All in HSL color space

2. **Tailwind Configuration**
   - Color mapping to CSS variables
   - Custom animations (accordion, collapsible, notification-pulse)
   - Border radius calculations
   - Typography plugin enabled

3. **Base Styles**
   - `sr-only` utility class
   - `scrollbar-hide` utility class
   - Global `* { border-color: var(--border) }`
   - Body defaults

4. **UI Primitives (12 core)**
   - Button, ScrollArea, Skeleton
   - Alert (Alert, AlertDescription, AlertTitle)
   - Collapsible (Collapsible, CollapsibleTrigger, CollapsibleContent)
   - Custom extensions: TagInput, TagFilterPopover, ToolFilterPopover

5. **Radix UI Dependencies** (6 packages)
   - @radix-ui/react-collapsible
   - @radix-ui/react-scroll-area
   - @radix-ui/react-dialog (for modals in other components)
   - @radix-ui/react-tabs
   - @radix-ui/react-dropdown-menu
   - @radix-ui/react-slot

6. **Utility Functions**
   - `cn()` from `lib/utils.ts` (clsx + twMerge)

7. **Icon Library**
   - lucide-react (0.451.0)

### B. **Content-Specific Dependencies**

1. **Markdown Rendering**
   - react-markdown (9.0.1)
   - remark-gfm (4.0.0)
   - @tailwindcss/typography (0.5.19)

2. **Code Editor**
   - @codemirror/state (6.4.1)
   - @codemirror/view (6.35.0)
   - @codemirror/lang-markdown (6.3.1)
   - @codemirror/commands (6.7.1)

### C. **Framework Dependencies**

- next (15.0.3)
- react (19.0.0)
- react-dom (19.0.0)
- TypeScript (5.6.3)

---

## Part 10: Implementation Implications

### A. Token System Requirements

Extracted components will require:
1. **CSS Variable injection** - All 14 design tokens in root/dark
2. **Tailwind configuration merge** - Config must extend with provided animations/colors
3. **Global stylesheet import** - globals.css or equivalent
4. **Typography plugin** - For markdown rendering

### B. Theme Switching

- **Detection**: `window.matchMedia('(prefers-color-scheme: dark)')`
- **Application**: `.dark` class on root or parent
- **CodeMirror**: Must detect theme at editor initialization

### C. Accessibility Compliance

- WCAG 2.1 AA via Radix UI components
- Manual focus management in tree components (roving tabindex)
- Semantic HTML requirements
- Icon hiding via `aria-hidden`

### D. Performance Considerations

- **Code Editor**: Only loaded when editing markdown files
- **Markdown Rendering**: React components compiled at render time (not pre-compiled)
- **ScrollArea**: Uses Radix primitive (performant)
- **No virtual scrolling**: Current implementation renders full content

---

## Part 11: File Structure Checklist for Export

```
component-library/
├── components/
│   ├── ui/
│   │   ├── button.tsx
│   │   ├── scroll-area.tsx
│   │   ├── skeleton.tsx
│   │   ├── alert.tsx
│   │   ├── collapsible.tsx
│   │   ├── tabs.tsx
│   │   ├── card.tsx
│   │   ├── badge.tsx
│   │   ├── dialog.tsx
│   │   ├── input.tsx
│   │   ├── label.tsx
│   │   ├── separator.tsx
│   │   ├── textarea.tsx
│   │   ├── select.tsx
│   │   ├── dropdown-menu.tsx
│   │   ├── checkbox.tsx
│   │   ├── radio-group.tsx
│   │   ├── switch.tsx
│   │   ├── tabs.tsx
│   │   ├── tooltip.tsx
│   │   ├── popover.tsx
│   │   ├── tag-input.tsx
│   │   ├── tag-filter-popover.tsx
│   │   ├── tool-filter-popover.tsx
│   │   └── [others]
│   ├── content/
│   │   ├── content-pane.tsx
│   │   ├── file-tree.tsx
│   │   ├── frontmatter-display.tsx
│   │   └── split-preview.tsx
│   └── editor/
│       ├── markdown-editor.tsx
│       └── split-preview.tsx
├── lib/
│   └── utils.ts (cn() function)
├── tailwind.config.js
├── app/globals.css
├── components.json (shadcn config)
└── package.json (with all dependencies)
```

---

## Summary: Critical Exports Needed

To successfully extract and reuse ContentPane, FileTree, and related components:

### **Required**:
1. All 14 CSS variables (light + dark modes)
2. All 12 core UI primitives + 3 custom components
3. CodeMirror packages (4 core, 1 optional)
4. Markdown packages (2: react-markdown, remark-gfm)
5. Utility functions (cn, CVA)
6. Tailwind configuration with custom animations
7. @tailwindcss/typography for prose styling
8. Lucide React icon library
9. All Radix UI dependencies

### **Optional** (but breaking if removed):
- Custom animations (accordion, collapsible, notification-pulse)
- Border radius variable calculations
- Dark mode theme definitions

### **Version Constraints**:
- React: 19.0.0+
- Next.js: 15.0.3+ (if server component usage)
- TypeScript: 5.6.3+
- Tailwind: 3.4.14+
