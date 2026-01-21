/**
 * @jest-environment jsdom
 *
 * SourceFilterBar Component Tests
 *
 * Tests for the SourceFilterBar component which provides filtering controls
 * for marketplace sources including artifact type, tags, and trust level.
 *
 * Note: Radix Select components are tested via accessibility queries since
 * they don't render as native select elements.
 */

import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SourceFilterBar, type FilterState } from '@/components/marketplace/source-filter-bar';

describe('SourceFilterBar', () => {
  const defaultProps = {
    currentFilters: {} as FilterState,
    onFilterChange: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders artifact type filter', () => {
      render(<SourceFilterBar {...defaultProps} />);

      expect(screen.getByLabelText('Filter by artifact type')).toBeInTheDocument();
    });

    it('renders trust level filter', () => {
      render(<SourceFilterBar {...defaultProps} />);

      expect(screen.getByLabelText('Filter by trust level')).toBeInTheDocument();
    });

    it('renders tags filter when availableTags provided', () => {
      render(
        <SourceFilterBar {...defaultProps} availableTags={['python', 'testing', 'automation']} />
      );

      expect(screen.getByText('Tags')).toBeInTheDocument();
      // Tags in filter bar have "Add tag filter:" prefix when not selected
      expect(screen.getByLabelText('Add tag filter: python')).toBeInTheDocument();
      expect(screen.getByLabelText('Add tag filter: testing')).toBeInTheDocument();
      expect(screen.getByLabelText('Add tag filter: automation')).toBeInTheDocument();
    });

    it('does not render tags filter when no availableTags', () => {
      render(<SourceFilterBar {...defaultProps} availableTags={[]} />);

      expect(screen.queryByText('Tags')).not.toBeInTheDocument();
    });

    it('limits displayed tags to 8', () => {
      const manyTags = Array.from({ length: 12 }, (_, i) => `tag-${i}`);
      render(<SourceFilterBar {...defaultProps} availableTags={manyTags} />);

      // Should show only first 8 tags
      expect(screen.getByLabelText('Add tag filter: tag-0')).toBeInTheDocument();
      expect(screen.getByLabelText('Add tag filter: tag-7')).toBeInTheDocument();
      expect(screen.queryByLabelText(/tag filter: tag-8/)).not.toBeInTheDocument();
    });

    it('applies custom className', () => {
      const { container } = render(
        <SourceFilterBar {...defaultProps} className="custom-filter-bar" />
      );

      expect(container.firstChild).toHaveClass('custom-filter-bar');
    });

    it('renders filter controls section', () => {
      render(<SourceFilterBar {...defaultProps} />);

      // Check that the Type and Trust labels are present
      expect(screen.getByText('Type')).toBeInTheDocument();
      expect(screen.getByText('Trust')).toBeInTheDocument();
    });
  });

  describe('Tag Filter', () => {
    it('toggles tag selection on click', async () => {
      const user = userEvent.setup();
      const onFilterChange = jest.fn();

      render(
        <SourceFilterBar
          currentFilters={{}}
          onFilterChange={onFilterChange}
          availableTags={['python', 'testing']}
        />
      );

      // When not selected, aria-label is "Add tag filter: python"
      await user.click(screen.getByLabelText('Add tag filter: python'));

      expect(onFilterChange).toHaveBeenCalledWith({
        tags: ['python'],
      });
    });

    it('adds tag to existing selection', async () => {
      const user = userEvent.setup();
      const onFilterChange = jest.fn();

      render(
        <SourceFilterBar
          currentFilters={{ tags: ['python'] }}
          onFilterChange={onFilterChange}
          availableTags={['python', 'testing', 'automation']}
        />
      );

      // testing is not selected, so has "Add" prefix
      await user.click(screen.getByLabelText('Add tag filter: testing'));

      expect(onFilterChange).toHaveBeenCalledWith({
        tags: ['python', 'testing'],
      });
    });

    it('removes tag from selection when already selected', async () => {
      const user = userEvent.setup();
      const onFilterChange = jest.fn();

      render(
        <SourceFilterBar
          currentFilters={{ tags: ['python', 'testing'] }}
          onFilterChange={onFilterChange}
          availableTags={['python', 'testing', 'automation']}
        />
      );

      // python is selected, so has "Remove" prefix - but there are 2 buttons
      // Use getAllByLabelText and click the first one (in the Tags section)
      const removeButtons = screen.getAllByLabelText('Remove tag filter: python');
      await user.click(removeButtons[0]);

      expect(onFilterChange).toHaveBeenCalledWith({
        tags: ['testing'],
      });
    });

    it('clears tags array when last tag is removed', async () => {
      const user = userEvent.setup();
      const onFilterChange = jest.fn();

      render(
        <SourceFilterBar
          currentFilters={{ tags: ['python'] }}
          onFilterChange={onFilterChange}
          availableTags={['python', 'testing']}
        />
      );

      // python is selected, so has "Remove" prefix
      const removeButtons = screen.getAllByLabelText('Remove tag filter: python');
      await user.click(removeButtons[0]);

      expect(onFilterChange).toHaveBeenCalledWith({
        tags: undefined,
      });
    });

    it('shows visual indication for selected tags via aria-pressed', () => {
      render(
        <SourceFilterBar
          currentFilters={{ tags: ['python'] }}
          onFilterChange={jest.fn()}
          availableTags={['python', 'testing']}
        />
      );

      // python is selected so has "Remove" prefix, testing has "Add" prefix
      const pythonButtons = screen.getAllByLabelText('Remove tag filter: python');
      // First one is in Tags section, has aria-pressed
      expect(pythonButtons[0]).toHaveAttribute('aria-pressed', 'true');

      const testingTag = screen.getByLabelText('Add tag filter: testing');
      expect(testingTag).toHaveAttribute('aria-pressed', 'false');
    });

    it('supports keyboard activation with Enter', async () => {
      const user = userEvent.setup();
      const onFilterChange = jest.fn();

      render(
        <SourceFilterBar
          currentFilters={{}}
          onFilterChange={onFilterChange}
          availableTags={['python']}
        />
      );

      const tagButton = screen.getByLabelText('Add tag filter: python');
      tagButton.focus();
      await user.keyboard('{Enter}');

      expect(onFilterChange).toHaveBeenCalledWith({
        tags: ['python'],
      });
    });

    it('supports keyboard activation with Space', async () => {
      const user = userEvent.setup();
      const onFilterChange = jest.fn();

      render(
        <SourceFilterBar
          currentFilters={{}}
          onFilterChange={onFilterChange}
          availableTags={['python']}
        />
      );

      const tagButton = screen.getByLabelText('Add tag filter: python');
      tagButton.focus();
      await user.keyboard(' ');

      expect(onFilterChange).toHaveBeenCalledWith({
        tags: ['python'],
      });
    });
  });

  describe('Clear Filters', () => {
    it('shows clear all button when filters are active', () => {
      render(
        <SourceFilterBar currentFilters={{ artifact_type: 'skill' }} onFilterChange={jest.fn()} />
      );

      expect(screen.getByRole('button', { name: 'Clear all filters' })).toBeInTheDocument();
    });

    it('hides clear all button when no filters active', () => {
      render(<SourceFilterBar {...defaultProps} />);

      expect(screen.queryByRole('button', { name: 'Clear all filters' })).not.toBeInTheDocument();
    });

    it('calls onFilterChange with empty object when clear all clicked', async () => {
      const user = userEvent.setup();
      const onFilterChange = jest.fn();

      render(
        <SourceFilterBar
          currentFilters={{ artifact_type: 'skill', trust_level: 'verified', tags: ['python'] }}
          onFilterChange={onFilterChange}
        />
      );

      await user.click(screen.getByRole('button', { name: 'Clear all filters' }));

      expect(onFilterChange).toHaveBeenCalledWith({});
    });

    it('removes individual artifact_type filter via active filter badge', async () => {
      const user = userEvent.setup();
      const onFilterChange = jest.fn();

      render(
        <SourceFilterBar
          currentFilters={{ artifact_type: 'skill' }}
          onFilterChange={onFilterChange}
        />
      );

      const removeButton = screen.getByRole('button', {
        name: 'Remove artifact type filter: skill',
      });
      await user.click(removeButton);

      expect(onFilterChange).toHaveBeenCalledWith({});
    });

    it('removes individual trust_level filter via active filter badge', async () => {
      const user = userEvent.setup();
      const onFilterChange = jest.fn();

      render(
        <SourceFilterBar
          currentFilters={{ trust_level: 'verified' }}
          onFilterChange={onFilterChange}
        />
      );

      const removeButton = screen.getByRole('button', {
        name: 'Remove trust level filter: verified',
      });
      await user.click(removeButton);

      expect(onFilterChange).toHaveBeenCalledWith({});
    });

    it('removes individual tag via active filter badge', async () => {
      const user = userEvent.setup();
      const onFilterChange = jest.fn();

      render(
        <SourceFilterBar
          currentFilters={{ tags: ['python', 'testing'] }}
          onFilterChange={onFilterChange}
          availableTags={['python', 'testing', 'automation']}
        />
      );

      // Get the active filters section and click the remove button there
      const activeFiltersSection = screen.getByText('Active filters:').parentElement;
      const removeButton = within(activeFiltersSection!).getAllByLabelText(
        'Remove tag filter: python'
      )[0];
      await user.click(removeButton);

      expect(onFilterChange).toHaveBeenCalledWith({
        tags: ['testing'],
      });
    });
  });

  describe('Active Filters Display', () => {
    it('shows active filters section when filters present', () => {
      render(
        <SourceFilterBar currentFilters={{ artifact_type: 'skill' }} onFilterChange={jest.fn()} />
      );

      expect(screen.getByText('Active filters:')).toBeInTheDocument();
    });

    it('hides active filters section when no filters', () => {
      render(<SourceFilterBar {...defaultProps} />);

      expect(screen.queryByText('Active filters:')).not.toBeInTheDocument();
    });

    it('displays correct filter count for single filter', () => {
      render(
        <SourceFilterBar currentFilters={{ artifact_type: 'skill' }} onFilterChange={jest.fn()} />
      );

      expect(screen.getByText('(1 filter)')).toBeInTheDocument();
    });

    it('displays correct filter count for multiple filters', () => {
      render(
        <SourceFilterBar
          currentFilters={{ artifact_type: 'skill', trust_level: 'verified', tags: ['python'] }}
          onFilterChange={jest.fn()}
        />
      );

      expect(screen.getByText('(3 filters)')).toBeInTheDocument();
    });

    it('counts each tag as a separate filter', () => {
      render(
        <SourceFilterBar
          currentFilters={{ tags: ['python', 'testing', 'automation'] }}
          onFilterChange={jest.fn()}
        />
      );

      expect(screen.getByText('(3 filters)')).toBeInTheDocument();
    });

    it('shows artifact type badge with correct label', () => {
      render(
        <SourceFilterBar currentFilters={{ artifact_type: 'skill' }} onFilterChange={jest.fn()} />
      );

      expect(screen.getByText('Type: skill')).toBeInTheDocument();
    });

    it('shows trust level badge with correct label', () => {
      render(
        <SourceFilterBar currentFilters={{ trust_level: 'verified' }} onFilterChange={jest.fn()} />
      );

      expect(screen.getByText('Trust: verified')).toBeInTheDocument();
    });

    it('shows tag badges in active filters', () => {
      render(
        <SourceFilterBar
          currentFilters={{ tags: ['python', 'testing'] }}
          onFilterChange={jest.fn()}
        />
      );

      // The tags should appear in active filters section as badges
      const activeFiltersSection = screen.getByText('Active filters:').parentElement;
      expect(within(activeFiltersSection!).getByText('python')).toBeInTheDocument();
      expect(within(activeFiltersSection!).getByText('testing')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has accessible labels for filter controls', () => {
      render(<SourceFilterBar {...defaultProps} availableTags={['python']} />);

      expect(screen.getByLabelText('Filter by artifact type')).toBeInTheDocument();
      expect(screen.getByLabelText('Filter by trust level')).toBeInTheDocument();
    });

    it('tag buttons have aria-pressed state', () => {
      render(
        <SourceFilterBar
          currentFilters={{ tags: ['python'] }}
          onFilterChange={jest.fn()}
          availableTags={['python', 'testing']}
        />
      );

      // python is selected, so first Remove button (in Tags section) has aria-pressed
      const pythonButtons = screen.getAllByLabelText('Remove tag filter: python');
      expect(pythonButtons[0]).toHaveAttribute('aria-pressed', 'true');

      const testingTag = screen.getByLabelText('Add tag filter: testing');
      expect(testingTag).toHaveAttribute('aria-pressed', 'false');
    });

    it('remove buttons have descriptive aria-labels', () => {
      render(
        <SourceFilterBar
          currentFilters={{ artifact_type: 'skill', trust_level: 'verified', tags: ['python'] }}
          onFilterChange={jest.fn()}
        />
      );

      expect(
        screen.getByRole('button', { name: 'Remove artifact type filter: skill' })
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: 'Remove trust level filter: verified' })
      ).toBeInTheDocument();
      // There will be multiple "Remove tag filter: python" buttons
      expect(screen.getAllByLabelText('Remove tag filter: python').length).toBeGreaterThan(0);
    });

    it('labels are associated with their controls', () => {
      render(<SourceFilterBar {...defaultProps} />);

      // Check that labels point to correct inputs
      const typeLabel = screen.getByText('Type');
      const trustLabel = screen.getByText('Trust');

      expect(typeLabel).toHaveAttribute('for', 'artifact-type-filter');
      expect(trustLabel).toHaveAttribute('for', 'trust-level-filter');
    });
  });
});
