'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown, ChevronRight, X, Loader2 } from 'lucide-react';
import { FileDiff } from '../../sdk/models/FileDiff';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

/**
 * Resolution type for sync conflict resolution
 */
export type ResolutionType = 'keep_local' | 'keep_remote' | 'merge';

/**
 * Props for DiffViewer component
 *
 * Configuration for displaying unified diffs with side-by-side view.
 */
interface DiffViewerProps {
  /** Array of file diffs to display */
  files: FileDiff[];
  /** Label for left (before) panel */
  leftLabel?: string;
  /** Label for right (after) panel */
  rightLabel?: string;
  /** Callback when user closes the diff viewer */
  onClose?: () => void;
  /** Show resolution action buttons (for sync conflict resolution) */
  showResolutionActions?: boolean;
  /** Callback when user selects a resolution */
  onResolve?: (resolution: ResolutionType) => void;
  /** Custom label for local version button (default: "Local (Project)") */
  localLabel?: string;
  /** Custom label for remote version button (default: "Remote (Collection)") */
  remoteLabel?: string;
  /** Show preview mode UI before applying resolution */
  previewMode?: boolean;
  /** Show loading state during resolution */
  isResolving?: boolean;
}

interface DiffLineProps {
  content: string;
  type: 'addition' | 'deletion' | 'context' | 'header';
  lineNumber?: number;
  side?: 'left' | 'right';
}

interface ParsedDiffLine {
  leftLineNumber?: number;
  rightLineNumber?: number;
  type: 'addition' | 'deletion' | 'context' | 'header';
  content: string;
}

function DiffLine({ content, type, lineNumber }: DiffLineProps) {
  const lineClasses = cn(
    'flex font-mono text-sm border-b border-border/50',
    type === 'addition' && 'bg-green-500/10 text-green-700 dark:text-green-400',
    type === 'deletion' && 'bg-red-500/10 text-red-700 dark:text-red-400',
    type === 'context' && 'text-foreground',
    type === 'header' && 'bg-muted/50 text-muted-foreground font-semibold'
  );

  return (
    <div className={lineClasses}>
      <span className="w-12 flex-shrink-0 select-none border-r border-border/50 pr-2 text-right text-gray-400">
        {lineNumber !== undefined ? lineNumber : ''}
      </span>
      <span className="flex-1 whitespace-pre px-2">{content}</span>
    </div>
  );
}

function SpacerLine() {
  return (
    <div className="flex border-b border-border/50 bg-muted/20 font-mono text-sm">
      <span className="w-12 flex-shrink-0 select-none border-r border-border/50 pr-2 text-right text-gray-400">
        &nbsp;
      </span>
      <span className="flex-1 whitespace-pre px-2">&nbsp;</span>
    </div>
  );
}

function parseDiff(unifiedDiff: string): ParsedDiffLine[] {
  const lines = unifiedDiff.split('\n');
  const parsed: ParsedDiffLine[] = [];
  let leftLineNum = 0;
  let rightLineNum = 0;

  for (const line of lines) {
    // Skip file headers
    if (line.startsWith('---') || line.startsWith('+++')) {
      continue;
    }

    // Parse hunk header: @@ -1,5 +1,6 @@
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

    // Parse diff lines
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
      // Context line (no prefix or space prefix)
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

function FileStatusBadge({ status }: { status: FileDiff['status'] }) {
  const variants: Record<
    FileDiff['status'],
    { variant: 'default' | 'secondary' | 'destructive' | 'outline'; label: string }
  > = {
    added: { variant: 'default', label: 'Added' },
    modified: { variant: 'secondary', label: 'Modified' },
    deleted: { variant: 'destructive', label: 'Deleted' },
    unchanged: { variant: 'outline', label: 'Unchanged' },
  };

  const { variant, label } = variants[status];

  return (
    <Badge variant={variant} className="text-xs">
      {label}
    </Badge>
  );
}

/**
 * DiffViewer - Side-by-side diff viewer with file browser
 *
 * Displays unified diffs in a professional side-by-side format. Features include:
 * - File list sidebar with expandable items showing change statistics
 * - Side-by-side diff panels with independent scrollbars
 * - Color-coded additions (green), deletions (red), and context lines
 * - File status badges (added, modified, deleted, unchanged)
 * - Change summary (total files added, modified, deleted)
 * - Optional sync conflict resolution actions (keep local/remote/merge)
 *
 * @example
 * Basic diff viewer:
 * ```tsx
 * <DiffViewer
 *   files={diffData.files}
 *   leftLabel="Collection"
 *   rightLabel="Project"
 *   onClose={() => closeDiff()}
 * />
 * ```
 *
 * @example
 * With sync resolution actions:
 * ```tsx
 * <DiffViewer
 *   files={diffData.files}
 *   leftLabel="Collection"
 *   rightLabel="Project"
 *   showResolutionActions={true}
 *   onResolve={(resolution) => handleResolve(resolution)}
 *   localLabel="Project"
 *   remoteLabel="Collection"
 *   isResolving={isResolving}
 *   previewMode={true}
 * />
 * ```
 *
 * @param props - DiffViewerProps configuration
 * @returns Full-height diff viewer component
 */
export function DiffViewer({
  files,
  leftLabel = 'Before',
  rightLabel = 'After',
  onClose,
  showResolutionActions = false,
  onResolve,
  localLabel,
  remoteLabel,
  previewMode = false,
  isResolving = false,
}: DiffViewerProps) {
  const [selectedFileIndex, setSelectedFileIndex] = useState(0);
  const [expandedFiles, setExpandedFiles] = useState<Set<number>>(new Set([0]));

  const selectedFile = files[selectedFileIndex];

  // Memoize parsed diff to avoid re-parsing on every render
  const parsedDiff = useMemo(() => {
    return selectedFile?.unified_diff ? parseDiff(selectedFile.unified_diff) : [];
  }, [selectedFile?.unified_diff]);

  // Refs for synchronized scrolling between left and right panels
  const leftScrollRef = useRef<HTMLDivElement>(null);
  const rightScrollRef = useRef<HTMLDivElement>(null);

  // Synchronized scrolling between left and right diff panels
  useEffect(() => {
    const leftScroll = leftScrollRef.current;
    const rightScroll = rightScrollRef.current;
    if (!leftScroll || !rightScroll) return;

    let isSyncing = false;

    const syncScroll = (source: HTMLDivElement, target: HTMLDivElement) => {
      if (isSyncing) return;
      isSyncing = true;
      target.scrollTop = source.scrollTop;
      requestAnimationFrame(() => {
        isSyncing = false;
      });
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

  // Memoize summary calculation
  const summary = useMemo(() => {
    return files.reduce(
      (acc, file) => {
        if (file.status === 'added') acc.added++;
        else if (file.status === 'modified') acc.modified++;
        else if (file.status === 'deleted') acc.deleted++;
        else acc.unchanged++;
        return acc;
      },
      { added: 0, modified: 0, deleted: 0, unchanged: 0 }
    );
  }, [files]);

  // Memoize parsed diffs for all files (for stats in sidebar)
  const parsedDiffs = useMemo(() => {
    const cache = new Map<string, ParsedDiffLine[]>();
    files.forEach((file) => {
      if (file.unified_diff) {
        cache.set(file.file_path, parseDiff(file.unified_diff));
      }
    });
    return cache;
  }, [files]);

  const toggleFileExpansion = (index: number) => {
    const newExpanded = new Set(expandedFiles);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedFiles(newExpanded);
  };

  if (files.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-muted-foreground">
        <p>No changes to display</p>
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden">
      {/* Header with summary */}
      <div className="flex flex-shrink-0 items-center justify-between border-b p-4">
        <div className="flex items-center gap-4">
          <h3 className="text-lg font-semibold">Diff Viewer</h3>
          <div className="flex items-center gap-2 text-sm">
            {summary.added > 0 && (
              <span className="text-green-600 dark:text-green-400">+{summary.added}</span>
            )}
            {summary.modified > 0 && (
              <span className="text-blue-600 dark:text-blue-400">~{summary.modified}</span>
            )}
            {summary.deleted > 0 && (
              <span className="text-red-600 dark:text-red-400">-{summary.deleted}</span>
            )}
          </div>
        </div>
        {onClose && (
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>

      <div className="flex min-h-0 min-w-0 flex-1 overflow-hidden">
        {/* File list sidebar */}
        <div className="min-h-0 w-64 flex-shrink-0 overflow-y-auto border-r bg-muted/20">
          <div className="space-y-1 p-2">
            {files.map((file, index) => {
              const isExpanded = expandedFiles.has(index);
              const isSelected = index === selectedFileIndex;

              return (
                <div key={index}>
                  <button
                    onClick={() => {
                      setSelectedFileIndex(index);
                      if (!isExpanded) {
                        toggleFileExpansion(index);
                      }
                    }}
                    className={cn(
                      'flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent',
                      isSelected && 'bg-accent'
                    )}
                  >
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleFileExpansion(index);
                      }}
                      className="flex-shrink-0"
                    >
                      {isExpanded ? (
                        <ChevronDown className="h-3 w-3" />
                      ) : (
                        <ChevronRight className="h-3 w-3" />
                      )}
                    </button>
                    <span className="flex-1 truncate font-mono text-xs">{file.file_path}</span>
                    <FileStatusBadge status={file.status} />
                  </button>

                  {isExpanded && (
                    <div className="ml-6 mt-1 space-y-0.5 text-xs text-muted-foreground">
                      {file.status === 'modified' &&
                        file.unified_diff &&
                        (() => {
                          const cached = parsedDiffs.get(file.file_path);
                          if (cached) {
                            const additions = cached.filter((l) => l.type === 'addition').length;
                            const deletions = cached.filter((l) => l.type === 'deletion').length;
                            return (
                              <div className="font-mono">
                                {additions} additions, {deletions} deletions
                              </div>
                            );
                          }
                          return null;
                        })()}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Diff viewer */}
        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          {/* File header */}
          <div className="flex-shrink-0 border-b bg-muted/30 px-4 py-2">
            <div className="flex items-center justify-between">
              <span className="font-mono text-sm font-semibold">{selectedFile?.file_path}</span>
              <FileStatusBadge status={selectedFile?.status || 'unchanged'} />
            </div>
          </div>

          {/* Side-by-side diff with synchronized scrolling and line alignment */}
          {selectedFile?.status === 'modified' && selectedFile.unified_diff ? (
            <div className="flex min-h-0 min-w-0 flex-1 overflow-hidden">
              {/* Left panel */}
              <div className="flex min-h-0 min-w-0 flex-1 flex-col border-r">
                <div className="flex-shrink-0 border-b bg-muted/50 px-4 py-2 text-sm font-medium">
                  {leftLabel}
                </div>
                <div ref={leftScrollRef} className="min-h-0 min-w-0 flex-1 overflow-auto">
                  {parsedDiff.map((line, idx) => {
                    if (line.type === 'addition') {
                      return <SpacerLine key={idx} />;
                    }
                    if (line.type === 'header') {
                      return (
                        <DiffLine key={idx} content={line.content} type="header" side="left" />
                      );
                    }
                    return (
                      <DiffLine
                        key={idx}
                        content={line.content}
                        type={line.type}
                        lineNumber={line.leftLineNumber}
                        side="left"
                      />
                    );
                  })}
                </div>
              </div>

              {/* Right panel */}
              <div className="flex min-h-0 min-w-0 flex-1 flex-col">
                <div className="flex-shrink-0 border-b bg-muted/50 px-4 py-2 text-sm font-medium">
                  {rightLabel}
                </div>
                <div ref={rightScrollRef} className="min-h-0 min-w-0 flex-1 overflow-auto">
                  {parsedDiff.map((line, idx) => {
                    if (line.type === 'deletion') {
                      return <SpacerLine key={idx} />;
                    }
                    if (line.type === 'header') {
                      return (
                        <DiffLine key={idx} content={line.content} type="header" side="right" />
                      );
                    }
                    return (
                      <DiffLine
                        key={idx}
                        content={line.content}
                        type={line.type}
                        lineNumber={line.rightLineNumber}
                        side="right"
                      />
                    );
                  })}
                </div>
              </div>
            </div>
          ) : selectedFile?.status === 'added' ? (
            <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
              <div className="flex-shrink-0 bg-green-500/10 px-4 py-2 text-sm text-green-700 dark:text-green-400">
                This file was added in {rightLabel}
              </div>
              <div className="min-h-0 min-w-0 flex-1 overflow-y-auto p-4 text-sm text-muted-foreground">
                Content preview not available for added files.
              </div>
            </div>
          ) : selectedFile?.status === 'deleted' ? (
            <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
              <div className="flex-shrink-0 bg-red-500/10 px-4 py-2 text-sm text-red-700 dark:text-red-400">
                This file was deleted from {leftLabel}
              </div>
              <div className="min-h-0 min-w-0 flex-1 overflow-y-auto p-4 text-sm text-muted-foreground">
                Content preview not available for deleted files.
              </div>
            </div>
          ) : (
            <div className="flex flex-1 items-center justify-center text-muted-foreground">
              <p>No changes in this file</p>
            </div>
          )}
        </div>
      </div>

      {/* Resolution Action Bar (for sync conflict resolution) */}
      {showResolutionActions && (
        <div className="flex flex-shrink-0 items-center justify-end gap-2 border-t bg-muted/20 p-4">
          {previewMode && (
            <span className="mr-auto text-sm text-muted-foreground">
              Preview mode - select which version to keep
            </span>
          )}
          <Button
            variant="outline"
            onClick={() => onResolve?.('keep_local')}
            disabled={isResolving}
            className="hover:bg-accent"
            title={`Keep the ${localLabel || 'local (project)'} version`}
          >
            Keep {localLabel || 'Local (Project)'}
          </Button>
          <Button
            variant="outline"
            onClick={() => onResolve?.('keep_remote')}
            disabled={isResolving}
            className="hover:bg-accent"
            title={`Keep the ${remoteLabel || 'remote (collection)'} version`}
          >
            Keep {remoteLabel || 'Remote (Collection)'}
          </Button>
          <Button
            variant="secondary"
            onClick={() => onResolve?.('merge')}
            disabled={isResolving}
            className="hover:bg-secondary/80"
            title="Manually merge changes (coming soon)"
          >
            Merge
          </Button>
          {isResolving && <Loader2 className="ml-2 h-4 w-4 animate-spin text-muted-foreground" />}
        </div>
      )}
    </div>
  );
}
