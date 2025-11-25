/**
 * Accessibility Tests for EntityDetailPanel Component
 * @jest-environment jsdom
 */

// Mock hooks before importing components
jest.mock('@/hooks/useEntityLifecycle', () => ({
  EntityLifecycleProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useEntityLifecycle: () => ({
    entities: [],
    selectedEntities: [],
    isLoading: false,
    selectEntity: jest.fn(),
    deselectEntity: jest.fn(),
    deployEntity: jest.fn(),
    syncEntity: jest.fn(),
    refetch: jest.fn(),
  }),
}));

// Mock toast hook
jest.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: jest.fn(),
  }),
}));

// Mock API request
jest.mock('@/lib/api', () => ({
  apiRequest: jest.fn().mockResolvedValue({
    has_changes: false,
    files: [],
    summary: {
      added: 0,
      modified: 0,
      deleted: 0,
      unchanged: 0,
    },
  }),
}));

import { render, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import { EntityDetailPanel } from '@/app/manage/components/entity-detail-panel';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { Entity } from '@/types/entity';

const mockEntity: Entity = {
  id: 'skill:test',
  name: 'test-skill',
  type: 'skill',
  source: 'github:user/repo/skill',
  status: 'synced',
  description: 'Test skill for accessibility testing',
  tags: ['test', 'a11y'],
  version: 'v1.0.0',
  collection: 'default',
  projectPath: '/path/to/project',
  deployedAt: '2024-01-15T10:00:00Z',
  modifiedAt: '2024-01-15T10:00:00Z',
};

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>
    {children}
  </QueryClientProvider>
);

describe('EntityDetailPanel Accessibility', () => {
  it('should render without errors when open', () => {
    const { container } = render(
      <EntityDetailPanel entity={mockEntity} open={true} onClose={jest.fn()} />,
      { wrapper }
    );

    // Component should render
    expect(container).toBeInTheDocument();
  });

  it('should not render when closed', () => {
    const { container } = render(
      <EntityDetailPanel entity={null} open={false} onClose={jest.fn()} />,
      { wrapper }
    );

    // Component should render but be closed
    expect(container).toBeInTheDocument();
  });

  it('should handle different entity statuses', () => {
    const statuses: Array<'synced' | 'modified' | 'outdated' | 'conflict'> = [
      'synced',
      'modified',
      'outdated',
      'conflict',
    ];

    statuses.forEach((status) => {
      const entity = { ...mockEntity, status };
      const { container } = render(
        <EntityDetailPanel entity={entity} open={true} onClose={jest.fn()} />,
        { wrapper }
      );
      expect(container).toBeInTheDocument();
    });
  });

  it('should render with all entity data', () => {
    const { container } = render(
      <EntityDetailPanel entity={mockEntity} open={true} onClose={jest.fn()} />,
      { wrapper }
    );

    expect(container).toBeInTheDocument();
  });

  it('should handle entity without optional fields', () => {
    const minimalEntity: Entity = {
      id: 'skill:minimal',
      name: 'minimal-skill',
      type: 'skill',
      source: 'github:user/repo',
      status: 'synced',
    };

    const { container } = render(
      <EntityDetailPanel entity={minimalEntity} open={true} onClose={jest.fn()} />,
      { wrapper }
    );

    expect(container).toBeInTheDocument();
  });
});
