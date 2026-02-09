/**
 * MemoryCard Component
 *
 * Single row in the Memory Inbox list. Dense, triage-oriented layout with
 * checkbox, confidence bar, type badge, content preview, metadata, and
 * a meatballs (three-dot) dropdown menu for status-aware actions.
 *
 * Design spec reference: section 3.4
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
import type { MemoryItemResponse } from '@/sdk/models/MemoryItemResponse';
import { Checkbox } from '@/components/ui/checkbox';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';
import { MemoryTypeBadge } from './memory-type-badge';
import {
  getConfidenceTier,
  getConfidenceColorClasses,
  getConfidenceBarColor,
  formatRelativeTime,
  getStatusDotClass,
} from './memory-utils';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface MemoryCardProps {
  /** The memory item data from the API. */
  memory: MemoryItemResponse;
  /** Whether this card's checkbox is checked. */
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
 * MemoryCard -- a single row in the memory inbox list.
 *
 * Layout: [Checkbox] [ConfidenceBar] [TypeBadge + Content + Metadata] [DropdownMenu]
 *
 * @example
 * ```tsx
 * <MemoryCard
 *   memory={item}
 *   selected={selectedIds.has(item.id)}
 *   focused={focusedIndex === idx}
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
export function MemoryCard({
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
}: MemoryCardProps) {
  const confidenceTier = getConfidenceTier(memory.confidence);
  const confidenceColors = getConfidenceColorClasses(confidenceTier);
  const confidencePercent = Math.round(memory.confidence * 100);

  // Extract provenance source string if available
  const provenanceSource =
    memory.provenance && typeof memory.provenance === 'object'
      ? (memory.provenance as Record<string, unknown>).source_type as string | undefined
      : undefined;

  // Extract tags if available (forward-compatible with future API additions)
  const tags = (memory as Record<string, unknown>).tags as string[] | undefined;
  const visibleTags = tags?.slice(0, 2);

  return (
    <div
      role="row"
      tabIndex={focused ? 0 : -1}
      aria-selected={selected}
      aria-label={`Memory item: ${memory.type}, ${confidencePercent}% confidence, ${memory.status}`}
      className={cn(
        'group flex items-stretch gap-3 px-6 py-3 cursor-pointer',
        'transition-colors duration-75',
        'hover:bg-accent/50',
        focused && 'bg-accent/70 ring-1 ring-ring ring-inset',
        selected && 'bg-primary/5'
      )}
      onClick={() => onClick(memory.id)}
      onKeyDown={(e) => {
        if (e.key === 'Enter') {
          onClick(memory.id);
        }
        if (e.key === ' ') {
          e.preventDefault();
          onToggleSelect(memory.id);
        }
      }}
    >
      {/* Checkbox */}
      <div
        className="flex items-center self-stretch -ml-6 pl-6 pr-3 cursor-pointer"
        onClick={(e) => {
          e.stopPropagation();
          const target = e.target as HTMLElement;
          if (!target.closest('button[role="checkbox"]')) {
            onToggleSelect(memory.id);
          }
        }}
        role="presentation"
      >
        <Checkbox
          checked={selected}
          onCheckedChange={() => onToggleSelect(memory.id)}
          aria-label={`Select memory: ${memory.content.slice(0, 40)}`}
        />
      </div>

      {/* Confidence bar */}
      <div
        className={cn(
          'w-[3px] self-stretch rounded-full flex-shrink-0',
          getConfidenceBarColor(confidenceTier)
        )}
        aria-hidden="true"
      />

      {/* Content area */}
      <div className="flex-1 min-w-0">
        {/* First row: type badge + content preview */}
        <div className="flex items-start gap-2">
          <MemoryTypeBadge type={memory.type} />
          <p className="text-sm leading-snug line-clamp-2 text-foreground">
            {memory.content}
          </p>
        </div>

        {/* Second row: metadata */}
        <div className="mt-1.5 flex items-center gap-3 text-xs text-muted-foreground">
          {/* Confidence percentage */}
          <span className={cn('font-medium', confidenceColors.text)}>
            {confidencePercent}%
          </span>

          {/* Relative time */}
          <span>{formatRelativeTime(memory.created_at)}</span>

          {/* Access count */}
          <span>Used {memory.access_count ?? 0}x</span>

          {/* Provenance source */}
          {provenanceSource && (
            <span className="truncate max-w-[120px]">{provenanceSource}</span>
          )}

          {/* Status dot + label */}
          <span className="flex items-center gap-1">
            <span
              className={cn(
                'h-1.5 w-1.5 rounded-full',
                getStatusDotClass(memory.status)
              )}
              aria-hidden="true"
            />
            {memory.status}
          </span>

          {/* Tags (first 2, if available) */}
          {visibleTags && visibleTags.length > 0 && (
            <>
              {visibleTags.map((tag) => (
                <Badge
                  key={tag}
                  variant="secondary"
                  className="text-[10px] px-1.5 py-0 h-4 leading-none"
                >
                  {tag}
                </Badge>
              ))}
            </>
          )}
        </div>
      </div>

      {/* Meatballs dropdown menu (always visible) */}
      <div className="flex items-center">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
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
                <DropdownMenuItem onClick={() => onApprove(memory.id)}>
                  <Check className="mr-2 h-4 w-4 text-emerald-600" aria-hidden="true" />
                  Approve
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onEdit(memory.id)}>
                  <Pencil className="mr-2 h-4 w-4" aria-hidden="true" />
                  Edit
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onReject(memory.id)}>
                  <X className="mr-2 h-4 w-4 text-red-500" aria-hidden="true" />
                  Reject
                </DropdownMenuItem>
              </>
            )}

            {/* active: Promote to Stable, Edit, Deprecate */}
            {memory.status === 'active' && (
              <>
                <DropdownMenuItem onClick={() => onApprove(memory.id)}>
                  <ShieldCheck className="mr-2 h-4 w-4 text-blue-600" aria-hidden="true" />
                  Promote to Stable
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onEdit(memory.id)}>
                  <Pencil className="mr-2 h-4 w-4" aria-hidden="true" />
                  Edit
                </DropdownMenuItem>
                {onDeprecate && (
                  <DropdownMenuItem
                    className="text-red-500 focus:text-red-500"
                    onClick={() => onDeprecate(memory.id)}
                  >
                    <Archive className="mr-2 h-4 w-4" aria-hidden="true" />
                    Deprecate
                  </DropdownMenuItem>
                )}
              </>
            )}

            {/* stable: Edit only */}
            {memory.status === 'stable' && (
              <DropdownMenuItem onClick={() => onEdit(memory.id)}>
                <Pencil className="mr-2 h-4 w-4" aria-hidden="true" />
                Edit
              </DropdownMenuItem>
            )}

            {/* deprecated: Reactivate, Edit */}
            {memory.status === 'deprecated' && (
              <>
                {onReactivate && (
                  <DropdownMenuItem onClick={() => onReactivate(memory.id)}>
                    <RotateCcw className="mr-2 h-4 w-4 text-amber-600" aria-hidden="true" />
                    Reactivate
                  </DropdownMenuItem>
                )}
                <DropdownMenuItem onClick={() => onEdit(memory.id)}>
                  <Pencil className="mr-2 h-4 w-4" aria-hidden="true" />
                  Edit
                </DropdownMenuItem>
              </>
            )}

            {/* Delete action (always present) */}
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-destructive focus:text-destructive"
              onClick={() => onDelete?.(memory.id)}
            >
              <Trash2 className="mr-2 h-4 w-4" aria-hidden="true" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}
