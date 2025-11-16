"use client";

import {
  Package,
  Terminal,
  Bot,
  Server,
  Webhook,
  AlertCircle,
  Clock,
  TrendingUp,
} from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { Artifact, ArtifactType } from "@/types/artifact";

interface ArtifactGridProps {
  artifacts: Artifact[];
  isLoading?: boolean;
  onArtifactClick: (artifact: Artifact) => void;
}

const artifactTypeIcons: Record<
  ArtifactType,
  React.ComponentType<{ className?: string }>
> = {
  skill: Package,
  command: Terminal,
  agent: Bot,
  mcp: Server,
  hook: Webhook,
};

const artifactTypeColors: Record<ArtifactType, string> = {
  skill: "bg-blue-500/10 text-blue-500 border-blue-500/20",
  command: "bg-purple-500/10 text-purple-500 border-purple-500/20",
  agent: "bg-green-500/10 text-green-500 border-green-500/20",
  mcp: "bg-orange-500/10 text-orange-500 border-orange-500/20",
  hook: "bg-pink-500/10 text-pink-500 border-pink-500/20",
};

const statusColors: Record<string, string> = {
  active: "bg-green-500/10 text-green-600 border-green-500/20",
  outdated: "bg-yellow-500/10 text-yellow-600 border-yellow-500/20",
  conflict: "bg-orange-500/10 text-orange-600 border-orange-500/20",
  error: "bg-red-500/10 text-red-600 border-red-500/20",
};

function ArtifactCard({
  artifact,
  onClick,
}: {
  artifact: Artifact;
  onClick: () => void;
}) {
  const Icon = artifactTypeIcons[artifact.type];

  return (
    <Card
      className="cursor-pointer transition-all hover:shadow-md hover:border-primary/50"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      }}
      aria-label={`View details for ${artifact.name}`}
      data-testid="artifact-card"
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0 flex-1">
            <div
              className={`flex-shrink-0 p-2 rounded-md border ${artifactTypeColors[artifact.type]}`}
            >
              <Icon className="h-4 w-4" />
            </div>
            <div className="min-w-0 flex-1">
              <h3 className="font-semibold truncate" title={artifact.name}>
                {artifact.metadata.title || artifact.name}
              </h3>
              <p className="text-xs text-muted-foreground truncate">
                {artifact.name}
              </p>
            </div>
          </div>
          <Badge
            className={`flex-shrink-0 ${statusColors[artifact.status]}`}
            variant="outline"
            data-testid="status-badge"
          >
            {artifact.status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Description */}
        <p className="text-sm text-muted-foreground line-clamp-2">
          {artifact.metadata.description || "No description available"}
        </p>

        {/* Metadata */}
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-1" title="Version">
            <Package className="h-3 w-3" />
            <span>{artifact.version || "N/A"}</span>
          </div>
          <div className="flex items-center gap-1" title="Last updated">
            <Clock className="h-3 w-3" />
            <span>{formatRelativeTime(artifact.updatedAt)}</span>
          </div>
          <div className="flex items-center gap-1" title="Usage count">
            <TrendingUp className="h-3 w-3" />
            <span>{artifact.usageStats.usageCount}</span>
          </div>
        </div>

        {/* Tags */}
        {artifact.metadata.tags && artifact.metadata.tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {artifact.metadata.tags.slice(0, 3).map((tag) => (
              <Badge key={tag} variant="secondary" className="text-xs" data-testid="tag-badge">
                {tag}
              </Badge>
            ))}
            {artifact.metadata.tags.length > 3 && (
              <Badge variant="secondary" className="text-xs">
                +{artifact.metadata.tags.length - 3}
              </Badge>
            )}
          </div>
        )}

        {/* Warnings */}
        {artifact.upstreamStatus.isOutdated && (
          <div className="flex items-center gap-1 text-xs text-yellow-600" data-testid="outdated-warning">
            <AlertCircle className="h-3 w-3" />
            <span>Update available</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ArtifactGridSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="artifact-grid-skeleton">
      {[...Array(6)].map((_, i) => (
        <Card key={i}>
          <CardHeader className="pb-3">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2 flex-1">
                <Skeleton className="h-8 w-8 rounded-md" />
                <div className="space-y-2 flex-1">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-3 w-24" />
                </div>
              </div>
              <Skeleton className="h-5 w-16 rounded-full" />
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <Skeleton className="h-10 w-full" />
            <div className="flex gap-4">
              <Skeleton className="h-3 w-16" />
              <Skeleton className="h-3 w-16" />
              <Skeleton className="h-3 w-16" />
            </div>
            <div className="flex gap-1">
              <Skeleton className="h-5 w-12 rounded-full" />
              <Skeleton className="h-5 w-16 rounded-full" />
              <Skeleton className="h-5 w-14 rounded-full" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 30) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

export function ArtifactGrid({
  artifacts,
  isLoading,
  onArtifactClick,
}: ArtifactGridProps) {
  if (isLoading) {
    return <ArtifactGridSkeleton />;
  }

  if (artifacts.length === 0) {
    return (
      <div className="text-center py-12" data-testid="artifact-grid-empty">
        <Package className="mx-auto h-12 w-12 text-muted-foreground/50" />
        <h3 className="mt-4 text-lg font-semibold">No artifacts found</h3>
        <p className="mt-2 text-sm text-muted-foreground">
          Try adjusting your filters or add new artifacts to your collection.
        </p>
      </div>
    );
  }

  return (
    <div
      className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
      role="grid"
      aria-label="Artifact grid"
      data-testid="artifact-grid"
    >
      {artifacts.map((artifact) => (
        <ArtifactCard
          key={artifact.id}
          artifact={artifact}
          onClick={() => onArtifactClick(artifact)}
        />
      ))}
    </div>
  );
}
