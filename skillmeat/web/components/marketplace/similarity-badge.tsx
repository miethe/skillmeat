/**
 * SimilarityBadge Component
 *
 * Color-coded pill badge that classifies an artifact similarity score
 * into a named band (High Match / Partial Match / Low Match) using
 * configurable thresholds and colors from GET /api/v1/settings/similarity.
 *
 * Score bands (applied in descending priority):
 *   score >= thresholds.high    → "High Match"
 *   score >= thresholds.partial → "Partial Match"
 *   score >= thresholds.low     → "Low Match"
 *   score < thresholds.floor    → render nothing (null)
 *   between floor and low       → render nothing (null)
 *
 * Text contrast is handled automatically by the Badge primitive using
 * the WCAG 2.0 relative luminance formula, ensuring AA compliance.
 */

import * as React from 'react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { SimilarityThresholds, SimilarityColors } from '@/types/similarity';

// ============================================================================
// Types
// ============================================================================

export interface SimilarityBadgeProps {
  /** Similarity score in the range [0.0, 1.0] */
  score: number;
  /** Score thresholds that define the match bands */
  thresholds: SimilarityThresholds;
  /** CSS color strings (hex) for each match band */
  colors: SimilarityColors;
  /** Additional CSS class names */
  className?: string;
}

// Internal band representation
interface SimilarityBand {
  label: string;
  color: string;
}

// ============================================================================
// Helpers
// ============================================================================

/**
 * Determine the similarity band for a given score and threshold config.
 * Returns null when the score falls below the display floor or between
 * the floor and the lowest named band.
 */
function resolveBand(
  score: number,
  thresholds: SimilarityThresholds,
  colors: SimilarityColors
): SimilarityBand | null {
  if (score >= thresholds.high) {
    return { label: 'High Match', color: colors.high };
  }
  if (score >= thresholds.partial) {
    return { label: 'Partial Match', color: colors.partial };
  }
  if (score >= thresholds.low) {
    return { label: 'Low Match', color: colors.low };
  }
  // Below the lowest named band — suppress (includes between floor and low)
  return null;
}

/**
 * Format a [0.0, 1.0] score as a percentage string, e.g. "87%".
 */
function formatPercent(score: number): string {
  return `${Math.round(score * 100)}%`;
}

// ============================================================================
// Component
// ============================================================================

/**
 * Renders a color-coded similarity score badge.
 *
 * Returns null when the score is below the configured floor threshold
 * or between the floor and the lowest named band.
 */
export function SimilarityBadge({ score, thresholds, colors, className }: SimilarityBadgeProps) {
  const band = resolveBand(score, thresholds, colors);

  if (!band) return null;

  const percent = formatPercent(score);
  // aria-label: "<Level>: <percent>" e.g. "High similarity: 87%"
  const levelName = band.label.split(' ')[0]; // "High" | "Partial" | "Low"
  const ariaLabel = `${levelName} similarity: ${percent}`;

  return (
    <Badge
      colorStyle={band.color}
      className={cn('gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium', className)}
      aria-label={ariaLabel}
    >
      <span className="font-semibold">{percent}</span>
      <span className="opacity-80">{band.label}</span>
    </Badge>
  );
}
