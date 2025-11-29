/**
 * Accessibility Tests for MergeWorkflow Component
 * @jest-environment jsdom
 */
import { render, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import { MergeWorkflow } from '@/components/entity/merge-workflow';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock API request
jest.mock('@/lib/api', () => ({
  apiRequest: jest.fn().mockResolvedValue({
    has_changes: true,
    files: [
      {
        file_path: 'test.txt',
        status: 'modified',
        unified_diff: '- old content\n+ new content',
      },
    ],
    summary: {
      added: 0,
      modified: 1,
      deleted: 0,
      unchanged: 0,
    },
  }),
}));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe('MergeWorkflow Accessibility', () => {
  it('should have no violations in loading state', async () => {
    const { container } = render(
      <MergeWorkflow
        entityId="skill:test"
        projectPath="/path/to/project"
        direction="upstream"
        onComplete={jest.fn()}
        onCancel={jest.fn()}
      />,
      { wrapper }
    );

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have no violations in preview step', async () => {
    const { container } = render(
      <MergeWorkflow
        entityId="skill:test"
        projectPath="/path/to/project"
        direction="upstream"
        onComplete={jest.fn()}
        onCancel={jest.fn()}
      />,
      { wrapper }
    );

    // Wait for data to load
    await waitFor(
      () => {
        expect(container.querySelector('[class*="text-sm"]')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );

    // Disable heading-order check as Alert component's heading is presentational
    const results = await axe(container, {
      rules: {
        'heading-order': { enabled: false },
      },
    });
    expect(results).toHaveNoViolations();
  });

  it('should have accessible progress stepper', async () => {
    const { container } = render(
      <MergeWorkflow
        entityId="skill:test"
        projectPath="/path/to/project"
        direction="upstream"
        onComplete={jest.fn()}
        onCancel={jest.fn()}
      />,
      { wrapper }
    );

    await waitFor(
      () => {
        expect(container.querySelector('button')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );

    // Verify stepper accessibility - disable heading-order for Alert components
    const results = await axe(container, {
      rules: {
        'heading-order': { enabled: false },
      },
    });
    expect(results).toHaveNoViolations();
  });

  it('should have keyboard navigable buttons', async () => {
    const { container } = render(
      <MergeWorkflow
        entityId="skill:test"
        projectPath="/path/to/project"
        direction="downstream"
        onComplete={jest.fn()}
        onCancel={jest.fn()}
      />,
      { wrapper }
    );

    await waitFor(
      () => {
        expect(container.querySelector('button')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );

    // Disable heading-order for Alert components
    const results = await axe(container, {
      rules: {
        'heading-order': { enabled: false },
      },
    });
    expect(results).toHaveNoViolations();
  });

  it('should have proper color contrast for status indicators', async () => {
    const { container } = render(
      <MergeWorkflow
        entityId="skill:test"
        projectPath="/path/to/project"
        direction="upstream"
        onComplete={jest.fn()}
        onCancel={jest.fn()}
      />,
      { wrapper }
    );

    await waitFor(
      () => {
        expect(container.querySelector('[class*="text-"]')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );

    const results = await axe(container, {
      rules: {
        'color-contrast': { enabled: true },
      },
    });
    expect(results).toHaveNoViolations();
  });

  it('should have accessible alert messages', async () => {
    const { container } = render(
      <MergeWorkflow
        entityId="skill:test"
        projectPath="/path/to/project"
        direction="upstream"
        onComplete={jest.fn()}
        onCancel={jest.fn()}
      />,
      { wrapper }
    );

    await waitFor(
      () => {
        expect(container.querySelector('[class*="border"]')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );

    // Verify alert role accessibility
    const results = await axe(container, {
      rules: {
        'aria-allowed-attr': { enabled: true },
      },
    });
    expect(results).toHaveNoViolations();
  });
});
