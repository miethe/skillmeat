'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

/**
 * Score breakdown from backend heuristic detector
 */
export interface ScoreBreakdown {
  dir_name_score: number;
  manifest_score: number;
  extensions_score: number;
  parent_hint_score: number;
  frontmatter_score: number;
  skill_manifest_bonus: number;
  container_hint_score: number;
  frontmatter_type_score: number;
  depth_penalty: number;
  raw_total: number;
  normalized_score: number;
}

/**
 * Signal configuration for display
 */
interface SignalDisplay {
  key: keyof Omit<ScoreBreakdown, 'raw_total' | 'normalized_score'>;
  label: string;
  description: string;
}

/**
 * Props for the HeuristicScoreBreakdown component
 */
export interface HeuristicScoreBreakdownProps {
  /**
   * Score breakdown from heuristic detector
   */
  breakdown: ScoreBreakdown;
  /**
   * Additional CSS classes
   */
  className?: string;
  /**
   * Display variant
   * - compact: Narrow layout for tooltips
   * - full: Spacious layout for modals/pages
   * @default 'full'
   */
  variant?: 'compact' | 'full';
}

/**
 * Signal display configuration with human-readable labels
 */
const SIGNALS: SignalDisplay[] = [
  {
    key: 'dir_name_score',
    label: 'Directory Name',
    description: 'Directory name matches artifact pattern',
  },
  {
    key: 'manifest_score',
    label: 'Manifest File',
    description: 'Has valid manifest file',
  },
  {
    key: 'extensions_score',
    label: 'File Extensions',
    description: 'Expected file extensions present',
  },
  {
    key: 'parent_hint_score',
    label: 'Parent Directory',
    description: 'Parent directory indicates artifact type',
  },
  {
    key: 'frontmatter_score',
    label: 'Frontmatter',
    description: 'Markdown frontmatter detected',
  },
  {
    key: 'skill_manifest_bonus',
    label: 'Skill Manifest Bonus',
    description: 'Definitive SKILL.md marker detected',
  },
  {
    key: 'container_hint_score',
    label: 'Container Hint',
    description: 'Inside a typed container directory (e.g. /skills)',
  },
  {
    key: 'frontmatter_type_score',
    label: 'Frontmatter Type',
    description: 'Explicit type field found in frontmatter',
  },
  {
    key: 'depth_penalty',
    label: 'Depth Penalty',
    description: 'Penalty for deep directory nesting',
  },
];

/**
 * HeuristicScoreBreakdown Component
 *
 * Displays the breakdown of heuristic detector scores showing all signal
 * contributions to the final confidence score.
 *
 * @example
 * ```tsx
 * // In tooltip (compact)
 * <HeuristicScoreBreakdown breakdown={scoreData} variant="compact" />
 *
 * // In modal (full)
 * <HeuristicScoreBreakdown breakdown={scoreData} variant="full" />
 * ```
 */
export function HeuristicScoreBreakdown({
  breakdown,
  className,
  variant = 'full',
}: HeuristicScoreBreakdownProps) {
  const isCompact = variant === 'compact';

  return (
    <div className={cn('space-y-2', isCompact ? 'text-xs' : 'text-sm', className)}>
      {/* Signal scores */}
      <div className={cn('space-y-1', isCompact ? 'space-y-0.5' : 'space-y-1')}>
        {SIGNALS.map((signal) => {
          const value = breakdown[signal.key];
          const isPositive = value > 0;
          const isNegative = value < 0;

          return (
            <div
              key={signal.key}
              className={cn('flex items-center justify-between', isCompact ? 'gap-2' : 'gap-3')}
            >
              <span
                className={cn('font-medium', isCompact ? 'text-xs' : 'text-sm', 'text-foreground')}
                title={signal.description}
              >
                {signal.label}
              </span>
              <span
                className={cn(
                  'font-mono tabular-nums',
                  isCompact ? 'text-xs' : 'text-sm',
                  isPositive && 'text-green-600 dark:text-green-400',
                  isNegative && 'text-red-600 dark:text-red-400',
                  !isPositive && !isNegative && 'text-muted-foreground'
                )}
                aria-label={`${signal.label}: ${value > 0 ? '+' : ''}${value}`}
              >
                {value > 0 ? '+' : ''}
                {value}
              </span>
            </div>
          );
        })}
      </div>

      {/* Calculation separator */}
      <div className="border-t border-border pt-2" />

      {/* Raw total */}
      <div className={cn('flex items-center justify-between', isCompact ? 'gap-2' : 'gap-3')}>
        <span className="font-semibold text-foreground">Raw Total</span>
        <span className="font-mono font-semibold tabular-nums">{breakdown.raw_total}</span>
      </div>

      {/* Normalization arrow */}
      <div className="flex items-center justify-center text-muted-foreground">
        <span className={cn('font-medium', isCompact ? 'text-xs' : 'text-sm')}>
          ↓ Normalized (0-100)
        </span>
      </div>

      {/* Final normalized score */}
      <div
        className={cn(
          'flex items-center justify-between rounded-md bg-muted px-3 py-2',
          isCompact && 'px-2 py-1.5'
        )}
      >
        <span className="font-bold text-foreground">Final Score</span>
        <span
          className={cn(
            'font-mono font-bold tabular-nums',
            isCompact ? 'text-base' : 'text-lg',
            'text-primary'
          )}
          aria-label={`Final normalized score: ${breakdown.normalized_score} out of 100`}
        >
          {breakdown.normalized_score}
        </span>
      </div>
    </div>
  );
}
