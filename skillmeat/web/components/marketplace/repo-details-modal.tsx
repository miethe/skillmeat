/**
 * Repo Details Modal
 *
 * Modal for displaying repository description and README content
 */

'use client';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { FileText } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { GitHubSource } from '@/types/marketplace';

// GitHubSource already includes repo_description and repo_readme fields
// This alias maintains backward compatibility with existing component props
type GitHubSourceWithReadme = GitHubSource;

interface RepoDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  source: GitHubSourceWithReadme;
}

/**
 * RepoDetailsModal - Display repository description and README
 *
 * Features:
 * - Shows user description or GitHub repo description at top
 * - Renders README markdown content in scrollable area
 * - Keyboard accessible (Escape to close via Dialog)
 * - Proper focus management via Radix Dialog
 *
 * @example
 * ```tsx
 * <RepoDetailsModal
 *   isOpen={showDetails}
 *   onClose={() => setShowDetails(false)}
 *   source={selectedSource}
 * />
 * ```
 */
export function RepoDetailsModal({ isOpen, onClose, source }: RepoDetailsModalProps) {
  // Prefer user-provided description, fall back to GitHub repo description
  const description = source.description || source.repo_description;
  const readmeContent = source.repo_readme;

  // Check if we have any content to display
  const hasContent = description || readmeContent;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        className="flex max-h-[85vh] flex-col overflow-hidden sm:max-w-2xl"
        aria-describedby={description ? 'repo-description' : undefined}
      >
        <DialogHeader className="flex-shrink-0">
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" aria-hidden="true" />
            {source.owner}/{source.repo_name}
          </DialogTitle>
          {description && (
            <DialogDescription id="repo-description" className="text-sm">
              {description}
            </DialogDescription>
          )}
        </DialogHeader>

        {!hasContent ? (
          <EmptyState />
        ) : (
          <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden">
            {/* README Section */}
            {readmeContent ? (
              <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
                <h3 className="mb-2 flex-shrink-0 text-sm font-medium text-muted-foreground">
                  README
                </h3>
                <ScrollArea className="min-h-0 min-w-0 flex-1 rounded-md border bg-card">
                  <div className="prose prose-sm max-w-none break-words p-4 dark:prose-invert prose-headings:break-words prose-p:break-words prose-code:break-all prose-pre:overflow-x-auto [overflow-wrap:anywhere] [word-break:break-word]">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {readmeContent}
                    </ReactMarkdown>
                  </div>
                </ScrollArea>
              </div>
            ) : (
              // Show message if we have description but no README
              <div className="flex flex-1 items-center justify-center rounded-md border bg-muted/20 p-8">
                <div className="text-center">
                  <FileText
                    className="mx-auto mb-2 h-8 w-8 text-muted-foreground opacity-50"
                    aria-hidden="true"
                  />
                  <p className="text-sm text-muted-foreground">No README available</p>
                </div>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

/**
 * Empty state when no description or README is available
 */
function EmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
      <FileText
        className="mb-4 h-12 w-12 text-muted-foreground opacity-50"
        aria-hidden="true"
      />
      <h3 className="mb-1 text-sm font-medium text-muted-foreground">
        No repository details available
      </h3>
      <p className="max-w-sm text-xs text-muted-foreground">
        This repository does not have a description or README content.
      </p>
    </div>
  );
}
