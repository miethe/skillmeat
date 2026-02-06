/**
 * Artifact Instance Indicator Component
 *
 * Displays a visual indicator for artifact instance levels:
 * - Source: GitHub icon with blue color (from marketplace/GitHub)
 * - Collection: Package icon with green color (user's collection, scope: 'user')
 * - Project: FolderOpen icon with purple color (deployed to project, scope: 'local')
 *
 * Positioned in top-right corner of modal with absolute positioning.
 * Includes tooltip explanations for each level.
 */

'use client';

import * as React from 'react';
import { Github, Package, FolderOpen } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { Artifact } from '@/types/artifact';

export interface ArtifactInstanceIndicatorProps {
  /** The artifact to display the instance level for */
  artifact: Artifact;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Configuration for each instance level
 */
const INSTANCE_LEVELS = {
  source: {
    label: 'Source',
    description: 'Available from marketplace or GitHub repository',
    icon: Github,
    colorClass: 'bg-blue-500 text-white border-blue-600',
    hexColor: '#3b82f6', // blue-500
  },
  collection: {
    label: 'Collection',
    description: 'Installed in your personal collection',
    icon: Package,
    colorClass: 'bg-green-500 text-white border-green-600',
    hexColor: '#22c55e', // green-500
  },
  project: {
    label: 'Project',
    description: 'Deployed to current project',
    icon: FolderOpen,
    colorClass: 'bg-purple-500 text-white border-purple-600',
    hexColor: '#a855f7', // purple-500
  },
} as const;

/**
 * Determine the instance level based on artifact properties
 */
function getInstanceLevel(artifact: Artifact): keyof typeof INSTANCE_LEVELS {
  // Project level: deployed to a project (scope: 'local')
  if (artifact.scope === 'local') {
    return 'project';
  }

  // Collection level: in user's collection (scope: 'user' and not from source)
  if (artifact.scope === 'user') {
    return 'collection';
  }

  // Source level: from marketplace or GitHub (origin check)
  if (artifact.origin === 'github' || artifact.origin === 'marketplace') {
    return 'source';
  }

  // Default to collection if unclear
  return 'collection';
}

/**
 * ArtifactInstanceIndicator - Visual indicator for artifact instance levels
 *
 * Shows where an artifact exists in the SkillMeat ecosystem:
 * - Source: Available from external repositories
 * - Collection: Installed in user's personal collection
 * - Project: Deployed to a specific project
 *
 * Positioned absolutely in top-right corner with appropriate colors and icons.
 * Includes hover tooltips with detailed explanations.
 *
 * @example
 * Basic usage in modal:
 * <div className="relative">
 *   <ArtifactInstanceIndicator artifact={artifact} />
 * </div>
 *
 * With custom styling:
 * <ArtifactInstanceIndicator
 *   artifact={artifact}
 *   className="top-4 right-4"
 * />
 *
 * @param props - ArtifactInstanceIndicatorProps configuration
 * @returns Badge component with instance level indicator
 */
export function ArtifactInstanceIndicator({ artifact, className }: ArtifactInstanceIndicatorProps) {
  const level = getInstanceLevel(artifact);
  const config = INSTANCE_LEVELS[level];
  const Icon = config.icon;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className={cn('absolute right-3 top-3 z-10', className)}>
            <Badge
              className={cn('px-2 py-1 text-xs font-medium shadow-sm', config.colorClass)}
              aria-label={`Instance level: ${config.label}`}
            >
              <Icon className="mr-1.5 h-3 w-3" />
              {config.label}
            </Badge>
          </div>
        </TooltipTrigger>
        <TooltipContent side="left" align="start">
          <div className="flex items-start gap-2">
            <Icon className="mt-0.5 h-4 w-4 text-muted-foreground" />
            <div>
              <p className="font-medium">{config.label}</p>
              <p className="max-w-48 text-xs text-muted-foreground">{config.description}</p>
            </div>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

/**
 * ArtifactInstanceIndicatorSkeleton - Loading skeleton for instance indicator
 *
 * Displays a placeholder while artifact data is being fetched.
 */
export function ArtifactInstanceIndicatorSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('absolute right-3 top-3 z-10', className)}>
      <div className="inline-flex animate-pulse items-center rounded-md border bg-muted px-2 py-1">
        <div className="mr-1.5 h-3 w-3 rounded bg-muted-foreground/20" />
        <span className="text-xs opacity-0">Collection</span>
      </div>
    </div>
  );
}
