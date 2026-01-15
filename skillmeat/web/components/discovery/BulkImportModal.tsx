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
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  Pencil,
  Package,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { useToastNotification } from '@/hooks';
import { useTrackDiscovery } from '@/lib/analytics';
import { TableSkeleton } from './skeletons';
import { ParameterEditorModal } from './ParameterEditorModal';
import { cn } from '@/lib/utils';
import type {
  BulkImportResult,
  ImportResult,
  ImportStatus,
  MatchType,
} from '@/types/discovery';
import { getReasonCodeMessage as getReasonMessage } from '@/types/discovery';
import type { ArtifactImportResult } from '@/types/notification';
import type { ArtifactType, ArtifactScope } from '@/types/artifact';
import type { ArtifactParameters } from './ParameterEditorModal';

/**
 * Discovered artifact from local filesystem with import status
 */
export interface DiscoveredArtifact {
  type: string;
  name: string;
  source?: string;
  version?: string;
  scope?: string | ArtifactScope;
  tags?: string[];
  aliases?: string[];
  description?: string;
  path: string;
  discovered_at: string;
  status?: ImportStatus;
  /** Hash-based collection matching result */
  collection_match?: {
    type: MatchType;
    matched_artifact_id: string | null;
    matched_name: string | null;
    confidence: number;
  } | null;
  /** Collection membership status */
  collection_status?: {
    in_collection: boolean;
    match_type: MatchType;
    matched_artifact_id: string | null;
  } | null;
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
 * Get the effective match type from a discovered artifact.
 * Prioritizes collection_match.type, falls back to collection_status.match_type.
 */
function getEffectiveMatchType(artifact: DiscoveredArtifact): MatchType {
  // Prefer collection_match (hash-based matching)
  if (artifact.collection_match?.type) {
    return artifact.collection_match.type;
  }
  // Fallback to collection_status.match_type
  if (artifact.collection_status?.match_type) {
    return artifact.collection_status.match_type;
  }
  return 'none';
}

/**
 * Get badge variant based on artifact's collection match status
 */
function getStatusVariant(artifact: DiscoveredArtifact): 'default' | 'secondary' | 'outline' {
  // Check for explicit skipped status first
  if (artifact.status === 'skipped') {
    return 'secondary'; // Gray for skipped
  }

  const matchType = getEffectiveMatchType(artifact);
  switch (matchType) {
    case 'none':
      return 'default'; // Green for new artifacts
    case 'exact':
    case 'hash':
      return 'outline'; // Blue for already in collection
    case 'name_type':
      return 'secondary'; // Yellow-ish for similar (needs review)
    default:
      return 'default';
  }
}

/**
 * Get status label text based on artifact's collection match status
 */
function getStatusLabel(artifact: DiscoveredArtifact): string {
  // Check for explicit skipped status first
  if (artifact.status === 'skipped') {
    return 'Skipped (marked to skip)';
  }

  const matchType = getEffectiveMatchType(artifact);
  switch (matchType) {
    case 'none':
      return 'New - Will add to Collection & Project';
    case 'exact':
    case 'hash':
      return 'Already in Collection, will add to Project';
    case 'name_type':
      return 'Similar artifact exists - Review needed';
    default:
      return 'New - Will add to Collection & Project';
  }
}

/**
 * Get result status icon and color
 */
function getResultStatusDisplay(result: ImportResult): {
  icon: React.ReactNode;
  colorClass: string;
  label: string;
} {
  switch (result.status) {
    case 'success':
      return {
        icon: <CheckCircle2 className="h-4 w-4" />,
        colorClass: 'text-green-600',
        label: 'Imported',
      };
    case 'skipped':
      return {
        icon: <AlertTriangle className="h-4 w-4" />,
        colorClass: 'text-yellow-600',
        label: 'Skipped',
      };
    case 'failed':
      return {
        icon: <XCircle className="h-4 w-4" />,
        colorClass: 'text-red-600',
        label: 'Failed',
      };
    default:
      return {
        icon: <AlertTriangle className="h-4 w-4" />,
        colorClass: 'text-gray-500',
        label: 'Unknown',
      };
  }
}

/**
 * Import Results Summary Component
 */
function ImportResultsSummary({
  results,
  onClose,
  onViewDetails,
}: {
  results: BulkImportResult;
  onClose: () => void;
  onViewDetails: () => void;
}) {
  const hasIssues = results.total_skipped > 0 || results.total_failed > 0;

  return (
    <div className="space-y-4">
      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4 p-4 bg-muted/50 rounded-lg">
        <div className="text-center">
          <div className="text-2xl font-bold text-green-600">{results.total_imported}</div>
          <div className="text-sm text-muted-foreground">Imported</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-yellow-600">{results.total_skipped}</div>
          <div className="text-sm text-muted-foreground">Skipped</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-red-600">{results.total_failed}</div>
          <div className="text-sm text-muted-foreground">Failed</div>
        </div>
      </div>

      {/* Summary Message */}
      {results.summary && (
        <p className="text-sm text-muted-foreground text-center">{results.summary}</p>
      )}

      {/* Issues Alert */}
      {hasIssues && (
        <Alert variant="default" className="border-yellow-500/50 bg-yellow-50 dark:bg-yellow-950/20">
          <AlertTriangle className="h-4 w-4 text-yellow-600" />
          <AlertDescription className="text-sm">
            Some artifacts were skipped or failed.{' '}
            <button
              onClick={onViewDetails}
              className="font-medium underline hover:no-underline"
            >
              View details
            </button>
          </AlertDescription>
        </Alert>
      )}

      {/* Duration */}
      {results.duration_ms && (
        <p className="text-xs text-muted-foreground text-center">
          Completed in {(results.duration_ms / 1000).toFixed(2)}s
        </p>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-2 pt-2">
        {hasIssues && (
          <Button variant="outline" onClick={onViewDetails}>
            View Details
          </Button>
        )}
        <Button onClick={onClose}>Done</Button>
      </div>
    </div>
  );
}

/**
 * Import Results Details Component
 */
function ImportResultsDetails({
  results,
  onBack,
  onClose,
}: {
  results: BulkImportResult;
  onBack: () => void;
  onClose: () => void;
}) {
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  const successResults = results.results.filter((r) => r.status === 'success');
  const skippedResults = results.results.filter((r) => r.status === 'skipped');
  const failedResults = results.results.filter((r) => r.status === 'failed');

  const toggleExpanded = (artifactId: string) => {
    setExpandedItems((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(artifactId)) {
        newSet.delete(artifactId);
      } else {
        newSet.add(artifactId);
      }
      return newSet;
    });
  };

  const renderResultItem = (result: ImportResult) => {
    const { icon, colorClass, label } = getResultStatusDisplay(result);
    const isExpanded = expandedItems.has(result.artifact_id);
    const hasDetails = result.details || result.error || result.skip_reason || result.reason_code;

    return (
      <div key={result.artifact_id} className="border-b last:border-b-0">
        <div
          className={cn(
            'flex items-center gap-3 p-3',
            hasDetails && 'cursor-pointer hover:bg-muted/50'
          )}
          onClick={() => hasDetails && toggleExpanded(result.artifact_id)}
          role={hasDetails ? 'button' : undefined}
          tabIndex={hasDetails ? 0 : undefined}
          onKeyDown={(e) => {
            if (hasDetails && (e.key === 'Enter' || e.key === ' ')) {
              e.preventDefault();
              toggleExpanded(result.artifact_id);
            }
          }}
        >
          <span className={colorClass}>{icon}</span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium truncate">{result.artifact_id}</span>
              <Badge variant="outline" className={cn('text-xs', colorClass)}>
                {label}
              </Badge>
            </div>
            {result.path && (
              <span className="text-xs text-muted-foreground truncate block">
                {result.path}
              </span>
            )}
          </div>
          {hasDetails && (
            <span className="text-muted-foreground">
              {isExpanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </span>
          )}
        </div>
        {isExpanded && hasDetails && (
          <div className="px-3 pb-3 pl-10 space-y-1">
            {result.reason_code && (
              <div className="text-sm">
                <span className="font-medium text-muted-foreground">Reason: </span>
                <span className={colorClass}>{getReasonMessage(result.reason_code)}</span>
              </div>
            )}
            {result.details && (
              <div className="text-sm">
                <span className="font-medium text-muted-foreground">Details: </span>
                <span className="text-muted-foreground">{result.details}</span>
              </div>
            )}
            {result.error && (
              <div className="text-sm">
                <span className="font-medium text-red-600">Error: </span>
                <span className="text-red-600">{result.error}</span>
              </div>
            )}
            {result.skip_reason && (
              <div className="text-sm">
                <span className="font-medium text-yellow-600">Skip reason: </span>
                <span className="text-yellow-600">{result.skip_reason}</span>
              </div>
            )}
            {result.tags_applied !== undefined && result.tags_applied > 0 && (
              <div className="text-sm">
                <span className="font-medium text-muted-foreground">Tags applied: </span>
                <span className="text-green-600">{result.tags_applied}</span>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* Summary Row */}
      <div className="flex items-center gap-4 text-sm">
        <span className="text-green-600 font-medium">{successResults.length} imported</span>
        <span className="text-yellow-600 font-medium">{skippedResults.length} skipped</span>
        <span className="text-red-600 font-medium">{failedResults.length} failed</span>
      </div>

      {/* Results List */}
      <div className="max-h-[400px] overflow-auto border rounded-md">
        {/* Failed Items First */}
        {failedResults.length > 0 && (
          <div>
            <div className="sticky top-0 bg-red-50 dark:bg-red-950/20 px-3 py-2 border-b font-medium text-sm text-red-600">
              Failed ({failedResults.length})
            </div>
            {failedResults.map(renderResultItem)}
          </div>
        )}

        {/* Skipped Items */}
        {skippedResults.length > 0 && (
          <div>
            <div className="sticky top-0 bg-yellow-50 dark:bg-yellow-950/20 px-3 py-2 border-b font-medium text-sm text-yellow-600">
              Skipped ({skippedResults.length})
            </div>
            {skippedResults.map(renderResultItem)}
          </div>
        )}

        {/* Success Items */}
        {successResults.length > 0 && (
          <div>
            <div className="sticky top-0 bg-green-50 dark:bg-green-950/20 px-3 py-2 border-b font-medium text-sm text-green-600">
              Imported ({successResults.length})
            </div>
            {successResults.map(renderResultItem)}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex justify-between gap-2 pt-2">
        <Button variant="ghost" onClick={onBack}>
          Back to Summary
        </Button>
        <Button onClick={onClose}>Done</Button>
      </div>
    </div>
  );
}

export function BulkImportModal({ artifacts, open, onClose, onImport }: BulkImportModalProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [skippedArtifacts, setSkippedArtifacts] = useState<Set<string>>(new Set());
  const [applyPathTags, setApplyPathTags] = useState(true);
  const [isImporting, setIsImporting] = useState(false);
  const [importResults, setImportResults] = useState<BulkImportResult | null>(null);
  const [showDetails, setShowDetails] = useState(false);

  // Parameter editor state
  const [editingArtifact, setEditingArtifact] = useState<DiscoveredArtifact | null>(null);
  const [artifactOverrides, setArtifactOverrides] = useState<Map<string, ArtifactParameters>>(new Map());

  const tracking = useTrackDiscovery();
  const { showImportResult, showError } = useToastNotification();

  // Track modal open
  useEffect(() => {
    if (open && artifacts.length > 0) {
      tracking.trackModalOpen(artifacts.length);
    }
  }, [open, artifacts.length, tracking]);

  // Reset state when modal opens/closes
  useEffect(() => {
    if (!open) {
      setImportResults(null);
      setShowDetails(false);
      setSelected(new Set());
      setSkippedArtifacts(new Set());
      setEditingArtifact(null);
      setArtifactOverrides(new Map());
    }
  }, [open]);

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
      // Get selected artifacts and apply overrides
      const selectedArtifacts = artifacts
        .filter((a) => selected.has(a.path))
        .map((artifact) => {
          const override = artifactOverrides.get(artifact.path);
          if (override) {
            return { ...artifact, ...override };
          }
          return artifact;
        });

      const skipList = Array.from(skippedArtifacts);
      const result = await onImport(selectedArtifacts, skipList, applyPathTags);

      const duration = Date.now() - startTime;

      // Store results for display
      setImportResults(result);

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
      setImportResults(null);
      setShowDetails(false);
      setEditingArtifact(null);
      setArtifactOverrides(new Map());
      onClose();
    }
  };

  const handleEdit = (artifact: DiscoveredArtifact) => {
    // Get existing overrides if any
    const override = artifactOverrides.get(artifact.path);
    const effectiveArtifact = override ? { ...artifact, ...override } : artifact;
    setEditingArtifact(effectiveArtifact);
  };

  const handleParameterSave = async (parameters: ArtifactParameters) => {
    if (editingArtifact) {
      setArtifactOverrides((prev) => {
        const newMap = new Map(prev);
        newMap.set(editingArtifact.path, parameters);
        return newMap;
      });
      setEditingArtifact(null);
    }
  };

  // Determine which view to show
  const showResultsSummary = importResults !== null && !showDetails;
  const showResultsDetails = importResults !== null && showDetails;
  const showSelectionView = importResults === null;

  return (
    <Dialog open={open} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="sm:max-w-[900px] max-h-[80vh] flex flex-col">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-primary/10 p-2">
              <Package className="h-5 w-5 text-primary" aria-hidden="true" />
            </div>
            <div>
              <DialogTitle>
                {showResultsSummary || showResultsDetails
                  ? 'Import Results'
                  : 'Review Discovered Artifacts'}
              </DialogTitle>
              <DialogDescription>
                {showResultsSummary || showResultsDetails
                  ? `Processed ${importResults?.total_requested || 0} artifacts`
                  : `Select artifacts to import into your collection (${artifacts.length} discovered)`}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {isImporting && (
          <span className="sr-only" role="status" aria-live="polite">
            Importing {selected.size} artifacts, please wait...
          </span>
        )}

        {/* Results Summary View */}
        {showResultsSummary && importResults && (
          <ImportResultsSummary
            results={importResults}
            onClose={handleClose}
            onViewDetails={() => setShowDetails(true)}
          />
        )}

        {/* Results Details View */}
        {showResultsDetails && importResults && (
          <ImportResultsDetails
            results={importResults}
            onBack={() => setShowDetails(false)}
            onClose={handleClose}
          />
        )}

        {/* Selection View */}
        {showSelectionView && (
          <>
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

                        // Apply overrides for display
                        const override = artifactOverrides.get(artifact.path);
                        const effectiveArtifact = override ? { ...artifact, ...override } : artifact;
                        const isModified = !!override;

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
                            <TableCell className="font-medium">
                              {artifact.name}
                              {isModified && (
                                <Badge variant="outline" className="ml-2 text-[10px] h-4 px-1 text-primary border-primary/20">
                                  Edited
                                </Badge>
                              )}
                            </TableCell>
                            <TableCell>
                              <code className={cn("text-xs bg-muted px-1.5 py-0.5 rounded", isModified && override?.version && override.version !== artifact.version && "bg-primary/10 text-primary")}>
                                {effectiveArtifact.version || '---'}
                              </code>
                            </TableCell>
                            <TableCell>
                              <span
                                className={cn("font-mono text-xs truncate block max-w-[200px]", isModified && override?.source && override.source !== artifact.source && "text-primary")}
                                title={effectiveArtifact.source}
                              >
                                {effectiveArtifact.source || '---'}
                              </span>
                            </TableCell>
                            <TableCell onClick={(e) => e.stopPropagation()}>
                              <Badge variant={getStatusVariant(artifact)} className="text-xs">
                                {getStatusLabel(artifact)}
                              </Badge>
                            </TableCell>
                            <TableCell onClick={(e) => e.stopPropagation()}>
                              <div className="flex items-center gap-2">
                                <Checkbox
                                  id={`skip-${artifact.path}`}
                                  checked={isMarkedToSkip}
                                  onCheckedChange={(checked) =>
                                    handleSkipToggle(artifact, checked === true)
                                  }
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
                                className={cn(isModified && "text-primary")}
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
                <Label htmlFor="apply-path-tags" className="text-sm cursor-pointer">
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
          </>
        )}
      </DialogContent>

      {/* Parameter Editor */}
      {editingArtifact && (
        <ParameterEditorModal
          artifact={{
            name: editingArtifact.name,
            type: editingArtifact.type as ArtifactType,
            source: editingArtifact.source,
            version: editingArtifact.version,
            scope: (editingArtifact.scope as ArtifactScope) || 'user',
            tags: editingArtifact.tags,
            aliases: editingArtifact.aliases,
          }}
          open={!!editingArtifact}
          onClose={() => setEditingArtifact(null)}
          onSave={handleParameterSave}
        />
      )}
    </Dialog>
  );
}
