'use client';

import * as React from 'react';
import { Github, Layers, Folder, ArrowRight, Loader2, ChevronUp, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { Artifact } from '@/types/artifact';

export interface ArtifactFlowBannerProps {
  artifact: Artifact;
  sourceInfo: {
    version: string;
    sha: string;
    hasUpdate: boolean;
    source: string;
  } | null;
  collectionInfo: {
    version: string;
    sha: string;
  };
  projectInfo: {
    version: string;
    sha: string;
    isModified: boolean;
    projectPath: string;
  } | null;
  onPullFromSource: () => void;
  onDeployToProject: () => void;
  onPushToCollection: () => void;
  isPulling: boolean;
  isDeploying: boolean;
  isPushing: boolean;
}

/**
 * ArtifactFlowBanner Component
 *
 * Visualizes the 3-tier artifact synchronization flow:
 * Source (GitHub) → Collection (Local) → Project (Deployed)
 *
 * Features:
 * - Three nodes with version + SHA display
 * - Status badges for updates and modifications
 * - Action buttons on connectors for sync operations
 * - Loading states during async operations
 * - Dark mode support
 *
 * @example
 * ```tsx
 * <ArtifactFlowBanner
 *   artifact={artifact}
 *   sourceInfo={{ version: "1.0.0", sha: "abc1234", hasUpdate: true, source: "user/repo" }}
 *   collectionInfo={{ version: "0.9.0", sha: "def5678" }}
 *   projectInfo={{ version: "0.9.0", sha: "def5678", isModified: true, projectPath: "/path" }}
 *   onPullFromSource={handlePull}
 *   onDeployToProject={handleDeploy}
 *   onPushToCollection={handlePush}
 *   isPulling={false}
 *   isDeploying={false}
 *   isPushing={false}
 * />
 * ```
 */
export function ArtifactFlowBanner({
  artifact: _artifact, // Unused but kept for API consistency
  sourceInfo,
  collectionInfo,
  projectInfo,
  onPullFromSource,
  onDeployToProject,
  onPushToCollection,
  isPulling,
  isDeploying,
  isPushing,
}: ArtifactFlowBannerProps) {
  const [isCollapsed, setIsCollapsed] = React.useState(false);
  const truncateSha = (sha: string): string => sha.slice(0, 7);

  if (isCollapsed) {
    const hasAnyIndicator = sourceInfo?.hasUpdate || projectInfo?.isModified;

    return (
      <div
        className={cn(
          "flex w-full cursor-pointer items-center gap-3 rounded-lg border bg-card px-4 transition-colors hover:bg-accent/50",
          hasAnyIndicator ? "py-3" : "py-2"
        )}
        onClick={() => setIsCollapsed(false)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setIsCollapsed(false);
          }
        }}
        aria-label="Expand artifact flow banner"
      >
        {/* Source summary */}
        <div className={cn(
          "flex items-center gap-1.5",
          sourceInfo?.hasUpdate && "relative rounded-md border border-blue-500 px-2 py-1"
        )}>
          <Github className="h-3.5 w-3.5 text-muted-foreground" />
          {sourceInfo ? (
            <code className="rounded bg-muted px-1 py-0.5 text-[10px] font-mono text-muted-foreground">
              {truncateSha(sourceInfo.sha)}
            </code>
          ) : (
            <span className="text-[10px] italic text-muted-foreground/50">Not configured</span>
          )}
          {sourceInfo?.hasUpdate && (
            <span className="absolute -right-1 -top-2 rounded-sm bg-blue-500 px-1 text-[9px] leading-tight text-white">
              New Update
            </span>
          )}
        </div>

        <ArrowRight className="h-3 w-3 shrink-0 text-muted-foreground" />

        {/* Collection summary */}
        <div className="flex items-center gap-1.5">
          <Layers className="h-3.5 w-3.5 text-muted-foreground" />
          <code className="rounded bg-muted px-1 py-0.5 text-[10px] font-mono text-muted-foreground">
            {truncateSha(collectionInfo.sha)}
          </code>
        </div>

        <ArrowRight className="h-3 w-3 shrink-0 text-muted-foreground" />

        {/* Project summary */}
        <div className={cn(
          "flex items-center gap-1.5",
          projectInfo?.isModified && "relative rounded-md border border-amber-500 px-2 py-1"
        )}>
          <Folder className="h-3.5 w-3.5 text-muted-foreground" />
          {projectInfo ? (
            <code className="rounded bg-muted px-1 py-0.5 text-[10px] font-mono text-muted-foreground">
              {truncateSha(projectInfo.sha)}
            </code>
          ) : (
            <span className="text-[10px] italic text-muted-foreground/50">Not deployed</span>
          )}
          {projectInfo?.isModified && (
            <span className="absolute -right-1 -top-2 rounded-sm bg-amber-500/80 px-1 text-[9px] leading-tight text-amber-950 dark:bg-amber-500/90 dark:text-white">
              Modified
            </span>
          )}
        </div>

        {/* Expand indicator */}
        <ChevronDown className="ml-auto h-4 w-4 shrink-0 text-muted-foreground transition-colors hover:text-foreground" />
      </div>
    );
  }

  return (
    <div className="relative w-full rounded-lg border bg-card p-6">
      {/* Collapse button */}
      <button
        type="button"
        onClick={() => setIsCollapsed(true)}
        className="absolute right-3 top-3 rounded-md p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        aria-label="Collapse artifact flow banner"
      >
        <ChevronUp className="h-4 w-4" />
      </button>

      <div className="flex items-center justify-between gap-4">
        {/* SOURCE NODE */}
        <div className="flex flex-col items-center gap-2">
          <div
            className={cn(
              'flex h-20 w-32 flex-col items-center justify-center rounded-lg border-2 bg-background p-3',
              sourceInfo ? 'border-muted-foreground' : 'border-dashed border-muted'
            )}
          >
            <Github
              className={cn('h-6 w-6', sourceInfo ? 'text-foreground' : 'text-muted-foreground')}
            />
            <span className="mt-1 text-xs font-medium text-muted-foreground">Source</span>
          </div>
          {sourceInfo ? (
            <div className="flex flex-col items-center gap-1 text-center">
              <span className="text-xs font-medium">{sourceInfo.version}</span>
              <code className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                {truncateSha(sourceInfo.sha)}
              </code>
              {sourceInfo.hasUpdate && (
                <Badge variant="default" className="mt-1 bg-blue-500 text-xs">
                  New Update
                </Badge>
              )}
            </div>
          ) : (
            <span className="text-xs text-muted-foreground">Not configured</span>
          )}
        </div>

        {/* CONNECTOR 1: Source → Collection */}
        <div className="flex flex-1 flex-col items-center gap-2">
          <svg width="100%" height="40" className="overflow-visible">
            <path
              d={`M 10 20 Q ${50} 20, ${90} 20`}
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="text-muted-foreground"
            />
            <path
              d={`M ${85} 15 L ${95} 20 L ${85} 25`}
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="text-muted-foreground"
            />
          </svg>
          <Button
            size="sm"
            onClick={onPullFromSource}
            disabled={!sourceInfo || isPulling}
            className="h-7 text-xs"
            title={!sourceInfo ? 'No upstream source configured' : 'Pull latest from source'}
          >
            {isPulling ? (
              <>
                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                Pulling...
              </>
            ) : (
              <>
                <ArrowRight className="mr-1 h-3 w-3" />
                Pull from Source
              </>
            )}
          </Button>
        </div>

        {/* COLLECTION NODE */}
        <div className="flex flex-col items-center gap-2">
          <div className="flex h-20 w-32 flex-col items-center justify-center rounded-lg border-2 border-primary bg-background p-3">
            <Layers className="h-6 w-6 text-primary" />
            <span className="mt-1 text-xs font-medium text-muted-foreground">Collection</span>
          </div>
          <div className="flex flex-col items-center gap-1 text-center">
            <span className="text-xs font-medium">{collectionInfo.version}</span>
            <code className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
              {truncateSha(collectionInfo.sha)}
            </code>
          </div>
        </div>

        {/* CONNECTOR 2: Collection → Project */}
        <div className="flex flex-1 flex-col items-center gap-2">
          <svg width="100%" height="40" className="overflow-visible">
            <path
              d={`M 10 20 Q ${50} 20, ${90} 20`}
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="text-muted-foreground"
            />
            <path
              d={`M ${85} 15 L ${95} 20 L ${85} 25`}
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="text-muted-foreground"
            />
          </svg>
          <Button
            size="sm"
            onClick={onDeployToProject}
            disabled={!projectInfo || isDeploying}
            className="h-7 text-xs"
            title={!projectInfo ? 'No project deployment found' : 'Deploy to project'}
          >
            {isDeploying ? (
              <>
                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                Deploying...
              </>
            ) : (
              <>
                <ArrowRight className="mr-1 h-3 w-3" />
                Deploy to Project
              </>
            )}
          </Button>
        </div>

        {/* PROJECT NODE */}
        <div className="flex flex-col items-center gap-2">
          <div
            className={cn(
              'flex h-20 w-32 flex-col items-center justify-center rounded-lg border-2 bg-background p-3',
              projectInfo
                ? projectInfo.isModified
                  ? 'border-orange-500 bg-orange-500/10'
                  : 'border-muted-foreground'
                : 'border-dashed border-muted'
            )}
          >
            <Folder
              className={cn(
                'h-6 w-6',
                projectInfo
                  ? projectInfo.isModified
                    ? 'text-orange-500'
                    : 'text-foreground'
                  : 'text-muted-foreground'
              )}
            />
            <span className="mt-1 text-xs font-medium text-muted-foreground">Project</span>
          </div>
          {projectInfo ? (
            <div className="flex flex-col items-center gap-1 text-center">
              <span className="text-xs font-medium">{projectInfo.version}</span>
              <code className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                {truncateSha(projectInfo.sha)}
              </code>
              {projectInfo.isModified && (
                <Badge
                  variant="secondary"
                  className="mt-1 bg-yellow-500/20 text-xs text-yellow-700 dark:text-yellow-400"
                >
                  Modified
                </Badge>
              )}
            </div>
          ) : (
            <span className="text-xs text-muted-foreground">Not deployed</span>
          )}
        </div>

        {/* CONNECTOR 3: Project → Collection */}
        <div className="flex flex-1 flex-col items-center gap-2">
          <svg width="100%" height="40" className="overflow-visible">
            <path
              d={`M 10 20 Q ${50} 20, ${90} 20`}
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeDasharray={projectInfo ? undefined : '4 4'}
              className={projectInfo ? 'text-muted-foreground' : 'text-muted'}
            />
            <path
              d={`M ${5} 15 L ${10} 20 L ${5} 25`}
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className={projectInfo ? 'text-muted-foreground' : 'text-muted'}
            />
          </svg>
          <Button
            size="sm"
            variant={projectInfo?.isModified ? 'default' : 'ghost'}
            onClick={onPushToCollection}
            disabled={!projectInfo || isPushing}
            className="h-7 text-xs"
            title={!projectInfo ? 'No project deployment found' : 'Push local changes back to collection'}
          >
            {isPushing ? (
              <>
                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                Pushing...
              </>
            ) : (
              <>
                <ArrowRight className="mr-1 h-3 w-3 rotate-180" />
                Push to Collection
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
