'use client';

/**
 * FolderDetailHeader Component
 *
 * Header component for the folder detail pane showing folder metadata
 * and bulk import action. Displays:
 * - Parent folder breadcrumb chip (if not at root)
 * - Folder name (h2)
 * - "Import All" button with count
 * - Folder description (from README)
 */

import { ChevronLeft, Download, Loader2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { FolderNode } from '@/lib/tree-builder';
import type { CatalogEntry } from '@/types/marketplace';

// ============================================================================
// Types
// ============================================================================

/**
 * Props for FolderDetailHeader component.
 */
export interface FolderDetailHeaderProps {
  /** Folder node data */
  folder: FolderNode;
  /** Parent folder name (null if at root) */
  parentFolderName: string | null;
  /** Extracted folder description (from README) */
  description: string | null;
  /** All catalog entries (for Import All) */
  entries: CatalogEntry[];
  /** Count of direct importable artifacts */
  importableCount: number;
  /** Whether bulk import is in progress */
  isImporting?: boolean;
  /** Callback when "Import All" is clicked */
  onImportAll: (entries: CatalogEntry[]) => void;
  /** Callback when parent chip is clicked */
  onNavigateToParent?: () => void;
}

// ============================================================================
// Component
// ============================================================================

/**
 * FolderDetailHeader - Header component for folder detail pane
 *
 * Displays folder metadata including name, parent breadcrumb, description,
 * and provides the "Import All" bulk action button for importing all
 * direct artifacts in the folder.
 *
 * @example
 * ```tsx
 * <FolderDetailHeader
 *   folder={selectedFolder}
 *   parentFolderName="plugins"
 *   description="Development tools for code formatting"
 *   entries={folderArtifacts}
 *   importableCount={5}
 *   isImporting={false}
 *   onImportAll={handleImportAll}
 *   onNavigateToParent={handleNavigateToParent}
 * />
 * ```
 */
export function FolderDetailHeader({
  folder,
  parentFolderName,
  description,
  entries,
  importableCount,
  isImporting = false,
  onImportAll,
  onNavigateToParent,
}: FolderDetailHeaderProps) {
  /**
   * Handle Import All button click.
   * Filters entries to only include direct artifacts (not descendants).
   */
  const handleImportAll = () => {
    // Filter to only direct artifacts in this folder
    const directArtifacts = entries.filter((entry) => {
      // Match entries where the parent directory matches the folder's fullPath
      const entryDir = entry.path.substring(0, entry.path.lastIndexOf('/'));
      return entryDir === folder.fullPath;
    });
    onImportAll(directArtifacts);
  };

  const isImportDisabled = importableCount === 0 || isImporting;

  return (
    <div className="space-y-4">
      {/* Parent breadcrumb chip */}
      {parentFolderName && onNavigateToParent && (
        <div>
          <Badge
            variant="outline"
            className="cursor-pointer transition-colors duration-200 hover:bg-muted"
            onClick={onNavigateToParent}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onNavigateToParent();
              }
            }}
            aria-label={`Navigate to parent folder: ${parentFolderName}`}
          >
            <ChevronLeft className="mr-1 h-3 w-3" aria-hidden="true" />
            {parentFolderName}
          </Badge>
        </div>
      )}

      {/* Title row with folder name and Import All button */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-2xl font-semibold">{folder.name}</h2>

        <Button
          variant="default"
          onClick={handleImportAll}
          disabled={isImportDisabled}
          className="transition-all duration-200"
          aria-label={
            isImporting
              ? 'Importing artifacts...'
              : `Import all ${importableCount} artifacts from this folder`
          }
        >
          {isImporting ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <Download className="mr-2 h-4 w-4" aria-hidden="true" />
          )}
          Import All ({importableCount})
        </Button>
      </div>

      {/* Description (from README) */}
      {description && (
        <p className="whitespace-pre-line text-sm text-muted-foreground">{description}</p>
      )}
    </div>
  );
}
