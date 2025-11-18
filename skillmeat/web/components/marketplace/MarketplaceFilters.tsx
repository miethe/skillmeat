"use client";

import { useState } from "react";
import { Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { MarketplaceFilters } from "@/types/marketplace";

interface MarketplaceFiltersProps {
  filters: MarketplaceFilters;
  onFiltersChange: (filters: MarketplaceFilters) => void;
  brokers?: Array<{ name: string; enabled: boolean }>;
}

const COMMON_LICENSES = [
  "MIT",
  "Apache-2.0",
  "GPL-3.0",
  "BSD-3-Clause",
  "ISC",
  "MPL-2.0",
  "LGPL-3.0",
  "Unknown",
];

const COMMON_TAGS = [
  "testing",
  "python",
  "javascript",
  "documentation",
  "productivity",
  "code-review",
  "database",
  "api",
  "automation",
  "security",
];

export function MarketplaceFilters({
  filters,
  onFiltersChange,
  brokers = [],
}: MarketplaceFiltersProps) {
  const [tagInput, setTagInput] = useState("");

  const handleFilterChange = (key: keyof MarketplaceFilters, value: any) => {
    onFiltersChange({
      ...filters,
      [key]: value === "all" || value === "" ? undefined : value,
    });
  };

  const handleAddTag = (tag: string) => {
    const trimmedTag = tag.trim().toLowerCase();
    if (!trimmedTag) return;

    const currentTags = filters.tags || [];
    if (currentTags.includes(trimmedTag)) return;

    onFiltersChange({
      ...filters,
      tags: [...currentTags, trimmedTag],
    });
    setTagInput("");
  };

  const handleRemoveTag = (tagToRemove: string) => {
    const currentTags = filters.tags || [];
    onFiltersChange({
      ...filters,
      tags: currentTags.filter((tag) => tag !== tagToRemove),
    });
  };

  const handleClearAll = () => {
    onFiltersChange({});
    setTagInput("");
  };

  // Count active filters
  const activeFilterCount = Object.values(filters).filter(
    (value) => value !== undefined && value !== "" && (!Array.isArray(value) || value.length > 0)
  ).length;

  const enabledBrokers = brokers.filter((b) => b.enabled);

  return (
    <div className="space-y-4">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search marketplace listings..."
          value={filters.query || ""}
          onChange={(e) => handleFilterChange("query", e.target.value)}
          className="pl-9"
          aria-label="Search marketplace"
        />
      </div>

      {/* Filter Controls */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Broker Filter */}
        {enabledBrokers.length > 0 && (
          <div>
            <label
              htmlFor="broker-filter"
              className="block text-sm font-medium mb-1.5"
            >
              Broker
            </label>
            <Select
              id="broker-filter"
              value={filters.broker || "all"}
              onChange={(e) => handleFilterChange("broker", e.target.value)}
            >
              <option value="all">All Brokers</option>
              {enabledBrokers.map((broker) => (
                <option key={broker.name} value={broker.name}>
                  {broker.name}
                </option>
              ))}
            </Select>
          </div>
        )}

        {/* License Filter */}
        <div>
          <label
            htmlFor="license-filter"
            className="block text-sm font-medium mb-1.5"
          >
            License
          </label>
          <Select
            id="license-filter"
            value={filters.license || "all"}
            onChange={(e) => handleFilterChange("license", e.target.value)}
          >
            <option value="all">All Licenses</option>
            {COMMON_LICENSES.map((license) => (
              <option key={license} value={license}>
                {license}
              </option>
            ))}
          </Select>
        </div>

        {/* Publisher Filter */}
        <div>
          <label
            htmlFor="publisher-filter"
            className="block text-sm font-medium mb-1.5"
          >
            Publisher
          </label>
          <Input
            id="publisher-filter"
            placeholder="Filter by publisher..."
            value={filters.publisher || ""}
            onChange={(e) => handleFilterChange("publisher", e.target.value)}
          />
        </div>
      </div>

      {/* Tags */}
      <div>
        <label
          htmlFor="tag-input"
          className="block text-sm font-medium mb-1.5"
        >
          Tags
        </label>
        <div className="flex gap-2 mb-2">
          <Input
            id="tag-input"
            placeholder="Add tag..."
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleAddTag(tagInput);
              }
            }}
          />
          <Button
            type="button"
            variant="outline"
            onClick={() => handleAddTag(tagInput)}
            disabled={!tagInput.trim()}
          >
            Add
          </Button>
        </div>

        {/* Selected Tags */}
        {filters.tags && filters.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {filters.tags.map((tag) => (
              <Badge key={tag} variant="secondary" className="gap-1">
                {tag}
                <button
                  onClick={() => handleRemoveTag(tag)}
                  className="hover:text-destructive focus:outline-none focus:ring-2 focus:ring-ring rounded-full"
                  aria-label={`Remove tag: ${tag}`}
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
          </div>
        )}

        {/* Suggested Tags */}
        <div className="flex flex-wrap gap-1.5">
          {COMMON_TAGS.filter(
            (tag) => !filters.tags?.includes(tag)
          ).slice(0, 8).map((tag) => (
            <Badge
              key={tag}
              variant="outline"
              className="cursor-pointer hover:bg-secondary"
              onClick={() => handleAddTag(tag)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  handleAddTag(tag);
                }
              }}
            >
              {tag}
            </Badge>
          ))}
        </div>
      </div>

      {/* Clear Filters */}
      {activeFilterCount > 0 && (
        <div className="flex items-center justify-between pt-2 border-t">
          <span className="text-sm text-muted-foreground">
            {activeFilterCount} {activeFilterCount === 1 ? "filter" : "filters"} active
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClearAll}
            aria-label="Clear all filters"
          >
            Clear all
          </Button>
        </div>
      )}
    </div>
  );
}
