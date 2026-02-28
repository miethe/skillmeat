/**
 * Pure unit tests for builderReducer.
 *
 * No DOM, no React — just pure function verification.
 * Each describe block covers one or more action types.
 */

import { builderReducer } from '@/hooks/use-workflow-builder';
import type { BuilderState, BuilderAction } from '@/hooks/use-workflow-builder';
import type { Workflow, WorkflowStage } from '@/types/workflow';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeStage(overrides: Partial<WorkflowStage> = {}): WorkflowStage {
  return {
    id: `stage-${Math.random()}`,
    stageIdRef: 'stage-ref',
    name: 'Test Stage',
    orderIndex: 0,
    stageType: 'agent',
    dependsOn: [],
    inputs: {},
    outputs: {},
    ...overrides,
  };
}

const initialState: BuilderState = {
  name: '',
  description: '',
  stages: [],
  parameters: [],
  tags: [],
  contextPolicy: { modules: [], inheritGlobal: true },
  selectedStageIndex: null,
  isEditorOpen: false,
  isDirty: false,
  isSaving: false,
  originalWorkflow: null,
};

function stateWithStages(...stages: WorkflowStage[]): BuilderState {
  return { ...initialState, stages };
}

function dispatch(state: BuilderState, action: BuilderAction): BuilderState {
  return builderReducer(state, action);
}

// ---------------------------------------------------------------------------
// SET_NAME
// ---------------------------------------------------------------------------

describe('SET_NAME', () => {
  it('sets the workflow name', () => {
    const next = dispatch(initialState, { type: 'SET_NAME', name: 'My Workflow' });
    expect(next.name).toBe('My Workflow');
  });

  it('marks state as dirty', () => {
    const next = dispatch(initialState, { type: 'SET_NAME', name: 'x' });
    expect(next.isDirty).toBe(true);
  });

  it('does not mutate other state fields', () => {
    const prev = { ...initialState, description: 'Keep this' };
    const next = dispatch(prev, { type: 'SET_NAME', name: 'n' });
    expect(next.description).toBe('Keep this');
  });
});

// ---------------------------------------------------------------------------
// SET_DESCRIPTION
// ---------------------------------------------------------------------------

describe('SET_DESCRIPTION', () => {
  it('sets the description and marks dirty', () => {
    const next = dispatch(initialState, { type: 'SET_DESCRIPTION', description: 'Detailed desc' });
    expect(next.description).toBe('Detailed desc');
    expect(next.isDirty).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// ADD_STAGE
// ---------------------------------------------------------------------------

describe('ADD_STAGE', () => {
  const stageA = makeStage({ name: 'A', id: 'a' });
  const stageB = makeStage({ name: 'B', id: 'b' });

  it('appends a stage when atIndex is omitted', () => {
    const state = stateWithStages(stageA);
    const next = dispatch(state, { type: 'ADD_STAGE', stage: stageB });
    expect(next.stages).toHaveLength(2);
    expect(next.stages[1]).toBe(stageB);
  });

  it('inserts at the given atIndex', () => {
    const stageC = makeStage({ name: 'C', id: 'c' });
    const state = stateWithStages(stageA, stageB);
    const next = dispatch(state, { type: 'ADD_STAGE', stage: stageC, atIndex: 1 });
    expect(next.stages[0]).toBe(stageA);
    expect(next.stages[1]).toBe(stageC);
    expect(next.stages[2]).toBe(stageB);
  });

  it('appends when atIndex equals stages.length', () => {
    const state = stateWithStages(stageA);
    const next = dispatch(state, { type: 'ADD_STAGE', stage: stageB, atIndex: 1 });
    expect(next.stages).toHaveLength(2);
    expect(next.stages[1]).toBe(stageB);
  });

  it('appends when atIndex is out of bounds', () => {
    const state = stateWithStages(stageA);
    const next = dispatch(state, { type: 'ADD_STAGE', stage: stageB, atIndex: 99 });
    expect(next.stages[1]).toBe(stageB);
  });

  it('marks state dirty', () => {
    const next = dispatch(initialState, { type: 'ADD_STAGE', stage: stageA });
    expect(next.isDirty).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// REMOVE_STAGE
// ---------------------------------------------------------------------------

describe('REMOVE_STAGE', () => {
  const s0 = makeStage({ id: 's0', name: 'S0' });
  const s1 = makeStage({ id: 's1', name: 'S1' });
  const s2 = makeStage({ id: 's2', name: 'S2' });

  it('removes the stage at the given index', () => {
    const next = dispatch(stateWithStages(s0, s1, s2), { type: 'REMOVE_STAGE', index: 1 });
    expect(next.stages).toHaveLength(2);
    expect(next.stages[0]).toBe(s0);
    expect(next.stages[1]).toBe(s2);
  });

  it('clears selectedStageIndex when the selected stage is removed', () => {
    const state = { ...stateWithStages(s0, s1), selectedStageIndex: 1 };
    const next = dispatch(state, { type: 'REMOVE_STAGE', index: 1 });
    expect(next.selectedStageIndex).toBeNull();
  });

  it('shifts selectedStageIndex down when a preceding stage is removed', () => {
    const state = { ...stateWithStages(s0, s1, s2), selectedStageIndex: 2 };
    const next = dispatch(state, { type: 'REMOVE_STAGE', index: 0 });
    expect(next.selectedStageIndex).toBe(1);
  });

  it('preserves selectedStageIndex when a following stage is removed', () => {
    const state = { ...stateWithStages(s0, s1, s2), selectedStageIndex: 0 };
    const next = dispatch(state, { type: 'REMOVE_STAGE', index: 2 });
    expect(next.selectedStageIndex).toBe(0);
  });

  it('is a no-op for out-of-bounds index', () => {
    const state = stateWithStages(s0);
    const next = dispatch(state, { type: 'REMOVE_STAGE', index: 5 });
    expect(next.stages).toHaveLength(1);
  });

  it('marks state dirty', () => {
    const next = dispatch(stateWithStages(s0), { type: 'REMOVE_STAGE', index: 0 });
    expect(next.isDirty).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// REORDER_STAGES
// ---------------------------------------------------------------------------

describe('REORDER_STAGES', () => {
  const a = makeStage({ id: 'a', name: 'A' });
  const b = makeStage({ id: 'b', name: 'B' });
  const c = makeStage({ id: 'c', name: 'C' });

  it('moves stage from lower index to higher index', () => {
    // [A, B, C] → move A (0) to position 2 → [B, C, A]
    const next = dispatch(stateWithStages(a, b, c), { type: 'REORDER_STAGES', fromIndex: 0, toIndex: 2 });
    expect(next.stages.map((s) => s.name)).toEqual(['B', 'C', 'A']);
  });

  it('moves stage from higher index to lower index', () => {
    // [A, B, C] → move C (2) to position 0 → [C, A, B]
    const next = dispatch(stateWithStages(a, b, c), { type: 'REORDER_STAGES', fromIndex: 2, toIndex: 0 });
    expect(next.stages.map((s) => s.name)).toEqual(['C', 'A', 'B']);
  });

  it('is a no-op when fromIndex === toIndex', () => {
    const state = stateWithStages(a, b, c);
    const next = dispatch(state, { type: 'REORDER_STAGES', fromIndex: 1, toIndex: 1 });
    expect(next).toBe(state);
  });

  it('is a no-op for out-of-bounds indices', () => {
    const state = stateWithStages(a, b);
    const next = dispatch(state, { type: 'REORDER_STAGES', fromIndex: 0, toIndex: 99 });
    expect(next).toBe(state);
  });

  it('tracks selected stage through a reorder (selected stage moves)', () => {
    // [A, B, C], selected=0 (A). Move A to index 2 → [B, C, A], selected should be 2.
    const state = { ...stateWithStages(a, b, c), selectedStageIndex: 0 };
    const next = dispatch(state, { type: 'REORDER_STAGES', fromIndex: 0, toIndex: 2 });
    expect(next.selectedStageIndex).toBe(2);
  });

  it('tracks selected stage when a preceding stage moves past it', () => {
    // [A, B, C], selected=2 (C). Move A(0) to index 2 → [B, C, A], selected shifts from 2 to 1.
    const state = { ...stateWithStages(a, b, c), selectedStageIndex: 2 };
    const next = dispatch(state, { type: 'REORDER_STAGES', fromIndex: 0, toIndex: 2 });
    expect(next.selectedStageIndex).toBe(1);
  });

  it('marks state dirty', () => {
    const next = dispatch(stateWithStages(a, b), { type: 'REORDER_STAGES', fromIndex: 0, toIndex: 1 });
    expect(next.isDirty).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// SELECT_STAGE
// ---------------------------------------------------------------------------

describe('SELECT_STAGE', () => {
  it('sets selectedStageIndex to the given index', () => {
    const next = dispatch(initialState, { type: 'SELECT_STAGE', index: 3 });
    expect(next.selectedStageIndex).toBe(3);
  });

  it('sets selectedStageIndex to null when passed null', () => {
    const state = { ...initialState, selectedStageIndex: 1 };
    const next = dispatch(state, { type: 'SELECT_STAGE', index: null });
    expect(next.selectedStageIndex).toBeNull();
  });

  it('does not set isDirty', () => {
    const next = dispatch(initialState, { type: 'SELECT_STAGE', index: 0 });
    expect(next.isDirty).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// TOGGLE_EDITOR
// ---------------------------------------------------------------------------

describe('TOGGLE_EDITOR', () => {
  it('sets isEditorOpen to true', () => {
    const next = dispatch(initialState, { type: 'TOGGLE_EDITOR', open: true });
    expect(next.isEditorOpen).toBe(true);
  });

  it('sets isEditorOpen to false', () => {
    const state = { ...initialState, isEditorOpen: true };
    const next = dispatch(state, { type: 'TOGGLE_EDITOR', open: false });
    expect(next.isEditorOpen).toBe(false);
  });

  it('does not set isDirty', () => {
    const next = dispatch(initialState, { type: 'TOGGLE_EDITOR', open: true });
    expect(next.isDirty).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// MARK_SAVED
// ---------------------------------------------------------------------------

describe('MARK_SAVED', () => {
  it('clears isDirty', () => {
    const state = { ...initialState, isDirty: true };
    const next = dispatch(state, { type: 'MARK_SAVED' });
    expect(next.isDirty).toBe(false);
  });

  it('clears isSaving', () => {
    const state = { ...initialState, isSaving: true };
    const next = dispatch(state, { type: 'MARK_SAVED' });
    expect(next.isSaving).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// LOAD_WORKFLOW
// ---------------------------------------------------------------------------

describe('LOAD_WORKFLOW', () => {
  const stage = makeStage({ id: 'loaded-s1', name: 'Loaded Stage' });

  const workflow: Workflow = {
    id: 'wf-load',
    uuid: 'wf-uuid-load',
    name: 'Loaded Workflow',
    description: 'From server',
    version: '2.0.0',
    status: 'active',
    definition: '',
    tags: ['tag-a', 'tag-b'],
    stages: [stage],
    parameters: {
      feature: { type: 'string', required: true, description: 'Feature name' },
    },
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-06-01T00:00:00Z',
  };

  it('populates name from the workflow', () => {
    const next = dispatch(initialState, { type: 'LOAD_WORKFLOW', workflow });
    expect(next.name).toBe('Loaded Workflow');
  });

  it('populates stages from the workflow', () => {
    const next = dispatch(initialState, { type: 'LOAD_WORKFLOW', workflow });
    expect(next.stages).toHaveLength(1);
    expect(next.stages[0]?.name).toBe('Loaded Stage');
  });

  it('populates tags from the workflow', () => {
    const next = dispatch(initialState, { type: 'LOAD_WORKFLOW', workflow });
    expect(next.tags).toEqual(['tag-a', 'tag-b']);
  });

  it('converts parameters from Record to array', () => {
    const next = dispatch(initialState, { type: 'LOAD_WORKFLOW', workflow });
    expect(next.parameters).toHaveLength(1);
  });

  it('clears isDirty after loading', () => {
    const state = { ...initialState, isDirty: true };
    const next = dispatch(state, { type: 'LOAD_WORKFLOW', workflow });
    expect(next.isDirty).toBe(false);
  });

  it('sets originalWorkflow to the loaded workflow', () => {
    const next = dispatch(initialState, { type: 'LOAD_WORKFLOW', workflow });
    expect(next.originalWorkflow).toBe(workflow);
  });

  it('resets selectedStageIndex to null', () => {
    const state = { ...initialState, selectedStageIndex: 3 };
    const next = dispatch(state, { type: 'LOAD_WORKFLOW', workflow });
    expect(next.selectedStageIndex).toBeNull();
  });

  it('resets isEditorOpen to false', () => {
    const state = { ...initialState, isEditorOpen: true };
    const next = dispatch(state, { type: 'LOAD_WORKFLOW', workflow });
    expect(next.isEditorOpen).toBe(false);
  });
});
