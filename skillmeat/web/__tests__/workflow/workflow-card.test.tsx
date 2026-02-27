/**
 * @jest-environment jsdom
 *
 * Tests for WorkflowCard and WorkflowCardSkeleton components.
 *
 * Focus areas:
 *   - Renders workflow name, stage count, status badge
 *   - Shows tags (max 3 + overflow badge)
 *   - Run / Edit buttons call their callbacks
 *   - Duplicate and Delete in dropdown menu work
 *   - Card link navigates to detail page
 *   - Skeleton renders without errors
 *   - Archived / deprecated workflows disable the Run button
 */

import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WorkflowCard, WorkflowCardSkeleton } from '@/components/workflow/workflow-card';
import type { Workflow } from '@/types/workflow';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeWorkflow(overrides: Partial<Workflow> = {}): Workflow {
  return {
    id: 'wf-001',
    uuid: 'wf-uuid-001',
    name: 'My Test Workflow',
    description: 'Runs the test suite end-to-end',
    version: '1.0.0',
    status: 'active',
    definition: '',
    tags: ['ci', 'testing', 'e2e'],
    stages: [
      { id: 's1', stageIdRef: 'stage-1', name: 'Build', orderIndex: 0, stageType: 'agent', dependsOn: [], inputs: {}, outputs: {} },
      { id: 's2', stageIdRef: 'stage-2', name: 'Test', orderIndex: 1, stageType: 'agent', dependsOn: [], inputs: {}, outputs: {} },
    ],
    parameters: {},
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-06-15T12:00:00Z',
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// WorkflowCard
// ---------------------------------------------------------------------------

describe('WorkflowCard', () => {
  describe('content rendering', () => {
    it('renders the workflow name', () => {
      render(<WorkflowCard workflow={makeWorkflow()} />);
      expect(screen.getByText('My Test Workflow')).toBeInTheDocument();
    });

    it('shows singular "stage" label for a single stage', () => {
      const wf = makeWorkflow({
        stages: [{ id: 's1', stageIdRef: 'stage-1', name: 'Only', orderIndex: 0, stageType: 'agent', dependsOn: [], inputs: {}, outputs: {} }],
      });
      render(<WorkflowCard workflow={wf} />);
      expect(screen.getByText(/1 stage\b/)).toBeInTheDocument();
    });

    it('shows plural "stages" label for multiple stages', () => {
      render(<WorkflowCard workflow={makeWorkflow()} />);
      expect(screen.getByText(/2 stages/)).toBeInTheDocument();
    });

    it('shows "0 stages" when stages array is empty', () => {
      render(<WorkflowCard workflow={makeWorkflow({ stages: [] })} />);
      expect(screen.getByText(/0 stages/)).toBeInTheDocument();
    });

    it('shows "Never run" when lastRunAt is not provided', () => {
      render(<WorkflowCard workflow={makeWorkflow()} />);
      expect(screen.getByText(/Never run/)).toBeInTheDocument();
    });

    it('shows last-run time when lastRunAt is provided', () => {
      const lastRunAt = new Date(Date.now() - 60_000).toISOString(); // 1 minute ago
      render(<WorkflowCard workflow={makeWorkflow()} lastRunAt={lastRunAt} />);
      // The helper produces "Last run X ago"
      expect(screen.getByText(/Last run/)).toBeInTheDocument();
    });
  });

  describe('status badge', () => {
    it.each([
      ['active', 'Active'],
      ['draft', 'Draft'],
      ['archived', 'Archived'],
      ['deprecated', 'Deprecated'],
    ] as const)('renders "%s" status badge with label "%s"', (status, label) => {
      render(<WorkflowCard workflow={makeWorkflow({ status })} />);
      expect(screen.getByText(label)).toBeInTheDocument();
    });
  });

  describe('tags', () => {
    it('displays up to 3 tags', () => {
      render(<WorkflowCard workflow={makeWorkflow({ tags: ['ci', 'testing', 'e2e'] })} />);
      expect(screen.getByText('ci')).toBeInTheDocument();
      expect(screen.getByText('testing')).toBeInTheDocument();
      expect(screen.getByText('e2e')).toBeInTheDocument();
    });

    it('shows "+1 more" overflow badge when 4 tags', () => {
      render(<WorkflowCard workflow={makeWorkflow({ tags: ['a', 'b', 'c', 'd'] })} />);
      expect(screen.getByText('+1 more')).toBeInTheDocument();
      // Only first 3 should be visible by name
      expect(screen.getByText('a')).toBeInTheDocument();
      expect(screen.queryByText('d')).not.toBeInTheDocument();
    });

    it('shows "+2 more" overflow badge when 5 tags', () => {
      render(<WorkflowCard workflow={makeWorkflow({ tags: ['a', 'b', 'c', 'd', 'e'] })} />);
      expect(screen.getByText('+2 more')).toBeInTheDocument();
    });

    it('renders no tag list when tags is empty', () => {
      render(<WorkflowCard workflow={makeWorkflow({ tags: [] })} />);
      expect(screen.queryByRole('list', { name: 'Tags' })).not.toBeInTheDocument();
    });

    it('renders tags as a list', () => {
      render(<WorkflowCard workflow={makeWorkflow({ tags: ['alpha', 'beta'] })} />);
      const tagList = screen.getByRole('list', { name: 'Tags' });
      const items = within(tagList).getAllByRole('listitem');
      expect(items).toHaveLength(2);
    });
  });

  describe('action buttons', () => {
    it('calls onRun when Run button is clicked', async () => {
      const user = userEvent.setup();
      const onRun = jest.fn();
      render(<WorkflowCard workflow={makeWorkflow()} onRun={onRun} />);
      await user.click(screen.getByRole('button', { name: /Run workflow/i }));
      expect(onRun).toHaveBeenCalledTimes(1);
    });

    it('calls onEdit when Edit button is clicked', async () => {
      const user = userEvent.setup();
      const onEdit = jest.fn();
      render(<WorkflowCard workflow={makeWorkflow()} onEdit={onEdit} />);
      await user.click(screen.getByRole('button', { name: /Edit workflow/i }));
      expect(onEdit).toHaveBeenCalledTimes(1);
    });

    it('disables Run button when status is "archived"', () => {
      render(<WorkflowCard workflow={makeWorkflow({ status: 'archived' })} onRun={jest.fn()} />);
      expect(screen.getByRole('button', { name: /Run workflow/i })).toBeDisabled();
    });

    it('disables Run button when status is "deprecated"', () => {
      render(<WorkflowCard workflow={makeWorkflow({ status: 'deprecated' })} onRun={jest.fn()} />);
      expect(screen.getByRole('button', { name: /Run workflow/i })).toBeDisabled();
    });

    it('disables Run button when onRun is not provided', () => {
      render(<WorkflowCard workflow={makeWorkflow()} />);
      expect(screen.getByRole('button', { name: /Run workflow/i })).toBeDisabled();
    });

    it('disables Edit button when onEdit is not provided', () => {
      render(<WorkflowCard workflow={makeWorkflow()} />);
      expect(screen.getByRole('button', { name: /Edit workflow/i })).toBeDisabled();
    });
  });

  describe('dropdown menu', () => {
    it('calls onDuplicate when Duplicate is clicked in overflow menu', async () => {
      const user = userEvent.setup();
      const onDuplicate = jest.fn();
      render(<WorkflowCard workflow={makeWorkflow()} onDuplicate={onDuplicate} />);

      await user.click(screen.getByRole('button', { name: /More options/i }));
      const duplicateItem = await screen.findByText('Duplicate');
      await user.click(duplicateItem);

      expect(onDuplicate).toHaveBeenCalledTimes(1);
    });

    it('calls onDelete when Delete is clicked in overflow menu', async () => {
      const user = userEvent.setup();
      const onDelete = jest.fn();
      render(<WorkflowCard workflow={makeWorkflow()} onDelete={onDelete} />);

      await user.click(screen.getByRole('button', { name: /More options/i }));
      const deleteItem = await screen.findByText('Delete');
      await user.click(deleteItem);

      expect(onDelete).toHaveBeenCalledTimes(1);
    });
  });

  describe('navigation link', () => {
    it('renders a link to the workflow detail page', () => {
      render(<WorkflowCard workflow={makeWorkflow({ id: 'wf-001' })} />);
      const link = screen.getByRole('link', { name: /View details for My Test Workflow/i });
      expect(link).toHaveAttribute('href', '/workflows/wf-001');
    });
  });

  describe('accessibility', () => {
    it('has an article landmark with the workflow name as accessible label', () => {
      render(<WorkflowCard workflow={makeWorkflow()} />);
      expect(screen.getByRole('article', { name: /Workflow: My Test Workflow/i })).toBeInTheDocument();
    });
  });
});

// ---------------------------------------------------------------------------
// WorkflowCardSkeleton
// ---------------------------------------------------------------------------

describe('WorkflowCardSkeleton', () => {
  it('renders without errors', () => {
    const { container } = render(<WorkflowCardSkeleton />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it('applies animate-pulse class', () => {
    const { container } = render(<WorkflowCardSkeleton />);
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });
});
