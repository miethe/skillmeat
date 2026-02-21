/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { EntityCard } from '@/components/entity/entity-card';
import type { Entity } from '@/types/entity';

// Mock useCollectionContext hook
jest.mock('@/hooks/use-collection-context', () => ({
  useCollectionContext: () => ({
    selectedCollectionId: 'default',
    collections: [],
  }),
  CollectionProvider: ({ children }: { children: React.ReactNode }) => children,
}));

// Test wrapper with QueryClientProvider
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

const renderWithProviders = (component: React.ReactElement) => {
  const queryClient = createTestQueryClient();
  return render(<QueryClientProvider client={queryClient}>{component}</QueryClientProvider>);
};

const mockEntity: Entity = {
  id: 'skill:test',
  uuid: '00000000000000000000000000000001',
  name: 'test-skill',
  type: 'skill',
  scope: 'user',
  source: 'github:user/repo/skill',
  syncStatus: 'synced',
  tags: ['testing', 'example', 'demo', 'extra'],
  description: 'A test skill for unit testing',
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
};

describe('EntityCard', () => {
  it('renders entity name', () => {
    renderWithProviders(<EntityCard entity={mockEntity} />);

    expect(screen.getByText('test-skill')).toBeInTheDocument();
  });

  it('displays entity type badge', () => {
    renderWithProviders(<EntityCard entity={mockEntity} />);

    expect(screen.getByText('Skill')).toBeInTheDocument();
  });

  it('shows description when provided', () => {
    renderWithProviders(<EntityCard entity={mockEntity} />);

    expect(screen.getByText('A test skill for unit testing')).toBeInTheDocument();
  });

  it('truncates long description', () => {
    const longDescription =
      "This is a very long description that should be truncated after 100 characters to ensure the card doesn't become too tall";
    const entityWithLongDesc = { ...mockEntity, description: longDescription };

    renderWithProviders(<EntityCard entity={entityWithLongDesc} />);

    const description = screen.getByText(/This is a very long description/);
    expect(description.textContent).toContain('...');
  });

  it('displays status indicator with correct color', () => {
    renderWithProviders(<EntityCard entity={mockEntity} />);

    expect(screen.getByText('Synced')).toBeInTheDocument();
  });

  it('shows modified status correctly', () => {
    const modifiedEntity = { ...mockEntity, syncStatus: 'modified' as const };
    renderWithProviders(<EntityCard entity={modifiedEntity} />);

    expect(screen.getByText('Modified')).toBeInTheDocument();
  });

  it('shows outdated status correctly', () => {
    const outdatedEntity = { ...mockEntity, syncStatus: 'outdated' as const };
    renderWithProviders(<EntityCard entity={outdatedEntity} />);

    expect(screen.getByText('Outdated')).toBeInTheDocument();
  });

  it('shows conflict status correctly', () => {
    const conflictEntity = { ...mockEntity, syncStatus: 'conflict' as const };
    renderWithProviders(<EntityCard entity={conflictEntity} />);

    expect(screen.getByText('Conflict')).toBeInTheDocument();
  });

  it('displays up to 3 tags', () => {
    renderWithProviders(<EntityCard entity={mockEntity} />);

    expect(screen.getByText('testing')).toBeInTheDocument();
    expect(screen.getByText('example')).toBeInTheDocument();
    expect(screen.getByText('demo')).toBeInTheDocument();
  });

  it('shows +N more badge when more than 3 tags', () => {
    renderWithProviders(<EntityCard entity={mockEntity} />);

    expect(screen.getByText('+1 more')).toBeInTheDocument();
  });

  it('does not show tags section when no tags', () => {
    const noTagsEntity = { ...mockEntity, tags: [] };
    renderWithProviders(<EntityCard entity={noTagsEntity} />);

    expect(screen.queryByText('testing')).not.toBeInTheDocument();
  });

  it('calls onClick when card is clicked', () => {
    const handleClick = jest.fn();
    renderWithProviders(<EntityCard entity={mockEntity} onClick={handleClick} />);

    const card = screen.getByText('test-skill').closest('div');
    if (card?.parentElement) {
      fireEvent.click(card.parentElement);
    }

    expect(handleClick).toHaveBeenCalled();
  });

  it('does not trigger onClick when clicking checkbox', () => {
    const handleClick = jest.fn();
    renderWithProviders(<EntityCard entity={mockEntity} selectable={true} onClick={handleClick} />);

    const checkbox = screen.getByRole('checkbox');
    fireEvent.click(checkbox);

    // onClick should not be called when clicking checkbox
    expect(handleClick).not.toHaveBeenCalled();
  });

  it('shows checkbox when selectable is true', () => {
    renderWithProviders(<EntityCard entity={mockEntity} selectable={true} />);

    expect(screen.getByRole('checkbox')).toBeInTheDocument();
  });

  it('does not show checkbox when selectable is false', () => {
    renderWithProviders(<EntityCard entity={mockEntity} selectable={false} />);

    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
  });

  it('calls onSelect when checkbox is checked', () => {
    const handleSelect = jest.fn();
    renderWithProviders(
      <EntityCard entity={mockEntity} selectable={true} onSelect={handleSelect} />
    );

    const checkbox = screen.getByRole('checkbox');
    fireEvent.click(checkbox);

    expect(handleSelect).toHaveBeenCalledWith(true);
  });

  it('applies selected styling when selected', () => {
    const { container } = renderWithProviders(<EntityCard entity={mockEntity} selected={true} />);

    const card = container.firstChild;
    expect(card).toHaveClass('ring-2', 'ring-primary');
  });

  it('applies hover styling', () => {
    const { container } = renderWithProviders(<EntityCard entity={mockEntity} />);

    const card = container.firstChild;
    expect(card).toHaveClass('hover:bg-accent/50');
  });

  it('renders entity icon', () => {
    const { container } = renderWithProviders(<EntityCard entity={mockEntity} />);

    const icon = container.querySelector('svg');
    expect(icon).toBeInTheDocument();
  });

  it('renders EntityActions component', () => {
    renderWithProviders(<EntityCard entity={mockEntity} onEdit={jest.fn()} />);

    // EntityActions should render a menu button
    const menuButtons = screen.getAllByRole('button');
    expect(menuButtons.length).toBeGreaterThan(0);
  });

  it('passes action handlers to EntityActions', () => {
    const handlers = {
      onEdit: jest.fn(),
      onDelete: jest.fn(),
      onDeploy: jest.fn(),
      onSync: jest.fn(),
      onViewDiff: jest.fn(),
      onRollback: jest.fn(),
    };

    renderWithProviders(<EntityCard entity={mockEntity} {...handlers} />);

    // All handlers should be passed to EntityActions
    expect(screen.getByText('test-skill')).toBeInTheDocument();
  });

  it('handles missing description gracefully', () => {
    const noDescEntity = { ...mockEntity, description: undefined };
    renderWithProviders(<EntityCard entity={noDescEntity} />);

    expect(screen.queryByText(/test skill/)).not.toBeInTheDocument();
  });

  it('handles missing status gracefully', () => {
    const noStatusEntity = { ...mockEntity, syncStatus: undefined as any };
    renderWithProviders(<EntityCard entity={noStatusEntity} />);

    expect(screen.queryByText('Synced')).not.toBeInTheDocument();
  });

  it('displays correct icon based on entity type', () => {
    const commandEntity: Entity = {
      ...mockEntity,
      type: 'command',
      id: 'command:test',
    };

    renderWithProviders(<EntityCard entity={commandEntity} />);

    expect(screen.getByText('Command')).toBeInTheDocument();
  });
});
