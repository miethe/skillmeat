'use client';

import { useState, useRef, useEffect } from 'react';
import { AlertTriangle, Check } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { FileDiff } from '@/sdk/models/FileDiff';

/**
 * Props for ConflictResolver component
 *
 * Controls file display, conflict information, and resolution callback.
 */
export interface ConflictResolverProps {
  /** The file diff containing the conflict */
  file: FileDiff;
  /** Currently selected resolution strategy */
  resolution: 'theirs' | 'ours' | 'manual' | null;
  /** Callback when user selects a resolution strategy */
  onResolve: (resolution: 'theirs' | 'ours' | 'manual') => void;
  /** Optional conflict analysis information for display */
  conflictInfo?: {
    /** Conflict severity: 'hard' (overlapping) or 'soft' (adjacent) */
    severity: 'hard' | 'soft' | 'none';
    /** Number of conflicts detected */
    conflictCount: number;
    /** Number of lines added */
    additions: number;
    /** Number of lines deleted */
    deletions: number;
  };
  /** Label for collection version (left panel) */
  collectionLabel?: string;
  /** Label for project version (right panel) */
  projectLabel?: string;
}

interface ParsedDiffLine {
  leftLineNumber?: number;
  rightLineNumber?: number;
  type: 'addition' | 'deletion' | 'context' | 'header';
  content: string;
}

interface DiffLineProps {
  content: string;
  type: 'addition' | 'deletion' | 'context' | 'header';
  lineNumber?: number;
}

function DiffLine({ content, type, lineNumber }: DiffLineProps) {
  const lineClasses = cn(
    'flex font-mono text-xs border-b border-border/50',
    type === 'addition' && 'bg-green-500/10 text-green-700 dark:text-green-400',
    type === 'deletion' && 'bg-red-500/10 text-red-700 dark:text-red-400',
    type === 'context' && 'text-foreground',
    type === 'header' && 'bg-muted/50 text-muted-foreground font-semibold'
  );

  return (
    <div className={lineClasses}>
      <span className="text-gray-400 select-none w-10 text-right pr-2 flex-shrink-0 border-r border-border/50 text-xs">
        {lineNumber !== undefined ? lineNumber : ''}
      </span>
      <span className="px-2 flex-1 whitespace-pre-wrap break-all">
        {content}
      </span>
    </div>
  );
}

function parseDiff(unifiedDiff: string): ParsedDiffLine[] {
  const lines = unifiedDiff.split('\n');
  const parsed: ParsedDiffLine[] = [];
  let leftLineNum = 0;
  let rightLineNum = 0;

  for (const line of lines) {
    if (line.startsWith('---') || line.startsWith('+++')) {
      continue;
    }

    if (line.startsWith('@@')) {
      const match = line.match(/@@ -(\d+),?\d* \+(\d+),?\d* @@/);
      if (match && match[1] && match[2]) {
        leftLineNum = parseInt(match[1], 10);
        rightLineNum = parseInt(match[2], 10);
      }
      parsed.push({
        type: 'header',
        content: line,
      });
      continue;
    }

    if (line.startsWith('+')) {
      parsed.push({
        rightLineNumber: rightLineNum++,
        type: 'addition',
        content: line.substring(1),
      });
    } else if (line.startsWith('-')) {
      parsed.push({
        leftLineNumber: leftLineNum++,
        type: 'deletion',
        content: line.substring(1),
      });
    } else {
      const content = line.startsWith(' ') ? line.substring(1) : line;
      parsed.push({
        leftLineNumber: leftLineNum++,
        rightLineNumber: rightLineNum++,
        type: 'context',
        content,
      });
    }
  }

  return parsed;
}

/**
 * ConflictResolver - Interactive conflict resolution card
 *
 * Displays a single file with conflicts and provides resolution options.
 * Features include:
 * - Visual conflict severity indicators (hard/soft) with color coding
 * - Side-by-side diff preview with synchronized scrolling
 * - Three resolution strategies: keep collection, keep project, manual merge
 * - Conflict statistics (additions/deletions, conflict count)
 * - Selected resolution confirmation summary
 *
 * @example
 * ```tsx
 * <ConflictResolver
 *   file={fileDiff}
 *   resolution="collection"
 *   onResolve={(strategy) => updateResolution(filePath, strategy)}
 *   conflictInfo={{
 *     severity: 'hard',
 *     conflictCount: 3,
 *     additions: 12,
 *     deletions: 8
 *   }}
 * />
 * ```
 *
 * @param props - ConflictResolverProps configuration
 * @returns Card component with conflict resolution options
 */
export function ConflictResolver({
  file,
  resolution,
  onResolve,
  conflictInfo,
  collectionLabel = 'Collection',
  projectLabel = 'Project',
}: ConflictResolverProps) {
  const leftScrollRef = useRef<HTMLDivElement>(null);
  const rightScrollRef = useRef<HTMLDivElement>(null);
  const [parsedDiff, setParsedDiff] = useState<ParsedDiffLine[]>([]);

  const hasConflicts = conflictInfo && conflictInfo.conflictCount > 0;
  const isHardConflict = conflictInfo?.severity === 'hard';
  const isSoftConflict = conflictInfo?.severity === 'soft';

  useEffect(() => {
    if (file.unified_diff) {
      setParsedDiff(parseDiff(file.unified_diff));
    }
  }, [file.unified_diff]);

  // Synchronized scrolling
  useEffect(() => {
    const leftScroll = leftScrollRef.current;
    const rightScroll = rightScrollRef.current;

    if (!leftScroll || !rightScroll) return;

    const syncScroll = (source: HTMLDivElement, target: HTMLDivElement) => {
      target.scrollTop = source.scrollTop;
    };

    const onLeftScroll = () => syncScroll(leftScroll, rightScroll);
    const onRightScroll = () => syncScroll(rightScroll, leftScroll);

    leftScroll.addEventListener('scroll', onLeftScroll);
    rightScroll.addEventListener('scroll', onRightScroll);

    return () => {
      leftScroll.removeEventListener('scroll', onLeftScroll);
      rightScroll.removeEventListener('scroll', onRightScroll);
    };
  }, []);

  const additions = conflictInfo?.additions ?? 0;
  const deletions = conflictInfo?.deletions ?? 0;

  return (
    <Card
      className={cn(
        'w-full transition-colors',
        isHardConflict && 'border-red-400 dark:border-red-800 bg-red-50/30 dark:bg-red-950/10',
        isSoftConflict && 'border-yellow-400 dark:border-yellow-800 bg-yellow-50/30 dark:bg-yellow-950/10',
        resolution && 'ring-2 ring-primary ring-offset-2'
      )}
    >
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 flex-wrap">
            <CardTitle className="text-base font-mono">{file.file_path}</CardTitle>
            <Badge variant="secondary" className="text-xs">
              Modified
            </Badge>
            {hasConflicts && (
              <Badge
                variant="destructive"
                className={cn(
                  'flex items-center gap-1 text-xs',
                  isHardConflict && 'bg-red-600 hover:bg-red-700 dark:bg-red-700 dark:hover:bg-red-800',
                  isSoftConflict && 'bg-yellow-600 hover:bg-yellow-700 dark:bg-yellow-700 dark:hover:bg-yellow-800'
                )}
              >
                <AlertTriangle className="h-3 w-3" />
                {conflictInfo.conflictCount} {conflictInfo.conflictCount === 1 ? 'conflict' : 'conflicts'}
              </Badge>
            )}
          </div>
        </div>

        {hasConflicts && conflictInfo && (
          <CardDescription className="pt-2">
            <div className="flex items-center gap-4 text-xs">
              <span
                className={cn(
                  'font-medium',
                  isHardConflict && 'text-red-700 dark:text-red-400',
                  isSoftConflict && 'text-yellow-700 dark:text-yellow-400'
                )}
              >
                {isHardConflict ? 'Hard Conflict (Overlapping)' : 'Soft Conflict (Adjacent)'}
              </span>
              <span className="text-muted-foreground">•</span>
              <span className="font-mono">
                <span className="text-green-600 dark:text-green-400">+{additions}</span>
                <span className="text-muted-foreground"> / </span>
                <span className="text-red-600 dark:text-red-400">-{deletions}</span>
              </span>
            </div>
          </CardDescription>
        )}
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Side-by-side diff preview */}
        {file.unified_diff && (
          <div className="border rounded-lg overflow-hidden" style={{ height: '300px' }}>
            <div className="flex h-full">
              {/* Left panel - Collection */}
              <div className="flex-1 flex flex-col border-r">
                <div className="px-3 py-1.5 bg-muted/50 border-b text-xs font-medium text-muted-foreground">
                  {collectionLabel}
                </div>
                <div ref={leftScrollRef} className="flex-1 overflow-y-auto">
                  {parsedDiff.map((line, idx) => {
                    if (line.type === 'addition') return null;
                    if (line.type === 'header') {
                      return <DiffLine key={idx} content={line.content} type="header" />;
                    }
                    return (
                      <DiffLine
                        key={idx}
                        content={line.content}
                        type={line.type}
                        lineNumber={line.leftLineNumber}
                      />
                    );
                  })}
                </div>
              </div>

              {/* Right panel - Project */}
              <div className="flex-1 flex flex-col">
                <div className="px-3 py-1.5 bg-muted/50 border-b text-xs font-medium text-muted-foreground">
                  {projectLabel}
                </div>
                <div ref={rightScrollRef} className="flex-1 overflow-y-auto">
                  {parsedDiff.map((line, idx) => {
                    if (line.type === 'deletion') return null;
                    if (line.type === 'header') {
                      return <DiffLine key={idx} content={line.content} type="header" />;
                    }
                    return (
                      <DiffLine
                        key={idx}
                        content={line.content}
                        type={line.type}
                        lineNumber={line.rightLineNumber}
                      />
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Resolution options - Radio button style */}
        <div className="space-y-2">
          <div className="text-sm font-medium">Choose Resolution:</div>
          <div className="grid grid-cols-3 gap-2">
            <ResolutionOption
              label={`Keep ${collectionLabel}`}
              description="Use upstream version"
              selected={resolution === 'theirs'}
              onClick={() => onResolve('theirs')}
              variant="primary"
            />
            <ResolutionOption
              label={`Keep ${projectLabel}`}
              description="Use local version"
              selected={resolution === 'ours'}
              onClick={() => onResolve('ours')}
              variant="secondary"
            />
            <ResolutionOption
              label="Manual Merge"
              description="Combine both"
              selected={resolution === 'manual'}
              onClick={() => onResolve('manual')}
              variant="neutral"
              disabled
            />
          </div>
        </div>

        {/* Resolution summary */}
        {resolution && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-primary/10 border border-primary/20">
            <Check className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
            <div className="text-sm">
              <div className="font-medium text-primary">Resolution Selected</div>
              <div className="text-muted-foreground text-xs mt-0.5">
                {resolution === 'theirs' && `Will use ${collectionLabel} version of this file`}
                {resolution === 'ours' && `Will keep ${projectLabel} version of this file`}
                {resolution === 'manual' && 'Will manually merge both versions (placeholder)'}
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface ResolutionOptionProps {
  label: string;
  description: string;
  selected: boolean;
  onClick: () => void;
  variant: 'primary' | 'secondary' | 'neutral';
  disabled?: boolean;
}

function ResolutionOption({
  label,
  description,
  selected,
  onClick,
  disabled = false,
}: ResolutionOptionProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'relative flex flex-col items-start gap-1 p-3 rounded-lg border-2 transition-all text-left',
        'hover:border-primary/50 hover:bg-accent/50',
        'focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2',
        selected && 'border-primary bg-primary/5 shadow-sm',
        !selected && 'border-border bg-background',
        disabled && 'opacity-50 cursor-not-allowed hover:border-border hover:bg-background'
      )}
    >
      {/* Radio indicator */}
      <div className="absolute top-3 right-3">
        <div
          className={cn(
            'h-4 w-4 rounded-full border-2 flex items-center justify-center transition-colors',
            selected && 'border-primary bg-primary',
            !selected && 'border-muted-foreground/30'
          )}
        >
          {selected && <div className="h-1.5 w-1.5 rounded-full bg-primary-foreground" />}
        </div>
      </div>

      <div className="pr-6">
        <div className="text-sm font-medium">{label}</div>
        <div className="text-xs text-muted-foreground">{description}</div>
        {disabled && <div className="text-xs text-orange-600 dark:text-orange-400 mt-1">Coming soon</div>}
      </div>
    </button>
  );
}
