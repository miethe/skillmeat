'use client';

import * as React from 'react';
import {
  Clock,
  Loader2,
  Check,
  X,
  ShieldQuestion,
  Ban,
  Pause,
} from 'lucide-react';

import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { StageExecution, ExecutionStatus } from '@/types/workflow';

// ============================================================================
// Types
// ============================================================================

export interface StageTimelineProps {
  stages: StageExecution[];
  selectedStageId: string | null;
  onSelectStage: (stageId: string) => void;
  className?: string;
}

// ============================================================================
// Status configuration
// ============================================================================

/**
 * Visual config for each ExecutionStatus value.
 * Colors follow the design reference: muted=pending, blue=running,
 * green=completed, red=failed, gray=cancelled, yellow=paused,
 * amber=waiting_for_approval.
 */
const STATUS_CONFIG: Record<
  ExecutionStatus,
  {
    icon: React.ElementType;
    iconClass?: string;
    nodeClass: string;
    connectorClass: string;
    label: string;
  }
> = {
  pending: {
    icon: Clock,
    nodeClass:
      'border-muted-foreground/30 bg-muted/50 text-muted-foreground/60',
    connectorClass: 'bg-border',
    label: 'Pending',
  },
  running: {
    icon: Loader2,
    iconClass: 'animate-spin',
    nodeClass: 'border-blue-500 bg-blue-50 text-blue-600 dark:bg-blue-950/50 dark:text-blue-400',
    connectorClass: 'bg-blue-300 dark:bg-blue-700',
    label: 'Running',
  },
  completed: {
    icon: Check,
    nodeClass:
      'border-green-500 bg-green-50 text-green-600 dark:bg-green-950/50 dark:text-green-400',
    connectorClass: 'bg-green-400 dark:bg-green-600',
    label: 'Completed',
  },
  failed: {
    icon: X,
    nodeClass: 'border-red-500 bg-red-50 text-red-600 dark:bg-red-950/50 dark:text-red-400',
    connectorClass: 'bg-red-300 dark:bg-red-700',
    label: 'Failed',
  },
  cancelled: {
    icon: Ban,
    nodeClass:
      'border-gray-400 bg-gray-50 text-gray-500 dark:bg-gray-900/50 dark:text-gray-400',
    connectorClass: 'bg-gray-300 dark:bg-gray-600',
    label: 'Cancelled',
  },
  paused: {
    icon: Pause,
    nodeClass:
      'border-yellow-500 bg-yellow-50 text-yellow-600 dark:bg-yellow-950/50 dark:text-yellow-400',
    connectorClass: 'bg-yellow-300 dark:bg-yellow-700',
    label: 'Paused',
  },
  waiting_for_approval: {
    icon: ShieldQuestion,
    nodeClass:
      'border-amber-500 bg-amber-50 text-amber-600 dark:bg-amber-950/50 dark:text-amber-400',
    connectorClass: 'bg-amber-300 dark:bg-amber-700',
    label: 'Waiting Gate',
  },
};

// ============================================================================
// Helpers
// ============================================================================

/**
 * Format a duration in milliseconds to a human-readable string.
 * E.g. 45000 → "45s", 83000 → "1:23", 3725000 → "1h 2m"
 */
function formatDuration(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  if (totalSeconds < 60) return `${totalSeconds}s`;
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes < 60) {
    return seconds === 0 ? `${minutes}m` : `${minutes}:${String(seconds).padStart(2, '0')}`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return remainingMinutes === 0 ? `${hours}h` : `${hours}h ${remainingMinutes}m`;
}

/**
 * Derive a display duration string from a StageExecution.
 * Returns elapsed time for running stages, final duration for completed ones.
 */
function getDurationText(stage: StageExecution): string | null {
  if (stage.durationMs != null && stage.durationMs > 0) {
    return formatDuration(stage.durationMs);
  }
  if (stage.startedAt && stage.status === 'running') {
    const elapsedMs = Date.now() - new Date(stage.startedAt).getTime();
    return formatDuration(Math.max(0, elapsedMs));
  }
  return null;
}

// ============================================================================
// StageTimelineNode (single item)
// ============================================================================

interface StageTimelineNodeProps {
  stage: StageExecution;
  isSelected: boolean;
  isLast: boolean;
  onSelect: () => void;
}

function StageTimelineNode({
  stage,
  isSelected,
  isLast,
  onSelect,
}: StageTimelineNodeProps) {
  const config = STATUS_CONFIG[stage.status];
  const Icon = config.icon;
  const isRunning = stage.status === 'running';
  const durationText = getDurationText(stage);
  const statusLabel = `${config.label}${durationText ? ` ${durationText}` : ''}`;

  return (
    <li
      role="listitem"
      className="flex items-start gap-3"
    >
      {/* ------------------------------------------------------------------ */}
      {/* Left column: node circle + connector line                           */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex flex-col items-center shrink-0 w-9">
        {/* Status circle */}
        <div
          className={cn(
            'h-9 w-9 rounded-full border-2 flex items-center justify-center transition-all duration-200',
            config.nodeClass,
            // Pulse ring for running stage
            isRunning && 'shadow-[0_0_0_4px_rgba(59,130,246,0.15)] dark:shadow-[0_0_0_4px_rgba(59,130,246,0.1)]',
          )}
          aria-hidden="true"
        >
          <Icon
            className={cn('h-4 w-4', config.iconClass)}
            aria-hidden="true"
          />
        </div>

        {/* Connector line to next node */}
        {!isLast && (
          <div
            className={cn(
              'w-0.5 flex-1 min-h-[1.5rem] transition-colors duration-300',
              config.connectorClass,
            )}
            aria-hidden="true"
          />
        )}
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Right column: clickable stage info card                             */}
      {/* ------------------------------------------------------------------ */}
      <button
        type="button"
        onClick={onSelect}
        aria-selected={isSelected}
        aria-current={isRunning ? 'step' : undefined}
        aria-label={`${stage.stageName}, ${statusLabel}`}
        className={cn(
          // Base layout
          'flex-1 min-w-0 rounded-md px-3 py-2 text-left text-sm',
          'transition-all duration-150 mb-3',
          // Unselected interactive state
          'hover:bg-accent/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1',
          // Selected state
          isSelected
            ? [
                'bg-accent ring-2 ring-ring',
                isRunning && 'bg-blue-50/80 ring-blue-400 dark:bg-blue-950/30 dark:ring-blue-500',
              ]
            : 'text-foreground',
        )}
      >
        {/* Status label (uppercase, muted, small) */}
        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-0.5">
          {config.label}
        </p>

        {/* Stage name */}
        <p className="font-semibold truncate leading-snug">
          {stage.stageName}
        </p>

        {/* Status + duration */}
        <p className="text-xs text-muted-foreground mt-0.5 capitalize">
          {statusLabel}
        </p>
      </button>
    </li>
  );
}

// ============================================================================
// StageTimeline
// ============================================================================

/**
 * StageTimeline — vertical timeline column for the execution dashboard.
 *
 * Displays a scrollable list of stage nodes with status-colored circles,
 * stage names, status text, and duration. Supports click selection and
 * J/K keyboard navigation.
 *
 * Accessibility:
 * - role="list" with role="listitem" per node
 * - aria-current="step" on the running stage
 * - aria-selected on the selected node
 * - J/K keys move selection (skips inputs/textareas)
 */
export function StageTimeline({
  stages,
  selectedStageId,
  onSelectStage,
  className,
}: StageTimelineProps) {
  // J/K keyboard navigation
  React.useEffect(() => {
    if (stages.length === 0) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Skip when focus is inside a text field
      const target = e.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        return;
      }

      if (e.key === 'j') {
        e.preventDefault();
        const currentIndex = stages.findIndex((s) => s.id === selectedStageId);
        const nextIndex =
          currentIndex === -1 ? 0 : Math.min(currentIndex + 1, stages.length - 1);
        const stage = stages[nextIndex];
        if (stage) onSelectStage(stage.id);
      } else if (e.key === 'k') {
        e.preventDefault();
        const currentIndex = stages.findIndex((s) => s.id === selectedStageId);
        const prevIndex =
          currentIndex <= 0 ? 0 : currentIndex - 1;
        const stage = stages[prevIndex];
        if (stage) onSelectStage(stage.id);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [stages, selectedStageId, onSelectStage]);

  if (stages.length === 0) {
    return (
      <div
        className={cn(
          'flex items-center justify-center h-full text-sm text-muted-foreground p-4',
          className,
        )}
      >
        No stages
      </div>
    );
  }

  return (
    <ScrollArea className={cn('h-full', className)}>
      <ol
        role="list"
        aria-label="Workflow stages"
        className="flex flex-col px-3 pt-3 pb-1"
      >
        {stages.map((stage, index) => (
          <StageTimelineNode
            key={stage.id}
            stage={stage}
            isSelected={stage.id === selectedStageId}
            isLast={index === stages.length - 1}
            onSelect={() => onSelectStage(stage.id)}
          />
        ))}
      </ol>
    </ScrollArea>
  );
}
