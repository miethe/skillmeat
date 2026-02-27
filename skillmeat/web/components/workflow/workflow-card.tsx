'use client';

import * as React from 'react';
import Link from 'next/link';
import { Play, Pencil, MoreHorizontal, GitBranch, Clock, CalendarDays, Copy, Trash2 } from 'lucide-react';
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
// Status badge config
// ---------------------------------------------------------------------------

const STATUS_CONFIG: Record<
  WorkflowStatus,
  { label: string; className: string }
> = {
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
// Helper: derive last-run text from workflow stages
// The Workflow type stores executions separately; this card receives the
// workflow definition only. Last-run time is surfaced if caller injects it
// via the optional `lastRunAt` prop.
// ---------------------------------------------------------------------------

function formatLastRun(lastRunAt?: string | null): string {
  if (!lastRunAt) return 'Never run';
  return `Last run ${formatDistanceToNow(lastRunAt)}`;
}

function formatUpdated(updatedAt: string): string {
  return formatDate(updatedAt, { month: 'short', day: 'numeric' });
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface WorkflowCardProps {
  /** Full workflow definition as returned by the API. */
  workflow: Workflow;
  /**
   * ISO 8601 timestamp of the most recent execution, if known.
   * Callers typically derive this from the latest WorkflowExecution for the
   * workflow; the card shows "Never run" when absent.
   */
  lastRunAt?: string | null;
  /** Triggered when the Run button is clicked. */
  onRun?: () => void;
  /** Triggered when the Edit button is clicked. */
  onEdit?: () => void;
  /** Triggered when Duplicate is selected from the overflow menu. */
  onDuplicate?: () => void;
  /** Triggered when Delete is selected from the overflow menu. */
  onDelete?: () => void;
  /** Optional className override for the outer card. */
  className?: string;
}

// ---------------------------------------------------------------------------
// WorkflowCard
// ---------------------------------------------------------------------------

/**
 * WorkflowCard
 *
 * Compact grid card summarising a workflow definition. Clicking the card
 * body navigates to the workflow detail page. Action buttons (Run, Edit,
 * three-dot menu) stop propagation so they don't trigger navigation.
 *
 * Accessibility: the card root is an `<article>` with an accessible label.
 * Action buttons carry explicit aria-labels. Tags are rendered as a list.
 *
 * @example
 * ```tsx
 * <WorkflowCard
 *   workflow={workflow}
 *   lastRunAt={latestExecution?.startedAt}
 *   onRun={() => startExecution(workflow.id)}
 *   onEdit={() => router.push(`/workflows/${workflow.id}/edit`)}
 *   onDuplicate={() => duplicateWorkflow(workflow.id)}
 *   onDelete={() => deleteWorkflow(workflow.id)}
 * />
 * ```
 */
export function WorkflowCard({
  workflow,
  lastRunAt,
  onRun,
  onEdit,
  onDuplicate,
  onDelete,
  className,
}: WorkflowCardProps) {
  const { id, name, status, stages, tags, updatedAt } = workflow;

  const stageCount = stages?.length ?? 0;
  const statusCfg = STATUS_CONFIG[status];

  // Tags: show up to 3, then "+N more"
  const visibleTags = tags.slice(0, 3);
  const overflowCount = tags.length - visibleTags.length;

  // Prevent action button clicks from bubbling to the card Link
  const stopProp = (e: React.MouseEvent) => e.stopPropagation();

  return (
    <article
      aria-label={`Workflow: ${name}`}
      className={cn(
        'group relative rounded-xl border bg-card shadow-sm',
        'transition-shadow duration-200 hover:shadow-md',
        className
      )}
    >
      {/* Card body — entire area is a navigation target */}
      <Link
        href={`/workflows/${id}`}
        className="block p-5 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded-xl"
        aria-label={`View details for ${name}`}
      >
        {/* Header: icon + name + status badge */}
        <div className="flex items-start gap-3">
          {/* Workflow icon container */}
          <div
            className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-500 dark:bg-indigo-500/15 dark:text-indigo-400"
            aria-hidden="true"
          >
            <GitBranch className="h-5 w-5" />
          </div>

          {/* Name + status */}
          <div className="min-w-0 flex-1">
            <h3 className="text-base font-semibold leading-snug text-foreground line-clamp-2">
              {name}
            </h3>
          </div>

          {/* Status badge — top-right */}
          <Badge
            variant="outline"
            className={cn('flex-shrink-0 text-xs font-medium', statusCfg.className)}
          >
            {statusCfg.label}
          </Badge>
        </div>

        {/* Metadata row: stage count + last run */}
        <p className="mt-3 text-sm text-muted-foreground">
          <span className="font-medium text-foreground">
            {stageCount} {stageCount === 1 ? 'stage' : 'stages'}
          </span>
          {' | '}
          <span className="inline-flex items-center gap-1">
            <Clock className="inline h-3 w-3 align-middle" aria-hidden="true" />
            {formatLastRun(lastRunAt)}
          </span>
        </p>

        {/* Tags */}
        {tags.length > 0 && (
          <ul
            role="list"
            aria-label="Tags"
            className="mt-3 flex flex-wrap gap-1.5"
          >
            {visibleTags.map((tag) => (
              <li key={tag} role="listitem">
                <Badge
                  variant="outline"
                  className="text-[11px] font-normal px-2 py-0.5 text-muted-foreground"
                >
                  {tag}
                </Badge>
              </li>
            ))}
            {overflowCount > 0 && (
              <li role="listitem">
                <Badge
                  variant="outline"
                  className="text-[11px] font-normal px-2 py-0.5 text-muted-foreground"
                >
                  +{overflowCount} more
                </Badge>
              </li>
            )}
          </ul>
        )}

        {/* Footer metadata: created by / updated */}
        <p className="mt-3 text-xs text-muted-foreground flex items-center gap-1">
          <CalendarDays className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
          <span>Updated {formatUpdated(updatedAt)}</span>
        </p>
      </Link>

      {/* Action bar — sits below the link so clicks don't navigate */}
      <div
        className="flex items-center gap-1.5 border-t px-5 py-3"
        onClick={stopProp}
      >
        {/* Run — primary action */}
        <Button
          size="sm"
          className="h-8 gap-1.5 bg-indigo-600 px-3 text-xs font-medium text-white hover:bg-indigo-700 focus-visible:ring-indigo-500"
          onClick={onRun}
          disabled={!onRun || status === 'archived' || status === 'deprecated'}
          aria-label={`Run workflow: ${name}`}
        >
          <Play className="h-3.5 w-3.5 fill-current" aria-hidden="true" />
          Run
        </Button>

        {/* Edit */}
        <Button
          size="sm"
          variant="ghost"
          className="h-8 gap-1.5 px-3 text-xs font-medium"
          onClick={onEdit}
          disabled={!onEdit}
          aria-label={`Edit workflow: ${name}`}
        >
          <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
          Edit
        </Button>

        {/* Spacer */}
        <div className="flex-1" />

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
    </article>
  );
}

// ---------------------------------------------------------------------------
// WorkflowCardSkeleton
// ---------------------------------------------------------------------------

/**
 * Loading skeleton for WorkflowCard — matches the card's visual footprint
 * so the grid doesn't jump when data loads.
 */
export function WorkflowCardSkeleton() {
  return (
    <div className="rounded-xl border bg-card shadow-sm animate-pulse">
      <div className="p-5 space-y-3">
        {/* Header */}
        <div className="flex items-start gap-3">
          <div className="h-10 w-10 flex-shrink-0 rounded-lg bg-muted" />
          <div className="flex-1 space-y-2">
            <div className="h-4 w-3/4 rounded bg-muted" />
            <div className="h-3 w-1/2 rounded bg-muted" />
          </div>
          <div className="h-5 w-16 rounded-full bg-muted" />
        </div>
        {/* Metadata */}
        <div className="h-3 w-1/2 rounded bg-muted" />
        {/* Tags */}
        <div className="flex gap-1.5">
          <div className="h-5 w-12 rounded-full bg-muted" />
          <div className="h-5 w-16 rounded-full bg-muted" />
          <div className="h-5 w-10 rounded-full bg-muted" />
        </div>
        {/* Footer */}
        <div className="h-3 w-1/3 rounded bg-muted" />
      </div>
      {/* Action bar */}
      <div className="flex gap-2 border-t px-5 py-3">
        <div className="h-8 w-16 rounded-md bg-muted" />
        <div className="h-8 w-16 rounded-md bg-muted" />
        <div className="ml-auto h-8 w-8 rounded-md bg-muted" />
      </div>
    </div>
  );
}
