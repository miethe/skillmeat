/**
 * ArtifactBrowseCard Component
 *
 * Discovery-focused card for browsing artifacts in the collection view.
 * Emphasizes metadata, description, and discovery features rather than
 * operational status/sync indicators (those belong on /manage page).
 *
 * Visual hierarchy:
 * 1. Type icon + Name + Author
 * 2. Description (2-3 line clamp)
 * 3. Tags (max 3 + overflow count)
 * 4. Tools + Deployed badge + Score
 */

'use client';

import * as React from 'react';
import * as LucideIcons from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';
import type { Artifact, ArtifactType } from '@/types/artifact';
import { getArtifactTypeConfig } from '@/types/artifact';
import { Tool } from '@/types/enums';
import { ScoreBadge } from '@/components/ScoreBadge';
import { PlatformBadge } from '@/components/platform-badge';
import { ArtifactGroupBadges } from '@/components/collection/artifact-group-badges';
import { TagSelectorPopover } from '@/components/collection/tag-selector-popover';

/**
 * Props for ArtifactBrowseCard component
 */
export interface ArtifactBrowseCardProps {
  /** The artifact to display */
  artifact: Artifact;

  /** Click handler for opening detail modal */
  onClick: () => void;

  /** Handler for quick deploy action */
  onQuickDeploy?: () => void;

  /** Handler for adding artifact to a group */
  onAddToGroup?: () => void;

  /** Handler for viewing artifact details */
  onViewDetails?: () => void;

  /** Handler for deleting artifact */
  onDelete?: (artifact: Artifact) => void;

  /** Whether to show collection badge (All Collections view) */
  showCollectionBadge?: boolean;

  /** Handler when collection badge is clicked */
  onCollectionClick?: (collectionId: string) => void;

  /** Additional CSS classes */
  className?: string;
}

// Type-specific border accent colors for visual differentiation
const artifactTypeBorderAccents: Record<ArtifactType, string> = {
  skill: 'border-l-purple-500',
  command: 'border-l-blue-500',
  agent: 'border-l-green-500',
  mcp: 'border-l-orange-500',
  hook: 'border-l-pink-500',
};

// Subtle background tints per artifact type
const artifactTypeCardTints: Record<ArtifactType, string> = {
  skill: 'bg-purple-500/[0.02] dark:bg-purple-500/[0.03]',
  command: 'bg-blue-500/[0.02] dark:bg-blue-500/[0.03]',
  agent: 'bg-green-500/[0.02] dark:bg-green-500/[0.03]',
  mcp: 'bg-orange-500/[0.02] dark:bg-orange-500/[0.03]',
  hook: 'bg-pink-500/[0.02] dark:bg-pink-500/[0.03]',
};

// Known tool names from the Tool enum for matching against tags
const TOOL_NAMES = new Set(Object.values(Tool));

/**
 * Check if a tag represents a Claude Code tool
 */
function isToolTag(tag: string): boolean {
  return TOOL_NAMES.has(tag as Tool);
}

/**
 * Extract tools from artifact tags that match known Tool enum values
 */
function extractToolsFromTags(tags?: string[]): string[] {
  if (!tags) return [];
  return tags.filter(isToolTag);
}

/**
 * Extract non-tool tags for display
 */
function extractDisplayTags(tags?: string[]): string[] {
  if (!tags) return [];
  return tags.filter((tag) => !isToolTag(tag));
}

/**
 * ArtifactBrowseCard - Discovery-focused card for the /collection page
 *
 * Shows artifact metadata for exploration and learning. Unlike the
 * operations card on /manage, this focuses on description, tags, and
 * discovery features rather than sync status or health indicators.
 *
 * @example
 * ```tsx
 * <ArtifactBrowseCard
 *   artifact={artifact}
 *   onClick={() => openDetailModal(artifact)}
 *   onQuickDeploy={() => openDeployDialog(artifact)}
 *   onAddToGroup={() => openGroupPicker(artifact)}
 * />
 * ```
 */
export function ArtifactBrowseCard({
  artifact,
  onClick,
  onQuickDeploy,
  onAddToGroup,
  onViewDetails,
  onDelete,
  showCollectionBadge = false,
  onCollectionClick,
  className,
}: ArtifactBrowseCardProps) {
  const config = getArtifactTypeConfig(artifact.type);

  // Get the icon component from Lucide
  const iconName = config?.icon ?? 'FileText';
  const IconComponent = (
    LucideIcons as unknown as Record<string, React.ComponentType<{ className?: string }>>
  )[iconName];
  const Icon = IconComponent || LucideIcons.FileText;

  // Extract tools and display tags
  const tools = extractToolsFromTags(artifact.tags);
  const displayTags = extractDisplayTags(artifact.tags);
  const visibleTags = displayTags.slice(0, 3);
  const remainingTagsCount = displayTags.length - visibleTags.length;

  // Determine author/source display
  const authorDisplay = artifact.author || artifact.source?.split('/')[0] || 'Unknown';

  // Check deployment count
  const deploymentCount = artifact.deployments?.length ?? 0;
  const hasDeployments = deploymentCount > 0;

  // Handle card click, avoiding trigger when clicking action buttons
  const handleCardClick = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    // Ignore clicks on buttons or dropdown triggers
    if (target.closest('button') || target.closest('[role="menuitem"]')) {
      return;
    }
    onClick();
  };

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick();
    }
  };

  // Copy CLI command to clipboard
  const handleCopyCliCommand = async () => {
    const command = `skillmeat deploy ${artifact.id}`;
    try {
      await navigator.clipboard.writeText(command);
    } catch (err) {
      console.error('Failed to copy CLI command:', err);
    }
  };

  return (
    <Card
      className={cn(
        'cursor-pointer border-l-4 transition-all',
        'hover:border-primary/50 hover:shadow-md',
        'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
        artifactTypeBorderAccents[artifact.type],
        artifactTypeCardTints[artifact.type],
        className
      )}
      onClick={handleCardClick}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
      aria-label={`View details for ${artifact.name}, ${artifact.type} artifact by ${authorDisplay}`}
    >
      {/* Header: Icon, Name, Author, Quick Actions */}
      <div className="p-4 pb-3">
        <div className="flex items-start justify-between gap-2">
          {/* Left: Icon and Name */}
          <div className="flex min-w-0 flex-1 items-center gap-3">
            {/* Type Icon */}
            <div className="flex-shrink-0 rounded-md border bg-background p-2">
              <Icon
                className={cn('h-5 w-5', config?.color ?? 'text-muted-foreground')}
                aria-hidden="true"
              />
            </div>

            {/* Name and Author */}
            <div className="min-w-0 flex-1">
              <h3 className="truncate font-semibold leading-tight" title={artifact.name}>
                {artifact.name}
              </h3>
              <p className="truncate text-sm text-muted-foreground" title={authorDisplay}>
                {authorDisplay}
              </p>
            </div>
          </div>

          {/* Right: Quick Actions Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 flex-shrink-0"
                aria-label={`Quick actions for ${artifact.name}`}
                onClick={(e) => e.stopPropagation()}
              >
                <LucideIcons.MoreVertical className="h-4 w-4" aria-hidden="true" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem
                onClick={() => {
                  onViewDetails?.();
                }}
              >
                <LucideIcons.Eye className="mr-2 h-4 w-4" aria-hidden="true" />
                View Details
              </DropdownMenuItem>

              {onQuickDeploy && (
                <DropdownMenuItem onClick={() => onQuickDeploy()}>
                  <LucideIcons.Rocket className="mr-2 h-4 w-4" aria-hidden="true" />
                  Quick Deploy
                </DropdownMenuItem>
              )}

              {onAddToGroup && (
                <DropdownMenuItem onClick={() => onAddToGroup()}>
                  <LucideIcons.FolderPlus className="mr-2 h-4 w-4" aria-hidden="true" />
                  Add to Group
                </DropdownMenuItem>
              )}

              <DropdownMenuSeparator />

              <DropdownMenuItem onClick={handleCopyCliCommand}>
                <LucideIcons.Terminal className="mr-2 h-4 w-4" aria-hidden="true" />
                Copy CLI Command
              </DropdownMenuItem>

              {onDelete && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    className="text-destructive focus:text-destructive"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(artifact);
                    }}
                  >
                    <LucideIcons.Trash2 className="mr-2 h-4 w-4" aria-hidden="true" />
                    Delete Artifact
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* Collection Badge (when in All Collections view) */}
        {showCollectionBadge && artifact.collections && artifact.collections.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1" role="list" aria-label="Collections">
            {artifact.collections.slice(0, 2).map((collection) => (
              <Badge
                key={collection.id}
                variant="outline"
                className="cursor-pointer text-xs hover:bg-accent"
                onClick={(e) => {
                  e.stopPropagation();
                  onCollectionClick?.(collection.id);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    e.stopPropagation();
                    onCollectionClick?.(collection.id);
                  }
                }}
                role="button"
                tabIndex={0}
                aria-label={`View collection ${collection.name}`}
              >
                <LucideIcons.FolderOpen className="mr-1 h-3 w-3" aria-hidden="true" />
                {collection.name}
              </Badge>
            ))}
            {artifact.collections.length > 2 && (
              <Badge
                variant="outline"
                className="text-xs"
                aria-label={`${artifact.collections.length - 2} more collections`}
              >
                +{artifact.collections.length - 2}
              </Badge>
            )}
          </div>
        )}
      </div>

      {/* Description */}
      <div className="px-4 pb-3">
        <p className="line-clamp-2 text-sm text-muted-foreground">
          {artifact.description || 'No description available.'}
        </p>
      </div>

      {/* Tags */}
      <div
        className="flex min-h-[28px] flex-wrap items-center gap-1 px-4 pb-3"
        role="list"
        aria-label="Tags"
      >
        {visibleTags.map((tag) => (
          <Badge key={tag} variant="secondary" className="text-xs" role="listitem">
            {tag}
          </Badge>
        ))}
        {remainingTagsCount > 0 && (
          <Badge
            variant="secondary"
            className="text-xs"
            aria-label={`${remainingTagsCount} more tags`}
          >
            +{remainingTagsCount} more
          </Badge>
        )}
        <TagSelectorPopover
          artifactId={artifact.id}
          trigger={
            <Button
              variant="ghost"
              size="icon"
              className="h-5 w-5 rounded-full"
              aria-label="Add tags"
            >
              <LucideIcons.Plus className="h-3 w-3" />
            </Button>
          }
        />
      </div>

      {/* Target Platforms */}
      <div className="flex flex-wrap items-center gap-1 px-4 pb-3" aria-label="Target platforms">
        {artifact.targetPlatforms && artifact.targetPlatforms.length > 0 ? (
          artifact.targetPlatforms.map((platform) => (
            <PlatformBadge key={`${artifact.id}-${platform}`} platform={platform} compact />
          ))
        ) : (
          <Badge variant="outline" className="text-xs text-muted-foreground">
            Universal
          </Badge>
        )}
      </div>

      {/* Group badges */}
      <ArtifactGroupBadges
        artifactId={artifact.id}
        collectionId={artifact.collections?.[0]?.id}
        maxVisible={3}
        onAddToGroup={onAddToGroup}
        className="mt-auto px-3 pb-1"
      />

      {/* Footer: Tools, Deployed Badge, Score */}
      <div className="flex items-center justify-between border-t px-4 py-3">
        {/* Left: Tools */}
        <div className="flex flex-wrap items-center gap-1" role="list" aria-label="Tools">
          {tools.slice(0, 3).map((tool) => (
            <Badge key={tool} variant="outline" className="text-xs font-normal" role="listitem">
              <LucideIcons.Wrench className="mr-1 h-3 w-3" aria-hidden="true" />
              {tool}
            </Badge>
          ))}
          {tools.length > 3 && (
            <Badge
              variant="outline"
              className="text-xs font-normal"
              aria-label={`${tools.length - 3} more tools`}
            >
              +{tools.length - 3}
            </Badge>
          )}
        </div>

        {/* Right: Deployed Badge + Score */}
        <div className="flex items-center gap-2">
          {hasDeployments && (
            <Badge variant="secondary" className="text-xs">
              <LucideIcons.CheckCircle2 className="mr-1 h-3 w-3" aria-hidden="true" />
              <span>Deployed ({deploymentCount})</span>
            </Badge>
          )}

          {artifact.score?.confidence !== undefined && (
            <ScoreBadge confidence={artifact.score.confidence * 100} size="sm" />
          )}
        </div>
      </div>
    </Card>
  );
}

/**
 * ArtifactBrowseCardSkeleton - Loading placeholder for ArtifactBrowseCard
 *
 * Displays a skeleton with matching dimensions while data is loading.
 */
export function ArtifactBrowseCardSkeleton({ className }: { className?: string }) {
  return (
    <Card
      className={cn('border-l-4', className)}
      aria-busy="true"
      aria-label="Loading artifact card"
    >
      {/* Header skeleton */}
      <div className="p-4 pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex flex-1 items-center gap-3">
            {/* Icon skeleton */}
            <div className="h-9 w-9 animate-pulse rounded-md bg-muted" aria-hidden="true" />
            {/* Name/author skeleton */}
            <div className="flex-1 space-y-2">
              <div className="h-4 w-32 animate-pulse rounded bg-muted" aria-hidden="true" />
              <div className="h-3 w-24 animate-pulse rounded bg-muted" aria-hidden="true" />
            </div>
          </div>
          {/* Actions skeleton */}
          <div className="h-8 w-8 animate-pulse rounded bg-muted" aria-hidden="true" />
        </div>
      </div>

      {/* Description skeleton */}
      <div className="space-y-2 px-4 pb-3">
        <div className="h-4 w-full animate-pulse rounded bg-muted" aria-hidden="true" />
        <div className="h-4 w-3/4 animate-pulse rounded bg-muted" aria-hidden="true" />
      </div>

      {/* Tags skeleton */}
      <div className="flex gap-1 px-4 pb-3">
        <div className="h-5 w-14 animate-pulse rounded-full bg-muted" aria-hidden="true" />
        <div className="h-5 w-16 animate-pulse rounded-full bg-muted" aria-hidden="true" />
        <div className="h-5 w-12 animate-pulse rounded-full bg-muted" aria-hidden="true" />
      </div>

      {/* Footer skeleton */}
      <div className="flex items-center justify-between border-t px-4 py-3">
        <div className="flex gap-1">
          <div className="h-5 w-16 animate-pulse rounded bg-muted" aria-hidden="true" />
          <div className="h-5 w-16 animate-pulse rounded bg-muted" aria-hidden="true" />
        </div>
        <div className="h-5 w-12 animate-pulse rounded bg-muted" aria-hidden="true" />
      </div>
    </Card>
  );
}
