'use client';

import Link from 'next/link';
import { Book, Folder, Layers, Sparkles, Tag, Trash2, Wrench, Copy, Edit3 } from 'lucide-react';
import type { Group } from '@/types/groups';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

const colorClassMap: Record<string, string> = {
  slate: 'border-l-slate-500',
  blue: 'border-l-blue-500',
  green: 'border-l-green-500',
  amber: 'border-l-amber-500',
  rose: 'border-l-rose-500',
};

const iconMap = {
  layers: Layers,
  folder: Folder,
  tag: Tag,
  sparkles: Sparkles,
  book: Book,
  wrench: Wrench,
} as const;

interface GroupCardProps {
  group: Group;
  onOpenDetails: (group: Group) => void;
  onEdit: (group: Group) => void;
  onDelete: (group: Group) => void;
  onCopy: (group: Group) => void;
}

export function GroupCard({ group, onOpenDetails, onEdit, onDelete, onCopy }: GroupCardProps) {
  const GroupIcon = iconMap[group.icon ?? 'layers'] ?? Layers;
  const tags = group.tags ?? [];
  const colorClass = colorClassMap[group.color ?? 'slate'] ?? colorClassMap.slate;

  return (
    <Card
      className={`border-l-4 ${colorClass} cursor-pointer transition-shadow hover:shadow-md`}
      role="button"
      tabIndex={0}
      onClick={() => onOpenDetails(group)}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          onOpenDetails(group);
        }
      }}
      aria-label={`Open details for ${group.name}`}
    >
      <CardHeader className="space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <GroupIcon className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            <CardTitle className="truncate text-base">{group.name}</CardTitle>
          </div>
          <Badge variant="secondary">{group.artifact_count}</Badge>
        </div>
        <CardDescription className="line-clamp-2 min-h-[2.5rem]">
          {group.description || 'No description provided.'}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-3">
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
          Updated {new Date(group.updated_at).toLocaleDateString()}
        </div>

        <div className="flex flex-wrap gap-2" onClick={(event) => event.stopPropagation()}>
          <Button asChild size="sm">
            <Link href={`/collection?collection=${group.collection_id}&group=${group.id}`}>
              Open Artifacts
            </Link>
          </Button>
          <Button variant="outline" size="sm" onClick={() => onEdit(group)}>
            <Edit3 className="mr-1 h-3.5 w-3.5" />
            Edit
          </Button>
          <Button variant="outline" size="sm" onClick={() => onCopy(group)}>
            <Copy className="mr-1 h-3.5 w-3.5" />
            Copy
          </Button>
          <Button variant="outline" size="sm" onClick={() => onDelete(group)}>
            <Trash2 className="mr-1 h-3.5 w-3.5" />
            Delete
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
