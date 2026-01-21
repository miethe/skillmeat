/**
 * Count Badge Component
 *
 * Displays a total artifact count with a tooltip breakdown by type.
 * Used for showing aggregated counts with detailed hover information.
 */

'use client';

import * as React from 'react';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

// ============================================================================
// Types
// ============================================================================

export interface CountBadgeProps {
  /** Counts by artifact type (e.g., { skill: 5, command: 3 }) */
  countsByType: Record<string, number>;
  /** Additional CSS classes */
  className?: string;
}

// ============================================================================
// Helpers
// ============================================================================

/**
 * Capitalize the first letter of a string and format for display.
 * Handles snake_case by converting to Title Case.
 * @example "skill" -> "Skills", "mcp_server" -> "Mcp Servers"
 */
function formatTypeName(type: string): string {
  return (
    type
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ') + 's'
  );
}

/**
 * Calculate total count from counts record.
 */
function calculateTotal(counts: Record<string, number>): number {
  return Object.values(counts).reduce((sum, count) => sum + count, 0);
}

/**
 * Build breakdown string for tooltip display.
 * @example "Skills: 5, Commands: 3, Agents: 2"
 */
function buildBreakdownText(counts: Record<string, number>): string {
  const entries = Object.entries(counts)
    .filter(([, count]) => count > 0)
    .sort(([, a], [, b]) => b - a); // Sort by count descending

  if (entries.length === 0) {
    return 'No artifacts';
  }

  return entries.map(([type, count]) => `${formatTypeName(type)}: ${count}`).join(', ');
}

// ============================================================================
// Component
// ============================================================================

export function CountBadge({ countsByType, className }: CountBadgeProps) {
  const total = calculateTotal(countsByType);
  const breakdownText = buildBreakdownText(countsByType);
  const hasItems = total > 0;

  // Build aria-label for accessibility
  const ariaLabel = hasItems
    ? `${total} artifact${total !== 1 ? 's' : ''}: ${breakdownText}`
    : 'No artifacts';

  // If no items, show a muted badge
  if (!hasItems) {
    return (
      <Badge
        variant="secondary"
        className={cn('text-muted-foreground', className)}
        aria-label={ariaLabel}
      >
        0
      </Badge>
    );
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant="secondary"
            className={cn('cursor-default tabular-nums', className)}
            aria-label={ariaLabel}
          >
            {total}
          </Badge>
        </TooltipTrigger>
        <TooltipContent>
          <p className="text-sm">{breakdownText}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
