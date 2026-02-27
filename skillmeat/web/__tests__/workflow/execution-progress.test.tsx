/**
 * @jest-environment jsdom
 *
 * Tests for ExecutionProgress component.
 *
 * Focus areas:
 *   - Correct progress percentage derived from terminal stage count
 *   - "N of M stages complete" label text
 *   - "All N stages complete" label text on completed execution
 *   - Pending status shows indeterminate / "Initializing…" text
 *   - Completed status shows 100% with all-complete message
 *   - Failed status shows progress with failed indication
 *   - Elapsed timer rendered when startedAt is provided for active executions
 *   - No stages: "No stages" label text
 */

import { render, screen } from '@testing-library/react';
import { ExecutionProgress } from '@/components/workflow/execution-progress';
import type { StageExecution, ExecutionStatus } from '@/types/workflow';

// ============================================================================
// Fixture factory
// ============================================================================

function makeStageExecution(
  overrides: Partial<StageExecution> = {}
): StageExecution {
  return {
    id: 'se-001',
    stageId: 'stage-id',
    stageName: 'Stage',
    stageType: 'agent',
    batchIndex: 0,
    status: 'pending',
    logs: [],
    outputs: {},
    ...overrides,
  };
}

function makeStages(statuses: ExecutionStatus[]): StageExecution[] {
  return statuses.map((status, i) =>
    makeStageExecution({ id: `se-${i}`, stageName: `Stage ${i + 1}`, status })
  );
}

// A recent startedAt (1 minute ago)
const STARTED_AT = new Date(Date.now() - 60_000).toISOString();

// ============================================================================
// Pending state
// ============================================================================

describe('ExecutionProgress — pending status', () => {
  it('shows "Initializing…" label text', () => {
    render(
      <ExecutionProgress
        stages={[]}
        executionStatus="pending"
        startedAt={null}
      />
    );
    expect(screen.getByText(/Initializing/i)).toBeInTheDocument();
  });

  it('renders indeterminate progressbar with aria-valuetext "Initializing"', () => {
    render(
      <ExecutionProgress
        stages={[]}
        executionStatus="pending"
        startedAt={null}
      />
    );
    expect(
      screen.getByRole('progressbar', { name: /Initializing/i })
    ).toBeInTheDocument();
  });

  it('does not render the determinate Progress bar when pending', () => {
    render(
      <ExecutionProgress
        stages={makeStages(['pending'])}
        executionStatus="pending"
        startedAt={null}
      />
    );
    // The determinate bar has aria-label "Stage completion progress"
    expect(
      screen.queryByLabelText('Stage completion progress')
    ).not.toBeInTheDocument();
  });
});

// ============================================================================
// Progress percentage
// ============================================================================

describe('ExecutionProgress — progress percentage', () => {
  it('shows "3 of 5 stages complete" when 3 terminal stages out of 5', () => {
    const stages = makeStages([
      'completed',
      'completed',
      'completed',
      'running',
      'pending',
    ]);
    render(
      <ExecutionProgress
        stages={stages}
        executionStatus="running"
        startedAt={STARTED_AT}
      />
    );
    expect(screen.getByText(/3 of 5 stages complete/i)).toBeInTheDocument();
  });

  it('passes correct aria-valuenow to the progress bar (60 for 3/5)', () => {
    const stages = makeStages([
      'completed',
      'completed',
      'completed',
      'running',
      'pending',
    ]);
    render(
      <ExecutionProgress
        stages={stages}
        executionStatus="running"
        startedAt={STARTED_AT}
      />
    );
    const progressBar = screen.getByLabelText('Stage completion progress');
    expect(progressBar).toHaveAttribute('aria-valuenow', '60');
  });

  it('shows "0 of 3 stages complete" when no stages are terminal', () => {
    const stages = makeStages(['running', 'pending', 'pending']);
    render(
      <ExecutionProgress
        stages={stages}
        executionStatus="running"
        startedAt={STARTED_AT}
      />
    );
    expect(screen.getByText(/0 of 3 stages complete/i)).toBeInTheDocument();
  });

  it('shows "No stages" when stages array is empty and not pending', () => {
    render(
      <ExecutionProgress
        stages={[]}
        executionStatus="running"
        startedAt={STARTED_AT}
      />
    );
    expect(screen.getByText(/No stages/i)).toBeInTheDocument();
  });
});

// ============================================================================
// Completed status
// ============================================================================

describe('ExecutionProgress — completed status', () => {
  it('shows "All N stages complete" when execution is completed', () => {
    const stages = makeStages(['completed', 'completed', 'completed']);
    render(
      <ExecutionProgress
        stages={stages}
        executionStatus="completed"
        startedAt={STARTED_AT}
      />
    );
    expect(screen.getByText(/All 3 stages complete/i)).toBeInTheDocument();
  });

  it('passes aria-valuenow="100" when all 3 stages are completed', () => {
    const stages = makeStages(['completed', 'completed', 'completed']);
    render(
      <ExecutionProgress
        stages={stages}
        executionStatus="completed"
        startedAt={STARTED_AT}
      />
    );
    const progressBar = screen.getByLabelText('Stage completion progress');
    expect(progressBar).toHaveAttribute('aria-valuenow', '100');
  });

  it('uses singular "stage" for a single-stage completed workflow', () => {
    const stages = makeStages(['completed']);
    render(
      <ExecutionProgress
        stages={stages}
        executionStatus="completed"
        startedAt={STARTED_AT}
      />
    );
    expect(screen.getByText(/All 1 stage complete/i)).toBeInTheDocument();
  });
});

// ============================================================================
// Failed status
// ============================================================================

describe('ExecutionProgress — failed status', () => {
  it('shows "N of M stages complete" (not all-complete) when failed', () => {
    const stages = makeStages(['completed', 'failed', 'pending']);
    render(
      <ExecutionProgress
        stages={stages}
        executionStatus="failed"
        startedAt={STARTED_AT}
      />
    );
    // 2 terminal (completed + failed), 3 total → "2 of 3 stages complete"
    expect(screen.getByText(/2 of 3 stages complete/i)).toBeInTheDocument();
  });

  it('passes aria-valuenow based on terminal count, not just completed', () => {
    const stages = makeStages(['completed', 'failed', 'pending']);
    render(
      <ExecutionProgress
        stages={stages}
        executionStatus="failed"
        startedAt={STARTED_AT}
      />
    );
    // 2 of 3 terminal → 66%
    const progressBar = screen.getByLabelText('Stage completion progress');
    expect(progressBar).toHaveAttribute('aria-valuenow', '67');
  });
});

// ============================================================================
// Cancelled status
// ============================================================================

describe('ExecutionProgress — cancelled status', () => {
  it('shows count label when cancelled', () => {
    const stages = makeStages(['completed', 'cancelled', 'pending']);
    render(
      <ExecutionProgress
        stages={stages}
        executionStatus="cancelled"
        startedAt={STARTED_AT}
      />
    );
    expect(screen.getByText(/2 of 3 stages complete/i)).toBeInTheDocument();
  });
});

// ============================================================================
// Elapsed time
// ============================================================================

describe('ExecutionProgress — elapsed time', () => {
  it('renders a timer element for running executions with startedAt', () => {
    render(
      <ExecutionProgress
        stages={makeStages(['running'])}
        executionStatus="running"
        startedAt={STARTED_AT}
      />
    );
    expect(screen.getByRole('timer')).toBeInTheDocument();
  });

  it('does not render a timer when startedAt is null', () => {
    render(
      <ExecutionProgress
        stages={[]}
        executionStatus="running"
        startedAt={null}
      />
    );
    expect(screen.queryByRole('timer')).not.toBeInTheDocument();
  });

  it('renders a timer for paused executions with startedAt', () => {
    render(
      <ExecutionProgress
        stages={makeStages(['paused'])}
        executionStatus="paused"
        startedAt={STARTED_AT}
      />
    );
    expect(screen.getByRole('timer')).toBeInTheDocument();
  });
});

// ============================================================================
// Container landmark
// ============================================================================

describe('ExecutionProgress — container', () => {
  it('renders a container with aria-label "Execution progress"', () => {
    render(
      <ExecutionProgress
        stages={[]}
        executionStatus="running"
        startedAt={null}
      />
    );
    expect(screen.getByLabelText('Execution progress')).toBeInTheDocument();
  });
});
