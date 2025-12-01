'use client';

import { useState } from 'react';
import { Server, Search, Filter, Plus, RefreshCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { MCPServer, MCPServerFilters, MCPServerStatus } from '@/types/mcp';
import { MCPServerCard } from './MCPServerCard';

interface MCPServerListProps {
  servers: MCPServer[];
  isLoading?: boolean;
  onServerClick: (server: MCPServer) => void;
  onAddServer: () => void;
  onRefresh?: () => void;
}

function MCPServerListSkeleton() {
  return (
    <div className="space-y-4">
      {[...Array(3)].map((_, i) => (
        <div key={i} className="rounded-lg border p-4">
          <div className="space-y-3">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-4 w-full" />
            <div className="flex gap-2">
              <Skeleton className="h-6 w-20" />
              <Skeleton className="h-6 w-24" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export function MCPServerList({
  servers,
  isLoading,
  onServerClick,
  onAddServer,
  onRefresh,
}: MCPServerListProps) {
  const [filters, setFilters] = useState<MCPServerFilters>({
    status: 'all',
    search: '',
  });

  // Filter servers
  const filteredServers = servers.filter((server) => {
    // Status filter
    if (filters.status !== 'all' && server.status !== filters.status) {
      return false;
    }

    // Search filter (name, description, repo)
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      const matchesName = server.name.toLowerCase().includes(searchLower);
      const matchesRepo = server.repo.toLowerCase().includes(searchLower);
      const matchesDescription = server.description?.toLowerCase().includes(searchLower) || false;

      if (!matchesName && !matchesRepo && !matchesDescription) {
        return false;
      }
    }

    return true;
  });

  const handleSearchChange = (value: string) => {
    setFilters((prev) => ({ ...prev, search: value }));
  };

  const handleStatusFilterChange = (value: string) => {
    setFilters((prev) => ({
      ...prev,
      status: value as MCPServerStatus | 'all',
    }));
  };

  if (isLoading) {
    return <MCPServerListSkeleton />;
  }

  return (
    <div className="space-y-4">
      {/* Header with filters */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-1 items-center gap-2">
          <div className="relative max-w-sm flex-1">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search servers..."
              value={filters.search}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="pl-8"
            />
          </div>

          <div className="w-[150px]">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <Select value={filters.status} onValueChange={handleStatusFilterChange}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Filter by status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="installed">Installed</SelectItem>
                  <SelectItem value="not_installed">Not Installed</SelectItem>
                  <SelectItem value="updating">Updating</SelectItem>
                  <SelectItem value="error">Error</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {onRefresh && (
            <Button variant="outline" size="sm" onClick={onRefresh} disabled={isLoading}>
              <RefreshCcw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
          )}
          <Button onClick={onAddServer}>
            <Plus className="mr-2 h-4 w-4" />
            Add Server
          </Button>
        </div>
      </div>

      {/* Empty state */}
      {filteredServers.length === 0 && !isLoading && (
        <div className="rounded-lg border py-12 text-center">
          <Server className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
          <h3 className="mb-2 text-lg font-semibold">
            {filters.search || filters.status !== 'all'
              ? 'No servers found'
              : 'No MCP servers configured'}
          </h3>
          <p className="mb-4 text-sm text-muted-foreground">
            {filters.search || filters.status !== 'all'
              ? 'Try adjusting your filters'
              : 'Get started by adding your first MCP server'}
          </p>
          {!filters.search && filters.status === 'all' && (
            <Button onClick={onAddServer}>
              <Plus className="mr-2 h-4 w-4" />
              Add MCP Server
            </Button>
          )}
        </div>
      )}

      {/* Server cards grid */}
      {filteredServers.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredServers.map((server) => (
            <MCPServerCard
              key={server.name}
              server={server}
              onClick={() => onServerClick(server)}
            />
          ))}
        </div>
      )}

      {/* Results count */}
      {filteredServers.length > 0 && (
        <div className="text-center text-sm text-muted-foreground">
          Showing {filteredServers.length} of {servers.length} server
          {servers.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
}
