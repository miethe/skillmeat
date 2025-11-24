'use client';

import { useState, useRef, useEffect } from 'react';
import { ChevronDown, ChevronRight, X } from 'lucide-react';
import { FileDiff } from '../../sdk/models/FileDiff';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';

interface DiffViewerProps {
  files: FileDiff[];
  leftLabel?: string;
  rightLabel?: string;
  onClose?: () => void;
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

function DiffLine({ content, type, lineNumber, side }: DiffLineProps) {
  const lineClasses = cn(
    'flex font-mono text-sm border-b border-border/50',
    type === 'addition' && 'bg-green-500/10 text-green-700 dark:text-green-400',
    type === 'deletion' && 'bg-red-500/10 text-red-700 dark:text-red-400',
    type === 'context' && 'text-foreground',
    type === 'header' && 'bg-muted/50 text-muted-foreground font-semibold'
  );

  return (
    <div className={lineClasses}>
      <span className="text-gray-400 select-none w-12 text-right pr-2 flex-shrink-0 border-r border-border/50">
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
    // Skip file headers
    if (line.startsWith('---') || line.startsWith('+++')) {
      continue;
    }

    // Parse hunk header: @@ -1,5 +1,6 @@
    if (line.startsWith('@@')) {
      const match = line.match(/@@ -(\d+),?\d* \+(\d+),?\d* @@/);
      if (match) {
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
  const variants: Record<FileDiff['status'], { variant: 'default' | 'secondary' | 'destructive' | 'outline'; label: string }> = {
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

export function DiffViewer({
  files,
  leftLabel = 'Before',
  rightLabel = 'After',
  onClose
}: DiffViewerProps) {
  const [selectedFileIndex, setSelectedFileIndex] = useState(0);
  const [expandedFiles, setExpandedFiles] = useState<Set<number>>(new Set([0]));
  const leftScrollRef = useRef<HTMLDivElement>(null);
  const rightScrollRef = useRef<HTMLDivElement>(null);

  const selectedFile = files[selectedFileIndex];
  const parsedDiff = selectedFile?.unified_diff
    ? parseDiff(selectedFile.unified_diff)
    : [];

  // Calculate summary
  const summary = files.reduce(
    (acc, file) => {
      if (file.status === 'added') acc.added++;
      else if (file.status === 'modified') acc.modified++;
      else if (file.status === 'deleted') acc.deleted++;
      else acc.unchanged++;
      return acc;
    },
    { added: 0, modified: 0, deleted: 0, unchanged: 0 }
  );

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
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        <p>No changes to display</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header with summary */}
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-4">
          <h3 className="font-semibold text-lg">Diff Viewer</h3>
          <div className="flex items-center gap-2 text-sm">
            {summary.added > 0 && (
              <span className="text-green-600 dark:text-green-400">
                +{summary.added}
              </span>
            )}
            {summary.modified > 0 && (
              <span className="text-blue-600 dark:text-blue-400">
                ~{summary.modified}
              </span>
            )}
            {summary.deleted > 0 && (
              <span className="text-red-600 dark:text-red-400">
                -{summary.deleted}
              </span>
            )}
          </div>
        </div>
        {onClose && (
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* File list sidebar */}
        <div className="w-64 border-r overflow-y-auto bg-muted/20">
          <div className="p-2 space-y-1">
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
                      'w-full flex items-center gap-2 px-2 py-1.5 rounded text-sm hover:bg-accent transition-colors text-left',
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
                    <span className="flex-1 truncate font-mono text-xs">
                      {file.file_path}
                    </span>
                    <FileStatusBadge status={file.status} />
                  </button>

                  {isExpanded && (
                    <div className="ml-6 mt-1 text-xs text-muted-foreground space-y-0.5">
                      {file.status === 'modified' && file.unified_diff && (
                        <div className="font-mono">
                          {parseDiff(file.unified_diff).filter(l => l.type === 'addition').length} additions,{' '}
                          {parseDiff(file.unified_diff).filter(l => l.type === 'deletion').length} deletions
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Diff viewer */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* File header */}
          <div className="px-4 py-2 border-b bg-muted/30">
            <div className="flex items-center justify-between">
              <span className="font-mono text-sm font-semibold">
                {selectedFile?.file_path}
              </span>
              <FileStatusBadge status={selectedFile?.status || 'unchanged'} />
            </div>
          </div>

          {/* Side-by-side diff */}
          {selectedFile?.status === 'modified' && selectedFile.unified_diff ? (
            <div className="flex flex-1 overflow-hidden">
              {/* Left panel */}
              <div className="flex-1 flex flex-col border-r">
                <div className="px-4 py-2 bg-muted/50 border-b text-sm font-medium">
                  {leftLabel}
                </div>
                <div
                  ref={leftScrollRef}
                  className="flex-1 overflow-y-auto"
                >
                  {parsedDiff.map((line, idx) => {
                    if (line.type === 'addition') return null;
                    if (line.type === 'header') {
                      return (
                        <DiffLine
                          key={idx}
                          content={line.content}
                          type="header"
                          side="left"
                        />
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
              <div className="flex-1 flex flex-col">
                <div className="px-4 py-2 bg-muted/50 border-b text-sm font-medium">
                  {rightLabel}
                </div>
                <div
                  ref={rightScrollRef}
                  className="flex-1 overflow-y-auto"
                >
                  {parsedDiff.map((line, idx) => {
                    if (line.type === 'deletion') return null;
                    if (line.type === 'header') {
                      return (
                        <DiffLine
                          key={idx}
                          content={line.content}
                          type="header"
                          side="right"
                        />
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
            <div className="flex-1 flex flex-col overflow-hidden">
              <div className="px-4 py-2 bg-green-500/10 text-green-700 dark:text-green-400 text-sm">
                This file was added in {rightLabel}
              </div>
              <div className="flex-1 overflow-y-auto p-4 text-sm text-muted-foreground">
                Content preview not available for added files.
              </div>
            </div>
          ) : selectedFile?.status === 'deleted' ? (
            <div className="flex-1 flex flex-col overflow-hidden">
              <div className="px-4 py-2 bg-red-500/10 text-red-700 dark:text-red-400 text-sm">
                This file was deleted from {leftLabel}
              </div>
              <div className="flex-1 overflow-y-auto p-4 text-sm text-muted-foreground">
                Content preview not available for deleted files.
              </div>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-muted-foreground">
              <p>No changes in this file</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
