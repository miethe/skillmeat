/**
 * @jest-environment jsdom
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { Artifact } from '@/types/artifact';

// Mock the useConflictCheck hook BEFORE importing the component
jest.mock('@/hooks', () => ({
  useConflictCheck: jest.fn(),
}));

// Mock the DiffViewer component
jest.mock('@/components/entity/diff-viewer', () => ({
  DiffViewer: ({ files, leftLabel, rightLabel }: any) => (
    <div data-testid="diff-viewer">
      <div>{leftLabel}</div>
      <div>{rightLabel}</div>
      <div>{files.length} files</div>
    </div>
  ),
}));

// Mock the Skeleton component
jest.mock('@/components/ui/skeleton', () => ({
  Skeleton: ({ className }: any) => <div data-testid="skeleton" className={className} />,
}));

// Now import the component after mocks are set up
import { SyncConfirmationDialog } from '@/components/sync-status/sync-confirmation-dialog';
import { useConflictCheck } from '@/hooks';
import type { FileDiff } from '@/sdk/models/FileDiff';
import type { ArtifactDiffResponse } from '@/sdk/models/ArtifactDiffResponse';

const mockUseConflictCheck = useConflictCheck as jest.MockedFunction<typeof useConflictCheck>;

// Helper factories for creating valid mock data
const createMockFileDiff = (overrides?: Partial<FileDiff>): FileDiff => ({
  file_path: 'test.txt',
  status: 'modified',
  collection_hash: null,
  project_hash: null,
  unified_diff: null,
  ...overrides,
});

const createMockArtifactDiffResponse = (
  overrides?: Partial<ArtifactDiffResponse>
): ArtifactDiffResponse => ({
  artifact_id: 'test-artifact-1',
  artifact_name: 'test-skill',
  artifact_type: 'skill',
  collection_name: 'default',
  project_path: '/path/to/project',
  has_changes: false,
  files: [],
  summary: {},
  ...overrides,
});

describe('SyncConfirmationDialog', () => {
  const mockArtifact: Artifact = {
    id: 'test-artifact-1',
    name: 'test-skill',
    type: 'skill',
    scope: 'user',
    syncStatus: 'synced',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  };

  const mockOnOpenChange = jest.fn();
  const mockOnOverwrite = jest.fn();
  const mockOnMerge = jest.fn();
  const mockOnCancel = jest.fn();

  const defaultProps = {
    artifact: mockArtifact,
    projectPath: '/path/to/project',
    open: true,
    onOpenChange: mockOnOpenChange,
    onOverwrite: mockOnOverwrite,
    onMerge: mockOnMerge,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Loading state', () => {
    it('shows loading skeleton when isLoading is true', () => {
      mockUseConflictCheck.mockReturnValue({
        diffData: undefined,
        hasChanges: false,
        hasConflicts: false,
        targetHasChanges: false,
        isLoading: true,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      // Should show skeleton elements (using toBeInTheDocument for elements)
      const skeletons = screen.getAllByTestId('skeleton');
      expect(skeletons.length).toBeGreaterThan(0);
    });

    it('does not show error or content during loading', () => {
      mockUseConflictCheck.mockReturnValue({
        diffData: undefined,
        hasChanges: false,
        hasConflicts: false,
        targetHasChanges: false,
        isLoading: true,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      expect(screen.queryByText(/Failed to load diff/)).not.toBeInTheDocument();
      expect(screen.queryByText(/No changes detected/)).not.toBeInTheDocument();
    });
  });

  describe('Error state', () => {
    it('shows error alert when error is set', () => {
      const mockError = new Error('Network error occurred');
      mockUseConflictCheck.mockReturnValue({
        diffData: undefined,
        hasChanges: false,
        hasConflicts: false,
        targetHasChanges: false,
        isLoading: false,
        error: mockError,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      expect(screen.getByText(/Failed to load diff/)).toBeInTheDocument();
      expect(screen.getByText(/Network error occurred/)).toBeInTheDocument();
    });

    it('shows generic error message when error has no message', () => {
      const mockError = new Error();
      mockUseConflictCheck.mockReturnValue({
        diffData: undefined,
        hasChanges: false,
        hasConflicts: false,
        targetHasChanges: false,
        isLoading: false,
        error: mockError,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      expect(screen.getByText(/An unexpected error occurred/)).toBeInTheDocument();
    });
  });

  describe('No changes state (deploy)', () => {
    it('shows "Safe to proceed" message when hasChanges is false', () => {
      mockUseConflictCheck.mockReturnValue({
        diffData: createMockArtifactDiffResponse({
          has_changes: false,
          files: [],
          summary: {},
        }),
        hasChanges: false,
        hasConflicts: false,
        targetHasChanges: false,
        isLoading: false,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      expect(screen.getByText('No changes detected')).toBeInTheDocument();
      expect(screen.getByText(/Safe to proceed/)).toBeInTheDocument();
    });

    it('shows non-destructive confirm button when no changes', () => {
      mockUseConflictCheck.mockReturnValue({
        diffData: createMockArtifactDiffResponse({
          has_changes: false,
          files: [],
          summary: {},
        }),
        hasChanges: false,
        hasConflicts: false,
        targetHasChanges: false,
        isLoading: false,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      const confirmButton = screen.getByRole('button', { name: /Confirm sync operation/ });
      expect(confirmButton).toBeInTheDocument();
      expect(confirmButton).toHaveTextContent('Confirm');
    });

    it('does not show merge button when no changes', () => {
      mockUseConflictCheck.mockReturnValue({
        diffData: createMockArtifactDiffResponse({
          has_changes: false,
          files: [],
          summary: {},
        }),
        hasChanges: false,
        hasConflicts: false,
        targetHasChanges: false,
        isLoading: false,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      expect(screen.queryByRole('button', { name: /Merge/ })).not.toBeInTheDocument();
    });
  });

  describe('Has changes state (deploy)', () => {
    it('shows DiffViewer with correct labels for deploy direction', () => {
      mockUseConflictCheck.mockReturnValue({
        diffData: createMockArtifactDiffResponse({
          has_changes: true,
          files: [
            createMockFileDiff({
              file_path: 'test.txt',
              status: 'modified',
            }),
          ],
          summary: { modified: 1 },
        }),
        hasChanges: true,
        hasConflicts: false,
        targetHasChanges: true,
        isLoading: false,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      // Check for file count and summary
      expect(screen.getByText(/1 file changed/)).toBeInTheDocument();
      expect(screen.getByText(/1 modified/)).toBeInTheDocument();
    });

    it('shows destructive Deploy button when has changes', () => {
      mockUseConflictCheck.mockReturnValue({
        diffData: createMockArtifactDiffResponse({
          has_changes: true,
          files: [createMockFileDiff({ file_path: 'test.txt', status: 'modified' })],
          summary: { modified: 1 },
        }),
        hasChanges: true,
        hasConflicts: false,
        targetHasChanges: true,
        isLoading: false,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      const deployButton = screen.getByRole('button', { name: /Deploy/ });
      expect(deployButton).toBeInTheDocument();
      expect(deployButton).toHaveTextContent('Deploy');
    });
  });

  describe('Has changes state (push)', () => {
    it('shows correct labels for push direction', () => {
      mockUseConflictCheck.mockReturnValue({
        diffData: createMockArtifactDiffResponse({
          has_changes: true,
          files: [createMockFileDiff({ file_path: 'test.txt', status: 'modified' })],
          summary: { modified: 1 },
        }),
        hasChanges: true,
        hasConflicts: false,
        targetHasChanges: true,
        isLoading: false,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="push" />);

      expect(screen.getByText('Push to Collection')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Push Changes/ })).toBeInTheDocument();
    });

    it('shows "Push Changes" button for push direction', () => {
      mockUseConflictCheck.mockReturnValue({
        diffData: createMockArtifactDiffResponse({
          has_changes: true,
          files: [createMockFileDiff({ file_path: 'test.txt', status: 'modified' })],
          summary: { modified: 1 },
        }),
        hasChanges: true,
        hasConflicts: false,
        targetHasChanges: true,
        isLoading: false,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="push" />);

      const pushButton = screen.getByRole('button', { name: /Push Changes/ });
      expect(pushButton).toBeInTheDocument();
      expect(pushButton).toHaveTextContent('Push Changes');
    });
  });

  describe('Has changes state (pull)', () => {
    it('shows correct labels for pull direction', () => {
      mockUseConflictCheck.mockReturnValue({
        diffData: createMockArtifactDiffResponse({
          has_changes: true,
          files: [createMockFileDiff({ file_path: 'test.txt', status: 'modified' })],
          summary: { modified: 1 },
        }),
        hasChanges: true,
        hasConflicts: false,
        targetHasChanges: true,
        isLoading: false,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="pull" />);

      expect(screen.getByText('Pull from Source')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Pull Changes/ })).toBeInTheDocument();
    });

    it('shows "Pull Changes" button for pull direction', () => {
      mockUseConflictCheck.mockReturnValue({
        diffData: createMockArtifactDiffResponse({
          has_changes: true,
          files: [createMockFileDiff({ file_path: 'test.txt', status: 'modified' })],
          summary: { modified: 1 },
        }),
        hasChanges: true,
        hasConflicts: false,
        targetHasChanges: true,
        isLoading: false,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="pull" />);

      const pullButton = screen.getByRole('button', { name: /Pull Changes/ });
      expect(pullButton).toBeInTheDocument();
      expect(pullButton).toHaveTextContent('Pull Changes');
    });
  });

  describe('Merge button gating', () => {
    it('enables merge button with secondary variant when targetHasChanges is true', () => {
      mockUseConflictCheck.mockReturnValue({
        diffData: createMockArtifactDiffResponse({
          has_changes: true,
          files: [createMockFileDiff({ file_path: 'test.txt', status: 'modified' })],
          summary: { modified: 1 },
        }),
        hasChanges: true,
        hasConflicts: false,
        targetHasChanges: true,
        isLoading: false,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      const mergeButton = screen.getByRole('button', { name: /Open merge workflow/ });
      expect(mergeButton).toBeInTheDocument();
      expect(mergeButton).not.toBeDisabled();
    });

    it('disables merge button when targetHasChanges is false', () => {
      mockUseConflictCheck.mockReturnValue({
        diffData: createMockArtifactDiffResponse({
          has_changes: true,
          files: [createMockFileDiff({ file_path: 'test.txt', status: 'modified' })],
          summary: { modified: 1 },
        }),
        hasChanges: true,
        hasConflicts: false,
        targetHasChanges: false,
        isLoading: false,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      const mergeButton = screen.getByRole('button', {
        name: /Merge unavailable: no local changes to merge/,
      });
      expect(mergeButton).toBeInTheDocument();
      expect(mergeButton).toBeDisabled();
    });

    it('shows tooltip when merge is disabled', async () => {
      const user = userEvent.setup();
      mockUseConflictCheck.mockReturnValue({
        diffData: createMockArtifactDiffResponse({
          has_changes: true,
          files: [createMockFileDiff({ file_path: 'test.txt', status: 'modified' })],
          summary: { modified: 1 },
        }),
        hasChanges: true,
        hasConflicts: false,
        targetHasChanges: false,
        isLoading: false,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      const mergeButton = screen.getByRole('button', {
        name: /Merge unavailable/,
      });

      await user.hover(mergeButton);

      // Tooltip should appear with explanation text (may be in multiple places due to aria-describedby)
      await waitFor(() => {
        const tooltipTexts = screen.getAllByText('No local changes to merge');
        expect(tooltipTexts.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Conflict warning', () => {
    it('shows conflict alert when hasConflicts is true', () => {
      mockUseConflictCheck.mockReturnValue({
        diffData: createMockArtifactDiffResponse({
          has_changes: true,
          files: [createMockFileDiff({ file_path: 'test.txt', status: 'modified' })],
          summary: { modified: 1, conflicts: 1 },
        }),
        hasChanges: true,
        hasConflicts: true,
        targetHasChanges: true,
        isLoading: false,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      expect(
        screen.getByText(/Consider merging to avoid losing project modifications/)
      ).toBeInTheDocument();
    });

    it('shows direction-specific conflict warning for push', () => {
      mockUseConflictCheck.mockReturnValue({
        diffData: createMockArtifactDiffResponse({
          has_changes: true,
          files: [createMockFileDiff({ file_path: 'test.txt', status: 'modified' })],
          summary: { modified: 1, conflicts: 1 },
        }),
        hasChanges: true,
        hasConflicts: true,
        targetHasChanges: true,
        isLoading: false,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="push" />);

      expect(
        screen.getByText(/Consider merging to preserve collection changes/)
      ).toBeInTheDocument();
    });

    it('shows direction-specific conflict warning for pull', () => {
      mockUseConflictCheck.mockReturnValue({
        diffData: createMockArtifactDiffResponse({
          has_changes: true,
          files: [createMockFileDiff({ file_path: 'test.txt', status: 'modified' })],
          summary: { modified: 1, conflicts: 1 },
        }),
        hasChanges: true,
        hasConflicts: true,
        targetHasChanges: true,
        isLoading: false,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="pull" />);

      expect(
        screen.getByText(/Consider merging to preserve your local modifications/)
      ).toBeInTheDocument();
    });

    it('does not show conflict alert when hasConflicts is false', () => {
      mockUseConflictCheck.mockReturnValue({
        diffData: createMockArtifactDiffResponse({
          has_changes: true,
          files: [createMockFileDiff({ file_path: 'test.txt', status: 'modified' })],
          summary: { modified: 1 },
        }),
        hasChanges: true,
        hasConflicts: false,
        targetHasChanges: true,
        isLoading: false,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      expect(screen.queryByText(/Consider merging/)).not.toBeInTheDocument();
    });
  });

  describe('Button actions', () => {
    it('calls onOverwrite when overwrite button is clicked', async () => {
      const user = userEvent.setup();
      mockUseConflictCheck.mockReturnValue({
        diffData: createMockArtifactDiffResponse({
          has_changes: true,
          files: [createMockFileDiff({ file_path: 'test.txt', status: 'modified' })],
          summary: { modified: 1 },
        }),
        hasChanges: true,
        hasConflicts: false,
        targetHasChanges: true,
        isLoading: false,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      const deployButton = screen.getByRole('button', { name: /Deploy/ });
      await user.click(deployButton);

      expect(mockOnOverwrite).toHaveBeenCalledTimes(1);
    });

    it('calls onMerge when merge button is clicked', async () => {
      const user = userEvent.setup();
      mockUseConflictCheck.mockReturnValue({
        diffData: createMockArtifactDiffResponse({
          has_changes: true,
          files: [createMockFileDiff({ file_path: 'test.txt', status: 'modified' })],
          summary: { modified: 1 },
        }),
        hasChanges: true,
        hasConflicts: false,
        targetHasChanges: true,
        isLoading: false,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      const mergeButton = screen.getByRole('button', { name: /Open merge workflow/ });
      await user.click(mergeButton);

      expect(mockOnMerge).toHaveBeenCalledTimes(1);
    });

    it('calls onCancel and onOpenChange when cancel button is clicked', async () => {
      const user = userEvent.setup();
      mockUseConflictCheck.mockReturnValue({
        diffData: createMockArtifactDiffResponse({
          has_changes: true,
          files: [createMockFileDiff({ file_path: 'test.txt', status: 'modified' })],
          summary: { modified: 1 },
        }),
        hasChanges: true,
        hasConflicts: false,
        targetHasChanges: true,
        isLoading: false,
        error: null,
      });

      render(
        <SyncConfirmationDialog {...defaultProps} onCancel={mockOnCancel} direction="deploy" />
      );

      const cancelButton = screen.getByRole('button', { name: /Cancel sync operation/ });
      await user.click(cancelButton);

      expect(mockOnCancel).toHaveBeenCalledTimes(1);
      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });

    it('calls only onOpenChange when cancel is clicked without onCancel prop', async () => {
      const user = userEvent.setup();
      mockUseConflictCheck.mockReturnValue({
        diffData: createMockArtifactDiffResponse({
          has_changes: true,
          files: [createMockFileDiff({ file_path: 'test.txt', status: 'modified' })],
          summary: { modified: 1 },
        }),
        hasChanges: true,
        hasConflicts: false,
        targetHasChanges: true,
        isLoading: false,
        error: null,
      });

      const propsWithoutCancel = { ...defaultProps };
      delete (propsWithoutCancel as any).onCancel;

      render(<SyncConfirmationDialog {...propsWithoutCancel} direction="deploy" />);

      const cancelButton = screen.getByRole('button', { name: /Cancel sync operation/ });
      await user.click(cancelButton);

      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });
  });

  describe('Dialog titles per direction', () => {
    it('shows "Deploy to Project" title for deploy direction', () => {
      mockUseConflictCheck.mockReturnValue({
        diffData: undefined,
        hasChanges: false,
        hasConflicts: false,
        targetHasChanges: false,
        isLoading: true,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      expect(screen.getByText('Deploy to Project')).toBeInTheDocument();
    });

    it('shows "Push to Collection" title for push direction', () => {
      mockUseConflictCheck.mockReturnValue({
        diffData: undefined,
        hasChanges: false,
        hasConflicts: false,
        targetHasChanges: false,
        isLoading: true,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="push" />);

      expect(screen.getByText('Push to Collection')).toBeInTheDocument();
    });

    it('shows "Pull from Source" title for pull direction', () => {
      mockUseConflictCheck.mockReturnValue({
        diffData: undefined,
        hasChanges: false,
        hasConflicts: false,
        targetHasChanges: false,
        isLoading: true,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="pull" />);

      expect(screen.getByText('Pull from Source')).toBeInTheDocument();
    });
  });

  describe('File count and summary', () => {
    it('shows correct file count for single file', () => {
      mockUseConflictCheck.mockReturnValue({
        diffData: createMockArtifactDiffResponse({
          has_changes: true,
          files: [createMockFileDiff({ file_path: 'test.txt', status: 'modified' })],
          summary: { modified: 1 },
        }),
        hasChanges: true,
        hasConflicts: false,
        targetHasChanges: true,
        isLoading: false,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      expect(screen.getByText(/1 file changed/)).toBeInTheDocument();
    });

    it('shows correct file count for multiple files', () => {
      mockUseConflictCheck.mockReturnValue({
        diffData: createMockArtifactDiffResponse({
          has_changes: true,
          files: [
            createMockFileDiff({ file_path: 'test1.txt', status: 'modified' }),
            createMockFileDiff({ file_path: 'test2.txt', status: 'added' }),
            createMockFileDiff({ file_path: 'test3.txt', status: 'deleted' }),
          ],
          summary: { modified: 1, added: 1, deleted: 1 },
        }),
        hasChanges: true,
        hasConflicts: false,
        targetHasChanges: true,
        isLoading: false,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      expect(screen.getByText(/3 files changed/)).toBeInTheDocument();
    });

    it('shows detailed summary with added, modified, deleted counts', () => {
      mockUseConflictCheck.mockReturnValue({
        diffData: createMockArtifactDiffResponse({
          has_changes: true,
          files: [
            createMockFileDiff({ file_path: 'test1.txt', status: 'modified' }),
            createMockFileDiff({ file_path: 'test2.txt', status: 'added' }),
            createMockFileDiff({ file_path: 'test3.txt', status: 'deleted' }),
          ],
          summary: { modified: 1, added: 1, deleted: 1 },
        }),
        hasChanges: true,
        hasConflicts: false,
        targetHasChanges: true,
        isLoading: false,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      expect(screen.getByText(/1 added, 1 modified, 1 deleted/)).toBeInTheDocument();
    });
  });

  describe('Dialog open state', () => {
    it('does not render when open is false', () => {
      mockUseConflictCheck.mockReturnValue({
        diffData: undefined,
        hasChanges: false,
        hasConflicts: false,
        targetHasChanges: false,
        isLoading: false,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} open={false} direction="deploy" />);

      expect(screen.queryByText('Deploy to Project')).not.toBeInTheDocument();
    });

    it('passes enabled: true to useConflictCheck when open is true', () => {
      mockUseConflictCheck.mockReturnValue({
        diffData: undefined,
        hasChanges: false,
        hasConflicts: false,
        targetHasChanges: false,
        isLoading: true,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} open={true} direction="deploy" />);

      expect(mockUseConflictCheck).toHaveBeenCalledWith('deploy', mockArtifact.id, {
        projectPath: '/path/to/project',
        enabled: true,
      });
    });

    it('passes enabled: false to useConflictCheck when open is false', () => {
      mockUseConflictCheck.mockReturnValue({
        diffData: undefined,
        hasChanges: false,
        hasConflicts: false,
        targetHasChanges: false,
        isLoading: false,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} open={false} direction="deploy" />);

      expect(mockUseConflictCheck).toHaveBeenCalledWith('deploy', mockArtifact.id, {
        projectPath: '/path/to/project',
        enabled: false,
      });
    });
  });
});
