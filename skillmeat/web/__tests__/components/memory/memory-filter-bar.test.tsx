/**
 * @jest-environment jsdom
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  MemoryFilterBar,
  type MemoryFilterBarProps,
} from '@/components/memory/memory-filter-bar';

// ---------------------------------------------------------------------------
// Default props factory
// ---------------------------------------------------------------------------

function createDefaultProps(
  overrides: Partial<MemoryFilterBarProps> = {}
): MemoryFilterBarProps {
  return {
    typeFilter: 'all',
    onTypeFilterChange: jest.fn(),
    statusFilter: 'all',
    onStatusFilterChange: jest.fn(),
    showDeprecated: false,
    onShowDeprecatedChange: jest.fn(),
    sortBy: 'newest',
    onSortByChange: jest.fn(),
    searchQuery: '',
    onSearchQueryChange: jest.fn(),
    counts: {
      all: 42,
      constraint: 10,
      decision: 8,
      gotcha: 6,
      style_rule: 7,
      learning: 5,
    },
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('MemoryFilterBar', () => {
  describe('Type tabs', () => {
    it('renders all type tabs', () => {
      const props = createDefaultProps();
      render(<MemoryFilterBar {...props} />);

      expect(screen.getByRole('tab', { name: /all/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /constraints/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /decisions/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /gotchas/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /style rules/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /learnings/i })).toBeInTheDocument();
    });

    it('shows count badges when counts provided', () => {
      const props = createDefaultProps();
      render(<MemoryFilterBar {...props} />);

      // Look for count badge values -- they appear as text within Badge elements
      expect(screen.getByText('42')).toBeInTheDocument(); // all
      expect(screen.getByText('10')).toBeInTheDocument(); // constraint
      expect(screen.getByText('8')).toBeInTheDocument();  // decision
      expect(screen.getByText('7')).toBeInTheDocument();  // style_rule
      expect(screen.getByText('5')).toBeInTheDocument();  // learning
      expect(screen.getByText('6')).toBeInTheDocument(); // gotcha
    });

    it('shows zero counts when counts not provided', () => {
      const props = createDefaultProps({ counts: undefined });
      render(<MemoryFilterBar {...props} />);

      // All count badges should show 0
      const zeroBadges = screen.getAllByText('0');
      expect(zeroBadges.length).toBe(6); // One per type tab
    });

    it('calls onTypeFilterChange when tab is clicked', async () => {
      const user = userEvent.setup();
      const onTypeFilterChange = jest.fn();
      const props = createDefaultProps({ onTypeFilterChange });
      render(<MemoryFilterBar {...props} />);

      const constraintTab = screen.getByRole('tab', { name: /constraints/i });
      await user.click(constraintTab);

      expect(onTypeFilterChange).toHaveBeenCalledWith('constraint');
    });

    it('has aria-label on the tab list', () => {
      const props = createDefaultProps();
      render(<MemoryFilterBar {...props} />);

      expect(
        screen.getByRole('tablist', { name: /filter by memory type/i })
      ).toBeInTheDocument();
    });
  });

  describe('Status dropdown', () => {
    it('renders status filter button with current label', () => {
      const props = createDefaultProps({ statusFilter: 'all' });
      render(<MemoryFilterBar {...props} />);

      expect(
        screen.getByLabelText(/filter by status: all active/i)
      ).toBeInTheDocument();
    });

    it('shows the selected status label', () => {
      const props = createDefaultProps({ statusFilter: 'candidate' });
      render(<MemoryFilterBar {...props} />);

      expect(
        screen.getByLabelText(/filter by status: candidate/i)
      ).toBeInTheDocument();
    });
  });

  describe('Sort dropdown', () => {
    it('renders sort button with current label', () => {
      const props = createDefaultProps({ sortBy: 'newest' });
      render(<MemoryFilterBar {...props} />);

      expect(
        screen.getByLabelText(/sort by: newest first/i)
      ).toBeInTheDocument();
    });

    it('shows the selected sort label', () => {
      const props = createDefaultProps({ sortBy: 'confidence-desc' });
      render(<MemoryFilterBar {...props} />);

      expect(
        screen.getByLabelText(/sort by: highest confidence/i)
      ).toBeInTheDocument();
    });
  });

  describe('Search input', () => {
    it('renders search input', () => {
      const props = createDefaultProps();
      render(<MemoryFilterBar {...props} />);

      expect(
        screen.getByLabelText('Search memories')
      ).toBeInTheDocument();
    });

    it('displays current search query value', () => {
      const props = createDefaultProps({ searchQuery: 'default export' });
      render(<MemoryFilterBar {...props} />);

      const input = screen.getByLabelText('Search memories');
      expect(input).toHaveValue('default export');
    });

    it('calls onSearchQueryChange when typing', async () => {
      const user = userEvent.setup();
      const onSearchQueryChange = jest.fn();
      const props = createDefaultProps({ onSearchQueryChange });
      render(<MemoryFilterBar {...props} />);

      const input = screen.getByLabelText('Search memories');
      await user.type(input, 'test');

      // onSearchQueryChange is called once per character typed
      expect(onSearchQueryChange).toHaveBeenCalledTimes(4);
    });

    it('has placeholder text', () => {
      const props = createDefaultProps();
      render(<MemoryFilterBar {...props} />);

      expect(
        screen.getByPlaceholderText('Search memories...')
      ).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has toolbar role with label on the controls row', () => {
      const props = createDefaultProps();
      render(<MemoryFilterBar {...props} />);

      expect(
        screen.getByRole('toolbar', { name: /memory filters/i })
      ).toBeInTheDocument();
    });
  });
});
