/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SourceCard, SourceCardSkeleton } from '@/components/marketplace/source-card';
import type { GitHubSource, TrustLevel, ScanStatus } from '@/types/marketplace';

// Mock next/navigation
const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

const createMockSource = (overrides?: Partial<GitHubSource>): GitHubSource => ({
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
  ...overrides,
});

describe('SourceCard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders source information correctly', () => {
      const source = createMockSource();
      render(<SourceCard source={source} />);

      expect(screen.getByText('anthropics/skills')).toBeInTheDocument();
      expect(screen.getByText('main')).toBeInTheDocument();
      expect(screen.getByText(/12/)).toBeInTheDocument();
    });

    it('displays owner and repo name', () => {
      const source = createMockSource({
        owner: 'my-org',
        repo_name: 'my-repo',
      });
      render(<SourceCard source={source} />);

      expect(screen.getByText('my-org/my-repo')).toBeInTheDocument();
    });

    it('displays branch/ref information', () => {
      const source = createMockSource({ ref: 'develop' });
      render(<SourceCard source={source} />);

      expect(screen.getByText('develop')).toBeInTheDocument();
    });

    it('displays root hint when provided', () => {
      const source = createMockSource({ root_hint: 'skills/' });
      render(<SourceCard source={source} />);

      expect(screen.getByText(/skills\//)).toBeInTheDocument();
    });

    it('does not display root hint when not provided', () => {
      const source = createMockSource({ root_hint: undefined });
      render(<SourceCard source={source} />);

      // Check that only ref is shown (no "•" separator)
      expect(screen.getByText('main')).toBeInTheDocument();
      expect(screen.queryByText(/•/)).not.toBeInTheDocument();
    });

    it('displays artifact count', () => {
      const source = createMockSource({ artifact_count: 42 });
      render(<SourceCard source={source} />);

      expect(screen.getByText(/Skills: 42/)).toBeInTheDocument();
    });

    it('displays "No artifacts detected" when count is 0', () => {
      const source = createMockSource({ artifact_count: 0 });
      render(<SourceCard source={source} />);

      expect(screen.getByText('No artifacts detected')).toBeInTheDocument();
    });
  });

  describe('Status Badges', () => {
    it('displays "Synced" badge for success status', () => {
      const source = createMockSource({ scan_status: 'success' });
      render(<SourceCard source={source} />);

      expect(screen.getByText('Synced')).toBeInTheDocument();
    });

    it('displays "Pending" badge for pending status', () => {
      const source = createMockSource({ scan_status: 'pending' });
      render(<SourceCard source={source} />);

      expect(screen.getByText('Pending')).toBeInTheDocument();
    });

    it('displays "Scanning" badge for scanning status', () => {
      const source = createMockSource({ scan_status: 'scanning' });
      render(<SourceCard source={source} />);

      expect(screen.getByText('Scanning')).toBeInTheDocument();
    });

    it('displays "Error" badge for error status', () => {
      const source = createMockSource({
        scan_status: 'error',
        last_error: 'Repository not found',
      });
      render(<SourceCard source={source} />);

      expect(screen.getByText('Error')).toBeInTheDocument();
    });
  });

  describe('Trust Level Badges', () => {
    it('displays "Basic" trust level', () => {
      const source = createMockSource({ trust_level: 'basic' });
      render(<SourceCard source={source} />);

      expect(screen.getByText('Basic')).toBeInTheDocument();
    });

    it('displays "Verified" trust level', () => {
      const source = createMockSource({ trust_level: 'verified' });
      render(<SourceCard source={source} />);

      expect(screen.getByText('Verified')).toBeInTheDocument();
    });

    it('displays "Official" trust level', () => {
      const source = createMockSource({ trust_level: 'official' });
      render(<SourceCard source={source} />);

      expect(screen.getByText('Official')).toBeInTheDocument();
    });

    it('displays "Untrusted" trust level', () => {
      const source = createMockSource({ trust_level: 'untrusted' });
      render(<SourceCard source={source} />);

      expect(screen.getByText('Untrusted')).toBeInTheDocument();
    });
  });

  describe('Last Sync Time', () => {
    it('displays formatted last sync time', () => {
      const source = createMockSource({
        last_sync_at: '2024-12-08T10:30:00Z',
      });
      render(<SourceCard source={source} />);

      // Check that a date is displayed (exact format may vary by locale)
      const timeText = screen.getByText(/12\/8\/2024|2024-12-08/);
      expect(timeText).toBeInTheDocument();
    });

    it('displays "Never synced" when last_sync_at is null', () => {
      const source = createMockSource({ last_sync_at: undefined });
      render(<SourceCard source={source} />);

      expect(screen.getByText('Never synced')).toBeInTheDocument();
    });
  });

  describe('Rescan Button', () => {
    it('renders rescan button', () => {
      const source = createMockSource();
      render(<SourceCard source={source} />);

      const rescanButton = screen.getByRole('button', { name: /rescan repository/i });
      expect(rescanButton).toBeInTheDocument();
    });

    it('calls onRescan when clicked', async () => {
      const user = userEvent.setup();
      const mockOnRescan = jest.fn();
      const source = createMockSource();

      render(<SourceCard source={source} onRescan={mockOnRescan} />);

      const rescanButton = screen.getByRole('button', { name: /rescan repository/i });
      await user.click(rescanButton);

      expect(mockOnRescan).toHaveBeenCalledWith('source-123');
    });

    it('does not navigate when rescan button is clicked', async () => {
      const user = userEvent.setup();
      const mockOnRescan = jest.fn();
      const source = createMockSource();

      render(<SourceCard source={source} onRescan={mockOnRescan} />);

      const rescanButton = screen.getByRole('button', { name: /rescan repository/i });
      await user.click(rescanButton);

      expect(mockPush).not.toHaveBeenCalled();
    });

    it('disables rescan button when isRescanning is true', () => {
      const source = createMockSource();
      render(<SourceCard source={source} isRescanning={true} />);

      const rescanButton = screen.getByRole('button', { name: /rescan repository/i });
      expect(rescanButton).toBeDisabled();
    });

    it('disables rescan button when scan_status is scanning', () => {
      const source = createMockSource({ scan_status: 'scanning' });
      render(<SourceCard source={source} />);

      const rescanButton = screen.getByRole('button', { name: /rescan repository/i });
      expect(rescanButton).toBeDisabled();
    });

    it('shows spinning icon when rescanning', () => {
      const source = createMockSource();
      render(<SourceCard source={source} isRescanning={true} />);

      const rescanButton = screen.getByRole('button', { name: /rescan repository/i });
      const icon = rescanButton.querySelector('svg');
      expect(icon).toHaveClass('animate-spin');
    });

    it('shows spinning icon when scan_status is scanning', () => {
      const source = createMockSource({ scan_status: 'scanning' });
      render(<SourceCard source={source} />);

      const rescanButton = screen.getByRole('button', { name: /rescan repository/i });
      const icon = rescanButton.querySelector('svg');
      expect(icon).toHaveClass('animate-spin');
    });
  });

  describe('Navigation', () => {
    it('navigates to detail page when card is clicked', async () => {
      const user = userEvent.setup();
      const source = createMockSource();

      render(<SourceCard source={source} />);

      const card = screen.getByRole('button', { name: /view source: anthropics\/skills/i });
      await user.click(card);

      expect(mockPush).toHaveBeenCalledWith('/marketplace/sources/source-123');
    });

    it('navigates to detail page when Open button is clicked', async () => {
      const user = userEvent.setup();
      const source = createMockSource();

      render(<SourceCard source={source} />);

      const openButton = screen.getByRole('button', { name: /view source details/i });
      await user.click(openButton);

      expect(mockPush).toHaveBeenCalledWith('/marketplace/sources/source-123');
    });

    it('navigates when Enter key is pressed', async () => {
      const user = userEvent.setup();
      const source = createMockSource();

      render(<SourceCard source={source} />);

      const card = screen.getByRole('button', { name: /view source: anthropics\/skills/i });
      card.focus();
      await user.keyboard('{Enter}');

      expect(mockPush).toHaveBeenCalledWith('/marketplace/sources/source-123');
    });

    it('navigates when Space key is pressed', async () => {
      const user = userEvent.setup();
      const source = createMockSource();

      render(<SourceCard source={source} />);

      const card = screen.getByRole('button', { name: /view source: anthropics\/skills/i });
      card.focus();
      await user.keyboard(' ');

      expect(mockPush).toHaveBeenCalledWith('/marketplace/sources/source-123');
    });

    it('calls custom onClick handler when provided', async () => {
      const user = userEvent.setup();
      const mockOnClick = jest.fn();
      const source = createMockSource();

      render(<SourceCard source={source} onClick={mockOnClick} />);

      const card = screen.getByRole('button', { name: /view source: anthropics\/skills/i });
      await user.click(card);

      expect(mockOnClick).toHaveBeenCalled();
      expect(mockPush).not.toHaveBeenCalled();
    });
  });

  describe('Accessibility', () => {
    it('has proper role and tabindex', () => {
      const source = createMockSource();
      render(<SourceCard source={source} />);

      const card = screen.getByRole('button', { name: /view source: anthropics\/skills/i });
      expect(card).toHaveAttribute('tabindex', '0');
    });

    it('has accessible label for card', () => {
      const source = createMockSource({
        owner: 'test-owner',
        repo_name: 'test-repo',
      });
      render(<SourceCard source={source} />);

      expect(
        screen.getByRole('button', { name: 'View source: test-owner/test-repo' })
      ).toBeInTheDocument();
    });

    it('has accessible label for rescan button', () => {
      const source = createMockSource();
      render(<SourceCard source={source} />);

      expect(
        screen.getByRole('button', { name: 'Rescan repository' })
      ).toBeInTheDocument();
    });

    it('has accessible label for open button', () => {
      const source = createMockSource();
      render(<SourceCard source={source} />);

      expect(
        screen.getByRole('button', { name: 'View source details' })
      ).toBeInTheDocument();
    });

    it('has screen reader text for rescan button', () => {
      const source = createMockSource();
      render(<SourceCard source={source} />);

      const srText = screen.getByText('Rescan');
      expect(srText).toHaveClass('sr-only');
    });
  });

  describe('Visual Styling', () => {
    it('has hover effect classes', () => {
      const source = createMockSource();
      render(<SourceCard source={source} />);

      const card = screen.getByRole('button', { name: /view source: anthropics\/skills/i });
      expect(card).toHaveClass('hover:shadow-md');
    });

    it('has blue accent border', () => {
      const source = createMockSource();
      render(<SourceCard source={source} />);

      const card = screen.getByRole('button', { name: /view source: anthropics\/skills/i });
      expect(card).toHaveClass('border-l-blue-500');
    });

    it('has transition classes', () => {
      const source = createMockSource();
      render(<SourceCard source={source} />);

      const card = screen.getByRole('button', { name: /view source: anthropics\/skills/i });
      expect(card).toHaveClass('transition-shadow');
    });
  });

  describe('Edge Cases', () => {
    it('handles very long repository names', () => {
      const source = createMockSource({
        owner: 'very-long-organization-name',
        repo_name: 'very-long-repository-name-that-might-overflow',
      });
      render(<SourceCard source={source} />);

      expect(
        screen.getByText(
          'very-long-organization-name/very-long-repository-name-that-might-overflow'
        )
      ).toBeInTheDocument();
    });

    it('handles missing optional props', () => {
      const source = createMockSource();
      render(<SourceCard source={source} />);

      // Should render without errors
      expect(screen.getByText('anthropics/skills')).toBeInTheDocument();
    });

    it('handles all props being undefined except required', () => {
      const source = createMockSource({
        last_sync_at: undefined,
        last_error: undefined,
        root_hint: undefined,
      });
      render(<SourceCard source={source} />);

      expect(screen.getByText('Never synced')).toBeInTheDocument();
    });
  });

  describe('Error Display', () => {
    it('shows error in tooltip when scan_status is error', async () => {
      const user = userEvent.setup();
      const source = createMockSource({
        scan_status: 'error',
        last_error: 'Repository not accessible',
      });
      render(<SourceCard source={source} />);

      const errorBadge = screen.getByText('Error');

      // Hover to show tooltip
      await user.hover(errorBadge);

      await waitFor(() => {
        expect(screen.getByText('Repository not accessible')).toBeInTheDocument();
      });
    });
  });
});

describe('SourceCardSkeleton', () => {
  it('renders skeleton loader', () => {
    render(<SourceCardSkeleton />);

    // Check for skeleton elements
    const skeletons = screen.getAllByTestId(/loading-skeleton/i);
    // Should have multiple skeleton elements
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('matches card structure', () => {
    const { container } = render(<SourceCardSkeleton />);

    // Should have card-like structure
    expect(container.querySelector('.border-l-4')).toBeInTheDocument();
  });
});
