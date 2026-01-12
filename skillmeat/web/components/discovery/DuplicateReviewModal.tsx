'use client';

import { useState, useMemo, useCallback } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Loader2,
  Package,
  CheckCircle2,
  AlertTriangle,
  Link2,
  Plus,
  XCircle,
  FileQuestion,
} from 'lucide-react';
import { useToastNotification } from '@/hooks';
import { cn } from '@/lib/utils';
import { DuplicateReviewTab } from './DuplicateReviewTab';
import type {
  DiscoveredArtifact,
  DuplicateMatch,
  DuplicateDecisionAction,
  ConfirmDuplicatesResponse,
} from '@/types/discovery';

/**
 * State for tracking duplicate review decisions
 */
interface DuplicateReviewState {
  /** Map of discovered path -> { collection_id, action } for duplicates */
  matches: Map<string, { collection_id: string; action: DuplicateDecisionAction }>;
  /** Set of paths to import as new artifacts */
  newArtifacts: Set<string>;
  /** Set of paths to skip */
  skipped: Set<string>;
}

export interface DuplicateReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  artifacts: DiscoveredArtifact[];
  projectPath: string;
  onConfirm: (
    matches: DuplicateMatch[],
    newArtifacts: string[],
    skipped: string[]
  ) => Promise<ConfirmDuplicatesResponse>;
}

/**
 * Categorize artifacts by their collection match status
 */
function categorizeArtifacts(artifacts: DiscoveredArtifact[]) {
  const newArtifacts: DiscoveredArtifact[] = [];
  const possibleDuplicates: DiscoveredArtifact[] = [];
  const exactMatches: DiscoveredArtifact[] = [];

  for (const artifact of artifacts) {
    const match = artifact.collection_match;

    if (!match || match.type === 'none') {
      newArtifacts.push(artifact);
    } else if (match.type === 'exact' || match.type === 'hash') {
      // Exact hash match - high confidence duplicate
      exactMatches.push(artifact);
    } else if (match.type === 'name_type') {
      // Name+type match - possible duplicate, needs review
      possibleDuplicates.push(artifact);
    } else {
      // Fallback: treat as new
      newArtifacts.push(artifact);
    }
  }

  return { newArtifacts, possibleDuplicates, exactMatches };
}

/**
 * Get tab badge variant based on count
 */
function getBadgeVariant(count: number): 'default' | 'secondary' | 'outline' {
  if (count === 0) return 'outline';
  return 'secondary';
}

/**
 * DuplicateReviewModal Component
 *
 * Comprehensive modal for reviewing discovered artifacts against collection.
 * Shows three tabs:
 * - New Artifacts: Ready to import, no duplicates found
 * - Possible Duplicates: Name/type matches that need user decision
 * - Exact Matches: Hash-matched duplicates that can be linked or skipped
 */
export function DuplicateReviewModal({
  isOpen,
  onClose,
  artifacts,
  projectPath: _projectPath,
  onConfirm,
}: DuplicateReviewModalProps) {
  const [activeTab, setActiveTab] = useState('new');
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingResult, setProcessingResult] = useState<ConfirmDuplicatesResponse | null>(null);
  const { showSuccess, showError } = useToastNotification();

  // State for tracking user decisions
  const [state, setState] = useState<DuplicateReviewState>({
    matches: new Map(),
    newArtifacts: new Set(),
    skipped: new Set(),
  });

  // Categorize artifacts
  const { newArtifacts, possibleDuplicates, exactMatches } = useMemo(
    () => categorizeArtifacts(artifacts),
    [artifacts]
  );

  // Initialize state when modal opens
  useMemo(() => {
    if (isOpen && artifacts.length > 0) {
      const initialMatches = new Map<string, { collection_id: string; action: DuplicateDecisionAction }>();
      const initialNew = new Set<string>();
      const initialSkipped = new Set<string>();

      // Initialize exact matches with 'link' action by default
      for (const artifact of exactMatches) {
        if (artifact.collection_match?.matched_artifact_id) {
          initialMatches.set(artifact.path, {
            collection_id: artifact.collection_match.matched_artifact_id,
            action: 'link',
          });
        }
      }

      // Initialize possible duplicates with 'link' action by default
      for (const artifact of possibleDuplicates) {
        if (artifact.collection_match?.matched_artifact_id) {
          initialMatches.set(artifact.path, {
            collection_id: artifact.collection_match.matched_artifact_id,
            action: 'link',
          });
        }
      }

      // Initialize new artifacts as selected for import
      for (const artifact of newArtifacts) {
        initialNew.add(artifact.path);
      }

      setState({
        matches: initialMatches,
        newArtifacts: initialNew,
        skipped: initialSkipped,
      });
    }
  }, [isOpen, artifacts, exactMatches, possibleDuplicates, newArtifacts]);

  // Reset state when modal closes
  const handleClose = useCallback(() => {
    if (!isProcessing) {
      setProcessingResult(null);
      setActiveTab('new');
      setState({
        matches: new Map(),
        newArtifacts: new Set(),
        skipped: new Set(),
      });
      onClose();
    }
  }, [isProcessing, onClose]);

  // Toggle selection for new artifact import
  const toggleNewArtifact = useCallback((path: string) => {
    setState((prev) => {
      const newSet = new Set(prev.newArtifacts);
      const skippedSet = new Set(prev.skipped);

      if (newSet.has(path)) {
        newSet.delete(path);
        skippedSet.add(path);
      } else {
        newSet.add(path);
        skippedSet.delete(path);
      }

      return { ...prev, newArtifacts: newSet, skipped: skippedSet };
    });
  }, []);

  // Toggle all new artifacts
  const toggleAllNewArtifacts = useCallback((selected: boolean) => {
    setState((prev) => {
      if (selected) {
        // Select all new artifacts
        const allPaths = newArtifacts.map((a) => a.path);
        return {
          ...prev,
          newArtifacts: new Set(allPaths),
          skipped: new Set([...prev.skipped].filter((p) => !allPaths.includes(p))),
        };
      } else {
        // Deselect all new artifacts
        const allPaths = newArtifacts.map((a) => a.path);
        return {
          ...prev,
          newArtifacts: new Set(),
          skipped: new Set([...prev.skipped, ...allPaths]),
        };
      }
    });
  }, [newArtifacts]);

  // Update match decision for a duplicate
  const updateMatchDecision = useCallback((
    path: string,
    collectionId: string | null,
    action: DuplicateDecisionAction
  ) => {
    setState((prev) => {
      const newMatches = new Map(prev.matches);
      const newSkipped = new Set(prev.skipped);

      if (collectionId && action === 'link') {
        newMatches.set(path, { collection_id: collectionId, action: 'link' });
        newSkipped.delete(path);
      } else if (action === 'skip') {
        newMatches.delete(path);
        newSkipped.add(path);
      } else {
        // "Not a duplicate" - treat as new artifact
        newMatches.delete(path);
        newSkipped.delete(path);
      }

      return { ...prev, matches: newMatches, skipped: newSkipped };
    });
  }, []);

  // Handle confirm button click
  const handleConfirm = async () => {
    setIsProcessing(true);
    setProcessingResult(null);

    try {
      // Convert state to API format
      const matchesArray: DuplicateMatch[] = [];
      state.matches.forEach((value, discoveredPath) => {
        matchesArray.push({
          discovered_path: discoveredPath,
          collection_artifact_id: value.collection_id,
          action: value.action,
        });
      });

      const newArtifactsArray = Array.from(state.newArtifacts);
      const skippedArray = Array.from(state.skipped);

      const result = await onConfirm(matchesArray, newArtifactsArray, skippedArray);
      setProcessingResult(result);

      if (result.status === 'success') {
        showSuccess(`Processed ${result.linked_count + result.imported_count} artifacts successfully`);
      } else if (result.status === 'partial') {
        showSuccess(`Processed artifacts with some issues: ${result.message}`);
      }
    } catch (error) {
      console.error('Failed to process duplicates:', error);
      showError(error, 'Failed to process artifacts');
    } finally {
      setIsProcessing(false);
    }
  };

  // Calculate summary stats
  const stats = useMemo(() => {
    const linkedCount = Array.from(state.matches.values()).filter((m) => m.action === 'link').length;
    const importCount = state.newArtifacts.size;
    const skipCount = state.skipped.size;

    return { linkedCount, importCount, skipCount };
  }, [state]);

  // Check if there's anything to process
  const hasDecisions = stats.linkedCount > 0 || stats.importCount > 0;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="flex h-[90vh] max-h-[90vh] w-[95vw] max-w-4xl flex-col overflow-hidden p-0 sm:w-[90vw]">
        <DialogHeader className="border-b px-6 pb-4 pt-6">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-primary/10 p-2">
              <Package className="h-5 w-5 text-primary" aria-hidden="true" />
            </div>
            <div>
              <DialogTitle>Review Discovered Artifacts</DialogTitle>
              <DialogDescription>
                {processingResult
                  ? processingResult.message
                  : `${newArtifacts.length} new artifacts, ${possibleDuplicates.length} possible duplicates, ${exactMatches.length} exact matches`}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {/* Processing state indicator */}
        {isProcessing && (
          <span className="sr-only" role="status" aria-live="polite">
            Processing artifacts, please wait...
          </span>
        )}

        {/* Results View */}
        {processingResult && (
          <div className="flex flex-1 flex-col overflow-hidden px-6 py-4">
            <div className="space-y-4">
              {/* Summary Stats */}
              <div className="grid grid-cols-3 gap-4 rounded-lg bg-muted/50 p-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">{processingResult.imported_count}</div>
                  <div className="text-sm text-muted-foreground">Imported</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">{processingResult.linked_count}</div>
                  <div className="text-sm text-muted-foreground">Linked</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-600">{processingResult.skipped_count}</div>
                  <div className="text-sm text-muted-foreground">Skipped</div>
                </div>
              </div>

              {/* Status indicator */}
              {processingResult.status === 'success' && (
                <Alert>
                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                  <AlertDescription>All operations completed successfully.</AlertDescription>
                </Alert>
              )}

              {processingResult.status === 'partial' && (
                <Alert variant="default" className="border-yellow-500/50 bg-yellow-50 dark:bg-yellow-950/20">
                  <AlertTriangle className="h-4 w-4 text-yellow-600" />
                  <AlertDescription>
                    Some operations completed with issues. Check the details below.
                  </AlertDescription>
                </Alert>
              )}

              {processingResult.status === 'failed' && (
                <Alert variant="destructive">
                  <XCircle className="h-4 w-4" />
                  <AlertDescription>
                    Operation failed. Please try again or contact support.
                  </AlertDescription>
                </Alert>
              )}

              {/* Errors list */}
              {processingResult.errors.length > 0 && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-900 dark:bg-red-950/20">
                  <h4 className="mb-2 font-medium text-red-700 dark:text-red-400">Errors:</h4>
                  <ul className="list-inside list-disc space-y-1 text-sm text-red-600 dark:text-red-400">
                    {processingResult.errors.map((error, idx) => (
                      <li key={idx}>{error}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div className="mt-auto flex justify-end pt-4">
              <Button onClick={handleClose}>Done</Button>
            </div>
          </div>
        )}

        {/* Review View */}
        {!processingResult && (
          <Tabs
            value={activeTab}
            onValueChange={setActiveTab}
            className="flex min-h-0 flex-1 flex-col overflow-hidden"
          >
            <div className="border-b px-6">
              <TabsList className="h-auto w-full justify-start rounded-none bg-transparent p-0">
                <TabsTrigger
                  value="new"
                  className="gap-2 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
                >
                  <Plus className="h-4 w-4" />
                  New Artifacts
                  <Badge variant={getBadgeVariant(newArtifacts.length)}>
                    {newArtifacts.length}
                  </Badge>
                </TabsTrigger>
                <TabsTrigger
                  value="possible"
                  className="gap-2 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
                >
                  <FileQuestion className="h-4 w-4" />
                  Possible Duplicates
                  <Badge variant={getBadgeVariant(possibleDuplicates.length)}>
                    {possibleDuplicates.length}
                  </Badge>
                </TabsTrigger>
                <TabsTrigger
                  value="exact"
                  className="gap-2 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
                >
                  <Link2 className="h-4 w-4" />
                  Exact Matches
                  <Badge variant={getBadgeVariant(exactMatches.length)}>
                    {exactMatches.length}
                  </Badge>
                </TabsTrigger>
              </TabsList>
            </div>

            {/* New Artifacts Tab */}
            <TabsContent value="new" className="mt-0 flex-1 overflow-hidden">
              <ScrollArea className="h-full">
                <div className="space-y-2 p-4">
                  {newArtifacts.length === 0 ? (
                    <div className="py-12 text-center">
                      <Plus className="mx-auto mb-4 h-12 w-12 text-muted-foreground/50" />
                      <h3 className="mb-2 text-lg font-semibold">No New Artifacts</h3>
                      <p className="text-sm text-muted-foreground">
                        All discovered artifacts match existing items in your collection.
                      </p>
                    </div>
                  ) : (
                    <>
                      {/* Select all header */}
                      <div className="flex items-center justify-between border-b pb-2">
                        <div className="flex items-center gap-2">
                          <Checkbox
                            id="select-all-new"
                            checked={state.newArtifacts.size === newArtifacts.length}
                            onCheckedChange={(checked) => toggleAllNewArtifacts(checked === true)}
                            aria-label="Select all new artifacts"
                          />
                          <label
                            htmlFor="select-all-new"
                            className="text-sm font-medium cursor-pointer"
                          >
                            Select all for import
                          </label>
                        </div>
                        <span className="text-sm text-muted-foreground">
                          {state.newArtifacts.size} of {newArtifacts.length} selected
                        </span>
                      </div>

                      {/* Artifact list */}
                      {newArtifacts.map((artifact) => (
                        <div
                          key={artifact.path}
                          className={cn(
                            'flex items-center gap-3 rounded-lg border p-3 transition-colors',
                            state.newArtifacts.has(artifact.path)
                              ? 'border-primary/50 bg-primary/5'
                              : 'border-muted bg-muted/20'
                          )}
                        >
                          <Checkbox
                            checked={state.newArtifacts.has(artifact.path)}
                            onCheckedChange={() => toggleNewArtifact(artifact.path)}
                            aria-label={`Import ${artifact.name}`}
                          />
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{artifact.name}</span>
                              <Badge variant="outline" className="text-xs">
                                {artifact.type}
                              </Badge>
                            </div>
                            {artifact.description && (
                              <p className="mt-1 truncate text-sm text-muted-foreground">
                                {artifact.description}
                              </p>
                            )}
                            <p className="mt-1 truncate text-xs text-muted-foreground/70">
                              {artifact.path}
                            </p>
                          </div>
                        </div>
                      ))}
                    </>
                  )}
                </div>
              </ScrollArea>
            </TabsContent>

            {/* Possible Duplicates Tab */}
            <TabsContent value="possible" className="mt-0 flex-1 overflow-hidden">
              <DuplicateReviewTab
                artifacts={possibleDuplicates}
                matchDecisions={state.matches}
                skippedPaths={state.skipped}
                onUpdateDecision={updateMatchDecision}
              />
            </TabsContent>

            {/* Exact Matches Tab */}
            <TabsContent value="exact" className="mt-0 flex-1 overflow-hidden">
              <ScrollArea className="h-full">
                <div className="space-y-2 p-4">
                  {exactMatches.length === 0 ? (
                    <div className="py-12 text-center">
                      <Link2 className="mx-auto mb-4 h-12 w-12 text-muted-foreground/50" />
                      <h3 className="mb-2 text-lg font-semibold">No Exact Matches</h3>
                      <p className="text-sm text-muted-foreground">
                        No discovered artifacts have identical content to collection items.
                      </p>
                    </div>
                  ) : (
                    <>
                      <Alert className="mb-4">
                        <CheckCircle2 className="h-4 w-4 text-green-600" />
                        <AlertDescription>
                          These artifacts have identical content (hash match) to existing collection
                          items. They will be linked rather than duplicated.
                        </AlertDescription>
                      </Alert>

                      {exactMatches.map((artifact) => {
                        const isSkipped = state.skipped.has(artifact.path);

                        return (
                          <div
                            key={artifact.path}
                            className={cn(
                              'rounded-lg border p-3',
                              isSkipped ? 'border-muted bg-muted/20 opacity-60' : 'border-green-200 bg-green-50/50 dark:border-green-900 dark:bg-green-950/20'
                            )}
                          >
                            <div className="flex items-start justify-between gap-4">
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center gap-2">
                                  <span className="font-medium">{artifact.name}</span>
                                  <Badge variant="outline" className="text-xs">
                                    {artifact.type}
                                  </Badge>
                                  <Badge variant="default" className="gap-1 text-xs bg-green-600">
                                    <CheckCircle2 className="h-3 w-3" />
                                    100% match
                                  </Badge>
                                </div>
                                <p className="mt-1 text-sm text-muted-foreground">
                                  Matches: <span className="font-mono">{artifact.collection_match?.matched_artifact_id}</span>
                                </p>
                              </div>
                              <div className="flex items-center gap-2">
                                <Checkbox
                                  id={`skip-exact-${artifact.path}`}
                                  checked={isSkipped}
                                  onCheckedChange={(checked) =>
                                    updateMatchDecision(
                                      artifact.path,
                                      artifact.collection_match?.matched_artifact_id || null,
                                      checked ? 'skip' : 'link'
                                    )
                                  }
                                  aria-label={`Skip ${artifact.name}`}
                                />
                                <label
                                  htmlFor={`skip-exact-${artifact.path}`}
                                  className="text-sm text-muted-foreground cursor-pointer"
                                >
                                  Skip
                                </label>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </>
                  )}
                </div>
              </ScrollArea>
            </TabsContent>
          </Tabs>
        )}

        {/* Footer */}
        {!processingResult && (
          <DialogFooter className="border-t px-6 py-4">
            <div className="flex w-full items-center justify-between">
              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                {stats.importCount > 0 && (
                  <span className="flex items-center gap-1">
                    <Plus className="h-4 w-4 text-green-600" />
                    {stats.importCount} to import
                  </span>
                )}
                {stats.linkedCount > 0 && (
                  <span className="flex items-center gap-1">
                    <Link2 className="h-4 w-4 text-blue-600" />
                    {stats.linkedCount} to link
                  </span>
                )}
                {stats.skipCount > 0 && (
                  <span className="flex items-center gap-1">
                    <XCircle className="h-4 w-4 text-gray-500" />
                    {stats.skipCount} to skip
                  </span>
                )}
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={handleClose} disabled={isProcessing}>
                  Cancel
                </Button>
                <Button onClick={handleConfirm} disabled={!hasDecisions || isProcessing}>
                  {isProcessing ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    'Confirm Decisions'
                  )}
                </Button>
              </div>
            </div>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}
