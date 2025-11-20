"use client";

import {
  Package,
  Terminal,
  Bot,
  Server,
  Webhook,
  AlertCircle,
} from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { Artifact, ArtifactType } from "@/types/artifact";

interface ArtifactListProps {
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

const artifactTypeLabels: Record<ArtifactType, string> = {
  skill: "Skill",
  command: "Command",
  agent: "Agent",
  mcp: "MCP Server",
  hook: "Hook",
};

// Icon colors for type differentiation (matches grid view badge colors)
const artifactTypeIconColors: Record<ArtifactType, string> = {
  skill: "text-blue-700 dark:text-blue-400",
  command: "text-purple-700 dark:text-purple-400",
  agent: "text-green-700 dark:text-green-400",
  mcp: "text-orange-700 dark:text-orange-400",
  hook: "text-pink-700 dark:text-pink-400",
};

// Subtle row background tints for visual differentiation
const artifactTypeRowTints: Record<ArtifactType, string> = {
  skill: "bg-blue-500/[0.02] dark:bg-blue-500/[0.03]",
  command: "bg-purple-500/[0.02] dark:bg-purple-500/[0.03]",
  agent: "bg-green-500/[0.02] dark:bg-green-500/[0.03]",
  mcp: "bg-orange-500/[0.02] dark:bg-orange-500/[0.03]",
  hook: "bg-pink-500/[0.02] dark:bg-pink-500/[0.03]",
};

// Left border accent colors for each artifact type
const artifactTypeBorderAccents: Record<ArtifactType, string> = {
  skill: "border-l-blue-500",
  command: "border-l-purple-500",
  agent: "border-l-green-500",
  mcp: "border-l-orange-500",
  hook: "border-l-pink-500",
};

const statusColors: Record<string, string> = {
  active: "bg-green-500/10 text-green-600 border-green-500/20",
  outdated: "bg-yellow-500/10 text-yellow-600 border-yellow-500/20",
  conflict: "bg-orange-500/10 text-orange-600 border-orange-500/20",
  error: "bg-red-500/10 text-red-600 border-red-500/20",
};

function ArtifactListSkeleton() {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Version</TableHead>
          <TableHead>Scope</TableHead>
          <TableHead className="hidden md:table-cell">Deployments</TableHead>
          <TableHead className="hidden lg:table-cell">Last Updated</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {[...Array(5)].map((_, i) => (
          <TableRow key={i}>
            <TableCell>
              <div className="space-y-2">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-48" />
              </div>
            </TableCell>
            <TableCell>
              <Skeleton className="h-4 w-16" />
            </TableCell>
            <TableCell>
              <Skeleton className="h-5 w-16 rounded-full" />
            </TableCell>
            <TableCell>
              <Skeleton className="h-4 w-12" />
            </TableCell>
            <TableCell>
              <Skeleton className="h-4 w-12" />
            </TableCell>
            <TableCell className="hidden md:table-cell">
              <Skeleton className="h-4 w-8" />
            </TableCell>
            <TableCell className="hidden lg:table-cell">
              <Skeleton className="h-4 w-16" />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
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

export function ArtifactList({
  artifacts,
  isLoading,
  onArtifactClick,
}: ArtifactListProps) {
  if (isLoading) {
    return <ArtifactListSkeleton />;
  }

  if (artifacts.length === 0) {
    return (
      <div className="text-center py-12" data-testid="artifact-list-empty">
        <Package className="mx-auto h-12 w-12 text-muted-foreground/50" />
        <h3 className="mt-4 text-lg font-semibold">No artifacts found</h3>
        <p className="mt-2 text-sm text-muted-foreground">
          Try adjusting your filters or add new artifacts to your collection.
        </p>
      </div>
    );
  }

  return (
    <div className="border rounded-md" data-testid="artifact-list">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Version</TableHead>
            <TableHead>Scope</TableHead>
            <TableHead className="hidden md:table-cell">Deployments</TableHead>
            <TableHead className="hidden lg:table-cell">Last Updated</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {artifacts.map((artifact) => {
            const Icon = artifactTypeIcons[artifact.type];
            return (
              <TableRow
                key={artifact.id}
                className={`cursor-pointer border-l-2 ${artifactTypeBorderAccents[artifact.type]} ${artifactTypeRowTints[artifact.type]}`}
                onClick={() => onArtifactClick(artifact)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onArtifactClick(artifact);
                  }
                }}
                aria-label={`View details for ${artifact.name}`}
                data-testid="artifact-row"
              >
                <TableCell>
                  <div className="space-y-1">
                    <div className="font-medium flex items-center gap-2">
                      {artifact.metadata.title || artifact.name}
                      {artifact.upstreamStatus.isOutdated && (
                        <AlertCircle className="h-3 w-3 text-yellow-600" data-testid="outdated-indicator" />
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {artifact.metadata.description || artifact.name}
                    </div>
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2" data-testid="type-badge">
                    <Icon className={`h-4 w-4 ${artifactTypeIconColors[artifact.type]}`} aria-hidden="true" />
                    <span className="text-sm">
                      {artifactTypeLabels[artifact.type]}
                    </span>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge
                    className={statusColors[artifact.status]}
                    variant="outline"
                    data-testid="status-badge"
                  >
                    {artifact.status}
                  </Badge>
                </TableCell>
                <TableCell>
                  <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
                    {artifact.version || "N/A"}
                  </code>
                </TableCell>
                <TableCell>
                  <Badge variant="secondary" className="text-xs capitalize">
                    {artifact.scope}
                  </Badge>
                </TableCell>
                <TableCell className="hidden md:table-cell">
                  <div className="text-sm">
                    {artifact.usageStats.totalDeployments}
                  </div>
                </TableCell>
                <TableCell className="hidden lg:table-cell">
                  <div className="text-sm text-muted-foreground">
                    {formatRelativeTime(artifact.updatedAt)}
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
