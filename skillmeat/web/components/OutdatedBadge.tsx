/**
 * OutdatedBadge Component
 *
 * Visual indicator for artifacts with available updates
 */

import { Badge } from '@/components/ui/badge';
import { AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface OutdatedBadgeProps {
  isOutdated: boolean;
  deployedVersion?: string;
  upstreamVersion?: string;
  versionDifference?: string;
  onClick?: () => void;
  className?: string;
}

/**
 * Determine badge variant based on version difference
 * - Major version changes: destructive (red)
 * - Minor/patch changes: secondary (yellow/amber)
 */
function getBadgeVariant(versionDifference?: string): 'destructive' | 'secondary' | 'outline' {
  if (!versionDifference) return 'secondary';

  const lowerDiff = versionDifference.toLowerCase();

  // Major version upgrade indicates breaking changes
  if (lowerDiff.includes('major')) {
    return 'destructive';
  }

  // Minor/patch are less critical
  return 'secondary';
}

/**
 * Badge component showing update availability status
 */
export function OutdatedBadge({
  isOutdated,
  deployedVersion,
  upstreamVersion,
  versionDifference,
  onClick,
  className,
}: OutdatedBadgeProps) {
  if (!isOutdated) {
    return null;
  }

  const variant = getBadgeVariant(versionDifference);
  const isClickable = !!onClick;

  const tooltipText = [
    `Current: ${deployedVersion || 'unknown'}`,
    `Available: ${upstreamVersion || 'unknown'}`,
    versionDifference ? `(${versionDifference})` : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <Badge
      variant={variant}
      className={cn(
        'gap-1',
        isClickable && 'cursor-pointer hover:opacity-80 transition-opacity',
        className
      )}
      onClick={onClick}
      title={tooltipText}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={
        isClickable
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
    >
      <AlertTriangle className="h-3 w-3" />
      Update available
    </Badge>
  );
}
