'use client';

import * as React from 'react';
import { Layers, CheckCircle2 } from 'lucide-react';
import * as LucideIcons from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { Group } from '@/types/groups';
import { getArtifactTypeConfig } from '@/types/artifact';
import type { ArtifactType } from '@/types/artifact';
import { useGroupArtifacts } from '@/hooks';
import { ICON_MAP, COLOR_TAILWIND_CLASSES } from '@/lib/group-constants';

// =============================================================================
// Constants
// =============================================================================

const MAX_TOOLTIP_ITEMS = 8;

// =============================================================================
// Helpers
// =============================================================================

function normalizeHexColor(value: string): string | null {
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
// Types
// =============================================================================

export interface MiniGroupCardProps {
  group: Group;
  onClick?: () => void;
  disabled?: boolean;
  selected?: boolean;
  className?: string;
  position?: number;
}

// =============================================================================
// Tooltip content
// =============================================================================

function GroupMemberTooltipContent({ groupId }: { groupId: string }) {
  const { data: artifacts, isLoading } = useGroupArtifacts(groupId);

  if (isLoading) {
    return (
      <p className="text-xs text-muted-foreground">Loading members...</p>
    );
  }

  if (!artifacts || artifacts.length === 0) {
    return <p className="text-xs text-muted-foreground italic">No artifacts</p>;
  }

  const visible = artifacts.slice(0, MAX_TOOLTIP_ITEMS);
  const overflow = artifacts.length - visible.length;

  return (
    <ul className="flex flex-col gap-1" role="list">
      {visible.map((a) => {
        // artifact_id is "type:name" — extract the type prefix if present
        const artifactType = a.artifact_id?.split(':')[0] as ArtifactType | undefined;
        const config = artifactType ? getArtifactTypeConfig(artifactType) : undefined;
        const iconName = config?.icon ?? 'FileText';
        const IconComponent = (
          LucideIcons as unknown as Record<string, React.ComponentType<{ className?: string }>>
        )[iconName];
        const Icon = IconComponent ?? LucideIcons.FileText;
        const displayName = a.artifact_id?.split(':')[1] ?? a.artifact_uuid;

        return (
          <li key={a.artifact_uuid} className="flex items-center gap-1.5" role="listitem">
            <Icon
              className={cn('h-3 w-3 shrink-0', config?.color ?? 'text-muted-foreground')}
              aria-hidden="true"
            />
            <span className="truncate text-xs">{displayName}</span>
          </li>
        );
      })}
      {overflow > 0 && (
        <li className="text-[10px] text-muted-foreground" role="listitem">
          +{overflow} more
        </li>
      )}
    </ul>
  );
}

// =============================================================================
// MiniGroupCard
// =============================================================================

export function MiniGroupCard({
  group,
  onClick,
  disabled = false,
  selected = false,
  className,
  position,
}: MiniGroupCardProps) {
  const handleClick = (e: React.MouseEvent) => {
    if (disabled || !onClick) return;
    const target = e.target as HTMLElement;
    if (target.closest('button')) return;
    onClick();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (disabled || !onClick) return;
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick();
    }
  };

  const isInteractive = !!onClick && !disabled;

  // Resolve icon from group.icon token, falling back to Layers
  const GroupIcon = ICON_MAP[group.icon ?? 'layers'] ?? Layers;

  // Resolve border color: token → Tailwind class; hex → inline style; fallback → slate
  const tokenColorClass = COLOR_TAILWIND_CLASSES[group.color ?? 'slate'] ?? COLOR_TAILWIND_CLASSES.slate;
  const customColor = group.color ? normalizeHexColor(group.color) : null;
  const borderColorClass = customColor ? 'border-l-border' : tokenColorClass;

  const card = (
    <Card
      className={cn(
        'relative flex w-full min-h-[140px] flex-col rounded-lg border border-l-[3px]',
        borderColorClass,
        'bg-muted/[0.03] p-3',
        'shadow-sm transition-all',
        isInteractive && 'cursor-pointer hover:shadow-md',
        isInteractive && 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1',
        selected && 'ring-2 ring-emerald-500 ring-offset-1',
        disabled && 'opacity-50 cursor-not-allowed pointer-events-none',
        className
      )}
      style={customColor ? { borderLeftColor: customColor } : undefined}
      onClick={isInteractive ? handleClick : undefined}
      onKeyDown={isInteractive ? handleKeyDown : undefined}
      role={isInteractive ? 'button' : undefined}
      tabIndex={isInteractive ? 0 : undefined}
      aria-label={`${group.name}, group with ${group.artifact_count} artifacts`}
      aria-disabled={disabled || undefined}
    >
      {/* Header row: icon + name + count badge */}
      <div className="flex items-center gap-1.5">
        <GroupIcon
          className="h-4 w-4 shrink-0 text-muted-foreground"
          aria-hidden="true"
        />
        <span
          className="truncate text-sm font-medium leading-tight flex-1"
          title={group.name}
        >
          {group.name}
        </span>
        <Badge
          variant="secondary"
          className="shrink-0 px-1.5 py-0 text-[10px] tabular-nums"
          aria-label={`${group.artifact_count} artifacts`}
        >
          {group.artifact_count}
        </Badge>
      </div>

      {/* Description zone - fixed height, 2-line clamp */}
      <div className="mt-1 h-[28px]">
        {group.description ? (
          <p
            className="line-clamp-2 text-xs leading-[14px] text-muted-foreground"
            title={group.description}
          >
            {group.description}
          </p>
        ) : (
          <p className="text-xs italic text-muted-foreground/60">
            {group.artifact_count} {group.artifact_count === 1 ? 'artifact' : 'artifacts'}
          </p>
        )}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Position badge (optional) */}
      {position !== undefined && (
        <div className="mt-1 flex">
          <span
            className="flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-muted px-1.5 text-[10px] font-semibold tabular-nums text-muted-foreground"
            aria-label={`Position ${position}`}
          >
            #{position}
          </span>
        </div>
      )}

      {/* Disabled overlay */}
      {disabled && (
        <div
          className="pointer-events-none absolute inset-0 flex items-center justify-center rounded-lg bg-background/50"
          aria-hidden="true"
        >
          <span className="rounded bg-background/80 px-2 py-0.5 text-xs font-medium text-muted-foreground shadow-sm">
            Already Selected
          </span>
        </div>
      )}

      {/* Selected checkmark overlay */}
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
        <TooltipContent
          side="top"
          className="max-w-[200px]"
        >
          <p className="mb-1.5 font-semibold">{group.name}</p>
          <GroupMemberTooltipContent groupId={group.id} />
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

MiniGroupCard.displayName = 'MiniGroupCard';

// =============================================================================
// Skeleton
// =============================================================================

export function MiniGroupCardSkeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'flex min-h-[140px] flex-col rounded-lg border border-l-[3px] border-l-border/30 p-3',
        'bg-muted/[0.02]',
        className
      )}
      aria-busy="true"
      aria-label="Loading group card"
    >
      {/* Header row skeleton */}
      <div className="flex items-center gap-1.5">
        <Skeleton className="h-4 w-4 rounded shrink-0" aria-hidden="true" />
        <Skeleton className="h-4 flex-1 rounded" aria-hidden="true" />
        <Skeleton className="h-4 w-6 rounded-full shrink-0" aria-hidden="true" />
      </div>

      {/* Description skeleton */}
      <div className="mt-1 space-y-1">
        <Skeleton className="h-3 w-full rounded" aria-hidden="true" />
        <Skeleton className="h-3 w-2/3 rounded" aria-hidden="true" />
      </div>

      <div className="flex-1" />
    </div>
  );
}
