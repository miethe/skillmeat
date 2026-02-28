'use client';

import * as React from 'react';
import Link from 'next/link';
import {
  Play,
  Pencil,
  MoreHorizontal,
  GitBranch,
  Clock,
  CalendarDays,
  Copy,
  Trash2,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn, formatDistanceToNow, formatDate } from '@/lib/utils';
import type { Workflow, WorkflowStatus } from '@/types/workflow';

// ---------------------------------------------------------------------------
// Status badge config — mirrors WorkflowCard for visual consistency
// ---------------------------------------------------------------------------

const STATUS_CONFIG: Record<WorkflowStatus, { label: string; className: string }> = {
  draft: {
    label: 'Draft',
    className: 'bg-yellow-500/10 text-yellow-600 border-yellow-500/20 dark:text-yellow-400',
  },
  active: {
    label: 'Active',
    className: 'bg-green-500/10 text-green-600 border-green-500/20 dark:text-green-400',
  },
  archived: {
    label: 'Archived',
    className: 'bg-muted text-muted-foreground border-border',
  },
  deprecated: {
    label: 'Deprecated',
    className: 'bg-orange-500/10 text-orange-600 border-orange-500/20 dark:text-orange-400',
  },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Max visible tags before overflow "+N" is shown. */
const MAX_VISIBLE_TAGS = 2;

function formatLastRun(lastRunAt?: string | null): string {
  if (!lastRunAt) return 'Never';
  return formatDistanceToNow(lastRunAt);
}

function formatUpdated(updatedAt: string): string {
  return formatDate(updatedAt, { month: 'short', day: 'numeric' });
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface WorkflowListItemProps {
  /** Full workflow definition as returned by the API. */
  workflow: Workflow;
  /**
   * ISO 8601 timestamp of the most recent execution, if known.
   * Displays "Never" when absent.
   */
  lastRunAt?: string | null;
  /** Triggered when the Run icon button is clicked. */
  onRun?: () => void;
  /** Triggered when the Edit icon button is clicked. */
  onEdit?: () => void;
  /** Triggered when Duplicate is selected from the overflow menu. */
  onDuplicate?: () => void;
  /** Triggered when Delete is selected from the overflow menu. */
  onDelete?: () => void;
  /**
   * When provided, clicking the row (or the name) calls this handler instead
   * of navigating to the workflow detail page. Action buttons are unaffected.
   */
  onClick?: () => void;
  /** Optional className override for the row container. */
  className?: string;
}

// ---------------------------------------------------------------------------
// WorkflowListItem
// ---------------------------------------------------------------------------

/**
 * WorkflowListItem
 *
 * Compact horizontal row for the workflow library list view. Each row
 * displays: name (link) + status badge, stage count, up to 2 tags with
 * overflow, last-run time, updated date, and action buttons.
 *
 * Clicking the workflow name (or row when `onClick` is provided) navigates
 * to the detail page, or calls `onClick` when provided. Action buttons
 * stop propagation so they never trigger navigation or onClick.
 *
 * Accessibility:
 * - Row root is an `<li>` with `role="row"` semantics handled by the parent.
 * - The name is an anchor with a descriptive aria-label.
 * - All action buttons carry explicit aria-labels.
 * - Tags are rendered as an inline list.
 *
 * @example
 * ```tsx
 * <ul role="list" aria-label="Workflows">
 *   {workflows.map((wf) => (
 *     <WorkflowListItem
 *       key={wf.id}
 *       workflow={wf}
 *       lastRunAt={latestExecution?.startedAt}
 *       onRun={() => startExecution(wf.id)}
 *       onEdit={() => router.push(`/workflows/${wf.id}/edit`)}
 *       onDuplicate={() => duplicateWorkflow(wf.id)}
 *       onDelete={() => deleteWorkflow(wf.id)}
 *       onClick={() => openWorkflowModal(wf.id)}
 *     />
 *   ))}
 * </ul>
 * ```
 */
export function WorkflowListItem({
  workflow,
  lastRunAt,
  onRun,
  onEdit,
  onDuplicate,
  onDelete,
  onClick,
  className,
}: WorkflowListItemProps) {
  const { id, name, status, stages, tags, updatedAt } = workflow;

  const stageCount = stages?.length ?? 0;
  const statusCfg = STATUS_CONFIG[status];
  const isRunDisabled = !onRun || status === 'archived' || status === 'deprecated';

  const visibleTags = tags.slice(0, MAX_VISIBLE_TAGS);
  const overflowCount = tags.length - visibleTags.length;

  // Prevent action button clicks from bubbling
  const stopProp = (e: React.MouseEvent) => e.stopPropagation();

  return (
    <li
      aria-label={`Workflow: ${name}`}
      onClick={onClick}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick();
              }
            }
          : undefined
      }
      tabIndex={onClick ? 0 : undefined}
      role={onClick ? 'button' : undefined}
      className={cn(
        'group flex items-center gap-4 border-b px-4 py-3 last:border-b-0',
        'transition-colors duration-150 hover:bg-muted/50',
        onClick && 'cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset',
        className
      )}
    >
      {/* ------------------------------------------------------------------ */}
      {/* Column 1: Icon + Name + Status badge                                */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex min-w-0 flex-1 items-center gap-3">
        {/* Workflow icon — decorative, mirrors WorkflowCard */}
        <div
          className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md bg-indigo-50 text-indigo-500 dark:bg-indigo-500/15 dark:text-indigo-400"
          aria-hidden="true"
        >
          <GitBranch className="h-4 w-4" />
        </div>

        {/* Name — link when no onClick, plain text when row handles the click */}
        {onClick ? (
          <span
            className={cn(
              'min-w-0 truncate text-sm font-medium text-foreground',
              'hover:text-indigo-600 dark:hover:text-indigo-400'
            )}
          >
            {name}
          </span>
        ) : (
          <Link
            href={`/workflows/${id}`}
            className={cn(
              'min-w-0 truncate text-sm font-medium text-foreground',
              'hover:text-indigo-600 dark:hover:text-indigo-400',
              'focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded'
            )}
            aria-label={`View details for ${name}`}
            onClick={stopProp}
          >
            {name}
          </Link>
        )}

        {/* Status badge — inline with name */}
        <Badge
          variant="outline"
          className={cn('flex-shrink-0 text-[11px] font-medium', statusCfg.className)}
        >
          {statusCfg.label}
        </Badge>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Column 2: Stage count                                               */}
      {/* ------------------------------------------------------------------ */}
      <div
        className="hidden w-20 flex-shrink-0 text-right text-sm text-muted-foreground sm:block"
        aria-label={`${stageCount} ${stageCount === 1 ? 'stage' : 'stages'}`}
      >
        <span className="font-medium tabular-nums text-foreground">{stageCount}</span>
        <span className="ml-1 text-xs">
          {stageCount === 1 ? 'stage' : 'stages'}
        </span>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Column 3: Tags (max 2 + overflow)                                   */}
      {/* ------------------------------------------------------------------ */}
      <div className="hidden w-36 flex-shrink-0 md:block">
        {tags.length > 0 ? (
          <ul
            role="list"
            aria-label="Tags"
            className="flex flex-wrap gap-1"
          >
            {visibleTags.map((tag) => (
              <li key={tag} role="listitem">
                <Badge
                  variant="outline"
                  className="text-[11px] font-normal px-1.5 py-0 text-muted-foreground"
                >
                  {tag}
                </Badge>
              </li>
            ))}
            {overflowCount > 0 && (
              <li role="listitem">
                <Badge
                  variant="outline"
                  className="text-[11px] font-normal px-1.5 py-0 text-muted-foreground"
                  aria-label={`${overflowCount} more tags`}
                >
                  +{overflowCount}
                </Badge>
              </li>
            )}
          </ul>
        ) : (
          <span className="text-xs text-muted-foreground/50">—</span>
        )}
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Column 4: Last run                                                  */}
      {/* ------------------------------------------------------------------ */}
      <div
        className="hidden w-28 flex-shrink-0 text-right lg:block"
        aria-label={lastRunAt ? `Last run ${formatLastRun(lastRunAt)}` : 'Never run'}
      >
        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
          <Clock className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
          {formatLastRun(lastRunAt)}
        </span>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Column 5: Updated date                                              */}
      {/* ------------------------------------------------------------------ */}
      <div
        className="hidden w-24 flex-shrink-0 text-right lg:block"
        aria-label={`Updated ${formatUpdated(updatedAt)}`}
      >
        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
          <CalendarDays className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
          {formatUpdated(updatedAt)}
        </span>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Column 6: Action buttons                                            */}
      {/* ------------------------------------------------------------------ */}
      <div
        className="flex flex-shrink-0 items-center gap-1"
        onClick={stopProp}
      >
        {/* Run — icon-only button with tooltip-quality aria-label */}
        <Button
          size="sm"
          variant="ghost"
          className={cn(
            'h-8 w-8 p-0',
            !isRunDisabled && 'text-indigo-600 hover:bg-indigo-50 hover:text-indigo-700 dark:text-indigo-400 dark:hover:bg-indigo-500/10'
          )}
          onClick={onRun}
          disabled={isRunDisabled}
          aria-label={`Run workflow: ${name}`}
        >
          <Play className="h-3.5 w-3.5 fill-current" aria-hidden="true" />
        </Button>

        {/* Edit — icon-only */}
        <Button
          size="sm"
          variant="ghost"
          className="h-8 w-8 p-0"
          onClick={onEdit}
          disabled={!onEdit}
          aria-label={`Edit workflow: ${name}`}
        >
          <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
        </Button>

        {/* Three-dot overflow menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              size="sm"
              variant="ghost"
              className="h-8 w-8 p-0"
              aria-label={`More options for workflow: ${name}`}
            >
              <MoreHorizontal className="h-4 w-4" aria-hidden="true" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-40">
            <DropdownMenuItem
              onClick={onDuplicate}
              disabled={!onDuplicate}
              className="gap-2 text-sm"
            >
              <Copy className="h-3.5 w-3.5" aria-hidden="true" />
              Duplicate
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={onDelete}
              disabled={!onDelete}
              className="gap-2 text-sm text-destructive focus:text-destructive"
            >
              <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </li>
  );
}

// ---------------------------------------------------------------------------
// WorkflowListItemSkeleton
// ---------------------------------------------------------------------------

/**
 * Loading skeleton for WorkflowListItem.
 *
 * Matches the row's visual footprint so the list height is stable while
 * data loads. Uses `animate-pulse` for a subtle shimmer effect.
 *
 * @example
 * ```tsx
 * // Render 5 skeleton rows while fetching
 * {isLoading && Array.from({ length: 5 }).map((_, i) => (
 *   <WorkflowListItemSkeleton key={i} />
 * ))}
 * ```
 */
export function WorkflowListItemSkeleton() {
  return (
    <li
      aria-hidden="true"
      className="flex items-center gap-4 border-b px-4 py-3 last:border-b-0 animate-pulse"
    >
      {/* Icon + name + badge */}
      <div className="flex flex-1 items-center gap-3 min-w-0">
        <div className="h-8 w-8 flex-shrink-0 rounded-md bg-muted" />
        <div className="h-3.5 w-40 rounded bg-muted" />
        <div className="h-5 w-14 flex-shrink-0 rounded-full bg-muted" />
      </div>

      {/* Stage count */}
      <div className="hidden w-20 sm:block">
        <div className="ml-auto h-3 w-14 rounded bg-muted" />
      </div>

      {/* Tags */}
      <div className="hidden w-36 md:flex gap-1">
        <div className="h-5 w-12 rounded-full bg-muted" />
        <div className="h-5 w-14 rounded-full bg-muted" />
      </div>

      {/* Last run */}
      <div className="hidden w-28 lg:block">
        <div className="ml-auto h-3 w-20 rounded bg-muted" />
      </div>

      {/* Updated */}
      <div className="hidden w-24 lg:block">
        <div className="ml-auto h-3 w-16 rounded bg-muted" />
      </div>

      {/* Action buttons */}
      <div className="flex flex-shrink-0 items-center gap-1">
        <div className="h-8 w-8 rounded-md bg-muted" />
        <div className="h-8 w-8 rounded-md bg-muted" />
        <div className="h-8 w-8 rounded-md bg-muted" />
      </div>
    </li>
  );
}
