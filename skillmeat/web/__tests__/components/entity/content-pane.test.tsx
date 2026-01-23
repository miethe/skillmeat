/**
 * @jest-environment jsdom
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ContentPane } from '@/components/entity/content-pane';

// Mock the SplitPreview component to simplify markdown rendering tests
jest.mock('@/components/editor/split-preview', () => ({
  SplitPreview: ({ content, isEditing, onChange }: any) => (
    <div data-testid="split-preview">
      {isEditing ? (
        <textarea
          data-testid="split-preview-editor"
          value={content}
          onChange={(e) => onChange?.(e.target.value)}
        />
      ) : (
        <div data-testid="split-preview-content">{content}</div>
      )}
    </div>
  ),
}));

// Mock the FrontmatterDisplay component
jest.mock('@/components/entity/frontmatter-display', () => ({
  FrontmatterDisplay: ({ frontmatter, defaultCollapsed, className }: any) => (
    <div data-testid="frontmatter-display" className={className}>
      <pre>{JSON.stringify(frontmatter, null, 2)}</pre>
    </div>
  ),
}));

// Sample content with frontmatter
const contentWithFrontmatter = `---
title: Test Document
author: Test Author
tags:
  - testing
  - jest
version: 1.0.0
---

# Main Content

This is the body of the document after the frontmatter.

## Section 1

Some text here.
`;

// Sample content without frontmatter
const contentWithoutFrontmatter = `# Regular Markdown

This is a document without any frontmatter.

## Section

Content here.
`;

// Simple non-markdown content
const plainTextContent = `This is plain text content
with multiple lines
but no frontmatter.`;

describe('ContentPane', () => {
  describe('Basic Rendering', () => {
    it('renders empty state when no path is provided', () => {
      render(<ContentPane path={null} content={null} />);

      expect(screen.getByText('No file selected')).toBeInTheDocument();
      expect(
        screen.getByText('Select a file from the tree on the left to view its contents.')
      ).toBeInTheDocument();
    });

    it('renders content when path and content provided', () => {
      render(
        <ContentPane path="test.txt" content="Hello world" />
      );

      expect(screen.getByText('test.txt')).toBeInTheDocument();
      expect(screen.getByText('Hello world')).toBeInTheDocument();
    });

    it('renders loading skeleton when isLoading is true', () => {
      const { container } = render(
        <ContentPane path="test.md" content={null} isLoading={true} />
      );

      // Should show skeleton elements
      const skeletons = container.querySelectorAll('.animate-pulse');
      // The skeleton should have multiple shimmer elements for lines
      expect(skeletons.length).toBeGreaterThan(0);
    });

    it('renders error state when error is provided', () => {
      render(
        <ContentPane path="test.md" content={null} error="Failed to load file" />
      );

      expect(screen.getByText('Failed to load file')).toBeInTheDocument();
    });

    it('renders empty content message for empty file', () => {
      render(
        <ContentPane path="empty.txt" content="" />
      );

      expect(screen.getByText('This file is empty')).toBeInTheDocument();
    });
  });

  describe('showFrontmatter Prop Behavior', () => {
    describe('When showFrontmatter=true (default)', () => {
      it('strips raw frontmatter from content when showFrontmatter=true', () => {
        render(
          <ContentPane
            path="test.md"
            content={contentWithFrontmatter}
            showFrontmatter={true}
          />
        );

        // FrontmatterDisplay should be rendered
        expect(screen.getByTestId('frontmatter-display')).toBeInTheDocument();

        // The raw frontmatter delimiters should NOT appear in the body content
        const splitPreview = screen.getByTestId('split-preview-content');
        expect(splitPreview.textContent).not.toContain('---\ntitle:');
        expect(splitPreview.textContent).not.toContain('author: Test Author');

        // But the body content should be present
        expect(splitPreview.textContent).toContain('# Main Content');
      });

      it('displays FrontmatterDisplay component with parsed frontmatter', () => {
        render(
          <ContentPane
            path="test.md"
            content={contentWithFrontmatter}
            showFrontmatter={true}
          />
        );

        const frontmatterDisplay = screen.getByTestId('frontmatter-display');
        expect(frontmatterDisplay).toBeInTheDocument();

        // Check that parsed frontmatter values are present
        expect(frontmatterDisplay.textContent).toContain('Test Document');
        expect(frontmatterDisplay.textContent).toContain('Test Author');
      });

      it('preserves body content after stripping frontmatter', () => {
        render(
          <ContentPane
            path="test.md"
            content={contentWithFrontmatter}
            showFrontmatter={true}
          />
        );

        const splitPreview = screen.getByTestId('split-preview-content');

        // All body content should be preserved
        expect(splitPreview.textContent).toContain('# Main Content');
        expect(splitPreview.textContent).toContain('This is the body of the document');
        expect(splitPreview.textContent).toContain('## Section 1');
        expect(splitPreview.textContent).toContain('Some text here.');
      });
    });

    describe('When showFrontmatter=false', () => {
      it('displays content with raw frontmatter when showFrontmatter=false', () => {
        render(
          <ContentPane
            path="test.md"
            content={contentWithFrontmatter}
            showFrontmatter={false}
          />
        );

        // The FrontmatterDisplay is still shown because frontmatter is detected
        // but the content passed to SplitPreview should include the raw frontmatter
        const splitPreview = screen.getByTestId('split-preview-content');

        // The body should include the raw frontmatter
        expect(splitPreview.textContent).toContain('---');
        expect(splitPreview.textContent).toContain('title: Test Document');
        expect(splitPreview.textContent).toContain('# Main Content');
      });
    });

    describe('Content Without Frontmatter', () => {
      it('handles content without frontmatter correctly when showFrontmatter=true', () => {
        render(
          <ContentPane
            path="test.md"
            content={contentWithoutFrontmatter}
            showFrontmatter={true}
          />
        );

        // FrontmatterDisplay should NOT be rendered
        expect(screen.queryByTestId('frontmatter-display')).not.toBeInTheDocument();

        // Full content should be displayed
        const splitPreview = screen.getByTestId('split-preview-content');
        expect(splitPreview.textContent).toContain('# Regular Markdown');
        expect(splitPreview.textContent).toContain('This is a document without any frontmatter');
      });

      it('handles content without frontmatter correctly when showFrontmatter=false', () => {
        render(
          <ContentPane
            path="test.md"
            content={contentWithoutFrontmatter}
            showFrontmatter={false}
          />
        );

        // FrontmatterDisplay should NOT be rendered
        expect(screen.queryByTestId('frontmatter-display')).not.toBeInTheDocument();

        // Full content should be displayed
        const splitPreview = screen.getByTestId('split-preview-content');
        expect(splitPreview.textContent).toContain('# Regular Markdown');
      });
    });

    describe('Non-Markdown Files', () => {
      it('displays frontmatter for non-markdown files with frontmatter', () => {
        render(
          <ContentPane
            path="test.txt"
            content={contentWithFrontmatter}
            showFrontmatter={true}
          />
        );

        // Frontmatter should be detected and displayed
        expect(screen.getByTestId('frontmatter-display')).toBeInTheDocument();
      });

      it('does not show frontmatter display for plain text without frontmatter', () => {
        render(
          <ContentPane
            path="test.txt"
            content={plainTextContent}
            showFrontmatter={true}
          />
        );

        // No frontmatter display
        expect(screen.queryByTestId('frontmatter-display')).not.toBeInTheDocument();

        // Content should be displayed
        expect(screen.getByText(/This is plain text content/)).toBeInTheDocument();
      });
    });
  });

  describe('Breadcrumb Navigation', () => {
    it('displays file path as breadcrumb', () => {
      render(
        <ContentPane path="src/components/test.tsx" content="content" />
      );

      expect(screen.getByText('src')).toBeInTheDocument();
      expect(screen.getByText('components')).toBeInTheDocument();
      expect(screen.getByText('test.tsx')).toBeInTheDocument();
    });

    it('highlights current file in breadcrumb', () => {
      render(
        <ContentPane path="src/test.tsx" content="content" />
      );

      const currentFile = screen.getByText('test.tsx');
      expect(currentFile).toHaveClass('font-medium');
    });
  });

  describe('Edit Mode', () => {
    it('shows Edit button for editable files when not in readOnly mode', () => {
      render(
        <ContentPane
          path="test.md"
          content="# Test"
          onEditStart={jest.fn()}
          onSave={jest.fn()}
        />
      );

      expect(screen.getByRole('button', { name: /Edit test.md/i })).toBeInTheDocument();
    });

    it('hides Edit button when readOnly is true', () => {
      render(
        <ContentPane
          path="test.md"
          content="# Test"
          readOnly={true}
          onEditStart={jest.fn()}
          onSave={jest.fn()}
        />
      );

      expect(screen.queryByRole('button', { name: /Edit/i })).not.toBeInTheDocument();
    });

    it('hides Edit button for non-editable file types', () => {
      render(
        <ContentPane
          path="test.exe"
          content="binary content"
          onEditStart={jest.fn()}
          onSave={jest.fn()}
        />
      );

      expect(screen.queryByRole('button', { name: /Edit/i })).not.toBeInTheDocument();
    });

    it('calls onEditStart when Edit button is clicked', async () => {
      const user = userEvent.setup();
      const handleEditStart = jest.fn();
      const handleEditChange = jest.fn();

      render(
        <ContentPane
          path="test.md"
          content="# Test"
          onEditStart={handleEditStart}
          onEditChange={handleEditChange}
          onSave={jest.fn()}
        />
      );

      await user.click(screen.getByRole('button', { name: /Edit test.md/i }));

      expect(handleEditStart).toHaveBeenCalled();
      expect(handleEditChange).toHaveBeenCalledWith('# Test');
    });

    it('shows Save and Cancel buttons when in edit mode', () => {
      render(
        <ContentPane
          path="test.md"
          content="# Test"
          isEditing={true}
          editedContent="# Edited"
          onSave={jest.fn()}
          onCancel={jest.fn()}
        />
      );

      expect(screen.getByRole('button', { name: /Save/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument();
    });

    it('calls onCancel when Cancel button is clicked', async () => {
      const user = userEvent.setup();
      const handleCancel = jest.fn();

      render(
        <ContentPane
          path="test.md"
          content="# Test"
          isEditing={true}
          editedContent="# Edited"
          onSave={jest.fn()}
          onCancel={handleCancel}
        />
      );

      await user.click(screen.getByRole('button', { name: /Cancel/i }));

      expect(handleCancel).toHaveBeenCalled();
    });

    it('calls onSave when Save button is clicked', async () => {
      const user = userEvent.setup();
      const handleSave = jest.fn();

      render(
        <ContentPane
          path="test.md"
          content="# Test"
          isEditing={true}
          editedContent="# Edited content"
          onSave={handleSave}
          onCancel={jest.fn()}
        />
      );

      await user.click(screen.getByRole('button', { name: /Save/i }));

      await waitFor(() => {
        expect(handleSave).toHaveBeenCalledWith('# Edited content');
      });
    });
  });

  describe('Truncation Banner', () => {
    it('shows truncation banner when truncationInfo.truncated is true', () => {
      render(
        <ContentPane
          path="large-file.md"
          content="# Truncated content"
          truncationInfo={{
            truncated: true,
            originalSize: 1048576, // 1MB
          }}
        />
      );

      expect(screen.getByText('Large file truncated')).toBeInTheDocument();
      expect(screen.getByText(/1.0 MB/)).toBeInTheDocument();
    });

    it('shows link to full file when fullFileUrl provided', () => {
      render(
        <ContentPane
          path="large-file.md"
          content="# Truncated content"
          truncationInfo={{
            truncated: true,
            originalSize: 2097152,
            fullFileUrl: 'https://github.com/user/repo/blob/main/large-file.md',
          }}
        />
      );

      const link = screen.getByRole('link', { name: /View full file on GitHub/i });
      expect(link).toHaveAttribute(
        'href',
        'https://github.com/user/repo/blob/main/large-file.md'
      );
    });

    it('does not show truncation banner when truncated is false', () => {
      render(
        <ContentPane
          path="normal-file.md"
          content="# Normal content"
          truncationInfo={{
            truncated: false,
          }}
        />
      );

      expect(screen.queryByText('Large file truncated')).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper region role and aria-label', () => {
      render(
        <ContentPane path="test.md" content="# Content" />
      );

      const region = screen.getByRole('region');
      expect(region).toHaveAttribute('aria-label', expect.stringContaining('Markdown file: test.md'));
    });

    it('supports custom ariaLabel', () => {
      render(
        <ContentPane
          path="test.md"
          content="# Content"
          ariaLabel="Custom accessibility label"
        />
      );

      const region = screen.getByRole('region');
      expect(region).toHaveAttribute('aria-label', 'Custom accessibility label');
    });

    it('has accessible breadcrumb navigation', () => {
      render(
        <ContentPane path="src/test.md" content="# Content" />
      );

      const nav = screen.getByRole('navigation', { name: /File path/i });
      expect(nav).toBeInTheDocument();
    });

    it('edit button has descriptive aria-label', () => {
      render(
        <ContentPane
          path="test.md"
          content="# Test"
          onEditStart={jest.fn()}
          onSave={jest.fn()}
        />
      );

      const editButton = screen.getByRole('button', { name: /Edit test.md/i });
      expect(editButton).toBeInTheDocument();
    });
  });

  describe('File Type Detection', () => {
    it('identifies markdown files correctly', () => {
      render(
        <ContentPane path="README.md" content="# Readme" />
      );

      // SplitPreview should be used for markdown
      expect(screen.getByTestId('split-preview')).toBeInTheDocument();
    });

    it('handles .MD extension (case insensitive)', () => {
      render(
        <ContentPane path="FILE.MD" content="# Uppercase Extension" />
      );

      expect(screen.getByTestId('split-preview')).toBeInTheDocument();
    });

    it('identifies non-markdown editable files', () => {
      render(
        <ContentPane
          path="config.json"
          content='{ "key": "value" }'
          onEditStart={jest.fn()}
          onSave={jest.fn()}
        />
      );

      // Should show edit button for JSON
      expect(screen.getByRole('button', { name: /Edit config.json/i })).toBeInTheDocument();
    });

    it('supports various editable extensions', () => {
      const editableExtensions = [
        'test.txt',
        'app.ts',
        'component.tsx',
        'index.js',
        'page.jsx',
        'script.py',
        'config.yml',
        'docker-compose.yaml',
        'settings.toml',
      ];

      editableExtensions.forEach((path) => {
        const { unmount } = render(
          <ContentPane
            path={path}
            content="content"
            onEditStart={jest.fn()}
            onSave={jest.fn()}
          />
        );

        expect(screen.getByRole('button', { name: new RegExp(`Edit ${path}`, 'i') })).toBeInTheDocument();
        unmount();
      });
    });
  });

  describe('Edge Cases', () => {
    it('handles null content gracefully', () => {
      render(
        <ContentPane path="test.txt" content={null} />
      );

      expect(screen.getByText('This file is empty')).toBeInTheDocument();
    });

    it('handles undefined path gracefully', () => {
      render(
        <ContentPane path={undefined as any} content="content" />
      );

      expect(screen.getByText('No file selected')).toBeInTheDocument();
    });

    it('handles malformed frontmatter gracefully', () => {
      const malformedContent = `---
title: Missing closing delimiter
author: Test

# This should still render
`;

      render(
        <ContentPane
          path="test.md"
          content={malformedContent}
          showFrontmatter={true}
        />
      );

      // Should still render without crashing
      expect(screen.getByTestId('split-preview')).toBeInTheDocument();
    });

    it('handles content with only frontmatter', () => {
      const onlyFrontmatter = `---
title: Only Frontmatter
---
`;

      render(
        <ContentPane
          path="test.md"
          content={onlyFrontmatter}
          showFrontmatter={true}
        />
      );

      // Should render frontmatter display
      expect(screen.getByTestId('frontmatter-display')).toBeInTheDocument();

      // Body should be effectively empty (just whitespace after stripping)
      const splitPreview = screen.getByTestId('split-preview-content');
      expect(splitPreview.textContent?.trim()).toBe('');
    });
  });
});
