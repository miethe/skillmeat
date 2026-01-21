'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ChangeBadge } from './ChangeBadge';
import type { FileDiff } from '@/types/sync';

interface DiffViewerProps {
  file: FileDiff;
  defaultExpanded?: boolean;
  className?: string;
}

export function DiffViewer({ file, defaultExpanded = true, className }: DiffViewerProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <div className={cn('overflow-hidden rounded-lg border', className)}>
      {/* Header with file path and badge */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 bg-muted/50 px-3 py-2 text-left transition-colors hover:bg-muted"
      >
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        )}
        <FileText className="h-4 w-4 text-muted-foreground" />
        <span className="flex-1 font-mono text-sm">{file.path}</span>
        {file.change_origin && <ChangeBadge origin={file.change_origin} size="sm" />}
      </button>

      {/* Diff content */}
      {expanded && (
        <pre className="overflow-x-auto bg-background p-3 text-sm">
          <code>{formatDiff(file.diff)}</code>
        </pre>
      )}
    </div>
  );
}

// Format diff with line highlighting
function formatDiff(diff: string): React.ReactNode {
  return diff.split('\n').map((line, i) => {
    let className = '';
    if (line.startsWith('+') && !line.startsWith('+++')) {
      className = 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300';
    } else if (line.startsWith('-') && !line.startsWith('---')) {
      className = 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300';
    } else if (line.startsWith('@@')) {
      className = 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300';
    }

    return (
      <div key={i} className={cn('whitespace-pre', className)}>
        {line || ' '}
      </div>
    );
  });
}

// Multi-file diff viewer
interface DiffViewerListProps {
  files: FileDiff[];
  className?: string;
}

export function DiffViewerList({ files, className }: DiffViewerListProps) {
  return (
    <div className={cn('space-y-4', className)}>
      {files.map((file, index) => (
        <DiffViewer key={`${file.path}-${index}`} file={file} />
      ))}
    </div>
  );
}
