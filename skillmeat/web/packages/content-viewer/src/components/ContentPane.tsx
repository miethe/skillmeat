'use client';

import { useState, useMemo, lazy, Suspense } from 'react';
import {
  FileText,
  AlertCircle,
  AlertTriangle,
  Edit,
  ChevronRight,
  Save,
  X,
  ExternalLink,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { Skeleton } from './ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from './ui/alert';
import { FrontmatterDisplay } from './FrontmatterDisplay';
import { parseFrontmatter, detectFrontmatter, stripFrontmatter } from '../lib/frontmatter';

/**
 * SplitPreview is lazy-loaded so that the CodeMirror editor bundle is only fetched
 * when a user enters edit mode on a markdown file.  Consumers who render ContentPane
 * in read-only mode (or for non-markdown files) will never download the editor chunk.
 */
const SplitPreview = lazy(() =>
  import('./SplitPreview').then((m) => ({ default: m.SplitPreview }))
);

// ============================================================================
// Types
// ============================================================================

/**
 * Truncation information for large files
 */
export interface TruncationInfo {
  /** Whether the content was truncated */
  truncated: boolean;
  /** Original file size in bytes (before truncation) */
  originalSize?: number;
  /** URL to view the full file (e.g., on GitHub) */
  fullFileUrl?: string;
}

export interface ContentPaneProps {
  path: string | null;
  content: string | null;
  isLoading?: boolean;
  error?: string | null;
  /**
   * When true, hides edit/save buttons and disables editing.
   * Content viewing with syntax highlighting remains functional.
   * @default false
   */
  readOnly?: boolean;
  /**
   * Truncation information for large files.
   * When provided and truncated is true, displays a warning banner.
   */
  truncationInfo?: TruncationInfo;
  // Lifted edit state from parent
  isEditing?: boolean;
  editedContent?: string;
  onEditStart?: () => void;
  onEditChange?: (content: string) => void;
  onSave?: (content: string) => void | Promise<void>;
  onCancel?: () => void;
  /**
   * Accessible label for the content pane region.
   * @default "File content viewer"
   */
  ariaLabel?: string;
  /**
   * Deprecated. Frontmatter is now automatically stripped from content
   * when FrontmatterDisplay component is shown (when frontmatter exists).
   * This prop is kept for backwards compatibility but no longer affects behavior.
   * @default false
   * @deprecated
   */
  showFrontmatter?: boolean;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Format bytes to human-readable string (e.g., "1.2 MB")
 */
function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const size = bytes / Math.pow(k, i);
  // Use 1 decimal place for KB and above, no decimals for bytes
  return i === 0 ? `${bytes} B` : `${size.toFixed(1)} ${sizes[i]}`;
}

/**
 * Check if a file is editable based on its extension
 */
function isEditableFile(path: string): boolean {
  const editableExtensions = [
    '.md',
    '.txt',
    '.json',
    '.ts',
    '.tsx',
    '.js',
    '.jsx',
    '.py',
    '.yml',
    '.yaml',
    '.toml',
  ];
  return editableExtensions.some((ext) => path.toLowerCase().endsWith(ext));
}

/**
 * Check if a file should use markdown editor (for .md files)
 */
function isMarkdownFile(path: string): boolean {
  return path.toLowerCase().endsWith('.md');
}

/**
 * Split path into breadcrumb segments
 */
function pathToBreadcrumbs(path: string): string[] {
  return path.split('/').filter(Boolean);
}

// ============================================================================
// Loading Skeletons
// ============================================================================

/**
 * Shown inside the Suspense boundary while the SplitPreview (CodeMirror) chunk
 * is being downloaded.  Mirrors the two-column split layout so the UI does not
 * shift once the editor mounts.
 */
function EditorLoadingSkeleton() {
  return (
    <div className="flex h-full min-w-0 flex-col gap-4 overflow-hidden lg:flex-row">
      {/* Editor panel placeholder */}
      <div className="min-h-[300px] min-w-0 flex-1 lg:min-h-0">
        <div className="h-full space-y-2 rounded-md border p-4">
          {[...Array(12)].map((_, i) => (
            <Skeleton key={i} className="h-4" style={{ width: `${50 + Math.random() * 50}%` }} />
          ))}
        </div>
      </div>
      {/* Preview panel placeholder */}
      <div className="min-h-[300px] min-w-0 flex-1 overflow-hidden lg:min-h-0">
        <div className="h-full space-y-2 rounded-md border bg-card p-6">
          {[...Array(12)].map((_, i) => (
            <Skeleton key={i} className="h-4" style={{ width: `${40 + Math.random() * 60}%` }} />
          ))}
        </div>
      </div>
    </div>
  );
}

function ContentPaneSkeleton() {
  return (
    <div className="flex h-full flex-col">
      <div className="border-b p-4">
        <Skeleton className="h-5 w-48" />
      </div>
      <div className="flex-1 space-y-2 p-4">
        {[...Array(20)].map((_, i) => (
          <Skeleton
            key={i}
            className="h-4 w-full"
            style={{ width: `${60 + Math.random() * 40}%` }}
          />
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Empty State
// ============================================================================

function EmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center py-12 text-center">
      <FileText className="mb-4 h-12 w-12 text-muted-foreground opacity-50" />
      <h3 className="mb-1 text-sm font-medium text-muted-foreground">No file selected</h3>
      <p className="max-w-sm text-xs text-muted-foreground">
        Select a file from the tree on the left to view its contents.
      </p>
    </div>
  );
}

// ============================================================================
// Error State
// ============================================================================

interface ErrorStateProps {
  error: string;
}

function ErrorState({ error }: ErrorStateProps) {
  return (
    <div className="flex h-full flex-col items-center justify-center p-4">
      <Alert variant="destructive" className="max-w-md">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription className="text-sm">{error}</AlertDescription>
      </Alert>
    </div>
  );
}

// ============================================================================
// Truncation Banner
// ============================================================================

interface TruncationBannerProps {
  originalSize?: number;
  fullFileUrl?: string;
}

function TruncationBanner({ originalSize, fullFileUrl }: TruncationBannerProps) {
  const sizeText = originalSize ? formatBytes(originalSize) : 'large file';

  return (
    <Alert className="mb-4 border-amber-500/50 bg-amber-50 dark:bg-amber-950/30">
      <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-500" />
      <AlertTitle className="text-amber-800 dark:text-amber-300">Large file truncated</AlertTitle>
      <AlertDescription className="text-amber-700 dark:text-amber-400">
        <span>This file ({sizeText}) has been truncated. Showing first 10,000 lines.</span>
        {fullFileUrl && (
          <a
            href={fullFileUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="ml-2 inline-flex items-center gap-1 font-medium text-amber-800 underline hover:text-amber-900 dark:text-amber-300 dark:hover:text-amber-200"
          >
            View full file on GitHub
            <ExternalLink className="h-3 w-3" aria-hidden="true" />
          </a>
        )}
      </AlertDescription>
    </Alert>
  );
}

// ============================================================================
// Breadcrumb Component
// ============================================================================

interface BreadcrumbProps {
  path: string;
  /** Optional ID for aria-labelledby usage */
  id?: string;
}

function Breadcrumb({ path, id }: BreadcrumbProps) {
  const segments = useMemo(() => pathToBreadcrumbs(path), [path]);

  return (
    <nav
      id={id}
      aria-label="File path"
      className="flex items-center gap-1 text-sm text-muted-foreground"
    >
      {segments.map((segment, index) => (
        <div key={index} className="flex items-center gap-1">
          {index > 0 && <ChevronRight className="h-3 w-3" aria-hidden="true" />}
          <span
            className={cn(index === segments.length - 1 && 'font-medium text-foreground')}
            aria-current={index === segments.length - 1 ? 'page' : undefined}
          >
            {segment}
          </span>
        </div>
      ))}
    </nav>
  );
}

// ============================================================================
// Line Numbers Component
// ============================================================================

interface LineNumbersProps {
  lineCount: number;
}

function LineNumbers({ lineCount }: LineNumbersProps) {
  return (
    <div className="select-none pr-4 text-right font-mono text-xs text-muted-foreground">
      {[...Array(lineCount)].map((_, i) => (
        <div key={i} className="leading-6">
          {i + 1}
        </div>
      ))}
    </div>
  );
}

// ============================================================================
// Content Display Component
// ============================================================================

interface ContentDisplayProps {
  content: string;
  showLineNumbers?: boolean;
}

function ContentDisplay({ content, showLineNumbers = false }: ContentDisplayProps) {
  const lines = useMemo(() => content.split('\n'), [content]);

  return (
    <div className="flex">
      {showLineNumbers && <LineNumbers lineCount={lines.length} />}
      <pre className="flex-1 whitespace-pre-wrap break-words font-mono text-xs leading-6">
        {content}
      </pre>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * ContentPane - File content viewer and editor component
 *
 * Displays the contents of a selected file with features like breadcrumb navigation,
 * optional line numbers, and edit functionality for supported file types.
 *
 * ## Bundle cost / optional editor loading
 *
 * The CodeMirror editor (via SplitPreview and MarkdownEditor) is **lazy-loaded**.
 * The editor chunk is only fetched from the network when the component actually
 * needs to render it — that is, when the file is a Markdown file (`*.md`) and the
 * component is mounted.  While the chunk loads a skeleton placeholder is shown
 * via a React `Suspense` boundary.
 *
 * - **Read-only mode** (`readOnly={true}`): The SplitPreview/MarkdownEditor module
 *   is still lazy-imported for markdown files because the preview panel is always
 *   rendered.  However, callers that pass `readOnly` avoid the full edit bundle
 *   cost for non-markdown file types entirely — only the markdown renderer
 *   (react-markdown, which is much lighter) loads in that case.
 *
 * - **Edit mode** (`readOnly={false}`, default): CodeMirror loads on first render
 *   of a markdown file.  Subsequent renders use the cached module.
 *
 * - **Non-markdown files** (`.ts`, `.json`, `.py`, …): SplitPreview is never
 *   rendered; CodeMirror is never loaded regardless of `readOnly`.
 *
 * ## Props controlling edit mode
 *
 * | Prop           | Purpose                                                              |
 * |----------------|----------------------------------------------------------------------|
 * | `readOnly`     | When `true`, hides all edit/save UI and disables edit mode entirely  |
 * | `isEditing`    | Lifted state — `true` when the user has clicked "Edit"               |
 * | `onEditStart`  | Called when user clicks the "Edit" button                            |
 * | `onEditChange` | Called on every keystroke in the editor with the updated content     |
 * | `onSave`       | Called when the user confirms the save; receives final content       |
 * | `onCancel`     | Called when the user dismisses the editor without saving             |
 *
 * @example
 * ```tsx
 * // Editable mode (default) — CodeMirror loads when user opens a .md file
 * <ContentPane
 *   path="src/index.ts"
 *   content={fileContent}
 *   isLoading={isLoading}
 *   error={error}
 *   onEditStart={() => handleEdit()}
 *   onSave={(content) => handleSave(content)}
 * />
 *
 * // Read-only mode — no edit controls rendered; CodeMirror NOT loaded for
 * // non-markdown files; markdown files render preview only (no editor panel)
 * <ContentPane
 *   path="README.md"
 *   content={fileContent}
 *   readOnly={true}
 * />
 * ```
 */
export function ContentPane({
  path,
  content,
  isLoading = false,
  error = null,
  readOnly = false,
  truncationInfo,
  isEditing = false,
  editedContent = '',
  onEditStart,
  onEditChange,
  onSave,
  onCancel,
  ariaLabel,
  showFrontmatter: _showFrontmatter = false,
}: ContentPaneProps) {
  // Generate unique ID for breadcrumb to use in aria-labelledby
  const breadcrumbId = path
    ? `content-pane-breadcrumb-${path.replace(/[^a-zA-Z0-9]/g, '-')}`
    : undefined;
  const [isSaving, setIsSaving] = useState(false);

  // Editing is disabled in read-only mode
  const canEdit = !readOnly && path && (onEditStart || onSave) && isEditableFile(path);
  const isMarkdown = path && isMarkdownFile(path);

  // Check if content is truncated
  const isTruncated = truncationInfo?.truncated === true;

  // Parse frontmatter from content (memoized to avoid reparsing on every render)
  const parsedContent = useMemo(() => {
    if (!content || typeof content !== 'string') {
      return { frontmatter: null, content: content || '' };
    }
    // Only parse if content appears to have frontmatter
    if (!detectFrontmatter(content)) {
      return { frontmatter: null, content };
    }
    return parseFrontmatter(content);
  }, [content]);

  // Content to display: always strip frontmatter when FrontmatterDisplay will be shown
  const displayContent = useMemo(() => {
    if (!content || typeof content !== 'string') {
      return content || '';
    }
    // Always strip frontmatter when FrontmatterDisplay will be shown (when frontmatter exists)
    // This prevents duplication between FrontmatterDisplay and raw content
    if (detectFrontmatter(content)) {
      return stripFrontmatter(content);
    }
    return content;
  }, [content]);

  // Handle edit button click
  const handleEditClick = () => {
    onEditChange?.(content || '');
    onEditStart?.();
  };

  // Handle save button click
  const handleSaveClick = async () => {
    if (!onSave) return;

    setIsSaving(true);
    try {
      await onSave(editedContent);
      onCancel?.();
    } catch (error) {
      console.error('Failed to save:', error);
      // Error handling can be expanded here
    } finally {
      setIsSaving(false);
    }
  };

  // Handle cancel button click
  const handleCancelClick = () => {
    onCancel?.();
  };

  // Loading state
  if (isLoading) {
    return <ContentPaneSkeleton />;
  }

  // Error state
  if (error) {
    return <ErrorState error={error} />;
  }

  // Empty state - no file selected
  if (!path) {
    return <EmptyState />;
  }

  // Empty content - file is empty or couldn't be loaded
  if (content === null || content === '') {
    return (
      <div
        className="flex h-full flex-col"
        role="region"
        aria-label={ariaLabel || `File content: ${path}`}
        aria-labelledby={breadcrumbId}
        data-testid="content-pane"
      >
        {/* Header with breadcrumb */}
        <div className="flex items-center justify-between border-b bg-muted/20 p-4">
          <Breadcrumb path={path} id={breadcrumbId} />
          {canEdit && !isEditing && (
            <Button variant="ghost" size="sm" onClick={handleEditClick} aria-label={`Edit ${path}`}>
              <Edit className="mr-2 h-4 w-4" aria-hidden="true" />
              Edit
            </Button>
          )}
          {!readOnly && isEditing && (
            <div className="flex gap-2">
              <Button variant="ghost" size="sm" onClick={handleCancelClick} disabled={isSaving}>
                <X className="mr-2 h-4 w-4" aria-hidden="true" />
                Cancel
              </Button>
              <Button variant="default" size="sm" onClick={handleSaveClick} disabled={isSaving}>
                <Save className="mr-2 h-4 w-4" aria-hidden="true" />
                {isSaving ? 'Saving...' : 'Save'}
              </Button>
            </div>
          )}
        </div>

        {/* Empty content message */}
        <div className="flex flex-1 items-center justify-center text-center">
          <div>
            <FileText
              className="mx-auto mb-2 h-8 w-8 text-muted-foreground opacity-50"
              aria-hidden="true"
            />
            <p className="text-sm text-muted-foreground">This file is empty</p>
          </div>
        </div>
      </div>
    );
  }

  // Markdown file - always use split preview (shows rendered markdown)
  if (isMarkdown) {
    return (
      <div
        className="flex h-full w-full flex-col overflow-hidden"
        role="region"
        aria-label={ariaLabel || `Markdown file: ${path}`}
        aria-labelledby={breadcrumbId}
        data-testid="content-pane"
      >
        {/* Header with breadcrumb and actions */}
        <div className="flex flex-shrink-0 items-center justify-between border-b bg-muted/20 p-4">
          <Breadcrumb path={path} id={breadcrumbId} />
          {!readOnly && isEditing ? (
            <div className="flex gap-2">
              <Button variant="ghost" size="sm" onClick={handleCancelClick} disabled={isSaving}>
                <X className="mr-2 h-4 w-4" aria-hidden="true" />
                Cancel
              </Button>
              <Button variant="default" size="sm" onClick={handleSaveClick} disabled={isSaving}>
                <Save className="mr-2 h-4 w-4" aria-hidden="true" />
                {isSaving ? 'Saving...' : 'Save'}
              </Button>
            </div>
          ) : (
            canEdit && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleEditClick}
                aria-label={`Edit ${path}`}
              >
                <Edit className="mr-2 h-4 w-4" aria-hidden="true" />
                Edit
              </Button>
            )
          )}
        </div>

        {/* Split-view editor and preview - preview always shown for markdown */}
        <div className="min-h-0 min-w-0 flex-1 overflow-auto p-4">
          {/* Truncation warning banner */}
          {isTruncated && (
            <TruncationBanner
              originalSize={truncationInfo?.originalSize}
              fullFileUrl={truncationInfo?.fullFileUrl}
            />
          )}
          {/* Frontmatter display (collapsed by default) */}
          {parsedContent.frontmatter && (
            <FrontmatterDisplay
              frontmatter={parsedContent.frontmatter}
              defaultCollapsed={true}
              className="mb-4"
            />
          )}
          <div className="min-w-0">
            <Suspense fallback={<EditorLoadingSkeleton />}>
              <SplitPreview
                content={isEditing ? editedContent : displayContent}
                onChange={(newContent) => onEditChange?.(newContent)}
                isEditing={isEditing}
              />
            </Suspense>
          </div>
        </div>
      </div>
    );
  }

  // Content display (read-only mode for non-markdown files)
  return (
    <div
      className="flex h-full w-full flex-col overflow-hidden"
      role="region"
      aria-label={ariaLabel || `File content: ${path}`}
      aria-labelledby={breadcrumbId}
      data-testid="content-pane"
    >
      {/* Header with breadcrumb and actions */}
      <div className="flex flex-shrink-0 items-center justify-between border-b bg-muted/20 p-4">
        <Breadcrumb path={path} id={breadcrumbId} />
        {canEdit && !isEditing && (
          <Button variant="ghost" size="sm" onClick={handleEditClick} aria-label={`Edit ${path}`}>
            <Edit className="mr-2 h-4 w-4" aria-hidden="true" />
            Edit
          </Button>
        )}
      </div>

      {/* Scrollable content area with horizontal scroll when needed */}
      <ScrollArea className="min-h-0 min-w-0 flex-1">
        <div className="p-4">
          {/* Truncation warning banner */}
          {isTruncated && (
            <TruncationBanner
              originalSize={truncationInfo?.originalSize}
              fullFileUrl={truncationInfo?.fullFileUrl}
            />
          )}
          {/* Frontmatter display (collapsed by default) */}
          {parsedContent.frontmatter && (
            <FrontmatterDisplay
              frontmatter={parsedContent.frontmatter}
              defaultCollapsed={true}
              className="mb-4"
            />
          )}
          <div className="max-w-full">
            <ContentDisplay content={displayContent} showLineNumbers={false} />
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}
