'use client';

/**
 * Workflow Detail Page
 *
 * Displays full details for a single workflow definition:
 *   - Header with status badge, Run/Edit actions, and three-dot menu
 *   - Stages tab: read-only vertical timeline with StageCard + StageConnector
 *   - Executions tab: recent run history with status, timing, duration
 *   - Settings tab: workflow metadata (description, tags, parameters, context policy, version)
 *
 * Client component — uses interactive tabs and React Query (useWorkflow, useWorkflowExecutions).
 * Next.js 15 client component: use useParams() instead of awaiting params prop.
 */

import * as React from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
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
} from 'lucide-react';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent } from '@/components/ui/tabs';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

import { PageHeader } from '@/components/shared/page-header';
import { TabNavigation } from '@/components/shared/tab-navigation';
import { StageCard } from '@/components/workflow/stage-card';
import { StageConnector } from '@/components/workflow/stage-connector';

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
// Tab definitions
// ============================================================================

const TABS = [
  { value: 'stages', label: 'Stages', icon: List },
  { value: 'executions', label: 'Executions', icon: History },
  { value: 'settings', label: 'Settings', icon: Settings2 },
];

// ============================================================================
// Status badge helpers
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

function WorkflowStatusBadge({ status }: { status: WorkflowStatus }) {
  const meta = WORKFLOW_STATUS_META[status];
  return (
    <Badge
      variant={WORKFLOW_STATUS_VARIANT[status]}
      className={cn(
        'shrink-0 capitalize',
        status === 'active' && 'bg-green-500/15 text-green-600 dark:text-green-400 border-green-500/30',
        status === 'draft' && 'bg-yellow-500/15 text-yellow-600 dark:text-yellow-400 border-yellow-500/30',
        status === 'archived' && 'text-muted-foreground',
        status === 'deprecated' && 'bg-orange-500/15 text-orange-600 dark:text-orange-400 border-orange-500/30',
      )}
      aria-label={`Workflow status: ${meta.label}`}
    >
      {meta.label}
    </Badge>
  );
}

// ============================================================================
// Execution status icon helper
// ============================================================================

function ExecutionStatusIcon({ status }: { status: ExecutionStatus }) {
  const meta = EXECUTION_STATUS_META[status];
  const iconProps = { className: cn('h-4 w-4 shrink-0', meta.colorClass), 'aria-hidden': true as const };

  switch (status) {
    case 'completed':
      return <CheckCircle2 {...iconProps} />;
    case 'failed':
      return <XCircle {...iconProps} />;
    case 'running':
      return <Loader2 {...iconProps} className={cn(iconProps.className, 'animate-spin')} />;
    case 'pending':
      return <Timer {...iconProps} />;
    case 'cancelled':
      return <Ban {...iconProps} />;
    case 'paused':
      return <PauseCircle {...iconProps} />;
    case 'waiting_for_approval':
      return <ShieldAlert {...iconProps} />;
    default:
      return <AlertCircle {...iconProps} />;
  }
}

// ============================================================================
// Duration formatter
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

function WorkflowDetailSkeleton() {
  return (
    <div
      className="mx-auto max-w-4xl space-y-6 px-4 py-6 sm:px-6"
      aria-busy="true"
      aria-label="Loading workflow detail"
    >
      {/* Back nav skeleton */}
      <Skeleton className="h-5 w-28" />

      {/* Header skeleton */}
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <Skeleton className="h-8 w-56" />
          <Skeleton className="h-6 w-16 rounded-full" />
        </div>
        <Skeleton className="h-4 w-80" />
      </div>

      {/* Tab bar skeleton */}
      <Skeleton className="h-10 w-full" />

      {/* Content skeleton */}
      <div className="space-y-4 pt-4">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-24 w-full rounded-lg" />
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Error state
// ============================================================================

function WorkflowDetailError({ id, onRetry }: { id: string; onRetry: () => void }) {
  return (
    <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6">
      <nav aria-label="Breadcrumb" className="mb-6">
        <Link href="/workflows">
          <Button variant="ghost" size="sm" className="gap-1.5 pl-0">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Back to workflows
          </Button>
        </Link>
      </nav>
      <div
        className="rounded-lg border border-destructive/30 bg-destructive/5 p-8 text-center"
        role="alert"
      >
        <AlertCircle className="mx-auto mb-3 h-8 w-8 text-destructive" aria-hidden="true" />
        <p className="text-sm font-medium text-destructive">Failed to load workflow</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Could not find workflow with ID:{' '}
          <code className="font-mono">{id}</code>
        </p>
        <div className="mt-4 flex justify-center gap-3">
          <Button variant="outline" size="sm" onClick={onRetry} className="gap-1.5">
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            Retry
          </Button>
          <Link href="/workflows">
            <Button variant="ghost" size="sm">
              Go to workflows
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// 404 state
// ============================================================================

function WorkflowNotFound({ id }: { id: string }) {
  return (
    <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6">
      <nav aria-label="Breadcrumb" className="mb-6">
        <Link href="/workflows">
          <Button variant="ghost" size="sm" className="gap-1.5 pl-0">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Back to workflows
          </Button>
        </Link>
      </nav>
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-24 text-center">
        <GitBranch className="mb-3 h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
        <p className="text-sm font-medium">Workflow not found</p>
        <p className="mt-1 font-mono text-xs text-muted-foreground/60">{id}</p>
        <Link href="/workflows" className="mt-4">
          <Button variant="outline" size="sm">
            Back to workflows
          </Button>
        </Link>
      </div>
    </div>
  );
}

// ============================================================================
// Stages tab
// ============================================================================

function StagesTab({ workflow }: { workflow: Workflow }) {
  const stages = [...(workflow.stages ?? [])].sort((a, b) => a.orderIndex - b.orderIndex);

  if (stages.length === 0) {
    return (
      <div
        className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16 text-center"
        role="status"
      >
        <List className="mb-3 h-8 w-8 text-muted-foreground/40" aria-hidden="true" />
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
// Executions tab
// ============================================================================

function ExecutionsTab({ workflowId }: { workflowId: string }) {
  const { data: executions, isLoading, error, refetch } = useWorkflowExecutions({
    workflowId,
    sortBy: 'started_at',
    sortOrder: 'desc',
    limit: 20,
  });

  if (isLoading) {
    return (
      <div className="space-y-3 py-4" aria-busy="true" aria-label="Loading executions">
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
        <p className="text-sm font-medium text-destructive">Failed to load executions</p>
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
        <History className="mb-3 h-8 w-8 text-muted-foreground/40" aria-hidden="true" />
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
          return (
            <li
              key={execution.id}
              className="flex items-center gap-4 rounded-lg border bg-card px-4 py-3 text-sm transition-colors hover:bg-muted/40"
            >
              {/* Status icon */}
              <ExecutionStatusIcon status={execution.status} />

              {/* Status label + trigger */}
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={cn('font-medium', meta.colorClass)}>{meta.label}</span>
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
                className="flex flex-col items-end gap-0.5 text-xs text-muted-foreground shrink-0"
                aria-label={`Started ${execution.startedAt ? new Date(execution.startedAt).toLocaleString() : 'unknown'}`}
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

              {/* Progress bar — shown for running executions */}
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
            </li>
          );
        })}
      </ul>
    </div>
  );
}

// ============================================================================
// Settings tab
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

function SettingsRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 py-1.5 text-sm">
      <dt className="shrink-0 text-muted-foreground">{label}</dt>
      <dd className="text-right font-medium">{children}</dd>
    </div>
  );
}

function SettingsTab({ workflow }: { workflow: Workflow }) {
  const hasParameters = Object.keys(workflow.parameters ?? {}).length > 0;
  const hasTags = (workflow.tags ?? []).length > 0;
  const hasContextPolicy =
    workflow.contextPolicy &&
    (workflow.contextPolicy.globalModules.length > 0 || workflow.contextPolicy.memory);
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
            <code className="font-mono text-xs text-muted-foreground">{workflow.uuid}</code>
          </SettingsRow>
          <SettingsRow label="Created">
            <time dateTime={workflow.createdAt} className="text-muted-foreground font-normal">
              {new Date(workflow.createdAt).toLocaleDateString(undefined, {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
              })}
            </time>
          </SettingsRow>
          <SettingsRow label="Updated">
            <time dateTime={workflow.updatedAt} className="text-muted-foreground font-normal">
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
          <p className="text-sm text-muted-foreground leading-relaxed">{workflow.description}</p>
        </SettingsSection>
      )}

      {/* Tags */}
      {hasTags && (
        <SettingsSection label="Tags">
          <div className="flex flex-wrap gap-2" role="list" aria-label="Workflow tags">
            {workflow.tags.map((tag) => (
              <Badge key={tag} variant="outline" role="listitem" className="gap-1">
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
                      <Badge variant="outline" className="text-xs text-red-500 border-red-500/30">
                        required
                      </Badge>
                    )}
                  </dd>
                </div>
                {param.description && (
                  <p className="mt-0.5 text-xs text-muted-foreground">{param.description}</p>
                )}
                {param.defaultValue !== undefined && (
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Default:{' '}
                    <code className="font-mono">{String(param.defaultValue)}</code>
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
                <dt className="mb-1.5 text-xs text-muted-foreground">Global modules</dt>
                <dd className="flex flex-wrap gap-1.5">
                  {workflow.contextPolicy!.globalModules.map((mod) => (
                    <Badge key={mod} variant="secondary" className="font-mono text-xs">
                      {mod}
                    </Badge>
                  ))}
                </dd>
              </div>
            )}
            {workflow.contextPolicy?.memory && (
              <div className="py-2 text-xs text-muted-foreground space-y-1">
                <dt className="font-medium text-foreground">Memory injection</dt>
                <dd>Project scope: {workflow.contextPolicy.memory.projectScope}</dd>
                <dd>Min confidence: {workflow.contextPolicy.memory.minConfidence}</dd>
                <dd>Max tokens: {workflow.contextPolicy.memory.maxTokens}</dd>
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
// Main page component
// ============================================================================

export default function WorkflowDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = typeof params.id === 'string' ? params.id : (params.id?.[0] ?? '');

  const [activeTab, setActiveTab] = React.useState('stages');

  const {
    data: workflow,
    isLoading,
    error,
    refetch,
  } = useWorkflow(id);

  // ---- Loading ----
  if (isLoading) {
    return <WorkflowDetailSkeleton />;
  }

  // ---- Error ----
  if (error) {
    return <WorkflowDetailError id={id} onRetry={() => refetch()} />;
  }

  // ---- Not found ----
  if (!workflow) {
    return <WorkflowNotFound id={id} />;
  }

  // ---- Action handlers ----
  const handleEdit = () => router.push(`/workflows/${id}/edit`);
  const handleDuplicate = () => {
    // Placeholder — wire to useDuplicateWorkflow mutation when ready
  };
  const handleDelete = () => {
    // Placeholder — wire to useDeleteWorkflow mutation + confirmation dialog when ready
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6">
      {/* Back navigation */}
      <nav aria-label="Breadcrumb" className="mb-6">
        <Link href="/workflows">
          <Button variant="ghost" size="sm" className="gap-1.5 pl-0">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Back to workflows
          </Button>
        </Link>
      </nav>

      {/* Page header */}
      <PageHeader
        className="mb-6"
        icon={<GitBranch className="h-6 w-6" />}
        title={workflow.name}
        description={workflow.description}
        actions={
          <div className="flex items-center gap-2">
            {/* Status badge */}
            <WorkflowStatusBadge status={workflow.status} />

            {/* Run button — only when active */}
            {workflow.status === 'active' && (
              <Button
                size="sm"
                className="gap-1.5"
                aria-label={`Run workflow: ${workflow.name}`}
                disabled
                title="Run workflow (coming soon)"
              >
                <Play className="h-3.5 w-3.5" aria-hidden="true" />
                Run
              </Button>
            )}

            {/* Edit button */}
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
                <DropdownMenuItem onClick={handleDuplicate} className="gap-2">
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
        }
      />

      {/* Tabbed content */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabNavigation
          tabs={TABS}
          ariaLabel="Workflow detail sections"
        />

        {/* Stages tab */}
        <TabsContent value="stages" role="tabpanel" aria-label="Workflow stages">
          <StagesTab workflow={workflow} />
        </TabsContent>

        {/* Executions tab */}
        <TabsContent value="executions" role="tabpanel" aria-label="Execution history">
          <ExecutionsTab workflowId={workflow.id} />
        </TabsContent>

        {/* Settings tab */}
        <TabsContent value="settings" role="tabpanel" aria-label="Workflow settings">
          <SettingsTab workflow={workflow} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
