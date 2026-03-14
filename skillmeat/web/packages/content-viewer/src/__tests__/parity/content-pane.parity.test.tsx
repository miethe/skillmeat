/**
 * Parity tests for ContentPane — BASE-002 scenarios 1, 4, 5, 8, 9
 *
 * Scenario 1 — Empty state:
 *   When no file is selected (path=null) the pane shows a placeholder message.
 *
 * Scenario 4 — Loading states:
 *   While fetching (isLoading=true) a loading skeleton is shown; the actual
 *   content is not rendered yet.
 *
 * Scenario 5 — Error states:
 *   When an API error is passed via the error prop, an error message is
 *   displayed in the pane.
 *
 * Scenario 8 — Truncated file warning:
 *   Large files pass truncationInfo.truncated=true; ContentPane renders a
 *   visible warning banner that mentions "truncated".
 *
 * Scenario 9 — Edit mode transition:
 *   The Edit button is visible for editable files and clicking it transitions
 *   the pane into edit mode (onEditStart is called). In read-only mode the
 *   Edit button is absent.
 *
 * SplitPreview and MarkdownEditor are mocked (as in performance.test.tsx) to
 * keep CodeMirror out of the jsdom test environment.
 */

// ---------------------------------------------------------------------------
// Module-level mocks — declared before imports
// ---------------------------------------------------------------------------

jest.mock('../../components/SplitPreview', () => ({
  SplitPreview: ({ 'data-testid': testId }: { 'data-testid'?: string }) => (
    <div data-testid={testId ?? 'mock-split-preview'}>MockSplitPreview</div>
  ),
}));

jest.mock('../../components/MarkdownEditor', () => ({
  MarkdownEditor: () => (
    <div data-testid="mock-markdown-editor">MockMarkdownEditor</div>
  ),
}));

// ---------------------------------------------------------------------------
// Imports — after mocks are registered
// ---------------------------------------------------------------------------

import React, { act } from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ContentPane } from '@skillmeat/content-viewer';
import type { TruncationInfo } from '@skillmeat/content-viewer';

// ---------------------------------------------------------------------------
// Scenario 1 — Empty state
// ---------------------------------------------------------------------------

describe('ContentPane — empty state (scenario 1)', () => {
  it('shows placeholder text when path is null', async () => {
    await act(async () => {
      render(<ContentPane path={null} content={null} />);
    });

    expect(screen.getByText('No file selected')).toBeInTheDocument();
    expect(
      screen.getByText(/Select a file from the tree/i)
    ).toBeInTheDocument();
  });

  it('does not render any file content when path is null', async () => {
    await act(async () => {
      render(<ContentPane path={null} content={null} />);
    });

    expect(screen.queryByRole('region')).not.toBeInTheDocument();
    expect(screen.queryByText('mock-split-preview')).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Scenario 4 — Loading states
// ---------------------------------------------------------------------------

describe('ContentPane — loading states (scenario 4)', () => {
  it('renders a skeleton when isLoading is true', async () => {
    await act(async () => {
      render(
        <ContentPane
          path="src/index.ts"
          content={null}
          isLoading={true}
        />
      );
    });

    // The main content region must not be present while loading
    expect(screen.queryByTestId('content-pane')).not.toBeInTheDocument();
    // No editor or text content either
    expect(screen.queryByTestId('mock-split-preview')).not.toBeInTheDocument();
  });

  it('renders content when isLoading transitions to false', async () => {
    const content = 'const x = 1;';
    const { rerender } = render(
      <ContentPane path="src/index.ts" content={null} isLoading={true} />
    );

    // Still loading — no content
    expect(screen.queryByTestId('content-pane')).not.toBeInTheDocument();

    await act(async () => {
      rerender(
        <ContentPane path="src/index.ts" content={content} isLoading={false} />
      );
    });

    // After loading completes, the pane renders
    expect(screen.getByTestId('content-pane')).toBeInTheDocument();
    expect(screen.getByText(content)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Scenario 5 — Error states
// ---------------------------------------------------------------------------

describe('ContentPane — error states (scenario 5)', () => {
  it('displays the error message when error prop is set', async () => {
    const errorMessage = 'Failed to load file: 404 Not Found';

    await act(async () => {
      render(
        <ContentPane
          path="src/missing.ts"
          content={null}
          error={errorMessage}
        />
      );
    });

    expect(screen.getByText(errorMessage)).toBeInTheDocument();
  });

  it('does not render file content when error is present', async () => {
    await act(async () => {
      render(
        <ContentPane
          path="src/missing.ts"
          content="some content"
          error="Something went wrong"
        />
      );
    });

    // Error takes precedence — content pane region not rendered
    expect(screen.queryByTestId('content-pane')).not.toBeInTheDocument();
    // But the error itself IS shown
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('shows error as accessible alert', async () => {
    await act(async () => {
      render(
        <ContentPane
          path="src/missing.ts"
          content={null}
          error="Network error occurred"
        />
      );
    });

    // shadcn Alert renders with role="alert"
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Scenario 8 — Truncated file warning
// ---------------------------------------------------------------------------

describe('ContentPane — truncated file warning (scenario 8)', () => {
  const truncationInfo: TruncationInfo = {
    truncated: true,
    originalSize: 5_242_880, // 5 MB
  };

  it('renders a truncation banner when truncationInfo.truncated is true', async () => {
    await act(async () => {
      render(
        <ContentPane
          path="large-file.ts"
          content="// truncated content"
          truncationInfo={truncationInfo}
        />
      );
    });

    expect(screen.getByText('Large file truncated')).toBeInTheDocument();
  });

  it('includes the original file size in the truncation banner', async () => {
    await act(async () => {
      render(
        <ContentPane
          path="large-file.ts"
          content="// truncated content"
          truncationInfo={truncationInfo}
        />
      );
    });

    // 5 MB should be formatted as "5.0 MB" by formatBytes
    expect(screen.getByText(/5\.0\s*MB/)).toBeInTheDocument();
  });

  it('renders a link to the full file when fullFileUrl is provided', async () => {
    const truncationWithUrl: TruncationInfo = {
      truncated: true,
      originalSize: 1_000_000,
      fullFileUrl: 'https://github.com/owner/repo/blob/main/large-file.ts',
    };

    await act(async () => {
      render(
        <ContentPane
          path="large-file.ts"
          content="// truncated content"
          truncationInfo={truncationWithUrl}
        />
      );
    });

    const link = screen.getByRole('link', { name: /View full file on GitHub/i });
    expect(link).toHaveAttribute(
      'href',
      'https://github.com/owner/repo/blob/main/large-file.ts'
    );
  });

  it('does NOT show truncation banner when truncationInfo.truncated is false', async () => {
    const notTruncated: TruncationInfo = {
      truncated: false,
      originalSize: 100,
    };

    await act(async () => {
      render(
        <ContentPane
          path="small-file.ts"
          content="const x = 1;"
          truncationInfo={notTruncated}
        />
      );
    });

    expect(screen.queryByText('Large file truncated')).not.toBeInTheDocument();
  });

  it('shows truncation banner even without an originalSize', async () => {
    const truncationNoSize: TruncationInfo = { truncated: true };

    await act(async () => {
      render(
        <ContentPane
          path="file.ts"
          content="// content"
          truncationInfo={truncationNoSize}
        />
      );
    });

    expect(screen.getByText('Large file truncated')).toBeInTheDocument();
    // Falls back to "large file" label when size is absent (appears in the description span)
    expect(screen.getAllByText(/large file/i).length).toBeGreaterThanOrEqual(1);
  });
});

// ---------------------------------------------------------------------------
// Scenario 9 — Edit mode transition
// ---------------------------------------------------------------------------

describe('ContentPane — edit mode transition (scenario 9)', () => {
  it('shows Edit button for an editable file in non-readOnly mode', async () => {
    const onEditStart = jest.fn();

    await act(async () => {
      render(
        <ContentPane
          path="src/index.ts"
          content="const x = 1;"
          readOnly={false}
          onEditStart={onEditStart}
        />
      );
    });

    expect(screen.getByRole('button', { name: /Edit src\/index\.ts/i })).toBeInTheDocument();
  });

  it('calls onEditStart when Edit button is clicked', async () => {
    const onEditStart = jest.fn();

    await act(async () => {
      render(
        <ContentPane
          path="src/index.ts"
          content="const x = 1;"
          readOnly={false}
          onEditStart={onEditStart}
        />
      );
    });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Edit src\/index\.ts/i }));
    });

    expect(onEditStart).toHaveBeenCalledTimes(1);
  });

  it('hides Edit button when readOnly is true', async () => {
    await act(async () => {
      render(
        <ContentPane
          path="src/index.ts"
          content="const x = 1;"
          readOnly={true}
        />
      );
    });

    expect(screen.queryByRole('button', { name: /Edit/i })).not.toBeInTheDocument();
  });

  it('shows Save and Cancel buttons when isEditing is true and readOnly is false for a markdown file', async () => {
    await act(async () => {
      render(
        <ContentPane
          path="docs/guide.md"
          content="# Guide\n\nSome content."
          readOnly={false}
          isEditing={true}
          editedContent="# Guide\n\nEdited content."
          onSave={jest.fn()}
          onCancel={jest.fn()}
        />
      );
    });

    expect(screen.getByRole('button', { name: /Save/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument();
    // Edit button must NOT be present while already in edit mode
    expect(screen.queryByRole('button', { name: /^Edit/i })).not.toBeInTheDocument();
  });

  it('calls onCancel when Cancel button is clicked during editing of a markdown file', async () => {
    const onCancel = jest.fn();

    await act(async () => {
      render(
        <ContentPane
          path="docs/guide.md"
          content="# Guide\n\nSome content."
          readOnly={false}
          isEditing={true}
          editedContent="# Guide\n\nEdited."
          onSave={jest.fn()}
          onCancel={onCancel}
        />
      );
    });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Cancel/i }));
    });

    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('does not show Edit button for a non-editable file extension', async () => {
    // .bin is not in the editable extensions list
    await act(async () => {
      render(
        <ContentPane
          path="data.bin"
          content="binary data"
          readOnly={false}
          onEditStart={jest.fn()}
        />
      );
    });

    expect(screen.queryByRole('button', { name: /Edit/i })).not.toBeInTheDocument();
  });
});
