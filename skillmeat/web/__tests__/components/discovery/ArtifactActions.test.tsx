import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ArtifactActions } from '@/components/discovery/ArtifactActions';
import type { DiscoveredArtifact } from '@/types/discovery';

// Mock the toast notification hook
const mockShowSuccess = jest.fn();
jest.mock('@/hooks/use-toast-notification', () => ({
  useToastNotification: () => ({
    showSuccess: mockShowSuccess,
  }),
}));

describe('ArtifactActions', () => {
  const mockArtifact: DiscoveredArtifact = {
    type: 'skill',
    name: 'test-skill',
    source: 'user/repo/skill',
    path: '/path/to/skill',
    discovered_at: '2024-01-01T00:00:00Z',
  };

  const mockProps = {
    artifact: mockArtifact,
    isSkipped: false,
    onImport: jest.fn(),
    onToggleSkip: jest.fn(),
    onViewDetails: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders trigger button', () => {
    render(<ArtifactActions {...mockProps} />);
    const button = screen.getByRole('button', { name: /actions for test-skill/i });
    expect(button).toBeInTheDocument();
  });

  it('opens menu when trigger is clicked', async () => {
    const user = userEvent.setup();
    render(<ArtifactActions {...mockProps} />);
    const button = screen.getByRole('button', { name: /actions for test-skill/i });

    await user.click(button);

    await waitFor(() => {
      const menu = screen.getByRole('menu');
      expect(within(menu).getByText('Import to Collection')).toBeInTheDocument();
      expect(within(menu).getByText('Skip for future')).toBeInTheDocument();
      expect(within(menu).getByText('View Details')).toBeInTheDocument();
      expect(within(menu).getByText('Copy Source URL')).toBeInTheDocument();
    });
  });

  it('calls onImport when Import action is clicked', async () => {
    const user = userEvent.setup();
    render(<ArtifactActions {...mockProps} />);
    const button = screen.getByRole('button', { name: /actions for test-skill/i });

    await user.click(button);

    const menu = await screen.findByRole('menu');
    const importItem = within(menu).getByRole('menuitem', { name: /import to collection/i });
    await user.click(importItem);

    expect(mockProps.onImport).toHaveBeenCalledTimes(1);
  });

  it('shows "Already imported" when isImported is true', async () => {
    const user = userEvent.setup();
    render(<ArtifactActions {...mockProps} isImported={true} />);
    const button = screen.getByRole('button', { name: /actions for test-skill/i });

    await user.click(button);

    const menu = await screen.findByRole('menu');
    expect(within(menu).getByText('Already imported')).toBeInTheDocument();
  });

  it('calls onToggleSkip with true when Skip action is clicked', async () => {
    const user = userEvent.setup();
    render(<ArtifactActions {...mockProps} />);
    const button = screen.getByRole('button', { name: /actions for test-skill/i });

    await user.click(button);

    const menu = await screen.findByRole('menu');
    const skipItem = within(menu).getByText('Skip for future');
    await user.click(skipItem);

    expect(mockProps.onToggleSkip).toHaveBeenCalledWith(true);
  });

  it('shows "Un-skip" when isSkipped is true', async () => {
    const user = userEvent.setup();
    render(<ArtifactActions {...mockProps} isSkipped={true} />);
    const button = screen.getByRole('button', { name: /actions for test-skill/i });

    await user.click(button);

    const menu = await screen.findByRole('menu');
    expect(within(menu).getByText('Un-skip')).toBeInTheDocument();
  });

  it('calls onToggleSkip with false when Un-skip action is clicked', async () => {
    const user = userEvent.setup();
    render(<ArtifactActions {...mockProps} isSkipped={true} />);
    const button = screen.getByRole('button', { name: /actions for test-skill/i });

    await user.click(button);

    const menu = await screen.findByRole('menu');
    const unskipItem = within(menu).getByText('Un-skip');
    await user.click(unskipItem);

    expect(mockProps.onToggleSkip).toHaveBeenCalledWith(false);
  });

  it('calls onViewDetails when View Details action is clicked', async () => {
    const user = userEvent.setup();
    render(<ArtifactActions {...mockProps} />);
    const button = screen.getByRole('button', { name: /actions for test-skill/i });

    await user.click(button);

    const menu = await screen.findByRole('menu');
    const detailsItem = within(menu).getByText('View Details');
    await user.click(detailsItem);

    expect(mockProps.onViewDetails).toHaveBeenCalledTimes(1);
  });

  it('disables Copy Source URL when source is undefined', async () => {
    const user = userEvent.setup();
    const artifactWithoutSource = { ...mockArtifact, source: undefined };
    render(<ArtifactActions {...mockProps} artifact={artifactWithoutSource} />);
    const button = screen.getByRole('button', { name: /actions for test-skill/i });

    await user.click(button);

    const menu = await screen.findByRole('menu');
    const copyItem = within(menu).getByRole('menuitem', { name: /copy source url/i });
    // Radix UI sets data-disabled="" when disabled is true
    expect(copyItem).toHaveAttribute('data-disabled');
  });

  it('copies source to clipboard when Copy Source URL is clicked', async () => {
    const user = userEvent.setup();
    // Mock clipboard API using defineProperty
    const writeTextMock = jest.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: writeTextMock,
      },
      writable: true,
      configurable: true,
    });

    render(<ArtifactActions {...mockProps} />);
    const button = screen.getByRole('button', { name: /actions for test-skill/i });

    await user.click(button);

    const menu = await screen.findByRole('menu');
    const copyItem = within(menu).getByRole('menuitem', { name: /copy source url/i });
    await user.click(copyItem);

    expect(writeTextMock).toHaveBeenCalledWith(mockArtifact.source);
    expect(mockShowSuccess).toHaveBeenCalledWith('Source URL copied to clipboard');
  });

  it('closes menu after action is performed', async () => {
    const user = userEvent.setup();
    render(<ArtifactActions {...mockProps} />);
    const button = screen.getByRole('button', { name: /actions for test-skill/i });

    // Open menu
    await user.click(button);
    const menu = await screen.findByRole('menu');
    expect(menu).toBeInTheDocument();

    // Click an action
    const importItem = within(menu).getByRole('menuitem', { name: /import to collection/i });
    await user.click(importItem);

    // Menu should close
    await waitFor(() => {
      expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    });
  });
});
