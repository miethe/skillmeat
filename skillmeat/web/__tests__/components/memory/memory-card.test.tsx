/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryCard, type MemoryCardProps } from '@/components/memory/memory-card';
import type { MemoryItemResponse } from '@/sdk/models/MemoryItemResponse';

// ---------------------------------------------------------------------------
// Mock data factory
// ---------------------------------------------------------------------------

function createMockMemory(overrides: Partial<MemoryItemResponse> = {}): MemoryItemResponse {
  return {
    id: 'test-id-1',
    project_id: 'project-1',
    type: 'constraint',
    content: 'Do not use default exports in components',
    confidence: 0.87,
    status: 'candidate',
    provenance: { source_type: 'session-abc123' },
    anchors: ['skillmeat/web/components'],
    ttl_policy: null,
    content_hash: 'hash123',
    access_count: 3,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    deprecated_at: null,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Default props factory
// ---------------------------------------------------------------------------

function createDefaultProps(overrides: Partial<MemoryCardProps> = {}): MemoryCardProps {
  return {
    memory: createMockMemory(),
    selected: false,
    focused: false,
    onToggleSelect: jest.fn(),
    onApprove: jest.fn(),
    onReject: jest.fn(),
    onEdit: jest.fn(),
    onMerge: jest.fn(),
    onClick: jest.fn(),
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('MemoryCard', () => {
  describe('Rendering', () => {
    it('renders memory content', () => {
      const props = createDefaultProps();
      render(<MemoryCard {...props} />);

      expect(
        screen.getByText('Do not use default exports in components')
      ).toBeInTheDocument();
    });

    it('renders type badge', () => {
      const props = createDefaultProps();
      render(<MemoryCard {...props} />);

      expect(screen.getByText('Constraint')).toBeInTheDocument();
    });

    it('renders confidence percentage', () => {
      const props = createDefaultProps();
      render(<MemoryCard {...props} />);

      expect(screen.getByText('87%')).toBeInTheDocument();
    });

    it('renders relative time from created_at', () => {
      const props = createDefaultProps();
      render(<MemoryCard {...props} />);

      // Created just now, so "just now" should appear
      expect(screen.getByText('just now')).toBeInTheDocument();
    });

    it('renders access count', () => {
      const props = createDefaultProps();
      render(<MemoryCard {...props} />);

      expect(screen.getByText('Used 3x')).toBeInTheDocument();
    });

    it('renders provenance source_type', () => {
      const props = createDefaultProps();
      render(<MemoryCard {...props} />);

      expect(screen.getByText('session-abc123')).toBeInTheDocument();
    });

    it('renders status label', () => {
      const props = createDefaultProps();
      render(<MemoryCard {...props} />);

      expect(screen.getByText('candidate')).toBeInTheDocument();
    });
  });

  describe('Confidence Tiers', () => {
    it('shows high confidence color for >= 0.85', () => {
      const props = createDefaultProps({
        memory: createMockMemory({ confidence: 0.92 }),
      });
      render(<MemoryCard {...props} />);

      const percent = screen.getByText('92%');
      expect(percent).toHaveClass('text-emerald-700');
    });

    it('shows medium confidence color for >= 0.60', () => {
      const props = createDefaultProps({
        memory: createMockMemory({ confidence: 0.72 }),
      });
      render(<MemoryCard {...props} />);

      const percent = screen.getByText('72%');
      expect(percent).toHaveClass('text-amber-700');
    });

    it('shows low confidence color for < 0.60', () => {
      const props = createDefaultProps({
        memory: createMockMemory({ confidence: 0.35 }),
      });
      render(<MemoryCard {...props} />);

      const percent = screen.getByText('35%');
      expect(percent).toHaveClass('text-red-700');
    });
  });

  describe('Interactions', () => {
    it('calls onClick when card is clicked', async () => {
      const user = userEvent.setup();
      const onClick = jest.fn();
      const props = createDefaultProps({ onClick });
      render(<MemoryCard {...props} />);

      const row = screen.getByRole('row');
      await user.click(row);

      expect(onClick).toHaveBeenCalledWith('test-id-1');
    });

    it('calls onToggleSelect when checkbox is clicked', async () => {
      const user = userEvent.setup();
      const onToggleSelect = jest.fn();
      const props = createDefaultProps({ onToggleSelect });
      render(<MemoryCard {...props} />);

      const checkbox = screen.getByRole('checkbox');
      await user.click(checkbox);

      expect(onToggleSelect).toHaveBeenCalledWith('test-id-1');
    });

    it('does not call onClick when checkbox is clicked', async () => {
      const user = userEvent.setup();
      const onClick = jest.fn();
      const onToggleSelect = jest.fn();
      const props = createDefaultProps({ onClick, onToggleSelect });
      render(<MemoryCard {...props} />);

      const checkbox = screen.getByRole('checkbox');
      await user.click(checkbox);

      // onToggleSelect should fire, but onClick should NOT fire
      expect(onToggleSelect).toHaveBeenCalled();
      expect(onClick).not.toHaveBeenCalled();
    });

    it('calls onApprove when approve button is clicked', async () => {
      const user = userEvent.setup();
      const onApprove = jest.fn();
      const memory = createMockMemory();
      const props = createDefaultProps({ onApprove, memory });
      render(<MemoryCard {...props} />);

      const approveButton = screen.getByLabelText(
        `Approve memory: ${memory.content.slice(0, 40)}`
      );
      await user.click(approveButton);

      expect(onApprove).toHaveBeenCalledWith('test-id-1');
    });

    it('calls onReject when reject button is clicked', async () => {
      const user = userEvent.setup();
      const onReject = jest.fn();
      const memory = createMockMemory();
      const props = createDefaultProps({ onReject, memory });
      render(<MemoryCard {...props} />);

      const rejectButton = screen.getByLabelText(
        `Reject memory: ${memory.content.slice(0, 40)}`
      );
      await user.click(rejectButton);

      expect(onReject).toHaveBeenCalledWith('test-id-1');
    });

    it('calls onEdit when edit button is clicked', async () => {
      const user = userEvent.setup();
      const onEdit = jest.fn();
      const memory = createMockMemory();
      const props = createDefaultProps({ onEdit, memory });
      render(<MemoryCard {...props} />);

      const editButton = screen.getByLabelText(
        `Edit memory: ${memory.content.slice(0, 40)}`
      );
      await user.click(editButton);

      expect(onEdit).toHaveBeenCalledWith('test-id-1');
    });

    it('does not call onClick when approve button is clicked', async () => {
      const user = userEvent.setup();
      const onClick = jest.fn();
      const onApprove = jest.fn();
      const memory = createMockMemory();
      const props = createDefaultProps({ onClick, onApprove, memory });
      render(<MemoryCard {...props} />);

      const approveButton = screen.getByLabelText(
        `Approve memory: ${memory.content.slice(0, 40)}`
      );
      await user.click(approveButton);

      expect(onApprove).toHaveBeenCalled();
      expect(onClick).not.toHaveBeenCalled();
    });
  });

  describe('Action button visibility', () => {
    it('renders action buttons in the DOM', () => {
      const memory = createMockMemory();
      const props = createDefaultProps({ memory });
      render(<MemoryCard {...props} />);

      expect(
        screen.getByLabelText(`Approve memory: ${memory.content.slice(0, 40)}`)
      ).toBeInTheDocument();
      expect(
        screen.getByLabelText(`Edit memory: ${memory.content.slice(0, 40)}`)
      ).toBeInTheDocument();
      expect(
        screen.getByLabelText(`Reject memory: ${memory.content.slice(0, 40)}`)
      ).toBeInTheDocument();
    });
  });

  describe('Visual states', () => {
    it('applies focused styling when focused is true', () => {
      const props = createDefaultProps({ focused: true });
      render(<MemoryCard {...props} />);

      const row = screen.getByRole('row');
      expect(row).toHaveClass('bg-accent/70');
      expect(row).toHaveClass('ring-1');
    });

    it('does not apply focused styling when focused is false', () => {
      const props = createDefaultProps({ focused: false });
      render(<MemoryCard {...props} />);

      const row = screen.getByRole('row');
      expect(row).not.toHaveClass('bg-accent/70');
    });

    it('applies selected styling when selected is true', () => {
      const props = createDefaultProps({ selected: true });
      render(<MemoryCard {...props} />);

      const row = screen.getByRole('row');
      expect(row).toHaveClass('bg-primary/5');
    });

    it('does not apply selected styling when selected is false', () => {
      const props = createDefaultProps({ selected: false });
      render(<MemoryCard {...props} />);

      const row = screen.getByRole('row');
      expect(row).not.toHaveClass('bg-primary/5');
    });

    it('shows correct status dot', () => {
      const props = createDefaultProps({
        memory: createMockMemory({ status: 'active' }),
      });
      const { container } = render(<MemoryCard {...props} />);

      // The status dot is a span with aria-hidden="true" and a bg class
      const dots = container.querySelectorAll('span[aria-hidden="true"]');
      const statusDot = Array.from(dots).find((el) =>
        el.classList.contains('rounded-full') && el.classList.contains('h-1.5')
      );
      expect(statusDot).toBeTruthy();
      expect(statusDot).toHaveClass('bg-emerald-400');
    });
  });

  describe('Keyboard navigation', () => {
    it('triggers onClick on Enter key', () => {
      const onClick = jest.fn();
      const props = createDefaultProps({ onClick });
      render(<MemoryCard {...props} />);

      const row = screen.getByRole('row');
      fireEvent.keyDown(row, { key: 'Enter' });

      expect(onClick).toHaveBeenCalledWith('test-id-1');
    });

    it('triggers onToggleSelect on Space key', () => {
      const onToggleSelect = jest.fn();
      const props = createDefaultProps({ onToggleSelect });
      render(<MemoryCard {...props} />);

      const row = screen.getByRole('row');
      fireEvent.keyDown(row, { key: ' ' });

      expect(onToggleSelect).toHaveBeenCalledWith('test-id-1');
    });

    it('prevents default on Space to avoid scrolling', () => {
      const onToggleSelect = jest.fn();
      const props = createDefaultProps({ onToggleSelect });
      render(<MemoryCard {...props} />);

      const row = screen.getByRole('row');
      const event = new KeyboardEvent('keydown', {
        key: ' ',
        bubbles: true,
        cancelable: true,
      });
      const preventDefaultSpy = jest.spyOn(event, 'preventDefault');

      row.dispatchEvent(event);

      expect(preventDefaultSpy).toHaveBeenCalled();
    });
  });

  describe('Accessibility', () => {
    it('has role="row"', () => {
      const props = createDefaultProps();
      render(<MemoryCard {...props} />);

      expect(screen.getByRole('row')).toBeInTheDocument();
    });

    it('has aria-selected matching selected prop', () => {
      const props = createDefaultProps({ selected: true });
      render(<MemoryCard {...props} />);

      expect(screen.getByRole('row')).toHaveAttribute('aria-selected', 'true');
    });

    it('has aria-selected false when not selected', () => {
      const props = createDefaultProps({ selected: false });
      render(<MemoryCard {...props} />);

      expect(screen.getByRole('row')).toHaveAttribute('aria-selected', 'false');
    });

    it('has descriptive aria-label', () => {
      const props = createDefaultProps();
      render(<MemoryCard {...props} />);

      const row = screen.getByRole('row');
      expect(row).toHaveAttribute(
        'aria-label',
        'Memory item: constraint, 87% confidence, candidate'
      );
    });

    it('has tabIndex=0 when focused', () => {
      const props = createDefaultProps({ focused: true });
      render(<MemoryCard {...props} />);

      expect(screen.getByRole('row')).toHaveAttribute('tabindex', '0');
    });

    it('has tabIndex=-1 when not focused', () => {
      const props = createDefaultProps({ focused: false });
      render(<MemoryCard {...props} />);

      expect(screen.getByRole('row')).toHaveAttribute('tabindex', '-1');
    });

    it('checkbox has aria-label for the memory content', () => {
      const props = createDefaultProps();
      render(<MemoryCard {...props} />);

      const checkbox = screen.getByRole('checkbox');
      expect(checkbox).toHaveAttribute(
        'aria-label',
        'Select memory: Do not use default exports in components'
      );
    });
  });
});
