/**
 * @jest-environment jsdom
 */
import { render, screen, within, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ManagePageFilters, type ManageStatusFilter } from '@/components/manage/manage-page-filters';
import type { ArtifactType } from '@/types/artifact';

// Polyfill scrollIntoView for Radix UI components
Element.prototype.scrollIntoView = jest.fn();

// Default props factory
function createDefaultProps() {
  return {
    search: '',
    status: 'all' as ManageStatusFilter,
    type: 'all' as ArtifactType | 'all',
    project: null as string | null,
    tags: [] as string[],
    onSearchChange: jest.fn(),
    onStatusChange: jest.fn(),
    onTypeChange: jest.fn(),
    onProjectChange: jest.fn(),
    onTagsChange: jest.fn(),
    onClearAll: jest.fn(),
    availableProjects: ['project-1', 'project-2', 'project-3'],
    availableTags: ['tag-1', 'tag-2', 'tag-3', 'frontend', 'backend'],
  };
}

describe('ManagePageFilters', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  describe('renders all filter elements', () => {
    it('renders search input', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} />);

      expect(screen.getByLabelText('Search artifacts by name or description')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Search artifacts...')).toBeInTheDocument();
    });

    it('renders project filter trigger', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} />);

      expect(screen.getByLabelText('Filter by project')).toBeInTheDocument();
    });

    it('renders status filter trigger', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} />);

      expect(screen.getByLabelText('Filter by status')).toBeInTheDocument();
    });

    it('renders type filter trigger', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} />);

      expect(screen.getByLabelText('Filter by artifact type')).toBeInTheDocument();
    });

    it('renders tags filter button', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} />);

      expect(screen.getByLabelText('Filter by tags')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /tags/i })).toBeInTheDocument();
    });

    it('has search role on container', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} />);

      expect(screen.getByRole('search')).toBeInTheDocument();
    });
  });

  describe('search input with debounce', () => {
    it('updates input value immediately on change', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} />);

      const searchInput = screen.getByLabelText('Search artifacts by name or description');
      await user.type(searchInput, 'test');

      expect(searchInput).toHaveValue('test');
    });

    it('calls onSearchChange after debounce delay', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} />);

      const searchInput = screen.getByLabelText('Search artifacts by name or description');
      await user.type(searchInput, 'test');

      // Should not be called immediately
      expect(props.onSearchChange).not.toHaveBeenCalled();

      // Advance past debounce delay (300ms)
      act(() => {
        jest.advanceTimersByTime(300);
      });

      expect(props.onSearchChange).toHaveBeenCalledWith('test');
    });

    it('clears search when clear button is clicked', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} search="existing" />);

      const clearButton = screen.getByLabelText('Clear search');
      await user.click(clearButton);

      expect(props.onSearchChange).toHaveBeenCalledWith('');
    });

    it('shows clear button only when search has value', () => {
      const props = createDefaultProps();
      const { rerender } = render(<ManagePageFilters {...props} />);

      expect(screen.queryByLabelText('Clear search')).not.toBeInTheDocument();

      rerender(<ManagePageFilters {...props} search="test" />);

      expect(screen.getByLabelText('Clear search')).toBeInTheDocument();
    });

    it('syncs internal state when search prop changes externally', () => {
      const props = createDefaultProps();
      const { rerender } = render(<ManagePageFilters {...props} />);

      const searchInput = screen.getByLabelText('Search artifacts by name or description');
      expect(searchInput).toHaveValue('');

      rerender(<ManagePageFilters {...props} search="external change" />);

      expect(searchInput).toHaveValue('external change');
    });
  });

  describe('status filter displays', () => {
    it('displays All Status when status is all', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} status="all" />);

      expect(screen.getByText('All Status')).toBeInTheDocument();
    });

    it('displays Has Drift when status is has-drift', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} status="has-drift" />);

      expect(screen.getByText('Has Drift')).toBeInTheDocument();
    });

    it('displays Needs Update when status is needs-update', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} status="needs-update" />);

      expect(screen.getByText('Needs Update')).toBeInTheDocument();
    });

    it('displays Deployed when status is deployed', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} status="deployed" />);

      expect(screen.getByText('Deployed')).toBeInTheDocument();
    });

    it('displays Error when status is error', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} status="error" />);

      expect(screen.getByText('Error')).toBeInTheDocument();
    });
  });

  describe('type filter displays', () => {
    it('displays All Types when type is all', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} type="all" />);

      expect(screen.getByText('All Types')).toBeInTheDocument();
    });

    it('displays Skills when type is skill', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} type="skill" />);

      expect(screen.getByText('Skills')).toBeInTheDocument();
    });

    it('displays Commands when type is command', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} type="command" />);

      expect(screen.getByText('Commands')).toBeInTheDocument();
    });
  });

  describe('project filter displays', () => {
    it('displays All Projects when project is null', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} project={null} />);

      expect(screen.getByText('All Projects')).toBeInTheDocument();
    });

    it('displays project name when project is selected', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} project="project-2" />);

      expect(screen.getByText('project-2')).toBeInTheDocument();
    });
  });

  describe('tags popover', () => {
    it('opens popover when button is clicked', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} />);

      const tagsButton = screen.getByRole('button', { name: /tags/i });
      await user.click(tagsButton);

      expect(screen.getByText('Filter by tags')).toBeInTheDocument();
      expect(screen.getByLabelText('Search available tags')).toBeInTheDocument();
    });

    it('displays available tags in popover', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} />);

      const tagsButton = screen.getByRole('button', { name: /tags/i });
      await user.click(tagsButton);

      expect(screen.getByRole('option', { name: /tag-1/ })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /tag-2/ })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /frontend/ })).toBeInTheDocument();
    });

    it('selects tag when clicked', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} />);

      const tagsButton = screen.getByRole('button', { name: /tags/i });
      await user.click(tagsButton);

      const tag1Option = screen.getByRole('option', { name: /tag-1/ });
      await user.click(tag1Option);

      expect(props.onTagsChange).toHaveBeenCalledWith(['tag-1']);
    });

    it('deselects tag when already selected', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} tags={['tag-1']} />);

      const tagsButton = screen.getByRole('button', { name: /tags.*1 selected/i });
      await user.click(tagsButton);

      const tag1Option = screen.getByRole('option', { name: /tag-1/ });
      await user.click(tag1Option);

      expect(props.onTagsChange).toHaveBeenCalledWith([]);
    });

    it('shows badge count when tags are selected', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} tags={['tag-1', 'tag-2']} />);

      const tagsButton = screen.getByLabelText(/tags.*2 selected/i);
      expect(within(tagsButton).getByText('2')).toBeInTheDocument();
    });

    it('filters tags by search', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} />);

      const tagsButton = screen.getByRole('button', { name: /tags/i });
      await user.click(tagsButton);

      const tagSearch = screen.getByLabelText('Search available tags');
      await user.type(tagSearch, 'front');

      expect(screen.getByRole('option', { name: /frontend/ })).toBeInTheDocument();
      expect(screen.queryByRole('option', { name: /tag-1/ })).not.toBeInTheDocument();
      expect(screen.queryByRole('option', { name: /backend/ })).not.toBeInTheDocument();
    });

    it('shows "No tags found" when search has no matches', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} />);

      const tagsButton = screen.getByRole('button', { name: /tags/i });
      await user.click(tagsButton);

      const tagSearch = screen.getByLabelText('Search available tags');
      await user.type(tagSearch, 'nonexistent');

      expect(screen.getByText('No tags found')).toBeInTheDocument();
    });

    it('clears all tags when Clear all button is clicked', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} tags={['tag-1', 'tag-2']} />);

      const tagsButton = screen.getByRole('button', { name: /tags.*2 selected/i });
      await user.click(tagsButton);

      const clearAllButton = screen.getByRole('button', { name: 'Clear all' });
      await user.click(clearAllButton);

      expect(props.onTagsChange).toHaveBeenCalledWith([]);
    });

    it('responds to keyboard navigation on tag option', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} />);

      const tagsButton = screen.getByRole('button', { name: /tags/i });
      await user.click(tagsButton);

      const tag1Option = screen.getByRole('option', { name: /tag-1/ });
      tag1Option.focus();
      await user.keyboard('{Enter}');

      expect(props.onTagsChange).toHaveBeenCalledWith(['tag-1']);
    });
  });

  describe('active filter chips', () => {
    it('does not show chips when no filters are active', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} />);

      expect(screen.queryByText('Active filters:')).not.toBeInTheDocument();
    });

    it('shows project chip when project filter is active', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} project="project-1" />);

      expect(screen.getByText('Active filters:')).toBeInTheDocument();
      expect(screen.getByText('Project: project-1')).toBeInTheDocument();
    });

    it('shows status chip when status filter is active', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} status="has-drift" />);

      expect(screen.getByText('Status: Has Drift')).toBeInTheDocument();
    });

    it('shows type chip when type filter is active', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} type="skill" />);

      expect(screen.getByText('Type: Skills')).toBeInTheDocument();
    });

    it('shows tag chips for each selected tag', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} tags={['tag-1', 'tag-2']} />);

      expect(screen.getByText('tag-1')).toBeInTheDocument();
      expect(screen.getByText('tag-2')).toBeInTheDocument();
    });

    it('removes project filter when chip X is clicked', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} project="project-1" />);

      const removeButton = screen.getByLabelText('Remove project filter: project-1');
      await user.click(removeButton);

      expect(props.onProjectChange).toHaveBeenCalledWith(null);
    });

    it('removes status filter when chip X is clicked', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} status="error" />);

      const removeButton = screen.getByLabelText('Remove status filter: Error');
      await user.click(removeButton);

      expect(props.onStatusChange).toHaveBeenCalledWith('all');
    });

    it('removes type filter when chip X is clicked', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} type="agent" />);

      const removeButton = screen.getByLabelText('Remove type filter: Agents');
      await user.click(removeButton);

      expect(props.onTypeChange).toHaveBeenCalledWith('all');
    });

    it('removes individual tag when chip X is clicked', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} tags={['tag-1', 'tag-2']} />);

      const removeButton = screen.getByLabelText('Remove tag filter: tag-1');
      await user.click(removeButton);

      expect(props.onTagsChange).toHaveBeenCalledWith(['tag-2']);
    });
  });

  describe('Clear All button', () => {
    it('does not show when no filters are active', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} />);

      expect(screen.queryByRole('button', { name: 'Clear All' })).not.toBeInTheDocument();
    });

    it('shows when search has value', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} search="test" />);

      expect(screen.getByRole('button', { name: 'Clear All' })).toBeInTheDocument();
    });

    it('shows when any filter is active', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} status="deployed" />);

      expect(screen.getByRole('button', { name: 'Clear All' })).toBeInTheDocument();
    });

    it('calls onClearAll when clicked', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} search="test" status="error" type="skill" />);

      const clearAllButton = screen.getByRole('button', { name: 'Clear All' });
      await user.click(clearAllButton);

      expect(props.onClearAll).toHaveBeenCalledTimes(1);
    });
  });

  describe('accessibility', () => {
    it('has aria-label on search container', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} />);

      expect(screen.getByRole('search')).toHaveAttribute('aria-label', 'Filter artifacts');
    });

    it('has aria-live on active filters section', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} status="error" />);

      const activeFilters = screen.getByRole('status');
      expect(activeFilters).toHaveAttribute('aria-live', 'polite');
    });

    it('tags button has aria-expanded state', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} />);

      const tagsButton = screen.getByRole('button', { name: /tags/i });
      expect(tagsButton).toHaveAttribute('aria-expanded', 'false');
    });

    it('tags button has aria-haspopup', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} />);

      const tagsButton = screen.getByRole('button', { name: /tags/i });
      expect(tagsButton).toHaveAttribute('aria-haspopup', 'listbox');
    });

    it('tag listbox has aria-multiselectable', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} />);

      const tagsButton = screen.getByRole('button', { name: /tags/i });
      await user.click(tagsButton);

      const listbox = screen.getByRole('listbox');
      expect(listbox).toHaveAttribute('aria-multiselectable', 'true');
    });

    it('icons have aria-hidden', () => {
      const props = createDefaultProps();
      const { container } = render(<ManagePageFilters {...props} />);

      const hiddenIcons = container.querySelectorAll('[aria-hidden="true"]');
      expect(hiddenIcons.length).toBeGreaterThan(0);
    });
  });

  describe('edge cases', () => {
    it('handles empty availableProjects array', () => {
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} availableProjects={[]} />);

      expect(screen.getByLabelText('Filter by project')).toBeInTheDocument();
    });

    it('handles empty availableTags array', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const props = createDefaultProps();
      render(<ManagePageFilters {...props} availableTags={[]} />);

      const tagsButton = screen.getByRole('button', { name: /tags/i });
      await user.click(tagsButton);

      expect(screen.getByText('No tags found')).toBeInTheDocument();
    });

    it('handles all filters active simultaneously', () => {
      const props = createDefaultProps();
      render(
        <ManagePageFilters
          {...props}
          search="test"
          status="error"
          type="skill"
          project="project-1"
          tags={['tag-1', 'tag-2']}
        />
      );

      expect(screen.getByText('Active filters:')).toBeInTheDocument();
      expect(screen.getByText('Project: project-1')).toBeInTheDocument();
      expect(screen.getByText('Status: Error')).toBeInTheDocument();
      expect(screen.getByText('Type: Skills')).toBeInTheDocument();
      expect(screen.getByText('tag-1')).toBeInTheDocument();
      expect(screen.getByText('tag-2')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Clear All' })).toBeInTheDocument();
    });

    it('cleans up debounce timer on unmount', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const props = createDefaultProps();
      const { unmount } = render(<ManagePageFilters {...props} />);

      const searchInput = screen.getByLabelText('Search artifacts by name or description');
      await user.type(searchInput, 'test');

      // Unmount before debounce completes
      unmount();

      // Advance timers - should not throw
      act(() => {
        jest.advanceTimersByTime(300);
      });

      // onSearchChange should not have been called after unmount
      expect(props.onSearchChange).not.toHaveBeenCalled();
    });
  });
});
