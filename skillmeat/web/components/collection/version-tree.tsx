"use client";

import { useMemo } from "react";
import {
  FolderOpen,
  GitBranch,
  AlertTriangle,
  CheckCircle2,
  Calendar,
  Hash,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { VersionGraph, VersionGraphNode } from "@/types/version";

interface VersionTreeViewProps {
  graph: VersionGraph | null | undefined;
  isLoading?: boolean;
}

/**
 * Format timestamp to relative time
 */
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
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/**
 * Truncate SHA hash for display
 */
function truncateSha(sha: string, length: number = 8): string {
  return sha.substring(0, length);
}

/**
 * Extract project name from path
 */
function getProjectName(path: string): string {
  const parts = path.split("/");
  return parts[parts.length - 1] || path;
}

/**
 * Tree node component for a single version
 */
function VersionTreeNode({
  node,
  isRoot = false,
  isLast = false,
  depth = 0,
}: {
  node: VersionGraphNode;
  isRoot?: boolean;
  isLast?: boolean;
  depth?: number;
}) {
  const { version_info, children, metadata } = node;
  const isCollection = version_info.location_type === "collection";
  const isModified = version_info.is_modified;

  // Determine display values
  const displayLocation = isCollection
    ? metadata.collection_name || "Collection"
    : getProjectName(version_info.location);

  const createdTime = formatRelativeTime(version_info.created_at);

  return (
    <div className="relative">
      {/* Tree connector lines */}
      {!isRoot && depth > 0 && (
        <>
          {/* Horizontal line */}
          <div
            className="absolute top-5 border-t border-border"
            style={{
              left: `${(depth - 1) * 24 + 4}px`,
              width: "16px",
            }}
          />
          {/* Vertical line from parent */}
          {!isLast && (
            <div
              className="absolute top-0 bottom-0 border-l border-border"
              style={{
                left: `${(depth - 1) * 24 + 4}px`,
              }}
            />
          )}
        </>
      )}

      {/* Node card */}
      <Card
        className={`mb-3 ${
          isCollection
            ? "border-primary/50 bg-primary/5"
            : isModified
              ? "border-yellow-500/50 bg-yellow-50/50 dark:bg-yellow-950/20"
              : "border-border bg-card"
        }`}
        style={{
          marginLeft: `${depth * 24}px`,
        }}
      >
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            {/* Icon */}
            <div
              className={`flex-shrink-0 p-2 rounded-lg ${
                isCollection
                  ? "bg-primary/10"
                  : isModified
                    ? "bg-yellow-500/10"
                    : "bg-muted"
              }`}
            >
              {isCollection ? (
                <FolderOpen
                  className={`h-4 w-4 ${isCollection ? "text-primary" : "text-muted-foreground"}`}
                />
              ) : (
                <GitBranch
                  className={`h-4 w-4 ${isModified ? "text-yellow-600" : "text-muted-foreground"}`}
                />
              )}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0 space-y-2">
              {/* Header */}
              <div className="flex items-center gap-2">
                <h4 className="font-semibold text-sm truncate">
                  {displayLocation}
                </h4>
                {isCollection && (
                  <Badge variant="outline" className="text-xs">
                    Source
                  </Badge>
                )}
                {isModified && (
                  <Badge
                    variant="outline"
                    className="text-xs bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border-yellow-500/30"
                  >
                    <AlertTriangle className="h-3 w-3 mr-1" />
                    Modified
                  </Badge>
                )}
                {!isModified && !isCollection && (
                  <Badge
                    variant="outline"
                    className="text-xs bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/30"
                  >
                    <CheckCircle2 className="h-3 w-3 mr-1" />
                    Synced
                  </Badge>
                )}
              </div>

              {/* Metadata grid */}
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                {/* Content SHA */}
                <div className="flex items-center gap-1 text-muted-foreground">
                  <Hash className="h-3 w-3" />
                  <code className="font-mono">
                    {truncateSha(version_info.content_sha)}
                  </code>
                </div>

                {/* Created time */}
                <div className="flex items-center gap-1 text-muted-foreground">
                  <Calendar className="h-3 w-3" />
                  <span>{createdTime}</span>
                </div>

                {/* Parent SHA (if modified) */}
                {version_info.parent_sha && (
                  <div className="col-span-2 flex items-center gap-1 text-muted-foreground">
                    <span className="text-xs">Parent:</span>
                    <code className="font-mono text-xs">
                      {truncateSha(version_info.parent_sha)}
                    </code>
                  </div>
                )}

                {/* Project path (if project deployment) */}
                {!isCollection && (
                  <div className="col-span-2 text-muted-foreground truncate">
                    <span className="text-xs">{version_info.location}</span>
                  </div>
                )}
              </div>

              {/* Additional metadata from node */}
              {metadata.deployed_at && (
                <div className="text-xs text-muted-foreground">
                  Deployed {formatRelativeTime(metadata.deployed_at)}
                </div>
              )}
              {metadata.modification_detected_at && (
                <div className="text-xs text-yellow-600 dark:text-yellow-400">
                  Modified {formatRelativeTime(metadata.modification_detected_at)}
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Render children */}
      {children && children.length > 0 && (
        <div className="relative">
          {children.map((child, index) => (
            <VersionTreeNode
              key={child.id}
              node={child}
              isLast={index === children.length - 1}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Loading skeleton for version tree
 */
function VersionTreeSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-24 w-full" />
      <div className="ml-6 space-y-3">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
      </div>
    </div>
  );
}

/**
 * Statistics summary component
 */
function VersionStatistics({ graph }: { graph: VersionGraph }) {
  const { statistics } = graph;

  return (
    <div className="grid grid-cols-4 gap-4 mb-6">
      <Card>
        <CardContent className="p-4">
          <div className="text-2xl font-bold">{statistics.total_deployments}</div>
          <div className="text-xs text-muted-foreground">Total Instances</div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-4">
          <div className="text-2xl font-bold text-green-600">
            {statistics.unmodified_count}
          </div>
          <div className="text-xs text-muted-foreground">Synced</div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-4">
          <div className="text-2xl font-bold text-yellow-600">
            {statistics.modified_count}
          </div>
          <div className="text-xs text-muted-foreground">Modified</div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-4">
          <div className="text-2xl font-bold text-orange-600">
            {statistics.orphaned_count}
          </div>
          <div className="text-xs text-muted-foreground">Orphaned</div>
        </CardContent>
      </Card>
    </div>
  );
}

/**
 * Main version tree visualization component
 */
export function VersionTreeView({ graph, isLoading }: VersionTreeViewProps) {
  // Memoize the tree rendering for performance
  const treeContent = useMemo(() => {
    if (!graph || !graph.root) {
      return (
        <div className="text-center py-8 text-muted-foreground">
          <GitBranch className="h-12 w-12 mx-auto mb-3 opacity-50" />
          <p>No version information available</p>
          <p className="text-xs mt-2">
            This artifact has not been deployed to any projects yet.
          </p>
        </div>
      );
    }

    return (
      <>
        <VersionStatistics graph={graph} />
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-muted-foreground mb-4">
            Version Tree
          </h3>
          <VersionTreeNode node={graph.root} isRoot={true} />
        </div>
      </>
    );
  }, [graph]);

  if (isLoading) {
    return <VersionTreeSkeleton />;
  }

  return <div className="w-full">{treeContent}</div>;
}
