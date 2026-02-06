/**
 * @jest-environment jsdom
 */
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DeploymentBadgeStack } from '@/components/shared/deployment-badge-stack';
import type { DeploymentSummary } from '@/types/artifact';

// Factory function for creating test deployments
function createTestDeployment(overrides: Partial<DeploymentSummary> = {}): DeploymentSummary {
  return {
    project_path: '/Users/test/projects/my-project',
    project_name: 'my-project',
    deployed_at: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('DeploymentBadgeStack', () => {
  describe('empty state', () => {
    it('returns null for empty deployments array', () => {
      const { container } = render(<DeploymentBadgeStack deployments={[]} />);
      expect(container.firstChild).toBeNull();
    });

    it('returns null for undefined deployments', () => {
      const { container } = render(
        <DeploymentBadgeStack deployments={undefined as unknown as DeploymentSummary[]} />
      );
      expect(container.firstChild).toBeNull();
    });

    it('returns null for null deployments', () => {
      const { container } = render(
        <DeploymentBadgeStack deployments={null as unknown as DeploymentSummary[]} />
      );
      expect(container.firstChild).toBeNull();
    });
  });

  describe('single deployment', () => {
    it('renders single deployment correctly', () => {
      const deployments = [createTestDeployment()];
      render(<DeploymentBadgeStack deployments={deployments} />);

      expect(screen.getByLabelText('Deployed to my-project')).toBeInTheDocument();
    });

    it('uses project_name when available', () => {
      const deployments = [
        createTestDeployment({ project_name: 'Custom Name', project_path: '/path/to/different' }),
      ];
      render(<DeploymentBadgeStack deployments={deployments} />);

      expect(screen.getByLabelText('Deployed to Custom Name')).toBeInTheDocument();
    });

    it('extracts project name from path when project_name is empty', () => {
      const deployments = [
        createTestDeployment({
          project_name: '',
          project_path: '/Users/test/projects/extracted-name',
        }),
      ];
      render(<DeploymentBadgeStack deployments={deployments} />);

      expect(screen.getByText('extracted-name')).toBeInTheDocument();
    });
  });

  describe('multiple deployments', () => {
    it('renders all deployments when count is within maxBadges', () => {
      const deployments = [
        createTestDeployment({ project_name: 'project-1', project_path: '/path/1' }),
        createTestDeployment({ project_name: 'project-2', project_path: '/path/2' }),
      ];
      render(<DeploymentBadgeStack deployments={deployments} />);

      expect(screen.getByLabelText('Deployed to project-1')).toBeInTheDocument();
      expect(screen.getByLabelText('Deployed to project-2')).toBeInTheDocument();
    });

    it('shows overflow badge when deployments exceed maxBadges', () => {
      const deployments = [
        createTestDeployment({ project_name: 'project-1', project_path: '/path/1' }),
        createTestDeployment({ project_name: 'project-2', project_path: '/path/2' }),
        createTestDeployment({ project_name: 'project-3', project_path: '/path/3' }),
      ];
      render(<DeploymentBadgeStack deployments={deployments} maxBadges={2} />);

      expect(screen.getByLabelText('Deployed to project-1')).toBeInTheDocument();
      expect(screen.getByLabelText('Deployed to project-2')).toBeInTheDocument();
      expect(screen.getByLabelText('1 more deployments')).toBeInTheDocument();
      expect(screen.getByText('+1')).toBeInTheDocument();
    });

    it('respects custom maxBadges prop', () => {
      const deployments = [
        createTestDeployment({ project_name: 'project-1', project_path: '/path/1' }),
        createTestDeployment({ project_name: 'project-2', project_path: '/path/2' }),
        createTestDeployment({ project_name: 'project-3', project_path: '/path/3' }),
        createTestDeployment({ project_name: 'project-4', project_path: '/path/4' }),
      ];
      render(<DeploymentBadgeStack deployments={deployments} maxBadges={3} />);

      expect(screen.getByLabelText('Deployed to project-1')).toBeInTheDocument();
      expect(screen.getByLabelText('Deployed to project-2')).toBeInTheDocument();
      expect(screen.getByLabelText('Deployed to project-3')).toBeInTheDocument();
      expect(screen.getByLabelText('1 more deployments')).toBeInTheDocument();
    });

    it('shows correct overflow count', () => {
      const deployments = [
        createTestDeployment({ project_name: 'project-1', project_path: '/path/1' }),
        createTestDeployment({ project_name: 'project-2', project_path: '/path/2' }),
        createTestDeployment({ project_name: 'project-3', project_path: '/path/3' }),
        createTestDeployment({ project_name: 'project-4', project_path: '/path/4' }),
        createTestDeployment({ project_name: 'project-5', project_path: '/path/5' }),
      ];
      render(<DeploymentBadgeStack deployments={deployments} maxBadges={2} />);

      expect(screen.getByText('+3')).toBeInTheDocument();
      expect(screen.getByLabelText('3 more deployments')).toBeInTheDocument();
    });
  });

  describe('badge click handling', () => {
    it('calls onBadgeClick when badge is clicked', async () => {
      const user = userEvent.setup();
      const onBadgeClick = jest.fn();
      const deployment = createTestDeployment();
      const deployments = [deployment];

      render(<DeploymentBadgeStack deployments={deployments} onBadgeClick={onBadgeClick} />);

      const badge = screen.getByLabelText('Deployed to my-project');
      await user.click(badge);

      expect(onBadgeClick).toHaveBeenCalledTimes(1);
      expect(onBadgeClick).toHaveBeenCalledWith(deployment);
    });

    it('badge is not clickable when no onBadgeClick handler', () => {
      const deployments = [createTestDeployment()];
      render(<DeploymentBadgeStack deployments={deployments} />);

      const badge = screen.getByLabelText('Deployed to my-project');
      expect(badge).not.toHaveAttribute('role', 'button');
      expect(badge).not.toHaveAttribute('tabIndex');
    });

    it('badge is keyboard accessible when clickable', async () => {
      const user = userEvent.setup();
      const onBadgeClick = jest.fn();
      const deployment = createTestDeployment();
      const deployments = [deployment];

      render(<DeploymentBadgeStack deployments={deployments} onBadgeClick={onBadgeClick} />);

      const badge = screen.getByLabelText('Deployed to my-project');
      expect(badge).toHaveAttribute('role', 'button');
      expect(badge).toHaveAttribute('tabIndex', '0');

      // Focus and press Enter
      badge.focus();
      await user.keyboard('{Enter}');

      expect(onBadgeClick).toHaveBeenCalledWith(deployment);
    });

    it('badge responds to Space key when clickable', async () => {
      const user = userEvent.setup();
      const onBadgeClick = jest.fn();
      const deployment = createTestDeployment();
      const deployments = [deployment];

      render(<DeploymentBadgeStack deployments={deployments} onBadgeClick={onBadgeClick} />);

      const badge = screen.getByLabelText('Deployed to my-project');
      badge.focus();
      await user.keyboard(' ');

      expect(onBadgeClick).toHaveBeenCalledWith(deployment);
    });
  });

  describe('overflow badge click handling', () => {
    it('calls onOverflowClick when overflow badge is clicked', async () => {
      const user = userEvent.setup();
      const onOverflowClick = jest.fn();
      const deployments = [
        createTestDeployment({ project_name: 'project-1', project_path: '/path/1' }),
        createTestDeployment({ project_name: 'project-2', project_path: '/path/2' }),
        createTestDeployment({ project_name: 'project-3', project_path: '/path/3' }),
      ];

      render(
        <DeploymentBadgeStack
          deployments={deployments}
          maxBadges={2}
          onOverflowClick={onOverflowClick}
        />
      );

      const overflowBadge = screen.getByLabelText('1 more deployments');
      await user.click(overflowBadge);

      expect(onOverflowClick).toHaveBeenCalledTimes(1);
    });

    it('overflow badge is not clickable when no onOverflowClick handler', () => {
      const deployments = [
        createTestDeployment({ project_name: 'project-1', project_path: '/path/1' }),
        createTestDeployment({ project_name: 'project-2', project_path: '/path/2' }),
        createTestDeployment({ project_name: 'project-3', project_path: '/path/3' }),
      ];

      render(<DeploymentBadgeStack deployments={deployments} maxBadges={2} />);

      const overflowBadge = screen.getByLabelText('1 more deployments');
      expect(overflowBadge).not.toHaveAttribute('role', 'button');
    });

    it('overflow badge is keyboard accessible when clickable', async () => {
      const user = userEvent.setup();
      const onOverflowClick = jest.fn();
      const deployments = [
        createTestDeployment({ project_name: 'project-1', project_path: '/path/1' }),
        createTestDeployment({ project_name: 'project-2', project_path: '/path/2' }),
        createTestDeployment({ project_name: 'project-3', project_path: '/path/3' }),
      ];

      render(
        <DeploymentBadgeStack
          deployments={deployments}
          maxBadges={2}
          onOverflowClick={onOverflowClick}
        />
      );

      const overflowBadge = screen.getByLabelText('1 more deployments');
      overflowBadge.focus();
      await user.keyboard('{Enter}');

      expect(onOverflowClick).toHaveBeenCalled();
    });
  });

  describe('path extraction', () => {
    it('extracts project name from Unix path', () => {
      const deployments = [
        createTestDeployment({
          project_name: '',
          project_path: '/Users/test/projects/unix-project',
        }),
      ];
      render(<DeploymentBadgeStack deployments={deployments} />);

      expect(screen.getByText('unix-project')).toBeInTheDocument();
    });

    it('extracts project name from Windows path', () => {
      const deployments = [
        createTestDeployment({
          project_name: '',
          project_path: 'C:\\Users\\test\\projects\\windows-project',
        }),
      ];
      render(<DeploymentBadgeStack deployments={deployments} />);

      expect(screen.getByText('windows-project')).toBeInTheDocument();
    });

    it('handles empty project path gracefully', () => {
      const deployments = [
        createTestDeployment({
          project_name: '',
          project_path: '',
        }),
      ];
      render(<DeploymentBadgeStack deployments={deployments} />);

      // Should show "Unknown" for empty path
      expect(screen.getByText('Unknown')).toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('has role="list" on container', () => {
      const deployments = [createTestDeployment()];
      render(<DeploymentBadgeStack deployments={deployments} />);

      expect(screen.getByRole('list')).toBeInTheDocument();
    });

    it('has aria-label on container', () => {
      const deployments = [createTestDeployment()];
      render(<DeploymentBadgeStack deployments={deployments} />);

      expect(screen.getByRole('list')).toHaveAttribute('aria-label', 'Deployment locations');
    });

    it('each badge is wrapped in listitem', () => {
      const deployments = [
        createTestDeployment({ project_name: 'project-1', project_path: '/path/1' }),
        createTestDeployment({ project_name: 'project-2', project_path: '/path/2' }),
      ];
      render(<DeploymentBadgeStack deployments={deployments} />);

      const listitems = screen.getAllByRole('listitem');
      expect(listitems).toHaveLength(2);
    });

    it('overflow badge is in listitem', () => {
      const deployments = [
        createTestDeployment({ project_name: 'project-1', project_path: '/path/1' }),
        createTestDeployment({ project_name: 'project-2', project_path: '/path/2' }),
        createTestDeployment({ project_name: 'project-3', project_path: '/path/3' }),
      ];
      render(<DeploymentBadgeStack deployments={deployments} maxBadges={2} />);

      const listitems = screen.getAllByRole('listitem');
      expect(listitems).toHaveLength(3); // 2 visible + 1 overflow
    });

    it('badge has descriptive aria-label', () => {
      const deployments = [
        createTestDeployment({ project_name: 'my-awesome-project', project_path: '/path' }),
      ];
      render(<DeploymentBadgeStack deployments={deployments} />);

      expect(screen.getByLabelText('Deployed to my-awesome-project')).toBeInTheDocument();
    });

    it('folder icon has aria-hidden', () => {
      const deployments = [createTestDeployment()];
      const { container } = render(<DeploymentBadgeStack deployments={deployments} />);

      const icon = container.querySelector('[aria-hidden="true"]');
      expect(icon).toBeInTheDocument();
    });
  });

  describe('custom className', () => {
    it('applies custom className to container', () => {
      const deployments = [createTestDeployment()];
      render(<DeploymentBadgeStack deployments={deployments} className="custom-class" />);

      const list = screen.getByRole('list');
      expect(list).toHaveClass('custom-class');
    });

    it('merges custom className with default classes', () => {
      const deployments = [createTestDeployment()];
      render(<DeploymentBadgeStack deployments={deployments} className="custom-class" />);

      const list = screen.getByRole('list');
      expect(list).toHaveClass('custom-class');
      expect(list).toHaveClass('flex');
    });
  });

  describe('tooltip on overflow badge', () => {
    it('overflow badge has tooltip structure', () => {
      const deployments = [
        createTestDeployment({ project_name: 'project-1', project_path: '/path/1' }),
        createTestDeployment({ project_name: 'project-2', project_path: '/path/2' }),
        createTestDeployment({ project_name: 'project-3', project_path: '/path/3' }),
      ];
      const { container } = render(
        <DeploymentBadgeStack deployments={deployments} maxBadges={2} />
      );

      // Tooltip trigger should be present
      const tooltipTrigger = container.querySelector('[data-state]');
      expect(tooltipTrigger).toBeInTheDocument();
    });
  });

  describe('edge cases', () => {
    it('handles single deployment at exact maxBadges', () => {
      const deployments = [createTestDeployment()];
      render(<DeploymentBadgeStack deployments={deployments} maxBadges={1} />);

      expect(screen.getByLabelText('Deployed to my-project')).toBeInTheDocument();
      expect(screen.queryByText(/\+\d+/)).not.toBeInTheDocument();
    });

    it('handles maxBadges of 0', () => {
      const deployments = [
        createTestDeployment({ project_name: 'project-1', project_path: '/path/1' }),
        createTestDeployment({ project_name: 'project-2', project_path: '/path/2' }),
      ];
      render(<DeploymentBadgeStack deployments={deployments} maxBadges={0} />);

      // All deployments should be in overflow
      expect(screen.getByText('+2')).toBeInTheDocument();
    });

    it('handles large number of deployments', () => {
      const deployments = Array.from({ length: 10 }, (_, i) =>
        createTestDeployment({
          project_name: `project-${i + 1}`,
          project_path: `/path/${i + 1}`,
        })
      );
      render(<DeploymentBadgeStack deployments={deployments} maxBadges={2} />);

      expect(screen.getByText('+8')).toBeInTheDocument();
      expect(screen.getByLabelText('8 more deployments')).toBeInTheDocument();
    });

    it('handles deployments with special characters in names', () => {
      const deployments = [
        createTestDeployment({
          project_name: 'my-project_v2.0',
          project_path: '/path/my-project_v2.0',
        }),
      ];
      render(<DeploymentBadgeStack deployments={deployments} />);

      expect(screen.getByText('my-project_v2.0')).toBeInTheDocument();
    });
  });

  describe('visual styling', () => {
    it('badges have hover style when clickable', () => {
      const onBadgeClick = jest.fn();
      const deployments = [createTestDeployment()];
      const { container } = render(
        <DeploymentBadgeStack deployments={deployments} onBadgeClick={onBadgeClick} />
      );

      const badge = container.querySelector('[role="button"]');
      expect(badge).toHaveClass('cursor-pointer');
      expect(badge).toHaveClass('hover:bg-muted');
    });

    it('badges do not have hover style when not clickable', () => {
      const deployments = [createTestDeployment()];
      render(<DeploymentBadgeStack deployments={deployments} />);

      const badge = screen.getByLabelText('Deployed to my-project');
      expect(badge).not.toHaveClass('cursor-pointer');
    });

    it('text is truncated for long project names', () => {
      const deployments = [
        createTestDeployment({
          project_name: 'very-long-project-name-that-should-be-truncated',
          project_path: '/path',
        }),
      ];
      const { container } = render(<DeploymentBadgeStack deployments={deployments} />);

      const textSpan = container.querySelector('.truncate');
      expect(textSpan).toBeInTheDocument();
    });
  });
});
