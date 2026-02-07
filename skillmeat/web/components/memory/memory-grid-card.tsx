/**
 * MemoryGridCard Component
 *
 * Card-based layout for displaying memory items in a grid view.
 * Follows the ArtifactBrowseCard pattern with a left border accent
 * colored by confidence tier, a meatballs menu for status-aware actions,
 * and a metadata footer.
 *
 * Visual hierarchy:
 * 1. Header: MemoryTypeBadge + meatballs menu
 * 2. Body: Content preview (3-line clamp)
 * 3. Metadata: Confidence %, relative time, access count, provenance source
 * 4. Footer: Status dot + label, quick action buttons (status-aware)
 */

'use client';

import * as React from 'react';
import {
  MoreVertical,
  Check,
  Pencil,
  X,
  ShieldCheck,
  RotateCcw,
  Archive,
  Trash2,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { MemoryItemResponse } from '@/sdk/models/MemoryItemResponse';
import { MemoryTypeBadge } from './memory-type-badge';
import {
  getConfidenceTier,
  getConfidenceColorClasses,
  formatRelativeTime,
  getStatusDotClass,
} from './memory-utils';
import type { ConfidenceTier } from './memory-utils';

// ---------------------------------------------------------------------------
// Confidence-based left border accent colors
// ---------------------------------------------------------------------------

/**
 * Maps confidence tier to a 4px left border color class.
 * Mirrors the ArtifactBrowseCard type-accent pattern but keyed on confidence.
 */
const confidenceBorderAccents: Record<ConfidenceTier, string> = {
  high: 'border-l-emerald-500',
  medium: 'border-l-amber-500',
  low: 'border-l-red-500',
};

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface MemoryGridCardProps {
  /** The memory item data from the API. */
  memory: MemoryItemResponse;
  /** Whether this card's checkbox is checked (selected state). */
  selected: boolean;
  /** Whether this card currently has keyboard focus (roving tabindex). */
  focused: boolean;
  /** Toggle selection state for this memory. */
  onToggleSelect: (id: string) => void;
  /** Approve (promote) this memory item. */
  onApprove: (id: string) => void;
  /** Reject (dismiss) this memory item. */
  onReject: (id: string) => void;
  /** Open the edit panel/dialog for this memory. */
  onEdit: (id: string) => void;
  /** Open merge dialog for this memory. */
  onMerge: (id: string) => void;
  /** Select/focus this card (opens detail panel). */
  onClick: (id: string) => void;
  /** Reactivate a deprecated memory item. */
  onReactivate?: (id: string) => void;
  /** Deprecate this memory item (for non-candidate statuses). */
  onDeprecate?: (id: string) => void;
  /** Delete this memory item. */
  onDelete?: (id: string) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * MemoryGridCard -- a card for displaying memory items in a grid layout.
 *
 * Layout: Card with left accent border, header with type badge and meatballs
 * menu, content preview, metadata row, and status footer.
 *
 * @example
 * ```tsx
 * <MemoryGridCard
 *   memory={item}
 *   selected={selectedIds.has(item.id)}
 *   focused={focusedId === item.id}
 *   onToggleSelect={toggleSelect}
 *   onApprove={handleApprove}
 *   onReject={handleReject}
 *   onEdit={handleEdit}
 *   onMerge={handleMerge}
 *   onClick={handleCardClick}
 *   onDelete={handleDelete}
 * />
 * ```
 */
export function MemoryGridCard({
  memory,
  selected,
  focused,
  onToggleSelect,
  onApprove,
  onReject,
  onEdit,
  onClick,
  onReactivate,
  onDeprecate,
  onDelete,
}: MemoryGridCardProps) {
  const confidenceTier = getConfidenceTier(memory.confidence);
  const confidenceColors = getConfidenceColorClasses(confidenceTier);
  const confidencePercent = Math.round(memory.confidence * 100);

  // Extract provenance source string if available
  const provenanceSource =
    memory.provenance && typeof memory.provenance === 'object'
      ? (memory.provenance as Record<string, unknown>).source_type as string | undefined
      : undefined;

  // Handle card click, avoiding trigger when clicking action buttons
  const handleCardClick = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    if (target.closest('button') || target.closest('[role="menuitem"]')) {
      return;
    }
    onClick(memory.id);
  };

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      onClick(memory.id);
    }
    if (e.key === ' ') {
      e.preventDefault();
      onToggleSelect(memory.id);
    }
  };

  return (
    <Card
      className={cn(
        'cursor-pointer border-l-4 transition-all',
        'hover:border-primary/50 hover:shadow-md',
        'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
        confidenceBorderAccents[confidenceTier],
        selected && 'bg-primary/5',
        focused && 'ring-2 ring-ring ring-offset-2'
      )}
      onClick={handleCardClick}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={focused ? 0 : -1}
      aria-pressed={selected}
      aria-label={`Memory item: ${memory.type}, ${confidencePercent}% confidence, ${memory.status}`}
    >
      {/* Header: Type Badge + Meatballs Menu */}
      <div className="flex items-start justify-between gap-2 p-4 pb-2">
        <MemoryTypeBadge type={memory.type} />

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 flex-shrink-0"
              aria-label={`Actions for memory: ${memory.content.slice(0, 40)}`}
              onClick={(e) => e.stopPropagation()}
            >
              <MoreVertical className="h-4 w-4" aria-hidden="true" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            {/* candidate: Approve, Edit, Reject */}
            {memory.status === 'candidate' && (
              <>
                <DropdownMenuItem
                  onClick={() => onApprove(memory.id)}
                >
                  <Check className="mr-2 h-4 w-4 text-emerald-600" aria-hidden="true" />
                  Approve
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => onEdit(memory.id)}
                >
                  <Pencil className="mr-2 h-4 w-4" aria-hidden="true" />
                  Edit
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => onReject(memory.id)}
                >
                  <X className="mr-2 h-4 w-4 text-red-500" aria-hidden="true" />
                  Reject
                </DropdownMenuItem>
              </>
            )}

            {/* active: Promote to Stable, Edit, Deprecate */}
            {memory.status === 'active' && (
              <>
                <DropdownMenuItem
                  onClick={() => onApprove(memory.id)}
                >
                  <ShieldCheck className="mr-2 h-4 w-4 text-blue-600" aria-hidden="true" />
                  Promote to Stable
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => onEdit(memory.id)}
                >
                  <Pencil className="mr-2 h-4 w-4" aria-hidden="true" />
                  Edit
                </DropdownMenuItem>
                {onDeprecate && (
                  <DropdownMenuItem
                    onClick={() => onDeprecate(memory.id)}
                  >
                    <Archive className="mr-2 h-4 w-4 text-red-500" aria-hidden="true" />
                    Deprecate
                  </DropdownMenuItem>
                )}
              </>
            )}

            {/* stable: Edit only */}
            {memory.status === 'stable' && (
              <DropdownMenuItem
                onClick={() => onEdit(memory.id)}
              >
                <Pencil className="mr-2 h-4 w-4" aria-hidden="true" />
                Edit
              </DropdownMenuItem>
            )}

            {/* deprecated: Reactivate, Edit */}
            {memory.status === 'deprecated' && (
              <>
                {onReactivate && (
                  <DropdownMenuItem
                    onClick={() => onReactivate(memory.id)}
                  >
                    <RotateCcw className="mr-2 h-4 w-4 text-amber-600" aria-hidden="true" />
                    Reactivate
                  </DropdownMenuItem>
                )}
                <DropdownMenuItem
                  onClick={() => onEdit(memory.id)}
                >
                  <Pencil className="mr-2 h-4 w-4" aria-hidden="true" />
                  Edit
                </DropdownMenuItem>
              </>
            )}

            {/* Delete: always available, destructive */}
            {onDelete && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  className="text-destructive focus:text-destructive"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(memory.id);
                  }}
                >
                  <Trash2 className="mr-2 h-4 w-4" aria-hidden="true" />
                  Delete
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Body: Content Preview */}
      <div className="px-4 pb-3">
        <p className="line-clamp-3 text-sm leading-snug text-foreground">
          {memory.content}
        </p>
      </div>

      {/* Metadata Row: Confidence, Time, Access Count */}
      <div className="flex items-center gap-3 px-4 pb-3 text-xs text-muted-foreground">
        <span className={cn('font-medium', confidenceColors.text)}>
          {confidencePercent}%
        </span>
        <span>{formatRelativeTime(memory.created_at)}</span>
        <span>Used {memory.access_count ?? 0}x</span>
        {provenanceSource && (
          <span className="truncate max-w-[100px]" title={provenanceSource}>{provenanceSource}</span>
        )}
      </div>

      {/* Footer: Status + Actions */}
      <div className="flex items-center justify-between border-t px-4 py-2.5">
        {/* Left: Status dot + label */}
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <span
            className={cn(
              'h-2 w-2 rounded-full',
              getStatusDotClass(memory.status)
            )}
            aria-hidden="true"
          />
          <span className="capitalize">{memory.status}</span>
        </span>

        {/* Right: Quick action buttons */}
        <TooltipProvider delayDuration={300}>
          <div className="flex items-center gap-1">
            {/* candidate: Approve + Reject */}
            {memory.status === 'candidate' && (
              <>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={(e) => { e.stopPropagation(); onApprove(memory.id); }}
                      aria-label="Approve"
                    >
                      <Check className="h-3.5 w-3.5 text-emerald-600" aria-hidden="true" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Approve</TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={(e) => { e.stopPropagation(); onReject(memory.id); }}
                      aria-label="Reject"
                    >
                      <X className="h-3.5 w-3.5 text-red-500" aria-hidden="true" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Reject</TooltipContent>
                </Tooltip>
              </>
            )}

            {/* active: Promote to Stable */}
            {memory.status === 'active' && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={(e) => { e.stopPropagation(); onApprove(memory.id); }}
                    aria-label="Promote to stable"
                  >
                    <ShieldCheck className="h-3.5 w-3.5 text-blue-600" aria-hidden="true" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Promote to stable</TooltipContent>
              </Tooltip>
            )}

            {/* deprecated: Reactivate */}
            {memory.status === 'deprecated' && onReactivate && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={(e) => { e.stopPropagation(); onReactivate(memory.id); }}
                    aria-label="Reactivate"
                  >
                    <RotateCcw className="h-3.5 w-3.5 text-amber-600" aria-hidden="true" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Reactivate</TooltipContent>
              </Tooltip>
            )}

            {/* Edit: always present */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={(e) => { e.stopPropagation(); onEdit(memory.id); }}
                  aria-label="Edit"
                >
                  <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Edit</TooltipContent>
            </Tooltip>
          </div>
        </TooltipProvider>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

/**
 * MemoryGridCardSkeleton -- loading placeholder matching MemoryGridCard layout.
 *
 * @example
 * ```tsx
 * <div className="grid grid-cols-3 gap-4">
 *   {Array.from({ length: 6 }).map((_, i) => (
 *     <MemoryGridCardSkeleton key={i} />
 *   ))}
 * </div>
 * ```
 */
export function MemoryGridCardSkeleton({ className }: { className?: string }) {
  return (
    <Card
      className={cn('border-l-4', className)}
      aria-busy="true"
      aria-label="Loading memory card"
    >
      {/* Header skeleton: badge + action button */}
      <div className="flex items-start justify-between gap-2 p-4 pb-2">
        <div className="h-4 w-16 animate-pulse rounded bg-muted" aria-hidden="true" />
        <div className="h-8 w-8 animate-pulse rounded bg-muted" aria-hidden="true" />
      </div>

      {/* Content skeleton: 3 lines */}
      <div className="space-y-2 px-4 pb-3">
        <div className="h-4 w-full animate-pulse rounded bg-muted" aria-hidden="true" />
        <div className="h-4 w-5/6 animate-pulse rounded bg-muted" aria-hidden="true" />
        <div className="h-4 w-2/3 animate-pulse rounded bg-muted" aria-hidden="true" />
      </div>

      {/* Metadata skeleton */}
      <div className="flex gap-3 px-4 pb-3">
        <div className="h-3 w-8 animate-pulse rounded bg-muted" aria-hidden="true" />
        <div className="h-3 w-14 animate-pulse rounded bg-muted" aria-hidden="true" />
        <div className="h-3 w-12 animate-pulse rounded bg-muted" aria-hidden="true" />
      </div>

      {/* Footer skeleton */}
      <div className="flex items-center justify-between border-t px-4 py-2.5">
        <div className="flex items-center gap-1.5">
          <div className="h-2 w-2 animate-pulse rounded-full bg-muted" aria-hidden="true" />
          <div className="h-3 w-16 animate-pulse rounded bg-muted" aria-hidden="true" />
        </div>
        <div className="flex items-center gap-1">
          <div className="h-7 w-7 animate-pulse rounded bg-muted" aria-hidden="true" />
          <div className="h-7 w-7 animate-pulse rounded bg-muted" aria-hidden="true" />
        </div>
      </div>
    </Card>
  );
}
