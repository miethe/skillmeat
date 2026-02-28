/**
 * ExecutionProgress Component
 *
 * Compact progress bar strip for the workflow execution dashboard.
 * Renders between the ExecutionHeader and the main split layout.
 *
 * Features:
 *  - shadcn Progress bar with percentage fill derived from terminal-stage count
 *  - "N of M stages complete" text label
 *  - Colour-coded bar accent: green (all complete), red (any failed), default (in-progress)
 *  - Indeterminate / pulsing state when execution status is `pending`
 *  - Live elapsed-time counter (updates every second for active executions)
 *
 * @example
 * ```tsx
 * <ExecutionProgress
 *   stages={execution.stages}
 *   executionStatus={execution.status}
 *   startedAt={execution.startedAt ?? null}
 * />
 * ```
 */

'use client';

import * as React from 'react';
import { Timer } from 'lucide-react';

import { cn } from '@/lib/utils';
import { Progress } from '@/components/ui/progress';

import type { StageExecution, ExecutionStatus } from '@/types/workflow';

// ============================================================================
// Types
// ============================================================================

export interface ExecutionProgressProps {
  /** Per-stage execution states from the workflow execution object */
  stages: StageExecution[];
  /** Overall execution lifecycle status */
  executionStatus: ExecutionStatus;
  /** ISO 8601 timestamp when execution began; null when not yet started */
  startedAt: string | null;
  /** Optional Tailwind class overrides for the outer element */
  className?: string;
}

// ============================================================================
// Constants
// ============================================================================

/** Statuses that count toward the "done" tally for the progress calculation */
const TERMINAL_STAGE_STATUSES = new Set<ExecutionStatus>([
  'completed',
  'failed',
  'cancelled',
]);

/** Statuses where the live elapsed-time counter should keep ticking */
const ACTIVE_EXECUTION_STATUSES = new Set<ExecutionStatus>([
  'running',
  'paused',
  'waiting_for_approval',
]);

// ============================================================================
// Helpers
// ============================================================================

/**
 * Derives the progress percentage and status-based colour accent from the
 * current stage list and overall execution status.
 *
 * Returns:
 *  - `pct`        : 0–100 integer for the Progress value prop
 *  - `doneCount`  : number of terminal stages (completed | failed | cancelled)
 *  - `totalCount` : total stages
 *  - `hasFailed`  : true when at least one stage has status "failed"
 *  - `allDone`    : true when execution is in a terminal state
 */
function deriveProgress(stages: StageExecution[], executionStatus: ExecutionStatus) {
  const totalCount = stages.length;
  const doneCount = stages.filter((s) => TERMINAL_STAGE_STATUSES.has(s.status)).length;
  const hasFailed =
    executionStatus === 'failed' || stages.some((s) => s.status === 'failed');
  const allDone = ['completed', 'failed', 'cancelled'].includes(executionStatus);
  const pct = totalCount === 0 ? 0 : Math.round((doneCount / totalCount) * 100);

  return { pct, doneCount, totalCount, hasFailed, allDone };
}

/**
 * Formats elapsed milliseconds as a human-readable duration string.
 *
 * - Under 1 minute : "42s"
 * - 1–59 minutes   : "3m 07s"
 * - 1 hour+        : "1h 22m"
 */
function formatElapsed(ms: number): string {
  const totalSeconds = Math.floor(ms / 1_000);
  const hours = Math.floor(totalSeconds / 3_600);
  const minutes = Math.floor((totalSeconds % 3_600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) return `${hours}h ${String(minutes).padStart(2, '0')}m`;
  if (minutes > 0) return `${minutes}m ${String(seconds).padStart(2, '0')}s`;
  return `${seconds}s`;
}

// ============================================================================
// Sub-components
// ============================================================================

/**
 * Renders the animated "indeterminate" track shown during `pending` state.
 *
 * Uses a standard HTML <style> element (no styled-jsx) to inject the
 * @keyframes rule. This is safe in Next.js App Router client components.
 * The keyframe slides a semi-transparent stripe across the track.
 */
function IndeterminateTrack() {
  return (
    <>
      {/* Keyframes: inject once into the document head via standard <style> */}
      <style>{`
        @keyframes ep-shimmer {
          0%   { transform: translateX(-100%); }
          100% { transform: translateX(400%); }
        }
      `}</style>
      <div
        className="relative h-1.5 w-full overflow-hidden rounded-full bg-primary/20"
        role="progressbar"
        aria-label="Initializing execution"
        aria-valuetext="Initializing"
      >
        {/* Animated shimmer stripe */}
        <div
          aria-hidden="true"
          className="absolute inset-y-0 w-1/4 rounded-full bg-primary/60"
          style={{ animation: 'ep-shimmer 1.6s ease-in-out infinite' }}
        />
      </div>
    </>
  );
}

// ============================================================================
// Live elapsed-time hook
// ============================================================================

/**
 * Returns a live elapsed-time string that updates once per second.
 * Stops ticking when the execution reaches a terminal or idle state.
 */
function useElapsedTime(
  startedAt: string | null,
  executionStatus: ExecutionStatus
): string | null {
  const [elapsed, setElapsed] = React.useState<string | null>(null);
  const isActive = ACTIVE_EXECUTION_STATUSES.has(executionStatus);

  React.useEffect(() => {
    if (!startedAt) {
      setElapsed(null);
      return;
    }

    const compute = () => {
      const ms = Date.now() - new Date(startedAt).getTime();
      setElapsed(formatElapsed(ms));
    };

    compute(); // Snapshot on mount / status change

    if (!isActive) return; // Don't tick for terminal states

    const id = setInterval(compute, 1_000);
    return () => clearInterval(id);
  }, [startedAt, isActive]);

  return elapsed;
}

// ============================================================================
// Main component
// ============================================================================

/**
 * ExecutionProgress — compact progress strip for the workflow execution dashboard.
 *
 * Layout (left to right, single row):
 *   [Progress bar ─────────────────]  [N of M stages complete]  ·  [⏱ elapsed]
 *
 * States:
 *   - pending             : indeterminate shimmer, "Initializing…" label
 *   - running             : filled bar (blue/primary), count label, live timer
 *   - completed           : 100% green bar, "All N stages complete"
 *   - failed              : red/destructive bar, count label
 *   - paused              : amber bar, count label, frozen timer
 *   - waiting_for_approval: default bar, count label, live timer
 *   - cancelled           : muted bar, count label, frozen timer
 *
 * Accessibility:
 *   - Progress bar: role="progressbar" with aria-valuenow/min/max/valuetext
 *   - Count label: aria-live="polite" when pending (announces "Initializing…")
 *   - Timer: role="timer" with aria-label (non-assertive; aria-live="off")
 */
export function ExecutionProgress({
  stages,
  executionStatus,
  startedAt,
  className,
}: ExecutionProgressProps) {
  const elapsed = useElapsedTime(startedAt, executionStatus);
  const isPending = executionStatus === 'pending';

  // ── Derived state ──────────────────────────────────────────────────────────
  const { pct, doneCount, totalCount, hasFailed, allDone } = deriveProgress(
    stages,
    executionStatus
  );

  // ── Progress bar accent class ──────────────────────────────────────────────
  //
  // shadcn Progress renders an Indicator child <div> inside the Root.
  // We can't add a className to the Indicator directly; instead we use the
  // Tailwind `[&>div]` arbitrary variant on the Progress root to target it.
  //
  const progressAccentClass: string = (() => {
    if (allDone && !hasFailed && executionStatus === 'completed') {
      return '[&>div]:bg-green-500 dark:[&>div]:bg-green-500';
    }
    if (hasFailed) {
      return '[&>div]:bg-destructive';
    }
    if (executionStatus === 'paused') {
      return '[&>div]:bg-amber-500';
    }
    if (executionStatus === 'cancelled') {
      return '[&>div]:bg-muted-foreground/50';
    }
    // Default: theme primary (running / waiting_for_approval)
    return '';
  })();

  // ── Text label ─────────────────────────────────────────────────────────────
  const labelText: string = (() => {
    if (isPending) return 'Initializing\u2026';
    if (totalCount === 0) return 'No stages';
    if (executionStatus === 'completed') {
      return `All ${totalCount} stage${totalCount !== 1 ? 's' : ''} complete`;
    }
    return `${doneCount} of ${totalCount} stage${totalCount !== 1 ? 's' : ''} complete`;
  })();

  // ── Accessibility text for the progress bar ────────────────────────────────
  const ariaValueText = isPending ? 'Initializing' : `${pct}% — ${labelText}`;

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div
      className={cn(
        // Compact strip — deliberately thin to avoid competing with content
        'flex min-h-0 items-center gap-3 px-4 py-2',
        'border-b border-border bg-background/80',
        className
      )}
      aria-label="Execution progress"
    >
      {/* ── Progress track ──────────────────────────────────────────────── */}
      <div className="relative min-w-0 flex-1">
        {isPending ? (
          <IndeterminateTrack />
        ) : (
          <Progress
            value={pct}
            className={cn('h-1.5 transition-all duration-500', progressAccentClass)}
            aria-label="Stage completion progress"
            aria-valuenow={pct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuetext={ariaValueText}
          />
        )}
      </div>

      {/* ── Count label ─────────────────────────────────────────────────── */}
      <p
        className={cn(
          'shrink-0 whitespace-nowrap text-xs tabular-nums',
          executionStatus === 'completed' && !hasFailed
            ? 'text-green-600 dark:text-green-400'
            : hasFailed
              ? 'text-destructive'
              : isPending
                ? 'text-muted-foreground/60 italic'
                : 'text-muted-foreground'
        )}
        aria-live={isPending ? 'polite' : 'off'}
      >
        {labelText}
      </p>

      {/* ── Elapsed time ────────────────────────────────────────────────── */}
      {elapsed !== null && (
        <>
          {/* Separator dot */}
          <span aria-hidden="true" className="shrink-0 select-none text-muted-foreground/30">
            ·
          </span>

          <time
            role="timer"
            aria-live="off"
            aria-label={`Elapsed time: ${elapsed}`}
            className="flex shrink-0 items-center gap-1 whitespace-nowrap text-xs tabular-nums text-muted-foreground"
          >
            <Timer className="h-3 w-3 shrink-0 text-muted-foreground/60" aria-hidden="true" />
            {elapsed}
          </time>
        </>
      )}
    </div>
  );
}
