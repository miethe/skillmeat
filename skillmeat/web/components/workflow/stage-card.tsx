'use client';

import * as React from 'react';
import { GripVertical, Pencil, Trash2, Bot, Wrench, BookOpen, Clock, RefreshCw } from 'lucide-react';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { InlineEdit } from '@/components/shared/inline-edit';
import type { WorkflowStage } from '@/types/workflow';

// ============================================================================
// Types
// ============================================================================

export interface StageCardProps {
  /** The workflow stage data to display. */
  stage: WorkflowStage;
  /** 0-based index; displayed as index+1 in the badge. */
  index: number;
  /** 'edit' for the builder canvas; 'readonly' for the detail page. */
  mode: 'edit' | 'readonly';
  /** Opens the stage detail/edit dialog. Edit mode only. */
  onEdit?: () => void;
  /** Removes the stage from the workflow. Edit mode only. */
  onDelete?: () => void;
  /** Called when the inline stage title is saved. Edit mode only. */
  onTitleChange?: (title: string) => void;
  /** Highlights the card with a primary ring. Edit mode only. */
  isSelected?: boolean;
  /** Additional CSS classes for the card root element. */
  className?: string;
  /**
   * Props spread onto the drag handle element.
   * Provided by @dnd-kit's useSortable listeners + attributes.
   * Intentionally typed as object to remain DnD-agnostic until integration.
   */
  dragHandleProps?: object;
}

// ============================================================================
// Helpers
// ============================================================================

/** Extract a human-readable agent name from a role artifact reference ("agent:name" → "name"). */
function parseAgentName(artifact: string | undefined): string | undefined {
  if (!artifact) return undefined;
  const parts = artifact.split(':');
  return parts.length > 1 ? parts.slice(1).join(':') : artifact;
}

/** Format a duration string like "30m" or "2h" for display. */
function formatDuration(raw: string | undefined): string | undefined {
  if (!raw) return undefined;
  return raw;
}

// ============================================================================
// Sub-components
// ============================================================================

interface SummaryRowProps {
  icon: React.ElementType;
  label: string;
  empty: boolean;
  emptyText: string;
  children: React.ReactNode;
}

function SummaryRow({ icon: Icon, label, empty, emptyText, children }: SummaryRowProps) {
  return (
    <div className="flex items-start gap-1.5 text-xs">
      <span className="text-muted-foreground font-medium shrink-0 mt-0.5 flex items-center gap-1">
        <Icon className="h-3 w-3 shrink-0" />
        {label}:
      </span>
      {empty ? (
        <span className="text-muted-foreground/60 italic">{emptyText}</span>
      ) : (
        <div className="flex flex-wrap gap-1">{children}</div>
      )}
    </div>
  );
}

// ============================================================================
// StageCard
// ============================================================================

/**
 * StageCard — displays a single workflow stage in either edit or readonly mode.
 *
 * Edit mode: drag handle, inline-editable title, edit/delete actions.
 * Readonly mode: plain title, footer with timeout/retry config, muted bg.
 *
 * DnD integration is deferred — pass `dragHandleProps` from @dnd-kit listeners
 * to connect drag behaviour without coupling this component to the library.
 */
export function StageCard({
  stage,
  index,
  mode,
  onEdit,
  onDelete,
  onTitleChange,
  isSelected = false,
  className,
  dragHandleProps,
}: StageCardProps) {
  const isEditMode = mode === 'edit';

  // Derived data -----------------------------------------------------------

  const agentName = parseAgentName(stage.roles?.primary?.artifact);
  const tools = stage.roles?.tools ?? [];
  const contextModules = stage.context?.modules ?? [];
  const timeout = formatDuration(stage.errorPolicy?.timeout);
  const retries = stage.errorPolicy?.retry?.maxAttempts;

  const hasTools = tools.length > 0;
  const hasContext = contextModules.length > 0;
  const hasFooter = !isEditMode && (timeout !== undefined || retries !== undefined);

  // -------------------------------------------------------------------------

  return (
    <div
      className={cn(
        // Base
        'rounded-lg border text-sm transition-all duration-150',
        // Edit mode
        isEditMode && [
          'bg-card relative group',
          'hover:shadow-sm',
          isSelected && 'ring-2 ring-primary border-primary',
        ],
        // Readonly mode
        !isEditMode && 'bg-muted/30',
        className
      )}
    >
      {/* ------------------------------------------------------------------ */}
      {/* Header                                                              */}
      {/* ------------------------------------------------------------------ */}
      <div
        className={cn(
          'flex items-center gap-2 px-3 py-2.5',
          isEditMode && 'pl-8' // room for the drag handle
        )}
      >
        {/* Drag handle — edit mode only */}
        {isEditMode && (
          <button
            type="button"
            aria-label="Drag to reorder stage"
            className={cn(
              'absolute left-2 top-1/2 -translate-y-1/2',
              'cursor-grab text-muted-foreground',
              'opacity-0 group-hover:opacity-100',
              'transition-opacity duration-150',
              'focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 rounded-sm'
            )}
            {...dragHandleProps}
          >
            <GripVertical className="h-4 w-4" />
          </button>
        )}

        {/* Stage number badge */}
        <div
          aria-label={`Stage ${index + 1}`}
          className={cn(
            'inline-flex items-center justify-center h-6 w-6 rounded-full',
            'text-xs font-semibold shrink-0 select-none',
            isEditMode
              ? 'bg-indigo-600 text-white dark:bg-indigo-500'
              : 'bg-muted text-muted-foreground'
          )}
        >
          {index + 1}
        </div>

        {/* Stage name */}
        <div className="flex-1 min-w-0">
          {isEditMode && onTitleChange ? (
            <InlineEdit
              value={stage.name}
              onChange={onTitleChange}
              placeholder="Untitled stage"
              as="span"
              className="font-semibold text-sm"
              inputClassName="h-6 text-sm font-semibold py-0"
            />
          ) : (
            <span className="font-semibold truncate block">{stage.name}</span>
          )}
        </div>

        {/* Edit / delete action buttons — edit mode only */}
        {isEditMode && (
          <div className="flex items-center gap-0.5 shrink-0">
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 text-muted-foreground hover:text-foreground"
              onClick={onEdit}
              aria-label={`Edit stage: ${stage.name}`}
            >
              <Pencil className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 text-muted-foreground hover:text-destructive"
              onClick={onDelete}
              aria-label={`Delete stage: ${stage.name}`}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        )}
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Summary rows                                                        */}
      {/* ------------------------------------------------------------------ */}
      <div className="px-3 pb-2.5 space-y-1.5">
        {/* Agent */}
        <SummaryRow
          icon={Bot}
          label="Agent"
          empty={!agentName}
          emptyText="No agent assigned"
        >
          <Badge
            variant="secondary"
            className={cn(
              'text-xs',
              isEditMode && 'bg-indigo-50 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300'
            )}
          >
            {agentName}
          </Badge>
        </SummaryRow>

        {/* Tools */}
        <SummaryRow
          icon={Wrench}
          label="Tools"
          empty={!hasTools}
          emptyText="No tools"
        >
          {tools.map((tool) => (
            <Badge key={tool} variant="secondary" className="text-xs">
              {tool}
            </Badge>
          ))}
        </SummaryRow>

        {/* Context */}
        <SummaryRow
          icon={BookOpen}
          label="Context"
          empty={!hasContext}
          emptyText="No context"
        >
          {contextModules.map((mod) => (
            <Badge key={mod} variant="secondary" className="text-xs font-mono">
              {mod}
            </Badge>
          ))}
        </SummaryRow>

        {/* Description — truncated */}
        {stage.description && (
          <p className="text-xs text-muted-foreground line-clamp-2 pt-0.5">
            {stage.description}
          </p>
        )}
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Footer — readonly mode only, shows timeout / retry config           */}
      {/* ------------------------------------------------------------------ */}
      {hasFooter && (
        <div
          className="px-3 py-2 border-t flex items-center gap-3 text-xs text-muted-foreground"
          aria-label="Stage configuration"
        >
          {timeout !== undefined && (
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" aria-hidden="true" />
              Timeout: {timeout}
            </span>
          )}
          {retries !== undefined && (
            <span className="flex items-center gap-1">
              <RefreshCw className="h-3 w-3" aria-hidden="true" />
              {retries === 1 ? 'No retries' : `Retries: ${retries - 1}`}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
