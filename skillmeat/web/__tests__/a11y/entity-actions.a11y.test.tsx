/**
 * Accessibility Tests for EntityActions Component
 * @jest-environment jsdom
 */
import { render } from '@testing-library/react';
import { axe } from 'jest-axe';
import { EntityActions } from '@/components/entity/entity-actions';
import type { Entity } from '@/types/entity';

const mockEntity: Entity = {
  id: 'skill:test',
  uuid: '00000000000000000000000000000001',
  name: 'test-skill',
  type: 'skill',
  scope: 'user',
  source: 'github:user/repo/skill',
  syncStatus: 'synced',
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
};

describe('EntityActions Accessibility', () => {
  it('should have no accessibility violations', async () => {
    const { container } = render(<EntityActions entity={mockEntity} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have accessible menu trigger button', async () => {
    const { getByRole } = render(<EntityActions entity={mockEntity} />);

    const menuButton = getByRole('button');
    expect(menuButton).toHaveAccessibleName();
  });

  it('should have no violations with all action handlers', async () => {
    const { container } = render(
      <EntityActions
        entity={mockEntity}
        onEdit={jest.fn()}
        onDelete={jest.fn()}
        onDeploy={jest.fn()}
        onSync={jest.fn()}
        onViewDiff={jest.fn()}
        onRollback={jest.fn()}
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have no violations with modified entity showing diff option', async () => {
    const modifiedEntity = { ...mockEntity, syncStatus: 'modified' as const };
    const { container } = render(<EntityActions entity={modifiedEntity} onViewDiff={jest.fn()} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have no violations with conflict entity showing rollback', async () => {
    const conflictEntity = { ...mockEntity, syncStatus: 'conflict' as const };
    const { container } = render(<EntityActions entity={conflictEntity} onRollback={jest.fn()} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
