'use client';

import * as React from 'react';
import { CheckCircle2, FolderOpen, Layers, Layers3 } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { COLOR_TAILWIND_CLASSES } from '@/lib/group-constants';
import { useDeploymentSetMembers } from '@/hooks';
import type { DeploymentSet, DeploymentSetMember, DeploymentSetMemberType } from '@/types/deployment-sets';

// =============================================================================
// Utilities (re-exported from deployment-set-card.tsx)
// =============================================================================

/**
 * Normalize a color value (token name or hex) to a valid hex string,
 * returning null when the input is not a valid hex.
 */
export function normalizeHexColor(value: string): string | null {
  const hex = value.trim().replace(/^#/, '').toLowerCase();
  if (/^[0-9a-f]{3}$/.test(hex)) {
    return `#${hex
      .split('')
      .map((part) => `${part}${part}`)
      .join('')}`;
  }
  if (/^[0-9a-f]{6}$/.test(hex)) {
    return `#${hex}`;
  }
  return null;
}

// =============================================================================
// Constants
// =============================================================================

/** Fallback left border when no color is set */
const FALLBACK_BORDER_CLASS = 'border-l-purple-500';

/** Member type icon components for tooltip member list */
const MEMBER_TYPE_ICON: Record<DeploymentSetMemberType, React.ElementType> = {
  artifact: Layers,
  group: FolderOpen,
  set: Layers3,
};

// =============================================================================
// Props
// =============================================================================

export interface MiniDeploymentSetCardProps {
  /** The deployment set to display */
  set: DeploymentSet;
  /** Click handler */
  onClick?: () => void;
  /** When true, shows "Already Selected" overlay and disables interaction */
  disabled?: boolean;
  /** When true, shows an emerald selection checkmark overlay */
  selected?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** 1-based position badge shown at the bottom of the card */
  position?: number;
}

// =============================================================================
// Internal sub-components
// =============================================================================

/** Tooltip content listing set members */
function MemberListTooltip({ setId, setName }: { setId: string; setName: string }) {
  const { data: members, isLoading } = useDeploymentSetMembers(setId);

  const MAX_SHOWN = 8;
  const shown = members?.slice(0, MAX_SHOWN) ?? [];
  const overflow = (members?.length ?? 0) - MAX_SHOWN;

  return (
    <div className="min-w-[160px] max-w-[240px] space-y-1.5 p-0.5">
      <p className="font-semibold leading-tight">{setName}</p>
      {isLoading ? (
        <p className="text-xs text-muted-foreground">Loading members...</p>
      ) : !members || members.length === 0 ? (
        <p className="text-xs text-muted-foreground">No members yet</p>
      ) : (
        <>
          <ul className="space-y-0.5" aria-label="Members">
            {shown.map((member) => (
              <MemberListItem key={member.id} member={member} />
            ))}
          </ul>
          {overflow > 0 && (
            <p className="text-xs text-muted-foreground">+{overflow} more</p>
          )}
        </>
      )}
    </div>
  );
}

/** Single member row inside the tooltip */
function MemberListItem({ member }: { member: DeploymentSetMember }) {
  const Icon = MEMBER_TYPE_ICON[member.member_type];

  let label: string;
  if (member.member_type === 'artifact') {
    label = member.artifact_uuid ?? member.id;
    // If we have an artifact type, try to get its config for the icon
  } else if (member.member_type === 'group') {
    label = member.group_id ?? member.id;
  } else {
    label = member.nested_set_id ?? member.id;
  }

  return (
    <li className="flex items-center gap-1.5 text-xs">
      <Icon className="h-3 w-3 shrink-0 text-muted-foreground" aria-hidden="true" />
      <span className="truncate text-muted-foreground">{label}</span>
    </li>
  );
}

// =============================================================================
// MiniDeploymentSetCard
// =============================================================================

/**
 * MiniDeploymentSetCard — Compact vertical card for deployment sets in grid layouts.
 *
 * Used in the AddMemberDialog (Sets tab) and in the Members tab of the
 * deployment set detail view. Matches MiniArtifactCard dimensions.
 *
 * @example
 * ```tsx
 * <MiniDeploymentSetCard
 *   set={deploymentSet}
 *   onClick={() => handleSelect(deploymentSet)}
 *   selected={selectedIds.has(deploymentSet.id)}
 * />
 * ```
 */
export function MiniDeploymentSetCard({
  set,
  onClick,
  disabled = false,
  selected = false,
  className,
  position,
}: MiniDeploymentSetCardProps) {
  // ── Color resolution ───────────────────────────────────────────────────────
  const isTokenColor = set.color && !set.color.startsWith('#');
  const customHex = set.color ? normalizeHexColor(set.color) : null;
  const borderColorClass = customHex
    ? 'border-l-border'
    : isTokenColor
      ? (COLOR_TAILWIND_CLASSES[set.color!] ?? FALLBACK_BORDER_CLASS)
      : FALLBACK_BORDER_CLASS;
  const borderColorStyle: React.CSSProperties = customHex
    ? { borderLeftColor: customHex }
    : {};

  // Color dot for the indicator
  const colorDotStyle: React.CSSProperties = {
    backgroundColor: customHex
      ? customHex
      : isTokenColor
        ? undefined
        : '#a855f7', // purple-500 fallback
  };
  const colorDotClass = isTokenColor
    ? (COLOR_TAILWIND_CLASSES[set.color!]?.replace('border-l-', 'bg-') ?? 'bg-purple-500')
    : '';

  // ── Tag display ────────────────────────────────────────────────────────────
  const displayTags = (set.tags ?? []).slice(0, 2);
  const remainingTagCount = (set.tags?.length ?? 0) - displayTags.length;

  // ── Interaction handlers ───────────────────────────────────────────────────
  const handleClick = (e: React.MouseEvent) => {
    if (disabled) return;
    const target = e.target as HTMLElement;
    if (target.closest('button')) return;
    onClick?.();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (disabled) return;
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick?.();
    }
  };

  const card = (
    <Card
      className={cn(
        'relative flex w-full min-h-[140px] flex-col rounded-lg border border-l-[3px] p-3',
        'bg-purple-500/[0.02] dark:bg-purple-500/[0.03]',
        'shadow-sm transition-all',
        !disabled && onClick && [
          'cursor-pointer',
          'hover:shadow-md hover:border-purple-400/50',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1',
        ],
        disabled && 'opacity-50 cursor-not-allowed pointer-events-none',
        selected && 'ring-2 ring-emerald-500 ring-offset-1',
        borderColorClass,
        className,
      )}
      style={{ ...borderColorStyle }}
      onClick={!disabled ? handleClick : undefined}
      onKeyDown={!disabled ? handleKeyDown : undefined}
      role={onClick && !disabled ? 'button' : undefined}
      tabIndex={onClick && !disabled ? 0 : undefined}
      aria-label={`${set.name} deployment set, ${set.member_count} ${set.member_count === 1 ? 'member' : 'members'}`}
      aria-disabled={disabled || undefined}
    >
      {/* Header row: icon + name + member count badge */}
      <div className="flex items-center gap-1.5">
        {set.icon ? (
          <span className="shrink-0 text-sm leading-none" aria-hidden="true">
            {set.icon}
          </span>
        ) : (
          <Layers3
            className="h-4 w-4 shrink-0 text-purple-500/70"
            aria-hidden="true"
          />
        )}
        <span
          className="truncate text-sm font-medium leading-tight flex-1"
          title={set.name}
        >
          {set.name}
        </span>
        <Badge
          variant="secondary"
          className="shrink-0 px-1.5 py-0 text-[10px] tabular-nums"
          aria-label={`${set.member_count} members`}
        >
          {set.member_count}
        </Badge>
      </div>

      {/* Color indicator dot */}
      <div className="mt-1.5 flex items-center gap-1.5">
        <span
          className={cn(
            'h-2 w-2 shrink-0 rounded-full border border-border/40',
            colorDotClass,
          )}
          style={!isTokenColor ? colorDotStyle : undefined}
          aria-hidden="true"
        />
        <span className="text-[10px] text-muted-foreground/60 uppercase tracking-wide">
          set
        </span>
      </div>

      {/* Description zone */}
      <div className="mt-1 h-[28px]">
        {set.description ? (
          <p
            className="line-clamp-2 text-xs leading-[14px] text-muted-foreground"
            title={set.description}
          >
            {set.description}
          </p>
        ) : (
          <p className="text-xs leading-[14px] text-muted-foreground/60">
            {set.member_count} {set.member_count === 1 ? 'member' : 'members'}
          </p>
        )}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Tag badges */}
      {(displayTags.length > 0 || remainingTagCount > 0) && (
        <div
          className="mt-1 flex flex-wrap items-center gap-1"
          role="list"
          aria-label="Tags"
        >
          {displayTags.map((tag) => (
            <Badge
              key={tag}
              variant="secondary"
              className="px-1.5 py-0 text-[10px]"
              role="listitem"
            >
              {tag}
            </Badge>
          ))}
          {remainingTagCount > 0 && (
            <Badge
              variant="secondary"
              className="px-1.5 py-0 text-[10px]"
              aria-label={`${remainingTagCount} more tags`}
            >
              +{remainingTagCount}
            </Badge>
          )}
        </div>
      )}

      {/* Position badge */}
      {position !== undefined && (
        <div className="mt-1 flex items-center">
          <span
            className="flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-muted px-1 text-[9px] font-semibold tabular-nums text-muted-foreground"
            aria-label={`Position ${position}`}
          >
            #{position}
          </span>
        </div>
      )}

      {/* "Already Selected" overlay — shown when disabled */}
      {disabled && (
        <div
          className="absolute inset-0 flex items-center justify-center rounded-lg bg-background/60"
          aria-hidden="true"
        >
          <span className="rounded-md bg-muted/90 px-2 py-1 text-[10px] font-medium text-muted-foreground shadow-sm">
            Already Selected
          </span>
        </div>
      )}

      {/* Selection checkmark overlay — shown when selected */}
      {selected && (
        <div
          className="pointer-events-none absolute inset-0 flex items-start justify-end rounded-lg bg-emerald-500/10 p-1.5"
          aria-hidden="true"
        >
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500 shadow">
            <CheckCircle2 className="h-3.5 w-3.5 text-white" />
          </span>
        </div>
      )}
    </Card>
  );

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>{card}</TooltipTrigger>
        <TooltipContent side="top" align="start" className="p-2">
          <MemberListTooltip setId={set.id} setName={set.name} />
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// =============================================================================
// MiniDeploymentSetCardSkeleton
// =============================================================================

/**
 * MiniDeploymentSetCardSkeleton — Loading placeholder matching card dimensions.
 */
export function MiniDeploymentSetCardSkeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'flex w-full min-h-[140px] flex-col rounded-lg border border-l-[3px] border-l-muted p-3',
        className,
      )}
      aria-busy="true"
      aria-label="Loading deployment set card"
    >
      {/* Header row skeleton */}
      <div className="flex items-center gap-1.5">
        <Skeleton className="h-4 w-4 rounded shrink-0" aria-hidden="true" />
        <Skeleton className="h-4 flex-1 rounded" aria-hidden="true" />
        <Skeleton className="h-4 w-6 rounded-full shrink-0" aria-hidden="true" />
      </div>

      {/* Color indicator skeleton */}
      <div className="mt-1.5 flex items-center gap-1.5">
        <Skeleton className="h-2 w-2 rounded-full shrink-0" aria-hidden="true" />
        <Skeleton className="h-2.5 w-6 rounded" aria-hidden="true" />
      </div>

      {/* Description skeleton */}
      <div className="mt-1 space-y-1">
        <Skeleton className="h-3 w-full rounded" aria-hidden="true" />
        <Skeleton className="h-3 w-2/3 rounded" aria-hidden="true" />
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Tags skeleton */}
      <div className="mt-1 flex gap-1">
        <Skeleton className="h-4 w-10 rounded-full" aria-hidden="true" />
        <Skeleton className="h-4 w-12 rounded-full" aria-hidden="true" />
      </div>
    </div>
  );
}
