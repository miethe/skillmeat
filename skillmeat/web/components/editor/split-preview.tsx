'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { MarkdownEditor } from './markdown-editor';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';

// ============================================================================
// Types
// ============================================================================

export interface SplitPreviewProps {
  content: string;
  onChange: (content: string) => void;
  isEditing: boolean;
  className?: string;
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * SplitPreview - Split-view markdown editor with live preview
 *
 * Features:
 * - Left side: MarkdownEditor component
 * - Right side: Rendered markdown preview
 * - Real-time preview updates as user types
 * - GitHub Flavored Markdown (GFM) support
 * - Responsive layout (side-by-side on desktop, stacked on mobile)
 * - Scrollable preview area
 *
 * @example
 * ```tsx
 * <SplitPreview
 *   content={markdownContent}
 *   onChange={(content) => setContent(content)}
 *   isEditing={true}
 * />
 * ```
 */
export function SplitPreview({
  content,
  onChange,
  isEditing,
  className,
}: SplitPreviewProps) {
  return (
    <div className={cn('flex flex-col lg:flex-row h-full gap-4', className)}>
      {/* Editor Panel - Only shown in edit mode */}
      {isEditing && (
        <div className="flex-1 min-w-0 min-h-[300px] lg:min-h-0">
          <MarkdownEditor
            initialContent={content}
            onChange={onChange}
            className="h-full"
          />
        </div>
      )}

      {/* Preview Panel - Always shown for markdown */}
      <div className={cn('flex-1 min-w-0 min-h-[300px] lg:min-h-0', !isEditing && 'w-full')}>
        <div className="h-full border rounded-md bg-card overflow-hidden">
          <ScrollArea className="h-full">
            <div className="p-6 prose prose-sm dark:prose-invert max-w-none break-words overflow-wrap-anywhere">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {content || '*No content to preview*'}
              </ReactMarkdown>
            </div>
          </ScrollArea>
        </div>
      </div>
    </div>
  );
}
