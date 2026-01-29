/**
 * Entity Card Component
 *
 * Card view for displaying a single entity with icon, name, type badge,
 * status indicator, tags, and actions menu.
 *
 * This component now wraps the UnifiedCard component for consistent
 * rendering across the application.
 */

'use client';

import * as React from 'react';
import type { Artifact } from '@/types/artifact';
import { UnifiedCard, UnifiedCardSkeleton } from '@/components/shared/unified-card';

/**
 * Props for EntityCard component
 *
 * Controls the card display, selection state, and action callbacks.
 */
export interface EntityCardProps {
  /** The artifact to display in the card (entity is deprecated alias) */
  entity: Artifact;
  /** Whether the card is currently selected */
  selected?: boolean;
  /** Whether the entity can be selected (shows checkbox) */
  selectable?: boolean;
  /** Callback when selection state changes */
  onSelect?: (selected: boolean) => void;
  /** Callback when card is clicked */
  onClick?: () => void;
  /** Callback for edit action */
  onEdit?: () => void;
  /** Callback for delete action */
  onDelete?: () => void;
  /** Callback for deploy action */
  onDeploy?: () => void;
  /** Callback for sync action */
  onSync?: () => void;
  /** Callback to view diff (enabled when status is "modified") */
  onViewDiff?: () => void;
  /** Callback to rollback (enabled for "modified" or "conflict" status) */
  onRollback?: () => void;
}

/**
 * EntityCard - Grid view card for displaying a single entity
 *
 * Renders entity information in card format with icon, name, type badge, description,
 * tags, status indicator, and action menu. Uses the unified ArtifactCard visual style.
 *
 * @example
 * ```tsx
 * <EntityCard
 *   entity={skill}
 *   selected={true}
 *   selectable={true}
 *   onSelect={(checked) => updateSelection(checked)}
 *   onClick={() => openDetail(skill)}
 *   onEdit={() => startEdit(skill)}
 *   onDelete={() => deleteEntity(skill)}
 * />
 * ```
 *
 * @param props - EntityCardProps configuration
 * @returns Unified card component with consistent ArtifactCard styling
 */
export function EntityCard(props: EntityCardProps) {
  return <UnifiedCard {...props} item={props.entity} />;
}

/**
 * EntityCardSkeleton - Loading skeleton for entity card
 *
 * Displays a placeholder while entity data is being fetched to prevent
 * layout shift and provide visual feedback to the user.
 * Uses the same unified ArtifactCard-style layout.
 *
 * @example
 * ```tsx
 * {isLoading && (
 *   <div className="grid gap-4">
 *     {Array.from({ length: 6 }).map((_, i) => (
 *       <EntityCardSkeleton key={i} />
 *     ))}
 *   </div>
 * )}
 * ```
 *
 * @returns Skeleton component matching EntityCard layout with selection checkbox
 */
export function EntityCardSkeleton() {
  return <UnifiedCardSkeleton selectable={true} />;
}
