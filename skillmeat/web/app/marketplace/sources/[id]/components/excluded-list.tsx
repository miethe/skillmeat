'use client';

/**
 * ExcludedArtifactsList Component
 *
 * Displays a collapsible list of excluded catalog entries with restore functionality.
 * Uses Radix Collapsible primitive for expand/collapse behavior.
 */

import { useState } from 'react';
import { ChevronDown, ChevronUp, RotateCcw, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useRestoreCatalogEntry } from '@/hooks';
import type { CatalogEntry } from '@/types/marketplace';

export interface ExcludedArtifactsListProps {
  /** Array of excluded catalog entries to display */
  entries: CatalogEntry[];
  /** Source ID for the restore mutation */
  sourceId: string;
}

/**
 * Formats a date string to a relative format for display.
 * Returns 'Unknown' if date is null/undefined.
 */
function formatRelativeDate(dateString: string | null | undefined): string {
  if (!dateString) return 'Unknown';

  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  return date.toLocaleDateString();
}

/**
 * ExcludedArtifactsList displays excluded catalog entries in a collapsible table.
 *
 * Features:
 * - Collapsible section (collapsed by default)
 * - Count indicator in header
 * - Table with Name, Path, Excluded date, and Restore action
 * - Restore button calls useRestoreCatalogEntry hook
 * - Returns null if no excluded entries (hidden section)
 */
export function ExcludedArtifactsList({ entries, sourceId }: ExcludedArtifactsListProps) {
  const [isOpen, setIsOpen] = useState(false);
  const restoreMutation = useRestoreCatalogEntry(sourceId);

  // Don't render anything if no excluded entries
  if (entries.length === 0) {
    return null;
  }

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className="mt-6">
      <CollapsibleTrigger asChild>
        <Button
          variant="ghost"
          className="flex items-center gap-2 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          aria-label={
            isOpen
              ? `Collapse excluded artifacts list (${entries.length} items)`
              : `Expand excluded artifacts list (${entries.length} items)`
          }
        >
          {isOpen ? (
            <ChevronUp className="h-4 w-4" aria-hidden="true" />
          ) : (
            <ChevronDown className="h-4 w-4" aria-hidden="true" />
          )}
          Show Excluded Artifacts ({entries.length})
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className="mt-4">
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Path</TableHead>
                <TableHead>Excluded</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {entries.map((entry) => (
                <TableRow key={entry.id}>
                  <TableCell className="font-medium">{entry.name}</TableCell>
                  <TableCell className="max-w-[200px] truncate text-sm text-muted-foreground">
                    {entry.path}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatRelativeDate(entry.excluded_at)}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => restoreMutation.mutate(entry.id)}
                      disabled={restoreMutation.isPending}
                      aria-label={`Restore ${entry.name} to catalog`}
                    >
                      {restoreMutation.isPending ? (
                        <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
                      ) : (
                        <>
                          <RotateCcw className="mr-1 h-3 w-3" aria-hidden="true" />
                          Restore
                        </>
                      )}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
