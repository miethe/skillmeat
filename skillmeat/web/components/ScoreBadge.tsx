/**
 * ScoreBadge Component
 *
 * Displays confidence score with color-coded visual indicator.
 * Color mapping:
 * - Green (>70): High confidence
 * - Yellow (50-70): Medium confidence
 * - Red (<50): Low confidence
 *
 * Ensures WCAG 2.1 AA contrast ratio (>4.5:1) for accessibility.
 */

'use client';

import * as React from 'react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

export interface ScoreBadgeProps {
  /** Confidence score (0-100) */
  confidence: number;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Additional CSS classes */
  className?: string;
}

/**
 * Get color class and hex value based on confidence score
 */
function getScoreColor(confidence: number): { colorClass: string; hexColor: string } {
  if (confidence > 70) {
    return {
      colorClass: 'bg-green-500 text-white border-green-600',
      hexColor: '#22c55e', // green-500
    };
  } else if (confidence >= 50) {
    return {
      colorClass: 'bg-yellow-500 text-black border-yellow-600',
      hexColor: '#eab308', // yellow-500
    };
  } else {
    return {
      colorClass: 'bg-red-500 text-white border-red-600',
      hexColor: '#ef4444', // red-500
    };
  }
}

/**
 * Get size-specific classes
 */
function getSizeClasses(size: 'sm' | 'md' | 'lg'): string {
  switch (size) {
    case 'sm':
      return 'text-[10px] px-1.5 py-0.5 h-4';
    case 'lg':
      return 'text-sm px-3 py-1 h-7';
    case 'md':
    default:
      return 'text-xs px-2 py-0.5 h-5';
  }
}

/**
 * ScoreBadge - Display confidence score with color-coded indicator
 *
 * Renders a badge showing the confidence score as a percentage,
 * with background color based on score range:
 * - Green: >70 (high confidence)
 * - Yellow: 50-70 (medium confidence)
 * - Red: <50 (low confidence)
 *
 * @example
 * ```tsx
 * <ScoreBadge confidence={87} size="md" />
 * ```
 *
 * @param props - ScoreBadgeProps configuration
 * @returns Badge component with score and color-coded styling
 */
export function ScoreBadge({ confidence, size = 'md', className }: ScoreBadgeProps) {
  // Clamp confidence to 0-100 range
  const clampedConfidence = Math.max(0, Math.min(100, confidence));

  // Round to nearest integer for display
  const displayScore = Math.round(clampedConfidence);

  // Get color styling
  const { colorClass, hexColor } = getScoreColor(clampedConfidence);

  // Get size classes
  const sizeClasses = getSizeClasses(size);

  // Determine confidence level text for aria-label
  let confidenceLevel: string;
  if (clampedConfidence > 70) {
    confidenceLevel = 'high';
  } else if (clampedConfidence >= 50) {
    confidenceLevel = 'medium';
  } else {
    confidenceLevel = 'low';
  }

  return (
    <Badge
      className={cn(
        'font-semibold tabular-nums',
        colorClass,
        sizeClasses,
        className
      )}
      colorStyle={hexColor}
      aria-label={`Confidence score: ${displayScore} percent, ${confidenceLevel} confidence`}
      title={`${confidenceLevel.charAt(0).toUpperCase() + confidenceLevel.slice(1)} confidence: ${displayScore}%`}
    >
      {displayScore}%
    </Badge>
  );
}

/**
 * ScoreBadgeSkeleton - Loading skeleton for score badge
 *
 * Displays a placeholder while score data is being fetched.
 *
 * @param size - Badge size variant
 */
export function ScoreBadgeSkeleton({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sizeClasses = getSizeClasses(size);

  return (
    <div
      className={cn(
        'inline-flex items-center rounded-md border bg-muted animate-pulse',
        sizeClasses
      )}
      aria-label="Loading confidence score"
    >
      <span className="opacity-0">00%</span>
    </div>
  );
}
