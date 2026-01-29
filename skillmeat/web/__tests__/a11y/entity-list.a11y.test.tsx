/**
 * Accessibility Tests for EntityList Component
 * @jest-environment jsdom
 */
import { render } from '@testing-library/react';
import { axe } from 'jest-axe';
import { EntityList } from '@/components/entity/entity-list';
import { EntityLifecycleProvider } from '@/hooks';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { Entity } from '@/types/entity';

const mockEntities: Entity[] = [
  {
    id: 'skill:1',
    name: 'skill-one',
    type: 'skill',
    scope: 'user',
    source: 'github:user/repo/skill1',
    syncStatus: 'synced',
    description: 'First test skill',
    tags: ['test'],
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
  {
    id: 'skill:2',
    name: 'skill-two',
    type: 'skill',
    scope: 'user',
    source: 'github:user/repo/skill2',
    syncStatus: 'modified',
    description: 'Second test skill',
    tags: ['test', 'example'],
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
];

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

// Wrapper to provide context
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>
    <EntityLifecycleProvider>{children}</EntityLifecycleProvider>
  </QueryClientProvider>
);

describe('EntityList Accessibility', () => {
  it('should have no violations in grid view', async () => {
    const { container } = render(<EntityList viewMode="grid" entities={mockEntities} />, {
      wrapper,
    });
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have no violations in list view', async () => {
    const { container } = render(<EntityList viewMode="list" entities={mockEntities} />, {
      wrapper,
    });
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have no violations with empty state', async () => {
    const { container } = render(<EntityList viewMode="grid" entities={[]} />, { wrapper });
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have no violations when selectable', async () => {
    const { container } = render(
      <EntityList viewMode="grid" entities={mockEntities} selectable={true} />,
      { wrapper }
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have proper heading hierarchy in list view', async () => {
    const { container } = render(<EntityList viewMode="list" entities={mockEntities} />, {
      wrapper,
    });

    // Verify heading exists and is accessible
    const results = await axe(container, {
      rules: {
        'heading-order': { enabled: true },
      },
    });
    expect(results).toHaveNoViolations();
  });

  it('should have accessible table structure in list view', async () => {
    const { container } = render(<EntityList viewMode="list" entities={mockEntities} />, {
      wrapper,
    });

    // Verify table accessibility
    const results = await axe(container, {
      rules: {
        'table-fake-caption': { enabled: true },
      },
    });
    expect(results).toHaveNoViolations();
  });

  it('should have no violations with all action handlers', async () => {
    const { container } = render(
      <EntityList
        viewMode="grid"
        entities={mockEntities}
        onEdit={jest.fn()}
        onDelete={jest.fn()}
        onDeploy={jest.fn()}
        onSync={jest.fn()}
        onViewDiff={jest.fn()}
        onRollback={jest.fn()}
      />,
      { wrapper }
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
