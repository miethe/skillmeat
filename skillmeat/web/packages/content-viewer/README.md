# @skillmeat/content-viewer

A collection of reusable React components for viewing, editing, and navigating file content. Provides an adapter abstraction pattern that decouples components from any specific backend API, allowing flexible integration with custom data sources.

## Overview

This package was extracted from the SkillMeat web application during a UI refactoring effort. It provides production-ready components for:

- **File tree browser** — Hierarchical navigation with keyboard support
- **File content viewer** — Display files with markdown editing and split preview
- **Frontmatter display** — Collapsible YAML frontmatter viewer
- **Markdown editor** — CodeMirror-based editor with live preview
- **Utilities** — Frontmatter parsing, README extraction, and more

The package uses an **adapter pattern** to remain backend-agnostic. You implement a simple `ContentViewerAdapter` interface and connect your own data-fetching hooks, making the components reusable across different APIs and applications.

## Installation

Install as a workspace dependency in your pnpm monorepo:

```bash
pnpm add @skillmeat/content-viewer
```

Or import directly from the workspace:

```typescript
import { FileTree, ContentPane } from '@skillmeat/content-viewer';
```

## Quick Start

### 1. Create an Adapter

Implement the `ContentViewerAdapter` interface by wrapping your application's data-fetching hooks:

```typescript
// lib/my-content-viewer-adapter.ts
import type { ContentViewerAdapter, AdapterHookOptions } from '@skillmeat/content-viewer';
import { useFetchFileTree, useFetchFileContent } from '@/hooks';

export const myAdapter: ContentViewerAdapter = {
  useFileTree(artifactId: string, options?: AdapterHookOptions) {
    // Wrap your hook and normalize the return shape
    const result = useFetchFileTree(artifactId, {
      enabled: options?.enabled !== false,
    });

    return {
      data: result.data,
      isLoading: result.isLoading,
      error: result.error ?? null,
    };
  },

  useFileContent(artifactId: string, filePath: string, options?: AdapterHookOptions) {
    const result = useFetchFileContent(artifactId, filePath, {
      enabled: options?.enabled !== false,
    });

    return {
      data: result.data,
      isLoading: result.isLoading,
      error: result.error ?? null,
    };
  },
};
```

### 2. Provide the Adapter

Wrap your component tree with `ContentViewerProvider`:

```typescript
// app/layout.tsx
import { ContentViewerProvider } from '@skillmeat/content-viewer';
import { myAdapter } from '@/lib/my-content-viewer-adapter';

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <ContentViewerProvider adapter={myAdapter}>
      {children}
    </ContentViewerProvider>
  );
}
```

### 3. Use Components

Now components can fetch data through your adapter:

```typescript
// components/MyViewer.tsx
'use client';

import { useState } from 'react';
import { FileTree, ContentPane } from '@skillmeat/content-viewer';

export function MyViewer({ artifactId }: { artifactId: string }) {
  const [selectedPath, setSelectedPath] = useState<string | null>(null);

  return (
    <div className="flex h-screen gap-4">
      <div className="w-64 border-r">
        <FileTree
          entityId={artifactId}
          files={[]} // Loaded via adapter
          selectedPath={selectedPath}
          onSelect={setSelectedPath}
        />
      </div>
      <div className="flex-1">
        <ContentPane
          path={selectedPath}
          content={null} // Loaded via adapter
          isLoading={false}
          onSave={(content) => console.log('Save:', content)}
        />
      </div>
    </div>
  );
}
```

## Components API

### FileTree

A hierarchical file browser with keyboard navigation and selection support.

**Props:**

```typescript
interface FileTreeProps {
  entityId: string;              // Unique identifier for the entity (used as adapter key)
  files: FileNode[];             // Array of file tree nodes
  selectedPath: string | null;   // Currently selected file path
  onSelect: (path: string) => void; // Called when user selects a file
  onAddFile?: () => void;        // Optional: called when user clicks "Add File"
  onDeleteFile?: (path: string) => void; // Optional: called when user deletes a file
  isLoading?: boolean;           // Show loading skeleton
  readOnly?: boolean;            // Hide create/delete buttons (default: false)
  ariaLabel?: string;            // Accessible label (default: "File browser")
}
```

**Features:**

- Expandable/collapsible directories
- File type icons (markdown, code, JSON, etc.)
- Full keyboard navigation (arrows, home/end, enter/space)
- ARIA tree pattern with roving tabindex
- Optional file creation and deletion
- Read-only mode for view-only interfaces

**Example:**

```typescript
<FileTree
  entityId="skill-123"
  files={[
    { name: 'src', type: 'directory', path: 'src', children: [
      { name: 'index.ts', type: 'file', path: 'src/index.ts' }
    ] }
  ]}
  selectedPath="src/index.ts"
  onSelect={(path) => handleSelect(path)}
  onDeleteFile={(path) => handleDelete(path)}
  readOnly={false}
/>
```

### ContentPane

Display and edit file content with syntax highlighting, markdown preview, and optional editing.

**Props:**

```typescript
interface ContentPaneProps {
  path: string | null;           // File path being displayed
  content: string | null;        // File content
  isLoading?: boolean;           // Show loading skeleton
  error?: string | null;         // Error message to display
  readOnly?: boolean;            // Hide edit/save buttons (default: false)
  truncationInfo?: TruncationInfo; // Info about truncated files
  // Lifted edit state
  isEditing?: boolean;           // True when in edit mode
  editedContent?: string;        // Content being edited
  onEditStart?: () => void;      // Called when user clicks "Edit"
  onEditChange?: (content: string) => void; // Called on every keystroke
  onSave?: (content: string) => void | Promise<void>; // Called on save
  onCancel?: () => void;         // Called on cancel
  ariaLabel?: string;            // Accessible label
}
```

**Features:**

- Breadcrumb navigation for file paths
- Syntax highlighting for code files
- Markdown split-preview (editor + preview) for `.md` files
- Optional frontmatter display
- Edit mode for supported file types
- Truncation warning for large files
- Lazy-loaded CodeMirror editor (bundle cost only on demand)

**Example:**

```typescript
const [isEditing, setIsEditing] = useState(false);
const [editedContent, setEditedContent] = useState('');

<ContentPane
  path="README.md"
  content={fileContent}
  isLoading={isLoading}
  isEditing={isEditing}
  editedContent={editedContent}
  onEditStart={() => {
    setEditedContent(fileContent);
    setIsEditing(true);
  }}
  onEditChange={setEditedContent}
  onSave={async (content) => {
    await saveFile(content);
    setIsEditing(false);
  }}
  onCancel={() => setIsEditing(false)}
/>
```

### FrontmatterDisplay

Display parsed YAML frontmatter as key-value pairs with collapsible state.

**Props:**

```typescript
interface FrontmatterDisplayProps {
  frontmatter: Record<string, unknown>; // Parsed YAML frontmatter object
  defaultCollapsed?: boolean;           // Start collapsed (default: false)
  className?: string;                   // Additional CSS classes
}
```

**Supports:**

- Strings, numbers, booleans, null
- Arrays (rendered as comma-separated values)
- Nested objects (one level, rendered indented)

**Example:**

```typescript
const frontmatter = {
  title: 'My Document',
  tags: ['react', 'typescript'],
  author: { name: 'John', email: 'john@example.com' }
};

<FrontmatterDisplay
  frontmatter={frontmatter}
  defaultCollapsed={false}
  className="mb-4"
/>
```

### SplitPreview

CodeMirror-based markdown editor with live preview. Lazy-loaded for performance.

**Props:**

```typescript
interface SplitPreviewProps {
  content: string;                      // Current content
  onChange: (content: string) => void;  // Called on every keystroke
  isEditing: boolean;                   // Control editor visibility
}
```

**Note:** This component is lazy-loaded and only fetched when rendering a markdown file in edit mode. Non-markdown files never trigger the download.

### MarkdownEditor

CodeMirror-based markdown editor for editing `.md` files. Also lazy-loaded.

**Props:**

```typescript
interface MarkdownEditorProps {
  content: string;                      // Current content
  onChange: (content: string) => void;  // Called on every keystroke
  readOnly?: boolean;                   // Disable editing (default: false)
}
```

## Adapter Pattern

The adapter pattern is the core architectural decision that makes this package reusable. Instead of baking in dependencies on a specific API client or state management library, components call `useContentViewerAdapter()` to access injected hooks.

### The `ContentViewerAdapter` Interface

```typescript
interface ContentViewerAdapter {
  useFileTree(
    artifactId: string,
    options?: AdapterHookOptions
  ): AdapterQueryResult<FileTreeResponse>;

  useFileContent(
    artifactId: string,
    filePath: string,
    options?: AdapterHookOptions
  ): AdapterQueryResult<FileContentResponse>;
}
```

### Implementing an Adapter

An adapter wraps your application's hooks and normalizes their return shape:

```typescript
const myAdapter: ContentViewerAdapter = {
  useFileTree(artifactId, options) {
    const result = myCustomHook(artifactId, { enabled: options?.enabled });
    return {
      data: result.data,
      isLoading: result.loading,
      error: result.err ?? null, // Normalize error field
    };
  },

  useFileContent(artifactId, filePath, options) {
    const result = myOtherHook(artifactId, filePath, {
      enabled: options?.enabled
    });
    return {
      data: result.data,
      isLoading: result.loading,
      error: result.err ?? null,
    };
  },
};
```

### Return Shape

All adapter hooks return `AdapterQueryResult<T>`:

```typescript
interface AdapterQueryResult<T> {
  data: T | undefined;        // Undefined while loading or on error
  isLoading: boolean;          // True during initial fetch
  error: Error | null;         // Non-null when fetch fails
}
```

## Utilities

### Frontmatter Parsing

```typescript
import {
  parseFrontmatter,   // Parse YAML + content
  stripFrontmatter,   // Remove YAML block
  detectFrontmatter,  // Check if content has YAML
} from '@skillmeat/content-viewer';

// Parse frontmatter and content separately
const { frontmatter, content } = parseFrontmatter(fileContent);

// Remove frontmatter before displaying
const contentWithoutFrontmatter = stripFrontmatter(fileContent);

// Check if file has frontmatter
if (detectFrontmatter(fileContent)) {
  // Show frontmatter display component
}
```

### README Utilities

```typescript
import {
  extractFirstParagraph,  // Get first paragraph from markdown
  extractFolderReadme,    // Find README in folder tree
} from '@skillmeat/content-viewer';

// Extract first paragraph for preview
const description = extractFirstParagraph(content);

// Find README.md in a folder
const readmeEntry = extractFolderReadme(fileTree, 'docs');
```

## Types

The package exports canonical type definitions for all data structures:

```typescript
import type {
  FileNode,                // A file or directory node
  FileTreeEntry,          // A catalog file tree entry
  FileTreeResponse,       // Catalog file tree API response
  FileContentResponse,    // Catalog file content API response
  ContentViewerAdapter,   // The adapter interface
  AdapterQueryResult,     // Normalized query result shape
  AdapterHookOptions,     // Common adapter hook options
} from '@skillmeat/content-viewer';
```

**FileNode:**

```typescript
interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  size?: number;              // File size in bytes
  children?: FileNode[];      // Directory contents
}
```

**FileTreeResponse (from API):**

```typescript
interface FileTreeResponse {
  entries: FileTreeEntry[];   // List of files/directories
  cached: boolean;            // Served from cache?
  cache_age_seconds?: number; // Cache age in seconds
}
```

**FileContentResponse (from API):**

```typescript
interface FileContentResponse {
  content: string;            // Decoded file content
  encoding: string;           // Encoding (usually "utf-8")
  size: number;               // File size in bytes
  sha: string;                // Git blob SHA
  truncated?: boolean;        // Content was truncated?
  original_size?: number;     // Original size before truncation
  cached: boolean;            // Served from cache?
  cache_age_seconds?: number; // Cache age in seconds
}
```

## Examples

### Modal Integration

Display a file viewer inside a modal dialog:

```typescript
'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { FileTree, ContentPane } from '@skillmeat/content-viewer';

export function ViewerModal({ artifactId, open, onClose }: Props) {
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState('');

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl h-96">
        <DialogHeader>
          <DialogTitle>View Files</DialogTitle>
        </DialogHeader>
        <div className="flex gap-4">
          <div className="w-64 border-r overflow-auto">
            <FileTree
              entityId={artifactId}
              files={[]} // Loaded via adapter
              selectedPath={selectedPath}
              onSelect={setSelectedPath}
              readOnly
            />
          </div>
          <div className="flex-1">
            <ContentPane
              path={selectedPath}
              content={null} // Loaded via adapter
              isEditing={isEditing}
              editedContent={editedContent}
              onEditStart={() => setIsEditing(true)}
              onEditChange={setEditedContent}
              onSave={async (content) => {
                // Handle save
                setIsEditing(false);
              }}
              onCancel={() => setIsEditing(false)}
            />
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

### Standalone Viewer

Use components without a modal:

```typescript
'use client';

import { useState } from 'react';
import { FileTree, ContentPane } from '@skillmeat/content-viewer';

export function FileViewer({ artifactId }: { artifactId: string }) {
  const [selectedPath, setSelectedPath] = useState<string | null>(null);

  return (
    <div className="grid grid-cols-3 gap-4 h-screen p-4">
      <div className="col-span-1 border rounded-lg overflow-hidden">
        <FileTree
          entityId={artifactId}
          files={[]}
          selectedPath={selectedPath}
          onSelect={setSelectedPath}
          readOnly
        />
      </div>
      <div className="col-span-2 border rounded-lg overflow-hidden">
        <ContentPane
          path={selectedPath}
          content={null}
          readOnly
        />
      </div>
    </div>
  );
}
```

### Custom Adapter Example (SkillMeat)

See SkillMeat's concrete implementation for reference:

```typescript
// In your application
import { skillmeatContentViewerAdapter, makeCatalogArtifactId } from '@/lib/content-viewer-adapter';
import { ContentViewerProvider } from '@skillmeat/content-viewer';

const artifactId = makeCatalogArtifactId(sourceId, artifactPath);

<ContentViewerProvider adapter={skillmeatContentViewerAdapter}>
  <FileTree artifactId={artifactId} />
</ContentViewerProvider>
```

The adapter encodes a composite key (sourceId + artifactPath) into a single string for the components to consume, making it easy to bridge between different identity schemes.

## Performance Considerations

### Lazy-Loaded Editor Bundle

The CodeMirror editor (used in `SplitPreview` and `MarkdownEditor`) is lazy-loaded and only fetched when needed:

- **Markdown files in edit mode**: Editor chunk downloaded
- **Non-markdown files**: Editor never downloaded
- **Read-only mode**: Editor chunk may still load for markdown files (preview uses a lighter markdown renderer)

This significantly reduces the initial bundle size for consumers. If you're only using `FileTree` and `ContentPane` for viewing, you may never download the editor.

### Component Structure

- **`FileTree`** - ~8 KB gzipped (fully bundled, no lazy loading)
- **`ContentPane`** - ~5 KB gzipped (fully bundled)
- **`FrontmatterDisplay`** - ~2 KB gzipped (fully bundled)
- **`SplitPreview` + `MarkdownEditor`** (lazy) - ~50 KB gzipped (on demand)

## Accessibility

All components follow WCAG 2.1 AA standards:

- **FileTree**: ARIA tree pattern with roving tabindex, keyboard navigation, labels
- **ContentPane**: Region landmarks, breadcrumb navigation, semantic HTML
- **FrontmatterDisplay**: Semantic structure with strong/emphasis for keys
- **Editor**: Full keyboard support and screen reader compatibility via CodeMirror

Test keyboard navigation with your screen reader before deploying.

## TypeScript

The package is fully typed with TypeScript. All components and utilities have complete type definitions. No `@ts-ignore` should be needed.

## License

See LICENSE file in the package root.
