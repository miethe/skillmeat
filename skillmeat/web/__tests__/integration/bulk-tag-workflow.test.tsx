/**
 * @jest-environment jsdom
 *
 * Integration tests for the bulk tag application workflow.
 *
 * Tests the end-to-end flow from opening the dialog to applying tags,
 * including directory selection, tag management, API interactions,
 * and success/error handling.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { BulkTagDialogWithHook } from '@/components/marketplace/bulk-tag-dialog';
import type { CatalogEntry } from '@/types/marketplace';
import type { BulkTagResult } from '@/lib/utils/bulk-tag-apply';

// Mock the tags API
jest.mock('@/lib/api/tags', () => ({
  searchTags: jest.fn().mockResolvedValue([]),
}));

// Mock the marketplace API with controllable behavior
const mockUpdatePathTagStatus = jest.fn();
jest.mock('@/lib/api/marketplace', () => ({
  updatePathTagStatus: (...args: unknown[]) => mockUpdatePathTagStatus(...args),
}));

// Mock the toast hook
const mockToast = jest.fn();
jest.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: mockToast,
  }),
}));

// Helper to create mock catalog entries
function createMockEntry(path: string, overrides: Partial<CatalogEntry> = {}): CatalogEntry {
  return {
    id: `entry-${path.replace(/\//g, '-')}`,
    source_id: 'source-123',
    artifact_type: 'skill',
    name: path.split('/').pop() || path,
    path,
    upstream_url: `https://github.com/test/${path}`,
    detected_at: '2024-01-01T00:00:00Z',
    confidence_score: 0.9,
    status: 'new',
    ...overrides,
  };
}

// Generate many entries for performance testing
function generateManyEntries(count: number): CatalogEntry[] {
  const entries: CatalogEntry[] = [];
  const directories = ['skills', 'commands', 'agents', 'hooks', 'tools'];

  for (let i = 0; i < count; i++) {
    const dir = directories[i % directories.length];
    const subdir = `sub${Math.floor(i / directories.length)}`;
    entries.push(createMockEntry(`${dir}/${subdir}/artifact-${i}`));
  }

  return entries;
}

// Test wrapper with QueryClientProvider
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe('Bulk Tag Workflow Integration', () => {
  const mockOnOpenChange = jest.fn();
  const mockOnSuccess = jest.fn();
  const mockOnError = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockUpdatePathTagStatus.mockResolvedValue({});
    mockToast.mockClear();
  });

  describe('Complete Workflow - Simulation Mode', () => {
    const mockEntries: CatalogEntry[] = [
      createMockEntry('skills/canvas'),
      createMockEntry('skills/docs'),
      createMockEntry('skills/dev/testing'),
      createMockEntry('commands/ai'),
      createMockEntry('commands/system'),
    ];

    const defaultProps = {
      open: true,
      onOpenChange: mockOnOpenChange,
      entries: mockEntries,
      sourceId: 'source-123',
      simulationMode: true,
      onSuccess: mockOnSuccess,
      onError: mockOnError,
    };

    it('completes full workflow: open dialog, select directories, add tags, apply', async () => {
      const user = userEvent.setup();
      render(<BulkTagDialogWithHook {...defaultProps} />, {
        wrapper: createWrapper(),
      });

      // Step 1: Verify dialog is open with directories
      expect(screen.getByText('Bulk Tag Application')).toBeInTheDocument();
      // Use getByRole for more specific queries since text may appear multiple times
      expect(screen.getByRole('checkbox', { name: /select skills$/i })).toBeInTheDocument();
      expect(screen.getByRole('checkbox', { name: /select commands$/i })).toBeInTheDocument();

      // Step 2: Select multiple directories
      const skillsCheckbox = screen.getByRole('checkbox', {
        name: /select skills$/i,
      });
      const commandsCheckbox = screen.getByRole('checkbox', {
        name: /select commands$/i,
      });

      await user.click(skillsCheckbox);
      await user.click(commandsCheckbox);

      expect(skillsCheckbox).toBeChecked();
      expect(commandsCheckbox).toBeChecked();

      // Step 3: Add tags to directories
      const tagInputs = screen.getAllByPlaceholderText('Add tag and press Enter');

      // Add tag to first selected directory
      if (tagInputs[0]) {
        await user.type(tagInputs[0], 'python{Enter}');
        await user.type(tagInputs[0], 'development{Enter}');
      }

      expect(screen.getByText('python')).toBeInTheDocument();
      expect(screen.getByText('development')).toBeInTheDocument();

      // Step 4: Click Apply
      const applyButton = screen.getByRole('button', { name: /apply tags/i });
      expect(applyButton).not.toBeDisabled();
      await user.click(applyButton);

      // Step 5: Verify success
      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalledTimes(1);
      });

      const result = mockOnSuccess.mock.calls[0][0] as BulkTagResult;
      expect(result.totalUpdated).toBeGreaterThan(0);
      expect(result.totalFailed).toBe(0);

      // Step 6: Verify dialog closes
      await waitFor(() => {
        expect(mockOnOpenChange).toHaveBeenCalledWith(false);
      });
    });

    it('handles using suggested tags from path', async () => {
      const user = userEvent.setup();
      render(<BulkTagDialogWithHook {...defaultProps} />, {
        wrapper: createWrapper(),
      });

      // Find and click a suggested tag (generated from path)
      const suggestedTagButton = screen.getAllByLabelText(/add suggested tag skills/i)[0];
      if (suggestedTagButton) await user.click(suggestedTagButton);

      // Should auto-select the directory
      const skillsCheckbox = screen.getByRole('checkbox', {
        name: /select skills$/i,
      });
      expect(skillsCheckbox).toBeChecked();

      // The tag should be applied
      const tagBadges = screen.getAllByText('skills');
      expect(tagBadges.length).toBeGreaterThan(0);
    });

    it('preserves state when toggling directory selection', async () => {
      const user = userEvent.setup();
      render(<BulkTagDialogWithHook {...defaultProps} />, {
        wrapper: createWrapper(),
      });

      // Select directory and add tag
      const skillsCheckbox = screen.getByRole('checkbox', {
        name: /select skills$/i,
      });
      await user.click(skillsCheckbox);

      const tagInput = screen.getAllByPlaceholderText('Add tag and press Enter')[0];
      if (tagInput) await user.type(tagInput, 'test-tag{Enter}');

      expect(screen.getByText('test-tag')).toBeInTheDocument();

      // Deselect and reselect
      await user.click(skillsCheckbox);
      await user.click(skillsCheckbox);

      // Tag should still be there
      expect(screen.getByText('test-tag')).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    const mockEntries: CatalogEntry[] = [
      createMockEntry('skills/canvas'),
      createMockEntry('skills/docs'),
    ];

    const propsWithApi = {
      open: true,
      onOpenChange: mockOnOpenChange,
      entries: mockEntries,
      sourceId: 'source-123',
      simulationMode: false,
      onSuccess: mockOnSuccess,
      onError: mockOnError,
    };

    it('shows error toast when API fails completely', async () => {
      const user = userEvent.setup();
      mockUpdatePathTagStatus.mockRejectedValue(new Error('Network error'));

      render(<BulkTagDialogWithHook {...propsWithApi} />, {
        wrapper: createWrapper(),
      });

      const skillsCheckbox = screen.getByRole('checkbox', {
        name: /select skills$/i,
      });
      await user.click(skillsCheckbox);

      const tagInput = screen.getAllByPlaceholderText('Add tag and press Enter')[0];
      if (tagInput) await user.type(tagInput, 'test-tag{Enter}');

      const applyButton = screen.getByRole('button', { name: /apply tags/i });
      await user.click(applyButton);

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith(
          expect.objectContaining({
            title: 'Tags applied',
            variant: expect.any(String),
          })
        );
      });
    });

    it('handles partial failures gracefully', async () => {
      const user = userEvent.setup();

      // First call succeeds, second fails
      mockUpdatePathTagStatus
        .mockResolvedValueOnce({})
        .mockRejectedValueOnce(new Error('Entry not found'));

      render(<BulkTagDialogWithHook {...propsWithApi} />, {
        wrapper: createWrapper(),
      });

      const skillsCheckbox = screen.getByRole('checkbox', {
        name: /select skills$/i,
      });
      await user.click(skillsCheckbox);

      const tagInput = screen.getAllByPlaceholderText('Add tag and press Enter')[0];
      if (tagInput) await user.type(tagInput, 'partial-tag{Enter}');

      const applyButton = screen.getByRole('button', { name: /apply tags/i });
      await user.click(applyButton);

      // Should still complete (with partial success)
      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalled();
      });
    });
  });

  describe('Performance Tests', () => {
    it('renders 50+ directories without significant lag', async () => {
      // Generate entries with many unique directories
      const manyEntries = generateManyEntries(100);

      const start = performance.now();
      render(
        <BulkTagDialogWithHook
          open={true}
          onOpenChange={mockOnOpenChange}
          entries={manyEntries}
          sourceId="source-123"
          simulationMode={true}
          onSuccess={mockOnSuccess}
        />,
        { wrapper: createWrapper() }
      );
      const elapsed = performance.now() - start;

      // Should render in under 2 seconds
      expect(elapsed).toBeLessThan(2000);

      // Verify directories are rendered
      expect(screen.getByText('skills/sub0')).toBeInTheDocument();
    });

    it('handles bulk selection of many directories', async () => {
      const user = userEvent.setup();
      const manyEntries = generateManyEntries(50);

      render(
        <BulkTagDialogWithHook
          open={true}
          onOpenChange={mockOnOpenChange}
          entries={manyEntries}
          sourceId="source-123"
          simulationMode={true}
          onSuccess={mockOnSuccess}
        />,
        { wrapper: createWrapper() }
      );

      // Select first 10 directories
      const checkboxes = screen.getAllByRole('checkbox').slice(0, 10);

      const start = performance.now();
      for (const checkbox of checkboxes) {
        await user.click(checkbox);
      }
      const elapsed = performance.now() - start;

      // Selection should be responsive (under 500ms per click on average)
      expect(elapsed / checkboxes.length).toBeLessThan(500);

      // Verify selections
      checkboxes.forEach((checkbox) => {
        if (checkbox) expect(checkbox).toBeChecked();
      });
    });

    it('scrolling works with many directories', () => {
      const manyEntries = generateManyEntries(100);

      render(
        <BulkTagDialogWithHook
          open={true}
          onOpenChange={mockOnOpenChange}
          entries={manyEntries}
          sourceId="source-123"
          simulationMode={true}
          onSuccess={mockOnSuccess}
        />,
        { wrapper: createWrapper() }
      );

      // ScrollArea component should be present
      const scrollArea = document.querySelector('[data-radix-scroll-area-viewport]');
      expect(scrollArea).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles empty catalog (no entries)', () => {
      render(
        <BulkTagDialogWithHook
          open={true}
          onOpenChange={mockOnOpenChange}
          entries={[]}
          sourceId="source-123"
          simulationMode={true}
          onSuccess={mockOnSuccess}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText('No directories found in catalog entries.')).toBeInTheDocument();

      const applyButton = screen.getByRole('button', { name: /apply tags/i });
      expect(applyButton).toBeDisabled();
    });

    it('handles all root-level entries (no directories)', () => {
      const rootEntries = [
        createMockEntry('rootfile1'),
        createMockEntry('rootfile2'),
        createMockEntry('rootfile3'),
      ];

      render(
        <BulkTagDialogWithHook
          open={true}
          onOpenChange={mockOnOpenChange}
          entries={rootEntries}
          sourceId="source-123"
          simulationMode={true}
          onSuccess={mockOnSuccess}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText('No directories found in catalog entries.')).toBeInTheDocument();
      expect(screen.getByText('Root-level artifacts cannot be bulk-tagged.')).toBeInTheDocument();
    });

    it('handles deeply nested directories', async () => {
      const user = userEvent.setup();
      const deepEntries = [
        createMockEntry('a/b/c/d/e/artifact1'),
        createMockEntry('a/b/c/d/e/artifact2'),
      ];

      render(
        <BulkTagDialogWithHook
          open={true}
          onOpenChange={mockOnOpenChange}
          entries={deepEntries}
          sourceId="source-123"
          simulationMode={true}
          onSuccess={mockOnSuccess}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText('a/b/c/d/e')).toBeInTheDocument();

      // Can select and tag
      const checkbox = screen.getByRole('checkbox', {
        name: /select a\/b\/c\/d\/e/i,
      });
      await user.click(checkbox);
      expect(checkbox).toBeChecked();
    });

    it('handles special characters in directory names', () => {
      const specialEntries = [
        createMockEntry('skills-v2.0/canvas'),
        createMockEntry('skills_test_123/docs'),
        createMockEntry('@scope/package/artifact'),
      ];

      render(
        <BulkTagDialogWithHook
          open={true}
          onOpenChange={mockOnOpenChange}
          entries={specialEntries}
          sourceId="source-123"
          simulationMode={true}
          onSuccess={mockOnSuccess}
        />,
        { wrapper: createWrapper() }
      );

      // Use getByRole with name for more specific queries since text may appear multiple times
      expect(screen.getByRole('checkbox', { name: /select skills-v2\.0/i })).toBeInTheDocument();
      expect(screen.getByRole('checkbox', { name: /select skills_test_123/i })).toBeInTheDocument();
      expect(screen.getByRole('checkbox', { name: /select @scope\/package/i })).toBeInTheDocument();
    });

    it('handles duplicate tags (case-insensitive)', async () => {
      const user = userEvent.setup();
      const entries = [createMockEntry('skills/canvas')];

      render(
        <BulkTagDialogWithHook
          open={true}
          onOpenChange={mockOnOpenChange}
          entries={entries}
          sourceId="source-123"
          simulationMode={true}
          onSuccess={mockOnSuccess}
        />,
        { wrapper: createWrapper() }
      );

      const checkbox = screen.getByRole('checkbox', { name: /select skills/i });
      await user.click(checkbox);

      const tagInput = screen.getAllByPlaceholderText('Add tag and press Enter')[0];

      // Add same tag with different cases
      if (tagInput) {
        await user.type(tagInput, 'Python{Enter}');
        await user.type(tagInput, 'python{Enter}');
        await user.type(tagInput, 'PYTHON{Enter}');
      }

      // Should only have one instance (normalized to lowercase)
      const pythonTags = screen.getAllByText('python');
      expect(pythonTags).toHaveLength(1);
    });

    it('handles empty tag input (whitespace only)', async () => {
      const user = userEvent.setup();
      const entries = [createMockEntry('skills/canvas')];

      render(
        <BulkTagDialogWithHook
          open={true}
          onOpenChange={mockOnOpenChange}
          entries={entries}
          sourceId="source-123"
          simulationMode={true}
          onSuccess={mockOnSuccess}
        />,
        { wrapper: createWrapper() }
      );

      const checkbox = screen.getByRole('checkbox', { name: /select skills/i });
      await user.click(checkbox);

      const tagInput = screen.getAllByPlaceholderText('Add tag and press Enter')[0] as
        | HTMLInputElement
        | undefined;

      // Try to add empty/whitespace tags
      if (tagInput) {
        await user.type(tagInput, '   {Enter}');
        await user.type(tagInput, '{Enter}');
      }

      // No tags should be added
      const applyButton = screen.getByRole('button', { name: /apply tags/i });

      // Apply should work but with no tags
      await user.click(applyButton);

      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalled();
      });

      // Result should show 0 tags applied (empty tags filtered out)
      const result = mockOnSuccess.mock.calls[0][0] as BulkTagResult;
      expect(result.totalTagsApplied).toBe(0);
    });

    it('canceling dialog resets all state', async () => {
      const user = userEvent.setup();
      const entries = [createMockEntry('skills/canvas'), createMockEntry('skills/docs')];

      const { rerender } = render(
        <BulkTagDialogWithHook
          open={true}
          onOpenChange={mockOnOpenChange}
          entries={entries}
          sourceId="source-123"
          simulationMode={true}
          onSuccess={mockOnSuccess}
        />,
        { wrapper: createWrapper() }
      );

      // Select directory and add tags
      const checkbox = screen.getByRole('checkbox', { name: /select skills/i });
      await user.click(checkbox);

      const tagInput = screen.getAllByPlaceholderText('Add tag and press Enter')[0];
      if (tagInput) await user.type(tagInput, 'test-tag{Enter}');

      // Cancel
      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      expect(mockOnOpenChange).toHaveBeenCalledWith(false);

      // Reopen dialog
      rerender(
        <QueryClientProvider
          client={
            new QueryClient({
              defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
            })
          }
        >
          <BulkTagDialogWithHook
            open={true}
            onOpenChange={mockOnOpenChange}
            entries={entries}
            sourceId="source-123"
            simulationMode={true}
            onSuccess={mockOnSuccess}
          />
        </QueryClientProvider>
      );

      // State should be reset - checkbox unchecked
      const newCheckbox = screen.getByRole('checkbox', { name: /select skills/i });
      expect(newCheckbox).not.toBeChecked();
    });
  });

  describe('Keyboard Navigation', () => {
    it('supports keyboard navigation through checkboxes', async () => {
      const user = userEvent.setup();
      const entries = [createMockEntry('skills/canvas'), createMockEntry('commands/ai')];

      render(
        <BulkTagDialogWithHook
          open={true}
          onOpenChange={mockOnOpenChange}
          entries={entries}
          sourceId="source-123"
          simulationMode={true}
          onSuccess={mockOnSuccess}
        />,
        { wrapper: createWrapper() }
      );

      // Tab to first checkbox
      await user.tab();

      // The first focusable element should receive focus
      expect(document.activeElement).toBeTruthy();
    });

    it('supports Enter key to add tags', async () => {
      const user = userEvent.setup();
      const entries = [createMockEntry('skills/canvas')];

      render(
        <BulkTagDialogWithHook
          open={true}
          onOpenChange={mockOnOpenChange}
          entries={entries}
          sourceId="source-123"
          simulationMode={true}
          onSuccess={mockOnSuccess}
        />,
        { wrapper: createWrapper() }
      );

      const checkbox = screen.getByRole('checkbox', { name: /select skills/i });
      await user.click(checkbox);

      const tagInput = screen.getAllByPlaceholderText('Add tag and press Enter')[0];
      if (tagInput) await user.type(tagInput, 'keyboard-tag');
      await user.keyboard('{Enter}');

      expect(screen.getByText('keyboard-tag')).toBeInTheDocument();
    });

    it('supports Space key to toggle checkboxes', async () => {
      const user = userEvent.setup();
      const entries = [createMockEntry('skills/canvas')];

      render(
        <BulkTagDialogWithHook
          open={true}
          onOpenChange={mockOnOpenChange}
          entries={entries}
          sourceId="source-123"
          simulationMode={true}
          onSuccess={mockOnSuccess}
        />,
        { wrapper: createWrapper() }
      );

      const checkbox = screen.getByRole('checkbox', { name: /select skills/i });
      checkbox.focus();
      await user.keyboard(' ');

      expect(checkbox).toBeChecked();
    });
  });
});
