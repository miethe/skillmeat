/**
 * @jest-environment jsdom
 *
 * Tests for StageCard component.
 *
 * Focus areas:
 *   - Edit mode: drag handle, edit/delete buttons, inline-editable title
 *   - Readonly mode: no drag handle, no edit/delete, footer with timeout/retry
 *   - onEdit and onDelete callbacks fire correctly
 *   - onTitleChange fires when title is edited (via InlineEdit)
 *   - Selected state applies ring highlight
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StageCard } from '@/components/workflow/stage-card';
import type { WorkflowStage } from '@/types/workflow';

// ---------------------------------------------------------------------------
// Mock InlineEdit — keep the component surface shallow; test title-change
// callback without pulling in the real InlineEdit keyboard behaviour.
// ---------------------------------------------------------------------------
jest.mock('@/components/shared/inline-edit', () => ({
  InlineEdit: ({
    value,
    onChange,
    placeholder,
  }: {
    value: string;
    onChange: (v: string) => void;
    placeholder?: string;
  }) => (
    <input
      aria-label="Stage title"
      defaultValue={value}
      placeholder={placeholder}
      onBlur={(e) => onChange(e.target.value)}
      onChange={(e) => onChange(e.target.value)}
    />
  ),
}));

// ---------------------------------------------------------------------------
// Fixture
// ---------------------------------------------------------------------------

function makeStage(overrides: Partial<WorkflowStage> = {}): WorkflowStage {
  return {
    id: 'stage-001',
    stageIdRef: 'code-review',
    name: 'Code Review',
    description: 'Automated code quality check',
    orderIndex: 0,
    stageType: 'agent',
    dependsOn: [],
    inputs: {},
    outputs: {},
    roles: {
      primary: { artifact: 'agent:reviewer-v1' },
      tools: ['skill:linter', 'skill:formatter'],
    },
    context: {
      modules: ['ctx:coding-standards'],
    },
    errorPolicy: {
      onFailure: 'halt',
      timeout: '30m',
      retry: { maxAttempts: 3, initialInterval: '30s', backoffMultiplier: 2, maxInterval: '5m', nonRetryableErrors: [] },
    },
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Edit mode
// ---------------------------------------------------------------------------

describe('StageCard — edit mode', () => {
  it('shows a drag handle button', () => {
    render(<StageCard stage={makeStage()} index={0} mode="edit" />);
    expect(screen.getByRole('button', { name: /Drag to reorder stage/i })).toBeInTheDocument();
  });

  it('shows an edit button', () => {
    render(<StageCard stage={makeStage()} index={0} mode="edit" onEdit={jest.fn()} />);
    expect(screen.getByRole('button', { name: /Edit stage: Code Review/i })).toBeInTheDocument();
  });

  it('shows a delete button', () => {
    render(<StageCard stage={makeStage()} index={0} mode="edit" onDelete={jest.fn()} />);
    expect(screen.getByRole('button', { name: /Delete stage: Code Review/i })).toBeInTheDocument();
  });

  it('calls onEdit when the edit button is clicked', async () => {
    const user = userEvent.setup();
    const onEdit = jest.fn();
    render(<StageCard stage={makeStage()} index={0} mode="edit" onEdit={onEdit} />);
    await user.click(screen.getByRole('button', { name: /Edit stage/i }));
    expect(onEdit).toHaveBeenCalledTimes(1);
  });

  it('calls onDelete when the delete button is clicked', async () => {
    const user = userEvent.setup();
    const onDelete = jest.fn();
    render(<StageCard stage={makeStage()} index={0} mode="edit" onDelete={onDelete} />);
    await user.click(screen.getByRole('button', { name: /Delete stage/i }));
    expect(onDelete).toHaveBeenCalledTimes(1);
  });

  it('renders InlineEdit for the stage title when onTitleChange is provided', () => {
    render(
      <StageCard stage={makeStage()} index={0} mode="edit" onTitleChange={jest.fn()} />
    );
    expect(screen.getByRole('textbox', { name: /Stage title/i })).toBeInTheDocument();
  });

  it('calls onTitleChange when the title input changes', async () => {
    const user = userEvent.setup();
    const onTitleChange = jest.fn();
    render(
      <StageCard stage={makeStage()} index={0} mode="edit" onTitleChange={onTitleChange} />
    );
    const input = screen.getByRole('textbox', { name: /Stage title/i });
    await user.clear(input);
    await user.type(input, 'New Name');
    // onTitleChange fires on each keystroke via our mock's onChange
    expect(onTitleChange).toHaveBeenCalled();
    expect(onTitleChange).toHaveBeenLastCalledWith('New Name');
  });

  it('does not show the footer (timeout/retry) in edit mode', () => {
    render(<StageCard stage={makeStage()} index={0} mode="edit" />);
    expect(screen.queryByLabelText('Stage configuration')).not.toBeInTheDocument();
  });

  describe('selected state', () => {
    it('applies ring-2 ring-primary classes when isSelected is true', () => {
      const { container } = render(
        <StageCard stage={makeStage()} index={0} mode="edit" isSelected />
      );
      const card = container.firstChild as HTMLElement;
      expect(card.className).toMatch(/ring-2/);
      expect(card.className).toMatch(/ring-primary/);
    });

    it('does not apply ring classes when isSelected is false', () => {
      const { container } = render(
        <StageCard stage={makeStage()} index={0} mode="edit" isSelected={false} />
      );
      const card = container.firstChild as HTMLElement;
      expect(card.className).not.toMatch(/ring-2/);
    });
  });

  it('shows the stage number badge', () => {
    render(<StageCard stage={makeStage()} index={2} mode="edit" />);
    expect(screen.getByLabelText('Stage 3')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Readonly mode
// ---------------------------------------------------------------------------

describe('StageCard — readonly mode', () => {
  it('does not show a drag handle', () => {
    render(<StageCard stage={makeStage()} index={0} mode="readonly" />);
    expect(screen.queryByRole('button', { name: /Drag to reorder/i })).not.toBeInTheDocument();
  });

  it('does not show an edit button', () => {
    render(<StageCard stage={makeStage()} index={0} mode="readonly" />);
    expect(screen.queryByRole('button', { name: /Edit stage/i })).not.toBeInTheDocument();
  });

  it('does not show a delete button', () => {
    render(<StageCard stage={makeStage()} index={0} mode="readonly" />);
    expect(screen.queryByRole('button', { name: /Delete stage/i })).not.toBeInTheDocument();
  });

  it('renders the stage title as plain text (not an input)', () => {
    render(<StageCard stage={makeStage()} index={0} mode="readonly" />);
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    expect(screen.getByText('Code Review')).toBeInTheDocument();
  });

  it('shows the timeout in the footer when errorPolicy.timeout is set', () => {
    render(<StageCard stage={makeStage()} index={0} mode="readonly" />);
    expect(screen.getByLabelText('Stage configuration')).toBeInTheDocument();
    expect(screen.getByText(/Timeout: 30m/i)).toBeInTheDocument();
  });

  it('shows retry count in the footer when errorPolicy.retry.maxAttempts is set', () => {
    render(<StageCard stage={makeStage()} index={0} mode="readonly" />);
    // maxAttempts=3 → "Retries: 2" (subtract 1 for the initial attempt)
    expect(screen.getByText(/Retries: 2/i)).toBeInTheDocument();
  });

  it('shows "No retries" when maxAttempts is 1', () => {
    const stage = makeStage({
      errorPolicy: {
        onFailure: 'halt',
        timeout: '10m',
        retry: { maxAttempts: 1, initialInterval: '30s', backoffMultiplier: 2, maxInterval: '5m', nonRetryableErrors: [] },
      },
    });
    render(<StageCard stage={stage} index={0} mode="readonly" />);
    expect(screen.getByText(/No retries/i)).toBeInTheDocument();
  });

  it('does not show footer when no errorPolicy', () => {
    const stage = makeStage({ errorPolicy: undefined });
    render(<StageCard stage={stage} index={0} mode="readonly" />);
    expect(screen.queryByLabelText('Stage configuration')).not.toBeInTheDocument();
  });

  it('shows the stage description when provided', () => {
    render(<StageCard stage={makeStage()} index={0} mode="readonly" />);
    expect(screen.getByText('Automated code quality check')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Summary rows (both modes)
// ---------------------------------------------------------------------------

describe('StageCard — summary rows', () => {
  it('displays the primary agent name extracted from the artifact reference', () => {
    render(<StageCard stage={makeStage()} index={0} mode="edit" />);
    expect(screen.getByText('reviewer-v1')).toBeInTheDocument();
  });

  it('shows "No agent assigned" when no primary role', () => {
    const stage = makeStage({ roles: undefined });
    render(<StageCard stage={stage} index={0} mode="edit" />);
    expect(screen.getByText(/No agent assigned/i)).toBeInTheDocument();
  });

  it('renders tool badges for each tool in roles.tools', () => {
    render(<StageCard stage={makeStage()} index={0} mode="edit" />);
    expect(screen.getByText('skill:linter')).toBeInTheDocument();
    expect(screen.getByText('skill:formatter')).toBeInTheDocument();
  });

  it('shows "No tools" when roles.tools is empty', () => {
    const stage = makeStage({ roles: { primary: { artifact: 'agent:a' }, tools: [] } });
    render(<StageCard stage={stage} index={0} mode="edit" />);
    expect(screen.getByText(/No tools/i)).toBeInTheDocument();
  });

  it('renders context module badges', () => {
    render(<StageCard stage={makeStage()} index={0} mode="edit" />);
    expect(screen.getByText('ctx:coding-standards')).toBeInTheDocument();
  });

  it('shows "No context" when context.modules is empty', () => {
    const stage = makeStage({ context: { modules: [] } });
    render(<StageCard stage={stage} index={0} mode="edit" />);
    expect(screen.getByText(/No context/i)).toBeInTheDocument();
  });
});
