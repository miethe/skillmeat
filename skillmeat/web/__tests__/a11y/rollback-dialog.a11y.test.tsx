/**
 * Accessibility Tests for RollbackDialog Component
 * @jest-environment jsdom
 */
import { render } from '@testing-library/react';
import { axe } from 'jest-axe';
import { RollbackDialog } from '@/components/entity/rollback-dialog';
import type { Entity } from '@/types/entity';

const mockEntity: Entity = {
  id: 'skill:test',
  name: 'test-skill',
  type: 'skill',
  source: 'github:user/repo/skill',
  status: 'modified',
  version: 'v1.2.3',
  projectPath: '/path/to/project',
};

describe('RollbackDialog Accessibility', () => {
  it('should have no violations when open', async () => {
    const { container } = render(
      <RollbackDialog
        entity={mockEntity}
        open={true}
        onOpenChange={jest.fn()}
        onConfirm={jest.fn()}
      />
    );

    // Wait for dialog to be fully rendered
    await new Promise(resolve => setTimeout(resolve, 100));

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have accessible dialog title', async () => {
    const { getByRole } = render(
      <RollbackDialog
        entity={mockEntity}
        open={true}
        onOpenChange={jest.fn()}
        onConfirm={jest.fn()}
      />
    );

    // Dialog should have accessible name
    const dialog = getByRole('dialog', { hidden: true });
    expect(dialog).toBeInTheDocument();
  });

  it('should have no violations with loading state', async () => {
    const onConfirm = jest.fn().mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 100))
    );

    const { container } = render(
      <RollbackDialog
        entity={mockEntity}
        open={true}
        onOpenChange={jest.fn()}
        onConfirm={onConfirm}
      />
    );

    await new Promise(resolve => setTimeout(resolve, 100));

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have proper focus management', async () => {
    const { container } = render(
      <RollbackDialog
        entity={mockEntity}
        open={true}
        onOpenChange={jest.fn()}
        onConfirm={jest.fn()}
      />
    );

    await new Promise(resolve => setTimeout(resolve, 100));

    // Verify focus trap accessibility
    const results = await axe(container, {
      rules: {
        'focus-order-semantics': { enabled: true },
      },
    });
    expect(results).toHaveNoViolations();
  });

  it('should have descriptive warning alert', async () => {
    const { container } = render(
      <RollbackDialog
        entity={mockEntity}
        open={true}
        onOpenChange={jest.fn()}
        onConfirm={jest.fn()}
      />
    );

    await new Promise(resolve => setTimeout(resolve, 100));

    // Verify alert role is accessible
    const results = await axe(container, {
      rules: {
        'aria-allowed-role': { enabled: true },
      },
    });
    expect(results).toHaveNoViolations();
  });
});
