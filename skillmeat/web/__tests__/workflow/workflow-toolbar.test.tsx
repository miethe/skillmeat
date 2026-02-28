/**
 * @jest-environment jsdom
 *
 * Tests for WorkflowToolbar component.
 *
 * Focus areas:
 *   - Search input renders with correct placeholder / initial value
 *   - Debounced search propagates to onFiltersChange
 *   - Clear button clears search and triggers filter update
 *   - Status filter options render and trigger updates
 *   - Sort options render and trigger updates
 *   - View toggle switches between grid and list
 *
 * Radix UI Select — jsdom polyfills:
 *   Radix Select needs hasPointerCapture, setPointerCapture, releasePointerCapture,
 *   and scrollIntoView in jsdom. We polyfill all four. We also open dropdowns with
 *   fireEvent.click (not userEvent.click) to avoid the pointer-capture throw path
 *   inside Radix's internal event handling.
 */

import { render, screen, within, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WorkflowToolbar } from '@/components/workflow/workflow-toolbar';
import type { WorkflowFilters } from '@/types/workflow';

// ---------------------------------------------------------------------------
// Polyfills — required for Radix UI Select in jsdom
// ---------------------------------------------------------------------------
Element.prototype.scrollIntoView = jest.fn();
if (!Element.prototype.hasPointerCapture) {
  Element.prototype.hasPointerCapture = () => false;
}
if (!Element.prototype.setPointerCapture) {
  (Element.prototype as unknown as { setPointerCapture: () => void }).setPointerCapture = jest.fn();
}
if (!Element.prototype.releasePointerCapture) {
  (Element.prototype as unknown as { releasePointerCapture: () => void }).releasePointerCapture = jest.fn();
}

// ---------------------------------------------------------------------------
// Mock useDebounce — sync (no delay) for predictable test assertions
// ---------------------------------------------------------------------------
jest.mock('@/hooks', () => ({
  useDebounce: (value: string, _delay: number) => value,
}));

// ---------------------------------------------------------------------------
// Default props factory
// ---------------------------------------------------------------------------

const DEFAULT_FILTERS: WorkflowFilters = {
  sortBy: 'updated_at',
  sortOrder: 'desc',
};

function renderToolbar(
  overrides: {
    filters?: WorkflowFilters;
    onFiltersChange?: jest.Mock;
    view?: 'grid' | 'list';
    onViewChange?: jest.Mock;
  } = {}
) {
  const onFiltersChange = overrides.onFiltersChange ?? jest.fn();
  const onViewChange = overrides.onViewChange ?? jest.fn();
  render(
    <WorkflowToolbar
      filters={overrides.filters ?? DEFAULT_FILTERS}
      onFiltersChange={onFiltersChange}
      view={overrides.view ?? 'grid'}
      onViewChange={onViewChange}
    />
  );
  return { onFiltersChange, onViewChange };
}

// ---------------------------------------------------------------------------
// Search input
// ---------------------------------------------------------------------------

describe('WorkflowToolbar — search input', () => {
  it('renders the search input', () => {
    renderToolbar();
    expect(screen.getByRole('searchbox', { name: /Search workflows/i })).toBeInTheDocument();
  });

  it('starts with the value from filters.search', () => {
    renderToolbar({ filters: { ...DEFAULT_FILTERS, search: 'hello' } });
    expect(screen.getByRole('searchbox', { name: /Search workflows/i })).toHaveValue('hello');
  });

  it('updates local value as the user types', async () => {
    const user = userEvent.setup();
    renderToolbar();
    const input = screen.getByRole('searchbox', { name: /Search workflows/i });
    await user.type(input, 'agent');
    expect(input).toHaveValue('agent');
  });

  it('calls onFiltersChange with the search term (debounce mocked to sync)', async () => {
    const user = userEvent.setup();
    const { onFiltersChange } = renderToolbar();
    const input = screen.getByRole('searchbox', { name: /Search workflows/i });
    await user.type(input, 'runner');
    expect(onFiltersChange).toHaveBeenCalledWith(
      expect.objectContaining({ search: 'runner' })
    );
  });

  it('shows the clear button when there is text in the search input', async () => {
    const user = userEvent.setup();
    renderToolbar();
    const input = screen.getByRole('searchbox', { name: /Search workflows/i });
    await user.type(input, 'x');
    expect(screen.getByRole('button', { name: /Clear search/i })).toBeInTheDocument();
  });

  it('does not show the clear button when search is empty', () => {
    renderToolbar();
    expect(screen.queryByRole('button', { name: /Clear search/i })).not.toBeInTheDocument();
  });

  it('clears search and calls onFiltersChange without search when clear is clicked', async () => {
    const user = userEvent.setup();
    const { onFiltersChange } = renderToolbar();
    const input = screen.getByRole('searchbox', { name: /Search workflows/i });
    await user.type(input, 'term');
    onFiltersChange.mockClear();

    await user.click(screen.getByRole('button', { name: /Clear search/i }));

    expect(input).toHaveValue('');
    expect(onFiltersChange).toHaveBeenCalledWith(
      expect.not.objectContaining({ search: expect.anything() })
    );
  });
});

// ---------------------------------------------------------------------------
// Status filter
// ---------------------------------------------------------------------------

describe('WorkflowToolbar — status filter', () => {
  it('renders the status filter trigger', () => {
    renderToolbar();
    expect(screen.getByRole('combobox', { name: /Filter by status/i })).toBeInTheDocument();
  });

  it('shows all status options when the select is opened', async () => {
    renderToolbar();
    // Use fireEvent to avoid Radix's internal pointer-capture throw
    fireEvent.click(screen.getByRole('combobox', { name: /Filter by status/i }));

    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'All statuses' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Draft' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Active' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Archived' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Deprecated' })).toBeInTheDocument();
    });
  });

  it('calls onFiltersChange with the selected status', async () => {
    const { onFiltersChange } = renderToolbar();
    fireEvent.click(screen.getByRole('combobox', { name: /Filter by status/i }));

    await waitFor(() => screen.getByRole('option', { name: 'Draft' }));
    fireEvent.click(screen.getByRole('option', { name: 'Draft' }));

    expect(onFiltersChange).toHaveBeenCalledWith(
      expect.objectContaining({ status: 'draft' })
    );
  });

  it('removes status from filters when "All statuses" is selected', async () => {
    const { onFiltersChange } = renderToolbar({
      filters: { ...DEFAULT_FILTERS, status: 'active' },
    });
    fireEvent.click(screen.getByRole('combobox', { name: /Filter by status/i }));

    await waitFor(() => screen.getByRole('option', { name: 'All statuses' }));
    fireEvent.click(screen.getByRole('option', { name: 'All statuses' }));

    const calledWith = onFiltersChange.mock.calls.at(-1)?.[0] as WorkflowFilters;
    expect(calledWith).not.toHaveProperty('status');
  });
});

// ---------------------------------------------------------------------------
// Sort
// ---------------------------------------------------------------------------

describe('WorkflowToolbar — sort options', () => {
  it('renders the sort trigger', () => {
    renderToolbar();
    expect(screen.getByRole('combobox', { name: /Sort workflows/i })).toBeInTheDocument();
  });

  it('shows all sort options when opened', async () => {
    renderToolbar();
    fireEvent.click(screen.getByRole('combobox', { name: /Sort workflows/i }));

    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'Updated (newest)' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Updated (oldest)' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Name (A-Z)' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Name (Z-A)' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Created (newest)' })).toBeInTheDocument();
    });
  });

  it('calls onFiltersChange with name_asc sort when "Name (A-Z)" is chosen', async () => {
    const { onFiltersChange } = renderToolbar();
    fireEvent.click(screen.getByRole('combobox', { name: /Sort workflows/i }));

    await waitFor(() => screen.getByRole('option', { name: 'Name (A-Z)' }));
    fireEvent.click(screen.getByRole('option', { name: 'Name (A-Z)' }));

    expect(onFiltersChange).toHaveBeenCalledWith(
      expect.objectContaining({ sortBy: 'name', sortOrder: 'asc' })
    );
  });

  it('calls onFiltersChange with created_at desc when "Created (newest)" is chosen', async () => {
    const { onFiltersChange } = renderToolbar();
    fireEvent.click(screen.getByRole('combobox', { name: /Sort workflows/i }));

    await waitFor(() => screen.getByRole('option', { name: 'Created (newest)' }));
    fireEvent.click(screen.getByRole('option', { name: 'Created (newest)' }));

    expect(onFiltersChange).toHaveBeenCalledWith(
      expect.objectContaining({ sortBy: 'created_at', sortOrder: 'desc' })
    );
  });
});

// ---------------------------------------------------------------------------
// View toggle
// ---------------------------------------------------------------------------

describe('WorkflowToolbar — view toggle', () => {
  it('renders grid and list toggle buttons inside a group', () => {
    renderToolbar();
    const group = screen.getByRole('group', { name: /View layout/i });
    expect(group).toBeInTheDocument();
    expect(within(group).getByRole('button', { name: /Grid view/i })).toBeInTheDocument();
    expect(within(group).getByRole('button', { name: /List view/i })).toBeInTheDocument();
  });

  it('Grid view button has aria-pressed="true" when view is grid', () => {
    renderToolbar({ view: 'grid' });
    expect(screen.getByRole('button', { name: /Grid view/i })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: /List view/i })).toHaveAttribute('aria-pressed', 'false');
  });

  it('List view button has aria-pressed="true" when view is list', () => {
    renderToolbar({ view: 'list' });
    expect(screen.getByRole('button', { name: /List view/i })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: /Grid view/i })).toHaveAttribute('aria-pressed', 'false');
  });

  it('calls onViewChange("list") when List view button is clicked', async () => {
    const user = userEvent.setup();
    const { onViewChange } = renderToolbar({ view: 'grid' });
    await user.click(screen.getByRole('button', { name: /List view/i }));
    expect(onViewChange).toHaveBeenCalledWith('list');
  });

  it('calls onViewChange("grid") when Grid view button is clicked', async () => {
    const user = userEvent.setup();
    const { onViewChange } = renderToolbar({ view: 'list' });
    await user.click(screen.getByRole('button', { name: /Grid view/i }));
    expect(onViewChange).toHaveBeenCalledWith('grid');
  });
});

// ---------------------------------------------------------------------------
// Accessible landmark
// ---------------------------------------------------------------------------

describe('WorkflowToolbar — accessibility', () => {
  it('renders a search landmark region', () => {
    renderToolbar();
    expect(screen.getByRole('search', { name: /Filter and sort workflows/i })).toBeInTheDocument();
  });
});
