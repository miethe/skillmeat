/**
 * Main merge workflow dialog
 * Orchestrates the full merge process through multiple steps
 */
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
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  GitMerge,
  Loader2,
} from 'lucide-react';
import { MergePreviewView } from './merge-preview-view';
import { ConflictList } from './conflict-list';
import { ConflictResolver } from './conflict-resolver';
import { MergeStrategySelector } from './merge-strategy-selector';
import { MergeProgressIndicator } from './merge-progress-indicator';
import { useMergeResultToast } from './merge-result-toast';
import {
  useAnalyzeMerge,
  usePreviewMerge,
  useExecuteMerge,
  useResolveConflict,
} from '@/hooks/use-merge';
import type {
  MergeAnalyzeRequest,
  MergeWorkflowState,
  ConflictMetadata,
  ConflictResolveRequest,
} from '@/types/merge';
import { cn } from '@/lib/utils';

interface MergeWorkflowDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  baseSnapshotId: string;
  localCollection: string;
  remoteSnapshotId: string;
  remoteCollection?: string;
  onComplete?: () => void;
}

const WORKFLOW_STEPS = [
  { id: 'analyze', label: 'Analyze' },
  { id: 'preview', label: 'Preview' },
  { id: 'resolve', label: 'Resolve' },
  { id: 'confirm', label: 'Confirm' },
  { id: 'execute', label: 'Execute' },
] as const;

export function MergeWorkflowDialog({
  open,
  onOpenChange,
  baseSnapshotId,
  localCollection,
  remoteSnapshotId,
  remoteCollection,
  onComplete,
}: MergeWorkflowDialogProps) {
  const [workflowState, setWorkflowState] = useState<MergeWorkflowState>({
    step: 'analyze',
    unresolvedConflicts: [],
    resolvedConflicts: new Map(),
    strategy: 'auto',
  });

  const [selectedConflict, setSelectedConflict] =
    useState<ConflictMetadata | null>(null);

  const analyzeMerge = useAnalyzeMerge();
  const previewMerge = usePreviewMerge();
  const executeMerge = useExecuteMerge();
  const resolveConflict = useResolveConflict();
  const { showSuccess, showError, showConflictResolved } = useMergeResultToast();

  // Auto-analyze on open
  useEffect(() => {
    if (open && workflowState.step === 'analyze') {
      handleAnalyze();
    }
  }, [open]);

  const mergeRequest: MergeAnalyzeRequest = {
    baseSnapshotId,
    localCollection,
    remoteSnapshotId,
    remoteCollection,
  };

  const handleAnalyze = async () => {
    try {
      const analysis = await analyzeMerge.mutateAsync(mergeRequest);
      setWorkflowState((prev) => ({
        ...prev,
        analysis,
        unresolvedConflicts: analysis.conflicts,
        step: 'preview',
      }));
    } catch (error) {
      showError(error instanceof Error ? error.message : 'Analysis failed');
    }
  };

  const handlePreview = async () => {
    try {
      const preview = await previewMerge.mutateAsync(mergeRequest);
      setWorkflowState((prev) => ({
        ...prev,
        preview,
        step:
          preview.potentialConflicts.length > 0 &&
          prev.strategy !== 'auto'
            ? 'resolve'
            : 'confirm',
      }));
    } catch (error) {
      showError(error instanceof Error ? error.message : 'Preview failed');
    }
  };

  const handleResolveConflict = async (resolution: ConflictResolveRequest) => {
    try {
      await resolveConflict.mutateAsync(resolution);

      setWorkflowState((prev) => {
        const newResolved = new Map(prev.resolvedConflicts);
        newResolved.set(resolution.filePath, resolution);

        const newUnresolved = prev.unresolvedConflicts.filter(
          (c) => c.filePath !== resolution.filePath
        );

        return {
          ...prev,
          resolvedConflicts: newResolved,
          unresolvedConflicts: newUnresolved,
        };
      });

      showConflictResolved(resolution.filePath);

      // Auto-select next unresolved conflict
      const remainingConflicts = workflowState.unresolvedConflicts.filter(
        (c) => c.filePath !== resolution.filePath
      );
      if (remainingConflicts.length > 0) {
        setSelectedConflict(remainingConflicts[0] ?? null);
      } else {
        setSelectedConflict(null);
      }
    } catch (error) {
      showError(
        error instanceof Error ? error.message : 'Failed to resolve conflict'
      );
    }
  };

  const handleExecute = async () => {
    try {
      setWorkflowState((prev) => ({ ...prev, step: 'execute' }));

      const result = await executeMerge.mutateAsync({
        ...mergeRequest,
        autoSnapshot: true,
      });

      if (result.success) {
        showSuccess(result.filesMerged.length, result.conflicts.length);
        onComplete?.();
        onOpenChange(false);
      } else {
        showError(result.error || 'Merge execution failed');
      }
    } catch (error) {
      showError(error instanceof Error ? error.message : 'Execution failed');
    }
  };

  const handleNext = () => {
    const currentIndex = WORKFLOW_STEPS.findIndex(
      (s) => s.id === workflowState.step
    );
    if (currentIndex < WORKFLOW_STEPS.length - 1) {
      const nextStep = WORKFLOW_STEPS[currentIndex + 1]?.id;

      if (nextStep === 'preview') {
        handlePreview();
      } else if (nextStep === 'execute') {
        handleExecute();
      } else if (nextStep) {
        setWorkflowState((prev) => ({ ...prev, step: nextStep }));
      }
    }
  };

  const handleBack = () => {
    const currentIndex = WORKFLOW_STEPS.findIndex(
      (s) => s.id === workflowState.step
    );
    if (currentIndex > 0) {
      const prevStep = WORKFLOW_STEPS[currentIndex - 1]?.id;
      if (prevStep) {
        setWorkflowState((prev) => ({ ...prev, step: prevStep }));
      }
    }
  };

  const canProceed = () => {
    switch (workflowState.step) {
      case 'analyze':
        return !!workflowState.analysis;
      case 'preview':
        return !!workflowState.preview;
      case 'resolve':
        return workflowState.unresolvedConflicts.length === 0;
      case 'confirm':
        return true;
      case 'execute':
        return false;
      default:
        return false;
    }
  };

  const getCurrentStepIndex = () =>
    WORKFLOW_STEPS.findIndex((s) => s.id === workflowState.step);

  const progressPercentage =
    ((getCurrentStepIndex() + 1) / WORKFLOW_STEPS.length) * 100;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[900px] max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <GitMerge className="h-5 w-5" />
            <DialogTitle>Merge Workflow</DialogTitle>
          </div>
          <DialogDescription>
            Merge changes from snapshot {remoteSnapshotId} into {localCollection}
          </DialogDescription>
        </DialogHeader>

        {/* Step Indicator */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            {WORKFLOW_STEPS.map((step, index) => (
              <div key={step.id} className="flex items-center flex-1">
                <div
                  className={cn(
                    'flex items-center gap-2 flex-1',
                    index < getCurrentStepIndex() && 'opacity-50'
                  )}
                >
                  <div
                    className={cn(
                      'h-8 w-8 rounded-full flex items-center justify-center text-xs font-semibold',
                      workflowState.step === step.id
                        ? 'bg-primary text-primary-foreground'
                        : index < getCurrentStepIndex()
                        ? 'bg-green-600 text-white'
                        : 'bg-muted text-muted-foreground'
                    )}
                  >
                    {index < getCurrentStepIndex() ? (
                      <CheckCircle className="h-4 w-4" />
                    ) : (
                      index + 1
                    )}
                  </div>
                  <span
                    className={cn(
                      'text-sm font-medium',
                      workflowState.step === step.id && 'text-primary'
                    )}
                  >
                    {step.label}
                  </span>
                </div>
                {index < WORKFLOW_STEPS.length - 1 && (
                  <div className="h-0.5 w-8 bg-muted mx-2" />
                )}
              </div>
            ))}
          </div>
          <Progress value={progressPercentage} className="h-1" />
        </div>

        {/* Step Content */}
        <div className="flex-1 overflow-y-auto">
          {workflowState.step === 'analyze' && (
            <div className="py-12 text-center">
              {analyzeMerge.isPending ? (
                <>
                  <Loader2 className="h-12 w-12 mx-auto mb-4 animate-spin text-primary" />
                  <p className="text-muted-foreground">Analyzing merge safety...</p>
                </>
              ) : (
                <>
                  <GitMerge className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p className="text-muted-foreground">
                    Ready to analyze merge compatibility
                  </p>
                </>
              )}
            </div>
          )}

          {workflowState.step === 'preview' && (
            <MergePreviewView
              preview={workflowState.preview ?? null}
              isLoading={previewMerge.isPending}
            />
          )}

          {workflowState.step === 'resolve' && (
            <div className="grid grid-cols-2 gap-4">
              <ConflictList
                conflicts={[
                  ...workflowState.unresolvedConflicts,
                  ...(workflowState.analysis?.conflicts ?? []).filter((c) =>
                    workflowState.resolvedConflicts.has(c.filePath)
                  ),
                ]}
                selectedConflict={selectedConflict ?? undefined}
                onSelectConflict={setSelectedConflict}
                resolvedConflicts={
                  new Set(workflowState.resolvedConflicts.keys())
                }
              />
              <ConflictResolver
                conflict={selectedConflict ?? null}
                onResolve={handleResolveConflict}
                isResolving={resolveConflict.isPending}
              />
            </div>
          )}

          {workflowState.step === 'confirm' && (
            <div className="space-y-4">
              <MergeStrategySelector
                value={workflowState.strategy}
                onChange={(strategy) =>
                  setWorkflowState((prev) => ({ ...prev, strategy }))
                }
              />
              {workflowState.preview && (
                <div className="rounded-lg border p-4 space-y-2">
                  <p className="font-semibold">Summary</p>
                  <div className="grid grid-cols-3 gap-2 text-sm">
                    <div>
                      <span className="text-muted-foreground">Files to merge:</span>
                      <span className="ml-2 font-semibold">
                        {workflowState.preview.filesAdded.length +
                          workflowState.preview.filesChanged.length}
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">
                        Conflicts resolved:
                      </span>
                      <span className="ml-2 font-semibold">
                        {workflowState.resolvedConflicts.size}
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Strategy:</span>
                      <Badge variant="outline" className="ml-2">
                        {workflowState.strategy}
                      </Badge>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {workflowState.step === 'execute' && (
            <MergeProgressIndicator
              filesTotal={
                (workflowState.preview?.filesAdded.length ?? 0) +
                (workflowState.preview?.filesChanged.length ?? 0)
              }
              filesProcessed={0}
              fileStatuses={[]}
            />
          )}
        </div>

        {/* Footer */}
        <DialogFooter>
          <div className="flex items-center justify-between w-full">
            <Button
              variant="outline"
              onClick={handleBack}
              disabled={
                getCurrentStepIndex() === 0 ||
                analyzeMerge.isPending ||
                previewMerge.isPending ||
                executeMerge.isPending
              }
            >
              <ChevronLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
            <Button
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={executeMerge.isPending}
            >
              Cancel
            </Button>
            {workflowState.step !== 'execute' && (
              <Button
                onClick={handleNext}
                disabled={
                  !canProceed() ||
                  analyzeMerge.isPending ||
                  previewMerge.isPending
                }
              >
                {workflowState.step === 'confirm' ? 'Execute Merge' : 'Next'}
                <ChevronRight className="h-4 w-4 ml-2" />
              </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
