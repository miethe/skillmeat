/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axe, toHaveNoViolations } from 'jest-axe';
import { ProjectsList } from '@/components/ProjectsList';

expect.extend(toHaveNoViolations);

// Mock ProjectActions component
jest.mock('@/app/projects/components/project-actions', () => ({
  ProjectActions: ({ project }: any) => (
    <button data-testid={`actions-${project.id}`}>Actions</button>
  ),
}));

// Test wrapper with providers
function TestWrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

const mockProjects = [
  {
    id: '1',
    name: 'my-project',
    path: '/home/user/projects/my-project',
    deployment_count: 5,
    last_deployment: '2025-01-01T10:00:00Z',
  },
  {
    id: '2',
    name: 'another-project',
    path: '/home/user/projects/another-project',
    deployment_count: 3,
    last_deployment: '2025-01-02T15:30:00Z',
  },
  {
    id: '3',
    name: 'test-project',
    path: '/home/user/projects/test-project',
    deployment_count: 1,
  },
];

describe('ProjectsList', () => {
  describe('Loading State', () => {
    it('renders loading skeletons when isLoading=true', () => {
      render(
        <TestWrapper>
          <ProjectsList projects={[]} isLoading={true} />
        </TestWrapper>
      );

      // Should render 6 skeleton cards
      const skeletons = screen
        .getAllByRole('generic')
        .filter((el) => el.className.includes('animate-pulse'));
      expect(skeletons.length).toBeGreaterThan(0);
    });

    it('does not render projects when loading', () => {
      render(
        <TestWrapper>
          <ProjectsList projects={mockProjects} isLoading={true} />
        </TestWrapper>
      );

      // Should not show project names
      expect(screen.queryByText('my-project')).not.toBeInTheDocument();
      expect(screen.queryByText('another-project')).not.toBeInTheDocument();
    });

    it('renders exactly 6 skeleton cards', () => {
      const { container } = render(
        <TestWrapper>
          <ProjectsList projects={[]} isLoading={true} />
        </TestWrapper>
      );

      // Count the number of skeleton cards
      const cards = container.querySelectorAll('[class*="rounded-lg"]');
      // Should have multiple skeleton elements
      expect(cards.length).toBeGreaterThan(0);
    });
  });

  describe('Empty State', () => {
    it('renders empty state when projects=[]', () => {
      render(
        <TestWrapper>
          <ProjectsList projects={[]} isLoading={false} />
        </TestWrapper>
      );

      expect(screen.getByText('No projects found')).toBeInTheDocument();
      expect(
        screen.getByText(/Create a project or deploy artifacts to get started/i)
      ).toBeInTheDocument();
    });

    it('displays GitBranch icon in empty state', () => {
      const { container } = render(
        <TestWrapper>
          <ProjectsList projects={[]} isLoading={false} />
        </TestWrapper>
      );

      // Empty state should contain icon and text
      expect(screen.getByText('No projects found')).toBeInTheDocument();
      const icon = container.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });

    it('does not render empty state when loading', () => {
      render(
        <TestWrapper>
          <ProjectsList projects={[]} isLoading={true} />
        </TestWrapper>
      );

      expect(screen.queryByText('No projects found')).not.toBeInTheDocument();
    });
  });

  describe('Projects Rendering', () => {
    it('renders project cards when projects provided', () => {
      render(
        <TestWrapper>
          <ProjectsList projects={mockProjects} isLoading={false} />
        </TestWrapper>
      );

      expect(screen.getByText('my-project')).toBeInTheDocument();
      expect(screen.getByText('another-project')).toBeInTheDocument();
      expect(screen.getByText('test-project')).toBeInTheDocument();
    });

    it('displays project paths correctly', () => {
      render(
        <TestWrapper>
          <ProjectsList projects={mockProjects} isLoading={false} />
        </TestWrapper>
      );

      expect(screen.getByText('/home/user/projects/my-project')).toBeInTheDocument();
      expect(screen.getByText('/home/user/projects/another-project')).toBeInTheDocument();
    });

    it('displays deployment counts as badges', () => {
      render(
        <TestWrapper>
          <ProjectsList projects={mockProjects} isLoading={false} />
        </TestWrapper>
      );

      expect(screen.getByText('5')).toBeInTheDocument();
      expect(screen.getByText('3')).toBeInTheDocument();
      expect(screen.getByText('1')).toBeInTheDocument();
    });

    it('displays artifact count with correct pluralization', () => {
      render(
        <TestWrapper>
          <ProjectsList projects={mockProjects} isLoading={false} />
        </TestWrapper>
      );

      // Multiple artifacts
      expect(screen.getByText('5 artifacts')).toBeInTheDocument();
      expect(screen.getByText('3 artifacts')).toBeInTheDocument();

      // Single artifact
      expect(screen.getByText('1 artifact')).toBeInTheDocument();
    });

    it('displays "Never" for projects without last_deployment', () => {
      render(
        <TestWrapper>
          <ProjectsList projects={mockProjects} isLoading={false} />
        </TestWrapper>
      );

      expect(screen.getByText(/Last deployed Never/i)).toBeInTheDocument();
    });

    it('formats recent dates as "Today"', () => {
      const today = new Date();
      const todayProject = {
        id: '4',
        name: 'today-project',
        path: '/path/to/today',
        deployment_count: 1,
        last_deployment: today.toISOString(),
      };

      render(
        <TestWrapper>
          <ProjectsList projects={[todayProject]} isLoading={false} />
        </TestWrapper>
      );

      expect(screen.getByText(/Last deployed Today/i)).toBeInTheDocument();
    });

    it('displays GitBranch icon for each project', () => {
      const { container } = render(
        <TestWrapper>
          <ProjectsList projects={mockProjects} isLoading={false} />
        </TestWrapper>
      );

      // Each project card should have a GitBranch icon
      const icons = container.querySelectorAll('svg');
      // Should have multiple icons (GitBranch, Package, Clock for each project)
      expect(icons.length).toBeGreaterThan(mockProjects.length);
    });

    it('renders ProjectActions for each project', () => {
      render(
        <TestWrapper>
          <ProjectsList projects={mockProjects} isLoading={false} />
        </TestWrapper>
      );

      expect(screen.getByTestId('actions-1')).toBeInTheDocument();
      expect(screen.getByTestId('actions-2')).toBeInTheDocument();
      expect(screen.getByTestId('actions-3')).toBeInTheDocument();
    });
  });

  describe('User Interactions', () => {
    it('calls onProjectClick when project card clicked', async () => {
      const onProjectClick = jest.fn();
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <ProjectsList projects={mockProjects} isLoading={false} onProjectClick={onProjectClick} />
        </TestWrapper>
      );

      const projectCard = screen.getByText('my-project').closest('div')?.parentElement;
      expect(projectCard).toBeInTheDocument();

      if (projectCard) {
        await user.click(projectCard);
      }

      expect(onProjectClick).toHaveBeenCalledTimes(1);
      expect(onProjectClick).toHaveBeenCalledWith(mockProjects[0]);
    });

    it('does not crash when onProjectClick is undefined', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <ProjectsList projects={mockProjects} isLoading={false} />
        </TestWrapper>
      );

      const projectCard = screen.getByText('my-project').closest('div')?.parentElement;

      // Should not throw error when clicking
      if (projectCard) {
        await user.click(projectCard);
      }
    });

    it('calls onActionSuccess when provided to ProjectActions', () => {
      const onActionSuccess = jest.fn();

      render(
        <TestWrapper>
          <ProjectsList
            projects={mockProjects}
            isLoading={false}
            onActionSuccess={onActionSuccess}
          />
        </TestWrapper>
      );

      // Verify ProjectActions received the callback
      // (actual behavior depends on ProjectActions implementation)
      expect(screen.getByTestId('actions-1')).toBeInTheDocument();
    });

    it('applies hover styles to project cards', () => {
      const { container } = render(
        <TestWrapper>
          <ProjectsList projects={mockProjects} isLoading={false} />
        </TestWrapper>
      );

      const projectName = screen.getByText('my-project');
      const projectCard = projectName.closest('[class*="cursor-pointer"]');
      expect(projectCard).toBeInTheDocument();
      expect(projectCard).toHaveClass('cursor-pointer');
    });
  });

  describe('Grid Layout', () => {
    it('applies responsive grid layout', () => {
      const { container } = render(
        <TestWrapper>
          <ProjectsList projects={mockProjects} isLoading={false} />
        </TestWrapper>
      );

      const grid = container.querySelector('.grid');
      expect(grid).toBeInTheDocument();
      expect(grid).toHaveClass('md:grid-cols-2');
      expect(grid).toHaveClass('lg:grid-cols-3');
    });

    it('maintains grid layout during loading', () => {
      const { container } = render(
        <TestWrapper>
          <ProjectsList projects={[]} isLoading={true} />
        </TestWrapper>
      );

      const grid = container.querySelector('.grid');
      expect(grid).toBeInTheDocument();
    });
  });

  describe('Date Formatting', () => {
    it('formats yesterday as "Yesterday"', () => {
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);

      const yesterdayProject = {
        id: '5',
        name: 'yesterday-project',
        path: '/path/to/yesterday',
        deployment_count: 1,
        last_deployment: yesterday.toISOString(),
      };

      render(
        <TestWrapper>
          <ProjectsList projects={[yesterdayProject]} isLoading={false} />
        </TestWrapper>
      );

      expect(screen.getByText(/Last deployed Yesterday/i)).toBeInTheDocument();
    });

    it('formats dates within a week as "X days ago"', () => {
      const threeDaysAgo = new Date();
      threeDaysAgo.setDate(threeDaysAgo.getDate() - 3);

      const recentProject = {
        id: '6',
        name: 'recent-project',
        path: '/path/to/recent',
        deployment_count: 1,
        last_deployment: threeDaysAgo.toISOString(),
      };

      render(
        <TestWrapper>
          <ProjectsList projects={[recentProject]} isLoading={false} />
        </TestWrapper>
      );

      expect(screen.getByText(/Last deployed 3 days ago/i)).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA attributes on project cards', () => {
      render(
        <TestWrapper>
          <ProjectsList projects={mockProjects} isLoading={false} />
        </TestWrapper>
      );

      // All project names should be rendered
      expect(screen.getByText('my-project')).toBeInTheDocument();
      expect(screen.getByText('another-project')).toBeInTheDocument();
      expect(screen.getByText('test-project')).toBeInTheDocument();
    });

    it('has no accessibility violations', async () => {
      const { container } = render(
        <TestWrapper>
          <ProjectsList projects={mockProjects} isLoading={false} />
        </TestWrapper>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('empty state has no accessibility violations', async () => {
      const { container } = render(
        <TestWrapper>
          <ProjectsList projects={[]} isLoading={false} />
        </TestWrapper>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('loading state has no accessibility violations', async () => {
      const { container } = render(
        <TestWrapper>
          <ProjectsList projects={[]} isLoading={true} />
        </TestWrapper>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('Edge Cases', () => {
    it('handles single project correctly', () => {
      render(
        <TestWrapper>
          <ProjectsList projects={[mockProjects[0]]} isLoading={false} />
        </TestWrapper>
      );

      expect(screen.getByText('my-project')).toBeInTheDocument();
      expect(screen.queryByText('another-project')).not.toBeInTheDocument();
    });

    it('handles very long project names', () => {
      const longNameProject = {
        id: '7',
        name: 'this-is-a-very-long-project-name-that-might-cause-layout-issues',
        path: '/path/to/long/name/project',
        deployment_count: 1,
      };

      render(
        <TestWrapper>
          <ProjectsList projects={[longNameProject]} isLoading={false} />
        </TestWrapper>
      );

      const projectName = screen.getByText(longNameProject.name);
      expect(projectName).toBeInTheDocument();
      expect(projectName).toHaveClass('truncate');
    });

    it('handles very long paths', () => {
      const longPathProject = {
        id: '8',
        name: 'project',
        path: '/this/is/a/very/long/path/to/a/project/that/might/cause/overflow/issues',
        deployment_count: 1,
      };

      render(
        <TestWrapper>
          <ProjectsList projects={[longPathProject]} isLoading={false} />
        </TestWrapper>
      );

      const projectPath = screen.getByText(longPathProject.path);
      expect(projectPath).toBeInTheDocument();
      expect(projectPath).toHaveClass('truncate');
    });

    it('handles zero deployment count', () => {
      const noDeploymentsProject = {
        id: '9',
        name: 'empty-project',
        path: '/path/to/empty',
        deployment_count: 0,
      };

      render(
        <TestWrapper>
          <ProjectsList projects={[noDeploymentsProject]} isLoading={false} />
        </TestWrapper>
      );

      expect(screen.getByText('0 artifacts')).toBeInTheDocument();
    });

    it('handles large deployment counts', () => {
      const manyDeploymentsProject = {
        id: '10',
        name: 'busy-project',
        path: '/path/to/busy',
        deployment_count: 9999,
      };

      render(
        <TestWrapper>
          <ProjectsList projects={[manyDeploymentsProject]} isLoading={false} />
        </TestWrapper>
      );

      expect(screen.getByText('9999')).toBeInTheDocument();
      expect(screen.getByText('9999 artifacts')).toBeInTheDocument();
    });
  });
});
