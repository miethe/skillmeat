/**
 * @jest-environment jsdom
 *
 * Tests for ExecutionHeader component.
 *
 * Focus areas:
 *   - Workflow name is rendered as a link to the workflow detail page
 *   - Run ID chip is truncated to 8 hex chars (dashes stripped)
 *   - Status badge shows the correct label for each ExecutionStatus
 *   - Running status: Pause + Cancel buttons visible
 *   - Paused status: Resume + Cancel buttons visible
 *   - Completed / Failed / Cancelled: Re-run button visible
 *   - Pending / waiting_for_approval: Cancel button visible
 *   - Button callbacks (onPause, onResume, onCancel, onRerun) fire on click
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ExecutionHeader } from '@/components/workflow/execution-header';
import type { WorkflowExecution, ExecutionStatus } from '@/types/workflow';

// ============================================================================
// Fixture factory
// ============================================================================

function makeExecution(
  overrides: Partial<WorkflowExecution> = {}
): WorkflowExecution {
  return {
    id: 'abcdef12-3456-7890-abcd-ef1234567890',
    workflowId: 'wf-001',
    status: 'running',
    trigger: 'manual',
    startedAt: new Date(Date.now() - 60_000).toISOString(), // 1 minute ago
    stages: [],
    currentStageIndex: 0,
    progressPct: 0,
    ...overrides,
  };
}

const DEFAULT_CALLBACKS = {
  onPause: jest.fn(),
  onResume: jest.fn(),
  onCancel: jest.fn(),
  onRerun: jest.fn(),
};

function renderHeader(
  executionOverrides: Partial<WorkflowExecution> = {},
  callbackOverrides: Partial<typeof DEFAULT_CALLBACKS> = {}
) {
  const callbacks = { ...DEFAULT_CALLBACKS, ...callbackOverrides };
  return render(
    <ExecutionHeader
      execution={makeExecution(executionOverrides)}
      workflowName="Code Review Pipeline"
      workflowId="wf-001"
      {...callbacks}
    />
  );
}

// ============================================================================
// Workflow name link
// ============================================================================

describe('ExecutionHeader — workflow name link', () => {
  it('renders the workflow name as an anchor element', () => {
    renderHeader();
    expect(
      screen.getByRole('link', { name: /Back to workflow: Code Review Pipeline/i })
    ).toBeInTheDocument();
  });

  it('links to the workflow detail page with the correct workflowId', () => {
    renderHeader();
    const link = screen.getByRole('link', { name: /Back to workflow/i });
    expect(link).toHaveAttribute('href', '/workflows/wf-001');
  });

  it('displays the workflow name text', () => {
    renderHeader();
    expect(screen.getByText('Code Review Pipeline')).toBeInTheDocument();
  });
});

// ============================================================================
// Run ID chip
// ============================================================================

describe('ExecutionHeader — run ID chip', () => {
  it('shows truncated run ID (first 8 hex chars, dashes stripped)', () => {
    // id: 'abcdef12-3456-7890-abcd-ef1234567890' → strip dashes → 'abcdef1234567890abcdef1234567890' → first 8 → 'abcdef12'
    renderHeader();
    expect(screen.getByText('abcdef12')).toBeInTheDocument();
  });

  it('renders the full run ID in the title attribute for tooltip', () => {
    renderHeader();
    // Find the span with aria-label "Run ID: ..." — it has the title attribute
    const fullIdEl = screen.getByLabelText(/Run ID:/i);
    expect(fullIdEl).toHaveAttribute('title', 'abcdef12-3456-7890-abcd-ef1234567890');
  });

  it('has a screen-reader-accessible full run ID via sr-only span', () => {
    renderHeader();
    // The full ID is also in the DOM via sr-only span
    const label = screen.getByLabelText(/Run ID: abcdef12-3456-7890-abcd-ef1234567890/i);
    expect(label).toBeInTheDocument();
  });
});

// ============================================================================
// Status badge
// ============================================================================

describe('ExecutionHeader — status badge', () => {
  const statusCases: [ExecutionStatus, string][] = [
    ['running', 'Running'],
    ['completed', 'Completed'],
    ['failed', 'Failed'],
    ['paused', 'Paused'],
    ['cancelled', 'Cancelled'],
    ['pending', 'Pending'],
    ['waiting_for_approval', 'Awaiting Approval'],
  ];

  it.each(statusCases)(
    'shows "%s" badge label for status %s',
    (status, expectedLabel) => {
      renderHeader({ status });
      expect(
        screen.getByLabelText(new RegExp(`Execution status: ${expectedLabel}`, 'i'))
      ).toBeInTheDocument();
    }
  );
});

// ============================================================================
// Action buttons — running
// ============================================================================

describe('ExecutionHeader — actions for running status', () => {
  it('renders Pause button', () => {
    renderHeader({ status: 'running' });
    expect(screen.getAllByRole('button', { name: 'Pause' })).not.toHaveLength(0);
  });

  it('renders Cancel button', () => {
    renderHeader({ status: 'running' });
    expect(screen.getAllByRole('button', { name: 'Cancel' })).not.toHaveLength(0);
  });

  it('does not render Resume button when running', () => {
    renderHeader({ status: 'running' });
    expect(screen.queryByRole('button', { name: 'Resume' })).not.toBeInTheDocument();
  });

  it('does not render Re-run button when running', () => {
    renderHeader({ status: 'running' });
    expect(screen.queryByRole('button', { name: 'Re-run' })).not.toBeInTheDocument();
  });

  it('calls onPause when Pause is clicked', async () => {
    const user = userEvent.setup();
    const onPause = jest.fn();
    renderHeader({ status: 'running' }, { onPause });
    // Desktop button (hidden sm:flex — may not match in jsdom; find by all)
    const pauseButtons = screen.getAllByRole('button', { name: 'Pause' });
    await user.click(pauseButtons[0]);
    expect(onPause).toHaveBeenCalledTimes(1);
  });

  it('calls onCancel when Cancel is clicked during running', async () => {
    const user = userEvent.setup();
    const onCancel = jest.fn();
    renderHeader({ status: 'running' }, { onCancel });
    const cancelButtons = screen.getAllByRole('button', { name: 'Cancel' });
    await user.click(cancelButtons[0]);
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});

// ============================================================================
// Action buttons — paused
// ============================================================================

describe('ExecutionHeader — actions for paused status', () => {
  it('renders Resume button', () => {
    renderHeader({ status: 'paused' });
    expect(screen.getAllByRole('button', { name: 'Resume' })).not.toHaveLength(0);
  });

  it('renders Cancel button', () => {
    renderHeader({ status: 'paused' });
    expect(screen.getAllByRole('button', { name: 'Cancel' })).not.toHaveLength(0);
  });

  it('does not render Pause button when paused', () => {
    renderHeader({ status: 'paused' });
    expect(screen.queryByRole('button', { name: 'Pause' })).not.toBeInTheDocument();
  });

  it('calls onResume when Resume is clicked', async () => {
    const user = userEvent.setup();
    const onResume = jest.fn();
    renderHeader({ status: 'paused' }, { onResume });
    const resumeButtons = screen.getAllByRole('button', { name: 'Resume' });
    await user.click(resumeButtons[0]);
    expect(onResume).toHaveBeenCalledTimes(1);
  });

  it('calls onCancel when Cancel is clicked during paused', async () => {
    const user = userEvent.setup();
    const onCancel = jest.fn();
    renderHeader({ status: 'paused' }, { onCancel });
    const cancelButtons = screen.getAllByRole('button', { name: 'Cancel' });
    await user.click(cancelButtons[0]);
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});

// ============================================================================
// Action buttons — terminal statuses (completed / failed / cancelled)
// ============================================================================

describe('ExecutionHeader — actions for terminal statuses', () => {
  it.each<ExecutionStatus>(['completed', 'failed', 'cancelled'])(
    'renders Re-run button for status "%s"',
    (status) => {
      renderHeader({ status });
      expect(screen.getAllByRole('button', { name: 'Re-run' })).not.toHaveLength(0);
    }
  );

  it.each<ExecutionStatus>(['completed', 'failed', 'cancelled'])(
    'does not render Pause or Resume for status "%s"',
    (status) => {
      renderHeader({ status });
      expect(screen.queryByRole('button', { name: 'Pause' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Resume' })).not.toBeInTheDocument();
    }
  );

  it('calls onRerun when Re-run is clicked on a completed execution', async () => {
    const user = userEvent.setup();
    const onRerun = jest.fn();
    renderHeader({ status: 'completed' }, { onRerun });
    const rerunButtons = screen.getAllByRole('button', { name: 'Re-run' });
    await user.click(rerunButtons[0]);
    expect(onRerun).toHaveBeenCalledTimes(1);
  });
});

// ============================================================================
// Action buttons — pending / waiting_for_approval
// ============================================================================

describe('ExecutionHeader — actions for pending / waiting_for_approval', () => {
  it.each<ExecutionStatus>(['pending', 'waiting_for_approval'])(
    'renders Cancel button for status "%s"',
    (status) => {
      renderHeader({ status });
      expect(screen.getAllByRole('button', { name: 'Cancel' })).not.toHaveLength(0);
    }
  );

  it.each<ExecutionStatus>(['pending', 'waiting_for_approval'])(
    'does not render Re-run, Pause, or Resume for status "%s"',
    (status) => {
      renderHeader({ status });
      expect(screen.queryByRole('button', { name: 'Re-run' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Pause' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Resume' })).not.toBeInTheDocument();
    }
  );
});

// ============================================================================
// Header landmark
// ============================================================================

describe('ExecutionHeader — landmark role', () => {
  it('renders a <header> element with aria-label "Execution header"', () => {
    renderHeader();
    expect(screen.getByRole('banner', { name: /Execution header/i })).toBeInTheDocument();
  });
});
