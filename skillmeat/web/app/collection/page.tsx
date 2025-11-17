"use client";

import { useState } from "react";
import { LayoutGrid, List } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Filters } from "@/components/collection/filters";
import { ArtifactGrid } from "@/components/collection/artifact-grid";
import { ArtifactList } from "@/components/collection/artifact-list";
import { ArtifactDetail } from "@/components/collection/artifact-detail";
import { useArtifacts } from "@/hooks/useArtifacts";
import type {
  Artifact,
  ArtifactFilters,
  ArtifactSort,
} from "@/types/artifact";

type ViewMode = "grid" | "list";

export default function CollectionPage() {
  // View state
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(
    null
  );
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  // Filter and sort state
  const [filters, setFilters] = useState<ArtifactFilters>({});
  const [sort, setSort] = useState<ArtifactSort>({
    field: "name",
    order: "asc",
  });

  // Fetch artifacts with React Query
  const { data, isLoading, error } = useArtifacts(filters, sort);

  const handleArtifactClick = (artifact: Artifact) => {
    setSelectedArtifact(artifact);
    setIsDetailOpen(true);
  };

  const handleDetailClose = () => {
    setIsDetailOpen(false);
    // Keep selectedArtifact for a moment to avoid flickering
    setTimeout(() => setSelectedArtifact(null), 300);
  };

  // Calculate active filter count
  const activeFilterCount = Object.values(filters).filter(
    (value) => value !== undefined && value !== "all" && value !== ""
  ).length;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Collection</h1>
        <p className="text-muted-foreground">
          Browse and manage your artifact collection
        </p>
      </div>

      {/* Filters */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="font-semibold">Filters</h2>
            {activeFilterCount > 0 && (
              <Badge variant="secondary">{activeFilterCount} active</Badge>
            )}
          </div>
          {activeFilterCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setFilters({})}
              aria-label="Clear all filters"
            >
              Clear all
            </Button>
          )}
        </div>
        <Filters
          filters={filters}
          sort={sort}
          onFiltersChange={setFilters}
          onSortChange={setSort}
        />
      </div>

      {/* Results Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="font-semibold">
            {isLoading ? (
              "Loading..."
            ) : error ? (
              "Error loading artifacts"
            ) : (
              <>
                {data?.total || 0}{" "}
                {data?.total === 1 ? "Artifact" : "Artifacts"}
              </>
            )}
          </h2>
        </div>

        {/* View Toggle */}
        <div
          className="flex items-center gap-1 border rounded-md p-1"
          role="group"
          aria-label="View mode"
        >
          <Button
            variant={viewMode === "grid" ? "secondary" : "ghost"}
            size="sm"
            onClick={() => setViewMode("grid")}
            aria-label="Grid view"
            aria-pressed={viewMode === "grid"}
          >
            <LayoutGrid className="h-4 w-4" />
          </Button>
          <Button
            variant={viewMode === "list" ? "secondary" : "ghost"}
            size="sm"
            onClick={() => setViewMode("list")}
            aria-label="List view"
            aria-pressed={viewMode === "list"}
          >
            <List className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
          <p className="text-sm text-destructive">
            Failed to load artifacts. Please try again later.
          </p>
        </div>
      )}

      {/* Artifacts View */}
      {!error && (
        <>
          {viewMode === "grid" ? (
            <ArtifactGrid
              artifacts={data?.artifacts || []}
              isLoading={isLoading}
              onArtifactClick={handleArtifactClick}
            />
          ) : (
            <ArtifactList
              artifacts={data?.artifacts || []}
              isLoading={isLoading}
              onArtifactClick={handleArtifactClick}
            />
          )}
        </>
      )}

      {/* Artifact Detail Drawer */}
      <ArtifactDetail
        artifact={selectedArtifact}
        isOpen={isDetailOpen}
        onClose={handleDetailClose}
      />
    </div>
  );
}
