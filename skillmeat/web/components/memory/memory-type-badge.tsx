/**
 * MemoryTypeBadge Component
 *
 * Small pill badge displaying a memory item's type with a type-specific icon
 * and color. Uses shadcn Badge with outline variant.
 *
 * Color mapping follows the design spec (section 2.2).
 */

'use client';

import * as React from 'react';
import type { LucideIcon } from 'lucide-react';
import {
  ShieldAlert,
  GitBranch,
  Wrench,
  Puzzle,
  Lightbulb,
  Palette,
  AlertCircle,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Type Configuration
// ---------------------------------------------------------------------------

interface MemoryTypeConfig {
  label: string;
  icon: LucideIcon;
  textClass: string;
  borderClass: string;
}

/**
 * Visual configuration for each known memory type.
 *
 * Includes types from both the SDK enum (decision, constraint, gotcha,
 * style_rule, learning) and the design spec (fix, pattern). The `gotcha` type
 * maps to the same visual treatment as `fix` since they represent the same
 * concept (gotcha is the DB name, fix is the display name).
 */
const MEMORY_TYPE_CONFIG: Record<string, MemoryTypeConfig> = {
  constraint: {
    label: 'Constraint',
    icon: ShieldAlert,
    textClass: 'text-violet-700 dark:text-violet-400',
    borderClass: 'border-violet-500/40',
  },
  decision: {
    label: 'Decision',
    icon: GitBranch,
    textClass: 'text-blue-700 dark:text-blue-400',
    borderClass: 'border-blue-500/40',
  },
  fix: {
    label: 'Fix',
    icon: Wrench,
    textClass: 'text-orange-700 dark:text-orange-400',
    borderClass: 'border-orange-500/40',
  },
  gotcha: {
    label: 'Gotcha',
    icon: Wrench,
    textClass: 'text-orange-700 dark:text-orange-400',
    borderClass: 'border-orange-500/40',
  },
  pattern: {
    label: 'Pattern',
    icon: Puzzle,
    textClass: 'text-cyan-700 dark:text-cyan-400',
    borderClass: 'border-cyan-500/40',
  },
  learning: {
    label: 'Learning',
    icon: Lightbulb,
    textClass: 'text-pink-700 dark:text-pink-400',
    borderClass: 'border-pink-500/40',
  },
  style_rule: {
    label: 'Style Rule',
    icon: Palette,
    textClass: 'text-teal-700 dark:text-teal-400',
    borderClass: 'border-teal-500/40',
  },
};

/** Fallback config for unknown/future memory types. */
const UNKNOWN_TYPE_CONFIG: MemoryTypeConfig = {
  label: 'Unknown',
  icon: AlertCircle,
  textClass: 'text-muted-foreground',
  borderClass: 'border-border',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export interface MemoryTypeBadgeProps {
  /** The memory type string (e.g. "constraint", "decision"). */
  type: string;
  /** Additional class names applied to the badge. */
  className?: string;
}

/**
 * MemoryTypeBadge -- renders a compact type pill with icon.
 *
 * @example
 * ```tsx
 * <MemoryTypeBadge type="constraint" />
 * <MemoryTypeBadge type="decision" className="mt-1" />
 * ```
 */
export function MemoryTypeBadge({ type, className }: MemoryTypeBadgeProps) {
  const config = MEMORY_TYPE_CONFIG[type] ?? UNKNOWN_TYPE_CONFIG;
  const Icon = config.icon;

  return (
    <Badge
      variant="outline"
      className={cn(
        'flex-shrink-0 gap-1 px-1.5 py-0 text-[10px] font-medium uppercase tracking-wider',
        config.textClass,
        config.borderClass,
        className
      )}
    >
      <Icon className="h-2.5 w-2.5" aria-hidden="true" />
      {config.label}
    </Badge>
  );
}

export { MEMORY_TYPE_CONFIG };
