/**
 * @jest-environment jsdom
 *
 * Performance tests for SyncConfirmationDialog file cap behavior.
 *
 * Verifies that large diffs (50+ files) are capped at 10 files by default,
 * that the "Show all N files" button expands to reveal all files, and that
 * render times remain acceptable.
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { Artifact } from '@/types/artifact';
import type { FileDiff } from '@/sdk/models/FileDiff';
import type { ArtifactDiffResponse } from '@/sdk/models/ArtifactDiffResponse';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

jest.mock('@/hooks', () => ({
  useConflictCheck: jest.fn(),
}));

// DiffViewer mock that exposes the file count it receives
jest.mock('@/components/entity/diff-viewer', () => ({
  DiffViewer: ({ files, leftLabel, rightLabel }: any) => (
    <div data-testid="diff-viewer">
      <div data-testid="diff-viewer-left-label">{leftLabel}</div>
      <div data-testid="diff-viewer-right-label">{rightLabel}</div>
      <div data-testid="diff-viewer-file-count">{files.length}</div>
      {files.map((f: any, i: number) => (
        <div key={i} data-testid={`diff-file-${i}`}>
          {f.file_path}
        </div>
      ))}
    </div>
  ),
}));

jest.mock('@/components/ui/skeleton', () => ({
  Skeleton: ({ className }: any) => <div data-testid="skeleton" className={className} />,
}));

import { SyncConfirmationDialog } from '@/components/sync-status/sync-confirmation-dialog';
import { useConflictCheck } from '@/hooks';

const mockUseConflictCheck = useConflictCheck as jest.MockedFunction<typeof useConflictCheck>;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Generate N mock FileDiff entries with unique paths */
function generateMockFiles(count: number): FileDiff[] {
  return Array.from({ length: count }, (_, i) => ({
    file_path: `src/components/file-${String(i).padStart(3, '0')}.tsx`,
    status: i % 3 === 0 ? 'added' : i % 3 === 1 ? 'modified' : 'deleted',
    collection_hash: `hash-coll-${i}`,
    project_hash: `hash-proj-${i}`,
    unified_diff:
      i % 3 === 1
        ? `--- a/file-${i}.tsx\n+++ b/file-${i}.tsx\n@@ -1,3 +1,4 @@\n context\n-old line ${i}\n+new line ${i}\n context`
        : null,
  }));
}

function buildDiffResponse(fileCount: number): ArtifactDiffResponse {
  const files = generateMockFiles(fileCount);
  const added = files.filter((f) => f.status === 'added').length;
  const modified = files.filter((f) => f.status === 'modified').length;
  const deleted = files.filter((f) => f.status === 'deleted').length;

  return {
    artifact_id: 'perf-test-artifact',
    artifact_name: 'perf-skill',
    artifact_type: 'skill',
    collection_name: 'default',
    project_path: '/path/to/project',
    has_changes: true,
    files,
    summary: { added, modified, deleted },
  };
}

const mockArtifact: Artifact = {
  id: 'perf-test-artifact',
  uuid: '00000000000000000000000000000001',
  name: 'perf-skill',
  type: 'skill',
  scope: 'user',
  syncStatus: 'synced',
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
};

const defaultProps = {
  artifact: mockArtifact,
  projectPath: '/path/to/project',
  open: true,
  onOpenChange: jest.fn(),
  onOverwrite: jest.fn(),
  onMerge: jest.fn(),
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('SyncConfirmationDialog — performance (file cap)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('file cap behavior with >10 files', () => {
    const FILE_COUNT = 50;

    beforeEach(() => {
      const diffData = buildDiffResponse(FILE_COUNT);
      mockUseConflictCheck.mockReturnValue({
        diffData,
        hasChanges: true,
        hasConflicts: false,
        targetHasChanges: true,
        isLoading: false,
        error: null,
      });
    });

    it('renders only the first 10 files by default', () => {
      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      const fileCountEl = screen.getByTestId('diff-viewer-file-count');
      expect(fileCountEl).toHaveTextContent('10');
    });

    it('shows "Show all N files" button with the total count', () => {
      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      const showAllButton = screen.getByRole('button', {
        name: `Show all ${FILE_COUNT} files`,
      });
      expect(showAllButton).toBeInTheDocument();
      expect(showAllButton).toHaveTextContent(`Show all ${FILE_COUNT} files`);
    });

    it('renders all files after clicking "Show all"', async () => {
      const user = userEvent.setup();
      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      // Verify capped first
      expect(screen.getByTestId('diff-viewer-file-count')).toHaveTextContent('10');

      // Click show all
      const showAllButton = screen.getByRole('button', {
        name: `Show all ${FILE_COUNT} files`,
      });
      await user.click(showAllButton);

      // Now all files should be passed to DiffViewer
      expect(screen.getByTestId('diff-viewer-file-count')).toHaveTextContent(String(FILE_COUNT));
    });

    it('hides "Show all" button after expanding', async () => {
      const user = userEvent.setup();
      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      const showAllButton = screen.getByRole('button', {
        name: `Show all ${FILE_COUNT} files`,
      });
      await user.click(showAllButton);

      expect(
        screen.queryByRole('button', { name: `Show all ${FILE_COUNT} files` })
      ).not.toBeInTheDocument();
    });

    it('still shows the total changed file count in the summary line', () => {
      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      // The summary line should reflect the total, not the capped number
      expect(screen.getByText(`${FILE_COUNT} files changed`, { exact: false })).toBeInTheDocument();
    });
  });

  describe('no cap when files <= 10', () => {
    it('does not show "Show all" button for 5 files', () => {
      const diffData = buildDiffResponse(5);
      mockUseConflictCheck.mockReturnValue({
        diffData,
        hasChanges: true,
        hasConflicts: false,
        targetHasChanges: true,
        isLoading: false,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      expect(screen.queryByRole('button', { name: /Show all/ })).not.toBeInTheDocument();
      expect(screen.getByTestId('diff-viewer-file-count')).toHaveTextContent('5');
    });

    it('does not show "Show all" button for exactly 10 files', () => {
      const diffData = buildDiffResponse(10);
      mockUseConflictCheck.mockReturnValue({
        diffData,
        hasChanges: true,
        hasConflicts: false,
        targetHasChanges: true,
        isLoading: false,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      expect(screen.queryByRole('button', { name: /Show all/ })).not.toBeInTheDocument();
      expect(screen.getByTestId('diff-viewer-file-count')).toHaveTextContent('10');
    });
  });

  describe('boundary: 11 files triggers the cap', () => {
    it('shows "Show all 11 files" button for exactly 11 files', () => {
      const diffData = buildDiffResponse(11);
      mockUseConflictCheck.mockReturnValue({
        diffData,
        hasChanges: true,
        hasConflicts: false,
        targetHasChanges: true,
        isLoading: false,
        error: null,
      });

      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);

      expect(screen.getByTestId('diff-viewer-file-count')).toHaveTextContent('10');
      expect(screen.getByRole('button', { name: 'Show all 11 files' })).toBeInTheDocument();
    });
  });

  describe('render performance', () => {
    it('renders 50 files (capped) in under 500ms', () => {
      const diffData = buildDiffResponse(50);
      mockUseConflictCheck.mockReturnValue({
        diffData,
        hasChanges: true,
        hasConflicts: false,
        targetHasChanges: true,
        isLoading: false,
        error: null,
      });

      const start = performance.now();
      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);
      const elapsed = performance.now() - start;

      expect(elapsed).toBeLessThan(500);
      // Confirm we are actually rendering the capped set
      expect(screen.getByTestId('diff-viewer-file-count')).toHaveTextContent('10');
    });

    it('renders 100 files (capped) in under 500ms', () => {
      const diffData = buildDiffResponse(100);
      mockUseConflictCheck.mockReturnValue({
        diffData,
        hasChanges: true,
        hasConflicts: false,
        targetHasChanges: true,
        isLoading: false,
        error: null,
      });

      const start = performance.now();
      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);
      const elapsed = performance.now() - start;

      expect(elapsed).toBeLessThan(500);
      expect(screen.getByTestId('diff-viewer-file-count')).toHaveTextContent('10');
    });

    it('renders a typical diff (5 files, no cap) in under 200ms', () => {
      const diffData = buildDiffResponse(5);
      mockUseConflictCheck.mockReturnValue({
        diffData,
        hasChanges: true,
        hasConflicts: false,
        targetHasChanges: true,
        isLoading: false,
        error: null,
      });

      const start = performance.now();
      render(<SyncConfirmationDialog {...defaultProps} direction="deploy" />);
      const elapsed = performance.now() - start;

      expect(elapsed).toBeLessThan(200);
      expect(screen.getByTestId('diff-viewer-file-count')).toHaveTextContent('5');
    });
  });
});
