'use client';

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { ChangeOrigin } from '@/types/drift';

interface ChangeBadgeProps {
  origin: ChangeOrigin;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  showTooltip?: boolean;
  className?: string;
}

const ORIGIN_CONFIG = {
  upstream: {
    label: 'Upstream',
    tooltip: 'Changed in upstream repository only',
    color: 'bg-blue-100 text-blue-700 border-blue-200',
    darkColor: 'dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-700',
    icon: '↓', // Down arrow - changes coming from upstream
  },
  local: {
    label: 'Local',
    tooltip: 'Modified locally (not in upstream)',
    color: 'bg-amber-100 text-amber-700 border-amber-200',
    darkColor: 'dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-700',
    icon: '✎', // Edit - local modifications
  },
  both: {
    label: 'Conflict',
    tooltip: 'Changed both locally and upstream - requires merge',
    color: 'bg-red-100 text-red-700 border-red-200',
    darkColor: 'dark:bg-red-900/30 dark:text-red-300 dark:border-red-700',
    icon: '⚠', // Warning - needs merge
  },
  none: {
    label: 'No Changes',
    tooltip: 'No changes detected',
    color: 'bg-gray-100 text-gray-600 border-gray-200',
    darkColor: 'dark:bg-gray-800 dark:text-gray-400 dark:border-gray-600',
    icon: '✓', // Check - no changes
  },
};

const SIZE_CLASSES = {
  sm: 'text-xs px-1.5 py-0.5',
  md: 'text-sm px-2 py-1',
  lg: 'text-base px-3 py-1.5',
};

export function ChangeBadge({
  origin,
  size = 'md',
  showLabel = true,
  showTooltip = true,
  className,
}: ChangeBadgeProps) {
  const config = ORIGIN_CONFIG[origin];

  const badge = (
    <Badge
      variant="outline"
      className={cn(
        'font-medium border cursor-default',
        config.color,
        config.darkColor,
        SIZE_CLASSES[size],
        className
      )}
    >
      <span className="mr-1">{config.icon}</span>
      {showLabel && config.label}
    </Badge>
  );

  if (!showTooltip) {
    return badge;
  }

  return (
    <TooltipProvider delayDuration={300}>
      <Tooltip>
        <TooltipTrigger asChild>{badge}</TooltipTrigger>
        <TooltipContent side="top" sideOffset={5}>
          <p className="text-sm">{config.tooltip}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
