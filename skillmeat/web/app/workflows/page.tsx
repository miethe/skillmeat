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
import { GitBranch, Plus, SearchX, Trash2, Play, Tag, Copy, Download, CheckSquare } from 'lucide-react';
import { PageHeader } from '@/components/shared/page-header';
import { BulkActionBar } from '@/components/shared';
import { WorkflowCard, WorkflowCardSkeleton } from '@/components/workflow/workflow-card';
import { WorkflowListItem, WorkflowListItemSkeleton } from '@/components/workflow/workflow-list-item';
import { WorkflowToolbar } from '@/components/workflow/workflow-toolbar';
import { WorkflowDetailModal } from '@/components/workflow/workflow-detail-modal';
import { ExecutionDetailModal } from '@/components/workflow/execution-detail-modal';
import { Button } from '@/components/ui/button';
import { useWorkflows, useDeleteWorkflow, useDuplicateWorkflow, useMultiSelect } from '@/hooks';
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
  const [selectionMode, setSelectionMode] = useState(false);

  // Modal state
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);
  const [selectedExecutionId, setSelectedExecutionId] = useState<string | null>(null);
  const [executionWorkflowId, setExecutionWorkflowId] = useState<string>('');

  // ── Data ─────────────────────────────────────────────────────────────────
  const { data, isLoading, isError } = useWorkflows(filters);
  const workflows = data?.items ?? [];

  // ── Multi-select ──────────────────────────────────────────────────────────
  const {
    isSelected,
    toggleSelection,
    selectAll,
    clearSelection,
    hasSelection,
    selectedCount,
    isAllSelected,
  } = useMultiSelect(workflows);

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

  const handleToggleSelectionMode = useCallback(() => {
    setSelectionMode((prev) => {
      if (prev) clearSelection();
      return !prev;
    });
  }, [clearSelection]);

  const handleBulkDelete = useCallback(async () => {
    const selectedWorkflows = workflows.filter((wf) => isSelected(wf.id));
    const names = selectedWorkflows.map((wf) => wf.name).join(', ');
    const confirmed = window.confirm(
      `Delete ${selectedCount} workflow${selectedCount === 1 ? '' : 's'} (${names})?\n\nThis action cannot be undone.`
    );
    if (!confirmed) return;

    for (const wf of selectedWorkflows) {
      try {
        await deleteWorkflow.mutateAsync(wf.id);
      } catch (err) {
        console.error('[WorkflowsPage] Bulk delete failed for:', wf.id, err);
      }
    }
    clearSelection();
    setSelectionMode(false);
  }, [workflows, isSelected, selectedCount, deleteWorkflow, clearSelection]);

  const handleBulkRun = useCallback(() => {
    const selectedWorkflows = workflows.filter((wf) => isSelected(wf.id));
    for (const wf of selectedWorkflows) {
      handleRun(wf.id, wf.name);
    }
    clearSelection();
    setSelectionMode(false);
  }, [workflows, isSelected, handleRun, clearSelection]);

  const handleBulkPlaceholder = useCallback((action: string) => {
    // Placeholder for future bulk actions
    console.log(`[WorkflowsPage] Bulk ${action} requested — coming soon`);
  }, []);

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
            onClick={selectionMode ? undefined : () => handleWorkflowClick(workflow.id)}
            onRun={() => handleRun(workflow.id, workflow.name)}
            onEdit={() => handleEdit(workflow.id)}
            onDuplicate={() => handleDuplicate(workflow.id)}
            onDelete={() => handleDelete(workflow.id, workflow.name)}
            selectionMode={selectionMode}
            isSelected={isSelected(workflow.id)}
            onToggleSelect={() => toggleSelection(workflow.id)}
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
              onClick={selectionMode ? undefined : () => handleWorkflowClick(workflow.id)}
              onRun={() => handleRun(workflow.id, workflow.name)}
              onEdit={() => handleEdit(workflow.id)}
              onDuplicate={() => handleDuplicate(workflow.id)}
              onDelete={() => handleDelete(workflow.id, workflow.name)}
              selectionMode={selectionMode}
              isSelected={isSelected(workflow.id)}
              onToggleSelect={() => toggleSelection(workflow.id)}
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
      <div className="flex items-center gap-2">
        <div className="flex-1">
          <WorkflowToolbar
            filters={filters}
            onFiltersChange={setFilters}
            view={view}
            onViewChange={setView}
          />
        </div>
        {/* Selection mode controls */}
        {!isEmpty && !isLoading && !isError && (
          <div className="flex items-center gap-2 flex-shrink-0">
            {selectionMode && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-9 text-sm"
                  onClick={selectAll}
                  disabled={isAllSelected}
                >
                  Select All
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-9 text-sm"
                  onClick={clearSelection}
                  disabled={!hasSelection}
                >
                  Select None
                </Button>
              </>
            )}
            <Button
              variant={selectionMode ? 'secondary' : 'outline'}
              size="sm"
              className="h-9 gap-1.5 text-sm"
              onClick={handleToggleSelectionMode}
              aria-pressed={selectionMode}
              aria-label={selectionMode ? 'Exit selection mode' : 'Enter selection mode'}
            >
              <CheckSquare className="h-4 w-4" aria-hidden="true" />
              {selectionMode ? 'Done' : 'Select'}
            </Button>
          </div>
        )}
      </div>

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

      {/* Bulk action bar — slides up when items are selected */}
      <BulkActionBar
        selectedCount={selectedCount}
        hasSelection={selectionMode && hasSelection}
        onClearSelection={clearSelection}
        actions={[
          {
            id: 'delete',
            label: 'Delete',
            icon: <Trash2 className="h-3.5 w-3.5" />,
            variant: 'destructive',
            onClick: handleBulkDelete,
          },
          {
            id: 'run',
            label: 'Run',
            icon: <Play className="h-3.5 w-3.5 fill-current" />,
            variant: 'default',
            onClick: handleBulkRun,
          },
          {
            id: 'tag',
            label: 'Add Tags',
            icon: <Tag className="h-3.5 w-3.5" />,
            variant: 'outline',
            onClick: () => handleBulkPlaceholder('tag'),
          },
          {
            id: 'duplicate',
            label: 'Duplicate',
            icon: <Copy className="h-3.5 w-3.5" />,
            variant: 'outline',
            onClick: () => handleBulkPlaceholder('duplicate'),
          },
          {
            id: 'export',
            label: 'Export',
            icon: <Download className="h-3.5 w-3.5" />,
            variant: 'outline',
            onClick: () => handleBulkPlaceholder('export'),
          },
        ]}
      />
    </div>
  );
}
