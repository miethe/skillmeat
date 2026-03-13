/**
 * AttestationBadge Component
 *
 * Inline badge displaying attestation status (owner scope + signature status).
 * Appears on artifact cards and detail headers alongside source/version badges.
 *
 * Variants (WF-3):
 *   unsigned    → muted zinc-400, circle outline icon
 *   user        → blue-600, single filled circle
 *   team        → green-600, double filled circle
 *   enterprise  → purple-600, triple filled circle (bold)
 */

'use client';

import * as React from 'react';
import { ShieldCheck, ShieldOff } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type AttestationVariant = 'unsigned' | 'user' | 'team' | 'enterprise';

export interface AttestationBadgeProps {
  /** Attestation tier */
  variant: AttestationVariant;
  /** Who created the attestation (actor identifier) */
  actor?: string;
  /** ISO-8601 date string when the attestation was created */
  date?: string;
  /** Additional Tailwind classes */
  className?: string;
}

// ---------------------------------------------------------------------------
// Variant configuration
// ---------------------------------------------------------------------------

interface VariantConfig {
  /** Badge label text */
  label: string;
  /** Dot indicator(s) rendered before the label */
  dots: number;
  /** CSS classes for the badge itself */
  badgeClass: string;
  /** Accessible scope description */
  scopeLabel: string;
}

const VARIANT_CONFIG: Record<AttestationVariant, VariantConfig> = {
  unsigned: {
    label: 'No attestation',
    dots: 0,
    badgeClass:
      'border-zinc-300 bg-zinc-100 text-zinc-400 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-500',
    scopeLabel: 'unsigned',
  },
  user: {
    label: 'User attested',
    dots: 1,
    badgeClass:
      'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-400',
    scopeLabel: 'user',
  },
  team: {
    label: 'Team attested',
    dots: 2,
    badgeClass:
      'border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-400',
    scopeLabel: 'team',
  },
  enterprise: {
    label: 'Enterprise',
    dots: 3,
    badgeClass:
      'border-purple-200 bg-purple-50 text-purple-700 dark:border-purple-800 dark:bg-purple-950 dark:text-purple-400 font-bold',
    scopeLabel: 'enterprise',
  },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Format an ISO date string to a localized short date.
 * Falls back to the raw string if parsing fails.
 */
function formatShortDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return iso;
  }
}

/**
 * Build the accessible aria-label for the badge.
 */
function buildAriaLabel(
  config: VariantConfig,
  actor?: string,
  date?: string
): string {
  if (config.scopeLabel === 'unsigned') {
    return 'Attestation status: no attestation';
  }

  const parts = [`Attestation status: ${config.scopeLabel} attested`];
  if (actor) parts.push(`by ${actor}`);
  if (date) parts.push(`on ${formatShortDate(date)}`);
  return parts.join(' ');
}

// ---------------------------------------------------------------------------
// Dot indicators
// ---------------------------------------------------------------------------

function DotIndicators({
  count,
  variant,
}: {
  count: number;
  variant: AttestationVariant;
}) {
  if (count === 0) {
    // Unsigned: hollow circle via ShieldOff-like ring
    return (
      <ShieldOff
        className="h-3 w-3 flex-shrink-0"
        aria-hidden="true"
      />
    );
  }

  if (variant === 'enterprise') {
    return (
      <ShieldCheck
        className="h-3 w-3 flex-shrink-0"
        aria-hidden="true"
      />
    );
  }

  // user (1) / team (2): filled dots
  return (
    <span className="flex flex-shrink-0 items-center gap-0.5" aria-hidden="true">
      {Array.from({ length: count }).map((_, i) => (
        <span
          key={i}
          className={cn(
            'inline-block h-1.5 w-1.5 rounded-full',
            variant === 'user' && 'bg-blue-600 dark:bg-blue-400',
            variant === 'team' && 'bg-green-600 dark:bg-green-400'
          )}
        />
      ))}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Tooltip content
// ---------------------------------------------------------------------------

function AttestationTooltipContent({
  config,
  actor,
  date,
  variant,
}: {
  config: VariantConfig;
  actor?: string;
  date?: string;
  variant: AttestationVariant;
}) {
  if (variant === 'unsigned') {
    return (
      <p className="text-xs">
        This artifact has not been attested.
      </p>
    );
  }

  return (
    <div className="space-y-1 text-xs">
      <p className="font-medium capitalize">{config.scopeLabel} attestation</p>
      {actor && (
        <p className="text-muted-foreground">
          <span className="font-medium">By:</span> {actor}
        </p>
      )}
      {date && (
        <p className="text-muted-foreground">
          <span className="font-medium">Date:</span> {formatShortDate(date)}
        </p>
      )}
      {!actor && !date && (
        <p className="text-muted-foreground">No additional details available.</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

/**
 * AttestationBadge — inline badge showing attestation tier with tooltip.
 *
 * Size matches existing source/version badges in UnifiedCard (h-5, text-xs).
 * No layout shift: fixed-width dot area preserves inline width across variants.
 *
 * @example
 * ```tsx
 * // On an artifact card
 * <AttestationBadge variant="user" actor="alice" date="2026-03-13T10:00:00Z" />
 *
 * // In a detail header
 * <AttestationBadge variant="enterprise" />
 *
 * // No attestation
 * <AttestationBadge variant="unsigned" />
 * ```
 */
export function AttestationBadge({
  variant,
  actor,
  date,
  className,
}: AttestationBadgeProps) {
  const config = VARIANT_CONFIG[variant];
  const ariaLabel = buildAriaLabel(config, actor, date);

  const badge = (
    <Badge
      variant="outline"
      className={cn(
        // Match ScoreBadge sm sizing / UnifiedCard metadata badge sizing
        'inline-flex h-5 cursor-default select-none items-center gap-1 px-1.5 py-0.5 text-xs',
        // Prevent layout shift: the badge always occupies the same flow space
        'flex-shrink-0 whitespace-nowrap',
        config.badgeClass,
        className
      )}
      aria-label={ariaLabel}
      role="status"
    >
      <DotIndicators count={config.dots} variant={variant} />
      <span>{config.label}</span>
    </Badge>
  );

  return (
    <TooltipProvider>
      <Tooltip delayDuration={300}>
        <TooltipTrigger asChild>{badge}</TooltipTrigger>
        <TooltipContent
          side="top"
          className="max-w-[200px]"
          // Tooltip is readable by screen readers via aria-label on the badge itself
          aria-hidden="true"
        >
          <AttestationTooltipContent
            config={config}
            actor={actor}
            date={date}
            variant={variant}
          />
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
