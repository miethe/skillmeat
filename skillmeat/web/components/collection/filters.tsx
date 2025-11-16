"use client";

import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import type {
  ArtifactFilters,
  ArtifactSort,
  SortField,
  SortOrder,
} from "@/types/artifact";

interface FiltersProps {
  filters: ArtifactFilters;
  sort: ArtifactSort;
  onFiltersChange: (filters: ArtifactFilters) => void;
  onSortChange: (sort: ArtifactSort) => void;
}

export function Filters({
  filters,
  sort,
  onFiltersChange,
  onSortChange,
}: FiltersProps) {
  const handleFilterChange = (key: keyof ArtifactFilters, value: string) => {
    onFiltersChange({
      ...filters,
      [key]: value === "all" ? undefined : value,
    });
  };

  const handleSortFieldChange = (field: string) => {
    onSortChange({
      ...sort,
      field: field as SortField,
    });
  };

  const handleSortOrderChange = (order: string) => {
    onSortChange({
      ...sort,
      order: order as SortOrder,
    });
  };

  return (
    <div className="space-y-4">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search artifacts by name, description, or tags..."
          value={filters.search || ""}
          onChange={(e) => handleFilterChange("search", e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Filter Controls */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        {/* Type Filter */}
        <div>
          <label
            htmlFor="type-filter"
            className="block text-sm font-medium mb-1.5"
          >
            Type
          </label>
          <Select
            id="type-filter"
            value={filters.type || "all"}
            onChange={(e) => handleFilterChange("type", e.target.value)}
          >
            <option value="all">All Types</option>
            <option value="skill">Skills</option>
            <option value="command">Commands</option>
            <option value="agent">Agents</option>
            <option value="mcp">MCP Servers</option>
            <option value="hook">Hooks</option>
          </Select>
        </div>

        {/* Status Filter */}
        <div>
          <label
            htmlFor="status-filter"
            className="block text-sm font-medium mb-1.5"
          >
            Status
          </label>
          <Select
            id="status-filter"
            value={filters.status || "all"}
            onChange={(e) => handleFilterChange("status", e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="active">Active</option>
            <option value="outdated">Outdated</option>
            <option value="conflict">Conflict</option>
            <option value="error">Error</option>
          </Select>
        </div>

        {/* Scope Filter */}
        <div>
          <label
            htmlFor="scope-filter"
            className="block text-sm font-medium mb-1.5"
          >
            Scope
          </label>
          <Select
            id="scope-filter"
            value={filters.scope || "all"}
            onChange={(e) => handleFilterChange("scope", e.target.value)}
          >
            <option value="all">All Scopes</option>
            <option value="user">User (Global)</option>
            <option value="local">Local (Project)</option>
          </Select>
        </div>

        {/* Sort Controls */}
        <div>
          <label
            htmlFor="sort-field"
            className="block text-sm font-medium mb-1.5"
          >
            Sort By
          </label>
          <div className="flex gap-2">
            <Select
              id="sort-field"
              value={sort.field}
              onChange={(e) => handleSortFieldChange(e.target.value)}
              className="flex-1"
            >
              <option value="name">Name</option>
              <option value="updatedAt">Last Updated</option>
              <option value="usageCount">Usage Count</option>
            </Select>
            <Select
              id="sort-order"
              value={sort.order}
              onChange={(e) => handleSortOrderChange(e.target.value)}
              aria-label="Sort order"
            >
              <option value="asc">A-Z</option>
              <option value="desc">Z-A</option>
            </Select>
          </div>
        </div>
      </div>
    </div>
  );
}
