'use client';

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Loader2, Pencil, Package } from 'lucide-react';
import { useToastNotification } from '@/hooks/use-toast-notification';
import { useTrackDiscovery } from '@/lib/analytics';
import { TableSkeleton } from './skeletons';
import type { BulkImportResult, ImportStatus } from '@/types/discovery';
import type { ArtifactImportResult } from '@/types/notification';

/**
 * Discovered artifact from local filesystem with import status
 */
export interface DiscoveredArtifact {
  type: string;
  name: string;
  source?: string;
  version?: string;
  scope?: string;
  tags?: string[];
  description?: string;
  path: string;
  discovered_at: string;
  status?: ImportStatus;
}

export interface BulkImportModalProps {
  artifacts: DiscoveredArtifact[];
  open: boolean;
  onClose: () => void;
  onImport: (
    selected: DiscoveredArtifact[],
    skipList?: string[],
    applyPathTags?: boolean
  ) => Promise<BulkImportResult>;
}

/**
 * Get badge variant based on import status
 */
function getStatusVariant(status?: ImportStatus): 'default' | 'secondary' | 'outline' {
  switch (status) {
    case 'success':
      return 'default'; // Green for new artifacts
    case 'skipped':
      return 'secondary'; // Gray for skipped
    default:
      return 'outline'; // Blue for existing in collection
  }
}

/**
 * Get status label text
 */
function getStatusLabel(status?: ImportStatus): string {
  switch (status) {
    case 'success':
      return 'Will add to Collection & Project';
    case 'skipped':
      return 'Skipped (marked to skip)';
    default:
      return 'Already in Collection, will add to Project';
  }
}

export function BulkImportModal({ artifacts, open, onClose, onImport }: BulkImportModalProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [skippedArtifacts, setSkippedArtifacts] = useState<Set<string>>(new Set());
  const [applyPathTags, setApplyPathTags] = useState(true);
  const [isImporting, setIsImporting] = useState(false);
  const tracking = useTrackDiscovery();
  const { showImportResult, showError } = useToastNotification();

  // Track modal open
  useEffect(() => {
    if (open && artifacts.length > 0) {
      tracking.trackModalOpen(artifacts.length);
    }
  }, [open, artifacts.length, tracking]);

  const isAllSelected = artifacts.length > 0 && selected.size === artifacts.length;
  const isPartiallySelected = selected.size > 0 && selected.size < artifacts.length;

  const toggleSelectAll = () => {
    if (isAllSelected) {
      setSelected(new Set());
    } else {
      setSelected(new Set(artifacts.map((a) => a.path)));
    }
  };

  const toggleSelect = (path: string) => {
    const newSelected = new Set(selected);
    if (newSelected.has(path)) {
      newSelected.delete(path);
    } else {
      newSelected.add(path);
    }
    setSelected(newSelected);
  };

  const handleSkipToggle = (artifact: DiscoveredArtifact, checked: boolean) => {
    setSkippedArtifacts((prev) => {
      const newSet = new Set(prev);
      const key = `${artifact.type}:${artifact.name}`;
      if (checked) {
        newSet.add(key);
      } else {
        newSet.delete(key);
      }
      return newSet;
    });
  };

  const handleImport = async () => {
    if (selected.size === 0) return;

    setIsImporting(true);
    const startTime = Date.now();
    try {
      const selectedArtifacts = artifacts.filter((a) => selected.has(a.path));
      const skipList = Array.from(skippedArtifacts);
      const result = await onImport(selectedArtifacts, skipList, applyPathTags);

      const duration = Date.now() - startTime;

      // Map import results to notification format
      const artifactResults: ArtifactImportResult[] = result.results.map((r, idx) => {
        const artifact = selectedArtifacts[idx];
        return {
          name: artifact?.name || r.artifact_id,
          type: (artifact?.type as ArtifactImportResult['type']) || 'skill',
          success: r.status === 'success',
          error: r.error,
        };
      });

      // Show success toast and create notification with detailed results
      showImportResult({
        total_imported: result.total_imported,
        total_failed: result.total_failed,
        artifacts: artifactResults,
      });

      // Track import
      tracking.trackImport({
        total_requested: result.total_requested,
        total_imported: result.total_imported,
        total_failed: result.total_failed,
        duration_ms: duration,
      });

      // Reset state and close
      setSelected(new Set());
      onClose();
    } catch (error) {
      console.error('Import failed:', error);
      showError(error, 'Import failed');

      // Track failed import
      const duration = Date.now() - startTime;
      tracking.trackImport({
        total_requested: selected.size,
        total_imported: 0,
        total_failed: selected.size,
        duration_ms: duration,
      });
    } finally {
      setIsImporting(false);
    }
  };

  const handleClose = () => {
    if (!isImporting) {
      setSelected(new Set());
      setSkippedArtifacts(new Set());
      onClose();
    }
  };

  const handleEdit = (artifact: DiscoveredArtifact) => {
    // TODO: Implement parameter editor
    console.log('Edit artifact:', artifact);
  };

  return (
    <Dialog open={open} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent
        className="sm:max-w-[900px] max-h-[80vh] flex flex-col"
      >
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-primary/10 p-2">
              <Package className="h-5 w-5 text-primary" aria-hidden="true" />
            </div>
            <div>
              <DialogTitle>Review Discovered Artifacts</DialogTitle>
              <DialogDescription>
                Select artifacts to import into your collection ({artifacts.length} discovered)
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {isImporting && (
          <span className="sr-only" role="status" aria-live="polite">
            Importing {selected.size} artifacts, please wait...
          </span>
        )}

        <div className="flex-1 overflow-auto border rounded-md" aria-busy={isImporting}>
          {isImporting ? (
            <div className="p-4">
              <TableSkeleton rows={artifacts.length > 5 ? 5 : artifacts.length} />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">
                    <Checkbox
                      checked={isAllSelected}
                      onCheckedChange={toggleSelectAll}
                      aria-label="Select all artifacts"
                      data-indeterminate={isPartiallySelected}
                    />
                  </TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Version</TableHead>
                  <TableHead className="min-w-[200px]">Source</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Skip Future</TableHead>
                  <TableHead className="w-20">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {artifacts.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                      No artifacts discovered
                    </TableCell>
                  </TableRow>
                ) : (
                  artifacts.map((artifact) => {
                    const artifactKey = `${artifact.type}:${artifact.name}`;
                    const isSkipped = artifact.status === 'skipped';
                    const isMarkedToSkip = skippedArtifacts.has(artifactKey);

                    return (
                      <TableRow
                        key={artifact.path}
                        data-state={selected.has(artifact.path) ? 'selected' : undefined}
                        className="cursor-pointer"
                        onClick={() => toggleSelect(artifact.path)}
                      >
                        <TableCell onClick={(e) => e.stopPropagation()}>
                          <Checkbox
                            checked={selected.has(artifact.path)}
                            onCheckedChange={() => toggleSelect(artifact.path)}
                            aria-label={`Select ${artifact.name}`}
                          />
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">{artifact.type}</Badge>
                        </TableCell>
                        <TableCell className="font-medium">{artifact.name}</TableCell>
                        <TableCell>
                          <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
                            {artifact.version || '—'}
                          </code>
                        </TableCell>
                        <TableCell>
                          <span className="font-mono text-xs truncate block max-w-[200px]" title={artifact.source}>
                            {artifact.source || '—'}
                          </span>
                        </TableCell>
                        <TableCell onClick={(e) => e.stopPropagation()}>
                          <Badge variant={getStatusVariant(artifact.status)} className="text-xs">
                            {getStatusLabel(artifact.status)}
                          </Badge>
                        </TableCell>
                        <TableCell onClick={(e) => e.stopPropagation()}>
                          <div className="flex items-center gap-2">
                            <Checkbox
                              id={`skip-${artifact.path}`}
                              checked={isMarkedToSkip}
                              onCheckedChange={(checked) => handleSkipToggle(artifact, checked === true)}
                              disabled={isSkipped || isImporting}
                              aria-label={`Don't show ${artifact.name} in future discoveries`}
                            />
                            <Label
                              htmlFor={`skip-${artifact.path}`}
                              className="text-xs text-muted-foreground cursor-pointer"
                            >
                              Skip
                            </Label>
                          </div>
                        </TableCell>
                        <TableCell onClick={(e) => e.stopPropagation()}>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleEdit(artifact)}
                            disabled={isImporting}
                            aria-label={`Edit ${artifact.name}`}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          )}
        </div>

        <DialogFooter>
          {/* Path Tags Option */}
          <div className="flex items-center gap-2 py-2 border-t">
            <Checkbox
              id="apply-path-tags"
              checked={applyPathTags}
              onCheckedChange={(checked) => setApplyPathTags(checked === true)}
              disabled={isImporting}
            />
            <Label
              htmlFor="apply-path-tags"
              className="text-sm cursor-pointer"
            >
              Apply approved path tags
            </Label>
            <span className="text-xs text-muted-foreground">
              Automatically tag artifacts based on their source path
            </span>
          </div>

          <div className="flex items-center justify-between w-full">
            <div className="text-sm text-muted-foreground">
              {selected.size > 0 && `${selected.size} selected`}
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={handleClose} disabled={isImporting}>
                Cancel
              </Button>
              <Button onClick={handleImport} disabled={selected.size === 0 || isImporting}>
                {isImporting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Importing...
                  </>
                ) : (
                  `Import ${selected.size > 0 ? `(${selected.size})` : ''}`
                )}
              </Button>
            </div>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
