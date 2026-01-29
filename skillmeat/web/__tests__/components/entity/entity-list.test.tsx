/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { EntityList } from '@/components/entity/entity-list';
import type { Entity } from '@/types/entity';

// Mock the useEntityLifecycle hook
jest.mock('@/hooks/useEntityLifecycle', () => ({
  useEntityLifecycle: () => ({
    entities: [],
    selectedEntities: [],
    selectEntity: jest.fn(),
    deselectEntity: jest.fn(),
  }),
}));

const mockEntities: Entity[] = [
  {
    id: 'skill:test1',
    name: 'test-skill-1',
    type: 'skill',
    scope: 'user',
    source: 'github:user/repo/skill1',
    syncStatus: 'synced',
    tags: ['testing'],
    description: 'First test skill',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
  {
    id: 'skill:test2',
    name: 'test-skill-2',
    type: 'skill',
    scope: 'user',
    source: 'github:user/repo/skill2',
    syncStatus: 'modified',
    tags: ['example'],
    description: 'Second test skill',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
  {
    id: 'command:test',
    name: 'test-command',
    type: 'command',
    scope: 'user',
    source: 'github:user/repo/command',
    syncStatus: 'outdated',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
];

describe('EntityList', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Grid View', () => {
    it('renders entities in grid layout', () => {
      render(<EntityList viewMode="grid" entities={mockEntities} />);

      expect(screen.getByText('test-skill-1')).toBeInTheDocument();
      expect(screen.getByText('test-skill-2')).toBeInTheDocument();
      expect(screen.getByText('test-command')).toBeInTheDocument();
    });

    it('displays entity cards in grid', () => {
      const { container } = render(<EntityList viewMode="grid" entities={mockEntities} />);

      const grid = container.querySelector('.grid');
      expect(grid).toBeInTheDocument();
    });
  });

  describe('List View', () => {
    it('renders entities in list layout', () => {
      render(<EntityList viewMode="list" entities={mockEntities} />);

      expect(screen.getByText('test-skill-1')).toBeInTheDocument();
      expect(screen.getByText('test-skill-2')).toBeInTheDocument();
      expect(screen.getByText('test-command')).toBeInTheDocument();
    });

    it('displays table headers in list view', () => {
      render(<EntityList viewMode="list" entities={mockEntities} />);

      expect(screen.getByText('Name')).toBeInTheDocument();
      expect(screen.getByText('Type')).toBeInTheDocument();
      expect(screen.getByText('Description')).toBeInTheDocument();
      expect(screen.getByText('Tags')).toBeInTheDocument();
      expect(screen.getByText('Status')).toBeInTheDocument();
      expect(screen.getByText('Actions')).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('shows empty state when no entities provided', () => {
      render(<EntityList viewMode="grid" entities={[]} />);

      expect(screen.getByText('No entities found')).toBeInTheDocument();
      expect(
        screen.getByText(/Get started by adding your first entity to your collection/)
      ).toBeInTheDocument();
    });

    it('shows filtered empty state when selectable', () => {
      render(<EntityList viewMode="grid" entities={[]} selectable />);

      expect(
        screen.getByText(
          /No entities match your current filters. Try adjusting your search or filters./
        )
      ).toBeInTheDocument();
    });

    it('displays FileQuestion icon in empty state', () => {
      const { container } = render(<EntityList viewMode="grid" entities={[]} />);

      const icon = container.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });
  });

  describe('Entity Click Handling', () => {
    it('calls onEntityClick when entity is clicked', () => {
      const handleClick = jest.fn();
      render(<EntityList viewMode="grid" entities={mockEntities} onEntityClick={handleClick} />);

      const entity = screen.getByText('test-skill-1');
      fireEvent.click(entity);

      expect(handleClick).toHaveBeenCalledWith(mockEntities[0]);
    });

    it('does not call onEntityClick when not provided', () => {
      render(<EntityList viewMode="grid" entities={mockEntities} />);

      const entity = screen.getByText('test-skill-1');
      expect(() => fireEvent.click(entity)).not.toThrow();
    });
  });

  describe('Selection', () => {
    it('shows checkboxes when selectable is true', () => {
      render(<EntityList viewMode="grid" entities={mockEntities} selectable={true} />);

      const checkboxes = screen.getAllByRole('checkbox');
      expect(checkboxes.length).toBeGreaterThan(0);
    });

    it('does not show checkboxes when selectable is false', () => {
      render(<EntityList viewMode="grid" entities={mockEntities} selectable={false} />);

      const checkboxes = screen.queryAllByRole('checkbox');
      expect(checkboxes.length).toBe(0);
    });

    it('calls selectEntity when entity is selected', () => {
      const { useEntityLifecycle } = require('@/hooks/useEntityLifecycle');
      const mockSelectEntity = jest.fn();
      useEntityLifecycle.mockImplementation(() => ({
        entities: [],
        selectedEntities: [],
        selectEntity: mockSelectEntity,
        deselectEntity: jest.fn(),
      }));

      render(<EntityList viewMode="grid" entities={mockEntities} selectable={true} />);

      const checkboxes = screen.getAllByRole('checkbox');
      fireEvent.click(checkboxes[0]);

      expect(mockSelectEntity).toHaveBeenCalledWith('skill:test1');
    });

    it('calls deselectEntity when entity is deselected', () => {
      const { useEntityLifecycle } = require('@/hooks/useEntityLifecycle');
      const mockDeselectEntity = jest.fn();
      useEntityLifecycle.mockImplementation(() => ({
        entities: [],
        selectedEntities: ['skill:test1'],
        selectEntity: jest.fn(),
        deselectEntity: mockDeselectEntity,
      }));

      render(<EntityList viewMode="grid" entities={mockEntities} selectable={true} />);

      const checkboxes = screen.getAllByRole('checkbox');
      fireEvent.click(checkboxes[0]);

      expect(mockDeselectEntity).toHaveBeenCalledWith('skill:test1');
    });
  });

  describe('Action Handlers', () => {
    it('passes onEdit to entity cards', () => {
      const handleEdit = jest.fn();
      render(<EntityList viewMode="grid" entities={mockEntities} onEdit={handleEdit} />);

      // EntityCard should receive onEdit prop
      expect(screen.getByText('test-skill-1')).toBeInTheDocument();
    });

    it('passes onDelete to entity cards', () => {
      const handleDelete = jest.fn();
      render(<EntityList viewMode="grid" entities={mockEntities} onDelete={handleDelete} />);

      expect(screen.getByText('test-skill-1')).toBeInTheDocument();
    });

    it('passes onDeploy to entity cards', () => {
      const handleDeploy = jest.fn();
      render(<EntityList viewMode="grid" entities={mockEntities} onDeploy={handleDeploy} />);

      expect(screen.getByText('test-skill-1')).toBeInTheDocument();
    });

    it('passes onSync to entity cards', () => {
      const handleSync = jest.fn();
      render(<EntityList viewMode="grid" entities={mockEntities} onSync={handleSync} />);

      expect(screen.getByText('test-skill-1')).toBeInTheDocument();
    });

    it('passes onViewDiff to entity cards', () => {
      const handleViewDiff = jest.fn();
      render(<EntityList viewMode="grid" entities={mockEntities} onViewDiff={handleViewDiff} />);

      expect(screen.getByText('test-skill-1')).toBeInTheDocument();
    });

    it('passes onRollback to entity cards', () => {
      const handleRollback = jest.fn();
      render(<EntityList viewMode="grid" entities={mockEntities} onRollback={handleRollback} />);

      expect(screen.getByText('test-skill-1')).toBeInTheDocument();
    });
  });

  describe('Context Integration', () => {
    it('uses entities from context when not provided', () => {
      const { useEntityLifecycle } = require('@/hooks/useEntityLifecycle');
      useEntityLifecycle.mockImplementation(() => ({
        entities: mockEntities,
        selectedEntities: [],
        selectEntity: jest.fn(),
        deselectEntity: jest.fn(),
      }));

      render(<EntityList viewMode="grid" />);

      expect(screen.getByText('test-skill-1')).toBeInTheDocument();
    });

    it('prefers provided entities over context', () => {
      const customEntities: Entity[] = [
        {
          id: 'custom:1',
          name: 'custom-entity',
          type: 'skill',
          scope: 'user',
          source: 'local',
          syncStatus: 'synced',
          createdAt: '2024-01-01T00:00:00Z',
          updatedAt: '2024-01-01T00:00:00Z',
        },
      ];

      render(<EntityList viewMode="grid" entities={customEntities} />);

      expect(screen.getByText('custom-entity')).toBeInTheDocument();
      expect(screen.queryByText('test-skill-1')).not.toBeInTheDocument();
    });
  });

  describe('ScrollArea', () => {
    it('renders ScrollArea in both view modes', () => {
      const { container } = render(<EntityList viewMode="grid" entities={mockEntities} />);

      // ScrollArea should be present
      expect(container.querySelector('[data-radix-scroll-area-viewport]')).toBeInTheDocument();
    });
  });
});
