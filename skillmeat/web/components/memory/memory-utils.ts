/**
 * Memory utility functions and constants.
 *
 * Provides confidence tier classification, color mapping, relative time
 * formatting, and status dot styling for memory components.
 */

// ---------------------------------------------------------------------------
// Confidence Tiers
// ---------------------------------------------------------------------------

export type ConfidenceTier = 'high' | 'medium' | 'low';

/**
 * Classify a 0-1 confidence score into a tier.
 *
 * Thresholds follow the design spec:
 *   high   >= 0.85
 *   medium >= 0.60
 *   low    <  0.60
 */
export function getConfidenceTier(confidence: number): ConfidenceTier {
  if (confidence >= 0.85) return 'high';
  if (confidence >= 0.60) return 'medium';
  return 'low';
}

/** Tailwind class sets for each confidence tier. */
export function getConfidenceColorClasses(tier: ConfidenceTier): {
  bg: string;
  text: string;
  border: string;
} {
  switch (tier) {
    case 'high':
      return {
        bg: 'bg-emerald-500/15 dark:bg-emerald-500/10',
        text: 'text-emerald-700 dark:text-emerald-400',
        border: 'border-emerald-500/30',
      };
    case 'medium':
      return {
        bg: 'bg-amber-500/15 dark:bg-amber-500/10',
        text: 'text-amber-700 dark:text-amber-400',
        border: 'border-amber-500/30',
      };
    case 'low':
      return {
        bg: 'bg-red-500/15 dark:bg-red-500/10',
        text: 'text-red-700 dark:text-red-400',
        border: 'border-red-500/30',
      };
  }
}

/** Solid bar color for the thin confidence indicator strip. */
export function getConfidenceBarColor(tier: ConfidenceTier): string {
  switch (tier) {
    case 'high':
      return 'bg-emerald-500';
    case 'medium':
      return 'bg-amber-500';
    case 'low':
      return 'bg-red-500';
  }
}

// ---------------------------------------------------------------------------
// Relative Time
// ---------------------------------------------------------------------------

/**
 * Format an ISO date string into a compact relative time string.
 *
 * Returns short forms like "2h ago", "3d ago", "1w ago" for dense UI.
 * Falls back to the date itself for very old items.
 */
export function formatRelativeTime(dateString: string | null | undefined): string {
  if (!dateString) return '';

  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return '';

  const now = Date.now();
  const diffMs = now - date.getTime();

  // Future dates
  if (diffMs < 0) return 'just now';

  const seconds = Math.floor(diffMs / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  const weeks = Math.floor(days / 7);
  const months = Math.floor(days / 30);

  if (seconds < 60) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  if (weeks < 5) return `${weeks}w ago`;
  if (months < 12) return `${months}mo ago`;

  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

// ---------------------------------------------------------------------------
// Status Dot Colors
// ---------------------------------------------------------------------------

/** Status dot Tailwind background classes keyed by memory status string. */
export const STATUS_DOT_CLASSES: Record<string, string> = {
  candidate: 'bg-amber-400',
  active: 'bg-emerald-400',
  stable: 'bg-blue-400',
  deprecated: 'bg-zinc-400 dark:bg-zinc-600',
};

/**
 * Get the dot color class for a status, with a safe fallback.
 */
export function getStatusDotClass(status: string): string {
  return STATUS_DOT_CLASSES[status] ?? 'bg-zinc-400';
}
