'use client';

import React from 'react';
import { Play, Pencil, MoreHorizontal, Workflow, Clock } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn, formatDistanceToNow } from '@skillmeat/web/lib/utils';

export interface WorkflowCardProps {
  id: string;
  name: string;
  description?: string;
  stageCount: number;
  lastRunAt?: string | Date;
  tags: string[];
  onRun: (id: string) => void;
  onEdit: (id: string) => void;
  onDuplicate: (id: string) => void;
  onDelete: (id: string) => void;
  onClick?: (id: string) => void;
}

export function WorkflowCard({
  id,
  name,
  description,
  stageCount,
  lastRunAt,
  tags,
  onRun,
  onEdit,
  onDuplicate,
  onDelete,
  onClick,
}: WorkflowCardProps) {
  return (
    <div
      className="group relative rounded-lg border bg-card p-4 hover:shadow-md transition-shadow cursor-pointer"
      onClick={() => onClick?.(id)}
    >
      <div className="flex items-center gap-2 mb-2">
        <Workflow className="w-4 h-4 text-indigo-500 shrink-0" />
        <h3 className="text-sm font-semibold truncate" title={name}>
          {name}
        </h3>
      </div>

      <div className="flex items-center gap-3 text-xs text-muted-foreground mb-3">
        <span className="flex items-center gap-1">
          {stageCount} {stageCount === 1 ? 'stage' : 'stages'}
        </span>
        {lastRunAt && (
          <div className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            <span>{formatDistanceToNow(lastRunAt)}</span>
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-1 mb-4 h-5 overflow-hidden">
        {tags.slice(0, 3).map((tag) => (
          <Badge key={tag} variant="outline" className="text-[10px] px-1.5 py-0 font-normal">
            {tag}
          </Badge>
        ))}
        {tags.length > 3 && (
          <Badge variant="outline" className="text-[10px] px-1.5 py-0 font-normal">
            +{tags.length - 3}
          </Badge>
        )}
      </div>

      <div className="pt-3 border-t flex items-center justify-between">
        <div className="text-[10px] text-muted-foreground truncate max-w-[100px]">
          {lastRunAt ? (
            <span>Last run: {new Date(lastRunAt).toLocaleDateString()}</span>
          ) : (
            <span>Never run</span>
          )}
        </div>

        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
          <Button
            size="sm"
            variant="default"
            className="h-8 px-2 text-xs gap-1"
            onClick={() => onRun(id)}
          >
            <Play className="w-3.5 h-3.5" />
            Run
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="h-8 w-8 p-0"
            onClick={() => onEdit(id)}
          >
            <Pencil className="w-3.5 h-3.5" />
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button size="sm" variant="ghost" className="h-8 w-8 p-0">
                <MoreHorizontal className="w-3.5 h-3.5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => onDuplicate(id)}>
                Duplicate
              </DropdownMenuItem>
              <DropdownMenuItem
                className="text-destructive focus:text-destructive"
                onClick={() => onDelete(id)}
              >
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </div>
  );
}
