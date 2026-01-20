'use client';

/**
 * CatalogList Component
 *
 * Table/list view for marketplace catalog entries.
 * Displays artifacts in a compact tabular format with:
 * - Name and path
 * - Type with icon
 * - Confidence score badge
 * - Status badge
 * - Actions (View on GitHub, Import)
 */

import { useState } from 'react';
import {
  ExternalLink,
  Download,
  Loader2,
  Sparkles,
  Bot,
  Terminal,
  Server,
  Webhook,
  HelpCircle,
} from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Skeleton } from '@/components/ui/skeleton';
import { ScoreBadge } from '@/components/ScoreBadge';
import { ExcludeArtifactDialog } from '@/components/marketplace/exclude-artifact-dialog';
import { useExcludeCatalogEntry } from '@/hooks';
import { cn } from '@/lib/utils';
import type { CatalogEntry, ArtifactType } from '@/types/marketplace';

// ============================================================================
// Types
// ============================================================================

interface CatalogListProps {
  entries: CatalogEntry[];
  sourceId: string;
  selectedEntries: Set<string>;
  onSelectEntry: (entryId: string, selected: boolean) => void;
  onImportSingle: (entryId: string) => void;
  onEntryClick: (entry: CatalogEntry) => void;
  isImporting: boolean;
  isLoading?: boolean;
}

// ============================================================================
// Constants
// ============================================================================

const artifactTypeIcons: Record<ArtifactType, React.ComponentType<{ className?: string }>> = {
  skill: Sparkles,
  command: Terminal,
  agent: Bot,
  mcp: Server,
  mcp_server: Server,
  hook: Webhook,
};

const artifactTypeLabels: Record<ArtifactType, string> = {
  skill: 'Skill',
  command: 'Command',
  agent: 'Agent',
  mcp: 'MCP',
  mcp_server: 'MCP Server',
  hook: 'Hook',
};

const artifactTypeIconColors: Record<ArtifactType, string> = {
  skill: 'text-blue-700 dark:text-blue-400',
  command: 'text-purple-700 dark:text-purple-400',
  agent: 'text-green-700 dark:text-green-400',
  mcp: 'text-orange-700 dark:text-orange-400',
  mcp_server: 'text-orange-700 dark:text-orange-400',
  hook: 'text-pink-700 dark:text-pink-400',
};

const artifactTypeRowTints: Record<ArtifactType, string> = {
  skill: 'bg-blue-500/[0.02] dark:bg-blue-500/[0.03]',
  command: 'bg-purple-500/[0.02] dark:bg-purple-500/[0.03]',
  agent: 'bg-green-500/[0.02] dark:bg-green-500/[0.03]',
  mcp: 'bg-orange-500/[0.02] dark:bg-orange-500/[0.03]',
  mcp_server: 'bg-orange-500/[0.02] dark:bg-orange-500/[0.03]',
  hook: 'bg-pink-500/[0.02] dark:bg-pink-500/[0.03]',
};

const artifactTypeBorderAccents: Record<ArtifactType, string> = {
  skill: 'border-l-blue-500',
  command: 'border-l-purple-500',
  agent: 'border-l-green-500',
  mcp: 'border-l-orange-500',
  mcp_server: 'border-l-orange-500',
  hook: 'border-l-pink-500',
};

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
    className: 'border-red-500 text-red-700 bg-red-50 dark:bg-red-950',
  },
  excluded: {
    label: 'Excluded',
    className: 'border-gray-400 text-gray-600 bg-gray-100 dark:bg-gray-800',
  },
};

// ============================================================================
// Skeleton Component
// ============================================================================

function CatalogListSkeleton() {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-[40px]"></TableHead>
          <TableHead>Name</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Confidence</TableHead>
          <TableHead>Status</TableHead>
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {[...Array(6)].map((_, i) => (
          <TableRow key={i}>
            <TableCell>
              <Skeleton className="h-4 w-4" />
            </TableCell>
            <TableCell>
              <div className="space-y-2">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-48" />
              </div>
            </TableCell>
            <TableCell>
              <Skeleton className="h-4 w-16" />
            </TableCell>
            <TableCell>
              <Skeleton className="h-6 w-12" />
            </TableCell>
            <TableCell>
              <Skeleton className="h-5 w-16 rounded-full" />
            </TableCell>
            <TableCell>
              <div className="flex justify-end gap-2">
                <Skeleton className="h-8 w-8" />
                <Skeleton className="h-8 w-20" />
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

// ============================================================================
// Row Component
// ============================================================================

interface CatalogRowProps {
  entry: CatalogEntry;
  sourceId: string;
  selected: boolean;
  onSelect: (selected: boolean) => void;
  onImport: () => void;
  onClick: () => void;
  isImporting: boolean;
}

function CatalogRow({
  entry,
  sourceId,
  selected,
  onSelect,
  onImport,
  onClick,
  isImporting,
}: CatalogRowProps) {
  const [excludeDialogOpen, setExcludeDialogOpen] = useState(false);
  const excludeMutation = useExcludeCatalogEntry(sourceId);

  const Icon = artifactTypeIcons[entry.artifact_type] || HelpCircle;
  const iconColor =
    artifactTypeIconColors[entry.artifact_type] || 'text-gray-500 dark:text-gray-400';
  const rowTint = artifactTypeRowTints[entry.artifact_type] || 'bg-gray-500/[0.02]';
  const borderAccent = artifactTypeBorderAccents[entry.artifact_type] || 'border-l-gray-400';
  const typeLabel = artifactTypeLabels[entry.artifact_type] || entry.artifact_type || 'Unknown';
  const entryStatus = statusConfig[entry.status] || {
    label: 'New',
    className: 'border-green-500 text-green-700 bg-green-50 dark:bg-green-950',
  };

  const canImport = entry.status === 'new' || entry.status === 'updated';
  const canSelect = entry.status !== 'removed' && entry.status !== 'excluded';

  return (
    <>
      <TableRow
        className={cn(
          'cursor-pointer border-l-2 transition-colors hover:bg-muted/50',
          borderAccent,
          rowTint
        )}
        onClick={onClick}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onClick();
          }
        }}
        aria-label={`View details for ${entry.name}`}
      >
        {/* Selection Checkbox */}
        <TableCell onClick={(e) => e.stopPropagation()}>
          <Checkbox
            checked={selected}
            onCheckedChange={onSelect}
            disabled={!canSelect}
            aria-label={`Select ${entry.name} for import`}
          />
        </TableCell>

        {/* Name and Path */}
        <TableCell>
          <div className="space-y-1">
            <div className="font-medium">{entry.name}</div>
            <div className="max-w-[300px] truncate text-xs text-muted-foreground">{entry.path}</div>
          </div>
        </TableCell>

        {/* Type */}
        <TableCell>
          <div className="flex items-center gap-2">
            <Icon className={cn('h-4 w-4', iconColor)} aria-hidden="true" />
            <span className="text-sm">{typeLabel}</span>
          </div>
        </TableCell>

        {/* Confidence */}
        <TableCell>
          <ScoreBadge
            confidence={entry.confidence_score}
            size="sm"
            breakdown={entry.score_breakdown}
          />
        </TableCell>

        {/* Status */}
        <TableCell>
          <div className="flex items-center gap-2">
            <Badge
              variant="outline"
              className={cn(entryStatus.className, entry.status === 'removed' && 'line-through')}
            >
              {entryStatus.label}
            </Badge>
            {/* Duplicate Badge (P4.3c) */}
            {entry.status === 'excluded' && entry.is_duplicate && (
              <Badge
                variant="outline"
                className="border-yellow-500 bg-yellow-50 text-yellow-700 dark:bg-yellow-950"
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
            {/* In Collection Badge */}
            {entry.in_collection && entry.status !== 'imported' && (
              <Badge
                variant="outline"
                className="border-emerald-500 bg-emerald-50 text-emerald-700 dark:bg-emerald-950"
                title="An artifact with this name and type already exists in your collection"
              >
                In Collection
              </Badge>
            )}
          </div>
        </TableCell>

        {/* Actions */}
        <TableCell onClick={(e) => e.stopPropagation()}>
          <div className="flex items-center justify-end gap-2">
            {/* View on GitHub */}
            <a
              href={entry.upstream_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
              aria-label={`View ${entry.name} on GitHub`}
            >
              <ExternalLink className="h-3 w-3" />
              <span className="hidden sm:inline">GitHub</span>
            </a>

            {/* Import Button */}
            {canImport && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onImport}
                  disabled={isImporting}
                  className="h-7 px-2"
                >
                  {isImporting ? (
                    <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
                  ) : (
                    <>
                      <Download className="mr-1 h-3 w-3" aria-hidden="true" />
                      Import
                    </>
                  )}
                </Button>
                <button
                  type="button"
                  className="cursor-pointer rounded-sm px-1 text-xs text-muted-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  onClick={() => setExcludeDialogOpen(true)}
                  aria-label={`Mark ${entry.name} as not an artifact`}
                >
                  Exclude
                </button>
              </>
            )}

            {entry.status === 'imported' && entry.import_date && (
              <span className="text-xs text-muted-foreground">
                Imported {new Date(entry.import_date).toLocaleDateString()}
              </span>
            )}
          </div>
        </TableCell>
      </TableRow>

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

// ============================================================================
// Main Component
// ============================================================================

export function CatalogList({
  entries,
  sourceId,
  selectedEntries,
  onSelectEntry,
  onImportSingle,
  onEntryClick,
  isImporting,
  isLoading,
}: CatalogListProps) {
  if (isLoading) {
    return <CatalogListSkeleton />;
  }

  if (entries.length === 0) {
    return null; // Empty state handled by parent
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[40px]"></TableHead>
            <TableHead>Name</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Confidence</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {entries.map((entry) => (
            <CatalogRow
              key={entry.id}
              entry={entry}
              sourceId={sourceId}
              selected={selectedEntries.has(entry.id)}
              onSelect={(selected) => onSelectEntry(entry.id, selected)}
              onImport={() => onImportSingle(entry.id)}
              onClick={() => onEntryClick(entry)}
              isImporting={isImporting}
            />
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
