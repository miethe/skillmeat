/**
 * @jest-environment jsdom
 *
 * RepoDetailsModal Component Tests
 *
 * Tests for the RepoDetailsModal component which displays repository
 * description and README content in a modal dialog.
 *
 * Note: Radix Dialog requires a container element for portals.
 * Complex dialog interactions are better tested in E2E tests.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RepoDetailsModal } from '@/components/marketplace/repo-details-modal';
import type { GitHubSource, TrustLevel, ScanStatus } from '@/types/marketplace';

// Mock react-markdown to avoid complex rendering in tests
jest.mock('react-markdown', () => {
  return function MockReactMarkdown({ children }: { children: string }) {
    return <div data-testid="markdown-content">{children}</div>;
  };
});

jest.mock('remark-gfm', () => () => {});

// Set up DOM element for dialog portal
beforeAll(() => {
  const portalRoot = document.createElement('div');
  portalRoot.setAttribute('id', 'radix-portal');
  document.body.appendChild(portalRoot);
});

afterAll(() => {
  const portalRoot = document.getElementById('radix-portal');
  if (portalRoot) {
    document.body.removeChild(portalRoot);
  }
});

const createMockSource = (
  overrides?: Partial<GitHubSource & { readme_content?: string }>
): GitHubSource & { readme_content?: string } => ({
  id: 'source-123',
  repo_url: 'https://github.com/anthropics/skills',
  owner: 'anthropics',
  repo_name: 'skills',
  ref: 'main',
  root_hint: undefined,
  trust_level: 'basic' as TrustLevel,
  visibility: 'public',
  scan_status: 'success' as ScanStatus,
  artifact_count: 12,
  last_sync_at: '2024-12-01T10:00:00Z',
  last_error: undefined,
  created_at: '2024-11-01T10:00:00Z',
  updated_at: '2024-12-01T10:00:00Z',
  description: 'A collection of useful Claude Code skills',
  ...overrides,
});

describe('RepoDetailsModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: jest.fn(),
    source: createMockSource(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Opening and Closing', () => {
    it('renders when isOpen is true', async () => {
      render(<RepoDetailsModal {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });
    });

    it('does not render when isOpen is false', () => {
      render(<RepoDetailsModal {...defaultProps} isOpen={false} />);

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('calls onClose when close button is clicked', async () => {
      const user = userEvent.setup();
      const onClose = jest.fn();

      render(<RepoDetailsModal {...defaultProps} onClose={onClose} />);

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Find close button (typically has an X icon in Radix Dialog)
      const closeButton = screen.getByRole('button', { name: /close/i });
      await user.click(closeButton);

      expect(onClose).toHaveBeenCalled();
    });

    it('closes on Escape key press', async () => {
      const user = userEvent.setup();
      const onClose = jest.fn();

      render(<RepoDetailsModal {...defaultProps} onClose={onClose} />);

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      await user.keyboard('{Escape}');

      expect(onClose).toHaveBeenCalled();
    });
  });

  describe('Title Display', () => {
    it('displays owner/repo_name as title', async () => {
      render(<RepoDetailsModal {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: 'anthropics/skills' })).toBeInTheDocument();
      });
    });

    it('displays custom owner/repo in title', async () => {
      const source = createMockSource({
        owner: 'my-org',
        repo_name: 'my-repo',
      });

      render(<RepoDetailsModal {...defaultProps} source={source} />);

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: 'my-org/my-repo' })).toBeInTheDocument();
      });
    });
  });

  describe('Description Display', () => {
    it('displays user-provided description', async () => {
      const source = createMockSource({
        description: 'This is a user description',
      });

      render(<RepoDetailsModal {...defaultProps} source={source} />);

      await waitFor(() => {
        expect(screen.getByText('This is a user description')).toBeInTheDocument();
      });
    });

    it('displays repo_description as fallback when no user description', async () => {
      const source = createMockSource({
        description: undefined,
        repo_description: 'GitHub repo description fallback',
      });

      render(<RepoDetailsModal {...defaultProps} source={source} />);

      await waitFor(() => {
        expect(screen.getByText('GitHub repo description fallback')).toBeInTheDocument();
      });
    });

    it('prefers user description over repo_description', async () => {
      const source = createMockSource({
        description: 'User provided',
        repo_description: 'From GitHub',
      });

      render(<RepoDetailsModal {...defaultProps} source={source} />);

      await waitFor(() => {
        expect(screen.getByText('User provided')).toBeInTheDocument();
        expect(screen.queryByText('From GitHub')).not.toBeInTheDocument();
      });
    });
  });

  describe('README Content', () => {
    it('displays README content when available', async () => {
      const source = createMockSource({
        readme_content: '# My README\n\nThis is the content.',
      });

      render(<RepoDetailsModal {...defaultProps} source={source} />);

      await waitFor(() => {
        expect(screen.getByText('README')).toBeInTheDocument();
        expect(screen.getByTestId('markdown-content')).toHaveTextContent('# My README');
      });
    });

    it('shows "No README available" when readme_content is absent', async () => {
      const source = createMockSource({
        description: 'Has description but no readme',
        readme_content: undefined,
      });

      render(<RepoDetailsModal {...defaultProps} source={source} />);

      await waitFor(() => {
        expect(screen.getByText('No README available')).toBeInTheDocument();
      });
    });
  });

  describe('Empty State', () => {
    it('shows empty state when no description and no README', async () => {
      const source = createMockSource({
        description: undefined,
        repo_description: undefined,
        readme_content: undefined,
      });

      render(<RepoDetailsModal {...defaultProps} source={source} />);

      await waitFor(() => {
        expect(screen.getByText('No repository details available')).toBeInTheDocument();
        expect(
          screen.getByText('This repository does not have a description or README content.')
        ).toBeInTheDocument();
      });
    });

    it('does not show empty state when description is present', async () => {
      const source = createMockSource({
        description: 'Has description',
        readme_content: undefined,
      });

      render(<RepoDetailsModal {...defaultProps} source={source} />);

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      expect(screen.queryByText('No repository details available')).not.toBeInTheDocument();
    });

    it('does not show empty state when README is present', async () => {
      const source = createMockSource({
        description: undefined,
        readme_content: '# README',
      });

      render(<RepoDetailsModal {...defaultProps} source={source} />);

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      expect(screen.queryByText('No repository details available')).not.toBeInTheDocument();
    });
  });

  describe('Loading State Handling', () => {
    it('handles source with minimal data', async () => {
      const minimalSource: GitHubSource & { readme_content?: string } = {
        id: 'minimal',
        repo_url: 'https://github.com/user/repo',
        owner: 'user',
        repo_name: 'repo',
        ref: 'main',
        trust_level: 'basic',
        visibility: 'public',
        scan_status: 'pending',
        artifact_count: 0,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };

      render(<RepoDetailsModal isOpen={true} onClose={jest.fn()} source={minimalSource} />);

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: 'user/repo' })).toBeInTheDocument();
        expect(screen.getByText('No repository details available')).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('has accessible dialog with title', async () => {
      render(<RepoDetailsModal {...defaultProps} />);

      await waitFor(() => {
        const dialog = screen.getByRole('dialog');
        expect(dialog).toHaveAttribute('aria-labelledby');
      });
    });
  });

  describe('Edge Cases', () => {
    it('handles very long repository names', async () => {
      const source = createMockSource({
        owner: 'very-long-organization-name-here',
        repo_name: 'extremely-long-repository-name-that-might-cause-issues',
      });

      render(<RepoDetailsModal {...defaultProps} source={source} />);

      await waitFor(() => {
        expect(
          screen.getByRole('heading', {
            name: 'very-long-organization-name-here/extremely-long-repository-name-that-might-cause-issues',
          })
        ).toBeInTheDocument();
      });
    });

    it('handles very long description', async () => {
      const longDescription = 'A'.repeat(1000);
      const source = createMockSource({
        description: longDescription,
      });

      render(<RepoDetailsModal {...defaultProps} source={source} />);

      await waitFor(() => {
        expect(screen.getByText(longDescription)).toBeInTheDocument();
      });
    });

    it('handles special characters in content', async () => {
      const source = createMockSource({
        description: 'Contains <script>alert("xss")</script> and "quotes" & ampersands',
        readme_content: '# Code examples\n\n```python\nprint("hello")\n```',
      });

      render(<RepoDetailsModal {...defaultProps} source={source} />);

      await waitFor(() => {
        expect(
          screen.getByText('Contains <script>alert("xss")</script> and "quotes" & ampersands')
        ).toBeInTheDocument();
      });
    });

    it('handles empty string description', async () => {
      const source = createMockSource({
        description: '',
        repo_description: 'Fallback',
      });

      render(<RepoDetailsModal {...defaultProps} source={source} />);

      await waitFor(() => {
        // Empty string is falsy, so fallback should be used
        expect(screen.getByText('Fallback')).toBeInTheDocument();
      });
    });

    it('handles empty string readme_content', async () => {
      const source = createMockSource({
        description: 'Has description',
        readme_content: '',
      });

      render(<RepoDetailsModal {...defaultProps} source={source} />);

      await waitFor(() => {
        // Empty string is falsy, so "No README available" should show
        expect(screen.getByText('No README available')).toBeInTheDocument();
      });
    });
  });
});
