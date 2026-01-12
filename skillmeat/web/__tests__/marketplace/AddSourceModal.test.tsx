/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AddSourceModal } from '@/components/marketplace/add-source-modal';
import { useCreateSource } from '@/hooks';

// Mock the hooks
jest.mock('@/hooks', () => ({
  useCreateSource: jest.fn(),
  useInferUrl: jest.fn(() => ({
    mutateAsync: jest.fn(),
    isPending: false,
    isSuccess: false,
    data: null,
    reset: jest.fn(),
  })),
  useToast: () => ({
    toast: jest.fn(),
  }),
}));

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

const renderWithClient = (ui: React.ReactElement) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
};

describe('AddSourceModal', () => {
  const mockOnOpenChange = jest.fn();
  const mockOnSuccess = jest.fn();
  const mockMutateAsync = jest.fn();
  const mockInferUrlMutateAsync = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    (useCreateSource as jest.Mock).mockReturnValue({
      mutateAsync: mockMutateAsync,
      isPending: false,
    });

    // Mock useInferUrl hook
    const useInferUrl = require('@/hooks').useInferUrl;
    (useInferUrl as jest.Mock).mockReturnValue({
      mutateAsync: mockInferUrlMutateAsync,
      isPending: false,
      isSuccess: false,
      data: null,
      reset: jest.fn(),
    });
  });

  describe('Rendering', () => {
    it('renders modal when open', () => {
      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      expect(screen.getByText('Add GitHub Source')).toBeInTheDocument();
      expect(
        screen.getByText(/Add a GitHub repository to scan for Claude Code artifacts/)
      ).toBeInTheDocument();
    });

    it('does not render when closed', () => {
      renderWithClient(
        <AddSourceModal
          open={false}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      expect(screen.queryByText('Add GitHub Source')).not.toBeInTheDocument();
    });

    it('renders all form fields', () => {
      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      expect(screen.getByLabelText('Repository URL')).toBeInTheDocument();
      expect(screen.getByLabelText('Branch / Tag')).toBeInTheDocument();
      expect(screen.getByLabelText('Root Directory (optional)')).toBeInTheDocument();
      // Trust Level field exists but Select component doesn't use htmlFor
      expect(screen.getByText('Trust Level')).toBeInTheDocument();
    });

    it('renders action buttons', () => {
      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /add source/i })).toBeInTheDocument();
    });
  });

  describe('URL Validation', () => {
    it('shows validation error for invalid URL', async () => {
      const user = userEvent.setup();
      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      const urlInput = screen.getByLabelText('Repository URL');
      await user.type(urlInput, 'not-a-valid-url');

      await waitFor(() => {
        expect(
          screen.getByText(/Enter a valid GitHub URL/)
        ).toBeInTheDocument();
      });
    });

    it('accepts valid GitHub URL', async () => {
      const user = userEvent.setup();
      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      const urlInput = screen.getByLabelText('Repository URL');
      await user.type(urlInput, 'https://github.com/owner/repo');

      await waitFor(() => {
        expect(
          screen.queryByText(/Enter a valid GitHub URL/)
        ).not.toBeInTheDocument();
      });
    });

    it('disables submit button for invalid URL', async () => {
      const user = userEvent.setup();
      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      const submitButton = screen.getByRole('button', { name: /add source/i });
      expect(submitButton).toBeDisabled();

      const urlInput = screen.getByLabelText('Repository URL');
      await user.type(urlInput, 'invalid-url');

      expect(submitButton).toBeDisabled();
    });

    it('enables submit button for valid URL', async () => {
      const user = userEvent.setup();
      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      const urlInput = screen.getByLabelText('Repository URL');
      await user.type(urlInput, 'https://github.com/anthropics/anthropic-cookbook');

      const submitButton = screen.getByRole('button', { name: /add source/i });
      await waitFor(() => {
        expect(submitButton).not.toBeDisabled();
      });
    });
  });

  describe('Form Interactions', () => {
    it('updates repository URL field', async () => {
      const user = userEvent.setup();
      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      const urlInput = screen.getByLabelText('Repository URL') as HTMLInputElement;
      await user.type(urlInput, 'https://github.com/owner/repo');

      expect(urlInput.value).toBe('https://github.com/owner/repo');
    });

    it('updates branch/tag field', async () => {
      const user = userEvent.setup();
      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      const refInput = screen.getByLabelText('Branch / Tag') as HTMLInputElement;
      await user.clear(refInput);
      await user.type(refInput, 'develop');

      expect(refInput.value).toBe('develop');
    });

    it('updates root directory field', async () => {
      const user = userEvent.setup();
      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      const rootInput = screen.getByLabelText('Root Directory (optional)') as HTMLInputElement;
      await user.type(rootInput, 'skills/');

      expect(rootInput.value).toBe('skills/');
    });

    it('updates trust level selector', async () => {
      const user = userEvent.setup();
      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      // Find the select trigger button
      const trustLevelText = screen.getByText('Trust Level');
      const selectTrigger = trustLevelText.closest('div')?.querySelector('button');
      expect(selectTrigger).toBeInTheDocument();

      if (selectTrigger) {
        await user.click(selectTrigger);

        const verifiedOption = await screen.findByRole('option', { name: /verified/i });
        await user.click(verifiedOption);

        // Select should show the new value
        expect(screen.getByText('Verified')).toBeInTheDocument();
      }
    });
  });

  describe('Form Submission', () => {
    it('submits form with valid data', async () => {
      const user = userEvent.setup();
      mockMutateAsync.mockResolvedValue({
        id: 'source-123',
        owner: 'owner',
        repo_name: 'repo',
      });

      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      const urlInput = screen.getByLabelText('Repository URL');
      await user.type(urlInput, 'https://github.com/owner/repo');

      const submitButton = screen.getByRole('button', { name: /add source/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledWith({
          repo_url: 'https://github.com/owner/repo',
          ref: 'main',
          root_hint: undefined,
          trust_level: 'basic',
        });
      });
    });

    it('submits form with all fields filled', async () => {
      const user = userEvent.setup();
      mockMutateAsync.mockResolvedValue({
        id: 'source-123',
        owner: 'anthropics',
        repo_name: 'skills',
      });

      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      const urlInput = screen.getByLabelText('Repository URL');
      await user.type(urlInput, 'https://github.com/anthropics/skills');

      const refInput = screen.getByLabelText('Branch / Tag');
      await user.clear(refInput);
      await user.type(refInput, 'v1.0.0');

      const rootInput = screen.getByLabelText('Root Directory (optional)');
      await user.type(rootInput, 'src/');

      // Update trust level
      const trustLevelText = screen.getByText('Trust Level');
      const selectTrigger = trustLevelText.closest('div')?.querySelector('button');
      if (selectTrigger) {
        await user.click(selectTrigger);
        const verifiedOption = await screen.findByRole('option', { name: /verified/i });
        await user.click(verifiedOption);
      }

      const submitButton = screen.getByRole('button', { name: /add source/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledWith({
          repo_url: 'https://github.com/anthropics/skills',
          ref: 'v1.0.0',
          root_hint: 'src/',
          trust_level: 'verified',
        });
      });
    });

    it('calls onSuccess callback after successful submission', async () => {
      const user = userEvent.setup();
      mockMutateAsync.mockResolvedValue({
        id: 'source-123',
        owner: 'owner',
        repo_name: 'repo',
      });

      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      const urlInput = screen.getByLabelText('Repository URL');
      await user.type(urlInput, 'https://github.com/owner/repo');

      const submitButton = screen.getByRole('button', { name: /add source/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalled();
      });
    });

    it('resets form after successful submission', async () => {
      const user = userEvent.setup();
      mockMutateAsync.mockResolvedValue({
        id: 'source-123',
        owner: 'owner',
        repo_name: 'repo',
      });

      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      const urlInput = screen.getByLabelText('Repository URL') as HTMLInputElement;
      await user.type(urlInput, 'https://github.com/owner/repo');

      const submitButton = screen.getByRole('button', { name: /add source/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(urlInput.value).toBe('');
      });
    });

    it('does not submit on Enter key press (form not ready)', async () => {
      const user = userEvent.setup();
      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      const urlInput = screen.getByLabelText('Repository URL');
      await user.type(urlInput, 'invalid-url{Enter}');

      expect(mockMutateAsync).not.toHaveBeenCalled();
    });
  });

  describe('Loading State', () => {
    it('shows loading state during submission', () => {
      (useCreateSource as jest.Mock).mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: true,
      });

      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      expect(screen.getByText(/adding.../i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /adding.../i })).toBeDisabled();
    });

    it('disables submit button during submission', () => {
      (useCreateSource as jest.Mock).mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: true,
      });

      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      const submitButton = screen.getByRole('button', { name: /adding.../i });
      expect(submitButton).toBeDisabled();
    });
  });

  describe('Error Handling', () => {
    it('handles submission error gracefully', async () => {
      const user = userEvent.setup();
      mockMutateAsync.mockRejectedValue(new Error('Network error'));

      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      const urlInput = screen.getByLabelText('Repository URL');
      await user.type(urlInput, 'https://github.com/owner/repo');

      const submitButton = screen.getByRole('button', { name: /add source/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalled();
      });

      // Modal should remain open on error
      expect(screen.getByText('Add GitHub Source')).toBeInTheDocument();
    });
  });

  describe('Cancel Action', () => {
    it('calls onOpenChange when cancel is clicked', async () => {
      const user = userEvent.setup();
      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });
  });

  describe('Accessibility', () => {
    it('has accessible labels for all inputs', () => {
      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      expect(screen.getByLabelText('Repository URL')).toBeInTheDocument();
      expect(screen.getByLabelText('Branch / Tag')).toBeInTheDocument();
      expect(screen.getByLabelText('Root Directory (optional)')).toBeInTheDocument();
      // Trust Level uses Label component that doesn't associate via htmlFor
      expect(screen.getByText('Trust Level')).toBeInTheDocument();
    });

    it('has proper button roles', () => {
      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      expect(screen.getByRole('button', { name: /cancel/i })).toHaveAttribute('type', 'button');
      expect(screen.getByRole('button', { name: /add source/i })).toHaveAttribute('type', 'submit');
    });

    it('provides helper text for optional fields', () => {
      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      expect(screen.getByText(/Subdirectory to start scanning from/)).toBeInTheDocument();
    });
  });

  describe('Default Values', () => {
    it('has default branch value of "main"', () => {
      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      const refInput = screen.getByLabelText('Branch / Tag') as HTMLInputElement;
      expect(refInput.value).toBe('main');
    });

    it('has default trust level displayed', () => {
      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      // Check that "Basic" is the selected option shown in the trigger
      expect(screen.getByText('Basic')).toBeInTheDocument();
    });

    it('has empty repository URL by default', () => {
      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      const urlInput = screen.getByLabelText('Repository URL') as HTMLInputElement;
      expect(urlInput.value).toBe('');
    });

    it('has empty root hint by default', () => {
      renderWithClient(
        <AddSourceModal
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      const rootInput = screen.getByLabelText('Root Directory (optional)') as HTMLInputElement;
      expect(rootInput.value).toBe('');
    });
  });
});
