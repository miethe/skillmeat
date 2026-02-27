/**
 * @jest-environment jsdom
 *
 * Tests for StageTimeline component.
 *
 * Focus areas:
 *   - Renders all ExecutionStatus variants with correct aria attributes
 *   - Click on stage node calls onSelectStage with the correct ID
 *   - Selected stage has aria-selected="true"; others have aria-selected="false"
 *   - Running stage has aria-current="step"
 *   - Empty state renders "No stages" message
 *   - J/K keyboard navigation moves selection through the list
 */

import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StageTimeline } from '@/components/workflow/stage-timeline';
import type { StageExecution, ExecutionStatus } from '@/types/workflow';

// ============================================================================
// Mocks
// ============================================================================

// ScrollArea in tests: just render children directly
jest.mock('@/components/ui/scroll-area', () => ({
  ScrollArea: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <div className={className}>{children}</div>
  ),
}));

// ============================================================================
// Fixture factory
// ============================================================================

function makeStageExecution(
  overrides: Partial<StageExecution> = {}
): StageExecution {
  return {
    id: 'stage-exec-001',
    stageId: 'code-review',
    stageName: 'Code Review',
    stageType: 'agent',
    batchIndex: 0,
    status: 'pending',
    logs: [],
    outputs: {},
    ...overrides,
  };
}

function makeStages(
  statuses: ExecutionStatus[],
  namePrefix = 'Stage'
): StageExecution[] {
  return statuses.map((status, i) => (
    makeStageExecution({
      id: `stage-${i}`,
      stageId: `stage-id-${i}`,
      stageName: `${namePrefix} ${i + 1}`,
      status,
    })
  ));
}

// ============================================================================
// Empty state
// ============================================================================

describe('StageTimeline — empty state', () => {
  it('renders "No stages" when stages array is empty', () => {
    render(
      <StageTimeline
        stages={[]}
        selectedStageId={null}
        onSelectStage={jest.fn()}
      />
    );
    expect(screen.getByText('No stages')).toBeInTheDocument();
  });

  it('does not render a list when stages are empty', () => {
    render(
      <StageTimeline
        stages={[]}
        selectedStageId={null}
        onSelectStage={jest.fn()}
      />
    );
    expect(screen.queryByRole('list')).not.toBeInTheDocument();
  });
});

// ============================================================================
// Status rendering
// ============================================================================

describe('StageTimeline — status rendering', () => {
  const ALL_STATUSES: ExecutionStatus[] = [
    'pending',
    'running',
    'completed',
    'failed',
    'cancelled',
    'paused',
    'waiting_for_approval',
  ];

  it.each(ALL_STATUSES)(
    'renders a stage with status "%s" without crashing',
    (status) => {
      const stages = [makeStageExecution({ id: 'x', status, stageName: 'Test Stage' })];
      render(
        <StageTimeline
          stages={stages}
          selectedStageId={null}
          onSelectStage={jest.fn()}
        />
      );
      // The button aria-label contains the stage name
      expect(screen.getByRole('button', { name: /Test Stage/i })).toBeInTheDocument();
    }
  );

  it('renders a list container with aria-label "Workflow stages"', () => {
    const stages = makeStages(['pending']);
    render(
      <StageTimeline
        stages={stages}
        selectedStageId={null}
        onSelectStage={jest.fn()}
      />
    );
    expect(screen.getByRole('list', { name: /Workflow stages/i })).toBeInTheDocument();
  });

  it('renders one button per stage', () => {
    const stages = makeStages(['pending', 'running', 'completed']);
    render(
      <StageTimeline
        stages={stages}
        selectedStageId={null}
        onSelectStage={jest.fn()}
      />
    );
    expect(screen.getAllByRole('button')).toHaveLength(3);
  });
});

// ============================================================================
// Selection — click interaction
// ============================================================================

describe('StageTimeline — click selection', () => {
  it('calls onSelectStage with the correct stage ID when a node is clicked', async () => {
    const user = userEvent.setup();
    const onSelectStage = jest.fn();
    const stages = makeStages(['pending', 'running']);

    render(
      <StageTimeline
        stages={stages}
        selectedStageId={null}
        onSelectStage={onSelectStage}
      />
    );

    // Click the second stage (Stage 2)
    await user.click(screen.getByRole('button', { name: /Stage 2/i }));
    expect(onSelectStage).toHaveBeenCalledWith('stage-1');
    expect(onSelectStage).toHaveBeenCalledTimes(1);
  });

  it('calls onSelectStage with the ID of the first stage when clicked', async () => {
    const user = userEvent.setup();
    const onSelectStage = jest.fn();
    const stages = makeStages(['completed']);

    render(
      <StageTimeline
        stages={stages}
        selectedStageId={null}
        onSelectStage={onSelectStage}
      />
    );

    await user.click(screen.getByRole('button', { name: /Stage 1/i }));
    expect(onSelectStage).toHaveBeenCalledWith('stage-0');
  });
});

// ============================================================================
// ARIA — selected state
// ============================================================================

describe('StageTimeline — aria-selected', () => {
  it('sets aria-selected="true" on the selected stage button', () => {
    const stages = makeStages(['completed', 'pending']);
    render(
      <StageTimeline
        stages={stages}
        selectedStageId="stage-0"
        onSelectStage={jest.fn()}
      />
    );
    const btn = screen.getByRole('button', { name: /Stage 1/i });
    expect(btn).toHaveAttribute('aria-selected', 'true');
  });

  it('sets aria-selected="false" on non-selected stage buttons', () => {
    const stages = makeStages(['completed', 'pending']);
    render(
      <StageTimeline
        stages={stages}
        selectedStageId="stage-0"
        onSelectStage={jest.fn()}
      />
    );
    const btn = screen.getByRole('button', { name: /Stage 2/i });
    expect(btn).toHaveAttribute('aria-selected', 'false');
  });

  it('no stage has aria-selected="true" when selectedStageId is null', () => {
    const stages = makeStages(['pending', 'running']);
    render(
      <StageTimeline
        stages={stages}
        selectedStageId={null}
        onSelectStage={jest.fn()}
      />
    );
    const buttons = screen.getAllByRole('button');
    buttons.forEach((btn) => {
      expect(btn).not.toHaveAttribute('aria-selected', 'true');
    });
  });
});

// ============================================================================
// ARIA — running stage
// ============================================================================

describe('StageTimeline — aria-current for running stage', () => {
  it('sets aria-current="step" on the running stage button', () => {
    const stages = [
      makeStageExecution({ id: 'a', stageName: 'Alpha', status: 'completed' }),
      makeStageExecution({ id: 'b', stageName: 'Beta', status: 'running' }),
      makeStageExecution({ id: 'c', stageName: 'Gamma', status: 'pending' }),
    ];
    render(
      <StageTimeline
        stages={stages}
        selectedStageId={null}
        onSelectStage={jest.fn()}
      />
    );
    expect(screen.getByRole('button', { name: /Beta/i })).toHaveAttribute(
      'aria-current',
      'step'
    );
  });

  it('does not set aria-current="step" on non-running stage buttons', () => {
    const stages = [
      makeStageExecution({ id: 'a', stageName: 'Alpha', status: 'completed' }),
      makeStageExecution({ id: 'b', stageName: 'Beta', status: 'running' }),
    ];
    render(
      <StageTimeline
        stages={stages}
        selectedStageId={null}
        onSelectStage={jest.fn()}
      />
    );
    expect(screen.getByRole('button', { name: /Alpha/i })).not.toHaveAttribute(
      'aria-current'
    );
  });
});

// ============================================================================
// Keyboard navigation (J / K)
// ============================================================================

describe('StageTimeline — J/K keyboard navigation', () => {
  it('pressing J selects the next stage when a stage is currently selected', () => {
    const onSelectStage = jest.fn();
    const stages = makeStages(['completed', 'pending', 'pending']);

    render(
      <StageTimeline
        stages={stages}
        selectedStageId="stage-0"
        onSelectStage={onSelectStage}
      />
    );

    fireEvent.keyDown(window, { key: 'j' });
    expect(onSelectStage).toHaveBeenCalledWith('stage-1');
  });

  it('pressing K selects the previous stage', () => {
    const onSelectStage = jest.fn();
    const stages = makeStages(['completed', 'running', 'pending']);

    render(
      <StageTimeline
        stages={stages}
        selectedStageId="stage-2"
        onSelectStage={onSelectStage}
      />
    );

    fireEvent.keyDown(window, { key: 'k' });
    expect(onSelectStage).toHaveBeenCalledWith('stage-1');
  });

  it('pressing J on the last stage stays on the last stage', () => {
    const onSelectStage = jest.fn();
    const stages = makeStages(['completed', 'completed']);

    render(
      <StageTimeline
        stages={stages}
        selectedStageId="stage-1"
        onSelectStage={onSelectStage}
      />
    );

    fireEvent.keyDown(window, { key: 'j' });
    expect(onSelectStage).toHaveBeenCalledWith('stage-1');
  });

  it('pressing K on the first stage stays on the first stage', () => {
    const onSelectStage = jest.fn();
    const stages = makeStages(['running', 'pending']);

    render(
      <StageTimeline
        stages={stages}
        selectedStageId="stage-0"
        onSelectStage={onSelectStage}
      />
    );

    fireEvent.keyDown(window, { key: 'k' });
    expect(onSelectStage).toHaveBeenCalledWith('stage-0');
  });

  it('pressing J when no stage is selected selects the first stage', () => {
    const onSelectStage = jest.fn();
    const stages = makeStages(['pending', 'pending']);

    render(
      <StageTimeline
        stages={stages}
        selectedStageId={null}
        onSelectStage={onSelectStage}
      />
    );

    fireEvent.keyDown(window, { key: 'j' });
    expect(onSelectStage).toHaveBeenCalledWith('stage-0');
  });

  it('does not fire onSelectStage on J/K when focus is inside a text input', () => {
    const onSelectStage = jest.fn();
    const stages = makeStages(['pending', 'pending']);

    render(
      <div>
        <input data-testid="text-input" />
        <StageTimeline
          stages={stages}
          selectedStageId={null}
          onSelectStage={onSelectStage}
        />
      </div>
    );

    const input = screen.getByTestId('text-input');
    fireEvent.keyDown(input, { key: 'j', target: input });
    // We simulated the event on the input element — the component guards against
    // target.tagName === 'INPUT'. Since window listener checks target, we fire
    // the event on window but with a synthetic target that is an INPUT.
    // Simplest: just verify calling jest.fn() is NOT called when the event
    // originates from an INPUT tag via the global listener check.
    // Since jsdom doesn't truly set e.target to input on window.dispatchEvent,
    // we validate the guard by confirming the default (no selection) path.
    expect(onSelectStage).not.toHaveBeenCalled();
  });

  it('does not react to keyboard when stages array is empty', () => {
    const onSelectStage = jest.fn();

    render(
      <StageTimeline
        stages={[]}
        selectedStageId={null}
        onSelectStage={onSelectStage}
      />
    );

    fireEvent.keyDown(window, { key: 'j' });
    fireEvent.keyDown(window, { key: 'k' });
    expect(onSelectStage).not.toHaveBeenCalled();
  });
});
