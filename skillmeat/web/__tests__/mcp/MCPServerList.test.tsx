/**
 * Tests for MCPServerList component
 *
 * Tests the MCP server list display with filtering and search functionality
 */

import { render, screen, fireEvent, within } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MCPServerList } from '@/components/mcp/MCPServerList';
import type { MCPServer } from '@/types/mcp';

// Mock the MCPServerCard component
jest.mock('@/components/mcp/MCPServerCard', () => ({
  MCPServerCard: ({ server, onClick }: any) => (
    <div data-testid={`server-card-${server.name}`} onClick={onClick}>
      {server.name}
    </div>
  ),
}));

describe('MCPServerList', () => {
  const mockServers: MCPServer[] = [
    {
      name: 'filesystem',
      repo: 'anthropics/mcp-filesystem',
      version: 'latest',
      description: 'File system access server',
      env_vars: { ROOT_PATH: '/home/user' },
      status: 'installed',
      installed_at: '2025-01-15T10:00:00Z',
    },
    {
      name: 'git',
      repo: 'anthropics/mcp-git',
      version: 'v1.0.0',
      description: 'Git operations server',
      env_vars: {},
      status: 'not_installed',
    },
    {
      name: 'database',
      repo: 'user/mcp-database',
      version: 'latest',
      env_vars: {},
      status: 'error',
    },
  ];

  const defaultProps = {
    servers: mockServers,
    onServerClick: jest.fn(),
    onAddServer: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders server list with all servers', () => {
      render(<MCPServerList {...defaultProps} />);

      expect(screen.getByTestId('server-card-filesystem')).toBeInTheDocument();
      expect(screen.getByTestId('server-card-git')).toBeInTheDocument();
      expect(screen.getByTestId('server-card-database')).toBeInTheDocument();
    });

    it('renders loading state', () => {
      render(<MCPServerList {...defaultProps} isLoading={true} />);

      // Should show skeleton loaders
      expect(screen.queryByTestId('server-card-filesystem')).not.toBeInTheDocument();
    });

    it('renders empty state when no servers', () => {
      render(<MCPServerList {...defaultProps} servers={[]} />);

      expect(screen.getByText(/No MCP servers configured/i)).toBeInTheDocument();
      expect(screen.getByText(/Get started by adding/i)).toBeInTheDocument();
    });

    it('shows Add Server button', () => {
      render(<MCPServerList {...defaultProps} />);

      const addButtons = screen.getAllByText(/Add Server/i);
      expect(addButtons.length).toBeGreaterThan(0);
    });

    it('shows Refresh button when onRefresh provided', () => {
      const onRefresh = jest.fn();
      render(<MCPServerList {...defaultProps} onRefresh={onRefresh} />);

      expect(screen.getByText(/Refresh/i)).toBeInTheDocument();
    });
  });

  describe('Search Functionality', () => {
    it('filters servers by name', () => {
      render(<MCPServerList {...defaultProps} />);

      const searchInput = screen.getByPlaceholderText(/Search servers/i);
      fireEvent.change(searchInput, { target: { value: 'git' } });

      expect(screen.getByTestId('server-card-git')).toBeInTheDocument();
      expect(screen.queryByTestId('server-card-filesystem')).not.toBeInTheDocument();
      expect(screen.queryByTestId('server-card-database')).not.toBeInTheDocument();
    });

    it('filters servers by repository', () => {
      render(<MCPServerList {...defaultProps} />);

      const searchInput = screen.getByPlaceholderText(/Search servers/i);
      fireEvent.change(searchInput, { target: { value: 'anthropics' } });

      expect(screen.getByTestId('server-card-filesystem')).toBeInTheDocument();
      expect(screen.getByTestId('server-card-git')).toBeInTheDocument();
      expect(screen.queryByTestId('server-card-database')).not.toBeInTheDocument();
    });

    it('filters servers by description', () => {
      render(<MCPServerList {...defaultProps} />);

      const searchInput = screen.getByPlaceholderText(/Search servers/i);
      fireEvent.change(searchInput, { target: { value: 'File system' } });

      expect(screen.getByTestId('server-card-filesystem')).toBeInTheDocument();
      expect(screen.queryByTestId('server-card-git')).not.toBeInTheDocument();
    });

    it('shows empty state when no search results', () => {
      render(<MCPServerList {...defaultProps} />);

      const searchInput = screen.getByPlaceholderText(/Search servers/i);
      fireEvent.change(searchInput, { target: { value: 'nonexistent' } });

      expect(screen.getByText(/No servers found/i)).toBeInTheDocument();
      expect(screen.getByText(/Try adjusting your filters/i)).toBeInTheDocument();
    });
  });

  describe('Status Filtering', () => {
    it('filters servers by installed status', () => {
      render(<MCPServerList {...defaultProps} />);

      // Find and click the status filter
      const statusFilter = screen.getByRole('combobox');
      fireEvent.click(statusFilter);

      // Select "Installed" option
      const installedOption = screen.getByRole('option', { name: /Installed/i });
      fireEvent.click(installedOption);

      expect(screen.getByTestId('server-card-filesystem')).toBeInTheDocument();
      expect(screen.queryByTestId('server-card-git')).not.toBeInTheDocument();
    });

    it('filters servers by not_installed status', () => {
      render(<MCPServerList {...defaultProps} />);

      const statusFilter = screen.getByRole('combobox');
      fireEvent.click(statusFilter);

      const notInstalledOption = screen.getByRole('option', {
        name: /Not Installed/i,
      });
      fireEvent.click(notInstalledOption);

      expect(screen.getByTestId('server-card-git')).toBeInTheDocument();
      expect(screen.queryByTestId('server-card-filesystem')).not.toBeInTheDocument();
    });

    it('filters servers by error status', () => {
      render(<MCPServerList {...defaultProps} />);

      const statusFilter = screen.getByRole('combobox');
      fireEvent.click(statusFilter);

      const errorOption = screen.getByRole('option', { name: /Error/i });
      fireEvent.click(errorOption);

      expect(screen.getByTestId('server-card-database')).toBeInTheDocument();
      expect(screen.queryByTestId('server-card-filesystem')).not.toBeInTheDocument();
    });
  });

  describe('User Interactions', () => {
    it('calls onServerClick when server is clicked', () => {
      render(<MCPServerList {...defaultProps} />);

      const serverCard = screen.getByTestId('server-card-filesystem');
      fireEvent.click(serverCard);

      expect(defaultProps.onServerClick).toHaveBeenCalledWith(mockServers[0]);
    });

    it('calls onAddServer when Add Server button is clicked', () => {
      render(<MCPServerList {...defaultProps} />);

      const addButton = screen.getAllByText(/Add Server/i)[0];
      fireEvent.click(addButton);

      expect(defaultProps.onAddServer).toHaveBeenCalled();
    });

    it('calls onRefresh when Refresh button is clicked', () => {
      const onRefresh = jest.fn();
      render(<MCPServerList {...defaultProps} onRefresh={onRefresh} />);

      const refreshButton = screen.getByText(/Refresh/i);
      fireEvent.click(refreshButton);

      expect(onRefresh).toHaveBeenCalled();
    });
  });

  describe('Combined Filters', () => {
    it('applies both search and status filters', () => {
      render(<MCPServerList {...defaultProps} />);

      // Apply search filter
      const searchInput = screen.getByPlaceholderText(/Search servers/i);
      fireEvent.change(searchInput, { target: { value: 'anthropics' } });

      // Apply status filter
      const statusFilter = screen.getByRole('combobox');
      fireEvent.click(statusFilter);
      const installedOption = screen.getByRole('option', { name: /Installed/i });
      fireEvent.click(installedOption);

      // Should only show filesystem (anthropics + installed)
      expect(screen.getByTestId('server-card-filesystem')).toBeInTheDocument();
      expect(screen.queryByTestId('server-card-git')).not.toBeInTheDocument();
      expect(screen.queryByTestId('server-card-database')).not.toBeInTheDocument();
    });
  });

  describe('Results Count', () => {
    it('shows correct count when all servers visible', () => {
      render(<MCPServerList {...defaultProps} />);

      expect(screen.getByText(/Showing 3 of 3 servers/i)).toBeInTheDocument();
    });

    it('shows correct count when filters applied', () => {
      render(<MCPServerList {...defaultProps} />);

      const searchInput = screen.getByPlaceholderText(/Search servers/i);
      fireEvent.change(searchInput, { target: { value: 'git' } });

      expect(screen.getByText(/Showing 1 of 3 servers/i)).toBeInTheDocument();
    });
  });
});
