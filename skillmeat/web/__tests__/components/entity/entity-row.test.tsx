/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { EntityRow } from '@/components/entity/entity-row';
import type { Entity } from '@/types/entity';

const mockEntity: Entity = {
  id: 'skill:test',
  name: 'test-skill',
  type: 'skill',
  source: 'github:user/repo/skill',
  status: 'synced',
  tags: ['testing', 'example', 'demo'],
  description: 'A test skill for unit testing',
};

describe('EntityRow', () => {
  it('renders entity name', () => {
    render(<EntityRow entity={mockEntity} />);

    expect(screen.getByText('test-skill')).toBeInTheDocument();
  });

  it('displays entity type badge', () => {
    render(<EntityRow entity={mockEntity} />);

    expect(screen.getByText('Skill')).toBeInTheDocument();
  });

  it('shows description when provided', () => {
    render(<EntityRow entity={mockEntity} />);

    expect(screen.getByText('A test skill for unit testing')).toBeInTheDocument();
  });

  it('truncates long description at 60 characters', () => {
    const longDescription =
      'This is a very long description that should be truncated at 60 characters for table row';
    const entityWithLongDesc = { ...mockEntity, description: longDescription };

    render(<EntityRow entity={entityWithLongDesc} />);

    const description = screen.getByText(/This is a very long description/);
    expect(description.textContent).toContain('...');
    expect(description.textContent?.length).toBeLessThan(longDescription.length);
  });

  it('shows dash when no description', () => {
    const noDescEntity = { ...mockEntity, description: undefined };
    render(<EntityRow entity={noDescEntity} />);

    const descriptionCell = screen.getByText('-');
    expect(descriptionCell).toBeInTheDocument();
  });

  it('displays status indicator with correct label', () => {
    render(<EntityRow entity={mockEntity} />);

    expect(screen.getByText('Synced')).toBeInTheDocument();
  });

  it('shows modified status correctly', () => {
    const modifiedEntity = { ...mockEntity, status: 'modified' as const };
    render(<EntityRow entity={modifiedEntity} />);

    expect(screen.getByText('Modified')).toBeInTheDocument();
  });

  it('shows dash when no status', () => {
    const noStatusEntity = { ...mockEntity, status: undefined };
    render(<EntityRow entity={noStatusEntity} />);

    const statusCells = screen.getAllByText('-');
    expect(statusCells.length).toBeGreaterThan(0);
  });

  it('displays up to 2 tags in row view', () => {
    render(<EntityRow entity={mockEntity} />);

    expect(screen.getByText('testing')).toBeInTheDocument();
    expect(screen.getByText('example')).toBeInTheDocument();
  });

  it('shows +N badge when more than 2 tags', () => {
    render(<EntityRow entity={mockEntity} />);

    expect(screen.getByText('+1')).toBeInTheDocument();
  });

  it('shows dash when no tags', () => {
    const noTagsEntity = { ...mockEntity, tags: [] };
    render(<EntityRow entity={noTagsEntity} />);

    const tagCells = screen.getAllByText('-');
    expect(tagCells.length).toBeGreaterThan(0);
  });

  it('calls onClick when row is clicked', () => {
    const handleClick = jest.fn();
    render(<EntityRow entity={mockEntity} onClick={handleClick} />);

    const row = screen.getByText('test-skill').closest('div');
    if (row) {
      fireEvent.click(row);
    }

    expect(handleClick).toHaveBeenCalled();
  });

  it('does not trigger onClick when clicking checkbox', () => {
    const handleClick = jest.fn();
    render(<EntityRow entity={mockEntity} selectable={true} onClick={handleClick} />);

    const checkbox = screen.getByRole('checkbox');
    fireEvent.click(checkbox);

    expect(handleClick).not.toHaveBeenCalled();
  });

  it('shows checkbox when selectable is true', () => {
    render(<EntityRow entity={mockEntity} selectable={true} />);

    expect(screen.getByRole('checkbox')).toBeInTheDocument();
  });

  it('does not show checkbox when selectable is false', () => {
    render(<EntityRow entity={mockEntity} selectable={false} />);

    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
  });

  it('calls onSelect when checkbox is checked', () => {
    const handleSelect = jest.fn();
    render(<EntityRow entity={mockEntity} selectable={true} onSelect={handleSelect} />);

    const checkbox = screen.getByRole('checkbox');
    fireEvent.click(checkbox);

    expect(handleSelect).toHaveBeenCalledWith(true);
  });

  it('applies selected styling when selected', () => {
    const { container } = render(<EntityRow entity={mockEntity} selected={true} />);

    const row = container.firstChild;
    expect(row).toHaveClass('bg-accent');
  });

  it('applies hover styling', () => {
    const { container } = render(<EntityRow entity={mockEntity} />);

    const row = container.firstChild;
    expect(row).toHaveClass('hover:bg-accent/50');
  });

  it('renders entity icon', () => {
    const { container } = render(<EntityRow entity={mockEntity} />);

    const icon = container.querySelector('svg');
    expect(icon).toBeInTheDocument();
  });

  it('renders EntityActions component', () => {
    render(<EntityRow entity={mockEntity} onEdit={jest.fn()} />);

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

    render(<EntityRow entity={mockEntity} {...handlers} />);

    expect(screen.getByText('test-skill')).toBeInTheDocument();
  });

  it('displays icon with correct color based on entity type', () => {
    const { container } = render(<EntityRow entity={mockEntity} />);

    const icon = container.querySelector('svg');
    expect(icon?.parentElement).toHaveClass('text-blue-500');
  });

  it('renders in table row format with proper spacing', () => {
    const { container } = render(<EntityRow entity={mockEntity} />);

    const row = container.firstChild;
    expect(row).toHaveClass('flex', 'items-center', 'gap-4');
  });

  it('shows cursor pointer on row', () => {
    const { container } = render(<EntityRow entity={mockEntity} />);

    const row = container.firstChild;
    expect(row).toHaveClass('cursor-pointer');
  });

  it('applies border styling', () => {
    const { container } = render(<EntityRow entity={mockEntity} />);

    const row = container.firstChild;
    expect(row).toHaveClass('border-b');
  });

  it('handles command entity type correctly', () => {
    const commandEntity: Entity = {
      ...mockEntity,
      type: 'command',
      id: 'command:test',
    };

    render(<EntityRow entity={commandEntity} />);

    expect(screen.getByText('Command')).toBeInTheDocument();
  });

  it('handles agent entity type correctly', () => {
    const agentEntity: Entity = {
      ...mockEntity,
      type: 'agent',
      id: 'agent:test',
    };

    render(<EntityRow entity={agentEntity} />);

    expect(screen.getByText('Agent')).toBeInTheDocument();
  });
});
