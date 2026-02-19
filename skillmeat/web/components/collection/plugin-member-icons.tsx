/**
 * PluginMemberIcons Component
 *
 * Displays a compact row of Lucide icons representing the artifact types
 * that belong to a plugin (composite). Shows up to 5 icons and collapses
 * additional members into a "+N" overflow badge.
 *
 * Used in plugin cards, plugin detail headers, and any surface that needs
 * a quick visual summary of what types a plugin bundles.
 *
 * Accessibility: WCAG 2.1 AA compliant.
 *   - Each icon has aria-hidden="true"; meaning is conveyed via sr-only text
 *   - The container has role="list" with an aria-label describing contents
 *   - Overflow badge uses aria-label with full count context
 *   - Optional tooltip shows the complete type breakdown on hover
 *
 * @example
 * ```tsx
 * // From an array of ArtifactType strings
 * <PluginMemberIcons memberTypes={['skill', 'skill', 'command', 'agent']} />
 *
 * // From member objects (e.g., composite members from API)
 * <PluginMemberIcons memberTypes={members.map(m => m.type)} size="lg" />
 *
 * // Without tooltip
 * <PluginMemberIcons memberTypes={types} showTooltip={false} />
 * ```
 */

'use client';

import * as React from 'react';
import * as LucideIcons from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { ArtifactType } from '@/types/artifact';
import { ARTIFACT_TYPES } from '@/types/artifact';

// ============================================================================
// Types
// ============================================================================

export interface PluginMemberIconsProps {
  /**
   * Array of artifact types representing the plugin's members.
   * Duplicate types are counted and shown once in the type breakdown.
   * The order determines which icons render first (left to right).
   */
  memberTypes: ArtifactType[];

  /**
   * Icon size variant.
   * - sm: 16px — tight inline contexts (card footers, compact lists)
   * - md: 20px — default; card headers, summary rows
   * - lg: 24px — detail views, headers
   * @default 'md'
   */
  size?: 'sm' | 'md' | 'lg';

  /**
   * Maximum number of icons to show before the overflow "+N" badge.
   * Additional member types beyond this limit are summarised in the badge.
   * @default 5
   */
  maxVisible?: number;

  /**
   * Whether to show a tooltip on hover with the full type breakdown.
   * @default true
   */
  showTooltip?: boolean;

  /** Additional CSS classes for the outer container */
  className?: string;
}

// ============================================================================
// Constants
// ============================================================================

/** Icon dimension classes keyed by size variant */
const ICON_SIZE_CLASSES: Record<NonNullable<PluginMemberIconsProps['size']>, string> = {
  sm: 'h-4 w-4',
  md: 'h-5 w-5',
  lg: 'h-6 w-6',
};

/** Container padding/gap keyed by size variant — keeps row tight at sm */
const GAP_CLASSES: Record<NonNullable<PluginMemberIconsProps['size']>, string> = {
  sm: 'gap-0.5',
  md: 'gap-1',
  lg: 'gap-1.5',
};

/** Icon wrapper size keyed by size variant (touch target / background pill) */
const WRAPPER_CLASSES: Record<NonNullable<PluginMemberIconsProps['size']>, string> = {
  sm: 'h-5 w-5',
  md: 'h-6 w-6',
  lg: 'h-7 w-7',
};

// ============================================================================
// Helpers
// ============================================================================

/**
 * Build a deduplicated, ordered list of unique types from the member array,
 * preserving first-occurrence order. Returns the count for each unique type
 * so the tooltip can show "3 skills, 2 commands" etc.
 */
function buildTypeCountMap(memberTypes: ArtifactType[]): Map<ArtifactType, number> {
  const map = new Map<ArtifactType, number>();
  for (const type of memberTypes) {
    map.set(type, (map.get(type) ?? 0) + 1);
  }
  return map;
}

/**
 * Build a human-readable ARIA label summarising the member types.
 * E.g. "Plugin contains 3 skills, 2 commands, 1 agent"
 */
function buildAriaLabel(typeCountMap: Map<ArtifactType, number>): string {
  if (typeCountMap.size === 0) return 'Plugin has no members';

  const parts: string[] = [];
  for (const [type, count] of typeCountMap) {
    const config = ARTIFACT_TYPES[type];
    const label = count === 1 ? config?.label ?? type : config?.pluralLabel ?? `${type}s`;
    parts.push(`${count} ${label.toLowerCase()}`);
  }

  return `Plugin contains ${parts.join(', ')}`;
}

// ============================================================================
// Sub-components
// ============================================================================

interface MemberIconProps {
  type: ArtifactType;
  iconSizeClass: string;
  wrapperClass: string;
}

/**
 * Single member icon with background pill, type color, and screen-reader label.
 */
function MemberIcon({ type, iconSizeClass, wrapperClass }: MemberIconProps) {
  const config = ARTIFACT_TYPES[type];
  const iconName = config?.icon ?? 'FileText';
  const IconComponent = (
    LucideIcons as unknown as Record<string, React.ComponentType<{ className?: string }>>
  )[iconName];
  const Icon = IconComponent ?? LucideIcons.FileText;
  const colorClass = config?.color ?? 'text-muted-foreground';
  const typeLabel = config?.label ?? type;

  return (
    <div
      className={cn(
        'flex flex-shrink-0 items-center justify-center rounded-md',
        'bg-background border border-border/60',
        wrapperClass
      )}
      role="listitem"
    >
      {/* Visible icon */}
      <Icon className={cn(iconSizeClass, colorClass)} aria-hidden="true" />
      {/* Screen-reader description */}
      <span className="sr-only">{typeLabel}</span>
    </div>
  );
}

interface OverflowBadgeProps {
  count: number;
  /** Types in the overflow, used for aria-label context */
  overflowTypes: ArtifactType[];
}

/**
 * Overflow indicator when there are more member types than maxVisible.
 */
function OverflowBadge({ count, overflowTypes }: OverflowBadgeProps) {
  const overflowLabels = overflowTypes
    .map((t) => ARTIFACT_TYPES[t]?.pluralLabel ?? `${t}s`)
    .join(', ');

  return (
    <div
      className={cn(
        'flex flex-shrink-0 items-center justify-center rounded-md',
        'bg-muted/70 border border-border/60 px-1',
        'text-[10px] font-medium leading-none text-muted-foreground'
      )}
      style={{ minWidth: '1.5rem', height: '1.5rem' }}
      role="listitem"
      aria-label={`${count} more member types: ${overflowLabels}`}
    >
      +{count}
    </div>
  );
}

// ============================================================================
// Tooltip content
// ============================================================================

interface MemberBreakdownTooltipProps {
  typeCountMap: Map<ArtifactType, number>;
  totalCount: number;
}

/**
 * Tooltip body listing each member type with its count and icon.
 */
function MemberBreakdownTooltip({ typeCountMap, totalCount }: MemberBreakdownTooltipProps) {
  return (
    <div className="space-y-1.5">
      <p className="text-xs font-semibold text-foreground">
        {totalCount} member{totalCount !== 1 ? 's' : ''}
      </p>
      <ul className="space-y-1">
        {Array.from(typeCountMap.entries()).map(([type, count]) => {
          const config = ARTIFACT_TYPES[type];
          const iconName = config?.icon ?? 'FileText';
          const IconComponent = (
            LucideIcons as unknown as Record<string, React.ComponentType<{ className?: string }>>
          )[iconName];
          const Icon = IconComponent ?? LucideIcons.FileText;
          const colorClass = config?.color ?? 'text-muted-foreground';
          const label = count === 1 ? config?.label ?? type : config?.pluralLabel ?? `${type}s`;

          return (
            <li key={type} className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Icon className={cn('h-3.5 w-3.5 flex-shrink-0', colorClass)} aria-hidden="true" />
              <span>
                {count} {label.toLowerCase()}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * PluginMemberIcons — compact icon row summarising a plugin's member types.
 *
 * Renders up to `maxVisible` (default 5) unique member type icons in a horizontal
 * row. When there are more unique types, a "+N" badge replaces the extras.
 * An optional hover tooltip (default on) shows the full breakdown with counts.
 *
 * Note: Duplicate member types are deduplicated for icon display purposes;
 * the tooltip and ARIA label reflect the actual counts.
 *
 * @param memberTypes - Array of ArtifactType values (may contain duplicates)
 * @param size - Icon size variant: 'sm' | 'md' | 'lg' (default: 'md')
 * @param maxVisible - Max icon count before overflow badge (default: 5)
 * @param showTooltip - Whether to show breakdown tooltip on hover (default: true)
 * @param className - Additional CSS classes for the outer container
 */
export function PluginMemberIcons({
  memberTypes,
  size = 'md',
  maxVisible = 5,
  showTooltip = true,
  className,
}: PluginMemberIconsProps) {
  // Build unique-type count map (preserves first-occurrence order)
  const typeCountMap = React.useMemo(() => buildTypeCountMap(memberTypes), [memberTypes]);

  // Unique types in order
  const uniqueTypes = React.useMemo(() => Array.from(typeCountMap.keys()), [typeCountMap]);

  // Visible vs overflow split
  const visibleTypes = uniqueTypes.slice(0, maxVisible);
  const overflowTypes = uniqueTypes.slice(maxVisible);
  const overflowCount = overflowTypes.length;

  // Dimension classes
  const iconSizeClass = ICON_SIZE_CLASSES[size];
  const wrapperClass = WRAPPER_CLASSES[size];
  const gapClass = GAP_CLASSES[size];

  // ARIA label for the list
  const ariaLabel = React.useMemo(() => buildAriaLabel(typeCountMap), [typeCountMap]);

  // Nothing to render when there are no members
  if (uniqueTypes.length === 0) {
    return null;
  }

  const content = (
    <div
      className={cn('flex items-center', gapClass, className)}
      role="list"
      aria-label={ariaLabel}
    >
      {visibleTypes.map((type) => (
        <MemberIcon
          key={type}
          type={type}
          iconSizeClass={iconSizeClass}
          wrapperClass={wrapperClass}
        />
      ))}
      {overflowCount > 0 && (
        <OverflowBadge count={overflowCount} overflowTypes={overflowTypes} />
      )}
    </div>
  );

  if (!showTooltip) {
    return content;
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          {/* Wrap in a span so TooltipTrigger can attach its ref */}
          <span className="inline-flex">{content}</span>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-[200px]">
          <MemberBreakdownTooltip
            typeCountMap={typeCountMap}
            totalCount={memberTypes.length}
          />
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
