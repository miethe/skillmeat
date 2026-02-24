/**
 * DeploymentSetMemberCard Component
 *
 * Read-only card for displaying a single member within a deployment set.
 * Borrows the type-colored left border visual language from ArtifactBrowseCard
 * but strips all action buttons — this card is purely informational/navigational.
 *
 * Supports three member types:
 *   - artifact: Full card with icon, name, description, and tags
 *   - group:    Summary card with member count
 *   - set:      Summary card with nested set info
 */

'use client';

import * as React from 'react';
import * as LucideIcons from 'lucide-react';
import { Box, Users, Layers3 } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { Artifact, ArtifactType } from '@/types/artifact';
import { getArtifactTypeConfig } from '@/types/artifact';
import type { DeploymentSetMember, DeploymentSetMemberType } from '@/types/deployment-sets';

// =============================================================================
// Visual constants (mirrored from ArtifactBrowseCard for style consistency)
// =============================================================================

/** Left border accent colors keyed by artifact type */
const ARTIFACT_TYPE_BORDER: Record<ArtifactType, string> = {
  skill: 'border-l-purple-500',
  command: 'border-l-blue-500',
  agent: 'border-l-green-500',
  mcp: 'border-l-orange-500',
  hook: 'border-l-pink-500',
  composite: 'border-l-indigo-500',
};

/** Subtle background tints per artifact type */
const ARTIFACT_TYPE_TINT: Record<ArtifactType, string> = {
  skill: 'bg-purple-500/[0.02] dark:bg-purple-500/[0.03]',
  command: 'bg-blue-500/[0.02] dark:bg-blue-500/[0.03]',
  agent: 'bg-green-500/[0.02] dark:bg-green-500/[0.03]',
  mcp: 'bg-orange-500/[0.02] dark:bg-orange-500/[0.03]',
  hook: 'bg-pink-500/[0.02] dark:bg-pink-500/[0.03]',
  composite: 'bg-indigo-500/[0.02] dark:bg-indigo-500/[0.03]',
};

/** Member-type-level border accent when no artifact type is available */
const MEMBER_TYPE_BORDER: Record<DeploymentSetMemberType, string> = {
  artifact: 'border-l-blue-400',
  group: 'border-l-green-400',
  set: 'border-l-purple-400',
};

/** Human-readable label for each member type */
const MEMBER_TYPE_LABEL: Record<DeploymentSetMemberType, string> = {
  artifact: 'Artifact',
  group: 'Group',
  set: 'Set',
};

/** Badge styling per member type */
const MEMBER_TYPE_BADGE_CLASS: Record<DeploymentSetMemberType, string> = {
  artifact:
    'bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800',
  group:
    'bg-green-100 text-green-700 border-green-200 dark:bg-green-950 dark:text-green-300 dark:border-green-800',
  set: 'bg-purple-100 text-purple-700 border-purple-200 dark:bg-purple-950 dark:text-purple-300 dark:border-purple-800',
};

/** Icon per member type (fallback when no artifact config is available) */
const MEMBER_TYPE_ICON: Record<DeploymentSetMemberType, React.ElementType> = {
  artifact: Box,
  group: Users,
  set: Layers3,
};

// =============================================================================
// Props
// =============================================================================

export interface DeploymentSetMemberCardProps {
  /** The raw deployment set member record */
  member: DeploymentSetMember;
  /**
   * Fully resolved Artifact for members whose member_type === 'artifact'.
   * When provided, enables the rich artifact card layout (icon, description, tags).
   * When absent, falls back to the simplified summary layout.
   */
  resolvedArtifact?: Artifact;
  /** 1-based display position shown as "#N" badge in the top-left corner */
  position: number;
  /** Optional click handler — when provided the card becomes interactive */
  onClick?: () => void;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Sub-components
// =============================================================================

/** Position pill badge rendered in the card's top-left corner */
function PositionBadge({ position }: { position: number }) {
  return (
    <span
      className="flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-muted px-1.5 text-[10px] font-semibold tabular-nums text-muted-foreground"
      aria-label={`Position ${position}`}
    >
      #{position}
    </span>
  );
}

/** Member-type badge rendered in the card's top-right corner */
function MemberTypeBadge({ type }: { type: DeploymentSetMemberType }) {
  return (
    <Badge
      variant="outline"
      className={cn('shrink-0 text-[10px] font-medium', MEMBER_TYPE_BADGE_CLASS[type])}
    >
      {MEMBER_TYPE_LABEL[type]}
    </Badge>
  );
}

// =============================================================================
// Layout: Artifact card (rich)
// =============================================================================

function ArtifactMemberCardContent({
  member,
  artifact,
  position,
}: {
  member: DeploymentSetMember;
  artifact: Artifact;
  position: number;
}) {
  const config = getArtifactTypeConfig(artifact.type);
  const iconName = config?.icon ?? 'FileText';
  const IconComponent = (
    LucideIcons as unknown as Record<string, React.ComponentType<{ className?: string }>>
  )[iconName];
  const Icon = IconComponent ?? LucideIcons.FileText;

  const displayTags = (artifact.tags ?? []).slice(0, 3);
  const remainingTagCount = (artifact.tags?.length ?? 0) - displayTags.length;

  return (
    <>
      {/* Header */}
      <div className="p-4 pb-3">
        <div className="flex items-start justify-between gap-2">
          {/* Left: position + icon + name */}
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <PositionBadge position={position} />

            {/* Type icon */}
            <div className="flex-shrink-0 rounded-md border bg-background p-2">
              <Icon
                className={cn('h-4 w-4', config?.color ?? 'text-muted-foreground')}
                aria-hidden="true"
              />
            </div>

            {/* Name */}
            <div className="min-w-0 flex-1">
              <h3
                className="truncate text-sm font-semibold leading-tight"
                title={artifact.name}
              >
                {artifact.name}
              </h3>
              {artifact.author && (
                <p
                  className="truncate text-xs text-muted-foreground"
                  title={artifact.author}
                >
                  {artifact.author}
                </p>
              )}
            </div>
          </div>

          {/* Right: member type badge */}
          <MemberTypeBadge type={member.member_type} />
        </div>
      </div>

      {/* Description */}
      <div className="px-4 pb-3">
        <p className="line-clamp-2 text-xs text-muted-foreground">
          {artifact.description ?? 'No description available.'}
        </p>
      </div>

      {/* Tags */}
      {(displayTags.length > 0 || remainingTagCount > 0) && (
        <div
          className="flex flex-wrap items-center gap-1 px-4 pb-4"
          role="list"
          aria-label="Tags"
        >
          {displayTags.map((tag) => (
            <Badge
              key={tag}
              variant="secondary"
              className="text-[10px] font-normal"
              role="listitem"
            >
              {tag}
            </Badge>
          ))}
          {remainingTagCount > 0 && (
            <Badge
              variant="secondary"
              className="text-[10px] font-normal"
              aria-label={`${remainingTagCount} more tags`}
            >
              +{remainingTagCount} more
            </Badge>
          )}
        </div>
      )}
    </>
  );
}

// =============================================================================
// Layout: Group / Set card (simplified summary)
// =============================================================================

function SummaryMemberCardContent({
  member,
  position,
}: {
  member: DeploymentSetMember;
  position: number;
}) {
  const MemberIcon = MEMBER_TYPE_ICON[member.member_type];

  // Build a sensible display name from the raw IDs we have
  const displayId =
    member.member_type === 'group'
      ? (member.group_id ?? member.id)
      : member.member_type === 'set'
        ? (member.nested_set_id ?? member.id)
        : member.id;

  return (
    <div className="flex items-center gap-3 p-4">
      {/* Position badge */}
      <PositionBadge position={position} />

      {/* Type icon */}
      <div className="flex-shrink-0 rounded-md border bg-background p-2">
        <MemberIcon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
      </div>

      {/* ID / name */}
      <div className="min-w-0 flex-1">
        <p
          className="truncate font-mono text-xs text-muted-foreground"
          title={displayId}
        >
          {displayId}
        </p>
      </div>

      {/* Member type badge */}
      <MemberTypeBadge type={member.member_type} />
    </div>
  );
}

// =============================================================================
// Public component
// =============================================================================

/**
 * DeploymentSetMemberCard
 *
 * Renders a read-only card representing one member of a deployment set.
 *
 * When `resolvedArtifact` is provided and the member type is 'artifact', a
 * rich card is shown (type-colored border, icon, name, description, tags)
 * borrowing the visual language of `ArtifactBrowseCard`.
 *
 * For group/set members — or artifact members whose full data has not yet been
 * resolved — a compact summary card is rendered instead.
 *
 * @example
 * ```tsx
 * <DeploymentSetMemberCard
 *   member={member}
 *   resolvedArtifact={artifactMap[member.artifact_uuid ?? '']}
 *   position={index + 1}
 *   onClick={() => openArtifactModal(member.artifact_uuid)}
 * />
 * ```
 */
export function DeploymentSetMemberCard({
  member,
  resolvedArtifact,
  position,
  onClick,
  className,
}: DeploymentSetMemberCardProps) {
  const isArtifactWithData =
    member.member_type === 'artifact' && resolvedArtifact !== undefined;

  // Determine visual accent from resolved artifact type, falling back to member type
  const borderClass = isArtifactWithData
    ? ARTIFACT_TYPE_BORDER[resolvedArtifact.type]
    : MEMBER_TYPE_BORDER[member.member_type];

  const tintClass = isArtifactWithData
    ? ARTIFACT_TYPE_TINT[resolvedArtifact.type]
    : '';

  // Interaction handlers (only wired when onClick is provided)
  const handleClick = onClick
    ? (e: React.MouseEvent) => {
        const target = e.target as HTMLElement;
        // Allow inner interactive elements (badges, links) to handle their own clicks
        if (target.closest('a') || target.closest('button')) return;
        onClick();
      }
    : undefined;

  const handleKeyDown = onClick
    ? (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }
    : undefined;

  // Build accessible label
  const ariaLabel = isArtifactWithData
    ? `${resolvedArtifact.name}, ${resolvedArtifact.type} artifact, position ${position}`
    : `${MEMBER_TYPE_LABEL[member.member_type]} member, position ${position}`;

  return (
    <Card
      className={cn(
        'border-l-4 transition-all',
        borderClass,
        tintClass,
        onClick &&
          'cursor-pointer hover:border-primary/50 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
        className,
      )}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      aria-label={ariaLabel}
    >
      {isArtifactWithData ? (
        <ArtifactMemberCardContent
          member={member}
          artifact={resolvedArtifact}
          position={position}
        />
      ) : (
        <SummaryMemberCardContent member={member} position={position} />
      )}
    </Card>
  );
}

// =============================================================================
// Skeleton loader
// =============================================================================

/**
 * DeploymentSetMemberCardSkeleton
 *
 * Loading placeholder that matches the dimensions of a rich artifact card.
 */
export function DeploymentSetMemberCardSkeleton({ className }: { className?: string }) {
  return (
    <Card
      className={cn('border-l-4', className)}
      aria-busy="true"
      aria-label="Loading member card"
    >
      <div className="p-4 pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex flex-1 items-center gap-3">
            {/* Position skeleton */}
            <div className="h-5 w-7 animate-pulse rounded-full bg-muted" aria-hidden="true" />
            {/* Icon skeleton */}
            <div className="h-8 w-8 animate-pulse rounded-md bg-muted" aria-hidden="true" />
            {/* Name skeleton */}
            <div className="flex-1 space-y-1.5">
              <div className="h-3.5 w-28 animate-pulse rounded bg-muted" aria-hidden="true" />
              <div className="h-3 w-20 animate-pulse rounded bg-muted" aria-hidden="true" />
            </div>
          </div>
          {/* Type badge skeleton */}
          <div className="h-5 w-14 animate-pulse rounded-full bg-muted" aria-hidden="true" />
        </div>
      </div>

      {/* Description skeleton */}
      <div className="space-y-1.5 px-4 pb-3">
        <div className="h-3 w-full animate-pulse rounded bg-muted" aria-hidden="true" />
        <div className="h-3 w-3/4 animate-pulse rounded bg-muted" aria-hidden="true" />
      </div>

      {/* Tags skeleton */}
      <div className="flex gap-1 px-4 pb-4">
        <div className="h-4 w-12 animate-pulse rounded-full bg-muted" aria-hidden="true" />
        <div className="h-4 w-14 animate-pulse rounded-full bg-muted" aria-hidden="true" />
      </div>
    </Card>
  );
}
