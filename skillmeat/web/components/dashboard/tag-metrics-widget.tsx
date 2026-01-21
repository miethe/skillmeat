/**
 * Tag Metrics Widget
 *
 * Dashboard widget showing tag statistics and top tags by artifact count
 */

'use client';

import { useTags } from '@/hooks';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Tag } from 'lucide-react';

interface TagMetricsWidgetProps {
  limit?: number;
  className?: string;
}

/**
 * Tag metrics widget showing overall tag stats and top tags
 *
 * Displays:
 * - Total number of tags
 * - Total tagged artifacts
 * - Top 5 tags by artifact count
 *
 * @example
 * ```tsx
 * <TagMetricsWidget limit={5} />
 * ```
 */
export function TagMetricsWidget({ limit = 5, className }: TagMetricsWidgetProps) {
  const { data: tagsData, isLoading } = useTags(100);
  const tags = tagsData?.items || [];

  // Calculate metrics
  const totalTags = tags.length;
  const topTags = tags
    .filter((t) => t.artifact_count !== undefined && t.artifact_count > 0)
    .sort((a, b) => (b.artifact_count || 0) - (a.artifact_count || 0))
    .slice(0, limit);
  const totalTagged = tags.reduce((sum, t) => sum + (t.artifact_count || 0), 0);

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Tag className="h-5 w-5" />
            Tags
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-4 grid grid-cols-2 gap-4">
            <div>
              <Skeleton className="mb-1 h-8 w-16" />
              <Skeleton className="h-4 w-24" />
            </div>
            <div>
              <Skeleton className="mb-1 h-8 w-16" />
              <Skeleton className="h-4 w-32" />
            </div>
          </div>
          <div className="space-y-2">
            <Skeleton className="mb-2 h-4 w-20" />
            {[...Array(limit)].map((_, i) => (
              <div key={i} className="flex items-center justify-between">
                <Skeleton className="h-6 w-24" />
                <Skeleton className="h-4 w-12" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Tag className="h-5 w-5" />
          Tags
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Summary Stats */}
        <div className="mb-4 grid grid-cols-2 gap-4">
          <div>
            <div className="text-2xl font-bold">{totalTags}</div>
            <div className="text-sm text-muted-foreground">Total Tags</div>
          </div>
          <div>
            <div className="text-2xl font-bold">{totalTagged}</div>
            <div className="text-sm text-muted-foreground">Tagged Artifacts</div>
          </div>
        </div>

        {/* Top Tags */}
        {topTags.length > 0 && (
          <div className="space-y-2">
            <div className="text-sm font-medium">Top Tags</div>
            {topTags.map((tag) => (
              <div key={tag.id} className="flex items-center justify-between">
                <Badge variant="secondary" colorStyle={tag.color}>
                  {tag.name}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  {tag.artifact_count} {tag.artifact_count === 1 ? 'artifact' : 'artifacts'}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Empty State */}
        {topTags.length === 0 && (
          <div className="py-4 text-center text-sm text-muted-foreground">No tags created yet</div>
        )}
      </CardContent>
    </Card>
  );
}
