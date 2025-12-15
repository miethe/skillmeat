/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { DiffViewer } from '@/components/entity/diff-viewer';
import type { FileDiff } from '@/sdk/models/FileDiff';

const mockFileDiffModified: FileDiff = {
  file_path: 'src/example.ts',
  status: 'modified',
  unified_diff: `@@ -1,3 +1,3 @@
 function example() {
-  console.log('old');
+  console.log('new');
 }`,
};

const mockFileDiffAdded: FileDiff = {
  file_path: 'src/new-file.ts',
  status: 'added',
  unified_diff: null,
};

const mockFileDiffDeleted: FileDiff = {
  file_path: 'src/old-file.ts',
  status: 'deleted',
  unified_diff: null,
};

const mockFileDiffUnchanged: FileDiff = {
  file_path: 'src/unchanged.ts',
  status: 'unchanged',
  unified_diff: null,
};

describe('DiffViewer', () => {
  it('renders file list correctly', () => {
    const files = [mockFileDiffModified, mockFileDiffAdded];
    render(<DiffViewer files={files} />);

    expect(screen.getByText('src/example.ts')).toBeInTheDocument();
    expect(screen.getByText('src/new-file.ts')).toBeInTheDocument();
  });

  it('displays summary statistics in header', () => {
    const files = [
      mockFileDiffModified,
      mockFileDiffAdded,
      mockFileDiffDeleted,
      mockFileDiffUnchanged,
    ];
    render(<DiffViewer files={files} />);

    expect(screen.getByText('+1')).toBeInTheDocument(); // Added
    expect(screen.getByText('~1')).toBeInTheDocument(); // Modified
    expect(screen.getByText('-1')).toBeInTheDocument(); // Deleted
  });

  it('renders empty state when no files provided', () => {
    render(<DiffViewer files={[]} />);

    expect(screen.getByText('No changes to display')).toBeInTheDocument();
  });

  it('shows file status badges correctly', () => {
    const files = [
      mockFileDiffModified,
      mockFileDiffAdded,
      mockFileDiffDeleted,
      mockFileDiffUnchanged,
    ];
    render(<DiffViewer files={files} />);

    expect(screen.getByText('Modified')).toBeInTheDocument();
    expect(screen.getByText('Added')).toBeInTheDocument();
    expect(screen.getByText('Deleted')).toBeInTheDocument();
    expect(screen.getByText('Unchanged')).toBeInTheDocument();
  });

  it('parses unified diff format and displays diff lines', () => {
    render(<DiffViewer files={[mockFileDiffModified]} />);

    // Should show old and new content
    expect(screen.getByText(/console\.log\('old'\)/)).toBeInTheDocument();
    expect(screen.getByText(/console\.log\('new'\)/)).toBeInTheDocument();
  });

  it('renders side-by-side view for modified files', () => {
    render(<DiffViewer files={[mockFileDiffModified]} leftLabel="Before" rightLabel="After" />);

    expect(screen.getByText('Before')).toBeInTheDocument();
    expect(screen.getByText('After')).toBeInTheDocument();
  });

  it('displays custom labels for left and right panels', () => {
    render(
      <DiffViewer files={[mockFileDiffModified]} leftLabel="Collection" rightLabel="Project" />
    );

    expect(screen.getByText('Collection')).toBeInTheDocument();
    expect(screen.getByText('Project')).toBeInTheDocument();
  });

  it('shows message for added files', () => {
    render(<DiffViewer files={[mockFileDiffAdded]} rightLabel="New Version" />);

    expect(screen.getByText(/This file was added in New Version/)).toBeInTheDocument();
  });

  it('shows message for deleted files', () => {
    render(<DiffViewer files={[mockFileDiffDeleted]} leftLabel="Old Version" />);

    expect(screen.getByText(/This file was deleted from Old Version/)).toBeInTheDocument();
  });

  it('displays no changes message for unchanged files', () => {
    render(<DiffViewer files={[mockFileDiffUnchanged]} />);

    expect(screen.getByText('No changes in this file')).toBeInTheDocument();
  });

  it('allows file selection by clicking', () => {
    const files = [mockFileDiffModified, mockFileDiffAdded];
    render(<DiffViewer files={files} />);

    const secondFile = screen.getByText('src/new-file.ts');
    fireEvent.click(secondFile);

    // Should display the selected file
    expect(screen.getByText(/Content preview not available for added files/)).toBeInTheDocument();
  });

  it('calls onClose handler when close button is clicked', () => {
    const handleClose = jest.fn();
    render(<DiffViewer files={[mockFileDiffModified]} onClose={handleClose} />);

    const closeButton = screen.getByRole('button', { name: '' });
    fireEvent.click(closeButton);

    expect(handleClose).toHaveBeenCalled();
  });

  it('expands and collapses file details', () => {
    render(<DiffViewer files={[mockFileDiffModified]} />);

    const fileButton = screen.getByText('src/example.ts');

    // Initially should be expanded (first file)
    expect(screen.getByText(/1 additions, 1 deletions/)).toBeInTheDocument();

    // Click to collapse
    const chevronButton = fileButton.parentElement?.querySelector('button');
    if (chevronButton) {
      fireEvent.click(chevronButton);
    }
  });

  it('handles empty diff gracefully', () => {
    const emptyDiff: FileDiff = {
      file_path: 'empty.ts',
      status: 'modified',
      unified_diff: '',
    };
    render(<DiffViewer files={[emptyDiff]} />);

    expect(screen.getByText('empty.ts')).toBeInTheDocument();
  });

  it('handles complex unified diff with multiple hunks', () => {
    const complexDiff: FileDiff = {
      file_path: 'complex.ts',
      status: 'modified',
      unified_diff: `@@ -1,5 +1,6 @@
 function test() {
-  const a = 1;
+  const a = 2;
+  const b = 3;
 }

@@ -10,3 +11,4 @@
 function other() {
-  return true;
+  return false;
+  console.log('added');
 }`,
    };
    render(<DiffViewer files={[complexDiff]} />);

    expect(screen.getByText('complex.ts')).toBeInTheDocument();
  });

  it('renders Diff Viewer title', () => {
    render(<DiffViewer files={[mockFileDiffModified]} />);

    expect(screen.getByText('Diff Viewer')).toBeInTheDocument();
  });

  // New tests for sync resolution actions
  describe('Sync Resolution Actions', () => {
    it('does not show resolution actions by default', () => {
      render(<DiffViewer files={[mockFileDiffModified]} />);

      expect(screen.queryByText(/Keep Local/)).not.toBeInTheDocument();
      expect(screen.queryByText(/Keep Remote/)).not.toBeInTheDocument();
      expect(screen.queryByText('Merge')).not.toBeInTheDocument();
    });

    it('shows resolution actions when showResolutionActions is true', () => {
      const handleResolve = jest.fn();
      render(
        <DiffViewer
          files={[mockFileDiffModified]}
          showResolutionActions={true}
          onResolve={handleResolve}
        />
      );

      expect(screen.getByText(/Keep Local \(Project\)/)).toBeInTheDocument();
      expect(screen.getByText(/Keep Remote \(Collection\)/)).toBeInTheDocument();
      expect(screen.getByText('Merge')).toBeInTheDocument();
    });

    it('uses custom labels for resolution buttons', () => {
      const handleResolve = jest.fn();
      render(
        <DiffViewer
          files={[mockFileDiffModified]}
          showResolutionActions={true}
          onResolve={handleResolve}
          localLabel="Working Copy"
          remoteLabel="Upstream"
        />
      );

      expect(screen.getByText('Keep Working Copy')).toBeInTheDocument();
      expect(screen.getByText('Keep Upstream')).toBeInTheDocument();
    });

    it('calls onResolve with correct resolution type when Keep Local clicked', () => {
      const handleResolve = jest.fn();
      render(
        <DiffViewer
          files={[mockFileDiffModified]}
          showResolutionActions={true}
          onResolve={handleResolve}
        />
      );

      const keepLocalButton = screen.getByText(/Keep Local \(Project\)/);
      fireEvent.click(keepLocalButton);

      expect(handleResolve).toHaveBeenCalledWith('keep_local');
    });

    it('calls onResolve with correct resolution type when Keep Remote clicked', () => {
      const handleResolve = jest.fn();
      render(
        <DiffViewer
          files={[mockFileDiffModified]}
          showResolutionActions={true}
          onResolve={handleResolve}
        />
      );

      const keepRemoteButton = screen.getByText(/Keep Remote \(Collection\)/);
      fireEvent.click(keepRemoteButton);

      expect(handleResolve).toHaveBeenCalledWith('keep_remote');
    });

    it('calls onResolve with correct resolution type when Merge clicked', () => {
      const handleResolve = jest.fn();
      render(
        <DiffViewer
          files={[mockFileDiffModified]}
          showResolutionActions={true}
          onResolve={handleResolve}
        />
      );

      const mergeButton = screen.getByText('Merge');
      fireEvent.click(mergeButton);

      expect(handleResolve).toHaveBeenCalledWith('merge');
    });

    it('disables resolution buttons when isResolving is true', () => {
      const handleResolve = jest.fn();
      render(
        <DiffViewer
          files={[mockFileDiffModified]}
          showResolutionActions={true}
          onResolve={handleResolve}
          isResolving={true}
        />
      );

      const keepLocalButton = screen.getByText(/Keep Local \(Project\)/);
      const keepRemoteButton = screen.getByText(/Keep Remote \(Collection\)/);
      const mergeButton = screen.getByText('Merge');

      expect(keepLocalButton).toBeDisabled();
      expect(keepRemoteButton).toBeDisabled();
      expect(mergeButton).toBeDisabled();
    });

    it('shows loading spinner when isResolving is true', () => {
      const handleResolve = jest.fn();
      render(
        <DiffViewer
          files={[mockFileDiffModified]}
          showResolutionActions={true}
          onResolve={handleResolve}
          isResolving={true}
        />
      );

      // Loader2 component should be rendered (check for svg with animation class)
      const spinner = document.querySelector('.animate-spin');
      expect(spinner).toBeInTheDocument();
    });

    it('shows preview mode message when previewMode is true', () => {
      const handleResolve = jest.fn();
      render(
        <DiffViewer
          files={[mockFileDiffModified]}
          showResolutionActions={true}
          onResolve={handleResolve}
          previewMode={true}
        />
      );

      expect(screen.getByText(/Preview mode - select which version to keep/)).toBeInTheDocument();
    });

    it('does not show preview mode message when previewMode is false', () => {
      const handleResolve = jest.fn();
      render(
        <DiffViewer
          files={[mockFileDiffModified]}
          showResolutionActions={true}
          onResolve={handleResolve}
          previewMode={false}
        />
      );

      expect(
        screen.queryByText(/Preview mode - select which version to keep/)
      ).not.toBeInTheDocument();
    });

    it('maintains existing diff functionality when resolution actions are enabled', () => {
      const handleResolve = jest.fn();
      render(
        <DiffViewer
          files={[mockFileDiffModified]}
          leftLabel="Collection"
          rightLabel="Project"
          showResolutionActions={true}
          onResolve={handleResolve}
        />
      );

      // Existing functionality should still work
      expect(screen.getByText('Collection')).toBeInTheDocument();
      expect(screen.getByText('Project')).toBeInTheDocument();
      expect(screen.getByText(/console\.log\('old'\)/)).toBeInTheDocument();
      expect(screen.getByText(/console\.log\('new'\)/)).toBeInTheDocument();
    });
  });
});
