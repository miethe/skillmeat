/**
 * Trust Badges Component
 *
 * Display trust badges (Official, Verified, Community) based on artifact source configuration.
 * Shows a badge with tooltip explaining the trust level.
 *
 * Design:
 * - Official: Blue badge with checkmark
 * - Verified: Green badge with checkmark
 * - Community: Gray badge
 * - Keyboard accessible tooltips
 * - Supports dark mode
 */

'use client';

import * as React from 'react';
import { ShieldCheck, Shield } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

/**
 * Trust level types for artifact sources
 */
export type TrustLevel = 'official' | 'verified' | 'community';

/**
 * Props for TrustBadges component
 */
export interface TrustBadgesProps {
  /** Trust level to display */
  trustLevel: TrustLevel;
  /** Optional source URL/identifier (shown in tooltip) */
  source?: string;
  /** Optional className for styling */
  className?: string;
}

/**
 * Badge configuration by trust level
 */
const BADGE_CONFIG: Record<
  TrustLevel,
  {
    label: string;
    icon: typeof ShieldCheck | typeof Shield | null;
    variant: 'default' | 'secondary' | 'outline';
    className: string;
    tooltip: string;
  }
> = {
  official: {
    label: 'Official',
    icon: ShieldCheck,
    variant: 'outline',
    className: 'border-blue-500 text-blue-700 bg-blue-50 dark:bg-blue-950',
    tooltip: 'Official artifact from trusted source',
  },
  verified: {
    label: 'Verified',
    icon: ShieldCheck,
    variant: 'outline',
    className: 'border-green-500 text-green-700 bg-green-50 dark:bg-green-950',
    tooltip: 'Community verified artifact',
  },
  community: {
    label: 'Community',
    icon: Shield,
    variant: 'outline',
    className: 'border-gray-400 text-gray-600 bg-gray-50 dark:bg-gray-900',
    tooltip: 'Community contributed artifact',
  },
};

/**
 * TrustBadges - Display trust level badge with tooltip
 *
 * @example
 * ```tsx
 * <TrustBadges
 *   trustLevel="official"
 *   source="anthropics/skills/canvas-design"
 * />
 * ```
 */
export function TrustBadges({ trustLevel, source, className }: TrustBadgesProps) {
  const config = BADGE_CONFIG[trustLevel];
  const Icon = config.icon;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant={config.variant}
            className={cn('gap-1 text-xs', config.className, className)}
            aria-label={config.tooltip}
          >
            {Icon && <Icon className="h-3 w-3" />}
            {config.label}
          </Badge>
        </TooltipTrigger>
        <TooltipContent>
          <div className="space-y-1">
            <p>{config.tooltip}</p>
            {source && (
              <p className="text-xs text-muted-foreground">Source: {source}</p>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

/**
 * Determine trust level from artifact source string
 *
 * Official sources:
 * - Contains 'anthropic/' or 'anthropics/' (case insensitive)
 * - Starts with 'claude-' (case insensitive)
 *
 * Verified sources:
 * - Starts with 'verified/' or 'trusted-' (case insensitive)
 *
 * Community sources:
 * - All other sources
 *
 * @param source - Source URL or identifier
 * @returns Trust level
 *
 * @example
 * ```tsx
 * getTrustLevelFromSource('anthropics/skills/canvas') // 'official'
 * getTrustLevelFromSource('verified/user/repo') // 'verified'
 * getTrustLevelFromSource('user/repo/skill') // 'community'
 * ```
 */
export function getTrustLevelFromSource(source: string): TrustLevel {
  const lowerSource = source.toLowerCase();

  // Official sources
  const officialPatterns = ['anthropic/', 'anthropics/', 'claude-'];
  if (officialPatterns.some((pattern) => lowerSource.includes(pattern))) {
    return 'official';
  }

  // Verified sources
  const verifiedPrefixes = ['verified/', 'trusted-'];
  if (verifiedPrefixes.some((prefix) => lowerSource.startsWith(prefix))) {
    return 'verified';
  }

  // Community (default)
  return 'community';
}
