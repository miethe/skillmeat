'use client';

import Link from 'next/link';
import { Copy, Edit3, Layers3, Rocket, Trash2 } from 'lucide-react';
import type { DeploymentSet } from '@/types/deployment-sets';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { COLOR_TAILWIND_CLASSES } from '@/lib/group-constants';

/**
 * Normalize a color value (token name or hex) to a valid hex string,
 * returning null when the input is not a valid hex.
 */
function normalizeHexColor(value: string): string | null {
  const hex = value.trim().replace(/^#/, '').toLowerCase();
  if (/^[0-9a-f]{3}$/.test(hex)) {
    return `#${hex
      .split('')
      .map((part) => `${part}${part}`)
      .join('')}`;
  }
  if (/^[0-9a-f]{6}$/.test(hex)) {
    return `#${hex}`;
  }
  return null;
}

interface DeploymentSetCardProps {
  set: DeploymentSet;
  onEdit: (set: DeploymentSet) => void;
  onDelete: (set: DeploymentSet) => void;
  onClone: (set: DeploymentSet) => void;
  onDeploy?: (set: DeploymentSet) => void;
}

export function DeploymentSetCard({ set, onEdit, onDelete, onClone, onDeploy }: DeploymentSetCardProps) {
  const tags = set.tags ?? [];
  const tokenColorClass =
    set.color && !set.color.startsWith('#')
      ? (COLOR_TAILWIND_CLASSES[set.color] ?? COLOR_TAILWIND_CLASSES.slate)
      : COLOR_TAILWIND_CLASSES.slate;
  const customColor = set.color ? normalizeHexColor(set.color) : null;
  const borderColorClass = customColor ? 'border-l-border' : tokenColorClass;

  return (
    <Card
      className={`border-l-4 ${borderColorClass} cursor-pointer transition-shadow hover:shadow-md`}
      style={customColor ? { borderLeftColor: customColor } : undefined}
      role="button"
      tabIndex={0}
      onClick={() => {}}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
        }
      }}
      aria-label={`Open ${set.name} deployment set`}
    >
      <CardHeader className="space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            {set.icon ? (
              <span className="shrink-0 text-base" aria-hidden="true">
                {set.icon}
              </span>
            ) : (
              <Layers3 className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            )}
            <CardTitle className="truncate text-base">{set.name}</CardTitle>
          </div>
          <Badge variant="secondary" aria-label={`${set.member_count} members`}>
            {set.member_count}
          </Badge>
        </div>
        <CardDescription className="line-clamp-2 min-h-[2.5rem]">
          {set.description || 'No description provided.'}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Tags row */}
        <div className="flex min-h-[1.5rem] flex-wrap gap-1">
          {tags.length > 0 ? (
            tags.map((tag) => (
              <Badge key={tag} variant="outline" className="text-xs">
                {tag}
              </Badge>
            ))
          ) : (
            <span className="text-xs text-muted-foreground">No tags</span>
          )}
        </div>

        <div className="text-xs text-muted-foreground">
          Updated {new Date(set.updated_at).toLocaleDateString()}
        </div>

        {/* Action buttons — stopPropagation so they don't trigger card click */}
        <div
          className="flex flex-wrap gap-2"
          onClick={(event) => event.stopPropagation()}
          onKeyDown={(event) => event.stopPropagation()}
        >
          <Button asChild size="sm">
            <Link href={`/deployment-sets/${set.id}`}>Open Set</Link>
          </Button>
          {onDeploy && (
            <Button size="sm" onClick={() => onDeploy(set)} aria-label={`Deploy ${set.name}`}>
              <Rocket className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
              Deploy
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={() => onEdit(set)}>
            <Edit3 className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
            Edit
          </Button>
          <Button variant="outline" size="sm" onClick={() => onClone(set)}>
            <Copy className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
            Clone
          </Button>
          <Button variant="outline" size="sm" onClick={() => onDelete(set)}>
            <Trash2 className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
            Delete
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
