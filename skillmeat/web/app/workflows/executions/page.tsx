'use client';

/**
 * All Executions Page
 *
 * Global list of all workflow execution runs across all workflows.
 * Filterable by status, sortable by started date, with skeleton loading
 * and empty states.
 *
 * Features:
 * - Per-row quick action buttons (cancel, pause, resume, re-run)
 * - Multi-select checkboxes with hover-reveal behavior
 * - Select All / Clear Selection controls
 * - Floating bulk action bar for batch operations
 */

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ListChecks,
  SearchX,
  ChevronDown,
  ChevronUp,
  ArrowUpDown,
  Clock,
  Zap,
  GitBranch,
} from 'lucide-react';
import { PageHeader } from '@/components/shared/page-header';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useWorkflowExecutions } from '@/hooks';
import { useExecutionSelection } from '@/hooks/use-execution-selection';
import { ExecutionRowActions } from '@/components/workflow/execution-row-actions';
import { ExecutionBulkActions } from '@/components/workflow/execution-bulk-actions';
import type { ExecutionFilters, ExecutionStatus } from '@/types/workflow';
import { EXECUTION_STATUS_META } from '@/types/workflow';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const SKELETON_COUNT = 8;

const STATUS_OPTIONS: Array<{ value: ExecutionStatus | 'all'; label: string }> = [
  { value: 'all', label: 'All statuses' },
  { value: 'running', label: 'Running' },
  { value: 'pending', label: 'Pending' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
  { value: 'paused', label: 'Paused' },
  { value: 'cancelled', label: 'Cancelled' },
  { value: 'waiting_for_approval', label: 'Awaiting Approval' },
];

// Status badge variant mapping — derived from EXECUTION_STATUS_META colorClass
const STATUS_BADGE_STYLES: Record<ExecutionStatus, string> = {
  running:
    'bg-blue-500/10 text-blue-400 border-blue-500/20 hover:bg-blue-500/20',
  pending:
    'bg-slate-500/10 text-slate-400 border-slate-500/20 hover:bg-slate-500/20',
  completed:
    'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 hover:bg-emerald-500/20',
  failed:
    'bg-red-500/10 text-red-400 border-red-500/20 hover:bg-red-500/20',
  cancelled:
    'bg-zinc-500/10 text-zinc-400 border-zinc-500/20 hover:bg-zinc-500/20',
  paused:
    'bg-amber-500/10 text-amber-400 border-amber-500/20 hover:bg-amber-500/20',
  waiting_for_approval:
    'bg-violet-500/10 text-violet-400 border-violet-500/20 hover:bg-violet-500/20',
};

const TRIGGER_LABELS: Record<string, string> = {
  manual: 'Manual',
  api: 'API',
  schedule: 'Schedule',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatRelativeTime(isoString?: string): string {
  if (!isoString) return '—';
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);

  if (diffSecs < 60) return 'just now';
  if (diffSecs < 3600) return `${Math.floor(diffSecs / 60)}m ago`;
  if (diffSecs < 86400) return `${Math.floor(diffSecs / 3600)}h ago`;
  if (diffSecs < 604800) return `${Math.floor(diffSecs / 86400)}d ago`;
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function formatDuration(ms?: number): string {
  if (ms === undefined || ms === null) return '—';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  if (ms < 3_600_000) {
    const m = Math.floor(ms / 60_000);
    const s = Math.floor((ms % 60_000) / 1000);
    return s > 0 ? `${m}m ${s}s` : `${m}m`;
  }
  const h = Math.floor(ms / 3_600_000);
  const m = Math.floor((ms % 3_600_000) / 60_000);
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

function truncateId(id?: string | null): string {
  if (!id) return '—';
  return id.length > 8 ? id.slice(0, 8) : id;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: ExecutionStatus }) {
  const meta = EXECUTION_STATUS_META[status];
  const styleClass = STATUS_BADGE_STYLES[status];

  return (
    <Badge
      variant="outline"
      className={`font-mono text-[11px] tracking-wide ${styleClass}`}
    >
      {meta?.label ?? status}
    </Badge>
  );
}

function TableSkeleton({ showCheckbox }: { showCheckbox?: boolean }) {
  return (
    <>
      {Array.from({ length: SKELETON_COUNT }).map((_, i) => (
        <TableRow key={i} className="border-border/40">
          {showCheckbox && (
            <TableCell className="w-10">
              <Skeleton className="h-4 w-4 rounded-sm" />
            </TableCell>
          )}
          <TableCell>
            <Skeleton className="h-4 w-20" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-36" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-5 w-24 rounded-full" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-20" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-14" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-16" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-8 w-20" />
          </TableCell>
        </TableRow>
      ))}
    </>
  );
}

// ---------------------------------------------------------------------------
// AllExecutionsPage
// ---------------------------------------------------------------------------

export default function AllExecutionsPage() {
  const router = useRouter();

  // ── State ─────────────────────────────────────────────────────────────────
  const [statusFilter, setStatusFilter] = useState<ExecutionStatus | 'all'>('all');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const filters: ExecutionFilters = {
    ...(statusFilter !== 'all' && { status: statusFilter }),
    sortBy: 'started_at',
    sortOrder,
  };

  // ── Data ──────────────────────────────────────────────────────────────────
  const { data: executions, isLoading, isError } = useWorkflowExecutions(filters);
  const rows = executions ?? [];

  // ── Selection ─────────────────────────────────────────────────────────────
  const {
    isSelected,
    toggleSelection,
    selectAll,
    clearSelection,
    hasSelection,
    selectedCount,
    selectedExecutions,
    isAllSelected,
  } = useExecutionSelection(rows);

  // ── Derived ───────────────────────────────────────────────────────────────
  const isEmpty = !isLoading && !isError && rows.length === 0;
  const hasFilters = statusFilter !== 'all';

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handleRowClick = useCallback(
    (workflowId: string, executionId: string) => {
      router.push(`/workflows/${workflowId}/executions/${executionId}`);
    },
    [router]
  );

  const handleClearFilters = useCallback(() => {
    setStatusFilter('all');
  }, []);

  const toggleSort = useCallback(() => {
    setSortOrder((prev) => (prev === 'desc' ? 'asc' : 'desc'));
  }, []);

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <PageHeader
        title="All Executions"
        description="Monitor workflow runs across your entire collection"
        icon={<ListChecks className="h-6 w-6" />}
      />

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Status filter */}
        <Select
          value={statusFilter}
          onValueChange={(v) => setStatusFilter(v as ExecutionStatus | 'all')}
        >
          <SelectTrigger
            className="h-9 w-[180px] border-border/60 bg-muted/30 text-sm"
            aria-label="Filter by status"
          >
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Sort toggle */}
        <Button
          variant="outline"
          size="sm"
          onClick={toggleSort}
          className="h-9 border-border/60 bg-muted/30 gap-1.5 text-sm"
          aria-label={`Sort by started date, currently ${sortOrder === 'desc' ? 'newest first' : 'oldest first'}`}
        >
          {sortOrder === 'desc' ? (
            <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
          ) : (
            <ChevronUp className="h-3.5 w-3.5" aria-hidden="true" />
          )}
          {sortOrder === 'desc' ? 'Newest first' : 'Oldest first'}
        </Button>

        {/* Active filter indicator */}
        {hasFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClearFilters}
            className="h-9 text-sm text-muted-foreground hover:text-foreground"
          >
            Clear filters
          </Button>
        )}

        {/* Select All / Clear Selection — visible when items selected */}
        {hasSelection && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              {selectedCount} selected
            </span>
            {!isAllSelected && (
              <Button
                variant="ghost"
                size="sm"
                onClick={selectAll}
                className="h-8 text-xs text-muted-foreground hover:text-foreground px-2"
              >
                Select all ({rows.length})
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={clearSelection}
              className="h-8 text-xs text-muted-foreground hover:text-foreground px-2"
            >
              Clear selection
            </Button>
          </div>
        )}

        {/* Row count */}
        {!isLoading && !isError && rows.length > 0 && !hasSelection && (
          <span className="ml-auto font-mono text-xs text-muted-foreground">
            {rows.length} run{rows.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Main content */}
      <main aria-label="Execution list">
        {/* Error state */}
        {isError && (
          <div
            role="alert"
            className="flex items-center justify-center rounded-lg border border-destructive/30 bg-destructive/5 py-12 text-center"
          >
            <p className="text-sm text-destructive">
              Failed to load executions. Please try refreshing the page.
            </p>
          </div>
        )}

        {/* Empty state — no data */}
        {isEmpty && !hasFilters && (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-24 text-center">
            <ListChecks
              className="mx-auto mb-4 h-10 w-10 text-muted-foreground/30"
              aria-hidden="true"
            />
            <h2 className="mb-1 text-base font-semibold">No executions yet</h2>
            <p className="mb-6 max-w-xs text-sm text-muted-foreground">
              Run a workflow to see executions appear here.
            </p>
            <Button asChild variant="outline" size="sm">
              <Link href="/workflows">
                <GitBranch className="mr-1.5 h-4 w-4" aria-hidden="true" />
                Browse Workflows
              </Link>
            </Button>
          </div>
        )}

        {/* Empty state — filtered */}
        {isEmpty && hasFilters && (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-24 text-center">
            <SearchX
              className="mx-auto mb-4 h-10 w-10 text-muted-foreground/30"
              aria-hidden="true"
            />
            <h2 className="mb-1 text-base font-semibold">No executions found</h2>
            <p className="mb-6 text-sm text-muted-foreground">
              No runs match the current filter. Try a different status.
            </p>
            <Button variant="outline" size="sm" onClick={handleClearFilters}>
              Clear filters
            </Button>
          </div>
        )}

        {/* Table */}
        {(isLoading || rows.length > 0) && (
          <div className="rounded-lg border border-border/60 bg-card overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="border-border/40 bg-muted/20 hover:bg-muted/20">
                  {/* Checkbox column */}
                  <TableHead className="w-10 pl-4">
                    {rows.length > 0 && (
                      <Checkbox
                        checked={isAllSelected}
                        onCheckedChange={(checked) =>
                          checked ? selectAll() : clearSelection()
                        }
                        aria-label={isAllSelected ? 'Deselect all executions' : 'Select all executions'}
                        className="data-[state=checked]:border-primary"
                      />
                    )}
                  </TableHead>

                  <TableHead className="w-[100px] font-mono text-xs text-muted-foreground">
                    Run ID
                  </TableHead>
                  <TableHead className="text-xs text-muted-foreground">
                    Workflow
                  </TableHead>
                  <TableHead className="text-xs text-muted-foreground">
                    Status
                  </TableHead>
                  <TableHead className="text-xs text-muted-foreground">
                    <button
                      className="flex items-center gap-1 hover:text-foreground transition-colors"
                      onClick={toggleSort}
                      aria-label="Sort by started date"
                    >
                      Started
                      <ArrowUpDown className="h-3 w-3" aria-hidden="true" />
                    </button>
                  </TableHead>
                  <TableHead className="text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" aria-hidden="true" />
                      Duration
                    </span>
                  </TableHead>
                  <TableHead className="text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Zap className="h-3 w-3" aria-hidden="true" />
                      Trigger
                    </span>
                  </TableHead>
                  <TableHead className="text-xs text-muted-foreground text-right pr-4">
                    Actions
                  </TableHead>
                </TableRow>
              </TableHeader>

              <TableBody>
                {isLoading && <TableSkeleton showCheckbox />}

                {!isLoading &&
                  rows.map((execution) => {
                    const selected = isSelected(execution.id);

                    return (
                      <TableRow
                        key={execution.id}
                        className={`group cursor-pointer border-border/30 transition-colors hover:bg-muted/40 ${
                          selected ? 'bg-muted/25' : ''
                        }`}
                        onClick={() =>
                          handleRowClick(execution.workflowId, execution.id)
                        }
                        role="link"
                        aria-label={`View execution ${truncateId(execution.id)} for ${execution.workflowName ?? 'workflow'}`}
                        aria-selected={selected}
                      >
                        {/* Checkbox */}
                        <TableCell
                          className="pl-4 w-10"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <Checkbox
                            checked={selected}
                            onCheckedChange={() => toggleSelection(execution.id)}
                            aria-label={`Select execution ${truncateId(execution.id)}`}
                            className={`transition-opacity ${
                              hasSelection
                                ? 'opacity-100'
                                : 'opacity-0 group-hover:opacity-100'
                            }`}
                          />
                        </TableCell>

                        {/* Run ID */}
                        <TableCell className="font-mono text-xs text-muted-foreground">
                          <span className="rounded bg-muted/50 px-1.5 py-0.5">
                            {truncateId(execution.id)}
                          </span>
                        </TableCell>

                        {/* Workflow name */}
                        <TableCell>
                          {execution.workflowName ? (
                            <Link
                              href={`/workflows/${execution.workflowId}`}
                              className="text-sm font-medium hover:text-primary hover:underline"
                              onClick={(e) => e.stopPropagation()}
                            >
                              {execution.workflowName}
                            </Link>
                          ) : (
                            <span className="font-mono text-xs text-muted-foreground">
                              {truncateId(execution.workflowId)}
                            </span>
                          )}
                        </TableCell>

                        {/* Status */}
                        <TableCell>
                          <StatusBadge status={execution.status} />
                        </TableCell>

                        {/* Started */}
                        <TableCell className="text-sm text-muted-foreground">
                          {formatRelativeTime(execution.startedAt)}
                        </TableCell>

                        {/* Duration */}
                        <TableCell className="font-mono text-xs text-muted-foreground">
                          {formatDuration(execution.durationMs)}
                        </TableCell>

                        {/* Trigger */}
                        <TableCell className="text-xs text-muted-foreground">
                          {TRIGGER_LABELS[execution.trigger] ?? execution.trigger}
                        </TableCell>

                        {/* Actions */}
                        <TableCell
                          className="pr-4 text-right"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <ExecutionRowActions execution={execution} />
                        </TableCell>
                      </TableRow>
                    );
                  })}
              </TableBody>
            </Table>
          </div>
        )}
      </main>

      {/* Floating bulk action bar */}
      <ExecutionBulkActions
        selectedExecutions={selectedExecutions}
        onClearSelection={clearSelection}
      />
    </div>
  );
}
