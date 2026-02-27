'use client';

/**
 * WorkflowBuilderView — Shared builder component used by both the
 * /workflows/new and /workflows/[id]/edit pages.
 *
 * Composes:
 *   - BuilderTopBar (sticky header with name editing + save actions)
 *   - BuilderSidebar (right-hand metadata panel, hidden on mobile)
 *   - BuilderDndContext (drag-sortable stage canvas)
 *   - StageEditor (slide-over panel for per-stage configuration)
 *
 * All state lives in useWorkflowBuilder. Mutations are fired via
 * useCreateWorkflow / useUpdateWorkflow. The component guards against
 * accidental navigation when there are unsaved changes.
 *
 * @example — Create mode (no existingWorkflow)
 * ```tsx
 * <WorkflowBuilderView />
 * ```
 *
 * @example — Edit mode
 * ```tsx
 * <WorkflowBuilderView existingWorkflow={workflow} />
 * ```
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { Plus } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { BuilderTopBar } from '@/components/workflow/builder-top-bar';
import { BuilderSidebar } from '@/components/workflow/builder-sidebar';
import { BuilderDndContext } from '@/components/workflow/builder-dnd-context';
import { StageEditor } from '@/components/workflow/stage-editor';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import {
  useWorkflowBuilder,
  useCreateWorkflow,
  useUpdateWorkflow,
} from '@/hooks';
import type { Workflow, WorkflowStage } from '@/types/workflow';

// ============================================================================
// Types
// ============================================================================

export interface WorkflowBuilderViewProps {
  /**
   * Pass the server-fetched Workflow when in edit mode.
   * Omit (or pass undefined) when creating a new workflow.
   */
  existingWorkflow?: Workflow;
}

// ============================================================================
// Empty state — shown when no stages have been added yet
// ============================================================================

interface EmptyCanvasProps {
  onAddStage: () => void;
}

function EmptyCanvas({ onAddStage }: EmptyCanvasProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-4',
        'rounded-xl border border-dashed border-border/60',
        'py-20 px-8 text-center',
        'bg-muted/20',
      )}
      aria-label="Empty workflow canvas"
    >
      {/* Icon */}
      <div
        className={cn(
          'flex h-12 w-12 items-center justify-center rounded-full',
          'bg-muted/60 text-muted-foreground/60',
        )}
        aria-hidden="true"
      >
        <Plus className="h-6 w-6" />
      </div>

      {/* Copy */}
      <div className="space-y-1">
        <p className="text-sm font-medium text-foreground/80">No stages yet</p>
        <p className="text-xs text-muted-foreground">
          Add your first stage to start building the workflow.
        </p>
      </div>

      {/* CTA */}
      <Button
        variant="outline"
        size="sm"
        onClick={onAddStage}
        className="gap-1.5"
      >
        <Plus className="h-3.5 w-3.5" aria-hidden="true" />
        Add your first stage
      </Button>
    </div>
  );
}

// ============================================================================
// WorkflowBuilderView
// ============================================================================

export function WorkflowBuilderView({ existingWorkflow }: WorkflowBuilderViewProps) {
  const router = useRouter();

  // ── Builder state ─────────────────────────────────────────────────────────

  const { state, dispatch, createNewStage, toCreateRequest, toUpdateRequest } =
    useWorkflowBuilder(existingWorkflow);

  // ── Mutations ─────────────────────────────────────────────────────────────

  const createMutation = useCreateWorkflow();
  const updateMutation = useUpdateWorkflow();

  const isMutating = createMutation.isPending || updateMutation.isPending;

  // ── Unsaved changes guard (beforeunload) ──────────────────────────────────

  React.useEffect(() => {
    if (!state.isDirty) return;

    function handleBeforeUnload(e: BeforeUnloadEvent) {
      e.preventDefault();
      // Modern browsers show their own message; setting returnValue triggers the dialog.
      e.returnValue = '';
    }

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [state.isDirty]);

  // ── Handlers ──────────────────────────────────────────────────────────────

  function handleAddStage(atIndex?: number) {
    const stage = createNewStage();
    dispatch({ type: 'ADD_STAGE', stage, atIndex });
  }

  function handleSelectStage(index: number) {
    dispatch({ type: 'SELECT_STAGE', index });
    dispatch({ type: 'TOGGLE_EDITOR', open: true });
  }

  function handleEditStage(index: number) {
    dispatch({ type: 'SELECT_STAGE', index });
    dispatch({ type: 'TOGGLE_EDITOR', open: true });
  }

  function handleDeleteStage(index: number) {
    dispatch({ type: 'REMOVE_STAGE', index });
  }

  function handleReorder(fromIndex: number, toIndex: number) {
    dispatch({ type: 'REORDER_STAGES', fromIndex, toIndex });
  }

  function handleTitleChange(index: number, title: string) {
    const stage = state.stages[index];
    if (!stage) return;
    dispatch({ type: 'UPDATE_STAGE', index, stage: { ...stage, name: title } });
  }

  function handleStageSave(updated: WorkflowStage) {
    if (state.selectedStageIndex === null) return;
    dispatch({
      type: 'UPDATE_STAGE',
      index: state.selectedStageIndex,
      stage: updated,
    });
    dispatch({ type: 'TOGGLE_EDITOR', open: false });
  }

  function handleCloseEditor() {
    dispatch({ type: 'TOGGLE_EDITOR', open: false });
  }

  // ── Save actions ──────────────────────────────────────────────────────────

  async function performSave(): Promise<Workflow | null> {
    dispatch({ type: 'SET_SAVING', isSaving: true });
    try {
      if (existingWorkflow) {
        const result = await updateMutation.mutateAsync({
          id: existingWorkflow.id,
          data: toUpdateRequest(),
        });
        dispatch({ type: 'MARK_SAVED' });
        return result;
      } else {
        const result = await createMutation.mutateAsync(toCreateRequest());
        dispatch({ type: 'MARK_SAVED' });
        return result;
      }
    } catch {
      dispatch({ type: 'SET_SAVING', isSaving: false });
      return null;
    }
  }

  async function handleSaveDraft() {
    await performSave();
  }

  async function handleSaveAndClose() {
    const result = await performSave();
    if (result) {
      router.push(`/workflows/${result.id}`);
    }
  }

  function handleBack() {
    if (state.isDirty) {
      const confirmed = window.confirm(
        'You have unsaved changes. Are you sure you want to leave without saving?'
      );
      if (!confirmed) return;
    }
    router.back();
  }

  // ── Selected stage for StageEditor ───────────────────────────────────────

  const selectedStage =
    state.selectedStageIndex !== null
      ? (state.stages[state.selectedStageIndex] ?? null)
      : null;

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div
      className="flex h-screen flex-col overflow-hidden bg-background"
      aria-label="Workflow builder"
    >
      {/* ── Top bar (sticky) ──────────────────────────────────────────────── */}
      <BuilderTopBar
        name={state.name}
        isDirty={state.isDirty}
        isSaving={state.isSaving || isMutating}
        onNameChange={(name) => dispatch({ type: 'SET_NAME', name })}
        onSaveDraft={handleSaveDraft}
        onSaveAndClose={handleSaveAndClose}
        onBack={handleBack}
      />

      {/* ── Main content row (canvas + sidebar) ─────────────────────────── */}
      <div className="flex min-h-0 flex-1 overflow-hidden">

        {/* ── Canvas (left, flex-1) ─────────────────────────────────────── */}
        <main
          className="flex min-w-0 flex-1 flex-col overflow-y-auto"
          aria-label="Workflow canvas"
        >
          <div className="mx-auto w-full max-w-2xl px-6 py-8">

            {state.stages.length === 0 ? (
              /* Empty state */
              <EmptyCanvas onAddStage={() => handleAddStage()} />
            ) : (
              /* Stage list with DnD */
              <BuilderDndContext
                stages={state.stages}
                selectedIndex={state.selectedStageIndex}
                onReorder={handleReorder}
                onSelectStage={handleSelectStage}
                onEditStage={handleEditStage}
                onDeleteStage={handleDeleteStage}
                onTitleChange={handleTitleChange}
                onAddStage={handleAddStage}
              >
                {/* "Add Stage" button at the bottom of the canvas */}
                <div className="pt-2">
                  <button
                    type="button"
                    onClick={() => handleAddStage()}
                    aria-label="Add stage to end of workflow"
                    className={cn(
                      'flex w-full items-center justify-center gap-2',
                      'rounded-lg border border-dashed border-border/60',
                      'py-3 text-sm font-medium',
                      'text-muted-foreground',
                      'transition-colors hover:border-primary/50 hover:text-primary hover:bg-primary/5',
                      'focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                    )}
                  >
                    <Plus className="h-4 w-4" aria-hidden="true" />
                    Add Stage
                  </button>
                </div>
              </BuilderDndContext>
            )}
          </div>
        </main>

        {/* ── Sidebar (right, w-80, hidden on mobile) ───────────────────── */}
        <BuilderSidebar
          name={state.name}
          description={state.description}
          tags={state.tags}
          contextPolicy={state.contextPolicy}
          parameters={state.parameters}
          onNameChange={(name) => dispatch({ type: 'SET_NAME', name })}
          onDescriptionChange={(description) =>
            dispatch({ type: 'SET_DESCRIPTION', description })
          }
          onTagsChange={(tags) => dispatch({ type: 'SET_TAGS', tags })}
          onContextPolicyChange={(policy) =>
            dispatch({ type: 'SET_CONTEXT_POLICY', policy })
          }
          onParametersChange={(parameters) =>
            dispatch({ type: 'SET_PARAMETERS', parameters })
          }
        />
      </div>

      {/* ── Stage editor slide-over ──────────────────────────────────────── */}
      <StageEditor
        stage={selectedStage}
        open={state.isEditorOpen && state.selectedStageIndex !== null}
        onClose={handleCloseEditor}
        onSave={handleStageSave}
      />
    </div>
  );
}

// ============================================================================
// Loading skeleton — used by the edit page while the workflow is fetching
// ============================================================================

export function WorkflowBuilderSkeleton() {
  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background">
      {/* Top bar skeleton */}
      <div className="flex items-center gap-3 border-b border-border px-4 py-2">
        <Skeleton className="h-8 w-8 rounded-md" />
        <Skeleton className="h-px w-px" />
        <Skeleton className="h-6 w-48 rounded" />
        <div className="ml-auto flex gap-2">
          <Skeleton className="h-8 w-24 rounded-md" />
          <Skeleton className="h-8 w-28 rounded-md" />
        </div>
      </div>
      {/* Canvas skeleton */}
      <div className="flex min-h-0 flex-1 overflow-hidden">
        <div className="flex min-w-0 flex-1 flex-col overflow-y-auto">
          <div className="mx-auto w-full max-w-2xl space-y-3 px-6 py-8">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-24 w-full rounded-lg" />
            ))}
          </div>
        </div>
        {/* Sidebar skeleton */}
        <div className="hidden md:flex w-80 shrink-0 flex-col border-l border-border/70">
          <div className="border-b border-border/70 px-4 py-3">
            <Skeleton className="h-4 w-24 rounded" />
          </div>
          <div className="space-y-4 p-4">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-8 w-full rounded-md" />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
