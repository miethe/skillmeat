/**
 * Accessibility Tests for EntityCard Component
 * @jest-environment jsdom
 */
import { render } from '@testing-library/react';
import { axe } from 'jest-axe';
import { EntityCard } from '@/components/entity/entity-card';
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

describe('EntityCard Accessibility', () => {
  it('should have no accessibility violations in default state', async () => {
    const { container } = render(<EntityCard entity={mockEntity} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have no violations when selectable', async () => {
    const { container } = render(
      <EntityCard entity={mockEntity} selectable={true} />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have no violations when selected', async () => {
    const { container } = render(
      <EntityCard entity={mockEntity} selectable={true} selected={true} />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have no violations with modified status', async () => {
    const modifiedEntity = { ...mockEntity, status: 'modified' as const };
    const { container } = render(<EntityCard entity={modifiedEntity} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have no violations with conflict status', async () => {
    const conflictEntity = { ...mockEntity, status: 'conflict' as const };
    const { container } = render(<EntityCard entity={conflictEntity} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have no violations without description', async () => {
    const noDescEntity = { ...mockEntity, description: undefined };
    const { container } = render(<EntityCard entity={noDescEntity} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have no violations with many tags', async () => {
    const manyTagsEntity = {
      ...mockEntity,
      tags: ['tag1', 'tag2', 'tag3', 'tag4', 'tag5'],
    };
    const { container } = render(<EntityCard entity={manyTagsEntity} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have accessible checkbox label when selectable', async () => {
    const { container, getByRole } = render(
      <EntityCard entity={mockEntity} selectable={true} />
    );

    const checkbox = getByRole('checkbox');
    expect(checkbox).toBeInTheDocument();

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have color contrast compliant status indicators', async () => {
    const statuses: Array<'synced' | 'modified' | 'outdated' | 'conflict'> = [
      'synced',
      'modified',
      'outdated',
      'conflict',
    ];

    for (const status of statuses) {
      const statusEntity = { ...mockEntity, status };
      const { container } = render(<EntityCard entity={statusEntity} />);
      const results = await axe(container, {
        rules: {
          'color-contrast': { enabled: true },
        },
      });
      expect(results).toHaveNoViolations();
    }
  });
});
