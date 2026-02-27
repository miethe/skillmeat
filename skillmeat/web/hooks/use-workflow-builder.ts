/**
 * Workflow Builder State Management
 *
 * useReducer-based local state hook for the Workflow Builder page.
 * Manages the in-progress working copy of a workflow definition until
 * the user explicitly saves via useCreateWorkflow / useUpdateWorkflow.
 *
 * State never touches the server until save is invoked. All mutations
 * set isDirty=true so the builder top bar can show the unsaved indicator.
 *
 * @see docs/project_plans/design/workflow-orchestration-ui-spec.md §6.4
 */

import { useCallback, useReducer } from 'react';
import type {
  ContextPolicy,
  CreateWorkflowRequest,
  UpdateWorkflowRequest,
  Workflow,
  WorkflowParameter,
  WorkflowStage,
} from '@/types/workflow';

// ============================================================================
// BuilderState
// ============================================================================

export interface BuilderState {
  /** Human-readable display name of the workflow. */
  name: string;
  /** Multi-line description of the workflow's purpose. */
  description: string;
  /** Ordered list of stage definitions. Mutated by ADD/UPDATE/REMOVE/REORDER. */
  stages: WorkflowStage[];
  /**
   * Named parameter declarations.
   * Stored as an array to preserve insertion order in the builder UI.
   * Serialised to Record<string, WorkflowParameter> for API requests.
   */
  parameters: WorkflowParameter[];
  /** Searchable tag list. */
  tags: string[];
  /** Workflow-level global context policy applied to all stages by default. */
  contextPolicy: ContextPolicy;
  /**
   * Zero-based index of the stage currently being edited.
   * null when no stage editor is open.
   */
  selectedStageIndex: number | null;
  /** Whether the stage editor slide-over panel is visible. */
  isEditorOpen: boolean;
  /** True when local state has diverged from the last saved (or initial) state. */
  isDirty: boolean;
  /** True during the async save mutation. Drives button loading state. */
  isSaving: boolean;
  /**
   * Original server-fetched workflow when in edit mode.
   * null in create mode.
   * Used to compute change diffs and to reset on discard.
   */
  originalWorkflow: Workflow | null;
}

// ============================================================================
// BuilderAction (discriminated union)
// ============================================================================

/** Set the workflow display name. */
interface SetNameAction {
  type: 'SET_NAME';
  name: string;
}

/** Set the workflow description. */
interface SetDescriptionAction {
  type: 'SET_DESCRIPTION';
  description: string;
}

/**
 * Insert a stage into the list.
 * When atIndex is provided the stage is inserted before that index.
 * When omitted the stage is appended to the end.
 */
interface AddStageAction {
  type: 'ADD_STAGE';
  stage: WorkflowStage;
  atIndex?: number;
}

/** Replace the stage at the given index with the updated stage value. */
interface UpdateStageAction {
  type: 'UPDATE_STAGE';
  index: number;
  stage: WorkflowStage;
}

/** Remove the stage at the given index. Clears selection if that stage is selected. */
interface RemoveStageAction {
  type: 'REMOVE_STAGE';
  index: number;
}

/**
 * Move a stage from fromIndex to toIndex.
 * Implements array-splice semantics: the element at fromIndex is removed
 * then re-inserted at toIndex (computed on the reduced array).
 */
interface ReorderStagesAction {
  type: 'REORDER_STAGES';
  fromIndex: number;
  toIndex: number;
}

/**
 * Set the selected stage index.
 * Pass null to deselect without closing the editor.
 */
interface SelectStageAction {
  type: 'SELECT_STAGE';
  index: number | null;
}

/** Open or close the stage editor slide-over panel. */
interface ToggleEditorAction {
  type: 'TOGGLE_EDITOR';
  open: boolean;
}

/** Replace the current tag list. */
interface SetTagsAction {
  type: 'SET_TAGS';
  tags: string[];
}

/** Replace the current parameter list. */
interface SetParametersAction {
  type: 'SET_PARAMETERS';
  parameters: WorkflowParameter[];
}

/** Update the workflow-level context policy. */
interface SetContextPolicyAction {
  type: 'SET_CONTEXT_POLICY';
  policy: ContextPolicy;
}

/**
 * Mark the current state as saved.
 * Clears isDirty and isSaving.
 */
interface MarkSavedAction {
  type: 'MARK_SAVED';
}

/** Toggle isSaving to track async save mutations. */
interface SetSavingAction {
  type: 'SET_SAVING';
  isSaving: boolean;
}

/**
 * Populate the builder from an existing server-fetched workflow.
 * Used when entering edit mode (/workflows/[id]/edit).
 * Sets isDirty=false and stores the workflow as originalWorkflow.
 */
interface LoadWorkflowAction {
  type: 'LOAD_WORKFLOW';
  workflow: Workflow;
}

export type BuilderAction =
  | SetNameAction
  | SetDescriptionAction
  | AddStageAction
  | UpdateStageAction
  | RemoveStageAction
  | ReorderStagesAction
  | SelectStageAction
  | ToggleEditorAction
  | SetTagsAction
  | SetParametersAction
  | SetContextPolicyAction
  | MarkSavedAction
  | SetSavingAction
  | LoadWorkflowAction;

// ============================================================================
// Initial state factory
// ============================================================================

const DEFAULT_CONTEXT_POLICY: ContextPolicy = {
  modules: [],
  inheritGlobal: true,
};

function makeEmptyState(): BuilderState {
  return {
    name: '',
    description: '',
    stages: [],
    parameters: [],
    tags: [],
    contextPolicy: DEFAULT_CONTEXT_POLICY,
    selectedStageIndex: null,
    isEditorOpen: false,
    isDirty: false,
    isSaving: false,
    originalWorkflow: null,
  };
}

/**
 * Derive initial BuilderState from an existing Workflow.
 * Parameters arrive from the server as Record<string, WorkflowParameter>;
 * we convert to an array preserving Object.entries() order.
 */
function stateFromWorkflow(workflow: Workflow): BuilderState {
  return {
    name: workflow.name,
    description: workflow.description ?? '',
    stages: workflow.stages ?? [],
    parameters: Object.values(workflow.parameters ?? {}),
    tags: workflow.tags ?? [],
    contextPolicy:
      workflow.contextPolicy != null
        ? {
            modules: workflow.contextPolicy.globalModules ?? [],
            inheritGlobal: true,
          }
        : DEFAULT_CONTEXT_POLICY,
    selectedStageIndex: null,
    isEditorOpen: false,
    isDirty: false,
    isSaving: false,
    originalWorkflow: workflow,
  };
}

// ============================================================================
// Reducer
// ============================================================================

export function builderReducer(state: BuilderState, action: BuilderAction): BuilderState {
  switch (action.type) {
    case 'SET_NAME':
      return { ...state, name: action.name, isDirty: true };

    case 'SET_DESCRIPTION':
      return { ...state, description: action.description, isDirty: true };

    case 'ADD_STAGE': {
      const { stage, atIndex } = action;
      let nextStages: WorkflowStage[];
      if (atIndex !== undefined && atIndex >= 0 && atIndex <= state.stages.length) {
        nextStages = [
          ...state.stages.slice(0, atIndex),
          stage,
          ...state.stages.slice(atIndex),
        ];
      } else {
        nextStages = [...state.stages, stage];
      }
      return { ...state, stages: nextStages, isDirty: true };
    }

    case 'UPDATE_STAGE': {
      if (action.index < 0 || action.index >= state.stages.length) return state;
      const nextStages = state.stages.map((s, i) => (i === action.index ? action.stage : s));
      return { ...state, stages: nextStages, isDirty: true };
    }

    case 'REMOVE_STAGE': {
      if (action.index < 0 || action.index >= state.stages.length) return state;
      const nextStages = state.stages.filter((_, i) => i !== action.index);
      // Clear selection when the removed stage was selected
      let nextSelectedIndex = state.selectedStageIndex;
      if (state.selectedStageIndex === action.index) {
        nextSelectedIndex = null;
      } else if (
        state.selectedStageIndex !== null &&
        state.selectedStageIndex > action.index
      ) {
        // Shift selection index down when a preceding stage was removed
        nextSelectedIndex = state.selectedStageIndex - 1;
      }
      return {
        ...state,
        stages: nextStages,
        selectedStageIndex: nextSelectedIndex,
        isDirty: true,
      };
    }

    case 'REORDER_STAGES': {
      const { fromIndex, toIndex } = action;
      const len = state.stages.length;
      if (
        fromIndex === toIndex ||
        fromIndex < 0 ||
        fromIndex >= len ||
        toIndex < 0 ||
        toIndex >= len
      ) {
        return state;
      }
      const nextStages = [...state.stages];
      // splice returns T[] — assert non-null since bounds are validated above
      const removed = nextStages.splice(fromIndex, 1)[0] as WorkflowStage;
      nextStages.splice(toIndex, 0, removed);

      // Keep selectedStageIndex tracking the same logical stage after reorder
      let nextSelectedIndex = state.selectedStageIndex;
      if (state.selectedStageIndex !== null) {
        if (state.selectedStageIndex === fromIndex) {
          nextSelectedIndex = toIndex;
        } else if (
          fromIndex < toIndex &&
          state.selectedStageIndex > fromIndex &&
          state.selectedStageIndex <= toIndex
        ) {
          nextSelectedIndex = state.selectedStageIndex - 1;
        } else if (
          fromIndex > toIndex &&
          state.selectedStageIndex >= toIndex &&
          state.selectedStageIndex < fromIndex
        ) {
          nextSelectedIndex = state.selectedStageIndex + 1;
        }
      }

      return {
        ...state,
        stages: nextStages,
        selectedStageIndex: nextSelectedIndex,
        isDirty: true,
      };
    }

    case 'SELECT_STAGE':
      return { ...state, selectedStageIndex: action.index };

    case 'TOGGLE_EDITOR':
      return { ...state, isEditorOpen: action.open };

    case 'SET_TAGS':
      return { ...state, tags: action.tags, isDirty: true };

    case 'SET_PARAMETERS':
      return { ...state, parameters: action.parameters, isDirty: true };

    case 'SET_CONTEXT_POLICY':
      return { ...state, contextPolicy: action.policy, isDirty: true };

    case 'MARK_SAVED':
      return { ...state, isDirty: false, isSaving: false };

    case 'SET_SAVING':
      return { ...state, isSaving: action.isSaving };

    case 'LOAD_WORKFLOW':
      return stateFromWorkflow(action.workflow);

    default:
      return state;
  }
}

// ============================================================================
// Temp ID counter for new stages
// ============================================================================

let _tempIdCounter = 0;

/**
 * Generate a temporary client-side stage ID.
 * The backend assigns the real UUID on persist; this is only used locally
 * in the builder to key React lists before the first save.
 */
function generateTempStageId(): string {
  _tempIdCounter += 1;
  return `temp-stage-${Date.now()}-${_tempIdCounter}`;
}

// ============================================================================
// Hook return type
// ============================================================================

export interface UseWorkflowBuilderReturn {
  /** Current builder state snapshot. */
  state: BuilderState;
  /** Dispatch a BuilderAction to mutate local state. */
  dispatch: React.Dispatch<BuilderAction>;
  /**
   * Factory that produces a new WorkflowStage pre-filled with sensible defaults.
   * The caller may pass partial overrides before dispatching ADD_STAGE.
   */
  createNewStage: (overrides?: Partial<WorkflowStage>) => WorkflowStage;
  /**
   * Serialise current builder state into a CreateWorkflowRequest.
   *
   * Note: The API requires YAML (yamlContent) rather than a structured payload.
   * This helper produces a minimal JSON stub that callers should convert to YAML
   * or pass directly to the YAML-generating utility in lib/api/workflows.ts.
   *
   * The returned object satisfies CreateWorkflowRequest shape so TypeScript
   * consumers can verify structural compatibility without a runtime YAML dep here.
   */
  toCreateRequest: () => CreateWorkflowRequest;
  /**
   * Serialise current builder state into an UpdateWorkflowRequest.
   * Identical to toCreateRequest but typed as a partial update.
   */
  toUpdateRequest: () => UpdateWorkflowRequest;
}

// ============================================================================
// Hook
// ============================================================================

/**
 * useWorkflowBuilder — Workflow Builder page state manager.
 *
 * @param existingWorkflow Pass the server-fetched Workflow when in edit mode.
 *   Omit or pass undefined when creating a new workflow.
 *
 * @example — Create mode
 * ```tsx
 * const { state, dispatch, createNewStage } = useWorkflowBuilder();
 * ```
 *
 * @example — Edit mode
 * ```tsx
 * const { data: workflow } = useWorkflow(id);
 * const builder = useWorkflowBuilder(workflow);
 * ```
 */
export function useWorkflowBuilder(existingWorkflow?: Workflow): UseWorkflowBuilderReturn {
  const [state, dispatch] = useReducer(
    builderReducer,
    existingWorkflow,
    (wf) => (wf ? stateFromWorkflow(wf) : makeEmptyState()),
  );

  // -------------------------------------------------------------------------
  // createNewStage
  // -------------------------------------------------------------------------

  const createNewStage = useCallback((overrides?: Partial<WorkflowStage>): WorkflowStage => {
    const nextOrder = state.stages.length;
    return {
      id: generateTempStageId(),
      stageIdRef: `stage-${nextOrder + 1}`,
      name: `Stage ${nextOrder + 1}`,
      description: '',
      orderIndex: nextOrder,
      stageType: 'agent',
      dependsOn: [],
      inputs: {},
      outputs: {},
      ...overrides,
    } satisfies WorkflowStage;
  }, [state.stages.length]);

  // -------------------------------------------------------------------------
  // toCreateRequest
  // -------------------------------------------------------------------------

  const toCreateRequest = useCallback((): CreateWorkflowRequest => {
    // Convert parameters array back to Record<string, WorkflowParameter>
    // We reconstruct parameter names from the description or fall back to
    // positional keys; the caller is expected to populate meaningful names.
    const parametersRecord: Record<string, WorkflowParameter> = {};
    state.parameters.forEach((p, i) => {
      const key = (p.description ?? `param${i + 1}`)
        .toLowerCase()
        .replace(/\s+/g, '_')
        .replace(/[^a-z0-9_]/g, '');
      parametersRecord[key || `param${i + 1}`] = p;
    });

    // Build a minimal structured representation that mirrors the SWDL schema.
    // The actual yamlContent must be generated by the API layer (lib/api/workflows.ts)
    // using a YAML serialiser. We produce a JSON-stringified placeholder here that
    // callers can replace with a real YAML string before sending to the server.
    const swdlPayload = {
      name: state.name,
      description: state.description || undefined,
      version: '1.0.0',
      tags: state.tags.length > 0 ? state.tags : undefined,
      stages: state.stages.map((stage, i) => ({
        id: stage.stageIdRef,
        name: stage.name,
        description: stage.description,
        type: stage.stageType,
        order_index: i,
        depends_on: stage.dependsOn,
        roles: stage.roles,
        inputs: stage.inputs,
        outputs: stage.outputs,
        context: stage.context,
        error_policy: stage.errorPolicy,
        handoff: stage.handoff,
        gate: stage.gate,
        ui: stage.ui,
      })),
      parameters:
        Object.keys(parametersRecord).length > 0 ? parametersRecord : undefined,
      context_policy:
        state.contextPolicy.modules.length > 0
          ? {
              global_modules: state.contextPolicy.modules,
            }
          : undefined,
    };

    return {
      yamlContent: JSON.stringify(swdlPayload, null, 2),
    };
  }, [state]);

  // -------------------------------------------------------------------------
  // toUpdateRequest
  // -------------------------------------------------------------------------

  const toUpdateRequest = useCallback((): UpdateWorkflowRequest => {
    return toCreateRequest();
  }, [toCreateRequest]);

  return {
    state,
    dispatch,
    createNewStage,
    toCreateRequest,
    toUpdateRequest,
  };
}
