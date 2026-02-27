/**
 * StatusDot Component
 *
 * A compact colored circle indicator for workflow execution status.
 * Supports optional pulse animation for active states and an inline
 * text label for contexts that need both visual and textual cues.
 *
 * @example Basic usage
 * ```tsx
 * <StatusDot status="running" />
 * ```
 *
 * @example With label
 * ```tsx
 * <StatusDot status="completed" showLabel size="lg" />
 * ```
 *
 * @example Custom label override
 * ```tsx
 * <StatusDot status="waiting_for_approval" showLabel label="Awaiting" size="sm" />
 * ```
 *
 * @example No pulse for running
 * ```tsx
 * <StatusDot status="running" pulse={false} />
 * ```
 *
 * @example Reuse color classes elsewhere
 * ```tsx
 * import { STATUS_DOT_COLORS } from '@/components/shared/status-dot';
 * const { dot } = STATUS_DOT_COLORS['failed'];
 * ```
 */

import { cn } from '@/lib/utils';
import type { ExecutionStatus } from '@/types/workflow';

// ============================================================================
// Types
// ============================================================================

export interface StatusDotProps {
  /** Workflow execution status to visualize. */
  status: ExecutionStatus;
  /** Size of the dot. Defaults to 'md'. */
  size?: 'sm' | 'md' | 'lg';
  /**
   * Whether to show the pulse animation ring.
   * Defaults to `true` for 'running' and 'waiting_for_approval'; `false` otherwise.
   * Provide an explicit boolean to override the default behavior.
   */
  pulse?: boolean;
  /** Whether to render a text label beside the dot. Defaults to false. */
  showLabel?: boolean;
  /**
   * Override the displayed label text.
   * When omitted the label comes from STATUS_DOT_COLORS[status].label.
   */
  label?: string;
  /** Additional CSS classes applied to the outer wrapper element. */
  className?: string;
}

// ============================================================================
// Configuration
// ============================================================================

/**
 * Per-status color and label configuration.
 *
 * Export this map so consumers can derive consistent colors without
 * needing to render a full StatusDot component.
 *
 * Properties:
 * - `dot`   — Tailwind bg-* class for the solid dot.
 * - `ping`  — Tailwind bg-* class for the ping animation overlay (same hue, slightly lighter).
 * - `label` — Human-readable status label used when showLabel is true.
 */
export const STATUS_DOT_COLORS: Record<
  ExecutionStatus,
  { dot: string; ping: string; label: string }
> = {
  pending: {
    dot: 'bg-gray-400',
    ping: 'bg-gray-400',
    label: 'Pending',
  },
  running: {
    dot: 'bg-blue-500',
    ping: 'bg-blue-400',
    label: 'Running',
  },
  completed: {
    dot: 'bg-emerald-500',
    ping: 'bg-emerald-400',
    label: 'Completed',
  },
  failed: {
    dot: 'bg-red-500',
    ping: 'bg-red-400',
    label: 'Failed',
  },
  cancelled: {
    dot: 'bg-gray-500',
    ping: 'bg-gray-400',
    label: 'Cancelled',
  },
  paused: {
    dot: 'bg-amber-500',
    ping: 'bg-amber-400',
    label: 'Paused',
  },
  waiting_for_approval: {
    dot: 'bg-purple-500',
    ping: 'bg-purple-400',
    label: 'Awaiting Approval',
  },
};

/** Statuses that pulse by default when no explicit `pulse` prop is provided. */
const AUTO_PULSE_STATUSES = new Set<ExecutionStatus>(['running', 'waiting_for_approval']);

// ============================================================================
// Size Mapping
// ============================================================================

/**
 * Tailwind w-/h- classes for each size variant.
 *
 * sm  = 6px  (w-1.5 h-1.5)
 * md  = 8px  (w-2   h-2)
 * lg  = 12px (w-3   h-3)
 */
const SIZE_CLASSES: Record<'sm' | 'md' | 'lg', string> = {
  sm: 'w-1.5 h-1.5',
  md: 'w-2 h-2',
  lg: 'w-3 h-3',
};

const LABEL_SIZE_CLASSES: Record<'sm' | 'md' | 'lg', string> = {
  sm: 'text-xs',
  md: 'text-xs',
  lg: 'text-sm',
};

// ============================================================================
// Component
// ============================================================================

/**
 * StatusDot — Compact execution status indicator.
 *
 * Renders a colored circle with an optional animated ping ring for active
 * states ('running', 'waiting_for_approval'). An optional inline text label
 * can be shown beside the dot for contexts that require textual clarity.
 *
 * This component is purely presentational (no state or effects) and requires
 * no 'use client' directive.
 *
 * @param status       - The ExecutionStatus value to represent visually.
 * @param size         - Dot size variant: 'sm' | 'md' | 'lg'. Default: 'md'.
 * @param pulse        - Force-enable or -disable the ping animation. When
 *                       omitted, pulses automatically for 'running' and
 *                       'waiting_for_approval'.
 * @param showLabel    - Render a text label beside the dot. Default: false.
 * @param label        - Override the label text (uses config label when absent).
 * @param className    - Extra Tailwind classes for the outer wrapper.
 */
export function StatusDot({
  status,
  size = 'md',
  pulse,
  showLabel = false,
  label,
  className,
}: StatusDotProps) {
  const config = STATUS_DOT_COLORS[status];
  const sizeClass = SIZE_CLASSES[size];
  const labelSizeClass = LABEL_SIZE_CLASSES[size];

  // Resolve whether to show pulse: explicit prop wins, otherwise auto-detect.
  const shouldPulse = pulse !== undefined ? pulse : AUTO_PULSE_STATUSES.has(status);

  const resolvedLabel = label ?? config.label;

  return (
    <span
      className={cn('inline-flex items-center gap-1.5', className)}
      aria-label={`Status: ${resolvedLabel}`}
      role="status"
    >
      {/* Dot wrapper — relative container for the ping overlay */}
      <span className={cn('relative flex shrink-0', sizeClass)}>
        {/* Ping animation ring — renders only when pulse is active */}
        {shouldPulse && (
          <span
            className={cn(
              'absolute inset-0 rounded-full opacity-75 animate-ping',
              config.ping
            )}
            aria-hidden="true"
          />
        )}
        {/* Solid dot */}
        <span
          className={cn('relative inline-flex rounded-full', sizeClass, config.dot)}
          aria-hidden="true"
        />
      </span>

      {/* Optional text label */}
      {showLabel && (
        <span
          className={cn(
            'leading-none text-foreground/80 tabular-nums',
            labelSizeClass
          )}
        >
          {resolvedLabel}
        </span>
      )}
    </span>
  );
}
