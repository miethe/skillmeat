/**
 * ArtifactCompactCard Component
 *
 * Compact card for displaying artifacts in folder view grid.
 * A smaller version of CatalogCard optimized for dense grid layouts.
 *
 * Features:
 * - Type badge with color coding
 * - Name display
 * - Confidence score badge
 * - Status badge
 * - Icon-only action buttons (import/exclude)
 * - Keyboard accessible (Enter/Space to click)
 * - Memoized for performance
 */

'use client';

import { memo, useState } from 'react';
import { Download, EyeOff, Loader2 } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { ScoreBadge } from '@/components/ScoreBadge';
import { ExcludeArtifactDialog } from '@/components/marketplace/exclude-artifact-dialog';
import { useExcludeCatalogEntry } from '@/hooks';
import type { CatalogEntry, ArtifactType } from '@/types/marketplace';

// ============================================================================
// Types
// ============================================================================

export interface ArtifactCompactCardProps {
  /** Catalog entry to display */
  entry: CatalogEntry;
  /** Source ID for exclude mutation */
  sourceId: string;
  /** Callback when card is clicked (opens modal) */
  onClick?: () => void;
  /** Callback when import is requested */
  onImport: () => void;
  /** Whether import is in progress */
  isImporting?: boolean;
}

// ============================================================================
// Type Configuration
// ============================================================================

/**
 * Color and label configuration for each artifact type.
 */
const typeConfig: Record<ArtifactType, { label: string; color: string }> = {
  skill: {
    label: 'Skill',
    color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  },
  command: {
    label: 'Command',
    color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  },
  agent: {
    label: 'Agent',
    color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  },
  mcp: {
    label: 'MCP',
    color: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  },
  mcp_server: {
    label: 'MCP',
    color: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  },
  hook: {
    label: 'Hook',
    color: 'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200',
  },
};

/**
 * Status badge configuration.
 */
const statusConfig: Record<string, { label: string; className: string }> = {
  new: {
    label: 'New',
    className: 'border-green-500 text-green-700 bg-green-50 dark:bg-green-950',
  },
  updated: {
    label: 'Updated',
    className: 'border-blue-500 text-blue-700 bg-blue-50 dark:bg-blue-950',
  },
  imported: {
    label: 'Imported',
    className: 'border-gray-500 text-gray-700 bg-gray-50 dark:bg-gray-950',
  },
  removed: {
    label: 'Removed',
    className: 'border-red-500 text-red-700 bg-red-50 dark:bg-red-950 line-through',
  },
  excluded: {
    label: 'Excluded',
    className: 'border-gray-400 text-gray-600 bg-gray-100 dark:bg-gray-800',
  },
};

// ============================================================================
// Component
// ============================================================================

/**
 * ArtifactCompactCard - Compact card for folder view grid
 *
 * Displays artifact info in a compact format suitable for grid layouts.
 * Includes type badge, name, confidence score, status, and action buttons.
 *
 * @example
 * ```tsx
 * <ArtifactCompactCard
 *   entry={catalogEntry}
 *   sourceId="source-123"
 *   onClick={() => openModal(entry)}
 *   onImport={() => handleImport(entry.id)}
 *   isImporting={false}
 * />
 * ```
 */
function ArtifactCompactCardComponent({
  entry,
  sourceId,
  onClick,
  onImport,
  isImporting = false,
}: ArtifactCompactCardProps) {
  const [excludeDialogOpen, setExcludeDialogOpen] = useState(false);
  const excludeMutation = useExcludeCatalogEntry(sourceId);

  const status = statusConfig[entry.status];
  const type = typeConfig[entry.artifact_type];

  // Determine if actions should be shown
  const canImport =
    entry.status !== 'imported' && entry.status !== 'removed' && entry.status !== 'excluded';
  const canExclude = entry.status !== 'excluded' && entry.status !== 'removed';

  // Keyboard handler for card click
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick?.();
    }
  };

  return (
    <>
      <Card
        className={cn(
          'relative cursor-pointer transition-shadow hover:shadow-md',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'
        )}
        onClick={onClick}
        onKeyDown={handleKeyDown}
        tabIndex={0}
        role="button"
        aria-label={`View details for ${entry.name} ${entry.artifact_type}`}
      >
        <div className="space-y-2 p-3">
          {/* Badges row */}
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge variant="outline" className={cn('text-[10px]', type.color)}>
              {type.label}
            </Badge>
            <ScoreBadge
              confidence={entry.confidence_score}
              size="sm"
              breakdown={entry.score_breakdown}
            />
            <Badge variant="outline" className={cn('text-[10px]', status.className)}>
              {status.label}
            </Badge>
          </div>

          {/* Duplicate/In Collection badges */}
          {(entry.is_duplicate || entry.in_collection) && (
            <div className="flex flex-wrap gap-1">
              {entry.status === 'excluded' && entry.is_duplicate && (
                <Badge
                  variant="outline"
                  className="border-yellow-500 bg-yellow-50 text-[10px] text-yellow-700 dark:bg-yellow-950"
                  title={
                    entry.duplicate_reason === 'within_source'
                      ? `Duplicate within this source${entry.duplicate_of ? `: ${entry.duplicate_of}` : ''}`
                      : entry.duplicate_reason === 'cross_source'
                        ? 'Duplicate from another source or collection'
                        : 'Marked as duplicate'
                  }
                >
                  Duplicate
                </Badge>
              )}
              {entry.in_collection && entry.status !== 'imported' && (
                <Badge
                  variant="outline"
                  className="border-emerald-500 bg-emerald-50 text-[10px] text-emerald-700 dark:bg-emerald-950"
                  title="An artifact with this name and type already exists in your collection"
                >
                  In Collection
                </Badge>
              )}
            </div>
          )}

          {/* Name */}
          <h4 className="truncate text-sm font-semibold" title={entry.name}>
            {entry.name}
          </h4>

          {/* Actions row */}
          <div
            className="flex items-center justify-end gap-1 pt-1"
            onClick={(e) => e.stopPropagation()}
          >
            {canImport && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={(e) => {
                        e.stopPropagation();
                        onImport();
                      }}
                      disabled={isImporting}
                      aria-label={`Import ${entry.name}`}
                    >
                      {isImporting ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                      ) : (
                        <Download className="h-3.5 w-3.5" aria-hidden="true" />
                      )}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Import</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
            {canExclude && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={(e) => {
                        e.stopPropagation();
                        setExcludeDialogOpen(true);
                      }}
                      aria-label={`Exclude ${entry.name}`}
                    >
                      <EyeOff className="h-3.5 w-3.5" aria-hidden="true" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Not an artifact</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
          </div>
        </div>
      </Card>

      <ExcludeArtifactDialog
        entry={entry}
        open={excludeDialogOpen}
        onOpenChange={setExcludeDialogOpen}
        onConfirm={() => {
          excludeMutation.mutate({ entryId: entry.id });
          setExcludeDialogOpen(false);
        }}
        isLoading={excludeMutation.isPending}
      />
    </>
  );
}

export const ArtifactCompactCard = memo(ArtifactCompactCardComponent);
