/**
 * @jest-environment jsdom
 *
 * Tests for ExecutionDetail component.
 *
 * Focus areas:
 *   - Empty state (null stage) renders "Select a stage" message
 *   - Renders stage name and status badge
 *   - Shows timing information (started, duration)
 *   - Error section shown only when stage is failed and has an errorMessage
 *   - Gate stage with waiting_for_approval shows Approve/Reject buttons
 *   - Approve button calls onApproveGate with the stage ID
 *   - Reject button calls onRejectGate with the stage ID
 *   - Children (log viewer slot) are rendered inside "Stage logs" section
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ExecutionDetail } from '@/components/workflow/execution-detail';
import type { StageExecution, ExecutionStatus, RawStageType } from '@/types/workflow';

// ============================================================================
// Mocks
// ============================================================================

// ScrollArea: render children directly
jest.mock('@/components/ui/scroll-area', () => ({
  ScrollArea: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <div className={className}>{children}</div>
  ),
}));

// Separator: simple hr
jest.mock('@/components/ui/separator', () => ({
  Separator: () => <hr />,
}));

// ============================================================================
// Fixture factory
// ============================================================================

function makeStageExecution(
  overrides: Partial<StageExecution> = {}
): StageExecution {
  return {
    id: 'se-001',
    stageId: 'code-review',
    stageName: 'Code Review',
    stageType: 'agent',
    batchIndex: 0,
    status: 'completed',
    startedAt: '2024-01-15T10:00:00.000Z',
    completedAt: '2024-01-15T10:05:00.000Z',
    durationMs: 300_000,
    agentUsed: 'agent:reviewer-v1',
    logs: [],
    outputs: {},
    ...overrides,
  };
}

// ============================================================================
// Empty state
// ============================================================================

describe('ExecutionDetail — empty state (null stage)', () => {
  it('renders "Select a stage" message when stage is null', () => {
    render(<ExecutionDetail stage={null} />);
    expect(screen.getByText(/Select a stage to view details/i)).toBeInTheDocument();
  });

  it('renders the detail panel container with aria-label "Stage detail panel"', () => {
    render(<ExecutionDetail stage={null} />);
    expect(screen.getByLabelText('Stage detail panel')).toBeInTheDocument();
  });

  it('does not render stage name heading when stage is null', () => {
    render(<ExecutionDetail stage={null} />);
    expect(screen.queryByRole('heading', { name: /Code Review/i })).not.toBeInTheDocument();
  });
});

// ============================================================================
// Stage name and status badge
// ============================================================================

describe('ExecutionDetail — stage name and status', () => {
  it('renders the stage name as a heading', () => {
    render(<ExecutionDetail stage={makeStageExecution()} />);
    expect(screen.getByRole('heading', { name: 'Code Review' })).toBeInTheDocument();
  });

  it('renders the status badge with aria-label for completed stage', () => {
    render(<ExecutionDetail stage={makeStageExecution({ status: 'completed' })} />);
    expect(
      screen.getByLabelText(/Stage status: Completed/i)
    ).toBeInTheDocument();
  });

  it('renders the status badge for running stage', () => {
    render(
      <ExecutionDetail
        stage={makeStageExecution({ status: 'running', completedAt: undefined, durationMs: undefined })}
      />
    );
    expect(screen.getByLabelText(/Stage status: Running/i)).toBeInTheDocument();
  });

  it.each<[ExecutionStatus, string]>([
    ['pending', 'Pending'],
    ['failed', 'Failed'],
    ['cancelled', 'Cancelled'],
    ['paused', 'Paused'],
    ['waiting_for_approval', 'Waiting Gate'],
  ])(
    'renders status badge label "%s" for status %s',
    (status, expectedLabel) => {
      render(
        <ExecutionDetail
          stage={makeStageExecution({ status })}
        />
      );
      expect(
        screen.getByLabelText(new RegExp(`Stage status: ${expectedLabel}`, 'i'))
      ).toBeInTheDocument();
    }
  );

  it('renders the stage type badge for the "agent" stage type (Standard)', () => {
    render(<ExecutionDetail stage={makeStageExecution({ stageType: 'agent' })} />);
    expect(screen.getByLabelText(/Stage type: Standard/i)).toBeInTheDocument();
  });

  it('renders the stage type badge for the "gate" stage type (Gate)', () => {
    render(<ExecutionDetail stage={makeStageExecution({ stageType: 'gate' })} />);
    expect(screen.getByLabelText(/Stage type: Gate/i)).toBeInTheDocument();
  });

  it('renders the stage type badge for the "fan_out" stage type (Checkpoint)', () => {
    render(<ExecutionDetail stage={makeStageExecution({ stageType: 'fan_out' })} />);
    expect(screen.getByLabelText(/Stage type: Checkpoint/i)).toBeInTheDocument();
  });
});

// ============================================================================
// Timing information
// ============================================================================

describe('ExecutionDetail — timing section', () => {
  it('renders "Timing" section heading', () => {
    render(<ExecutionDetail stage={makeStageExecution()} />);
    // Section uses aria-labelledby; find the heading text
    expect(screen.getByText('Timing')).toBeInTheDocument();
  });

  it('renders a <time> element for startedAt when provided', () => {
    render(<ExecutionDetail stage={makeStageExecution({ startedAt: '2024-01-15T10:00:00.000Z' })} />);
    // There should be a <time> element for startedAt
    const times = document.querySelectorAll('time');
    expect(times.length).toBeGreaterThanOrEqual(1);
    const startTime = Array.from(times).find(
      (t) => t.getAttribute('dateTime') === '2024-01-15T10:00:00.000Z'
    );
    expect(startTime).toBeTruthy();
  });

  it('renders formatted duration from durationMs when available', () => {
    // 300_000 ms = 5 minutes → "5m"
    render(
      <ExecutionDetail
        stage={makeStageExecution({ durationMs: 300_000, status: 'completed' })}
      />
    );
    expect(screen.getByText('5m')).toBeInTheDocument();
  });

  it('renders "—" for duration when durationMs is absent and not running', () => {
    render(
      <ExecutionDetail
        stage={makeStageExecution({ durationMs: undefined, status: 'pending', startedAt: undefined })}
      />
    );
    // Definition list has multiple "—" entries; at least one should exist
    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBeGreaterThanOrEqual(1);
  });

  it('renders "In progress…" for Ended when stage is running', () => {
    render(
      <ExecutionDetail
        stage={makeStageExecution({
          status: 'running',
          completedAt: undefined,
          durationMs: undefined,
        })}
      />
    );
    expect(screen.getByText(/In progress/i)).toBeInTheDocument();
  });

  it('renders completedAt time element when stage is completed', () => {
    render(
      <ExecutionDetail
        stage={makeStageExecution({
          completedAt: '2024-01-15T10:05:00.000Z',
          status: 'completed',
        })}
      />
    );
    const times = document.querySelectorAll('time');
    const endTime = Array.from(times).find(
      (t) => t.getAttribute('dateTime') === '2024-01-15T10:05:00.000Z'
    );
    expect(endTime).toBeTruthy();
  });
});

// ============================================================================
// Error callout
// ============================================================================

describe('ExecutionDetail — error callout', () => {
  it('shows error alert section when stage failed and has errorMessage', () => {
    render(
      <ExecutionDetail
        stage={makeStageExecution({
          status: 'failed',
          errorMessage: 'Syntax error on line 42',
        })}
      />
    );
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/Syntax error on line 42/i)).toBeInTheDocument();
  });

  it('shows "Stage failed" heading in the error alert', () => {
    render(
      <ExecutionDetail
        stage={makeStageExecution({
          status: 'failed',
          errorMessage: 'Timeout exceeded',
        })}
      />
    );
    expect(screen.getByText(/Stage failed/i)).toBeInTheDocument();
  });

  it('does not show error alert when stage failed but errorMessage is absent', () => {
    render(
      <ExecutionDetail
        stage={makeStageExecution({ status: 'failed', errorMessage: undefined })}
      />
    );
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('does not show error alert when stage is completed', () => {
    render(
      <ExecutionDetail
        stage={makeStageExecution({ status: 'completed', errorMessage: undefined })}
      />
    );
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});

// ============================================================================
// Gate approval panel
// ============================================================================

describe('ExecutionDetail — gate approval panel', () => {
  const gateWaitingStage = makeStageExecution({
    stageType: 'gate',
    status: 'waiting_for_approval',
    stageName: 'Security Gate',
  });

  it('renders gate approval panel with "Awaiting approval" text', () => {
    render(<ExecutionDetail stage={gateWaitingStage} />);
    expect(screen.getByLabelText('Gate approval required')).toBeInTheDocument();
    expect(screen.getByText(/Awaiting approval/i)).toBeInTheDocument();
  });

  it('renders Approve button with aria-label containing stage name', () => {
    render(<ExecutionDetail stage={gateWaitingStage} />);
    expect(
      screen.getByRole('button', { name: /Approve gate: Security Gate/i })
    ).toBeInTheDocument();
  });

  it('renders Reject button with aria-label containing stage name', () => {
    render(<ExecutionDetail stage={gateWaitingStage} />);
    expect(
      screen.getByRole('button', { name: /Reject gate: Security Gate/i })
    ).toBeInTheDocument();
  });

  it('calls onApproveGate with the stage ID when Approve is clicked', async () => {
    const user = userEvent.setup();
    const onApproveGate = jest.fn();
    render(<ExecutionDetail stage={gateWaitingStage} onApproveGate={onApproveGate} />);
    await user.click(screen.getByRole('button', { name: /Approve gate/i }));
    expect(onApproveGate).toHaveBeenCalledWith('se-001');
    expect(onApproveGate).toHaveBeenCalledTimes(1);
  });

  it('calls onRejectGate with the stage ID when Reject is clicked', async () => {
    const user = userEvent.setup();
    const onRejectGate = jest.fn();
    render(<ExecutionDetail stage={gateWaitingStage} onRejectGate={onRejectGate} />);
    await user.click(screen.getByRole('button', { name: /Reject gate/i }));
    expect(onRejectGate).toHaveBeenCalledWith('se-001');
    expect(onRejectGate).toHaveBeenCalledTimes(1);
  });

  it('does not render gate panel when stage is "gate" type but not waiting_for_approval', () => {
    render(
      <ExecutionDetail
        stage={makeStageExecution({ stageType: 'gate', status: 'completed' })}
      />
    );
    expect(screen.queryByLabelText('Gate approval required')).not.toBeInTheDocument();
  });

  it('does not render gate panel for non-gate stage types even if waiting_for_approval', () => {
    render(
      <ExecutionDetail
        stage={makeStageExecution({ stageType: 'agent', status: 'waiting_for_approval' })}
      />
    );
    expect(screen.queryByLabelText('Gate approval required')).not.toBeInTheDocument();
  });
});

// ============================================================================
// Children (log viewer slot)
// ============================================================================

describe('ExecutionDetail — children (log viewer slot)', () => {
  it('renders children inside the "Stage logs" section', () => {
    render(
      <ExecutionDetail stage={makeStageExecution()}>
        <div>Log viewer content</div>
      </ExecutionDetail>
    );
    const logsSection = screen.getByRole('region', { name: 'Stage logs' });
    expect(logsSection).toBeInTheDocument();
    expect(screen.getByText('Log viewer content')).toBeInTheDocument();
  });

  it('does not render the logs section when no children are provided', () => {
    render(<ExecutionDetail stage={makeStageExecution()} />);
    expect(screen.queryByRole('region', { name: 'Stage logs' })).not.toBeInTheDocument();
  });
});

// ============================================================================
// Agent & Tools section
// ============================================================================

describe('ExecutionDetail — agent section', () => {
  it('shows agent name extracted from artifact reference', () => {
    render(
      <ExecutionDetail
        stage={makeStageExecution({ agentUsed: 'agent:researcher-v1' })}
      />
    );
    expect(screen.getByText('researcher-v1')).toBeInTheDocument();
  });

  it('shows "No agent assigned" when agentUsed is absent', () => {
    render(
      <ExecutionDetail
        stage={makeStageExecution({ agentUsed: undefined })}
      />
    );
    expect(screen.getByText(/No agent assigned/i)).toBeInTheDocument();
  });
});
