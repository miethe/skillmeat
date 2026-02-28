'use client';

/**
 * WorkflowDetailModal
 *
 * Dialog-based modal for inspecting a workflow definition in-place.
 * Mirrors the content of the WorkflowDetailPage (stages timeline,
 * execution history, settings) without requiring a full navigation.
 *
 * Three tabs:
 *   - Stages     — vertical timeline with StageCard + StageConnector
 *   - Executions — recent run history with status, timing, duration
 *   - Settings   — workflow metadata (description, tags, parameters,
 *                  context policy, error policy, version)
 *
 * Cross-linking:
 *   - "Open Full Page" button navigates to /workflows/{id}
 *   - Clicking an execution row calls onExecutionClick(executionId)
 */

import * as React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Play,
  Pencil,
  MoreHorizontal,
  Copy,
  Trash2,
  GitBranch,
  Clock,
  Tag,
  Settings2,
  List,
  History,
  CheckCircle2,
  XCircle,
  Loader2,
  PauseCircle,
  Ban,
  Timer,
  ShieldAlert,
  AlertCircle,
  CalendarDays,
  RefreshCw,
  ExternalLink,
  ChevronRight,
} from 'lucide-react';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

import { TabNavigation } from '@/components/shared/tab-navigation';
import { StageCard } from '@/components/workflow/stage-card';
import { StageConnector } from '@/components/workflow/stage-connector';
import { RunWorkflowDialog } from '@/components/workflow/run-workflow-dialog';

import { useWorkflow, useWorkflowExecutions } from '@/hooks';
import type {
  Workflow,
  WorkflowStatus,
  WorkflowExecution,
  ExecutionStatus,
} from '@/types/workflow';
import {
  WORKFLOW_STATUS_META,
  EXECUTION_STATUS_META,
} from '@/types/workflow';

// ============================================================================
// Props interface
// ============================================================================

export interface WorkflowDetailModalProps {
  /** Workflow ID to load. null means the modal is closed. */
  workflowId: string | null;
  /** Controlled open state. */
  open: boolean;
  /** Called when the modal should close. */
  onClose: () => void;
  /**
   * Called when the user clicks an execution row.
   * Use this to open an ExecutionDetailModal or navigate to the execution page.
   */
  onExecutionClick?: (executionId: string) => void;
}

// ============================================================================
// Tab definitions
// ============================================================================

const TABS = [
  { value: 'stages', label: 'Stages', icon: List },
  { value: 'executions', label: 'Executions', icon: History },
  { value: 'settings', label: 'Settings', icon: Settings2 },
];

// ============================================================================
// Status badge variants
// ============================================================================

const WORKFLOW_STATUS_VARIANT: Record<
  WorkflowStatus,
  'default' | 'secondary' | 'outline' | 'destructive'
> = {
  active: 'default',
  draft: 'secondary',
  archived: 'outline',
  deprecated: 'outline',
};

// ============================================================================
// WorkflowStatusBadge
// ============================================================================

function WorkflowStatusBadge({ status }: { status: WorkflowStatus }) {
  const meta = WORKFLOW_STATUS_META[status];
  return (
    <Badge
      variant={WORKFLOW_STATUS_VARIANT[status]}
      className={cn(
        'shrink-0 capitalize',
        status === 'active' &&
          'border-green-500/30 bg-green-500/15 text-green-600 dark:text-green-400',
        status === 'draft' &&
          'border-yellow-500/30 bg-yellow-500/15 text-yellow-600 dark:text-yellow-400',
        status === 'archived' && 'text-muted-foreground',
        status === 'deprecated' &&
          'border-orange-500/30 bg-orange-500/15 text-orange-600 dark:text-orange-400'
      )}
      aria-label={`Workflow status: ${meta.label}`}
    >
      {meta.label}
    </Badge>
  );
}

// ============================================================================
// ExecutionStatusIcon
// ============================================================================

function ExecutionStatusIcon({ status }: { status: ExecutionStatus }) {
  const meta = EXECUTION_STATUS_META[status];
  const baseClass = cn('h-4 w-4 shrink-0', meta.colorClass);

  switch (status) {
    case 'completed':
      return <CheckCircle2 className={baseClass} aria-hidden="true" />;
    case 'failed':
      return <XCircle className={baseClass} aria-hidden="true" />;
    case 'running':
      return (
        <Loader2
          className={cn(baseClass, 'animate-spin')}
          aria-hidden="true"
        />
      );
    case 'pending':
      return <Timer className={baseClass} aria-hidden="true" />;
    case 'cancelled':
      return <Ban className={baseClass} aria-hidden="true" />;
    case 'paused':
      return <PauseCircle className={baseClass} aria-hidden="true" />;
    case 'waiting_for_approval':
      return <ShieldAlert className={baseClass} aria-hidden="true" />;
    default:
      return <AlertCircle className={baseClass} aria-hidden="true" />;
  }
}

// ============================================================================
// Formatters
// ============================================================================

function formatDuration(ms: number | undefined): string {
  if (ms === undefined || ms === null) return '—';
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes === 0) return `${seconds}s`;
  return `${minutes}m ${seconds}s`;
}

function formatRelativeTime(iso: string | undefined): string {
  if (!iso) return '—';
  const date = new Date(iso);
  const now = Date.now();
  const diffMs = now - date.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  const diffHours = Math.floor(diffMin / 60);
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays > 0) return `${diffDays}d ago`;
  if (diffHours > 0) return `${diffHours}h ago`;
  if (diffMin > 0) return `${diffMin}m ago`;
  return 'just now';
}

// ============================================================================
// Loading skeleton
// ============================================================================

function ModalSkeleton() {
  return (
    <div
      className="space-y-5 p-6"
      aria-busy="true"
      aria-label="Loading workflow detail"
    >
      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-5 w-14 rounded-full" />
        </div>
        <Skeleton className="h-4 w-72" />
      </div>

      {/* Tab bar */}
      <Skeleton className="h-9 w-full" />

      {/* Content */}
      <div className="space-y-3 pt-2">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-20 w-full rounded-lg" />
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Error state (inline, within the modal)
// ============================================================================

function ModalError({
  workflowId,
  onRetry,
}: {
  workflowId: string;
  onRetry: () => void;
}) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-8 text-center"
      role="alert"
    >
      <AlertCircle
        className="h-8 w-8 text-destructive"
        aria-hidden="true"
      />
      <p className="text-sm font-medium text-destructive">
        Failed to load workflow
      </p>
      <p className="text-xs text-muted-foreground">
        Could not find workflow with ID:{' '}
        <code className="font-mono">{workflowId}</code>
      </p>
      <Button
        variant="outline"
        size="sm"
        onClick={onRetry}
        className="gap-1.5"
      >
        <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
        Retry
      </Button>
    </div>
  );
}

// ============================================================================
// StagesTab
// ============================================================================

function StagesTab({ workflow }: { workflow: Workflow }) {
  const stages = [...(workflow.stages ?? [])].sort(
    (a, b) => a.orderIndex - b.orderIndex
  );

  if (stages.length === 0) {
    return (
      <div
        className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16 text-center"
        role="status"
      >
        <List
          className="mb-3 h-8 w-8 text-muted-foreground/40"
          aria-hidden="true"
        />
        <p className="text-sm text-muted-foreground">No stages defined</p>
      </div>
    );
  }

  return (
    <div
      className="flex flex-col items-center py-4"
      role="list"
      aria-label={`Workflow stages — ${stages.length} stage${stages.length !== 1 ? 's' : ''}`}
    >
      {stages.map((stage, idx) => (
        <React.Fragment key={stage.id}>
          <div role="listitem" className="w-full max-w-xl">
            <StageCard stage={stage} index={idx} mode="readonly" />
          </div>
          {idx < stages.length - 1 && (
            <StageConnector
              showAddButton={false}
              variant="sequential"
              aria-hidden="true"
            />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

// ============================================================================
// ExecutionsTab
// ============================================================================

function ExecutionsTab({
  workflowId,
  onExecutionClick,
}: {
  workflowId: string;
  onExecutionClick?: (executionId: string) => void;
}) {
  const {
    data: executions,
    isLoading,
    error,
    refetch,
  } = useWorkflowExecutions({
    workflowId,
    sortBy: 'started_at',
    sortOrder: 'desc',
    limit: 20,
  });

  if (isLoading) {
    return (
      <div
        className="space-y-3 py-4"
        aria-busy="true"
        aria-label="Loading executions"
      >
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-16 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="rounded-lg border border-destructive/30 bg-destructive/5 p-6 text-center"
        role="alert"
      >
        <p className="text-sm font-medium text-destructive">
          Failed to load executions
        </p>
        <Button
          variant="outline"
          size="sm"
          className="mt-3 gap-1.5"
          onClick={() => refetch()}
        >
          <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
          Retry
        </Button>
      </div>
    );
  }

  if (!executions || executions.length === 0) {
    return (
      <div
        className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16 text-center"
        role="status"
      >
        <History
          className="mb-3 h-8 w-8 text-muted-foreground/40"
          aria-hidden="true"
        />
        <p className="text-sm text-muted-foreground">No executions yet</p>
        <p className="mt-1 text-xs text-muted-foreground/60">
          Run the workflow to see execution history.
        </p>
      </div>
    );
  }

  return (
    <div className="py-4">
      <ul className="space-y-2" aria-label="Workflow execution history">
        {executions.map((execution: WorkflowExecution) => {
          const meta = EXECUTION_STATUS_META[execution.status];
          const isClickable = !!onExecutionClick;

          return (
            <li key={execution.id}>
              <button
                type="button"
                onClick={
                  isClickable
                    ? () => onExecutionClick(execution.id)
                    : undefined
                }
                disabled={!isClickable}
                className={cn(
                  'relative w-full overflow-hidden rounded-lg border bg-card px-4 py-3 text-left text-sm transition-colors',
                  isClickable
                    ? 'cursor-pointer hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1'
                    : 'cursor-default'
                )}
                aria-label={`Execution ${meta.label}, started ${formatRelativeTime(execution.startedAt)}, duration ${formatDuration(execution.durationMs)}${isClickable ? '. Click to view details.' : ''}`}
              >
                <div className="flex items-center gap-4">
                  {/* Status icon */}
                  <ExecutionStatusIcon status={execution.status} />

                  {/* Status label + trigger */}
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={cn('font-medium', meta.colorClass)}>
                        {meta.label}
                      </span>
                      <Badge variant="outline" className="text-xs">
                        {execution.trigger}
                      </Badge>
                    </div>
                    {execution.errorMessage && (
                      <p className="mt-0.5 truncate text-xs text-muted-foreground">
                        {execution.errorMessage}
                      </p>
                    )}
                  </div>

                  {/* Timing */}
                  <div
                    className="flex shrink-0 flex-col items-end gap-0.5 text-xs text-muted-foreground"
                  >
                    <span className="flex items-center gap-1">
                      <CalendarDays className="h-3 w-3" aria-hidden="true" />
                      {formatRelativeTime(execution.startedAt)}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" aria-hidden="true" />
                      {formatDuration(execution.durationMs)}
                    </span>
                  </div>

                  {/* Chevron affordance when clickable */}
                  {isClickable && (
                    <ChevronRight
                      className="h-4 w-4 shrink-0 text-muted-foreground/50"
                      aria-hidden="true"
                    />
                  )}
                </div>

                {/* Progress bar — running executions only */}
                {execution.status === 'running' && (
                  <div
                    className="absolute bottom-0 left-0 right-0 h-0.5 overflow-hidden rounded-b-lg bg-muted"
                    aria-hidden="true"
                  >
                    <div
                      className="h-full bg-blue-500 transition-all duration-300"
                      style={{ width: `${execution.progressPct}%` }}
                    />
                  </div>
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

// ============================================================================
// SettingsTab helpers
// ============================================================================

function SettingsSection({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-2">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {label}
      </h3>
      <div className="rounded-lg border bg-card p-4">{children}</div>
    </section>
  );
}

function SettingsRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-1.5 text-sm">
      <dt className="shrink-0 text-muted-foreground">{label}</dt>
      <dd className="text-right font-medium">{children}</dd>
    </div>
  );
}

// ============================================================================
// SettingsTab
// ============================================================================

function SettingsTab({ workflow }: { workflow: Workflow }) {
  const hasParameters = Object.keys(workflow.parameters ?? {}).length > 0;
  const hasTags = (workflow.tags ?? []).length > 0;
  const hasContextPolicy =
    workflow.contextPolicy &&
    (workflow.contextPolicy.globalModules.length > 0 ||
      workflow.contextPolicy.memory);
  const hasErrorPolicy = !!workflow.errorPolicy;

  return (
    <div className="space-y-5 py-4">
      {/* General */}
      <SettingsSection label="General">
        <dl className="divide-y divide-border/50">
          <SettingsRow label="Version">
            <code className="font-mono text-xs">{workflow.version}</code>
          </SettingsRow>
          <SettingsRow label="Status">
            <WorkflowStatusBadge status={workflow.status} />
          </SettingsRow>
          <SettingsRow label="UUID">
            <code className="font-mono text-xs text-muted-foreground">
              {workflow.uuid}
            </code>
          </SettingsRow>
          <SettingsRow label="Created">
            <time
              dateTime={workflow.createdAt}
              className="font-normal text-muted-foreground"
            >
              {new Date(workflow.createdAt).toLocaleDateString(undefined, {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
              })}
            </time>
          </SettingsRow>
          <SettingsRow label="Updated">
            <time
              dateTime={workflow.updatedAt}
              className="font-normal text-muted-foreground"
            >
              {new Date(workflow.updatedAt).toLocaleDateString(undefined, {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
              })}
            </time>
          </SettingsRow>
        </dl>
      </SettingsSection>

      {/* Description */}
      {workflow.description && (
        <SettingsSection label="Description">
          <p className="text-sm leading-relaxed text-muted-foreground">
            {workflow.description}
          </p>
        </SettingsSection>
      )}

      {/* Tags */}
      {hasTags && (
        <SettingsSection label="Tags">
          <div
            className="flex flex-wrap gap-2"
            role="list"
            aria-label="Workflow tags"
          >
            {workflow.tags.map((tag) => (
              <Badge
                key={tag}
                variant="outline"
                role="listitem"
                className="gap-1"
              >
                <Tag className="h-3 w-3" aria-hidden="true" />
                {tag}
              </Badge>
            ))}
          </div>
        </SettingsSection>
      )}

      {/* Parameters */}
      {hasParameters && (
        <SettingsSection label="Parameters">
          <dl className="divide-y divide-border/50">
            {Object.entries(workflow.parameters).map(([key, param]) => (
              <div key={key} className="py-2 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <dt className="font-mono text-xs font-medium">{key}</dt>
                  <dd className="flex items-center gap-1.5">
                    <Badge variant="secondary" className="text-xs">
                      {param.type}
                    </Badge>
                    {param.required && (
                      <Badge
                        variant="outline"
                        className="border-red-500/30 text-xs text-red-500"
                      >
                        required
                      </Badge>
                    )}
                  </dd>
                </div>
                {param.description && (
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {param.description}
                  </p>
                )}
                {param.defaultValue !== undefined && (
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Default:{' '}
                    <code className="font-mono">
                      {String(param.defaultValue)}
                    </code>
                  </p>
                )}
              </div>
            ))}
          </dl>
        </SettingsSection>
      )}

      {/* Context Policy */}
      {hasContextPolicy && (
        <SettingsSection label="Context Policy">
          <dl className="divide-y divide-border/50">
            {(workflow.contextPolicy!.globalModules ?? []).length > 0 && (
              <div className="py-2">
                <dt className="mb-1.5 text-xs text-muted-foreground">
                  Global modules
                </dt>
                <dd className="flex flex-wrap gap-1.5">
                  {workflow.contextPolicy!.globalModules.map((mod) => (
                    <Badge
                      key={mod}
                      variant="secondary"
                      className="font-mono text-xs"
                    >
                      {mod}
                    </Badge>
                  ))}
                </dd>
              </div>
            )}
            {workflow.contextPolicy?.memory && (
              <div className="space-y-1 py-2 text-xs text-muted-foreground">
                <dt className="font-medium text-foreground">
                  Memory injection
                </dt>
                <dd>
                  Project scope:{' '}
                  {workflow.contextPolicy.memory.projectScope}
                </dd>
                <dd>
                  Min confidence:{' '}
                  {workflow.contextPolicy.memory.minConfidence}
                </dd>
                <dd>
                  Max tokens: {workflow.contextPolicy.memory.maxTokens}
                </dd>
              </div>
            )}
          </dl>
        </SettingsSection>
      )}

      {/* Error Policy */}
      {hasErrorPolicy && (
        <SettingsSection label="Error Policy">
          <dl className="divide-y divide-border/50">
            <SettingsRow label="On stage failure">
              <Badge variant="secondary" className="text-xs">
                {workflow.errorPolicy!.onStageFailure}
              </Badge>
            </SettingsRow>
            {workflow.errorPolicy?.defaultRetry && (
              <>
                <SettingsRow label="Max attempts">
                  {workflow.errorPolicy.defaultRetry.maxAttempts}
                </SettingsRow>
                <SettingsRow label="Initial interval">
                  {workflow.errorPolicy.defaultRetry.initialInterval}
                </SettingsRow>
                <SettingsRow label="Max interval">
                  {workflow.errorPolicy.defaultRetry.maxInterval}
                </SettingsRow>
              </>
            )}
          </dl>
        </SettingsSection>
      )}
    </div>
  );
}

// ============================================================================
// WorkflowModalContent — inner content loaded after data is available
// ============================================================================

function WorkflowModalContent({
  workflow,
  activeTab,
  setActiveTab,
  onClose,
  onExecutionClick,
}: {
  workflow: Workflow;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onClose: () => void;
  onExecutionClick?: (executionId: string) => void;
}) {
  const router = useRouter();
  const [runDialogOpen, setRunDialogOpen] = React.useState(false);

  const handleEdit = () => {
    onClose();
    router.push(`/workflows/${workflow.id}/edit`);
  };

  const handleDuplicate = () => {
    // Placeholder — wire to useDuplicateWorkflow mutation when ready
  };

  const handleDelete = () => {
    // Placeholder — wire to useDeleteWorkflow mutation + confirmation dialog when ready
  };

  return (
    <>
      {/* ---- Dialog header ---- */}
      <DialogHeader className="shrink-0 border-b px-6 pb-4 pt-6">
        <div className="flex items-start justify-between gap-4">
          {/* Title + status */}
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <GitBranch
                className="h-5 w-5 shrink-0 text-muted-foreground"
                aria-hidden="true"
              />
              <DialogTitle className="truncate text-lg font-semibold leading-tight">
                {workflow.name}
              </DialogTitle>
              <WorkflowStatusBadge status={workflow.status} />
            </div>
            {workflow.description && (
              <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                {workflow.description}
              </p>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex shrink-0 items-center gap-2">
            {/* Open full page */}
            <Link
              href={`/workflows/${workflow.id}`}
              onClick={onClose}
              aria-label={`Open full page for ${workflow.name}`}
            >
              <Button variant="ghost" size="sm" className="gap-1.5">
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                Open
              </Button>
            </Link>

            {/* Run — only when active */}
            {workflow.status === 'active' && (
              <Button
                size="sm"
                className="gap-1.5"
                onClick={() => setRunDialogOpen(true)}
                aria-label={`Run workflow: ${workflow.name}`}
              >
                <Play className="h-3.5 w-3.5" aria-hidden="true" />
                Run
              </Button>
            )}

            {/* Edit */}
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={handleEdit}
              aria-label={`Edit workflow: ${workflow.name}`}
            >
              <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
              Edit
            </Button>

            {/* Three-dot menu */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  aria-label="More workflow actions"
                >
                  <MoreHorizontal className="h-4 w-4" aria-hidden="true" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  onClick={handleDuplicate}
                  className="gap-2"
                >
                  <Copy className="h-4 w-4" aria-hidden="true" />
                  Duplicate
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={handleDelete}
                  className="gap-2 text-destructive focus:text-destructive"
                >
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </DialogHeader>

      {/* ---- Tabbed content ---- */}
      <Tabs
        value={activeTab}
        onValueChange={setActiveTab}
        className="flex min-h-0 flex-1 flex-col"
      >
        <div className="shrink-0 px-6">
          <TabNavigation tabs={TABS} ariaLabel="Workflow detail sections" />
        </div>

        <ScrollArea className="flex-1 px-6">
          {/* Stages */}
          <TabsContent
            value="stages"
            role="tabpanel"
            aria-label="Workflow stages"
          >
            <StagesTab workflow={workflow} />
          </TabsContent>

          {/* Executions */}
          <TabsContent
            value="executions"
            role="tabpanel"
            aria-label="Execution history"
          >
            <ExecutionsTab
              workflowId={workflow.id}
              onExecutionClick={onExecutionClick}
            />
          </TabsContent>

          {/* Settings */}
          <TabsContent
            value="settings"
            role="tabpanel"
            aria-label="Workflow settings"
          >
            <SettingsTab workflow={workflow} />
          </TabsContent>
        </ScrollArea>
      </Tabs>

      {/* ---- RunWorkflowDialog (nested, separate Dialog) ---- */}
      <RunWorkflowDialog
        workflow={workflow}
        open={runDialogOpen}
        onClose={() => setRunDialogOpen(false)}
        onSuccess={(executionId) => {
          setRunDialogOpen(false);
          if (onExecutionClick) {
            onExecutionClick(executionId);
          }
        }}
      />
    </>
  );
}

// ============================================================================
// WorkflowDetailModal — public export
// ============================================================================

export function WorkflowDetailModal({
  workflowId,
  open,
  onClose,
  onExecutionClick,
}: WorkflowDetailModalProps) {
  const [activeTab, setActiveTab] = React.useState('stages');

  // Reset to Stages tab each time the modal opens for a (potentially different) workflow
  React.useEffect(() => {
    if (open) {
      setActiveTab('stages');
    }
  }, [open, workflowId]);

  // useWorkflow has `enabled: !!id` internally, so passing an empty string
  // when workflowId is null safely suppresses the query.
  const {
    data: workflow,
    isLoading,
    error,
    refetch,
  } = useWorkflow(workflowId ?? '');

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent
        className="flex max-h-[85vh] max-w-4xl flex-col gap-0 overflow-hidden p-0"
        aria-label={
          workflow ? `Workflow detail: ${workflow.name}` : 'Workflow detail'
        }
      >
        {isLoading ? (
          <ModalSkeleton />
        ) : error || (!isLoading && !workflow && workflowId) ? (
          <div className="p-6">
            <ModalError
              workflowId={workflowId ?? ''}
              onRetry={() => refetch()}
            />
          </div>
        ) : workflow ? (
          <WorkflowModalContent
            workflow={workflow}
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            onClose={onClose}
            onExecutionClick={onExecutionClick}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
