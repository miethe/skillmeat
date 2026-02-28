'use client';

/**
 * Workflow Library Page
 *
 * Full implementation of the workflow list view with grid/list toggle,
 * search/filter toolbar, loading skeletons, empty states, and card actions.
 */

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { GitBranch, Plus, SearchX } from 'lucide-react';
import { PageHeader } from '@/components/shared/page-header';
import { WorkflowCard, WorkflowCardSkeleton } from '@/components/workflow/workflow-card';
import { WorkflowListItem, WorkflowListItemSkeleton } from '@/components/workflow/workflow-list-item';
import { WorkflowToolbar } from '@/components/workflow/workflow-toolbar';
import { WorkflowDetailModal } from '@/components/workflow/workflow-detail-modal';
import { ExecutionDetailModal } from '@/components/workflow/execution-detail-modal';
import { Button } from '@/components/ui/button';
import { useWorkflows, useDeleteWorkflow, useDuplicateWorkflow } from '@/hooks';
import type { WorkflowFilters } from '@/types/workflow';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DEFAULT_FILTERS: WorkflowFilters = {
  sortBy: 'updated_at',
  sortOrder: 'desc',
};

const SKELETON_COUNT = 6;

// ---------------------------------------------------------------------------
// WorkflowsPage
// ---------------------------------------------------------------------------

export default function WorkflowsPage() {
  const router = useRouter();

  // ── State ────────────────────────────────────────────────────────────────
  const [filters, setFilters] = useState<WorkflowFilters>(DEFAULT_FILTERS);
  const [view, setView] = useState<'grid' | 'list'>('grid');

  // Modal state
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);
  const [selectedExecutionId, setSelectedExecutionId] = useState<string | null>(null);
  const [executionWorkflowId, setExecutionWorkflowId] = useState<string>('');

  // ── Data ─────────────────────────────────────────────────────────────────
  const { data, isLoading, isError } = useWorkflows(filters);
  const workflows = data?.items ?? [];

  const deleteWorkflow = useDeleteWorkflow();
  const duplicateWorkflow = useDuplicateWorkflow();

  // ── Derived state ─────────────────────────────────────────────────────────
  const hasActiveFilters = Boolean(filters.search || filters.status);
  const isEmpty = !isLoading && !isError && workflows.length === 0;
  const isEmptyFromFilters = isEmpty && hasActiveFilters;
  const isEmptyFromNoData = isEmpty && !hasActiveFilters;

  // ── Handlers ─────────────────────────────────────────────────────────────

  const handleClearFilters = useCallback(() => {
    setFilters(DEFAULT_FILTERS);
  }, []);

  const handleWorkflowClick = useCallback((workflowId: string) => {
    setSelectedWorkflowId(workflowId);
  }, []);

  const handleCloseWorkflowModal = useCallback(() => {
    setSelectedWorkflowId(null);
  }, []);

  const handleExecutionClick = useCallback((executionId: string) => {
    // Find which workflow this execution belongs to (it's the currently open workflow)
    setSelectedExecutionId(executionId);
    setExecutionWorkflowId(selectedWorkflowId ?? '');
  }, [selectedWorkflowId]);

  const handleCloseExecutionModal = useCallback(() => {
    setSelectedExecutionId(null);
  }, []);

  const handleExecutionWorkflowClick = useCallback((workflowId: string) => {
    // Close execution modal and open workflow modal
    setSelectedExecutionId(null);
    setSelectedWorkflowId(workflowId);
  }, []);

  const handleRun = useCallback((workflowId: string, workflowName: string) => {
    // Placeholder — RunWorkflowDialog will be wired in a later phase
    console.log('[WorkflowsPage] Run requested for:', workflowId, workflowName);
  }, []);

  const handleEdit = useCallback(
    (workflowId: string) => {
      router.push(`/workflows/${workflowId}/edit`);
    },
    [router]
  );

  const handleDuplicate = useCallback(
    async (workflowId: string) => {
      try {
        await duplicateWorkflow.mutateAsync({ id: workflowId });
      } catch (err) {
        console.error('[WorkflowsPage] Duplicate failed:', err);
      }
    },
    [duplicateWorkflow]
  );

  const handleDelete = useCallback(
    async (workflowId: string, workflowName: string) => {
      const confirmed = window.confirm(
        `Delete "${workflowName}"?\n\nThis action cannot be undone.`
      );
      if (!confirmed) return;

      try {
        await deleteWorkflow.mutateAsync(workflowId);
      } catch (err) {
        console.error('[WorkflowsPage] Delete failed:', err);
      }
    },
    [deleteWorkflow]
  );

  // ── Render helpers ────────────────────────────────────────────────────────

  function renderSkeletons() {
    if (view === 'grid') {
      return (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: SKELETON_COUNT }).map((_, i) => (
            <WorkflowCardSkeleton key={i} />
          ))}
        </div>
      );
    }

    return (
      <div className="rounded-lg border bg-card">
        <ul role="list" aria-label="Loading workflows" aria-busy="true">
          {Array.from({ length: SKELETON_COUNT }).map((_, i) => (
            <WorkflowListItemSkeleton key={i} />
          ))}
        </ul>
      </div>
    );
  }

  function renderEmptyFromFilters() {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-24 text-center">
        <SearchX
          className="mx-auto mb-4 h-12 w-12 text-muted-foreground/40"
          aria-hidden="true"
        />
        <h2 className="mb-1 text-base font-semibold text-foreground">
          No workflows match your filters
        </h2>
        <p className="mb-6 text-sm text-muted-foreground">
          Try broadening your search or clearing the active filters.
        </p>
        <Button variant="outline" size="sm" onClick={handleClearFilters}>
          Clear filters
        </Button>
      </div>
    );
  }

  function renderEmptyFromNoData() {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-24 text-center">
        <GitBranch
          className="mx-auto mb-4 h-12 w-12 text-muted-foreground/40"
          aria-hidden="true"
        />
        <h2 className="mb-1 text-base font-semibold text-foreground">No workflows yet</h2>
        <p className="mb-6 text-sm text-muted-foreground">
          Create your first workflow to start orchestrating your AI agents.
        </p>
        <Button asChild>
          <Link href="/workflows/new">
            <Plus className="mr-1.5 h-4 w-4" aria-hidden="true" />
            New Workflow
          </Link>
        </Button>
      </div>
    );
  }

  function renderGrid() {
    return (
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {workflows.map((workflow) => (
          <WorkflowCard
            key={workflow.id}
            workflow={workflow}
            onClick={() => handleWorkflowClick(workflow.id)}
            onRun={() => handleRun(workflow.id, workflow.name)}
            onEdit={() => handleEdit(workflow.id)}
            onDuplicate={() => handleDuplicate(workflow.id)}
            onDelete={() => handleDelete(workflow.id, workflow.name)}
          />
        ))}
      </div>
    );
  }

  function renderList() {
    return (
      <div className="rounded-lg border bg-card">
        <ul role="list" aria-label="Workflows">
          {workflows.map((workflow) => (
            <WorkflowListItem
              key={workflow.id}
              workflow={workflow}
              onClick={() => handleWorkflowClick(workflow.id)}
              onRun={() => handleRun(workflow.id, workflow.name)}
              onEdit={() => handleEdit(workflow.id)}
              onDuplicate={() => handleDuplicate(workflow.id)}
              onDelete={() => handleDelete(workflow.id, workflow.name)}
            />
          ))}
        </ul>
      </div>
    );
  }

  // ── Main render ───────────────────────────────────────────────────────────

  return (
    <div className="space-y-6 p-6">
      {/* Page header */}
      <PageHeader
        title="Workflows"
        description="Browse, run, and manage your orchestration workflows."
        icon={<GitBranch className="h-6 w-6" />}
        actions={
          <Button asChild>
            <Link href="/workflows/new">
              <Plus className="mr-1.5 h-4 w-4" aria-hidden="true" />
              New Workflow
            </Link>
          </Button>
        }
      />

      {/* Toolbar: search, status filter, sort, view toggle */}
      <WorkflowToolbar
        filters={filters}
        onFiltersChange={setFilters}
        view={view}
        onViewChange={setView}
      />

      {/* Content area */}
      <main aria-label="Workflow list">
        {isLoading && renderSkeletons()}

        {isError && (
          <div
            role="alert"
            className="flex items-center justify-center rounded-lg border border-destructive/30 bg-destructive/5 py-12 text-center"
          >
            <p className="text-sm text-destructive">
              Failed to load workflows. Please try refreshing the page.
            </p>
          </div>
        )}

        {!isLoading && !isError && isEmptyFromFilters && renderEmptyFromFilters()}
        {!isLoading && !isError && isEmptyFromNoData && renderEmptyFromNoData()}

        {!isLoading && !isError && !isEmpty && view === 'grid' && renderGrid()}
        {!isLoading && !isError && !isEmpty && view === 'list' && renderList()}
      </main>

      {/* Detail Modals */}
      <WorkflowDetailModal
        workflowId={selectedWorkflowId}
        open={selectedWorkflowId !== null}
        onClose={handleCloseWorkflowModal}
        onExecutionClick={handleExecutionClick}
      />

      <ExecutionDetailModal
        executionId={selectedExecutionId}
        workflowId={executionWorkflowId}
        open={selectedExecutionId !== null}
        onClose={handleCloseExecutionModal}
        onWorkflowClick={handleExecutionWorkflowClick}
      />
    </div>
  );
}
