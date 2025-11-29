/**
 * Accessibility Tests for EntityRow Component
 * @jest-environment jsdom
 */
import { render } from '@testing-library/react';
import { axe } from 'jest-axe';
import { EntityRow } from '@/components/entity/entity-row';
import type { Entity } from '@/types/entity';

const mockEntity: Entity = {
  id: 'skill:test',
  name: 'test-skill',
  type: 'skill',
  source: 'github:user/repo/skill',
  status: 'synced',
  tags: ['testing', 'example'],
  description: 'A test skill for accessibility testing',
};

describe('EntityRow Accessibility', () => {
  it('should have no accessibility violations in default state', async () => {
    const { container } = render(<EntityRow entity={mockEntity} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have no violations when selectable', async () => {
    const { container } = render(<EntityRow entity={mockEntity} selectable={true} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have no violations when selected', async () => {
    const { container } = render(
      <EntityRow entity={mockEntity} selectable={true} selected={true} />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have accessible checkbox when selectable', async () => {
    const { getByRole, container } = render(<EntityRow entity={mockEntity} selectable={true} />);

    const checkbox = getByRole('checkbox');
    expect(checkbox).toBeInTheDocument();

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have no violations with different entity types', async () => {
    const entityTypes: Array<Entity['type']> = ['skill', 'command', 'agent', 'mcp', 'hook'];

    for (const type of entityTypes) {
      const entity = { ...mockEntity, type, id: `${type}:test` };
      const { container } = render(<EntityRow entity={entity} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    }
  });

  it('should have proper color contrast for status indicators', async () => {
    const statuses: Array<'synced' | 'modified' | 'outdated' | 'conflict'> = [
      'synced',
      'modified',
      'outdated',
      'conflict',
    ];

    for (const status of statuses) {
      const statusEntity = { ...mockEntity, status };
      const { container } = render(<EntityRow entity={statusEntity} />);
      const results = await axe(container, {
        rules: {
          'color-contrast': { enabled: true },
        },
      });
      expect(results).toHaveNoViolations();
    }
  });

  it('should have no violations without description', async () => {
    const noDescEntity = { ...mockEntity, description: undefined };
    const { container } = render(<EntityRow entity={noDescEntity} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have no violations without tags', async () => {
    const noTagsEntity = { ...mockEntity, tags: undefined };
    const { container } = render(<EntityRow entity={noTagsEntity} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
