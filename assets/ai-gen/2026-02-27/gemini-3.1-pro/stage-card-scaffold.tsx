'use client';

import * as React from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical, Pencil, X, Bot, Wrench, BookOpen } from 'lucide-react';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export type WorkflowStage = {
  id: string;
  name: string;
  description?: string;
  agentName?: string;
  tools: string[];
  contextModules: string[];
  timeout?: number;
  retryCount?: number;
  failureAction?: 'stop' | 'skip' | 'retry';
};

interface StageCardProps {
  stage: WorkflowStage;
  index: number;
  mode: 'edit' | 'readonly';
  onEdit?: () => void;
  onDelete?: () => void;
  isDragging?: boolean;
}

export const StageCard: React.FC<StageCardProps> = ({
  stage,
  index,
  mode,
  onEdit,
  onDelete,
  isDragging,
}) => {
  const isEditMode = mode === 'edit';

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
  } = useSortable({
    id: stage.id,
    disabled: !isEditMode,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const ReadonlyBadgeWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <button className="border-none bg-transparent p-0 text-left cursor-pointer hover:underline underline-offset-2">
      {children}
    </button>
  );

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'rounded-lg border p-4',
        isEditMode ? 'bg-card relative group' : 'bg-muted/30',
        isDragging && 'opacity-50'
      )}
      {...attributes}
    >
      {isEditMode && (
        <div
          {...listeners}
          className="absolute left-2 top-1/2 -translate-y-1/2 cursor-grab text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity"
        >
          <GripVertical className="h-4 w-4" />
        </div>
      )}

      <header className={cn('flex items-center gap-2', isEditMode && 'pl-6')}>
        <div className="inline-flex items-center justify-center h-6 w-6 rounded-full bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300 text-xs font-semibold shrink-0">
          {index}
        </div>
        <h3 className="text-sm font-semibold flex-1">{stage.name}</h3>
        {isEditMode && (
          <>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onEdit}>
              <Pencil className="h-3.5 w-3.5" />
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive" onClick={onDelete}>
              <X className="h-3.5 w-3.5" />
            </Button>
          </>
        )}
      </header>

      <div className="mt-3 space-y-1.5">
        {stage.agentName && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Bot className="h-3.5 w-3.5" />
            {isEditMode ? (
              <Badge variant="secondary" className="text-xs bg-indigo-50 text-indigo-700">
                {stage.agentName}
              </Badge>
            ) : (
              <ReadonlyBadgeWrapper>
                <Badge variant="secondary" className="text-xs bg-indigo-50 text-indigo-700">
                  {stage.agentName}
                </Badge>
              </ReadonlyBadgeWrapper>
            )}
          </div>
        )}

        {stage.tools.length > 0 && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Wrench className="h-3.5 w-3.5" />
            <div className="flex flex-wrap gap-1">
              {stage.tools.map((tool) =>
                isEditMode ? (
                  <Badge key={tool} variant="secondary" className="text-xs">
                    {tool}
                  </Badge>
                ) : (
                  <ReadonlyBadgeWrapper key={tool}>
                    <Badge variant="secondary" className="text-xs">
                      {tool}
                    </Badge>
                  </ReadonlyBadgeWrapper>
                )
              )}
            </div>
          </div>
        )}

        {stage.contextModules.length > 0 && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <BookOpen className="h-3.5 w-3.5" />
            <div className="flex flex-wrap gap-1">
              {stage.contextModules.map((mod) =>
                isEditMode ? (
                  <Badge key={mod} variant="secondary" className="text-xs">
                    {mod}
                  </Badge>
                ) : (
                  <ReadonlyBadgeWrapper key={mod}>
                    <Badge variant="secondary" className="text-xs">
                      {mod}
                    </Badge>
                  </ReadonlyBadgeWrapper>
                )
              )}
            </div>
          </div>
        )}

        {stage.description && (
          <p className="text-xs text-muted-foreground truncate">{stage.description}</p>
        )}
      </div>

      {!isEditMode && (stage.timeout !== undefined || stage.retryCount !== undefined) && (
        <footer className="mt-3 pt-3 border-t text-xs text-muted-foreground">
          {stage.timeout !== undefined && `Timeout: ${stage.timeout}m`}
          {stage.timeout !== undefined && stage.retryCount !== undefined && ' | '}
          {stage.retryCount !== undefined && `Retries: ${stage.retryCount}`}
        </footer>
      )}
    </div>
  );
};
