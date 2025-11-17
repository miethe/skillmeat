"use client";

import { useState } from "react";
import {
  Package,
  Terminal,
  Bot,
  Server,
  Webhook,
  ExternalLink,
  Calendar,
  User,
  FileText,
  TrendingUp,
  AlertCircle,
  CheckCircle,
  XCircle,
  Tag,
  Copy,
  Trash2,
  RefreshCw,
  Upload,
} from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { DeployDialog } from "./deploy-dialog";
import { SyncDialog } from "./sync-dialog";
import type { Artifact, ArtifactType } from "@/types/artifact";

interface ArtifactDetailProps {
  artifact: Artifact | null;
  isOpen: boolean;
  onClose: () => void;
  isLoading?: boolean;
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

const statusIcons: Record<string, React.ComponentType<{ className?: string }>> =
  {
    active: CheckCircle,
    outdated: AlertCircle,
    conflict: AlertCircle,
    error: XCircle,
  };

const statusColors: Record<string, string> = {
  active: "text-green-600",
  outdated: "text-yellow-600",
  conflict: "text-orange-600",
  error: "text-red-600",
};

function DetailSkeleton() {
  return (
    <div className="space-y-6 pr-8">
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
      </div>

      <div className="space-y-3">
        <Skeleton className="h-6 w-32" />
        <div className="grid grid-cols-2 gap-4">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      </div>

      <div className="space-y-3">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-24 w-full" />
      </div>
    </div>
  );
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins} minutes ago`;
  if (diffHours < 24) return `${diffHours} hours ago`;
  if (diffDays < 30) return `${diffDays} days ago`;
  return formatDate(dateString);
}

export function ArtifactDetail({
  artifact,
  isOpen,
  onClose,
  isLoading,
}: ArtifactDetailProps) {
  const [isDeployDialogOpen, setIsDeployDialogOpen] = useState(false);
  const [isSyncDialogOpen, setIsSyncDialogOpen] = useState(false);

  if (!isOpen) return null;

  const Icon = artifact ? artifactTypeIcons[artifact.type] : Package;
  const StatusIcon = (artifact
    ? statusIcons[artifact.status]
    : CheckCircle) as React.ComponentType<{ className?: string }>;

  return (
    <>
      <Sheet open={isOpen} onOpenChange={(open) => !open && onClose()}>
        <SheetContent side="right" onClose={onClose}>
          {isLoading || !artifact ? (
            <DetailSkeleton />
          ) : (
            <div className="space-y-6 pr-8">
              {/* Header */}
              <SheetHeader>
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 p-3 rounded-lg bg-primary/10">
                    <Icon className="h-6 w-6 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <SheetTitle className="text-xl">
                      {artifact.metadata.title || artifact.name}
                    </SheetTitle>
                    <SheetDescription className="mt-1">
                      {artifactTypeLabels[artifact.type]} · {artifact.name}
                    </SheetDescription>
                  </div>
                </div>
              </SheetHeader>

              {/* Status Badge */}
              <div className="flex items-center gap-2">
                <StatusIcon
                  className={`h-4 w-4 ${statusColors[artifact.status]}`}
                />
                <Badge variant="outline" className="capitalize">
                  {artifact.status}
                </Badge>
                <Badge variant="secondary" className="capitalize">
                  {artifact.scope}
                </Badge>
              </div>

              {/* Description */}
              {artifact.metadata.description && (
                <div>
                  <p className="text-sm text-muted-foreground">
                    {artifact.metadata.description}
                  </p>
                </div>
              )}

              {/* Metadata Grid */}
              <div className="space-y-3">
                <h3 className="font-semibold text-sm">Metadata</h3>
                <div className="grid grid-cols-2 gap-3">
                  <MetadataItem
                    icon={<Package className="h-4 w-4" />}
                    label="Version"
                    value={artifact.version || "N/A"}
                  />
                  <MetadataItem
                    icon={<User className="h-4 w-4" />}
                    label="Author"
                    value={artifact.metadata.author || "Unknown"}
                  />
                  <MetadataItem
                    icon={<FileText className="h-4 w-4" />}
                    label="License"
                    value={artifact.metadata.license || "N/A"}
                  />
                  <MetadataItem
                    icon={<Calendar className="h-4 w-4" />}
                    label="Created"
                    value={formatDate(artifact.createdAt)}
                  />
                </div>
              </div>

              {/* Tags */}
              {artifact.metadata.tags && artifact.metadata.tags.length > 0 && (
                <div className="space-y-3">
                  <h3 className="font-semibold text-sm flex items-center gap-2">
                    <Tag className="h-4 w-4" />
                    Tags
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {artifact.metadata.tags.map((tag) => (
                      <Badge key={tag} variant="secondary">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Upstream Status */}
              <div className="space-y-3">
                <h3 className="font-semibold text-sm">Upstream Status</h3>
                <div className="rounded-lg border p-4 space-y-2">
                  {artifact.upstreamStatus.hasUpstream ? (
                    <>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">
                          Source
                        </span>
                        {artifact.source && (
                          <a
                            href={artifact.upstreamStatus.upstreamUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-primary hover:underline flex items-center gap-1"
                          >
                            {artifact.source}
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        )}
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">
                          Current Version
                        </span>
                        <code className="text-xs bg-muted px-2 py-1 rounded">
                          {artifact.upstreamStatus.currentVersion || "N/A"}
                        </code>
                      </div>
                      {artifact.upstreamStatus.isOutdated && (
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-muted-foreground">
                            Latest Version
                          </span>
                          <code className="text-xs bg-yellow-500/10 text-yellow-600 px-2 py-1 rounded border border-yellow-500/20">
                            {artifact.upstreamStatus.upstreamVersion}
                          </code>
                        </div>
                      )}
                      {artifact.upstreamStatus.lastChecked && (
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-muted-foreground">
                            Last Checked
                          </span>
                          <span className="text-sm">
                            {formatRelativeTime(
                              artifact.upstreamStatus.lastChecked
                            )}
                          </span>
                        </div>
                      )}
                    </>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      No upstream source configured
                    </p>
                  )}
                </div>
              </div>

              {/* Usage Stats */}
              <div className="space-y-3">
                <h3 className="font-semibold text-sm flex items-center gap-2">
                  <TrendingUp className="h-4 w-4" />
                  Usage Statistics
                </h3>
                <div className="grid grid-cols-2 gap-3">
                  <StatCard
                    label="Total Deployments"
                    value={artifact.usageStats.totalDeployments}
                  />
                  <StatCard
                    label="Active Projects"
                    value={artifact.usageStats.activeProjects}
                  />
                  <StatCard
                    label="Usage Count"
                    value={artifact.usageStats.usageCount}
                  />
                  <StatCard
                    label="Last Used"
                    value={
                      artifact.usageStats.lastUsed
                        ? formatRelativeTime(artifact.usageStats.lastUsed)
                        : "Never"
                    }
                  />
                </div>
              </div>

              {/* Aliases */}
              {artifact.aliases && artifact.aliases.length > 0 && (
                <div className="space-y-3">
                  <h3 className="font-semibold text-sm">Aliases</h3>
                  <div className="flex flex-wrap gap-2">
                    {artifact.aliases.map((alias) => (
                      <code
                        key={alias}
                        className="text-xs bg-muted px-2 py-1 rounded"
                      >
                        {alias}
                      </code>
                    ))}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="space-y-3 pt-4 border-t">
                <h3 className="font-semibold text-sm">Actions</h3>
                <div className="flex flex-col gap-2">
                  {/* Deploy Button */}
                  <Button
                    variant="default"
                    className="w-full justify-start"
                    onClick={() => setIsDeployDialogOpen(true)}
                  >
                    <Upload className="h-4 w-4 mr-2" />
                    Deploy to Project
                  </Button>

                  {/* Sync Button */}
                  {artifact.upstreamStatus.hasUpstream && (
                    <Button
                      variant={
                        artifact.upstreamStatus.isOutdated
                          ? "default"
                          : "outline"
                      }
                      className="w-full justify-start"
                      onClick={() => setIsSyncDialogOpen(true)}
                    >
                      <RefreshCw className="h-4 w-4 mr-2" />
                      {artifact.upstreamStatus.isOutdated
                        ? "Update to Latest Version"
                        : "Sync with Upstream"}
                    </Button>
                  )}

                  <Button variant="outline" className="w-full justify-start">
                    <Copy className="h-4 w-4 mr-2" />
                    Duplicate Artifact
                  </Button>
                  <Button
                    variant="outline"
                    className="w-full justify-start text-destructive hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Remove from Collection
                  </Button>
                </div>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>

      {/* Deploy Dialog */}
      <DeployDialog
        artifact={artifact}
        isOpen={isDeployDialogOpen}
        onClose={() => setIsDeployDialogOpen(false)}
        onSuccess={() => {
          // Refresh artifact data or show success message
          setIsDeployDialogOpen(false);
        }}
      />

      {/* Sync Dialog */}
      <SyncDialog
        artifact={artifact}
        isOpen={isSyncDialogOpen}
        onClose={() => setIsSyncDialogOpen(false)}
        onSuccess={() => {
          // Refresh artifact data or show success message
          setIsSyncDialogOpen(false);
        }}
      />
    </>
  );
}

function MetadataItem({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1 text-xs text-muted-foreground">
        {icon}
        <span>{label}</span>
      </div>
      <p className="text-sm font-medium truncate" title={value}>
        {value}
      </p>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border p-3 space-y-1">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold">{value}</p>
    </div>
  );
}
