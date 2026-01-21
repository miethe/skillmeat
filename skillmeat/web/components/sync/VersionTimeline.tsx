'use client';

import { cn } from '@/lib/utils';
import type { ChangeOrigin } from '@/types/drift';

interface TimelineEntry {
  id: string;
  label: string;
  version?: string;
  type: 'collection' | 'deployment' | 'sync' | 'local';
  timestamp?: string;
  change_origin?: ChangeOrigin;
  isCurrent?: boolean;
}

interface VersionTimelineProps {
  entries: TimelineEntry[];
  className?: string;
}

const TYPE_COLORS = {
  collection: {
    dot: 'bg-blue-500',
    line: 'bg-blue-200 dark:bg-blue-800',
    text: 'text-blue-700 dark:text-blue-300',
  },
  deployment: {
    dot: 'bg-blue-500',
    line: 'bg-blue-200 dark:bg-blue-800',
    text: 'text-blue-700 dark:text-blue-300',
  },
  sync: {
    dot: 'bg-green-500',
    line: 'bg-green-200 dark:bg-green-800',
    text: 'text-green-700 dark:text-green-300',
  },
  local: {
    dot: 'bg-amber-500',
    line: 'bg-amber-200 dark:bg-amber-800',
    text: 'text-amber-700 dark:text-amber-300',
  },
};

export function VersionTimeline({ entries, className }: VersionTimelineProps) {
  return (
    <div className={cn('relative', className)}>
      {entries.map((entry, index) => {
        const colors = TYPE_COLORS[entry.type];
        const isLast = index === entries.length - 1;

        return (
          <div key={entry.id} className="flex items-start gap-3">
            {/* Timeline dot and line */}
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  'h-3 w-3 rounded-full ring-2 ring-background',
                  colors.dot,
                  entry.isCurrent && 'ring-4 ring-primary/20'
                )}
              />
              {!isLast && <div className={cn('h-8 w-0.5', colors.line)} />}
            </div>

            {/* Entry content */}
            <div className="-mt-1 pb-6">
              <div className="flex items-center gap-2">
                {entry.version && (
                  <span className="font-mono text-sm font-medium">{entry.version}</span>
                )}
                <span className={cn('text-sm', colors.text)}>({entry.label})</span>
                {entry.isCurrent && (
                  <span className="rounded bg-primary px-1.5 py-0.5 text-xs text-primary-foreground">
                    Current
                  </span>
                )}
              </div>
              {entry.timestamp && (
                <span className="text-xs text-muted-foreground">
                  {formatTimestamp(entry.timestamp)}
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}
