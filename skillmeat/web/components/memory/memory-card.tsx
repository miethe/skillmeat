/**
 * MemoryCard Component
 *
 * Single row in the Memory Inbox list. Dense, triage-oriented layout with
 * checkbox, confidence bar, type badge, content preview, metadata, and
 * hover-revealed action buttons.
 *
 * Design spec reference: section 3.4
 */

'use client';

import * as React from 'react';
import { Check, Pencil, X, ShieldCheck, RotateCcw, Archive } from 'lucide-react';
import type { MemoryItemResponse } from '@/sdk/models/MemoryItemResponse';
import { Checkbox } from '@/components/ui/checkbox';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
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
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * MemoryCard -- a single row in the memory inbox list.
 *
 * Layout: [Checkbox] [ConfidenceBar] [TypeBadge + Content + Metadata] [Actions]
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
}: MemoryCardProps) {
  const confidenceTier = getConfidenceTier(memory.confidence);
  const confidenceColors = getConfidenceColorClasses(confidenceTier);
  const confidencePercent = Math.round(memory.confidence * 100);

  // Extract provenance source string if available
  const provenanceSource =
    memory.provenance && typeof memory.provenance === 'object'
      ? (memory.provenance as Record<string, unknown>).source_type as string | undefined
      : undefined;

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
      <div className="flex items-center" onClick={(e) => e.stopPropagation()}>
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
        </div>
      </div>

      {/* Action buttons (visible on hover/focus-within, status-aware) */}
      <TooltipProvider delayDuration={300}>
        <div
          className={cn(
            'flex items-center gap-1 opacity-0 transition-opacity',
            'group-hover:opacity-100 group-focus-within:opacity-100'
          )}
        >
          {/* candidate: Approve (green check), Edit, Reject (red X) */}
          {memory.status === 'candidate' && (
            <>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={(e) => {
                      e.stopPropagation();
                      onApprove(memory.id);
                    }}
                    aria-label={`Approve memory: ${memory.content.slice(0, 40)}`}
                  >
                    <Check className="h-3.5 w-3.5 text-emerald-600" aria-hidden="true" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Promote to active</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={(e) => {
                      e.stopPropagation();
                      onEdit(memory.id);
                    }}
                    aria-label={`Edit memory: ${memory.content.slice(0, 40)}`}
                  >
                    <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Edit</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={(e) => {
                      e.stopPropagation();
                      onReject(memory.id);
                    }}
                    aria-label={`Reject memory: ${memory.content.slice(0, 40)}`}
                  >
                    <X className="h-3.5 w-3.5 text-red-500" aria-hidden="true" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Reject</TooltipContent>
              </Tooltip>
            </>
          )}

          {/* active: Promote (blue shield), Edit, Deprecate (red archive) */}
          {memory.status === 'active' && (
            <>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={(e) => {
                      e.stopPropagation();
                      onApprove(memory.id);
                    }}
                    aria-label={`Promote memory to stable: ${memory.content.slice(0, 40)}`}
                  >
                    <ShieldCheck className="h-3.5 w-3.5 text-blue-600" aria-hidden="true" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Promote to stable</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={(e) => {
                      e.stopPropagation();
                      onEdit(memory.id);
                    }}
                    aria-label={`Edit memory: ${memory.content.slice(0, 40)}`}
                  >
                    <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Edit</TooltipContent>
              </Tooltip>
              {onDeprecate && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeprecate(memory.id);
                      }}
                      aria-label={`Deprecate memory: ${memory.content.slice(0, 40)}`}
                    >
                      <Archive className="h-3.5 w-3.5 text-red-500" aria-hidden="true" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Deprecate</TooltipContent>
                </Tooltip>
              )}
            </>
          )}

          {/* stable: Edit only */}
          {memory.status === 'stable' && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={(e) => {
                    e.stopPropagation();
                    onEdit(memory.id);
                  }}
                  aria-label={`Edit memory: ${memory.content.slice(0, 40)}`}
                >
                  <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Edit</TooltipContent>
            </Tooltip>
          )}

          {/* deprecated: Reactivate (amber), Edit */}
          {memory.status === 'deprecated' && (
            <>
              {onReactivate && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={(e) => {
                        e.stopPropagation();
                        onReactivate(memory.id);
                      }}
                      aria-label={`Reactivate memory: ${memory.content.slice(0, 40)}`}
                    >
                      <RotateCcw className="h-3.5 w-3.5 text-amber-600" aria-hidden="true" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Reactivate as candidate</TooltipContent>
                </Tooltip>
              )}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={(e) => {
                      e.stopPropagation();
                      onEdit(memory.id);
                    }}
                    aria-label={`Edit memory: ${memory.content.slice(0, 40)}`}
                  >
                    <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Edit</TooltipContent>
              </Tooltip>
            </>
          )}
        </div>
      </TooltipProvider>
    </div>
  );
}
