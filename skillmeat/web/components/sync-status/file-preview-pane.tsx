'use client';

import { useMemo } from 'react';
import { File, FileText, FileCode } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';

// ============================================================================
// Types
// ============================================================================

export interface FilePreviewPaneProps {
  filePath: string | null;
  content: string | null;
  tier: 'source' | 'collection' | 'project';
  isLoading: boolean;
}

type FileType = 'markdown' | 'code' | 'text';

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Detect file type based on file extension
 */
function getFileType(path: string): FileType {
  const ext = path.split('.').pop()?.toLowerCase();
  if (ext === 'md') return 'markdown';
  if (['ts', 'tsx', 'js', 'jsx', 'py', 'json', 'yaml', 'yml', 'toml'].includes(ext || ''))
    return 'code';
  return 'text';
}

/**
 * Extract filename from path
 */
function getFileName(path: string): string {
  return path.split('/').pop() || path;
}

/**
 * Get tier badge variant and label
 */
function getTierConfig(tier: 'source' | 'collection' | 'project') {
  const configs = {
    source: { variant: 'outline' as const, label: 'Source' },
    collection: { variant: 'secondary' as const, label: 'Collection' },
    project: { variant: 'default' as const, label: 'Project' },
  };
  return configs[tier];
}

/**
 * Simple markdown to HTML converter (basic subset)
 */
function renderMarkdown(markdown: string): string {
  let html = markdown;

  // Headers
  html = html.replace(/^### (.*$)/gim, '<h3 class="text-lg font-semibold mt-4 mb-2">$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2 class="text-xl font-semibold mt-6 mb-3">$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold mt-8 mb-4">$1</h1>');

  // Bold and italic
  html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

  // Code blocks
  html = html.replace(
    /```(\w+)?\n([\s\S]*?)```/g,
    '<pre class="bg-muted rounded-md p-4 my-3 overflow-x-auto"><code class="text-sm font-mono">$2</code></pre>'
  );

  // Inline code
  html = html.replace(/`(.+?)`/g, '<code class="bg-muted px-1.5 py-0.5 rounded text-sm">$1</code>');

  // Links
  html = html.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" class="text-primary underline">$1</a>');

  // Lists
  html = html.replace(/^\* (.+)$/gim, '<li class="ml-4">$1</li>');
  html = html.replace(/^- (.+)$/gim, '<li class="ml-4">$1</li>');

  // Line breaks
  html = html.replace(/\n/g, '<br />');

  return html;
}

// ============================================================================
// Loading Skeleton
// ============================================================================

function PreviewSkeleton() {
  return (
    <div className="flex h-full flex-col">
      <div className="border-b p-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-5 w-20" />
        </div>
      </div>
      <div className="flex-1 space-y-3 p-6">
        {[...Array(15)].map((_, i) => (
          <Skeleton
            key={i}
            className="h-4"
            style={{ width: `${50 + Math.random() * 50}%` }}
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
      <File className="mb-4 h-16 w-16 text-muted-foreground opacity-40" />
      <h3 className="mb-2 text-base font-medium text-muted-foreground">No file selected</h3>
      <p className="max-w-sm text-sm text-muted-foreground">
        Select a file from the file list to preview its contents
      </p>
    </div>
  );
}

// ============================================================================
// Error State
// ============================================================================

function ErrorState() {
  return (
    <div className="flex h-full flex-col items-center justify-center py-12 text-center">
      <FileText className="mb-4 h-16 w-16 text-destructive opacity-50" />
      <h3 className="mb-2 text-base font-medium text-destructive">Content unavailable</h3>
      <p className="max-w-sm text-sm text-muted-foreground">
        Unable to load file content. The file may be too large or in an unsupported format.
      </p>
    </div>
  );
}

// ============================================================================
// Content Renderers
// ============================================================================

interface MarkdownContentProps {
  content: string;
}

function MarkdownContent({ content }: MarkdownContentProps) {
  const renderedHtml = useMemo(() => renderMarkdown(content), [content]);

  return (
    <div
      className="prose prose-sm dark:prose-invert max-w-none"
      dangerouslySetInnerHTML={{ __html: renderedHtml }}
    />
  );
}

interface CodeContentProps {
  content: string;
  filePath: string;
}

function CodeContent({ content, filePath }: CodeContentProps) {
  const language = useMemo(() => {
    const ext = filePath.split('.').pop()?.toLowerCase();
    return ext || 'text';
  }, [filePath]);

  return (
    <div className="relative">
      <div className="absolute right-2 top-2">
        <Badge variant="outline" className="text-xs">
          {language}
        </Badge>
      </div>
      <pre className="overflow-x-auto rounded-md bg-muted p-4">
        <code className="text-sm font-mono leading-relaxed">{content}</code>
      </pre>
    </div>
  );
}

interface TextContentProps {
  content: string;
}

function TextContent({ content }: TextContentProps) {
  return (
    <pre className="whitespace-pre-wrap break-words font-mono text-sm leading-relaxed">
      {content}
    </pre>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * FilePreviewPane - Displays file content with appropriate rendering
 *
 * Features:
 * - Markdown rendering with basic HTML conversion
 * - Syntax-highlighted code display
 * - Plain text display for other files
 * - Loading skeleton state
 * - Empty state when no file selected
 * - Error state for unavailable content
 * - Tier badge showing which version is displayed
 * - Dark mode support
 *
 * @example
 * ```tsx
 * <FilePreviewPane
 *   filePath="README.md"
 *   content={fileContent}
 *   tier="collection"
 *   isLoading={false}
 * />
 * ```
 */
export function FilePreviewPane({ filePath, content, tier, isLoading }: FilePreviewPaneProps) {
  // Loading state
  if (isLoading) {
    return <PreviewSkeleton />;
  }

  // Empty state - no file selected
  if (!filePath) {
    return <EmptyState />;
  }

  // Error state - file selected but no content
  if (content === null) {
    return <ErrorState />;
  }

  // Get file metadata
  const fileName = getFileName(filePath);
  const fileType = getFileType(filePath);
  const tierConfig = getTierConfig(tier);

  // Select icon based on file type
  const FileIcon = fileType === 'markdown' ? FileText : fileType === 'code' ? FileCode : File;

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header with file name and tier badge */}
      <div className="flex items-center justify-between border-b bg-muted/20 px-4 py-3">
        <div className="flex items-center gap-2">
          <FileIcon className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-medium">
            File Preview: <span className="font-semibold">{fileName}</span>
          </h3>
        </div>
        <Badge variant={tierConfig.variant}>{tierConfig.label}</Badge>
      </div>

      {/* Scrollable content area */}
      <ScrollArea className="flex-1">
        <div className="p-6">
          {fileType === 'markdown' && <MarkdownContent content={content} />}
          {fileType === 'code' && <CodeContent content={content} filePath={filePath} />}
          {fileType === 'text' && <TextContent content={content} />}
        </div>
      </ScrollArea>
    </div>
  );
}
