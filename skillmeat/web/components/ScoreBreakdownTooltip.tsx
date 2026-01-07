'use client';

import * as React from 'react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { type ScoreBreakdown } from '@/components/HeuristicScoreBreakdown';

/**
 * Props for the ScoreBreakdownTooltip component
 */
export interface ScoreBreakdownTooltipProps {
  /**
   * Score breakdown data from heuristic detector
   */
  breakdown: ScoreBreakdown;
  /**
   * Trigger element (what shows the tooltip on hover)
   */
  children: React.ReactNode;
  /**
   * Side for tooltip placement
   * @default 'top'
   */
  side?: 'top' | 'right' | 'bottom' | 'left';
  /**
   * Delay before showing (ms)
   * @default 200
   */
  delayDuration?: number;
  /**
   * Additional CSS classes for tooltip content
   */
  className?: string;
}

/**
 * Short label mapping for inline format
 */
const SIGNAL_LABELS: Record<keyof Omit<ScoreBreakdown, 'raw_total' | 'normalized_score'>, string> = {
  dir_name_score: 'Dir Name',
  manifest_score: 'Manifest',
  extensions_score: 'Extensions',
  parent_hint_score: 'Parent',
  frontmatter_score: 'Frontmatter',
  skill_manifest_bonus: 'Manifest Bonus',
  container_hint_score: 'Container',
  frontmatter_type_score: 'Type Hint',
  depth_penalty: 'Depth',
};

/**
 * Format score breakdown as inline string
 * Shows only non-zero signals with sign (+/-)
 * @example "Dir Name: +30, Manifest: +25, Extensions: +20, Depth: -3"
 */
function formatInlineBreakdown(breakdown: ScoreBreakdown): string {
  const signals: string[] = [];

  // Iterate through signals and format non-zero values
  (Object.keys(SIGNAL_LABELS) as Array<keyof typeof SIGNAL_LABELS>).forEach((key) => {
    const value = breakdown[key];
    if (value !== 0) {
      const label = SIGNAL_LABELS[key];
      const sign = value > 0 ? '+' : '';
      signals.push(`${label}: ${sign}${value}`);
    }
  });

  return signals.join(', ');
}

/**
 * ScoreBreakdownTooltip Component
 *
 * Displays an inline score breakdown in a Radix Tooltip for hover display.
 * Shows only non-zero signals in a single-line format for compactness.
 *
 * Accessibility features:
 * - Radix Tooltip provides: keyboard navigation (Tab to focus trigger, tooltip shows),
 *   Escape to close, proper ARIA attributes (role="tooltip", aria-describedby)
 * - Screen reader announcement provides summary of score breakdown
 * - All interactive elements are keyboard-accessible
 *
 * @example
 * ```tsx
 * // Wrap a confidence badge
 * <ScoreBreakdownTooltip breakdown={match.score_breakdown}>
 *   <Badge variant="outline">85%</Badge>
 * </ScoreBreakdownTooltip>
 *
 * // Wrap custom trigger
 * <ScoreBreakdownTooltip
 *   breakdown={match.score_breakdown}
 *   side="right"
 *   delayDuration={300}
 * >
 *   <Button variant="ghost" size="sm">
 *     View Score Details
 *   </Button>
 * </ScoreBreakdownTooltip>
 * ```
 */
export function ScoreBreakdownTooltip({
  breakdown,
  children,
  side = 'top',
  delayDuration = 200,
  className,
}: ScoreBreakdownTooltipProps) {
  // Generate inline breakdown text
  const inlineBreakdown = formatInlineBreakdown(breakdown);

  // Generate screen reader summary
  const srSummary = `Confidence score breakdown: ${breakdown.normalized_score}% confidence from ${breakdown.raw_total} raw points. ${inlineBreakdown}.`;

  return (
    <TooltipProvider>
      <Tooltip delayDuration={delayDuration}>
        <TooltipTrigger asChild>{children}</TooltipTrigger>
        <TooltipContent
          side={side}
          className={className || 'max-w-md p-2'}
          aria-label="Confidence score breakdown showing signal contributions"
        >
          {/* Screen reader announcement */}
          <span className="sr-only">{srSummary}</span>
          {/* Visual inline breakdown */}
          <p className="text-xs text-foreground">{inlineBreakdown}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
