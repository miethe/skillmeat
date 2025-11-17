"use client";

import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { MarketplaceFilters, ArtifactCategory } from "@/types/marketplace";
import { Filter, X } from "lucide-react";

interface MarketplaceFiltersProps {
  filters: MarketplaceFilters;
  onChange: (filters: Partial<MarketplaceFilters>) => void;
  onReset?: () => void;
}

const ARTIFACT_TYPES: { value: ArtifactCategory; label: string }[] = [
  { value: "skill", label: "Skills" },
  { value: "command", label: "Commands" },
  { value: "agent", label: "Agents" },
  { value: "hook", label: "Hooks" },
  { value: "mcp-server", label: "MCP Servers" },
  { value: "bundle", label: "Bundles" },
];

const LICENSES = ["MIT", "Apache-2.0", "GPL-3.0", "BSD-3-Clause", "ISC", "Other"];

const POPULAR_TAGS = [
  "documentation",
  "productivity",
  "code-review",
  "testing",
  "deployment",
  "analytics",
  "security",
  "database",
];

export function MarketplaceFilters({ filters, onChange, onReset }: MarketplaceFiltersProps) {
  const hasActiveFilters =
    filters.artifact_type ||
    filters.license ||
    filters.publisher ||
    filters.free_only ||
    filters.verified_only ||
    (filters.tags && filters.tags.length > 0);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <CardTitle className="flex items-center gap-2 text-lg font-semibold">
          <Filter className="h-4 w-4" />
          Filters
        </CardTitle>
        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onReset}
            className="h-8 text-sm"
            aria-label="Clear all filters"
          >
            <X className="mr-1 h-3 w-3" />
            Clear
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Artifact Type Filter */}
        <div className="space-y-2">
          <Label htmlFor="artifact-type">Type</Label>
          <select
            id="artifact-type"
            value={filters.artifact_type || ""}
            onChange={(e) =>
              onChange({
                artifact_type: e.target.value ? (e.target.value as ArtifactCategory) : undefined,
              })
            }
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <option value="">All Types</option>
            {ARTIFACT_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
        </div>

        {/* License Filter */}
        <div className="space-y-2">
          <Label htmlFor="license">License</Label>
          <select
            id="license"
            value={filters.license || ""}
            onChange={(e) => onChange({ license: e.target.value || undefined })}
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <option value="">All Licenses</option>
            {LICENSES.map((license) => (
              <option key={license} value={license}>
                {license}
              </option>
            ))}
          </select>
        </div>

        {/* Popular Tags */}
        <div className="space-y-2">
          <Label>Popular Tags</Label>
          <div className="flex flex-wrap gap-2">
            {POPULAR_TAGS.map((tag) => {
              const isSelected = filters.tags?.includes(tag) || false;
              return (
                <button
                  key={tag}
                  onClick={() => {
                    const currentTags = filters.tags || [];
                    const newTags = isSelected
                      ? currentTags.filter((t) => t !== tag)
                      : [...currentTags, tag];
                    onChange({ tags: newTags.length > 0 ? newTags : undefined });
                  }}
                  className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                    isSelected
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
                  }`}
                  aria-pressed={isSelected}
                >
                  {tag}
                </button>
              );
            })}
          </div>
        </div>

        {/* Boolean Filters */}
        <div className="space-y-3">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="free-only"
              checked={filters.free_only || false}
              onCheckedChange={(checked) => onChange({ free_only: checked as boolean })}
            />
            <Label
              htmlFor="free-only"
              className="text-sm font-normal leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
            >
              Free only
            </Label>
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox
              id="verified-only"
              checked={filters.verified_only || false}
              onCheckedChange={(checked) => onChange({ verified_only: checked as boolean })}
            />
            <Label
              htmlFor="verified-only"
              className="text-sm font-normal leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
            >
              Verified publishers only
            </Label>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
