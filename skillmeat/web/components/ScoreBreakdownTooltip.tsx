'use client';

import * as React from 'react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  HeuristicScoreBreakdown,
  type ScoreBreakdown,
} from '@/components/HeuristicScoreBreakdown';

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
 * ScoreBreakdownTooltip Component
 *
 * Wraps the HeuristicScoreBreakdown component in a Radix Tooltip for hover display.
 * Uses the compact variant for narrow tooltip display.
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
  // Generate screen reader summary
  const srSummary = `Confidence score breakdown: ${breakdown.normalized_score}% confidence from ${breakdown.raw_total} raw points. Signals include directory name, manifest file, file extensions, parent directory, frontmatter, and depth penalty.`;

  return (
    <TooltipProvider>
      <Tooltip delayDuration={delayDuration}>
        <TooltipTrigger asChild>{children}</TooltipTrigger>
        <TooltipContent
          side={side}
          className={className || 'max-w-xs p-3'}
          aria-label="Confidence score breakdown showing signal contributions"
        >
          {/* Screen reader announcement */}
          <span className="sr-only">{srSummary}</span>
          {/* Visual breakdown */}
          <HeuristicScoreBreakdown breakdown={breakdown} variant="compact" />
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
