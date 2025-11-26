'use client';

import { useState, useMemo } from 'react';
import { FileText, AlertCircle, Edit, ChevronRight, Save, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { SplitPreview } from '@/components/editor/split-preview';

// ============================================================================
// Types
// ============================================================================

export interface ContentPaneProps {
  path: string | null;
  content: string | null;
  isLoading?: boolean;
  error?: string | null;
  // Lifted edit state from parent
  isEditing?: boolean;
  editedContent?: string;
  onEditStart?: () => void;
  onEditChange?: (content: string) => void;
  onSave?: (content: string) => void | Promise<void>;
  onCancel?: () => void;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Check if a file is editable based on its extension
 */
function isEditableFile(path: string): boolean {
  const editableExtensions = ['.md', '.txt', '.json', '.ts', '.tsx', '.js', '.jsx', '.py', '.yml', '.yaml', '.toml'];
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
// Loading Skeleton
// ============================================================================

function ContentPaneSkeleton() {
  return (
    <div className="h-full flex flex-col">
      <div className="border-b p-4">
        <Skeleton className="h-5 w-48" />
      </div>
      <div className="flex-1 p-4 space-y-2">
        {[...Array(20)].map((_, i) => (
          <Skeleton key={i} className="h-4 w-full" style={{ width: `${60 + Math.random() * 40}%` }} />
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
    <div className="flex flex-col items-center justify-center h-full text-center py-12">
      <FileText className="h-12 w-12 text-muted-foreground opacity-50 mb-4" />
      <h3 className="text-sm font-medium text-muted-foreground mb-1">No file selected</h3>
      <p className="text-xs text-muted-foreground max-w-sm">
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
    <div className="flex flex-col items-center justify-center h-full p-4">
      <Alert variant="destructive" className="max-w-md">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription className="text-sm">
          {error}
        </AlertDescription>
      </Alert>
    </div>
  );
}

// ============================================================================
// Breadcrumb Component
// ============================================================================

interface BreadcrumbProps {
  path: string;
}

function Breadcrumb({ path }: BreadcrumbProps) {
  const segments = useMemo(() => pathToBreadcrumbs(path), [path]);

  return (
    <div className="flex items-center gap-1 text-sm text-muted-foreground">
      {segments.map((segment, index) => (
        <div key={index} className="flex items-center gap-1">
          {index > 0 && <ChevronRight className="h-3 w-3" />}
          <span
            className={cn(
              index === segments.length - 1 && 'text-foreground font-medium'
            )}
          >
            {segment}
          </span>
        </div>
      ))}
    </div>
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
    <div className="select-none text-right pr-4 text-xs text-muted-foreground font-mono">
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
      <pre className="flex-1 text-xs font-mono leading-6 whitespace-pre-wrap break-words">
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
 * Features:
 * - File path displayed in breadcrumb style at top
 * - Scrollable content area for large files
 * - Monospace font for code/text content
 * - Loading state with skeleton
 * - Error state display with alert
 * - Empty state when no file selected
 * - Edit button for editable files (.md, .txt, .json, etc.)
 * - Split-view markdown editor with live preview for .md files
 * - Save and Cancel buttons in edit mode
 * - Optional line numbers (nice to have)
 *
 * @example
 * ```tsx
 * <ContentPane
 *   path="src/index.ts"
 *   content={fileContent}
 *   isLoading={isLoading}
 *   error={error}
 *   onEdit={() => handleEdit()}
 *   onSave={(content) => handleSave(content)}
 * />
 * ```
 */
export function ContentPane({
  path,
  content,
  isLoading = false,
  error = null,
  isEditing = false,
  editedContent = '',
  onEditStart,
  onEditChange,
  onSave,
  onCancel,
}: ContentPaneProps) {
  const [isSaving, setIsSaving] = useState(false);

  const canEdit = path && (onEditStart || onSave) && isEditableFile(path);
  const isMarkdown = path && isMarkdownFile(path);

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
      <div className="h-full flex flex-col">
        {/* Header with breadcrumb */}
        <div className="border-b p-4 flex items-center justify-between bg-muted/20">
          <Breadcrumb path={path} />
          {canEdit && !isEditing && (
            <Button variant="ghost" size="sm" onClick={handleEditClick}>
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </Button>
          )}
          {isEditing && (
            <div className="flex gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCancelClick}
                disabled={isSaving}
              >
                <X className="mr-2 h-4 w-4" />
                Cancel
              </Button>
              <Button
                variant="default"
                size="sm"
                onClick={handleSaveClick}
                disabled={isSaving}
              >
                <Save className="mr-2 h-4 w-4" />
                {isSaving ? 'Saving...' : 'Save'}
              </Button>
            </div>
          )}
        </div>

        {/* Empty content message */}
        <div className="flex-1 flex items-center justify-center text-center">
          <div>
            <FileText className="h-8 w-8 text-muted-foreground opacity-50 mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">This file is empty</p>
          </div>
        </div>
      </div>
    );
  }

  // Markdown file - always use split preview (shows rendered markdown)
  if (isMarkdown) {
    return (
      <div className="h-full w-full flex flex-col overflow-hidden">
        {/* Header with breadcrumb and actions */}
        <div className="border-b p-4 flex items-center justify-between bg-muted/20 flex-shrink-0">
          <Breadcrumb path={path} />
          {isEditing ? (
            <div className="flex gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCancelClick}
                disabled={isSaving}
              >
                <X className="mr-2 h-4 w-4" />
                Cancel
              </Button>
              <Button
                variant="default"
                size="sm"
                onClick={handleSaveClick}
                disabled={isSaving}
              >
                <Save className="mr-2 h-4 w-4" />
                {isSaving ? 'Saving...' : 'Save'}
              </Button>
            </div>
          ) : (
            canEdit && (
              <Button variant="ghost" size="sm" onClick={handleEditClick}>
                <Edit className="mr-2 h-4 w-4" />
                Edit
              </Button>
            )
          )}
        </div>

        {/* Split-view editor and preview - preview always shown for markdown */}
        <div className="flex-1 p-4 overflow-x-auto overflow-y-hidden min-h-0 min-w-0">
          <SplitPreview
            content={isEditing ? editedContent : content}
            onChange={(newContent) => onEditChange?.(newContent)}
            isEditing={isEditing}
          />
        </div>
      </div>
    );
  }

  // Content display (read-only mode for non-markdown files)
  return (
    <div className="h-full w-full flex flex-col overflow-hidden">
      {/* Header with breadcrumb and actions */}
      <div className="border-b p-4 flex items-center justify-between bg-muted/20 flex-shrink-0">
        <Breadcrumb path={path} />
        {canEdit && !isEditing && (
          <Button variant="ghost" size="sm" onClick={handleEditClick}>
            <Edit className="mr-2 h-4 w-4" />
            Edit
          </Button>
        )}
      </div>

      {/* Scrollable content area with horizontal scroll when needed */}
      <ScrollArea className="flex-1 min-h-0 min-w-0">
        <div className="p-4">
          <div className="overflow-x-auto max-w-full">
            <ContentDisplay content={content} showLineNumbers={false} />
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}
