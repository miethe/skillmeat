/**
 * @jest-environment jsdom
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DirectoryTagInput } from '@/components/marketplace/directory-tag-input';

// Mock the tags API
jest.mock('@/lib/api/tags', () => ({
  searchTags: jest.fn(),
}));

import { searchTags } from '@/lib/api/tags';

const mockSearchTags = searchTags as jest.MockedFunction<typeof searchTags>;

// Wrapper with QueryClientProvider
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
      },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('DirectoryTagInput', () => {
  const mockOnAddTag = jest.fn();
  const mockOnRemoveTag = jest.fn();
  const mockOnAddSuggestedTag = jest.fn();

  const defaultProps = {
    directoryPath: 'skills/canvas-design',
    currentTags: [] as string[],
    suggestedTags: ['skills', 'canvas-design'],
    onAddTag: mockOnAddTag,
    onRemoveTag: mockOnRemoveTag,
    onAddSuggestedTag: mockOnAddSuggestedTag,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockSearchTags.mockResolvedValue([]);
  });

  describe('Basic Rendering', () => {
    it('renders input field', () => {
      render(<DirectoryTagInput {...defaultProps} />, { wrapper: createWrapper() });

      expect(screen.getByPlaceholderText('Add tag and press Enter')).toBeInTheDocument();
    });

    it('renders add button', () => {
      render(<DirectoryTagInput {...defaultProps} />, { wrapper: createWrapper() });

      expect(screen.getByRole('button', { name: /add tag to/i })).toBeInTheDocument();
    });

    it('renders current tags', () => {
      render(<DirectoryTagInput {...defaultProps} currentTags={['python', 'typescript']} />, {
        wrapper: createWrapper(),
      });

      expect(screen.getByText('python')).toBeInTheDocument();
      expect(screen.getByText('typescript')).toBeInTheDocument();
    });

    it('renders suggested tags', () => {
      render(<DirectoryTagInput {...defaultProps} />, { wrapper: createWrapper() });

      expect(screen.getByText('skills')).toBeInTheDocument();
      expect(screen.getByText('canvas-design')).toBeInTheDocument();
    });

    it('hides suggested tags that are already applied', () => {
      render(
        <DirectoryTagInput
          {...defaultProps}
          currentTags={['skills']}
          suggestedTags={['skills', 'canvas-design']}
        />,
        { wrapper: createWrapper() }
      );

      // skills should not appear in suggestions since it's already applied
      const suggestedList = screen.getByRole('list', {
        name: /suggested tags for/i,
      });
      expect(within(suggestedList).queryByText('skills')).not.toBeInTheDocument();
      expect(within(suggestedList).getByText('canvas-design')).toBeInTheDocument();
    });
  });

  describe('Tag Input', () => {
    it('adds tag via Enter key', async () => {
      const user = userEvent.setup();
      render(<DirectoryTagInput {...defaultProps} />, { wrapper: createWrapper() });

      const input = screen.getByPlaceholderText('Add tag and press Enter');
      await user.type(input, 'new-tag{Enter}');

      expect(mockOnAddTag).toHaveBeenCalledWith('new-tag');
    });

    it('adds tag via button click', async () => {
      const user = userEvent.setup();
      render(<DirectoryTagInput {...defaultProps} />, { wrapper: createWrapper() });

      const input = screen.getByPlaceholderText('Add tag and press Enter');
      await user.type(input, 'button-tag');

      const addButton = screen.getByRole('button', { name: /add tag to/i });
      await user.click(addButton);

      expect(mockOnAddTag).toHaveBeenCalledWith('button-tag');
    });

    it('clears input after adding tag', async () => {
      const user = userEvent.setup();
      render(<DirectoryTagInput {...defaultProps} />, { wrapper: createWrapper() });

      const input = screen.getByPlaceholderText('Add tag and press Enter') as HTMLInputElement;
      await user.type(input, 'test-tag{Enter}');

      expect(input.value).toBe('');
    });

    it('disables add button when input is empty', () => {
      render(<DirectoryTagInput {...defaultProps} />, { wrapper: createWrapper() });

      const addButton = screen.getByRole('button', { name: /add tag to/i });
      expect(addButton).toBeDisabled();
    });

    it('does not add empty tags', async () => {
      const user = userEvent.setup();
      render(<DirectoryTagInput {...defaultProps} />, { wrapper: createWrapper() });

      const input = screen.getByPlaceholderText('Add tag and press Enter');
      await user.type(input, '   {Enter}');

      expect(mockOnAddTag).not.toHaveBeenCalled();
    });
  });

  describe('Autocomplete API Integration', () => {
    it('calls search API when typing', async () => {
      const user = userEvent.setup();
      mockSearchTags.mockResolvedValue([]);

      render(<DirectoryTagInput {...defaultProps} />, { wrapper: createWrapper() });

      const input = screen.getByPlaceholderText('Add tag and press Enter');
      await user.type(input, 'py');

      await waitFor(() => {
        expect(mockSearchTags).toHaveBeenCalled();
      });
    });

    it('debounces search API calls', async () => {
      const user = userEvent.setup();
      mockSearchTags.mockResolvedValue([]);

      render(<DirectoryTagInput {...defaultProps} />, { wrapper: createWrapper() });

      const input = screen.getByPlaceholderText('Add tag and press Enter');

      // Type quickly
      await user.type(input, 'abc');

      // Wait for debounce to settle
      await waitFor(
        () => {
          expect(mockSearchTags).toHaveBeenCalled();
        },
        { timeout: 300 }
      );

      // Should have called with the final value
      const calls = mockSearchTags.mock.calls;
      expect(calls.length).toBeGreaterThan(0);
      const lastCall = calls[calls.length - 1];
      expect(lastCall?.[0]).toBe('abc');
    });
  });

  describe('Tag Removal', () => {
    it('calls onRemoveTag when clicking tag badge', async () => {
      const user = userEvent.setup();
      render(<DirectoryTagInput {...defaultProps} currentTags={['python', 'typescript']} />, {
        wrapper: createWrapper(),
      });

      const pythonBadge = screen.getByLabelText(/remove tag python/i);
      await user.click(pythonBadge);

      expect(mockOnRemoveTag).toHaveBeenCalledWith('python');
    });
  });

  describe('Suggested Tags', () => {
    it('calls onAddSuggestedTag when clicking suggested tag', async () => {
      const user = userEvent.setup();
      render(<DirectoryTagInput {...defaultProps} />, { wrapper: createWrapper() });

      const suggestedTag = screen.getByLabelText(/add suggested tag skills/i);
      await user.click(suggestedTag);

      expect(mockOnAddSuggestedTag).toHaveBeenCalledWith('skills');
    });

    it('hides suggested tags section when all are applied', () => {
      render(
        <DirectoryTagInput
          {...defaultProps}
          currentTags={['skills', 'canvas-design']}
          suggestedTags={['skills', 'canvas-design']}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.queryByRole('list', { name: /suggested tags for/i })).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has accessible input label', () => {
      render(<DirectoryTagInput {...defaultProps} />, { wrapper: createWrapper() });

      expect(screen.getByLabelText(/add tag for skills\/canvas-design/i)).toBeInTheDocument();
    });

    it('has accessible tag lists', () => {
      render(<DirectoryTagInput {...defaultProps} currentTags={['python']} />, {
        wrapper: createWrapper(),
      });

      expect(screen.getByRole('list', { name: /applied tags for/i })).toBeInTheDocument();
      expect(screen.getByRole('list', { name: /suggested tags for/i })).toBeInTheDocument();
    });

    it('has ARIA attributes for autocomplete', () => {
      render(<DirectoryTagInput {...defaultProps} />, { wrapper: createWrapper() });

      const input = screen.getByPlaceholderText('Add tag and press Enter');
      expect(input).toHaveAttribute('aria-autocomplete', 'list');
      expect(input).toHaveAttribute('aria-expanded');
    });
  });
});
