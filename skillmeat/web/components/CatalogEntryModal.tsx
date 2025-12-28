/**
 * Catalog Entry Modal
 *
 * Modal for displaying detailed catalog entry information including confidence scores.
 */

'use client';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScoreBadge } from '@/components/ScoreBadge';
import { cn } from '@/lib/utils';
import { GitBranch, GitCommit, Calendar, Download, ExternalLink, Loader2 } from 'lucide-react';
import { HeuristicScoreBreakdown } from '@/components/HeuristicScoreBreakdown';
import type { CatalogEntry, ArtifactType, CatalogStatus } from '@/types/marketplace';

interface CatalogEntryModalProps {
  entry: CatalogEntry | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImport?: (entry: CatalogEntry) => void;
  isImporting?: boolean;
}

/**
 * Format ISO date string to human-readable format
 */
function formatDate(isoDate: string): string {
  const date = new Date(isoDate);
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

/**
 * Shorten SHA to first 7 characters
 */
function shortenSha(sha: string): string {
  return sha.slice(0, 7);
}

// Type badge color configuration
const typeConfig: Record<ArtifactType, { label: string; color: string }> = {
  skill: { label: 'Skill', color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' },
  command: { label: 'Command', color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' },
  agent: { label: 'Agent', color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' },
  mcp_server: { label: 'MCP', color: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200' },
  hook: { label: 'Hook', color: 'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200' },
};

// Status badge configuration
const statusConfig: Record<CatalogStatus, { label: string; className: string }> = {
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
};

export function CatalogEntryModal({
  entry,
  open,
  onOpenChange,
  onImport,
  isImporting = false,
}: CatalogEntryModalProps) {
  if (!entry) return null;

  // Determine if import button should be disabled
  const isImportDisabled = entry.status === 'imported' || entry.status === 'removed' || isImporting;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl h-[85vh] flex flex-col overflow-hidden">
        <DialogHeader>
          <DialogTitle>Catalog Entry Details</DialogTitle>
          <DialogDescription className="sr-only">
            Detailed view of the {entry.name} artifact including confidence scores, metadata, and import options
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto overflow-x-hidden min-h-0 py-4">
          <div className="grid gap-6">
            {/* Header Section */}
            <div className="border-b pb-4 space-y-2">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold">{entry.name}</h2>
                <div className="flex items-center gap-2">
                  <Badge className={typeConfig[entry.artifact_type]?.color || 'bg-gray-100'}>
                    {typeConfig[entry.artifact_type]?.label || entry.artifact_type}
                  </Badge>
                  <Badge variant="outline" className={statusConfig[entry.status]?.className}>
                    {statusConfig[entry.status]?.label || entry.status}
                  </Badge>
                </div>
              </div>
              <div className="flex items-center gap-3 min-w-0">
                <ScoreBadge
                  confidence={entry.confidence_score}
                  size="md"
                  breakdown={entry.score_breakdown}
                />
                <div className="overflow-x-auto flex-1 min-w-0">
                  <code className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded whitespace-nowrap">
                    {entry.path}
                  </code>
                </div>
              </div>
            </div>

            {/* Confidence Section */}
            <section
              aria-label="Confidence score breakdown"
              className="space-y-3 border-t pt-4"
            >
              <h3 className="text-sm font-medium">Confidence Score Breakdown</h3>
              <div className="max-h-[200px] overflow-y-auto">
                {entry.score_breakdown ? (
                  <HeuristicScoreBreakdown
                    breakdown={entry.score_breakdown}
                    variant="full"
                  />
                ) : (
                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">
                      Score breakdown not available for this entry.
                    </p>
                    <p className="text-xs text-muted-foreground/70">
                      Rescan the source to generate detailed scoring breakdown for artifacts.
                    </p>
                  </div>
                )}
              </div>
            </section>

            {/* Metadata Section - TASK-3.5 */}
            <section
              aria-label="Artifact details"
              className="space-y-4"
            >
              <h3 className="font-semibold text-sm">Metadata</h3>

              {/* Path Details */}
              <div className="space-y-2">
                <div className="grid grid-cols-[140px_1fr] gap-2 text-sm">
                  <span className="text-muted-foreground font-medium">Path:</span>
                  <div className="overflow-x-auto">
                    <code className="text-xs bg-muted px-2 py-1 rounded font-mono whitespace-nowrap">
                      {entry.path}
                    </code>
                  </div>
                </div>

                <div className="grid grid-cols-[140px_1fr] gap-2 text-sm">
                  <span className="text-muted-foreground font-medium">Upstream URL:</span>
                  <div className="overflow-x-auto">
                    <a
                      href={entry.upstream_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline inline-flex items-center gap-1 whitespace-nowrap"
                      aria-label={`View source repository for ${entry.name} on GitHub`}
                    >
                      <span>{entry.upstream_url}</span>
                      <ExternalLink className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
                    </a>
                  </div>
                </div>

                {entry.detected_version && (
                  <div className="grid grid-cols-[140px_1fr] gap-2 text-sm">
                    <span className="text-muted-foreground font-medium inline-flex items-center gap-1">
                      <GitBranch className="h-3 w-3" aria-hidden="true" />
                      Version:
                    </span>
                    <div className="overflow-x-auto">
                      <code className="text-xs bg-muted px-2 py-1 rounded font-mono whitespace-nowrap">
                        {entry.detected_version}
                      </code>
                    </div>
                  </div>
                )}

                {entry.detected_sha && (
                  <div className="grid grid-cols-[140px_1fr] gap-2 text-sm">
                    <span className="text-muted-foreground font-medium inline-flex items-center gap-1">
                      <GitCommit className="h-3 w-3" aria-hidden="true" />
                      SHA:
                    </span>
                    <div className="overflow-x-auto">
                      <code className="text-xs bg-muted px-2 py-1 rounded font-mono whitespace-nowrap">
                        {shortenSha(entry.detected_sha)}
                      </code>
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-[140px_1fr] gap-2 text-sm">
                  <span className="text-muted-foreground font-medium inline-flex items-center gap-1">
                    <Calendar className="h-3 w-3" aria-hidden="true" />
                    Detected at:
                  </span>
                  <span>{formatDate(entry.detected_at)}</span>
                </div>
              </div>
            </section>
          </div>
        </div>

        {/* Action Buttons - TASK-3.6 */}
        <DialogFooter className="flex-shrink-0 border-t pt-4 mt-auto">
          <Button
            variant="outline"
            onClick={() => window.open(entry.upstream_url, '_blank', 'noopener,noreferrer')}
            aria-label={`View ${entry.name} source repository on GitHub`}
          >
            <ExternalLink className="mr-2 h-4 w-4" aria-hidden="true" />
            View on GitHub
          </Button>

          {onImport && (
            <Button
              variant="default"
              onClick={() => onImport(entry)}
              disabled={isImportDisabled}
              aria-label={
                isImporting
                  ? `Importing ${entry.name}...`
                  : isImportDisabled
                  ? `Cannot import ${entry.name} - ${entry.status === 'imported' ? 'already imported' : 'artifact removed'}`
                  : `Import ${entry.name} artifact`
              }
            >
              {isImporting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                  Importing...
                </>
              ) : (
                <>
                  <Download className="mr-2 h-4 w-4" aria-hidden="true" />
                  Import
                </>
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
