/**
 * @jest-environment jsdom
 *
 * Sources Page Filter Integration Tests
 *
 * These tests verify the integration between the SourceFilterBar component
 * and filter state management. Full page integration is better tested in E2E.
 *
 * Note: These tests focus on component integration rather than full page rendering
 * since the sources page has complex dependencies (TanStack Query, Next.js navigation).
 */

import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SourceFilterBar, type FilterState } from '@/components/marketplace/source-filter-bar';

describe('SourceFilterBar Integration', () => {
  const availableTags = ['python', 'testing', 'automation', 'ci-cd'];

  describe('Filter State Management', () => {
    it('maintains filter state correctly when adding filters', async () => {
      const user = userEvent.setup();
      let currentFilters: FilterState = {};

      const onFilterChange = (newFilters: FilterState) => {
        currentFilters = newFilters;
      };

      const { rerender } = render(
        <SourceFilterBar
          currentFilters={currentFilters}
          onFilterChange={onFilterChange}
          availableTags={availableTags}
        />
      );

      // Add first tag
      await user.click(screen.getByLabelText('Add tag filter: python'));
      expect(currentFilters).toEqual({ tags: ['python'] });

      // Rerender with updated state
      rerender(
        <SourceFilterBar
          currentFilters={currentFilters}
          onFilterChange={onFilterChange}
          availableTags={availableTags}
        />
      );

      // Add second tag
      await user.click(screen.getByLabelText('Add tag filter: testing'));
      expect(currentFilters.tags).toContain('python');
      expect(currentFilters.tags).toContain('testing');
    });

    it('removes filter correctly', async () => {
      const user = userEvent.setup();
      let currentFilters: FilterState = { tags: ['python', 'testing'] };

      const onFilterChange = (newFilters: FilterState) => {
        currentFilters = newFilters;
      };

      render(
        <SourceFilterBar
          currentFilters={currentFilters}
          onFilterChange={onFilterChange}
          availableTags={availableTags}
        />
      );

      // Remove python tag using the first Remove button (in Tags section)
      const removeButtons = screen.getAllByLabelText('Remove tag filter: python');
      await user.click(removeButtons[0]);

      expect(currentFilters.tags).toEqual(['testing']);
    });

    it('clears all filters', async () => {
      const user = userEvent.setup();
      let currentFilters: FilterState = {
        artifact_type: 'skill',
        trust_level: 'verified',
        tags: ['python'],
      };

      const onFilterChange = (newFilters: FilterState) => {
        currentFilters = newFilters;
      };

      render(
        <SourceFilterBar
          currentFilters={currentFilters}
          onFilterChange={onFilterChange}
          availableTags={availableTags}
        />
      );

      await user.click(screen.getByRole('button', { name: 'Clear all filters' }));

      expect(currentFilters).toEqual({});
    });
  });

  describe('Active Filters Display', () => {
    it('shows correct filter count', () => {
      render(
        <SourceFilterBar
          currentFilters={{
            artifact_type: 'skill',
            trust_level: 'verified',
            tags: ['python', 'testing'],
          }}
          onFilterChange={jest.fn()}
          availableTags={availableTags}
        />
      );

      // 1 artifact_type + 1 trust_level + 2 tags = 4 filters
      expect(screen.getByText('(4 filters)')).toBeInTheDocument();
    });

    it('displays active filter badges', () => {
      render(
        <SourceFilterBar
          currentFilters={{
            artifact_type: 'skill',
            trust_level: 'verified',
            tags: ['python'],
          }}
          onFilterChange={jest.fn()}
          availableTags={availableTags}
        />
      );

      expect(screen.getByText('Type: skill')).toBeInTheDocument();
      expect(screen.getByText('Trust: verified')).toBeInTheDocument();

      const activeFiltersSection = screen.getByText('Active filters:').parentElement;
      expect(within(activeFiltersSection!).getByText('python')).toBeInTheDocument();
    });
  });

  describe('Tag Selection UI', () => {
    it('shows selected state for active tags', () => {
      render(
        <SourceFilterBar
          currentFilters={{ tags: ['python'] }}
          onFilterChange={jest.fn()}
          availableTags={availableTags}
        />
      );

      const pythonButtons = screen.getAllByLabelText('Remove tag filter: python');
      expect(pythonButtons[0]).toHaveAttribute('aria-pressed', 'true');

      const testingButton = screen.getByLabelText('Add tag filter: testing');
      expect(testingButton).toHaveAttribute('aria-pressed', 'false');
    });

    it('limits visible tags to 8', () => {
      const manyTags = Array.from({ length: 12 }, (_, i) => `tag-${i}`);

      render(
        <SourceFilterBar
          currentFilters={{}}
          onFilterChange={jest.fn()}
          availableTags={manyTags}
        />
      );

      expect(screen.getByLabelText('Add tag filter: tag-0')).toBeInTheDocument();
      expect(screen.getByLabelText('Add tag filter: tag-7')).toBeInTheDocument();
      expect(screen.queryByLabelText(/tag filter: tag-8/)).not.toBeInTheDocument();
    });
  });

  describe('Keyboard Navigation', () => {
    it('tag buttons are keyboard accessible', async () => {
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

      expect(onFilterChange).toHaveBeenCalledWith({ tags: ['python'] });
    });

    it('clear all button is keyboard accessible', async () => {
      const user = userEvent.setup();
      const onFilterChange = jest.fn();

      render(
        <SourceFilterBar
          currentFilters={{ artifact_type: 'skill' }}
          onFilterChange={onFilterChange}
          availableTags={availableTags}
        />
      );

      const clearButton = screen.getByRole('button', { name: 'Clear all filters' });
      clearButton.focus();
      await user.keyboard('{Enter}');

      expect(onFilterChange).toHaveBeenCalledWith({});
    });
  });

  describe('Filter Combinations', () => {
    it('preserves other filters when adding a tag', async () => {
      const user = userEvent.setup();
      let currentFilters: FilterState = {
        artifact_type: 'skill',
        trust_level: 'verified',
      };

      const onFilterChange = (newFilters: FilterState) => {
        currentFilters = newFilters;
      };

      render(
        <SourceFilterBar
          currentFilters={currentFilters}
          onFilterChange={onFilterChange}
          availableTags={availableTags}
        />
      );

      await user.click(screen.getByLabelText('Add tag filter: python'));

      expect(currentFilters).toEqual({
        artifact_type: 'skill',
        trust_level: 'verified',
        tags: ['python'],
      });
    });

    it('preserves tags when removing other filters', async () => {
      const user = userEvent.setup();
      let currentFilters: FilterState = {
        artifact_type: 'skill',
        tags: ['python', 'testing'],
      };

      const onFilterChange = (newFilters: FilterState) => {
        currentFilters = newFilters;
      };

      render(
        <SourceFilterBar
          currentFilters={currentFilters}
          onFilterChange={onFilterChange}
          availableTags={availableTags}
        />
      );

      // Remove artifact_type filter
      await user.click(screen.getByRole('button', { name: 'Remove artifact type filter: skill' }));

      expect(currentFilters.artifact_type).toBeUndefined();
      expect(currentFilters.tags).toEqual(['python', 'testing']);
    });
  });

  describe('Empty States', () => {
    it('hides clear button when no filters', () => {
      render(
        <SourceFilterBar
          currentFilters={{}}
          onFilterChange={jest.fn()}
          availableTags={availableTags}
        />
      );

      expect(screen.queryByRole('button', { name: 'Clear all filters' })).not.toBeInTheDocument();
    });

    it('hides active filters section when no filters', () => {
      render(
        <SourceFilterBar
          currentFilters={{}}
          onFilterChange={jest.fn()}
          availableTags={availableTags}
        />
      );

      expect(screen.queryByText('Active filters:')).not.toBeInTheDocument();
    });

    it('hides tags section when no available tags', () => {
      render(
        <SourceFilterBar currentFilters={{}} onFilterChange={jest.fn()} availableTags={[]} />
      );

      expect(screen.queryByText('Tags')).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('all interactive elements have accessible names', () => {
      render(
        <SourceFilterBar
          currentFilters={{ artifact_type: 'skill', tags: ['python'] }}
          onFilterChange={jest.fn()}
          availableTags={availableTags}
        />
      );

      // Filter controls
      expect(screen.getByLabelText('Filter by artifact type')).toBeInTheDocument();
      expect(screen.getByLabelText('Filter by trust level')).toBeInTheDocument();

      // Tag buttons
      expect(screen.getAllByLabelText(/tag filter: python/).length).toBeGreaterThan(0);

      // Remove buttons
      expect(
        screen.getByRole('button', { name: 'Remove artifact type filter: skill' })
      ).toBeInTheDocument();

      // Clear all
      expect(screen.getByRole('button', { name: 'Clear all filters' })).toBeInTheDocument();
    });

    it('filter labels are associated with controls', () => {
      render(
        <SourceFilterBar currentFilters={{}} onFilterChange={jest.fn()} availableTags={[]} />
      );

      const typeLabel = screen.getByText('Type');
      const trustLabel = screen.getByText('Trust');

      expect(typeLabel).toHaveAttribute('for', 'artifact-type-filter');
      expect(trustLabel).toHaveAttribute('for', 'trust-level-filter');
    });
  });
});
