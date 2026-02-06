'use client';

import { useState, useEffect, useMemo } from 'react';
import { Check, Loader2, AlertCircle, ChevronRight, AlertTriangle } from 'lucide-react';
import { DiffViewer } from './diff-viewer';
import { ConflictResolver } from './conflict-resolver';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardFooter,
} from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import { apiRequest } from '@/lib/api';
import type { ArtifactDiffResponse, ArtifactSyncResponse, FileDiff } from '@/sdk';

/**
 * Props for MergeWorkflow component
 *
 * Configuration for multi-step merge and conflict resolution workflow.
 */
interface MergeWorkflowProps {
  /** ID of the entity to sync */
  entityId: string;
  /** Path to the target project for deployment/sync */
  projectPath: string;
  /** Direction of sync: 'upstream' (project→collection) or 'downstream' (collection→project) */
  direction: 'upstream' | 'downstream';
  /** Callback when workflow completes successfully */
  onComplete: () => void;
  /** Callback when user cancels the workflow */
  onCancel: () => void;
}

type Step = 'preview' | 'resolve' | 'apply';

type ConflictResolution = 'collection' | 'project' | 'merge';

interface ConflictState {
  [filePath: string]: ConflictResolution;
}

type ConflictSeverity = 'none' | 'soft' | 'hard';

interface ConflictAnalysis {
  severity: ConflictSeverity;
  conflictCount: number;
  overlappingLines: number;
  adjacentLines: number;
  additionCount: number;
  deletionCount: number;
}

interface FileConflictInfo extends ConflictAnalysis {
  filePath: string;
}

type ProgressStage = 'preparing' | 'resolving' | 'applying' | 'finalizing' | 'complete';

interface ProgressState {
  percent: number;
  stage: ProgressStage;
  message: string;
  currentFile?: string;
  totalFiles?: number;
  currentFileIndex?: number;
}

/**
 * Analyzes a unified diff to detect conflicts and their severity
 */
function analyzeConflicts(unifiedDiff: string | null | undefined): ConflictAnalysis {
  if (!unifiedDiff) {
    return {
      severity: 'none',
      conflictCount: 0,
      overlappingLines: 0,
      adjacentLines: 0,
      additionCount: 0,
      deletionCount: 0,
    };
  }

  const lines = unifiedDiff.split('\n');
  let additionCount = 0;
  let deletionCount = 0;
  let overlappingLines = 0;
  let adjacentLines = 0;

  // Track line positions to detect overlaps
  const deletionRanges: Array<{ start: number; end: number }> = [];
  const additionRanges: Array<{ start: number; end: number }> = [];

  let currentLineNum = 0;
  let consecutiveDeletions = 0;
  let consecutiveAdditions = 0;
  let deletionStart = -1;
  let additionStart = -1;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line) continue;

    // Parse hunk header to get line numbers
    if (line.startsWith('@@')) {
      const match = line.match(/@@ -(\d+),?\d* \+(\d+),?\d* @@/);
      if (match && match[1]) {
        currentLineNum = parseInt(match[1], 10);
        consecutiveDeletions = 0;
        consecutiveAdditions = 0;
        deletionStart = -1;
        additionStart = -1;
      }
      continue;
    }

    if (line.startsWith('-') && !line.startsWith('---')) {
      deletionCount++;
      if (consecutiveDeletions === 0) {
        deletionStart = currentLineNum;
      }
      consecutiveDeletions++;
      currentLineNum++;
    } else if (line.startsWith('+') && !line.startsWith('+++')) {
      additionCount++;
      if (consecutiveAdditions === 0) {
        additionStart = currentLineNum;
      }
      consecutiveAdditions++;
    } else if (line.startsWith(' ') || (!line.startsWith('+') && !line.startsWith('-'))) {
      // Context line - save previous ranges
      if (consecutiveDeletions > 0 && deletionStart >= 0) {
        deletionRanges.push({ start: deletionStart, end: deletionStart + consecutiveDeletions });
      }
      if (consecutiveAdditions > 0 && additionStart >= 0) {
        additionRanges.push({ start: additionStart, end: additionStart + consecutiveAdditions });
      }
      consecutiveDeletions = 0;
      consecutiveAdditions = 0;
      deletionStart = -1;
      additionStart = -1;
      currentLineNum++;
    }
  }

  // Save final ranges
  if (consecutiveDeletions > 0 && deletionStart >= 0) {
    deletionRanges.push({ start: deletionStart, end: deletionStart + consecutiveDeletions });
  }
  if (consecutiveAdditions > 0 && additionStart >= 0) {
    additionRanges.push({ start: additionStart, end: additionStart + consecutiveAdditions });
  }

  // Detect overlapping and adjacent changes
  for (const delRange of deletionRanges) {
    for (const addRange of additionRanges) {
      // Check for overlap (same line numbers affected)
      if (
        (delRange.start <= addRange.end && delRange.end >= addRange.start) ||
        (addRange.start <= delRange.end && addRange.end >= delRange.start)
      ) {
        overlappingLines +=
          Math.min(delRange.end, addRange.end) - Math.max(delRange.start, addRange.start);
      }
      // Check for adjacent changes (within 2 lines)
      else if (
        Math.abs(delRange.end - addRange.start) <= 2 ||
        Math.abs(addRange.end - delRange.start) <= 2
      ) {
        adjacentLines += Math.min(delRange.end - delRange.start, addRange.end - addRange.start);
      }
    }
  }

  const conflictCount =
    overlappingLines > 0
      ? Math.ceil(overlappingLines / 3)
      : adjacentLines > 0
        ? Math.ceil(adjacentLines / 5)
        : 0;

  const severity: ConflictSeverity =
    overlappingLines > 0 ? 'hard' : adjacentLines > 0 ? 'soft' : 'none';

  return {
    severity,
    conflictCount: Math.max(conflictCount, severity === 'hard' ? 1 : 0),
    overlappingLines,
    adjacentLines,
    additionCount,
    deletionCount,
  };
}

/**
 * Analyzes all modified files for conflicts
 */
function analyzeAllConflicts(files: FileDiff[]): FileConflictInfo[] {
  return files
    .filter((file) => file.status === 'modified')
    .map((file) => ({
      filePath: file.file_path,
      ...analyzeConflicts(file.unified_diff),
    }));
}

/**
 * MergeWorkflow - Multi-step workflow for syncing entities and resolving conflicts
 *
 * Orchestrates a three-step process for syncing entities between collection and projects:
 *
 * 1. **Preview Step**: Shows diff summary with conflict detection and analysis
 *    - Displays all changed files (added, modified, deleted)
 *    - Detects and highlights conflicts (hard/soft)
 *    - Allows user to review changes before proceeding
 *
 * 2. **Resolve Step**: Interactive conflict resolution for each modified file
 *    - Shows side-by-side diff for conflicting files
 *    - Provides three resolution options: keep collection, keep project, manual merge
 *    - Displays conflict severity and change statistics
 *    - Only shown if conflicts are detected
 *
 * 3. **Apply Step**: Final review and merge execution
 *    - Shows summary of changes and selected resolutions
 *    - Displays progress during merge operation
 *    - Confirms success with final results
 *
 * @example
 * ```tsx
 * <MergeWorkflow
 *   entityId="skill:canvas-design"
 *   projectPath="/home/user/my-project"
 *   direction="downstream"
 *   onComplete={() => refreshUI()}
 *   onCancel={() => closeDialog()}
 * />
 * ```
 *
 * @param props - MergeWorkflowProps configuration
 * @returns Multi-step workflow component with progress stepper
 */
export function MergeWorkflow({
  entityId,
  projectPath,
  direction,
  onComplete,
  onCancel,
}: MergeWorkflowProps) {
  const [currentStep, setCurrentStep] = useState<Step>('preview');
  const [diffData, setDiffData] = useState<ArtifactDiffResponse | null>(null);
  const [conflictResolutions, setConflictResolutions] = useState<ConflictState>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isApplying, setIsApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncResult, setSyncResult] = useState<ArtifactSyncResponse | null>(null);

  // Load diff data on mount
  useEffect(() => {
    loadDiff();
  }, [entityId, projectPath]);

  const loadDiff = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiRequest<ArtifactDiffResponse>(
        `/artifacts/${encodeURIComponent(entityId)}/diff?project_path=${encodeURIComponent(projectPath)}`
      );
      setDiffData(response);

      // Initialize conflict resolutions for modified files
      const initialResolutions: ConflictState = {};
      response.files
        .filter((file) => file.status === 'modified')
        .forEach((file) => {
          initialResolutions[file.file_path] = 'collection'; // Default to collection
        });
      setConflictResolutions(initialResolutions);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load diff');
    } finally {
      setIsLoading(false);
    }
  };

  const handleContinueFromPreview = () => {
    if (!diffData) return;

    // Check if there are any modified files (potential conflicts)
    const hasConflicts = diffData.files.some((file) => file.status === 'modified');

    if (hasConflicts) {
      setCurrentStep('resolve');
    } else {
      // No conflicts, skip directly to apply
      setCurrentStep('apply');
    }
  };

  const handleBackToPreview = () => {
    setCurrentStep('preview');
  };

  const handleContinueFromResolve = () => {
    setCurrentStep('apply');
  };

  const handleApplyChanges = async () => {
    if (!diffData) return;

    setIsApplying(true);
    setError(null);

    try {
      // Build sync request based on direction and conflict resolutions
      const syncRequest = {
        project_path: direction === 'upstream' ? projectPath : undefined,
        force: false,
        strategy: determineStrategy(),
      };

      const response = await apiRequest<ArtifactSyncResponse>(
        `/artifacts/${encodeURIComponent(entityId)}/sync`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(syncRequest),
        }
      );

      setSyncResult(response);

      if (response.success) {
        // Success - show result briefly then complete
        setTimeout(() => {
          onComplete();
        }, 2000);
      } else {
        setError(response.message || 'Sync failed');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply changes');
    } finally {
      setIsApplying(false);
    }
  };

  const determineStrategy = (): string => {
    // Analyze conflict resolutions to determine overall strategy
    const resolutions = Object.values(conflictResolutions);
    const allCollection = resolutions.every((r) => r === 'collection');
    const allProject = resolutions.every((r) => r === 'project');

    if (allCollection) return 'theirs'; // Take upstream/collection
    if (allProject) return 'ours'; // Keep local/project
    return 'manual'; // Mixed resolutions require manual handling
  };

  const setConflictResolution = (filePath: string, resolution: ConflictResolution) => {
    setConflictResolutions((prev) => ({
      ...prev,
      [filePath]: resolution,
    }));
  };

  const allConflictsResolved = () => {
    if (!diffData) return false;
    const modifiedFiles = diffData.files.filter((file) => file.status === 'modified');
    return modifiedFiles.every((file) => conflictResolutions[file.file_path] !== undefined);
  };

  if (isLoading) {
    return (
      <Card className="w-full">
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (error && !diffData) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle>Error</CardTitle>
        </CardHeader>
        <CardContent>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Failed to load diff</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </CardContent>
        <CardFooter>
          <Button variant="outline" onClick={onCancel}>
            Close
          </Button>
        </CardFooter>
      </Card>
    );
  }

  return (
    <div className="w-full space-y-6">
      {/* Progress Stepper */}
      <div className="flex items-center justify-center gap-2">
        <StepIndicator
          step={1}
          label="Preview"
          isActive={currentStep === 'preview'}
          isComplete={currentStep === 'resolve' || currentStep === 'apply'}
        />
        <ChevronRight className="h-4 w-4 text-muted-foreground" />
        <StepIndicator
          step={2}
          label="Resolve"
          isActive={currentStep === 'resolve'}
          isComplete={currentStep === 'apply'}
        />
        <ChevronRight className="h-4 w-4 text-muted-foreground" />
        <StepIndicator
          step={3}
          label="Apply"
          isActive={currentStep === 'apply'}
          isComplete={syncResult?.success === true}
        />
      </div>

      {/* Step Content */}
      {currentStep === 'preview' && (
        <PreviewStep
          diffData={diffData!}
          direction={direction}
          onContinue={handleContinueFromPreview}
          onCancel={onCancel}
        />
      )}

      {currentStep === 'resolve' && (
        <ResolveStep
          diffData={diffData!}
          conflictResolutions={conflictResolutions}
          onSetResolution={setConflictResolution}
          onContinue={handleContinueFromResolve}
          onBack={handleBackToPreview}
          canContinue={allConflictsResolved()}
        />
      )}

      {currentStep === 'apply' && (
        <ApplyStep
          diffData={diffData!}
          conflictResolutions={conflictResolutions}
          direction={direction}
          onApply={handleApplyChanges}
          onBack={() => setCurrentStep('resolve')}
          isApplying={isApplying}
          syncResult={syncResult}
          error={error}
          onDone={onComplete}
        />
      )}
    </div>
  );
}

interface StepIndicatorProps {
  step: number;
  label: string;
  isActive: boolean;
  isComplete: boolean;
}

function StepIndicator({ step, label, isActive, isComplete }: StepIndicatorProps) {
  return (
    <div className="flex items-center gap-2">
      <div
        className={cn(
          'flex h-8 w-8 items-center justify-center rounded-full border-2 text-sm font-semibold',
          isComplete && 'border-green-600 bg-green-600 text-white',
          isActive && !isComplete && 'border-primary bg-primary text-primary-foreground',
          !isActive && !isComplete && 'border-muted-foreground text-muted-foreground'
        )}
      >
        {isComplete ? <Check className="h-4 w-4" /> : step}
      </div>
      <span
        className={cn(
          'text-sm font-medium',
          isActive && 'text-foreground',
          !isActive && 'text-muted-foreground'
        )}
      >
        {label}
      </span>
    </div>
  );
}

interface PreviewStepProps {
  diffData: ArtifactDiffResponse;
  direction: 'upstream' | 'downstream';
  onContinue: () => void;
  onCancel: () => void;
}

function PreviewStep({ diffData, direction, onContinue, onCancel }: PreviewStepProps) {
  const summary = diffData.summary || { added: 0, modified: 0, deleted: 0, unchanged: 0 };
  const hasChanges = diffData.has_changes;

  // Memoize expensive conflict analysis
  const conflictAnalysis = useMemo(() => analyzeAllConflicts(diffData.files), [diffData.files]);
  const hasConflicts = useMemo(
    () => conflictAnalysis.some((c) => c.conflictCount > 0),
    [conflictAnalysis]
  );
  const conflictCount = useMemo(
    () => conflictAnalysis.reduce((sum, c) => sum + c.conflictCount, 0),
    [conflictAnalysis]
  );

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Preview Changes</CardTitle>
        <CardDescription>
          {direction === 'upstream'
            ? 'Review changes to sync from project to collection'
            : 'Review changes to sync from collection to project'}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Conflict Warning */}
        {hasConflicts && (
          <Alert
            variant="destructive"
            className="border-orange-300 bg-orange-50 dark:border-orange-800 dark:bg-orange-950/20"
          >
            <AlertTriangle className="h-4 w-4 text-orange-600 dark:text-orange-500" />
            <AlertTitle className="text-orange-900 dark:text-orange-300">
              Conflicts Detected
            </AlertTitle>
            <AlertDescription className="text-orange-800 dark:text-orange-400">
              {conflictCount} {conflictCount === 1 ? 'conflict' : 'conflicts'} detected in{' '}
              {summary.modified} modified {summary.modified === 1 ? 'file' : 'files'}. You will need
              to resolve these in the next step.
            </AlertDescription>
          </Alert>
        )}

        {/* Summary */}
        <div className="flex items-center gap-4 rounded-lg border p-4">
          <div className="flex-1">
            <h4 className="mb-2 text-sm font-semibold">Summary of Changes</h4>
            <div className="flex items-center gap-4 text-sm">
              {(summary.added ?? 0) > 0 && (
                <span className="text-green-600 dark:text-green-400">+{summary.added} added</span>
              )}
              {(summary.modified ?? 0) > 0 && (
                <span className="text-blue-600 dark:text-blue-400">
                  ~{summary.modified} modified
                </span>
              )}
              {(summary.deleted ?? 0) > 0 && (
                <span className="text-red-600 dark:text-red-400">-{summary.deleted} deleted</span>
              )}
              {!hasChanges && <span className="text-muted-foreground">No changes detected</span>}
            </div>
          </div>
        </div>

        {/* Diff Viewer */}
        {hasChanges && (
          <div className="overflow-hidden rounded-lg border" style={{ height: '500px' }}>
            <DiffViewer
              files={diffData.files}
              leftLabel={direction === 'upstream' ? 'Collection' : 'Project'}
              rightLabel={direction === 'upstream' ? 'Project' : 'Collection'}
            />
          </div>
        )}

        {!hasChanges && (
          <div className="flex items-center justify-center py-12 text-muted-foreground">
            <p>No changes to preview</p>
          </div>
        )}
      </CardContent>
      <CardFooter className="flex justify-between">
        <Button variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button onClick={onContinue} disabled={!hasChanges}>
          Continue
        </Button>
      </CardFooter>
    </Card>
  );
}

interface ConflictSummaryPanelProps {
  conflicts: FileConflictInfo[];
}

function ConflictSummaryPanel({ conflicts }: ConflictSummaryPanelProps) {
  const totalConflicts = conflicts.reduce((sum, c) => sum + c.conflictCount, 0);
  const hardConflicts = conflicts.filter((c) => c.severity === 'hard');
  const softConflicts = conflicts.filter((c) => c.severity === 'soft');
  const filesWithConflicts = conflicts.filter((c) => c.conflictCount > 0).length;

  if (totalConflicts === 0) {
    return null;
  }

  return (
    <Alert
      variant="destructive"
      className="border-orange-300 bg-orange-50 dark:border-orange-800 dark:bg-orange-950/20"
    >
      <AlertTriangle className="h-4 w-4 text-orange-600 dark:text-orange-500" />
      <AlertTitle className="text-orange-900 dark:text-orange-300">Conflicts Detected</AlertTitle>
      <AlertDescription className="text-orange-800 dark:text-orange-400">
        <div className="mt-2 space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span>Total conflicts:</span>
            <span className="font-semibold">{totalConflicts}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span>Files affected:</span>
            <span className="font-semibold">{filesWithConflicts}</span>
          </div>
          <div className="grid grid-cols-2 gap-2 border-t border-orange-300 pt-2 dark:border-orange-800">
            <div className="space-y-1">
              <div className="text-xs font-medium">Hard Conflicts</div>
              <div className="text-lg font-bold text-red-700 dark:text-red-400">
                {hardConflicts.length}
              </div>
              <div className="text-xs text-orange-700 dark:text-orange-500">
                Overlapping changes
              </div>
            </div>
            <div className="space-y-1">
              <div className="text-xs font-medium">Soft Conflicts</div>
              <div className="text-lg font-bold text-yellow-700 dark:text-yellow-400">
                {softConflicts.length}
              </div>
              <div className="text-xs text-orange-700 dark:text-orange-500">Adjacent changes</div>
            </div>
          </div>
          <div className="border-t border-orange-300 pt-2 text-xs dark:border-orange-800">
            Review each file carefully and select the appropriate resolution strategy.
          </div>
        </div>
      </AlertDescription>
    </Alert>
  );
}

interface ResolveStepProps {
  diffData: ArtifactDiffResponse;
  conflictResolutions: ConflictState;
  onSetResolution: (filePath: string, resolution: ConflictResolution) => void;
  onContinue: () => void;
  onBack: () => void;
  canContinue: boolean;
}

function ResolveStep({
  diffData,
  conflictResolutions,
  onSetResolution,
  onContinue,
  onBack,
  canContinue,
}: ResolveStepProps) {
  // Memoize modified files list
  const modifiedFiles = useMemo(
    () => diffData.files.filter((file) => file.status === 'modified'),
    [diffData.files]
  );

  // Memoize expensive conflict analysis
  const conflictAnalysis = useMemo(() => analyzeAllConflicts(diffData.files), [diffData.files]);

  // Map resolution strategies: 'collection'/'project'/'merge' -> 'theirs'/'ours'/'manual'
  const mapResolutionToStrategy = (
    resolution: ConflictResolution | undefined
  ): 'theirs' | 'ours' | 'manual' | null => {
    if (!resolution) return null;
    if (resolution === 'collection') return 'theirs';
    if (resolution === 'project') return 'ours';
    if (resolution === 'merge') return 'manual';
    return null;
  };

  const mapStrategyToResolution = (strategy: 'theirs' | 'ours' | 'manual'): ConflictResolution => {
    if (strategy === 'theirs') return 'collection';
    if (strategy === 'ours') return 'project';
    if (strategy === 'manual') return 'merge';
    return 'collection';
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Resolve Conflicts</CardTitle>
        <CardDescription>
          Choose how to handle modified files. Select the version to keep for each file.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Conflict Summary Panel */}
        <ConflictSummaryPanel conflicts={conflictAnalysis} />

        {modifiedFiles.length === 0 ? (
          <div className="flex items-center justify-center py-12 text-muted-foreground">
            <p>No conflicts to resolve</p>
          </div>
        ) : (
          <div className="space-y-3">
            {modifiedFiles.map((file) => {
              const fileConflictInfo = conflictAnalysis.find((c) => c.filePath === file.file_path);
              return (
                <ConflictResolver
                  key={file.file_path}
                  file={file}
                  resolution={mapResolutionToStrategy(conflictResolutions[file.file_path])}
                  onResolve={(strategy) =>
                    onSetResolution(file.file_path, mapStrategyToResolution(strategy))
                  }
                  conflictInfo={
                    fileConflictInfo
                      ? {
                          severity: fileConflictInfo.severity,
                          conflictCount: fileConflictInfo.conflictCount,
                          additions: fileConflictInfo.additionCount,
                          deletions: fileConflictInfo.deletionCount,
                        }
                      : undefined
                  }
                  collectionLabel="Collection"
                  projectLabel="Project"
                />
              );
            })}
          </div>
        )}
      </CardContent>
      <CardFooter className="flex justify-between">
        <Button variant="outline" onClick={onBack}>
          Back
        </Button>
        <Button onClick={onContinue} disabled={!canContinue}>
          Continue
        </Button>
      </CardFooter>
    </Card>
  );
}

interface ApplyStepProps {
  diffData: ArtifactDiffResponse;
  conflictResolutions: ConflictState;
  direction: 'upstream' | 'downstream';
  onApply: () => void;
  onBack: () => void;
  isApplying: boolean;
  syncResult: ArtifactSyncResponse | null;
  error: string | null;
  onDone: () => void;
}

function ApplyStep({
  diffData,
  conflictResolutions,
  direction,
  onApply,
  onBack,
  isApplying,
  syncResult,
  error,
  onDone,
}: ApplyStepProps) {
  const summary = diffData.summary || { added: 0, modified: 0, deleted: 0, unchanged: 0 };
  const modifiedFiles = diffData.files.filter((file) => file.status === 'modified');
  const [progress, setProgress] = useState<ProgressState>({
    percent: 0,
    stage: 'preparing',
    message: 'Preparing merge...',
  });

  // Simulate progress when applying changes
  useEffect(() => {
    if (!isApplying) {
      // Reset progress when not applying
      setProgress({
        percent: 0,
        stage: 'preparing',
        message: 'Preparing merge...',
      });
      return;
    }

    // Calculate total files to process
    const totalFiles = (summary.added ?? 0) + (summary.modified ?? 0) + (summary.deleted ?? 0);

    // Define progressive stages with timing
    const stages: Array<{
      stage: ProgressStage;
      startPercent: number;
      endPercent: number;
      message: string;
      duration: number;
    }> = [
      {
        stage: 'preparing',
        startPercent: 0,
        endPercent: 20,
        message: 'Preparing merge...',
        duration: 300,
      },
      {
        stage: 'resolving',
        startPercent: 20,
        endPercent: 50,
        message: 'Resolving conflicts...',
        duration: 600,
      },
      {
        stage: 'applying',
        startPercent: 50,
        endPercent: 80,
        message: 'Applying changes...',
        duration: 800,
      },
      {
        stage: 'finalizing',
        startPercent: 80,
        endPercent: 100,
        message: 'Finalizing...',
        duration: 400,
      },
    ];

    let currentStageIndex = 0;

    const advanceProgress = () => {
      if (currentStageIndex >= stages.length) {
        return;
      }

      const stage = stages[currentStageIndex];
      if (!stage) return;

      const range = stage.endPercent - stage.startPercent;
      const steps = 10; // Number of incremental updates per stage
      const stepSize = range / steps;
      const stepDuration = stage.duration / steps;

      let currentStep = 0;

      const stepInterval = setInterval(() => {
        currentStep++;
        const newPercent = Math.min(stage.startPercent + stepSize * currentStep, stage.endPercent);

        // Optionally show file-level progress during 'applying' stage
        let currentFile: string | undefined;
        let currentFileIndex: number | undefined;
        if (stage.stage === 'applying' && totalFiles > 0) {
          const fileProgress = ((newPercent - 50) / 30) * totalFiles; // Map 50-80% to file count
          currentFileIndex = Math.floor(fileProgress);
          if (currentFileIndex < diffData.files.length) {
            currentFile = diffData.files[currentFileIndex]?.file_path;
          }
        }

        setProgress({
          percent: newPercent,
          stage: stage.stage,
          message: stage.message,
          currentFile,
          currentFileIndex: currentFileIndex !== undefined ? currentFileIndex + 1 : undefined,
          totalFiles: totalFiles > 0 ? totalFiles : undefined,
        });

        if (currentStep >= steps) {
          clearInterval(stepInterval);
          currentStageIndex++;
          if (currentStageIndex < stages.length) {
            advanceProgress();
          }
        }
      }, stepDuration);
    };

    advanceProgress();
  }, [isApplying, diffData.files, summary.added, summary.modified, summary.deleted]);

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Apply Changes</CardTitle>
        <CardDescription>Review the final summary and apply the merge operation.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary */}
        <div className="space-y-3 rounded-lg border p-4">
          <h4 className="text-sm font-semibold">Summary</h4>
          <div className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Direction:</span>
              <span className="font-medium">
                {direction === 'upstream' ? 'Project → Collection' : 'Collection → Project'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Files to add:</span>
              <span className="font-medium text-green-600 dark:text-green-400">
                {summary.added}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Files to modify:</span>
              <span className="font-medium text-blue-600 dark:text-blue-400">
                {summary.modified}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Files to delete:</span>
              <span className="font-medium text-red-600 dark:text-red-400">{summary.deleted}</span>
            </div>
          </div>
        </div>

        {/* Conflict Resolutions */}
        {modifiedFiles.length > 0 && (
          <div className="space-y-3 rounded-lg border p-4">
            <h4 className="text-sm font-semibold">Conflict Resolutions</h4>
            <div className="space-y-2">
              {modifiedFiles.map((file) => (
                <div key={file.file_path} className="flex items-center justify-between text-sm">
                  <span className="font-mono text-muted-foreground">{file.file_path}</span>
                  <Badge variant="outline">
                    {conflictResolutions[file.file_path] === 'collection'
                      ? 'Keep Collection'
                      : conflictResolutions[file.file_path] === 'project'
                        ? 'Keep Project'
                        : 'Merge Both'}
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Progress Indicator - shown when applying */}
        {isApplying && (
          <div className="space-y-4 rounded-lg border bg-muted/30 p-6">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">{progress.message}</span>
                <span className="tabular-nums text-muted-foreground">
                  {Math.round(progress.percent)}%
                </span>
              </div>
              <Progress value={progress.percent} className="h-3" />
            </div>

            {/* Step-by-step progress */}
            <div className="space-y-2.5">
              <ProgressStepItem
                label="Preparing merge"
                isComplete={progress.percent > 20}
                isActive={progress.stage === 'preparing'}
              />
              <ProgressStepItem
                label="Resolving conflicts"
                isComplete={progress.percent > 50}
                isActive={progress.stage === 'resolving'}
              />
              <ProgressStepItem
                label="Applying changes"
                isComplete={progress.percent > 80}
                isActive={progress.stage === 'applying'}
              />
              <ProgressStepItem
                label="Finalizing"
                isComplete={progress.percent >= 100}
                isActive={progress.stage === 'finalizing'}
              />
            </div>

            {/* File-level progress (optional) */}
            {progress.currentFile && progress.currentFileIndex && progress.totalFiles && (
              <div className="border-t pt-3">
                <p className="text-xs text-muted-foreground">
                  Processing file {progress.currentFileIndex} of {progress.totalFiles}:{' '}
                  <span className="font-mono font-medium">{progress.currentFile}</span>
                </p>
              </div>
            )}
          </div>
        )}

        {/* Result Messages */}
        {syncResult && syncResult.success && (
          <Alert>
            <Check className="h-4 w-4" />
            <AlertTitle>Success</AlertTitle>
            <AlertDescription>
              {syncResult.message}
              {syncResult.synced_files_count && (
                <span className="mt-1 block">Synced {syncResult.synced_files_count} file(s)</span>
              )}
            </AlertDescription>
          </Alert>
        )}

        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </CardContent>
      <CardFooter className="flex justify-between">
        {!syncResult && !isApplying && (
          <>
            <Button variant="outline" onClick={onBack}>
              Back
            </Button>
            <Button onClick={onApply} disabled={isApplying}>
              Apply Changes
            </Button>
          </>
        )}
        {isApplying && (
          <div className="flex w-full items-center justify-center gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>Applying changes...</span>
          </div>
        )}
        {syncResult && (
          <div className="flex w-full justify-end">
            <Button onClick={onDone}>Done</Button>
          </div>
        )}
      </CardFooter>
    </Card>
  );
}

interface ProgressStepItemProps {
  label: string;
  isComplete: boolean;
  isActive: boolean;
}

function ProgressStepItem({ label, isComplete, isActive }: ProgressStepItemProps) {
  return (
    <div className="flex items-center gap-3">
      <div
        className={cn(
          'flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full border-2 transition-colors',
          isComplete && 'border-green-600 bg-green-600',
          isActive && !isComplete && 'border-primary bg-background',
          !isActive && !isComplete && 'border-muted bg-background'
        )}
      >
        {isComplete ? (
          <Check className="h-3 w-3 text-white" />
        ) : isActive ? (
          <Loader2 className="h-3 w-3 animate-spin text-primary" />
        ) : (
          <div className="h-1.5 w-1.5 rounded-full bg-muted" />
        )}
      </div>
      <span
        className={cn(
          'text-sm transition-colors',
          isComplete && 'font-medium text-green-600 dark:text-green-400',
          isActive && !isComplete && 'font-medium text-foreground',
          !isActive && !isComplete && 'text-muted-foreground'
        )}
      >
        {label}
      </span>
    </div>
  );
}
