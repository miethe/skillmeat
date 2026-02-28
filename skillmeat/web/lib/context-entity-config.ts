/**
 * Context Entity Type Configuration
 *
 * Centralised, configurable map of display properties per entity type.
 * Import `getEntityTypeConfig` in components rather than hardcoding colours or labels.
 */

export interface ContextEntityTypeConfig {
  /** Display name shown in badges (e.g., "Config", "Spec") */
  label: string;
  /** Tailwind colour key used for dynamic class generation (e.g., "blue") */
  color: string;
  /** Badge background class (e.g., "bg-blue-500/10") */
  bgClass: string;
  /** Badge text class (e.g., "text-blue-600 dark:text-blue-400") */
  textClass: string;
  /** Card left-border accent class (e.g., "border-l-blue-500") */
  borderClass: string;
  /** Card subtle background tint (e.g., "bg-blue-500/[0.02]") */
  cardBgClass: string;
  /** Lucide icon name identifier used to resolve the correct icon */
  icon: 'settings' | 'file-text' | 'shield' | 'book-open' | 'clock' | 'file';
}

export const CONTEXT_ENTITY_TYPE_CONFIG: Record<string, ContextEntityTypeConfig> = {
  project_config: {
    label: 'Config',
    color: 'blue',
    bgClass: 'bg-blue-500/10',
    textClass: 'text-blue-600 dark:text-blue-400',
    borderClass: 'border-l-blue-500',
    cardBgClass: 'bg-blue-500/[0.02] dark:bg-blue-500/[0.03]',
    icon: 'settings',
  },
  spec_file: {
    label: 'Spec',
    color: 'purple',
    bgClass: 'bg-purple-500/10',
    textClass: 'text-purple-600 dark:text-purple-400',
    borderClass: 'border-l-purple-500',
    cardBgClass: 'bg-purple-500/[0.02] dark:bg-purple-500/[0.03]',
    icon: 'file-text',
  },
  rule_file: {
    label: 'Rule',
    color: 'orange',
    bgClass: 'bg-orange-500/10',
    textClass: 'text-orange-600 dark:text-orange-400',
    borderClass: 'border-l-orange-500',
    cardBgClass: 'bg-orange-500/[0.02] dark:bg-orange-500/[0.03]',
    icon: 'shield',
  },
  context_file: {
    label: 'Context',
    color: 'green',
    bgClass: 'bg-green-500/10',
    textClass: 'text-green-600 dark:text-green-400',
    borderClass: 'border-l-green-500',
    cardBgClass: 'bg-green-500/[0.02] dark:bg-green-500/[0.03]',
    icon: 'book-open',
  },
  progress_template: {
    label: 'Progress',
    color: 'yellow',
    bgClass: 'bg-yellow-500/10',
    textClass: 'text-yellow-600 dark:text-yellow-400',
    borderClass: 'border-l-yellow-500',
    cardBgClass: 'bg-yellow-500/[0.02] dark:bg-yellow-500/[0.03]',
    icon: 'clock',
  },
};

/** Default fallback configuration used for unknown entity types. */
export const DEFAULT_ENTITY_TYPE_CONFIG: ContextEntityTypeConfig = {
  label: 'Entity',
  color: 'gray',
  bgClass: 'bg-muted',
  textClass: 'text-muted-foreground',
  borderClass: 'border-l-border',
  cardBgClass: '',
  icon: 'file',
};

/**
 * Returns the display configuration for a given entity type string.
 * Tries exact match first, then lowercase, then uppercase enum-style (e.g. "RULE_FILE").
 * Falls back to `DEFAULT_ENTITY_TYPE_CONFIG` for unrecognised types.
 */
export function getEntityTypeConfig(entityType: string | undefined | null): ContextEntityTypeConfig {
  if (!entityType) return DEFAULT_ENTITY_TYPE_CONFIG;

  // Exact match (most common — API returns lowercase snake_case)
  const exact = CONTEXT_ENTITY_TYPE_CONFIG[entityType];
  if (exact) return exact;

  // Try lowercase (handles any casing from API)
  const lower = CONTEXT_ENTITY_TYPE_CONFIG[entityType.toLowerCase()];
  if (lower) return lower;

  return DEFAULT_ENTITY_TYPE_CONFIG;
}
