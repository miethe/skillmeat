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

    // The file path appears in both sidebar and the diff file header for the selected file,
    // so we assert at least one instance is present using queryAllByText.
    expect(screen.queryAllByText('src/example.ts').length).toBeGreaterThanOrEqual(1);
    expect(screen.queryAllByText('src/new-file.ts').length).toBeGreaterThanOrEqual(1);
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
    // Use a single-file list per render so each status badge is unambiguous.
    // The refactored diff header now also renders a FileStatusBadge for the selected
    // file, so with 4 different files the selected file's status appears twice.
    const { unmount } = render(<DiffViewer files={[mockFileDiffModified]} />);
    expect(screen.queryAllByText('Modified').length).toBeGreaterThanOrEqual(1);
    unmount();

    const { unmount: u2 } = render(<DiffViewer files={[mockFileDiffAdded]} />);
    expect(screen.queryAllByText('Added').length).toBeGreaterThanOrEqual(1);
    u2();

    const { unmount: u3 } = render(<DiffViewer files={[mockFileDiffDeleted]} />);
    expect(screen.queryAllByText('Deleted').length).toBeGreaterThanOrEqual(1);
    u3();

    render(<DiffViewer files={[mockFileDiffUnchanged]} />);
    expect(screen.queryAllByText('Unchanged').length).toBeGreaterThanOrEqual(1);
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

    // The second file appears in the sidebar; click the sidebar entry
    const sidebarEntries = screen.queryAllByText('src/new-file.ts');
    // Click the first occurrence (sidebar entry)
    fireEvent.click(sidebarEntries[0]);

    // Should display the selected file message
    expect(screen.getByText(/Content preview not available for added files/)).toBeInTheDocument();
  });

  it('calls onClose handler when close button is clicked', () => {
    const handleClose = jest.fn();
    render(<DiffViewer files={[mockFileDiffModified]} onClose={handleClose} />);

    // The header close button has an X icon. Use getAllByRole to find all unnamed
    // buttons and click the first one (the header X button). The refactored component
    // may have multiple unnamed icon buttons (e.g. close + sidebar chevrons with role=button).
    // We target the ghost/icon button in the header by its containing div position.
    // Fallback: filter by the button that triggers onClose via icon-only ghost variant.
    const allButtons = screen.getAllByRole('button');
    // The close button is the only ghost icon-sized button with the X svg inside it.
    const closeButton = allButtons.find(
      (btn) => btn.querySelector('svg.lucide-x') !== null
    );
    expect(closeButton).toBeDefined();
    fireEvent.click(closeButton!);

    expect(handleClose).toHaveBeenCalled();
  });

  it('expands and collapses file details', () => {
    render(<DiffViewer files={[mockFileDiffModified]} />);

    // First file is selected and expanded by default: stats visible
    expect(screen.getByText(/1 additions, 1 deletions/)).toBeInTheDocument();

    // The sidebar entry for src/example.ts appears at least once.
    // The expand/collapse chevron is a span with role="button" inside the sidebar row.
    const fileChevrons = screen.getAllByRole('button').filter(
      (btn) => btn.querySelector('svg.lucide-chevron-down') !== null ||
               btn.querySelector('svg.lucide-chevron-right') !== null
    );
    // Alternatively target the span[role=button] chevron inside the sidebar
    const chevronSpans = document.querySelectorAll('span[role="button"]');
    expect(chevronSpans.length).toBeGreaterThan(0);
    // Click the chevron to collapse the first file
    fireEvent.click(chevronSpans[0]);
    // After collapse, stats should disappear
    expect(screen.queryByText(/1 additions, 1 deletions/)).not.toBeInTheDocument();
  });

  it('handles empty diff gracefully', () => {
    const emptyDiff: FileDiff = {
      file_path: 'empty.ts',
      status: 'modified',
      unified_diff: '',
    };
    render(<DiffViewer files={[emptyDiff]} />);

    // file path appears in sidebar and diff file header; assert at least 1 occurrence
    expect(screen.queryAllByText('empty.ts').length).toBeGreaterThanOrEqual(1);
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

    // File path appears in sidebar and diff file header
    expect(screen.queryAllByText('complex.ts').length).toBeGreaterThanOrEqual(1);
  });

  it('renders Diff Viewer title', () => {
    render(<DiffViewer files={[mockFileDiffModified]} />);

    expect(screen.getByText('Diff Viewer')).toBeInTheDocument();
  });

  // ===========================================================================
  // Large-diff guardrail tests (TASK-7.1 - Performance refactor validation)
  // ===========================================================================

  describe('Large file count guardrails (>50 files)', () => {
    /**
     * Generate N distinct file diffs to simulate a large diff.
     * Only the first file gets a unified_diff so it renders diff content.
     */
    function makeFileDiffs(count: number): FileDiff[] {
      return Array.from({ length: count }, (_, i) => ({
        file_path: `src/file-${String(i).padStart(3, '0')}.ts`,
        status: 'modified' as const,
        unified_diff: i === 0
          ? `@@ -1,2 +1,2 @@\n line\n-old\n+new`
          : `@@ -1 +1 @@\n-old\n+new`,
      }));
    }

    it('renders only 50 files when count exceeds threshold', () => {
      const files = makeFileDiffs(75);
      render(<DiffViewer files={files} />);

      // First 50 files should appear in sidebar
      expect(screen.queryAllByText('src/file-000.ts').length).toBeGreaterThanOrEqual(1);
      expect(screen.queryAllByText('src/file-049.ts').length).toBeGreaterThanOrEqual(1);

      // Files beyond threshold should NOT appear in sidebar
      expect(screen.queryByText('src/file-050.ts')).not.toBeInTheDocument();
      expect(screen.queryByText('src/file-074.ts')).not.toBeInTheDocument();
    });

    it('shows "Load all N files" button when count exceeds threshold', () => {
      const files = makeFileDiffs(75);
      render(<DiffViewer files={files} />);

      // The banner shows how many files are shown and a load-all button
      expect(screen.getByText(/Showing 50 of 75 files/)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Load all 75 files/i })).toBeInTheDocument();
    });

    it('reveals all files after clicking "Load all" button', () => {
      const files = makeFileDiffs(75);
      render(<DiffViewer files={files} />);

      // Initially file-074 is not in the sidebar
      expect(screen.queryByText('src/file-074.ts')).not.toBeInTheDocument();

      // Click "Load all" button
      fireEvent.click(screen.getByRole('button', { name: /Load all 75 files/i }));

      // Now all files should be in the sidebar
      expect(screen.queryAllByText('src/file-074.ts').length).toBeGreaterThanOrEqual(1);
      // The banner is gone
      expect(screen.queryByText(/Showing 50 of 75 files/)).not.toBeInTheDocument();
    });

    it('does NOT show "Load all" banner when file count is at or below threshold', () => {
      const files = makeFileDiffs(50);
      render(<DiffViewer files={files} />);

      // Exactly 50 files — no banner
      expect(screen.queryByText(/Showing 50 of/)).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Load all/i })).not.toBeInTheDocument();
    });

    it('does NOT show "Load all" banner for small diffs', () => {
      render(<DiffViewer files={[mockFileDiffModified, mockFileDiffAdded]} />);

      expect(screen.queryByText(/Showing 50 of/)).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Load all/i })).not.toBeInTheDocument();
    });
  });

  describe('Large file diff guardrails (on-demand parse)', () => {
    /**
     * Generate a unified diff string that exceeds the 1000-line threshold.
     * The LARGE_DIFF_LINE_THRESHOLD in diff-viewer.tsx is 1000 lines.
     */
    function makeLargeDiffString(lines = 1100): string {
      const hunkLines = Array.from({ length: lines }, (_, i) =>
        i % 3 === 0 ? `-old line ${i}` : i % 3 === 1 ? `+new line ${i}` : ` context ${i}`
      );
      return `@@ -1,${lines} +1,${lines} @@\n${hunkLines.join('\n')}`;
    }

    it('shows "Load diff" button for large unified diffs instead of rendering them', () => {
      const largeDiff: FileDiff = {
        file_path: 'big-file.ts',
        status: 'modified',
        unified_diff: makeLargeDiffString(1100),
      };

      render(<DiffViewer files={[largeDiff]} />);

      // Should NOT render the raw diff content (too large)
      expect(screen.queryByText(/old line 0/)).not.toBeInTheDocument();

      // Should show the placeholder with size info and a "Load diff" button
      expect(screen.getByText(/This file diff is large/)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Load diff/i })).toBeInTheDocument();
    });

    it('renders diff content after clicking "Load diff"', () => {
      const largeDiff: FileDiff = {
        file_path: 'big-file.ts',
        status: 'modified',
        unified_diff: makeLargeDiffString(1100),
      };

      render(<DiffViewer files={[largeDiff]} />);

      // Click "Load diff" to expand
      fireEvent.click(screen.getByRole('button', { name: /Load diff/i }));

      // After loading, the placeholder should be gone
      expect(screen.queryByText(/This file diff is large/)).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Load diff/i })).not.toBeInTheDocument();
    });

    it('renders small diffs immediately without a "Load diff" button', () => {
      render(<DiffViewer files={[mockFileDiffModified]} />);

      // Small diff: no load button, content rendered directly
      expect(screen.queryByRole('button', { name: /Load diff/i })).not.toBeInTheDocument();
      expect(screen.getByText(/console\.log\('old'\)/)).toBeInTheDocument();
    });

    it('shows stats for large files in the sidebar without loading full diff', () => {
      const largeDiff: FileDiff = {
        file_path: 'big-file.ts',
        status: 'modified',
        unified_diff: makeLargeDiffString(1100),
      };

      render(<DiffViewer files={[largeDiff]} />);

      // Sidebar stats are computed by the lightweight computeDiffStats scanner,
      // not by the full parseDiff that is blocked for large files.
      // The file is expanded by default (index 0), so stats should be visible.
      expect(screen.getByText(/additions, \d+ deletions/)).toBeInTheDocument();
    });

    it('large-diff state resets when files prop changes', () => {
      const largeDiff: FileDiff = {
        file_path: 'big-file.ts',
        status: 'modified',
        unified_diff: makeLargeDiffString(1100),
      };

      const { rerender } = render(<DiffViewer files={[largeDiff]} />);

      // Load the large diff
      fireEvent.click(screen.getByRole('button', { name: /Load diff/i }));
      expect(screen.queryByRole('button', { name: /Load diff/i })).not.toBeInTheDocument();

      // Rerender with the same large diff but a different file_path — cache should reset
      const differentLargeDiff: FileDiff = {
        file_path: 'other-big-file.ts',
        status: 'modified',
        unified_diff: makeLargeDiffString(1100),
      };
      rerender(<DiffViewer files={[differentLargeDiff]} />);

      // New file starts in collapsed/load-button state
      expect(screen.getByRole('button', { name: /Load diff/i })).toBeInTheDocument();
    });
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
